#!/bin/bash

# Text2SQL Skill Installation Script
# This script sets up the Text2SQL skill with all necessary dependencies

set -e  # Exit on error

echo "========================================"
echo "Text2SQL Skill Installation"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Error: Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "Found Python $PYTHON_VERSION"
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Ask about virtual environment
echo "Do you want to create a virtual environment? (recommended)"
read -p "Create venv? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    VENV_DIR="$PROJECT_DIR/venv"

    if [ -d "$VENV_DIR" ]; then
        echo "Virtual environment already exists at $VENV_DIR"
        read -p "Recreate it? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_DIR"
            $PYTHON_CMD -m venv "$VENV_DIR"
        fi
    else
        echo "Creating virtual environment..."
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi

    # Activate virtual environment
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    PYTHON_CMD="python"  # Use venv python
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
$PYTHON_CMD -m pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo "Installing dependencies..."
$PYTHON_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "1. Activate the virtual environment:"
    echo "   source $VENV_DIR/bin/activate"
    echo ""
fi
echo "2. Test the installation:"
echo "   python scripts/schema_scanner.py --help"
echo ""
echo "3. Read the documentation:"
echo "   cat README.md"
echo ""
echo "4. Try exploring a database:"
echo "   python scripts/schema_scanner.py --connection-string 'postgresql://user:pass@localhost/dbname'"
echo ""
echo "For more information, see README.md"
echo ""
