"""
UI Voice Commands Integration
Extends AIOS voice commands to support dynamic UI transformations.
"""

import logging
import platform
import subprocess
import os
import sys
import threading
import time
from typing import Dict, Any, Optional, List
import re

logger = logging.getLogger("AIOS.UIVoiceCommands")

try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    logger.warning("Eel not available - UI voice commands will run in limited mode")
    EEL_AVAILABLE = False


class ScheduledShutdownManager:
    """Manages scheduled shutdown/restart with countdown and cancellation."""

    def __init__(self):
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._scheduled_command: Optional[str] = None
        self._fire_at: Optional[float] = None

    def schedule(self, command: str, delay_seconds: int) -> Dict[str, Any]:
        with self._lock:
            if self._timer is not None:
                return {"success": False, "message": "A shutdown is already scheduled. Cancel it first."}
            self._scheduled_command = command
            self._fire_at = time.time() + delay_seconds
            self._timer = threading.Timer(delay_seconds, self._execute)
            self._timer.daemon = True
            self._timer.start()
            logger.info("Scheduled %s in %ds", command, delay_seconds)
            return {
                "success": True,
                "message": f"{command.title()} scheduled in {delay_seconds} seconds",
                "speak": f"I'll {command} in {self._format_duration(delay_seconds)}",
                "delay_seconds": delay_seconds,
            }

    def cancel(self) -> Dict[str, Any]:
        with self._lock:
            if self._timer is None:
                return {"success": False, "message": "No scheduled shutdown to cancel"}
            self._timer.cancel()
            cmd = self._scheduled_command
            self._timer = None
            self._scheduled_command = None
            self._fire_at = None
            logger.info("Cancelled scheduled %s", cmd)
            return {"success": True, "message": f"Scheduled {cmd} cancelled", "speak": "Scheduled action cancelled"}

    def status(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._timer is None:
                return None
            remaining = max(0, int(self._fire_at - time.time()))
            return {"command": self._scheduled_command, "remaining_seconds": remaining}

    def _execute(self):
        with self._lock:
            cmd = self._scheduled_command
            self._timer = None
            self._scheduled_command = None
            self._fire_at = None
        logger.info("Executing scheduled %s", cmd)
        try:
            if EEL_AVAILABLE:
                eel.execute_system_command(cmd, {})
            else:
                _run_system_power_command(cmd)
        except Exception as e:
            logger.error("Scheduled %s failed: %s", cmd, e)

    @staticmethod
    def _format_duration(seconds: int) -> str:
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"


def _run_system_power_command(command: str) -> Dict[str, Any]:
    """Execute a platform-appropriate power management command."""
    system = platform.system()
    try:
        if command == 'shutdown':
            if system == 'Darwin':
                subprocess.Popen(['osascript', '-e', 'tell app "System Events" to shut down'])
            elif system == 'Windows':
                subprocess.Popen(['shutdown', '/s', '/t', '0'])
            else:
                subprocess.Popen(['shutdown', '-h', 'now'])
            return {'success': True, 'message': 'Shutting down', 'speak': 'Shutting down now'}

        elif command == 'restart':
            if system == 'Darwin':
                subprocess.Popen(['osascript', '-e', 'tell app "System Events" to restart'])
            elif system == 'Windows':
                subprocess.Popen(['shutdown', '/r', '/t', '0'])
            else:
                subprocess.Popen(['shutdown', '-r', 'now'])
            return {'success': True, 'message': 'Restarting', 'speak': 'Restarting now'}

        elif command == 'sleep':
            if system == 'Darwin':
                subprocess.Popen(['pmset', 'sleepnow'])
            elif system == 'Windows':
                subprocess.Popen(['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'])
            else:
                subprocess.Popen(['systemctl', 'suspend'])
            return {'success': True, 'message': 'Sleeping', 'speak': 'Putting computer to sleep'}

        elif command == 'hibernate':
            if system == 'Darwin':
                # pmset hibernatemode 25 = hibernate to disk
                subprocess.Popen(['pmset', '-a', 'hibernatemode', '25'])
                subprocess.Popen(['pmset', 'sleepnow'])
            elif system == 'Windows':
                subprocess.Popen(['rundll32.exe', 'powrprof.dll,SetSuspendState', '1,1,0'])
            else:
                subprocess.Popen(['systemctl', 'hibernate'])
            return {'success': True, 'message': 'Hibernating', 'speak': 'Hibernating computer'}

        elif command == 'lock_screen':
            if system == 'Darwin':
                subprocess.Popen([
                    '/System/Library/CoreServices/Menu Extras/User.menu/'
                    'Contents/Resources/CGSession', '-suspend'
                ])
            elif system == 'Windows':
                subprocess.Popen(['rundll32.exe', 'user32.dll,LockWorkStation'])
            else:
                subprocess.Popen(['loginctl', 'lock-session'])
            return {'success': True, 'message': 'Screen locked', 'speak': 'Locking screen'}

        elif command == 'logout':
            if system == 'Darwin':
                subprocess.Popen(['osascript', '-e', 'tell app "System Events" to log out'])
            elif system == 'Windows':
                subprocess.Popen(['shutdown', '/l'])
            else:
                subprocess.Popen(['loginctl', 'terminate-user', os.getenv('USER', '')])
            return {'success': True, 'message': 'Logging out', 'speak': 'Logging out'}

        return {'success': False, 'message': f'Unknown power command: {command}'}
    except Exception as e:
        logger.error("Power command %s failed: %s", command, e)
        return {'success': False, 'message': str(e), 'speak': f'Could not {command}'}


_scheduled_shutdown = ScheduledShutdownManager()


def _graceful_app_shutdown():
    """Stop minikernel + eel and exit cleanly."""
    try:
        from kernel.onboarding_gui import minikernel_shutdown_kernel
        minikernel_shutdown_kernel()
    except Exception:
        pass
    try:
        if EEL_AVAILABLE:
            eel.quit_app()
    except Exception:
        pass
    threading.Timer(1.0, lambda: os._exit(0)).start()


def _graceful_app_restart():
    """Stop minikernel + eel then re-exec the process."""
    try:
        from kernel.onboarding_gui import minikernel_shutdown_kernel
        minikernel_shutdown_kernel()
    except Exception:
        pass
    try:
        if EEL_AVAILABLE:
            eel.quit_app()
    except Exception:
        pass

    def _do_restart():
        time.sleep(1.0)
        python = sys.executable
        os.execl(python, python, *sys.argv)

    threading.Thread(target=_do_restart, daemon=True).start()


class UIVoiceCommandHandler:
    """Handles voice commands for UI mode transformations"""
    
    def __init__(self):
        self.command_patterns = self._build_command_patterns()
        self.current_mode = 'avatar'
        logger.info("UI Voice Command Handler initialized")
    
    def _build_command_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build regex patterns for voice command matching"""
        # NOTE: Order matters! More specific patterns should come first.
        # System control patterns are checked early to prevent conflicts.
        return {
            'system_control': [
                # Scheduled actions — must come before plain shutdown/restart
                {'pattern': r'(shutdown|shut\s+down|turn\s+off|restart|reboot)\s+(?:in|after)\s+(\d+)\s+(second|minute|hour)s?', 'action': 'scheduled_shutdown'},
                {'pattern': r'cancel\s+(?:scheduled\s+)?(?:shutdown|restart|reboot)', 'action': 'cancel_scheduled_shutdown'},
                # Exit/shutdown patterns - must come first to avoid AI assistant conflicts
                {'pattern': r'^(exit|quit|close)$', 'action': 'shutdown'},
                {'pattern': r'^(exit|quit|close)\s+(port\s*aios|aios|system|application|app|program)$', 'action': 'shutdown'},
                {'pattern': r'(shut\s+down|shutdown|turn\s+off)\s+(the\s+)?(computer|system|port\s*aios|aios|application|app|program)', 'action': 'shutdown'},
                {'pattern': r'restart\s+(the\s+)?(computer|system|port\s*aios|aios)', 'action': 'restart'},
                {'pattern': r'hibernate', 'action': 'hibernate'},
                {'pattern': r'(put\s+computer\s+to\s+)?sleep', 'action': 'system_sleep'},
                {'pattern': r'lock\s+(my\s+)?(screen|computer)', 'action': 'lock_screen'},
                {'pattern': r'(log\s+out|logout|sign\s+out)', 'action': 'logout'},
                {'pattern': r'empty\s+trash', 'action': 'empty_trash'},
                {'pattern': r'show\s+battery', 'action': 'show_battery'},
                {'pattern': r'battery\s+status', 'action': 'show_battery'},
                {'pattern': r'(show\s+)?(disk\s+space|storage)', 'action': 'show_disk_space'},
                {'pattern': r'(show\s+)?(memory|ram)\s+usage', 'action': 'show_memory'},
                {'pattern': r'(show\s+)?(cpu|processor)\s+usage', 'action': 'show_cpu'},
            ],
            'browser': [
                {'pattern': r'open\s+(the\s+)?(web\s+)?browser', 'action': 'open_browser'},
                {'pattern': r'launch\s+(the\s+)?browser', 'action': 'open_browser'},
                {'pattern': r'browse\s+(to\s+)?(.+)', 'action': 'browse_to', 'extract': 'url'},
                {'pattern': r'go\s+to\s+(.+\.(com|org|net|io|edu|gov))', 'action': 'browse_to', 'extract': 'url'},
                {'pattern': r'search\s+(for\s+)?(.+)', 'action': 'search_web', 'extract': 'query'},
            ],
            'desktop': [
                {'pattern': r'show\s+(my\s+)?(files|desktop|folders?)', 'action': 'show_desktop'},
                {'pattern': r'open\s+file\s+(browser|explorer|manager)', 'action': 'show_desktop'},
                {'pattern': r'browse\s+(my\s+)?(files|documents)', 'action': 'show_desktop'},
                {'pattern': r'show\s+me\s+(the\s+)?file\s+system', 'action': 'show_desktop'},
            ],
            'document': [
                {'pattern': r'open\s+(file|document)\s+(.+)', 'action': 'open_document', 'extract': 'filename'},
                {'pattern': r'show\s+(me\s+)?(file|document)\s+(.+)', 'action': 'open_document', 'extract': 'filename'},
                {'pattern': r'read\s+(file|document)\s+(.+)', 'action': 'open_document', 'extract': 'filename'},
                {'pattern': r'view\s+(.+\.(txt|md|pdf|doc))', 'action': 'open_document', 'extract': 'filename'},
            ],
            'media': [
                {'pattern': r'show\s+(me\s+)?(image|picture|photo)\s+(.+)', 'action': 'show_image', 'extract': 'filename'},
                {'pattern': r'play\s+(video|movie)\s+(.+)', 'action': 'play_video', 'extract': 'filename'},
                {'pattern': r'open\s+(image|picture|photo)\s+(.+)', 'action': 'show_image', 'extract': 'filename'},
                {'pattern': r'display\s+(image|picture)\s+(.+)', 'action': 'show_image', 'extract': 'filename'},
            ],
            'terminal': [
                {'pattern': r'open\s+(the\s+)?terminal', 'action': 'open_terminal'},
                {'pattern': r'show\s+(me\s+)?(the\s+)?command\s+line', 'action': 'open_terminal'},
                {'pattern': r'open\s+(command\s+)?(prompt|console)', 'action': 'open_terminal'},
                {'pattern': r'terminal\s+mode', 'action': 'open_terminal'},
            ],
            'applications': [
                {'pattern': r'open\s+(application|app|program)\s+(.+)', 'action': 'open_application', 'extract': 'app_name'},
                {'pattern': r'launch\s+(.+)', 'action': 'open_application', 'extract': 'app_name'},
                {'pattern': r'start\s+(.+)', 'action': 'open_application', 'extract': 'app_name'},
                {'pattern': r'run\s+(.+)', 'action': 'open_application', 'extract': 'app_name'},
            ],
            'downloads': [
                {'pattern': r'download\s+(software|package|program)\s+(.+)', 'action': 'download_software', 'extract': 'package'},
                {'pattern': r'install\s+(software|package|program)?\s*(.+)', 'action': 'download_software', 'extract': 'package'},
                {'pattern': r'get\s+(software|package)\s+(.+)', 'action': 'download_software', 'extract': 'package'},
            ],
            'system': [
                {'pattern': r'(show\s+)?(system\s+)?status', 'action': 'system_status'},
                {'pattern': r'check\s+(system\s+)?status', 'action': 'system_status'},
                {'pattern': r'how\s+(is\s+)?(the\s+)?system(\s+doing)?', 'action': 'system_status'},
                {'pattern': r'system\s+(info|information)', 'action': 'system_status'},
            ],
            'updates': [
                {'pattern': r'update\s+(the\s+)?system', 'action': 'update_system'},
                {'pattern': r'install\s+system\s+updates?', 'action': 'update_system'},
                {'pattern': r'(seek|search|look)\s+(out|for)\s+updates?', 'action': 'check_updates'},
                {'pattern': r'check\s+for\s+updates?', 'action': 'check_updates'},
                {'pattern': r'^updates?$', 'action': 'check_updates'},
            ],
            'notifications': [
                {'pattern': r'show\s+(me\s+)?(my\s+)?notifications?', 'action': 'show_notifications'},
                {'pattern': r'(check|view)\s+notifications?', 'action': 'show_notifications'},
                {'pattern': r'any\s+notifications?', 'action': 'show_notifications'},
                {'pattern': r'what\'?s\s+new', 'action': 'show_notifications'},
                {'pattern': r'clear\s+notifications?', 'action': 'clear_notifications'},
            ],
            'navigation': [
                {'pattern': r'(go\s+)?back\s+to\s+(the\s+)?avatar', 'action': 'back_to_avatar'},
                {'pattern': r'(close|exit)\s+(this|current)(\s+view)?', 'action': 'close_view'},
                {'pattern': r'return\s+to\s+(normal|avatar)\s+mode', 'action': 'back_to_avatar'},
                {'pattern': r'show\s+(the\s+)?avatar', 'action': 'back_to_avatar'},
            ],
            'file_operations': [
                {'pattern': r'go\s+to\s+(folder|directory)\s+(.+)', 'action': 'navigate_folder', 'extract': 'folder'},
                {'pattern': r'navigate\s+to\s+(.+)', 'action': 'navigate_folder', 'extract': 'folder'},
                {'pattern': r'cd\s+(.+)', 'action': 'navigate_folder', 'extract': 'folder'},
                {'pattern': r'list\s+(files|directory|contents)', 'action': 'list_files'},
            ],
            'ai_assistance': [
                {'pattern': r'(hey\s+)?(aios|ai|assistant)', 'action': 'wake_ai'},
                {'pattern': r'help\s+(me\s+)?(with\s+)?(.+)', 'action': 'ai_help', 'extract': 'query'},
                {'pattern': r'what\s+(can\s+you|do\s+you)\s+(.+)', 'action': 'ai_help', 'extract': 'query'},
                {'pattern': r'explain\s+(.+)', 'action': 'ai_explain', 'extract': 'topic'},
                {'pattern': r'tell\s+me\s+about\s+(.+)', 'action': 'ai_explain', 'extract': 'topic'},
            ],
            'productivity': [
                {'pattern': r'take\s+(a\s+)?note\s+(.+)', 'action': 'create_note', 'extract': 'content'},
                {'pattern': r'create\s+(a\s+)?reminder\s+(.+)', 'action': 'create_reminder', 'extract': 'content'},
                {'pattern': r'remind\s+me\s+to\s+(.+)', 'action': 'create_reminder', 'extract': 'content'},
                {'pattern': r'set\s+(a\s+)?timer\s+for\s+(.+)', 'action': 'set_timer', 'extract': 'duration'},
                {'pattern': r'show\s+(my\s+)?todo\s+list', 'action': 'show_todos'},
                {'pattern': r'add\s+to\s+(my\s+)?todo\s+(.+)', 'action': 'add_todo', 'extract': 'task'},
            ],
            'quick_actions': [
                {'pattern': r'screenshot', 'action': 'take_screenshot'},
                {'pattern': r'take\s+(a\s+)?screenshot', 'action': 'take_screenshot'},
                {'pattern': r'screen\s+capture', 'action': 'take_screenshot'},
                {'pattern': r'(what\'?s\s+)?(the\s+)?time', 'action': 'show_time'},
                {'pattern': r'(what\'?s\s+)?(the\s+)?date', 'action': 'show_date'},
                {'pattern': r'(show\s+)?(system\s+)?volume', 'action': 'show_volume'},
                {'pattern': r'(increase|raise|turn\s+up)\s+(the\s+)?volume', 'action': 'volume_up'},
                {'pattern': r'(decrease|lower|turn\s+down)\s+(the\s+)?volume', 'action': 'volume_down'},
                {'pattern': r'mute', 'action': 'volume_mute'},
            ],
            'search': [
                {'pattern': r'find\s+(file|files)\s+(named\s+)?(.+)', 'action': 'search_files', 'extract': 'query'},
                {'pattern': r'search\s+(for\s+)?(file|files)\s+(.+)', 'action': 'search_files', 'extract': 'query'},
                {'pattern': r'where\s+is\s+(file\s+)?(.+)', 'action': 'search_files', 'extract': 'query'},
                {'pattern': r'locate\s+(.+)', 'action': 'search_files', 'extract': 'query'},
            ],
            'workspace': [
                {'pattern': r'create\s+(new\s+)?(file|document)\s+(.+)', 'action': 'create_file', 'extract': 'filename'},
                {'pattern': r'new\s+(file|document)\s+(.+)', 'action': 'create_file', 'extract': 'filename'},
                {'pattern': r'create\s+(new\s+)?folder\s+(.+)', 'action': 'create_folder', 'extract': 'foldername'},
                {'pattern': r'delete\s+(file|folder)\s+(.+)', 'action': 'delete_item', 'extract': 'item'},
                {'pattern': r'rename\s+(.+)\s+to\s+(.+)', 'action': 'rename_item', 'extract': 'names'},
            ],
            'fun': [
                {'pattern': r'tell\s+(me\s+)?(a\s+)?joke', 'action': 'tell_joke'},
                {'pattern': r'(flip\s+a\s+)?coin', 'action': 'flip_coin'},
                {'pattern': r'roll\s+(a\s+)?dice', 'action': 'roll_dice'},
                {'pattern': r'(give\s+me\s+)?(a\s+)?random\s+number', 'action': 'random_number'},
            ],
            'developer_tools': [
                {'pattern': r'git\s+status', 'action': 'git_status'},
                {'pattern': r'git\s+(commit|push|pull)', 'action': 'git_command', 'extract': 'command'},
                {'pattern': r'show\s+(git\s+)?log', 'action': 'git_log'},
                {'pattern': r'open\s+(in\s+)?(vs\s+code|vscode)', 'action': 'open_vscode'},
                {'pattern': r'open\s+(in\s+)?editor', 'action': 'open_editor'},
                {'pattern': r'run\s+tests', 'action': 'run_tests'},
                {'pattern': r'(show\s+)?console\s+log', 'action': 'show_console_log'},
                {'pattern': r'(show\s+)?error\s+log', 'action': 'show_error_log'},
                {'pattern': r'clear\s+logs', 'action': 'clear_logs'},
                {'pattern': r'start\s+server', 'action': 'start_server'},
                {'pattern': r'stop\s+server', 'action': 'stop_server'},
                {'pattern': r'docker\s+(ps|status)', 'action': 'docker_status'},
                {'pattern': r'docker\s+(start|stop|restart)\s+(.+)', 'action': 'docker_container', 'extract': 'container'},
            ],
            'network': [
                {'pattern': r'(show\s+)?(my\s+)?ip\s+address', 'action': 'show_ip'},
                {'pattern': r'(what\'?s\s+)?my\s+ip', 'action': 'show_ip'},
                {'pattern': r'(show\s+)?wifi\s+status', 'action': 'show_wifi'},
                {'pattern': r'(show\s+)?network\s+status', 'action': 'show_network'},
                {'pattern': r'ping\s+(.+)', 'action': 'ping_host', 'extract': 'host'},
                {'pattern': r'(test\s+)?internet\s+connection', 'action': 'test_internet'},
                {'pattern': r'(show\s+)?network\s+speed', 'action': 'show_network_speed'},
                {'pattern': r'connect\s+to\s+wifi\s+(.+)', 'action': 'connect_wifi', 'extract': 'network'},
                {'pattern': r'disconnect\s+(from\s+)?wifi', 'action': 'disconnect_wifi'},
                {'pattern': r'(enable|turn\s+on)\s+airplane\s+mode', 'action': 'airplane_mode_on'},
                {'pattern': r'(disable|turn\s+off)\s+airplane\s+mode', 'action': 'airplane_mode_off'},
            ],
            'media_control': [
                {'pattern': r'(play|pause)\s+music', 'action': 'media_play_pause'},
                {'pattern': r'(stop|pause)\s+(music|playback)', 'action': 'media_stop'},
                {'pattern': r'next\s+(song|track)', 'action': 'media_next'},
                {'pattern': r'previous\s+(song|track)', 'action': 'media_previous'},
                {'pattern': r'skip\s+(song|track)', 'action': 'media_next'},
                {'pattern': r'play\s+(.+)', 'action': 'media_play', 'extract': 'query'},
                {'pattern': r'shuffle\s+(on|off)', 'action': 'media_shuffle', 'extract': 'state'},
                {'pattern': r'repeat\s+(on|off)', 'action': 'media_repeat', 'extract': 'state'},
                {'pattern': r'(show\s+)?now\s+playing', 'action': 'media_now_playing'},
                {'pattern': r'what\'?s\s+playing', 'action': 'media_now_playing'},
            ],
            'window_management': [
                {'pattern': r'minimize\s+(window|all)', 'action': 'minimize_window'},
                {'pattern': r'maximize\s+window', 'action': 'maximize_window'},
                {'pattern': r'close\s+(window|tab)', 'action': 'close_window'},
                {'pattern': r'full\s+screen', 'action': 'toggle_fullscreen'},
                {'pattern': r'(exit\s+)?full\s+screen', 'action': 'exit_fullscreen'},
                {'pattern': r'split\s+screen', 'action': 'split_screen'},
                {'pattern': r'(show\s+)?desktop', 'action': 'show_desktop'},
                {'pattern': r'hide\s+(all\s+)?windows', 'action': 'hide_windows'},
                {'pattern': r'switch\s+(to\s+)?(.+)', 'action': 'switch_app', 'extract': 'app'},
            ],
            'calendar_time': [
                {'pattern': r'(what\'?s\s+)?(today\'?s\s+)?schedule', 'action': 'show_schedule'},
                {'pattern': r'(show\s+)?calendar', 'action': 'show_calendar'},
                {'pattern': r'add\s+event\s+(.+)', 'action': 'add_calendar_event', 'extract': 'event'},
                {'pattern': r'next\s+meeting', 'action': 'next_meeting'},
                {'pattern': r'set\s+alarm\s+for\s+(.+)', 'action': 'set_alarm', 'extract': 'time'},
                {'pattern': r'cancel\s+alarm', 'action': 'cancel_alarm'},
                {'pattern': r'(show\s+)?timezone', 'action': 'show_timezone'},
                {'pattern': r'convert\s+time\s+(.+)', 'action': 'convert_time', 'extract': 'query'},
            ],
            'clipboard': [
                {'pattern': r'copy\s+(.+)', 'action': 'copy_text', 'extract': 'text'},
                {'pattern': r'paste', 'action': 'paste_text'},
                {'pattern': r'(show\s+)?clipboard', 'action': 'show_clipboard'},
                {'pattern': r'(show\s+)?clipboard\s+history', 'action': 'show_clipboard_history'},
                {'pattern': r'clear\s+clipboard', 'action': 'clear_clipboard'},
            ],
            'accessibility': [
                {'pattern': r'(zoom\s+)?in', 'action': 'zoom_in'},
                {'pattern': r'(zoom\s+)?out', 'action': 'zoom_out'},
                {'pattern': r'reset\s+zoom', 'action': 'reset_zoom'},
                {'pattern': r'(increase|larger)\s+(text\s+)?size', 'action': 'increase_text_size'},
                {'pattern': r'(decrease|smaller)\s+(text\s+)?size', 'action': 'decrease_text_size'},
                {'pattern': r'(enable|turn\s+on)\s+dark\s+mode', 'action': 'dark_mode_on'},
                {'pattern': r'(disable|turn\s+off)\s+dark\s+mode', 'action': 'dark_mode_off'},
                {'pattern': r'(toggle\s+)?dark\s+mode', 'action': 'toggle_dark_mode'},
                {'pattern': r'(enable|turn\s+on)\s+voice\s+over', 'action': 'voiceover_on'},
                {'pattern': r'(disable|turn\s+off)\s+voice\s+over', 'action': 'voiceover_off'},
            ],
            'web_search': [
                {'pattern': r'(google\s+)?search\s+(for\s+)?(.+)', 'action': 'google_search', 'extract': 'query'},
                {'pattern': r'wikipedia\s+(.+)', 'action': 'wikipedia_search', 'extract': 'query'},
                {'pattern': r'youtube\s+(.+)', 'action': 'youtube_search', 'extract': 'query'},
                {'pattern': r'(show\s+)?weather', 'action': 'show_weather'},
                {'pattern': r'weather\s+(in\s+)?(.+)', 'action': 'show_weather', 'extract': 'location'},
                {'pattern': r'(show\s+)?news', 'action': 'show_news'},
                {'pattern': r'translate\s+(.+)', 'action': 'translate', 'extract': 'text'},
            ],
            'email': [
                {'pattern': r'(show\s+)?(my\s+)?email', 'action': 'show_email'},
                {'pattern': r'(check\s+)?inbox', 'action': 'check_inbox'},
                {'pattern': r'new\s+email\s+to\s+(.+)', 'action': 'new_email', 'extract': 'recipient'},
                {'pattern': r'send\s+email\s+to\s+(.+)', 'action': 'send_email', 'extract': 'recipient'},
                {'pattern': r'reply\s+(to\s+)?(email|message)', 'action': 'reply_email'},
                {'pattern': r'forward\s+(email|message)', 'action': 'forward_email'},
                {'pattern': r'mark\s+as\s+(read|unread)', 'action': 'mark_email', 'extract': 'status'},
                {'pattern': r'delete\s+email', 'action': 'delete_email'},
                {'pattern': r'search\s+email\s+(for\s+)?(.+)', 'action': 'search_email', 'extract': 'query'},
                {'pattern': r'unread\s+(emails|messages)', 'action': 'show_unread'},
            ],
            'smart_home': [
                {'pattern': r'turn\s+(on|off)\s+(the\s+)?lights?', 'action': 'control_lights', 'extract': 'state'},
                {'pattern': r'(dim|brighten)\s+(the\s+)?lights?', 'action': 'adjust_lights', 'extract': 'action'},
                {'pattern': r'set\s+lights?\s+to\s+(\d+)\s*%?', 'action': 'set_light_brightness', 'extract': 'brightness'},
                {'pattern': r'turn\s+(on|off)\s+(.+)', 'action': 'control_device', 'extract': 'device'},
                {'pattern': r'(set\s+)?thermostat\s+to\s+(\d+)', 'action': 'set_temperature', 'extract': 'temp'},
                {'pattern': r'(what\'?s\s+)?(the\s+)?temperature', 'action': 'show_temperature'},
                {'pattern': r'lock\s+(the\s+)?door', 'action': 'lock_door'},
                {'pattern': r'unlock\s+(the\s+)?door', 'action': 'unlock_door'},
                {'pattern': r'(show\s+)?security\s+cameras?', 'action': 'show_cameras'},
                {'pattern': r'arm\s+(the\s+)?alarm', 'action': 'arm_alarm'},
                {'pattern': r'disarm\s+(the\s+)?alarm', 'action': 'disarm_alarm'},
            ],
            'advanced_ai': [
                {'pattern': r'train\s+model\s+(.+)', 'action': 'train_model', 'extract': 'model'},
                {'pattern': r'run\s+model\s+(.+)', 'action': 'run_model', 'extract': 'model'},
                {'pattern': r'(show\s+)?model\s+status', 'action': 'show_model_status'},
                {'pattern': r'analyze\s+(.+)', 'action': 'ai_analyze', 'extract': 'data'},
                {'pattern': r'generate\s+(.+)', 'action': 'ai_generate', 'extract': 'prompt'},
                {'pattern': r'summarize\s+(.+)', 'action': 'ai_summarize', 'extract': 'content'},
                {'pattern': r'(show\s+)?ai\s+models', 'action': 'list_ai_models'},
                {'pattern': r'load\s+model\s+(.+)', 'action': 'load_ai_model', 'extract': 'model'},
                {'pattern': r'unload\s+model', 'action': 'unload_ai_model'},
            ],
            'automation': [
                {'pattern': r'create\s+(workflow|automation)\s+(.+)', 'action': 'create_automation', 'extract': 'workflow'},
                {'pattern': r'run\s+(workflow|automation)\s+(.+)', 'action': 'run_automation', 'extract': 'workflow'},
                {'pattern': r'(show\s+)?automations?', 'action': 'list_automations'},
                {'pattern': r'schedule\s+(.+)', 'action': 'schedule_task', 'extract': 'task'},
                {'pattern': r'(show\s+)?scheduled\s+tasks', 'action': 'show_scheduled'},
                {'pattern': r'cancel\s+(task|automation)\s+(.+)', 'action': 'cancel_automation', 'extract': 'task'},
            ],
            'browserbase': [
                # Open Browserbase cloud browser
                {'pattern': r'open\s+browserbase', 'action': 'open_browserbase'},
                {'pattern': r'(use|launch|start)\s+(browserbase|cloud\s+browser)', 'action': 'open_browserbase'},
                {'pattern': r'cloud\s+browser', 'action': 'open_browserbase'},
                # Automate a task via Browserbase
                {'pattern': r'automate\s+(.+)', 'action': 'browserbase_automate', 'extract': 'task'},
                {'pattern': r'(run|execute)\s+automation\s+(.+)', 'action': 'browserbase_automate', 'extract': 'task'},
                # Navigate to a URL in Browserbase
                {'pattern': r'browse\s+(.+)\s+with\s+(browserbase|cloud|automation)', 'action': 'browserbase_navigate', 'extract': 'url'},
                {'pattern': r'(go\s+to|visit|open)\s+(.+)\s+in\s+(browserbase|cloud\s+browser)', 'action': 'browserbase_navigate', 'extract': 'url'},
                # Configure
                {'pattern': r'configure\s+browserbase', 'action': 'open_browserbase'},
                # Close
                {'pattern': r'close\s+(browserbase|cloud\s+browser)', 'action': 'close_browserbase'},
            ],
            'database': [
                {'pattern': r'(show\s+)?databases?', 'action': 'list_databases'},
                {'pattern': r'connect\s+to\s+database\s+(.+)', 'action': 'connect_database', 'extract': 'db'},
                {'pattern': r'query\s+(.+)', 'action': 'database_query', 'extract': 'query'},
                {'pattern': r'(show\s+)?tables', 'action': 'show_tables'},
                {'pattern': r'describe\s+(table\s+)?(.+)', 'action': 'describe_table', 'extract': 'table'},
                {'pattern': r'export\s+data\s+(.+)', 'action': 'export_data', 'extract': 'query'},
            ],
            'cloud_services': [
                {'pattern': r'(show\s+)?aws\s+instances', 'action': 'aws_list_instances'},
                {'pattern': r'(show\s+)?azure\s+resources', 'action': 'azure_list_resources'},
                {'pattern': r'(show\s+)?gcp\s+instances', 'action': 'gcp_list_instances'},
                {'pattern': r'deploy\s+to\s+(aws|azure|gcp)', 'action': 'cloud_deploy', 'extract': 'provider'},
                {'pattern': r'(show\s+)?cloud\s+costs?', 'action': 'show_cloud_costs'},
                {'pattern': r's3\s+upload\s+(.+)', 'action': 's3_upload', 'extract': 'file'},
                {'pattern': r's3\s+download\s+(.+)', 'action': 's3_download', 'extract': 'file'},
            ],
            'code_generation': [
                {'pattern': r'generate\s+function\s+(.+)', 'action': 'generate_function', 'extract': 'spec'},
                {'pattern': r'generate\s+class\s+(.+)', 'action': 'generate_class', 'extract': 'spec'},
                {'pattern': r'refactor\s+(.+)', 'action': 'refactor_code', 'extract': 'target'},
                {'pattern': r'optimize\s+(.+)', 'action': 'optimize_code', 'extract': 'target'},
                {'pattern': r'add\s+tests?\s+for\s+(.+)', 'action': 'generate_tests', 'extract': 'target'},
                {'pattern': r'document\s+(.+)', 'action': 'generate_docs', 'extract': 'target'},
                {'pattern': r'fix\s+bug\s+in\s+(.+)', 'action': 'fix_bug', 'extract': 'location'},
            ],
            'social_media': [
                {'pattern': r'post\s+to\s+(twitter|x)\s+(.+)', 'action': 'post_twitter', 'extract': 'content'},
                {'pattern': r'post\s+to\s+linkedin\s+(.+)', 'action': 'post_linkedin', 'extract': 'content'},
                {'pattern': r'post\s+to\s+facebook\s+(.+)', 'action': 'post_facebook', 'extract': 'content'},
                {'pattern': r'(show\s+)?social\s+mentions', 'action': 'show_mentions'},
                {'pattern': r'(show\s+)?notifications', 'action': 'show_social_notifications'},
            ],
            'music': [
                {'pattern': r'play\s+music\s+(.+)', 'action': 'play_music', 'extract': 'query'},
                {'pattern': r'play\s+video\s+(.+)', 'action': 'play_video', 'extract': 'query'},
                {'pattern': r'(show\s+)?music\s+library', 'action': 'show_music_library'},
                {'pattern': r'(show\s+)?video\s+library', 'action': 'show_video_library'},
            ]
        }
    
    def process_command(self, text: str) -> Optional[Dict[str, Any]]:
        # Update AI Guardian if available
        try:
            from kernel.ai_guardian_bridge import get_guardian_bridge
            bridge = get_guardian_bridge()
            bridge.set_activity('thinking')
            bridge.set_emotion('thinking')
        except Exception:
            pass
        """
        Process voice command and return UI action
        Returns: {'action': str, 'mode': str, 'data': dict} or None
        """
        text = text.lower().strip()
        logger.info(f"Processing UI voice command: {text}")
        
        # Try to match against all patterns
        for category, patterns in self.command_patterns.items():
            for pattern_info in patterns:
                match = re.search(pattern_info['pattern'], text, re.IGNORECASE)
                if match:
                    logger.info(f"Matched pattern: {pattern_info['pattern']} in category: {category}")
                    return self._execute_action(pattern_info['action'], match, text)
        
        return None
    
    def _execute_action(self, action: str, match, original_text: str) -> Dict[str, Any]:
        """Execute the matched voice command action"""
        
        if action == 'show_desktop':
            return {
                'action': 'switch_mode',
                'mode': 'desktop',
                'data': {'path': None}
            }
        
        elif action == 'open_document':
            # Extract filename from match groups
            filename = match.group(2) if match.lastindex >= 2 else match.group(1)
            return {
                'action': 'switch_mode',
                'mode': 'document',
                'data': {'filename': filename.strip()}
            }
        
        elif action == 'show_image':
            filename = match.group(3) if match.lastindex >= 3 else match.group(2)
            return {
                'action': 'switch_mode',
                'mode': 'media',
                'data': {'type': 'image', 'filename': filename.strip()}
            }
        
        elif action == 'play_video':
            filename = match.group(2)
            return {
                'action': 'switch_mode',
                'mode': 'media',
                'data': {'type': 'video', 'filename': filename.strip()}
            }
        
        elif action == 'open_terminal':
            return {
                'action': 'switch_mode',
                'mode': 'terminal',
                'data': {'message': 'Terminal initialized via voice command'}
            }
        
        elif action == 'open_browser':
            return {
                'action': 'switch_mode',
                'mode': 'browser',
                'data': {'url': 'about:blank'}
            }
        
        elif action == 'browse_to':
            url = match.group(2) if match.lastindex >= 2 else match.group(1)
            return {
                'action': 'switch_mode',
                'mode': 'browser',
                'data': {'url': url.strip()}
            }
        
        elif action == 'search_web':
            query = match.group(2) if match.lastindex >= 2 else match.group(1)
            return {
                'action': 'switch_mode',
                'mode': 'browser',
                'data': {'url': f'https://www.google.com/search?q={query.strip().replace(" ", "+")}'}
            }
        
        elif action == 'open_browserbase':
            return {
                'action': 'switch_mode',
                'mode': 'browserbase',
                'data': {}
            }

        elif action == 'browserbase_automate':
            task = match.group(2) if match.lastindex >= 2 else match.group(1)
            return {
                'action': 'switch_mode',
                'mode': 'browserbase',
                'data': {'task': task.strip()}
            }

        elif action == 'browserbase_navigate':
            # group 2 is the URL portion for most patterns
            url = match.group(2) if match.lastindex >= 2 else match.group(1)
            return {
                'action': 'switch_mode',
                'mode': 'browserbase',
                'data': {'url': url.strip()}
            }

        elif action == 'close_browserbase':
            return {
                'action': 'switch_mode',
                'mode': 'avatar',
                'data': {}
            }

        elif action == 'back_to_avatar':
            return {
                'action': 'switch_mode',
                'mode': 'avatar',
                'data': {}
            }
        
        elif action == 'close_view':
            return {
                'action': 'switch_mode',
                'mode': 'avatar',
                'data': {}
            }
        
        elif action == 'navigate_folder':
            folder = match.group(2) if match.lastindex >= 2 else match.group(1)
            return {
                'action': 'switch_mode',
                'mode': 'desktop',
                'data': {'path': folder.strip()}
            }
        
        elif action == 'list_files':
            return {
                'action': 'switch_mode',
                'mode': 'desktop',
                'data': {'path': None}
            }
        
        elif action == 'open_application':
            app_name = match.group(2) if match.lastindex >= 2 else match.group(1)
            return {
                'action': 'execute_command',
                'command': 'open_application',
                'data': {'app_name': app_name.strip()}
            }
        
        elif action == 'download_software':
            # Extract package name from match groups
            package = None
            if match.lastindex >= 2:
                package = match.group(2)
            elif match.lastindex >= 1:
                package = match.group(1)
            
            if package and package.strip():
                return {
                    'action': 'execute_command',
                    'command': 'download_software',
                    'data': {'package': package.strip()}
                }
            else:
                return {
                    'action': 'request_input',
                    'message': 'What software would you like to download?'
                }
        
        elif action == 'system_status':
            return {
                'action': 'execute_command',
                'command': 'system_status',
                'data': {}
            }
        
        elif action == 'check_updates':
            return {
                'action': 'execute_command',
                'command': 'check_updates',
                'data': {}
            }
        
        elif action == 'update_system':
            return {
                'action': 'execute_command',
                'command': 'update_system',
                'data': {}
            }
        
        elif action == 'show_notifications':
            return {
                'action': 'switch_mode',
                'mode': 'notifications',
                'data': {}
            }
        
        elif action == 'clear_notifications':
            return {
                'action': 'execute_command',
                'command': 'clear_notifications',
                'data': {}
            }
        
        elif action == 'ai_help':
            query = match.group(3) if match.lastindex >= 3 else match.group(2) if match.lastindex >= 2 else match.group(1)
            return {
                'action': 'execute_command',
                'command': 'ai_help',
                'data': {'query': query.strip()}
            }
        
        elif action == 'ai_search':
            query = match.group(2) if match.lastindex >= 2 else match.group(1)
            return {
                'action': 'execute_command',
                'command': 'ai_search',
                'data': {'query': query.strip()}
            }
        
        elif action == 'ai_conversation':
            query = match.group(2) if match.lastindex >= 2 else match.group(1)
            return {
                'action': 'execute_command',
                'command': 'ai_conversation',
                'data': {'query': query.strip()}
            }
        
        elif action == 'ai_settings':
            return {
                'action': 'execute_command',
                'command': 'ai_settings',
                'data': {}
            }
        
        # Scheduled shutdown
        elif action == 'scheduled_shutdown':
            cmd_word = match.group(1).lower().replace(' ', '_')
            command = 'restart' if 'restart' in cmd_word or 'reboot' in cmd_word else 'shutdown'
            amount = int(match.group(2))
            unit = match.group(3).lower()
            multiplier = {'second': 1, 'minute': 60, 'hour': 3600}.get(unit, 60)
            delay = amount * multiplier
            return {
                'action': 'execute_command',
                'command': 'scheduled_shutdown',
                'data': {'command': command, 'delay_seconds': delay}
            }

        elif action == 'cancel_scheduled_shutdown':
            return {
                'action': 'execute_command',
                'command': 'cancel_scheduled_shutdown',
                'data': {}
            }

        # System control actions - shutdown, restart, exit
        elif action == 'shutdown':
            return {
                'action': 'confirm_and_execute',
                'command': 'shutdown',
                'confirmation_message': 'Are you sure you want to shutdown PortAIOS?',
                'data': {}
            }

        elif action == 'restart':
            return {
                'action': 'confirm_and_execute',
                'command': 'restart',
                'confirmation_message': 'Are you sure you want to restart PortAIOS?',
                'data': {}
            }

        elif action == 'hibernate':
            return {
                'action': 'confirm_and_execute',
                'command': 'hibernate',
                'confirmation_message': 'Hibernate the computer?',
                'data': {}
            }

        elif action == 'system_sleep':
            return {
                'action': 'execute_command',
                'command': 'sleep',
                'data': {}
            }

        elif action == 'lock_screen':
            return {
                'action': 'execute_command',
                'command': 'lock_screen',
                'data': {}
            }

        elif action == 'logout':
            return {
                'action': 'confirm_and_execute',
                'command': 'logout',
                'confirmation_message': 'Are you sure you want to log out?',
                'data': {}
            }
        
        return {
            'action': 'unknown', 
            'mode': self.current_mode, 
            'data': {}
            }
    
        


# Eel integration
if EEL_AVAILABLE:
    ui_voice_handler = UIVoiceCommandHandler()
    
    @eel.expose
    def execute_system_command(command: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute system commands triggered by voice"""
        try:
            # ── Scheduled shutdown ──────────────────────────────────────────
            if command == 'scheduled_shutdown':
                sub_cmd = data.get('command', 'shutdown')
                delay = int(data.get('delay_seconds', 60))
                return _scheduled_shutdown.schedule(sub_cmd, delay)

            elif command == 'cancel_scheduled_shutdown':
                return _scheduled_shutdown.cancel()

            elif command == 'scheduled_shutdown_status':
                status = _scheduled_shutdown.status()
                if status:
                    remaining = status['remaining_seconds']
                    return {
                        'success': True,
                        'message': f"{status['command'].title()} in {remaining}s",
                        'speak': f"{status['command']} in {remaining} seconds",
                        'data': status,
                    }
                return {'success': True, 'message': 'No shutdown scheduled', 'speak': 'No shutdown is scheduled'}

            # ── Application-level shutdown (quit eel/PortAIOS) ──────────────
            elif command == 'shutdown':
                logger.info("Shutdown command received via voice")
                _graceful_app_shutdown()
                return {'success': True, 'message': 'System shutting down', 'speak': 'Shutting down PortAIOS'}

            elif command == 'restart':
                logger.info("Restart command received via voice")
                _graceful_app_restart()
                return {'success': True, 'message': 'System restarting', 'speak': 'Restarting PortAIOS'}

            # ── Power management ─────────────────────────────────────────────
            elif command in ('sleep', 'hibernate', 'lock_screen', 'logout'):
                return _run_system_power_command(command)

            # Handle special update commands
            elif command == 'check_updates':
                from kernel.system_updater import check_for_updates
                result_data = check_for_updates()
                
                message = result_data.get('message', 'Update check completed')
                if result_data.get('available'):
                    speak = f"{result_data.get('count', 0)} updates available"
                else:
                    speak = "System is up to date"
                
                return {
                    'success': True,
                    'message': message,
                    'speak': speak,
                    'data': result_data
                }
            
            elif command == 'update_system':
                from kernel.system_updater import install_system_updates
                result_data = install_system_updates(auto_approve=False)
                
                return {
                    'success': result_data.get('success', False),
                    'message': result_data.get('message', 'Update operation completed'),
                    'speak': result_data.get('message', 'Please approve updates manually for security'),
                    'data': result_data
                }
            
            # Handle standard commands from agent_commands
            from kernel.agent_commands import COMMANDS
            
            if command in COMMANDS:
                result = COMMANDS[command](data)
                return {
                    'success': bool(result),
                    'message': result.message if hasattr(result, 'message') else str(result),
                    'speak': result.speak if hasattr(result, 'speak') else None
                }
            else:
                return {
                    'success': False,
                    'message': f'Unknown command: {command}',
                    'speak': f'Command {command} not found'
                }
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            return {
                'success': False,
                'message': str(e),
                'speak': f'Error: {str(e)}'
            }
    
    @eel.expose
    def get_system_notifications() -> List[Dict[str, Any]]:
        """Get system notifications"""
        # This is a placeholder - can be extended with real notification system
        notifications = []
        
        try:
            # Check for system updates
            import platform
            system = platform.system()
            
            notifications.append({
                'id': 'system_info',
                'type': 'info',
                'title': 'System Information',
                'message': f'Running on {system}',
                'timestamp': 'now'
            })
            
            # Check if updates are available
            try:
                import subprocess
                if system == "Linux":
                    # Check apt updates
                    result = subprocess.run(['apt', 'list', '--upgradable'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and 'upgradable' in result.stdout:
                        count = result.stdout.count('\n') - 1
                        if count > 0:
                            notifications.append({
                                'id': 'updates_available',
                                'type': 'warning',
                                'title': 'Updates Available',
                                'message': f'{count} package updates available',
                                'timestamp': 'now'
                            })
            except:
                pass
            
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
        
        return notifications
    
    @eel.expose
    def clear_system_notifications() -> Dict[str, Any]:
        """Clear system notifications"""
        return {
            'success': True,
            'message': 'Notifications cleared',
            'speak': 'All notifications cleared'
        }
    
    @eel.expose
    def process_ui_voice_command(text: str) -> Optional[Dict[str, Any]]:
        """Process voice command for UI transformations"""
        return ui_voice_handler.process_command(text)
    
    @eel.expose
    def get_ui_command_examples() -> Dict[str, List[str]]:
        """Get example voice commands for each UI mode"""
        return {
            'desktop': [
                "Show my files",
                "Open file browser",
                "Browse my documents"
            ],
            'document': [
                "Open document readme.txt",
                "Show me file notes.md"
            ],
            'media': [
                "Show me image photo.jpg",
                "Play video demo.mp4"
            ],
            'terminal': [
                "Open terminal",
                "Show command line"
            ],
            'browser': [
                "Open browser",
                "Open web browser",
                "Search for AIOS"
            ],
            'applications': [
                "Open application firefox",
                "Launch vscode",
                "Start calculator"
            ],
            'downloads': [
                "Download software python",
                "Install package git"
            ],
            'system': [
                "System status",
                "Check status",
                "System information"
            ],
            'updates': [
                "Check for updates",
                "Update system",
                "Seek out updates"
            ],
            'notifications': [
                "Show notifications",
                "What's new",
                "Clear notifications"
            ],
            'navigation': [
                "Back to avatar",
                "Close this view"
            ],
            'browserbase': [
                "Open browserbase",
                "Launch cloud browser",
                "Automate google search for AI news",
                "Browse github.com with browserbase",
                "Cloud browser"
            ]
        }


def setup_ui_voice_commands():
    """Initialize UI voice command handler"""
    if EEL_AVAILABLE:
        logger.info("UI Voice Commands initialized and exposed to Eel")
        return ui_voice_handler
    else:
        logger.warning("Eel not available - UI Voice Commands running in standalone mode")
        return UIVoiceCommandHandler()


# Export
__all__ = ['UIVoiceCommandHandler', 'setup_ui_voice_commands']
