#!/bin/bash
# Build Python package for PyPI distribution

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname $(dirname $(dirname $SCRIPT_DIR)))"

cd "$PROJECT_ROOT/minikernel"

echo "════════════════════════════════════════════════════════════"
echo "  Building MiniKernel Python Package"
echo "════════════════════════════════════════════════════════════"
echo

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/
echo "✓ Cleaned"

# Install build dependencies
echo "Installing build dependencies..."
pip install --upgrade build twine
echo "✓ Dependencies installed"

# Build package
echo "Building package..."
python -m build
echo "✓ Package built"

# Check package
echo "Checking package..."
twine check dist/*
echo "✓ Package checked"

echo
echo "════════════════════════════════════════════════════════════"
echo "  Package Build Complete"
echo "════════════════════════════════════════════════════════════"
echo
echo "Artifacts created:"
ls -lh dist/
echo
echo "To test installation:"
echo "  pip install dist/minikernel-0.1.0-py3-none-any.whl"
echo
echo "To upload to PyPI (when ready):"
echo "  twine upload dist/*"
echo
