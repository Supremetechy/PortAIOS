# PortAIOS Web Interface - Test Checklist

## 🧪 Manual Testing Guide

Use this checklist to verify all functionality after the consolidation.

### ✅ Basic Interface Tests

- [ ] Open `web/index-dynamic-avatar.html` in browser
- [ ] Page loads without errors (check browser console - F12)
- [ ] All CSS styles load correctly (cyberpunk theme visible)
- [ ] Avatar displays in center of screen
- [ ] Dock buttons visible at bottom
- [ ] Voice bar visible at bottom
- [ ] System bar visible at top

### ✅ Dock Navigation Tests

- [ ] Click **⚡ AVATAR** - Returns to avatar view
- [ ] Click **📊 DASHBOARD** - Shows system dashboard
- [ ] Click **📁 DESKTOP** - Opens file browser
- [ ] Click **🌐 BROWSER** - Opens web browser panel
- [ ] Click **💻 TERMINAL** - Opens terminal interface
- [ ] Click **📄 DOCUMENT** - Opens document viewer
- [ ] Click **🎮 GAMES** - Opens fullscreen games launcher
- [ ] Click **🤖 CREATOR** - Opens Avatar Creator modal
- [ ] Click **🧪 TESTS** - Opens Test Suite modal

### ✅ Modal Screen Tests

#### Avatar Creator Pro
- [ ] Modal opens when clicking 🤖 CREATOR
- [ ] Modal has proper styling (cyan borders, dark background)
- [ ] Close button (✕) works
- [ ] ESC key closes modal
- [ ] Click outside modal closes it
- [ ] Three panels display (Basic, Preview, Advanced)
- [ ] All controls are interactive
- [ ] Preview canvas renders
- [ ] Quick presets buttons work
- [ ] Randomize button changes values
- [ ] Range sliders update values
- [ ] Color pickers work
- [ ] Save & Apply button functions

#### Test Suite
- [ ] Modal opens when clicking 🧪 TESTS
- [ ] Modal has proper styling
- [ ] Close button works
- [ ] Voice command test buttons display
- [ ] Gesture test buttons display
- [ ] Voice keyboard test buttons display
- [ ] System status indicators show
- [ ] Test log displays
- [ ] Clear Log button works
- [ ] Export Log button works
- [ ] Camera enable button works (may require permissions)

### ✅ Fullscreen Screen Tests

#### Games Launcher
- [ ] Fullscreen overlay appears
- [ ] Back button (← Back to Games) displays
- [ ] Four game cards visible
- [ ] Game cards have hover effects
- [ ] High score displays (initially 0)
- [ ] Play count displays (initially 0)
- [ ] Click game card opens game canvas
- [ ] Back button closes fullscreen
- [ ] ESC key closes fullscreen

### ✅ Voice Command Tests

**Note:** Microphone permissions required

- [ ] Click 🎤 microphone button
- [ ] Say "Hey AIOS" activates listening
- [ ] Voice transcript appears in voice bar
- [ ] Say "open browser" - switches to browser mode
- [ ] Say "show files" - switches to desktop mode
- [ ] Say "terminal" - switches to terminal mode
- [ ] Say "play games" - opens games launcher
- [ ] Say "avatar creator" - opens Avatar Creator
- [ ] Say "test suite" - opens Test Suite
- [ ] Say "back to avatar" - returns to avatar mode

### ✅ Keyboard Shortcuts

- [ ] ESC closes Avatar Creator modal
- [ ] ESC closes Test Suite modal
- [ ] ESC closes Games fullscreen

### ✅ Screen Manager API Tests

Open browser console (F12) and run:

```javascript
// Test screen manager exists
console.log(window.screenManager);

// Test opening screens programmatically
screenManager.openScreen('avatar-creator');
// Should open Avatar Creator

// Test closing
screenManager.closeScreen('avatar-creator');
// Should close modal

// Test checking if open
console.log(screenManager.isScreenOpen('avatar-creator'));
// Should return false

// Test games screen
screenManager.openScreen('games');
// Should open fullscreen

// Close all
screenManager.closeAllScreens();
// Should close everything
```

Expected results:
- [ ] screenManager object exists
- [ ] openScreen() opens modals
- [ ] closeScreen() closes modals
- [ ] isScreenOpen() returns correct boolean
- [ ] closeAllScreens() closes everything

### ✅ Integration Tests

- [ ] Switching modes preserves avatar state
- [ ] Mini-pip appears when leaving avatar mode
- [ ] Clicking mini-pip returns to avatar
- [ ] Mode label updates in system bar
- [ ] Active dock button highlights
- [ ] Toast notifications appear
- [ ] No JavaScript errors in console
- [ ] No CSS loading errors (check Network tab)

### ✅ Responsive Design Tests

Test at different viewport sizes:

**Desktop (1920x1080)**
- [ ] All elements visible
- [ ] Proper spacing and layout
- [ ] Dock buttons fit comfortably

**Tablet (768x1024)**
- [ ] Layout adjusts appropriately
- [ ] Modal sizes responsive
- [ ] Touch targets adequate

**Mobile (375x667)**
- [ ] Single column layouts activate
- [ ] Buttons remain accessible
- [ ] Text remains readable

### ✅ Browser Compatibility

Test in multiple browsers:

**Chrome/Edge**
- [ ] All features work
- [ ] Voice input works
- [ ] Animations smooth

**Firefox**
- [ ] All features work
- [ ] Voice input works
- [ ] Animations smooth

**Safari**
- [ ] All features work
- [ ] Voice input works
- [ ] Animations smooth

### ✅ Performance Tests

- [ ] Page load time < 3 seconds
- [ ] Modal open/close smooth (no jank)
- [ ] Mode transitions smooth
- [ ] No memory leaks (check Dev Tools)
- [ ] Avatar animation smooth (60fps)

### ✅ Avatar Creator Specific Tests

- [ ] Name field accepts input
- [ ] Type selector changes preview
- [ ] Size slider affects preview
- [ ] Primary color picker updates preview
- [ ] Secondary color picker updates preview
- [ ] Animation style selector works
- [ ] Particle count slider updates
- [ ] Glow intensity affects preview
- [ ] Rotation speed changes preview
- [ ] Complexity slider works
- [ ] Physics toggle functions
- [ ] Voice reactivity slider works

**Preset Tests:**
- [ ] Cyber preset applies cyan theme
- [ ] Matrix preset applies green theme
- [ ] Neon preset applies magenta theme
- [ ] Ghost preset applies white theme
- [ ] Fire preset applies red/orange theme
- [ ] Ice preset applies blue/white theme

**Save/Export Tests:**
- [ ] Export downloads JSON file
- [ ] Save stores in localStorage
- [ ] Save & Apply closes modal
- [ ] Avatar updates in real-time

### ✅ Games Launcher Specific Tests

- [ ] Memory Matrix card displays
- [ ] Neural Shooter card displays
- [ ] Cyber Poker card displays
- [ ] Coming Soon card displays (disabled)
- [ ] High scores persist between sessions
- [ ] Play counts increment
- [ ] Stats stored in localStorage

### ✅ Test Suite Specific Tests

**Voice Commands Section:**
- [ ] All test buttons clickable
- [ ] Commands log to test log
- [ ] Timestamp appears in log

**Gesture Controls Section:**
- [ ] Camera enable button works
- [ ] Video element displays
- [ ] Gesture test buttons work
- [ ] Events dispatched correctly

**Voice Keyboard Section:**
- [ ] Keyboard command buttons work
- [ ] Commands process correctly

**System Status Section:**
- [ ] All 6 status indicators show
- [ ] Green indicators (success state)
- [ ] Pulse animation visible

### 🐛 Error Scenarios to Test

- [ ] What happens if microphone access denied?
- [ ] What happens if camera access denied?
- [ ] Can you open multiple modals? (should only allow one)
- [ ] Does back button work from games?
- [ ] Does closing modal restore previous state?
- [ ] Network errors handled gracefully?

### 📝 Console Checks

After all tests, check browser console for:
- [ ] No red errors
- [ ] Only expected warnings
- [ ] Initialization messages appear
- [ ] Screen registration messages appear

Expected console messages:
```
[ScreenManager] Registered screen: avatar-creator (modal)
[ScreenManager] Registered screen: games (fullscreen)
[ScreenManager] Registered screen: test-suite (modal)
[AIOS] Voice keyboard commands initialized
[AIOS] Native Dynamic Interface initialized
```

## 🎯 Priority Issues

If you find issues, prioritize fixing:

1. **Critical:** Screens won't open
2. **Critical:** JavaScript errors blocking functionality
3. **High:** Voice commands not working
4. **High:** Modal won't close
5. **Medium:** Styling issues
6. **Low:** Minor animation glitches

## 📊 Test Results Template

```
Test Date: _______________
Browser: _________________
OS: ______________________

PASS/FAIL Summary:
- Basic Interface: ___/7
- Dock Navigation: ___/9
- Modal Screens: ___/26
- Fullscreen: ___/8
- Voice Commands: ___/10
- Keyboard: ___/3
- Screen Manager API: ___/5
- Integration: ___/8

Total: ___/76

Issues Found:
1. ________________________________
2. ________________________________
3. ________________________________
```

## ✅ Sign-Off

- [ ] All critical tests passing
- [ ] No console errors
- [ ] Voice commands functional
- [ ] All screens accessible
- [ ] Documentation reviewed
- [ ] Ready for production use

---

**Tester:** _______________  
**Date:** _______________  
**Signature:** _______________
