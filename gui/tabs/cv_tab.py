"""
CV Tab - Cyclic Voltammetry measurement using TSP
"""

import customtkinter as ctk
from tkinter import PanedWindow, Frame, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import threading
import time
import os

from gui.tabs.base_tab import BaseTab
from experiments.experiment_types.cv_experiment import CVExperiment


class CVTab(BaseTab):
    """
    CV tab for Cyclic Voltammetry measurement using TSP
    """
    
    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None):
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        
        # CV-specific data arrays
        self.cv_voltage_data = []
        self.cv_current_data = []
        self.cv_time_data = []  # Time data for each measurement point
        self.cv_measurement_running = False
        self.cv_experiment = None
        
        # Create widgets
        self.create_widgets()
        
        # Setup graphs
        self.setup_graphs()
        
        # Refresh SMU status on startup
        self.after(1000, self.refresh_smu_status)
    
    def create_widgets(self):
        """Create CV tab widgets"""
        # Create PanedWindow for resizable panels
        paned = PanedWindow(self, orient='horizontal', sashwidth=8, sashrelief='raised', bg='#2b2b2b')
        paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left column container
        left_container = Frame(paned, bg='#1a1a1a')
        paned.add(left_container, minsize=300, width=400)
        
        # Left column - Scrollable
        left_frame = ctk.CTkScrollableFrame(left_container, width=400)
        left_frame.pack(fill='both', expand=True)
        
        # SMU Connection Status
        smu_status_frame = ctk.CTkFrame(left_frame)
        smu_status_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(smu_status_frame, text="Keithley 2450 SMU Status", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        smu_info_frame = ctk.CTkFrame(smu_status_frame)
        smu_info_frame.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(smu_info_frame, text='Status:', width=100).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.smu_status_label = ctk.CTkLabel(smu_info_frame, text='Checking...', width=250, anchor='w')
        self.smu_status_label.grid(row=0, column=1, padx=5, pady=2, sticky='w')
        
        ctk.CTkLabel(smu_info_frame, text='Device ID:', width=100).grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.smu_idn_label = ctk.CTkLabel(smu_info_frame, text='N/A', width=250, anchor='w', wraplength=250)
        self.smu_idn_label.grid(row=1, column=1, padx=5, pady=2, sticky='w')
        
        # Control buttons
        smu_btn_frame = ctk.CTkFrame(smu_status_frame)
        smu_btn_frame.pack(pady=5)
        self.create_blue_button(smu_btn_frame, text='🔍 Detect SMU', command=self.detect_smu, width=120, height=30).pack(side='left', padx=2)
        self.create_blue_button(smu_btn_frame, text='🔄 Refresh', command=self.refresh_smu_status, width=120, height=30).pack(side='left', padx=2)
        
        # CV Parameters
        params_frame = ctk.CTkFrame(left_frame)
        params_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(params_frame, text="CV Parameters", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        params_grid = ctk.CTkFrame(params_frame)
        params_grid.pack(fill='x', padx=5, pady=5)
        
        # Voltage vertices
        ctk.CTkLabel(params_grid, text='V1 (V):', width=120).grid(row=0, column=0, padx=5, pady=2)
        self.v1_entry = ctk.CTkEntry(params_grid, width=150)
        self.v1_entry.insert(0, '0.0')
        self.v1_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='V2 (V):', width=120).grid(row=1, column=0, padx=5, pady=2)
        self.v2_entry = ctk.CTkEntry(params_grid, width=150)
        self.v2_entry.insert(0, '1.0')
        self.v2_entry.grid(row=1, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='V3 (V):', width=120).grid(row=2, column=0, padx=5, pady=2)
        self.v3_entry = ctk.CTkEntry(params_grid, width=150)
        self.v3_entry.insert(0, '-1.0')
        self.v3_entry.grid(row=2, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='V4 (V):', width=120).grid(row=3, column=0, padx=5, pady=2)
        self.v4_entry = ctk.CTkEntry(params_grid, width=150)
        self.v4_entry.insert(0, '0.0')
        self.v4_entry.grid(row=3, column=1, padx=5, pady=2)
        
        # Points per second
        ctk.CTkLabel(params_grid, text='Points/Second:', width=120).grid(row=4, column=0, padx=5, pady=2)
        self.points_per_sec_entry = ctk.CTkEntry(params_grid, width=150)
        self.points_per_sec_entry.insert(0, '10')
        self.points_per_sec_entry.grid(row=4, column=1, padx=5, pady=2)
        
        # Current range
        ctk.CTkLabel(params_grid, text='Current Range (A):', width=120).grid(row=5, column=0, padx=5, pady=2)
        self.current_range_entry = ctk.CTkEntry(params_grid, width=150)
        self.current_range_entry.insert(0, '0.1')
        self.current_range_entry.grid(row=5, column=1, padx=5, pady=2)
        
        # Control buttons
        control_frame = ctk.CTkFrame(left_frame)
        control_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(control_frame, text="Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        btn_frame = ctk.CTkFrame(control_frame)
        btn_frame.pack(pady=5)
        self.create_blue_button(btn_frame, text='▶️ Run CV Sweep', command=self.run_cv_sweep, width=150, height=35).pack(pady=2)
        self.cv_stop_button = self.create_blue_button(btn_frame, text='⏹️ Stop', command=self.stop_cv_sweep, width=150, height=35,
                                                      fg_color='#0D47A1', hover_color='#0C3A7A', state='disabled')
        self.cv_stop_button.pack(pady=2)
        
        # Status
        status_frame = ctk.CTkFrame(left_frame)
        status_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(status_frame, text="Status", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        status_content = ctk.CTkFrame(status_frame)
        status_content.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(status_content, text='Status:', width=100).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.cv_status_label = ctk.CTkLabel(status_content, text='Ready', text_color='green', width=250)
        self.cv_status_label.grid(row=0, column=1, padx=5, pady=2, sticky='w')
        
        ctk.CTkLabel(status_content, text='Data Points:', width=100).grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.cv_points_label = ctk.CTkLabel(status_content, text='0', width=250)
        self.cv_points_label.grid(row=1, column=1, padx=5, pady=2, sticky='w')
        
        # Export
        export_frame = ctk.CTkFrame(left_frame)
        export_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(export_frame, text="Export", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        export_btn_frame = ctk.CTkFrame(export_frame)
        export_btn_frame.pack(pady=5)
        self.create_blue_button(export_btn_frame, text='Save Data', command=self.save_cv_data, width=120).pack(side='left', padx=2)
        self.create_blue_button(export_btn_frame, text='Export PNG', command=self.export_graph_png, width=120).pack(side='left', padx=2)
        
        # Right column container
        right_container = Frame(paned, bg='#1a1a1a')
        paned.add(right_container, minsize=400)
        
        # Right column - CV Graph
        right_frame = ctk.CTkFrame(right_container)
        right_frame.pack(fill='both', expand=True)
        
        graph_control_frame = ctk.CTkFrame(right_frame)
        graph_control_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(graph_control_frame, text="CV Characteristic", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        # Axis selection controls
        axis_frame = ctk.CTkFrame(graph_control_frame)
        axis_frame.pack(fill='x', padx=5, pady=5)
        
        axis_label_frame = ctk.CTkFrame(axis_frame)
        axis_label_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(axis_label_frame, text='X-Axis:', width=60).pack(side='left', padx=5)
        self.cv_x_axis_combo = ctk.CTkComboBox(
            axis_label_frame, 
            values=['Voltage', 'Current', 'Time'],
            width=150, 
            command=self.on_cv_axis_change
        )
        self.cv_x_axis_combo.set('Voltage')
        self.cv_x_axis_combo.pack(side='left', padx=5)
        
        ctk.CTkLabel(axis_label_frame, text='Y-Axis:', width=60).pack(side='left', padx=5)
        self.cv_y_axis_combo = ctk.CTkComboBox(
            axis_label_frame,
            values=['Voltage', 'Current'],
            width=150, 
            command=self.on_cv_axis_change
        )
        self.cv_y_axis_combo.set('Current')
        self.cv_y_axis_combo.pack(side='left', padx=5)
        
        # CV Graph frame
        self.cv_graph_frame = ctk.CTkFrame(right_frame)
        self.cv_graph_frame.pack(fill='both', expand=True, padx=10, pady=5)
    
    def setup_graphs(self):
        """Initialize CV graph"""
        self.cv_fig, self.cv_ax = plt.subplots(figsize=(8, 6))
        self.cv_ax.set_xlabel("Voltage (V)", color='black', fontsize=12)
        self.cv_ax.set_ylabel("Current (A)", color='black', fontsize=12)
        self.cv_ax.set_title("Cyclic Voltammetry", color='black', fontsize=14, fontweight='bold', pad=15)
        self.cv_ax.set_facecolor('white')
        self.cv_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.cv_ax.set_axisbelow(True)
        self.cv_ax.tick_params(colors='black', labelsize=10)
        for spine in self.cv_ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
        
        # Create canvas
        self.cv_canvas = FigureCanvasTkAgg(self.cv_fig, self.cv_graph_frame)
        self.cv_canvas.draw()
        self.cv_canvas.get_tk_widget().pack(side='top', fill='both', expand=1)
        
        # Add navigation toolbar
        self.cv_toolbar = NavigationToolbar2Tk(self.cv_canvas, self.cv_graph_frame)
        self.cv_toolbar.update()
    
    def detect_smu(self):
        """Detect and connect to Keithley 2450 SMU"""
        self.smu_status_label.configure(text="Scanning...", text_color='orange')
        threading.Thread(target=self._run_detect_smu_logic, daemon=True).start()
    
    def _run_detect_smu_logic(self):
        """Background thread for SMU detection"""
        try:
            detected_smu = self.hw_controller.auto_detect_smu()
            if detected_smu:
                if self.hw_controller.smu:
                    try:
                        self.hw_controller.smu.close()
                    except:
                        pass
                self.hw_controller.smu = detected_smu
                self.after(0, lambda: messagebox.showinfo('Success', 
                    f'Keithley 2450 SMU detected!\nResource: {detected_smu.resource_name}'))
                self.after(0, self.refresh_smu_status)
            else:
                self.after(0, lambda: messagebox.showwarning('Not Found', 
                    'Keithley 2450 SMU not found.'))
                self.after(0, lambda: self.smu_status_label.configure(text='✗ Not Connected', text_color='red'))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror('Error', f'Error detecting SMU: {str(e)}'))
            self.after(0, lambda: self.smu_status_label.configure(text='✗ Error', text_color='red'))
    
    def refresh_smu_status(self):
        """Refresh SMU connection status"""
        self.smu_status_label.configure(text="Checking...", text_color='orange')
        threading.Thread(target=self._run_refresh_smu_logic, daemon=True).start()
    
    def _run_refresh_smu_logic(self):
        """Background thread for SMU status refresh"""
        try:
            smu_info = self.hw_controller.get_smu_info()
            self.after(0, lambda: self._update_smu_ui(smu_info))
        except Exception as e:
            self.after(0, lambda: self._update_smu_error(str(e)))
    
    def _update_smu_ui(self, smu_info):
        """Update SMU UI"""
        if smu_info.get('connected', False):
            self.smu_status_label.configure(text='✓ Connected', text_color='green')
            self.smu_idn_label.configure(text=smu_info.get('idn', 'N/A'))
        else:
            self.smu_status_label.configure(text='✗ Not Connected', text_color='red')
            self.smu_idn_label.configure(text='N/A')
    
    def _update_smu_error(self, error_msg):
        """Update SMU UI with error"""
        self.smu_status_label.configure(text=f'Error: {error_msg[:30]}', text_color='orange')
    
    def run_cv_sweep(self):
        """Run CV sweep"""
        if self.cv_measurement_running:
            messagebox.showinfo('In Progress', 'CV measurement already running.')
            return
        
        try:
            # Get parameters
            v1 = float(self.v1_entry.get())
            v2 = float(self.v2_entry.get())
            v3 = float(self.v3_entry.get())
            v4 = float(self.v4_entry.get())
            points_per_second = float(self.points_per_sec_entry.get())
            current_range = float(self.current_range_entry.get())
            
            # Validate
            if points_per_second <= 0:
                messagebox.showerror('Error', 'Points per second must be positive.')
                return
            if current_range <= 0:
                messagebox.showerror('Error', 'Current range must be positive.')
                return
            
            # Check SMU connection
            if not self.hw_controller.smu or not self.hw_controller.smu.connected:
                messagebox.showerror('Error', 'SMU not connected. Please detect SMU first.')
                return
            
            # Clear previous data
            self.cv_voltage_data.clear()
            self.cv_current_data.clear()
            self.cv_time_data.clear()
            
            # Update UI
            self.cv_measurement_running = True
            self.cv_stop_button.configure(state='normal')
            self.cv_status_label.configure(text='Running...', text_color='orange')
            self.cv_points_label.configure(text='0')
            
            # Run in background thread
            threading.Thread(
                target=self._run_cv_sweep_thread,
                args=(v1, v2, v3, v4, points_per_second, current_range),
                daemon=True
            ).start()
            
        except ValueError:
            messagebox.showerror('Error', 'Invalid parameter values. Please enter numbers.')
        except Exception as e:
            messagebox.showerror('Error', f'Error starting CV sweep: {e}')
    
    def _run_cv_sweep_thread(self, v1, v2, v3, v4, points_per_second, current_range):
        """Background thread for CV sweep"""
        try:
            # Record start time for time data calculation
            sweep_start_time = time.time()
            
            # Create CV experiment
            self.cv_experiment = CVExperiment(self.hw_controller, self.data_handler)
            
            # Run experiment
            self.cv_experiment.run(v1, v2, v3, v4, points_per_second, current_range)
            
            # Get data from experiment instance
            if self.cv_experiment and hasattr(self.cv_experiment, 'voltage_data') and hasattr(self.cv_experiment, 'current_data'):
                self.cv_voltage_data = self.cv_experiment.voltage_data.copy()
                self.cv_current_data = self.cv_experiment.current_data.copy()
                
                # Calculate time data: time elapsed from start for each point
                # Time can be calculated as index / points_per_second or from actual elapsed time
                # We'll use index-based time for consistency
                self.cv_time_data = []
                if points_per_second > 0:
                    for i in range(len(self.cv_voltage_data)):
                        time_elapsed = i / points_per_second
                        self.cv_time_data.append(time_elapsed)
                else:
                    # Fallback: use actual elapsed time if points_per_second is invalid
                    for i in range(len(self.cv_voltage_data)):
                        time_elapsed = time.time() - sweep_start_time
                        self.cv_time_data.append(time_elapsed)
                
                # Update UI
                self.after(0, lambda: self._update_cv_graph())
                self.after(0, lambda: self.cv_points_label.configure(text=str(len(self.cv_voltage_data))))
                self.after(0, lambda: self.cv_status_label.configure(text='Completed', text_color='green'))
            else:
                # Fallback: try to read from data_handler if experiment doesn't have data
                from utils.logger_config import get_logger
                logger = get_logger(__name__)
                logger.warning("Experiment completed but no data found in experiment instance")
                self.after(0, lambda: self.cv_status_label.configure(text='Completed (no data)', text_color='orange'))
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror('Error', f'CV sweep error: {e}'))
            self.after(0, lambda: self.cv_status_label.configure(text='Error', text_color='red'))
        finally:
            self.cv_measurement_running = False
            self.after(0, lambda: self.cv_stop_button.configure(state='disabled'))
    
    def stop_cv_sweep(self):
        """Stop CV sweep"""
        if self.cv_experiment:
            self.cv_experiment.stop()
        self.cv_measurement_running = False
        self.cv_stop_button.configure(state='disabled')
        self.cv_status_label.configure(text='Stopped', text_color='orange')
    
    def on_cv_axis_change(self, *args):
        """Handle CV axis selection change"""
        x_axis_type = self.cv_x_axis_combo.get()
        y_axis_type = self.cv_y_axis_combo.get()
        self.plot_cv_xy_graph(x_axis_type, y_axis_type)
    
    def plot_cv_xy_graph(self, x_axis_type, y_axis_type):
        """Plot CV graph with selected axes"""
        self.cv_ax.clear()
        
        # Select data based on axis types
        x_data = []
        y_data = []
        xlabel = ""
        ylabel = ""
        title = ""
        
        if x_axis_type == 'Voltage':
            x_data = self.cv_voltage_data
            xlabel = "Voltage (V)"
        elif x_axis_type == 'Current':
            x_data = self.cv_current_data
            xlabel = "Current (A)"
        elif x_axis_type == 'Time':
            x_data = self.cv_time_data
            xlabel = "Time (s)"
        
        if y_axis_type == 'Voltage':
            y_data = self.cv_voltage_data
            ylabel = "Voltage (V)"
        elif y_axis_type == 'Current':
            y_data = self.cv_current_data
            ylabel = "Current (A)"
        
        # Determine title based on axis combination
        if x_axis_type == 'Voltage' and y_axis_type == 'Current':
            title = "Cyclic Voltammetry (I-V)"
        elif x_axis_type == 'Current' and y_axis_type == 'Voltage':
            title = "Cyclic Voltammetry (V-I)"
        elif x_axis_type == 'Time' and y_axis_type == 'Voltage':
            title = "Voltage vs Time"
        elif x_axis_type == 'Time' and y_axis_type == 'Current':
            title = "Current vs Time"
        else:
            title = f"{y_axis_type} vs {x_axis_type}"
        
        # Plot the data
        if len(x_data) > 0 and len(y_data) > 0 and len(x_data) == len(y_data):
            self.cv_ax.plot(x_data, y_data, color='#C73E1D', linewidth=2.5, alpha=0.85)
        
        # Formatting
        self.cv_ax.set_facecolor('white')
        self.cv_ax.set_xlabel(xlabel, color='black', fontsize=12)
        self.cv_ax.set_ylabel(ylabel, color='black', fontsize=12)
        self.cv_ax.set_title(title, color='black', fontsize=14, fontweight='bold', pad=15)
        self.cv_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.cv_ax.set_axisbelow(True)
        self.cv_ax.tick_params(colors='black', labelsize=10)
        for spine in self.cv_ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
        
        # Set axis limits
        if len(x_data) > 0 and len(y_data) > 0:
            x_margin = (max(x_data) - min(x_data)) * 0.05 if max(x_data) > min(x_data) else 1
            y_margin = (max(y_data) - min(y_data)) * 0.1 if max(y_data) > min(y_data) else 1
            self.cv_ax.set_xlim(min(x_data) - x_margin, max(x_data) + x_margin)
            self.cv_ax.set_ylim(min(y_data) - y_margin, max(y_data) + y_margin)
        
        self.cv_fig.tight_layout(pad=2.0)
        self.cv_canvas.draw()
    
    def _update_cv_graph(self):
        """Update CV graph with current data - uses selected axes"""
        x_axis_type = self.cv_x_axis_combo.get()
        y_axis_type = self.cv_y_axis_combo.get()
        self.plot_cv_xy_graph(x_axis_type, y_axis_type)
    
    def save_cv_data(self):
        """Save CV data to file"""
        try:
            if not self.cv_voltage_data or not self.cv_current_data:
                messagebox.showwarning('No Data', 'No CV data to save.')
                return
            
            filename = filedialog.asksaveasfilename(
                defaultextension='.csv',
                filetypes=[('CSV Files', '*.csv'), ('All Files', '*.*')]
            )
            if filename:
                import csv
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Voltage (V)', 'Current (A)'])
                    for v, i in zip(self.cv_voltage_data, self.cv_current_data):
                        writer.writerow([v, i])
                messagebox.showinfo('Success', f'CV data saved to {filename}')
        except Exception as e:
            messagebox.showerror('Error', f'Error saving CV data: {e}')
    
    def export_graph_png(self):
        """Export CV graph as PNG"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension='.png',
                filetypes=[('PNG Files', '*.png')]
            )
            if filename:
                self.cv_fig.savefig(filename, dpi=300, bbox_inches='tight')
                messagebox.showinfo('Success', f'Graph exported to {filename}')
        except Exception as e:
            messagebox.showerror('Error', f'Error exporting graph: {e}')

