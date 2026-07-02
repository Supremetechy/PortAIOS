"""
Streaming Parser

Parses voice commands as they're being spoken (streaming)
Reduces latency between speech and action
"""

import logging
import threading
from typing import Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue

logger = logging.getLogger("MiniKernel.Streaming")


@dataclass
class PartialIntent:
    """Represents a partial intent being built"""
    text_so_far: str = ""
    confidence: float = 0.0
    predicted_action: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class StreamingParser:
    """
    Streaming Parser for real-time command processing
    
    Strategy:
    1. Receive partial transcriptions as user speaks
    2. Build confidence as more words arrive
    3. Execute when confidence threshold reached
    4. Don't wait for complete sentence
    
    Example:
    - User says: "find the file..."
    - After "find" → confidence 30%
    - After "find the" → confidence 50%
    - After "find the file" → confidence 80% → EXECUTE
    - User still saying: "...I downloaded yesterday" (refinement)
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.75,
        execute_callback: Optional[Callable[[str], None]] = None
    ):
        self.confidence_threshold = confidence_threshold
        self.execute_callback = execute_callback
        
        self.partial_intent: Optional[PartialIntent] = None
        self.word_buffer: List[str] = []
        
        # Keyword triggers for fast execution
        self.action_keywords = {
            "find": 0.7,
            "search": 0.7,
            "delete": 0.9,  # Higher threshold for destructive
            "move": 0.6,
            "copy": 0.6,
            "list": 0.5,
            "show": 0.5,
            "open": 0.6,
            "kill": 0.9,
            "stop": 0.8,
            "install": 0.8,
        }
        
        self._lock = threading.Lock()
        
        logger.info(f"Streaming Parser initialized (threshold={confidence_threshold})")
    
    def process_word(self, word: str) -> Optional[str]:
        """
        Process a single word from streaming STT
        
        Args:
            word: Word from speech recognition
            
        Returns:
            Action to execute if threshold reached, None otherwise
        """
        with self._lock:
            # Add to buffer
            self.word_buffer.append(word.lower())
            
            # Update partial intent
            text_so_far = " ".join(self.word_buffer)
            
            if not self.partial_intent:
                self.partial_intent = PartialIntent(text_so_far=text_so_far)
            else:
                self.partial_intent.text_so_far = text_so_far
            
            # Calculate confidence
            confidence = self._calculate_confidence()
            self.partial_intent.confidence = confidence
            
            # Check if should execute
            if confidence >= self.confidence_threshold:
                action = text_so_far
                
                # Reset for next command
                self.reset()
                
                # Trigger callback
                if self.execute_callback:
                    self.execute_callback(action)
                
                logger.info(f"Streaming execute: '{action}' (confidence={confidence:.2f})")
                return action
            
            logger.debug(f"Partial: '{text_so_far}' (confidence={confidence:.2f})")
            return None
    
    def process_transcript(self, transcript: str) -> Optional[str]:
        """
        Process a complete or partial transcript
        
        Args:
            transcript: Text from STT (may be partial)
            
        Returns:
            Action to execute if threshold reached
        """
        words = transcript.split()
        
        result = None
        for word in words:
            result = self.process_word(word)
            if result:
                break
        
        return result
    
    def _calculate_confidence(self) -> float:
        """
        Calculate confidence that we have a complete intent
        
        Strategy:
        1. Check for action keywords
        2. Count meaningful words
        3. Check for typical command structure
        """
        text = self.partial_intent.text_so_far
        words = self.word_buffer
        
        confidence = 0.0
        
        # Check for action keywords (highest weight)
        for keyword, threshold in self.action_keywords.items():
            if keyword in words:
                confidence = max(confidence, threshold)
                self.partial_intent.predicted_action = keyword
                break
        
        # Length-based confidence
        word_count = len(words)
        if word_count >= 2:
            confidence += 0.1
        if word_count >= 3:
            confidence += 0.1
        if word_count >= 4:
            confidence += 0.05
        
        # Pattern matching
        if self._matches_command_pattern(words):
            confidence += 0.2
        
        # Cap at 1.0
        return min(confidence, 1.0)
    
    def _matches_command_pattern(self, words: List[str]) -> bool:
        """
        Check if words match typical command patterns
        
        Patterns:
        - [action] [object]
        - [action] [object] [preposition] [location]
        - [show/list] [target]
        """
        if len(words) < 2:
            return False
        
        # Common patterns
        action_verbs = {"find", "search", "move", "copy", "delete", "list", "show", "open", "kill", "stop", "install"}
        prepositions = {"to", "in", "from", "at"}
        
        # Pattern: [verb] [noun]
        if words[0] in action_verbs and len(words) >= 2:
            return True
        
        # Pattern: [verb] [article] [noun]
        if len(words) >= 3 and words[0] in action_verbs and words[1] in {"the", "a", "an"}:
            return True
        
        return False
    
    def reset(self) -> None:
        """Reset parser state for next command"""
        with self._lock:
            self.partial_intent = None
            self.word_buffer = []
    
    def get_partial_intent(self) -> Optional[PartialIntent]:
        """Get current partial intent"""
        with self._lock:
            return self.partial_intent
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """Update confidence threshold"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        logger.debug(f"Confidence threshold set to {threshold:.2f}")


class StreamingVoiceCommandProcessor:
    """
    Complete streaming voice command processor
    
    Combines:
    - Streaming STT (partial transcripts)
    - Streaming parser
    - Intent execution
    """
    
    def __init__(
        self,
        voice_pipeline,
        intent_parser,
        execution_engine
    ):
        self.voice = voice_pipeline
        self.parser = intent_parser
        self.executor = execution_engine
        
        self.streaming_parser = StreamingParser(
            confidence_threshold=0.75,
            execute_callback=self._execute_intent
        )
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        logger.info("Streaming Voice Command Processor initialized")
    
    def start(self) -> None:
        """Start streaming processing"""
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info("Streaming processor started")
    
    def stop(self) -> None:
        """Stop streaming processing"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Streaming processor stopped")
    
    def _process_loop(self) -> None:
        """Main processing loop"""
        while self._running:
            try:
                # Listen for speech
                transcript = self.voice.listen(timeout_seconds=5)
                
                if transcript:
                    # Process streaming
                    self.streaming_parser.process_transcript(transcript)
            
            except Exception as e:
                logger.error(f"Streaming error: {e}")
    
    def _execute_intent(self, command: str) -> None:
        """Execute a command (callback from streaming parser)"""
        try:
            # Parse intent
            intent = self.parser.parse(command)
            
            # Validate
            from minikernel.intent.command_validator import CommandValidator
            validator = CommandValidator()
            validation = validator.validate(intent)
            
            # Execute
            result = self.executor.execute(intent, validation, confirmed=False)
            
            if result.success:
                logger.info(f"Executed: {command}")
                self.voice.speak("Done")
            else:
                logger.warning(f"Failed: {command}")
                self.voice.speak("Could not complete that action")
        
        except Exception as e:
            logger.error(f"Execution error: {e}")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    def mock_execute(action: str):
        print(f"EXECUTE: {action}")
    
    parser = StreamingParser(execute_callback=mock_execute)
    
    # Simulate streaming words
    test_words = ["find", "the", "file", "I", "downloaded"]
    
    for word in test_words:
        result = parser.process_word(word)
        if result:
            print(f"Executed early: {result}")
            break
