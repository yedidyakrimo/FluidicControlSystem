"""
Experiment Manager - Main class for managing experiments
"""

from experiments.experiment_types.time_dependent import TimeDependentExperiment
from experiments.experiment_types.iv_experiment import IVExperiment
from experiments.safety_checks import SafetyChecker


class ExperimentManager:
    """
    מנהל ניסויים ראשי
    מטפל בכל סוגי הניסויים ומספק ממשק אחיד
    """
    
    def __init__(self, hardware_controller, data_handler):
        self.hw_controller = hardware_controller
        self.data_handler = data_handler
        self.is_running = False
        
        # יצירת מופעים של סוגי הניסויים
        self.time_dependent_exp = TimeDependentExperiment(hardware_controller, data_handler)
        self.iv_exp = IVExperiment(hardware_controller, data_handler)
        
        # בדיקות בטיחות
        self.safety_checker = SafetyChecker(hardware_controller)
        
        # ניסוי נוכחי
        self.current_experiment = None
    
    def perform_safety_checks(self):
        """
        ביצוע בדיקות בטיחות
        Returns: True אם הכל בסדר, False אם יש בעיה
        """
        return self.safety_checker.perform_all_checks()
    
    def stop_experiment(self):
        """עצירת הניסוי הנוכחי"""
        self.is_running = False
        if self.current_experiment:
            self.current_experiment.is_running = False
            self.current_experiment.stop()
        self.hw_controller.stop_pump()
        print("Experiment stopped.")
    
    def finish_experiment(self):
        """סיום הניסוי - השלמת שלב נוכחי ואז עצירה"""
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
        הרצת ניסוי תלוי זמן
        experiment_program: רשימת שלבים
        """
        self.is_running = True
        self.current_experiment = self.time_dependent_exp
        self.time_dependent_exp.is_running = True
        self.time_dependent_exp.run(experiment_program)
        self.is_running = False
        self.current_experiment = None
    
    def run_iv_experiment(self, start_v, end_v, step_v, delay=0.1):
        """
        הרצת ניסוי I-V
        start_v: מתח התחלתי (V)
        end_v: מתח סופי (V)
        step_v: גודל צעד (V)
        delay: השהיה בין מדידות (שניות)
        """
        self.is_running = True
        self.current_experiment = self.iv_exp
        self.iv_exp.is_running = True
        self.iv_exp.run(start_v, end_v, step_v, delay)
        self.is_running = False
        self.current_experiment = None

