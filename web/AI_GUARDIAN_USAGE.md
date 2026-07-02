# AI Guardian 3D Interactive Avatar

## Overview

The AI Guardian is a fully interactive 3D holographic avatar that serves as the visual interface for PortAIOS. It features:

- **Holographic Visual Style** - Matches the aesthetic of the original AI-Guardian.jpg image
- **Lip-Sync Animation** - Real-time viseme morphing synchronized with speech
- **Hand Gestures** - Dynamic poses (stop, wave, point, thinking)
- **Facial Expressions** - Emotions (smile, thinking, surprise, neutral)
- **Audio-Reactive Effects** - Glowing and pulsing based on voice volume
- **Particle System** - Environmental particles for enhanced visual appeal

## Quick Start

### JavaScript Usage

```javascript
import { AIGuardianController } from './ai-guardian-integration.js';

// Initialize the guardian
const guardian = new AIGuardianController(container, {
    modelUrl: '/models/ai_guardian.glb',
    autoRotate: true,
    enableParticles: true
});

await guardian.init();

// Make the guardian speak with automatic gestures and emotions
await guardian.speak("Hello! I am your AI Guardian.", {
    emotion: 'happy',
    gesture: 'wave'
});

// Set activity state
guardian.setActivity('thinking');  // idle, listening, thinking, speaking

// Set emotion
guardian.setEmotion('surprised');  // neutral, happy, thinking, surprised

// Set gesture
guardian.setGesture('stop');  // none, stop, wave, point, thinking

// Stop speaking
guardian.stop();
```

### Global Access

The guardian is automatically available globally after initialization:

```javascript
// Available on window.AIOS.guardian
window.AIOS.guardian.speak("Welcome to PortAIOS!");

// Also aliased as window.AIOS.avatar for backward compatibility
window.AIOS.avatar.setEmotion('happy');
```

## Features

### 1. Lip-Sync Visemes

The guardian supports 7 viseme morph targets for realistic lip-sync:

- `viseme_aa` - Open mouth (ah, a sounds)
- `viseme_o` - Round lips (o, oh sounds)
- `viseme_e` - Wide smile (e, eh sounds)
- `viseme_i` - Narrow smile (i, ee sounds)
- `viseme_u` - Pucker (u, oo sounds)
- `viseme_m` - Lips closed (m, b, p sounds)
- `viseme_f` - Lower lip to teeth (f, v sounds)

Visemes are automatically synchronized when using the backend TTS with viseme support.

### 2. Hand Gestures

Four gesture poses are available:

- **stop** - Right hand raised, palm forward (used for alerts, warnings)
- **wave** - Right hand up in greeting position (used for welcomes)
- **point** - Right hand forward, finger extended (used for directions)
- **thinking** - Right hand to chin (used for processing, analyzing)

Gestures are auto-detected from speech text or can be set manually.

### 3. Facial Expressions

Three expression morph targets:

- **smile** - Happy, positive expression
- **thinking** - Slight frown, contemplative
- **surprise** - Raised eyebrows, open mouth

Expressions blend at 70% with other animations.

### 4. Activity States

Activity affects the holographic glow intensity:

- **idle** (0.3) - Low energy, gentle glow
- **listening** (0.5) - Medium energy
- **thinking** (0.7) - High energy, more pulsing
- **speaking** (1.0) - Maximum energy, full effects

## Backend Integration

### Python TTS with Visemes

The guardian integrates with the Piper viseme server:

```python
from kernel.viseme_integration import setup_viseme_integration

# In your Eel setup
setup_viseme_integration(eel)

# The frontend will receive viseme data automatically
```

### Viseme Data Format

```json
{
  "phonemes": [
    {"phoneme": "h", "start": 0.0, "end": 0.1},
    {"phoneme": "e", "start": 0.1, "end": 0.2},
    {"phoneme": "l", "start": 0.2, "end": 0.3}
  ],
  "audio": "base64_encoded_wav_data"
}
```

## Auto-Detection

The guardian automatically detects emotions and gestures from speech text:

### Gesture Keywords

- **stop**: "stop", "halt", "wait", "pause"
- **wave**: "hello", "hi", "greet", "welcome"
- **point**: "look", "see", "there", "this", "that"
- **thinking**: "think", "consider", "analyze", "process", "hmm"

### Emotion Keywords

- **happy**: "great", "excellent", "perfect", "wonderful", "success"
- **thinking**: "analyzing", "processing", "calculating", "considering"
- **surprised**: "wow", "amazing", "incredible", "unexpected"

Example:
```javascript
// This will automatically use 'wave' gesture and 'happy' emotion
guardian.speak("Hello! Welcome to the system!");

// This will use 'thinking' gesture and 'thinking' emotion
guardian.speak("Let me analyze that for you...");
```

## Customization

### Colors

```javascript
const guardian = new AIGuardianController(container, {
    colorPrimary: new THREE.Color(0x00ffff),    // Cyan
    colorSecondary: new THREE.Color(0x0088ff)   // Blue
});
```

### Performance

```javascript
const guardian = new AIGuardianController(container, {
    autoRotate: false,         // Disable auto-rotation
    enableParticles: false     // Disable particle system for better performance
});
```

## Model Generation

To regenerate the 3D model with different parameters:

```bash
cd kernel
python3 ai_guardian_3d_generator.py
```

This creates `/models/ai_guardian.glb` with all morph targets.

## Troubleshooting

### Guardian Not Loading

1. Check browser console for errors
2. Verify `/models/ai_guardian.glb` exists
3. Check Three.js CDN availability
4. Fall back to placeholder mode

### No Lip-Sync

1. Verify viseme WebSocket connection (ws://localhost:8766)
2. Check Piper viseme server is running
3. Verify phoneme data is being received
4. Use Web Speech API fallback if needed

### Performance Issues

1. Disable particles: `enableParticles: false`
2. Disable auto-rotate: `autoRotate: false`
3. Reduce particle count in `ai-guardian-3d.js`
4. Use lower device pixel ratio

## API Reference

### AIGuardianController

**Constructor Options:**
- `modelUrl` - Path to GLB file (default: '/models/ai_guardian.glb')
- `colorPrimary` - Primary glow color (default: cyan)
- `colorSecondary` - Secondary glow color (default: blue)
- `autoRotate` - Enable idle rotation (default: true)
- `enableParticles` - Enable particle system (default: true)
- `visemeWebSocket` - WebSocket URL for visemes (default: 'ws://localhost:8766')

**Methods:**

- `async init()` - Initialize the guardian
- `async speak(text, options)` - Make guardian speak
- `stop()` - Stop speaking and reset
- `setActivity(state)` - Set activity level
- `setEmotion(emotion)` - Set facial expression
- `setGesture(gesture)` - Set hand gesture
- `destroy()` - Cleanup and remove

### AIGuardian3D (Low-level)

Direct 3D renderer control:

- `setViseme(viseme, weight)` - Set specific viseme morph
- `setVolume(volume)` - Set audio-reactive volume (0-1)
- All methods from AIGuardianController

## Examples

### Simple Greeting

```javascript
const guardian = await initAIGuardian();
guardian.speak("Welcome to PortAIOS! I'm your AI Guardian.");
```

### Contextual Interaction

```javascript
// Processing state
guardian.setActivity('thinking');
guardian.setEmotion('thinking');
await processData();

// Success state
guardian.setActivity('speaking');
guardian.setEmotion('happy');
guardian.speak("Analysis complete! Everything looks great.");
```

### Manual Viseme Control

```javascript
// For custom lip-sync without backend
guardian.setViseme('viseme_aa', 1.0);  // Open mouth
setTimeout(() => guardian.setViseme('viseme_m', 1.0), 200);  // Close
```

## Files

- `kernel/ai_guardian_3d_generator.py` - Model generator with morph targets
- `web/ai-guardian-3d.js` - Low-level 3D renderer with shaders
- `web/ai-guardian-integration.js` - High-level controller with voice integration
- `web/onboarding-guardian.js` - Onboarding page integration
- `models/ai_guardian.glb` - Generated 3D model with 14 morph targets

## Credits

Built for PortAIOS using:
- Three.js for 3D rendering
- Trimesh for model generation
- Custom GLSL shaders for holographic effects
- Piper TTS for viseme generation
