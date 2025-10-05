# hardware_control.py

import serial  # Library for serial communication (e.g., with the pump)
import nidaqmx  # Library for NI DAQ devices (e.g., NI USB-6002)
import time
import random  # For simulation purposes until a real device is connected

# Try to import pyvisa, if not available, SMU will run in simulation mode
try:
    import pyvisa  # Library for VISA communication (e.g., with Keithley SMU)  # noqa: F401
    PYVISA_AVAILABLE = True
except ImportError:
    PYVISA_AVAILABLE = False
    print("PyVISA not available. SMU will run in simulation mode.")


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

        # We'll use a try-except block to handle NI-DAQmx driver errors.
        try:
            # Initialize connection to the NI USB device.
            # The ni_device_name is the name of your NI device (e.g., 'Dev1').
            self.ni_task = nidaqmx.Task()
            # Add an analog input channel for a simulated pressure sensor.
            # This is where we would configure the specific channels for our sensors (pressure, temp, flow).
            self.ni_task.ai_channels.add_ai_voltage_chan(f"{ni_device_name}/ai0")
            print(f"Connected to NI device: {ni_device_name}")
        except nidaqmx.errors.DaqError as e:
            # If the NI-DAQmx driver is not found, print an error message.
            print(f"Error connecting to NI device: {e}")
            print("Running in simulation mode for NI sensors.")
            self.ni_task = None

        # Initialize Keithley 2450 SMU
        self.smu = None
        if smu_resource and PYVISA_AVAILABLE:
            try:
                self.rm = pyvisa.ResourceManager()
                self.smu = self.rm.open_resource(smu_resource)
                print(f"Connected to Keithley 2450 SMU: {smu_resource}")
            except Exception as e:
                print(f"Error connecting to Keithley SMU: {e}")
                print("Running in simulation mode for SMU.")
                self.smu = None
        elif smu_resource and not PYVISA_AVAILABLE:
            print("PyVISA not available. Running in simulation mode for SMU.")
            self.smu = None

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
            # Simulation for a non-connected pump.
            sim_flow = random.uniform(0.5, 2.0)
            sim_pressure = random.uniform(5.0, 15.0)
            sim_rpm = random.randint(300, 600)
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
            # Simulation for a non-connected NI device.
            sim_pressure = random.uniform(0.5, 2.5)  # Simulating a pressure value.
            return sim_pressure

    # This function will read the level from the level sensor connected to the NI device.
    def read_level_sensor(self):
        if self.ni_task:
            # We would add a specific channel for the level sensor in the __init__ method.
            # Placeholder for the actual reading function.
            level = self.ni_task.read_from_level_channel()
            return level
        else:
            # Simulating a level value.
            sim_level = random.uniform(0.1, 0.9)  # Level as a fraction of tank height.
            return sim_level

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
        # Reads data from a temperature sensor.
        sim_temp = random.uniform(20.0, 50.0)
        return sim_temp

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
            # Simulation mode
            sim_flow = random.uniform(0.5, 2.0)
            return sim_flow

    # --- SMU Control Functions ---
    def setup_smu_iv_sweep(self, start_v, end_v, step_v, current_limit=0.1):
        """
        Setup Keithley 2450 SMU for I-V sweep measurement
        start_v: Starting voltage (V)
        end_v: Ending voltage (V)
        step_v: Voltage step (V)
        current_limit: Current limit (A)
        """
        if self.smu:
            try:
                # Reset SMU
                self.smu.write("*RST")
                time.sleep(1)
                
                # Configure source function to voltage
                self.smu.write("SOUR:FUNC VOLT")
                
                # Set voltage range
                self.smu.write(f"SOUR:VOLT:RANG {max(abs(start_v), abs(end_v))}")
                
                # Set current limit
                self.smu.write(f"SOUR:VOLT:ILIM {current_limit}")
                
                # Configure measurement function to current
                self.smu.write("SENS:FUNC 'CURR'")
                
                # Set current range
                self.smu.write(f"SENS:CURR:RANG {current_limit}")
                
                # Configure sweep parameters
                self.smu.write(f"SOUR:VOLT:STAR {start_v}")
                self.smu.write(f"SOUR:VOLT:STOP {end_v}")
                self.smu.write(f"SOUR:VOLT:STEP {step_v}")
                
                # Set sweep mode
                self.smu.write("SOUR:VOLT:MODE SWE")
                
                # Set measurement delay
                self.smu.write("SENS:CURR:DC:APER 0.1")
                
                print(f"SMU configured for I-V sweep: {start_v}V to {end_v}V, step {step_v}V")
                
            except Exception as e:
                print(f"Error configuring SMU: {e}")
        else:
            print(f"SMU not connected. Simulating I-V setup: {start_v}V to {end_v}V, step {step_v}V")

    def read_smu_data(self):
        """
        Read voltage and current from Keithley 2450 SMU
        Returns dictionary with voltage and current values
        """
        if self.smu:
            try:
                # Trigger measurement
                self.smu.write("INIT")
                
                # Read voltage and current
                voltage = float(self.smu.query("READ?"))
                current = float(self.smu.query("MEAS:CURR?"))
                
                return {"voltage": voltage, "current": current}
                
            except Exception as e:
                print(f"Error reading SMU data: {e}")
                return None
        else:
            # Simulation mode - generate realistic I-V curve data
            sim_voltage = random.uniform(-2.0, 2.0)
            sim_current = sim_voltage * 0.1 + random.uniform(-0.01, 0.01)  # Linear with noise
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