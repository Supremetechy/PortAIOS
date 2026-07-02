# Avatar Creation System Guide

## Overview

The Avatar Creation System provides a visual interface for generating custom 3D avatars with full lip-sync capabilities. Users can design their avatar through an intuitive web interface and have it automatically wired to the React 3D lip-sync system.

## Features

### 🎨 Visual Avatar Designer
- **Real-time Preview**: See your avatar customization in real-time
- **Preset Library**: Quick-start templates (Neutral, Friendly, Professional, Energetic)
- **Fine-tuning Controls**: Sliders for precise customization
- **Progress Feedback**: Visual progress bar with stage updates

### 🎤 Lip-Sync Ready
All generated avatars include:
- **ARKit Blendshapes**: jawOpen, eyeBlinkLeft/Right, mouthSmile, browInnerUp
- **Oculus Visemes**: viseme_aa, viseme_E, viseme_O, viseme_PP (and more)
- **Automatic Wiring**: Generated avatars load directly in React 3D system

### ⚙️ Customization Options

#### Expression Controls
- **Smile Intensity** (0.0 - 1.0): Warmth and friendliness
- **Frown Intensity** (0.0 - 1.0): Seriousness or concern
- **Surprise Intensity** (0.0 - 1.0): Expressiveness and energy
- **Wink Intensity** (0.0 - 1.0): Playfulness

#### Physical Features
- **Head Size** (0.08 - 0.16): Avatar head radius
- **Skin Color**: Full RGB color picker
- **Lip-Sync Strength** (0.0 - 1.0): Phoneme animation intensity

## Usage

### Access the Avatar Creator

1. **From Onboarding UI**: Click "Customize Avatar" button
2. **Direct URL**: Navigate to `web/avatar-creator.html`
3. **From Main UI**: Avatar customization panel in right sidebar

### Creating an Avatar

#### Method 1: Using Presets (Quick)
```
1. Open Avatar Creator
2. Click a preset card (e.g., "Friendly")
3. Click "Generate Avatar"
4. Wait for progress completion (10-20 seconds)
5. Click "Load in 3D Viewer" to test
```

#### Method 2: Custom Design (Advanced)
```
1. Start with a preset or neutral base
2. Adjust sliders for fine-tuning:
   - Head Size: 0.12 (default)
   - Smile: 0.6 (friendly)
   - Surprise: 0.2 (slightly expressive)
   - Lip-Sync Strength: 1.0 (full animation)
3. Pick skin color with color picker
4. Click "Generate Avatar"
5. Monitor progress stages:
   - Initializing (0%)
   - Parsing parameters (10%)
   - Building base mesh (20%)
   - Creating morph targets (40%)
   - Generating GLB (60%)
   - Validating (80%)
   - Finalizing (95%)
   - Complete! (100%)
```

### Loading Generated Avatar

After generation completes:

```javascript
// Option 1: Automatic redirect
// Click "Load in 3D Viewer" button

// Option 2: Manual loading in avatar-integration.html
const modelUrl = '/models/avatar_generated.glb';
if (window.reactAvatar) {
    window.reactAvatar.loadModel(modelUrl);
}
```

## Technical Details

### Generated Avatar Specs

**File Format**: GLB (Binary glTF)
**File Size**: ~400KB
**Morph Targets**: 23 total

#### Morph Target List
1. **Expressions** (ARKit compatible):
   - Smile, mouthSmileLeft, mouthSmileRight
   - Frown
   - Surprise, browInnerUp
   - Wink_Left, eyeBlinkLeft
   - Wink_Right, eyeBlinkRight

2. **Visemes** (Oculus/OVRLipSync compatible):
   - viseme_aa, Viseme_A (jaw open for "ah")
   - viseme_O, Viseme_O (rounded lips for "oh")
   - viseme_E, Viseme_E (wide mouth for "ee")
   - viseme_PP, Viseme_M (lips closed for "m/p")

3. **Critical for Lip-Sync**:
   - jawOpen (primary jaw movement)

### Backend API

#### Start Generation
```python
# Python (Backend)
from kernel.avatar_creation_server import start_avatar_generation

params = {
    "head_radius": 0.12,
    "head_color": [0.9, 0.8, 0.7],
    "smile_strength": 0.6,
    "frown_strength": 0.0,
    "surprise_strength": 0.2,
    "wink_strength": 0.0,
    "viseme_strength": 1.0
}

result = start_avatar_generation(params)
# Returns: {"success": True, "message": "Avatar generation started"}
```

```javascript
// JavaScript (Frontend)
if (typeof eel !== 'undefined') {
    const result = await eel.start_avatar_generation(params)();
    if (result.success) {
        // Poll for status updates
    }
}
```

#### Check Status
```javascript
const status = await eel.get_avatar_generation_status()();
console.log(status);
// {
//   "in_progress": true,
//   "progress": 60,
//   "stage": "generating_glb",
//   "message": "Generating GLB file...",
//   "error": null,
//   "result_path": null
// }
```

#### Get Presets
```javascript
const presets = await eel.get_avatar_presets()();
console.log(presets.friendly);
// {
//   "name": "Friendly",
//   "description": "Warm and welcoming",
//   "head_radius": 0.12,
//   ...
// }
```

### Progress Stages

| Stage | Progress | Description |
|-------|----------|-------------|
| initializing | 0% | Starting generation process |
| parsing_params | 10% | Validating input parameters |
| building_mesh | 20% | Creating base 3D geometry |
| creating_morphs | 40% | Building morph targets for animation |
| generating_glb | 60% | Encoding GLB binary format |
| validating | 80% | Verifying morph target integrity |
| finalizing | 95% | Final optimizations |
| complete | 100% | Avatar ready! |

## Integration with Lip-Sync

### Automatic Wiring

Generated avatars are **automatically compatible** with the lip-sync system:

1. **Morph Target Names**: Match phoneme map exactly
2. **ARKit Blendshapes**: Recognized by Avatar.jsx diagnostics
3. **Oculus Visemes**: Map to PHONEME_TO_VISEME dictionary

### Testing Lip-Sync

```javascript
// In avatar-integration.html
if (window.reactAvatar) {
    await window.reactAvatar.loadModel('/models/avatar_generated.glb');
    
    // Test with speech
    window.reactAvatar.speak("Hello world", {
        phonemes: [
            {time: 0.0, phoneme: "HH"},
            {time: 0.1, phoneme: "EH"},
            {time: 0.2, phoneme: "L"},
            {time: 0.4, phoneme: "OW"}
        ]
    });
}
```

### Phoneme → Viseme → Morph Target Flow

```
User speaks "Hello"
  ↓
Piper TTS generates: [{phoneme: "HH"}, {phoneme: "EH"}, {phoneme: "L"}...]
  ↓
phonemeMap.js maps: HH → viseme_PP, EH → viseme_E, L → viseme_DD
  ↓
Avatar.jsx applies: viseme_PP → blendshape[14], viseme_E → blendshape[19]
  ↓
Avatar mouth moves in sync with audio!
```

## File Locations

- **Frontend UI**: `web/avatar-creator.html`
- **Frontend Controller**: `web/avatar-creator.js`
- **Backend Server**: `kernel/avatar_creation_server.py`
- **Avatar Generator**: `kernel/avatar_generator.py`
- **Output Location**: `models/avatar_generated.glb`

## Troubleshooting

### Avatar doesn't load in 3D viewer

**Check console for errors:**
```javascript
// Should see:
[Avatar] morph targets present on GLB: [jawOpen, eyeBlinkLeft, viseme_aa, ...]
[Avatar] phoneme-map coverage: 23/23 — all visemes present ✓
```

**If missing morphs:**
- Regenerate avatar with viseme_strength = 1.0
- Verify `_MORPH_BUILDERS` includes all Oculus visemes

### Lip-sync not working

**Verify morph targets:**
```javascript
// In browser console
const mesh = window.reactAvatar.morphMeshes[0];
console.log(Object.keys(mesh.morphTargetDictionary));
// Should include: jawOpen, viseme_aa, viseme_E, viseme_O, viseme_PP
```

**Check phoneme data:**
```javascript
// Ensure backend sends phonemes
window.reactAvatar.speak("test", {
    phonemes: [{time: 0, phoneme: "T"}, ...] // Must be present!
});
```

### Generation stuck at certain stage

**Common causes:**
- Heavy CPU usage (wait or restart)
- Missing dependencies (trimesh, numpy)
- Disk space (avatar ~400KB but temp files larger)

**Solution:**
```bash
# Check logs
tail -f ~/.aios/portaios.log

# Restart backend
python run_onboarding.py
```

## Next Steps

1. **Customize Avatar**: Experiment with presets and sliders
2. **Test Lip-Sync**: Load avatar and speak phrases
3. **Integrate**: Use generated avatar as default in your app
4. **Extend**: Add more morph targets for additional expressions

## API Reference

See [`kernel/avatar_creation_server.py`](../kernel/avatar_creation_server.py) for full API documentation.
