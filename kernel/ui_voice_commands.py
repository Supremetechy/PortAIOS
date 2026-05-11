"""
UI Voice Commands Integration
Extends AIOS voice commands to support dynamic UI transformations.
"""

import logging
from typing import Dict, Any, Optional, List
import re

logger = logging.getLogger("AIOS.UIVoiceCommands")

try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    logger.warning("Eel not available - UI voice commands will run in limited mode")
    EEL_AVAILABLE = False


class UIVoiceCommandHandler:
    """Handles voice commands for UI mode transformations"""
    
    def __init__(self):
        self.command_patterns = self._build_command_patterns()
        self.current_mode = 'avatar'
        logger.info("UI Voice Command Handler initialized")
    
    def _build_command_patterns(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build regex patterns for voice command matching"""
        return {
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
            'system_control': [
                {'pattern': r'(put\s+computer\s+to\s+)?sleep', 'action': 'system_sleep'},
                {'pattern': r'lock\s+(my\s+)?(screen|computer)', 'action': 'lock_screen'},
                {'pattern': r'(log\s+out|logout|sign\s+out)', 'action': 'logout'},
                {'pattern': r'(shut\s+down|shutdown|turn\s+off)\s+(computer|system)', 'action': 'shutdown'},
                {'pattern': r'restart\s+(computer|system)', 'action': 'restart'},
                {'pattern': r'empty\s+trash', 'action': 'empty_trash'},
                {'pattern': r'show\s+battery', 'action': 'show_battery'},
                {'pattern': r'battery\s+status', 'action': 'show_battery'},
                {'pattern': r'(show\s+)?(disk\s+space|storage)', 'action': 'show_disk_space'},
                {'pattern': r'(show\s+)?(memory|ram)\s+usage', 'action': 'show_memory'},
                {'pattern': r'(show\s+)?(cpu|processor)\s+usage', 'action': 'show_cpu'},
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
            # Handle special update commands
            if command == 'check_updates':
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
