# Voice-Controlled Browser - System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER SPEAKS                                  │
│                    "scroll down" / "Hey Fish"                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      MICROPHONE INPUT                                │
│                   (System Audio Device)                              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────────┐
        │        STT SELECTION LAYER                 │
        │  (Automatic based on "Hey Fish")          │
        └────────┬──────────────────────┬────────────┘
                 │                      │
        ┌────────▼─────────┐   ┌───────▼────────┐
        │   Local STT      │   │   Fish STT     │
        │  (faster-whisper)│   │  (Cloud API)   │
        │                  │   │                │
        │  • Always on     │   │  • "Hey Fish"  │
        │  • ~500ms        │   │  • ~2-3s       │
        │  • Offline       │   │  • Cloud       │
        │  • Commands      │   │  • Long text   │
        └────────┬─────────┘   └───────┬────────┘
                 │                     │
                 └──────────┬──────────┘
                            │
                            ▼
        ┌──────────────────────────────────────────┐
        │         COMMAND PARSER                   │
        │    (Natural Language Processing)         │
        │                                          │
        │  Input: "scroll down"                   │
        │  Output: {type: "scroll", dir: "down"}  │
        └──────────────────┬───────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────┐
        │         CONTROL HUB (FastAPI)            │
        │      Orchestrates All Components         │
        │                                          │
        │  • Routes commands                       │
        │  • Manages state                         │
        │  • Coordinates services                  │
        └──────────┬──────────────────┬────────────┘
                   │                  │
         ┌─────────▼────────┐  ┌─────▼──────────┐
         │  Simple Actions  │  │ Complex Tasks  │
         │  (Fast path)     │  │ (AI path)      │
         └─────────┬────────┘  └─────┬──────────┘
                   │                 │
         ┌─────────▼────────┐  ┌─────▼──────────┐
         │ Chrome Extension │  │  browser-use   │
         │   (WebSocket)    │  │   AI Agent     │
         │                  │  │                │
         │  • Scroll        │  │  • Book flight │
         │  • Click         │  │  • Compare     │
         │  • Type          │  │  • Fill forms  │
         │  • Navigate      │  │  • Multi-step  │
         └─────────┬────────┘  └─────┬──────────┘
                   │                 │
                   └────────┬────────┘
                            │
                            ▼
        ┌──────────────────────────────────────────┐
        │         CHROMIUM BROWSER                 │
        │    (Remote Debugging Mode: 9222)         │
        │                                          │
        │  • Executes actions                      │
        │  • Renders pages                         │
        │  • Manages tabs                          │
        └────────────────────┬─────────────────────┘
                             │
                             ▼
        ┌──────────────────────────────────────────┐
        │         FISH AUDIO TTS                   │
        │       (Voice Feedback)                   │
        │                                          │
        │  Output: "Done" / "Scrolling" / etc.    │
        └────────────────────┬─────────────────────┘
                             │
                             ▼
        ┌──────────────────────────────────────────┐
        │         SPEAKER OUTPUT                   │
        │      (Confirmation Audio)                │
        └──────────────────────────────────────────┘
```

---

## Component Communication

```
┌─────────────────┐
│   Local STT     │─────────┐
│  (Port: N/A)    │         │
└─────────────────┘         │
                            │
┌─────────────────┐         │    ┌──────────────────┐
│   Fish STT      │─────────┼───▶│  Control Hub     │
│  (Cloud API)    │         │    │  (Port: 8080)    │
└─────────────────┘         │    │                  │
                            │    │  • FastAPI       │
┌─────────────────┐         │    │  • WebSocket     │
│  Command Parser │─────────┘    │  • HTTP REST     │
│   (Library)     │              └────────┬─────────┘
└─────────────────┘                       │
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
          ┌─────────▼──────────┐  ┌──────▼──────┐  ┌──────────▼────────┐
          │ Chrome Extension   │  │ browser-use │  │   Fish TTS        │
          │  (WebSocket Client)│  │  AI Agent   │  │  (Cloud API)      │
          │                    │  │             │  │                   │
          │  ws://localhost:   │  │  CDP: 9222  │  │  HTTPS API        │
          │        8080/ws     │  │             │  │                   │
          └─────────┬──────────┘  └──────┬──────┘  └───────────────────┘
                    │                    │
                    └──────────┬─────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Chromium Browser   │
                    │  (CDP Port: 9222)   │
                    │                     │
                    │  http://localhost:  │
                    │         9222        │
                    └─────────────────────┘
```

---

## Data Flow Examples

### Example 1: Simple Command ("scroll down")

```
1. User speaks: "scroll down"
   │
2. Microphone captures audio
   │
3. Local STT (faster-whisper) transcribes → "scroll down"
   │
4. Command Parser analyzes → {type: "scroll", direction: "down"}
   │
5. Control Hub receives parsed command
   │
6. Browser Controller sends to Chrome Extension via WebSocket
   │
7. Chrome Extension content script executes:
   window.scrollBy({top: window.innerHeight * 0.8, behavior: 'smooth'})
   │
8. Fish TTS speaks: "Done"
   │
9. Speaker outputs confirmation
```

### Example 2: Fish Transcription ("Hey Fish" → text → "Done Fish")

```
1. User speaks: "Hey Fish"
   │
2. Local STT transcribes → "hey fish"
   │
3. Control Hub detects wake phrase
   │
4. Local STT stops, Fish STT activates
   │
5. Fish TTS speaks: "Ready for transcription"
   │
6. User speaks long text: "This is a long paragraph about..."
   │
7. User speaks: "Done Fish"
   │
8. Fish STT sends accumulated audio to Fish Audio API
   │
9. Fish Audio returns transcription
   │
10. Control Hub types transcription into active field
    │
11. Fish TTS speaks: "Transcription complete"
    │
12. Local STT resumes listening
```

### Example 3: Complex Task ("book a flight to NYC")

```
1. User speaks: "book a flight to NYC"
   │
2. Local STT transcribes → "book a flight to nyc"
   │
3. Command Parser detects complex task
   │
4. Control Hub routes to browser-use controller
   │
5. Fish TTS speaks: "Executing task"
   │
6. browser-use Agent:
   a. Opens Google Flights
   b. Enters NYC as destination
   c. Selects dates
   d. Compares prices
   e. (Optionally) Books flight
   │
7. Fish TTS speaks: "Task complete"
```

---

## File Responsibilities

```
services/
├── local_stt.py      → Audio capture → VAD → Whisper → Text
├── fish_stt.py       → Audio buffer → Fish API → Text
└── fish_tts.py       → Text → Fish API → MP3 → Speaker

parsers/
└── command_parser.py → Text → Regex patterns → Structured command

controllers/
└── browser_controller.py → Command → WebSocket/browser-use → Execution

control_hub.py → Orchestrates everything + FastAPI server
main.py → Entry point + initialization

Chrome Extension:
├── background.js → WebSocket client + Tab management
└── content.js → DOM manipulation + Action execution
```

---

## State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                     VOICE BROWSER STATE                      │
└─────────────────────────────────────────────────────────────┘

States:
1. IDLE
   - Local STT listening
   - Waiting for voice input
   
2. PROCESSING_COMMAND
   - Transcribed text received
   - Parsing command
   - Routing to executor
   
3. FISH_MODE_ACTIVE
   - Fish STT recording
   - Local STT paused
   - Waiting for "Done Fish"
   
4. EXECUTING_ACTION
   - Command being executed
   - Browser responding
   - TTS providing feedback
   
5. COMPLEX_TASK_RUNNING
   - browser-use agent active
   - Multi-step execution
   - Progress updates via TTS

Transitions:
IDLE → PROCESSING_COMMAND (voice detected)
PROCESSING_COMMAND → FISH_MODE_ACTIVE ("Hey Fish")
FISH_MODE_ACTIVE → PROCESSING_COMMAND ("Done Fish")
PROCESSING_COMMAND → EXECUTING_ACTION (simple command)
PROCESSING_COMMAND → COMPLEX_TASK_RUNNING (complex task)
EXECUTING_ACTION → IDLE (action complete)
COMPLEX_TASK_RUNNING → IDLE (task complete)
```

---

## Network Ports

```
8080  → Control Hub (FastAPI + WebSocket)
9222  → Chrome Remote Debugging (CDP)
N/A   → Fish Audio API (HTTPS cloud)
N/A   → OpenAI/Anthropic API (HTTPS cloud)
```

---

## Technology Stack Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                          │
│                   (Voice + Browser)                          │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                         │
│  • Chrome Extension (JavaScript)                             │
│  • Chrome Browser (Chromium)                                 │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                          │
│  • FastAPI (Web Framework)                                   │
│  • WebSocket (Real-time communication)                       │
│  • Command Parser (NLP)                                      │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                   BUSINESS LOGIC LAYER                       │
│  • Browser Controller (Automation)                           │
│  • browser-use Agent (AI automation)                         │
│  • State Management                                          │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                   SERVICES LAYER                             │
│  • Local STT (faster-whisper)                                │
│  • Fish Audio STT (Cloud)                                    │
│  • Fish Audio TTS (Cloud)                                    │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                       │
│  • Python Runtime (3.12)                                     │
│  • uv (Package manager)                                      │
│  • Virtual Environment                                       │
│  • System Audio (sounddevice)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Model

```
┌─────────────────────────────────────────────────────────────┐
│                      SECURITY LAYERS                         │
└─────────────────────────────────────────────────────────────┘

1. LOCAL PROCESSING
   ✓ Audio processing on-device (Local STT)
   ✓ No audio sent to cloud unless user says "Hey Fish"
   ✓ Command parsing local

2. API SECURITY
   ✓ API keys in environment variables
   ✓ HTTPS for all cloud APIs
   ✓ No credentials in code

3. BROWSER ISOLATION
   ✓ Chrome runs in separate profile
   ✓ Remote debugging limited to localhost
   ✓ Extension permissions minimal

4. NETWORK SECURITY
   ✓ WebSocket local only (localhost:8080)
   ✓ No external WebSocket connections
   ✓ CORS enabled for localhost only

5. DATA PRIVACY
   ✓ No telemetry
   ✓ No logging of sensitive data
   ✓ No data persistence (except Chrome profile)
```

---

This architecture ensures:
- ✅ Low latency for common commands
- ✅ High accuracy for transcription
- ✅ Extensibility for new features
- ✅ Privacy-first design
- ✅ Reliable voice feedback
