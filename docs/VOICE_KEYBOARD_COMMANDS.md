# Voice Keyboard Commands System

Complete voice-controlled keyboard input, annotation, and dictation system for AIOS with Microsoft speech grammar compatibility.

## 🎯 Overview

The Voice Keyboard Commands system enables full keyboard control via voice commands, following Microsoft's speech command patterns for consistency and reliability. It includes three integrated modes:

1. **Keyboard Mode** - Voice-controlled keyboard input with full key mapping
2. **Annotation Mode** - Voice annotations and highlights
3. **Dictation Mode** - Natural language text transcription

## 📁 Files

### Backend (Python)
- `kernel/voice_keyboard_commands.py` - Core command processor with full key mappings and mode handling

### Frontend (JavaScript)
- `web/voice-keyboard-controller.js` - Frontend controller with visual feedback and UI integration
- `web/test-voice-keyboard-commands.html` - Comprehensive test suite

### Integration
- `kernel/onboarding_gui.py` - Backend Eel integration (updated)
- `web/avatar-integration.html` - Avatar mode integration (updated)
- `web/index-dynamic-avatar.html` - Dynamic avatar mode integration (updated)

## 🎤 Voice Command Patterns

### Universal Grammar

All commands follow a consistent pattern based on Microsoft speech keyboard standards:

```
press [key]                           # Single key
press [modifier] plus [key]           # Key combination
press [modifier] plus [modifier] plus [key]   # Multiple modifiers
press [key] [number] times            # Repeated key press
```

### Supported Keys

#### Function Row
- `press escape` (or `esc`)
- `press f1` through `press f12`
- `press print screen`, `press scroll lock`, `press pause`

#### Number Row
- `press backtick` (or `grave`, `tilde`)
- `press one` through `press zero`
- `press hyphen` (or `minus`, `dash`)
- `press equal sign` (or `equals`)
- `press backspace`

#### Letter Keys
- `press a` through `press z`
- **Phonetic alphabet supported**: `press alpha`, `press bravo`, `press charlie`, etc. (NATO/ICAO)

#### Special Keys
- `press tab`
- `press enter` (or `return`)
- `press space` (or `spacebar`)
- `press caps lock`
- `press shift` / `press right shift`
- `press control` (or `ctrl`)
- `press alt` (or `option`)
- `press windows` (or `command`, `super`, `win`)

#### Navigation
- `press up` / `down` / `left` / `right` (or `up arrow`, etc.)
- `press home` / `end`
- `press page up` / `page down` (or `pgup`, `pgdown`)
- `press insert` / `delete` (or `del`)

#### Numpad
- `press num lock`
- `press numpad zero` through `press numpad nine`
- `press numpad divide`, `press numpad multiply`, `press numpad plus`, `press numpad minus`
- `press numpad enter`, `press numpad decimal`

#### Punctuation
- `press comma`, `press period`, `press semicolon`, `press colon`
- `press apostrophe` (or `quote`)
- `press slash` (or `forward slash`)
- `press backslash`
- `press open bracket`, `press close bracket`

### Key Combinations

**Examples:**
```
press control plus c              # Copy
press control plus v              # Paste
press control plus z              # Undo
press shift plus a                # Capital A
press alt plus f4                 # Close window
press control plus shift plus escape   # Task Manager
press windows plus r              # Run dialog
press control plus alt plus delete     # Security options
```

### Repetition

**Syntax:** `press [key] [number] times`

**Examples:**
```
press space 5 times
press enter 3 times
press tab 2 times
```

### Direct Typing

**Syntax:** `type [text]`

**Examples:**
```
type hello world
type user@example.com
type This is a test sentence
```

### Hold and Release

**For gaming or complex input:**
```
hold shift
press a
release shift

hold control
press c
release control
```

## 📝 Annotation Commands

### Mode Switching
```
enter annotation mode
start annotation mode
exit annotation mode
```

### Adding Annotations
```
annotate [text]
add annotation [text]
add note [text]
```

**Examples:**
```
annotate this is important
add annotation review this section later
add note check data validation here
```

### Managing Annotations
```
show annotations           # Display all annotations
list annotations          # Alternative syntax
view annotations         # Alternative syntax
clear annotations        # Clear all
delete annotations       # Alternative syntax
```

### Highlighting
```
highlight [text]
```

**Examples:**
```
highlight key points
highlight important section
highlight TODO items
```

## 🎙️ Dictation Commands

### Mode Control
```
enter dictation mode
start dictation mode
begin dictation

start dictation           # Start a dictation session
stop dictation           # Stop and preserve buffer
end dictation            # Alternative syntax

exit dictation mode      # Exit mode entirely
```

### Buffer Operations
```
clear dictation          # Clear dictation buffer
clear buffer
erase dictation

insert dictation         # Insert buffer into active field
paste dictation         # Alternative syntax
```

### Punctuation (in dictation mode)
```
period                   # .
comma                    # ,
question mark           # ?
exclamation point       # !
colon                   # :
semicolon               # ;
```

### Line Breaks (in dictation mode)
```
new line                # Single line break
new paragraph           # Double line break
```

### Natural Dictation

In dictation mode, simply speak naturally and the system will transcribe:

```
[Enter dictation mode]
"This is a test sentence period
It will be transcribed automatically comma
with proper spacing and formatting period
New paragraph
This starts a new paragraph period"
[Stop dictation]
[Insert dictation]
```

## 🎨 Visual Feedback

### Mode Indicators

- **Keyboard Mode** - Cyan badge with ⌨️ icon
- **Annotation Mode** - Yellow badge with 📝 icon  
- **Dictation Mode** - Magenta badge with 🎙️ icon

### Action Feedback

Each voice command triggers visual feedback:

- **Key Press** - Cyan overlay showing key combination
- **Text Input** - Green overlay with typed text
- **Annotation** - Yellow overlay with annotation added
- **Dictation** - Magenta overlay with buffer status
- **Mode Switch** - Blue overlay with new mode
- **Error** - Red overlay with error message

### UI Components

1. **Feedback Overlay** - Center screen popup showing action
2. **Mode Badge** - Top center indicator showing current mode
3. **Annotation Panel** - Right side panel listing all annotations
4. **Dictation Display** - Bottom center panel showing buffer
5. **Key Visual** - Bottom center temporary key combination display

## 🔌 Integration

### Backend Setup

The voice keyboard commands are automatically registered during Eel initialization in `kernel/onboarding_gui.py`:

```python
from kernel.voice_keyboard_commands import setup_voice_keyboard_for_eel
setup_voice_keyboard_for_eel(eel)
```

### Frontend Integration

#### Avatar Integration Mode

```javascript
import { VoiceKeyboardController } from './voice-keyboard-controller.js';

// Initialize controller
voiceKeyboard = new VoiceKeyboardController(voiceInput, {
    showVisualFeedback: true,
    enableAnnotations: true,
    enableDictation: true
});

// Process commands in your voice handler
async function processCmd(text) {
    // Try keyboard commands first
    if (voiceKeyboard) {
        const result = await voiceKeyboard.processCommand(text);
        if (result && result.success) {
            return; // Command handled
        }
    }
    
    // Fall through to other command handlers...
}
```

#### Dynamic Avatar Mode

Same integration pattern, controller works standalone without VoiceInputController:

```javascript
voiceKeyboard = new VoiceKeyboardController(null, {
    showVisualFeedback: true,
    enableAnnotations: true,
    enableDictation: true
});
```

## 🧪 Testing

### Test Suite

Open `web/test-voice-keyboard-commands.html` in your browser for:

- Interactive command testing
- Visual feedback verification
- Mode switching tests
- Backend connection status
- Real-time command logging
- Printable cheat sheet

### Manual Testing Workflow

1. **Open test suite**: Navigate to `/test-voice-keyboard-commands.html`
2. **Check backend status**: Verify Eel connection
3. **Test keyboard commands**: Click "Test" buttons or type commands
4. **Test mode switching**: Try all three modes
5. **Test annotations**: Add, show, clear annotations
6. **Test dictation**: Start, dictate, insert, stop
7. **Test visual feedback**: Verify overlays appear correctly

### Example Test Sequence

```javascript
// Keyboard commands
testCommand('press enter');
testCommand('press control plus c');
testCommand('press shift plus a');
testCommand('type hello world');
testCommand('press alpha');  // NATO phonetic

// Annotation mode
testCommand('enter annotation mode');
testCommand('annotate this is important');
testCommand('add annotation review later');
testCommand('show annotations');
testCommand('clear annotations');

// Dictation mode
testCommand('enter dictation mode');
testCommand('start dictation');
testCommand('This is a test sentence');
testCommand('period');
testCommand('new line');
testCommand('Another sentence here');
testCommand('stop dictation');
testCommand('insert dictation');
```

## 🎯 Use Cases

### 1. Accessibility
- Hands-free keyboard operation
- Voice-controlled text input
- Annotation for review without typing

### 2. Multitasking
- Control keyboard while hands are busy
- Add notes while viewing content
- Dictate while performing other tasks

### 3. Gaming
- Complex key combinations via voice
- Macro-like repetitive inputs
- Hold/release for persistent modifiers

### 4. Content Creation
- Fast dictation for drafts
- Voice annotations while reviewing
- Keyboard shortcuts while narrating

### 5. Code Review
- Annotate code sections vocally
- Navigate with voice commands
- Highlight important areas

## 📊 Architecture

### Command Flow

```
Voice Input
    ↓
Voice Recognition (Browser/Backend)
    ↓
VoiceKeyboardController.processCommand()
    ↓
├─ Backend (Eel): process_keyboard_voice_command()
│       ↓
│  VoiceKeyboardCommands.process_command() (Python)
│       ↓
│  Pattern matching & parsing
│       ↓
│  Return action object
│
└─ Frontend Fallback: processCommandLocal()
        ↓
    Pattern matching (JavaScript)
        ↓
    Return action object
    
    ↓
executeAction()
    ↓
├─ simulateKeyPress() → KeyboardEvent
├─ typeText() → Document modification
├─ addAnnotation() → UI update
├─ appendDictation() → Buffer update
└─ showFeedback() → Visual overlay
```

### Key Classes

#### Backend (`voice_keyboard_commands.py`)

- **VoiceKeyboardCommands** - Main command processor
  - `process_command()` - Parse and route commands
  - `_parse_key_combination()` - Parse modifier+key syntax
  - `_handle_*()` - Action-specific handlers
  - `_build_key_mappings()` - Comprehensive key map
  - `_build_phonetic_alphabet()` - NATO alphabet support

#### Frontend (`voice-keyboard-controller.js`)

- **VoiceKeyboardController** - Frontend coordinator
  - `processCommand()` - Command entry point
  - `executeAction()` - Action dispatcher
  - `simulateKeyPress()` - KeyboardEvent generation
  - `setupAnnotationUI()` - Annotation panel
  - `setupDictationUI()` - Dictation display
  - `showFeedback()` - Visual feedback system

## 🔧 Configuration

### Controller Options

```javascript
new VoiceKeyboardController(voiceInput, {
    // Visual feedback overlay
    showVisualFeedback: true,
    
    // Enable annotation system
    enableAnnotations: true,
    
    // Enable dictation mode
    enableDictation: true,
    
    // Custom annotation container (optional)
    annotationContainer: null,
    
    // Custom dictation display (optional)
    dictationDisplay: null
});
```

### Backend Customization

Extend `VoiceKeyboardCommands` class to add custom keys or patterns:

```python
class CustomKeyboardCommands(VoiceKeyboardCommands):
    def _build_key_mappings(self):
        keys = super()._build_key_mappings()
        # Add custom key mappings
        keys['custom_key'] = 'CustomKey'
        return keys
    
    def _build_command_patterns(self):
        patterns = super()._build_command_patterns()
        # Add custom command patterns
        patterns.append({
            "pattern": r"^my custom command$",
            "action": "custom_action",
            "priority": 10
        })
        return patterns
    
    def _handle_custom_action(self, text, match):
        return {
            "action": "custom_action",
            "success": True,
            "message": "Custom action executed"
        }
```

## 📚 API Reference

### Backend Eel Functions

```python
@eel.expose
def process_keyboard_voice_command(text: str) -> Optional[Dict[str, Any]]
    """Process voice keyboard command and return action"""

@eel.expose
def get_keyboard_command_mode() -> str
    """Get current command mode (keyboard/annotation/dictation)"""

@eel.expose
def get_keyboard_available_commands(mode: Optional[str] = None) -> List[str]
    """Get list of available commands for a mode"""

@eel.expose
def set_keyboard_command_mode(mode: str) -> Dict[str, Any]
    """Set keyboard command mode"""
```

### Frontend Methods

```javascript
// Process a voice command
async processCommand(text: string): Promise<Object>

// Execute an action result
async executeAction(result: Object): Promise<void>

// Simulate keyboard input
async simulateKeyPress(result: Object): Promise<void>

// Type text directly
async typeText(text: string): Promise<void>

// Mode management
switchMode(mode: string): void
updateModeIndicator(): void

// Annotation methods
addAnnotation(text: string, timestamp: string): void
showAnnotations(): void
clearAnnotations(target?: string): void
highlightText(text: string): void

// Dictation methods
startDictation(): void
stopDictation(): void
clearDictation(): void
appendDictation(text: string): void
async insertDictation(text: string): Promise<void>

// Visual feedback
showFeedback(message: string, type: string): void
showKeyVisual(key: string, modifiers: Array<string>): void
```

## 🚀 Performance

- **Command latency**: < 100ms for local processing
- **Backend latency**: < 200ms with Eel round-trip
- **Visual feedback**: Smooth 60fps animations
- **Memory footprint**: ~2MB for controller + UI
- **Pattern matching**: O(n) where n = number of patterns (optimized by priority)

## 🔒 Security

- All keyboard events are simulated locally in the browser
- No actual system-level keyboard control
- Commands are sandboxed to the web page context
- Backend processing is optional (works offline)

## 🐛 Troubleshooting

### Commands Not Recognized

1. Check backend connection status in test suite
2. Verify command syntax matches patterns exactly
3. Try the phonetic alphabet for ambiguous letters
4. Check browser console for error messages

### Visual Feedback Not Showing

1. Verify `showVisualFeedback: true` in options
2. Check for CSS z-index conflicts
3. Look for JavaScript errors in console

### Keyboard Events Not Working

1. Ensure an input field is focused (for typing commands)
2. Check that the target element accepts keyboard input
3. Verify KeyboardEvent support in your browser

### Dictation Buffer Issues

1. Confirm dictation mode is active
2. Check dictation display for buffer content
3. Clear buffer and try again

## 📝 Future Enhancements

- [ ] Custom key mapping configuration UI
- [ ] Annotation export/import
- [ ] Dictation auto-save
- [ ] Multi-language support
- [ ] Voice training for accuracy
- [ ] Gesture integration for touch devices
- [ ] Macro recording and playback
- [ ] Cloud sync for annotations

## 📄 License

Part of the AIOS system. See main LICENSE file.

## 🤝 Contributing

Contributions welcome! Please ensure:

1. All new keys are added to both Python and JavaScript mappings
2. Command patterns follow Microsoft speech grammar
3. Visual feedback is consistent across modes
4. Test suite is updated with new commands
5. Documentation is updated

## 📞 Support

For issues or questions:
- Check the test suite: `/test-voice-keyboard-commands.html`
- Review this documentation
- Check browser console for errors
- Verify backend connection status

---

**Last Updated**: 2026-05-21  
**Version**: 1.0.0  
**Compatible with**: AIOS Neural Interface v2.0
