#!/bin/bash
#
# MiniKernel VirtualBox VM Creation Script
# Automatically creates and configures a VirtualBox VM for MiniKernel
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"

VM_NAME="MiniKernel"
VM_MEMORY=2048
VM_CPUS=2
VM_VRAM=128

ISO_PATH="${OUTPUT_DIR}/minikernel.iso"
VDI_PATH="${OUTPUT_DIR}/minikernel-persistent.vdi"

echo "=========================================="
echo "MiniKernel VirtualBox VM Setup"
echo "=========================================="

# Check VBoxManage
#if ! command -v VBoxManage &> /dev/null; then
#    echo "ERROR: VBoxManage not found. Please install VirtualBox."
#    exit 1
#fi

# Check if VM already exists
if VBoxManage list vms | grep -q "\"$VM_NAME\""; then
    echo "VM '$VM_NAME' already exists."
    read -p "Delete and recreate? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing VM..."
        VBoxManage unregistervm "$VM_NAME" --delete || true
    else
        echo "Aborting."
        exit 1
    fi
fi

# Check if ISO exists
if [ ! -f "$ISO_PATH" ]; then
    echo "ERROR: ISO not found at $ISO_PATH"
    echo "Run ./build.sh first to build the ISO"
    exit 1
fi

# Create VM
echo "Creating VM: $VM_NAME"
VBoxManage createvm \
    --name "$VM_NAME" \
    --ostype "Linux_64" \
    --register

# Configure VM
echo "Configuring VM..."
VBoxManage modifyvm "$VM_NAME" \
    --memory $VM_MEMORY \
    --cpus $VM_CPUS \
    --vram $VM_VRAM \
    --acpi on \
    --ioapic on \
    --pae on \
    --hwvirtex on \
    --nestedpaging on \
    --largepages on \
    --vtxvpid on \
    --boot1 dvd \
    --boot2 disk \
    --boot3 none \
    --boot4 none \
    --audio-driver default \
    --audio-enabled on \
    --audiocontroller ac97 \
    --nic1 nat \
    --natpf1 "ssh,tcp,,2222,,22" \
    --clipboard-mode bidirectional \
    --draganddrop bidirectional

# Create storage controllers
echo "Creating storage controllers..."

# IDE controller for CD/DVD
VBoxManage storagectl "$VM_NAME" \
    --name "IDE" \
    --add ide \
    --controller PIIX4 \
    --portcount 2 \
    --hostiocache on \
    --bootable on

# SATA controller for hard disk
VBoxManage storagectl "$VM_NAME" \
    --name "SATA" \
    --add sata \
    --controller IntelAhci \
    --portcount 4 \
    --hostiocache on \
    --bootable on

# Attach ISO
echo "Attaching ISO: $ISO_PATH"
VBoxManage storageattach "$VM_NAME" \
    --storagectl "IDE" \
    --port 0 \
    --device 0 \
    --type dvddrive \
    --medium "$ISO_PATH"

# Create or attach persistent disk
if [ ! -f "$VDI_PATH" ]; then
    echo "Creating persistent disk: $VDI_PATH"
    VBoxManage createmedium disk \
        --filename "$VDI_PATH" \
        --size 8192 \
        --format VDI \
        --variant Standard
    
    # Format the disk
    echo "Formatting persistent disk..."
    # We'll format it on first boot
fi

echo "Attaching persistent disk: $VDI_PATH"
VBoxManage storageattach "$VM_NAME" \
    --storagectl "SATA" \
    --port 0 \
    --device 0 \
    --type hdd \
    --medium "$VDI_PATH"

# Set up shared folder (optional)
SHARED_FOLDER="${SCRIPT_DIR}/../.."
if [ -d "$SHARED_FOLDER" ]; then
    echo "Setting up shared folder: $SHARED_FOLDER"
    VBoxManage sharedfolder add "$VM_NAME" \
        --name "shared" \
        --hostpath "$SHARED_FOLDER" \
        --automount \
        --auto-mount-point "/mnt/shared" || true
fi

# Create snapshot
echo "Creating initial snapshot..."
VBoxManage snapshot "$VM_NAME" take "Initial State" \
    --description "Fresh MiniKernel installation"

echo ""
echo "=========================================="
echo "VM Created Successfully!"
echo "=========================================="
echo ""
echo "VM Name: $VM_NAME"
echo "Memory: ${VM_MEMORY} MB"
echo "CPUs: $VM_CPUS"
echo "ISO: $ISO_PATH"
echo "Disk: $VDI_PATH"
echo ""
echo "To start the VM:"
echo "  VBoxManage startvm \"$VM_NAME\""
echo ""
echo "Or use GUI:"
echo "  VirtualBox -> $VM_NAME -> Start"
echo ""
echo "SSH access (after network configured):"
echo "  ssh -p 2222 root@localhost"
echo "  Password: minikernel"
echo ""
echo "First boot instructions:"
echo "  1. Boot from ISO"
echo "  2. Login as root (password: minikernel)"
echo "  3. Format persistent disk: mkfs.ext4 /dev/sda"
echo "  4. Reboot: reboot"
echo "  5. MiniKernel will auto-mount /dev/sda1 at /mnt/persistent"
echo ""

# Ask to start VM
read -p "Start VM now? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "Starting VM..."
    VBoxManage startvm "$VM_NAME"
fi
