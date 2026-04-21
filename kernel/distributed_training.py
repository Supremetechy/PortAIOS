"""
Distributed Training Coordinator for AI-OS
Manages distributed training across multiple GPUs and nodes
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time
import json
import socket


class DistributedBackend(Enum):
    """Distributed training backends"""
    NCCL = "nccl"  # NVIDIA Collective Communications Library
    GLOO = "gloo"  # CPU/GPU
    MPI = "mpi"  # Message Passing Interface
    HOROVOD = "horovod"  # Uber's distributed training framework
    RAY = "ray"  # Ray distributed framework


class TrainingStrategy(Enum):
    """Training distribution strategies"""
    DATA_PARALLEL = "data_parallel"  # Replicate model, split data
    MODEL_PARALLEL = "model_parallel"  # Split model across devices
    PIPELINE_PARALLEL = "pipeline_parallel"  # Pipeline stages
    HYBRID = "hybrid"  # Combination of strategies
    ZERO = "zero"  # Zero Redundancy Optimizer (DeepSpeed)


class NodeRole(Enum):
    """Node roles in distributed training"""
    MASTER = "master"
    WORKER = "worker"
    PARAMETER_SERVER = "parameter_server"


@dataclass
class NodeInfo:
    """Information about a training node"""
    node_id: str
    hostname: str
    ip_address: str
    port: int
    role: NodeRole
    gpu_count: int
    rank: int
    world_size: int
    local_rank: int = 0
    
    def get_address(self) -> str:
        """Get node address"""
        return f"{self.ip_address}:{self.port}"


@dataclass
class DistributedConfig:
    """Distributed training configuration"""
    backend: DistributedBackend
    strategy: TrainingStrategy
    master_addr: str
    master_port: int
    world_size: int
    nodes: List[NodeInfo] = field(default_factory=list)
    timeout_seconds: int = 1800
    use_mixed_precision: bool = True
    gradient_accumulation_steps: int = 1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'backend': self.backend.value,
            'strategy': self.strategy.value,
            'master_addr': self.master_addr,
            'master_port': self.master_port,
            'world_size': self.world_size,
            'timeout_seconds': self.timeout_seconds,
            'use_mixed_precision': self.use_mixed_precision,
            'gradient_accumulation_steps': self.gradient_accumulation_steps
        }
    
    def get_env_vars(self, rank: int = 0) -> Dict[str, str]:
        """Get environment variables for distributed training"""
        return {
            'MASTER_ADDR': self.master_addr,
            'MASTER_PORT': str(self.master_port),
            'WORLD_SIZE': str(self.world_size),
            'RANK': str(rank),
            'LOCAL_RANK': str(rank % self._get_gpus_per_node()),
        }
    
    def _get_gpus_per_node(self) -> int:
        """Get GPUs per node (assuming uniform)"""
        if self.nodes:
            return self.nodes[0].gpu_count
        return 1


@dataclass
class TrainingJob:
    """Distributed training job"""
    job_id: str
    name: str
    config: DistributedConfig
    model_name: str
    dataset_name: str
    batch_size_per_gpu: int
    epochs: int
    checkpoint_dir: str
    
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_epoch: int = 0
    current_step: int = 0
    
    @property
    def global_batch_size(self) -> int:
        """Calculate global batch size"""
        return self.batch_size_per_gpu * self.config.world_size
    
    @property
    def runtime_seconds(self) -> float:
        """Get runtime in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0


class DistributedCoordinator:
    """Coordinates distributed training across multiple nodes"""
    
    def __init__(self):
        self.jobs: Dict[str, TrainingJob] = {}
        self.nodes: Dict[str, NodeInfo] = {}
        self.is_master = False
        self.local_node: Optional[NodeInfo] = None
        self.node_heartbeats: Dict[str, float] = {}
        self.node_status: Dict[str, str] = {}
    
    def initialize_cluster(self, node_configs: List[Dict]) -> bool:
        """Initialize cluster from node configurations"""
        print("[DISTRIBUTED] Initializing cluster...")
        
        try:
            for i, config in enumerate(node_configs):
                node = NodeInfo(
                    node_id=config.get('node_id', f"node-{i}"),
                    hostname=config['hostname'],
                    ip_address=config['ip_address'],
                    port=config.get('port', 29500),
                    role=NodeRole(config.get('role', 'worker')),
                    gpu_count=config['gpu_count'],
                    rank=config['rank'],
                    world_size=len(node_configs)
                )
                
                self.nodes[node.node_id] = node
                
                # Check if this is the current node
                if self._is_local_node(node):
                    self.local_node = node
                    self.is_master = (node.role == NodeRole.MASTER)
                    print(f"[DISTRIBUTED]   Local node: {node.node_id} (rank {node.rank})")
            
            print(f"[DISTRIBUTED] ✓ Cluster initialized with {len(self.nodes)} node(s)")
            return True
            
        except Exception as e:
            print(f"[DISTRIBUTED] ✗ Failed to initialize cluster: {e}")
            return False

    def heartbeat(self, node_id: str) -> None:
        self.node_heartbeats[node_id] = time.time()
        if node_id not in self.node_status:
            self.node_status[node_id] = "healthy"

    def set_node_status(self, node_id: str, status: str) -> None:
        self.node_status[node_id] = status

    def prune_stale_nodes(self, timeout_seconds: int = 60) -> List[str]:
        now = time.time()
        removed = []
        for node_id, ts in list(self.node_heartbeats.items()):
            if now - ts > timeout_seconds:
                removed.append(node_id)
                del self.node_heartbeats[node_id]
                self.node_status[node_id] = "stale"
        if removed:
            print(f"[DISTRIBUTED] Stale nodes: {removed}")
        return removed
    
    def _is_local_node(self, node: NodeInfo) -> bool:
        """Check if node is the local node"""
        local_hostname = socket.gethostname()
        local_ip = socket.gethostbyname(local_hostname)
        
        return node.hostname == local_hostname or node.ip_address == local_ip
    
    def create_training_job(self, 
                           name: str,
                           model_name: str,
                           dataset_name: str,
                           gpus_per_node: int,
                           num_nodes: int,
                           batch_size_per_gpu: int,
                           epochs: int,
                           backend: DistributedBackend = DistributedBackend.NCCL,
                           strategy: TrainingStrategy = TrainingStrategy.DATA_PARALLEL) -> Optional[str]:
        """Create a distributed training job"""
        
        job_id = f"train-{model_name}-{int(datetime.now().timestamp())}"
        
        # Select nodes for this job
        available_nodes = list(self.nodes.values())[:num_nodes]
        if len(available_nodes) < num_nodes:
            print(f"[DISTRIBUTED] Not enough nodes available ({len(available_nodes)} < {num_nodes})")
            return None
        
        # Configure distributed training
        master_node = available_nodes[0]
        config = DistributedConfig(
            backend=backend,
            strategy=strategy,
            master_addr=master_node.ip_address,
            master_port=master_node.port,
            world_size=num_nodes * gpus_per_node,
            nodes=available_nodes
        )
        
        # Create job
        job = TrainingJob(
            job_id=job_id,
            name=name,
            config=config,
            model_name=model_name,
            dataset_name=dataset_name,
            batch_size_per_gpu=batch_size_per_gpu,
            epochs=epochs,
            checkpoint_dir=f"/aios/var/checkpoints/{job_id}"
        )
        
        self.jobs[job_id] = job
        
        print(f"[DISTRIBUTED] Created training job: {name}")
        print(f"[DISTRIBUTED]   Job ID: {job_id}")
        print(f"[DISTRIBUTED]   Strategy: {strategy.value}")
        print(f"[DISTRIBUTED]   Nodes: {num_nodes}")
        print(f"[DISTRIBUTED]   World Size: {config.world_size}")
        print(f"[DISTRIBUTED]   Global Batch Size: {job.global_batch_size}")
        
        return job_id
    
    def start_training_job(self, job_id: str) -> bool:
        """Start a distributed training job"""
        if job_id not in self.jobs:
            print(f"[DISTRIBUTED] Job not found: {job_id}")
            return False
        
        job = self.jobs[job_id]
        
        print(f"[DISTRIBUTED] Starting training job: {job.name}")
        
        # Generate training scripts for each rank
        for node in job.config.nodes:
            for local_rank in range(node.gpu_count):
                rank = node.rank * node.gpu_count + local_rank
                self._generate_worker_script(job, rank, local_rank)
        
        job.status = "running"
        job.start_time = datetime.now()
        
        print(f"[DISTRIBUTED] ✓ Job started")
        return True
    
    def _generate_worker_script(self, job: TrainingJob, rank: int, local_rank: int):
        """Generate training script for a worker"""
        # In a real implementation, this would generate and launch actual training scripts
        # For now, we just simulate it
        
        env_vars = job.config.get_env_vars(rank)
        env_vars['LOCAL_RANK'] = str(local_rank)
        
        script = f"""
#!/bin/bash
# Training worker for {job.name} - Rank {rank}

export MASTER_ADDR={env_vars['MASTER_ADDR']}
export MASTER_PORT={env_vars['MASTER_PORT']}
export WORLD_SIZE={env_vars['WORLD_SIZE']}
export RANK={env_vars['RANK']}
export LOCAL_RANK={env_vars['LOCAL_RANK']}

# Launch training
python train.py \\
    --model {job.model_name} \\
    --dataset {job.dataset_name} \\
    --batch-size {job.batch_size_per_gpu} \\
    --epochs {job.epochs} \\
    --checkpoint-dir {job.checkpoint_dir} \\
    --backend {job.config.backend.value} \\
    --strategy {job.config.strategy.value}
"""
        
        # In production, would save and execute this script
        print(f"[DISTRIBUTED]   Generated script for rank {rank}")
    
    def stop_training_job(self, job_id: str) -> bool:
        """Stop a running training job"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        # In production, would actually stop the processes
        job.status = "stopped"
        job.end_time = datetime.now()
        
        print(f"[DISTRIBUTED] Stopped training job: {job.name}")
        return True
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get training job status"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        
        return {
            'job_id': job.job_id,
            'name': job.name,
            'status': job.status,
            'current_epoch': job.current_epoch,
            'total_epochs': job.epochs,
            'runtime_seconds': job.runtime_seconds,
            'world_size': job.config.world_size,
            'global_batch_size': job.global_batch_size
        }
    
    def list_jobs(self) -> List[Dict]:
        """List all training jobs"""
        return [self.get_job_status(job_id) for job_id in self.jobs.keys()]
    
    def get_pytorch_config(self, job_id: str) -> Optional[Dict]:
        """Get PyTorch distributed configuration"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        
        return {
            'init_method': f'tcp://{job.config.master_addr}:{job.config.master_port}',
            'backend': job.config.backend.value,
            'world_size': job.config.world_size,
            'timeout': job.config.timeout_seconds
        }
    
    def get_tensorflow_config(self, job_id: str) -> Optional[Dict]:
        """Get TensorFlow distributed configuration"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        
        # Build cluster spec
        cluster_spec = {
            'worker': [node.get_address() for node in job.config.nodes]
        }
        
        return {
            'cluster': cluster_spec,
            'task': {'type': 'worker', 'index': 0},
            'protocol': 'grpc'
        }
    
    def print_summary(self):
        """Print distributed coordinator summary"""
        print("\n" + "="*80)
        print("DISTRIBUTED TRAINING COORDINATOR")
        print("="*80)
        
        print(f"\nCluster Nodes: {len(self.nodes)}")
        for node in self.nodes.values():
            marker = " (LOCAL)" if node == self.local_node else ""
            print(f"  {node.node_id}: {node.hostname} - {node.gpu_count} GPU(s) - Rank {node.rank}{marker}")
        
        print(f"\nTraining Jobs: {len(self.jobs)}")
        if self.jobs:
            print("-" * 80)
            for job in self.jobs.values():
                print(f"  {job.name} ({job.status})")
                print(f"    Strategy: {job.config.strategy.value}")
                print(f"    World Size: {job.config.world_size}")
                print(f"    Epoch: {job.current_epoch}/{job.epochs}")
                if job.start_time:
                    print(f"    Runtime: {job.runtime_seconds:.1f}s")
        
        print("\n" + "="*80 + "\n")


# Helper functions for common distributed training setups

def create_single_node_config(hostname: str = None, gpu_count: int = 1) -> List[Dict]:
    """Create configuration for single-node training"""
    if hostname is None:
        hostname = socket.gethostname()
    
    ip_address = socket.gethostbyname(hostname)
    
    return [{
        'node_id': 'node-0',
        'hostname': hostname,
        'ip_address': ip_address,
        'port': 29500,
        'role': 'master',
        'gpu_count': gpu_count,
        'rank': 0
    }]


def create_multi_node_config(nodes: List[Tuple[str, int]]) -> List[Dict]:
    """
    Create configuration for multi-node training
    
    Args:
        nodes: List of (hostname, gpu_count) tuples
    """
    configs = []
    
    for rank, (hostname, gpu_count) in enumerate(nodes):
        try:
            ip_address = socket.gethostbyname(hostname)
        except:
            ip_address = hostname  # Assume it's already an IP
        
        configs.append({
            'node_id': f'node-{rank}',
            'hostname': hostname,
            'ip_address': ip_address,
            'port': 29500 + rank,
            'role': 'master' if rank == 0 else 'worker',
            'gpu_count': gpu_count,
            'rank': rank
        })
    
    return configs


# Example training configurations

class TrainingTemplates:
    """Predefined training configuration templates"""
    
    @staticmethod
    def llm_pretraining(model_size: str = "7B", num_gpus: int = 8):
        """LLM pre-training configuration"""
        batch_sizes = {
            "1B": 32,
            "7B": 8,
            "13B": 4,
            "70B": 1
        }
        
        return {
            'model_name': f'llm-{model_size}',
            'dataset_name': 'common_crawl',
            'batch_size_per_gpu': batch_sizes.get(model_size, 4),
            'epochs': 1,
            'strategy': TrainingStrategy.ZERO,
            'backend': DistributedBackend.NCCL,
            'num_nodes': max(1, num_gpus // 8),
            'gpus_per_node': min(8, num_gpus)
        }
    
    @staticmethod
    def computer_vision_training(model_name: str = "resnet50", num_gpus: int = 4):
        """Computer vision training configuration"""
        return {
            'model_name': model_name,
            'dataset_name': 'imagenet',
            'batch_size_per_gpu': 128,
            'epochs': 90,
            'strategy': TrainingStrategy.DATA_PARALLEL,
            'backend': DistributedBackend.NCCL,
            'num_nodes': 1,
            'gpus_per_node': num_gpus
        }
    
    @staticmethod
    def fine_tuning(model_name: str, dataset_name: str, num_gpus: int = 2):
        """Fine-tuning configuration"""
        return {
            'model_name': model_name,
            'dataset_name': dataset_name,
            'batch_size_per_gpu': 16,
            'epochs': 10,
            'strategy': TrainingStrategy.DATA_PARALLEL,
            'backend': DistributedBackend.NCCL,
            'num_nodes': 1,
            'gpus_per_node': num_gpus
        }


if __name__ == "__main__":
    # Test distributed coordinator
    coordinator = DistributedCoordinator()
    
    # Single node configuration
    config = create_single_node_config(gpu_count=2)
    coordinator.initialize_cluster(config)
    
    # Create training job
    job_id = coordinator.create_training_job(
        name="ResNet-50 Training",
        model_name="resnet50",
        dataset_name="imagenet",
        gpus_per_node=2,
        num_nodes=1,
        batch_size_per_gpu=128,
        epochs=90
    )
    
    coordinator.print_summary()
