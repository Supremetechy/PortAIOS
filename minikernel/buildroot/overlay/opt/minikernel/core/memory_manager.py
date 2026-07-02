"""
Memory Manager

Handles memory allocation, paging, and resource tracking
Essential kernel service for microkernel architecture
"""

import logging
import threading
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("MiniKernel.Memory")


class MemoryType(Enum):
    """Types of memory allocation"""
    KERNEL = "kernel"       # Kernel space
    USER = "user"          # User space
    SHARED = "shared"      # Shared memory
    DEVICE = "device"      # Device/DMA
    CACHE = "cache"        # Cache/buffers


@dataclass
class MemoryBlock:
    """Represents an allocated memory block"""
    id: str
    owner: str
    size_bytes: int
    mem_type: MemoryType
    allocated_at: datetime = field(default_factory=datetime.now)
    locked: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.allocated_at).total_seconds()


class MemoryManager:
    """
    Memory Manager for MiniKernel
    
    Capabilities:
    - Memory allocation/deallocation
    - Memory tracking per process
    - Memory limits enforcement
    - Statistics and monitoring
    """
    
    def __init__(
        self,
        total_memory_mb: int = 8192,
        page_size_kb: int = 4
    ):
        self.total_memory_bytes = total_memory_mb * 1024 * 1024
        self.page_size_bytes = page_size_kb * 1024
        
        self.blocks: Dict[str, MemoryBlock] = {}
        self.process_limits: Dict[str, int] = {}  # process_id -> max_bytes
        
        self._lock = threading.RLock()
        self._next_block_id = 0
        
        self.stats = {
            "allocations": 0,
            "deallocations": 0,
            "allocation_failures": 0,
            "oom_events": 0
        }
        
        logger.info(f"Memory Manager created: {total_memory_mb} MB total")
    
    def initialize(self) -> None:
        """Initialize memory subsystem"""
        logger.info(f"Memory subsystem initialized: {self.total_memory_bytes / (1024**2):.0f} MB")
    
    def shutdown(self) -> None:
        """Shutdown memory subsystem"""
        with self._lock:
            # Free all blocks
            self.blocks.clear()
        logger.info("Memory subsystem shutdown")
    
    def mem_allocate(
        self,
        owner: str,
        size_bytes: int,
        mem_type: MemoryType = MemoryType.USER,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Allocate memory block
        
        Returns: Block ID if successful, None otherwise
        """
        with self._lock:
            # Check if enough free memory
            if not self._can_allocate(owner, size_bytes):
                logger.warning(f"Allocation denied: {owner} requested {size_bytes} bytes")
                self.stats["allocation_failures"] += 1
                return None
            
            # Create block
            block_id = f"mem_{self._next_block_id}"
            self._next_block_id += 1
            
            block = MemoryBlock(
                id=block_id,
                owner=owner,
                size_bytes=size_bytes,
                mem_type=mem_type,
                metadata=metadata or {}
            )
            
            self.blocks[block_id] = block
            self.stats["allocations"] += 1
            
            logger.debug(f"Allocated {size_bytes} bytes to {owner} (id={block_id})")
            return block_id
    
    def mem_free(self, block_id: str, owner: str) -> bool:
        """
        Free a memory block
        
        Returns: True if successful
        """
        with self._lock:
            if block_id not in self.blocks:
                logger.warning(f"Block not found: {block_id}")
                return False
            
            block = self.blocks[block_id]
            
            # Verify ownership
            if block.owner != owner:
                logger.error(f"Access denied: {owner} cannot free block owned by {block.owner}")
                return False
            
            # Check if locked
            if block.locked:
                logger.warning(f"Cannot free locked block: {block_id}")
                return False
            
            del self.blocks[block_id]
            self.stats["deallocations"] += 1
            
            logger.debug(f"Freed {block.size_bytes} bytes from {owner} (id={block_id})")
            return True
    
    def mem_resize(self, block_id: str, new_size_bytes: int, owner: str) -> bool:
        """
        Resize a memory block
        
        Returns: True if successful
        """
        with self._lock:
            if block_id not in self.blocks:
                return False
            
            block = self.blocks[block_id]
            
            if block.owner != owner:
                logger.error(f"Access denied: {owner} cannot resize block owned by {block.owner}")
                return False
            
            old_size = block.size_bytes
            size_diff = new_size_bytes - old_size
            
            # Check if can grow
            if size_diff > 0:
                if not self._can_allocate(owner, size_diff):
                    return False
            
            block.size_bytes = new_size_bytes
            logger.debug(f"Resized block {block_id}: {old_size} → {new_size_bytes} bytes")
            return True
    
    def mem_lock(self, block_id: str, owner: str) -> bool:
        """Lock a memory block (prevent swapping/freeing)"""
        with self._lock:
            if block_id not in self.blocks:
                return False
            
            block = self.blocks[block_id]
            if block.owner != owner:
                return False
            
            block.locked = True
            logger.debug(f"Locked block: {block_id}")
            return True
    
    def mem_unlock(self, block_id: str, owner: str) -> bool:
        """Unlock a memory block"""
        with self._lock:
            if block_id not in self.blocks:
                return False
            
            block = self.blocks[block_id]
            if block.owner != owner:
                return False
            
            block.locked = False
            logger.debug(f"Unlocked block: {block_id}")
            return True
    
    def set_process_limit(self, process_id: str, limit_mb: int) -> None:
        """Set memory limit for a process"""
        with self._lock:
            self.process_limits[process_id] = limit_mb * 1024 * 1024
            logger.debug(f"Set memory limit for {process_id}: {limit_mb} MB")
    
    def get_process_usage(self, process_id: str) -> Dict[str, Any]:
        """Get memory usage for a process"""
        with self._lock:
            blocks = [b for b in self.blocks.values() if b.owner == process_id]
            total_bytes = sum(b.size_bytes for b in blocks)
            
            limit_bytes = self.process_limits.get(process_id, self.total_memory_bytes)
            
            return {
                "process_id": process_id,
                "allocated_mb": total_bytes / (1024 * 1024),
                "limit_mb": limit_bytes / (1024 * 1024),
                "usage_percent": (total_bytes / limit_bytes * 100) if limit_bytes > 0 else 0,
                "blocks": len(blocks),
                "locked_blocks": len([b for b in blocks if b.locked])
            }
    
    def get_system_usage(self) -> Dict[str, Any]:
        """Get overall system memory usage"""
        with self._lock:
            total_allocated = sum(b.size_bytes for b in self.blocks.values())
            
            by_type = {}
            for mem_type in MemoryType:
                blocks = [b for b in self.blocks.values() if b.mem_type == mem_type]
                by_type[mem_type.value] = {
                    "blocks": len(blocks),
                    "bytes": sum(b.size_bytes for b in blocks)
                }
            
            return {
                "total_mb": self.total_memory_bytes / (1024 * 1024),
                "allocated_mb": total_allocated / (1024 * 1024),
                "free_mb": (self.total_memory_bytes - total_allocated) / (1024 * 1024),
                "usage_percent": (total_allocated / self.total_memory_bytes * 100),
                "blocks_total": len(self.blocks),
                "by_type": by_type,
                "stats": self.stats
            }
    
    def _can_allocate(self, owner: str, size_bytes: int) -> bool:
        """Check if allocation is possible"""
        # Check system limit
        total_allocated = sum(b.size_bytes for b in self.blocks.values())
        if total_allocated + size_bytes > self.total_memory_bytes:
            logger.warning("OOM: System memory exhausted")
            self.stats["oom_events"] += 1
            return False
        
        # Check process limit
        if owner in self.process_limits:
            owner_allocated = sum(
                b.size_bytes for b in self.blocks.values() if b.owner == owner
            )
            if owner_allocated + size_bytes > self.process_limits[owner]:
                logger.warning(f"OOM: Process {owner} exceeded limit")
                return False
        
        return True
    
    def collect_garbage(self, max_age_seconds: Optional[float] = None) -> int:
        """
        Garbage collection - free old unlocked blocks
        
        Returns: Number of blocks freed
        """
        with self._lock:
            to_free = []
            
            for block_id, block in self.blocks.items():
                if block.locked:
                    continue
                
                if max_age_seconds and block.age_seconds > max_age_seconds:
                    to_free.append(block_id)
            
            for block_id in to_free:
                del self.blocks[block_id]
            
            if to_free:
                logger.info(f"GC: Freed {len(to_free)} blocks")
            
            return len(to_free)
    
    def defragment(self) -> None:
        """Placeholder for memory defragmentation"""
        logger.info("Memory defragmentation requested (not implemented)")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    mem = MemoryManager(total_memory_mb=1024)
    mem.initialize()
    
    # Set process limit
    mem.set_process_limit("test_process", 100)
    
    # Allocate memory
    block1 = mem.mem_allocate("test_process", 50 * 1024 * 1024, MemoryType.USER)
    print(f"Allocated: {block1}")
    
    # Check usage
    usage = mem.get_process_usage("test_process")
    print(f"Usage: {usage}")
    
    # System stats
    system = mem.get_system_usage()
    print(f"System: {system}")
