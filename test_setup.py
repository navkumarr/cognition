#!/usr/bin/env python3
"""
Quick test script to verify voice browser installation
"""

import sys
import os

def test_imports():
    """Test if all required packages are installed."""
    print("Testing imports...")
    
    try:
        import fastapi
        print("  ✓ fastapi")
    except ImportError:
        print("  ✗ fastapi - run: uv pip install -e .")
        return False
    
    try:
        import browser_use
        print("  ✓ browser-use")
    except ImportError:
        print("  ✗ browser-use")
        return False
    
    try:
        import faster_whisper
        print("  ✓ faster-whisper")
    except ImportError:
        print("  ✗ faster-whisper")
        return False
    
    try:
        import sounddevice
        print("  ✓ sounddevice")
    except ImportError:
        print("  ✗ sounddevice")
        return False
    
    try:
        import httpx
        print("  ✓ httpx")
    except ImportError:
        print("  ✗ httpx")
        return False
    
    try:
        import websockets
        print("  ✓ websockets")
    except ImportError:
        print("  ✗ websockets")
        return False
    
    return True


def test_api_keys():
    """Check if API keys are set."""
    print("\nChecking API keys...")
    
    has_fish = os.getenv("FISH_AUDIO_API_KEY")
    if has_fish:
        print("  ✓ FISH_AUDIO_API_KEY set")
    else:
        print("  ⚠ FISH_AUDIO_API_KEY not set (TTS/Fish STT disabled)")
    
    has_openai = os.getenv("OPENAI_API_KEY")
    has_anthropic = os.getenv("ANTHROPIC_API_KEY")
    
    if has_openai:
        print("  ✓ OPENAI_API_KEY set")
    elif has_anthropic:
        print("  ✓ ANTHROPIC_API_KEY set")
    else:
        print("  ⚠ No LLM API key set (complex tasks disabled)")


def test_chrome():
    """Test Chrome remote debugging connection."""
    print("\nChecking Chrome remote debugging...")
    
    try:
        import httpx
        response = httpx.get("http://localhost:9222/json", timeout=2)
        if response.status_code == 200:
            print("  ✓ Chrome debugging port accessible")
            data = response.json()
            print(f"  ✓ Found {len(data)} Chrome tabs")
        else:
            print("  ✗ Chrome returned error")
            return False
    except Exception as e:
        print("  ✗ Chrome not accessible")
        print("  Run: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-voice &")
        return False
    
    return True


def test_microphone():
    """Test microphone access."""
    print("\nChecking microphone...")
    
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        
        if input_devices:
            print(f"  ✓ Found {len(input_devices)} input devices")
            default = sd.query_devices(kind='input')
            print(f"  ✓ Default: {default['name']}")
        else:
            print("  ✗ No input devices found")
            return False
    except Exception as e:
        print(f"  ✗ Microphone error: {e}")
        return False
    
    return True


def test_command_parser():
    """Test command parser."""
    print("\nTesting command parser...")
    
    try:
        from parsers.command_parser import CommandParser
        
        parser = CommandParser()
        
        # Test simple command
        result = parser.parse("scroll down")
        assert result['type'] == 'scroll'
        print("  ✓ Simple command parsing")
        
        # Test navigation
        result = parser.parse("go to google.com")
        assert result['type'] == 'navigate'
        print("  ✓ Navigation parsing")
        
        # Test complex task
        result = parser.parse("book a flight to NYC")
        assert result['type'] == 'complex_task'
        print("  ✓ Complex task detection")
        
    except Exception as e:
        print(f"  ✗ Parser error: {e}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("Voice Browser Installation Test")
    print("=" * 50)
    print()
    
    results = []
    
    results.append(("Imports", test_imports()))
    test_api_keys()  # Non-blocking
    results.append(("Chrome", test_chrome()))
    results.append(("Microphone", test_microphone()))
    results.append(("Parser", test_command_parser()))
    
    print()
    print("=" * 50)
    print("Test Results")
    print("=" * 50)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    print()
    
    if all(r[1] for r in results):
        print("✓ All tests passed! Ready to run voice browser.")
        print()
        print("Start with: uv run main.py")
        return 0
    else:
        print("✗ Some tests failed. Check errors above.")
        print()
        print("Run setup script: ./start.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())
