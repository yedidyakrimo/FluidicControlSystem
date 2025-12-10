"""
Test HardwareController with MCusb-1408FS-Plus
"""

from hardware.hardware_controller import HardwareController

print("="*60)
print("Testing HardwareController with MCusb-1408FS-Plus")
print("="*60 + "\n")

try:
    # Initialize hardware controller
    print("Initializing HardwareController...")
    hw_controller = HardwareController(
        pump_port='COM3',
        mc_board_num=0,  # Board 0 as detected
        smu_resource=None
    )
    
    print("\n[OK] HardwareController initialized successfully")
    print(f"  - DAQ Device: {hw_controller.ni_device_name}")
    print(f"  - DAQ Connected: {hw_controller.ni_daq.is_connected()}")
    print(f"  - DAQ Simulation Mode: {hw_controller.ni_daq.simulation_mode}")
    
    # Test sensor readings
    print("\n" + "-"*60)
    print("Testing sensor readings...")
    print("-"*60)
    
    try:
        pressure = hw_controller.read_pressure_sensor()
        print(f"  - Pressure: {pressure:.2f} bar")
    except Exception as e:
        print(f"  - Pressure: Error - {e}")
    
    try:
        temperature = hw_controller.read_temperature_sensor()
        print(f"  - Temperature: {temperature:.2f} °C")
    except Exception as e:
        print(f"  - Temperature: Error - {e}")
    
    try:
        flow = hw_controller.read_flow_sensor()
        print(f"  - Flow: {flow:.2f} ml/min")
    except Exception as e:
        print(f"  - Flow: Error - {e}")
    
    try:
        level = hw_controller.read_level_sensor()
        print(f"  - Level: {level*100:.2f} %")
    except Exception as e:
        print(f"  - Level: Error - {e}")
    
    # Test digital outputs (valves)
    print("\n" + "-"*60)
    print("Testing digital outputs (valves)...")
    print("-"*60)
    
    try:
        hw_controller.set_valves(True, False)
        print("  - Valves set: Valve 1 (Main) = ON, Valve 2 (Rinsing) = OFF")
    except Exception as e:
        print(f"  - Valves: Error - {e}")
    
    # Cleanup
    print("\n" + "-"*60)
    print("Cleaning up...")
    print("-"*60)
    hw_controller.cleanup()
    print("[OK] Cleanup completed")
    
    print("\n" + "="*60)
    print("[SUCCESS] All tests completed!")
    print("="*60)
    
except Exception as e:
    print(f"\n[ERROR] Failed to initialize HardwareController: {e}")
    import traceback
    traceback.print_exc()

