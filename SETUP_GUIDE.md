# Voice-Controlled Web Browser - Quick Setup Guide

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd /Users/nav/Documents/code/temp/browser/voice_browser
./start.sh
```

The script will:
- ✓ Create virtual environment
- ✓ Install all dependencies
- ✓ Check Chrome debugging port
- ✓ Verify microphone access
- ✓ Start the server

### 2. Set API Keys

```bash
# Required for TTS and Fish transcription
export FISH_AUDIO_API_KEY="your_key_here"

# Required for complex tasks (choose one)
export OPENAI_API_KEY="your_key_here"
# OR
export ANTHROPIC_API_KEY="your_key_here"
```

Or create `.env` file:

```bash
cp .env.example .env
# Edit .env with your keys
```

### 3. Start Chrome with Debugging

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-voice-browser &
```

### 4. Install Chrome Extension

1. Open Chrome: `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select: `/Users/nav/Documents/code/temp/browser/chrome_extension/`

Note: You need to create icon files (icon16.png, icon48.png, icon128.png) first, or the extension will show warnings (but still work).

### 5. Start Voice Control

```bash
cd /Users/nav/Documents/code/temp/browser/voice_browser
uv run main.py
```

Server runs on: `http://localhost:8080`

---

## 🎤 Voice Commands

### Quick Commands (Local STT - Always Listening)

**Navigation:**
- "go to google.com"
- "open youtube"
- "search for python tutorials"

**Scrolling:**
- "scroll down"
- "scroll up"
- "go to top"
- "go to bottom"

**Clicking:**
- "click search button"
- "press submit"
- "click sign in"

**Typing:**
- "type hello world"
- "enter my email"

**Tabs:**
- "new tab"
- "close tab"
- "next tab"
- "previous tab"
- "switch to tab 2"

**Browser:**
- "go back"
- "go forward"
- "refresh"

### Fish Transcription Mode (Long Text)

1. Say: **"Hey Fish"**
2. Wait for: "Ready for transcription"
3. Speak your long text
4. Say: **"Done Fish"**
5. Text appears in active field

### Complex Tasks (AI Agent)

Multi-step tasks using browser-use:
- "book a flight from SFO to JFK"
- "compare laptop prices under $1000"
- "find cheapest hotel in Paris"
- "order pizza from Domino's"

---

## 🏗️ Architecture

```
Microphone → Local STT (Whisper) → Command Parser → Browser Actions
                ↓
            "Hey Fish" detected
                ↓
        Fish Audio STT (Cloud) → Transcription → Type in Field
                ↓
            "Done Fish"
                ↓
        Back to Local STT

All actions → Fish Audio TTS → Audio Feedback
```

---

## 📁 Project Structure

```
voice_browser/
├── services/
│   ├── local_stt.py       # Faster-whisper for commands
│   ├── fish_stt.py        # Fish Audio for transcription
│   └── fish_tts.py        # Fish Audio voice feedback
├── parsers/
│   └── command_parser.py  # NL → structured commands
├── controllers/
│   └── browser_controller.py  # browser-use + WebSocket
├── control_hub.py         # FastAPI orchestrator
├── main.py               # Entry point
├── start.sh              # Setup script
└── README.md            # Full documentation

chrome_extension/         # Chrome extension
├── manifest.json
├── background.js        # WebSocket client
├── content.js          # DOM actions
└── popup.html          # Status UI
```

---

## 🔧 Configuration

### Adjust STT Sensitivity

Edit `services/local_stt.py`:

```python
LocalSTT(
    model_size="base.en",    # tiny.en (faster) | small.en (accurate)
    vad_threshold=0.02,      # Lower = more sensitive
    silence_duration=1.0,    # Seconds before transcribing
)
```

### Change Voice Feedback

Edit `control_hub.py`:

```python
self.fish_tts = FishTTS(
    api_key=fish_api_key,
    voice_id="your_voice_id",  # Optional custom voice
)
```

### Browser-use LLM

The system uses environment variables:
- `OPENAI_API_KEY` → Uses GPT-4
- `ANTHROPIC_API_KEY` → Uses Claude
- `GROQ_API_KEY` → Uses Groq models

---

## 🐛 Troubleshooting

### No audio detected

```bash
# Check microphone permissions
System Preferences → Security & Privacy → Privacy → Microphone

# Test microphone
python -c "import sounddevice as sd; print(sd.query_devices())"

# Lower VAD threshold in local_stt.py
vad_threshold=0.01  # More sensitive
```

### Chrome connection failed

```bash
# Check Chrome is running with debugging
curl http://localhost:9222/json

# Restart Chrome with correct flags
killall "Google Chrome"
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-voice-browser &
```

### Extension not working

1. Check extension is loaded: `chrome://extensions/`
2. Check WebSocket connection in extension popup
3. View background service worker logs
4. Ensure server is running on port 8080

### Fish Audio errors

```bash
# Verify API key
curl -H "Authorization: Bearer $FISH_AUDIO_API_KEY" \
  https://api.fish.audio/v1/models

# Check account credits
# Visit: https://fish.audio/console
```

### Commands not recognized

Check logs:
```bash
# Server logs show parsed commands
# Look for: "Parsing command: ..." and "Parsed as ..."
```

Add custom patterns in `parsers/command_parser.py`

---

## 🧪 Testing

### Test Local STT

```bash
cd voice_browser
uv run python -c "
from services.local_stt import LocalSTT
import time

def print_result(text):
    print(f'Transcribed: {text}')

stt = LocalSTT()
stt.start_listening(print_result)
print('Listening for 30 seconds...')
time.sleep(30)
stt.stop_listening()
"
```

### Test Command Parser

```bash
uv run python -c "
from parsers.command_parser import CommandParser
p = CommandParser()
print(p.parse('scroll down'))
print(p.parse('go to google.com'))
print(p.parse('book a flight to NYC'))
"
```

### Test Fish TTS

```bash
uv run python -c "
import asyncio
from services.fish_tts import FishTTS
import os

async def test():
    tts = FishTTS(api_key=os.getenv('FISH_AUDIO_API_KEY'))
    await tts.speak('Hello from Fish Audio')

asyncio.run(test())
"
```

---

## 📊 Performance

- **Local STT Latency**: ~500ms (base.en model)
- **Fish Audio STT**: ~2-3s (cloud processing)
- **Command Execution**: <100ms (simple actions)
- **Complex Tasks**: Variable (depends on task complexity)

**Optimize for speed:**
- Use `tiny.en` model for STT (faster, less accurate)
- Reduce `silence_duration` to 0.5s
- Use local TTS instead of Fish Audio

---

## 🔐 Privacy

- **Local STT**: All audio processed on-device (faster-whisper)
- **Fish Audio**: Audio sent to cloud for transcription/TTS
- **browser-use**: Task descriptions sent to LLM API
- **No telemetry**: System doesn't collect or send usage data

---

## 📝 Adding Custom Commands

1. Edit `parsers/command_parser.py`
2. Add pattern and parser function
3. Update `controllers/browser_controller.py` to handle action
4. Test with voice command

Example - Add "zoom in" command:

```python
# In command_parser.py
CommandType.ZOOM: [
    (r"zoom (in|out)", self._parse_zoom),
],

def _parse_zoom(self, match) -> Dict[str, Any]:
    direction = match.group(1)
    return {"direction": direction}

# In browser_controller.py
elif cmd_type == "zoom":
    direction = command.get("direction")
    action = {"type": "zoom", "direction": direction}
```

---

## 🎯 Next Steps

1. **Add wake word**: Integrate Porcupine for "Hey Browser"
2. **Visual feedback**: Create overlay showing current command
3. **Command history**: Log and replay commands
4. **Multi-language**: Support languages beyond English
5. **Custom voices**: Train Fish Audio voice models
6. **Offline mode**: Use local TTS (piper, coqui)

---

## 📚 Resources

- **browser-use**: https://github.com/browser-use/browser-use
- **faster-whisper**: https://github.com/SYSTRAN/faster-whisper
- **Fish Audio**: https://fish.audio/docs
- **Chrome DevTools Protocol**: https://chromedevtools.github.io/devtools-protocol/

---

## 🤝 Support

Issues? Check:
1. Server logs (stdout)
2. Chrome extension console
3. Browser DevTools console
4. README.md full documentation

---

**Happy Voice Browsing! 🎤✨**
