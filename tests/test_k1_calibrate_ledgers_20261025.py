"""K1 calibration regressions: accounting, held-out fit, and pinned requests."""
import pytest

from scripts.adhoc import k1_calibrate_ledgers_20261025 as k1


def test_total_input_includes_cache_but_cost_does_not_double_count_thinking():
    row = {"input_tokens": 2, "cache_write": 100, "cache_read": 30,
           "output_tokens": 200, "thinking_tokens": 160}
    assert k1.total_input(row) == 132
    assert k1.cost(row) == pytest.approx(2 * 5e-6 + 100 * 6.25e-6 + 30 * .5e-6 + 200 * 25e-6)


def sample(date, size, tokens):
    return {"date": date, "phase": "full", "payload_bytes": size,
            "total_input_tokens": tokens, "input_tokens": tokens,
            "cache_read": 0, "cache_write": 0, "output_tokens": 20,
            "max_tokens": 100, "stop_reason": "end_turn", "raw_a1_error_percent": 0,
            "cost_usd": .1}


def test_fit_is_on_the_other_canary_and_keeps_unknown_unjoined_rows():
    rows = [sample("a", 100, 30), sample("b", 200, 80)]
    unknown = sample("a", None, 40)
    unknown["phase"] = "report"
    rows.append(unknown)
    phases = k1.calibrate(rows)
    assert rows[0]["leave_other_canary_out"]["predicted_input_tokens"] == 40
    assert rows[1]["leave_other_canary_out"]["predicted_input_tokens"] == 60
    assert phases["full"]["fit_tokens_per_byte"] == 110 / 300
    assert phases["report"]["fit_tokens_per_byte"] is None
    assert rows[2]["leave_other_canary_out"] is None


def test_pinned_request_refuses_changed_bytes_and_external_paths(tmp_path):
    path = tmp_path / "payload.json"
    raw = b'{"messages": []}'
    path.write_bytes(raw)
    reader = k1.Reader(tmp_path)
    pin = {"path": str(path), "sha256": k1.sha(raw)}
    assert reader.pinned(pin) == {"messages": []}
    path.write_bytes(b'{"messages": [1]}')
    with pytest.raises(ValueError, match="changed archived snapshot"):
        reader.pinned(pin)
    with pytest.raises(ValueError):
        reader.raw(tmp_path.parent / "foreign.json")


def test_context_digest_must_bind_logical_request(tmp_path):
    payload = {"model": "example", "max_tokens": 10, "messages": []}
    context = {"request_sha256": "0" * 64, "input_tokens": 20}
    pins = {}
    for name, obj in (("request", payload), ("context", context)):
        raw = k1.canonical(obj)
        path = tmp_path / f"{name}.json"
        path.write_bytes(raw)
        pins[name] = {"path": str(path), "sha256": k1.sha(raw)}
    ledger = {"receipt_completion": {**pins, "usage_id": "one"},
              "typed_audit": {"stages": []},
              "rows": [{"usage_id": "one", "phase": "full_receipt_completion"}]}
    with pytest.raises(ValueError, match="count does not bind"):
        k1.request_mapping(k1.Reader(tmp_path), ledger)


@pytest.mark.parametrize("rows", [[], [{"usage_id": "one", "phase": "typed_audit_worker"}]])
def test_stage_must_join_correct_accounted_phase(tmp_path, rows):
    ledger = {"receipt_completion": {"usage_id": "one"},
              "typed_audit": {"stages": []}, "rows": rows}
    with pytest.raises(ValueError, match="expected phase"):
        k1.request_mapping(k1.Reader(tmp_path), ledger)


def test_duplicate_stage_usage_id_is_not_silently_overwritten(tmp_path):
    payload = {"model": "example", "max_tokens": 10, "messages": []}
    context = {"request_sha256": k1.sha(k1.canonical(payload)), "input_tokens": 20}
    pins = {}
    for name, obj in (("request", payload), ("context", context)):
        raw = k1.canonical(obj)
        path = tmp_path / f"{name}.json"
        path.write_bytes(raw)
        pins[name] = {"path": str(path), "sha256": k1.sha(raw)}
    stage = {**pins, "usage_id": "one", "selection": {"phase": "full_receipt_completion"}}
    ledger = {"receipt_completion": stage, "typed_audit": {"stages": [stage]},
              "rows": [{"usage_id": "one", "phase": "full_receipt_completion"}]}
    with pytest.raises(ValueError, match="duplicate retained stage"):
        k1.request_mapping(k1.Reader(tmp_path), ledger)


def test_duplicate_abandoned_usage_is_not_double_counted(tmp_path, monkeypatch):
    folder = tmp_path / "data/d4d_concatenated/claudecode_api_core" / "2026-10-20a_claude-opus-5-api-generic-v10_rep1"
    folder.mkdir(parents=True)
    (folder / "CHORUS_api_usage_x.json").write_bytes(k1.canonical({"rows": [], "generation_id": "g"}))
    row = {"usage_id": "x", "generation_id": "g"}
    (folder / "CHORUS_abandoned_attempts.jsonl").write_bytes((k1.canonical(row) + b"\n") * 2)
    monkeypatch.setattr(k1, "request_mapping", lambda *args: {})
    with pytest.raises(ValueError, match="duplicate abandoned"):
        k1.analyze(tmp_path)
