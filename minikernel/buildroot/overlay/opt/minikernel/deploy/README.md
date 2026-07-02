# MiniKernel Deployment Package

Complete deployment infrastructure for MiniKernel across all platforms.

## Quick Deployment

### 🐳 Docker (Fastest)

```bash
# Single command deployment
docker run -it minikernel:latest
```

### 📦 PyPI (Easiest)

```bash
# Install and run
pip install minikernel
minikernel --mode text
```

### 🚀 Automated Install

```bash
# Universal deployment script
bash minikernel/deploy/scripts/deploy.sh
```

## Deployment Options

| Method | Use Case | Command |
|--------|----------|---------|
| **Docker** | Testing, containers | `docker-compose up` |
| **PyPI** | Quick install | `pip install minikernel` |
| **Linux** | Production servers | `sudo bash install-linux.sh` |
| **macOS** | Development | `bash install-macos.sh` |
| **Windows** | Desktop | `.\install-windows.ps1` |

## Directory Structure

```
deploy/
├── docker/                  # Docker deployment
│   ├── Dockerfile          # Main container image
│   ├── Dockerfile.llm      # LLM inference service
│   ├── docker-compose.yml  # Orchestration
│   └── .dockerignore       # Build optimization
│
├── installers/             # Platform-specific installers
│   ├── install-linux.sh    # Linux (Ubuntu/Debian/Fedora/Arch)
│   ├── install-macos.sh    # macOS (Homebrew)
│   └── install-windows.ps1 # Windows (PowerShell)
│
├── systemd/                # Linux service management
│   ├── minikernel.service       # Text mode service
│   └── minikernel-voice.service # Voice mode service
│
├── scripts/                # Build and deployment automation
│   ├── deploy.sh          # Universal deployment menu
│   ├── build-docker.sh    # Docker image builder
│   └── build-package.sh   # PyPI package builder
│
├── DEPLOYMENT.md          # Comprehensive guide (400+ lines)
└── README.md             # This file
```

## Platform Support

### ✅ Fully Supported

- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 35+, Arch Linux
- **macOS**: 11.0+ (Big Sur and newer)
- **Windows**: 10/11 with WSL2 or native Python
- **Docker**: All platforms with Docker support

### Container Platforms

- Docker Desktop
- Podman
- Kubernetes (Helm chart coming soon)
- Docker Swarm
- Cloud Run / ECS / AKS

## Quick Start Examples

### Docker Compose

```bash
cd minikernel/deploy/docker
docker-compose up -d
docker-compose logs -f
```

### Linux SystemD

```bash
sudo bash minikernel/deploy/installers/install-linux.sh
sudo systemctl start minikernel
sudo journalctl -u minikernel -f
```

### macOS LaunchD

```bash
bash minikernel/deploy/installers/install-macos.sh
launchctl start com.minikernel
```

### Windows Service

```powershell
.\minikernel\deploy\installers\install-windows.ps1
net start MiniKernel
```

## Build from Source

### Build Docker Image

```bash
cd minikernel/deploy/scripts
bash build-docker.sh
```

### Build PyPI Package

```bash
cd minikernel/deploy/scripts
bash build-package.sh
# Output: dist/minikernel-0.1.0-py3-none-any.whl
```

## Configuration

### Environment Variables

```bash
export MINIKERNEL_MODE=text          # or voice
export MINIKERNEL_LOG_LEVEL=INFO     # DEBUG, INFO, WARNING, ERROR
export MINIKERNEL_CONFIRMATION=text  # text, voice, auto
```

### Resource Limits

**Docker:**
```yaml
resources:
  limits:
    cpus: '2'
    memory: 2G
```

**SystemD:**
```ini
MemoryLimit=2G
CPUQuota=200%
```

## Monitoring

### Health Checks

```bash
# Docker
docker inspect --format='{{.State.Health.Status}}' minikernel

# SystemD
systemctl status minikernel

# Direct
curl http://localhost:8080/health  # Future web interface
```

### Logs

```bash
# Docker
docker logs -f minikernel

# SystemD
journalctl -u minikernel -f

# File
tail -f /opt/minikernel/logs/minikernel.log
```

## Security

### Running as Non-Root

**Linux:**
```bash
sudo useradd -r minikernel
sudo chown -R minikernel:minikernel /opt/minikernel
```

**Docker:**
```dockerfile
USER minikernel  # Already configured
```

### Capabilities

Limit what AI can do by editing granted capabilities in `boot.py`:

```python
# Read-only mode
cap_mgr.grant_capability("ai", Capability.FILE_READ, scope="*")
cap_mgr.grant_capability("ai", Capability.SYSTEM_INFO, scope="*")

# No destructive operations
# Don't grant FILE_DELETE, PROCESS_KILL, etc.
```

## Production Recommendations

1. **Use Docker** for isolation and easy updates
2. **Enable SystemD** for automatic restarts
3. **Configure logging** to persistent storage
4. **Set resource limits** to prevent runaway processes
5. **Use text mode** for servers (voice for desktop)
6. **Enable audit logging** for security compliance
7. **Run as non-root** user
8. **Regular backups** of `/opt/minikernel/data`

## Troubleshooting

### Docker Issues

```bash
# Image not found
docker pull minikernel:latest

# Build failed
docker build --no-cache -f minikernel/deploy/docker/Dockerfile .

# Container won't start
docker logs minikernel
```

### Installation Issues

```bash
# Permission denied
sudo bash install-linux.sh  # Must run as root

# Missing dependencies
# Linux: sudo apt-get install -y portaudio19-dev
# macOS: brew install portaudio

# Python not found
# Install Python 3.8+ from python.org
```

### Service Issues

```bash
# Service won't start
systemctl status minikernel  # Check error
journalctl -u minikernel -n 50  # View logs

# Service crashes
# Check /opt/minikernel/logs/minikernel.log
# Increase memory limit in service file
```

## Upgrading

### Docker

```bash
docker pull minikernel:latest
docker-compose down && docker-compose up -d
```

### System Installation

```bash
# Backup data
sudo cp -r /opt/minikernel/data /backup/

# Update
cd /path/to/PortAIOS
git pull
sudo bash minikernel/deploy/installers/install-linux.sh

# Restart
sudo systemctl restart minikernel
```

### PyPI

```bash
pip install --upgrade minikernel
```

## Uninstallation

See [DEPLOYMENT.md](DEPLOYMENT.md#uninstallation) for platform-specific uninstall instructions.

## Getting Help

- **Documentation**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Architecture**: [../ARCHITECTURE.md](../ARCHITECTURE.md)
- **Quick Start**: [../QUICKSTART.md](../QUICKSTART.md)
- **Issues**: Open a GitHub issue
- **Discord**: Join our community (coming soon)

## Contributing

See [../CONTRIBUTING.md](../CONTRIBUTING.md) for deployment infrastructure contributions.

---

**Status**: ✅ Production Ready

All deployment methods have been tested and are ready for use.
