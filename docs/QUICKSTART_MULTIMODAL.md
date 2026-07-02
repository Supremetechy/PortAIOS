# PortAIOS Multimodal AI System - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Install Dependencies

```bash
pip install -r requirements_gui.txt
```

This installs the new multimodal components:
- **MediaPipe** - Hand/face/eye tracking
- **scikit-learn** - AI learning and predictions
- **pandas** - Data analysis

### Step 2: Run PortAIOS

```bash
python run_onboarding.py
# or use the installer/launcher if you built the app
```

The multimodal system will automatically initialize!

### Step 3: Enable Gesture Control

1. Look for the **"✋ Enable Gesture Control"** button (bottom-right corner)
2. Click it and grant camera permissions
3. You'll see a live camera feed with gesture detection

### Step 4: Try Your First Gestures

**Easy gestures to start:**

1. **👍 Thumbs Up** - System will recognize it and show confirmation
2. **👉 Point** - Point at any UI element to select it
3. **⬆️ Swipe Up** - Swipe your hand upward to scroll up
4. **👋 Wave** - Wave to switch between windows

### Step 5: Combine Voice + Gesture

Try these powerful multimodal commands:

```
Say: "Open that file" + Point at a file
Say: "Delete this" + Point at item  
Say: "Yes" OR give thumbs up (both work!)
```

---

## 📋 Gesture Cheat Sheet (Print This!)

### Basic Hand Gestures

| Gesture | How to Do It | What It Does |
|---------|--------------|--------------|
| 👍 | Thumb up, fingers closed | Confirm/Accept |
| 👎 | Thumb down, fingers closed | Cancel/Reject |
| ✌️ | Index + middle extended | Double click |
| 👌 | Thumb + index circle | Play/Pause |
| 👉 | Only index extended | Click/Select |
| ✊ | All fingers closed | Close window |
| 🖐️ | All fingers open | Stop/Release |
| 🤏 | Thumb + index close | Grab/Drag |

### Swipe Gestures

| Gesture | How to Do It | What It Does |
|---------|--------------|--------------|
| ⬆️ | Hand up quickly | Scroll up |
| ⬇️ | Hand down quickly | Scroll down |
| ⬅️ | Hand left quickly | Go back |
| ➡️ | Hand right quickly | Go forward |
| 👋 | Hand left-right-left | Switch window |

### Face Gestures

| Gesture | How to Do It | What It Does |
|---------|--------------|--------------|
| 🙂 | Nod head up-down | Confirm |
| 🙅 | Shake head left-right | Cancel |
| 😊 | Smile | Take screenshot |

---

## 💡 Pro Tips

### 1. Better Gesture Recognition

- **Lighting:** Use bright, even lighting
- **Position:** Keep hands in camera frame
- **Distance:** 1-2 feet from camera works best
- **Speed:** Do gestures deliberately, not too fast

### 2. Privacy Controls

- **Camera Indicator:** Red dot shows when camera is active
- **Privacy Mode:** Click 🔒 to blur your video feed
- **Quick Disable:** Click camera button to turn off instantly
- **Auto-Off:** Camera stops when you close PortAIOS

### 3. AI Learning

The system learns from your usage:
- Predicts apps you'll open
- Suggests files based on time
- Learns your preferred input methods
- All data stored locally (100% private)

**View your AI insights:**
```javascript
// In browser console or via UI
eel.get_learning_stats()()
```

### 4. Customize Gestures

Edit `kernel/gesture_commands.py` to customize:

```python
# Change what a gesture does
self.register_command(GestureCommand(
    gesture_type=GestureType.PEACE_SIGN,
    action_type=ActionType.SCREENSHOT,  # Changed from DOUBLE_CLICK
    description="Take screenshot with peace sign"
))
```

---

## 🐛 Troubleshooting

### Camera Won't Start

**Problem:** Permission denied
**Fix:** 
1. Check system camera permissions
2. Close other apps using camera (Zoom, Skype, etc.)
3. Try different camera index: `start_gesture_camera(1)`

### Gestures Not Detected

**Problem:** Low accuracy
**Fix:**
1. Improve lighting (turn on lights!)
2. Clean camera lens
3. Position hands closer to camera
4. Do gestures more slowly and deliberately

### Low FPS / Laggy

**Problem:** System too slow
**Fix:**
1. Close other apps
2. Lower camera resolution in settings
3. Disable face tracking (hand-only mode)
4. Use lower FPS (15 instead of 30)

### AI Not Learning

**Problem:** No predictions shown
**Fix:**
1. Use the system for 2-3 days to collect data
2. Make sure learning is enabled
3. Check database: `~/.portaios/learning/behavior.db` exists

---

## 🎯 Example Workflows

### Morning Routine
```
8:00 AM - AI suggests: "Open Slack" (you usually do)
👍 Thumbs up to confirm
AI learns: You confirm Slack at 8 AM on weekdays
```

### File Management
```
Say: "Show me yesterday's files"
👉 Point at a file
Say: "Open this"
✊ Close with fist gesture when done
```

### Media Control
```
👌 OK sign to play/pause music
⬆️⬇️ Swipe up/down for volume
😊 Smile to take screenshot
```

### Web Browsing
```
⬅️ Swipe left to go back
➡️ Swipe right to go forward
⬆️⬇️ Swipe to scroll
👉 Point to click links
```

---

## 📊 System Status

Check if everything is working:

```javascript
// In browser console
eel.get_multimodal_status()()

// Expected output:
{
  "enabled": true,
  "camera_active": true,
  "fps": 30,
  "gestures_detected": [...],
  "learning_enabled": true
}
```

---

## 🔄 Updates & Features

### What's New in This Release

✅ **Gesture Control** - Full hand, face, eye tracking
✅ **AI Learning** - Predictive suggestions based on behavior
✅ **Multimodal Fusion** - Voice + Gesture + Gaze combined
✅ **Privacy First** - 100% local processing, no cloud
✅ **30+ Gestures** - Comprehensive gesture library
✅ **Real-time Feedback** - See gestures as they're detected
✅ **Customizable** - Map any gesture to any action

### Coming Soon

🔜 Mobile companion app
🔜 Advanced AI predictions
🔜 Accessibility enhancements

---

## 🆘 Need Help?

1. **Read Full Docs:** `docs/MULTIMODAL_SYSTEM_COMPLETE.md`
2. **Check Troubleshooting:** See section above
3. **View Examples:** Try the example workflows
4. **Experiment:** The system is designed to be intuitive!

---

## 🎉 You're Ready!

Start using PortAIOS with gestures, voice, and AI learning.

**Remember:**
- The system learns as you use it
- All data stays on your device
- You can customize everything
- Have fun exploring! 🚀

---

*Welcome to the future of human-computer interaction!*
Issues in console log in chrome browser
avatar-integration.html:9  GET https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&family=Syne+Mono&display=swap net::ERR_INTERNET_DISCONNECTED
avatar-integration.html:51 Uncaught SyntaxError: Unexpected token ':' (at avatar-integration.html:51:16)
SpatialEnvironmentRenderer.js:39  GET https://esm.sh/three@0.160.0/examples/jsm/postprocessing/UnrealBloomPass.js net::ERR_INTERNET_DISCONNECTED
SpatialEnvironmentRenderer.js:36  GET https://esm.sh/three@0.160.0/examples/jsm/postprocessing/EffectComposer.js net::ERR_INTERNET_DISCONNECTED
SpatialEnvironmentRenderer.js:38  GET https://esm.sh/three@0.160.0/examples/jsm/postprocessing/ShaderPass.js net::ERR_INTERNET_DISCONNECTED
SpatialEnvironmentRenderer.js:37  GET https://esm.sh/three@0.160.0/examples/jsm/postprocessing/RenderPass.js net::ERR_INTERNET_DISCONNECTED
SpatialEnvironmentRenderer.js:35  GET https://esm.sh/three@0.160.0 net::ERR_INTERNET_DISCONNECTED
avatar-integration.html:1 Uncaught TypeError: Failed to resolve module specifier "react". Relative references must start with either "/", "./", or "../".