"""Local STT service using Vosk for quick voice commands."""

import asyncio
import json
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from typing import Optional, Callable
import logging
import os

logger = logging.getLogger(__name__)


class LocalSTT:
    """Local speech-to-text using Vosk for low-latency commands."""
    
    def __init__(
        self,
        model_path: str = "vosk-model-small-en-us-0.15",
        sample_rate: int = 16000,
    ):
        """
        Initialize local STT.
        
        Args:
            model_path: Path to Vosk model directory
            sample_rate: Audio sample rate
        """
        self.sample_rate = sample_rate
        self.is_listening = False
        self.callback_fn: Optional[Callable] = None
        self.partial_callback_fn: Optional[Callable] = None
        self.event_loop = None
        
        # Find model path
        if not os.path.isabs(model_path):
            # Try relative to current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            model_path = os.path.join(parent_dir, model_path)
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Vosk model not found at: {model_path}")
        
        logger.info(f"Loading Vosk model from: {model_path}")
        self.model = Model(model_path)
        logger.info("Local STT initialized with Vosk")
    
    def start_listening(self, callback: Callable[[str], None], partial_callback: Optional[Callable[[str], None]] = None):
        """
        Start listening for voice commands.
        
        Args:
            callback: Function to call with final transcribed text
            partial_callback: Optional function to call with partial transcriptions
        """
        self.callback_fn = callback
        self.partial_callback_fn = partial_callback
        self.is_listening = True
        
        # Create recognizer for this session
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        self.recognizer.SetWords(True)
        
        logger.info("Starting local STT listening")
        
        # Start audio stream
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.int16,  # Vosk expects int16
            callback=self._audio_callback,
            blocksize=4000,  # ~250ms chunks at 16kHz
        )
        self.stream.start()
        print("🎤 Listening... (speak naturally)")
    
    def stop_listening(self):
        """Stop listening for voice commands."""
        self.is_listening = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        logger.info("Stopped local STT listening")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Process audio chunks from microphone."""
        if not self.is_listening:
            return
        
        if status:
            logger.warning(f"Audio status: {status}")
        
        # Convert to bytes (Vosk expects bytes)
        audio_data = bytes(indata)
        
        # Process with Vosk
        if self.recognizer.AcceptWaveform(audio_data):
            # Final result - complete utterance
            result = json.loads(self.recognizer.Result())
            text = result.get('text', '').strip()
            
            if text:
                print(f"\n🎤 YOU SAID: {text}")
                logger.info(f"Transcribed: {text}")
                
                # Call callback in thread-safe way
                if self.event_loop and self.event_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self._async_callback(text), 
                        self.event_loop
                    )
                else:
                    logger.warning("No event loop available for callback")
        else:
            # Partial result - still speaking
            partial = json.loads(self.recognizer.PartialResult())
            partial_text = partial.get('partial', '')
            
            if partial_text:
                # Show what's being recognized in real-time
                print(f"\r🎙️  {partial_text}", end='', flush=True)
                
                # Send partial to callback if available
                if self.partial_callback_fn and self.event_loop and self.event_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self._async_partial_callback(partial_text),
                        self.event_loop
                    )
    
    async def _async_callback(self, text: str):
        """Async wrapper for callback."""
        if self.callback_fn:
            if asyncio.iscoroutinefunction(self.callback_fn):
                await self.callback_fn(text)
            else:
                self.callback_fn(text)
    
    async def _async_partial_callback(self, text: str):
        """Async wrapper for partial callback."""
        if self.partial_callback_fn:
            if asyncio.iscoroutinefunction(self.partial_callback_fn):
                await self.partial_callback_fn(text)
            else:
                self.partial_callback_fn(text)
