"""
SCPI commands for Keithley 2450 SMU
All SCPI commands are organized here for easy maintenance
"""


class SCPICommands:
    """
    Collection of SCPI commands for Keithley 2450 SMU
    All commands are static methods for easy access
    """
    
    # --- Identification and Reset ---
    @staticmethod
    def identify():
        """Query device identification"""
        return "*IDN?"
    
    @staticmethod
    def reset():
        """Reset device to default state"""
        return "*RST"
    
    # --- Source Configuration ---
    @staticmethod
    def set_source_voltage():
        """Set source function to voltage"""
        return "SOUR:FUNC VOLT"
    
    @staticmethod
    def set_source_current():
        """Set source function to current"""
        return "SOUR:FUNC CURR"
    
    @staticmethod
    def set_voltage_range(voltage_range):
        """Set voltage range"""
        return f"SOUR:VOLT:RANG {voltage_range}"
    
    @staticmethod
    def set_voltage_range_auto():
        """Enable auto-range for voltage source"""
        return "SOUR:VOLT:RANG:AUTO ON"
    
    @staticmethod
    def set_current_limit(current_limit):
        """Set current limit (compliance)"""
        return f"SOUR:VOLT:ILIM {current_limit}"
    
    @staticmethod
    def set_voltage(voltage):
        """Set output voltage"""
        return f"SOUR:VOLT {voltage}"
    
    @staticmethod
    def query_voltage():
        """Query current voltage setting"""
        return "SOUR:VOLT?"
    
    @staticmethod
    def set_current_source_range(current_range):
        """Set current source range"""
        return f"SOUR:CURR:RANG {current_range}"
    
    @staticmethod
    def set_current_source_range_auto():
        """Enable auto-range for current source"""
        return "SOUR:CURR:RANG:AUTO ON"
    
    @staticmethod
    def set_current(current):
        """Set output current"""
        return f"SOUR:CURR {current}"
    
    @staticmethod
    def query_current():
        """Query current current setting"""
        return "SOUR:CURR?"
    
    @staticmethod
    def set_voltage_limit(voltage_limit):
        """Set voltage limit (compliance) for current source mode"""
        return f"SOUR:CURR:VLIM {voltage_limit}"
    
    # --- Sense (Measurement) Configuration ---
    @staticmethod
    def set_sense_current():
        """Set measurement function to current"""
        return 'SENS:FUNC "CURR"'
    
    @staticmethod
    def set_sense_voltage():
        """Set measurement function to voltage"""
        return 'SENS:FUNC "VOLT"'
    
    @staticmethod
    def set_sense_voltage_and_current():
        """Set measurement functions to both voltage and current"""
        return 'SENS:FUNC "VOLT","CURR"'
    
    @staticmethod
    def set_current_range(current_range):
        """Set current measurement range"""
        return f"SENS:CURR:RANG {current_range}"
    
    @staticmethod
    def set_current_measurement_range_auto():
        """Enable auto-range for current measurement"""
        return "SENS:CURR:RANG:AUTO ON"
    
    @staticmethod
    def set_voltage_measurement_range(voltage_range):
        """Set voltage measurement range"""
        return f"SENS:VOLT:RANG {voltage_range}"
    
    @staticmethod
    def set_voltage_measurement_range_auto():
        """Enable auto-range for voltage measurement"""
        return "SENS:VOLT:RANG:AUTO ON"
    
    @staticmethod
    def set_nplc(nplc=1):
        """Set Number of Power Line Cycles for measurement"""
        return f"SENS:CURR:NPLC {nplc}"
    
    @staticmethod
    def set_voltage_nplc(nplc=1):
        """Set Number of Power Line Cycles for voltage measurement"""
        return f"SENS:VOLT:NPLC {nplc}"
    
    @staticmethod
    def set_aperture_time(time_seconds):
        """Set aperture time for measurement"""
        return f"SENS:CURR:APER {time_seconds}"
    
    # --- Output Control ---
    @staticmethod
    def output_on():
        """Turn output on"""
        return "OUTP ON"
    
    @staticmethod
    def output_off():
        """Turn output off"""
        return "OUTP OFF"
    
    @staticmethod
    def query_output_state():
        """Query output state (ON/OFF)"""
        return "OUTP?"
    
    # --- Measurement Commands ---
    @staticmethod
    def measure_current():
        """Measure current (performs measurement automatically)"""
        return "MEAS:CURR?"
    
    @staticmethod
    def measure_voltage():
        """Measure voltage (performs measurement automatically)"""
        return "MEAS:VOLT?"
    
    @staticmethod
    def read_data():
        """Read measurement data"""
        return "READ?"
    
    @staticmethod
    def initiate_continuous():
        """Enable continuous measurement mode (updates display in real-time)"""
        return ":INITiate:CONTinuous ON"
    
    # --- Display Control ---
    @staticmethod
    def set_display_home():
        """Switch display to HOME screen"""
        return ":DISPlay:SCReen HOME"
    
    # --- Status Queries ---
    @staticmethod
    def query_operation_status():
        """Query operation status condition"""
        return "STAT:OPER:COND?"
    
    # --- Data Format Configuration ---
    @staticmethod
    def set_format_elements():
        """Set data format elements for READ? command (V, I, R, S)"""
        return "FORM:ELEM VOLT,CURR,RES,STAT"

