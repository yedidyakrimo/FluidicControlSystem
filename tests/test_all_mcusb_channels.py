"""
Test all MCusb-1408FS-Plus analog input channels
to identify which channel is connected to Keithley
"""

from hardware.hardware_controller import HardwareController
import time

print("="*60)
print("Testing all MCusb-1408FS-Plus analog input channels")
print("="*60 + "\n")

# Initialize hardware controller
hw_controller = HardwareController(
    pump_port='COM3',
    mc_board_num=0,
    smu_resource=None
)

if not hw_controller.ni_daq or not hw_controller.ni_daq.is_connected():
    print("[ERROR] MCusb-1408FS-Plus is not connected!")
    exit(1)

print("[OK] MCusb-1408FS-Plus is connected\n")
print("Reading all channels (CH0-CH3)...")
print("Note: Connect Keithley to one channel and see which one changes\n")
print("-"*60)

# Read all channels multiple times to see variations
for iteration in range(5):
    print(f"\nIteration {iteration + 1}:")
    for ch in range(4):  # CH0-CH3
        try:
            voltage = hw_controller.ni_daq.read_analog_input(f'ai{ch}')
            if voltage is not None:
                print(f"  CH{ch} (ai{ch}): {voltage:.4f} V")
            else:
                print(f"  CH{ch} (ai{ch}): Error reading")
        except Exception as e:
            print(f"  CH{ch} (ai{ch}): Error - {e}")
    
    if iteration < 4:
        time.sleep(0.5)

print("\n" + "="*60)
print("Analysis:")
print("  - If all channels show ~2.5V, check connections")
print("  - The channel connected to Keithley should change when SMU voltage changes")
print("  - Channel connected to ground should be ~0V")
print("="*60)

