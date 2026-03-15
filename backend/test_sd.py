import sounddevice as sd
import speech_recognition as sr
import soundfile as sf
import tempfile
import os
import io

print('Listening 4 secs...')
fs = 16000
audio_data = sd.rec(int(4 * fs), samplerate=fs, channels=1, dtype='int16')
sd.wait()

with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
    n = f.name
sf.write(n, audio_data, fs)

r = sr.Recognizer()
try:
    with sr.AudioFile(n) as source:
        audio = r.record(source)
    print("Heard:", r.recognize_google(audio))
except Exception as e:
    print("Failed SR", e)
os.remove(n)
