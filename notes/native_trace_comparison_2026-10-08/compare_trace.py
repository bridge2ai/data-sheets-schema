#!/usr/bin/env python3
"""Bounded offline comparison of two exact Trace constructors, never a native run."""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from dataclasses import fields, is_dataclass
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import selectors
import signal
import stat
import subprocess
import sys
import time
from types import ModuleType
import zlib


DRIVER = Path(__file__).resolve()
UTILITY_RELATIVE = "notes/native_profile_recovery_2026-10-07/trace_prefix_profile.py"
UTILITY_SHA256 = "4097c8dff6e921b146feb49854b67487adc54b5a4da7943e22c9293849df01bf"
PREPARATION_SHA256 = "b72bcea58c3a64be466b642fd6493a1da51865f7f8afd730d8816f9c01756f15"
BASELINE_COMMIT = "0125eebbc214d0907c3b69d23758cd9441911a78"
CANDIDATE_COMMIT = "a8c11973da120cc0f792eef2d574dab7d910b09d"
MODULES = ("native_shared_contract", "native_shared_evidence", "native_shared_observations")
COMMON_MODULES = {
    MODULES[0]: "76664d4d9023a9a3a1975ca66f82bee0a4ce4b789c99c19606987ab2e50e65b9",
    MODULES[1]: "a50b042d1825456d70571dbf5e314ea5204f9d1451319e1c8353462852e294e5",
}
MODULE_PINS = {
    "baseline": {**COMMON_MODULES, MODULES[2]: "3bc93c2d1720d4e41ee83e7be7d8758a56836062c316f75ecc4b505e80b6d3ab"},
    "candidate": {**COMMON_MODULES, MODULES[2]: "4dc91259ecb079e8efe3067b0eeb01e584b575bdda813fcc6e7494bf39bcbba4"},
}
FORMAT = "native_trace_constructor_comparison_v1"
PAYLOAD_FORMAT = "native_trace_constructor_payload_v1"
ROLES = ("baseline", "candidate")
ORDER = ("baseline", "candidate", "candidate", "baseline", "baseline", "candidate")
CONTROLS = ("foreign_session", "exchanged_roles", "foreign_runtime_model")
HARD_WALL_SECONDS = 120
MAX_REPORT_BYTES = 4 * 1024 * 1024
MAX_PAYLOAD_BYTES = 128 * 1024 * 1024
MAX_COMPRESSED_BYTES = 8 * 1024 * 1024
MAX_WIRE_BYTES = 24 * 1024 * 1024
TRACE_FIELDS = ("transcript", "control", "session", "policy", "calls", "callbacks", "results", "decisions", "frames", "terminal")
WRONG_COMMAND_SUFFIX = "\n# diagnostic intentionally different command"
SCOPE = "Exact 0125 and reviewed single-decode Trace constructors on one preserved synthetic checkpoint"
LIMITATIONS = (
    "Constructor-only comparison; no callback, replay, helper, native or provider execution.",
    "Three alternating timing pairs share process and filesystem caches; no whole-path fraction or deadline inference.",
    "Candidate authority is exactly three compiled source modules, not an authenticated whole candidate Git tree.",
    "Recovered baseline source and original case bytes are verified; extraction-normalized historical file modes are not preserved claims.",
    "Fixed synthetic preparation05 is unchanged; no labels, source identities or policy/runtime paths are normalized.",
    "Before/after pins and local audit restrictions are local evidence, not authenticated execution or complete ABA protection.",
    "The unavailable 4366 source, native 900-second acceptance and scientific eligibility are not evaluated.",
    "Full evidence sidecars may contain private input paths and remain external; only compact evidence is suitable for repository notes.",
)


class ComparisonError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise ComparisonError(reason)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                      separators=(",", ":")).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utility():
    path = DRIVER.parents[2] / UTILITY_RELATIVE
    require(path.resolve(strict=True) == path, "utility path is not physical")
    raw = path.read_bytes()
    require(sha(raw) == UTILITY_SHA256, "utility differs from reviewed pin")
    module = ModuleType("trace_comparison_pinned_utility")
    module.__file__ = str(path)
    exec(compile(raw, "reviewed-utility/trace_prefix_profile.py", "exec"), module.__dict__)
    require(module.read_file(path, UTILITY_SHA256) == raw, "utility changed during load")
    return module


def isolation():
    require(sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode is True,
            "diagnostic requires -I -B -S")


def effect_guard(event, args):
    """No target process, socket, dynamic library or filesystem mutation event is allowed."""
    if (event.startswith(("socket.", "subprocess.", "os.exec", "os.spawn", "os.posix_spawn", "ctypes."))
            or event in {"os.system", "os.fork", "os.forkpty", "pty.spawn", "os.mkdir", "os.remove",
                         "os.rmdir", "os.rename", "os.link", "os.symlink", "os.chmod", "os.chown",
                         "os.truncate", "os.utime", "os.chdir", "os.putenv", "os.unsetenv",
                         "os.setxattr", "os.removexattr", "os.chflags"}):
        raise ComparisonError("worker forbids process, network, native loading and mutation effects")
    if event == "open":
        require(len(args) == 3, "unknown open audit shape")
        _, mode, flags = args
        writable = (type(mode) is str and any(c in mode for c in "wax+")) or (
            type(flags) is int and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        require(not writable, "worker forbids path and descriptor writes")


def module_bytes(tools, root, role):
    require(role in ROLES, "unknown source role")
    return {name: tools.read_file(root / "src/data_sheets_schema" / (name + ".py"), expected)
            for name, expected in MODULE_PINS[role].items()}


@contextmanager
def activated(modules):
    names = [n for n in sys.modules if n == "data_sheets_schema" or n.startswith("data_sheets_schema.")]
    previous = {n: sys.modules.pop(n) for n in names}
    package = ModuleType("data_sheets_schema")
    package.__path__ = []
    sys.modules[package.__name__] = package
    try:
        for short, module in modules.items():
            sys.modules["data_sheets_schema." + short] = module
            setattr(package, short, module)
        yield package
    finally:
        for name in list(sys.modules):
            if name == "data_sheets_schema" or name.startswith("data_sheets_schema."):
                del sys.modules[name]
        sys.modules.update(previous)


def compile_modules(tools, root, role, selected):
    """Canonical identities, explicit role/hash filenames; never import package initializers or pyc."""
    result = {}
    with activated(result) as package:
        for short in MODULES:
            path = root / "src/data_sheets_schema" / (short + ".py")
            raw = tools.read_file(path, MODULE_PINS[role][short])
            require(raw == selected[short], "source changed before compilation")
            name = "data_sheets_schema." + short
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            logical = f"trace-comparison/{role}/{sha(raw)}/{short}.py"
            exec(compile(raw, logical, "exec"), module.__dict__)
            require(module.__file__ == str(path) and module.__spec__.origin == str(path), "module origin differs")
            result[short] = module
            setattr(package, short, module)
    return result


def case_inventory(tools, case):
    entries = {}
    for current, dirs, files in os.walk(case, followlinks=False):
        for name in dirs:
            require(not (Path(current) / name).is_symlink(), "case has a directory symlink")
        for name in files:
            path = Path(current) / name
            raw = tools.read_file(path)
            entries[path.relative_to(case).as_posix()] = {
                "bytes": len(raw), "mode": stat.S_IMODE(path.stat().st_mode), "sha256": sha(raw)}
            require(len(entries) <= 68, "case has unexpected files")
    return {"entries": entries, "files": len(entries), "bytes": sum(x["bytes"] for x in entries.values())}


def checkpoint(tools, preparation):
    raw = tools.read_file(preparation, PREPARATION_SHA256)
    report = tools.strict_json(raw)
    require(report["format"] == "native_full_schema_checkpoint_v2" and report["status"] == "completed"
            and report["report_role"] == "checkpoint_preparation" and report["mode"] == "prepare",
            "selected report is not completed preparation05")
    result = report["result"]
    case = preparation.parent / "case"
    actual = case_inventory(tools, case)
    require(canonical(actual) == canonical(result["case_inventory"]), "case bytes, membership or modes differ")
    require(actual["files"] == 68 and actual["bytes"] == 25352291, "checkpoint inventory differs")
    def saved(name):
        require(name in actual["entries"], "checkpoint member is not in captured inventory")
        return tools.read_file(tools.member(case, name), actual["entries"][name]["sha256"])
    require(result["selection_relative"] == "authority/profile-selection.json", "selection identity differs")
    selection_raw = saved(result["selection_relative"])
    selection = tools.strict_json(selection_raw)
    composition_raw = saved("authority/profile-composition.json")
    composition = tools.strict_json(composition_raw)
    runtime_raw = saved("authority/profile-runtime.json")
    runtime = tools.strict_json(runtime_raw)
    execution_raw = saved("checkpoint/stages/binding/execution.json")
    execution = tools.strict_json(execution_raw)
    require(execution_raw == saved("checkpoint/synthetic-full-schema-4618-v1/registration.json"),
            "bound execution differs from captured registration")
    require(composition["runtime_raw_json"].encode() == runtime_raw
            and composition["runtime_sha256"] == sha(runtime_raw)
            and composition["selection_raw_json"].encode() == selection_raw
            and composition["selection_sha256"] == sha(selection_raw)
            and execution["composition_raw_json"].encode() == composition_raw
            and execution["composition_sha256"] == sha(composition_raw)
            and canonical(execution["runtime"]) == canonical(runtime), "captured authority association differs")
    policy = composition["policy"]
    require(sha(canonical(policy)) == composition["policy_sha256"], "policy hash differs")
    labels = {"arm": "BASELINE (input documents only)", "label": "offline-full-schema-4618-v1",
              "method": "claudecode_direct", "project": "SYNTHETIC"}
    require(selection["run"] == labels and runtime["deadline_seconds"] == 900,
            "synthetic labels or original runtime limit differ")
    observation_raw = saved("checkpoint/stages/observations/000017.json")
    observation = tools.strict_json(observation_raw)
    require(observation["kind"] == "d4d_native_shared_stage_observation"
            and type(observation["version"]) is int and observation["version"] == 1
            and observation["observation_type"] == "advance_admitted"
            and observation["execution_sha256"] == sha(execution_raw)
            and observation["selection_sha256"] == sha(selection_raw), "final observation binding differs")
    streams = {}
    for stream, count in (("transcript", 61), ("control", 22)):
        relative = f"checkpoint/synthetic-full-schema-4618-v1/{stream}.jsonl"
        complete = saved(relative)
        ref = observation[stream + "_prefix"]
        prefix = tools.verify_prefix(ref, complete, stream=stream, original_path=str(case / relative),
                                     execution_sha256=sha(execution_raw))
        require(prefix == complete and ref["lines"] == count, "observation does not cover complete selected stream")
        streams[stream] = {"raw": prefix, "reference": ref}
    binding = {"preparation_sha256": sha(raw), "case_inventory_sha256": sha(canonical(actual)),
               "case_files": actual["files"], "case_bytes": actual["bytes"], "labels": labels,
               "observation_index": 17, "observation_sha256": sha(observation_raw),
               "execution_sha256": sha(execution_raw), "selection_sha256": sha(selection_raw),
               "composition_sha256": sha(composition_raw), "policy_sha256": composition["policy_sha256"],
               "runtime_sha256": sha(runtime_raw), "session_id": observation["session_id"],
               "streams": {n: {k: v for k, v in x["reference"].items() if k != "path"}
                           for n, x in streams.items()}}
    return {"case": case, "streams": streams, "policy": policy, "runtime": runtime,
            "session_id": observation["session_id"], "binding": binding}


def verify_inputs(tools, baseline, candidate, recovery, preparation):
    recovered = tools.verify_inputs(baseline, recovery)
    selected = {"baseline": module_bytes(tools, baseline, "baseline"),
                "candidate": module_bytes(tools, candidate, "candidate")}
    require(selected["baseline"] == recovered["module_bytes"], "baseline module capture differs")
    captured = checkpoint(tools, preparation)
    binding = {"checkpoint": captured["binding"], "recovered_provenance": recovered["provenance"],
               "compiled_modules": json.loads(canonical(MODULE_PINS)), "candidate_declared_commit": CANDIDATE_COMMIT,
               "candidate_authentication_scope": "only the three exact compiled modules"}
    return {"binding": binding, "captured": captured, "modules": selected}


def full_typed(value):
    """Lossless bytes and complete typed structures; no digest replaces a compared value."""
    if value is None:
        return ["none"]
    if type(value) in (bool, int, float, str):
        require(type(value) is not float or math.isfinite(value), "nonfinite semantic value")
        return [type(value).__name__, value]
    if type(value) is bytes:
        return ["bytes_base64", base64.b64encode(value).decode("ascii")]
    if type(value) in (tuple, list):
        return [type(value).__name__, [full_typed(x) for x in value]]
    if type(value) is dict:
        return ["dict", [[full_typed(k), full_typed(v)] for k, v in value.items()]]
    if is_dataclass(value) and not isinstance(value, type):
        return ["dataclass", type(value).__module__ + "." + type(value).__qualname__,
                [[f.name, full_typed(getattr(value, f.name))] for f in fields(value)]]
    raise ComparisonError("unsupported complete semantic value")


@contextmanager
def lossless_formatter(tools):
    original = tools.typed_value
    tools.typed_value = full_typed
    try:
        yield
    finally:
        tools.typed_value = original


def semantic_trace(tools, trace):
    """All public Trace queries for the selected admitted, pending checkpoint."""
    semantics = tools.semantic_trace(trace)
    pending = trace.pending()
    require(type(pending) is tuple and len(pending) == 1, "checkpoint does not have one pending advance")
    identity = pending[0]
    request = trace.request(identity)
    inputs = tools.strict_json(request.input_json)
    require(request.tool_name == "Bash" and type(inputs) is dict
            and type(inputs.get("command")) is str and inputs["command"],
            "pending checkpoint call has no exact Bash command")
    command = inputs["command"]
    exact = tools.outcome(lambda: trace.current_advance(identity, command))
    wrong = tools.outcome(lambda: trace.current_advance(identity, command + WRONG_COMMAND_SUFFIX))
    require(exact["status"] == "returned" and wrong["status"] == "refused",
            "current_advance exact or wrong-command control differs")
    semantics["current_advance"] = {"tool_use_id": identity, "command": command,
                                     "exact": exact, "wrong_command": wrong}
    return semantics


def construct(tools, factory, *, timed):
    started = time.thread_time_ns(), time.perf_counter_ns()
    trace, failure = None, None
    try:
        trace = factory()
    except ValueError as exc:
        failure = exc
    elapsed = {"thread_cpu_ns": time.thread_time_ns() - started[0], "wall_ns": time.perf_counter_ns() - started[1]}
    fingerprint_started = time.perf_counter_ns()
    with lossless_formatter(tools):
        value = ({"status": "returned", "semantics": semantic_trace(tools, trace)} if failure is None else
                 {"status": "refused", "exception": tools.exception_value(failure)})
    raw = canonical(value)
    require(len(raw) <= MAX_PAYLOAD_BYTES, "complete semantic state exceeds byte bound")
    return trace, raw, {"timed": timed, **elapsed, "fingerprint_wall_ns": time.perf_counter_ns() - fingerprint_started,
                        "status": value["status"], "semantic_sha256": sha(raw)}


def factory_for(modules, captured, control=None):
    c, observed = modules[MODULES[0]], modules[MODULES[2]]
    prefixes = {name: c.EvidencePrefix(stream=name, path=value["reference"]["path"], raw=value["raw"],
                 bytes=len(value["raw"]), sha256=value["reference"]["sha256"], lines=value["reference"]["lines"])
                for name, value in captured["streams"].items()}
    # Each construction receives its own complete mutable declarations.
    policy = json.loads(canonical(captured["policy"]))
    runtime = json.loads(canonical(captured["runtime"]))
    session = captured["session_id"]
    if control == "foreign_session":
        session = "diagnostic-foreign-session"
    elif control == "exchanged_roles":
        prefixes = {"transcript": prefixes["control"], "control": prefixes["transcript"]}
    elif control == "foreign_runtime_model":
        runtime["model"] = "diagnostic-other-model"
    else:
        require(control is None, "unknown refusal control")
    return lambda: observed.Trace(prefixes["transcript"], prefixes["control"], session_id=session,
                                  policy=policy, runtime=runtime)


def decode_count(tools, modules, captured):
    observed = modules[MODULES[2]]
    original = observed.rows
    counts = {"transcript": 0, "control": 0}
    def counted(prefix):
        require(prefix.stream in counts, "decoder saw another stream")
        counts[prefix.stream] += 1
        return original(prefix)
    observed.rows = counted
    try:
        _, raw, _ = construct(tools, factory_for(modules, captured), timed=False)
    finally:
        observed.rows = original
    return counts, raw


def compare_constructors(tools, loaded, captured):
    states, samples = {}, []
    for index, role in enumerate(ORDER):
        with activated(loaded[role]):
            _, raw, metrics = construct(tools, factory_for(loaded[role], captured), timed=True)
        require(metrics["status"] == "returned", "positive constructor refused")
        if role in states:
            require(raw == states[role], "timed constructor state changed between independent instances")
        else:
            states[role] = raw
        samples.append({"sample": index, "role": role, **metrics})
    require(states["baseline"] == states["candidate"], "complete positive payloads differ")
    counts, refusal_rows, payloads = {}, {}, {}
    for role in ROLES:
        with activated(loaded[role]):
            count, raw = decode_count(tools, loaded[role], captured)
            expected = 2 if role == "baseline" else 1
            require(count == {"transcript": expected, "control": expected}, "full-stream decode counts differ")
            require(raw == states[role], "decode instrumentation changed complete semantics")
            counts[role] = count
            refusals = []
            for control in CONTROLS:
                _, refusal, metrics = construct(tools, factory_for(loaded[role], captured, control), timed=False)
                require(metrics["status"] == "refused", "negative constructor control returned")
                refusals.append({"control": control, "outcome": tools.strict_json(refusal)})
            refusal_rows[role] = refusals
            first = factory_for(loaded[role], captured)()
            second = factory_for(loaded[role], captured)()
            require(first is not second and first.calls is not second.calls and first.frames is not second.frames,
                    "constructor instances share mutable state")
            # Also mutate nested decoded objects: separate outer dicts alone
            # would not detect a shared decoded-row cache between instances.
            first.frames[next(iter(first.frames))]["diagnostic_mutation"] = True
            first.calls[next(iter(first.calls))][2]["input"]["diagnostic_mutation"] = True
            first.calls.clear()
            first.frames.clear()
            first.policy.clear()
            with lossless_formatter(tools):
                second_raw = canonical({"status": "returned", "semantics": semantic_trace(tools, second)})
            require(second_raw == states[role], "mutating one constructor changed another instance")
            payloads[role] = {"format": PAYLOAD_FORMAT, "positive": tools.strict_json(states[role]),
                              "refusal_controls": refusals}
    require(canonical(refusal_rows["baseline"]) == canonical(refusal_rows["candidate"]),
            "complete refusal graphs differ")
    return {"samples": samples, "decode_counts": counts,
            "instance_independence": {role: True for role in ROLES}, "payloads": payloads}


def pack_payload(document):
    raw = canonical(document)
    require(len(raw) <= MAX_PAYLOAD_BYTES, "uncompressed payload exceeds byte bound")
    compressed = gzip.compress(raw, mtime=0)
    require(len(compressed) <= MAX_COMPRESSED_BYTES, "compressed payload exceeds byte bound")
    return compressed, {"compressed_sha256": sha(compressed), "compressed_bytes": len(compressed),
                        "uncompressed_sha256": sha(raw), "uncompressed_bytes": len(raw)}


def unpack_payload(tools, compressed, pin):
    require(type(compressed) is bytes and len(compressed) <= MAX_COMPRESSED_BYTES,
            "compressed payload exceeds byte bound")
    require(set(pin) == {"compressed_sha256", "compressed_bytes", "uncompressed_sha256", "uncompressed_bytes"},
            "payload pin shape differs")
    require(type(pin["compressed_bytes"]) is int and type(pin["uncompressed_bytes"]) is int
            and 0 < pin["uncompressed_bytes"] <= MAX_PAYLOAD_BYTES
            and pin["compressed_bytes"] == len(compressed) and pin["compressed_sha256"] == sha(compressed),
            "compressed payload pin differs")
    decoder = zlib.decompressobj(31)
    raw = decoder.decompress(compressed, MAX_PAYLOAD_BYTES + 1)
    require(len(raw) <= MAX_PAYLOAD_BYTES and decoder.eof and not decoder.unused_data
            and not decoder.unconsumed_tail, "payload is truncated, oversized or contains trailing members")
    require(len(raw) == pin["uncompressed_bytes"] and sha(raw) == pin["uncompressed_sha256"],
            "uncompressed payload pin differs")
    document = tools.strict_json(raw)
    require(canonical(document) == raw, "full payload is not canonical strict JSON")
    return raw, document


def validate_typed(value, *, depth=0):
    require(depth <= 128 and type(value) is list and value and type(value[0]) is str,
            "invalid complete typed value")
    tag = value[0]
    if tag == "none":
        require(len(value) == 1, "invalid none value")
    elif tag in {"bool", "int", "float", "str", "bytes_base64"}:
        expected = {"bool": bool, "int": int, "float": float, "str": str, "bytes_base64": str}[tag]
        require(len(value) == 2 and type(value[1]) is expected, "typed scalar type differs")
        if tag == "float":
            require(math.isfinite(value[1]), "typed scalar is nonfinite")
        if tag == "bytes_base64":
            decoded = base64.b64decode(value[1], validate=True)
            require(base64.b64encode(decoded).decode("ascii") == value[1], "noncanonical typed bytes")
    elif tag in {"list", "tuple"}:
        require(len(value) == 2 and type(value[1]) is list, "invalid typed sequence")
        for item in value[1]:
            validate_typed(item, depth=depth + 1)
    elif tag in {"dict", "dataclass"}:
        require(len(value) == (2 if tag == "dict" else 3), "invalid typed mapping shape")
        if tag == "dataclass":
            require(type(value[1]) is str and value[1].startswith("data_sheets_schema."),
                    "another dataclass identity")
        pairs = value[-1]
        require(type(pairs) is list, "invalid typed mapping")
        keys = set()
        for pair in pairs:
            require(type(pair) is list and len(pair) == 2, "invalid typed mapping entry")
            if tag == "dict":
                validate_typed(pair[0], depth=depth + 1)
            else:
                require(type(pair[0]) is str, "invalid dataclass field")
            identity = canonical(pair[0])
            require(identity not in keys, "duplicate typed mapping key")
            keys.add(identity)
            validate_typed(pair[1], depth=depth + 1)
    else:
        raise ComparisonError("unknown complete typed value tag")


def validate_exception(graph):
    seen = set()
    def visit(node):
        if node is None:
            return
        require(type(node) is dict, "invalid exception graph")
        if set(node) == {"reference"}:
            require(type(node["reference"]) is int and node["reference"] in seen, "unbound exception reference")
            return
        require(set(node) == {"node", "type", "arguments", "cause", "context", "suppress_context", "notes"},
                "exception graph node shape differs")
        require(type(node["node"]) is int and node["node"] == len(seen) < 32
                and type(node["type"]) is str and bool(node["type"])
                and type(node["suppress_context"]) is bool, "exception graph identity differs")
        seen.add(node["node"])
        validate_typed(node["arguments"])
        require(node["arguments"][0] == "tuple", "exception arguments are not a tuple")
        validate_typed(node["notes"])
        visit(node["cause"])
        visit(node["context"])
    require(graph is not None, "missing refusal graph")
    visit(graph)


def validate_outcome(value, *, positive=False):
    require(type(value) is dict, "invalid semantic outcome")
    if value.get("status") == "returned":
        if positive:
            require(set(value) == {"status", "semantics"} and type(value["semantics"]) is dict
                    and set(value["semantics"]) == {"state", "pending", "tool_methods", "current_advance"},
                    "incomplete Trace semantics")
            semantics = value["semantics"]
            validate_typed(semantics["state"])
            validate_typed(semantics["pending"])
            require(semantics["state"][0] == "dict" and semantics["pending"][0] == "tuple"
                    and type(semantics["tool_methods"]) is dict and semantics["tool_methods"],
                    "missing state or tool-method denominator")
            pairs = semantics["state"][1]
            require([key for key, _ in pairs] == [["str", name] for name in TRACE_FIELDS],
                    "complete Trace state field roster differs")
            state = {key[1]: value for key, value in pairs}
            require(state["session"][0] == "str" and bool(state["session"][1])
                    and (state["terminal"] == ["none"] or state["terminal"][0] == "int"),
                    "Trace scalar state has another type")
            for stream in ("transcript", "control"):
                prefix = state[stream]
                require(prefix[0] == "dataclass" and prefix[1] == "data_sheets_schema.native_shared_contract.EvidencePrefix"
                        and [name for name, _ in prefix[2]] == ["stream", "path", "raw", "bytes", "sha256", "lines"],
                        "complete prefix field roster differs")
                slots = dict(prefix[2])
                require(slots["stream"] == ["str", stream] and slots["path"][0] == "str"
                        and slots["raw"][0] == "bytes_base64" and slots["bytes"][0] == "int"
                        and slots["sha256"][0] == "str" and slots["lines"][0] == "int", "prefix types differ")
                raw = base64.b64decode(slots["raw"][1], validate=True)
                require(slots["bytes"][1] == len(raw) and slots["sha256"][1] == sha(raw)
                        and slots["lines"][1] == raw.count(b"\n") and raw.endswith(b"\n"),
                        "literal prefix content differs from its metadata")
            for name in ("calls", "callbacks", "results", "decisions", "frames", "policy"):
                require(state[name][0] == "dict", "Trace mapping has another type")
            call_ids = [key[1] for key, _ in state["calls"][1] if key[0] == "str"]
            require(len(call_ids) == len(state["calls"][1]) and set(call_ids) == set(semantics["tool_methods"]),
                    "tool-method denominator differs from captured calls")
            results = [key[1] for key, _ in state["results"][1] if key[0] == "str"]
            require(len(results) == len(state["results"][1]) and set(results) <= set(call_ids)
                    and semantics["pending"] == ["tuple", [["str", name] for name in call_ids if name not in results]],
                    "pending or result identities differ")
            for identity, methods in semantics["tool_methods"].items():
                require(type(identity) is str and identity and type(methods) is dict
                        and set(methods) == {"request", "admitted", "settled"}, "incomplete method observations")
                for result in methods.values():
                    validate_outcome(result)
            advance = semantics["current_advance"]
            require(type(advance) is dict and set(advance) == {"tool_use_id", "command", "exact", "wrong_command"}
                    and semantics["pending"] == ["tuple", [["str", advance["tool_use_id"]]]]
                    and type(advance["command"]) is str and advance["command"], "incomplete current advance query")
            call = next(item for key, item in state["calls"][1] if key == ["str", advance["tool_use_id"]])
            require(call[0] == "tuple" and len(call[1]) == 3, "current advance call shape differs")
            declaration = json_from_typed(call[1][2])
            require(declaration.get("name") == "Bash" and type(declaration.get("input")) is dict
                    and declaration["input"].get("command") == advance["command"], "advance query differs from captured call")
            validate_outcome(advance["exact"])
            validate_outcome(advance["wrong_command"])
            require(advance["exact"]["status"] == "returned" and advance["wrong_command"]["status"] == "refused"
                    and canonical(advance["exact"]) == canonical(semantics["tool_methods"][advance["tool_use_id"]]["admitted"]),
                    "current advance positive/refusal outcomes differ")
        else:
            require(set(value) == {"status", "value"}, "incomplete method return")
            validate_typed(value["value"])
    else:
        require(not positive and set(value) == {"status", "exception"} and value["status"] == "refused",
                "invalid refusal outcome")
        validate_exception(value["exception"])


def json_from_typed(value):
    """Decode only the JSON-valued policy, after strict typed validation."""
    if value[0] == "none":
        return None
    if value[0] in {"bool", "int", "float", "str"}:
        return value[1]
    if value[0] == "list":
        return [json_from_typed(item) for item in value[1]]
    require(value[0] == "dict", "policy is not a JSON-valued typed structure")
    require(all(key[0] == "str" for key, _ in value[1]), "policy has a nonstring key")
    return {key[1]: json_from_typed(item) for key, item in value[1]}


def validate_state_binding(positive, binding):
    state = {key[1]: value for key, value in positive["semantics"]["state"][1]}
    require(state["session"] == ["str", binding["session_id"]]
            and sha(canonical(json_from_typed(state["policy"]))) == binding["policy_sha256"],
            "complete state session or policy differs from selected checkpoint")
    for stream in ("transcript", "control"):
        prefix = dict(state[stream][2])
        selected = binding["streams"][stream]
        require(prefix["bytes"][1] == selected["through_bytes"]
                and prefix["lines"][1] == selected["lines"] and prefix["sha256"][1] == selected["sha256"]
                and sha(canonical({"domain": "native_shared_stream_v1", "execution_sha256": binding["execution_sha256"],
                    "stream": stream, "path": prefix["path"][1]})) == selected["stream_id"],
                "complete state prefix differs from selected checkpoint")


def summary_validation(tools, summary, blobs, binding, driver_pin, python_pin):
    require(type(summary) is dict and set(summary) == {
        "format", "scope", "status", "binding", "driver_sha256", "utility_sha256", "python_identity",
        "startup_flags", "samples", "decode_counts", "instance_independence", "payloads", "required",
        "completed", "failed", "missing", "parity_passed", "inputs_unchanged", "environment", "worker_wall_ns",
        "overhead", "execution_authorized", "native_acceptance_evaluated", "scientific_eligibility", "limitations"},
        "worker summary shape differs")
    require(summary["format"] == FORMAT and summary["scope"] == SCOPE and summary["status"] == "completed"
            and canonical(summary["binding"]) == canonical(binding) and summary["driver_sha256"] == driver_pin
            and summary["utility_sha256"] == UTILITY_SHA256 and summary["python_identity"] == python_pin
            and canonical(summary["startup_flags"]) == canonical({"isolated": 1, "no_site": 1,
                                                                 "dont_write_bytecode": True}),
            "worker source, capture or runtime binding differs")
    for flag in ("execution_authorized", "native_acceptance_evaluated", "scientific_eligibility"):
        require(summary[flag] is False, "worker claims acceptance")
    require(summary["parity_passed"] is True and summary["inputs_unchanged"] is True
            and canonical(summary["required"]) == canonical({"timed_constructors": 6, "decode_checks": 2,
                                        "refusal_controls": 6, "instance_checks": 2, "advance_controls": 4})
            and canonical(summary["completed"]) == canonical(summary["required"])
            and summary["failed"] == [] and summary["missing"] == [],
            "worker denominator is incomplete")
    require(canonical(summary["decode_counts"]) == canonical({"baseline": {"transcript": 2, "control": 2},
                                          "candidate": {"transcript": 1, "control": 1}})
            and summary["instance_independence"] == {"baseline": True, "candidate": True}
            and all(type(v) is bool for v in summary["instance_independence"].values()),
            "worker decode or independence control differs")
    require(summary["limitations"] == list(LIMITATIONS)
            and type(summary["environment"]) is dict and set(summary["environment"]) == {"python", "platform", "machine"}
            and all(type(v) is str and v for v in summary["environment"].values()), "environment or scope disclosure differs")
    require(type(summary["worker_wall_ns"]) is int and summary["worker_wall_ns"] >= 0
            and type(summary["overhead"]) is dict and set(summary["overhead"]) == {
                "setup_wall_ns", "final_verification_wall_ns", "evidence_pack_wall_ns"}
            and all(type(v) is int and v >= 0 for v in summary["overhead"].values()), "invalid overhead timings")
    require(set(blobs) == set(summary["payloads"]) == {role + ".json.gz" for role in ROLES}, "payload roster differs")
    states = {}
    for role in ROLES:
        name = role + ".json.gz"
        raw, payload = unpack_payload(tools, blobs[name], summary["payloads"][name])
        require(type(payload) is dict and set(payload) == {"format", "positive", "refusal_controls"}
                and payload["format"] == PAYLOAD_FORMAT and payload["positive"].get("status") == "returned",
                "complete payload shape differs")
        validate_outcome(payload["positive"], positive=True)
        validate_state_binding(payload["positive"], binding["checkpoint"])
        require(len(payload["refusal_controls"]) == len(CONTROLS), "refusal denominator differs")
        for row, control in zip(payload["refusal_controls"], CONTROLS):
            require(set(row) == {"control", "outcome"} and row["control"] == control
                    and set(row["outcome"]) == {"status", "exception"}
                    and row["outcome"]["status"] == "refused", "refusal payload differs")
            validate_outcome(row["outcome"])
        states[role] = raw, payload
    require(states["baseline"][0] == states["candidate"][0], "full role payloads differ")
    require(len(summary["samples"]) == len(ORDER), "timed denominator differs")
    for index, (sample, role) in enumerate(zip(summary["samples"], ORDER)):
        require(set(sample) == {"sample", "role", "timed", "thread_cpu_ns", "wall_ns", "fingerprint_wall_ns",
                                "status", "semantic_sha256"} and type(sample["sample"]) is int
                and sample["sample"] == index and sample["role"] == role and sample["timed"] is True
                and sample["status"] == "returned"
                and sample["semantic_sha256"] == sha(canonical(states[role][1]["positive"])), "timed sample differs")
        for key in ("thread_cpu_ns", "wall_ns", "fingerprint_wall_ns"):
            require(type(sample[key]) is int and sample[key] >= 0, "invalid timing")
    return summary


def dispatch(argv):
    """One closed child, bounded pipe capture, fixed wall deadline, kill and reap."""
    started = time.monotonic()
    child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": MAX_WIRE_BYTES, "stderr": 4096}
    timed_out, overflow, killed = False, False, False
    with selectors.DefaultSelector() as selector:
        for stream, name in ((child.stdout, "stdout"), (child.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        try:
            while selector.get_map():
                remaining = HARD_WALL_SECONDS - (time.monotonic() - started)
                if remaining <= 0 and not killed:
                    timed_out = True
                if (timed_out or overflow) and not killed:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    killed = True
                for key, _ in selector.select(max(0.0, min(0.1, remaining)) if not killed else 0.1):
                    part = os.read(key.fileobj.fileno(), 65536)
                    if not part:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    target, limit = captured[key.data], limits[key.data]
                    if len(target) + len(part) > limit:
                        overflow = True
                    target.extend(part[:max(0, limit - len(target))])
            try:
                code = child.wait(timeout=max(0.0, HARD_WALL_SECONDS - (time.monotonic() - started)))
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                killed = True
                code = child.wait()
        finally:
            if child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
            for stream in (child.stdout, child.stderr):
                stream.close()
    return code, bytes(captured["stdout"]), bytes(captured["stderr"]), timed_out, overflow


def worker(baseline, candidate, recovery, preparation):
    tools = utility()
    started = time.perf_counter_ns()
    python_path = Path(sys.executable).resolve(strict=True)
    python_pin, driver_pin = tools.executable_identity(python_path), sha(tools.read_file(DRIVER))
    before = verify_inputs(tools, baseline, candidate, recovery, preparation)
    loaded = {role: compile_modules(tools, root, role, before["modules"][role])
              for role, root in (("baseline", baseline), ("candidate", candidate))}
    setup_done = time.perf_counter_ns()
    measured = compare_constructors(tools, loaded, before["captured"])
    verified_at = time.perf_counter_ns()
    after = verify_inputs(tools, baseline, candidate, recovery, preparation)
    require(canonical(before["binding"]) == canonical(after["binding"]), "inputs changed during constructor comparison")
    require(tools.executable_identity(python_path) == python_pin and sha(tools.read_file(DRIVER)) == driver_pin,
            "worker interpreter or driver changed")
    finalized = time.perf_counter_ns()
    blobs, pins = {}, {}
    for role in ROLES:
        name = role + ".json.gz"
        blobs[name], pins[name] = pack_payload(measured["payloads"][role])
    required = {"timed_constructors": 6, "decode_checks": 2, "refusal_controls": 6, "instance_checks": 2,
                "advance_controls": 4}
    summary = {"format": FORMAT, "scope": SCOPE, "status": "completed", "binding": before["binding"],
        "driver_sha256": driver_pin, "utility_sha256": UTILITY_SHA256, "python_identity": python_pin,
        "startup_flags": {"isolated": sys.flags.isolated, "no_site": sys.flags.no_site,
                          "dont_write_bytecode": sys.dont_write_bytecode},
        "samples": measured["samples"], "decode_counts": measured["decode_counts"],
        "instance_independence": measured["instance_independence"], "payloads": pins,
        "required": required, "completed": dict(required), "failed": [], "missing": [],
        "parity_passed": True, "inputs_unchanged": True,
        "environment": {"python": sys.version, "platform": sys.platform, "machine": os.uname().machine},
        "worker_wall_ns": time.perf_counter_ns() - started,
        "overhead": {"setup_wall_ns": setup_done - started, "final_verification_wall_ns": finalized - verified_at,
                     "evidence_pack_wall_ns": time.perf_counter_ns() - finalized},
        "execution_authorized": False, "native_acceptance_evaluated": False, "scientific_eligibility": False,
        "limitations": list(LIMITATIONS)}
    return summary, blobs


def output_path(output, protected):
    output = Path(output).absolute()
    require(output.parent.resolve(strict=True) == output.parent, "output parent is not physical")
    require(not output.exists() and not output.is_symlink(), "output must be new")
    for path in protected:
        path = Path(path).resolve(strict=True)
        require(not output.is_relative_to(path) and not path.is_relative_to(output), "output overlaps protected input or runtime")
    return output


def run_comparison(baseline, candidate, recovery, preparation, output):
    isolation()
    tools = utility()
    baseline, candidate, recovery, preparation = (Path(p).resolve(strict=True) for p in (
        baseline, candidate, recovery, preparation))
    interpreter = Path(sys.executable).resolve(strict=True)
    output = output_path(output, (baseline, candidate, recovery, preparation.parent, DRIVER.parents[2],
                                  Path(sys.base_prefix).resolve(strict=True), interpreter))
    before = verify_inputs(tools, baseline, candidate, recovery, preparation)
    driver_pin, python_pin = sha(tools.read_file(DRIVER)), tools.executable_identity(interpreter)
    argv = [str(interpreter), "-I", "-B", "-S", str(DRIVER), "--worker", "--baseline", str(baseline),
            "--candidate", str(candidate), "--recovery", str(recovery), "--preparation", str(preparation)]
    started = time.perf_counter_ns()
    exit_code, stdout, stderr, timed_out, overflow = dispatch(argv)
    elapsed = time.perf_counter_ns() - started
    after = verify_inputs(tools, baseline, candidate, recovery, preparation)
    require(canonical(before["binding"]) == canonical(after["binding"]), "inputs changed during bounded child")
    require(sha(tools.read_file(DRIVER)) == driver_pin and tools.executable_identity(interpreter) == python_pin,
            "parent source or interpreter changed")
    blobs = {}
    if timed_out or overflow or exit_code:
        summary = {"format": FORMAT, "scope": SCOPE,
            "status": "diagnostic_timeout" if timed_out else "diagnostic_refused", "binding": before["binding"],
            "driver_sha256": driver_pin, "utility_sha256": UTILITY_SHA256, "python_identity": python_pin,
            "parity_passed": False, "inputs_unchanged": True,
            "required": {"timed_constructors": 6, "decode_checks": 2, "refusal_controls": 6, "instance_checks": 2,
                         "advance_controls": 4},
            "completed": {}, "failed": ["bounded_worker"], "missing": ["verified_complete_worker_payload"],
            "execution_authorized": False, "native_acceptance_evaluated": False, "scientific_eligibility": False,
            "limitations": list(LIMITATIONS)}
    else:
        require(not stderr and len(stdout) <= MAX_WIRE_BYTES, "unexpected or excessive worker output")
        wire = tools.strict_json(stdout)
        require(type(wire) is dict and set(wire) == {"summary", "payloads_base64"}, "worker wire shape differs")
        require(type(wire["payloads_base64"]) is dict and set(wire["payloads_base64"]) == {r + ".json.gz" for r in ROLES},
                "worker payload roster differs")
        for name, encoded in wire["payloads_base64"].items():
            require(type(encoded) is str and len(encoded) <= 4 * ((MAX_COMPRESSED_BYTES + 2) // 3), "worker payload exceeds wire cap")
            blobs[name] = base64.b64decode(encoded, validate=True)
        summary = summary_validation(tools, wire["summary"], blobs, before["binding"], driver_pin, python_pin)
    summary.update(parent_child_wall_ns=elapsed, diagnostic_wall_bound_seconds=HARD_WALL_SECONDS,
                   child_exit_code=exit_code, captured_output_truncated=overflow,
                   stdout_bytes=len(stdout), stdout_sha256=sha(stdout),
                   stderr_bytes=len(stderr), stderr_sha256=sha(stderr))
    raw = canonical(summary) + b"\n"
    require(len(raw) <= MAX_REPORT_BYTES, "report exceeds fixed byte bound")
    output_path(output, (baseline, candidate, recovery, preparation.parent, DRIVER.parents[2],
                         Path(sys.base_prefix).resolve(strict=True), interpreter))
    output.mkdir()
    for name, data in {**blobs, "report.json": raw}.items():
        with (output / name).open("xb") as stream:
            stream.write(data)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate", "recovery", "preparation"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        isolation()
        if args.worker:
            require(args.output is None, "worker has no output capability")
            sys.addaudithook(effect_guard)
            summary, blobs = worker(args.baseline, args.candidate, args.recovery, args.preparation)
            wire = canonical({"summary": summary, "payloads_base64": {
                name: base64.b64encode(raw).decode("ascii") for name, raw in blobs.items()}}) + b"\n"
            require(len(wire) <= MAX_WIRE_BYTES, "worker wire exceeds fixed byte bound")
            sys.stdout.buffer.write(wire)
            return 0
        require(args.output is not None, "output is required")
        result = run_comparison(args.baseline, args.candidate, args.recovery, args.preparation, args.output)
        print(json.dumps({"status": result["status"], "parity_passed": result["parity_passed"]}))
        return 0 if result["status"] == "completed" else 1
    except Exception as exc:
        reason = str(exc) if type(exc) is ComparisonError else type(exc).__name__
        print("diagnostic refused: " + reason, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
