"""
IV Write Program Tab - Define voltage jumps programmatically
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import time

from gui.tabs.base_tab import BaseTab


class IVProgramTab(BaseTab):
    """
    Tab that lets the user define voltage-duration steps and run them on the SMU
    while keeping the IV graph in sync.
    """

    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None):
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        self.iv_step_running = False
        self.iv_stop_requested = False
        self.iv_thread = None
        self.iv_voltages = []
        self.iv_currents = []
        self.create_widgets()

    def create_widgets(self):
        """Create IV write program widgets."""
        editor_frame = ctk.CTkFrame(self)
        editor_frame.pack(fill='both', expand=True, padx=10, pady=5)

        ctk.CTkLabel(editor_frame, text="I-V Write Program", font=('Helvetica', 14, 'bold')).pack(pady=5)

        self.program_editor = ctk.CTkTextbox(editor_frame, width=800, height=320)
        program_template = '''# Define I-V steps (voltage in V, duration in seconds)
# step1: voltage=0.0, duration=5
# step2: voltage=0.5, duration=5
# step3: voltage=1.0, duration=5
# step4: voltage=0.0, duration=5
# Use '# ' for comments and keep voltage/duration values numeric.
'''
        self.program_editor.insert('1.0', program_template)
        self.program_editor.pack(fill='both', expand=True, padx=5, pady=5)

        control_frame = ctk.CTkFrame(self)
        control_frame.pack(fill='x', padx=10, pady=5)

        btn_frame = ctk.CTkFrame(control_frame)
        btn_frame.pack(pady=5)
        self.create_blue_button(btn_frame, text='Load Program', command=self.load_program, width=110).pack(side='left', padx=4)
        self.create_blue_button(btn_frame, text='Save Program', command=self.save_program, width=110).pack(side='left', padx=4)
        self.create_blue_button(btn_frame, text='Run Program', command=self.run_program, width=110).pack(side='left', padx=4)
        self.create_blue_button(btn_frame, text='Stop Program', command=self.stop_program, width=110,
                                fg_color='#0D47A1', hover_color='#0C3A7A').pack(side='left', padx=4)

        params_frame = ctk.CTkFrame(self)
        params_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(params_frame, text='Current limit (A):').grid(row=0, column=0, padx=5, pady=2, sticky='w')
        self.current_limit_entry = ctk.CTkEntry(params_frame, width=100)
        self.current_limit_entry.insert(0, '0.1')
        self.current_limit_entry.grid(row=0, column=1, padx=5, pady=2, sticky='w')

        ctk.CTkLabel(params_frame, text='Jump size (V):').grid(row=0, column=2, padx=5, pady=2, sticky='w')
        self.jump_size_entry = ctk.CTkEntry(params_frame, width=100)
        self.jump_size_entry.insert(0, '0.1')
        self.jump_size_entry.grid(row=0, column=3, padx=5, pady=2, sticky='w')

        ctk.CTkLabel(params_frame, text='Samples/sec:').grid(row=1, column=0, padx=5, pady=2, sticky='w')
        self.sample_rate_entry = ctk.CTkEntry(params_frame, width=100)
        self.sample_rate_entry.insert(0, '3')
        self.sample_rate_entry.grid(row=1, column=1, padx=5, pady=2, sticky='w')

        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(status_frame, text="IV Program Status", font=('Helvetica', 14, 'bold')).pack(pady=5)
        self.program_status_label = ctk.CTkLabel(status_frame, text='Ready', width=400)
        self.program_status_label.pack(pady=5)

    def load_program(self):
        """Load program from file."""
        try:
            filename = filedialog.askopenfilename(filetypes=[('Text Files', '*.txt')])
            if filename:
                with open(filename, 'r', encoding='utf-8') as f:
                    program_text = f.read()
                self.program_editor.delete('1.0', 'end')
                self.program_editor.insert('1.0', program_text)
                self.update_status("Loaded program", 'blue')
        except Exception as e:
            messagebox.showerror('Error', f"Error loading program: {e}")

    def save_program(self):
        """Save program to file."""
        try:
            program_text = self.program_editor.get('1.0', 'end-1c')
            filename = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text Files', '*.txt')])
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(program_text)
                self.update_status("Saved program", 'green')
        except Exception as e:
            messagebox.showerror('Error', f"Error saving program: {e}")

    def parse_program(self, program_text):
        """Parse the user-defined I-V program (targets only)."""
        targets = []
        for line in program_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' not in line:
                continue
            try:
                _, body = line.split(':', 1)
                kv_pairs = [part.strip() for part in body.split(',') if '=' in part]
                for part in kv_pairs:
                    key, value = part.split('=', 1)
                    if key.strip().lower() == 'voltage':
                        targets.append(float(value.strip()))
                        break
            except ValueError as err:
                print(f"Skipping line due to parse error: {line} ({err})")
                continue
        return targets

    def run_program(self):
        """Run the IV write program."""
        if self.iv_step_running:
            messagebox.showinfo('In progress', 'IV program already running.')
            return
        program_text = self.program_editor.get('1.0', 'end-1c')
        targets = self.parse_program(program_text)
        if not targets:
            messagebox.showerror('Error', 'No valid target voltages found. Define at least one voltage.')
            return
        try:
            current_limit = float(self.current_limit_entry.get())
        except ValueError:
            messagebox.showerror('Error', 'Invalid current limit.')
            return
        try:
            jump_size = float(self.jump_size_entry.get())
            if jump_size <= 0:
                raise ValueError("Jump size must be positive")
        except ValueError:
            messagebox.showerror('Error', 'Invalid jump size.')
            return
        try:
            sample_rate = float(self.sample_rate_entry.get())
            if sample_rate <= 0:
                raise ValueError("Sample rate must be positive")
        except ValueError:
            messagebox.showerror('Error', 'Invalid samples/sec.')
            return
        self.iv_stop_requested = False
        self.iv_step_running = True
        self.iv_voltages.clear()
        self.iv_currents.clear()
        self.data_handler.create_new_file()
        self.exp_manager.is_running = True
        self.update_status('Running I-V program…', 'orange')
        self.iv_thread = threading.Thread(
            target=self._run_program_thread,
            args=(targets, current_limit, jump_size, sample_rate),
            daemon=True
        )
        self.iv_thread.start()

    def stop_program(self):
        """Stop the running IV program."""
        self.iv_stop_requested = True
        if self.iv_step_running:
            self.update_status('Stopping program…', 'orange')
        self.exp_manager.stop_experiment()

    def _run_program_thread(self, targets, current_limit, jump_size, sample_rate):
        """Thread worker for running the IV program."""
        sample_interval = max(0.02, 1.0 / sample_rate)
        try:
            if self.hw_controller.smu:
                self.hw_controller.setup_smu_for_iv_measurement(current_limit)
            program_start_time = time.time()
            current_voltage = None
            measurement = self.hw_controller.measure_smu() if self.hw_controller.smu else None
            if measurement:
                current_voltage = measurement['voltage']
            else:
                current_voltage = targets[0]

            for idx, target_voltage in enumerate(targets):
                if self.iv_stop_requested:
                    break
                step_label = f"{idx+1}/{len(targets)}"
                direction = 1 if target_voltage > current_voltage else -1
                while not self.iv_stop_requested and (
                    (direction > 0 and current_voltage < target_voltage - 1e-6) or
                    (direction < 0 and current_voltage > target_voltage + 1e-6)
                ):
                    next_voltage = current_voltage + direction * jump_size
                    if direction > 0:
                        next_voltage = min(next_voltage, target_voltage)
                    else:
                        next_voltage = max(next_voltage, target_voltage)
                    if self.hw_controller.smu:
                        self.hw_controller.set_smu_voltage(next_voltage, current_limit)
                    time.sleep(sample_interval)
                    measurement = self.hw_controller.measure_smu()
                    measured_voltage = measurement['voltage'] if measurement else next_voltage
                    current_reading = measurement['current'] if measurement else 0.0
                    current_voltage = measured_voltage
                    self._record_iv_measurement(
                        program_start_time, step_label, target_voltage,
                        measured_voltage, current_reading
                    )
                if self.iv_stop_requested:
                    break
                if self.hw_controller.smu:
                    self.hw_controller.set_smu_voltage(target_voltage, current_limit)
                time.sleep(sample_interval)
                measurement = self.hw_controller.measure_smu()
                measured_voltage = measurement['voltage'] if measurement else target_voltage
                current_reading = measurement['current'] if measurement else 0.0
                current_voltage = measured_voltage
                self._record_iv_measurement(
                    program_start_time, step_label, target_voltage,
                    measured_voltage, current_reading
                )
        except Exception as exc:
            print(f"Error running IV program: {exc}")
            self.update_status('Error during run', 'red')
        finally:
            self.iv_step_running = False
            self.iv_stop_requested = False
            self.exp_manager.is_running = False
            try:
                self.data_handler.close_file()
            except Exception as err:
                print(f"Error closing IV program file: {err}")
            self.hw_controller.stop_smu()
            self.update_status('Ready', 'green')
            if self.update_queue:
                self.update_queue.put(('UPDATE_IV_STATUS', ('Ready', 'green')))
                self.update_queue.put(('UPDATE_IV_STATUS_BAR', 'I-V program completed.'))

    def _record_iv_measurement(self, start_time, step_label, target_voltage, measured_voltage, current_reading):
        timestamp = time.time() - start_time
        self.iv_voltages.append(measured_voltage)
        self.iv_currents.append(current_reading)
        data_point = {
            "time": timestamp,
            "flow_setpoint": "",
            "pump_flow_read": "",
            "pressure_read": "",
            "temp_read": "",
            "level_read": "",
            "program_step": step_label,
            "voltage": measured_voltage,
            "current": current_reading,
            "target_voltage": target_voltage
        }
        self.data_handler.append_data(data_point)
        if self.update_queue:
            self.update_queue.put(('UPDATE_IV_GRAPH', (list(self.iv_voltages), list(self.iv_currents))))
            self.update_queue.put(('UPDATE_IV_STATUS_BAR',
                                   f"Target {target_voltage:.3f} V ({step_label}): {measured_voltage:.3f} V, {current_reading:.3e} A"))

    def update_status(self, text, color='black'):
        """Update the status label from any thread."""
        def updater():
            self.program_status_label.configure(text=text, text_color=color)
        self.after(0, updater)

