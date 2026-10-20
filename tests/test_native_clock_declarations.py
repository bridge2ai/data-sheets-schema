"""Offline declaration reuse oracles; kernel observations remain fresh."""
import ctypes
import threading

import pytest

from data_sheets_schema import native_clock_domain_v1 as clocks


BOOT_A = '12345678-1234-1234-1234-123456789abc'
BOOT_B = '87654321-4321-4321-4321-cba987654321'


class Function:
    def __init__(self, call):
        self.call = call

    def __call__(self, *args):
        return self.call(*args)


class Library:
    def __init__(self):
        self.boot = BOOT_A
        self.size = 37
        self.sysctl_status = 0
        self.mach_status = 0
        self.timebase = (1, 1)
        self.missing_mach = False
        self.buffers = []
        self.sizes = []
        self.results = []
        self.mach_lookups = 0
        self.events = []
        self.sysctlbyname = Function(self.sysctl)
        self.mach = Function(self.query_mach)

    def sysctl(self, name, output, size, new_value, new_size):
        assert name == b'kern.bootsessionuuid'
        assert new_value is None and new_size == 0
        self.events.append('sysctl')
        self.buffers.append(output)
        self.sizes.append(size._obj)
        output.raw = self.boot.encode('ascii') + b'\0'
        size._obj.value = self.size
        return self.sysctl_status

    @property
    def mach_timebase_info(self):
        self.events.append('mach_binding')
        self.mach_lookups += 1
        if self.missing_mach:
            raise OSError('invented missing Mach symbol')
        return self.mach

    def query_mach(self, result):
        self.events.append('mach')
        value = result._obj
        self.results.append(value)
        value.numer, value.denom = self.timebase
        return self.mach_status


@pytest.fixture
def backend(monkeypatch):
    libraries, loads = [Library()], []

    def load(path, *, use_errno):
        assert path == '/usr/lib/libSystem.B.dylib' and use_errno is True
        loads.append(path)
        return libraries[-1]

    monkeypatch.setattr(ctypes, 'CDLL', load)
    monkeypatch.setattr(clocks, '_DARWIN_BINDINGS', threading.local())
    return libraries, loads


def test_reuses_declarations_but_observes_changed_kernel_values(backend):
    libraries, loads = backend
    library = libraries[0]
    assert clocks._darwin_values() == (BOOT_A, {'numerator': 1, 'denominator': 1})
    library.boot, library.timebase = BOOT_B, (125, 3)
    assert clocks._darwin_values() == (BOOT_B, {'numerator': 125, 'denominator': 3})
    assert len(loads) == 1 and library.mach_lookups == 1
    assert library.events == ['sysctl', 'mach_binding', 'mach', 'sysctl', 'mach']
    for objects in (library.buffers, library.sizes, library.results):
        assert len(objects) == 2 and objects[0] is not objects[1]
    assert type(library.results[0]) is type(library.results[1])


@pytest.mark.parametrize('attribute,value,error,match,mach_calls', [
    ('sysctl_status', 1, OSError, 'kern.bootsessionuuid unavailable', 1),
    ('size', 36, clocks.ClockDomainError, 'invalid fixed shape', 1),
    ('boot', '00000000-0000-0000-0000-000000000000',
        clocks.ClockDomainError, 'boot identifier is invalid', 1),
    ('mach_status', 1, clocks.ClockDomainError, 'Mach timebase unavailable', 2),
    ('timebase', (0, 1), clocks.ClockDomainError, 'Mach timebase unavailable', 2),
    ('timebase', (1, 0), clocks.ClockDomainError, 'Mach timebase unavailable', 2),
])
def test_warm_declarations_do_not_hide_current_query_failures(
        backend, attribute, value, error, match, mach_calls):
    libraries, loads = backend
    library = libraries[0]
    clocks._darwin_values()
    setattr(library, attribute, value)
    with pytest.raises(error, match=match):
        clocks._darwin_values()
    assert len(loads) == 1 and len(library.buffers) == 2
    assert len(library.results) == mach_calls and library.mach_lookups == 1


def test_bad_boot_precedes_mach_binding_and_failed_bindings_are_not_retained(backend):
    libraries, loads = backend
    library = libraries[0]
    library.size, library.missing_mach = 36, True
    with pytest.raises(clocks.ClockDomainError, match='invalid fixed shape'):
        clocks._darwin_values()
    assert library.events == ['sysctl']
    library.size = 37
    with pytest.raises(OSError, match='invented missing Mach symbol'):
        clocks._darwin_values()
    assert library.events == ['sysctl', 'sysctl', 'mach_binding']
    library.missing_mach = False
    assert clocks._darwin_values()[0] == BOOT_A
    assert library.events[-3:] == ['sysctl', 'mach_binding', 'mach']
    assert len(loads) == 1 and library.mach_lookups == 2


def test_changed_cdll_constructor_uses_new_bindings(backend, monkeypatch):
    libraries, loads = backend
    clocks._darwin_values()
    replacement = Library()
    replacement.boot, replacement.timebase = BOOT_B, (5, 2)
    monkeypatch.setattr(ctypes, 'CDLL', lambda *args, **kwargs: replacement)
    assert clocks._darwin_values() == (BOOT_B, {'numerator': 5, 'denominator': 2})
    assert len(loads) == 1 and len(libraries[0].buffers) == 1
    assert replacement.mach_lookups == 1


def test_changed_pointer_factory_rebuilds_signatures(backend, monkeypatch):
    libraries, loads = backend
    library = libraries[0]
    clocks._darwin_values()
    original_pointer, observed = ctypes.POINTER, []

    def pointer(value):
        observed.append(value)
        return original_pointer(value)

    monkeypatch.setattr(ctypes, 'POINTER', pointer)
    clocks._darwin_values()
    assert len(loads) == 2 and library.mach_lookups == 2
    assert observed == [ctypes.c_size_t, type(library.results[-1])]
    assert type(library.results[0]) is not type(library.results[1])


def test_threads_have_distinct_function_signatures_and_timebase_types(monkeypatch):
    libraries, outcomes, failures = [], [], []

    def load(*args, **kwargs):
        library = Library()
        libraries.append(library)
        return library

    def query_twice():
        try:
            outcomes.append((clocks._darwin_values(), clocks._darwin_values()))
        except BaseException as error:
            failures.append(error)

    monkeypatch.setattr(ctypes, 'CDLL', load)
    monkeypatch.setattr(clocks, '_DARWIN_BINDINGS', threading.local())
    workers = [threading.Thread(target=query_twice) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=5)
    assert not any(worker.is_alive() for worker in workers)
    assert not failures and len(outcomes) == 2 and outcomes[0] == outcomes[1]
    assert len(libraries) == 2
    assert all(len(lib.results) == 2 and lib.mach_lookups == 1 for lib in libraries)
    assert libraries[0].mach is not libraries[1].mach
    assert type(libraries[0].results[0]) is not type(libraries[1].results[0])
