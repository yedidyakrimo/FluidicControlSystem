"""
Base experiment class
"""

from abc import ABC, abstractmethod


class BaseExperiment(ABC):
    """Base class for all experiment types"""
    
    def __init__(self, hardware_controller, data_handler):
        self.hw_controller = hardware_controller
        self.data_handler = data_handler
        self.is_running = False
    
    @abstractmethod
    def run(self, *args, **kwargs):
        """Run the experiment - must be implemented in all subclasses"""
        pass
    
    def stop(self):
        """Stop the experiment"""
        self.is_running = False
        if self.hw_controller:
            self.hw_controller.stop_pump()
        print("Experiment stopped.")
    
    def finish(self):
        """Finish the experiment - complete current step then stop"""
        self.is_running = False
        print("Experiment finishing - completing current step...")
        if self.hw_controller:
            self.hw_controller.stop_pump()
        print("Experiment finished.")

