"""
Experiment Manager - Main class for managing experiments
"""

from experiments.experiment_types.time_dependent import TimeDependentExperiment
from experiments.experiment_types.iv_experiment import IVExperiment
from experiments.safety_checks import SafetyChecker


class ExperimentManager:
    """
    Main experiment manager
    Handles all experiment types and provides a unified interface
    """
    
    def __init__(self, hardware_controller, data_handler):
        self.hw_controller = hardware_controller
        self.data_handler = data_handler
        self.is_running = False
        
        # Create instances of experiment types
        self.time_dependent_exp = TimeDependentExperiment(hardware_controller, data_handler)
        self.iv_exp = IVExperiment(hardware_controller, data_handler)
        
        # Safety checks (bypassed for now - sensors not yet installed)
        self.safety_checker = SafetyChecker(hardware_controller, bypass_checks=True)
        
        # Current experiment
        self.current_experiment = None
    
    def perform_safety_checks(self):
        """
        Perform safety checks
        Returns: True if everything is OK, False if there's a problem
        """
        return self.safety_checker.perform_all_checks()
    
    def stop_experiment(self):
        """Stop the current experiment"""
        self.is_running = False
        if self.current_experiment:
            self.current_experiment.is_running = False
            self.current_experiment.stop()
        self.hw_controller.stop_pump()
        print("Experiment stopped.")
    
    def finish_experiment(self):
        """Finish the experiment - complete current step then stop"""
        self.is_running = False
        if self.current_experiment:
            self.current_experiment.is_running = False
            self.current_experiment.finish()
        else:
            print("Experiment finishing - completing current step...")
            self.hw_controller.stop_pump()
        print("Experiment finished.")
    
    def run_time_dependent_experiment(self, experiment_program):
        """
        Run time-dependent experiment
        experiment_program: List of steps
        """
        self.is_running = True
        self.current_experiment = self.time_dependent_exp
        self.time_dependent_exp.is_running = True
        self.time_dependent_exp.run(experiment_program)
        self.is_running = False
        self.current_experiment = None
    
    def run_iv_experiment(self, start_v, end_v, step_v, delay=0.1):
        """
        Run I-V experiment
        start_v: Start voltage (V)
        end_v: End voltage (V)
        step_v: Step size (V)
        delay: Delay between measurements (seconds)
        """
        self.is_running = True
        self.current_experiment = self.iv_exp
        self.iv_exp.is_running = True
        self.iv_exp.run(start_v, end_v, step_v, delay)
        self.is_running = False
        self.current_experiment = None

