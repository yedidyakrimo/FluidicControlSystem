# main_app.py

import PySimpleGUI as sg
from hardware_control import HardwareController
from experiment_logic import ExperimentManager
from data_handler import DataHandler
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import random

# Set the theme for the GUI to a more professional, dark theme.
sg.theme('DarkBlue2')

# --- Layout Definitions ---
# Main Tab Layout
main_tab_layout = [
    [sg.Frame('Experiment Parameters', [
        [sg.Text('Flow Rate (ml/min):', size=(20, 1)), sg.Input(key='-FLOW_RATE-', default_text='1.5', size=(10, 1))],
        [sg.Text('Duration (sec):', size=(20, 1)), sg.Input(key='-DURATION-', default_text='60', size=(10, 1))],
        [sg.Text('Valve Settings:', size=(20, 1)),
         sg.Radio('Main', "RADIO1", default=True, key='-VALVE_MAIN-'),
         sg.Radio('Rinsing', "RADIO1", key='-VALVE_RINSING-')]
    ])],
    [sg.Frame('Control', [
        [sg.Button('Start Experiment', key='-START_EXP-', size=(15, 2), button_color=('white', 'green')),
         sg.Button('Stop Experiment', key='-STOP_EXP-', size=(15, 2), button_color=('white', 'red'))]
    ], element_justification='center')],
    [sg.Frame('Current Readings', [
        [sg.Text('Pressure:', size=(12, 1)), sg.Text('N/A', key='-PRESSURE_READ-')],
        [sg.Text('Temperature:', size=(12, 1)), sg.Text('N/A', key='-TEMP_READ-')],
        [sg.Text('Flow:', size=(12, 1)), sg.Text('N/A', key='-FLOW_READ-')],
        [sg.Text('Level:', size=(12, 1)), sg.Text('N/A', key='-LEVEL_READ-')]
    ])],
    [sg.Text('', size=(40, 1), key='-STATUS_BAR-', font=('Helvetica', 10, 'italic'))],
    [sg.Frame('Real-Time Monitoring', [
        [sg.Canvas(key='-GRAPH1_CANVAS-', size=(290, 190)), sg.Canvas(key='-GRAPH2_CANVAS-', size=(290, 190))],
        [sg.Canvas(key='-GRAPH3_CANVAS-', size=(290, 190)), sg.Canvas(key='-GRAPH4_CANVAS-', size=(290, 190))]
    ])]
]

# IV Tab Layout
iv_tab_layout = [
    [sg.Frame('Quick Control', [
        [sg.Button('Direct setting', key='-IV_DIRECT_SET-'), sg.Button('Direct run', key='-IV_DIRECT_RUN-')]
    ], border_width=0)],
    [sg.Frame('Parameters', [
        [sg.Text('Range:', size=(15, 1)), sg.Input(key='-IV_RANGE-', size=(10, 1))],
        [sg.Text('Step:', size=(15, 1)), sg.Input(key='-IV_STEP-', size=(10, 1))],
        [sg.Text('Time:', size=(15, 1)), sg.Input(key='-IV_TIME-', size=(10, 1))],
        [sg.Text('Flow rate:', size=(15, 1)), sg.Input(key='-IV_FLOW_RATE-', size=(10, 1))],
        [sg.Text('Valve setting:', size=(15, 1)), sg.Radio('Main', "IV_RADIO", default=True, key='-IV_VALVE_MAIN-'),
         sg.Radio('Rinsing', "IV_RADIO", key='-IV_VALVE_RINSING-')]
    ], border_width=0)],
    [sg.Frame('Program Control', [
        [sg.Button('Choose program', key='-IV_CHOOSE_PROGRAM-')],
        [sg.Button('Run program', key='-IV_RUN_PROGRAM-')]
    ], border_width=0)],
    [sg.Button('Save to file', key='-IV_SAVE_FILE-')],
    [sg.Canvas(key='-IV_GRAPH_CANVAS-', size=(600, 400), background_color='white')]
]

# Write Program Tab Layout
write_program_layout = [
    [sg.Frame('Program Editor', [
        [sg.Multiline(size=(70, 15), key='-PROGRAM_EDITOR-', 
                     default_text='# Write your experiment program here\n# Example:\n# step1: flow=1.5, duration=60, temp=25, valve=main\n# step2: flow=2.0, duration=30, temp=30, valve=rinsing\n# step3: flow=0.5, duration=120, temp=20, valve=main')]
    ])],
    [sg.Frame('Program Control', [
        [sg.Button('Load Program', key='-LOAD_PROGRAM-', size=(12, 1)),
         sg.Button('Save Program', key='-SAVE_PROGRAM-', size=(12, 1)),
         sg.Button('Run Program', key='-RUN_PROGRAM-', size=(12, 1)),
         sg.Button('Stop Program', key='-STOP_PROGRAM-', size=(12, 1))]
    ])],
    [sg.Frame('Program Library', [
        [sg.Listbox(values=['Standard Test', 'Temperature Ramp', 'Flow Ramp', 'I-V Measurement'], 
                   size=(30, 6), key='-PROGRAM_LIST-')],
        [sg.Button('Load Selected', key='-LOAD_SELECTED-', size=(15, 1))]
    ])],
    [sg.Frame('Program Status', [
        [sg.Text('Status:', size=(10, 1)), sg.Text('Ready', key='-PROGRAM_STATUS-', size=(50, 1))]
    ])]
]

# Create the tab group with the different layouts.
tab_group = sg.TabGroup([
    [sg.Tab('Main', main_tab_layout)],
    [sg.Tab('IV', iv_tab_layout)],
    [sg.Tab('Write program', write_program_layout)]
])

# Define the main window layout with the tab group.
layout = [[tab_group]]


# --- GUI Drawing Functions ---
def draw_figure(canvas, figure):
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    return figure_canvas_agg


def update_graph(fig_agg, x_data, y_data):
    ax = fig_agg.figure.get_axes()[0]
    ax.cla()
    ax.plot(x_data, y_data)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Value")
    ax.set_title("Real-Time Data")
    ax.grid(True)
    fig_agg.draw()

def update_iv_graph(fig_agg, x_data, y_data):
    ax = fig_agg.figure.get_axes()[0]
    ax.cla()
    ax.plot(x_data, y_data, 'b-', linewidth=2)
    ax.set_xlabel("Voltage (V)")
    ax.set_ylabel("Current (A)")
    ax.set_title("I-V Characteristic")
    ax.grid(True)
    fig_agg.draw()

def run_iv_measurement(hw_controller, data_handler, window, fig_agg, x_data, y_data, range_val, step_val):
    """
    Run I-V measurement in separate thread
    """
    window['-STATUS_BAR-'].update("Starting I-V measurement...")
    
    # Clear previous data
    x_data.clear()
    y_data.clear()
    
    # Create new data file
    data_handler.create_new_file()
    
    try:
        # Setup SMU
        hw_controller.setup_smu_iv_sweep(-range_val, range_val, step_val)
        
        # Perform I-V sweep
        voltage_points = []
        current_points = []
        
        for v in range(int(-range_val/step_val), int(range_val/step_val) + 1):
            voltage = v * step_val
            
            # Set voltage and measure current
            if hw_controller.smu:
                try:
                    hw_controller.smu.write(f"SOUR:VOLT {voltage}")
                    hw_controller.smu.write("INIT")
                    current = float(hw_controller.smu.query("MEAS:CURR?"))
                except Exception as e:
                    print(f"Error in I-V measurement: {e}")
                    current = voltage * 0.1 + random.uniform(-0.01, 0.01)
            else:
                # Simulation mode
                current = voltage * 0.1 + random.uniform(-0.01, 0.01)
            
            voltage_points.append(voltage)
            current_points.append(current)
            
            # Update graph
            x_data.append(voltage)
            y_data.append(current)
            window.write_event_value('-UPDATE_IV_GRAPH-', (x_data, y_data))
            
            # Save data point
            data_point = {
                "time": len(voltage_points),
                "voltage": voltage,
                "current": current
            }
            data_handler.append_data(data_point)
            
            time.sleep(0.1)  # Small delay between measurements
        
        window['-STATUS_BAR-'].update("I-V measurement completed")
        
    except Exception as e:
        window['-STATUS_BAR-'].update(f"I-V measurement error: {e}")
        print(f"I-V measurement error: {e}")
    
    finally:
        data_handler.close_file()
        hw_controller.stop_smu()

def parse_program(program_text):
    """
    Parse program text into experiment steps
    Format: step1: flow=1.5, duration=60, temp=25, valve=main
    """
    steps = []
    if not program_text or not program_text.strip():
        return steps
        
    lines = program_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith('step') and ':' in line:
            try:
                step_data = {}
                parts = line.split(':')[1].strip().split(',')
                
                for part in parts:
                    part = part.strip()
                    if '=' in part:
                        key, value = part.split('=')
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'flow':
                            step_data['flow_rate'] = float(value)
                        elif key == 'duration':
                            step_data['duration'] = int(value)
                        elif key == 'temp':
                            step_data['temperature'] = float(value)
                        elif key == 'valve':
                            if value == 'main':
                                step_data['valve_setting'] = {'valve1': True, 'valve2': False}
                            elif value == 'rinsing':
                                step_data['valve_setting'] = {'valve1': False, 'valve2': True}
                
                if 'flow_rate' in step_data and 'duration' in step_data:
                    steps.append(step_data)
                    
            except (ValueError, IndexError) as e:
                print(f"Error parsing line: {line}, Error: {e}")
                continue
    
    return steps

def run_program_thread(exp_manager, experiment_program, window, fig1_agg, fig2_agg, fig3_agg, fig4_agg,
                      flow_x_data, flow_y_data, pressure_x_data, pressure_y_data,
                      temp_x_data, temp_y_data, level_x_data, level_y_data):
    """
    Run program from Write Program tab
    """
    exp_manager.is_running = True
    window['-PROGRAM_STATUS-'].update('Starting program...')

    data_handler = exp_manager.data_handler
    data_handler.create_new_file()

    for step in experiment_program:
        if not exp_manager.is_running:
            break

        duration = step.get('duration')
        flow_rate = step.get('flow_rate')
        temperature = step.get('temperature', 25.0)
        valve_setting = step.get('valve_setting', {'valve1': True, 'valve2': False})

        window['-PROGRAM_STATUS-'].update(f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min, Temp={temperature}°C")

        # Set hardware parameters
        exp_manager.hw_controller.set_pump_flow_rate(flow_rate)
        exp_manager.hw_controller.set_heating_plate_temp(temperature)
        exp_manager.hw_controller.set_valves(valve_setting['valve1'], valve_setting['valve2'])

        start_time = time.time()

        while time.time() - start_time < duration and exp_manager.is_running:
            if not exp_manager.perform_safety_checks():
                break

            pump_data = exp_manager.hw_controller.read_pump_data()
            pressure = exp_manager.hw_controller.read_pressure_sensor()
            temperature_read = exp_manager.hw_controller.read_temperature_sensor()
            level = exp_manager.hw_controller.read_level_sensor()

            current_time = time.time()
            
            # Update all data arrays
            flow_x_data.append(current_time)
            flow_y_data.append(pump_data['flow'])
            pressure_x_data.append(current_time)
            pressure_y_data.append(pressure)
            temp_x_data.append(current_time)
            temp_y_data.append(temperature_read)
            level_x_data.append(current_time)
            level_y_data.append(level * 100)

            data_point = {
                "time": current_time,
                "flow_setpoint": flow_rate,
                "pump_flow_read": pump_data['flow'],
                "pressure_read": pressure,
                "temp_read": temperature_read,
                "level_read": level,
                "program_step": len(experiment_program)
            }
            data_handler.append_data(data_point)

            # Update all graphs
            window.write_event_value('-UPDATE_GRAPH1-', (flow_x_data, flow_y_data))
            window.write_event_value('-UPDATE_GRAPH2-', (pressure_x_data, pressure_y_data))
            window.write_event_value('-UPDATE_GRAPH3-', (temp_x_data, temp_y_data))
            window.write_event_value('-UPDATE_GRAPH4-', (level_x_data, level_y_data))
            time.sleep(1)

    exp_manager.stop_experiment()
    data_handler.close_file()
    window['-PROGRAM_STATUS-'].update('Program completed.')


# --- Experiment Thread Function ---
def experiment_thread(exp_manager, experiment_program, window, fig1_agg, fig2_agg, fig3_agg, fig4_agg, 
                     flow_x_data, flow_y_data, pressure_x_data, pressure_y_data, 
                     temp_x_data, temp_y_data, level_x_data, level_y_data):
    exp_manager.is_running = True
    window['-STATUS_BAR-'].update('Starting experiment...')

    data_handler = exp_manager.data_handler
    data_handler.create_new_file()

    for step in experiment_program:
        if not exp_manager.is_running:
            break

        duration = step.get('duration')
        flow_rate = step.get('flow_rate')

        window['-STATUS_BAR-'].update(f"Executing step: Duration={duration}s, Flow Rate={flow_rate} ml/min")

        exp_manager.hw_controller.set_pump_flow_rate(flow_rate)

        start_time = time.time()

        while time.time() - start_time < duration and exp_manager.is_running:
            if not exp_manager.perform_safety_checks():
                break

            pump_data = exp_manager.hw_controller.read_pump_data()
            pressure = exp_manager.hw_controller.read_pressure_sensor()
            temperature = exp_manager.hw_controller.read_temperature_sensor()
            level = exp_manager.hw_controller.read_level_sensor()

            current_time = time.time()
            
            # Update flow data
            flow_x_data.append(current_time)
            flow_y_data.append(pump_data['flow'])
            
            # Update pressure data
            pressure_x_data.append(current_time)
            pressure_y_data.append(pressure)
            
            # Update temperature data
            temp_x_data.append(current_time)
            temp_y_data.append(temperature)
            
            # Update level data
            level_x_data.append(current_time)
            level_y_data.append(level * 100)  # Convert to percentage

            data_point = {
                "time": current_time,
                "flow_setpoint": flow_rate,
                "pump_flow_read": pump_data['flow'],
                "pressure_read": pressure,
                "temp_read": temperature,
                "level_read": level
            }
            data_handler.append_data(data_point)

            # Update all graphs
            window.write_event_value('-UPDATE_GRAPH1-', (flow_x_data, flow_y_data))
            window.write_event_value('-UPDATE_GRAPH2-', (pressure_x_data, pressure_y_data))
            window.write_event_value('-UPDATE_GRAPH3-', (temp_x_data, temp_y_data))
            window.write_event_value('-UPDATE_GRAPH4-', (level_x_data, level_y_data))
            time.sleep(1)

    exp_manager.stop_experiment()
    data_handler.close_file()
    window['-STATUS_BAR-'].update('Experiment finished.')


# --- Main Application Loop ---
def main():
    window = sg.Window('Fluidic Control System', layout, size=(600, 600), finalize=True)

    # Initialize multiple graphs for the Main tab.
    # Graph 1: Flow vs Time
    fig1, ax1 = plt.subplots(figsize=(2.9, 1.9))
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Flow (ml/min)")
    ax1.set_title("Flow Rate")
    ax1.grid(True)
    fig1_agg = draw_figure(window['-GRAPH1_CANVAS-'].TKCanvas, fig1)
    flow_x_data, flow_y_data = [], []

    # Graph 2: Pressure vs Time
    fig2, ax2 = plt.subplots(figsize=(2.9, 1.9))
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Pressure (PSI)")
    ax2.set_title("Pressure")
    ax2.grid(True)
    fig2_agg = draw_figure(window['-GRAPH2_CANVAS-'].TKCanvas, fig2)
    pressure_x_data, pressure_y_data = [], []

    # Graph 3: Temperature vs Time
    fig3, ax3 = plt.subplots(figsize=(2.9, 1.9))
    ax3.set_xlabel("Time (s)")
    ax3.set_ylabel("Temperature (°C)")
    ax3.set_title("Temperature")
    ax3.grid(True)
    fig3_agg = draw_figure(window['-GRAPH3_CANVAS-'].TKCanvas, fig3)
    temp_x_data, temp_y_data = [], []

    # Graph 4: Level vs Time
    fig4, ax4 = plt.subplots(figsize=(2.9, 1.9))
    ax4.set_xlabel("Time (s)")
    ax4.set_ylabel("Level (%)")
    ax4.set_title("Liquid Level")
    ax4.grid(True)
    fig4_agg = draw_figure(window['-GRAPH4_CANVAS-'].TKCanvas, fig4)
    level_x_data, level_y_data = [], []

    # Initialize a separate graph for the IV tab.
    iv_fig, iv_ax = plt.subplots(figsize=(6, 4))
    iv_ax.set_xlabel("Voltage (V)")
    iv_ax.set_ylabel("Current (A)")
    iv_ax.set_title("I-V Curve")
    iv_ax.grid(True)
    iv_fig_agg = draw_figure(window['-IV_GRAPH_CANVAS-'].TKCanvas, iv_fig)
    iv_x_data, iv_y_data = [], []

    # Initialize our three core components.
    hw_controller = HardwareController(pump_port='COM3', ni_device_name='Dev1', smu_resource='USB0::0x05E6::0x2450::0123456789::INSTR')
    data_handler = DataHandler()
    exp_manager = ExperimentManager(hw_controller, data_handler)

    while True:
        event, values = window.read(timeout=100)

        if event == sg.WIN_CLOSED:
            break

        if event == '-START_EXP-':
            try:
                flow_rate = float(values['-FLOW_RATE-'])
                duration = int(values['-DURATION-'])
                valve_setting = {'valve1': values['-VALVE_MAIN-'], 'valve2': not values['-VALVE_MAIN-']}

                experiment_program = [{'duration': duration, 'flow_rate': flow_rate, 'valve_setting': valve_setting}]

                threading.Thread(target=experiment_thread,
                                 args=(exp_manager, experiment_program, window, fig1_agg, fig2_agg, fig3_agg, fig4_agg,
                                       flow_x_data, flow_y_data, pressure_x_data, pressure_y_data,
                                       temp_x_data, temp_y_data, level_x_data, level_y_data),
                                 daemon=True).start()

            except ValueError:
                sg.popup_error('Invalid input for Flow Rate or Duration. Please enter numbers.')

        if event == '-STOP_EXP-':
            exp_manager.stop_experiment()

        if event == '-UPDATE_GRAPH1-':
            x, y = values['-UPDATE_GRAPH1-']
            update_graph(fig1_agg, x, y)

        if event == '-UPDATE_GRAPH2-':
            x, y = values['-UPDATE_GRAPH2-']
            update_graph(fig2_agg, x, y)

        if event == '-UPDATE_GRAPH3-':
            x, y = values['-UPDATE_GRAPH3-']
            update_graph(fig3_agg, x, y)

        if event == '-UPDATE_GRAPH4-':
            x, y = values['-UPDATE_GRAPH4-']
            update_graph(fig4_agg, x, y)

        if event == '-UPDATE_IV_GRAPH-':
            x, y = values['-UPDATE_IV_GRAPH-']
            update_iv_graph(iv_fig_agg, x, y)

        # IV Tab Event Handling
        if event == '-IV_DIRECT_SET-':
            try:
                range_val = float(values['-IV_RANGE-']) if values['-IV_RANGE-'] else 2.0
                step_val = float(values['-IV_STEP-']) if values['-IV_STEP-'] else 0.1
                time_val = float(values['-IV_TIME-']) if values['-IV_TIME-'] else 1.0
                flow_rate = float(values['-IV_FLOW_RATE-']) if values['-IV_FLOW_RATE-'] else 1.5
                
                # Setup SMU for I-V measurement
                hw_controller.setup_smu_iv_sweep(-range_val, range_val, step_val)
                
                # Set flow rate
                hw_controller.set_pump_flow_rate(flow_rate)
                
                # Set valves
                valve_main = values['-IV_VALVE_MAIN-']
                hw_controller.set_valves(valve_main, not valve_main)
                
                window['-STATUS_BAR-'].update(f"I-V setup completed: Range={range_val}V, Step={step_val}V, Flow={flow_rate}ml/min")
                
            except ValueError:
                sg.popup_error("Invalid input values. Please enter numbers.")

        if event == '-IV_DIRECT_RUN-':
            try:
                range_val = float(values['-IV_RANGE-']) if values['-IV_RANGE-'] else 2.0
                step_val = float(values['-IV_STEP-']) if values['-IV_STEP-'] else 0.1
                
                # Start I-V measurement in separate thread
                threading.Thread(target=run_iv_measurement, 
                               args=(hw_controller, data_handler, window, iv_fig_agg, iv_x_data, iv_y_data, range_val, step_val),
                               daemon=True).start()
                
            except ValueError:
                sg.popup_error("Invalid input values. Please enter numbers.")

        if event == '-IV_SAVE_FILE-':
            try:
                # Save current I-V data
                if iv_x_data and iv_y_data:
                    data_handler.create_new_file()
                    for i, (v, i_val) in enumerate(zip(iv_x_data, iv_y_data)):
                        data_point = {
                            "time": i,
                            "voltage": v,
                            "current": i_val
                        }
                        data_handler.append_data(data_point)
                    data_handler.close_file()
                    window['-STATUS_BAR-'].update("I-V data saved to file")
                else:
                    sg.popup_error("No I-V data to save")
            except Exception as e:
                sg.popup_error(f"Error saving I-V data: {e}")

        # Write Program Tab Event Handling
        if event == '-LOAD_PROGRAM-':
            try:
                filename = sg.popup_get_file('Load Program File', file_types=(('Text Files', '*.txt'),))
                if filename:
                    with open(filename, 'r') as f:
                        program_text = f.read()
                    window['-PROGRAM_EDITOR-'].update(program_text)
                    window['-PROGRAM_STATUS-'].update(f"Loaded: {filename}")
            except Exception as e:
                sg.popup_error(f"Error loading program: {e}")

        if event == '-SAVE_PROGRAM-':
            try:
                program_text = values['-PROGRAM_EDITOR-']
                filename = sg.popup_get_file('Save Program File', save_as=True, file_types=(('Text Files', '*.txt'),))
                if filename:
                    with open(filename, 'w') as f:
                        f.write(program_text)
                    window['-PROGRAM_STATUS-'].update(f"Saved: {filename}")
            except Exception as e:
                sg.popup_error(f"Error saving program: {e}")

        if event == '-LOAD_SELECTED-':
            try:
                selected = values['-PROGRAM_LIST-']
                if selected:
                    program_name = selected[0]
                    program_templates = {
                        'Standard Test': 'step1: flow=1.5, duration=60, temp=25, valve=main\nstep2: flow=2.0, duration=30, temp=30, valve=rinsing',
                        'Temperature Ramp': 'step1: flow=1.0, duration=30, temp=20, valve=main\nstep2: flow=1.0, duration=30, temp=30, valve=main\nstep3: flow=1.0, duration=30, temp=40, valve=main',
                        'Flow Ramp': 'step1: flow=0.5, duration=60, temp=25, valve=main\nstep2: flow=1.0, duration=60, temp=25, valve=main\nstep3: flow=1.5, duration=60, temp=25, valve=main',
                        'I-V Measurement': 'step1: flow=1.0, duration=10, temp=25, valve=main\n# I-V measurement will be performed automatically'
                    }
                    if program_name in program_templates:
                        window['-PROGRAM_EDITOR-'].update(program_templates[program_name])
                        window['-PROGRAM_STATUS-'].update(f"Loaded template: {program_name}")
            except Exception as e:
                sg.popup_error(f"Error loading template: {e}")

        if event == '-RUN_PROGRAM-':
            try:
                program_text = values['-PROGRAM_EDITOR-']
                experiment_program = parse_program(program_text)
                if experiment_program:
                    window['-PROGRAM_STATUS-'].update("Running program...")
                    threading.Thread(target=run_program_thread,
                                   args=(exp_manager, experiment_program, window, fig1_agg, fig2_agg, fig3_agg, fig4_agg,
                                         flow_x_data, flow_y_data, pressure_x_data, pressure_y_data,
                                         temp_x_data, temp_y_data, level_x_data, level_y_data),
                                   daemon=True).start()
                else:
                    sg.popup_error("Invalid program format")
            except Exception as e:
                sg.popup_error(f"Error running program: {e}")

        if event == '-STOP_PROGRAM-':
            exp_manager.stop_experiment()
            window['-PROGRAM_STATUS-'].update("Program stopped")

        if not exp_manager.is_running:
            pressure = hw_controller.read_pressure_sensor()
            temperature = hw_controller.read_temperature_sensor()
            pump_data = hw_controller.read_pump_data()
            level = hw_controller.read_level_sensor()

            window['-PRESSURE_READ-'].update(f"{pressure:.2f} PSI")
            window['-TEMP_READ-'].update(f"{temperature:.2f} °C")
            window['-FLOW_READ-'].update(f"{pump_data['flow']:.2f} ml/min")
            window['-LEVEL_READ-'].update(f"{level:.2f} %")

    window.close()


if __name__ == "__main__":
    main()