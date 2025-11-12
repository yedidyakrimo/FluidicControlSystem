"""
General settings and constants for the Fluidic Control System
"""

# Window settings
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
WINDOW_TITLE = 'Fluidic Control System'

# Appearance settings
APPEARANCE_MODE = "dark"
COLOR_THEME = "blue"

# Default values
DEFAULT_FLOW_RATE = 1.5  # ml/min
DEFAULT_CURRENT_LIMIT = 0.1  # A
DEFAULT_VOLTAGE_RANGE = 10.0  # V
DEFAULT_STEP_SIZE = 0.1  # V

# Data settings
DATA_DIRECTORY = "data"
CSV_DELIMITER = ","
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# Update intervals (in milliseconds)
SENSOR_UPDATE_INTERVAL = 1000  # 1 second
GUI_UPDATE_INTERVAL = 100  # 100ms

# Safety thresholds
MIN_LEVEL_THRESHOLD = 0.05  # 5% capacity
MAX_PRESSURE_THRESHOLD = 100.0  # psi (adjust as needed)
MAX_TEMPERATURE_THRESHOLD = 100.0  # Celsius (adjust as needed)

