"""
Graph widget for displaying real-time data
"""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import customtkinter as ctk
import numpy as np


class GraphWidget(ctk.CTkFrame):
    """
    Widget for displaying matplotlib graphs
    """
    
    def __init__(self, parent, title="Graph", xlabel="X", ylabel="Y", color='#2E86AB'):
        """
        Initialize graph widget
        
        Args:
            parent: Parent widget
            title: Graph title
            xlabel: X-axis label
            ylabel: Y-axis label
            color: Line color
        """
        super().__init__(parent)
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.color = color
        
        # Create figure
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.ax.set_xlabel(self.xlabel, color='black', fontsize=10)
        self.ax.set_ylabel(self.ylabel, color='black', fontsize=10)
        self.ax.set_title(self.title, color='black', fontsize=12, fontweight='bold', pad=10)
        self.ax.set_facecolor('white')
        self.ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.ax.set_axisbelow(True)
        self.ax.tick_params(colors='black', labelsize=9)
        for spine in self.ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side='top', fill='both', expand=1)
        
        # Add navigation toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
    
    def update_data(self, x_data, y_data):
        """
        Update graph with new data
        
        Args:
            x_data: X-axis data
            y_data: Y-axis data
        """
        self.ax.clear()
        if len(x_data) > 0 and len(y_data) > 0:
            self.ax.plot(x_data, y_data, color=self.color, linewidth=2, alpha=0.85)
        self.ax.set_xlabel(self.xlabel, color='black', fontsize=10)
        self.ax.set_ylabel(self.ylabel, color='black', fontsize=10)
        self.ax.set_title(self.title, color='black', fontsize=12, fontweight='bold', pad=10)
        self.ax.set_facecolor('white')
        self.ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.ax.set_axisbelow(True)
        self.ax.tick_params(colors='black', labelsize=9)
        for spine in self.ax.spines.values():
            spine.set_color('black')
            spine.set_linewidth(1)
        self.canvas.draw()
    
    def clear(self):
        """Clear graph"""
        self.ax.clear()
        self.ax.set_xlabel(self.xlabel, color='black', fontsize=10)
        self.ax.set_ylabel(self.ylabel, color='black', fontsize=10)
        self.ax.set_title(self.title, color='black', fontsize=12, fontweight='bold', pad=10)
        self.ax.set_facecolor('white')
        self.ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.canvas.draw()


class MultiPanelGraphWidget(ctk.CTkFrame):
    """
    Widget for displaying multiple graphs in a grid
    """
    
    def __init__(self, parent, graphs_config):
        """
        Initialize multi-panel graph widget
        
        Args:
            parent: Parent widget
            graphs_config: List of tuples (title, ylabel, color) for each graph
        """
        super().__init__(parent)
        
        # Create figure with subplots
        n_graphs = len(graphs_config)
        if n_graphs == 4:
            self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(12, 10))
            self.axes = [self.ax1, self.ax2, self.ax3, self.ax4]
        else:
            # Fallback for other numbers
            rows = int(np.ceil(np.sqrt(n_graphs)))
            cols = int(np.ceil(n_graphs / rows))
            self.fig, axes = plt.subplots(rows, cols, figsize=(12, 10))
            if n_graphs == 1:
                self.axes = [axes]
            else:
                self.axes = axes.flatten() if hasattr(axes, 'flatten') else [axes]
        
        # Configure each subplot
        for i, (ax, (title, ylabel, color)) in enumerate(zip(self.axes, graphs_config)):
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
        
        self.graphs_config = graphs_config
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side='top', fill='both', expand=1)
        
        # Add navigation toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
    
    def update_data(self, data_dict):
        """
        Update graphs with new data
        
        Args:
            data_dict: Dictionary with keys matching graph titles and values as (x_data, y_data) tuples
        """
        for i, (title, _, color) in enumerate(self.graphs_config):
            if title in data_dict:
                x_data, y_data = data_dict[title]
                self.axes[i].clear()
                if len(x_data) > 0 and len(y_data) > 0:
                    self.axes[i].plot(x_data, y_data, color=color, linewidth=2, alpha=0.85)
                self.axes[i].set_xlabel("Time (s)", color='black', fontsize=10)
                self.axes[i].set_ylabel(self.graphs_config[i][1], color='black', fontsize=10)
                self.axes[i].set_title(title, color='black', fontsize=12, fontweight='bold', pad=10)
                self.axes[i].set_facecolor('white')
                self.axes[i].grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
                self.axes[i].set_axisbelow(True)
        self.canvas.draw()
    
    def clear(self):
        """Clear all graphs"""
        for ax in self.axes:
            ax.clear()
            ax.set_facecolor('white')
            ax.grid(True, alpha=0.4, color='gray', linestyle='-', linewidth=0.5)
        self.canvas.draw()

