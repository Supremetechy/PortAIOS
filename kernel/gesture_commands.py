#!/usr/bin/env python3
"""
PortAIOS Gesture Command Mapping
Maps gestures to system actions and integrates with voice commands
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import time

from kernel.gesture_controller import GestureType, GestureEvent, get_gesture_controller

logger = logging.getLogger("AIOS.GestureCommands")

# Try to import Eel
try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    EEL_AVAILABLE = False
    logger.warning("Eel not available - gesture commands will run in limited mode")


class ActionType(Enum):
    """Types of actions that can be triggered"""
    # File operations
    FILE_OPEN = "file_open"
    FILE_CLOSE = "file_close"
    FILE_DELETE = "file_delete"
    FILE_COPY = "file_copy"
    FILE_MOVE = "file_move"
    FILE_SELECT = "file_select"
    
    # Window management
    WINDOW_MINIMIZE = "window_minimize"
    WINDOW_MAXIMIZE = "window_maximize"
    WINDOW_CLOSE = "window_close"
    WINDOW_SWITCH = "window_switch"
    WINDOW_MOVE = "window_move"
    WINDOW_RESIZE = "window_resize"
    
    # Navigation
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"
    SCROLL_LEFT = "scroll_left"
    SCROLL_RIGHT = "scroll_right"
    PAGE_BACK = "page_back"
    PAGE_FORWARD = "page_forward"
    GO_HOME = "go_home"
    
    # UI Control
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG_START = "drag_start"
    DRAG_END = "drag_end"
    SELECT_ALL = "select_all"
    COPY = "copy"
    PASTE = "paste"
    UNDO = "undo"
    REDO = "redo"
    
    # Media control
    PLAY_PAUSE = "play_pause"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    MUTE = "mute"
    NEXT_TRACK = "next_track"
    PREV_TRACK = "prev_track"
    
    # System control
    LOCK_SCREEN = "lock_screen"
    SCREENSHOT = "screenshot"
    OPEN_TERMINAL = "open_terminal"
    OPEN_BROWSER = "open_browser"
    SHOW_DESKTOP = "show_desktop"
    
    # Voice integration
    START_VOICE = "start_voice"
    STOP_VOICE = "stop_voice"
    
    # Confirmation
    CONFIRM = "confirm"
    CANCEL = "cancel"
    
    # Custom
    CUSTOM = "custom"


@dataclass
class GestureCommand:
    """Maps a gesture to an action"""
    gesture_type: GestureType
    action_type: ActionType
    confidence_threshold: float = 0.7
    cooldown_seconds: float = 0.5
    requires_confirmation: bool = False
    description: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class GestureCommandMapper:
    """
    Maps gestures to system actions
    Manages gesture-to-command relationships with context awareness
    """
    
    def __init__(self):
        self.commands: Dict[GestureType, List[GestureCommand]] = {}
        self.last_trigger_time: Dict[str, float] = {}
        self.pending_confirmation: Optional[GestureCommand] = None
        
        # Context state
        self.current_mode = "desktop"  # desktop, browser, file_manager, media, etc.
        self.dragging = False
        self.selected_object = None
        
        # Register default gesture mappings
        self._register_default_commands()
        
        # Setup gesture controller callbacks
        self._setup_gesture_callbacks()
    
    def _register_default_commands(self):
        """Register default gesture-to-command mappings"""
        
        # Confirmation gestures
        self.register_command(GestureCommand(
            gesture_type=GestureType.THUMBS_UP,
            action_type=ActionType.CONFIRM,
            description="Confirm action"
        ))
        
        self.register_command(GestureCommand(
            gesture_type=GestureType.THUMBS_DOWN,
            action_type=ActionType.CANCEL,
            description="Cancel action"
        ))
        
        # Navigation gestures
        self.register_command(GestureCommand(
            gesture_type=GestureType.SWIPE_UP,
            action_type=ActionType.SCROLL_UP,
            description="Scroll up"
        ))
        
        self.register_command(GestureCommand(
            gesture_type=GestureType.SWIPE_DOWN,
            action_type=ActionType.SCROLL_DOWN,
            description="Scroll down"
        ))
        
        self.register_command(GestureCommand(
            gesture_type=GestureType.SWIPE_LEFT,
            action_type=ActionType.PAGE_BACK,
            description="Go back"
        ))
        
        self.register_command(GestureCommand(
            gesture_type=GestureType.SWIPE_RIGHT,
            action_type=ActionType.PAGE_FORWARD,
            description="Go forward"
        ))
        
        # Click gestures
        self.register_command(GestureCommand(
            gesture_type=GestureType.POINTING,
            action_type=ActionType.CLICK,
            description="Click/Select",
            cooldown_seconds=0.3
        ))
        
        self.register_command(GestureCommand(
            gesture_type=GestureType.PEACE_SIGN,
            action_type=ActionType.DOUBLE_CLICK,
            description="Double click"
        ))
        
        # Drag and drop
        self.register_command(GestureCommand(
            gesture_type=GestureType.PINCH,
            action_type=ActionType.DRAG_START,
            description="Start dragging"
        ))
        
        self.register_command(GestureCommand(
            gesture_type=GestureType.OPEN_PALM,
            action_type=ActionType.DRAG_END,
            description="Release drag"
        ))
        
        # Window management
        self.register_command(GestureCommand(
            gesture_type=GestureType.FIST,
            action_type=ActionType.WINDOW_CLOSE,
            description="Close window",
            requires_confirmation=True
        ))
        
        self.register_command(GestureCommand(
            gesture_type=GestureType.WAVE,
            action_type=ActionType.WINDOW_SWITCH,
            description="Switch window"
        ))
        
        # Media control
        self.register_command(GestureCommand(
            gesture_type=GestureType.OK_SIGN,
            action_type=ActionType.PLAY_PAUSE,
            description="Play/Pause"
        ))
        
        # Volume control (head gestures)
        self.register_command(GestureCommand(
            gesture_type=GestureType.HEAD_NOD,
            action_type=ActionType.CONFIRM,
            description="Confirm (head nod)"
        ))
        
        self.register_command(GestureCommand(
            gesture_type=GestureType.HEAD_SHAKE,
            action_type=ActionType.CANCEL,
            description="Cancel (head shake)"
        ))
        
        # Eye gaze navigation
        self.register_command(GestureCommand(
            gesture_type=GestureType.LOOK_UP,
            action_type=ActionType.SCROLL_UP,
            description="Scroll up (eye gaze)",
            confidence_threshold=0.8
        ))
        
        self.register_command(GestureCommand(
            gesture_type=GestureType.LOOK_DOWN,
            action_type=ActionType.SCROLL_DOWN,
            description="Scroll down (eye gaze)",
            confidence_threshold=0.8
        ))
        
        # System shortcuts
        self.register_command(GestureCommand(
            gesture_type=GestureType.SMILE,
            action_type=ActionType.SCREENSHOT,
            description="Take screenshot"
        ))
        
        logger.info(f"Registered {len(self.commands)} default gesture commands")
    
    def register_command(self, command: GestureCommand):
        """Register a gesture command"""
        if command.gesture_type not in self.commands:
            self.commands[command.gesture_type] = []
        self.commands[command.gesture_type].append(command)
    
    def unregister_command(self, gesture_type: GestureType, action_type: ActionType):
        """Unregister a specific gesture command"""
        if gesture_type in self.commands:
            self.commands[gesture_type] = [
                cmd for cmd in self.commands[gesture_type]
                if cmd.action_type != action_type
            ]
    
    def _setup_gesture_callbacks(self):
        """Setup callbacks with gesture controller"""
        controller = get_gesture_controller()
        
        # Register callback for all gesture types
        for gesture_type in GestureType:
            if gesture_type not in [GestureType.NONE, GestureType.UNKNOWN]:
                controller.register_gesture_callback(
                    gesture_type,
                    lambda event, gt=gesture_type: self._handle_gesture(event, gt)
                )
    
    def _handle_gesture(self, event: GestureEvent, gesture_type: GestureType):
        """Handle detected gesture"""
        # Get commands for this gesture
        commands = self.commands.get(gesture_type, [])
        if not commands:
            return
        
        # Filter by confidence threshold
        valid_commands = [
            cmd for cmd in commands
            if event.confidence >= cmd.confidence_threshold
        ]
        
        if not valid_commands:
            return
        
        # Context-based filtering (pick the most appropriate command)
        best_command = self._select_best_command(valid_commands, event)
        if not best_command:
            return
        
        # Check cooldown
        cooldown_key = f"{gesture_type.value}_{best_command.action_type.value}"
        now = time.time()
        last_time = self.last_trigger_time.get(cooldown_key, 0)
        
        if now - last_time < best_command.cooldown_seconds:
            return  # Still in cooldown
        
        # Handle confirmation requirement
        if best_command.requires_confirmation and not self.pending_confirmation:
            self.pending_confirmation = best_command
            self._request_confirmation(best_command)
            return
        
        # Execute command
        self._execute_command(best_command, event)
        
        # Update last trigger time
        self.last_trigger_time[cooldown_key] = now
    
    def _select_best_command(self, commands: List[GestureCommand], event: GestureEvent) -> Optional[GestureCommand]:
        """Select the most appropriate command based on context"""
        if len(commands) == 1:
            return commands[0]
        
        # Context-based selection
        # TODO: Implement sophisticated context awareness
        # For now, return highest confidence
        return max(commands, key=lambda cmd: cmd.confidence_threshold)
    
    def _request_confirmation(self, command: GestureCommand):
        """Request user confirmation for command"""
        logger.info(f"Requesting confirmation for: {command.description}")
        
        # Send to UI
        if EEL_AVAILABLE:
            try:
                eel.show_gesture_confirmation({
                    'action': command.action_type.value,
                    'description': command.description,
                    'timeout': 5  # 5 seconds to confirm
                })
            except:
                pass
        
        # Set timeout to clear pending confirmation
        import threading
        def clear_confirmation():
            time.sleep(5)
            if self.pending_confirmation == command:
                self.pending_confirmation = None
                logger.info("Confirmation timeout")
        
        threading.Thread(target=clear_confirmation, daemon=True).start()
    
    def _execute_command(self, command: GestureCommand, event: GestureEvent):
        """Execute the command action"""
        logger.info(f"Executing gesture command: {command.description} ({command.action_type.value})")
        
        action_type = command.action_type
        
        # Handle confirmation actions
        if action_type == ActionType.CONFIRM:
            if self.pending_confirmation:
                # Execute the pending command
                self._execute_command(self.pending_confirmation, event)
                self.pending_confirmation = None
            return
        
        elif action_type == ActionType.CANCEL:
            if self.pending_confirmation:
                logger.info("Action cancelled by user")
                self.pending_confirmation = None
            return
        
        # Execute based on action type
        result = None
        
        try:
            if action_type in [ActionType.SCROLL_UP, ActionType.SCROLL_DOWN, 
                              ActionType.SCROLL_LEFT, ActionType.SCROLL_RIGHT]:
                result = self._handle_scroll(action_type)
            
            elif action_type in [ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.RIGHT_CLICK]:
                result = self._handle_click(action_type, event.position)
            
            elif action_type in [ActionType.DRAG_START, ActionType.DRAG_END]:
                result = self._handle_drag(action_type, event.position)
            
            elif action_type in [ActionType.WINDOW_CLOSE, ActionType.WINDOW_MINIMIZE, 
                                ActionType.WINDOW_MAXIMIZE, ActionType.WINDOW_SWITCH]:
                result = self._handle_window(action_type)
            
            elif action_type in [ActionType.PLAY_PAUSE, ActionType.VOLUME_UP, 
                                ActionType.VOLUME_DOWN, ActionType.MUTE]:
                result = self._handle_media(action_type)
            
            elif action_type in [ActionType.PAGE_BACK, ActionType.PAGE_FORWARD]:
                result = self._handle_navigation(action_type)
            
            elif action_type == ActionType.SCREENSHOT:
                result = self._handle_screenshot()
            
            else:
                logger.warning(f"Unhandled action type: {action_type.value}")
            
            # Send result to UI
            if result and EEL_AVAILABLE:
                try:
                    eel.gesture_command_executed({
                        'action': action_type.value,
                        'gesture': event.gesture_type.value,
                        'result': result,
                        'timestamp': event.timestamp
                    })
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Error executing command: {e}")
    
    def _handle_scroll(self, action_type: ActionType) -> Dict[str, Any]:
        """Handle scroll actions"""
        if EEL_AVAILABLE:
            direction = action_type.value.replace('scroll_', '')
            try:
                eel.perform_scroll(direction)()
            except:
                pass
        
        return {"action": "scroll", "direction": action_type.value}
    
    def _handle_click(self, action_type: ActionType, position: Optional[tuple]) -> Dict[str, Any]:
        """Handle click actions"""
        click_type = action_type.value
        
        if position and EEL_AVAILABLE:
            try:
                eel.perform_click(click_type, position[0], position[1])()
            except:
                pass
        
        return {"action": "click", "type": click_type, "position": position}
    
    def _handle_drag(self, action_type: ActionType, position: Optional[tuple]) -> Dict[str, Any]:
        """Handle drag and drop"""
        if action_type == ActionType.DRAG_START:
            self.dragging = True
            self.selected_object = position
            logger.info(f"Started dragging from {position}")
        
        elif action_type == ActionType.DRAG_END:
            self.dragging = False
            logger.info(f"Dropped at {position}")
            
            if self.selected_object and position and EEL_AVAILABLE:
                try:
                    eel.perform_drag_drop(
                        self.selected_object[0], self.selected_object[1],
                        position[0], position[1]
                    )()
                except:
                    pass
            
            self.selected_object = None
        
        return {"action": "drag", "type": action_type.value, "position": position}
    
    def _handle_window(self, action_type: ActionType) -> Dict[str, Any]:
        """Handle window management"""
        if EEL_AVAILABLE:
            try:
                eel.perform_window_action(action_type.value)()
            except:
                pass
        
        return {"action": "window", "type": action_type.value}
    
    def _handle_media(self, action_type: ActionType) -> Dict[str, Any]:
        """Handle media control"""
        if EEL_AVAILABLE:
            try:
                eel.perform_media_action(action_type.value)()
            except:
                pass
        
        return {"action": "media", "type": action_type.value}
    
    def _handle_navigation(self, action_type: ActionType) -> Dict[str, Any]:
        """Handle navigation"""
        if EEL_AVAILABLE:
            try:
                eel.perform_navigation(action_type.value)()
            except:
                pass
        
        return {"action": "navigation", "type": action_type.value}
    
    def _handle_screenshot(self) -> Dict[str, Any]:
        """Take screenshot"""
        if EEL_AVAILABLE:
            try:
                result = eel.take_screenshot()()
                return {"action": "screenshot", "result": result}
            except:
                pass
        
        return {"action": "screenshot"}
    
    def set_mode(self, mode: str):
        """Set current interaction mode"""
        self.current_mode = mode
        logger.info(f"Gesture mode changed to: {mode}")
    
    def get_command_list(self) -> List[Dict[str, Any]]:
        """Get list of all registered commands"""
        command_list = []
        for gesture_type, commands in self.commands.items():
            for cmd in commands:
                command_list.append({
                    'gesture': gesture_type.value,
                    'action': cmd.action_type.value,
                    'description': cmd.description,
                    'confidence_threshold': cmd.confidence_threshold,
                    'requires_confirmation': cmd.requires_confirmation
                })
        return command_list


# Global instance
_gesture_command_mapper = None


def get_gesture_command_mapper() -> GestureCommandMapper:
    """Get or create global gesture command mapper"""
    global _gesture_command_mapper
    if _gesture_command_mapper is None:
        _gesture_command_mapper = GestureCommandMapper()
    return _gesture_command_mapper


# Eel integration
if EEL_AVAILABLE:
    def setup_gesture_commands_eel_api():
        """Setup Eel-exposed functions for gesture commands"""
        mapper = get_gesture_command_mapper()
        
        @eel.expose
        def get_gesture_commands() -> List[Dict[str, Any]]:
            """Get list of all gesture commands"""
            return mapper.get_command_list()
        
        @eel.expose
        def set_gesture_mode(mode: str) -> Dict[str, Any]:
            """Set gesture interaction mode"""
            mapper.set_mode(mode)
            return {"success": True, "mode": mode}
        
        @eel.expose
        def register_custom_gesture(gesture: str, action: str, description: str) -> Dict[str, Any]:
            """Register a custom gesture command"""
            try:
                gesture_type = GestureType[gesture.upper()]
                action_type = ActionType[action.upper()]
                
                command = GestureCommand(
                    gesture_type=gesture_type,
                    action_type=action_type,
                    description=description
                )
                
                mapper.register_command(command)
                return {"success": True, "message": f"Registered {gesture} → {action}"}
            
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        logger.info("Gesture commands Eel API initialized")
        return mapper


__all__ = [
    'GestureCommandMapper',
    'GestureCommand',
    'ActionType',
    'get_gesture_command_mapper',
    'setup_gesture_commands_eel_api'
]
