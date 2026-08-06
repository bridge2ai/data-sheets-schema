"""Tests for the run-telemetry collector and its schema."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.run_telemetry import (
    SCHEMA_PATH,
    SCHEMA_VERSION,
    _evaluations_for,
    collect_report,
    comparisons,
    run_telemetry,
)

REPO = Path(__file__).resolve().parents[1]


def _seed_run(root: Path, label: str, project: str) -> Path:
    """A synthetic run: two invocations, an audit retry, one repair round."""
    core_dir = root / "claudecode_agent_core" / label
    full_dir = root / "claudecode_agent" / label
    core_dir.mkdir(parents=True)
    full_dir.mkdir(parents=True)
    (full_dir / f"{project}_d4d.yaml").write_text("id: x\n")
    (core_dir / f"{project}_d4d_core.yaml").write_text("id: x\n")
    (core_dir / f"{project}_reconciliation.md").write_text("# ok\n")

    def row(phase, attempt, started, out_tok=100, stop="end_turn"):
        return {"phase": phase, "attempt": attempt, "started_at": started,
                "seconds": 10.0, "input_tokens": 50, "output_tokens": out_tok,
                "cache_read": 5, "cache_write": 7, "max_tokens": 96000,
                "stop_reason": stop}

    # Two invocations: a >6 min gap sits between the report row and the
    # repair row. The audit needed two attempts.
    usage = [
        row("full", 1, "2026-08-05T20:00:00+00:00"),
        row("core", 1, "2026-08-05T20:05:00+00:00"),
        row("audit", 1, "2026-08-05T20:10:00+00:00", stop="max_tokens"),
        row("audit", 2, "2026-08-05T20:12:00+00:00"),
        row("report", 1, "2026-08-05T20:15:00+00:00"),
        row("repair_full", 1, "2026-08-05T21:00:00+00:00"),
    ]
    prov = {
        "record_generated_at": "2026-08-05T21:10:00+00:00",
        "run": {"label": label, "project": project,
                "method": "claudecode_agent", "arm": "BASELINE",
                "replicate": 1},
        "model": {"model": "claude-opus-5", "provider": "LBL CBORG"},
        "api_usage": usage,
        "repair": [{"phase": "repair_full", "round": 1,
                    "outcome": "applied", "findings": 12}],
        "validation": {"problems": []},
    }
    (core_dir / f"{project}_provenance.yaml").write_text(
        yaml.safe_dump(prov), encoding="utf-8")
    reasoning = [
        {"phase": "full", "attempt": 1, "reasoning_tokens_estimate": 40,
         "visible_text_chars": 240, "reasoning_present": True,
         "reasoning_available": False},
        {"phase": "core", "attempt": 1, "reasoning_tokens_estimate": 10,
         "visible_text_chars": 360},
        {"phase": "audit", "attempt": 1, "reasoning_tokens_estimate": 5,
         "visible_text_chars": 100},
        {"phase": "audit", "attempt": 2, "reasoning_tokens_estimate": 6,
         "visible_text_chars": 120},
        {"phase": "report", "attempt": 1, "reasoning_tokens_estimate": 3,
         "visible_text_chars": 90},
        {"phase": "repair_full", "attempt": 1,
         "reasoning_tokens_estimate": 2, "visible_text_chars": 80},
    ]
    (core_dir / f"{project}_reasoning.jsonl").write_text(
        "\n".join(json.dumps(e) for e in reasoning) + "\n", encoding="utf-8")
    return core_dir


class TestRunTelemetry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_dir = _seed_run(self.root, "2026-08-05_test_rep1", "CHORUS")

    def test_recorded_timing_and_invocations(self):
        t = run_telemetry(self.run_dir, "CHORUS")
        self.assertEqual(t["timing_basis"], "recorded")
        self.assertEqual(t["wall_seconds_estimate"], 60.0)
        # The >6 min gap before the repair row marks a second invocation.
        self.assertEqual(t["invocations"], 2)

    def test_attempts_join_reasoning_by_occurrence(self):
        t = run_telemetry(self.run_dir, "CHORUS")
        audit = next(p for p in t["phases"] if p["phase"] == "audit")
        self.assertEqual(len(audit["attempts"]), 2)
        self.assertEqual(audit["attempts"][0]["stop_reason"], "max_tokens")
        self.assertEqual(audit["attempts"][0]["reasoning_tokens_estimate"], 5)
        self.assertEqual(audit["attempts"][1]["reasoning_tokens_estimate"], 6)
        full = next(p for p in t["phases"] if p["phase"] == "full")
        self.assertIs(full["attempts"][0]["reasoning_present"], True)
        self.assertIs(full["attempts"][0]["reasoning_available"], False)

    def test_totals_repair_and_validation_state(self):
        t = run_telemetry(self.run_dir, "CHORUS")
        self.assertEqual(t["validation_state"], "valid")
        self.assertEqual(t["validation_problem_count"], 0)
        self.assertEqual(t["total_output_tokens"], 600)
        self.assertEqual(t["total_reasoning_tokens_estimate"], 66)
        self.assertEqual(t["repair_rounds"],
                         [{"artifact": "full", "round": 1,
                           "outcome": "applied", "findings": 12}])

    def test_missing_provenance_returns_none(self):
        self.assertIsNone(run_telemetry(self.run_dir, "NOPE"))

    def test_record_stats_carry_file_and_content_figures(self):
        t = run_telemetry(self.run_dir, "CHORUS")
        stats = {s["artifact"]: s for s in t["records"]}
        self.assertEqual(set(stats), {"full", "core", "report"})
        self.assertEqual(stats["full"]["root_slot_count"], 1)
        self.assertEqual(stats["full"]["populated_root_slot_count"], 1)
        self.assertEqual(len(stats["full"]["sha256"]), 64)
        # The report is markdown: file figures only, no content claims.
        self.assertNotIn("root_slot_count", stats["report"])

    def test_comparisons_need_two_values_and_stay_mechanical(self):
        t = run_telemetry(self.run_dir, "CHORUS")
        self.assertEqual(comparisons([t]), [],
                         "a single run compares nothing")
        t2 = dict(t, project="AI_READI")
        comp = {c["metric"]: c for c in comparisons([t, t2])}
        self.assertIn("total_output_tokens", comp)
        self.assertEqual(len(comp["total_output_tokens"]["values"]), 2)
        full = comp["full_phase_output_tokens"]["values"][0]
        self.assertEqual(full["value"], 100.0)

    def test_evaluations_attach_on_exact_path_match_only(self):
        scores = self.root / "scores.json"
        core_path = self.run_dir / "CHORUS_d4d_core.yaml"
        scores.write_text(json.dumps([
            {"project": "CHORUS", "file_path": str(core_path),
             "timestamp": "2026-08-06T00:00:00",
             "rubric10": {"total": 34, "max": 50, "percentage": 68.0}},
            {"project": "CHORUS",
             "file_path": "data/d4d_concatenated/claudecode_agent_core/CHORUS_d4d_core.yaml",
             "rubric10": {"total": 10, "max": 50}},
        ]))
        got = _evaluations_for({"core": core_path}, scores, "presence")
        self.assertEqual(len(got), 1, "the label-less legacy path must not "
                                      "attach to a label-addressed run")
        self.assertEqual(got[0]["score"], 34.0)
        self.assertEqual(got[0]["artifact"], "core")
        self.assertEqual(got[0]["evaluation_type"], "presence")

    def test_hollow_counting_is_maximal_and_keeps_falsy_values(self):
        from data_sheets_schema.run_telemetry import count_hollows
        record = {
            "a": "text",
            "b": None,                          # hollow
            "c": {"x": None, "y": "", "z": []},  # one hollow object, not 3
            "d": [{"name": "real"}, {"name": "  "}],  # one hollow member
            "e": 0,                             # a value, not a hollow
            "f": False,                         # a value, not a hollow
            "g": ["", None],                    # hollow list, counts once
        }
        self.assertEqual(count_hollows(record), 4)
        self.assertEqual(count_hollows({"a": 1}), 0)
        self.assertEqual(count_hollows({}), 1)

    def test_record_stats_report_nested_hollows(self):
        (self.run_dir.parent.parent / "claudecode_agent" /
         "2026-08-05_test_rep1" / "CHORUS_d4d.yaml").write_text(
            "id: x\nok: v\nempty: null\nobj:\n  a: null\n  b: ''\n")
        t = run_telemetry(self.run_dir, "CHORUS")
        full = next(s for s in t["records"] if s["artifact"] == "full")
        self.assertEqual(full["root_slot_count"], 4)
        self.assertEqual(full["populated_root_slot_count"], 2)
        self.assertEqual(full["hollow_value_count"], 2)

    def test_findings_pass_through_to_the_report(self):
        finding = {"topic": "test", "kind": "observation",
                   "claim": "the fixture ran", "evidence": "this test"}
        report = collect_report("2026-08-05_test", root=self.root,
                                findings=[finding])
        self.assertEqual(report["findings"], [finding])

    def test_report_validates_against_the_schema(self):
        report = collect_report(
            "2026-08-05_test", root=self.root,
            findings=[{"topic": "fixture", "kind": "interpretation",
                       "claim": "synthetic data behaves",
                       "evidence": "this suite",
                       "relates_to": ["#369"]}])
        self.assertEqual(len(report["runs"]), 1)
        self.assertIn("records", report["runs"][0])
        self.assertEqual(report["schema_version"], SCHEMA_VERSION)
        out = self.root / "report.yaml"
        out.write_text(yaml.safe_dump(report, sort_keys=False),
                       encoding="utf-8")
        res = subprocess.run(
            ["poetry", "run", "linkml-validate",
             "-s", str(REPO / SCHEMA_PATH), "-C", "RunTelemetryReport",
             str(out)],
            capture_output=True, text=True, timeout=180, cwd=REPO)
        self.assertEqual(res.returncode, 0,
                         (res.stdout + res.stderr)[:800])


if __name__ == "__main__":
    unittest.main()
