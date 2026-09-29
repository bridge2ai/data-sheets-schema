"""Person names checked against the bundle they were read from (#2918).

The CM4AI bundle names two authors only as `Axelsson U` and `Metallo C`.
Runs wrote `Ulrika Axelsson` and `Christian Metallo`, and four published
CM4AI records still carry `Christian Metallo`. The ORCID beside it is in
the bundle: the person is right, the given name came from memory. That is
#547's "right answer, no evidence" for a name, and identifier grounding
cannot see it because a name is not an identifier.
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema import name_grounding as ng
from data_sheets_schema.name_grounding import (
    BundleIndex,
    check_record,
    classify,
    exact_key,
    iter_name_leaves,
    name_tokens,
)

SLOTS = frozenset({"creators", "principal_investigator", "contact_person",
                   "committee_members"})


def cls(name: str, token: str, bundle: str) -> str:
    return classify(token, name_tokens(name), BundleIndex(bundle))


class TokenTest(unittest.TestCase):

    def test_two_or_more_letters_split_at_hyphens(self):
        self.assertEqual(name_tokens("Jean-Christophe Bélisle-Pipon"),
                         ["Jean", "Christophe", "Bélisle", "Pipon"])
        self.assertEqual(name_tokens("Metallo C"), ["Metallo"])
        self.assertEqual(name_tokens("M Muralidharan"), ["Muralidharan"])

    def test_identifier_spans_are_not_name_tokens(self):
        """`ORCID` is not part of anyone's name, and whether the id is in the
        bundle is #547's question."""
        self.assertEqual(name_tokens("Vardit Ravitsky (ORCID:0000-0002-7080-8801)"),
                         ["Vardit", "Ravitsky"])
        self.assertEqual(name_tokens("Jane Parker (jane.parker@example.org, "
                                     "https://orcid.org/0000-0002-1825-0097)"),
                         ["Jane", "Parker"])
        self.assertEqual(name_tokens("ORCID:0000-0002-7080-8801"), [])

    def test_a_decomposed_mark_stays_inside_its_token(self):
        """`[^\\W\\d_]+` would cut `Be\\u0301lisle` in two."""
        self.assertEqual(name_tokens("Bélisle"), ["Bélisle"])
        self.assertEqual(exact_key("Bélisle"), exact_key("Bélisle"))


class ClassTest(unittest.TestCase):
    """All four outcomes."""

    LIST = "Clark T; Parker J; Axelsson U; Ballllosero Navarro F; Metallo C; Muralidharan M"

    def test_grounded(self):
        self.assertEqual(cls("Ulrika Axelsson", "Ulrika", "Ulrika Axelsson (KTH)"), "grounded")
        self.assertEqual(cls("ulrika axelsson", "ulrika", "ULRIKA AXELSSON"), "grounded")

    def test_initial_expanded_after_the_surname(self):
        """The bundle's form: `Surname I`, one person per `;`."""
        for name, token in (("Christian Metallo", "Christian"), ("Ulrika Axelsson", "Ulrika"),
                            ("Tim Clark", "Tim"), ("Frida Ballllosero Navarro", "Frida")):
            with self.subTest(name=name):
                self.assertEqual(cls(name, token, self.LIST), "initial_expanded")

    def test_initial_expanded_before_the_surname(self):
        """`C. Metallo`, and hyphenated initials: `J.-C. Bélisle-Pipon`."""
        bundle = "as reported by C. Metallo and J.-C. Bélisle-Pipon."
        self.assertEqual(cls("Christian Metallo", "Christian", bundle), "initial_expanded")
        name = "Jean-Christophe Bélisle-Pipon"
        self.assertEqual(cls(name, "Jean", bundle), "initial_expanded")
        self.assertEqual(cls(name, "Christophe", bundle), "initial_expanded")

    def test_initials_written_together(self):
        """`Levinson MA`: both given names are expansions of that pair."""
        bundle = "Lenkiewicz J, Levinson MA, Marquez C"
        self.assertEqual(cls("Maxwell Adam Levinson", "Maxwell", bundle), "initial_expanded")
        self.assertEqual(cls("Maxwell Adam Levinson", "Adam", bundle), "initial_expanded")

    def test_diacritic_dropped(self):
        """Synthetic: the real CM4AI bundle writes both spellings (see the
        corpus test), so it cannot exercise this class."""
        bundle = "Jean-Christophe Bélisle-Pipon (Simon Fraser University)"
        name = "Jean-Christophe Belisle-Pipon"
        self.assertEqual(cls(name, "Belisle", bundle), "diacritic_dropped")
        self.assertEqual(cls(name, "Pipon", bundle), "grounded")

    def test_diacritic_dropped_is_symmetric(self):
        """A mark the record added is the same finding, under the issue's name."""
        self.assertEqual(cls("Frédéric Belisle", "Frédéric", "Frederic Belisle"), "diacritic_dropped")

    def test_absent(self):
        self.assertEqual(cls("Christian Smith", "Christian", self.LIST), "absent")
        self.assertEqual(cls("Christian Smith", "Smith", self.LIST), "absent")
        self.assertEqual(cls("Christian Metallo", "Christian", "Metallo X; Marquez D"), "absent")

    def test_another_persons_initial_is_not_this_persons(self):
        """In `Marquez C; Metallo X` and `Marquez C\\nMetallo X` the C is
        Marquez's trailing initial, not a leading initial of Metallo."""
        for bundle in ("Marquez C; Metallo X", "Marquez C\nMetallo X", "Marquez C, Metallo X"):
            with self.subTest(bundle=bundle):
                self.assertEqual(cls("Christian Metallo", "Christian", bundle), "absent")

    def test_a_word_in_lower_case_is_never_an_expanded_initial(self):
        """Prose in a person slot: `access requests` beside `Access R` is not
        a person whose initial R was expanded."""
        self.assertEqual(cls("access requests", "requests", "Access R forms"), "absent")
        self.assertEqual(cls("Christian Metallo", "Christian", "metallo C"), "absent")


class InitialExpandedIsAnExpansionTest(unittest.TestCase):
    """`initial_expanded` is a given name written where the bundle has only
    its initial (#3001). The `absent` cases here are tokens and capitals
    that are not that and were classed `initial_expanded` before review
    round 1; beside each, the real expansion the rule must keep. Whether a
    token is a finding is untouched: only its class moves."""

    def test_a_token_that_is_itself_initials_expands_nothing(self):
        """A degree (the corpus's `Jorge Contreras, JD`, AI_READI 2026-08-05
        v3 rep2) and initials the record kept as a pair."""
        name = "Jorge Contreras, JD"
        bundle = "Authors: Contreras J; Metallo C"
        self.assertEqual(cls(name, "Jorge", bundle), "initial_expanded")
        self.assertEqual(cls(name, "JD", bundle), "absent")
        self.assertEqual(cls("JC Bélisle-Pipon", "JC", "Bélisle-Pipon J-C"), "absent")

    def test_the_surname_is_a_word_the_record_writes_as_one(self):
        """The corpus's `… in the FAIRhub DataCite metadata` (AI_READI
        2026-08-11 rep1): `the` stood in for a surname because the bundle
        writes `The` before a capital. A run of capitals is no surname either."""
        bundle = "The D, and Levinson MA D; Hansen JN"
        self.assertEqual(cls("creator of record in the FAIRhub DataCite metadata", "DataCite",
                             bundle), "absent")
        self.assertEqual(cls("Dora MA", "Dora", bundle), "absent")
        self.assertEqual(cls("Jakob Hansen", "Jakob", bundle), "initial_expanded")

    def test_a_capital_glued_to_a_digit_is_not_an_initial(self):
        """The ORCID check digit before the next line's surname, as the CM4AI
        bundle writes `…-420X\\nMetallo C`, and a model name (`Dexcom G6`)."""
        bundle = "ORCID\n0000-0003-3960-420X\nMetallo C\nDexcom G6"
        self.assertEqual(cls("Xanthe Metallo", "Xanthe", bundle), "absent")
        self.assertEqual(cls("Christian Metallo", "Christian", bundle), "initial_expanded")
        self.assertEqual(BundleIndex(bundle).initials_beside("Dexcom"), set())

    def test_a_run_of_capitals_followed_by_a_word_is_an_acronym(self):
        """`Hansen JN, Gao J` gives Hansen `JN`; `Hansen JN reports` and
        `Clark RO-Crate` are prose. The cost: `Levinson MA and` is read the
        same way (see the module docstring)."""
        self.assertEqual(BundleIndex("Hansen JN, Gao J").initials_beside("Hansen"), {"j", "n"})
        self.assertEqual(cls("Jakob Hansen", "Jakob", "Hansen JN reports"), "absent")
        self.assertEqual(cls("Rosa Clark", "Rosa", "Clark RO-Crate"), "absent")

    def test_initials_do_not_run_on_into_other_capitals(self):
        """The CM4AI bundle's `Axelsson U\\nKTH Royal Institute`, `Clark T.
        EVI:` and `Bélisle-Pipon JC. A Scoping Review`: only a single capital
        continues a single capital, and a line break ends them."""
        for bundle, surname, not_an_initial, initial in (
                ("Axelsson U\nKTH Royal Institute", "Axelsson", "Kerstin", "Ulrika"),
                ("Axelsson U\nH. Smith", "Axelsson", "Hedda", "Ulrika"),
                ("Clark T. EVI: a platform", "Clark", "Viggo", "Tim"),
                ("Bélisle-Pipon JC. A Scoping Review", "Bélisle-Pipon", "Agathe", "Jean")):
            with self.subTest(bundle=bundle):
                self.assertEqual(cls(f"{not_an_initial} {surname}", not_an_initial, bundle),
                                 "absent")
                self.assertEqual(cls(f"{initial} {surname}", initial, bundle), "initial_expanded")

    def test_a_sentence_after_an_initial_is_not_a_second_initial(self):
        """`Clark T. A study` gives Clark no `A`; `Wilkinson, M. D. The FAIR`
        still gives Wilkinson both, because the `D` ends at its period."""
        self.assertEqual(cls("Amy Clark", "Amy", "Clark T. A study of"), "absent")
        for token in ("Mark", "David"):
            with self.subTest(token=token):
                self.assertEqual(cls("Mark David Wilkinson", token,
                                     "Wilkinson, M. D. The FAIR principles"), "initial_expanded")

    def test_the_next_entrys_leading_initial_is_not_this_surnames(self):
        """In `C. Metallo, T. Clark` the T opens Clark's entry. The mirror of
        `test_another_persons_initial_is_not_this_persons`."""
        bundle = "C. Metallo, T. Clark"
        self.assertEqual(cls("Tim Metallo", "Tim", bundle), "absent")
        self.assertEqual(cls("Christian Metallo", "Christian", bundle), "initial_expanded")
        self.assertEqual(cls("Tim Clark", "Tim", bundle), "initial_expanded")

    def test_capitals_ending_the_line_before_do_not_take_the_initial_after(self):
        """`La Jolla, CA\\nClark T`: whatever `CA` is, it is on another line,
        so Clark's own `T` still counts."""
        self.assertEqual(cls("Tim Clark", "Tim", "La Jolla, CA\nClark T"), "initial_expanded")

    def test_a_line_break_ends_initials_before_the_surname_too(self):
        """`Clark T.\\nA. Metallo`: the A is Metallo's. Read across the line
        break, `T. A.` would be one run that is Clark's trailing initials."""
        self.assertEqual(cls("Amy Metallo", "Amy", "Clark T.\nA. Metallo"), "initial_expanded")


class AfterTheSurnameSeparatorTest(unittest.TestCase):
    """The separators the docstring allows after a surname (#3003): at most
    one comma before the initial, and joiners or spaces, on one line,
    between the initials written together."""

    def test_one_comma_before_the_initial(self):
        self.assertEqual(cls("Christian Metallo", "Christian", "Metallo, C."), "initial_expanded")

    def test_two_commas_or_a_semicolon_end_the_entry(self):
        for bundle in ("Metallo,, C.", "Metallo; C."):
            with self.subTest(bundle=bundle):
                self.assertEqual(cls("Christian Metallo", "Christian", bundle), "absent")

    def test_initials_joined_after_the_surname(self):
        name = "Jean-Christophe Bélisle-Pipon"
        for bundle in ("Bélisle-Pipon J-C", "Bélisle-Pipon J.-C.", "Bélisle-Pipon J C",
                       "Bélisle-Pipon J-C and Metallo C"):
            for token in ("Jean", "Christophe"):
                with self.subTest(bundle=bundle, token=token):
                    self.assertEqual(cls(name, token, bundle), "initial_expanded")

    def test_spaces_on_one_line_join_initials_and_a_line_break_does_not(self):
        """Text extracted from a PDF spaces initials unevenly (`J  C`); a
        line break ends them (`J\\nC`)."""
        name = "Jean-Christophe Bélisle-Pipon"
        for token in ("Jean", "Christophe"):
            with self.subTest(token=token):
                self.assertEqual(cls(name, token, "Bélisle-Pipon J  C"), "initial_expanded")
        self.assertEqual(cls(name, "Jean", "Bélisle-Pipon J\nC"), "initial_expanded")
        self.assertEqual(cls(name, "Christophe", "Bélisle-Pipon J\nC"), "absent")


class LowerBoundTest(unittest.TestCase):
    """What a whole-bundle token match can and cannot see."""

    def test_a_given_name_in_another_persons_entry_grounds_the_token(self):
        """The documented lower bound. `Clark T` expanded into `Emma Clark`
        is not caught when an Emma is anywhere in the bundle."""
        bundle = "Emma Lundberg (KTH). Authors: Clark T; Parker J"
        out = check_record({"creators": [{"name": "Emma Clark"}]}, bundle, SLOTS)
        self.assertEqual(out["counts"]["grounded"], 2)
        self.assertEqual(out["findings"], [])

    def test_a_line_wrapped_name(self):
        """The CM4AI bundle has `Charlotte` once, as `Charlotte\\nMarquez`."""
        bundle = "Maxwell Adam Levinson1, Charlotte\nMarquez2, Sami Nourreddine2"
        out = check_record({"creators": [{"name": "Charlotte Marquez"}]}, bundle, SLOTS)
        self.assertEqual(out["counts"]["grounded"], 2)
        self.assertEqual(cls("Christian Metallo", "Christian", "Marquez C;\nMetallo\nC"),
                         "initial_expanded")

    def test_a_source_typo_is_grounded_as_written(self):
        """`Ballllosero` is the bundle's own spelling; a record that corrects
        it is not supported by the bytes."""
        bundle = "Axelsson U; Ballllosero Navarro F; Chinn B"
        kept = check_record({"creators": [{"name": "Ballllosero Navarro F"}]}, bundle, SLOTS)
        self.assertEqual(kept["counts"]["grounded"], 2)
        fixed = check_record({"creators": [{"name": "Frida Ballesteros Navarro"}]}, bundle, SLOTS)
        self.assertEqual({(f["token"], f["class"]) for f in fixed["findings"]},
                         {("Ballesteros", "absent"), ("Frida", "initial_expanded")})


class WalkTest(unittest.TestCase):

    def test_person_and_creator_slots_in_both_forms(self):
        record = {
            "id": "doi:10.1/x",
            "creators": [
                {"id": "ORCID:0000-0003-2404-3040", "name": "Christian Metallo",
                 "affiliations": [{"name": "University of California San Diego"}]},
                "Metallo C",
                {"id": "Uma Axelsson"},
                {"name": "CM4AI Consortium",
                 "principal_investigator": {"name": "Trey Ideker"}},
            ],
            "maintainers": [{"name": "Not A Person-Ranged Slot"}],
            "license_and_use_terms": {"contact_person": "Vardit Ravitsky (ORCID:0000-0002-7080-8801)"},
            "data_governance": {"committee_members": ["Jillian Parker", {"name": "Tim Clark"}]},
        }
        self.assertEqual(list(iter_name_leaves(record, SLOTS)), [
            ("creators[0].name", "Christian Metallo"),
            ("creators[1]", "Metallo C"),
            ("creators[3].name", "CM4AI Consortium"),
            ("creators[3].principal_investigator.name", "Trey Ideker"),
            ("license_and_use_terms.contact_person", "Vardit Ravitsky (ORCID:0000-0002-7080-8801)"),
            ("data_governance.committee_members[0]", "Jillian Parker"),
            ("data_governance.committee_members[1].name", "Tim Clark"),
        ])

    def test_the_slots_come_from_the_schema(self):
        """Derived, never listed: a new Person-ranged slot changes this set,
        and this test says so."""
        self.assertEqual(ng.person_name_slots(), frozenset({
            "committee_contact", "committee_members", "contact_person", "creators",
            "governance_committee_contact", "principal_investigator"}))


class CountTest(unittest.TestCase):

    BUNDLE = "Clark T; Axelsson U; Metallo C; Trey Ideker"

    def test_occurrences_and_distinct_are_both_reported(self):
        """One expanded name in two places is one fact and two occurrences."""
        record = {"creators": [{"name": "Christian Metallo"},
                               {"name": "Trey Ideker",
                                "principal_investigator": "Christian Metallo"}]}
        out = check_record(record, self.BUNDLE, SLOTS)
        self.assertEqual(out["counts"], {"grounded": 4, "diacritic_dropped": 0,
                                         "initial_expanded": 2, "absent": 0})
        self.assertEqual(out["distinct"]["initial_expanded"], 1)
        self.assertEqual(out["distinct"]["grounded"], 3)
        self.assertEqual(out["name_leaves"], 3)
        self.assertEqual(out["findings"], [
            {"kind": "name_token_not_in_bundle", "path": "creators[0].name",
             "name": "Christian Metallo", "token": "Christian", "class": "initial_expanded"},
            {"kind": "name_token_not_in_bundle", "path": "creators[1].principal_investigator",
             "name": "Christian Metallo", "token": "Christian", "class": "initial_expanded"},
        ])
        self.assertEqual(out["instrument"], ng.INSTRUMENT)

    def test_a_record_that_is_not_a_mapping_is_not_checked(self):
        self.assertFalse(check_record(["x"], self.BUNDLE, SLOTS)["checked"])
        self.assertEqual(check_record(None, self.BUNDLE, SLOTS)["reason"],
                         "the record is an empty document")

    def test_parse_record_names_what_pyyaml_raises(self):
        """An impossible date raises ValueError, not YAMLError."""
        self.assertEqual(ng.parse_record(b"release_date: 2026-02-30\n"),
                         (None, "does not parse: ValueError"))
        self.assertEqual(ng.parse_record(b"a: [\n"), (None, "does not parse: ParserError"))
        self.assertEqual(ng.parse_record(b"\xff"), (None, "does not parse: UnicodeDecodeError"))
        self.assertEqual(ng.parse_record(b"a: 1\n"), ({"a": 1}, None))


def _md5(raw: bytes) -> str:
    return hashlib.md5(raw).hexdigest()


READ = b"Authors: Ulrika Axelsson; Metallo C\n"        # what the run read
TODAY = b"Authors: Axelsson U; Metallo C\n"             # the bundle after it drifted
BUNDLE_PATH = "data/preprocessed/concatenated/P_preprocessed.txt"


def make_run(root: Path) -> dict:
    """One run P under label L in a corpus tree of its own: a provenance
    record's directory, a drifted bundle on disk, and three records."""
    concat = root / "data" / "d4d_concatenated"
    core_dir = concat / "claudecode_api_core" / "L"
    full_dir = concat / "claudecode_api" / "L"
    (core_dir / "intermediate").mkdir(parents=True)
    full_dir.mkdir(parents=True)
    bundle = root / BUNDLE_PATH
    bundle.parent.mkdir(parents=True)
    bundle.write_bytes(TODAY)
    record = {"creators": [{"name": "Ulrika Axelsson"}, {"name": "Christian Metallo"}]}
    (core_dir / "intermediate" / "P_full.yaml").write_text(yaml.safe_dump(record))
    (full_dir / "P_d4d.yaml").write_text(yaml.safe_dump(record))
    (core_dir / "P_d4d_core.yaml").write_text(yaml.safe_dump({"creators": [{"name": "Axelsson U"}]}))
    return {"core_dir": core_dir, "bundle": bundle, "provenance": core_dir / "P_provenance.yaml",
            "inputs": {"bundle_path": BUNDLE_PATH, "bundle_md5": _md5(READ)}}


class RunTest(unittest.TestCase):
    """`check_run` reads the bytes the record hashed, never a drifted file."""

    READ, BUNDLE_PATH = READ, BUNDLE_PATH

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        run = make_run(Path(self.tmp.name))
        self.core_dir, self.bundle = run["core_dir"], run["bundle"]
        self.provenance, self.inputs = run["provenance"], run["inputs"]

    def _run(self, inputs=None, records=ng.RECORDS):
        from data_sheets_schema import schema_cache
        self.provenance.write_text("# header\n" + yaml.safe_dump(
            {"run": {"project": "P"}, "inputs": self.inputs if inputs is None else inputs}))
        schema_cache.forget(self.provenance)   # a rewrite inside one mtime tick (#1203)
        return ng.check_run(self.provenance, records)

    def _entry(self):
        return {"commit": "c" * 40, "date": "2026-09-01", "md5": _md5(self.READ),
                "sha256": hashlib.sha256(self.READ).hexdigest(), "matched_on": ["md5"]}

    def test_a_drifted_bundle_is_read_as_the_version_the_record_hashed(self):
        """`Ulrika` is in the bytes the run read and not in today's file:
        grounded, where today's bytes would have made it an expansion."""
        with mock.patch("data_sheets_schema.provenance.bundle_bytes_for",
                        return_value=(self.READ, self._entry())) as git:
            out = self._run()
        git.assert_called_once_with(self.BUNDLE_PATH, md5=_md5(self.READ), sha256=None)
        self.assertTrue(out["checked"])
        self.assertEqual(out["bundle"]["source"], "git blob")
        self.assertEqual(out["bundle"]["commit"], "c" * 40)
        # The md5 of the bytes checked: the version read, not today's file.
        self.assertEqual(out["bundle"]["md5"], _md5(self.READ))
        self.assertNotEqual(out["bundle"]["md5"], _md5(TODAY))
        full = out["records"]["full"]
        self.assertEqual([(f["token"], f["class"]) for f in full["findings"]],
                         [("Christian", "initial_expanded")])

    def test_the_bundle_on_disk_when_it_is_the_bytes_hashed(self):
        self.bundle.write_bytes(self.READ)
        with mock.patch("data_sheets_schema.provenance.bundle_bytes_for",
                        side_effect=AssertionError("git was asked")):
            out = self._run()
        self.assertEqual(out["bundle"], {"source": "bundle on disk", "path": self.BUNDLE_PATH,
                                         "matched_on": ["md5"], "md5": _md5(self.READ)})

    def test_every_recorded_hash_must_match_the_file_on_disk(self):
        """The md5 matches and the sha256 does not: not the bytes read."""
        self.bundle.write_bytes(self.READ)
        inputs = {**self.inputs, "bundle_sha256": "0" * 64}
        with mock.patch("data_sheets_schema.provenance.bundle_bytes_for",
                        return_value=None) as git:
            out = self._run(inputs)
        git.assert_called_once()
        self.assertFalse(out["checked"])
        self.assertIn("is not those bytes", out["reason"])

    def test_no_recorded_hash_is_not_checked_and_git_is_not_asked(self):
        with mock.patch("data_sheets_schema.provenance.bundle_bytes_for",
                        side_effect=AssertionError("git was asked")):
            out = self._run({"bundle_path": self.BUNDLE_PATH})
        self.assertFalse(out["checked"])
        self.assertIn("pins no md5 or sha256", out["reason"])

    def test_no_committed_version_or_no_git_is_not_checked(self):
        from data_sheets_schema.provenance import GitUnavailable
        with mock.patch("data_sheets_schema.provenance.bundle_bytes_for", return_value=None):
            self.assertIn("no committed version", self._run()["reason"])
        with mock.patch("data_sheets_schema.provenance.bundle_bytes_for",
                        side_effect=GitUnavailable("shallow clone")):
            out = self._run()
        self.assertFalse(out["checked"])
        self.assertIn("shallow clone", out["reason"])

    def test_the_record_scope_is_named_and_each_record_reported(self):
        self.bundle.write_bytes(self.READ)
        out = self._run()
        self.assertEqual(out["record_scope"], ["phase1", "full", "core"])
        self.assertEqual(set(out["records"]), {"phase1", "full", "core"})
        self.assertTrue(out["records"]["phase1"]["path"].endswith("intermediate/P_full.yaml"))
        self.assertEqual(out["records"]["core"]["findings"], [])
        only = self._run(records=("core",))
        self.assertEqual(list(only["records"]), ["core"])

    def test_a_run_without_a_phase1_snapshot_says_so(self):
        self.bundle.write_bytes(self.READ)
        (self.core_dir / "intermediate" / "P_full.yaml").unlink()
        out = self._run()
        self.assertEqual(out["records"]["phase1"],
                         {"checked": False, "path": None, "reason": "the run kept no phase-1 snapshot"})
        self.assertTrue(out["records"]["full"]["checked"])

    def test_a_phase1_snapshot_that_cannot_be_read_is_reported(self):
        """An attested snapshot whose bytes changed raises UsageLedgerError."""
        from data_sheets_schema.usage_ledger import UsageLedgerError
        self.bundle.write_bytes(self.READ)
        with mock.patch("data_sheets_schema.receipts.phase1_snapshot_read",
                        side_effect=UsageLedgerError("generation snapshot bytes changed")):
            out = self._run()
        self.assertFalse(out["records"]["phase1"]["checked"])
        self.assertIn("snapshot bytes changed", out["records"]["phase1"]["reason"])
        self.assertTrue(out["records"]["full"]["checked"])

    def test_one_record_that_does_not_parse_leaves_the_others_checked(self):
        self.bundle.write_bytes(self.READ)
        full = self.core_dir.parent.parent / "claudecode_api" / "L" / "P_d4d.yaml"
        full.write_text("release_date: 2026-02-30\ncreators: [{name: Christian Metallo}]\n")
        out = self._run()
        self.assertEqual(out["records"]["full"],
                         {"checked": False, "path": str(full), "reason": "does not parse: ValueError"})
        self.assertTrue(out["records"]["phase1"]["checked"])
        self.assertTrue(out["records"]["core"]["checked"])

    def test_bundle_bytes_that_are_not_utf8_are_refused(self):
        """Decoded with replacement, `B\\ufffdlisle` would lose `Bélisle`
        and report a finding the bytes do not support."""
        raw = "Authors: Jean-Christophe Bélisle-Pipon\n".encode("latin-1")
        self.bundle.write_bytes(raw)
        out = self._run({"bundle_path": self.BUNDLE_PATH, "bundle_md5": _md5(raw)})
        self.assertFalse(out["checked"])
        self.assertIn("not UTF-8", out["reason"])
        self.assertEqual(out["bundle"]["source"], "bundle on disk")

    def test_a_provenance_record_that_does_not_parse_is_not_checked(self):
        self.provenance.write_text("inputs: [\n")
        out = ng.check_run(self.provenance)
        self.assertFalse(out["checked"])
        self.assertIn("cannot be read", out["reason"])


class CliTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.record = root / "r.yaml"
        self.record.write_text(yaml.safe_dump({"creators": [{"name": "Christian Metallo"}]}))
        self.bundle = root / "b.txt"
        self.bundle.write_text("Clark T; Metallo C\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _invoke(self, *args):
        from data_sheets_schema.cli import cli
        return CliRunner().invoke(cli, ["provenance", "name-grounding", *args])

    def test_a_record_and_a_bundle(self):
        result = self._invoke("--full", str(self.record), "--bundle", str(self.bundle))
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("lower bound", result.output)
        self.assertIn("given on the command line", result.output)
        self.assertIn("1 name leaf; grounded 1 (1 distinct) · diacritic_dropped 0 · "
                      "initial_expanded 1 (1 distinct) · absent 0", result.output)
        self.assertIn("creators[0].name 'Christian Metallo': Christian (initial_expanded)",
                      result.output)

    def test_json(self):
        result = self._invoke("--full", str(self.record), "--bundle", str(self.bundle), "--json")
        self.assertEqual(result.exit_code, 0, result.output)
        [out] = json.loads(result.output)
        self.assertEqual(out["records"]["given"]["counts"]["initial_expanded"], 1)
        self.assertEqual(out["bundle"]["md5"], _md5(self.bundle.read_bytes()))

    def test_a_bundle_or_record_that_cannot_be_read_is_refused(self):
        self.bundle.write_bytes("Bélisle-Pipon J-C\n".encode("latin-1"))
        result = self._invoke("--full", str(self.record), "--bundle", str(self.bundle))
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("not UTF-8", result.output)
        self.bundle.write_text("Clark T; Metallo C\n")
        self.record.write_text("release_date: 2026-02-30\n")
        result = self._invoke("--full", str(self.record), "--bundle", str(self.bundle))
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("does not parse: ValueError", result.output)

    def test_the_modes_do_not_mix(self):
        self.assertEqual(self._invoke("--full", str(self.record)).exit_code, 2)
        self.assertEqual(self._invoke("--full", str(self.record), "--bundle", str(self.bundle),
                                      "--label", "L").exit_code, 2)
        self.assertEqual(self._invoke().exit_code, 2)

    def test_a_label_reads_the_run_through_its_provenance_record(self):
        """The run mode is `check_run` on each record the label holds."""
        run = make_run(Path(self.tmp.name) / "corpus")
        run["bundle"].write_bytes(READ)
        run["provenance"].write_text(yaml.safe_dump({"run": {"project": "P"}, "inputs": run["inputs"]}))
        with mock.patch("data_sheets_schema.provenance.record_path_for",
                        lambda project, method, label: run["core_dir"] / f"{project}_provenance.yaml"):
            result = self._invoke("--label", "L", "--method", "claudecode_api",
                                  "--record", "full")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("P L [claudecode_api]", result.output)
        self.assertIn(f"bundle on disk, matched on md5; md5 {_md5(READ)}", result.output)
        self.assertIn("record scope: full", result.output)
        self.assertIn("2 name leaves;", result.output)
        self.assertIn("Christian (initial_expanded)", result.output)


# The committed CM4AI runs on the bundle the issue measured (md5 50037fc6…).
CM4AI_RUNS = {
    ("claudecode_agent", "2026-09-01_claude-opus-5-api-generic-v7_rep1"): {"Christian"},
    ("claudecode_agent", "2026-09-01_claude-opus-5-api-generic-v7_rep2"): {"Christian", "Tim"},
    ("claudecode_agent", "2026-09-01_claude-opus-5-api-generic-v7_rep3"): set(),
    ("claudecode_api", "2026-09-04_claude-opus-5-api-generic-v8_rep1"): {"Christian"},
    ("claudecode_api", "2026-09-04b_claude-opus-5-api-generic-v8_rep1"): {"Christian"},
    ("claudecode_api", "2026-09-04c_claude-opus-5-api-generic-v8_rep1"): set(),
    ("claudecode_api", "2026-09-04g_claude-opus-5-api-generic-v8_rep1"): set(),
    ("claudecode_api", "2026-09-04g_claude-opus-5-api-generic-v8_rep2"): {"Christian", "Ulrika"},
    ("claudecode_api", "2026-09-04g_claude-opus-5-api-generic-v8_rep3"):
        {"Alina", "Brenton", "Christian", "Frida", "Tim", "Ulrika"},
}
#: The four published finals the issue lists, and their cores; the audit
#: repaired 04g rep2 and rep3, whose finals carry none.
PUBLISHED_WITH_CHRISTIAN = {
    ("claudecode_agent", "2026-09-01_claude-opus-5-api-generic-v7_rep1"),
    ("claudecode_agent", "2026-09-01_claude-opus-5-api-generic-v7_rep2"),
    ("claudecode_api", "2026-09-04_claude-opus-5-api-generic-v8_rep1"),
    ("claudecode_api", "2026-09-04b_claude-opus-5-api-generic-v8_rep1"),
}
CM4AI_BUNDLE_MD5 = "50037fc631eafda807e19f83f6579818"


def _skip_if_shallow(out: dict) -> None:
    """A drifted bundle is recovered from git history, which a shallow clone
    does not have (`bundle_blob_history` refuses it rather than reporting no
    match); CI's merge lane checks out with fetch-depth 0."""
    if not out.get("checked") and "shallow" in str(out.get("reason")):
        raise unittest.SkipTest("shallow clone: the version the record hashed is not here")


@pytest.mark.corpus   # walks committed records under data/d4d_concatenated (#1203)
class CorpusTest(unittest.TestCase):
    """The issue's CM4AI table, reproduced on the bytes each record hashed.

    Record scope: for each of the nine CM4AI runs generated on bundle md5
    50037fc6…, the phase-1 snapshot (`intermediate/CM4AI_full.yaml`, the
    issue's "intermediate full records"), the final full record and the
    derived core, each checked on its own.
    """

    @classmethod
    def setUpClass(cls):
        from data_sheets_schema.provenance import record_path_for
        cls.results = {}
        for method, label in CM4AI_RUNS:
            path = record_path_for("CM4AI", method, label)
            if not path.exists():
                raise unittest.SkipTest(f"{path} is not in this checkout")
            cls.results[(method, label)] = out = ng.check_run(path)
            _skip_if_shallow(out)

    def _tokens(self, key, which):
        rec = self.results[key]["records"][which]
        self.assertTrue(rec.get("checked"), rec)
        return {f["token"] for f in rec["findings"]}

    def test_every_run_read_the_measured_bundle_and_names_its_scope(self):
        """The bytes checked are the measured bundle's (#3002): a run whose
        record pinned, or resolved to, any other bundle fails here, not only
        in the table tests downstream."""
        for key, out in self.results.items():
            with self.subTest(run=key[1]):
                self.assertTrue(out["checked"], out.get("reason"))
                self.assertEqual(out["bundle"]["md5"], CM4AI_BUNDLE_MD5)
                self.assertIn(out["bundle"]["source"], ("bundle on disk", "git blob"))
                self.assertIn("md5", out["bundle"]["matched_on"])
                self.assertEqual(out["record_scope"], ["phase1", "full", "core"])
                self.assertEqual(list(out["records"]), out["record_scope"])

    def test_the_intermediate_full_records_report_the_issues_table(self):
        for key, expected in CM4AI_RUNS.items():
            with self.subTest(run=key[1]):
                self.assertEqual(self._tokens(key, "phase1"), expected)

    def test_the_published_finals_and_their_cores_carry_christian(self):
        for key in CM4AI_RUNS:
            for which in ("full", "core"):
                with self.subTest(run=key[1], record=which):
                    expected = {"Christian"} if key in PUBLISHED_WITH_CHRISTIAN else set()
                    self.assertEqual(self._tokens(key, which), expected)

    def test_every_expansion_on_this_bundle_is_of_an_initial(self):
        """Each flag is a surname the bundle gives with that initial only."""
        classes = {f["class"] for out in self.results.values()
                   for rec in out["records"].values() for f in rec["findings"]}
        self.assertEqual(classes, {"initial_expanded"})

    def test_belisle_pipon_is_grounded_in_the_real_bundle(self):
        """The issue's criterion said `diacritic_dropped`. The bundle writes
        the name without the mark six times, so both spellings ground."""
        from data_sheets_schema.provenance import record_path_for
        path = record_path_for("CM4AI", *next(iter(PUBLISHED_WITH_CHRISTIAN)))
        raw, basis = ng.record_bundle_bytes(yaml.safe_load(path.read_text(encoding="utf-8")), path)
        self.assertEqual(hashlib.md5(raw).hexdigest(), CM4AI_BUNDLE_MD5, basis)
        text = raw.decode("utf-8")
        self.assertEqual(text.count("Belisle-Pipon"), 6)
        self.assertGreater(text.count("Bélisle-Pipon"), 0)
        for spelling in ("Jean-Christophe Belisle-Pipon", "Jean-Christophe Bélisle-Pipon"):
            with self.subTest(spelling=spelling):
                out = check_record({"creators": [{"name": spelling}]}, text)
                self.assertEqual(out["counts"]["grounded"], 4)
                self.assertEqual(out["findings"], [])

    def test_the_command_reports_the_same_run(self):
        from data_sheets_schema.cli import cli
        result = CliRunner().invoke(cli, [
            "provenance", "name-grounding", "--label",
            "2026-09-01_claude-opus-5-api-generic-v7_rep2", "--project", "CM4AI", "--json"])
        self.assertEqual(result.exit_code, 0, result.output)
        [out] = json.loads(result.output)
        self.assertEqual(out["method"], "claudecode_agent")
        self.assertEqual({f["token"] for f in out["records"]["phase1"]["findings"]},
                         {"Christian", "Tim"})
        self.assertEqual([f["path"] for f in out["records"]["full"]["findings"]],
                         ["creators[17].name"])


#: The corpus's three `initial_expanded` occurrences that expanded nothing
#: (#3001), each read on the bytes its run hashed: a degree kept beside the
#: name, and an organisation word with `the` standing in for a surname.
NOT_EXPANSIONS = {
    ("claudecode_agent", "2026-08-05_claude-opus-5-1m-generic-v3_rep2", "AI_READI"):
        {("full", "creators[5].principal_investigator", "JD"),
         ("core", "creators[5].principal_investigator", "JD")},
    ("claudecode_agent", "2026-08-11_claude-opus-5-api-generic_rep1", "AI_READI"):
        {("phase1", "creators[20].principal_investigator", "DataCite")},
}


@pytest.mark.corpus   # reads committed records under data/d4d_concatenated (#1203)
class NotAnExpansionCorpusTest(unittest.TestCase):
    """Record scope: the records named in `NOT_EXPANSIONS`. Each token is
    still a finding; only its class is `absent`, not `initial_expanded`."""

    def test_a_degree_and_an_organisation_word_are_absent(self):
        from data_sheets_schema.provenance import record_path_for
        for (method, label, project), expected in NOT_EXPANSIONS.items():
            path = record_path_for(project, method, label)
            if not path.exists():
                self.skipTest(f"{path} is not in this checkout")
            out = ng.check_run(path)
            _skip_if_shallow(out)
            for which, where, token in expected:
                with self.subTest(run=label, record=which, token=token):
                    rec = out["records"][which]
                    self.assertTrue(rec.get("checked"), rec)
                    self.assertIn((where, token, "absent"),
                                  {(f["path"], f["token"], f["class"]) for f in rec["findings"]})


#: A run whose bundle drifted after it. The AI_READI bytes it hashed (the
#: 2026-07-28 version) carry `captured` three times and today's file none,
#: and its core's `license_and_use_terms.contact_person` is prose that says
#: "the captured license text": grounded on the bytes the run read, a
#: finding on today's. The one such record among the 192 drifted ones.
DRIFTED = ("claudecode_agent", "2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2", "AI_READI")


@pytest.mark.corpus   # reads a committed record under data/d4d_concatenated (#1203)
class DriftCorpusTest(unittest.TestCase):
    """Record scope: that one run's phase-1 snapshot, full record and core."""

    def test_a_drifted_run_is_read_on_the_bytes_it_hashed(self):
        from data_sheets_schema.backfill_checks import declared_bundle
        from data_sheets_schema.provenance import record_path_for
        method, label, project = DRIFTED
        path = record_path_for(project, method, label)
        if not path.exists():
            self.skipTest(f"{path} is not in this checkout")
        out = ng.check_run(path)
        _skip_if_shallow(out)
        self.assertTrue(out["checked"], out.get("reason"))
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        raw, _ = ng.record_bundle_bytes(record, path)
        self.assertEqual(hashlib.md5(raw).hexdigest(), record["inputs"]["bundle_md5"])
        today = declared_bundle(record, path).read_bytes()
        today_words = BundleIndex(today.decode("utf-8")).exact
        if hashlib.md5(today).hexdigest() == record["inputs"]["bundle_md5"] or "captured" in today_words:
            self.skipTest("today's bundle no longer separates the two readings")
        self.assertIn("captured", BundleIndex(raw.decode("utf-8")).exact)
        self.assertEqual(out["bundle"]["source"], "git blob")
        self.assertEqual(out["record_scope"], ["phase1", "full", "core"])
        for which in ("phase1", "full", "core"):
            with self.subTest(record=which):
                self.assertTrue(out["records"][which]["checked"], out["records"][which])
                self.assertEqual(out["records"][which]["findings"], [])
        core = yaml.safe_load(Path(out["records"]["core"]["path"]).read_text(encoding="utf-8"))
        self.assertIn(("license_and_use_terms.contact_person", "captured", "absent"),
                      {(f["path"], f["token"], f["class"])
                       for f in check_record(core, today.decode("utf-8"))["findings"]})


if __name__ == "__main__":
    unittest.main()
