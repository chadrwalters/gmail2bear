#!/bin/bash
# One-liner installation script for Gmail to Bear

set -e

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This script is only supported on macOS."
    exit 1
fi

# Check if UV is installed
if command -v uv &> /dev/null; then
    echo "UV detected. Will use UV for installation."
    USE_UV=true
else
    echo "UV not detected. Checking for pip..."
    if command -v pip &> /dev/null; then
        echo "pip detected. Will use pip for installation."
        USE_UV=false
    else
        echo "Error: Neither UV nor pip is installed."
        echo "Please install UV (recommended) or pip to continue."
        exit 1
    fi
fi

# Create config directory
CONFIG_DIR="$HOME/.gmail2bear"
mkdir -p "$CONFIG_DIR"

# Clone the repository if not already cloned
REPO_DIR="$HOME/gmail2bear"
if [ ! -d "$REPO_DIR" ]; then
    echo "Cloning Gmail to Bear repository..."
    git clone https://github.com/chadrwalters/gmail2bear.git "$REPO_DIR"
fi

# Navigate to the repository directory
cd "$REPO_DIR"

# Install the package
if [ "$USE_UV" = true ]; then
    echo "Installing Gmail to Bear using UV..."
    uv pip install -e .
else
    echo "Installing Gmail to Bear using pip..."
    pip install -e .
fi

# Create default configuration
echo "Creating default configuration..."
if [ "$USE_UV" = true ]; then
    uv run gmail2bear init-config --config "$CONFIG_DIR/config.ini"
else
    gmail2bear init-config --config "$CONFIG_DIR/config.ini"
fi

# Install the service
echo "Installing Gmail to Bear service..."
if [ "$USE_UV" = true ]; then
    uv run gmail2bear service install \
        --config "$CONFIG_DIR/config.ini" \
        --credentials "$CONFIG_DIR/credentials.json" \
        --token "$CONFIG_DIR/token.pickle" \
        --state "$CONFIG_DIR/state.txt"
else
    gmail2bear service install \
        --config "$CONFIG_DIR/config.ini" \
        --credentials "$CONFIG_DIR/credentials.json" \
        --token "$CONFIG_DIR/token.pickle" \
        --state "$CONFIG_DIR/state.txt"
fi

echo ""
echo "Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit the configuration file at $CONFIG_DIR/config.ini"
echo "2. Place your Google API credentials at $CONFIG_DIR/credentials.json"
echo "3. Start the service with: gmail2bear service start"
echo "4. Check the service status with: gmail2bear service status"
echo ""
echo "For more information, see the README.md file in the repository."
