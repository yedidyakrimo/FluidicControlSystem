"""
Hardware configuration settings
"""

HARDWARE_CONFIG = {
    'pump': {
        'port': 'COM3',
        'baudrate': 9600,
        'timeout': 1,
        'type': 'Vapourtec SF-10'
    },
    'ni_daq': {
        'device_name': 'Dev1',
        'type': 'NI USB-6002'
    },
    'smu': {
        'auto_detect': True,
        'resource': None,  # Will be auto-detected if None
        'type': 'Keithley 2450',
        'default_current_limit': 0.1  # A
    },
    'sensors': {
        'pressure': {
            'channel': 'ai0',
            'type': 'Ashcroft ZL92'
        },
        'temperature': {
            'channel': 'ai1',
            'type': 'Temperature sensor'
        },
        'flow': {
            'channel': 'ai2',
            'type': 'Biotech AB-40010'
        },
        'level': {
            'channel': 'ai3',
            'type': 'Level sensor'
        }
    }
}

