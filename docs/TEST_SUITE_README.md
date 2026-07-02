# AIOS Test Suite Documentation

## 📋 Overview

Comprehensive testing suite for the consolidated AIOS avatar integration system, covering voice recognition, lipsync animation, and all integrated features.

## 🎯 Test Files

### 1. test-dashboard.html
**Main Testing Hub**
- Unified entry point for all tests
- Browser compatibility checker
- Quick navigation to test suites
- System status overview
- Links to main application

**Usage:**
```
Open test-dashboard.html in your browser
```

### 2. test-voice-system.html  
**Voice System Test Suite**

Tests covered:
- ✅ Web Speech API support check
- ✅ Microphone permission
- ✅ Voice controller initialization
- ✅ Wake word detection ("Hey AIOS")
- ✅ Speech recognition accuracy
- ✅ Voice command processing (next, back, help)
- ✅ Continuous listening mode
- ✅ Auto-sleep after timeout

**Features:**
- Real-time transcript display
- Interactive test buttons
- Automated scoring
- Status logging
- 10-second timeouts per test

**Usage:**
```
1. Open test-voice-system.html
2. Grant microphone permission
3. Click test buttons or let auto-tests run
4. Follow voice prompts
5. Check score at bottom
```

### 3. test-lipsync-system.html
**Lipsync System Test Suite**

Tests covered:
- ✅ LipSync avatar initialization
- ✅ Phoneme-to-viseme mapping
- ✅ Mouth animation sequences
- ✅ Audio synchronization
- ✅ Binary fallback mode

**Features:**
- Live avatar display
- Real-time viseme indicator
- Individual phoneme testing (40+ phonemes)
- Speech test buttons
- Custom text input
- Emotion testing

**Usage:**
```
1. Open test-lipsync-system.html
2. Avatar auto-initializes
3. Click test buttons to run tests
4. Click individual phonemes to test
5. Type custom text and click "Speak"
```

## 🧪 Test Categories

### Browser Compatibility Tests
**What:** Checks if browser supports required APIs
**Tests:**
- Web Speech Recognition API
- Speech Synthesis API
- WebGL support
- Microphone access

### Voice System Tests
**What:** Validates voice input and command processing
**Tests:**
- Controller initialization
- Wake word detection
- Real-time transcription
- Command recognition
- Continuous mode
- Auto-sleep

### Lipsync Tests
**What:** Validates mouth animation and synchronization
**Tests:**
- Avatar rendering
- Phoneme mapping
- Viseme animation
- Audio sync
- Fallback mode

## 📊 Test Results

### Scoring System
- **Green (✓):** Test passed
- **Red (✗):** Test failed
- **Yellow (⏳):** Test pending

### Summary Display
- Shows X/Y tests passed
- **100% pass:** Green message "All tests passed!"
- **<100% pass:** Orange warning with fail count

## 🎤 Voice Test Examples

### Test 1: Wake Word Detection
```
1. Click "Start" button
2. Say: "Hey AIOS"
3. Should show: ✓ Wake word detected
```

### Test 2: Command Recognition
```
1. Click test button for "next"
2. Say: "next" or "continue"
3. Should show: ✓ Command recognized
```

### Test 3: Continuous Listening
```
1. Click "Test" button
2. Say 2 different phrases
3. Should show: ✓ Detected 2 phrases
```

## 💬 Lipsync Test Examples

### Test 1: Short Phrase
```
1. Click "Short Phrase" button
2. Watch avatar mouth move
3. See viseme display update
```

### Test 2: Individual Phoneme
```
1. Click any phoneme button (e.g., "AA")
2. Watch mouth shape change
3. See corresponding viseme
```

### Test 3: Custom Text
```
1. Type "Hello world" in text box
2. Click "Speak Custom Text"
3. Watch synchronized animation
```

## 🔧 Troubleshooting

### Voice Tests Failing
**Issue:** Microphone permission denied
**Fix:** Allow microphone in browser settings

**Issue:** Wake word not detected
**Fix:** Speak clearly, check microphone volume

**Issue:** Speech recognition timeout
**Fix:** Ensure stable internet (API requires connection)

### Lipsync Tests Failing
**Issue:** Avatar not rendering
**Fix:** Check WebGL support, update graphics drivers

**Issue:** No mouth movement
**Fix:** Wait for avatar initialization, check console

**Issue:** Viseme not updating
**Fix:** Ensure avatar initialized successfully

## 📱 Browser Support

### Full Support (All Features)
- ✅ Chrome 80+
- ✅ Edge 80+
- ✅ Opera 67+

### Partial Support (No Voice)
- ⚠️ Firefox (no Web Speech API)
- ⚠️ Safari (limited Speech API)

### Mobile Support
- ✅ Chrome Android (full support)
- ⚠️ Safari iOS (limited voice)

## 🚀 Running Tests

### Quick Start
```bash
# Open in browser
open test-dashboard.html

# Or use local server
python3 -m http.server 8000
# Then open http://localhost:8000/test-dashboard.html
```

### Automated Testing
Tests auto-run on page load:
- Browser compatibility (immediate)
- Avatar initialization (500ms delay)

Manual tests require button clicks.

### Sequential Testing
Recommended order:
1. Voice System Tests (requires interaction)
2. Lipsync Tests (mostly automated)
3. Main Application (full integration)

## 📈 Test Coverage

### Voice System: 8 Tests
1. Browser support ✓
2. Mic permission ✓
3. Controller init ✓
4. Wake word ✓
5. Recognition ✓
6. Commands (3x) ✓
7. Continuous mode ✓
8. Auto-sleep ✓

### Lipsync System: 5 Tests
1. Avatar init ✓
2. Viseme mapping ✓
3. Mouth animation ✓
4. Audio sync ✓
5. Binary fallback ✓

### Total: 13 Automated Tests

## 🎯 Success Criteria

### Voice System
- ✅ All 8 tests pass
- ✅ Wake word detects within 10s
- ✅ Commands recognize accurately
- ✅ Auto-sleep triggers correctly

### Lipsync System
- ✅ All 5 tests pass
- ✅ Avatar renders properly
- ✅ Mouth syncs with speech
- ✅ All phonemes mapped

### Overall
- ✅ 13/13 tests passing
- ✅ No console errors
- ✅ Smooth animations
- ✅ Responsive UI

## 📝 Notes

### Production Use
- HTTPS required for voice in production
- Microphone permission persists per domain
- Speech API requires internet connection

### Development
- Works on localhost without HTTPS
- Console logging available
- Real-time status updates

### Performance
- Voice tests: ~2-3 minutes total
- Lipsync tests: ~1-2 minutes total
- Lightweight, minimal CPU usage

---

**Status:** ✅ Production Ready
**Version:** 1.0
**Last Updated:** 2026-05-07
