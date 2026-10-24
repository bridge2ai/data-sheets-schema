"""D-C (owner decision 2026-10-23): generic_v10 report and reconcile output room.

The 2026-10-22a CHORUS canary's report used 83,367 of its 96,000-token cap.
Shared generation 1 raises the report (and its regate) and reconcile_full to
the route ceiling; every other renderer keeps its recorded budget, and the
dollar readout's worst-case bound follows the same caps.
"""
import hashlib
import json
from types import SimpleNamespace

import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema import dollar_readout as dr
from data_sheets_schema import shared_generation as sg


def _spec(shared, render=25):
    return SimpleNamespace(shared_generation_version=shared, render_version=render, condition="generic_v10")


@pytest.mark.parametrize("phase", ["report", "reconcile_full"])
def test_shared_v1_report_and_reconcile_get_the_route_ceiling(phase):
    assert api.phase_max_tokens(_spec(1), phase, 16000, model="claude-opus-5") == 128000


@pytest.mark.parametrize("phase", ["report", "reconcile_full"])
def test_unshared_renderers_keep_their_recorded_budget(phase):
    assert api.phase_max_tokens(_spec(0, render=12), phase, 16000, model="claude-opus-5") == 96000


def test_shared_v1_leaves_other_phases_alone():
    assert api.phase_max_tokens(_spec(1), "repair_full", 16000, model="claude-opus-5") == api.PHASE_MAX_TOKENS["repair_full"]
    assert api.phase_max_tokens(_spec(1), "core", 16000, model="claude-opus-5") == api.PHASE_MAX_TOKENS["core"]


def test_route_limit_still_clamps(monkeypatch):
    monkeypatch.setitem(api.MODEL_OUTPUT_LIMIT, "small-offline-route", 64000)
    assert api.phase_max_tokens(_spec(1), "report", 16000, model="small-offline-route") == 64000


# Which runner budget each readout phase is sent with: the regate and the
# report after repair share the report budget.
RUNNER_PHASE = {"report_regate": "report", "report_after_repair": "report"}


@pytest.mark.parametrize("phase", sorted(set(dr.PHASE_OUTPUT_CAPS) - {"full_readdress"}))
def test_readout_mirrors_the_runner_cap_for_every_phase(phase):
    reg = {"format": sg.FORMAT}
    assert dr.SHARED_V1_FORMAT == sg.FORMAT
    runner = api.phase_max_tokens(_spec(1), RUNNER_PHASE.get(phase, phase), 16000, model="claude-opus-5")
    assert dr.get_phase_output_cap(phase, registration=reg) == runner


def test_readout_without_a_v10_registration_keeps_the_historical_caps():
    assert dr.get_phase_output_cap("report") == dr.CAP_REPORT_FAMILY == 96000
    assert dr.get_phase_output_cap("report", registration={"format": "something_else"}) == 96000


def _v10_ledger(**extra):
    raw = json.dumps({"format": sg.FORMAT, "audit_limits": {"worker_output_tokens": 64000}})
    pin = {"sha256": hashlib.sha256(raw.encode()).hexdigest(), "raw_json": raw}
    return {"version": 1, "identity": {"project": "CHORUS", "label": "dc_caps"}, "rows": [],
            "input_identity": {"shared_generation": {"registration": pin}}, **extra}


def test_the_readout_finds_a_v10_ledgers_registration_itself():
    """The operator CLI passes no registration; the ledger's pinned bytes select the v10 caps."""
    summary = dr.compute_readout(_v10_ledger(pending_call={"phase": "report", "attempt": 1}), project="CHORUS")
    assert summary["pending_call"]["output_cap_tokens"] == 128000
    tampered = _v10_ledger(pending_call={"phase": "report", "attempt": 1})
    tampered["input_identity"]["shared_generation"]["registration"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="differs from its sha256"):
        dr.compute_readout(tampered, project="CHORUS")


def test_pending_v10_report_worst_case_uses_the_raised_cap():
    ledger = {"version": 1, "identity": {"project": "CHORUS", "label": "dc_caps"}, "rows": [],
              "pending_call": {"phase": "report", "attempt": 1}}
    summary = dr.compute_readout(ledger, project="CHORUS", registration={"format": sg.FORMAT})
    assert summary["pending_call"]["output_cap_tokens"] == 128000


def test_an_abandoned_attempt_is_priced_at_the_cap_it_recorded(tmp_path):
    """Two abandoned report attempts that differ only in their recorded max_tokens differ by exactly that output."""
    def settled(max_tokens):
        run_dir = tmp_path / f"cap{max_tokens}"
        run_dir.mkdir()
        (run_dir / "CHORUS_api_usage_x.json").write_text(json.dumps(_v10_ledger()), encoding="utf-8")
        (run_dir / "CHORUS_abandoned_attempts.jsonl").write_text(
            json.dumps({"phase": "report", "attempt": 1, "usage_id": "u1", "max_tokens": max_tokens}) + "\n",
            encoding="utf-8")
        return dr.compute_readout(run_dir / "CHORUS_api_usage_x.json", project="CHORUS")["settled_dollars"]
    assert abs((settled(60000) - settled(50000)) - 10000 * 25e-6) < 1e-9

