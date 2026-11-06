"""Real sys.monitoring event/frame and cache-observation fixtures for N2, 2026-10-26.

Inputs: synthetic saved Python source, never production imports or provider calls.
Outputs: temporary diagnostic JSONL; validates the observer before timed trials.
Refs #4354. No production callable is wrapped or replaced by these tests.
"""
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest


HELPER = Path(__file__).resolve().parents[1] / "scripts/adhoc/native_recorder_observer_20261026.py"
spec = importlib.util.spec_from_file_location("native_recorder_observer_fixture", HELPER)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


def saved_module(tmp_path, name, source):
    path = tmp_path / "src/data_sheets_schema" / (name.replace(".", "/") + ".py")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    namespace = {"__name__": "data_sheets_schema." + name, "__file__": str(path)}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace


def fresh_observer(tmp_path, monkeypatch, *, phases=None, caches=None):
    if not hasattr(sys, "monitoring"):
        pytest.skip("real monitoring event fixtures require Python 3.12+")
    result = observer.Observer(tmp_path, tmp_path / "events", phases=phases or {}, cache_targets=caches or {})
    # Synthetic functions are deliberately not installed in sys.modules. The
    # independent origin test below covers production namespace rejection.
    monkeypatch.setattr(result, "_origins", lambda: [])
    return result


def events(result):
    return [json.loads(line) for line in (result.output / "observer.jsonl").read_text().splitlines()]


def test_real_monitoring_frames_return_unwind_identity_and_not_reached(tmp_path, monkeypatch):
    ns = saved_module(tmp_path, "provenance", """
def check_record(data):
    if data == 'bad':
        raise ValueError('private exception text must not be logged')
    return ('unchanged', data)

def _record_validator():
    return 'not called'

class ProvenanceRecord:
    def write(self, data):
        return check_record(data)
""")
    func, code = ns["check_record"], ns["check_record"].__code__
    before_tools = [sys.monitoring.get_tool(i) for i in range(6)] if hasattr(sys, "monitoring") else []
    seen = fresh_observer(tmp_path, monkeypatch, phases={"provenance": {
        "check_record": "record_validation", "ProvenanceRecord.write": "record_write",
        "_record_validator": "record_validator_construction"}})
    try:
        seen.start(arm_trace=False)
        assert sys.monitoring.get_events(seen.tool) & sys.monitoring.events.PY_UNWIND
        def unrelated_exception():
            raise LookupError('unrelated exception outside the selected source')
        with pytest.raises(LookupError, match='unrelated exception'):
            unrelated_exception()
        assert ns["ProvenanceRecord"]().write("ok") == ("unchanged", "ok")
        assert not sys.monitoring.get_local_events(seen.tool, code) & sys.monitoring.events.PY_UNWIND
        assert sys.monitoring.get_local_events(seen.tool, code) & sys.monitoring.events.PY_RETURN
        with pytest.raises(ValueError, match="private exception"):
            ns["ProvenanceRecord"]().write("bad")
    finally:
        seen.close()
    assert ns["check_record"] is func and ns["check_record"].__code__ is code
    assert [sys.monitoring.get_tool(i) for i in range(6)] == before_tools
    assert seen.valid
    assert seen.unmatched_unwind_events > 0
    assert not seen.active
    assert seen.stats["provenance:check_record"]["calls"] == 2
    assert seen.stats["provenance:check_record"]["returns"] == 1
    assert seen.stats["provenance:check_record"]["unwinds"] == 1
    rows = events(seen)
    assert len([r for r in rows if r["event"] == "phase_start"]) == 4
    assert len([r for r in rows if r["event"] == "phase_end"]) == 4
    assert rows[-1]["phases"]["provenance:_record_validator"] == "not_reached"
    assert "private exception text" not in (seen.output / "observer.jsonl").read_text()


TYPED_SOURCE = """
import json
_VALIDATED_BOUNDED_BYTES = set()
def _bounded_json(raw, label, limit):
    key = raw
    if key in _VALIDATED_BOUNDED_BYTES:
        return json.loads(raw)
    value = json.loads(raw)
    if len(_VALIDATED_BOUNDED_BYTES) >= 2:
        _VALIDATED_BOUNDED_BYTES.clear()
    _VALIDATED_BOUNDED_BYTES.add(key)
    return value

class DerivationCache:
    def __init__(self):
        self._rows, self._bytes = {}, 0
        self.max_entries, self.max_bytes = 1, 100
    def _store(self, key, encoded):
        while self._rows and (len(self._rows) >= self.max_entries or self._bytes + len(encoded) > self.max_bytes):
            self._bytes -= len(self._rows.pop(next(iter(self._rows))))
        self._rows[key] = encoded
        self._bytes += len(encoded)
    def _derive(self, key):
        encoded = self._rows.get(key)
        if encoded is None:
            encoded = b'{}'
            self._store(key, encoded)
        value = json.loads(encoded)
        return value
"""


def test_actual_warm_decode_hits_and_confirmed_evictions(tmp_path, monkeypatch):
    ns = saved_module(tmp_path, "typed_audit", TYPED_SOURCE)
    seen = fresh_observer(tmp_path, monkeypatch, caches={"typed_audit": (
        "_bounded_json", "DerivationCache._derive", "DerivationCache._store")})
    originals = (ns["_bounded_json"], ns["DerivationCache"]._store, ns["DerivationCache"]._derive)
    try:
        seen.start(arm_trace=False)
        assert ns["_bounded_json"](b'{}', "x", 100) == {}
        assert ns["_bounded_json"](b'{}', "x", 100) == {}
        assert ns["_bounded_json"](b'[]', "x", 100) == []
        assert ns["_bounded_json"](b'0', "x", 100) == 0
        cache = ns["DerivationCache"]()
        assert cache._derive("first") == {}
        assert cache._derive("first") == {}
        assert cache._derive("second") == {}
    finally:
        seen.close()
    assert seen.valid and not seen.active
    assert originals == (ns["_bounded_json"], ns["DerivationCache"]._store, ns["DerivationCache"]._derive)
    warm = seen.stats["typed_audit:_bounded_json"]["counters"]
    assert warm["warm_decode_entries"] == warm["warm_decode_returns"] == 1
    assert warm["warm_decode_input_bytes"] == 2
    assert warm["validated_set_clear_entries"] == 1
    assert warm["validated_set_clear_entries_removed_if_success"] == 2
    cache_stats = seen.stats["typed_audit:DerivationCache._store"]["counters"]
    assert cache_stats["typed_eviction_entries"] == cache_stats["evictions_confirmed"] == 1
    derives = seen.stats["typed_audit:DerivationCache._derive"]["counters"]
    assert derives["derive_hits"] == 1 and derives["derive_misses"] == 2


def test_original_inline_eviction_source_is_observed_without_store(tmp_path, monkeypatch):
    original = TYPED_SOURCE.replace("            self._store(key, encoded)", """
            while self._rows and len(self._rows) >= self.max_entries:
                self._bytes -= len(self._rows.pop(next(iter(self._rows))))
            self._rows[key] = encoded
            self._bytes += len(encoded)""")
    ns = saved_module(tmp_path, "typed_audit", original)
    seen = fresh_observer(tmp_path, monkeypatch, caches={"typed_audit": ("DerivationCache._derive",)})
    try:
        seen.start(arm_trace=False)
        cache = ns["DerivationCache"]()
        cache._derive("first")
        cache._derive("second")
    finally:
        seen.close()
    assert seen.valid
    counts = seen.stats["typed_audit:DerivationCache._derive"]["counters"]
    assert counts["typed_eviction_entries"] == counts["evictions_confirmed"] == 1


@pytest.mark.parametrize("legacy", [False, True])
def test_open_distinguishes_serialized_shared_cache_from_original_raw_cache(tmp_path, monkeypatch, legacy):
    common = """
def _open(packet, *, derivations=None):
    raw_packet = json.dumps(packet).encode()
    key = ('open', packet['id'])
"""
    if legacy:
        body = """
    opened = getattr(derivations, '_opened', None)
    if opened is None:
        opened = derivations._opened = {}
    hit = opened.get(key)
    if hit is not None:
        raw_bytes, payload_json = hit
        return dict(raw_bytes), payload_json
    while len(opened) >= derivations.max_entries:
        opened.pop(next(iter(opened)))
    opened[key] = ({'data': b'abc'}, '{}')
    return {'data': b'abc'}, '{}'
"""
    else:
        body = """
    hit = derivations._rows.get(key)
    if hit is not None:
        value = json.loads(hit)
        return {name: blob.encode() for name, blob in value['raw'].items()}, value['payload']
    derivations._store(key, b'{"raw":{"data":"abc"},"payload":"{}"}')
    return {'data': b'abc'}, '{}'
"""
    ns = saved_module(tmp_path, "typed_audit", TYPED_SOURCE + common + body)
    seen = fresh_observer(tmp_path, monkeypatch, caches={"typed_audit": ("_open", "DerivationCache._store")})
    try:
        seen.start(arm_trace=False)
        cache = ns["DerivationCache"]()
        assert ns["_open"]({'id': 'one'}, derivations=cache) == ({'data': b'abc'}, '{}')
        assert ns["_open"]({'id': 'one'}, derivations=cache) == ({'data': b'abc'}, '{}')
        assert ns["_open"]({'id': 'two'}, derivations=cache) == ({'data': b'abc'}, '{}')
    finally:
        seen.close()
    assert seen.valid and not seen.active
    counts = seen.stats["typed_audit:_open"]["counters"]
    assert counts["open_hits"] == 1 and counts["open_misses"] == 2
    marker = "open_legacy_copy" if legacy else "open_serialized_decode"
    assert counts[marker + "_entries"] == counts[marker + "_returns"] == 1
    assert counts[marker + "_next_line_observed"] == 1
    assert counts[marker + "_through_function_end_ns"] >= counts[marker + "_to_next_line_ns"]
    assert ("open_serialized_decode_entries" in counts) is not legacy
    target = next(t for t in seen.targets.values() if t["qualname"] == "_open")
    assert target["cache_model"] == ("separate_legacy_opened_raw_tuple_cache" if legacy else
                                      "shared_bounded_serialized_rows_with_json_decode_and_unblob")
    if legacy:
        assert counts["legacy_open_eviction_entries"] == counts["evictions_confirmed"] == 1
    else:
        stores = seen.stats["typed_audit:DerivationCache._store"]["counters"]
        assert stores["store_product_open"] == 2
        assert stores["evicted_product_open"] == stores["evictions_confirmed"] == 1


def test_shared_memo_eviction_and_natural_runtime_token_return(tmp_path, monkeypatch):
    memo = saved_module(tmp_path, "shared_generation", """
import json
def memo(spec, namespace, raw_parts, build):
    key = namespace
    cache = spec.cache
    if key in cache:
        return json.loads(cache[key])
    result = build()
    encoded = json.dumps(result).encode()
    while cache and len(cache) >= 1:
        del cache[next(iter(cache))]
    cache[key] = encoded
    return json.loads(encoded)
""")
    token = saved_module(tmp_path, "native_catalog_reuse", """
_READY = object()
calls = 0
def runtime_token():
    global calls
    calls += 1
    return _READY if calls == 1 else None
""")
    seen = fresh_observer(tmp_path, monkeypatch, caches={"shared_generation": ("memo",),
        "native_catalog_reuse": ("runtime_token",)})
    state = types.SimpleNamespace(cache={})
    try:
        seen.start(arm_trace=False)
        memo["memo"](state, "first", (), lambda: {})
        memo["memo"](state, "first", (), lambda: pytest.fail("cache miss unexpectedly rebuilt"))
        memo["memo"](state, "second", (), lambda: {})
        assert token["runtime_token"]() is token["_READY"]
        assert token["runtime_token"]() is None
    finally:
        seen.close()
    assert seen.valid and token["calls"] == 2  # Observer never invokes token itself.
    counts = seen.stats["shared_generation:memo"]["counters"]
    assert counts["shared_hit_decode_entries"] == 1
    assert counts["shared_miss_entries"] == 2
    assert counts["shared_eviction_entries"] == counts["evictions_confirmed"] == 1
    assert seen.stats["native_catalog_reuse:runtime_token"]["counters"] == {
        "runtime_token_ready": 1, "runtime_token_none": 1}


def test_callback_sink_failure_does_not_replace_production_result(tmp_path, monkeypatch):
    ns = saved_module(tmp_path, "provenance", "def check_record(data):\n    return data\n")
    seen = fresh_observer(tmp_path, monkeypatch, phases={"provenance": {"check_record": "validation"}})
    try:
        seen.start(arm_trace=False)
        real_emit = seen._emit
        def failed_sink(*args, **kwargs):
            raise OSError("synthetic diagnostic disk full")
        monkeypatch.setattr(seen, "_emit", failed_sink)
        assert ns["check_record"]("untouched") == "untouched"
        monkeypatch.setattr(seen, "_emit", real_emit)
    finally:
        seen.close()
    assert not seen.valid
    assert events(seen)[-1]["valid"] is False


def test_absent_counter_source_is_unknown_and_changed_marker_is_refused(tmp_path):
    seen = observer.Observer(tmp_path, tmp_path / "events", phases={}, cache_targets={"typed_audit": ("_bounded_json",)})
    try:
        assert seen.missing == ["typed_audit:_bounded_json"]
        assert seen.stats == {}
    finally:
        seen.close()
    saved_module(tmp_path, "typed_audit", "def _bounded_json(raw, label, limit):\n    return {}\n")
    with pytest.raises(RuntimeError, match="counter source shape"):
        observer.Observer(tmp_path, tmp_path / "changed", phases={}, cache_targets={"typed_audit": ("_bounded_json",)})


def test_foreign_loaded_module_marks_origin_invalid_without_importing_it(tmp_path, monkeypatch):
    module = types.ModuleType("data_sheets_schema.observer_foreign_fixture")
    module.__file__ = str(HELPER)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    seen = observer.Observer(tmp_path, tmp_path / "events", phases={}, cache_targets={})
    try:
        before = set(sys.modules)
        rows = seen._origins()
        assert set(sys.modules) == before
        row = next(r for r in rows if r["name"] == module.__name__)
        assert row["within_selected_package"] is False
        assert seen.valid is False
    finally:
        seen.close()


def test_non_recorder_bootstrap_does_not_read_config(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["python", "provenance", "validate-records"])
    namespace = {"__file__": str(tmp_path / 'nonexistent.py')}
    exec(observer.BOOTSTRAP, namespace)
    assert "_recorder_observer_runpy" not in namespace
    assert "_recorder_observer_Path" not in namespace
    assert observer.install_from_config(tmp_path) is None


def test_os_process_age_is_available_and_nonnegative():
    result = observer.process_age()
    assert result["seconds"] >= 0
    assert result["method"]
