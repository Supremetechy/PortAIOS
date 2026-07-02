# Building MiniKernel on macOS using Docker

Since you're on **macOS** and Buildroot requires Linux, we'll use Docker to build the ISO.

## Quick Start

```bash
cd minikernel/buildroot

# Option 1: Use default configuration
./build-docker.sh

# Option 2: Configure first, then build
./configure.sh
./build-docker.sh
```

## What Happens

1. **Docker Image**: Builds Ubuntu 22.04 container with all dependencies
2. **Build Process**: Runs build.sh inside the container
3. **Output**: ISO and VDI files appear in `output/` directory

## Build Time

- **First build**: 1-2 hours (downloads and compiles everything)
- **Subsequent builds**: 5-10 minutes (incremental)

## Requirements

- ✅ Docker Desktop for Mac (you have it!)
- ✅ 10 GB free disk space
- ✅ 4 GB RAM for Docker
- ⏱️ 1-2 hours of time

## Starting the Build NOW

Ready to build? Here's what to do:

### Standard Build (Recommended)
```bash
cd minikernel/buildroot
./build-docker.sh
```

This will:
1. Build the Docker image (~5 minutes)
2. Download Buildroot (~2 minutes)
3. Compile kernel and packages (~1-2 hours)
4. Create bootable ISO
5. Create VirtualBox VDI disk

### With Configuration
```bash
cd minikernel/buildroot
./configure.sh
# Select your preferred variant
./build-docker.sh
```

## Monitoring Progress

The build will show:
- Package downloads
- Compilation progress
- Final ISO creation

You can safely:
- Let it run in background
- Close terminal (if running in tmux/screen)
- Put Mac to sleep (might slow down build)

## After Build Completes

Output files will be in `minikernel/buildroot/output/`:
- `minikernel.iso` - Bootable ISO (~400 MB)
- `minikernel-persistent.vdi` - VirtualBox disk (8 GB)
- `bzImage` - Linux kernel
- `rootfs.ext2` - Root filesystem

Then run:
```bash
./create_vm.sh
```

To automatically create and start a VirtualBox VM!

## Troubleshooting

### Docker not running
```bash
# Start Docker Desktop app
open -a Docker
# Wait for it to start, then retry
```

### Out of disk space
```bash
# Clean Docker
docker system prune -a

# Or increase Docker disk in:
# Docker Desktop → Settings → Resources → Disk limit
```

### Build interrupted
```bash
# Resume by running again
./build-docker.sh
# Buildroot will continue from where it stopped
```

## Alternative: Linux VM

If you prefer not to use Docker, you can:

1. Install a Linux VM (VirtualBox, VMware, Parallels)
2. Use Ubuntu 22.04
3. Run build.sh directly inside the VM

```bash
# Inside Linux VM
sudo apt-get install build-essential libncurses-dev rsync wget
cd /path/to/minikernel/buildroot
./build.sh
```

## Ready to Start?

Run this now:
```bash
cd ~/Desktop/PortAIOS/minikernel/buildroot
./build-docker.sh
```

Build time: ~1-2 hours. Grab a coffee! ☕
