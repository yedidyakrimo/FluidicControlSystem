"""
IV Program Tab - Write and run IV sweep programs
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk, simpledialog
import threading
import time
import pandas as pd

from gui.tabs.base_tab import BaseTab


class IVProgramTab(BaseTab):
    """IV write-program tab with table-based editor."""

    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None):
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        self.table_data = []
        self.iv_program_running = False
        self.iv_stop_requested = False
        self.iv_thread = None
        self.iv_times_min = []
        self.iv_voltages = []
        self.iv_currents = []
        self.create_widgets()

    def create_widgets(self):
        """Create IV program tab widgets."""
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        ctk.CTkLabel(table_frame, text="IV Program Table", font=('Helvetica', 14, 'bold')).pack(pady=5)

        table_container = ctk.CTkFrame(table_frame)
        table_container.pack(fill='both', expand=True, padx=5, pady=5)

        v_scrollbar = ttk.Scrollbar(table_container, orient='vertical')
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar = ttk.Scrollbar(table_container, orient='horizontal')
        h_scrollbar.pack(side='bottom', fill='x')

        self.program_table = ttk.Treeview(
            table_container,
            columns=(
                'Step',
                'Start Voltage (V)',
                'Stop Voltage (V)',
                'Voltage Step (V)',
                'Step Duration (min)',
                'Cycles',
                'Flow Rate (ml/min)',
                'Valve',
                'Current Limit (A)'
            ),
            show='headings',
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            height=12
        )
        v_scrollbar.config(command=self.program_table.yview)
        h_scrollbar.config(command=self.program_table.xview)

        for heading in self.program_table['columns']:
            self.program_table.heading(heading, text=heading)

        self.program_table.column('Step', width=60, anchor='center')
        self.program_table.column('Start Voltage (V)', width=120, anchor='center')
        self.program_table.column('Stop Voltage (V)', width=120, anchor='center')
        self.program_table.column('Voltage Step (V)', width=120, anchor='center')
        self.program_table.column('Step Duration (min)', width=130, anchor='center')
        self.program_table.column('Cycles', width=80, anchor='center')
        self.program_table.column('Flow Rate (ml/min)', width=130, anchor='center')
        self.program_table.column('Valve', width=100, anchor='center')
        self.program_table.column('Current Limit (A)', width=120, anchor='center')
        self.program_table.pack(side='left', fill='both', expand=True)

        self.program_table.bind('<Double-1>', self.on_cell_double_click)
        self.program_table.bind('<Button-1>', self.on_cell_click)

        table_control_frame = ctk.CTkFrame(table_frame)
        table_control_frame.pack(fill='x', padx=5, pady=5)
        self.create_blue_button(table_control_frame, text='➕ Add Step', command=self.add_step_row, width=100).pack(side='left', padx=2)
        self.create_blue_button(table_control_frame, text='➖ Delete Step', command=self.delete_selected_row, width=100).pack(side='left', padx=2)
        self.create_blue_button(table_control_frame, text='🗑️ Clear All', command=self.clear_table, width=100).pack(side='left', padx=2)
        self.create_blue_button(table_control_frame, text='🔄 Renumber Steps', command=self.renumber_steps, width=120).pack(side='left', padx=2)

        control_frame = ctk.CTkFrame(self)
        control_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(control_frame, text="Program Control", font=('Helvetica', 14, 'bold')).pack(pady=5)

        control_btn_frame = ctk.CTkFrame(control_frame)
        control_btn_frame.pack(pady=5)
        self.create_blue_button(control_btn_frame, text='📂 Load from Excel', command=self.load_from_excel, width=140).pack(side='left', padx=5)
        self.create_blue_button(control_btn_frame, text='💾 Save to Excel', command=self.save_to_excel, width=140).pack(side='left', padx=5)
        self.create_blue_button(control_btn_frame, text='▶️ Run Program', command=self.run_program, width=120).pack(side='left', padx=5)
        self.create_blue_button(
            control_btn_frame,
            text='⏹️ Stop Program',
            command=self.stop_program,
            width=120,
            fg_color='#0D47A1',
            hover_color='#0C3A7A'
        ).pack(side='left', padx=5)

        library_frame = ctk.CTkFrame(self)
        library_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(library_frame, text="Program Library", font=('Helvetica', 14, 'bold')).pack(pady=5)

        library_content = ctk.CTkFrame(library_frame)
        library_content.pack(fill='x', padx=5, pady=5)
        self.program_var = ctk.StringVar(value="Single Sweep")
        self.program_optionmenu = ctk.CTkOptionMenu(
            library_content,
            values=["Single Sweep", "Triple Cycle", "Wide Scan"],
            variable=self.program_var,
            width=300
        )
        self.program_optionmenu.pack(side='left', padx=5)
        self.create_blue_button(library_content, text='Load Selected', command=self.load_selected, width=150).pack(side='left', padx=5)

        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(status_frame, text="Program Status", font=('Helvetica', 14, 'bold')).pack(pady=5)

        status_content = ctk.CTkFrame(status_frame)
        status_content.pack(fill='x', padx=5, pady=5)
        ctk.CTkLabel(status_content, text='Status:', width=80).pack(side='left', padx=5)
        self.program_status_label = ctk.CTkLabel(status_content, text='Ready', width=500)
        self.program_status_label.pack(side='left', padx=5)

        step_progress_frame = ctk.CTkFrame(status_frame)
        step_progress_frame.pack(fill='x', padx=5, pady=5)
        self.step_info_label = ctk.CTkLabel(step_progress_frame, text="Step: - / -", font=('Helvetica', 11))
        self.step_info_label.pack(side='left', padx=5)
        self.step_time_label = ctk.CTkLabel(step_progress_frame, text="Time remaining (step): -", font=('Helvetica', 10))
        self.step_time_label.pack(side='left', padx=5)
        self.step_total_time_label = ctk.CTkLabel(step_progress_frame, text="Time remaining (total): -", font=('Helvetica', 10))
        self.step_total_time_label.pack(side='left', padx=5)
        self.step_progress_bar = ctk.CTkProgressBar(step_progress_frame, width=300)
        self.step_progress_bar.pack(side='left', padx=5)
        self.step_progress_bar.set(0)

        self.add_step_row()

    def add_step_row(self):
        """Add a new row to IV program table."""
        step_num = len(self.table_data) + 1
        self.table_data.append({
            'step': step_num,
            'start_voltage': -1.0,
            'stop_voltage': 1.0,
            'step_voltage': 0.1,
            'duration': 0.2,
            'cycles': 1,
            'flow_rate': 1.5,
            'valve': 'main',
            'current_limit': 0.1
        })
        self.update_table_display()

    def delete_selected_row(self):
        """Delete selected row from table."""
        selected = self.program_table.selection()
        if not selected:
            messagebox.showwarning('Warning', 'Please select a row to delete.')
            return
        for item in selected:
            values = self.program_table.item(item, 'values')
            if values:
                step_num = int(values[0])
                self.table_data = [s for s in self.table_data if s['step'] != step_num]
        self.renumber_steps()
        self.update_table_display()

    def clear_table(self):
        """Clear program table."""
        if messagebox.askyesno('Confirm', 'Are you sure you want to clear all steps?'):
            self.table_data.clear()
            self.update_table_display()
            self.add_step_row()

    def renumber_steps(self):
        """Renumber all steps sequentially."""
        for i, step in enumerate(self.table_data, 1):
            step['step'] = i
        self.update_table_display()

    def update_table_display(self):
        """Refresh treeview from table_data."""
        for item in self.program_table.get_children():
            self.program_table.delete(item)

        sorted_data = sorted(self.table_data, key=lambda x: x['step'])
        for step in sorted_data:
            self.program_table.insert('', 'end', values=(
                step['step'],
                step['start_voltage'],
                step['stop_voltage'],
                step['step_voltage'],
                step['duration'],
                step['cycles'],
                step['flow_rate'],
                step['valve'],
                step['current_limit']
            ))

    def on_cell_click(self, event):
        """Handle single click (selection only)."""
        _ = event

    def on_cell_double_click(self, event):
        """Open editor for a double-clicked cell."""
        region = self.program_table.identify_region(event.x, event.y)
        if region != 'cell':
            return
        selected = self.program_table.selection()
        if not selected:
            return
        item = selected[0]
        column = self.program_table.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        values = self.program_table.item(item, 'values')
        if not values:
            return
        step_num = int(values[0])
        step = next((s for s in self.table_data if s['step'] == step_num), None)
        if not step:
            return

        column_names = [
            'Step', 'Start Voltage (V)', 'Stop Voltage (V)', 'Voltage Step (V)',
            'Step Duration (min)', 'Cycles', 'Flow Rate (ml/min)', 'Valve', 'Current Limit (A)'
        ]
        self.edit_cell(column_index, column_names[column_index], step, values[column_index])

    def edit_cell(self, column_index, column_name, step, current_value):
        """Edit a single cell value."""
        if column_index == 0:
            messagebox.showinfo('Info', 'Use "Renumber Steps" button to renumber steps.')
            return

        new_value = simpledialog.askstring(f"Edit {column_name}", f"Enter {column_name}:", initialvalue=str(current_value))
        if new_value is None or not new_value.strip():
            return
        new_value = new_value.strip()

        try:
            if column_name == 'Start Voltage (V)':
                step['start_voltage'] = float(new_value)
            elif column_name == 'Stop Voltage (V)':
                step['stop_voltage'] = float(new_value)
            elif column_name == 'Voltage Step (V)':
                step['step_voltage'] = float(new_value)
            elif column_name == 'Step Duration (min)':
                duration = float(new_value)
                if duration <= 0:
                    raise ValueError("Duration must be > 0")
                step['duration'] = duration
            elif column_name == 'Cycles':
                cycles = int(float(new_value))
                if cycles <= 0:
                    raise ValueError("Cycles must be > 0")
                step['cycles'] = cycles
            elif column_name == 'Flow Rate (ml/min)':
                flow_rate = float(new_value)
                if flow_rate < 0:
                    raise ValueError("Flow rate must be >= 0")
                step['flow_rate'] = min(flow_rate, 5.0)
            elif column_name == 'Valve':
                valve = new_value.lower()
                if valve not in ['main', 'rinsing']:
                    raise ValueError("Valve must be main or rinsing")
                step['valve'] = valve
            elif column_name == 'Current Limit (A)':
                current_limit = float(new_value)
                if current_limit <= 0:
                    raise ValueError("Current limit must be > 0")
                step['current_limit'] = current_limit
        except ValueError as e:
            messagebox.showerror('Error', f'Invalid value: {e}')
            return

        self.update_table_display()

    def load_from_excel(self):
        """Load IV program from Excel/CSV."""
        try:
            filename = filedialog.askopenfilename(
                filetypes=[('Excel Files', '*.xlsx'), ('CSV Files', '*.csv'), ('All Files', '*.*')]
            )
            if not filename:
                return

            if filename.endswith('.csv'):
                df = pd.read_csv(filename)
            else:
                df = pd.read_excel(filename)

            self.table_data.clear()
            for idx, row in df.iterrows():
                step = {
                    'step': int(row.get('Step', idx + 1)),
                    'start_voltage': float(row.get('Start Voltage (V)', -1.0)),
                    'stop_voltage': float(row.get('Stop Voltage (V)', 1.0)),
                    'step_voltage': float(row.get('Voltage Step (V)', 0.1)),
                    'duration': float(row.get('Step Duration (min)', 0.2)),
                    'cycles': int(row.get('Cycles', 1)),
                    'flow_rate': float(row.get('Flow Rate (ml/min)', 1.5)),
                    'valve': str(row.get('Valve', 'main')).lower(),
                    'current_limit': float(row.get('Current Limit (A)', 0.1))
                }
                if step['valve'] not in ['main', 'rinsing']:
                    step['valve'] = 'main'
                if step['flow_rate'] < 0:
                    step['flow_rate'] = 0.0
                if step['flow_rate'] > 5.0:
                    step['flow_rate'] = 5.0
                if step['cycles'] <= 0:
                    step['cycles'] = 1
                if step['duration'] <= 0:
                    step['duration'] = 0.2
                self.table_data.append(step)

            self.renumber_steps()
            self.update_table_display()
            self.update_status(f"Loaded: {filename}", 'green')
        except Exception as e:
            messagebox.showerror('Error', f"Error loading file: {e}")

    def save_to_excel(self):
        """Save IV program to Excel/CSV."""
        try:
            if not self.table_data:
                messagebox.showwarning('Warning', 'No program data to save.')
                return
            filename = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[('Excel Files', '*.xlsx'), ('CSV Files', '*.csv')]
            )
            if not filename:
                return

            sorted_data = sorted(self.table_data, key=lambda x: x['step'])
            df = pd.DataFrame(sorted_data)
            df = df[[
                'step', 'start_voltage', 'stop_voltage', 'step_voltage', 'duration',
                'cycles', 'flow_rate', 'valve', 'current_limit'
            ]]
            df.columns = [
                'Step', 'Start Voltage (V)', 'Stop Voltage (V)', 'Voltage Step (V)',
                'Step Duration (min)', 'Cycles', 'Flow Rate (ml/min)', 'Valve', 'Current Limit (A)'
            ]

            if filename.endswith('.csv'):
                df.to_csv(filename, index=False)
            else:
                df.to_excel(filename, index=False)

            self.update_status(f"Saved: {filename}", 'green')
        except Exception as e:
            messagebox.showerror('Error', f"Error saving file: {e}")

    def load_selected(self):
        """Load a template from IV library."""
        selected = self.program_var.get()
        templates = {
            'Single Sweep': [
                {'step': 1, 'start_voltage': -1.0, 'stop_voltage': 1.0, 'step_voltage': 0.1, 'duration': 0.2, 'cycles': 1, 'flow_rate': 1.5, 'valve': 'main', 'current_limit': 0.1}
            ],
            'Triple Cycle': [
                {'step': 1, 'start_voltage': -1.0, 'stop_voltage': 1.0, 'step_voltage': 0.1, 'duration': 0.15, 'cycles': 3, 'flow_rate': 1.5, 'valve': 'main', 'current_limit': 0.1}
            ],
            'Wide Scan': [
                {'step': 1, 'start_voltage': -2.0, 'stop_voltage': 2.0, 'step_voltage': 0.2, 'duration': 0.1, 'cycles': 2, 'flow_rate': 1.0, 'valve': 'main', 'current_limit': 0.1},
                {'step': 2, 'start_voltage': 2.0, 'stop_voltage': -2.0, 'step_voltage': -0.2, 'duration': 0.1, 'cycles': 1, 'flow_rate': 1.0, 'valve': 'rinsing', 'current_limit': 0.1}
            ]
        }
        if selected in templates:
            self.table_data = [dict(step) for step in templates[selected]]
            self.update_table_display()
            self.update_status(f"Loaded template: {selected}", 'green')

    def _build_voltage_points(self, start_val, stop_val, step_val):
        """Build safe voltage list with direction/step validation."""
        if start_val == stop_val:
            return [start_val]
        if step_val == 0:
            raise ValueError("Voltage step must not be zero when start and stop differ.")
        if start_val < stop_val and step_val < 0:
            raise ValueError("Voltage step must be positive for ascending sweep.")
        if start_val > stop_val and step_val > 0:
            raise ValueError("Voltage step must be negative for descending sweep.")

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

    def _format_time_remaining(self, seconds):
        """Format seconds as Xm Ys."""
        if seconds is None or seconds < 0:
            return "-"
        s = int(round(seconds))
        if s > 60:
            return f"{s // 60}m {s % 60}s"
        return f"{s}s"

    def update_step_progress(self, step_index, total_steps, step_remaining, step_progress, total_remaining=None):
        """Update local progress controls."""
        self.after(0, lambda: self.step_info_label.configure(text=f"Step: {step_index} / {total_steps}"))
        self.after(0, lambda: self.step_time_label.configure(text=f"Time remaining (step): {self._format_time_remaining(step_remaining)}"))
        self.after(0, lambda: self.step_total_time_label.configure(text=f"Time remaining (total): {self._format_time_remaining(total_remaining)}"))
        self.after(0, lambda: self.step_progress_bar.set(max(0.0, min(1.0, step_progress))))

    def run_program(self):
        """Start IV program execution thread."""
        if self.iv_program_running:
            messagebox.showinfo('In progress', 'IV program already running.')
            return
        if not self.table_data:
            messagebox.showerror('Error', 'No program steps defined.')
            return

        self.iv_stop_requested = False
        self.iv_program_running = True
        self.iv_times_min.clear()
        self.iv_voltages.clear()
        self.iv_currents.clear()
        self.iv_thread = threading.Thread(target=self._run_program_thread, daemon=True)
        self.iv_thread.start()

    def stop_program(self):
        """Request stop for the running IV program."""
        self.iv_stop_requested = True
        if self.iv_program_running:
            self.update_status('Stopping program...', 'orange')
            if self.update_queue:
                self.update_queue.put(('UPDATE_IV_STATUS', ('Stopping...', 'orange')))
                self.update_queue.put(('UPDATE_IV_STATUS_BAR', 'Stopping IV program...'))

    def _run_program_thread(self):
        """Run IV program step-by-step."""
        start_time = time.time()
        sample_interval_s = 0.5
        settling_time_s = 0.5
        total_step_units = 0

        try:
            sorted_steps = sorted(self.table_data, key=lambda x: x['step'])
            for row in sorted_steps:
                points = self._build_voltage_points(row['start_voltage'], row['stop_voltage'], row['step_voltage'])
                total_step_units += len(points) * max(1, int(row['cycles']))

            if total_step_units <= 0:
                raise ValueError("Program has no executable IV points.")

            self.data_handler.create_new_file()
            self.exp_manager.is_running = True
            self.update_status('Running IV program...', 'orange')
            if self.update_queue:
                self.update_queue.put(('UPDATE_IV_STATUS', ('Running program...', 'orange')))

            completed_units = 0
            for row_index, row in enumerate(sorted_steps, start=1):
                if self.iv_stop_requested:
                    break

                start_v = float(row['start_voltage'])
                stop_v = float(row['stop_voltage'])
                step_v = float(row['step_voltage'])
                dwell_min = float(row['duration'])
                cycles = int(row['cycles'])
                flow_rate = min(5.0, max(0.0, float(row['flow_rate'])))
                current_limit = float(row['current_limit'])
                valve_main = str(row['valve']).lower() == 'main'

                if dwell_min <= 0:
                    raise ValueError(f"Step {row_index}: duration must be greater than 0.")
                if cycles <= 0:
                    raise ValueError(f"Step {row_index}: cycles must be greater than 0.")
                if current_limit <= 0:
                    raise ValueError(f"Step {row_index}: current limit must be greater than 0.")

                voltage_points = self._build_voltage_points(start_v, stop_v, step_v)
                self.hw_controller.setup_smu_for_iv_measurement(current_limit)
                self.hw_controller.set_pump_flow_rate(flow_rate)
                self.hw_controller.set_valves(valve_main, not valve_main)
                self.hw_controller.start_pump()

                for cycle_index in range(1, cycles + 1):
                    if self.iv_stop_requested:
                        break
                    for point_index, voltage in enumerate(voltage_points, start=1):
                        if self.iv_stop_requested:
                            break

                        self.hw_controller.set_smu_voltage(voltage, current_limit)
                        if point_index > 1 or cycle_index > 1:
                            time.sleep(settling_time_s)

                        dwell_seconds = dwell_min * 60.0
                        point_start = time.time()
                        while (time.time() - point_start) < dwell_seconds and not self.iv_stop_requested:
                            measured_current = self._read_iv_current_only()
                            if measured_current is None:
                                time.sleep(sample_interval_s)
                                continue
                            measured_voltage = voltage
                            elapsed_time = time.time() - start_time
                            elapsed_time_min = elapsed_time / 60.0

                            self.iv_times_min.append(elapsed_time_min)
                            self.iv_voltages.append(measured_voltage)
                            self.iv_currents.append(measured_current)
                            self.data_handler.append_data({
                                "time": elapsed_time,
                                "flow_setpoint": flow_rate,
                                "pump_flow_read": flow_rate,
                                "pressure_read": "",
                                "temp_read": "",
                                "level_read": "",
                                "program_step": f"{row_index}.{cycle_index}",
                                "voltage": measured_voltage,
                                "current": measured_current,
                                "target_voltage": voltage
                            })

                            progress = completed_units / total_step_units
                            point_elapsed = time.time() - point_start
                            step_remaining = max(0.0, dwell_seconds - point_elapsed)
                            estimated_total = max(0.0, (total_step_units - completed_units) * dwell_seconds - point_elapsed)
                            self.update_step_progress(row_index, len(sorted_steps), step_remaining, progress, estimated_total)

                            if self.update_queue:
                                self.update_queue.put(('UPDATE_IV_GRAPH', (list(self.iv_voltages), list(self.iv_currents))))
                                self.update_queue.put((
                                    'UPDATE_IV_TIME_GRAPH',
                                    (list(self.iv_times_min), list(self.iv_voltages), list(self.iv_currents))
                                ))
                                self.update_queue.put((
                                    'UPDATE_IV_STATUS_BAR',
                                    f"Step {row_index}/{len(sorted_steps)} Cycle {cycle_index}/{cycles}: "
                                    f"V={voltage:.3f}V, I={measured_current:.3e}A"
                                ))
                            time.sleep(sample_interval_s)

                        completed_units += 1

            if self.iv_stop_requested:
                self.update_status('Stopped', 'orange')
                if self.update_queue:
                    self.update_queue.put(('UPDATE_IV_STATUS', ('Stopped', 'orange')))
                    self.update_queue.put(('UPDATE_IV_STATUS_BAR', 'IV program stopped by user'))
            else:
                self.update_status('Completed', 'green')
                if self.update_queue:
                    self.update_queue.put(('UPDATE_IV_STATUS', ('Completed', 'green')))
                    self.update_queue.put(('UPDATE_IV_STATUS_BAR', 'IV program completed'))

        except Exception as exc:
            self.update_status(f'Error: {exc}', 'red')
            if self.update_queue:
                self.update_queue.put(('UPDATE_IV_STATUS', ('Error', 'red')))
                self.update_queue.put(('UPDATE_IV_STATUS_BAR', f'IV program error: {exc}'))
        finally:
            self.iv_program_running = False
            self.iv_stop_requested = False
            self.exp_manager.is_running = False
            try:
                self.hw_controller.stop_pump()
            except Exception:
                pass
            try:
                self.hw_controller.stop_smu()
            except Exception:
                pass
            try:
                self.data_handler.close_file()
            except Exception:
                pass

    def update_status(self, text, color='black'):
        """Update status label safely from any thread."""
        self.after(0, lambda: self.program_status_label.configure(text=text, text_color=color))

    def _read_iv_current_only(self):
        """Read only current from SMU in IV mode (voltage is setpoint)."""
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
        except Exception:
            return None

