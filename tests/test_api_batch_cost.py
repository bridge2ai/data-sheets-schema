"""Tests for the cumulative dollar cap on `d4d api batch` (Step A2c / #4829, #4830).

`d4d api batch` accepts `--max-cost-dollars <FLOAT>`.
- Rejects negative values at CLI entry.
- Calculates per-run and cumulative spend using the rates in `run_telemetry`.
- Reports cumulative cost in each per-run output and in the final summary.
- Stops between runs when cumulative spent meets or exceeds `--max-cost-dollars`,
  releasing the lock cleanly and exiting with an informative ClickException.
- Completes without error if the cap is met on the very last run of the batch.
- Halts further runs even under `--continue-on-error` when validation errors occur.
"""

import inspect
import unittest
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from data_sheets_schema.cli import cli
from data_sheets_schema.cli.api import batch_cmd


class ApiBatchCostValidationTest(unittest.TestCase):
    """CLI option registration and argument validation."""

    def test_max_cost_dollars_option_exists_on_batch_cmd(self):
        opts = {param.name: param for param in batch_cmd.params}
        self.assertIn("max_cost_dollars", opts)
        self.assertEqual(opts["max_cost_dollars"].type.name, "float")

    def test_negative_max_cost_dollars_is_rejected(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "api",
                "batch",
                "--label-prefix", "2026-10-11_claude-opus-5-api-generic-test",
                "--max-cost-dollars", "-1.50",
            ],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--max-cost-dollars must be positive", result.output)

    def test_negative_small_fraction_is_rejected(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "api",
                "batch",
                "--label-prefix", "2026-10-11_claude-opus-5-api-generic-test",
                "--max-cost-dollars", "-0.01",
            ],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--max-cost-dollars must be positive", result.output)

    def test_non_finite_max_cost_dollars_is_rejected(self):
        runner = CliRunner()
        for bad in ("nan", "inf", "-inf"):
            with self.subTest(bad=bad):
                result = runner.invoke(
                    cli,
                    [
                        "api",
                        "batch",
                        "--label-prefix", "2026-10-11_claude-opus-5-api-generic-test",
                        "--max-cost-dollars", bad,
                    ],
                )
                self.assertNotEqual(result.exit_code, 0)
                self.assertIn("--max-cost-dollars must be positive", result.output)


class ApiBatchCostStopTest(unittest.TestCase):
    """Stopping behavior between runs when the cumulative cap is met."""

    def _dummy_plan(self, spec):
        return {
            "approx_total_input_tokens": 1000,
            "model": {"name": "claude-opus-5", "temperature": 0.0, "max_tokens": 1000},
            "phases": [],
        }

    def _make_mock_execute(self, cost_per_run_dollars=1.0, validation_problems=None):
        # RATE_INPUT is 5e-6, RATE_OUTPUT is 25e-6.
        # 100,000 input tokens = $0.50; 20,000 output tokens = $0.50 -> $1.00 total.
        input_tokens = int((cost_per_run_dollars * 0.5) / 5e-6)
        output_tokens = int((cost_per_run_dollars * 0.5) / 25e-6)

        def mock_execute(spec):
            return {
                "project": spec.project,
                "label": spec.label,
                "usage": [
                    {
                        "phase": "full",
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cache_read": 0,
                        "cache_write": 0,
                    }
                ],
                "skipped": [],
                "validation_problems": validation_problems or [],
                "checks": {
                    "pair": {"ran": True, "errors": 0},
                    "report": {"checked": True, "findings": []},
                    "grounding": {"checked": True, "distinct": {"absent": 0}},
                    "form": {
                        "checked": True,
                        "organisational_fragments": 0,
                        "undeclared_prefix_occurrences": 0,
                        "british_spellings": 0,
                    },
                },
                "outputs": {"full": "full.yaml", "core": "core.yaml", "provenance": None},
                "already_complete": False,
            }

        return MagicMock(side_effect=mock_execute)

    @patch("data_sheets_schema.cli.api._require_bundle")
    @patch("data_sheets_schema.cli.api._plan_or_refuse")
    def test_cost_stop_stops_before_subsequent_runs(self, mock_plan, mock_bundle):
        mock_plan.side_effect = self._dummy_plan
        mock_bundle.return_value = None

        mock_exec = self._make_mock_execute(cost_per_run_dollars=1.0)
        with patch("data_sheets_schema.api_runner.execute", mock_exec):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "api",
                    "batch",
                    "--projects", "AI_READI",
                    "--replicates", "3",
                    "--arm", "baseline",
                    "--condition", "generic",
                    "--label-prefix", "2026-10-11_claude-opus-5-api-generic-testcost1",
                    "--allow-condition-mismatch",
                    "--yes",
                    "--no-branch-guard",
                    "--no-canary-gate",
                    "--max-cost-dollars", "1.50",
                ],
            )

        # 3 replicates scheduled.
        # Run 1 costs $1.00 (spent $1.00 < $1.50).
        # Run 2 costs $1.00 (spent $2.00 >= $1.50).
        # Should stop before run 3 launches!
        self.assertEqual(mock_exec.call_count, 2)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("cost=$1.00", result.output)
        self.assertIn("cost=$2.00", result.output)
        self.assertIn("2 succeeded, 0 failed", result.output)
        self.assertIn("(cost: $2.00)", result.output)
        self.assertIn(
            "cumulative cost stop: spent $2.00 >= $1.50 cap. Remaining runs were stopped.",
            result.output,
        )

    @patch("data_sheets_schema.cli.api._require_bundle")
    @patch("data_sheets_schema.cli.api._plan_or_refuse")
    def test_cap_met_on_final_run_completes_without_error(self, mock_plan, mock_bundle):
        mock_plan.side_effect = self._dummy_plan
        mock_bundle.return_value = None

        mock_exec = self._make_mock_execute(cost_per_run_dollars=1.0)
        with patch("data_sheets_schema.api_runner.execute", mock_exec):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "api",
                    "batch",
                    "--projects", "AI_READI",
                    "--replicates", "2",
                    "--arm", "baseline",
                    "--condition", "generic",
                    "--label-prefix", "2026-10-11_claude-opus-5-api-generic-testcost2",
                    "--allow-condition-mismatch",
                    "--yes",
                    "--no-branch-guard",
                    "--no-canary-gate",
                    "--max-cost-dollars", "1.50",
                ],
            )

        # 2 replicates scheduled, both executed. Cap is met on run 2, which is
        # the last run (i == len(specs)), so no runs were stopped.
        self.assertEqual(mock_exec.call_count, 2)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("2 succeeded, 0 failed", result.output)
        self.assertIn("(cost: $2.00)", result.output)
        self.assertNotIn("Remaining runs were stopped", result.output)

    @patch("data_sheets_schema.cli.api._require_bundle")
    @patch("data_sheets_schema.cli.api._plan_or_refuse")
    def test_under_budget_completes_all_runs_with_cost_summary(self, mock_plan, mock_bundle):
        mock_plan.side_effect = self._dummy_plan
        mock_bundle.return_value = None

        mock_exec = self._make_mock_execute(cost_per_run_dollars=0.25)
        with patch("data_sheets_schema.api_runner.execute", mock_exec):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "api",
                    "batch",
                    "--projects", "AI_READI",
                    "--replicates", "3",
                    "--arm", "baseline",
                    "--condition", "generic",
                    "--label-prefix", "2026-10-11_claude-opus-5-api-generic-testcost3",
                    "--allow-condition-mismatch",
                    "--yes",
                    "--no-branch-guard",
                    "--no-canary-gate",
                    "--max-cost-dollars", "5.00",
                ],
            )

        self.assertEqual(mock_exec.call_count, 3)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("3 succeeded, 0 failed", result.output)
        self.assertIn("(cost: $0.75)", result.output)
        self.assertNotIn("Remaining runs were stopped", result.output)

    @patch("data_sheets_schema.cli.api._require_bundle")
    @patch("data_sheets_schema.cli.api._plan_or_refuse")
    def test_continue_on_error_does_not_bypass_cost_cap(self, mock_plan, mock_bundle):
        mock_plan.side_effect = self._dummy_plan
        mock_bundle.return_value = None

        mock_exec = self._make_mock_execute(
            cost_per_run_dollars=2.0,
            validation_problems=[{"artifact": "full", "error": "missing field"}],
        )
        with patch("data_sheets_schema.api_runner.execute", mock_exec):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "api",
                    "batch",
                    "--projects", "AI_READI",
                    "--replicates", "3",
                    "--arm", "baseline",
                    "--condition", "generic",
                    "--label-prefix", "2026-10-11_claude-opus-5-api-generic-testcost4",
                    "--allow-condition-mismatch",
                    "--yes",
                    "--no-branch-guard",
                    "--no-canary-gate",
                    "--continue-on-error",
                    "--max-cost-dollars", "1.50",
                ],
            )

        # Run 1 has validation problems, but spent $2.00 >= $1.50 cap.
        # Despite --continue-on-error, it must NOT launch run 2.
        self.assertEqual(mock_exec.call_count, 1)
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("❌ invalid output (1 failure(s))", result.output)
        self.assertIn("cost=$2.00", result.output)
        self.assertIn("0 succeeded, 1 failed", result.output)
        self.assertIn("(cost: $2.00)", result.output)
        self.assertIn(
            "cumulative cost stop: spent $2.00 >= $1.50 cap. Remaining runs were stopped.",
            result.output,
        )


class ApiBatchCostStructureTest(unittest.TestCase):
    """Source inspection guarantees control flow and lock invariants."""

    def _source(self):
        return inspect.getsource(batch_cmd.callback)

    def test_run_lock_released_exactly_once(self):
        """Releasing twice or not at all permanently corrupts lock state."""
        self.assertEqual(self._source().count("run_lock.release(lock_path)"), 1)

    def test_lock_release_precedes_cost_stop_exception(self):
        src = self._source()
        release_idx = src.index("run_lock.release(lock_path)")
        stop_raise_idx = src.index("raise click.ClickException(canary_stop)")
        self.assertLess(release_idx, stop_raise_idx)

    def test_cost_stop_routes_through_canary_stop_raise(self):
        src = self._source()
        self.assertIn("canary_stop = cost_stop", src)
        self.assertIn("if canary_stop:\n        raise click.ClickException(canary_stop)", src)


if __name__ == "__main__":
    unittest.main()


class ApiBatchCostAccountingTest(unittest.TestCase):
    """#5045 review: what the cap counts — this invocation's billed attempts,
    including those of a run that raised, and none of a run's history."""

    ROW = {"phase": "full", "input_tokens": 100_000, "output_tokens": 20_000,
           "cache_read": 0, "cache_write": 0}               # $1.00

    def _invoke(self, mock_exec, billed, extra, reps="3"):
        plan = ApiBatchCostStopTest()._dummy_plan
        with patch("data_sheets_schema.cli.api._require_bundle", return_value=None), \
             patch("data_sheets_schema.cli.api._plan_or_refuse", side_effect=plan), \
             patch("data_sheets_schema.cli.api._billed_rows", side_effect=lambda spec, *a: billed(spec)), \
             patch("data_sheets_schema.api_runner.execute", mock_exec):
            return CliRunner().invoke(cli, [
                "api", "batch", "--projects", "AI_READI", "--replicates", reps, "--arm", "baseline",
                "--condition", "generic", "--label-prefix", "2026-10-17_claude-opus-5-api-generic-testcost9",
                "--allow-condition-mismatch", "--yes", "--no-branch-guard", "--no-canary-gate", *extra])

    def test_zero_cap_is_refused(self):
        result = CliRunner().invoke(cli, ["api", "batch", "--label-prefix", "x", "--max-cost-dollars", "0"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--max-cost-dollars must be positive", result.output)

    def test_a_run_that_raised_counts_the_attempts_it_persisted(self):
        on_disk: dict = {}

        def raising(spec):
            on_disk.setdefault(spec.label, {})[f"{spec.label}-u1"] = {**self.ROW, "usage_id": f"{spec.label}-u1"}
            raise RuntimeError("phase audit: retries exhausted")

        mock_exec = MagicMock(side_effect=raising)
        result = self._invoke(mock_exec, lambda spec: dict(on_disk.get(spec.label, {})),
                              ["--continue-on-error", "--max-cost-dollars", "1.50"])
        self.assertEqual(mock_exec.call_count, 2, result.output)
        self.assertIn("cumulative cost stop: spent $2.00 >= $1.50 cap", result.output)

    def test_a_run_that_raises_after_its_usage_was_counted_is_not_counted_twice(self):
        on_disk: dict = {}

        def counted_then_raises(spec):
            row = {**self.ROW, "usage_id": f"{spec.label}-u1"}
            on_disk[spec.label] = {row["usage_id"]: row}
            return {"usage": [row]}           # no "skipped": raises after the count (#5068)

        mock_exec = MagicMock(side_effect=counted_then_raises)
        result = self._invoke(mock_exec, lambda spec: dict(on_disk.get(spec.label, {})),
                              ["--continue-on-error", "--max-cost-dollars", "1.50"])
        # $1.00 per run, once: the stop comes after run 2, not after run 1 at $2.00.
        self.assertEqual(mock_exec.call_count, 2, result.output)
        self.assertIn("cumulative cost stop: spent $2.00 >= $1.50 cap", result.output)

    def test_usage_spent_before_this_invocation_is_not_counted(self):
        old = {**self.ROW, "output_tokens": 60_000, "usage_id": "old"}     # $2.00 of history

        def resumed(spec):
            res = ApiBatchCostStopTest()._make_mock_execute(1.0)(spec)
            res["usage"] = [old] + [{**u, "usage_id": f"{spec.label}-new"} for u in res["usage"]]
            return res

        mock_exec = MagicMock(side_effect=resumed)
        result = self._invoke(mock_exec, lambda spec: {"old": old}, ["--max-cost-dollars", "1.50"])
        # $1.00 per run of new spend: the stop comes after run 2, not run 1.
        self.assertEqual(mock_exec.call_count, 2, result.output)
        self.assertIn("cumulative cost stop: spent $2.00 >= $1.50 cap", result.output)


class BilledRowsReadTest(unittest.TestCase):
    """`_billed_rows` over real files (#5068): the provenance record's
    api_usage and this run's journal rows, keyed by usage id, foreign rows
    left out, and an unreadable source named rather than silently dropped."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.spec = SimpleNamespace(provenance_path=self.root / "P_provenance.yaml")

    def _read(self, journal=()):
        from data_sheets_schema.cli.api import _billed_rows
        unreadable: list = []
        with patch("data_sheets_schema.usage_ledger.ledger_path", return_value=self.root / "absent.json"), \
             patch("data_sheets_schema.api_runner._abandoned_rows", return_value=list(journal)), \
             patch("data_sheets_schema.usage_ledger.identity_is_foreign",
                   side_effect=lambda spec, ident: ident == "other-run"):
            return _billed_rows(self.spec, unreadable), unreadable

    def test_provenance_and_journal_rows_by_usage_id(self):
        self.spec.provenance_path.write_text(
            "api_usage:\n- {usage_id: a, input_tokens: 1}\n- {input_tokens: 2}\n- {usage_id: a, input_tokens: 9}\n",
            encoding="utf-8")
        rows, unreadable = self._read([{"usage_id": "j1", "run_identity": "this-run"},
                                       {"usage_id": "j2", "run_identity": "other-run"}])
        self.assertEqual(sorted(rows), ["a", "j1"])
        self.assertEqual(rows["a"]["input_tokens"], 1)
        self.assertEqual(unreadable, [])

    def test_an_unreadable_source_is_named(self):
        self.spec.provenance_path.write_text("api_usage: [unclosed\n", encoding="utf-8")
        rows, unreadable = self._read()
        self.assertEqual(rows, {})
        self.assertEqual(unreadable, ["provenance api_usage"])
