"""
NI USB-6002 DAQ control module
"""

import nidaqmx
from hardware.base import HardwareBase


class NIUSB6002(HardwareBase):
    """
    National Instruments USB-6002 DAQ controller
    """
    
    def __init__(self, device_name='Dev1'):
        """
        Initialize NI USB-6002
        
        Args:
            device_name: NI device name (e.g., 'Dev1')
        """
        super().__init__()
        self.device_name = f"NI USB-6002 ({device_name})"
        self.ni_device_name = device_name
        self.ni_task = None
        
        self.connect()
    
    def connect(self):
        """Connect to NI device"""
        try:
            self.ni_task = nidaqmx.Task()
            # Add an analog input channel for pressure sensor
            self.ni_task.ai_channels.add_ai_voltage_chan(f"{self.ni_device_name}/ai0")
            print(f"Connected to NI device: {self.ni_device_name}")
            self.connected = True
            self.simulation_mode = False
            return True
        except (nidaqmx.errors.DaqError, nidaqmx.errors.DaqNotFoundError, Exception) as e:
            print(f"Error connecting to NI device: {e}")
            print("Running in simulation mode for NI sensors.")
            self.ni_task = None
            self.enable_simulation()
            return False
    
    def disconnect(self):
        """Disconnect from NI device"""
        if self.ni_task:
            try:
                self.ni_task.close()
            except:
                pass
            self.ni_task = None
        self.connected = False
    
    def read_analog_input(self, channel):
        """
        Read analog input from specified channel
        
        Args:
            channel: Channel name (e.g., 'ai0', 'ai1')
            
        Returns:
            Voltage value or None on error
        """
        if self.ni_task:
            try:
                # For now, using the default channel configured in __init__
                # In full implementation, would configure channel dynamically
                voltage = self.ni_task.read()
                return voltage
            except nidaqmx.errors.DaqError as e:
                print(f"Error reading from NI device: {e}")
                return None
        else:
            return None
    
    def write_digital_output(self, channel, value):
        """
        Write digital output
        
        Args:
            channel: Digital output channel
            value: Output value (True/False or 0/1)
            
        Returns:
            True if successful, False otherwise
        """
        if self.ni_task:
            try:
                # Add digital output channel
                do_channel = f"{self.ni_device_name}/{channel}"
                self.ni_task.do_channels.add_do_chan(do_channel)
                self.ni_task.write([value])
                return True
            except nidaqmx.errors.DaqError as e:
                print(f"Error writing digital output: {e}")
                return False
        else:
            return False
    
    def write_analog_output(self, channel, voltage):
        """
        Write analog output
        
        Args:
            channel: Analog output channel (e.g., 'ao0')
            voltage: Voltage value (0-5V)
            
        Returns:
            True if successful, False otherwise
        """
        if self.ni_task:
            try:
                ao_channel = f"{self.ni_device_name}/{channel}"
                self.ni_task.ao_channels.add_ao_voltage_chan(ao_channel)
                self.ni_task.write(voltage)
                return True
            except nidaqmx.errors.DaqError as e:
                print(f"Error writing analog output: {e}")
                return False
        else:
            return False

