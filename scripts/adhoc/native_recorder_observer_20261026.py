#!/usr/bin/env python3
"""Observe native recorder timing without replacing production callables.

Purpose: N2 recorder timeout diagnosis (#4354), 2026-10-26. Inputs: the selected
checkout and naturally executing ``python -m data_sheets_schema.cli provenance
record``. Outputs: exclusive JSONL phase/counter evidence and a 170-second
process-age faulthandler stack. No production imports, wrappers, provider calls,
guard changes, or claim that diagnostic timings equal uninstrumented timings.

Install the identical BOOTSTRAP immediately before ``cli()`` in diagnostic-only
copies of cli/__main__.py, with this helper and its adjacent CONFIG_NAME. The
closed registered child environment is unchanged. Omit all diagnostic changes
from the three required uninstrumented 01969cbed trials.
"""
from __future__ import annotations

import ast
import atexit
import ctypes
import faulthandler
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time


BOOTSTRAP = '''# Diagnostic-only recorder observer; identical in both measured revisions.
import sys as _recorder_observer_sys
if _recorder_observer_sys.argv[1:3] == ["provenance", "record"]:
    import runpy as _recorder_observer_runpy
    from pathlib import Path as _recorder_observer_Path
    _recorder_observer_root = _recorder_observer_Path(__file__).resolve().parents[3]
    _recorder_observer_runpy.run_path(str(
        _recorder_observer_root / "scripts/adhoc/native_recorder_observer_20261026.py"
    ))["install_from_config"](_recorder_observer_root)
'''
CONFIG_NAME = "native_recorder_observer_20261026.config.json"
CONFIG_BYTES = b'{"output_parent":"/private/tmp/d4d-recorder-observer-20261026"}\n'
MAX_PHASE_EVENTS_PER_TARGET = 512

# Only these ordinary functions get local return events and timed unwind events.
# PY_UNWIND is global-only in CPython; unrelated unwinds are counted and ignored.
# Cache functions get local LINE events; recursive YAML/JSON leaf calls do not.
PHASES = {
    "cli.provenance": {"record": "recorder", "_inline_checks": "inline_checks"},
    "provenance": {"ProvenanceRecord.write": "record_write", "check_record": "record_validation",
                   "_record_validator": "record_validator_construction"},
    "backfill_checks": {"compute": "backfill_compute", "apply": "backfill_apply"},
    "duplicate_keys": {"find_duplicate_keys": "duplicate_keys", "duplicate_keys_in": "duplicate_keys_file"},
    "receipts": {"check": "receipts", "block_for": "receipt_block"},
    "grounding": {"form_facts": "form", "check_run": "grounding"},
    "report_claims": {"check_report": "report_claims"},
    "d4d_pair_consistency": {"validate_pair_data": "pair_consistency"},
    "native_shared_capture": {
        "live_provenance_block": "native_live_provenance", "_recorded_run": "native_recorded_run",
        "_base": "native_base", "_load": "native_load", "_load_live": "native_load_live",
        "_loaded": "native_loaded", "_checked_observations": "native_checked_observations",
    },
    "native_shared_receipts": {"_ReceiptCatalogContext.schema_data": "receipt_schema_catalog"},
}
CACHE_TARGETS = {
    "typed_audit": ("_bounded_json", "_open", "DerivationCache._derive", "DerivationCache._store"),
    "shared_generation": ("memo",),
    "native_catalog_reuse": ("runtime_token",),
}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": _sha(raw)}


def process_age():
    """Read this process's OS start time; importing cli preceded __main__.

    Darwin layout: local macOS SDK sys/proc_info.h struct proc_bsdinfo,
    PROC_PIDTBSDINFO=3; sys/param.h MAXCOMLEN=16. No ps subprocess is used.
    """
    if sys.platform == "darwin":
        class ProcBSDInfo(ctypes.Structure):
            _fields_ = [(name, ctypes.c_uint32) for name in (
                "flags", "status", "xstatus", "pid", "ppid", "uid", "gid",
                "ruid", "rgid", "svuid", "svgid", "rfu_1")]
            _fields_ += [("comm", ctypes.c_char * 16), ("name", ctypes.c_char * 32)]
            _fields_ += [(name, ctypes.c_uint32) for name in (
                "nfiles", "pgid", "pjobc", "e_tdev", "e_tpgid")]
            _fields_ += [("nice", ctypes.c_int32), ("start_sec", ctypes.c_uint64),
                        ("start_usec", ctypes.c_uint64)]
        lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                                    ctypes.c_void_p, ctypes.c_int]
        lib.proc_pidinfo.restype = ctypes.c_int
        info = ProcBSDInfo()
        result = lib.proc_pidinfo(os.getpid(), 3, 0, ctypes.byref(info), ctypes.sizeof(info))
        if result != ctypes.sizeof(info) or info.pid != os.getpid():
            raise RuntimeError("cannot establish recorder process age with libproc")
        age = time.time() - info.start_sec - info.start_usec / 1_000_000
        method = "libproc.proc_pidinfo(PROC_PIDTBSDINFO)"
    elif sys.platform.startswith("linux"):
        fields = Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()
        started = int(fields[19]) / os.sysconf("SC_CLK_TCK")
        age = float(Path("/proc/uptime").read_text().split()[0]) - started
        method = "/proc/self/stat starttime and /proc/uptime"
    else:
        raise RuntimeError("no verified process-age reader for this platform")
    if age < 0:
        raise RuntimeError("process age is negative; diagnostic timer not established")
    return {"seconds": age, "method": method}


def _definitions(tree):
    found = {}
    def walk(nodes, parents=()):
        for node in nodes:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                name = ".".join((*parents, node.name))
                if not isinstance(node, ast.ClassDef):
                    found[name] = node
                walk(node.body, (*parents, node.name))
    walk(tree.body)
    return found


def _counter_sites(node, qualname):
    """Match exact statement AST, not line numbers shared across revisions.

    A LINE callback precedes a statement. An eviction entry becomes confirmed
    only at the next local line/return/unwind after the dictionary shrank by one.
    No eviction is inferred merely from final cache size or byte differences.
    """
    spellings = {
        "return json.loads(raw)": "warm_decode",
        "_VALIDATED_BOUNDED_BYTES.clear()": "validated_set_clear",
        "self._bytes -= len(self._rows.pop(next(iter(self._rows))))": "typed_eviction",
        "del cache[next(iter(cache))]": "shared_eviction",
        "return json.loads(cache[key])": "shared_hit_decode",
        "result = build()": "shared_miss",
        "value = json.loads(encoded)": "derive_decode",
        "value = json.loads(hit)": "open_serialized_decode",
        "raw_bytes, payload_json = hit": "open_legacy_copy",
        "opened.pop(next(iter(opened)))": "legacy_open_eviction",
    }
    signatures = {ast.dump(ast.parse(s).body[0], include_attributes=False): label
                  for s, label in spellings.items()}
    sites = {}
    for child in ast.walk(node):
        if not isinstance(child, ast.stmt):
            continue
        label = signatures.get(ast.dump(child, include_attributes=False))
        if label:
            sites[child.lineno] = label
        if (qualname == "DerivationCache._derive" and isinstance(child, ast.If)
                and ast.dump(child.test, include_attributes=False)
                == ast.dump(ast.parse("encoded is None", mode="eval").body, include_attributes=False)):
            sites[child.lineno] = "derive_lookup"
        if (qualname == "_open" and isinstance(child, ast.If)
                and ast.dump(child.test, include_attributes=False)
                == ast.dump(ast.parse("hit is not None", mode="eval").body, include_attributes=False)):
            sites[child.lineno] = "open_lookup"
    return sites


def _instance_dict(value):
    if value is None:
        return {}
    try:
        result = object.__getattribute__(value, "__dict__")
    except (AttributeError, TypeError):
        return {}
    return result if type(result) is dict else {}


def _cache_rows(frame, kind):
    value = (frame.f_locals.get("opened") if kind == "legacy_open_eviction" else
             frame.f_locals.get("cache") if kind == "shared_eviction" else
             _instance_dict(frame.f_locals.get("self")).get("_rows"))
    return value if type(value) is dict else None


class Observer:
    """One diagnostic process; retain code objects and scalar summaries only."""
    def __init__(self, root, output, *, phases=None, cache_targets=None):
        self.root, self.output = Path(root).resolve(), Path(output).resolve()
        self.phases = PHASES if phases is None else phases
        self.cache_targets = CACHE_TARGETS if cache_targets is None else cache_targets
        self.targets, self.source_pins, self.missing = {}, {}, []
        self.codes, self.active, self.stats = {}, {}, {}
        self.valid, self.closed, self.tool = True, False, None
        self.events_written = 0
        self.callback_ns = self.callback_count = 0
        self.unmatched_unwind_events = 0
        self.started_ns = time.monotonic_ns()
        self.last_snapshot_ns = self.started_ns
        self.next_id = 0
        self.trace_stream = None
        self.output.mkdir(parents=True, exist_ok=False)
        self.fd = os.open(self.output / "observer.jsonl", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        modules = set(self.phases) | set(self.cache_targets)
        for module in sorted(modules):
            path = self.root / "src/data_sheets_schema" / (module.replace(".", "/") + ".py")
            names = set(self.phases.get(module, {})) | set(self.cache_targets.get(module, ()))
            if not path.is_file():
                self.missing.extend(f"{module}:{name}" for name in sorted(names))
                continue
            raw = path.read_bytes()
            self.source_pins[str(path)] = {"bytes": len(raw), "sha256": _sha(raw)}
            definitions = _definitions(ast.parse(raw, filename=str(path)))
            for name in sorted(names):
                node = definitions.get(name)
                if node is None:
                    self.missing.append(f"{module}:{name}")
                    continue
                cache = name in self.cache_targets.get(module, ())
                if isinstance(node, ast.AsyncFunctionDef) or any(
                        isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node)):
                    raise RuntimeError(f"observer target is not an ordinary function: {module}:{name}")
                target = {"id": f"{module}:{name}", "module": module, "qualname": name,
                          "phase": self.phases.get(module, {}).get(name), "cache": cache,
                          "firstlineno": min([node.lineno, *(d.lineno for d in node.decorator_list)]),
                          "source": str(path), "counter_sites": _counter_sites(node, name) if cache else {}}
                required = {"_bounded_json": {"warm_decode"},
                            "DerivationCache._derive": {"derive_lookup", "derive_decode"},
                            "DerivationCache._store": {"typed_eviction"},
                            "memo": {"shared_eviction", "shared_hit_decode", "shared_miss"}}
                if cache and not required.get(name, set()).issubset(set(target["counter_sites"].values())):
                    raise RuntimeError(f"counter source shape is not established: {module}:{name}")
                if cache and name == "_open":
                    markers = set(target["counter_sites"].values())
                    if {"open_lookup", "open_serialized_decode"}.issubset(markers):
                        target["cache_model"] = "shared_bounded_serialized_rows_with_json_decode_and_unblob"
                    elif {"open_lookup", "open_legacy_copy", "legacy_open_eviction"}.issubset(markers):
                        target["cache_model"] = "separate_legacy_opened_raw_tuple_cache"
                    else:
                        target["cache_model"] = "not_implemented_for_this_source_shape"
                self.targets[(str(path), name)] = target
                self.stats[target["id"]] = {"calls": 0, "returns": 0, "unwinds": 0,
                    "inclusive_wall_ns": 0, "inclusive_thread_cpu_ns": 0, "counters": {}}

    def _emit(self, event, **values):
        self.events_written += 1
        row = {"event": event, "sequence": self.events_written, "pid": os.getpid(),
               "elapsed_ns": time.monotonic_ns() - self.started_ns, **values}
        raw = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
        while raw:
            written = os.write(self.fd, raw)
            if written <= 0:
                raise OSError("diagnostic JSONL write made no progress")
            raw = raw[written:]

    def _origins(self):
        """No imports to populate this inventory; only naturally loaded modules."""
        rows = []
        package = self.root / "src/data_sheets_schema"
        for name, module in sorted(tuple(sys.modules.items())):
            if name != "data_sheets_schema" and not name.startswith("data_sheets_schema."):
                continue
            attrs = vars(module) if module is not None else {}
            path = attrs.get("__file__")
            row = {"name": name, "path": path}
            if path:
                selected = Path(path).resolve()
                row["within_selected_package"] = selected.is_relative_to(package)
                if selected.is_file():
                    row.update(_pin(selected))
                if not row["within_selected_package"]:
                    self.valid = False
            namespace = attrs.get("__path__")
            if namespace is not None:
                row["namespace"] = [str(p) for p in namespace]
                if any(not Path(p).resolve().is_relative_to(package) for p in namespace):
                    self.valid = False
            rows.append(row)
        return rows

    def start(self, *, arm_trace=True, configuration=None):
        if not hasattr(sys, "monitoring"):
            raise RuntimeError("recorder observer requires Python sys.monitoring (3.12+)")
        monitoring = sys.monitoring
        for candidate in (5, 4, 3, 2, 1, 0):
            if monitoring.get_tool(candidate) is None:
                monitoring.use_tool_id(candidate, "d4d-native-recorder-observer")
                self.tool = candidate
                break
        if self.tool is None:
            raise RuntimeError("no free sys.monitoring tool id; refusing to replace another observer")
        age = process_age()
        delay = max(0.001, 170 - age["seconds"])
        if arm_trace:
            self.trace_stream = (self.output / "stack-170s.txt").open("xb", buffering=0)
            # Source/origin hashes below may take time; arm before that work and
            # refresh the OS age after opening the output rather than reusing it.
            age = process_age()
            delay = max(0.001, 170 - age["seconds"])
            faulthandler.dump_traceback_later(delay, repeat=False, file=self.trace_stream, exit=False)
        self._emit("observer_start", helper=_pin(Path(__file__).resolve()), root=str(self.root),
                   python={"executable": sys.executable, "version": sys.version},
                   process_age=age, trace_after_seconds=delay, trace_target_process_age_seconds=170,
                   trace_enabled=arm_trace, origins=self._origins(), source_pins=self.source_pins,
                   configuration=configuration,
                   targets=list(self.targets.values()), absent_in_source=self.missing,
                   timings="inclusive nested wall and thread CPU; never sum nested wall timings",
                   counters="LINE entries are attempts; confirmed evictions require observed removal",
                   overhead="global PY_START until each unrelated location disables itself; global-only PY_UNWIND filtered by target code; local PY_RETURN/LINE only on listed targets")
        monitoring.register_callback(self.tool, monitoring.events.PY_START, self._start)
        monitoring.register_callback(self.tool, monitoring.events.PY_RETURN, self._returned)
        monitoring.register_callback(self.tool, monitoring.events.PY_UNWIND, self._unwound)
        monitoring.register_callback(self.tool, monitoring.events.LINE, self._line)
        monitoring.set_events(self.tool, monitoring.events.PY_START | monitoring.events.PY_UNWIND)
        atexit.register(self.close)
        return self

    def _failure(self, exc):
        self.valid = False
        # Diagnostic failures never replace a production result or skip a guard.
        if self.tool is not None:
            try:
                sys.monitoring.set_events(self.tool, 0)
            except BaseException:
                pass
            for code in tuple(self.codes):
                try:
                    sys.monitoring.set_local_events(self.tool, code, 0)
                except BaseException:
                    pass
        try:
            self._emit("observer_error", error_type=type(exc).__name__, detail="callback failed; measurement invalid")
        except BaseException:
            # This may be the same failed sink that caused the callback error.
            # No payload/exception string is copied to the production stream.
            try:
                os.write(2, b"d4d recorder observer failed; diagnostic evidence is incomplete\n")
            except BaseException:
                pass

    def _start(self, code, offset):
        tick = time.monotonic_ns()
        try:
            target = self.codes.get(code)
            if target is None:
                target = self.targets.get((code.co_filename, code.co_qualname))
                if target is None:
                    return sys.monitoring.DISABLE
                if code.co_firstlineno != target["firstlineno"]:
                    raise RuntimeError("loaded target does not match saved source definition")
                self.codes[code] = target
                # PY_UNWIND is not a local event (CPython monitoring.h/code.h).
                # Enabling it here raises ValueError before the first call starts.
                events = sys.monitoring.events.PY_RETURN
                if target["counter_sites"]:
                    events |= sys.monitoring.events.LINE
                sys.monitoring.set_local_events(self.tool, code, events)
            frame = sys._getframe(1)
            if frame.f_code is not code:
                raise RuntimeError("sys.monitoring start callback frame mismatch")
            key = (threading.get_ident(), id(frame))
            self.next_id += 1
            state = {"id": self.next_id, "target": target["id"], "wall": tick,
                     "cpu": time.thread_time_ns(), "pending_eviction": None}
            self.active[key] = state
            self.stats[target["id"]]["calls"] += 1
            if target["qualname"] == "DerivationCache._store":
                stored = frame.f_locals.get("key")
                product = (stored[0] if type(stored) is tuple and stored and
                           type(stored[0]) is str and stored[0] in ("open", "derive") else "unknown")
                self._inc(target, "store_product_" + product)
                encoded = frame.f_locals.get("encoded")
                if type(encoded) is bytes:
                    self._inc(target, "store_product_" + product + "_bytes", len(encoded))
            if target["qualname"] == "_base":
                self._inc(target, "catalog_argument_present" if frame.f_locals.get("_catalogs") is not None
                          else "catalog_argument_absent")
            if target["phase"] and self.stats[target["id"]]["calls"] <= MAX_PHASE_EVENTS_PER_TARGET:
                state["phase_logged"] = True
                self._emit("phase_start", call=state["id"], target=target["id"],
                           phase=target["phase"], thread=key[0])
            elif target["phase"]:
                self._inc(target, "phase_call_details_suppressed_at_bound")
        except Exception as exc:
            self._failure(exc)
        finally:
            self.callback_ns += time.monotonic_ns() - tick
            self.callback_count += 1

    def _inc(self, target, name, amount=1):
        counters = self.stats[target["id"]]["counters"]
        counters[name] = counters.get(name, 0) + amount

    def _confirm_eviction(self, target, state, frame):
        pending = state["pending_eviction"]
        if pending is None:
            return
        kind, before, product = pending
        rows = _cache_rows(frame, kind)
        if rows is not None and len(rows) == before - 1:
            self._inc(target, "evictions_confirmed")
            self._inc(target, "evicted_product_" + product)
        else:
            self._inc(target, "evictions_unconfirmed")
        state["pending_eviction"] = None

    def _line(self, code, lineno):
        tick = time.monotonic_ns()
        try:
            target = self.codes[code]
            frame = sys._getframe(1)
            if frame.f_code is not code:
                raise RuntimeError("sys.monitoring line callback frame mismatch")
            state = self.active[(threading.get_ident(), id(frame))]
            self._confirm_eviction(target, state, frame)
            if "decode_line" in state:
                previous, started = state.pop("decode_line")
                self._inc(target, previous + "_next_line_observed")
                self._inc(target, previous + "_to_next_line_ns", tick - started)
            marker = target["counter_sites"].get(lineno)
            if marker:
                self._inc(target, marker + "_entries")
            if marker in ("typed_eviction", "shared_eviction", "legacy_open_eviction"):
                rows = _cache_rows(frame, marker)
                if rows is None:
                    self._inc(target, "eviction_state_unavailable")
                else:
                    victim = next(iter(rows), None)
                    product = (victim[0] if type(victim) is tuple and victim and
                               type(victim[0]) is str and victim[0] in ("open", "derive") else
                               "legacy_open" if marker == "legacy_open_eviction" else
                               "legacy_derive" if target["qualname"] == "DerivationCache._derive" else "unknown")
                    state["pending_eviction"] = (marker, len(rows), product)
            elif marker == "derive_lookup":
                self._inc(target, "derive_misses" if frame.f_locals.get("encoded") is None else "derive_hits")
            elif marker == "open_lookup":
                self._inc(target, "open_misses" if frame.f_locals.get("hit") is None else "open_hits")
                raw = frame.f_locals.get("raw_packet")
                if type(raw) is bytes:
                    self._inc(target, "open_lookup_packet_bytes", len(raw))
            elif marker in ("warm_decode", "derive_decode", "shared_hit_decode", "open_serialized_decode", "open_legacy_copy"):
                raw = frame.f_locals.get("raw" if marker == "warm_decode" else
                                         "hit" if marker == "open_serialized_decode" else "encoded")
                if marker == "shared_hit_decode":
                    cache, key = frame.f_locals.get("cache"), frame.f_locals.get("key")
                    raw = cache.get(key) if type(cache) is dict else None
                if type(raw) is bytes:
                    self._inc(target, marker + "_input_bytes", len(raw))
                state["decode"] = (marker, tick)
                state["decode_line"] = (marker, tick)
            elif marker == "validated_set_clear":
                value = frame.f_globals.get("_VALIDATED_BOUNDED_BYTES")
                if type(value) is set:
                    self._inc(target, "validated_set_clear_entries_removed_if_success", len(value))
            if tick - self.last_snapshot_ns >= 1_000_000_000:
                self._snapshot("periodic")
        except Exception as exc:
            self._failure(exc)
        finally:
            self.callback_ns += time.monotonic_ns() - tick
            self.callback_count += 1

    def _end(self, code, frame, kind, value, tick):
        if frame.f_code is not code:
            raise RuntimeError("sys.monitoring end callback frame mismatch")
        target = self.codes[code]
        state = self.active.pop((threading.get_ident(), id(frame)))
        self._confirm_eviction(target, state, frame)
        wall, cpu = tick - state["wall"], time.thread_time_ns() - state["cpu"]
        stats = self.stats[target["id"]]
        stats[kind] += 1
        stats["inclusive_wall_ns"] += wall
        stats["inclusive_thread_cpu_ns"] += cpu
        if "decode" in state:
            marker, started = state["decode"]
            self._inc(target, marker + "_" + kind)
            self._inc(target, marker + "_through_function_end_ns", tick - started)
        if target["module"] == "native_catalog_reuse" and kind == "returns":
            label = ("runtime_token_none" if value is None else "runtime_token_ready"
                     if value is frame.f_globals.get("_READY") else "runtime_token_other")
            self._inc(target, label)
        if state.get("phase_logged"):
            self._emit("phase_end", call=state["id"], target=target["id"], phase=target["phase"],
                       outcome=kind, inclusive_wall_ns=wall, inclusive_thread_cpu_ns=cpu)
            if tick - self.last_snapshot_ns >= 1_000_000_000:
                self._snapshot("phase_end")

    def _returned(self, code, offset, value):
        tick = time.monotonic_ns()
        try:
            self._end(code, sys._getframe(1), "returns", value, tick)
        except Exception as exc:
            self._failure(exc)
        finally:
            self.callback_ns += time.monotonic_ns() - tick
            self.callback_count += 1

    def _unwound(self, code, offset, exception):
        tick = time.monotonic_ns()
        try:
            if code not in self.codes:
                self.unmatched_unwind_events += 1
                return  # Global-only exception event: do not return DISABLE.
            self._end(code, sys._getframe(1), "unwinds", None, tick)
        except Exception as exc:
            self._failure(exc)
        finally:
            self.callback_ns += time.monotonic_ns() - tick
            self.callback_count += 1

    def _snapshot(self, reason):
        self.last_snapshot_ns = time.monotonic_ns()
        self._emit("counter_snapshot", reason=reason, stats=self.stats,
                   active_calls=[{key: row[key] for key in ("id", "target", "wall")} for row in self.active.values()],
                   callback_count=self.callback_count, callback_body_ns=self.callback_ns,
                   unmatched_unwind_events=self.unmatched_unwind_events,
                   valid=self.valid)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.tool is not None:
            sys.monitoring.set_events(self.tool, 0)
            for code in self.codes:
                sys.monitoring.set_local_events(self.tool, code, 0)
            for event in (sys.monitoring.events.PY_START, sys.monitoring.events.PY_RETURN,
                          sys.monitoring.events.PY_UNWIND, sys.monitoring.events.LINE):
                sys.monitoring.register_callback(self.tool, event, None)
            sys.monitoring.free_tool_id(self.tool)
        if self.trace_stream is not None:
            faulthandler.cancel_dump_traceback_later()
            self.trace_stream.close()
        changed = [path for path, pin in self.source_pins.items()
                   if not Path(path).is_file() or _sha(Path(path).read_bytes()) != pin["sha256"]]
        if changed:
            self.valid = False
        origins = self._origins()
        self._snapshot("close")
        self._emit("observer_end", valid=self.valid, changed_sources=changed, origins=origins,
                   phases={name: ("not_reached" if stats["calls"] == 0 else
                                  "unfinished" if stats["calls"] > stats["returns"] + stats["unwinds"] else
                                  "observed_complete") for name, stats in self.stats.items()},
                   limitation="No end event after SIGKILL; retain incremental snapshots and stack. Timing overhead is not subtracted.")
        os.close(self.fd)


def install_from_config(root):
    """Diagnostic-only bootstrap, independent of the closed child environment."""
    if sys.argv[1:3] != ["provenance", "record"]:
        return None
    root = Path(root).resolve()
    config = root / "scripts/adhoc" / CONFIG_NAME
    raw = config.read_bytes()
    if raw != CONFIG_BYTES:
        raise RuntimeError("diagnostic observer config must equal the paired committed bytes")
    parent = Path(json.loads(raw)["output_parent"])
    output = parent / f"recorder-{os.getpid()}-{time.time_ns()}"
    return Observer(root, output).start(configuration=_pin(config))
