import os
import io
import wave
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path="backend/.env")

api_key = os.getenv("SAMBANOVA_API_KEY")
base_url = "https://api.sambanova.ai/v1"

client = OpenAI(api_key=api_key, base_url=base_url)

def test_stt():
    print("Recording 3 seconds...")
    fs = 16000
    duration = 3
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    print("Recording finished.")

    # Save to file using soundfile (often cleaner headers)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    
    sf.write(tmp_path, recording, fs)
    
    print(f"Sending to SambaNova STT (file: {tmp_path})...")
    try:
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="Whisper-Large-v3", 
                file=f
            )
        print(f"Transcription: {transcript.text}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    test_stt()
