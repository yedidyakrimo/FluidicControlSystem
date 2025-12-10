# FluidicControlSystem
## Fluidic Control System for Fuel Quality Testing

### Introduction
This project is an automated control system designed for testing the quality of various fuels. The system is intended for use by researchers and academics at Bar-Ilan University, led by Professor Amos Sharoni. It enables controlled experiments involving temperature, pressure, and flow, as well as the measurement of electrical properties of fuel samples using advanced hardware components.

### Key Features
* **Automated Control:** The system provides automatic control over liquid flow, pressure, and temperature.
* **Real-Time Data Measurement:** It collects and displays data in real time from pressure, temperature, and flow sensors.
* **I-V Measurements:** The system is capable of performing complex I-V (current-voltage) experiments.
* **Graphical User Interface (GUI):** A user-friendly graphical interface allows for experiment management, data visualization, and real-time data saving to files.
* **Simulation Mode:** The system can be operated in a full simulation mode without a physical hardware connection, which is useful for testing and debugging.
* **Multiple Plot Windows:** 4 real-time monitoring graphs for comprehensive data visualization.
* **Programmable Experiments:** Write and execute complex multi-step experiment programs.

### Hardware Components
The system is built around the following key hardware components:
* **Pump:** Vapourtec SF-10
* **Pressure Sensor:** Ashcroft ZL92
* **Flow Sensor:** Biotech AB-40010
* **Source Measure Unit (SMU):** Keithley 2450 SMU
* **Controller:** NI USB-6002
* **3/2 Valves:** Automated valve control
* **Temperature Controller:** Precise temperature management

### Software Architecture
The system is built with a modular architecture:

**Core Modules:**
* **`main_app.py`** - Main GUI application and control loop (root directory)
* **`scripts/main.py`** - Application entry point
* **`utils/data_handler.py`** - Data logging and CSV/Excel management

**Hardware Modules** (`hardware/`):
* **`hardware_controller.py`** - Unified hardware interface
* **`pump/`** - Vapourtec pump control
* **`smu/`** - Keithley 2450 SMU control with SCPI commands
* **`ni_daq/`** - NI USB-6002 DAQ control
* **`sensors/`** - Pressure, temperature, flow, and level sensors

**Experiment Modules** (`experiments/`):
* **`experiment_manager.py`** - Main experiment manager
* **`experiment_types/`** - Time-dependent and I-V experiments
* **`safety_checks.py`** - Safety monitoring

**GUI Modules** (`gui/tabs/`):
* **`main_tab.py`** - Main experiment control and monitoring
* **`iv_tab.py`** - I-V measurement interface
* **`program_tab.py`** - Program editor and execution
* **`browser_tab.py`** - Experiment browser
* **`scheduler_tab.py`** - Experiment scheduler

**Test Scripts** (`tests/`):
* Hardware detection and connection tests
* MCusb-1408FS-Plus DAQ tests
* Keithley 2450 SMU tests
* SCPI command validation tests
* See `tests/README.md` for details

### Installation
To run the software, ensure you have Python 3.7+ and pip installed.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/FluidicControlSystem.git
   cd FluidicControlSystem
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install hardware drivers (optional):**
   * NI-DAQmx drivers for NI USB-6002
   * VISA drivers for Keithley 2450 SMU
   * Serial drivers for Vapourtec SF-10 pump

### Usage

#### Basic Usage
Run the main application:
```bash
python main.py
```
or
```bash
python main_app.py
```

#### Main Tab
- Set flow rate and duration
- Choose valve settings (Main/Rinsing)
- Monitor real-time data in 4 graphs
- Start/stop experiments

#### IV Tab
- Configure I-V measurement parameters
- Set voltage range and step size
- Perform current-voltage measurements
- Save I-V data to CSV

#### Write Program Tab
- Write custom experiment programs
- Load predefined templates
- Execute multi-step experiments
- Save and load program files

### Program Format
Write experiment programs using this format:
```
step1: flow=1.5, duration=60, temp=25, valve=main
step2: flow=2.0, duration=30, temp=30, valve=rinsing
step3: flow=0.5, duration=120, temp=20, valve=main
```

### Simulation Mode
The system automatically runs in simulation mode when hardware is not connected, allowing for testing and development without physical equipment.

### Data Output
All experiments are automatically saved to CSV files with timestamps in the `data/` directory. Data includes:
- Time stamps
- Flow rates (setpoint and measured)
- Pressure readings
- Temperature readings
- Level readings
- Valve states

### Safety Features
- Automatic liquid level monitoring
- Emergency stop functionality
- Hardware status checking
- Error handling and recovery

### Requirements
- Python 3.7+
- customtkinter (GUI framework)
- matplotlib (plotting)
- pyserial (serial communication)
- nidaqmx (NI DAQ support)
- numpy (numerical operations)
- pyvisa (VISA communication for SMU)
- pandas (data handling)
- openpyxl (Excel export)

### Contributing
Contributions to this project are welcome. Please feel free to reach out with any suggestions or improvements.

### License
This project is licensed under the MIT License - see the LICENSE file for details.
