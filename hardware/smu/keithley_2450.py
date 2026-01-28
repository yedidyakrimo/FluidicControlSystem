"""
Keithley 2450 SMU (Source Measure Unit) control module
"""

import time
from hardware.base import HardwareBase
from hardware.smu.scpi_commands import SCPICommands
from utils.logger_config import get_logger

logger = get_logger(__name__)

# Try to import pyvisa
PYVISA_AVAILABLE = False
VISA_BACKEND = None

try:
    import pyvisa
    PYVISA_AVAILABLE = True
    
    # Try to determine which VISA backend is available
    try:
        rm_ni = pyvisa.ResourceManager()
        VISA_BACKEND = '@ni'
        # Log at module level (before logger is available)
        import logging
        logging.getLogger('hardware.smu').info("Using NI-VISA backend (recommended for USB devices)")
        rm_ni.close()
    except:
        try:
            rm_py = pyvisa.ResourceManager('@py')
            VISA_BACKEND = '@py'
            import logging
            logging.getLogger('hardware.smu').info("Using pyvisa-py backend (limited USB support)")
            rm_py.close()
        except:
            VISA_BACKEND = None
            import logging
            logging.getLogger('hardware.smu').warning("VISA backend could not be initialized")
except ImportError:
    PYVISA_AVAILABLE = False
    import logging
    logging.getLogger('hardware.smu').warning("PyVISA not available. SMU will run in simulation mode.")


class Keithley2450(HardwareBase):
    """
    Keithley 2450 Source Measure Unit controller
    """
    
    def __init__(self, resource=None):
        """
        Initialize Keithley 2450 SMU
        
        Args:
            resource: VISA resource string (e.g., 'USB0::0x05E6::0x2450::04666218::INSTR')
                     If None, will attempt auto-detection
        """
        super().__init__()
        self.device_name = "Keithley 2450 SMU"
        self.resource = resource
        self.smu = None
        self.rm = None
        self.scpi = SCPICommands()
        
        if PYVISA_AVAILABLE:
            self._initialize_visa()
            if resource:
                self.connect_to_resource(resource)
            else:
                self.auto_detect()
        else:
            self.enable_simulation()
    
    def _initialize_visa(self):
        """Initialize VISA ResourceManager"""
        try:
            # Try default (NI-VISA) first
            try:
                self.rm = pyvisa.ResourceManager()
                logger.debug("Using default VISA backend (NI-VISA)")
            except Exception as e1:
                # Try explicit @ni
                try:
                    self.rm = pyvisa.ResourceManager('@ni')
                    logger.debug("Using NI-VISA backend (@ni)")
                except Exception as e2:
                    # Fallback to pyvisa-py
                    try:
                        self.rm = pyvisa.ResourceManager('@py')
                        logger.debug("Using pyvisa-py backend (limited USB support)")
                    except Exception as e3:
                        logger.error(f"Failed to initialize any VISA backend: Default={e1}, @ni={e2}, @py={e3}")
                        self.enable_simulation()
        except Exception as e:
            logger.error(f"Error initializing VISA ResourceManager: {e}")
            self.enable_simulation()
    
    def connect(self):
        """Connect to SMU (alias for auto_detect or connect_to_resource)"""
        if self.resource:
            return self.connect_to_resource(self.resource)
        else:
            return self.auto_detect()
    
    def connect_to_resource(self, resource):
        """
        Connect to specific VISA resource
        
        Args:
            resource: VISA resource string
            
        Returns:
            True if connected, False otherwise
        """
        if not self.rm:
            logger.warning("VISA ResourceManager not initialized")
            return False
        
        try:
            logger.debug(f"Attempting to connect to: {resource}...")
            self.smu = self.rm.open_resource(resource)
            # Set timeout to 5000ms (5 seconds) to prevent hanging
            self.smu.timeout = 5000
            logger.debug("Resource opened successfully")
            
            # Test connection
            idn = self.smu.query(self.scpi.identify())
            logger.info(f"Connected to Keithley 2450 SMU: {resource}")
            logger.debug(f"Device ID: {idn.strip()}")
            
            self.connected = True
            self.simulation_mode = False
            return True
        except Exception as e:
            logger.error(f"Error connecting to specified SMU resource {resource}: {e}")
            self.enable_simulation()
            return False
    
    def auto_detect(self):
        """
        Auto-detect Keithley 2450 SMU from available VISA resources
        
        Returns:
            True if found and connected, False otherwise
        """
        if not self.rm:
            logger.warning("VISA ResourceManager not initialized")
            self.enable_simulation()
            return False
        
        try:
            resources = self.rm.list_resources()
            logger.debug(f"Found {len(resources)} VISA resource(s)")
            
            for resource in resources:
                logger.debug(f"Checking resource: {resource}")
                try:
                    inst = self.rm.open_resource(resource)
                    # Set timeout to 2000ms (2 seconds) for device detection
                    inst.timeout = 2000
                    idn = inst.query(self.scpi.identify())
                    logger.debug(f"  IDN: {idn.strip()}")
                    
                    # Check if it's a Keithley 2450
                    if "2450" in idn.upper() or "KEITHLEY" in idn.upper():
                        logger.info(f"Found Keithley 2450 SMU at {resource}")
                        self.smu = inst
                        # Set timeout to 5000ms (5 seconds) for normal operations
                        self.smu.timeout = 5000
                        self.resource = resource
                        self.connected = True
                        self.simulation_mode = False
                        return True
                    else:
                        inst.close()
                except Exception as e:
                    logger.debug(f"Could not query {resource}: {e}")
                    continue
            
            logger.warning("No Keithley 2450 SMU found in available resources.")
            self.enable_simulation()
            return False
            
        except Exception as e:
            logger.error(f"Error during SMU auto-detection: {e}")
            self.enable_simulation()
            return False
    
    def disconnect(self):
        """Disconnect from SMU"""
        if self.smu:
            try:
                self.stop()
                self.smu.close()
            except:
                pass
            self.smu = None
        self.connected = False
    
    def list_resources(self):
        """
        List all available VISA resources
        
        Returns:
            List of resource strings
        """
        if not self.rm:
            return []
        
        try:
            resources = self.rm.list_resources()
            return list(resources)
        except Exception as e:
            logger.error(f"Error listing VISA resources: {e}")
            return []
    
    def get_info(self):
        """
        Get information about the connected SMU with active health check
        
        Performs an active "ping" by sending *IDN? command.
        If timeout or error occurs, closes connection and marks as disconnected.
        
        Returns:
            Dictionary with device information
        """
        if not self.smu:
            return {"connected": False, "info": "SMU not connected"}
        
        try:
            # Active Health Check: Send *IDN? command with timeout
            # This verifies the device is actually responsive, not just that the port is open
            idn = self.smu.query(self.scpi.identify())
            return {
                "connected": True,
                "idn": idn.strip(),
                "resource": self.smu.resource_name
            }
        except Exception as e:
            # Timeout or communication error - device is not responsive
            error_msg = str(e)
            logger.warning(f"SMU health check failed: {error_msg}")
            
            # Close the connection explicitly
            try:
                if self.smu:
                    self.smu.close()
            except:
                pass
            
            # Mark as disconnected
            self.smu = None
            self.connected = False
            
            return {
                "connected": False,
                "error": error_msg,
                "info": "Connection closed due to timeout/error"
            }
    
    def setup_for_iv_measurement(self, current_limit=0.1, voltage_range=None):
        """
        Setup SMU for I-V measurement (Source Voltage, Measure Current).
        
        Improvements:
        - Uses Auto-Range for both Source and Measure.
        - Forces display to HOME screen (Current shown big, Voltage small).
        
        Args:
            current_limit: Current limit (A)
            voltage_range: DEPRECATED - Auto-range is now used. Kept for backward compatibility.
            
        Returns:
            True if successful, False otherwise
        """
        if not self.smu:
            logger.warning("SMU not connected - operation skipped")
            return False
        
        try:
            # 1. Configure Source: Voltage
            logger.debug("Sending: SOUR:FUNC VOLT")
            self.smu.write(self.scpi.set_source_voltage())
            
            # Enable Auto Range for Source
            logger.debug("Sending: SOUR:VOLT:RANG:AUTO ON")
            self.smu.write(self.scpi.set_voltage_range_auto())
            
            # 2. Configure Measure: Current
            logger.debug('Sending: SENS:FUNC "CURR"')
            self.smu.write(self.scpi.set_sense_current())
            
            # Enable Auto Range for Measure
            logger.debug("Sending: SENS:CURR:RANG:AUTO ON")
            self.smu.write(self.scpi.set_current_measurement_range_auto())
            
            # 3. Set Compliance (Current Limit)
            logger.debug(f'Sending: SOUR:VOLT:ILIM {current_limit}')
            self.smu.write(self.scpi.set_current_limit(current_limit))
            
            # 4. Set Speed (NPLC 1 is standard for good speed/accuracy balance)
            logger.debug('Sending: SENS:CURR:NPLC 1')
            self.smu.write(self.scpi.set_nplc(1))
            
            # 5. Turn Output On
            logger.debug("Sending: OUTP ON")
            self.smu.write(self.scpi.output_on())
            
            # NOTE: Display command is NOT sent here - it will be sent in set_voltage()
            # after the bias value is set, so the device knows what the fixed value is
            # and can display correctly (Current large on top, Voltage small on bottom)
            
            logger.info("SMU Setup Complete: Source V, Measure I")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up SMU: {e}", exc_info=True)
            return False
    
    def setup_iv_sweep(self, start_v, end_v, step_v, current_limit=0.1):
        """
        Setup SMU for I-V sweep measurement (manual sweep mode)
        
        Args:
            start_v: Starting voltage (V)
            end_v: Ending voltage (V)
            step_v: Voltage step (V)
            current_limit: Current limit (A)
        """
        if not self.smu:
            logger.warning(f"SMU not connected. Simulating I-V setup: {start_v}V to {end_v}V, step {step_v}V")
            return
        
        try:
            # Reset SMU
            logger.debug("Sending: *RST")
            self.smu.write(self.scpi.reset())
            time.sleep(0.5)
            
            # Configure source function to voltage
            logger.debug("Sending: SOUR:FUNC VOLT")
            self.smu.write(self.scpi.set_source_voltage())
            
            # Set voltage range
            # Keithley 2450 has specific ranges: 0.2V, 2V, 20V, 200V
            # Select the appropriate range that covers the voltage sweep
            max_voltage = max(abs(start_v), abs(end_v))
            
            # Select the smallest range that covers the maximum voltage
            if max_voltage <= 0.2:
                voltage_range = 0.2
            elif max_voltage <= 2.0:
                voltage_range = 2.0
            elif max_voltage <= 20.0:
                voltage_range = 20.0
            else:
                voltage_range = 200.0
            
            logger.debug(f"Sending: SOUR:VOLT:RANG {voltage_range} (max voltage: {max_voltage}V)")
            self.smu.write(self.scpi.set_voltage_range(voltage_range))
            
            # Set current limit
            logger.debug(f"Sending: SOUR:VOLT:ILIM {current_limit}")
            self.smu.write(self.scpi.set_current_limit(current_limit))
            
            # Configure measurement function to current
            logger.debug('Sending: SENS:FUNC "CURR"')
            self.smu.write(self.scpi.set_sense_current())
            
            # Set current range
            logger.debug(f"Sending: SENS:CURR:RANG {current_limit}")
            self.smu.write(self.scpi.set_current_range(current_limit))
            
            # Set NPLC
            logger.debug("Sending: SENS:CURR:NPLC 1")
            self.smu.write(self.scpi.set_nplc(1))
            
            # Set aperture time
            logger.debug("Sending: SENS:CURR:APER 0.1")
            self.smu.write(self.scpi.set_aperture_time(0.1))
            
            logger.info(f"SMU configured for manual I-V sweep: {start_v}V to {end_v}V, step {step_v}V")
            logger.debug("Note: Using manual sweep (not built-in sweep mode) to avoid trigger model issues")
            
        except Exception as e:
            logger.error(f"Error configuring SMU: {e}", exc_info=True)
    
    def set_voltage(self, voltage):
        """
        Set SMU output voltage (bias value)
        
        Args:
            voltage: Voltage to set (V)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.smu:
            logger.warning("SMU not connected - cannot set voltage")
            return False
        
        try:
            # Set voltage value (bias)
            logger.debug(f"Sending: SOUR:VOLT {voltage}")
            self.smu.write(self.scpi.set_voltage(voltage))
            time.sleep(0.2)  # Wait for voltage to stabilize
            
            # Send display command AFTER setting bias value
            # This ensures the device knows what the fixed value (voltage) is
            # and what the measured value (current) is, so it can display correctly
            logger.debug("Sending: DISPlay:SCReen HOME (after setting voltage bias)")
            self.smu.write(self.scpi.set_display_home())
            time.sleep(0.2)  # Wait for display to update
            
            return True
        except Exception as e:
            logger.error(f"Error setting SMU voltage: {e}")
            return False
    
    def setup_for_current_source_measurement(self, voltage_limit=20.0, current_range=None):
        """
        Setup SMU for Current Source (Source Current, Measure Voltage).
        
        Improvements:
        - Uses Auto-Range for both Source and Measure.
        - Forces display to HOME screen (Voltage shown big, Current small).
        
        Args:
            voltage_limit: Voltage limit (compliance) (V)
            current_range: DEPRECATED - Auto-range is now used. Kept for backward compatibility.
            
        Returns:
            True if successful, False otherwise
        """
        if not self.smu:
            logger.warning("SMU not connected - operation skipped")
            return False
        
        try:
            # 0. Reset device to ensure clean state
            logger.debug("Sending: *RST")
            self.smu.write(self.scpi.reset())
            time.sleep(0.1)
            
            # 1. Configure Source: Current
            logger.debug("Sending: SOUR:FUNC CURR")
            self.smu.write(self.scpi.set_source_current())
            logger.debug("Sending: SOUR:CURR:RANG:AUTO ON")
            self.smu.write(self.scpi.set_current_source_range_auto())
            
            # 2. Configure Measure: Voltage
            logger.debug('Sending: SENS:FUNC "VOLT"')
            self.smu.write(self.scpi.set_sense_voltage())
            logger.debug("Sending: SENS:VOLT:RANG:AUTO ON")
            self.smu.write(self.scpi.set_voltage_measurement_range_auto())
            
            # 3. Set Compliance & Speed
            logger.debug(f"Sending: SOUR:CURR:VLIM {voltage_limit}")
            self.smu.write(self.scpi.set_voltage_limit(voltage_limit))
            logger.debug('Sending: SENS:VOLT:NPLC 1')
            self.smu.write(self.scpi.set_voltage_nplc(1))
            
            # 4. Turn Output On
            logger.debug("Sending: OUTP ON")
            self.smu.write(self.scpi.output_on())
            
            # NOTE: Display command is NOT sent here - it will be sent in set_current()
            # after the bias value is set, so the device knows what the fixed value is
            # and can display correctly (Voltage large on top, Current small on bottom)
            
            logger.info("SMU Setup Complete: Source I, Measure V")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up SMU: {e}", exc_info=True)
            return False
    
    def set_current(self, current):
        """
        Set SMU output current (bias value)
        
        Args:
            current: Current to set (A)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.smu:
            logger.warning("SMU not connected - cannot set current")
            return False
        
        try:
            # Set current value (bias)
            logger.debug(f"Sending: SOUR:CURR {current}")
            self.smu.write(self.scpi.set_current(current))
            time.sleep(0.2)  # Wait for current to stabilize
            
            # Send display command AFTER setting bias value
            # This ensures the device knows what the fixed value (current) is
            # and what the measured value (voltage) is, so it can display correctly
            logger.debug("Sending: DISPlay:SCReen HOME (after setting current bias)")
            self.smu.write(self.scpi.set_display_home())
            time.sleep(0.2)  # Wait for display to update
            
            return True
        except Exception as e:
            logger.error(f"Error setting SMU current: {e}")
            return False
    
    def measure(self, mode="voltage"):
        """
        Measure voltage and current from SMU.
        
        IMPORTANT (based on real 2450 behaviour):
        - READ? returns a SINGLE measured value, according to SENS:FUNC:
          * In voltage mode (Source Current / Measure Voltage) we use SENS:FUNC "VOLT",
            so READ? returns **voltage only**.
          * In current mode (Source Voltage / Measure Current) we use SENS:FUNC "CURR",
            so READ? returns **current only**.
        - The complementary (non-measured) value is taken from the programmed source:
          * Voltage mode:  voltage = READ? (measured), current = SOUR:CURR? (setpoint)
          * Current mode:  current = READ? (measured), voltage = SOUR:VOLT? (setpoint)
        
        Args:
            mode: "voltage" (Source Current / Measure Voltage - למדוד מתח)
                  OR "current" (Source Voltage / Measure Current - למדוד זרם)
        
        Returns:
            dict with keys:
                - 'voltage': float
                - 'current': float
            or None on error.
        """
        if not self.smu:
            return None
        
        try:
            data = {}
            
            if mode == "voltage":
                # Voltage mode: Source I, Measure V (למדוד מתח)
                # READ? returns voltage (because SENS:FUNC "VOLT")
                read_string = self.smu.query(self.scpi.read_data()).strip()
                try:
                    voltage = float(read_string)
                except ValueError as e:
                    logger.warning(f"Could not parse READ? voltage response: {read_string}, error: {e}")
                    return None
                
                # Current is the programmed source current (setpoint)
                try:
                    i_str = self.smu.query(self.scpi.query_current()).strip()
                    current = float(i_str)
                except Exception as e:
                    logger.warning(f"Could not read programmed current (SOUR:CURR?): {e}")
                    return None
                
                data["voltage"] = voltage
                data["current"] = current
            
            elif mode == "current":
                # Current mode: Source V, Measure I (למדוד זרם)
                # READ? returns current (because SENS:FUNC "CURR")
                read_string = self.smu.query(self.scpi.read_data()).strip()
                try:
                    current = float(read_string)
                except ValueError as e:
                    logger.warning(f"Could not parse READ? current response: {read_string}, error: {e}")
                    return None
                
                # Voltage is the programmed source voltage (setpoint)
                try:
                    v_str = self.smu.query(self.scpi.query_voltage()).strip()
                    voltage = float(v_str)
                except Exception as e:
                    logger.warning(f"Could not read programmed voltage (SOUR:VOLT?): {e}")
                    return None
                
                data["voltage"] = voltage
                data["current"] = current
            
            else:
                logger.warning(f"Unknown measure mode '{mode}'. Expected 'voltage' or 'current'.")
                return None
            
            # Refresh display to show updated measurement values in real-time
            try:
                self.smu.write(self.scpi.set_display_home())
            except Exception:
                # Ignore display refresh errors
                pass
            
            return data
        except Exception as e:
            logger.error(f"Error measuring SMU: {e}", exc_info=True)
            return None
    
    def read_data(self):
        """
        Read voltage and current from SMU
        
        Returns:
            Dictionary with voltage and current values
        """
        return self.measure()
    
    def get_output_state(self):
        """
        Get SMU output state (ON/OFF)
        
        Returns:
            True if output is ON, False otherwise
        """
        if not self.smu:
            return False
        
        try:
            state = self.smu.query(self.scpi.query_output_state())
            return "1" in state or "ON" in state.upper()
        except Exception as e:
            logger.warning(f"Error reading SMU output state: {e}")
            return False
    
    def stop(self):
        """Stop SMU operation"""
        if self.smu:
            try:
                self.smu.write(self.scpi.set_voltage(0))
                self.smu.write(self.scpi.output_off())
                logger.info("SMU stopped")
            except Exception as e:
                logger.error(f"Error stopping SMU: {e}")
        else:
            logger.debug("SMU not connected - simulating stop")

