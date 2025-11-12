"""
Time-dependent experiment type
"""

import time
from experiments.base_experiment import BaseExperiment
from experiments.safety_checks import SafetyChecker


class TimeDependentExperiment(BaseExperiment):
    """ניסוי תלוי זמן - ריצה לפי תוכנית עם שלבים"""
    
    def __init__(self, hardware_controller, data_handler):
        super().__init__(hardware_controller, data_handler)
        self.safety_checker = SafetyChecker(hardware_controller)
    
    def run(self, experiment_program):
        """
        הרצת ניסוי תלוי זמן
        experiment_program: רשימת שלבים, כל שלב הוא dict עם:
            - duration: משך זמן (שניות)
            - flow_rate: קצב זרימה (ml/min)
            - valve_setting: הגדרות שסתומים (dict עם valve1, valve2)
            - temp: טמפרטורה (אופציונלי)
        """
        self.is_running = True
        print("Starting time-dependent experiment...")
        
        # יצירת קובץ נתונים חדש
        self.data_handler.create_new_file()
        
        # ביצוע כל שלב בתוכנית
        for step in experiment_program:
            if not self.is_running:
                break  # יציאה אם הניסוי הופסק
            
            duration = step.get('duration')
            flow_rate = step.get('flow_rate')
            valve_setting = step.get('valve_setting', {})
            temperature = step.get('temp', None)
            
            print(f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min")
            
            # הגדרת קצב זרימה ושסתומים
            self.hw_controller.set_pump_flow_rate(flow_rate)
            if valve_setting:
                self.hw_controller.set_valves(
                    valve_setting.get('valve1', 'main'),
                    valve_setting.get('valve2', 'main')
                )
            
            # הגדרת טמפרטורה אם נדרש
            if temperature is not None:
                # כאן ניתן להוסיף לוגיקה להגדרת טמפרטורה
                pass
            
            start_time = time.time()
            
            # לולאה למשך השלב
            while time.time() - start_time < duration and self.is_running:
                # בדיקות בטיחות
                if not self.safety_checker.perform_all_checks():
                    self.stop()
                    break
                
                # קריאת נתונים מכל החיישנים
                pump_data = self.hw_controller.read_pump_data()
                pressure_data = self.hw_controller.read_pressure_sensor()
                temp_data = self.hw_controller.read_temperature_sensor()
                level_data = self.hw_controller.read_level_sensor()
                
                # איסוף כל הנתונים
                data_point = {
                    "time": time.time(),
                    "flow_setpoint": flow_rate,
                    "pump_flow_read": pump_data.get('flow', 0),
                    "pressure_read": pressure_data,
                    "temp_read": temp_data,
                    "level_read": level_data
                }
                
                # שמירת נתונים לקובץ
                self.data_handler.append_data(data_point)
                
                # המתנה לסקירה הבאה
                time.sleep(1)
        
        self.stop()
        print("Time-dependent experiment finished.")

