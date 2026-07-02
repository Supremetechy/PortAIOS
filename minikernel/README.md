# MiniKernel - AI-First Voice-Controlled Operating System

## Overview

MiniKernel is a lightweight, AI-driven operating system designed to compete with traditional OS functionality (Linux, macOS, Windows) while maintaining a **voice-first, LLM-as-an-Interface** architecture. Unlike GUI-centric systems, MiniKernel treats the AI as the primary interaction layer.

## Architecture Principles

### 1. **Microkernel Foundation**
- Minimal kernel running only essential services (IPC, scheduling, memory)
- Everything else runs in user space for security and modularity
- Inspired by seL4, Minix, and modern microkernel designs

### 2. **LLM-as-an-Interface**
- Natural language is the primary interface
- Intent Engine translates voice → structured commands → kernel API
- No dependency on traditional GUI paradigms

### 3. **Lightweight AI Stack**
- Quantized LLMs (Llama-3-8B, Mistral-7B at 3-4 bit)
- Optimized inference via llama.cpp / ExecuTorch
- Local execution for privacy and speed

### 4. **Agentic Security**
- Tool-use sandboxing (AI outputs commands, doesn't execute directly)
- Capability-based security model
- Human-in-the-loop for destructive operations

## Core Components

### Kernel Layer (`core/`)
- **microkernel.py** - Minimal kernel: IPC, scheduling, memory
- **ipc_manager.py** - Inter-process communication
- **memory_manager.py** - Memory allocation and paging
- **process_scheduler.py** - Process/thread scheduling

### Intent Engine (`intent/`)
- **intent_parser.py** - Natural language → Intermediate Representation
- **command_validator.py** - Safety checks and sandboxing
- **execution_engine.py** - IR → System calls

### AI Stack (`ai/`)
- **inference_engine.py** - Quantized LLM inference (llama.cpp)
- **rag_system.py** - Vector database for context (ChromaDB/FAISS)
- **voice_pipeline.py** - STT (Whisper.cpp) + TTS (Piper)
- **streaming_parser.py** - Real-time command parsing

### OS Services (`services/`)
- **filesystem_service.py** - AI-searchable file operations
- **process_service.py** - Process management via voice
- **package_service.py** - Software installation/updates
- **network_service.py** - Network configuration

### Security (`security/`)
- **sandbox.py** - Command execution sandbox
- **capability_manager.py** - Capability-based permissions
- **confirmation_loop.py** - Human-in-the-loop verification

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Kernel | Custom Python microkernel |
| Inference | llama.cpp (GGUF quantized models) |
| STT | Whisper.cpp (local) |
| TTS | Piper TTS (local) |
| Vector DB | ChromaDB / FAISS |
| Search | SQLite FTS5 + Vector extension |

## Key Features

### 1. **Voice-First Operations**
```
User: "Find the file I downloaded yesterday and move it to the work folder"
↓
Intent Engine: Parse → {action: "move", file: "recent:download:1day", dest: "/work"}
↓
Filesystem Service: Execute with confirmation
```

### 2. **Streaming Command Parsing**
- Commands execute as sentences are parsed (not after completion)
- Reduces latency from voice → action

### 3. **Context-Aware RAG**
- System maintains indexed knowledge of:
  - File structures and metadata
  - System settings and state
  - User preferences and patterns
  - Documentation and help

### 4. **Capability-Based Security**
- AI agents have scoped permissions (not root access)
- Permissions granted per-operation, not globally
- Automatic elevation requests for privileged operations

## Comparison with Traditional OS

| Feature | Traditional OS | MiniKernel |
|---------|---------------|------------|
| Primary Interface | GUI + CLI | Voice + AI |
| File Navigation | Folder browsing | Semantic search |
| Process Control | Task Manager | Voice commands |
| Software Install | Package manager GUI | "Install X" |
| Security Model | User/root | Capability-based |
| System Size | GB (kernel + userland) | MB (microkernel + AI) |

## Development Roadmap

### Phase 1: Core Infrastructure ✓
- [x] Microkernel basics
- [x] Intent Engine
- [x] Voice pipeline integration

### Phase 2: Essential Services
- [ ] Filesystem with semantic search
- [ ] Process management
- [ ] Package manager integration

### Phase 3: AI Optimization
- [ ] Model quantization pipeline
- [ ] RAG system with ChromaDB
- [ ] Streaming parser

### Phase 4: Security Hardening
- [ ] Sandbox implementation
- [ ] Capability manager
- [ ] Audit logging

### Phase 5: Hardware Support
- [ ] Driver abstraction layer
- [ ] Hardware compatibility testing
- [ ] Performance optimization

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Download models
python minikernel/setup/download_models.py

# Boot minikernel
python minikernel/boot.py
```

## Design Decisions

### Why Microkernel?
- **Modularity**: Services crash without kernel panic
- **Security**: Smaller attack surface
- **Flexibility**: Easy to swap components

### Why Local LLM?
- **Privacy**: No data leaves the device
- **Latency**: No network round-trips
- **Reliability**: Works offline

### Why Voice-First?
- **Accessibility**: Natural interaction
- **Speed**: Faster than GUI navigation for many tasks
- **Future-proof**: Voice is the interface of tomorrow

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE)

## Acknowledgments

Built on insights from PortAIOS and modern OS research.
