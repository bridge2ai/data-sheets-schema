"""Offline invented quota evidence, never an account reading (#2370)."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_subscription_guard as guard

NOW = 1792537200
REGISTRATION = b'{"synthetic":true}'
WORD = b'{"synthetic_owner_word":true}'
RUNTIME = {"auth": {"loggedIn": True, "authMethod": "claude.ai",
                   "apiProvider": "firstParty", "expected_api_key_source": "none"}}


def observation():
    return {"type": "rate_limit_event", "rate_limit_info": {
        "status": "allowed_warning", "isUsingOverage": False, "rateLimitType": "seven_day",
        "utilization": 0.5, "resetsAt": NOW + 3600,
        "unifiedWindows": {"seven_day": {"utilization": 0.5, "resetsAt": NOW + 3600}}}}


def document(event=None, **changes):
    event_raw = guard.canonical(observation() if event is None else event)
    return {"kind": guard.KIND, "version": guard.VERSION,
        "registration_sha256": guard.sha(REGISTRATION), "runtime_sha256": guard.sha(guard.canonical(RUNTIME)),
        "launch_word_sha256": guard.sha(WORD), "max_starting_weekly_utilization": 0.8,
        "max_age_seconds": 300,
        "captured_at": datetime.fromtimestamp(NOW, timezone.utc).isoformat().replace("+00:00", "Z"),
        "event_json": event_raw.decode(), "event_sha256": guard.sha(event_raw), **changes}


def build(doc=None, *, clock=lambda: NOW):
    raw = guard.canonical(document() if doc is None else doc)
    return guard.SubscriptionGuard(raw, expected_sha256=guard.sha(raw), registration_raw=REGISTRATION,
        runtime=RUNTIME, launch_word_raw=WORD, clock=clock)


def test_exact_evidence_one_dispatch_and_long_run_readback():
    item = build()
    item.before_dispatch()
    with pytest.raises(ValueError, match="already consumed"):
        item.before_dispatch()
    saved = guard.validate_saved_snapshot(item.raw, item.snapshot(), registration_raw=REGISTRATION,
        runtime=RUNTIME, launch_word_raw=WORD)
    assert saved.dispatched and saved.reading["utilization"] == 0.5


@pytest.mark.parametrize("key,value", [
    ("isUsingOverage", True), ("isUsingOverage", None), ("isUsingOverage", 0),
    ("isUsingOverage", "false"), ("status", "rejected"), ("status", None),
    ("utilization", True), ("utilization", -0.1), ("utilization", 1.1),
    ("utilization", 10 ** 1000), ("resetsAt", True), ("resetsAt", 0),
])
def test_invalid_or_unknown_observation_refused(key, value):
    event = observation()
    event["rate_limit_info"][key] = value
    with pytest.raises(ValueError):
        build(document(event))


def test_weekly_missing_and_alias_conflicts_refused():
    event = observation()
    event["rate_limit_info"].pop("rateLimitType")
    event["rate_limit_info"].pop("unifiedWindows")
    with pytest.raises(ValueError, match="no seven_day"):
        build(document(event))
    event = observation()
    event["rate_limit_info"]["unifiedWindows"]["seven_day"]["utilization"] = 0.4
    with pytest.raises(ValueError, match="conflict"):
        build(document(event))


@pytest.mark.parametrize("key,value", [
    ("max_age_seconds", True), ("max_age_seconds", 301), ("max_age_seconds", 0),
    ("max_starting_weekly_utilization", True), ("max_starting_weekly_utilization", -1),
    ("version", True), ("registration_sha256", "x"), ("runtime_sha256", "x"),
    ("launch_word_sha256", "x"), ("event_sha256", "x"),
    ("captured_at", "2026-10-20Z"), ("captured_at", "brokenZ"),
])
def test_guard_policy_and_binding_fail_closed(key, value):
    with pytest.raises(ValueError):
        build(document(**{key: value}))


@pytest.mark.parametrize("offset", [-1, 301, float("inf")])
def test_stale_future_invalid_clock_refused(offset):
    with pytest.raises(ValueError):
        build(clock=lambda: NOW + offset)


def test_dispatch_rechecks_time_file_reset_and_headroom(tmp_path):
    clock = [NOW]
    item = build(clock=lambda: clock[0])
    clock[0] += 301
    with pytest.raises(ValueError, match="stale"):
        item.before_dispatch()
    item = build()
    item.path = tmp_path / "observation.json"
    item.path.write_bytes(item.raw + b"\n")
    with pytest.raises(ValueError, match="changed"):
        item.before_dispatch()
    with pytest.raises(ValueError, match="headroom"):
        build(document(max_starting_weekly_utilization=0.4))
    event = observation()
    event["rate_limit_info"].pop("unifiedWindows")
    event["rate_limit_info"]["resetsAt"] = NOW
    with pytest.raises(ValueError, match="reset"):
        build(document(event))
    event["rate_limit_info"]["resetsAt"] += 3600
    event["rate_limit_info"]["utilization"] = 1
    with pytest.raises(ValueError, match="headroom"):
        build(document(event, max_starting_weekly_utilization=1))


def test_live_overage_rejection_or_exhaustion_are_sticky():
    for key, value in (("isUsingOverage", True), ("status", "rejected"), ("utilization", 1)):
        item, event = build(), observation()
        event["rate_limit_info"].pop("unifiedWindows")
        event["rate_limit_info"][key] = value
        with pytest.raises(ValueError):
            item.observe(event)
        assert item.stop_reason and item.observed_events == 1
    item = build()
    item.observe({"type": "assistant"})
    item.observe(observation())
    assert item.stop_reason is None and item.observed_events == 1


def test_saved_snapshot_rejects_changed_scientific_or_policy_metadata():
    item = build()
    for key, value in (("maximum_starting_utilization", 0.99), ("weekly", {"utilization": 0}),
                       ("basis", "authenticated"), ("dispatched", 1), ("observed_rate_limit_events", True)):
        snapshot = deepcopy(item.snapshot())
        snapshot[key] = value
        with pytest.raises(ValueError):
            guard.validate_saved_snapshot(item.raw, snapshot, registration_raw=REGISTRATION,
                runtime=RUNTIME, launch_word_raw=WORD)


@pytest.mark.parametrize("utilization,maximum", [(0.5, 0.4), (1, 1)])
def test_self_consistently_rehashed_saved_admission_still_requires_headroom(utilization, maximum):
    event = observation()
    event["rate_limit_info"].pop("unifiedWindows")
    event["rate_limit_info"]["utilization"] = utilization
    doc = document(event, max_starting_weekly_utilization=maximum)
    raw = guard.canonical(doc)
    snapshot = build().snapshot()
    snapshot.update(guard_sha256=guard.sha(raw), observation_sha256=doc["event_sha256"],
        weekly={"utilization": utilization, "resets_at": NOW + 3600},
        maximum_starting_utilization=maximum, dispatched=True)
    # Identity/hash consistency alone cannot certify a forbidden admission.
    # No present-day timestamp/reset check is needed for historical readback.
    with pytest.raises(ValueError, match="headroom"):
        guard.validate_saved_snapshot(raw, snapshot, registration_raw=REGISTRATION,
            runtime=RUNTIME, launch_word_raw=WORD)


def test_saved_observation_reset_must_follow_capture_but_can_expire_later():
    item = build()
    guard.validate_saved_snapshot(item.raw, item.snapshot(), registration_raw=REGISTRATION,
        runtime=RUNTIME, launch_word_raw=WORD)  # old observations do not get re-aged
    event = observation()
    event["rate_limit_info"].pop("unifiedWindows")
    event["rate_limit_info"]["resetsAt"] = NOW
    doc = document(event)
    raw = guard.canonical(doc)
    snapshot = item.snapshot()
    snapshot.update(guard_sha256=guard.sha(raw), observation_sha256=doc["event_sha256"],
        weekly={"utilization": 0.5, "resets_at": NOW}, dispatched=True)
    with pytest.raises(ValueError, match="reset"):
        guard.validate_saved_snapshot(raw, snapshot, registration_raw=REGISTRATION,
            runtime=RUNTIME, launch_word_raw=WORD)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'])
def test_json_duplicate_and_nonfinite_refused(raw):
    with pytest.raises(ValueError):
        guard.strict_json(raw)


def test_read_regular_rejects_symlinks_and_oversize(tmp_path):
    target = tmp_path / "raw"
    target.write_bytes(b"123")
    link = tmp_path / "link"
    link.symlink_to(target)
    for path, limit in ((link, 4), (target, 2)):
        with pytest.raises(ValueError):
            guard.read_regular(path, limit=limit)


def test_actual_shared_frontdoor_refuses_unsafe_before_engine(tmp_path, monkeypatch):
    from data_sheets_schema import native_shared_execution as execution
    from data_sheets_schema import native_execution_engine as engine
    monkeypatch.setattr(execution.registration, "verified", lambda raw: {
        "runtime": RUNTIME, "attempt_directory": str(tmp_path / "fresh-attempt")})
    monkeypatch.setattr(guard, "_now", lambda: NOW)
    dispatched = []
    monkeypatch.setattr(engine, "launch", lambda *a, **k: dispatched.append(k) or k["effects"].launch_guard)
    path, word = tmp_path / "guard", tmp_path / "word"
    word.write_bytes(WORD)
    path.write_bytes(guard.canonical(document(max_starting_weekly_utilization=0.1)))
    kwargs = dict(review_path="invented-review", ci_path="invented-ci", launch_word_path=word,
        subscription_guard_path=path, subscription_guard_sha256=guard.sha(path.read_bytes()))
    with pytest.raises(ValueError, match="headroom"):
        execution.launch(REGISTRATION, **kwargs)
    assert not dispatched
    path.write_bytes(guard.canonical(document()))
    kwargs["subscription_guard_sha256"] = guard.sha(path.read_bytes())
    item = execution.launch(REGISTRATION, **kwargs)
    assert isinstance(item, guard.SubscriptionGuard) and len(dispatched) == 1
    kwargs.pop("subscription_guard_path")
    with pytest.raises(TypeError):
        execution.launch(REGISTRATION, **kwargs)
    (tmp_path / "fresh-attempt").mkdir()
    kwargs["subscription_guard_path"] = path
    monkeypatch.setattr(guard, "_now", lambda: NOW + 301)
    with pytest.raises(ValueError, match="new.*resume"):
        execution.launch(REGISTRATION, **kwargs)


def test_new_guard_modules_are_in_dependency_closure():
    from data_sheets_schema.native_attribution_registration import _code_pins
    pins = _code_pins()
    for name in ("native_subscription_guard", "native_permission_probe", "native_probe_provider", "native_generation"):
        assert "src/data_sheets_schema/" + name + ".py" in pins


def test_engine_admission_consumes_before_spawn_and_overage_stops_before_adapter(tmp_path):
    from data_sheets_schema import native_execution_engine as engine
    item, events = build(), []
    def file(path, name):
        events.append("read")
        return item.raw
    def write(path, raw):
        assert item.dispatched
        events.append("durable-admission")
        assert guard.strict_json(raw) == {"guard_sha256": guard.sha(item.raw), "consumed": True}
    engine._admit_subscription_guard(item, tmp_path, file, write)
    events.append("mock-spawn")
    assert events == ["read", "durable-admission", "mock-spawn"]
    class BudgetStop(Exception):
        pass
    observer = engine._guarded_observer(item, SimpleNamespace(observe=lambda e: events.append("adapter")), BudgetStop)
    observer({"type": "assistant"})
    event = observation()
    event["rate_limit_info"]["isUsingOverage"] = True
    with pytest.raises(BudgetStop, match="subscription guard"):
        observer(event)
    assert events.count("adapter") == 1 and item.stop_reason
    item = build(clock=lambda: NOW + 299)
    item.clock = lambda: NOW + 301
    with pytest.raises(ValueError, match="stale"):
        engine._admit_subscription_guard(item, tmp_path, file, write)
    assert not item.dispatched


def test_engine_recaptured_owner_word_must_match_guard_before_reservation():
    from data_sheets_schema import native_execution_engine as engine
    item = build()
    engine._join_subscription_authority(item, REGISTRATION, {"runtime": RUNTIME},
                                       {"raw": {"launch_word": WORD}})
    with pytest.raises(ValueError, match="launch_word_sha256"):
        engine._join_subscription_authority(item, REGISTRATION, {"runtime": RUNTIME},
                                           {"raw": {"launch_word": WORD + b"\n"}})
    with pytest.raises(ValueError, match="registration_sha256"):
        engine._join_subscription_authority(item, REGISTRATION + b"\n", {"runtime": RUNTIME},
                                           {"raw": {"launch_word": WORD}})
    assert not item.dispatched


@pytest.mark.parametrize("retained", ["subscription-guard.json", "subscription-dispatched.json"])
def test_read_final_rejects_stripped_guard_snapshot_even_with_rehashed_marker(tmp_path, retained):
    from data_sheets_schema import native_execution_engine as engine
    attempt, evidence = tmp_path / "attempt", tmp_path / "evidence"
    attempt.mkdir(); evidence.mkdir()
    value = {"attempt_directory": str(attempt), "evidence_directory": str(evidence),
             "attempt_id": "invented", "composition_sha256": "x", "runtime": RUNTIME}
    result = {"kind": "d4d_native_shared_attempt", "version": 1, "attempt_id": "invented",
              "composition_sha256": "x", "registration_sha256": guard.sha(REGISTRATION),
              "started_sha256": guard.sha(b"start"), **engine.UNASSESSED}
    (attempt / "registration.json").write_bytes(REGISTRATION)
    (attempt / "started.json").write_bytes(b"start")
    (attempt / retained).write_bytes(b"retained guard evidence")
    raw = guard.canonical(result)
    (evidence / "final.json").write_bytes(raw)
    (evidence / "published.json").write_bytes(guard.canonical({
        "final_sha256": guard.sha(raw), "started_sha256": guard.sha(b"start"),
        "registration_sha256": guard.sha(REGISTRATION)}))
    contract = SimpleNamespace(require_fixed=lambda: None, kind=result["kind"],
        registration=SimpleNamespace(verified=lambda raw: value), composition=None,
        authority=None, gates=None, replay=None, shared=None)
    effects = SimpleNamespace(file=lambda path, name: path.read_bytes(),
        durable_new=None, sync_directory=None, mkdir_durable=None, signals=None, now=None,
        probe_runtime=None, expected_runtime_observation=None, authorizations=None, unchanged=None, sys=None)
    with pytest.raises(ValueError, match="missing its final snapshot"):
        engine.read_final(REGISTRATION, contract=contract, effects=effects)
