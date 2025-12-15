#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify READ? command returns all values (voltage, current, resistance, status)
"""

import sys
import io
import time

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import pyvisa
except ImportError:
    print("ERROR: pyvisa not installed!")
    print("Install with: pip install pyvisa")
    sys.exit(1)

print("=" * 70)
print("Testing READ? Command with FORM:ELEM Configuration")
print("=" * 70)

try:
    # Connect to device
    print("\n1. Connecting to VISA...")
    rm = pyvisa.ResourceManager()
    resources = rm.list_resources()
    
    if len(resources) == 0:
        print("ERROR: No devices found!")
        sys.exit(1)
    
    # Find Keithley 2450
    print(f"\n2. Searching for Keithley 2450...")
    print(f"   Found {len(resources)} resource(s)")
    
    keithley_resource = None
    for resource in resources:
        try:
            inst = rm.open_resource(resource)
            idn = inst.query("*IDN?")
            if "2450" in idn.upper() or "KEITHLEY" in idn.upper():
                keithley_resource = resource
                print(f"   ✓ Found Keithley 2450: {resource}")
                print(f"   Device ID: {idn.strip()}")
                break
            inst.close()
        except:
            continue
    
    if not keithley_resource:
        print("ERROR: Keithley 2450 not found!")
        sys.exit(1)
    
    # Open connection
    inst = rm.open_resource(keithley_resource)
    inst.timeout = 5000  # 5 second timeout
    
    print("\n" + "=" * 70)
    print("3. Setting up Keithley for I-V measurement...")
    print("=" * 70)
    
    # Setup commands (same as setup_for_iv_measurement)
    setup_commands = [
        ("*RST", "Reset device"),
        ("SOUR:FUNC VOLT", "Set source function to voltage"),
        ("SOUR:VOLT:RANG:AUTO ON", "Enable auto-range for voltage source"),
        ('SENS:FUNC "CURR"', "Set sense function to current"),
        ("SENS:CURR:RANG:AUTO ON", "Enable auto-range for current measurement"),
        ("SOUR:VOLT:ILIM 0.1", "Set current limit to 0.1A"),
        ("SENS:CURR:NPLC 1", "Set NPLC to 1"),
        ("FORM:ELEM VOLT,CURR,RES,STAT", "Set data format elements (V, I, R, S)"),
        ("SOUR:VOLT 1.0", "Set voltage to 1.0V"),
        ("OUTP ON", "Turn output on"),
    ]
    
    for cmd, desc in setup_commands:
        try:
            print(f"   Sending: {cmd:40} ({desc})")
            inst.write(cmd)
            time.sleep(0.1)  # Small delay between commands
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            sys.exit(1)
    
    print("\n" + "=" * 70)
    print("4. Testing READ? command...")
    print("=" * 70)
    
    # Wait a bit for measurement to stabilize
    time.sleep(0.5)
    
    # Test READ? command multiple times
    for i in range(5):
        try:
            print(f"\n   Test #{i+1}:")
            read_string = inst.query("READ?")
            print(f"   Raw response: '{read_string}'")
            
            # Parse the response
            values = read_string.strip().split(',')
            print(f"   Parsed values: {values}")
            print(f"   Number of values: {len(values)}")
            
            if len(values) >= 2:
                try:
                    voltage = float(values[0])
                    current = float(values[1])
                    print(f"   ✓ Voltage: {voltage} V")
                    print(f"   ✓ Current: {current} A")
                    
                    if len(values) >= 3:
                        try:
                            resistance = float(values[2])
                            print(f"   ✓ Resistance: {resistance} Ω")
                        except:
                            print(f"   - Resistance: {values[2]} (could not parse)")
                    
                    if len(values) >= 4:
                        try:
                            status = int(values[3])
                            print(f"   ✓ Status: {status}")
                        except:
                            print(f"   - Status: {values[3]} (could not parse)")
                    
                    if len(values) == 4:
                        print(f"   ✓ SUCCESS: READ? returned all 4 values!")
                    elif len(values) == 2:
                        print(f"   ⚠ WARNING: READ? returned only 2 values (expected 4)")
                    else:
                        print(f"   ⚠ WARNING: READ? returned {len(values)} values (expected 4)")
                except ValueError as e:
                    print(f"   ✗ ERROR: Could not parse values: {e}")
            else:
                print(f"   ✗ ERROR: READ? returned only {len(values)} value(s) (expected at least 2)")
                print(f"   This means FORM:ELEM might not be working correctly")
            
            time.sleep(0.2)
            
        except Exception as e:
            print(f"   ✗ ERROR reading: {e}")
            import traceback
            traceback.print_exc()
    
    # Cleanup
    print("\n" + "=" * 70)
    print("5. Cleaning up...")
    print("=" * 70)
    try:
        inst.write("SOUR:VOLT 0")
        inst.write("OUTP OFF")
        print("   ✓ Output turned off")
    except:
        pass
    
    inst.close()
    rm.close()
    
    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n✗ FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

