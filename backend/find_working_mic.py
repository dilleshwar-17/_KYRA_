import sounddevice as sd
import numpy as np

print("Testing all input devices for audio signal...")
working_devices = []

try:
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            try:
                # Record 1 second on this device
                rec = sd.rec(16000, samplerate=16000, channels=1, device=i, dtype='float32')
                sd.wait()
                vol = np.max(np.abs(rec))
                
                # If volume is above 0.001 it's likely not completely dead/muted
                print(f"Device [{i}] {dev['name'][:30]}: max_volume={vol:.5f}")
                if vol > 0.001:
                    working_devices.append((i, vol, dev['name']))
            except Exception as e:
                print(f"Device [{i}] skip (error: {e})")
                
    if working_devices:
        working_devices.sort(key=lambda x: x[1], reverse=True)
        print("\n--- RECOMMENDED DEVICES ---")
        for i, vol, name in working_devices:
            print(f"[{i}] {name} (vol: {vol:.5f}) <<< USE THIS")
    else:
        print("\n[FAILED] NO MICROPHONE DETECTED ANY SOUND. Check Windows Privacy Settings for Microphone!")
except Exception as e:
    print(f"Global error: {e}")
