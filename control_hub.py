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

from services.fish_stt_continuous_v2 import FishSTTContinuousV2
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
        
        if not fish_api_key:
            raise ValueError("FISH_AUDIO_API_KEY environment variable is required")
        
        # Initialize components
        self.local_stt = FishSTTContinuousV2(
            api_key=fish_api_key,
            silence_threshold=0.02,
            silence_duration=1.0,
            min_audio_duration=0.5,
            status_callback=self._handle_stt_status
        )
        self.fish_stt = FishSTT(api_key=fish_api_key)
        self.fish_tts = FishTTS(api_key=fish_api_key) if fish_api_key else None
        self.parser = CommandParser()
        self.browser_controller = BrowserController()
        
        # State
        self.is_local_listening = False
        self.is_fish_active = False
        
        # Task management - ensure only one task runs at a time
        self.is_task_running = False
        
        # WebSocket connections for status updates
        self.ws_connections: set = set()
        
        # Store event loop for thread-safe async calls
        self.event_loop = None
        
        logger.info("Voice Browser Hub initialized")
    
    async def start(self):
        """Start the hub."""
        # Store the event loop for thread-safe async calls
        import asyncio
        self.event_loop = asyncio.get_running_loop()
        logger.info(f"Event loop stored: {self.event_loop}")
        
        await self.browser_controller.initialize()
        self._start_local_listening()
        logger.info("Voice Browser Hub started (using Fish Audio V2)")
    
    def _start_local_listening(self):
        """Start local STT for command listening."""
        if not self.is_local_listening:
            # V2 doesn't need event loop - uses threading
            self.local_stt.start_listening(
                self._handle_local_transcription_sync
            )
            self.is_local_listening = True
            logger.info("Local STT listening started (V2)")
    
    def _stop_local_listening(self):
        """Stop local STT."""
        if self.is_local_listening:
            self.local_stt.stop_listening()
            self.is_local_listening = False
            logger.info("Local STT stopped")
    
    def _handle_stt_status(self, status: str, text: str):
        """Handle status updates from STT service (called from thread)."""
        if self.event_loop and self.event_loop.is_running():
            import asyncio
            asyncio.run_coroutine_threadsafe(
                self.broadcast_status(status, text),
                self.event_loop
            )
        else:
            logger.error("No event loop available for status update")
    
    def _handle_local_transcription_sync(self, text: str):
        """
        Handle transcription from local STT (synchronous wrapper for V2).
        
        Args:
            text: Transcribed text
        """
        # V2 calls this from a thread, so schedule async handler
        if self.event_loop and self.event_loop.is_running():
            import asyncio
            asyncio.run_coroutine_threadsafe(
                self._handle_local_transcription(text),
                self.event_loop
            )
        else:
            logger.error("No event loop available to handle transcription")
    
    async def _handle_local_transcription(self, text: str):
        """
        Handle transcription from local STT.
        
        Args:
            text: Transcribed text
        """
        # Broadcast the final transcription (but don't change status yet)
        await self.broadcast_transcription(text, partial=False)
        
        text_lower = text.lower().strip()
        
        # Check for Fish Audio activation
        if "hey fish" in text_lower and self.fish_stt:
            logger.info("Fish Audio activated")
            await self.broadcast_status("listening", "Fish Audio Active")
            self._stop_local_listening()
            self.fish_stt.activate(self._handle_fish_transcription)
            self.is_fish_active = True
            
            return
        
        # Check for Fish Audio deactivation
        if "done fish" in text_lower and self.is_fish_active:
            logger.info("Fish Audio deactivated")
            await self.broadcast_status("idle", "Ready")
            self.fish_stt.deactivate()
            self.is_fish_active = False
            self._start_local_listening()
    
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
        # Check if a task is already running
        if self.is_task_running:
            logger.warning("Task already running, ignoring new command")
            print("⚠️  Task already in progress")
            return
        
        print(f"\n⚙️  PROCESSING: {text}")
        await self.broadcast_status("processing", "Processing...")
        
        # Parse command
        command = self.parser.parse(text)
        cmd_type = command.get("type")
        print(f"📋 COMMAND TYPE: {cmd_type}")
        print(f"📋 FULL COMMAND: {command}")
        
        if cmd_type == CommandType.UNKNOWN:
            print("⚠️  Command not recognized")
            await self.broadcast_status("error", "Command not recognized")
            # Reset to ready after error
            await asyncio.sleep(2)
            await self.broadcast_status("idle", "Ready")
            return
        
        # Execute command
        if cmd_type == CommandType.COMPLEX_TASK:
            # Use browser-use for complex tasks
            description = command.get("description")
            print(f"🤖 Using AI agent for complex task: '{description}'")
            
            # Mark task as running
            self.is_task_running = True
            
            await self.broadcast_status("processing", "AI agent working...")
            
            try:
                result = await self.browser_controller.execute_complex_task(description)
                print(f"✅ Task result: {result}")
                await self.broadcast_status("idle", "Ready")
            except Exception as e:
                print(f"❌ Task failed: {e}")
                await self.broadcast_status("error", "Task failed")
                await asyncio.sleep(2)
                await self.broadcast_status("idle", "Ready")
            finally:
                # Always reset task state
                self.is_task_running = False
        else:
            # Use simple actions for direct commands
            print(f"🎯 Executing simple action...")
            print(f"   Type: {cmd_type}")
            print(f"   Details: {command}")
            
            # Mark task as running
            self.is_task_running = True
            
            await self.broadcast_status("processing", "Executing action...")
            
            try:
                success = await self.browser_controller.execute_simple_action(command)
                
                if success:
                    print("✅ Action completed successfully")
                    await self.broadcast_status("idle", "Ready")
                else:
                    print("❌ Action failed")
                    await self.broadcast_status("error", "Action failed")
                    # Reset to ready after error
                    await asyncio.sleep(2)
                    await self.broadcast_status("idle", "Ready")
            except Exception as e:
                print(f"❌ Action error: {e}")
                await self.broadcast_status("error", "Action error")
                await asyncio.sleep(2)
                await self.broadcast_status("idle", "Ready")
            finally:
                # Always reset task state
                self.is_task_running = False
    
    async def broadcast_status(self, status: str, text: str):
        """Broadcast status update to all connected WebSocket clients."""
        message = {
            "type": "status",
            "action": {"status": status, "text": text}
        }
        
        # Send to all connected WebSocket clients
        disconnected = set()
        for ws in self.ws_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to WebSocket: {e}")
                disconnected.add(ws)
        
        # Remove disconnected clients
        self.ws_connections -= disconnected
    
    async def broadcast_transcription(self, text: str, partial: bool = False):
        """Broadcast transcription to all connected WebSocket clients."""
        message = {
            "type": "transcription",
            "action": {"text": text, "partial": partial}
        }
        
        disconnected = set()
        for ws in self.ws_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.debug(f"Failed to send to WebSocket: {e}")
                disconnected.add(ws)
        
        self.ws_connections -= disconnected
    
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
    """WebSocket endpoint for Chrome extension status updates."""
    await websocket.accept()
    logger.info("✅ WebSocket client connected")
    print("🔌 Chrome extension connected via WebSocket")
    
    # Add to connections
    if hub:
        hub.ws_connections.add(websocket)
        print(f"📊 Total WebSocket connections: {len(hub.ws_connections)}")
    
    try:
        # Send initial status
        initial_message = {
            "type": "status",
            "action": {"status": "idle", "text": "Ready"}
        }
        await websocket.send_json(initial_message)
        print(f"📤 Sent initial status to extension: {initial_message}")
        
        while True:
            # Keep connection alive, receive any messages from extension
            data = await websocket.receive_text()
            logger.debug(f"Received from extension: {data}")
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        print("🔌 Chrome extension disconnected")
    finally:
        if hub and websocket in hub.ws_connections:
            hub.ws_connections.remove(websocket)
            print(f"📊 Total WebSocket connections: {len(hub.ws_connections)}")


def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the FastAPI server."""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
