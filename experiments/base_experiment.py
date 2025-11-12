"""
Base experiment class
"""

from abc import ABC, abstractmethod


class BaseExperiment(ABC):
    """מחלקה בסיסית לכל סוגי הניסויים"""
    
    def __init__(self, hardware_controller, data_handler):
        self.hw_controller = hardware_controller
        self.data_handler = data_handler
        self.is_running = False
    
    @abstractmethod
    def run(self, *args, **kwargs):
        """הרצת הניסוי - חייב להיות מיושם בכל מחלקה יורשת"""
        pass
    
    def stop(self):
        """עצירת הניסוי"""
        self.is_running = False
        if self.hw_controller:
            self.hw_controller.stop_pump()
        print("Experiment stopped.")
    
    def finish(self):
        """סיום הניסוי - השלמת שלב נוכחי ואז עצירה"""
        self.is_running = False
        print("Experiment finishing - completing current step...")
        if self.hw_controller:
            self.hw_controller.stop_pump()
        print("Experiment finished.")

