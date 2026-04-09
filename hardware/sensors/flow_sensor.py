"""
Flow sensor (Biotech AB-40010) control module
"""

import time
from hardware.base import HardwareBase
from utils.logger_config import get_logger

logger = get_logger(__name__)


class FlowSensor(HardwareBase):
    """
    Biotech AB-40010 Flow sensor
    Connected through NI USB-6002
    """
    
    def __init__(self, ni_daq=None, channel='ai2', pump_setpoint_flow=0.2):
        """
        Initialize flow sensor
        
        Args:
            ni_daq: NI DAQ device instance
            channel: Analog input channel
            pump_setpoint_flow: Reference flow rate from pump (for simulation)
        """
        super().__init__()
        self.device_name = "Biotech AB-40010 Flow Sensor"
        self.ni_daq = ni_daq
        self.channel = channel
        self.pump_setpoint_flow = pump_setpoint_flow
        self.sim_start_time = time.time()
        self.flow_change_time = time.time()
        self.previous_setpoint_flow = pump_setpoint_flow
        
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
    
    def update_pump_setpoint(self, flow_rate):
        """Update pump setpoint flow (for realistic simulation)"""
        self.previous_setpoint_flow = self.pump_setpoint_flow
        self.pump_setpoint_flow = flow_rate
        self.flow_change_time = time.time()
    
    def read(self):
        """
        Read flow rate value
        
        Returns:
            Flow rate in L/min (or None on error)
        """
        if self.ni_daq and self.ni_daq.is_connected():
            try:
                voltage = self.ni_daq.read_analog_input(self.channel)
                # Check if voltage is None (read failed)
                if voltage is None:
                    return None
                # Convert voltage to flow rate (calibration factor needed)
                # Typical flow sensor: 0-5V = 0-10 L/min
                flow_rate = voltage * 2.0  # Placeholder conversion
                return flow_rate
            except Exception as e:
                logger.debug(f"Error reading flow sensor: {e}")
                return None
        else:
            return None

