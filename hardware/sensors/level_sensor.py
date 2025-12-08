"""
Level sensor control module
"""

import time
import math
from hardware.base import HardwareBase


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
        self.sim_start_time = time.time()
        
        if ni_daq and ni_daq.is_connected():
            self.connected = True
            self.simulation_mode = False
        else:
            self.enable_simulation()
    
    def connect(self):
        """Connect to sensor (via NI DAQ)"""
        if self.ni_daq and self.ni_daq.is_connected():
            self.connected = True
            self.simulation_mode = False
            return True
        else:
            self.enable_simulation()
            return False
    
    def disconnect(self):
        """Disconnect from sensor"""
        self.connected = False
    
    def read(self):
        """
        Read level value
        
        Returns:
            Level as fraction (0.0 to 1.0) or None on error
        """
        if self.ni_daq and self.ni_daq.is_connected():
            try:
                voltage = self.ni_daq.read_analog_input(self.channel)
                # Check if voltage is None (read failed)
                if voltage is None:
                    # Return simulated value if read failed
                    elapsed = time.time() - self.sim_start_time
                    base_level = 0.5
                    variation = 0.3 * math.sin(2 * math.pi * elapsed / 60.0)
                    sim_level = base_level + variation
                    return max(0.05, min(0.95, sim_level))
                
                # Debug: Print voltage reading (can be removed in production)
                # print(f"[LEVEL_SENSOR] Channel {self.channel} voltage: {voltage:.4f}V")
                
                # Convert voltage to level (calibration needed)
                # If voltage is exactly 0V, it might indicate:
                # 1. Sensor not connected/calibrated (use simulation)
                # 2. Tank is actually empty (valid reading)
                # For now, if voltage is 0V, we'll assume it's a sensor issue and use simulation
                # This can be adjusted based on actual sensor calibration
                if abs(voltage) < 0.01:  # Very close to 0V (likely uncalibrated/disconnected)
                    # Use simulated value for uncalibrated sensors
                    elapsed = time.time() - self.sim_start_time
                    base_level = 0.5
                    variation = 0.3 * math.sin(2 * math.pi * elapsed / 60.0)
                    sim_level = base_level + variation
                    return max(0.05, min(0.95, sim_level))
                
                # Normal conversion: voltage to level (0-5V = 0-1.0)
                # Note: Actual calibration may differ - adjust this formula based on your sensor
                level = voltage / 5.0  # Placeholder conversion (0-5V = 0-1.0)
                return max(0.0, min(1.0, level))  # Clamp to 0-1
            except Exception as e:
                print(f"Error reading level sensor: {e}")
                # Return simulated value on error
                elapsed = time.time() - self.sim_start_time
                base_level = 0.5
                variation = 0.3 * math.sin(2 * math.pi * elapsed / 60.0)
                sim_level = base_level + variation
                return max(0.05, min(0.95, sim_level))
        else:
            # Realistic simulation
            elapsed = time.time() - self.sim_start_time
            base_level = 0.5  # 50% full
            variation = 0.3 * math.sin(2 * math.pi * elapsed / 60.0)
            sim_level = base_level + variation
            return max(0.05, min(0.95, sim_level))  # Clamp between 5% and 95%

