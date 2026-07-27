"""
Process Service

Voice-controlled process management
Wraps kernel scheduler with high-level operations
"""

import logging
import psutil
import signal
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("MiniKernel.Process")


@dataclass
class ProcessInfo:
    """Process information"""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_mb: float
    created_time: datetime
    cmdline: List[str]
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_time).total_seconds()


class ProcessService:
    """
    Process Service for MiniKernel
    
    Capabilities:
    - List running processes
    - Start/stop processes
    - Monitor resource usage
    - Voice-friendly process control
    
    Uses psutil for cross-platform process management
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        
        # Process name aliases for voice commands
        self.aliases = {
            "chrome": ["chrome", "chromium", "google-chrome"],
            "firefox": ["firefox", "firefox-esr"],
            "terminal": ["terminal", "gnome-terminal", "konsole", "xterm"],
            "editor": ["code", "vim", "emacs", "nano", "gedit"]
        }

        # Voice-friendly priority levels mapped to OS nice values.
        # Negative (higher-priority) values typically require elevated
        # privileges and will fail with AccessDenied on most systems.
        self._nice_levels = {"low": 10, "normal": 0, "high": -10}

        logger.info("Process Service created")
    
    def initialize(self) -> None:
        """Initialize process service"""
        logger.info("Process Service initialized")
    
    def shutdown(self) -> None:
        """Shutdown process service"""
        logger.info("Process Service shutdown")
    
    def list_processes(
        self,
        name_filter: Optional[str] = None,
        sort_by: str = "cpu"
    ) -> List[ProcessInfo]:
        """
        List running processes
        
        Args:
            name_filter: Filter by process name
            sort_by: Sort by 'cpu', 'memory', or 'name'
            
        Returns:
            List of ProcessInfo
        """
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 
                                         'memory_info', 'create_time', 'cmdline']):
            try:
                info = proc.info
                
                # Apply filter
                if name_filter:
                    if name_filter.lower() not in info['name'].lower():
                        continue
                
                # Create ProcessInfo
                memory_mb = info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0
                
                proc_info = ProcessInfo(
                    pid=info['pid'],
                    name=info['name'],
                    status=info['status'],
                    cpu_percent=info['cpu_percent'] or 0.0,
                    memory_mb=memory_mb,
                    created_time=datetime.fromtimestamp(info['create_time']),
                    cmdline=info['cmdline'] or []
                )
                
                processes.append(proc_info)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort
        if sort_by == "cpu":
            processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        elif sort_by == "memory":
            processes.sort(key=lambda p: p.memory_mb, reverse=True)
        elif sort_by == "name":
            processes.sort(key=lambda p: p.name)
        
        logger.debug(f"Listed {len(processes)} processes")
        return processes
    
    def find_process(self, name: str) -> Optional[ProcessInfo]:
        """
        Find a process by name (supports aliases)
        
        Args:
            name: Process name or alias
            
        Returns:
            ProcessInfo or None
        """
        # Check aliases
        search_names = self.aliases.get(name.lower(), [name])
        
        for search_name in search_names:
            processes = self.list_processes(name_filter=search_name)
            if processes:
                return processes[0]  # Return first match
        
        return None
    
    def kill_process(self, name: str, force: bool = False) -> bool:
        """
        Kill a process by name
        
        Args:
            name: Process name or alias
            force: Use SIGKILL instead of SIGTERM
            
        Returns:
            True if successful
        """
        proc_info = self.find_process(name)
        
        if not proc_info:
            logger.warning(f"Process not found: {name}")
            return False
        
        try:
            process = psutil.Process(proc_info.pid)
            
            if force:
                process.kill()  # SIGKILL
                logger.info(f"Force killed: {name} (pid={proc_info.pid})")
            else:
                process.terminate()  # SIGTERM
                logger.info(f"Terminated: {name} (pid={proc_info.pid})")
            
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Failed to kill {name}: {e}")
            return False
    
    def start_process(self, command: str, args: Optional[List[str]] = None) -> Optional[int]:
        """
        Start a new process
        
        Args:
            command: Command to execute
            args: Command arguments
            
        Returns:
            PID if successful, None otherwise
        """
        import subprocess
        
        try:
            cmd = [command]
            if args:
                cmd.extend(args)
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            logger.info(f"Started: {command} (pid={process.pid})")
            return process.pid
            
        except Exception as e:
            logger.error(f"Failed to start {command}: {e}")
            return None
    
    def set_priority(self, name: str, priority: str = "normal") -> bool:
        """
        Set a process's scheduling priority via OS nice value

        Args:
            name: Process name or alias
            priority: 'low', 'normal', or 'high'

        Returns:
            True if successful
        """
        proc_info = self.find_process(name)

        if not proc_info:
            logger.warning(f"Process not found: {name}")
            return False

        nice_value = self._nice_levels.get(priority, 0)

        try:
            process = psutil.Process(proc_info.pid)
            process.nice(nice_value)
            logger.info(f"Set priority of '{name}' (pid={proc_info.pid}) to {priority} (nice={nice_value})")
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as e:
            logger.error(f"Failed to set priority for {name}: {e}")
            return False

    def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """Get detailed info about a specific process"""
        try:
            proc = psutil.Process(pid)
            
            return ProcessInfo(
                pid=proc.pid,
                name=proc.name(),
                status=proc.status(),
                cpu_percent=proc.cpu_percent(),
                memory_mb=proc.memory_info().rss / (1024 * 1024),
                created_time=datetime.fromtimestamp(proc.create_time()),
                cmdline=proc.cmdline()
            )
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system process statistics"""
        all_processes = self.list_processes()
        
        return {
            "total_processes": len(all_processes),
            "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
            "memory_usage_percent": psutil.virtual_memory().percent,
            "top_cpu": all_processes[:5] if all_processes else [],
            "top_memory": sorted(all_processes, key=lambda p: p.memory_mb, reverse=True)[:5]
        }
    
    def add_alias(self, alias: str, process_names: List[str]) -> None:
        """Add a process name alias"""
        self.aliases[alias.lower()] = process_names
        logger.debug(f"Added alias: {alias} → {process_names}")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    ps = ProcessService()
    ps.initialize()
    
    # List all processes
    processes = ps.list_processes()
    print(f"Total processes: {len(processes)}")
    
    # Top CPU consumers
    print("\nTop CPU consumers:")
    for proc in processes[:5]:
        print(f"  {proc.name}: {proc.cpu_percent:.1f}%")
    
    # System stats
    stats = ps.get_system_stats()
    print(f"\nCPU: {stats['cpu_usage_percent']:.1f}%")
    print(f"Memory: {stats['memory_usage_percent']:.1f}%")
    
    ps.shutdown()
