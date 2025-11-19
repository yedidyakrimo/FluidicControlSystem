"""
DAQ control modules
Supports both NI USB-6002 and MCusb-1408FS-Plus
"""

from .ni_usb6002 import NIUSB6002
from .mcusb_1408fs import MCusb1408FS

__all__ = ['NIUSB6002', 'MCusb1408FS']
