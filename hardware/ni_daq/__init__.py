"""
DAQ control modules
Supports both NI USB-6002 and MCusb-1408FS-Plus
"""

# NI USB-6002 import is optional (requires nidaqmx)
try:
    from .ni_usb6002 import NIUSB6002
except ImportError:
    NIUSB6002 = None
    print("Warning: NI USB-6002 not available (nidaqmx not installed)")

try:
    from .mcusb_1408fs import MCusb1408FS
except (ImportError, OSError):
    MCusb1408FS = None
    print("Warning: MCusb-1408FS not available (cbw64.dll / MCC Universal Library not installed)")

__all__ = ['NIUSB6002', 'MCusb1408FS']
