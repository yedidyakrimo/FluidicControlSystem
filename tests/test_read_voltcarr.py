#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test READ? with SENS:FUNC "VOLT,CURR" (no comma between quotes)
"""

import sys
import io
import time
import pyvisa

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("Testing SENS:FUNC \"VOLT,CURR\" (single string)")

rm = pyvisa.ResourceManager()
resources = rm.list_resources()

inst = None
for r in resources:
    try:
        temp = rm.open_resource(r)
        if "2450" in temp.query("*IDN?").upper():
            inst = temp
            print(f"Found: {r}")
            break
        temp.close()
    except:
        continue

if not inst:
    print("ERROR: Not found")
    sys.exit(1)

inst.timeout = 5000

try:
    inst.write("*RST")
    time.sleep(0.2)
    inst.write("SOUR:FUNC VOLT")
    inst.write('SENS:FUNC "VOLT,CURR"')  # Single string, comma inside quotes
    inst.write("SOUR:VOLT 1.0")
    inst.write("OUTP ON")
    time.sleep(0.5)
    
    result = inst.query("READ?")
    print(f"\nRaw result: '{result.strip()}'")
    values = result.strip().split(',')
    print(f"Values: {values}")
    print(f"Count: {len(values)}")
    
    inst.write("OUTP OFF")
    inst.close()
    rm.close()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

