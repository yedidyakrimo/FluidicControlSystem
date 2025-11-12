"""
Base class for all GUI tabs
"""

import customtkinter as ctk


class BaseTab(ctk.CTkFrame):
    """
    Base class for all tabs
    Provides common functionality and interface
    """
    
    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None):
        """
        Initialize base tab
        
        Args:
            parent: Parent widget
            hw_controller: Hardware controller instance
            data_handler: Data handler instance
            exp_manager: Experiment manager instance
            update_queue: Queue for thread-safe GUI updates
        """
        super().__init__(parent)
        self.hw_controller = hw_controller
        self.data_handler = data_handler
        self.exp_manager = exp_manager
        self.update_queue = update_queue
        
        # Common data arrays
        self.flow_x_data, self.flow_y_data = [], []
        self.pressure_x_data, self.pressure_y_data = [], []
        self.temp_x_data, self.temp_y_data = [], []
        self.level_x_data, self.level_y_data = [], []
    
    def create_widgets(self):
        """
        Create tab widgets
        Must be implemented by subclasses
        """
        raise NotImplementedError("Subclass must implement create_widgets()")
    
    def update_data(self):
        """
        Update tab data
        Can be overridden by subclasses
        """
        pass
    
    def cleanup(self):
        """
        Cleanup when tab is closed
        Can be overridden by subclasses
        """
        pass

