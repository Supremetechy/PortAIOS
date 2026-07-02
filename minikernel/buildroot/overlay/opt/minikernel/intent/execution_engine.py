"""
Execution Engine

Executes validated intents by translating them to system calls
Final step in the Intent → Kernel pipeline
"""

import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from minikernel.intent.intent_parser import IntentResult, IntentType
from minikernel.intent.command_validator import ValidationResult

logger = logging.getLogger("MiniKernel.Executor")


@dataclass
class ExecutionResult:
    """Result of command execution"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ExecutionEngine:
    """
    Execution Engine - IR → System Calls
    
    Translates validated intent into actual kernel operations
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel  # Reference to MicroKernel
        
        # Handler registry for different intent types
        self.handlers: Dict[IntentType, Callable] = {
            IntentType.FILE_OPERATION: self._handle_file_operation,
            IntentType.PROCESS_CONTROL: self._handle_process_control,
            IntentType.SYSTEM_INFO: self._handle_system_info,
            IntentType.PACKAGE_MANAGEMENT: self._handle_package_management,
        }
        
        self.stats = {
            "commands_executed": 0,
            "commands_failed": 0,
            "total_execution_time_ms": 0.0
        }
        
        logger.info("Execution Engine initialized")
    
    def execute(
        self,
        intent: IntentResult,
        validation: ValidationResult,
        confirmed: bool = False
    ) -> ExecutionResult:
        """
        Execute a validated intent
        
        Args:
            intent: Parsed intent
            validation: Validation result
            confirmed: Whether user confirmed (for risky operations)
            
        Returns:
            ExecutionResult
        """
        start_time = datetime.now()
        
        # Check if valid
        if not validation.is_valid:
            logger.warning(f"Attempted to execute invalid command: {intent.action}")
            return ExecutionResult(
                success=False,
                error="Command validation failed: " + ", ".join(validation.errors)
            )
        
        # Check if confirmation required but not provided
        if validation.requires_confirmation and not confirmed:
            logger.info(f"Command requires confirmation: {intent.action}")
            return ExecutionResult(
                success=False,
                error="Confirmation required",
                output={"confirmation_prompt": validation.confirmation_prompt}
            )
        
        # Route to appropriate handler
        handler = self.handlers.get(intent.intent_type)
        if not handler:
            logger.error(f"No handler for intent type: {intent.intent_type.value}")
            return ExecutionResult(
                success=False,
                error=f"Unsupported intent type: {intent.intent_type.value}"
            )
        
        try:
            # Execute
            result = handler(intent, validation.sanitized_params)
            
            # Update stats
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.stats["commands_executed"] += 1
            self.stats["total_execution_time_ms"] += execution_time
            
            result.execution_time_ms = execution_time
            
            logger.info(f"Executed: {intent.action} ({execution_time:.2f}ms)")
            return result
            
        except Exception as e:
            self.stats["commands_failed"] += 1
            logger.error(f"Execution failed: {intent.action} - {e}")
            return ExecutionResult(
                success=False,
                error=str(e)
            )
    
    def _handle_file_operation(self, intent: IntentResult, params: Dict[str, Any]) -> ExecutionResult:
        """Handle file operations"""
        action = intent.action
        
        if action == "find":
            return self._file_find(params)
        elif action == "move":
            return self._file_move(params)
        elif action == "copy":
            return self._file_copy(params)
        elif action == "delete":
            return self._file_delete(params)
        elif action == "list":
            return self._file_list(params)
        else:
            return ExecutionResult(
                success=False,
                error=f"Unknown file action: {action}"
            )
    
    def _handle_process_control(self, intent: IntentResult, params: Dict[str, Any]) -> ExecutionResult:
        """Handle process control"""
        action = intent.action
        
        if action == "start":
            return self._process_start(params)
        elif action == "stop":
            return self._process_stop(params)
        elif action == "list":
            return self._process_list(params)
        elif action == "priority":
            return self._process_priority(params)
        else:
            return ExecutionResult(
                success=False,
                error=f"Unknown process action: {action}"
            )
    
    def _handle_system_info(self, intent: IntentResult, params: Dict[str, Any]) -> ExecutionResult:
        """Handle system info queries"""
        action = intent.action
        
        if action == "memory_info":
            return self._get_memory_info()
        elif action == "disk_info":
            return self._get_disk_info()
        elif action == "cpu_info":
            return self._get_cpu_info()
        elif action == "system_status":
            return self._get_system_status()
        else:
            return ExecutionResult(
                success=False,
                error=f"Unknown system info query: {action}"
            )
    
    def _handle_package_management(self, intent: IntentResult, params: Dict[str, Any]) -> ExecutionResult:
        """Handle package management"""
        action = intent.action
        
        if action == "install":
            return self._package_install(params)
        elif action == "uninstall":
            return self._package_uninstall(params)
        elif action == "update_all":
            return self._package_update_all(params)
        else:
            return ExecutionResult(
                success=False,
                error=f"Unknown package action: {action}"
            )
    
    # File operation implementations
    
    def _file_find(self, params: Dict[str, Any]) -> ExecutionResult:
        """Find files"""
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")
        
        # Get filesystem service
        fs_service = self.kernel.get_service("filesystem")
        if not fs_service:
            return ExecutionResult(success=False, error="Filesystem service not available")
        
        query = params.get("query", "")
        location = params.get("location", "/")
        time_filter = params.get("time_filter")
        
        # Would call filesystem service to search
        # For now, return placeholder
        return ExecutionResult(
            success=True,
            output={
                "query": query,
                "location": location,
                "results": [],  # Would contain actual search results
                "message": f"Searching for '{query}' in {location}..."
            }
        )
    
    def _file_move(self, params: Dict[str, Any]) -> ExecutionResult:
        """Move files"""
        source = params.get("source", "")
        dest = params.get("destination", "")
        
        return ExecutionResult(
            success=True,
            output={"message": f"Would move '{source}' to '{dest}'"}
        )
    
    def _file_copy(self, params: Dict[str, Any]) -> ExecutionResult:
        """Copy files"""
        source = params.get("source", "")
        dest = params.get("destination", "")
        
        return ExecutionResult(
            success=True,
            output={"message": f"Would copy '{source}' to '{dest}'"}
        )
    
    def _file_delete(self, params: Dict[str, Any]) -> ExecutionResult:
        """Delete files"""
        target = params.get("target", "")
        
        return ExecutionResult(
            success=True,
            output={"message": f"Would delete '{target}'"}
        )
    
    def _file_list(self, params: Dict[str, Any]) -> ExecutionResult:
        """List files"""
        path = params.get("path", ".")
        recursive = params.get("recursive", False)
        
        return ExecutionResult(
            success=True,
            output={
                "path": path,
                "files": [],  # Would contain actual file list
                "message": f"Listing files in {path}..."
            }
        )
    
    # Process control implementations
    
    def _process_start(self, params: Dict[str, Any]) -> ExecutionResult:
        """Start a process"""
        program = params.get("program", "")
        
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")
        
        scheduler = self.kernel.get_service("scheduler")
        if not scheduler:
            return ExecutionResult(success=False, error="Scheduler not available")
        
        # Would create and start process via scheduler
        return ExecutionResult(
            success=True,
            output={"message": f"Would start '{program}'"}
        )
    
    def _process_stop(self, params: Dict[str, Any]) -> ExecutionResult:
        """Stop a process"""
        process = params.get("process", "")
        force = params.get("force", False)
        
        return ExecutionResult(
            success=True,
            output={"message": f"Would stop '{process}' (force={force})"}
        )
    
    def _process_list(self, params: Dict[str, Any]) -> ExecutionResult:
        """List processes"""
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")
        
        scheduler = self.kernel.get_service("scheduler")
        if not scheduler:
            return ExecutionResult(success=False, error="Scheduler not available")
        
        # Get process list from scheduler
        processes = []  # Would get from scheduler.list_processes()
        
        return ExecutionResult(
            success=True,
            output={
                "processes": processes,
                "count": len(processes)
            }
        )
    
    def _process_priority(self, params: Dict[str, Any]) -> ExecutionResult:
        """Change process priority"""
        process = params.get("process", "")
        priority = params.get("priority", "normal")
        
        return ExecutionResult(
            success=True,
            output={"message": f"Would set '{process}' priority to {priority}"}
        )
    
    # System info implementations
    
    def _get_memory_info(self) -> ExecutionResult:
        """Get memory information"""
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")
        
        mem_service = self.kernel.get_service("memory")
        if not mem_service:
            return ExecutionResult(success=False, error="Memory service not available")
        
        usage = mem_service.get_system_usage()
        
        return ExecutionResult(
            success=True,
            output=usage
        )
    
    def _get_disk_info(self) -> ExecutionResult:
        """Get disk information"""
        return ExecutionResult(
            success=True,
            output={
                "total_gb": 500,
                "used_gb": 250,
                "free_gb": 250,
                "usage_percent": 50.0
            }
        )
    
    def _get_cpu_info(self) -> ExecutionResult:
        """Get CPU information"""
        return ExecutionResult(
            success=True,
            output={
                "cores": 8,
                "usage_percent": 25.5,
                "load_avg": [1.2, 1.5, 1.8]
            }
        )
    
    def _get_system_status(self) -> ExecutionResult:
        """Get overall system status"""
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")
        
        stats = self.kernel.get_stats()
        
        return ExecutionResult(
            success=True,
            output=stats
        )
    
    # Package management implementations
    
    def _package_install(self, params: Dict[str, Any]) -> ExecutionResult:
        """Install a package"""
        package = params.get("package", "")
        
        return ExecutionResult(
            success=True,
            output={"message": f"Would install package '{package}'"}
        )
    
    def _package_uninstall(self, params: Dict[str, Any]) -> ExecutionResult:
        """Uninstall a package"""
        package = params.get("package", "")
        
        return ExecutionResult(
            success=True,
            output={"message": f"Would uninstall package '{package}'"}
        )
    
    def _package_update_all(self, params: Dict[str, Any]) -> ExecutionResult:
        """Update all packages"""
        return ExecutionResult(
            success=True,
            output={"message": "Would update all packages"}
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self.stats.copy()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    from minikernel.intent.intent_parser import IntentParser
    from minikernel.intent.command_validator import CommandValidator
    
    parser = IntentParser()
    validator = CommandValidator()
    executor = ExecutionEngine()
    
    # Simulate command execution
    cmd = "list all files"
    
    intent = parser.parse(cmd)
    validation = validator.validate(intent)
    
    if validation.is_valid:
        result = executor.execute(intent, validation, confirmed=True)
        print(f"Success: {result.success}")
        print(f"Output: {result.output}")
