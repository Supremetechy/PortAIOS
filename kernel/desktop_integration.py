"""
Desktop Integration for AIOS
Provides backend support for native desktop features accessible via voice commands
"""

import os
import platform
import subprocess
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("AIOS.DesktopIntegration")

try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    EEL_AVAILABLE = False
    logger.warning("Eel not available - desktop integration disabled")


class DesktopIntegrationManager:
    """Manages desktop integration features for AIOS"""
    
    def __init__(self, filesystem_manager=None):
        self.fs_manager = filesystem_manager
        self.system = platform.system()
        logger.info(f"Desktop integration initialized for {self.system}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        return {
            "system": self.system,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
    
    def list_directory(self, path: Optional[str] = None) -> Dict[str, Any]:
        """List contents of a directory"""
        try:
            if not path:
                # Default to user home directory
                path = str(Path.home())
            
            path_obj = Path(path).expanduser().resolve()
            
            if not path_obj.exists():
                return {"success": False, "error": "Path does not exist", "files": []}
            
            if not path_obj.is_dir():
                return {"success": False, "error": "Path is not a directory", "files": []}
            
            files = []
            for item in sorted(path_obj.iterdir()):
                try:
                    stat = item.stat()
                    files.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "folder" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else 0,
                        "modified": stat.st_mtime,
                        "hidden": item.name.startswith('.')
                    })
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not access {item}: {e}")
                    continue
            
            return {
                "success": True,
                "path": str(path_obj),
                "files": files,
                "count": len(files)
            }
            
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return {"success": False, "error": str(e), "files": []}
    
    def open_file_or_folder(self, path: str) -> Dict[str, Any]:
        """Open a file or folder with the default system application"""
        try:
            path_obj = Path(path).expanduser().resolve()
            
            if not path_obj.exists():
                return {"success": False, "error": "Path does not exist"}
            
            # Open with default application based on OS
            if self.system == "Windows":
                os.startfile(str(path_obj))
            elif self.system == "Darwin":  # macOS
                subprocess.run(["open", str(path_obj)], check=True)
            else:  # Linux and others
                subprocess.run(["xdg-open", str(path_obj)], check=True)
            
            logger.info(f"Opened: {path_obj}")
            return {"success": True, "path": str(path_obj)}
            
        except Exception as e:
            logger.error(f"Error opening {path}: {e}")
            return {"success": False, "error": str(e)}
    
    def launch_application(self, app_name: str) -> Dict[str, Any]:
        """Launch an application by name"""
        try:
            logger.info(f"Attempting to launch: {app_name}")
            
            # Common application mappings
            app_mappings = {
                "notepad": "notepad.exe" if self.system == "Windows" else "gedit",
                "calculator": "calc.exe" if self.system == "Windows" else "gnome-calculator",
                "terminal": "cmd.exe" if self.system == "Windows" else "gnome-terminal",
                "browser": "chrome" if self.system == "Windows" else "google-chrome",
                "firefox": "firefox",
                "chrome": "chrome" if self.system == "Windows" else "google-chrome"
            }
            
            # Try to get mapped app name
            command = app_mappings.get(app_name.lower(), app_name)
            
            if self.system == "Windows":
                subprocess.Popen([command], shell=True)
            elif self.system == "Darwin":  # macOS
                subprocess.Popen(["open", "-a", command])
            else:  # Linux
                subprocess.Popen([command])
            
            logger.info(f"Launched: {command}")
            return {"success": True, "app": app_name, "command": command}
            
        except Exception as e:
            logger.error(f"Error launching {app_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_home_directory(self) -> str:
        """Get user's home directory"""
        return str(Path.home())
    
    def get_desktop_path(self) -> str:
        """Get path to user's desktop"""
        return str(Path.home() / "Desktop")
    
    def get_documents_path(self) -> str:
        """Get path to user's documents"""
        return str(Path.home() / "Documents")
    
    def get_downloads_path(self) -> str:
        """Get path to user's downloads"""
        return str(Path.home() / "Downloads")


def setup_desktop_integration(filesystem_manager=None):
    """Setup desktop integration with Eel if available"""
    if not EEL_AVAILABLE:
        logger.warning("Eel not available - skipping desktop integration setup")
        return None
    
    desktop = DesktopIntegrationManager(filesystem_manager)
    
    @eel.expose
    def get_system_info() -> Dict[str, Any]:
        """Get system information"""
        return desktop.get_system_info()
    
    @eel.expose
    def list_directory(path: Optional[str] = None) -> Dict[str, Any]:
        """List directory contents"""
        return desktop.list_directory(path)
    
    @eel.expose
    def open_file_or_folder(path: str) -> Dict[str, Any]:
        """Open file or folder"""
        return desktop.open_file_or_folder(path)
    
    @eel.expose
    def launch_application(app_name: str) -> Dict[str, Any]:
        """Launch an application"""
        return desktop.launch_application(app_name)
    
    @eel.expose
    def get_special_paths() -> Dict[str, str]:
        """Get special folder paths"""
        return {
            "home": desktop.get_home_directory(),
            "desktop": desktop.get_desktop_path(),
            "documents": desktop.get_documents_path(),
            "downloads": desktop.get_downloads_path()
        }
    
    logger.info("Desktop integration setup complete")
    return desktop


__all__ = ['DesktopIntegrationManager', 'setup_desktop_integration']
