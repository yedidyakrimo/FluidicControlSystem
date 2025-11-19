# Test Scripts

This directory contains all test scripts for the Fluidic Control System.

## Test Files

### Hardware Detection Tests
- `test_mcusb_detection.py` - Detects and tests MCusb-1408FS-Plus DAQ device
- `test_keithley.py` - Detects and tests Keithley 2450 SMU device

### Hardware Controller Tests
- `test_hardware_controller.py` - Tests the HardwareController class with MCusb device
- `test_all_mcusb_channels.py` - Tests all analog input channels on MCusb-1408FS-Plus

### MCusb-1408FS-Plus Specific Tests
- `test_device_info.py` - Gets detailed device information
- `test_digital_ports.py` - Tests digital I/O ports
- `test_analog_output.py` - Tests analog output channels
- `test_analog_output_ranges.py` - Tests different analog output ranges

### Keithley SMU Tests
- `test_scpi_commands.py` - Tests individual SCPI commands
- `test_all_scpi.py` - Tests all SCPI commands used in the application

## Running Tests

All tests should be run from the project root directory:

```bash
python tests/test_mcusb_detection.py
python tests/test_keithley.py
python tests/test_hardware_controller.py
# etc.
```

Or from within the tests directory:

```bash
cd tests
python test_mcusb_detection.py
```

## Notes

- Some tests require hardware to be connected
- Some tests may require specific drivers (NI-VISA for Keithley, mcculw for MCusb)
- Check individual test files for specific requirements

