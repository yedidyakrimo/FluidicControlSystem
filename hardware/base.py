"""
Base class for all hardware components
"""


class HardwareBase:
    """
    Base class for all hardware components.
    Provides common interface and simulation mode support.
    """
    
    def __init__(self):
        """Initialize hardware base"""
        self.connected = False
        self.simulation_mode = False
        self.device_name = None
    
    def connect(self):
        """
        Connect to hardware device
        Must be implemented by subclasses
        """
        raise NotImplementedError("Subclass must implement connect()")
    
    def disconnect(self):
        """
        Disconnect from hardware device
        Must be implemented by subclasses
        """
        raise NotImplementedError("Subclass must implement disconnect()")
    
    def is_connected(self):
        """Check if device is connected"""
        return self.connected
    
    def enable_simulation(self):
        """Enable simulation mode"""
        self.simulation_mode = True
        self.connected = False
        print(f"{self.device_name or 'Device'} running in simulation mode")
    
    def disable_simulation(self):
        """Disable simulation mode"""
        self.simulation_mode = False

