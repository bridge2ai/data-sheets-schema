"""Real A/C consumer scopes and non-mutating test observations for U3-D R9.

Tests keep invented input data, but use the source-loaded production consumers
and their genuine classifier projection. No verifier or mint is substituted.
"""
from contextlib import contextmanager
import sys
import threading

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_controls_orchestration as controls


@contextmanager
def loaded_consumer(name, dependencies=None):
    dependencies = authority.dependency_identity() if dependencies is None else dependencies
    with authority.loaded_verified_package_module(
            'data_sheets_schema.' + name,
            package_sources=dependencies['base']['package_sources']) as consumer:
        yield consumer


def command_guidance(policy):
    dependencies = authority.dependency_identity()
    with controls.loaded_controls(dependencies) as projection, \
            loaded_consumer('native_shared_policy', dependencies) as policy_consumer:
        return policy_consumer.command_guidance(policy, classifier_projection=projection)


@contextmanager
def observe_consumer_calls(targets, *, refuse=None, forbid=False, arm='legacy'):
    """Observe actual function entry without changing any pinned callable.

    ``targets`` maps (module basename, function name) to local names to retain.
    The optional refusal is a deliberately injected test exception at that
    actual function entry, so a cached result cannot masquerade as a fresh call.
    ``legacy`` is the default for existing tests. The experimental ``monitoring``
    arm uses current-thread entry/resume events, without disabling code objects.
    Its matcher deliberately has no repository-root filter: verified consumers
    can be reloaded under a different source path with the same basename.

    A pre-existing callable profile hook needs its original before-observation
    ordering. In that case only, monitoring uses an ordered profile compatibility
    shim rather than relying on CPython's ordering of independent tool callbacks.
    The diagnostic timing arms require no prior hook and do not measure this shim.
    """
    if arm not in {'legacy', 'monitoring'}:
        raise ValueError('consumer observer arm must be legacy or monitoring')
    calls = []
    previous = sys.getprofile()
    names = frozenset(name for _, name in targets)

    def record(frame):
        # Most calls cannot match. Avoid parsing every unrelated filename while
        # the genuine source checks and historical callbacks are running.
        if frame.f_code.co_name not in names:
            return
        key = (frame.f_code.co_filename.rsplit('/', 1)[-1].removesuffix('.py'),
               frame.f_code.co_name)
        if key not in targets:
            return
        calls.append((key, {name: frame.f_locals[name]
                            for name in targets[key] if name in frame.f_locals}))
        if forbid:
            raise AssertionError('forbidden production operation: ' + '.'.join(key))
        if refuse is not None and key == refuse[0]:
            raise refuse[1]

    def observe(frame, event, argument):
        if previous is not None:
            previous(frame, event, argument)
        if event != 'call':
            return
        # Preserve the legacy callback body (including its fast name rejection)
        # instead of adding a helper dispatch to every measured legacy call.
        if frame.f_code.co_name not in names:
            return
        key = (frame.f_code.co_filename.rsplit('/', 1)[-1].removesuffix('.py'),
               frame.f_code.co_name)
        if key not in targets:
            return
        calls.append((key, {name: frame.f_locals[name]
                            for name in targets[key] if name in frame.f_locals}))
        if forbid:
            raise AssertionError('forbidden production operation: ' + '.'.join(key))
        if refuse is not None and key == refuse[0]:
            raise refuse[1]

    if arm == 'legacy':
        sys.setprofile(observe)
        try:
            yield calls
        finally:
            sys.setprofile(previous)
        return

    monitor = getattr(sys, 'monitoring', None)
    if monitor is None:
        raise RuntimeError('consumer monitoring requires a sys.monitoring interpreter')
    if previous is not None and not callable(previous):
        raise TypeError('consumer monitoring cannot chain a non-callable profile hook')
    thread = threading.get_ident()
    tool = None
    owner = 'd4d-wp1-consumer-' + str(thread) + '-' + str(id(calls))
    enabled = True
    events = (monitor.events.PY_START, monitor.events.PY_RESUME, monitor.events.PY_THROW)

    def start(code, offset, *arguments):
        nonlocal enabled
        if not enabled or threading.get_ident() != thread or previous is not None:
            return
        if code.co_name not in names:
            return
        # PY_START runs at the target's entry. Never read locals from a callback
        # frame, a caller, or an unexpected interpreter frame on a guessed index.
        frame = sys._getframe(1)
        if frame.f_code is not code:
            enabled = False
            raise RuntimeError('consumer monitoring frame identity mismatch')
        try:
            record(frame)
        except BaseException:
            # A legacy profile callback that raises is cleared by CPython. If
            # the test catches that exception inside the scope, do not silently
            # resume observation on subsequent calls in the monitoring arm.
            enabled = False
            raise

    # Scope setup/teardown must not leak a claimed tool if a pre-existing profile
    # hook raises on a monitoring builtin's c_return. Temporarily suspend that
    # hook around tool management, and restore the captured state last (even None).
    claimed = False
    try:
        if previous is not None:
            sys.setprofile(None)
        tool = next((value for value in (5, 4, 3) if monitor.get_tool(value) is None), None)
        if tool is None:
            raise RuntimeError('no free monitoring slot for consumer observer')
        monitor.use_tool_id(tool, owner)
        claimed = True
        for event in events:
            monitor.register_callback(tool, event, start)
        monitor.set_events(tool, events[0] | events[1] | events[2])
        if previous is not None:
            sys.setprofile(observe)
        yield calls
    finally:
        try:
            try:
                # A hook installed by the body must not interrupt cleanup either.
                sys.setprofile(None)
            finally:
                current = monitor.get_tool(tool) if tool is not None else None
                if current == owner:
                    try:
                        monitor.set_events(tool, 0)
                    finally:
                        try:
                            # Attempt every unregister even if one refuses;
                            # incomplete cleanup remains a failed canary.
                            errors = []
                            for event in events:
                                try:
                                    monitor.register_callback(tool, event, None)
                                except BaseException as exc:
                                    errors.append(exc)
                            if errors:
                                raise errors[0]
                        finally:
                            monitor.free_tool_id(tool)
                elif claimed:
                    raise RuntimeError('consumer monitoring tool ownership changed')
        finally:
            sys.setprofile(previous)
