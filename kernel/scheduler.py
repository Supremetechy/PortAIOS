"""
AI Workload Scheduler for AI-OS
Manages process scheduling and resource allocation for AI workloads
"""

import os
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import deque
import heapq


class JobPriority(Enum):
    """Job priority levels"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class JobStatus(Enum):
    """Job status"""
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResourceType(Enum):
    """Resource types"""
    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"


@dataclass
class ResourceRequirements:
    """Resource requirements for a job"""
    cpu_cores: float = 1.0
    memory_gb: float = 1.0
    gpu_count: int = 0
    gpu_memory_gb: float = 0.0
    disk_gb: float = 0.0
    estimated_runtime_seconds: float = 0.0
    
    def __str__(self):
        parts = [f"CPU: {self.cpu_cores}", f"RAM: {self.memory_gb:.1f}GB"]
        if self.gpu_count > 0:
            parts.append(f"GPU: {self.gpu_count}x{self.gpu_memory_gb:.1f}GB")
        return ", ".join(parts)


@dataclass
class Job:
    """Represents a schedulable job"""
    job_id: str
    name: str
    command: str
    requirements: ResourceRequirements
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.QUEUED
    user: str = "root"
    tenant_id: str = "default"
    working_dir: str = "/"
    environment: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # Job IDs this depends on
    max_retries: int = 0
    retry_count: int = 0
    
    # Runtime info
    submitted_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_resources: Dict[str, Any] = field(default_factory=dict)
    process_id: Optional[int] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    
    @property
    def runtime_seconds(self) -> float:
        """Get runtime in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return 0.0
    
    @property
    def wait_time_seconds(self) -> float:
        """Get wait time in queue"""
        if self.started_at:
            return (self.started_at - self.submitted_at).total_seconds()
        return (datetime.now() - self.submitted_at).total_seconds()
    
    def __lt__(self, other):
        """Compare for priority queue (lower priority value = higher priority)"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.submitted_at < other.submitted_at


@dataclass
class ResourcePool:
    """Available resource pool"""
    total_cpu_cores: float
    total_memory_gb: float
    total_gpu_count: int
    total_gpu_memory_gb: float
    
    available_cpu_cores: float = 0.0
    available_memory_gb: float = 0.0
    available_gpu_ids: Set[int] = field(default_factory=set)
    available_gpu_memory_gb: float = 0.0
    
    def __post_init__(self):
        """Initialize available resources"""
        self.available_cpu_cores = self.total_cpu_cores
        self.available_memory_gb = self.total_memory_gb
        self.available_gpu_ids = set(range(self.total_gpu_count))
        self.available_gpu_memory_gb = self.total_gpu_memory_gb
    
    def can_allocate(self, requirements: ResourceRequirements) -> bool:
        """Check if requirements can be satisfied"""
        return (
            self.available_cpu_cores >= requirements.cpu_cores and
            self.available_memory_gb >= requirements.memory_gb and
            len(self.available_gpu_ids) >= requirements.gpu_count and
            self.available_gpu_memory_gb >= requirements.gpu_memory_gb * requirements.gpu_count
        )
    
    def allocate(self, requirements: ResourceRequirements) -> Dict[str, Any]:
        """Allocate resources and return allocation details"""
        if not self.can_allocate(requirements):
            raise ValueError("Insufficient resources")
        
        # Allocate CPUs
        self.available_cpu_cores -= requirements.cpu_cores
        
        # Allocate memory
        self.available_memory_gb -= requirements.memory_gb
        
        # Allocate GPUs
        allocated_gpus = []
        if requirements.gpu_count > 0:
            allocated_gpus = list(self.available_gpu_ids)[:requirements.gpu_count]
            for gpu_id in allocated_gpus:
                self.available_gpu_ids.remove(gpu_id)
            self.available_gpu_memory_gb -= requirements.gpu_memory_gb * requirements.gpu_count
        
        return {
            'cpu_cores': requirements.cpu_cores,
            'memory_gb': requirements.memory_gb,
            'gpu_ids': allocated_gpus,
            'gpu_memory_gb': requirements.gpu_memory_gb
        }
    
    def release(self, allocation: Dict[str, Any]):
        """Release allocated resources"""
        self.available_cpu_cores += allocation.get('cpu_cores', 0)
        self.available_memory_gb += allocation.get('memory_gb', 0)
        
        gpu_ids = allocation.get('gpu_ids', [])
        if gpu_ids:
            self.available_gpu_ids.update(gpu_ids)
            self.available_gpu_memory_gb += allocation.get('gpu_memory_gb', 0) * len(gpu_ids)
    
    def get_utilization(self) -> Dict[str, float]:
        """Get resource utilization percentages"""
        return {
            'cpu': ((self.total_cpu_cores - self.available_cpu_cores) / self.total_cpu_cores * 100) 
                   if self.total_cpu_cores > 0 else 0,
            'memory': ((self.total_memory_gb - self.available_memory_gb) / self.total_memory_gb * 100)
                      if self.total_memory_gb > 0 else 0,
            'gpu': ((self.total_gpu_count - len(self.available_gpu_ids)) / self.total_gpu_count * 100)
                   if self.total_gpu_count > 0 else 0
        }


class JobScheduler:
    """AI workload scheduler with priority queue and resource management"""
    
    def __init__(self, resource_pool: ResourcePool, security_manager: Optional[Any] = None, tenant_id: str = "default"):
        self.resource_pool = resource_pool
        self.job_queue: List[Job] = []  # Priority queue
        self.running_jobs: Dict[str, Job] = {}
        self.completed_jobs: Dict[str, Job] = {}
        self.failed_jobs: Dict[str, Job] = {}
        self.all_jobs: Dict[str, Job] = {}
        self.security_manager = security_manager
        self.tenant_id = tenant_id
        
        self.scheduling_enabled = True
        self.max_concurrent_jobs = 100
    
    def submit_job(self, job: Job) -> bool:
        """Submit a job to the scheduler"""
        if job.job_id in self.all_jobs:
            print(f"[SCHEDULER] Job {job.job_id} already exists")
            return False
        
        # Validate dependencies
        for dep_id in job.dependencies:
            if dep_id not in self.all_jobs:
                print(f"[SCHEDULER] Dependency {dep_id} not found")
                return False
        
        if self.security_manager:
            try:
                from kernel.security import ResourceDescriptor, ResourceType, Permission, SecurityContext, AccessLevel
                context = SecurityContext(
                    agent_id=job.user,
                    access_level=AccessLevel.STANDARD,
                    groups=set(),
                    authenticated_factors=[],
                )
                resource = ResourceDescriptor(
                    resource_type=ResourceType.SYSTEM,
                    resource_id=f"job:{job.job_id}",
                    owner_agent_id=job.user,
                )
                allowed, reason = self.security_manager.authorize(context, resource, Permission.MANAGE)
                if not allowed:
                    print(f"[SCHEDULER] Job submit denied ({reason})")
                    return False
            except Exception as e:
                print(f"[SCHEDULER] Security check failed: {e}")
                return False

        # Add to queue
        heapq.heappush(self.job_queue, job)
        self.all_jobs[job.job_id] = job
        
        print(f"[SCHEDULER] Submitted job: {job.name} ({job.priority.name})")
        print(f"[SCHEDULER]   Requirements: {job.requirements}")
        
        return True
    
    def _can_run_job(self, job: Job) -> bool:
        """Check if job can run (dependencies satisfied and resources available)"""
        # Check dependencies
        for dep_id in job.dependencies:
            dep_job = self.all_jobs.get(dep_id)
            if not dep_job or dep_job.status != JobStatus.COMPLETED:
                return False
        
        # Check resources
        return self.resource_pool.can_allocate(job.requirements)
    
    def _start_job(self, job: Job) -> bool:
        """Start a job"""
        try:
            # Allocate resources
            allocation = self.resource_pool.allocate(job.requirements)
            job.assigned_resources = allocation
            
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            
            # In a real implementation, this would actually start the process
            # For now, we simulate it
            job.process_id = os.getpid()  # Placeholder
            
            # Move to running jobs
            self.running_jobs[job.job_id] = job
            
            print(f"[SCHEDULER] Started job: {job.name}")
            print(f"[SCHEDULER]   Allocated: {allocation}")
            
            return True
            
        except Exception as e:
            print(f"[SCHEDULER] Failed to start job {job.name}: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            self.failed_jobs[job.job_id] = job
            return False
    
    def schedule(self):
        """Run scheduling cycle"""
        if not self.scheduling_enabled:
            return
        
        # Try to start jobs from queue
        started_count = 0
        
        while self.job_queue and len(self.running_jobs) < self.max_concurrent_jobs:
            # Peek at highest priority job
            if not self.job_queue:
                break
            
            job = heapq.heappop(self.job_queue)
            
            # Check if can run
            if self._can_run_job(job):
                if self._start_job(job):
                    started_count += 1
            else:
                # Put back in queue if dependencies not met
                if any(self.all_jobs.get(dep_id).status != JobStatus.COMPLETED 
                       for dep_id in job.dependencies):
                    heapq.heappush(self.job_queue, job)
                else:
                    # Resources not available, put back and stop trying
                    heapq.heappush(self.job_queue, job)
                    break
        
        if started_count > 0:
            print(f"[SCHEDULER] Started {started_count} job(s)")
    
    def complete_job(self, job_id: str, exit_code: int = 0, error: Optional[str] = None):
        """Mark a job as completed"""
        if job_id not in self.running_jobs:
            print(f"[SCHEDULER] Job {job_id} not running")
            return
        
        job = self.running_jobs[job_id]
        
        # Release resources
        self.resource_pool.release(job.assigned_resources)
        
        # Update job status
        job.completed_at = datetime.now()
        job.exit_code = exit_code
        
        if exit_code == 0 and not error:
            job.status = JobStatus.COMPLETED
            self.completed_jobs[job_id] = job
            print(f"[SCHEDULER] Completed job: {job.name} (runtime: {job.runtime_seconds:.2f}s)")
        else:
            job.status = JobStatus.FAILED
            job.error_message = error
            
            # Retry if allowed
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.QUEUED
                job.started_at = None
                job.completed_at = None
                heapq.heappush(self.job_queue, job)
                print(f"[SCHEDULER] Retrying job: {job.name} (attempt {job.retry_count + 1}/{job.max_retries + 1})")
            else:
                self.failed_jobs[job_id] = job
                print(f"[SCHEDULER] Failed job: {job.name} - {error}")
        
        # Remove from running
        del self.running_jobs[job_id]
        
        # Schedule next jobs
        self.schedule()
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = self.all_jobs.get(job_id)
        if not job:
            return False
        
        if job.status == JobStatus.RUNNING:
            # Release resources
            self.resource_pool.release(job.assigned_resources)
            del self.running_jobs[job_id]
        elif job.status == JobStatus.QUEUED:
            # Remove from queue
            self.job_queue = [j for j in self.job_queue if j.job_id != job_id]
            heapq.heapify(self.job_queue)
        
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now()
        
        print(f"[SCHEDULER] Cancelled job: {job.name}")
        return True
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a running job"""
        if job_id not in self.running_jobs:
            return False
        
        job = self.running_jobs[job_id]
        job.status = JobStatus.PAUSED
        
        print(f"[SCHEDULER] Paused job: {job.name}")
        return True
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        if job_id not in self.running_jobs:
            return False
        
        job = self.running_jobs[job_id]
        if job.status != JobStatus.PAUSED:
            return False
        
        job.status = JobStatus.RUNNING
        
        print(f"[SCHEDULER] Resumed job: {job.name}")
        return True
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            'queued': len(self.job_queue),
            'running': len(self.running_jobs),
            'completed': len(self.completed_jobs),
            'failed': len(self.failed_jobs),
            'total': len(self.all_jobs),
            'resource_utilization': self.resource_pool.get_utilization()
        }
    
    def list_jobs(self, status: Optional[JobStatus] = None) -> List[Job]:
        """List jobs with optional status filter"""
        jobs = list(self.all_jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        return sorted(jobs, key=lambda j: j.submitted_at, reverse=True)
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self.all_jobs.get(job_id)
    
    def print_summary(self):
        """Print scheduler summary"""
        stats = self.get_queue_stats()
        util = stats['resource_utilization']
        
        print("\n" + "="*80)
        print("JOB SCHEDULER SUMMARY")
        print("="*80)
        
        print(f"\nJobs:")
        print(f"  Queued:    {stats['queued']}")
        print(f"  Running:   {stats['running']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Failed:    {stats['failed']}")
        print(f"  Total:     {stats['total']}")
        
        print(f"\nResource Utilization:")
        print(f"  CPU:    {util['cpu']:.1f}%")
        print(f"  Memory: {util['memory']:.1f}%")
        print(f"  GPU:    {util['gpu']:.1f}%")
        
        print(f"\nResource Pool:")
        print(f"  CPU:    {self.resource_pool.available_cpu_cores:.1f}/{self.resource_pool.total_cpu_cores} cores")
        print(f"  Memory: {self.resource_pool.available_memory_gb:.1f}/{self.resource_pool.total_memory_gb:.1f} GB")
        print(f"  GPU:    {len(self.resource_pool.available_gpu_ids)}/{self.resource_pool.total_gpu_count} devices")
        
        if self.running_jobs:
            print(f"\nRunning Jobs:")
            print("-" * 80)
            for job in self.running_jobs.values():
                print(f"  {job.name} ({job.priority.name})")
                print(f"    Runtime: {job.runtime_seconds:.1f}s | Resources: {job.requirements}")
        
        print("\n" + "="*80 + "\n")


# Predefined job templates
class JobTemplates:
    """Predefined job templates for common AI workloads"""
    
    @staticmethod
    def training_job(name: str, model_type: str, gpu_count: int = 1) -> Job:
        """Model training job"""
        return Job(
            job_id=f"train-{model_type}-{int(time.time())}",
            name=name,
            command=f"python train.py --model {model_type}",
            requirements=ResourceRequirements(
                cpu_cores=4.0,
                memory_gb=16.0,
                gpu_count=gpu_count,
                gpu_memory_gb=8.0,
                estimated_runtime_seconds=3600
            ),
            priority=JobPriority.HIGH
        )
    
    @staticmethod
    def inference_job(name: str, batch_size: int = 32) -> Job:
        """Inference job"""
        return Job(
            job_id=f"inference-{int(time.time())}",
            name=name,
            command=f"python inference.py --batch-size {batch_size}",
            requirements=ResourceRequirements(
                cpu_cores=2.0,
                memory_gb=8.0,
                gpu_count=1,
                gpu_memory_gb=4.0,
                estimated_runtime_seconds=300
            ),
            priority=JobPriority.NORMAL
        )
    
    @staticmethod
    def data_preprocessing_job(name: str) -> Job:
        """Data preprocessing job"""
        return Job(
            job_id=f"preprocess-{int(time.time())}",
            name=name,
            command="python preprocess.py",
            requirements=ResourceRequirements(
                cpu_cores=8.0,
                memory_gb=32.0,
                gpu_count=0,
                estimated_runtime_seconds=1800
            ),
            priority=JobPriority.NORMAL
        )
    
    @staticmethod
    def hyperparameter_tuning_job(name: str, trials: int = 100) -> Job:
        """Hyperparameter tuning job"""
        return Job(
            job_id=f"tune-{int(time.time())}",
            name=name,
            command=f"python tune.py --trials {trials}",
            requirements=ResourceRequirements(
                cpu_cores=4.0,
                memory_gb=16.0,
                gpu_count=1,
                gpu_memory_gb=8.0,
                estimated_runtime_seconds=7200
            ),
            priority=JobPriority.LOW,
            max_retries=2
        )


if __name__ == "__main__":
    # Test scheduler
    pool = ResourcePool(
        total_cpu_cores=16.0,
        total_memory_gb=64.0,
        total_gpu_count=2,
        total_gpu_memory_gb=24.0
    )
    
    scheduler = JobScheduler(pool)
    
    # Submit some test jobs
    job1 = JobTemplates.training_job("Train ResNet", "resnet50", gpu_count=1)
    job2 = JobTemplates.inference_job("Batch Inference")
    job3 = JobTemplates.data_preprocessing_job("Preprocess Dataset")
    
    scheduler.submit_job(job1)
    scheduler.submit_job(job2)
    scheduler.submit_job(job3)
    
    # Run scheduling
    scheduler.schedule()
    scheduler.print_summary()
