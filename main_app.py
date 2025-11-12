# main_app.py

import customtkinter as ctk
from tkinter import filedialog, messagebox
from hardware.hardware_controller import HardwareController
from experiments.experiment_manager import ExperimentManager
from data_handler import DataHandler
import queue

# Import new tab modules
from gui.tabs.main_tab import MainTab
from gui.tabs.iv_tab import IVTab
from gui.tabs.program_tab import ProgramTab
from gui.tabs.browser_tab import BrowserTab
from gui.tabs.scheduler_tab import SchedulerTab

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- Main Application Class ---
class FluidicControlApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title('Fluidic Control System')
        self.geometry('1400x900')
        
        # Queue for thread-safe GUI updates
        self.update_queue = queue.Queue()
        
        # Initialize hardware components
        # Let the system auto-detect the Keithley device
        self.hw_controller = HardwareController(
            pump_port='COM3', 
            ni_device_name='Dev1', 
            smu_resource=None  # Auto-detect Keithley 2450
        )
        self.data_handler = DataHandler()
        self.exp_manager = ExperimentManager(self.hw_controller, self.data_handler)
        
        # Create UI
        self.create_widgets()
        
        # Start periodic update check
        self.check_update_queue()
        
        # Start sensor reading loop
        self.update_sensor_readings()
        
        # Refresh SMU status on startup (if IV tab exists)
        if hasattr(self, 'iv_tab_instance'):
            self.after(500, self.iv_tab_instance.refresh_smu_status)
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Create tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs using new tab modules
        main_tab_frame = self.tabview.add("Main")
        self.main_tab_instance = MainTab(
            main_tab_frame, 
            self.hw_controller, 
            self.data_handler, 
            self.exp_manager, 
            self.update_queue
        )
        self.main_tab_instance.pack(fill='both', expand=True)
        
        iv_tab_frame = self.tabview.add("IV")
        self.iv_tab_instance = IVTab(
            iv_tab_frame, 
            self.hw_controller, 
            self.data_handler, 
            self.exp_manager, 
            self.update_queue
        )
        self.iv_tab_instance.pack(fill='both', expand=True)
        
        program_tab_frame = self.tabview.add("Write program")
        self.program_tab_instance = ProgramTab(
            program_tab_frame, 
            self.hw_controller, 
            self.data_handler, 
            self.exp_manager, 
            self.update_queue
        )
        self.program_tab_instance.pack(fill='both', expand=True)
        
        browser_tab_frame = self.tabview.add("Experiment Browser")
        self.browser_tab_instance = BrowserTab(
            browser_tab_frame, 
            self.hw_controller, 
            self.data_handler, 
            self.exp_manager, 
            self.update_queue
        )
        self.browser_tab_instance.pack(fill='both', expand=True)
        
        scheduler_tab_frame = self.tabview.add("Scheduler")
        self.scheduler_tab_instance = SchedulerTab(
            scheduler_tab_frame, 
            self.hw_controller, 
            self.data_handler, 
            self.exp_manager, 
            self.update_queue
        )
        self.scheduler_tab_instance.pack(fill='both', expand=True)
    
    def check_update_queue(self):
        """Check for thread-safe GUI updates and route to appropriate tabs"""
        try:
            while True:
                update_type, data = self.update_queue.get_nowait()
                
                # Route updates to appropriate tabs
                if update_type in ['UPDATE_GRAPH1', 'UPDATE_GRAPH2', 'UPDATE_GRAPH3', 'UPDATE_GRAPH4']:
                    # Main tab graph updates
                    if hasattr(self, 'main_tab_instance'):
                        x, y = data
                        if update_type == 'UPDATE_GRAPH1':
                            self.main_tab_instance.flow_x_data = list(x)
                            self.main_tab_instance.flow_y_data = list(y)
                        elif update_type == 'UPDATE_GRAPH2':
                            self.main_tab_instance.pressure_x_data = list(x)
                            self.main_tab_instance.pressure_y_data = list(y)
                        elif update_type == 'UPDATE_GRAPH3':
                            self.main_tab_instance.temp_x_data = list(x)
                            self.main_tab_instance.temp_y_data = list(y)
                        elif update_type == 'UPDATE_GRAPH4':
                            self.main_tab_instance.level_x_data = list(x)
                            self.main_tab_instance.level_y_data = list(y)
                        
                        # Update graphs
                        if self.main_tab_instance.graph_mode_var.get() == "multi":
                            self.main_tab_instance.update_multi_panel_graphs()
                        else:
                            self.main_tab_instance.on_axis_change()
                        self.main_tab_instance.update_statistics()
                
                elif update_type in ['UPDATE_IV_GRAPH', 'UPDATE_IV_STATUS', 'UPDATE_IV_FILE', 
                                     'UPDATE_IV_STATUS_BAR', 'UPDATE_IV_TIME_GRAPH']:
                    # IV tab updates
                    if hasattr(self, 'iv_tab_instance'):
                        if update_type == 'UPDATE_IV_GRAPH':
                            x, y = data
                            self.iv_tab_instance.update_iv_graph(x, y)
                            self.iv_tab_instance.update_iv_statistics()
                            # Update current readings with last point
                            if len(x) > 0 and len(y) > 0:
                                last_v = x[-1]
                                last_i = y[-1]
                                resistance = last_v / last_i if last_i != 0 else float('inf')
                                self.iv_tab_instance.iv_voltage_label.configure(
                                    text=self.iv_tab_instance.format_value_with_unit(last_v, 'voltage'))
                                self.iv_tab_instance.iv_current_label.configure(
                                    text=self.iv_tab_instance.format_value_with_unit(last_i, 'current'))
                                if resistance != float('inf'):
                                    self.iv_tab_instance.iv_resistance_label.configure(
                                        text=self.iv_tab_instance.format_value_with_unit(resistance, 'resistance'))
                                else:
                                    self.iv_tab_instance.iv_resistance_label.configure(text="∞")
                        elif update_type == 'UPDATE_IV_STATUS':
                            text, color = data
                            self.iv_tab_instance.iv_status_label.configure(text=text, text_color=color)
                        elif update_type == 'UPDATE_IV_FILE':
                            self.iv_tab_instance.iv_file_label.configure(text=data)
                        elif update_type == 'UPDATE_IV_STATUS_BAR':
                            self.iv_tab_instance.iv_status_bar.configure(text=data)
                        elif update_type == 'UPDATE_IV_TIME_GRAPH':
                            x_axis_type = self.iv_tab_instance.iv_x_axis_combo.get()
                            y_axis_type = self.iv_tab_instance.iv_y_axis_combo.get()
                            self.iv_tab_instance.plot_iv_xy_graph(x_axis_type, y_axis_type)
                
                elif update_type in ['UPDATE_STATUS', 'UPDATE_RECORDING_STATUS', 'UPDATE_FILE', 'UPDATE_READINGS']:
                    # Main tab status updates
                    if hasattr(self, 'main_tab_instance'):
                        if update_type == 'UPDATE_STATUS':
                            self.main_tab_instance.status_bar.configure(text=data)
                        elif update_type == 'UPDATE_RECORDING_STATUS':
                            text, color = data
                            self.main_tab_instance.recording_status_label.configure(text=text, text_color=color)
                        elif update_type == 'UPDATE_FILE':
                            self.main_tab_instance.current_file_label.configure(text=data)
                        elif update_type == 'UPDATE_READINGS':
                            pressure, temp, flow, level = data
                            self.main_tab_instance.pressure_label.configure(text=f"{pressure:.2f} PSI")
                            self.main_tab_instance.temp_label.configure(text=f"{temp:.2f} °C")
                            self.main_tab_instance.flow_label.configure(text=f"{flow:.2f} ml/min")
                            self.main_tab_instance.level_label.configure(text=f"{level:.2f} %")
                
                elif update_type == 'UPDATE_PROGRAM_STATUS':
                    # Program tab status updates
                    if hasattr(self, 'program_tab_instance'):
                        self.program_tab_instance.program_status_label.configure(text=data)
                        
        except queue.Empty:
            pass
        finally:
            # Schedule next check
            self.after(100, self.check_update_queue)
    
    def update_sensor_readings(self):
        """Periodically update sensor readings"""
        if not self.exp_manager.is_running:
            try:
                pressure = self.hw_controller.read_pressure_sensor()
                temperature = self.hw_controller.read_temperature_sensor()
                pump_data = self.hw_controller.read_pump_data()
                level = self.hw_controller.read_level_sensor()
                
                self.update_queue.put(('UPDATE_READINGS', (pressure, temperature, pump_data['flow'], level * 100)))
            except Exception as e:
                print(f"Error reading sensors: {e}")
        
        # Schedule next update
        self.after(1000, self.update_sensor_readings)


# --- Main Application Loop ---
def main():
    app = FluidicControlApp()
    app.mainloop()


if __name__ == "__main__":
    main()
