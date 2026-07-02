# MiniKernel Quick Start Guide

## What is MiniKernel?

MiniKernel is a lightweight, AI-first, voice-controlled operating system that demonstrates how an LLM can serve as the primary interface layer. Instead of GUI windows and CLI commands, you interact with your system through natural language.

## Installation

### 1. Prerequisites

```bash
# Python 3.8+ required
python3 --version

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-dev

# macOS
brew install portaudio
```

### 2. Install MiniKernel

```bash
cd minikernel

# Install dependencies
pip install -r requirements.txt

# Optional: Install LLM support
pip install llama-cpp-python

# Optional: Download a quantized model
# wget https://huggingface.co/.../llama-3-8b-q4.gguf -P models/
```

## Running MiniKernel

### Text Mode (Recommended for First Run)

```bash
python3 boot.py --mode text --log-level INFO
```

You'll see:
```
  __  __ _       _ _  __                    _ 
 |  \/  (_)_ __ (_) |/ /___ _ __ _ __   ___| |
 | |\/| | | '_ \| | ' // _ \ '__| '_ \ / _ \ |
 | |  | | | | | | | . \  __/ |  | | | |  __/ |
 |_|  |_|_|_| |_|_|_|\_\___|_|  |_| |_|\\___|_|

  AI-First Voice-Controlled Operating System
======================================================================

Kernel State: running
Services Running: 6
Memory: 0.0 MB allocated
AI Agent Capabilities: 3
  - file:read (scope: *)
  - process:list (scope: *)
  - system:info (scope: *)

======================================================================
Text Mode Active
======================================================================

Type commands or 'exit' to quit

minikernel> 
```

### Voice Mode (Requires Microphone)

```bash
python3 boot.py --mode voice --confirmation voice
```

## Example Commands

### Text Mode Examples

```bash
# File operations
minikernel> find files modified yesterday
minikernel> list all files in documents
minikernel> search for python files

# Process management
minikernel> list all processes
minikernel> show me memory usage
minikernel> show system status

# Package management
minikernel> install vim

# Exit
minikernel> exit
```

### Voice Mode Examples

Just speak naturally:

- "Find the file I downloaded yesterday"
- "List all running processes"
- "Show me memory usage"
- "Install Python packages"
- "What's the system status?"

## How It Works

### 1. Intent Parsing

Your command goes through pattern matching:

```
"find the file I downloaded yesterday"
  ↓
Intent: FILE_OPERATION
Action: find
Parameters: {
  query: "file",
  time_filter: {days_ago: 1}
}
Confidence: 0.9
```

### 2. Validation

The validator checks safety:

```
Risk Level: SAFE (read-only operation)
Requires Confirmation: No
```

### 3. Execution

The command is executed safely:

```
✓ Searching for 'file' modified in last 1 day...
Found 3 files
```

## Safety Features

### 1. Command Validation

Dangerous commands are blocked:

```bash
minikernel> delete /etc/passwd
✗ Invalid command: Cannot delete protected path: /etc/passwd
```

### 2. Confirmation for Risky Operations

Destructive operations require confirmation:

```bash
minikernel> delete myfile.txt
==============================================================
CONFIRMATION REQUIRED
==============================================================
Prompt: Delete 'myfile.txt'?
Command: delete myfile.txt
Risk Level: MEDIUM
==============================================================
Confirm? (yes/no): yes
✓ Would delete 'myfile.txt'
```

### 3. Capability-Based Security

The AI agent only has specific permissions:

- ✓ READ files anywhere
- ✓ LIST processes
- ✓ VIEW system info
- ✗ DELETE files (requires explicit grant)
- ✗ KILL processes (requires explicit grant)
- ✗ INSTALL packages (requires confirmation)

## Testing

### Run the Test Suite

```bash
cd minikernel
pytest tests/test_minikernel.py -v
```

Expected output:
```
tests/test_minikernel.py::TestMicrokernel::test_kernel_creation PASSED
tests/test_minikernel.py::TestMicrokernel::test_service_registration PASSED
tests/test_minikernel.py::TestMicrokernel::test_kernel_boot PASSED
tests/test_minikernel.py::TestIntentParser::test_file_find PASSED
tests/test_minikernel.py::TestIntentParser::test_process_kill PASSED
tests/test_minikernel.py::TestCommandValidator::test_safe_command PASSED
tests/test_minikernel.py::TestCommandValidator::test_dangerous_command PASSED
tests/test_minikernel.py::TestCapabilityManager::test_agent_registration PASSED
...
```

## Architecture Overview

```
Voice/Text Input
      ↓
Intent Parser (Natural Language → Structured Intent)
      ↓
Validator (Safety Checks)
      ↓
Confirmation Loop (If Risky)
      ↓
Execution Engine (Intent → System Calls)
      ↓
Microkernel Services
```

## Key Components

| Component | Purpose |
|-----------|---------|
| **Microkernel** | Minimal kernel (IPC, Memory, Scheduler) |
| **Intent Engine** | Translates NL → system calls |
| **AI Stack** | Voice pipeline, LLM inference |
| **Services** | FileSystem, Process, Package management |
| **Security** | Sandbox, capabilities, confirmation |

## Configuration

### Confirmation Modes

```bash
# Text confirmation (default)
python3 boot.py --confirmation text

# Voice confirmation
python3 boot.py --confirmation voice

# Auto-approve (testing only!)
python3 boot.py --confirmation auto
```

### Logging Levels

```bash
# See everything
python3 boot.py --log-level DEBUG

# Normal output
python3 boot.py --log-level INFO

# Errors only
python3 boot.py --log-level ERROR
```

## Troubleshooting

### "No module named 'kernel'"

Make sure you're running from the parent directory of minikernel:

```bash
cd /path/to/PortAIOS  # Not minikernel/
python3 minikernel/boot.py
```

### Voice not working

1. Check microphone:
```bash
# Test recording
arecord -d 3 test.wav
aplay test.wav
```

2. Verify PortAIOS voice components are installed:
```bash
pip install -r requirements_gui.txt
```

3. Try text mode first to verify the system works

### "Permission denied"

Some operations need confirmation or elevated permissions:

```bash
# Use confirmation mode
python3 boot.py --confirmation text

# Grant more capabilities (in code)
# Edit boot.py and add more capability grants
```

## What Can You Do?

### ✅ Currently Implemented

- Parse natural language commands
- Validate command safety
- Execute file operations (search, list)
- Process management (list, info)
- System monitoring (memory, CPU, disk)
- Sandbox execution
- Capability-based security
- Human-in-the-loop confirmation

### 🚧 Placeholder (Would Work with Full Implementation)

- Actual file moves/copies/deletes
- Process start/stop
- Package install/uninstall
- LLM-based intent parsing (requires model)
- Streaming voice commands

## Next Steps

1. **Run Tests**: `pytest tests/test_minikernel.py -v`
2. **Try Text Mode**: `python3 boot.py --mode text`
3. **Experiment with Commands**: Try different natural language queries
4. **Read Architecture**: See `ARCHITECTURE.md` for deep dive
5. **Try Voice Mode**: `python3 boot.py --mode voice` (if you have mic)

## Extending MiniKernel

### Add a New Command

1. Edit `intent/intent_parser.py` - add pattern
2. Edit `intent/command_validator.py` - add validation rules
3. Edit `intent/execution_engine.py` - add handler

### Add a New Service

1. Create service in `services/`
2. Register in `boot.py`
3. Set priority and dependencies

### Grant More Capabilities

Edit `boot.py` in the boot sequence:

```python
# Grant file delete capability
self.capabilities.grant_capability(
    "minikernel_ai", 
    Capability.FILE_DELETE,
    scope="/home/user/*"  # Limit to user directory
)
```

## Philosophy

MiniKernel demonstrates that:

1. **Voice can be primary interface** - Natural language is intuitive
2. **AI needs guardrails** - Validation + confirmation = safety
3. **Microkernel = modularity** - Services isolated, failures contained
4. **Capabilities > permissions** - Fine-grained, scoped access control

## Learn More

- `README.md` - Project overview
- `ARCHITECTURE.md` - Detailed architecture
- `requirements.txt` - Dependencies
- `tests/` - Test examples

## Support

This is a demonstration system showing how an AI-first OS could work. For questions or issues, review the architecture documentation and test suite.

---

**Welcome to the future of operating systems! 🚀**
