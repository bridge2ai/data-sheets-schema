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

    def test_missing_record_is_none_rather_than_consistent(self):
        from data_sheets_schema.api_runner import pair_consistency
        spec = self._spec("NO_SUCH_PROJECT")
        self.assertIsNone(pair_consistency(spec))


if __name__ == "__main__":
    unittest.main()
