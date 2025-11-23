# Voice Browser Quick Reference Card

## 🚀 Start Server
```bash
cd browser/voice_browser
./start.sh
```

## 🎤 Voice Commands Cheat Sheet

### Navigation
```
"go to google.com"
"open youtube"
"visit reddit.com"
```

### Search
```
"search for python tutorials"
"google best restaurants near me"
"find machine learning courses"
```

### Scrolling
```
"scroll down"
"scroll up"
"page down"
"go to top"
"go to bottom"
```

### Clicking
```
"click search button"
"press submit"
"click sign in"
"select first result"
```

### Typing
```
"type hello world"
"enter my email address"
"input test message"
```

### Tabs
```
"new tab"
"close tab"
"next tab"
"previous tab"
"switch to tab 2"
```

### Browser Controls
```
"go back"
"go forward"
"refresh"
"reload"
"stop"
```

### Fish Transcription Mode
```
1. Say: "Hey Fish"
2. [wait for confirmation]
3. Speak your long text
4. Say: "Done Fish"
5. Text appears in active field
```

### Complex Tasks (AI Agent)
```
"book a flight from SFO to JFK"
"compare laptop prices under $1000"
"find cheapest hotel in Paris for next week"
"order a large pepperoni pizza"
```

## 🔧 Quick Troubleshooting

### No audio detected
```bash
# Check microphone in System Preferences
# Lower sensitivity in services/local_stt.py
vad_threshold=0.01
```

### Chrome not connecting
```bash
# Start Chrome with debugging
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-voice-browser &
```

### Extension not loaded
```
1. chrome://extensions/
2. Enable "Developer mode"
3. Load unpacked: browser/chrome_extension/
```

### API key errors
```bash
export FISH_AUDIO_API_KEY="your_key"
export OPENAI_API_KEY="your_key"  # or ANTHROPIC_API_KEY
```

## 📊 Status Check

### Test installation
```bash
cd voice_browser
uv run python test_setup.py
```

### Check server status
```bash
curl http://localhost:8080/
```

### View logs
```
Server logs appear in terminal where you ran main.py
```

## 🎯 API Keys Needed

1. **FISH_AUDIO_API_KEY** (optional but recommended)
   - Get from: https://fish.audio/
   - Used for: TTS + Fish transcription mode

2. **OPENAI_API_KEY** or **ANTHROPIC_API_KEY** (for complex tasks)
   - OpenAI: https://platform.openai.com/
   - Anthropic: https://console.anthropic.com/
   - Used for: Complex multi-step tasks

## 📱 Extension Popup

Click extension icon to see:
- ✓ Connection status
- ✓ Listening state
- ✓ Fish mode active/inactive
- ✓ Quick command examples

## 🔄 Restart Everything

```bash
# Kill all processes
killall "Google Chrome"
pkill -f "main.py"

# Restart
cd browser/voice_browser
./start.sh

# In another terminal, start Chrome
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-voice-browser &
```

## 📚 Full Documentation

- README.md - Complete technical docs
- SETUP_GUIDE.md - Detailed setup instructions
- IMPLEMENTATION_SUMMARY.md - What was built

---

**Server**: http://localhost:8080
**WebSocket**: ws://localhost:8080/ws
**Chrome CDP**: http://localhost:9222

---

**Quick Start**: `cd voice_browser && ./start.sh`
