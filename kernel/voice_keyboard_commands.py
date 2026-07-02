#!/usr/bin/env python3
"""
Voice-controlled keyboard, annotation, and dictation system for AIOS
Supports full keyboard control via voice commands with Microsoft speech grammar compatibility
"""

import logging
import re
import subprocess
import webbrowser
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

logger = logging.getLogger("AIOS.VoiceKeyboard")

try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    EEL_AVAILABLE = False
    logger.warning("Eel not available - voice keyboard commands will run in standalone mode")


class CommandMode(Enum):
    """Voice command modes"""
    KEYBOARD = "keyboard"
    ANNOTATION = "annotation"
    DICTATION = "dictation"


class VoiceKeyboardCommands:
    """
    Handles voice-controlled keyboard input, annotation, and dictation
    Follows Microsoft speech keyboard command patterns for consistency
    """
    
    def __init__(self):
        self.current_mode = CommandMode.KEYBOARD
        self.dictation_buffer = ""
        self.annotation_active = False
        self.annotation_context = {}
        
        # Build comprehensive key mappings
        self.key_map = self._build_key_mappings()
        self.modifier_map = self._build_modifier_mappings()
        self.phonetic_map = self._build_phonetic_alphabet()
        
        # Command patterns for parsing
        self.patterns = self._build_command_patterns()
        
        logger.info("VoiceKeyboardCommands initialized")
    
    def _build_key_mappings(self) -> Dict[str, str]:
        """Build complete keyboard key name mappings"""
        keys = {
            # Function row
            "escape": "Escape", "esc": "Escape",
            "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4",
            "f5": "F5", "f6": "F6", "f7": "F7", "f8": "F8",
            "f9": "F9", "f10": "F10", "f11": "F11", "f12": "F12",
            "print screen": "PrintScreen", "scroll lock": "ScrollLock", "pause": "Pause",
            
            # Number row
            "backtick": "`", "grave": "`", "tilde": "~",
            "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
            "six": "6", "seven": "7", "eight": "8", "nine": "9", "zero": "0",
            "hyphen": "-", "minus": "-", "dash": "-",
            "equal sign": "=", "equals": "=",
            "backspace": "Backspace",
            
            # Tab row
            "tab": "Tab",
            "q": "q", "w": "w", "e": "e", "r": "r", "t": "t",
            "y": "y", "u": "u", "i": "i", "o": "o", "p": "p",
            "open bracket": "[", "left bracket": "[",
            "close bracket": "]", "right bracket": "]",
            "backslash": "\\",
            
            # Home row
            "caps lock": "CapsLock",
            "a": "a", "b": "b", "c": "c", "d": "d", "f": "f", "g": "g",
            "h": "h", "j": "j", "k": "k", "l": "l",
            "semicolon": ";", "colon": ":",
            "apostrophe": "'", "quote": "'", "single quote": "'",
            "enter": "Enter", "return": "Enter",
            
            # Bottom row
            "shift": "Shift",
            "z": "z", "x": "x", "v": "v", "n": "n", "m": "m",
            "comma": ",", "period": ".", "dot": ".",
            "forward slash": "/", "slash": "/",
            
            # Control row
            "control": "Control", "ctrl": "Control",
            "windows": "Meta", "command": "Meta", "super": "Meta",
            "alt": "Alt", "option": "Alt",
            "space": " ", "spacebar": " ",
            "menu": "ContextMenu",
            
            # Navigation cluster
            "insert": "Insert", "delete": "Delete", "del": "Delete",
            "home": "Home", "end": "End",
            "page up": "PageUp", "pgup": "PageUp",
            "page down": "PageDown", "pgdown": "PageDown",
            
            # Arrow keys
            "up": "ArrowUp", "up arrow": "ArrowUp",
            "down": "ArrowDown", "down arrow": "ArrowDown",
            "left": "ArrowLeft", "left arrow": "ArrowLeft",
            "right": "ArrowRight", "right arrow": "ArrowRight",
            
            # Numpad
            "num lock": "NumLock",
            "numpad divide": "NumpadDivide", "numpad slash": "NumpadDivide",
            "numpad multiply": "NumpadMultiply", "numpad star": "NumpadMultiply",
            "numpad minus": "NumpadSubtract",
            "numpad plus": "NumpadAdd",
            "numpad enter": "NumpadEnter",
            "numpad decimal": "NumpadDecimal", "numpad dot": "NumpadDecimal",
            "numpad zero": "Numpad0", "numpad one": "Numpad1", "numpad two": "Numpad2",
            "numpad three": "Numpad3", "numpad four": "Numpad4", "numpad five": "Numpad5",
            "numpad six": "Numpad6", "numpad seven": "Numpad7", "numpad eight": "Numpad8",
            "numpad nine": "Numpad9",
        }
        return keys
    
    def _build_modifier_mappings(self) -> Dict[str, str]:
        """Build modifier key mappings"""
        return {
            "shift": "Shift",
            "control": "Control", "ctrl": "Control",
            "alt": "Alt", "option": "Alt",
            "windows": "Meta", "command": "Meta", "super": "Meta", "win": "Meta",
        }
    
    def _build_phonetic_alphabet(self) -> Dict[str, str]:
        """Build NATO/ICAO phonetic alphabet for letter disambiguation"""
        return {
            "alpha": "a", "bravo": "b", "charlie": "c", "delta": "d",
            "echo": "e", "foxtrot": "f", "golf": "g", "hotel": "h",
            "india": "i", "juliet": "j", "kilo": "k", "lima": "l",
            "mike": "m", "november": "n", "oscar": "o", "papa": "p",
            "quebec": "q", "romeo": "r", "sierra": "s", "tango": "t",
            "uniform": "u", "victor": "v", "whiskey": "w", "x-ray": "x",
            "yankee": "y", "zulu": "z"
        }
    
    def _build_command_patterns(self) -> List[Dict[str, Any]]:
        """Build regex patterns for command recognition"""
        return [
            # Mode switching
            {
                "pattern": r"^(?:enter|start|begin|enable)\s+(keyboard|annotation|dictation)\s+mode$",
                "action": "switch_mode",
                "priority": 10
            },
            {
                "pattern": r"^(?:exit|stop|end|disable)\s+(keyboard|annotation|dictation)\s+mode$",
                "action": "exit_mode",
                "priority": 10
            },
            
            # Keyboard commands - single key
            {
                "pattern": r"^press\s+(.+?)(?:\s+(\d+)\s+times?)?$",
                "action": "press_key",
                "priority": 5
            },
            {
                "pattern": r"^type\s+(.+)$",
                "action": "type_text",
                "priority": 5
            },
            {
                "pattern": r"^hold\s+(.+)$",
                "action": "hold_key",
                "priority": 5
            },
            {
                "pattern": r"^release\s+(.+)$",
                "action": "release_key",
                "priority": 5
            },
            
            # Annotation commands
            {
                "pattern": r"^annotate\s+(.+)$",
                "action": "annotate",
                "priority": 7
            },
            {
                "pattern": r"^(?:add|create)\s+(?:annotation|note)\s+(.+)$",
                "action": "add_annotation",
                "priority": 7
            },
            {
                "pattern": r"^(?:show|list|view)\s+annotations?$",
                "action": "show_annotations",
                "priority": 7
            },
            {
                "pattern": r"^(?:clear|delete)\s+annotation(?:s)?(?:\s+(.+))?$",
                "action": "clear_annotations",
                "priority": 7
            },
            {
                "pattern": r"^highlight\s+(.+)$",
                "action": "highlight_text",
                "priority": 7
            },
            
            # Dictation commands
            {
                "pattern": r"^(?:start|begin)\s+dictation$",
                "action": "start_dictation",
                "priority": 8
            },
            {
                "pattern": r"^(?:stop|end)\s+dictation$",
                "action": "stop_dictation",
                "priority": 8
            },
            {
                "pattern": r"^(?:clear|erase)\s+(?:dictation|buffer)$",
                "action": "clear_dictation",
                "priority": 8
            },
            {
                "pattern": r"^(?:insert|paste)\s+dictation$",
                "action": "insert_dictation",
                "priority": 8
            },
            
            # System / navigation commands
            {
                "pattern": r"^(?:show|open)\s+files?(?:\s+(?:browser|manager|explorer))?$",
                "action": "show_files",
                "priority": 9
            },
            {
                "pattern": r"^open\s+(?:(?:a\s+)?(?:web\s+)?browser|chrome|firefox|safari)$",
                "action": "open_browser",
                "priority": 9
            },
            {
                "pattern": r"^(?:help|show\s+(?:help|commands?)|what\s+can\s+(?:i|you)\s+say)$",
                "action": "help",
                "priority": 9
            },

            # Dictation punctuation
            {
                "pattern": r"^(?:new\s+)?(?:line|paragraph)$",
                "action": "dictation_newline",
                "priority": 6
            },
            {
                "pattern": r"^(period|comma|question mark|exclamation point|colon|semicolon)$",
                "action": "dictation_punctuation",
                "priority": 6
            },
        ]
    
    def process_command(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Process voice command and return action
        
        Args:
            text: Voice command text
            
        Returns:
            Dict with action details or None if no match
        """
        text = text.lower().strip()
        
        # Sort patterns by priority
        sorted_patterns = sorted(self.patterns, key=lambda x: x["priority"], reverse=True)
        
        for pattern_def in sorted_patterns:
            match = re.match(pattern_def["pattern"], text, re.IGNORECASE)
            if match:
                action = pattern_def["action"]
                handler = getattr(self, f"_handle_{action}", None)
                
                if handler:
                    return handler(text, match)
                else:
                    logger.warning(f"No handler for action: {action}")
        
        # If in dictation mode, treat unmatched text as dictation input
        if self.current_mode == CommandMode.DICTATION:
            return self._handle_dictation_input(text)
        
        return None
    
    # ========== Mode Switching Handlers ==========
    
    def _handle_switch_mode(self, text: str, match) -> Dict[str, Any]:
        """Switch to a different command mode"""
        mode_name = match.group(1)
        
        try:
            new_mode = CommandMode(mode_name)
            old_mode = self.current_mode
            self.current_mode = new_mode
            
            logger.info(f"Switched from {old_mode.value} to {new_mode.value} mode")
            
            return {
                "action": "mode_switch",
                "old_mode": old_mode.value,
                "new_mode": new_mode.value,
                "success": True,
                "message": f"Switched to {new_mode.value} mode"
            }
        except ValueError:
            return {
                "action": "mode_switch",
                "success": False,
                "error": f"Unknown mode: {mode_name}"
            }
    
    def _handle_exit_mode(self, text: str, match) -> Dict[str, Any]:
        """Exit current mode and return to keyboard mode"""
        old_mode = self.current_mode
        self.current_mode = CommandMode.KEYBOARD
        
        return {
            "action": "mode_exit",
            "old_mode": old_mode.value,
            "new_mode": "keyboard",
            "success": True,
            "message": f"Exited {old_mode.value} mode"
        }
    
    # ========== Keyboard Command Handlers ==========
    
    def _handle_press_key(self, text: str, match) -> Dict[str, Any]:
        """Handle 'press [key]' or 'press [modifier] plus [key]' commands"""
        key_phrase = match.group(1).strip()
        repeat_count = int(match.group(2)) if match.group(2) else 1
        
        # Parse the key phrase for modifiers and key
        parsed = self._parse_key_combination(key_phrase)
        
        if not parsed:
            return {
                "action": "press_key",
                "success": False,
                "error": f"Could not parse key: {key_phrase}"
            }
        
        return {
            "action": "press_key",
            "success": True,
            "key": parsed["key"],
            "modifiers": parsed["modifiers"],
            "repeat": repeat_count,
            "original": text
        }
    
    def _parse_key_combination(self, phrase: str) -> Optional[Dict[str, Any]]:
        """
        Parse key combination like 'control plus c' or 'shift plus alt plus delete'
        
        Returns:
            Dict with 'key' and 'modifiers' list, or None if invalid
        """
        parts = [p.strip() for p in phrase.split("plus")]
        
        modifiers = []
        key = None
        
        for part in parts:
            # Check if it's a modifier
            if part in self.modifier_map:
                modifiers.append(self.modifier_map[part])
            # Check if it's a phonetic letter
            elif part in self.phonetic_map:
                key = self.phonetic_map[part]
            # Check if it's a regular key
            elif part in self.key_map:
                key = self.key_map[part]
            # Single letter/number
            elif len(part) == 1 and (part.isalnum() or part in "!@#$%^&*()_+-=[]{}|;:',.<>?/`~"):
                key = part
            else:
                # Last part should be the main key
                key = part
        
        if key is None:
            return None
        
        return {
            "key": key,
            "modifiers": modifiers
        }
    
    def _handle_type_text(self, text: str, match) -> Dict[str, Any]:
        """Handle 'type [text]' command"""
        text_to_type = match.group(1).strip()
        
        return {
            "action": "type_text",
            "success": True,
            "text": text_to_type
        }
    
    def _handle_hold_key(self, text: str, match) -> Dict[str, Any]:
        """Handle 'hold [key]' command"""
        key_name = match.group(1).strip()
        
        if key_name in self.modifier_map:
            key = self.modifier_map[key_name]
        elif key_name in self.key_map:
            key = self.key_map[key_name]
        else:
            key = key_name
        
        return {
            "action": "hold_key",
            "success": True,
            "key": key
        }
    
    def _handle_release_key(self, text: str, match) -> Dict[str, Any]:
        """Handle 'release [key]' command"""
        key_name = match.group(1).strip()
        
        if key_name in self.modifier_map:
            key = self.modifier_map[key_name]
        elif key_name in self.key_map:
            key = self.key_map[key_name]
        else:
            key = key_name
        
        return {
            "action": "release_key",
            "success": True,
            "key": key
        }
    
    # ========== Annotation Handlers ==========
    
    def _handle_annotate(self, text: str, match) -> Dict[str, Any]:
        """Handle 'annotate [text]' command"""
        annotation_text = match.group(1).strip()
        
        return {
            "action": "annotate",
            "success": True,
            "text": annotation_text,
            "timestamp": self._get_timestamp()
        }
    
    def _handle_add_annotation(self, text: str, match) -> Dict[str, Any]:
        """Handle 'add annotation [text]' command"""
        annotation_text = match.group(1).strip()
        
        return {
            "action": "add_annotation",
            "success": True,
            "text": annotation_text,
            "timestamp": self._get_timestamp()
        }
    
    def _handle_show_annotations(self, text: str, match) -> Dict[str, Any]:
        """Handle 'show annotations' command"""
        return {
            "action": "show_annotations",
            "success": True
        }
    
    def _handle_clear_annotations(self, text: str, match) -> Dict[str, Any]:
        """Handle 'clear annotations' command"""
        target = match.group(1) if match.lastindex >= 1 else None
        
        return {
            "action": "clear_annotations",
            "success": True,
            "target": target
        }
    
    def _handle_highlight_text(self, text: str, match) -> Dict[str, Any]:
        """Handle 'highlight [text]' command"""
        text_to_highlight = match.group(1).strip()
        
        return {
            "action": "highlight_text",
            "success": True,
            "text": text_to_highlight
        }
    
    # ========== Dictation Handlers ==========
    
    def _handle_start_dictation(self, text: str, match) -> Dict[str, Any]:
        """Handle 'start dictation' command"""
        self.dictation_buffer = ""
        
        return {
            "action": "start_dictation",
            "success": True,
            "message": "Dictation mode started"
        }
    
    def _handle_stop_dictation(self, text: str, match) -> Dict[str, Any]:
        """Handle 'stop dictation' command"""
        buffer_content = self.dictation_buffer
        
        return {
            "action": "stop_dictation",
            "success": True,
            "buffer": buffer_content,
            "message": f"Dictation stopped. {len(buffer_content)} characters captured."
        }
    
    def _handle_clear_dictation(self, text: str, match) -> Dict[str, Any]:
        """Handle 'clear dictation' command"""
        self.dictation_buffer = ""
        
        return {
            "action": "clear_dictation",
            "success": True,
            "message": "Dictation buffer cleared"
        }
    
    def _handle_insert_dictation(self, text: str, match) -> Dict[str, Any]:
        """Handle 'insert dictation' command"""
        buffer_content = self.dictation_buffer
        self.dictation_buffer = ""  # Clear after insert
        
        return {
            "action": "insert_dictation",
            "success": True,
            "text": buffer_content
        }
    
    def _handle_dictation_input(self, text: str) -> Dict[str, Any]:
        """Handle free-form dictation input"""
        self.dictation_buffer += text + " "
        
        return {
            "action": "dictation_input",
            "success": True,
            "text": text,
            "buffer_length": len(self.dictation_buffer)
        }
    
    def _handle_dictation_newline(self, text: str, match) -> Dict[str, Any]:
        """Handle newline in dictation"""
        if "paragraph" in text:
            self.dictation_buffer += "\n\n"
        else:
            self.dictation_buffer += "\n"
        
        return {
            "action": "dictation_newline",
            "success": True,
            "type": "paragraph" if "paragraph" in text else "line"
        }
    
    def _handle_dictation_punctuation(self, text: str, match) -> Dict[str, Any]:
        """Handle punctuation in dictation"""
        punctuation_map = {
            "period": ".",
            "comma": ",",
            "question mark": "?",
            "exclamation point": "!",
            "colon": ":",
            "semicolon": ";"
        }
        
        punct = match.group(1)
        symbol = punctuation_map.get(punct, punct)
        
        # Remove trailing space before punctuation
        self.dictation_buffer = self.dictation_buffer.rstrip() + symbol + " "
        
        return {
            "action": "dictation_punctuation",
            "success": True,
            "punctuation": symbol
        }
    
    def _handle_show_files(self, text: str, match) -> Dict[str, Any]:
        """Open the system file manager"""
        import sys
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", "."])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", "."])
            else:
                subprocess.Popen(["xdg-open", "."])
            return {"action": "show_files", "success": True}
        except Exception as e:
            return {"action": "show_files", "success": False, "error": str(e)}

    def _handle_open_browser(self, text: str, match) -> Dict[str, Any]:
        """Open the default web browser"""
        try:
            webbrowser.open("about:blank")
            return {"action": "open_browser", "success": True}
        except Exception as e:
            return {"action": "open_browser", "success": False, "error": str(e)}

    def _handle_help(self, text: str, match) -> Dict[str, Any]:
        """Return available commands for current mode"""
        commands = self.get_available_commands()
        return {"action": "help", "success": True, "commands": commands, "mode": self.current_mode.value}

    # ========== Utility Methods ==========

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_current_mode(self) -> str:
        """Get current command mode"""
        return self.current_mode.value
    
    def get_available_commands(self, mode: Optional[str] = None) -> List[str]:
        """Get list of available commands for a mode"""
        target_mode = mode if mode else self.current_mode.value
        
        commands = {
            "keyboard": [
                "press [key]",
                "press [modifier] plus [key]",
                "press [key] [number] times",
                "type [text]",
                "hold [modifier]",
                "release [modifier]",
                "Examples: press control plus c, press shift plus a, press enter"
            ],
            "annotation": [
                "annotate [text]",
                "add annotation [text]",
                "show annotations",
                "clear annotations",
                "highlight [text]",
                "Examples: annotate important section, highlight key points"
            ],
            "dictation": [
                "start dictation",
                "stop dictation",
                "clear dictation",
                "insert dictation",
                "new line / new paragraph",
                "period, comma, question mark, exclamation point",
                "Examples: Just speak naturally and AIOS will transcribe"
            ]
        }
        
        return commands.get(target_mode, [])


# ========== Eel Integration ==========

_keyboard_commands = None

def setup_voice_keyboard_for_eel(eel_module):
    """Setup Eel-exposed functions for voice keyboard commands"""
    global _keyboard_commands
    _keyboard_commands = VoiceKeyboardCommands()
    
    @eel_module.expose
    def process_keyboard_voice_command(text: str) -> Optional[Dict[str, Any]]:
        """Process voice keyboard command from frontend"""
        return _keyboard_commands.process_command(text)
    
    @eel_module.expose
    def get_keyboard_command_mode() -> str:
        """Get current keyboard command mode"""
        return _keyboard_commands.get_current_mode()
    
    @eel_module.expose
    def get_keyboard_available_commands(mode: Optional[str] = None) -> List[str]:
        """Get available commands for current or specified mode"""
        return _keyboard_commands.get_available_commands(mode)
    
    @eel_module.expose
    def set_keyboard_command_mode(mode: str) -> Dict[str, Any]:
        """Set keyboard command mode"""
        try:
            new_mode = CommandMode(mode)
            old_mode = _keyboard_commands.current_mode
            _keyboard_commands.current_mode = new_mode
            
            return {
                "success": True,
                "old_mode": old_mode.value,
                "new_mode": new_mode.value
            }
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid mode: {mode}"
            }
    
    logger.info("Voice keyboard commands registered with Eel")


if __name__ == "__main__":
    # Test the command processor
    kb = VoiceKeyboardCommands()
    
    test_commands = [
        "press control plus c",
        "press shift plus a",
        "press enter",
        "press f5 3 times",
        "type hello world",
        "annotate this is important",
        "start dictation",
        "period",
        "new line",
        "stop dictation",
    ]
    
    print("Testing Voice Keyboard Commands:\n")
    for cmd in test_commands:
        result = kb.process_command(cmd)
        print(f"Command: {cmd}")
        print(f"Result: {result}\n")
