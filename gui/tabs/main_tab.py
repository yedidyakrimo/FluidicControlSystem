"""
Main Tab - Primary experiment control and monitoring
"""

import customtkinter as ctk
from tkinter import PanedWindow, Frame, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import threading
import time
import os
import re
from datetime import datetime
import numpy as np
import queue

from gui.tabs.base_tab import BaseTab


class MainTab(BaseTab):
    """
    Main tab for experiment control and real-time monitoring
    """
    
    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None):
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        
        # Current flow rate
        self.current_flow_rate = 1.5
        
        # Track cumulative time for resume capability
        self.last_total_time = 0.0
        self.experiment_base_time = None
        
        # Create widgets
        self.create_widgets()
        
        # Setup graphs
        self.setup_graphs()
    
    def create_widgets(self):
        """Create Main tab widgets"""
        # Create PanedWindow for resizable panels
        paned = PanedWindow(self, orient='horizontal', sashwidth=8, sashrelief='raised', bg='#2b2b2b')
        paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left column container
        left_container = Frame(paned, bg='#1a1a1a')
        paned.add(left_container, minsize=250, width=400)
        
        # Left column - Scrollable
        left_frame = ctk.CTkScrollableFrame(left_container, width=400)
        left_frame.pack(fill='both', expand=True)
        
        # Experiment Parameters
        exp_frame = ctk.CTkFrame(left_frame)
        exp_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(exp_frame, text="Experiment Parameters", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        flow_frame = ctk.CTkFrame(exp_frame)
        flow_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(flow_frame, text='Flow Rate (ml/min):', width=150).pack(side='left', padx=5)
        self.flow_rate_entry = ctk.CTkEntry(flow_frame, width=100)
        self.flow_rate_entry.insert(0, '1.5')
        self.flow_rate_entry.pack(side='left', padx=5)
        
        duration_frame = ctk.CTkFrame(exp_frame)
        duration_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(duration_frame, text='Duration (sec):', width=150).pack(side='left', padx=5)
        self.duration_entry = ctk.CTkEntry(duration_frame, width=100)
        self.duration_entry.insert(0, '60')
        self.duration_entry.pack(side='left', padx=5)
        
        valve_frame = ctk.CTkFrame(exp_frame)
        valve_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(valve_frame, text='Valve Settings:', width=150).pack(side='left', padx=5)
        self.valve_var = ctk.StringVar(value="main")
        ctk.CTkRadioButton(valve_frame, text="Main", variable=self.valve_var, value="main").pack(side='left', padx=5)
        ctk.CTkRadioButton(valve_frame, text="Rinsing", variable=self.valve_var, value="rinsing").pack(side='left', padx=5)
        
        # Experiment Metadata
        metadata_frame = ctk.CTkFrame(left_frame)
        metadata_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(metadata_frame, text="Experiment Metadata", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        name_frame = ctk.CTkFrame(metadata_frame)
        name_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(name_frame, text='Experiment Name:', width=120).pack(side='left', padx=5)
        self.exp_name_entry = ctk.CTkEntry(name_frame, width=200)
        self.exp_name_entry.insert(0, 'experiment_data')
        self.exp_name_entry.pack(side='left', padx=5)
        
        desc_frame = ctk.CTkFrame(metadata_frame)
        desc_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(desc_frame, text='Description:', width=120).pack(side='left', padx=5)
        self.exp_desc_entry = ctk.CTkEntry(desc_frame, width=200)
        self.exp_desc_entry.pack(side='left', padx=5)
        
        tags_frame = ctk.CTkFrame(metadata_frame)
        tags_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(tags_frame, text='Tags (comma-separated):', width=120).pack(side='left', padx=5)
        self.exp_tags_entry = ctk.CTkEntry(tags_frame, width=200)
        self.exp_tags_entry.insert(0, 'test')
        self.exp_tags_entry.pack(side='left', padx=5)
        
        operator_frame = ctk.CTkFrame(metadata_frame)
        operator_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(operator_frame, text='Operator:', width=120).pack(side='left', padx=5)
        self.exp_operator_entry = ctk.CTkEntry(operator_frame, width=200)
        self.exp_operator_entry.pack(side='left', padx=5)
        
        ctk.CTkLabel(metadata_frame, text='(Metadata will be saved with experiment data)', 
                    font=('Helvetica', 9), text_color='gray').pack(pady=2)
        
        # Control buttons
        control_frame = ctk.CTkFrame(left_frame)
        control_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(control_frame, text="Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        self.start_btn = ctk.CTkButton(control_frame, text='Start Recording', 
                                       command=self.start_recording, fg_color='green', width=150, height=40)
        self.start_btn.pack(pady=2)
        
        self.stop_btn = ctk.CTkButton(control_frame, text='Stop Recording', 
                                      command=self.stop_recording, fg_color='red', width=150, height=40)
        self.stop_btn.pack(pady=2)
        
        self.finish_btn = ctk.CTkButton(control_frame, text='Finish Recording', 
                                        command=self.finish_recording, fg_color='orange', width=150, height=40)
        self.finish_btn.pack(pady=2)
        
        self.update_flow_btn = ctk.CTkButton(control_frame, text='Update Flow', 
                                            command=self.update_flow, fg_color='purple', width=150)
        self.update_flow_btn.pack(pady=2)
        
        self.clear_graph_btn = ctk.CTkButton(control_frame, text='Clear Graph', 
                                             command=self.clear_graph, fg_color='gray', width=150)
        self.clear_graph_btn.pack(pady=2)
        
        export_menu_frame = ctk.CTkFrame(control_frame)
        export_menu_frame.pack(pady=2)
        
        ctk.CTkLabel(export_menu_frame, text='Export:', width=80).pack(side='left', padx=5)
        self.export_btn = ctk.CTkButton(export_menu_frame, text='Excel', 
                                       command=self.export_excel, fg_color='blue', width=100)
        self.export_btn.pack(side='left', padx=2)
        
        ctk.CTkButton(export_menu_frame, text='PNG', 
                     command=self.export_graph_png, fg_color='green', width=100).pack(side='left', padx=2)
        
        ctk.CTkButton(export_menu_frame, text='PDF', 
                     command=self.export_graph_pdf, fg_color='red', width=100).pack(side='left', padx=2)
        
        # Current Readings
        readings_frame = ctk.CTkFrame(left_frame)
        readings_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(readings_frame, text="Current Readings", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        readings_grid = ctk.CTkFrame(readings_frame)
        readings_grid.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(readings_grid, text='Pressure:', width=120).grid(row=0, column=0, padx=5, pady=2)
        self.pressure_label = ctk.CTkLabel(readings_grid, text='N/A', width=180)
        self.pressure_label.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(readings_grid, text='Temperature:', width=120).grid(row=1, column=0, padx=5, pady=2)
        self.temp_label = ctk.CTkLabel(readings_grid, text='N/A', width=180)
        self.temp_label.grid(row=1, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(readings_grid, text='Flow:', width=120).grid(row=2, column=0, padx=5, pady=2)
        self.flow_label = ctk.CTkLabel(readings_grid, text='N/A', width=180)
        self.flow_label.grid(row=2, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(readings_grid, text='Level:', width=120).grid(row=3, column=0, padx=5, pady=2)
        self.level_label = ctk.CTkLabel(readings_grid, text='N/A', width=180)
        self.level_label.grid(row=3, column=1, padx=5, pady=2)
        
        # Real-time Statistics Panel
        stats_frame = ctk.CTkFrame(left_frame)
        stats_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(stats_frame, text="Real-Time Statistics", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        stats_grid = ctk.CTkFrame(stats_frame)
        stats_grid.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(stats_grid, text='Flow:', width=120, font=('Helvetica', 10, 'bold')).grid(row=0, column=0, padx=5, pady=2)
        self.flow_stats_label = ctk.CTkLabel(stats_grid, text='Mean: N/A | Std: N/A', width=260, font=('Helvetica', 9))
        self.flow_stats_label.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(stats_grid, text='Pressure:', width=120, font=('Helvetica', 10, 'bold')).grid(row=1, column=0, padx=5, pady=2)
        self.pressure_stats_label = ctk.CTkLabel(stats_grid, text='Mean: N/A | Std: N/A', width=260, font=('Helvetica', 9))
        self.pressure_stats_label.grid(row=1, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(stats_grid, text='Temperature:', width=120, font=('Helvetica', 10, 'bold')).grid(row=2, column=0, padx=5, pady=2)
        self.temp_stats_label = ctk.CTkLabel(stats_grid, text='Mean: N/A | Std: N/A', width=260, font=('Helvetica', 9))
        self.temp_stats_label.grid(row=2, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(stats_grid, text='Level:', width=120, font=('Helvetica', 10, 'bold')).grid(row=3, column=0, padx=5, pady=2)
        self.level_stats_label = ctk.CTkLabel(stats_grid, text='Mean: N/A | Std: N/A', width=260, font=('Helvetica', 9))
        self.level_stats_label.grid(row=3, column=1, padx=5, pady=2)
        
        # Recording Status
        status_frame = ctk.CTkFrame(left_frame)
        status_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(status_frame, text="Recording Status", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        status_grid = ctk.CTkFrame(status_frame)
        status_grid.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(status_grid, text='Status:', width=120).grid(row=0, column=0, padx=5, pady=2)
        self.recording_status_label = ctk.CTkLabel(status_grid, text='Ready', text_color='green', width=220)
        self.recording_status_label.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(status_grid, text='File:', width=120).grid(row=1, column=0, padx=5, pady=2)
        self.current_file_label = ctk.CTkLabel(status_grid, text='No file selected', width=220)
        self.current_file_label.grid(row=1, column=1, padx=5, pady=2)
        
        # Status bar
        self.status_bar = ctk.CTkLabel(left_frame, text='', font=('Helvetica', 10))
        self.status_bar.pack(pady=5)
        
        # Right column container
        right_container = Frame(paned, bg='#1a1a1a')
        paned.add(right_container, minsize=400)
        
        # Right column - Multi-Panel Graphs
        right_frame = ctk.CTkFrame(right_container)
        right_frame.pack(fill='both', expand=True)
        
        graph_control_frame = ctk.CTkFrame(right_frame)
        graph_control_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(graph_control_frame, text="Real-Time Monitoring", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        # Graph mode toggle
        mode_frame = ctk.CTkFrame(graph_control_frame)
        mode_frame.pack(fill='x', padx=5, pady=5)
        ctk.CTkLabel(mode_frame, text='View Mode:', width=80).pack(side='left', padx=5)
        self.graph_mode_var = ctk.StringVar(value="single")
        ctk.CTkRadioButton(mode_frame, text="Multi-Panel (4 graphs)", variable=self.graph_mode_var, value="multi", command=self.on_graph_mode_change).pack(side='left', padx=5)
        ctk.CTkRadioButton(mode_frame, text="Single Graph (X-Y)", variable=self.graph_mode_var, value="single", command=self.on_graph_mode_change).pack(side='left', padx=5)
        
        # Single graph controls (shown initially)
        self.axis_frame = ctk.CTkFrame(graph_control_frame)
        self.axis_frame.pack(fill='x', padx=5, pady=5)
        
        axis_label_frame = ctk.CTkFrame(self.axis_frame)
        axis_label_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(axis_label_frame, text='X-Axis:', width=60).pack(side='left', padx=5)
        self.x_axis_combo = ctk.CTkComboBox(axis_label_frame, 
                                            values=['Time', 'Flow Rate', 'Pressure', 'Temperature', 'Level'],
                                            width=150, command=self.on_axis_change)
        self.x_axis_combo.set('Time')
        self.x_axis_combo.pack(side='left', padx=5)
        
        ctk.CTkLabel(axis_label_frame, text='Y-Axis:', width=60).pack(side='left', padx=5)
        self.y_axis_combo = ctk.CTkComboBox(axis_label_frame,
                                            values=['Flow Rate', 'Pressure', 'Temperature', 'Level'],
                                            width=150, command=self.on_axis_change)
        self.y_axis_combo.set('Pressure')
        self.y_axis_combo.pack(side='left', padx=5)
        
        # Multi-panel graph frames container
        self.multi_graph_frame = ctk.CTkFrame(right_frame)
        self.multi_graph_frame.pack_forget()  # Hidden by default
        
        # Single graph frame (shown initially)
        self.main_graph_frame = ctk.CTkFrame(right_frame)
        self.main_graph_frame.pack(fill='both', expand=True, pady=5)
    
    def setup_graphs(self):
        """Initialize matplotlib graphs"""
        # Multi-panel graphs (2x2 grid)
        self.multi_fig, ((self.flow_ax, self.pressure_ax), 
                         (self.temp_ax, self.level_ax)) = plt.subplots(2, 2, figsize=(12, 10))
        
        # Configure each subplot
        graphs_config = [
            (self.flow_ax, 'Flow Rate', 'Flow Rate (ml/min)', '#2E86AB'),
            (self.pressure_ax, 'Pressure', 'Pressure (PSI)', '#A23B72'),
            (self.temp_ax, 'Temperature', 'Temperature (°C)', '#F18F01'),
            (self.level_ax, 'Liquid Level', 'Level (%)', '#06A77D')
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
        
        # Create canvas for multi-panel graph
        self.multi_canvas = FigureCanvasTkAgg(self.multi_fig, self.multi_graph_frame)
        self.multi_canvas.draw()
        self.multi_canvas.get_tk_widget().pack(side='top', fill='both', expand=1)
        
        # Add navigation toolbar for multi-panel
        self.multi_toolbar = NavigationToolbar2Tk(self.multi_canvas, self.multi_graph_frame)
        self.multi_toolbar.update()
        
        # Single graph (for X-Y mode)
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
        
        # Create canvas for main graph
        self.main_canvas = FigureCanvasTkAgg(self.main_fig, self.main_graph_frame)
        self.main_canvas.draw()
        self.main_canvas.get_tk_widget().pack(side='top', fill='both', expand=1)
        
        # Add navigation toolbar for single graph
        self.main_toolbar = NavigationToolbar2Tk(self.main_canvas, self.main_graph_frame)
        self.main_toolbar.update()
        
        # Initialize graphs
        self.update_multi_panel_graphs()
        self.plot_xy_graph('Time', 'Pressure', [], [])
    
    def on_graph_mode_change(self):
        """Switch between multi-panel and single graph modes"""
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
    
    def update_multi_panel_graphs(self):
        """Update all 4 graphs in multi-panel view"""
        # Flow graph
        self.flow_ax.clear()
        if len(self.flow_x_data) > 0 and len(self.flow_y_data) > 0:
            self.flow_ax.plot(self.flow_x_data, self.flow_y_data, color='#2E86AB', linewidth=2, alpha=0.85)
        self.flow_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.flow_ax.set_ylabel("Flow Rate (ml/min)", color='black', fontsize=10)
        self.flow_ax.set_title("Flow Rate", color='black', fontsize=12, fontweight='bold', pad=10)
        self.flow_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.flow_ax.set_axisbelow(True)
        
        # Pressure graph
        self.pressure_ax.clear()
        if len(self.pressure_x_data) > 0 and len(self.pressure_y_data) > 0:
            self.pressure_ax.plot(self.pressure_x_data, self.pressure_y_data, color='#A23B72', linewidth=2, alpha=0.85)
        self.pressure_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.pressure_ax.set_ylabel("Pressure (PSI)", color='black', fontsize=10)
        self.pressure_ax.set_title("Pressure", color='black', fontsize=12, fontweight='bold', pad=10)
        self.pressure_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.pressure_ax.set_axisbelow(True)
        
        # Temperature graph
        self.temp_ax.clear()
        if len(self.temp_x_data) > 0 and len(self.temp_y_data) > 0:
            self.temp_ax.plot(self.temp_x_data, self.temp_y_data, color='#F18F01', linewidth=2, alpha=0.85)
        self.temp_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.temp_ax.set_ylabel("Temperature (°C)", color='black', fontsize=10)
        self.temp_ax.set_title("Temperature", color='black', fontsize=12, fontweight='bold', pad=10)
        self.temp_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.temp_ax.set_axisbelow(True)
        
        # Level graph
        self.level_ax.clear()
        if len(self.level_x_data) > 0 and len(self.level_y_data) > 0:
            self.level_ax.plot(self.level_x_data, self.level_y_data, color='#06A77D', linewidth=2, alpha=0.85)
        self.level_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.level_ax.set_ylabel("Level (%)", color='black', fontsize=10)
        self.level_ax.set_title("Liquid Level", color='black', fontsize=12, fontweight='bold', pad=10)
        self.level_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.level_ax.set_axisbelow(True)
        
        # Apply styling to all axes
        for ax in [self.flow_ax, self.pressure_ax, self.temp_ax, self.level_ax]:
            ax.set_facecolor('white')
            ax.tick_params(colors='black', labelsize=9)
            for spine in ax.spines.values():
                spine.set_color('black')
                spine.set_linewidth(1)
        
        self.multi_fig.tight_layout(pad=2.0)
        self.multi_canvas.draw()
    
    def on_axis_change(self, *args):
        """Handle axis selection change"""
        x_axis_type = self.x_axis_combo.get()
        y_axis_type = self.y_axis_combo.get()
        self.plot_xy_graph(x_axis_type, y_axis_type, [], [])
    
    def plot_xy_graph(self, x_axis_type, y_axis_type, x_data, y_data):
        """Plot X vs Y with any combination of parameters"""
        self.main_ax.clear()
        
        # Get the appropriate data arrays based on selected axes
        param_arrays = {
            'Time': self.flow_x_data,
            'Flow Rate': self.flow_y_data,
            'Pressure': self.pressure_y_data,
            'Temperature': self.temp_y_data,
            'Level': self.level_y_data
        }
        
        if x_axis_type in param_arrays and y_axis_type in param_arrays:
            x_param = param_arrays[x_axis_type]
            y_param = param_arrays[y_axis_type]
        else:
            x_param = x_data if x_data else []
            y_param = y_data if y_data else []
        
        # Define styles for each parameter
        styles = {
            'Flow Rate': {'ylabel': 'Flow Rate (ml/min)', 'unit': 'ml/min'},
            'Pressure': {'ylabel': 'Pressure (PSI)', 'unit': 'PSI'},
            'Temperature': {'ylabel': 'Temperature (°C)', 'unit': '°C'},
            'Level': {'ylabel': 'Liquid Level (%)', 'unit': '%'},
            'Time': {'ylabel': 'Time (s)', 'unit': 's'}
        }
        
        x_style = styles.get(x_axis_type, {'ylabel': x_axis_type, 'unit': ''})
        y_style = styles.get(y_axis_type, {'ylabel': y_axis_type, 'unit': ''})
        
        # Use the data from param_arrays or fallback
        if len(x_param) > 0 and len(y_param) > 0:
            x_plot = list(x_param)
            y_plot = list(y_param)
        elif len(x_data) > 0 and len(y_data) > 0:
            x_plot = x_data
            y_plot = y_data
        else:
            # Generate demo data - clean sine waves
            x_demo = np.linspace(0, 60, 200)
            if y_axis_type == 'Flow Rate':
                y_demo = 1.5 + 0.3 * np.sin(2 * np.pi * x_demo / 20)
            elif y_axis_type == 'Pressure':
                y_demo = 10 + 2 * np.sin(2 * np.pi * x_demo / 15)
            elif y_axis_type == 'Temperature':
                y_demo = 25 + 5 * np.sin(2 * np.pi * x_demo / 25)
            elif y_axis_type == 'Level':
                y_demo = 50 + 20 * np.sin(2 * np.pi * x_demo / 30)
            else:
                y_demo = 10 + 2 * np.sin(2 * np.pi * x_demo / 15)
            x_plot = x_demo.tolist()
            y_plot = y_demo.tolist()
        
        # Plot the data
        self.main_ax.plot(x_plot, y_plot, color='#2E86AB', linewidth=2.5, alpha=0.85)
        
        # Formatting
        self.main_ax.set_facecolor('white')
        self.main_ax.set_xlabel(x_style['ylabel'], color='black', fontsize=13)
        self.main_ax.set_ylabel(y_style['ylabel'], color='black', fontsize=13)
        self.main_ax.set_title(f"{y_axis_type} vs {x_axis_type}", color='black', fontsize=14, fontweight='bold', pad=15)
        
        # Subtle grid
        self.main_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5, which='both')
        self.main_ax.set_axisbelow(True)
        
        # Clean tick styling
        self.main_ax.tick_params(colors='black', labelsize=10, width=1)
        
        # Clean spines
        for spine in self.main_ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
        
        # Set axis limits
        if len(x_plot) > 0 and len(y_plot) > 0:
            x_margin = (max(x_plot) - min(x_plot)) * 0.05 if max(x_plot) > min(x_plot) else 1
            y_margin = (max(y_plot) - min(y_plot)) * 0.1 if max(y_plot) > min(y_plot) else 1
            self.main_ax.set_xlim(min(x_plot) - x_margin, max(x_plot) + x_margin)
            self.main_ax.set_ylim(min(y_plot) - y_margin, max(y_plot) + y_margin)
        
        self.main_fig.tight_layout(pad=2.0)
        self.main_canvas.draw()
    
    def update_statistics(self):
        """Calculate and update real-time statistics"""
        try:
            # Flow statistics
            if len(self.flow_y_data) > 0:
                flow_mean = np.mean(self.flow_y_data)
                flow_std = np.std(self.flow_y_data)
                flow_min = np.min(self.flow_y_data)
                flow_max = np.max(self.flow_y_data)
                self.flow_stats_label.configure(text=f'Mean: {flow_mean:.2f} | Std: {flow_std:.2f} | Range: [{flow_min:.2f}, {flow_max:.2f}]')
            else:
                self.flow_stats_label.configure(text='Mean: N/A | Std: N/A')
            
            # Pressure statistics
            if len(self.pressure_y_data) > 0:
                pressure_mean = np.mean(self.pressure_y_data)
                pressure_std = np.std(self.pressure_y_data)
                pressure_min = np.min(self.pressure_y_data)
                pressure_max = np.max(self.pressure_y_data)
                self.pressure_stats_label.configure(text=f'Mean: {pressure_mean:.2f} | Std: {pressure_std:.2f} | Range: [{pressure_min:.2f}, {pressure_max:.2f}]')
            else:
                self.pressure_stats_label.configure(text='Mean: N/A | Std: N/A')
            
            # Temperature statistics
            if len(self.temp_y_data) > 0:
                temp_mean = np.mean(self.temp_y_data)
                temp_std = np.std(self.temp_y_data)
                temp_min = np.min(self.temp_y_data)
                temp_max = np.max(self.temp_y_data)
                self.temp_stats_label.configure(text=f'Mean: {temp_mean:.2f} | Std: {temp_std:.2f} | Range: [{temp_min:.2f}, {temp_max:.2f}]')
            else:
                self.temp_stats_label.configure(text='Mean: N/A | Std: N/A')
            
            # Level statistics
            if len(self.level_y_data) > 0:
                level_mean = np.mean(self.level_y_data)
                level_std = np.std(self.level_y_data)
                level_min = np.min(self.level_y_data)
                level_max = np.max(self.level_y_data)
                self.level_stats_label.configure(text=f'Mean: {level_mean:.2f} | Std: {level_std:.2f} | Range: [{level_min:.2f}, {level_max:.2f}]')
            else:
                self.level_stats_label.configure(text='Mean: N/A | Std: N/A')
        except Exception as e:
            print(f"Error updating statistics: {e}")
    
    # --- Event Handlers ---
    def start_recording(self):
        """Start recording experiment - continues from last point if data exists"""
        try:
            file_name = self.exp_name_entry.get().strip()
            if not file_name:
                messagebox.showerror('Error', 'Please enter an experiment name before starting recording.')
                return
            
            if not re.match(r'^[a-zA-Z0-9_-]+$', file_name):
                messagebox.showerror('Error', 'Experiment name can only contain letters, numbers, underscores, and hyphens.')
                return
            
            flow_rate = float(self.flow_rate_entry.get())
            duration = int(self.duration_entry.get())
            valve_setting = {'valve1': self.valve_var.get() == 'main', 'valve2': self.valve_var.get() == 'rinsing'}
            
            self.current_flow_rate = flow_rate
            experiment_program = [{'duration': duration, 'flow_rate': flow_rate, 'valve_setting': valve_setting}]
            
            # Check if this is a new experiment or continuation
            is_new_experiment = not self.data_handler.file_path or not os.path.exists(self.data_handler.file_path)
            
            if is_new_experiment:
                # New experiment - save metadata and create new file
                metadata = {
                    'name': file_name,
                    'description': self.exp_desc_entry.get().strip(),
                    'tags': [tag.strip() for tag in self.exp_tags_entry.get().split(',') if tag.strip()],
                    'operator': self.exp_operator_entry.get().strip(),
                    'start_time': datetime.now().isoformat()
                }
                self.data_handler.set_custom_filename(file_name)
                self.data_handler.set_metadata(metadata)
                self.last_total_time = 0.0
                self.experiment_base_time = time.time()
            else:
                # Continuing existing experiment
                if self.experiment_base_time is None:
                    if len(self.flow_x_data) > 0:
                        self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
                        self.experiment_base_time = time.time() - self.last_total_time
                    else:
                        self.last_total_time = 0.0
                        self.experiment_base_time = time.time()
            
            if self.update_queue:
                self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Recording...', 'red')))
                if is_new_experiment:
                    self.update_queue.put(('UPDATE_FILE', f"{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"))
                self.update_queue.put(('UPDATE_READINGS', (0, 0, flow_rate, 0)))
            
            threading.Thread(target=self.experiment_thread,
                             args=(experiment_program, is_new_experiment),
                             daemon=True).start()
        except ValueError:
            messagebox.showerror('Error', 'Invalid input for Flow Rate or Duration. Please enter numbers.')
    
    def stop_recording(self):
        """Stop recording - preserves data for continuation"""
        self.exp_manager.stop_experiment()
        
        # Update last total time based on current data
        if len(self.flow_x_data) > 0:
            self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
        
        if self.update_queue:
            self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Stopped', 'orange')))
            self.update_queue.put(('UPDATE_STATUS', f'Recording stopped. Total time: {self.last_total_time:.1f}s. Click Start to continue.'))
    
    def finish_recording(self):
        """Finish recording gracefully - closes file and resets"""
        self.exp_manager.finish_experiment()
        
        # Close the file and reset for new experiment
        if self.data_handler.file_path:
            self.data_handler.close_file()
        
        # Reset cumulative time for next experiment
        self.last_total_time = 0.0
        self.experiment_base_time = None
        
        if self.update_queue:
            self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Completed', 'green')))
            self.update_queue.put(('UPDATE_STATUS', 'Experiment finished. Ready for new experiment.'))
    
    def clear_graph(self):
        """Clear all graphs"""
        self.flow_x_data.clear()
        self.flow_y_data.clear()
        self.pressure_x_data.clear()
        self.pressure_y_data.clear()
        self.temp_x_data.clear()
        self.temp_y_data.clear()
        self.level_x_data.clear()
        self.level_y_data.clear()
        
        x_axis_type = self.x_axis_combo.get()
        y_axis_type = self.y_axis_combo.get()
        self.plot_xy_graph(x_axis_type, y_axis_type, [], [])
        
        if self.update_queue:
            self.update_queue.put(('UPDATE_STATUS', 'Graph cleared.'))
            self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Ready', 'green')))
    
    def update_flow(self):
        """Update flow rate - works during experiment for real-time changes"""
        try:
            new_flow_rate = float(self.flow_rate_entry.get())
            
            # Validate flow rate range
            if new_flow_rate < 0:
                messagebox.showerror('Error', 'Flow rate cannot be negative.')
                return
            if new_flow_rate > 10:
                if not messagebox.askyesno('Warning', f'Flow rate {new_flow_rate} ml/min is high. Continue?'):
                    return
            
            if new_flow_rate != self.current_flow_rate:
                old_flow_rate = self.current_flow_rate
                self.current_flow_rate = new_flow_rate
                
                # Update hardware controller immediately
                self.hw_controller.set_pump_flow_rate(new_flow_rate)
                
                # Update status
                if self.update_queue:
                    status_msg = f'Flow rate updated: {old_flow_rate:.2f} → {new_flow_rate:.2f} ml/min'
                    self.update_queue.put(('UPDATE_STATUS', status_msg))
                
                # Log flow change to data file if recording
                if self.data_handler.file_path and self.data_handler.file:
                    self.data_handler.log_flow_change(new_flow_rate)
                
                # Update current readings display
                if self.update_queue:
                    self.update_queue.put(('UPDATE_READINGS', (0, 0, new_flow_rate, 0)))
                
                # If experiment is running, show confirmation
                if self.exp_manager.is_running:
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_STATUS', f'Flow updated during experiment: {new_flow_rate:.2f} ml/min (will apply on next reading)'))
            else:
                # Flow rate is the same, just confirm
                if self.update_queue:
                    self.update_queue.put(('UPDATE_STATUS', f'Flow rate already set to {new_flow_rate:.2f} ml/min'))
                
        except ValueError:
            messagebox.showerror('Error', 'Invalid flow rate. Please enter a valid number.')
        except Exception as e:
            messagebox.showerror('Error', f'Error updating flow rate: {e}')
    
    def export_excel(self):
        """Export data to Excel"""
        try:
            if self.data_handler.file_path and os.path.exists(self.data_handler.file_path):
                filename = filedialog.asksaveasfilename(
                    defaultextension='.xlsx',
                    filetypes=[('Excel Files', '*.xlsx')],
                    title='Save Excel File As'
                )
                if filename:
                    if not filename.endswith('.xlsx'):
                        filename += '.xlsx'
                    success = self.data_handler.export_to_excel(filename)
                    if success:
                        messagebox.showinfo('Export Complete', f'Excel file exported successfully!\n{filename}')
                    else:
                        messagebox.showerror('Error', 'Failed to export Excel file. Check console for details.')
            else:
                messagebox.showerror('Error', 'No experiment data to export. Run an experiment first.')
        except Exception as e:
            messagebox.showerror('Error', f'Error exporting to Excel: {e}\n\nPlease check:\n- File is not open in another program\n- You have write permissions\n- Disk has enough space')
    
    def export_graph_png(self):
        """Export current graph as PNG"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension='.png',
                filetypes=[('PNG Files', '*.png')]
            )
            if filename:
                if self.graph_mode_var.get() == "multi":
                    self.multi_fig.savefig(filename, dpi=300, bbox_inches='tight')
                else:
                    self.main_fig.savefig(filename, dpi=300, bbox_inches='tight')
                messagebox.showinfo('Export Complete', 'Graph exported as PNG successfully!')
        except Exception as e:
            messagebox.showerror('Error', f'Error exporting graph: {e}')
    
    def export_graph_pdf(self):
        """Export current graph as PDF"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension='.pdf',
                filetypes=[('PDF Files', '*.pdf')]
            )
            if filename:
                if self.graph_mode_var.get() == "multi":
                    self.multi_fig.savefig(filename, bbox_inches='tight')
                else:
                    self.main_fig.savefig(filename, bbox_inches='tight')
                messagebox.showinfo('Export Complete', 'Graph exported as PDF successfully!')
        except Exception as e:
            messagebox.showerror('Error', f'Error exporting graph: {e}')
    
    def experiment_thread(self, experiment_program, is_new_experiment=True):
        """Run experiment in separate thread - continues from last point if resuming"""
        self.exp_manager.is_running = True
        
        if is_new_experiment:
            if self.update_queue:
                self.update_queue.put(('UPDATE_STATUS', 'Starting new experiment...'))
            self.data_handler.create_new_file()
            self.experiment_base_time = time.time()
            self.last_total_time = 0.0
        else:
            if self.update_queue:
                self.update_queue.put(('UPDATE_STATUS', f'Resuming experiment from {self.last_total_time:.1f}s...'))
            if not self.data_handler.file_path or not os.path.exists(self.data_handler.file_path):
                self.data_handler.create_new_file()
                self.experiment_base_time = time.time()
                self.last_total_time = 0.0
            else:
                if self.experiment_base_time is None:
                    if len(self.flow_x_data) > 0:
                        self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
                        self.experiment_base_time = time.time() - self.last_total_time
                    else:
                        self.experiment_base_time = time.time()
                        self.last_total_time = 0.0
        
        experiment_start_time = self.experiment_base_time
        
        for step in experiment_program:
            if not self.exp_manager.is_running:
                break
            
            duration = step.get('duration')
            flow_rate = self.current_flow_rate
            valve_setting = step.get('valve_setting', {'valve1': True, 'valve2': False})
            
            if self.update_queue:
                self.update_queue.put(('UPDATE_STATUS', f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min"))
            
            self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
            self.exp_manager.hw_controller.set_valves(valve_setting['valve1'], valve_setting['valve2'])
            
            start_time = time.time()
            
            while time.time() - start_time < duration and self.exp_manager.is_running:
                if not self.exp_manager.perform_safety_checks():
                    break
                
                # Check for flow rate updates
                if self.current_flow_rate != flow_rate:
                    old_flow_rate = flow_rate
                    flow_rate = self.current_flow_rate
                    self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_STATUS', f'Flow changed during experiment: {old_flow_rate:.2f} → {flow_rate:.2f} ml/min'))
                
                current_time = time.time()
                remaining_time = duration - (current_time - start_time)
                elapsed_time_from_start = current_time - experiment_start_time
                
                pump_data = self.exp_manager.hw_controller.read_pump_data()
                pressure = self.exp_manager.hw_controller.read_pressure_sensor()
                temperature = self.exp_manager.hw_controller.read_temperature_sensor()
                level = self.exp_manager.hw_controller.read_level_sensor()
                
                if self.update_queue:
                    self.update_queue.put(('UPDATE_STATUS', f"Running: {remaining_time:.0f}s remaining, Flow={flow_rate}ml/min"))
                
                # Update data arrays
                self.flow_x_data.append(elapsed_time_from_start)
                self.flow_y_data.append(pump_data['flow'])
                self.pressure_x_data.append(elapsed_time_from_start)
                self.pressure_y_data.append(pressure)
                self.temp_x_data.append(elapsed_time_from_start)
                self.temp_y_data.append(temperature)
                self.level_x_data.append(elapsed_time_from_start)
                self.level_y_data.append(level * 100)
                
                data_point = {
                    "time": elapsed_time_from_start,
                    "flow_setpoint": self.current_flow_rate,
                    "pump_flow_read": pump_data['flow'],
                    "pressure_read": pressure,
                    "temp_read": temperature,
                    "level_read": level
                }
                
                self.data_handler.append_data(data_point)
                
                # Update graphs via queue
                if self.update_queue:
                    self.update_queue.put(('UPDATE_GRAPH1', (list(self.flow_x_data), list(self.flow_y_data))))
                    self.update_queue.put(('UPDATE_GRAPH2', (list(self.pressure_x_data), list(self.pressure_y_data))))
                    self.update_queue.put(('UPDATE_GRAPH3', (list(self.temp_x_data), list(self.temp_y_data))))
                    self.update_queue.put(('UPDATE_GRAPH4', (list(self.level_x_data), list(self.level_y_data))))
                time.sleep(1)
        
        self.exp_manager.stop_experiment()
        
        # Update last total time
        if len(self.flow_x_data) > 0:
            self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
        
        if self.update_queue:
            self.update_queue.put(('UPDATE_STATUS', f'Experiment paused. Total time: {self.last_total_time:.1f}s. Click Start to continue.'))
            self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Paused', 'orange')))

