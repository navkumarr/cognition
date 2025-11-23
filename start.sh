#!/bin/bash

# Voice Browser Startup Script

set -e

echo "=========================================="
echo "Voice-Controlled Browser Setup"
echo "=========================================="
echo

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if in voice_browser directory
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Run this script from voice_browser directory${NC}"
    exit 1
fi

# Check for API key
if [ -z "$FISH_AUDIO_API_KEY" ]; then
    echo -e "${YELLOW}Warning: FISH_AUDIO_API_KEY not set${NC}"
    echo "Fish Audio TTS/STT will be disabled"
    echo "Set it with: export FISH_AUDIO_API_KEY='your-key'"
    echo
fi

# Check for LLM API keys (for browser-use)
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${YELLOW}Warning: No LLM API key set${NC}"
    echo "Complex tasks (browser-use) will not work"
    echo "Set one of:"
    echo "  export OPENAI_API_KEY='your-key'"
    echo "  export ANTHROPIC_API_KEY='your-key'"
    echo
fi

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
    echo
fi

# Install/update dependencies
echo "Installing dependencies..."
uv pip install -e . > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo

# Check if Chrome is running with debugging port
echo "Checking Chrome remote debugging..."
if curl -s http://localhost:9222/json > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Chrome debugging port accessible${NC}"
else
    echo -e "${RED}✗ Chrome not running with remote debugging${NC}"
    echo
    echo "Start Chrome with:"
    echo "  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\"
    echo "    --remote-debugging-port=9222 \\"
    echo "    --user-data-dir=/tmp/chrome-voice-browser &"
    echo
    echo "Then run this script again."
    exit 1
fi
echo

# Check microphone access
echo "Checking microphone access..."
.venv/bin/python -c "import sounddevice as sd; devices = sd.query_devices(); print(f'Found {len(devices)} audio devices')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Microphone accessible${NC}"
else
    echo -e "${RED}✗ Microphone not accessible${NC}"
    echo "Grant microphone permissions in System Preferences"
fi
echo

echo "=========================================="
echo "Starting Voice Browser Control Hub"
echo "=========================================="
echo
echo "Server will run on http://localhost:8080"
echo
echo "Voice Commands:"
echo "  • Quick: 'scroll down', 'click button', 'go to google.com'"
echo "  • Transcribe: 'Hey Fish' → speak → 'Done Fish'"
echo "  • Complex: 'book a flight to NYC'"
echo
echo "Press Ctrl+C to stop"
echo
echo "=========================================="
echo

# Run the server
uv run main.py
