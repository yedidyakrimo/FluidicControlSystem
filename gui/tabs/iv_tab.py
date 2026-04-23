"""
IV Tab - I-V measurement and characterization
"""

import customtkinter as ctk
from tkinter import PanedWindow, Frame, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import threading
import time
import os

from gui.tabs.base_tab import BaseTab


class IVTab(BaseTab):
    """
    IV tab for I-V measurement and characterization
    """
    
    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None):
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        
        # IV-specific data arrays
        self.iv_x_data, self.iv_y_data = [], []
        self.iv_time_x_data, self.iv_time_v_data, self.iv_time_i_data = [], [], []
        self.iv_measurement_start_time = None
        self.iv_measurement_stop = False  # Flag to stop measurement
        self.iv_auto_scale_enabled = True  # Default: auto-scale ON for IV graph
        self.iv_output_enabled = False
        
        # Temperature sensor channel (ai1 is already used for temperature in hardware_controller)
        self.temp_sensor_channel = 'ai1'  # Using ai1 which is the temperature sensor channel
        
        # Rate limiting for error messages (print only every 10 seconds)
        self.last_temp_error_print_time = {}
        
        # Create widgets
        self.create_widgets()
        
        # Setup graphs
        self.setup_graphs()
        
        # Refresh MCusb status on startup
        self.after(1000, self.refresh_mcusb_status)
        
        # Start periodic update of MCusb readings (every 100ms for real-time)
        self.update_mcusb_readings()
    
    def create_widgets(self):
        """Create IV tab widgets"""
        # Create PanedWindow for resizable panels
        paned = PanedWindow(self, orient='horizontal', sashwidth=8, sashrelief='raised', bg='#2b2b2b')
        paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left column container
        left_container = Frame(paned, bg='#1a1a1a')
        paned.add(left_container, minsize=250, width=400)
        
        # Left column - Scrollable
        left_frame = ctk.CTkScrollableFrame(left_container, width=400)
        left_frame.pack(fill='both', expand=True)
        
        # Top of IV tab now starts with experiment configuration/controls.
        # Hardware status/control panels are moved to the bottom by request.
        output_top_frame = ctk.CTkFrame(left_frame)
        output_top_frame.pack(fill='x', pady=5)
        self.iv_output_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            output_top_frame,
            text="Enable SMU Output",
            variable=self.iv_output_var,
            command=self.on_iv_output_toggle
        ).pack(side='left', padx=8, pady=6)
        
        # I-V Parameters
        params_frame = ctk.CTkFrame(left_frame)
        params_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(params_frame, text="I-V Parameters", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        params_grid = ctk.CTkFrame(params_frame)
        params_grid.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(params_grid, text='Start (V):', width=120).grid(row=0, column=0, padx=5, pady=2)
        self.iv_start_entry = ctk.CTkEntry(params_grid, width=150)
        self.iv_start_entry.insert(0, '-2.0')
        self.iv_start_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='Stop (V):', width=120).grid(row=1, column=0, padx=5, pady=2)
        self.iv_stop_entry = ctk.CTkEntry(params_grid, width=150)
        self.iv_stop_entry.insert(0, '2.0')
        self.iv_stop_entry.grid(row=1, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='Step (V):', width=120).grid(row=2, column=0, padx=5, pady=2)
        self.iv_step_entry = ctk.CTkEntry(params_grid, width=150)
        self.iv_step_entry.insert(0, '0.1')
        self.iv_step_entry.grid(row=2, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='Step Duration (min):', width=120).grid(row=3, column=0, padx=5, pady=2)
        self.iv_time_entry = ctk.CTkEntry(params_grid, width=150)
        self.iv_time_entry.insert(0, '1.0')
        self.iv_time_entry.grid(row=3, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_grid, text='Flow rate (ml/min):', width=120).grid(row=4, column=0, padx=5, pady=2)
        self.iv_flow_entry = ctk.CTkEntry(params_grid, width=150)
        self.iv_flow_entry.insert(0, '1.5')
        self.iv_flow_entry.grid(row=4, column=1, padx=5, pady=2)
        ctk.CTkLabel(params_grid, text='(Max: 5.0)', width=80, font=('Helvetica', 9), text_color='gray').grid(row=4, column=2, padx=2, pady=2)
        
        # Sync flow rate entries
        self.iv_flow_entry.bind('<FocusOut>', self.iv_sync_flow_entries)
        self.iv_flow_entry.bind('<Return>', self.iv_sync_flow_entries)
        if hasattr(self, 'iv_flow_rate_entry'):
            self.iv_flow_rate_entry.bind('<FocusOut>', self.iv_sync_flow_entries)
            self.iv_flow_rate_entry.bind('<Return>', self.iv_sync_flow_entries)
        
        ctk.CTkLabel(params_grid, text='Valve setting:', width=120).grid(row=5, column=0, padx=5, pady=2)
        self.iv_valve_var = ctk.StringVar(value="main")
        valve_btn_frame = ctk.CTkFrame(params_grid)
        valve_btn_frame.grid(row=5, column=1, padx=5, pady=2)
        ctk.CTkRadioButton(valve_btn_frame, text="Main", variable=self.iv_valve_var, value="main").pack(side='left', padx=5)
        ctk.CTkRadioButton(valve_btn_frame, text="Rinsing", variable=self.iv_valve_var, value="rinsing").pack(side='left', padx=5)
        
        # Quick Control
        quick_frame = ctk.CTkFrame(left_frame)
        quick_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(quick_frame, text="Quick Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        btn_frame = ctk.CTkFrame(quick_frame)
        btn_frame.pack(pady=5)
        self.create_blue_button(btn_frame, text='Direct setting', command=self.iv_direct_set, width=150, height=35).pack(pady=2)
        self.create_blue_button(btn_frame, text='Direct run', command=self.iv_direct_run, width=150, height=35).pack(pady=2)
        self.iv_stop_button = self.create_blue_button(btn_frame, text='Stop Measurement', command=self.iv_stop_measurement, width=150, height=35,
                                                     fg_color='#0D47A1', hover_color='#0C3A7A', state='disabled')
        self.iv_stop_button.pack(pady=2)
        
        # Program Control
        prog_frame = ctk.CTkFrame(left_frame)
        prog_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(prog_frame, text="Program Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        prog_btn_frame = ctk.CTkFrame(prog_frame)
        prog_btn_frame.pack(pady=5)
        self.create_blue_button(prog_btn_frame, text='Choose program', command=self.iv_choose_program, width=150).pack(pady=2)
        self.create_blue_button(prog_btn_frame, text='Run program', command=self.iv_run_program, width=150).pack(pady=2)
        
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
        self.create_blue_button(export_btn_frame, text='Save to file', command=self.iv_save_file, width=150).pack(pady=2)
        
        export_menu_frame = ctk.CTkFrame(export_frame)
        export_menu_frame.pack(pady=2)
        ctk.CTkLabel(export_menu_frame, text='Export:', width=80).pack(side='left', padx=5)
        self.create_blue_button(export_menu_frame, text='Excel', command=self.iv_export_excel, width=100).pack(side='left', padx=2)
        self.create_blue_button(export_menu_frame, text='PNG', command=self.iv_export_graph_png, width=100).pack(side='left', padx=2)
        self.create_blue_button(export_menu_frame, text='PDF', command=self.iv_export_graph_pdf, width=100).pack(side='left', padx=2)
        
        # ------------------------------------------------------------------
        # Bottom hardware blocks (moved here per requested order)
        # 1) Keithley 2450 SMU Status
        # 2) Vapourtec SF-10 Pump Status
        # 3) Quick SMU Control
        # 4) MCusb-1408FS-Plus DAQ Status
        # 5) Temperature Monitor
        # ------------------------------------------------------------------

        # 1. SMU Connection Status
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

        ctk.CTkLabel(smu_info_frame, text='Resource:', width=100).grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.smu_resource_label = ctk.CTkLabel(smu_info_frame, text='N/A', width=250, anchor='w', wraplength=250)
        self.smu_resource_label.grid(row=2, column=1, padx=5, pady=2, sticky='w')

        smu_btn_frame = ctk.CTkFrame(smu_status_frame)
        smu_btn_frame.pack(pady=5)
        self.create_blue_button(smu_btn_frame, text='🔍 Detect SMU', command=self.detect_smu, width=120, height=30).pack(side='left', padx=2)
        self.create_blue_button(smu_btn_frame, text='🔄 Refresh Status', command=self.refresh_smu_status, width=120, height=30).pack(side='left', padx=2)
        self.create_blue_button(smu_btn_frame, text='📋 List Devices', command=self.list_visa_devices, width=120, height=30).pack(side='left', padx=2)

        # 2. Pump status
        pump_status_frame = ctk.CTkFrame(left_frame)
        pump_status_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(pump_status_frame, text="Vapourtec SF-10 Pump Status",
                     font=('Helvetica', 14, 'bold')).pack(pady=5)

        pump_info_frame = ctk.CTkFrame(pump_status_frame)
        pump_info_frame.pack(fill='x', padx=5, pady=5)

        ctk.CTkLabel(pump_info_frame, text='Status:', width=100).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.iv_pump_status_label = ctk.CTkLabel(pump_info_frame, text='Checking...', width=250, anchor='w')
        self.iv_pump_status_label.grid(row=0, column=1, padx=5, pady=2, sticky='w')

        flow_quick_frame = ctk.CTkFrame(pump_status_frame)
        flow_quick_frame.pack(fill='x', padx=5, pady=5)
        ctk.CTkLabel(flow_quick_frame, text='Quick Flow Rate (ml/min):', width=150).pack(side='left', padx=5)
        self.iv_flow_rate_entry = ctk.CTkEntry(flow_quick_frame, width=100)
        self.iv_flow_rate_entry.insert(0, '1.5')
        self.iv_flow_rate_entry.pack(side='left', padx=5)
        self.iv_update_flow_btn = self.create_blue_button(flow_quick_frame, text='Update Flow',
                                                          command=self.iv_update_flow, width=100)
        self.iv_update_flow_btn.pack(side='left', padx=2)
        # Bind sync events now that both entries exist
        self.iv_flow_rate_entry.bind('<FocusOut>', self.iv_sync_flow_entries)
        self.iv_flow_rate_entry.bind('<Return>', self.iv_sync_flow_entries)

        pump_btn_frame = ctk.CTkFrame(pump_status_frame)
        pump_btn_frame.pack(pady=5)
        self.create_blue_button(pump_btn_frame, text='🔄 Refresh Status',
                                command=self.iv_refresh_pump_status, width=120, height=30).pack(side='left', padx=2)
        self.after(1500, self.iv_refresh_pump_status)

        # 3. Quick SMU Control
        smu_control_frame = ctk.CTkFrame(left_frame)
        smu_control_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(smu_control_frame, text="Quick SMU Control", font=('Helvetica', 14, 'bold')).pack(pady=5)

        smu_control_grid = ctk.CTkFrame(smu_control_frame)
        smu_control_grid.pack(fill='x', padx=5, pady=5)

        ctk.CTkLabel(smu_control_grid, text='Set Voltage (V):', width=120).grid(row=0, column=0, padx=5, pady=2)
        self.smu_voltage_entry = ctk.CTkEntry(smu_control_grid, width=100)
        self.smu_voltage_entry.insert(0, '0.0')
        self.smu_voltage_entry.grid(row=0, column=1, padx=5, pady=2)

        ctk.CTkLabel(smu_control_grid, text='Current Limit (A):', width=120).grid(row=1, column=0, padx=5, pady=2)
        self.smu_current_limit_entry = ctk.CTkEntry(smu_control_grid, width=100)
        self.smu_current_limit_entry.insert(0, '0.1')
        self.smu_current_limit_entry.grid(row=1, column=1, padx=5, pady=2)

        smu_control_btn_frame = ctk.CTkFrame(smu_control_frame)
        smu_control_btn_frame.pack(pady=5)
        self.create_blue_button(smu_control_btn_frame, text='Set Voltage', command=self.set_smu_voltage_manual, width=100, height=30).pack(side='left', padx=2)
        self.create_blue_button(smu_control_btn_frame, text='Measure', command=self.measure_smu_manual, width=100, height=30).pack(side='left', padx=2)
        self.create_blue_button(smu_control_btn_frame, text='Output OFF', command=self.smu_output_off, width=100, height=30,
                                fg_color='#0D47A1', hover_color='#0C3A7A').pack(side='left', padx=2)

        # 4. MCusb status
        mcusb_status_frame = ctk.CTkFrame(left_frame)
        mcusb_status_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(mcusb_status_frame, text="MCusb-1408FS-Plus DAQ Status", font=('Helvetica', 14, 'bold')).pack(pady=5)

        mcusb_info_frame = ctk.CTkFrame(mcusb_status_frame)
        mcusb_info_frame.pack(fill='x', padx=5, pady=5)

        ctk.CTkLabel(mcusb_info_frame, text='Status:', width=100).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.mcusb_status_label = ctk.CTkLabel(mcusb_info_frame, text='Checking...', width=250, anchor='w')
        self.mcusb_status_label.grid(row=0, column=1, padx=5, pady=2, sticky='w')

        ctk.CTkLabel(mcusb_info_frame, text='Device:', width=100).grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.mcusb_device_label = ctk.CTkLabel(mcusb_info_frame, text='N/A', width=250, anchor='w')
        self.mcusb_device_label.grid(row=1, column=1, padx=5, pady=2, sticky='w')

        ctk.CTkLabel(mcusb_info_frame, text='Channel 0 (IN HI):', width=100).grid(row=2, column=0, padx=5, pady=2, sticky='w')
        self.mcusb_ch0_label = ctk.CTkLabel(mcusb_info_frame, text='N/A', width=250, anchor='w')
        self.mcusb_ch0_label.grid(row=2, column=1, padx=5, pady=2, sticky='w')

        mcusb_btn_frame = ctk.CTkFrame(mcusb_status_frame)
        mcusb_btn_frame.pack(pady=5)
        self.create_blue_button(mcusb_btn_frame, text='🔄 Refresh', command=self.refresh_mcusb_status, width=120, height=30).pack(side='left', padx=2)
        self.create_blue_button(mcusb_btn_frame, text='📊 Read Channels', command=self.read_mcusb_channels, width=120, height=30).pack(side='left', padx=2)

        # 5. Temperature monitor
        temp_monitor_frame = ctk.CTkFrame(left_frame)
        temp_monitor_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(temp_monitor_frame, text="Temperature Monitor", font=('Helvetica', 14, 'bold')).pack(pady=5)

        temp_info_frame = ctk.CTkFrame(temp_monitor_frame)
        temp_info_frame.pack(fill='x', padx=5, pady=5)

        ctk.CTkLabel(temp_info_frame, text='Temperature:', width=100).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.temp_display_label = ctk.CTkLabel(temp_info_frame, text='N/A', width=250, anchor='w', font=('Helvetica', 12, 'bold'))
        self.temp_display_label.grid(row=0, column=1, padx=5, pady=2, sticky='w')

        ctk.CTkLabel(temp_info_frame, text='Voltage (V):', width=100).grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.temp_voltage_label = ctk.CTkLabel(temp_info_frame, text='N/A', width=250, anchor='w')
        self.temp_voltage_label.grid(row=1, column=1, padx=5, pady=2, sticky='w')

        # Status bar
        self.iv_status_bar = ctk.CTkLabel(left_frame, text='', font=('Helvetica', 10))
        self.iv_status_bar.pack(pady=5)
        
        # Right column container
        right_container = Frame(paned, bg='#1a1a1a')
        paned.add(right_container, minsize=400)
        
        # Right column - IV Graph
        right_frame = ctk.CTkFrame(right_container)
        right_frame.pack(fill='both', expand=True)
        
        graph_control_frame = ctk.CTkFrame(right_frame)
        graph_control_frame.pack(fill='x', pady=5)
        ctk.CTkLabel(graph_control_frame, text="I-V Characteristic", font=('Helvetica', 14, 'bold')).pack(pady=5)

        auto_scale_frame = ctk.CTkFrame(graph_control_frame)
        auto_scale_frame.pack(fill='x', padx=5, pady=2)
        ctk.CTkLabel(auto_scale_frame, text='Zoom Control:', width=80).pack(side='left', padx=5)
        self.iv_auto_scale_btn = self.create_blue_button(
            auto_scale_frame,
            text='🔓 Auto-Scale ON',
            command=self.toggle_iv_auto_scale,
            width=150,
            height=30
        )
        self.iv_auto_scale_btn.pack(side='left', padx=2)
        
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
    
    def setup_graphs(self):
        """Initialize IV graph"""
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
    
    # --- Utility Functions ---
    def get_si_unit_label(self, value, unit_type='voltage'):
        """Get appropriate SI unit label based on value magnitude"""
        abs_value = abs(value) if value != 0 else 1e-9
        
        if unit_type == 'voltage':
            if abs_value >= 1e3:
                return ('kV', 1e-3)
            elif abs_value >= 1:
                return ('V', 1)
            elif abs_value >= 1e-3:
                return ('mV', 1e3)
            elif abs_value >= 1e-6:
                return ('µV', 1e6)
            elif abs_value >= 1e-9:
                return ('nV', 1e9)
            else:
                return ('pV', 1e12)
        else:  # current
            if abs_value >= 1:
                return ('A', 1)
            elif abs_value >= 1e-3:
                return ('mA', 1e3)
            elif abs_value >= 1e-6:
                return ('µA', 1e6)
            elif abs_value >= 1e-9:
                return ('nA', 1e9)
            else:
                return ('pA', 1e12)
    
    def get_axis_unit_label(self, data, unit_type='voltage'):
        """Get appropriate SI unit label based on data range"""
        if not data or len(data) == 0:
            return ('V', 1) if unit_type == 'voltage' else ('A', 1)
        
        max_abs = max(abs(min(data)), abs(max(data))) if data else 1e-9
        return self.get_si_unit_label(max_abs, unit_type)
    
    def format_value_with_unit(self, value, unit_type='voltage'):
        """Format a single value with appropriate SI unit"""
        if value == float('inf') or value == float('-inf'):
            return "∞"
        
        if unit_type == 'resistance':
            abs_value = abs(value) if value != 0 else 1e-9
            if abs_value >= 1e6:
                return f"{value * 1e-6:.2f} MΩ"
            elif abs_value >= 1e3:
                return f"{value * 1e-3:.2f} kΩ"
            elif abs_value >= 1:
                return f"{value:.2f} Ω"
            elif abs_value >= 1e-3:
                return f"{value * 1e3:.2f} mΩ"
            else:
                return f"{value:.2e} Ω"
        else:
            unit, scale = self.get_si_unit_label(value, unit_type)
            scaled_value = value * scale
            if abs(scaled_value) >= 100:
                return f"{scaled_value:.1f} {unit}"
            elif abs(scaled_value) >= 10:
                return f"{scaled_value:.2f} {unit}"
            elif abs(scaled_value) >= 1:
                return f"{scaled_value:.3f} {unit}"
            else:
                return f"{scaled_value:.4f} {unit}"
    
    def format_range_with_unit(self, min_val, max_val, unit_type='voltage'):
        """Format a range (min to max) with appropriate SI unit"""
        max_abs = max(abs(min_val), abs(max_val)) if min_val != 0 or max_val != 0 else 1e-9
        
        if unit_type == 'resistance':
            if max_abs >= 1e6:
                return f"{min_val * 1e-6:.2f} to {max_val * 1e-6:.2f} MΩ"
            elif max_abs >= 1e3:
                return f"{min_val * 1e-3:.2f} to {max_val * 1e-3:.2f} kΩ"
            elif max_abs >= 1:
                return f"{min_val:.2f} to {max_val:.2f} Ω"
            elif max_abs >= 1e-3:
                return f"{min_val * 1e3:.2f} to {max_val * 1e3:.2f} mΩ"
            else:
                return f"{min_val:.2e} to {max_val:.2e} Ω"
        else:
            unit, scale = self.get_si_unit_label(max_abs, unit_type)
            min_scaled = min_val * scale
            max_scaled = max_val * scale
            if abs(max_scaled) >= 100:
                return f"{min_scaled:.1f} to {max_scaled:.1f} {unit}"
            elif abs(max_scaled) >= 10:
                return f"{min_scaled:.2f} to {max_scaled:.2f} {unit}"
            elif abs(max_scaled) >= 1:
                return f"{min_scaled:.3f} to {max_scaled:.3f} {unit}"
            else:
                return f"{min_scaled:.4f} to {max_scaled:.4f} {unit}"
    
    # --- SMU Control Functions ---
    def detect_smu(self):
        """Detect and connect to Keithley 2450 SMU automatically (with threading)"""
        print("DEBUG: Detect SMU button clicked")
        
        # 1. Update UI immediately (Main Thread)
        self.smu_status_label.configure(text="Scanning for devices...", text_color='orange')
        
        # 2. Run logic in background thread
        threading.Thread(target=self._run_detect_smu_logic, daemon=True).start()
    
    def _run_detect_smu_logic(self):
        """Background thread for SMU detection"""
        try:
            # Heavy VISA operations here (this can take several seconds)
            detected_smu = self.hw_controller.auto_detect_smu()
            
            # 3. Schedule UI update back on Main Thread
            if detected_smu:
                if self.hw_controller.smu:
                    try:
                        self.hw_controller.smu.close()
                    except:
                        pass
                self.hw_controller.smu = detected_smu
                self.after(0, lambda: messagebox.showinfo('Success', 
                    f'Keithley 2450 SMU detected and connected!\nResource: {detected_smu.resource_name}'))
                self.after(0, self.refresh_smu_status)
            else:
                self.after(0, lambda: messagebox.showwarning('Not Found', 
                    'Keithley 2450 SMU not found. Please check:\n1. Device is powered on\n2. USB cable is connected\n3. VISA drivers are installed'))
                self.after(0, lambda: self.smu_status_label.configure(text='✗ Not Connected', text_color='red'))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: messagebox.showerror('Error', f'Error detecting SMU: {error_msg}'))
            self.after(0, lambda: self.smu_status_label.configure(text='✗ Not Connected', text_color='red'))
    
    def refresh_smu_status(self):
        """Refresh SMU connection status display (with threading)"""
        print("DEBUG: Refresh SMU button clicked")
        
        # 1. Update UI immediately (Main Thread)
        self.smu_status_label.configure(text="Checking...", text_color='orange')
        
        # 2. Run logic in background thread
        threading.Thread(target=self._run_refresh_smu_logic, daemon=True).start()
    
    def _run_refresh_smu_logic(self):
        """Background thread for SMU status refresh with re-initialization"""
        try:
            # Step A: Check if software object exists
            # Step B: Active Health Check (performed in get_smu_info())
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
            
            # 3. Schedule UI update back on Main Thread
            self.after(0, lambda: self._update_smu_ui(smu_info))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._update_smu_error(error_msg))
    
    def _update_smu_ui(self, smu_info):
        """Update SMU UI with results (called on main thread)"""
        try:
            if smu_info.get('connected', False):
                self.smu_status_label.configure(text='✓ Connected', text_color='green')
                self.smu_idn_label.configure(text=smu_info.get('idn', 'N/A'))
                self.smu_resource_label.configure(text=smu_info.get('resource', 'N/A'))
            else:
                self.smu_status_label.configure(text='✗ Not Connected', text_color='red')
                self.smu_idn_label.configure(text='N/A')
                self.smu_resource_label.configure(text='N/A')
        except Exception as e:
            self.smu_status_label.configure(text=f'Error: {str(e)[:30]}', text_color='orange')
    
    def _update_smu_error(self, error_msg):
        """Update SMU UI with error (called on main thread)"""
        self.smu_status_label.configure(text=f'Error: {error_msg[:30]}', text_color='orange')
    
    def refresh_mcusb_status(self):
        """Refresh MCusb-1408FS-Plus connection status display (with threading)"""
        print("DEBUG: Refresh MCusb button clicked")
        
        # 1. Update UI immediately (Main Thread)
        self.mcusb_status_label.configure(text="Checking...", text_color='orange')
        
        # 2. Run logic in background thread
        threading.Thread(target=self._run_refresh_mcusb_logic, daemon=True).start()
    
    def _run_refresh_mcusb_logic(self):
        """Background thread for MCusb status refresh"""
        try:
            # Check connection status
            is_connected = (self.hw_controller.ni_daq and 
                           self.hw_controller.ni_daq.is_connected())
            device_name = self.hw_controller.ni_device_name if is_connected else 'N/A'
            
            # 3. Schedule UI update back on Main Thread
            self.after(0, lambda: self._update_mcusb_ui(is_connected, device_name))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: self._update_mcusb_error(error_msg))
    
    def _update_mcusb_ui(self, is_connected, device_name):
        """Update MCusb UI with results (called on main thread)"""
        try:
            if is_connected:
                self.mcusb_status_label.configure(text='Connected', text_color='green')
                self.mcusb_device_label.configure(text=device_name)
                # Read channels (this is quick, can stay on main thread)
                self.read_mcusb_channels()
            else:
                self.mcusb_status_label.configure(text='Not Connected', text_color='red')
                self.mcusb_device_label.configure(text='N/A')
                self.mcusb_ch0_label.configure(text='N/A')
        except Exception as e:
            self.mcusb_status_label.configure(text=f'Error: {str(e)[:30]}', text_color='orange')
    
    def _update_mcusb_error(self, error_msg):
        """Update MCusb UI with error (called on main thread)"""
        self.mcusb_status_label.configure(text=f'Error: {error_msg[:30]}', text_color='orange')
    
    def read_mcusb_channels(self):
        """Read voltage from MCusb-1408FS-Plus channels"""
        try:
            if not self.hw_controller.ni_daq or not self.hw_controller.ni_daq.is_connected():
                messagebox.showwarning('Not Connected', 'MCusb-1408FS-Plus is not connected.')
                return
            
            # Read Channel 0 (IN HI) - try differential first (if IN HI and IN LO are on CH0)
            # If that doesn't work, fall back to single-ended
            voltage_ch0 = self.hw_controller.ni_daq.read_analog_input('ai0', differential=True)
            if voltage_ch0 is None:
                # Fall back to single-ended if differential fails
                voltage_ch0 = self.hw_controller.ni_daq.read_analog_input('ai0', differential=False)
            
            if voltage_ch0 is not None:
                self.mcusb_ch0_label.configure(text=f'{voltage_ch0:.4f} V', text_color='green')
            else:
                self.mcusb_ch0_label.configure(text='Error reading', text_color='red')
                
        except Exception as e:
            messagebox.showerror('Error', f'Error reading MCusb channels: {e}')
    
    def _should_print_temp_error(self, error_key, interval_seconds=10):
        """
        Check if enough time has passed since last error print
        
        Args:
            error_key: Unique key for this error type
            interval_seconds: Minimum seconds between prints (default 10)
        
        Returns:
            True if should print, False otherwise
        """
        import time
        current_time = time.time()
        if error_key not in self.last_temp_error_print_time:
            self.last_temp_error_print_time[error_key] = current_time
            return True
        
        if current_time - self.last_temp_error_print_time[error_key] >= interval_seconds:
            self.last_temp_error_print_time[error_key] = current_time
            return True
        
        return False
    
    def read_temperature_sensor(self):
        """
        Read temperature from 4-20mA temperature transmitter via MCusb-1408FS-Plus
        Uses 556 Ohm shunt resistor to convert current to voltage
        
        Hardware:
        - Sensor Range: 0°C to 150°C
        - Current Output: 4mA (at 0°C) to 20mA (at 150°C)
        - Shunt Resistor: 556 Ohms
        - Input: Voltage across shunt resistor
        
        Formula:
        1. Current (mA) = Voltage / 556 * 1000
        2. Temperature (°C) = (Current_mA - 4) * (150 / 16)
        """
        try:
            if not self.hw_controller.ni_daq or not self.hw_controller.ni_daq.is_connected():
                return None, None
            
            # Read voltage from temperature sensor channel (ai1)
            voltage = self.hw_controller.ni_daq.read_analog_input(self.temp_sensor_channel, differential=False)
            
            if voltage is None:
                return None, None
            
            # Use the temperature sensor's calibration function
            if hasattr(self.hw_controller, 'temperature_sensor') and hasattr(self.hw_controller.temperature_sensor, 'calculate_temperature_from_voltage'):
                temperature = self.hw_controller.temperature_sensor.calculate_temperature_from_voltage(voltage)
            else:
                # Fallback: Direct calculation using exact formula
                # Step 1: Calculate Current (mA)
                # Formula: current_mA = (voltage / 556.0) * 1000.0
                current_mA = (voltage / 556.0) * 1000.0
                
                # Step 2: Check for disconnected sensor
                if current_mA < 3.5:
                    if self._should_print_temp_error("sensor_disconnected"):
                        print(f"Warning: Temperature sensor appears disconnected. Current: {current_mA:.3f}mA")
                    return voltage, None
                
                # Step 3: Calculate Temperature (°C)
                # Formula: temp_c = (current_mA - 4.0) * (150.0 / 16.0)
                temp_c = (current_mA - 4.0) * (150.0 / 16.0)
                
                # Clamp temperature to valid range (0-150°C)
                temperature = max(0.0, min(150.0, temp_c))
            
            return voltage, temperature
        except Exception as e:
            if self._should_print_temp_error("read_exception"):
                print(f"Error reading temperature sensor: {e}")
            return None, None
    
    def update_mcusb_readings(self):
        """Periodically update MCusb channel readings and temperature in real-time"""
        try:
            if self.hw_controller.ni_daq and self.hw_controller.ni_daq.is_connected():
                # Read Channel 0 (IN HI) - try differential first (if IN HI and IN LO are on CH0)
                # If that doesn't work, fall back to single-ended
                voltage_ch0 = self.hw_controller.ni_daq.read_analog_input('ai0', differential=True)
                if voltage_ch0 is None:
                    # Fall back to single-ended if differential fails
                    voltage_ch0 = self.hw_controller.ni_daq.read_analog_input('ai0', differential=False)
                
                if voltage_ch0 is not None:
                    self.mcusb_ch0_label.configure(text=f'{voltage_ch0:.4f} V', text_color='green')
                else:
                    self.mcusb_ch0_label.configure(text='Error', text_color='red')
                
                # Read temperature sensor (ai1)
                temp_voltage, temperature = self.read_temperature_sensor()
                if temp_voltage is not None:
                    self.temp_voltage_label.configure(text=f'{temp_voltage:.4f} V', text_color='green')
                    if temperature is not None:
                        self.temp_display_label.configure(text=f'{temperature:.2f} °C', text_color='green')
                    else:
                        self.temp_display_label.configure(text='Sensor Disconnected', text_color='red')
                else:
                    self.temp_voltage_label.configure(text='Error', text_color='red')
                    self.temp_display_label.configure(text='Error', text_color='red')
        except Exception as e:
            pass  # Silently fail to avoid spam
        
        # Schedule next update (every 100ms for real-time updates)
        self.after(100, self.update_mcusb_readings)
    
    def list_visa_devices(self):
        """List all available VISA devices (with threading)"""
        print("DEBUG: List VISA devices button clicked")
        
        # 1. Show loading message immediately (Main Thread)
        messagebox.showinfo('Scanning', 'Scanning for VISA devices...\nThis may take a few seconds.')
        
        # 2. Run logic in background thread
        threading.Thread(target=self._run_list_visa_devices_logic, daemon=True).start()
    
    def _run_list_visa_devices_logic(self):
        """Background thread for listing VISA devices"""
        try:
            # Heavy VISA operations here (this can take several seconds)
            resources = self.hw_controller.list_visa_resources()
            
            if resources:
                device_list = "Available VISA Devices:\n\n"
                for i, resource in enumerate(resources, 1):
                    device_list += f"{i}. {resource}\n"
                    try:
                        # Access ResourceManager through SMU object
                        if self.hw_controller.smu and hasattr(self.hw_controller.smu, 'rm') and self.hw_controller.smu.rm:
                            inst = self.hw_controller.smu.rm.open_resource(resource)
                            inst.timeout = 2000
                            idn = inst.query("*IDN?")
                            device_list += f"   IDN: {idn.strip()}\n"
                            inst.close()
                    except:
                        device_list += "   (Could not query device)\n"
                    device_list += "\n"
                
                # 3. Schedule UI update back on Main Thread
                self.after(0, lambda: messagebox.showinfo('VISA Devices', device_list))
            else:
                self.after(0, lambda: messagebox.showinfo('VISA Devices', 'No VISA devices found.'))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: messagebox.showerror('Error', f'Error listing VISA devices: {error_msg}'))
    
    def set_smu_voltage_manual(self):
        """Set SMU voltage manually"""
        try:
            voltage = float(self.smu_voltage_entry.get())
            current_limit = float(self.smu_current_limit_entry.get())
            
            self.hw_controller.setup_smu_for_iv_measurement(current_limit)
            
            if self.hw_controller.set_smu_voltage(voltage, current_limit):
                messagebox.showinfo('Success', f'Voltage set to {voltage}V\nCurrent limit: {current_limit}A')
                self.refresh_smu_status()
            else:
                messagebox.showerror('Error', 'Failed to set voltage. Check SMU connection.')
        except ValueError:
            messagebox.showerror('Error', 'Please enter valid numbers for voltage and current limit.')
        except Exception as e:
            messagebox.showerror('Error', f'Error setting voltage: {e}')
    
    def measure_smu_manual(self):
        """Take a manual measurement from SMU"""
        try:
            measurement = self.hw_controller.measure_smu()
            if measurement:
                voltage = measurement.get('voltage', 0)
                current = measurement.get('current', 0)
                resistance = voltage / current if current != 0 else float('inf')
                
                self.iv_voltage_label.configure(text=self.format_value_with_unit(voltage, 'voltage'))
                self.iv_current_label.configure(text=self.format_value_with_unit(current, 'current'))
                if resistance != float('inf'):
                    self.iv_resistance_label.configure(text=self.format_value_with_unit(resistance, 'resistance'))
                else:
                    self.iv_resistance_label.configure(text='∞')
                
                messagebox.showinfo('Measurement', 
                    f'Voltage: {self.format_value_with_unit(voltage, "voltage")}\n'
                    f'Current: {self.format_value_with_unit(current, "current")}\n'
                    f'Resistance: {self.format_value_with_unit(resistance, "resistance") if resistance != float("inf") else "∞"}')
            else:
                messagebox.showerror('Error', 'Failed to measure. Check SMU connection.')
        except Exception as e:
            messagebox.showerror('Error', f'Error measuring: {e}')
    
    def smu_output_off(self):
        """Turn off SMU output"""
        try:
            self.hw_controller.stop_smu()
            messagebox.showinfo('Success', 'SMU output turned OFF')
            self.refresh_smu_status()
        except Exception as e:
            messagebox.showerror('Error', f'Error turning off output: {e}')

    def on_iv_output_toggle(self):
        """Enable/disable SMU output from IV tab top switch."""
        enabled = self.iv_output_var.get()
        self.iv_output_enabled = enabled

        if not enabled:
            try:
                if self.hw_controller.smu is not None and hasattr(self.hw_controller, 'smu'):
                    self.hw_controller.stop_smu()
                if self.update_queue:
                    self.update_queue.put(('UPDATE_IV_STATUS_BAR', 'SMU output turned OFF'))
            except Exception as e:
                messagebox.showerror('Error', f'Error turning off SMU output: {e}')
            return

        try:
            if self.hw_controller.smu is None or not hasattr(self.hw_controller, 'smu'):
                raise RuntimeError("SMU not connected.")

            voltage = float(self.smu_voltage_entry.get()) if hasattr(self, 'smu_voltage_entry') else 0.0
            current_limit = float(self.smu_current_limit_entry.get()) if hasattr(self, 'smu_current_limit_entry') else 0.1
            self.hw_controller.setup_smu_for_iv_measurement(current_limit)
            self.hw_controller.set_smu_voltage(voltage, current_limit)
            if self.update_queue:
                self.update_queue.put(('UPDATE_IV_STATUS_BAR', f'SMU output enabled: {voltage:.3f} V'))
        except Exception as e:
            self.iv_output_var.set(False)
            self.iv_output_enabled = False
            messagebox.showerror('Error', f'Error enabling SMU output: {e}')
    
    # --- Pump Control Functions ---
    def iv_refresh_pump_status(self):
        """Refresh pump connection status"""
        if hasattr(self, 'iv_pump_status_label'):
            self.iv_pump_status_label.configure(text="Scanning...", text_color='orange')
        threading.Thread(target=self._iv_run_refresh_pump_logic, daemon=True).start()
    
    def _iv_run_refresh_pump_logic(self):
        """Background thread for pump status refresh"""
        try:
            pump_info = self.hw_controller.pump.get_info()
            if not pump_info.get('connected', False):
                # Try to reconnect
                if hasattr(self.hw_controller.pump, 'force_reconnect'):
                    self.hw_controller.pump.force_reconnect()
                    time.sleep(2.0)
                    pump_info = {
                        "device_name": self.hw_controller.pump.device_name,
                        "port": self.hw_controller.pump.port,
                        "connected": True,
                        "status": "Connected",
                        "status_color": "green"
                    }
                else:
                    pump_info = self.hw_controller.pump.get_info()
            
            self.after(0, lambda: self._iv_update_pump_ui(pump_info))
        except Exception as e:
            self.after(0, lambda: self._iv_update_pump_error(str(e)))
    
    def _iv_update_pump_ui(self, pump_info):
        """Update pump UI"""
        if hasattr(self, 'iv_pump_status_label'):
            status_text = pump_info.get('status', 'Unknown')
            status_color = pump_info.get('status_color', 'gray')
            self.iv_pump_status_label.configure(text=status_text, text_color=status_color)
    
    def _iv_update_pump_error(self, error_msg):
        """Update pump UI with error"""
        if hasattr(self, 'iv_pump_status_label'):
            self.iv_pump_status_label.configure(text='Error', text_color='red')
    
    def iv_update_flow(self):
        """Update flow rate in IV tab"""
        try:
            new_flow_rate = float(self.iv_flow_rate_entry.get())
            
            if new_flow_rate < 0:
                messagebox.showerror('Error', 'Flow rate cannot be negative.')
                return
            
            MAX_FLOW_RATE = 5.0
            if new_flow_rate > MAX_FLOW_RATE:
                messagebox.showwarning('Flow Rate Limit', 
                    f'Maximum flow rate is {MAX_FLOW_RATE} ml/min.')
                new_flow_rate = MAX_FLOW_RATE
                self.iv_flow_rate_entry.delete(0, 'end')
                self.iv_flow_rate_entry.insert(0, str(MAX_FLOW_RATE))
            
            self.hw_controller.set_pump_flow_rate(new_flow_rate)
            
            # Sync with iv_flow_entry
            if hasattr(self, 'iv_flow_entry'):
                self.iv_flow_entry.delete(0, 'end')
                self.iv_flow_entry.insert(0, str(new_flow_rate))
            
            if self.update_queue:
                self.update_queue.put(('UPDATE_IV_STATUS_BAR', 
                    f'Flow rate updated: {new_flow_rate:.2f} ml/min'))
        except ValueError:
            messagebox.showerror('Error', 'Invalid flow rate. Please enter a valid number.')
        except Exception as e:
            messagebox.showerror('Error', f'Error updating flow rate: {e}')
    
    def iv_sync_flow_entries(self, event=None):
        """Sync flow rate entries"""
        try:
            source = event.widget if event else None
            if source == self.iv_flow_entry:
                # Update iv_flow_rate_entry from iv_flow_entry
                value = self.iv_flow_entry.get()
                if hasattr(self, 'iv_flow_rate_entry'):
                    self.iv_flow_rate_entry.delete(0, 'end')
                    self.iv_flow_rate_entry.insert(0, value)
            elif source == self.iv_flow_rate_entry:
                # Update iv_flow_entry from iv_flow_rate_entry
                value = self.iv_flow_rate_entry.get()
                if hasattr(self, 'iv_flow_entry'):
                    self.iv_flow_entry.delete(0, 'end')
                    self.iv_flow_entry.insert(0, value)
        except:
            pass
    
    # --- I-V Measurement Functions ---
    def iv_direct_set(self):
        """IV direct setting"""
        try:
            start_val = float(self.iv_start_entry.get()) if self.iv_start_entry.get() else -2.0
            stop_val = float(self.iv_stop_entry.get()) if self.iv_stop_entry.get() else 2.0
            step_val = float(self.iv_step_entry.get()) if self.iv_step_entry.get() else 0.1
            dwell_time_min = float(self.iv_time_entry.get()) if self.iv_time_entry.get() else 1.0
            flow_rate = float(self.iv_flow_entry.get()) if self.iv_flow_entry.get() else 1.5
            
            # Enforce maximum flow rate of 5.0 ml/min
            MAX_FLOW_RATE = 5.0
            if flow_rate > MAX_FLOW_RATE:
                messagebox.showwarning('Flow Rate Limit', 
                    f'Maximum flow rate is {MAX_FLOW_RATE} ml/min.\n'
                    f'Flow rate will be set to {MAX_FLOW_RATE} ml/min.')
                flow_rate = MAX_FLOW_RATE
                self.iv_flow_entry.delete(0, 'end')
                self.iv_flow_entry.insert(0, str(MAX_FLOW_RATE))
            if flow_rate < 0:
                messagebox.showerror('Error', 'Flow rate cannot be negative.')
                return
            if dwell_time_min <= 0:
                messagebox.showerror('Error', 'Step duration must be greater than 0 minutes.')
                return
            try:
                # Centralized sweep validation: non-zero step and correct direction.
                self._build_voltage_points(start_val, stop_val, step_val)
            except ValueError as validation_error:
                messagebox.showerror('Error', str(validation_error))
                return
            
            self.hw_controller.setup_smu_iv_sweep(start_val, stop_val, step_val)
            self.hw_controller.set_pump_flow_rate(flow_rate)
            valve_main = self.iv_valve_var.get() == 'main'
            self.hw_controller.set_valves(valve_main, not valve_main)
            
            if self.update_queue:
                self.update_queue.put((
                    'UPDATE_IV_STATUS_BAR',
                    f"I-V setup completed: Start={start_val}V, Stop={stop_val}V, Step={step_val}V, Dwell={dwell_time_min} min, Flow={flow_rate} ml/min"
                ))
        except ValueError:
            messagebox.showerror('Error', "Invalid input values. Please enter numbers.")
    
    def iv_direct_run(self):
        """IV direct run"""
        try:
            start_val = float(self.iv_start_entry.get()) if self.iv_start_entry.get() else -2.0
            stop_val = float(self.iv_stop_entry.get()) if self.iv_stop_entry.get() else 2.0
            step_val = float(self.iv_step_entry.get()) if self.iv_step_entry.get() else 0.1
            dwell_time_min = float(self.iv_time_entry.get()) if self.iv_time_entry.get() else 1.0
            
            if dwell_time_min <= 0:
                messagebox.showerror('Error', 'Step duration must be greater than 0 minutes.')
                return
            try:
                # Validate sweep before launching measurement thread.
                self._build_voltage_points(start_val, stop_val, step_val)
            except ValueError as validation_error:
                messagebox.showerror('Error', str(validation_error))
                return
            
            # Reset stop flag and enable stop button
            self.iv_measurement_stop = False
            if hasattr(self, 'iv_stop_button'):
                self.iv_stop_button.configure(state='normal')
            
            threading.Thread(target=self.run_iv_measurement,
                           args=(start_val, stop_val, step_val, dwell_time_min),
                           daemon=True).start()
        except ValueError:
            messagebox.showerror('Error', "Invalid input values. Please enter numbers.")
    
    def iv_stop_measurement(self):
        """Stop IV measurement"""
        self.iv_measurement_stop = True
        
        # Stop pump when measurement is stopped
        try:
            self.hw_controller.stop_pump()
            if self.update_queue:
                self.update_queue.put(('UPDATE_IV_STATUS_BAR', 'Pump stopped'))
        except Exception as e:
            print(f"Error stopping pump: {e}")
        
        if hasattr(self, 'iv_stop_button'):
            self.iv_stop_button.configure(state='disabled')
        if self.update_queue:
            self.update_queue.put(('UPDATE_IV_STATUS', ('Stopped', 'orange')))
            self.update_queue.put(('UPDATE_IV_STATUS_BAR', "Measurement stopped by user"))
    
    def iv_choose_program(self):
        """IV choose program - placeholder"""
        pass
    
    def iv_run_program(self):
        """IV run program - placeholder"""
        pass
    
    def read_iv_time_data(self):
        """Read voltage and current in real-time from SMU"""
        # BUG FIX #3: Better None check for SMU
        if self.hw_controller.smu is not None and hasattr(self.hw_controller, 'smu'):
            try:
                smu_data = self.hw_controller.read_smu_data()
                if smu_data and isinstance(smu_data, dict):
                    voltage = smu_data.get('voltage')
                    current = smu_data.get('current')
                    if voltage is not None and current is not None:
                        return voltage, current
                return None, None
            except (AttributeError, KeyError, Exception) as e:
                print(f"Error reading I-V: {e}")
                return None, None
        else:
            return None, None

    def _extract_current_value(self, measurement):
        """Extract current value from different SMU response key variants."""
        if not isinstance(measurement, dict):
            return None
        for key in ('current', 'measured_current', 'i', 'current_A'):
            if key in measurement and measurement.get(key) is not None:
                try:
                    return float(measurement.get(key))
                except (TypeError, ValueError):
                    return None
        return None

    def _read_iv_current_only(self):
        """Read only measured current (READ?) from SMU in IV mode."""
        try:
            if self.hw_controller.smu is None or not hasattr(self.hw_controller, 'smu'):
                return None
            if not hasattr(self.hw_controller.smu, 'smu') or self.hw_controller.smu.smu is None:
                return None
            if not hasattr(self.hw_controller.smu, 'scpi'):
                return None

            read_cmd = self.hw_controller.smu.scpi.read_data()
            read_value = self.hw_controller.smu.smu.query(read_cmd).strip()
            return float(read_value)
        except Exception as e:
            print(f"Error reading IV current (READ?): {e}")
            return None
    
    def _build_voltage_points(self, start_val, stop_val, step_val):
        """Build safe voltage list with direction/step validation."""
        if start_val == stop_val:
            return [start_val]
        if step_val == 0:
            raise ValueError("Step must not be zero when start and stop differ.")
        if start_val < stop_val and step_val < 0:
            raise ValueError("Step must be positive for ascending sweep.")
        if start_val > stop_val and step_val > 0:
            raise ValueError("Step must be negative for descending sweep.")
        
        points = []
        v = start_val
        epsilon = abs(step_val) * 1e-9 + 1e-12
        max_points = 100000
        
        if step_val > 0:
            while v <= stop_val + epsilon and len(points) < max_points:
                points.append(v)
                v += step_val
        else:
            while v >= stop_val - epsilon and len(points) < max_points:
                points.append(v)
                v += step_val
        
        if len(points) >= max_points:
            raise ValueError("Too many voltage points. Check step/start/stop values.")
        return points

    def run_iv_measurement(self, start_val, stop_val, step_val, dwell_time_min):
        """Run time-based I-V measurement with fixed pump flow and 0.5s current sampling."""
        # Reset stop flag
        self.iv_measurement_stop = False
        sample_interval_s = 0.5
        settling_time_s = 0.5
        dwell_seconds = dwell_time_min * 60.0
        
        if self.update_queue:
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
        if self.data_handler.file_path and self.update_queue:
            filename = os.path.basename(self.data_handler.file_path)
            self.update_queue.put(('UPDATE_IV_FILE', filename))
        
        # Get flow rate from entry
        try:
            flow_rate = float(self.iv_flow_entry.get()) if hasattr(self, 'iv_flow_entry') and self.iv_flow_entry.get() else 1.5
            MAX_FLOW_RATE = 5.0
            if flow_rate > MAX_FLOW_RATE:
                flow_rate = MAX_FLOW_RATE
            if flow_rate < 0:
                flow_rate = 1.5
        except:
            flow_rate = 1.5
        
        # Start pump automatically before measurement
        try:
            if self.hw_controller.pump and hasattr(self.hw_controller.pump, 'connected'):
                if not self.hw_controller.pump.connected:
                    # Try to reconnect
                    if hasattr(self.hw_controller.pump, 'force_reconnect'):
                        self.hw_controller.pump.force_reconnect()
                        time.sleep(2.0)
                
                # Set flow rate and start pump
                self.hw_controller.set_pump_flow_rate(flow_rate)
                time.sleep(0.3)
                pump_started = self.hw_controller.start_pump()
                
                # Set valves
                if hasattr(self, 'iv_valve_var'):
                    valve_main = self.iv_valve_var.get() == 'main'
                    self.hw_controller.set_valves(valve_main, not valve_main)
                
                if pump_started:
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_IV_STATUS_BAR', 
                            f'Pump started: {flow_rate} ml/min'))
                else:
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_IV_STATUS_BAR', 
                            'Warning: Pump start failed'))
        except Exception as e:
            print(f"Error starting pump: {e}")
            if self.update_queue:
                self.update_queue.put(('UPDATE_IV_STATUS_BAR', 
                    f'Warning: Could not start pump: {e}'))
        
        try:
            try:
                current_limit = float(self.smu_current_limit_entry.get()) if hasattr(self, 'smu_current_limit_entry') else 0.1
            except:
                current_limit = 0.1
            
            voltage_points = self._build_voltage_points(start_val, stop_val, step_val)
            
            total_points = len(voltage_points)
            
            # Configure SMU
            # BUG FIX #3: Better None check for SMU
            if self.hw_controller.smu is not None and hasattr(self.hw_controller, 'smu'):
                try:
                    self.hw_controller.setup_smu_for_iv_measurement(current_limit)
                except (AttributeError, RuntimeError, Exception) as e:
                    print(f"Error configuring SMU: {e}")
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_IV_STATUS', ('Error', 'red')))
                        self.update_queue.put(('UPDATE_IV_STATUS_BAR', f"Error configuring SMU: {e}"))
                    return
            else:
                print("SMU not connected. Cannot perform measurement.")
                if self.update_queue:
                    self.update_queue.put(('UPDATE_IV_STATUS', ('Error', 'red')))
                    self.update_queue.put(('UPDATE_IV_STATUS_BAR', "SMU not connected"))
                return
            
            # Perform time-based step sweep:
            # each voltage is held for dwell_seconds; current sampled every 0.5 s.
            # Voltage is taken from software setpoint; current is measured continuously.
            for step_index, voltage in enumerate(voltage_points, start=1):
                # Check if measurement should be stopped
                if self.iv_measurement_stop:
                    print("Measurement stopped by user")
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_IV_STATUS', ('Stopped', 'orange')))
                        self.update_queue.put(('UPDATE_IV_STATUS_BAR', "Measurement stopped by user"))
                    # BUG FIX #2: Lambda closure - capture button reference correctly
                    if hasattr(self, 'iv_stop_button'):
                        btn = self.iv_stop_button
                        self.after(0, lambda b=btn: b.configure(state='disabled'))
                    break
                
                # BUG FIX #3: Better None check for SMU
                if self.hw_controller.smu is not None and hasattr(self.hw_controller, 'smu'):
                    try:
                        self.hw_controller.set_smu_voltage(voltage, current_limit)
                        # No settling delay on first step; only between voltage transitions
                        if step_index > 1:
                            time.sleep(settling_time_s)
                    except Exception as e:
                        print(f"Error in I-V measurement at {voltage}V: {e}")
                        continue
                else:
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_IV_STATUS', ('Error', 'red')))
                        self.update_queue.put(('UPDATE_IV_STATUS_BAR', "SMU not connected"))
                    return
                step_start_time = time.time()
                while (time.time() - step_start_time) < dwell_seconds and not self.iv_measurement_stop:
                    # IV mode policy:
                    # - Voltage comes from the programmed setpoint.
                    # - Only current is read from SMU (READ? with SENS:FUNC CURR).
                    current = self._read_iv_current_only()
                    if current is None:
                        time.sleep(sample_interval_s)
                        continue
                    
                    elapsed_time_s = time.time() - self.iv_measurement_start_time
                    elapsed_time_min = elapsed_time_s / 60.0
                    
                    # Update graph arrays
                    self.iv_x_data.append(voltage)
                    self.iv_y_data.append(current)
                    self.iv_time_x_data.append(elapsed_time_min)
                    self.iv_time_v_data.append(voltage)
                    self.iv_time_i_data.append(current)
                    
                    pump_flow_read = flow_rate
                    try:
                        pump_data = self.hw_controller.read_pump_data()
                        if isinstance(pump_data, dict):
                            pump_flow_read = pump_data.get('flow', flow_rate)
                    except Exception:
                        pass
                    
                    # Save data point using DataHandler schema
                    data_point = {
                        "time": elapsed_time_s,
                        "flow_setpoint": flow_rate,
                        "pump_flow_read": pump_flow_read,
                        "pressure_read": "",
                        "temp_read": "",
                        "level_read": "",
                        "program_step": step_index,
                        "voltage": voltage,
                        "current": current,
                        "target_voltage": voltage
                    }
                    self.data_handler.append_data(data_point)
                    
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_IV_GRAPH', (list(self.iv_x_data), list(self.iv_y_data))))
                        self.update_queue.put((
                            'UPDATE_IV_STATUS_BAR',
                            f"Step {step_index}/{total_points}: V={voltage:.3f}V, t={elapsed_time_min:.2f} min"
                        ))
                    self.after(
                        0,
                        lambda v=voltage, i=current: (
                            self.iv_voltage_label.configure(text=self.format_value_with_unit(v, 'voltage')),
                            self.iv_current_label.configure(text=self.format_value_with_unit(i, 'current')),
                            self.iv_resistance_label.configure(
                                text=self.format_value_with_unit(v / i, 'resistance') if abs(i) > 1e-12 else '∞'
                            )
                        )
                    )
                    
                    time.sleep(sample_interval_s)
                
                # Check stop flag between steps
                if self.iv_measurement_stop:
                    print("Measurement stopped by user")
                    try:
                        self.hw_controller.stop_pump()
                    except Exception as e:
                        print(f"Error stopping pump: {e}")
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_IV_STATUS', ('Stopped', 'orange')))
                        self.update_queue.put(('UPDATE_IV_STATUS_BAR', "Measurement stopped by user"))
                    if hasattr(self, 'iv_stop_button'):
                        btn = self.iv_stop_button
                        self.after(0, lambda b=btn: b.configure(state='disabled'))
                    break
            
            if self.update_queue:
                self.update_queue.put(('UPDATE_IV_STATUS', ('Completed', 'green')))
                self.update_queue.put(('UPDATE_IV_STATUS_BAR', "I-V measurement completed"))
            
            # Stop pump when measurement ends
            try:
                self.hw_controller.stop_pump()
                if self.update_queue:
                    self.update_queue.put(('UPDATE_IV_STATUS_BAR', 'Pump stopped'))
            except Exception as e:
                print(f"Error stopping pump: {e}")
            
            # BUG FIX #2: Lambda closure - capture button reference correctly
            if hasattr(self, 'iv_stop_button'):
                btn = self.iv_stop_button
                self.after(0, lambda b=btn: b.configure(state='disabled'))
            
        except Exception as e:
            if self.update_queue:
                self.update_queue.put(('UPDATE_IV_STATUS', ('Error', 'red')))
                self.update_queue.put(('UPDATE_IV_STATUS_BAR', f"I-V measurement error: {e}"))
            print(f"I-V measurement error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            try:
                self.data_handler.close_file()
            except Exception as e:
                print(f"Error closing IV data file: {e}")
            finally:
                self.hw_controller.stop_smu()
    
    # --- Graph Functions ---
    def on_iv_axis_change(self, *args):
        """Handle IV axis selection change"""
        x_axis_type = self.iv_x_axis_combo.get()
        y_axis_type = self.iv_y_axis_combo.get()
        self.plot_iv_xy_graph(x_axis_type, y_axis_type)
    
    def plot_iv_xy_graph(self, x_axis_type, y_axis_type):
        """Plot IV graph with selected axes and automatic unit scaling"""
        saved_xlim = None
        saved_ylim = None
        if not self.iv_auto_scale_enabled:
            saved_xlim = self.iv_ax.get_xlim()
            saved_ylim = self.iv_ax.get_ylim()

        self.iv_ax.clear()
        
        if x_axis_type == 'Time' and y_axis_type == 'Voltage':
            x_data = self.iv_time_x_data
            y_data = self.iv_time_v_data
            xlabel_base = "Time"
            ylabel_base = "Voltage"
            title = "Voltage vs Time"
            y_unit, y_scale = self.get_axis_unit_label(y_data, 'voltage')
            ylabel = f"{ylabel_base} ({y_unit})"
            xlabel = f"{xlabel_base} (min)"
            y_data_scaled = [y * y_scale for y in y_data] if y_data else []
            x_data_scaled = x_data
        elif x_axis_type == 'Time' and y_axis_type == 'Current':
            x_data = self.iv_time_x_data
            y_data = self.iv_time_i_data
            xlabel_base = "Time"
            ylabel_base = "Current"
            title = "Current vs Time"
            y_unit, y_scale = self.get_axis_unit_label(y_data, 'current')
            ylabel = f"{ylabel_base} ({y_unit})"
            xlabel = f"{xlabel_base} (min)"
            y_data_scaled = [y * y_scale for y in y_data] if y_data else []
            x_data_scaled = x_data
        elif x_axis_type == 'Voltage' and y_axis_type == 'Current':
            x_data = self.iv_x_data
            y_data = self.iv_y_data
            xlabel_base = "Voltage"
            ylabel_base = "Current"
            title = "I-V Characteristic"
            x_unit, x_scale = self.get_axis_unit_label(x_data, 'voltage')
            y_unit, y_scale = self.get_axis_unit_label(y_data, 'current')
            xlabel = f"{xlabel_base} ({x_unit})"
            ylabel = f"{ylabel_base} ({y_unit})"
            x_data_scaled = [x * x_scale for x in x_data] if x_data else []
            y_data_scaled = [y * y_scale for y in y_data] if y_data else []
        elif x_axis_type == 'Current' and y_axis_type == 'Voltage':
            x_data = self.iv_y_data
            y_data = self.iv_x_data
            xlabel_base = "Current"
            ylabel_base = "Voltage"
            title = "V-I Characteristic"
            x_unit, x_scale = self.get_axis_unit_label(x_data, 'current')
            y_unit, y_scale = self.get_axis_unit_label(y_data, 'voltage')
            xlabel = f"{xlabel_base} ({x_unit})"
            ylabel = f"{ylabel_base} ({y_unit})"
            x_data_scaled = [x * x_scale for x in x_data] if x_data else []
            y_data_scaled = [y * y_scale for y in y_data] if y_data else []
        else:
            x_data = self.iv_x_data
            y_data = self.iv_y_data
            xlabel_base = "Voltage"
            ylabel_base = "Current"
            title = "I-V Characteristic"
            x_unit, x_scale = self.get_axis_unit_label(x_data, 'voltage')
            y_unit, y_scale = self.get_axis_unit_label(y_data, 'current')
            xlabel = f"{xlabel_base} ({x_unit})"
            ylabel = f"{ylabel_base} ({y_unit})"
            x_data_scaled = [x * x_scale for x in x_data] if x_data else []
            y_data_scaled = [y * y_scale for y in y_data] if y_data else []
        
        # Plot the data
        if len(x_data_scaled) > 0 and len(y_data_scaled) > 0:
            self.iv_ax.plot(x_data_scaled, y_data_scaled, color='#C73E1D', linewidth=2.5, alpha=0.85)
        else:
            self.iv_ax.plot([], [], color='#C73E1D', linewidth=2.5)
        
        # Formatting
        self.iv_ax.set_facecolor('white')
        self.iv_ax.set_xlabel(xlabel, color='black', fontsize=11)
        self.iv_ax.set_ylabel(ylabel, color='black', fontsize=11)
        self.iv_ax.set_title(title, color='black', fontsize=12, fontweight='bold', pad=12)
        
        self.iv_ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5, which='both')
        self.iv_ax.set_axisbelow(True)
        self.iv_ax.tick_params(colors='black', labelsize=9)
        
        for spine in self.iv_ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
        
        # Set axis limits
        if len(x_data_scaled) > 0 and len(y_data_scaled) > 0:
            if self.iv_auto_scale_enabled:
                x_margin = (max(x_data_scaled) - min(x_data_scaled)) * 0.05 if max(x_data_scaled) > min(x_data_scaled) else 1
                y_margin = (max(y_data_scaled) - min(y_data_scaled)) * 0.1 if max(y_data_scaled) > min(y_data_scaled) else 1
                self.iv_ax.set_xlim(min(x_data_scaled) - x_margin, max(x_data_scaled) + x_margin)
                self.iv_ax.set_ylim(min(y_data_scaled) - y_margin, max(y_data_scaled) + y_margin)
            elif saved_xlim is not None and saved_ylim is not None:
                self.iv_ax.set_xlim(saved_xlim)
                self.iv_ax.set_ylim(saved_ylim)
        
        self.iv_fig.tight_layout(pad=2.0)
        self.iv_canvas.draw()

    def toggle_iv_auto_scale(self):
        """Toggle auto-scale on/off for IV graph."""
        self.iv_auto_scale_enabled = not self.iv_auto_scale_enabled
        if self.iv_auto_scale_enabled:
            self.iv_auto_scale_btn.configure(
                text='🔓 Auto-Scale ON',
                fg_color='#1E88E5',
                hover_color='#1565C0'
            )
        else:
            self.iv_auto_scale_btn.configure(
                text='🔒 Auto-Scale OFF',
                fg_color='#616161',
                hover_color='#424242'
            )
        self.on_iv_axis_change()
    
    def update_iv_graph(self, x_data, y_data):
        """Update IV graph - now uses axis selection"""
        if x_data and y_data:
            self.iv_x_data = list(x_data)
            self.iv_y_data = list(y_data)
        
        x_axis_type = self.iv_x_axis_combo.get()
        y_axis_type = self.iv_y_axis_combo.get()
        self.plot_iv_xy_graph(x_axis_type, y_axis_type)

    def update_iv_time_graph(self, time_data, voltage_data, current_data):
        """Update IV time-series buffers and replot with selected axes."""
        if time_data is not None:
            self.iv_time_x_data = list(time_data)
        if voltage_data is not None:
            self.iv_time_v_data = list(voltage_data)
            # Keep IV characteristic arrays synced for non-time axes as well.
            self.iv_x_data = list(voltage_data)
        if current_data is not None:
            self.iv_time_i_data = list(current_data)
            self.iv_y_data = list(current_data)

        x_axis_type = self.iv_x_axis_combo.get()
        y_axis_type = self.iv_y_axis_combo.get()
        self.plot_iv_xy_graph(x_axis_type, y_axis_type)
    
    def update_iv_statistics(self):
        """Calculate and update I-V statistics"""
        try:
            # BUG FIX #4: Thread-safe access and length validation
            # Make copies to avoid race conditions
            iv_x_copy = list(self.iv_x_data) if self.iv_x_data else []
            iv_y_copy = list(self.iv_y_data) if self.iv_y_data else []
            
            # Validate arrays have same length and are not empty
            if len(iv_x_copy) > 0 and len(iv_y_copy) > 0 and len(iv_x_copy) == len(iv_y_copy):
                self.iv_points_label.configure(text=str(len(iv_x_copy)))
                
                v_min = min(iv_x_copy)
                v_max = max(iv_x_copy)
                self.iv_vrange_label.configure(text=self.format_range_with_unit(v_min, v_max, 'voltage'))
                
                i_min = min(iv_y_copy)
                i_max = max(iv_y_copy)
                self.iv_irange_label.configure(text=self.format_range_with_unit(i_min, i_max, 'current'))
                
                resistances = []
                for v, i in zip(iv_x_copy, iv_y_copy):
                    # BUG FIX #12: Better check for division by zero (also check for very small values)
                    if i is not None and v is not None and abs(i) > 1e-10:  # Avoid division by very small numbers
                        resistances.append(v / i)
                
                if resistances:
                    max_r = max(resistances)
                    min_r = min(resistances)
                    self.iv_maxr_label.configure(text=self.format_value_with_unit(max_r, 'resistance'))
                    self.iv_minr_label.configure(text=self.format_value_with_unit(min_r, 'resistance'))
                else:
                    self.iv_maxr_label.configure(text="N/A")
                    self.iv_minr_label.configure(text="N/A")
            else:
                self.iv_points_label.configure(text='0')
                self.iv_vrange_label.configure(text='N/A')
                self.iv_irange_label.configure(text='N/A')
                self.iv_maxr_label.configure(text='N/A')
                self.iv_minr_label.configure(text='N/A')
        except (ValueError, TypeError, ZeroDivisionError) as e:
            print(f"Error updating I-V statistics: {e}")
        except Exception as e:
            print(f"Unexpected error updating I-V statistics: {e}")
    
    # --- Export Functions ---
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
                if self.update_queue:
                    self.update_queue.put(('UPDATE_IV_STATUS_BAR', "I-V data saved to file"))
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

