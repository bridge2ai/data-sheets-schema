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
        self.assertIn("--max-cost-dollars must be non-negative", result.output)

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
        self.assertIn("--max-cost-dollars must be non-negative", result.output)


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
