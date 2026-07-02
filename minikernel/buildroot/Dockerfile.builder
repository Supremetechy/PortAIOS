# MiniKernel Buildroot Builder
# Docker container for building MiniKernel ISO on macOS/Windows

FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libncurses-dev \
    rsync \
    wget \
    git \
    bc \
    libssl-dev \
    libelf-dev \
    flex \
    bison \
    cpio \
    unzip \
    file \
    python3 \
    python3-dev \
    python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

# Create build user (don't build as root)
RUN useradd -m -s /bin/bash builder && \
    echo "builder ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set up workspace
WORKDIR /workspace
RUN chown builder:builder /workspace

USER builder

# Default command
CMD ["/bin/bash"]
