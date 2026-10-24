"""D-C (owner decision 2026-10-23): generic_v10 report and reconcile output room.

The 2026-10-22a CHORUS canary's report used 83,367 of its 96,000-token cap.
Shared generation 1 raises the report (and its regate) and reconcile_full to
the route ceiling; every other renderer keeps its recorded budget, and the
dollar readout's worst-case bound follows the same caps.
"""
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


def test_readout_mirrors_the_runner_caps():
    reg = {"format": sg.FORMAT}
    assert dr.SHARED_V1_FORMAT == sg.FORMAT
    for phase in ("report", "report_regate", "reconcile_full"):
        runner_phase = "report" if phase == "report_regate" else phase  # the regate shares the report budget
        assert dr.get_phase_output_cap(phase, registration=reg) == api.SHARED_PHASE_MAX_TOKENS[runner_phase]
    assert dr.get_phase_output_cap("report") == dr.CAP_REPORT_FAMILY == 96000
    assert dr.get_phase_output_cap("repair_full", registration=reg) == dr.CAP_REPORT_FAMILY


def test_pending_v10_report_worst_case_uses_the_raised_cap():
    ledger = {"version": 1, "identity": {"project": "CHORUS", "label": "dc_caps"}, "rows": [],
              "pending_call": {"phase": "report", "attempt": 1}}
    summary = dr.compute_readout(ledger, project="CHORUS", registration={"format": sg.FORMAT})
    assert summary["pending_call"]["output_cap_tokens"] == 128000
