# syntax=docker/dockerfile:1
# =============================================================================
# PortAIOS — Production Docker Image
# =============================================================================
# Build:
#   docker build -t portaios .
#   docker build --build-arg INCLUDE_TTS=1 -t portaios:full .
#
# Run (browser connects to http://localhost:8001):
#   docker run -p 8001:8001 -p 8765:8765 portaios
#
# With GPU (requires NVIDIA Container Toolkit):
#   docker run --gpus all -p 8001:8001 -p 8765:8765 portaios

ARG PYTHON_VERSION=3.11

# =============================================================================
# Stage 1 — builder: install all Python deps (includes compilation)
# =============================================================================
FROM python:${PYTHON_VERSION}-slim AS builder

# System packages needed to compile C-extension deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        portaudio19-dev \
        libsndfile1-dev \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
        libopenblas-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy dependency manifests first — Docker layer cache skips re-installing
# packages when only source files change.
COPY requirements.txt requirements-server.txt ./

# Install into an isolated prefix so we can COPY it cleanly to the final stage
RUN pip install --no-cache-dir --prefix=/install -r requirements-server.txt

# Optional: full TTS support (large — enable with: --build-arg INCLUDE_TTS=1)
ARG INCLUDE_TTS=0
RUN if [ "$INCLUDE_TTS" = "1" ]; then \
        pip install --no-cache-dir --prefix=/install TTS>=0.22.0 piper-tts>=1.4.0; \
    fi

# =============================================================================
# Stage 2 — final: minimal runtime image
# =============================================================================
FROM python:${PYTHON_VERSION}-slim AS final

LABEL org.opencontainers.image.title="PortAIOS" \
      org.opencontainers.image.description="AI Operating System — neural interface & agent platform" \
      org.opencontainers.image.source="https://github.com/Supremetechy/PortAIOS"

# Runtime-only system libraries (no compiler toolchain)
RUN apt-get update && apt-get install -y --no-install-recommends \
        portaudio19-dev \
        libsndfile1 \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
        libopenblas0 \
        procps \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Pull compiled packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application source (order: rarely-changed → frequently-changed)
COPY installer/   ./installer/
COPY minikernel/  ./minikernel/
COPY kernel/      ./kernel/
COPY web/         ./web/
COPY assets/      ./assets/
COPY server.py docker_server.py run_onboarding.py ./

# models/ is volume-mounted at runtime to avoid baking large GLB/GGUF files
# into the image — create the directory so mounts attach cleanly.
RUN mkdir -p /app/models

# Non-root user for security
RUN useradd --system --create-home --uid 1001 aios \
    && chown -R aios:aios /app
RUN mkdir -p /home/aios/.aios && chown aios:aios /home/aios/.aios

USER aios

# ── Ports ────────────────────────────────────────────────────────────────────
# 8001 — Eel/Bottle web UI  (open http://localhost:8001 in your host browser)
# 8765 — WebSocket viseme/avatar stream
EXPOSE 8001 8765

# ── Environment ──────────────────────────────────────────────────────────────
ENV AIOS_HEADLESS=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/home/aios

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:8001/ > /dev/null || exit 1

# ── Entrypoint ───────────────────────────────────────────────────────────────
# Override CMD to run just the viseme bridge: docker run portaios python docker_server.py
ENTRYPOINT ["python"]
CMD ["run_onboarding.py"]
