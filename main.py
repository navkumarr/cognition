"""Main entry point for voice-controlled browser."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from control_hub import run_server


def main():
    """Main entry point."""
    print("=" * 60)
    print("Voice-Controlled Browser")
    print("=" * 60)
    print()
    print("Commands:")
    print("  - Quick commands: 'scroll down', 'click search', 'go to google.com'")
    print("  - Fish transcription: 'Hey Fish' -> speak -> 'Done Fish'")
    print("  - Complex tasks: 'book a flight to NYC', 'compare laptop prices'")
    print()
    print("Requirements:")
    print("  1. Chrome running with --remote-debugging-port=9222")
    print("  2. FISH_AUDIO_API_KEY environment variable (optional)")
    print("  3. Chrome extension installed (for simple actions)")
    print()
    print("=" * 60)
    print()
    
    # Check for API key
    if not os.getenv("FISH_AUDIO_API_KEY"):
        print("⚠️  Warning: FISH_AUDIO_API_KEY not set - TTS/Fish STT disabled")
        print()
    
    # Check Chrome
    print("Make sure Chrome is running with:")
    print("  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
    print()
    
    print("Starting control hub on http://localhost:8080")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        run_server(host="0.0.0.0", port=8080)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
