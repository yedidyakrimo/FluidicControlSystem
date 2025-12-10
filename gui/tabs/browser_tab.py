"""
Browser Tab - Experiment browser and comparison
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
import glob
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from gui.tabs.base_tab import BaseTab


class BrowserTab(BaseTab):
    """
    Browser tab for browsing, loading, and comparing experiments
    """
    
    def __init__(self, parent, hw_controller, data_handler, exp_manager, update_queue=None):
        super().__init__(parent, hw_controller, data_handler, exp_manager, update_queue)
        
        # Experiment list tracking
        self.experiment_buttons = []
        self.selected_experiments = []
        
        # Create widgets
        self.create_widgets()
        
        # Initialize experiment list
        self.refresh_experiments()
    
    def create_widgets(self):
        """Create Browser tab widgets"""
        # Search and filter frame
        search_frame = ctk.CTkFrame(self)
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
        
        self.create_blue_button(search_controls, text='Refresh', command=self.refresh_experiments, width=100).pack(side='left', padx=5)
        
        # Experiments list
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Scrollable frame for experiments
        self.exp_list_frame = ctk.CTkScrollableFrame(list_frame)
        self.exp_list_frame.pack(fill='both', expand=True)
        
        # Action buttons
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill='x', padx=10, pady=5)
        
        self.create_blue_button(action_frame, text='Load Selected', command=self.load_experiment, width=150).pack(side='left', padx=5)
        self.create_blue_button(action_frame, text='Compare Selected', command=self.compare_experiments, width=150).pack(side='left', padx=5)
        self.create_blue_button(action_frame, text='Export Selected', command=self.export_selected_experiment, width=150).pack(side='left', padx=5)
    
    def refresh_experiments(self):
        """Refresh the list of experiments from data folder"""
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
            df = pd.read_csv(exp['file'])
            
            # Load data into arrays (these will be shared with MainTab via update_queue)
            # BUG FIX #1: Thread-safe update with lock
            with self.data_lock:
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
                
                # Make copies for queue
                flow_x_copy = list(self.flow_x_data)
                flow_y_copy = list(self.flow_y_data)
                pressure_x_copy = list(self.pressure_x_data)
                pressure_y_copy = list(self.pressure_y_data)
                temp_x_copy = list(self.temp_x_data)
                temp_y_copy = list(self.temp_y_data)
                level_x_copy = list(self.level_x_data)
                level_y_copy = list(self.level_y_data)
            
            # Update graphs via queue (MainTab will handle this)
            if self.update_queue:
                self.update_queue.put(('UPDATE_GRAPH1', (flow_x_copy, flow_y_copy)))
                self.update_queue.put(('UPDATE_GRAPH2', (pressure_x_copy, pressure_y_copy)))
                self.update_queue.put(('UPDATE_GRAPH3', (temp_x_copy, temp_y_copy)))
                self.update_queue.put(('UPDATE_GRAPH4', (level_x_copy, level_y_copy)))
            
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
            titles = ['Flow Rate (ml/min)', 'Pressure (bar)', 'Temperature (°C)', 'Level (%)']
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
                    # Read CSV and export to Excel
                    df = pd.read_csv(selected[0]['file'])
                    df.to_excel(filename, index=False)
                messagebox.showinfo('Success', 'Experiment exported successfully!')
        except Exception as e:
            messagebox.showerror('Error', f"Error exporting experiment: {e}")

