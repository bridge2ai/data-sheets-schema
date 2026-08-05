"""The three VOICE failure modes must stay distinguishable (#292).

All three 2026-07-31 replicates fail `related_datasets`, each differently, and
`linkml-validate` reports them as three unrelated errors. The rerun's answer
differs per mode:

    inline_target   an object where the schema declares a string. #297: LinkML
                    cannot express string-or-inline, so only validation catches
                    it. generic-v4 adds a rule (#338); recurrence retires it.
    aliased_type    a DataCite spelling the enum declares as an `alias` (#223).
                    `normalise_enum_aliases` rewrites these on the write path,
                    so recurrence means the normaliser did not run.
    unknown_type    `related_to`, not an alias of anything. DataCite's 36
                    relation types are deliberately specific and have no generic
                    "is related to", so this is a real generation failure and is
                    left failing rather than normalised into something valid.

Reading three tracebacks and remembering which was which is how "did the rerun
fix it" gets answered wrong. These pin the classification against the actual
replicates, so the question is answerable mechanically afterwards.
"""

import unittest
from pathlib import Path

import yaml

from data_sheets_schema.related_datasets import (ALIASED_TYPE, INLINE_TARGET,
                                                 UNKNOWN_TYPE, Defect, inspect,
                                                 summarise)

REPO = Path(__file__).resolve().parents[2]
REPLICATES = REPO / "data" / "d4d_concatenated" / "claudecode_agent"
LABEL = "2026-07-31_claude-opus-5-generic-v2_{rep}"


def _voice(rep):
    path = REPLICATES / LABEL.format(rep=rep) / "VOICE_d4d.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class TestTheKnownFailures(unittest.TestCase):
    """Pinned against the real replicates, not fixtures.

    A fixture would encode what I believe the failures are; these encode what
    they actually are, which is the point of a regression baseline.
    """

    def test_rep1_is_an_inline_target(self):
        record = _voice("rep1")
        if record is None:
            self.skipTest("replicate not on disk")
        self.assertEqual([d.mode for d in inspect(record)], [INLINE_TARGET])

    def test_rep2_is_an_unknown_relationship_type(self):
        record = _voice("rep2")
        if record is None:
            self.skipTest("replicate not on disk")
        modes = [d.mode for d in inspect(record)]
        self.assertEqual(modes, [UNKNOWN_TYPE])
        self.assertIn("related_to", inspect(record)[0].detail)

    def test_rep3_is_three_aliased_types_not_one(self):
        """`linkml-validate` stops at the first. All three entries are bad, and
        a checker that stopped early would call rep3 fixed as soon as the
        ordering changed."""
        record = _voice("rep3")
        if record is None:
            self.skipTest("replicate not on disk")
        defects = inspect(record)
        self.assertEqual([d.mode for d in defects], [ALIASED_TYPE] * 3)
        self.assertEqual([d.index for d in defects], [0, 1, 2])

    def test_the_three_replicates_fail_differently(self):
        """The premise of separating them at all."""
        modes = set()
        for rep in ("rep1", "rep2", "rep3"):
            record = _voice(rep)
            if record is None:
                self.skipTest("replicates not on disk")
            modes |= {d.mode for d in inspect(record)}
        self.assertEqual(modes, {INLINE_TARGET, UNKNOWN_TYPE, ALIASED_TYPE})


class TestClassification(unittest.TestCase):

    def test_a_permissible_value_is_not_a_defect(self):
        self.assertEqual(inspect({"related_datasets": [
            {"relationship_type": "has_part",
             "target_dataset": "https://doi.org/10.1234/x"}]}), [])

    def test_an_alias_is_distinguished_from_an_invention(self):
        """Both are "not a permissible value"; only one is the schema's fault.

        An alias means the schema declared the name valid and validation
        rejected it, which the write-path normaliser fixes. An invention means
        the model reached for a word the vocabulary lacks, which it does not.
        """
        aliased = inspect({"related_datasets": [
            {"relationship_type": "IsNewVersionOf", "target_dataset": "x"}]})
        invented = inspect({"related_datasets": [
            {"relationship_type": "related_to", "target_dataset": "x"}]})
        self.assertEqual([d.mode for d in aliased], [ALIASED_TYPE])
        self.assertEqual([d.mode for d in invented], [UNKNOWN_TYPE])

    def test_an_inline_target_is_reported_whatever_the_type_is(self):
        """rep1's `relationship_type` is valid; only its target is wrong."""
        defects = inspect({"related_datasets": [
            {"relationship_type": "has_part",
             "target_dataset": {"id": "x", "title": "A dataset"}}]})
        self.assertEqual([d.mode for d in defects], [INLINE_TARGET])

    def test_both_defects_in_one_entry_are_reported(self):
        defects = inspect({"related_datasets": [
            {"relationship_type": "related_to", "target_dataset": {"id": "x"}}]})
        self.assertEqual({d.mode for d in defects}, {INLINE_TARGET, UNKNOWN_TYPE})

    def test_every_bad_entry_is_reported_not_just_the_first(self):
        defects = inspect({"related_datasets": [
            {"relationship_type": "has_part", "target_dataset": "ok"},
            {"relationship_type": "related_to", "target_dataset": "x"},
            {"relationship_type": "References", "target_dataset": "y"},
        ]})
        self.assertEqual([(d.index, d.mode) for d in defects],
                         [(1, UNKNOWN_TYPE), (2, ALIASED_TYPE)])

    def test_a_bare_mapping_is_accepted_as_well_as_a_list(self):
        defects = inspect({"related_datasets":
                           {"relationship_type": "related_to",
                            "target_dataset": "x"}})
        self.assertEqual([d.mode for d in defects], [UNKNOWN_TYPE])

    def test_an_absent_slot_is_not_a_defect(self):
        self.assertEqual(inspect({}), [])
        self.assertEqual(inspect({"related_datasets": None}), [])


class TestOwnership(unittest.TestCase):
    """Each mode names what would address it, or says nothing does."""

    def test_the_inline_target_points_at_v4(self):
        defect = Defect(0, INLINE_TARGET, "x")
        self.assertEqual(defect.addressed_by, "generic_v4")

    def test_the_other_two_claim_no_prompt_rule(self):
        """`aliased_type` is a pipeline concern and `unknown_type` a real
        generation failure. Naming a prompt version for either would suggest
        the next run fixes it."""
        for mode in (ALIASED_TYPE, UNKNOWN_TYPE):
            with self.subTest(mode=mode):
                self.assertIsNone(Defect(0, mode, "x").addressed_by)

    def test_the_summary_names_the_owner(self):
        line = summarise([Defect(0, INLINE_TARGET, "x"),
                          Defect(1, UNKNOWN_TYPE, "y")])
        self.assertIn("generic_v4", line)
        self.assertIn("#292", line)

    def test_no_defects_says_so(self):
        self.assertIn("no defects", summarise([]))


class TestTheCanonicalSetIsClean(unittest.TestCase):
    """The three failing replicates are VOICE, which has no canonical record.

    If a canonical record ever carries one of these, selection admitted a record
    that does not validate — which is the criterion selection is built on.
    """

    def test_no_canonical_record_has_a_related_datasets_defect(self):
        from data_sheets_schema.evaluation_plan import NothingSelected, plan
        try:
            paths = {e.path for e in plan()}
        except NothingSelected:
            self.skipTest("no canonical record on disk")
        for path in sorted(paths):
            record = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
            with self.subTest(record=Path(path).name):
                self.assertEqual(inspect(record), [])


if __name__ == "__main__":
    unittest.main()
