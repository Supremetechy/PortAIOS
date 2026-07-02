# MiniKernel Buildroot - Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Build the Bootable ISO

```bash
cd minikernel/buildroot
./build.sh
```

**Time**: 1-2 hours first time, 5-10 minutes for rebuilds  
**Output**: `output/minikernel.iso` and `output/minikernel-persistent.vdi`

### Step 2: Create VirtualBox VM

```bash
./create_vm.sh
```

**What it does**:
- Creates a VirtualBox VM named "MiniKernel"
- Attaches the bootable ISO
- Attaches the persistent 8GB VDI disk
- Configures 2GB RAM, 2 CPUs, audio, networking
- Starts the VM automatically

### Step 3: First Boot Setup

When the VM boots:

1. **Login**: `root` / `minikernel`
2. **Format persistent disk** (first boot only):
   ```bash
   mkfs.ext4 /dev/sda1
   ```
3. **Reboot**:
   ```bash
   reboot
   ```
4. **Use MiniKernel**:
   ```bash
   minikernel          # Voice interface
   minikernel-cli      # CLI interface
   ```

## 🎯 What You Get

✅ **Bootable ISO** - Run MiniKernel as a real operating system  
✅ **VirtualBox Integration** - Seamless VM support with guest additions  
✅ **Persistent Storage** - 8GB VDI disk for data that survives reboots  
✅ **Binary Compatibility** - Run native Linux executables and .deb packages  
✅ **System Call Interface** - Direct CPU/memory access via C bridge  
✅ **Voice Interface** - AI-first voice-controlled OS  

## 📁 What Gets Built

```
minikernel/buildroot/output/
├── minikernel.iso              # Bootable ISO (~400 MB)
├── minikernel-persistent.vdi   # Persistent disk (8 GB dynamic)
├── bzImage                     # Linux kernel
└── rootfs.ext2                 # Root filesystem
```

## 🔧 Architecture Overview

### Three Core Components

#### 1. System Call Interface
**File**: `minikernel/core/native/syscall_bridge.c`

Provides direct hardware access from Python:
```python
from minikernel.core import syscall_bridge

# Memory mapping
addr = syscall_bridge.mmap(4096, -1, PROT_READ | PROT_WRITE, MAP_ANONYMOUS)

# Direct syscalls
result = syscall_bridge.syscall(SYS_getpid)
```

#### 2. Binary Compatibility Layer
**File**: `minikernel/core/elf_loader.py`

Run native Linux binaries (like Wine/WSL):
```python
from minikernel.core.elf_loader import BinaryCompatibilityLayer

bcl = BinaryCompatibilityLayer(kernel)
loaded = bcl.load_elf('/bin/ls')
bcl.execute(loaded, ['ls', '-la'])

# Install .deb packages
bcl.install_package('package.deb')
```

#### 3. VirtualBox Disk Persistence
**File**: `minikernel/core/disk_image.py`

Manage VirtualBox .vdi disks:
```python
from minikernel.core.disk_image import DiskImage

disk = DiskImage('/path/to/minikernel-persistent.vdi')
disk.open()
disk.write_block(0, b'Persistent data')
disk.mount_filesystem('/mnt/persistent')
```

## 🎮 Usage Examples

### Voice Interface

```bash
minikernel

# Speak commands:
"List files in the home directory"
"Find all Python files"
"Show running processes"
"What is the system uptime"
```

### CLI Interface

```bash
minikernel-cli

minikernel> list files in /opt
minikernel> find files containing "test"
minikernel> show system status
minikernel> exit
```

### Installing Software

```bash
# Download a .deb package
wget http://example.com/package.deb

# Install it
minikernel-cli
minikernel> install package.deb
```

### Running Native Binaries

```bash
# From Python
python3
>>> from minikernel.core.elf_loader import BinaryCompatibilityLayer
>>> from minikernel.core.microkernel import MicroKernel
>>> kernel = MicroKernel()
>>> kernel.boot()
>>> bcl = BinaryCompatibilityLayer(kernel)
>>> loaded = bcl.load_elf('/bin/echo')
>>> bcl.execute(loaded, ['echo', 'Hello from MiniKernel!'])
```

## 🐛 Troubleshooting

### Build Fails

**Problem**: Missing dependencies

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install build-essential libncurses-dev rsync wget

# Fedora/RHEL
sudo dnf groupinstall "Development Tools"
```

### VM Won't Boot

**Problem**: VirtualBox settings

**Solution**:
1. Enable VT-x/AMD-V in BIOS
2. Check boot order (CD/DVD first)
3. Try safe mode in boot menu

### Persistent Disk Not Working

**Problem**: Disk not mounted

**Solution**:
```bash
# Check if disk is attached
lsblk

# Format it (first boot only)
mkfs.ext4 /dev/sda1

# Mount manually if needed
mount /dev/sda1 /mnt/persistent
```

### Voice Features Not Working

**Problem**: Audio not configured

**Solution**:
1. Enable audio in VirtualBox settings
2. Check ALSA: `aplay -l`
3. Test microphone: `arecord -d 5 test.wav`

## 🔄 Development Workflow

### Making Changes

1. **Edit source** in `minikernel/`
2. **Rebuild**:
   ```bash
   cd minikernel/buildroot
   ./build.sh rebuild
   ```
3. **Test** in VirtualBox
4. **Iterate**

### Fast Iteration with Shared Folders

Instead of rebuilding:

1. Set up VirtualBox shared folder
2. Mount it in VM: `/mnt/shared`
3. Edit files on host
4. Restart MiniKernel in VM:
   ```bash
   /etc/init.d/S99minikernel restart
   ```

## 📊 Performance

| Metric | Value |
|--------|-------|
| Boot time (cold) | 30-60 seconds |
| Boot time (warm) | 15-30 seconds |
| RAM usage (idle) | ~512 MB |
| RAM usage (with LLM) | ~2-4 GB |
| ISO size | ~400 MB |
| Disk size | 8 GB (dynamic) |

## 📚 Next Steps

After getting MiniKernel running:

1. **Explore voice commands** - Try natural language commands
2. **Install packages** - Test .deb installation
3. **Test persistence** - Create files, reboot, verify they persist
4. **Run binaries** - Load and execute native executables
5. **Add AI models** - Download LLMs to `/mnt/persistent/models/`

## 📖 Full Documentation

- **Architecture Details**: `minikernel/BUILDROOT_COMPLETE.md`
- **Build System**: `minikernel/buildroot/README.md`
- **MiniKernel Core**: `minikernel/README.md`
- **Architecture**: `minikernel/ARCHITECTURE.md`

## 🎯 What Makes This Unique

Traditional OS:
```
User → GUI → System Calls → Kernel → Hardware
```

MiniKernel:
```
User → Voice → LLM → Intent Parser → Microkernel → Hardware
         ↓
    Natural Language
```

**Key Differences**:
- **Voice-First**: AI is the primary interface, not an addon
- **Intent-Based**: Natural language understanding, not memorized commands
- **Microkernel**: Minimal kernel, everything else in userspace
- **Bootable**: Real OS that runs on hardware/VMs
- **Binary Compatible**: Run existing Linux software

## 🏆 Summary

You now have:

✅ A **real, bootable operating system**  
✅ That runs in **VirtualBox**  
✅ With **persistent storage**  
✅ That can **execute native binaries**  
✅ With **direct hardware access**  
✅ Controlled by **voice and AI**  

**One command to build everything**:
```bash
cd minikernel/buildroot && ./build.sh && ./create_vm.sh
```

Enjoy your AI-first operating system! 🎉
