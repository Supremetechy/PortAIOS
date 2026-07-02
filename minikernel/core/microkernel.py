"""
MicroKernel - Minimal kernel running essential services only

Design Philosophy:
- Keep kernel minimal (IPC, scheduling, memory management)
- Everything else runs in user space
- Inspired by seL4 and Minix architecture
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("MiniKernel")


class KernelState(Enum):
    """Kernel operational states"""
    UNINITIALIZED = "uninitialized"
    BOOTING = "booting"
    RUNNING = "running"
    SUSPENDED = "suspended"
    SHUTTING_DOWN = "shutting_down"
    HALTED = "halted"
    PANIC = "panic"


class ServicePriority(Enum):
    """Service initialization priority"""
    CRITICAL = 0    # Must start first (IPC, Memory)
    HIGH = 1        # Core services (Scheduler, Security)
    NORMAL = 2      # Standard services (Filesystem, Network)
    LOW = 3         # Optional services (AI, Voice)


@dataclass
class KernelService:
    """Represents a kernel service"""
    name: str
    priority: ServicePriority
    instance: Any
    state: str = "stopped"
    start_time: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    
    def start(self) -> bool:
        """Start the service"""
        try:
            if hasattr(self.instance, 'initialize'):
                self.instance.initialize()
            self.state = "running"
            self.start_time = datetime.now()
            logger.info(f"✓ Started service: {self.name}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to start {self.name}: {e}")
            self.state = "failed"
            return False
    
    def stop(self) -> bool:
        """Stop the service"""
        try:
            if hasattr(self.instance, 'shutdown'):
                self.instance.shutdown()
            self.state = "stopped"
            logger.info(f"✓ Stopped service: {self.name}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to stop {self.name}: {e}")
            return False


@dataclass
class KernelStats:
    """Kernel runtime statistics"""
    boot_time: datetime
    uptime_seconds: float = 0.0
    syscalls_total: int = 0
    context_switches: int = 0
    interrupts_handled: int = 0
    memory_allocated_mb: float = 0.0
    active_processes: int = 0
    
    def update_uptime(self):
        """Update uptime calculation"""
        self.uptime_seconds = (datetime.now() - self.boot_time).total_seconds()


class MicroKernel:
    """
    Minimal microkernel implementation
    
    Responsibilities:
    1. Service lifecycle management
    2. System call interface
    3. Resource coordination
    4. Panic handling
    
    Does NOT handle:
    - File operations (→ FileSystemService)
    - Process management (→ ProcessService)
    - Network (→ NetworkService)
    - AI/Voice (→ User space)
    """
    
    def __init__(self):
        self.state = KernelState.UNINITIALIZED
        self.services: Dict[str, KernelService] = {}
        self.stats = None
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()
        
        # Kernel ring buffer for logs
        self._ring_buffer: List[str] = []
        self._ring_buffer_size = 1000
        
        logger.info("MicroKernel instance created")
    
    def register_service(
        self,
        name: str,
        instance: Any,
        priority: ServicePriority,
        dependencies: Optional[List[str]] = None
    ) -> None:
        """Register a service with the kernel"""
        with self._lock:
            service = KernelService(
                name=name,
                priority=priority,
                instance=instance,
                dependencies=dependencies or []
            )
            self.services[name] = service
            logger.debug(f"Registered service: {name} (priority={priority.name})")
    
    def boot(self) -> bool:
        """
        Boot the microkernel
        
        Boot sequence:
        1. Initialize stats
        2. Start services by priority
        3. Verify critical services
        4. Enter running state
        """
        logger.info("=" * 60)
        logger.info("MiniKernel Boot Sequence Starting")
        logger.info("=" * 60)
        
        self.state = KernelState.BOOTING
        self.stats = KernelStats(boot_time=datetime.now())
        
        try:
            # Sort services by priority
            sorted_services = sorted(
                self.services.values(),
                key=lambda s: s.priority.value
            )
            
            # Start services
            for service in sorted_services:
                # Check dependencies
                for dep in service.dependencies:
                    if dep not in self.services or self.services[dep].state != "running":
                        logger.error(f"Dependency not met: {service.name} requires {dep}")
                        self._kernel_panic(f"Service dependency failure: {service.name}")
                        return False
                
                if not service.start():
                    if service.priority == ServicePriority.CRITICAL:
                        self._kernel_panic(f"Critical service failed: {service.name}")
                        return False
                    else:
                        logger.warning(f"Non-critical service failed: {service.name}")
            
            # Verify critical services
            critical_services = [s for s in self.services.values() 
                               if s.priority == ServicePriority.CRITICAL]
            if not all(s.state == "running" for s in critical_services):
                self._kernel_panic("Not all critical services running")
                return False
            
            self.state = KernelState.RUNNING
            logger.info("=" * 60)
            logger.info("✓ MiniKernel boot complete")
            logger.info(f"✓ {len([s for s in self.services.values() if s.state == 'running'])} services running")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            self._kernel_panic(f"Boot failure: {e}")
            return False
    
    def syscall(self, call: str, **kwargs) -> Dict[str, Any]:
        """
        System call interface
        
        All user space → kernel space interactions go through here
        """
        with self._lock:
            self.stats.syscalls_total += 1
            
            try:
                # Route to appropriate service
                if call.startswith("ipc_"):
                    service = self.services.get("ipc")
                elif call.startswith("mem_"):
                    service = self.services.get("memory")
                elif call.startswith("proc_"):
                    service = self.services.get("scheduler")
                else:
                    return {"success": False, "error": f"Unknown syscall: {call}"}
                
                if not service or service.state != "running":
                    return {"success": False, "error": f"Service unavailable for: {call}"}
                
                # Delegate to service
                handler = getattr(service.instance, call, None)
                if handler:
                    result = handler(**kwargs)
                    return {"success": True, "result": result}
                else:
                    return {"success": False, "error": f"No handler for: {call}"}
                    
            except Exception as e:
                logger.error(f"Syscall error {call}: {e}")
                return {"success": False, "error": str(e)}
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a service instance by name"""
        service = self.services.get(name)
        return service.instance if service else None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get kernel statistics"""
        if self.stats:
            self.stats.update_uptime()
            return {
                "state": self.state.value,
                "uptime_seconds": self.stats.uptime_seconds,
                "syscalls": self.stats.syscalls_total,
                "services": len([s for s in self.services.values() if s.state == "running"]),
                "memory_mb": self.stats.memory_allocated_mb,
                "processes": self.stats.active_processes
            }
        return {}
    
    def shutdown(self) -> bool:
        """
        Graceful shutdown sequence
        
        1. Stop accepting syscalls
        2. Stop services (reverse priority order)
        3. Final cleanup
        """
        logger.info("MiniKernel shutdown initiated")
        self.state = KernelState.SHUTTING_DOWN
        self._shutdown_event.set()
        
        # Stop services in reverse priority order
        sorted_services = sorted(
            self.services.values(),
            key=lambda s: s.priority.value,
            reverse=True
        )
        
        for service in sorted_services:
            if service.state == "running":
                service.stop()
        
        self.state = KernelState.HALTED
        logger.info("✓ MiniKernel halted")
        return True
    
    def _kernel_panic(self, reason: str) -> None:
        """
        Kernel panic - unrecoverable error
        
        Similar to Linux kernel panic
        """
        self.state = KernelState.PANIC
        logger.critical("!" * 60)
        logger.critical("KERNEL PANIC")
        logger.critical(f"Reason: {reason}")
        logger.critical("!" * 60)
        
        # Dump state for debugging
        logger.critical(f"State: {self.state.value}")
        logger.critical(f"Services: {len(self.services)}")
        for name, service in self.services.items():
            logger.critical(f"  {name}: {service.state}")
    
    def _log_to_ring_buffer(self, message: str) -> None:
        """Add message to kernel ring buffer (like dmesg)"""
        timestamp = datetime.now().isoformat()
        entry = f"[{timestamp}] {message}"
        
        if len(self._ring_buffer) >= self._ring_buffer_size:
            self._ring_buffer.pop(0)
        
        self._ring_buffer.append(entry)
    
    def get_ring_buffer(self, lines: int = 100) -> List[str]:
        """Get recent kernel messages"""
        return self._ring_buffer[-lines:]
    
    def __repr__(self) -> str:
        return f"<MicroKernel state={self.state.value} services={len(self.services)}>"


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    kernel = MicroKernel()
    
    # Would normally register services here
    # kernel.register_service("ipc", IPCManager(), ServicePriority.CRITICAL)
    # kernel.register_service("memory", MemoryManager(), ServicePriority.CRITICAL)
    # etc.
    
    print(kernel)
