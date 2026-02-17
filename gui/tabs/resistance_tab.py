"""
Resistance Tab - Main tab functionality plus bias voltage, current measurement,
and resistance R = V/I (Ohm's law), with resistance displayed in graphs.
"""

import customtkinter as ctk
from tkinter import Frame
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import threading
import time
import os

from gui.tabs.main_tab import MainTab
from utils.logger_config import get_logger

logger = get_logger(__name__)


class ResistanceTab(MainTab):
    """
    Tab with full Main tab functionality plus resistance measurement:
    set bias voltage, measure current, compute R = V/I, show resistance in graphs.
    """

    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None):
        # Must set before super().__init__() because setup_graphs() -> update_multi_panel_graphs() uses them
        self.resistance_time_data = []
        self.resistance_y_data = []
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        # Inject resistance UI and add "Resistance" to axis combos (after super created widgets)
        self._add_resistance_ui()
        self._add_resistance_to_axis_combos()

    def _add_resistance_ui(self):
        """Add 'Resistance Measurement' block to the left column (after super().create_widgets())."""
        try:
            paned = self.winfo_children()[0]
            left_container = paned.winfo_children()[0]
            left_frame = left_container.winfo_children()[0]
        except IndexError:
            logger.warning("Could not find left_frame for resistance UI")
            return
        resistance_frame = ctk.CTkFrame(left_frame)
        # CTkScrollableFrame uses grid internally; use grid to avoid "pack inside grid" error
        resistance_frame.grid(row=20, column=0, sticky='ew', pady=5)
        ctk.CTkLabel(resistance_frame, text="Resistance Measurement", font=('Helvetica', 14, 'bold')).pack(pady=5)
        grid_frame = ctk.CTkFrame(resistance_frame)
        grid_frame.pack(fill='x', padx=5, pady=5)
        ctk.CTkLabel(grid_frame, text='Bias Voltage (V):', width=120).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.resistance_bias_label = ctk.CTkLabel(grid_frame, text='—', width=120)
        self.resistance_bias_label.grid(row=0, column=1, padx=5, pady=2, sticky='w')
        ctk.CTkLabel(grid_frame, text='Current (A):', width=120).grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.resistance_current_label = ctk.CTkLabel(grid_frame, text='—', width=120)
        self.resistance_current_label.grid(row=1, column=1, padx=5, pady=2, sticky='w')
        ctk.CTkLabel(grid_frame, text='Resistance R (Ω):', width=120).grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.resistance_r_label = ctk.CTkLabel(grid_frame, text='—', width=120)
        self.resistance_r_label.grid(row=2, column=1, padx=5, pady=2, sticky='w')

    def _add_resistance_to_axis_combos(self):
        """Add 'Resistance' to X and Y axis combo values."""
        self.x_axis_combo.configure(
            values=['Time', 'Flow Rate', 'Pressure', 'Temperature', 'Level', 'Voltage', 'Current', 'Resistance']
        )
        self.y_axis_combo.configure(
            values=['Flow Rate', 'Pressure', 'Temperature', 'Level', 'Voltage', 'Current', 'Resistance']
        )

    def setup_graphs(self):
        """Initialize matplotlib graphs: 4-panel multi (Voltage, Current, Flow, Resistance) + single X-Y."""
        # Multi-panel: 1x4 (Voltage, Current, Flow, Resistance)
        self.multi_fig, (self.voltage_ax, self.current_ax, self.flow_ax, self.resistance_ax) = plt.subplots(
            1, 4, figsize=(18, 5)
        )
        graphs_config = [
            (self.voltage_ax, 'Voltage', 'Voltage (V)', '#2E86AB'),
            (self.current_ax, 'Current', 'Current (A)', '#A23B72'),
            (self.flow_ax, 'Flow Rate', 'Flow Rate (ml/min)', '#F18F01'),
            (self.resistance_ax, 'Resistance', 'Resistance (Ω)', '#2E7D32'),
        ]
        for ax, title, ylabel, color in graphs_config:
            ax.set_xlabel("Time (s)", color='black', fontsize=10)
            ax.set_ylabel(ylabel, color='black', fontsize=10)
            ax.set_title(title, color='black', fontsize=12, fontweight='bold', pad=10)
            ax.set_facecolor('white')
            ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
            ax.set_axisbelow(True)
            ax.tick_params(colors='black', labelsize=9)
            for spine in ax.spines.values():
                spine.set_color('black')
                spine.set_linewidth(1)
        self.multi_canvas = FigureCanvasTkAgg(self.multi_fig, self.multi_graph_frame)
        self.multi_canvas.draw()
        self.multi_canvas.get_tk_widget().pack(side='top', fill='both', expand=1)
        self.multi_toolbar = NavigationToolbar2Tk(self.multi_canvas, self.multi_graph_frame)
        self.multi_toolbar.update()
        # Single graph (X-Y)
        self.main_fig, self.main_ax = plt.subplots(figsize=(6, 6))
        self.main_ax.set_xlabel("Time (s)", color='black', fontsize=12)
        self.main_ax.set_ylabel("Value", color='black', fontsize=12)
        self.main_ax.set_title("Real-Time Data Monitoring", color='black', fontsize=14, fontweight='bold', pad=15)
        self.main_ax.set_facecolor('white')
        self.main_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.main_ax.set_axisbelow(True)
        self.main_ax.tick_params(colors='black', labelsize=10)
        for spine in self.main_ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
        self.main_canvas = FigureCanvasTkAgg(self.main_fig, self.main_graph_frame)
        self.main_canvas.draw()
        self.main_canvas.get_tk_widget().pack(side='top', fill='both', expand=1)
        self.main_toolbar = NavigationToolbar2Tk(self.main_canvas, self.main_graph_frame)
        self.main_toolbar.update()
        self.update_multi_panel_graphs()
        self.plot_xy_graph('Time', 'Current', [], [])

    def update_multi_panel_graphs(self):
        """Update all 4 graphs including Resistance."""
        with self.data_lock:
            flow_x_copy = list(self.flow_x_data) if self.flow_x_data else []
            flow_y_copy = list(self.flow_y_data) if self.flow_y_data else []
            keithley_time_copy = list(self.keithley_time_data) if self.keithley_time_data else []
            keithley_voltage_copy = list(self.keithley_voltage_data) if self.keithley_voltage_data else []
            keithley_current_copy = list(self.keithley_current_data) if self.keithley_current_data else []
            resistance_time_copy = list(self.resistance_time_data) if self.resistance_time_data else []
            resistance_y_copy = list(self.resistance_y_data) if self.resistance_y_data else []
        # Voltage
        if not self.auto_scale_enabled:
            voltage_xlim = self.voltage_ax.get_xlim()
            voltage_ylim = self.voltage_ax.get_ylim()
        self.voltage_ax.clear()
        if len(keithley_time_copy) > 0 and len(keithley_voltage_copy) > 0:
            min_len = min(len(keithley_time_copy), len(keithley_voltage_copy))
            self.voltage_ax.plot(keithley_time_copy[:min_len], keithley_voltage_copy[:min_len],
                                 color='#2E86AB', linewidth=2, alpha=0.85)
            if min_len > 0:
                self.voltage_ax.relim()
                if self.auto_scale_enabled:
                    self.voltage_ax.autoscale()
                else:
                    self.voltage_ax.set_xlim(voltage_xlim)
                    self.voltage_ax.set_ylim(voltage_ylim)
        self.voltage_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.voltage_ax.set_ylabel("Voltage (V)", color='black', fontsize=10)
        self.voltage_ax.set_title("Voltage", color='black', fontsize=12, fontweight='bold', pad=10)
        self.voltage_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.voltage_ax.set_axisbelow(True)
        # Current
        if not self.auto_scale_enabled:
            current_xlim = self.current_ax.get_xlim()
            current_ylim = self.current_ax.get_ylim()
        self.current_ax.clear()
        if len(keithley_time_copy) > 0 and len(keithley_current_copy) > 0:
            min_len = min(len(keithley_time_copy), len(keithley_current_copy))
            self.current_ax.plot(keithley_time_copy[:min_len], keithley_current_copy[:min_len],
                                color='#A23B72', linewidth=2, alpha=0.85)
            if min_len > 0:
                self.current_ax.relim()
                if self.auto_scale_enabled:
                    self.current_ax.autoscale()
                else:
                    self.current_ax.set_xlim(current_xlim)
                    self.current_ax.set_ylim(current_ylim)
        self.current_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.current_ax.set_ylabel("Current (A)", color='black', fontsize=10)
        self.current_ax.set_title("Current", color='black', fontsize=12, fontweight='bold', pad=10)
        self.current_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.current_ax.set_axisbelow(True)
        # Flow
        if not self.auto_scale_enabled:
            flow_xlim = self.flow_ax.get_xlim()
            flow_ylim = self.flow_ax.get_ylim()
        self.flow_ax.clear()
        if len(flow_x_copy) > 0 and len(flow_y_copy) > 0:
            min_len = min(len(flow_x_copy), len(flow_y_copy))
            self.flow_ax.plot(flow_x_copy[:min_len], flow_y_copy[:min_len],
                              color='#F18F01', linewidth=2, alpha=0.85)
            if min_len > 0:
                self.flow_ax.relim()
                if self.auto_scale_enabled:
                    self.flow_ax.autoscale()
                else:
                    self.flow_ax.set_xlim(flow_xlim)
                    self.flow_ax.set_ylim(flow_ylim)
        self.flow_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.flow_ax.set_ylabel("Flow Rate (ml/min)", color='black', fontsize=10)
        self.flow_ax.set_title("Flow Rate", color='black', fontsize=12, fontweight='bold', pad=10)
        self.flow_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.flow_ax.set_axisbelow(True)
        # Resistance
        if not self.auto_scale_enabled:
            res_xlim = self.resistance_ax.get_xlim()
            res_ylim = self.resistance_ax.get_ylim()
        self.resistance_ax.clear()
        if len(resistance_time_copy) > 0 and len(resistance_y_copy) > 0:
            min_len = min(len(resistance_time_copy), len(resistance_y_copy))
            self.resistance_ax.plot(resistance_time_copy[:min_len], resistance_y_copy[:min_len],
                                    color='#2E7D32', linewidth=2, alpha=0.85)
            if min_len > 0:
                self.resistance_ax.relim()
                if self.auto_scale_enabled:
                    self.resistance_ax.autoscale()
                else:
                    self.resistance_ax.set_xlim(res_xlim)
                    self.resistance_ax.set_ylim(res_ylim)
        self.resistance_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.resistance_ax.set_ylabel("Resistance (Ω)", color='black', fontsize=10)
        self.resistance_ax.set_title("Resistance", color='black', fontsize=12, fontweight='bold', pad=10)
        self.resistance_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.resistance_ax.set_axisbelow(True)
        for ax in [self.voltage_ax, self.current_ax, self.flow_ax, self.resistance_ax]:
            ax.set_facecolor('white')
            ax.tick_params(colors='black', labelsize=9)
            for spine in ax.spines.values():
                spine.set_color('black')
                spine.set_linewidth(1)
        self.multi_fig.tight_layout(pad=2.0)
        self.multi_canvas.draw()

    def on_graph_mode_change(self):
        """Switch between multi-panel (4 graphs) and single graph modes."""
        mode = self.graph_mode_var.get()
        if mode == "multi":
            self.axis_frame.pack_forget()
            self.main_graph_frame.pack_forget()
            self.multi_graph_frame.pack(fill='both', expand=True, pady=5)
            self.update_multi_panel_graphs()
        else:
            self.multi_graph_frame.pack_forget()
            self.axis_frame.pack(fill='x', padx=5, pady=5)
            self.main_graph_frame.pack(fill='both', expand=True, pady=5)
            self.on_axis_change()

    def plot_xy_graph(self, x_axis_type, y_axis_type, x_data, y_data):
        """Plot X vs Y including Resistance option."""
        import numpy as np
        saved_xlim = None
        saved_ylim = None
        if not self.auto_scale_enabled:
            saved_xlim = self.main_ax.get_xlim()
            saved_ylim = self.main_ax.get_ylim()
        self.main_ax.clear()
        with self.data_lock:
            flow_x_copy = list(self.flow_x_data) if self.flow_x_data else []
            flow_y_copy = list(self.flow_y_data) if self.flow_y_data else []
            pressure_x_copy = list(self.pressure_x_data) if self.pressure_x_data else []
            pressure_y_copy = list(self.pressure_y_data) if self.pressure_y_data else []
            temp_x_copy = list(self.temp_x_data) if self.temp_x_data else []
            temp_y_copy = list(self.temp_y_data) if self.temp_y_data else []
            level_x_copy = list(self.level_x_data) if self.level_x_data else []
            level_y_copy = list(self.level_y_data) if self.level_y_data else []
            keithley_time_copy = list(self.keithley_time_data) if self.keithley_time_data else []
            keithley_voltage_copy = list(self.keithley_voltage_data) if self.keithley_voltage_data else []
            keithley_current_copy = list(self.keithley_current_data) if self.keithley_current_data else []
            resistance_time_copy = list(self.resistance_time_data) if self.resistance_time_data else []
            resistance_y_copy = list(self.resistance_y_data) if self.resistance_y_data else []
        x_param = []
        y_param = []
        if x_axis_type == 'Time':
            if len(flow_x_copy) > 0:
                x_param = flow_x_copy
            elif len(pressure_x_copy) > 0:
                x_param = pressure_x_copy
            elif len(temp_x_copy) > 0:
                x_param = temp_x_copy
            elif len(level_x_copy) > 0:
                x_param = level_x_copy
            elif len(resistance_time_copy) > 0:
                x_param = resistance_time_copy
        elif x_axis_type == 'Flow Rate':
            x_param = flow_y_copy
        elif x_axis_type == 'Pressure':
            x_param = pressure_y_copy
        elif x_axis_type == 'Temperature':
            x_param = temp_y_copy
        elif x_axis_type == 'Level':
            x_param = level_y_copy
        elif x_axis_type == 'Voltage':
            x_param = keithley_voltage_copy
        elif x_axis_type == 'Current':
            x_param = keithley_current_copy
        elif x_axis_type == 'Resistance':
            x_param = resistance_y_copy
        if y_axis_type == 'Flow Rate':
            y_param = flow_y_copy
        elif y_axis_type == 'Pressure':
            y_param = pressure_y_copy
        elif y_axis_type == 'Temperature':
            y_param = temp_y_copy
        elif y_axis_type == 'Level':
            y_param = level_y_copy
        elif y_axis_type == 'Voltage':
            y_param = keithley_voltage_copy
        elif y_axis_type == 'Current':
            y_param = keithley_current_copy
        elif y_axis_type == 'Resistance':
            y_param = resistance_y_copy
        if x_axis_type == 'Time' and len(y_param) > 0:
            if y_axis_type == 'Flow Rate' and len(flow_x_copy) > 0:
                x_param = flow_x_copy
            elif y_axis_type == 'Pressure' and len(pressure_x_copy) > 0:
                x_param = pressure_x_copy
            elif y_axis_type == 'Temperature' and len(temp_x_copy) > 0:
                x_param = temp_x_copy
            elif y_axis_type == 'Level' and len(level_x_copy) > 0:
                x_param = level_x_copy
            elif y_axis_type == 'Voltage' and len(keithley_time_copy) > 0:
                x_param = keithley_time_copy
            elif y_axis_type == 'Current' and len(keithley_time_copy) > 0:
                x_param = keithley_time_copy
            elif y_axis_type == 'Resistance' and len(resistance_time_copy) > 0:
                x_param = resistance_time_copy
        if len(x_data) > 0:
            x_param = x_data
        if len(y_data) > 0:
            y_param = y_data
        styles = {
            'Flow Rate': {'ylabel': 'Flow Rate (ml/min)', 'unit': 'ml/min'},
            'Pressure': {'ylabel': 'Pressure (bar)', 'unit': 'bar'},
            'Temperature': {'ylabel': 'Temperature (°C)', 'unit': '°C'},
            'Level': {'ylabel': 'Liquid Level (%)', 'unit': '%'},
            'Time': {'ylabel': 'Time (s)', 'unit': 's'},
            'Voltage': {'ylabel': 'Voltage (V)', 'unit': 'V'},
            'Current': {'ylabel': 'Current (A)', 'unit': 'A'},
            'Resistance': {'ylabel': 'Resistance (Ω)', 'unit': 'Ω'},
        }
        x_style = styles.get(x_axis_type, {'ylabel': x_axis_type, 'unit': ''})
        y_style = styles.get(y_axis_type, {'ylabel': y_axis_type, 'unit': ''})
        if len(x_param) > 0 and len(y_param) > 0:
            min_len = min(len(x_param), len(y_param))
            x_plot = list(x_param[:min_len])
            y_plot = list(y_param[:min_len])
        else:
            x_demo = np.linspace(0, 60, 200)
            if y_axis_type == 'Flow Rate':
                y_demo = 1.5 + 0.3 * np.sin(2 * np.pi * x_demo / 20)
            elif y_axis_type == 'Pressure':
                y_demo = 10 + 2 * np.sin(2 * np.pi * x_demo / 15)
            elif y_axis_type == 'Temperature':
                y_demo = 25 + 5 * np.sin(2 * np.pi * x_demo / 25)
            elif y_axis_type == 'Level':
                y_demo = 50 + 20 * np.sin(2 * np.pi * x_demo / 30)
            elif y_axis_type == 'Voltage':
                y_demo = 1.0 + 0.5 * np.sin(2 * np.pi * x_demo / 20)
            elif y_axis_type == 'Current':
                y_demo = 0.001 + 0.0005 * np.sin(2 * np.pi * x_demo / 20)
            elif y_axis_type == 'Resistance':
                y_demo = 1000 + 200 * np.sin(2 * np.pi * x_demo / 20)
            else:
                y_demo = 10 + 2 * np.sin(2 * np.pi * x_demo / 15)
            x_plot = x_demo.tolist()
            y_plot = y_demo.tolist()
        self.main_ax.plot(x_plot, y_plot, color='#2E86AB', linewidth=2.5, alpha=0.85)
        self.main_ax.set_facecolor('white')
        self.main_ax.set_xlabel(x_style['ylabel'], color='black', fontsize=13)
        self.main_ax.set_ylabel(y_style['ylabel'], color='black', fontsize=13)
        self.main_ax.set_title(f"{y_axis_type} vs {x_axis_type}", color='black', fontsize=14, fontweight='bold', pad=15)
        self.main_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5, which='both')
        self.main_ax.set_axisbelow(True)
        self.main_ax.tick_params(colors='black', labelsize=10, width=1)
        for spine in self.main_ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
        if len(x_plot) > 0 and len(y_plot) > 0:
            if self.auto_scale_enabled:
                x_margin = (max(x_plot) - min(x_plot)) * 0.05 if max(x_plot) > min(x_plot) else 1
                y_margin = (max(y_plot) - min(y_plot)) * 0.1 if max(y_plot) > min(y_plot) else 1
                self.main_ax.set_xlim(min(x_plot) - x_margin, max(x_plot) + x_margin)
                self.main_ax.set_ylim(min(y_plot) - y_margin, max(y_plot) + y_margin)
            elif saved_xlim is not None and saved_ylim is not None:
                self.main_ax.set_xlim(saved_xlim)
                self.main_ax.set_ylim(saved_ylim)
        self.main_fig.tight_layout(pad=2.0)
        self.main_canvas.draw()

    def clear_graph(self):
        """Clear all graphs including resistance data."""
        with self.data_lock:
            self.resistance_time_data.clear()
            self.resistance_y_data.clear()
        super().clear_graph()
        if self.update_queue:
            self.update_queue.put(('UPDATE_RTAB_STATUS', 'Graph cleared. Clock reset.'))
            self.update_queue.put(('UPDATE_RTAB_RECORDING_STATUS', ('Ready', 'green')))

    def _rtab_put(self, update_type, data):
        """Send update to queue with RTAB prefix so main_app routes to this tab.
        main_app.check_update_queue() handles UPDATE_RTAB_* and applies updates to this instance."""
        rtab_map = {
            'UPDATE_GRAPH1': 'UPDATE_RTAB_GRAPH1',
            'UPDATE_GRAPH2': 'UPDATE_RTAB_GRAPH2',
            'UPDATE_GRAPH3': 'UPDATE_RTAB_GRAPH3',
            'UPDATE_GRAPH4': 'UPDATE_RTAB_GRAPH4',
            'UPDATE_STATUS': 'UPDATE_RTAB_STATUS',
            'UPDATE_RECORDING_STATUS': 'UPDATE_RTAB_RECORDING_STATUS',
            'UPDATE_FILE': 'UPDATE_RTAB_FILE',
            'UPDATE_READINGS': 'UPDATE_RTAB_READINGS',
            'UPDATE_STEP_START': 'UPDATE_RTAB_STEP_START',
            'UPDATE_STEP_PROGRESS': 'UPDATE_RTAB_STEP_PROGRESS',
            'UPDATE_STEP_COMPLETE': 'UPDATE_RTAB_STEP_COMPLETE',
        }
        key = rtab_map.get(update_type, update_type)
        if self.update_queue:
            self.update_queue.put((key, data))

    def start_recording(self):
        """Start recording; send status updates to this tab (UPDATE_RTAB_*)."""
        from tkinter import messagebox
        from datetime import datetime
        import re
        logger.debug("start_recording() called [ResistanceTab]")
        try:
            file_name = self.exp_name_entry.get().strip()
            if not file_name:
                messagebox.showerror('Error', 'Please enter an experiment name before starting recording.')
                return
            if not re.match(r'^[a-zA-Z0-9_-]+$', file_name):
                messagebox.showerror('Error', 'Experiment name can only contain letters, numbers, underscores, and hyphens.')
                return
            flow_rate = float(self.flow_rate_entry.get())
            if flow_rate < 0:
                messagebox.showerror('Error', 'Flow rate cannot be negative.')
                return
            MAX_FLOW_RATE = 5.0
            if flow_rate > MAX_FLOW_RATE:
                from tkinter import messagebox as mb
                mb.showwarning('Flow Rate Limit', f'Maximum flow rate is {MAX_FLOW_RATE} ml/min.')
                flow_rate = MAX_FLOW_RATE
                self.flow_rate_entry.delete(0, 'end')
                self.flow_rate_entry.insert(0, str(MAX_FLOW_RATE))
            duration = int(self.duration_entry.get())
            valve_setting = {'valve1': self.valve_var.get() == 'main', 'valve2': self.valve_var.get() == 'rinsing'}
            self.current_flow_rate = flow_rate
            experiment_program = [{'duration': duration, 'flow_rate': flow_rate, 'valve_setting': valve_setting}]
            file_is_closed = (
                not self.data_handler.file_path or not os.path.exists(self.data_handler.file_path) or
                self.data_handler.file is None or getattr(self.data_handler, 'file_closed', False)
            )
            is_new_experiment = self.experiment_base_time is None or file_is_closed
            if is_new_experiment:
                if file_is_closed:
                    metadata = {
                        'name': file_name,
                        'description': self.exp_desc_entry.get().strip(),
                        'tags': [tag.strip() for tag in self.exp_tags_entry.get().split(',') if tag.strip()],
                        'operator': self.exp_operator_entry.get().strip(),
                        'start_time': datetime.now().isoformat()
                    }
                    self.data_handler.set_custom_filename(file_name)
                    self.data_handler.set_metadata(metadata)
                    self.data_handler.create_new_file()
                    self.last_total_time = 0.0
                    self.experiment_base_time = time.time()
            else:
                if self.experiment_base_time is None:
                    with self.data_lock:
                        if len(self.flow_x_data) > 0:
                            self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
                            self.experiment_base_time = time.time() - self.last_total_time
                        else:
                            self.experiment_base_time = time.time()
                            self.last_total_time = 0.0
            if self.update_queue:
                self._rtab_put('UPDATE_RECORDING_STATUS', ('Recording...', 'red'))
                if is_new_experiment:
                    self._rtab_put('UPDATE_FILE', f"{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
                self._rtab_put('UPDATE_READINGS', (0, 0, flow_rate, 0))
            thread = threading.Thread(target=self.experiment_thread, args=(experiment_program, is_new_experiment), daemon=True)
            thread.start()
        except ValueError as e:
            logger.warning(f"ValueError in start_recording: {e}")
            from tkinter import messagebox as mb
            mb.showerror('Error', 'Invalid input for Flow Rate or Duration. Please enter numbers.')

    def stop_recording(self):
        """Stop recording; send status to this tab."""
        self.exp_manager.stop_experiment()
        with self.data_lock:
            if len(self.flow_x_data) > 0:
                self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
        if self.update_queue:
            self._rtab_put('UPDATE_RECORDING_STATUS', ('Paused', 'orange'))
            self._rtab_put('UPDATE_STATUS', f'Recording paused. Total time: {self.last_total_time:.1f}s. Click Start to resume.')

    def finish_recording(self):
        """Finish recording; send status to this tab."""
        self.exp_manager.finish_experiment()
        if self.data_handler.file_path and self.data_handler.file:
            self.data_handler.file.flush()
            self.data_handler.close_file()
            csv_path = self.data_handler.file_path
            excel_path = csv_path.replace('.csv', '.xlsx')
            try:
                success = self.data_handler.export_to_excel(excel_path)
                if success:
                    if self.update_queue:
                        self._rtab_put('UPDATE_STATUS', f'Experiment finished. File closed and converted to Excel: {excel_path}')
                else:
                    if self.update_queue:
                        self._rtab_put('UPDATE_STATUS', 'Experiment finished. CSV closed. Excel conversion failed.')
            except Exception as e:
                logger.warning(f"Error during Excel conversion: {e}")
                if self.update_queue:
                    self._rtab_put('UPDATE_STATUS', f'Experiment finished. CSV closed. Excel conversion error: {e}')
        self.last_total_time = 0.0
        self.experiment_base_time = None
        self.measurement_counter = 0
        if self.update_queue:
            self._rtab_put('UPDATE_RECORDING_STATUS', ('Completed', 'green'))
            self._rtab_put('UPDATE_FILE', 'No file - will create new file on next Start')

    def experiment_thread(self, experiment_program, is_new_experiment=True):
        """Run experiment in separate thread; same as MainTab but with R = V/I and UPDATE_RTAB_*."""
        logger.debug("Starting experiment thread [ResistanceTab]")
        self.exp_manager.is_running = True
        if is_new_experiment:
            if self.update_queue:
                self._rtab_put('UPDATE_STATUS', 'Starting new experiment...')
            if not self.data_handler.file_path or not os.path.exists(self.data_handler.file_path) or self.data_handler.file is None:
                self.data_handler.create_new_file()
            if self.experiment_base_time is None:
                self.experiment_base_time = time.time()
                self.last_total_time = 0.0
        else:
            if self.update_queue:
                self._rtab_put('UPDATE_STATUS', f'Resuming experiment from {self.last_total_time:.1f}s...')
            if not self.data_handler.file_path or not os.path.exists(self.data_handler.file_path):
                self.data_handler.create_new_file()
                self.experiment_base_time = time.time()
                self.last_total_time = 0.0
            else:
                if self.experiment_base_time is None:
                    with self.data_lock:
                        if len(self.flow_x_data) > 0:
                            self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
                            self.experiment_base_time = time.time() - self.last_total_time
                        else:
                            self.experiment_base_time = time.time()
                            self.last_total_time = 0.0
        experiment_start_time = self.experiment_base_time
        total_steps = len(experiment_program)
        for step_index, step in enumerate(experiment_program, start=1):
            if not self.exp_manager.is_running:
                break
            duration = step.get('duration')
            flow_rate = step.get('flow_rate', self.current_flow_rate)
            if 'flow_rate' in step:
                self.current_flow_rate = flow_rate
            temperature = step.get('temperature', None)
            valve_setting = step.get('valve_setting', {'valve1': True, 'valve2': False})
            if self.update_queue:
                self._rtab_put('UPDATE_STEP_START', (step_index, total_steps, duration))
                temp_str = f", Temp={temperature}°C" if temperature else ""
                mode_str = ""
                if step.get('measurement_mode'):
                    mode_str = f", Mode={'Voltage' if step.get('measurement_mode') == 'voltage' else 'Current'}"
                self._rtab_put('UPDATE_STATUS', f"Executing step {step_index}/{total_steps}: Duration={duration}s, Flow Rate={flow_rate} ml/min{temp_str}{mode_str}")
            if temperature is not None:
                try:
                    self.exp_manager.hw_controller.set_heating_plate_temp(temperature)
                except Exception as e:
                    logger.warning(f"Could not set temperature: {e}")
            try:
                self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
                time.sleep(0.3)
                self.exp_manager.hw_controller.start_pump()
                time.sleep(0.5)
                self.exp_manager.hw_controller.set_valves(valve_setting['valve1'], valve_setting['valve2'])
            except Exception as e:
                logger.warning(f"Pump timeout/error: {e}")
                if hasattr(self.exp_manager.hw_controller.pump, 'connected'):
                    self.exp_manager.hw_controller.pump.connected = False
                if self.update_queue:
                    self._rtab_put('UPDATE_STATUS', 'Experiment stopped: Pump unresponsive')
                    self._rtab_put('UPDATE_RECORDING_STATUS', ('Stopped: Pump Timeout', 'red'))
                self.exp_manager.stop_experiment()
                self.after(0, lambda: self.pump_status_label.configure(text='✗ Disconnected (Timeout)', text_color='red'))
                return
            if self.keithley_output_enabled and self.hw_controller.smu is not None:
                try:
                    measurement_mode = step.get('measurement_mode', None)
                    if measurement_mode:
                        mode = measurement_mode
                        self.after(0, lambda m=mode: self.keithley_mode_var.set(m))
                        self.after(0, self.on_keithley_mode_change)
                    else:
                        mode = self.keithley_mode_var.get()
                    bias_value = float(self.keithley_bias_entry.get())
                    if mode == "voltage":
                        voltage_limit = float(self.keithley_voltage_limit_entry.get())
                        self.hw_controller.setup_smu_for_current_source(voltage_limit)
                        self.hw_controller.set_smu_current(bias_value)
                    else:
                        current_limit = float(self.keithley_current_limit_entry.get())
                        self.hw_controller.setup_smu_for_iv_measurement(current_limit)
                        self.hw_controller.set_smu_voltage(bias_value, current_limit)
                except (ValueError, Exception) as e:
                    logger.warning(f"Error setting up Keithley: {e}")
                    self.keithley_output_enabled = False
            start_time = time.time()
            loop_count = 0
            while time.time() - start_time < duration and self.exp_manager.is_running:
                loop_count += 1
                if not self.exp_manager.perform_safety_checks():
                    break
                step_elapsed = time.time() - start_time
                step_remaining = max(0, duration - step_elapsed)
                step_progress = min(1.0, step_elapsed / duration) if duration > 0 else 0.0
                if self.update_queue:
                    self._rtab_put('UPDATE_STEP_PROGRESS', (step_index, total_steps, step_remaining, step_progress))
                if self.current_flow_rate != flow_rate:
                    old_fr = flow_rate
                    flow_rate = self.current_flow_rate
                    try:
                        self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
                        if self.update_queue:
                            self._rtab_put('UPDATE_STATUS', f'Flow changed: {old_fr:.2f} → {flow_rate:.2f} ml/min')
                    except Exception as e:
                        logger.warning(f"Pump timeout during flow update: {e}")
                        if hasattr(self.exp_manager.hw_controller.pump, 'connected'):
                            self.exp_manager.hw_controller.pump.connected = False
                        if self.update_queue:
                            self._rtab_put('UPDATE_STATUS', 'Experiment stopped: Pump unresponsive')
                            self._rtab_put('UPDATE_RECORDING_STATUS', ('Stopped: Pump Timeout', 'red'))
                        self.exp_manager.stop_experiment()
                        self.after(0, lambda: self.pump_status_label.configure(text='✗ Disconnected (Timeout)', text_color='red'))
                        break
                current_time = time.time()
                remaining_time = duration - (current_time - start_time)
                elapsed_time_from_start = current_time - experiment_start_time
                try:
                    pump_data = self.exp_manager.hw_controller.read_pump_data()
                except Exception as e:
                    logger.warning(f"Pump timeout during data read: {e}")
                    if hasattr(self.exp_manager.hw_controller.pump, 'connected'):
                        self.exp_manager.hw_controller.pump.connected = False
                    if self.update_queue:
                        self._rtab_put('UPDATE_STATUS', 'Experiment stopped: Pump unresponsive')
                        self._rtab_put('UPDATE_RECORDING_STATUS', ('Stopped: Pump Timeout', 'red'))
                    self.exp_manager.stop_experiment()
                    self.after(0, lambda: self.pump_status_label.configure(text='✗ Disconnected (Timeout)', text_color='red'))
                    break
                pressure = self.exp_manager.hw_controller.read_pressure_sensor()
                temperature = self.exp_manager.hw_controller.read_temperature_sensor()
                level = self.exp_manager.hw_controller.read_level_sensor()
                keithley_voltage = None
                keithley_current = None
                if self.keithley_output_enabled and self.hw_controller.smu is not None:
                    try:
                        current_mode = step.get('measurement_mode', None) or self.keithley_mode_var.get()
                        smu_measurement = self.hw_controller.measure_smu(mode=current_mode)
                        if smu_measurement:
                            keithley_voltage = smu_measurement.get('voltage', None)
                            keithley_current = smu_measurement.get('current', None)
                            if keithley_voltage is not None:
                                self.keithley_voltage_label.configure(text=f'{keithley_voltage:.4f} V')
                            if keithley_current is not None:
                                self.keithley_current_label.configure(text=f'{keithley_current:.6f} A')
                    except Exception as e:
                        logger.debug(f"Error reading Keithley: {e}")
                if self.update_queue:
                    status_msg = f"Running: {remaining_time:.0f}s remaining, Flow={flow_rate}ml/min"
                    if keithley_voltage is not None:
                        status_msg += f", V={keithley_voltage:.3f}V, I={keithley_current:.6f}A"
                    self._rtab_put('UPDATE_STATUS', status_msg)
                R = None
                if keithley_voltage is not None and keithley_current is not None and abs(keithley_current) > 1e-12:
                    R = keithley_voltage / keithley_current
                bias_str = '—'
                if self.keithley_output_enabled:
                    try:
                        bias_str = self.keithley_bias_entry.get()
                    except Exception:
                        pass
                with self.data_lock:
                    self.flow_x_data.append(elapsed_time_from_start)
                    self.flow_y_data.append(pump_data['flow'])
                    self.pressure_x_data.append(elapsed_time_from_start)
                    self.pressure_y_data.append(pressure if pressure is not None else float('nan'))
                    self.temp_x_data.append(elapsed_time_from_start)
                    self.temp_y_data.append(temperature if temperature is not None else float('nan'))
                    self.level_x_data.append(elapsed_time_from_start)
                    self.level_y_data.append(level * 100 if level is not None else float('nan'))
                    self.keithley_time_data.append(elapsed_time_from_start)
                    self.keithley_voltage_data.append(keithley_voltage if keithley_voltage is not None else 0.0)
                    self.keithley_current_data.append(keithley_current if keithley_current is not None else 0.0)
                    if R is not None:
                        self.resistance_time_data.append(elapsed_time_from_start)
                        self.resistance_y_data.append(R)
                data_point = {
                    "measurement_id": self.measurement_counter,
                    "time": elapsed_time_from_start,
                    "flow_setpoint": self.current_flow_rate,
                    "pump_flow_read": pump_data['flow'],
                    "pressure_read": pressure if pressure is not None else "",
                    "temp_read": temperature if temperature is not None else "",
                    "level_read": level if level is not None else "",
                    "voltage": keithley_voltage if keithley_voltage is not None else "",
                    "current": keithley_current if keithley_current is not None else "",
                    "target_voltage": float(self.keithley_bias_entry.get()) if self.keithley_output_enabled else "",
                    "resistance": R if R is not None else "",
                }
                self.data_handler.append_data(data_point)
                if self.update_queue:
                    try:
                        with self.data_lock:
                            flow_x_copy = list(self.flow_x_data)
                            flow_y_copy = list(self.flow_y_data)
                            pressure_x_copy = list(self.pressure_x_data)
                            pressure_y_copy = list(self.pressure_y_data)
                            temp_x_copy = list(self.temp_x_data)
                            temp_y_copy = list(self.temp_y_data)
                            level_x_copy = list(self.level_x_data)
                            level_y_copy = list(self.level_y_data)
                            resistance_time_copy = list(self.resistance_time_data)
                            resistance_y_copy = list(self.resistance_y_data)
                        self._rtab_put('UPDATE_GRAPH1', (flow_x_copy, flow_y_copy))
                        self._rtab_put('UPDATE_GRAPH2', (pressure_x_copy, pressure_y_copy))
                        self._rtab_put('UPDATE_GRAPH3', (temp_x_copy, temp_y_copy))
                        self._rtab_put('UPDATE_GRAPH4', (level_x_copy, level_y_copy))
                        self.update_queue.put(('UPDATE_RTAB_RESISTANCE', (resistance_time_copy, resistance_y_copy)))
                        cur_str = f'{keithley_current:.6f} A' if keithley_current is not None else '—'
                        r_str = f'{R:.2f} Ω' if R is not None else '—'
                        self.update_queue.put(('UPDATE_RTAB_RESISTANCE_READINGS', (bias_str, cur_str, r_str)))
                    except Exception as e:
                        logger.warning(f"Error updating graphs: {e}")
                time.sleep(1)
            if self.update_queue:
                self._rtab_put('UPDATE_STEP_COMPLETE', (step_index, total_steps))
        self.exp_manager.hw_controller.stop_pump()
        if self.keithley_output_enabled and self.hw_controller.smu is not None:
            try:
                self.hw_controller.stop_smu()
            except Exception as e:
                logger.warning(f"Error stopping Keithley: {e}")
        self.exp_manager.stop_experiment()
        with self.data_lock:
            if len(self.flow_x_data) > 0:
                self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
        if self.update_queue:
            self._rtab_put('UPDATE_STATUS', f'Experiment paused. Total time: {self.last_total_time:.1f}s. Click Start to continue.')
            self._rtab_put('UPDATE_RECORDING_STATUS', ('Paused', 'orange'))
