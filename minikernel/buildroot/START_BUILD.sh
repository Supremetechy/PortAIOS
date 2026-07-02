#!/bin/bash
#
# Simple Build Starter for MiniKernel
# Run this in a Terminal and leave it running
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║              🚀 MiniKernel Build - Interactive Mode 🚀               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

This will build MiniKernel in a Docker container.
Keep this terminal open - the build takes ~2 hours.

Press Ctrl+C to stop (build can be resumed later)

EOF

read -p "Ready to start? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "Starting Docker build..."
echo "Time started: $(date)"
echo ""

# Run interactively so you can see progress
docker run --rm \
    -v "${PROJECT_ROOT}:/workspace" \
    -w /workspace/minikernel/buildroot \
    minikernel-builder \
    bash -c "
        echo '=========================================='
        echo 'MiniKernel Build Starting'
        echo '=========================================='
        echo ''
        ./build.sh
        echo ''
        echo '=========================================='
        echo 'Build Complete!'
        echo 'Output in: output/minikernel.iso'
        echo '=========================================='
    "

echo ""
echo "Build finished at: $(date)"
echo ""
echo "Next step: ./create_vm.sh"
