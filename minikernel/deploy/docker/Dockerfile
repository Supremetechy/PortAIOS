# MiniKernel Docker Image
# AI-First Voice-Controlled Operating System

FROM python:3.11-slim

LABEL maintainer="MiniKernel Project"
LABEL description="AI-First Voice-Controlled Operating System"
LABEL version="0.1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    MINIKERNEL_HOME=/opt/minikernel

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Audio support
    portaudio19-dev \
    alsa-utils \
    # Build tools
    build-essential \
    cmake \
    git \
    # System utilities
    procps \
    psmisc \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create minikernel user (non-root for security)
RUN useradd -m -s /bin/bash minikernel && \
    mkdir -p ${MINIKERNEL_HOME} && \
    chown -R minikernel:minikernel ${MINIKERNEL_HOME}

# Set working directory
WORKDIR ${MINIKERNEL_HOME}

# Copy requirements first (for layer caching)
COPY --chown=minikernel:minikernel minikernel/requirements.txt ./requirements.txt
COPY --chown=minikernel:minikernel requirements_gui.txt ./requirements_gui.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_gui.txt

# Copy MiniKernel source code
COPY --chown=minikernel:minikernel minikernel/ ./minikernel/
COPY --chown=minikernel:minikernel kernel/audio/ ./kernel/audio/

# Copy models directory (if exists)
COPY --chown=minikernel:minikernel models/ ./models/ 2>/dev/null || true

# Create necessary directories
RUN mkdir -p \
    ${MINIKERNEL_HOME}/data \
    ${MINIKERNEL_HOME}/logs \
    ${MINIKERNEL_HOME}/models \
    && chown -R minikernel:minikernel ${MINIKERNEL_HOME}

# Switch to minikernel user
USER minikernel

# Expose ports (for future web interface)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; sys.path.insert(0, '${MINIKERNEL_HOME}'); from minikernel.core.microkernel import MicroKernel; print('healthy')" || exit 1

# Set entrypoint
ENTRYPOINT ["python3", "minikernel/boot.py"]

# Default command (text mode)
CMD ["--mode", "text", "--log-level", "INFO"]
