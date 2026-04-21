"""
Hardware Detection Module for AI-OS
Detects and identifies all hardware components including CPU, GPU, TPU, and system specs
"""

import platform
import subprocess
import json
import os
import shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class ProcessorType(Enum):
    """Types of processors that can be detected"""
    CPU = "cpu"
    GPU = "gpu"
    TPU = "tpu"
    NPU = "npu"  # Neural Processing Unit
    VPU = "vpu"  # Vision Processing Unit
    UNKNOWN = "unknown"


class Vendor(Enum):
    """Hardware vendors"""
    INTEL = "intel"
    AMD = "amd"
    NVIDIA = "nvidia"
    GOOGLE = "google"
    APPLE = "apple"
    ARM = "arm"
    QUALCOMM = "qualcomm"
    UNKNOWN = "unknown"


@dataclass
class ProcessorInfo:
    """Information about a processor"""
    processor_type: ProcessorType
    vendor: Vendor
    model: str
    cores: int
    threads: int
    frequency_mhz: float
    capabilities: List[str]
    memory_gb: Optional[float] = None  # For GPUs/TPUs with dedicated memory
    compute_capability: Optional[str] = None  # For CUDA, ROCm, etc.
    pci_address: Optional[str] = None
    driver_version: Optional[str] = None
    memory_gb: Optional[float] = None
    bus_id: Optional[str] = None
    device_id: Optional[str] = None


@dataclass
class MemoryInfo:
    """System memory information"""
    total_gb: float
    available_gb: float
    used_gb: float
    swap_total_gb: float
    swap_used_gb: float


@dataclass
class StorageDevice:
    """Storage device information"""
    device_name: str
    mount_point: Optional[str]
    total_gb: float
    used_gb: float
    filesystem_type: str
    is_ssd: bool
    model: str


@dataclass
class SystemSpecs:
    """Complete system specifications"""
    hostname: str
    os_type: str
    os_version: str
    kernel_version: str
    architecture: str
    processors: List[ProcessorInfo]
    memory: MemoryInfo
    storage_devices: List[StorageDevice]
    network_interfaces: List[Dict[str, Any]]
    boot_time: str
    uptime_seconds: float


class HardwareDetector:
    """Main hardware detection class"""
    
    def __init__(self):
        self.platform_system = platform.system()
        self.detected_processors: List[ProcessorInfo] = []
        
    def detect_all(self) -> SystemSpecs:
        """Detect all hardware components and return complete system specs"""
        print("[BOOT] Initializing hardware detection...")
        
        processors = self._detect_all_processors()
        memory = self._detect_memory()
        storage = self._detect_storage()
        network = self._detect_network()
        
        specs = SystemSpecs(
            hostname=platform.node(),
            os_type=self.platform_system,
            os_version=platform.version(),
            kernel_version=platform.release(),
            architecture=platform.machine(),
            processors=processors,
            memory=memory,
            storage_devices=storage,
            network_interfaces=network,
            boot_time=self._get_boot_time(),
            uptime_seconds=self._get_uptime()
        )
        
        return specs
    
    def _detect_all_processors(self) -> List[ProcessorInfo]:
        """Detect all processors: CPU, GPU, TPU, NPU"""
        processors = []
        
        # Detect CPU(s)
        cpu_info = self._detect_cpu()
        if cpu_info:
            processors.append(cpu_info)
        
        # Detect GPU(s)
        gpus = self._detect_gpus()
        processors.extend(gpus)
        
        # Detect TPU(s)
        tpus = self._detect_tpus()
        processors.extend(tpus)
        
        # Detect NPU/VPU
        npus = self._detect_npus()
        processors.extend(npus)
        
        return processors
    
    def _detect_cpu(self) -> Optional[ProcessorInfo]:
        """Detect CPU information"""
        print("[BOOT] Detecting CPU...")
        
        try:
            if self.platform_system == "Linux":
                return self._detect_cpu_linux()
            elif self.platform_system == "Darwin":  # macOS
                return self._detect_cpu_macos()
            elif self.platform_system == "Windows":
                return self._detect_cpu_windows()
        except Exception as e:
            print(f"[WARN] CPU detection failed: {e}")
        
        return None
    
    def _detect_cpu_linux(self) -> Optional[ProcessorInfo]:
        """Detect CPU on Linux"""
        try:
            # Read /proc/cpuinfo
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
            
            # Parse CPU info
            model = None
            cores = 0
            flags = []
            frequency = 0.0
            
            for line in cpuinfo.split('\n'):
                if 'model name' in line and not model:
                    model = line.split(':')[1].strip()
                elif 'cpu cores' in line:
                    cores = int(line.split(':')[1].strip())
                elif 'flags' in line and not flags:
                    flags = line.split(':')[1].strip().split()
                elif 'cpu MHz' in line and frequency == 0:
                    frequency = float(line.split(':')[1].strip())
            
            # Count threads
            threads = cpuinfo.count('processor')
            
            # Determine vendor
            vendor = Vendor.UNKNOWN
            if model:
                model_lower = model.lower()
                if 'intel' in model_lower:
                    vendor = Vendor.INTEL
                elif 'amd' in model_lower:
                    vendor = Vendor.AMD
                elif 'apple' in model_lower:
                    vendor = Vendor.APPLE
                elif 'arm' in model_lower:
                    vendor = Vendor.ARM
            
            return ProcessorInfo(
                processor_type=ProcessorType.CPU,
                vendor=vendor,
                model=model or "Unknown CPU",
                cores=cores or threads,
                threads=threads,
                frequency_mhz=frequency,
                capabilities=flags[:20]  # First 20 flags
            )
            
        except Exception as e:
            print(f"[WARN] Linux CPU detection failed: {e}")
            return None
    
    def _detect_cpu_macos(self) -> Optional[ProcessorInfo]:
        """Detect CPU on macOS"""
        try:
            model = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
            cores = int(subprocess.check_output(['sysctl', '-n', 'hw.physicalcpu']).decode().strip())
            threads = int(subprocess.check_output(['sysctl', '-n', 'hw.logicalcpu']).decode().strip())
            freq_raw = subprocess.check_output(['sysctl', '-n', 'hw.cpufrequency']).decode().strip()
            try:
                freq = float(freq_raw) / 1e6
            except Exception:
                freq = 0.0
            
            vendor = Vendor.UNKNOWN
            if 'Intel' in model:
                vendor = Vendor.INTEL
            elif 'Apple' in model or 'M1' in model or 'M2' in model or 'M3' in model:
                vendor = Vendor.APPLE
            
            return ProcessorInfo(
                processor_type=ProcessorType.CPU,
                vendor=vendor,
                model=model,
                cores=cores,
                threads=threads,
                frequency_mhz=freq,
                capabilities=[]
            )
        except Exception as e:
            print(f"[WARN] macOS CPU detection failed: {e}")
            return None
    
    def _detect_cpu_windows(self) -> Optional[ProcessorInfo]:
        """Detect CPU on Windows"""
        try:
            model = platform.processor()
            cores = platform.cpu_count() or 0
            
            vendor = Vendor.UNKNOWN
            if 'Intel' in model:
                vendor = Vendor.INTEL
            elif 'AMD' in model:
                vendor = Vendor.AMD
            
            return ProcessorInfo(
                processor_type=ProcessorType.CPU,
                vendor=vendor,
                model=model,
                cores=cores,
                threads=cores,  # Approximation
                frequency_mhz=0.0,
                capabilities=[]
            )
        except Exception as e:
            print(f"[WARN] Windows CPU detection failed: {e}")
            return None
    
    def _detect_gpus(self) -> List[ProcessorInfo]:
        """Detect GPU(s) - NVIDIA, AMD, Intel, Apple"""
        print("[BOOT] Detecting GPUs...")
        gpus = []
        
        # Try NVIDIA GPUs
        nvidia_gpus = self._detect_nvidia_gpus()
        gpus.extend(nvidia_gpus)
        
        # Try AMD GPUs
        amd_gpus = self._detect_amd_gpus()
        gpus.extend(amd_gpus)
        
        # Try Intel GPUs
        intel_gpus = self._detect_intel_gpus()
        gpus.extend(intel_gpus)
        
        # Try Apple GPUs
        apple_gpus = self._detect_apple_gpus()
        gpus.extend(apple_gpus)
        
        return gpus
    
    def _detect_nvidia_gpus(self) -> List[ProcessorInfo]:
        """Detect NVIDIA GPUs using nvidia-smi"""
        gpus = []
        if not shutil.which('nvidia-smi') or not os.access(shutil.which('nvidia-smi'), os.X_OK):
            return gpus
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,compute_cap,driver_version,pci.bus_id',
                 '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 5:
                            gpus.append(ProcessorInfo(
                                processor_type=ProcessorType.GPU,
                                vendor=Vendor.NVIDIA,
                                model=parts[0],
                                cores=0,  # CUDA cores require different query
                                threads=0,
                                frequency_mhz=0.0,
                                memory_gb=float(parts[1]) / 1024.0,
                                compute_capability=parts[2],
                                driver_version=parts[3],
                                pci_address=parts[4],
                                capabilities=['CUDA', 'cuDNN', 'TensorRT']
                            ))
                        
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError, Exception) as e:
            print(f"[INFO] NVIDIA GPU detection: {e}")
        
        return gpus
    
    def _detect_amd_gpus(self) -> List[ProcessorInfo]:
        """Detect AMD GPUs using rocm-smi"""
        gpus = []
        if not shutil.which('rocm-smi') or not os.access(shutil.which('rocm-smi'), os.X_OK):
            return gpus
        try:
            result = subprocess.run(
                ['rocm-smi', '--showproductname'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'GPU' in line and ':' in line:
                        model = line.split(':')[1].strip()
                        gpus.append(ProcessorInfo(
                            processor_type=ProcessorType.GPU,
                            vendor=Vendor.AMD,
                            model=model,
                            cores=0,
                            threads=0,
                            frequency_mhz=0.0,
                            capabilities=['ROCm', 'HIP']
                        ))
                        
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError, Exception) as e:
            print(f"[INFO] AMD GPU detection: {e}")
        
        return gpus
    
    def _detect_intel_gpus(self) -> List[ProcessorInfo]:
        """Detect Intel GPUs"""
        gpus = []
        
        if self.platform_system == "Linux":
            try:
                result = subprocess.run(
                    ['lspci', '-v'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'VGA' in line and 'Intel' in line:
                            model = line.split(':')[-1].strip()
                            gpus.append(ProcessorInfo(
                                processor_type=ProcessorType.GPU,
                                vendor=Vendor.INTEL,
                                model=model,
                                cores=0,
                                threads=0,
                                frequency_mhz=0.0,
                                capabilities=['OneAPI', 'Level Zero']
                            ))
            except Exception as e:
                print(f"[INFO] Intel GPU detection: {e}")
        
        return gpus
    
    def _detect_apple_gpus(self) -> List[ProcessorInfo]:
        """Detect Apple Silicon GPUs"""
        gpus = []
        
        if self.platform_system == "Darwin":
            try:
                chip = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
                if any(m in chip for m in ['M1', 'M2', 'M3', 'M4']):
                    # Apple Silicon has integrated GPU
                    gpus.append(ProcessorInfo(
                        processor_type=ProcessorType.GPU,
                        vendor=Vendor.APPLE,
                        model=f"{chip} GPU",
                        cores=0,  # Varies by model
                        threads=0,
                        frequency_mhz=0.0,
                        capabilities=['Metal', 'Neural Engine']
                    ))
            except Exception as e:
                print(f"[INFO] Apple GPU detection: {e}")
        
        return gpus
    
    def _detect_tpus(self) -> List[ProcessorInfo]:
        """Detect TPUs (Google Cloud TPU)"""
        print("[BOOT] Detecting TPUs...")
        tpus = []
        
        try:
            # Check for TPU via environment or device listing
            import os
            if 'TPU_NAME' in os.environ:
                tpus.append(ProcessorInfo(
                    processor_type=ProcessorType.TPU,
                    vendor=Vendor.GOOGLE,
                    model=os.environ.get('TPU_NAME', 'Cloud TPU'),
                    cores=8,  # TPU v2/v3 typically have 8 cores
                    threads=8,
                    frequency_mhz=0.0,
                    capabilities=['TensorFlow', 'JAX', 'PyTorch/XLA']
                ))
            
            # Try to detect local Edge TPU
            if self.platform_system == "Linux":
                result = subprocess.run(
                    ['lsusb'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if 'Global Unichip Corp' in result.stdout or 'Edge TPU' in result.stdout:
                    tpus.append(ProcessorInfo(
                        processor_type=ProcessorType.TPU,
                        vendor=Vendor.GOOGLE,
                        model='Coral Edge TPU',
                        cores=1,
                        threads=1,
                        frequency_mhz=0.0,
                        capabilities=['TensorFlow Lite']
                    ))
                    
        except Exception as e:
            print(f"[INFO] TPU detection: {e}")
        
        return tpus
    
    def _detect_npus(self) -> List[ProcessorInfo]:
        """Detect NPUs/VPUs (Intel Movidius, Qualcomm, etc.)"""
        print("[BOOT] Detecting NPUs/VPUs...")
        npus = []
        
        try:
            if self.platform_system == "Linux":
                result = subprocess.run(
                    ['lsusb'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # Intel Movidius
                if 'Movidius' in result.stdout:
                    npus.append(ProcessorInfo(
                        processor_type=ProcessorType.VPU,
                        vendor=Vendor.INTEL,
                        model='Movidius VPU',
                        cores=1,
                        threads=1,
                        frequency_mhz=0.0,
                        capabilities=['OpenVINO']
                    ))
                    
        except Exception as e:
            print(f"[INFO] NPU detection: {e}")
        
        return npus
    
    def _detect_memory(self) -> MemoryInfo:
        """Detect system memory"""
        print("[BOOT] Detecting system memory...")
        
        try:
            if self.platform_system == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                
                mem_total = 0
                mem_available = 0
                swap_total = 0
                swap_free = 0
                
                for line in meminfo.split('\n'):
                    if 'MemTotal' in line:
                        mem_total = int(line.split()[1]) / 1024.0 / 1024.0  # GB
                    elif 'MemAvailable' in line:
                        mem_available = int(line.split()[1]) / 1024.0 / 1024.0
                    elif 'SwapTotal' in line:
                        swap_total = int(line.split()[1]) / 1024.0 / 1024.0
                    elif 'SwapFree' in line:
                        swap_free = int(line.split()[1]) / 1024.0 / 1024.0
                
                return MemoryInfo(
                    total_gb=mem_total,
                    available_gb=mem_available,
                    used_gb=mem_total - mem_available,
                    swap_total_gb=swap_total,
                    swap_used_gb=swap_total - swap_free
                )
                
            elif self.platform_system == "Darwin":
                mem_bytes = int(subprocess.check_output(['sysctl', '-n', 'hw.memsize']).decode().strip())
                mem_gb = mem_bytes / 1024.0 / 1024.0 / 1024.0
                
                return MemoryInfo(
                    total_gb=mem_gb,
                    available_gb=mem_gb * 0.5,  # Approximation
                    used_gb=mem_gb * 0.5,
                    swap_total_gb=0.0,
                    swap_used_gb=0.0
                )
                
        except Exception as e:
            print(f"[WARN] Memory detection failed: {e}")
        
        return MemoryInfo(0, 0, 0, 0, 0)
    
    def _detect_storage(self) -> List[StorageDevice]:
        """Detect storage devices"""
        print("[BOOT] Detecting storage devices...")
        devices = []
        
        try:
            if self.platform_system == "Linux":
                result = subprocess.run(
                    ['df', '-h', '-T'],
                    capture_output=True,
                    text=True
                )
                
                for line in result.stdout.split('\n')[1:]:
                    parts = line.split()
                    if len(parts) >= 7 and parts[0].startswith('/dev/'):
                        try:
                            total = self._parse_size(parts[2])
                            used = self._parse_size(parts[3])
                            
                            # Check if SSD
                            device_name = parts[0].split('/')[-1].rstrip('0123456789')
                            is_ssd = self._is_ssd(device_name)
                            
                            devices.append(StorageDevice(
                                device_name=parts[0],
                                mount_point=parts[6],
                                total_gb=total,
                                used_gb=used,
                                filesystem_type=parts[1],
                                is_ssd=is_ssd,
                                model=device_name
                            ))
                        except:
                            pass
                            
        except Exception as e:
            print(f"[WARN] Storage detection failed: {e}")
        
        return devices
    
    def _is_ssd(self, device_name: str) -> bool:
        """Check if device is SSD"""
        try:
            rotational_path = f'/sys/block/{device_name}/queue/rotational'
            with open(rotational_path, 'r') as f:
                return f.read().strip() == '0'
        except:
            return False
    
    def _parse_size(self, size_str: str) -> float:
        """Parse size string (e.g., '100G', '1.5T') to GB"""
        size_str = size_str.upper().replace(',', '.')
        
        multipliers = {'K': 1/1024/1024, 'M': 1/1024, 'G': 1, 'T': 1024, 'P': 1024*1024}
        
        for suffix, mult in multipliers.items():
            if suffix in size_str:
                return float(size_str.replace(suffix, '')) * mult
        
        return float(size_str)
    
    def _detect_network(self) -> List[Dict[str, Any]]:
        """Detect network interfaces"""
        print("[BOOT] Detecting network interfaces...")
        interfaces = []
        
        try:
            if self.platform_system == "Linux":
                result = subprocess.run(
                    ['ip', 'addr'],
                    capture_output=True,
                    text=True
                )
                
                current_iface = None
                for line in result.stdout.split('\n'):
                    if line and line[0].isdigit():
                        parts = line.split(':')
                        if len(parts) >= 2:
                            current_iface = {
                                'name': parts[1].strip(),
                                'addresses': []
                            }
                            interfaces.append(current_iface)
                    elif 'inet ' in line and current_iface:
                        addr = line.strip().split()[1]
                        current_iface['addresses'].append(addr)
                        
        except Exception as e:
            print(f"[WARN] Network detection failed: {e}")
        
        return interfaces
    
    def _get_boot_time(self) -> str:
        """Get system boot time"""
        try:
            if self.platform_system == "Linux":
                result = subprocess.run(
                    ['who', '-b'],
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip()
        except:
            pass
        return "Unknown"
    
    def _get_uptime(self) -> float:
        """Get system uptime in seconds"""
        try:
            if self.platform_system == "Linux":
                with open('/proc/uptime', 'r') as f:
                    return float(f.read().split()[0])
        except:
            pass
        return 0.0
    
    def print_system_report(self, specs: SystemSpecs) -> None:
        """Print a formatted system report"""
        print("\n" + "="*80)
        print("AI-OS HARDWARE DETECTION REPORT".center(80))
        print("="*80 + "\n")
        
        print(f"Hostname: {specs.hostname}")
        print(f"OS: {specs.os_type} {specs.os_version}")
        print(f"Kernel: {specs.kernel_version}")
        print(f"Architecture: {specs.architecture}")
        print(f"Boot Time: {specs.boot_time}")
        print(f"Uptime: {specs.uptime_seconds:.0f} seconds\n")
        
        print("-" * 80)
        print("PROCESSORS")
        print("-" * 80)
        
        for proc in specs.processors:
            print(f"\n[{proc.processor_type.value.upper()}] {proc.vendor.value.upper()} - {proc.model}")
            print(f"  Cores: {proc.cores} | Threads: {proc.threads} | Frequency: {proc.frequency_mhz:.0f} MHz")
            if proc.memory_gb:
                print(f"  VRAM: {proc.memory_gb:.2f} GB")
            if proc.compute_capability:
                print(f"  Compute Capability: {proc.compute_capability}")
            if proc.driver_version:
                print(f"  Driver: {proc.driver_version}")
            if proc.capabilities:
                print(f"  Capabilities: {', '.join(proc.capabilities[:10])}")
        
        print("\n" + "-" * 80)
        print("MEMORY")
        print("-" * 80)
        print(f"Total: {specs.memory.total_gb:.2f} GB")
        print(f"Used: {specs.memory.used_gb:.2f} GB")
        print(f"Available: {specs.memory.available_gb:.2f} GB")
        print(f"Swap Total: {specs.memory.swap_total_gb:.2f} GB")
        print(f"Swap Used: {specs.memory.swap_used_gb:.2f} GB")
        
        print("\n" + "-" * 80)
        print("STORAGE")
        print("-" * 80)
        for device in specs.storage_devices:
            storage_type = "SSD" if device.is_ssd else "HDD"
            print(f"\n{device.device_name} ({storage_type}) - {device.filesystem_type}")
            print(f"  Mount: {device.mount_point}")
            print(f"  Total: {device.total_gb:.2f} GB | Used: {device.used_gb:.2f} GB")
        
        print("\n" + "-" * 80)
        print("NETWORK")
        print("-" * 80)
        for iface in specs.network_interfaces:
            print(f"\n{iface['name']}")
            for addr in iface.get('addresses', []):
                print(f"  {addr}")
        
        print("\n" + "="*80 + "\n")
    
    def to_json(self, specs: SystemSpecs) -> str:
        """Export system specs to JSON"""
        def convert_enum(obj):
            if isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, list):
                return [convert_enum(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_enum(v) for k, v in obj.items()}
            elif hasattr(obj, '__dict__'):
                return convert_enum(asdict(obj))
            return obj
        
        return json.dumps(convert_enum(specs), indent=2)


if __name__ == "__main__":
    detector = HardwareDetector()
    specs = detector.detect_all()
    detector.print_system_report(specs)
    
    # Save to JSON
    with open('/tmp/system_specs.json', 'w') as f:
        f.write(detector.to_json(specs))
    print("[INFO] System specs saved to /tmp/system_specs.json")
