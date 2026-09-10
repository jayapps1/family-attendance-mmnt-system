"""Temporarily restore the system DLL search path for external Windows programs."""
from contextlib import contextmanager
import os
import sys


@contextmanager
def system_libraries():
    frozen_windows = sys.platform == "win32" and getattr(sys, "frozen", False)
    if frozen_windows:
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    try:
        yield
    finally:
        if frozen_windows:
            ctypes.windll.kernel32.SetDllDirectoryW(str(sys._MEIPASS))
