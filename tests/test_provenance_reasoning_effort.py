"""#397 — reasoning effort was in no prompt, so most runs lost it.

`{EFFORT}` appears in none of the generic prompts, v1 through v4, so
`parse_header` finds no `# Reasoning effort:` line and the field is simply
absent. Measured over 2026-08: 12 API records carry no effort at all, while the
three agentic sweeps carry it only because a launch message told the agent to
write it by hand — the out-of-band intervention #419 and #422 exist to remove.

Fixed in the recorder rather than in the prompt. Adding a header line to v3
would change its bytes, re-baseline the condition for every project, and now
demand a pin rotation (#432); the recorder can establish the same fact without
touching a frozen baseline.

The rule that shapes all of this: **an effort nobody chose is not a value.**
Where none can be established the field stays absent and the gap is named,
because "the provider default applied" and "we ran at high" are different
claims and only one of them is comparable across runs.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from data_sheets_schema import provenance


def header(model: str, runtime: str = "Claude API (direct)",
           effort: str | None = None) -> str:
    lines = ["# D4D Datasheet for TESTPROJ Dataset",
             f"# Agent runtime: {runtime}",
             "# Provider: Anthropic",
             f"# Model: {model}"]
    if effort:
        lines.append(f"# Reasoning effort: {effort}")
    lines += ["# Temperature: 0.0", ""]
    return "\n".join(lines)


class TestEffortFromTheRoute(unittest.TestCase):
    """CBORG exposes effort as a model-name suffix, not a parameter, because
    this family rejects `temperature` outright. The route is therefore evidence
    about effort — and the only evidence either path currently produces."""

    def test_a_suffixed_route_yields_the_effort(self):
        for route, want in (("google/claude-opus-5-high", "high"),
                            ("google/claude-opus-5-low", "low"),
                            ("CLAUDE-OPUS-5-MEDIUM", "medium"),
                            ("some-model-minimal", "minimal")):
            with self.subTest(route=route):
                effort, basis = provenance._effort_from_route(route)
                self.assertEqual(want, effort)
                self.assertIn("model route", basis)

    def test_an_unsuffixed_route_yields_nothing_not_a_default(self):
        for route in ("claude-opus-5", "claude-opus-5-1m", None, ""):
            with self.subTest(route=route):
                self.assertEqual((None, None),
                                 provenance._effort_from_route(route))

    def test_a_route_merely_containing_a_level_is_not_a_match(self):
        """`-high` must be the suffix. A route named `highlight-model` names no
        effort, and treating it as `high` would invent one."""
        self.assertEqual((None, None),
                         provenance._effort_from_route("highlight-model"))


class TestWhatTheRecordSays(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = os.getcwd()
        self.addCleanup(os.chdir, self.cwd)
        self.addCleanup(self.tmp.cleanup)
        os.chdir(self.root)
        self.label, self.method = "2026-08-11_test_rep1", "claudecode_agent"
        self.concat = Path("data/d4d_concatenated")
        self.full_dir = self.concat / self.method / self.label
        self.core_dir = self.concat / f"{self.method}_core" / self.label
        self.full_dir.mkdir(parents=True)
        self.core_dir.mkdir(parents=True)
        # marker the repo-root guard (#672) requires; the scratch root
        # stands in for the repo by design in these tests
        Path("src/data_sheets_schema").mkdir(parents=True, exist_ok=True)
        self.bundle = Path("bundle.txt")
        self.bundle.write_text("source documents\n")

    def _write(self, model: str, runtime: str = "Claude API (direct)",
               effort: str | None = None):
        body = yaml.safe_dump({"id": "https://example.org/x", "name": "x"})
        (self.full_dir / "TESTPROJ_d4d.yaml").write_text(
            header(model, runtime, effort) + body)
        (self.core_dir / "TESTPROJ_d4d_core.yaml").write_text(
            header(model, runtime, effort) + body)
        (self.core_dir / "TESTPROJ_reconciliation.md").write_text("# r\n")

    def _record(self, **kw):
        rec = provenance.build_record(
            "TESTPROJ", self.method, self.label, mode="live",
            input_bundle=self.bundle, input_verified=True,
            concat_dir=self.concat, **kw)
        return rec.data

    def _gap(self, data):
        return [u for u in (data.get("unverified") or [])
                if u.get("field") == "model.reasoning_effort"]

    def test_the_route_supplies_it_with_no_flag_needed(self):
        self._write("google/claude-opus-5-high")
        model = self._record()["model"]
        self.assertEqual("high", model["reasoning_effort"])
        self.assertIn("model route", model["reasoning_effort_basis"])

    def test_an_unladdered_route_records_the_gap_and_no_value(self):
        """The 12 records that lost it did so silently. This is the same
        absence, said out loud."""
        self._write("claude-opus-5")
        data = self._record()
        self.assertNotIn("reasoning_effort", data["model"])
        gap = self._gap(data)
        self.assertEqual(1, len(gap))
        self.assertIsNone(gap[0]["value"])
        self.assertIn("no effort ladder", gap[0]["reason"])

    def test_no_record_ever_writes_default_or_unspecified(self):
        self._write("claude-opus-5")
        text = yaml.safe_dump(self._record()["model"]).lower()
        for banned in ("default", "unspecified", "n/a", "not applicable"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, text)

    def test_the_flag_is_recorded_as_asserted_and_still_flagged(self):
        self._write("claude-opus-5")
        data = self._record(reasoning_effort="high")
        self.assertEqual("high", data["model"]["reasoning_effort"])
        self.assertIn("asserted by the launcher",
                      data["model"]["reasoning_effort_basis"])
        # Recorded *and* listed: a launcher's assertion is better than nothing
        # and is not an observation.
        self.assertEqual(1, len(self._gap(data)))

    def test_the_route_wins_over_the_flag(self):
        """The route is evidence; the flag is a claim. A flag that disagreed
        with the route would otherwise overwrite the observation."""
        self._write("google/claude-opus-5-high")
        data = self._record(reasoning_effort="low")
        self.assertEqual("high", data["model"]["reasoning_effort"])

    def test_the_flag_disagreeing_with_the_route_is_recorded_not_erased(self):
        """Keeping the route silently would hide the more interesting fact:
        somebody believed this run ran at an effort it did not run at (#451)."""
        self._write("google/claude-opus-5-high")
        data = self._record(reasoning_effort="low")
        self.assertEqual("high", data["model"]["reasoning_effort"])
        notes = " ".join(data.get("notes") or [])
        self.assertIn("Reasoning effort mismatch", notes)
        self.assertIn("'high'", notes)
        self.assertIn("'low'", notes)

    def test_an_agreeing_flag_produces_no_mismatch_note(self):
        self._write("google/claude-opus-5-high")
        data = self._record(reasoning_effort="high")
        self.assertNotIn("Reasoning effort mismatch",
                         " ".join(data.get("notes") or []))

    def test_claude_code_effort_is_asserted_when_the_environment_is_silent(self):
        """With no `CLAUDE_EFFORT` to corroborate it, a header value is only a
        restatement of whatever the agent was told to write."""
        self._write("claude-opus-5", runtime="Claude Code", effort="high")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_EFFORT", None)
            model = self._record()["model"]
        self.assertEqual("high", model["reasoning_effort"])
        self.assertEqual("asserted by the generating agent, not observed",
                         model["reasoning_effort_basis"])

    def test_claude_code_effort_is_observed_when_the_environment_agrees(self):
        """The runtime *does* expose effort (#449). Where the header and
        `CLAUDE_EFFORT` agree, the value was read rather than asserted — unlike
        the temperature beside it, which the runtime exposes no knob for."""
        self._write("claude-opus-5", runtime="Claude Code", effort="high")
        with mock.patch.dict(os.environ, {"CLAUDE_EFFORT": "high"}):
            data = self._record()
        self.assertEqual("high", data["model"]["reasoning_effort"])
        self.assertIn("observed", data["model"]["reasoning_effort_basis"])
        self.assertIn("CLAUDE_EFFORT", data["model"]["reasoning_effort_basis"])
        self.assertEqual([], self._gap(data))

    def test_a_disagreeing_environment_does_not_settle_it_either_way(self):
        """The recorder may be a different session than the generator, so a
        mismatch is reported and neither value is overwritten."""
        self._write("claude-opus-5", runtime="Claude Code", effort="high")
        with mock.patch.dict(os.environ, {"CLAUDE_EFFORT": "low"}):
            data = self._record()
        self.assertEqual("high", data["model"]["reasoning_effort"])
        self.assertEqual("asserted by the generating agent, not observed",
                         data["model"]["reasoning_effort_basis"])
        gap = self._gap(data)
        self.assertEqual(1, len(gap))
        self.assertIn("disagree", gap[0]["reason"])

    def test_the_gap_does_not_change_attestation(self):
        """Reporting a gap must not retroactively downgrade runs. Effort is not
        an attesting field, and 12 existing records lack it."""
        from data_sheets_schema.runs import attestation
        self._write("claude-opus-5")
        rec = provenance.build_record(
            "TESTPROJ", self.method, self.label, mode="live",
            input_bundle=self.bundle, input_verified=True,
            concat_dir=self.concat)
        rec.write(provenance.record_path_for("TESTPROJ", self.method,
                                             self.label, self.concat))
        self.assertEqual("live", attestation(self.method, self.label,
                                             "TESTPROJ", self.concat))


class TestTheCLIFlag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = os.getcwd()
        self.addCleanup(os.chdir, self.cwd)
        self.addCleanup(self.tmp.cleanup)
        os.chdir(self.root)
        self.label, self.method = "2026-08-11_test_rep1", "claudecode_agent"
        concat = Path("data/d4d_concatenated")
        full = concat / self.method / self.label
        core = concat / f"{self.method}_core" / self.label
        full.mkdir(parents=True)
        core.mkdir(parents=True)
        # marker the repo-root guard (#672) requires; the scratch root
        # stands in for the repo by design in these tests
        Path("src/data_sheets_schema").mkdir(parents=True, exist_ok=True)
        body = yaml.safe_dump({"id": "https://example.org/x", "name": "x"})
        head = header("claude-opus-5", "Claude Code")
        (full / "P_d4d.yaml").write_text(head + body)
        (core / "P_d4d_core.yaml").write_text(head + body)
        (core / "P_reconciliation.md").write_text("# r\n")
        Path("b.txt").write_text("docs\n")
        self.out = core / "P_provenance.yaml"

    def _run(self, *extra):
        from click.testing import CliRunner
        from data_sheets_schema.cli.provenance import provenance as cli
        return CliRunner().invoke(cli, [
            "record", "--project", "P", "--method", self.method,
            "--label", self.label, "--input-bundle", "b.txt", *extra])

    def test_the_flag_reaches_the_record(self):
        r = self._run("--reasoning-effort", "high")
        self.assertEqual(0, r.exit_code, r.output)
        data = yaml.safe_load(self.out.read_text())
        self.assertEqual("high", data["model"]["reasoning_effort"])

    def test_without_the_flag_the_gap_is_recorded(self):
        r = self._run()
        self.assertEqual(0, r.exit_code, r.output)
        data = yaml.safe_load(self.out.read_text())
        self.assertNotIn("reasoning_effort", data["model"])
        self.assertTrue(any(u.get("field") == "model.reasoning_effort"
                            for u in data.get("unverified") or []))

    def test_the_placeholder_values_the_help_forbids_are_refused(self):
        """The help said "default" is not a value and nothing enforced it
        (#450). A record carrying it would disagree with
        `procedure_fingerprint`, which discards exactly these strings."""
        for banned in ("default", "n/a", "unspecified", "not applicable"):
            with self.subTest(banned=banned):
                r = self._run("--reasoning-effort", banned)
                self.assertNotEqual(0, r.exit_code)
                self.assertFalse(self.out.exists(),
                                 "a refused effort must not write a record")

    def test_a_misspelled_effort_is_refused_rather_than_recorded(self):
        r = self._run("--reasoning-effort", "hgih")
        self.assertNotEqual(0, r.exit_code)

    def test_effort_ladder_matches_the_recorder(self):
        """The CLI duplicates the ladder to keep its imports lazy. If the two
        drift, the flag and the route parser accept different vocabularies."""
        from data_sheets_schema.cli.provenance import EFFORT_CHOICES
        self.assertEqual(tuple(provenance._EFFORT_LADDER),
                         tuple(EFFORT_CHOICES))


class TestTheGapIsVisibleFromTheCommandLine(unittest.TestCase):
    """#447. Every record has carried an `unverified` list since temperature
    got a basis, and no command read it — so naming the effort gap honestly
    would have landed in a field nobody sees."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = os.getcwd()
        self.addCleanup(os.chdir, self.cwd)
        self.addCleanup(self.tmp.cleanup)
        os.chdir(self.root)
        # Dated before REQUEST_REQUIRED_FROM on purpose: a later label would
        # fail `--strict` on the missing instruction (#419), which is correct
        # and would hide what this class is testing.
        self.label, self.method = "2026-08-09_test_rep1", "claudecode_agent"
        concat = Path("data/d4d_concatenated")
        full = concat / self.method / self.label
        core = concat / f"{self.method}_core" / self.label
        full.mkdir(parents=True)
        core.mkdir(parents=True)
        # marker the repo-root guard (#672) requires; the scratch root
        # stands in for the repo by design in these tests
        Path("src/data_sheets_schema").mkdir(parents=True, exist_ok=True)
        body = yaml.safe_dump({"id": "https://example.org/x", "name": "x"})
        head = header("claude-opus-5", "Claude Code")
        (full / "P_d4d.yaml").write_text(head + body)
        (core / "P_d4d_core.yaml").write_text(head + body)
        (core / "P_reconciliation.md").write_text("# r\n")
        Path("b.txt").write_text("docs\n")

        rec = provenance.build_record(
            "P", self.method, self.label, mode="live",
            input_bundle=Path("b.txt"), input_verified=True, concat_dir=concat)
        rec.write(provenance.record_path_for("P", self.method, self.label,
                                             concat))

    def _check(self, *args):
        from click.testing import CliRunner
        from data_sheets_schema.cli.runs import runs
        return CliRunner().invoke(runs, ["check", *args])

    def test_the_count_is_reported(self):
        r = self._check()
        self.assertEqual(0, r.exit_code, r.output)
        self.assertIn("recorded but not observed", r.output)
        self.assertIn("model.reasoning_effort", r.output)

    def test_it_is_never_the_reason_a_run_fails(self):
        """These values are usable *with* a caveat, so counting them must not
        gate anything — that would collapse the caveat back into the binary the
        list exists to avoid.

        This fixture does fail `--strict`, for an unrelated and correct reason:
        it has never been validated, so #396's gate fires. The claim under test
        is that no failure line is about an unobserved value.
        """
        r = self._check("--strict")
        failures = [ln for ln in r.output.splitlines() if "❌" in ln]
        self.assertTrue(failures, r.output)
        for line in failures:
            self.assertIn("nothing to verify", line)
            self.assertNotIn("not observed", line)
            self.assertNotIn("reasoning_effort", line)
        self.assertIn("recorded but not observed", r.output)


if __name__ == "__main__":
    unittest.main()
