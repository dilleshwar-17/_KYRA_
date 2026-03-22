import sounddevice as sd
import numpy as np
import time

def test_mics():
    print("--- 🎤 Mic Tester: Identifying your working microphone ---")
    devices = sd.query_devices()
    input_devices = [i for i, d in enumerate(devices) if d.get('max_input_channels', 0) > 0]
    
    results = []
    
    print(f"Found {len(input_devices)} input devices. Testing each for 1.5 seconds...")
    print("Please make some noise or speak clearly during the test!")
    
    for idx in input_devices:
        name = devices[idx]['name']
        print(f"Testing [{idx}] {name}...", end=" ", flush=True)
        try:
            fs = 16000
            duration = 1.5
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16', device=idx)
            sd.wait()
            peak = np.max(np.abs(recording))
            print(f"Peak Level: {peak}")
            results.append((idx, name, peak))
        except Exception as e:
            print(f"Error: {e}")
            
    print("\n--- Summary (Sorted by Volume) ---")
    results.sort(key=lambda x: x[2], reverse=True)
    for idx, name, peak in results:
        status = "✅ WORKING" if peak > 500 else "❌ SILENT"
        print(f"{status} | Index [{idx}]: {name} (Peak: {peak})")
    
    if results and results[0][2] > 500:
        best_idx = results[0][0]
        print(f"\nRECOMMENDATION: Set KYRA_MIC_DEVICE={best_idx} in your .env file.")
    else:
        print("\nNo working microphone detected with sufficient volume. Please check your system settings.")

if __name__ == "__main__":
    test_mics()
