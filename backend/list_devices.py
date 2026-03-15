import sounddevice as sd
import numpy as np

print("Testing microphone...")
try:
    fs = 16000
    duration = 3  # seconds
    print("Speak now...")
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    print("Recording finished.")
    
    volume = np.max(np.abs(myrecording))
    print(f"Max volume level detected: {volume}")
    
    if volume < 100:
        print("WARNING: The recorded audio is very quiet. The microphone might be muted or using the wrong input device.")
    else:
        print("Microphone is working! Audio was captured.")

except Exception as e:
    print(f"Error recording audio: {e}")
