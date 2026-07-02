#!/usr/bin/env python3
"""
PortAIOS Multimodal Interaction Controller
Fuses voice, gesture, and traditional inputs into unified commands
Provides context-aware command routing and intelligent disambiguation
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading

logger = logging.getLogger("AIOS.Multimodal")

# Import subsystems
try:
    from kernel.gesture_controller import GestureType, GestureEvent, get_gesture_controller
    from kernel.gesture_commands import get_gesture_command_mapper, ActionType
    from kernel.ai_learning_engine import get_ai_learning_engine, UserAction
    GESTURE_AVAILABLE = True
except ImportError as e:
    GESTURE_AVAILABLE = False
    logger.warning(f"Gesture system not available: {e}")

try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    EEL_AVAILABLE = False


class InputMode(Enum):
    """Available input modalities"""
    VOICE = "voice"
    GESTURE = "gesture"
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    GAZE = "gaze"
    MULTIMODAL = "multimodal"  # Combined inputs


class CommandIntent(Enum):
    """High-level command intents"""
    NAVIGATE = "navigate"
    SELECT = "select"
    EXECUTE = "execute"
    MODIFY = "modify"
    CREATE = "create"
    DELETE = "delete"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    QUERY = "query"


@dataclass
class MultimodalCommand:
    """Represents a fused multimodal command"""
    intent: CommandIntent
    target: Optional[str] = None
    action: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Input sources
    voice_input: Optional[str] = None
    gesture_input: Optional[GestureEvent] = None
    gaze_position: Optional[Tuple[float, float]] = None
    
    # Metadata
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    needs_confirmation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'intent': self.intent.value,
            'target': self.target,
            'action': self.action,
            'parameters': self.parameters,
            'voice_input': self.voice_input,
            'gesture_type': self.gesture_input.gesture_type.value if self.gesture_input else None,
            'confidence': self.confidence,
            'timestamp': self.timestamp,
            'needs_confirmation': self.needs_confirmation
        }


class MultimodalController:
    """
    Main multimodal interaction controller
    Coordinates voice, gesture, and other inputs into unified commands
    """
    
    def __init__(self):
        self.enabled = False
        
        # Input buffers (for temporal fusion)
        self.voice_buffer = deque(maxlen=10)
        self.gesture_buffer = deque(maxlen=30)
        self.gaze_buffer = deque(maxlen=60)
        
        # Current state
        self.current_context = {
            'mode': 'desktop',
            'selected_object': None,
            'last_action': None,
            'active_app': None
        }
        
        # Pending commands (waiting for disambiguation)
        self.pending_command: Optional[MultimodalCommand] = None
        self.pending_timeout = 3.0  # seconds
        self.pending_timer = None
        
        # Command history
        self.command_history = deque(maxlen=100)
        
        # Subsystem references
        self.gesture_controller = None
        self.gesture_mapper = None
        self.ai_engine = None
        
        # Learning integration
        self.learning_enabled = True
        
        # Command callbacks
        self.command_callbacks = []
        
        # Initialize subsystems
        self._init_subsystems()
        
        logger.info("Multimodal Controller initialized")
    
    def _init_subsystems(self):
        """Initialize subsystems"""
        if GESTURE_AVAILABLE:
            try:
                self.gesture_controller = get_gesture_controller()
                self.gesture_mapper = get_gesture_command_mapper()
                self.ai_engine = get_ai_learning_engine()
                logger.info("Subsystems initialized")
            except Exception as e:
                logger.error(f"Failed to initialize subsystems: {e}")
        
        # Initialize AI Guardian bridge
        try:
            from kernel.ai_guardian_bridge import get_guardian_bridge
            self.guardian_bridge = get_guardian_bridge()
            logger.info("AI Guardian bridge initialized in multimodal controller")
        except Exception as e:
            logger.debug(f"Guardian bridge not available: {e}")
            self.guardian_bridge = None
    
    def enable(self):
        """Enable multimodal interaction"""
        self.enabled = True
        logger.info("Multimodal interaction enabled")
    
    def disable(self):
        """Disable multimodal interaction"""
        self.enabled = False
        logger.info("Multimodal interaction disabled")
    
    def process_voice_command(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Update guardian to listening state
        if self.guardian_bridge:
            try:
                self.guardian_bridge.set_activity('listening')
            except Exception:
                pass
        """
        Process voice command with potential gesture fusion
        
        Example:
        - "Open that file" + pointing gesture → Opens the pointed file
        - "Delete this" + gaze at item → Deletes the gazed item
        """
        if not self.enabled:
            return {'success': False, 'error': 'Multimodal controller disabled'}
        
        logger.info(f"Processing voice command: '{text}'")
        
        # Add to voice buffer
        self.voice_buffer.append({
            'text': text,
            'timestamp': time.time(),
            'context': context or {}
        })
        
        # Parse intent from voice
        intent, target, action = self._parse_voice_intent(text)
        
        # Check for gesture fusion opportunity
        recent_gesture = self._get_recent_gesture(timeout=2.0)
        gaze_position = self._get_recent_gaze(timeout=1.0)
        
        # Fuse inputs if available
        if recent_gesture or gaze_position:
            command = self._fuse_inputs(
                voice_text=text,
                voice_intent=intent,
                gesture=recent_gesture,
                gaze=gaze_position
            )
        else:
            # Voice-only command
            command = MultimodalCommand(
                intent=intent,
                target=target,
                action=action,
                voice_input=text
            )
        
        # Execute or request confirmation
        result = self._execute_command(command)
        
        # Learn from this interaction
        if self.learning_enabled and result.get('success'):
            self._record_interaction(command, InputMode.VOICE)
        
        return result
    
    def process_gesture(self, gesture: GestureEvent) -> Dict[str, Any]:
        """
        Process gesture input with potential voice fusion
        """
        if not self.enabled:
            return {'success': False, 'error': 'Multimodal controller disabled'}
        
        logger.info(f"Processing gesture: {gesture.gesture_type.value}")
        
        # Add to gesture buffer
        self.gesture_buffer.append(gesture)
        
        # Check for voice fusion opportunity
        recent_voice = self._get_recent_voice(timeout=2.0)
        
        if recent_voice:
            # Fuse with recent voice command
            intent, _, _ = self._parse_voice_intent(recent_voice['text'])
            
            command = self._fuse_inputs(
                voice_text=recent_voice['text'],
                voice_intent=intent,
                gesture=gesture,
                gaze=None
            )
        else:
            # Gesture-only command
            intent = self._gesture_to_intent(gesture)
            
            command = MultimodalCommand(
                intent=intent,
                gesture_input=gesture,
                confidence=gesture.confidence
            )
        
        # Execute
        result = self._execute_command(command)
        
        # Learn from this interaction
        if self.learning_enabled and result.get('success'):
            self._record_interaction(command, InputMode.GESTURE)
        
        return result
    
    def update_gaze_position(self, x: float, y: float):
        """Update eye gaze position"""
        self.gaze_buffer.append({
            'position': (x, y),
            'timestamp': time.time()
        })
    
    def _fuse_inputs(self, 
                     voice_text: Optional[str] = None,
                     voice_intent: Optional[CommandIntent] = None,
                     gesture: Optional[GestureEvent] = None,
                     gaze: Optional[Tuple[float, float]] = None) -> MultimodalCommand:
        """
        Fuse multiple input modalities into a single command
        
        Fusion rules:
        1. Voice provides intent and action
        2. Gesture provides spatial information or confirmation
        3. Gaze provides target selection
        """
        
        # Determine primary intent
        intent = voice_intent or (self._gesture_to_intent(gesture) if gesture else CommandIntent.QUERY)
        
        # Determine target
        target = None
        confidence = 1.0
        
        # Voice might specify target
        if voice_text:
            target = self._extract_target_from_voice(voice_text)
        
        # Gesture provides spatial target
        if gesture and gesture.position and not target:
            target = self._get_object_at_position(gesture.position)
            confidence *= gesture.confidence
        
        # Gaze provides target if nothing else specified
        if gaze and not target:
            target = self._get_object_at_position(gaze)
            confidence *= 0.8  # Gaze is less certain
        
        # Determine action
        action = None
        if voice_text:
            action = self._extract_action_from_voice(voice_text)
        
        # Build fused command
        command = MultimodalCommand(
            intent=intent,
            target=target,
            action=action,
            voice_input=voice_text,
            gesture_input=gesture,
            gaze_position=gaze,
            confidence=confidence
        )
        
        logger.info(f"Fused command: intent={intent.value}, target={target}, confidence={confidence:.2f}")
        
        return command
    
    def _parse_voice_intent(self, text: str) -> Tuple[CommandIntent, Optional[str], Optional[str]]:
        """Parse intent from voice command"""
        text_lower = text.lower()
        
        # Intent patterns
        if any(word in text_lower for word in ['open', 'launch', 'start', 'run']):
            return CommandIntent.EXECUTE, self._extract_app_name(text), 'open'
        
        elif any(word in text_lower for word in ['close', 'quit', 'exit']):
            return CommandIntent.EXECUTE, None, 'close'
        
        elif any(word in text_lower for word in ['delete', 'remove', 'trash']):
            return CommandIntent.DELETE, self._extract_target_from_voice(text), 'delete'
        
        elif any(word in text_lower for word in ['select', 'choose', 'pick']):
            return CommandIntent.SELECT, self._extract_target_from_voice(text), 'select'
        
        elif any(word in text_lower for word in ['scroll', 'move', 'navigate']):
            return CommandIntent.NAVIGATE, None, self._extract_direction(text)
        
        elif any(word in text_lower for word in ['yes', 'confirm', 'ok', 'sure']):
            return CommandIntent.CONFIRM, None, 'confirm'
        
        elif any(word in text_lower for word in ['no', 'cancel', 'nevermind']):
            return CommandIntent.CANCEL, None, 'cancel'
        
        else:
            return CommandIntent.QUERY, None, None
    
    def _gesture_to_intent(self, gesture: Optional[GestureEvent]) -> CommandIntent:
        """Convert gesture to intent"""
        if not gesture:
            return CommandIntent.QUERY
        
        gesture_type = gesture.gesture_type
        
        if gesture_type == GestureType.THUMBS_UP:
            return CommandIntent.CONFIRM
        elif gesture_type == GestureType.THUMBS_DOWN:
            return CommandIntent.CANCEL
        elif gesture_type == GestureType.POINTING:
            return CommandIntent.SELECT
        elif gesture_type == GestureType.FIST:
            return CommandIntent.DELETE
        elif gesture_type in [GestureType.SWIPE_LEFT, GestureType.SWIPE_RIGHT, 
                             GestureType.SWIPE_UP, GestureType.SWIPE_DOWN]:
            return CommandIntent.NAVIGATE
        else:
            return CommandIntent.EXECUTE
    
    def _extract_target_from_voice(self, text: str) -> Optional[str]:
        """Extract target from voice command"""
        # Look for demonstratives
        if any(word in text.lower() for word in ['this', 'that', 'these', 'those']):
            return 'pointed_object'  # Requires gesture/gaze
        
        # Extract filename/app name
        # Simplified - would need more sophisticated NLP
        return None
    
    def _extract_app_name(self, text: str) -> Optional[str]:
        """Extract app name from voice command"""
        text_lower = text.lower()
        
        # Common apps
        apps = {
            'browser': 'web browser',
            'chrome': 'Google Chrome',
            'firefox': 'Firefox',
            'safari': 'Safari',
            'terminal': 'Terminal',
            'finder': 'Finder',
            'explorer': 'File Explorer',
            'spotify': 'Spotify',
            'slack': 'Slack',
            'vscode': 'Visual Studio Code',
            'code': 'Visual Studio Code'
        }
        
        for key, app_name in apps.items():
            if key in text_lower:
                return app_name
        
        return None
    
    def _extract_action_from_voice(self, text: str) -> Optional[str]:
        """Extract action verb from voice command"""
        text_lower = text.lower()
        
        actions = ['open', 'close', 'delete', 'move', 'copy', 'paste', 'select', 
                  'scroll', 'click', 'drag', 'drop']
        
        for action in actions:
            if action in text_lower:
                return action
        
        return None
    
    def _extract_direction(self, text: str) -> str:
        """Extract direction from text"""
        text_lower = text.lower()
        
        if 'up' in text_lower:
            return 'up'
        elif 'down' in text_lower:
            return 'down'
        elif 'left' in text_lower:
            return 'left'
        elif 'right' in text_lower:
            return 'right'
        
        return 'forward'
    
    def _get_recent_voice(self, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """Get most recent voice command within timeout"""
        now = time.time()
        for voice_entry in reversed(self.voice_buffer):
            if now - voice_entry['timestamp'] <= timeout:
                return voice_entry
        return None
    
    def _get_recent_gesture(self, timeout: float = 2.0) -> Optional[GestureEvent]:
        """Get most recent gesture within timeout"""
        now = time.time()
        for gesture in reversed(self.gesture_buffer):
            if now - gesture.timestamp <= timeout:
                return gesture
        return None
    
    def _get_recent_gaze(self, timeout: float = 1.0) -> Optional[Tuple[float, float]]:
        """Get most recent gaze position within timeout"""
        now = time.time()
        for gaze_entry in reversed(self.gaze_buffer):
            if now - gaze_entry['timestamp'] <= timeout:
                return gaze_entry['position']
        return None
    
    def _get_object_at_position(self, position: Tuple[float, float]) -> Optional[str]:
        """Get UI object at screen position (normalized coordinates)"""
        # This would integrate with the UI system to detect what's at the position
        # For now, return placeholder
        return f"object_at_{position[0]:.2f}_{position[1]:.2f}"
    
    def _execute_command(self, command: MultimodalCommand) -> Dict[str, Any]:
        # Update guardian based on command intent
        if self.guardian_bridge:
            try:
                intent = command.intent.name if hasattr(command.intent, 'name') else str(command.intent)
                
                if 'OPEN' in intent or 'LAUNCH' in intent:
                    self.guardian_bridge.set_gesture('point')
                elif 'CLOSE' in intent or 'DELETE' in intent:
                    self.guardian_bridge.set_gesture('stop')
                elif 'SELECT' in intent:
                    self.guardian_bridge.set_gesture('point')
                
                self.guardian_bridge.set_activity('thinking')
            except Exception:
                pass
        """Execute the multimodal command"""
        logger.info(f"Executing multimodal command: {command.intent.value}")
        
        # Check if confirmation needed
        if command.needs_confirmation and command.intent not in [CommandIntent.CONFIRM, CommandIntent.CANCEL]:
            self.pending_command = command
            self._request_confirmation(command)
            return {'success': True, 'status': 'pending_confirmation', 'command': command.to_dict()}
        
        # Handle confirmation/cancel
        if command.intent == CommandIntent.CONFIRM:
            if self.pending_command:
                cmd = self.pending_command
                self.pending_command = None
                return self._execute_command(cmd)
            return {'success': False, 'error': 'Nothing to confirm'}
        
        elif command.intent == CommandIntent.CANCEL:
            if self.pending_command:
                self.pending_command = None
                return {'success': True, 'message': 'Command cancelled'}
            return {'success': False, 'error': 'Nothing to cancel'}
        
        # Execute based on intent
        result = None
        
        try:
            if command.intent == CommandIntent.EXECUTE:
                result = self._execute_action(command)
            
            elif command.intent == CommandIntent.SELECT:
                result = self._select_object(command)
            
            elif command.intent == CommandIntent.NAVIGATE:
                result = self._navigate(command)
            
            elif command.intent == CommandIntent.DELETE:
                result = self._delete_object(command)
            
            else:
                result = {'success': False, 'error': f'Unhandled intent: {command.intent.value}'}
            
            # Trigger callbacks
            for callback in self.command_callbacks:
                try:
                    callback(command, result)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            # Add to history
            self.command_history.append(command)
            
            return result
        
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_action(self, command: MultimodalCommand) -> Dict[str, Any]:
        """Execute an action command"""
        if command.action == 'open' and command.target:
            # Trigger UI to open app/file
            if EEL_AVAILABLE:
                try:
                    eel.open_application(command.target)()
                except:
                    pass
            return {'success': True, 'action': 'opened', 'target': command.target}
        
        return {'success': True, 'action': command.action}
    
    def _select_object(self, command: MultimodalCommand) -> Dict[str, Any]:
        """Select an object"""
        self.current_context['selected_object'] = command.target
        return {'success': True, 'selected': command.target}
    
    def _navigate(self, command: MultimodalCommand) -> Dict[str, Any]:
        """Navigate (scroll, swipe, etc.)"""
        direction = command.action or 'forward'
        
        if EEL_AVAILABLE:
            try:
                eel.perform_scroll(direction)()
            except:
                pass
        
        return {'success': True, 'navigation': direction}
    
    def _delete_object(self, command: MultimodalCommand) -> Dict[str, Any]:
        """Delete an object"""
        if not command.target:
            return {'success': False, 'error': 'No target specified'}
        
        # This would integrate with file system
        return {'success': True, 'deleted': command.target}
    
    def _request_confirmation(self, command: MultimodalCommand):
        """Request user confirmation"""
        logger.info(f"Requesting confirmation for: {command.intent.value}")
        
        if EEL_AVAILABLE:
            try:
                eel.show_multimodal_confirmation({
                    'intent': command.intent.value,
                    'target': command.target,
                    'action': command.action,
                    'message': f"Confirm: {command.action} {command.target}?"
                })()
            except:
                pass
        
        # Auto-cancel after timeout
        def cancel_pending():
            time.sleep(self.pending_timeout)
            if self.pending_command == command:
                self.pending_command = None
                logger.info("Confirmation timeout")
        
        self.pending_timer = threading.Thread(target=cancel_pending, daemon=True)
        self.pending_timer.start()
    
    def _record_interaction(self, command: MultimodalCommand, input_mode: InputMode):
        """Record interaction for learning"""
        if not self.ai_engine:
            return
        
        try:
            action = UserAction(
                timestamp=command.timestamp,
                action_type=command.intent.value,
                target=command.target or 'unknown',
                context={
                    'hour': time.localtime().tm_hour,
                    'day_of_week': time.localtime().tm_wday,
                    'mode': self.current_context['mode']
                },
                input_method=input_mode.value,
                success=True
            )
            
            self.ai_engine.record_action(action)
        
        except Exception as e:
            logger.error(f"Failed to record interaction: {e}")
    
    def register_command_callback(self, callback):
        """Register callback for command execution"""
        self.command_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get controller status"""
        return {
            'enabled': self.enabled,
            'current_mode': self.current_context['mode'],
            'pending_command': self.pending_command.to_dict() if self.pending_command else None,
            'voice_buffer_size': len(self.voice_buffer),
            'gesture_buffer_size': len(self.gesture_buffer),
            'command_history_size': len(self.command_history)
        }


# Global instance
_multimodal_controller = None


def get_multimodal_controller() -> MultimodalController:
    """Get or create global multimodal controller"""
    global _multimodal_controller
    if _multimodal_controller is None:
        _multimodal_controller = MultimodalController()
    return _multimodal_controller


# Eel integration
if EEL_AVAILABLE:
    def setup_multimodal_eel_api():
        """Setup Eel-exposed functions for multimodal control"""
        controller = get_multimodal_controller()
        
        @eel.expose
        def process_multimodal_voice(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
            """Process voice command with multimodal fusion"""
            return controller.process_voice_command(text, context)
        
        @eel.expose
        def update_gaze(x: float, y: float):
            """Update eye gaze position"""
            controller.update_gaze_position(x, y)
        
        @eel.expose
        def get_multimodal_status() -> Dict[str, Any]:
            """Get multimodal controller status"""
            return controller.get_status()
        
        @eel.expose
        def enable_multimodal(enabled: bool) -> Dict[str, Any]:
            """Enable/disable multimodal interaction"""
            if enabled:
                controller.enable()
            else:
                controller.disable()
            return {'success': True, 'enabled': enabled}
        
        logger.info("Multimodal controller Eel API initialized")
        return controller


__all__ = [
    'MultimodalController',
    'MultimodalCommand',
    'InputMode',
    'CommandIntent',
    'get_multimodal_controller',
    'setup_multimodal_eel_api'
]
