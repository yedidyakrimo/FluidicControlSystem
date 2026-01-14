# Excel Export Documentation

## Overview

This document provides a comprehensive guide on how experimental data flows from collection to Excel export in the Fluidic Control System. The system collects real-time sensor data during experiments, stores it in CSV format, and provides functionality to export this data to well-formatted Excel files.

---

## Table of Contents

1. [Data Flow Overview](#data-flow-overview)
2. [Data Collection Process](#data-collection-process)
3. [Data Storage (CSV Format)](#data-storage-csv-format)
4. [Excel Export Process](#excel-export-process)
5. [Excel File Structure](#excel-file-structure)
6. [Code Implementation Details](#code-implementation-details)
7. [Usage Instructions](#usage-instructions)
8. [Error Handling](#error-handling)
9. [Data Fields Reference](#data-fields-reference)

---

## Data Flow Overview

The data flow from collection to Excel follows this path:

```
Hardware Sensors → Experiment Thread → Data Arrays → CSV File → Excel Export
     ↓                    ↓                  ↓            ↓            ↓
  Pump, Pressure,    Real-time data    In-memory    Persistent    Formatted
  Temperature,      collection loop    storage      storage        Excel file
  Level, Keithley   (1 second         (for graphs) (data/ folder)  (.xlsx)
  SMU               intervals)
```

### Detailed Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXPERIMENT EXECUTION                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  experiment_thread() - Main Tab (main_tab.py)                   │
│  • Runs in separate thread                                      │
│  • Collects data every 1 second                                 │
│  • Reads from hardware controllers                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Hardware Controller Reads                                      │
│  • read_pump_data() → flow rate                                 │
│  • read_pressure_sensor() → pressure                            │
│  • read_temperature_sensor() → temperature                      │
│  • read_level_sensor() → liquid level                            │
│  • measure_smu() → voltage, current (if Keithley enabled)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Data Point Creation                                            │
│  data_point = {                                                 │
│    "measurement_id": counter,                                   │
│    "time": elapsed_time,                                        │
│    "flow_setpoint": target_flow,                                 │
│    "pump_flow_read": actual_flow,                                │
│    "pressure_read": pressure_value,                             │
│    "temp_read": temperature_value,                               │
│    "level_read": level_value,                                    │
│    "voltage": keithley_voltage,                                  │
│    "current": keithley_current,                                  │
│    "target_voltage": bias_voltage                                │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
    ┌──────────────────────┐  ┌──────────────────────┐
    │  In-Memory Arrays    │  │  CSV File Storage    │
    │  (for real-time      │  │  (persistent)        │
    │   graph updates)     │  │                      │
    │  • flow_x_data       │  │  • data_handler      │
    │  • flow_y_data       │  │    .append_data()    │
    │  • pressure_x_data   │  │  • CSV format        │
    │  • pressure_y_data   │  │  • data/ folder      │
    │  • temp_x_data       │  │                      │
    │  • temp_y_data       │  │                      │
    │  • level_x_data      │  │                      │
    │  • level_y_data      │  │                      │
    │  • keithley_*_data   │  │                      │
    └──────────────────────┘  └──────────────────────┘
                                        │
                                        ▼
                            ┌──────────────────────┐
                            │  Excel Export        │
                            │  • User clicks       │
                            │    "Excel" button    │
                            │  • File dialog       │
                            │  • export_to_excel() │
                            └──────────────────────┘
                                        │
                                        ▼
                            ┌──────────────────────┐
                            │  Excel File (.xlsx)  │
                            │  • Experiment Data   │
                            │    sheet             │
                            │  • Summary sheet     │
                            │  • Formatted columns │
                            └──────────────────────┘
```

---

## Data Collection Process

### 1. Experiment Start

When a user clicks "Start Recording" in the Main Tab:

1. **File Creation**: A new CSV file is created in the `data/` folder
   - Filename format: `{experiment_name}_{timestamp}.csv`
   - Example: `experiment_data_20241215_143022.csv`

2. **Metadata Writing**: Experiment metadata is written as comments at the top of the CSV file:
   ```csv
   # Experiment Metadata
   # name: experiment_data
   # description: Test run
   # tags: test,flow
   # operator: John Doe
   # start_time: 2024-12-15T14:30:22
   #
   ```

3. **CSV Header**: Column headers are written:
   ```csv
   measurement_id,time,flow_setpoint,pump_flow_read,pressure_read,temp_read,level_read,program_step,voltage,current,target_voltage
   ```

### 2. Real-Time Data Collection Loop

The `experiment_thread()` function runs in a separate thread and collects data every 1 second:

**Location**: `gui/tabs/main_tab.py`, lines 1484-1814

**Process**:
1. **Hardware Reading** (lines 1657-1707):
   ```python
   pump_data = self.exp_manager.hw_controller.read_pump_data()
   pressure = self.exp_manager.hw_controller.read_pressure_sensor()
   temperature = self.exp_manager.hw_controller.read_temperature_sensor()
   level = self.exp_manager.hw_controller.read_level_sensor()
   
   # Keithley measurements (if enabled)
   if self.keithley_output_enabled:
       smu_measurement = self.hw_controller.measure_smu(mode=current_mode)
       keithley_voltage = smu_measurement.get('voltage', None)
       keithley_current = smu_measurement.get('current', None)
   ```

2. **Data Point Creation** (lines 1752-1763):
   ```python
   data_point = {
       "measurement_id": self.measurement_counter,
       "time": elapsed_time_from_start,
       "flow_setpoint": self.current_flow_rate,
       "pump_flow_read": pump_data['flow'],
       "pressure_read": pressure if pressure is not None else "",
       "temp_read": temperature if temperature is not None else "",
       "level_read": level if level is not None else "",
       "voltage": keithley_voltage if keithley_voltage is not None else "",
       "current": keithley_current if keithley_current is not None else "",
       "target_voltage": float(self.keithley_bias_entry.get()) if self.keithley_output_enabled else ""
   }
   ```

3. **Data Storage** (line 1765):
   ```python
   self.data_handler.append_data(data_point)
   ```

4. **Graph Updates**: Data is also stored in in-memory arrays for real-time graph visualization (lines 1716-1750)

5. **Loop Continuation**: The loop continues until:
   - Experiment duration is reached
   - User clicks "Stop Recording"
   - Safety checks fail
   - Hardware timeout occurs

---

## Data Storage (CSV Format)

### CSV File Structure

**Location**: `utils/data_handler.py`

**File Creation** (lines 43-93):
- Files are stored in the `data/` folder (created automatically if it doesn't exist)
- Filename includes timestamp for uniqueness
- Metadata is written as comment lines (starting with `#`)
- CSV header row defines all column names

**Data Appending** (lines 96-103):
- Each data point is appended as a new row
- Uses Python's `csv.DictWriter` for structured writing
- Data is written immediately (no buffering delay)

### CSV File Example

```csv
# Experiment Metadata
# name: experiment_data
# description: Flow rate test
# tags: test,flow
# operator: Jane Smith
# start_time: 2024-12-15T14:30:22
#
measurement_id,time,flow_setpoint,pump_flow_read,pressure_read,temp_read,level_read,program_step,voltage,current,target_voltage
1,0.0,1.5,1.48,15.2,25.3,0.75,,1.5000,0.0025,1.5
2,1.0,1.5,1.49,15.3,25.4,0.76,,1.5010,0.0026,1.5
3,2.0,1.5,1.51,15.1,25.5,0.77,,1.5020,0.0027,1.5
```

### CSV Column Descriptions

| Column Name | Description | Data Type | Example |
|------------|-------------|-----------|---------|
| `measurement_id` | Sequential measurement number | Integer | 1, 2, 3, ... |
| `time` | Elapsed time from experiment start | Float (seconds) | 0.0, 1.0, 2.0, ... |
| `flow_setpoint` | Target flow rate set by user | Float (ml/min) | 1.5 |
| `pump_flow_read` | Actual flow rate from pump sensor | Float (ml/min) | 1.48 |
| `pressure_read` | Pressure sensor reading | Float (bar) | 15.2 |
| `temp_read` | Temperature sensor reading | Float (°C) | 25.3 |
| `level_read` | Liquid level sensor reading | Float (0-1) | 0.75 |
| `program_step` | Program step identifier (if using Program Tab) | String | "" or step name |
| `voltage` | Keithley SMU voltage reading | Float (V) | 1.5000 |
| `current` | Keithley SMU current reading | Float (A) | 0.0025 |
| `target_voltage` | Target bias voltage set on Keithley | Float (V) | 1.5 |

**Note**: Empty strings (`""`) are used for missing or unavailable sensor readings.

---

## Excel Export Process

### User Interface

**Location**: `gui/tabs/main_tab.py`, lines 1430-1450

**Button**: "Excel" button in the Control section of Main Tab

**Process**:
1. User clicks the "Excel" button
2. File dialog opens to select save location
3. User selects or enters filename (default extension: `.xlsx`)
4. `export_excel()` method is called
5. Success or error message is displayed

### Export Function Implementation

**Location**: `utils/data_handler.py`, lines 141-225

**Function**: `export_to_excel(output_path=None)`

**Step-by-Step Process**:

1. **Validation** (lines 146-148):
   ```python
   if not self.file_path or not os.path.exists(self.file_path):
       print("No data file to export. Run an experiment first.")
       return False
   ```

2. **File Flushing** (lines 151-153):
   ```python
   if self.file:
       self.file.flush()  # Ensure all data is written to disk
   ```

3. **CSV Reading** (line 156):
   ```python
   df = pd.read_csv(self.file_path, comment='#')
   ```
   - Uses pandas to read CSV file
   - Automatically skips comment lines (starting with `#`)
   - Creates a DataFrame with all data

4. **Empty Data Check** (lines 158-161):
   ```python
   if df.empty or len(df) == 0:
       print("CSV file is empty. No data to export.")
       return False
   ```

5. **Output Path Generation** (lines 163-169):
   ```python
   if output_path is None:
       output_path = self.file_path.replace('.csv', '.xlsx')
   
   if not output_path.endswith('.xlsx'):
       output_path += '.xlsx'
   ```

6. **Excel File Creation** (lines 172-207):
   ```python
   with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
       # Write main data sheet
       df.to_excel(writer, sheet_name='Experiment Data', index=False)
       
       # Format columns (auto-adjust width)
       # ... formatting code ...
       
       # Create summary sheet
       summary_df = pd.DataFrame(summary_data)
       summary_df.to_excel(writer, sheet_name='Summary', index=False)
   ```

7. **Success Return** (lines 209-210):
   ```python
   print(f"Data exported to Excel: {output_path}")
   return True
   ```

### Excel Export Flow Diagram

```
User clicks "Excel" button
         │
         ▼
export_excel() called (main_tab.py)
         │
         ▼
File dialog opens
         │
         ▼
User selects filename
         │
         ▼
data_handler.export_to_excel(filename)
         │
         ▼
┌────────────────────────┐
│ 1. Validate file exists│
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│ 2. Flush CSV file      │
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│ 3. Read CSV with pandas│
│    (skip comments)     │
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│ 4. Check data not empty│
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│ 5. Create Excel writer │
│    (openpyxl engine)   │
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│ 6. Write "Experiment   │
│    Data" sheet         │
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│ 7. Auto-format columns │
│    (adjust widths)     │
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│ 8. Calculate summary   │
│    statistics           │
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│ 9. Write "Summary"     │
│    sheet               │
└────────────────────────┘
         │
         ▼
┌────────────────────────┐
│ 10. Close Excel file   │
└────────────────────────┘
         │
         ▼
Success message displayed
```

---

## Excel File Structure

### Sheet 1: "Experiment Data"

This sheet contains all the raw experimental data in tabular format.

**Columns** (same as CSV):
- `measurement_id`
- `time`
- `flow_setpoint`
- `pump_flow_read`
- `pressure_read`
- `temp_read`
- `level_read`
- `program_step`
- `voltage`
- `current`
- `target_voltage`

**Features**:
- Auto-adjusted column widths (max 50 characters)
- All data types preserved (numbers, strings, empty cells)
- No index column (row numbers start at 1)
- Ready for analysis, charting, or further processing

**Example**:

| measurement_id | time | flow_setpoint | pump_flow_read | pressure_read | temp_read | level_read | program_step | voltage | current | target_voltage |
|---------------|------|---------------|-----------------|---------------|-----------|------------|--------------|---------|---------|----------------|
| 1 | 0.0 | 1.5 | 1.48 | 15.2 | 25.3 | 0.75 | | 1.5000 | 0.0025 | 1.5 |
| 2 | 1.0 | 1.5 | 1.49 | 15.3 | 25.4 | 0.76 | | 1.5010 | 0.0026 | 1.5 |
| 3 | 2.0 | 1.5 | 1.51 | 15.1 | 25.5 | 0.77 | | 1.5020 | 0.0027 | 1.5 |

### Sheet 2: "Summary"

This sheet provides a quick overview of key experiment statistics.

**Columns**:
- `Parameter`: Name of the statistic
- `Value`: Calculated value

**Summary Statistics**:

| Parameter | Description | Calculation |
|-----------|-------------|-------------|
| Total Data Points | Number of measurements | `len(df)` |
| Experiment Duration (s) | Total time span | `time[last] - time[first]` |
| Average Flow Rate | Mean pump flow reading | `mean(pump_flow_read)` |
| Max Pressure | Maximum pressure value | `max(pressure_read)` |
| Min Temperature | Minimum temperature value | `min(temp_read)` |
| Max Level | Maximum level value | `max(level_read)` |

**Example**:

| Parameter | Value |
|-----------|-------|
| Total Data Points | 600 |
| Experiment Duration (s) | 599.00 |
| Average Flow Rate | 1.49 |
| Max Pressure | 16.5 |
| Min Temperature | 24.8 |
| Max Level | 0.85 |

**Note**: If a sensor column is missing or contains no valid data, the corresponding statistic shows "N/A".

---

## Code Implementation Details

### Key Files

1. **`gui/tabs/main_tab.py`**
   - **Lines 1430-1450**: `export_excel()` method - UI handler for Excel export
   - **Lines 1484-1814**: `experiment_thread()` - Data collection loop
   - **Lines 1752-1765**: Data point creation and storage

2. **`utils/data_handler.py`**
   - **Lines 43-93**: `create_new_file()` - CSV file creation
   - **Lines 96-103**: `append_data()` - Data point writing
   - **Lines 141-225**: `export_to_excel()` - Excel export implementation

### Dependencies

**Required Python Packages**:
- `pandas`: Data manipulation and Excel writing
- `openpyxl`: Excel file format support (used by pandas)
- `csv`: CSV file writing (standard library)
- `os`: File system operations (standard library)
- `datetime`: Timestamp generation (standard library)

**Installation**:
```bash
pip install pandas openpyxl
```

### Thread Safety

**Important**: Data collection runs in a separate thread (`experiment_thread`), while Excel export runs on the main UI thread. The system uses thread-safe mechanisms:

1. **Data Lock**: `self.data_lock` protects in-memory data arrays
2. **File Flushing**: Before reading CSV for export, the file is flushed to ensure all data is written
3. **Queue System**: Graph updates use a queue system for thread-safe UI updates

---

## Usage Instructions

### Exporting Data to Excel

1. **Run an Experiment**:
   - Enter experiment name in "Experiment Name" field
   - Set flow rate and other parameters
   - Click "Start Recording"
   - Let the experiment run (data is collected every 1 second)
   - Click "Stop Recording" or "Finish Recording" when done

2. **Export to Excel**:
   - Click the "Excel" button in the Control section
   - A file dialog will open
   - Choose a location and filename (or use default)
   - Click "Save"
   - A success message will appear when export completes

3. **Open Excel File**:
   - Navigate to the saved location
   - Open the `.xlsx` file in Microsoft Excel, LibreOffice Calc, or any compatible spreadsheet application
   - Review the "Experiment Data" sheet for all measurements
   - Check the "Summary" sheet for quick statistics

### Multiple Measurements in Same File

The system supports multiple measurements in the same CSV file:

- Each measurement has a unique `measurement_id`
- When you click "Start Recording" again (without clicking "Finish"), a new measurement begins
- The `measurement_counter` increments for each new measurement
- All measurements are exported together in the same Excel file

### Exporting from Browser Tab

You can also export experiments from the Browser Tab:

1. Go to the "Browser" tab
2. Select an experiment from the list
3. Click "Export" button
4. Choose Excel format (`.xlsx`) or CSV format (`.csv`)

---

## Error Handling

### Common Errors and Solutions

1. **"No data file to export"**
   - **Cause**: No experiment has been run yet
   - **Solution**: Run an experiment first, then export

2. **"CSV file is empty"**
   - **Cause**: Experiment was started but no data was collected
   - **Solution**: Ensure sensors are connected and experiment runs for at least 1 second

3. **"Permission denied"**
   - **Cause**: Excel file is open in another program
   - **Solution**: Close the Excel file and try again

4. **"Error parsing CSV file"**
   - **Cause**: CSV file is corrupted or has invalid format
   - **Solution**: Check the CSV file manually, or run a new experiment

5. **"File may be open in another program"**
   - **Cause**: The target Excel file is already open
   - **Solution**: Close the file in Excel/other program and retry

### Error Handling Code

The export function includes comprehensive error handling:

```python
try:
    # Export process
    ...
except pd.errors.EmptyDataError:
    print("CSV file contains no data rows.")
    return False
except pd.errors.ParserError as e:
    print(f"Error parsing CSV file: {e}")
    return False
except PermissionError:
    print(f"Permission denied: Cannot write to {output_path}.")
    return False
except Exception as e:
    print(f"Error exporting to Excel: {e}")
    traceback.print_exc()
    return False
```

---

## Data Fields Reference

### Complete Field List

| Field Name | Type | Unit | Description | Source |
|------------|------|------|-------------|--------|
| `measurement_id` | Integer | - | Sequential measurement number | Auto-incremented |
| `time` | Float | seconds | Elapsed time from experiment start | Calculated from `time.time()` |
| `flow_setpoint` | Float | ml/min | Target flow rate set by user | User input / program step |
| `pump_flow_read` | Float | ml/min | Actual flow rate from pump | Pump sensor (Vapourtec SF-10) |
| `pressure_read` | Float | bar | Pressure sensor reading | Pressure sensor hardware |
| `temp_read` | Float | °C | Temperature sensor reading | Temperature sensor hardware |
| `level_read` | Float | 0-1 | Liquid level (0=empty, 1=full) | Level sensor hardware |
| `program_step` | String | - | Program step identifier | Program Tab (if used) |
| `voltage` | Float | V | Keithley SMU voltage reading | Keithley 2450 SMU |
| `current` | Float | A | Keithley SMU current reading | Keithley 2450 SMU |
| `target_voltage` | Float | V | Target bias voltage on Keithley | User input (if SMU enabled) |

### Data Type Handling

- **Numbers**: Stored as floats or integers in CSV, preserved in Excel
- **Empty Values**: Stored as empty strings (`""`) in CSV, appear as empty cells in Excel
- **Missing Sensors**: If a sensor is disconnected, the value is stored as empty string
- **NaN Values**: Temperature/pressure/level may show NaN in graphs if sensor disconnected, but exported as empty string in CSV/Excel

### Data Validation

- **Flow Rate**: Validated to be between 0 and 5.0 ml/min (maximum pump capacity)
- **Time**: Always positive, starts at 0.0
- **Measurement ID**: Always positive integer, increments for each new measurement
- **Sensor Readings**: May be empty if sensor is disconnected or unavailable

---

## Advanced Topics

### Custom Export Locations

By default, Excel files are saved to the location chosen in the file dialog. You can also programmatically specify the export path:

```python
# In your code
success = data_handler.export_to_excel("C:/Users/User/Documents/my_experiment.xlsx")
```

### Batch Export

To export multiple experiments:

1. Use the Browser Tab to view all experiments
2. Export each one individually, or
3. Manually copy CSV files and convert them using pandas:

```python
import pandas as pd

# Read CSV
df = pd.read_csv("data/experiment_data_20241215_143022.csv", comment='#')

# Export to Excel
df.to_excel("output.xlsx", index=False)
```

### Excel Formatting Customization

The current implementation auto-adjusts column widths. To add more formatting (colors, borders, charts), you can modify the `export_to_excel()` function in `utils/data_handler.py`:

```python
from openpyxl.styles import Font, PatternFill, Alignment

# Example: Format header row
header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
header_font = Font(bold=True, color="FFFFFF")

for cell in worksheet[1]:
    cell.fill = header_fill
    cell.font = header_font
```

### Metadata Export

Currently, metadata is stored in the CSV file as comments and in a separate JSON file. To include metadata in the Excel file, you could add a "Metadata" sheet:

```python
metadata_df = pd.DataFrame([self.metadata])
metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
```

---

## Troubleshooting

### Excel File Won't Open

- **Check file extension**: Ensure it's `.xlsx` (not `.xls`)
- **Check file size**: Empty or corrupted files may not open
- **Try different application**: Test with LibreOffice Calc or Google Sheets

### Missing Data in Excel

- **Check CSV file**: Open the original CSV to verify data exists
- **Check for errors**: Look at console output for error messages
- **Verify sensors**: Ensure sensors were connected during experiment

### Slow Export

- **Large files**: Experiments with many data points (>10,000) may take longer
- **Disk speed**: Export speed depends on disk I/O performance
- **Background processes**: Close other applications to free up resources

### Column Width Issues

- Columns are auto-adjusted, but very long values may be truncated
- Manually adjust column widths in Excel if needed
- Maximum column width is set to 50 characters in the code

---

## Summary

The Excel export functionality provides a seamless way to:

1. **Export experimental data** from CSV format to Excel format
2. **Preserve all data** including sensor readings, timestamps, and metadata
3. **Create summary statistics** for quick analysis
4. **Format data** for easy viewing and further analysis

The entire process is automated and user-friendly, requiring only a single button click to export all collected experimental data into a professional Excel file format.

---

## Related Documentation

- **Main Tab Documentation**: `docs/Main_Tab_Button_Layout_Documentation.md`
- **Data Handler Code**: `utils/data_handler.py`
- **Keithley Integration**: `docs/KEITHLEY_READ_COMMAND_DOCUMENTATION.md`
- **Code Documentation**: `docs/CODE_DOCUMENTATION.md`

---

**Last Updated**: December 2024  
**Version**: 1.0  
**Author**: Fluidic Control System Documentation

