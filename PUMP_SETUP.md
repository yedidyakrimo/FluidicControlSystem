# Vapourtec SF-10 Pump Setup Guide

## Installation

To connect to the Vapourtec SF-10 pump, you must install the `vapourtec` Python library:

```bash
pip install vapourtec
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Connection Protocol

The pump connection uses a **hybrid approach**:

1. **Library Connection**: Use the `vapourtec` library for the initial connection handshake
2. **Raw Commands**: Use raw serial commands for configuration that the library doesn't support

### Critical Patches Required

#### 1. Black Tube Type Setup (CRITICAL)

The library does not natively support setting the "Black" tube type (ID 3). This must be done via raw command immediately after connection:

```python
from vapourtec import SF10

pump = SF10('COM3')
pump.ser.write(b'STTA 3\r\n')  # Set Tube Type A = 3 (Black)
time.sleep(0.5)  # Wait for hardware to process
```

**Without this patch, the pump will not accept flow rate commands.**

#### 2. Pressure Reading Patch

The standard `read_all()` method causes an `AttributeError`. Use `in_waiting` instead:

```python
def get_pressure(pump_obj):
    try:
        pump_obj.ser.write(b'GP\r\n')  # Send 'Get Pressure'
        time.sleep(0.1)  # Wait for response
        
        # Use in_waiting instead of read_all()
        if pump_obj.ser.in_waiting > 0:
            response = pump_obj.ser.read(pump_obj.ser.in_waiting).decode().strip()
            return float(response)
        return 0.0
    except Exception as e:
        print(f"Error reading pressure: {e}")
        return None
```

### Timing Requirements

Always include short delays after sending raw commands:
- After `STTA` command: `time.sleep(0.5)` seconds
- After `GP` command: `time.sleep(0.1)` seconds

This allows the hardware to process the request before reading the response.

## Flow Rate Limits

- **Maximum Flow Rate**: 5.0 ml/min
- **Minimum Flow Rate**: 0.0 ml/min
- The system will automatically cap any flow rate above 5.0 ml/min

## Connection Status

The pump status is displayed in the Main tab:
- **Connected** (green): Pump is connected and ready
- **Simulation Mode** (orange): Library not found, running in simulation
- **Not Connected** (red): Connection failed

## Troubleshooting

### "vapourtec library not found"

**Solution**: Install the library:
```bash
pip install vapourtec
```

### Pump doesn't accept flow rate commands

**Solution**: Make sure the tube type is set correctly. The code automatically sends `STTA 3` after connection, but verify it's working.

### Pressure reading fails

**Solution**: The code uses `in_waiting` method which should work. If it still fails, check:
1. Serial port connection (COM3)
2. Pump is powered on
3. Correct baudrate (usually 9600)

## Example Usage

```python
from hardware.pump.vapourtec_pump import VapourtecPump

# Initialize pump (automatically connects and sets tube type)
pump = VapourtecPump(port='COM3', tube_type=3)

# Set flow rate (max 5.0 ml/min)
pump.set_flow_rate(2.5)

# Start pump
pump.start()

# Read pressure
pressure = pump.get_pressure()
print(f"Current pressure: {pressure} bar")

# Stop pump
pump.stop()

# Disconnect
pump.disconnect()
```


