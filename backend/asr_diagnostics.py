import sounddevice as sd
import numpy as np
import speech_recognition as sr
import soundfile as sf
import tempfile
import os

def test_config(device_id, samplerate, channels):
    print(f"\n[TEST] Device: {device_id}, SR: {samplerate}, Channels: {channels}")
    try:
        duration = 3
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='int16', device=device_id)
        sd.wait()
        
        volume = np.max(np.abs(recording))
        print(f"  -> Max Volume: {volume}")
        
        if volume < 50:
            print("  -> Result: SILENT/TOO QUIET")
            return False, volume
        
        # Try transcription
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            tmp = f.name
        sf.write(tmp, recording, samplerate)
        
        r = sr.Recognizer()
        with sr.AudioFile(tmp) as source:
            audio = r.record(source)
        os.remove(tmp)
        
        try:
            text = r.recognize_google(audio)
            print(f"  -> Result: SUCCESS (Heard: '{text}')")
            return True, volume
        except sr.UnknownValueError:
            print("  -> Result: NO WORDS RECOGNIZED")
            return False, volume
        except sr.RequestError as e:
            print(f"  -> Result: GOOGLE SR ERROR ({e})")
            return False, volume
            
    except Exception as e:
        print(f"  -> Result: ERROR ({e})")
        return False, 0

def run_diagnostics():
    devices = sd.query_devices()
    input_devices = [i for i, d in enumerate(devices) if d['max_input_channels'] > 0]
    
    samplerates = [16000, 44100, 48000]
    channels_options = [1, 2]
    
    print("Starting ASR Diagnostics...")
    print("Please speak clearly during the 'Speak now' prompts.")
    
    results = []
    
    # Test default first
    print("\n--- Testing Default Device ---")
    res, vol = test_config(None, 16000, 1)
    results.append(("Default", 16000, 1, res, vol))
    
    # Test all input devices
    for dev_id in input_devices:
        dev_info = devices[dev_id]
        print(f"\n--- Testing Device {dev_id}: {dev_info['name']} ---")
        for sr_val in samplerates:
            for ch in channels_options:
                if ch <= dev_info['max_input_channels']:
                    res, vol = test_config(dev_id, sr_val, ch)
                    results.append((dev_id, sr_val, ch, res, vol))
    
    print("\n" + "="*30)
    print("DIAGNOSTIC SUMMARY")
    print("="*30)
    for r in results:
        status = "WORKING" if r[3] else "FAILED"
        print(f"Device {r[0]} | SR: {r[1]} | CH: {r[2]} | Vol: {r[4]} | Status: {status}")

if __name__ == "__main__":
    run_diagnostics()
