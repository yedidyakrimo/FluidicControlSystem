"""
Level sensor control module
"""

from hardware.base import HardwareBase
from utils.logger_config import get_logger

logger = get_logger(__name__)


class LevelSensor(HardwareBase):
    """
    Level sensor
    Connected through NI USB-6002
    """
    
    def __init__(self, ni_daq=None, channel='ai3'):
        """
        Initialize level sensor
        
        Args:
            ni_daq: NI DAQ device instance
            channel: Analog input channel
        """
        super().__init__()
        self.device_name = "Level Sensor"
        self.ni_daq = ni_daq
        self.channel = channel
        
        if ni_daq and ni_daq.is_connected():
            self.connected = True
            self.simulation_mode = False
        else:
            self.connected = False
            self.simulation_mode = False
    
    def connect(self):
        """Connect to sensor (via NI DAQ)"""
        if self.ni_daq and self.ni_daq.is_connected():
            self.connected = True
            self.simulation_mode = False
            return True
        else:
            self.connected = False
            self.simulation_mode = False
            return False
    
    def disconnect(self):
        """Disconnect from sensor"""
        self.connected = False
    
    def read(self):
        """
        Read level value
        
        Returns:
            Level as fraction (0.0 to 1.0) or None on error (in real mode)
            In simulation mode, returns simulated value
        """
        # If no DAQ is available, do not provide simulated values
        if self.simulation_mode or not (self.ni_daq and self.ni_daq.is_connected()):
            return None
        
        # Real mode - try to read actual sensor
        try:
            voltage = self.ni_daq.read_analog_input(self.channel)
            
            # Check if voltage is None (read failed)
            if voltage is None:
                # In real mode, return None on read failure
                logger.debug(f"Level sensor: Failed to read voltage from channel {self.channel}")
                return None
            
            # Debug: Print voltage reading (can be enabled for debugging)
            # print(f"[LEVEL_SENSOR] Channel {self.channel} voltage: {voltage:.4f}V")
            
            # Convert voltage to level (calibration needed)
            # Note: If voltage is 0V, it could be:
            # 1. Tank is actually empty (valid reading)
            # 2. Sensor disconnected (but we can't distinguish, so treat as valid)
            # We'll treat 0V as valid (empty tank) and only return None on actual read failure
            
            # Normal conversion: voltage to level (0-5V = 0-1.0)
            # Note: Actual calibration may differ - adjust this formula based on your sensor
            # DAQ range is -10V to +10V, but sensor typically outputs 0-5V
            # Clamp negative voltages to 0 (noise or offset)
            voltage_clamped = max(0.0, voltage)
            level = voltage_clamped / 5.0  # Placeholder conversion (0-5V = 0-1.0)
            return max(0.0, min(1.0, level))  # Clamp to 0-1
            
        except Exception as e:
            logger.debug(f"Error reading level sensor: {e}")
            # In real mode, return None on error
            return None

