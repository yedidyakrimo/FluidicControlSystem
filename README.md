# FluidicControlSystem
# Fluidic Control System for Fuel Quality Testing

## Introduction
This project is an automated control system designed for testing the quality of various fuels. The system is intended for use by researchers and academics at Bar-Ilan University, led by Professor Amos Sharoni. It enables controlled experiments involving temperature, pressure, and flow, as well as the measurement of electrical properties of fuel samples using advanced hardware components.

## Key Features
* **Automated Control:** The system provides automatic control over liquid flow, pressure, and temperature.
* **Real-Time Data Measurement:** It collects and displays data in real time from pressure, temperature, and flow sensors.
* **I-V Measurements:** The system is capable of performing complex I-V (current-voltage) experiments.
* **Graphical User Interface (GUI):** A user-friendly graphical interface allows for experiment management, data visualization, and real-time data saving to files.
* **Simulation Mode:** The system can be operated in a full simulation mode without a physical hardware connection, which is useful for testing and debugging.

## Hardware
The system is built around the following key hardware components:
* **Pump:** Vapourtec SF-10
* **Pressure Sensor:** Ashcroft ZL92
* **Flow Sensor:** Biotech AB-40010
* **Source Measure Unit (SMU):** Keithley 2450 SMU
* **Controller:** NI USB-6002

## Installation
To run the software, ensure you have Python and pip installed.
1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/FluidicControlSystem.git](https://github.com/your-username/FluidicControlSystem.git)
    cd FluidicControlSystem
    ```
2.  **Install the drivers:**
    * Ensure that the NI-DAQmx drivers are installed on your machine.
    * Verify that all other hardware components are connected and their drivers are up to date.
3.  **Install Python libraries:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage
* Run the main application from your terminal within the project directory:
    ```bash
    python main_app.py
    ```
* If the hardware is not connected, the system will automatically run in simulation mode.

## Contributions
Contributions to this project are welcome. Please feel free to reach out with any suggestions or improvements.
