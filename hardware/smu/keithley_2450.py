"""
Keithley 2450 SMU (Source Measure Unit) control module
"""

import time
from hardware.base import HardwareBase
from hardware.smu.scpi_commands import SCPICommands

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
        print("Using NI-VISA backend (recommended for USB devices)")
        rm_ni.close()
    except:
        try:
            rm_py = pyvisa.ResourceManager('@py')
            VISA_BACKEND = '@py'
            print("Using pyvisa-py backend (limited USB support)")
            rm_py.close()
        except:
            VISA_BACKEND = None
            print("Warning: VISA backend could not be initialized")
except ImportError:
    PYVISA_AVAILABLE = False
    print("PyVISA not available. SMU will run in simulation mode.")


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
                print("Using default VISA backend (NI-VISA)")
            except Exception as e1:
                # Try explicit @ni
                try:
                    self.rm = pyvisa.ResourceManager('@ni')
                    print("Using NI-VISA backend (@ni)")
                except Exception as e2:
                    # Fallback to pyvisa-py
                    try:
                        self.rm = pyvisa.ResourceManager('@py')
                        print("Using pyvisa-py backend (limited USB support)")
                    except Exception as e3:
                        print(f"Failed to initialize any VISA backend:")
                        print(f"  Default: {e1}")
                        print(f"  @ni: {e2}")
                        print(f"  @py: {e3}")
                        self.enable_simulation()
        except Exception as e:
            print(f"Error initializing VISA ResourceManager: {e}")
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
            print("VISA ResourceManager not initialized")
            return False
        
        try:
            print(f"Attempting to connect to: {resource}...")
            self.smu = self.rm.open_resource(resource)
            print(f"Resource opened successfully")
            
            # Test connection
            idn = self.smu.query(self.scpi.identify())
            print(f"\n✅ Connection Successful!")
            print(f"Connected to Keithley 2450 SMU: {resource}")
            print(f"Device ID: {idn.strip()}")
            
            self.connected = True
            self.simulation_mode = False
            return True
        except Exception as e:
            print(f"❌ Error connecting to specified SMU resource {resource}: {e}")
            import traceback
            traceback.print_exc()
            self.enable_simulation()
            return False
    
    def auto_detect(self):
        """
        Auto-detect Keithley 2450 SMU from available VISA resources
        
        Returns:
            True if found and connected, False otherwise
        """
        if not self.rm:
            print("VISA ResourceManager not initialized")
            self.enable_simulation()
            return False
        
        try:
            resources = self.rm.list_resources()
            print(f"Found {len(resources)} VISA resource(s):")
            
            for resource in resources:
                print(f"  - {resource}")
                try:
                    inst = self.rm.open_resource(resource)
                    idn = inst.query(self.scpi.identify())
                    print(f"    IDN: {idn.strip()}")
                    
                    # Check if it's a Keithley 2450
                    if "2450" in idn.upper() or "KEITHLEY" in idn.upper():
                        print(f"    ✓ Found Keithley 2450 SMU at {resource}")
                        self.smu = inst
                        self.resource = resource
                        self.connected = True
                        self.simulation_mode = False
                        return True
                    else:
                        inst.close()
                except Exception as e:
                    print(f"    Could not query {resource}: {e}")
                    continue
            
            print("No Keithley 2450 SMU found in available resources.")
            self.enable_simulation()
            return False
            
        except Exception as e:
            print(f"Error during SMU auto-detection: {e}")
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
            print(f"Error listing VISA resources: {e}")
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
            print(f"SMU health check failed: {error_msg}")
            
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
            print("SMU not connected.")
            return False
        
        try:
            # 1. Configure Source: Voltage
            print("Sending: SOUR:FUNC VOLT")
            self.smu.write(self.scpi.set_source_voltage())
            
            # Enable Auto Range for Source
            print("Sending: SOUR:VOLT:RANG:AUTO ON")
            self.smu.write(self.scpi.set_voltage_range_auto())
            
            # 2. Configure Measure: Current
            print('Sending: SENS:FUNC "CURR"')
            self.smu.write(self.scpi.set_sense_current())
            
            # Enable Auto Range for Measure
            print("Sending: SENS:CURR:RANG:AUTO ON")
            self.smu.write(self.scpi.set_current_measurement_range_auto())
            
            # 3. Set Compliance (Current Limit)
            print(f'Sending: SOUR:VOLT:ILIM {current_limit}')
            self.smu.write(self.scpi.set_current_limit(current_limit))
            
            # 4. Set Speed (NPLC 1 is standard for good speed/accuracy balance)
            print('Sending: SENS:CURR:NPLC 1')
            self.smu.write(self.scpi.set_nplc(1))
            
            # 4.5. Set Data Format: Ensure READ? returns voltage, current, resistance, status
            print('Sending: FORM:ELEM VOLT,CURR,RES,STAT')
            self.smu.write(self.scpi.set_format_elements())
            
            # 5. Turn Output On
            print("Sending: OUTP ON")
            self.smu.write(self.scpi.output_on())
            
            # NOTE: Display command is NOT sent here - it will be sent in set_voltage()
            # after the bias value is set, so the device knows what the fixed value is
            # and can display correctly (Current large on top, Voltage small on bottom)
            
            print("SMU Setup Complete: Source V, Measure I")
            return True
            
        except Exception as e:
            print(f"Error setting up SMU: {e}")
            import traceback
            traceback.print_exc()
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
            print(f"SMU not connected. Simulating I-V setup: {start_v}V to {end_v}V, step {step_v}V")
            return
        
        try:
            # Reset SMU
            print("Sending: *RST")
            self.smu.write(self.scpi.reset())
            time.sleep(0.5)
            
            # Configure source function to voltage
            print("Sending: SOUR:FUNC VOLT")
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
            
            print(f"Sending: SOUR:VOLT:RANG {voltage_range} (max voltage: {max_voltage}V)")
            self.smu.write(self.scpi.set_voltage_range(voltage_range))
            
            # Set current limit
            print(f"Sending: SOUR:VOLT:ILIM {current_limit}")
            self.smu.write(self.scpi.set_current_limit(current_limit))
            
            # Configure measurement function to current
            print('Sending: SENS:FUNC "CURR"')
            self.smu.write(self.scpi.set_sense_current())
            
            # Set current range
            print(f"Sending: SENS:CURR:RANG {current_limit}")
            self.smu.write(self.scpi.set_current_range(current_limit))
            
            # Set NPLC
            print("Sending: SENS:CURR:NPLC 1")
            self.smu.write(self.scpi.set_nplc(1))
            
            # Set aperture time
            print("Sending: SENS:CURR:APER 0.1")
            self.smu.write(self.scpi.set_aperture_time(0.1))
            
            print(f"SMU configured for manual I-V sweep: {start_v}V to {end_v}V, step {step_v}V")
            print("Note: Using manual sweep (not built-in sweep mode) to avoid trigger model issues")
            
        except Exception as e:
            print(f"Error configuring SMU: {e}")
            import traceback
            traceback.print_exc()
    
    def set_voltage(self, voltage):
        """
        Set SMU output voltage (bias value)
        
        Args:
            voltage: Voltage to set (V)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.smu:
            print("SMU not connected. Cannot set voltage.")
            return False
        
        try:
            # Set voltage value (bias)
            print(f"Sending: SOUR:VOLT {voltage}")
            self.smu.write(self.scpi.set_voltage(voltage))
            time.sleep(0.2)  # Wait for voltage to stabilize
            
            # Send display command AFTER setting bias value
            # This ensures the device knows what the fixed value (voltage) is
            # and what the measured value (current) is, so it can display correctly
            print("Sending: DISPlay:SCReen HOME (after setting voltage bias)")
            self.smu.write(self.scpi.set_display_home())
            time.sleep(0.2)  # Wait for display to update
            
            return True
        except Exception as e:
            print(f"Error setting SMU voltage: {e}")
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
            print("SMU not connected.")
            return False
        
        try:
            # 0. Reset device to ensure clean state
            print("Sending: *RST")
            self.smu.write(self.scpi.reset())
            time.sleep(0.1)
            
            # 1. Configure Source: Current
            print("Sending: SOUR:FUNC CURR")
            self.smu.write(self.scpi.set_source_current())
            print("Sending: SOUR:CURR:RANG:AUTO ON")
            self.smu.write(self.scpi.set_current_source_range_auto())
            
            # 2. Configure Measure: Voltage
            print('Sending: SENS:FUNC "VOLT"')
            self.smu.write(self.scpi.set_sense_voltage())
            print("Sending: SENS:VOLT:RANG:AUTO ON")
            self.smu.write(self.scpi.set_voltage_measurement_range_auto())
            
            # 3. Set Compliance & Speed
            print(f"Sending: SOUR:CURR:VLIM {voltage_limit}")
            self.smu.write(self.scpi.set_voltage_limit(voltage_limit))
            print('Sending: SENS:VOLT:NPLC 1')
            self.smu.write(self.scpi.set_voltage_nplc(1))
            
            # 3.5. Set Data Format: Ensure READ? returns voltage, current, resistance, status
            print('Sending: FORM:ELEM VOLT,CURR,RES,STAT')
            self.smu.write(self.scpi.set_format_elements())
            
            # 4. Turn Output On
            print("Sending: OUTP ON")
            self.smu.write(self.scpi.output_on())
            
            # NOTE: Display command is NOT sent here - it will be sent in set_current()
            # after the bias value is set, so the device knows what the fixed value is
            # and can display correctly (Voltage large on top, Current small on bottom)
            
            print("SMU Setup Complete: Source I, Measure V")
            return True
            
        except Exception as e:
            print(f"Error setting up SMU: {e}")
            import traceback
            traceback.print_exc()
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
            print("SMU not connected. Cannot set current.")
            return False
        
        try:
            # Set current value (bias)
            print(f"Sending: SOUR:CURR {current}")
            self.smu.write(self.scpi.set_current(current))
            time.sleep(0.2)  # Wait for current to stabilize
            
            # Send display command AFTER setting bias value
            # This ensures the device knows what the fixed value (current) is
            # and what the measured value (voltage) is, so it can display correctly
            print("Sending: DISPlay:SCReen HOME (after setting current bias)")
            self.smu.write(self.scpi.set_display_home())
            time.sleep(0.2)  # Wait for display to update
            
            return True
        except Exception as e:
            print(f"Error setting SMU current: {e}")
            return False
    
    def measure(self, mode="voltage"):
        """
        Measure voltage and current from SMU
        
        Uses READ? command to read all values simultaneously (more efficient)
        
        Args:
            mode: "voltage" (Source Voltage / Measure Current) 
                  OR "current" (Source Current / Measure Voltage)
        
        Returns:
            Dictionary with voltage and current, or None on error
        """
        if not self.smu:
            return None
        
        try:
            # Use READ? to get all measurements simultaneously
            # READ? returns: voltage,current,resistance,status (comma-separated) when FORM:ELEM VOLT,CURR,RES,STAT is set
            read_string = self.smu.query(self.scpi.read_data())
            
            # Parse the response (comma-separated values)
            values = read_string.strip().split(',')
            
            data = {}
            if len(values) >= 2:
                # First value is voltage, second is current
                data['voltage'] = float(values[0])
                data['current'] = float(values[1])
            else:
                # Fallback if parsing fails
                print(f"Warning: Could not parse READ? response: {read_string}")
                return None
            
            # Refresh display to show updated measurement values in real-time
            # This ensures the display updates as measurements are taken
            try:
                self.smu.write(self.scpi.set_display_home())
            except:
                pass  # Ignore errors, this is just to refresh display
            
            return data
        except Exception as e:
            print(f"Error measuring SMU: {e}")
            import traceback
            traceback.print_exc()
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
            print(f"Error reading SMU output state: {e}")
            return False
    
    def stop(self):
        """Stop SMU operation"""
        if self.smu:
            try:
                self.smu.write(self.scpi.set_voltage(0))
                self.smu.write(self.scpi.output_off())
                print("SMU stopped")
            except Exception as e:
                print(f"Error stopping SMU: {e}")
        else:
            print("SMU not connected. Simulating stop.")

