"""
Pressure sensor (Ashcroft ZL92) control module
"""

import time
import math
from hardware.base import HardwareBase


class PressureSensor(HardwareBase):
    """
    Ashcroft ZL92 Pressure sensor
    Connected through NI USB-6002
    """
    
    def __init__(self, ni_daq=None, channel='ai0'):
        """
        Initialize pressure sensor
        
        Args:
            ni_daq: NI DAQ device instance
            channel: Analog input channel
        """
        super().__init__()
        self.device_name = "Ashcroft ZL92 Pressure Sensor"
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
        Read pressure value
        
        Returns:
            Pressure value in psi (or None on error)
        """
        if self.ni_daq and self.ni_daq.is_connected():
            try:
                voltage = self.ni_daq.read_analog_input(self.channel)
                # Convert voltage to pressure using calibration factor
                # Pressure = (Voltage - Offset) * ScaleFactor
                pressure = voltage * 100  # Placeholder conversion
                return pressure
            except Exception as e:
                print(f"Error reading pressure sensor: {e}")
                return None
        else:
            # Realistic simulation
            elapsed = time.time() - self.sim_start_time
            base_pressure = 1.5
            variation = 0.8 * math.sin(2 * math.pi * elapsed / 20.0)
            sim_pressure = base_pressure + variation
            return max(0.1, sim_pressure)

