"""
MCusb-1408FS-Plus DAQ control module
Measurement Computing USB-1408FS-Plus
"""

try:
    from mcculw import ul
    from mcculw.enums import ULRange, DigitalIODirection, InterfaceType
    MCCULW_AVAILABLE = True
    # USB-1408FS-Plus analog outputs support only 0-5V range
    ANALOG_OUTPUT_RANGE = ULRange.UNI5VOLTS
except ImportError:
    MCCULW_AVAILABLE = False
    ANALOG_OUTPUT_RANGE = None
    print("mcculw library not available. MCusb-1408FS-Plus will run in simulation mode.")

from hardware.base import HardwareBase


class MCusb1408FS(HardwareBase):
    """
    Measurement Computing USB-1408FS-Plus DAQ controller
    """
    
    def __init__(self, board_num=0):
        """
        Initialize MCusb-1408FS-Plus
        
        Args:
            board_num: Board number (default 0 for first board)
        """
        super().__init__()
        self.device_name = "MCusb-1408FS-Plus"
        self.board_num = board_num
        self.board_id = None
        
        self.connect()
    
    def connect(self):
        """Connect to MCusb-1408FS-Plus device"""
        if not MCCULW_AVAILABLE:
            print("mcculw library not available. Running in simulation mode.")
            self.enable_simulation()
            return False
        
        try:
            # Get board info
            board_info = ul.get_board_name(self.board_num)
            if board_info:
                self.board_id = self.board_num
                print(f"Connected to {self.device_name} (Board {self.board_num})")
                self.connected = True
                self.simulation_mode = False
                return True
            else:
                raise Exception("Board not found")
        except Exception as e:
            print(f"Error connecting to {self.device_name}: {e}")
            print("Running in simulation mode.")
            self.enable_simulation()
            return False
    
    def disconnect(self):
        """Disconnect from MCusb-1408FS-Plus device"""
        # mcculw doesn't require explicit disconnect
        self.connected = False
        self.board_id = None
    
    def read_analog_input(self, channel, differential=False):
        """
        Read analog input from specified channel
        
        Args:
            channel: Channel number (0-7 for USB-1408FS-Plus) or string like 'ai0'
            differential: If True, read differential measurement (IN HI - IN LO)
                        For Channel 0, reads CH0 (IN HI) and CH1 (IN LO) and returns difference
            
        Returns:
            Voltage value in volts or None on error
        """
        if not self.connected or not MCCULW_AVAILABLE:
            return None
        
        try:
            # Convert channel string to int (e.g., 'ai0' -> 0, 'ai1' -> 1)
            if isinstance(channel, str):
                # Extract number from channel string
                channel_num = int(channel.replace('ai', ''))
            else:
                channel_num = int(channel)
            
            # USB-1408FS-Plus has 4 analog input channels (0-3)
            if channel_num > 3:
                print(f"Warning: Channel {channel_num} is out of range. USB-1408FS-Plus has 4 channels (0-3)")
                return None
            
            if differential:
                # Differential measurement: Read IN HI (CH0) and IN LO (CH1) and return difference
                # FIXED: Use ul.to_eng_units() for correct conversion
                # For Channel 0 differential, we read CH0 as IN HI and CH1 as IN LO
                try:
                    ai_range = ULRange.BIP10VOLTS
                    
                    # Read IN HI (Channel 0)
                    hi_raw = ul.a_in(self.board_id, channel_num, ai_range)
                    hi_voltage = ul.to_eng_units(self.board_id, ai_range, hi_raw)
                    
                    # Read IN LO (Channel 1, or ground if CH1 not available)
                    # For differential pair, typically CH0 and CH1 are paired
                    lo_channel = channel_num + 1 if channel_num < 3 else 0
                    try:
                        lo_raw = ul.a_in(self.board_id, lo_channel, ai_range)
                        lo_voltage = ul.to_eng_units(self.board_id, ai_range, lo_raw)
                    except Exception as e:
                        # If CH1 read fails, assume IN LO is at ground (0V)
                        lo_voltage = 0.0
                    
                    # Return differential voltage (IN HI - IN LO)
                    diff_voltage = hi_voltage - lo_voltage
                    return diff_voltage
                except Exception as e:
                    print(f"Error reading differential input: {e}")
                    import traceback
                    traceback.print_exc()
                    return None
            else:
                # Single-ended measurement
                # FIXED: Use ul.to_eng_units() for correct conversion
                # The mcculw library automatically handles the board's ADC resolution (13-bit for USB-1408FS-Plus)
                # Read analog input (USB-1408FS-Plus uses BIP10VOLTS range: -10V to +10V)
                ai_range = ULRange.BIP10VOLTS
                raw_value = ul.a_in(self.board_id, channel_num, ai_range)
                
                # Use the MCC function to correctly convert counts to Volts
                # This function handles the 13-bit resolution automatically
                voltage_volts = ul.to_eng_units(self.board_id, ai_range, raw_value)
                
                return voltage_volts
        except Exception as e:
            print(f"Error reading analog input channel {channel}: {e}")
            return None
    
    def write_digital_output(self, channel, value):
        """
        Write digital output using dedicated DIO ports
        
        FIXED: USB-1408FS-Plus has 16 dedicated Digital I/O lines (Port A and Port B)
        Use ul.d_bit_out() for proper digital I/O control
        
        Args:
            channel: Channel specification (e.g., 'port0/line0' or port/bit number)
            value: Output value (True/False or 0/1)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected or not MCCULW_AVAILABLE:
            return False
        
        try:
            # Parse channel specification
            # Format: 'port0/line0' -> port 0, bit 0
            # Or just a number for bit number (defaults to port 0)
            if isinstance(channel, str):
                if '/' in channel:
                    parts = channel.split('/')
                    port_str = parts[0].replace('port', '')
                    bit_str = parts[1].replace('line', '')
                    port_num = int(port_str)
                    bit_num = int(bit_str)
                else:
                    # Default to port 0
                    port_num = 0
                    bit_num = int(channel.replace('line', ''))
            else:
                # Default to port 0, bit = channel number
                port_num = 0
                bit_num = int(channel)
            
            # USB-1408FS-Plus has Port A (bits 0-7) and Port B (bits 0-7)
            # For simplicity, we'll use AUXPORT (Port A) for port 0
            # You may need to adjust this based on your physical connections
            if port_num == 0:
                dio_port = DigitalIODirection.AUXPORT
            else:
                # Port B - you may need to use a different enum value
                dio_port = DigitalIODirection.AUXPORT  # Default to AUXPORT
            
            # Ensure bit number is valid (0-7)
            bit_num = max(0, min(7, bit_num))
            
            # Convert value to 0 or 1
            bit_value = 1 if value else 0
            
            # Write digital bit using mcculw function
            ul.d_bit_out(self.board_id, dio_port, bit_num, bit_value)
            
            print(f"Digital output: Port {port_num}, Bit {bit_num} set to {bit_value} ({'ON' if value else 'OFF'})")
            return True
        except Exception as e:
            print(f"Error writing digital output {channel}: {e}")
            # Fallback: Try using analog output simulation if DIO fails
            print(f"Attempting fallback to analog output simulation...")
            try:
                # Fallback to analog output simulation
                ao_channel = 1
                voltage = 5.0 if value else 0.0
                # Use 12-bit DAC (4095 max counts)
                MAX_DAC_COUNT = 4095
                if voltage >= 5.0:
                    counts = MAX_DAC_COUNT
                else:
                    counts = int((voltage / 5.0) * MAX_DAC_COUNT)
                counts = max(0, min(MAX_DAC_COUNT, counts))
                ul.a_out(self.board_id, ao_channel, ANALOG_OUTPUT_RANGE, counts)
                print(f"Fallback: Digital output {channel} -> Analog output {ao_channel}: {voltage}V")
                return True
            except Exception as e2:
                print(f"Error in fallback analog output: {e2}")
                return False
    
    def write_analog_output(self, channel, voltage):
        """
        Write analog output
        
        Args:
            channel: Analog output channel (e.g., 'ao0' or channel number)
            voltage: Voltage value (typically 0-5V or -10V to +10V)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected or not MCCULW_AVAILABLE:
            return False
        
        try:
            # Convert channel string to int (e.g., 'ao0' -> 0)
            if isinstance(channel, str):
                channel_num = int(channel.replace('ao', ''))
            else:
                channel_num = int(channel)
            
            # USB-1408FS-Plus analog outputs support only 0-5V range
            # FIXED: USB-1408FS-Plus has 12-bit DAC, not 16-bit
            # Max count for 12-bit is 2^12 - 1 = 4095
            MAX_DAC_COUNT = 4095
            DAC_RANGE = 5.0  # 0-5V range (UNI5VOLTS)
            
            # Clamp voltage to valid range
            voltage = max(0.0, min(DAC_RANGE, voltage))
            
            # Convert voltage to 12-bit counts
            if voltage >= DAC_RANGE:
                counts = MAX_DAC_COUNT
            else:
                counts = int((voltage / DAC_RANGE) * MAX_DAC_COUNT)
            
            # Clamp counts to valid range (0-4095 for 12-bit unipolar)
            counts = max(0, min(MAX_DAC_COUNT, counts))
            
            # Write analog output
            ul.a_out(self.board_id, channel_num, ANALOG_OUTPUT_RANGE, counts)
            
            return True
        except Exception as e:
            print(f"Error writing analog output channel {channel}: {e}")
            return False

