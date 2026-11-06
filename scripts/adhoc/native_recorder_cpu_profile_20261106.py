#!/usr/bin/env python3
"""CPU checkpoints for the U0 recorder diagnostic, #4354, 2026-11-06.

Inputs: one diagnostic source root and the exact adjacent configuration below.
Outputs: an exclusive external recorder directory, Observer JSONL, CPU-timed
pstats snapshots, getrusage phase deltas and the inherited 170s watchdog stack.
No production callable is replaced and no provider or native binary is invoked.
This is intrusive diagnostic instrumentation, never baseline timing evidence.
"""
from __future__ import annotations

import cProfile
import hashlib
import importlib.util
import json
import marshal
import os
from pathlib import Path
import resource
import sys
import threading
import time


_base_path = Path(__file__).with_name("native_recorder_observer_20261026.py")
_spec = importlib.util.spec_from_file_location("native_recorder_cpu_observer_base", _base_path)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

CONFIG_NAME = "native_recorder_cpu_profile_20261106.config.json"
CONFIG_BYTES = b'{"output_parent":"/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-u0-20261106/cpu-observer-output"}\n'
BOOTSTRAP = '''# Diagnostic-only CPU observer; never install in baseline sources.
import sys as _recorder_cpu_sys
if _recorder_cpu_sys.argv[1:3] == ["provenance", "record"]:
    import runpy as _recorder_cpu_runpy
    from pathlib import Path as _recorder_cpu_Path
    _recorder_cpu_root = _recorder_cpu_Path(__file__).resolve().parents[3]
    _recorder_cpu_runpy.run_path(str(
        _recorder_cpu_root / "scripts/adhoc/native_recorder_cpu_profile_20261106.py"
    ))["install_from_config"](_recorder_cpu_root)
'''

PHASES = {module: dict(names) for module, names in base.PHASES.items()}
for _module, _names in {
    "provenance": {"build_record": "record_construction"},
    "cli.provenance": {"_recorded_receipt_origin": "receipt_origin_readback"},
    "receipt_origin": {"origin": "receipt_origin", "origin_captured": "receipt_origin_captured"},
    "native_shared_capture": {"_document": "native_document_decode", "phase_replay": "native_phase_replay"},
    "record_schema": {"compile_record_schema": "record_schema_compile",
                      "_compile_record_schema": "record_schema_compile_uncached"},
    "native_shared_receipts": {"_ReceiptCatalogContext.catalog": "receipt_catalog",
                               "_ReceiptCatalogContext._typed_catalog": "typed_receipt_catalog"},
    "audit_omissions": {"_schema_with_root_bases": "omission_schema_roots",
                        "_schema_product": "omission_schema_product"},
    "schema_snapshot": {"capture_schema": "schema_snapshot"},
}.items():
    PHASES.setdefault(_module, {}).update(_names)

# The phase observer deliberately accepts ordinary functions only. These real
# 01969cbed targets yield; cProfile retains their frames without phase wrapping.
# Generator call counts can represent resumptions, not distinct invocations.
GENERATOR_PROFILE_ONLY = ("schema_view:captured_view",
                          "record_schema:RecordValidationPlugin.process")

RUSAGE_FIELDS = ("ru_utime", "ru_stime", "ru_minflt", "ru_majflt", "ru_inblock",
                 "ru_oublock", "ru_nvcsw", "ru_nivcsw")
BOUNDARY_TARGETS = frozenset({
    "cli.provenance:record", "cli.provenance:_inline_checks",
    "provenance:ProvenanceRecord.write", "provenance:check_record",
    "backfill_checks:compute", "backfill_checks:apply",
    "native_shared_capture:_recorded_run",
})
BOUNDARY_INTERVAL_NS = 5_000_000_000


def usage():
    """Process-wide CPU/counters; ru_maxrss is a peak, not current resident size."""
    value = resource.getrusage(resource.RUSAGE_SELF)
    return {**{key: getattr(value, key) for key in RUSAGE_FIELDS},
            "max_rss_bytes": value.ru_maxrss * (1 if sys.platform == "darwin" else 1024),
            "monotonic_ns": time.monotonic_ns(), "process_cpu_ns": time.process_time_ns()}


def usage_delta(before, after):
    return {**{key: after[key] - before[key] for key in RUSAGE_FIELDS},
            "wall_ns": after["monotonic_ns"] - before["monotonic_ns"],
            "process_cpu_ns": after["process_cpu_ns"] - before["process_cpu_ns"],
            "max_rss_bytes": after["max_rss_bytes"],
            "peak_rss_growth_bytes": after["max_rss_bytes"] - before["max_rss_bytes"]}


def _label(code):
    return ("~", 0, code) if isinstance(code, str) else (code.co_filename, code.co_firstlineno, code.co_name)


def pstats_mapping(entries):
    """Translate the copied getstats entries without disabling the live profiler.

    cProfile.dump_stats/create_stats call disable(); they must not be called by
    the checkpoint thread. getstats copies C profiler entries while holding the
    CPython GIL. The resulting Python records can safely be serialized later.
    """
    stats, callers_by_code = {}, {}
    for entry in entries:
        callers = {}
        stats[_label(entry.code)] = (entry.callcount - entry.reccallcount, entry.callcount,
                                    entry.inlinetime, entry.totaltime, callers)
        callers_by_code[id(entry.code)] = callers
    for entry in entries:
        caller = _label(entry.code)
        for subentry in entry.calls or ():
            callers = callers_by_code.get(id(subentry.code))
            if callers is None:
                continue
            value = (subentry.callcount, subentry.callcount - subentry.reccallcount,
                     subentry.inlinetime, subentry.totaltime)
            previous = callers.get(caller, (0, 0, 0.0, 0.0))
            callers[caller] = tuple(a + b for a, b in zip(previous, value))
    return stats


class CPUObserver(base.Observer):
    """The existing phase/counter observer plus CPU-timed, durable checkpoints."""

    def __init__(self, root, output, *, phases=None, cache_targets=None,
                 checkpoint_seconds=5.0, milestone_ages=(150.0, 170.0)):
        if checkpoint_seconds <= 0 or not milestone_ages or any(age < 0 for age in milestone_ages):
            raise ValueError("positive checkpoint interval and nonnegative milestone ages required")
        self._cpu_lock = threading.RLock()
        self._stop = threading.Event()
        self._checkpoint_thread = None
        self._profile = cProfile.Profile(timer=time.process_time)
        self._profile_enabled = False
        self._owner_thread = None
        self._phase_usage = {}
        self._last_boundary_checkpoint_ns = None
        self.checkpoint_seconds = checkpoint_seconds
        self.milestone_ages = tuple(sorted(set(milestone_ages)))
        self.completed_milestones = set()
        self.checkpoint_count = 0
        self.checkpoint_wall_ns = self.checkpoint_cpu_ns = 0
        self._age_at_start = None
        super().__init__(root, output, phases=PHASES if phases is None else phases,
                         cache_targets=cache_targets)

    def _emit(self, event, **values):
        with self._cpu_lock:
            if event == "phase_start":
                current = usage()
                self._phase_usage[values["call"]] = {
                    "call": values["call"], "target": values["target"],
                    "phase": values["phase"], "thread": values["thread"], "started": current}
                values["process_rusage_enter"] = current
            elif event == "phase_end":
                previous = self._phase_usage.pop(values["call"], None)
                current = usage()
                values["process_rusage_exit"] = current
                if previous is not None:
                    values["inclusive_process_rusage_delta"] = usage_delta(previous["started"], current)
            super()._emit(event, **values)
            if (event in ("phase_start", "phase_end") and self._profile_enabled
                    and values["target"] in BOUNDARY_TARGETS):
                tick = time.monotonic_ns()
                force = values["target"] == "cli.provenance:record"
                if (force or self._last_boundary_checkpoint_ns is None
                        or tick - self._last_boundary_checkpoint_ns >= BOUNDARY_INTERVAL_NS):
                    # Phase rusage remains detailed. Full profiles cover only
                    # major boundaries, at most once per five seconds except
                    # entry/exit of the outer recorder, plus periodic saves.
                    self.checkpoint(event, "profile-phase-boundary.prof", rolling=True)
                    self._last_boundary_checkpoint_ns = time.monotonic_ns()

    def _atomic(self, filename, raw):
        if Path(filename).name != filename or not filename or filename.startswith("."):
            raise ValueError("checkpoint name must be one plain path component")
        destination = self.output / filename
        temporary = self.output / ("." + filename + "." + str(self.checkpoint_count) + ".tmp")
        with temporary.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        return {"path": str(destination), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

    def process_age_now(self):
        if self._age_at_start is None:
            return base.process_age()["seconds"]
        return self._age_at_start + (time.monotonic_ns() - self._age_clock_ns) / 1_000_000_000

    def checkpoint(self, reason, filename="profile-latest.prof", *, rolling=True):
        """Save a parseable partial profile even while a selected phase is active."""
        with self._cpu_lock:
            if self.closed:
                return None
            started_wall, started_cpu = time.monotonic_ns(), time.thread_time_ns()
            self.checkpoint_count += 1
            sampled = usage()
            # getstats itself holds the GIL; no disable()/enable() on this thread.
            entries = self._profile.getstats()
            raw = marshal.dumps(pstats_mapping(entries))
            artifact = self._atomic(filename, raw)
            current = {"reason": reason, "checkpoint": self.checkpoint_count,
                "profile": artifact, "rolling_artifact": rolling,
                "process_age_seconds": self.process_age_now(), "rusage": sampled,
                "active_phases": [{key: value for key, value in row.items() if key != "started"}
                    | {"inclusive_process_rusage_delta": usage_delta(row["started"], sampled)}
                    for row in self._phase_usage.values()],
                "profile_timer": "time.process_time", "profiled_thread": self._owner_thread,
                "scope": "profiled recorder thread; CPU clock includes all process threads; active frames may be incomplete",
                "limitation": "nested deltas are inclusive/non-additive; profiler, checkpoint I/O and observer overhead are not subtracted"}
            self._atomic(filename + ".json", (json.dumps(current, sort_keys=True) + "\n").encode())
            self.checkpoint_wall_ns += time.monotonic_ns() - started_wall
            self.checkpoint_cpu_ns += time.thread_time_ns() - started_cpu
            super()._emit("cpu_profile_checkpoint", **current,
                checkpoint_body_wall_ns=self.checkpoint_wall_ns,
                checkpoint_thread_cpu_ns=self.checkpoint_cpu_ns)
            os.fsync(self.fd)
            return current

    def _snapshot(self, reason):
        with self._cpu_lock:
            # The base snapshot references mutable counters. Serialize while the
            # same lock protects this subclass's emit/checkpoint observations.
            super()._snapshot(reason)
            current = usage()
            super()._emit("process_rusage_snapshot", reason=reason, rusage=current,
                active_phases=[{"call": row["call"], "target": row["target"],
                    "phase": row["phase"], "inclusive_process_rusage_delta": usage_delta(row["started"], current)}
                    for row in self._phase_usage.values()])

    def _due_checkpoints(self):
        age = self.process_age_now()
        for target in self.milestone_ages:
            if target not in self.completed_milestones and age >= target:
                self.checkpoint("process_age_milestone", f"profile-age-{target:g}s.prof", rolling=False)
                self.completed_milestones.add(target)
        self.checkpoint("periodic")

    def _periodic(self):
        while not self._stop.wait(self.checkpoint_seconds):
            try:
                self._due_checkpoints()
            except Exception as exc:
                self._failure(exc)
                self._stop.set()

    def start(self, *, arm_trace=True, configuration=None, background=True):
        if sys.implementation.name != "cpython" or (hasattr(sys, "_is_gil_enabled") and not sys._is_gil_enabled()):
            raise RuntimeError("CPU checkpoints require GIL-enabled CPython")
        if sys.getprofile() is not None:
            raise RuntimeError("existing profiler present; refusing to replace it")
        self._owner_thread = threading.get_ident()
        self._age_at_start = base.process_age()["seconds"]
        self._age_clock_ns = time.monotonic_ns()
        super().start(arm_trace=arm_trace, configuration=configuration)
        self._profile.enable()
        self._profile_enabled = True
        self._emit("cpu_profile_start", helper=base._pin(Path(__file__).resolve()),
            parent_helper=base._pin(_base_path), timer="time.process_time",
            periodic_seconds=self.checkpoint_seconds, milestone_process_ages=self.milestone_ages,
            boundary_targets=sorted(BOUNDARY_TARGETS), boundary_throttle_seconds=5,
            generator_profile_only=GENERATOR_PROFILE_ONLY,
            generator_counts="cProfile generator call counts may count resumptions; no ordinary-function phase timing is claimed",
            rusage_scope="RUSAGE_SELF includes checkpoint thread; max RSS is a peak, not current RSS",
            limitation="diagnostic overhead; inclusive nested phases cannot be summed; Python checkpoints can be delayed by a held GIL; inherited faulthandler watchdog targets age 170s",
            unobserved="parent-process native_shared_execution.read_final/native_execution_engine.read_final are outside this recorder-only bootstrap")
        self.checkpoint("initial", "profile-initial.prof", rolling=False)
        self._due_checkpoints()  # Retain already-due age checkpoints at installation.
        if background:
            self._checkpoint_thread = threading.Thread(target=self._periodic,
                name="d4d-recorder-cpu-checkpoints", daemon=True)
            self._checkpoint_thread.start()
        return self

    def close(self):
        if self.closed:
            return
        self._stop.set()
        thread = self._checkpoint_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
            if thread.is_alive():
                self.valid = False
                # Never close a sink still used by a checkpoint thread.
                return
        if self._profile_enabled:
            if threading.get_ident() != self._owner_thread:
                self.valid = False
                return
            self._profile.disable()
            self._profile_enabled = False
        try:
            self.checkpoint("final", "profile-final.prof", rolling=False)
        except Exception as exc:
            self._failure(exc)
        with self._cpu_lock:
            super().close()


def install_from_config(root):
    """Activate only the recorder, with byte-exact fixed external destination."""
    if sys.argv[1:3] != ["provenance", "record"]:
        return None
    root = Path(root).resolve()
    config = root / "scripts/adhoc" / CONFIG_NAME
    raw = config.read_bytes()
    if raw != CONFIG_BYTES:
        raise RuntimeError("CPU observer config must equal the declared canonical bytes")
    parent = Path(json.loads(raw)["output_parent"])
    if not parent.is_dir() or parent.resolve(strict=True) != parent or parent.is_relative_to(root):
        raise RuntimeError("CPU observer parent must be an existing exact external directory")
    output = parent / f"recorder-{os.getpid()}-{time.time_ns()}"
    return CPUObserver(root, output).start(configuration=base._pin(config))
