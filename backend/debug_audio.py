import sounddevice as sd  # type: ignore

print("Available Audio Devices:")
print("-" * 50)
devices = sd.query_devices()
for i, d in enumerate(devices):
    print(f"ID: {i} | Name: {d['name']} | Input Channels: {d['max_input_channels']} | Output Channels: {d['max_output_channels']} | Default SR: {int(d['default_samplerate'])}")
print("-" * 50)
print(f"Default Input Device ID: {sd.default.device[0]}")
print(f"Default Output Device ID: {sd.default.device[1]}")
