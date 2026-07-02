# DeepGram Voice Agent Integration

## Overview

PortAIOS now integrates with DeepGram's unified voice agent API, providing a seamless voice interaction experience with:

- **Speech-to-Text (STT)**: DeepGram Nova/Flux models for high-accuracy transcription
- **Language Model (LLM)**: OpenAI, Anthropic, or Google models for intelligent responses
- **Text-to-Speech (TTS)**: DeepGram Aura voices for natural speech synthesis

All three components work together in a single WebSocket connection for low-latency, natural conversations.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up API Key

Get your DeepGram API key from [console.deepgram.com](https://console.deepgram.com/) and add it to your environment:

```bash
# Create .env file
cp .env.example .env

# Edit .env and add your key
DEEPGRAM_API_KEY=your_key_here
```

### 3. Configure the Agent

Edit `config.json` to customize your voice agent:

```json
{
  "agent": {
    "listen": {
      "provider": {"type": "deepgram", "model": "nova-3"}
    },
    "think": {
      "provider": {"type": "google", "model": "gemini-2.0-flash-exp"},
      "prompt": "You are the AI agent for an AI Operating System..."
    },
    "speak": {
      "provider": {"type": "deepgram", "model": "aura-2-odysseus-en"}
    }
  }
}
```

### 4. Test the Integration

```bash
python test_deepgram_integration.py
```

## Architecture

### Files Created/Modified

**New Files:**
- `kernel/audio/deepgram_backend.py` - Core DeepGram voice agent implementation
- `kernel/deepgram_voice_integration.py` - High-level integration with PortAIOS
- `test_deepgram_integration.py` - Test suite
- `.env.example` - Environment variable template
- `docs/DEEPGRAM_INTEGRATION_GUIDE.md` - Detailed documentation

**Modified Files:**
- `kernel/audio/tts.py` - Added DeepGram TTS backend
- `kernel/voice_assistant.py` - Integrated DeepGram as primary voice agent
- `requirements.txt` - Added `deepgram-sdk>=3.0.0`
- `requirements-server.txt` - Documented DeepGram inclusion

### Component Hierarchy

```
DeepGramClient.py (your original SDK example)
    ↓
kernel/audio/deepgram_backend.py (unified voice agent)
    ↓
kernel/deepgram_voice_integration.py (PortAIOS integration)
    ↓
kernel/voice_assistant.py (uses DeepGram as primary)
    ↓
Your application
```

## Usage Examples

### Basic Usage

```python
from kernel.deepgram_voice_integration import get_deepgram_integration

# Get integration instance
integration = get_deepgram_integration()

# Enable the voice agent
if integration.is_available():
    integration.enable()
    # Agent is now listening and responding
    integration.disable()
```

### With Voice Assistant

```python
from kernel.voice_assistant import VoiceOnboardingAssistant

# DeepGram is used automatically if available
assistant = VoiceOnboardingAssistant()

# Force fallback to traditional TTS/STT
assistant = VoiceOnboardingAssistant(use_deepgram=False)
```

### Direct Agent Usage

```python
from kernel.audio.deepgram_backend import DeepGramVoiceAgent

def on_response(text):
    print(f"Agent: {text}")

def on_audio(audio_data):
    # Handle audio output
    pass

agent = DeepGramVoiceAgent(
    on_response=on_response,
    on_audio=on_audio
)

with agent:
    # Agent is running
    time.sleep(60)  # Listen for 60 seconds
```

## Configuration Options

### STT Models (Listen)

- `nova-3` - Latest, most accurate (recommended)
- `nova-2` - Previous generation
- `flux-general-en` - Fast general-purpose

### LLM Providers (Think)

**OpenAI:**
```json
{"type": "open_ai", "model": "gpt-4o-mini"}
```
Requires: `OPENAI_API_KEY`

**Anthropic:**
```json
{"type": "anthropic", "model": "claude-3-5-sonnet-20241022"}
```
Requires: `ANTHROPIC_API_KEY`

**Google:**
```json
{"type": "google", "model": "gemini-2.0-flash-exp"}
```
Requires: `GOOGLE_API_KEY`

### TTS Voices (Speak)

Male voices:
- `aura-2-odysseus-en` - Warm and authoritative (default)
- `aura-2-orion-en` - Deep and resonant
- `aura-2-arcas-en` - Youthful
- `aura-2-perseus-en` - Clear and articulate
- `aura-2-angus-en` - Irish accent
- `aura-2-orpheus-en` - Theatrical
- `aura-2-helios-en` - Warm

Female voices:
- `aura-2-asteria-en` - Clear and friendly
- `aura-2-luna-en` - Calm and soothing
- `aura-2-stella-en` - Bright and energetic
- `aura-2-athena-en` - Professional
- `aura-2-hera-en` - Confident

## Fallback System

The integration automatically falls back to local TTS/STT if:
- DeepGram API key is not set
- DeepGram SDK is not installed
- Network connection is unavailable
- API rate limits are reached

Fallback priority:
1. **DeepGram** (unified agent)
2. **Piper TTS** + **Whisper STT** (local ONNX models)
3. **Coqui TTS** + **Whisper STT**
4. **espeak-ng** + **SpeechRecognition**
5. **macOS say** + **SpeechRecognition**
6. **Silent** (log-only fallback)

## Testing

Run the test suite to verify integration:

```bash
python test_deepgram_integration.py
```

Expected output:
```
✅ DEEPGRAM_API_KEY is set
✅ DeepGram SDK installed
✅ DeepGram backend module available
✅ DeepGram integration ready
✅ TTS Engine: deepgram
✅ Assistant using DeepGram
✅ All tests passed!
```

## Troubleshooting

### API Key Not Found

```bash
# Check if key is set
echo $DEEPGRAM_API_KEY

# Set temporarily
export DEEPGRAM_API_KEY=your_key_here

# Or add to .env file
echo "DEEPGRAM_API_KEY=your_key_here" >> .env
```

### SDK Not Installed

```bash
pip install deepgram-sdk>=3.0.0
```

### Using Fallback Instead of DeepGram

Check the console output when creating the voice assistant:
- `🎤 Using DeepGram unified voice agent` - Working correctly
- `⚠️ DeepGram not available` - Missing API key or SDK
- No message - Check imports and integration

### Audio Issues

- Verify microphone permissions
- Check audio sample rate settings in `config.json`
- Test with DeepGram's web playground first

## Benefits

✅ **Unified Pipeline**: Single WebSocket for entire conversation flow  
✅ **Low Latency**: Optimized streaming for real-time interaction  
✅ **Natural Conversations**: Better context than separate STT/TTS  
✅ **Easy Configuration**: Single config file for all settings  
✅ **Automatic Fallback**: Gracefully degrades to local models  
✅ **Flexible LLM**: Choose OpenAI, Anthropic, or Google  
✅ **High-Quality Voices**: Premium DeepGram Aura voices  

## Next Steps

1. **Customize the System Prompt**: Edit `config.json` → `agent.think.prompt`
2. **Try Different Voices**: Test various Aura models
3. **Integrate with UI**: Use the Eel API for web frontend
4. **Add Callbacks**: Handle responses and audio in your app
5. **Monitor Usage**: Check DeepGram console for API usage

## Documentation

- [Full Integration Guide](docs/DEEPGRAM_INTEGRATION_GUIDE.md)
- [Voice Commands Reference](docs/VOICE_COMMANDS_QUICK_REFERENCE.md)
- [DeepGram API Docs](https://developers.deepgram.com/)

## Support

For issues or questions:
- Check the test suite: `python test_deepgram_integration.py`
- Review logs for error messages
- Consult the full guide: `docs/DEEPGRAM_INTEGRATION_GUIDE.md`
