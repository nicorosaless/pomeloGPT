#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set PYTHONPATH to the project root
export PYTHONPATH="$SCRIPT_DIR"

echo "Starting PomeloGPT Backend..."
echo "Project Root: $SCRIPT_DIR"

# Check if requirements are installed
if ! python3 -c "import fastapi, uvicorn, ollama" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install -r "$SCRIPT_DIR/backend/requirements.txt"
fi

# Run the backend
python3 "$SCRIPT_DIR/backend/main.py"
