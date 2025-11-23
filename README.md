# Voice-Controlled Web Browser

Fully voice-controlled web browser using Chromium, browser-use AI agent, and Fish Audio for TTS feedback.

## Features

- **Dual STT System**:
  - Local STT (faster-whisper): Quick commands like "scroll down", "click button"
  - Fish Audio STT: High-quality transcription for long text (activated by "Hey Fish")

- **Voice Commands**:
  - Scrolling: "scroll down", "page up", "go to top"
  - Navigation: "go to google.com", "open youtube"
  - Clicking: "click search button", "press submit"
  - Typing: "type hello world", "enter my email"
  - Search: "search for python tutorials", "google best restaurants"
  - Tabs: "new tab", "close tab", "next tab", "switch to tab 2"
  - Browser: "go back", "refresh", "stop"

- **Complex Tasks** (browser-use AI):
  - "book a flight to NYC"
  - "compare laptop prices under $1000"
  - "find cheapest hotel in Paris"

- **Fish Audio TTS**: Voice feedback for all actions

## Setup

### 1. Install Dependencies

```bash
cd /Users/nav/Documents/code/temp/browser/voice_browser
uv venv
source .venv/bin/activate  # or .venv/bin/activate.fish for fish shell
uv pip install -e .
```

### 2. Set Environment Variables

```bash
# Required for Fish Audio TTS/STT
export FISH_AUDIO_API_KEY="your-api-key-here"

# Optional: OpenAI/Anthropic for browser-use complex tasks
export OPENAI_API_KEY="your-openai-key"
# or
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### 3. Start Chrome with Remote Debugging

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-voice-browser
```

### 4. Install Chrome Extension (Optional, for simple actions)

The Chrome extension at `../../iris/chrome_letta_actions/` can execute simple DOM actions.

1. Open Chrome: `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `iris/chrome_letta_actions/` directory

### 5. Run Voice Browser

```bash
# Using uv
uv run main.py

# Or with activated venv
python main.py
```

The server will start on `http://localhost:8080`

## Usage

### Quick Commands (Local STT)

Just speak naturally:
- "scroll down"
- "go to reddit.com"
- "click sign in"
- "search for machine learning"
- "new tab"

The system listens continuously and responds with TTS feedback.

### Fish Transcription Mode

For typing long text:
1. Say: **"Hey Fish"**
2. Wait for confirmation ("Ready for transcription")
3. Speak your text
4. Say: **"Done Fish"**
5. Text is typed into active field

### Complex Tasks

Say multi-step tasks:
- "book a flight from SFO to JFK on December 25th"
- "find and compare prices for iPhone 15"
- "order a large pepperoni pizza from Domino's"

The browser-use AI agent will execute multiple steps automatically.

## Architecture

```
┌─────────────────────────────────────┐
│   Voice Input (Microphone)          │
└──────────────┬──────────────────────┘
               │
     ┌─────────┴─────────┐
     ▼                   ▼
┌─────────┐        ┌──────────┐
│ Local   │        │  Fish    │
│ STT     │        │  Audio   │
│(Whisper)│        │  STT     │
└────┬────┘        └────┬─────┘
     │                  │
     │ "Hey Fish" detected
     └──────────────────┤
                        │
     ┌──────────────────▼──────────────┐
     │    Command Parser               │
     │  (Natural Language → Actions)   │
     └──────────────────┬──────────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
     ┌────────┐   ┌─────────┐  ┌──────────┐
     │ Simple │   │ Complex │  │   Fish   │
     │ Action │   │  Task   │  │   TTS    │
     │        │   │ (AI)    │  │ Feedback │
     └────┬───┘   └────┬────┘  └──────────┘
          │            │
          ▼            ▼
     Chrome Ext   browser-use
          │            │
          └─────┬──────┘
                ▼
           Chromium Browser
```

## API Endpoints

### HTTP

- `GET /`: Status and health check
- `POST /command?text=<command>`: Execute command via HTTP

### WebSocket

- `ws://localhost:8080/ws`: Real-time command execution

## Configuration

Edit `control_hub.py` to customize:

- **STT Models**: Change `LocalSTT(model_size="base.en")` to `"tiny.en"` (faster) or `"small.en"` (more accurate)
- **Voice Activity Detection**: Adjust `vad_threshold` in LocalSTT
- **Silence Duration**: Change `silence_duration` (default 1.0s)
- **Chrome CDP URL**: Change `cdp_url` if not using port 9222

## Troubleshooting

### No audio detected
- Check microphone permissions
- Adjust `vad_threshold` in `services/local_stt.py`
- Test with: `python -c "import sounddevice; print(sounddevice.query_devices())"`

### Chrome connection failed
- Ensure Chrome is running with `--remote-debugging-port=9222`
- Check if port 9222 is accessible: `curl http://localhost:9222/json`

### Fish Audio errors
- Verify `FISH_AUDIO_API_KEY` is set correctly
- Check API key has credits/is valid
- Review logs for API error messages

### Browser-use fails
- Set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- Complex tasks require LLM API access
- Check browser-use logs for specific errors

## Development

### Project Structure

```
voice_browser/
├── services/
│   ├── local_stt.py      # Local speech-to-text
│   ├── fish_stt.py       # Fish Audio STT
│   └── fish_tts.py       # Fish Audio TTS
├── parsers/
│   └── command_parser.py # NL command parsing
├── controllers/
│   └── browser_controller.py  # Browser automation
├── control_hub.py        # FastAPI orchestrator
└── main.py              # Entry point
```

### Adding Commands

Edit `parsers/command_parser.py`:

```python
# Add pattern
CommandType.YOUR_COMMAND: [
    (r"your pattern", self._parse_your_command),
],

# Add parser
def _parse_your_command(self, match) -> Dict[str, Any]:
    return {"param": match.group(1)}
```

### Testing

```bash
# Test STT only
python -c "from services.local_stt import LocalSTT; stt = LocalSTT(); stt.start_listening(print); import time; time.sleep(30)"

# Test command parser
python -c "from parsers.command_parser import CommandParser; p = CommandParser(); print(p.parse('scroll down'))"

# Test browser controller
python -c "import asyncio; from controllers.browser_controller import BrowserController; bc = BrowserController(); asyncio.run(bc.execute_simple_action({'type': 'scroll', 'direction': 'down'}))"
```

## License

MIT
