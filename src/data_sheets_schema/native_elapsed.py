"""Suspension-inclusive, non-adjustable elapsed time for attempt deadlines."""
import ctypes
from functools import lru_cache
import sys
import time


@lru_cache(maxsize=1)
def _mach_clock():
    # macOS SDK mach/mach_time.h: mach_continuous_time is "like
    # mach_absolute_time, but advances during sleep" (available since 10.12).
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
    class Timebase(ctypes.Structure):
        _fields_ = [('numer', ctypes.c_uint32), ('denom', ctypes.c_uint32)]
    conversion = library.mach_timebase_info
    conversion.argtypes = [ctypes.POINTER(Timebase)]
    conversion.restype = ctypes.c_int
    scale = Timebase()
    if conversion(ctypes.byref(scale)) != 0 or not scale.numer or not scale.denom:
        raise RuntimeError('continuous clock timebase unavailable')
    clock = library.mach_continuous_time
    clock.argtypes = []
    clock.restype = ctypes.c_uint64
    return clock, scale.numer, scale.denom


def elapsed_ns():
    """Never fall back to an adjustable or suspension-excluding clock."""
    if sys.platform == 'darwin':
        clock, numer, denom = _mach_clock()
        return clock() * numer // denom
    if sys.platform.startswith('linux') and hasattr(time, 'CLOCK_BOOTTIME'):
        return time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    raise RuntimeError('suspension-inclusive elapsed clock unavailable on this platform')
