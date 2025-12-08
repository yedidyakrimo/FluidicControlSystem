"""
Hardware control module
"""

from .pump.vapourtec_pump import VapourtecPump
from .smu.keithley_2450 import Keithley2450
# NI USB-6002 import is optional (requires nidaqmx)
try:
    from .ni_daq.ni_usb6002 import NIUSB6002
except ImportError:
    NIUSB6002 = None
    print("Warning: NI USB-6002 not available (nidaqmx not installed)")

from .sensors.pressure_sensor import PressureSensor
from .sensors.temperature_sensor import TemperatureSensor
from .sensors.flow_sensor import FlowSensor
from .sensors.level_sensor import LevelSensor

# For backward compatibility - create HardwareController that uses all modules
from .hardware_controller import HardwareController

__all__ = [
    'VapourtecPump',
    'Keithley2450',
    'NIUSB6002',
    'PressureSensor',
    'TemperatureSensor',
    'FlowSensor',
    'LevelSensor',
    'HardwareController'
]
