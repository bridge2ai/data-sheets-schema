"""Referent coherence and guarded merging.

The case that matters is CM4AI's: replicates that agree on every field they share
while one of them quietly describes a single release rather than the whole
programme. A check that only compares shared fields cannot see it, which is how
an incoherent record got written and passed schema validation.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sheets_schema.merge import (
    AGREE,
    ASYMMETRIC,
    REFERENTIAL,
    REPRESENTATIONAL,
    ReferentJudgement,
    _parse_referent,
    referent_report,
    union_merge,
    write_merge,
)


def judge(same=True, reason="test"):
    def _j(*, slot, values):
        return ReferentJudgement(same_referent=same, reason=reason)
    return _j


def fitness(mapping, default=0.9):
    """Scorer keyed on the rendered value, returning a bare float."""
    def _s(*, project, slot, value):
        return mapping.get((slot, str(value)), default)
    return _s


class TestAsymmetry(unittest.TestCase):
    """The signal the first version of this check inverted."""

    def test_identity_field_in_one_replicate_only_is_asymmetric(self):
        recs = {"a": {"title": "T", "doi": "doi:10.1/X"},
                "b": {"title": "T"},
                "c": {"title": "T"}}
        rep = referent_report(recs, judge=judge())
        f = next(x for x in rep.findings if x.slot == "doi")
        self.assertEqual(f.kind, ASYMMETRIC)
        self.assertEqual(f.holders, ["a"])
        self.assertEqual(f.missing, ["b", "c"])
        self.assertFalse(rep.coherent)
        self.assertIn("doi", rep.verdict)

    def test_the_cm4ai_shape_is_caught(self):
        """One replicate pins a release; the others describe the programme.

        Every shared field agrees, so a comparison-only check reports nothing.
        """
        recs = {
            "rep1": {"title": "CM4AI Data Releases", "status": "Beta"},
            "rep2": {"title": "CM4AI Data Releases", "status": "Beta",
                     "version": "Dataverse version 2.0",
                     "issued": "2026-06-17T00:00:00Z",
                     "doi": "doi:10.18130/V3/HIGT4C"},
            "rep3": {"title": "CM4AI Data Releases", "status": "Beta"},
        }
        rep = referent_report(recs, judge=judge())
        self.assertFalse(rep.coherent)
        self.assertEqual({f.slot for f in rep.blocking},
                         {"version", "issued", "doi"})
        self.assertIn("only some replicates", rep.verdict)

    def test_missing_naming_field_is_not_asymmetric(self):
        """An absent title is an omission, not a different subject."""
        recs = {"a": {"title": "T", "doi": "d"}, "b": {"doi": "d"}}
        rep = referent_report(recs, judge=judge())
        self.assertNotIn("title", {f.slot for f in rep.blocking})
        self.assertTrue(rep.coherent)


class TestRepresentationalVsReferential(unittest.TestCase):

    def test_normalisation_handles_scheme_case_and_slash(self):
        recs = {"a": {"landing_page": "https://Example.org/Data/"},
                "b": {"landing_page": "example.org/Data"}}
        f = referent_report(recs, judge=judge(same=False)).findings[0]
        self.assertEqual(f.kind, AGREE, "should not have reached the judge")

    def test_judge_marks_licence_url_vs_label_representational(self):
        recs = {"a": {"license": "https://creativecommons.org/licenses/by-nc-sa/4.0/"},
                "b": {"license": "CC BY-NC-SA 4.0"}}
        rep = referent_report(recs, judge=judge(same=True))
        self.assertEqual(rep.findings[0].kind, REPRESENTATIONAL)
        self.assertTrue(rep.coherent, "form differences must not block a merge")
        self.assertIn("differ only in form", rep.verdict)

    def test_judge_marks_programme_vs_release_referential(self):
        recs = {"a": {"title": "CM4AI Data Release Programme"},
                "b": {"title": "CM4AI June 2026 Data Release"}}
        rep = referent_report(recs, judge=judge(same=False))
        self.assertEqual(rep.findings[0].kind, REFERENTIAL)
        self.assertFalse(rep.coherent)

    def test_no_judge_defaults_to_refusing(self):
        """Without a semantic judge, an unexplained difference must not pass."""
        recs = {"a": {"license": "URL-form"}, "b": {"license": "label-form"}}
        rep = referent_report(recs, judge=None)
        self.assertEqual(rep.findings[0].kind, REFERENTIAL)
        self.assertIn("safe default", rep.findings[0].reason)


class TestGuardedMerge(unittest.TestCase):

    def test_unguarded_merge_is_refused_when_incoherent(self):
        recs = {"a": {"x": 1, "doi": "d"}, "b": {"x": 1}}
        with self.assertRaises(ValueError) as ctx:
            union_merge(recs, guarded=False, judge=judge())
        self.assertIn("refusing an unguarded merge", str(ctx.exception))

    def test_guarded_merge_takes_all_referent_fields_from_one_base(self):
        """The fix for the incoherent CM4AI record.

        Unguarded, the title came from the programme replicate and the DOI from
        the release replicate. Guarded, both come from the base or neither does.
        """
        recs = {
            "prog": {"title": "Programme", "a": 1, "b": 2, "c": 3},
            "rel": {"title": "June Release", "doi": "doi:10.1/X",
                    "version": "2.0", "a": 1},
        }
        r = union_merge(recs, base="prog", guarded=True, judge=judge(same=False))
        self.assertEqual(r.record["title"], "Programme")
        self.assertNotIn("doi", r.record,
                         "an identity the base never asserted must not be imported")
        self.assertNotIn("version", r.record)

    def test_guarded_merge_still_gains_non_referent_coverage(self):
        recs = {"a": {"title": "T", "x": 1},
                "b": {"title": "T", "y": 2, "z": 3}}
        r = union_merge(recs, base="a", guarded=True, judge=judge())
        self.assertEqual(set(r.record), {"title", "x", "y", "z"})
        self.assertEqual(r.source_of["y"], "b")

    def test_contested_slots_go_to_the_best_fitting_value(self):
        recs = {"a": {"s": "weak"}, "b": {"s": "strong"}}
        r = union_merge(recs, scorer=fitness({("s", "strong"): 1.0,
                                              ("s", "weak"): 0.2}),
                        base="a", guarded=True, judge=judge())
        self.assertEqual(r.record["s"], "strong")
        self.assertEqual(r.source_of["s"], "b")
        self.assertEqual(r.contested, 1)

    def test_ties_break_toward_the_base(self):
        """Keeps the merge as close to one coherent record as evidence allows."""
        recs = {"a": {"s": "A"}, "b": {"s": "B"}}
        r = union_merge(recs, scorer=fitness({}, default=0.9),
                        base="b", guarded=True, judge=judge())
        self.assertEqual(r.record["s"], "B")

    def test_base_defaults_to_the_widest_record(self):
        recs = {"a": {"x": 1}, "b": {"x": 1, "y": 2, "z": 3}}
        self.assertEqual(union_merge(recs, judge=judge()).base, "b")

    def test_contributions_are_reported(self):
        recs = {"a": {"x": 1, "y": 1}, "b": {"z": 1}}
        r = union_merge(recs, base="a", guarded=True, judge=judge())
        self.assertEqual(r.contributions, {"a": 2, "b": 1})

    def test_write_merge_roundtrips(self):
        import yaml
        recs = {"a": {"title": "T", "x": 1}, "b": {"title": "T", "y": 2}}
        r = union_merge(recs, base="a", guarded=True, judge=judge())
        with TemporaryDirectory() as td:
            p = write_merge(r, Path(td) / "nested" / "m.yaml")
            self.assertEqual(yaml.safe_load(p.read_text()), r.record)


class TestParseReferent(unittest.TestCase):

    def test_full_reply(self):
        j = _parse_referent('{"same_referent": false, "reason": "different DOI"}')
        self.assertFalse(j.same_referent)
        self.assertEqual(j.reason, "different DOI")

    def test_truncated_reply_recovers_the_verdict(self):
        j = _parse_referent('{"same_referent": true, "reason": "the licence UR')
        self.assertTrue(j.same_referent)
        self.assertIn("truncated", j.reason)

    def test_unreadable_reply_raises_rather_than_defaulting(self):
        """Defaulting True would wave through the fork this check exists to catch."""
        with self.assertRaises(ValueError):
            _parse_referent("")

    def test_reply_without_the_field_raises(self):
        with self.assertRaises(ValueError):
            _parse_referent('{"reason": "forgot the verdict"}')


if __name__ == "__main__":
    unittest.main()
