# PortAIOS Web Interface - Quick Start Guide

## 🚀 Getting Started

The PortAIOS web interface has been streamlined into a unified system with seamless screen transitions. No more page reloads—everything is now accessible from the main interface!

## 📁 Main Files

### Primary Interface
- **`index-dynamic-avatar.html`** - Your main entry point with dock navigation
- **`avatar-integration.html`** - Advanced neural interface mode

### Supporting Files
- **`screen-manager.js`** - Screen management engine
- **`screen-styles.css`** - Cyberpunk UI theme
- **`screens/`** - Modular screen components

## 🎯 Navigation Methods

### 1. Dock Buttons (Bottom Bar)
Click any icon in the dock to switch modes:
- **⚡ AVATAR** - Return to avatar view
- **📊 DASHBOARD** - System dashboard
- **📁 DESKTOP** - File browser
- **🌐 BROWSER** - Web browser
- **💻 TERMINAL** - Command terminal
- **📄 DOCUMENT** - Document viewer
- **🎮 GAMES** - Mini-games launcher (fullscreen)
- **🤖 CREATOR** - Avatar Creator Pro (modal)
- **🧪 TESTS** - Test Suite (modal)

### 2. Voice Commands
Say **"Hey AIOS"** or click the 🎤 microphone button, then:
- *"open browser"* / *"show files"* / *"terminal"*
- *"play games"* / *"games"* / *"arcade"*
- *"avatar creator"* / *"create avatar"*
- *"test suite"* / *"run tests"*
- *"back to avatar"* / *"go back"*

### 3. Keyboard Shortcuts
- **ESC** - Close any modal screen
- Use voice keyboard commands for navigation

## 🎨 New Features

### Avatar Creator Pro
**Access:** Click 🤖 CREATOR in dock or say *"avatar creator"*

**Features:**
- Customize avatar appearance (colors, size, type)
- Live preview with real-time updates
- Quick presets (Cyber, Matrix, Neon, Ghost, Fire, Ice)
- Advanced settings (particles, glow, physics)
- Export/Save configurations
- Randomize button for experimentation

**Usage:**
1. Adjust settings in left panel
2. Watch live preview in center
3. Fine-tune advanced settings in right panel
4. Click **Save & Apply** to use your avatar
5. Click **Export** to save configuration file

### AIOS Mini-Games
**Access:** Click 🎮 GAMES in dock or say *"play games"*

**Available Games:**
- **🧠 Memory Matrix** - Match pairs in the grid
- **🎯 Neural Shooter** - Defend the neural network
- **🎴 Cyber Poker** - Texas Hold'em poker

**Features:**
- High score tracking
- Play count statistics
- Fullscreen game experience
- Click **← Back** to return to main interface

### Test Suite
**Access:** Click 🧪 TESTS in dock or say *"test suite"*

**Test Categories:**
- **Voice Commands** - Test voice recognition
- **Gesture Controls** - Test hand gestures with webcam
- **Voice Keyboard** - Test keyboard commands
- **System Status** - View integration status

**Features:**
- Interactive test buttons
- Real-time test log
- Export test results
- Camera enable/disable for gesture testing

## 🔧 Developer Usage

### Opening Screens Programmatically
```javascript
// Open any registered screen
window.screenManager.openScreen('avatar-creator');

// Open with options
window.screenManager.openScreen('games', { startGame: 'memory' });

// Close a screen
window.screenManager.closeScreen('avatar-creator');

// Check if open
if (window.screenManager.isScreenOpen('games')) {
  console.log('Games screen is open');
}
```

### Registering New Screens
```javascript
screenManager.registerScreen('my-screen', {
  type: 'modal',           // or 'fullscreen'
  title: '🎯 My Custom Screen',
  size: 'large',           // small, medium, large, fullscreen
  content: createMyContent, // Function returning HTML/DOM
  onOpen: initMyScreen,    // Optional initialization
  onClose: cleanupMyScreen // Optional cleanup
});
```

### Adding Dock Buttons
```html
<button type="button" class="dock-btn" 
        onclick="window.screenManager.openScreen('my-screen')"
        aria-label="My Screen">
  <span class="icon">🎯</span>MY SCREEN
</button>
```

## 📦 File Structure

```
web/
├── index-dynamic-avatar.html    # Main interface
├── avatar-integration.html      # Advanced mode
├── screen-manager.js            # Screen system
├── screen-styles.css            # UI styles
├── screens/                     # Screen modules
│   ├── avatar-creator-screen.js
│   ├── games-screen.js
│   └── test-suite-screen.js
├── archive/                     # Old files (archived)
├── INTEGRATION_SUMMARY.md       # Full documentation
└── QUICK_START_GUIDE.md        # This file
```

## ✨ Tips & Tricks

### Switching Modes Quickly
- Use voice commands for hands-free navigation
- ESC key always closes modals
- Mini-pip appears when not in avatar mode (click to return)

### Avatar Customization
- Start with a preset, then customize
- Use randomize button for inspiration
- Export your favorite configurations
- Real-time preview updates as you change settings

### Voice Commands
- Wake word: "Hey AIOS" (always listening)
- Or click microphone button manually
- Commands are context-aware
- Transcript shows what was recognized

### Testing
- Test suite is great for debugging voice/gesture issues
- Enable camera to test gestures live
- Export logs for troubleshooting
- All system components show integration status

## 🎮 Voice Command Cheat Sheet

### Navigation
- "open browser" / "show browser"
- "show files" / "file browser" / "desktop"
- "open terminal" / "command line"
- "show dashboard" / "system stats"
- "back to avatar" / "go back" / "home"

### Games & Tools
- "play games" / "games" / "arcade"
- "avatar creator" / "create avatar" / "customize avatar"
- "test suite" / "run tests" / "test voice"

### System
- "what time is it?" / "current time"
- "system status" / "how are you?"
- "help" / "what can you do?"

## 🐛 Troubleshooting

### Screen Won't Open
1. Open browser console (F12)
2. Check for JavaScript errors
3. Verify screen is registered in init function
4. Ensure screen module file exists

### Voice Not Working
1. Check microphone permissions
2. Use test suite to verify voice input
3. Click microphone button if wake word isn't working
4. Check browser console for errors

### Modal Won't Close
1. Press ESC key
2. Click outside modal (on dark overlay)
3. Use close button (✕) in header
4. Refresh page as last resort

### Styles Look Wrong
1. Clear browser cache
2. Verify screen-styles.css is loaded
3. Check browser console for 404 errors
4. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

## 📚 Additional Resources

- **INTEGRATION_SUMMARY.md** - Complete technical documentation
- **archive/README.md** - Information about archived files
- **Context.md** - PortAIOS system overview
- **README.md** - Main project documentation

## 🎉 What's New

### Version 2.0 (2026-06-20)
- ✅ Unified screen management system
- ✅ Modal and fullscreen screen support
- ✅ Avatar Creator Pro integrated
- ✅ Games launcher integrated
- ✅ Test suite integrated
- ✅ Reduced from 14 HTML files to 2 main files
- ✅ Seamless transitions without page reloads
- ✅ Consistent cyberpunk theme across all screens
- ✅ Enhanced voice command support
- ✅ Better mobile responsiveness

## 💡 Future Enhancements

Coming soon:
- Full game implementations (Memory, Shooter, Poker)
- Settings/preferences screen
- Interactive help system
- Plugin architecture for third-party screens
- Custom keyboard shortcuts
- Multi-screen layouts

---

**Questions?** Check the full documentation in INTEGRATION_SUMMARY.md or explore the code!

**Happy exploring the neural interface! 🚀⚡**
