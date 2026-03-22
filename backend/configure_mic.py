import sounddevice as sd
import numpy as np
import os
import time

def list_devices():
    print("\nAvailable Input Devices:")
    print("-" * 50)
    devices = sd.query_devices()
    input_devices = []
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            print(f"[{i}] {dev['name']} (Channels: {dev['max_input_channels']}, Default SR: {dev['default_samplerate']})")
            input_devices.append(i)
    print("-" * 50)
    return input_devices

def test_device(device_id):
    duration = 3  # seconds
    fs = 16000
    print(f"\n[TESTING DEVICE {device_id}] Speak now for {duration} seconds...")
    try:
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32', device=device_id)
        sd.wait()
        vol = np.max(np.abs(recording))
        print(f"Max Volume detected: {vol:.5f}")
        if vol > 0.01:
            print(">>> SUCCESS: Sound detected!")
            return True
        else:
            print(">>> FAILED: No significant sound detected. Try another device or check your mute settings.")
            return False
    except Exception as e:
        print(f"Error testing device: {e}")
        return False

def update_env(device_id):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            lines = f.readlines()
    
    found = False
    new_lines = []
    for line in lines:
        if line.startswith("KYRA_MIC_DEVICE="):
            new_lines.append(f"KYRA_MIC_DEVICE={device_id}\n")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append(f"KYRA_MIC_DEVICE={device_id}\n")
    
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    print(f"\n[OK] Updated .env with KYRA_MIC_DEVICE={device_id}")

def main():
    print("=" * 50)
    print(" KYRA Microphone Configuration Tool ")
    print("=" * 50)
    
    while True:
        input_ids = list_devices()
        try:
            choice = input("\nEnter Device ID to test (or 'q' to quit): ").strip().lower()
            if choice == 'q':
                break
            
            dev_id = int(choice)
            if dev_id not in input_ids:
                print("Invalid Device ID. Please pick from the list.")
                continue
            
            if test_device(dev_id):
                confirm = input("Did this microphone work? (y/n): ").strip().lower()
                if confirm == 'y':
                    update_env(dev_id)
                    print("\nConfiguration complete! You can now restart KYRA.")
                    break
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
