# Purpose: opt-in pass-through attribution of the unchanged long pipeline test.
# Inputs: exact test node, owned checkout, --d4d-profile-output external path.
# Outputs: JSON events, source pins, phase outcomes and restoration diagnostics.
# Issue: bridge2ai/data-sheets-schema#5015; no PR yet. Date: 2026-10-12.
# Migration: header only; see MIGRATION.md for original source and path setup.
"""Opt-in pass-through profiling of one real shared-generation pipeline test."""
from __future__ import annotations

import atexit
import functools
import hashlib
import importlib
import json
import os
from pathlib import Path
import resource
import sys
import threading
import time

import pytest

NODE = "tests/test_shared_generation_runtime.py::test_real_complete_api_pipeline_and_completed_recheck"
TARGETS = {
    "api_runner": ("execute", "_validator_lines", "validate_outputs"),
    "schema_sync": ("check",),
    "shared_generation": ("capture", "assert_current"),
    "typed_audit_runtime": ("prepare_packet", "_rebuild", "completion_check"),
    "typed_audit": ("DerivationCache._derive", "_derive_uncached", "check"),
    "audit_omissions": ("_schema",),
    "schema_view": ("version_document",),
}


def pytest_addoption(parser):
    group = parser.getgroup("d4d-target-profile")
    group.addoption("--d4d-profile-output", help="New external JSON output; enables this one-node profiler")


class Profile:
    def __init__(self, output, root):
        self.output, self.root = output, root
        self.events, self.originals, self.sources, self.errors = [], [], [], []
        self.phases, self.imports = [], []
        self.local = threading.local()
        self.counter = 0
        self.lock = threading.Lock()
        self.restored = False
        self.session_exit = None

    def save(self):
        try:
            payload = {
                "kind": "d4d_single_node_passthrough_profile_v1", "nodeid": NODE,
                "root": str(self.root), "executable": sys.executable,
                "python": sys.version, "argv": sys.argv, "sys_path": list(sys.path),
                "pid": os.getpid(), "session_exit": self.session_exit,
                "restored": self.restored, "sources": self.sources,
                "imports_before_setup": self.imports, "phases": self.phases,
                "events": self.events, "errors": self.errors,
                "limits": ["Instrumented attribution, not an uninstrumented speed measurement",
                           "Thread CPU excludes child CPU; nested inclusive times overlap",
                           "Exclusive time subtracts only instrumented descendants",
                           "Child CPU deltas are process-wide reaped-child counters",
                           "Graceful pytest/atexit persistence only; SIGKILL cannot be handled"],
            }
            temporary = self.output.with_name(self.output.name + ".tmp")
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2)
                stream.write("\n")
            os.replace(temporary, self.output)
        except Exception as exc:
            self.errors.append({"stage": "save", "exception": type(exc).__name__, "message": str(exc)})

    def restore(self):
        if self.restored:
            return
        for owner, name, original, wrapper in reversed(self.originals):
            try:
                current = getattr(owner, name)
                if current is wrapper:
                    setattr(owner, name, original)
                elif current is not original:
                    self.errors.append({"stage": "restore", "name": name,
                                        "message": "binding changed by another owner; left intact"})
            except Exception as exc:
                self.errors.append({"stage": "restore", "name": name,
                                    "exception": type(exc).__name__})
        self.restored = not any(error["stage"] == "restore" for error in self.errors)

    def finish(self):
        try:
            self.restore()
        finally:
            self.save()

    @staticmethod
    def caller():
        frame = sys._getframe(2)
        try:
            while frame:
                if Path(frame.f_code.co_filename).name in {
                    "test_shared_generation_runtime.py", "test_shared_generation_completed_replay.py"
                }:
                    values = {key: value for key in ("mutation", "change", "case")
                              if type(value := frame.f_locals.get(key)) is str}
                    return {"function": frame.f_code.co_name, "line": frame.f_lineno, **values}
                frame = frame.f_back
            return None
        finally:
            del frame

    def wrap(self, owner, name, label):
        original = getattr(owner, name)

        @functools.wraps(original)
        def measured(*args, **kwargs):
            stack, event = None, None
            try:
                stack = getattr(self.local, "stack", None)
                if stack is None:
                    stack = self.local.stack = []
                with self.lock:
                    self.counter += 1
                    ordinal = self.counter
                event = {"id": ordinal, "parent": stack[-1]["id"] if stack else None,
                         "function": label, "thread": threading.get_ident(),
                         "child_wall_ns": 0, "child_thread_ns": 0, "exception": None}
                if label == "api_runner.execute":
                    event["caller"] = self.caller()
                child_before = resource.getrusage(resource.RUSAGE_CHILDREN) if label == "api_runner._validator_lines" else None
                wall, cpu = time.perf_counter_ns(), time.thread_time_ns()
                stack.append(event)
            except Exception as exc:
                if stack and stack[-1] is event:
                    stack.pop()
                event = None
                self.errors.append({"stage": "event_start", "function": label, "exception": type(exc).__name__})
            try:
                return original(*args, **kwargs)
            except BaseException as exc:
                if event is not None:
                    event["exception"] = type(exc).__name__
                raise
            finally:
                if event is not None:
                    try:
                        end_wall, end_cpu = time.perf_counter_ns(), time.thread_time_ns()
                        stack.pop()
                        event["wall_ns"], event["thread_ns"] = end_wall - wall, end_cpu - cpu
                        event["exclusive_wall_ns"] = event["wall_ns"] - event.pop("child_wall_ns")
                        event["exclusive_thread_ns"] = event["thread_ns"] - event.pop("child_thread_ns")
                        if child_before is not None:
                            after = resource.getrusage(resource.RUSAGE_CHILDREN)
                            event["reaped_child_user_s"] = after.ru_utime - child_before.ru_utime
                            event["reaped_child_system_s"] = after.ru_stime - child_before.ru_stime
                        if stack:
                            stack[-1]["child_wall_ns"] += event["wall_ns"]
                            stack[-1]["child_thread_ns"] += event["thread_ns"]
                        with self.lock:
                            self.events.append(event)
                    except Exception as exc:
                        if stack and stack[-1] is event:
                            stack.pop()
                        self.errors.append({"stage": "event_end", "function": label, "exception": type(exc).__name__})

        setattr(owner, name, measured)
        self.originals.append((owner, name, original, measured))

    def install(self):
        for suffix, names in TARGETS.items():
            qualified = "data_sheets_schema." + suffix
            already_loaded = qualified in sys.modules
            start = time.perf_counter_ns()
            module = importlib.import_module(qualified)
            self.imports.append({"module": qualified, "already_loaded": already_loaded,
                                 "wall_ns": time.perf_counter_ns() - start})
            source = Path(module.__file__).resolve()
            if not source.is_relative_to(self.root / "src/data_sheets_schema"):
                raise pytest.UsageError(f"profiling target loaded from wrong source: {source}")
            raw = source.read_bytes()
            self.sources.append({"module": qualified, "path": str(source), "bytes": len(raw),
                                 "sha256": hashlib.sha256(raw).hexdigest()})
            for name in names:
                label = suffix + "." + name
                owner = module
                if "." in name:
                    parent, name = name.split(".", 1)
                    owner = getattr(module, parent)
                self.wrap(owner, name, label)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    destination = config.getoption("--d4d-profile-output")
    if destination is None:
        return
    if hasattr(config, "workerinput") or config.getoption("numprocesses", default=0):
        raise pytest.UsageError("target profiling requires serial execution (-n0)")
    if [item.nodeid for item in items] != [NODE]:
        raise pytest.UsageError("target profiling requires exactly the designated pipeline node")
    root = Path(config.rootpath).resolve()
    output = Path(destination).resolve()
    if output.is_relative_to(root):
        raise pytest.UsageError("profile output must be external to the checkout")
    if (not output.parent.is_dir() or os.path.lexists(output)
            or os.path.lexists(output.with_name(output.name + ".tmp"))):
        raise pytest.UsageError("profile output requires an existing external parent and fresh output names")
    state = config._d4d_target_profile = Profile(output, root)
    atexit.register(state.finish)
    try:
        state.install()
    except BaseException:
        state.finish()
        raise
    state.save()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    state = getattr(item.config, "_d4d_target_profile", None)
    if state is not None:
        report = outcome.get_result()
        state.phases.append({"when": report.when, "outcome": report.outcome, "duration": report.duration})
        state.save()


def pytest_sessionfinish(session, exitstatus):
    state = getattr(session.config, "_d4d_target_profile", None)
    if state is not None:
        state.session_exit = int(exitstatus)
        state.finish()


def pytest_unconfigure(config):
    state = getattr(config, "_d4d_target_profile", None)
    if state is not None:
        state.finish()
