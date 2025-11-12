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
        Get information about the connected SMU
        
        Returns:
            Dictionary with device information
        """
        if not self.smu:
            return {"connected": False, "info": "SMU not connected"}
        
        try:
            idn = self.smu.query(self.scpi.identify())
            return {
                "connected": True,
                "idn": idn.strip(),
                "resource": self.smu.resource_name
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
    
    def setup_for_iv_measurement(self, current_limit=0.1):
        """
        Setup SMU for I-V measurement
        
        Args:
            current_limit: Current limit (A)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.smu:
            print("SMU not connected. Cannot setup SMU.")
            return False
        
        try:
            # Configure as voltage source
            print("Sending: SOUR:FUNC VOLT")
            self.smu.write(self.scpi.set_source_voltage())
            
            # Configure measurement function to current
            print('Sending: SENS:FUNC "CURR"')
            self.smu.write(self.scpi.set_sense_current())
            
            # Set current limit/compliance
            print(f'Sending: SOUR:VOLT:ILIM {current_limit}')
            self.smu.write(self.scpi.set_current_limit(current_limit))
            
            # Set NPLC
            print('Sending: SENS:CURR:NPLC 1')
            self.smu.write(self.scpi.set_nplc(1))
            
            # Set current range
            print(f'Sending: SENS:CURR:RANG {current_limit}')
            self.smu.write(self.scpi.set_current_range(current_limit))
            
            # Turn output on
            print("Sending: OUTP ON")
            self.smu.write(self.scpi.output_on())
            
            print(f"SMU configured for I-V measurement (current limit: {current_limit}A)")
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
            voltage_range = max(abs(start_v), abs(end_v))
            print(f"Sending: SOUR:VOLT:RANG {voltage_range}")
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
        Set SMU output voltage
        
        Args:
            voltage: Voltage to set (V)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.smu:
            print("SMU not connected. Cannot set voltage.")
            return False
        
        try:
            self.smu.write(self.scpi.set_voltage(voltage))
            return True
        except Exception as e:
            print(f"Error setting SMU voltage: {e}")
            return False
    
    def measure(self):
        """
        Measure voltage and current from SMU
        
        Returns:
            Dictionary with voltage and current, or None on error
        """
        if not self.smu:
            return None
        
        try:
            # MEAS:CURR? performs measurement automatically
            current_string = self.smu.query(self.scpi.measure_current())
            current = float(current_string)
            
            # Read voltage setting
            voltage_string = self.smu.query(self.scpi.query_voltage())
            voltage = float(voltage_string)
            
            return {"voltage": voltage, "current": current}
        except Exception as e:
            print(f"Error measuring SMU: {e}")
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

