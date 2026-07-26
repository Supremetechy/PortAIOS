#!/usr/bin/env python3
"""
Test script to verify .env file loading for DeepGram API key
"""

import os
import sys
from pathlib import Path

def test_env_loading():
    """Test that .env file is loaded correctly."""
    print("=" * 60)
    print("Environment Variable Loading Test")
    print("=" * 60)
    
    # Check if .env file exists
    env_path = Path('.env')
    if env_path.exists():
        print(f"✅ .env file found at: {env_path.absolute()}")
    else:
        print(f"❌ .env file not found at: {env_path.absolute()}")
        return False
    
    # Try to load with env_loader (which handles fallback)
    try:
        from kernel.env_loader import load_env_file
        print("✅ env_loader module found")
        
        # Load the .env file
        result = load_env_file(env_path)
        if result:
            print(f"✅ Loaded .env from {env_path.absolute()}")
        else:
            print(f"⚠️  .env file found but no variables loaded")
    except ImportError as e:
        print(f"❌ env_loader not available: {e}")
        return False
    
    # Check if DEEPGRAM_API_KEY is set
    api_key = os.getenv('DEEPGRAM_API_KEY')
    if api_key:
        print("✅ DEEPGRAM_API_KEY is loaded")
        print(f"   Key starts with: {api_key[:20]}...")
        print(f"   Key length: {len(api_key)} characters")
    else:
        print("❌ DEEPGRAM_API_KEY not found in environment")
        print("\nDebugging:")
        print(f"   .env file contents:")
        with open(env_path, 'r') as f:
            for line in f:
                if 'DEEPGRAM' in line and not line.strip().startswith('#'):
                    print(f"   {line.strip()}")
        return False
    
    # Test DeepGram integration loading
    print("\n" + "=" * 60)
    print("Testing DeepGram Integration Module")
    print("=" * 60)
    
    try:
        from kernel.deepgram_voice_integration import get_deepgram_integration
        print("✅ DeepGram integration module imported")
        
        # Try to get integration
        integration = get_deepgram_integration()
        print("✅ DeepGram integration instance created")
        
        # Check if available
        if integration.is_available():
            print("✅ DeepGram integration is available")
            status = integration.get_status()
            print(f"\nStatus:")
            print(f"   Available: {status['available']}")
            print(f"   Enabled: {status['enabled']}")
            print(f"   Fallback Mode: {status['fallback_mode']}")
        else:
            print("⚠️  DeepGram integration not available")
            print("   This might be due to missing DeepGram SDK")
            print("   Install with: pip install deepgram-sdk")
    except ImportError as e:
        print(f"⚠️  Could not import DeepGram integration: {e}")
    except Exception as e:
        print(f"⚠️  Error testing integration: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Environment loading test PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_env_loading()
    sys.exit(0 if success else 1)
