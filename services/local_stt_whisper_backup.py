"""Local STT service using faster-whisper for quick voice commands."""

import asyncio
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class LocalSTT:
    """Local speech-to-text using faster-whisper for low-latency commands."""
    
    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        sample_rate: int = 16000,
        vad_threshold: float = 0.02,
        silence_duration: float = 1.0,
    ):
        """
        Initialize local STT service.
        
        Args:
            model_size: Whisper model size (tiny.en, base.en, small.en)
            device: cpu or cuda
            compute_type: int8, float16, or float32
            sample_rate: Audio sample rate
            vad_threshold: Voice activity detection threshold
            silence_duration: Seconds of silence to trigger transcription
        """
        self.sample_rate = sample_rate
        self.vad_threshold = vad_threshold
        self.silence_duration = silence_duration
        self.is_listening = False
        self.audio_buffer = []
        self.silence_counter = 0
        self.callback_fn: Optional[Callable] = None
        self.event_loop = None
        
        logger.info(f"Loading Whisper model: {model_size}")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info("Local STT initialized")
    
    def start_listening(self, callback: Callable[[str], None]):
        """
        Start listening for voice commands.
        
        Args:
            callback: Function to call with transcribed text
        """
        self.callback_fn = callback
        self.is_listening = True
        self.audio_buffer = []
        self.silence_counter = 0
        
        logger.info("Starting local STT listening")
        
        # Start audio stream
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32,
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * 0.1),  # 100ms chunks
        )
        self.stream.start()
    
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
        
        # Convert to mono and calculate RMS for VAD
        audio_chunk = indata[:, 0]
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        
        # Voice activity detection
        if rms > self.vad_threshold:
            self.audio_buffer.append(audio_chunk)
            self.silence_counter = 0
        else:
            self.silence_counter += 1
            
            # If we have audio and enough silence, transcribe
            silence_duration = self.silence_counter * 0.1  # 100ms chunks
            if self.audio_buffer and silence_duration >= self.silence_duration:
                self._transcribe_buffer()
    
    def _transcribe_buffer(self):
        """Transcribe accumulated audio buffer."""
        if not self.audio_buffer:
            return
        
        try:
            # Concatenate audio chunks
            audio_data = np.concatenate(self.audio_buffer)
            
            # Skip very short audio
            if len(audio_data) < self.sample_rate * 0.3:  # < 0.3 seconds
                print(f"⚠️  Audio too short: {len(audio_data) / self.sample_rate:.2f}s")
                self.audio_buffer = []
                self.silence_counter = 0
                return
            
            print(f"🔄 Transcribing {len(audio_data) / self.sample_rate:.2f}s of audio...")
            
            # Transcribe without VAD filter for better results
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=1,
                language="en",
                vad_filter=False,  # Disable VAD, we already did it
            )
            
            # Extract text
            text = " ".join([segment.text.strip() for segment in segments])
            
            if text and self.callback_fn:
                logger.info(f"Transcribed: {text}")
                print(f"\n🎤 YOU SAID: {text}")
                # Call callback in thread-safe way
                if self.event_loop and self.event_loop.is_running():
                    asyncio.run_coroutine_threadsafe(self._async_callback(text), self.event_loop)
                else:
                    logger.warning("No event loop available for callback")
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
        finally:
            # Clear buffer
            self.audio_buffer = []
            self.silence_counter = 0
    
    async def _async_callback(self, text: str):
        """Async wrapper for callback."""
        if self.callback_fn:
            if asyncio.iscoroutinefunction(self.callback_fn):
                await self.callback_fn(text)
            else:
                self.callback_fn(text)
