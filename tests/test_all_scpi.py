#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test ALL SCPI commands used in the code to find errors
"""

import pyvisa
import time
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 70)
print("Testing ALL SCPI Commands from hardware_control.py")
print("=" * 70)

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
                print(f"Device ID: {idn.strip()}\n")
                break
            inst.close()
        except:
            continue
    
    if not keithley_resource:
        print("ERROR: Keithley 2450 not found!")
        exit(1)
    
    inst = rm.open_resource(keithley_resource)
    inst.timeout = 5000
    
    # Test setup_smu_for_iv_measurement commands
    print("=" * 70)
    print("Testing setup_smu_for_iv_measurement() commands:")
    print("=" * 70)
    
    test_commands_1 = [
        ("SOUR:FUNC VOLT", "Set source function to voltage"),
        ('SENS:FUNC "CURR"', "Set sense function to current"),
        ("SOUR:VOLT:ILIM 0.1", "Set current limit (compliance) - FIXED: was SENS:CURR:PROT"),
        ('SENS:CURR:NPLC 1', "Set NPLC"),
        ('SENS:CURR:RANG 0.1', "Set current range"),
        ("OUTP ON", "Turn output on"),
    ]
    
    for cmd, desc in test_commands_1:
        try:
            inst.write(cmd)
            print(f"  OK: {cmd:30s} - {desc}")
        except Exception as e:
            print(f"  ERROR: {cmd:30s} - {str(e)[:60]}")
    
    # Reset before next test
    inst.write("*RST")
    time.sleep(0.5)
    
    # Test setup_smu_iv_sweep commands
    print("\n" + "=" * 70)
    print("Testing setup_smu_iv_sweep() commands:")
    print("=" * 70)
    
    test_commands_2 = [
        ("*RST", "Reset"),
        ("SOUR:FUNC VOLT", "Set source function"),
        ("SOUR:VOLT:RANG 10", "Set voltage range"),
        ("SOUR:VOLT:ILIM 0.1", "Set current limit (compliance)"),
        ('SENS:FUNC "CURR"', "Set sense function"),
        ("SENS:CURR:RANG 0.1", "Set current range"),
        ("SENS:CURR:NPLC 1", "Set NPLC"),
        ("SENS:CURR:APER 0.1", "Set aperture"),
        # Note: Using manual sweep mode (not built-in sweep) to avoid trigger model issues
        # Removed: SOUR:VOLT:STARt, SOUR:VOLT:STOP, SOUR:SWE:POIN, SOUR:SWE:SPAC, SOUR:SWE:VOLT:STAT
    ]
    
    for cmd, desc in test_commands_2:
        try:
            inst.write(cmd)
            print(f"  OK: {cmd:35s} - {desc}")
        except Exception as e:
            print(f"  ERROR: {cmd:35s} - {str(e)[:60]}")
    
    # Test query commands
    print("\n" + "=" * 70)
    print("Testing query commands:")
    print("=" * 70)
    
    test_queries = [
        ("MEAS:CURR?", "Measure current"),
        ("SOUR:VOLT?", "Query voltage"),
        ("OUTP?", "Query output state"),
        ("STAT:OPER:COND?", "Query operation status"),
    ]
    
    for cmd, desc in test_queries:
        try:
            result = inst.query(cmd)
            print(f"  OK: {cmd:30s} - {desc} -> {result.strip()[:40]}")
        except Exception as e:
            print(f"  ERROR: {cmd:30s} - {str(e)[:60]}")
    
    # Clean up
    inst.write("SOUR:VOLT 0")
    inst.write("OUTP OFF")
    inst.close()
    rm.close()
    
    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

