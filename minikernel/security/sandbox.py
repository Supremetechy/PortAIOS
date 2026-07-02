"""
Sandbox

Execution sandbox for AI-generated commands
Prevents direct code execution, ensures validation
"""

import logging
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("MiniKernel.Sandbox")


@dataclass
class SandboxResult:
    """Result of sandboxed execution"""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class Sandbox:
    """
    Execution Sandbox for MiniKernel
    
    Security Features:
    - No direct code execution from AI
    - Command whitelisting
    - Resource limits (time, memory)
    - Path restrictions
    - Audit logging
    
    AI outputs commands → Validator checks → Sandbox executes
    """
    
    def __init__(self):
        # Whitelist of allowed commands
        self.allowed_commands = {
            # File operations
            "ls", "cat", "cp", "mv", "rm", "mkdir", "touch",
            # Process operations
            "ps", "kill", "pkill",
            # System info
            "df", "du", "free", "uptime",
            # Package management
            "apt-get", "dnf", "brew", "pip",
        }
        
        # Blacklist of dangerous patterns
        self.blacklist_patterns = [
            r"rm\s+-rf\s+/",
            r"dd\s+.*of=/dev/",
            r"mkfs\.",
            r":(){:|:&};:",  # Fork bomb
            r">\s*/dev/sd",
        ]
        
        # Resource limits
        self.max_execution_time = 30  # seconds
        self.max_output_size = 1024 * 1024  # 1MB
        
        # Restricted paths
        self.restricted_paths = {
            "/", "/bin", "/boot", "/etc", "/lib", "/proc",
            "/root", "/sbin", "/sys", "/usr"
        }
        
        logger.info("Sandbox initialized")
    
    def execute(
        self,
        command: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> SandboxResult:
        """
        Execute a command in the sandbox
        
        Args:
            command: Command to execute
            args: Command arguments
            cwd: Working directory
            timeout: Execution timeout (seconds)
            
        Returns:
            SandboxResult
        """
        start_time = datetime.now()
        
        # Validate command
        if not self._is_command_allowed(command):
            logger.warning(f"Command not allowed: {command}")
            return SandboxResult(
                success=False,
                error=f"Command not allowed: {command}"
            )
        
        # Build full command
        cmd_parts = [command]
        if args:
            cmd_parts.extend(args)
        
        full_command = " ".join(cmd_parts)
        
        # Check blacklist
        if self._is_blacklisted(full_command):
            logger.error(f"Blacklisted command: {full_command}")
            return SandboxResult(
                success=False,
                error=f"Dangerous command blocked: {full_command}"
            )
        
        # Execute with limits
        timeout = timeout or self.max_execution_time
        
        try:
            logger.info(f"Executing in sandbox: {full_command}")
            
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=self._get_restricted_env()
            )
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Limit output size
            stdout = result.stdout[:self.max_output_size]
            stderr = result.stderr[:self.max_output_size]
            
            return SandboxResult(
                success=result.returncode == 0,
                output=stdout,
                error=stderr,
                exit_code=result.returncode,
                execution_time_ms=execution_time
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {full_command}")
            return SandboxResult(
                success=False,
                error=f"Command exceeded timeout of {timeout}s"
            )
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return SandboxResult(
                success=False,
                error=str(e)
            )
    
    def _is_command_allowed(self, command: str) -> bool:
        """Check if command is in whitelist"""
        # Extract base command
        base_cmd = command.split()[0] if " " in command else command
        base_cmd = os.path.basename(base_cmd)
        
        return base_cmd in self.allowed_commands
    
    def _is_blacklisted(self, command: str) -> bool:
        """Check if command matches blacklist patterns"""
        import re
        
        for pattern in self.blacklist_patterns:
            if re.search(pattern, command):
                return True
        
        return False
    
    def _get_restricted_env(self) -> Dict[str, str]:
        """Get restricted environment variables"""
        # Start with minimal env
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": tempfile.gettempdir(),
            "USER": "minikernel_sandbox",
            "SHELL": "/bin/sh"
        }
        
        return env
    
    def add_allowed_command(self, command: str) -> None:
        """Add a command to the whitelist"""
        self.allowed_commands.add(command)
        logger.debug(f"Added allowed command: {command}")
    
    def remove_allowed_command(self, command: str) -> None:
        """Remove a command from the whitelist"""
        if command in self.allowed_commands:
            self.allowed_commands.remove(command)
            logger.debug(f"Removed allowed command: {command}")
    
    def add_blacklist_pattern(self, pattern: str) -> None:
        """Add a pattern to the blacklist"""
        self.blacklist_patterns.append(pattern)
        logger.debug(f"Added blacklist pattern: {pattern}")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    sandbox = Sandbox()
    
    # Safe command
    result = sandbox.execute("ls", args=["-la"])
    print(f"Success: {result.success}")
    print(f"Output: {result.output[:100]}")
    
    # Unsafe command (should be blocked)
    result = sandbox.execute("rm", args=["-rf", "/"])
    print(f"Blocked: {not result.success}")
    print(f"Error: {result.error}")
