"""Synthetic CPU-profile diagnostics for U0/#4354, 2026-11-06.

No native/provider execution. Inputs are small saved functions; outputs are
temporary pstats/JSONL checkpoints. Production return/refusal behavior survives.
"""
import importlib.util
import json
from pathlib import Path
import pstats
import sys
import threading

import pytest


HELPER = Path(__file__).resolve().parents[1] / "scripts/adhoc/native_recorder_cpu_profile_20261106.py"
spec = importlib.util.spec_from_file_location("native_recorder_cpu_profile_fixture", HELPER)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def synthetic(tmp_path):
    path = tmp_path / "src/data_sheets_schema/provenance.py"
    path.parent.mkdir(parents=True)
    source = '''
def leaf(size):
    total = 0
    for value in range(size):
        total += (value * value) % 97
    return total

def check_record(size, checkpoint=None, refuse=False):
    result = sum(leaf(size) for _ in range(3))
    if checkpoint is not None:
        checkpoint()
    if refuse:
        raise ValueError("private refusal remains intact")
    return result

class Catalog:
    def catalog(self):
        return 17
'''
    path.write_text(source)
    namespace = {"__name__": "data_sheets_schema.provenance", "__file__": str(path)}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace


def make_observer(tmp_path, monkeypatch, **kwargs):
    if not hasattr(sys, "monitoring"):
        pytest.skip("requires Python 3.12+ sys.monitoring")
    result = profile.CPUObserver(tmp_path, tmp_path / "cpu-evidence",
        phases={"provenance": {"check_record": "record_validation"}}, cache_targets={}, **kwargs)
    monkeypatch.setattr(result, "_origins", lambda: [])
    return result


def events(seen):
    return [json.loads(line) for line in (seen.output / "observer.jsonl").read_text().splitlines()]


def test_cpu_pstats_counts_partial_checkpoint_and_refusal_are_preserved(tmp_path, monkeypatch):
    ns = synthetic(tmp_path)
    seen = make_observer(tmp_path, monkeypatch)
    original = ns["check_record"]
    before_tools = [sys.monitoring.get_tool(i) for i in range(6)]
    try:
        seen.start(arm_trace=False, background=False)
        expected = sum((value * value) % 97 for value in range(2000)) * 3
        assert ns["check_record"](2000, lambda: seen.checkpoint("test-active", "partial.prof", rolling=False)) == expected
        with pytest.raises(ValueError, match="private refusal remains intact"):
            ns["check_record"](500, refuse=True)
    finally:
        seen.close()
    assert seen.valid and ns["check_record"] is original and not seen._phase_usage
    assert [sys.monitoring.get_tool(i) for i in range(6)] == before_tools
    final = pstats.Stats(str(seen.output / "profile-final.prof"))
    leaf = [value for key, value in final.stats.items() if key[2] == "leaf"]
    assert len(leaf) == 1 and leaf[0][0:2] == (6, 6) and leaf[0][2] > 0
    partial = pstats.Stats(str(seen.output / "partial.prof"))
    assert any(key[2] == "leaf" and value[1] == 3 for key, value in partial.stats.items())
    rows = events(seen)
    checkpoint = next(row for row in rows if row["event"] == "cpu_profile_checkpoint" and row["reason"] == "test-active")
    assert checkpoint["profile_timer"] == "time.process_time"
    active = checkpoint["active_phases"]
    assert len(active) == 1 and active[0]["phase"] == "record_validation"
    assert active[0]["inclusive_process_rusage_delta"]["process_cpu_ns"] > 0
    ended = [row for row in rows if row["event"] == "phase_end"]
    assert [row["outcome"] for row in ended] == ["returns", "unwinds"]
    assert all(row["inclusive_process_rusage_delta"]["ru_utime"] >= 0 for row in ended)
    assert "private refusal" not in (seen.output / "observer.jsonl").read_text()
    assert (seen.output / "profile-phase-boundary.prof").stat().st_size > 0
    assert not list(seen.output.glob("*.tmp"))


def test_periodic_checkpoint_does_not_disable_main_profiler_and_thread_stops(tmp_path, monkeypatch):
    ns = synthetic(tmp_path)
    seen = make_observer(tmp_path, monkeypatch, checkpoint_seconds=0.01)
    completed = threading.Event()
    checkpoint_threads = []
    original = seen._due_checkpoints
    def tick():
        original()
        checkpoint_threads.append(threading.get_ident())
        completed.set()
    monkeypatch.setattr(seen, "_due_checkpoints", tick)
    try:
        seen.start(arm_trace=False)
        completed.clear()
        checkpoint_threads.clear()
        ns["check_record"](1000)
        assert completed.wait(timeout=2)
        assert seen._checkpoint_thread.ident in checkpoint_threads
        ns["check_record"](1000)
    finally:
        seen.close()
    assert seen.valid and not seen._checkpoint_thread.is_alive()
    stats = pstats.Stats(str(seen.output / "profile-final.prof")).stats
    assert next(value[1] for key, value in stats.items() if key[2] == "leaf") == 6
    assert any(row["event"] == "cpu_profile_checkpoint" and row["reason"] == "periodic" for row in events(seen))


def test_repeated_catalog_phases_keep_rusage_without_full_profile_per_call(tmp_path, monkeypatch):
    ns = synthetic(tmp_path)
    if not hasattr(sys, "monitoring"):
        pytest.skip("requires Python 3.12+ sys.monitoring")
    seen = profile.CPUObserver(tmp_path, tmp_path / "cpu-evidence",
        phases={"provenance": {"Catalog.catalog": "receipt_catalog"}}, cache_targets={})
    monkeypatch.setattr(seen, "_origins", lambda: [])
    try:
        seen.start(arm_trace=False, background=False)
        count = seen.checkpoint_count
        catalog = ns["Catalog"]()
        for _ in range(50):
            assert catalog.catalog() == 17
        assert seen.checkpoint_count == count
    finally:
        seen.close()
    rows = [row for row in events(seen) if row["event"] == "phase_end"]
    assert len(rows) == 50
    assert all("inclusive_process_rusage_delta" in row for row in rows)


def test_major_boundary_profiles_are_throttled(tmp_path, monkeypatch):
    ns = synthetic(tmp_path)
    seen = make_observer(tmp_path, monkeypatch)
    try:
        seen.start(arm_trace=False, background=False)
        count = seen.checkpoint_count
        for _ in range(20):
            ns["check_record"](10)
        assert seen.checkpoint_count == count + 1
    finally:
        seen.close()


def test_profile_constructor_uses_process_cpu_timer(tmp_path, monkeypatch):
    synthetic(tmp_path)
    constructor = profile.cProfile.Profile
    calls = []
    def recorded(*args, **kwargs):
        calls.append(kwargs)
        return constructor(*args, **kwargs)
    monkeypatch.setattr(profile.cProfile, "Profile", recorded)
    seen = make_observer(tmp_path, monkeypatch)
    seen.close()
    assert calls == [{"timer": profile.time.process_time}]


def test_milestones_are_process_age_bound_and_retained_once(tmp_path, monkeypatch):
    synthetic(tmp_path)
    seen = make_observer(tmp_path, monkeypatch)
    age = [149.0]
    monkeypatch.setattr(seen, "process_age_now", lambda: age[0])
    try:
        seen.start(arm_trace=False, background=False)
        seen._due_checkpoints()
        assert not (seen.output / "profile-age-150s.prof").exists()
        age[0] = 151.0
        seen._due_checkpoints()
        first = (seen.output / "profile-age-150s.prof").read_bytes()
        age[0] = 171.0
        seen._due_checkpoints()
        assert (seen.output / "profile-age-150s.prof").read_bytes() == first
        assert (seen.output / "profile-age-170s.prof").stat().st_size > 0
        assert seen.completed_milestones == {150.0, 170.0}
    finally:
        seen.close()


def test_checkpoint_failure_marks_diagnostic_invalid_without_swallowing_refusal(tmp_path, monkeypatch):
    ns = synthetic(tmp_path)
    seen = make_observer(tmp_path, monkeypatch)
    seen.start(arm_trace=False, background=False)
    def broken(*unused, **kwargs):
        raise OSError("private output failure")
    monkeypatch.setattr(seen, "_atomic", broken)
    try:
        with pytest.raises(ValueError, match="private refusal remains intact"):
            ns["check_record"](50, refuse=True)
    finally:
        seen.close()
    assert not seen.valid
    assert "private output failure" not in (seen.output / "observer.jsonl").read_text()


def test_existing_profiler_is_not_replaced(tmp_path, monkeypatch):
    synthetic(tmp_path)
    seen = make_observer(tmp_path, monkeypatch)
    existing = lambda *args: None
    monkeypatch.setattr(profile.sys, "getprofile", lambda: existing)
    with pytest.raises(RuntimeError, match="existing profiler"):
        seen.start(arm_trace=False, background=False)
    seen.close()


def test_installer_ignores_non_recorder_and_requires_canonical_config(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["d4d", "receipts", "derive"])
    assert profile.install_from_config(tmp_path) is None
    monkeypatch.setattr(sys, "argv", ["d4d", "provenance", "record"])
    config = tmp_path / "scripts/adhoc" / profile.CONFIG_NAME
    config.parent.mkdir(parents=True)
    config.write_bytes(profile.CONFIG_BYTES + b" ")
    with pytest.raises(RuntimeError, match="canonical bytes"):
        profile.install_from_config(tmp_path)


def test_usage_delta_labels_peak_rss_and_inclusive_cpu():
    before = {key: 1 for key in profile.RUSAGE_FIELDS} | {
        "max_rss_bytes": 100, "monotonic_ns": 100, "process_cpu_ns": 10}
    after = {key: 3 for key in profile.RUSAGE_FIELDS} | {
        "max_rss_bytes": 140, "monotonic_ns": 180, "process_cpu_ns": 50}
    delta = profile.usage_delta(before, after)
    assert delta["max_rss_bytes"] == 140 and delta["peak_rss_growth_bytes"] == 40
    assert delta["wall_ns"] == 80 and delta["process_cpu_ns"] == 40


def test_bootstrap_is_narrow_and_fixed_destination_is_external():
    assert '["provenance", "record"]' in profile.BOOTSTRAP
    assert "native_recorder_cpu_profile_20261106.py" in profile.BOOTSTRAP
    assert json.loads(profile.CONFIG_BYTES)["output_parent"].endswith("/native-u0-20261106/cpu-observer-output")


def test_default_phase_roster_leaves_real_generator_shapes_to_cprofile(tmp_path, monkeypatch):
    package = tmp_path / "src/data_sheets_schema"
    package.mkdir(parents=True)
    (package / "schema_view.py").write_text("def captured_view():\n    yield None\n")
    (package / "record_schema.py").write_text(
        "class RecordValidationPlugin:\n    def process(self):\n        yield None\n\n"
        "def compile_record_schema():\n    return {}\n")
    assert "captured_view" not in profile.PHASES.get("schema_view", {})
    assert "RecordValidationPlugin.process" not in profile.PHASES["record_schema"]
    # This constructor used to reject both real generator shapes before any
    # recorder work could run; the ordinary compile phase remains observed.
    seen = profile.CPUObserver(tmp_path, tmp_path / "cpu-evidence")
    monkeypatch.setattr(seen, "_origins", lambda: [])
    try:
        targets = {row["id"] for row in seen.targets.values()}
        assert "record_schema:compile_record_schema" in targets
        assert not set(profile.GENERATOR_PROFILE_ONLY) & targets
    finally:
        seen.close()
