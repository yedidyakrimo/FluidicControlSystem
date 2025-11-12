"""
Safety checks for experiments
"""


class SafetyChecker:
    """מחלקה לבדיקות בטיחות במהלך ניסויים"""
    
    def __init__(self, hardware_controller):
        self.hw_controller = hardware_controller
    
    def check_level(self, threshold=0.05):
        """
        בדיקת רמת נוזל
        threshold: סף מינימלי (0.05 = 5%)
        Returns: True אם הכל בסדר, False אם יש בעיה
        """
        try:
            current_level = self.hw_controller.read_level_sensor()
            if current_level < threshold:
                print(f"WARNING: Liquid level is extremely low ({current_level*100:.1f}%). Stopping experiment.")
                return False
            return True
        except Exception as e:
            print(f"Error checking level: {e}")
            return True  # Continue if we can't check
    
    def check_pressure(self, max_pressure=100.0):
        """
        בדיקת לחץ מקסימלי
        max_pressure: לחץ מקסימלי מותר (PSI)
        Returns: True אם הכל בסדר, False אם יש בעיה
        """
        try:
            current_pressure = self.hw_controller.read_pressure_sensor()
            if current_pressure > max_pressure:
                print(f"WARNING: Pressure is too high ({current_pressure:.2f} PSI). Stopping experiment.")
                return False
            return True
        except Exception as e:
            print(f"Error checking pressure: {e}")
            return True  # Continue if we can't check
    
    def check_temperature(self, max_temperature=100.0):
        """
        בדיקת טמפרטורה מקסימלית
        max_temperature: טמפרטורה מקסימלית מותרת (°C)
        Returns: True אם הכל בסדר, False אם יש בעיה
        """
        try:
            current_temp = self.hw_controller.read_temperature_sensor()
            if current_temp > max_temperature:
                print(f"WARNING: Temperature is too high ({current_temp:.2f} °C). Stopping experiment.")
                return False
            return True
        except Exception as e:
            print(f"Error checking temperature: {e}")
            return True  # Continue if we can't check
    
    def perform_all_checks(self, level_threshold=0.05, max_pressure=100.0, max_temperature=100.0):
        """
        ביצוע כל בדיקות הבטיחות
        Returns: True אם הכל בסדר, False אם יש בעיה
        """
        if not self.check_level(level_threshold):
            return False
        if not self.check_pressure(max_pressure):
            return False
        if not self.check_temperature(max_temperature):
            return False
        return True

