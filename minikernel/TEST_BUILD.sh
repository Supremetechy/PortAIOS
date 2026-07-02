#!/bin/bash
# Quick test to verify all Buildroot components are in place

echo "=========================================="
echo "MiniKernel Buildroot Component Verification"
echo "=========================================="
echo ""

check_file() {
    if [ -f "$1" ]; then
        echo "✓ $1"
        return 0
    else
        echo "✗ $1 (MISSING)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo "✓ $1/"
        return 0
    else
        echo "✗ $1/ (MISSING)"
        return 1
    fi
}

failed=0

echo "Core Components:"
check_file "minikernel/core/native/syscall_bridge.c" || failed=1
check_file "minikernel/core/elf_loader.py" || failed=1
check_file "minikernel/core/disk_image.py" || failed=1
check_file "minikernel/boot.py" || failed=1
echo ""

echo "Buildroot Configuration:"
check_file "minikernel/buildroot/build.sh" || failed=1
check_file "minikernel/buildroot/create_vm.sh" || failed=1
check_file "minikernel/buildroot/config/minikernel_defconfig" || failed=1
check_file "minikernel/buildroot/config/kernel.config" || failed=1
check_file "minikernel/buildroot/config/isolinux.cfg" || failed=1
echo ""

echo "Overlay Files:"
check_file "minikernel/buildroot/overlay/etc/init.d/S99minikernel" || failed=1
check_file "minikernel/buildroot/overlay/etc/fstab" || failed=1
check_file "minikernel/buildroot/overlay/etc/profile.d/minikernel.sh" || failed=1
echo ""

echo "Documentation:"
check_file "BUILD_SUMMARY.md" || failed=1
check_file "minikernel/BUILDROOT_COMPLETE.md" || failed=1
check_file "minikernel/QUICKSTART_BUILDROOT.md" || failed=1
check_file "minikernel/buildroot/README.md" || failed=1
check_file "minikernel/buildroot/INSTALL.txt" || failed=1
echo ""

echo "Directories:"
check_dir "minikernel/buildroot/config" || failed=1
check_dir "minikernel/buildroot/overlay" || failed=1
check_dir "minikernel/buildroot/output" || failed=1
echo ""

echo "=========================================="
if [ $failed -eq 0 ]; then
    echo "✓ All components present!"
    echo ""
    echo "Ready to build. Run:"
    echo "  cd minikernel/buildroot"
    echo "  ./build.sh"
else
    echo "✗ Some components missing!"
    exit 1
fi
echo "=========================================="
