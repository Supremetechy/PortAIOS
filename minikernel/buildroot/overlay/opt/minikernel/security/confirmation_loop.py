"""
Confirmation Loop

Human-in-the-loop verification for risky operations
Implements the safety confirmation mechanism
"""

import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger("MiniKernel.Confirmation")


class ConfirmationMode(Enum):
    """Confirmation modes"""
    VOICE = "voice"         # Voice confirmation
    TEXT = "text"           # Text input
    AUTO_APPROVE = "auto"   # Auto-approve (for testing)
    AUTO_DENY = "deny"      # Auto-deny (lockdown mode)


@dataclass
class ConfirmationRequest:
    """Represents a confirmation request"""
    request_id: str
    prompt: str
    command: str
    risk_level: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ConfirmationLoop:
    """
    Human-in-the-Loop Confirmation System
    
    For destructive or risky operations, require explicit confirmation
    
    Example flow:
    1. AI wants to delete files
    2. System generates confirmation request
    3. User is prompted (voice or text)
    4. User approves/denies
    5. System executes or aborts
    
    Modes:
    - Voice: "Are you sure you want to delete this? Say yes or no"
    - Text: Interactive prompt
    - Auto: For testing/automation
    """
    
    def __init__(
        self,
        mode: ConfirmationMode = ConfirmationMode.VOICE,
        voice_pipeline=None
    ):
        self.mode = mode
        self.voice = voice_pipeline
        
        # Pending confirmations
        self.pending: Dict[str, ConfirmationRequest] = {}
        
        # Confirmation history
        self.history: List[Dict[str, Any]] = []
        
        # Custom confirmation handlers
        self.handlers: Dict[ConfirmationMode, Callable] = {
            ConfirmationMode.VOICE: self._voice_confirm,
            ConfirmationMode.TEXT: self._text_confirm,
            ConfirmationMode.AUTO_APPROVE: self._auto_approve,
            ConfirmationMode.AUTO_DENY: self._auto_deny
        }
        
        logger.info(f"Confirmation Loop initialized (mode={mode.value})")
    
    def request_confirmation(
        self,
        prompt: str,
        command: str,
        risk_level: str = "medium"
    ) -> bool:
        """
        Request user confirmation
        
        Args:
            prompt: Confirmation prompt to show user
            command: Command being confirmed
            risk_level: Risk level (low, medium, high, critical)
            
        Returns:
            True if user confirmed, False otherwise
        """
        import uuid
        
        request_id = str(uuid.uuid4())[:8]
        
        request = ConfirmationRequest(
            request_id=request_id,
            prompt=prompt,
            command=command,
            risk_level=risk_level
        )
        
        self.pending[request_id] = request
        
        logger.info(f"Confirmation requested: {prompt}")
        
        # Get handler for current mode
        handler = self.handlers.get(self.mode, self._text_confirm)
        
        try:
            # Request confirmation
            confirmed = handler(request)
            
            # Record in history
            self._record_confirmation(request, confirmed)
            
            # Remove from pending
            if request_id in self.pending:
                del self.pending[request_id]
            
            return confirmed
            
        except Exception as e:
            logger.error(f"Confirmation error: {e}")
            # On error, deny for safety
            return False
    
    def _voice_confirm(self, request: ConfirmationRequest) -> bool:
        """Voice-based confirmation"""
        if not self.voice:
            logger.warning("Voice pipeline not available, falling back to text")
            return self._text_confirm(request)
        
        # Speak the prompt
        self.voice.speak(f"{request.prompt}. Say yes to confirm or no to cancel.")
        
        # Listen for response
        max_attempts = 3
        for attempt in range(max_attempts):
            response = self.voice.listen(timeout_seconds=10)
            
            if response:
                response_lower = response.lower().strip()
                
                # Check for affirmative
                if any(word in response_lower for word in ["yes", "confirm", "approve", "do it", "proceed"]):
                    logger.info("Confirmation: APPROVED (voice)")
                    return True
                
                # Check for negative
                if any(word in response_lower for word in ["no", "cancel", "deny", "stop", "abort"]):
                    logger.info("Confirmation: DENIED (voice)")
                    return False
                
                # Unclear response
                self.voice.speak("I didn't understand. Please say yes or no.")
            else:
                self.voice.speak("No response detected. Please say yes or no.")
        
        # Timeout after max attempts - default to deny
        logger.warning("Confirmation timeout - denying request")
        self.voice.speak("Confirmation timeout. Request cancelled.")
        return False
    
    def _text_confirm(self, request: ConfirmationRequest) -> bool:
        """Text-based confirmation"""
        print("\n" + "=" * 60)
        print("CONFIRMATION REQUIRED")
        print("=" * 60)
        print(f"Prompt: {request.prompt}")
        print(f"Command: {request.command}")
        print(f"Risk Level: {request.risk_level.upper()}")
        print("=" * 60)
        
        max_attempts = 3
        for attempt in range(max_attempts):
            response = input("Confirm? (yes/no): ").strip().lower()
            
            if response in ["yes", "y", "confirm", "approve"]:
                logger.info("Confirmation: APPROVED (text)")
                return True
            elif response in ["no", "n", "cancel", "deny"]:
                logger.info("Confirmation: DENIED (text)")
                return False
            else:
                print(f"Invalid response. Please answer yes or no. ({max_attempts - attempt - 1} attempts remaining)")
        
        logger.warning("Confirmation timeout - denying request")
        return False
    
    def _auto_approve(self, request: ConfirmationRequest) -> bool:
        """Auto-approve mode (for testing)"""
        logger.info(f"Auto-approved: {request.prompt}")
        return True
    
    def _auto_deny(self, request: ConfirmationRequest) -> bool:
        """Auto-deny mode (lockdown)"""
        logger.warning(f"Auto-denied: {request.prompt}")
        return False
    
    def set_mode(self, mode: ConfirmationMode) -> None:
        """Change confirmation mode"""
        self.mode = mode
        logger.info(f"Confirmation mode changed to: {mode.value}")
    
    def set_voice_pipeline(self, voice_pipeline) -> None:
        """Set voice pipeline for voice confirmations"""
        self.voice = voice_pipeline
        logger.info("Voice pipeline set for confirmations")
    
    def _record_confirmation(self, request: ConfirmationRequest, confirmed: bool) -> None:
        """Record confirmation in history"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request.request_id,
            "prompt": request.prompt,
            "command": request.command,
            "risk_level": request.risk_level,
            "confirmed": confirmed
        }
        
        self.history.append(event)
        
        # Keep last 100 confirmations
        if len(self.history) > 100:
            self.history = self.history[-100:]
    
    def get_history(self, limit: int = 20) -> list:
        """Get confirmation history"""
        return self.history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get confirmation statistics"""
        total = len(self.history)
        approved = sum(1 for e in self.history if e["confirmed"])
        denied = total - approved
        
        return {
            "mode": self.mode.value,
            "pending_requests": len(self.pending),
            "total_confirmations": total,
            "approved": approved,
            "denied": denied,
            "approval_rate": (approved / total * 100) if total > 0 else 0
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Text mode
    loop = ConfirmationLoop(mode=ConfirmationMode.TEXT)
    
    # Request confirmation
    confirmed = loop.request_confirmation(
        prompt="Delete all files in /tmp?",
        command="rm -rf /tmp/*",
        risk_level="high"
    )
    
    print(f"\nUser confirmed: {confirmed}")
    
    # Show stats
    print(f"\nStats: {loop.get_stats()}")
