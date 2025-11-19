"""
Hardware Controller - Main interface for all hardware components
This class provides a unified interface to all hardware devices
"""

from .pump.vapourtec_pump import VapourtecPump
from .smu.keithley_2450 import Keithley2450
from .ni_daq.mcusb_1408fs import MCusb1408FS
from .sensors.pressure_sensor import PressureSensor
from .sensors.temperature_sensor import TemperatureSensor
from .sensors.flow_sensor import FlowSensor
from .sensors.level_sensor import LevelSensor


class HardwareController:
    """
    Main hardware controller that manages all hardware components
    Provides backward compatibility with the old hardware_control.py interface
    """
    
    def __init__(self, pump_port='COM3', mc_board_num=0, smu_resource=None):
        """
        Initialize hardware controller with all components
        
        Args:
            pump_port: Serial port for pump
            mc_board_num: MCusb-1408FS-Plus board number (default 0)
            smu_resource: SMU VISA resource (None for auto-detect)
        """
        # Initialize pump
        self.pump = VapourtecPump(port=pump_port)
        
        # Initialize MCusb-1408FS-Plus DAQ (replacing NI USB-6002)
        self.ni_daq = MCusb1408FS(board_num=mc_board_num)
        
        # Initialize sensors (connected to NI DAQ)
        self.pressure_sensor = PressureSensor(ni_daq=self.ni_daq, channel='ai0')
        self.temperature_sensor = TemperatureSensor(ni_daq=self.ni_daq, channel='ai1')
        self.flow_sensor = FlowSensor(ni_daq=self.ni_daq, channel='ai2', pump_setpoint_flow=1.5)
        self.level_sensor = LevelSensor(ni_daq=self.ni_daq, channel='ai3')
        
        # Initialize SMU
        self.smu = Keithley2450(resource=smu_resource)
        
        # Store for backward compatibility
        self.ni_device_name = f"MCusb-1408FS-Plus (Board {mc_board_num})"
        # For backward compatibility, create a dummy ni_task attribute
        self.ni_task = None  # MCusb doesn't use ni_task like NI DAQ
    
    # --- Pump Control Functions (backward compatibility) ---
    def set_pump_flow_rate(self, flow_rate_ml_min):
        """Set pump flow rate"""
        result = self.pump.set_flow_rate(flow_rate_ml_min)
        # Update flow sensor setpoint for realistic simulation
        if hasattr(self.flow_sensor, 'update_pump_setpoint'):
            self.flow_sensor.update_pump_setpoint(flow_rate_ml_min)
        return result
    
    def read_pump_data(self):
        """Read pump data"""
        return self.pump.read_data()
    
    def stop_pump(self):
        """Stop pump"""
        self.pump.stop()
    
    # --- Sensor Read Functions (backward compatibility) ---
    def read_pressure_sensor(self):
        """Read pressure sensor"""
        return self.pressure_sensor.read()
    
    def read_temperature_sensor(self):
        """Read temperature sensor"""
        return self.temperature_sensor.read()
    
    def read_flow_sensor(self):
        """Read flow sensor"""
        return self.flow_sensor.read()
    
    def read_level_sensor(self):
        """Read level sensor"""
        return self.level_sensor.read()
    
    # --- DAQ Device Control Functions (backward compatibility) ---
    def set_valves(self, valve_1_state, valve_2_state):
        """
        Control 3/2 valves through MCusb-1408FS-Plus digital outputs
        """
        if self.ni_daq and self.ni_daq.is_connected():
            try:
                # Write valve states to digital outputs
                self.ni_daq.write_digital_output('port0/line0', valve_1_state)
                self.ni_daq.write_digital_output('port0/line1', valve_2_state)
                print(f"Valves set: Valve 1 (Main) = {valve_1_state}, Valve 2 (Rinsing) = {valve_2_state}")
            except Exception as e:
                print(f"Error controlling valves: {e}")
        else:
            print(f"Setting valves: Valve 1 (Main) = {valve_1_state}, Valve 2 (Rinsing) = {valve_2_state}")
            print("Running in simulation mode - valves not connected")
    
    def set_heating_plate_temp(self, temperature_celsius):
        """
        Control heating plate temperature through MCusb-1408FS-Plus
        """
        if self.ni_daq and self.ni_daq.is_connected():
            try:
                # Convert temperature to voltage (0-5V range)
                # Assuming 0V = 20°C, 5V = 100°C
                voltage = (temperature_celsius - 20.0) / 16.0  # 16°C per volt
                voltage = max(0.0, min(5.0, voltage))  # Clamp to 0-5V
                
                self.ni_daq.write_analog_output('ao0', voltage)
                print(f"Heating plate temperature set to {temperature_celsius}°C (Voltage: {voltage:.2f}V)")
            except Exception as e:
                print(f"Error controlling heating plate: {e}")
        else:
            print(f"Setting heating plate temperature to {temperature_celsius}°C")
            print("Running in simulation mode - heating plate not connected")
    
    # --- SMU Functions (backward compatibility) ---
    def auto_detect_smu(self):
        """Auto-detect SMU (returns SMU instance if found)"""
        if self.smu.auto_detect():
            return self.smu
        return None
    
    def list_visa_resources(self):
        """List all available VISA resources"""
        return self.smu.list_resources()
    
    def get_smu_info(self):
        """Get SMU information"""
        return self.smu.get_info()
    
    def setup_smu_for_iv_measurement(self, current_limit=0.1, voltage_range=None):
        """Setup SMU for I-V measurement"""
        return self.smu.setup_for_iv_measurement(current_limit, voltage_range)
    
    def set_smu_voltage(self, voltage, current_limit=0.1):
        """Set SMU voltage"""
        return self.smu.set_voltage(voltage)
    
    def measure_smu(self):
        """Measure voltage and current from SMU"""
        return self.smu.measure()
    
    def get_smu_output_state(self):
        """Get SMU output state"""
        return self.smu.get_output_state()
    
    def setup_smu_iv_sweep(self, start_v, end_v, step_v, current_limit=0.1):
        """Setup SMU for I-V sweep"""
        self.smu.setup_iv_sweep(start_v, end_v, step_v, current_limit)
    
    def read_smu_data(self):
        """Read SMU data"""
        return self.smu.read_data()
    
    def is_smu_sweep_complete(self):
        """Check if SMU sweep is complete"""
        # For manual sweep, always return True (sweep is controlled manually)
        return True
    
    def stop_smu(self):
        """Stop SMU"""
        self.smu.stop()
    
    def cleanup(self):
        """
        Cleanup all hardware connections
        Should be called when application is closing
        """
        print("Cleaning up hardware connections...")
        
        # Stop pump
        try:
            self.stop_pump()
            if hasattr(self.pump, 'disconnect'):
                self.pump.disconnect()
        except Exception as e:
            print(f"Error cleaning up pump: {e}")
        
        # Stop SMU
        try:
            self.stop_smu()
            if hasattr(self.smu, 'disconnect'):
                self.smu.disconnect()
        except Exception as e:
            print(f"Error cleaning up SMU: {e}")
        
        # Disconnect MCusb-1408FS-Plus DAQ
        try:
            if hasattr(self.ni_daq, 'disconnect'):
                self.ni_daq.disconnect()
        except Exception as e:
            print(f"Error cleaning up MCusb-1408FS-Plus DAQ: {e}")
        
        print("Hardware cleanup completed.")

