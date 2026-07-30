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


class TestDerivedProvenance(unittest.TestCase):
    """A merged record must be able to say how it came to exist (#176 step 2).

    `provenance.py` had no mode for "consumed other generated records", so a
    merged record could claim `live` (asserting a generation that never
    happened), `reconstructed` (implying an original run to recover), or nothing
    at all. That is what kept merged records unshippable.
    """

    def _sources(self, td):
        """Fixtures carry provenance, because unattested sources are refused.

        A merge may only consume runs whose conditions can be established, so a
        fixture without provenance is correctly rejected — the test has to build
        sources that would really be admissible.
        """
        import yaml
        root = Path(td) / "data" / "d4d_concatenated"
        srcs = {}
        for n, slots in ((1, {"title": "T", "a": 1}), (2, {"title": "T", "b": 2})):
            label = f"lab_rep{n}"
            p = root / "claudecode_agent" / label / "P_d4d.yaml"
            p.parent.mkdir(parents=True)
            p.write_text(yaml.safe_dump(slots))
            prov = root / "claudecode_agent_core" / label / "P_provenance.yaml"
            prov.parent.mkdir(parents=True)
            prov.write_text(yaml.safe_dump({
                "record_mode": "live",
                "inputs": {"bundle_md5": "a",
                           "hash_basis": "verified identical to the bytes consumed"},
                "schema": {"full_md5": "s"}, "model": {"model": "m"},
                "outputs": {"full": {"md5": "x"}}}))
            srcs[f"rep{n}"] = p
        return srcs

    def test_sources_are_pinned_by_md5(self):
        import yaml
        from data_sheets_schema.evidence_score import load_record
        with TemporaryDirectory() as td:
            srcs = self._sources(td)
            recs = {k: load_record(v) for k, v in srcs.items()}
            r = union_merge(recs, base="rep1", guarded=True, judge=judge())
            out = Path(td) / "merged" / "P_d4d.yaml"
            write_merge(r, out, sources=srcs, project="P",
                        method="claudecode_agent_merged", label="lab")
            rec = yaml.safe_load(
                (out.parent / "P_provenance.yaml").read_text())
            self.assertEqual(rec["record_mode"], "derived")
            self.assertEqual(rec["record_type"], "d4d_derived_provenance")
            self.assertEqual(len(rec["sources"]), 2)
            for src in rec["sources"]:
                self.assertTrue(src["md5"], "a named source is not a pinned one")

    def test_source_method_is_the_source_not_the_merge(self):
        """A record generated by claudecode_agent does not become a merged one."""
        import yaml
        from data_sheets_schema.evidence_score import load_record
        with TemporaryDirectory() as td:
            srcs = self._sources(td)
            recs = {k: load_record(v) for k, v in srcs.items()}
            r = union_merge(recs, base="rep1", guarded=True, judge=judge())
            out = Path(td) / "merged" / "P_d4d.yaml"
            write_merge(r, out, sources=srcs, project="P",
                        method="claudecode_agent_merged", label="lab")
            rec = yaml.safe_load((out.parent / "P_provenance.yaml").read_text())
            self.assertEqual({s["method"] for s in rec["sources"]},
                             {"claudecode_agent"})

    def test_model_and_prompt_are_marked_not_applicable(self):
        """Absence must be stated, not left for a reader to infer."""
        import yaml
        from data_sheets_schema.evidence_score import load_record
        with TemporaryDirectory() as td:
            srcs = self._sources(td)
            recs = {k: load_record(v) for k, v in srcs.items()}
            r = union_merge(recs, base="rep1", guarded=True, judge=judge())
            out = Path(td) / "merged" / "P_d4d.yaml"
            write_merge(r, out, sources=srcs, project="P",
                        method="claudecode_agent_merged", label="lab")
            rec = yaml.safe_load((out.parent / "P_provenance.yaml").read_text())
            fields = {n["field"] for n in rec["not_applicable"]}
            self.assertEqual(fields, {"model", "prompts", "inputs.bundle_md5"})
            self.assertNotIn("model", rec)

    def test_a_derived_record_must_name_sources(self):
        from data_sheets_schema.provenance import build_derived_record
        with self.assertRaises(ValueError):
            build_derived_record("P", "m", "l", sources=[], derivation="x",
                                 outputs={})

    def test_writing_without_sources_writes_no_provenance(self):
        """Probes may write a bare record; it just must not look provenanced."""
        from data_sheets_schema.evidence_score import load_record
        with TemporaryDirectory() as td:
            srcs = self._sources(td)
            recs = {k: load_record(v) for k, v in srcs.items()}
            r = union_merge(recs, base="rep1", guarded=True, judge=judge())
            out = Path(td) / "merged" / "P_d4d.yaml"
            write_merge(r, out)
            self.assertTrue(out.exists())
            self.assertFalse((out.parent / "P_provenance.yaml").exists())

    def test_contributed_slots_sum_to_the_record(self):
        import yaml
        from data_sheets_schema.evidence_score import load_record
        with TemporaryDirectory() as td:
            srcs = self._sources(td)
            recs = {k: load_record(v) for k, v in srcs.items()}
            r = union_merge(recs, base="rep1", guarded=True, judge=judge())
            out = Path(td) / "merged" / "P_d4d.yaml"
            write_merge(r, out, sources=srcs, project="P",
                        method="claudecode_agent_merged", label="lab")
            rec = yaml.safe_load((out.parent / "P_provenance.yaml").read_text())
            self.assertEqual(sum(s["contributed_slots"] for s in rec["sources"]),
                             len(r.record))


class TestDerivedRecordRequiresItsArtifact(unittest.TestCase):
    """A derived record exists to describe an artifact (#189).

    Unlike a generation record, where a phase may legitimately not have produced
    a report, a derived record whose output is missing describes nothing — yet
    would still be discovered and counted as provenance.
    """

    def _source(self):
        from data_sheets_schema.provenance import Contribution
        return Contribution(label="r1", project="P", method="m", path="p",
                            md5="abc", slots=1)

    def test_missing_output_is_refused(self):
        from data_sheets_schema.provenance import build_derived_record
        with self.assertRaises(FileNotFoundError):
            build_derived_record("P", "m", "L", sources=[self._source()],
                                 derivation="rule",
                                 outputs={"full": Path("/nonexistent.yaml")})

    def test_empty_outputs_is_refused(self):
        from data_sheets_schema.provenance import build_derived_record
        with self.assertRaises(FileNotFoundError):
            build_derived_record("P", "m", "L", sources=[self._source()],
                                 derivation="rule", outputs={})

    def test_existing_output_is_accepted(self):
        from data_sheets_schema.provenance import build_derived_record
        with TemporaryDirectory() as td:
            f = Path(td) / "r.yaml"
            f.write_text("id: x\n")
            rec = build_derived_record("P", "m", "L", sources=[self._source()],
                                       derivation="rule", outputs={"full": f})
            self.assertTrue(rec.data["outputs"]["full"]["md5"])


class TestConditionComparability(unittest.TestCase):
    """A comparison must isolate one change (#190)."""

    def test_the_v2_experiment_is_comparable(self):
        from data_sheets_schema.api_runner import comparable_conditions
        self.assertTrue(comparable_conditions("generic", "generic_v2"),
                        "v1 vs v2 differs only in base — that is the experiment")

    def test_the_tuning_comparison_is_comparable(self):
        from data_sheets_schema.api_runner import comparable_conditions
        self.assertTrue(comparable_conditions("generic", "tuned"))

    def test_crossing_both_axes_is_refused(self):
        from data_sheets_schema.api_runner import (
            comparable_conditions, condition_delta, confounded_note)
        self.assertFalse(comparable_conditions("generic_v2", "tuned"))
        self.assertEqual(sorted(condition_delta("generic_v2", "tuned")),
                         ["base", "tuned"])
        self.assertIn("cannot be attributed to either alone",
                      confounded_note("generic_v2", "tuned"))

    def test_a_comparable_pair_has_no_note(self):
        from data_sheets_schema.api_runner import confounded_note
        self.assertIsNone(confounded_note("generic", "tuned"))

    def test_every_condition_declares_both_axes(self):
        from data_sheets_schema.api_runner import (
            CONDITION_AXES, CONDITION_PROMPTS)
        self.assertEqual(set(CONDITION_AXES), set(CONDITION_PROMPTS),
                         "a condition without declared axes cannot be placed")
        for name, axes in CONDITION_AXES.items():
            with self.subTest(condition=name):
                self.assertEqual(set(axes), {"base", "tuned"})


class TestCarveOutEnforcement(unittest.TestCase):
    """The playbook's conditions must hold on every path (#192, #193)."""

    def _corpus(self, td, mode="live", method="claudecode_agent"):
        """A source record with provenance, at an arbitrary root."""
        import yaml
        root = Path(td) / "data" / "d4d_concatenated"
        label = "lab_rep1"
        rec = root / method / label / "P_d4d.yaml"
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_text(yaml.safe_dump({"title": "T"}))
        prov = root / f"{method}_core" / label / "P_provenance.yaml"
        prov.parent.mkdir(parents=True, exist_ok=True)
        body = {"record_mode": mode,
                "inputs": {"bundle_md5": "a",
                           "hash_basis": "verified identical to the bytes consumed"},
                "schema": {"full_md5": "s"}, "model": {"model": "m"},
                "outputs": {"full": {"md5": "x"}}}
        prov.write_text(yaml.safe_dump(body))
        return rec

    def test_a_derived_source_is_refused_by_record_mode_not_by_name(self):
        """A method not named *_merged must still be caught (#192)."""
        from data_sheets_schema.merge import check_sources
        with TemporaryDirectory() as td:
            src = self._corpus(td, mode="derived", method="claudecode_agent_union")
            with self.assertRaises(ValueError) as ctx:
                check_sources({"a": src}, "P")
            self.assertIn("itself a derived record", str(ctx.exception))

    def test_a_live_source_passes(self):
        from data_sheets_schema.merge import check_sources
        with TemporaryDirectory() as td:
            check_sources({"a": self._corpus(td)}, "P")

    def test_union_merge_checks_when_given_paths(self):
        """The condition is about whether the merge is legitimate, so it must
        not depend on the caller having asked for provenance (#193)."""
        from data_sheets_schema.evidence_score import load_record
        from data_sheets_schema.merge import union_merge
        with TemporaryDirectory() as td:
            src = self._corpus(td, mode="derived")
            recs = {"a": load_record(src), "b": load_record(src)}
            with self.assertRaises(ValueError):
                union_merge(recs, project="P", base="a", guarded=True,
                            judge=judge(), source_paths={"a": src, "b": src})

    def test_an_empty_project_is_refused_rather_than_failing_everything(self):
        from data_sheets_schema.merge import check_sources
        with TemporaryDirectory() as td:
            with self.assertRaises(ValueError) as ctx:
                check_sources({"a": self._corpus(td)}, "")
            self.assertIn("needs the project", str(ctx.exception))

    def test_attestation_is_read_where_the_source_lives(self):
        """A source outside the working corpus must not report `none`."""
        from data_sheets_schema.merge import check_sources
        with TemporaryDirectory() as td:
            check_sources({"a": self._corpus(td)}, "P")   # would raise if wrong
