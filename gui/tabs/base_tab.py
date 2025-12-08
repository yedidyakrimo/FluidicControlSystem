"""
Base class for all GUI tabs
"""

import customtkinter as ctk
import threading


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
        
        # Lock for thread-safe access to data arrays (BUG FIX #1: Race Conditions)
        self.data_lock = threading.Lock()

        # Shared button style
        self.BLUE_BUTTON_FG = '#1E88E5'
        self.BLUE_BUTTON_HOVER = '#1565C0'
    
    def create_blue_button(self, parent, **kwargs):
        """Helper that applies the standardized blue button palette."""
        kwargs.setdefault('fg_color', self.BLUE_BUTTON_FG)
        kwargs.setdefault('hover_color', self.BLUE_BUTTON_HOVER)
        return ctk.CTkButton(parent, **kwargs)
    
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

