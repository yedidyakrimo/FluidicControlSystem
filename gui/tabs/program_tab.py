"""
Program Tab - Write and run experiment programs
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import time

from gui.tabs.base_tab import BaseTab


class ProgramTab(BaseTab):
    """
    Program tab for writing and running experiment programs
    """
    
    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None, main_tab_ref=None):
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        self.main_tab_ref = main_tab_ref  # Reference to MainTab for integration
        
        # Create widgets
        self.create_widgets()
    
    def create_widgets(self):
        """Create Program tab widgets"""
        # Program Editor
        editor_frame = ctk.CTkFrame(self)
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
        control_frame = ctk.CTkFrame(self)
        control_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(control_frame, text="Program Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        control_btn_frame = ctk.CTkFrame(control_frame)
        control_btn_frame.pack(pady=5)
        self.create_blue_button(control_btn_frame, text='Load Program', command=self.load_program, width=120).pack(side='left', padx=5)
        self.create_blue_button(control_btn_frame, text='Save Program', command=self.save_program, width=120).pack(side='left', padx=5)
        self.create_blue_button(control_btn_frame, text='Run Program', command=self.run_program, width=120).pack(side='left', padx=5)
        self.create_blue_button(control_btn_frame, text='Stop Program', command=self.stop_program, width=120,
                                fg_color='#0D47A1', hover_color='#0C3A7A').pack(side='left', padx=5)
        
        # Program Library
        library_frame = ctk.CTkFrame(self)
        library_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(library_frame, text="Program Library", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        library_content = ctk.CTkFrame(library_frame)
        library_content.pack(fill='x', padx=5, pady=5)
        
        self.program_var = ctk.StringVar(value="Standard Test")
        self.program_optionmenu = ctk.CTkOptionMenu(
            library_content, 
            values=["Standard Test", "Temperature Ramp", "Flow Ramp", "Valve Switching Test", "Complex Multi-Step"],
            variable=self.program_var,
            width=300
        )
        self.program_optionmenu.pack(side='left', padx=5)
        
        self.create_blue_button(library_content, text='Load Selected', command=self.load_selected, width=150).pack(side='left', padx=5)
        
        # Program Status
        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(status_frame, text="Program Status", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        status_content = ctk.CTkFrame(status_frame)
        status_content.pack(fill='x', padx=5, pady=5)
        
        ctk.CTkLabel(status_content, text='Status:', width=80).pack(side='left', padx=5)
        self.program_status_label = ctk.CTkLabel(status_content, text='Ready', width=400)
        self.program_status_label.pack(side='left', padx=5)
    
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
                if self.update_queue:
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
                if self.update_queue:
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
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_PROGRAM_STATUS', f"Loaded template: {selected}"))
        except Exception as e:
            messagebox.showerror('Error', f"Error loading template: {e}")
    
    def run_program(self):
        """Run program - triggers MainTab.start_recording_from_program_tab()"""
        try:
            # Parse program
            program_text = self.program_editor.get('1.0', 'end-1c')
            experiment_program = self.parse_program(program_text)
            
            if not experiment_program:
                messagebox.showerror('Error', "Invalid program format or empty program")
                return
            
            # Check if MainTab reference exists
            if not self.main_tab_ref:
                messagebox.showerror('Error', 
                    "MainTab reference not available. Cannot start recording.\n"
                    "Please use the Main tab to start experiments.")
                return
            
            # Check if experiment name is set in MainTab
            exp_name = self.main_tab_ref.exp_name_entry.get().strip()
            if not exp_name:
                messagebox.showwarning('Warning', 
                    'Please enter an experiment name in the Main tab before running program.\n\n'
                    'The program will use the Main tab for recording and monitoring.')
                return
            
            # Call the wrapper method (doesn't change existing MainTab behavior)
            success = self.main_tab_ref.start_recording_from_program_tab(experiment_program)
            
            if success:
                if self.update_queue:
                    self.update_queue.put(('UPDATE_PROGRAM_STATUS', 
                        f"Program started via Main tab: {len(experiment_program)} steps"))
            else:
                messagebox.showerror('Error', 
                    'Failed to start program. Please check:\n'
                    '1. Experiment name is valid\n'
                    '2. All program steps are valid')
                
        except Exception as e:
            messagebox.showerror('Error', f"Error running program: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_program(self):
        """Stop program - triggers MainTab.stop_recording()"""
        if self.main_tab_ref:
            # Use existing stop_recording() method - no changes needed!
            self.main_tab_ref.stop_recording()
            if self.update_queue:
                self.update_queue.put(('UPDATE_PROGRAM_STATUS', "Program stopped via Main tab"))
        else:
            # Fallback to direct stop (for backward compatibility)
            self.exp_manager.stop_experiment()
            if self.update_queue:
                self.update_queue.put(('UPDATE_PROGRAM_STATUS', "Program stopped"))
    
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
                                flow_rate = float(value)
                                # Enforce maximum flow rate of 5.0 ml/min
                                MAX_FLOW_RATE = 5.0
                                if flow_rate > MAX_FLOW_RATE:
                                    print(f"Warning: Flow rate {flow_rate} ml/min exceeds maximum of {MAX_FLOW_RATE} ml/min. Setting to {MAX_FLOW_RATE} ml/min.")
                                    flow_rate = MAX_FLOW_RATE
                                if flow_rate < 0:
                                    print(f"Warning: Flow rate cannot be negative. Setting to 0.")
                                    flow_rate = 0.0
                                step_data['flow_rate'] = flow_rate
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
    
    def run_program_thread(self, experiment_program):
        """Run program from Write Program tab"""
        self.exp_manager.is_running = True
        if self.update_queue:
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
            
            if self.update_queue:
                self.update_queue.put(('UPDATE_PROGRAM_STATUS', f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min, Temp={temperature}°C"))
            
            # Set pump flow rate and start the pump
            self.exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
            time.sleep(0.3)  # Wait for pump to process flow rate setting
            self.exp_manager.hw_controller.start_pump()  # Start the pump
            time.sleep(0.5)  # Wait for pump to actually start running
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
                
                if self.update_queue:
                    self.update_queue.put(('UPDATE_STATUS', f"Running: {remaining_time:.0f}s remaining, Flow={flow_rate}ml/min"))
                
                # Update data arrays (thread-safe with lock - BUG FIX #1)
                with self.data_lock:
                    self.flow_x_data.append(elapsed_time_from_start)
                    self.flow_y_data.append(pump_data['flow'])
                    self.pressure_x_data.append(elapsed_time_from_start)
                    # FIXED: Handle None like temperature
                    if pressure is not None:
                        self.pressure_y_data.append(pressure)
                    else:
                        self.pressure_y_data.append(float('nan'))
                    self.temp_x_data.append(elapsed_time_from_start)
                    self.temp_y_data.append(temperature_read)
                    self.level_x_data.append(elapsed_time_from_start)
                    # FIXED: Handle None like temperature and pressure
                    if level is not None:
                        self.level_y_data.append(level * 100)
                    else:
                        self.level_y_data.append(float('nan'))
                
                data_point = {
                    "time": elapsed_time_from_start,
                    "flow_setpoint": flow_rate,
                    "pump_flow_read": pump_data['flow'],
                    "pressure_read": pressure if pressure is not None else "",  # FIXED: Handle None
                    "temp_read": temperature_read if temperature_read is not None else "",
                    "level_read": level if level is not None else "",
                    "program_step": len(experiment_program)
                }
                self.data_handler.append_data(data_point)
                
                # Update graphs (thread-safe - BUG FIX #1)
                if self.update_queue:
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
                time.sleep(1)
        
        self.exp_manager.stop_experiment()
        self.data_handler.close_file()
        if self.update_queue:
            self.update_queue.put(('UPDATE_PROGRAM_STATUS', 'Program completed.'))

