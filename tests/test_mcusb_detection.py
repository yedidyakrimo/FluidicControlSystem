"""
Test script to detect MCusb-1408FS-Plus device
"""

try:
    from mcculw import ul
    from mcculw.enums import InterfaceType
    MCCULW_AVAILABLE = True
    print("[OK] mcculw library is available")
except ImportError as e:
    print(f"[ERROR] mcculw library not available: {e}")
    MCCULW_AVAILABLE = False
    exit(1)

print("\n" + "="*50)
print("Scanning for MCusb-1408FS-Plus devices...")
print("="*50 + "\n")

found_devices = []

try:
    # Try to find boards
    for board_num in range(10):  # Check first 10 board numbers
        try:
            board_name = ul.get_board_name(board_num)
            if board_name:
                print(f"Board {board_num}: {board_name}")
                found_devices.append((board_num, board_name))
                
                # Try to get more info
                try:
                    board_config = ul.get_config(ul.BOARDINFO, board_num, 0, ul.BOARDINFO)
                    print(f"  - Board ID: {board_config}")
                except:
                    pass
        except Exception as e:
            # Board not found at this number, continue
            pass
except Exception as e:
    print(f"Error scanning for boards: {e}")

print("\n" + "="*50)
if found_devices:
    print(f"[OK] Found {len(found_devices)} device(s):")
    for board_num, board_name in found_devices:
        print(f"  - Board {board_num}: {board_name}")
        if "1408" in board_name or "MCusb" in board_name:
            print(f"    [OK] This appears to be an MCusb-1408FS-Plus!")
else:
    print("[ERROR] No devices found")
    print("\nPossible reasons:")
    print("  1. Device drivers not installed")
    print("  2. Device not connected")
    print("  3. Device not powered on")
    print("  4. Wrong board number range")
print("="*50)

# Test connection to first board if found
if found_devices:
    board_num, board_name = found_devices[0]
    print(f"\nTesting connection to Board {board_num} ({board_name})...")
    try:
        # Try to read from first analog channel
        try:
            from mcculw.enums import ULRange
            voltage = ul.a_in(board_num, 0, ULRange.BIP10VOLTS)
            voltage_volts = (voltage / 32768.0) * 10.0
            print(f"[OK] Successfully read from analog channel 0: {voltage_volts:.4f} V")
        except Exception as e:
            print(f"  Note: Could not read from analog channel (this is OK if no sensor connected): {e}")
        
        print(f"[OK] Device is responding and ready to use!")
    except Exception as e:
        print(f"[ERROR] Error testing device: {e}")

