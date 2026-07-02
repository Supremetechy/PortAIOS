# MiniKernel Build Configuration Options

## Build Variants

MiniKernel provides several pre-configured build variants:

### 1. Standard (Default)
- **Size**: ~400 MB ISO
- **RAM**: 512 MB minimum, 2 GB recommended
- **Features**: Balanced configuration with all essential features
- **Use case**: General purpose, testing, demos

```bash
./configure.sh
# Select option 1
./build.sh
```

### 2. Minimal
- **Size**: ~200 MB ISO
- **RAM**: 256 MB minimum
- **Features**: Bare minimum to boot and run MiniKernel
- **Use case**: Embedded systems, resource-constrained environments

```bash
./configure.sh
# Select option 2
./build.sh
```

**What's included:**
- Linux kernel (minimal drivers)
- Python 3 (no extra packages)
- BusyBox (basic utilities)
- MiniKernel core only

**What's excluded:**
- Development tools
- Audio support
- VirtualBox guest additions
- Extra utilities

### 3. Developer
- **Size**: ~800 MB ISO
- **RAM**: 2 GB minimum, 4 GB recommended
- **Features**: Full development environment
- **Use case**: Development, debugging, testing

```bash
./configure.sh
# Select option 3
./build.sh
```

**What's included:**
- All standard features
- GCC compiler + toolchain
- GDB, strace, valgrind
- Git, vim, nano
- Network debugging tools
- Debug symbols

**Additional tools:**
- autoconf, automake, cmake
- Python development headers
- Full ALSA audio stack
- SSH server (OpenSSH + Dropbear)

### 4. Production
- **Size**: ~300 MB ISO
- **RAM**: 512 MB minimum
- **Features**: Optimized and hardened for deployment
- **Use case**: Production deployments

```bash
./configure.sh
# Select option 4
# Edit config/variants/production_defconfig (set password hash)
./build.sh
```

**Optimizations:**
- Compiler optimization (-O3)
- Link-time optimization (LTO)
- Stack protection (SSP)
- RELRO hardening
- Stripped binaries (no debug symbols)

**Security:**
- Hardened kernel config
- Fail2ban
- iptables
- CA certificates
- No default root password (hash required)

### 5. Custom
- **Size**: Varies
- **Features**: Interactive configuration
- **Use case**: Special requirements

```bash
./configure.sh
# Select option 5
# Buildroot menuconfig will launch
```

## Build Platforms

### Linux (Native)

```bash
# Install dependencies
sudo apt-get install build-essential libncurses-dev rsync wget

# Build
cd minikernel/buildroot
./build.sh
```

**Recommended distributions:**
- Ubuntu 20.04+ / Debian 11+
- Fedora 35+ / RHEL 8+
- Arch Linux

### macOS (Docker)

```bash
# Install Docker Desktop first
# https://docs.docker.com/desktop/install/mac-install/

# Build using Docker
cd minikernel/buildroot
./build-docker.sh
```

**Requirements:**
- Docker Desktop for Mac
- 10 GB free disk space
- 4 GB RAM for Docker

### Windows (WSL2 or Docker)

**Option 1: WSL2**
```bash
# Install WSL2 with Ubuntu
wsl --install -d Ubuntu-22.04

# Inside WSL2
sudo apt-get install build-essential libncurses-dev rsync wget
cd /mnt/c/path/to/minikernel/buildroot
./build.sh
```

**Option 2: Docker**
```bash
# Install Docker Desktop
# https://docs.docker.com/desktop/install/windows-install/

# Build using Docker
cd minikernel/buildroot
./build-docker.sh
```

## Build Options

### Parallel Builds

Speed up builds by using multiple CPU cores:

```bash
# In build.sh, builds use all cores by default
make -j$(nproc)

# To limit cores (e.g., 4 cores):
make -j4
```

### Including AI Models

Include pre-downloaded LLM models in the ISO:

```bash
# Place models in models/ directory
cp your-model.gguf ../models/

# Configure
./configure.sh
# Select "Include LLM models in ISO? [y/N]" → y

# Build
./build.sh
```

**Note**: This will significantly increase ISO size (~2-4 GB per model)

### Custom Kernel Configuration

Edit kernel configuration:

```bash
# After running build.sh once
cd build/buildroot-*/output/build/linux-*
make menuconfig

# Save and rebuild
cd ../../../../..
./build.sh rebuild
```

### Custom Package Selection

Add packages to Buildroot:

```bash
# Edit your defconfig
vim config/minikernel_defconfig

# Add packages, e.g.:
# BR2_PACKAGE_HTOP=y
# BR2_PACKAGE_TMUX=y

# Rebuild
./build.sh rebuild
```

## Build Outputs

After successful build:

```
minikernel/buildroot/output/
├── minikernel.iso              # Bootable ISO
├── minikernel-persistent.vdi   # VirtualBox disk
├── bzImage                     # Kernel image
├── rootfs.ext2                 # Root filesystem
└── rootfs.tar                  # Root filesystem archive
```

## Build Times

| Configuration | First Build | Rebuild | Size |
|--------------|-------------|---------|------|
| Minimal | 45-60 min | 5 min | ~200 MB |
| Standard | 60-90 min | 5-10 min | ~400 MB |
| Developer | 90-120 min | 10-15 min | ~800 MB |
| Production | 60-90 min | 5-10 min | ~300 MB |

*Times on modern 4-core CPU with SSD*

## Advanced Options

### Cross-Compilation

Build for different architectures:

```bash
# Edit defconfig
# Change BR2_x86_64=y to:
BR2_aarch64=y  # ARM 64-bit
BR2_arm=y      # ARM 32-bit
```

### Static IP Configuration

Instead of DHCP:

```bash
# Edit overlay/etc/network/interfaces
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
```

### Additional Init Scripts

Add custom startup scripts:

```bash
# Create in overlay/etc/init.d/
cp my_service overlay/etc/init.d/S98myservice
chmod +x overlay/etc/init.d/S98myservice
```

### Persistent Storage Size

Change VDI disk size:

```bash
# In create_vm.sh, modify:
VBoxManage createmedium disk --size 16384  # 16 GB instead of 8 GB
```

## Troubleshooting Builds

### Build Fails: Missing Dependencies

```bash
# Ubuntu/Debian
sudo apt-get install build-essential libncurses-dev rsync wget \
    git bc libssl-dev libelf-dev flex bison

# Fedora/RHEL
sudo dnf groupinstall "Development Tools"
sudo dnf install ncurses-devel rsync wget git bc openssl-devel
```

### Build Fails: Out of Disk Space

```bash
# Clean old builds
./build.sh clean

# Check space
df -h
```

### Build Fails: Download Issues

```bash
# Use different mirror
export BR2_PRIMARY_SITE=http://buildroot.org/downloads

# Or continue interrupted build
./build.sh rebuild
```

### Docker Build Fails

```bash
# Increase Docker resources
# Docker Desktop → Settings → Resources
# - CPUs: 4+
# - Memory: 4 GB+
# - Disk: 20 GB+

# Clean and retry
docker system prune -a
./build-docker.sh
```

## Configuration Files

| File | Purpose |
|------|---------|
| `config/minikernel_defconfig` | Default configuration |
| `config/variants/minimal_defconfig` | Minimal build |
| `config/variants/developer_defconfig` | Developer build |
| `config/variants/production_defconfig` | Production build |
| `config/kernel.config` | Linux kernel configuration |
| `config/isolinux.cfg` | Boot menu |
| `overlay/` | Files added to root filesystem |

## Next Steps

After choosing your configuration:

1. **Configure**: `./configure.sh`
2. **Build**: `./build.sh` (Linux) or `./build-docker.sh` (macOS/Windows)
3. **Test**: `./create_vm.sh`
4. **Deploy**: Use the ISO in VirtualBox, QEMU, or bare metal

For more information, see:
- `README.md` - Build system overview
- `INSTALL.txt` - Installation instructions
- `../BUILDROOT_COMPLETE.md` - Technical details
