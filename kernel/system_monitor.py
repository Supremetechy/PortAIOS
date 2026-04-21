"""
System Monitoring and Resource Management for AI-OS
Tracks CPU, GPU, memory, and disk usage in real-time
"""

import time
import subprocess
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CPUStats:
    """CPU usage statistics"""
    usage_percent: float
    user_percent: float
    system_percent: float
    idle_percent: float
    iowait_percent: float
    load_average_1min: float
    load_average_5min: float
    load_average_15min: float
    core_count: int
    thread_count: int
    frequency_mhz: float
    temperature_celsius: Optional[float] = None


@dataclass
class GPUStats:
    """GPU usage statistics"""
    gpu_id: int
    name: str
    usage_percent: float
    memory_used_mb: float
    memory_total_mb: float
    memory_percent: float
    temperature_celsius: Optional[float]
    power_usage_watts: Optional[float]
    power_limit_watts: Optional[float]
    fan_speed_percent: Optional[float]
    compute_processes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_gb: float
    used_gb: float
    available_gb: float
    cached_gb: float
    buffers_gb: float
    swap_total_gb: float
    swap_used_gb: float
    usage_percent: float


@dataclass
class DiskStats:
    """Disk usage statistics"""
    device: str
    mount_point: str
    total_gb: float
    used_gb: float
    available_gb: float
    usage_percent: float
    read_mb: float
    write_mb: float
    io_percent: float


@dataclass
class NetworkStats:
    """Network usage statistics"""
    interface: str
    rx_mb: float
    tx_mb: float
    rx_packets: int
    tx_packets: int
    rx_errors: int
    tx_errors: int


@dataclass
class SystemSnapshot:
    """Complete system resource snapshot"""
    timestamp: datetime
    uptime_seconds: float
    cpu_stats: CPUStats
    gpu_stats: List[GPUStats]
    memory_stats: MemoryStats
    disk_stats: List[DiskStats]
    network_stats: List[NetworkStats]
    process_count: int
    thread_count: int


class SystemMonitor:
    """Real-time system monitoring"""
    
    def __init__(self):
        self.history: List[SystemSnapshot] = []
        self.max_history = 100
        self._last_hardware_snapshot: Optional[Dict[str, Any]] = None
        
    def get_snapshot(self) -> SystemSnapshot:
        """Get current system snapshot"""
        return SystemSnapshot(
            timestamp=datetime.now(),
            uptime_seconds=self._get_uptime(),
            cpu_stats=self._get_cpu_stats(),
            gpu_stats=self._get_gpu_stats(),
            memory_stats=self._get_memory_stats(),
            disk_stats=self._get_disk_stats(),
            network_stats=self._get_network_stats(),
            process_count=self._get_process_count(),
            thread_count=self._get_thread_count()
        )

    def check_hotplug(self) -> Dict[str, Any]:
        """Detect hardware changes between scans"""
        try:
            from kernel.hardware_detection import HardwareDetector
            detector = HardwareDetector()
            specs = detector.detect_all()
            current = {
                "processors": [p.model for p in specs.processors],
                "storage_devices": [d.device_name for d in specs.storage_devices],
                "network_interfaces": [i["name"] for i in specs.network_interfaces],
            }
            if self._last_hardware_snapshot is None:
                self._last_hardware_snapshot = current
                return {"added": {}, "removed": {}}

            added = {
                k: [x for x in current[k] if x not in self._last_hardware_snapshot.get(k, [])]
                for k in current
            }
            removed = {
                k: [x for x in self._last_hardware_snapshot.get(k, []) if x not in current.get(k, [])]
                for k in current
            }
            self._last_hardware_snapshot = current
            return {"added": added, "removed": removed}
        except Exception as e:
            return {"error": str(e)}
    
    def _get_uptime(self) -> float:
        """Get system uptime in seconds"""
        try:
            with open('/proc/uptime', 'r') as f:
                return float(f.read().split()[0])
        except:
            return 0.0
    
    def _get_cpu_stats(self) -> CPUStats:
        """Get CPU statistics"""
        try:
            if not os.path.exists('/proc/stat'):
                raise FileNotFoundError("/proc/stat not available")
            # Read /proc/stat for CPU usage
            with open('/proc/stat', 'r') as f:
                cpu_line = f.readline()
                cpu_values = [float(x) for x in cpu_line.split()[1:]]
            
            user = cpu_values[0]
            system = cpu_values[2]
            idle = cpu_values[3]
            iowait = cpu_values[4] if len(cpu_values) > 4 else 0
            
            total = sum(cpu_values)
            
            usage = ((total - idle) / total * 100) if total > 0 else 0
            
            # Get load averages
            with open('/proc/loadavg', 'r') as f:
                loads = f.read().split()[:3]
                load_1, load_5, load_15 = [float(x) for x in loads]
            
            # Get CPU count
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read()
                cores = cpuinfo.count('processor')
            
            # Try to get CPU frequency
            freq = 0.0
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'cpu MHz' in line:
                            freq = float(line.split(':')[1].strip())
                            break
            except:
                pass
            
            # Try to get temperature
            temp = None
            try:
                result = subprocess.run(
                    ['cat', '/sys/class/thermal/thermal_zone0/temp'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0:
                    temp = float(result.stdout.strip()) / 1000.0
            except:
                pass
            
            return CPUStats(
                usage_percent=usage,
                user_percent=(user / total * 100) if total > 0 else 0,
                system_percent=(system / total * 100) if total > 0 else 0,
                idle_percent=(idle / total * 100) if total > 0 else 0,
                iowait_percent=(iowait / total * 100) if total > 0 else 0,
                load_average_1min=load_1,
                load_average_5min=load_5,
                load_average_15min=load_15,
                core_count=cores,
                thread_count=cores,
                frequency_mhz=freq,
                temperature_celsius=temp
            )
            
        except Exception as e:
            print(f"[MONITOR] Warning: CPU stats failed: {e}")
            return CPUStats(0, 0, 0, 100, 0, 0, 0, 0, 0, 0, 0)
    
    def _get_gpu_stats(self) -> List[GPUStats]:
        """Get GPU statistics"""
        gpus = []
        
        try:
            # Try NVIDIA GPUs
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit,fan.speed',
                 '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 9:
                            gpus.append(GPUStats(
                                gpu_id=int(parts[0]),
                                name=parts[1],
                                usage_percent=float(parts[2]) if parts[2] != '[N/A]' else 0,
                                memory_used_mb=float(parts[3]) if parts[3] != '[N/A]' else 0,
                                memory_total_mb=float(parts[4]) if parts[4] != '[N/A]' else 0,
                                memory_percent=(float(parts[3]) / float(parts[4]) * 100) if parts[3] != '[N/A]' and parts[4] != '[N/A]' else 0,
                                temperature_celsius=float(parts[5]) if parts[5] != '[N/A]' else None,
                                power_usage_watts=float(parts[6]) if parts[6] != '[N/A]' else None,
                                power_limit_watts=float(parts[7]) if parts[7] != '[N/A]' else None,
                                fan_speed_percent=float(parts[8]) if parts[8] != '[N/A]' else None
                            ))
        except Exception as e:
            pass
        
        return gpus
    
    def _get_memory_stats(self) -> MemoryStats:
        """Get memory statistics"""
        try:
            if not os.path.exists('/proc/meminfo'):
                raise FileNotFoundError("/proc/meminfo not available")
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = int(parts[1].strip().split()[0])  # KB
                        meminfo[key] = value
            
            total_gb = meminfo.get('MemTotal', 0) / 1024.0 / 1024.0
            available_gb = meminfo.get('MemAvailable', 0) / 1024.0 / 1024.0
            cached_gb = meminfo.get('Cached', 0) / 1024.0 / 1024.0
            buffers_gb = meminfo.get('Buffers', 0) / 1024.0 / 1024.0
            swap_total_gb = meminfo.get('SwapTotal', 0) / 1024.0 / 1024.0
            swap_free_gb = meminfo.get('SwapFree', 0) / 1024.0 / 1024.0
            
            used_gb = total_gb - available_gb
            swap_used_gb = swap_total_gb - swap_free_gb
            usage_percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
            
            return MemoryStats(
                total_gb=total_gb,
                used_gb=used_gb,
                available_gb=available_gb,
                cached_gb=cached_gb,
                buffers_gb=buffers_gb,
                swap_total_gb=swap_total_gb,
                swap_used_gb=swap_used_gb,
                usage_percent=usage_percent
            )
            
        except Exception as e:
            print(f"[MONITOR] Warning: Memory stats failed: {e}")
            return MemoryStats(0, 0, 0, 0, 0, 0, 0, 0)
    
    def _get_disk_stats(self) -> List[DiskStats]:
        """Get disk statistics"""
        disks = []
        
        try:
            result = subprocess.run(
                ['df', '-B1'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 6 and parts[0].startswith('/dev/'):
                        device = parts[0]
                        total_gb = int(parts[1]) / (1024**3)
                        used_gb = int(parts[2]) / (1024**3)
                        available_gb = int(parts[3]) / (1024**3)
                        usage_percent = float(parts[4].rstrip('%'))
                        mount_point = parts[5]
                        
                        disks.append(DiskStats(
                            device=device,
                            mount_point=mount_point,
                            total_gb=total_gb,
                            used_gb=used_gb,
                            available_gb=available_gb,
                            usage_percent=usage_percent,
                            read_mb=0,
                            write_mb=0,
                            io_percent=0
                        ))
        except Exception as e:
            pass
        
        return disks
    
    def _get_network_stats(self) -> List[NetworkStats]:
        """Get network statistics"""
        stats = []
        
        try:
            with open('/proc/net/dev', 'r') as f:
                lines = f.readlines()[2:]  # Skip header
                
                for line in lines:
                    parts = line.split(':')
                    if len(parts) == 2:
                        iface = parts[0].strip()
                        values = parts[1].split()
                        
                        if len(values) >= 16:
                            rx_bytes = int(values[0])
                            rx_packets = int(values[1])
                            rx_errors = int(values[2])
                            tx_bytes = int(values[8])
                            tx_packets = int(values[9])
                            tx_errors = int(values[10])
                            
                            stats.append(NetworkStats(
                                interface=iface,
                                rx_mb=rx_bytes / (1024 * 1024),
                                tx_mb=tx_bytes / (1024 * 1024),
                                rx_packets=rx_packets,
                                tx_packets=tx_packets,
                                rx_errors=rx_errors,
                                tx_errors=tx_errors
                            ))
        except Exception as e:
            pass
        
        return stats
    
    def _get_process_count(self) -> int:
        """Get number of running processes"""
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return len(result.stdout.strip().split('\n')) - 1
        except:
            pass
        return 0
    
    def _get_thread_count(self) -> int:
        """Get total number of threads"""
        try:
            with open('/proc/stat', 'r') as f:
                for line in f:
                    if line.startswith('processes'):
                        return int(line.split()[1])
        except:
            pass
        return 0
    
    def print_snapshot(self, snapshot: SystemSnapshot):
        """Print formatted system snapshot"""
        print("\n" + "="*80)
        print(f"SYSTEM SNAPSHOT - {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Uptime
        uptime_hours = snapshot.uptime_seconds / 3600
        print(f"\nUptime: {uptime_hours:.2f} hours")
        print(f"Processes: {snapshot.process_count}")
        
        # CPU
        print(f"\n[CPU]")
        print(f"  Usage: {snapshot.cpu_stats.usage_percent:.1f}%")
        print(f"  Load Average: {snapshot.cpu_stats.load_average_1min:.2f}, {snapshot.cpu_stats.load_average_5min:.2f}, {snapshot.cpu_stats.load_average_15min:.2f}")
        print(f"  Cores: {snapshot.cpu_stats.core_count} | Frequency: {snapshot.cpu_stats.frequency_mhz:.0f} MHz")
        if snapshot.cpu_stats.temperature_celsius:
            print(f"  Temperature: {snapshot.cpu_stats.temperature_celsius:.1f}°C")
        
        # GPU
        if snapshot.gpu_stats:
            print(f"\n[GPU] - {len(snapshot.gpu_stats)} device(s)")
            for gpu in snapshot.gpu_stats:
                print(f"  GPU {gpu.gpu_id}: {gpu.name}")
                print(f"    Usage: {gpu.usage_percent:.1f}% | Memory: {gpu.memory_percent:.1f}% ({gpu.memory_used_mb:.0f}/{gpu.memory_total_mb:.0f} MB)")
                if gpu.temperature_celsius:
                    print(f"    Temperature: {gpu.temperature_celsius:.1f}°C", end='')
                if gpu.power_usage_watts:
                    print(f" | Power: {gpu.power_usage_watts:.1f}W", end='')
                if gpu.fan_speed_percent:
                    print(f" | Fan: {gpu.fan_speed_percent:.0f}%", end='')
                print()
        
        # Memory
        print(f"\n[MEMORY]")
        print(f"  Total: {snapshot.memory_stats.total_gb:.2f} GB")
        print(f"  Used: {snapshot.memory_stats.used_gb:.2f} GB ({snapshot.memory_stats.usage_percent:.1f}%)")
        print(f"  Available: {snapshot.memory_stats.available_gb:.2f} GB")
        print(f"  Cached: {snapshot.memory_stats.cached_gb:.2f} GB")
        if snapshot.memory_stats.swap_total_gb > 0:
            print(f"  Swap: {snapshot.memory_stats.swap_used_gb:.2f}/{snapshot.memory_stats.swap_total_gb:.2f} GB")
        
        # Disk
        if snapshot.disk_stats:
            print(f"\n[DISK]")
            for disk in snapshot.disk_stats[:5]:  # Show first 5
                print(f"  {disk.mount_point}: {disk.used_gb:.1f}/{disk.total_gb:.1f} GB ({disk.usage_percent:.1f}%)")
        
        # Network
        if snapshot.network_stats:
            print(f"\n[NETWORK]")
            for net in snapshot.network_stats:
                if net.interface != 'lo':  # Skip loopback
                    print(f"  {net.interface}: ↓ {net.rx_mb:.2f} MB ↑ {net.tx_mb:.2f} MB")
        
        print("\n" + "="*80 + "\n")
    
    def monitor_continuous(self, interval_seconds: int = 5, duration_seconds: int = 60):
        """Monitor system continuously"""
        print(f"[MONITOR] Starting continuous monitoring (interval: {interval_seconds}s, duration: {duration_seconds}s)")
        
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            snapshot = self.get_snapshot()
            self.print_snapshot(snapshot)
            
            # Store in history
            self.history.append(snapshot)
            if len(self.history) > self.max_history:
                self.history.pop(0)
            
            time.sleep(interval_seconds)
        
        print("[MONITOR] Monitoring complete")


if __name__ == "__main__":
    monitor = SystemMonitor()
    snapshot = monitor.get_snapshot()
    monitor.print_snapshot(snapshot)
