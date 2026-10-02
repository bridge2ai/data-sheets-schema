"""The receipt rows of the cross-arm table (#902, #831).

A count without its denominator compares nothing: receiptable leaves run from
142 to 508 within one arm. These pin the arithmetic behind the pooled section
— in particular that a rate's numerator and denominator come from the same set
of records, which is the mis-measure #831's own body made by dividing by a
list capped at 50 entries.
"""
import importlib.util
import unittest
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "arm_comparison.py"


def _module():
    spec = importlib.util.spec_from_file_location("arm_comparison", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Rate(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_a_zero_numerator_over_a_real_denominator_is_a_rate_not_a_dash(self):
        self.assertEqual(self.m._rate(0, 3400), "0/3400 = 0.0%")

    def test_nothing_measured_and_nothing_to_divide_are_both_a_dash(self):
        for num, den in ((None, 10), (5, 0), (5, None), (None, None)):
            with self.subTest(num=num, den=den):
                self.assertEqual(self.m._rate(num, den), "–")


class Pooled(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def _rec(self, **kw):
        base = dict(receiptable=100, withreceipt=50, neverreceipted=40, addedafter=10,
                    snippets=200, wrongchunk=4, unverified=0, unreviewed=0)
        base.update(kw)
        return base

    def test_a_key_no_record_carries_is_none_and_never_zero(self):
        """The agentic path writes no phase-1 snapshot, so its records carry no
        split. A 0 there would assert that reconciliation added nothing after
        the receipt, which is not what an absent snapshot says."""
        reps = [self._rec(neverreceipted=None, addedafter=None) for _ in range(3)]
        t = self.m.pooled_receipts(reps)
        self.assertIsNone(t["neverreceipted"])
        self.assertIsNone(t["addedafter"])
        self.assertEqual(t["receiptable"], 300)
        self.assertEqual(t["records"], 3)
        self.assertEqual(t["split_records"], 0)

    def test_the_split_is_divided_by_the_records_that_carry_it(self):
        """Not by every checked record: `receiptable` is carried by all of them
        and the split only by those with a snapshot, so pooling the two
        independently would divide a numerator from one set of records by a
        denominator from another."""
        reps = [self._rec(), self._rec(neverreceipted=None, addedafter=None)]
        t = self.m.pooled_receipts(reps)
        self.assertEqual(t["receiptable"], 200)          # both records
        self.assertEqual(t["split_receiptable"], 100)    # only the one with a split
        self.assertEqual(t["neverreceipted"], 40)
        self.assertEqual(t["split_records"], 1)
        self.assertEqual(self.m._rate(t["neverreceipted"], t["split_receiptable"]), "40/100 = 40.0%")
        # the wrong denominator would have halved it
        self.assertEqual(self.m._rate(t["neverreceipted"], t["receiptable"]), "40/200 = 20.0%")

    def test_records_counts_only_the_records_that_were_measured(self):
        reps = [self._rec(), self._rec(receiptable=None)]
        self.assertEqual(self.m.pooled_receipts(reps)["records"], 1)


class Metrics(unittest.TestCase):
    def setUp(self):
        self.m = _module()

    def test_an_unchecked_receipt_measures_nothing(self):
        for block in ({}, {"checked": False}, {"checked": None}):
            with self.subTest(block=block):
                self.assertEqual(set(self.m.receipt_metrics(block).values()), {None})

    def test_without_a_receipt_is_the_difference_not_the_capped_list(self):
        """The stored list is capped at 50 entries with the remainder in a
        counter beside it; #831's body divided by the capped list and reported
        coverage at twice its level."""
        block = {"checked": True, "snippets": {"total": 10},
                 "chunks": {"total": 4, "reviewed": 4},
                 "slots": {"receiptable": 300, "with_receipt": 100,
                           "without_receipt": [f"a[{i}]" for i in range(50)],
                           "without_receipt_truncated": 150}}
        self.assertEqual(self.m.receipt_metrics(block)["noreceipt"], 200)

    def test_a_block_predating_the_counters_falls_back_to_the_list(self):
        block = {"checked": True, "snippets": {"total": 10},
                 "chunks": {"total": 4, "reviewed": 4},
                 "slots": {"without_receipt": ["a", "b"], "without_receipt_truncated": 7}}
        out = self.m.receipt_metrics(block)
        self.assertEqual(out["noreceipt"], 9)
        self.assertIsNone(out["receiptable"])

    def test_the_split_passes_through_as_none_where_the_block_has_none(self):
        block = {"checked": True, "snippets": {"total": 10},
                 "chunks": {"total": 4, "reviewed": 4},
                 "slots": {"receiptable": 10, "with_receipt": 4,
                           "never_receipted": None, "added_after_receipt": None}}
        out = self.m.receipt_metrics(block)
        self.assertIsNone(out["neverreceipted"])
        self.assertIsNone(out["addedafter"])
        self.assertEqual(out["noreceipt"], 6)

    def test_wrongchunk_sums_the_three_attribution_kinds(self):
        block = {"checked": True, "chunks": {"total": 1, "reviewed": 1},
                 "snippets": {"total": 100, "adjacent": 3, "elsewhere": 2, "spans_boundary": 1},
                 "slots": {"receiptable": 10, "with_receipt": 10}}
        out = self.m.receipt_metrics(block)
        self.assertEqual((out["wrongchunk"], out["snippets"]), (6, 100))


class Section(unittest.TestCase):
    """The rendered rows, not only the arithmetic behind them: the denominator
    switch and the "(of N records)" suffix live in `receipt_section`, and a
    row is what a reader acts on (#1198 round 2)."""

    def setUp(self):
        self.m = _module()

    def _rec(self, **kw):
        base = dict(receiptable=100, withreceipt=50, neverreceipted=40, addedafter=10,
                    snippets=200, wrongchunk=4, unverified=0, unreviewed=0)
        base.update(kw)
        return base

    def _row(self, reps):
        data = {k: {p: [] for p in self.m.PROJECTS} for k, *_ in self.m.ARMS}
        first_arm, first_project = self.m.ARMS[0][0], self.m.PROJECTS[0]
        data[first_arm][first_project] = reps
        lines = self.m.receipt_section(data)
        body = [l for l in lines if l.startswith("| ") and not l.startswith("| arm")]
        return body[0] if body else ""

    def test_a_whole_arm_with_the_split_names_no_record_count(self):
        row = self._row([self._rec(), self._rec()])
        self.assertIn("80/200 = 40.0%", row)          # never, over both records
        self.assertNotIn("of 2 records", row)

    def test_an_arm_that_mixes_snapshot_and_no_snapshot_says_how_many_the_split_covers(self):
        row = self._row([self._rec(), self._rec(neverreceipted=None, addedafter=None)])
        self.assertIn("40/100 = 40.0%", row)           # the split's own denominator
        self.assertIn("(of 1 records)", row)
        self.assertIn("100/200 = 50.0%", row)          # coverage still over both

    def test_an_arm_with_no_split_at_all_shows_a_dash_and_no_suffix(self):
        row = self._row([self._rec(neverreceipted=None, addedafter=None) for _ in range(2)])
        self.assertRegex(row, r"\|\s+–\s+\|\s+–\s+\|")
        self.assertNotIn("of 0 records", row)

    def test_an_arm_with_no_measured_record_is_left_out_entirely(self):
        self.assertEqual(self._row([]), "")


def test_report_cells_keep_unmeasured_zeros_out_of_the_mean():
    m = _module()
    reps = [{"report": 0, "claims_checked": 0},
            {"report": 0, "claims_checked": 4},
            {"report": 2, "claims_checked": 0}]
    assert m.cell(reps, "report", "reps") == "1.0 ± 1.4 [0ᵘ,0,2] (n=2)"
    assert m.cell(reps[:1], "report", "reps") == "– [0ᵘ]"
    assert m.cell([{"report": None}], "report", "reps") == "– [–]"


def test_check_detects_report_changes_without_overwriting_any_output(tmp_path, monkeypatch):
    m = _module()
    data = {k: {p: [] for p in m.PROJECTS} for k, *_ in m.ARMS}
    data["v8prod"]["CHORUS"] = [{"report": 0, "claims_checked": 5}]
    m.OUT_MD = tmp_path / "comparison.md"
    original = m.render_markdown(data, {})
    m.OUT_MD.write_text(original)
    monkeypatch.setattr(m, "collect", lambda: data)
    monkeypatch.setattr(m, "EVAL_DIRS", {})
    monkeypatch.setattr(m, "write_figures", lambda *args: pytest.fail("check must not write figures"))
    monkeypatch.setattr(m, "write_markdown", lambda *args: pytest.fail("check must not overwrite Markdown"))
    monkeypatch.setattr("sys.argv", ["arm_comparison.py", "--check"])
    assert m.main() == 0
    data["v8prod"]["CHORUS"][0]["report"] = 2
    assert m.main() == 1
    assert m.OUT_MD.read_text() == original
    m.OUT_MD.unlink()
    assert m.main() == 1
    assert not m.OUT_MD.exists()


@pytest.mark.corpus
def test_committed_comparison_matches_current_records():
    """Catch changed report measurements that leave the published rows stale."""
    m = _module()
    data = m.collect()
    scores = {rubric: {key: {p: m.rubric_scores(prefix, p, rubric) for p in m.PROJECTS}
                      for key, _display, prefix, *_ in m.ARMS} for rubric in m.EVAL_DIRS}
    assert m.OUT_MD.read_text(encoding="utf-8") == m.render_markdown(data, scores), (
        "Run scripts/arm_comparison.py to refresh the committed table and figures")


class RemovalRows(unittest.TestCase):
    """The removal rows (#2923): a record the classifier could not measure —
    no phase-1 snapshot, the agentic path's case — is `–`, never 0 (#899)."""

    def setUp(self):
        self.m = _module()

    def _rows(self, block, report_claims):
        from unittest import mock
        with mock.patch("data_sheets_schema.removals.for_record", return_value=block):
            return self.m.removal_metrics(Path("P_provenance.yaml"), {"report_claims": report_claims})

    def test_a_record_with_no_snapshot_is_unmeasured_on_every_removal_row(self):
        from data_sheets_schema.removals import classify
        rows = self._rows(classify(None, {}), {"snapshot_checked": False, "removals_unrecorded_count": None})
        self.assertEqual(rows, {"unfoundedremovals": None, "unfoundedreconcile": None, "unfoundedrelocated": None,
                                "lowconfidenceflat": None, "receipteddeleted": None, "unfoundedrewrites": None,
                                "unfoundedrewritesnotmodel": None, "unrecordedremovals": None})
        self.assertEqual({self.m.fmt(rows, k) for k in rows}, {"–"})
        self.assertEqual(self.m.cell([rows] * 3, "unfoundedremovals", "reps"), "– [–,–,–]")

    def test_a_measured_record_carries_its_counts_and_a_measured_zero_stays_zero(self):
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "data_governance": {"committee_name": "DAC"}, "license": "CC-BY"}
        receipt = {"chunks": [{"id": "c001", "status": "extracted",
                               "extracted": [{"slot": "data_governance.committee_name", "snippet": "the DAC"}]}]}
        block = classify(before, {"id": "doi:10.1/x", "license": "CC-BY"}, {"findings": []}, receipt=receipt)
        rows = self._rows(block, {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual(rows, {"unfoundedremovals": 1, "unfoundedreconcile": None, "unfoundedrelocated": 0,
                                "lowconfidenceflat": 0, "receipteddeleted": 1, "unfoundedrewrites": 0,
                                "unfoundedrewritesnotmodel": 0, "unrecordedremovals": 0})

    def test_an_unrecorded_count_the_block_did_not_measure_is_not_read(self):
        """`removals_unrecorded_count` is only a measurement where the report
        block read a snapshot."""
        from data_sheets_schema.removals import classify
        rows = self._rows(classify(None, {}), {"snapshot_checked": False, "removals_unrecorded_count": 0})
        self.assertIsNone(rows["unrecordedremovals"])

    def test_the_deletion_rows_say_a_reworded_or_moved_value_counts_as_deleted(self):
        """#3207: the text test is the value's own text surviving, so the
        published definitions must not read as true deletions; and #3229:
        coincidental flattening deflates them, so the definitions must not
        call them upper bounds."""
        for key in ("unfoundedremovals", "receipteddeleted"):
            text = self.m.METRICS[key][3]
            self.assertIn("removals v3", text)
            self.assertIn("reworded", text)
            self.assertNotIn("upper bound", text)        # #3229: the counts err both ways
            self.assertIn("#3207", text)
            self.assertIn("#3229", text)
        definition = self.m.METRICS["unfoundedremovals"][3]
        for phrase in ("a resolver URL and the CURIE it names read as one text, #3129",
                       "a British spelling and its American form, #3038",
                       "a value of numbers only survives only as a scalar equal to it, never quoted in prose, "
                       "and never below five digits, #3243, #3130",
                       "counted on its own row below (#3243)"):
            self.assertIn(phrase, definition)

    def test_the_rewrite_row_counts_unfounded_in_place_rewrites_apart_from_removals(self):
        """#3243: a carried scalar whose path now holds other text is on its
        own row, sorted by the same finding paths, never in the removal rows."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "license": "CC-BY", "description": "old words", "title": "t"}
        after = {"id": "doi:10.1/x", "license": "CC0", "description": "new words entirely", "title": "t"}
        rows = self._rows(classify(before, after, {"findings": [{"slot": "license", "issue": "x"}]}),
                          {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual((rows["unfoundedremovals"], rows["unfoundedrewrites"]), (0, 1))
        keys = list(self.m.METRICS)
        self.assertEqual(keys.index("unfoundedrewrites"), keys.index("receipteddeleted") + 1)
        self.assertIn("#3243", self.m.METRICS["unfoundedrewrites"][3])

    def test_the_relocation_row_counts_unfounded_removals_with_a_candidate_and_moves_nothing(self):
        """#3223: a reported-only row under the removals, counting those
        whose words recur in one final scalar; the removal count beside it
        is what it was without the row."""
        from data_sheets_schema.removals import classify
        note = "The healthsheet answers N/A to the sampling strategy question for this release."
        before = {"id": "doi:10.1/x", "sampling": {"notes": note, "is_sample": True}, "license": "CC-BY"}
        after = {"id": "doi:10.1/x", "sampling": {"is_sample": True, "source_caveats":
                                                   "For this release's sampling strategy question the healthsheet answers N/A."}}
        rows = self._rows(classify(before, after, {"findings": []}),
                          {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual((rows["unfoundedremovals"], rows["unfoundedrelocated"]), (2, 1))
        keys = list(self.m.METRICS)
        self.assertEqual(keys.index("unfoundedrelocated"), keys.index("unfoundedreconcile") + 1)
        definition = self.m.METRICS["unfoundedrelocated"][3]
        for phrase in ("#3223", "Reported only: no count above moves", "removals_relocated_sample_2026-09-29.yaml",
                       "change of standing"):
            self.assertIn(phrase, definition)

    def test_the_low_confidence_row_sizes_the_deflation_and_moves_nothing(self):
        """#3367: flattenings by a one- or two-token needle (or the surplus
        route) that no finding would found, beside the removals; the
        removal count is what it was."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "keywords": ["UF", "voice biomarkers of adults"], "license": "CC-BY"}
        after = {"id": "doi:10.1/x", "keywords": "UF; voice biomarkers of adults"}
        rows = self._rows(classify(before, after, {"findings": []}),
                          {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual((rows["unfoundedremovals"], rows["lowconfidenceflat"]), (1, 1))
        keys = list(self.m.METRICS)
        self.assertEqual(keys.index("lowconfidenceflat"), keys.index("unfoundedrelocated") + 1)
        definition = self.m.METRICS["lowconfidenceflat"][3]
        for phrase in ("#3367", "Reported only: no count moves", "bounds nothing (#3229)"):
            self.assertIn(phrase, definition)

    def test_the_not_the_models_row_counts_normaliser_forms_and_amends_within_the_rewrites(self):
        """#3366: a sub-row of the rewrite row; the rewrite row keeps them."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "issued": "2024-05-01", "description": "old words", "title": "t"}
        after = {"id": "doi:10.1/x", "issued": "2024-05-01T00:00:00Z", "description": "new text", "title": "u"}
        rows = self._rows(classify(before, after, {"findings": []}, amended_paths={"title"}),
                          {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual((rows["unfoundedrewrites"], rows["unfoundedrewritesnotmodel"]), (3, 2))
        keys = list(self.m.METRICS)
        self.assertEqual(keys.index("unfoundedrewritesnotmodel"), keys.index("unfoundedrewrites") + 1)
        definition = self.m.METRICS["unfoundedrewritesnotmodel"][3]
        for phrase in ("#3366", "never subtracted", "curator's recorded amend disposition", "#903"):
            self.assertIn(phrase, definition)

    def test_the_low_confidence_and_not_the_models_rows_read_the_unfounded_subsets(self):
        """#3728: a founded low-confidence flattening, and a founded rewrite
        of the normaliser's form or at an amend, are in the block's totals
        and not in the rows, which are without a finding."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "keywords": ["UF", "voice biomarkers of adults"],
                  "data_governance": {"committee_name": "DAC", "notes": "reviewed yearly by the board"},
                  "issued": "2024-05-01", "title": "t", "description": "old words"}
        after = {"id": "doi:10.1/x", "keywords": "UF; voice biomarkers of adults",
                 "data_governance": "DAC reviewed yearly by the board",
                 "issued": "2024-05-01T00:00:00Z", "title": "u", "description": "new text"}
        block = classify(before, after, {"findings": [{"slot": "data_governance", "record": "full"},
                                                     {"slot": "issued", "record": "full"},
                                                     {"slot": "title", "record": "full"}]},
                         amended_paths={"title"})
        self.assertEqual((block["flattened_low_confidence"], block["rewritten"]), (2, 3))
        rows = self._rows(block, {"snapshot_checked": True, "removals_unrecorded_count": 0})
        self.assertEqual((rows["lowconfidenceflat"], rows["unfoundedrewrites"], rows["unfoundedrewritesnotmodel"]),
                         (1, 1, 0))

    def test_the_rows_are_in_the_table(self):
        for key in ("unfoundedremovals", "unfoundedreconcile", "unfoundedrelocated", "lowconfidenceflat",
                    "receipteddeleted", "unfoundedrewrites", "unfoundedrewritesnotmodel", "unrecordedremovals"):
            self.assertIn(key, self.m.METRICS)
        keys = list(self.m.METRICS)
        self.assertEqual(keys.index("unfoundedreconcile"), keys.index("unfoundedremovals") + 1)

    def test_the_reconcile_row_counts_only_what_reconcile_full_removed(self):
        """#3150: the all-phase row counts a repair round's removals too; the
        row below it counts reconcile_full's alone, a measured 0 where every
        unfounded value went at repair, and – where no phase is attributed."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "a": "1", "b": "2", "c": "3"}
        stages = [("reconcile_full", {"id": "doi:10.1/x", "b": "2", "c": "3"}),
                  ("repair_full_r1", {"id": "doi:10.1/x"})]
        claims = {"snapshot_checked": True, "removals_unrecorded_count": 0}
        rows = self._rows(classify(before, {"id": "doi:10.1/x"}, {"findings": []}, intermediates=stages), claims)
        self.assertEqual((rows["unfoundedremovals"], rows["unfoundedreconcile"]), (3, 1))
        at_repair = [("reconcile_full", before), ("repair_full_r1", {"id": "doi:10.1/x"})]
        rows = self._rows(classify(before, {"id": "doi:10.1/x"}, {"findings": []}, intermediates=at_repair), claims)
        self.assertEqual((rows["unfoundedremovals"], rows["unfoundedreconcile"]), (3, 0))
        gap = [("reconcile_full", None), ("repair_full_r1", {"id": "doi:10.1/x"})]
        rows = self._rows(classify(before, {"id": "doi:10.1/x"}, {"findings": []}, intermediates=gap), claims)
        self.assertEqual((rows["unfoundedremovals"], rows["unfoundedreconcile"]), (3, None))

    def test_the_all_phase_row_says_it_counts_every_phase(self):
        """#3150: the published definition names the repair rounds it
        counts and why they are split out."""
        definition = self.m.METRICS["unfoundedremovals"][3]
        for phrase in ("Every phase after phase 1 is counted", "repair_full_rN",
                       "acts on validation errors, not on the audit", "the row below isolates reconcile_full"):
            self.assertIn(phrase, definition)
        self.assertIn("reconcile_full removed", self.m.METRICS["unfoundedreconcile"][3])

    def test_the_row_definition_states_the_exclusions_the_classifier_applies(self):
        """#3079: a value only a core-only finding's path covers is counted
        in the row, and the published definition says so rather than 'no
        audit finding's path covers'; the past-end reading (#3077) and the
        dropped-entry rule (#3076) are stated with it."""
        from data_sheets_schema.removals import classify
        before = {"id": "doi:10.1/x", "data_governance": {"committee_name": "DAC"}}
        block = classify(before, {"id": "doi:10.1/x"},
                         {"findings": [{"record": "core", "slot": "data_governance", "issue": "x"}]})
        rows = self._rows(block, {"snapshot_checked": True, "removals_unrecorded_count": 1})
        self.assertEqual((rows["unfoundedremovals"], block["unfounded_named_by_core_finding"]), (1, 1))
        definition = self.m.METRICS["unfoundedremovals"][3]
        for phrase in ("not scoped to the core record alone", "a value only a core-only finding's path covers "
                       "is counted here", "one past the end of its list read as the last entry",
                       "for an entry dropped from a list"):
            self.assertIn(phrase, definition)
        self.assertNotIn("no finding named the value", definition)


class ReleaseInventory(unittest.TestCase):
    """The release-level corpus inventory (#2914, #3282): a cross-project
    difference on doi, license, version or issued is labelled corpus-driven
    where the corpus holds no release evidence, and each arm's pinned
    manifest is inventoried rather than assumed to be today's."""

    def setUp(self):
        self.m = _module()
        self.empty = {k: {p: [] for p in self.m.PROJECTS} for k, *_ in self.m.ARMS}

    def _doc(self, e11, e102=None):
        sub = lambda name, score: ({"name": name, "score": score} if score is not None
                                   else {"name": name, "score": None, "applicable": False})
        return {"elements": [
            {"id": 1, "sub_elements": [sub("Persistent Identifier (DOI, RRID, or URI)", e11)]},
            {"id": 3, "sub_elements": [sub("License Terms Allow Reuse", 0)]},
            {"id": 6, "sub_elements": [sub("Renamed element", 1)]},
            {"id": 10, "sub_elements": [sub("Dataset Published on a Recognized Platform", 1),
                                        sub("Citation and DOI for Cross-referencing", e102)]}]}

    def test_the_corpus_limited_project_is_named_with_its_inventory(self):
        text = "\n".join(self.m.release_inventory_section(self.empty, {}))
        self.assertIn("| CHORUS | 0 (0 current) | none | none | none | none | no | `exclude` |", text)
        self.assertIn("AI_READI's document corpus carries its RO-Crate and its licence "
                      "(`ro_crate_metadata`; `dataset_license`)", text)
        self.assertIn("CHORUS's corpus has 0 tier-1 sources, no release record, no license/DUA/IRB "
                      "source, and the crate manifest declares its crate `document_corpus: exclude`", text)
        self.assertIn("`doi`, `license`, `version` and `issued` are **corpus-driven** for CHORUS, "
                      "not a measure of generation quality", text)

    def test_release_subelements_are_counted_per_project_and_evaluator_with_na_apart(self):
        scores = {"rubric10": {"v7prod": {"CHORUS": [
            {"file": "a.json", "evaluator": "ev", "doc": self._doc(0)},
            {"file": "b.json", "evaluator": "ev", "doc": self._doc(1, 0)},
            {"file": "b.json", "evaluator": "ev", "doc": self._doc(1, 0)},     # the same file once
            {"file": "c.json", "evaluator": "other", "doc": self._doc(1, 1)}]}}}
        rows = self.m._release_subelement_rows(scores)
        # E6.1 is renamed in these docs, so it is read as absent, never as a score.
        self.assertEqual(rows, ["| CHORUS | `ev` | 1/2 | 0/2 | – | 0/1, 1 N/A |",
                                "| CHORUS | `other` | 1/1 | 0/1 | – | 1/1 |"])

    def test_a_pinned_manifest_whose_corpus_differs_from_todays_is_named(self):
        import tempfile
        from unittest import mock
        today = (self.m.ROOT / self.m.SOURCE_MANIFEST).read_bytes()
        crate = (self.m.ROOT / self.m.CRATE_MANIFEST).read_bytes()
        then = today.replace(b"source_type: license", b"source_type: documentation", 1)   # AI_READI's
        with tempfile.TemporaryDirectory() as tmp:
            concat = Path(tmp)
            data = {k: {p: [] for p in self.m.PROJECTS} for k, *_ in self.m.ARMS}
            for p, md5 in (("AI_READI", "a" * 32), ("CHORUS", "a" * 32), ("VOICE", "b" * 32)):
                d = concat / "claudecode_api_core" / "L_rep1"
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{p}_provenance.yaml").write_text(
                    f"inputs:\n  source_manifest:\n    path: {self.m.SOURCE_MANIFEST}\n    md5: {md5}\n")
                data["v8prod"][p] = [{"label": "L_rep1"}]
            versions = {"a" * 32: (then, {"commit": "c" * 40, "date": "2026-09-01"})}
            with mock.patch.object(self.m, "CONCAT", concat), \
                    mock.patch.object(self.m, "_method_for", lambda label, project: "claudecode_api"), \
                    mock.patch("data_sheets_schema.provenance.committed_bytes_for",
                               lambda path, md5=None, sha256=None: versions.get(md5)):
                rows = self.m._pinned_manifest_rows(data, today, crate)
        self.assertEqual(rows, [
            "| v8 API production (2026-09-04f/g) | `aaaaaaaaaaaa` (2 records), committed 2026-09-01 "
            "(`cccccccccc`) | differs: AI_READI | as today | |",
            "| v8 API production (2026-09-04f/g) | `bbbbbbbbbbbb` (1 records) | – | – | "
            "no committed version of `data/preprocessed/source_manifest.yaml` hashes to it |"])

    def test_a_record_pinning_no_manifest_or_no_hash_says_so_and_git_is_not_asked(self):
        """#3903: `path: null` (a run that selected no manifest, #621) and a
        path with no hash are named as such, never as a git miss on `None`."""
        import tempfile
        from unittest import mock
        today = (self.m.ROOT / self.m.SOURCE_MANIFEST).read_bytes()
        crate = (self.m.ROOT / self.m.CRATE_MANIFEST).read_bytes()
        blocks = {"AI_READI": "path: null\n",
                  "CHORUS": f"path: {self.m.SOURCE_MANIFEST}\n",
                  "VOICE": "path: null\n    md5: " + "d" * 32 + "\n"}
        asked = []
        with tempfile.TemporaryDirectory() as tmp:
            concat = Path(tmp)
            data = {k: {p: [] for p in self.m.PROJECTS} for k, *_ in self.m.ARMS}
            d = concat / "claudecode_api_core" / "L_rep1"
            d.mkdir(parents=True)
            for p, block in blocks.items():
                (d / f"{p}_provenance.yaml").write_text("inputs:\n  source_manifest:\n    " + block)
                data["v8prod"][p] = [{"label": "L_rep1"}]
            with mock.patch.object(self.m, "CONCAT", concat), \
                    mock.patch.object(self.m, "_method_for", lambda label, project: "claudecode_api"), \
                    mock.patch("data_sheets_schema.provenance.committed_bytes_for",
                               lambda *a, **k: asked.append(a) or None):
                rows = self.m._pinned_manifest_rows(data, today, crate)
        self.assertEqual(asked, [])
        arm = "| v8 API production (2026-09-04f/g) |"
        self.assertEqual(sorted(rows), sorted([
            f"{arm} no hash recorded (1 records) | – | – | the records pinned no source manifest |",
            f"{arm} no hash recorded (1 records) | – | – | the records name "
            "`data/preprocessed/source_manifest.yaml` but pinned no hash of it, "
            "so no version can be recovered |",
            f"{arm} `dddddddddddd` (1 records) | – | – | "
            "the records pinned a hash but no source-manifest path |"]))
        self.assertFalse(any("`None`" in r for r in rows))


# Live form metrics carry the run's schema and disclose fallbacks (#4216).
@pytest.fixture
def form_run(tmp_path, monkeypatch):
    import hashlib
    import yaml

    m = _module()
    m.CONCAT = tmp_path / "concatenated"
    label, project = "test_run_rep1", "P"
    monkeypatch.setattr(m, "_method_for", lambda *_args: "claudecode_agent")
    monkeypatch.setattr(m, "removal_metrics", lambda *_args: {})
    full = m.CONCAT / "claudecode_agent" / label / f"{project}_d4d.yaml"
    core = m.CONCAT / "claudecode_agent_core" / label / f"{project}_d4d_core.yaml"
    prov = core.parent / f"{project}_provenance.yaml"
    full.parent.mkdir(parents=True)
    core.parent.mkdir(parents=True)
    full.write_text(yaml.safe_dump({"id": "foo:1", "publisher": "doi:10.1/a",
                                   "description": "research centre",
                                   "variables": [{"unit": "ROR:032db5x82#bench"}]}))
    core.write_text(yaml.safe_dump({"id": "doi:10.1/core"}))
    schema = {"id": "https://example.org/run", "name": "run", "default_range": "string",
              "prefixes": {"foo": "https://foo.example.org/", "linkml": "https://w3id.org/linkml/"},
              "types": {"string": {"uri": "xsd:string", "base": "str"},
                        "uriorcurie": {"uri": "xsd:anyURI", "base": "URIorCURIE"}},
              "classes": {"Dataset": {"attributes": {
                  "id": {"range": "uriorcurie", "identifier": True},
                  "publisher": {"range": "uriorcurie"},
                  "variables": {"range": "VariableMetadata", "multivalued": True}}},
                  "VariableMetadata": {"attributes": {"unit": {"range": "uriorcurie"}}}}}
    schema_path = tmp_path / "run_all.yaml"
    schema_path.write_text(yaml.safe_dump(schema))
    record = {"schema": {"full_path": str(schema_path),
                         "full_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest()},
              "validation": {"passed": True}, "grounding": {"distinct": {"absent": 7}},
              "pair_consistency": {"errors": 3}, "report_claims": {"findings": [{}]},
              "form": {"undeclared_prefix_occurrences": 999}}
    prov.write_text(yaml.safe_dump(record))
    return m, label, project, full, core, prov, record


def test_live_form_uses_run_schema_for_prefixes_and_identifier_walk(form_run):
    m, label, project, full, core, prov, record = form_run
    before = {path: path.read_bytes() for path in (full, core, prov)}
    today = m.form_facts(full, core)
    row = m.run_metrics(label, project)
    assert today["undeclared_prefix_occurrences"] == 1
    assert today["organisational_fragments"] == 0
    assert row["undeclared"] == 3 and row["orgfrag"] == 1
    assert row["british"] == today["british_spellings"]
    assert row["gc"] == today["gc_label_variant_occurrences"]
    assert (row["ungrounded"], row["pair"], row["report"]) == (7, 3, 1)
    assert row["form_schema_basis"] == {"source": "the run's schema, on disk",
                                         "path": record["schema"]["full_path"],
                                         "sha256": record["schema"]["full_sha256"]}
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("unavailable", [False, True])
def test_schema_fallback_uses_todays_values_and_exposes_why(form_run, monkeypatch, unavailable):
    import yaml
    m, label, project, full, core, prov, record = form_run
    if unavailable:
        record["schema"]["full_sha256"] = "a" * 64
        monkeypatch.setattr("data_sheets_schema.reconstructed_bytes.reconstructed_bytes_for",
                            lambda *_args, **_kwargs: None)
        def no_git(*_args, **_kwargs):
            raise FileNotFoundError("git unavailable")
        monkeypatch.setattr("data_sheets_schema.provenance.committed_bytes_for", no_git)
    else:
        record.pop("schema")
    prov.write_text(yaml.safe_dump(record))
    row = m.run_metrics(label, project)
    assert row["undeclared"] == 1 and row["orgfrag"] == 0
    assert row["form_schema_basis"]["source"] == "today's schema"
    expected = "git could not be run" if unavailable else "the record names no merged schema"
    assert expected in row["form_schema_basis"]["reason"]
    data = {arm: {p: [] for p in m.PROJECTS} for arm, *_ in m.ARMS}
    data[m.ARMS[0][0]][m.PROJECTS[0]] = [row]
    rendered = "\n".join(m.form_schema_section(data))
    assert "today's schema" in rendered and expected in rendered
    assert label in rendered
    assert "do not attest that the requested historical bytes were used" in rendered
    assert "naming declaration, not the run's schema" in rendered
    assert "Current prefix instrument:" in rendered and "Current British-spelling instrument:" in rendered


def test_missing_or_invalid_runs_do_not_acquire_live_form_measurements(form_run, monkeypatch):
    import yaml
    m, label, project, _full, core, prov, record = form_run
    def unexpected(*_args, **_kwargs):
        pytest.fail("excluded records must not be measured")
    monkeypatch.setattr(m, "form_facts", unexpected)
    record["validation"]["passed"] = False
    prov.write_text(yaml.safe_dump(record))
    assert m.run_metrics(label, project) is None
    assert (label, project) in m.EXCLUDED_INVALID
    core.unlink()
    assert m.run_metrics(label, project) is None


def test_form_schema_section_escapes_recorded_basis_and_distinguishes_absence():
    m = _module()
    data = {arm: {p: [] for p in m.PROJECTS} for arm, *_ in m.ARMS}
    data[m.ARMS[0][0]][m.PROJECTS[0]] = [
        {"label": "run|extra\nrow", "form_schema_basis": {"source": "today's schema",
         "reason": "bad | pin <schema> `name`"}}, {"label": "legacy"}]
    rendered = "\n".join(m.form_schema_section(data))
    assert "run&#124;extra<br>row" in rendered
    assert "bad &#124; pin &lt;schema&gt; &#96;name&#96;" in rendered
    assert "legacy | unrecorded — no schema basis supplied" in rendered


def test_live_reference_worst_is_distinguished_from_stored_canary_thresholds(tmp_path):
    m = _module()
    data = {arm: {p: [] for p in m.PROJECTS} for arm, *_ in m.ARMS}
    # The historical v4 live recompute moves 0/6/0 to 116/56/51 (#4216).
    m.CONCAT = tmp_path
    data["v4"]["AI_READI"] = [{"undeclared": n, "label": f"fixture_rep{i}"}
                               for i, n in enumerate((116, 56, 51), 1)]
    for row in data["v4"]["AI_READI"]:
        full = tmp_path / "claudecode_agent" / row["label"] / "AI_READI_d4d.yaml"
        core = tmp_path / "claudecode_agent_core" / row["label"] / "AI_READI_d4d_core.yaml"
        full.parent.mkdir(parents=True)
        core.parent.mkdir(parents=True)
        full.write_text("id: ex:fixture\n")
        core.write_text("id: ex:fixture\n")
        (core.parent / "AI_READI_provenance.yaml").write_text("{}\n")
    text = m.render_markdown(data, {})
    assert "74.3 ± 36.2 [116,56,51] worst 116" in text
    assert "worst on this report's measurement basis" in text
    assert "Canary gates read stored form blocks" in text
    assert "this live recompute does not change their thresholds" in text
    assert "the value the canary gate holds runs against" not in text
    assert "the canary-gate baseline)" not in text
