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
from utils.logger_config import get_logger

logger = get_logger(__name__)


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
        
        # Track measurement number for multiple measurements in same file
        self.measurement_counter = 0
        
        # Keithley 2450 control variables
        self.keithley_mode = "voltage"  # "voltage" or "current"
        self.keithley_bias_value = 0.0
        self.keithley_output_enabled = False
        self.keithley_current_limit = 0.1
        self.keithley_voltage_data = []
        self.keithley_current_data = []
        self.keithley_time_data = []
        
        # Graph auto-scale control
        self.auto_scale_enabled = True  # Default: auto-scale ON
        
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
        
        # ========== 1. CONTROL BUTTONS (TOP) ==========
        control_frame = ctk.CTkFrame(left_frame)
        control_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(control_frame, text="Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        # Row 1: Start | Stop | Finish (horizontal)
        row1_frame = ctk.CTkFrame(control_frame)
        row1_frame.pack(pady=2)
        self.start_btn = self.create_blue_button(row1_frame, text='Start Recording',
                                                 command=self.start_recording, width=120, height=40)
        self.start_btn.pack(side='left', padx=2)
        
        self.stop_btn = self.create_blue_button(row1_frame, text='Stop Recording',
                                                command=self.stop_recording, width=120, height=40,
                                                fg_color='#0D47A1', hover_color='#0C3A7A')
        self.stop_btn.pack(side='left', padx=2)
        
        self.finish_btn = self.create_blue_button(row1_frame, text='Finish Recording',
                                                  command=self.finish_recording, width=120, height=40,
                                                  fg_color='#0C6CC0', hover_color='#0A518A')
        self.finish_btn.pack(side='left', padx=2)
        
        # Row 2: Clear Graph (Update Flow moved to flow rate entry row)
        row2_frame = ctk.CTkFrame(control_frame)
        row2_frame.pack(pady=2)
        
        self.clear_graph_btn = self.create_blue_button(row2_frame, text='Clear Graph',
                                                       command=self.clear_graph, width=120)
        self.clear_graph_btn.pack(side='left', padx=2)
        
        # Row 3: Export (Excel, PNG, PDF) (horizontal)
        export_menu_frame = ctk.CTkFrame(control_frame)
        export_menu_frame.pack(pady=2)
        ctk.CTkLabel(export_menu_frame, text='Export:', width=80).pack(side='left', padx=5)
        self.export_btn = self.create_blue_button(export_menu_frame, text='Excel',
                                                 command=self.export_excel, width=100)
        self.export_btn.pack(side='left', padx=2)
        
        self.create_blue_button(export_menu_frame, text='PNG', 
                               command=self.export_graph_png, width=100).pack(side='left', padx=2)
        
        self.create_blue_button(export_menu_frame, text='PDF', 
                               command=self.export_graph_pdf, width=100).pack(side='left', padx=2)
        
        # Row 4: Segment Label (for marking phases in experiment)
        segment_frame = ctk.CTkFrame(control_frame)
        segment_frame.pack(fill='x', pady=2)
        ctk.CTkLabel(segment_frame, text='Segment Label:', width=100).pack(side='left', padx=5)
        self.segment_entry = ctk.CTkEntry(segment_frame, width=150, placeholder_text='e.g., "Heating Phase"')
        self.segment_entry.pack(side='left', padx=5)
        self.add_segment_btn = self.create_blue_button(segment_frame, text='Add Segment',
                                                       command=self.add_segment_label, width=100)
        self.add_segment_btn.pack(side='left', padx=2)
        
        # ========== 2. VAPOURTEC SF-10 PUMP STATUS & CONTROL ==========
        pump_status_frame = ctk.CTkFrame(left_frame)
        pump_status_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(pump_status_frame, text="Vapourtec SF-10 Pump Status", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        pump_info_frame = ctk.CTkFrame(pump_status_frame)
        pump_info_frame.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(pump_info_frame, text='Status:', width=100).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.pump_status_label = ctk.CTkLabel(pump_info_frame, text='Checking...', width=250, anchor='w')
        self.pump_status_label.grid(row=0, column=1, padx=5, pady=2, sticky='w')
        
        # Port - commented out (not displayed)
        # ctk.CTkLabel(pump_info_frame, text='Port:', width=100).grid(row=1, column=0, padx=5, pady=2, sticky='w')
        # self.pump_port_label = ctk.CTkLabel(pump_info_frame, text='N/A', width=250, anchor='w')
        # self.pump_port_label.grid(row=1, column=1, padx=5, pady=2, sticky='w')
        
        # Flow Rate - commented out (not displayed)
        # ctk.CTkLabel(pump_info_frame, text='Flow Rate:', width=100).grid(row=2, column=0, padx=5, pady=2, sticky='w')
        # self.pump_flow_label = ctk.CTkLabel(pump_info_frame, text='N/A', width=250, anchor='w')
        # self.pump_flow_label.grid(row=2, column=1, padx=5, pady=2, sticky='w')
        
        # Quick Flow Rate Setting (compact)
        flow_quick_frame = ctk.CTkFrame(pump_status_frame)
        flow_quick_frame.pack(fill='x', padx=5, pady=5)
        ctk.CTkLabel(flow_quick_frame, text='Quick Flow Rate (ml/min):', width=150).pack(side='left', padx=5)
        self.flow_rate_entry = ctk.CTkEntry(flow_quick_frame, width=100)
        self.flow_rate_entry.insert(0, '1.5')
        self.flow_rate_entry.pack(side='left', padx=5)
        self.update_flow_btn = self.create_blue_button(flow_quick_frame, text='Update Flow',
                                                      command=self.update_flow, width=100)
        self.update_flow_btn.pack(side='left', padx=2)
        
        # Control buttons
        pump_btn_frame = ctk.CTkFrame(pump_status_frame)
        pump_btn_frame.pack(pady=5)
        self.create_blue_button(pump_btn_frame, text='🔄 Refresh Status', command=self.refresh_pump_status, width=120, height=30).pack(side='left', padx=2)
        
        # ========== 3. KEITHLEY 2450 SMU CONTROL ==========
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
        ctk.CTkRadioButton(mode_radio_frame, text="Source Current / Measure Voltage", 
                          variable=self.keithley_mode_var, value="voltage",
                          command=self.on_keithley_mode_change).pack(side='left', padx=5)
        ctk.CTkRadioButton(mode_radio_frame, text="Source Voltage / Measure Current", 
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
        
        # ========== 4. CURRENT READINGS (LIVE) ==========
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
        
        # Experiment Parameters (kept for functionality)
        exp_frame = ctk.CTkFrame(left_frame)
        exp_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(exp_frame, text="Experiment Parameters", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        duration_frame = ctk.CTkFrame(exp_frame)
        duration_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(duration_frame, text='Duration (sec):', width=150).pack(side='left', padx=5)
        self.duration_entry = ctk.CTkEntry(duration_frame, width=100)
        self.duration_entry.insert(0, '6000')
        self.duration_entry.pack(side='left', padx=5)
        
        valve_frame = ctk.CTkFrame(exp_frame)
        valve_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(valve_frame, text='Valve Settings:', width=150).pack(side='left', padx=5)
        self.valve_var = ctk.StringVar(value="main")
        ctk.CTkRadioButton(valve_frame, text="Main", variable=self.valve_var, value="main").pack(side='left', padx=5)
        ctk.CTkRadioButton(valve_frame, text="Rinsing", variable=self.valve_var, value="rinsing").pack(side='left', padx=5)
        
        # Step Progress Frame
        step_progress_frame = ctk.CTkFrame(left_frame)
        step_progress_frame.pack(fill='x', padx=10, pady=5)
        
        ctk.CTkLabel(step_progress_frame, text="Program Progress", 
                     font=('Helvetica', 12, 'bold')).pack(pady=5)
        
        self.step_info_label = ctk.CTkLabel(step_progress_frame, text="Step: - / -", 
                                           font=('Helvetica', 11))
        self.step_info_label.pack(pady=2)
        
        self.step_time_label = ctk.CTkLabel(step_progress_frame, text="Time remaining: -", 
                                           font=('Helvetica', 10))
        self.step_time_label.pack(pady=2)
        
        self.step_progress_bar = ctk.CTkProgressBar(step_progress_frame, width=400)
        self.step_progress_bar.pack(pady=5)
        self.step_progress_bar.set(0)
        
        # Experiment Metadata (kept for functionality)
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
        ctk.CTkRadioButton(mode_frame, text="Multi-Panel (3 graphs)", variable=self.graph_mode_var, value="multi", command=self.on_graph_mode_change).pack(side='left', padx=5)
        ctk.CTkRadioButton(mode_frame, text="Single Graph (X-Y)", variable=self.graph_mode_var, value="single", command=self.on_graph_mode_change).pack(side='left', padx=5)
        
        # Auto-scale toggle button
        auto_scale_frame = ctk.CTkFrame(graph_control_frame)
        auto_scale_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(auto_scale_frame, text='Zoom Control:', width=80).pack(side='left', padx=5)
        self.auto_scale_btn = self.create_blue_button(
            auto_scale_frame, 
            text='🔓 Auto-Scale ON', 
            command=self.toggle_auto_scale, 
            width=150,
            height=30
        )
        self.auto_scale_btn.pack(side='left', padx=2)
        
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
        self.y_axis_combo.set('Current')
        self.y_axis_combo.pack(side='left', padx=5)
        
        # Multi-panel graph frames container
        self.multi_graph_frame = ctk.CTkFrame(right_frame)
        self.multi_graph_frame.pack_forget()  # Hidden by default
        
        # Single graph frame (shown initially)
        self.main_graph_frame = ctk.CTkFrame(right_frame)
        self.main_graph_frame.pack(fill='both', expand=True, pady=5)
    
    def setup_graphs(self):
        """Initialize matplotlib graphs"""
        # Multi-panel graphs (1x3 grid: Voltage, Current, Flow)
        self.multi_fig, (self.voltage_ax, self.current_ax, self.flow_ax) = plt.subplots(1, 3, figsize=(15, 5))
        
        # Configure each subplot
        graphs_config = [
            (self.voltage_ax, 'Voltage', 'Voltage (V)', '#2E86AB'),
            (self.current_ax, 'Current', 'Current (A)', '#A23B72'),
            (self.flow_ax, 'Flow Rate', 'Flow Rate (ml/min)', '#F18F01')
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
        self.plot_xy_graph('Time', 'Current', [], [])
    
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
        """Update all 3 graphs in multi-panel view: Voltage, Current, Flow"""
        # BUG FIX #1 & #4: Thread-safe access with lock and make copies
        with self.data_lock:
            flow_x_copy = list(self.flow_x_data) if self.flow_x_data else []
            flow_y_copy = list(self.flow_y_data) if self.flow_y_data else []
            keithley_time_copy = list(self.keithley_time_data) if self.keithley_time_data else []
            keithley_voltage_copy = list(self.keithley_voltage_data) if self.keithley_voltage_data else []
            keithley_current_copy = list(self.keithley_current_data) if self.keithley_current_data else []
        
        # Voltage graph
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
        
        # Current graph
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
        
        # Flow graph
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
        
        # Apply styling to all axes
        for ax in [self.voltage_ax, self.current_ax, self.flow_ax]:
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
        # Save current limits if auto-scale is disabled
        saved_xlim = None
        saved_ylim = None
        if not self.auto_scale_enabled:
            saved_xlim = self.main_ax.get_xlim()
            saved_ylim = self.main_ax.get_ylim()
        
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
            'Pressure': {'ylabel': 'Pressure (bar)', 'unit': 'bar'},
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
        
        # Set axis limits (only if auto-scale is enabled)
        if len(x_plot) > 0 and len(y_plot) > 0:
            if self.auto_scale_enabled:
                x_margin = (max(x_plot) - min(x_plot)) * 0.05 if max(x_plot) > min(x_plot) else 1
                y_margin = (max(y_plot) - min(y_plot)) * 0.1 if max(y_plot) > min(y_plot) else 1
                self.main_ax.set_xlim(min(x_plot) - x_margin, max(x_plot) + x_margin)
                self.main_ax.set_ylim(min(y_plot) - y_margin, max(y_plot) + y_margin)
            else:
                # Restore previous limits to preserve zoom (if they were saved)
                if saved_xlim is not None and saved_ylim is not None:
                    self.main_ax.set_xlim(saved_xlim)
                    self.main_ax.set_ylim(saved_ylim)
        
        self.main_fig.tight_layout(pad=2.0)
        self.main_canvas.draw()
    
    def toggle_auto_scale(self):
        """Toggle auto-scale on/off for graphs"""
        self.auto_scale_enabled = not self.auto_scale_enabled
        
        if self.auto_scale_enabled:
            # Auto-scale is ON
            self.auto_scale_btn.configure(
                text='🔓 Auto-Scale ON', 
                fg_color='#1E88E5',
                hover_color='#1565C0'
            )
            # Re-apply auto-scale to current view
            if self.graph_mode_var.get() == "multi":
                self.update_multi_panel_graphs()
            else:
                self.on_axis_change()
        else:
            # Auto-scale is OFF (zoom locked)
            self.auto_scale_btn.configure(
                text='🔒 Zoom Locked', 
                fg_color='#FF9800',
                hover_color='#F57C00'
            )
            # Don't change limits - preserve current zoom
    
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
            logger.debug(f"Error updating statistics: {e}")
    
    # --- Event Handlers ---
    def start_recording(self):
        """Start recording experiment - continues from last point if data exists"""
        logger.debug("start_recording() called")
        try:
            file_name = self.exp_name_entry.get().strip()
            logger.debug(f"Experiment name: {file_name}")
            if not file_name:
                messagebox.showerror('Error', 'Please enter an experiment name before starting recording.')
                return
            
            if not re.match(r'^[a-zA-Z0-9_-]+$', file_name):
                messagebox.showerror('Error', 'Experiment name can only contain letters, numbers, underscores, and hyphens.')
                return
            
            flow_rate = float(self.flow_rate_entry.get())
            logger.debug(f"Flow rate: {flow_rate} ml/min")
            
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
            
            # Check if we should create new file or resume existing
            file_is_closed = (
                not self.data_handler.file_path or  # No file path
                not os.path.exists(self.data_handler.file_path) or  # File doesn't exist
                self.data_handler.file is None or  # File handle is None
                getattr(self.data_handler, 'file_closed', False)  # File was explicitly closed by Finish
            )
            
            # Determine if this is a new experiment or resume
            is_new_experiment = (
                self.experiment_base_time is None or  # No active experiment timing
                file_is_closed  # File was closed (by Finish)
            )
            
            if is_new_experiment:
                # NEW EXPERIMENT - always create new file
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
                    
                    # Reset experiment timing
                    self.last_total_time = 0.0
                    self.experiment_base_time = time.time()
            else:
                # RESUME EXISTING EXPERIMENT (after Stop/Pause)
                # File is still open, continue writing to it
                if self.experiment_base_time is None:
                    # Calculate base time from existing data
                    with self.data_lock:
                        if len(self.flow_x_data) > 0:
                            self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
                            self.experiment_base_time = time.time() - self.last_total_time
                        else:
                            self.experiment_base_time = time.time()
                            self.last_total_time = 0.0
            
            if self.update_queue:
                self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Recording...', 'red')))
                if is_new_experiment:
                    self.update_queue.put(('UPDATE_FILE', f"{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"))
                self.update_queue.put(('UPDATE_READINGS', (0, 0, flow_rate, 0)))
            
            logger.debug(f"Starting experiment thread with program: {experiment_program}")
            logger.debug(f"Is new experiment: {is_new_experiment}")
            thread = threading.Thread(target=self.experiment_thread,
                             args=(experiment_program, is_new_experiment),
                             daemon=True)
            thread.start()
            logger.debug(f"Thread started: {thread.is_alive()}")
        except ValueError as e:
            logger.warning(f"ValueError in start_recording: {e}")
            messagebox.showerror('Error', 'Invalid input for Flow Rate or Duration. Please enter numbers.')
        except Exception as e:
            logger.error(f"Unexpected error in start_recording: {e}", exc_info=True)
            messagebox.showerror('Error', f'Unexpected error: {e}')
    
    def stop_recording(self):
        """Stop recording - PAUSE mode (file remains open for resume)"""
        self.exp_manager.stop_experiment()
        
        # Update last total time based on current data (thread-safe - BUG FIX #1)
        with self.data_lock:
            if len(self.flow_x_data) > 0:
                self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
        
        # IMPORTANT: File remains open - this is a PAUSE, not a finish
        # User can click Start again to resume in the same file
        
        if self.update_queue:
            self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Paused', 'orange')))
            self.update_queue.put(('UPDATE_STATUS', 
                f'Recording paused. Total time: {self.last_total_time:.1f}s. '
                f'File remains open. Click Start to resume, or Finish to close file.'))
    
    def start_recording_from_program_tab(self, experiment_program):
        """
        Wrapper method to start recording from ProgramTab.
        This method does NOT change the existing start_recording() behavior.
        
        Args:
            experiment_program: List of experiment steps from ProgramTab
            
        Returns:
            True if started successfully, False otherwise
        """
        logger.debug("start_recording_from_program_tab() called")
        
        # Validate experiment name (same as start_recording)
        file_name = self.exp_name_entry.get().strip()
        if not file_name:
            return False  # ProgramTab will show error message
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', file_name):
            return False  # ProgramTab will show error message
        
        # Validate program steps
        for i, step in enumerate(experiment_program):
            flow_rate = step.get('flow_rate', 0)
            if flow_rate < 0:
                return False
            
            MAX_FLOW_RATE = 5.0
            if flow_rate > MAX_FLOW_RATE:
                step['flow_rate'] = MAX_FLOW_RATE  # Auto-correct
        
        # Set current_flow_rate from first step (for backward compatibility)
        if experiment_program and 'flow_rate' in experiment_program[0]:
            self.current_flow_rate = experiment_program[0]['flow_rate']
        
        # Check if we should create new file or resume existing (same logic as start_recording)
        file_is_closed = (
            not self.data_handler.file_path or  # No file path
            not os.path.exists(self.data_handler.file_path) or  # File doesn't exist
            self.data_handler.file is None or  # File handle is None
            getattr(self.data_handler, 'file_closed', False)  # File was explicitly closed by Finish
        )
        
        # Determine if this is a new experiment or resume
        is_new_experiment = (
            self.experiment_base_time is None or  # No active experiment timing
            file_is_closed  # File was closed (by Finish)
        )
        
        if is_new_experiment:
            # NEW EXPERIMENT - always create new file
            if file_is_closed:
                # Reset measurement counter for new experiment
                self.measurement_counter = 0
                
                # Create new file with metadata
                metadata = {
                    'name': file_name,
                    'description': self.exp_desc_entry.get().strip(),
                    'tags': [tag.strip() for tag in self.exp_tags_entry.get().split(',') if tag.strip()],
                    'operator': self.exp_operator_entry.get().strip(),
                    'start_time': datetime.now().isoformat(),
                    'program_source': 'ProgramTab'  # Mark source
                }
                self.data_handler.set_custom_filename(file_name)
                self.data_handler.set_metadata(metadata)
                self.data_handler.create_new_file()
                
                # Reset experiment timing
                self.last_total_time = 0.0
                self.experiment_base_time = time.time()
        else:
            # RESUME EXISTING EXPERIMENT (after Stop/Pause)
            # File is still open, continue writing to it
            if self.experiment_base_time is None:
                # Calculate base time from existing data
                with self.data_lock:
                    if len(self.flow_x_data) > 0:
                        self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
                        self.experiment_base_time = time.time() - self.last_total_time
                    else:
                        self.experiment_base_time = time.time()
                        self.last_total_time = 0.0
        
        # Same UI updates as start_recording()
        if self.update_queue:
            self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Recording...', 'red')))
            if is_new_experiment:
                self.update_queue.put(('UPDATE_FILE', f"{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"))
        
        # Use existing experiment_thread() - no changes needed!
        logger.debug(f"Starting experiment thread with program: {experiment_program}")
        thread = threading.Thread(target=self.experiment_thread,
                         args=(experiment_program, is_new_experiment),
                         daemon=True)
        thread.start()
        logger.debug(f"Thread started: {thread.is_alive()}")
        
        return True
    
    def finish_recording(self):
        """Finish recording - CLOSE file permanently and convert to Excel"""
        self.exp_manager.finish_experiment()
        
        # Close the file permanently
        if self.data_handler.file_path and self.data_handler.file:
            # Ensure all data is flushed
            self.data_handler.file.flush()
            
            # Close CSV file
            self.data_handler.close_file()
            
            # Automatically convert to Excel
            csv_path = self.data_handler.file_path
            excel_path = csv_path.replace('.csv', '.xlsx')
            
            try:
                success = self.data_handler.export_to_excel(excel_path)
                if success:
                    print(f"Automatically converted to Excel: {excel_path}")
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_STATUS', 
                            f'Experiment finished. File closed and converted to Excel: {excel_path}'))
                else:
                    print("Warning: CSV file closed but Excel conversion failed")
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_STATUS', 
                            'Experiment finished. CSV file closed. Excel conversion failed - check console.'))
            except Exception as e:
                logger.warning(f"Error during automatic Excel conversion: {e}")
                if self.update_queue:
                    self.update_queue.put(('UPDATE_STATUS', 
                        f'Experiment finished. CSV file closed. Excel conversion error: {e}'))
        
        # Reset all experiment state for new experiment
        self.last_total_time = 0.0
        self.experiment_base_time = None
        self.measurement_counter = 0
        
        if self.update_queue:
            self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Completed', 'green')))
            self.update_queue.put(('UPDATE_FILE', 'No file - will create new file on next Start'))
    
    def update_step_progress(self, step_index, total_steps, step_remaining, step_progress):
        """Update step progress widgets"""
        if hasattr(self, 'step_info_label'):
            self.step_info_label.configure(text=f"Step: {step_index} / {total_steps}")
        
        if hasattr(self, 'step_time_label'):
            if step_remaining > 60:
                mins = int(step_remaining // 60)
                secs = int(step_remaining % 60)
                self.step_time_label.configure(text=f"Time remaining: {mins}m {secs}s")
            else:
                self.step_time_label.configure(text=f"Time remaining: {int(step_remaining)}s")
        
        if hasattr(self, 'step_progress_bar'):
            self.step_progress_bar.set(step_progress)
    
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
        
        # Reset clock/timer for next experiment
        self.experiment_base_time = None
        self.last_total_time = 0.0
        
        x_axis_type = self.x_axis_combo.get()
        y_axis_type = self.y_axis_combo.get()
        self.plot_xy_graph(x_axis_type, y_axis_type, [], [])
        
        if self.update_queue:
            self.update_queue.put(('UPDATE_STATUS', 'Graph cleared. Clock reset.'))
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
        logger.debug("Refresh pump button clicked")
        
        # 1. Update UI immediately (Main Thread)
        self.pump_status_label.configure(text="Scanning...", text_color='orange')
        
        # 2. Run logic in background thread
        threading.Thread(target=self._run_refresh_pump_logic, daemon=True).start()
    
    def _run_refresh_pump_logic(self):
        """Background thread for pump status refresh with smart reconnection"""
        try:
            import time
            
            # Step 1: Check current status first (with health check)
            logger.debug("Checking current pump status...")
            pump_info = self.hw_controller.pump.get_info()
            
            # Step 2: If already connected and working, don't force reconnect
            if pump_info.get('connected', False) and not pump_info.get('simulation_mode', False):
                logger.debug("Pump already connected and responsive - no reconnection needed")
                # Schedule UI update
                self.after(0, lambda: self._update_pump_ui(pump_info))
                return
            
            # Step 3: If not connected or in simulation mode, attempt force reconnection
            logger.debug("Pump not connected or in simulation mode - attempting FORCE reconnection...")
            
            if hasattr(self.hw_controller.pump, 'force_reconnect'):
                reconnect_success = self.hw_controller.pump.force_reconnect()
            else:
                # Fallback to regular connect if force_reconnect doesn't exist
                reconnect_success = self.hw_controller.pump.connect()
            
            # Step 4: Handle success and failure differently
            if reconnect_success:
                logger.info("Pump force reconnection successful")
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
                logger.debug("Trusting force_reconnect result - marking as connected without health check")
            else:
                logger.warning("Pump force reconnection failed - staying in simulation mode")
                # Only call get_info() if reconnection failed to read actual error/disconnected state
                pump_info = self.hw_controller.pump.get_info()
            
            # Step 5: Schedule UI update back on Main Thread
            self.after(0, lambda: self._update_pump_ui(pump_info))
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Error during pump refresh: {error_msg}")
            self.after(0, lambda: self._update_pump_error(error_msg))
    
    def _update_pump_ui(self, pump_info):
        """Update pump UI with results (called on main thread)"""
        try:
            # Update status label with color
            status_text = pump_info.get('status', 'Unknown')
            status_color = pump_info.get('status_color', 'gray')
            self.pump_status_label.configure(text=status_text, text_color=status_color)
            
            # Update port - commented out (not displayed)
            # port_text = pump_info.get('port', 'N/A')
            # self.pump_port_label.configure(text=port_text)
            
            # Update flow rate - commented out (not displayed)
            # flow_rate = pump_info.get('current_flow_rate', 0.0)
            # self.pump_flow_label.configure(text=f'{flow_rate:.2f} ml/min')
            
            # Max flow rate is fixed at 5.0 ml/min (no need to display)
        except Exception as e:
            logger.debug(f"Error updating pump UI: {e}")
            self.pump_status_label.configure(text='Error', text_color='red')
    
    def _update_pump_error(self, error_msg):
        """Update pump UI with error (called on main thread)"""
        logger.warning(f"Error refreshing pump status: {error_msg}")
        self.pump_status_label.configure(text='Error', text_color='red')
    
    def refresh_keithley_status(self):
        """Refresh Keithley 2450 SMU connection status (with threading)"""
        logger.debug("Refresh Keithley button clicked")
        
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
                    logger.debug("SMU disconnected, attempting re-initialization...")
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
                        logger.info("SMU reconnection successful")
                    else:
                        logger.warning("SMU reconnection failed - device not found")
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
            logger.debug(f"Error updating Keithley UI: {e}")
            self.keithley_status_label.configure(text='Error', text_color='red')
    
    def _update_keithley_error(self, error_msg):
        """Update Keithley UI with error (called on main thread)"""
        logger.warning(f"Error refreshing Keithley status: {error_msg}")
        self.keithley_status_label.configure(text='Error', text_color='red')
    
    def on_keithley_mode_change(self):
        """Handle Keithley measurement mode change"""
        mode = self.keithley_mode_var.get()
        self.keithley_mode = mode
        
        # Update UI labels / visible fields
        if mode == "voltage":
            # Voltage mode = Source Current / Measure Voltage (למדוד מתח)
            self.keithley_bias_label.configure(text='Bias Current (A):')
            self.keithley_voltage_limit_entry.pack(side='left', padx=5)
            self.keithley_current_limit_entry.pack_forget()
        else:  # current mode
            # Current mode = Source Voltage / Measure Current (למדוד זרם)
            self.keithley_bias_label.configure(text='Bias Voltage (V):')
            self.keithley_current_limit_entry.pack(side='left', padx=5)
            self.keithley_voltage_limit_entry.pack_forget()

        # --- New: Safe automatic mode switch sequence ---
        try:
            # If there is no SMU, nothing to do
            if self.hw_controller.smu is None:
                return

            # Read current UI values with safe defaults
            try:
                bias_value = float(self.keithley_bias_entry.get() or 0.0)
            except ValueError:
                bias_value = 0.0

            try:
                current_limit = float(self.keithley_current_limit_entry.get() or 0.1)
            except ValueError:
                current_limit = 0.1

            try:
                voltage_limit = float(self.keithley_voltage_limit_entry.get() or 20.0)
            except ValueError:
                voltage_limit = 20.0

            # Perform safe mode reconfiguration on the hardware layer
            success = self.hw_controller.configure_smu_mode_safe(
                mode=mode,
                bias_value=bias_value,
                current_limit=current_limit,
                voltage_limit=voltage_limit,
            )

            # Update status bar for user feedback
            if self.update_queue:
                if success:
                    self.update_queue.put((
                        'UPDATE_STATUS',
                        f'SMU mode switched safely to {mode} (bias reset to 0, output state preserved)'
                    ))
                else:
                    self.update_queue.put((
                        'UPDATE_STATUS',
                        f'Error while switching SMU mode to {mode}'
                    ))
        except Exception as e:
            logger.debug(f"Error in on_keithley_mode_change safe reconfiguration: {e}")
    
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
                logger.warning(f"Error turning off SMU: {e}")
        else:
            # Setup and enable SMU output based on mode
            try:
                if self.hw_controller.smu is not None and hasattr(self.hw_controller, 'smu'):
                    mode = self.keithley_mode_var.get()
                    bias_value = float(self.keithley_bias_entry.get())
                    
                    if mode == "voltage":
                        # Voltage mode = Source Current / Measure Voltage (למדוד מתח)
                        voltage_limit = float(self.keithley_voltage_limit_entry.get())
                        self.hw_controller.setup_smu_for_current_source(voltage_limit)
                        self.hw_controller.set_smu_current(bias_value)
                    else:  # current mode
                        # Current mode = Source Voltage / Measure Current (למדוד זרם)
                        current_limit = float(self.keithley_current_limit_entry.get())
                        self.hw_controller.setup_smu_for_iv_measurement(current_limit)
                        self.hw_controller.set_smu_voltage(bias_value, current_limit)
                    
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_STATUS', f'SMU output enabled: {bias_value} {"V" if mode == "voltage" else "A"}'))
            except (ValueError, Exception) as e:
                logger.warning(f"Error enabling SMU: {e}")
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
    
    def add_segment_label(self):
        """Add a segment label marker to the data file"""
        segment_text = self.segment_entry.get().strip()
        
        if not segment_text:
            messagebox.showwarning('Warning', 'Please enter a segment label.')
            return
        
        if not self.data_handler.file_path or not self.data_handler.file:
            messagebox.showwarning('Warning', 'No active recording. Start recording first.')
            return
        
        # Create a special data point to mark segment
        current_time = 0.0
        if self.experiment_base_time:
            current_time = time.time() - self.experiment_base_time
        
        segment_data = {
            "measurement_id": "SEGMENT",
            "time": current_time,
            "flow_setpoint": "",
            "pump_flow_read": f"--- {segment_text} ---",
            "pressure_read": "",
            "temp_read": "",
            "level_read": "",
            "program_step": "SEGMENT_MARKER",
            "voltage": "",
            "current": "",
            "target_voltage": ""
        }
        
        # Write segment marker to file
        self.data_handler.append_data(segment_data)
        
        # Clear entry for next segment
        self.segment_entry.delete(0, 'end')
        
        if self.update_queue:
            self.update_queue.put(('UPDATE_STATUS', f'Segment marker added: "{segment_text}"'))
    
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
        logger.debug(f"Starting experiment thread")
        logger.debug(f"Program: {experiment_program}")
        logger.debug(f"Is new experiment: {is_new_experiment}")
        self.exp_manager.is_running = True
        
        # Note: is_new_experiment is already determined in start_recording/start_recording_from_program_tab
        # This thread just uses the value passed to it
        
        if is_new_experiment:
            if self.update_queue:
                self.update_queue.put(('UPDATE_STATUS', 'Starting new experiment...'))
            # Create file only if it doesn't exist (for multiple measurements in same file)
            # Note: measurement_counter was already incremented in start_recording/start_recording_from_program_tab
            if not self.data_handler.file_path or not os.path.exists(self.data_handler.file_path) or self.data_handler.file is None:
                self.data_handler.create_new_file()
            # Ensure base_time is set (should already be set in start_recording)
            if self.experiment_base_time is None:
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
        total_steps = len(experiment_program)
        
        for step_index, step in enumerate(experiment_program, start=1):
            if not self.exp_manager.is_running:
                break
            
            duration = step.get('duration')
            # Use flow_rate from step if available, otherwise use current_flow_rate (backward compatible)
            flow_rate = step.get('flow_rate', self.current_flow_rate)
            # Update current_flow_rate for consistency
            if 'flow_rate' in step:
                self.current_flow_rate = flow_rate
            
            # Support temperature from program steps (optional, backward compatible)
            temperature = step.get('temperature', None)
            valve_setting = step.get('valve_setting', {'valve1': True, 'valve2': False})
            
            # Send step start notification
            if self.update_queue:
                self.update_queue.put(('UPDATE_STEP_START', (step_index, total_steps, duration)))
                temp_str = f", Temp={temperature}°C" if temperature else ""
                measurement_mode_str = ""
                if step.get('measurement_mode'):
                    mode_display = "Voltage" if step.get('measurement_mode') == 'voltage' else "Current"
                    measurement_mode_str = f", Mode={mode_display}"
                self.update_queue.put(('UPDATE_STATUS', 
                    f"Executing step {step_index}/{total_steps}: Duration={duration}s, Flow Rate={flow_rate} ml/min{temp_str}{measurement_mode_str}"))
            
            # Set heating plate temperature if provided (optional, backward compatible)
            if temperature is not None:
                try:
                    self.exp_manager.hw_controller.set_heating_plate_temp(temperature)
                except Exception as e:
                    logger.warning(f"Could not set temperature: {e}")
            
            # Set pump flow rate and start the pump (with timeout handling)
            logger.debug(f"Setting pump flow rate to {flow_rate} ml/min")
            try:
                self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
                time.sleep(0.3)  # Wait for pump to process flow rate setting
                logger.debug("Starting pump...")
                pump_started = self.exp_manager.hw_controller.start_pump()  # Start the pump
                logger.debug(f"Pump start result: {pump_started}")
                time.sleep(0.5)  # Wait for pump to actually start running
                logger.debug("Setting valves...")
                self.exp_manager.hw_controller.set_valves(valve_setting['valve1'], valve_setting['valve2'])
            except Exception as e:
                # Catch SerialReadTimeoutException or any other timeout/communication error
                error_msg = str(e)
                error_type = type(e).__name__
                logger.warning(f"Pump timeout/error: {error_type}: {error_msg}")
                
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
                
                logger.warning("Experiment stopped due to pump timeout")
                return  # Exit the experiment thread
            
            # Setup Keithley 2450 if enabled
            if self.keithley_output_enabled and self.hw_controller.smu is not None:
                try:
                    # Check if this step specifies a measurement_mode (from program table)
                    measurement_mode = step.get('measurement_mode', None)
                    
                    if measurement_mode:
                        # Use measurement_mode from program step
                        mode = measurement_mode
                        # Update UI to reflect the current mode
                        self.after(0, lambda m=mode: self.keithley_mode_var.set(m))
                        # Update UI fields (show/hide appropriate limit fields)
                        self.after(0, self.on_keithley_mode_change)
                        logger.debug(f"Step specifies measurement_mode: {mode}")
                    else:
                        # Fallback to UI setting (backward compatibility)
                        mode = self.keithley_mode_var.get()
                        logger.debug(f"Using measurement_mode from UI: {mode}")
                    
                    bias_value = float(self.keithley_bias_entry.get())
                    
                    if mode == "voltage":
                        # Voltage mode = Source Current / Measure Voltage (למדוד מתח)
                        voltage_limit = float(self.keithley_voltage_limit_entry.get())
                        logger.debug(f"Setting up Keithley: Voltage mode (measure voltage), Bias={bias_value}A, Limit={voltage_limit}V")
                        self.hw_controller.setup_smu_for_current_source(voltage_limit)
                        self.hw_controller.set_smu_current(bias_value)
                    else:  # current mode
                        # Current mode = Source Voltage / Measure Current (למדוד זרם)
                        current_limit = float(self.keithley_current_limit_entry.get())
                        logger.debug(f"Setting up Keithley: Current mode (measure current), Bias={bias_value}V, Limit={current_limit}A")
                        self.hw_controller.setup_smu_for_iv_measurement(current_limit)
                        self.hw_controller.set_smu_voltage(bias_value, current_limit)
                    
                    logger.debug("Keithley 2450 configured and enabled")
                except (ValueError, Exception) as e:
                    logger.warning(f"Error setting up Keithley: {e}")
                    self.keithley_output_enabled = False
            
            start_time = time.time()
            logger.debug("Starting data collection loop...")
            loop_count = 0
            
            while time.time() - start_time < duration and self.exp_manager.is_running:
                loop_count += 1
                if loop_count % 10 == 0:  # Log every 10 iterations
                    logger.debug(f"Loop iteration {loop_count}")
                if not self.exp_manager.perform_safety_checks():
                    break
                
                # Calculate step progress and send update
                step_elapsed = time.time() - start_time
                step_remaining = max(0, duration - step_elapsed)
                step_progress = min(1.0, step_elapsed / duration) if duration > 0 else 0.0
                
                if self.update_queue:
                    self.update_queue.put(('UPDATE_STEP_PROGRESS', 
                        (step_index, total_steps, step_remaining, step_progress)))
                
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
                        logger.warning(f"Pump timeout during flow update: {error_type}: {error_msg}")
                        
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
                        
                        logger.warning("Experiment stopped due to pump timeout")
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
                    logger.warning(f"Pump timeout during data read: {error_type}: {error_msg}")
                    
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
                    
                    logger.warning("Experiment stopped due to pump timeout")
                    break  # Exit the loop
                
                pressure = self.exp_manager.hw_controller.read_pressure_sensor()
                temperature = self.exp_manager.hw_controller.read_temperature_sensor()
                level = self.exp_manager.hw_controller.read_level_sensor()
                
                # Read Keithley measurements if enabled
                keithley_voltage = None
                keithley_current = None
                if self.keithley_output_enabled and self.hw_controller.smu is not None:
                    try:
                        # Get current mode - prefer step's measurement_mode, fallback to UI
                        measurement_mode = step.get('measurement_mode', None)
                        if measurement_mode:
                            current_mode = measurement_mode
                        else:
                            current_mode = self.keithley_mode_var.get()  # "voltage" or "current"
                        
                        # Measure with correct mode
                        smu_measurement = self.hw_controller.measure_smu(mode=current_mode)
                        if smu_measurement:
                            keithley_voltage = smu_measurement.get('voltage', None)
                            keithley_current = smu_measurement.get('current', None)
                            
                            # Update display
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
                    self.update_queue.put(('UPDATE_STATUS', status_msg))
                
                # Update data arrays (thread-safe with lock - BUG FIX #1)
                with self.data_lock:
                    self.flow_x_data.append(elapsed_time_from_start)
                    self.flow_y_data.append(pump_data['flow'])
                    self.pressure_x_data.append(elapsed_time_from_start)
                    # Append pressure (or NaN if sensor disconnected) - FIXED: Handle None like temperature
                    if pressure is not None:
                        self.pressure_y_data.append(pressure)
                    else:
                        # Use NaN to show gaps in graph when sensor is disconnected
                        self.pressure_y_data.append(float('nan'))
                    self.temp_x_data.append(elapsed_time_from_start)
                    # Append temperature (or NaN if sensor disconnected)
                    if temperature is not None:
                        self.temp_y_data.append(temperature)
                    else:
                        # Use NaN to show gaps in graph when sensor is disconnected
                        self.temp_y_data.append(float('nan'))
                    self.level_x_data.append(elapsed_time_from_start)
                    # FIXED: Handle None like temperature and pressure
                    if level is not None:
                        self.level_y_data.append(level * 100)
                    else:
                        # Use NaN to show gaps in graph when sensor is disconnected
                        self.level_y_data.append(float('nan'))
                    
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
                    "measurement_id": self.measurement_counter,
                    "time": elapsed_time_from_start,
                    "flow_setpoint": self.current_flow_rate,
                    "pump_flow_read": pump_data['flow'],
                    "pressure_read": pressure if pressure is not None else "",  # FIXED: Handle None like temperature
                    "temp_read": temperature if temperature is not None else "",
                    "level_read": level if level is not None else "",  # FIXED: Handle None
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
                        if loop_count == 1:  # Log on first iteration
                            logger.debug(f"Sent graph updates to queue")
                            logger.debug(f"Flow data: {len(flow_x_copy)} points")
                            logger.debug(f"Pressure data: {len(pressure_x_copy)} points")
                    except Exception as e:
                        logger.warning(f"Error updating graphs: {e}")
                time.sleep(1)
            
            # Send step complete notification
            if self.update_queue:
                self.update_queue.put(('UPDATE_STEP_COMPLETE', (step_index, total_steps)))
        
        # Stop the pump when experiment ends
        self.exp_manager.hw_controller.stop_pump()
        
        # Stop Keithley if enabled
        if self.keithley_output_enabled and self.hw_controller.smu is not None:
            try:
                self.hw_controller.stop_smu()
                logger.debug("Keithley stopped")
            except Exception as e:
                logger.warning(f"Error stopping Keithley: {e}")
        
        self.exp_manager.stop_experiment()
        
        # Update last total time (thread-safe - BUG FIX #1)
        with self.data_lock:
            if len(self.flow_x_data) > 0:
                self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
        
        if self.update_queue:
            self.update_queue.put(('UPDATE_STATUS', f'Experiment paused. Total time: {self.last_total_time:.1f}s. Click Start to continue.'))
            self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Paused', 'orange')))

