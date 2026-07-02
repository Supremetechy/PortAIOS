#!/bin/bash
# Build MiniKernel Docker images

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname $(dirname $(dirname $SCRIPT_DIR)))"

cd "$PROJECT_ROOT"

echo "════════════════════════════════════════════════════════════"
echo "  Building MiniKernel Docker Images"
echo "════════════════════════════════════════════════════════════"
echo

# Build main image
echo "Building main MiniKernel image..."
docker build \
    -f minikernel/deploy/docker/Dockerfile \
    -t minikernel:latest \
    -t minikernel:0.1.0 \
    .

echo "✓ Main image built: minikernel:latest"
echo

# Build LLM image (optional)
read -p "Build LLM inference image? (requires GPU) [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Building LLM inference image..."
    docker build \
        -f minikernel/deploy/docker/Dockerfile.llm \
        -t minikernel-llm:latest \
        -t minikernel-llm:0.1.0 \
        .
    echo "✓ LLM image built: minikernel-llm:latest"
fi

echo
echo "════════════════════════════════════════════════════════════"
echo "  Docker Images Ready"
echo "════════════════════════════════════════════════════════════"
echo
echo "Run with:"
echo "  docker run -it minikernel:latest"
echo
echo "Or use Docker Compose:"
echo "  cd minikernel/deploy/docker"
echo "  docker-compose up"
echo
