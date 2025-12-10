"""
Time-dependent experiment type
"""

import time
from experiments.base_experiment import BaseExperiment
from experiments.safety_checks import SafetyChecker


class TimeDependentExperiment(BaseExperiment):
    """Time-dependent experiment - runs according to a program with steps"""
    
    def __init__(self, hardware_controller, data_handler):
        super().__init__(hardware_controller, data_handler)
        # Safety checks bypassed for now - sensors not yet installed
        self.safety_checker = SafetyChecker(hardware_controller, bypass_checks=True)
    
    def run(self, experiment_program):
        """
        Run time-dependent experiment
        experiment_program: List of steps, each step is a dict with:
            - duration: Duration (seconds)
            - flow_rate: Flow rate (ml/min)
            - valve_setting: Valve settings (dict with valve1, valve2)
            - temp: Temperature (optional)
        """
        self.is_running = True
        print("Starting time-dependent experiment...")
        
        # Create new data file
        self.data_handler.create_new_file()
        
        # Execute each step in the program
        for step in experiment_program:
            if not self.is_running:
                break  # Exit if experiment was stopped
            
            duration = step.get('duration')
            flow_rate = step.get('flow_rate')
            valve_setting = step.get('valve_setting', {})
            temperature = step.get('temp', None)
            
            print(f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min")
            
            # Set flow rate and valves
            self.hw_controller.set_pump_flow_rate(flow_rate)
            if valve_setting:
                self.hw_controller.set_valves(
                    valve_setting.get('valve1', 'main'),
                    valve_setting.get('valve2', 'main')
                )
            
            # Set temperature if required
            if temperature is not None:
                # Temperature control logic can be added here
                pass
            
            start_time = time.time()
            
            # Loop for the duration of the step
            while time.time() - start_time < duration and self.is_running:
                # Safety checks
                if not self.safety_checker.perform_all_checks():
                    self.stop()
                    break
                
                # Read data from all sensors
                pump_data = self.hw_controller.read_pump_data()
                pressure_data = self.hw_controller.read_pressure_sensor()
                temp_data = self.hw_controller.read_temperature_sensor()
                level_data = self.hw_controller.read_level_sensor()
                
                # Collect all data
                data_point = {
                    "time": time.time(),
                    "flow_setpoint": flow_rate,
                    "pump_flow_read": pump_data.get('flow', 0),
                    "pressure_read": pressure_data if pressure_data is not None else "",  # FIXED: Handle None
                    "temp_read": temp_data if temp_data is not None else "",
                    "level_read": level_data if level_data is not None else ""
                }
                
                # Save data to file
                self.data_handler.append_data(data_point)
                
                # Wait for next scan
                time.sleep(1)
        
        self.stop()
        print("Time-dependent experiment finished.")

