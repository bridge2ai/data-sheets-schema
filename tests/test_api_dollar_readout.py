"""Unit and integration tests for the live dollar readout (Step A3b / #1763, #4345, #4829)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from data_sheets_schema.dollar_readout import (
    CAP_FULL,
    CAP_FULL_READDRESS,
    CAP_REPORT_FAMILY,
    compute_readout,
    extract_saved_snapshot,
    format_readout,
    get_phase_output_cap,
    price_abandoned_row,
    price_settled_row,
    price_settled_rows,
    price_tokens,
)
from scripts.api_dollar_readout import main as cli_main

REPO_ROOT = Path(__file__).resolve().parents[1]
V9_CHORUS_LEDGER_PATH = (
    REPO_ROOT
    / "data/d4d_concatenated/claudecode_api_core/2026-09-12_claude-opus-5-api-generic-v9_rep1/CHORUS_api_usage_46d8033e251b3c6e.json"
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v9_chorus_ledger_exact_reproduction():
    """Gate requirement: reproduces $3.30811950 from the v9 CHORUS ledger file."""
    assert V9_CHORUS_LEDGER_PATH.is_file(), f"Missing required fixture: {V9_CHORUS_LEDGER_PATH}"

    summary = compute_readout(V9_CHORUS_LEDGER_PATH)

    assert summary["settled_calls"] == 6
    assert abs(summary["settled_dollars"] - 3.30811950) < 1e-8
    assert summary["has_pending_call"] is False
    assert summary["pending_call"] is None
    assert abs(summary["total_projected_dollars"] - 3.30811950) < 1e-8


def test_chorus_pending_full_worst_case():
    """Gate requirement: synthetic pending_call at v9 full input reproduces ~3.45 ($3.44632375)."""
    ledger = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "test_chorus", "condition": "generic_v10"},
        "rows": [],
        "pending_call": {
            "phase": "full",
            "attempt": 1,
            "started_at": "2026-10-11T00:00:00Z",
            "usage_id": "call_1",
        },
    }
    summary = compute_readout(ledger, project="CHORUS")
    assert summary["has_pending_call"] is True
    pending = summary["pending_call"]
    assert pending["output_cap_tokens"] == CAP_FULL  # 128,000
    assert abs(pending["output_worst_case_dollars"] - 3.20) < 1e-8
    # v9 input: 9636 uncached + 31703 cache_write = 0.24632375
    assert abs(pending["input_worst_case_dollars"] - 0.24632375) < 1e-8
    # Total: 3.20 + 0.24632375 = 3.44632375
    assert abs(pending["pending_worst_case_dollars"] - 3.44632375) < 1e-8
    assert abs(summary["total_projected_dollars"] - 3.44632375) < 1e-8
    # Formatted display rounds to $3.45
    formatted = format_readout(summary)
    assert "$3.4463" in formatted or "3.44632375" in formatted


def test_ai_readi_pending_full_worst_case():
    """Gate requirement: synthetic pending_call at v8 full input reproduces ~4.50 ($4.50469250)."""
    ledger = {
        "version": 1,
        "identity": {"project": "AI_READI", "label": "test_aireadi", "condition": "generic_v10"},
        "rows": [],
        "pending_call": {
            "phase": "full",
            "attempt": 1,
            "started_at": "2026-10-11T00:00:00Z",
            "usage_id": "call_2",
        },
    }
    summary = compute_readout(ledger, project="AI_READI")
    assert summary["has_pending_call"] is True
    pending = summary["pending_call"]
    assert pending["output_cap_tokens"] == CAP_FULL  # 128,000
    assert abs(pending["output_worst_case_dollars"] - 3.20) < 1e-8
    # v8 input: 6361 uncached + 203662 cache_write = 1.30469250
    assert abs(pending["input_worst_case_dollars"] - 1.3046925) < 1e-8
    # Total: 3.20 + 1.3046925 = 4.50469250
    assert abs(pending["pending_worst_case_dollars"] - 4.5046925) < 1e-8
    assert abs(summary["total_projected_dollars"] - 4.5046925) < 1e-8


def test_full_readdress_cap_and_input():
    """full_readdress uses 8,000 output cap (READDRESS_MAX_TOKENS) plus full in/out tokens."""
    ledger = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "test_readdress"},
        "rows": [],
        "pending_call": {
            "phase": "full_readdress",
            "attempt": 1,
            "started_at": "2026-10-11T00:00:00Z",
        },
    }
    summary = compute_readout(ledger, project="CHORUS")
    pending = summary["pending_call"]
    assert pending["output_cap_tokens"] == CAP_FULL_READDRESS  # 8000
    assert abs(pending["output_worst_case_dollars"] - (8000 * 25e-6)) < 1e-8  # $0.20


@pytest.mark.parametrize(
    "phase",
    [
        "reconcile_full",
        "report",
        "report_regate",
        "repair_full",
        "report_after_repair",
    ],
)
def test_report_family_caps(phase):
    """All report family phases use the 96,000 output cap ($2.40)."""
    assert get_phase_output_cap(phase) == CAP_REPORT_FAMILY  # 96,000
    ledger = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "test_report_family"},
        "rows": [],
        "pending_call": {"phase": phase, "attempt": 1},
    }
    summary = compute_readout(ledger, project="CHORUS")
    pending = summary["pending_call"]
    assert pending["output_cap_tokens"] == 96000
    assert abs(pending["output_worst_case_dollars"] - (96000 * 25e-6)) < 1e-8  # $2.40


def test_receipt_completion_saved_snapshot(tmp_path):
    """receipt_completion resolves max_tokens and input_tokens from hash-verified saved snapshots."""
    req_file = tmp_path / "receipt_completion_request.json"
    req_file.write_text(json.dumps({"max_tokens": 75000}), encoding="utf-8")

    ctx_file = tmp_path / "receipt_completion_context.json"
    ctx_file.write_text(json.dumps({"input_tokens": 50000}), encoding="utf-8")

    ledger_file = tmp_path / "CHORUS_api_usage_test.json"
    ledger_data = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "test_rc"},
        "rows": [],
        "receipt_completion": {
            "request": {"path": str(req_file), "sha256": _sha256_file(req_file)},
            "context": {"path": str(ctx_file), "sha256": _sha256_file(ctx_file)},
        },
        "pending_call": {
            "phase": "receipt_completion",
            "attempt": 1,
            "started_at": "2026-10-11T00:00:00Z",
        },
    }
    ledger_file.write_text(json.dumps(ledger_data), encoding="utf-8")

    summary = compute_readout(ledger_file)
    pending = summary["pending_call"]
    assert pending["output_cap_tokens"] == 75000
    assert abs(pending["output_worst_case_dollars"] - (75000 * 25e-6)) < 1e-8  # 1.875
    assert pending["input_bound"] == 50000
    assert pending["input_bound_unknown"] is False
    assert abs(pending["input_worst_case_dollars"] - (50000 * 5e-6)) < 1e-8  # 0.25
    assert abs(pending["pending_worst_case_dollars"] - 2.125) < 1e-8


def test_typed_audit_saved_snapshot(tmp_path):
    """typed_audit stage resolves max_tokens and input_tokens from hash-verified stage snapshots."""
    req_file = tmp_path / "typed_audit_0_request.json"
    req_file.write_text(json.dumps({"max_tokens": 30000}), encoding="utf-8")

    ctx_file = tmp_path / "typed_audit_0_context.json"
    ctx_file.write_text(json.dumps({"input_tokens": 20000}), encoding="utf-8")

    ledger_file = tmp_path / "CHORUS_api_usage_typed.json"
    ledger_data = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "test_typed"},
        "rows": [],
        "typed_audit": {
            "stages": [
                {
                    "request": {"path": str(req_file), "sha256": _sha256_file(req_file)},
                    "context": {"path": str(ctx_file), "sha256": _sha256_file(ctx_file)},
                }
            ]
        },
        "pending_call": {
            "phase": "typed_audit_worker",
            "attempt": 1,
            "started_at": "2026-10-11T00:00:00Z",
        },
    }
    ledger_file.write_text(json.dumps(ledger_data), encoding="utf-8")

    summary = compute_readout(ledger_file)
    pending = summary["pending_call"]
    assert pending["output_cap_tokens"] == 30000
    assert pending["input_bound"] == 20000
    assert pending["input_bound_unknown"] is False
    assert abs(pending["pending_worst_case_dollars"] - (30000 * 25e-6 + 20000 * 5e-6)) < 1e-8


def test_saved_snapshot_sha256_mismatch_rejected(tmp_path):
    """Tampered snapshot with mismatched sha256 is rejected and fails closed."""
    ctx_file = tmp_path / "typed_audit_0_context.json"
    ctx_file.write_text(json.dumps({"input_tokens": 20000}), encoding="utf-8")

    assert extract_saved_snapshot({"path": str(ctx_file), "sha256": "0" * 64}) is None


def test_unknown_pending_input_bound_fails_closed():
    """Unresolved pending input bound never prices as $0.00 and fails closed on trigger/cap."""
    ledger = {
        "version": 1,
        "identity": {"project": "UNCALIBRATED_PROJECT", "label": "test_unknown"},
        "rows": [{"output_tokens": 40000}],  # $1.00 settled
        "pending_call": {
            "phase": "full",
            "attempt": 1,
        },
    }
    summary = compute_readout(ledger, cap=15.0, trigger=11.5)
    assert summary["has_pending_call"] is True
    assert summary["pending_input_bound_unknown"] is True
    pending = summary["pending_call"]
    assert pending["input_bound"] is None
    assert pending["input_bound_source"] == "unknown"
    assert pending["input_bound_unknown"] is True
    assert pending["input_worst_case_dollars"] is None
    assert pending["pending_worst_case_dollars"] is None
    assert summary["total_projected_dollars"] is None
    assert summary["trigger_reached"] is True
    assert summary["cap_reached"] is True
    formatted = format_readout(summary)
    assert "UNKNOWN" in formatted


def test_custom_bounds_and_worst_case_cache():
    """Custom bounds override baseline, and worst_case_cache prices at RATE_CACHE_WRITE."""
    custom = {
        "CHORUS": {
            "report_regate": 200000,
        }
    }
    ledger = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "test_custom"},
        "rows": [],
        "pending_call": {"phase": "report_regate", "attempt": 1},
    }
    # Uncached default ($5/M)
    s_uncached = compute_readout(ledger, project="CHORUS", custom_bounds=custom, worst_case_cache=False)
    p_uncached = s_uncached["pending_call"]
    assert p_uncached["input_bound"] == 200000
    assert abs(p_uncached["input_worst_case_dollars"] - (200000 * 5e-6)) < 1e-8  # $1.00

    # Cache write worst-case ($6.25/M)
    s_cache = compute_readout(ledger, project="CHORUS", custom_bounds=custom, worst_case_cache=True)
    p_cache = s_cache["pending_call"]
    assert abs(p_cache["input_worst_case_dollars"] - (200000 * 6.25e-6)) < 1e-8  # $1.25


def test_cap_and_operator_trigger_alerts():
    """Alerts fire when projected spend reaches or exceeds trigger or cap."""
    ledger = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "test_alerts"},
        "rows": [
            {"input_tokens": 100000, "output_tokens": 300000}  # 0.5 + 7.5 = $8.00
        ],
        "pending_call": {
            "phase": "full",
            "attempt": 1,
        },
    }
    # CHORUS pending full is ~3.4463, total projected is ~11.4463
    # Cap = 15.00, Trigger = 11.00 -> total 11.4463 >= trigger 11.00 -> trigger_reached!
    s1 = compute_readout(ledger, project="CHORUS", cap=15.0, trigger=11.0)
    assert s1["trigger_reached"] is True
    assert s1["cap_reached"] is False
    assert "TRIGGER REACHED" in format_readout(s1)

    # Trigger = 12.00 -> not reached
    s2 = compute_readout(ledger, project="CHORUS", cap=15.0, trigger=12.0)
    assert s2["trigger_reached"] is False
    assert s2["cap_reached"] is False

    # Cap = 10.00 -> cap_reached!
    s3 = compute_readout(ledger, project="CHORUS", cap=10.0, trigger=9.0)
    assert s3["cap_reached"] is True
    assert "CAP EXCEEDED" in format_readout(s3)


def test_cli_runner_on_v9_ledger():
    """CLI tool runs successfully on historical v9 ledger and outputs $3.30811950."""
    runner = CliRunner()
    result = runner.invoke(cli_main, ["--ledger", str(V9_CHORUS_LEDGER_PATH)])
    assert result.exit_code == 0
    assert "3.30811950" in result.output
    assert "Settled calls:   6" in result.output

    # JSON output
    result_json = runner.invoke(cli_main, ["--ledger", str(V9_CHORUS_LEDGER_PATH), "--json"])
    assert result_json.exit_code == 0
    data = json.loads(result_json.output)
    assert data["settled_calls"] == 6
    assert abs(data["settled_dollars"] - 3.30811950) < 1e-8


def test_cli_runner_trigger_exit_code(tmp_path):
    """CLI returns exit code 1 when stop trigger reached, and exit code 2 when cap reached."""
    ledger_file = tmp_path / "test_api_usage_trigger.json"
    ledger_data = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "test_exit"},
        "rows": [{"output_tokens": 400000}],  # 400k * 25e-6 = $10.00
    }
    ledger_file.write_text(json.dumps(ledger_data), encoding="utf-8")

    runner = CliRunner()
    # Trigger = $9.00 -> exit code 1
    res1 = runner.invoke(cli_main, ["--ledger", str(ledger_file), "--trigger", "9.0"])
    assert res1.exit_code == 1
    assert "TRIGGER REACHED" in res1.output

    # Cap = $8.00 -> exit code 2
    res2 = runner.invoke(cli_main, ["--ledger", str(ledger_file), "--cap", "8.0"])
    assert res2.exit_code == 2
    assert "CAP EXCEEDED" in res2.output


def test_unpriced_model_raises_value_error():
    """Ledger or registration naming a model outside opus-5 pricing raises ValueError."""
    ledger = {
        "version": 1,
        "identity": {
            "project": "CHORUS",
            "label": "test_unpriced",
            "model": "claude-sonnet-4",
        },
        "rows": [{"output_tokens": 1000}],
    }
    with pytest.raises(ValueError, match="do not cover model"):
        compute_readout(ledger)


def test_pending_call_foreign_identity_raises_value_error():
    """Pending call with mismatched run_identity raises ValueError."""
    ledger = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "lbl_a", "method": "claudecode_api"},
        "rows": [],
        "pending_call": {
            "phase": "full",
            "attempt": 1,
            "run_identity": {"project": "AI_READI", "label": "lbl_b", "method": "claudecode_api"},
        },
    }
    with pytest.raises(ValueError, match="conflicts with ledger identity"):
        compute_readout(ledger)


def test_relative_snapshot_pin_resolves_from_metadata_dir(tmp_path):
    """Relative pin paths in a registration snapshot resolve against metadata_dir / intermediate/."""
    meta_dir = tmp_path / "run_dir"
    inter_dir = meta_dir / "intermediate"
    inter_dir.mkdir(parents=True)
    ctx_file = inter_dir / "omission_ctx.json"
    ctx_bytes = b'{"format": "omission_context_v1", "input_tokens": 12345}\n'
    ctx_file.write_bytes(ctx_bytes)
    import hashlib
    ctx_sha = hashlib.sha256(ctx_bytes).hexdigest()

    pin = {"path": "omission_ctx.json", "sha256": ctx_sha, "bytes": len(ctx_bytes)}
    snap = extract_saved_snapshot(pin, metadata_dir=meta_dir)
    assert snap is not None
    assert snap["input_tokens"] == 12345

    ledger = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "lbl_snap"},
        "rows": [],
        "receipt_completion": {"context": pin},
        "pending_call": {"phase": "receipt_completion", "attempt": 1},
    }
    summary = compute_readout(ledger, metadata_dir=meta_dir)
    assert summary["identity"]["project"] == "CHORUS"
    assert summary["pending_call"]["input_bound"] == 12345


# Real run layouts (#5117). The 2026-10-20a and 2026-10-22a CHORUS generic_v10
# canaries as committed on origin/data/chorus-v10-api-canaries-2026-10-22: the
# usage ledger cut to the keys the readout reads, the abandoned-attempts journal
# verbatim, the reasoning log without its thinking blocks, and every snapshot the
# generation's index lists, by name and size.
V10_FIXTURES = REPO_ROOT / "tests/fixtures/dollar_readout_v10"
RUN_20A = "2026-10-20a_claude-opus-5-api-generic-v10_rep1"
RUN_22A = "2026-10-22a_claude-opus-5-api-generic-v10_rep1"


def _fixture_ledger(label: str) -> tuple[str, dict]:
    (path,) = (V10_FIXTURES / label).glob("CHORUS_api_usage_*.json")
    return path.name, json.loads(path.read_text(encoding="utf-8"))


def _fixture_row(label: str) -> dict:
    return json.loads((V10_FIXTURES / label / "CHORUS_abandoned_attempts.jsonl").read_text(encoding="utf-8"))


def _snapshot_sizes(label: str) -> dict[str, int]:
    listing = json.loads((V10_FIXTURES / label / "snapshots.json").read_text(encoding="utf-8"))
    return {entry["file"]: entry["bytes"] for entry in listing["snapshots"]}


def _call(row: dict) -> dict:
    """The pending call `usage_ledger.begin_call` records for the call a row settled."""
    return {key: row[key] for key in ("usage_id", "phase", "attempt", "started_at")}


def _sent(row: dict) -> int:
    return row["input_tokens"] + row["cache_write"] + row["cache_read"]


def _lay_out_run(tmp_path, label, *, rows=None, pending=None, through=None, journal=True, reasoning=False):
    """A canary's run directory as the runner left it with `rows` settled and the
    snapshots up to the file `through` written, each as zeros of its real size.
    Returns the ledger path."""
    source = V10_FIXTURES / label
    meta = tmp_path / "data/d4d_concatenated/claudecode_api_core" / label
    intermediate = meta / "intermediate"
    intermediate.mkdir(parents=True)
    name, ledger = _fixture_ledger(label)
    if rows is not None:
        ledger["rows"] = rows
    if pending is not None:
        ledger["pending_call"] = pending
    (meta / name).write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    if journal:
        journal_bytes = (source / "CHORUS_abandoned_attempts.jsonl").read_bytes()
        (meta / "CHORUS_abandoned_attempts.jsonl").write_bytes(journal_bytes)
    if reasoning:
        (meta / "CHORUS_reasoning.jsonl").write_bytes((source / "CHORUS_reasoning.jsonl").read_bytes())
    listing = json.loads((source / "snapshots.json").read_text(encoding="utf-8"))
    index = {"version": 1, "generation_id": listing["generation_id"], "run_identity": listing["run_identity"],
             "input_identity": {}, "snapshots": []}
    for entry in listing["snapshots"]:
        with (intermediate / entry["file"]).open("wb") as out:
            out.truncate(entry["bytes"])
        index["snapshots"].append({
            "name": entry["name"],
            "path": f"data/d4d_concatenated/claudecode_api_core/{label}/intermediate/{entry['file']}",
            "sha256": hashlib.sha256(bytes(entry["bytes"])).hexdigest(),
            **({"usage_id": entry["usage_id"]} if "usage_id" in entry else {}),
        })
        if entry["file"] == through:
            break
    (intermediate / "CHORUS_snapshot_index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return meta / name


@pytest.mark.parametrize(
    "label, phase, max_tokens, priced_before, priced_now, settled_now",
    [
        (RUN_20A, "report", 96000, 0.8547045, 3.2546295, 23.84207325),
        (RUN_22A, "typed_audit_integration", 32000, 1.98137875, 2.78120375, 17.95198325),
    ],
)
def test_dropped_stream_is_priced_at_the_max_tokens_it_sent(
    tmp_path, label, phase, max_tokens, priced_before, priced_now, settled_now
):
    """Both canaries' dropped streams recorded message_start's usage: the whole input
    and a placeholder 3 or 7 output tokens, which was priced as settled usage."""
    ledger_path = _lay_out_run(tmp_path, label)
    row = _fixture_row(label)
    assert row["stream_trace"]["message_start_seen"] is True
    assert row["stream_trace"]["message_delta_seen"] is False
    assert price_settled_row(row) == pytest.approx(priced_before, abs=1e-9)

    summary = compute_readout(ledger_path)
    (priced,) = summary["abandoned_attempts"]
    assert (priced["phase"], priced["final_usage"], priced["output_tokens_priced"]) == (phase, False, max_tokens)
    assert priced["input_source"] == "recorded"
    assert priced["dollars"] == pytest.approx(priced_now, abs=1e-9)
    assert summary["abandoned_dollars"] == pytest.approx(priced_now, abs=1e-9)
    assert summary["settled_dollars"] == pytest.approx(settled_now, abs=1e-8)
    assert "abandoned attempts:   1" in format_readout(summary)


def test_dropped_stream_with_its_final_usage_is_priced_as_recorded():
    """message_delta carries the final output count; a row that saw it is its usage."""
    row = _fixture_row(RUN_22A)
    row = {**row, "output_tokens": 31000, "stream_trace": {**row["stream_trace"], "message_delta_seen": True}}
    priced = price_abandoned_row(row)
    assert (priced["final_usage"], priced["output_tokens_priced"]) == (True, 31000)
    assert priced["dollars"] == pytest.approx(price_settled_row(row), abs=1e-12)


def test_dropped_stream_before_message_start_is_priced_at_its_cap_and_input_bound(tmp_path):
    """With no usage at all, input is the phase's bound: here the report request the run measured."""
    ledger_path = _lay_out_run(tmp_path, RUN_20A)
    row = _fixture_row(RUN_20A)
    row.update(input_tokens=None, output_tokens=None, cache_read=None, cache_write=None)
    row["stream_trace"] = {**row["stream_trace"], "message_start_seen": False}
    (ledger_path.parent / "CHORUS_abandoned_attempts.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    (priced,) = compute_readout(ledger_path)["abandoned_attempts"]
    assert priced["input_source"] == "measured[report]"
    assert priced["dollars"] == pytest.approx(167639 * 5e-6 + 32869 * 6.25e-6 + 96000 * 25e-6, abs=1e-9)


def test_a_prior_generations_abandoned_attempt_is_counted(tmp_path):
    """A fresh generation's journal boundary is the journal's size when it began
    (`usage_ledger._empty`), so reading from it skipped the 10-20a generation's
    dropped report. A row of a generation the ledger does not name stays out."""
    ledger_path = _lay_out_run(tmp_path, RUN_20A)
    prior = json.loads(ledger_path.read_text(encoding="utf-8"))
    journal = ledger_path.parent / "CHORUS_abandoned_attempts.jsonl"
    other_generation = (V10_FIXTURES / RUN_22A / "CHORUS_abandoned_attempts.jsonl").read_bytes()
    journal.write_bytes(journal.read_bytes() + other_generation)
    ledger_path.rename(ledger_path.with_name(f"{ledger_path.stem}.previous-{'a' * 32}.json"))
    ledger_path.write_text(json.dumps({
        "version": 1, "identity": prior["identity"], "generation_id": "b" * 32,
        "prior_generation_ids": [prior["generation_id"]], "accept_legacy": False, "rows": [],
        "abandoned_journal_offset": journal.stat().st_size,
    }, indent=2) + "\n", encoding="utf-8")

    summary = compute_readout(ledger_path)
    (priced,) = summary["abandoned_attempts"]
    assert (priced["generation_id"], priced["phase"]) == (prior["generation_id"], "report")
    assert priced["dollars"] == pytest.approx(3.2546295, abs=1e-9)
    assert summary["settled_calls"] == len(prior["rows"]) == 11
    assert summary["settled_dollars"] == pytest.approx(price_settled_rows(prior["rows"]) + 3.2546295, abs=1e-8)


def test_pending_report_bound_is_derived_from_the_files_the_run_wrote(tmp_path):
    """10-22a cut back to its report call. The static v9 baseline (44,534 + 31,703
    cache read) put its worst case at $2.6385; the report then cost $2.8838."""
    _, ledger = _fixture_ledger(RUN_22A)
    *settled, report = ledger["rows"]
    ledger_path = _lay_out_run(tmp_path, RUN_22A, rows=settled, pending=_call(report),
                               through="CHORUS_reconcile_core.yaml")
    sizes = _snapshot_sizes(RUN_22A)
    carried = (sizes["CHORUS_audit.json"] + sizes["CHORUS_full.yaml"] + sizes["CHORUS_core.yaml"]
               + sizes["CHORUS_reconcile_core.yaml"] + 3 * sizes["CHORUS_reconcile_full.yaml"])
    assert carried == 261_950

    summary = compute_readout(ledger_path)
    pending = summary["pending_call"]
    full = settled[0]
    assert pending["input_bound"] == {
        "input_tokens": full["input_tokens"] + carried, "cache_write": full["cache_write"], "cache_read": 0}
    assert pending["input_bound_source"] == (
        "derived[report]: measured[full] + 261,950 bytes "
        "(audit.json, full.yaml, core.yaml, reconcile_core.yaml, 3x reconcile_full.yaml)")
    assert sum(pending["input_bound"].values()) == 336_135 >= _sent(report) == 189_513
    assert pending["pending_worst_case_dollars"] >= price_settled_row(report)
    assert "Pending input bound: derived[report]" in format_readout(summary)


def test_the_runners_count_of_the_request_is_preferred(tmp_path):
    """#5157 pins the endpoint's count of a report-family request before dispatch,
    as `{project}_{phase}_context.json`; only this generation's pin is read."""
    _, ledger = _fixture_ledger(RUN_22A)
    *settled, report = ledger["rows"]
    ledger_path = _lay_out_run(tmp_path, RUN_22A, rows=settled, pending=_call(report),
                               through="CHORUS_reconcile_core.yaml")
    intermediate = ledger_path.parent / "intermediate"
    raw = json.dumps({
        "capacity_authority": "caller assertion",
        "context_limit_basis": "Route context window 1,000,000 tokens; sized for largest bundle",
        "context_limit_tokens": 1000000, "input_tokens": _sent(report), "method": "endpoint messages.count_tokens",
        "request_sha256": hashlib.sha256(b"report request").hexdigest(),
        "phase": "report", "attempt": 1, "max_tokens": 128000,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")
    (intermediate / "CHORUS_report_context.json").write_bytes(raw)
    assert compute_readout(ledger_path)["pending_call"]["input_bound_source"].startswith("derived[report]")

    index_path = intermediate / "CHORUS_snapshot_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["snapshots"].append({
        "name": "CHORUS_report_context.json",
        "path": f"data/d4d_concatenated/claudecode_api_core/{RUN_22A}/intermediate/CHORUS_report_context.json",
        "sha256": hashlib.sha256(raw).hexdigest(),
    })
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    pending = compute_readout(ledger_path)["pending_call"]
    assert (pending["input_bound"], pending["input_bound_source"]) == (189_513, "CHORUS_report_context.json")
    assert pending["output_cap_tokens"] == 128000


@pytest.mark.parametrize("label, dropped_before", [(RUN_20A, False), (RUN_22A, True)])
@pytest.mark.parametrize(
    "phase, through", [("reconcile_full", "CHORUS_audit_evidence.json"), ("report", "CHORUS_reconcile_core.yaml")]
)
def test_derived_bound_covers_the_request_each_canary_sent(tmp_path, label, dropped_before, phase, through):
    _, ledger = _fixture_ledger(label)
    at = next(i for i, row in enumerate(ledger["rows"]) if row["phase"] == phase)
    sent = ledger["rows"][at]
    ledger_path = _lay_out_run(tmp_path, label, rows=ledger["rows"][:at], pending=_call(sent),
                               through=through, journal=dropped_before)
    pending = compute_readout(ledger_path)["pending_call"]
    assert pending["input_bound_source"].startswith(f"derived[{phase}]: measured[full] + ")
    assert sum(pending["input_bound"].values()) >= _sent(sent)
    assert pending["input_worst_case_dollars"] >= price_tokens(
        input_tokens=sent["input_tokens"], cache_write=sent["cache_write"], cache_read=sent["cache_read"])


def test_a_retry_is_bounded_by_the_input_its_dropped_attempt_measured(tmp_path):
    """10-20a while the report's second transport attempt ran: the first had dropped
    after message_start, which reports the request's whole input."""
    _, ledger = _fixture_ledger(RUN_20A)
    report = ledger["rows"][9]
    ledger_path = _lay_out_run(tmp_path, RUN_20A, rows=ledger["rows"][:9], pending=_call(report),
                               through="CHORUS_report_incomplete_attempt1_1.txt")
    pending = compute_readout(ledger_path)["pending_call"]
    assert pending["input_bound_source"] == "measured[report]"
    assert pending["input_bound"] == {"input_tokens": 167639, "cache_write": 32869, "cache_read": 0}
    assert sum(pending["input_bound"].values()) == _sent(report)


def test_pending_regate_bound_is_the_report_request_with_the_report_it_rejected(tmp_path):
    _, ledger = _fixture_ledger(RUN_20A)
    *settled, regate = ledger["rows"]
    ledger_path = _lay_out_run(tmp_path, RUN_20A, rows=settled, pending=_call(regate),
                               through="CHORUS_report_before_regate.md")
    pending = compute_readout(ledger_path)["pending_call"]
    assert pending["input_bound"] == {"input_tokens": 167639 + 162181, "cache_write": 32869, "cache_read": 0}
    assert pending["input_bound_source"] == (
        "derived[report_regate]: measured[report] + 162,181 bytes (report_before_regate.md)")
    assert sum(pending["input_bound"].values()) >= _sent(regate)


def test_a_completed_call_known_only_from_its_reasoning_entry_is_priced(tmp_path):
    """A reasoning entry whose usage_id no ledger row carries adds its output tokens."""
    _, ledger = _fixture_ledger(RUN_22A)
    *settled, report = ledger["rows"]
    ledger_path = _lay_out_run(tmp_path, RUN_22A, rows=settled, reasoning=True)
    summary = compute_readout(ledger_path)
    assert summary["settled_dollars"] == pytest.approx(
        price_settled_rows(settled) + 2.78120375 + report["output_tokens"] * 25e-6, abs=1e-8)


def test_shared_generation_2_routing_request_count_pin_is_used(tmp_path, monkeypatch):
    """Shared generation 2 journals each admitted ordinary request under
    `source_heading_admissions.rows`, carrying both `count.input_tokens` and
    `payload.max_tokens` before dispatch."""
    meta = tmp_path / "run_sg2"
    inter = meta / "intermediate"
    inter.mkdir(parents=True)
    req_path = inter / "CHORUS_full_routing_request.json"
    req_bytes = json.dumps({
        "generation_id": "c" * 32,
        "registration_sha256": "d" * 64,
        "phase": "full",
        "attempt": 1,
        "prior_usage_ids": [],
        "count": {
            "input_tokens": 74185,
            "context_limit_tokens": 1000000,
        },
        "payload": {
            "model": "anthropic/claude-opus-4-7",
            "max_tokens": 128000,
            "messages": [{"role": "user", "content": "..."}],
        },
    }, sort_keys=True).encode("utf-8")
    req_path.write_bytes(req_bytes)
    req_sha = hashlib.sha256(req_bytes).hexdigest()

    # Also verify that a stale file of the same relative path in CWD does not
    # shadow the hash-verified file under metadata_dir (R4 gen F6 / N8).
    cwd_dir = tmp_path / "other_cwd"
    (cwd_dir / "intermediate").mkdir(parents=True)
    (cwd_dir / "intermediate" / "CHORUS_full_routing_request.json").write_text(
        json.dumps({"count": {"input_tokens": 999}, "payload": {"max_tokens": 1000}}),
        encoding="utf-8",
    )
    monkeypatch.chdir(cwd_dir)

    ledger_file = meta / "CHORUS_api_usage_sg2.json"
    ledger_file.write_text(json.dumps({
        "version": 1,
        "identity": {"project": "CHORUS", "label": "sg2_test", "condition": "generic_v10"},
        "generation_id": "c" * 32,
        "rows": [],
        "source_heading_admissions": {
            "rows": [
                {
                    "phase": "full",
                    "attempt": 1,
                    "request": {"path": "intermediate/CHORUS_full_routing_request.json", "sha256": req_sha},
                    "usage_id": None,
                    "response": None,
                }
            ]
        },
        "pending_call": {"phase": "full", "attempt": 1, "started_at": "2026-10-25T00:00:00Z"},
    }), encoding="utf-8")

    summary = compute_readout(ledger_file)
    pending = summary["pending_call"]
    assert pending["input_bound"] == 74185
    assert pending["input_bound_source"] == "CHORUS_full_routing_request.json"
    assert pending["output_cap_tokens"] == 128000
    assert pending["input_bound_static"] is False
    assert summary["pending_input_bound_static"] is False
    assert "WARNING:" not in format_readout(summary)


def test_derived_bound_is_capped_at_the_context_window_less_max_tokens(tmp_path):
    """A derived input bound (`measured[full] + carried bytes`) cannot exceed the
    room the context window leaves beside `max_tokens` (`window - max_tokens`)."""
    _, ledger = _fixture_ledger(RUN_22A)
    *settled, report = ledger["rows"]
    ledger_path = _lay_out_run(tmp_path, RUN_22A, rows=settled, pending=_call(report),
                               through="CHORUS_reconcile_core.yaml")
    # Uncapped derived report bound on 10-22a is 336,135 tokens (303,266 uncached + 32,869 cache_write),
    # with report fallback output_cap_tokens = 96,000.
    # Under a 350,000-token window, window - max_tokens = 254,000 (cutting uncached input_tokens by 82,135).
    reg_350k = {"audit_limits": {"context_limit_tokens": 350000}}
    summary = compute_readout(ledger_path, registration=reg_350k)
    pending = summary["pending_call"]
    assert sum(pending["input_bound"].values()) == 350000 - 96000 == 254000
    assert pending["input_bound"] == {
        "input_tokens": 254000 - 32869,
        "cache_write": 32869,
        "cache_read": 0,
    }
    assert pending["input_bound_source"].endswith("; capped at the 350,000-token window less 96,000 max_tokens")

    # When window - max_tokens is smaller than cache_write alone (e.g. window = 116,000 -> cap = 20,000),
    # input_tokens is reduced to 0 and cache_write is clamped to 20,000 (R11-F2).
    reg_116k = {"routing": {"generation_limits": {"context_limit_tokens": 116000}}}
    summary_tight = compute_readout(ledger_path, registration=reg_116k)
    pending_tight = summary_tight["pending_call"]
    assert pending_tight["input_bound"] == {"input_tokens": 0, "cache_write": 20000, "cache_read": 0}
    assert sum(pending_tight["input_bound"].values()) == 20000

    # Without a registration, the window recorded in this generation's typed_audit stage context is used.
    raw_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    stage_ctx_path = ledger_path.parent / "intermediate" / "CHORUS_typed_audit_worker_context.json"
    stage_bytes = json.dumps({"input_tokens": 1000, "context_limit_tokens": 350000}).encode("utf-8")
    stage_ctx_path.write_bytes(stage_bytes)
    raw_ledger["typed_audit"] = {
        "stages": [
            {
                "context": {
                    "path": str(stage_ctx_path),
                    "sha256": hashlib.sha256(stage_bytes).hexdigest(),
                }
            }
        ]
    }
    ledger_path.write_text(json.dumps(raw_ledger, indent=2) + "\n", encoding="utf-8")

    summary_from_pin = compute_readout(ledger_path)
    assert sum(summary_from_pin["pending_call"]["input_bound"].values()) == 254000
    assert summary_from_pin["pending_call"]["input_bound_source"].endswith(
        "; capped at the 350,000-token window less 96,000 max_tokens"
    )


def test_static_baseline_bound_is_flagged_with_warning(tmp_path):
    """When no count pin or measured request exists yet, the static project baseline
    is flagged with `input_bound_static = True` and a display warning (#5117)."""
    ledger = {
        "version": 1,
        "identity": {"project": "CHORUS", "label": "test_static_warn", "condition": "generic_v10"},
        "rows": [],
        "pending_call": {"phase": "full", "attempt": 1},
    }
    summary = compute_readout(ledger, project="CHORUS")
    assert summary["pending_input_bound_static"] is True
    assert summary["pending_call"]["input_bound_static"] is True
    formatted = format_readout(summary)
    assert (
        "WARNING: pending full input is a static baseline from earlier runs "
        "(baseline[CHORUS][full]); it may be low for this run"
    ) in formatted

    # An unmeasured abandoned attempt that falls back to baseline[CHORUS][full] also warns (N8).
    meta = tmp_path / "run_abandoned_static"
    meta.mkdir()
    (meta / "CHORUS_abandoned_attempts.jsonl").write_text(
        json.dumps({"phase": "full", "usage_id": "u_aband_1", "generation_id": "g1"}) + "\n",
        encoding="utf-8",
    )
    ledger_file = meta / "CHORUS_api_usage.json"
    ledger_file.write_text(
        json.dumps({
            "version": 1,
            "generation_id": "g1",
            "identity": {"project": "CHORUS", "label": "test_static_warn", "condition": "generic_v10"},
            "rows": [],
        }),
        encoding="utf-8",
    )
    aband_summary = compute_readout(ledger_file)
    assert aband_summary["abandoned_input_bound_static"] is True
    assert aband_summary["abandoned_attempts"][0]["input_bound_static"] is True
    assert (
        "WARNING: abandoned full input is a static baseline from earlier runs "
        "(baseline[CHORUS][full]); it may be low for this run"
    ) in format_readout(aband_summary)

