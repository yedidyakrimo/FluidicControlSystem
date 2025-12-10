"""
Vapourtec SF-10 Pump control module
Updated to use the vapourtec library
"""

import time
import math
from hardware.base import HardwareBase

# Try to import the vapourtec library
try:
    from vapourtec import SF10
    VAPOURTEC_AVAILABLE = True
except ImportError:
    VAPOURTEC_AVAILABLE = False
    print("=" * 60)
    print("WARNING: vapourtec library not found!")
    print("Pump will run in simulation mode.")
    print("")
    print("To connect to the real pump, install the library:")
    print("  pip install vapourtec")
    print("=" * 60)


class VapourtecPump(HardwareBase):
    """
    Vapourtec SF-10 Pump controller
    Uses the vapourtec library for communication
    Maximum flow rate: 5.0 ml/min
    """
    
    MAX_FLOW_RATE = 5.0  # Maximum allowed flow rate in ml/min
    
    def __init__(self, port='COM3', baudrate=9600, timeout=1, tube_type=3):
        """
        Initialize Vapourtec pump
        
        Args:
            port: Serial port (e.g., 'COM3' on Windows)
            baudrate: Serial communication baudrate (usually 9600)
            timeout: Serial timeout in seconds
            tube_type: Tube type ID (3 = Black, default)
        """
        super().__init__()
        self.device_name = "Vapourtec SF-10 Pump"
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.tube_type = tube_type
        self.pump = None
        self.ser = None  # Direct serial access for raw commands
        
        # Simulation state variables
        self.sim_start_time = time.time()
        self.pump_setpoint_flow = 1.5  # Default flow rate setpoint
        self.previous_setpoint_flow = 1.5
        self.flow_change_time = time.time()
        self.is_running = False
        
        self.connect()
    
    def connect(self):
        """Connect to pump via vapourtec library"""
        if not VAPOURTEC_AVAILABLE:
            print("Vapourtec library not available. Running in simulation mode.")
            self.enable_simulation()
            return False
        
        try:
            # Use vapourtec library for connection handshake
            self.pump = SF10(self.port)
            # Get direct access to serial port for raw commands
            # This is needed because the library doesn't support all commands natively
            self.ser = self.pump.ser
            
            # CRITICAL PATCH: The library does not natively support setting the "Black" tube type
            # This prevents the pump from accepting flow rates. We must send a raw command.
            print(f"[SETUP] Setting Tube Type to ID {self.tube_type} (Black tube)...")
            self.ser.write(f'STTA {self.tube_type}\r\n'.encode())
            time.sleep(0.5)  # Wait for hardware to process the command
            
            # Set mode to flow mode using library method
            if hasattr(self.pump, 'MODE_FLOW'):
                self.pump.set_mode(self.pump.MODE_FLOW)
            
            print(f"[SUCCESS] Connected to Vapourtec pump on port {self.port}")
            self.connected = True
            self.simulation_mode = False
            return True
        except Exception as e:
            print(f"Error connecting to Vapourtec pump: {e}")
            self.pump = None
            self.ser = None
            self.enable_simulation()
            return False
    
    def disconnect(self):
        """Disconnect from pump"""
        if self.pump:
            try:
                self.stop()  # Stop pump before disconnecting
                self.pump.disconnect()
            except Exception as e:
                print(f"Error during disconnect: {e}")
            self.pump = None
            self.ser = None
        self.connected = False
        self.is_running = False
    
    def force_reconnect(self):
        """
        Force a hard reconnection attempt with RETRY LOGIC.
        Retries up to 2 times to handle pump boot-up lag or zombie ports.
        
        Returns:
            True if successfully connected, False otherwise
        """
        if not VAPOURTEC_AVAILABLE:
            print("Vapourtec library not available. Cannot force reconnect.")
            self.enable_simulation()
            return False
        
        # --- Aggressive Cleanup First ---
        print(f"[FORCE_RECONNECT] Attempting hard reconnection to pump on port {self.port}...")
        
        try:
            # Stop pump before disconnecting
            if self.pump:
                try:
                    self.stop()
                except:
                    pass
            
            # Close all connections aggressively
            if self.pump:
                try:
                    self.pump.disconnect()
                except:
                    pass
            if self.ser:
                try:
                    self.ser.close()
                except:
                    pass
        except Exception as e:
            print(f"[FORCE_RECONNECT] Error during cleanup: {e}")
        
        # Reset all references
        self.pump = None
        self.ser = None
        self.connected = False
        self.is_running = False
        
        # --- Retry Loop (The Fix) ---
        max_retries = 2
        for attempt in range(max_retries):
            try:
                print(f"[FORCE_RECONNECT] Connection attempt {attempt+1}/{max_retries}...")
                
                # 1. Initialize Library
                self.pump = SF10(self.port)
                self.ser = self.pump.ser
                
                # 2. CRITICAL: Send Black Tube Command
                # Allow a tiny pause for serial to stabilize
                time.sleep(0.2)
                print(f"[FORCE_RECONNECT] Setting Tube Type to ID {self.tube_type} (Black tube)...")
                self.ser.write(f'STTA {self.tube_type}\r\n'.encode())
                time.sleep(0.5)  # Wait for hardware to process the command
                
                # 3. Set Mode
                if hasattr(self.pump, 'MODE_FLOW'):
                    print(f"[FORCE_RECONNECT] Setting mode to FLOW...")
                    self.pump.set_mode(self.pump.MODE_FLOW)
                
                # 4. Success!
                print(f"[FORCE_RECONNECT] ✅ Connected successfully on attempt {attempt+1}")
                self.connected = True
                self.simulation_mode = False
                return True
                
            except Exception as e:
                error_msg = str(e)
                print(f"[FORCE_RECONNECT] Attempt {attempt+1} failed: {error_msg}")
                
                # Clean up specific to this failed attempt
                try:
                    if self.pump:
                        self.pump.disconnect()
                except:
                    pass
                try:
                    if self.ser:
                        self.ser.close()
                except:
                    pass
                
                self.pump = None
                self.ser = None
                
                # If this was not the last attempt, wait and try again
                if attempt < max_retries - 1:
                    print("[FORCE_RECONNECT] Waiting 2 seconds for device to recover...")
                    time.sleep(2.0)  # Critical wait for pump boot-up or port release
        
        # If we get here, all retries failed
        print("[FORCE_RECONNECT] ❌ All connection attempts failed. Falling back to Simulation.")
        self.enable_simulation()
        return False
    
    def set_flow_rate(self, flow_rate_ml_min):
        """
        Set pump flow rate
        
        Uses the vapourtec library's set_flow_rate() method, which works correctly
        after the tube type has been set via raw command (STTA).
        
        Args:
            flow_rate_ml_min: Flow rate in ml/min (max 5.0)
            
        Returns:
            True if successful, False if invalid
        """
        # Enforce maximum flow rate limit
        if flow_rate_ml_min > self.MAX_FLOW_RATE:
            print(f"Warning: Flow rate {flow_rate_ml_min} ml/min exceeds maximum of {self.MAX_FLOW_RATE} ml/min. Setting to {self.MAX_FLOW_RATE} ml/min.")
            flow_rate_ml_min = self.MAX_FLOW_RATE
        
        if flow_rate_ml_min < 0:
            print(f"Warning: Flow rate cannot be negative. Setting to 0.")
            flow_rate_ml_min = 0.0
        
        if self.pump and self.connected:
            try:
                # Use library method - this works after tube type is set
                self.pump.set_flow_rate(float(flow_rate_ml_min))
                print(f"Set pump flow rate to {flow_rate_ml_min} ml/min.")
                # Store for simulation fallback
                self.previous_setpoint_flow = self.pump_setpoint_flow
                self.pump_setpoint_flow = flow_rate_ml_min
                self.flow_change_time = time.time()
                return True
            except Exception as e:
                print(f"Error setting flow rate: {e}")
                return False
        else:
            # Simulation mode
            print("Pump is not connected. Simulating flow rate setting.")
            self.previous_setpoint_flow = self.pump_setpoint_flow
            self.pump_setpoint_flow = flow_rate_ml_min
            self.flow_change_time = time.time()
            time.sleep(0.1)
            return True
    
    def start(self):
        """Start the pump - following the exact sequence from working examples"""
        if self.pump and self.connected:
            try:
                print("[PUMP] Starting pump...")
                
                # Step 1: Ensure tube type is set (should already be set in connect, but double-check)
                if self.ser:
                    print("[PUMP] Verifying tube type is set...")
                    self.ser.write(f'STTA {self.tube_type}\r\n'.encode())
                    time.sleep(0.5)
                
                # Step 2: Ensure mode is set to FLOW
                if hasattr(self.pump, 'MODE_FLOW'):
                    print("[PUMP] Setting mode to FLOW...")
                    self.pump.set_mode(self.pump.MODE_FLOW)
                    time.sleep(0.2)
                
                # Step 3: Ensure flow rate is set before starting
                if self.pump_setpoint_flow > 0:
                    print(f"[PUMP] Setting flow rate to {self.pump_setpoint_flow} ml/min...")
                    self.pump.set_flow_rate(float(self.pump_setpoint_flow))
                    time.sleep(0.3)  # Wait for pump to process flow rate
                
                # Step 4: Start the pump using library method (as in working examples)
                print("[PUMP] Calling pump.start()...")
                self.pump.start()
                time.sleep(0.5)  # Wait for pump to actually start running
                
                self.is_running = True
                print("[PUMP] Pump started successfully!")
                return True
            except Exception as e:
                print(f"[PUMP ERROR] Error starting pump: {e}")
                import traceback
                traceback.print_exc()
                self.is_running = False
                return False
        else:
            print("[PUMP] Pump is not connected. Simulating start.")
            self.is_running = True
            return True
    
    def stop(self):
        """Stop the pump"""
        if self.pump and self.connected:
            try:
                self.pump.stop()
                self.is_running = False
                print("Pump stopped.")
                return True
            except Exception as e:
                print(f"Error stopping pump: {e}")
                return False
        else:
            print("Pump is not connected. Simulating stop.")
            self.is_running = False
            return True
    
    def get_pressure(self):
        """
        Get current pressure reading from pump using GP command
        
        Protocol:
        - Send: b'GP\r\n'
        - Wait: 0.1 seconds (CRITICAL timing)
        - Read: Use in_waiting to check bytes, then read(num_bytes)
        - DO NOT use: ser.read_all() (causes AttributeError)
        
        Returns:
            Pressure value in bar (or 0.0 if empty/error, or None on connection failure)
        """
        if self.pump and self.ser and self.connected:
            try:
                # Clear any pending data first
                if self.ser.in_waiting > 0:
                    self.ser.read(self.ser.in_waiting)
                
                # Send GP command (Get Pressure) - raw bytes as specified
                self.ser.write(b'GP\r\n')
                
                # CRITICAL: Must wait 0.1 seconds to allow pump to populate buffer
                time.sleep(0.1)
                
                # CRITICAL: Use in_waiting to check available bytes (NOT read_all())
                bytes_available = self.ser.in_waiting
                
                if bytes_available > 0:
                    # Read exactly the number of bytes available
                    response_bytes = self.ser.read(bytes_available)
                    response = response_bytes.decode('ascii', errors='ignore').strip()
                    
                    # Try to parse as float
                    if response:
                        try:
                            pressure = float(response)
                            return pressure
                        except ValueError:
                            # If not a number, try to extract number from response
                            import re
                            numbers = re.findall(r'-?\d+\.?\d*', response)
                            if numbers:
                                try:
                                    pressure = float(numbers[0])
                                    return pressure
                                except ValueError:
                                    pass
                            # Could not parse - return 0.0 as specified
                            print(f"Warning: Could not parse pressure response: '{response}'. Returning 0.0")
                            return 0.0
                else:
                    # No response - return 0.0 as specified
                    return 0.0
                    
            except Exception as e:
                print(f"Error reading pressure: {e}")
                return None
        else:
            # Simulation mode - return simulated pressure
            return self._simulate_data().get('pressure')
    
    def read_data(self):
        """
        Read data from pump (flow, pressure, RPM)
        
        Returns:
            Dictionary with flow, pressure, and rpm
        """
        if self.pump and self.connected:
            try:
                # Get pressure
                pressure = self.get_pressure()
                
                # Get flow rate (current setpoint)
                flow = self.pump_setpoint_flow
                
                # RPM calculation (if available from pump, otherwise estimate)
                # Typical: RPM ≈ flow_rate * 100
                rpm = int(300 + (flow * 100))
                
                return {
                    "flow": flow,
                    "pressure": pressure if pressure is not None else 0.0,
                    "rpm": rpm
                }
            except Exception as e:
                print(f"Error reading pump data: {e}")
                return self._simulate_data()
        else:
            # Realistic simulation
            return self._simulate_data()
    
    def _simulate_data(self):
        """Generate realistic simulated pump data"""
        elapsed = time.time() - self.sim_start_time
        
        if not hasattr(self, 'flow_change_time'):
            self.flow_change_time = self.sim_start_time
        
        time_since_change = time.time() - self.flow_change_time
        
        # Small sinusoidal variation (±0.5%)
        flow_variation = 0.005 * self.pump_setpoint_flow * math.sin(2 * math.pi * elapsed / 25.0)
        
        # Smooth transition when flow changes
        if time_since_change < 3.0:
            transition_factor = 1.0 - math.exp(-time_since_change / 0.8)
            sim_flow = self.previous_setpoint_flow + (self.pump_setpoint_flow - self.previous_setpoint_flow) * transition_factor
        else:
            sim_flow = self.pump_setpoint_flow
        
        sim_flow = sim_flow + flow_variation
        
        # Pressure correlates with flow
        base_pressure = 8.0 + (self.pump_setpoint_flow * 2.0)
        pressure_variation = 1.5 * math.sin(2 * math.pi * elapsed / 12.0 + math.pi/4)
        sim_pressure = base_pressure + pressure_variation
        
        # RPM correlates with flow
        base_rpm = 300 + (self.pump_setpoint_flow * 100)
        rpm_variation = 20 * math.sin(2 * math.pi * elapsed / 18.0)
        sim_rpm = int(base_rpm + rpm_variation)
        
        return {"flow": sim_flow, "pressure": sim_pressure, "rpm": sim_rpm}
    
    def get_info(self):
        """
        Get pump connection information with active health check
        
        Performs an active "ping" by sending GV (Get Version) command.
        If timeout or error occurs, closes connection and marks as disconnected.
        
        Returns:
            Dictionary with pump status information
        """
        info = {
            "device_name": self.device_name,
            "port": self.port,
            "connected": self.connected,
            "simulation_mode": self.simulation_mode,
            "is_running": self.is_running,
            "current_flow_rate": self.pump_setpoint_flow,
            "tube_type": self.tube_type,
            "max_flow_rate": self.MAX_FLOW_RATE
        }
        
        # Active Health Check: Only if we think we're connected
        if self.connected and not self.simulation_mode and self.ser:
            try:
                # Clear any pending data first
                if self.ser.in_waiting > 0:
                    self.ser.read(self.ser.in_waiting)
                
                # Send GV (Get Version) command as a ping
                # This verifies the device is actually responsive, not just that the port is open
                self.ser.write(b'GV\r\n')
                time.sleep(0.5)  # Increased wait time for response (from 0.2 to 0.5)
                
                # Check if we got a response (even if we don't parse it)
                if self.ser.in_waiting > 0:
                    # Device responded - read and discard the response
                    self.ser.read(self.ser.in_waiting)
                    info["status"] = "Connected"
                    info["status_color"] = "green"
                    info["connected"] = True  # Ensure connected flag is set
                else:
                    # No response - try one more time with longer wait
                    time.sleep(0.5)
                    if self.ser.in_waiting > 0:
                        self.ser.read(self.ser.in_waiting)
                        info["status"] = "Connected"
                        info["status_color"] = "green"
                        info["connected"] = True
                    else:
                        # Still no response - device is not responsive
                        raise Exception("No response to GV command after retry")
                    
            except Exception as e:
                # Timeout or communication error - device is not responsive
                error_msg = str(e)
                print(f"Pump health check failed: {error_msg}")
                
                # Close the connection explicitly
                try:
                    if self.pump:
                        self.pump.disconnect()
                except:
                    pass
                try:
                    if self.ser:
                        self.ser.close()
                except:
                    pass
                
                # Mark as disconnected
                self.pump = None
                self.ser = None
                self.connected = False
                info["connected"] = False
                info["status"] = "Not Connected"
                info["status_color"] = "red"
        elif self.connected and not self.simulation_mode:
            # Connected but no serial port yet (just after force_reconnect)
            # This can happen briefly after reconnection
            info["status"] = "Connected"
            info["status_color"] = "green"
            info["connected"] = True
        elif self.simulation_mode:
            info["status"] = "Simulation Mode"
            info["status_color"] = "orange"
        else:
            info["status"] = "Not Connected"
            info["status_color"] = "red"
        
        return info
