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
        # Rate limiting for error messages (print only every 10 seconds)
        self.last_error_print_time = {}
        
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
    
    def _should_print_error(self, error_key, interval_seconds=10):
        """
        Check if enough time has passed since last error print
        
        Args:
            error_key: Unique key for this error type
            interval_seconds: Minimum seconds between prints (default 10)
        
        Returns:
            True if should print, False otherwise
        """
        current_time = time.time()
        if error_key not in self.last_error_print_time:
            self.last_error_print_time[error_key] = current_time
            return True
        
        if current_time - self.last_error_print_time[error_key] >= interval_seconds:
            self.last_error_print_time[error_key] = current_time
            return True
        
        return False
    
    def read(self):
        """
        Read temperature value from 4-20mA temperature transmitter
        
        Hardware:
        - Sensor Range: 0°C to 150°C
        - Current Output: 4mA (at 0°C) to 20mA (at 150°C)
        - Shunt Resistor: 556 Ohms
        - Input: Voltage across shunt resistor
        
        Returns:
            Temperature in Celsius, or None if sensor disconnected
        """
        if self.ni_daq and self.ni_daq.is_connected():
            try:
                voltage = self.ni_daq.read_analog_input(self.channel)
                # Check if voltage is None (read failed)
                if voltage is None:
                    if self._should_print_error("voltage_none"):
                        print("Warning: Temperature sensor read failed - voltage is None")
                    return None
                
                # Convert voltage to temperature using 4-20mA calibration
                temperature = self.calculate_temperature_from_voltage(voltage)
                
                if temperature is None:
                    # Sensor disconnected - return None instead of simulated value
                    return None
                
                return temperature
            except Exception as e:
                if self._should_print_error("read_exception"):
                    print(f"Error reading temperature sensor: {e}")
                return None
        else:
            # Simulation mode - return realistic value
            elapsed = time.time() - self.sim_start_time
            base_temp = 25.0  # Room temperature
            variation = 5.0 * math.sin(2 * math.pi * elapsed / 45.0)
            sim_temp = base_temp + variation
            return max(20.0, min(50.0, sim_temp))  # Clamp between 20°C and 50°C
    
    def calculate_temperature_from_voltage(self, voltage_measured):
        """
        Calculate temperature from voltage measured across 556 Ohm shunt resistor
        
        Args:
            voltage_measured: Voltage in Volts (measured across 556 Ohm shunt)
        
        Returns:
            Temperature in Celsius, or None if sensor disconnected
        """
        # Constants
        SHUNT_RESISTANCE = 556.0  # Ohms
        MIN_CURRENT_MA = 4.0  # mA at 0°C
        MAX_CURRENT_MA = 20.0  # mA at 150°C
        MIN_TEMP = 0.0  # °C
        MAX_TEMP = 150.0  # °C
        DISCONNECT_THRESHOLD_MA = 3.5  # mA - below this indicates disconnected sensor
        
        try:
            # Step 1: Convert Voltage to Current (mA)
            # Formula: current_mA = (voltage / 556.0) * 1000.0
            current_mA = (voltage_measured / 556.0) * 1000.0
            
            # Step 2: Error Handling - Check for disconnected sensor
            if current_mA < DISCONNECT_THRESHOLD_MA:
                if self._should_print_error("sensor_disconnected"):
                    print(f"Warning: Temperature sensor appears disconnected. Current: {current_mA:.3f}mA (expected >= 4mA)")
                return None
            
            # Step 3: Calculate Temperature (°C)
            # Formula: temp_c = (current_mA - 4.0) * (150.0 / 16.0)
            # Range: 4mA -> 0°C, 20mA -> 150°C
            temp_c = (current_mA - 4.0) * (150.0 / 16.0)
            
            # Clamp temperature to valid range (0-150°C)
            temperature = max(0.0, min(150.0, temp_c))
            
            return temperature
            
        except (ZeroDivisionError, ValueError, TypeError) as e:
            if self._should_print_error("calc_exception"):
                print(f"Error calculating temperature from voltage: {e}")
            return None

