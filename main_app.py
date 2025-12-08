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
from gui.tabs.iv_program_tab import IVProgramTab

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
        
        # Flag to stop periodic callbacks
        self.is_closing = False
        self.check_update_job = None
        self.sensor_update_job = None
        self.smu_refresh_job = None
        # Track all after() callbacks for cleanup
        self.pending_callbacks = []
        
        # Initialize hardware components
        # Let the system auto-detect the Keithley device
        self.hw_controller = HardwareController(
            pump_port='COM3', 
            mc_board_num=0,  # MCusb-1408FS-Plus board number (default 0)
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
        # BUG FIX #5: Better check for tab instance existence
        if hasattr(self, 'iv_tab_instance') and self.iv_tab_instance is not None:
            try:
                self.smu_refresh_job = self.after(500, self.iv_tab_instance.refresh_smu_status)
                if self.smu_refresh_job:
                    self.pending_callbacks.append(self.smu_refresh_job)
            except (AttributeError, RuntimeError) as e:
                print(f"Warning: Could not refresh SMU status on startup: {e}")
        
        # Set up window close handler
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
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
        
        iv_program_tab_frame = self.tabview.add("Write Program IV")
        self.iv_program_tab_instance = IVProgramTab(
            iv_program_tab_frame,
            self.hw_controller,
            self.data_handler,
            self.exp_manager,
            self.update_queue
        )
        self.iv_program_tab_instance.pack(fill='both', expand=True)
        
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
        if self.is_closing:
            return
        try:
            while True:
                update_type, data = self.update_queue.get_nowait()
                
                # Route updates to appropriate tabs
                if update_type in ['UPDATE_GRAPH1', 'UPDATE_GRAPH2', 'UPDATE_GRAPH3', 'UPDATE_GRAPH4']:
                    # Main tab graph updates
                    if hasattr(self, 'main_tab_instance') and self.main_tab_instance is not None:
                        try:
                            x, y = data
                            print(f"[MAIN_APP] Received {update_type}: {len(x) if x else 0} x points, {len(y) if y else 0} y points")
                            # BUG FIX #1: Thread-safe update of data arrays with lock
                            with self.main_tab_instance.data_lock:
                                # Update the data arrays first
                                if update_type == 'UPDATE_GRAPH1':
                                    self.main_tab_instance.flow_x_data = list(x) if x else []
                                    self.main_tab_instance.flow_y_data = list(y) if y else []
                                    print(f"[MAIN_APP] Updated flow data: {len(self.main_tab_instance.flow_x_data)} points")
                                elif update_type == 'UPDATE_GRAPH2':
                                    self.main_tab_instance.pressure_x_data = list(x) if x else []
                                    self.main_tab_instance.pressure_y_data = list(y) if y else []
                                    print(f"[MAIN_APP] Updated pressure data: {len(self.main_tab_instance.pressure_x_data)} points")
                                elif update_type == 'UPDATE_GRAPH3':
                                    self.main_tab_instance.temp_x_data = list(x) if x else []
                                    self.main_tab_instance.temp_y_data = list(y) if y else []
                                elif update_type == 'UPDATE_GRAPH4':
                                    self.main_tab_instance.level_x_data = list(x) if x else []
                                    self.main_tab_instance.level_y_data = list(y) if y else []
                            
                            # Update graphs based on current mode
                            graph_mode = self.main_tab_instance.graph_mode_var.get()
                            print(f"[MAIN_APP] Graph mode: {graph_mode}")
                            if graph_mode == "multi":
                                print(f"[MAIN_APP] Calling update_multi_panel_graphs()")
                                self.main_tab_instance.update_multi_panel_graphs()
                            else:
                                # For single graph mode, update with current axis selection
                                x_axis_type = self.main_tab_instance.x_axis_combo.get()
                                y_axis_type = self.main_tab_instance.y_axis_combo.get()
                                print(f"[MAIN_APP] Calling plot_xy_graph({x_axis_type}, {y_axis_type})")
                                self.main_tab_instance.plot_xy_graph(x_axis_type, y_axis_type, [], [])
                            
                            # Update statistics
                            self.main_tab_instance.update_statistics()
                            print(f"[MAIN_APP] Graph update completed")
                        except Exception as e:
                            print(f"[MAIN_APP ERROR] Error updating graphs: {e}")
                            import traceback
                            traceback.print_exc()
                
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
                        elif update_type == 'UPDATE_MCUSB_CH0':
                            # MCusb channel 0 reading update
                            voltage = data
                            self.iv_tab_instance.mcusb_ch0_label.configure(
                                text=f'{voltage:.4f} V', text_color='green')
                
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
            # Schedule next check (only if not closing)
            if not self.is_closing:
                self.check_update_job = self.after(100, self.check_update_queue)
                if self.check_update_job:
                    self.pending_callbacks.append(self.check_update_job)
    
    def update_sensor_readings(self):
        """Periodically update sensor readings"""
        if self.is_closing:
            return
        if not self.exp_manager.is_running:
            try:
                pressure = self.hw_controller.read_pressure_sensor()
                temperature = self.hw_controller.read_temperature_sensor()
                pump_data = self.hw_controller.read_pump_data()
                level = self.hw_controller.read_level_sensor()
                
                self.update_queue.put(('UPDATE_READINGS', (pressure, temperature, pump_data['flow'], level * 100)))
            except Exception as e:
                print(f"Error reading sensors: {e}")
        
        # Schedule next update (only if not closing)
        if not self.is_closing:
            self.sensor_update_job = self.after(1000, self.update_sensor_readings)
            if self.sensor_update_job:
                self.pending_callbacks.append(self.sensor_update_job)
    
    def on_closing(self):
        """Handle window close event - cleanup all resources"""
        print("Application closing...")
        self.is_closing = True
        
        # Cancel ALL scheduled callbacks
        try:
            # Cancel tracked callbacks
            if self.check_update_job:
                try:
                    self.after_cancel(self.check_update_job)
                except:
                    pass
                self.check_update_job = None
            if self.sensor_update_job:
                try:
                    self.after_cancel(self.sensor_update_job)
                except:
                    pass
                self.sensor_update_job = None
            if self.smu_refresh_job:
                try:
                    self.after_cancel(self.smu_refresh_job)
                except:
                    pass
                self.smu_refresh_job = None
            
            # Cancel all pending callbacks
            for callback_id in self.pending_callbacks:
                try:
                    self.after_cancel(callback_id)
                except:
                    pass
            self.pending_callbacks.clear()
            
            # Try to cancel any remaining after() callbacks by checking common IDs
            # This is a workaround for CustomTkinter internal callbacks
            try:
                # Update to process any pending events before destroying
                self.update_idletasks()
            except:
                pass
        except Exception as e:
            print(f"Error cancelling scheduled callbacks: {e}")
        
        # Stop all running experiments
        try:
            self.exp_manager.stop_experiment()
            self.exp_manager.finish_experiment()
        except Exception as e:
            print(f"Error stopping experiments: {e}")
        
        # Close data file if open
        try:
            if self.data_handler.file_path:
                self.data_handler.close_file()
        except Exception as e:
            print(f"Error closing data file: {e}")
        
        # Cleanup hardware connections
        try:
            self.hw_controller.cleanup()
        except Exception as e:
            print(f"Error cleaning up hardware: {e}")
        
        # Cleanup tabs
        try:
            if hasattr(self, 'main_tab_instance'):
                self.main_tab_instance.cleanup()
            if hasattr(self, 'iv_tab_instance'):
                self.iv_tab_instance.cleanup()
            if hasattr(self, 'program_tab_instance'):
                self.program_tab_instance.cleanup()
            if hasattr(self, 'browser_tab_instance'):
                self.browser_tab_instance.cleanup()
            if hasattr(self, 'scheduler_tab_instance'):
                self.scheduler_tab_instance.cleanup()
        except Exception as e:
            print(f"Error cleaning up tabs: {e}")
        
        # Destroy window and quit mainloop
        print("Application closed.")
        import os
        
        try:
            # First, quit the mainloop to stop processing events
            self.quit()
        except Exception as e:
            print(f"Error quitting mainloop: {e}")
        
        try:
            # Then destroy the window
            self.destroy()
        except Exception as e:
            print(f"Error destroying window: {e}")
        
        # Force exit to ensure process terminates immediately
        # This prevents CustomTkinter internal callbacks from causing errors
        # os._exit() terminates immediately without running cleanup handlers
        # (We've already done all cleanup above)
        os._exit(0)


# --- Main Application Loop ---
def main():
    app = FluidicControlApp()
    app.mainloop()


if __name__ == "__main__":
    main()
