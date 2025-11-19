"""
Test digital ports on MCusb-1408FS-Plus
"""

from mcculw import ul
from mcculw.enums import DigitalIODirection, ULRange

board_num = 0

print("Testing digital ports on USB-1408FS-Plus...")
print("="*60)

# Check available ports
print("\nChecking available digital ports...")
try:
    # USB-1408FS-Plus typically has FirstPortA and FirstPortB
    # Let's try different port configurations
    ports_to_try = [
        ("FirstPortA", 0),
        ("FirstPortB", 1),
        ("AuxPort", 2),
    ]
    
    for port_name, port_num in ports_to_try:
        try:
            # Try to configure port as output
            ul.d_config_port(board_num, port_num, DigitalIODirection.OUT)
            print(f"  [OK] Port {port_num} ({port_name}) configured as output")
            
            # Try to write to it
            ul.d_out(board_num, port_num, 1)
            print(f"  [OK] Successfully wrote to port {port_num}")
            
            # Read back
            value = ul.d_in(board_num, port_num)
            print(f"  [OK] Read back value: {value}")
            
        except Exception as e:
            print(f"  [ERROR] Port {port_num} ({port_name}): {e}")
            
except Exception as e:
    print(f"[ERROR] Error testing ports: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Note: USB-1408FS-Plus may use FirstPortA (0) and FirstPortB (1)")
print("="*60)

