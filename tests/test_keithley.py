#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for Keithley 2450 detection
"""

import pyvisa
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("Testing Keithley 2450 SMU Detection")
print("=" * 60)

try:
    # Try to create ResourceManager
    print("\n1. Attempting to connect to VISA...")
    rm = pyvisa.ResourceManager()
    print(f"   OK VISA ResourceManager created: {rm}")
    
    # List all available resources
    print("\n2. Searching for available devices...")
    resources = rm.list_resources()
    print(f"   Found {len(resources)} resource(s):")
    
    if len(resources) == 0:
        print("   ERROR: No devices found!")
        print("\n   Tips:")
        print("   - Make sure device is connected via USB")
        print("   - Make sure device is powered on")
        print("   - Make sure NI-VISA is installed")
    else:
        for i, resource in enumerate(resources, 1):
            print(f"\n   {i}. {resource}")
            
            # Try to connect to device
            try:
                inst = rm.open_resource(resource)
                idn = inst.query("*IDN?")
                print(f"      OK Connection successful!")
                print(f"      Device ID: {idn.strip()}")
                
                # Check if it's Keithley 2450
                if "2450" in idn.upper() or "KEITHLEY" in idn.upper():
                    print(f"      OK This is Keithley 2450 SMU!")
                    print(f"      Resource string: {resource}")
                else:
                    print(f"      WARNING: This is not Keithley 2450")
                
                inst.close()
            except Exception as e:
                print(f"      ERROR connecting: {e}")
    
    rm.close()
    print("\n" + "=" * 60)
    print("Test completed")
    print("=" * 60)
    
except Exception as e:
    print(f"\nERROR: {e}")
    print("\nOptions:")
    print("1. Make sure NI-VISA is installed")
    print("2. Try: py -m pip install pyvisa pyvisa-py")
    import traceback
    traceback.print_exc()

