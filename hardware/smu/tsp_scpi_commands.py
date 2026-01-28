"""
TSP-related SCPI commands for Keithley 2450
Separate from existing scpi_commands.py to maintain isolation
"""


class TSPSCPICommands:
    """
    Collection of TSP-related SCPI commands for Keithley 2450 SMU
    All commands are static methods for easy access
    """
    
    # --- TSP Script Loading and Execution ---
    @staticmethod
    def loadscript(script_name):
        """
        Load a TSP script from file
        
        Args:
            script_name: Name of script file to load
        """
        return f"loadscript {script_name}"
    
    @staticmethod
    def loadscriptrun(script_content):
        """
        Load and run TSP script from string content
        
        Note: This command expects the script content to be sent
        as a multi-line string. The actual implementation will
        handle the script content separately.
        """
        return "loadscriptrun"
    
    @staticmethod
    def script_delete(script_name):
        """Delete a TSP script"""
        return f"script.delete(\"{script_name}\")"
    
    @staticmethod
    def script_run(script_name):
        """Run a loaded TSP script"""
        return f"script.run(\"{script_name}\")"
    
    # --- Buffer Operations ---
    # Note: These are Lua functions that need to be executed via SCPI
    # The proper way is to use printbuffer() Lua function directly
    @staticmethod
    def printbuffer(start_index, end_index, buffer_name="defbuffer1"):
        """
        Print buffer data using Lua printbuffer function
        This returns the Lua command that will be executed via SCPI
        
        Args:
            start_index: Start index (1-based)
            end_index: End index (1-based)
            buffer_name: Buffer name (default: defbuffer1)
        """
        # printbuffer is a Lua function: printbuffer(start, end, buffer.readings, buffer.sourcevalues)
        return f"printbuffer({start_index}, {end_index}, {buffer_name}.readings, {buffer_name}.sourcevalues)"
    
    @staticmethod
    def printbuffer_readings(start_index, end_index, buffer_name="defbuffer1"):
        """
        Print buffer readings (measured values) using Lua printbuffer
        This returns the Lua command that will be executed via SCPI
        
        Args:
            start_index: Start index (1-based)
            end_index: End index (1-based)
            buffer_name: Buffer name (default: defbuffer1)
        """
        # printbuffer for readings only
        return f"printbuffer({start_index}, {end_index}, {buffer_name}.readings)"
    
    @staticmethod
    def printbuffer_source(start_index, end_index, buffer_name="defbuffer1"):
        """
        Print buffer source values using Lua printbuffer
        This returns the Lua command that will be executed via SCPI
        
        Args:
            start_index: Start index (1-based)
            end_index: End index (1-based)
            buffer_name: Buffer name (default: defbuffer1)
        """
        # printbuffer for source values only
        return f"printbuffer({start_index}, {end_index}, {buffer_name}.sourcevalues)"
    
    @staticmethod
    def buffer_clear(buffer_name="defbuffer1"):
        """
        Clear buffer using Lua
        This returns the Lua command that will be executed via SCPI
        """
        return f"{buffer_name}.clear()"
    
    @staticmethod
    def buffer_n(buffer_name="defbuffer1"):
        """
        Query number of readings in buffer using Lua
        This returns the Lua command that will be executed via SCPI
        """
        # Return Lua expression to get buffer size
        return f"print({buffer_name}.n)"
    
    # --- Operation Complete ---
    @staticmethod
    def operation_complete():
        """Query operation complete status"""
        return "*OPC?"
    
    # --- Error Status ---
    @staticmethod
    def event_status_register():
        """Query event status register"""
        return "*ESR?"
    
    @staticmethod
    def standard_event_status():
        """Query standard event status"""
        return "*STB?"
    
    # --- System Error Query ---
    @staticmethod
    def system_error():
        """Query system error (returns error code and message)"""
        return "SYST:ERR?"
    
    # --- Language/Command Set ---
    @staticmethod
    def set_language_scpi():
        """Set command language to SCPI"""
        return "*LANG SCPI"
    
    @staticmethod
    def query_language():
        """Query current command language"""
        return "*LANG?"

