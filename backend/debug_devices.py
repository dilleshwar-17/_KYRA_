import sounddevice as sd
print("--- Audio Input Devices ---")
try:
    default_in = sd.default.device[0]
    for i, dev in enumerate(sd.query_devices()):
        if dev['max_input_channels'] > 0:
            default_marker = " (DEFAULT)" if i == default_in else ""
            print(f"[{i}] {dev['name']}{default_marker}")
except Exception as e:
    print(f"Error listing devices: {e}")
