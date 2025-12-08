"""
I-V experiment type
"""

import time
from experiments.base_experiment import BaseExperiment


class IVExperiment(BaseExperiment):
    """I-V experiment - current-voltage characteristic measurement"""
    
    def run(self, start_v, end_v, step_v, delay=0.1):
        """
        Run I-V experiment
        start_v: Start voltage (V)
        end_v: End voltage (V)
        step_v: Step size (V)
        delay: Delay between measurements (seconds)
        """
        if not self.is_running:
            self.is_running = True
            print("Starting I-V measurement...")
        
        try:
            # Create new data file
            self.data_handler.create_new_file()
            
            # Setup SMU for I-V measurement (manual sweep, not using built-in sweep)
            if self.hw_controller.smu:
                self.hw_controller.setup_smu_iv_sweep(start_v, end_v, step_v)
            
            # Calculate voltage points for manual sweep
            if start_v <= end_v:
                voltage_points = []
                v = start_v
                while v <= end_v:
                    voltage_points.append(v)
                    v += step_v
            else:
                voltage_points = []
                v = start_v
                while v >= end_v:
                    voltage_points.append(v)
                    v -= step_v
            
            # Perform manual sweep - set voltage and measure for each point
            for voltage in voltage_points:
                if not self.is_running:
                    break
                
                # Set voltage
                if self.hw_controller.smu:
                    self.hw_controller.set_smu_voltage(voltage)
                    time.sleep(0.1)  # Wait for voltage stabilization
                    # Measure
                    smu_data = self.hw_controller.measure_smu()
                    if smu_data:
                        self.data_handler.append_data(smu_data)
                else:
                    # Simulation mode
                    smu_data = {"voltage": voltage, "current": voltage * 0.1}
                    self.data_handler.append_data(smu_data)
                
                time.sleep(delay)  # Delay between measurements
        
        except Exception as e:
            print(f"Error in I-V experiment: {e}")
        finally:
            self.stop()
            print("I-V measurement finished.")

