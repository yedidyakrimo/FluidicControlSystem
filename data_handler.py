# data_handler.py

import csv
from datetime import datetime
import os  # Library for interacting with the operating system, used here for file paths.


# This class handles saving data to a file.
class DataHandler:
    # The constructor.
    def __init__(self, data_folder="data"):
        # We will create a 'data' folder to store all experiment files.
        self.data_folder = data_folder
        self.file_path = None  # This will store the path to the current file.
        self.file = None
        self.writer = None

        # Check if the data folder exists; if not, create it.
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
            print(f"Created data folder: {self.data_folder}")

    # This function creates a new CSV file for a new experiment.
    def create_new_file(self):
        # Generate a unique filename using the current timestamp.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"experiment_data_{timestamp}.csv"
        self.file_path = os.path.join(self.data_folder, filename)

        # Open the file in write mode ('w') with a newline='' argument to prevent empty rows.
        self.file = open(self.file_path, 'w', newline='')
        # Create a CSV writer object.
        self.writer = csv.DictWriter(self.file, fieldnames=[
            "time",
            "flow_setpoint",
            "pump_flow_read",
            "pressure_read",
            "temp_read"
            # We can add more fieldnames here for other sensors if needed.
        ])

        # Write the header row to the CSV file.
        self.writer.writeheader()
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

    # This function closes the file. It's crucial to call this at the end of every experiment.
    def close_file(self):
        if self.file:
            self.file.close()
            print(f"Data file closed.")


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