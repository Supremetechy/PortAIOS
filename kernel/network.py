"""
Network Stack for AI-OS
Handles networking initialization, configuration, and management
"""

import socket
import subprocess
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json


class NetworkProtocol(Enum):
    """Network protocols"""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    HTTP = "http"
    HTTPS = "https"
    GRPC = "grpc"
    WEBSOCKET = "websocket"


class InterfaceState(Enum):
    """Network interface states"""
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class IPAddress:
    """IP address information"""
    address: str
    netmask: str
    broadcast: Optional[str]
    version: int  # 4 or 6
    
    def __str__(self):
        return f"{self.address}/{self.get_cidr()}"
    
    def get_cidr(self) -> int:
        """Convert netmask to CIDR notation"""
        if self.version == 4 and self.netmask:
            return sum([bin(int(x)).count('1') for x in self.netmask.split('.')])
        return 0


@dataclass
class NetworkInterface:
    """Network interface information"""
    name: str
    mac_address: Optional[str]
    state: InterfaceState
    ip_addresses: List[IPAddress]
    mtu: int
    rx_bytes: int
    tx_bytes: int
    rx_packets: int
    tx_packets: int
    
    @property
    def rx_mb(self) -> float:
        return self.rx_bytes / (1024 * 1024)
    
    @property
    def tx_mb(self) -> float:
        return self.tx_bytes / (1024 * 1024)


@dataclass
class Route:
    """Network route information"""
    destination: str
    gateway: str
    interface: str
    metric: int


@dataclass
class DNSConfig:
    """DNS configuration"""
    nameservers: List[str]
    search_domains: List[str]


class NetworkManager:
    """Manages network stack for AI-OS"""
    
    def __init__(self, security_manager: Optional[Any] = None):
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.routes: List[Route] = []
        self.dns_config: Optional[DNSConfig] = None
        self.hostname: str = ""
        self.security_manager = security_manager
        
    def initialize(self):
        """Initialize network stack"""
        print("[NET] Initializing network stack...")

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
                    resource_type=ResourceType.NETWORK,
                    resource_id="network_stack",
                    owner_agent_id="system",
                )
                allowed, reason = self.security_manager.authorize(context, resource, Permission.MANAGE)
                if not allowed:
                    print(f"[NET] Network init denied ({reason})")
                    return False
            except Exception as e:
                print(f"[NET] Security check failed: {e}")
                return False
        
        # Get hostname
        self._get_hostname()
        
        # Detect network interfaces
        self._detect_interfaces()
        
        # Get routing table
        self._get_routes()
        
        # Get DNS configuration
        self._get_dns_config()
        
        # Configure loopback
        self._ensure_loopback()
        
        print(f"[NET] Network stack initialized with {len(self.interfaces)} interface(s)")
        return True
    
    def _get_hostname(self):
        """Get system hostname"""
        try:
            self.hostname = socket.gethostname()
            print(f"[NET] Hostname: {self.hostname}")
        except Exception as e:
            print(f"[NET] Warning: Could not get hostname: {e}")
            self.hostname = "aios-host"
    
    def _detect_interfaces(self):
        """Detect network interfaces"""
        print("[NET] Detecting network interfaces...")
        
        try:
            import platform
            if platform.system() == "Linux":
                self._detect_interfaces_linux()
            elif platform.system() == "Darwin":
                self._detect_interfaces_macos()
            elif platform.system() == "Windows":
                self._detect_interfaces_windows()
        except Exception as e:
            print(f"[NET] Warning: Interface detection failed: {e}")
    
    def _detect_interfaces_linux(self):
        """Detect network interfaces on Linux"""
        try:
            # Use 'ip addr' command
            result = subprocess.run(
                ['ip', '-json', 'addr'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                interfaces_data = json.loads(result.stdout)
                
                for iface_data in interfaces_data:
                    name = iface_data.get('ifname', '')
                    mac = iface_data.get('address', '')
                    state = InterfaceState.UP if 'UP' in iface_data.get('flags', []) else InterfaceState.DOWN
                    mtu = iface_data.get('mtu', 0)
                    
                    # Parse IP addresses
                    ip_addresses = []
                    for addr_info in iface_data.get('addr_info', []):
                        ip = addr_info.get('local', '')
                        prefix_len = addr_info.get('prefixlen', 0)
                        family = addr_info.get('family', '')
                        
                        if family == 'inet':
                            version = 4
                            # Convert prefix to netmask
                            mask_bits = ['1'] * prefix_len + ['0'] * (32 - prefix_len)
                            netmask = '.'.join([str(int(''.join(mask_bits[i:i+8]), 2)) for i in range(0, 32, 8)])
                        elif family == 'inet6':
                            version = 6
                            netmask = f"/{prefix_len}"
                        else:
                            continue
                        
                        ip_addresses.append(IPAddress(
                            address=ip,
                            netmask=netmask,
                            broadcast=addr_info.get('broadcast'),
                            version=version
                        ))
                    
                    # Get statistics
                    stats = iface_data.get('stats64', {})
                    rx_bytes = stats.get('rx', {}).get('bytes', 0)
                    tx_bytes = stats.get('tx', {}).get('bytes', 0)
                    rx_packets = stats.get('rx', {}).get('packets', 0)
                    tx_packets = stats.get('tx', {}).get('packets', 0)
                    
                    interface = NetworkInterface(
                        name=name,
                        mac_address=mac if mac else None,
                        state=state,
                        ip_addresses=ip_addresses,
                        mtu=mtu,
                        rx_bytes=rx_bytes,
                        tx_bytes=tx_bytes,
                        rx_packets=rx_packets,
                        tx_packets=tx_packets
                    )
                    
                    self.interfaces[name] = interface
                    print(f"[NET]   {name}: {state.value} - {len(ip_addresses)} address(es)")
                    
        except subprocess.TimeoutExpired:
            print("[NET] Warning: Interface detection timed out")
        except FileNotFoundError:
            print("[NET] Warning: 'ip' command not found, trying fallback")
            self._detect_interfaces_fallback()
        except Exception as e:
            print(f"[NET] Warning: Linux interface detection failed: {e}")
    
    def _detect_interfaces_macos(self):
        """Detect network interfaces on macOS"""
        try:
            result = subprocess.run(
                ['ifconfig'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self._parse_ifconfig_output(result.stdout)
                
        except Exception as e:
            print(f"[NET] Warning: macOS interface detection failed: {e}")
    
    def _detect_interfaces_windows(self):
        """Detect network interfaces on Windows"""
        try:
            result = subprocess.run(
                ['ipconfig', '/all'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print("[NET] Windows interface detection - using basic parsing")
                # Basic parsing for Windows
                # In production, would use win32 APIs
                
        except Exception as e:
            print(f"[NET] Warning: Windows interface detection failed: {e}")
    
    def _detect_interfaces_fallback(self):
        """Fallback interface detection using Python socket library"""
        try:
            # Get all addresses
            hostname = socket.gethostname()
            addresses = socket.getaddrinfo(hostname, None)
            
            # Create a basic interface entry
            ip_addresses = []
            for addr in addresses:
                if addr[0] == socket.AF_INET:  # IPv4
                    ip_addresses.append(IPAddress(
                        address=addr[4][0],
                        netmask="255.255.255.0",  # Guess
                        broadcast=None,
                        version=4
                    ))
            
            if ip_addresses:
                interface = NetworkInterface(
                    name="default",
                    mac_address=None,
                    state=InterfaceState.UP,
                    ip_addresses=ip_addresses,
                    mtu=1500,
                    rx_bytes=0,
                    tx_bytes=0,
                    rx_packets=0,
                    tx_packets=0
                )
                self.interfaces["default"] = interface
                
        except Exception as e:
            print(f"[NET] Warning: Fallback interface detection failed: {e}")
    
    def _parse_ifconfig_output(self, output: str):
        """Parse ifconfig output"""
        current_iface = None
        lines = output.split('\n')
        
        for line in lines:
            if line and not line.startswith('\t') and not line.startswith(' '):
                # New interface
                parts = line.split(':')
                if parts:
                    name = parts[0].strip()
                    current_iface = name
                    
                    self.interfaces[name] = NetworkInterface(
                        name=name,
                        mac_address=None,
                        state=InterfaceState.UNKNOWN,
                        ip_addresses=[],
                        mtu=1500,
                        rx_bytes=0,
                        tx_bytes=0,
                        rx_packets=0,
                        tx_packets=0
                    )
            elif current_iface and 'inet ' in line:
                # IP address
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part == 'inet' and i + 1 < len(parts):
                        ip = parts[i + 1]
                        self.interfaces[current_iface].ip_addresses.append(
                            IPAddress(
                                address=ip,
                                netmask="255.255.255.0",
                                broadcast=None,
                                version=4
                            )
                        )
    
    def _get_routes(self):
        """Get routing table"""
        print("[NET] Reading routing table...")
        
        try:
            import platform
            if platform.system() == "Linux":
                result = subprocess.run(
                    ['ip', 'route'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 3:
                                destination = parts[0] if parts[0] != 'default' else '0.0.0.0/0'
                                gateway = parts[2] if 'via' in parts else ''
                                interface = parts[-1]
                                
                                self.routes.append(Route(
                                    destination=destination,
                                    gateway=gateway,
                                    interface=interface,
                                    metric=0
                                ))
                    
                    print(f"[NET]   Found {len(self.routes)} route(s)")
                    
        except Exception as e:
            print(f"[NET] Warning: Could not read routing table: {e}")
    
    def _get_dns_config(self):
        """Get DNS configuration"""
        print("[NET] Reading DNS configuration...")
        
        try:
            nameservers = []
            search_domains = []
            
            # Try to read /etc/resolv.conf
            try:
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('nameserver'):
                            ns = line.split()[1]
                            nameservers.append(ns)
                        elif line.startswith('search'):
                            domains = line.split()[1:]
                            search_domains.extend(domains)
            except FileNotFoundError:
                print("[NET]   /etc/resolv.conf not found")
            
            self.dns_config = DNSConfig(
                nameservers=nameservers,
                search_domains=search_domains
            )
            
            if nameservers:
                print(f"[NET]   DNS servers: {', '.join(nameservers)}")
                
        except Exception as e:
            print(f"[NET] Warning: Could not read DNS config: {e}")
    
    def _ensure_loopback(self):
        """Ensure loopback interface is up"""
        if 'lo' not in self.interfaces:
            print("[NET] Creating loopback interface...")
            self.interfaces['lo'] = NetworkInterface(
                name='lo',
                mac_address='00:00:00:00:00:00',
                state=InterfaceState.UP,
                ip_addresses=[
                    IPAddress(address='127.0.0.1', netmask='255.0.0.0', broadcast=None, version=4)
                ],
                mtu=65536,
                rx_bytes=0,
                tx_bytes=0,
                rx_packets=0,
                tx_packets=0
            )
        else:
            print("[NET] Loopback interface detected")
    
    def get_interface(self, name: str) -> Optional[NetworkInterface]:
        """Get interface by name"""
        return self.interfaces.get(name)
    
    def list_interfaces(self) -> List[str]:
        """List all interface names"""
        return list(self.interfaces.keys())
    
    def get_default_interface(self) -> Optional[str]:
        """Get default network interface"""
        for route in self.routes:
            if route.destination in ['default', '0.0.0.0/0']:
                return route.interface
        
        # Fallback: return first non-loopback interface
        for name, iface in self.interfaces.items():
            if name != 'lo' and iface.state == InterfaceState.UP:
                return name
        
        return None
    
    def test_connectivity(self, host: str = "8.8.8.8", timeout: int = 3) -> bool:
        """Test network connectivity"""
        print(f"[NET] Testing connectivity to {host}...")
        
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 53))
            print(f"[NET]   ✓ Connected to {host}")
            return True
        except Exception as e:
            print(f"[NET]   ✗ Could not connect to {host}: {e}")
            return False
    
    def print_network_summary(self):
        """Print network configuration summary"""
        print("\n" + "="*80)
        print("NETWORK CONFIGURATION")
        print("="*80)
        print(f"\nHostname: {self.hostname}")
        
        print(f"\nInterfaces: {len(self.interfaces)}")
        for name, iface in self.interfaces.items():
            print(f"\n  {name} ({iface.state.value})")
            if iface.mac_address:
                print(f"    MAC: {iface.mac_address}")
            print(f"    MTU: {iface.mtu}")
            
            for ip in iface.ip_addresses:
                print(f"    IP: {ip}")
            
            if iface.rx_bytes > 0 or iface.tx_bytes > 0:
                print(f"    RX: {iface.rx_mb:.2f} MB ({iface.rx_packets} packets)")
                print(f"    TX: {iface.tx_mb:.2f} MB ({iface.tx_packets} packets)")
        
        if self.routes:
            print(f"\nRoutes: {len(self.routes)}")
            for route in self.routes[:5]:  # Show first 5
                print(f"  {route.destination} via {route.gateway} dev {route.interface}")
        
        if self.dns_config and self.dns_config.nameservers:
            print(f"\nDNS Servers:")
            for ns in self.dns_config.nameservers:
                print(f"  {ns}")
        
        print("\n" + "="*80 + "\n")


# AI-specific networking utilities
class AINetworkUtils:
    """Networking utilities for AI workloads"""
    
    @staticmethod
    def get_recommended_ports() -> Dict[str, int]:
        """Get recommended ports for AI services"""
        return {
            'inference_api': 8000,
            'training_api': 8001,
            'model_registry': 8002,
            'metrics': 9090,
            'tensorboard': 6006,
            'jupyter': 8888,
            'ray_dashboard': 8265,
            'mlflow': 5000,
        }
    
    @staticmethod
    def check_port_available(port: int, host: str = '127.0.0.1') -> bool:
        """Check if a port is available"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result != 0  # Port is available if connection fails
        except Exception:
            return False
    
    @staticmethod
    def get_distributed_training_config() -> Dict[str, Any]:
        """Get configuration for distributed training"""
        return {
            'backend': 'nccl',  # For NVIDIA GPUs
            'init_method': 'tcp://localhost:23456',
            'world_size': 1,
            'rank': 0,
        }


if __name__ == "__main__":
    # Test network manager
    net = NetworkManager()
    net.initialize()
    net.print_network_summary()
    net.test_connectivity()
