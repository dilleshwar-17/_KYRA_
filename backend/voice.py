"""
KYRA - Voice Module
Speech-to-Text (microphone input) and Text-to-Speech (edge-tts output).
Uses Microsoft's neural voices via edge-tts, with Windows Media Player for playback.
"""
import threading
import asyncio
import tempfile
import os
import subprocess

try:
    import pygame
    # Initialize pygame mixer
    pygame.mixer.init()
    _pygame_available = True
except (ImportError, Exception) as e:
    _pygame_available = False
    print(f"[WARNING] pygame/audio initialization failed: {e}")

# ─── TTS Setup (edge-tts) ───────────────────────────────────────────────────

_EDGE_TTS_VOICE = "en-US-AriaNeural"   # High-quality, natural-sounding female voice
_EDGE_TTS_RATE  = "+0%"               # Normal speed (use "+10%" to be faster)
_EDGE_TTS_PITCH = "+0Hz"              # Normal pitch

try:
    import edge_tts as _edge_tts
    _tts_available = True
    print(f"[OK] TTS (edge-tts / {_EDGE_TTS_VOICE}) ready")
except ImportError:
    _tts_available = False
    print("[WARNING] edge-tts not installed — TTS disabled. Run: pip install edge-tts")


async def _generate_audio(text: str, output_path: str):
    """Generate mp3 audio from text using edge-tts."""
    communicate = _edge_tts.Communicate(text, _EDGE_TTS_VOICE, rate=_EDGE_TTS_RATE, pitch=_EDGE_TTS_PITCH)
    await communicate.save(output_path)


def speak(text: str):
    """
    Convert text to speech (blocking) using edge-tts and pygame.
    """
    if os.getenv("KYRA_SKIP_BACKEND_TTS", "false").lower() == "true":
        print(f"[Backend TTS Skipped] {text}")
        return

    if not _tts_available or not _pygame_available:
        print(f"[TTS disabled] {text}")
        return
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        
        asyncio.run(_generate_audio(text, tmp_path))
        
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"[TTS Error] {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            # Wait a bit before deleting to ensure playback is fully complete
            pygame.time.wait(500)
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def speak_async(text: str):
    """Non-blocking TTS. Returns a thread (joinable)."""
    t = threading.Thread(target=speak, args=(text,), daemon=True)
    t.start()
    return t


# ─── STT Setup ────────────────────────────────────────────────────────────────

_recognizer = None
_sr = None

try:
    import speech_recognition as sr
    import sounddevice as sd
    import soundfile as sf
    import tempfile
    import os
    import numpy as np
    import torch
    from openai import OpenAI
    
    _sr = sr
    _recognizer = sr.Recognizer()
    print("[OK] STT (SpeechRecognition + sounddevice) ready")
    
    # Load VAD
    print("[INFO] Loading VAD model for active listening...")
    _vad_model, _vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                            model='silero_vad',
                                            force_reload=False)
    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = _vad_utils
    
    # Setup SambaNova Client
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env")
    _sambanova_api_key = os.getenv("SAMBANOVA_API_KEY")
    if _sambanova_api_key:
        _openai_client = OpenAI(api_key=_sambanova_api_key, base_url="https://api.sambanova.ai/v1")
    else:
        _openai_client = None

except ImportError as e:
    print(f"[WARNING] STT unavailable (missing dep): {e}")
    _recognizer = None
except Exception as e:
    print(f"[ERROR] STT init error: {e}")
    _recognizer = None


def _get_supported_info(device_id=None):
    """Detect working samplerate and channels for the given device. Silero VAD requires 16000 Hz."""
    try:
        sd.check_input_settings(device=device_id, samplerate=16000, channels=1)
        return 16000, 1
    except Exception:
        return 16000, 1  # Fallback


def listen(timeout: int = 4) -> "str | None":
    """
    Capture audio from microphone using VAD and return transcribed text.
    Waits until speech ends instead of a fixed timeout.
    Returns None if mic unavailable or nothing heard.
    """
    if _recognizer is None or _sr is None:
        print("[WARNING] STT disabled — no microphone available")
        return None

    # Cast to avoid NoneType errors in linters
    sr_mod = _sr
    rec = _recognizer

    # Assertions to help the type checker realize these are not None
    assert sr_mod is not None
    assert rec is not None

    try:
        # Prefer an explicitly configured device
        device_env = os.getenv("KYRA_MIC_DEVICE")
        device_id = None
        if device_env:
            try:
                device_id = int(device_env)
            except ValueError:
                device_id = device_env

        fs, channels = _get_supported_info(device_id)
        print(f"[INFO] Active Listening (SR: {fs}, Device: {device_id})...")

        # Lower threshold to 0.15 for laptop mics/quieter distances
        vad_iterator = VADIterator(_vad_model, threshold=0.15)
        chunk_size = 512
        buffer = []
        is_speaking = False
        speech_detected_ever = False

        # Read up to `timeout` seconds waiting for speech to start, otherwise stop.
        # Once speech starts, continue until it stops.
        max_silent_chunks = int((timeout * fs) / chunk_size)
        _silent_count: int = 0

        try:
            with sd.InputStream(samplerate=fs, channels=1, blocksize=chunk_size, device=device_id) as stream:
                while True:
                    audio_chunk, overflowed = stream.read(chunk_size)
                    audio_float32 = audio_chunk[:, 0].astype(np.float32)
                    audio_tensor = torch.from_numpy(audio_float32)
                    
                    speech_dict = vad_iterator(audio_tensor, return_seconds=True)
                    
                    if speech_dict and 'start' in speech_dict:
                        is_speaking = True
                        speech_detected_ever = True
                        buffer = [audio_float32]
                        
                    if is_speaking:
                        buffer.append(audio_float32)
                    else:
                        _silent_count = _silent_count + 1
                        if not speech_detected_ever and _silent_count > max_silent_chunks:
                            print("[INFO] Listen timeout. No speech detected.")
                            return None
                        
                    if speech_dict and 'end' in speech_dict:
                        break
        except Exception as e:
            print(f"[ERROR] Could not open microphone device {device_id}: {e}")
            print("[TIP] Run 'python backend/configure_mic.py' to select a working microphone.")
            return None

        if not buffer:
             return None

        audio_raw = np.concatenate(buffer)

        # ── Audio Pre-processing (Normalization) ──────────────────────────────
        max_val = np.max(np.abs(audio_raw))
        if max_val > 0.0001: # Prevent amplifying pure digital silence
            audio_raw = audio_raw / max_val * 0.9 # Normalize to 90% peak
        
        # Convert to int16 for WAV saving
        audio_int = (audio_raw * 32767).astype(np.int16)

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            tmp_name = f.name
        sf.write(tmp_name, audio_int, fs)

        text = None

        # 1. Try SambaNova Whisper STT
        if _openai_client:
            print("[INFO] STT: Trying SambaNova Whisper...")
            try:
                with open(tmp_name, "rb") as f:
                    transcript = _openai_client.audio.transcriptions.create(
                        model="Whisper-Large-v3", 
                        file=f
                    )
                text = transcript.text
                print(f"[INFO] SambaNova Heard: {text}")
            except Exception as e:
                print(f"[WARNING] SambaNova STT failed ({e}), falling back to Google...")

        # 2. Fallback to Google STT
        if not text:
            try:
                with sr_mod.AudioFile(tmp_name) as source:
                    audio = rec.record(source)
                text = rec.recognize_google(audio)
                print(f"[INFO] Google Heard: {text}")
            except sr_mod.UnknownValueError:
                print("[INFO] Could not understand audio")
            except sr_mod.RequestError as e:
                print(f"[ERROR] Google STT service error: {e}")
            except Exception as e:
                print(f"[ERROR] STT error: {e}")

        os.remove(tmp_name)
        return text

    except Exception as e:
        print(f"[ERROR] Listen stream error: {e}")
        return None

def get_sentiment(text: str) -> float:
    """
    Returns a sentiment score between -1.0 (very sad/angry) and 1.0 (very happy).
    Uses a simple keyword mapping.
    """
    if not text:
        return 0.0
    
    text = text.lower()
    positive = ["happy", "great", "awesome", "good", "nice", "love", "thanks", "thank", "excited", "wow", "amazing", "fun"]
    negative = ["sad", "bad", "angry", "hate", "sorry", "terrible", "worst", "unhappy", "upset", "cry", "fear", "scared", "no"]
    
    pos_score = sum(1 for w in positive if w in text)
    neg_score = sum(1 for w in negative if w in text)
    
    total = pos_score + neg_score
    if total == 0:
        return 0.0
    
    return (pos_score - neg_score) / total
