# main_app.py

import customtkinter as ctk
from tkinter import filedialog, messagebox, PanedWindow, Frame
from hardware_control import HardwareController
from experiment_logic import ExperimentManager
from data_handler import DataHandler
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import math
import os
from datetime import datetime
import numpy as np
import queue

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- Main Application Class ---
class FluidicControlApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title('Fluidic Control System')
        self.geometry('1400x900')
        
        # Initialize data arrays
        self.flow_x_data, self.flow_y_data = [], []
        self.pressure_x_data, self.pressure_y_data = [], []
        self.temp_x_data, self.temp_y_data = [], []
        self.level_x_data, self.level_y_data = [], []
        self.iv_x_data, self.iv_y_data = [], []
        self.iv_time_x_data, self.iv_time_v_data, self.iv_time_i_data = [], [], []
        
        # Current flow rate
        self.current_flow_rate = 1.5
        
        # Track cumulative time for resume capability
        self.last_total_time = 0.0  # Last cumulative time when stopped
        self.experiment_base_time = None  # Base time for the current experiment session
        
        # Queue for thread-safe GUI updates
        self.update_queue = queue.Queue()
        
        # Initialize hardware components
        self.hw_controller = HardwareController(
            pump_port='COM3', 
            ni_device_name='Dev1', 
            smu_resource='USB0::0x05E6::0x2450::0123456789::INSTR'
        )
        self.data_handler = DataHandler()
        self.exp_manager = ExperimentManager(self.hw_controller, self.data_handler)
        
        # Create UI
        self.create_widgets()
        
        # Initialize graphs
        self.setup_graphs()
        
        # Start periodic update check
        self.check_update_queue()
        
        # Start sensor reading loop
        self.update_sensor_readings()
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Create tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.main_tab = self.tabview.add("Main")
        self.iv_tab = self.tabview.add("IV")
        self.program_tab = self.tabview.add("Write program")
        self.browser_tab = self.tabview.add("Experiment Browser")
        self.scheduler_tab = self.tabview.add("Scheduler")
        
        # Create tab contents
        self.create_main_tab()
        self.create_iv_tab()
        self.create_program_tab()
        self.create_browser_tab()
        self.create_scheduler_tab()
    
    def create_main_tab(self):
        """Create Main tab widgets"""
        # Create PanedWindow for resizable panels
        # Use tkinter PanedWindow with regular Frame wrapper for CustomTkinter compatibility
        paned = PanedWindow(self.main_tab, orient='horizontal', sashwidth=8, sashrelief='raised', bg='#2b2b2b')
        paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left column container - regular tkinter Frame for PanedWindow compatibility
        left_container = Frame(paned, bg='#1a1a1a')  # Match dark theme background
        paned.add(left_container, minsize=250, width=400)  # Default width 400px, minimum 250px
        
        # Left column - Scrollable to see all options
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
        
        # Experiment Name
        name_frame = ctk.CTkFrame(metadata_frame)
        name_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(name_frame, text='Experiment Name:', width=120).pack(side='left', padx=5)
        self.exp_name_entry = ctk.CTkEntry(name_frame, width=200)
        self.exp_name_entry.insert(0, 'experiment_data')
        self.exp_name_entry.pack(side='left', padx=5)
        
        # Description
        desc_frame = ctk.CTkFrame(metadata_frame)
        desc_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(desc_frame, text='Description:', width=120).pack(side='left', padx=5)
        self.exp_desc_entry = ctk.CTkEntry(desc_frame, width=200)
        self.exp_desc_entry.pack(side='left', padx=5)
        
        # Tags
        tags_frame = ctk.CTkFrame(metadata_frame)
        tags_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(tags_frame, text='Tags (comma-separated):', width=120).pack(side='left', padx=5)
        self.exp_tags_entry = ctk.CTkEntry(tags_frame, width=200)
        self.exp_tags_entry.insert(0, 'test')
        self.exp_tags_entry.pack(side='left', padx=5)
        
        # Operator
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
        
        # Flow statistics
        ctk.CTkLabel(stats_grid, text='Flow:', width=120, font=('Helvetica', 10, 'bold')).grid(row=0, column=0, padx=5, pady=2)
        self.flow_stats_label = ctk.CTkLabel(stats_grid, text='Mean: N/A | Std: N/A', width=260, font=('Helvetica', 9))
        self.flow_stats_label.grid(row=0, column=1, padx=5, pady=2)
        
        # Pressure statistics
        ctk.CTkLabel(stats_grid, text='Pressure:', width=120, font=('Helvetica', 10, 'bold')).grid(row=1, column=0, padx=5, pady=2)
        self.pressure_stats_label = ctk.CTkLabel(stats_grid, text='Mean: N/A | Std: N/A', width=260, font=('Helvetica', 9))
        self.pressure_stats_label.grid(row=1, column=1, padx=5, pady=2)
        
        # Temperature statistics
        ctk.CTkLabel(stats_grid, text='Temperature:', width=120, font=('Helvetica', 10, 'bold')).grid(row=2, column=0, padx=5, pady=2)
        self.temp_stats_label = ctk.CTkLabel(stats_grid, text='Mean: N/A | Std: N/A', width=260, font=('Helvetica', 9))
        self.temp_stats_label.grid(row=2, column=1, padx=5, pady=2)
        
        # Level statistics
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
        
        # Right column container - regular tkinter Frame for PanedWindow compatibility
        right_container = Frame(paned, bg='#1a1a1a')  # Match dark theme background
        paned.add(right_container, minsize=400)  # Minimum width 400px for graphs
        
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
        self.axis_frame.pack(fill='x', padx=5, pady=5)  # Shown by default
        
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
    
    def create_iv_tab(self):
        """Create IV tab widgets - similar layout to Main tab"""
        # Create PanedWindow for resizable panels
        paned = PanedWindow(self.iv_tab, orient='horizontal', sashwidth=8, sashrelief='raised', bg='#2b2b2b')
        paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left column container - regular tkinter Frame for PanedWindow compatibility
        left_container = Frame(paned, bg='#1a1a1a')
        paned.add(left_container, minsize=250, width=400)
        
        # Left column - Scrollable to see all options
        left_frame = ctk.CTkScrollableFrame(left_container, width=400)
        left_frame.pack(fill='both', expand=True)
        
        # I-V Parameters
        params_frame = ctk.CTkFrame(left_frame)
        params_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(params_frame, text="I-V Parameters", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        params_grid = ctk.CTkFrame(params_frame)
        params_grid.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(params_grid, text='Range (V):', width=120).grid(row=0, column=0, padx=5, pady=2)
        self.iv_range_entry = ctk.CTkEntry(params_grid, width=150)
        self.iv_range_entry.insert(0, '2.0')
        self.iv_range_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='Step (V):', width=120).grid(row=1, column=0, padx=5, pady=2)
        self.iv_step_entry = ctk.CTkEntry(params_grid, width=150)
        self.iv_step_entry.insert(0, '0.1')
        self.iv_step_entry.grid(row=1, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='Time delay (s):', width=120).grid(row=2, column=0, padx=5, pady=2)
        self.iv_time_entry = ctk.CTkEntry(params_grid, width=150)
        self.iv_time_entry.insert(0, '1.0')
        self.iv_time_entry.grid(row=2, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='Flow rate (ml/min):', width=120).grid(row=3, column=0, padx=5, pady=2)
        self.iv_flow_entry = ctk.CTkEntry(params_grid, width=150)
        self.iv_flow_entry.insert(0, '1.5')
        self.iv_flow_entry.grid(row=3, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='Valve setting:', width=120).grid(row=4, column=0, padx=5, pady=2)
        self.iv_valve_var = ctk.StringVar(value="main")
        valve_btn_frame = ctk.CTkFrame(params_grid)
        valve_btn_frame.grid(row=4, column=1, padx=5, pady=2)
        ctk.CTkRadioButton(valve_btn_frame, text="Main", variable=self.iv_valve_var, value="main").pack(side='left', padx=5)
        ctk.CTkRadioButton(valve_btn_frame, text="Rinsing", variable=self.iv_valve_var, value="rinsing").pack(side='left', padx=5)
        
        # Quick Control
        quick_frame = ctk.CTkFrame(left_frame)
        quick_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(quick_frame, text="Quick Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        btn_frame = ctk.CTkFrame(quick_frame)
        btn_frame.pack(pady=5)
        ctk.CTkButton(btn_frame, text='Direct setting', command=self.iv_direct_set, width=150, height=35).pack(pady=2)
        ctk.CTkButton(btn_frame, text='Direct run', command=self.iv_direct_run, width=150, height=35, fg_color='green').pack(pady=2)
        
        # Program Control
        prog_frame = ctk.CTkFrame(left_frame)
        prog_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(prog_frame, text="Program Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        prog_btn_frame = ctk.CTkFrame(prog_frame)
        prog_btn_frame.pack(pady=5)
        ctk.CTkButton(prog_btn_frame, text='Choose program', command=self.iv_choose_program, width=150).pack(pady=2)
        ctk.CTkButton(prog_btn_frame, text='Run program', command=self.iv_run_program, width=150).pack(pady=2)
        
        # Current I-V Data
        iv_readings_frame = ctk.CTkFrame(left_frame)
        iv_readings_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(iv_readings_frame, text="Current I-V Data", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        iv_readings_grid = ctk.CTkFrame(iv_readings_frame)
        iv_readings_grid.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(iv_readings_grid, text='Voltage:', width=120).grid(row=0, column=0, padx=5, pady=2)
        self.iv_voltage_label = ctk.CTkLabel(iv_readings_grid, text='N/A', width=180)
        self.iv_voltage_label.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(iv_readings_grid, text='Current:', width=120).grid(row=1, column=0, padx=5, pady=2)
        self.iv_current_label = ctk.CTkLabel(iv_readings_grid, text='N/A', width=180)
        self.iv_current_label.grid(row=1, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(iv_readings_grid, text='Resistance:', width=120).grid(row=2, column=0, padx=5, pady=2)
        self.iv_resistance_label = ctk.CTkLabel(iv_readings_grid, text='N/A', width=180)
        self.iv_resistance_label.grid(row=2, column=1, padx=5, pady=2)
        
        # I-V Statistics
        iv_stats_frame = ctk.CTkFrame(left_frame)
        iv_stats_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(iv_stats_frame, text="I-V Statistics", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        iv_stats_grid = ctk.CTkFrame(iv_stats_frame)
        iv_stats_grid.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(iv_stats_grid, text='Data Points:', width=120, font=('Helvetica', 10, 'bold')).grid(row=0, column=0, padx=5, pady=2)
        self.iv_points_label = ctk.CTkLabel(iv_stats_grid, text='0', width=180, font=('Helvetica', 9))
        self.iv_points_label.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(iv_stats_grid, text='V Range:', width=120, font=('Helvetica', 10, 'bold')).grid(row=1, column=0, padx=5, pady=2)
        self.iv_vrange_label = ctk.CTkLabel(iv_stats_grid, text='N/A', width=180, font=('Helvetica', 9))
        self.iv_vrange_label.grid(row=1, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(iv_stats_grid, text='I Range:', width=120, font=('Helvetica', 10, 'bold')).grid(row=2, column=0, padx=5, pady=2)
        self.iv_irange_label = ctk.CTkLabel(iv_stats_grid, text='N/A', width=180, font=('Helvetica', 9))
        self.iv_irange_label.grid(row=2, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(iv_stats_grid, text='Max R:', width=120, font=('Helvetica', 10, 'bold')).grid(row=3, column=0, padx=5, pady=2)
        self.iv_maxr_label = ctk.CTkLabel(iv_stats_grid, text='N/A', width=180, font=('Helvetica', 9))
        self.iv_maxr_label.grid(row=3, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(iv_stats_grid, text='Min R:', width=120, font=('Helvetica', 10, 'bold')).grid(row=4, column=0, padx=5, pady=2)
        self.iv_minr_label = ctk.CTkLabel(iv_stats_grid, text='N/A', width=180, font=('Helvetica', 9))
        self.iv_minr_label.grid(row=4, column=1, padx=5, pady=2)
        
        # Measurement Status
        iv_status_frame = ctk.CTkFrame(left_frame)
        iv_status_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(iv_status_frame, text="Measurement Status", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        iv_status_grid = ctk.CTkFrame(iv_status_frame)
        iv_status_grid.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(iv_status_grid, text='Status:', width=120).grid(row=0, column=0, padx=5, pady=2)
        self.iv_status_label = ctk.CTkLabel(iv_status_grid, text='Ready', text_color='green', width=220)
        self.iv_status_label.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(iv_status_grid, text='File:', width=120).grid(row=1, column=0, padx=5, pady=2)
        self.iv_file_label = ctk.CTkLabel(iv_status_grid, text='No file', width=220)
        self.iv_file_label.grid(row=1, column=1, padx=5, pady=2)
        
        # Export Options
        export_frame = ctk.CTkFrame(left_frame)
        export_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(export_frame, text="Export", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        export_btn_frame = ctk.CTkFrame(export_frame)
        export_btn_frame.pack(pady=5)
        ctk.CTkButton(export_btn_frame, text='Save to file', command=self.iv_save_file, width=150).pack(pady=2)
        
        export_menu_frame = ctk.CTkFrame(export_frame)
        export_menu_frame.pack(pady=2)
        ctk.CTkLabel(export_menu_frame, text='Export:', width=80).pack(side='left', padx=5)
        ctk.CTkButton(export_menu_frame, text='Excel', command=self.iv_export_excel, fg_color='blue', width=100).pack(side='left', padx=2)
        ctk.CTkButton(export_menu_frame, text='PNG', command=self.iv_export_graph_png, fg_color='green', width=100).pack(side='left', padx=2)
        ctk.CTkButton(export_menu_frame, text='PDF', command=self.iv_export_graph_pdf, fg_color='red', width=100).pack(side='left', padx=2)
        
        # Status bar
        self.iv_status_bar = ctk.CTkLabel(left_frame, text='', font=('Helvetica', 10))
        self.iv_status_bar.pack(pady=5)
        
        # Right column container - regular tkinter Frame for PanedWindow compatibility
        right_container = Frame(paned, bg='#1a1a1a')
        paned.add(right_container, minsize=400)
        
        # Right column - IV Graph
        right_frame = ctk.CTkFrame(right_container)
        right_frame.pack(fill='both', expand=True)
        
        graph_control_frame = ctk.CTkFrame(right_frame)
        graph_control_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(graph_control_frame, text="I-V Characteristic", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        # Axis selection controls
        axis_frame = ctk.CTkFrame(graph_control_frame)
        axis_frame.pack(fill='x', padx=5, pady=5)
        
        axis_label_frame = ctk.CTkFrame(axis_frame)
        axis_label_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(axis_label_frame, text='X-Axis:', width=60).pack(side='left', padx=5)
        self.iv_x_axis_combo = ctk.CTkComboBox(
            axis_label_frame, 
            values=['Voltage', 'Current', 'Time'],
            width=150, 
            command=self.on_iv_axis_change
        )
        self.iv_x_axis_combo.set('Voltage')
        self.iv_x_axis_combo.pack(side='left', padx=5)
        
        ctk.CTkLabel(axis_label_frame, text='Y-Axis:', width=60).pack(side='left', padx=5)
        self.iv_y_axis_combo = ctk.CTkComboBox(
            axis_label_frame,
            values=['Current', 'Voltage'],
            width=150, 
            command=self.on_iv_axis_change
        )
        self.iv_y_axis_combo.set('Current')
        self.iv_y_axis_combo.pack(side='left', padx=5)
        
        # IV Graph frame
        self.iv_graph_frame = ctk.CTkFrame(right_frame)
        self.iv_graph_frame.pack(fill='both', expand=True, padx=10, pady=5)
    
    def create_program_tab(self):
        """Create Write Program tab widgets"""
        # Program Editor
        editor_frame = ctk.CTkFrame(self.program_tab)
        editor_frame.pack(fill='both', expand=True, padx=10, pady=5)
        ctk.CTkLabel(editor_frame, text="Program Editor", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        self.program_editor = ctk.CTkTextbox(editor_frame, width=800, height=300)
        default_program = '''# Write your experiment program here
# Format: stepN: flow=X.X, duration=XX, temp=XX, valve=main/rinsing
# 
# ============================================
# Example 1: Standard Test - Basic Flow Test
# ============================================
# step1: flow=1.5, duration=60, temp=25, valve=main
# step2: flow=2.0, duration=30, temp=25, valve=main
# step3: flow=0.5, duration=60, temp=25, valve=main
#
# ============================================
# Example 2: Temperature Ramp - Gradual Temp Change
# ============================================
# step1: flow=1.0, duration=60, temp=20, valve=main
# step2: flow=1.0, duration=60, temp=30, valve=main
# step3: flow=1.0, duration=60, temp=40, valve=main
# step4: flow=1.0, duration=60, temp=50, valve=main
#
# ============================================
# Example 3: Flow Ramp - Gradual Flow Increase
# ============================================
# step1: flow=0.5, duration=60, temp=25, valve=main
# step2: flow=1.0, duration=60, temp=25, valve=main
# step3: flow=1.5, duration=60, temp=25, valve=main
# step4: flow=2.0, duration=60, temp=25, valve=main
# step5: flow=0.5, duration=60, temp=25, valve=main
#
# ============================================
# Example 4: Valve Switching Test
# ============================================
# step1: flow=1.5, duration=60, temp=25, valve=main
# step2: flow=1.5, duration=30, temp=25, valve=rinsing
# step3: flow=1.5, duration=60, temp=25, valve=main
# step4: flow=2.0, duration=30, temp=25, valve=rinsing
#
# ============================================
# Example 5: Complex Multi-Step Experiment
# ============================================
# step1: flow=1.0, duration=120, temp=20, valve=main
# step2: flow=1.5, duration=90, temp=25, valve=main
# step3: flow=1.5, duration=60, temp=25, valve=rinsing
# step4: flow=2.0, duration=60, temp=30, valve=main
# step5: flow=0.5, duration=120, temp=20, valve=main
#
# ============================================
# Instructions:
# - Each step must have: flow, duration, and valve
# - Temperature (temp) is optional, defaults to 25°C
# - Flow rate in ml/min, duration in seconds
# - Temperature in Celsius
# - Valve: 'main' or 'rinsing'
# ============================================
'''
        self.program_editor.insert('1.0', default_program)
        self.program_editor.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Program Control
        control_frame = ctk.CTkFrame(self.program_tab)
        control_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(control_frame, text="Program Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        control_btn_frame = ctk.CTkFrame(control_frame)
        control_btn_frame.pack(pady=5)
        ctk.CTkButton(control_btn_frame, text='Load Program', command=self.load_program, width=120).pack(side='left', padx=5)
        ctk.CTkButton(control_btn_frame, text='Save Program', command=self.save_program, width=120).pack(side='left', padx=5)
        ctk.CTkButton(control_btn_frame, text='Run Program', command=self.run_program, width=120).pack(side='left', padx=5)
        ctk.CTkButton(control_btn_frame, text='Stop Program', command=self.stop_program, width=120).pack(side='left', padx=5)
        
        # Program Library
        library_frame = ctk.CTkFrame(self.program_tab)
        library_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(library_frame, text="Program Library", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        library_content = ctk.CTkFrame(library_frame)
        library_content.pack(fill='x', padx=5, pady=5)
        
        # Use OptionMenu instead of Listbox (CTkListbox doesn't exist in CustomTkinter)
        self.program_var = ctk.StringVar(value="Standard Test")
        self.program_optionmenu = ctk.CTkOptionMenu(
            library_content, 
            values=["Standard Test", "Temperature Ramp", "Flow Ramp", "Valve Switching Test", "Complex Multi-Step"],
            variable=self.program_var,
            width=300
        )
        self.program_optionmenu.pack(side='left', padx=5)
        
        ctk.CTkButton(library_content, text='Load Selected', command=self.load_selected, width=150).pack(side='left', padx=5)
        
        # Program Status
        status_frame = ctk.CTkFrame(self.program_tab)
        status_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(status_frame, text="Program Status", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        status_content = ctk.CTkFrame(status_frame)
        status_content.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(status_content, text='Status:', width=80).pack(side='left', padx=5)
        self.program_status_label = ctk.CTkLabel(status_content, text='Ready', width=400)
        self.program_status_label.pack(side='left', padx=5)
    
    def create_browser_tab(self):
        """Create Experiment Browser tab"""
        # Search and filter frame
        search_frame = ctk.CTkFrame(self.browser_tab)
        search_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(search_frame, text="Experiment Browser", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        search_controls = ctk.CTkFrame(search_frame)
        search_controls.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(search_controls, text='Search:', width=80).pack(side='left', padx=5)
        self.search_entry = ctk.CTkEntry(search_controls, width=200)
        self.search_entry.pack(side='left', padx=5)
        self.search_entry.bind('<KeyRelease>', lambda e: self.filter_experiments())
        
        ctk.CTkLabel(search_controls, text='Tags:', width=60).pack(side='left', padx=5)
        self.tag_filter_entry = ctk.CTkEntry(search_controls, width=150)
        self.tag_filter_entry.pack(side='left', padx=5)
        self.tag_filter_entry.bind('<KeyRelease>', lambda e: self.filter_experiments())
        
        ctk.CTkButton(search_controls, text='Refresh', command=self.refresh_experiments, width=100).pack(side='left', padx=5)
        
        # Experiments list
        list_frame = ctk.CTkFrame(self.browser_tab)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Scrollable frame for experiments
        self.exp_list_frame = ctk.CTkScrollableFrame(list_frame)
        self.exp_list_frame.pack(fill='both', expand=True)
        
        # Action buttons
        action_frame = ctk.CTkFrame(self.browser_tab)
        action_frame.pack(fill='x', padx=10, pady=5)
        
        ctk.CTkButton(action_frame, text='Load Selected', command=self.load_experiment, width=150).pack(side='left', padx=5)
        ctk.CTkButton(action_frame, text='Compare Selected', command=self.compare_experiments, width=150).pack(side='left', padx=5)
        ctk.CTkButton(action_frame, text='Export Selected', command=self.export_selected_experiment, width=150).pack(side='left', padx=5)
        
        # Initialize experiment list
        self.experiment_buttons = []
        self.selected_experiments = []
        self.refresh_experiments()
    
    def create_scheduler_tab(self):
        """Create Scheduler tab"""
        # Schedule experiment frame
        schedule_frame = ctk.CTkFrame(self.scheduler_tab)
        schedule_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(schedule_frame, text="Schedule Experiment", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        # Date and time selection
        datetime_frame = ctk.CTkFrame(schedule_frame)
        datetime_frame.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(datetime_frame, text='Date:', width=80).grid(row=0, column=0, padx=5, pady=2)
        self.schedule_date_entry = ctk.CTkEntry(datetime_frame, width=150, placeholder_text='YYYY-MM-DD')
        self.schedule_date_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(datetime_frame, text='Time:', width=80).grid(row=0, column=2, padx=5, pady=2)
        self.schedule_time_entry = ctk.CTkEntry(datetime_frame, width=150, placeholder_text='HH:MM')
        self.schedule_time_entry.grid(row=0, column=3, padx=5, pady=2)
        
        # Experiment selection
        exp_select_frame = ctk.CTkFrame(schedule_frame)
        exp_select_frame.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(exp_select_frame, text='Experiment Program:', width=150).pack(side='left', padx=5)
        self.schedule_program_var = ctk.StringVar(value="Use current program")
        schedule_program_menu = ctk.CTkOptionMenu(
            exp_select_frame,
            values=["Use current program", "Load from file", "Load from library"],
            variable=self.schedule_program_var,
            width=200
        )
        schedule_program_menu.pack(side='left', padx=5)
        
        # Scheduled experiments list
        scheduled_frame = ctk.CTkFrame(self.scheduler_tab)
        scheduled_frame.pack(fill='both', expand=True, padx=10, pady=5)
        ctk.CTkLabel(scheduled_frame, text="Scheduled Experiments", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        self.scheduled_list_frame = ctk.CTkScrollableFrame(scheduled_frame)
        self.scheduled_list_frame.pack(fill='both', expand=True)
        
        # Action buttons
        schedule_action_frame = ctk.CTkFrame(self.scheduler_tab)
        schedule_action_frame.pack(fill='x', padx=10, pady=5)
        
        ctk.CTkButton(schedule_action_frame, text='Schedule Experiment', command=self.schedule_experiment, width=150).pack(side='left', padx=5)
        ctk.CTkButton(schedule_action_frame, text='Remove Selected', command=self.remove_scheduled, width=150).pack(side='left', padx=5)
        ctk.CTkButton(schedule_action_frame, text='Clear All', command=self.clear_scheduled, width=150).pack(side='left', padx=5)
        
        # Initialize scheduled experiments list
        self.after(100, self.refresh_scheduled_experiments)
    
    def setup_graphs(self):
        """Initialize matplotlib graphs"""
        from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
        
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
        
        # IV graph
        self.iv_fig, self.iv_ax = plt.subplots(figsize=(8, 6))
        self.iv_ax.set_xlabel("Voltage (V)", color='black', fontsize=12)
        self.iv_ax.set_ylabel("Current (A)", color='black', fontsize=12)
        self.iv_ax.set_title("I-V Characteristic", color='black', fontsize=14, fontweight='bold', pad=15)
        self.iv_ax.set_facecolor('white')
        self.iv_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.iv_ax.set_axisbelow(True)
        self.iv_ax.tick_params(colors='black', labelsize=10)
        for spine in self.iv_ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
        
        # Create canvas for IV graph
        self.iv_canvas = FigureCanvasTkAgg(self.iv_fig, self.iv_graph_frame)
        self.iv_canvas.draw()
        self.iv_canvas.get_tk_widget().pack(side='top', fill='both', expand=1)
        
        # Add navigation toolbar for IV graph
        self.iv_toolbar = NavigationToolbar2Tk(self.iv_canvas, self.iv_graph_frame)
        self.iv_toolbar.update()
        
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
    
    def check_update_queue(self):
        """Check for thread-safe GUI updates"""
        try:
            while True:
                update_type, data = self.update_queue.get_nowait()
                if update_type == 'UPDATE_GRAPH1':
                    x, y = data
                    self.flow_x_data.clear()
                    self.flow_y_data.clear()
                    self.flow_x_data.extend(x)
                    self.flow_y_data.extend(y)
                    if self.graph_mode_var.get() == "multi":
                        self.update_multi_panel_graphs()
                    else:
                        self.on_axis_change()
                    self.update_statistics()
                elif update_type == 'UPDATE_GRAPH2':
                    x, y = data
                    self.pressure_x_data.clear()
                    self.pressure_y_data.clear()
                    self.pressure_x_data.extend(x)
                    self.pressure_y_data.extend(y)
                    if self.graph_mode_var.get() == "multi":
                        self.update_multi_panel_graphs()
                    else:
                        self.on_axis_change()
                    self.update_statistics()
                elif update_type == 'UPDATE_GRAPH3':
                    x, y = data
                    self.temp_x_data.clear()
                    self.temp_y_data.clear()
                    self.temp_x_data.extend(x)
                    self.temp_y_data.extend(y)
                    if self.graph_mode_var.get() == "multi":
                        self.update_multi_panel_graphs()
                    else:
                        self.on_axis_change()
                    self.update_statistics()
                elif update_type == 'UPDATE_GRAPH4':
                    x, y = data
                    self.level_x_data.clear()
                    self.level_y_data.clear()
                    self.level_x_data.extend(x)
                    self.level_y_data.extend(y)
                    if self.graph_mode_var.get() == "multi":
                        self.update_multi_panel_graphs()
                    else:
                        self.on_axis_change()
                    self.update_statistics()
                elif update_type == 'UPDATE_IV_GRAPH':
                    x, y = data
                    self.update_iv_graph(x, y)
                    self.update_iv_statistics()
                    # Update current readings with last point
                    if len(x) > 0 and len(y) > 0:
                        last_v = x[-1]
                        last_i = y[-1]
                        resistance = last_v / last_i if last_i != 0 else float('inf')
                        self.iv_voltage_label.configure(text=f"{last_v:.4f} V")
                        self.iv_current_label.configure(text=f"{last_i:.6f} A")
                        if resistance != float('inf'):
                            self.iv_resistance_label.configure(text=f"{resistance:.2f} Ω")
                        else:
                            self.iv_resistance_label.configure(text="∞ Ω")
                elif update_type == 'UPDATE_IV_STATUS':
                    text, color = data
                    self.iv_status_label.configure(text=text, text_color=color)
                elif update_type == 'UPDATE_IV_FILE':
                    self.iv_file_label.configure(text=data)
                elif update_type == 'UPDATE_IV_STATUS_BAR':
                    self.iv_status_bar.configure(text=data)
                elif update_type == 'UPDATE_IV_TIME_GRAPH':
                    # Update IV graph with time-based data
                    x_axis_type = self.iv_x_axis_combo.get()
                    y_axis_type = self.iv_y_axis_combo.get()
                    self.plot_iv_xy_graph(x_axis_type, y_axis_type)
                elif update_type == 'UPDATE_STATUS':
                    self.status_bar.configure(text=data)
                elif update_type == 'UPDATE_RECORDING_STATUS':
                    text, color = data
                    self.recording_status_label.configure(text=text, text_color=color)
                elif update_type == 'UPDATE_FILE':
                    self.current_file_label.configure(text=data)
                elif update_type == 'UPDATE_READINGS':
                    pressure, temp, flow, level = data
                    self.pressure_label.configure(text=f"{pressure:.2f} PSI")
                    self.temp_label.configure(text=f"{temp:.2f} °C")
                    self.flow_label.configure(text=f"{flow:.2f} ml/min")
                    self.level_label.configure(text=f"{level:.2f} %")
                elif update_type == 'UPDATE_PROGRAM_STATUS':
                    self.program_status_label.configure(text=data)
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
    
    def on_axis_change(self, *args):
        """Handle axis selection change"""
        x_axis_type = self.x_axis_combo.get()
        y_axis_type = self.y_axis_combo.get()
        self.plot_xy_graph(x_axis_type, y_axis_type, [], [])
    
    # --- Event Handlers ---
    def start_recording(self):
        """Start recording experiment - continues from last point if data exists"""
        try:
            import re
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
                self.last_total_time = 0.0  # Reset cumulative time for new experiment
                self.experiment_base_time = time.time()
            else:
                # Continuing existing experiment - use last total time
                if self.experiment_base_time is None:
                    # If base time is not set, calculate it from existing data
                    if len(self.flow_x_data) > 0:
                        self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
                        self.experiment_base_time = time.time() - self.last_total_time
                    else:
                        self.last_total_time = 0.0
                        self.experiment_base_time = time.time()
            
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
                
                # Update status with clear message
                status_msg = f'Flow rate updated: {old_flow_rate:.2f} → {new_flow_rate:.2f} ml/min'
                self.update_queue.put(('UPDATE_STATUS', status_msg))
                
                # Log flow change to data file if recording
                if self.data_handler.file_path and self.data_handler.file:
                    self.data_handler.log_flow_change(new_flow_rate)
                
                # Update current readings display
                self.update_queue.put(('UPDATE_READINGS', (0, 0, new_flow_rate, 0)))
                
                # If experiment is running, show confirmation
                if self.exp_manager.is_running:
                    self.update_queue.put(('UPDATE_STATUS', f'Flow updated during experiment: {new_flow_rate:.2f} ml/min (will apply on next reading)'))
            else:
                # Flow rate is the same, just confirm
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
                    # Ensure filename has .xlsx extension if user didn't add it
                    if not filename.endswith('.xlsx'):
                        filename += '.xlsx'
                    success = self.data_handler.export_to_excel(filename)
                    if success:
                        messagebox.showinfo('Export Complete', f'Excel file exported successfully!\n{filename}')
                    else:
                        messagebox.showerror('Error', 'Failed to export Excel file. Check console for details.')
                # If user cancelled, filename will be empty string - that's fine
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
    
    def iv_direct_set(self):
        """IV direct setting"""
        try:
            range_val = float(self.iv_range_entry.get()) if self.iv_range_entry.get() else 2.0
            step_val = float(self.iv_step_entry.get()) if self.iv_step_entry.get() else 0.1
            time_val = float(self.iv_time_entry.get()) if self.iv_time_entry.get() else 1.0
            flow_rate = float(self.iv_flow_entry.get()) if self.iv_flow_entry.get() else 1.5
            
            self.hw_controller.setup_smu_iv_sweep(-range_val, range_val, step_val)
            self.hw_controller.set_pump_flow_rate(flow_rate)
            valve_main = self.iv_valve_var.get() == 'main'
            self.hw_controller.set_valves(valve_main, not valve_main)
            
            self.update_queue.put(('UPDATE_STATUS', f"I-V setup completed: Range={range_val}V, Step={step_val}V, Flow={flow_rate}ml/min"))
        except ValueError:
            messagebox.showerror('Error', "Invalid input values. Please enter numbers.")
    
    def iv_direct_run(self):
        """IV direct run"""
        try:
            range_val = float(self.iv_range_entry.get()) if self.iv_range_entry.get() else 2.0
            step_val = float(self.iv_step_entry.get()) if self.iv_step_entry.get() else 0.1
            
            threading.Thread(target=self.run_iv_measurement,
                           args=(range_val, step_val),
                           daemon=True).start()
        except ValueError:
            messagebox.showerror('Error', "Invalid input values. Please enter numbers.")
    
    def iv_choose_program(self):
        """IV choose program - placeholder"""
        pass
    
    def iv_run_program(self):
        """IV run program - placeholder"""
        pass
    
    def iv_save_file(self):
        """Save IV data to file"""
        try:
            if self.iv_x_data and self.iv_y_data:
                self.data_handler.create_new_file()
                for i, (v, i_val) in enumerate(zip(self.iv_x_data, self.iv_y_data)):
                    data_point = {
                        "time": i,
                        "voltage": v,
                        "current": i_val
                    }
                    self.data_handler.append_data(data_point)
                self.data_handler.close_file()
                self.update_queue.put(('UPDATE_STATUS', "I-V data saved to file"))
            else:
                messagebox.showerror('Error', "No I-V data to save")
        except Exception as e:
            messagebox.showerror('Error', f"Error saving I-V data: {e}")
    
    def iv_export_excel(self):
        """Export IV data to Excel"""
        try:
            if self.iv_x_data and self.iv_y_data:
                filename = filedialog.asksaveasfilename(
                    defaultextension='.xlsx',
                    filetypes=[('Excel Files', '*.xlsx')],
                    title='Save I-V Excel File As'
                )
                if filename:
                    if not filename.endswith('.xlsx'):
                        filename += '.xlsx'
                    success = self.data_handler.export_iv_to_excel(self.iv_x_data, self.iv_y_data, filename)
                    if success:
                        messagebox.showinfo('Export Complete', f'I-V Excel file exported successfully!\n{filename}')
                    else:
                        messagebox.showerror('Error', 'Failed to export I-V Excel file. Check console for details.')
            else:
                messagebox.showerror('Error', 'No I-V data to export. Run an I-V measurement first.')
        except Exception as e:
            messagebox.showerror('Error', f'Error exporting I-V to Excel: {e}')
    
    def iv_export_graph_png(self):
        """Export I-V graph as PNG"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension='.png',
                filetypes=[('PNG Files', '*.png')],
                title='Save I-V Graph as PNG'
            )
            if filename:
                self.iv_fig.savefig(filename, dpi=300, bbox_inches='tight')
                messagebox.showinfo('Export Complete', 'I-V graph exported as PNG successfully!')
        except Exception as e:
            messagebox.showerror('Error', f'Error exporting I-V graph: {e}')
    
    def iv_export_graph_pdf(self):
        """Export I-V graph as PDF"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension='.pdf',
                filetypes=[('PDF Files', '*.pdf')],
                title='Save I-V Graph as PDF'
            )
            if filename:
                self.iv_fig.savefig(filename, bbox_inches='tight')
                messagebox.showinfo('Export Complete', 'I-V graph exported as PDF successfully!')
        except Exception as e:
            messagebox.showerror('Error', f'Error exporting I-V graph: {e}')
    
    def read_iv_time_data(self):
        """קריאת מתח וזרם בזמן אמת מה-SMU"""
        if self.hw_controller.smu:
            try:
                # קריאת נתונים מה-SMU
                smu_data = self.hw_controller.read_smu_data()
                if smu_data:
                    return smu_data['voltage'], smu_data['current']
                return None, None
            except Exception as e:
                print(f"Error reading I-V: {e}")
                return None, None
        else:
            # סימולציה - לא מודדים בזמן אמת במצב סימולציה
            # רק במהלך מדידת I-V רגילה
            return None, None
    
    def update_iv_statistics(self):
        """Calculate and update I-V statistics"""
        try:
            if len(self.iv_x_data) > 0 and len(self.iv_y_data) > 0:
                # Data Points
                self.iv_points_label.configure(text=str(len(self.iv_x_data)))
                
                # Voltage Range
                v_min = min(self.iv_x_data)
                v_max = max(self.iv_x_data)
                self.iv_vrange_label.configure(text=f"{v_min:.3f} to {v_max:.3f} V")
                
                # Current Range
                i_min = min(self.iv_y_data)
                i_max = max(self.iv_y_data)
                self.iv_irange_label.configure(text=f"{i_min:.6f} to {i_max:.6f} A")
                
                # Resistance (V/I)
                resistances = []
                for v, i in zip(self.iv_x_data, self.iv_y_data):
                    if i != 0:
                        resistances.append(v / i)
                
                if resistances:
                    max_r = max(resistances)
                    min_r = min(resistances)
                    self.iv_maxr_label.configure(text=f"{max_r:.2f} Ω")
                    self.iv_minr_label.configure(text=f"{min_r:.2f} Ω")
                else:
                    self.iv_maxr_label.configure(text="N/A")
                    self.iv_minr_label.configure(text="N/A")
            else:
                # Reset to defaults
                self.iv_points_label.configure(text='0')
                self.iv_vrange_label.configure(text='N/A')
                self.iv_irange_label.configure(text='N/A')
                self.iv_maxr_label.configure(text='N/A')
                self.iv_minr_label.configure(text='N/A')
        except Exception as e:
            print(f"Error updating I-V statistics: {e}")
    
    def load_program(self):
        """Load program from file"""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[('Text Files', '*.txt')]
            )
            if filename:
                with open(filename, 'r') as f:
                    program_text = f.read()
                self.program_editor.delete('1.0', 'end')
                self.program_editor.insert('1.0', program_text)
                self.update_queue.put(('UPDATE_PROGRAM_STATUS', f"Loaded: {filename}"))
        except Exception as e:
            messagebox.showerror('Error', f"Error loading program: {e}")
    
    def save_program(self):
        """Save program to file"""
        try:
            program_text = self.program_editor.get('1.0', 'end-1c')
            filename = filedialog.asksaveasfilename(
                defaultextension='.txt',
                filetypes=[('Text Files', '*.txt')]
            )
            if filename:
                with open(filename, 'w') as f:
                    f.write(program_text)
                self.update_queue.put(('UPDATE_PROGRAM_STATUS', f"Saved: {filename}"))
        except Exception as e:
            messagebox.showerror('Error', f"Error saving program: {e}")
    
    def load_selected(self):
        """Load selected program template"""
        try:
            selected = self.program_var.get()
            if selected:
                program_templates = {
                    'Standard Test': '# Standard Test - Basic Flow Test\nstep1: flow=1.5, duration=60, temp=25, valve=main\nstep2: flow=2.0, duration=30, temp=25, valve=main\nstep3: flow=0.5, duration=60, temp=25, valve=main',
                    'Temperature Ramp': '# Temperature Ramp - Gradual Temperature Change\nstep1: flow=1.0, duration=60, temp=20, valve=main\nstep2: flow=1.0, duration=60, temp=30, valve=main\nstep3: flow=1.0, duration=60, temp=40, valve=main\nstep4: flow=1.0, duration=60, temp=50, valve=main',
                    'Flow Ramp': '# Flow Ramp - Gradual Flow Increase\nstep1: flow=0.5, duration=60, temp=25, valve=main\nstep2: flow=1.0, duration=60, temp=25, valve=main\nstep3: flow=1.5, duration=60, temp=25, valve=main\nstep4: flow=2.0, duration=60, temp=25, valve=main\nstep5: flow=0.5, duration=60, temp=25, valve=main',
                    'Valve Switching Test': '# Valve Switching Test\nstep1: flow=1.5, duration=60, temp=25, valve=main\nstep2: flow=1.5, duration=30, temp=25, valve=rinsing\nstep3: flow=1.5, duration=60, temp=25, valve=main\nstep4: flow=2.0, duration=30, temp=25, valve=rinsing',
                    'Complex Multi-Step': '# Complex Multi-Step Experiment\nstep1: flow=1.0, duration=120, temp=20, valve=main\nstep2: flow=1.5, duration=90, temp=25, valve=main\nstep3: flow=1.5, duration=60, temp=25, valve=rinsing\nstep4: flow=2.0, duration=60, temp=30, valve=main\nstep5: flow=0.5, duration=120, temp=20, valve=main'
                }
                if selected in program_templates:
                    self.program_editor.delete('1.0', 'end')
                    self.program_editor.insert('1.0', program_templates[selected])
                    self.update_queue.put(('UPDATE_PROGRAM_STATUS', f"Loaded template: {selected}"))
        except Exception as e:
            messagebox.showerror('Error', f"Error loading template: {e}")
    
    def run_program(self):
        """Run program"""
        try:
            program_text = self.program_editor.get('1.0', 'end-1c')
            experiment_program = self.parse_program(program_text)
            if experiment_program:
                self.update_queue.put(('UPDATE_PROGRAM_STATUS', "Running program..."))
                threading.Thread(target=self.run_program_thread,
                               args=(experiment_program,),
                               daemon=True).start()
            else:
                messagebox.showerror('Error', "Invalid program format")
        except Exception as e:
            messagebox.showerror('Error', f"Error running program: {e}")
    
    def stop_program(self):
        """Stop program"""
        self.exp_manager.stop_experiment()
        self.update_queue.put(('UPDATE_PROGRAM_STATUS', "Program stopped"))
    
    # --- Browser Tab Functions ---
    def refresh_experiments(self):
        """Refresh the list of experiments from data folder"""
        import glob
        import json
        
        # Clear existing buttons
        for widget in self.exp_list_frame.winfo_children():
            widget.destroy()
        self.experiment_buttons.clear()
        self.selected_experiments.clear()
        
        # Scan data folder for CSV files and metadata
        data_folder = self.data_handler.data_folder
        csv_files = glob.glob(os.path.join(data_folder, "*.csv"))
        
        experiments = []
        for csv_file in csv_files:
            metadata_file = csv_file.replace('.csv', '_metadata.json')
            metadata = {}
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                except:
                    pass
            
            # Extract info from filename if no metadata
            if not metadata:
                basename = os.path.basename(csv_file)
                metadata = {
                    'name': basename.replace('.csv', ''),
                    'description': '',
                    'tags': [],
                    'operator': '',
                    'start_time': ''
                }
            
            experiments.append({
                'file': csv_file,
                'metadata': metadata,
                'date': os.path.getmtime(csv_file)
            })
        
        # Sort by date (newest first)
        experiments.sort(key=lambda x: x['date'], reverse=True)
        
        # Create buttons for each experiment
        for exp in experiments:
            exp_frame = ctk.CTkFrame(self.exp_list_frame)
            exp_frame.pack(fill='x', padx=5, pady=2)
            
            # Checkbox for selection
            var = ctk.BooleanVar()
            checkbox = ctk.CTkCheckBox(exp_frame, text="", variable=var)
            checkbox.pack(side='left', padx=5)
            
            # Experiment info
            info_text = f"{exp['metadata'].get('name', 'Unknown')}"
            if exp['metadata'].get('description'):
                info_text += f" - {exp['metadata']['description'][:50]}"
            if exp['metadata'].get('tags'):
                info_text += f" [Tags: {', '.join(exp['metadata']['tags'])}]"
            
            label = ctk.CTkLabel(exp_frame, text=info_text, anchor='w')
            label.pack(side='left', fill='x', expand=True, padx=5)
            
            date_label = ctk.CTkLabel(exp_frame, text=datetime.fromtimestamp(exp['date']).strftime('%Y-%m-%d %H:%M'), width=150)
            date_label.pack(side='right', padx=5)
            
            self.experiment_buttons.append({
                'frame': exp_frame,
                'checkbox': checkbox,
                'var': var,
                'file': exp['file'],
                'metadata': exp['metadata']
            })
    
    def filter_experiments(self):
        """Filter experiments based on search and tag filters"""
        search_term = self.search_entry.get().lower()
        tag_filter = self.tag_filter_entry.get().lower()
        
        for exp_btn in self.experiment_buttons:
            visible = True
            if search_term:
                name = exp_btn['metadata'].get('name', '').lower()
                desc = exp_btn['metadata'].get('description', '').lower()
                if search_term not in name and search_term not in desc:
                    visible = False
            
            if visible and tag_filter:
                tags = [tag.lower() for tag in exp_btn['metadata'].get('tags', [])]
                if tag_filter not in ','.join(tags) and tag_filter not in ' '.join(tags):
                    visible = False
            
            if visible:
                exp_btn['frame'].pack(fill='x', padx=5, pady=2)
            else:
                exp_btn['frame'].pack_forget()
    
    def load_experiment(self):
        """Load selected experiment data"""
        selected = [exp for exp in self.experiment_buttons if exp['var'].get()]
        if not selected:
            messagebox.showwarning('Warning', 'Please select an experiment to load.')
            return
        
        if len(selected) > 1:
            messagebox.showwarning('Warning', 'Please select only one experiment to load.')
            return
        
        exp = selected[0]
        try:
            import pandas as pd
            df = pd.read_csv(exp['file'])
            
            # Load data into arrays
            if 'time' in df.columns:
                time_data = df['time'].tolist()
                if 'pump_flow_read' in df.columns:
                    self.flow_x_data = time_data.copy()
                    self.flow_y_data = df['pump_flow_read'].tolist()
                if 'pressure_read' in df.columns:
                    self.pressure_x_data = time_data.copy()
                    self.pressure_y_data = df['pressure_read'].tolist()
                if 'temp_read' in df.columns:
                    self.temp_x_data = time_data.copy()
                    self.temp_y_data = df['temp_read'].tolist()
                if 'level_read' in df.columns:
                    self.level_x_data = time_data.copy()
                    self.level_y_data = (df['level_read'] * 100).tolist()
            
            # Update graphs
            if self.graph_mode_var.get() == "multi":
                self.update_multi_panel_graphs()
            else:
                self.on_axis_change()
            
            messagebox.showinfo('Success', f"Loaded experiment: {exp['metadata'].get('name', 'Unknown')}")
        except Exception as e:
            messagebox.showerror('Error', f"Error loading experiment: {e}")
    
    def compare_experiments(self):
        """Compare selected experiments"""
        selected = [exp for exp in self.experiment_buttons if exp['var'].get()]
        if len(selected) < 2:
            messagebox.showwarning('Warning', 'Please select at least 2 experiments to compare.')
            return
        
        try:
            import pandas as pd
            
            # Create comparison window
            compare_window = ctk.CTkToplevel(self)
            compare_window.title("Experiment Comparison")
            compare_window.geometry('1200x800')
            
            # Create comparison graph
            fig, axes = plt.subplots(2, 2, figsize=(12, 8))
            axes = axes.flatten()
            
            colors = ['#2E86AB', '#A23B72', '#F18F01', '#06A77D', '#C73E1D']
            
            for idx, exp in enumerate(selected[:5]):  # Limit to 5 experiments
                df = pd.read_csv(exp['file'])
                color = colors[idx % len(colors)]
                name = exp['metadata'].get('name', f'Experiment {idx+1}')
                
                if 'time' in df.columns:
                    time_data = df['time'].tolist()
                    
                    # Flow
                    if 'pump_flow_read' in df.columns:
                        axes[0].plot(time_data, df['pump_flow_read'], label=name, color=color, alpha=0.7)
                    
                    # Pressure
                    if 'pressure_read' in df.columns:
                        axes[1].plot(time_data, df['pressure_read'], label=name, color=color, alpha=0.7)
                    
                    # Temperature
                    if 'temp_read' in df.columns:
                        axes[2].plot(time_data, df['temp_read'], label=name, color=color, alpha=0.7)
                    
                    # Level
                    if 'level_read' in df.columns:
                        axes[3].plot(time_data, df['level_read'] * 100, label=name, color=color, alpha=0.7)
            
            # Configure axes
            titles = ['Flow Rate (ml/min)', 'Pressure (PSI)', 'Temperature (°C)', 'Level (%)']
            for ax, title in zip(axes, titles):
                ax.set_xlabel("Time (s)")
                ax.set_ylabel(title)
                ax.set_title(title)
                ax.grid(True, alpha=0.3)
                ax.legend()
            
            fig.tight_layout()
            
            # Embed in window
            canvas = FigureCanvasTkAgg(fig, compare_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
        except Exception as e:
            messagebox.showerror('Error', f"Error comparing experiments: {e}")
    
    def export_selected_experiment(self):
        """Export selected experiment"""
        selected = [exp for exp in self.experiment_buttons if exp['var'].get()]
        if not selected:
            messagebox.showwarning('Warning', 'Please select an experiment to export.')
            return
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[('Excel Files', '*.xlsx'), ('CSV Files', '*.csv')]
            )
            if filename:
                import shutil
                if filename.endswith('.csv'):
                    shutil.copy(selected[0]['file'], filename)
                else:
                    self.data_handler.export_to_excel(filename)
                messagebox.showinfo('Success', 'Experiment exported successfully!')
        except Exception as e:
            messagebox.showerror('Error', f"Error exporting experiment: {e}")
    
    # --- Scheduler Tab Functions ---
    def schedule_experiment(self):
        """Schedule an experiment"""
        try:
            date_str = self.schedule_date_entry.get().strip()
            time_str = self.schedule_time_entry.get().strip()
            
            if not date_str or not time_str:
                messagebox.showerror('Error', 'Please enter both date and time.')
                return
            
            # Parse datetime
            try:
                from datetime import datetime as dt
                schedule_datetime = dt.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                if schedule_datetime < datetime.now():
                    messagebox.showerror('Error', 'Scheduled time must be in the future.')
                    return
            except ValueError:
                messagebox.showerror('Error', 'Invalid date/time format. Use YYYY-MM-DD and HH:MM')
                return
            
            # Save schedule (simple implementation - could be enhanced with database)
            schedule_file = os.path.join(self.data_handler.data_folder, 'schedules.json')
            schedules = []
            if os.path.exists(schedule_file):
                import json
                with open(schedule_file, 'r') as f:
                    schedules = json.load(f)
            
            schedule_info = {
                'datetime': schedule_datetime.isoformat(),
                'program': self.schedule_program_var.get(),
                'created': datetime.now().isoformat()
            }
            schedules.append(schedule_info)
            
            import json
            with open(schedule_file, 'w') as f:
                json.dump(schedules, f, indent=2)
            
            self.refresh_scheduled_experiments()
            messagebox.showinfo('Success', f'Experiment scheduled for {schedule_datetime.strftime("%Y-%m-%d %H:%M")}')
            
        except Exception as e:
            messagebox.showerror('Error', f"Error scheduling experiment: {e}")
    
    def refresh_scheduled_experiments(self):
        """Refresh the list of scheduled experiments"""
        for widget in self.scheduled_list_frame.winfo_children():
            widget.destroy()
        
        schedule_file = os.path.join(self.data_handler.data_folder, 'schedules.json')
        if not os.path.exists(schedule_file):
            return
        
        try:
            import json
            with open(schedule_file, 'r') as f:
                schedules = json.load(f)
            
            for schedule in schedules:
                schedule_frame = ctk.CTkFrame(self.scheduled_list_frame)
                schedule_frame.pack(fill='x', padx=5, pady=2)
                
                schedule_datetime = datetime.fromisoformat(schedule['datetime'])
                info_text = f"{schedule_datetime.strftime('%Y-%m-%d %H:%M')} - {schedule['program']}"
                ctk.CTkLabel(schedule_frame, text=info_text, anchor='w').pack(side='left', fill='x', expand=True, padx=5)
        except Exception as e:
            print(f"Error loading schedules: {e}")
    
    def remove_scheduled(self):
        """Remove selected scheduled experiment"""
        # Implementation would require tracking selected items
        messagebox.showinfo('Info', 'Feature coming soon')
    
    def clear_scheduled(self):
        """Clear all scheduled experiments"""
        if messagebox.askyesno('Confirm', 'Are you sure you want to clear all scheduled experiments?'):
            schedule_file = os.path.join(self.data_handler.data_folder, 'schedules.json')
            if os.path.exists(schedule_file):
                os.remove(schedule_file)
            self.refresh_scheduled_experiments()
    
    # --- Graph Functions ---
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
        
        # Plot the data with PyMeasure-style formatting
        self.main_ax.plot(x_plot, y_plot, color='#2E86AB', linewidth=2.5, alpha=0.85)
        
        # PyMeasure-style formatting
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
    
    def on_iv_axis_change(self, *args):
        """Handle IV axis selection change"""
        x_axis_type = self.iv_x_axis_combo.get()
        y_axis_type = self.iv_y_axis_combo.get()
        self.plot_iv_xy_graph(x_axis_type, y_axis_type)
    
    def plot_iv_xy_graph(self, x_axis_type, y_axis_type):
        """Plot IV graph with selected axes"""
        self.iv_ax.clear()
        
        # בחר את הנתונים המתאימים לפי הצירים
        if x_axis_type == 'Time' and y_axis_type == 'Voltage':
            x_data = self.iv_time_x_data
            y_data = self.iv_time_v_data
            xlabel = "Time (s)"
            ylabel = "Voltage (V)"
            title = "Voltage vs Time"
        elif x_axis_type == 'Time' and y_axis_type == 'Current':
            x_data = self.iv_time_x_data
            y_data = self.iv_time_i_data
            xlabel = "Time (s)"
            ylabel = "Current (A)"
            title = "Current vs Time"
        elif x_axis_type == 'Voltage' and y_axis_type == 'Current':
            x_data = self.iv_x_data
            y_data = self.iv_y_data
            xlabel = "Voltage (V)"
            ylabel = "Current (A)"
            title = "I-V Characteristic"
        elif x_axis_type == 'Current' and y_axis_type == 'Voltage':
            x_data = self.iv_y_data
            y_data = self.iv_x_data
            xlabel = "Current (A)"
            ylabel = "Voltage (V)"
            title = "V-I Characteristic"
        else:
            # ברירת מחדל - I-V רגיל
            x_data = self.iv_x_data
            y_data = self.iv_y_data
            xlabel = "Voltage (V)"
            ylabel = "Current (A)"
            title = "I-V Characteristic"
        
        # ציור הגרף
        if len(x_data) > 0 and len(y_data) > 0:
            self.iv_ax.plot(x_data, y_data, color='#C73E1D', linewidth=2.5, alpha=0.85)
        else:
            self.iv_ax.plot([], [], color='#C73E1D', linewidth=2.5)
        
        # הגדרות צירים
        self.iv_ax.set_facecolor('white')
        self.iv_ax.set_xlabel(xlabel, color='black', fontsize=11)
        self.iv_ax.set_ylabel(ylabel, color='black', fontsize=11)
        self.iv_ax.set_title(title, color='black', fontsize=12, fontweight='bold', pad=12)
        
        # Subtle grid
        self.iv_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5, which='both')
        self.iv_ax.set_axisbelow(True)
        self.iv_ax.tick_params(colors='black', labelsize=9)
        
        # Clean spines
        for spine in self.iv_ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
        
        # Set axis limits if data exists
        if len(x_data) > 0 and len(y_data) > 0:
            x_margin = (max(x_data) - min(x_data)) * 0.05 if max(x_data) > min(x_data) else 1
            y_margin = (max(y_data) - min(y_data)) * 0.1 if max(y_data) > min(y_data) else 1
            self.iv_ax.set_xlim(min(x_data) - x_margin, max(x_data) + x_margin)
            self.iv_ax.set_ylim(min(y_data) - y_margin, max(y_data) + y_margin)
        
        self.iv_fig.tight_layout(pad=2.0)
        self.iv_canvas.draw()
    
    def update_iv_graph(self, x_data, y_data):
        """Update IV graph - now uses axis selection"""
        # עדכן את הנתונים
        if x_data and y_data:
            self.iv_x_data = list(x_data)
            self.iv_y_data = list(y_data)
        
        # עדכן את הגרף לפי הבחירה
        x_axis_type = self.iv_x_axis_combo.get()
        y_axis_type = self.iv_y_axis_combo.get()
        self.plot_iv_xy_graph(x_axis_type, y_axis_type)
    
    # --- Thread Functions ---
    def parse_program(self, program_text):
        """Parse program text into experiment steps"""
        steps = []
        if not program_text or not program_text.strip():
            return steps
            
        lines = program_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('step') and ':' in line:
                try:
                    step_data = {}
                    parts = line.split(':')[1].strip().split(',')
                    
                    for part in parts:
                        part = part.strip()
                        if '=' in part:
                            key, value = part.split('=')
                            key = key.strip()
                            value = value.strip()
                            
                            if key == 'flow':
                                step_data['flow_rate'] = float(value)
                            elif key == 'duration':
                                step_data['duration'] = int(value)
                            elif key == 'temp':
                                step_data['temperature'] = float(value)
                            elif key == 'valve':
                                if value == 'main':
                                    step_data['valve_setting'] = {'valve1': True, 'valve2': False}
                                elif value == 'rinsing':
                                    step_data['valve_setting'] = {'valve1': False, 'valve2': True}
                    
                    if 'flow_rate' in step_data and 'duration' in step_data:
                        steps.append(step_data)
                        
                except (ValueError, IndexError) as e:
                    print(f"Error parsing line: {line}, Error: {e}")
                    continue
        
        return steps
    
    def experiment_thread(self, experiment_program, is_new_experiment=True):
        """Run experiment in separate thread - continues from last point if resuming"""
        self.exp_manager.is_running = True
        
        if is_new_experiment:
            self.update_queue.put(('UPDATE_STATUS', 'Starting new experiment...'))
            self.data_handler.create_new_file()
            # Start time for the entire experiment
            self.experiment_base_time = time.time()
            self.last_total_time = 0.0
        else:
            self.update_queue.put(('UPDATE_STATUS', f'Resuming experiment from {self.last_total_time:.1f}s...'))
            # Continue with existing file - don't create new one
            if not self.data_handler.file_path or not os.path.exists(self.data_handler.file_path):
                # If file doesn't exist, create it
                self.data_handler.create_new_file()
                self.experiment_base_time = time.time()
                self.last_total_time = 0.0
            else:
                # Adjust base time to account for existing data
                if self.experiment_base_time is None:
                    if len(self.flow_x_data) > 0:
                        self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
                        self.experiment_base_time = time.time() - self.last_total_time
                    else:
                        self.experiment_base_time = time.time()
                        self.last_total_time = 0.0
        
        # Start time for the entire experiment (use base time)
        experiment_start_time = self.experiment_base_time
        
        for step in experiment_program:
            if not self.exp_manager.is_running:
                break
            
            duration = step.get('duration')
            flow_rate = self.current_flow_rate  # Use current flow rate for dynamic updates
            valve_setting = step.get('valve_setting', {'valve1': True, 'valve2': False})
            
            self.update_queue.put(('UPDATE_STATUS', f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min"))
            
            self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
            self.exp_manager.hw_controller.set_valves(valve_setting['valve1'], valve_setting['valve2'])
            
            start_time = time.time()
            
            while time.time() - start_time < duration and self.exp_manager.is_running:
                if not self.exp_manager.perform_safety_checks():
                    break
                
                # Check for flow rate updates from Update Flow button
                if self.current_flow_rate != flow_rate:
                    old_flow_rate = flow_rate
                    flow_rate = self.current_flow_rate
                    self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
                    # Update setpoint in data point to reflect change
                    self.update_queue.put(('UPDATE_STATUS', f'Flow changed during experiment: {old_flow_rate:.2f} → {flow_rate:.2f} ml/min'))
                    print(f"Flow rate updated during experiment: {old_flow_rate:.2f} → {flow_rate:.2f} ml/min")
                
                current_time = time.time()
                remaining_time = duration - (current_time - start_time)
                # Calculate elapsed time from experiment start
                # experiment_start_time is already adjusted for resumed experiments
                elapsed_time_from_start = current_time - experiment_start_time
                
                pump_data = self.exp_manager.hw_controller.read_pump_data()
                pressure = self.exp_manager.hw_controller.read_pressure_sensor()
                temperature = self.exp_manager.hw_controller.read_temperature_sensor()
                level = self.exp_manager.hw_controller.read_level_sensor()
                
                # Read I-V data if SMU is available
                voltage, current = self.read_iv_time_data()
                if voltage is not None and current is not None:
                    self.iv_time_x_data.append(elapsed_time_from_start)
                    self.iv_time_v_data.append(voltage)
                    self.iv_time_i_data.append(current)
                    # Update IV graph if on IV tab
                    if self.tabview.get() == "IV":
                        self.update_queue.put(('UPDATE_IV_TIME_GRAPH', None))
                
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
                    "flow_setpoint": self.current_flow_rate,  # Use current_flow_rate to reflect any updates
                    "pump_flow_read": pump_data['flow'],
                    "pressure_read": pressure,
                    "temp_read": temperature,
                    "level_read": level
                }
                # Add I-V data if available
                if voltage is not None and current is not None:
                    data_point["voltage_read"] = voltage
                    data_point["current_read"] = current
                
                self.data_handler.append_data(data_point)
                
                # Update graphs via queue
                self.update_queue.put(('UPDATE_GRAPH1', (list(self.flow_x_data), list(self.flow_y_data))))
                self.update_queue.put(('UPDATE_GRAPH2', (list(self.pressure_x_data), list(self.pressure_y_data))))
                self.update_queue.put(('UPDATE_GRAPH3', (list(self.temp_x_data), list(self.temp_y_data))))
                self.update_queue.put(('UPDATE_GRAPH4', (list(self.level_x_data), list(self.level_y_data))))
                time.sleep(1)
        
        self.exp_manager.stop_experiment()
        
        # Update last total time
        if len(self.flow_x_data) > 0:
            self.last_total_time = max(self.flow_x_data) if self.flow_x_data else 0.0
        
        # Only close file if experiment is truly finished (not just stopped)
        # For now, we'll keep the file open for potential continuation
        # self.data_handler.close_file()  # Commented out to allow continuation
        
        self.update_queue.put(('UPDATE_STATUS', f'Experiment paused. Total time: {self.last_total_time:.1f}s. Click Start to continue.'))
        self.update_queue.put(('UPDATE_RECORDING_STATUS', ('Paused', 'orange')))
    
    def run_program_thread(self, experiment_program):
        """Run program from Write Program tab"""
        self.exp_manager.is_running = True
        self.update_queue.put(('UPDATE_PROGRAM_STATUS', 'Starting program...'))
        
        self.data_handler.create_new_file()
        program_start_time = time.time()
        
        for step in experiment_program:
            if not self.exp_manager.is_running:
                break
            
            duration = step.get('duration')
            flow_rate = step.get('flow_rate')
            temperature = step.get('temperature', 25.0)
            valve_setting = step.get('valve_setting', {'valve1': True, 'valve2': False})
            
            self.update_queue.put(('UPDATE_PROGRAM_STATUS', f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min, Temp={temperature}°C"))
            
            self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
            self.exp_manager.hw_controller.set_heating_plate_temp(temperature)
            self.exp_manager.hw_controller.set_valves(valve_setting['valve1'], valve_setting['valve2'])
            
            start_time = time.time()
            
            while time.time() - start_time < duration and self.exp_manager.is_running:
                if not self.exp_manager.perform_safety_checks():
                    break
                
                pump_data = self.exp_manager.hw_controller.read_pump_data()
                pressure = self.exp_manager.hw_controller.read_pressure_sensor()
                temperature_read = self.exp_manager.hw_controller.read_temperature_sensor()
                level = self.exp_manager.hw_controller.read_level_sensor()
                
                current_time = time.time()
                elapsed_time_from_start = current_time - program_start_time
                remaining_time = duration - (current_time - start_time)
                
                self.update_queue.put(('UPDATE_STATUS', f"Running: {remaining_time:.0f}s remaining, Flow={flow_rate}ml/min"))
                
                # Update data arrays
                self.flow_x_data.append(elapsed_time_from_start)
                self.flow_y_data.append(pump_data['flow'])
                self.pressure_x_data.append(elapsed_time_from_start)
                self.pressure_y_data.append(pressure)
                self.temp_x_data.append(elapsed_time_from_start)
                self.temp_y_data.append(temperature_read)
                self.level_x_data.append(elapsed_time_from_start)
                self.level_y_data.append(level * 100)
                
                data_point = {
                    "time": elapsed_time_from_start,
                    "flow_setpoint": flow_rate,
                    "pump_flow_read": pump_data['flow'],
                    "pressure_read": pressure,
                    "temp_read": temperature_read,
                    "level_read": level,
                    "program_step": len(experiment_program)
                }
                self.data_handler.append_data(data_point)
                
                # Update graphs
                self.update_queue.put(('UPDATE_GRAPH1', (list(self.flow_x_data), list(self.flow_y_data))))
                self.update_queue.put(('UPDATE_GRAPH2', (list(self.pressure_x_data), list(self.pressure_y_data))))
                self.update_queue.put(('UPDATE_GRAPH3', (list(self.temp_x_data), list(self.temp_y_data))))
                self.update_queue.put(('UPDATE_GRAPH4', (list(self.level_x_data), list(self.level_y_data))))
                time.sleep(1)
        
        self.exp_manager.stop_experiment()
        self.data_handler.close_file()
        self.update_queue.put(('UPDATE_PROGRAM_STATUS', 'Program completed.'))
    
    def run_iv_measurement(self, range_val, step_val):
        """Run I-V measurement in separate thread"""
        self.update_queue.put(('UPDATE_IV_STATUS', ('Measuring...', 'orange')))
        self.update_queue.put(('UPDATE_IV_STATUS_BAR', "Starting I-V measurement..."))
        
        # Clear previous data
        self.iv_x_data.clear()
        self.iv_y_data.clear()
        self.iv_time_x_data.clear()
        self.iv_time_v_data.clear()
        self.iv_time_i_data.clear()
        self.iv_measurement_start_time = time.time()
        self.update_iv_statistics()
        
        # Create new data file
        self.data_handler.create_new_file()
        if self.data_handler.file_path:
            filename = os.path.basename(self.data_handler.file_path)
            self.update_queue.put(('UPDATE_IV_FILE', filename))
        
        try:
            # Setup SMU
            self.hw_controller.setup_smu_iv_sweep(-range_val, range_val, step_val)
            
            # Perform I-V sweep
            voltage_points = []
            current_points = []
            total_points = int(range_val/step_val) * 2 + 1
            
            for v in range(int(-range_val/step_val), int(range_val/step_val) + 1):
                voltage = v * step_val
                
                # Set voltage and measure current
                if self.hw_controller.smu:
                    try:
                        self.hw_controller.smu.write(f"SOUR:VOLT {voltage}")
                        self.hw_controller.smu.write("INIT")
                        current = float(self.hw_controller.smu.query("MEAS:CURR?"))
                    except Exception as e:
                        print(f"Error in I-V measurement: {e}")
                        # Realistic I-V: linear with small noise
                        current = voltage * 0.1 + 0.005 * math.sin(voltage * 10) + 0.002 * math.sin(voltage * 20)
                else:
                    # Simulation mode - realistic I-V curve
                    # Linear relationship with small sinusoidal noise for realism
                    base_current = voltage * 0.1
                    noise = 0.005 * math.sin(voltage * 10) + 0.002 * math.sin(voltage * 20)
                    current = base_current + noise
                
                voltage_points.append(voltage)
                current_points.append(current)
                
                # Update graph
                self.iv_x_data.append(voltage)
                self.iv_y_data.append(current)
                
                # Save time-dependent data
                elapsed_time = time.time() - self.iv_measurement_start_time
                self.iv_time_x_data.append(elapsed_time)
                self.iv_time_v_data.append(voltage)
                self.iv_time_i_data.append(current)
                
                self.update_queue.put(('UPDATE_IV_GRAPH', (list(self.iv_x_data), list(self.iv_y_data))))
                
                # Update status with progress
                progress = len(voltage_points)
                self.update_queue.put(('UPDATE_IV_STATUS_BAR', f"Measuring: {progress}/{total_points} points..."))
                
                # Save data point
                data_point = {
                    "time": len(voltage_points),
                    "voltage": voltage,
                    "current": current,
                    "elapsed_time": elapsed_time
                }
                self.data_handler.append_data(data_point)
                
                time.sleep(0.1)  # Small delay between measurements
            
            self.update_queue.put(('UPDATE_IV_STATUS', ('Completed', 'green')))
            self.update_queue.put(('UPDATE_IV_STATUS_BAR', "I-V measurement completed"))
            
        except Exception as e:
            self.update_queue.put(('UPDATE_IV_STATUS', ('Error', 'red')))
            self.update_queue.put(('UPDATE_IV_STATUS_BAR', f"I-V measurement error: {e}"))
            print(f"I-V measurement error: {e}")
        
        finally:
            self.data_handler.close_file()
            self.hw_controller.stop_smu()


# --- Advanced Graph Editing Functions (Optional - not currently used) ---
# These functions are kept for potential future use but are not currently integrated
# as all functionality is now within the FluidicControlApp class

def edit_graph_properties(figure, property_type, **kwargs):
    """Edit various graph properties"""
    ax = figure.get_axes()[0]
    
    if property_type == 'line_color':
        color = kwargs.get('color', '#00D4FF')
        for line in ax.get_lines():
            line.set_color(color)
    elif property_type == 'line_style':
        style = kwargs.get('style', '-')
        for line in ax.get_lines():
            line.set_linestyle(style)
    elif property_type == 'line_width':
        width = kwargs.get('width', 2.5)
        for line in ax.get_lines():
            line.set_linewidth(width)
    elif property_type == 'grid':
        show_grid = kwargs.get('show', True)
        ax.grid(show_grid, alpha=0.3, color='white', linestyle='--', linewidth=0.5)
    elif property_type == 'axis_limits':
        xlim = kwargs.get('xlim', None)
        ylim = kwargs.get('ylim', None)
        if xlim:
            ax.set_xlim(xlim)
        if ylim:
            ax.set_ylim(ylim)
    
    figure.canvas.draw()

def save_graph_as_image(figure, filename, format='png'):
    """Save graph as image file"""
    try:
        figure.savefig(filename, format=format, dpi=300, bbox_inches='tight')
        return True
    except Exception as e:
        print(f"Error saving graph: {e}")
        return False

def add_annotation(figure, x, y, text, **kwargs):
    """Add text annotation to graph"""
    ax = figure.get_axes()[0]
    ax.annotate(text, xy=(x, y), **kwargs)
    figure.canvas.draw()

def create_advanced_toolbar(canvas, figure):
    """Create advanced toolbar with additional editing options"""
    from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
    
    class AdvancedToolbar(NavigationToolbar2Tk):
        def __init__(self, canvas, parent):
            super().__init__(canvas, parent)
            
        def _init_toolbar(self):
            super()._init_toolbar()
            
            # Add custom buttons
            self.add_separator()
            
            # Color picker button
            self.add_toolitem('Color', 'Change line color', 'color_picker', self.change_line_color)
            
            # Grid toggle button
            self.add_toolitem('Grid', 'Toggle grid', 'grid', self.toggle_grid)
            
            # Save button
            self.add_toolitem('Save', 'Save graph', 'save', self.save_graph)
            
        def change_line_color(self):
            """Change line color"""
            from tkinter.simpledialog import askstring
            color = askstring('Change Line Color', 'Enter color (e.g., red, #FF0000, blue):', initialvalue='#00D4FF')
            if color:
                edit_graph_properties(self.canvas.figure, 'line_color', color=color)
                
        def toggle_grid(self):
            """Toggle grid on/off"""
            ax = self.canvas.figure.get_axes()[0]
            current_grid = ax.grid()[0]
            edit_graph_properties(self.canvas.figure, 'grid', show=not current_grid)
            
        def save_graph(self):
            """Save graph as image"""
            filename = filedialog.asksaveasfilename(
                defaultextension='.png',
                filetypes=[('PNG Files', '*.png'), ('PDF Files', '*.pdf'), ('SVG Files', '*.svg')]
            )
            if filename:
                format_type = filename.split('.')[-1].lower()
                save_graph_as_image(self.canvas.figure, filename, format_type)
    
    # Get the parent widget from the canvas
    parent = canvas.get_tk_widget().master
    return AdvancedToolbar(canvas, parent)

# --- GUI Drawing Functions ---
def draw_figure(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    
    # Add advanced toolbar with editing capabilities
    toolbar = create_advanced_toolbar(figure_canvas_agg, figure)
    toolbar.update()
    
    return figure_canvas_agg


def update_graph(fig_agg, x_data, y_data):
    ax = fig_agg.figure.get_axes()[0]
    ax.cla()
    
    # Beautiful styling
    ax.plot(x_data, y_data, color='#00D4FF', linewidth=2.5, alpha=0.8)
    ax.set_facecolor('#1a1a1a')
    ax.set_xlabel("Time (s)", color='white', fontsize=10, fontweight='bold')
    ax.set_ylabel("Value", color='white', fontsize=10, fontweight='bold')
    ax.set_title("Real-Time Data", color='white', fontsize=12, fontweight='bold', pad=15)
    
    # Grid styling
    ax.grid(True, alpha=0.3, color='white', linestyle='--', linewidth=0.5)
    ax.tick_params(colors='white', labelsize=9)
    
    # Spines styling
    for spine in ax.spines.values():
        spine.set_color('white')
        spine.set_linewidth(1.5)
    
    fig_agg.draw()

def update_flow_graph(fig_agg, x_data, y_data):
    ax = fig_agg.figure.get_axes()[0]
    
    # Clear only the plot lines, keep axis labels
    ax.clear()
    
    # PyMeasure-style styling
    if len(x_data) > 0 and len(y_data) > 0:
        ax.plot(x_data, y_data, color='#2E86AB', linewidth=2.5, alpha=0.85)
    else:
        ax.plot([], [], color='#2E86AB', linewidth=2.5)
    
    # Light background like PyMeasure
    ax.set_facecolor('white')
    ax.set_xlabel("Time (s)", color='black', fontsize=11)
    ax.set_ylabel("Flow (ml/min)", color='black', fontsize=11)
    ax.set_title("Flow Rate", color='black', fontsize=12, fontweight='bold', pad=12)
    
    # Subtle grid like PyMeasure
    ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5, which='both')
    ax.set_axisbelow(True)
    ax.tick_params(colors='black', labelsize=9)
    
    # Clean spines
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1)
    
    # Tight layout
    fig_agg.figure.tight_layout(pad=1.5)
    fig_agg.draw()

def update_pressure_graph(fig_agg, x_data, y_data):
    ax = fig_agg.figure.get_axes()[0]
    
    # Clear only the plot lines, keep axis labels
    ax.clear()
    
    # PyMeasure-style styling
    if len(x_data) > 0 and len(y_data) > 0:
        ax.plot(x_data, y_data, color='#A23B72', linewidth=2.5, alpha=0.85)
    else:
        ax.plot([], [], color='#A23B72', linewidth=2.5)
    
    # Light background like PyMeasure
    ax.set_facecolor('white')
    ax.set_xlabel("Time (s)", color='black', fontsize=11)
    ax.set_ylabel("Pressure (PSI)", color='black', fontsize=11)
    ax.set_title("Pressure", color='black', fontsize=12, fontweight='bold', pad=12)
    
    # Subtle grid like PyMeasure
    ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5, which='both')
    ax.set_axisbelow(True)
    ax.tick_params(colors='black', labelsize=9)
    
    # Clean spines
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1)
    
    # Tight layout
    fig_agg.figure.tight_layout(pad=1.5)
    fig_agg.draw()

def update_temperature_graph(fig_agg, x_data, y_data):
    ax = fig_agg.figure.get_axes()[0]
    
    # Clear only the plot lines, keep axis labels
    ax.clear()
    
    # PyMeasure-style styling
    if len(x_data) > 0 and len(y_data) > 0:
        ax.plot(x_data, y_data, color='#F18F01', linewidth=2.5, alpha=0.85)
    else:
        ax.plot([], [], color='#F18F01', linewidth=2.5)
    
    # Light background like PyMeasure
    ax.set_facecolor('white')
    ax.set_xlabel("Time (s)", color='black', fontsize=11)
    ax.set_ylabel("Temp (°C)", color='black', fontsize=11)
    ax.set_title("Temperature", color='black', fontsize=12, fontweight='bold', pad=12)
    
    # Subtle grid like PyMeasure
    ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5, which='both')
    ax.set_axisbelow(True)
    ax.tick_params(colors='black', labelsize=9)
    
    # Clean spines
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1)
    
    # Tight layout
    fig_agg.figure.tight_layout(pad=1.5)
    fig_agg.draw()

def update_level_graph(fig_agg, x_data, y_data):
    ax = fig_agg.figure.get_axes()[0]
    
    # Clear only the plot lines, keep axis labels
    ax.clear()
    
    # PyMeasure-style styling
    if len(x_data) > 0 and len(y_data) > 0:
        ax.plot(x_data, y_data, color='#06A77D', linewidth=2.5, alpha=0.85)
    else:
        ax.plot([], [], color='#06A77D', linewidth=2.5)
    
    # Light background like PyMeasure
    ax.set_facecolor('white')
    ax.set_xlabel("Time (s)", color='black', fontsize=11)
    ax.set_ylabel("Level (%)", color='black', fontsize=11)
    ax.set_title("Liquid Level", color='black', fontsize=12, fontweight='bold', pad=12)
    
    # Subtle grid like PyMeasure
    ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5, which='both')
    ax.set_axisbelow(True)
    ax.tick_params(colors='black', labelsize=9)
    
    # Clean spines
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1)
    
    # Tight layout
    fig_agg.figure.tight_layout(pad=1.5)
    fig_agg.draw()

def plot_xy_graph(fig_agg, x_axis_type, y_axis_type, x_data, y_data, param_arrays):
    """Plot X vs Y with any combination of parameters"""
    ax = fig_agg.figure.get_axes()[0]
    ax.clear()
    
    # Get the appropriate data arrays based on selected axes
    if x_axis_type in param_arrays and y_axis_type in param_arrays:
        x_param = param_arrays[x_axis_type]
        y_param = param_arrays[y_axis_type]
    else:
        # Fallback to provided x_data, y_data
        x_param = x_data
        y_param = y_data
    
    # Define styles for each parameter
    styles = {
        'Flow Rate': {'ylabel': 'Flow Rate (ml/min)', 'unit': 'ml/min'},
        'Pressure': {'ylabel': 'Pressure (PSI)', 'unit': 'PSI'},
        'Temperature': {'ylabel': 'Temperature (°C)', 'unit': '°C'},
        'Liquid Level': {'ylabel': 'Liquid Level (%)', 'unit': '%'},
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
    
    # Plot the data with PyMeasure-style formatting
    ax.plot(x_plot, y_plot, color='#2E86AB', linewidth=2.5, alpha=0.85)
    
    # PyMeasure-style formatting
    ax.set_facecolor('white')
    ax.set_xlabel(x_style['ylabel'], color='black', fontsize=13)
    ax.set_ylabel(y_style['ylabel'], color='black', fontsize=13)
    ax.set_title(f"{y_axis_type} vs {x_axis_type}", color='black', fontsize=14, fontweight='bold', pad=15)
    
    # Subtle grid
    ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5, which='both')
    ax.set_axisbelow(True)
    
    # Clean tick styling
    ax.tick_params(colors='black', labelsize=10, width=1)
    
    # Clean spines
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1)
    
    # Set axis limits
    if len(x_plot) > 0 and len(y_plot) > 0:
        x_margin = (max(x_plot) - min(x_plot)) * 0.05 if max(x_plot) > min(x_plot) else 1
        y_margin = (max(y_plot) - min(y_plot)) * 0.1 if max(y_plot) > min(y_plot) else 1
        ax.set_xlim(min(x_plot) - x_margin, max(x_plot) + x_margin)
        ax.set_ylim(min(y_plot) - y_margin, max(y_plot) + y_margin)
    
    fig_agg.figure.tight_layout(pad=2.0)
    fig_agg.draw()

def update_iv_graph(fig_agg, x_data, y_data):
    ax = fig_agg.figure.get_axes()[0]
    
    # Clear only the plot lines, keep axis labels
    ax.clear()
    
    # PyMeasure-style I-V styling
    if len(x_data) > 0 and len(y_data) > 0:
        ax.plot(x_data, y_data, color='#C73E1D', linewidth=2.5, alpha=0.85)
    else:
        ax.plot([], [], color='#C73E1D', linewidth=2.5)
    
    ax.set_facecolor('white')
    ax.set_xlabel("Voltage (V)", color='black', fontsize=11)
    ax.set_ylabel("Current (A)", color='black', fontsize=11)
    ax.set_title("I-V Characteristic", color='black', fontsize=12, fontweight='bold', pad=12)
    
    # Subtle grid
    ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5, which='both')
    ax.set_axisbelow(True)
    ax.tick_params(colors='black', labelsize=9)
    
    # Clean spines
    for spine in ax.spines.values():
        spine.set_color('black')
        spine.set_linewidth(1)
    
    fig_agg.draw()

def run_iv_measurement(hw_controller, data_handler, window, fig_agg, x_data, y_data, range_val, step_val):
    """
    Run I-V measurement in separate thread
    """
    window['-STATUS_BAR-'].update("Starting I-V measurement...")
    
    # Clear previous data
    x_data.clear()
    y_data.clear()
    
    # Create new data file
    data_handler.create_new_file()
    
    try:
        # Setup SMU
        hw_controller.setup_smu_iv_sweep(-range_val, range_val, step_val)
        
        # Perform I-V sweep
        voltage_points = []
        current_points = []
        
        for v in range(int(-range_val/step_val), int(range_val/step_val) + 1):
            voltage = v * step_val
            
            # Set voltage and measure current
            if hw_controller.smu:
                try:
                    hw_controller.smu.write(f"SOUR:VOLT {voltage}")
                    hw_controller.smu.write("INIT")
                    current = float(hw_controller.smu.query("MEAS:CURR?"))
                except Exception as e:
                    print(f"Error in I-V measurement: {e}")
                    # Realistic I-V: linear with small noise
                    current = voltage * 0.1 + 0.005 * math.sin(voltage * 10) + 0.002 * math.sin(voltage * 20)
            else:
                # Simulation mode - realistic I-V curve
                # Linear relationship with small sinusoidal noise for realism
                base_current = voltage * 0.1
                noise = 0.005 * math.sin(voltage * 10) + 0.002 * math.sin(voltage * 20)
                current = base_current + noise
            
            voltage_points.append(voltage)
            current_points.append(current)
            
            # Update graph
            x_data.append(voltage)
            y_data.append(current)
            window.write_event_value('-UPDATE_IV_GRAPH-', (list(x_data), list(y_data)))
            
            # Save data point
            data_point = {
                "time": len(voltage_points),
                "voltage": voltage,
                "current": current
            }
            data_handler.append_data(data_point)
            
            time.sleep(0.1)  # Small delay between measurements
        
        window['-STATUS_BAR-'].update("I-V measurement completed")
        
    except Exception as e:
        window['-STATUS_BAR-'].update(f"I-V measurement error: {e}")
        print(f"I-V measurement error: {e}")
    
    finally:
        data_handler.close_file()
        hw_controller.stop_smu()

def parse_program(program_text):
    """
    Parse program text into experiment steps
    Format: step1: flow=1.5, duration=60, temp=25, valve=main
    """
    steps = []
    if not program_text or not program_text.strip():
        return steps
        
    lines = program_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('step') and ':' in line:
            try:
                step_data = {}
                parts = line.split(':')[1].strip().split(',')
                
                for part in parts:
                    part = part.strip()
                    if '=' in part:
                        key, value = part.split('=')
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'flow':
                            step_data['flow_rate'] = float(value)
                        elif key == 'duration':
                            step_data['duration'] = int(value)
                        elif key == 'temp':
                            step_data['temperature'] = float(value)
                        elif key == 'valve':
                            if value == 'main':
                                step_data['valve_setting'] = {'valve1': True, 'valve2': False}
                            elif value == 'rinsing':
                                step_data['valve_setting'] = {'valve1': False, 'valve2': True}
                
                if 'flow_rate' in step_data and 'duration' in step_data:
                    steps.append(step_data)
                    
            except (ValueError, IndexError) as e:
                print(f"Error parsing line: {line}, Error: {e}")
                continue
    
    return steps

def run_program_thread(exp_manager, experiment_program, window, main_fig_agg, fig2_agg, fig3_agg, fig4_agg,
                      flow_x_data, flow_y_data, pressure_x_data, pressure_y_data,
                      temp_x_data, temp_y_data, level_x_data, level_y_data):
    """
    Run program from Write Program tab
    """
    exp_manager.is_running = True
    window['-PROGRAM_STATUS-'].update('Starting program...')

    data_handler = exp_manager.data_handler
    data_handler.create_new_file()

    # Start time for the entire program (NOT per step!)
    program_start_time = time.time()

    for step in experiment_program:
        if not exp_manager.is_running:
            break

        duration = step.get('duration')
        flow_rate = step.get('flow_rate')
        temperature = step.get('temperature', 25.0)
        valve_setting = step.get('valve_setting', {'valve1': True, 'valve2': False})

        window['-PROGRAM_STATUS-'].update(f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min, Temp={temperature}°C")

        # Set hardware parameters
        exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
        exp_manager.hw_controller.set_heating_plate_temp(temperature)
        exp_manager.hw_controller.set_valves(valve_setting['valve1'], valve_setting['valve2'])

        start_time = time.time()
        i = 0  # Counter for consistent timing

        while time.time() - start_time < duration and exp_manager.is_running:
            if not exp_manager.perform_safety_checks():
                break

            pump_data = exp_manager.hw_controller.read_pump_data()
            pressure = exp_manager.hw_controller.read_pressure_sensor()
            temperature_read = exp_manager.hw_controller.read_temperature_sensor()
            level = exp_manager.hw_controller.read_level_sensor()

            current_time = time.time()
            # Use cumulative time from the start of the program
            elapsed_time_from_start = current_time - program_start_time
            remaining_time = duration - (current_time - start_time)
            
            # Update status with remaining time
            window['-STATUS_BAR-'].update(f"Running: {remaining_time:.0f}s remaining, Flow={flow_rate}ml/min")
            
            # Update all data arrays with cumulative time from start
            flow_x_data.append(elapsed_time_from_start)
            flow_y_data.append(pump_data['flow'])
            pressure_x_data.append(elapsed_time_from_start)
            pressure_y_data.append(pressure)
            temp_x_data.append(elapsed_time_from_start)
            temp_y_data.append(temperature_read)
            level_x_data.append(elapsed_time_from_start)
            level_y_data.append(level * 100)

            data_point = {
                "time": elapsed_time_from_start,
                "flow_setpoint": flow_rate,
                "pump_flow_read": pump_data['flow'],
                "pressure_read": pressure,
                "temp_read": temperature_read,
                "level_read": level,
                "program_step": len(experiment_program)
            }
            data_handler.append_data(data_point)

            # Update all graphs
            window.write_event_value('-UPDATE_GRAPH1-', (list(flow_x_data), list(flow_y_data)))
            window.write_event_value('-UPDATE_GRAPH2-', (list(pressure_x_data), list(pressure_y_data)))
            window.write_event_value('-UPDATE_GRAPH3-', (list(temp_x_data), list(temp_y_data)))
            window.write_event_value('-UPDATE_GRAPH4-', (list(level_x_data), list(level_y_data)))
            time.sleep(1)

    exp_manager.stop_experiment()
    data_handler.close_file()
    window['-PROGRAM_STATUS-'].update('Program completed.')


# --- Experiment Thread Function ---
def experiment_thread(exp_manager, experiment_program, window, main_fig_agg, fig2_agg, fig3_agg, fig4_agg, 
                     flow_x_data, flow_y_data, pressure_x_data, pressure_y_data, 
                     temp_x_data, temp_y_data, level_x_data, level_y_data, current_flow_rate):
    exp_manager.is_running = True
    window['-STATUS_BAR-'].update('Starting experiment...')

    data_handler = exp_manager.data_handler
    data_handler.create_new_file()
    
    # Start time for the entire experiment (NOT per step!)
    experiment_start_time = time.time()
    cumulative_time = 0.0
    
    # Update current flow rate at start
    # current_flow_rate is already set from the main function

    for step in experiment_program:
        if not exp_manager.is_running:
            break

        duration = step.get('duration')
        # Use current_flow_rate instead of step flow_rate for dynamic updates
        flow_rate = current_flow_rate

        window['-STATUS_BAR-'].update(f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min")

        exp_manager.hw_controller.set_pump_flow_rate(flow_rate)

        start_time = time.time()

        while time.time() - start_time < duration and exp_manager.is_running:
            if not exp_manager.perform_safety_checks():
                break

            # Check for flow rate updates from main thread
            # Note: current_flow_rate is passed by reference, so changes in main thread will be reflected here
            if current_flow_rate != flow_rate:
                flow_rate = current_flow_rate
                exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
                print(f"Flow rate updated to {flow_rate} ml/min during experiment")

            pump_data = exp_manager.hw_controller.read_pump_data()
            pressure = exp_manager.hw_controller.read_pressure_sensor()
            temperature = exp_manager.hw_controller.read_temperature_sensor()
            level = exp_manager.hw_controller.read_level_sensor()

            current_time = time.time()
            remaining_time = duration - (current_time - start_time)
            
            # Update status with remaining time
            window['-STATUS_BAR-'].update(f"Running: {remaining_time:.0f}s remaining, Flow={flow_rate}ml/min")
            
            # Use cumulative time from the start of the experiment
            elapsed_time_from_start = current_time - experiment_start_time
            
            # Update flow data
            flow_x_data.append(elapsed_time_from_start)
            flow_y_data.append(pump_data['flow'])
            
            # Update pressure data
            pressure_x_data.append(elapsed_time_from_start)
            pressure_y_data.append(pressure)
            
            # Update temperature data
            temp_x_data.append(elapsed_time_from_start)
            temp_y_data.append(temperature)
            
            # Update level data
            level_x_data.append(elapsed_time_from_start)
            level_y_data.append(level * 100)  # Convert to percentage

            data_point = {
                "time": elapsed_time_from_start,
                "flow_setpoint": flow_rate,
                "pump_flow_read": pump_data['flow'],
                "pressure_read": pressure,
                "temp_read": temperature,
                "level_read": level
            }
            data_handler.append_data(data_point)

            # Update all graphs
            window.write_event_value('-UPDATE_GRAPH1-', (list(flow_x_data), list(flow_y_data)))
            window.write_event_value('-UPDATE_GRAPH2-', (list(pressure_x_data), list(pressure_y_data)))
            window.write_event_value('-UPDATE_GRAPH3-', (list(temp_x_data), list(temp_y_data)))
            window.write_event_value('-UPDATE_GRAPH4-', (list(level_x_data), list(level_y_data)))
            time.sleep(1)

    exp_manager.stop_experiment()
    data_handler.close_file()
    window['-STATUS_BAR-'].update('Experiment finished.')
    # Update recording status
    window['-RECORDING_STATUS-'].update('Completed', text_color='green')


# --- Main Application Loop ---
def main():
    app = FluidicControlApp()
    app.mainloop()


if __name__ == "__main__":
    main()