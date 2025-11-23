#!/usr/bin/env python3
"""
Test script for local STT functionality.
This will help debug microphone and speech recognition issues.
"""

import sys
import time
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

print("=" * 60)
print("Local STT Test Script")
print("=" * 60)
print()

# Test 1: List audio devices
print("TEST 1: Audio Devices")
print("-" * 60)
try:
    devices = sd.query_devices()
    input_devices = [d for d in devices if d['max_input_channels'] > 0]
    print(f"Found {len(input_devices)} input devices:")
    for i, device in enumerate(input_devices):
        print(f"  [{i}] {device['name']}")
        print(f"      Channels: {device['max_input_channels']}")
        print(f"      Sample Rate: {device['default_samplerate']}")
    
    default_input = sd.query_devices(kind='input')
    print(f"\nDefault input device: {default_input['name']}")
    print("✅ Audio devices detected")
except Exception as e:
    print(f"❌ Error detecting audio devices: {e}")
    sys.exit(1)

print()

# Test 2: Record audio and check levels
print("TEST 2: Microphone Level Check (5 seconds)")
print("-" * 60)
print("Speak now! Testing microphone levels...")

sample_rate = 16000
duration = 5
audio_levels = []

def audio_callback(indata, frames, time_info, status):
    """Capture audio and calculate RMS."""
    if status:
        print(f"Status: {status}")
    
    audio_chunk = indata[:, 0]
    rms = np.sqrt(np.mean(audio_chunk ** 2))
    audio_levels.append(rms)
    
    # Visual level indicator
    bars = int(rms * 1000)
    print(f"\rLevel: {'█' * min(bars, 50)} {rms:.4f}", end='', flush=True)

try:
    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32,
        callback=audio_callback,
    ):
        time.sleep(duration)
    
    print()
    max_level = max(audio_levels) if audio_levels else 0
    avg_level = sum(audio_levels) / len(audio_levels) if audio_levels else 0
    
    print(f"\nMax level: {max_level:.4f}")
    print(f"Avg level: {avg_level:.4f}")
    
    if max_level > 0.02:
        print("✅ Microphone is working! Audio detected.")
    else:
        print("⚠️  Low audio levels. Speak louder or check microphone.")
except Exception as e:
    print(f"\n❌ Error recording audio: {e}")
    sys.exit(1)

print()

# Test 3: Voice Activity Detection
print("TEST 3: Voice Activity Detection (10 seconds)")
print("-" * 60)
print("Speak a few short sentences. System will detect when you speak.")

vad_threshold = 0.02
silence_duration = 1.0
sample_rate = 16000

audio_buffer = []
silence_counter = 0
speech_detected = False

def vad_callback(indata, frames, time_info, status):
    """Voice activity detection callback."""
    global audio_buffer, silence_counter, speech_detected
    
    audio_chunk = indata[:, 0]
    rms = np.sqrt(np.mean(audio_chunk ** 2))
    
    if rms > vad_threshold:
        if not speech_detected:
            print(f"\n🎤 Speech detected! (level: {rms:.4f})")
            speech_detected = True
        audio_buffer.append(audio_chunk)
        silence_counter = 0
    else:
        silence_counter += 1
        silence_secs = silence_counter * 0.1
        
        if audio_buffer and silence_secs >= silence_duration:
            print(f"🔇 Silence detected ({len(audio_buffer)} chunks buffered)")
            audio_buffer = []
            speech_detected = False
            silence_counter = 0

try:
    print("Listening...")
    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32,
        callback=vad_callback,
        blocksize=int(sample_rate * 0.1),
    ):
        time.sleep(10)
    
    print("\n✅ Voice activity detection working")
except Exception as e:
    print(f"\n❌ VAD error: {e}")
    sys.exit(1)

print()

# Test 4: Load Whisper model
print("TEST 4: Load Whisper Model")
print("-" * 60)
try:
    print("Loading base.en model (this may take a moment)...")
    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    print("✅ Whisper model loaded successfully")
except Exception as e:
    print(f"❌ Error loading Whisper model: {e}")
    sys.exit(1)

print()

# Test 5: Full transcription test
print("TEST 5: Full Speech-to-Text Test (10 seconds)")
print("-" * 60)
print("Speak clearly. After 1 second of silence, your speech will be transcribed.")
print("Say something like: 'scroll down' or 'go to google dot com'")
print()

class SimpleSTT:
    def __init__(self):
        self.model = model
        self.sample_rate = 16000
        self.vad_threshold = 0.02
        self.silence_duration = 1.0
        self.audio_buffer = []
        self.silence_counter = 0
        self.transcription_count = 0
    
    def audio_callback(self, indata, frames, time_info, status):
        audio_chunk = indata[:, 0]
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        
        # Visual feedback
        if rms > self.vad_threshold:
            print("🎤 ", end='', flush=True)
        
        if rms > self.vad_threshold:
            self.audio_buffer.append(audio_chunk)
            self.silence_counter = 0
        else:
            self.silence_counter += 1
            
            silence_duration = self.silence_counter * 0.1
            if self.audio_buffer and silence_duration >= self.silence_duration:
                self.transcribe_buffer()
    
    def transcribe_buffer(self):
        if not self.audio_buffer:
            return
        
        try:
            audio_data = np.concatenate(self.audio_buffer)
            
            if len(audio_data) < self.sample_rate * 0.5:
                self.audio_buffer = []
                self.silence_counter = 0
                return
            
            print("\n\n🔄 Transcribing...")
            
            print(f"Audio length: {len(audio_data) / self.sample_rate:.2f}s")
            
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=1,
                language="en",
                vad_filter=True,
            )
            
            segments_list = list(segments)
            print(f"Found {len(segments_list)} segments")
            
            text = " ".join([segment.text.strip() for segment in segments_list])
            
            if text:
                self.transcription_count += 1
                print(f"\n{'=' * 60}")
                print(f"✅ TRANSCRIPTION #{self.transcription_count}: {text}")
                print(f"{'=' * 60}\n")
            
        except Exception as e:
            print(f"\n❌ Transcription error: {e}\n")
        finally:
            self.audio_buffer = []
            self.silence_counter = 0

try:
    stt = SimpleSTT()
    
    print("Listening for 10 seconds...")
    print("(🎤 = speech detected, transcription happens after silence)\n")
    
    stream = sd.InputStream(
        samplerate=stt.sample_rate,
        channels=1,
        dtype=np.float32,
        callback=stt.audio_callback,
        blocksize=int(stt.sample_rate * 0.1),
    )
    
    stream.start()
    time.sleep(10)
    stream.stop()
    stream.close()
    
    print("\n\n✅ Full STT test completed")
    
    if stt.transcription_count > 0:
        print(f"✅ Successfully transcribed {stt.transcription_count} speech segment(s)")
    else:
        print("⚠️  No speech was transcribed. Possible issues:")
        print("   - Speak louder")
        print("   - Check microphone permissions")
        print("   - Lower vad_threshold in services/local_stt.py")
    
except Exception as e:
    print(f"\n❌ Full test error: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("Test Complete!")
print("=" * 60)
print()

if stt.transcription_count > 0:
    print("✅ All tests passed! Your microphone and STT are working.")
    print()
    print("If the main app isn't working, the issue is likely in:")
    print("  1. Event loop integration (asyncio)")
    print("  2. Callback function execution")
    print("  3. Command parser or hub logic")
else:
    print("⚠️  STT not working properly. Try:")
    print("  1. Grant microphone permissions in System Preferences")
    print("  2. Speak louder and more clearly")
    print("  3. Adjust vad_threshold (currently 0.02)")

sys.exit(0)
