"""
Program Tab - Write and run experiment programs
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk, simpledialog
import re
import threading
import time
import pandas as pd

from gui.tabs.base_tab import BaseTab


class ProgramTab(BaseTab):
    """
    Program tab for writing and running experiment programs
    """
    
    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None, main_tab_ref=None, resistance_tab_ref=None):
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        self.main_tab_ref = main_tab_ref  # Reference to MainTab for integration
        self.resistance_tab_ref = resistance_tab_ref  # Reference to ResistanceTab to run program from Resistance tab
        self._last_run_via_resistance = False  # Track which tab started the program (for Stop)
        
        # Store table data
        self.table_data = []  # List of dicts: [{'step': 1, 'duration': 1.0, 'flow_rate': 0.2, 'measurement_mode': 'voltage', 'valve': 'main'}, ...]
        
        # Create widgets
        self.create_widgets()
    
    def create_widgets(self):
        """Create Program tab widgets"""
        # Program Table (Excel-like interface)
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        ctk.CTkLabel(table_frame, text="Program Table", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        # Create Treeview with scrollbars
        table_container = ctk.CTkFrame(table_frame)
        table_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_container, orient='vertical')
        v_scrollbar.pack(side='right', fill='y')
        
        h_scrollbar = ttk.Scrollbar(table_container, orient='horizontal')
        h_scrollbar.pack(side='bottom', fill='x')
        
        # Treeview table
        self.program_table = ttk.Treeview(
            table_container,
            columns=('Step', 'Duration (min)', 'Flow Rate (ml/min)', 'Measurement Mode', 'Valve', 'Bias Voltage (V)', 'Bias Current (A)'),
            show='headings',
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            height=12
        )
        
        # Configure scrollbars
        v_scrollbar.config(command=self.program_table.yview)
        h_scrollbar.config(command=self.program_table.xview)
        
        # Define column headings and widths
        self.program_table.heading('Step', text='Step')
        self.program_table.heading('Duration (min)', text='Duration (min)')
        self.program_table.heading('Flow Rate (ml/min)', text='Flow Rate (ml/min)')
        self.program_table.heading('Measurement Mode', text='Measurement Mode')
        self.program_table.heading('Valve', text='Valve')
        self.program_table.heading('Bias Voltage (V)', text='Bias Voltage (V)')
        self.program_table.heading('Bias Current (A)', text='Bias Current (A)')
        
        self.program_table.column('Step', width=60, anchor='center')
        self.program_table.column('Duration (min)', width=120, anchor='center')
        self.program_table.column('Flow Rate (ml/min)', width=150, anchor='center')
        self.program_table.column('Measurement Mode', width=180, anchor='center')
        self.program_table.column('Valve', width=100, anchor='center')
        self.program_table.column('Bias Voltage (V)', width=110, anchor='center')
        self.program_table.column('Bias Current (A)', width=110, anchor='center')
        
        self.program_table.pack(side='left', fill='both', expand=True)
        
        # Bind double-click for editing
        self.program_table.bind('<Double-1>', self.on_cell_double_click)
        self.program_table.bind('<Button-1>', self.on_cell_click)
        
        # Table control buttons
        table_control_frame = ctk.CTkFrame(table_frame)
        table_control_frame.pack(fill='x', padx=5, pady=5)
        
        self.create_blue_button(table_control_frame, text='➕ Add Step', command=self.add_step_row, width=100).pack(side='left', padx=2)
        self.create_blue_button(table_control_frame, text='➖ Delete Step', command=self.delete_selected_row, width=100).pack(side='left', padx=2)
        self.create_blue_button(table_control_frame, text='🗑️ Clear All', command=self.clear_table, width=100).pack(side='left', padx=2)
        self.create_blue_button(table_control_frame, text='🔄 Renumber Steps', command=self.renumber_steps, width=120).pack(side='left', padx=2)
        
        # Program Control
        control_frame = ctk.CTkFrame(self)
        control_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(control_frame, text="Program Control", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        # Run / file name (used as experiment file name when running)
        run_name_frame = ctk.CTkFrame(control_frame)
        run_name_frame.pack(fill='x', padx=5, pady=(0, 5))
        ctk.CTkLabel(run_name_frame, text='Run name (file name):', width=160).pack(side='left', padx=5)
        self.run_name_entry = ctk.CTkEntry(run_name_frame, width=220, placeholder_text='Optional – otherwise use name from Main/Resistance tab')
        self.run_name_entry.pack(side='left', padx=5)
        
        control_btn_frame = ctk.CTkFrame(control_frame)
        control_btn_frame.pack(pady=5)
        self.create_blue_button(control_btn_frame, text='📂 Load from Excel', command=self.load_from_excel, width=140).pack(side='left', padx=5)
        self.create_blue_button(control_btn_frame, text='💾 Save to Excel', command=self.save_to_excel, width=140).pack(side='left', padx=5)
        self.create_blue_button(control_btn_frame, text='▶️ Run (Main)', command=self.run_program, width=110).pack(side='left', padx=5)
        self.create_blue_button(control_btn_frame, text='▶️ Run (Resistance)', command=self.run_program_from_resistance_tab, width=140).pack(side='left', padx=5)
        self.create_blue_button(control_btn_frame, text='⏹️ Stop Program', command=self.stop_program, width=120,
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
            values=["Standard Test", "Flow Ramp", "Valve Switching Test", "Measurement Mode Switch"],
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
        
        # Step Progress Frame
        step_progress_frame = ctk.CTkFrame(status_frame)
        step_progress_frame.pack(fill='x', padx=5, pady=5)
        
        self.step_info_label = ctk.CTkLabel(step_progress_frame, text="Step: - / -", 
                                           font=('Helvetica', 11))
        self.step_info_label.pack(side='left', padx=5)
        
        self.step_time_label = ctk.CTkLabel(step_progress_frame, text="Time remaining (step): -", 
                                           font=('Helvetica', 10))
        self.step_time_label.pack(side='left', padx=5)
        
        self.step_total_time_label = ctk.CTkLabel(step_progress_frame, text="Time remaining (total): -", 
                                                 font=('Helvetica', 10))
        self.step_total_time_label.pack(side='left', padx=5)
        
        self.step_progress_bar = ctk.CTkProgressBar(step_progress_frame, width=300)
        self.step_progress_bar.pack(side='left', padx=5)
        self.step_progress_bar.set(0)
        
        # Initialize with one empty row
        self.add_step_row()
    
    def add_step_row(self):
        """Add a new step row to the table"""
        step_num = len(self.table_data) + 1
        new_step = {
            'step': step_num,
            'duration': 1.0,
            'flow_rate': 0.2,
            'measurement_mode': 'voltage',
            'valve': 'main',
            'bias_voltage': 0.0,
            'bias_current': 0.0
        }
        self.table_data.append(new_step)
        self.update_table_display()
    
    def delete_selected_row(self):
        """Delete the selected row from the table"""
        selected = self.program_table.selection()
        if not selected:
            messagebox.showwarning('Warning', 'Please select a row to delete.')
            return
        
        for item in selected:
            # Get step number from the row
            values = self.program_table.item(item, 'values')
            if values:
                step_num = int(values[0])
                # Remove from data
                self.table_data = [s for s in self.table_data if s['step'] != step_num]
        
        self.renumber_steps()
        self.update_table_display()
    
    def clear_table(self):
        """Clear all rows from the table"""
        if messagebox.askyesno('Confirm', 'Are you sure you want to clear all steps?'):
            self.table_data.clear()
            self.update_table_display()
            # Add one empty row
            self.add_step_row()
    
    def renumber_steps(self):
        """Renumber all steps sequentially"""
        for i, step in enumerate(self.table_data, 1):
            step['step'] = i
        self.update_table_display()
    
    def update_table_display(self):
        """Update the table display from table_data"""
        # Clear existing items
        for item in self.program_table.get_children():
            self.program_table.delete(item)
        
        # Sort by step number
        sorted_data = sorted(self.table_data, key=lambda x: x['step'])
        
        # Insert rows
        for step in sorted_data:
            self.program_table.insert('', 'end', values=(
                step['step'],
                step['duration'],
                step['flow_rate'],
                step['measurement_mode'],
                step['valve'],
                step.get('bias_voltage', 0),
                step.get('bias_current', 0)
            ))
    
    def on_cell_click(self, event):
        """Handle cell click - prevent default selection behavior"""
        region = self.program_table.identify_region(event.x, event.y)
        if region == 'cell':
            column = self.program_table.identify_column(event.x)
            # Allow selection for deletion, but we'll handle editing separately
    
    def on_cell_double_click(self, event):
        """Handle double-click on cell for editing"""
        region = self.program_table.identify_region(event.x, event.y)
        if region == 'cell':
            item = self.program_table.selection()[0]
            column = self.program_table.identify_column(event.x)
            column_index = int(column.replace('#', '')) - 1  # Convert to 0-based index
            
            # Get current values
            values = self.program_table.item(item, 'values')
            step_num = int(values[0])
            
            # Find the step in table_data
            step = next((s for s in self.table_data if s['step'] == step_num), None)
            if not step:
                return
            
            # Column names mapping
            column_names = ['Step', 'Duration (min)', 'Flow Rate (ml/min)', 'Measurement Mode', 'Valve', 'Bias Voltage (V)', 'Bias Current (A)']
            column_name = column_names[column_index]
            
            # Edit based on column
            self.edit_cell(item, column_index, column_name, step)
    
    def edit_cell(self, item, column_index, column_name, step):
        """Edit a cell value"""
        current_value = self.program_table.item(item, 'values')[column_index]
        
        if column_name == 'Step':
            # Step number - use renumber instead
            messagebox.showinfo('Info', 'Use "Renumber Steps" button to renumber steps.')
            return
        
        elif column_name == 'Duration (min)':
            # Duration - numeric input
            new_value = simpledialog.askstring(
                "Edit Duration",
                "Enter Duration (minutes):",
                initialvalue=str(current_value)
            )
            if new_value is not None and new_value.strip():
                try:
                    duration = float(new_value)
                    if duration < 0:
                        messagebox.showerror('Error', 'Duration must be positive.')
                        return
                    step['duration'] = duration
                except ValueError:
                    messagebox.showerror('Error', 'Invalid duration value.')
                    return
        
        elif column_name == 'Flow Rate (ml/min)':
            # Flow rate - numeric input with validation
            new_value = simpledialog.askstring(
                "Edit Flow Rate",
                "Enter Flow Rate (ml/min, max 5.0):",
                initialvalue=str(current_value)
            )
            if new_value is not None and new_value.strip():
                try:
                    flow_rate = float(new_value)
                    if flow_rate < 0:
                        messagebox.showerror('Error', 'Flow rate cannot be negative.')
                        return
                    if flow_rate > 5.0:
                        messagebox.showwarning('Warning', f'Flow rate {flow_rate} exceeds maximum of 5.0. Setting to 5.0.')
                        flow_rate = 5.0
                    step['flow_rate'] = flow_rate
                except ValueError:
                    messagebox.showerror('Error', 'Invalid flow rate value.')
                    return
        
        elif column_name == 'Measurement Mode':
            # Measurement mode - dropdown
            new_value = simpledialog.askstring(
                "Edit Measurement Mode",
                "Enter Measurement Mode (voltage/current):",
                initialvalue=str(current_value)
            )
            if new_value is not None and new_value.strip():
                new_value = new_value.lower().strip()
                if new_value in ['voltage', 'current']:
                    step['measurement_mode'] = new_value
                else:
                    messagebox.showerror('Error', 'Measurement mode must be "voltage" or "current".')
                    return
        
        elif column_name == 'Valve':
            # Valve - dropdown
            new_value = simpledialog.askstring(
                "Edit Valve",
                "Enter Valve (main/rinsing):",
                initialvalue=str(current_value)
            )
            if new_value is not None and new_value.strip():
                new_value = new_value.lower().strip()
                if new_value in ['main', 'rinsing']:
                    step['valve'] = new_value
                else:
                    messagebox.showerror('Error', 'Valve must be "main" or "rinsing".')
                    return
        
        elif column_name == 'Bias Voltage (V)':
            new_value = simpledialog.askstring(
                "Edit Bias Voltage",
                "Enter Bias Voltage (V):",
                initialvalue=str(current_value)
            )
            if new_value is not None and new_value.strip():
                try:
                    step['bias_voltage'] = float(new_value)
                except ValueError:
                    messagebox.showerror('Error', 'Invalid number.')
                    return
        
        elif column_name == 'Bias Current (A)':
            new_value = simpledialog.askstring(
                "Edit Bias Current",
                "Enter Bias Current (A):",
                initialvalue=str(current_value)
            )
            if new_value is not None and new_value.strip():
                try:
                    step['bias_current'] = float(new_value)
                except ValueError:
                    messagebox.showerror('Error', 'Invalid number.')
                    return
        
        # Update display
        self.update_table_display()
    
    def table_to_program(self):
        """Convert table data to experiment program format"""
        program = []
        sorted_data = sorted(self.table_data, key=lambda x: x['step'])
        
        for step in sorted_data:
            duration_minutes = float(step.get('duration', 0))
            step_dict = {
                # Keep internal timing in seconds so runtime behavior/resolution is unchanged.
                'duration': duration_minutes * 60.0,
                'flow_rate': step['flow_rate'],
                'valve_setting': {'valve1': True, 'valve2': False} if step['valve'] == 'main' else {'valve1': False, 'valve2': True}
            }
            if step.get('measurement_mode'):
                step_dict['measurement_mode'] = step['measurement_mode']
            step_dict['bias_voltage'] = step.get('bias_voltage', 0.0)
            step_dict['bias_current'] = step.get('bias_current', 0.0)
            program.append(step_dict)
        
        return program
    
    def load_from_excel(self):
        """Load program from Excel/CSV file"""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[('Excel Files', '*.xlsx'), ('CSV Files', '*.csv'), ('All Files', '*.*')]
            )
            if filename:
                if filename.endswith('.csv'):
                    df = pd.read_csv(filename)
                else:
                    df = pd.read_excel(filename)
                
                # Clear existing data
                self.table_data.clear()
                
                # Convert DataFrame to table_data format
                for idx, row in df.iterrows():
                    if 'Duration (min)' in row:
                        duration_minutes = float(row.get('Duration (min)', 1.0))
                    else:
                        # Backward compatibility: older files store seconds.
                        duration_minutes = float(row.get('Duration (s)', 60)) / 60.0
                    step = {
                        'step': int(row.get('Step', idx + 1)),
                        'duration': duration_minutes,
                        'flow_rate': float(row.get('Flow Rate (ml/min)', 0.2)),
                        'measurement_mode': str(row.get('Measurement Mode', 'voltage')).lower(),
                        'valve': str(row.get('Valve', 'main')).lower(),
                        'bias_voltage': float(row.get('Bias Voltage (V)', 0)),
                        'bias_current': float(row.get('Bias Current (A)', 0))
                    }
                    if step['measurement_mode'] not in ['voltage', 'current']:
                        step['measurement_mode'] = 'voltage'
                    if step['valve'] not in ['main', 'rinsing']:
                        step['valve'] = 'main'
                    if step['flow_rate'] > 5.0:
                        step['flow_rate'] = 5.0
                    if step['flow_rate'] < 0:
                        step['flow_rate'] = 0.0
                    self.table_data.append(step)
                
                self.renumber_steps()
                self.update_table_display()
                
                if self.update_queue:
                    self.update_queue.put(('UPDATE_PROGRAM_STATUS', f"Loaded: {filename}"))
        except Exception as e:
            messagebox.showerror('Error', f"Error loading file: {e}")
    
    def save_to_excel(self):
        """Save program to Excel/CSV file"""
        try:
            if not self.table_data:
                messagebox.showwarning('Warning', 'No program data to save.')
                return
            
            filename = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[('Excel Files', '*.xlsx'), ('CSV Files', '*.csv')]
            )
            if filename:
                # Convert table_data to DataFrame
                sorted_data = sorted(self.table_data, key=lambda x: x['step'])
                for s in sorted_data:
                    s.setdefault('bias_voltage', 0.0)
                    s.setdefault('bias_current', 0.0)
                df = pd.DataFrame(sorted_data)
                df = df[['step', 'duration', 'flow_rate', 'measurement_mode', 'valve', 'bias_voltage', 'bias_current']]
                df.columns = ['Step', 'Duration (min)', 'Flow Rate (ml/min)', 'Measurement Mode', 'Valve', 'Bias Voltage (V)', 'Bias Current (A)']
                
                if filename.endswith('.csv'):
                    df.to_csv(filename, index=False)
                else:
                    df.to_excel(filename, index=False)
                
                if self.update_queue:
                    self.update_queue.put(('UPDATE_PROGRAM_STATUS', f"Saved: {filename}"))
        except Exception as e:
            messagebox.showerror('Error', f"Error saving file: {e}")
    
    def load_selected(self):
        """Load selected program template"""
        try:
            selected = self.program_var.get()
            if selected:
                templates = {
                    'Standard Test': [
                        {'step': 1, 'duration': 1.0, 'flow_rate': 0.2, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0},
                        {'step': 2, 'duration': 0.5, 'flow_rate': 2.0, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0},
                        {'step': 3, 'duration': 1.0, 'flow_rate': 0.5, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0}
                    ],
                    'Flow Ramp': [
                        {'step': 1, 'duration': 1.0, 'flow_rate': 0.2, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0},
                        {'step': 2, 'duration': 1.0, 'flow_rate': 0.5, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0},
                        {'step': 3, 'duration': 1.0, 'flow_rate': 1.0, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0},
                        {'step': 4, 'duration': 1.0, 'flow_rate': 1.5, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0}
                    ],
                    'Valve Switching Test': [
                        {'step': 1, 'duration': 1.0, 'flow_rate': 0.2, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0},
                        {'step': 2, 'duration': 0.5, 'flow_rate': 0.2, 'measurement_mode': 'voltage', 'valve': 'rinsing', 'bias_voltage': 0.0, 'bias_current': 0.0},
                        {'step': 3, 'duration': 1.0, 'flow_rate': 0.2, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0}
                    ],
                    'Measurement Mode Switch': [
                        {'step': 1, 'duration': 1.0, 'flow_rate': 0.2, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0},
                        {'step': 2, 'duration': 1.0, 'flow_rate': 0.2, 'measurement_mode': 'current', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0},
                        {'step': 3, 'duration': 1.0, 'flow_rate': 2.0, 'measurement_mode': 'voltage', 'valve': 'main', 'bias_voltage': 0.0, 'bias_current': 0.0}
                    ]
                }
                
                if selected in templates:
                    self.table_data = templates[selected].copy()
                    self.update_table_display()
                    if self.update_queue:
                        self.update_queue.put(('UPDATE_PROGRAM_STATUS', f"Loaded template: {selected}"))
        except Exception as e:
            messagebox.showerror('Error', f"Error loading template: {e}")
    
    def run_program(self):
        """Run program via Main tab (default)."""
        self._last_run_via_resistance = False
        self._run_program_impl(self.main_tab_ref, "Main")

    def run_program_from_resistance_tab(self):
        """Run program via Resistance tab (graphs and recording in Resistance tab)."""
        self._last_run_via_resistance = True
        self._run_program_impl(self.resistance_tab_ref, "Resistance")

    def _run_program_impl(self, tab_ref, tab_name):
        """Run program using the given tab (Main or Resistance). Uses Run name from this tab if set."""
        try:
            experiment_program = self.table_to_program()
            if not experiment_program:
                messagebox.showerror('Error', "No program steps defined. Please add at least one step.")
                return
            if not tab_ref:
                messagebox.showerror('Error',
                    f"{tab_name} tab reference not available. Cannot start recording.")
                return
            # Prefer run name from this tab; otherwise use name from target tab
            run_name = self.run_name_entry.get().strip() if hasattr(self, 'run_name_entry') else ''
            if not run_name:
                run_name = tab_ref.exp_name_entry.get().strip()
            if not run_name:
                messagebox.showwarning('Warning',
                    'Enter a run name here (Run name) or in the {} tab.'.format(tab_name))
                return
            if not re.match(r'^[a-zA-Z0-9_-]+$', run_name):
                messagebox.showerror('Error', 'Run name can only contain letters, numbers, underscores, and hyphens.')
                return
            # Set target tab's experiment name so the run uses this file name
            tab_ref.exp_name_entry.delete(0, 'end')
            tab_ref.exp_name_entry.insert(0, run_name)
            success = tab_ref.start_recording_from_program_tab(experiment_program)
            if success:
                if self.update_queue:
                    self.update_queue.put(('UPDATE_PROGRAM_STATUS',
                        f"Program started via {tab_name} tab: {len(experiment_program)} steps"))
            else:
                messagebox.showerror('Error',
                    'Failed to start program. Please check:\n'
                    '1. Experiment name is valid\n'
                    '2. All program steps are valid')
        except Exception as e:
            messagebox.showerror('Error', f"Error running program: {e}")
            import traceback
            traceback.print_exc()
    
    def _format_time_remaining(self, seconds):
        """Format seconds as 'Xm Ys' or 'Xs'."""
        if seconds is None or seconds < 0:
            return "-"
        s = int(round(seconds))
        if s > 60:
            return f"{s // 60}m {s % 60}s"
        return f"{s}s"

    def update_step_progress(self, step_index, total_steps, step_remaining, step_progress, total_remaining=None):
        """Update step progress widgets. total_remaining = time left for entire program."""
        if hasattr(self, 'step_info_label'):
            self.step_info_label.configure(text=f"Step: {step_index} / {total_steps}")
        
        if hasattr(self, 'step_time_label'):
            self.step_time_label.configure(text=f"Time remaining (step): {self._format_time_remaining(step_remaining)}")
        
        if hasattr(self, 'step_total_time_label'):
            self.step_total_time_label.configure(text=f"Time remaining (total): {self._format_time_remaining(total_remaining)}")
        
        if hasattr(self, 'step_progress_bar'):
            self.step_progress_bar.set(step_progress)
    
    def stop_program(self):
        """Stop program - stops the tab that started it (Main or Resistance)."""
        tab = self.resistance_tab_ref if self._last_run_via_resistance else self.main_tab_ref
        if tab:
            tab.stop_recording()
            tab_name = "Resistance" if self._last_run_via_resistance else "Main"
            if self.update_queue:
                self.update_queue.put(('UPDATE_PROGRAM_STATUS', f"Program stopped via {tab_name} tab"))
        else:
            self.exp_manager.stop_experiment()
            if self.update_queue:
                self.update_queue.put(('UPDATE_PROGRAM_STATUS', "Program stopped"))
