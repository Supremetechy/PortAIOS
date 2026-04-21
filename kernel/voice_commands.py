#!/usr/bin/env python3
"""
Voice Command Handlers for AIOS Onboarding
Backend processing for voice commands
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("VoiceCommands")


class OnboardingVoiceCommands:
    """Handle voice commands during onboarding"""
    
    def __init__(self):
        self.current_step = 0
        self.paused = False
        self.handlers = self._register_handlers()
    
    def _register_handlers(self) -> Dict:
        """Register command handlers"""
        return {
            'next': self.handle_next,
            'back': self.handle_back,
            'skip': self.handle_skip,
            'help': self.handle_help,
            'status': self.handle_status,
            'pause': self.handle_pause,
            'resume': self.handle_resume,
            'cancel': self.handle_cancel,
            'install': self.handle_install,
            'yes': self.handle_yes,
            'no': self.handle_no,
        }
    
    def process_command(self, command: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process a voice command"""
        logger.info(f"Processing command: '{command}'")
        
        if context:
            self.current_step = context.get('step', 0)
        
        cmd_lower = command.lower().strip()
        
        # Find matching handler
        for cmd_type, handler in self.handlers.items():
            if cmd_type in cmd_lower:
                return handler(command, context)
        
        # Parse complex commands
        result = self._parse_complex_command(cmd_lower, context)
        if result:
            return result
        
        return {
            'action': 'unknown',
            'success': False,
            'message': f"Command '{command}' not recognized"
        }
    
    def _parse_complex_command(self, command: str, context: Optional[Dict]) -> Optional[Dict]:
        """Parse complex multi-word commands"""
        
        # "go to step X"
        if 'go to step' in command:
            try:
                step_num = int(''.join(filter(str.isdigit, command)))
                return {
                    'action': 'goto',
                    'target_step': step_num,
                    'success': True
                }
            except:
                pass
        
        # "enable X" / "disable X"
        if command.startswith('enable '):
            feature = command.replace('enable ', '').strip()
            return {
                'action': 'enable',
                'feature': feature,
                'success': True
            }
        
        if command.startswith('disable '):
            feature = command.replace('disable ', '').strip()
            return {
                'action': 'disable',
                'feature': feature,
                'success': True
            }
        
        return None
    
    # Command Handlers
    def handle_next(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle next command"""
        return {
            'action': 'next',
            'success': True,
            'message': 'Moving to next step'
        }
    
    def handle_back(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle back command"""
        return {
            'action': 'back',
            'success': True,
            'message': 'Going back'
        }
    
    def handle_skip(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle skip command"""
        return {
            'action': 'skip',
            'success': True,
            'message': 'Skipping current step'
        }
    
    def handle_help(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle help command"""
        hints = self.get_hints_for_context(context)
        return {
            'action': 'help',
            'success': True,
            'hints': hints,
            'message': f"Available commands: {', '.join(hints)}"
        }
    
    def handle_status(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle status command"""
        step = context.get('step', 0) if context else self.current_step
        step_type = context.get('type', 'general') if context else 'general'
        title = context.get('title', 'Unknown') if context else 'Unknown'
        
        return {
            'action': 'status',
            'success': True,
            'step': step,
            'step_type': step_type,
            'title': title,
            'paused': self.paused
        }
    
    def handle_pause(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle pause command"""
        self.paused = True
        return {
            'action': 'pause',
            'success': True,
            'paused': True,
            'message': 'Process paused'
        }
    
    def handle_resume(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle resume command"""
        self.paused = False
        return {
            'action': 'resume',
            'success': True,
            'paused': False,
            'message': 'Resuming'
        }
    
    def handle_cancel(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle cancel command"""
        return {
            'action': 'cancel',
            'success': True,
            'requires_confirmation': True,
            'message': 'Are you sure you want to cancel?'
        }
    
    def handle_install(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle install command"""
        return {
            'action': 'install',
            'success': True,
            'message': 'Starting installation'
        }
    
    def handle_yes(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle yes confirmation"""
        return {
            'action': 'confirm',
            'value': True,
            'success': True
        }
    
    def handle_no(self, command: str, context: Optional[Dict]) -> Dict:
        """Handle no confirmation"""
        return {
            'action': 'confirm',
            'value': False,
            'success': True
        }
    
    def get_hints_for_context(self, context: Optional[Dict]) -> List[str]:
        """Get voice hints based on context"""
        if not context:
            return ['next', 'back', 'help', 'status']
        
        step_type = context.get('type', 'general')
        
        hint_map = {
            'welcome': ['next', 'help', 'skip'],
            'hardware_detection': ['next', 'back', 'status'],
            'gpu_config': ['next', 'back', 'enable GPU', 'disable GPU'],
            'system_config': ['next', 'back', 'customize', 'use defaults'],
            'installation': ['install', 'pause', 'status', 'cancel'],
            'complete': ['finish', 'restart', 'summary']
        }
        
        return hint_map.get(step_type, ['next', 'back', 'help', 'status'])


# Global instance
_voice_commands = OnboardingVoiceCommands()


def setup_voice_commands_for_eel(eel_module):
    """Setup Eel-exposed voice command functions"""
    
    @eel_module.expose
    def process_voice_command(command: str, context: Optional[Dict] = None):
        """Process voice command from frontend"""
        return _voice_commands.process_command(command, context)
    
    @eel_module.expose
    def get_step_voice_hints(context: Optional[Dict] = None):
        """Get voice hints for current step"""
        return _voice_commands.get_hints_for_context(context)
    
    @eel_module.expose
    def request_voice_input(input_type: str = 'text'):
        """Request specific voice input"""
        logger.info(f"Voice input requested: {input_type}")
        return {'status': 'ok', 'type': input_type}
    
    logger.info("Voice command handlers registered with Eel")
    return _voice_commands


if __name__ == "__main__":
    # Test command processing
    commands = OnboardingVoiceCommands()
    
    test_cases = [
        "next",
        "go back",
        "help",
        "status",
        "enable GPU acceleration",
        "disable automatic updates",
        "install",
        "pause",
    ]
    
    print("=" * 60)
    print("Testing Voice Commands")
    print("=" * 60)
    
    for cmd in test_cases:
        result = commands.process_command(cmd)
        print(f"\nCommand: '{cmd}'")
        print(f"Result: {result}")
    
    print("\n" + "=" * 60)
