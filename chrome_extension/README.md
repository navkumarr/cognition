# Voice Browser Chrome Extension

Real-time status overlay showing voice recognition and agent activity.

## Features

- **Status Indicator**: Green (Ready) → Blue (Listening) → Orange (Processing) → Red (Error)
- **Live Transcription**: Shows what you're saying in real-time
- **Non-intrusive**: Top-right overlay, doesn't block page content
- **Always visible**: Works on all websites

## Installation

1. **Open Chrome Extensions**
   ```
   chrome://extensions/
   ```

2. **Enable Developer Mode**
   - Toggle the switch in the top right

3. **Load Extension**
   - Click "Load unpacked"
   - Select this directory: `/Users/nav/Documents/code/temp/browser/chrome_extension/`

4. **Verify**
   - You should see "Voice Browser Control" in your extensions list
   - Visit any website and you'll see a status widget in the top right

## Usage

The widget automatically shows:
- 🟢 **Green "Ready"**: System is idle, waiting for commands
- 🔵 **Blue "Listening"**: Actively transcribing speech
- 🟠 **Orange "Processing/Executing"**: Running a command or AI agent
- 🔴 **Red "Error/Failed"**: Command failed

When you speak, your transcription appears below the status indicator for 3 seconds.

## Troubleshooting

**Widget not appearing?**
- Refresh the page after installing the extension
- Check that the extension is enabled in chrome://extensions/

**Status not updating?**
- Make sure the voice browser backend is running (`./start_voice_browser.sh`)
- Check Chrome's DevTools console for errors (F12)

**Connection issues?**
- The extension connects to `ws://localhost:8765`
- Ensure the voice browser server is running on port 8080
