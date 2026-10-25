"""Produce existing native permission manifests from actual process evidence.

#4760, 2026-10-20. No simulator, executable discovery or provider fallback.
Calling produce_saved_probe is an explicit live-binary action; offline tests
must mock its process boundary and must not call the registered native binary.
"""
from __future__ import annotations

from copy import deepcopy
import io
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time

from .native_subscription_guard import canonical, read_regular, sha, strict_json
from .native_probe_provider import local_provider

MAX_STREAM = 8 * 1024 * 1024
MAX_PROBE_SECONDS = 600


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
    """Terminate/reap the new process group, including inherited pipe holders."""
    if process is None:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
    if process.poll() is None:
        raise RuntimeError("permission child could not be reaped")


def _identity(expected):
    from .native_execution_registration import executable_identity
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
        try:
            _terminate(process)
        finally:
            if process is not None:
                for stream in (process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()
            _write_new(directory / "version.stdout", bytes(outputs["stdout"]))
            _write_new(directory / "version.stderr", bytes(outputs["stderr"]))


def _run_native(expected, launch, policy, observer, classifier, controls, server, deadline):
    """Actual native process with bounded I/O and the existing control protocol."""
    native = controls["native_control"]
    control = native.NativeControl(policy, classifier, launch["config_root"], event_observer=observer)
    process = None
    transcript, journal, stderr = io.BytesIO(), io.StringIO(), bytearray()
    stopped = False
    try:
        _identity(expected)
        if time.monotonic() >= deadline:
            raise TimeoutError("permission probe deadline elapsed before process creation")
        process = subprocess.Popen(launch["argv"], cwd=launch["cwd"], env=launch["environment"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        os.set_blocking(process.stderr.fileno(), False)
        control.start(process, _Bounded(transcript, MAX_STREAM), _Bounded(journal, MAX_STREAM),
                      "Execute the scripted local permission cases in order, then finish.")
        while process.poll() is None or not control.stdout_closed:
            if time.monotonic() >= deadline:
                raise TimeoutError("permission probe deadline elapsed")
            if server.failure is not None:
                raise ValueError("scripted permission provider failed") from server.failure
            try:
                raw = os.read(process.stderr.fileno(), 65536)
            except BlockingIOError:
                raw = b""
            stderr.extend(raw)
            if len(stderr) > MAX_STREAM:
                raise ValueError("permission stderr exceeds its byte bound")
            control.service()
        control.finish()
    except controls["run_native_canary"].BudgetStop:
        # Only a durable exact expected effect-stop observed by this controller
        # may yield a negative trace. Other failures are never a passed probe.
        if getattr(observer, "expected_stop", False):
            stopped = True
        else:
            raise
    finally:
        try:
            _terminate(process)
        finally:
            try:
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
    if (not control.control_shutdown_complete or control.unfinished_control_workers != 0
            or process is None or process.poll() is None):
        raise ValueError("permission probe cleanup was incomplete")
    _identity(expected)
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


class _SharedObserver:
    def __init__(self, p, expected, selected, launch, trace, controls):
        self.p, self.expected, self.selected, self.launch = p, expected, selected, launch
        self.trace, self.controls = trace, controls
        self.session = None
        self.cases, self.members = [], {}
        self.calls = {}
        self.expected_stop = False
        self.policy = p.projected_policy(expected, selected, launch["effect_root"])

    def __call__(self, event):
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
                for name in ("effect-stop.json", "parent-stop.json"):
                    _write_new(Path(self.launch["evidence_root"]) / name, self.members[name])
                self.expected_stop = True
                raise self.controls["run_native_canary"].BudgetStop("prohibited_file_effect")

    def classify(self, command, python, programs, policy):
        case = next((case for case in self.cases if case["tool"] == "Bash"
                     and case["input"]["command"] == command), None)
        if case is None:
            raise ValueError("native Bash command is outside scripted case roster")
        return self.p._classification(self.expected, self.selected, self.launch,
            self.session, case, self.controls, policy=self.policy)[0]


def _trace(expected, directory, deadline, controls, p, selected=None, trace="settled"):
    _remaining(deadline)
    roots = ("config_root", "stub_root") if selected is None else (
        "config_root", "stub_root", "effect_root", "evidence_root")
    launch = {key: str(directory / key) for key in roots}
    launch["cwd"] = expected["policy"]["readonly_lookups"]["repository"]
    if selected is None:
        # Reuse the verifier's overlap rules before creating anything.
        from pathlib import PurePosixPath
        protected = [launch["cwd"], expected["source"]["path"],
                     *expected["policy"]["readonly_lookups"]["inputs"],
                     *expected["policy"]["readonly_lookups"]["output_directories"]]
        for root in launch.values():
            if root == launch["cwd"]:
                continue
            r = PurePosixPath(root)
            if any(r == PurePosixPath(q) or r in PurePosixPath(q).parents
                   or PurePosixPath(q) in r.parents for q in protected):
                raise ValueError("permission probe isolation overlaps authority")
    else:
        p._roots(expected, selected, launch)
    for key in roots:
        Path(launch[key]).mkdir(parents=True, exist_ok=False)
    _write_new(Path(launch["config_root"]) / "settings.json", b"{}")
    stub_sources = p.stub_files()
    for name, text in stub_sources.items():
        relative = name.removeprefix("stubs/") if selected is not None else name
        _write_new(Path(launch["stub_root"]) / relative, text.encode())
    if selected is None:
        from .native_attribution_controller import _classify
        observer = lambda event: None
        cases = p.probe_cases(expected)
        classifier = lambda command, python, programs, policy: _classify(
            command, python, programs, policy, controls)
        policy = expected["policy"]
        source_code = Path(__file__).with_name("native_probe_provider.py").read_bytes()
        supplier = lambda: cases
        reply = None
    else:
        observer = _SharedObserver(p, expected, selected, launch, trace, controls)
        classifier, policy = observer.classify, observer.policy
        source_code = p.recipe_sources()["recipe/provider.py"].encode()
        supplier = lambda: observer.cases
        # Execute the exact fixed pure selector whose hash the existing protocol
        # records. The HTTP/SSE transport is separately pinned production code.
        namespace = {}
        exec(compile(source_code, "fixed-permission-recipe/provider.py", "exec"), namespace)
        reply = namespace["reply"]
    with local_provider(cases=supplier, model=expected["runtime"]["model"],
                        deadline=deadline, reply=reply) as (server, url):
        launch.update(provider_url=url, provider_source_sha256=sha(source_code),
            executable=deepcopy(expected["runtime"]["executable"]),
            environment={**expected["permission_environment"], "CLAUDE_CONFIG_DIR": launch["config_root"],
                "PYTHONPATH": launch["stub_root"], "ANTHROPIC_BASE_URL": url,
                "ANTHROPIC_API_KEY": "d4d-local-permission-probe-token"},
            argv=p.probe_argv(expected) if selected is None else p.probe_argv(expected, policy))
        result = _run_native(expected, launch, policy, observer, classifier, controls, server, deadline)
        if server.failure is not None:
            raise ValueError("scripted permission provider failed") from server.failure
    launch.update(exit_code=result["exit_code"], shutdown=result["shutdown"])
    if selected is None:
        launch["shutdown"].pop("child_reaped")
    members = {"launch.json": canonical(launch), "config.json": b"{}",
               "transcript.jsonl": result["transcript.jsonl"], "control.jsonl": result["control.jsonl"]}
    # stderr remains retained alongside raw evidence even though the fixed
    # existing manifest roster has no stderr member.
    if selected is None:
        members["provider.py"] = source_code
    else:
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
    return members


def produce_saved_probe(expected, directory, *, deadline_seconds):
    """Run the pinned binary against loopback and publish only verified evidence.

    The new directory is retained on every failure; no source or existing output
    is reset, overwritten or cleaned. This function is never called implicitly
    during registration, import, dry-run, or validation.
    """
    if type(deadline_seconds) is not int or not 0 < deadline_seconds <= MAX_PROBE_SECONDS:
        raise ValueError("permission probe deadline must be 1..600 seconds")
    selected_deadline = expected.get("runtime", {}).get("deadline_seconds", MAX_PROBE_SECONDS)
    if type(selected_deadline) is not int or deadline_seconds > selected_deadline:
        raise ValueError("permission probe deadline exceeds selected runtime deadline")
    deadline = time.monotonic() + deadline_seconds
    from . import native_attribution_controller as composition
    from . import native_execution_permissions as legacy
    from . import native_shared_permissions as shared
    selected = None
    p = shared if expected.get("kind") == shared.EXPECTED_KIND else legacy
    controls = composition.load_controls()
    if p is shared:
        selection_raw = read_regular(expected["selection"]["path"], limit=shared.MAX_MEMBER)
        selected = shared.contract.parse_selection(selection_raw)
        shared._pin(expected["selection"], selection_raw)
        shared._authority(expected, selected, controls)
        sources = {row["module"]: row for row in expected["production_sources"]}
        for name in ("native_permission_probe", "native_probe_provider", "native_subscription_guard"):
            path = Path(__file__).with_name(name + ".py")
            pin = sources.get("data_sheets_schema." + name)
            raw = path.read_bytes()
            if pin != {"module": "data_sheets_schema." + name, "path": str(path.resolve()),
                       "sha256": sha(raw), "bytes": len(raw)}:
                raise ValueError("permission producer source is absent from selected production closure: " + name)
    else:
        legacy._authority(expected, controls)
    _identity(expected)
    directory = Path(directory)
    if not directory.is_absolute() or directory.parent.resolve(strict=True) != directory.parent:
        raise ValueError("permission evidence directory must have a resolved absolute parent")
    protected = [expected["policy"]["readonly_lookups"]["repository"],
        expected["source"]["path"], expected["runtime"]["executable"]["path"],
        *expected["policy"]["readonly_lookups"]["inputs"],
        *expected["policy"]["readonly_lookups"]["output_directories"]]
    protected += [value for key, value in expected["permission_environment"].items()
                  if key in ("CLAUDE_CONFIG_DIR", "D4D_LAUNCH_INSTRUCTION") and value.startswith("/")]
    if selected is not None:
        protected += [expected["selection"]["path"], selected["stage_root"]]
    for value in protected:
        path = Path(value).resolve()
        if directory == path or directory in path.parents or path in directory.parents:
            raise ValueError("permission evidence directory overlaps protected authority")
    _remaining(deadline)
    directory.mkdir(mode=0o700)
    (directory / "version-config").mkdir(mode=0o700)
    source = read_regular(expected["source"]["path"], limit=p.MAX_BYTES if p is legacy else p.MAX_MEMBER)
    if sha(source) != expected["source"]["sha256"]:
        raise ValueError("permission source differs from selected source")
    files = {"policy.json": canonical(expected["policy"]), "source.before": source,
             "version.txt": _version(expected, deadline, directory)}
    if p is legacy:
        files.update({name: text.encode() for name, text in p.stub_files().items()})
        files["cases.json"] = canonical(p.probe_cases(expected))
        files.update(_trace(expected, directory / "trace", deadline, controls, p))
    else:
        files["selection.json"] = selection_raw
        files.update({name: text.encode() for name, text in p.recipe_sources().items()})
        for trace in p.TRACES:
            rows = _trace(expected, directory / trace, deadline, controls, p, selected, trace)
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
        _write_new(directory / "captured" / name, raw)
        row = {"text": raw.decode("utf-8"), "sha256": sha(raw)}
        if p is shared:
            row["bytes"] = len(raw)
        manifest["members"][name] = row
    raw_manifest = canonical(manifest)
    reading = p.verify_saved_probe(raw_manifest, expected=expected)
    _remaining(deadline)
    if reading.get("checked") is not True or reading.get("passed") is not True:
        raise ValueError("actual permission observation did not pass its verifier")
    _write_new(directory / "verification.json", canonical(reading))
    transport = Path(__file__).with_name("native_probe_provider.py").read_bytes()
    _write_new(directory / "transport-provider.py", transport)
    _write_new(directory / "producer-evidence.json", canonical({
        "kind": "d4d_native_probe_producer_evidence", "version": 1,
        "manifest_sha256": sha(raw_manifest), "transport_source_sha256": sha(transport),
        "selector_source_sha256": sha(files["recipe/provider.py"] if p is shared else files["provider.py"]),
        "basis": "Actual transport source and fixed selector are distinct; no simulator or fallback."}))
    output = directory / "permission-probe.json"
    _write_new(output, raw_manifest)
    return output
