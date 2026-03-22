import sounddevice as sd
print("\n--- Available Audio Devices ---")
devices = sd.query_devices()
for i, d in enumerate(devices):
    input_channels = d.get('max_input_channels', 0)
    output_channels = d.get('max_output_channels', 0)
    default = "*" if i == sd.default.device[0] else " "
    print(f"{default} [{i}] {d['name']} (In: {input_channels}, Out: {output_channels})")
print("\n* = Default Input Device")
