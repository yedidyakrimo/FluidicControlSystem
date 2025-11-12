#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify SCPI commands for Keithley 2450
"""

import pyvisa
import time

print("=" * 60)
print("Testing SCPI Commands for Keithley 2450")
print("=" * 60)

try:
    # Connect to device
    rm = pyvisa.ResourceManager()
    resources = rm.list_resources()
    
    if len(resources) == 0:
        print("ERROR: No devices found!")
        exit(1)
    
    # Find Keithley 2450
    keithley_resource = None
    for resource in resources:
        try:
            inst = rm.open_resource(resource)
            idn = inst.query("*IDN?")
            if "2450" in idn.upper() or "KEITHLEY" in idn.upper():
                keithley_resource = resource
                print(f"Found Keithley 2450: {resource}")
                print(f"Device ID: {idn.strip()}")
                break
            inst.close()
        except:
            continue
    
    if not keithley_resource:
        print("ERROR: Keithley 2450 not found!")
        exit(1)
    
    inst = rm.open_resource(keithley_resource)
    inst.timeout = 5000  # 5 second timeout
    
    print("\n" + "=" * 60)
    print("Testing individual SCPI commands...")
    print("=" * 60)
    
    # Test commands one by one
    test_commands = [
        ("*RST", "Reset"),
        ("SOUR:FUNC VOLT", "Set source function to voltage"),
        ("SENS:FUNC \"CURR\"", "Set sense function to current"),
        ("SENS:CURR:PROT 0.1", "Set current protection"),
        ("SENS:CURR:NPLC 1", "Set NPLC (FIXED: was CURR:NPLC)"),
        ("SENS:CURR:RANG 0.1", "Set current range"),
        ("SOUR:VOLT 1.0", "Set voltage to 1V"),
        ("OUTP ON", "Turn output on"),
        ("INIT", "Initiate measurement"),
        ("READ?", "Read measurement"),
        ("SOUR:VOLT?", "Query voltage"),
        ("MEAS:CURR?", "Measure current"),
        ("OUTP?", "Query output state"),
        ("OUTP OFF", "Turn output off"),
    ]
    
    print("\nTesting basic commands:")
    for cmd, desc in test_commands:
        try:
            if "?" in cmd:
                result = inst.query(cmd)
                print(f"  OK: {cmd:30s} -> {result.strip()[:50]}")
            else:
                inst.write(cmd)
                print(f"  OK: {cmd:30s} ({desc})")
        except Exception as e:
            print(f"  ERROR: {cmd:30s} -> {str(e)[:50]}")
    
    print("\n" + "=" * 60)
    print("Testing sweep commands...")
    print("=" * 60)
    
    sweep_commands = [
        ("*RST", "Reset"),
        ("SOUR:FUNC VOLT", "Set source function"),
        ("SOUR:VOLT:RANG 10", "Set voltage range"),
        ("SOUR:VOLT:ILIM 0.1", "Set current limit"),
        ("SENS:FUNC \"CURR\"", "Set sense function"),
        ("SENS:CURR:RANG 0.1", "Set current range"),
        ("SOUR:VOLT:STARt 0", "Set start voltage (FIXED: was STAR)"),
        ("SOUR:VOLT:STOP 5", "Set stop voltage"),
        ("SOUR:SWE:POIN 11", "Set sweep points"),
        ("SOUR:SWE:SPAC LIN", "Set sweep spacing (FIXED: was SOUR:VOLT:MODE SWE)"),
        ("SOUR:SWE:VOLT:STAT ON", "Enable voltage sweep (FIXED: was SOUR:VOLT:MODE SWE)"),
        ("SENS:CURR:APER 0.1", "Set aperture (FIXED: was SENS:CURR:DC:APER)"),
    ]
    
    for cmd, desc in sweep_commands:
        try:
            inst.write(cmd)
            print(f"  OK: {cmd:35s} ({desc})")
        except Exception as e:
            print(f"  ERROR: {cmd:35s} -> {str(e)[:50]}")
    
    # Clean up
    inst.write("SOUR:VOLT 0")
    inst.write("OUTP OFF")
    inst.close()
    rm.close()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

