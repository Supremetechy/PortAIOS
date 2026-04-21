"""
Container Runtime Support for AI-OS
Integrates with Docker and Podman for containerized AI workloads
"""

import subprocess
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ContainerRuntime(Enum):
    """Supported container runtimes"""
    DOCKER = "docker"
    PODMAN = "podman"
    CONTAINERD = "containerd"
    NONE = "none"


class ContainerStatus(Enum):
    """Container status"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    EXITED = "exited"
    CREATED = "created"
    UNKNOWN = "unknown"


@dataclass
class ContainerImage:
    """Container image information"""
    repository: str
    tag: str
    image_id: str
    created: datetime
    size_mb: float
    
    @property
    def full_name(self) -> str:
        return f"{self.repository}:{self.tag}"


@dataclass
class GPUConfig:
    """GPU configuration for containers"""
    enabled: bool = False
    device_ids: List[int] = field(default_factory=list)  # Specific GPU IDs
    capabilities: List[str] = field(default_factory=lambda: ["compute", "utility"])
    runtime: str = "nvidia"  # nvidia, rocm, etc.


@dataclass
class ContainerConfig:
    """Container configuration"""
    name: str
    image: str
    command: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    volumes: Dict[str, str] = field(default_factory=dict)  # host_path: container_path
    ports: Dict[int, int] = field(default_factory=dict)  # host_port: container_port
    gpu_config: Optional[GPUConfig] = None
    memory_limit_gb: Optional[float] = None
    cpu_limit: Optional[float] = None  # Number of CPUs
    network: str = "bridge"
    auto_remove: bool = False
    detach: bool = True


@dataclass
class Container:
    """Running container information"""
    container_id: str
    name: str
    image: str
    status: ContainerStatus
    created: datetime
    ports: Dict[str, str]
    labels: Dict[str, str]
    
    @property
    def short_id(self) -> str:
        return self.container_id[:12]


class ContainerManager:
    """Manages container runtime operations"""
    
    def __init__(self, security_manager: Optional[Any] = None):
        self.runtime = self._detect_runtime()
        self.runtime_version: Optional[str] = None
        self.security_manager = security_manager
        
        if self.runtime != ContainerRuntime.NONE:
            self.runtime_version = self._get_runtime_version()
    
    def _detect_runtime(self) -> ContainerRuntime:
        """Detect available container runtime"""
        print("[CONTAINER] Detecting container runtime...")
        
        # Try Docker
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("[CONTAINER]   Found Docker")
                return ContainerRuntime.DOCKER
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Try Podman
        try:
            result = subprocess.run(
                ['podman', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("[CONTAINER]   Found Podman")
                return ContainerRuntime.PODMAN
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        print("[CONTAINER]   No container runtime found")
        return ContainerRuntime.NONE

    def is_kubernetes_available(self) -> bool:
        try:
            result = subprocess.run(['kubectl', 'version', '--client'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def deploy_k8s_manifest(self, manifest_path: str) -> bool:
        """Deploy a Kubernetes manifest using kubectl"""
        if not self.is_kubernetes_available():
            print("[CONTAINER] Kubernetes client not available")
            return False
        try:
            result = subprocess.run(['kubectl', 'apply', '-f', manifest_path], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"[CONTAINER] ✓ Applied manifest {manifest_path}")
                return True
            print(f"[CONTAINER] ✗ kubectl apply failed: {result.stderr}")
            return False
        except Exception as e:
            print(f"[CONTAINER] ✗ kubectl error: {e}")
            return False
    
    def _get_runtime_version(self) -> str:
        """Get runtime version"""
        try:
            cmd = [self.runtime.value, '--version']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "Unknown"
    
    def is_available(self) -> bool:
        """Check if container runtime is available"""
        return self.runtime != ContainerRuntime.NONE
    
    def pull_image(self, image: str) -> bool:
        """Pull container image"""
        if not self.is_available():
            print("[CONTAINER] No runtime available")
            return False
        
        print(f"[CONTAINER] Pulling image: {image}")
        
        try:
            cmd = [self.runtime.value, 'pull', image]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"[CONTAINER]   ✓ Pulled {image}")
                return True
            else:
                print(f"[CONTAINER]   ✗ Failed to pull {image}: {result.stderr}")
                return False
        except Exception as e:
            print(f"[CONTAINER]   ✗ Error: {e}")
            return False
    
    def list_images(self) -> List[ContainerImage]:
        """List available images"""
        if not self.is_available():
            return []
        
        images = []
        
        try:
            cmd = [self.runtime.value, 'images', '--format', '{{json .}}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        data = json.loads(line)
                        
                        # Parse size (could be in MB, GB)
                        size_str = data.get('Size', '0B')
                        size_mb = self._parse_size_to_mb(size_str)
                        
                        images.append(ContainerImage(
                            repository=data.get('Repository', ''),
                            tag=data.get('Tag', ''),
                            image_id=data.get('ID', ''),
                            created=datetime.now(),  # Could parse CreatedAt
                            size_mb=size_mb
                        ))
        except Exception as e:
            print(f"[CONTAINER] Error listing images: {e}")
        
        return images
    
    def _parse_size_to_mb(self, size_str: str) -> float:
        """Parse size string to MB"""
        try:
            size_str = size_str.strip().upper()
            
            if 'GB' in size_str:
                return float(size_str.replace('GB', '')) * 1024
            elif 'MB' in size_str:
                return float(size_str.replace('MB', ''))
            elif 'KB' in size_str:
                return float(size_str.replace('KB', '')) / 1024
            else:
                return 0.0
        except:
            return 0.0
    
    def create_container(self, config: ContainerConfig) -> Optional[str]:
        """Create and optionally start a container"""
        if not self.is_available():
            print("[CONTAINER] No runtime available")
            return None
        
        print(f"[CONTAINER] Creating container: {config.name}")

        if self.security_manager:
            try:
                from kernel.security import ResourceDescriptor, ResourceType, Permission, SecurityContext, AccessLevel
                context = SecurityContext(
                    agent_id="system",
                    access_level=AccessLevel.ADMIN,
                    groups={"system"},
                    authenticated_factors=[],
                )
                resource = ResourceDescriptor(
                    resource_type=ResourceType.SYSTEM,
                    resource_id=f"container:{config.name}",
                    owner_agent_id="system",
                )
                allowed, reason = self.security_manager.authorize(context, resource, Permission.MANAGE)
                if not allowed:
                    print(f"[CONTAINER] Create denied ({reason})")
                    return None
            except Exception as e:
                print(f"[CONTAINER] Security check failed: {e}")
                return None
        
        # Build command
        cmd = [self.runtime.value, 'run']
        
        # Add name
        cmd.extend(['--name', config.name])
        
        # Detach mode
        if config.detach:
            cmd.append('-d')
        
        # Auto remove
        if config.auto_remove:
            cmd.append('--rm')
        
        # Environment variables
        for key, value in config.environment.items():
            cmd.extend(['-e', f'{key}={value}'])
        
        # Volumes
        for host_path, container_path in config.volumes.items():
            cmd.extend(['-v', f'{host_path}:{container_path}'])
        
        # Ports
        for host_port, container_port in config.ports.items():
            cmd.extend(['-p', f'{host_port}:{container_port}'])
        
        # GPU support
        if config.gpu_config and config.gpu_config.enabled:
            if self.runtime == ContainerRuntime.DOCKER:
                cmd.append('--gpus')
                if config.gpu_config.device_ids:
                    gpu_ids = ','.join(map(str, config.gpu_config.device_ids))
                    cmd.append(f'"device={gpu_ids}"')
                else:
                    cmd.append('all')
        
        # Memory limit
        if config.memory_limit_gb:
            memory_mb = int(config.memory_limit_gb * 1024)
            cmd.extend(['--memory', f'{memory_mb}m'])
        
        # CPU limit
        if config.cpu_limit:
            cmd.extend(['--cpus', str(config.cpu_limit)])
        
        # Network
        cmd.extend(['--network', config.network])
        
        # Image
        cmd.append(config.image)
        
        # Command
        if config.command:
            cmd.extend(config.command.split())
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                container_id = result.stdout.strip()
                print(f"[CONTAINER]   ✓ Created container: {container_id[:12]}")
                return container_id
            else:
                print(f"[CONTAINER]   ✗ Failed: {result.stderr}")
                return None
        except Exception as e:
            print(f"[CONTAINER]   ✗ Error: {e}")
            return None
    
    def list_containers(self, all_containers: bool = False) -> List[Container]:
        """List containers"""
        if not self.is_available():
            return []
        
        containers = []
        
        try:
            cmd = [self.runtime.value, 'ps', '--format', '{{json .}}']
            if all_containers:
                cmd.append('-a')
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        data = json.loads(line)
                        
                        # Parse status
                        status_str = data.get('State', data.get('Status', '')).lower()
                        status = ContainerStatus.UNKNOWN
                        for s in ContainerStatus:
                            if s.value in status_str:
                                status = s
                                break
                        
                        containers.append(Container(
                            container_id=data.get('ID', ''),
                            name=data.get('Names', ''),
                            image=data.get('Image', ''),
                            status=status,
                            created=datetime.now(),
                            ports={},
                            labels={}
                        ))
        except Exception as e:
            print(f"[CONTAINER] Error listing containers: {e}")
        
        return containers
    
    def start_container(self, container_id: str) -> bool:
        """Start a container"""
        if not self.is_available():
            return False
        
        try:
            cmd = [self.runtime.value, 'start', container_id]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"[CONTAINER]   ✓ Started container: {container_id[:12]}")
                return True
            else:
                print(f"[CONTAINER]   ✗ Failed to start: {result.stderr}")
                return False
        except Exception as e:
            print(f"[CONTAINER]   ✗ Error: {e}")
            return False
    
    def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """Stop a container"""
        if not self.is_available():
            return False

        if self.security_manager:
            try:
                from kernel.security import ResourceDescriptor, ResourceType, Permission, SecurityContext, AccessLevel
                context = SecurityContext(
                    agent_id="system",
                    access_level=AccessLevel.ADMIN,
                    groups={"system"},
                    authenticated_factors=[],
                )
                resource = ResourceDescriptor(
                    resource_type=ResourceType.SYSTEM,
                    resource_id=f"container:{container_id}",
                    owner_agent_id="system",
                )
                allowed, reason = self.security_manager.authorize(context, resource, Permission.MANAGE)
                if not allowed:
                    print(f"[CONTAINER] Stop denied ({reason})")
                    return False
            except Exception as e:
                print(f"[CONTAINER] Security check failed: {e}")
                return False
        
        try:
            cmd = [self.runtime.value, 'stop', '-t', str(timeout), container_id]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            
            if result.returncode == 0:
                print(f"[CONTAINER]   ✓ Stopped container: {container_id[:12]}")
                return True
            else:
                print(f"[CONTAINER]   ✗ Failed to stop: {result.stderr}")
                return False
        except Exception as e:
            print(f"[CONTAINER]   ✗ Error: {e}")
            return False
    
    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a container"""
        if not self.is_available():
            return False
        
        try:
            cmd = [self.runtime.value, 'rm']
            if force:
                cmd.append('-f')
            cmd.append(container_id)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"[CONTAINER]   ✓ Removed container: {container_id[:12]}")
                return True
            else:
                print(f"[CONTAINER]   ✗ Failed to remove: {result.stderr}")
                return False
        except Exception as e:
            print(f"[CONTAINER]   ✗ Error: {e}")
            return False
    
    def exec_in_container(self, container_id: str, command: str) -> Optional[str]:
        """Execute command in container"""
        if not self.is_available():
            return None
        
        try:
            cmd = [self.runtime.value, 'exec', container_id] + command.split()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"[CONTAINER]   ✗ Exec failed: {result.stderr}")
                return None
        except Exception as e:
            print(f"[CONTAINER]   ✗ Error: {e}")
            return None
    
    def get_container_logs(self, container_id: str, tail: int = 100) -> Optional[str]:
        """Get container logs"""
        if not self.is_available():
            return None
        
        try:
            cmd = [self.runtime.value, 'logs', '--tail', str(tail), container_id]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return result.stdout
            else:
                return None
        except Exception as e:
            print(f"[CONTAINER]   ✗ Error: {e}")
            return None


# Predefined AI container configurations
class AIContainerTemplates:
    """Predefined container templates for AI workloads"""
    
    @staticmethod
    def pytorch_jupyter(gpu_enabled: bool = False) -> ContainerConfig:
        """PyTorch with Jupyter Notebook"""
        gpu_config = GPUConfig(enabled=gpu_enabled) if gpu_enabled else None
        
        return ContainerConfig(
            name="pytorch-jupyter",
            image="pytorch/pytorch:latest",
            command="jupyter notebook --ip=0.0.0.0 --no-browser --allow-root",
            ports={8888: 8888},
            gpu_config=gpu_config,
            environment={
                'JUPYTER_ENABLE_LAB': 'yes'
            }
        )
    
    @staticmethod
    def tensorflow_serving(model_path: str, gpu_enabled: bool = False) -> ContainerConfig:
        """TensorFlow Serving"""
        gpu_config = GPUConfig(enabled=gpu_enabled) if gpu_enabled else None
        
        return ContainerConfig(
            name="tf-serving",
            image="tensorflow/serving:latest",
            ports={8501: 8501},
            volumes={model_path: '/models/model'},
            gpu_config=gpu_config,
            environment={
                'MODEL_NAME': 'model'
            }
        )
    
    @staticmethod
    def mlflow_server() -> ContainerConfig:
        """MLflow Tracking Server"""
        return ContainerConfig(
            name="mlflow-server",
            image="ghcr.io/mlflow/mlflow:latest",
            command="mlflow server --host 0.0.0.0",
            ports={5000: 5000}
        )
    
    @staticmethod
    def ray_cluster(gpu_enabled: bool = False) -> ContainerConfig:
        """Ray cluster head node"""
        gpu_config = GPUConfig(enabled=gpu_enabled) if gpu_enabled else None
        
        return ContainerConfig(
            name="ray-head",
            image="rayproject/ray:latest",
            command="ray start --head --port=6379 --dashboard-host=0.0.0.0 --block",
            ports={8265: 8265, 6379: 6379},
            gpu_config=gpu_config
        )


if __name__ == "__main__":
    # Test container manager
    manager = ContainerManager()
    
    if manager.is_available():
        print(f"\n[CONTAINER] Runtime: {manager.runtime.value}")
        print(f"[CONTAINER] Version: {manager.runtime_version}\n")
        
        # List images
        images = manager.list_images()
        print(f"[CONTAINER] Found {len(images)} image(s)")
        
        # List containers
        containers = manager.list_containers(all_containers=True)
        print(f"[CONTAINER] Found {len(containers)} container(s)")
    else:
        print("[CONTAINER] No container runtime available")
