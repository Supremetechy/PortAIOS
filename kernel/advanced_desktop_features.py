"""
Advanced Desktop Features for AIOS
Provides clipboard access, screenshots, notifications, and system interactions
"""

import os
import platform
import logging
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
import base64

logger = logging.getLogger("AIOS.AdvancedDesktop")

try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    EEL_AVAILABLE = False
    logger.warning("Eel not available - advanced desktop features disabled")


class AdvancedDesktopFeatures:
    """Advanced desktop integration features"""
    
    def __init__(self):
        self.system = platform.system()
        self.clipboard_backend = self._detect_clipboard_backend()
        self.screenshot_backend = self._detect_screenshot_backend()
        logger.info(f"Advanced desktop features initialized for {self.system}")
    
    def _detect_clipboard_backend(self) -> Optional[str]:
        """Detect available clipboard backend"""
        try:
            if self.system == "Darwin":  # macOS
                return "pbcopy"
            elif self.system == "Windows":
                return "clip"
            else:  # Linux
                # Try to find xclip or xsel
                for cmd in ["xclip", "xsel"]:
                    if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
                        return cmd
            return None
        except Exception as e:
            logger.warning(f"Could not detect clipboard backend: {e}")
            return None
    
    def _detect_screenshot_backend(self) -> Optional[str]:
        """Detect available screenshot backend"""
        try:
            if self.system == "Darwin":  # macOS
                return "screencapture"
            elif self.system == "Windows":
                return "windows"  # Will use PowerShell
            else:  # Linux
                # Try to find screenshot tools
                for cmd in ["scrot", "import", "gnome-screenshot"]:
                    if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
                        return cmd
            return None
        except Exception as e:
            logger.warning(f"Could not detect screenshot backend: {e}")
            return None
    
    # ============ CLIPBOARD OPERATIONS ============
    
    def get_clipboard(self) -> Dict[str, Any]:
        """Get text from clipboard"""
        try:
            if self.system == "Darwin":
                result = subprocess.run(["pbpaste"], capture_output=True, text=True)
                return {"success": True, "text": result.stdout}
            
            elif self.system == "Windows":
                # Use PowerShell to get clipboard
                result = subprocess.run(
                    ["powershell", "-command", "Get-Clipboard"],
                    capture_output=True,
                    text=True
                )
                return {"success": True, "text": result.stdout.strip()}
            
            else:  # Linux
                if self.clipboard_backend == "xclip":
                    result = subprocess.run(
                        ["xclip", "-selection", "clipboard", "-o"],
                        capture_output=True,
                        text=True
                    )
                    return {"success": True, "text": result.stdout}
                elif self.clipboard_backend == "xsel":
                    result = subprocess.run(
                        ["xsel", "--clipboard", "--output"],
                        capture_output=True,
                        text=True
                    )
                    return {"success": True, "text": result.stdout}
                else:
                    return {"success": False, "error": "No clipboard backend available"}
        
        except Exception as e:
            logger.error(f"Error getting clipboard: {e}")
            return {"success": False, "error": str(e)}
    
    def set_clipboard(self, text: str) -> Dict[str, Any]:
        """Set clipboard text"""
        try:
            if self.system == "Darwin":
                subprocess.run(["pbcopy"], input=text.encode(), check=True)
                return {"success": True}
            
            elif self.system == "Windows":
                subprocess.run(
                    ["powershell", "-command", f"Set-Clipboard -Value '{text}'"],
                    check=True
                )
                return {"success": True}
            
            else:  # Linux
                if self.clipboard_backend == "xclip":
                    subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=text.encode(),
                        check=True
                    )
                    return {"success": True}
                elif self.clipboard_backend == "xsel":
                    subprocess.run(
                        ["xsel", "--clipboard", "--input"],
                        input=text.encode(),
                        check=True
                    )
                    return {"success": True}
                else:
                    return {"success": False, "error": "No clipboard backend available"}
        
        except Exception as e:
            logger.error(f"Error setting clipboard: {e}")
            return {"success": False, "error": str(e)}
    
    # ============ SCREENSHOT OPERATIONS ============
    
    def take_screenshot(self, save_path: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot"""
        try:
            if not save_path:
                # Default to temp directory
                import tempfile
                import time
                timestamp = int(time.time())
                save_path = os.path.join(tempfile.gettempdir(), f"aios_screenshot_{timestamp}.png")
            
            save_path = Path(save_path).expanduser().resolve()
            
            if self.system == "Darwin":
                subprocess.run(["screencapture", "-x", str(save_path)], check=True)
            
            elif self.system == "Windows":
                # Use PowerShell to take screenshot
                ps_script = f"""
                Add-Type -AssemblyName System.Windows.Forms
                $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
                $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
                $bitmap.Save('{save_path}')
                """
                subprocess.run(["powershell", "-command", ps_script], check=True)
            
            else:  # Linux
                if self.screenshot_backend == "scrot":
                    subprocess.run(["scrot", str(save_path)], check=True)
                elif self.screenshot_backend == "import":
                    subprocess.run(["import", "-window", "root", str(save_path)], check=True)
                elif self.screenshot_backend == "gnome-screenshot":
                    subprocess.run(["gnome-screenshot", "-f", str(save_path)], check=True)
                else:
                    return {"success": False, "error": "No screenshot backend available"}
            
            # Read screenshot and encode to base64
            with open(save_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            return {
                "success": True,
                "path": str(save_path),
                "data": image_data,
                "size": os.path.getsize(save_path)
            }
        
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return {"success": False, "error": str(e)}
    
    def take_window_screenshot(self, window_title: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot of a specific window"""
        try:
            import tempfile
            import time
            timestamp = int(time.time())
            save_path = os.path.join(tempfile.gettempdir(), f"aios_window_{timestamp}.png")
            
            if self.system == "Darwin":
                # Interactive window selection on macOS
                subprocess.run(["screencapture", "-w", save_path], check=True)
            
            elif self.system == "Windows":
                # Would need specific window handling - simplified for now
                return {"success": False, "error": "Window screenshot not yet implemented for Windows"}
            
            else:  # Linux
                if self.screenshot_backend == "scrot":
                    subprocess.run(["scrot", "-s", save_path], check=True)
                elif self.screenshot_backend == "import":
                    subprocess.run(["import", save_path], check=True)
                else:
                    return {"success": False, "error": "No screenshot backend available"}
            
            with open(save_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            return {
                "success": True,
                "path": save_path,
                "data": image_data,
                "size": os.path.getsize(save_path)
            }
        
        except Exception as e:
            logger.error(f"Error taking window screenshot: {e}")
            return {"success": False, "error": str(e)}
    
    # ============ NOTIFICATION OPERATIONS ============
    
    def send_notification(self, title: str, message: str, timeout: int = 5000) -> Dict[str, Any]:
        """Send a system notification"""
        try:
            if self.system == "Darwin":
                # Use osascript for macOS notifications
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(["osascript", "-e", script], check=True)
            
            elif self.system == "Windows":
                # Use PowerShell for Windows notifications
                ps_script = f"""
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
                
                $template = @"
                <toast>
                    <visual>
                        <binding template="ToastText02">
                            <text id="1">{title}</text>
                            <text id="2">{message}</text>
                        </binding>
                    </visual>
                </toast>
"@
                
                $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
                $xml.LoadXml($template)
                $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("AIOS").Show($toast)
                """
                subprocess.run(["powershell", "-command", ps_script], check=True)
            
            else:  # Linux
                # Use notify-send for Linux
                subprocess.run(
                    ["notify-send", title, message, "-t", str(timeout)],
                    check=True
                )
            
            return {"success": True}
        
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {"success": False, "error": str(e)}
    
    # ============ SYSTEM OPERATIONS ============
    
    def get_active_window(self) -> Dict[str, Any]:
        """Get information about the currently active window"""
        try:
            if self.system == "Darwin":
                script = '''
                tell application "System Events"
                    set frontApp to name of first application process whose frontmost is true
                    set frontWindow to name of front window of application process frontApp
                    return {frontApp, frontWindow}
                end tell
                '''
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True
                )
                parts = result.stdout.strip().split(", ")
                return {
                    "success": True,
                    "app": parts[0] if len(parts) > 0 else "",
                    "window": parts[1] if len(parts) > 1 else ""
                }
            
            elif self.system == "Windows":
                # Use PowerShell to get active window
                ps_script = """
                Add-Type @"
                    using System;
                    using System.Runtime.InteropServices;
                    public class Win32 {
                        [DllImport("user32.dll")]
                        public static extern IntPtr GetForegroundWindow();
                        [DllImport("user32.dll")]
                        public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
                    }
"@
                $handle = [Win32]::GetForegroundWindow()
                $title = New-Object System.Text.StringBuilder 256
                [Win32]::GetWindowText($handle, $title, 256)
                Write-Output $title.ToString()
                """
                result = subprocess.run(
                    ["powershell", "-command", ps_script],
                    capture_output=True,
                    text=True
                )
                return {
                    "success": True,
                    "window": result.stdout.strip()
                }
            
            else:  # Linux
                # Try xdotool first
                try:
                    result = subprocess.run(
                        ["xdotool", "getactivewindow", "getwindowname"],
                        capture_output=True,
                        text=True
                    )
                    return {
                        "success": True,
                        "window": result.stdout.strip()
                    }
                except FileNotFoundError:
                    return {"success": False, "error": "xdotool not available"}
                except subprocess.CalledProcessError as e:
                    logger.warning(f"xdotool failed: {e}")
                    return {"success": False, "error": "Failed to get active window"}
                except Exception as e:
                    logger.error(f"Unexpected error getting active window: {e}")
                    return {"success": False, "error": str(e)}
        
        except Exception as e:
            logger.error(f"Error getting active window: {e}")
            return {"success": False, "error": str(e)}


def setup_advanced_desktop_features():
    """Setup advanced desktop features with Eel if available"""
    if not EEL_AVAILABLE:
        logger.warning("Eel not available - skipping advanced desktop features setup")
        return None
    
    features = AdvancedDesktopFeatures()
    
    @eel.expose
    def get_clipboard() -> Dict[str, Any]:
        """Get clipboard text"""
        return features.get_clipboard()
    
    @eel.expose
    def set_clipboard(text: str) -> Dict[str, Any]:
        """Set clipboard text"""
        return features.set_clipboard(text)
    
    @eel.expose
    def take_screenshot(save_path: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot"""
        return features.take_screenshot(save_path)
    
    @eel.expose
    def take_window_screenshot(window_title: Optional[str] = None) -> Dict[str, Any]:
        """Take a window screenshot"""
        return features.take_window_screenshot(window_title)
    
    @eel.expose
    def send_notification(title: str, message: str, timeout: int = 5000) -> Dict[str, Any]:
        """Send a system notification"""
        return features.send_notification(title, message, timeout)
    
    @eel.expose
    def get_active_window() -> Dict[str, Any]:
        """Get active window info"""
        return features.get_active_window()
    
    logger.info("Advanced desktop features setup complete")
    return features


__all__ = ['AdvancedDesktopFeatures', 'setup_advanced_desktop_features']
