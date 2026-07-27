"""
Execution Engine

Executes validated intents by translating them to system calls
Final step in the Intent → Kernel pipeline
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import psutil

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
        time_filter = params.get("time_filter")

        modified_since = None
        if time_filter and "days_ago" in time_filter:
            modified_since = datetime.now() - timedelta(days=time_filter["days_ago"])

        try:
            entries = fs_service.search(query, modified_since=modified_since)
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))

        results = [
            {
                "path": entry.path,
                "name": entry.name,
                "size_bytes": entry.size_bytes,
                "modified_time": entry.modified_time.isoformat(),
            }
            for entry in entries
        ]

        return ExecutionResult(
            success=True,
            output={
                "query": query,
                "results": results,
                "count": len(results),
                "message": f"Found {len(results)} file(s) matching '{query}'",
            }
        )

    def _file_move(self, params: Dict[str, Any]) -> ExecutionResult:
        """Move files"""
        source = params.get("source", "")
        dest = params.get("destination", "")

        if not source or not dest:
            return ExecutionResult(success=False, error="Missing source or destination")

        try:
            src_path = Path(source).expanduser()
            if not src_path.exists():
                return ExecutionResult(success=False, error=f"Source not found: {src_path}")
            dest_path = Path(dest).expanduser()
            shutil.move(str(src_path), str(dest_path))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))

        return ExecutionResult(
            success=True,
            output={"message": f"Moved '{src_path}' to '{dest_path}'"}
        )

    def _file_copy(self, params: Dict[str, Any]) -> ExecutionResult:
        """Copy files"""
        source = params.get("source", "")
        dest = params.get("destination", "")

        if not source or not dest:
            return ExecutionResult(success=False, error="Missing source or destination")

        try:
            src_path = Path(source).expanduser()
            if not src_path.exists():
                return ExecutionResult(success=False, error=f"Source not found: {src_path}")
            dest_path = Path(dest).expanduser()
            if src_path.is_dir():
                shutil.copytree(str(src_path), str(dest_path), dirs_exist_ok=True)
            else:
                shutil.copy2(str(src_path), str(dest_path))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))

        return ExecutionResult(
            success=True,
            output={"message": f"Copied '{src_path}' to '{dest_path}'"}
        )

    def _file_delete(self, params: Dict[str, Any]) -> ExecutionResult:
        """Delete files"""
        target = params.get("target", "")

        if not target:
            return ExecutionResult(success=False, error="No target specified")

        try:
            target_path = Path(target).expanduser()
            if not target_path.exists():
                return ExecutionResult(success=False, error=f"Target not found: {target_path}")
            if target_path.is_dir():
                shutil.rmtree(str(target_path))
            else:
                target_path.unlink()
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))

        return ExecutionResult(
            success=True,
            output={"message": f"Deleted '{target_path}'"}
        )

    def _file_list(self, params: Dict[str, Any]) -> ExecutionResult:
        """List files"""
        path = params.get("path") or "."
        recursive = params.get("recursive", False)

        try:
            base_path = Path(path).expanduser()
            if not base_path.exists():
                return ExecutionResult(success=False, error=f"Path not found: {base_path}")
            if not base_path.is_dir():
                return ExecutionResult(success=False, error=f"Not a directory: {base_path}")

            if recursive:
                files = sorted(str(p.relative_to(base_path)) for p in base_path.rglob("*"))
            else:
                files = sorted(p.name for p in base_path.iterdir())
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))

        return ExecutionResult(
            success=True,
            output={
                "path": str(base_path),
                "files": files,
                "message": f"Listing {len(files)} entries in {base_path}",
            }
        )
    
    # Process control implementations
    
    def _process_start(self, params: Dict[str, Any]) -> ExecutionResult:
        """Start a process"""
        program = params.get("program", "")
        args = params.get("args") or []

        if not program:
            return ExecutionResult(success=False, error="No program specified")
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")

        proc_service = self.kernel.get_service("process")
        if not proc_service:
            return ExecutionResult(success=False, error="Process service not available")

        try:
            pid = proc_service.start_process(program, args)
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))

        if pid is None:
            return ExecutionResult(
                success=False,
                error=f"Failed to start '{program}': no such file or directory: '{program}'"
            )

        return ExecutionResult(
            success=True,
            output={"pid": pid, "message": f"Started '{program}' (pid={pid})"}
        )

    def _process_stop(self, params: Dict[str, Any]) -> ExecutionResult:
        """Stop a process"""
        process = params.get("process", "")
        force = params.get("force", False)

        if not process:
            return ExecutionResult(success=False, error="No process specified")
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")

        proc_service = self.kernel.get_service("process")
        if not proc_service:
            return ExecutionResult(success=False, error="Process service not available")

        if not proc_service.kill_process(process, force=force):
            return ExecutionResult(success=False, error=f"Process not found or could not be stopped: {process}")

        return ExecutionResult(
            success=True,
            output={"message": f"Stopped '{process}' (force={force})"}
        )

    def _process_list(self, params: Dict[str, Any]) -> ExecutionResult:
        """List processes"""
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")

        proc_service = self.kernel.get_service("process")
        if not proc_service:
            return ExecutionResult(success=False, error="Process service not available")

        name_filter = params.get("filter")
        processes = proc_service.list_processes(name_filter=name_filter)

        output_processes = [
            {
                "pid": p.pid,
                "name": p.name,
                "status": p.status,
                "cpu_percent": p.cpu_percent,
                "memory_mb": round(p.memory_mb, 1),
            }
            for p in processes
        ]

        return ExecutionResult(
            success=True,
            output={
                "processes": output_processes,
                "count": len(output_processes)
            }
        )

    def _process_priority(self, params: Dict[str, Any]) -> ExecutionResult:
        """Change process priority"""
        process = params.get("process", "")
        priority = params.get("priority", "normal")

        if not process:
            return ExecutionResult(success=False, error="No process specified")
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")

        proc_service = self.kernel.get_service("process")
        if not proc_service:
            return ExecutionResult(success=False, error="Process service not available")

        if not proc_service.set_priority(process, priority):
            return ExecutionResult(
                success=False,
                error=f"Could not set priority for '{process}' (permission denied or process not found)"
            )

        return ExecutionResult(
            success=True,
            output={"message": f"Set '{process}' priority to {priority}"}
        )
    
    # System info implementations
    
    def _get_memory_info(self) -> ExecutionResult:
        """Get memory information"""
        vm = psutil.virtual_memory()
        usage = {
            "total_mb": round(vm.total / (1024 * 1024), 1),
            "used_mb": round((vm.total - vm.available) / (1024 * 1024), 1),
            "free_mb": round(vm.available / (1024 * 1024), 1),
            "usage_percent": vm.percent,
        }

        return ExecutionResult(
            success=True,
            output=usage
        )
    
    def _get_disk_info(self) -> ExecutionResult:
        """Get disk information"""
        usage = shutil.disk_usage("/")
        return ExecutionResult(
            success=True,
            output={
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "usage_percent": round(usage.used / usage.total * 100, 1),
            }
        )

    def _get_cpu_info(self) -> ExecutionResult:
        """Get CPU information"""
        load_avg = list(os.getloadavg()) if hasattr(os, "getloadavg") else None
        return ExecutionResult(
            success=True,
            output={
                "cores": psutil.cpu_count(logical=True),
                "usage_percent": psutil.cpu_percent(interval=0.1),
                "load_avg": load_avg,
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

        if not package:
            return ExecutionResult(success=False, error="No package specified")
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")

        pkg_service = self.kernel.get_service("package")
        if not pkg_service:
            return ExecutionResult(success=False, error="Package service not available")

        if not pkg_service.install(package):
            return ExecutionResult(success=False, error=f"Failed to install package '{package}'")

        return ExecutionResult(
            success=True,
            output={"message": f"Installed package '{package}'"}
        )

    def _package_uninstall(self, params: Dict[str, Any]) -> ExecutionResult:
        """Uninstall a package"""
        package = params.get("package", "")

        if not package:
            return ExecutionResult(success=False, error="No package specified")
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")

        pkg_service = self.kernel.get_service("package")
        if not pkg_service:
            return ExecutionResult(success=False, error="Package service not available")

        if not pkg_service.uninstall(package):
            return ExecutionResult(success=False, error=f"Failed to uninstall package '{package}'")

        return ExecutionResult(
            success=True,
            output={"message": f"Uninstalled package '{package}'"}
        )

    def _package_update_all(self, params: Dict[str, Any]) -> ExecutionResult:
        """Update all packages"""
        if not self.kernel:
            return ExecutionResult(success=False, error="Kernel not available")

        pkg_service = self.kernel.get_service("package")
        if not pkg_service:
            return ExecutionResult(success=False, error="Package service not available")

        if not pkg_service.update_all():
            return ExecutionResult(success=False, error="Failed to update packages")

        return ExecutionResult(
            success=True,
            output={"message": "Updated all packages"}
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
