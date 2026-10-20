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
