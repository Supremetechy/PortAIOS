"""
Filesystem Management Layer for AI-OS
Handles file system operations, mounting, and management
"""

import os
import shutil
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class FileSystemType(Enum):
    """Supported filesystem types"""
    EXT4 = "ext4"
    XFS = "xfs"
    BTRFS = "btrfs"
    NTFS = "ntfs"
    FAT32 = "fat32"
    TMPFS = "tmpfs"
    NFS = "nfs"
    FUSE = "fuse"


class MountOptions(Enum):
    """Mount options"""
    RW = "rw"  # Read-write
    RO = "ro"  # Read-only
    NOEXEC = "noexec"  # No execution
    NOSUID = "nosuid"  # No setuid
    NODEV = "nodev"  # No device files
    SYNC = "sync"  # Synchronous I/O
    ASYNC = "async"  # Asynchronous I/O


@dataclass
class MountPoint:
    """Represents a mounted filesystem"""
    device: str
    mount_path: str
    fs_type: FileSystemType
    options: List[MountOptions]
    total_bytes: int
    used_bytes: int
    available_bytes: int
    
    @property
    def usage_percent(self) -> float:
        """Calculate usage percentage"""
        if self.total_bytes == 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100.0
    
    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024**3)
    
    @property
    def used_gb(self) -> float:
        return self.used_bytes / (1024**3)
    
    @property
    def available_gb(self) -> float:
        return self.available_bytes / (1024**3)


@dataclass
class FileMetadata:
    """File metadata information"""
    path: str
    size_bytes: int
    is_directory: bool
    is_file: bool
    permissions: str
    owner: str
    group: str
    modified_time: float
    created_time: float
    accessed_time: float


class FileSystemManager:
    """Manages filesystem operations for AI-OS"""
    
    def __init__(self, security_manager: Optional[Any] = None):
        self.mounted_filesystems: Dict[str, MountPoint] = {}
        self.virtual_root = os.environ.get("AIOS_ROOT", "/aios")
        self.security_manager = security_manager

    def _owner_from_path(self, path: str) -> Optional[str]:
        parts = Path(path).parts
        root_parts = Path(self.virtual_root).parts
        if len(parts) >= len(root_parts) + 1 and parts[:len(root_parts)] == root_parts:
            if len(parts) >= len(root_parts) + 2 and parts[len(root_parts)] == "home":
                return parts[len(root_parts) + 1] if len(parts) > len(root_parts) + 1 else None
        return None

    def _authorize_fs(self, action: Any, path: str, is_dir: bool, context: Optional[Any]) -> bool:
        if not self.security_manager:
            return True
        if context is None:
            print(f"[FS] Access denied (missing security context) for {path}")
            return False

        try:
            from kernel.security import ResourceDescriptor, ResourceType
        except Exception as e:
            print(f"[FS] Security module unavailable: {e}")
            return False

        resource_type = ResourceType.DIRECTORY if is_dir else ResourceType.FILE
        owner_agent_id = self._owner_from_path(path)
        resource = ResourceDescriptor(
            resource_type=resource_type,
            resource_id=path,
            owner_agent_id=owner_agent_id,
        )
        allowed, reason = self.security_manager.authorize(context, resource, action)
        if not allowed:
            print(f"[FS] Access denied ({reason}) for {path}")
        return allowed
        
    def initialize(self):
        """Initialize filesystem manager"""
        print("[FS] Initializing filesystem manager...")
        
        # Create essential directories
        self._create_essential_directories()
        
        # Scan existing mount points
        self._scan_mounts()
        
        print(f"[FS] Filesystem manager initialized with {len(self.mounted_filesystems)} mount points")
    
    def _create_essential_directories(self):
        """Create essential OS directories"""
        root = self.virtual_root
        essential_dirs = [
            f"{root}/bin",      # Binaries
            f"{root}/etc",      # Configuration
            f"{root}/var",      # Variable data
            f"{root}/tmp",      # Temporary files
            f"{root}/home",     # User home directories
            f"{root}/models",   # AI models
            f"{root}/datasets", # Training datasets
            f"{root}/cache",    # Model cache
            f"{root}/logs",     # System logs
            f"{root}/run",      # Runtime data
        ]
        
        for directory in essential_dirs:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
                print(f"[FS]   Created: {directory}")
            except PermissionError:
                fallback = Path("/tmp/aios")
                self.virtual_root = str(fallback)
                os.environ["AIOS_ROOT"] = self.virtual_root
                print(f"[FS]   Warning: {directory} not writable, falling back to {self.virtual_root}")
                self._create_essential_directories()
                return
            except Exception as e:
                print(f"[FS]   Warning: Could not create {directory}: {e}")
    
    def _scan_mounts(self):
        """Scan existing mount points"""
        print("[FS] Scanning mounted filesystems...")
        
        # For demonstration, we'll scan actual mounted filesystems
        try:
            if os.name == 'posix' and os.path.exists('/proc/mounts'):
                with open('/proc/mounts', 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            device = parts[0]
                            mount_path = parts[1]
                            fs_type_str = parts[2]
                            options_str = parts[3]
                            
                            # Skip certain virtual filesystems
                            if fs_type_str in ['proc', 'sysfs', 'devpts', 'cgroup', 'cgroup2']:
                                continue
                            
                            try:
                                stat = os.statvfs(mount_path)
                                total = stat.f_blocks * stat.f_frsize
                                available = stat.f_bavail * stat.f_frsize
                                used = total - available
                                
                                # Parse filesystem type
                                try:
                                    fs_type = FileSystemType(fs_type_str)
                                except ValueError:
                                    fs_type = FileSystemType.FUSE  # Default for unknown
                                
                                # Parse options
                                options = []
                                for opt in options_str.split(','):
                                    try:
                                        options.append(MountOptions(opt))
                                    except ValueError:
                                        pass
                                
                                mount_point = MountPoint(
                                    device=device,
                                    mount_path=mount_path,
                                    fs_type=fs_type,
                                    options=options,
                                    total_bytes=total,
                                    used_bytes=used,
                                    available_bytes=available
                                )
                                
                                self.mounted_filesystems[mount_path] = mount_point
                                
                            except Exception as e:
                                print(f"[FS]   Warning: Could not stat {mount_path}: {e}")
                                
        except Exception as e:
            print(f"[FS]   Warning: Could not scan mounts: {e}")
    
    def get_mount_point(self, path: str) -> Optional[MountPoint]:
        """Get mount point for a given path"""
        path = os.path.abspath(path)
        
        # Find the longest matching mount point
        best_match = None
        best_match_len = 0
        
        for mount_path, mount_point in self.mounted_filesystems.items():
            if path.startswith(mount_path) and len(mount_path) > best_match_len:
                best_match = mount_point
                best_match_len = len(mount_path)
        
        return best_match
    
    def get_disk_usage(self, path: str) -> Dict[str, Any]:
        """Get disk usage for a path"""
        try:
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            available = stat.f_bavail * stat.f_frsize
            used = total - available
            
            return {
                'total_bytes': total,
                'used_bytes': used,
                'available_bytes': available,
                'total_gb': total / (1024**3),
                'used_gb': used / (1024**3),
                'available_gb': available / (1024**3),
                'usage_percent': (used / total * 100) if total > 0 else 0
            }
        except Exception as e:
            print(f"[FS] Error getting disk usage for {path}: {e}")
            return {}
    
    def list_directory(self, path: str, recursive: bool = False, context: Optional[Any] = None) -> List[FileMetadata]:
        """List directory contents"""
        files = []
        
        try:
            path_obj = Path(path)
            
            if not path_obj.exists():
                print(f"[FS] Path does not exist: {path}")
                return files
            
            if not path_obj.is_dir():
                print(f"[FS] Path is not a directory: {path}")
                return files

            try:
                from kernel.security import Permission
                if not self._authorize_fs(Permission.READ, path, True, context):
                    return files
            except Exception:
                pass
            
            items = path_obj.rglob('*') if recursive else path_obj.iterdir()
            
            for item in items:
                try:
                    stat_info = item.stat()
                    
                    metadata = FileMetadata(
                        path=str(item),
                        size_bytes=stat_info.st_size,
                        is_directory=item.is_dir(),
                        is_file=item.is_file(),
                        permissions=oct(stat_info.st_mode)[-3:],
                        owner=str(stat_info.st_uid),
                        group=str(stat_info.st_gid),
                        modified_time=stat_info.st_mtime,
                        created_time=stat_info.st_ctime,
                        accessed_time=stat_info.st_atime
                    )
                    
                    files.append(metadata)
                    
                except Exception as e:
                    print(f"[FS] Error getting metadata for {item}: {e}")
            
        except Exception as e:
            print(f"[FS] Error listing directory {path}: {e}")
        
        return files
    
    def create_directory(self, path: str, parents: bool = True, context: Optional[Any] = None) -> bool:
        """Create a directory"""
        try:
            try:
                from kernel.security import Permission
                if not self._authorize_fs(Permission.WRITE, path, True, context):
                    return False
            except Exception:
                pass
            Path(path).mkdir(parents=parents, exist_ok=True)
            print(f"[FS] Created directory: {path}")
            return True
        except Exception as e:
            print(f"[FS] Error creating directory {path}: {e}")
            return False
    
    def delete_path(self, path: str, recursive: bool = False, context: Optional[Any] = None) -> bool:
        """Delete a file or directory"""
        try:
            path_obj = Path(path)
            
            if not path_obj.exists():
                print(f"[FS] Path does not exist: {path}")
                return False

            try:
                from kernel.security import Permission
                if not self._authorize_fs(Permission.DELETE, path, path_obj.is_dir(), context):
                    return False
            except Exception:
                pass
            
            if path_obj.is_dir():
                if recursive:
                    shutil.rmtree(path)
                    print(f"[FS] Deleted directory recursively: {path}")
                else:
                    path_obj.rmdir()
                    print(f"[FS] Deleted empty directory: {path}")
            else:
                path_obj.unlink()
                print(f"[FS] Deleted file: {path}")
            
            return True
            
        except Exception as e:
            print(f"[FS] Error deleting {path}: {e}")
            return False
    
    def copy_path(self, source: str, destination: str, context: Optional[Any] = None) -> bool:
        """Copy a file or directory"""
        try:
            source_obj = Path(source)
            
            if not source_obj.exists():
                print(f"[FS] Source does not exist: {source}")
                return False

            try:
                from kernel.security import Permission
                if not self._authorize_fs(Permission.READ, source, source_obj.is_dir(), context):
                    return False
                if not self._authorize_fs(Permission.WRITE, destination, source_obj.is_dir(), context):
                    return False
            except Exception:
                pass
            
            if source_obj.is_dir():
                shutil.copytree(source, destination)
                print(f"[FS] Copied directory: {source} -> {destination}")
            else:
                shutil.copy2(source, destination)
                print(f"[FS] Copied file: {source} -> {destination}")
            
            return True
            
        except Exception as e:
            print(f"[FS] Error copying {source} to {destination}: {e}")
            return False
    
    def move_path(self, source: str, destination: str, context: Optional[Any] = None) -> bool:
        """Move a file or directory"""
        try:
            try:
                from kernel.security import Permission
                source_obj = Path(source)
                if not self._authorize_fs(Permission.DELETE, source, source_obj.is_dir(), context):
                    return False
                if not self._authorize_fs(Permission.WRITE, destination, source_obj.is_dir(), context):
                    return False
            except Exception:
                pass
            shutil.move(source, destination)
            print(f"[FS] Moved: {source} -> {destination}")
            return True
        except Exception as e:
            print(f"[FS] Error moving {source} to {destination}: {e}")
            return False
    
    def get_file_info(self, path: str, context: Optional[Any] = None) -> Optional[FileMetadata]:
        """Get file metadata"""
        try:
            path_obj = Path(path)
            
            if not path_obj.exists():
                return None

            try:
                from kernel.security import Permission
                if not self._authorize_fs(Permission.READ, path, path_obj.is_dir(), context):
                    return None
            except Exception:
                pass
            
            stat_info = path_obj.stat()
            
            return FileMetadata(
                path=str(path_obj),
                size_bytes=stat_info.st_size,
                is_directory=path_obj.is_dir(),
                is_file=path_obj.is_file(),
                permissions=oct(stat_info.st_mode)[-3:],
                owner=str(stat_info.st_uid),
                group=str(stat_info.st_gid),
                modified_time=stat_info.st_mtime,
                created_time=stat_info.st_ctime,
                accessed_time=stat_info.st_atime
            )
            
        except Exception as e:
            print(f"[FS] Error getting file info for {path}: {e}")
            return None
    
    def check_available_space(self, path: str, required_gb: float) -> bool:
        """Check if sufficient space is available"""
        usage = self.get_disk_usage(path)
        if not usage:
            return False
        
        available_gb = usage.get('available_gb', 0)
        return available_gb >= required_gb
    
    def print_mount_summary(self):
        """Print summary of mounted filesystems"""
        print("\n" + "="*80)
        print("MOUNTED FILESYSTEMS")
        print("="*80)
        
        for mount_path, mount_point in sorted(self.mounted_filesystems.items()):
            print(f"\n{mount_path}")
            print(f"  Device: {mount_point.device}")
            print(f"  Type: {mount_point.fs_type.value}")
            print(f"  Size: {mount_point.total_gb:.2f} GB")
            print(f"  Used: {mount_point.used_gb:.2f} GB ({mount_point.usage_percent:.1f}%)")
            print(f"  Available: {mount_point.available_gb:.2f} GB")
            
            if mount_point.options:
                options_str = ', '.join(opt.value for opt in mount_point.options[:5])
                print(f"  Options: {options_str}")
        
        print("\n" + "="*80 + "\n")


# AI-specific filesystem utilities
class AIFileSystemUtils:
    """Utilities for AI workload filesystem management"""
    
    @staticmethod
    def get_model_storage_path() -> str:
        """Get path for model storage"""
        root = os.environ.get("AIOS_ROOT", "/aios")
        return f"{root}/models"
    
    @staticmethod
    def get_dataset_storage_path() -> str:
        """Get path for dataset storage"""
        root = os.environ.get("AIOS_ROOT", "/aios")
        return f"{root}/datasets"
    
    @staticmethod
    def get_cache_path() -> str:
        """Get path for model cache"""
        root = os.environ.get("AIOS_ROOT", "/aios")
        return f"{root}/cache"
    
    @staticmethod
    def get_checkpoint_path() -> str:
        """Get path for training checkpoints"""
        root = os.environ.get("AIOS_ROOT", "/aios")
        return f"{root}/var/checkpoints"
    
    @staticmethod
    def estimate_model_size(model_type: str, parameters_millions: int) -> float:
        """Estimate model size in GB"""
        # Rough estimates (float32: 4 bytes per parameter)
        bytes_per_param = 4
        total_bytes = parameters_millions * 1_000_000 * bytes_per_param
        
        # Add overhead for optimizer states, gradients, etc.
        overhead_multiplier = 1.5
        
        return (total_bytes * overhead_multiplier) / (1024**3)
    
    @staticmethod
    def check_model_storage_space(model_size_gb: float) -> bool:
        """Check if enough space for model"""
        fs_manager = FileSystemManager()
        model_path = AIFileSystemUtils.get_model_storage_path()
        return fs_manager.check_available_space(model_path, model_size_gb * 1.2)  # 20% buffer


if __name__ == "__main__":
    # Test filesystem manager
    fs = FileSystemManager()
    fs.initialize()
    fs.print_mount_summary()
