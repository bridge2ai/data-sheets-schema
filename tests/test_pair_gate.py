"""The full/core pair check, run by the runner and reported by `runs check`.

Why this exists (#544): the API path has `reconcile_full` and `reconcile_core`
phases and writes `# Phase 4 reconciliation: completed` into every core header,
but nothing ever ran `validate_pair_data` afterwards. The checker had been in
the tree since long before, with tests — and no caller. Across the 2026-08-13
v4 arm 11 of 12 pairs disagreed; the agentic playbook runs the same checker at
its own phase 4 and scored 0 of 15.

Every one of those records validates individually, which is why no gate saw it:
`linkml-validate` and `runs check` each read one file at a time, and this is a
property of two files together.
"""

import unittest
from pathlib import Path

import yaml

from data_sheets_schema.runs import (
    PAIR_CONSISTENT,
    PAIR_DIVERGENT,
    PAIR_NOT_RUN,
    PAIR_STALE,
    PAIR_UNRECORDED,
    pair_status,
)

METHOD, LABEL, PROJECT = "claudecode_agent", "2026-01-01_test_rep1", "CHORUS"


class PairStatusTest(unittest.TestCase):
    """`pair_status` reads what a run attested, and re-checks it."""

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.core_dir = self.root / f"{METHOD}_core" / LABEL
        self.full_dir = self.root / METHOD / LABEL
        self.core_dir.mkdir(parents=True)
        self.full_dir.mkdir(parents=True)
        self.full = self.full_dir / f"{PROJECT}_d4d.yaml"
        self.core = self.core_dir / f"{PROJECT}_d4d_core.yaml"
        self.full.write_text("id: x\n", encoding="utf-8")
        self.core.write_text("id: x\n", encoding="utf-8")
        self.addCleanup(self._tmp.cleanup)

    def _write(self, block):
        rec = {"run": {"project": PROJECT}}
        if block is not None:
            rec["pair_consistency"] = block
        (self.core_dir / f"{PROJECT}_provenance.yaml").write_text(
            yaml.safe_dump(rec), encoding="utf-8")

    def _pins(self):
        from data_sheets_schema.provenance import _md5
        return {"full": {"path": str(self.full), "md5": _md5(self.full)},
                "core": {"path": str(self.core), "md5": _md5(self.core)}}

    def _status(self):
        return pair_status(METHOD, LABEL, PROJECT, self.root)

    def test_absent_block_is_unrecorded_not_consistent(self):
        """The distinction the whole corpus depends on.

        Every record written before this landed has no block. Reporting those
        as consistent would assert agreement nobody checked — the same error
        as calling an unmeasured reasoning spend zero.
        """
        self._write(None)
        self.assertEqual(self._status(), (PAIR_UNRECORDED, 0))

    def test_consistent_pair(self):
        self._write({"ran": True, "consistent": True, "errors": 0,
                     "artifacts": self._pins()})
        self.assertEqual(self._status(), (PAIR_CONSISTENT, 0))

    def test_divergent_pair_carries_its_error_count(self):
        self._write({"ran": True, "consistent": False, "errors": 6,
                     "artifacts": self._pins()})
        self.assertEqual(self._status(), (PAIR_DIVERGENT, 6))

    def test_checker_that_could_not_run_is_not_a_pass(self):
        """A checker that failed to load says so; it does not report agreement."""
        self._write({"ran": False, "reason": "schema would not load"})
        self.assertEqual(self._status(), (PAIR_NOT_RUN, 0))

    def test_editing_either_record_makes_the_verdict_stale(self):
        """Both files, because either one alone can break the pair."""
        for edited in (self.full, self.core):
            with self.subTest(edited=edited.name):
                self.full.write_text("id: x\n", encoding="utf-8")
                self.core.write_text("id: x\n", encoding="utf-8")
                self._write({"ran": True, "consistent": True, "errors": 0,
                             "artifacts": self._pins()})
                self.assertEqual(self._status()[0], PAIR_CONSISTENT)
                edited.write_text("id: y\n", encoding="utf-8")
                self.assertEqual(self._status()[0], PAIR_STALE)

    def test_pins_name_the_paths_rather_than_rebuilding_them(self):
        """The two records are not in one directory (#544 review).

        The full record is under `{method}/{label}/` and the core one under
        `{method}_core/{label}/`, beside the provenance file. A re-check that
        derived the full record's path from the provenance file's own location
        would look for a file that was never there and call every pair stale —
        which is what the first version of this did.
        """
        self.assertNotEqual(self.full.parent, self.core.parent)
        self._write({"ran": True, "consistent": True, "errors": 0,
                     "artifacts": self._pins()})
        self.assertEqual(self._status()[0], PAIR_CONSISTENT)


class PairConsistencyTest(unittest.TestCase):
    """`pair_consistency` on real v4 records, which is where it came from."""

    LABEL = "2026-08-13_claude-opus-5-api-generic-v4_rep1"

    def _spec(self, project):
        from data_sheets_schema.api_runner import RunSpec
        return RunSpec(
            project=project, arm="baseline", method=METHOD,
            bundle=Path(f"data/preprocessed/concatenated/"
                        f"{project}_preprocessed.txt"),
            label=self.LABEL, condition="generic_v4")

    def test_finds_the_divergence_the_v4_arm_shipped_with(self):
        from data_sheets_schema.api_runner import pair_consistency
        spec = self._spec("CHORUS")
        if not (spec.full_path.exists() and spec.core_path.exists()):
            self.skipTest("v4 CHORUS records not present in this checkout")
        block = pair_consistency(spec)
        self.assertTrue(block["ran"])
        self.assertFalse(block["consistent"],
                         "CHORUS v4 rep1's pair disagrees; if this now passes, "
                         "the records were regenerated and the figure in #544 "
                         "needs restating")
        self.assertGreater(block["errors"], 0)
        self.assertEqual(set(block["artifacts"]), {"full", "core"})

    def test_missing_record_names_the_missing_file(self):
        """Distinct from a block that was never written.

        `None` means no check happened at all — which is what every record
        predating this reports. A run whose record was absent did check, and
        found nothing to check against; collapsing the two would file it with
        the 122 historical records instead of as the defect it is.
        """
        from data_sheets_schema.api_runner import pair_consistency
        block = pair_consistency(self._spec("NO_SUCH_PROJECT"))
        self.assertFalse(block["ran"])
        self.assertIn("missing", block["reason"])

    def test_truncation_is_declared_rather_than_silent(self):
        """`errors` is the true count even when `findings` is cut at 20."""
        from data_sheets_schema.api_runner import pair_consistency
        spec = self._spec("CHORUS")
        if not (spec.full_path.exists() and spec.core_path.exists()):
            self.skipTest("v4 CHORUS records not present in this checkout")
        block = pair_consistency(spec)
        dropped = block["findings_truncated"] or 0
        self.assertEqual(len(block["findings"]) + dropped, block["errors"])




class RecordGateTest(unittest.TestCase):
    """The new key must survive the gate the runner runs on its own output.

    `execute()` writes the record and immediately calls `check_provenance`,
    raising if it is not usable. A top-level key that gate rejected would fail
    every live run *after* the model spend, which is the most expensive place
    to discover it and the one no unit test of `pair_consistency` reaches.
    """

    LABEL = "2026-08-13_claude-opus-5-api-generic-v4_rep1"

    def test_pair_block_does_not_break_check_provenance(self):
        import tempfile

        from data_sheets_schema.runs import check_provenance
        src = Path("data/d4d_concatenated/claudecode_agent_core") / self.LABEL \
            / "CHORUS_provenance.yaml"
        if not src.exists():
            self.skipTest("v4 CHORUS record not present in this checkout")
        rec = yaml.safe_load(src.read_text(encoding="utf-8"))
        rec["pair_consistency"] = {
            "ran": True, "consistent": False, "errors": 6,
            "artifacts": {"full": {"path": "x", "md5": "y"},
                          "core": {"path": "x", "md5": "y"}}}
        # A copy. Round-tripping the real record through yaml.safe_dump would
        # strip the header comments it carries.
        tmp = Path(tempfile.mkdtemp()) / "CHORUS_provenance.yaml"
        tmp.write_text(yaml.safe_dump(rec, sort_keys=False), encoding="utf-8")
        self.assertTrue(check_provenance(
            "claudecode_agent", self.LABEL, "CHORUS", record=tmp)["ok"])


if __name__ == "__main__":
    unittest.main()


class SchemaMovedTest(unittest.TestCase):
    """#520's guard, which the first version of this check left out (#550).

    A slot added to `CoreDataset` after a pair was written is absent from that
    pair because it *could not have been present*. That is a fact about the
    schema's history, not a defect in the record, so presence divergence warns
    rather than errors when the pair predates the current schema. Content
    disagreement stays an error either way: two records asserting different
    values for one slot were wrong when they were written.

    Omitting the flag made `related_datasets` — added to core after most of the
    corpus existed — report as a defect in 70 pairs, and led me to tell the user
    the agentic arm had 100 divergent pairs of 125 when it has none of 15.
    """

    BASE = Path("data/d4d_concatenated")

    def _pairs(self, series):
        from data_sheets_schema.backfill_checks import record_paths
        out = []
        for p in sorted(self.BASE.glob(f"*_core/{series}_rep*/*_provenance.yaml")):
            q = record_paths(p)
            if q["full"].exists() and q["core"].exists():
                out.append(q)
        return out

    def _divergent(self, series, guard):
        from data_sheets_schema.d4d_pair_consistency import (
            load_pair_schema, pair_predates_current_schema, validate_pair_data,
        )
        from data_sheets_schema.provenance import CORE_SCHEMA, FULL_SCHEMA
        pairs = self._pairs(series)
        if not pairs:
            self.skipTest(f"{series} not present in this checkout")
        schema = load_pair_schema(FULL_SCHEMA, CORE_SCHEMA)
        n = 0
        for q in pairs:
            full = yaml.safe_load(q["full"].read_text(encoding="utf-8")) or {}
            core = yaml.safe_load(q["core"].read_text(encoding="utf-8")) or {}
            moved = pair_predates_current_schema(q["core"]) if guard else False
            if not validate_pair_data(full, core, schema,
                                      schema_moved=moved).passed:
                n += 1
        return n, len(pairs)

    def test_the_agentic_arm_is_clean_and_the_guard_is_why_that_is_visible(self):
        series = "2026-08-11_claude-opus-5-claudecode-generic"
        self.assertEqual(self._divergent(series, guard=True), (0, 15))
        # Without the guard, 13 of the 15 report — the two exceptions state
        # `related_datasets` in neither record, so there is no presence
        # divergence to misread. 13 reported defects where there are none is
        # what I sent upstream as "the agentic arm is not clean".
        self.assertEqual(self._divergent(series, guard=False)[0], 13)

    def test_the_v4_arm_diverges_with_the_guard_applied(self):
        """The guard does not explain the API arm away.

        All 12 v4 pairs have a moved digest too, so the guard applies to both
        arms equally. Eleven still fail, on content rather than presence.
        """
        self.assertEqual(
            self._divergent("2026-08-13_claude-opus-5-api-generic-v4",
                            guard=True), (11, 12))

    def test_the_recorded_block_says_which_reading_it_used(self):
        p = (self.BASE / "claudecode_agent_core"
             / "2026-08-11_claude-opus-5-claudecode-generic_rep1"
             / "AI_READI_provenance.yaml")
        if not p.exists():
            self.skipTest("record not present in this checkout")
        block = yaml.safe_load(p.read_text(encoding="utf-8"))["pair_consistency"]
        self.assertTrue(block["schema_moved"])
        self.assertTrue(block["consistent"])
