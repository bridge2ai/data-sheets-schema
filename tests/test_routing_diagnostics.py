"""Slot-meaning diagnostic: release-timing text under confidential or
sensitive elements (#2931).

The synthetic records carry no project prose. The corpus replay names its
record set: the nine CM4AI full records the issue parsed (v6 agentic
2026-08-28 rep1-3, v7 API 2026-09-01 rep1-3, v8 API 2026-09-04g rep1-3) and
their nine core twins, each by path.
"""

import json
import sys
import unittest
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import routing_diagnostics as rd
from data_sheets_schema.routing_diagnostics import (
    AVAILABILITY_TIMING, EMBARGO, RELEASE_TIMING, slot_meaning_mismatch,
)

ROOT = Path(__file__).resolve().parents[1]

#: Written for these tests, not taken from any record or bundle.
EMBARGO_TEXT = "Two assay deposits are held under a pre-publication embargo; their download links read Embargoed."


def _paths(record):
    return [m.path for m in slot_meaning_mismatch(record)]


class TestTheSlotDecidesNotTheText(unittest.TestCase):
    """The same sentence is a finding in one slot and correct routing in another."""

    def test_embargo_text_under_confidential_elements_is_flagged(self):
        record = {"id": "example:ds", "confidential_elements": [{
            "name": "Deposits under embargo", "confidential_elements_present": True,
            "confidentiality_details": EMBARGO_TEXT}]}
        found = slot_meaning_mismatch(record)
        self.assertEqual([(m.slot, m.path, m.kinds, m.present) for m in found], [
            ("confidential_elements", "confidential_elements[0].name", (EMBARGO,), True),
            ("confidential_elements", "confidential_elements[0].confidentiality_details",
             (EMBARGO, RELEASE_TIMING), True)])
        self.assertEqual(found[1].terms, ("embargo", "Embargoed", "pre-publication"))

    def test_embargo_text_under_sensitive_elements_is_flagged(self):
        record = {"sensitive_elements": [{"sensitive_elements_present": False,
                                          "sensitivity_details": EMBARGO_TEXT}]}
        found = slot_meaning_mismatch(record)
        self.assertEqual([(m.slot, m.path, m.present) for m in found],
                         [("sensitive_elements", "sensitive_elements[0].sensitivity_details", False)])

    def test_the_same_text_under_known_limitations_is_not_flagged(self):
        self.assertEqual(_paths({"known_limitations": [{"description": EMBARGO_TEXT}]}), [])

    def test_the_same_text_under_distribution_slots_is_not_flagged(self):
        record = {"distribution_dates": [{"description": EMBARGO_TEXT, "release_dates": ["Q3 2026"]}],
                  "distribution_formats": [{"description": EMBARGO_TEXT}],
                  "external_resources": [{"external_resources": [EMBARGO_TEXT]}],
                  "third_party_sharing": [{"is_shared": True, "description": EMBARGO_TEXT}]}
        self.assertEqual(_paths(record), [])

    def test_one_record_carrying_the_text_everywhere_is_flagged_only_where_the_slot_is_wrong(self):
        record = {"known_limitations": [{"description": EMBARGO_TEXT}],
                  "distribution_dates": [{"description": EMBARGO_TEXT}],
                  "confidential_elements": [{"confidentiality_details": EMBARGO_TEXT}],
                  "missing_data_documentation": [{"description": EMBARGO_TEXT}]}
        self.assertEqual(_paths(record), ["confidential_elements[0].confidentiality_details"])

    def test_a_nested_dataset_answers_the_same_question(self):
        record = {"resources": [{"id": "example:part", "known_limitations": [{"description": EMBARGO_TEXT}],
                                 "confidential_elements": [{"description": EMBARGO_TEXT}]}]}
        self.assertEqual(_paths(record), ["resources[0].confidential_elements[0].description"])


class TestTheLexicon(unittest.TestCase):
    def _kinds(self, text, slot="confidential_elements"):
        return [m.kinds for m in slot_meaning_mismatch({slot: [{"description": text}]})]

    def test_each_kind_is_reachable_without_the_word_embargo(self):
        self.assertEqual(self._kinds("Deposits will be released upon publication of the companion paper."),
                         [(RELEASE_TIMING,)])
        self.assertEqual(self._kinds("The imaging tier is not yet publicly available."),
                         [(AVAILABILITY_TIMING,)])
        self.assertEqual(self._kinds("Assay files will be made publicly available in a later deposit."),
                         [(AVAILABILITY_TIMING,)])
        self.assertEqual(self._kinds("Assay files will be made available after publication."),
                         [(RELEASE_TIMING, AVAILABILITY_TIMING)])

    def test_access_control_language_is_what_these_slots_describe_and_is_not_matched(self):
        """Withholding a sensitive variable is correct routing; the full schema
        describes confidential elements as 'why it cannot be released'."""
        for text in ("Raw recordings are withheld from the public release and available only under controlled access.",
                     "Full postal codes cannot be released and are held under a data use agreement.",
                     "The release states that no human subjects were enrolled.",
                     "Variables treated as sensitive are withheld from this public release.",
                     "Biospecimens are banked for future studies under restricted access."):
            with self.subTest(text=text[:40]):
                self.assertEqual(self._kinds(text), [])
                self.assertEqual(self._kinds(text, "sensitive_elements"), [])

    def test_identifiers_and_source_caveats_are_not_read_but_notes_are(self):
        record = {"confidential_elements": [{
            "id": "example:ds#confidential-embargoed-deposits",
            "source_caveats": ["The source mentions an embargo only in a table footnote."],
            "notes": "Two deposits remain under embargo."}]}
        self.assertEqual(_paths(record), ["confidential_elements[0].notes"])

    def test_a_record_that_breaks_the_list_shape_still_says_what_it_says(self):
        self.assertEqual([(m.path, m.present) for m in slot_meaning_mismatch(
            {"confidential_elements": "Under embargo until 2027."})],
            [("confidential_elements", None)])
        self.assertEqual(_paths({"confidential_elements": {"confidentiality_details": EMBARGO_TEXT}}),
                         ["confidential_elements.confidentiality_details"])
        self.assertEqual(_paths({"confidential_elements": ["Under embargo until 2027.", "ZIP codes"]}),
                         ["confidential_elements[0]"])

    def test_a_record_that_is_not_a_mapping_is_not_a_clean_one(self):
        for record in (None, [], "text"):
            with self.subTest(record=record), self.assertRaises(TypeError):
                slot_meaning_mismatch(record)


#: `safe_load` keeps the second `confidential_elements`, so the parsed record
#: is clean while the text says the embargo is confidential (#1029).
DUPLICATED_SLOT = (
    "confidential_elements:\n"
    "- confidential_elements_present: true\n"
    "  confidentiality_details: Two assay deposits are held under embargo.\n"
    "known_limitations:\n"
    "- description: Two assay deposits are held under embargo.\n"
    "confidential_elements:\n"
    "- confidential_elements_present: false\n"
)


class TestADuplicatedKeyHidesWhatItReplaced(unittest.TestCase):
    def test_a_scoped_slot_written_twice_is_named(self):
        self.assertEqual(_paths(yaml.safe_load(DUPLICATED_SLOT)), [])     # what the parse shows
        self.assertEqual([(d["path"], d["key"], d["lines"]) for d in rd.unread_duplicate_keys(DUPLICATED_SLOT)],
                         [("$", "confidential_elements", [1, 6])])

    def test_a_key_repeated_inside_a_scoped_entry_is_named(self):
        for text in ("confidential_elements:\n- name: a\n  name: b\n",
                     "resources:\n- sensitive_elements:\n  - sensitivity_details: a\n    sensitivity_details: b\n",
                     "resources:\n- confidential_elements: []\n  confidential_elements: []\n"):
            with self.subTest(text=text):
                self.assertEqual(len(rd.unread_duplicate_keys(text)), 1)

    def test_a_duplicate_the_scan_would_not_read_anyway_is_not_named(self):
        for text in ("source_caveats: a\nsource_caveats: b\n",
                     "known_limitations:\n- description: a\n  description: b\n",
                     "confidential_elements:\n- id: x:a\n  id: x:b\n",
                     "confidential_elements:\n- source_caveats:\n    note: a\n    note: b\n",
                     # an ancestor whose dropped copy holds no scoped slot
                     "resources:\n- known_limitations:\n  - description: a\nresources:\n- id: x:part\n",
                     # the kept copy is the one holding the slot, and it is scanned
                     "resources:\n- id: x:part\nresources:\n- confidential_elements:\n  - name: a\n",
                     # `1` and `"1"` are two keys to the loader, so nothing is dropped
                     "1:\n  confidential_elements:\n  - name: a\n\"1\":\n  id: x:part\n",
                     # the loader merges every `<<`, so two are not a duplicate
                     "a: &a\n  confidential_elements: [x]\nb: &b\n  y: 1\nc:\n  <<: *a\n  <<: *b\n"):
            with self.subTest(text=text):
                self.assertEqual(rd.unread_duplicate_keys(text), [])


#: Two `resources` blocks: `safe_load` keeps the second, so the embargo entry
#: in the first is never scanned and the parse reads clean (#3005, #2980).
DUPLICATED_ANCESTOR = (
    "resources:\n"
    "- confidential_elements:\n"
    "  - confidential_elements_present: true\n"
    "    confidentiality_details: Two assay deposits are held under embargo.\n"
    "resources:\n"
    "- id: x:part\n"
)


class TestADuplicatedAncestorHidesAScopedSlot(unittest.TestCase):
    def test_the_parse_reads_clean_and_the_ancestor_is_named(self):
        self.assertEqual(_paths(yaml.safe_load(DUPLICATED_ANCESTOR)), [])  # what the parse shows
        self.assertEqual(_paths(yaml.safe_load(DUPLICATED_ANCESTOR.split("resources:\n- id")[0])),
                         ["resources[0].confidential_elements[0].confidentiality_details"])
        self.assertEqual([(d["path"], d["key"], d["lines"]) for d in rd.unread_duplicate_keys(DUPLICATED_ANCESTOR)],
                         [("$", "resources", [1, 5])])

    def test_the_slot_is_found_at_any_depth_and_through_any_key(self):
        for text, where in (
                ("resources:\n- parts:\n    x:\n      sensitive_elements: []\n  parts: {}\n",
                 ("resources[0]", "parts")),
                ("source_caveats:\n  confidential_elements: [a]\nsource_caveats: b\n", ("$", "source_caveats")),
                ("resources:\n- id: x:a\n- id: x:b\n  sub:\n  - confidential_elements: [a]\n  sub: []\n",
                 ("resources[1]", "sub")),
                ("base: &b\n  confidential_elements: [a]\nresources:\n  <<: *b\nresources: {}\n",
                 ("$", "resources"))):
            with self.subTest(text=text):
                self.assertEqual([(d["path"], d["key"]) for d in rd.unread_duplicate_keys(text)], [where])

    def test_a_scoped_slot_duplicated_inside_a_dropped_ancestor_is_named_with_it(self):
        text = ("resources:\n- confidential_elements: [a]\n  confidential_elements: [b]\n"
                "resources:\n- id: x:part\n")
        self.assertEqual([(d["path"], d["key"]) for d in rd.unread_duplicate_keys(text)],
                         [("$", "resources"), ("resources[0]", "confidential_elements")])

    def test_each_duplicate_is_named_once(self):
        """A scoped slot written twice whose dropped value also nests a scoped
        slot is caught by both rules and named once."""
        text = "confidential_elements:\n- sensitive_elements: [a]\nconfidential_elements: []\n"
        self.assertEqual([(d["path"], d["key"]) for d in rd.unread_duplicate_keys(text)],
                         [("$", "confidential_elements")])


#: Deeper than the composer (two frames a level) can recurse, whatever the limit.
DEEP = 2 * sys.getrecursionlimit() + 100


class TestARecordTheLoaderRejectsIsNotChecked(unittest.TestCase):
    """`check_text` never raises for a record the loader rejects (#3006)."""

    def test_whatever_the_loader_raises_is_a_reason_not_a_crash(self):
        for text, raised in (("created_on: 2026-02-30\n", "ValueError: day is out of range for month"),
                             ("created_on: 2026-13-01\n", "ValueError: month must be in 1..12"),
                             ("n: !!int abc\n", "ValueError"),
                             ("t: !!timestamp nope\n", "AttributeError"),
                             ("[" * DEEP + "]" * DEEP, "RecursionError")):
            with self.subTest(text=text[:30]):
                found, reason = rd.check_text(text)
                self.assertIsNone(found)
                self.assertIn(f"the YAML loader raised {raised}", reason)

    def test_a_syntax_error_and_a_list_keep_their_reasons(self):
        self.assertEqual(rd.check_text("a: b: c\n"), (None, "mapping values are not allowed here"))
        self.assertEqual(rd.check_text("- a list\n"), (None, "a record is a mapping, not list"))

    def test_a_scan_nested_past_the_limit_is_not_checked(self):
        from unittest import mock
        with mock.patch.object(rd, "slot_meaning_mismatch", side_effect=RecursionError("too deep")):
            self.assertEqual(rd.check_text("a: b\n"), (None, "too deep"))

    def test_a_readable_record_is_checked(self):
        found, reason = rd.check_text(yaml.safe_dump({"confidential_elements": [{"description": EMBARGO_TEXT}]}))
        self.assertIsNone(reason)
        self.assertEqual([m.path for m in found], ["confidential_elements[0].description"])
        self.assertEqual(rd.check_text("known_limitations: []\n"), ([], None))


#: What each released version reads. A new version adds a line, and a line
#: is not edited, so the findings of v1 mean one thing wherever they are
#: cited. Nothing here enforces that last rule: an old line rewritten in
#: place passes every test below and shows only in the diff.
LEXICON_PINS = {
    1: "03262c5bc4b3676d479ec509226545e7527dbb7090b62c003fbbca60e4834299",
}


class TestTheInstrument(unittest.TestCase):
    def test_the_lexicon_digest_is_pinned_to_the_version(self):
        """Editing the scope, the skipped keys, the lexicon or how it is
        compiled fails here until the new digest is pinned under the current
        version. A bump is what makes that pin a new line; re-pinning under
        an existing version also passes, and only the diff shows it (#3008).
        Two versions pinning one digest fail: a bump that changed nothing."""
        self.assertEqual(rd.INSTRUMENT_VERSION, max(LEXICON_PINS))
        self.assertEqual(rd.LEXICON_SHA256, LEXICON_PINS[rd.INSTRUMENT_VERSION])
        self.assertEqual(len(set(LEXICON_PINS.values())), len(LEXICON_PINS),
                         "two versions pin one lexicon: a bump that changed nothing, or an old pin rewritten")
        self.assertEqual(rd.INSTRUMENT, f"routing_diagnostics v{rd.INSTRUMENT_VERSION} (#2931)")

    def test_the_digest_covers_how_the_lexicon_is_compiled(self):
        """The alternatives alone do not fix what matches: the word-boundary
        wrapper and the case rule do too, so both move the digest."""
        import re
        digest = lambda patterns: rd._digest(rd.SCOPED_SLOTS, rd.SKIPPED_KEYS, patterns)  # noqa: E731
        self.assertEqual(digest(rd._PATTERNS), rd.LEXICON_SHA256)
        case_sensitive = {k: re.compile(p.pattern) for k, p in rd._PATTERNS.items()}
        unbounded = {k: re.compile("(?:" + "|".join(rd.LEXICON[k]) + ")", p.flags)
                     for k, p in rd._PATTERNS.items()}
        for changed in (case_sensitive, unbounded):
            self.assertNotEqual(digest(changed), rd.LEXICON_SHA256)
        self.assertNotEqual(rd._digest(rd.SCOPED_SLOTS[:1], rd.SKIPPED_KEYS, rd._PATTERNS), rd.LEXICON_SHA256)
        self.assertNotEqual(rd._digest(rd.SCOPED_SLOTS, frozenset({"id"}), rd._PATTERNS), rd.LEXICON_SHA256)

    def test_the_report_says_it_is_not_a_gate(self):
        block = rd.report({"confidential_elements": [{"description": EMBARGO_TEXT}]})
        self.assertEqual((block["instrument"], block["gating"], block["count"]),
                         (rd.INSTRUMENT, False, 1))
        self.assertEqual(block["mismatches"][0]["kinds"], [EMBARGO, RELEASE_TIMING])
        json.dumps(block)                                        # plain data

    def test_both_schemas_declare_the_slots_and_the_present_flags_the_scan_reads(self):
        """`_entries` reads `<slot>_present` off each entry; a schema rename
        would leave the instrument reading a key no record carries."""
        from data_sheets_schema import schema_digest
        from data_sheets_schema.schema_view import shared_view
        for target in ("Dataset", "CoreDataset"):
            view = shared_view(schema_digest.CLASS_SCHEMA[target])
            for slot in rd.SCOPED_SLOTS:
                with self.subTest(target=target, slot=slot):
                    declared = view.induced_slot(slot, target)
                    flag = view.induced_slot(f"{slot}_present", declared.range)
                    self.assertEqual(flag.range, "boolean")


class TestTheCommand(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.flagged = base / "flagged.yaml"
        self.flagged.write_text(yaml.safe_dump({"confidential_elements": [
            {"confidential_elements_present": True, "confidentiality_details": EMBARGO_TEXT}]}))
        self.routed = base / "routed.yaml"
        self.routed.write_text(yaml.safe_dump({"known_limitations": [{"description": EMBARGO_TEXT}]}))
        self.broken = base / "broken.yaml"
        self.broken.write_text("- a list\n- not a record\n")

    def _invoke(self, *args):
        from data_sheets_schema.cli.evaluate import evaluate
        return CliRunner().invoke(evaluate, ["slot-meaning", *map(str, args)])

    def test_findings_are_reported_and_do_not_fail_the_command(self):
        before = {p: p.read_bytes() for p in Path(self.tmp.name).iterdir()}
        out = self._invoke(self.flagged, self.routed)
        self.assertEqual(out.exit_code, 0, out.output)
        self.assertIn(f"{self.flagged}\n  confidential_elements[0].confidentiality_details: "
                      "embargo, release_timing", out.output)
        self.assertNotIn(str(self.routed), out.output)
        self.assertIn("1 slot-meaning mismatch(es) in 1 of 2 record(s) checked, 1 in an entry "
                      "asserting its elements present; not gating", out.output)
        self.assertEqual({p: p.read_bytes() for p in Path(self.tmp.name).iterdir()}, before)  # read-only

    def test_json_names_the_instrument_and_every_record(self):
        out = self._invoke("--json", self.flagged, self.routed)
        self.assertEqual(out.exit_code, 0, out.output)
        doc = json.loads(out.output)
        self.assertEqual((doc["instrument"], doc["gating"]), (rd.INSTRUMENT, False))
        self.assertEqual([(r["path"], r["checked"], r["count"]) for r in doc["records"]],
                         [(str(self.flagged), True, 1), (str(self.routed), True, 0)])

    def test_a_record_it_could_not_read_fails_the_command(self):
        """Non-gating on findings, but a record never looked at is not clean."""
        out = self._invoke(self.flagged, self.broken)
        self.assertEqual(out.exit_code, 1, out.output)
        self.assertIn(f"{self.broken}\n  not checked: a record is a mapping, not list", out.output)
        self.assertIn("1 record(s) could not be checked", out.output)

    def test_a_record_that_repeats_a_scoped_slot_is_not_checked(self):
        """The last value parses clean; the one before it is the finding."""
        duplicated = Path(self.tmp.name) / "duplicated.yaml"
        duplicated.write_text(DUPLICATED_SLOT)
        out = self._invoke(self.routed, duplicated)
        self.assertEqual(out.exit_code, 1, out.output)
        self.assertIn(f"{duplicated}\n  not checked: duplicate key `confidential_elements` at $ on lines 1, 6: "
                      "a loader keeps only the last", out.output)
        self.assertIn("0 slot-meaning mismatch(es) in 0 of 1 record(s) checked", out.output)

    def test_a_record_whose_ancestor_hides_a_scoped_slot_is_not_checked(self):
        """#3005: the second `resources` parses clean; the first held the embargo."""
        duplicated = Path(self.tmp.name) / "ancestor.yaml"
        duplicated.write_text(DUPLICATED_ANCESTOR)
        out = self._invoke(duplicated)
        self.assertEqual(out.exit_code, 1, out.output)
        self.assertIn(f"{duplicated}\n  not checked: duplicate key `resources` at $ on lines 1, 5", out.output)
        self.assertIn("0 slot-meaning mismatch(es) in 0 of 0 record(s) checked", out.output)
        doc = json.loads(self._invoke("--json", duplicated).output.split("\nError:")[0])
        self.assertEqual([(r["checked"], "resources" in r["reason"]) for r in doc["records"]], [(False, True)])

    def test_a_record_the_loader_rejects_does_not_silence_the_others(self):
        """#3006: an impossible unquoted date raises a bare ValueError."""
        bad_date = Path(self.tmp.name) / "bad_date.yaml"
        bad_date.write_text("id: example:ds\ncreated_on: 2026-02-30\n")
        out = self._invoke(self.flagged, bad_date, self.routed)
        self.assertEqual(out.exit_code, 1, out.output)
        self.assertIsInstance(out.exception, SystemExit, out.exception)        # not a traceback
        self.assertIn(f"{self.flagged}\n  confidential_elements[0].confidentiality_details", out.output)
        self.assertIn(f"{bad_date}\n  not checked: the YAML loader raised ValueError: day is out of range",
                      out.output)
        self.assertIn("1 slot-meaning mismatch(es) in 1 of 2 record(s) checked", out.output)
        self.assertIn("1 record(s) could not be checked", out.output)
        doc = json.loads(self._invoke("--json", self.flagged, bad_date).output.split("\nError:")[0])
        self.assertEqual([(r["path"], r["checked"]) for r in doc["records"]],
                         [(str(self.flagged), True), (str(bad_date), False)])


#: The nine CM4AI records #2931 parsed, by (method directory, label).
CM4AI_REPLAY = (
    ("claudecode_agent", "2026-08-28_claude-opus-5-claudecode-generic-v6_rep1"),
    ("claudecode_agent", "2026-08-28_claude-opus-5-claudecode-generic-v6_rep2"),
    ("claudecode_agent", "2026-08-28_claude-opus-5-claudecode-generic-v6_rep3"),
    ("claudecode_agent", "2026-09-01_claude-opus-5-api-generic-v7_rep1"),
    ("claudecode_agent", "2026-09-01_claude-opus-5-api-generic-v7_rep2"),
    ("claudecode_agent", "2026-09-01_claude-opus-5-api-generic-v7_rep3"),
    ("claudecode_api", "2026-09-04g_claude-opus-5-api-generic-v8_rep1"),
    ("claudecode_api", "2026-09-04g_claude-opus-5-api-generic-v8_rep2"),
    ("claudecode_api", "2026-09-04g_claude-opus-5-api-generic-v8_rep3"),
)

_DETAILS = ["confidential_elements[0].confidentiality_details"]
_NAME_AND_DETAILS = ["confidential_elements[0].name", *_DETAILS]
#: Expected flagged paths per label; every other label in the set flags nothing.
CM4AI_EXPECTED = {
    "2026-08-28_claude-opus-5-claudecode-generic-v6_rep2": _NAME_AND_DETAILS,
    "2026-08-28_claude-opus-5-claudecode-generic-v6_rep3": _NAME_AND_DETAILS,
    "2026-09-01_claude-opus-5-api-generic-v7_rep2": _DETAILS,
    "2026-09-04g_claude-opus-5-api-generic-v8_rep1": _DETAILS,
    "2026-09-04g_claude-opus-5-api-generic-v8_rep2": _DETAILS,
}


@pytest.mark.corpus   # reads 18 committed records by name; the main-branch lane (#1203)
class TestTheCommittedCM4AIRecords(unittest.TestCase):
    """Replay on the records the issue parsed. Each record's own path is
    named; nothing is globbed, and a record that moves fails here."""

    def _records(self, core):
        for method, label in CM4AI_REPLAY:
            path = (ROOT / "data/d4d_concatenated" / f"{method}_core" / label / "CM4AI_d4d_core.yaml"
                    if core else ROOT / "data/d4d_concatenated" / method / label / "CM4AI_d4d.yaml")
            self.assertTrue(path.is_file(), f"named record missing: {path}")
            yield label, yaml.safe_load(path.read_text(encoding="utf-8"))

    def _check(self, core):
        flagged = {}
        for label, record in self._records(core):
            found = slot_meaning_mismatch(record)
            if found:
                flagged[label] = [m.path for m in found]
                # Every finding here is the embargo, and every one claims the
                # elements exist — the defect the issue names.
                self.assertTrue(all(m.present is True and EMBARGO in m.kinds
                                    and m.slot == "confidential_elements" for m in found), label)
            # The embargo is stated in every record; unflagged ones state it
            # elsewhere, so a miss is the scope working, not absent text.
            self.assertIn("embargo", yaml.safe_dump(record).lower(), label)
        self.assertEqual(flagged, CM4AI_EXPECTED)

    def test_the_full_records_flag_exactly_the_five_the_issue_found(self):
        self._check(core=False)

    def test_the_core_twins_carry_the_same_five(self):
        self._check(core=True)


if __name__ == "__main__":
    unittest.main()
