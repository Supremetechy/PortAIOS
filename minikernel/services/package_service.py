"""
Package Service

Voice-controlled package management
Supports multiple package managers (apt, brew, pip, etc.)
"""

import logging
import subprocess
import platform
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("MiniKernel.Package")


class PackageManager(Enum):
    """Supported package managers"""
    APT = "apt"           # Debian/Ubuntu
    DNF = "dnf"           # Fedora/RHEL
    PACMAN = "pacman"     # Arch
    BREW = "brew"         # macOS/Linux
    PIP = "pip"           # Python
    NPM = "npm"           # Node.js
    UNKNOWN = "unknown"


@dataclass
class PackageInfo:
    """Package information"""
    name: str
    version: str
    description: str
    installed: bool
    manager: PackageManager


class PackageService:
    """
    Package Service for MiniKernel
    
    Capabilities:
    - Install/uninstall packages
    - Update packages
    - Search for packages
    - Multi-manager support
    
    Voice commands like:
    - "install vim"
    - "update all packages"
    - "search for text editor"
    """
    
    def __init__(self):
        self.primary_manager = self._detect_package_manager()
        
        logger.info(f"Package Service created (manager={self.primary_manager.value})")
    
    def initialize(self) -> None:
        """Initialize package service"""
        logger.info("Package Service initialized")
    
    def shutdown(self) -> None:
        """Shutdown package service"""
        logger.info("Package Service shutdown")
    
    def _detect_package_manager(self) -> PackageManager:
        """Detect the primary package manager for this system"""
        system = platform.system()
        
        # Check for specific package managers
        managers = [
            ("apt-get", PackageManager.APT),
            ("dnf", PackageManager.DNF),
            ("pacman", PackageManager.PACMAN),
            ("brew", PackageManager.BREW),
        ]
        
        for cmd, manager in managers:
            if self._command_exists(cmd):
                logger.debug(f"Detected package manager: {manager.value}")
                return manager
        
        logger.warning("No package manager detected")
        return PackageManager.UNKNOWN
    
    def _command_exists(self, command: str) -> bool:
        """Check if a command exists"""
        try:
            subprocess.run(
                ["which", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def install(self, package: str, manager: Optional[PackageManager] = None) -> bool:
        """
        Install a package
        
        Args:
            package: Package name
            manager: Package manager to use (default: auto-detect)
            
        Returns:
            True if successful
        """
        manager = manager or self.primary_manager
        
        if manager == PackageManager.UNKNOWN:
            logger.error("No package manager available")
            return False
        
        # Build install command
        if manager == PackageManager.APT:
            cmd = ["sudo", "apt-get", "install", "-y", package]
        elif manager == PackageManager.DNF:
            cmd = ["sudo", "dnf", "install", "-y", package]
        elif manager == PackageManager.PACMAN:
            cmd = ["sudo", "pacman", "-S", "--noconfirm", package]
        elif manager == PackageManager.BREW:
            cmd = ["brew", "install", package]
        elif manager == PackageManager.PIP:
            cmd = ["pip", "install", package]
        elif manager == PackageManager.NPM:
            cmd = ["npm", "install", "-g", package]
        else:
            logger.error(f"Unsupported package manager: {manager.value}")
            return False
        
        try:
            logger.info(f"Installing {package} via {manager.value}...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully installed: {package}")
                return True
            else:
                logger.error(f"Installation failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Installation timeout: {package}")
            return False
        except Exception as e:
            logger.error(f"Installation error: {e}")
            return False
    
    def uninstall(self, package: str, manager: Optional[PackageManager] = None) -> bool:
        """
        Uninstall a package
        
        Args:
            package: Package name
            manager: Package manager to use
            
        Returns:
            True if successful
        """
        manager = manager or self.primary_manager
        
        if manager == PackageManager.UNKNOWN:
            logger.error("No package manager available")
            return False
        
        # Build uninstall command
        if manager == PackageManager.APT:
            cmd = ["sudo", "apt-get", "remove", "-y", package]
        elif manager == PackageManager.DNF:
            cmd = ["sudo", "dnf", "remove", "-y", package]
        elif manager == PackageManager.PACMAN:
            cmd = ["sudo", "pacman", "-R", "--noconfirm", package]
        elif manager == PackageManager.BREW:
            cmd = ["brew", "uninstall", package]
        elif manager == PackageManager.PIP:
            cmd = ["pip", "uninstall", "-y", package]
        elif manager == PackageManager.NPM:
            cmd = ["npm", "uninstall", "-g", package]
        else:
            logger.error(f"Unsupported package manager: {manager.value}")
            return False
        
        try:
            logger.info(f"Uninstalling {package} via {manager.value}...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully uninstalled: {package}")
                return True
            else:
                logger.error(f"Uninstall failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Uninstall error: {e}")
            return False
    
    def update_all(self, manager: Optional[PackageManager] = None) -> bool:
        """
        Update all packages
        
        Args:
            manager: Package manager to use
            
        Returns:
            True if successful
        """
        manager = manager or self.primary_manager
        
        if manager == PackageManager.UNKNOWN:
            logger.error("No package manager available")
            return False
        
        # Build update command
        if manager == PackageManager.APT:
            cmd = ["sudo", "apt-get", "update", "&&", "sudo", "apt-get", "upgrade", "-y"]
        elif manager == PackageManager.DNF:
            cmd = ["sudo", "dnf", "upgrade", "-y"]
        elif manager == PackageManager.PACMAN:
            cmd = ["sudo", "pacman", "-Syu", "--noconfirm"]
        elif manager == PackageManager.BREW:
            cmd = ["brew", "upgrade"]
        elif manager == PackageManager.PIP:
            cmd = ["pip", "list", "--outdated", "--format=freeze", "|", "grep", "-v", "'^\-e'", "|", "cut", "-d", "=", "-f", "1", "|", "xargs", "-n1", "pip", "install", "-U"]
        else:
            logger.error(f"Unsupported package manager: {manager.value}")
            return False
        
        try:
            logger.info(f"Updating all packages via {manager.value}...")
            
            result = subprocess.run(
                " ".join(cmd),
                shell=True,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("Successfully updated all packages")
                return True
            else:
                logger.error(f"Update failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Update error: {e}")
            return False
    
    def search(self, query: str, manager: Optional[PackageManager] = None) -> List[PackageInfo]:
        """
        Search for packages
        
        Args:
            query: Search query
            manager: Package manager to use
            
        Returns:
            List of matching packages
        """
        manager = manager or self.primary_manager
        
        # Placeholder - would parse actual package manager output
        logger.info(f"Searching for '{query}' via {manager.value}")
        
        return []
    
    def is_installed(self, package: str, manager: Optional[PackageManager] = None) -> bool:
        """Check if a package is installed"""
        manager = manager or self.primary_manager
        
        if manager == PackageManager.APT:
            cmd = ["dpkg", "-l", package]
        elif manager == PackageManager.BREW:
            cmd = ["brew", "list", package]
        elif manager == PackageManager.PIP:
            cmd = ["pip", "show", package]
        else:
            return False
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return result.returncode == 0
        except:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get package management statistics"""
        return {
            "primary_manager": self.primary_manager.value,
            "available_managers": [
                m.value for m in PackageManager 
                if m != PackageManager.UNKNOWN and self._command_exists(m.value)
            ]
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    pkg = PackageService()
    pkg.initialize()
    
    print(f"Package manager: {pkg.primary_manager.value}")
    print(f"Stats: {pkg.get_stats()}")
    
    # Check if vim is installed
    if pkg.is_installed("vim"):
        print("vim is installed")
    else:
        print("vim is not installed")
    
    pkg.shutdown()
