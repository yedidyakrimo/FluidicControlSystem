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
        
        # Keithley 2450 control variables
        self.keithley_mode = "voltage"  # "voltage" or "current"
        self.keithley_bias_value = 0.0
        self.keithley_output_enabled = False
        self.keithley_current_limit = 0.1
        self.keithley_voltage_data = []
        self.keithley_current_data = []
        self.keithley_time_data = []
        
        # Create widgets
        self.create_widgets()
        
        # Setup graphs
        self.setup_graphs()
        
        # Refresh pump status on startup
        self.after(500, self.refresh_pump_status)
        
        # Refresh Keithley status on startup
        self.after(1000, self.refresh_keithley_status)
    
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
        
        # Pump Connection Status
        pump_status_frame = ctk.CTkFrame(left_frame)
        pump_status_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(pump_status_frame, text="Vapourtec SF-10 Pump Status", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        pump_info_frame = ctk.CTkFrame(pump_status_frame)
        pump_info_frame.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(pump_info_frame, text='Status:', width=100).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.pump_status_label = ctk.CTkLabel(pump_info_frame, text='Checking...', width=250, anchor='w')
        self.pump_status_label.grid(row=0, column=1, padx=5, pady=2, sticky='w')
        
        ctk.CTkLabel(pump_info_frame, text='Port:', width=100).grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.pump_port_label = ctk.CTkLabel(pump_info_frame, text='N/A', width=250, anchor='w')
        self.pump_port_label.grid(row=1, column=1, padx=5, pady=2, sticky='w')
        
        ctk.CTkLabel(pump_info_frame, text='Flow Rate:', width=100).grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.pump_flow_label = ctk.CTkLabel(pump_info_frame, text='N/A', width=250, anchor='w')
        self.pump_flow_label.grid(row=2, column=1, padx=5, pady=2, sticky='w')
        
        ctk.CTkLabel(pump_info_frame, text='Max Flow:', width=100).grid(row=3, column=0, padx=5, pady=2, sticky='w')
        self.pump_max_flow_label = ctk.CTkLabel(pump_info_frame, text='5.0 ml/min', width=250, anchor='w', text_color='gray')
        self.pump_max_flow_label.grid(row=3, column=1, padx=5, pady=2, sticky='w')
        
        # Control buttons
        pump_btn_frame = ctk.CTkFrame(pump_status_frame)
        pump_btn_frame.pack(pady=5)
        self.create_blue_button(pump_btn_frame, text='🔄 Refresh Status', command=self.refresh_pump_status, width=120, height=30).pack(side='left', padx=2)
        
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
        ctk.CTkLabel(flow_frame, text='(Max: 5.0)', width=80, font=('Helvetica', 9), text_color='gray').pack(side='left', padx=2)
        
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
        
        self.start_btn = self.create_blue_button(control_frame, text='Start Recording',
                                                 command=self.start_recording, width=150, height=40)
        self.start_btn.pack(pady=2)
        
        self.stop_btn = self.create_blue_button(control_frame, text='Stop Recording',
                                                command=self.stop_recording, width=150, height=40,
                                                fg_color='#0D47A1', hover_color='#0C3A7A')
        self.stop_btn.pack(pady=2)
        
        self.finish_btn = self.create_blue_button(control_frame, text='Finish Recording',
                                                  command=self.finish_recording, width=150, height=40,
                                                  fg_color='#0C6CC0', hover_color='#0A518A')
        self.finish_btn.pack(pady=2)
        
        self.update_flow_btn = self.create_blue_button(control_frame, text='Update Flow',
                                                      command=self.update_flow, width=150)
        self.update_flow_btn.pack(pady=2)
        
        self.clear_graph_btn = self.create_blue_button(control_frame, text='Clear Graph',
                                                       command=self.clear_graph, width=150)
        self.clear_graph_btn.pack(pady=2)
        
        export_menu_frame = ctk.CTkFrame(control_frame)
        export_menu_frame.pack(pady=2)
        
        ctk.CTkLabel(export_menu_frame, text='Export:', width=80).pack(side='left', padx=5)
        self.export_btn = self.create_blue_button(export_menu_frame, text='Excel',
                                                 command=self.export_excel, width=100)
        self.export_btn.pack(side='left', padx=2)
        
        self.create_blue_button(export_menu_frame, text='PNG', command=self.export_graph_png, width=100).pack(side='left', padx=2)
        
        self.create_blue_button(export_menu_frame, text='PDF', command=self.export_graph_pdf, width=100).pack(side='left', padx=2)
        
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
        
        # ========== KEITHLEY 2450 CONTROL PANEL ==========
        keithley_frame = ctk.CTkFrame(left_frame)
        keithley_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(keithley_frame, text="Keithley 2450 SMU Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        # SMU Connection Status
        smu_status_frame = ctk.CTkFrame(keithley_frame)
        smu_status_frame.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(smu_status_frame, text='Status:', width=100).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.keithley_status_label = ctk.CTkLabel(smu_status_frame, text='Checking...', width=250, anchor='w')
        self.keithley_status_label.grid(row=0, column=1, padx=5, pady=2, sticky='w')
        
        # Measurement Mode Selector
        mode_frame = ctk.CTkFrame(keithley_frame)
        mode_frame.pack(fill='x', padx=5, pady=5)
        ctk.CTkLabel(mode_frame, text="Measurement Mode:", font=('Helvetica', 12, 'bold')).pack(pady=2)
        
        self.keithley_mode_var = ctk.StringVar(value="voltage")
        mode_radio_frame = ctk.CTkFrame(mode_frame)
        mode_radio_frame.pack(pady=2)
        ctk.CTkRadioButton(mode_radio_frame, text="Source Voltage / Measure Current", 
                          variable=self.keithley_mode_var, value="voltage",
                          command=self.on_keithley_mode_change).pack(side='left', padx=5)
        ctk.CTkRadioButton(mode_radio_frame, text="Source Current / Measure Voltage", 
                          variable=self.keithley_mode_var, value="current",
                          command=self.on_keithley_mode_change).pack(side='left', padx=5)
        
        # Bias Input Field (dynamic label)
        bias_frame = ctk.CTkFrame(keithley_frame)
        bias_frame.pack(fill='x', padx=5, pady=5)
        self.keithley_bias_label = ctk.CTkLabel(bias_frame, text='Bias Voltage (V):', width=150)
        self.keithley_bias_label.pack(side='left', padx=5)
        self.keithley_bias_entry = ctk.CTkEntry(bias_frame, width=100)
        self.keithley_bias_entry.insert(0, '0.0')
        self.keithley_bias_entry.pack(side='left', padx=5)
        
        # Current Limit (for voltage mode)
        current_limit_frame = ctk.CTkFrame(keithley_frame)
        current_limit_frame.pack(fill='x', padx=5, pady=5)
        ctk.CTkLabel(current_limit_frame, text='Current Limit (A):', width=150).pack(side='left', padx=5)
        self.keithley_current_limit_entry = ctk.CTkEntry(current_limit_frame, width=100)
        self.keithley_current_limit_entry.insert(0, '0.1')
        self.keithley_current_limit_entry.pack(side='left', padx=5)
        
        # Voltage Limit (for current mode) - initially hidden
        voltage_limit_frame = ctk.CTkFrame(keithley_frame)
        voltage_limit_frame.pack(fill='x', padx=5, pady=5)
        ctk.CTkLabel(voltage_limit_frame, text='Voltage Limit (V):', width=150).pack(side='left', padx=5)
        self.keithley_voltage_limit_entry = ctk.CTkEntry(voltage_limit_frame, width=100)
        self.keithley_voltage_limit_entry.insert(0, '20.0')
        # Initially hidden (only shown in current mode)
        self.keithley_voltage_limit_entry.pack_forget()
        
        # Enable SMU Output Toggle
        output_frame = ctk.CTkFrame(keithley_frame)
        output_frame.pack(fill='x', padx=5, pady=5)
        self.keithley_output_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(output_frame, text="Enable SMU Output", variable=self.keithley_output_var,
                     command=self.on_keithley_output_toggle).pack(side='left', padx=5)
        
        # Current Readings Display
        readings_smu_frame = ctk.CTkFrame(keithley_frame)
        readings_smu_frame.pack(fill='x', padx=5, pady=5)
        ctk.CTkLabel(readings_smu_frame, text="SMU Readings", font=('Helvetica', 12, 'bold')).pack(pady=2)
        
        smu_readings_grid = ctk.CTkFrame(readings_smu_frame)
        smu_readings_grid.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(smu_readings_grid, text='Voltage:', width=120).grid(row=0, column=0, padx=5, pady=2)
        self.keithley_voltage_label = ctk.CTkLabel(smu_readings_grid, text='N/A', width=180)
        self.keithley_voltage_label.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(smu_readings_grid, text='Current:', width=120).grid(row=1, column=0, padx=5, pady=2)
        self.keithley_current_label = ctk.CTkLabel(smu_readings_grid, text='N/A', width=180)
        self.keithley_current_label.grid(row=1, column=1, padx=5, pady=2)
        
        # Refresh SMU Status button
        smu_btn_frame = ctk.CTkFrame(keithley_frame)
        smu_btn_frame.pack(pady=5)
        self.create_blue_button(smu_btn_frame, text='🔄 Refresh SMU Status', 
                               command=self.refresh_keithley_status, width=150, height=30).pack(side='left', padx=2)
        
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
                                            values=['Time', 'Flow Rate', 'Pressure', 'Temperature', 'Level', 'Voltage', 'Current'],
                                            width=150, command=self.on_axis_change)
        self.x_axis_combo.set('Time')
        self.x_axis_combo.pack(side='left', padx=5)
        
        ctk.CTkLabel(axis_label_frame, text='Y-Axis:', width=60).pack(side='left', padx=5)
        self.y_axis_combo = ctk.CTkComboBox(axis_label_frame,
                                            values=['Flow Rate', 'Pressure', 'Temperature', 'Level', 'Voltage', 'Current'],
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
        # BUG FIX #1 & #4: Thread-safe access with lock and make copies
        with self.data_lock:
            flow_x_copy = list(self.flow_x_data) if self.flow_x_data else []
            flow_y_copy = list(self.flow_y_data) if self.flow_y_data else []
            pressure_x_copy = list(self.pressure_x_data) if self.pressure_x_data else []
            pressure_y_copy = list(self.pressure_y_data) if self.pressure_y_data else []
            temp_x_copy = list(self.temp_x_data) if self.temp_x_data else []
            temp_y_copy = list(self.temp_y_data) if self.temp_y_data else []
            level_x_copy = list(self.level_x_data) if self.level_x_data else []
            level_y_copy = list(self.level_y_data) if self.level_y_data else []
        
        # Flow graph
        self.flow_ax.clear()
        if len(flow_x_copy) > 0 and len(flow_y_copy) > 0:
            min_len = min(len(flow_x_copy), len(flow_y_copy))
            self.flow_ax.plot(flow_x_copy[:min_len], flow_y_copy[:min_len], color='#2E86AB', linewidth=2, alpha=0.85)
            # Auto-scale axes
            if min_len > 0:
                self.flow_ax.relim()
                self.flow_ax.autoscale()
        self.flow_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.flow_ax.set_ylabel("Flow Rate (ml/min)", color='black', fontsize=10)
        self.flow_ax.set_title("Flow Rate", color='black', fontsize=12, fontweight='bold', pad=10)
        self.flow_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.flow_ax.set_axisbelow(True)
        
        # Pressure graph
        self.pressure_ax.clear()
        if len(pressure_x_copy) > 0 and len(pressure_y_copy) > 0:
            min_len = min(len(pressure_x_copy), len(pressure_y_copy))
            self.pressure_ax.plot(pressure_x_copy[:min_len], pressure_y_copy[:min_len], color='#A23B72', linewidth=2, alpha=0.85)
            # Auto-scale axes
            if min_len > 0:
                self.pressure_ax.relim()
                self.pressure_ax.autoscale()
        self.pressure_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.pressure_ax.set_ylabel("Pressure (PSI)", color='black', fontsize=10)
        self.pressure_ax.set_title("Pressure", color='black', fontsize=12, fontweight='bold', pad=10)
        self.pressure_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.pressure_ax.set_axisbelow(True)
        
        # Temperature graph
        self.temp_ax.clear()
        if len(temp_x_copy) > 0 and len(temp_y_copy) > 0:
            min_len = min(len(temp_x_copy), len(temp_y_copy))
            self.temp_ax.plot(temp_x_copy[:min_len], temp_y_copy[:min_len], color='#F18F01', linewidth=2, alpha=0.85)
            # Auto-scale axes
            if min_len > 0:
                self.temp_ax.relim()
                self.temp_ax.autoscale()
        self.temp_ax.set_xlabel("Time (s)", color='black', fontsize=10)
        self.temp_ax.set_ylabel("Temperature (°C)", color='black', fontsize=10)
        self.temp_ax.set_title("Temperature", color='black', fontsize=12, fontweight='bold', pad=10)
        self.temp_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.temp_ax.set_axisbelow(True)
        
        # Level graph
        self.level_ax.clear()
        if len(level_x_copy) > 0 and len(level_y_copy) > 0:
            min_len = min(len(level_x_copy), len(level_y_copy))
            self.level_ax.plot(level_x_copy[:min_len], level_y_copy[:min_len], color='#06A77D', linewidth=2, alpha=0.85)
            # Auto-scale axes
            if min_len > 0:
                self.level_ax.relim()
                self.level_ax.autoscale()
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
        
        # BUG FIX #1 & #4: Thread-safe access with lock and make copies
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
        
        # Get the appropriate data arrays based on selected axes
        # For X-axis: Time uses flow_x_data (or any time array), other params use their Y data
        # For Y-axis: use the corresponding Y data array
        x_param = []
        y_param = []
        
        if x_axis_type == 'Time':
            # Use time from any available data array (they should all have the same time)
            if len(flow_x_copy) > 0:
                x_param = flow_x_copy
            elif len(pressure_x_copy) > 0:
                x_param = pressure_x_copy
            elif len(temp_x_copy) > 0:
                x_param = temp_x_copy
            elif len(level_x_copy) > 0:
                x_param = level_x_copy
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
        
        # If X is Time, make sure we use the correct time array that matches the Y data
        if x_axis_type == 'Time' and len(y_param) > 0:
            # Use the time array that corresponds to the Y-axis data
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
        
        # If we have x_data and y_data passed in, use those instead (override above)
        if len(x_data) > 0:
            x_param = x_data
        if len(y_data) > 0:
            y_param = y_data
        
        # Define styles for each parameter
        styles = {
            'Flow Rate': {'ylabel': 'Flow Rate (ml/min)', 'unit': 'ml/min'},
            'Pressure': {'ylabel': 'Pressure (PSI)', 'unit': 'PSI'},
            'Temperature': {'ylabel': 'Temperature (°C)', 'unit': '°C'},
            'Level': {'ylabel': 'Liquid Level (%)', 'unit': '%'},
            'Time': {'ylabel': 'Time (s)', 'unit': 's'},
            'Voltage': {'ylabel': 'Voltage (V)', 'unit': 'V'},
            'Current': {'ylabel': 'Current (A)', 'unit': 'A'}
        }
        
        x_style = styles.get(x_axis_type, {'ylabel': x_axis_type, 'unit': ''})
        y_style = styles.get(y_axis_type, {'ylabel': y_axis_type, 'unit': ''})
        
        # Use the data we extracted or fallback to demo data
        if len(x_param) > 0 and len(y_param) > 0:
            # Make sure arrays are the same length
            min_len = min(len(x_param), len(y_param))
            x_plot = list(x_param[:min_len])
            y_plot = list(y_param[:min_len])
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
            elif y_axis_type == 'Voltage':
                y_demo = 1.0 + 0.5 * np.sin(2 * np.pi * x_demo / 20)
            elif y_axis_type == 'Current':
                y_demo = 0.001 + 0.0005 * np.sin(2 * np.pi * x_demo / 20)
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
            # BUG FIX #4: Thread-safe access with lock and length validation
            with self.data_lock:
                # Flow statistics
                flow_y_copy = list(self.flow_y_data) if self.flow_y_data else []
                pressure_y_copy = list(self.pressure_y_data) if self.pressure_y_data else []
                temp_y_copy = list(self.temp_y_data) if self.temp_y_data else []
                level_y_copy = list(self.level_y_data) if self.level_y_data else []
            
            # Calculate statistics on copies to avoid race conditions
            if len(flow_y_copy) > 0:
                flow_mean = np.mean(flow_y_copy)
                flow_std = np.std(flow_y_copy)
                flow_min = np.min(flow_y_copy)
                flow_max = np.max(flow_y_copy)
                self.flow_stats_label.configure(text=f'Mean: {flow_mean:.2f} | Std: {flow_std:.2f} | Range: [{flow_min:.2f}, {flow_max:.2f}]')
            else:
                self.flow_stats_label.configure(text='Mean: N/A | Std: N/A')
            
            # Pressure statistics
            if len(pressure_y_copy) > 0:
                pressure_mean = np.mean(pressure_y_copy)
                pressure_std = np.std(pressure_y_copy)
                pressure_min = np.min(pressure_y_copy)
                pressure_max = np.max(pressure_y_copy)
                self.pressure_stats_label.configure(text=f'Mean: {pressure_mean:.2f} | Std: {pressure_std:.2f} | Range: [{pressure_min:.2f}, {pressure_max:.2f}]')
            else:
                self.pressure_stats_label.configure(text='Mean: N/A | Std: N/A')
            
            # Temperature statistics (filter out NaN values from disconnected sensor)
            temp_y_valid = [t for t in temp_y_copy if not (isinstance(t, float) and (np.isnan(t) or np.isinf(t)))]
            if len(temp_y_valid) > 0:
                temp_mean = np.mean(temp_y_valid)
                temp_std = np.std(temp_y_valid)
                temp_min = np.min(temp_y_valid)
                temp_max = np.max(temp_y_valid)
                self.temp_stats_label.configure(text=f'Mean: {temp_mean:.2f} | Std: {temp_std:.2f} | Range: [{temp_min:.2f}, {temp_max:.2f}]')
            else:
                self.temp_stats_label.configure(text='Mean: N/A | Std: N/A')
            
            # Level statistics
            if len(level_y_copy) > 0:
                level_mean = np.mean(level_y_copy)
                level_std = np.std(level_y_copy)
                level_min = np.min(level_y_copy)
                level_max = np.max(level_y_copy)
                self.level_stats_label.configure(text=f'Mean: {level_mean:.2f} | Std: {level_std:.2f} | Range: [{level_min:.2f}, {level_max:.2f}]')
            else:
                self.level_stats_label.configure(text='Mean: N/A | Std: N/A')
        except Exception as e:
            print(f"Error updating statistics: {e}")
    
    # --- Event Handlers ---
    def start_recording(self):
        """Start recording experiment - continues from last point if data exists"""
        print("[MAIN_TAB] start_recording() called")
        try:
            file_name = self.exp_name_entry.get().strip()
            print(f"[MAIN_TAB] Experiment name: {file_name}")
            if not file_name:
                messagebox.showerror('Error', 'Please enter an experiment name before starting recording.')
                return
            
            if not re.match(r'^[a-zA-Z0-9_-]+$', file_name):
                messagebox.showerror('Error', 'Experiment name can only contain letters, numbers, underscores, and hyphens.')
                return
            
            flow_rate = float(self.flow_rate_entry.get())
            print(f"[MAIN_TAB] Flow rate: {flow_rate} ml/min")
            
            # Validate flow rate range
            if flow_rate < 0:
                messagebox.showerror('Error', 'Flow rate cannot be negative.')
                return
            
            # Enforce maximum flow rate of 5.0 ml/min
            MAX_FLOW_RATE = 5.0
            if flow_rate > MAX_FLOW_RATE:
                messagebox.showwarning('Flow Rate Limit', 
                    f'Maximum flow rate is {MAX_FLOW_RATE} ml/min.\n'
                    f'Flow rate will be set to {MAX_FLOW_RATE} ml/min.')
                flow_rate = MAX_FLOW_RATE
                self.flow_rate_entry.delete(0, 'end')
                self.flow_rate_entry.insert(0, str(MAX_FLOW_RATE))
            
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
            
            print(f"[MAIN_TAB] Starting experiment thread with program: {experiment_program}")
            print(f"[MAIN_TAB] Is new experiment: {is_new_experiment}")
            thread = threading.Thread(target=self.experiment_thread,
                             args=(experiment_program, is_new_experiment),
                             daemon=True)
            thread.start()
            print(f"[MAIN_TAB] Thread started: {thread.is_alive()}")
        except ValueError as e:
            print(f"[MAIN_TAB ERROR] ValueError: {e}")
            messagebox.showerror('Error', 'Invalid input for Flow Rate or Duration. Please enter numbers.')
        except Exception as e:
            print(f"[MAIN_TAB ERROR] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror('Error', f'Unexpected error: {e}')
    
    def stop_recording(self):
        """Stop recording - preserves data for continuation"""
        self.exp_manager.stop_experiment()
        
        # Update last total time based on current data (thread-safe - BUG FIX #1)
        with self.data_lock:
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
        # BUG FIX #1: Thread-safe clearing with lock
        with self.data_lock:
            self.flow_x_data.clear()
            self.flow_y_data.clear()
            self.pressure_x_data.clear()
            self.pressure_y_data.clear()
            self.temp_x_data.clear()
            self.temp_y_data.clear()
            self.level_x_data.clear()
            self.level_y_data.clear()
            # Clear Keithley data
            self.keithley_voltage_data.clear()
            self.keithley_current_data.clear()
            self.keithley_time_data.clear()
        
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
                self.flow_rate_entry.delete(0, 'end')
                self.flow_rate_entry.insert(0, str(self.current_flow_rate))
                return
            
            # Enforce maximum flow rate of 5.0 ml/min
            MAX_FLOW_RATE = 5.0
            if new_flow_rate > MAX_FLOW_RATE:
                messagebox.showwarning('Flow Rate Limit', 
                    f'Maximum flow rate is {MAX_FLOW_RATE} ml/min.\n'
                    f'Flow rate will be set to {MAX_FLOW_RATE} ml/min.')
                new_flow_rate = MAX_FLOW_RATE
                self.flow_rate_entry.delete(0, 'end')
                self.flow_rate_entry.insert(0, str(MAX_FLOW_RATE))
            
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
    
    def refresh_pump_status(self):
        """Refresh pump connection status (with threading)"""
        print("DEBUG: Refresh pump button clicked")
        
        # 1. Update UI immediately (Main Thread)
        self.pump_status_label.configure(text="Scanning...", text_color='orange')
        
        # 2. Run logic in background thread
        threading.Thread(target=self._run_refresh_pump_logic, daemon=True).start()
    
    def _run_refresh_pump_logic(self):
        """Background thread for pump status refresh with smart reconnection"""
        try:
            import time
            
            # Step 1: Check current status first (with health check)
            print("[REFRESH] Checking current pump status...")
            pump_info = self.hw_controller.pump.get_info()
            
            # Step 2: If already connected and working, don't force reconnect
            if pump_info.get('connected', False) and not pump_info.get('simulation_mode', False):
                print("[REFRESH] ✅ Pump already connected and responsive - no reconnection needed")
                # Schedule UI update
                self.after(0, lambda: self._update_pump_ui(pump_info))
                return
            
            # Step 3: If not connected or in simulation mode, attempt force reconnection
            print("[REFRESH] Pump not connected or in simulation mode - attempting FORCE reconnection...")
            
            if hasattr(self.hw_controller.pump, 'force_reconnect'):
                reconnect_success = self.hw_controller.pump.force_reconnect()
            else:
                # Fallback to regular connect if force_reconnect doesn't exist
                reconnect_success = self.hw_controller.pump.connect()
            
            # Step 4: Handle success and failure differently
            if reconnect_success:
                print("[REFRESH] ✅ Pump force reconnection successful")
                # Give the pump more time to stabilize after reconnection
                # Increased to 2.0 seconds to ensure hardware is fully ready
                time.sleep(2.0)
                
                # CRITICAL FIX: Don't call get_info() after successful reconnection
                # The health check in get_info() might fail while pump is still initializing,
                # causing it to disconnect the pump again. Instead, trust force_reconnect()
                # and manually construct the pump_info dictionary with positive values.
                pump_info = {
                    "device_name": self.hw_controller.pump.device_name,
                    "port": self.hw_controller.pump.port,
                    "connected": True,  # Trust force_reconnect result
                    "simulation_mode": False,
                    "is_running": self.hw_controller.pump.is_running,
                    "current_flow_rate": self.hw_controller.pump.pump_setpoint_flow,
                    "tube_type": self.hw_controller.pump.tube_type,
                    "max_flow_rate": self.hw_controller.pump.MAX_FLOW_RATE,
                    "status": "Connected",
                    "status_color": "green"
                }
                print("[REFRESH] Trusting force_reconnect result - marking as connected without health check")
            else:
                print("[REFRESH] ❌ Pump force reconnection failed - staying in simulation mode")
                # Only call get_info() if reconnection failed to read actual error/disconnected state
                pump_info = self.hw_controller.pump.get_info()
            
            # Step 5: Schedule UI update back on Main Thread
            self.after(0, lambda: self._update_pump_ui(pump_info))
        except Exception as e:
            error_msg = str(e)
            print(f"[REFRESH] Error during pump refresh: {error_msg}")
            self.after(0, lambda: self._update_pump_error(error_msg))
    
    def _update_pump_ui(self, pump_info):
        """Update pump UI with results (called on main thread)"""
        try:
            # Update status label with color
            status_text = pump_info.get('status', 'Unknown')
            status_color = pump_info.get('status_color', 'gray')
            self.pump_status_label.configure(text=status_text, text_color=status_color)
            
            # Update port
            port_text = pump_info.get('port', 'N/A')
            self.pump_port_label.configure(text=port_text)
            
            # Update flow rate
            flow_rate = pump_info.get('current_flow_rate', 0.0)
            self.pump_flow_label.configure(text=f'{flow_rate:.2f} ml/min')
            
            # Update max flow rate display
            max_flow = pump_info.get('max_flow_rate', 5.0)
            self.pump_max_flow_label.configure(text=f'{max_flow:.1f} ml/min')
        except Exception as e:
            print(f"Error updating pump UI: {e}")
            self.pump_status_label.configure(text='Error', text_color='red')
    
    def _update_pump_error(self, error_msg):
        """Update pump UI with error (called on main thread)"""
        print(f"Error refreshing pump status: {error_msg}")
        self.pump_status_label.configure(text='Error', text_color='red')
    
    def refresh_keithley_status(self):
        """Refresh Keithley 2450 SMU connection status (with threading)"""
        print("DEBUG: Refresh Keithley button clicked")
        
        # 1. Update UI immediately (Main Thread)
        self.keithley_status_label.configure(text="Scanning...", text_color='orange')
        
        # 2. Run logic in background thread
        threading.Thread(target=self._run_refresh_keithley_logic, daemon=True).start()
    
    def _run_refresh_keithley_logic(self):
        """Background thread for Keithley status refresh with re-initialization"""
        try:
            # Step A: Check if software object exists
            # Step B: Active Health Check (performed in get_smu_info())
            if self.hw_controller.smu is not None and hasattr(self.hw_controller, 'smu'):
                smu_info = self.hw_controller.get_smu_info()
                
                # Step C: If disconnected, attempt re-initialization (re-scan resources)
                if not smu_info.get('connected', False):
                    print("[REFRESH] SMU disconnected, attempting re-initialization...")
                    # Try to auto-detect and reconnect
                    detected_smu = self.hw_controller.auto_detect_smu()
                    if detected_smu:
                        # Close old connection if exists
                        if self.hw_controller.smu:
                            try:
                                self.hw_controller.smu.close()
                            except:
                                pass
                        self.hw_controller.smu = detected_smu
                        # Re-check status after reconnection
                        smu_info = self.hw_controller.get_smu_info()
                        print("[REFRESH] SMU reconnection successful")
                    else:
                        print("[REFRESH] SMU reconnection failed - device not found")
            else:
                smu_info = {"connected": False, "info": "SMU not available"}
            
            # 3. Schedule UI update back on Main Thread
            self.after(0, lambda: self._update_keithley_ui(smu_info))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._update_keithley_error(error_msg))
    
    def _update_keithley_ui(self, smu_info):
        """Update Keithley UI with results (called on main thread)"""
        try:
            if smu_info.get('connected', False):
                self.keithley_status_label.configure(text='✓ Connected', text_color='green')
            else:
                self.keithley_status_label.configure(text='✗ Not Connected', text_color='red')
        except Exception as e:
            print(f"Error updating Keithley UI: {e}")
            self.keithley_status_label.configure(text='Error', text_color='red')
    
    def _update_keithley_error(self, error_msg):
        """Update Keithley UI with error (called on main thread)"""
        print(f"Error refreshing Keithley status: {error_msg}")
        self.keithley_status_label.configure(text='Error', text_color='red')
    
    def on_keithley_mode_change(self):
        """Handle Keithley measurement mode change"""
        mode = self.keithley_mode_var.get()
        self.keithley_mode = mode
        
        if mode == "voltage":
            self.keithley_bias_label.configure(text='Bias Voltage (V):')
            self.keithley_current_limit_entry.pack(side='left', padx=5)
            self.keithley_voltage_limit_entry.pack_forget()
        else:  # current mode
            self.keithley_bias_label.configure(text='Bias Current (A):')
            self.keithley_voltage_limit_entry.pack(side='left', padx=5)
            self.keithley_current_limit_entry.pack_forget()
    
    def on_keithley_output_toggle(self):
        """Handle Keithley output enable/disable toggle"""
        enabled = self.keithley_output_var.get()
        self.keithley_output_enabled = enabled
        
        if not enabled:
            # Turn off SMU output
            try:
                if self.hw_controller.smu is not None and hasattr(self.hw_controller, 'smu'):
                    self.hw_controller.stop_smu()
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_STATUS', 'SMU output turned OFF'))
            except Exception as e:
                print(f"Error turning off SMU: {e}")
        else:
            # Setup and enable SMU output based on mode
            try:
                if self.hw_controller.smu is not None and hasattr(self.hw_controller, 'smu'):
                    mode = self.keithley_mode_var.get()
                    bias_value = float(self.keithley_bias_entry.get())
                    
                    if mode == "voltage":
                        current_limit = float(self.keithley_current_limit_entry.get())
                        self.hw_controller.setup_smu_for_iv_measurement(current_limit)
                        self.hw_controller.set_smu_voltage(bias_value, current_limit)
                    else:  # current mode
                        voltage_limit = float(self.keithley_voltage_limit_entry.get())
                        # Setup for current source mode
                        self.hw_controller.setup_smu_for_current_source(voltage_limit)
                        self.hw_controller.set_smu_current(bias_value)
                    
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_STATUS', f'SMU output enabled: {bias_value} {"V" if mode == "voltage" else "A"}'))
            except (ValueError, Exception) as e:
                print(f"Error enabling SMU: {e}")
                self.keithley_output_var.set(False)
                self.keithley_output_enabled = False
                if self.update_queue:
                    self.update_queue.put(('UPDATE_STATUS', f'Error enabling SMU: {e}'))
    
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
        print(f"[EXPERIMENT_THREAD] Starting experiment thread")
        print(f"[EXPERIMENT_THREAD] Program: {experiment_program}")
        print(f"[EXPERIMENT_THREAD] Is new experiment: {is_new_experiment}")
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
                    # BUG FIX #1: Thread-safe access
                    with self.data_lock:
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
            
            # Set pump flow rate and start the pump (with timeout handling)
            print(f"[EXPERIMENT_THREAD] Setting pump flow rate to {flow_rate} ml/min")
            try:
                self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
                time.sleep(0.3)  # Wait for pump to process flow rate setting
                print(f"[EXPERIMENT_THREAD] Starting pump...")
                pump_started = self.exp_manager.hw_controller.start_pump()  # Start the pump
                print(f"[EXPERIMENT_THREAD] Pump start result: {pump_started}")
                time.sleep(0.5)  # Wait for pump to actually start running
                print(f"[EXPERIMENT_THREAD] Setting valves...")
                self.exp_manager.hw_controller.set_valves(valve_setting['valve1'], valve_setting['valve2'])
            except Exception as e:
                # Catch SerialReadTimeoutException or any other timeout/communication error
                error_msg = str(e)
                error_type = type(e).__name__
                print(f"[EXPERIMENT_THREAD] Pump timeout/error: {error_type}: {error_msg}")
                
                # Mark pump as disconnected
                if hasattr(self.exp_manager.hw_controller.pump, 'connected'):
                    self.exp_manager.hw_controller.pump.connected = False
                
                # Stop the experiment safely
                if self.update_queue:
                    self.update_queue.put(('UPDATE_STATUS', 'Experiment stopped: Pump unresponsive'))
                    self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Stopped: Pump Timeout', 'red')))
                
                # Stop experiment manager
                self.exp_manager.stop_experiment()
                
                # Update UI to show pump disconnected
                self.after(0, lambda: self.pump_status_label.configure(text='✗ Disconnected (Timeout)', text_color='red'))
                
                print("[EXPERIMENT_THREAD] Experiment stopped due to pump timeout")
                return  # Exit the experiment thread
            
            # Setup Keithley 2450 if enabled
            if self.keithley_output_enabled and self.hw_controller.smu is not None:
                try:
                    mode = self.keithley_mode_var.get()
                    bias_value = float(self.keithley_bias_entry.get())
                    
                    if mode == "voltage":
                        current_limit = float(self.keithley_current_limit_entry.get())
                        print(f"[EXPERIMENT_THREAD] Setting up Keithley: Voltage mode, Bias={bias_value}V, Limit={current_limit}A")
                        self.hw_controller.setup_smu_for_iv_measurement(current_limit)
                        self.hw_controller.set_smu_voltage(bias_value, current_limit)
                    else:  # current mode
                        voltage_limit = float(self.keithley_voltage_limit_entry.get())
                        print(f"[EXPERIMENT_THREAD] Setting up Keithley: Current mode, Bias={bias_value}A, Limit={voltage_limit}V")
                        self.hw_controller.setup_smu_for_current_source(voltage_limit)
                        self.hw_controller.set_smu_current(bias_value)
                    
                    print(f"[EXPERIMENT_THREAD] Keithley 2450 configured and enabled")
                except (ValueError, Exception) as e:
                    print(f"[EXPERIMENT_THREAD] Error setting up Keithley: {e}")
                    self.keithley_output_enabled = False
            
            start_time = time.time()
            print(f"[EXPERIMENT_THREAD] Starting data collection loop...")
            loop_count = 0
            
            while time.time() - start_time < duration and self.exp_manager.is_running:
                loop_count += 1
                if loop_count % 10 == 0:  # Print every 10 iterations
                    print(f"[EXPERIMENT_THREAD] Loop iteration {loop_count}")
                if not self.exp_manager.perform_safety_checks():
                    break
                
                # Check for flow rate updates (with timeout handling)
                if self.current_flow_rate != flow_rate:
                    old_flow_rate = flow_rate
                    flow_rate = self.current_flow_rate
                    try:
                        self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
                        if self.update_queue:
                            self.update_queue.put(('UPDATE_STATUS', f'Flow changed during experiment: {old_flow_rate:.2f} → {flow_rate:.2f} ml/min'))
                    except Exception as e:
                        # Catch timeout during flow rate update
                        error_msg = str(e)
                        error_type = type(e).__name__
                        print(f"[EXPERIMENT_THREAD] Pump timeout during flow update: {error_type}: {error_msg}")
                        
                        # Mark pump as disconnected
                        if hasattr(self.exp_manager.hw_controller.pump, 'connected'):
                            self.exp_manager.hw_controller.pump.connected = False
                        
                        # Stop the experiment safely
                        if self.update_queue:
                            self.update_queue.put(('UPDATE_STATUS', 'Experiment stopped: Pump unresponsive'))
                            self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Stopped: Pump Timeout', 'red')))
                        
                        # Stop experiment manager
                        self.exp_manager.stop_experiment()
                        
                        # Update UI to show pump disconnected
                        self.after(0, lambda: self.pump_status_label.configure(text='✗ Disconnected (Timeout)', text_color='red'))
                        
                        print("[EXPERIMENT_THREAD] Experiment stopped due to pump timeout")
                        break  # Exit the loop
                
                current_time = time.time()
                remaining_time = duration - (current_time - start_time)
                elapsed_time_from_start = current_time - experiment_start_time
                
                # Read sensor data (with timeout handling for pump)
                try:
                    pump_data = self.exp_manager.hw_controller.read_pump_data()
                except Exception as e:
                    # Catch timeout when reading pump data
                    error_msg = str(e)
                    error_type = type(e).__name__
                    print(f"[EXPERIMENT_THREAD] Pump timeout during data read: {error_type}: {error_msg}")
                    
                    # Mark pump as disconnected
                    if hasattr(self.exp_manager.hw_controller.pump, 'connected'):
                        self.exp_manager.hw_controller.pump.connected = False
                    
                    # Stop the experiment safely
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_STATUS', 'Experiment stopped: Pump unresponsive'))
                        self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Stopped: Pump Timeout', 'red')))
                    
                    # Stop experiment manager
                    self.exp_manager.stop_experiment()
                    
                    # Update UI to show pump disconnected
                    self.after(0, lambda: self.pump_status_label.configure(text='✗ Disconnected (Timeout)', text_color='red'))
                    
                    print("[EXPERIMENT_THREAD] Experiment stopped due to pump timeout")
                    break  # Exit the loop
                
                pressure = self.exp_manager.hw_controller.read_pressure_sensor()
                temperature = self.exp_manager.hw_controller.read_temperature_sensor()
                level = self.exp_manager.hw_controller.read_level_sensor()
                
                # Read Keithley measurements if enabled
                keithley_voltage = None
                keithley_current = None
                if self.keithley_output_enabled and self.hw_controller.smu is not None:
                    try:
                        smu_measurement = self.hw_controller.measure_smu()
                        if smu_measurement:
                            keithley_voltage = smu_measurement.get('voltage', None)
                            keithley_current = smu_measurement.get('current', None)
                            
                            # Update display
                            if keithley_voltage is not None:
                                self.keithley_voltage_label.configure(text=f'{keithley_voltage:.4f} V')
                            if keithley_current is not None:
                                self.keithley_current_label.configure(text=f'{keithley_current:.6f} A')
                    except Exception as e:
                        print(f"[EXPERIMENT_THREAD] Error reading Keithley: {e}")
                
                if self.update_queue:
                    status_msg = f"Running: {remaining_time:.0f}s remaining, Flow={flow_rate}ml/min"
                    if keithley_voltage is not None:
                        status_msg += f", V={keithley_voltage:.3f}V, I={keithley_current:.6f}A"
                    self.update_queue.put(('UPDATE_STATUS', status_msg))
                
                # Update data arrays (thread-safe with lock - BUG FIX #1)
                with self.data_lock:
                    self.flow_x_data.append(elapsed_time_from_start)
                    self.flow_y_data.append(pump_data['flow'])
                    self.pressure_x_data.append(elapsed_time_from_start)
                    self.pressure_y_data.append(pressure)
                    self.temp_x_data.append(elapsed_time_from_start)
                    # Append temperature (or NaN if sensor disconnected)
                    if temperature is not None:
                        self.temp_y_data.append(temperature)
                    else:
                        # Use NaN to show gaps in graph when sensor is disconnected
                        self.temp_y_data.append(float('nan'))
                    self.level_x_data.append(elapsed_time_from_start)
                    self.level_y_data.append(level * 100)
                    
                    # Store Keithley data for graphing (synchronized with time)
                    self.keithley_time_data.append(elapsed_time_from_start)
                    if keithley_voltage is not None:
                        self.keithley_voltage_data.append(keithley_voltage)
                    else:
                        self.keithley_voltage_data.append(0.0)
                    if keithley_current is not None:
                        self.keithley_current_data.append(keithley_current)
                    else:
                        self.keithley_current_data.append(0.0)
                
                data_point = {
                    "time": elapsed_time_from_start,
                    "flow_setpoint": self.current_flow_rate,
                    "pump_flow_read": pump_data['flow'],
                    "pressure_read": pressure,
                    "temp_read": temperature if temperature is not None else "",
                    "level_read": level,
                    "voltage": keithley_voltage if keithley_voltage is not None else "",
                    "current": keithley_current if keithley_current is not None else "",
                    "target_voltage": float(self.keithley_bias_entry.get()) if self.keithley_output_enabled else ""
                }
                
                self.data_handler.append_data(data_point)
                
                # Update graphs via queue (thread-safe - BUG FIX #1)
                if self.update_queue:
                    try:
                        # Make copies while holding lock
                        with self.data_lock:
                            flow_x_copy = list(self.flow_x_data)
                            flow_y_copy = list(self.flow_y_data)
                            pressure_x_copy = list(self.pressure_x_data)
                            pressure_y_copy = list(self.pressure_y_data)
                            temp_x_copy = list(self.temp_x_data)
                            temp_y_copy = list(self.temp_y_data)
                            level_x_copy = list(self.level_x_data)
                            level_y_copy = list(self.level_y_data)
                        
                        self.update_queue.put(('UPDATE_GRAPH1', (flow_x_copy, flow_y_copy)))
                        self.update_queue.put(('UPDATE_GRAPH2', (pressure_x_copy, pressure_y_copy)))
                        self.update_queue.put(('UPDATE_GRAPH3', (temp_x_copy, temp_y_copy)))
                        self.update_queue.put(('UPDATE_GRAPH4', (level_x_copy, level_y_copy)))
                        if loop_count == 1:  # Print on first iteration
                            print(f"[EXPERIMENT_THREAD] Sent graph updates to queue")
                            print(f"[EXPERIMENT_THREAD] Flow data: {len(flow_x_copy)} points")
                            print(f"[EXPERIMENT_THREAD] Pressure data: {len(pressure_x_copy)} points")
                    except Exception as e:
                        print(f"[EXPERIMENT_THREAD ERROR] Error updating graphs: {e}")
                time.sleep(1)
        
        # Stop the pump when experiment ends
        self.exp_manager.hw_controller.stop_pump()
        
        # Stop Keithley if enabled
        if self.keithley_output_enabled and self.hw_controller.smu is not None:
            try:
                self.hw_controller.stop_smu()
                print(f"[EXPERIMENT_THREAD] Keithley stopped")
            except Exception as e:
                print(f"[EXPERIMENT_THREAD] Error stopping Keithley: {e}")
        
        self.exp_manager.stop_experiment()
        
        # Update last total time (thread-safe - BUG FIX #1)
        with self.data_lock:
            if len(self.flow_x_data) > 0:
                self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
        
        if self.update_queue:
            self.update_queue.put(('UPDATE_STATUS', f'Experiment paused. Total time: {self.last_total_time:.1f}s. Click Start to continue.'))
            self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Paused', 'orange')))

