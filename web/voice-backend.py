#!/usr/bin/env python3
"""
Voice Backend for AIOS Onboarding
Extends avatar-bridge.py with voice command processing
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, Optional, TYPE_CHECKING, List, Tuple
from datetime import datetime
from collections import deque

# Speech recognition backend (optional advanced features)
if TYPE_CHECKING:
    import speech_recognition as sr
else:
    sr = None
    try:
        import speech_recognition as sr
        SPEECH_RECOGNITION_AVAILABLE = True
    except ImportError:
        SPEECH_RECOGNITION_AVAILABLE = False
        logging.warning("speech_recognition not available (pip install SpeechRecognition)")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceBackend")


class VoiceCommandProcessor:
    """Process and route voice commands with advanced NLP"""
    
    def __init__(self):
        self.command_handlers = {}
        self.context = {}
        self.awaiting_response = False
        self.expected_response_type = None
        
        # Advanced NLP features
        self.command_history: deque = deque(maxlen=10)  # Last 10 commands
        self.multi_step_buffer: List[str] = []  # Buffer for multi-step commands
        self.intent_patterns = self._build_intent_patterns()
        self.context_state = {
            'current_step': None,
            'last_action': None,
            'user_preferences': {},
            'conversation_context': []
        }
        
    def register_handler(self, command_type: str, handler):
        """Register a command handler"""
        self.command_handlers[command_type] = handler
        logger.info(f"Registered handler for: {command_type}")
    
    def _build_intent_patterns(self) -> Dict[str, List[Tuple[re.Pattern, str]]]:
        """Build regex patterns for intent detection"""
        return {
            'navigation': [
                (re.compile(r'\b(go|move|navigate)\s+to\s+(\w+)'), 'navigate_to'),
                (re.compile(r'\b(show|display|open)\s+(\w+)'), 'show'),
                (re.compile(r'\b(close|hide|exit)\s+(\w+)?'), 'close'),
            ],
            'action': [
                (re.compile(r'\b(start|begin|initiate)\s+(\w+)'), 'start'),
                (re.compile(r'\b(stop|end|terminate)\s+(\w+)'), 'stop'),
                (re.compile(r'\b(pause|resume)\s+(\w+)?'), 'pause_resume'),
                (re.compile(r'\b(save|store)\s+(\w+)'), 'save'),
                (re.compile(r'\b(load|retrieve)\s+(\w+)'), 'load'),
            ],
            'query': [
                (re.compile(r'\b(what|which|who|where|when|why|how)\s+'), 'question'),
                (re.compile(r'\b(tell me|show me|explain)\s+'), 'request_info'),
                (re.compile(r'\b(is|are|can|do|does)\s+'), 'yes_no_question'),
            ],
            'multi_step': [
                (re.compile(r'\b(then|and then|after that|next)\s+'), 'continuation'),
                (re.compile(r'\b(first|second|third|finally)\s+'), 'sequence'),
            ]
        }
    
    async def process_command(self, command: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a voice command with context awareness and return action"""
        
        try:
            logger.info(f"Processing command: '{command}'")
            
            # Validate input
            if not command or not isinstance(command, str):
                return {
                    'action': 'error',
                    'message': 'Invalid command',
                    'command': command
                }
            
            # Add to command history
            self.command_history.append({
                'command': command,
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id
            })
            
            # Check for multi-step command continuation
            # Only buffer if we already have commands OR it's clearly a continuation word
            if self._is_multi_step_continuation(command):
                self.multi_step_buffer.append(command)
                return {
                    'action': 'multi_step_buffered',
                    'message': 'Command buffered. Continue or say "execute"',
                    'buffered_commands': len(self.multi_step_buffer)
                }
            # If buffer has commands but this isn't a continuation, execute buffer first
            elif self.multi_step_buffer:
                # Save current command for after
                current_cmd = command
                result = await self._execute_multi_step_commands()
                # Now process current command
                return result
            
            # Check if user wants to execute buffered commands
            if command.lower().strip() in ['execute', 'run', 'do it', 'go']:
                if self.multi_step_buffer:
                    return await self._execute_multi_step_commands()
                else:
                    return {
                        'action': 'info',
                        'message': 'No buffered commands to execute'
                    }
            
            # Detect intent
            intent = self._detect_intent(command)
            
            # Parse command with context awareness
            parsed = self.parse_command(command, intent)
            logger.info(f"Parsed: {parsed} | Intent: {intent}")
            
            # Update context
            self._update_context(command, parsed, intent)
            
            # If awaiting specific response
            if self.awaiting_response:
                return await self.handle_response(parsed, command)
            
            # Route to appropriate handler
            handler = self.command_handlers.get(parsed['type'])
            
            if handler:
                result = await handler(parsed, command, self.context)
                # Store last action for context
                self.context_state['last_action'] = result.get('action')
                return result
            
            # Try intent-based handling if no direct handler
            if intent and intent != 'unknown':
                return await self._handle_by_intent(intent, command, parsed)
            
            # Default handler
            return {
                'action': 'unknown',
                'message': 'Command not recognized',
                'command': command,
                'suggestion': self._suggest_command(command)
            }
        
        except Exception as e:
            logger.error(f"Error processing command '{command}': {e}", exc_info=True)
            return {
                'action': 'error',
                'message': f'Error processing command: {str(e)}',
                'command': command
            }
    
    def _is_multi_step_continuation(self, command: str) -> bool:
        """Check if command is part of a multi-step sequence"""
        lower = command.lower().strip()
        # Only match if it's a continuation phrase, not a standalone command
        continuation_words = ['then', 'and then', 'after that', 'afterwards']
        # "next" only counts if followed by more text (e.g., "next go to settings")
        if lower.startswith('next ') and len(lower.split()) > 1:
            return True
        return any(lower.startswith(word) for word in continuation_words)
    
    async def _execute_multi_step_commands(self) -> Dict[str, Any]:
        """Execute all buffered multi-step commands"""
        results = []
        commands = list(self.multi_step_buffer)
        self.multi_step_buffer.clear()
        
        for cmd in commands:
            # Remove continuation words
            clean_cmd = re.sub(r'^(then|and then|after that|next|afterwards)\s+', '', cmd.lower().strip())
            
            # Detect intent for the cleaned command
            intent = self._detect_intent(clean_cmd)
            parsed = self.parse_command(clean_cmd, intent)
            handler = self.command_handlers.get(parsed['type'])
            
            if handler:
                result = await handler(parsed, clean_cmd, self.context)
                results.append(result)
            else:
                # Try intent-based handling
                result = await self._handle_by_intent(intent, clean_cmd, parsed) if intent else {
                    'action': 'unknown',
                    'command': clean_cmd
                }
                results.append(result)
        
        return {
            'action': 'multi_step_executed',
            'message': f'Executed {len(results)} commands',
            'results': results
        }
    
    def _detect_intent(self, command: str) -> Optional[str]:
        """Detect user intent from command using pattern matching"""
        lower_cmd = command.lower().strip()
        
        for intent_category, patterns in self.intent_patterns.items():
            for pattern, intent_type in patterns:
                if pattern.search(lower_cmd):
                    return f"{intent_category}:{intent_type}"
        
        return None
    
    def _update_context(self, command: str, parsed: Dict, intent: Optional[str]):
        """Update conversation context based on command"""
        self.context_state['conversation_context'].append({
            'command': command,
            'parsed_type': parsed['type'],
            'intent': intent,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 5 context items
        if len(self.context_state['conversation_context']) > 5:
            self.context_state['conversation_context'].pop(0)
    
    async def _handle_by_intent(self, intent: str, command: str, parsed: Dict) -> Dict[str, Any]:
        """Handle command based on detected intent"""
        category, intent_type = intent.split(':') if ':' in intent else (intent, 'unknown')
        
        if category == 'query':
            return {
                'action': 'query',
                'intent': intent_type,
                'message': f'Question detected: {command}',
                'requires_context': True
            }
        elif category == 'navigation':
            # Extract target from command
            match = re.search(r'(go|move|navigate|show|display|open)\s+(?:to\s+)?(\w+)', command.lower())
            target = match.group(2) if match else None
            return {
                'action': 'navigate',
                'direction': intent_type,
                'target': target,
                'message': f'Navigating: {intent_type} to {target}'
            }
        elif category == 'action':
            match = re.search(r'(start|stop|pause|resume|save|load)\s+(\w+)', command.lower())
            target = match.group(2) if match else None
            return {
                'action': intent_type,
                'target': target,
                'message': f'Action: {intent_type} {target or ""}'
            }
        
        return {
            'action': 'intent_detected',
            'intent': intent,
            'message': f'Detected intent: {intent}'
        }
    
    def _suggest_command(self, command: str) -> Optional[str]:
        """Suggest a similar command based on history and patterns"""
        lower_cmd = command.lower()
        
        # Check for common misspellings or variations
        suggestions = {
            'nxt': 'next',
            'bck': 'back',
            'hlp': 'help',
            'skp': 'skip',
            'ys': 'yes',
            'n': 'no'
        }
        
        for typo, correct in suggestions.items():
            if typo in lower_cmd:
                return f"Did you mean '{correct}'?"
        
        # Check command history for similar patterns
        if self.command_history:
            last_cmd = self.command_history[-1]['command'].lower()
            # Simple similarity check
            if len(set(lower_cmd.split()) & set(last_cmd.split())) > 0:
                return f"Similar to your last command: '{last_cmd}'"
        
        return None
    
    def parse_command(self, command: str, intent: Optional[str] = None) -> Dict[str, Any]:
        """Parse command into type and parameters with improved NLP and context awareness"""
        
        lower_cmd = command.lower().strip()
        words = re.findall(r"\b\w+\b", lower_cmd)
        
        # Sentiment analysis for mixed phrases (e.g., "yeah no" or "no way")
        affirmative_words = ['yes', 'yeah', 'yep', 'sure', 'okay', 'ok', 'fine', 'correct', 'right', 'affirmative']
        negative_words = ['no', 'nope', 'nah', 'not', 'never', 'negative', 'wrong']
        
        affirmative_count = sum(1 for word in words if word in affirmative_words)
        negative_count = sum(1 for word in words if word in negative_words)
        
        # Navigation commands
        if any(word in words for word in ['next', 'continue', 'proceed', 'forward']):
            return {'type': 'next', 'params': []}
        
        if any(word in words for word in ['back', 'previous', 'return', 'backward']):
            return {'type': 'back', 'params': []}
        
        if 'skip' in words:
            return {'type': 'skip', 'params': []}
        
        # Confirmation with sentiment analysis
        # Check for negative phrases that override affirmatives
        negative_phrases = ['no way', 'not really', 'not sure', 'nah yeah', 'yeah no']
        if any(phrase in lower_cmd for phrase in negative_phrases):
            return {'type': 'no', 'params': []}
        
        # Affirmative phrases that override negatives  
        affirmative_phrases = ['yes please', 'yeah sure', 'sure thing', 'sounds good']
        if any(phrase in lower_cmd for phrase in affirmative_phrases):
            return {'type': 'yes', 'params': []}
        
        # Use word count for mixed signals
        if affirmative_count > 0 or negative_count > 0:
            # If both present, last word wins (more natural)
            last_sentiment_word = None
            for word in reversed(words):
                if word in affirmative_words or word in negative_words:
                    last_sentiment_word = word
                    break
            
            if last_sentiment_word:
                if last_sentiment_word in affirmative_words:
                    return {'type': 'yes', 'params': []}
                elif last_sentiment_word in negative_words:
                    return {'type': 'no', 'params': []}
        
        # Help
        if any(word in words for word in ['help', 'what', 'how', 'explain']):
            return {'type': 'help', 'params': []}
        
        # Repeat
        if 'repeat' in words or 'again' in words or 'say again' in lower_cmd:
            return {'type': 'repeat', 'params': []}
        
        # Input (e.g., "type John Doe")
        if lower_cmd.startswith('type ') or lower_cmd.startswith('enter '):
            value = command.split(None, 1)[1] if ' ' in command else ''
            return {'type': 'input', 'params': [value]}
        
        # Text
        if lower_cmd.startswith('say '):
            value = command.split(None, 1)[1] if ' ' in command else ''
            return {'type': 'text', 'params': [value]}
        
        # Custom/unknown
        return {'type': 'custom', 'params': [command]}
    
    async def handle_response(self, parsed: Dict, raw_command: str) -> Dict[str, Any]:
        """Handle response when awaiting specific input"""
        
        if self.expected_response_type == 'yes_no':
            if parsed['type'] == 'yes':
                self.awaiting_response = False
                self.expected_response_type = None
                return {'action': 'response_yes', 'value': True}
            elif parsed['type'] == 'no':
                self.awaiting_response = False
                self.expected_response_type = None
                return {'action': 'response_no', 'value': False}
            else:
                return {
                    'action': 'clarify',
                    'message': 'Please say yes or no'
                }
        
        elif self.expected_response_type == 'text':
            self.awaiting_response = False
            self.expected_response_type = None
            return {
                'action': 'response_text',
                'value': raw_command
            }
        
        return {'action': 'unknown'}
    
    def request_response(self, response_type: str):
        """Request a specific type of voice response"""
        self.awaiting_response = True
        self.expected_response_type = response_type
        logger.info(f"Requesting {response_type} response")


class AdvancedVoiceRecognition:
    """
    Advanced voice recognition using offline models
    Optional enhancement over Web Speech API
    """
    
    def __init__(self):
        if not SPEECH_RECOGNITION_AVAILABLE:
            raise RuntimeError("speech_recognition library not available")
        
        if sr is None:
            raise RuntimeError("speech_recognition module not loaded")
        
        self.recognizer: 'sr.Recognizer' = sr.Recognizer()
        self.microphone: Optional['sr.Microphone'] = None
        
    def recognize_from_audio(self, audio_data: bytes) -> Optional[str]:
        """Recognize speech from audio bytes"""
        if sr is None:
            return None
            
        try:
            # Convert bytes to AudioData
            audio: 'sr.AudioData' = sr.AudioData(audio_data, 16000, 2)
            
            # Try multiple engines
            try:
                # Google Speech Recognition (requires internet)
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                logger.warning("Could not understand audio")
                return None
            except sr.RequestError as e:
                logger.error(f"Recognition service error: {e}")
                
                # Fallback to offline Sphinx
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    return text
                except:
                    return None
        
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return None
    
    def listen_from_microphone(self, timeout: int = 5) -> Optional[str]:
        """Listen directly from microphone (for testing)"""
        if sr is None:
            return None
            
        if not self.microphone:
            self.microphone = sr.Microphone()
        
        try:
            with self.microphone as source:
                logger.info("Listening from microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout)
                
            logger.info("Processing audio...")
            text = self.recognizer.recognize_google(audio)
            return text
        
        except sr.WaitTimeoutError:
            logger.warning("Listening timeout")
            return None
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return None
        except Exception as e:
            logger.error(f"Microphone error: {e}")
            return None


# Default command handlers
async def handle_next(parsed, command, context):
    """Handle next command"""
    return {
        'action': 'navigate',
        'direction': 'next',
        'message': 'Moving to next step'
    }

async def handle_back(parsed, command, context):
    """Handle back command"""
    return {
        'action': 'navigate',
        'direction': 'back',
        'message': 'Going back'
    }

async def handle_help(parsed, command, context):
    """Handle help command"""
    return {
        'action': 'help',
        'message': 'Available commands: next, back, yes, no, repeat, type [text]'
    }

async def handle_repeat(parsed, command, context):
    """Handle repeat command"""
    return {
        'action': 'repeat',
        'message': 'Repeating current step'
    }

async def handle_input(parsed, command, context):
    """Handle input command"""
    value = parsed['params'][0] if parsed['params'] else ''
    return {
        'action': 'input',
        'value': value,
        'message': f'Input received: {value}'
    }

async def handle_yes(parsed, command, context):
    """Handle yes command"""
    return {
        'action': 'confirm',
        'value': True,
        'message': 'Confirmed'
    }

async def handle_no(parsed, command, context):
    """Handle no command"""
    return {
        'action': 'confirm',
        'value': False,
        'message': 'Declined'
    }

async def handle_skip(parsed, command, context):
    """Handle skip command"""
    return {
        'action': 'navigate',
        'direction': 'skip',
        'message': 'Skipping current step'
    }


# Integration with WebSocket server
class VoiceWebSocketHandler:
    """Handle voice-related WebSocket messages"""
    
    def __init__(self, command_processor: VoiceCommandProcessor):
        self.processor = command_processor
    
    async def handle_message(self, message_type: str, data: Dict, websocket):
        """Handle voice-related WebSocket message"""
        
        try:
            if message_type == 'voice_command':
                # Process voice command
                command = data.get('command', '')
                result = await self.processor.process_command(command)
                
                # Send result back to client
                await websocket.send(json.dumps({
                    'type': 'voice_command_result',
                    'result': result
                }))
            
            elif message_type == 'request_voice_input':
                # Request specific voice input from user
                response_type = data.get('response_type', 'text')
                self.processor.request_response(response_type)
                
                await websocket.send(json.dumps({
                    'type': 'voice_input_requested',
                    'response_type': response_type
                }))
            
            elif message_type == 'voice_audio_data':
                # Process audio data (if using advanced recognition)
                audio_data = data.get('audio', '')
                # Handle audio processing here
                pass
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
            try:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': str(e)
                }))
            except:
                pass  # Websocket might be closed


def create_voice_processor():
    """Create and configure voice command processor"""
    
    processor = VoiceCommandProcessor()
    
    # Register default handlers
    processor.register_handler('next', handle_next)
    processor.register_handler('back', handle_back)
    processor.register_handler('help', handle_help)
    processor.register_handler('repeat', handle_repeat)
    processor.register_handler('input', handle_input)
    processor.register_handler('yes', handle_yes)
    processor.register_handler('no', handle_no)
    processor.register_handler('skip', handle_skip)
    
    return processor


# Eel integration functions
def setup_eel_voice_functions(eel_module):
    """Setup Eel-exposed voice functions"""
    
    processor = create_voice_processor()
    
    @eel_module.expose
    def process_voice_command(command: str):
        """Process voice command from frontend"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(processor.process_command(command))
        loop.close()
        return result
    
    @eel_module.expose
    def request_voice_input(response_type: str = 'text'):
        """Request voice input from user"""
        processor.request_response(response_type)
        return {'status': 'ok', 'awaiting': response_type}
    
    return processor


# CLI testing
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("AIOS Voice Backend - Test Mode")
    print("=" * 60)
    
    processor = create_voice_processor()
    
    # Test basic commands
    test_commands = [
        "next",
        "go back",
        "yes",
        "help",
        "type John Doe",
        "repeat that"
    ]
    
    async def test():
        print("\nTesting command parsing:\n")
        
        for cmd in test_commands:
            result = await processor.process_command(cmd)
            print(f"Command: '{cmd}'")
            print(f"Result: {result}")
            print()
    
    asyncio.run(test())
    
    # Interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        print("\n" + "=" * 60)
        print("Interactive Mode - Enter commands (Ctrl+C to exit)")
        print("=" * 60)
        
        async def interactive():
            while True:
                try:
                    cmd = input("\nYou: ")
                    if cmd.lower() in ['quit', 'exit']:
                        break
                    
                    result = await processor.process_command(cmd)
                    print(f"Result: {result}")
                
                except KeyboardInterrupt:
                    break
        
        asyncio.run(interactive())
    
    # Microphone test
    if len(sys.argv) > 1 and sys.argv[1] == '--mic':
        if SPEECH_RECOGNITION_AVAILABLE:
            print("\n" + "=" * 60)
            print("Microphone Test - Speak now!")
            print("=" * 60)
            
            recognizer = AdvancedVoiceRecognition()
            
            async def mic_test():
                text = recognizer.listen_from_microphone(timeout=10)
                
                if text:
                    print(f"\nHeard: '{text}'")
                    result = await processor.process_command(text)
                    print(f"Result: {result}")
                else:
                    print("No speech detected")
            
            asyncio.run(mic_test())
        else:
            print("speech_recognition not available")
            print("Install with: pip install SpeechRecognition pyaudio")
