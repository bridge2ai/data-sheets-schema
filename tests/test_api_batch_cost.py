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
             patch("data_sheets_schema.cli.api._billed_rows", side_effect=lambda spec, *a, **k: billed(spec)), \
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
        self.spec = SimpleNamespace(provenance_path=self.root / "P_provenance.yaml",
                                    metadata_dir=self.root, project="P")

    def _read(self, journal=(), ledger=None, before=frozenset(), pending=None, real_identity=False):
        import contextlib
        import json
        from data_sheets_schema.cli.api import _billed_rows
        ledger_file = self.root / "ledger.json"
        if ledger is not None:
            ledger_file.write_text(json.dumps(ledger), encoding="utf-8")
        unreadable: list = []
        with patch("data_sheets_schema.usage_ledger.ledger_path", return_value=ledger_file), \
             patch("data_sheets_schema.usage_ledger._read", side_effect=lambda spec: json.loads(ledger_file.read_text())), \
             patch("data_sheets_schema.api_runner._abandoned_rows", return_value=list(journal)), \
             (contextlib.nullcontext() if real_identity else
              patch("data_sheets_schema.usage_ledger.identity_is_foreign",
                    side_effect=lambda spec, ident: ident == "other-run")):
            return _billed_rows(self.spec, unreadable, before, pending), unreadable

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
        self.assertEqual(unreadable, ["could not read provenance api_usage"])

    def test_a_pending_call_is_named_and_not_returned_as_a_row(self):
        """Not a row (#5073 F1): a resume can settle it with real counters,
        and the id must not be in the pre-run set that excludes them."""
        ledger = {"rows": [{"usage_id": "r1", "input_tokens": 5}],
                  "pending_call": {"usage_id": "p1", "phase": "audit"}}
        pending: set = set()
        rows, gaps = self._read(ledger=ledger, pending=pending)
        self.assertEqual(sorted(rows), ["r1"])
        self.assertEqual(pending, {"p1"})
        self.assertEqual(gaps, ["call p1 (audit) has no recorded usage"])

    def test_a_pending_call_from_before_the_run_is_not_named(self):
        _, gaps = self._read(ledger={"rows": [], "pending_call": {"usage_id": "p0", "phase": "full"}},
                             before={"p0"})
        self.assertEqual(gaps, [])

    def test_a_reasoning_entry_with_no_usage_row_counts_its_output(self):
        """Through the real `identity_is_foreign` with dict identities as the
        runner writes them, and only the ledger's current generation (#5073
        F3, F4)."""
        import json
        self.spec.__dict__.update(label="L", method="claudecode_api", condition="generic_v8")
        this = {"project": "P", "label": "L", "method": "claudecode_api", "condition": "generic_v8"}
        (self.root / "P_reasoning.jsonl").write_text("\n".join(json.dumps(e) for e in [
            {"usage_id": "a", "phase": "full", "output_tokens": 7, "generation_id": "g2", "run_identity": this},
            {"usage_id": "lost", "phase": "core", "output_tokens": 40, "generation_id": "g2", "run_identity": this},
            {"usage_id": "foreign", "output_tokens": 9, "generation_id": "g2",
             "run_identity": {**this, "label": "other"}},
            {"usage_id": "toplevel", "output_tokens": 9, "generation_id": "g2", **this, "condition": "generic_v7"},
            {"usage_id": "old", "output_tokens": 5, "generation_id": "g1", "run_identity": this},
            {"usage_id": "nogen", "output_tokens": 5, "run_identity": this},
            {"phase": "legacy", "output_tokens": 3, "generation_id": "g2"},          # no usage id
        ]) + "\n", encoding="utf-8")
        self.spec.provenance_path.write_text("api_usage:\n- {usage_id: a, input_tokens: 1}\n", encoding="utf-8")
        rows, gaps = self._read(ledger={"rows": [], "generation_id": "g2"}, real_identity=True)
        self.assertEqual(sorted(rows), ["a", "lost"])
        self.assertEqual(rows["lost"]["output_tokens"], 40)
        self.assertNotIn("input_tokens", rows["lost"])
        self.assertEqual(gaps, ["1 response(s) in the reasoning log have no usage row (input tokens unknown)"])

    def test_a_torn_reasoning_line_is_named_and_the_rest_still_count(self):
        """#5070 R4: one torn line, a killed run's partial write, no longer
        drops every other reasoning-only response from the count."""
        import json
        entry = {"usage_id": "lost", "phase": "core", "output_tokens": 40, "generation_id": "g2"}
        (self.root / "P_reasoning.jsonl").write_text(json.dumps(entry) + "\n{not json\n", encoding="utf-8")
        rows, gaps = self._read(ledger={"rows": [], "generation_id": "g2"})
        self.assertEqual(sorted(rows), ["lost"])
        self.assertEqual(gaps, ["1 unreadable line(s) in the reasoning log (line 2)",
                                "1 response(s) in the reasoning log have no usage row (input tokens unknown)"])


class ApiBatchTotalsWithoutCapTest(ApiBatchCostAccountingTest):
    """#5068: the printed totals are this invocation's spend whether or not
    --max-cost-dollars is set."""

    def test_history_is_not_in_the_totals_without_a_cap(self):
        old = {**self.ROW, "output_tokens": 60_000, "usage_id": "old"}

        def resumed(spec):
            return {**ApiBatchCostStopTest()._make_mock_execute(1.0)(spec),
                    "usage": [old, {**self.ROW, "usage_id": f"{spec.label}-new"}]}

        result = self._invoke(MagicMock(side_effect=resumed), lambda spec: {"old": old}, [], reps="1")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("tokens: 100,000 in, 20,000 out (cost: $1.00)", result.output)

    def test_a_raised_run_is_in_the_totals_without_a_cap(self):
        on_disk: dict = {}

        def raising(spec):
            on_disk[spec.label] = {"u1": {**self.ROW, "usage_id": "u1"}}
            raise RuntimeError("phase audit: retries exhausted")

        result = self._invoke(MagicMock(side_effect=raising), lambda spec: dict(on_disk.get(spec.label, {})),
                              ["--continue-on-error"], reps="1")
        self.assertIn("tokens: 100,000 in, 20,000 out (cost: $1.00)", result.output)


class ApiBatchRealBilledRowsTest(ApiBatchCostAccountingTest):
    """The batch over the real `_billed_rows`, ledger file stubbed per run
    (#5073 F1, F2): what is pending before the run, and how a raise names
    what it could not count."""

    def _invoke_real(self, mock_exec, ledgers, extra=(), reps="1"):
        import json
        import tempfile
        from pathlib import Path
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        def path(spec):
            return root / f"{spec.label}.json"

        def write(spec, data):
            path(spec).write_text(json.dumps(data), encoding="utf-8")

        def execute(spec):
            return mock_exec(spec, lambda data: write(spec, data))

        def setup(spec):
            if spec.label in ledgers:
                write(spec, ledgers[spec.label])
        plan = ApiBatchCostStopTest()._dummy_plan
        with patch("data_sheets_schema.cli.api._require_bundle", return_value=None), \
             patch("data_sheets_schema.cli.api._plan_or_refuse",
                   side_effect=lambda spec: (setup(spec), plan(spec))[1]), \
             patch("data_sheets_schema.usage_ledger.ledger_path", side_effect=path), \
             patch("data_sheets_schema.usage_ledger._read", side_effect=lambda spec: json.loads(path(spec).read_text())), \
             patch("data_sheets_schema.api_runner._abandoned_rows", return_value=[]), \
             patch("data_sheets_schema.api_runner.execute", side_effect=execute):
            return CliRunner(mix_stderr=False).invoke(cli, [
                "api", "batch", "--projects", "AI_READI", "--replicates", reps, "--arm", "baseline",
                "--condition", "generic", "--label-prefix", "2026-10-17_claude-opus-5-api-generic-testcost9",
                "--allow-condition-mismatch", "--yes", "--no-branch-guard", "--no-canary-gate", *extra])

    LABEL = "2026-10-17_claude-opus-5-api-generic-testcost9_rep1"

    def test_a_pending_call_settled_on_resume_is_counted_by_this_invocation(self):
        """#5073 F1: the call an earlier invocation left pending is settled
        with real counters by this one, which must count them."""
        recovered = {**self.ROW, "usage_id": "p1", "phase": "audit"}

        def resumed(spec, write):
            write({"rows": [recovered]})
            return {**ApiBatchCostStopTest()._make_mock_execute(1.0)(spec), "usage": [recovered]}

        result = self._invoke_real(resumed, {self.LABEL: {"rows": [], "pending_call": {
            "usage_id": "p1", "phase": "audit"}}})
        self.assertEqual(result.exit_code, 0, result.output + result.stderr)
        self.assertIn("tokens: 100,000 in, 20,000 out (cost: $1.00)", result.output)

    def test_a_raise_names_its_own_pending_call_and_not_an_earlier_one(self):
        """#5073 F2: the real wiring of `gaps` and `before` at batch level."""
        def raising(spec, write):
            write({"rows": [{**self.ROW, "usage_id": "u1"}], "pending_call": {"usage_id": "p1", "phase": "report"}})
            raise RuntimeError("phase report: killed")

        result = self._invoke_real(raising, {self.LABEL: {"rows": [], "pending_call": {
            "usage_id": "p0", "phase": "full"}}}, ["--continue-on-error"])
        self.assertIn("cost of the raised run may be undercounted: call p1 (report) has no recorded usage",
                      result.stderr)
        self.assertNotIn("p0", result.stderr)
        self.assertIn("tokens: 100,000 in, 20,000 out (cost: $1.00)", result.output)

    def test_a_raise_does_not_name_a_call_an_earlier_invocation_left_pending(self):
        """#5073 F2: `before` reaches `_billed_rows` from the batch; without
        it the earlier pending call is named as this run's (R2)."""
        def refused(spec, write):
            raise RuntimeError("API call p0 has unresolved accounting")

        result = self._invoke_real(refused, {self.LABEL: {"rows": [], "pending_call": {
            "usage_id": "p0", "phase": "full"}}}, ["--continue-on-error"])
        self.assertIn("unresolved accounting", result.stderr)
        self.assertNotIn("may be undercounted", result.stderr)


class ApiBatchSuccessPathRowsTest(ApiBatchCostAccountingTest):
    """#5069: a successful run counts the billed rows recorded on disk that
    its returned usage lacks, such as an attempt abandoned during the report
    regate and merged in at the final accounting."""

    def test_a_recorded_row_missing_from_the_returned_usage_is_counted(self):
        def finished(spec):
            row = {**self.ROW, "usage_id": "u1"}
            abandoned = {**self.ROW, "usage_id": "ab1", "phase": "report", "snapshot": "s"}
            on_disk = {"u1": row, "ab1": abandoned}
            finished.on_disk = on_disk
            return {**ApiBatchCostStopTest()._make_mock_execute(1.0)(spec), "usage": [row]}
        finished.on_disk = {}
        result = self._invoke(MagicMock(side_effect=finished), lambda spec: dict(finished.on_disk), [], reps="1")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("tokens: 200,000 in, 40,000 out (cost: $2.00)", result.output)

    def test_returned_rows_without_a_usage_id_are_not_unioned_and_it_is_said(self):
        def finished(spec):
            finished.on_disk = {"u1": {**self.ROW, "usage_id": "u1"}}
            return ApiBatchCostStopTest()._make_mock_execute(1.0)(spec)    # rows carry no usage id
        finished.on_disk = {}
        result = CliRunner(mix_stderr=False)
        with patch("data_sheets_schema.cli.api._require_bundle", return_value=None), \
             patch("data_sheets_schema.cli.api._plan_or_refuse", side_effect=ApiBatchCostStopTest()._dummy_plan), \
             patch("data_sheets_schema.cli.api._billed_rows", side_effect=lambda spec, *a, **k: dict(finished.on_disk)), \
             patch("data_sheets_schema.api_runner.execute", MagicMock(side_effect=finished)):
            result = result.invoke(cli, [
                "api", "batch", "--projects", "AI_READI", "--replicates", "1", "--arm", "baseline",
                "--condition", "generic", "--label-prefix", "2026-10-17_claude-opus-5-api-generic-testcost9",
                "--allow-condition-mismatch", "--yes", "--no-branch-guard", "--no-canary-gate"])
        self.assertEqual(result.exit_code, 0, result.output + result.stderr)
        self.assertIn("1 returned usage row(s) carry no usage id", result.stderr)
        self.assertIn("(cost: $1.00)", result.output)          # u1 on disk is not added


class ApiBatchPricingTest(unittest.TestCase):
    """#5062: the cap is priced at one model's posted rates, and a dry run
    shows the cap without inventing an estimate."""

    ARGS = ["api", "batch", "--projects", "AI_READI", "--replicates", "1", "--arm", "baseline",
            "--condition", "generic", "--label-prefix", "2026-10-17_claude-opus-5-api-generic-testcost9",
            "--allow-condition-mismatch", "--yes", "--no-branch-guard", "--no-canary-gate"]

    def _invoke(self, extra, model=None):
        from data_sheets_schema import api_runner
        real = api_runner._model_settings
        settings = (lambda c=None: {**real(c), "name": model}) if model else real
        with patch("data_sheets_schema.cli.api._require_bundle", return_value=None), \
             patch("data_sheets_schema.cli.api._plan_or_refuse", side_effect=ApiBatchCostStopTest()._dummy_plan), \
             patch("data_sheets_schema.api_runner._model_settings", side_effect=settings), \
             patch("data_sheets_schema.api_runner.execute") as mock_exec:
            return CliRunner().invoke(cli, [*self.ARGS, *extra]), mock_exec

    def test_rates_cover_the_opus_5_routes_only(self):
        from data_sheets_schema.run_telemetry import rates_cover
        for name in ("claude-opus-5", "google/claude-opus-5-high", "anthropic/claude-opus-5", "CLAUDE-OPUS-5"):
            self.assertTrue(rates_cover(name), name)
        for name in ("claude-opus-5-5", "claude-sonnet-4-5-20250929", "google/claude-opus-5-5-high", "", None):
            self.assertFalse(rates_cover(name), name)

    def test_a_cap_on_a_model_the_rates_do_not_price_is_refused(self):
        result, mock_exec = self._invoke(["--max-cost-dollars", "5"], model="claude-sonnet-4-5-20250929")
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("do not price claude-sonnet-4-5-20250929", result.output)
        mock_exec.assert_not_called()

    def test_no_cap_means_no_pricing_check(self):
        result, _ = self._invoke(["--dry-run"], model="claude-sonnet-4-5-20250929")
        self.assertEqual(result.exit_code, 0, result.output)

    def test_a_dry_run_shows_the_cap_and_says_there_is_no_estimate(self):
        result, mock_exec = self._invoke(["--dry-run", "--max-cost-dollars", "15"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("cost cap $15.00, checked between runs; no dollar estimate", result.output)
        mock_exec.assert_not_called()
