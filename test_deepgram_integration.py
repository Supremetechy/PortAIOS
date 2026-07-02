#!/usr/bin/env python3
"""
Test script for DeepGram voice agent integration.

This script tests the DeepGram integration and demonstrates fallback behavior.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_deepgram_availability():
    """Test if DeepGram is available and configured."""
    print("=" * 60)
    print("DeepGram Availability Test")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if api_key:
        print("✅ DEEPGRAM_API_KEY is set")
        print(f"   Key: {api_key[:8]}...{api_key[-4:]}")
    else:
        print("❌ DEEPGRAM_API_KEY is not set")
        print("   Set it in .env file or environment")
    
    # Check SDK installation
    try:
        import deepgram
        print(f"✅ DeepGram SDK installed (version: {deepgram.__version__})")
    except ImportError:
        print("❌ DeepGram SDK not installed")
        print("   Install with: pip install deepgram-sdk")
        return False
    
    # Check backend module
    try:
        from kernel.audio.deepgram_backend import DEEPGRAM_AVAILABLE, get_deepgram_agent
        if DEEPGRAM_AVAILABLE:
            print("✅ DeepGram backend module available")
        else:
            print("❌ DeepGram backend module not available")
            return False
    except ImportError as e:
        print(f"❌ Failed to import DeepGram backend: {e}")
        return False
    
    # Check integration module
    try:
        from kernel.deepgram_voice_integration import get_deepgram_integration
        integration = get_deepgram_integration()
        if integration.is_available():
            print("✅ DeepGram integration ready")
            return True
        else:
            print("⚠️  DeepGram integration not available (likely missing API key)")
            return False
    except Exception as e:
        print(f"❌ Failed to initialize DeepGram integration: {e}")
        return False


def test_tts_backend():
    """Test TTS backend detection."""
    print("\n" + "=" * 60)
    print("TTS Backend Detection Test")
    print("=" * 60)
    
    try:
        from kernel.audio.tts import get_tts_engine
        
        # Auto-detect
        print("\nAuto-detecting TTS backend...")
        engine = get_tts_engine()
        print(f"✅ TTS Engine: {engine.name}")
        
        # Test DeepGram specifically
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if api_key:
            print("\nTesting DeepGram TTS backend...")
            try:
                dg_engine = get_tts_engine(prefer="deepgram")
                print(f"✅ DeepGram TTS available: {dg_engine.name}")
            except Exception as e:
                print(f"⚠️  DeepGram TTS not available: {e}")
        
        return True
    except Exception as e:
        print(f"❌ TTS test failed: {e}")
        return False


def test_voice_assistant():
    """Test voice assistant with DeepGram integration."""
    print("\n" + "=" * 60)
    print("Voice Assistant Integration Test")
    print("=" * 60)
    
    try:
        from kernel.voice_assistant import VoiceOnboardingAssistant, DEEPGRAM_AVAILABLE
        
        print(f"\nDeepGram available in voice_assistant: {DEEPGRAM_AVAILABLE}")
        
        # Test with DeepGram enabled
        print("\nCreating assistant with DeepGram enabled...")
        assistant = VoiceOnboardingAssistant(use_deepgram=True)
        
        if hasattr(assistant, '_use_deepgram') and assistant._use_deepgram:
            print("✅ Assistant using DeepGram")
        else:
            print("⚠️  Assistant using fallback TTS/STT")
            if assistant.tts:
                print(f"   TTS Backend: {assistant.tts.name if hasattr(assistant.tts, 'name') else 'unknown'}")
            if assistant.stt:
                print(f"   STT Backend: {assistant.stt.__class__.__name__}")
        
        # Test with DeepGram disabled
        print("\nCreating assistant with DeepGram disabled...")
        assistant_fallback = VoiceOnboardingAssistant(use_deepgram=False)
        
        if assistant_fallback.tts:
            print(f"✅ Fallback TTS: {assistant_fallback.tts.name if hasattr(assistant_fallback.tts, 'name') else 'unknown'}")
        if assistant_fallback.stt:
            print(f"✅ Fallback STT: {assistant_fallback.stt.__class__.__name__}")
        
        return True
    except Exception as e:
        print(f"❌ Voice assistant test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_loading():
    """Test configuration file loading."""
    print("\n" + "=" * 60)
    print("Configuration Loading Test")
    print("=" * 60)
    
    config_path = project_root / "config.json"
    
    if not config_path.exists():
        print(f"⚠️  Config file not found: {config_path}")
        return False
    
    try:
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("✅ Config file loaded successfully")
        
        # Check agent configuration
        if "agent" in config:
            agent_config = config["agent"]
            
            # Listen
            if "listen" in agent_config:
                listen = agent_config["listen"]["provider"]
                print(f"✅ STT Model: {listen.get('type')} / {listen.get('model')}")
            
            # Think
            if "think" in agent_config:
                think = agent_config["think"]["provider"]
                print(f"✅ LLM Model: {think.get('type')} / {think.get('model')}")
            
            # Speak
            if "speak" in agent_config:
                speak = agent_config["speak"]["provider"]
                print(f"✅ TTS Model: {speak.get('type')} / {speak.get('model')}")
        
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PortAIOS DeepGram Integration Test Suite")
    print("=" * 60)
    print()
    
    results = {
        "DeepGram Availability": test_deepgram_availability(),
        "Configuration Loading": test_config_loading(),
        "TTS Backend": test_tts_backend(),
        "Voice Assistant": test_voice_assistant(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("⚠️  Some tests failed. See details above.")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
