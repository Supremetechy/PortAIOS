"""
AI Guardian 3D Backend Bridge
Connects Python backend systems to the AI Guardian 3D frontend
"""

import logging
from typing import Dict, Any, Optional, Callable
import threading

logger = logging.getLogger("AIOS.AIGuardianBridge")

try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    EEL_AVAILABLE = False
    logger.warning("Eel not available - AI Guardian bridge will not work")


class AIGuardianBridge:
    """
    Bridge between backend systems and AI Guardian 3D frontend.
    Handles avatar state synchronization and command routing.
    """
    
    def __init__(self):
        self.lock = threading.Lock()
        self.current_state = {
            'activity': 'idle',
            'emotion': 'neutral',
            'gesture': 'none',
            'speaking': False
        }
        self.callback = None
        
    def set_callback(self, callback: Callable):
        """Set callback for state change notifications"""
        with self.lock:
            self.callback = callback
    
    def update_state(self, **kwargs) -> Dict[str, Any]:
        """Update guardian state and sync to frontend"""
        with self.lock:
            for key, value in kwargs.items():
                if key in self.current_state:
                    self.current_state[key] = value
            
            # Notify frontend if Eel is available
            if EEL_AVAILABLE:
                try:
                    eel.guardian_state_update(self.current_state)
                except Exception as e:
                    logger.debug(f"Could not sync to frontend: {e}")
            
            # Call registered callback
            if self.callback:
                try:
                    self.callback(self.current_state.copy())
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            return {'success': True, 'state': self.current_state.copy()}
    
    def set_activity(self, activity: str) -> Dict[str, Any]:
        """Set guardian activity: idle, listening, thinking, speaking"""
        return self.update_state(activity=activity)
    
    def set_emotion(self, emotion: str) -> Dict[str, Any]:
        """Set guardian emotion: neutral, happy, thinking, surprised"""
        return self.update_state(emotion=emotion)
    
    def set_gesture(self, gesture: str) -> Dict[str, Any]:
        """Set guardian gesture: none, stop, wave, point, thinking"""
        return self.update_state(gesture=gesture)
    
    def speak(self, text: str, emotion: Optional[str] = None, gesture: Optional[str] = None) -> Dict[str, Any]:
        """
        Make the guardian speak with optional emotion and gesture.
        Integrates with existing TTS system.
        """
        logger.info(f"[AIGuardian] Speaking: {text[:50]}...")
        
        # Update state
        updates = {'activity': 'speaking', 'speaking': True}
        if emotion:
            updates['emotion'] = emotion
        if gesture:
            updates['gesture'] = gesture
        
        self.update_state(**updates)
        
        # Send to frontend
        if EEL_AVAILABLE:
            try:
                eel.guardian_speak(text, emotion or 'neutral', gesture or 'none')
            except Exception as e:
                logger.debug(f"Could not send to frontend: {e}")
        
        return {'success': True, 'text': text}
    
    def stop_speaking(self) -> Dict[str, Any]:
        """Stop guardian from speaking"""
        if EEL_AVAILABLE:
            try:
                eel.guardian_stop()
            except Exception as e:
                logger.debug(f"Could not send stop to frontend: {e}")
        
        return self.update_state(activity='idle', speaking=False, gesture='none')
    
    def get_state(self) -> Dict[str, Any]:
        """Get current guardian state"""
        with self.lock:
            return self.current_state.copy()


# Global instance
_guardian_bridge = None


def get_guardian_bridge() -> AIGuardianBridge:
    """Get or create the global AI Guardian bridge instance"""
    global _guardian_bridge
    if _guardian_bridge is None:
        _guardian_bridge = AIGuardianBridge()
        logger.info("[AIGuardian] Bridge initialized")
    return _guardian_bridge


def setup_guardian_eel_api():
    """Setup Eel API endpoints for AI Guardian control"""
    if not EEL_AVAILABLE:
        logger.warning("Eel not available - Guardian API not registered")
        return
    
    bridge = get_guardian_bridge()
    
    @eel.expose
    def guardian_set_activity(activity: str) -> Dict[str, Any]:
        """Set guardian activity from frontend"""
        return bridge.set_activity(activity)
    
    @eel.expose
    def guardian_set_emotion(emotion: str) -> Dict[str, Any]:
        """Set guardian emotion from frontend"""
        return bridge.set_emotion(emotion)
    
    @eel.expose
    def guardian_set_gesture(gesture: str) -> Dict[str, Any]:
        """Set guardian gesture from frontend"""
        return bridge.set_gesture(gesture)
    
    @eel.expose
    def guardian_speak_backend(text: str, emotion: Optional[str] = None, 
                               gesture: Optional[str] = None) -> Dict[str, Any]:
        """Make guardian speak from backend with TTS integration"""
        return bridge.speak(text, emotion, gesture)
    
    @eel.expose
    def guardian_stop_backend() -> Dict[str, Any]:
        """Stop guardian from speaking"""
        return bridge.stop_speaking()
    
    @eel.expose
    def guardian_get_state() -> Dict[str, Any]:
        """Get current guardian state"""
        return bridge.get_state()
    
    logger.info("[AIGuardian] Eel API registered")


# Integration helpers for existing systems

def integrate_with_voice_assistant(voice_assistant):
    """
    Integrate AI Guardian with VoiceOnboardingAssistant.
    Makes the guardian react to voice assistant state changes.
    """
    bridge = get_guardian_bridge()
    
    # Wrap the speak method
    original_speak = voice_assistant.speak
    
    def guardian_speak(text: str):
        # Detect emotion/gesture from text
        text_lower = text.lower()
        
        emotion = 'neutral'
        gesture = 'none'
        
        # Auto-detect emotion
        if any(word in text_lower for word in ['great', 'excellent', 'perfect', 'success']):
            emotion = 'happy'
        elif any(word in text_lower for word in ['analyzing', 'processing', 'thinking']):
            emotion = 'thinking'
        elif any(word in text_lower for word in ['wow', 'amazing', 'incredible']):
            emotion = 'surprised'
        
        # Auto-detect gesture
        if any(word in text_lower for word in ['hello', 'hi', 'welcome', 'greet']):
            gesture = 'wave'
        elif any(word in text_lower for word in ['stop', 'wait', 'halt']):
            gesture = 'stop'
        elif any(word in text_lower for word in ['look', 'see', 'there', 'this']):
            gesture = 'point'
        elif any(word in text_lower for word in ['think', 'consider', 'analyze']):
            gesture = 'thinking'
        
        # Update guardian
        bridge.speak(text, emotion, gesture)
        
        # Call original speak
        original_speak(text)
    
    voice_assistant.speak = guardian_speak
    logger.info("[AIGuardian] Integrated with VoiceOnboardingAssistant")


def integrate_with_multimodal_controller(multimodal_controller):
    """
    Integrate AI Guardian with MultimodalController.
    Makes the guardian react to multimodal commands and gestures.
    """
    bridge = get_guardian_bridge()
    
    # Add callback for command execution
    def on_command_executed(command_data):
        if not command_data.get('success'):
            bridge.set_emotion('neutral')
            return
        
        # React based on command type
        intent = command_data.get('intent', '')
        
        if 'open' in intent or 'launch' in intent:
            bridge.set_emotion('neutral')
            bridge.set_gesture('point')
        elif 'close' in intent or 'delete' in intent:
            bridge.set_gesture('stop')
        elif 'select' in intent:
            bridge.set_gesture('point')
        elif 'navigate' in intent:
            bridge.set_gesture('point')
    
    multimodal_controller.register_command_callback(on_command_executed)
    logger.info("[AIGuardian] Integrated with MultimodalController")


def integrate_with_ui_voice_commands(ui_voice_handler):
    """
    Integrate AI Guardian with UIVoiceCommandHandler.
    Makes the guardian react to UI voice commands.
    """
    bridge = get_guardian_bridge()
    
    # Wrap process_command
    original_process = ui_voice_handler.process_command
    
    def guardian_process_command(text: str):
        # Set thinking state while processing
        bridge.set_activity('thinking')
        bridge.set_emotion('thinking')
        
        result = original_process(text)
        
        if result and result.get('success'):
            # Success - happy gesture
            bridge.set_emotion('happy')
            bridge.set_gesture('none')
        elif result and not result.get('success'):
            # Failure - neutral
            bridge.set_emotion('neutral')
            bridge.set_gesture('none')
        
        # Return to idle
        bridge.set_activity('idle')
        
        return result
    
    ui_voice_handler.process_command = guardian_process_command
    logger.info("[AIGuardian] Integrated with UIVoiceCommandHandler")


__all__ = [
    'AIGuardianBridge',
    'get_guardian_bridge',
    'setup_guardian_eel_api',
    'integrate_with_voice_assistant',
    'integrate_with_multimodal_controller',
    'integrate_with_ui_voice_commands'
]
