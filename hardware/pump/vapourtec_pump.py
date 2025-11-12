"""
Vapourtec SF-10 Pump control module
"""

import serial
import time
import math
from hardware.base import HardwareBase


class VapourtecPump(HardwareBase):
    """
    Vapourtec SF-10 Pump controller
    """
    
    def __init__(self, port='COM3', baudrate=9600, timeout=1):
        """
        Initialize Vapourtec pump
        
        Args:
            port: Serial port (e.g., 'COM3' on Windows)
            baudrate: Serial communication baudrate
            timeout: Serial timeout in seconds
        """
        super().__init__()
        self.device_name = "Vapourtec SF-10 Pump"
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.pump = None
        
        # Simulation state variables
        self.sim_start_time = time.time()
        self.pump_setpoint_flow = 1.5  # Default flow rate setpoint
        self.previous_setpoint_flow = 1.5
        self.flow_change_time = time.time()
        
        self.connect()
    
    def connect(self):
        """Connect to pump via serial port"""
        try:
            self.pump = serial.Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
            print(f"Connected to Vapourtec pump on port {self.port}")
            self.connected = True
            self.simulation_mode = False
            return True
        except serial.SerialException as e:
            print(f"Error connecting to Vapourtec pump: {e}")
            self.pump = None
            self.enable_simulation()
            return False
    
    def disconnect(self):
        """Disconnect from pump"""
        if self.pump:
            try:
                self.pump.close()
            except:
                pass
            self.pump = None
        self.connected = False
    
    def set_flow_rate(self, flow_rate_ml_min):
        """
        Set pump flow rate
        
        Args:
            flow_rate_ml_min: Flow rate in ml/min
            
        Returns:
            True if successful
        """
        if self.pump:
            # The Vapourtec pump uses a specific command set
            command = f"SET_FLOW {flow_rate_ml_min}\r\n"
            self.pump.write(command.encode())
            print(f"Set pump flow rate to {flow_rate_ml_min} ml/min.")
            return True
        else:
            # Simulation mode
            print("Pump is not connected. Simulating flow rate setting.")
            # Store previous setpoint for smooth transition
            self.previous_setpoint_flow = self.pump_setpoint_flow
            self.pump_setpoint_flow = flow_rate_ml_min
            self.flow_change_time = time.time()
            time.sleep(0.1)
            return True
    
    def read_data(self):
        """
        Read data from pump (flow, pressure, RPM)
        
        Returns:
            Dictionary with flow, pressure, and rpm
        """
        if self.pump:
            # Query pump status
            self.pump.write(b"GET_STATUS\r\n")
            response = self.pump.readline().decode().strip()
            print(f"Pump data received: {response}")
            # For now, return simulated data (would parse response in real implementation)
            return {"flow": 1.5, "pressure": 10.2, "rpm": 500}
        else:
            # Realistic simulation
            return self._simulate_data()
    
    def _simulate_data(self):
        """Generate realistic simulated pump data"""
        elapsed = time.time() - self.sim_start_time
        
        if not hasattr(self, 'flow_change_time'):
            self.flow_change_time = self.sim_start_time
        
        time_since_change = time.time() - self.flow_change_time
        
        # Small sinusoidal variation (±0.5%)
        flow_variation = 0.005 * self.pump_setpoint_flow * math.sin(2 * math.pi * elapsed / 25.0)
        
        # Smooth transition when flow changes
        if time_since_change < 3.0:
            transition_factor = 1.0 - math.exp(-time_since_change / 0.8)
            sim_flow = self.previous_setpoint_flow + (self.pump_setpoint_flow - self.previous_setpoint_flow) * transition_factor
        else:
            sim_flow = self.pump_setpoint_flow
        
        sim_flow = sim_flow + flow_variation
        
        # Pressure correlates with flow
        base_pressure = 8.0 + (self.pump_setpoint_flow * 2.0)
        pressure_variation = 1.5 * math.sin(2 * math.pi * elapsed / 12.0 + math.pi/4)
        sim_pressure = base_pressure + pressure_variation
        
        # RPM correlates with flow
        base_rpm = 300 + (self.pump_setpoint_flow * 100)
        rpm_variation = 20 * math.sin(2 * math.pi * elapsed / 18.0)
        sim_rpm = int(base_rpm + rpm_variation)
        
        return {"flow": sim_flow, "pressure": sim_pressure, "rpm": sim_rpm}
    
    def stop(self):
        """Stop the pump"""
        if self.pump:
            command = "STOP\r\n"
            self.pump.write(command.encode())
            print("Pump stopped.")
        else:
            print("Pump is not connected. Simulating stop.")

