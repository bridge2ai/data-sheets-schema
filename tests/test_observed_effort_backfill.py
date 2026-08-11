"""Recording the effort a run's own model route already names (#448).

`_effort_from_route` runs only when a record is built, so 49 records written
before it existed named `google/claude-opus-5-high` and carried no
`reasoning_effort`. The information was in the route all along.

The property that makes a bulk pass defensible: this adds no claim the record
was not already making. The route is in the record; the effort is read off it.
So the value is **observed**, and must not appear in `unverified` — unlike an
effort asserted by a launcher, which must.
"""

import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.provenance import (
    apply_effort_basis,
    apply_observed_effort,
    effort_basis_gap,
    observed_effort_gap,
)

PREAMBLE = ("# D4D generation provenance record\n"
            "# record_version 1 — see src/data_sheets_schema/provenance.py\n")


class TestObservedEffortBackfill(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "X_provenance.yaml"

    def _write(self, model, extra=None):
        data = {"record_version": 1, "model": model,
                "unverified": [{"field": "model.temperature"}]}
        data.update(extra or {})
        self.path.write_text(
            PREAMBLE + yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def _load(self):
        return yaml.safe_load(self.path.read_text(encoding="utf-8"))

    def test_a_suffixed_route_is_recoverable(self):
        self._write({"model": "google/claude-opus-5-high"})
        gap = observed_effort_gap(self.path)
        self.assertEqual(gap["effort"], "high")
        self.assertIn("model route", gap["basis"])

    def test_a_route_with_no_ladder_yields_nothing(self):
        """`claude-opus-5` is not "default" — it is a route offering no ladder.

        Filling it would invent the distinction CLAUDE.md forbids: a run that
        did not choose an effort is a different claim from one whose effort is
        unknown, and neither is a run at high.
        """
        for route in ("claude-opus-5", "claude-opus-5[1m]",
                      "google/claude-opus-5"):
            with self.subTest(route=route):
                self._write({"model": route})
                self.assertIsNone(observed_effort_gap(self.path))

    def test_an_existing_effort_is_never_overwritten(self):
        self._write({"model": "google/claude-opus-5-high",
                     "reasoning_effort": "low",
                     "reasoning_effort_basis": "asserted by the launcher"})
        self.assertIsNone(observed_effort_gap(self.path))
        self.assertIsNone(apply_observed_effort(self.path))
        self.assertEqual(self._load()["model"]["reasoning_effort"], "low")

    def test_applying_writes_the_effort_and_its_basis(self):
        self._write({"model": "google/claude-opus-5-high"})
        apply_observed_effort(self.path)
        model = self._load()["model"]
        self.assertEqual(model["reasoning_effort"], "high")
        self.assertIn("model route", model["reasoning_effort_basis"])

    def test_the_value_is_observed_so_it_does_not_enter_unverified(self):
        """The whole reason a bulk pass is safe here.

        An effort asserted by a launcher belongs in `unverified`; one read off
        the route the record already carries does not, because it is not a new
        claim. Recording it as unverified would understate what is known.
        """
        self._write({"model": "google/claude-opus-5-high"})
        apply_observed_effort(self.path)
        fields = [e.get("field") for e in self._load().get("unverified") or []]
        self.assertEqual(fields, ["model.temperature"])
        self.assertNotIn("model.reasoning_effort", fields)

    def test_the_comment_preamble_survives(self):
        """It carries record_version and a pointer to the module; safe_dump
        would drop it silently."""
        self._write({"model": "google/claude-opus-5-high"})
        apply_observed_effort(self.path)
        text = self.path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# D4D generation provenance record"))
        self.assertIn("record_version 1", text)

    def test_every_other_field_is_left_alone(self):
        """A 49-record rewrite must change only what it claims to change."""
        extra = {"run": {"label": "L", "project": "P"},
                 "validation": {"passed": True, "artifacts": {"full": {}}},
                 "inputs": {"bundle_md5": "abc", "bundle_path": "b.txt"}}
        self._write({"model": "google/claude-opus-5-high"}, extra)
        before = self._load()
        apply_observed_effort(self.path)
        after = self._load()
        for key in ("run", "validation", "inputs", "unverified",
                    "record_version"):
            self.assertEqual(after[key], before[key], key)
        self.assertEqual(set(after) , set(before))

    def test_a_record_with_no_model_block_is_skipped(self):
        self.path.write_text(PREAMBLE + yaml.safe_dump({"record_version": 1}),
                             encoding="utf-8")
        self.assertIsNone(observed_effort_gap(self.path))

    def test_a_missing_file_is_skipped(self):
        self.assertIsNone(observed_effort_gap(self.path / "nope.yaml"))

    def test_unparseable_yaml_is_skipped_not_raised(self):
        """One bad record must not abort a corpus-wide pass — the failure #444
        fixed for the scope sweep."""
        self.path.write_text("this: [is: not: valid", encoding="utf-8")
        self.assertIsNone(observed_effort_gap(self.path))

    def test_undecodable_bytes_are_skipped_too(self):
        """A different code path from bad YAML, and only one was covered (#472).

        `read_text` raises UnicodeDecodeError before the parser is reached, so
        a `except yaml.YAMLError` guard lets it through and the sweep dies on
        record N of 162 — under --execute, partway through writing.
        """
        self.path.write_bytes(b"\xff\xfe\x00 model: not utf-8")
        self.assertIsNone(observed_effort_gap(self.path))

    def test_an_unreadable_path_is_skipped(self):
        """A directory where a file is expected raises OSError, not YAMLError."""
        directory = Path(self.tmp.name) / "a_directory.yaml"
        directory.mkdir()
        self.assertIsNone(observed_effort_gap(directory))

    def test_the_write_leaves_no_temp_file_behind(self):
        """Atomic via rename, so a record is its old bytes or its new ones.

        Unlike `Record.write`, which creates a record for a run that just
        happened, this mutates records that already exist and are attested — a
        truncated write here destroys provenance rather than failing to add it.
        """
        self._write({"model": "google/claude-opus-5-high"})
        apply_observed_effort(self.path)
        strays = [p.name for p in Path(self.tmp.name).iterdir()
                  if p.name != self.path.name]
        self.assertEqual(strays, [])
        self.assertEqual(self._load()["model"]["reasoning_effort"], "high")

    def test_applying_twice_is_a_no_op(self):
        self._write({"model": "google/claude-opus-5-high"})
        self.assertIsNotNone(apply_observed_effort(self.path))
        first = self.path.read_text(encoding="utf-8")
        self.assertIsNone(apply_observed_effort(self.path))
        self.assertEqual(self.path.read_text(encoding="utf-8"), first)


@unittest.skipUnless(Path("data/d4d_concatenated").exists(), "corpus absent")
class TestAgainstTheRealCorpus(unittest.TestCase):
    def test_no_recoverable_effort_is_left_unrecorded(self):
        """The 49 are done, and nothing has regressed.

        Fails if a new record lands whose route names an effort it does not
        carry — which is the state #448 was filed about.
        """
        gaps = [g for g in
                (observed_effort_gap(p) for p in
                 Path("data/d4d_concatenated").glob(
                     "*_core/*/*_provenance.yaml"))
                if g]
        self.assertEqual(gaps, [], f"{len(gaps)} record(s) still recoverable")

    def test_every_recorded_effort_says_where_it_came_from(self):
        """A value with no basis cannot be placed on the ladder #397 defines.

        The invariant is *not* "the route must name it" — that was this test's
        first premise and it was wrong. CLAUDE.md gives three sources in order:
        the route (observed), `--reasoning-effort` (asserted by the launcher),
        and nothing (absent, gap named). The agentic path legitimately records
        `high` on a ladderless route because the runtime exposes `CLAUDE_EFFORT`
        (#449). What distinguishes those cases is the *basis*, so that is what
        is asserted.

        17 records predate the basis field and are pinned by count, not
        excused: 15 from the 2026-08-07 sweep carrying `high` with no basis, and
        2 carrying the forbidden `default` (#470). The number may only go down.
        """
        without_basis = []
        for p in Path("data/d4d_concatenated").glob(
                "*_core/*/*_provenance.yaml"):
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            model = data.get("model") or {}
            effort = model.get("reasoning_effort")
            if not effort or effort == "not applicable":
                continue
            if not model.get("reasoning_effort_basis"):
                without_basis.append(str(p))

        self.assertEqual(
            without_basis, [],
            "a record carries an effort with no basis; every effort must say "
            "whether it was read from the route, asserted by the generating "
            "agent, or observed from the runtime (#397, #470)")

    def test_no_record_states_an_effort_that_names_none(self):
        """`default` and kin are forbidden values, not null (#470).

        Anything grouping runs by effort reads them as a third condition
        alongside `high` and absent. Two records carried `default`; the value
        was removed rather than corrected, because a run that did not choose an
        effort is a different claim from one at any level.
        """
        from data_sheets_schema.provenance import PLACEHOLDER_EFFORTS

        offenders = []
        for p in Path("data/d4d_concatenated").glob(
                "*_core/*/*_provenance.yaml"):
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            effort = (data.get("model") or {}).get("reasoning_effort")
            if effort and str(effort).strip().lower() in PLACEHOLDER_EFFORTS:
                offenders.append((str(p), effort))
        self.assertEqual(offenders, [])

    def test_the_backfilled_records_all_carry_their_basis(self):
        """The 49 this pass wrote are the well-formed case, asserted as such."""
        n = 0
        for p in Path("data/d4d_concatenated").glob(
                "*_core/*/*_provenance.yaml"):
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            model = data.get("model") or {}
            if (model.get("model") or "").endswith("-high"):
                self.assertEqual(model.get("reasoning_effort"), "high", str(p))
                self.assertIn("model route",
                              model.get("reasoning_effort_basis") or "", str(p))
                n += 1
        self.assertEqual(n, 49)


class TestEffortBasis(unittest.TestCase):
    """Every recorded effort must say where it came from (#470).

    A value with no basis cannot be placed on the ladder #397 defines — route
    (observed), launcher/agent (asserted), or absent (gap named) — and anything
    grouping runs by effort reads it as a third condition.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "X_provenance.yaml"

    def _write(self, model, unverified=None):
        data = {"record_version": 1, "model": model,
                "unverified": unverified if unverified is not None else []}
        self.path.write_text(
            PREAMBLE + yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def _load(self):
        return yaml.safe_load(self.path.read_text(encoding="utf-8"))

    def test_a_real_value_without_a_basis_gets_one(self):
        self._write({"model": "claude-opus-5", "reasoning_effort": "high"})
        change = apply_effort_basis(self.path)
        self.assertEqual(change["action"], "record_basis")
        model = self._load()["model"]
        self.assertEqual(model["reasoning_effort"], "high")
        self.assertIn("asserted by the generating agent",
                      model["reasoning_effort_basis"])

    def test_recording_a_basis_keeps_the_value(self):
        """The value is right; only its provenance was missing."""
        self._write({"model": "claude-opus-5", "reasoning_effort": "high"})
        apply_effort_basis(self.path)
        self.assertEqual(self._load()["model"]["reasoning_effort"], "high")

    def test_a_placeholder_is_removed_not_relabelled(self):
        """`default` names no effort, so no basis can be honest about it."""
        self._write({"model": "claude-opus-5[1m]", "reasoning_effort": "default"})
        change = apply_effort_basis(self.path)
        self.assertEqual(change["action"], "drop_placeholder")
        model = self._load()["model"]
        self.assertNotIn("reasoning_effort", model)
        self.assertNotIn("reasoning_effort_basis", model)

    def test_a_dropped_placeholder_names_the_gap(self):
        """Deleting a value silently would be worse than keeping it."""
        self._write({"model": "claude-opus-5[1m]", "reasoning_effort": "default"})
        apply_effort_basis(self.path)
        entries = [e for e in self._load()["unverified"]
                   if e["field"] == "model.reasoning_effort"]
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0]["value"])
        self.assertIn("names no effort", entries[0]["reason"])

    def test_every_placeholder_spelling_is_caught(self):
        for value in ("default", "unspecified", "n/a", "none", "unknown",
                      "DEFAULT", " Default "):
            with self.subTest(value=value):
                self._write({"model": "m", "reasoning_effort": value})
                self.assertEqual(effort_basis_gap(self.path)["action"],
                                 "drop_placeholder")

    def test_an_existing_basis_is_left_alone(self):
        self._write({"model": "m", "reasoning_effort": "high",
                     "reasoning_effort_basis": "read from the model route"})
        self.assertIsNone(effort_basis_gap(self.path))
        self.assertIsNone(apply_effort_basis(self.path))

    def test_not_applicable_is_not_a_gap(self):
        """A run that declares the field inapplicable has already answered."""
        self._write({"model": "m", "reasoning_effort": "not applicable"})
        self.assertIsNone(effort_basis_gap(self.path))

    def test_an_absent_effort_is_not_a_gap(self):
        """Absent is the honest state for a route with no ladder."""
        self._write({"model": "claude-opus-5"})
        self.assertIsNone(effort_basis_gap(self.path))

    def test_applying_twice_is_a_no_op(self):
        self._write({"model": "m", "reasoning_effort": "high"})
        self.assertIsNotNone(apply_effort_basis(self.path))
        first = self.path.read_text(encoding="utf-8")
        self.assertIsNone(apply_effort_basis(self.path))
        self.assertEqual(self.path.read_text(encoding="utf-8"), first)

    def test_existing_unverified_entries_survive(self):
        self._write({"model": "m", "reasoning_effort": "high"},
                    unverified=[{"field": "model.temperature", "value": None,
                                 "reason": "pre-existing"}])
        apply_effort_basis(self.path)
        fields = [e["field"] for e in self._load()["unverified"]]
        self.assertIn("model.temperature", fields)
        self.assertIn("model.reasoning_effort", fields)

    def test_unreadable_records_are_skipped_not_raised(self):
        self.path.write_bytes(b"\xff\xfe bad")
        self.assertIsNone(effort_basis_gap(self.path))
