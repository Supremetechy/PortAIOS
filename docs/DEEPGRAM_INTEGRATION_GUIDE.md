# DeepGram Voice Agent Integration Guide

This guide explains how to use the DeepGram voice agent integration in PortAIOS.

## Overview

The DeepGram voice agent provides a unified voice interaction pipeline that combines:
- **STT (Speech-to-Text)**: DeepGram Nova or Flux models
- **LLM (Think)**: OpenAI, Anthropic, or Google models  
- **TTS (Text-to-Speech)**: DeepGram Aura voices

This replaces the traditional separate TTS/STT backends with a single conversational agent.

## Setup

### 1. Install Dependencies

The DeepGram SDK is included in the requirements:

```bash
pip install -r requirements.txt
```

### 2. Get DeepGram API Key

1. Sign up at [https://console.deepgram.com/](https://console.deepgram.com/)
2. Create a new API key
3. Copy the API key

### 3. Configure Environment

Create a `.env` file in the project root (or copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your DeepGram API key:

```bash
DEEPGRAM_API_KEY=your_deepgram_api_key_here
```

### 4. Configure Voice Agent Settings

Edit `config.json` to customize the voice agent behavior:

```json
{
  "audio": {
    "input": {
      "encoding": "linear16",
      "sample_rate": 48000
    },
    "output": {
      "encoding": "linear16",
      "sample_rate": 24000,
      "container": "none"
    }
  },
  "agent": {
    "listen": {
      "provider": {
        "type": "deepgram",
        "model": "nova-3"
      }
    },
    "think": {
      "provider": {
        "type": "google",
        "model": "gemini-2.0-flash-exp"
      },
      "prompt": "You are the AI agent for an AI Operating System..."
    },
    "speak": {
      "provider": {
        "type": "deepgram",
        "model": "aura-2-odysseus-en"
      }
    }
  }
}
```

## Configuration Options

### STT (Listen) Models

Available DeepGram STT models:
- `nova-3` - Latest, most accurate model
- `nova-2` - Previous generation
- `flux-general-en` - Fast, general-purpose

### LLM (Think) Providers

Configure the "think" provider:

**OpenAI:**
```json
"think": {
  "provider": {
    "type": "open_ai",
    "model": "gpt-4o-mini"
  }
}
```
Requires: `OPENAI_API_KEY` environment variable

**Anthropic:**
```json
"think": {
  "provider": {
    "type": "anthropic",
    "model": "claude-3-5-sonnet-20241022"
  }
}
```
Requires: `ANTHROPIC_API_KEY` environment variable

**Google:**
```json
"think": {
  "provider": {
    "type": "google",
    "model": "gemini-2.0-flash-exp"
  }
}
```
Requires: `GOOGLE_API_KEY` environment variable

### TTS (Speak) Voices

Available DeepGram Aura voices:
- `aura-2-odysseus-en` - Male, warm and authoritative
- `aura-2-asteria-en` - Female, clear and friendly
- `aura-2-luna-en` - Female, calm and soothing
- `aura-2-stella-en` - Female, bright and energetic
- `aura-2-athena-en` - Female, professional
- `aura-2-hera-en` - Female, confident
- `aura-2-orion-en` - Male, deep and resonant
- `aura-2-arcas-en` - Male, youthful
- `aura-2-perseus-en` - Male, clear and articulate
- `aura-2-angus-en` - Male, Irish accent
- `aura-2-orpheus-en` - Male, theatrical
- `aura-2-helios-en` - Male, warm

## Usage

### Programmatic Usage

```python
from kernel.deepgram_voice_integration import get_deepgram_integration

# Get the integration instance
integration = get_deepgram_integration()

# Check if available
if integration.is_available():
    # Enable the agent
    integration.enable()
    
    # The agent is now listening for voice input
    # and will respond automatically
    
    # Optional: Send text for testing
    integration.send_text("Hello, how are you?")
    
    # Disable when done
    integration.disable()
else:
    print("DeepGram not available - check API key")
```

### Context Manager Usage

```python
from kernel.deepgram_voice_integration import get_deepgram_integration

integration = get_deepgram_integration()

with integration:
    # Agent is enabled within this block
    print("Voice agent is active")
    # ... your code here ...
# Agent is automatically disabled when exiting
```

### Voice Assistant Integration

The `VoiceOnboardingAssistant` now uses DeepGram by default:

```python
from kernel.voice_assistant import VoiceOnboardingAssistant

# DeepGram is used automatically if available
assistant = VoiceOnboardingAssistant()

# Force fallback to traditional TTS/STT
assistant = VoiceOnboardingAssistant(use_deepgram=False)
```

## Fallback Behavior

If DeepGram is not available (missing API key or SDK), the system automatically falls back to:

1. **Piper TTS** (if available) - Local neural TTS
2. **Whisper STT** (if available) - Local speech recognition
3. **Other local TTS/STT backends** - System say, espeak, etc.

This ensures the voice system continues to work even without DeepGram.

## Priority Order

When auto-detecting TTS backends, the priority is:

1. **DeepGram** (if API key is set)
2. Piper TTS
3. Coqui TTS
4. espeak-ng
5. macOS say
6. Silent (fallback)

## Troubleshooting

### DeepGram Not Working

1. **Check API Key**: Ensure `DEEPGRAM_API_KEY` is set in `.env`
   ```bash
   echo $DEEPGRAM_API_KEY
   ```

2. **Check SDK Installation**:
   ```bash
   python -c "import deepgram; print(deepgram.__version__)"
   ```

3. **Check Logs**: Look for DeepGram messages in console output

### Audio Issues

- Check microphone permissions
- Verify sample rate settings match your hardware
- Test with the DeepGram playground first

### API Key Issues

- Ensure the API key has sufficient credits
- Check for rate limiting in DeepGram console
- Verify the API key is active (not revoked)

## Advanced Configuration

### Custom System Prompt

Edit the `prompt` field in `config.json`:

```json
"think": {
  "provider": {
    "type": "google",
    "model": "gemini-2.0-flash-exp"
  },
  "prompt": "You are a helpful AI assistant specialized in system administration. Be concise and technical."
}
```

### Audio Settings

Adjust sample rates for your hardware:

```json
"audio": {
  "input": {
    "encoding": "linear16",
    "sample_rate": 16000  // Lower for slower systems
  },
  "output": {
    "encoding": "linear16",
    "sample_rate": 16000  // Lower for slower systems
  }
}
```

## Benefits of DeepGram Agent

1. **Unified Pipeline**: Single WebSocket connection for entire conversation
2. **Low Latency**: Optimized for real-time interaction
3. **Natural Conversations**: Better context handling than separate STT/TTS
4. **Easy Configuration**: Single config file for all voice settings
5. **Automatic Fallback**: Gracefully degrades to local TTS/STT if unavailable

## Next Steps

- Customize the system prompt for your use case
- Try different voice models to find your preference
- Integrate with your application using the provided APIs
- Set up callbacks for custom handling of responses

## Related Documentation

- [Voice Commands Guide](VOICE_COMMANDS_QUICK_REFERENCE.md)
- [Multimodal Integration](MULTIMODAL_SYSTEM_COMPLETE.md)
- [Avatar Integration](AVATAR_INTEGRATION_README.md)
