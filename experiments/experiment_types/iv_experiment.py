"""
I-V experiment type
"""

import time
from experiments.base_experiment import BaseExperiment


class IVExperiment(BaseExperiment):
    """ניסוי I-V - מדידת מאפיין זרם-מתח"""
    
    def run(self, start_v, end_v, step_v, delay=0.1):
        """
        הרצת ניסוי I-V
        start_v: מתח התחלתי (V)
        end_v: מתח סופי (V)
        step_v: גודל צעד (V)
        delay: השהיה בין מדידות (שניות)
        """
        if not self.is_running:
            self.is_running = True
            print("Starting I-V measurement...")
        
        try:
            # יצירת קובץ נתונים חדש
            self.data_handler.create_new_file()
            
            # הגדרת SMU למדידת I-V (sweep ידני, לא שימוש ב-sweep מובנה)
            if self.hw_controller.smu:
                self.hw_controller.setup_smu_iv_sweep(start_v, end_v, step_v)
            
            # חישוב נקודות מתח ל-sweep ידני
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
            
            # ביצוע sweep ידני - הגדרת מתח ומדידה לכל נקודה
            for voltage in voltage_points:
                if not self.is_running:
                    break
                
                # הגדרת מתח
                if self.hw_controller.smu:
                    self.hw_controller.set_smu_voltage(voltage)
                    time.sleep(0.1)  # המתנה לייצוב מתח
                    # מדידה
                    smu_data = self.hw_controller.measure_smu()
                    if smu_data:
                        self.data_handler.append_data(smu_data)
                else:
                    # מצב סימולציה
                    smu_data = {"voltage": voltage, "current": voltage * 0.1}
                    self.data_handler.append_data(smu_data)
                
                time.sleep(delay)  # השהיה בין מדידות
        
        except Exception as e:
            print(f"Error in I-V experiment: {e}")
        finally:
            self.stop()
            print("I-V measurement finished.")

