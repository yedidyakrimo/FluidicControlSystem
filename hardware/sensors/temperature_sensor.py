"""
Temperature sensor control module
"""

import time
import math
from hardware.base import HardwareBase


class TemperatureSensor(HardwareBase):
    """
    Temperature sensor
    Connected through NI USB-6002
    """
    
    def __init__(self, ni_daq=None, channel='ai1'):
        """
        Initialize temperature sensor
        
        Args:
            ni_daq: NI DAQ device instance
            channel: Analog input channel
        """
        super().__init__()
        self.device_name = "Temperature Sensor"
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
        Read temperature value
        
        Returns:
            Temperature in Celsius
        """
        if self.ni_daq and self.ni_daq.is_connected():
            try:
                voltage = self.ni_daq.read_analog_input(self.channel)
                # Convert voltage to temperature (calibration needed)
                temperature = voltage * 20.0 + 20.0  # Placeholder conversion
                return temperature
            except Exception as e:
                print(f"Error reading temperature sensor: {e}")
                return None
        else:
            # Realistic simulation
            elapsed = time.time() - self.sim_start_time
            base_temp = 25.0  # Room temperature
            variation = 5.0 * math.sin(2 * math.pi * elapsed / 45.0)
            sim_temp = base_temp + variation
            return max(20.0, min(50.0, sim_temp))  # Clamp between 20°C and 50°C

