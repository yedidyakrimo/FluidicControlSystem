"""
Scheduler Tab - Schedule experiments for future execution
"""

import customtkinter as ctk
from tkinter import messagebox
import os
import json
from datetime import datetime

from gui.tabs.base_tab import BaseTab


class SchedulerTab(BaseTab):
    """
    Scheduler tab for scheduling experiments
    """
    
    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None):
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        
        # Scheduled experiments tracking
        self.scheduled_items = []
        self.refresh_job = None
        
        # Create widgets
        self.create_widgets()
        
        # Initialize scheduled experiments list
        self.refresh_job = self.after(100, self.refresh_scheduled_experiments)
    
    def create_widgets(self):
        """Create Scheduler tab widgets"""
        # Schedule experiment frame
        schedule_frame = ctk.CTkFrame(self)
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
        scheduled_frame = ctk.CTkFrame(self)
        scheduled_frame.pack(fill='both', expand=True, padx=10, pady=5)
        ctk.CTkLabel(scheduled_frame, text="Scheduled Experiments", font=('Helvetica', 14, 'bold')).pack(pady=5)
        
        self.scheduled_list_frame = ctk.CTkScrollableFrame(scheduled_frame)
        self.scheduled_list_frame.pack(fill='both', expand=True)
        
        # Action buttons
        schedule_action_frame = ctk.CTkFrame(self)
        schedule_action_frame.pack(fill='x', padx=10, pady=5)
        
        self.create_blue_button(schedule_action_frame, text='Schedule Experiment', command=self.schedule_experiment, width=150).pack(side='left', padx=5)
        self.create_blue_button(schedule_action_frame, text='Remove Selected', command=self.remove_scheduled, width=150).pack(side='left', padx=5)
        self.create_blue_button(schedule_action_frame, text='Clear All', command=self.clear_scheduled, width=150).pack(side='left', padx=5)
    
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
                schedule_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
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
                with open(schedule_file, 'r') as f:
                    schedules = json.load(f)
            
            schedule_info = {
                'datetime': schedule_datetime.isoformat(),
                'program': self.schedule_program_var.get(),
                'created': datetime.now().isoformat()
            }
            schedules.append(schedule_info)
            
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
        
        self.scheduled_items.clear()
        
        schedule_file = os.path.join(self.data_handler.data_folder, 'schedules.json')
        if not os.path.exists(schedule_file):
            return
        
        try:
            with open(schedule_file, 'r') as f:
                schedules = json.load(f)
            
            for idx, schedule in enumerate(schedules):
                schedule_frame = ctk.CTkFrame(self.scheduled_list_frame)
                schedule_frame.pack(fill='x', padx=5, pady=2)
                
                # Checkbox for selection
                var = ctk.BooleanVar()
                checkbox = ctk.CTkCheckBox(schedule_frame, text="", variable=var)
                checkbox.pack(side='left', padx=5)
                
                schedule_datetime = datetime.fromisoformat(schedule['datetime'])
                info_text = f"{schedule_datetime.strftime('%Y-%m-%d %H:%M')} - {schedule['program']}"
                ctk.CTkLabel(schedule_frame, text=info_text, anchor='w').pack(side='left', fill='x', expand=True, padx=5)
                
                self.scheduled_items.append({
                    'frame': schedule_frame,
                    'checkbox': checkbox,
                    'var': var,
                    'index': idx,
                    'schedule': schedule
                })
        except Exception as e:
            print(f"Error loading schedules: {e}")
    
    def remove_scheduled(self):
        """Remove selected scheduled experiment"""
        selected = [item for item in self.scheduled_items if item['var'].get()]
        if not selected:
            messagebox.showwarning('Warning', 'Please select a scheduled experiment to remove.')
            return
        
        try:
            schedule_file = os.path.join(self.data_handler.data_folder, 'schedules.json')
            if not os.path.exists(schedule_file):
                return
            
            with open(schedule_file, 'r') as f:
                schedules = json.load(f)
            
            # Remove selected items (in reverse order to maintain indices)
            for item in sorted(selected, key=lambda x: x['index'], reverse=True):
                schedules.pop(item['index'])
            
            with open(schedule_file, 'w') as f:
                json.dump(schedules, f, indent=2)
            
            self.refresh_scheduled_experiments()
            messagebox.showinfo('Success', f'Removed {len(selected)} scheduled experiment(s)')
        except Exception as e:
            messagebox.showerror('Error', f"Error removing scheduled experiment: {e}")
    
    def clear_scheduled(self):
        """Clear all scheduled experiments"""
        if messagebox.askyesno('Confirm', 'Are you sure you want to clear all scheduled experiments?'):
            schedule_file = os.path.join(self.data_handler.data_folder, 'schedules.json')
            if os.path.exists(schedule_file):
                os.remove(schedule_file)
            self.refresh_scheduled_experiments()
            messagebox.showinfo('Success', 'All scheduled experiments cleared.')
    
    def cleanup(self):
        """Cleanup when tab is closed"""
        if self.refresh_job:
            try:
                self.after_cancel(self.refresh_job)
            except:
                pass
            self.refresh_job = None

