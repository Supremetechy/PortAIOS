# MiniKernel Buildroot Configuration

This directory contains the Buildroot configuration for building a bootable MiniKernel ISO.

## Quick Start

```bash
cd minikernel/buildroot
./build.sh
```

## What Gets Built

The build process creates:

1. **minikernel.iso** - Bootable ISO for VirtualBox/QEMU
2. **minikernel-persistent.vdi** - VirtualBox persistent disk (8GB)
3. **bzImage** - Linux kernel
4. **rootfs.ext2** - Root filesystem

## Directory Structure

```
buildroot/
├── build.sh              # Main build script
├── config/
│   ├── minikernel_defconfig  # Buildroot configuration
│   ├── kernel.config         # Linux kernel configuration
│   └── isolinux.cfg          # Boot menu
├── overlay/              # Files to include in rootfs
│   ├── etc/
│   │   ├── init.d/
│   │   │   └── S99minikernel # MiniKernel startup script
│   │   ├── fstab            # Filesystem table
│   │   └── profile.d/
│   │       └── minikernel.sh # Environment setup
│   └── opt/
│       └── minikernel/      # MiniKernel source (copied during build)
├── build/                # Build artifacts (gitignored)
└── output/               # Final ISO and images
```

## Build Requirements

### Ubuntu/Debian
```bash
sudo apt-get install build-essential libncurses-dev rsync wget \
    git bc libssl-dev libelf-dev flex bison
```

### Fedora/RHEL
```bash
sudo dnf groupinstall "Development Tools"
sudo dnf install ncurses-devel rsync wget git bc openssl-devel \
    elfutils-libelf-devel flex bison
```

### macOS
```bash
brew install wget rsync gnu-tar
```

Note: Building on macOS requires a Linux VM or container.

## Build Process

### 1. Full Build
```bash
./build.sh
```

Downloads Buildroot, configures it, and builds everything (~1-2 hours first time).

### 2. Incremental Rebuild
```bash
./build.sh rebuild
```

Rebuilds without re-downloading or reconfiguring.

### 3. Clean Build
```bash
./build.sh clean
./build.sh
```

### 4. Interactive Configuration
```bash
./build.sh menuconfig
```

## Testing in VirtualBox

### Automatic Setup
```bash
cd minikernel/buildroot
./create_vm.sh
```

### Manual Setup

1. Create new VM:
   - Name: MiniKernel
   - Type: Linux
   - Version: Other Linux (64-bit)
   - Memory: 2048 MB minimum, 4096 MB recommended

2. Storage:
   - IDE Controller: Attach `output/minikernel.iso`
   - SATA Controller: Attach `output/minikernel-persistent.vdi`

3. Settings:
   - System → Enable EFI (optional)
   - Network → Adapter 1: NAT or Bridged
   - Audio → Enable Audio Output (for voice features)
   - Shared Folders → Add folder named "shared" (optional)

4. Boot order:
   - CD/DVD first
   - Hard Disk second

## Testing in QEMU

```bash
qemu-system-x86_64 \
    -cdrom output/minikernel.iso \
    -hda output/minikernel-persistent.vdi \
    -m 2048 \
    -enable-kvm \
    -device AC97 \
    -net nic -net user
```

## Architecture Components

### System Call Interface
- **Native C bridge**: `minikernel/core/native/syscall_bridge.c`
- Provides direct hardware access via `ctypes`
- Memory mapping, syscalls, and low-level operations

### Binary Compatibility Layer
- **ELF Loader**: `minikernel/core/elf_loader.py`
- Loads and executes native Linux binaries
- Intercepts syscalls and translates to microkernel API
- Similar to Wine/WSL compatibility

### Disk Persistence
- **VDI Handler**: `minikernel/core/disk_image.py`
- Manages VirtualBox .vdi disk images
- Provides persistent filesystem across reboots
- Integrated with `filesystem_service.py`

## Filesystem Layout

```
/ (root - in RAM from ISO)
├── boot/
│   └── bzImage           # Linux kernel
├── etc/
│   ├── init.d/
│   │   └── S99minikernel # Auto-starts MiniKernel
│   └── fstab             # Mounts persistent disk
├── opt/
│   └── minikernel/       # MiniKernel installation
│       ├── core/         # Microkernel
│       ├── services/     # OS services
│       ├── ai/           # AI inference
│       └── models/       # LLM models
├── mnt/
│   ├── persistent/       # VirtualBox persistent disk (mounted)
│   └── shared/           # VirtualBox shared folder
└── var/
    └── log/
        └── minikernel.log
```

## Boot Process

1. BIOS/UEFI loads ISOLINUX from ISO
2. ISOLINUX loads Linux kernel (`bzImage`)
3. Kernel boots with initrd (`rootfs.ext2`)
4. Init system starts (systemd/sysvinit)
5. `/etc/init.d/S99minikernel` runs:
   - Mounts persistent disk (`/dev/sda1` → `/mnt/persistent`)
   - Mounts shared folders
   - Starts MiniKernel microkernel
6. MiniKernel boots:
   - Loads services (filesystem, process, network)
   - Initializes AI stack (LLM, STT, TTS)
   - Starts voice interface

## Customization

### Adding Packages

Edit `config/minikernel_defconfig` and add package options:
```
BR2_PACKAGE_YOURPACKAGE=y
```

Then rebuild:
```bash
./build.sh rebuild
```

### Modifying Kernel

Edit `config/kernel.config` to add kernel features, then rebuild.

### Adding Files to Rootfs

Place files in `overlay/` directory structure. They will be copied to the root filesystem.

Example:
```bash
mkdir -p overlay/usr/local/bin
cp my_script.sh overlay/usr/local/bin/
chmod +x overlay/usr/local/bin/my_script.sh
```

## Troubleshooting

### Build Fails
- Check dependencies are installed
- Verify disk space (need ~10GB free)
- Try `./build.sh clean` then rebuild

### VM Won't Boot
- Verify BIOS/UEFI settings
- Check boot order (CD first)
- Enable VT-x/AMD-V in BIOS
- Try safe mode: Select "minikernel-safe" in boot menu

### Persistent Disk Not Mounting
- Check VirtualBox disk is attached
- Verify disk is formatted: `mkfs.ext4 /dev/sda1`
- Check `/var/log/minikernel.log` for errors

### Voice Features Not Working
- Enable audio in VirtualBox settings
- Check ALSA: `aplay -l`
- Verify microphone permissions

## Development Workflow

1. Edit MiniKernel source in `minikernel/`
2. Run `./build.sh rebuild` to update ISO
3. Test in VirtualBox
4. Iterate

For faster iteration, use VirtualBox shared folders to mount source directly.

## Performance

- **Build time (first)**: 1-2 hours
- **Build time (incremental)**: 5-10 minutes
- **ISO size**: ~300-500 MB
- **RAM usage**: 512 MB minimum, 2 GB recommended
- **Disk usage**: 8 GB persistent disk

## Next Steps

After successful build:

1. **Test boot**: Boot the ISO in VirtualBox
2. **Test persistence**: Create files, reboot, verify they persist
3. **Test voice**: Try voice commands
4. **Install packages**: Test `.deb` installation
5. **Run binaries**: Test native executable loading

## References

- [Buildroot Manual](https://buildroot.org/downloads/manual/manual.html)
- [Linux Kernel Documentation](https://kernel.org/doc/)
- [VirtualBox Manual](https://www.virtualbox.org/manual/)
