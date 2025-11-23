"""Central control hub for voice-controlled browser."""

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from services.local_stt import LocalSTT
from services.fish_stt import FishSTT
from services.fish_tts import FishTTS
from parsers.command_parser import CommandParser, CommandType
from controllers.browser_controller import BrowserController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voice Browser Control Hub")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VoiceBrowserHub:
    """Central hub orchestrating voice control components."""
    
    def __init__(self):
        """Initialize voice browser hub."""
        # Get API key from environment
        fish_api_key = os.getenv("FISH_AUDIO_API_KEY", "")
        
        # Initialize components
        self.local_stt = LocalSTT()
        self.fish_stt = FishSTT(api_key=fish_api_key) if fish_api_key else None
        self.fish_tts = FishTTS(api_key=fish_api_key) if fish_api_key else None
        self.parser = CommandParser()
        self.browser_controller = BrowserController()
        
        # State
        self.is_local_listening = False
        self.is_fish_active = False
        
        logger.info("Voice Browser Hub initialized")
    
    async def start(self):
        """Start the hub."""
        await self.browser_controller.initialize()
        self._start_local_listening()
        logger.info("Voice Browser Hub started")
    
    def _start_local_listening(self):
        """Start local STT for command listening."""
        if not self.is_local_listening:
            # Pass the current event loop to local_stt
            import asyncio
            try:
                self.local_stt.event_loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.warning("No running event loop found")
            
            self.local_stt.start_listening(self._handle_local_transcription)
            self.is_local_listening = True
            logger.info("Local STT listening started")
    
    def _stop_local_listening(self):
        """Stop local STT."""
        if self.is_local_listening:
            self.local_stt.stop_listening()
            self.is_local_listening = False
            logger.info("Local STT stopped")
    
    async def _handle_local_transcription(self, text: str):
        """
        Handle transcription from local STT.
        
        Args:
            text: Transcribed text
        """
        text_lower = text.lower().strip()
        
        # Check for Fish Audio activation
        if "hey fish" in text_lower and self.fish_stt:
            logger.info("Fish Audio activated")
            self._stop_local_listening()
            self.fish_stt.activate(self._handle_fish_transcription)
            self.is_fish_active = True
            
            if self.fish_tts:
                await self.fish_tts.speak("Ready for transcription", blocking=False)
            return
        
        # Check for Fish Audio deactivation
        if "done fish" in text_lower and self.is_fish_active:
            logger.info("Fish Audio deactivated")
            self.fish_stt.deactivate()
            self.is_fish_active = False
            self._start_local_listening()
            
            if self.fish_tts:
                await self.fish_tts.speak("Transcription complete", blocking=False)
            return
        
        # Process as command
        await self._process_command(text)
    
    async def _handle_fish_transcription(self, text: str):
        """
        Handle transcription from Fish Audio STT.
        
        Args:
            text: Transcribed text
        """
        logger.info(f"Fish transcription: {text}")
        
        # For now, just log it - you could send it to a text field
        if self.fish_tts:
            await self.fish_tts.speak("Transcription received", blocking=False)
        
        # Send to active text field via browser controller
        command = {
            "type": CommandType.TYPE,
            "text": text,
        }
        await self.browser_controller.execute_simple_action(command)
    
    async def _process_command(self, text: str):
        """
        Process voice command.
        
        Args:
            text: Command text
        """
        print(f"\n⚙️  PROCESSING: {text}")
        
        # Parse command
        command = self.parser.parse(text)
        cmd_type = command.get("type")
        print(f"📋 COMMAND TYPE: {cmd_type}")
        
        if cmd_type == CommandType.UNKNOWN:
            if self.fish_tts:
                await self.fish_tts.speak("Command not recognized", blocking=False)
            return
        
        # Execute command
        if cmd_type == CommandType.COMPLEX_TASK:
            # Use browser-use for complex tasks
            print("🤖 Using AI agent for complex task...")
            if self.fish_tts:
                await self.fish_tts.speak("Executing task", blocking=False)
            
            description = command.get("description")
            result = await self.browser_controller.execute_complex_task(description)
            print(f"✅ Task result: {result}")
            
            if self.fish_tts:
                await self.fish_tts.speak("Task complete", blocking=False)
        else:
            # Use simple actions for direct commands
            print(f"🎯 Executing action: {command}")
            success = await self.browser_controller.execute_simple_action(command)
            
            if success:
                print("✅ Action completed successfully")
                if self.fish_tts:
                    await self.fish_tts.speak("Done", blocking=False)
            else:
                print("❌ Action failed")
                if self.fish_tts:
                    await self.fish_tts.speak("Failed", blocking=False)
    
    async def cleanup(self):
        """Clean up resources."""
        self._stop_local_listening()
        await self.browser_controller.cleanup()
        logger.info("Voice Browser Hub cleaned up")


# Global hub instance
hub: Optional[VoiceBrowserHub] = None


@app.on_event("startup")
async def startup():
    """Start hub on app startup."""
    global hub
    hub = VoiceBrowserHub()
    await hub.start()


@app.on_event("shutdown")
async def shutdown():
    """Clean up on shutdown."""
    global hub
    if hub:
        await hub.cleanup()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Voice Browser Control Hub",
        "status": "running",
        "local_stt": hub.is_local_listening if hub else False,
        "fish_active": hub.is_fish_active if hub else False,
    }


@app.post("/command")
async def execute_command(text: str):
    """
    Execute voice command via HTTP.
    
    Args:
        text: Command text
    """
    if hub:
        await hub._process_command(text)
        return {"status": "processed", "command": text}
    return {"status": "error", "message": "Hub not initialized"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Process command
            if hub:
                await hub._process_command(data)
                await websocket.send_text(f"Processed: {data}")
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the FastAPI server."""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
