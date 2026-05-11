"""
System Update Manager for AIOS
Handles checking and installing system updates
"""
import logging
import subprocess
import platform
import sys
from typing import Dict, List, Optional, Any

logger = logging.getLogger("AIOS.SystemUpdater")


class SystemUpdater:
    """Manages system updates across different platforms"""
    
    def __init__(self):
        self.system = platform.system()
        logger.info(f"SystemUpdater initialized for {self.system}")
    
    def check_updates(self) -> Dict[str, Any]:
        """Check for available system updates"""
        try:
            if self.system == "Linux":
                return self._check_linux_updates()
            elif self.system == "Darwin":
                return self._check_macos_updates()
            elif self.system == "Windows":
                return self._check_windows_updates()
            else:
                return {
                    'available': False,
                    'count': 0,
                    'message': f'Update checking not supported on {self.system}'
                }
        except Exception as e:
            logger.error(f"Error checking updates: {e}")
            return {
                'available': False,
                'count': 0,
                'error': str(e)
            }
    
    def _check_linux_updates(self) -> Dict[str, Any]:
        """Check for updates on Linux"""
        try:
            # Try apt (Debian/Ubuntu)
            result = subprocess.run(
                ['apt', 'list', '--upgradable'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                count = max(0, len(lines) - 1)  # Subtract header line
                
                return {
                    'available': count > 0,
                    'count': count,
                    'message': f'{count} package updates available',
                    'packages': lines[1:] if count > 0 else []
                }
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Error checking apt updates: {e}")
        
        # Try dnf (Fedora/RHEL)
        try:
            result = subprocess.run(
                ['dnf', 'check-update'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # dnf returns 100 when updates are available
            if result.returncode == 100:
                lines = [l for l in result.stdout.split('\n') if l.strip() and not l.startswith('Last')]
                count = len(lines)
                
                return {
                    'available': True,
                    'count': count,
                    'message': f'{count} package updates available'
                }
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Error checking dnf updates: {e}")
        
        return {
            'available': False,
            'count': 0,
            'message': 'No supported package manager found'
        }
    
    def _check_macos_updates(self) -> Dict[str, Any]:
        """Check for updates on macOS"""
        try:
            result = subprocess.run(
                ['softwareupdate', '-l'],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if 'No new software available' in result.stdout:
                return {
                    'available': False,
                    'count': 0,
                    'message': 'System is up to date'
                }
            else:
                # Count update lines
                lines = [l for l in result.stdout.split('\n') if '*' in l or 'Title:' in l]
                count = len(lines)
                
                return {
                    'available': count > 0,
                    'count': count,
                    'message': f'{count} updates available'
                }
        except Exception as e:
            logger.error(f"Error checking macOS updates: {e}")
            return {
                'available': False,
                'count': 0,
                'error': str(e)
            }
    
    def _check_windows_updates(self) -> Dict[str, Any]:
        """Check for updates on Windows"""
        try:
            # Use PowerShell to check Windows Update
            ps_script = """
            $UpdateSession = New-Object -ComObject Microsoft.Update.Session
            $UpdateSearcher = $UpdateSession.CreateUpdateSearcher()
            $SearchResult = $UpdateSearcher.Search("IsInstalled=0")
            $SearchResult.Updates.Count
            """
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                count = int(result.stdout.strip())
                return {
                    'available': count > 0,
                    'count': count,
                    'message': f'{count} Windows updates available'
                }
        except Exception as e:
            logger.error(f"Error checking Windows updates: {e}")
        
        return {
            'available': False,
            'count': 0,
            'message': 'Unable to check Windows updates'
        }
    
    def install_updates(self, auto_approve: bool = False) -> Dict[str, Any]:
        """Install system updates (requires elevated privileges)"""
        if not auto_approve:
            return {
                'success': False,
                'message': 'Updates require manual approval for safety'
            }
        
        try:
            if self.system == "Linux":
                return self._install_linux_updates()
            elif self.system == "Darwin":
                return self._install_macos_updates()
            elif self.system == "Windows":
                return self._install_windows_updates()
            else:
                return {
                    'success': False,
                    'message': f'Update installation not supported on {self.system}'
                }
        except Exception as e:
            logger.error(f"Error installing updates: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _install_linux_updates(self) -> Dict[str, Any]:
        """Install updates on Linux"""
        try:
            # Try apt
            result = subprocess.run(
                ['sudo', 'apt', 'upgrade', '-y'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': 'System updates installed successfully'
                }
            else:
                return {
                    'success': False,
                    'message': f'Update failed: {result.stderr}'
                }
        except FileNotFoundError:
            pass
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        # Try dnf
        try:
            result = subprocess.run(
                ['sudo', 'dnf', 'upgrade', '-y'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': 'System updates installed successfully'
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        return {
            'success': False,
            'message': 'No supported package manager found'
        }
    
    def _install_macos_updates(self) -> Dict[str, Any]:
        """Install updates on macOS"""
        try:
            result = subprocess.run(
                ['sudo', 'softwareupdate', '-i', '-a'],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            return {
                'success': result.returncode == 0,
                'message': 'Updates installed' if result.returncode == 0 else f'Failed: {result.stderr}'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _install_windows_updates(self) -> Dict[str, Any]:
        """Install updates on Windows"""
        return {
            'success': False,
            'message': 'Automatic Windows updates require admin privileges. Please use Windows Update settings.'
        }


# Singleton instance
_updater = SystemUpdater()


def check_for_updates() -> Dict[str, Any]:
    """Check for system updates"""
    return _updater.check_updates()


def install_system_updates(auto_approve: bool = False) -> Dict[str, Any]:
    """Install system updates"""
    return _updater.install_updates(auto_approve)


if __name__ == "__main__":
    # Test the updater
    print("Checking for updates...")
    result = check_for_updates()
    print(f"Result: {result}")
