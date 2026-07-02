# Quick Start Guide - After Bug Fixes

## Issues Resolved ✅

1. ✅ Terminal manager Eel callback error
2. ✅ Minikernel log file permission error

## Installation

### 1. Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install DeepGram SDK (optional, for voice agent)
pip install deepgram-sdk
```

### 2. Configure DeepGram (Optional)

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your DeepGram API key
# DEEPGRAM_API_KEY=your_key_here
```

### 3. Start the Application

```bash
python kernel/onboarding_gui.py
```

## What to Expect

### On First Run

✅ **No permission errors** - Logs will be written to `~/.portaios/minikernel.log`  
✅ **No terminal manager errors** - Graceful fallback if callback not available  
⚠️ **DeepGram warning** - Expected if SDK not installed or API key not set  

### DeepGram Integration

If you installed the DeepGram SDK and set the API key:

1. **Look for the DeepGram panel** (bottom-right corner)
2. **Status should show**: "Ready" or "Available"
3. **Click "Enable Agent"** to start the voice agent
4. **Test it**: Click "Test" button and enter a message

### Fallback Behavior

If DeepGram is not available:
- ✅ Application still works
- ✅ Voice input falls back to browser-based speech recognition
- ✅ All features remain functional

## Troubleshooting

### Missing Dependencies

If you see `ModuleNotFoundError`:
```bash
pip install -r requirements.txt
```

### DeepGram Not Working

Check these in order:
1. SDK installed: `pip list | grep deepgram`
2. API key set: `echo $DEEPGRAM_API_KEY`
3. Check browser console for errors

### Log Files

Check log files for detailed error messages:
```bash
# Primary location
cat ~/.portaios/minikernel.log

# Fallback location
cat /tmp/minikernel.log
```

## Testing DeepGram Integration

### 1. Check Status
```bash
# In browser console:
window.voiceBridge.getStatus()
```

### 2. Enable Agent
```bash
# In browser console:
await window.deepgramAgent.enable()
```

### 3. Test Voice
- Click "Test" button in DeepGram panel
- Enter: "Hello, how are you?"
- Agent should respond

## Next Steps

1. ✅ Application starts without errors
2. 🎤 Configure DeepGram for voice agent
3. 🎨 Customize the UI and settings
4. 📖 Read the integration guides in `docs/`

## Documentation

- `README_DEEPGRAM.md` - DeepGram integration overview
- `docs/DEEPGRAM_INTEGRATION_GUIDE.md` - Complete setup guide
- `docs/DEEPGRAM_WEB_INTEGRATION.md` - Web frontend guide
- `WEB_INTEGRATION_SUMMARY.md` - Technical summary
- `BUGFIXES_SUMMARY.md` - Details on fixes applied

---

**You're all set!** The application should now start cleanly. 🚀
