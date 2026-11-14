"""Produce existing native permission manifests from actual process evidence.

#4760/#4759, U4 preparation, 2026-11-08. Includes static binary verification.
No simulator, executable discovery or provider fallback.
Calling produce_saved_probe is an explicit live-binary action; offline tests
must mock its process boundary and must not call the registered native binary.
"""
from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import threading
import time

from .native_subscription_guard import canonical, read_regular, sha, strict_json
from .native_probe_provider import local_provider
from .native_path_identity import overlaps

MAX_STREAM = 8 * 1024 * 1024
MAX_PROBE_SECONDS = 600
U4_ACCOUNT_LABEL = 'LBL work Claude Max'
U4_EFFORT = 'high'
U4_RECEIPT_INSTRUMENT = 4


@contextmanager
def _probe_signals():
    """Turn the first stop into unwinding; subsequent stops cannot abort it."""
    previous = {}
    def stop(signum, frame):
        for number in previous:
            signal.signal(number, signal.SIG_IGN)
        raise InterruptedError("permission probe stopped by signal " + str(signum))
    try:
        for number in (signal.SIGINT, signal.SIGTERM):
            previous[number] = signal.signal(number, stop)
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


@contextmanager
def _cleanup_signals():
    previous = {number: signal.signal(number, signal.SIG_IGN)
                for number in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def require_u4_runtime(runtime):
    """Validate D106's saved selection, without querying an account or binary.

    The declaration records selected auth expectations, not authenticated
    account identity. The external owner-choice record binds the LBL label.
    Live account/headroom evidence is still a separately authorized gate.
    """
    from . import native_shared_permissions as permission
    permission._runtime(runtime)
    if runtime['effort'] != U4_EFFORT:
        raise ValueError('D106 requires explicit native effort high')
    if runtime['auth']['subscriptionType'] != 'max':
        raise ValueError('D106 requires the selected Max subscription')


def require_u4_expectation(expected):
    """Accept only the shared protocol and D106 runtime; no legacy fallback.

    This check reads no selected files. Genuine receipt-policy v4 is checked
    when producing from a captured selection or verifying an execution body;
    a saved probe alone is not a new receipt-policy or account attestation.
    """
    from . import native_shared_permissions as permission
    permission._object(expected, permission.EXPECTED_KEYS, 'U4 expected')
    if (expected['kind'] != permission.EXPECTED_KIND
            or type(expected['version']) is not int
            or expected['version'] != permission.VERSION):
        raise ValueError('unsupported U4 shared permission expectation')
    require_u4_runtime(expected['runtime'])


class _Transport:
    """Two source-attested host capabilities; never C's classifier carrier."""
    __slots__ = ('_native', '_budget', '_pins', '_attestor', '_active',
                 '_control_type', '_stop_type')

    def __init__(self, dependencies, attestor):
        self._native, self._budget = sys.modules.get('native_control'), sys.modules.get('budgeted_cborg')
        self._pins = tuple({'name': name,
            'path': str(Path(__file__).resolve().parents[2] / dependencies['base']['modules'][name]['path']),
            'sha256': dependencies['base']['modules'][name]['sha256']}
            for name in ('native_control', 'budgeted_cborg'))
        self._attestor, self._active = attestor, True
        self._control_type = getattr(self._native, 'NativeControl', None)
        self._stop_type = getattr(self._budget, 'BudgetStop', None)
        self.check()

    def check(self):
        if (not self._active or not isinstance(self._control_type, type)
                or not isinstance(self._stop_type, type)
                or not issubclass(self._stop_type, Exception)):
            raise ValueError('permission transport capability is unavailable or expired')
        for module, pin in zip((self._native, self._budget), self._pins):
            if self._attestor(module) != pin:
                raise ValueError('permission transport source identity differs')
        if (getattr(self._native, 'NativeControl', None) is not self._control_type
                or getattr(self._budget, 'BudgetStop', None) is not self._stop_type):
            raise ValueError('permission transport member changed')

    @property
    def budget_stop(self):
        self.check()
        return self._stop_type

    def control(self, *args, **kwargs):
        self.check()
        value = self._control_type(*args, **kwargs)
        self.check()
        return value


@contextmanager
def _loaded_probe_inputs(expected):
    """Capture all genuine inputs on the main thread and retain their lifetime.

    A's public map and loader are unchanged. C supplies the pure projection;
    the separate host projection exposes only NativeControl and BudgetStop.
    Callbacks never enter a loader or obtain a new authority object.
    """
    from . import native_execution_authority_v2 as authority
    from . import native_shared_permission_orchestration as permission
    from . import native_shared_selection as selection
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('permission probe capture requires the main thread')
    require_u4_expectation(expected)
    dependencies = authority.dependency_identity()
    captured = selection.capture(expected['selection']['path'])
    selected = captured.document()
    selection_raw = captured.registration.raw
    transport = None
    with permission.loaded_permission_inputs(dependencies) as (controls, sources), \
            authority.loaded_verified_package_module('data_sheets_schema.native_shared_permissions',
                package_sources=dependencies['base']['package_sources']) as consumer:
        try:
            consumer._pin(expected['selection'], selection_raw)
            consumer._authority(expected, selected, sources)
            receipt = consumer.contract.parse_receipt_policy(captured.receipt_policy.raw)
            if receipt['receipt_instrument_version'] != U4_RECEIPT_INSTRUMENT:
                raise ValueError('D105 retains receipt instrument v4')
            # Populate fixed package dependencies before the controller workers.
            consumer._dependencies()
            consumer._permission_protocol()
            transport = _Transport(dependencies, authority.module_source_identity)
            yield consumer, controls, sources, transport, selected, selection_raw
            transport.check()
            if authority.dependency_identity() != dependencies:
                raise ValueError('permission dependency identity changed during capture')
        finally:
            if transport is not None:
                transport._active = False


def _bounded_binary_check(argv, *, stdin, capture_output, timeout, check, env, cwd):
    """Concurrent bounded capture and process-group cleanup for offline checks."""
    if stdin != subprocess.DEVNULL or capture_output is not True or check is not False:
        raise ValueError("binary checks require closed stdin and explicit result inspection")
    deadline = time.monotonic() + timeout
    process = None
    output = {"stdout": bytearray(), "stderr": bytearray()}
    try:
        with selectors.DefaultSelector() as selector:
            process = subprocess.Popen(
                argv, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=env, cwd=cwd, start_new_session=True)
            for name in output:
                stream = getattr(process, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or process.poll() is None:
                if time.monotonic() >= deadline:
                    raise subprocess.TimeoutExpired(argv, timeout)
                for key, _ in selector.select(timeout=min(0.02, max(0, deadline - time.monotonic()))):
                    raw = os.read(key.fd, 4097 - len(output[key.data]))
                    if not raw:
                        selector.unregister(key.fileobj)
                    else:
                        if len(output[key.data]) + len(raw) > 4096:
                            raise ValueError("binary check output exceeds its byte bound")
                        output[key.data].extend(raw)
            return subprocess.CompletedProcess(
                argv, process.returncode, bytes(output["stdout"]), bytes(output["stderr"]))
    finally:
        try:
            _terminate(process)
        finally:
            if process is not None:
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()


def verify_retained_binary(pins, *, allow_resolved_symlink=False,
                           require_macho=True, check_version=False,
                           check_codesign=False, runner=None, timeout_seconds=10):
    """Verify #4759 retained executable pins without launching by default.

    ``pins`` is a registration's runtime.executable block. Static verification
    never discovers a binary or invokes one. Explicit version/signature flags
    enable a bounded process-group runner; offline unit tests inject mocks.
    A supplied runner replaces that boundary and must enforce equivalent limits.
    Only ``--version`` and the system codesign verifier are allowed.
    A Mach-O magic check identifies a format, not executable compatibility.
    No result grants permission to run a generation or replaces its registration.
    """
    from .native_shared_runtime_values import executable_identity

    if (not isinstance(pins, dict)
            or not {"path", "sha256", "version"} <= set(pins)
            or set(pins) - {"path", "sha256", "version", "init_version"}):
        raise ValueError("binary pins require path, sha256 and version")
    if (not isinstance(pins["sha256"], str)
            or re.fullmatch(r"[a-f0-9]{64}", pins["sha256"]) is None):
        raise ValueError("binary SHA256 must be an exact lowercase digest")
    if (not isinstance(pins["version"], str) or not pins["version"].strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in pins["version"])):
        raise ValueError("binary version must be a nonempty single-line pin")
    for flag in (allow_resolved_symlink, require_macho, check_version, check_codesign):
        if type(flag) is not bool:
            raise ValueError("binary verification options must be booleans")
    if (type(timeout_seconds) not in (int, float)
            or not 0 < timeout_seconds <= 60):
        raise ValueError("binary check timeout must be within (0, 60] seconds")
    if runner is None:
        runner = _bounded_binary_check
    if not isinstance(pins["path"], str) or not pins["path"]:
        raise ValueError("binary path must be an absolute path")
    selected = Path(pins["path"])
    if not selected.is_absolute() or ".." in selected.parts:
        raise ValueError("binary path must be absolute without parent traversal")
    resolved = selected.resolve(strict=True)
    if resolved != selected and not allow_resolved_symlink:
        raise ValueError("binary symlink requires explicit resolved-path permission")
    if not resolved.is_file():
        raise ValueError("retained binary must be a regular executable file")

    def capture():
        if selected.resolve(strict=True) != resolved:
            raise ValueError("retained binary path changed during verification")
        value = executable_identity(resolved)
        if value["sha256"] != pins["sha256"]:
            raise ValueError("retained binary differs from registered SHA256")
        return value

    observed = capture()
    with resolved.open("rb") as stream:
        magic = stream.read(4)
    macho = magic in {
        b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca",
    }
    if require_macho and (not macho or observed["bytes"] < 28):
        raise ValueError("retained binary does not have a Mach-O header")
    result = {
        "path": pins["path"], "resolved_path": str(resolved),
        "sha256": observed["sha256"], "bytes": observed["bytes"],
        "macho_magic": macho, "expected_version": pins["version"],
        "observed_version": None, "version_verified": False,
        "codesign_verified": False,
    }
    if check_version or check_codesign:
        # Never inherit account credentials, config or provider route. This is
        # an offline version check, not an account or permission probe.
        with tempfile.TemporaryDirectory(prefix="d4d-binary-verify-") as directory:
            environment = {
                "PATH": "/usr/bin:/bin", "HOME": directory,
                "CLAUDE_CONFIG_DIR": directory,
                "ANTHROPIC_BASE_URL": "http://127.0.0.1:1",
                "ANTHROPIC_API_KEY": "d4d-offline-version-only",
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                "DISABLE_AUTOUPDATER": "1",
            }
            commands = []
            if check_version:
                commands.append(("version", [str(resolved), "--version"]))
            if check_codesign:
                commands.append(("codesign", [
                    "/usr/bin/codesign", "--verify", "--strict", str(resolved)]))
            for kind, argv in commands:
                capture()
                completed = runner(
                    argv, stdin=subprocess.DEVNULL, capture_output=True,
                    timeout=timeout_seconds, check=False, env=environment,
                    cwd=directory)
                capture()
                if (type(completed.stdout) is not bytes or type(completed.stderr) is not bytes
                        or max(len(completed.stdout), len(completed.stderr)) > 4096):
                    raise ValueError("binary check requires bounded byte output")
                if completed.returncode != 0:
                    raise ValueError(f"retained binary {kind} check failed")
                if kind == "version":
                    if (completed.stderr
                            or completed.stdout != (pins["version"] + "\n").encode()):
                        raise ValueError("observed binary version differs from registration")
                    result.update(observed_version=pins["version"], version_verified=True)
                else:
                    result["codesign_verified"] = True
    capture()
    return result


def _remaining(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError("permission probe deadline elapsed")


class _Bounded:
    def __init__(self, stream, limit):
        self.stream, self.limit, self.count = stream, limit, 0

    def write(self, value):
        self.count += len(value.encode() if isinstance(value, str) else value)
        if self.count > self.limit:
            raise ValueError("permission probe stream exceeds its byte bound")
        return self.stream.write(value)

    def flush(self):
        return self.stream.flush()


def _terminate(process):
    """Terminate/reap the group; leader exit never excuses a signal denial.

    Even when the host refuses a group signal, attempt a bounded direct-child
    reap. Preserve the signal error: reaping the leader does not establish that
    inherited pipe holders or other members of its group have stopped.
    """
    if process is None:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass
        finally:
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
    if process.poll() is None:
        raise RuntimeError("permission child could not be reaped")


def _identity(expected):
    from .native_shared_runtime_values import executable_identity
    wanted = expected["runtime"]["executable"]
    observed = executable_identity(wanted["path"])
    if observed["sha256"] != wanted["sha256"]:
        raise ValueError("permission probe executable differs from registered SHA256")
    return observed


def _version(expected, deadline, directory):
    """Bound stdout/stderr and the whole version check; no blocking readline."""
    _identity(expected)
    _remaining(deadline)
    process = None
    outputs = {"stdout": bytearray(), "stderr": bytearray()}
    try:
        with selectors.DefaultSelector() as selector:
            process = subprocess.Popen([expected["runtime"]["executable"]["path"], "--version"],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env={**expected["permission_environment"],
                     "CLAUDE_CONFIG_DIR": str(directory / "version-config"),
                     "ANTHROPIC_BASE_URL": "http://127.0.0.1:1",
                     "ANTHROPIC_API_KEY": "d4d-local-permission-probe-token"},
                start_new_session=True)
            for role in outputs:
                stream = getattr(process, role)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, role)
            while selector.get_map() or process.poll() is None:
                if time.monotonic() >= deadline:
                    raise TimeoutError("permission probe deadline elapsed during version check")
                for key, _ in selector.select(timeout=0.02):
                    raw = os.read(key.fd, 4096)
                    if not raw:
                        selector.unregister(key.fileobj)
                    else:
                        outputs[key.data].extend(raw)
                        if len(outputs[key.data]) > 4096:
                            raise ValueError("permission version output exceeds its bound")
            if process.returncode != 0 or outputs["stderr"]:
                raise ValueError("registered binary version check did not complete cleanly")
        raw = bytes(outputs["stdout"])
        if raw != (expected["runtime"]["executable"]["version"] + "\n").encode():
            raise ValueError("observed native version differs from registration")
        return raw
    finally:
        with _cleanup_signals():
            try:
                _terminate(process)
            finally:
                if process is not None:
                    for stream in (process.stdout, process.stderr):
                        if stream is not None:
                            stream.close()
                _write_new(directory / "version.stdout", bytes(outputs["stdout"]))
                _write_new(directory / "version.stderr", bytes(outputs["stderr"]))


def _pipe_tail(stream, limit, deadline):
    """Retain raw shutdown bytes without parsing or dispatching callbacks."""
    output = bytearray()
    if stream is None or stream.closed:
        return b"", "unavailable"
    try:
        os.set_blocking(stream.fileno(), False)
        while time.monotonic() < deadline:
            try:
                raw = os.read(stream.fileno(), min(65536, limit - len(output) + 1))
            except BlockingIOError:
                time.sleep(0.001)
                continue
            if not raw:
                return bytes(output), "eof"
            remaining = limit - len(output)
            output.extend(raw[:remaining])
            if len(raw) > remaining:
                return bytes(output), "byte_limit"
        return bytes(output), "time_limit"
    except OSError as exc:
        return bytes(output), type(exc).__name__


def _run_native(expected, launch, policy, observer, classifier, transport, server, deadline):
    """Actual native process with bounded I/O and the existing control protocol."""
    budget_stop = transport.budget_stop
    control = transport.control(policy, classifier, launch["config_root"], event_observer=observer)
    process = None
    transcript, journal, stderr = io.BytesIO(), io.StringIO(), bytearray()
    stopped, stderr_closed = False, False
    tail, drainage = b"", {}
    try:
        _identity(expected)
        if time.monotonic() >= deadline:
            raise TimeoutError("permission probe deadline elapsed before process creation")
        process = subprocess.Popen(launch["argv"], cwd=launch["cwd"], env=launch["environment"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        os.set_blocking(process.stderr.fileno(), False)
        control.start(process, _Bounded(transcript, MAX_STREAM), _Bounded(journal, MAX_STREAM),
                      "Execute the scripted local permission cases in order, then finish.")
        while process.poll() is None or not control.stdout_closed or not stderr_closed:
            if time.monotonic() >= deadline:
                raise TimeoutError("permission probe deadline elapsed")
            if server.failure is not None:
                raise ValueError("scripted permission provider failed") from server.failure
            try:
                raw = os.read(process.stderr.fileno(), 65536)
                stderr_closed = not raw
            except BlockingIOError:
                raw = b""
            stderr.extend(raw)
            if len(stderr) > MAX_STREAM:
                raise ValueError("permission stderr exceeds its byte bound")
            control.service()
        control.finish()
    except budget_stop:
        # Only a durable exact expected effect-stop observed by this controller
        # may yield a negative trace. Other failures are never a passed probe.
        if getattr(observer, "expected_stop", False):
            stopped = True
        else:
            raise
    finally:
        with _cleanup_signals():
            try:
                _terminate(process)
            finally:
                try:
                    if process is not None:
                        drain_deadline = time.monotonic() + 1
                        tail, drainage['stdout'] = _pipe_tail(process.stdout, MAX_STREAM, drain_deadline)
                        extra, drainage['stderr'] = _pipe_tail(
                            process.stderr, max(0, MAX_STREAM - len(stderr)), drain_deadline)
                        stderr.extend(extra)
                    control.close()
                finally:
                    if process is not None:
                        for stream in (process.stdin, process.stdout, process.stderr):
                            if stream is not None and not stream.closed:
                                stream.close()
                    # Preserve even timeout/refusal/overflow traces. Publication
                    # still requires a full independently verified manifest.
                    evidence = Path(launch["config_root"]).parent
                    _write_new(evidence / "transcript.jsonl", transcript.getvalue())
                    _write_new(evidence / "control.jsonl", journal.getvalue().encode())
                    _write_new(evidence / "stderr.txt", bytes(stderr))
                    _write_new(evidence / "stdout.unprocessed", tail)
                    _write_new(evidence / "cleanup.json", canonical({
                        'drainage': drainage, 'child_reaped': process is not None and process.poll() is not None,
                        'control_shutdown_complete': control.control_shutdown_complete,
                        'unfinished_control_workers': control.unfinished_control_workers}))
    if any(status != 'eof' for status in drainage.values()):
        raise ValueError("permission pipe drainage was incomplete")
    if tail and not stopped:
        raise ValueError("permission process left unprocessed stdout")
    if (not control.control_shutdown_complete or control.unfinished_control_workers != 0
            or process is None or process.poll() is None):
        raise ValueError("permission probe cleanup was incomplete")
    _identity(expected)
    transport.check()
    if not stopped and process.returncode != 0:
        raise ValueError("permission probe native process failed")
    return {
        "transcript.jsonl": transcript.getvalue(),
        "control.jsonl": journal.getvalue().encode(),
        "stderr.txt": bytes(stderr),
        "exit_code": process.returncode,
        "shutdown": {"control_initialized": control.initialized,
                     "control_shutdown_complete": control.control_shutdown_complete,
                     "unfinished_control_workers": control.unfinished_control_workers,
                     "child_reaped": process.poll() is not None},
    }


def _write_new(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _inventory(p, expected, selected, launch, session):
    """Capture actual files, including absent destinations; never synthesize after."""
    shape = p._inventory(expected, selected, launch, session, completed=False)
    for row in shape["files"]:
        path = Path(row["path"])
        if path.exists() or path.is_symlink():
            raw = read_regular(path, limit=p.MAX_MEMBER)
            row.update(exists=True, text=raw.decode(), sha256=sha(raw), bytes=len(raw))
        else:
            row.update(exists=False, text=None, sha256=None, bytes=0)
    source = read_regular(expected["source"]["path"], limit=p.MAX_MEMBER)
    if sha(source) != expected["source"]["sha256"]:
        raise ValueError("permission probe source changed")
    return shape


class _RetainedMembers(dict):
    """Persist captured bytes before making them available for publication."""
    def __init__(self, root):
        super().__init__()
        self.root = Path(root)

    def __setitem__(self, name, raw):
        _write_new(self.root / name, raw)
        super().__setitem__(name, raw)

    def update(self, values):
        for name, raw in values.items():
            self[name] = raw


class _SharedObserver:
    def __init__(self, p, expected, selected, launch, trace, controls, transport):
        self.p, self.expected, self.selected, self.launch = p, expected, selected, launch
        self.trace, self.controls = trace, controls
        self.transport = transport
        self.session = None
        self.cases, self.members = [], _RetainedMembers(launch["evidence_root"])
        self.calls = {}
        self.expected_stop = False
        self.policy = p.projected_policy(expected, selected, launch["effect_root"])

    def __call__(self, event):
        self.transport.check()
        p = self.p
        if event.get("type") == "system" and event.get("subtype") == "init":
            if self.session is not None:
                raise ValueError("permission probe has repeated native init")
            self.session = event.get("session_id")
            if not isinstance(self.session, str):
                raise ValueError("permission probe init lacks session identity")
            recipe = p._recipe_data(self.expected, self.selected, self.launch, self.session)
            _, fixed, requests, _ = recipe
            for path, raw in fixed.items():
                _write_new(path, raw)
            for index, context in enumerate(p.CONTEXTS, 1):
                _write_new(Path(self.launch["effect_root"]) / "requests" / ("%06d.json" % index),
                           requests[context])
            # The producer creates only fixed synthetic requests. Native Write
            # must create every response that the after-inventory verifies.
            (Path(self.launch["effect_root"]) / "responses").mkdir()
            self.members["projection.json"] = canonical(p.projection(
                self.expected, self.selected, self.launch, self.session))
            self.members["neutral.before.json"] = canonical(_inventory(
                p, self.expected, self.selected, self.launch, self.session))
            all_cases = p.probe_cases(self.expected, self.selected, self.launch, self.session)
            self.members["cases.json"] = canonical([{k: v for k, v in case.items() if k != "input"}
                                                    for case in all_cases])
            self.cases = ([case for case in all_cases if case["mode"] != "observer_stopped"]
                          if self.trace == "settled" else
                          [case for case in all_cases if case["id"] == self.trace[5:]])
        if event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content", []):
                if block.get("type") == "tool_use":
                    self.calls[block["id"]] = event
        if event.get("type") == "control_request":
            identity = event.get("request", {}).get("input", {}).get("tool_use_id")
            case = next((case for case in self.cases if case["id"] == identity), None)
            if case is None:
                raise ValueError("native callback is outside scripted case roster")
            classification, view = p._classification(self.expected, self.selected, self.launch,
                self.session, case, self.controls, policy=self.policy)
            if case["mode"] == "observer_stopped":
                stop = p.effect_stop(self.expected, self.policy, case, view,
                                     self.calls[identity], event, classification)
                self.members["effect-stop.json"] = canonical(stop)
                self.members["parent-stop.json"] = canonical({
                    "kind": "native_shared_permission_parent_stop", "version": 1,
                    "outcome": "observer_stopped", "effect_stop_sha256": sha(canonical(stop)),
                    "reason_code": "prohibited_file_effect", "error_type": "BudgetStop"})
                self.expected_stop = True
                raise self.transport.budget_stop("prohibited_file_effect")

    def classify(self, command, python, programs, policy):
        self.transport.check()
        case = next((case for case in self.cases if case["tool"] == "Bash"
                     and case["input"]["command"] == command), None)
        if case is None:
            raise ValueError("native Bash command is outside scripted case roster")
        return self.p._classification(self.expected, self.selected, self.launch,
            self.session, case, self.controls, policy=self.policy)[0]


def _trace(expected, directory, deadline, controls, p, selected, transport, trace="settled"):
    _remaining(deadline)
    roots = ("config_root", "stub_root", "effect_root", "evidence_root")
    launch = {key: str(directory / key) for key in roots}
    launch["cwd"] = expected["policy"]["readonly_lookups"]["repository"]
    p._roots(expected, selected, launch)
    for key in roots:
        Path(launch[key]).mkdir(parents=True, exist_ok=False)
    _write_new(Path(launch["config_root"]) / "settings.json", b"{}")
    stub_sources = p.stub_files()
    for name, text in stub_sources.items():
        relative = name.removeprefix("stubs/")
        _write_new(Path(launch["stub_root"]) / relative, text.encode())
    observer = _SharedObserver(p, expected, selected, launch, trace, controls, transport)
    classifier, policy = observer.classify, observer.policy
    source_code = p.recipe_sources()["recipe/provider.py"].encode()
    supplier = lambda: observer.cases
    # Execute the fixed pure selector before starting transport/controller
    # threads. It is generated by the verified consumer, never supplied input.
    namespace = {}
    exec(compile(source_code, "fixed-permission-recipe/provider.py", "exec"), namespace)
    reply = namespace["reply"]
    from .native_model_aliases import model_aliases
    with local_provider(cases=supplier, model=model_aliases(expected['runtime'])['returned'],
                        deadline=deadline, reply=reply) as (server, url):
        launch.update(provider_url=url, provider_source_sha256=sha(source_code),
            executable=deepcopy(expected["runtime"]["executable"]),
            environment={**expected["permission_environment"], "CLAUDE_CONFIG_DIR": launch["config_root"],
                "PYTHONPATH": launch["stub_root"], "ANTHROPIC_BASE_URL": url,
                "ANTHROPIC_API_KEY": "d4d-local-permission-probe-token"},
            argv=p.probe_argv(expected, policy))
        _write_new(directory / "launch.before.json", canonical(launch))
        result = _run_native(expected, launch, policy, observer, classifier, transport, server, deadline)
        if server.failure is not None:
            raise ValueError("scripted permission provider failed") from server.failure
    launch.update(exit_code=result["exit_code"], shutdown=result["shutdown"])
    members = {"launch.json": canonical(launch), "config.json": b"{}",
               "transcript.jsonl": result["transcript.jsonl"], "control.jsonl": result["control.jsonl"]}
    # stderr remains retained alongside raw evidence even though the fixed
    # existing manifest roster has no stderr member.
    members.update(observer.members)
    members["neutral.after.json"] = canonical(_inventory(
        p, expected, selected, launch, observer.session))
    if trace == "settled":
        events = p._rows(result["transcript.jsonl"], "native transcript")
        terminal_hash, parent_hash = sha(canonical(events[-1])), None
    else:
        terminal_hash, parent_hash = None, sha(members["parent-stop.json"])
    members["outcome.json"] = canonical({
        "kind": "native_shared_permission_outcome", "version": 1,
        "mode": "settled" if trace == "settled" else "observer_stopped",
        "session_id": observer.session, "terminal_sha256": terminal_hash,
        "parent_stop_sha256": parent_hash})
    for name, raw in members.items():
        _write_new(directory / "completed" / name, raw)
    return members


def produce_saved_probe(expected, directory, *, deadline_seconds):
    """Run the pinned binary against loopback and publish only verified evidence.

    The new directory is retained on every failure; no source or existing output
    is reset, overwritten or cleaned. This function is never called implicitly
    during registration, import, dry-run, or validation.
    """
    if type(deadline_seconds) is not int or not 0 < deadline_seconds <= MAX_PROBE_SECONDS:
        raise ValueError("permission probe deadline must be 1..600 seconds")
    require_u4_expectation(expected)
    # Keep a bounded immutable JSON snapshot across caller mutation/callbacks.
    from . import native_shared_permissions as shared
    expected_raw = canonical(expected)
    if len(expected_raw) > shared.MAX_METADATA:
        raise ValueError('permission expectation exceeds metadata bound')
    expected = strict_json(expected_raw)
    if deadline_seconds > expected['runtime']['deadline_seconds']:
        raise ValueError("permission probe deadline exceeds selected runtime deadline")
    deadline = time.monotonic() + deadline_seconds
    with _probe_signals(), _loaded_probe_inputs(expected) as inputs:
        return _produce_captured(expected, directory, deadline, *inputs)


def _produce_captured(expected, directory, deadline, p, controls, controller_sources,
                      transport, selected, selection_raw):
    """Host-only producer using already captured, live source-bound inputs."""
    sources = {row["module"]: row for row in expected["production_sources"]}
    transport_source = None
    for name in ("native_permission_probe", "native_probe_provider", "native_subscription_guard"):
        path = Path(__file__).with_name(name + ".py")
        pin = sources.get("data_sheets_schema." + name)
        raw = read_regular(path, limit=p.MAX_MEMBER)
        if pin != {"module": "data_sheets_schema." + name, "path": str(path.resolve()),
                   "sha256": sha(raw), "bytes": len(raw)}:
            raise ValueError("permission producer source is absent from selected production closure: " + name)
        if name == "native_probe_provider":
            transport_source = raw
    _identity(expected)
    directory = Path(directory)
    if not directory.is_absolute() or directory.parent.resolve(strict=True) != directory.parent:
        raise ValueError("permission evidence directory must have a resolved absolute parent")
    protected = [expected["policy"]["readonly_lookups"]["repository"],
        expected["source"]["path"], expected["runtime"]["executable"]["path"],
        *expected["policy"]["readonly_lookups"]["inputs"],
        *expected["policy"]["readonly_lookups"]["output_directories"]]
    protected += [value for key, value in expected["permission_environment"].items()
                  if key in ("CLAUDE_CONFIG_DIR", "D4D_LAUNCH_INSTRUCTION", "PYSTOW_HOME") and value.startswith("/")]
    protected += [expected["selection"]["path"], selected["stage_root"]]
    for value in protected:
        if overlaps(directory, value):
            raise ValueError("permission evidence directory overlaps protected authority")
    _remaining(deadline)
    directory.mkdir(mode=0o700)
    try:
        _write_new(directory / "transport-provider.py", transport_source)
        (directory / "version-config").mkdir(mode=0o700)
        source = read_regular(expected["source"]["path"], limit=p.MAX_MEMBER)
        if sha(source) != expected["source"]["sha256"]:
            raise ValueError("permission source differs from selected source")
        files = _RetainedMembers(directory / "captured")
        files.update({"policy.json": canonical(expected["policy"]), "source.before": source})
        files["selection.json"] = selection_raw
        files.update({name: text.encode() for name, text in p.recipe_sources().items()})
        files["version.txt"] = _version(expected, deadline, directory)
        for trace in p.TRACES:
            rows = _trace(expected, directory / trace, deadline, controls, p, selected, transport, trace)
            roster = rows.pop("cases.json")
            if trace == "settled":
                files["cases.json"] = roster
            files.update({"traces/" + trace + "/" + name: raw for name, raw in rows.items()})
        files["source.after"] = read_regular(expected["source"]["path"], limit=len(source) + 1)
        _remaining(deadline)
        _identity(expected)
        manifest = {"kind": p.KIND, "version": p.VERSION, "origin": p.ORIGIN,
                    "binding": deepcopy(expected), "members": {}}
        for name, raw in files.items():
            row = {"text": raw.decode("utf-8"), "sha256": sha(raw), "bytes": len(raw)}
            manifest["members"][name] = row
        raw_manifest = canonical(manifest)
        reading = p.verify_saved_probe(raw_manifest, expected=expected, controls=controls,
                                       controller_sources=controller_sources)
        _remaining(deadline)
        if reading.get("checked") is not True or reading.get("passed") is not True:
            raise ValueError("actual permission observation did not pass its verifier")
        _write_new(directory / "verification.json", canonical(reading))
        _write_new(directory / "producer-evidence.json", canonical({
            "kind": "d4d_native_probe_producer_evidence", "version": 1,
            "manifest_sha256": sha(raw_manifest), "transport_source_sha256": sha(transport_source),
            "selector_source_sha256": sha(files["recipe/provider.py"]),
            "basis": "Actual transport source and fixed selector are distinct; no simulator or fallback."}))
        output = directory / "permission-probe.json"
        _write_new(output, raw_manifest)
        return output
    except BaseException as exc:
        _write_new(directory / 'failure.json', canonical({
            'error_type': type(exc).__name__, 'message': str(exc)}))
        raise
