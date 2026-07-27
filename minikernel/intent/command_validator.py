"""
Command Validator

Validates and sanitizes commands before execution
Implements the safety layer for agentic security
"""

import logging
import os
import re
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum

from minikernel.intent.intent_parser import IntentResult, IntentType

logger = logging.getLogger("MiniKernel.Validator")


class RiskLevel(Enum):
    """Command risk levels"""
    SAFE = "safe"           # No risk, execute immediately
    LOW = "low"             # Minor risk, log only
    MEDIUM = "medium"       # Moderate risk, confirmation recommended
    HIGH = "high"           # High risk, confirmation required
    CRITICAL = "critical"   # Destructive, must confirm


@dataclass
class ValidationResult:
    """Result of command validation"""
    is_valid: bool
    risk_level: RiskLevel
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None
    warnings: List[str] = None
    errors: List[str] = None
    sanitized_params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []


class CommandValidator:
    """
    Command Validator - Safety layer for AI commands
    
    Responsibilities:
    1. Validate command parameters
    2. Assess risk level
    3. Sanitize inputs (prevent injection)
    4. Determine if human confirmation needed
    """
    
    def __init__(self):
        # Patterns for dangerous operations
        self.dangerous_patterns = [
            r"rm\s+-rf\s+/",
            r"format\s+",
            r"mkfs\.",
            r"dd\s+.*of=/dev/",
            r":(){:|:&};:",  # Fork bomb
        ]
        
        # Protected paths (cannot be deleted without confirmation)
        self.protected_paths = {
            "/", "/bin", "/boot", "/etc", "/lib", "/lib64",
            "/proc", "/root", "/sbin", "/sys", "/usr", "/var"
        }
        
        # Safe file extensions
        self.safe_extensions = {
            ".txt", ".md", ".json", ".log", ".csv",
            ".jpg", ".png", ".gif", ".pdf"
        }
        
        logger.info("Command Validator initialized")
    
    def validate(self, intent: IntentResult) -> ValidationResult:
        """
        Validate an intent before execution
        
        Args:
            intent: Parsed intent to validate
            
        Returns:
            ValidationResult with risk assessment
        """
        # Start with safe assumption
        result = ValidationResult(
            is_valid=True,
            risk_level=RiskLevel.SAFE,
            sanitized_params=intent.parameters.copy()
        )
        
        # Route to specific validators
        if intent.intent_type == IntentType.FILE_OPERATION:
            return self._validate_file_operation(intent)
        elif intent.intent_type == IntentType.PROCESS_CONTROL:
            return self._validate_process_control(intent)
        elif intent.intent_type == IntentType.PACKAGE_MANAGEMENT:
            return self._validate_package_management(intent)
        elif intent.intent_type == IntentType.SYSTEM_INFO:
            return self._validate_system_info(intent)
        
        return result
    
    def _validate_file_operation(self, intent: IntentResult) -> ValidationResult:
        """Validate file operations"""
        action = intent.action
        params = intent.parameters
        
        # DELETE operations - highest risk
        if action == "delete":
            target = params.get("target", "")

            # Check if targeting protected path
            if self._is_protected_path(target):
                return ValidationResult(
                    is_valid=False,
                    risk_level=RiskLevel.CRITICAL,
                    errors=[f"Cannot delete protected path: {target}"]
                )
            
            # Check for wildcards in sensitive locations
            if "*" in target or "?" in target:
                return ValidationResult(
                    is_valid=True,
                    risk_level=RiskLevel.HIGH,
                    requires_confirmation=True,
                    confirmation_prompt=f"Delete multiple files matching '{target}'?",
                    warnings=["Wildcard deletion detected"]
                )
            
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=True,
                confirmation_prompt=f"Delete '{target}'?",
                sanitized_params=params
            )
        
        # MOVE/RENAME operations
        elif action in ["move", "rename"]:
            source = params.get("source", "")
            dest = params.get("destination", "")
            
            # Prevent overwriting system files
            if self._is_protected_path(dest):
                return ValidationResult(
                    is_valid=False,
                    risk_level=RiskLevel.HIGH,
                    errors=[f"Cannot move to protected location: {dest}"]
                )
            
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.LOW,
                sanitized_params=self._sanitize_paths(params)
            )
        
        # COPY operations - generally safe
        elif action == "copy":
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.SAFE,
                sanitized_params=self._sanitize_paths(params)
            )
        
        # FIND/LIST operations - read-only, safe
        elif action in ["find", "list"]:
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.SAFE,
                sanitized_params=self._sanitize_paths(params)
            )
        
        return ValidationResult(
            is_valid=True,
            risk_level=RiskLevel.LOW,
            sanitized_params=params
        )
    
    def _validate_process_control(self, intent: IntentResult) -> ValidationResult:
        """Validate process control operations"""
        action = intent.action
        params = intent.parameters
        
        # KILL/STOP operations
        if action in ["stop", "kill"]:
            process = params.get("process", "")
            
            # Protected system processes
            protected_processes = {
                "init", "systemd", "kernel", "minikernel"
            }
            
            if process.lower() in protected_processes:
                return ValidationResult(
                    is_valid=False,
                    risk_level=RiskLevel.CRITICAL,
                    errors=[f"Cannot kill protected process: {process}"]
                )
            
            # Force kill requires confirmation
            if params.get("force", False):
                return ValidationResult(
                    is_valid=True,
                    risk_level=RiskLevel.MEDIUM,
                    requires_confirmation=True,
                    confirmation_prompt=f"Force kill process '{process}'?",
                    sanitized_params=params
                )
            
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.LOW,
                sanitized_params=params
            )
        
        # START operations - check for dangerous commands
        elif action == "start":
            program = params.get("program", "")
            
            # Check against dangerous patterns
            for pattern in self.dangerous_patterns:
                if re.search(pattern, program):
                    return ValidationResult(
                        is_valid=False,
                        risk_level=RiskLevel.CRITICAL,
                        errors=[f"Dangerous command detected: {program}"]
                    )
            
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.SAFE,
                sanitized_params=self._sanitize_command(params)
            )
        
        # LIST/STATUS - read-only, safe
        elif action in ["list", "status"]:
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.SAFE,
                sanitized_params=params
            )
        
        return ValidationResult(
            is_valid=True,
            risk_level=RiskLevel.LOW,
            sanitized_params=params
        )
    
    def _validate_package_management(self, intent: IntentResult) -> ValidationResult:
        """Validate package management operations"""
        action = intent.action
        params = intent.parameters
        
        # INSTALL operations - medium risk
        if action == "install":
            package = params.get("package", "")
            
            # Validate package name (prevent injection)
            if not self._is_valid_package_name(package):
                return ValidationResult(
                    is_valid=False,
                    risk_level=RiskLevel.HIGH,
                    errors=[f"Invalid package name: {package}"]
                )
            
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=True,
                confirmation_prompt=f"Install package '{package}'?",
                sanitized_params={"package": self._sanitize_package_name(package)}
            )
        
        # UNINSTALL operations - medium risk
        elif action == "uninstall":
            package = params.get("package", "")
            
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.MEDIUM,
                requires_confirmation=True,
                confirmation_prompt=f"Uninstall package '{package}'?",
                sanitized_params={"package": self._sanitize_package_name(package)}
            )
        
        # UPDATE operations - low risk
        elif action == "update_all":
            return ValidationResult(
                is_valid=True,
                risk_level=RiskLevel.LOW,
                requires_confirmation=True,
                confirmation_prompt="Update all packages?",
                sanitized_params=params
            )
        
        return ValidationResult(
            is_valid=True,
            risk_level=RiskLevel.LOW,
            sanitized_params=params
        )
    
    def _validate_system_info(self, intent: IntentResult) -> ValidationResult:
        """Validate system info queries - always safe"""
        return ValidationResult(
            is_valid=True,
            risk_level=RiskLevel.SAFE,
            sanitized_params=intent.parameters
        )
    
    def _is_protected_path(self, path: str) -> bool:
        """
        Check whether *path* is (or falls under) a protected system directory.

        A naive `str.startswith` check against protected paths that include
        bare "/" would match every absolute path, since "/" is a prefix of
        all of them — that previously blocked all real file operations, not
        just ones touching system directories. This normalizes the path and
        requires an exact match or a real subdirectory relationship instead.
        """
        if not path:
            return False

        normalized = os.path.normpath(os.path.expanduser(path))

        for protected in self.protected_paths:
            protected_norm = os.path.normpath(protected)
            if protected_norm == "/":
                if normalized == "/":
                    return True
                continue
            if normalized == protected_norm or normalized.startswith(protected_norm + os.sep):
                return True

        return False

    # Sanitization methods

    def _sanitize_paths(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize file paths to prevent injection"""
        sanitized = params.copy()
        
        for key in ["source", "destination", "target", "path", "location"]:
            if key in sanitized and isinstance(sanitized[key], str):
                # Remove dangerous characters
                path = sanitized[key]
                path = path.replace(";", "")
                path = path.replace("|", "")
                path = path.replace("&", "")
                path = path.replace("$", "")
                path = path.replace("`", "")
                sanitized[key] = path
        
        return sanitized
    
    def _sanitize_command(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize command parameters"""
        sanitized = params.copy()
        
        if "program" in sanitized:
            program = sanitized["program"]
            # Remove shell metacharacters
            program = re.sub(r'[;&|`$]', '', program)
            sanitized["program"] = program
        
        return sanitized
    
    def _sanitize_package_name(self, package: str) -> str:
        """Sanitize package name"""
        # Only allow alphanumeric, dash, underscore
        return re.sub(r'[^a-zA-Z0-9\-_.]', '', package)
    
    def _is_valid_package_name(self, package: str) -> bool:
        """Check if package name is valid"""
        # Must be alphanumeric with dash/underscore
        return bool(re.match(r'^[a-zA-Z0-9\-_.]+$', package))
    
    def add_protected_path(self, path: str) -> None:
        """Add a path to the protected list"""
        self.protected_paths.add(path)
        logger.debug(f"Added protected path: {path}")
    
    def remove_protected_path(self, path: str) -> None:
        """Remove a path from the protected list"""
        if path in self.protected_paths:
            self.protected_paths.remove(path)
            logger.debug(f"Removed protected path: {path}")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    from minikernel.intent.intent_parser import IntentParser
    
    parser = IntentParser()
    validator = CommandValidator()
    
    test_commands = [
        "delete /etc/passwd",  # Should block
        "delete my_file.txt",  # Should confirm
        "list all files",      # Safe
        "install vim",         # Should confirm
        "kill init",           # Should block
    ]
    
    for cmd in test_commands:
        intent = parser.parse(cmd)
        validation = validator.validate(intent)
        
        print(f"\n'{cmd}'")
        print(f"  Valid: {validation.is_valid}")
        print(f"  Risk: {validation.risk_level.value}")
        print(f"  Confirm: {validation.requires_confirmation}")
        if validation.errors:
            print(f"  Errors: {validation.errors}")
        if validation.confirmation_prompt:
            print(f"  Prompt: {validation.confirmation_prompt}")
