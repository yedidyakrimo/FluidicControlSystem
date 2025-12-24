# data_handler.py

import csv
from datetime import datetime
import os  # Library for interacting with the operating system, used here for file paths.
import pandas as pd  # For Excel export functionality


# This class handles saving data to a file.
class DataHandler:
    # The constructor.
    def __init__(self, data_folder="data"):
        # We will create a 'data' folder to store all experiment files.
        self.data_folder = data_folder
        self.file_path = None  # This will store the path to the current file.
        self.file = None
        self.writer = None
        self.custom_filename = None  # Store custom filename for recording
        self.metadata = None  # Store experiment metadata

        # Check if the data folder exists; if not, create it.
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            print(f"Created data folder: {self.data_folder}")

    def set_custom_filename(self, filename):
        """
        Set custom filename for recording
        filename: The base filename (without extension)
        """
        self.custom_filename = filename
        print(f"Custom filename set to: {filename}")
    
    def set_metadata(self, metadata):
        """
        Set experiment metadata
        metadata: Dictionary with experiment metadata (name, description, tags, operator, etc.)
        """
        self.metadata = metadata
        print(f"Metadata set: {metadata}")

    # This function creates a new CSV file for a new experiment.
    def create_new_file(self):
        # Generate a unique filename using the current timestamp.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Use custom filename if set, otherwise use default
        if self.custom_filename:
            filename = f"{self.custom_filename}_{timestamp}.csv"
        else:
            filename = f"experiment_data_{timestamp}.csv"
            
        self.file_path = os.path.join(self.data_folder, filename)

        # Open the file in write mode ('w') with a newline='' argument to prevent empty rows.
        self.file = open(self.file_path, 'w', newline='')
        
        # Write metadata as comments at the beginning of the file
        if self.metadata:
            self.file.write("# Experiment Metadata\n")
            for key, value in self.metadata.items():
                if isinstance(value, list):
                    value = ','.join(str(v) for v in value)
                self.file.write(f"# {key}: {value}\n")
            self.file.write("#\n")
        
        # Create a CSV writer object.
        self.writer = csv.DictWriter(self.file, fieldnames=[
            "measurement_id",
            "time",
            "flow_setpoint",
            "pump_flow_read",
            "pressure_read",
            "temp_read",
            "level_read",
            "program_step",
            "voltage",
            "current",
            "target_voltage"
            # We can add more fieldnames here for other sensors if needed.
        ])

        # Write the header row to the CSV file.
        self.writer.writeheader()
        
        # Save metadata to separate JSON file
        if self.metadata:
            metadata_file = self.file_path.replace('.csv', '_metadata.json')
            import json
            with open(metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        
        print(f"New data file created at: {self.file_path}")

    # This function appends a new data point (a dictionary) to the CSV file.
    def append_data(self, data_point):
        if self.writer and data_point:
            try:
                self.writer.writerow(data_point)
                # You can add a print statement for debugging if needed:
                # print(f"Appended data: {data_point}")
            except Exception as e:
                print(f"Error writing data: {e}")
        elif not self.writer:
            print("Warning: No file open for writing data")

    def log_flow_change(self, new_flow_rate):
        """
        Log a flow rate change to the data file
        new_flow_rate: The new flow rate value
        """
        if self.writer:
            try:
                # Create a special data point to mark flow change
                flow_change_data = {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "flow_setpoint": new_flow_rate,
                    "pump_flow_read": "FLOW_CHANGE",
                    "pressure_read": "",
                    "temp_read": "",
                    "level_read": "",
                    "program_step": "FLOW_UPDATE",
                    "voltage": "",
                    "current": ""
                }
                self.writer.writerow(flow_change_data)
                print(f"Flow rate change logged: {new_flow_rate} ml/min")
            except Exception as e:
                print(f"Error logging flow change: {e}")
        else:
            print("Warning: No file open for logging flow change")

    # This function closes the file. It's crucial to call this at the end of every experiment.
    def close_file(self):
        if self.file:
            self.file.close()
            self.file = None
            self.writer = None
            print(f"Data file closed.")

    def export_to_excel(self, output_path=None):
        """
        Export the current CSV data to Excel format
        output_path: Optional path for Excel file. If None, uses same name as CSV with .xlsx extension
        """
        if not self.file_path or not os.path.exists(self.file_path):
            print("No data file to export. Run an experiment first.")
            return False
        
        try:
            # Ensure file is closed before reading
            if self.file:
                self.file.flush()
            
            # Read the CSV file, skipping comment lines that start with #
            df = pd.read_csv(self.file_path, comment='#')
            
            # Check if file is empty or has no valid data
            if df.empty or len(df) == 0:
                print("CSV file is empty. No data to export.")
                return False
            
            # Generate output path if not provided
            if output_path is None:
                output_path = self.file_path.replace('.csv', '.xlsx')
            
            # Ensure output path has .xlsx extension
            if not output_path.endswith('.xlsx'):
                output_path += '.xlsx'
            
            # Create Excel writer with formatting
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Write data to Excel
                df.to_excel(writer, sheet_name='Experiment Data', index=False)
                
                # Get the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Experiment Data']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Add summary sheet
                summary_data = {
                    'Parameter': ['Total Data Points', 'Experiment Duration (s)', 'Average Flow Rate', 'Max Pressure', 'Min Temperature', 'Max Level'],
                    'Value': [
                        len(df),
                        f"{df['time'].iloc[-1] - df['time'].iloc[0]:.2f}" if len(df) > 1 and 'time' in df.columns else "0",
                        f"{df['pump_flow_read'].mean():.2f}" if 'pump_flow_read' in df.columns and pd.notna(df['pump_flow_read']).any() else "N/A",
                        f"{df['pressure_read'].max():.2f}" if 'pressure_read' in df.columns and pd.notna(df['pressure_read']).any() else "N/A",
                        f"{df['temp_read'].min():.2f}" if 'temp_read' in df.columns and pd.notna(df['temp_read']).any() else "N/A",
                        f"{df['level_read'].max():.2f}" if 'level_read' in df.columns and pd.notna(df['level_read']).any() else "N/A"
                    ]
                }
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            print(f"Data exported to Excel: {output_path}")
            return True
            
        except pd.errors.EmptyDataError:
            print("CSV file contains no data rows (only comments or headers).")
            return False
        except pd.errors.ParserError as e:
            print(f"Error parsing CSV file: {e}")
            return False
        except PermissionError:
            print(f"Permission denied: Cannot write to {output_path}. File may be open in another program.")
            return False
        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            import traceback
            traceback.print_exc()
            return False

    def export_iv_to_excel(self, voltage_data, current_data, output_path=None):
        """
        Export I-V measurement data to Excel
        voltage_data: List of voltage values
        current_data: List of current values
        output_path: Optional path for Excel file
        """
        try:
            # Create DataFrame from I-V data
            df = pd.DataFrame({
                'Voltage (V)': voltage_data,
                'Current (A)': current_data,
                'Resistance (Ohm)': [v/i if i != 0 else float('inf') for v, i in zip(voltage_data, current_data)]
            })
            
            # Generate output path if not provided
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(self.data_folder, f"iv_measurement_{timestamp}.xlsx")
            
            # Create Excel writer
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Write I-V data
                df.to_excel(writer, sheet_name='I-V Data', index=False)
                
                # Add I-V curve plot (basic statistics)
                stats_data = {
                    'Parameter': ['Data Points', 'Voltage Range (V)', 'Current Range (A)', 'Max Resistance (Ohm)', 'Min Resistance (Ohm)'],
                    'Value': [
                        len(df),
                        f"{df['Voltage (V)'].min():.3f} to {df['Voltage (V)'].max():.3f}",
                        f"{df['Current (A)'].min():.3f} to {df['Current (A)'].max():.3f}",
                        f"{df['Resistance (Ohm)'].max():.2f}",
                        f"{df['Resistance (Ohm)'].min():.2f}"
                    ]
                }
                
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='I-V Statistics', index=False)
            
            print(f"I-V data exported to Excel: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error exporting I-V data to Excel: {e}")
            return False


# We can also add a simple example to show how this class can be used.
if __name__ == "__main__":
    # Create an instance of the DataHandler.
    handler = DataHandler()

    # Create a new file for a simulated experiment.
    handler.create_new_file()

    # Simulate some data points and append them.
    simulated_data_point_1 = {
        "time": 1.0,
        "flow_setpoint": 1.5,
        "pump_flow_read": 1.48,
        "pressure_read": 10.2,
        "temp_read": 25.5
    }
    handler.append_data(simulated_data_point_1)

    simulated_data_point_2 = {
        "time": 2.0,
        "flow_setpoint": 1.5,
        "pump_flow_read": 1.51,
        "pressure_read": 10.3,
        "temp_read": 25.6
    }
    handler.append_data(simulated_data_point_2)

    # Close the file after the experiment is finished.
    handler.close_file()