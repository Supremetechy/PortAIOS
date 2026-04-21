"""
Resource Manager for AI-OS
Handles GPU scheduling, memory allocation, and resource optimization
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time

from kernel.hardware_detection import HardwareDetector, ProcessorInfo, ProcessorType


class GPUSchedulingPolicy(Enum):
    """GPU scheduling policies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    EXCLUSIVE = "exclusive"
    SHARED = "shared"
    AFFINITY = "affinity"
    FAIR_SHARE = "fair_share"


class MemoryAllocationStrategy(Enum):
    """Memory allocation strategies"""
    FIRST_FIT = "first_fit"
    BEST_FIT = "best_fit"
    WORST_FIT = "worst_fit"
    BUDDY_SYSTEM = "buddy_system"


class PowerPolicy(Enum):
    """Power management policies for accelerators"""
    PERFORMANCE = "performance"
    BALANCED = "balanced"
    POWERSAVE = "powersave"


@dataclass
class GPUAllocation:
    """GPU allocation information"""
    gpu_id: int
    process_id: str
    tenant_id: str
    memory_allocated_gb: float
    allocated_at: float = field(default_factory=time.time)
    exclusive: bool = False
    priority: int = 0
    
    @property
    def allocation_time_seconds(self) -> float:
        return time.time() - self.allocated_at


@dataclass
class GPUStatus:
    """GPU status and availability"""
    gpu_id: int
    name: str
    total_memory_gb: float
    used_memory_gb: float
    temperature_celsius: Optional[float]
    power_usage_watts: Optional[float]
    utilization_percent: float
    processes: List[str] = field(default_factory=list)
    
    @property
    def available_memory_gb(self) -> float:
        return self.total_memory_gb - self.used_memory_gb
    
    @property
    def memory_utilization_percent(self) -> float:
        return (self.used_memory_gb / self.total_memory_gb * 100) if self.total_memory_gb > 0 else 0


@dataclass
class MemorySegment:
    """Memory segment for allocation tracking"""
    start_address: int
    size_gb: float
    allocated: bool = False
    process_id: Optional[str] = None


class GPUScheduler:
    """GPU scheduling and allocation manager"""
    
    def __init__(self, gpus: List[ProcessorInfo]):
        self.gpus = {i: gpu for i, gpu in enumerate(gpus)}
        self.allocations: Dict[int, List[GPUAllocation]] = {i: [] for i in range(len(gpus))}
        self.policy = GPUSchedulingPolicy.LEAST_LOADED
        self.affinity_map: Dict[str, int] = {}  # process_id -> gpu_id
        self.tenant_gpu_usage_gb: Dict[str, float] = {}
    
    def get_gpu_status(self, gpu_id: int) -> Optional[GPUStatus]:
        """Get current status of a GPU"""
        if gpu_id not in self.gpus:
            return None
        
        gpu = self.gpus[gpu_id]
        allocations = self.allocations[gpu_id]
        
        used_memory = sum(a.memory_allocated_gb for a in allocations)
        processes = [a.process_id for a in allocations]
        
        return GPUStatus(
            gpu_id=gpu_id,
            name=gpu.model,
            total_memory_gb=gpu.memory_gb or 0,
            used_memory_gb=used_memory,
            temperature_celsius=None,  # Would query actual GPU
            power_usage_watts=None,
            utilization_percent=0.0,  # Would query actual GPU
            processes=processes
        )
    
    def can_allocate(self, gpu_id: int, memory_gb: float, exclusive: bool = False) -> bool:
        """Check if GPU can allocate requested memory"""
        status = self.get_gpu_status(gpu_id)
        if not status:
            return False
        
        # Check if GPU is exclusively allocated
        if any(a.exclusive for a in self.allocations[gpu_id]):
            return False
        
        # Check if requesting exclusive access but GPU has allocations
        if exclusive and self.allocations[gpu_id]:
            return False
        
        # Check available memory
        return status.available_memory_gb >= memory_gb
    
    def allocate_gpu(
        self,
        process_id: str,
        memory_gb: float,
        gpu_id: Optional[int] = None,
        exclusive: bool = False,
        tenant_id: str = "default",
        priority: int = 0,
    ) -> Optional[int]:
        """Allocate GPU for a process"""
        
        # If specific GPU requested
        if gpu_id is not None:
            if self.can_allocate(gpu_id, memory_gb, exclusive):
                allocation = GPUAllocation(
                    gpu_id=gpu_id,
                    process_id=process_id,
                    tenant_id=tenant_id,
                    memory_allocated_gb=memory_gb,
                    exclusive=exclusive,
                    priority=priority,
                )
                self.allocations[gpu_id].append(allocation)
                self.tenant_gpu_usage_gb[tenant_id] = self.tenant_gpu_usage_gb.get(tenant_id, 0.0) + memory_gb
                
                # Set affinity
                if self.policy == GPUSchedulingPolicy.AFFINITY:
                    self.affinity_map[process_id] = gpu_id
                
                print(f"[GPU] Allocated GPU {gpu_id} to {process_id}: {memory_gb:.2f} GB")
                return gpu_id
            else:
                print(f"[GPU] Cannot allocate GPU {gpu_id}: insufficient resources")
                return None
        
        # Automatic GPU selection based on policy
        selected_gpu = self._select_gpu(memory_gb, exclusive, process_id, tenant_id)
        
        if selected_gpu is not None:
            allocation = GPUAllocation(
                gpu_id=selected_gpu,
                process_id=process_id,
                tenant_id=tenant_id,
                memory_allocated_gb=memory_gb,
                exclusive=exclusive,
                priority=priority,
            )
            self.allocations[selected_gpu].append(allocation)
            self.tenant_gpu_usage_gb[tenant_id] = self.tenant_gpu_usage_gb.get(tenant_id, 0.0) + memory_gb
            
            if self.policy == GPUSchedulingPolicy.AFFINITY:
                self.affinity_map[process_id] = selected_gpu
            
            print(f"[GPU] Allocated GPU {selected_gpu} to {process_id}: {memory_gb:.2f} GB")
            return selected_gpu
        
        print(f"[GPU] No GPU available for {process_id}")
        return None
    
    def _select_gpu(self, memory_gb: float, exclusive: bool, process_id: str, tenant_id: str) -> Optional[int]:
        """Select GPU based on scheduling policy"""
        
        # Check affinity first
        if self.policy == GPUSchedulingPolicy.AFFINITY and process_id in self.affinity_map:
            gpu_id = self.affinity_map[process_id]
            if self.can_allocate(gpu_id, memory_gb, exclusive):
                return gpu_id
        
        if self.policy == GPUSchedulingPolicy.ROUND_ROBIN:
            return self._select_round_robin(memory_gb, exclusive)
        
        elif self.policy == GPUSchedulingPolicy.LEAST_LOADED:
            return self._select_least_loaded(memory_gb, exclusive)
        
        elif self.policy == GPUSchedulingPolicy.EXCLUSIVE:
            return self._select_exclusive(memory_gb)
        
        elif self.policy == GPUSchedulingPolicy.FAIR_SHARE:
            return self._select_fair_share(memory_gb, exclusive, tenant_id)
        
        else:  # SHARED or default
            return self._select_least_loaded(memory_gb, exclusive)
    
    def _select_round_robin(self, memory_gb: float, exclusive: bool) -> Optional[int]:
        """Round-robin GPU selection"""
        for gpu_id in sorted(self.gpus.keys()):
            if self.can_allocate(gpu_id, memory_gb, exclusive):
                return gpu_id
        return None
    
    def _select_least_loaded(self, memory_gb: float, exclusive: bool) -> Optional[int]:
        """Select GPU with most available memory"""
        best_gpu = None
        max_available = 0.0
        
        for gpu_id in self.gpus.keys():
            if self.can_allocate(gpu_id, memory_gb, exclusive):
                status = self.get_gpu_status(gpu_id)
                if status and status.available_memory_gb > max_available:
                    max_available = status.available_memory_gb
                    best_gpu = gpu_id
        
        return best_gpu
    
    def _select_exclusive(self, memory_gb: float) -> Optional[int]:
        """Select GPU for exclusive access"""
        for gpu_id in self.gpus.keys():
            if not self.allocations[gpu_id]:  # No allocations
                status = self.get_gpu_status(gpu_id)
                if status and status.available_memory_gb >= memory_gb:
                    return gpu_id
        return None

    def _select_fair_share(self, memory_gb: float, exclusive: bool, tenant_id: str) -> Optional[int]:
        """Select GPU to balance per-tenant usage first, then free memory"""
        candidate_gpus = []
        for gpu_id in self.gpus.keys():
            if self.can_allocate(gpu_id, memory_gb, exclusive):
                status = self.get_gpu_status(gpu_id)
                if status:
                    candidate_gpus.append((gpu_id, status.available_memory_gb))
        if not candidate_gpus:
            return None
        tenant_usage = self.tenant_gpu_usage_gb.get(tenant_id, 0.0)
        candidate_gpus.sort(key=lambda x: (-x[1], tenant_usage))
        return candidate_gpus[0][0]
    
    def release_gpu(self, process_id: str, gpu_id: Optional[int] = None):
        """Release GPU allocation for a process"""
        released = False
        
        if gpu_id is not None:
            # Release from specific GPU
            for alloc in self.allocations[gpu_id]:
                if alloc.process_id == process_id:
                    self.tenant_gpu_usage_gb[alloc.tenant_id] = max(
                        0.0, self.tenant_gpu_usage_gb.get(alloc.tenant_id, 0.0) - alloc.memory_allocated_gb
                    )
            self.allocations[gpu_id] = [
                a for a in self.allocations[gpu_id] if a.process_id != process_id
            ]
            released = True
        else:
            # Release from all GPUs
            for gpu_id in self.allocations.keys():
                before = len(self.allocations[gpu_id])
                for alloc in self.allocations[gpu_id]:
                    if alloc.process_id == process_id:
                        self.tenant_gpu_usage_gb[alloc.tenant_id] = max(
                            0.0, self.tenant_gpu_usage_gb.get(alloc.tenant_id, 0.0) - alloc.memory_allocated_gb
                        )
                self.allocations[gpu_id] = [
                    a for a in self.allocations[gpu_id] if a.process_id != process_id
                ]
                if len(self.allocations[gpu_id]) < before:
                    released = True
        
        if released:
            print(f"[GPU] Released GPU allocation for {process_id}")
            
            # Remove affinity
            if process_id in self.affinity_map:
                del self.affinity_map[process_id]
    
    def get_all_gpu_status(self) -> List[GPUStatus]:
        """Get status of all GPUs"""
        return [self.get_gpu_status(gpu_id) for gpu_id in sorted(self.gpus.keys())]
    
    def print_gpu_status(self):
        """Print GPU status summary"""
        print("\n" + "="*80)
        print("GPU STATUS")
        print("="*80)
        
        for status in self.get_all_gpu_status():
            if status:
                print(f"\nGPU {status.gpu_id}: {status.name}")
                print(f"  Memory: {status.used_memory_gb:.2f}/{status.total_memory_gb:.2f} GB ({status.memory_utilization_percent:.1f}%)")
                print(f"  Processes: {len(status.processes)}")
                if status.processes:
                    for proc in status.processes:
                        alloc = next((a for a in self.allocations[status.gpu_id] if a.process_id == proc), None)
                        if alloc:
                            print(f"    - {proc}: {alloc.memory_allocated_gb:.2f} GB")
        
        print("\n" + "="*80 + "\n")


class MemoryManager:
    """System memory manager with allocation strategies"""
    
    def __init__(self, total_memory_gb: float):
        self.total_memory_gb = total_memory_gb
        self.allocations: Dict[str, float] = {}
        self.allocations_by_node: Dict[str, Dict[int, float]] = {}
        self.numa_nodes: Dict[int, float] = {0: total_memory_gb}
        self.numa_reserved_gb: Dict[int, float] = {0: 2.0}
        self.strategy = MemoryAllocationStrategy.BEST_FIT
        self.reserved_system_gb = 2.0  # Reserve for OS
    
    @property
    def available_memory_gb(self) -> float:
        """Get available memory"""
        used = sum(self.allocations.values())
        return self.total_memory_gb - used - self.reserved_system_gb
    
    @property
    def used_memory_gb(self) -> float:
        """Get used memory"""
        return sum(self.allocations.values())
    
    @property
    def utilization_percent(self) -> float:
        """Get memory utilization percentage"""
        usable = self.total_memory_gb - self.reserved_system_gb
        return (self.used_memory_gb / usable * 100) if usable > 0 else 0
    
    def can_allocate(self, size_gb: float) -> bool:
        """Check if memory can be allocated"""
        return self.available_memory_gb >= size_gb
    
    def allocate(self, process_id: str, size_gb: float) -> bool:
        """Allocate memory for a process"""
        if not self.can_allocate(size_gb):
            print(f"[MEMORY] Cannot allocate {size_gb:.2f} GB for {process_id}: insufficient memory")
            return False
        
        self.allocations[process_id] = size_gb
        print(f"[MEMORY] Allocated {size_gb:.2f} GB to {process_id}")
        return True

    def allocate_numa(self, process_id: str, size_gb: float, node_id: Optional[int] = None) -> bool:
        """Allocate memory with optional NUMA node targeting"""
        if node_id is None:
            return self.allocate(process_id, size_gb)
        if node_id not in self.numa_nodes:
            print(f"[MEMORY] NUMA node {node_id} not available")
            return False
        available = self.numa_nodes[node_id] - self.numa_reserved_gb.get(node_id, 0.0)
        allocated = self.allocations_by_node.get(process_id, {}).get(node_id, 0.0)
        if allocated + size_gb > available:
            print(f"[MEMORY] Cannot allocate {size_gb:.2f} GB on NUMA node {node_id}")
            return False
        self.allocations_by_node.setdefault(process_id, {})[node_id] = allocated + size_gb
        self.allocations[process_id] = self.allocations.get(process_id, 0.0) + size_gb
        print(f"[MEMORY] Allocated {size_gb:.2f} GB to {process_id} on NUMA node {node_id}")
        return True
    
    def release(self, process_id: str) -> bool:
        """Release memory for a process"""
        if process_id in self.allocations:
            size = self.allocations[process_id]
            del self.allocations[process_id]
            if process_id in self.allocations_by_node:
                del self.allocations_by_node[process_id]
            print(f"[MEMORY] Released {size:.2f} GB from {process_id}")
            return True
        return False

    def set_numa_nodes(self, node_capacities_gb: Dict[int, float], reserved_gb: Optional[Dict[int, float]] = None):
        self.numa_nodes = dict(node_capacities_gb)
        if reserved_gb:
            self.numa_reserved_gb = dict(reserved_gb)
        else:
            self.numa_reserved_gb = {node: 2.0 for node in self.numa_nodes}

    def get_numa_status(self) -> Dict[int, Dict[str, float]]:
        status = {}
        for node_id, total in self.numa_nodes.items():
            reserved = self.numa_reserved_gb.get(node_id, 0.0)
            allocated = sum(
                allocs.get(node_id, 0.0) for allocs in self.allocations_by_node.values()
            )
            status[node_id] = {
                "total_gb": total,
                "reserved_gb": reserved,
                "allocated_gb": allocated,
                "available_gb": max(0.0, total - reserved - allocated),
            }
        return status
    
    def get_allocation(self, process_id: str) -> float:
        """Get allocated memory for a process"""
        return self.allocations.get(process_id, 0.0)
    
    def print_status(self):
        """Print memory status"""
        print("\n" + "="*80)
        print("MEMORY STATUS")
        print("="*80)
        
        print(f"\nTotal Memory: {self.total_memory_gb:.2f} GB")
        print(f"Reserved (System): {self.reserved_system_gb:.2f} GB")
        print(f"Used: {self.used_memory_gb:.2f} GB")
        print(f"Available: {self.available_memory_gb:.2f} GB")
        print(f"Utilization: {self.utilization_percent:.1f}%")
        
        if self.allocations:
            print(f"\nAllocations: {len(self.allocations)}")
            for process_id, size in sorted(self.allocations.items(), key=lambda x: x[1], reverse=True):
                print(f"  {process_id}: {size:.2f} GB")

        if self.numa_nodes and len(self.numa_nodes) > 1:
            print("\nNUMA Nodes:")
            for node_id, stats in self.get_numa_status().items():
                print(f"  Node {node_id}: {stats['allocated_gb']:.2f}/{stats['total_gb']:.2f} GB (avail {stats['available_gb']:.2f} GB)")
        
        print("\n" + "="*80 + "\n")


@dataclass
class ResourceQuota:
    cpu_cores: float = 0.0
    memory_gb: float = 0.0
    gpu_memory_gb: float = 0.0
    max_jobs: int = 0


@dataclass
class TenantUsage:
    cpu_cores: float = 0.0
    memory_gb: float = 0.0
    gpu_memory_gb: float = 0.0
    active_jobs: int = 0


class TenantRegistry:
    def __init__(self):
        self.quotas: Dict[str, ResourceQuota] = {}
        self.usage: Dict[str, TenantUsage] = {}

    def set_quota(self, tenant_id: str, quota: ResourceQuota) -> None:
        self.quotas[tenant_id] = quota
        if tenant_id not in self.usage:
            self.usage[tenant_id] = TenantUsage()

    def get_quota(self, tenant_id: str) -> ResourceQuota:
        return self.quotas.get(tenant_id, ResourceQuota())

    def get_usage(self, tenant_id: str) -> TenantUsage:
        return self.usage.get(tenant_id, TenantUsage())

    def apply_usage(self, tenant_id: str, cpu_cores: float, memory_gb: float, gpu_memory_gb: float, jobs_delta: int) -> None:
        usage = self.usage.setdefault(tenant_id, TenantUsage())
        usage.cpu_cores = max(0.0, usage.cpu_cores + cpu_cores)
        usage.memory_gb = max(0.0, usage.memory_gb + memory_gb)
        usage.gpu_memory_gb = max(0.0, usage.gpu_memory_gb + gpu_memory_gb)
        usage.active_jobs = max(0, usage.active_jobs + jobs_delta)


@dataclass
class TenantUsageReport:
    tenant_id: str
    cpu_cores: float
    memory_gb: float
    gpu_memory_gb: float
    active_jobs: int
    quota: ResourceQuota
    timestamp: float = field(default_factory=time.time)


class TenantUsageTracker:
    """Tracks per-tenant resource usage and produces usage reports"""

    def __init__(self, tenant_registry: TenantRegistry):
        self.tenant_registry = tenant_registry

    def get_report(self, tenant_id: str) -> TenantUsageReport:
        usage = self.tenant_registry.get_usage(tenant_id)
        quota = self.tenant_registry.get_quota(tenant_id)
        return TenantUsageReport(
            tenant_id=tenant_id,
            cpu_cores=usage.cpu_cores,
            memory_gb=usage.memory_gb,
            gpu_memory_gb=usage.gpu_memory_gb,
            active_jobs=usage.active_jobs,
            quota=quota,
        )

    def get_all_reports(self) -> List[TenantUsageReport]:
        return [self.get_report(tid) for tid in self.tenant_registry.quotas]


class QuotaManager:
    def __init__(self, tenant_registry: TenantRegistry):
        self.tenant_registry = tenant_registry

    def can_allocate(self, tenant_id: str, cpu_cores: float, memory_gb: float, gpu_memory_gb: float, jobs_delta: int) -> bool:
        quota = self.tenant_registry.get_quota(tenant_id)
        usage = self.tenant_registry.get_usage(tenant_id)

        if quota.cpu_cores and usage.cpu_cores + cpu_cores > quota.cpu_cores:
            return False
        if quota.memory_gb and usage.memory_gb + memory_gb > quota.memory_gb:
            return False
        if quota.gpu_memory_gb and usage.gpu_memory_gb + gpu_memory_gb > quota.gpu_memory_gb:
            return False
        if quota.max_jobs and usage.active_jobs + jobs_delta > quota.max_jobs:
            return False
        return True


class ResourceManager:
    """Central resource management for AI-OS"""
    
    def __init__(self):
        self.gpu_scheduler: Optional[GPUScheduler] = None
        self.memory_manager: Optional[MemoryManager] = None
        self.tenant_registry = TenantRegistry()
        self.quota_manager = QuotaManager(self.tenant_registry)
        self.power_policy = PowerPolicy.BALANCED
        self.initialized = False
    
    def initialize(self):
        """Initialize resource manager with detected hardware"""
        print("[RESOURCE] Initializing resource manager...")
        
        # Detect hardware
        detector = HardwareDetector()
        specs = detector.detect_all()
        
        # Initialize GPU scheduler
        gpus = [p for p in specs.processors if p.processor_type == ProcessorType.GPU]
        if gpus:
            self.gpu_scheduler = GPUScheduler(gpus)
            print(f"[RESOURCE]   Initialized GPU scheduler with {len(gpus)} GPU(s)")
        else:
            print("[RESOURCE]   No GPUs detected")
        
        # Initialize memory manager
        self.memory_manager = MemoryManager(specs.memory.total_gb)
        print(f"[RESOURCE]   Initialized memory manager with {specs.memory.total_gb:.2f} GB")
        
        self.initialized = True
        print("[RESOURCE] ✓ Resource manager initialized")

    def set_gpu_policy(self, policy: GPUSchedulingPolicy):
        if self.gpu_scheduler:
            self.gpu_scheduler.policy = policy

    def set_power_policy(self, policy: PowerPolicy):
        self.power_policy = policy
        if self.gpu_scheduler:
            for gpu_id in self.gpu_scheduler.gpus.keys():
                print(f"[POWER] Set GPU {gpu_id} policy to {policy.value}")
    
    def allocate_resources(
        self,
        process_id: str,
        cpu_cores: float = 0,
        memory_gb: float = 0,
        gpu_memory_gb: float = 0,
        gpu_id: Optional[int] = None,
        exclusive_gpu: bool = False,
        tenant_id: str = "default",
        priority: int = 0,
    ) -> Dict[str, Any]:
        """Allocate resources for a process"""
        
        if not self.initialized:
            print("[RESOURCE] Resource manager not initialized")
            return {}
        
        allocations = {}

        if not self.quota_manager.can_allocate(
            tenant_id, cpu_cores, memory_gb, gpu_memory_gb, jobs_delta=1
        ):
            print(f"[RESOURCE] Quota exceeded for tenant {tenant_id}")
            return {}
        
        # Allocate memory
        if memory_gb > 0 and self.memory_manager:
            if self.memory_manager.allocate(process_id, memory_gb):
                allocations['memory_gb'] = memory_gb
            else:
                return {}  # Failed to allocate memory
        
        # Allocate GPU
        if gpu_memory_gb > 0 and self.gpu_scheduler:
            allocated_gpu = self.gpu_scheduler.allocate_gpu(
                process_id, gpu_memory_gb, gpu_id, exclusive_gpu, tenant_id=tenant_id, priority=priority
            )
            if allocated_gpu is not None:
                allocations['gpu_id'] = allocated_gpu
                allocations['gpu_memory_gb'] = gpu_memory_gb
            else:
                # Rollback memory allocation
                if 'memory_gb' in allocations:
                    self.memory_manager.release(process_id)
                return {}
        
        allocations['cpu_cores'] = cpu_cores
        allocations['tenant_id'] = tenant_id
        self.tenant_registry.apply_usage(tenant_id, cpu_cores, memory_gb, gpu_memory_gb, jobs_delta=1)
        
        return allocations
    
    def release_resources(self, process_id: str, tenant_id: str = "default", cpu_cores: float = 0.0, memory_gb: float = 0.0, gpu_memory_gb: float = 0.0):
        """Release all resources for a process"""
        
        if self.memory_manager:
            self.memory_manager.release(process_id)
        
        if self.gpu_scheduler:
            self.gpu_scheduler.release_gpu(process_id)
        
        self.tenant_registry.apply_usage(tenant_id, -cpu_cores, -memory_gb, -gpu_memory_gb, jobs_delta=-1)
    
    def get_available_resources(self) -> Dict[str, Any]:
        """Get currently available resources"""
        resources = {
            'cpu_cores': 0,
            'memory_gb': 0,
            'gpus': []
        }
        
        if self.memory_manager:
            resources['memory_gb'] = self.memory_manager.available_memory_gb
        
        if self.gpu_scheduler:
            for status in self.gpu_scheduler.get_all_gpu_status():
                if status:
                    resources['gpus'].append({
                        'gpu_id': status.gpu_id,
                        'name': status.name,
                        'available_memory_gb': status.available_memory_gb,
                        'total_memory_gb': status.total_memory_gb
                    })
        
        return resources

    def set_tenant_quota(self, tenant_id: str, quota: ResourceQuota) -> None:
        self.tenant_registry.set_quota(tenant_id, quota)

    def get_tenant_usage(self, tenant_id: str) -> TenantUsage:
        return self.tenant_registry.get_usage(tenant_id)
    
    def print_summary(self):
        """Print resource manager summary"""
        if not self.initialized:
            print("[RESOURCE] Resource manager not initialized")
            return
        
        if self.memory_manager:
            self.memory_manager.print_status()
        
        if self.gpu_scheduler:
            self.gpu_scheduler.print_gpu_status()

        if self.tenant_registry.usage:
            print("\n" + "="*80)
            print("TENANT USAGE")
            print("="*80)
            for tenant_id, usage in sorted(self.tenant_registry.usage.items()):
                print(f"\nTenant: {tenant_id}")
                print(f"  CPU Cores: {usage.cpu_cores:.2f}")
                print(f"  Memory: {usage.memory_gb:.2f} GB")
                print(f"  GPU Memory: {usage.gpu_memory_gb:.2f} GB")
                print(f"  Active Jobs: {usage.active_jobs}")
            print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    # Test resource manager
    manager = ResourceManager()
    manager.initialize()
    manager.print_summary()
    
    # Test allocation
    print("\nTesting resource allocation...")
    alloc = manager.allocate_resources("test-process", memory_gb=8.0, gpu_memory_gb=4.0)
    print(f"Allocated: {alloc}")
    
    manager.print_summary()
    
    # Release
    manager.release_resources("test-process")
    manager.print_summary()
