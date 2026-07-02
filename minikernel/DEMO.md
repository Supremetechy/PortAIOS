# MiniKernel Live Demonstration

## Quick Demo Script

This document shows real examples of MiniKernel in action.

## 1. Intent Parsing Examples

### Natural Language → Structured Commands

```python
from minikernel.intent.intent_parser import IntentParser

parser = IntentParser()

# Example 1: File search with time filter
intent = parser.parse("find the file I downloaded yesterday")
# Result:
# {
#   "intent_type": "file_operation",
#   "action": "find",
#   "parameters": {
#     "query": "file",
#     "time_filter": {"days_ago": 1}
#   },
#   "confidence": 0.9
# }

# Example 2: Process control
intent = parser.parse("kill chrome")
# Result:
# {
#   "intent_type": "process_control",
#   "action": "stop",
#   "parameters": {
#     "process": "chrome",
#     "force": True
#   },
#   "confidence": 0.9
# }

# Example 3: Package management
intent = parser.parse("install vim")
# Result:
# {
#   "intent_type": "package_management",
#   "action": "install",
#   "parameters": {
#     "package": "vim"
#   },
#   "confidence": 0.9
# }
```

## 2. Security Validation Examples

### Risk Assessment in Action

```python
from minikernel.intent.command_validator import CommandValidator

validator = CommandValidator()

# SAFE: Read-only operation
intent = parser.parse("list all files")
validation = validator.validate(intent)
# → Valid: True
# → Risk: SAFE
# → Confirmation: Not required

# BLOCKED: Protected path
intent = parser.parse("delete /etc/passwd")
validation = validator.validate(intent)
# → Valid: False
# → Risk: CRITICAL
# → Error: "Cannot delete protected path"

# REQUIRES CONFIRMATION: User file deletion
intent = parser.parse("delete myfile.txt")
validation = validator.validate(intent)
# → Valid: True
# → Risk: MEDIUM
# → Confirmation: Required
# → Prompt: "Delete 'myfile.txt'?"
```

## 3. Capability-Based Security

### Scoped Permissions Example

```python
from minikernel.security.capability_manager import CapabilityManager, Capability

# Create manager and agent
cap_mgr = CapabilityManager()
agent = cap_mgr.register_agent("ai_assistant", "AI Assistant")

# Grant READ access to user files only
cap_mgr.grant_capability(
    "ai_assistant",
    Capability.FILE_READ,
    scope="/home/user/*"
)

# Grant PROCESS_LIST globally
cap_mgr.grant_capability(
    "ai_assistant",
    Capability.PROCESS_LIST,
    scope="*"
)

# Check permissions
cap_mgr.check_capability("ai_assistant", Capability.FILE_READ, "/home/user/doc.txt")
# → True ✓

cap_mgr.check_capability("ai_assistant", Capability.FILE_READ, "/etc/passwd")
# → False ✗ (outside scope)

cap_mgr.check_capability("ai_assistant", Capability.FILE_DELETE, "/home/user/doc.txt")
# → False ✗ (no DELETE capability)
```

## 4. Full Command Flow

### End-to-End Example: "delete report.pdf"

```python
# User command (voice or text)
command = "delete report.pdf"

# Step 1: Parse intent
intent = parser.parse(command)
# → FILE_OPERATION, delete, {target: "report.pdf"}

# Step 2: Validate
validation = validator.validate(intent)
# → Valid: True
# → Risk: MEDIUM
# → Requires confirmation: True

# Step 3: Check capabilities
has_permission = cap_mgr.check_capability(
    "ai_assistant",
    Capability.FILE_DELETE,
    "report.pdf"
)
# → Depends on granted capabilities

# Step 4: Request confirmation
from minikernel.security.confirmation_loop import ConfirmationLoop, ConfirmationMode

confirmation = ConfirmationLoop(mode=ConfirmationMode.TEXT)
confirmed = confirmation.request_confirmation(
    "Delete 'report.pdf'?",
    command,
    "medium"
)
# User prompted: "Delete 'report.pdf'? (yes/no)"
# User responds: "yes"
# → True

# Step 5: Execute (if all checks pass)
from minikernel.intent.execution_engine import ExecutionEngine

executor = ExecutionEngine(kernel=kernel)
result = executor.execute(intent, validation, confirmed=True)
# → Success: True
# → Output: "File deleted"
```

## 5. Microkernel Boot Sequence

### System Initialization

```python
from minikernel.core.microkernel import MicroKernel, ServicePriority
from minikernel.core.ipc_manager import IPCManager
from minikernel.core.memory_manager import MemoryManager
from minikernel.core.process_scheduler import ProcessScheduler

# Create kernel
kernel = MicroKernel()

# Register critical services
kernel.register_service("ipc", IPCManager(), ServicePriority.CRITICAL)
kernel.register_service("memory", MemoryManager(), ServicePriority.CRITICAL)
kernel.register_service("scheduler", ProcessScheduler(), ServicePriority.HIGH)

# Boot (services start in priority order)
kernel.boot()
# Output:
# ============================================================
# MiniKernel Boot Sequence Starting
# ============================================================
# ✓ Started service: ipc
# ✓ Started service: memory
# ✓ Started service: scheduler
# ============================================================
# ✓ MiniKernel boot complete
# ✓ 3 services running
# ============================================================

# Get stats
stats = kernel.get_stats()
print(f"Uptime: {stats['uptime_seconds']:.1f}s")
print(f"Services: {stats['services']}")
print(f"Memory: {stats['memory_mb']:.1f} MB")
```

## 6. Interactive Session Example

### Text Mode Session

```
$ python3 minikernel/boot.py --mode text

======================================================================
  __  __ _       _ _  __                    _ 
 |  \/  (_)_ __ (_) |/ /___ _ __ _ __   ___| |
 | |\/| | | '_ \| | ' // _ \ '__| '_ \ / _ \ |
 | |  | | | | | | | . \  __/ |  | | | |  __/ |
 |_|  |_|_|_| |_|_|_|\_\___|_|  |_| |_|\___|_|

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

minikernel> find files modified yesterday
✓ Searching for 'files' modified in last 1 day...

minikernel> list all processes
✓ Listing processes...

minikernel> show memory usage
✓ Memory: 0.0 MB allocated, 4096.0 MB total

minikernel> delete important.txt
==============================================================
CONFIRMATION REQUIRED
==============================================================
Prompt: Delete 'important.txt'?
Command: delete important.txt
Risk Level: MEDIUM
==============================================================
Confirm? (yes/no): no
✗ Command cancelled by user

minikernel> show system status
✓ {
  "state": "running",
  "uptime_seconds": 42.5,
  "syscalls": 15,
  "services": 6,
  "memory_mb": 0.0,
  "processes": 0
}

minikernel> exit

======================================================================
Shutting down...
======================================================================
✓ MiniKernel halted
```

## 7. Voice Mode Example (Conceptual)

### Voice Interaction Flow

```
[System boots]
System (speaks): "MiniKernel ready. Listening for commands."

[User speaks]: "Find the file I downloaded yesterday"
System (processes): Parsing... validating... executing...
System (speaks): "Found 3 files. The most recent is report.pdf."

[User speaks]: "Delete it"
System (speaks): "Delete report.pdf? Say yes to confirm or no to cancel."

[User speaks]: "Yes"
System (processes): Executing deletion...
System (speaks): "Done. Report.pdf has been deleted."

[User speaks]: "Show me memory usage"
System (speaks): "Memory usage is 100 megabytes allocated out of 4 gigabytes total."

[User speaks]: "Install Python"
System (speaks): "Install package Python? Say yes to confirm."

[User speaks]: "Yes"
System (processes): Running package manager...
System (speaks): "Installing... This may take a moment."
System (speaks): "Done. Python has been installed."

[User speaks]: "Exit"
System (speaks): "Shutting down MiniKernel. Goodbye."
```

## 8. Streaming Parser Example

### Low-Latency Command Processing

```python
from minikernel.ai.streaming_parser import StreamingParser

def execute_command(cmd):
    print(f"EXECUTING: {cmd}")

parser = StreamingParser(
    confidence_threshold=0.75,
    execute_callback=execute_command
)

# Simulate words arriving from STT
words = ["find", "the", "file", "I", "downloaded"]

for word in words:
    result = parser.process_word(word)
    # After "find" → 70% confidence (not enough)
    # After "the" → 75% confidence (threshold reached!)
    # → EXECUTES: "find the"
    # No need to wait for complete sentence!
```

## 9. Security Sandbox Example

### Safe Command Execution

```python
from minikernel.security.sandbox import Sandbox

sandbox = Sandbox()

# Safe command
result = sandbox.execute("ls", args=["-la", "/tmp"])
# → Executes successfully
# → Returns: SandboxResult(success=True, output="...")

# Blocked command (not in whitelist)
result = sandbox.execute("dangerous_command")
# → Blocked before execution
# → Returns: SandboxResult(success=False, error="Command not allowed")

# Blacklisted pattern
result = sandbox.execute("rm", args=["-rf", "/"])
# → Blocked by pattern matching
# → Returns: SandboxResult(success=False, error="Dangerous command blocked")
```

## 10. Process Service Example

### Voice-Controlled Process Management

```python
from minikernel.services.process_service import ProcessService

ps = ProcessService()
ps.initialize()

# List all processes
processes = ps.list_processes()
print(f"Total processes: {len(processes)}")

# Find a specific process
chrome = ps.find_process("chrome")
if chrome:
    print(f"Chrome PID: {chrome.pid}")
    print(f"CPU: {chrome.cpu_percent}%")
    print(f"Memory: {chrome.memory_mb:.1f} MB")

# Kill a process
success = ps.kill_process("chrome")
print(f"Killed chrome: {success}")

# Get system stats
stats = ps.get_system_stats()
print(f"Total processes: {stats['total_processes']}")
print(f"CPU usage: {stats['cpu_usage_percent']:.1f}%")
print(f"Memory usage: {stats['memory_usage_percent']:.1f}%")
```

## Key Takeaways

1. **Natural Language Works**: Commands parse accurately
2. **Security is Strong**: 4-layer validation prevents harm
3. **Latency is Low**: Streaming reduces wait time
4. **Modularity Wins**: Each component independent and testable
5. **Voice is Viable**: Primary interface is feasible

## Try It Yourself

```bash
# Start in text mode
python3 minikernel/boot.py --mode text

# Run tests
pytest minikernel/tests/test_minikernel.py -v

# Read architecture
cat minikernel/ARCHITECTURE.md
```

---

**MiniKernel proves that AI-first, voice-controlled operating systems are not science fiction—they're achievable today!** 🚀
