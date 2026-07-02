<img width="2048" height="2048" alt="image" src="https://github.com/user-attachments/assets/5ef8a34d-3321-48dd-a418-6a1ebaa9b563" />

# PortAIOS — Desktop App Packaging

Turns PortAIOS into a double-clickable app for macOS, Windows, and Linux.
The bundled app ships with its own Python runtime, so end users don't need
Python installed.

## What end users see

- **macOS**: `PortAIOS.app` — drag into `/Applications`, double-click to launch.
- **Windows**: `PortAIOS-Setup-1.0.0.exe` installer → desktop + Start Menu shortcut.
- **Linux**: `PortAIOS-x86_64.AppImage` — `chmod +x` then double-click, or the
  unpacked `dist/PortAIOS/` folder.

First launch creates `~/Library/Application Support/PortAIOS/` (macOS),
`%APPDATA%\PortAIOS\` (Windows), or `~/.local/share/PortAIOS/` (Linux) for
config, logs, and user-downloaded models.

## Build prerequisites

You **must build on the target OS** — PyInstaller doesn't cross-compile.

- **macOS**: Xcode command-line tools, Python 3.10+
- **Windows**: Python 3.10+ from python.org, optionally
  [Inno Setup](https://jrsoftware.org/isinfo.php) for the installer EXE
- **Linux**: `python3.10+`, `python3-venv`, `curl` (for AppImage tool)

## Building

From the project root:

```bash
# macOS
bash installer/macos/build.sh
# optional: PORTAIOS_MAKE_DMG=1 bash installer/macos/build.sh
# optional: PORTAIOS_SIGN_IDENTITY="Developer ID Application: Name" bash installer/macos/build.sh

# Windows
installer\windows\build.bat
# optional: set PORTAIOS_MAKE_INSTALLER=1 && installer\windows\build.bat

# Linux
bash installer/linux/build.sh
# optional: PORTAIOS_MAKE_APPIMAGE=1 bash installer/linux/build.sh
```

Output lands in `dist/`.

## What's bundled

**Included by default:** `eel`, `bottle`, `websockets`, `numpy`, `psutil`,
`GPUtil`, `soundfile`, plus your `web/`, `assets/`, `models/`, kernel code.

**Excluded by default:** `TTS`, `torch`, `pyaudio`, `PyQt6`, `opencv-python` —
these add 1–2 GB and are optional since the UI falls back to the browser's
Web Speech API. Set `PORTAIOS_INCLUDE_TTS=1` to include them.

## Code signing

### macOS (Gatekeeper)

Unsigned apps trigger "cannot be opened because the developer cannot be
verified" on other Macs. Options:

1. **Sign + notarize** (for public distribution): set
   `PORTAIOS_SIGN_IDENTITY` to your Developer ID cert, then manually
   notarize with `xcrun notarytool` — requires a paid Apple Developer
   account ($99/year).
2. **Tell users to right-click → Open** on first launch — acceptable for
   trusted internal distribution.

### Windows (SmartScreen)

Unsigned `.exe` installers show "Windows protected your PC" warning.
Users click "More info → Run anyway." A real code-signing cert from a
CA removes this; self-signed certs don't help.

### Linux

No signing infrastructure. AppImage just works.

## Troubleshooting

- **Bundle is huge (>500 MB)**: you probably set `PORTAIOS_INCLUDE_TTS=1`.
  `torch` alone is ~800 MB. Only include if your users actually need
  server-side TTS.
- **"Module not found" at runtime**: add the module to `hiddenimports` in
  `installer/PortAIOS.spec`.
- **macOS app won't open, no error**: check
  `~/Library/Application Support/PortAIOS/portaios.log`.
- **Windows build fails on `bottle-websocket`**: install
  `Microsoft C++ Build Tools` — some deps compile from source.

## File layout

```
installer/
├── launcher.py              # PyInstaller entry point
├── first_run.py             # user data dir setup
├── PortAIOS.spec            # shared PyInstaller spec
├── requirements-build.txt   # build-time deps
├── icons/
│   ├── generate_icons.sh    # regenerates icons from one source PNG
│   ├── PortAIOS.icns        # macOS
│   ├── PortAIOS.ico         # Windows
│   └── PortAIOS.png         # Linux
├── macos/build.sh
├── windows/build.bat
├── windows/installer.iss    # Inno Setup script
└── linux/build.sh
```
# Voice Keyboard Commands Integration Summary

## ✅ Completed Implementation

### 1. Backend Module (`kernel/voice_keyboard_commands.py`)
- ✅ Complete keyboard key mappings (100+ keys)
- ✅ Microsoft speech grammar compatibility
- ✅ NATO phonetic alphabet support
- ✅ Three command modes: Keyboard, Annotation, Dictation
- ✅ Pattern-based command parsing
- ✅ Modifier key combinations (Ctrl+C, Alt+F4, etc.)
- ✅ Key repetition support (press space 5 times)
- ✅ Direct text typing
- ✅ Eel backend integration

### 2. Frontend Controller (`web/voice-keyboard-controller.js`)
- ✅ VoiceKeyboardController class
- ✅ Visual feedback system with overlays
- ✅ Annotation UI panel (right side)
- ✅ Dictation display panel (bottom center)
- ✅ Mode indicator badge (top center)
- ✅ Keyboard event simulation
- ✅ Client-side command fallback
- ✅ Real-time status updates

### 3. Integration Points
- ✅ `kernel/onboarding_gui.py` - Eel setup integration
- ✅ `web/avatar-integration.html` - Full avatar mode integration
- ✅ `web/index-dynamic-avatar.html` - Dynamic avatar mode integration
- ✅ Both modes process keyboard commands before other commands

### 4. Testing & Documentation
- ✅ Comprehensive test suite (`web/test-voice-keyboard-commands.html`)
- ✅ Complete documentation (`docs/VOICE_KEYBOARD_COMMANDS.md`)
- ✅ Quick reference guide (`web/VOICE_COMMANDS_QUICK_REFERENCE.md`)
- ✅ Inline code comments throughout
- ✅ Module unit test verified

## 🎯 Features Implemented

### Keyboard Control
- ✅ Single key press (press enter, press a, press escape)
- ✅ Key combinations (press control plus c)
- ✅ Multiple modifiers (press control plus shift plus escape)
- ✅ Key repetition (press space 5 times)
- ✅ Direct typing (type hello world)
- ✅ Phonetic alphabet (press alpha = A)
- ✅ Hold/release modifiers (hold shift, release shift)
- ✅ Arrow keys, function keys, numpad
- ✅ All punctuation and special characters

### Annotation System
- ✅ Add annotations via voice
- ✅ Visual annotation panel
- ✅ Show/hide annotations
- ✅ Clear all annotations
- ✅ Text highlighting
- ✅ Timestamp tracking

### Dictation Mode
- ✅ Natural language transcription
- ✅ Voice punctuation (period, comma, etc.)
- ✅ Line breaks (new line, new paragraph)
- ✅ Dictation buffer management
- ✅ Insert dictation into active field
- ✅ Clear buffer
- ✅ Word and character count display

### Visual Feedback
- ✅ Color-coded mode badges
- ✅ Animated feedback overlays
- ✅ Key combination displays
- ✅ Annotation list UI
- ✅ Dictation buffer preview
- ✅ Real-time status updates

## 📁 Files Created/Modified

### New Files (3)
```
kernel/voice_keyboard_commands.py              # Backend command processor
web/voice-keyboard-controller.js               # Frontend controller
web/test-voice-keyboard-commands.html          # Test suite
docs/VOICE_KEYBOARD_COMMANDS.md                # Full documentation
web/VOICE_COMMANDS_QUICK_REFERENCE.md          # Quick guide
```

### Modified Files (3)
```
kernel/onboarding_gui.py                       # Added Eel integration
web/avatar-integration.html                    # Integrated keyboard commands
web/index-dynamic-avatar.html                  # Integrated keyboard commands
```

## 🎤 Voice Command Examples

### Keyboard
```
press enter
press control plus c
press shift plus a
press control plus shift plus escape
press space 5 times
type hello world
press alpha
```

### Annotation
```
enter annotation mode
annotate this is important
add annotation review later
show annotations
highlight key points
clear annotations
```

### Dictation
```
enter dictation mode
start dictation
This is a test sentence period
New line
Another sentence here period
stop dictation
insert dictation
```

## 🔧 Technical Architecture

```
Voice Input (Browser/Microphone)
    ↓
AI*OS Voice Processing
    ↓
VoiceKeyboardController.processCommand()
    ↓
    ├─ Backend: process_keyboard_voice_command() [via Eel]
    │      ↓
    │  VoiceKeyboardCommands (Python)
    │      ↓
    │  Pattern matching & parsing
    │      ↓
    │  Return action object
    │
    └─ Frontend: processCommandLocal() [fallback]
           ↓
       Pattern matching (JavaScript)
           ↓
       Return action object
    ↓
executeAction()
    ↓
    ├─ simulateKeyPress() → DOM KeyboardEvent
    ├─ typeText() → Document.execCommand
    ├─ addAnnotation() → UI panel update
    └─ appendDictation() → Buffer update
    ↓
Visual Feedback (overlays, badges, panels)
```

### Test URL
```
http://localhost:8080/test-voice-keyboard-commands.html
```

### Quick Test Commands
```python
# Backend test
python3 -c "from kernel.voice_keyboard_commands import VoiceKeyboardCommands; kb = VoiceKeyboardCommands(); print(kb.process_command('press enter'))"
```

## 🚀 Usage in AI*OS

### Avatar Integration Mode
1. Open `avatar-integration.html`
2. Say "Hey AI*OS"
3. Say any keyboard command
4. Command is processed automatically
5. Visual feedback appears

### Dynamic Avatar Mode
1. Open `index-dynamic-avatar.html`
2. Say "Hey AIOS"
3. Say any keyboard command
4. Command is processed automatically
5. Visual feedback appears

| Voice Command | Action |
|--------------|--------|
| `exit` | Shutdown PortAIOS |
| `quit` | Shutdown PortAIOS |
| `close` | Shutdown PortAIOS |
| `shutdown PortAIOS` | Shutdown PortAIOS |
| `exit PortAIOS` | Shutdown PortAIOS |
| `shutdown system` | Shutdown PortAIOS |
| `turn off application` | Shutdown PortAIOS |
| `close application` | Shutdown PortAIOS |

### System Control Commands
Control your computer with voice:

| Voice Command | Action |
|--------------|--------|
| `sleep` | Put computer to sleep |
| `put computer to sleep` | Put computer to sleep |
| `lock screen` | Lock your screen |
| `lock my computer` | Lock your screen |
| `log out` | Log out of your account |
| `logout` | Log out of your account |

---

## 🎉 NEW: Multimodal AI System

PortAIOS now includes a **complete multimodal interaction system** with:

### ✨ Features

- **🖐️ Gesture Control** - Hand, face, and eye tracking using MediaPipe
- **🧠 AI Learning** - Learns your behavior and predicts actions
- **🔀 Multimodal Fusion** - Combines voice + gesture + gaze
- **🔒 Privacy First** - 100% local processing, no cloud
- **30+ Gestures** - Comprehensive gesture library

### 🚀 Quick Start

```bash
# Install multimodal dependencies
pip install -r requirements_gui.txt

# Run PortAIOS
python run_onboarding.py

# Click "✋ Enable Gesture Control" button
# Grant camera permissions
# Start using gestures!
```

### 📖 Documentation

- **Quick Start:** [`QUICKSTART_MULTIMODAL.md`](QUICKSTART_MULTIMODAL.md)
- **Complete Guide:** [`docs/MULTIMODAL_SYSTEM_COMPLETE.md`](docs/MULTIMODAL_SYSTEM_COMPLETE.md)

### 🎯 Example Gestures

| Gesture | Action |
|---------|--------|
| 👍 Thumbs Up | Confirm |
| 👉 Pointing | Click/Select |
| ⬆️ Swipe Up | Scroll Up |
| 👋 Wave | Switch Window |
| 😊 Smile | Screenshot |

**Try multimodal commands:**
- Say "Open that file" + Point at file
- Say "Delete this" + Point at item
- Say "Yes" OR give thumbs up

---

## Platform Compatibility

| Feature | macOS | Windows | Linux |
|---------|-------|---------|-------|
| Shutdown PortAIOS | ✅ | ✅ | ✅ |
| Sleep | ✅ | ✅ | ✅ |
| Lock Screen | ✅ | ✅ | ✅ |
| Logout | ⚠️ Requires confirmation | ✅ | ✅ |


## 📊 Statistics

- **Supported Keys**: 100+
- **Command Patterns**: 15+
- **Modes**: 3 (Keyboard, Annotation, Dictation)
- **Visual Components**: 5

## 🎯 Integration Points Verified

✅ Both avatar modes process keyboard commands in `processCmd()` / `processVoiceCommand()`
✅ Keyboard commands have priority (checked first)
✅ Visual feedback works in both modes
✅ Backend integration via Eel confirmed
✅ Client-side fallback functional
✅ Mode switching operational
✅ All UI components render correctly

## 🔐 Security Notes

- Keyboard events are simulated in browser context only
- No system-level keyboard control
- Commands sandboxed to web page
- Backend processing is optional
- Works offline with client-side fallback

## 🛠️ Troubleshooting

- Ensure `python3 server.py` is running
- Check browser console for errors
- Try different commands
- Verify visual feedback works


## 🎉 Ready for Use

The voice keyboard commands system is fully integrated and ready to use in both AIOS avatar modes. Users can now control keyboard input, add annotations, and dictate text entirely by voice using natural Microsoft-compatible speech commands.

**Status**: ✅ COMPLETE
**Version**: 1.0.0
**Date**: 2026-05-21
**Compatibility**: AIOS Neural Interface v2.0

---

**To use:**
1. Start AIOS (`python3 server.py`)
2. Open avatar mode (either version)
3. Say "Hey AI*OS press enter" or any command
4. Watch the visual feedback
5. Try annotation and dictation modes

**To test:**
1. Open `/test-voice-keyboard-commands.html`
2. Click test buttons or type commands
3. Verify visual feedback and logging

**To test on real hardware:**
1. Open `/test-voice-keyboard-commands.html`
2. Click test buttons or type commands
3. Verify visual feedback and logging

**To shutdown:**
1. Open avatar mode (either version)
2. Say "Hey AI*OS shutdown PortAIOS" or any shutdown command
3. Watch the visual feedback
4. Confirm shutdown

# PortAIOS Voice Commands - Shutdown & System Control

## Quick Reference

### Exit/Shutdown Commands
Use these commands to gracefully shut down PortAIOS:

| Command | Action |
|---|---|
| `exit` / `quit` / `close` | Shut down PortAIOS (with confirmation) |
| `shutdown PortAIOS` | Shut down PortAIOS (with confirmation) |
| `restart PortAIOS` | Restart PortAIOS (with confirmation) |
| `shutdown in 5 minutes` | Schedule shutdown in 5 minutes |
| `restart in 10 minutes` | Schedule restart in 10 minutes |
| `cancel shutdown` | Cancel any pending scheduled shutdown |
| `sleep` | Put computer to sleep |
| `hibernate` | Hibernate computer (with confirmation) |
| `lock screen` | Lock the screen immediately |
| `log out` | Log out (with confirmation) |

## How to Use

1. **Start PortAIOS** with voice commands enabled
2. **Speak clearly** using any of the commands above
3. **Wait for confirmation** - destructive commands show a dialog before executing

## Examples

### Shutting Down PortAIOS
```
User: "exit"
PortAIOS: [confirmation dialog] "Are you sure you want to shutdown PortAIOS?"
User: Yes
PortAIOS: "Shutting down PortAIOS"
[System shuts down gracefully]
```

### Scheduled Shutdown
```
User: "shutdown in 5 minutes"
PortAIOS: "I'll shutdown in 5 minutes"
[5 minutes later: system shuts down automatically]

User: "cancel shutdown"
PortAIOS: "Scheduled action cancelled"
```

### Putting Computer to Sleep
```
User: "sleep"
PortAIOS: "Putting computer to sleep"
[Computer enters sleep mode]
```

### Locking Screen
```
User: "lock screen"
PortAIOS: "Locking screen"
[Screen locks immediately]
```


## Technical Details

### Implementation
- Voice commands are processed by `kernel/ui_voice_commands.py`
- System power commands are executed by `_run_system_power_command()` (platform-aware)
- Application shutdown uses `_graceful_app_shutdown()` — stops minikernel first, then eel
- Scheduled shutdown uses `ScheduledShutdownManager` with `threading.Timer` and cancellation
- Confirmation dialogs are handled by `web/confirmation-dialog.js` via `window.showConfirmation()`

### Pattern Matching
Commands use regex pattern matching with priority ordering:
- Scheduled shutdown patterns (`shutdown in N minutes`) are checked **first**
- Cancel scheduled shutdown patterns come next
- Plain shutdown/restart/logout require a confirmation dialog before executing
- `sleep` and `lock_screen` execute immediately without confirmation

### Safety Features
- Graceful cleanup on exit (minikernel stops before eel exits)
- Confirmation dialogs for all destructive operations (shutdown, restart, hibernate, logout)
- Scheduled shutdown with countdown and cancellation support
- Proper signal handling (SIGINT, SIGTERM)
- Process cleanup for avatar bridge and subprocesses
- Platform-aware power management (macOS pmset, Linux systemd, Windows shutdown.exe)

## Troubleshooting

### Command Not Recognized
- Speak clearly and avoid background noise
- Use one of the exact phrases listed above
- Check that voice input is working (test with other commands)

### System Not Shutting Down
- Check the console logs for error messages
- Verify the confirmation dialog appeared and was accepted
- Ensure proper permissions for system commands (sleep, lock, logout)

### Voice Input Not Working
- Check microphone permissions
- Verify voice input system is initialized
- Test with simple commands first (e.g., "help")

### Scheduled Shutdown Not Firing
- Check that no cancel command was issued
- Verify timer was acknowledged ("I'll shutdown in N minutes")
- Check Python logs for ScheduledShutdownManager errors

## Related Files
- `kernel/ui_voice_commands.py` - Main voice command handler + power management
- `web/confirmation-dialog.js` - Confirmation dialog UI
- `kernel/onboarding_gui.py` - Shutdown/cleanup functions + minikernel bridge
- `server.py` - WebSocket server with improved error handling
- `test_shutdown_fixes.py` - Test suite for shutdown functionality

## Future Enhancements

- [x] Implement system restart functionality (graceful minikernel-aware restart)
- [x] Add confirmation prompts for destructive actions (shutdown, restart, hibernate, logout)
- [x] Support for scheduled shutdown (e.g., "shutdown in 5 minutes") with cancellation
- [x] Integration with system power management settings (pmset, systemd, Windows shutdown.exe)

---

## Architecture Notes

Creating an AI-based, voice-controlled, lightweight kernel, that is able to compete with the functionality of Linux, macOS, or Windows while remaining lightweight and voice-driven, the system cannot rely on a traditional GUI-first paradigm. Instead, it must utilize an LLM-as-an-Interface architecture.

Here is the architectural breakdown of what such a system needs to perform standard OS tasks.
1. The Core Kernel Architecture (The Foundation)

To remain lightweight, the kernel must be modular and focused on Direct Hardware Abstraction.

    Microkernel Design: Unlike the monolithic Linux kernel, a microkernel (like seL4 or Minix) is better here. It keeps the kernel minimal, running only essential services (IPC, scheduling, memory management) in kernel space, while everything else (drivers, file systems, the AI agent) runs in user space.

    The "Intent Engine" (The Bridge): This is the heart of my system. It is a translation layer that sits between the LLM and the Kernel API.

        How it works: The LLM parses natural language (e.g., "Find the file I downloaded yesterday and move it to the work folder") and converts it into a structured Intermediate Representation (IR), such as a JSON-based command, which the Kernel then executes via a System Call.

2. The AI Stack (The "Brain")

Since I require a small, quantized LLM (e.g., Llama-3-8B or Mistral-7B, quantized to 4-bit or 3-bit), it must be optimized.

    Local Inference Engine: Use highly optimized libraries like llama.cpp or ExecuTorch (by PyTorch) to run the LLM on minimal RAM.

    Context Management (RAG): The AI cannot "remember" everything. It needs a Retrieval-Augmented Generation (RAG) system.

        When a user asks a question, the system searches a local vector database (like ChromaDB or FAISS) that contains indexes of file structures, system settings, and documentation. This keeps the LLM "smart" without needing a massive parameter count.

    Voice-to-Intent Pipeline:

        STT (Speech-to-Text): Use a lightweight, local model like Whisper.cpp.

        TTS (Text-to-Speech): Use a high-quality, lightweight engine like Piper TTS.

3. Essential OS Services (Voice-Enabled)

To match Linux/Windows/Mac functionality, the AI must have "Agentic" access to these subsystems:

    File System Management: The AI needs a "FileSystem API" tool. Instead of browsing folders, the AI maintains a searchable database of file metadata (tags, content summaries, paths).

    Process Management: The AI needs the ability to:

        List processes (os.list_processes())

        Kill unresponsive tasks (os.terminate(process_id))

        Allocate memory/CPU priority via voice ("Prioritize this compilation task").

    Package/Software Management: A system like apt or brew but controlled by AI. The AI should be able to:

        "Download and install a text editor." (AI searches repos, validates dependencies, installs).

        "Update all my applications."

4. The "Agentic" Security Model

This is the most critical part. Granting an LLM root/admin access to your system is dangerous.

    Tool-Use Sandboxing: The LLM should not execute code directly. It should output a command, which is then passed to a Validator Module.

    Confirmation Loop: For "destructive" commands (e.g., rm -rf, format drive), the system must implement a mandatory human-in-the-loop verification via voice ("Are you sure you want to delete all files in Documents?").

    Capability-Based Security: The AI agent should only have permissions to the specific folders or processes it is currently working on, rather than global root access.

5. Challenges to Overcome

    Latency: The gap between saying a command and the action. This requires Stream-processing, where the command is executed as the sentence is being parsed, rather than waiting for the entire sentence to finish.

    Context Switching: Managing multiple windows or background tasks via voice requires the AI to maintain a "State Machine" of the user's focus.

    Hardware Compatibility: To be like Linux, you need drivers. An AI OS might need a "Translation Layer" that allows it to use existing Linux drivers to ensure it works with modern hardware.

Summary Checklist for Development
Component	Technology/Approach
Kernel	Microkernel (seL4 or custom Rust-based)
Inference	llama.cpp (Quantized GGUF models)
Voice	Whisper.cpp (STT) + Piper (TTS)
Search	Vector Database (SQLite + Vector Extension)
Interface	CLI-to-Voice Wrapper (Executes CLI commands)
