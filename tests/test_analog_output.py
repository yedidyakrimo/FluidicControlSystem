"""
Test analog outputs individually
"""

from mcculw import ul
from mcculw.enums import ULRange

board_num = 0

print("Testing analog outputs on USB-1408FS-Plus")
print("="*60)

for ao_ch in range(2):
    print(f"\nTesting Analog Output Channel {ao_ch}:")
    
    # Try different voltage values
    test_voltages = [0.0, 1.0, 2.5, 5.0]
    
    for voltage in test_voltages:
        try:
            # Convert to counts
            counts = int((voltage / 10.0) * 32768)
            counts = max(-32768, min(32767, counts))
            
            print(f"  Trying {voltage}V (counts: {counts})...", end=" ")
            ul.a_out(board_num, ao_ch, ULRange.BIP10VOLTS, counts)
            print("[OK]")
        except Exception as e:
            print(f"[ERROR] {e}")

