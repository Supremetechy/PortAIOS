"""
Process Scheduler

Manages process lifecycle and CPU time allocation
Implements simple priority-based scheduling
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger("MiniKernel.Scheduler")


class ProcessState(Enum):
    """Process states"""
    NEW = "new"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


class ProcessPriority(Enum):
    """Process priority levels"""
    REALTIME = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    IDLE = 4


@dataclass
class Process:
    """Represents a process"""
    pid: str
    name: str
    priority: ProcessPriority
    state: ProcessState = ProcessState.NEW
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    cpu_time_seconds: float = 0.0
    memory_blocks: List[str] = field(default_factory=list)
    parent_pid: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # For execution
    target: Optional[Callable] = None
    thread: Optional[threading.Thread] = None
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def runtime_seconds(self) -> float:
        if self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return 0.0


class ProcessScheduler:
    """
    Process Scheduler for MiniKernel
    
    Implements:
    - Process creation/termination
    - Priority-based scheduling
    - Process state management
    - Basic round-robin within priority levels
    """
    
    def __init__(self, time_slice_ms: int = 100):
        self.processes: Dict[str, Process] = {}
        self.ready_queue: List[str] = []
        self.time_slice_seconds = time_slice_ms / 1000.0
        
        self._lock = threading.RLock()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._running = False
        self._next_pid = 0
        
        self.stats = {
            "processes_created": 0,
            "processes_terminated": 0,
            "context_switches": 0,
            "total_cpu_time": 0.0
        }
        
        logger.info(f"Process Scheduler created (time_slice={time_slice_ms}ms)")
    
    def initialize(self) -> None:
        """Initialize scheduler"""
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self._scheduler_thread.start()
        logger.info("Process Scheduler initialized")
    
    def shutdown(self) -> None:
        """Shutdown scheduler"""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=2.0)
        
        # Terminate all processes
        with self._lock:
            for pid in list(self.processes.keys()):
                self.proc_terminate(pid)
        
        logger.info("Process Scheduler shutdown")
    
    def proc_create(
        self,
        name: str,
        target: Optional[Callable] = None,
        priority: ProcessPriority = ProcessPriority.NORMAL,
        parent_pid: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a new process
        
        Returns: PID if successful
        """
        with self._lock:
            pid = f"proc_{self._next_pid}"
            self._next_pid += 1
            
            process = Process(
                pid=pid,
                name=name,
                priority=priority,
                target=target,
                parent_pid=parent_pid,
                metadata=metadata or {}
            )
            
            self.processes[pid] = process
            self.stats["processes_created"] += 1
            
            logger.info(f"Created process: {name} (pid={pid}, priority={priority.name})")
            return pid
    
    def proc_start(self, pid: str) -> bool:
        """
        Start a process (move to ready queue)
        
        Returns: True if successful
        """
        with self._lock:
            if pid not in self.processes:
                return False
            
            process = self.processes[pid]
            
            if process.state != ProcessState.NEW:
                logger.warning(f"Process {pid} already started")
                return False
            
            process.state = ProcessState.READY
            process.started_at = datetime.now()
            self.ready_queue.append(pid)
            
            logger.debug(f"Started process: {pid}")
            return True
    
    def proc_terminate(self, pid: str) -> bool:
        """
        Terminate a process
        
        Returns: True if successful
        """
        with self._lock:
            if pid not in self.processes:
                return False
            
            process = self.processes[pid]
            process.state = ProcessState.TERMINATED
            
            # Remove from ready queue
            if pid in self.ready_queue:
                self.ready_queue.remove(pid)
            
            # Stop thread if running
            if process.thread and process.thread.is_alive():
                # Note: Python doesn't support forced thread termination
                # Process should check a flag and exit gracefully
                pass
            
            self.stats["processes_terminated"] += 1
            logger.info(f"Terminated process: {pid}")
            
            # Clean up after some time
            # (In real OS, would reclaim resources immediately)
            
            return True
    
    def proc_block(self, pid: str) -> bool:
        """Block a process (waiting for I/O, etc.)"""
        with self._lock:
            if pid not in self.processes:
                return False
            
            process = self.processes[pid]
            if process.state == ProcessState.RUNNING:
                process.state = ProcessState.BLOCKED
                if pid in self.ready_queue:
                    self.ready_queue.remove(pid)
                logger.debug(f"Blocked process: {pid}")
                return True
            
            return False
    
    def proc_unblock(self, pid: str) -> bool:
        """Unblock a process (make it ready)"""
        with self._lock:
            if pid not in self.processes:
                return False
            
            process = self.processes[pid]
            if process.state == ProcessState.BLOCKED:
                process.state = ProcessState.READY
                self.ready_queue.append(pid)
                logger.debug(f"Unblocked process: {pid}")
                return True
            
            return False
    
    def proc_set_priority(self, pid: str, priority: ProcessPriority) -> bool:
        """Change process priority"""
        with self._lock:
            if pid not in self.processes:
                return False
            
            old_priority = self.processes[pid].priority
            self.processes[pid].priority = priority
            
            # Re-sort ready queue
            self._sort_ready_queue()
            
            logger.debug(f"Changed priority: {pid} {old_priority.name} → {priority.name}")
            return True
    
    def get_process(self, pid: str) -> Optional[Process]:
        """Get process info"""
        return self.processes.get(pid)
    
    def list_processes(self, state: Optional[ProcessState] = None) -> List[Process]:
        """List all processes, optionally filtered by state"""
        with self._lock:
            if state:
                return [p for p in self.processes.values() if p.state == state]
            return list(self.processes.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        with self._lock:
            return {
                "processes_total": len(self.processes),
                "processes_running": len([p for p in self.processes.values() 
                                        if p.state == ProcessState.RUNNING]),
                "processes_ready": len(self.ready_queue),
                "processes_blocked": len([p for p in self.processes.values() 
                                         if p.state == ProcessState.BLOCKED]),
                **self.stats
            }
    
    def _schedule_loop(self) -> None:
        """Main scheduler loop (runs in background thread)"""
        logger.debug("Scheduler loop started")
        
        while self._running:
            try:
                self._schedule_tick()
                time.sleep(self.time_slice_seconds)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
        
        logger.debug("Scheduler loop stopped")
    
    def _schedule_tick(self) -> None:
        """One scheduling tick"""
        with self._lock:
            if not self.ready_queue:
                return
            
            # Sort by priority
            self._sort_ready_queue()
            
            # Get highest priority process
            pid = self.ready_queue[0]
            process = self.processes.get(pid)
            
            if not process:
                self.ready_queue.pop(0)
                return
            
            # Run process
            if process.state == ProcessState.READY:
                self._run_process(process)
    
    def _run_process(self, process: Process) -> None:
        """Execute a process for one time slice"""
        process.state = ProcessState.RUNNING
        
        # If process has a target function, run it in a thread
        if process.target and (not process.thread or not process.thread.is_alive()):
            process.thread = threading.Thread(
                target=self._process_wrapper,
                args=(process,),
                daemon=True
            )
            process.thread.start()
        
        # Account for CPU time
        process.cpu_time_seconds += self.time_slice_seconds
        self.stats["total_cpu_time"] += self.time_slice_seconds
        self.stats["context_switches"] += 1
        
        # Move to back of queue (round-robin)
        if process.state == ProcessState.RUNNING:
            process.state = ProcessState.READY
            self.ready_queue.pop(0)
            self.ready_queue.append(process.pid)
    
    def _process_wrapper(self, process: Process) -> None:
        """Wrapper for process execution"""
        try:
            if process.target:
                process.target()
        except Exception as e:
            logger.error(f"Process {process.pid} error: {e}")
        finally:
            # Process finished
            process.state = ProcessState.TERMINATED
            if process.pid in self.ready_queue:
                self.ready_queue.remove(process.pid)
    
    def _sort_ready_queue(self) -> None:
        """Sort ready queue by priority"""
        self.ready_queue.sort(
            key=lambda pid: self.processes[pid].priority.value 
            if pid in self.processes else 999
        )


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    scheduler = ProcessScheduler()
    scheduler.initialize()
    
    # Create some processes
    def sample_task():
        for i in range(3):
            print(f"Task running: {i}")
            time.sleep(0.5)
    
    pid1 = scheduler.proc_create("test_process_1", target=sample_task)
    pid2 = scheduler.proc_create("test_process_2", priority=ProcessPriority.HIGH)
    
    if pid1:
        scheduler.proc_start(pid1)
    
    # Wait and check stats
    time.sleep(2)
    print(scheduler.get_stats())
    
    scheduler.shutdown()
