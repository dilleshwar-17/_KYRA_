"""
KYRA - Passive Wake Word Listener
Runs in a background thread. Continuously records short audio chunks
and checks if "Hey Kyra" was spoken using Google STT.
When detected, triggers a full command listen and notifies all WS clients.
"""
import threading
import tempfile
import os
import time
import asyncio
import sys
# Help IDE find adjacent modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_active = False
_loop_ref = None          # asyncio event loop from main.py
_clients: set = set()     # WebSocket clients to broadcast to
_callback = None          # Optional callback for wake words

try:
    import sounddevice as sd
    import soundfile as sf
    import speech_recognition as sr
    import numpy as np
    import torch
    
    _sr_available = True
    _recognizer = sr.Recognizer()
    print("[OK] Wake word listener (sounddevice) ready")
    
    # Load VAD
    print("[INFO] Loading VAD model for wake word...")
    _vad_model, _vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                            model='silero_vad',
                                            force_reload=False)
    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = _vad_utils
except ImportError as e:
    _sr_available = False
    print(f"[WARNING] Wake word listener unavailable: {e}")

def _get_supported_info(device_id=None):
    """Detect working samplerate and channels. Silero VAD REQUIRES 16000 Hz."""
    try:
        sd.check_input_settings(device=device_id, samplerate=16000, channels=1)
        return 16000, 1
    except Exception:
        # Resampling will be required if hardware strictly rejects 16k, but Windows usually accepts it.
        return 16000, 1

def _check_mic_level(audio_data):
    """Check if the audio has enough signal to be worth transcribing."""
    level = np.max(np.abs(audio_data))
    return level > 200 # Threshold to ignore silence

# ── Wake-word config ───────────────────────────────────────────────────────────
WAKE_PHRASES = [
    "hey kyra", "hi kyra", "hey kira", "hi kira",
    "hey kera", "hey cara", "ok kyra", "okay kyra",
    "hey keira", "hi keira", "hey kaira", "hi kaira",
    "hello kyra", "hello kira", "hello keira",
    "hey tyra", "hey cairo", "hey hera", "hey sierra"
]
CHUNK_SEC   = 4    # how long each passive listen chunk is
FS          = 16000


def _transcribe_chunk(audio_data, fs) -> str | None:
    """Save numpy audio to temp WAV and run Google STT. Returns lowercase text or None."""
    try:
        # Pre-process: Normalization
        max_val = np.max(np.abs(audio_data))
        if max_val > 0.0001:  # Prevent amplifying pure static/silence, but allow very quiet mics
            audio_data = audio_data / max_val * 0.9
        
        audio_int = (audio_data * 32767).astype(np.int16)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        sf.write(tmp, audio_int, fs)
        with sr.AudioFile(tmp) as source:
            audio = _recognizer.record(source)
        os.remove(tmp)
        text = _recognizer.recognize_google(audio)
        return text.lower().strip()
    except sr.UnknownValueError:
        return None
    except Exception:
        return None


def _extract_command(transcript: str) -> str:
    """Strip the wake phrase from transcript to get just the command."""
    for phrase in WAKE_PHRASES:
        if phrase in transcript:
            cmd = transcript.replace(phrase, "").strip(" ,.")
            return cmd if cmd else ""
    return ""


def _broadcast(payload: dict):
    """Thread-safe push to all connected WebSocket clients."""
    if _loop_ref is None:
        return
    import json
    msg = json.dumps(payload)

    async def _send_all():
        dead = set()
        for ws in list(_clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        for ws in dead:
            _clients.discard(ws)

    asyncio.run_coroutine_threadsafe(_send_all(), _loop_ref)


def _listen_loop():
    """Background thread — streams audio, detects speech with VAD, captures and transcribes on speech end."""
    global _active
    print("[INFO] Passive wake-word listener started — say 'Hey Kyra'!")
    device_env = os.getenv("KYRA_MIC_DEVICE")
    device_id = None
    if device_env:
        try:
            device_id = int(device_env)
        except ValueError:
            device_id = device_env

    fs, channels = _get_supported_info(device_id)
    print(f"[INFO] Wake-word SR: {fs}, Device: {device_id}")
    
    # Lower threshold to 0.15 for laptop mics/quieter distances
    vad_iterator = VADIterator(_vad_model, threshold=0.15)
    chunk_size = 512
    
    buffer = []
    is_speaking = False

    try:
        with sd.InputStream(samplerate=fs, channels=1, blocksize=chunk_size, device=device_id) as stream:
            while _active:
                audio_chunk, overflowed = stream.read(chunk_size)
                if overflowed:
                    pass
                
                audio_float32 = audio_chunk[:, 0].astype(np.float32)
                audio_tensor = torch.from_numpy(audio_float32)
                
                speech_dict = vad_iterator(audio_tensor, return_seconds=True)
                
                if speech_dict and 'start' in speech_dict:
                    is_speaking = True
                    buffer = [audio_float32] # Reset buffer at speech start
                    
                if is_speaking:
                    buffer.append(audio_float32)
                    
                if speech_dict and 'end' in speech_dict:
                    is_speaking = False
                    
                    if len(buffer) > 0:
                        # Reconstruct full audio
                        full_audio = np.concatenate(buffer)
                        transcript = _transcribe_chunk(full_audio, fs)
                        buffer = [] # clear buffer
                        
                        if not transcript:
                            continue
                            
                        print(f"[passive] heard: {transcript}")

                        # ── Wake word detected? ──────────────────────────────────────────
                        if any(p in transcript for p in WAKE_PHRASES):
                            command = _extract_command(transcript)

                            if command:
                                print(f"[INFO] Wake command: {command}")
                                # Notify frontend: wake word heard and we are processing
                                _broadcast({"event": "state", "state": "listening"})
                                if _callback:
                                    # The callback is responsible for being thread-safe
                                    # and scheduling work on the main loop.
                                    _callback(command)
                            # If only wake word is heard without a command, we just ignore it and continue listening.
                            # This creates a more seamless "Hey Google, what's the weather" experience.
    except Exception as e:
        print(f"[wake_loop] error: {e}")
        print("[TIP] If the microphone failed to open, run 'python backend/configure_mic.py'")
        time.sleep(1)


# ── Public API ─────────────────────────────────────────────────────────────────

def start(loop, clients: set, callback=None):
    """Start the passive listener. Pass asyncio loop, clients set, and an optional callback."""
    global _active, _loop_ref, _clients, _callback
    if not _sr_available:
        print("[WARNING] Passive listener disabled (missing deps).")
        return
    _active = True
    _loop_ref = loop
    _clients = clients
    _callback = callback
    t = threading.Thread(target=_listen_loop, daemon=True, name="wakeword")
    t.start()


def stop():
    global _active
    _active = False
