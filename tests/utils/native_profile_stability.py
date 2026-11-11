"""WP1 diagnostic-only profile stability boundary, 2026-11-10.

Inputs: an already installed consumer observer and the unchanged synthetic
diagnostic body. Output: retained mutation-attempt and restoration evidence.
This is instrumentation, not a production policy or a hostile-extension sandbox.
Both compared arms must use it. Its audit overhead is part of the measured path.
"""
from contextlib import contextmanager
import sys
import threading


class ProfileMutationRefused(RuntimeError):
    """The observed body attempted to invalidate its observation instrument."""


_ACTIVE = None
_PROBE = None
_INSTALLED = False
_LOCK = threading.RLock()
_PROBE_EVENT = 'd4d.wp1.profile_stability_probe'
_REFUSED_EVENTS = frozenset(('sys.setprofile', 'sys.settrace',
                             'sys.monitoring.register_callback'))
_PROFILER_CONFLICT = 'Another profiling tool is already active'


def _raised(code, offset, exception):
    """Retain caught CPython profiler conflicts without replacing the exception.

    #5745: reservation prevents acquisition, but enable() does not audit its
    failed attempt. RAISE observes the exception reaching Python, including a
    call through a saved method or C adapter. CALL-only matching misses those
    adapters. An identical user-raised ValueError conservatively invalidates
    this diagnostic too; the event is evidence of a conflict, not provenance
    that uniquely identifies a caller or a hostile-extension security boundary.
    """
    active = _ACTIVE
    if (active is not None and type(exception) is ValueError
            and len(exception.args) == 1 and type(exception.args[0]) is str
            and exception.args[0] == _PROFILER_CONFLICT):
        active['attempts'].append({
            'event': 'profiler_acquisition_conflict',
            'thread': threading.get_ident(),
            'exception_type': 'ValueError', 'exception_message': _PROFILER_CONFLICT,
        })


def _audit(event, arguments):
    if event == _PROBE_EVENT:
        probe = _PROBE
        if probe is not None and len(arguments) == 1 and arguments[0] is probe['token']:
            probe['seen'] = True
        return
    active = _ACTIVE
    if active is None:
        return
    active['audit_events'] += 1
    if event in _REFUSED_EVENTS:
        # Do not filter by caller thread: all-thread setters can change the
        # observed thread from another thread. Attempts remain sticky if caught.
        active['attempts'].append({'event': event, 'thread': threading.get_ident()})
        raise ProfileMutationRefused('WP1 profile mutation refused: ' + event)


def _verify_installation():
    global _INSTALLED, _PROBE
    if not _INSTALLED:
        sys.addaudithook(_audit)
        _INSTALLED = True
    probe = {'token': object(), 'seen': False}
    _PROBE = probe
    try:
        sys.audit(_PROBE_EVENT, probe['token'])
    finally:
        _PROBE = None
    if not probe['seen']:
        raise RuntimeError('WP1 profile audit installation witness failed')


def _tools(monitor):
    return [(monitor.get_tool(tool), monitor.get_events(tool)) for tool in range(6)]


@contextmanager
def profile_stability_scope():
    """Refuse audited hook changes and reserve cProfile's public tool slot.

    On the pinned CPython 3.13 runtime, legacy and all-thread profile setters
    audit before C hook-state writes. cProfile instead claims public tool 2;
    reserving it refuses acquisition before callback setup. Its RAISE callback
    retains the exact conflict even when the observed body catches the error.
    Reserving 2 alone does not protect the internal legacy profiling tool 6.

    This boundary does not enforce arbitrary hostile C memory writes or transient
    monitoring-mask changes. Timing arms remain closed pending their other gates.
    """
    global _ACTIVE
    if sys.implementation.name != 'cpython' or sys.version_info[:2] != (3, 13):
        raise RuntimeError('WP1 profile boundary requires the pinned CPython 3.13 runtime')
    monitor = sys.monitoring
    tool = monitor.PROFILER_ID
    result = {'kind': 'wp1_profile_stability', 'installation_verified': False,
              'reserved_profiler_tool': tool, 'attempts': [], 'audit_events': 0,
              'profiler_conflict_observer': 'sys.monitoring.RAISE',
              'body_error': None, 'restored': False, 'completed': False,
              'stable': False, 'drift': [],
              'scope': 'Common audit guard overhead is included; no general observer equivalence or security claim.'}
    with _LOCK:
        if _ACTIVE is not None:
            raise RuntimeError('WP1 profile stability scopes cannot overlap')
        _verify_installation()
        result['installation_verified'] = True
        expected_profile = sys.getprofile()
        expected_future = threading.getprofile()
        expected_trace = sys.gettrace()
        if tool != 2 or monitor.get_tool(tool) is not None:
            raise RuntimeError('WP1 profiler reservation requires free tool 2')
        owner = 'd4d-wp1-profile-stability-' + str(id(result))
        monitor.use_tool_id(tool, owner)
        callback_installed = False
        previous_callback = None

        def release_profiler_tool():
            try:
                monitor.set_events(tool, 0)
            finally:
                try:
                    if callback_installed:
                        monitor.register_callback(tool, monitor.events.RAISE, previous_callback)
                finally:
                    monitor.free_tool_id(tool)

        try:
            if monitor.get_events(tool) != 0:
                raise RuntimeError('WP1 profiler reservation must have zero events')
            previous_callback = monitor.register_callback(tool, monitor.events.RAISE, _raised)
            callback_installed = True
            monitor.set_events(tool, monitor.events.RAISE)
            expected_tools = _tools(monitor)
            _ACTIVE = result
        except BaseException:
            if monitor.get_tool(tool) == owner:
                release_profiler_tool()
            raise
    try:
        yield result
    except BaseException as exc:
        result['body_error'] = type(exc).__name__
        raise
    finally:
        with _LOCK:
            # Compare while active; deactivate before instrumentation restoration.
            if sys.getprofile() is not expected_profile:
                result['drift'].append('current_thread_profile')
            if threading.getprofile() is not expected_future:
                result['drift'].append('future_thread_profile')
            if sys.gettrace() is not expected_trace:
                result['drift'].append('current_thread_trace')
            if _tools(monitor) != expected_tools:
                result['drift'].append('public_monitoring_owners_or_masks')
            if _ACTIVE is not result:
                result['drift'].append('guard_ownership')
            _ACTIVE = None
            try:
                # threading.setprofile_all_threads sets this Python default
                # before its audited C call; restore even when that call refused.
                threading.setprofile(expected_future)
                if sys.getprofile() is not expected_profile:
                    sys.setprofile(expected_profile)
                if sys.gettrace() is not expected_trace:
                    sys.settrace(expected_trace)
            finally:
                if monitor.get_tool(tool) != owner:
                    result['drift'].append('reserved_tool_ownership')
                else:
                    release_profiler_tool()
            result['restored'] = (sys.getprofile() is expected_profile
                and threading.getprofile() is expected_future
                and sys.gettrace() is expected_trace and monitor.get_tool(tool) is None)
            result['stable'] = not result['attempts'] and not result['drift'] and result['restored']
            result['completed'] = result['stable'] and result['body_error'] is None
        if not result['stable']:
            raise ProfileMutationRefused('WP1 profile scope invalidated by mutation attempt or state drift')
