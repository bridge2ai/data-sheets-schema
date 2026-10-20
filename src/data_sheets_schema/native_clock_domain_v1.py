"""Private fixed, trusted-local-kernel clock consistency; no activated route.

No runner/profile/helper route selects this module. Kernel boot identity is not
host authentication. Saved validation performs no live clock or OS acquisition.
"""
import json
import os
import re
import sys
import threading
import time

FORMAT = 'native_clock_domain_v1'
MAX_DECLARATION_BYTES = 2048
MAX_BOOT_BYTES = 64
_UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
_IMPLEMENTATIONS = {'linux': 'clock_gettime(CLOCK_MONOTONIC)',
                    'darwin': 'mach_absolute_time()'}
_BOOT_PATH = '/proc/sys/kernel/random/boot_id'
_NAMESPACE_PATH = '/proc/thread-self/ns/time'
# Linux UAPI <linux/nsfs.h>: _IO(0xb7, 0x3); <linux/sched.h>.
_NS_GET_NSTYPE = 0xb703
_CLONE_NEWTIME = 0x00000080
_OMITTED = object()


class ClockDomainError(ValueError):
    """Unavailable, malformed or unequal domain; no deadline fallback."""


def _uuid(value):
    return (type(value) is str and _UUID.fullmatch(value) is not None
            and value != '00000000-0000-0000-0000-000000000000')


def _integer(value, minimum, maximum):
    return type(value) is int and minimum <= value <= maximum


def _encoded(value):
    if type(value) is not dict:
        raise ClockDomainError('clock domain must be a closed object')
    common = {'format', 'platform', 'clock', 'implementation', 'boot_uuid'}
    platform = value.get('platform')
    if type(platform) is not str or platform not in _IMPLEMENTATIONS:
        raise ClockDomainError('clock domain platform is unsupported')
    specific = 'time_namespace' if platform == 'linux' else 'timebase'
    if (set(value) != common | {specific} or type(value['format']) is not str
            or value['format'] != FORMAT or type(value['clock']) is not str
            or value['clock'] != 'monotonic_ns'
            or type(value['implementation']) is not str
            or value['implementation'] != _IMPLEMENTATIONS[platform]
            or not _uuid(value['boot_uuid'])):
        raise ClockDomainError('clock domain declaration differs from its closed contract')
    fields = value[specific]
    if type(fields) is not dict:
        raise ClockDomainError('clock domain platform fields must be a closed object')
    if platform == 'linux':
        valid = (set(fields) == {'device', 'inode', 'type'}
            and _integer(fields['device'], 0, 2**64 - 1)
            and _integer(fields['inode'], 1, 2**64 - 1)
            and type(fields['type']) is str and fields['type'] == 'CLONE_NEWTIME')
    else:
        valid = (set(fields) == {'numerator', 'denominator'}
            and all(_integer(fields[key], 1, 2**32 - 1) for key in fields))
    if not valid:
        raise ClockDomainError('clock domain platform fields are invalid')
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True,
                     separators=(',', ':'), allow_nan=False).encode('ascii')
    if len(raw) > MAX_DECLARATION_BYTES:
        raise ClockDomainError('clock domain exceeds its declaration bound')
    return raw


def validate_declaration(value):
    """Validate and detach saved claims only; this does not establish locality."""
    return json.loads(_encoded(value))


def _clock(platform):
    info = time.get_clock_info('monotonic')
    if (info.implementation != _IMPLEMENTATIONS[platform]
            or info.monotonic is not True or info.adjustable is not False):
        raise ClockDomainError('local monotonic clock implementation is unsupported')
    if platform == 'darwin' and (sys.implementation.name != 'cpython'
                                or sys.version_info < (3, 10)):
        raise ClockDomainError('local macOS Python clock contract is unsupported')
    return _IMPLEMENTATIONS[platform]


def _close_all(handles):
    """Close each owned descriptor once; report, but never retry, the first error."""
    first = None
    while handles:
        fd = handles.pop()
        try:
            os.close(fd)
        except BaseException as error:
            if first is None:
                first = error
    return first


def _read_boot_id():
    fd = os.open(_BOOT_PATH, os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK | os.O_NOFOLLOW)
    handles = [fd]
    try:
        parts, remaining = [], MAX_BOOT_BYTES + 1
        while remaining:
            part = os.read(fd, remaining)
            if not part:
                break
            parts.append(part)
            remaining -= len(part)
        raw = b''.join(parts)
        if len(raw) > MAX_BOOT_BYTES:
            raise ClockDomainError('local boot identifier exceeds its byte bound')
        if raw.endswith(b'\n'):
            raw = raw[:-1]
        value = raw.decode('ascii').lower()
        if not _uuid(value):
            raise ClockDomainError('local boot identifier is invalid')
    except BaseException:
        _close_all(handles)
        raise
    error = _close_all(handles)
    if error is not None:
        raise error
    return value


def _namespace(fd):
    import fcntl
    if fcntl.ioctl(fd, _NS_GET_NSTYPE) != _CLONE_NEWTIME:
        raise ClockDomainError('local namespace descriptor is not a time namespace')
    info = os.fstat(fd)
    fields = {'device': info.st_dev, 'inode': info.st_ino, 'type': 'CLONE_NEWTIME'}
    if not (_integer(fields['device'], 0, 2**64 - 1)
            and _integer(fields['inode'], 1, 2**64 - 1)):
        raise ClockDomainError('local namespace descriptor identity is invalid')
    return fields


def _linux():
    handles = []
    try:
        first = os.open(_NAMESPACE_PATH, os.O_RDONLY | os.O_CLOEXEC)
        handles.append(first)
        namespace = _namespace(first)
        implementation = _clock('linux')
        boot = _read_boot_id()
        second = os.open(_NAMESPACE_PATH, os.O_RDONLY | os.O_CLOEXEC)
        handles.append(second)
        if _namespace(second) != namespace:
            raise ClockDomainError('local time namespace changed during acquisition')
        # Remove ownership before close: an interrupted close must not cause
        # another close against a possibly recycled descriptor number.
        os.close(handles.pop())
        declaration = {'format': FORMAT, 'platform': 'linux', 'clock': 'monotonic_ns',
            'implementation': implementation, 'boot_uuid': boot, 'time_namespace': namespace}
        _encoded(declaration)
        handles.pop()  # Transfer exactly the first namespace descriptor.
        return declaration, first
    except BaseException as error:
        _close_all(handles)
        if isinstance(error, (KeyboardInterrupt, SystemExit, ClockDomainError)):
            raise
        raise ClockDomainError('Linux clock-domain acquisition unavailable') from error


def _darwin_values():
    """Two fixed in-process libSystem queries; no search, process or provider."""
    import ctypes
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
    sysctl = library.sysctlbyname
    sysctl.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                      ctypes.c_void_p, ctypes.c_size_t]
    sysctl.restype = ctypes.c_int
    output = ctypes.create_string_buffer(37)
    size = ctypes.c_size_t(37)
    if sysctl(b'kern.bootsessionuuid', output, ctypes.byref(size), None, 0) != 0:
        raise OSError(ctypes.get_errno(), 'kern.bootsessionuuid unavailable')
    if size.value != 37 or output.raw[-1:] != b'\0':
        raise ClockDomainError('macOS boot identifier has an invalid fixed shape')
    boot = output.raw[:-1].decode('ascii').lower()
    if not _uuid(boot):
        raise ClockDomainError('macOS boot identifier is invalid')

    class Timebase(ctypes.Structure):
        _fields_ = [('numer', ctypes.c_uint32), ('denom', ctypes.c_uint32)]

    timebase = library.mach_timebase_info
    timebase.argtypes = [ctypes.POINTER(Timebase)]
    timebase.restype = ctypes.c_int
    result = Timebase()
    if timebase(ctypes.byref(result)) != 0 or not result.numer or not result.denom:
        raise ClockDomainError('macOS Mach timebase unavailable')
    return boot, {'numerator': result.numer, 'denominator': result.denom}


def _darwin():
    try:
        implementation = _clock('darwin')
        boot, timebase = _darwin_values()
        declaration = {'format': FORMAT, 'platform': 'darwin', 'clock': 'monotonic_ns',
            'implementation': implementation, 'boot_uuid': boot, 'timebase': timebase}
        _encoded(declaration)
        return declaration, None
    except BaseException as error:
        if isinstance(error, (KeyboardInterrupt, SystemExit, ClockDomainError)):
            raise
        raise ClockDomainError('macOS clock-domain acquisition unavailable') from error


def _capture():
    if sys.platform == 'linux':
        return _linux()
    if sys.platform == 'darwin':
        return _darwin()
    raise ClockDomainError('local clock-domain platform is unsupported')


class _DomainLease:
    def __init__(self, declaration, namespace_fd):
        self._raw = _encoded(declaration)
        self._namespace_fd = namespace_fd
        self._closed = False
        self._close_error = None
        self._creator_thread = threading.current_thread()
        self._operation_active = False

    def _require_thread(self):
        if threading.current_thread() is not self._creator_thread:
            raise ClockDomainError('clock-domain lease belongs to another thread')

    def _begin_operation(self):
        self._require_thread()
        if self._operation_active:
            raise ClockDomainError('clock-domain lease operation is already active')
        self._operation_active = True

    def declaration(self):
        """Detached captured claim, readable after close without a live assertion."""
        return json.loads(self._raw)

    def require_current(self, expected=_OMITTED):
        """Reacquire on this thread and compare; never convert/reset a deadline."""
        self._begin_operation()
        try:
            if self._closed:
                raise ClockDomainError('clock-domain lease is closed')
            expected_raw = self._raw if expected is _OMITTED else _encoded(expected)
            if expected_raw != self._raw:
                raise ClockDomainError('owner and local clock domains differ')
            with capture_domain() as current:
                if current._raw != self._raw:
                    raise ClockDomainError('local clock domain changed')
        finally:
            self._operation_active = False

    def close(self):
        self._begin_operation()
        try:
            if self._closed:
                if self._close_error is not None:
                    raise self._close_error
                return
            self._closed = True
            fd, self._namespace_fd = self._namespace_fd, None
            if fd is not None:
                self._close_error = _close_all([fd])
                if self._close_error is not None:
                    raise self._close_error
        finally:
            self._operation_active = False

    def __enter__(self):
        self._require_thread()
        if self._operation_active:
            raise ClockDomainError('clock-domain lease operation is already active')
        if self._closed:
            raise ClockDomainError('clock-domain lease is closed')
        return self

    def __exit__(self, kind, error, traceback):
        self._require_thread()
        if self._operation_active:
            raise ClockDomainError('clock-domain lease operation is already active')
        if error is None:
            self.close()
        else:
            try:
                self.close()
            except BaseException:
                pass  # Preserve the original body exception and its traceback.
        return False


def capture_domain():
    """Acquire the fixed local domain, retaining its Linux namespace lifetime."""
    declaration, fd = _capture()
    try:
        return _DomainLease(declaration, fd)
    except BaseException:
        if fd is not None:
            _close_all([fd])
        raise
