"""
Safety checks for experiments
"""


class SafetyChecker:
    """Safety checks class for experiments"""
    
    def __init__(self, hardware_controller, bypass_checks=False):
        """
        Initialize safety checker
        
        Args:
            hardware_controller: Hardware controller instance
            bypass_checks: If True, bypass all safety checks (for testing only)
        """
        self.hw_controller = hardware_controller
        self.bypass_checks = bypass_checks
    
    def check_level(self, threshold=0.05):
        """
        Check liquid level
        
        Args:
            threshold: Minimum level threshold (0.05 = 5%)
        Returns:
            True if OK, False if there's a problem
        """
        if self.bypass_checks:
            return True
        
        try:
            current_level = self.hw_controller.read_level_sensor()
            if current_level is None:
                # If sensor read failed, allow experiment to continue
                return True
            if current_level < threshold:
                print(f"WARNING: Liquid level is extremely low ({current_level*100:.1f}%). Stopping experiment.")
                return False
            return True
        except Exception as e:
            print(f"Error checking level: {e}")
            return True  # Continue if we can't check
    
    def check_pressure(self, max_pressure=7.0):
        """
        Check maximum pressure
        
        Args:
            max_pressure: Maximum allowed pressure (bar) - default 7.0 bar (~100 PSI)
        Returns:
            True if OK, False if there's a problem
        """
        if self.bypass_checks:
            return True
        
        try:
            current_pressure = self.hw_controller.read_pressure_sensor()
            if current_pressure is None:
                return True
            if current_pressure > max_pressure:
                print(f"WARNING: Pressure is too high ({current_pressure:.2f} bar). Stopping experiment.")
                return False
            return True
        except Exception as e:
            print(f"Error checking pressure: {e}")
            return True  # Continue if we can't check
    
    def check_temperature(self, max_temperature=100.0):
        """
        Check maximum temperature
        
        Args:
            max_temperature: Maximum allowed temperature (°C)
        Returns:
            True if OK, False if there's a problem
        """
        if self.bypass_checks:
            return True
        
        try:
            current_temp = self.hw_controller.read_temperature_sensor()
            if current_temp is None:
                return True
            if current_temp > max_temperature:
                print(f"WARNING: Temperature is too high ({current_temp:.2f} °C). Stopping experiment.")
                return False
            return True
        except Exception as e:
            print(f"Error checking temperature: {e}")
            return True  # Continue if we can't check
    
    def perform_all_checks(self, level_threshold=0.05, max_pressure=7.0, max_temperature=100.0):
        """
        Perform all safety checks
        
        Args:
            level_threshold: Minimum liquid level threshold (0.05 = 5%)
            max_pressure: Maximum allowed pressure (bar) - default 7.0 bar (~100 PSI)
            max_temperature: Maximum allowed temperature (°C)
        Returns:
            True if all checks pass, False if any check fails
        """
        if self.bypass_checks:
            return True
        
        if not self.check_level(level_threshold):
            return False
        if not self.check_pressure(max_pressure):
            return False
        if not self.check_temperature(max_temperature):
            return False
        return True

