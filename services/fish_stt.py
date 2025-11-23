"""Fish Audio STT service for high-quality transcription."""

import asyncio
import numpy as np
import sounddevice as sd
import httpx
from typing import Optional, Callable
import logging
import io
import wave

logger = logging.getLogger(__name__)


class FishSTT:
    """Fish Audio STT service activated by 'Hey Fish' wake phrase."""
    
    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.fish.audio",
        sample_rate: int = 16000,
    ):
        """
        Initialize Fish Audio STT service.
        
        Args:
            api_key: Fish Audio API key
            api_base: API base URL
            sample_rate: Audio sample rate
        """
        self.api_key = api_key
        self.api_base = api_base
        self.sample_rate = sample_rate
        self.is_active = False
        self.is_recording = False
        self.audio_buffer = []
        self.callback_fn: Optional[Callable] = None
        
        logger.info("Fish Audio STT initialized")
    
    def activate(self, callback: Callable[[str], None]):
        """
        Activate Fish STT (called when 'Hey Fish' detected).
        
        Args:
            callback: Function to call with transcribed text
        """
        self.callback_fn = callback
        self.is_active = True
        self.is_recording = True
        self.audio_buffer = []
        
        logger.info("Fish STT activated - recording started")
        
        # Start audio stream
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32,
            callback=self._audio_callback,
        )
        self.stream.start()
    
    def deactivate(self):
        """Deactivate Fish STT (called when 'Done Fish' detected)."""
        self.is_active = False
        self.is_recording = False
        
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        
        logger.info("Fish STT deactivated - processing recording")
        
        # Transcribe accumulated audio
        asyncio.create_task(self._transcribe_and_callback())
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Record audio chunks."""
        if not self.is_recording:
            return
        
        self.audio_buffer.append(indata[:, 0].copy())
    
    async def _transcribe_and_callback(self):
        """Transcribe accumulated audio via Fish Audio API."""
        if not self.audio_buffer:
            logger.warning("No audio to transcribe")
            return
        
        try:
            # Concatenate audio
            audio_data = np.concatenate(self.audio_buffer)
            
            # Convert to WAV format in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                
                # Convert float32 to int16
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())
            
            wav_buffer.seek(0)
            
            # Call Fish Audio API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base}/v1/asr",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    files={
                        "audio": ("audio.wav", wav_buffer, "audio/wav"),
                    },
                    data={
                        "language": "en",
                    },
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("text", "")
                    
                    if text and self.callback_fn:
                        logger.info(f"Fish transcribed: {text}")
                        print(f"\n🐟 FISH TRANSCRIBED: {text}")
                        if asyncio.iscoroutinefunction(self.callback_fn):
                            await self.callback_fn(text)
                        else:
                            self.callback_fn(text)
                else:
                    logger.error(f"Fish API error: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Fish transcription error: {e}")
        finally:
            self.audio_buffer = []
