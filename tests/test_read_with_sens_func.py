#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify READ? command with SENS:FUNC "VOLT","CURR" instead of FORM:ELEM
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
    sys.exit(1)

print("=" * 70)
print("Testing READ? Command with SENS:FUNC \"VOLT\",\"CURR\"")
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
    keithley_resource = None
    for resource in resources:
        try:
            inst = rm.open_resource(resource)
            idn = inst.query("*IDN?")
            if "2450" in idn.upper() or "KEITHLEY" in idn.upper():
                keithley_resource = resource
                print(f"   ✓ Found Keithley 2450: {resource}")
                break
            inst.close()
        except:
            continue
    
    if not keithley_resource:
        print("ERROR: Keithley 2450 not found!")
        sys.exit(1)
    
    inst = rm.open_resource(keithley_resource)
    inst.timeout = 5000
    
    print("\n" + "=" * 70)
    print("3. Setting up Keithley...")
    print("=" * 70)
    
    # Setup with SENS:FUNC "VOLT","CURR"
    setup_commands = [
        ("*RST", "Reset device"),
        ("SOUR:FUNC VOLT", "Set source function to voltage"),
        ("SOUR:VOLT:RANG:AUTO ON", "Enable auto-range"),
        ('SENS:FUNC "VOLT","CURR"', "Set sense function to BOTH voltage and current"),
        ("SENS:CURR:RANG:AUTO ON", "Enable auto-range for current"),
        ("SENS:VOLT:RANG:AUTO ON", "Enable auto-range for voltage"),
        ("SOUR:VOLT:ILIM 0.1", "Set current limit"),
        ("SENS:CURR:NPLC 1", "Set NPLC"),
        ("SOUR:VOLT 1.0", "Set voltage to 1.0V"),
        ("OUTP ON", "Turn output on"),
    ]
    
    for cmd, desc in setup_commands:
        try:
            print(f"   Sending: {cmd:40} ({desc})")
            inst.write(cmd)
            time.sleep(0.1)
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
            sys.exit(1)
    
    print("\n" + "=" * 70)
    print("4. Testing READ? command...")
    print("=" * 70)
    
    time.sleep(0.5)
    
    # Test READ? command
    for i in range(5):
        try:
            print(f"\n   Test #{i+1}:")
            read_string = inst.query("READ?")
            print(f"   Raw response: '{read_string.strip()}'")
            
            values = read_string.strip().split(',')
            print(f"   Parsed values: {values}")
            print(f"   Number of values: {len(values)}")
            
            if len(values) >= 2:
                try:
                    voltage = float(values[0])
                    current = float(values[1])
                    print(f"   ✓ Voltage: {voltage} V")
                    print(f"   ✓ Current: {current} A")
                    print(f"   ✓ SUCCESS: READ? returned {len(values)} values!")
                except ValueError as e:
                    print(f"   ✗ ERROR parsing: {e}")
            else:
                print(f"   ✗ ERROR: Only {len(values)} value(s) returned")
            
            time.sleep(0.2)
        except Exception as e:
            print(f"   ✗ ERROR: {e}")
    
    # Cleanup
    print("\n" + "=" * 70)
    print("5. Cleaning up...")
    inst.write("SOUR:VOLT 0")
    inst.write("OUTP OFF")
    inst.close()
    rm.close()
    
    print("Test completed!")
    print("=" * 70)
    
except Exception as e:
    print(f"\n✗ FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()

