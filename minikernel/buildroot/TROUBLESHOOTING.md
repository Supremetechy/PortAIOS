# MiniKernel Buildroot Troubleshooting

## Common Build Errors

### Error: "You have legacy configuration in your .config!"

**Problem**: Buildroot found an old/incompatible configuration file.

**Solution**:
```bash
# Option 1: Clean config files
cd minikernel/buildroot
./clean.sh
# Select option 4 (Clean Buildroot config files)
./build-docker.sh

# Option 2: Full clean and rebuild
./clean.sh
# Select option 5 (Full clean)
./build-docker.sh

# Option 3: Manual clean
rm -rf build/
./build-docker.sh
```

**Why it happens**: 
- Previous build attempt left incompatible config
- Buildroot version mismatch
- Manual config edits

### Error: "make: *** No rule to make target 'defconfig'"

**Problem**: Buildroot not downloaded yet or build directory corrupted.

**Solution**:
```bash
cd minikernel/buildroot
./clean.sh
# Select option 5 (Full clean)
./build-docker.sh
```

### Error: Docker build fails

**Problem**: Docker daemon not running or out of resources.

**Solution**:
```bash
# Check Docker is running
docker info

# If not, start Docker Desktop
open -a Docker

# Increase Docker resources:
# Docker Desktop → Settings → Resources
# - CPUs: 4+
# - Memory: 4 GB+
# - Disk: 20 GB+

# Clean Docker cache
docker system prune -a

# Retry build
./build-docker.sh
```

### Error: "Cannot download package"

**Problem**: Network issue or mirror down.

**Solution**:
```bash
# Try different mirror
export BR2_PRIMARY_SITE=http://buildroot.org/downloads

# Or retry - downloads resume automatically
./build-docker.sh
```

### Error: Out of disk space

**Problem**: Not enough space for build.

**Solution**:
```bash
# Check available space
df -h

# Clean old builds
./clean.sh
# Select option 2 (Clean everything including downloads)

# Free up Docker space
docker system prune -a

# Check Docker disk usage
docker system df
```

### Error: Permission denied

**Problem**: Files created by Docker owned by root.

**Solution**:
```bash
# Fix ownership (macOS/Linux)
sudo chown -R $USER:$USER build/ output/

# Or use clean script
./clean.sh
# Select option 5 (Full clean)
```

### Error: Build hangs or very slow

**Problem**: Insufficient resources or background processes.

**Solution**:
```bash
# Increase Docker resources
# Docker Desktop → Settings → Resources → Memory: 6-8 GB

# Close other applications

# Check CPU usage
top

# Use fewer parallel jobs (slower but more stable)
# Edit build.sh and change:
# make -j$(nproc)
# to:
# make -j2
```

### Error: "Package not found" during build

**Problem**: Package name typo in defconfig or package removed from Buildroot.

**Solution**:
```bash
# Check package exists in Buildroot
cd build/buildroot-*/
make list-defconfigs | grep <package>

# Or use menuconfig to select packages
cd minikernel/buildroot
./configure.sh
# Select option 5 (Custom)
```

### Error: Kernel build fails

**Problem**: Kernel config incompatibility.

**Solution**:
```bash
# Use default kernel config instead of custom
# Edit config/minikernel_defconfig
# Change:
#   BR2_LINUX_KERNEL_USE_CUSTOM_CONFIG=y
#   BR2_LINUX_KERNEL_CUSTOM_CONFIG_FILE="..."
# To:
#   BR2_LINUX_KERNEL_USE_DEFCONFIG=y
#   BR2_LINUX_KERNEL_DEFCONFIG="x86_64"

# Rebuild
./clean.sh && ./build-docker.sh
```

### Error: Python package build fails

**Problem**: Python package dependency issue.

**Solution**:
```bash
# Disable problematic package
# Edit config/minikernel_defconfig
# Remove or comment out failing package

# Use minimal Python
# Remove:
#   BR2_PACKAGE_PYTHON_NUMPY=y
# Keep only:
#   BR2_PACKAGE_PYTHON3=y
```

## Build Performance Issues

### Very slow build

**Causes**:
- Insufficient RAM
- Slow disk (HDD vs SSD)
- Background processes
- Network speed (downloads)

**Solutions**:
```bash
# Use minimal variant (faster)
./configure.sh
# Select option 2 (Minimal)

# Enable parallel build
./configure.sh
# Answer 'y' to parallel build

# Build locally on Linux if possible
# (Much faster than Docker on macOS)
```

### Build keeps recompiling same packages

**Problem**: Timestamps or config changes.

**Solution**:
```bash
# Clean and rebuild from scratch
./clean.sh
# Select option 5

# Don't edit config during build
# Don't stop/start build repeatedly
```

## VirtualBox Issues

### VM won't boot from ISO

**Problem**: Boot order or BIOS settings.

**Solution**:
```bash
# Check boot order
VBoxManage modifyvm MiniKernel --boot1 dvd --boot2 disk

# Enable VT-x/AMD-V
VBoxManage modifyvm MiniKernel --hwvirtex on

# Try safe mode
# In boot menu, select "minikernel-safe"
```

### Persistent disk not mounting

**Problem**: Disk not formatted or wrong device.

**Solution**:
```bash
# First boot only - format the disk
mkfs.ext4 /dev/sda1

# Check if disk is attached
lsblk

# Manual mount
mount /dev/sda1 /mnt/persistent
```

### No network in VM

**Problem**: Network adapter not configured.

**Solution**:
```bash
# Check adapter is enabled
VBoxManage modifyvm MiniKernel --nic1 nat

# Or use bridged mode
VBoxManage modifyvm MiniKernel --nic1 bridged --bridgeadapter1 en0

# Inside VM, check DHCP
dhcpcd eth0
```

### No audio in VM

**Problem**: Audio controller not enabled.

**Solution**:
```bash
# Enable audio
VBoxManage modifyvm MiniKernel --audio-enabled on --audiocontroller ac97

# Inside VM, check ALSA
aplay -l
```

## Debugging Build Issues

### Get detailed build log

```bash
# Build with verbose output
cd minikernel/buildroot
./build-docker.sh 2>&1 | tee build.log

# Check specific package build
cd build/buildroot-*/
make <package>-rebuild V=1
```

### Check what's consuming disk

```bash
# Check build directory size
du -sh build/

# Check downloads
du -sh build/buildroot-*/dl/

# Check output
du -sh output/
```

### Verify configuration

```bash
# Check current config
cd build/buildroot-*/
make show-defconfig

# Compare with our config
diff .config ../../config/minikernel_defconfig
```

## Getting Help

### Collect diagnostic info

```bash
# System info
uname -a
docker --version
df -h

# Build info
cd minikernel/buildroot
./build-docker.sh 2>&1 | tail -50

# Package this and share
```

### Useful commands

```bash
# List all Buildroot packages
cd build/buildroot-*/
make list-defconfigs

# Show package dependencies
make <package>-show-depends

# Show package info
make <package>-show-info
```

## Quick Fixes

### Start fresh

```bash
cd minikernel/buildroot
./clean.sh  # Option 5
./build-docker.sh
```

### Use minimal config

```bash
./configure.sh  # Option 2 (Minimal)
./build-docker.sh
```

### Build outside Docker (Linux only)

```bash
# On Linux machine
sudo apt-get install build-essential libncurses-dev rsync wget
./build.sh
```

### Skip problematic packages

```bash
# Edit config, remove failing packages
vim config/minikernel_defconfig
# Remove lines with packages that fail
./build-docker.sh
```

## Still Having Issues?

1. Check `BUILD_OPTIONS.md` for configuration details
2. Read `README.md` for build system overview
3. Try minimal variant first
4. Ensure Docker has enough resources (4GB RAM, 20GB disk)
5. Build on Linux if possible (faster and more reliable)

## Common Success Path

```bash
# Clean start
cd minikernel/buildroot
./clean.sh  # Select option 5

# Use minimal config (faster, fewer issues)
./configure.sh  # Select option 2
./build-docker.sh

# Wait ~45-60 minutes
# Boot with: ./create_vm.sh
```
