# DeepGram Web Frontend Integration Guide

This guide explains the web frontend integration for the DeepGram voice agent in PortAIOS.

## Overview

The web frontend integration provides:
- **UI Control Panel**: Visual controls for enabling/disabling the DeepGram agent
- **Status Indicators**: Real-time status updates in the existing UI
- **Mode Switching**: Seamless switching between DeepGram and browser-based voice
- **Visual Feedback**: Notifications and animations for voice events

## Components

### 1. DeepGram Voice Agent UI (`deepgram-voice-agent.js`)

The main UI component that provides:
- Control panel with enable/disable buttons
- Real-time status display
- Test functionality
- Automatic status monitoring

**Usage:**
```javascript
// Auto-initialized on page load
// Access via:
window.deepgramAgent

// Or create manually:
const agent = new DeepGramVoiceAgent({
  autoEnable: false,
  showUI: true,
  onResponse: (text) => console.log('Agent:', text),
  onError: (err) => console.error(err)
});
await agent.init();
```

### 2. Voice Integration Bridge (`deepgram-voice-integration.js`)

Manages switching between DeepGram and browser voice modes:
- Automatic mode detection
- Seamless mode switching
- Unified API for both modes
- Integration with existing voice-input.js

**Usage:**
```javascript
// Access global bridge instance
window.voiceBridge

// Switch modes
await window.toggleVoiceMode();

// Get current mode
const mode = window.voiceBridge.getMode(); // 'deepgram' or 'browser'

// Send text
await window.voiceBridge.sendText('Hello!');
```

### 3. Status Indicator (`deepgram-status-indicator.js`)

Updates existing UI elements with DeepGram status:
- Voice status badge
- Mic status indicator
- Speech status display
- Animated voice bars
- Toast notifications

**Usage:**
```javascript
// Auto-initialized, access via:
window.deepgramStatusIndicator

// Show notification
window.deepgramStatusIndicator.showNotification('Message', 'success');
```

## UI Elements Updated

The integration updates these existing HTML elements:

| Element ID | Description | Updated With |
|------------|-------------|--------------|
| `voice-status` | Voice system status | DeepGram/Browser mode |
| `mic-status` | Microphone source | DeepGram/Browser |
| `speech-status` | Speech recognition status | Listening/Ready |
| `voice-bars` | Audio level bars | Animated when active |
| `avatar-status-text` | Avatar guide status | Mode and state |

## Control Panel

The DeepGram control panel appears in the bottom-right corner and includes:

### Status Information
- **Status**: Current agent state (Available/Running/Not configured)
- **Mode**: DeepGram Unified Agent or Fallback
- **Agent**: Listening or Stopped

### Controls
- **Enable Agent**: Start the DeepGram voice agent
- **Disable Agent**: Stop the agent
- **Test**: Send a test message to the agent

### Visual States
- **Green dot + "Active"**: Agent is running
- **Blue dot + "Ready"**: Agent available but not running
- **Red dot + "Unavailable"**: DeepGram not configured

## API Endpoints (Eel)

The following Eel endpoints are available for JavaScript:

```javascript
// Get DeepGram status
const status = await eel.get_deepgram_status()();
// Returns: { available, enabled, fallback_mode, agent_running }

// Enable DeepGram agent
const result = await eel.enable_deepgram_voice()();

// Disable DeepGram agent
const result = await eel.disable_deepgram_voice()();

// Send text to agent (for testing)
await eel.send_text_to_deepgram('Hello, how are you?')();
```

## Integration Flow

```
User Interaction
    ↓
Voice Bridge (deepgram-voice-integration.js)
    ↓
┌─────────────────┬──────────────────┐
│ DeepGram Mode   │ Browser Mode     │
├─────────────────┼──────────────────┤
│ DeepGram Agent  │ voice-input.js   │
│ (via Eel API)   │ (Web Speech API) │
└─────────────────┴──────────────────┘
    ↓
Status Indicator Updates
    ↓
UI Elements + Avatar
```

## Events

The integration dispatches custom events:

### `voiceModeChanged`
Fired when switching between DeepGram and browser modes.

```javascript
document.addEventListener('voiceModeChanged', (e) => {
  console.log('New mode:', e.detail.mode);
});
```

## Styling

The integration uses the existing AIOS styling system with:
- Holo-card design
- Glow effects
- Cyberpunk aesthetics
- Responsive animations

All styles are injected dynamically and follow the existing design language.

## Auto-Initialization

Components auto-initialize on page load:

1. **DeepGram Voice Agent**: Only on main pages (not onboarding)
2. **Voice Bridge**: Always initializes and detects best mode
3. **Status Indicator**: Always initializes

## Manual Control

### Enable DeepGram
```javascript
await window.deepgramAgent.enable();
```

### Disable DeepGram
```javascript
await window.deepgramAgent.disable();
```

### Switch to Browser Mode
```javascript
await window.voiceBridge.switchMode('browser');
```

### Switch to DeepGram Mode
```javascript
await window.voiceBridge.switchMode('deepgram');
```

### Toggle Between Modes
```javascript
await window.toggleVoiceMode();
```

## Fallback Behavior

If DeepGram is unavailable:
1. Voice bridge automatically selects browser mode
2. Status indicator shows "Fallback Mode"
3. Warning notice displays in control panel
4. All voice functionality continues via browser

## Testing

### Test DeepGram Agent
Click the "Test" button in the control panel, or:

```javascript
await window.deepgramAgent.testAgent();
```

### Check Status
```javascript
const status = window.voiceBridge.getStatus();
console.log(status);
// {
//   mode: 'deepgram',
//   deepgramAvailable: true,
//   deepgramEnabled: true,
//   browserActive: false
// }
```

### Monitor Status Changes
```javascript
setInterval(() => {
  const status = window.deepgramAgent.getStatus();
  console.log('DeepGram status:', status);
}, 2000);
```

## Notifications

Toast notifications appear for:
- Mode switching
- Agent enable/disable
- Errors
- Important status changes

Show custom notifications:
```javascript
window.deepgramStatusIndicator.showNotification(
  'Custom message',
  'success' // or 'info', 'warning', 'error'
);
```

## Integration with Avatar

The voice bridge automatically integrates with the avatar system:

```javascript
// Avatar speaks agent responses
if (window.AIOS?.avatar) {
  window.AIOS.avatar.speak(response);
}
```

## Troubleshooting

### DeepGram Panel Not Showing
- Check browser console for errors
- Verify `deepgram-voice-agent.js` is loaded
- Ensure Eel is available

### Status Not Updating
- Check `deepgram-status-indicator.js` is loaded
- Verify Eel connection
- Check browser console for errors

### Mode Switching Not Working
- Verify both DeepGram SDK and browser support
- Check API key is set
- Review browser console logs

### Visual Indicators Not Updating
- Ensure HTML elements exist (check element IDs)
- Verify status indicator is initialized
- Check for JavaScript errors

## Best Practices

1. **Prefer DeepGram**: Set `preferDeepGram: true` for better quality
2. **Show UI**: Keep `showUI: true` for user control
3. **Monitor Status**: Use status indicators for visibility
4. **Handle Errors**: Implement error callbacks
5. **Test Thoroughly**: Use test button before production

## Files Added

- `web/deepgram-voice-agent.js` - Main UI component
- `web/deepgram-voice-integration.js` - Voice mode bridge
- `web/deepgram-status-indicator.js` - Status updates

## Files Modified

- `web/index.html` - Added script references
- `kernel/onboarding_gui.py` - Added Eel API setup

## Next Steps

1. Customize the control panel position/style
2. Add keyboard shortcuts for mode switching
3. Implement voice activity detection visualization
4. Add conversation history display
5. Create user preferences for default mode

## Related Documentation

- [DeepGram Integration Guide](DEEPGRAM_INTEGRATION_GUIDE.md)
- [Voice Commands Reference](VOICE_COMMANDS_QUICK_REFERENCE.md)
- [Avatar Integration](AVATAR_INTEGRATION_README.md)
