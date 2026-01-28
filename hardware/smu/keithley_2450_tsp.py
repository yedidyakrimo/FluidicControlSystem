"""
TSP (Test Script Processor) wrapper for Keithley 2450
Provides TSP-based operations without modifying the existing keithley_2450.py
"""

import time
from hardware.smu.tsp_script_generator import TSPScriptGenerator
from hardware.smu.tsp_scpi_commands import TSPSCPICommands
from utils.logger_config import get_logger

logger = get_logger(__name__)


class Keithley2450TSP:
    """
    TSP wrapper for Keithley 2450 SMU
    Uses existing Keithley2450 connection but adds TSP layer
    Does NOT modify keithley_2450.py
    """
    
    def __init__(self, keithley_2450_instance):
        """
        Initialize TSP wrapper
        
        Args:
            keithley_2450_instance: Instance of Keithley2450 class
        """
        self.keithley = keithley_2450_instance
        self.tsp_scpi = TSPSCPICommands()
        self.script_generator = TSPScriptGenerator()
        
    def _get_visa_resource(self):
        """
        Get VISA resource from Keithley2450 instance
        
        Returns:
            VISA resource or None if not connected
        """
        if not self.keithley or not self.keithley.smu:
            return None
        return self.keithley.smu
    
    def _ensure_scpi_mode(self):
        """
        Ensure device is in SCPI mode before sending loadscriptrun
        
        Returns:
            True if in SCPI mode, False otherwise
        """
        smu = self._get_visa_resource()
        if not smu:
            return False
        
        try:
            # Check current language
            lang = smu.query(self.tsp_scpi.query_language()).strip()
            
            # If not SCPI, set it
            if "SCPI" not in lang.upper():
                logger.debug(f"Device is in {lang} mode, switching to SCPI...")
                smu.write(self.tsp_scpi.set_language_scpi())
                time.sleep(0.1)
                # Verify
                lang = smu.query(self.tsp_scpi.query_language()).strip()
                if "SCPI" not in lang.upper():
                    logger.warning(f"Failed to set SCPI mode, current: {lang}")
                    return False
            
            return True
        except Exception as e:
            logger.warning(f"Could not verify/set SCPI mode: {e}")
            # Try to set anyway
            try:
                smu.write(self.tsp_scpi.set_language_scpi())
                time.sleep(0.1)
                return True
            except:
                return False
    
    def _check_system_error(self):
        """
        Check for system errors and return error message if any
        
        Returns:
            tuple: (has_error: bool, error_message: str)
        """
        smu = self._get_visa_resource()
        if not smu:
            return (False, "")
        
        try:
            error_str = smu.query(self.tsp_scpi.system_error()).strip()
            # Format: "error_code,\"error_message\""
            parts = error_str.split(',', 1)
            if len(parts) >= 2:
                error_code = parts[0].strip()
                error_msg = parts[1].strip().strip('"')
                
                # Error code 0 means no error
                try:
                    if int(error_code) != 0:
                        return (True, f"Error {error_code}: {error_msg}")
                except ValueError:
                    pass
            
            return (False, "")
        except Exception as e:
            logger.debug(f"Could not check system error: {e}")
            return (False, "")
    
    def write_tsp_script(self, script_content, script_name="cv_sweep"):
        """
        Write TSP script to instrument using loadscriptrun
        
        Args:
            script_content: Lua script content as string
            script_name: Optional script name (not used with loadscriptrun)
            
        Returns:
            True if successful, False otherwise
        """
        smu = self._get_visa_resource()
        if not smu:
            logger.warning("TSP: SMU not connected")
            return False
        
        try:
            # Step 1: Ensure device is in SCPI mode
            if not self._ensure_scpi_mode():
                logger.warning("TSP: Could not ensure SCPI mode")
                return False
            
            # Step 2: Clear any previous errors
            self._check_system_error()  # Just to clear error queue
            
            # Step 3: Prepare script with proper line endings
            # According to Keithley manual, loadscriptrun requires:
            # 1. loadscriptrun on first line
            # 2. Script content (each line with \r\n)
            # 3. endscript on last line
            # IMPORTANT: All must be sent as ONE block with \r\n line endings
            
            # Step 4: Increase timeout for script loading
            original_timeout = smu.timeout
            smu.timeout = 10000  # 10 seconds for script loading
            
            # Step 5: Build complete script block with \r\n line endings
            # IMPORTANT: PyVISA write() adds terminator automatically, but loadscriptrun
            # needs the entire block without terminators on internal lines
            # Solution: Temporarily disable terminator or use write_raw
            
            script_lines = script_content.strip().split('\n')
            # Join with \r\n (Windows line ending required by Keithley)
            formatted_script = '\r\n'.join(script_lines)
            
            # Build complete command block (no terminator on internal lines)
            full_command = f"loadscriptrun\r\n{formatted_script}\r\nendscript"
            
            # Step 6: Send complete command as one block
            # Save original terminator and temporarily disable it
            original_write_termination = getattr(smu, 'write_termination', None)
            try:
                # Disable write termination for loadscriptrun
                smu.write_termination = ''
                # Send as bytes to avoid any automatic processing
                if hasattr(smu, 'write_raw'):
                    smu.write_raw(full_command.encode('utf-8') + b'\n')
                else:
                    # Fallback: write with explicit newline
                    smu.write(full_command + '\n')
            finally:
                # Restore original termination
                if original_write_termination is not None:
                    smu.write_termination = original_write_termination
            
            # Step 7: Small delay to allow script to start
            time.sleep(0.2)
            
            # Step 8: Check for errors
            has_error, error_msg = self._check_system_error()
            if has_error:
                logger.error(f"TSP Error after sending script: {error_msg}")
                smu.timeout = original_timeout
                return False
            
            # Step 9: Restore timeout
            smu.timeout = original_timeout
            
            return True
        except Exception as e:
            logger.error(f"TSP Error writing script: {e}")
            # Check for system error
            has_error, error_msg = self._check_system_error()
            if has_error:
                logger.error(f"System error: {error_msg}")
            return False
    
    def run_cv_sweep_tsp(self, v1, v2, v3, v4, points_per_second, current_range, current_limit=0.1, timeout=300):
        """
        Run Cyclic Voltammetry sweep using TSP
        
        Args:
            v1, v2, v3, v4: Voltage vertices (V)
            points_per_second: Sampling density (points/sec)
            current_range: Manual current range (A)
            current_limit: Current limit/compliance (A), default 0.1
            timeout: Maximum time to wait for completion (seconds)
            
        Returns:
            dict with keys:
                - 'success': bool
                - 'voltage_data': list of voltages
                - 'current_data': list of currents
                - 'error': error message if failed
        """
        smu = self._get_visa_resource()
        if not smu:
            return {
                'success': False,
                'voltage_data': [],
                'current_data': [],
                'error': 'SMU not connected'
            }
        
        try:
            # Generate TSP script
            script = self.script_generator.generate_cv_sweep_script(
                v1, v2, v3, v4, points_per_second, current_range, current_limit
            )
            
            # Write and execute script
            if not self.write_tsp_script(script):
                # Check for detailed error
                has_error, error_msg = self._check_system_error()
                if has_error:
                    return {
                        'success': False,
                        'voltage_data': [],
                        'current_data': [],
                        'error': f'Failed to write TSP script: {error_msg}'
                    }
                return {
                    'success': False,
                    'voltage_data': [],
                    'current_data': [],
                    'error': 'Failed to write TSP script (check system errors)'
                }
            
            # Wait for completion using *OPC?
            # Important: Wait a bit before querying to avoid "Query Interrupted"
            time.sleep(0.2)
            
            original_timeout = smu.timeout
            smu.timeout = timeout * 1000  # Convert to milliseconds
            
            try:
                # Wait for operation complete
                opc_result = smu.query(self.tsp_scpi.operation_complete())
                if "1" not in str(opc_result):
                    logger.warning(f"Operation complete query returned unexpected value: {opc_result}")
                
                # Check for errors after completion
                has_error, error_msg = self._check_system_error()
                if has_error:
                    logger.warning(f"System error after sweep completion: {error_msg}")
            except Exception as e:
                logger.warning(f"Error waiting for operation complete: {e}")
                # Check for system error
                has_error, error_msg = self._check_system_error()
                if has_error:
                    logger.error(f"System error: {error_msg}")
            
            # Restore timeout
            smu.timeout = original_timeout
            
            # Fetch buffer data
            return self.fetch_buffer_data()
            
        except Exception as e:
            return {
                'success': False,
                'voltage_data': [],
                'current_data': [],
                'error': f'TSP sweep error: {str(e)}'
            }
    
    def fetch_buffer_data(self):
        """
        Fetch voltage and current data from defbuffer1
        
        Returns:
            dict with keys:
                - 'success': bool
                - 'voltage_data': list of voltages (source values)
                - 'current_data': list of currents (readings)
                - 'error': error message if failed
        """
        smu = self._get_visa_resource()
        if not smu:
            return {
                'success': False,
                'voltage_data': [],
                'current_data': [],
                'error': 'SMU not connected'
            }
        
        try:
            # Save original timeout
            original_timeout = smu.timeout
            
            # Create a TSP script that formats output as comma-separated values
            # Format: n,reading1,reading2,...,readingN,source1,source2,...,sourceN
            fetch_script = """local n = defbuffer1.n
if n == 0 then
    print("EMPTY")
else
    -- Get readings and sourcevalues separately
    local readings_str = ""
    local source_str = ""
    for i = 1, n do
        if i > 1 then
            readings_str = readings_str .. ","
            source_str = source_str .. ","
        end
        readings_str = readings_str .. tostring(defbuffer1.readings[i])
        source_str = source_str .. tostring(defbuffer1.sourcevalues[i])
    end
    -- Print in format: n,readings,sourcevalues
    print(n .. "," .. readings_str .. "," .. source_str)
end"""
            
            # Ensure SCPI mode before sending script
            if not self._ensure_scpi_mode():
                smu.timeout = original_timeout
                return {
                    'success': False,
                    'voltage_data': [],
                    'current_data': [],
                    'error': 'Could not ensure SCPI mode'
                }
            
            # Send the fetch script with proper format
            # Build complete command block with \r\n line endings
            fetch_lines = fetch_script.strip().split('\n')
            formatted_fetch = '\r\n'.join(fetch_lines)
            fetch_command = f"loadscriptrun\r\n{formatted_fetch}\r\nendscript"
            
            # Send complete command as one block
            # Temporarily disable write termination
            original_write_termination = getattr(smu, 'write_termination', None)
            try:
                smu.write_termination = ''
                if hasattr(smu, 'write_raw'):
                    smu.write_raw(fetch_command.encode('utf-8') + b'\n')
                else:
                    smu.write(fetch_command + '\n')
            finally:
                if original_write_termination is not None:
                    smu.write_termination = original_write_termination
            
            # Wait for script to execute
            # Don't use *OPC? immediately as it might interfere with reading the output
            time.sleep(0.3)
            
            # Check for errors
            has_error, error_msg = self._check_system_error()
            if has_error:
                logger.warning(f"System error after fetch script: {error_msg}")
            
            # Read the result from print() output
            # Increase timeout for reading large buffers
            smu.timeout = 5000  # 5 seconds for reading
            try:
                result_str = smu.read().strip()
            except Exception as e:
                # If read() fails, try waiting a bit more and use *OPC? to ensure completion
                time.sleep(0.2)
                try:
                    smu.query("*OPC?")  # This ensures script completed
                    # Try reading again
                    result_str = smu.read().strip()
                except Exception as e2:
                    smu.timeout = original_timeout
                    return {
                        'success': False,
                        'voltage_data': [],
                        'current_data': [],
                        'error': f'Failed to read buffer data: {e}, {e2}'
                    }
            
            # Restore timeout
            smu.timeout = original_timeout
            
            # Check if buffer is empty
            if result_str == "EMPTY" or result_str == "0":
                return {
                    'success': True,
                    'voltage_data': [],
                    'current_data': [],
                    'error': None
                }
            
            # Parse the result
            # Format: n,reading1,reading2,...,readingN,source1,source2,...,sourceN
            parts = result_str.split(',')
            
            if len(parts) < 2:
                return {
                    'success': False,
                    'voltage_data': [],
                    'current_data': [],
                    'error': f'Invalid data format: {result_str}'
                }
            
            try:
                n = int(float(parts[0]))
                if n == 0:
                    return {
                        'success': True,
                        'voltage_data': [],
                        'current_data': [],
                        'error': None
                    }
                
                # Extract readings (current) and sourcevalues (voltage)
                # parts[1] to parts[n] are readings
                # parts[n+1] to parts[2*n] are sourcevalues
                if len(parts) < (1 + 2 * n):
                    return {
                        'success': False,
                        'voltage_data': [],
                        'current_data': [],
                        'error': f'Incomplete data: expected {1 + 2 * n} values, got {len(parts)}'
                    }
                
                current_data = [float(x) for x in parts[1:n+1]]
                voltage_data = [float(x) for x in parts[n+1:2*n+1]]
            except (ValueError, IndexError) as e:
                return {
                    'success': False,
                    'voltage_data': [],
                    'current_data': [],
                    'error': f'Error parsing buffer data: {e}, data: {result_str[:100]}'
                }
            
            # Check for errors
            esr = smu.query(self.tsp_scpi.event_status_register()).strip()
            if int(esr) != 0:
                logger.warning(f"Event status register indicates errors: {esr}")
            
            return {
                'success': True,
                'voltage_data': voltage_data,
                'current_data': current_data,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'voltage_data': [],
                'current_data': [],
                'error': f'Error fetching buffer data: {str(e)}'
            }
    
    def is_connected(self):
        """Check if underlying Keithley2450 is connected"""
        return self.keithley and self.keithley.connected and not self.keithley.simulation_mode

