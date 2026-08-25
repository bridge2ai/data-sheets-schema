"""Presence is scoped to the schema a pair was generated against (#520).

Adding `related_datasets` to `CoreDataset` (#510) made 70 historical pairs
report `shared-slot-presence`. Every one of those findings is *true* — the core
record does lack a fact its full record states — and none is actionable: the
slot did not exist when the pair was written.

The obvious fix was rejected. Running `--sync-core` over them would make a
2026-07-28 core record assert content no run of that date produced, break
`validation.artifacts.*.md5`, and orphan its reconciliation report — the same
principle as `pre_registry` (#399) and the `canonical_superseded_by` tombstone
(#516): historical evidence is annotated, never rewritten to satisfy a rule
that postdates it.

So the finding is demoted to a warning for pairs that predate the current
schema, and kept fatal for pairs that do not.
"""

import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.d4d_pair_consistency import (load_pair_schema,
                                                     pair_predates_current_schema,
                                                     validate_pair_data)

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
CORE = ROOT / "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"

RELATION = [{"target_dataset": "https://e.org/other",
             "relationship_type": "supplements"}]


class TestPresenceIsScoped(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pair = load_pair_schema(FULL, CORE)
        cls.full = {"id": "https://e.org/d", "name": "x",
                    "related_datasets": RELATION}
        cls.core = {"id": "https://e.org/d", "name": "x"}

    def test_a_current_pair_still_fails(self):
        """The check must keep working for records being written now."""
        report = validate_pair_data(self.full, self.core, self.pair,
                                    schema_moved=False)
        self.assertEqual(len(report.errors), 1)
        self.assertEqual(report.errors[0].code, "shared-slot-presence")

    def test_a_pair_predating_the_schema_warns_instead(self):
        report = validate_pair_data(self.full, self.core, self.pair,
                                    schema_moved=True)
        self.assertEqual(report.errors, [])
        self.assertEqual(len(report.warnings), 1)
        self.assertTrue(report.passed)

    def test_the_warning_says_why_it_is_not_fatal(self):
        """A demoted finding that does not explain itself reads as a bug in
        the checker rather than a fact about the schema's history."""
        report = validate_pair_data(self.full, self.core, self.pair,
                                    schema_moved=True)
        self.assertIn("predates the current schema",
                      report.warnings[0].message)

    def test_content_disagreement_stays_fatal_regardless(self):
        """The exemption must not leak into the check that matters most. Two
        records asserting different values for one slot were wrong when they
        were written; no schema change excuses that."""
        core = {"id": "https://e.org/d", "name": "DIFFERENT",
                "related_datasets": RELATION}
        report = validate_pair_data(self.full, core, self.pair,
                                    schema_moved=True)
        self.assertTrue(any(i.code == "shared-slot-content"
                            for i in report.errors))


class TestTheScopeComesFromEvidence(unittest.TestCase):
    """Read from the record's own recorded schema digest, not from a date or a
    hand-maintained list of when each slot arrived — the hand-maintained-list
    problem #431 removed elsewhere and #518/#521 removed from the build."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def _pair(self, digest):
        core = self.dir / "P_d4d_core.yaml"
        core.write_text("id: x\n", encoding="utf-8")
        if digest is not None:
            (self.dir / "P_provenance.yaml").write_text(
                yaml.safe_dump({"schema": {"digest_md5": digest}}),
                encoding="utf-8")
        return core

    def test_a_stale_digest_counts_as_predating(self):
        self.assertTrue(pair_predates_current_schema(
            self._pair("0" * 32)))

    def test_the_current_digest_does_not(self):
        from data_sheets_schema import schema_digest
        live = schema_digest.fingerprint(schema_digest.digest_text("Dataset"))
        self.assertFalse(pair_predates_current_schema(self._pair(live)))

    def test_absent_provenance_is_held_to_the_current_schema(self):
        """The strict reading. A pair that cannot show it predates the schema
        does not get the exemption — silence is not a licence."""
        self.assertFalse(pair_predates_current_schema(self._pair(None)))

    def test_an_unreadable_record_is_not_fatal(self):
        core = self.dir / "P_d4d_core.yaml"
        core.write_text("id: x\n", encoding="utf-8")
        (self.dir / "P_provenance.yaml").write_bytes(b"\xff\xfe not yaml")
        self.assertFalse(pair_predates_current_schema(core))


class TestAgainstTheCorpus(unittest.TestCase):
    def test_the_canonical_arm_agrees_with_its_own_recorded_digest(self):
        """Derived from the record, not asserted about the corpus. An earlier
        version of this test asserted the canonical arm *predates* the current
        schema — true from #403 through the 2026-08-20b arm, and falsified the
        day #676 selected canonicals generated under the current schema. A
        corpus fact baked into a test breaks whenever the corpus improves; the
        behavioural claim is that `pair_predates_current_schema` answers
        exactly what the record's own `schema.digest_md5` says against the
        live digest."""
        import yaml as _yaml

        from data_sheets_schema import schema_digest
        from data_sheets_schema.runs import canonical_runs

        runs = canonical_runs()
        if not runs:
            self.skipTest("no canonical records")
        live = schema_digest.fingerprint(schema_digest.digest_text("Dataset"))
        checked = 0
        for project, info in sorted(runs.items()):
            base = (ROOT / "data/d4d_concatenated/claudecode_agent_core"
                    / info["label"])
            core = base / f"{project}_d4d_core.yaml"
            prov = base / f"{project}_provenance.yaml"
            if not core.exists() or not prov.exists():
                continue
            checked += 1
            with self.subTest(project=project):
                # Mirror the function's own branches: absent or unreadable
                # provenance is held to the current schema (returns False),
                # so the test must not error where the function answers.
                try:
                    rec = _yaml.safe_load(
                        prov.read_text(encoding="utf-8")) or {}
                    recorded = (rec.get("schema") or {}).get("digest_md5")
                except Exception:
                    recorded = None
                expected = bool(recorded) and recorded != live
                self.assertEqual(expected, pair_predates_current_schema(core))
        if not checked:
            self.skipTest("no canonical pair has both core and provenance "
                          "on disk — nothing was tested, and a silent green "
                          "here would claim otherwise")
