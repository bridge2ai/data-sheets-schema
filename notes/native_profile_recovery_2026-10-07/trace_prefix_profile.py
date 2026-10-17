#!/usr/bin/env python3
"""Pinned, bounded Trace construction diagnostic; never a native execution route.

The parent starts only this script's closed worker with an isolated interpreter.
The worker compiles three verified source modules, constructs Trace over retained
prefixes, and rejects process/network/filesystem-write effects. No historical
finalizer, fixture builder, callback executor, provider or runtime is invoked.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import cProfile
from dataclasses import fields, is_dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import time
from types import ModuleType


SOURCE_COMMIT = "0125eebbc214d0907c3b69d23758cd9441911a78"
SOURCE_TREE = "142af4bfd8f32bd6b37d61434cfb30e8bfac5bf1"
ARTIFACT_ID = 11408295434
RUN_ID = 37451274006
ZIP_SHA256 = "0ec5378065601dae7d81801a6ad051dd9cb07b82c6b99cf0b4ea4d8e4cbc0dae"
MANIFEST_SHA256 = "f7e1ac1cf4f7edf2e855e7545a01a6f5c27fbe7c023251abd99d6f82915020e0"
SOURCE_MANIFEST_SHA256 = "53f8a7378e8babf3c746fef6c2e54c27d9bbba1c0bcd621cb91ee86c004a4798"
CASE_MANIFEST_SHA256 = "1fc631110a8dc7d1db8ff28af35243e6edfddb8737d70aad32928410794d0de4"
CASE_RELATIVE = "neutral/test_actual_public_correction_0/native26"
ORIGINAL_CASE = "/home/runner/work/_temp/d4d-native-shared-37451274006-1/cases/" + CASE_RELATIVE
ORIGINAL_REPO = "/home/runner/work/data-sheets-schema/data-sheets-schema"
MODULES = ("native_shared_contract", "native_shared_evidence", "native_shared_observations")
HARD_WALL_SECONDS = 120
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_REPORT_BYTES = 2 * 1024 * 1024
FORMAT = "native_trace_prefix_profile_v1"
SCOPE = "0125 retained-prefix Trace construction only; no native or scientific acceptance"


class ProfileError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise ProfileError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def invalid(value):
        raise ProfileError("non-finite JSON value")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read_file(path, expected=None):
    """Read one bounded regular file without following a link or changing bytes."""
    path = Path(path)
    require(path.resolve(strict=True) == path.absolute(), "input path contains a symlink")
    before = path.stat()
    require(stat.S_ISREG(before.st_mode), "input is not a regular file")
    require(before.st_size <= MAX_FILE_BYTES, "input exceeds diagnostic file bound")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(MAX_FILE_BYTES + 1)
        after = os.fstat(stream.fileno())
    def identity(info):
        # Reading may update atime; that is not a content or identity change.
        return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                info.st_mtime_ns, info.st_ctime_ns)
    require(identity(before) == identity(opened) == identity(after) == identity(path.stat())
            and path.resolve(strict=True) == path.absolute(), "input changed while reading")
    require(len(raw) == before.st_size <= MAX_FILE_BYTES, "input size changed")
    if expected is not None:
        require(sha(raw) == expected, "input hash differs from recovered pin")
    return raw


def member(root, relative):
    path = PurePosixPath(relative)
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in relative,
            "manifest member escapes its root")
    return root.joinpath(*path.parts)


def executable_identity(path):
    """Bind the selected physical interpreter without publishing its host path."""
    path = Path(path).resolve(strict=True)
    raw = read_file(path)
    info = path.stat()
    metadata = {key: getattr(info, key) for key in (
        "st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")}
    return {"sha256": sha(raw), "bytes": len(raw), "path_sha256": sha(str(path).encode()),
            "metadata_sha256": sha(canonical(metadata))}


def verify_prefix(ref, raw, *, stream, original_path, execution_sha256):
    """Validate the actual retained prefix; never repair its path/length/identity."""
    require(type(ref) is dict and set(ref) == {
        "stream", "path", "stream_id", "through_bytes", "lines", "sha256"},
        "prefix has another shape")
    require(ref["stream"] == stream and ref["path"] == original_path,
            "prefix role or original path differs")
    for key in ("through_bytes", "lines"):
        require(type(ref[key]) is int and ref[key] > 0, "prefix length must be a positive integer")
    require(ref["through_bytes"] <= len(raw), "prefix exceeds retained stream")
    prefix = raw[:ref["through_bytes"]]
    require(prefix.endswith(b"\n") and prefix.count(b"\n") == ref["lines"],
            "prefix does not end at its declared physical line boundary")
    require(all(prefix.split(b"\n")[:-1]), "prefix contains a blank physical row")
    require(sha(prefix) == ref["sha256"], "prefix hash differs")
    identity = {"domain": "native_shared_stream_v1", "execution_sha256": execution_sha256,
                "stream": stream, "path": original_path}
    require(sha(canonical(identity)) == ref["stream_id"], "prefix stream identity differs")
    return prefix


def verify_inputs(source, recovery):
    """Verify the selected source, original upload and all recovered regular files."""
    source, recovery = Path(source).resolve(strict=True), Path(recovery).resolve(strict=True)
    artifact = recovery / "artifact"
    read_file(recovery / f"artifact-{ARTIFACT_ID}.zip", ZIP_SHA256)
    manifest = strict_json(read_file(artifact / "artifact-manifest.json", MANIFEST_SHA256))
    uploaded = {}
    for name, pin in manifest.items():
        raw = read_file(member(artifact, name), pin["sha256"])
        require(len(raw) == pin["bytes"], "uploaded member size differs")
        uploaded[name] = raw
    require(sha(uploaded["source-before.json"]) == SOURCE_MANIFEST_SHA256,
            "source manifest differs")
    require(uploaded["source-before.json"] == uploaded["source-after-neutral.json"]
            == uploaded["source-final.json"], "historical source preservation differs")
    source_manifest = strict_json(uploaded["source-before.json"])
    require(source_manifest["head"] == SOURCE_COMMIT and source_manifest["tree"] == SOURCE_TREE
            and source_manifest["tracked_exact"] is True, "historical source identity differs")
    require(read_file(source / ".git/HEAD").strip() == SOURCE_COMMIT.encode(),
            "diagnostic requires the exact detached recovered source commit")
    module_bytes, source_count, gitlinks = {}, 0, {}
    for name, pin in source_manifest["entries"].items():
        if pin["mode"] == "160000":
            gitlinks[name] = pin["gitlink"]
            continue  # Opaque historical gitlinks; none is imported by this diagnostic.
        path = member(source, name)
        raw = read_file(path, pin["sha256"])
        mode = "100755" if path.stat().st_mode & 0o111 else "100644"
        require(len(raw) == pin["bytes"] and mode == pin["mode"], "source bytes or mode differ")
        source_count += 1
        for module in MODULES:
            if name == f"src/data_sheets_schema/{module}.py":
                module_bytes[module] = raw
    require(source_count == 9214 and len(gitlinks) == 2 and set(module_bytes) == set(MODULES),
            "source inventory differs")
    require(sha(uploaded["case-manifest.json"]) == CASE_MANIFEST_SHA256, "case manifest differs")
    case_manifest = strict_json(uploaded["case-manifest.json"])
    require(case_manifest["unchanged_during_archive"] is True, "historical archive changed")
    recovered = recovery / "captured/cases"
    case_bytes = {}
    for name, pin in case_manifest["entries"].items():
        if pin["type"] != "file":
            continue  # The original absolute pytest symlink is never followed.
        raw = read_file(member(recovered, name), pin["sha256"])
        require(len(raw) == pin["bytes"], "recovered case member size differs")
        case_bytes[name] = raw
    require(len(case_bytes) == 83, "recovered regular-file inventory differs")
    def saved(name):
        return case_bytes[CASE_RELATIVE + "/" + name]
    composition = strict_json(saved("authority/composition-execution.json"))
    registration_raw = saved("native-attempt/registration.json")
    registration = strict_json(registration_raw)
    runtime_raw = saved("authority/runtime-execution.json")
    runtime = strict_json(runtime_raw)
    selection_raw = saved("authority/selection.json")
    selection = strict_json(selection_raw)
    require(composition["runtime_raw_json"].encode() == runtime_raw
            and sha(runtime_raw) == composition["runtime_sha256"], "runtime identity differs")
    require(composition["selection_raw_json"].encode() == selection_raw
            and sha(selection_raw) == composition["selection_sha256"], "selection identity differs")
    require(registration["runtime"] == runtime
            and registration["composition_sha256"] == sha(saved("authority/composition-execution.json")),
            "registration runtime or composition differs")
    policy = composition["policy"]
    require(sha(canonical(policy)) == composition["policy_sha256"], "policy identity differs")
    labels = {"arm": "BASELINE (input documents only)", "label": "offline-neutral",
              "method": "claudecode_direct", "project": "SYNTHETIC"}
    require(selection["run"] == labels, "original synthetic labels differ")
    require(runtime["deadline_seconds"] == 900 and runtime["model"] == "synthetic-native-model"
            and runtime["executable"]["path"] == ORIGINAL_CASE + "/ordinary-python-test-peer",
            "original runtime declarations differ")
    require(composition["working_directory"] == registration["working_directory"] == ORIGINAL_REPO
            and policy["readonly_lookups"]["repository"] == ORIGINAL_REPO,
            "original working directory differs")
    streams = {name: saved("native-attempt/" + name + ".jsonl") for name in ("transcript", "control")}
    for name, count in (("transcript", 67), ("control", 24)):
        raw = streams[name]
        require(raw.endswith(b"\n") and raw.count(b"\n") == count, "retained stream rows differ")
        require(all(type(strict_json(line)) is dict for line in raw.split(b"\n")[:-1]),
                "retained stream row is not an object")
    observations = []
    previous_lengths = {"transcript": 0, "control": 0}
    for index in range(15):
        raw = saved(f"fresh-attempt/stages/observations/{index:06d}.json")
        row = strict_json(raw)
        require(row["kind"] == "d4d_native_shared_stage_observation" and row["version"] == 1
                and row["execution_sha256"] == sha(registration_raw)
                and row["selection_sha256"] == sha(selection_raw)
                and row["session_id"] == "43540000-0000-4000-8000-000000000001",
                "observation binding differs")
        prefixes = {}
        for stream in streams:
            ref = row[stream + "_prefix"]
            prefixes[stream] = verify_prefix(ref, streams[stream], stream=stream,
                original_path=ORIGINAL_CASE + "/native-attempt/" + stream + ".jsonl",
                execution_sha256=sha(registration_raw))
            require(ref["through_bytes"] >= previous_lengths[stream], "observation prefix regressed")
            previous_lengths[stream] = ref["through_bytes"]
        observations.append({"index": index, "raw_sha256": sha(raw), "document": row,
                             "prefixes": prefixes})
    provenance = {"source_commit": SOURCE_COMMIT, "source_tree": SOURCE_TREE,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256, "source_files_verified": source_count,
        "opaque_gitlinks_not_imported": gitlinks, "artifact_id": ARTIFACT_ID, "run_id": RUN_ID,
        "artifact_zip_sha256": ZIP_SHA256, "case_manifest_sha256": CASE_MANIFEST_SHA256,
        "regular_case_files_verified": 83, "labels": labels,
        "composition_sha256": sha(saved("authority/composition-execution.json")),
        "policy_sha256": composition["policy_sha256"], "runtime_sha256": sha(runtime_raw),
        "selection_sha256": sha(selection_raw), "execution_sha256": sha(registration_raw),
        "original_path_identities_preserved": True,
        "registered_acceptance_deadline_seconds": 900,
        "streams": {key: {"sha256": sha(raw), "bytes": len(raw), "lines": raw.count(b"\n")}
                    for key, raw in streams.items()},
        "modules": {name: sha(raw) for name, raw in module_bytes.items()}}
    return {"source": source, "module_bytes": module_bytes, "observations": observations,
            "policy": policy, "runtime": runtime, "provenance": provenance}


@contextmanager
def load_modules(source, module_bytes):
    """Execute exactly the verified .py bytes; no package initializers or pyc reads."""
    names = [name for name in sys.modules if name == "data_sheets_schema"
             or name.startswith("data_sheets_schema.")]
    previous = {name: sys.modules.pop(name) for name in names}
    try:
        package = ModuleType("data_sheets_schema")
        package.__path__ = []
        sys.modules[package.__name__] = package
        loaded = {}
        for short in MODULES:
            name = "data_sheets_schema." + short
            path = Path(source) / "src/data_sheets_schema" / (short + ".py")
            raw = module_bytes[short]
            require(read_file(path, sha(raw)) == raw, "module changed before compilation")
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            # The logical filename also prevents private host paths in profiler output.
            exec(compile(raw, f"pinned0125/src/data_sheets_schema/{short}.py", "exec"), module.__dict__)
            require(Path(module.__file__) == path and module.__spec__.origin == str(path),
                    "loaded module origin differs")
            setattr(package, short, module)
            loaded[short] = module
        yield loaded
    finally:
        for name in list(sys.modules):
            if name == "data_sheets_schema" or name.startswith("data_sheets_schema."):
                del sys.modules[name]
        sys.modules.update(previous)


def typed_value(value):
    """Complete typed state encoding, including order and immutable byte identities."""
    if value is None:
        return ["none"]
    if type(value) in (bool, int, float, str):
        return [type(value).__name__, value]
    if type(value) is bytes:
        return ["bytes", len(value), sha(value)]
    if type(value) in (tuple, list):
        return [type(value).__name__, [typed_value(item) for item in value]]
    if type(value) is dict:
        return ["dict", [[typed_value(key), typed_value(item)] for key, item in value.items()]]
    if is_dataclass(value) and not isinstance(value, type):
        return ["dataclass", type(value).__module__ + "." + type(value).__qualname__,
                [[field.name, typed_value(getattr(value, field.name))] for field in fields(value)]]
    raise ProfileError("unsupported diagnostic semantic value type")


def exception_value(error):
    """Retain the bounded exception graph, including cause/context/suppression."""
    seen = {}
    def encode(value):
        if value is None:
            return None
        identity = id(value)
        if identity in seen:
            return {"reference": seen[identity]}
        require(len(seen) < 32, "exception graph exceeds diagnostic bound")
        number = len(seen)
        seen[identity] = number
        return {"node": number, "type": type(value).__module__ + "." + type(value).__qualname__,
                "arguments": typed_value(value.args), "cause": encode(value.__cause__),
                "context": encode(value.__context__), "suppress_context": value.__suppress_context__,
                "notes": typed_value(getattr(value, "__notes__", None))}
    return encode(error)


def outcome(call):
    try:
        return {"status": "returned", "value": typed_value(call())}
    except ValueError as exc:
        return {"status": "refused", "exception": exception_value(exc)}


def semantic_trace(trace):
    methods = {}
    for identity in trace.calls:
        methods[identity] = {name: outcome(lambda name=name: getattr(trace, name)(identity))
                             for name in ("request", "admitted", "settled")}
    return {"state": typed_value(vars(trace)), "pending": typed_value(trace.pending()),
            "tool_methods": methods}


def effect_guard(event, args):
    """Audit hook for the diagnostic child, installed before repository code loads."""
    if (event.startswith(("socket.", "subprocess.", "os.exec", "os.spawn", "os.posix_spawn"))
            or event in {"os.system", "os.fork", "os.forkpty", "pty.spawn", "ctypes.dlopen",
                         "os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.link",
                         "os.symlink", "os.chmod", "os.chown", "os.truncate", "os.utime"}):
        raise RuntimeError("diagnostic forbids process, network and filesystem effects")
    if event == "open":
        mode, flags = args[1], args[2]
        if ((isinstance(mode, str) and any(character in mode for character in "wax+"))
                or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))):
            raise RuntimeError("diagnostic forbids filesystem writes")


def profile_rows(profiler):
    result = []
    for entry in profiler.getstats():
        code = entry.code
        if isinstance(code, str):
            label = {"file": "builtin", "line": 0, "function": code}
        else:
            filename = code.co_filename
            public = filename if filename.startswith("pinned0125/") else Path(filename).name
            label = {"file": public, "line": code.co_firstlineno, "function": code.co_name}
        result.append({**label, "calls": entry.callcount, "recursive_calls": entry.reccallcount,
                       "total_thread_cpu_seconds": entry.totaltime,
                       "inline_thread_cpu_seconds": entry.inlinetime})
    return sorted(result, key=lambda row: (-row["total_thread_cpu_seconds"], row["file"], row["line"]))


def measured_trace(factory, *, instrumented):
    profiler = cProfile.Profile(timer=time.thread_time) if instrumented else None
    failure = None
    wall, cpu = time.perf_counter_ns(), time.thread_time_ns()
    if profiler is not None:
        profiler.enable()
    try:
        try:
            trace = factory()
        except ValueError as exc:
            failure = exc
            trace = None
    finally:
        if profiler is not None:
            profiler.disable()
        cpu, wall = time.thread_time_ns() - cpu, time.perf_counter_ns() - wall
    if trace is not None:
        result = {"status": "returned", "semantics": semantic_trace(trace)}
    else:
        result = {"status": "refused", "exception": exception_value(failure)}
    report = {"status": result["status"], "semantic_sha256": sha(canonical(result)),
              "thread_cpu_ns": cpu, "wall_ns": wall}
    if trace is not None:
        report.update(calls=len(trace.calls), callbacks=len(trace.callbacks),
                      decisions=len(trace.decisions), results=len(trace.results),
                      pending=list(trace.pending()))
    else:
        report.update(exception=result["exception"]["type"],
                      refusal_sha256=sha(canonical(result["exception"])))
    if profiler is not None:
        report["profile"] = profile_rows(profiler)
    return report


def run_worker(source, recovery):
    interpreter = Path(sys.executable).resolve(strict=True)
    interpreter_before = executable_identity(interpreter)
    driver_before = sha(read_file(Path(__file__).resolve(strict=True)))
    inputs = verify_inputs(source, recovery)
    rows = []
    with load_modules(inputs["source"], inputs["module_bytes"]) as modules:
        c = modules["native_shared_contract"]
        observed = modules["native_shared_observations"]
        for item in inputs["observations"]:
            document = item["document"]
            prefixes = {}
            for name, raw in item["prefixes"].items():
                ref = document[name + "_prefix"]
                prefixes[name] = c.EvidencePrefix(stream=name, path=ref["path"], raw=raw,
                    bytes=len(raw), sha256=ref["sha256"], lines=ref["lines"])
            factory = lambda: observed.Trace(prefixes["transcript"], prefixes["control"],
                session_id=document["session_id"], policy=inputs["policy"], runtime=inputs["runtime"])
            plain = measured_trace(factory, instrumented=False)
            instrumented = measured_trace(factory, instrumented=True)
            require(plain["semantic_sha256"] == instrumented["semantic_sha256"],
                    "instrumented Trace semantics differ")
            rows.append({"index": item["index"], "observation_type": document["observation_type"],
                "observation_sha256": item["raw_sha256"],
                "prefixes": {name: {key: ref[key] for key in ("stream_id", "through_bytes", "lines", "sha256")}
                             for name in prefixes for ref in [document[name + "_prefix"]]},
                "plain": plain, "instrumented": instrumented})
        # Explicit negative controls use the first valid retained prefix. Copies
        # change only the diagnostic arguments; original declarations stay intact.
        first = inputs["observations"][0]
        small = {name: c.EvidencePrefix(stream=name, path=first["document"][name + "_prefix"]["path"],
                    raw=raw, bytes=len(raw), sha256=sha(raw), lines=raw.count(b"\n"))
                 for name, raw in first["prefixes"].items()}
        common = {"session_id": first["document"]["session_id"], "policy": inputs["policy"],
                  "runtime": inputs["runtime"]}
        controls = {
            "foreign_session": lambda: observed.Trace(small["transcript"], small["control"],
                **{**common, "session_id": "diagnostic-foreign-session"}),
            "exchanged_roles": lambda: observed.Trace(small["control"], small["transcript"], **common),
            "foreign_runtime_model": lambda: observed.Trace(small["transcript"], small["control"],
                **{**common, "runtime": {**inputs["runtime"], "model": "diagnostic-other-model"}}),
        }
        refusals = []
        for name, factory in controls.items():
            plain = measured_trace(factory, instrumented=False)
            instrumented = measured_trace(factory, instrumented=True)
            require(plain["status"] == instrumented["status"] == "refused"
                    and plain["semantic_sha256"] == instrumented["semantic_sha256"],
                    "negative-control refusal parity failed")
            refusals.append({"control": name, "plain": plain, "instrumented": instrumented})
    after = verify_inputs(source, recovery)
    require(inputs["provenance"] == after["provenance"], "inputs changed during diagnostic")
    require(canonical(inputs["policy"]) == canonical(after["policy"])
            and canonical(inputs["runtime"]) == canonical(after["runtime"]),
            "Trace changed the supplied declarations")
    require(executable_identity(interpreter) == interpreter_before,
            "worker interpreter changed during diagnostic")
    require(sha(read_file(Path(__file__).resolve(strict=True))) == driver_before,
            "worker driver changed during diagnostic")
    return {"format": FORMAT, "scope": SCOPE, "status": "measured", "parity_passed": True,
        "scientific_eligibility": False, "native_acceptance_passed": False,
        "historical_capture_complete": False, "inputs_unchanged": True,
        "retained_prefixes_returned": sum(row["plain"]["status"] == "returned" for row in rows),
        "retained_prefixes_refused": sum(row["plain"]["status"] == "refused" for row in rows),
        "provenance": inputs["provenance"], "prefixes": rows, "refusal_controls": refusals,
        "measurement": {"repetitions_per_mode": 1, "order": "plain then instrumented per prefix",
            "timed_scope": "Trace constructor only; semantic readback/fingerprinting excluded",
            "instrumentation": "cProfile with calling-thread CPU timer; instrumentation overhead retained",
            "hard_wall_seconds": HARD_WALL_SECONDS},
        "driver_sha256": driver_before,
        "environment": {"implementation": platform.python_implementation(),
            "python_version": platform.python_version(), "system": platform.system(),
            "release": platform.release(), "machine": platform.machine(),
            "interpreter": interpreter_before,
            "startup_flags": {"isolated": sys.flags.isolated, "no_site": sys.flags.no_site,
                              "dont_write_bytecode": sys.dont_write_bytecode}},
        "limitations": ["Not a complete saved replay, runtime execution or scientific evaluation.",
            "No reconstruction of the unavailable 4366 source or its CPU measurements.",
            "No whole-path fraction, estimated savings or 900-second deadline inference.",
            "Known repeated parsing is tracked by #4537/#4576; this is baseline characterization.",
            "Representative full-schema _load_live/_run profiling requires a separate reviewed fixture."]}


def run_profile(source, recovery, output):
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
            "parent requires -I -B -S startup")
    source, recovery = Path(source).resolve(strict=True), Path(recovery).resolve(strict=True)
    output = Path(output).absolute()
    require(output.parent.resolve(strict=True) == output.parent, "output parent must be an existing physical directory")
    require(not output.exists() and not output.is_symlink(), "output must be new")
    for protected in (source, recovery):
        require(not output.is_relative_to(protected) and not protected.is_relative_to(output),
                "output overlaps protected recovered inputs")
    before = verify_inputs(source, recovery)["provenance"]
    driver = Path(__file__).resolve(strict=True)
    driver_sha = sha(read_file(driver))
    interpreter = Path(sys.executable).resolve(strict=True)
    interpreter_before = executable_identity(interpreter)
    argv = [str(interpreter), "-I", "-B", "-S", str(driver), "--worker", "--source", str(source),
            "--recovery", str(recovery)]
    started = time.perf_counter_ns()
    try:
        child = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=HARD_WALL_SECONDS, check=False)
        child_elapsed = time.perf_counter_ns() - started
        if child.returncode:
            # The closed worker emits only a fixed diagnostic class/reason,
            # never input paths, documents or an exception traceback.
            diagnostic = child.stderr[:512].decode("utf-8", "replace").strip()
            require(diagnostic.startswith("diagnostic refused:") and "\n" not in diagnostic,
                    "bounded diagnostic worker failed without a diagnostic")
            raise ProfileError("bounded worker failed: " + diagnostic)
        require(not child.stderr and len(child.stdout) <= MAX_REPORT_BYTES,
                "worker emitted unexpected or excessive output")
        report = strict_json(child.stdout)
        require(report.get("format") == FORMAT and report.get("provenance") == before
                and report.get("parity_passed") is True, "worker report differs from selected inputs")
        require(report.get("driver_sha256") == driver_sha
                and report.get("environment", {}).get("interpreter") == interpreter_before
                and report["environment"].get("startup_flags") == {
                    "isolated": 1, "no_site": 1, "dont_write_bytecode": True},
                "worker interpreter, driver or startup identity differs")
    except subprocess.TimeoutExpired:
        child_elapsed = time.perf_counter_ns() - started
        report = {"format": FORMAT, "scope": SCOPE, "status": "diagnostic_timeout",
                  "parity_passed": False, "provenance": before,
                  "scientific_eligibility": False, "native_acceptance_passed": False,
                  "historical_capture_complete": False,
                  "hard_wall_seconds": HARD_WALL_SECONDS}
    require(verify_inputs(source, recovery)["provenance"] == before,
            "inputs changed during bounded child")
    require(sha(read_file(driver)) == driver_sha, "driver changed during diagnostic")
    require(executable_identity(interpreter) == interpreter_before,
            "selected interpreter changed during diagnostic")
    report["driver_sha256"] = driver_sha
    report["isolated_child"] = True
    report["child_elapsed_wall_ns"] = child_elapsed
    report["selected_interpreter"] = interpreter_before
    raw = json.dumps(report, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    require(len(raw) <= MAX_REPORT_BYTES, "diagnostic report exceeds byte bound")
    output.mkdir()
    with (output / "report.json").open("xb") as stream:
        stream.write(raw)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--recovery", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.worker:
            require(args.output is None, "worker has no output-path capability")
            require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
                    "worker requires -I -B -S startup")
            sys.addaudithook(effect_guard)
            result = run_worker(args.source, args.recovery)
            sys.stdout.buffer.write(canonical(result) + b"\n")
            return 0
        require(args.output is not None, "--output is required")
        result = run_profile(args.source, args.recovery, args.output)
        print(json.dumps({"status": result["status"], "parity_passed": result["parity_passed"]}))
        return 0 if result["status"] == "measured" else 1
    except (ProfileError, OSError, ValueError, KeyError) as exc:
        # Detailed paths/raw fixture payloads are intentionally not published.
        reason = str(exc) if type(exc) is ProfileError else type(exc).__name__
        print(f"diagnostic refused: {reason}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
