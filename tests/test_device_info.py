"""
Get detailed information about USB-1408FS-Plus capabilities
"""

from mcculw import ul
from mcculw.enums import ULRange, DigitalIODirection

board_num = 0

print("USB-1408FS-Plus Device Information")
print("="*60)

try:
    board_name = ul.get_board_name(board_num)
    print(f"Board Name: {board_name}")
    
    # Try to get board info
    try:
        # Get number of analog input channels
        num_ai_channels = ul.get_config(ul.BOARDINFO, board_num, 0, ul.BOARDINFO)
        print(f"Board Info (raw): {num_ai_channels}")
    except:
        pass
    
    # Test analog inputs
    print("\nAnalog Input Channels:")
    for ch in range(8):
        try:
            voltage = ul.a_in(board_num, ch, ULRange.BIP10VOLTS)
            voltage_volts = (voltage / 32768.0) * 10.0
            print(f"  Channel {ch}: {voltage_volts:.4f} V")
        except Exception as e:
            print(f"  Channel {ch}: Error - {e}")
    
    # Check for digital I/O
    print("\nDigital I/O:")
    print("  Note: USB-1408FS-Plus may not have digital I/O ports")
    print("  or may require different configuration")
    
    # Check for analog outputs
    print("\nAnalog Output Channels:")
    for ch in range(2):  # Most devices have 2 analog outputs
        try:
            # Try to write 0V
            counts = int((0.0 / 10.0) * 32768)
            ul.a_out(board_num, ch, ULRange.BIP10VOLTS, counts)
            print(f"  Channel {ch}: Available")
        except Exception as e:
            print(f"  Channel {ch}: Error - {e}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

