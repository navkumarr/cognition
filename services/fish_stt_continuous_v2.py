"""Fish Audio STT service for continuous voice recognition - V2 Rewrite"""

import asyncio
import numpy as np
import sounddevice as sd
import httpx
from typing import Optional, Callable
import logging
import io
import wave
import threading

logger = logging.getLogger(__name__)


class FishSTTContinuousV2:
    """Continuous Fish Audio STT service - simplified and reliable."""
    
    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.fish.audio/v1/asr",
        sample_rate: int = 16000,
        silence_threshold: float = 0.02,  # RMS threshold for voice detection
        silence_duration: float = 1.0,    # Seconds of silence before transcribing
        min_audio_duration: float = 0.5,  # Minimum audio length to transcribe
        status_callback: Optional[Callable] = None,  # Callback for status updates
    ):
        """
        Initialize Fish Audio continuous STT service.
        
        Args:
            api_key: Fish Audio API key
            api_base: API base URL for ASR
            sample_rate: Audio sample rate (16kHz)
            silence_threshold: RMS level to detect voice vs silence
            silence_duration: How long to wait in silence before transcribing
            min_audio_duration: Minimum audio duration to send to API
            status_callback: Optional callback for status updates (status, text)
        """
        self.api_key = api_key
        self.api_base = api_base
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.min_audio_duration = min_audio_duration
        self.status_callback = status_callback
        
        self.is_listening = False
        self.callback_fn: Optional[Callable] = None
        
        # Audio buffering - simple approach
        self.audio_buffer = []
        self.silence_chunks = 0
        self.is_recording = False
        
        # Threading for async transcription
        self.transcription_thread = None
        
        logger.info(f"Fish Audio continuous STT V2 initialized (threshold: {silence_threshold})")
    
    def start_listening(self, callback: Callable[[str], None]):
        """
        Start listening for voice commands.
        
        Args:
            callback: Function to call with transcribed text
        """
        self.callback_fn = callback
        self.is_listening = True
        self.audio_buffer = []
        self.silence_chunks = 0
        self.is_recording = False
        
        logger.info("Starting Fish Audio continuous listening")
        
        # Start audio stream
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32,
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * 0.1),  # 100ms chunks
        )
        self.stream.start()
        print(f"🎤 Listening... (threshold: {self.silence_threshold:.4f})")
    
    def stop_listening(self):
        """Stop listening for voice commands."""
        self.is_listening = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        logger.info("Stopped Fish Audio listening")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Process audio chunks from microphone."""
        if not self.is_listening:
            return
        
        if status:
            logger.warning(f"Audio status: {status}")
        
        # Get mono audio and calculate RMS
        audio_chunk = indata[:, 0].copy()
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        
        # Simple voice activity detection
        if rms > self.silence_threshold:
            # Voice detected
            if not self.is_recording:
                self.is_recording = True
                self.audio_buffer = []
                print("\r🎙️  Recording...", end='', flush=True)
                # Notify status callback that we're listening
                if self.status_callback:
                    self.status_callback("listening", "Listening...")
            
            self.audio_buffer.append(audio_chunk)
            self.silence_chunks = 0
            
        else:
            # Silence detected
            if self.is_recording:
                self.silence_chunks += 1
                silence_duration = self.silence_chunks * 0.1  # 100ms per chunk
                
                if silence_duration >= self.silence_duration:
                    # Enough silence - transcribe the buffer
                    self._process_buffer()
                    self.is_recording = False
                    self.silence_chunks = 0
    
    def _process_buffer(self):
        """Process the audio buffer and send to Fish Audio API."""
        if not self.audio_buffer:
            return
        
        try:
            # Concatenate audio chunks
            audio_data = np.concatenate(self.audio_buffer)
            duration = len(audio_data) / self.sample_rate
            
            # Check minimum duration
            if duration < self.min_audio_duration:
                logger.info(f"Audio too short ({duration:.2f}s), skipping")
                print(f"\r⏩ Audio too short ({duration:.2f}s)", end='', flush=True)
                self.audio_buffer = []
                return
            
            # Calculate RMS to verify it's not just noise
            overall_rms = np.sqrt(np.mean(audio_data ** 2))
            
            if overall_rms < self.silence_threshold * 0.5:
                logger.info(f"Audio too quiet (RMS: {overall_rms:.4f}), skipping")
                print(f"\r🔇 Too quiet (RMS: {overall_rms:.4f})", end='', flush=True)
                self.audio_buffer = []
                return
            
            print(f"\n🔄 Transcribing {duration:.1f}s (RMS: {overall_rms:.4f})...")
            
            # Notify that we're processing
            if self.status_callback:
                self.status_callback("processing", "Transcribing...")
            
            # Convert to WAV
            wav_data = self._audio_to_wav(audio_data)
            
            # Clear buffer before transcription
            self.audio_buffer = []
            
            # Transcribe in a separate thread
            self.transcription_thread = threading.Thread(
                target=self._transcribe_sync,
                args=(wav_data,),
                daemon=True
            )
            self.transcription_thread.start()
            
        except Exception as e:
            logger.error(f"Buffer processing error: {e}", exc_info=True)
            self.audio_buffer = []
    
    def _audio_to_wav(self, audio_data: np.ndarray) -> bytes:
        """Convert float32 audio to WAV bytes."""
        # Convert float32 to int16
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # Create WAV in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_int16.tobytes())
        
        return wav_buffer.getvalue()
    
    def _transcribe_sync(self, wav_data: bytes):
        """Synchronously transcribe audio using Fish Audio API."""
        try:
            # Use httpx synchronous client
            with httpx.Client(timeout=30.0) as client:
                files = {'audio': ('audio.wav', wav_data, 'audio/wav')}
                headers = {'Authorization': f'Bearer {self.api_key}'}
                data = {'language': 'en'}
                
                response = client.post(
                    self.api_base,
                    files=files,
                    headers=headers,
                    data=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result.get('text', '').strip()
                    
                    if text:
                        print(f"\n✅ TRANSCRIBED: '{text}'")
                        logger.info(f"Transcribed: {text}")
                        
                        # Don't reset to idle - let command processing handle status
                        # The control_hub will set status based on command execution result
                        
                        # Call callback
                        if self.callback_fn:
                            self.callback_fn(text)
                    else:
                        print("\n⚠️  Empty transcription")
                        logger.warning("Empty transcription received")
                        # Reset to idle only for empty transcriptions
                        if self.status_callback:
                            self.status_callback("idle", "Ready")
                        
                else:
                    logger.error(f"Fish Audio API error: {response.status_code} - {response.text}")
                    print(f"\n❌ API Error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            print(f"\n❌ Transcription failed: {e}")
