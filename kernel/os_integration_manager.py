"""
PortAIOS Operating System Integration Manager
==============================================
Unified interface for complete OS control through the dynamic avatar interface.
Provides file system, application, browser, terminal, and system management.
"""

import importlib.util
import os
import platform
import subprocess
import psutil
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger("AIOS.OSIntegration")

EEL_AVAILABLE = importlib.util.find_spec("eel") is not None
if not EEL_AVAILABLE:
    logger.warning("Eel not available - OS integration disabled")


@dataclass
class FileItem:
    """Represents a file or folder in the file system"""
    name: str
    path: str
    type: str  # 'file' or 'folder'
    size: int
    modified: float
    is_hidden: bool
    extension: str = ""
    icon: str = "📄"
    permissions: str = ""
    owner: str = ""


@dataclass
class ProcessInfo:
    """Represents a running process"""
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float
    status: str
    user: str = ""


@dataclass
class ApplicationInfo:
    """Represents an installed application"""
    name: str
    command: str
    icon: str
    category: str
    description: str = ""


class OSIntegrationManager:
    """
    Unified OS integration manager for PortAIOS.
    Provides complete control over the underlying operating system.
    """
    
    def __init__(self):
        self.system = platform.system()
        self.current_path = str(Path.home())
        self.bookmarks = self._load_bookmarks()
        self.recent_files = []
        self.running_apps = {}
        logger.info(f"OS Integration Manager initialized for {self.system}")
    
    # ============================================================================
    # FILE SYSTEM OPERATIONS
    # ============================================================================
    
    def list_directory(self, path: Optional[str] = None, show_hidden: bool = False) -> Dict[str, Any]:
        """List contents of a directory with detailed metadata"""
        try:
            if not path:
                path = self.current_path
            
            path_obj = Path(path).expanduser().resolve()
            
            if not path_obj.exists():
                return {"success": False, "error": "Path does not exist", "files": []}
            
            if not path_obj.is_dir():
                return {"success": False, "error": "Path is not a directory", "files": []}
            
            self.current_path = str(path_obj)
            files = []
            folders = []
            
            for item in sorted(path_obj.iterdir()):
                try:
                    # Skip hidden files if requested
                    if not show_hidden and item.name.startswith('.'):
                        continue
                    
                    stat = item.stat()
                    is_hidden = item.name.startswith('.')
                    
                    file_item = FileItem(
                        name=item.name,
                        path=str(item),
                        type="folder" if item.is_dir() else "file",
                        size=stat.st_size if item.is_file() else 0,
                        modified=stat.st_mtime,
                        is_hidden=is_hidden,
                        extension=item.suffix.lower() if item.is_file() else "",
                        icon=self._get_file_icon(item),
                        permissions=oct(stat.st_mode)[-3:],
                        owner=self._get_file_owner(item)
                    )
                    
                    if item.is_dir():
                        folders.append(asdict(file_item))
                    else:
                        files.append(asdict(file_item))
                        
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not access {item}: {e}")
                    continue
            
            # Sort: folders first, then files
            all_items = folders + files
            
            return {
                "success": True,
                "path": str(path_obj),
                "parent": str(path_obj.parent) if path_obj.parent != path_obj else None,
                "files": all_items,
                "total_files": len(files),
                "total_folders": len(folders)
            }
            
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return {"success": False, "error": str(e), "files": []}
    
    def _get_file_icon(self, path: Path) -> str:
        """Get emoji icon for file type"""
        if path.is_dir():
            special_folders = {
                "Desktop": "🖥️",
                "Documents": "📄",
                "Downloads": "⬇️",
                "Pictures": "🖼️",
                "Music": "🎵",
                "Videos": "🎬",
                "Applications": "📦",
                "Library": "📚"
            }
            return special_folders.get(path.name, "📁")
        
        ext = path.suffix.lower()
        icons = {
            # Code
            '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨', '.json': '📋',
            '.java': '☕', '.cpp': '⚙️', '.c': '⚙️', '.go': '🔷', '.rs': '🦀',
            # Documents
            '.pdf': '📕', '.doc': '📘', '.docx': '📘', '.txt': '📝', '.md': '📖',
            '.xlsx': '📊', '.csv': '📊', '.ppt': '📽️', '.pptx': '📽️',
            # Media
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🎞️', '.svg': '🎨',
            '.mp4': '🎬', '.mov': '🎬', '.avi': '🎬', '.mkv': '🎬',
            '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.ogg': '🎵',
            # Archives
            '.zip': '🗜️', '.tar': '🗜️', '.gz': '🗜️', '.rar': '🗜️', '.7z': '🗜️',
            # Executables
            '.exe': '⚡', '.app': '📦', '.dmg': '💿', '.deb': '📦', '.rpm': '📦',
            # Data
            '.db': '🗄️', '.sql': '🗄️', '.sqlite': '🗄️',
        }
        return icons.get(ext, '📄')
    
    def _get_file_owner(self, path: Path) -> str:
        """Get file owner (platform-specific)"""
        try:
            if self.system == "Windows":
                return ""  # Complex on Windows
            else:
                import pwd
                return pwd.getpwuid(path.stat().st_uid).pw_name
        except:
            return ""
    
    def create_folder(self, path: str, name: str) -> Dict[str, Any]:
        """Create a new folder"""
        try:
            new_path = Path(path) / name
            new_path.mkdir(parents=True, exist_ok=False)
            logger.info(f"Created folder: {new_path}")
            return {"success": True, "path": str(new_path)}
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_item(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """Delete a file or folder"""
        try:
            path_obj = Path(path)
            if path_obj.is_dir():
                if recursive:
                    import shutil
                    shutil.rmtree(path_obj)
                else:
                    path_obj.rmdir()
            else:
                path_obj.unlink()
            logger.info(f"Deleted: {path}")
            return {"success": True, "path": path}
        except Exception as e:
            logger.error(f"Error deleting {path}: {e}")
            return {"success": False, "error": str(e)}
    
    def rename_item(self, old_path: str, new_name: str) -> Dict[str, Any]:
        """Rename a file or folder"""
        try:
            old_path_obj = Path(old_path)
            new_path = old_path_obj.parent / new_name
            old_path_obj.rename(new_path)
            logger.info(f"Renamed: {old_path} -> {new_path}")
            return {"success": True, "old_path": old_path, "new_path": str(new_path)}
        except Exception as e:
            logger.error(f"Error renaming {old_path}: {e}")
            return {"success": False, "error": str(e)}
    
    def copy_items(self, items: List[str], destination: str) -> Dict[str, Any]:
        """Copy files or folders"""
        import shutil
        try:
            copied = []
            for item in items:
                src = Path(item)
                dst = Path(destination) / src.name
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                copied.append(str(dst))
            return {"success": True, "copied": copied}
        except Exception as e:
            logger.error(f"Error copying items: {e}")
            return {"success": False, "error": str(e)}
    
    def move_items(self, items: List[str], destination: str) -> Dict[str, Any]:
        """Move files or folders"""
        import shutil
        try:
            moved = []
            for item in items:
                src = Path(item)
                dst = Path(destination) / src.name
                shutil.move(str(src), str(dst))
                moved.append(str(dst))
            return {"success": True, "moved": moved}
        except Exception as e:
            logger.error(f"Error moving items: {e}")
            return {"success": False, "error": str(e)}
    
    def read_file(self, path: str, max_size: int = 1024 * 1024) -> Dict[str, Any]:
        """Read file contents"""
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return {"success": False, "error": "File does not exist"}
            
            if path_obj.stat().st_size > max_size:
                return {"success": False, "error": f"File too large (max {max_size} bytes)"}
            
            # Try to read as text
            try:
                with open(path_obj, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"success": True, "content": content, "type": "text"}
            except UnicodeDecodeError:
                # Binary file
                import base64
                with open(path_obj, 'rb') as f:
                    content = base64.b64encode(f.read()).decode('utf-8')
                return {"success": True, "content": content, "type": "binary"}
                
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return {"success": False, "error": str(e)}
    
    def write_file(self, path: str, content: str, binary: bool = False) -> Dict[str, Any]:
        """Write content to file"""
        try:
            path_obj = Path(path)
            if binary:
                import base64
                with open(path_obj, 'wb') as f:
                    f.write(base64.b64decode(content))
            else:
                with open(path_obj, 'w', encoding='utf-8') as f:
                    f.write(content)
            logger.info(f"Written to file: {path}")
            return {"success": True, "path": path}
        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            return {"success": False, "error": str(e)}
    
    def search_files(self, query: str, search_path: Optional[str] = None, max_results: int = 100) -> Dict[str, Any]:
        """Search for files by name"""
        try:
            if not search_path:
                search_path = self.current_path
            
            results = []
            search_path_obj = Path(search_path)
            
            for item in search_path_obj.rglob(f"*{query}*"):
                if len(results) >= max_results:
                    break
                try:
                    stat = item.stat()
                    results.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "folder" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else 0,
                        "modified": stat.st_mtime
                    })
                except (PermissionError, OSError):
                    continue
            
            return {"success": True, "results": results, "count": len(results)}
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return {"success": False, "error": str(e), "results": []}
    
    def _load_bookmarks(self) -> List[Dict[str, str]]:
        """Load file system bookmarks"""
        home = Path.home()
        bookmarks = [
            {"name": "Home", "path": str(home), "icon": "🏠"},
            {"name": "Desktop", "path": str(home / "Desktop"), "icon": "🖥️"},
            {"name": "Documents", "path": str(home / "Documents"), "icon": "📄"},
            {"name": "Downloads", "path": str(home / "Downloads"), "icon": "⬇️"},
            {"name": "Pictures", "path": str(home / "Pictures"), "icon": "🖼️"},
            {"name": "Music", "path": str(home / "Music"), "icon": "🎵"},
            {"name": "Videos", "path": str(home / "Videos"), "icon": "🎬"},
        ]
        return [b for b in bookmarks if Path(b["path"]).exists()]
    
    def get_bookmarks(self) -> List[Dict[str, str]]:
        """Get file system bookmarks"""
        return self.bookmarks
    
    # ============================================================================
    # APPLICATION MANAGEMENT
    # ============================================================================
    
    def get_installed_applications(self) -> List[Dict[str, Any]]:
        """Get list of installed applications"""
        apps = []
        
        if self.system == "Darwin":  # macOS
            apps_dir = Path("/Applications")
            if apps_dir.exists():
                for app in apps_dir.glob("*.app"):
                    apps.append({
                        "name": app.stem,
                        "path": str(app),
                        "icon": "📦",
                        "category": "Application"
                    })
        
        elif self.system == "Windows":
            # Common Windows applications
            common_apps = [
                {"name": "Notepad", "command": "notepad.exe", "icon": "📝", "category": "Utilities"},
                {"name": "Calculator", "command": "calc.exe", "icon": "🔢", "category": "Utilities"},
                {"name": "Paint", "command": "mspaint.exe", "icon": "🎨", "category": "Graphics"},
                {"name": "Command Prompt", "command": "cmd.exe", "icon": "⚫", "category": "System"},
                {"name": "PowerShell", "command": "powershell.exe", "icon": "🔷", "category": "System"},
            ]
            apps.extend(common_apps)
        
        elif self.system == "Linux":
            # Common Linux applications
            common_apps = [
                {"name": "Terminal", "command": "gnome-terminal", "icon": "⚫", "category": "System"},
                {"name": "Files", "command": "nautilus", "icon": "📁", "category": "Utilities"},
                {"name": "Text Editor", "command": "gedit", "icon": "📝", "category": "Utilities"},
                {"name": "Firefox", "command": "firefox", "icon": "🦊", "category": "Internet"},
                {"name": "Calculator", "command": "gnome-calculator", "icon": "🔢", "category": "Utilities"},
            ]
            apps.extend(common_apps)
        
        return apps
    
    def launch_application(self, app_path_or_command: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Launch an application"""
        try:
            if args is None:
                args = []
            
            if self.system == "Darwin" and app_path_or_command.endswith('.app'):
                # macOS app bundle
                process = subprocess.Popen(['open', app_path_or_command] + args)
            elif self.system == "Windows":
                process = subprocess.Popen([app_path_or_command] + args, shell=True)
            else:
                process = subprocess.Popen([app_path_or_command] + args)
            
            self.running_apps[process.pid] = {
                "name": app_path_or_command,
                "pid": process.pid,
                "started": datetime.now().isoformat()
            }
            
            logger.info(f"Launched application: {app_path_or_command} (PID: {process.pid})")
            return {"success": True, "pid": process.pid, "name": app_path_or_command}
            
        except Exception as e:
            logger.error(f"Error launching application {app_path_or_command}: {e}")
            return {"success": False, "error": str(e)}
    
    def open_file_with_app(self, file_path: str) -> Dict[str, Any]:
        """Open a file with default application"""
        try:
            path_obj = Path(file_path).resolve()
            if not path_obj.exists():
                return {"success": False, "error": "File does not exist"}
            
            if self.system == "Windows":
                os.startfile(str(path_obj))  # type: ignore[attr-defined]
            elif self.system == "Darwin":
                subprocess.run(['open', str(path_obj)])
            else:  # Linux
                subprocess.run(['xdg-open', str(path_obj)])
            
            # Add to recent files
            self.recent_files.insert(0, str(path_obj))
            self.recent_files = self.recent_files[:20]  # Keep last 20
            
            logger.info(f"Opened file: {path_obj}")
            return {"success": True, "path": str(path_obj)}
            
        except Exception as e:
            logger.error(f"Error opening file {file_path}: {e}")
            return {"success": False, "error": str(e)}
    
    # ============================================================================
    # PROCESS MANAGEMENT
    # ============================================================================
    
    def get_running_processes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status', 'username']):
                try:
                    info = proc.info
                    processes.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "cpu_percent": info['cpu_percent'] or 0.0,
                        "memory_mb": info['memory_info'].rss / (1024 * 1024) if info['memory_info'] else 0,
                        "status": info['status'],
                        "user": info.get('username', '')
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            return processes[:limit]
            
        except Exception as e:
            logger.error(f"Error getting processes: {e}")
            return []
    
    def kill_process(self, pid: int) -> Dict[str, Any]:
        """Kill a process by PID"""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            logger.info(f"Killed process: {pid}")
            return {"success": True, "pid": pid}
        except Exception as e:
            logger.error(f"Error killing process {pid}: {e}")
            return {"success": False, "error": str(e)}
    
    # ============================================================================
    # SYSTEM INFORMATION
    # ============================================================================
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "success": True,
                "system": {
                    "os": self.system,
                    "platform": platform.platform(),
                    "architecture": platform.machine(),
                    "processor": platform.processor(),
                    "python_version": platform.python_version(),
                    "hostname": platform.node()
                },
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(logical=False),
                    "count_logical": psutil.cpu_count(logical=True)
                },
                "memory": {
                    "total_gb": memory.total / (1024 ** 3),
                    "available_gb": memory.available / (1024 ** 3),
                    "used_gb": memory.used / (1024 ** 3),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": disk.total / (1024 ** 3),
                    "used_gb": disk.used / (1024 ** 3),
                    "free_gb": disk.free / (1024 ** 3),
                    "percent": disk.percent
                },
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"success": False, "error": str(e)}
    
    def get_special_paths(self) -> Dict[str, str]:
        """Get special system paths"""
        home = Path.home()
        return {
            "home": str(home),
            "desktop": str(home / "Desktop"),
            "documents": str(home / "Documents"),
            "downloads": str(home / "Downloads"),
            "pictures": str(home / "Pictures"),
            "music": str(home / "Music"),
            "videos": str(home / "Videos"),
            "current": self.current_path
        }


# ============================================================================
# EEL INTEGRATION
# ============================================================================

def setup_os_integration():
    """Setup OS integration with Eel"""
    if not EEL_AVAILABLE:
        logger.warning("Eel not available - skipping OS integration setup")
        return None

    import eel  # re-import locally so the type-checker knows it's bound here

    os_mgr = OSIntegrationManager()

    # File System
    @eel.expose
    def os_list_directory(path=None, show_hidden=False):
        return os_mgr.list_directory(path, show_hidden)
    
    @eel.expose
    def os_create_folder(path, name):
        return os_mgr.create_folder(path, name)
    
    @eel.expose
    def os_delete_item(path, recursive=False):
        return os_mgr.delete_item(path, recursive)
    
    @eel.expose
    def os_rename_item(old_path, new_name):
        return os_mgr.rename_item(old_path, new_name)
    
    @eel.expose
    def os_copy_items(items, destination):
        return os_mgr.copy_items(items, destination)
    
    @eel.expose
    def os_move_items(items, destination):
        return os_mgr.move_items(items, destination)
    
    @eel.expose
    def os_read_file(path, max_size=1024*1024):
        return os_mgr.read_file(path, max_size)
    
    @eel.expose
    def os_write_file(path, content, binary=False):
        return os_mgr.write_file(path, content, binary)
    
    @eel.expose
    def os_search_files(query, search_path=None, max_results=100):
        return os_mgr.search_files(query, search_path, max_results)
    
    @eel.expose
    def os_get_bookmarks():
        return os_mgr.get_bookmarks()
    
    # Applications
    @eel.expose
    def os_get_applications():
        return os_mgr.get_installed_applications()
    
    @eel.expose
    def os_launch_application(app_path, args=None):
        return os_mgr.launch_application(app_path, args)
    
    @eel.expose
    def os_open_file(file_path):
        return os_mgr.open_file_with_app(file_path)
    
    # Processes
    @eel.expose
    def os_get_processes(limit=50):
        return os_mgr.get_running_processes(limit)
    
    @eel.expose
    def os_kill_process(pid):
        return os_mgr.kill_process(pid)
    
    # System
    @eel.expose
    def os_get_system_info():
        return os_mgr.get_system_info()
    
    @eel.expose
    def os_get_special_paths():
        return os_mgr.get_special_paths()
    
    logger.info("OS Integration setup complete")
    return os_mgr


__all__ = ['OSIntegrationManager', 'setup_os_integration']
