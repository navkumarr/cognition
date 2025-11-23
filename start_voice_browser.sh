#!/bin/bash

# Voice Browser Startup Script
# Opens Chrome with debugging port and starts the voice control system

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CHROME_USER_DATA="/tmp/voice-browser-chrome"

echo "🎙️  Voice Browser Startup"
echo "=========================================="
echo ""

# Create Chrome user data directory if it doesn't exist
if [ ! -d "$CHROME_USER_DATA" ]; then
    echo "📁 Creating Chrome profile directory..."
    mkdir -p "$CHROME_USER_DATA"
fi

# Check if Chrome is already running with debugging port
if lsof -Pi :9222 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "✅ Chrome is already running with debugging port 9222"
else
    echo "🌐 Starting Chrome with remote debugging..."
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
        --remote-debugging-port=9222 \
        --user-data-dir="$CHROME_USER_DATA" \
        --disable-blink-features=AutomationControlled \
        "about:blank" &
    
    CHROME_PID=$!
    echo "   Chrome PID: $CHROME_PID"
    echo "   Waiting for Chrome to start..."
    sleep 3
fi

echo ""
echo "🚀 Starting Voice Browser Server..."
echo "   http://localhost:8080"
echo "   (Press Ctrl+C to stop)"
echo ""

cd "$SCRIPT_DIR"

# Activate virtual environment and run main.py
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

exec .venv/bin/python main.py
