"""Why a run has no reasoning log — three answers, not one (#400).

`d4d provenance reasoning` printed a single message for every empty case, which
conflated a runtime limit, an unrecoverable gap, and a defect. They license
completely different responses, and only the third is worth chasing.

The distinction matters most where arms are compared: a run with no log has not
spent zero reasoning, it has no measurement.
"""

import unittest

from data_sheets_schema.reasoning import (
    CAPTURE_FROM,
    HAS_LOG,
    NO_LOG_MISSING,
    NO_LOG_PREDATES,
    NO_LOG_RUNTIME,
    log_status,
)


class TestLogStatus(unittest.TestCase):
    def test_an_existing_log_is_present_whatever_the_runtime(self):
        for runtime in ("Claude Code", "Claude API (direct)", None):
            with self.subTest(runtime=runtime):
                self.assertEqual(
                    log_status(runtime, "2026-08-07_x_rep1", True), HAS_LOG)

    def test_an_agentic_run_cannot_capture(self):
        """No log can exist: a subagent has no access to its token accounting.

        Not a gap to fill. A log carrying only the effort level would look
        comparable with the API path's and would not be — the substitution
        #400 argues against.
        """
        self.assertEqual(
            log_status("Claude Code", "2026-08-07_x_rep1", False),
            NO_LOG_RUNTIME)

    def test_the_runtime_check_is_case_and_space_insensitive(self):
        for spelling in ("claude code", "  Claude Code  ", "CLAUDE CODE"):
            with self.subTest(spelling=spelling):
                self.assertEqual(
                    log_status(spelling, "2026-08-07_x_rep1", False),
                    NO_LOG_RUNTIME)

    def test_an_api_run_before_capture_is_unrecoverable(self):
        self.assertEqual(
            log_status("Claude API (direct)", "2026-07-29_x_rep1", False),
            NO_LOG_PREDATES)

    def test_an_api_run_after_capture_with_no_log_is_a_defect(self):
        """The only one of the three worth chasing."""
        self.assertEqual(
            log_status("Claude API (direct)", "2026-08-05_x_rep1", False),
            NO_LOG_MISSING)

    def test_the_boundary_is_inclusive_of_the_capture_date(self):
        """A run *on* CAPTURE_FROM should have written one."""
        self.assertEqual(
            log_status("Claude API (direct)", f"{CAPTURE_FROM}_x_rep1", False),
            NO_LOG_MISSING)
        earlier = "2026-07-30"
        self.assertLess(earlier, CAPTURE_FROM)
        self.assertEqual(
            log_status("Claude API (direct)", f"{earlier}_x_rep1", False),
            NO_LOG_PREDATES)

    def test_an_unknown_runtime_is_not_excused_as_a_runtime_limit(self):
        """Only Claude Code is known to be unable to capture.

        Treating an unrecorded runtime as incapable would quietly absolve a
        real defect, which is the direction that loses information.
        """
        self.assertEqual(
            log_status(None, "2026-08-05_x_rep1", False), NO_LOG_MISSING)


class TestAgainstTheRealCorpus(unittest.TestCase):
    def test_no_api_run_after_capture_is_missing_its_log(self):
        """0 missing today: every empty case is a limit, not a defect.

        Fails if an API run lands without a log, which is the condition this
        classification exists to make visible.
        """
        from pathlib import Path

        import yaml

        from data_sheets_schema.api_runner import CONCAT_DIR
        from data_sheets_schema.provenance import record_path_for
        from data_sheets_schema.runs import discover

        if not Path("data/d4d_concatenated").exists():
            self.skipTest("corpus absent")

        missing = []
        for run in discover():
            if run.is_core or run.deterministic:
                continue
            for project in run.projects:
                log = (CONCAT_DIR / f"{run.method}_core" / run.label /
                       f"{project}_reasoning.jsonl")
                rec = record_path_for(project, run.method, run.label)
                runtime = None
                if rec.exists():
                    try:
                        data = yaml.safe_load(rec.read_text("utf-8")) or {}
                        runtime = (data.get("model") or {}).get("agent_runtime")
                    except Exception:            # noqa: BLE001
                        runtime = None
                if log_status(runtime, run.label, log.exists()) == NO_LOG_MISSING:
                    missing.append(f"{run.label}/{project}")
        self.assertEqual(missing, [])
