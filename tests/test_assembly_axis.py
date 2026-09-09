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


A = "a" * 64
B = "b" * 64


def _record(digest):
    return {"prompts": {"assembly": {"sha256": digest}}}


class AssemblyDigestsTest(unittest.TestCase):
    def test_the_shapes_a_caller_already_has(self):
        self.assertEqual(assembly_digests(_record(A)), frozenset({A}))
        self.assertEqual(assembly_digests([_record(A), _record(B)]),
                         frozenset({A, B}))
        self.assertEqual(assembly_digests(A), frozenset({A}))
        self.assertEqual(assembly_digests([A, B]), frozenset({A, B}))

    def test_a_mapping_of_records_by_project_is_read(self):
        """The natural in-memory shape here, and the one most likely to be
        passed. It used to read as no records at all (#1092)."""
        self.assertEqual(
            assembly_digests({"AI_READI": _record(A), "CHORUS": _record(B)}),
            frozenset({A, B}))

    def test_what_it_cannot_read_contributes_nothing(self):
        """An arm predating the digest yields an empty set — which
        `condition_delta` reports as unmeasured, not as agreement."""
        for source in (None, {}, [{}], [{"prompts": {}}],
                       [{"prompts": {"assembly": {}}}], 7):
            with self.subTest(source=source):
                self.assertEqual(assembly_digests(source), frozenset())

    def test_a_malformed_record_does_not_raise(self):
        """`or {}` let a truthy non-dict through and crashed on `.get` — the
        opposite of what the docstring promised (#1092). `runs._dig` had it
        right ten lines away."""
        for source in ({"prompts": [{"assembly": {"sha256": A}}]},
                       {"prompts": {"assembly": "aaa"}},
                       {"prompts": {"assembly": {"sha256": 7}}},
                       b"aaa"):
            with self.subTest(source=source):
                self.assertEqual(assembly_digests(source), frozenset())

    def test_only_something_shaped_like_a_digest_counts(self):
        """A path passed where a digest was meant became a digest of its own,
        and two different paths reported two arms as differing (#1092)."""
        for source in ("data/d4d_concatenated/x/AI_READI_provenance.yaml",
                       "", "None", A.upper(), A[:-1]):
            with self.subTest(source=source):
                self.assertEqual(assembly_digests(source), frozenset())

    def test_a_lazy_sequence_that_fails_partway_keeps_what_it_read(self):
        """Discarding the partial result puts a half-read arm in the same
        bucket as an unread one (#1092)."""
        def gen():
            yield _record(A)
            raise TypeError("boom")
        self.assertEqual(assembly_digests(gen()), frozenset({A}))


class ConditionDeltaTest(unittest.TestCase):
    def test_without_records_the_answer_is_the_prompt_only_one(self):
        self.assertEqual(condition_delta("generic_v8", "generic_v9"), ["base"])

    def test_with_records_a_moved_assembly_is_an_axis(self):
        self.assertEqual(
            condition_delta("generic_v8", "generic_v9",
                            [_record(A)], [_record(B)]),
            ["base", "assembly"])

    def test_an_unmoved_assembly_adds_nothing(self):
        self.assertEqual(
            condition_delta("generic_v8", "generic_v9",
                            [_record(A)], [_record(A)]),
            ["base"])

    def test_asked_and_unreadable_is_its_own_axis_not_agreement(self):
        """#1092, the blocking finding of the review of this branch.

        Gating on "both sides have digests" made an empty side return exactly
        the prompt-only answer #1073 was filed against, with nothing saying
        so — and `arm_facts` yields empty facts for a mistyped label prefix
        rather than raising, so one capital letter was enough. The
        repository's precedent is that an absent measurement is a third
        answer: `pre_registry` beside `uncanonical`, `runtime_cannot_capture`
        beside `missing`, UNMEASURABLE beside a held floor.
        """
        for a, b in (([_record(A)], [{}]), ([{}], [_record(A)]), ([{}], [{}]),
                     ([_record(A)], [])):
            with self.subTest(a=a, b=b):
                self.assertEqual(
                    condition_delta("generic_v8", "generic_v9", a, b),
                    ["base", "assembly unmeasured"])

    def test_not_asking_is_still_not_asking(self):
        """Passing neither side keeps the prompt-only answer: the assembly of
        a run that has not happened yet is not knowable from a name."""
        self.assertEqual(
            condition_delta("generic_v8", "generic_v9", None, None), ["base"])

    def test_an_arm_built_two_ways_has_no_value_on_the_axis(self):
        """Not a difference — an absence of a value (#1092).

        The first version called it a difference and used set equality, so two
        arms each carrying the same two digests compared **equal** and no axis
        was reported at all, while the docstring claimed the opposite.
        `d4d runs compare-arms` has always reported "not constant within this
        arm" separately, which is the right shape: folding it into a
        difference makes `confounded_note` say the runner built the two arms
        differently when it built one arm two ways.
        """
        for a, b in (([_record(A), _record(B)], [_record(A)]),
                     ([_record(A)], [_record(A), _record(B)]),
                     ([_record(A), _record(B)], [_record(A), _record(B)])):
            with self.subTest(a=len(a), b=len(b)):
                self.assertEqual(
                    condition_delta("generic_v8", "generic_v9", a, b),
                    ["base", "assembly not constant"])

    def test_an_unknown_condition_still_short_circuits(self):
        self.assertEqual(condition_delta("generic_v8", "nope", [_record(A)],
                                         [_record(B)]),
                         ["unknown condition"])


class ComparableConditionsTest(unittest.TestCase):
    def test_adjacent_bases_are_comparable_on_names_alone(self):
        self.assertTrue(comparable_conditions("generic_v8", "generic_v9"))

    def test_a_moved_assembly_makes_them_not_comparable(self):
        """Two axes moved, so the existing one-axis rule refuses it — no new
        branch, which is the point: the axis is an axis."""
        self.assertFalse(comparable_conditions("generic_v8", "generic_v9",
                                               [_record(A)], [_record(B)]))

    def test_an_unmeasured_assembly_also_makes_them_not_comparable(self):
        """A caller that asked for the axis and could not get it has not
        established comparability (#1092)."""
        self.assertFalse(comparable_conditions("generic_v8", "generic_v9",
                                               [_record(A)], [{}]))

    def test_the_note_names_the_assembly_and_where_it_read_it(self):
        note = confounded_note("generic_v8", "generic_v9",
                               [_record(A)], [_record(B)])
        self.assertIn("base and assembly", note)
        self.assertIn("prompts.assembly.sha256", note)

    def test_the_note_says_when_the_axis_could_not_be_read(self):
        note = confounded_note("generic_v8", "generic_v9",
                               [_record(A)], [{}])
        self.assertIn("could not be read", note)
        self.assertIn("not agreement", note)

    def test_the_note_says_when_an_arm_is_not_constant(self):
        note = confounded_note("generic_v8", "generic_v9",
                               [_record(A), _record(B)], [_record(A)])
        self.assertIn("more than one", note)
        self.assertIn("compare-arms", note)

    def test_the_docstring_says_the_axis_is_one_field_of_five(self):
        """#1092: `runs.arm_confounds` reads five procedure fields and is the
        record-based answer. On the v7-against-v8 pair the records also differ
        on the schema digest, so this delta under-reports the evidence — which
        it must say rather than look record-based and be narrower."""
        self.assertIn("one field of the five", condition_delta.__doc__)
        self.assertIn("arm_confounds", condition_delta.__doc__)

    def test_no_note_when_only_the_base_moved(self):
        self.assertIsNone(confounded_note("generic_v8", "generic_v9",
                                          [_record(A)], [_record(A)]))


class TheRealArmsTest(unittest.TestCase):
    """The case that motivated this, read off the corpus rather than a
    fixture: v7 and v8 production were generated under different assemblies,
    which the condition names alone do not say."""

    #: Both v8 label prefixes, because they are one arm launched twice
    #: (04f carried CHORUS and VOICE, 04g AI_READI and CM4AI).
    V8 = ("2026-09-04f_claude-opus-5-api-generic-v8",
          "2026-09-04g_claude-opus-5-api-generic-v8")
    V7 = "2026-09-01_claude-opus-5-api-generic-v7"

    def _digests(self, prefix):
        from data_sheets_schema.runs import arm_assembly_digests
        try:
            return arm_assembly_digests(prefix)
        except LookupError:
            self.skipTest(f"no records under {prefix} in this checkout")

    def test_v7_and_v8_production_differ_on_assembly(self):
        v7 = self._digests(self.V7)
        v8 = sorted({d for p in self.V8 for d in self._digests(p)})
        self.assertEqual(len(v7), 1, v7)
        self.assertEqual(len(v8), 1, "the v8 halves are one assembly: %s" % v8)
        self.assertNotEqual(sorted(v7), v8)
        self.assertEqual(condition_delta("generic_v7", "generic_v8", v7, v8),
                         ["base", "assembly"])
        self.assertFalse(comparable_conditions("generic_v7", "generic_v8",
                                               v7, v8))

    def test_a_mistyped_label_prefix_raises_rather_than_reading_as_empty(self):
        """#1092: it used to yield no digests, which made the axis vanish and
        returned the very answer #1073 was filed against."""
        from data_sheets_schema.runs import arm_assembly_digests
        self._digests(self.V7)          # skip unless the corpus is here
        with self.assertRaises(LookupError):
            arm_assembly_digests(self.V7.replace("2026-09-01", "2026-09-01X"))


if __name__ == "__main__":
    unittest.main()
