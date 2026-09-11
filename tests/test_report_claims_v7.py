"""Adversarial cases from #1089, #1194 and #1196."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_sheets_schema import report_claims as rc
from tests.test_report_claims import DECLARED


class ReportClaimsV7(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def check(self, text, full=None, core=None, snapshot=None):
        path = self.root / "report.md"
        path.write_text(text)
        return rc.check_report(path, full or {}, core or {}, DECLARED,
                               snapshot=snapshot, dispositions_expected=True)

    def test_a_record_side_schema_assertion_is_not_the_reports_claim(self):
        text = ("The audit found the core record had dropped `splits` and relocated its "
                "content to trailing `notes` prose, and that the core record's "
                "`source_caveats` asserted the core schema has no such slot — "
                "an assertion the digest does not support.")
        self.assertEqual(self.check(text)["findings"], [])
        # A directly named subject before the phrase is still a false claim.
        direct = "The `notes` slot is not declared in the core schema."
        self.assertEqual(self.check(text + "\n" + direct)["findings"][0]["slot"], "notes")
        for subject in ("the report states", "the audit says"):
            direct = ("The core record says it is schema compliant, and " + subject
                      + " that `notes` is not declared in the core schema.")
            self.assertEqual([f["slot"] for f in self.check(direct)["findings"]], ["notes"])

    def test_a_nested_path_keeps_every_segment(self):
        text = "The information remains in `data_governance.stewards.name`."
        wrong = {"data_governance": {"other": {"name": "Wrong entity"}}}
        right = {"data_governance": {"stewards": [{"name": "The steward"}]}}
        self.assertEqual(len(self.check(text, full=wrong)["findings"]), 1)
        self.assertEqual(self.check(text, full=right)["findings"], [])

    def test_a_declared_root_slot_is_not_satisfied_by_a_nested_namesake(self):
        text = "The correction remains in `errata`."
        nested = {"resources": [{"errata": ["another dataset's correction"]}]}
        self.assertEqual(len(self.check(text, full=nested)["findings"]), 1)
        shorthand = "The reviewers remain in `review_details`."
        self.assertEqual(self.check(shorthand, full={"ethical_reviews": [
            {"review_details": "Two reviewers"} ]})["findings"], [])

    def test_prose_record_scope_is_enforced_and_reported(self):
        for text in ("The value remains in `core.errata`.",
                     "In the core record the value remains in `errata`.",
                     "The value remains in `errata` in the core record."):
            with self.subTest(text=text):
                findings = self.check(text, full={"errata": ["full only"]})["findings"]
                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0]["record"], "core")
                self.assertNotIn("neither", findings[0]["detail"])
        text = "The value remains in `errata` in both records."
        self.assertEqual(self.check(text, full={"errata": ["full only"]})["findings"][0]["record"], "both")
        self.assertEqual(self.check(text, full={"errata": [1]}, core={"errata": [1]})["findings"], [])

    def test_mixed_parent_values_count_entries_not_parent_matches(self):
        text = "| full | `resources.tags` | removed |"
        full = {"resources": [{"tags": [1, 2, 3]}, {"tags": [4, 5]}, {"tags": 6}]}
        findings = self.check(text, full=full)["findings"]
        self.assertEqual(findings[0]["kind"], "removal_not_performed")
        self.assertIn("6 entries", findings[0]["detail"])

    def test_an_identical_row_in_another_table_is_not_excluded_by_text(self):
        row = "| `errata` | Reviewed | Removed |"
        text = ("| Slot | Disposition | Reason |\n|---|---|---|\n" + row
                + "\n\n| Slot | Assessment | Change |\n|---|---|---|\n" + row)
        findings = self.check(text, core={"errata": ["still present"]})["findings"]
        self.assertEqual([(f["kind"], f["slot"]) for f in findings],
                         [("removal_not_performed", "errata")])

    def test_unbordered_dispositions_and_embedded_record_qualifiers(self):
        text = "Slot | Disposition | Reason\n--- | --- | ---\ncore `errata` | Retained | Kept\n"
        block = self.check(text, full={"errata": ["full only"]})
        self.assertEqual(block["disposition_rows"], 1)
        self.assertEqual(block["findings"][0]["record"], "core")

    def test_not_only_is_affirmative_and_a_long_negation_still_negates(self):
        self.assertEqual(self.check("It not only remains in `errata`.")["prose_retention_claims"], 1)
        text = "No " + "documented " * 20 + "value remains in `errata`."
        self.assertEqual(self.check(text)["prose_retention_claims"], 0)

    def test_parenthetical_negation_does_not_change_the_surrounding_claim(self):
        text = ("The identifier is used — no registered CURIE prefix is supplied — "
                "and the award details remain in `notes`.")
        self.assertEqual(self.check(text, full={"notes": "award details"})["prose_retention_claims"], 1)
        text = "No value — even an older correction — remains in `errata`."
        self.assertEqual(self.check(text)["prose_retention_claims"], 0)

    def test_implicit_and_explicit_core_removal_are_one_finding(self):
        text = ("**Action:** the `errata` block was removed.\n\n"
                "| Slot | Disposition |\n|---|---|\n| core `errata` | Removed |")
        findings = self.check(text, core={"errata": ["still there"]})["findings"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["kind"], "removal_not_performed")

    def test_weak_removal_does_not_suppress_a_different_or_denied_change(self):
        cases = [
            ("Every projected entry keeps its `id`, and the two slots the projection drops are described below.", "id"),
            ("The core record omits the full record's `errata`.", "errata"),
            ("The core record remains a projection: it carries no fact the full record does not, and omits `errata`.", "errata"),
            ("The core record remains a projection: it carries no fact the full record does\nnot, and omits `errata`.", "errata"),
            ("`errata` was retained in the full record and is absent from the reconciled core record.", "errata"),
            ("`extension_mechanism` was retained in the full record and is **absent** from the reconciled core record.", "extension_mechanism"),
            ("The `creators` list includes Marquez C and omits Park S and Zhao X.", "creators"),
            ("`withdrawal_mechanism` now contains only withdrawal facts (withdraw at any time).", "withdrawal_mechanism"),
            ("The entry drops `archival` and instead carries `future_guarantees`.", "future_guarantees"),
            ("It is not the case that `errata` was removed.", "errata"),
        ]
        for text, slot in cases:
            with self.subTest(text=text):
                self.assertIn(slot, self.check(text, snapshot={slot: ["before"]})["removals_unrecorded"])
        for text in ("`errata`, and `funders` were removed.",
                     "The full and core record omit `errata` and `funders`.",
                     "`errata` and `funders` are absent from the core record and the full record.",
                     "The core record is unchanged, and the full record omits `errata` and `funders`."):
            with self.subTest(text=text):
                self.assertEqual(self.check(text, snapshot={"errata": [1], "funders": [1]})["removals_unrecorded"], [])

    def test_independent_removal_predicates_keep_their_own_record_scopes(self):
        for text in (
            "The full record omits `errata` and the core record omits `funders`.",
            "The core record omits `funders` and the full record omits `errata`.",
            "`errata` was removed from the full record and `funders` was removed from the core record.",
            "`funders` was removed from the core record and `errata` was removed from the full record.",
        ):
            with self.subTest(text=text):
                result = self.check(text, snapshot={"errata": [1], "funders": [1]})
                self.assertEqual(result["removals_unrecorded"], ["funders"])

    def test_snapshot_hash_identifies_the_bytes_that_were_parsed(self):
        core = self.root / "X_d4d_core.yaml"
        directory = self.root / "intermediate"
        directory.mkdir()
        snapshot = directory / "X_full.yaml"
        before = b"id: before\nerrata: [old]\n"
        snapshot.write_bytes(before)
        original = Path.read_bytes

        def replaced_after_read(path):
            data = original(path)
            if path == snapshot:
                path.write_text("id: after\n")
            return data

        with patch.object(Path, "read_bytes", replaced_after_read):
            doc, pin = rc.phase1_snapshot_with_pin_for(core)
        self.assertEqual(doc["id"], "before")
        self.assertEqual(pin["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(pin["path"], str(snapshot))

    def test_schema_attribution_stops_at_each_sentence_in_a_reason_cell(self):
        for attributed in ("The core record says the slot was reviewed.",
                           "The core record says the slot is not declared in the core schema."):
            text = ("| Slot | Disposition | Reason |\n|---|---|---|\n"
                    "| `errata` | Reviewed | " + attributed
                    + " This slot is not declared in the core schema. |")
            findings = self.check(text)["findings"]
            self.assertEqual([(f["kind"], f["slot"]) for f in findings], [("false_schema_claim", "errata")])

    def test_an_unsupported_disposition_does_not_hide_later_rows(self):
        text = ("Slot | Disposition | Reason\n---|---|---\n"
                "keywords | Retained | Kept\nerrata | Reviewed | No change needed\n"
                "distributions | Retained | Kept\n")
        block = self.check(text, full={"keywords": ["a"]})
        self.assertEqual(block["disposition_rows"], 2)
        self.assertEqual([(f["kind"], f["slot"]) for f in block["findings"]],
                         [("retention_not_shown", "distributions")])
        # Data can contain words that also appear as column labels.
        text = text.replace("errata | Reviewed | No change needed", "notes | Reviewed | Reason")
        block = self.check(text, full={"keywords": ["a"]})
        self.assertEqual(block["disposition_rows"], 2)
        self.assertEqual([f["slot"] for f in block["findings"]], ["distributions"])

    def test_core_absence_does_not_cancel_a_full_removal(self):
        for text in ("`anomalies` removed from full, was already absent from core.",
                     "`anomalies` was removed from the full record, already absent from the core record."):
            with self.subTest(text=text):
                self.assertEqual(self.check(text, snapshot={"anomalies": [1]})["removals_unrecorded"], [])

    def test_independent_retentions_keep_their_own_record_scope(self):
        text = ("The citation remains in `citation` in the full record, and the keywords "
                "remain in `keywords` in the core record.")
        full = {"citation": "Paper", "keywords": ["a"]}
        self.assertEqual(self.check(text, full=full, core={"keywords": ["a"]})["findings"], [])
        findings = self.check(text, full=full)["findings"]
        self.assertEqual([(f["slot"], f["record"]) for f in findings], [("keywords", "core")])
        text = "In the core record, a value remains in `errata` and another remains in `keywords`."
        findings = self.check(text, full={"errata": [1], "keywords": [1]}, core={"errata": [1]})["findings"]
        self.assertEqual([(f["slot"], f["record"]) for f in findings], [("keywords", "core")])
        text = "Nothing remains in `errata` and the value remains in `keywords` in the full record."
        self.assertEqual(self.check(text, full={"keywords": [1]})["prose_retention_claims"], 1)

    def test_schema_attribution_ends_at_independent_while_and_yet_clauses(self):
        for join in (", while", ", yet"):
            text = ("| Slot | Disposition | Reason |\n|---|---|---|\n"
                    "| `errata` | Reviewed | The core record says the slot was reviewed"
                    + join + " this slot is not declared in the core schema. |")
            self.assertEqual([f["kind"] for f in self.check(text)["findings"]], ["false_schema_claim"])

    def test_a_following_separator_identifies_an_unfamiliar_table_header(self):
        text = ("| Slot | Disposition | Reason |\n|---|---|---|\n"
                "| `keywords` | Retained | Kept |\n"
                "| Item | Assessment | Action |\n|---|---|---|\n"
                "| `errata` | Reviewed | Removed |")
        findings = self.check(text, full={"keywords": [1]}, core={"errata": [1]})["findings"]
        self.assertEqual([(f["kind"], f["slot"]) for f in findings], [("removal_not_performed", "errata")])

    def test_retention_and_absence_predicates_have_separate_scopes(self):
        for suffix in ("and is absent from the core record.", ", already absent from the core record."):
            text = "The citation remains in `citation` in the full record " + suffix
            self.assertEqual(self.check(text, full={"citation": "paper"})["findings"], [])

    def test_coordinated_retention_verbs_inherit_their_negative_subject(self):
        for verb in ("stays", "also stays", "is retained"):
            text = "No value remains in `errata` and " + verb + " in `keywords`."
            self.assertEqual(self.check(text)["prose_retention_claims"], 0)
        text = "The value remains in `notes`, no value remains in `errata` and stays in `keywords`."
        self.assertEqual(self.check(text, full={"notes": "text"})["prose_retention_claims"], 1)

    def test_active_full_removals_survive_core_absence_context(self):
        for verb in ("drops", "omits", "removes", "deletes", "strips", "withdraws"):
            text = "The full record " + verb + " `anomalies`, already absent from the core record."
            self.assertEqual(self.check(text, snapshot={"anomalies": [1]})["removals_unrecorded"], [])

    def test_absent_and_unusable_snapshots_are_not_measured_as_empty(self):
        core = self.root / "X_d4d_core.yaml"
        self.assertEqual(rc.phase1_snapshot_with_pin_for(core), (None, None))
        directory = self.root / "intermediate"
        directory.mkdir()
        snapshot = directory / "X_full.yaml"
        for raw in (b"[]\n", b"{}\n", b"id: [unterminated", b"\xff"):
            with self.subTest(raw=raw):
                snapshot.write_bytes(raw)
                doc, pin = rc.phase1_snapshot_with_pin_for(core)
                self.assertIsNone(doc)
                self.assertEqual(pin["state"], "unusable")
                self.assertEqual(pin["sha256"], hashlib.sha256(raw).hexdigest())
                self.assertTrue(pin["reason"])
