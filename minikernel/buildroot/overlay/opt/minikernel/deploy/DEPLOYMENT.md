# MiniKernel Deployment Guide

Complete guide for deploying MiniKernel in various environments.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker Deployment](#docker-deployment)
3. [Linux Installation](#linux-installation)
4. [macOS Installation](#macos-installation)
5. [Windows Installation](#windows-installation)
6. [PyPI Package](#pypi-package)
7. [Production Deployment](#production-deployment)
8. [Configuration](#configuration)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Using Docker (Recommended for Testing)

```bash
# Pull and run
docker run -it minikernel:latest

# Or build from source
cd minikernel/deploy/docker
docker-compose up
```

### Using PyPI Package

```bash
# Install
pip install minikernel

# Run
minikernel --mode text
```

### From Source

```bash
# Clone repository
git clone https://github.com/yourusername/minikernel.git
cd minikernel

# Install dependencies
pip install -r requirements.txt

# Run
python3 boot.py --mode text
```

---

## Docker Deployment

### 1. Build Images

```bash
# Build main image
cd /path/to/PortAIOS
docker build -f minikernel/deploy/docker/Dockerfile -t minikernel:latest .

# Or use the build script
bash minikernel/deploy/scripts/build-docker.sh
```

### 2. Run Container

**Interactive Mode:**
```bash
docker run -it --rm \
  --name minikernel \
  -v minikernel-data:/opt/minikernel/data \
  minikernel:latest --mode text
```

**Background Service:**
```bash
docker run -d \
  --name minikernel \
  --restart unless-stopped \
  -v minikernel-data:/opt/minikernel/data \
  -v minikernel-logs:/opt/minikernel/logs \
  minikernel:latest --mode text
```

### 3. Docker Compose (Recommended)

```bash
cd minikernel/deploy/docker

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**With LLM Service:**
```bash
# Start with GPU-accelerated LLM
docker-compose --profile llm up -d
```

### Docker Configuration

**Environment Variables:**
```bash
docker run -it \
  -e MINIKERNEL_MODE=text \
  -e MINIKERNEL_LOG_LEVEL=INFO \
  -e MINIKERNEL_CONFIRMATION=text \
  minikernel:latest
```

**Resource Limits:**
```bash
docker run -it \
  --memory=2g \
  --cpus=2 \
  minikernel:latest
```

---

## Linux Installation

### Automated Installation

**Ubuntu/Debian:**
```bash
# Download and run installer
sudo bash minikernel/deploy/installers/install-linux.sh
```

**Fedora/RHEL:**
```bash
# Same installer supports multiple distros
sudo bash minikernel/deploy/installers/install-linux.sh
```

**Arch Linux:**
```bash
sudo bash minikernel/deploy/installers/install-linux.sh
```

### Manual Installation

**1. Install Dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip portaudio19-dev alsa-utils

# Fedora/RHEL
sudo dnf install -y python3 python3-pip portaudio-devel alsa-utils

# Arch
sudo pacman -S python python-pip portaudio alsa-utils
```

**2. Create Installation Directory:**
```bash
sudo mkdir -p /opt/minikernel
sudo chown $USER:$USER /opt/minikernel
```

**3. Copy Files:**
```bash
cp -r minikernel /opt/minikernel/
cp -r kernel/audio /opt/minikernel/kernel/
cp -r models /opt/minikernel/
```

**4. Install Python Dependencies:**
```bash
cd /opt/minikernel
pip install -r minikernel/requirements.txt
```

**5. Create CLI Wrapper:**
```bash
sudo tee /usr/local/bin/minikernel > /dev/null << 'EOF'
#!/bin/bash
cd /opt/minikernel
exec python3 minikernel/boot.py "$@"
EOF

sudo chmod +x /usr/local/bin/minikernel
```

### SystemD Service

**Install Service:**
```bash
# Copy service files
sudo cp minikernel/deploy/systemd/minikernel.service /etc/systemd/system/
sudo cp minikernel/deploy/systemd/minikernel-voice.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable minikernel

# Start service
sudo systemctl start minikernel

# Check status
sudo systemctl status minikernel
```

**Service Management:**
```bash
# Start
sudo systemctl start minikernel

# Stop
sudo systemctl stop minikernel

# Restart
sudo systemctl restart minikernel

# View logs
sudo journalctl -u minikernel -f

# Disable autostart
sudo systemctl disable minikernel
```

---

## macOS Installation

### Automated Installation

```bash
# Run installer
bash minikernel/deploy/installers/install-macos.sh
```

### Manual Installation

**1. Install Homebrew (if needed):**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**2. Install Dependencies:**
```bash
brew install python@3.11 portaudio
```

**3. Install MiniKernel:**
```bash
sudo mkdir -p /usr/local/minikernel
sudo chown $USER /usr/local/minikernel

cp -r minikernel /usr/local/minikernel/
cp -r kernel/audio /usr/local/minikernel/kernel/
cp -r models /usr/local/minikernel/

cd /usr/local/minikernel
pip3 install -r minikernel/requirements.txt
```

**4. Create CLI Wrapper:**
```bash
sudo tee /usr/local/bin/minikernel > /dev/null << 'EOF'
#!/bin/bash
cd /usr/local/minikernel
exec python3 minikernel/boot.py "$@"
EOF

sudo chmod +x /usr/local/bin/minikernel
```

### LaunchD Service

**Create Service:**
```bash
tee ~/Library/LaunchAgents/com.minikernel.plist > /dev/null << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.minikernel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/usr/local/minikernel/minikernel/boot.py</string>
        <string>--mode</string>
        <string>text</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# Load service
launchctl load ~/Library/LaunchAgents/com.minikernel.plist
```

---

## Windows Installation

### Automated Installation

**Run PowerShell as Administrator:**
```powershell
# Run installer
.\minikernel\deploy\installers\install-windows.ps1
```

### Manual Installation

**1. Install Python:**
- Download from https://python.org (3.8+)
- Check "Add Python to PATH" during installation

**2. Install MiniKernel:**
```powershell
# Create installation directory
New-Item -ItemType Directory -Path "C:\Program Files\MiniKernel" -Force

# Copy files
Copy-Item -Path "minikernel" -Destination "C:\Program Files\MiniKernel" -Recurse
Copy-Item -Path "kernel\audio" -Destination "C:\Program Files\MiniKernel\kernel" -Recurse
Copy-Item -Path "models" -Destination "C:\Program Files\MiniKernel" -Recurse

# Install dependencies
cd "C:\Program Files\MiniKernel"
pip install -r minikernel\requirements.txt
```

**3. Create Batch Wrapper:**
```batch
@echo off
cd /d "C:\Program Files\MiniKernel"
python minikernel\boot.py %*
```
Save as `C:\Windows\System32\minikernel.bat`

### Windows Service (Optional)

**Using NSSM:**
```powershell
# Install NSSM from https://nssm.cc/

# Install service
nssm install MiniKernel python "C:\Program Files\MiniKernel\minikernel\boot.py" --mode text

# Configure service
nssm set MiniKernel DisplayName "MiniKernel - AI OS"
nssm set MiniKernel Description "AI-First Voice-Controlled Operating System"
nssm set MiniKernel Start SERVICE_AUTO_START

# Start service
net start MiniKernel
```

---

## PyPI Package

### Installation

```bash
# Install from PyPI (when published)
pip install minikernel

# Or install from source with pip
cd /path/to/PortAIOS/minikernel
pip install .

# Install with extras
pip install minikernel[llm]      # Include LLM support
pip install minikernel[dev]      # Include dev tools
pip install minikernel[all]      # Everything
```

### Building Package

```bash
# Build package for distribution
cd minikernel
bash deploy/scripts/build-package.sh

# Test installation
pip install dist/minikernel-0.1.0-py3-none-any.whl

# Upload to PyPI (maintainers only)
twine upload dist/*
```

---

## Production Deployment

### Security Hardening

**1. Run as Non-Root User:**
```bash
# Create dedicated user
sudo useradd -r -s /bin/bash minikernel

# Set ownership
sudo chown -R minikernel:minikernel /opt/minikernel

# Run as minikernel user
sudo -u minikernel minikernel --mode text
```

**2. Restrict Capabilities:**
```bash
# Limit what AI can do
# Edit minikernel/boot.py to grant minimal capabilities
```

**3. Enable Audit Logging:**
```bash
# Configure logging in /opt/minikernel/data/logs/
# Monitor with: tail -f /opt/minikernel/data/logs/audit.log
```

### Reverse Proxy (Nginx)

For web interface (future):
```nginx
server {
    listen 80;
    server_name minikernel.example.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Load Balancing

For high availability:
```yaml
# docker-compose with multiple instances
version: '3.8'
services:
  minikernel-1:
    image: minikernel:latest
    # ... config
  
  minikernel-2:
    image: minikernel:latest
    # ... config
  
  nginx:
    image: nginx
    # Load balancer config
```

---

## Configuration

### Environment Variables

```bash
# Operation mode
export MINIKERNEL_MODE=text          # text or voice
export MINIKERNEL_LOG_LEVEL=INFO     # DEBUG, INFO, WARNING, ERROR
export MINIKERNEL_CONFIRMATION=text  # text, voice, or auto

# Paths
export MINIKERNEL_DATA_DIR=/opt/minikernel/data
export MINIKERNEL_LOG_DIR=/opt/minikernel/logs
export MINIKERNEL_MODEL_DIR=/opt/minikernel/models

# LLM Configuration
export MINIKERNEL_LLM_MODEL=/opt/minikernel/models/llama-3-8b-q4.gguf
export MINIKERNEL_LLM_CONTEXT_SIZE=2048
export MINIKERNEL_LLM_THREADS=4
```

### Configuration File

Create `~/.minikernel/config.yaml`:
```yaml
mode: text
log_level: INFO
confirmation_mode: text

paths:
  data: /opt/minikernel/data
  logs: /opt/minikernel/logs
  models: /opt/minikernel/models

llm:
  model: llama-3-8b-q4.gguf
  context_size: 2048
  threads: 4
  gpu_layers: 0

security:
  capabilities:
    file_read: true
    file_write: false
    file_delete: false
    process_list: true
    process_kill: false
    package_install: false
```

---

## Monitoring

### Health Checks

**Docker:**
```bash
# Built-in health check
docker inspect --format='{{.State.Health.Status}}' minikernel
```

**SystemD:**
```bash
# Check service status
systemctl status minikernel

# View logs
journalctl -u minikernel -f
```

### Metrics

**View kernel stats:**
```python
# In Python REPL
from minikernel.core.microkernel import MicroKernel
kernel = MicroKernel()
kernel.boot()
print(kernel.get_stats())
```

**Log monitoring:**
```bash
# Real-time logs
tail -f /opt/minikernel/logs/minikernel.log

# Error logs only
grep ERROR /opt/minikernel/logs/minikernel.log
```

---

## Troubleshooting

### Common Issues

**1. "No module named 'minikernel'"**
```bash
# Ensure correct Python path
export PYTHONPATH=/opt/minikernel:$PYTHONPATH

# Or reinstall
pip install -e /opt/minikernel
```

**2. "Permission denied"**
```bash
# Fix ownership
sudo chown -R $USER:$USER /opt/minikernel

# Or run with sudo (not recommended)
sudo minikernel --mode text
```

**3. "Whisper not available"**
```bash
# Install audio dependencies
sudo apt-get install portaudio19-dev  # Ubuntu/Debian
brew install portaudio                 # macOS

# Reinstall Python packages
pip install -r requirements_gui.txt
```

**4. "Model not found"**
```bash
# Download model
wget https://huggingface.co/.../llama-3-8b-q4.gguf -P /opt/minikernel/models/

# Or use without LLM (pattern matching only)
minikernel --mode text  # Works without LLM
```

### Debug Mode

```bash
# Enable debug logging
minikernel --mode text --log-level DEBUG

# Or set environment variable
export MINIKERNEL_LOG_LEVEL=DEBUG
minikernel --mode text
```

### Getting Help

```bash
# View help
minikernel --help

# Test installation
minikernel --version

# Run tests
cd /opt/minikernel
pytest minikernel/tests/
```

---

## Upgrade

### Docker

```bash
# Pull latest image
docker pull minikernel:latest

# Recreate container
docker-compose down
docker-compose up -d
```

### System Installation

```bash
# Backup data
cp -r /opt/minikernel/data /opt/minikernel/data.backup

# Update files
cd /path/to/PortAIOS
git pull
cp -r minikernel /opt/minikernel/

# Restart service
sudo systemctl restart minikernel
```

### PyPI

```bash
# Upgrade package
pip install --upgrade minikernel
```

---

## Uninstallation

### Linux

```bash
# Stop service
sudo systemctl stop minikernel
sudo systemctl disable minikernel

# Remove service files
sudo rm /etc/systemd/system/minikernel*.service

# Remove installation
sudo rm -rf /opt/minikernel
sudo rm /usr/local/bin/minikernel

# Remove user
sudo userdel minikernel
```

### macOS

```bash
# Stop service
launchctl unload ~/Library/LaunchAgents/com.minikernel.plist
rm ~/Library/LaunchAgents/com.minikernel.plist

# Remove installation
sudo rm -rf /usr/local/minikernel
sudo rm /usr/local/bin/minikernel
```

### Windows

```powershell
# Stop service (if installed)
net stop MiniKernel
nssm remove MiniKernel confirm

# Remove installation
Remove-Item -Path "C:\Program Files\MiniKernel" -Recurse -Force
Remove-Item -Path "C:\Windows\System32\minikernel.bat"
```

### Docker

```bash
# Remove containers
docker-compose down -v

# Remove images
docker rmi minikernel:latest minikernel-llm:latest

# Remove volumes
docker volume rm minikernel-data minikernel-logs minikernel-models
```

---

## Next Steps

- [Architecture Overview](../ARCHITECTURE.md)
- [Quick Start Guide](../QUICKSTART.md)
- [API Documentation](../docs/)
- [Contributing Guide](../CONTRIBUTING.md)

---

**Questions?** Open an issue on GitHub or check the troubleshooting section above.
