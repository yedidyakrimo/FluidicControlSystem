"""
Test analog outputs with different ranges
"""

from mcculw import ul
from mcculw.enums import ULRange

board_num = 0

print("Testing analog outputs with different ranges")
print("="*60)

ranges_to_test = [
    (ULRange.BIP10VOLTS, "BIP10VOLTS (±10V)"),
    (ULRange.UNI10VOLTS, "UNI10VOLTS (0-10V)"),
    (ULRange.BIP5VOLTS, "BIP5VOLTS (±5V)"),
    (ULRange.UNI5VOLTS, "UNI5VOLTS (0-5V)"),
]

for ao_ch in range(2):
    print(f"\nAnalog Output Channel {ao_ch}:")
    
    for ul_range, range_name in ranges_to_test:
        try:
            # Try 0V
            if "UNI" in range_name:
                # For unipolar, 0V = 0 counts
                counts = 0
            else:
                # For bipolar, 0V = middle (0 counts)
                counts = 0
            
            print(f"  {range_name}: 0V...", end=" ")
            ul.a_out(board_num, ao_ch, ul_range, counts)
            print("[OK]", end=" ")
            
            # Try 5V
            if "UNI10" in range_name:
                counts = int((5.0 / 10.0) * 65536)  # 0-10V, 16-bit
            elif "UNI5" in range_name:
                counts = int((5.0 / 5.0) * 65536)  # 0-5V, 16-bit
            elif "BIP10" in range_name:
                counts = int((5.0 / 10.0) * 32768)  # ±10V, 16-bit
            else:  # BIP5
                counts = int((5.0 / 5.0) * 32768)  # ±5V, 16-bit
            
            ul.a_out(board_num, ao_ch, ul_range, counts)
            print("5V [OK]")
            
        except Exception as e:
            print(f"[ERROR] {e}")

