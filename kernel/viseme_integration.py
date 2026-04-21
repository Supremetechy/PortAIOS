#!/usr/bin/env python3
"""
Viseme Integration for AIOS Onboarding
Bridges PiperWebSocketBackend with Eel frontend for real-time lip-sync
"""

import logging
import base64
from typing import Optional, Callable, List, Dict, Any
from threading import Lock

logger = logging.getLogger("VisemeIntegration")


class VisemeStreamBridge:
    """
    Bridge between Piper TTS backend and Eel frontend
    Streams phoneme data in real-time for avatar lip-sync
    """
    
    def __init__(self):
        self.eel_callback: Optional[Callable] = None
        self.lock = Lock()
        self.current_utterance_id = 0
        
    def set_eel_callback(self, callback: Callable):
        """Set the Eel callback function for sending phoneme data to frontend"""
        with self.lock:
            self.eel_callback = callback
            logger.info("Eel callback registered for viseme streaming")
    
    def on_visemes_callback(self, phoneme_timeline: List[Dict], wav_bytes: bytes):
        """
        Called by PiperWebSocketBackend when TTS generates phoneme data
        
        Args:
            phoneme_timeline: List of {"p": phoneme, "t": time, "d": duration}
            wav_bytes: Raw WAV audio data
        """
        with self.lock:
            if not self.eel_callback:
                logger.warning("No Eel callback registered, phoneme data dropped")
                return
            
            self.current_utterance_id += 1
            
            # Encode audio as base64
            audio_b64 = base64.b64encode(wav_bytes).decode('utf-8')
            
            # Prepare data for frontend
            payload = {
                'utterance_id': self.current_utterance_id,
                'audio': audio_b64,
                'phonemes': phoneme_timeline,
                'sample_rate': 22050  # Piper default
            }
            
            logger.info(f"Streaming {len(phoneme_timeline)} phonemes to frontend (utterance {self.current_utterance_id})")
            
            try:
                # Send to frontend via Eel
                self.eel_callback(payload)
            except Exception as e:
                logger.error(f"Failed to send phoneme data to frontend: {e}")
    
    def get_callback(self):
        """Get the callback function to pass to PiperWebSocketBackend"""
        return self.on_visemes_callback


# Global instance
_viseme_bridge = VisemeStreamBridge()


def get_viseme_bridge() -> VisemeStreamBridge:
    """Get the global viseme bridge instance"""
    return _viseme_bridge


def setup_viseme_integration(eel_module):
    """
    Setup Eel-exposed functions for viseme/phoneme streaming
    
    Call this from kernel/onboarding_gui.py during Eel setup
    """
    
    bridge = get_viseme_bridge()
    
    @eel_module.expose
    def register_viseme_listener():
        """Frontend calls this to start receiving viseme data"""
        logger.info("Frontend registered for viseme streaming")
        
        # The actual data is pushed via push_viseme_data
        return {'status': 'ok', 'message': 'Listening for visemes'}
    
    # Create a function that Eel can call to push data to frontend
    def push_viseme_data(payload: Dict[str, Any]):
        """Push phoneme/audio data to frontend"""
        try:
            eel_module.receive_viseme_data(payload)
        except Exception as e:
            logger.error(f"Error pushing viseme data: {e}")
    
    # Register the push function with the bridge
    bridge.set_eel_callback(push_viseme_data)
    
    logger.info("Viseme integration setup complete")
    
    return bridge


def create_piper_backend_with_visemes(url: str = "ws://localhost:8766"):
    """
    Create a PiperWebSocketBackend with viseme callback integrated
    
    Args:
        url: WebSocket URL for piper_viseme_server.py
        
    Returns:
        PiperWebSocketBackend instance
    """
    try:
        from kernel.voice_assistant import PiperWebSocketBackend
        
        bridge = get_viseme_bridge()
        
        backend = PiperWebSocketBackend(
            url=url,
            on_visemes=bridge.get_callback()
        )
        
        logger.info(f"Created Piper backend with viseme streaming to {url}")
        return backend
        
    except Exception as e:
        logger.error(f"Failed to create Piper backend: {e}")
        raise


# Phoneme to viseme mapping (IPA to mouth shapes)
PHONEME_TO_VISEME = {
    # Bilabial (lips together)
    'p': 'P', 'b': 'P', 'm': 'P',
    
    # Labiodental (teeth on lip)
    'f': 'F', 'v': 'F',
    
    # Dental/Alveolar
    'θ': 'TH', 'ð': 'TH',  # "th"
    't': 'T', 'd': 'T', 's': 'S', 'z': 'S',
    'n': 'T', 'l': 'T',
    
    # Postalveolar
    'ʃ': 'CH', 'ʒ': 'CH',  # "sh", "zh"
    'tʃ': 'CH', 'dʒ': 'CH',  # "ch", "j"
    'r': 'R',
    
    # Velar
    'k': 'K', 'g': 'K', 'ŋ': 'K',  # "ng"
    
    # Vowels - open mouth
    'a': 'AA', 'ɑ': 'AA', 'æ': 'AA',  # "ah", "a"
    'e': 'E', 'ɛ': 'E', 'ə': 'E',  # "eh", schwa
    'i': 'I', 'ɪ': 'I',  # "ee", "ih"
    'o': 'O', 'ɔ': 'O', 'ɒ': 'O',  # "oh", "aw"
    'u': 'U', 'ʊ': 'U',  # "oo", "uh"
    
    # Diphthongs
    'aɪ': 'AI', 'aʊ': 'AA', 'ɔɪ': 'O',
    'eɪ': 'E', 'oʊ': 'O',
    
    # Glottal/silence
    'h': 'REST', ' ': 'REST', '_': 'REST'
}


def phoneme_to_viseme(phoneme: str) -> str:
    """
    Convert IPA phoneme to viseme (mouth shape) code
    
    Args:
        phoneme: IPA phoneme string
        
    Returns:
        Viseme code (e.g., 'P', 'F', 'AA', etc.)
    """
    return PHONEME_TO_VISEME.get(phoneme, 'REST')


def enhance_timeline_with_visemes(phoneme_timeline: List[Dict]) -> List[Dict]:
    """
    Add viseme codes to phoneme timeline
    
    Args:
        phoneme_timeline: List of {"p": phoneme, "t": time, "d": duration}
        
    Returns:
        Enhanced timeline with viseme codes added
    """
    enhanced = []
    
    for item in phoneme_timeline:
        phoneme = item['p']
        viseme = phoneme_to_viseme(phoneme)
        
        enhanced.append({
            **item,
            'v': viseme  # Add viseme code
        })
    
    return enhanced


if __name__ == "__main__":
    # Test phoneme to viseme mapping
    print("=== Phoneme to Viseme Mapping Test ===\n")
    
    test_phonemes = ['p', 'b', 'm', 'f', 'v', 't', 'd', 's', 'a', 'i', 'o', 'u']
    
    for phoneme in test_phonemes:
        viseme = phoneme_to_viseme(phoneme)
        print(f"Phoneme '{phoneme}' → Viseme '{viseme}'")
    
    print("\n=== Timeline Enhancement Test ===\n")
    
    test_timeline = [
        {'p': 'h', 't': 0.0, 'd': 0.04},
        {'p': 'ɛ', 't': 0.04, 'd': 0.08},
        {'p': 'l', 't': 0.12, 'd': 0.06},
        {'p': 'oʊ', 't': 0.18, 'd': 0.10},
    ]
    
    enhanced = enhance_timeline_with_visemes(test_timeline)
    
    for item in enhanced:
        print(f"Phoneme: {item['p']:4} | Time: {item['t']:.3f}s | Duration: {item['d']:.3f}s | Viseme: {item['v']}")
