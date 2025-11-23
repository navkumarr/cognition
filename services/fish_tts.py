"""Fish Audio TTS service for voice feedback."""

import asyncio
import httpx
import sounddevice as sd
import numpy as np
from typing import Optional
import logging
import io
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class FishTTS:
    """Fish Audio TTS service for voice feedback."""
    
    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.fish.audio",
        voice_id: Optional[str] = None,
        sample_rate: int = 24000,
    ):
        """
        Initialize Fish Audio TTS service.
        
        Args:
            api_key: Fish Audio API key
            api_base: API base URL
            voice_id: Voice ID to use (optional)
            sample_rate: Output sample rate
        """
        self.api_key = api_key
        self.api_base = api_base
        self.voice_id = voice_id
        self.sample_rate = sample_rate
        self.is_speaking = False
        
        logger.info("Fish Audio TTS initialized")
    
    async def speak(self, text: str, blocking: bool = True):
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to speak
            blocking: Whether to wait for speech to complete
        """
        if self.is_speaking and blocking:
            logger.info("Already speaking, waiting...")
            while self.is_speaking:
                await asyncio.sleep(0.1)
        
        self.is_speaking = True
        logger.info(f"Speaking: {text}")
        
        try:
            # Call Fish Audio TTS API
            async with httpx.AsyncClient(timeout=30.0) as client:
                data = {
                    "text": text,
                    "format": "mp3",
                }
                
                if self.voice_id:
                    data["reference_id"] = self.voice_id
                
                response = await client.post(
                    f"{self.api_base}/v1/tts",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=data,
                )
                
                if response.status_code == 200:
                    # Get audio data
                    audio_data = response.content
                    
                    # Convert MP3 to numpy array for playback
                    audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
                    
                    # Convert to numpy array
                    samples = np.array(audio_segment.get_array_of_samples())
                    
                    # Convert to float32
                    if audio_segment.sample_width == 2:
                        samples = samples.astype(np.float32) / 32768.0
                    
                    # Reshape if stereo
                    if audio_segment.channels == 2:
                        samples = samples.reshape((-1, 2))
                    
                    # Play audio
                    sd.play(samples, audio_segment.frame_rate)
                    
                    if blocking:
                        sd.wait()
                    
                    logger.info("Speech completed")
                else:
                    logger.error(f"TTS API error: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            self.is_speaking = False
    
    def stop(self):
        """Stop current speech."""
        sd.stop()
        self.is_speaking = False
        logger.info("Speech stopped")
