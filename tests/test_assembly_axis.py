"""`condition_delta` can see a runner-side assembly change when given records.

Why this exists (#1073): `CONDITION_AXES` records two axes per condition —
which generic base a condition is built on, and whether it is tuned — and both
are properties of the *prompt*. A change to how the runner assembles a request
is invisible to them.

That is not hypothetical. The declared-scope block (#932) landed after all
twelve v8 records were generated, so a v9 run differs from the retained v8
corpus by that block *and* the two prompt rules, while
`condition_delta("generic_v8", "generic_v9")` returned `["base"]` and a pull
request body written from it claimed the comparison measured the rules alone.
The information already existed — `assembly_digest` fingerprints the layout and
the phase instructions precisely so a change of this kind is visible in
provenance (#353) — and what was missing was the join.

The axis is only ever reported from evidence, never inferred from a name: the
assembly of a run that has not happened yet is not knowable from a condition
name, which is why the axes were prompt-only to begin with.
"""
import unittest

from data_sheets_schema.api_runner import (assembly_digests,
                                           comparable_conditions,
                                           condition_delta, confounded_note)


def _record(digest):
    return {"prompts": {"assembly": {"sha256": digest}}}


class AssemblyDigestsTest(unittest.TestCase):
    def test_the_shapes_a_caller_already_has(self):
        self.assertEqual(assembly_digests(_record("a")), frozenset({"a"}))
        self.assertEqual(assembly_digests([_record("a"), _record("b")]),
                         frozenset({"a", "b"}))
        self.assertEqual(assembly_digests("a"), frozenset({"a"}))
        self.assertEqual(assembly_digests(["a", "b"]), frozenset({"a", "b"}))

    def test_what_it_cannot_read_contributes_nothing(self):
        """An arm predating the digest yields an empty set, which makes the
        axis unavailable rather than falsely different."""
        for source in (None, {}, [{}], [{"prompts": {}}],
                       [{"prompts": {"assembly": {}}}], 7):
            with self.subTest(source=source):
                self.assertEqual(assembly_digests(source), frozenset())


class ConditionDeltaTest(unittest.TestCase):
    def test_without_records_the_answer_is_the_prompt_only_one(self):
        self.assertEqual(condition_delta("generic_v8", "generic_v9"), ["base"])

    def test_with_records_a_moved_assembly_is_an_axis(self):
        self.assertEqual(
            condition_delta("generic_v8", "generic_v9",
                            [_record("aaa")], [_record("bbb")]),
            ["base", "assembly"])

    def test_an_unmoved_assembly_adds_nothing(self):
        self.assertEqual(
            condition_delta("generic_v8", "generic_v9",
                            [_record("aaa")], [_record("aaa")]),
            ["base"])

    def test_one_side_missing_leaves_the_axis_unavailable(self):
        """Not "the same": an arm whose records carry no digest supports no
        claim about its assembly either way."""
        self.assertEqual(
            condition_delta("generic_v8", "generic_v9", [_record("aaa")], [{}]),
            ["base"])

    def test_an_arm_that_is_internally_inconsistent_differs(self):
        """Two digests inside one arm means it was not generated under one
        assembly, so it is not equal to any single-assembly arm."""
        self.assertEqual(
            condition_delta("generic_v8", "generic_v9",
                            [_record("aaa"), _record("bbb")], [_record("aaa")]),
            ["base", "assembly"])

    def test_an_unknown_condition_still_short_circuits(self):
        self.assertEqual(condition_delta("generic_v8", "nope", [_record("a")],
                                         [_record("b")]),
                         ["unknown condition"])


class ComparableConditionsTest(unittest.TestCase):
    def test_adjacent_bases_are_comparable_on_names_alone(self):
        self.assertTrue(comparable_conditions("generic_v8", "generic_v9"))

    def test_a_moved_assembly_makes_them_not_comparable(self):
        """Two axes moved, so the existing one-axis rule refuses it — no new
        branch, which is the point: the axis is an axis."""
        self.assertFalse(comparable_conditions("generic_v8", "generic_v9",
                                               [_record("aaa")],
                                               [_record("bbb")]))

    def test_the_note_names_the_assembly_and_where_it_read_it(self):
        note = confounded_note("generic_v8", "generic_v9",
                               [_record("aaa")], [_record("bbb")])
        self.assertIn("base and assembly", note)
        self.assertIn("prompts.assembly.sha256", note)

    def test_no_note_when_only_the_base_moved(self):
        self.assertIsNone(confounded_note("generic_v8", "generic_v9",
                                          [_record("aaa")], [_record("aaa")]))


class TheRealArmsTest(unittest.TestCase):
    """The case that motivated this, read off the corpus rather than a
    fixture: v7 and v8 production were generated under different assemblies,
    which the condition names alone do not say."""

    def test_v7_and_v8_production_differ_on_assembly(self):
        from data_sheets_schema.runs import arm_assembly_digests
        v7 = arm_assembly_digests("2026-09-01_claude-opus-5-api-generic-v7")
        v8 = arm_assembly_digests("2026-09-04f_claude-opus-5-api-generic-v8")
        if not (v7 and v8):
            self.skipTest("the production records are not in this checkout")
        self.assertEqual(len(v7), 1, v7)
        self.assertEqual(len(v8), 1, v8)
        self.assertNotEqual(v7, v8)
        self.assertEqual(condition_delta("generic_v7", "generic_v8", v7, v8),
                         ["base", "assembly"])
        self.assertFalse(comparable_conditions("generic_v7", "generic_v8",
                                               v7, v8))


if __name__ == "__main__":
    unittest.main()
