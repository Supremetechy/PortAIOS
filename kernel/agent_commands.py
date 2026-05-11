"""
AIOS Agent Command Handlers

Each handler receives a context dict and returns a CommandResult.
Handlers perform real OS-level operations via subprocess, kernel
subsystems, or platform APIs. They are pure Python — no web imports.
"""

import glob
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AIOS.agent.commands")


@dataclass
class CommandResult:
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    speak: str = ""  # text for TTS to say

    def __bool__(self):
        return self.success


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: List[str], timeout: int = 15, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, **kw,
    )


def _system() -> str:
    return platform.system()  # Darwin, Linux, Windows


# ═══════════════════════════════════════════════════════════════════════════
# 1. LIST INSTALLED PROGRAMS
# ═══════════════════════════════════════════════════════════════════════════

def list_programs(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Discover natively installed programs / applications."""
    system = _system()
    apps: List[str] = []

    try:
        if system == "Darwin":
            # macOS: scan /Applications + Homebrew
            app_dir = Path("/Applications")
            if app_dir.exists():
                apps = sorted(
                    p.stem for p in app_dir.iterdir()
                    if p.suffix == ".app"
                )
            # Add Homebrew CLI tools
            brew_bin = Path("/opt/homebrew/bin")
            if not brew_bin.exists():
                brew_bin = Path("/usr/local/bin")
            if brew_bin.exists():
                cli_tools = sorted(
                    p.name for p in brew_bin.iterdir()
                    if p.is_file() and os.access(p, os.X_OK)
                )[:30]
                apps.extend(f"[cli] {t}" for t in cli_tools)

        elif system == "Linux":
            # dpkg, rpm, or flatpak
            for cmd_name, cmd_args in [
                ("dpkg", ["dpkg", "--get-selections"]),
                ("rpm", ["rpm", "-qa", "--qf", "%{NAME}\n"]),
                ("flatpak", ["flatpak", "list", "--app", "--columns=application"]),
            ]:
                try:
                    r = _run(cmd_args, timeout=10)
                    if r.returncode == 0:
                        lines = [l.strip().split("\t")[0] for l in r.stdout.strip().splitlines() if l.strip()]
                        apps.extend(lines[:80])
                        break
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            # Also scan /usr/share/applications for .desktop files
            desktop_dir = Path("/usr/share/applications")
            if desktop_dir.exists():
                for dp in sorted(desktop_dir.glob("*.desktop"))[:40]:
                    apps.append(f"[gui] {dp.stem}")

        elif system == "Windows":
            r = _run([
                "powershell", "-Command",
                "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object DisplayName | Format-Table -HideTableHeaders",
            ], timeout=20)
            if r.returncode == 0:
                apps = [l.strip() for l in r.stdout.splitlines() if l.strip()]

        count = len(apps)
        display = apps[:25]
        msg = "\n".join(display)
        if count > 25:
            msg += f"\n... and {count - 25} more"

        return CommandResult(
            success=True,
            message=msg,
            data={"programs": apps, "count": count},
            speak=f"I found {count} programs on your system. Some notable ones include {', '.join(display[:5])}.",
        )
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Failed to list programs: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 2. OPEN WEB BROWSER
# ═══════════════════════════════════════════════════════════════════════════

def open_browser(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Open the default web browser, optionally to a URL."""
    import webbrowser
    url = ctx.get("url", "https://www.google.com")
    try:
        webbrowser.open(url)
        return CommandResult(True, f"Opened browser to {url}", speak=f"Opening browser to {url}")
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Could not open browser: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 3. FILE SYSTEM BROWSING
# ═══════════════════════════════════════════════════════════════════════════

def browse_filesystem(ctx: Dict[str, Any] = {}) -> CommandResult:
    """List files in a directory."""
    path = ctx.get("path", str(Path.home()))
    show_hidden = ctx.get("show_hidden", False)
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return CommandResult(False, f"Path does not exist: {path}", speak=f"Path {path} does not exist.")
        if not p.is_dir():
            # Single file info
            stat = p.stat()
            size = stat.st_size
            mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            return CommandResult(
                True,
                f"{p.name}  {size:,} bytes  modified {mod_time}",
                data={"type": "file", "name": p.name, "size": size, "modified": mod_time},
                speak=f"{p.name} is {size:,} bytes, last modified {mod_time}.",
            )

        entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        if not show_hidden:
            entries = [e for e in entries if not e.name.startswith(".")]

        items = []
        for e in entries[:40]:
            kind = "dir" if e.is_dir() else "file"
            size = e.stat().st_size if e.is_file() else 0
            items.append({"name": e.name, "type": kind, "size": size})

        lines = []
        for item in items:
            prefix = "[DIR]  " if item["type"] == "dir" else "       "
            size_str = f'{item["size"]:>10,}' if item["type"] == "file" else "          "
            lines.append(f"{prefix}{item['name']:40s} {size_str}")

        msg = f"Contents of {p}:\n" + "\n".join(lines)
        dirs = sum(1 for i in items if i["type"] == "dir")
        files = sum(1 for i in items if i["type"] == "file")
        return CommandResult(
            True, msg, data={"path": str(p), "items": items},
            speak=f"Directory {p.name} contains {dirs} folders and {files} files.",
        )
    except PermissionError:
        return CommandResult(False, f"Permission denied: {path}", speak="Permission denied.")
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Error browsing filesystem: {e}")

# 3.5 CREATE DIRECTORY
def create_directory(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Create a new directory."""
    path = ctx.get("path", str(Path.home()))
    try:
        p = Path(path).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return CommandResult(True, f"Created directory: {p}", speak=f"Directory {p.name} created.")
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Could not create directory: {e}")
    

# ═══════════════════════════════════════════════════════════════════════════
# 4. CREATE DOCUMENT
# ═══════════════════════════════════════════════════════════════════════════

def create_document(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Create a new text file / document."""
    name = ctx.get("name", f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    content = ctx.get("content", "")
    directory = ctx.get("directory", str(Path.home() / "Documents"))

    try:
        d = Path(directory).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        filepath = d / name
        filepath.write_text(content or f"# Created by AIOS\n# {datetime.now().isoformat()}\n")
        return CommandResult(
            True,
            f"Created: {filepath}",
            data={"path": str(filepath)},
            speak=f"Document {name} created in {d.name}.",
        )
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Could not create document: {e}")
    
# 4.5 Write to documents
def write_document(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Write to an existing text file / document."""
    name = ctx.get("name", f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    content = ctx.get("content", "")
    directory = ctx.get("directory", str(Path.home() / "Documents"))

    try:
        d = Path(directory).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        filepath = d / name
        if not filepath.exists():
            return CommandResult(False, f"File does not exist: {filepath}", speak=f"File {name} does not exist.")
        with filepath.open("a") as f:
            f.write("\n" + content)
        return CommandResult(
            True,
            f"Updated: {filepath}",
            data={"path": str(filepath)},
            speak=f"Document {name} updated in {d.name}.",
        )
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Could not update document: {e}")
    
# 4.6 Read from documents
def read_document(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Read from an existing text file / document."""
    name = ctx.get("name", f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    directory = ctx.get("directory", str(Path.home() / "Documents"))

    try:
        d = Path(directory).expanduser()
        filepath = d / name
        if not filepath.exists():
            return CommandResult(False, f"File does not exist: {filepath}", speak=f"File {name} does not exist.")
        content = filepath.read_text()
        return CommandResult(
            True,
            f"Content of {filepath}:\n{content[:2000]}",
            data={"path": str(filepath), "content": content},
            speak=f"Read document {name} from {d.name}.",
        )
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Could not read document: {e}")
    
# 4.7 Edit document (overwrite)
def edit_document(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Edit an existing text file / document."""
    name = ctx.get("name", f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    content = ctx.get("content", "")
    directory = ctx.get("directory", str(Path.home() / "Documents"))

    try:
        d = Path(directory).expanduser()
        filepath = d / name
        filepath.write_text(content)
        return CommandResult(
            True,
            f"Edited: {filepath}",
            data={"path": str(filepath)},
            speak=f"Document {name} edited in {d.name}.",
        )
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Could not edit document: {e}")
    
    
# 4.8 Delete document
def delete_document(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Delete an existing text file / document."""
    name = ctx.get("name", f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    directory = ctx.get("directory", str(Path.home() / "Documents"))

    try:
        d = Path(directory).expanduser()
        filepath = d / name
        if not filepath.exists():
            return CommandResult(False, f"File does not exist: {filepath}", speak=f"File {name} does not exist.")
        filepath.unlink()
        return CommandResult(
            True,
            f"Deleted: {filepath}",
            data={"path": str(filepath)},
            speak=f"Document {name} deleted from {d.name}.",
        )
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Could not delete document: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 5. TAKE SCREENSHOT / SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════════

def take_snapshot(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Take a screenshot / system snapshot."""
    system = _system()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = ctx.get("path", str(Path.home() / "Desktop" / f"snapshot_{ts}.png"))

    try:
        if system == "Darwin":
            _run(["screencapture", "-x", dest])
        elif system == "Linux":
            # Try multiple tools
            for tool_cmd in [
                ["gnome-screenshot", "-f", dest],
                ["scrot", dest],
                ["import", "-window", "root", dest],
            ]:
                try:
                    r = _run(tool_cmd, timeout=5)
                    if r.returncode == 0:
                        break
                except FileNotFoundError:
                    continue
        elif system == "Windows":
            _run([
                "powershell", "-Command",
                f"Add-Type -AssemblyName System.Windows.Forms; "
                f"[System.Windows.Forms.Screen]::PrimaryScreen | ForEach-Object {{ "
                f"$bmp = New-Object System.Drawing.Bitmap($_.Bounds.Width, $_.Bounds.Height); "
                f"$g = [System.Drawing.Graphics]::FromImage($bmp); "
                f"$g.CopyFromScreen($_.Bounds.Location, [System.Drawing.Point]::Empty, $_.Bounds.Size); "
                f"$bmp.Save('{dest}') }}",
            ])

        if Path(dest).exists():
            return CommandResult(True, f"Screenshot saved: {dest}",
                                data={"path": dest}, speak="Screenshot captured.")
        else:
            return CommandResult(False, "Screenshot tool not found",
                                speak="No screenshot tool available on this system.")
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Screenshot failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 6. CHECK NETWORK CONNECTIONS
# ═══════════════════════════════════════════════════════════════════════════

def check_network(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Show network interfaces, connectivity, and active connections."""
    results = {"interfaces": [], "internet": False, "connections": []}
    lines = []

    try:
        # Get interfaces
        try:
            from kernel.network import NetworkManager
            nm = NetworkManager()
            nm.initialize()
            for iface in nm.interfaces.values():
                info = f"{iface.name}: {iface.state.value}"
                if iface.ip_addresses:
                    info += f" — {iface.ip_addresses[0].address}"
                lines.append(info)
                results["interfaces"].append({
                    "name": iface.name,
                    "state": iface.state.value,
                    "ips": [str(a) for a in iface.ip_addresses],
                })
        except Exception:
            # Fallback to system commands
            system = _system()
            if system == "Darwin":
                r = _run(["ifconfig"])
            else:
                r = _run(["ip", "addr", "show"])
            if r.returncode == 0:
                lines.append(r.stdout[:500])

        # Test internet connectivity
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            results["internet"] = True
            lines.append("Internet: CONNECTED")
        except OSError:
            lines.append("Internet: OFFLINE")

        # Active connections
        try:
            if _system() == "Darwin":
                r = _run(["netstat", "-an", "-p", "tcp"])
            else:
                r = _run(["ss", "-tuln"])
            if r.returncode == 0:
                conn_lines = r.stdout.strip().splitlines()[:15]
                lines.append(f"\nActive connections ({len(conn_lines)}):")
                lines.extend(conn_lines)
        except Exception:
            pass

        iface_count = len(results["interfaces"])
        inet_status = "online" if results["internet"] else "offline"
        return CommandResult(
            True, "\n".join(lines), data=results,
            speak=f"Found {iface_count} network interfaces. Internet is {inet_status}.",
        )
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Network check failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 7. CHECK BLUETOOTH
# ═══════════════════════════════════════════════════════════════════════════

def check_bluetooth(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Scan for nearby Bluetooth devices."""
    system = _system()
    devices = []

    try:
        if system == "Darwin":
            # macOS: system_profiler
            r = _run(["system_profiler", "SPBluetoothDataType", "-json"], timeout=10)
            if r.returncode == 0:
                data = json.loads(r.stdout)
                bt = data.get("SPBluetoothDataType", [{}])[0]
                # Connected devices
                for section_key in ["device_connected", "device_not_connected"]:
                    section = bt.get(section_key, [])
                    if isinstance(section, list):
                        for entry in section:
                            if isinstance(entry, dict):
                                for name, info in entry.items():
                                    devices.append({
                                        "name": name,
                                        "connected": section_key == "device_connected",
                                        "address": info.get("device_address", ""),
                                    })

        elif system == "Linux":
            # bluetoothctl
            try:
                r = _run(["bluetoothctl", "devices"], timeout=5)
                if r.returncode == 0:
                    for line in r.stdout.strip().splitlines():
                        parts = line.split(maxsplit=2)
                        if len(parts) >= 3:
                            devices.append({
                                "name": parts[2],
                                "address": parts[1],
                                "connected": False,
                            })
            except FileNotFoundError:
                pass

        if devices:
            lines = [f"{'Name':30s} {'Address':20s} {'Status'}" ]
            for d in devices:
                status = "Connected" if d.get("connected") else "Paired"
                lines.append(f"{d['name']:30s} {d.get('address',''):20s} {status}")
            return CommandResult(
                True, "\n".join(lines), data={"devices": devices},
                speak=f"Found {len(devices)} Bluetooth devices.",
            )
        else:
            return CommandResult(True, "No Bluetooth devices found.",
                                data={"devices": []},
                                speak="No Bluetooth devices were found.")
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Bluetooth scan failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 8. DOWNLOAD / INSTALL SOFTWARE
# ═══════════════════════════════════════════════════════════════════════════

def download_software(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Download or install a software package."""
    package = ctx.get("package", "")
    if not package:
        return CommandResult(False, "No package name specified.",
                            speak="What software would you like to install?")

    system = _system()
    try:
        if system == "Darwin":
            # Try Homebrew
            if shutil.which("brew"):
                r = _run(["brew", "install", package], timeout=120)
                if r.returncode == 0:
                    return CommandResult(True, f"Installed {package} via Homebrew",
                                        speak=f"{package} installed successfully via Homebrew.")
                else:
                    return CommandResult(False, f"Homebrew error: {r.stderr[:200]}",
                                        speak=f"Failed to install {package}. {r.stderr[:80]}")
            else:
                return CommandResult(False, "Homebrew not found",
                                    speak="Homebrew is not installed. Install it first to manage packages.")

        elif system == "Linux":
            # Try apt, then dnf, then pacman
            for pm, cmd in [
                ("apt", ["sudo", "apt-get", "install", "-y", package]),
                ("dnf", ["sudo", "dnf", "install", "-y", package]),
                ("pacman", ["sudo", "pacman", "-S", "--noconfirm", package]),
            ]:
                if shutil.which(pm.split()[0] if " " in pm else pm):
                    r = _run(cmd, timeout=120)
                    if r.returncode == 0:
                        return CommandResult(True, f"Installed {package} via {pm}",
                                            speak=f"{package} installed successfully.")
                    else:
                        return CommandResult(False, f"{pm} error: {r.stderr[:200]}",
                                            speak=f"Failed to install {package}.")

        elif system == "Windows":
            if shutil.which("winget"):
                r = _run(["winget", "install", package], timeout=120)
                if r.returncode == 0:
                    return CommandResult(True, f"Installed {package} via winget",
                                        speak=f"{package} installed.")

        # pip fallback for Python packages
        r = _run([sys.executable, "-m", "pip", "install", package], timeout=120)
        if r.returncode == 0:
            return CommandResult(True, f"Installed {package} via pip",
                                speak=f"Python package {package} installed.")

        return CommandResult(False, "No package manager available",
                            speak="No supported package manager found.")
    except subprocess.TimeoutExpired:
        return CommandResult(False, "Installation timed out",
                            speak=f"Installation of {package} timed out.")
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Installation failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 9. CHECK COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════════════

def check_compatibility(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Check system compatibility for a given software or requirement."""
    target = ctx.get("target", "")
    try:
        from kernel.compatibility_checker import CompatibilityChecker
        checker = CompatibilityChecker()

        meta = {}
        if target.endswith(".txt"):
            meta["requirements_path"] = target
        elif "/" in target or "\\" in target:
            meta["binary_path"] = target
        elif ":" in target:
            meta["container_image"] = target
        else:
            meta["binary_path"] = shutil.which(target) or target

        report = checker.check(meta)
        lines = [f"Compatible: {'Yes' if report.compatible else 'No'}"]
        if report.issues:
            lines.append("Issues:")
            for issue in report.issues:
                lines.append(f"  - {issue}")
        if report.suggestions:
            lines.append("Suggestions:")
            for s in report.suggestions:
                lines.append(f"  - {s}")

        compat_str = "compatible" if report.compatible else "not compatible"
        return CommandResult(
            True, "\n".join(lines),
            data={"compatible": report.compatible, "issues": report.issues},
            speak=f"{target} is {compat_str} with this system.",
        )
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Compatibility check failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 10. OPEN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

def open_application(ctx: Dict[str, Any] = {}) -> CommandResult:
    import subprocess
    import shutil
    from pathlib import Path
    from datetime import datetime
    import platform
    import sys

    """Open an installed application by name."""
    app_name = ctx.get("app", "")
    if not app_name:
        return CommandResult(False, "No application specified.",
                            speak="Which application would you like to open?")

    system = _system()
    try:
        if system == "Darwin":
            # Try exact match first, then fuzzy
            app_path = Path(f"/Applications/{app_name}.app")
            if not app_path.exists():
                # Fuzzy search
                matches = list(Path("/Applications").glob(f"*{app_name}*.app"))
                if matches:
                    app_path = matches[0]
                else:
                    # Try 'open -a' which does its own fuzzy match
                    r = _run(["open", "-a", app_name])
                    if r.returncode == 0:
                        return CommandResult(True, f"Opened {app_name}",
                                            speak=f"Opening {app_name}.")
                    return CommandResult(False, f"Application '{app_name}' not found.",
                                        speak=f"I couldn't find {app_name}.")
            _run(["open", str(app_path)])
            return CommandResult(True, f"Opened {app_path.stem}",
                                speak=f"Opening {app_path.stem}.")

        elif system == "Linux":
            # Try xdg-open, then direct command
            binary = shutil.which(app_name.lower())
            if binary:
                subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return CommandResult(True, f"Opened {app_name}",
                                    speak=f"Opening {app_name}.")
            # Search .desktop files
            desktop_dirs = [
                Path("/usr/share/applications"),
                Path.home() / ".local/share/applications",
            ]
            for dd in desktop_dirs:
                for dp in dd.glob("*.desktop"):
                    if app_name.lower() in dp.stem.lower():
                        _run(["xdg-open", str(dp)])
                        return CommandResult(True, f"Opened {dp.stem}",
                                            speak=f"Opening {dp.stem}.")
            return CommandResult(False, f"Application '{app_name}' not found.",
                                speak=f"I couldn't find {app_name}.")

        elif system == "Windows":
            r = _run(["cmd", "/c", "start", "", app_name])
            if r.returncode == 0:
                return CommandResult(True, f"Opened {app_name}",
                                    speak=f"Opening {app_name}.")
            return CommandResult(False, f"Could not open {app_name}",
                                speak=f"Failed to open {app_name}.")

        return CommandResult(False, f"Unsupported platform: {system}",
                            speak=f"I can't launch applications on {system}.")

    except Exception as e:
        return CommandResult(False, str(e), speak=f"Failed to open {app_name}: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 11. SYSTEM STATUS
# ═══════════════════════════════════════════════════════════════════════════

def system_status(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Get current system resource usage."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot

        lines = [
            f"CPU Usage:    {cpu}%",
            f"Memory:       {mem.percent}% ({mem.used // (1024**3):.1f} / {mem.total // (1024**3):.1f} GB)",
            f"Disk:         {disk.percent}% ({disk.used // (1024**3):.1f} / {disk.total // (1024**3):.1f} GB)",
            f"Uptime:       {str(uptime).split('.')[0]}",
            f"Platform:     {platform.system()} {platform.release()}",
            f"Architecture: {platform.machine()}",
            f"Python:       {platform.python_version()}",
            f"Hostname:     {platform.node()}",
        ]

        return CommandResult(
            True, "\n".join(lines),
            data={"cpu": cpu, "memory": mem.percent, "disk": disk.percent},
            speak=f"CPU at {cpu}%, memory at {mem.percent}%, disk at {disk.percent}%. System uptime {str(uptime).split('.')[0]}.",
        )
    except ImportError:
        return CommandResult(
            True,
            f"Platform: {platform.system()} {platform.release()} {platform.machine()}",
            speak=f"Running {platform.system()} {platform.release()} on {platform.machine()}.",
        )


# ═══════════════════════════════════════════════════════════════════════════
# 12. SEARCH FILES
# ═══════════════════════════════════════════════════════════════════════════

def search_files(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Search for files by name pattern."""
    pattern = ctx.get("pattern", "")
    directory = ctx.get("directory", str(Path.home()))
    if not pattern:
        return CommandResult(False, "No search pattern specified.",
                            speak="What file are you looking for?")

    try:
        p = Path(directory).expanduser().resolve()
        matches = []
        for match in p.rglob(f"*{pattern}*"):
            if len(matches) >= 20:
                break
            try:
                matches.append({
                    "path": str(match),
                    "name": match.name,
                    "size": match.stat().st_size if match.is_file() else 0,
                    "type": "file" if match.is_file() else "dir",
                })
            except (PermissionError, OSError):
                continue

        if matches:
            lines = [f"{m['name']:40s} {m['path']}" for m in matches]
            return CommandResult(
                True, "\n".join(lines), data={"matches": matches},
                speak=f"Found {len(matches)} files matching {pattern}.",
            )
        else:
            return CommandResult(True, f"No files found matching '{pattern}'",
                                speak=f"No files found matching {pattern}.")
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Search failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 13. RUN SHELL COMMAND
# ═══════════════════════════════════════════════════════════════════════════

def run_command(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Execute a shell command and return its output."""
    cmd = ctx.get("command", "")
    if not cmd:
        return CommandResult(False, "No command specified.",
                            speak="What command should I run?")

    # Safety: block destructive commands
    blocked = ["rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb", "format c:"]
    cmd_lower = cmd.lower()
    for b in blocked:
        if b in cmd_lower:
            return CommandResult(False, f"Blocked dangerous command: {cmd}",
                                speak="That command is blocked for safety reasons.")

    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
        )
        output = r.stdout[:2000] if r.stdout else r.stderr[:2000]
        success = r.returncode == 0
        return CommandResult(
            success, output or "(no output)",
            data={"exit_code": r.returncode},
            speak=f"Command {'completed successfully' if success else 'failed with errors'}.",
        )
    except subprocess.TimeoutExpired:
        return CommandResult(False, "Command timed out after 30 seconds.",
                            speak="The command timed out.")
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Command failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 14. HARDWARE INFO
# ═══════════════════════════════════════════════════════════════════════════

def hardware_info(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Get detailed hardware information."""
    try:
        from kernel.hardware_detection import HardwareDetector
        detector = HardwareDetector()
        specs = detector.detect_all()

        lines = []
        for proc in specs.processors:
            kind = proc.processor_type.value.upper()
            lines.append(f"{kind}: {proc.vendor.value} {proc.model}")
            if proc.cores:
                lines.append(f"  Cores: {proc.cores}, Threads: {proc.threads}")
            if proc.memory_gb:
                lines.append(f"  VRAM: {proc.memory_gb:.1f} GB")

        lines.append(f"Memory: {specs.memory.total_gb:.1f} GB total, {specs.memory.available_gb:.1f} GB available")
        lines.append(f"Storage: {len(specs.storage_devices)} device(s)")
        for dev in specs.storage_devices:
            lines.append(f"  {dev.device_name}: {dev.total_gb:.1f} GB")

        cpu_name = specs.processors[0].model if specs.processors else "unknown"
        gpu_count = sum(1 for p in specs.processors if p.processor_type.value == "gpu")
        return CommandResult(
            True, "\n".join(lines), data={"specs": str(specs)},
            speak=f"Your system has a {cpu_name} processor, {specs.memory.total_gb:.0f} gigabytes of RAM, and {gpu_count} GPU{'s' if gpu_count != 1 else ''}.",
        )
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Hardware detection failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 15. OPEN FILE MANAGER
# ═══════════════════════════════════════════════════════════════════════════

def open_file_manager(ctx: Dict[str, Any] = {}) -> CommandResult:
    """Open the system file manager to a directory."""
    path = ctx.get("path", str(Path.home()))
    system = _system()
    try:
        if system == "Darwin":
            _run(["open", path])
        elif system == "Linux":
            _run(["xdg-open", path])
        elif system == "Windows":
            _run(["explorer", path])
        return CommandResult(True, f"Opened file manager at {path}",
                            speak=f"Opening file manager.")
    except Exception as e:
        return CommandResult(False, str(e), speak=f"Could not open file manager: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# 16. PROCESS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def list_processes(ctx: Dict[str, Any] = {}) -> CommandResult:
    """List running processes sorted by CPU or memory usage."""
    try:
        import psutil
        sort_by = ctx.get("sort", "cpu")
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        key = "cpu_percent" if sort_by == "cpu" else "memory_percent"
        procs.sort(key=lambda x: x.get(key, 0) or 0, reverse=True)
        top = procs[:15]

        lines = [f"{'PID':>7s}  {'CPU%':>6s}  {'MEM%':>6s}  {'Name'}"]
        for p in top:
            lines.append(
                f"{p['pid']:7d}  {(p.get('cpu_percent') or 0):5.1f}%  "
                f"{(p.get('memory_percent') or 0):5.1f}%  {p['name']}"
            )

        return CommandResult(
            True, "\n".join(lines), data={"processes": top},
            speak=f"Showing top {len(top)} processes. The most active is {top[0]['name']}.",
        )
    except ImportError:
        return CommandResult(False, "psutil not available", speak="Process monitoring requires psutil.")


# ═══════════════════════════════════════════════════════════════════════════
# COMMAND REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

COMMANDS = {
    "list_programs":      list_programs,
    "open_browser":       open_browser,
    "browse_filesystem":  browse_filesystem,
    "create_document":    create_document,
    "take_snapshot":      take_snapshot,
    "check_network":      check_network,
    "check_bluetooth":    check_bluetooth,
    "download_software":  download_software,
    "check_compatibility": check_compatibility,
    "open_application":   open_application,
    "system_status":      system_status,
    "search_files":       search_files,
    "run_command":        run_command,
    "hardware_info":      hardware_info,
    "open_file_manager":  open_file_manager,
    "list_processes":     list_processes,
    "write_document":     write_document,
    "read_document":      read_document,
    "edit_document":      edit_document,
    "delete_document":    delete_document,
    "create_directory":   create_directory
    
}