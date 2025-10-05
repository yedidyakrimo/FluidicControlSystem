# experiment_logic.py

import time
from hardware_control import HardwareController  # Import the HardwareController class we just created
from data_handler import DataHandler  # We will create this class next to handle data saving


# This class manages the different types of experiments.
class ExperimentManager:
    # The constructor takes the hardware controller and data handler objects.
    def __init__(self, hardware_controller, data_handler):
        # Store the hardware controller and data handler as attributes of the class.
        self.hw_controller = hardware_controller
        self.data_handler = data_handler
        self.is_running = False  # A flag to check if an experiment is currently running.

    # This function is a placeholder for safety checks.
    # It will be called periodically during an experiment.
    def perform_safety_checks(self):
        # Read the level from the level sensor.
        current_level = self.hw_controller.read_level_sensor()
        # The document specifies that the experiment should stop if the liquid level is low.
        if current_level < 0.1:  # Assuming 0.1 is the low-level threshold (10% capacity).
            print("WARNING: Liquid level is low. Stopping experiment.")
            self.stop_experiment()  # Call the function to safely stop the experiment.
            # You can add more warnings here later, like for high pressure or temperature.
            return False  # Return False to indicate a safety issue was found.
        return True  # Return True if everything is OK.

    # This function safely stops the running experiment.
    def stop_experiment(self):
        self.is_running = False
        self.hw_controller.stop_pump()  # Stop the pump.
        # We can also add logic here to close the valves and turn off the heater.
        print("Experiment stopped.")

    # --- Time-Dependent Experiment Functions ---
    # This is the main function for running a time-dependent experiment.
    # It takes a list of experiment parameters as a 'program'.
    def run_time_dependent_experiment(self, experiment_program):
        self.is_running = True
        print("Starting time-dependent experiment...")

        # This will save the column headers for the data file.
        self.data_handler.create_new_file()

        # Iterate through each step in the experiment program.
        for step in experiment_program:
            if not self.is_running:
                break  # Exit the loop if the user has stopped the experiment.

            duration = step.get('duration')  # Get the duration for this step.
            flow_rate = step.get('flow_rate')  # Get the flow rate for this step.
            valve_setting = step.get('valve_setting')  # Get the valve setting.

            print(f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min")

            # Set the flow rate and valve settings from the hardware controller.
            self.hw_controller.set_pump_flow_rate(flow_rate)
            self.hw_controller.set_valves(valve_setting['valve1'], valve_setting['valve2'])

            start_time = time.time()  # Get the current time to track the step duration.

            # This loop runs for the duration of the current step.
            while time.time() - start_time < duration and self.is_running:
                # Perform the safety checks. If a safety issue is found, the inner loop will break.
                if not self.perform_safety_checks():
                    break

                # Read data from all sensors.
                pump_data = self.hw_controller.read_pump_data()
                pressure_data = self.hw_controller.read_pressure_sensor()
                temp_data = self.hw_controller.read_temperature_sensor()

                # Collect all the data into a single dictionary.
                data_point = {
                    "time": time.time(),
                    "flow_setpoint": flow_rate,
                    "pump_flow_read": pump_data['flow'],
                    "pressure_read": pressure_data,
                    "temp_read": temp_data
                }

                # Append the data to the data file in real-time.
                self.data_handler.append_data(data_point)

                # Wait for the next sampling period (e.g., 1 second).
                time.sleep(1)

        self.stop_experiment()  # Safely stop the experiment after the loop finishes.
        print("Experiment finished.")

    # --- I-V Experiment Functions ---
    # This function handles I-V or V-I measurements.
    # The experiment will be executed by the Keithley 2450 SMU.
    def run_iv_experiment(self, start_v, end_v, step_v):
        if not self.is_running:
            self.is_running = True
            print("Starting I-V measurement...")

            try:
                # The SMU will handle the sweeps, so we just need to set it up and read the results.
                self.hw_controller.setup_smu_iv_sweep(start_v, end_v, step_v)

                # A loop to read the SMU data as it becomes available.
                while self.is_running:
                    smu_data = self.hw_controller.read_smu_data()
                    if smu_data:
                        self.data_handler.append_data(smu_data)
                    # The loop would run until the SMU signals that the sweep is complete.
                    if self.hw_controller.is_smu_sweep_complete():
                        break
                    time.sleep(0.1)  # Small delay to prevent excessive CPU usage

            except Exception as e:
                print(f"Error in I-V experiment: {e}")
            finally:
                self.stop_experiment()
                print("I-V measurement finished.")