# hardware_control.py

import serial  # Library for serial communication (e.g., with the pump)
import nidaqmx  # Library for NI DAQ devices (e.g., NI USB-6002)
import time
import math  # For sin functions for realistic simulation

# Try to import pyvisa, if not available, SMU will run in simulation mode
PYVISA_AVAILABLE = False
VISA_BACKEND = None

try:
    import pyvisa  # Library for VISA communication (e.g., with Keithley SMU)  # noqa: F401
    PYVISA_AVAILABLE = True
    
    # Try to determine which VISA backend is available
    try:
        # Try NI-VISA first (best for USB devices like Keithley 2450)
        rm_ni = pyvisa.ResourceManager()
        VISA_BACKEND = '@ni'  # NI-VISA
        print("Using NI-VISA backend (recommended for USB devices)")
        rm_ni.close()
    except:
        try:
            # Fall back to pyvisa-py
            rm_py = pyvisa.ResourceManager('@py')
            VISA_BACKEND = '@py'  # pyvisa-py
            print("Using pyvisa-py backend (limited USB support)")
            rm_py.close()
        except:
            VISA_BACKEND = None
            print("Warning: VISA backend could not be initialized")
            
except ImportError:
    PYVISA_AVAILABLE = False
    print("PyVISA not available. SMU will run in simulation mode.")
    print("To use Keithley 2450, install: pip install pyvisa")
    print("For USB support, also install NI-VISA from: https://www.ni.com/en-il/support/downloads/drivers/download.ni-visa.html")


# This class will handle all communication with the physical hardware components.
class HardwareController:
    # The __init__ method is a constructor. It runs when you create an object of this class.
    def __init__(self, pump_port, ni_device_name, smu_resource=None):
        # We'll use a try-except block to handle potential serial connection errors.
        try:
            # Initialize connection to the Vapourtec pump.
            # The pump_port is the name of the serial port (e.g., 'COM3' on Windows or '/dev/ttyUSB0' on Linux).
            self.pump = serial.Serial(pump_port, baudrate=9600, timeout=1)
            print(f"Connected to Vapourtec pump on port {pump_port}")
        except serial.SerialException as e:
            # If connection fails, print an error message.
            print(f"Error connecting to Vapourtec pump: {e}")
            self.pump = None  # Set pump to None to indicate it's not connected.

        # Store ni_device_name for later use
        self.ni_device_name = ni_device_name
        
        # We'll use a try-except block to handle NI-DAQmx driver errors.
        try:
            # Initialize connection to the NI USB device.
            # The ni_device_name is the name of your NI device (e.g., 'Dev1').
            self.ni_task = nidaqmx.Task()
            # Add an analog input channel for a simulated pressure sensor.
            # This is where we would configure the specific channels for our sensors (pressure, temp, flow).
            self.ni_task.ai_channels.add_ai_voltage_chan(f"{ni_device_name}/ai0")
            print(f"Connected to NI device: {ni_device_name}")
        except (nidaqmx.errors.DaqError, nidaqmx.errors.DaqNotFoundError, Exception) as e:
            # If the NI-DAQmx driver is not found, print an error message.
            print(f"Error connecting to NI device: {e}")
            print("Running in simulation mode for NI sensors.")
            self.ni_task = None

        # Initialize Keithley 2450 SMU
        self.smu = None
        self.rm = None
        if PYVISA_AVAILABLE:
            try:
                # Try to initialize VISA ResourceManager
                # First try default (NI-VISA) which is best for USB devices
                try:
                    self.rm = pyvisa.ResourceManager()
                    print("Using default VISA backend (NI-VISA)")
                except Exception as e1:
                    # If default fails, try with explicit @ni
                    try:
                        self.rm = pyvisa.ResourceManager('@ni')
                        print("Using NI-VISA backend (@ni)")
                    except Exception as e2:
                        # Fallback to pyvisa-py (limited USB support)
                        try:
                            self.rm = pyvisa.ResourceManager('@py')
                            print("Using pyvisa-py backend (limited USB support)")
                        except Exception as e3:
                            print(f"Failed to initialize any VISA backend:")
                            print(f"  Default: {e1}")
                            print(f"  @ni: {e2}")
                            print(f"  @py: {e3}")
                            raise e3
                # If smu_resource is provided, try to connect to it
                if smu_resource:
                    try:
                        print(f"Attempting to connect to: {smu_resource}...")
                        self.smu = self.rm.open_resource(smu_resource)
                        print(f"Resource opened successfully")
                        # Test connection
                        idn = self.smu.query("*IDN?")
                        print(f"\n✅ Connection Successful!")
                        print(f"Connected to Keithley 2450 SMU: {smu_resource}")
                        print(f"Device ID: {idn.strip()}")
                        print(f"SMU object created: {self.smu is not None}")
                    except Exception as e:
                        print(f"❌ Error connecting to specified SMU resource {smu_resource}: {e}")
                        import traceback
                        traceback.print_exc()
                        print("Trying to auto-detect Keithley 2450...")
                        self.smu = self.auto_detect_smu()
                else:
                    # Try to auto-detect
                    print("No SMU resource specified. Trying to auto-detect Keithley 2450...")
                    self.smu = self.auto_detect_smu()
            except Exception as e:
                print(f"Error initializing VISA ResourceManager: {e}")
                print("Running in simulation mode for SMU.")
                self.smu = None
        else:
            print("PyVISA not available. Running in simulation mode for SMU.")
            self.smu = None
        
        # Simulation state variables for realistic data generation
        self.sim_start_time = time.time()
        self.pump_setpoint_flow = 1.5  # Default flow rate setpoint

    # --- Pump Control Functions ---
    # This function sets the flow rate for the Vapourtec SF-10 pump.
    def set_pump_flow_rate(self, flow_rate_ml_min):
        if self.pump:
            # The Vapourtec pump uses a specific command set.
            # This is a placeholder command; we would need to look up the exact command format in the datasheet.
            command = f"SET_FLOW {flow_rate_ml_min}\r\n"
            self.pump.write(command.encode())  # Encode the string to bytes and send it.
            print(f"Set pump flow rate to {flow_rate_ml_min} ml/min.")
        else:
            print("Pump is not connected. Simulating flow rate setting.")
            # Store previous setpoint for smooth transition
            if hasattr(self, 'pump_setpoint_flow'):
                self.previous_setpoint_flow = self.pump_setpoint_flow
            else:
                self.previous_setpoint_flow = flow_rate_ml_min
            
            # Store setpoint for realistic simulation
            self.pump_setpoint_flow = flow_rate_ml_min
            
            # Record time of change for smooth transition
            self.flow_change_time = time.time()
            
            time.sleep(0.1)
            return True

    # This function reads data from the pump (flow, pressure, RPM).
    def read_pump_data(self):
        if self.pump:
            # This is a placeholder for a real command to query pump data.
            self.pump.write(b"GET_STATUS\r\n")
            response = self.pump.readline().decode().strip()  # Read the response from the pump.
            # We would parse the response string to get the data.
            print(f"Pump data received: {response}")
            # For now, we'll return simulated data.
            return {"flow": 1.5, "pressure": 10.2, "rpm": 500}
        else:
            # Realistic simulation: flow very close to setpoint with minimal variation
            elapsed = time.time() - self.sim_start_time
            
            # Track when flow was last changed for smooth transition
            if not hasattr(self, 'flow_change_time'):
                self.flow_change_time = self.sim_start_time
            
            # Calculate time since last flow change
            time_since_change = time.time() - self.flow_change_time
            
            # Very small sinusoidal variation (±0.5% instead of 2%)
            flow_variation = 0.005 * self.pump_setpoint_flow * math.sin(2 * math.pi * elapsed / 25.0)
            
            # Add smooth transition when flow changes (exponential approach)
            # If flow was just changed, gradually approach new setpoint
            if time_since_change < 3.0:  # First 3 seconds after change
                # Exponential approach: starts at old value, approaches new value
                transition_factor = 1.0 - math.exp(-time_since_change / 0.8)  # Fast transition
                # Use previous setpoint if available, otherwise use current
                if hasattr(self, 'previous_setpoint_flow'):
                    sim_flow = self.previous_setpoint_flow + (self.pump_setpoint_flow - self.previous_setpoint_flow) * transition_factor
                else:
                    sim_flow = self.pump_setpoint_flow
            else:
                # After transition period, flow is very close to setpoint
                sim_flow = self.pump_setpoint_flow
            
            # Add minimal noise variation
            sim_flow = sim_flow + flow_variation
            
            # Pressure correlates with flow (higher flow = higher pressure) with sin variation
            base_pressure = 8.0 + (self.pump_setpoint_flow * 2.0)  # Base pressure scales with flow
            pressure_variation = 1.5 * math.sin(2 * math.pi * elapsed / 12.0 + math.pi/4)
            sim_pressure = base_pressure + pressure_variation
            
            # RPM correlates with flow
            base_rpm = 300 + (self.pump_setpoint_flow * 100)
            rpm_variation = 20 * math.sin(2 * math.pi * elapsed / 18.0)
            sim_rpm = int(base_rpm + rpm_variation)
            
            return {"flow": sim_flow, "pressure": sim_pressure, "rpm": sim_rpm}

    # This function turns the pump off.
    def stop_pump(self):
        if self.pump:
            command = "STOP\r\n"
            self.pump.write(command.encode())
            print("Pump stopped.")
        else:
            print("Pump is not connected. Simulating stop.")

    # --- NI Device and Sensor Read Functions ---
    # This function reads the voltage from a sensor connected to the NI device.
    def read_pressure_sensor(self):
        if self.ni_task:
            try:
                # This reads the analog input voltage from the channel we added in __init__.
                voltage = self.ni_task.read()
                # We would then convert the voltage to a pressure value using a calibration factor.
                # For the Ashcroft ZL92 sensor, the datasheet would provide this formula.
                # Pressure = (Voltage - Offset) * ScaleFactor
                pressure = voltage * 100  # Placeholder conversion
                return pressure
            except nidaqmx.errors.DaqError as e:
                print(f"Error reading from NI device: {e}")
                return None
        else:
            # Realistic simulation using sin function
            elapsed = time.time() - self.sim_start_time
            # Base pressure with sinusoidal variation (period ~20 seconds)
            base_pressure = 1.5
            variation = 0.8 * math.sin(2 * math.pi * elapsed / 20.0)
            sim_pressure = base_pressure + variation
            return max(0.1, sim_pressure)  # Ensure positive value

    # This function will read the level from the level sensor connected to the NI device.
    def read_level_sensor(self):
        if self.ni_task:
            # We would add a specific channel for the level sensor in the __init__ method.
            # Placeholder for the actual reading function.
            level = self.ni_task.read_from_level_channel()
            return level
        else:
            # Realistic simulation using sin function
            elapsed = time.time() - self.sim_start_time
            # Base level with slow sinusoidal variation (period ~60 seconds)
            base_level = 0.5  # 50% full
            variation = 0.3 * math.sin(2 * math.pi * elapsed / 60.0)
            sim_level = base_level + variation
            return max(0.05, min(0.95, sim_level))  # Clamp between 5% and 95%

    # --- Other Hardware Control Functions (Placeholders) ---
    def set_valves(self, valve_1_state, valve_2_state):
        """
        Control 3/2 valves through NI USB-6002 digital outputs
        valve_1_state: True = Main reservoir, False = Rinsing reservoir
        valve_2_state: True = Main reservoir, False = Rinsing reservoir
        """
        if self.ni_task:
            try:
                # Add digital output channels for valve control
                # Assuming valves are connected to digital output lines
                self.ni_task.do_channels.add_do_chan(f"{self.ni_device_name}/port0/line0")  # Valve 1
                self.ni_task.do_channels.add_do_chan(f"{self.ni_device_name}/port0/line1")  # Valve 2
                
                # Write valve states
                self.ni_task.write([valve_1_state, valve_2_state])
                print(f"Valves set: Valve 1 (Main) = {valve_1_state}, Valve 2 (Rinsing) = {valve_2_state}")
                
            except nidaqmx.errors.DaqError as e:
                print(f"Error controlling valves: {e}")
                print("Running in simulation mode for valve control.")
        else:
            print(f"Setting valves: Valve 1 (Main) = {valve_1_state}, Valve 2 (Rinsing) = {valve_2_state}")
            print("Running in simulation mode - valves not connected")

    def set_heating_plate_temp(self, temperature_celsius):
        """
        Control heating plate temperature through NI USB-6002
        Uses analog output to control temperature controller
        """
        if self.ni_task:
            try:
                # Add analog output channel for temperature control
                self.ni_task.ao_channels.add_ao_voltage_chan(f"{self.ni_device_name}/ao0")
                
                # Convert temperature to voltage (0-5V range)
                # Assuming 0V = 20°C, 5V = 100°C
                voltage = (temperature_celsius - 20.0) / 16.0  # 16°C per volt
                voltage = max(0.0, min(5.0, voltage))  # Clamp to 0-5V
                
                self.ni_task.write(voltage)
                print(f"Heating plate temperature set to {temperature_celsius}°C (Voltage: {voltage:.2f}V)")
                
            except nidaqmx.errors.DaqError as e:
                print(f"Error controlling heating plate: {e}")
                print("Running in simulation mode for temperature control.")
        else:
            print(f"Setting heating plate temperature to {temperature_celsius}°C")
            print("Running in simulation mode - heating plate not connected")

    def read_temperature_sensor(self):
        # Realistic simulation using sin function
        elapsed = time.time() - self.sim_start_time
        # Base temperature with slow sinusoidal variation (period ~45 seconds)
        base_temp = 25.0  # Room temperature
        variation = 5.0 * math.sin(2 * math.pi * elapsed / 45.0)
        sim_temp = base_temp + variation
        return max(20.0, min(50.0, sim_temp))  # Clamp between 20°C and 50°C

    def read_flow_sensor(self):
        """
        Read flow rate from Biotech AB-40010 flow sensor
        Connected through NI USB-6002 analog input
        """
        if self.ni_task:
            try:
                # Read voltage from flow sensor (assuming connected to ai1)
                voltage = self.ni_task.read()
                # Convert voltage to flow rate (calibration factor needed)
                # Typical flow sensor: 0-5V = 0-10 L/min
                flow_rate = voltage * 2.0  # Placeholder conversion
                return flow_rate
            except nidaqmx.errors.DaqError as e:
                print(f"Error reading flow sensor: {e}")
                return None
        else:
            # Realistic simulation: flow very close to pump setpoint
            elapsed = time.time() - self.sim_start_time
            
            # Track when flow was last changed for smooth transition
            if not hasattr(self, 'flow_change_time'):
                self.flow_change_time = self.sim_start_time
            
            time_since_change = time.time() - self.flow_change_time
            
            # Very small variation (±0.5%)
            flow_variation = 0.005 * self.pump_setpoint_flow * math.sin(2 * math.pi * elapsed / 25.0)
            
            # Smooth transition when flow changes
            if time_since_change < 3.0:
                if hasattr(self, 'previous_setpoint_flow'):
                    transition_factor = 1.0 - math.exp(-time_since_change / 0.8)
                    sim_flow = self.previous_setpoint_flow + (self.pump_setpoint_flow - self.previous_setpoint_flow) * transition_factor
                else:
                    sim_flow = self.pump_setpoint_flow
            else:
                sim_flow = self.pump_setpoint_flow
            
            sim_flow = sim_flow + flow_variation
            return max(0.1, sim_flow)  # Ensure positive value

    # --- SMU Detection and Control Functions ---
    def auto_detect_smu(self):
        """
        Auto-detect Keithley 2450 SMU from available VISA resources
        Returns the SMU resource if found, None otherwise
        """
        if not self.rm:
            return None
        
        try:
            # List all available VISA resources
            resources = self.rm.list_resources()
            print(f"Found {len(resources)} VISA resource(s):")
            
            for resource in resources:
                print(f"  - {resource}")
                try:
                    # Try to open the resource
                    inst = self.rm.open_resource(resource)
                    # Query device identification
                    idn = inst.query("*IDN?")
                    print(f"    IDN: {idn.strip()}")
                    
                    # Check if it's a Keithley 2450
                    if "2450" in idn.upper() or "KEITHLEY" in idn.upper():
                        print(f"    ✓ Found Keithley 2450 SMU at {resource}")
                        return inst
                    else:
                        inst.close()
                except Exception as e:
                    print(f"    Could not query {resource}: {e}")
                    continue
            
            print("No Keithley 2450 SMU found in available resources.")
            return None
            
        except Exception as e:
            print(f"Error during SMU auto-detection: {e}")
            return None
    
    def list_visa_resources(self):
        """
        List all available VISA resources
        Returns list of resource strings
        """
        if not self.rm:
            return []
        
        try:
            resources = self.rm.list_resources()
            return list(resources)
        except Exception as e:
            print(f"Error listing VISA resources: {e}")
            return []
    
    def get_smu_info(self):
        """
        Get information about the connected SMU
        Returns dictionary with device information
        """
        if not self.smu:
            print("get_smu_info: SMU is None")
            return {"connected": False, "info": "SMU not connected"}
        
        try:
            print(f"get_smu_info: Querying *IDN? from {self.smu.resource_name}")
            idn = self.smu.query("*IDN?")
            print(f"get_smu_info: Got IDN response: {idn.strip()}")
            return {
                "connected": True,
                "idn": idn.strip(),
                "resource": self.smu.resource_name
            }
        except Exception as e:
            print(f"get_smu_info: Error querying SMU: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    def setup_smu_for_iv_measurement(self, current_limit=0.1):
        """
        Setup SMU for I-V measurement - configure once before sweep
        current_limit: Current limit (A)
        """
        if not self.smu:
            print("SMU not connected. Cannot setup SMU.")
            return False
        
        try:
            # Configure as voltage source
            print("Sending: SOUR:FUNC VOLT")
            self.smu.write("SOUR:FUNC VOLT")
            # Configure measurement function to current
            print('Sending: SENS:FUNC "CURR"')
            self.smu.write('SENS:FUNC "CURR"')
            # Set current limit/compliance (using SOUR:VOLT:ILIM instead of SENS:CURR:PROT)
            print(f'Sending: SOUR:VOLT:ILIM {current_limit}')
            self.smu.write(f'SOUR:VOLT:ILIM {current_limit}')
            # Set NPLC for better accuracy (1 instead of 0.01 for less noise)
            # Fixed: NPLC must be under SENS, not directly under CURR
            print('Sending: SENS:CURR:NPLC 1')
            self.smu.write('SENS:CURR:NPLC 1')
            # Set appropriate current range
            print(f'Sending: SENS:CURR:RANG {current_limit}')
            self.smu.write(f'SENS:CURR:RANG {current_limit}')
            # Turn output on
            print("Sending: OUTP ON")
            self.smu.write("OUTP ON")
            print(f"SMU configured for I-V measurement (current limit: {current_limit}A)")
            return True
        except Exception as e:
            print(f"Error setting up SMU: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_smu_voltage(self, voltage, current_limit=0.1):
        """
        Set SMU output voltage - only sets voltage, doesn't reconfigure
        voltage: Voltage to set (V)
        current_limit: Current limit (A) - not used here, kept for compatibility
        """
        if not self.smu:
            print("SMU not connected. Cannot set voltage.")
            return False
        
        try:
            # Only set voltage, don't reconfigure everything
            self.smu.write(f"SOUR:VOLT {voltage}")
            return True
        except Exception as e:
            print(f"Error setting SMU voltage: {e}")
            return False
    
    def measure_smu(self):
        """
        Measure voltage and current from SMU
        Returns dictionary with voltage and current, or None on error
        Uses MEAS:CURR? which performs measurement automatically (no INIT needed)
        """
        if not self.smu:
            return None
        
        try:
            # Read current using MEAS:CURR? (MEAS:CURR? performs measurement automatically, no INIT needed)
            current_string = self.smu.query('MEAS:CURR?')
            current = float(current_string)
            # Read voltage (the source voltage we set)
            voltage_string = self.smu.query('SOUR:VOLT?')
            voltage = float(voltage_string)
            return {"voltage": voltage, "current": current}
        except Exception as e:
            print(f"Error measuring SMU: {e}")
            return None
    
    def get_smu_output_state(self):
        """
        Get SMU output state (ON/OFF)
        Returns True if output is ON, False otherwise
        """
        if not self.smu:
            return False
        
        try:
            state = self.smu.query("OUTP?")
            return "1" in state or "ON" in state.upper()
        except Exception as e:
            print(f"Error reading SMU output state: {e}")
            return False
    
    # --- SMU Control Functions ---
    def setup_smu_iv_sweep(self, start_v, end_v, step_v, current_limit=0.1):
        """
        Setup Keithley 2450 SMU for I-V sweep measurement
        Note: We do manual sweep (not using built-in sweep mode) to avoid trigger model issues
        start_v: Starting voltage (V)
        end_v: Ending voltage (V)
        step_v: Voltage step (V)
        current_limit: Current limit (A)
        """
        if self.smu:
            try:
                # Reset SMU (this resets everything including sweep mode)
                print("Sending: *RST")
                self.smu.write("*RST")
                time.sleep(0.5)
                
                # Configure source function to voltage
                print("Sending: SOUR:FUNC VOLT")
                self.smu.write("SOUR:FUNC VOLT")
                
                # Set voltage range (use max of start/end for safety)
                voltage_range = max(abs(start_v), abs(end_v))
                print(f"Sending: SOUR:VOLT:RANG {voltage_range}")
                self.smu.write(f"SOUR:VOLT:RANG {voltage_range}")
                
                # Set current limit
                print(f"Sending: SOUR:VOLT:ILIM {current_limit}")
                self.smu.write(f"SOUR:VOLT:ILIM {current_limit}")
                
                # Configure measurement function to current
                print('Sending: SENS:FUNC "CURR"')
                self.smu.write('SENS:FUNC "CURR"')
                
                # Set current range
                print(f"Sending: SENS:CURR:RANG {current_limit}")
                self.smu.write(f"SENS:CURR:RANG {current_limit}")
                
                # Note: Current limit already set above with SOUR:VOLT:ILIM
                # SENS:CURR:PROT is not supported, using SOUR:VOLT:ILIM instead
                
                # Set NPLC for better accuracy
                print("Sending: SENS:CURR:NPLC 1")
                self.smu.write("SENS:CURR:NPLC 1")
                
                # Set aperture time
                print("Sending: SENS:CURR:APER 0.1")
                self.smu.write("SENS:CURR:APER 0.1")
                
                # IMPORTANT: Do NOT enable sweep mode - we do manual sweep
                # This avoids trigger model errors (Error 2710)
                # The sweep will be done manually by setting voltage and measuring in a loop
                
                print(f"SMU configured for manual I-V sweep: {start_v}V to {end_v}V, step {step_v}V")
                print("Note: Using manual sweep (not built-in sweep mode) to avoid trigger model issues")
                
            except Exception as e:
                print(f"Error configuring SMU: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"SMU not connected. Simulating I-V setup: {start_v}V to {end_v}V, step {step_v}V")

    def read_smu_data(self):
        """
        Read voltage and current from Keithley 2450 SMU
        Returns dictionary with voltage and current values
        """
        if self.smu:
            try:
                # Read voltage and current separately
                # MEAS:CURR? performs measurement automatically (no INIT needed)
                # READ? returns only the measured value (current if SENS:FUNC is CURR)
                # So we need to read both separately
                current = float(self.smu.query("MEAS:CURR?"))
                voltage = float(self.smu.query("SOUR:VOLT?"))
                
                return {"voltage": voltage, "current": current}
                
            except Exception as e:
                print(f"Error reading SMU data: {e}")
                return None
        else:
            # Simulation mode - generate realistic I-V curve data
            # For I-V measurements, we'll use a simple linear relationship
            # The actual I-V sweep will be handled in run_iv_measurement
            sim_voltage = 0.0
            sim_current = 0.0
            return {"voltage": sim_voltage, "current": sim_current}

    def is_smu_sweep_complete(self):
        """
        Check if SMU sweep is complete
        """
        if self.smu:
            try:
                # Check if sweep is complete
                status = self.smu.query("STAT:OPER:COND?")
                return int(status) & 0x1000 == 0  # Bit 12 indicates sweep complete
            except Exception as e:
                print(f"Error checking SMU status: {e}")
                return True
        else:
            # Simulation mode - always return True after some time
            return True

    def stop_smu(self):
        """
        Stop SMU operation
        """
        if self.smu:
            try:
                self.smu.write("SOUR:VOLT 0")
                self.smu.write("OUTP OFF")
                print("SMU stopped")
            except Exception as e:
                print(f"Error stopping SMU: {e}")
        else:
            print("SMU not connected. Simulating stop.")