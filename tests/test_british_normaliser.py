"""The write-time American-spelling normaliser (#1002, v8 step J).

The instrument (`grounding.BRITISH_PATTERNS`, v3) says what is British; the
normaliser says what the American form is, one rule per pattern. The VOICE
v8 canary wrote `programme` four times in its own prose (8 counted, v7
worst 2) under a prompt that has asked for American English since v5 on
the API path (v4 on the agentic one).
"""

import unittest

import yaml

from data_sheets_schema import grounding
from data_sheets_schema.american_spelling import (RULES, americanise, normalise_british_spellings,
                                                  rules_cover_instrument)
from data_sheets_schema.api_runner import identifier_rewrite_summary, normalise_record_text

#: One or more samples per instrument pattern, British → American.
SAMPLES = {
    "licence": "license", "licences": "licenses", "licenced": "licensed", "licencing": "licensing",
    "analyse": "analyze", "analysed": "analyzed", "analysing": "analyzing",
    "organise": "organize", "organised": "organized", "organisation": "organization",
    "organisations": "organizations", "organisationally": "organizationally", "organisers": "organizers",
    "enrol": "enroll", "enrols": "enrolls", "enrolment": "enrollment", "enrolments": "enrollments",
    "programme": "program", "programmes": "programs",
    "standardise": "standardize", "standardisation": "standardization",
    "labelling": "labeling", "labelled": "labeled",
    "centre": "center", "centres": "centers", "centred": "centered", "centring": "centering",
    "recognise": "recognize", "recognised": "recognized",
    "utilise": "utilize", "utilisation": "utilization",
    "catalogue": "catalog", "catalogues": "catalogs", "catalogued": "cataloged", "cataloguing": "cataloging",
    "summarise": "summarize", "summarising": "summarizing",
    "behaviour": "behavior", "behaviours": "behaviors", "behavioural": "behavioral", "behaviourally": "behaviorally",
    "colour": "color", "coloured": "colored", "colourful": "colorful", "colourings": "colorings",
    "favour": "favor", "favourite": "favorite", "unfavourable": "unfavorable", "favourably": "favorably",
    "honour": "honor", "honourable": "honorable",
    "metre": "meter", "metres": "meters", "centimetres": "centimeters", "kilometre": "kilometer",
    "tumour": "tumor", "tumours": "tumors",
    "oedema": "edema", "oedematous": "edematous",
    "paediatric": "pediatric", "paediatrics": "pediatrics",
    "haemoglobin": "hemoglobin", "haematology": "hematology", "haemorrhage": "hemorrhage",
    "anaemia": "anemia", "anaemic": "anemic",
    "ageing": "aging",
    "travelling": "traveling", "travelled": "traveled", "travellers": "travelers",
    "counselling": "counseling", "counsellors": "counselors",
    "cancelled": "canceled", "cancelling": "canceling",
    "modelling": "modeling", "modelled": "modeled", "modellers": "modelers",
    "totalling": "totaling", "totalled": "totaled",
    "artefact": "artifact", "artefacts": "artifacts",
    "fibre": "fiber", "fibres": "fibers",
    "litre": "liter", "litres": "liters",
    "neighbourhood": "neighborhood", "labour": "labor", "laboured": "labored", "humourous": "humorous",
    "flavours": "flavors", "endeavour": "endeavor", "armour": "armor", "vapour": "vapor",
    "defence": "defense", "offences": "offenses", "pretence": "pretense",
    "fulfil": "fulfill", "fulfils": "fulfills", "fulfilment": "fulfillment",
    "practise": "practice", "practised": "practiced", "practises": "practices", "practising": "practicing",
    "sceptical": "skeptical", "scepticism": "skepticism", "sceptics": "skeptics",
    "sulphur": "sulfur", "sulphuric": "sulfuric",
    "minimise": "minimize", "optimised": "optimized", "personalisation": "personalization",
    "generalisability": "generalizability", "prioritising": "prioritizing", "characterisation": "characterization",
    "harmonised": "harmonized", "normalisations": "normalizations", "anonymisers": "anonymizers",
    "pseudonymised": "pseudonymized", "visualise": "visualize", "randomised": "randomized",
    "emphasise": "emphasize", "hypothesised": "hypothesized", "synthesise": "synthesize",
    "digitised": "digitized", "authorisation": "authorization", "operationalised": "operationalized",
    "tokenisation": "tokenization", "westernised": "westernized",
}

#: American words the instrument deliberately leaves alone (homographs).
UNTOUCHED = ("analyses", "practice", "license", "program", "emphasis", "hypothesis", "synthesis",
             "analysis", "specialist", "judgement", "cancellation", "centered", "meter", "enrollment")


class TestTheRules(unittest.TestCase):
    def test_every_instrument_pattern_has_a_rule_of_the_same_source(self):
        self.assertEqual(rules_cover_instrument(), [])
        self.assertEqual(len(RULES), len(grounding.BRITISH_PATTERNS))

    def test_every_sample_is_rewritten_to_its_american_form(self):
        for british, american in SAMPLES.items():
            with self.subTest(british):
                out, pairs, skipped = americanise(f"the {british} here")
                self.assertEqual(out, f"the {american} here")
                self.assertEqual((pairs, skipped), ([(british, american)], []))

    def test_every_instrument_pattern_is_exercised_by_a_sample(self):
        for pattern in grounding.BRITISH_PATTERNS:
            with self.subTest(pattern.pattern[:40]):
                self.assertTrue(any(pattern.search(w) for w in SAMPLES), "no sample hits this pattern")

    def test_the_instrument_counts_zero_on_what_the_normaliser_writes(self):
        # Capitalised forms between lower-case words: a title-case run would be skipped on purpose.
        prose = " ".join(SAMPLES) + ". the " + " the ".join(w.capitalize() for w in SAMPLES) + " the end"
        self.assertGreater(grounding.british_spellings(prose), 0)
        out, _, _ = americanise(prose)
        self.assertEqual(grounding.british_spellings(out), 0)

    def test_american_homographs_are_untouched(self):
        text = " ".join(UNTOUCHED)
        out, pairs, _ = americanise(text)
        self.assertEqual((out, pairs), (text, []))

    def test_case_is_preserved(self):
        out, _, _ = americanise("Programme PROGRAMME programme Organisation ANAEMIA")
        self.assertEqual(out, "Program PROGRAM program Organization ANEMIA")

    def test_quoted_spans_and_identifier_shaped_tokens_are_left_as_written(self):
        text = ('the programme "the Bridge2AI Programme" https://x.org/programme/ programme.csv '
                "doi:10.1/programme a@programme.org  centre_of_data programme")
        out, pairs, _ = americanise(text)
        self.assertEqual(out, ('the program "the Bridge2AI Programme" https://x.org/programme/ programme.csv '
                               "doi:10.1/programme a@programme.org  centre_of_data program"))
        self.assertEqual(pairs, [("programme", "program"), ("programme", "program")])

    def test_punctuation_after_a_full_stop_is_not_an_identifier(self):
        """#1004 (1): `'the programme.'` was exempt as an identifier — 10 residuals across the corpus."""
        for text, want in (("'the programme.'", "'the program.'"), ("(programme.)", "(program.)"),
                            ('programme."', 'program."'), ("programme...", "program..."),
                            ("e.g.programme", "e.g.programme"), ("10:30 programme", "10:30 program"),
                            ("programme: next", "program: next"),
                            # #1005: a fragment on a bare id, anchors, aliases and tags are not prose
                            ("id: x#person-favour", "id: x#person-favour"), ("&programme centre", "&programme center"),
                            ("*programme", "*programme"), ("!programme centre", "!programme center"),
                            ("the *programme* was", "the *program* was"), ("**colour** image", "**color** image"),
                            ("*emphasised*", "*emphasized*"), ("R&D programme", "R&D program"),
                            ("[programme](#programme)", "[programme](#programme)")):   # one token with `#`: protected whole
            with self.subTest(text):
                self.assertEqual(americanise(text)[0], want)

    def test_title_case_runs_and_genus_names_are_left_as_written_and_reported(self):
        """#1004 (2): the VOICE bundle names the Temerty Centre; "Temerty Center" would be a grounding error."""
        text = ("Temerty Centre for Artificial Intelligence, the Programme Director, Favour Okonkwo, "
                "Haemophilus influenzae; the programme's centre. Programme data")
        out, pairs, skipped = americanise(text)
        self.assertEqual(out, ("Temerty Centre for Artificial Intelligence, the Programme Director, Favour Okonkwo, "
                               "Haemophilus influenzae; the program's center. Program data"))
        self.assertEqual(skipped, [("Programme", "title-case run"), ("Centre", "title-case run"),
                                   ("Favour", "title-case run"), ("Haemophilus", "proper noun")])
        self.assertEqual(pairs, [("programme", "program"), ("Programme", "Program"), ("centre", "center")])

    def test_it_is_idempotent(self):
        once, _, _ = americanise(" ".join(SAMPLES))
        twice, pairs, _ = americanise(once)
        self.assertEqual((once, pairs), (twice, []))


RECORD = """# generated by the runner — provenance header: programme
id: doi:10.1/programme
title: The Programme Title
description: |
  A programme of work. The organisation analysed "the programme's" data
  and catalogued its behaviour at the centre.
programme_notes: keeps its key
keywords:
- programme
- 'organisation catalogue'
- "quoted programme"
funders:
- name: Wellcome Programme
  url: https://wellcome.org/programme
  notes: >
    the favourable centre
distribution:
  download_url: https://x.org/programme.zip
  path: data/programme.csv
"""


class TestTheYamlWalker(unittest.TestCase):
    def test_keys_header_and_identifiers_survive_and_prose_is_rewritten(self):
        log = []
        out = normalise_british_spellings(RECORD, phase="full", log=log)
        self.assertIn("# generated by the runner — provenance header: programme", out)
        self.assertIn("programme_notes: keeps its key", out)
        self.assertIn("id: doi:10.1/programme", out)
        self.assertIn("url: https://wellcome.org/programme", out)
        self.assertIn("download_url: https://x.org/programme.zip", out)
        self.assertIn("path: data/programme.csv", out)
        doc = yaml.safe_load(out)
        self.assertEqual(doc["title"], "The Programme Title")             # a title-case run: skipped, logged
        self.assertEqual(doc["description"],
                         "A program of work. The organization analyzed \"the programme's\" data\n"
                         "and cataloged its behavior at the center.\n")
        self.assertEqual(doc["keywords"], ["program", "organization catalog", "quoted programme"])
        self.assertEqual(doc["funders"][0]["name"], "Wellcome Programme")   # likewise
        self.assertEqual(doc["funders"][0]["notes"], "the favorable center\n")
        # What the instrument still counts: the header line, the four
        # identifier-shaped tokens (`/programme`, `programme.zip`, …) and the
        # two title-case runs — left as written on purpose, and counted on
        # purpose.
        self.assertEqual(grounding.british_spellings(out), 7)
        # Rule order, not text order: the fold by phase and slot does not care.
        self.assertEqual(sorted((e["slot"], e["from"]) for e in log if e["kind"] == "british_spelling_skipped"),
                         [("name", "Programme"), ("title", "Programme")])
        self.assertEqual(sorted((e["slot"], e["from"], e["to"]) for e in log if e["kind"] == "british_spelling"),
                         sorted([("description", "programme", "program"), ("description", "organisation", "organization"),
                          ("description", "analysed", "analyzed"), ("description", "catalogued", "cataloged"),
                          ("description", "behaviour", "behavior"), ("description", "centre", "center"),
                          ("keywords", "programme", "program"),
                          ("keywords", "organisation", "organization"), ("keywords", "catalogue", "catalog"),
                          ("notes", "favourable", "favorable"), ("notes", "centre", "center")]))
        self.assertTrue(all(e["phase"] == "full" for e in log))

    def test_block_scalar_list_items_and_comments(self):
        """#1004 (3, 4): `- |` is a block; a comment value and a trailing comment are not prose."""
        log = []
        text = ("notes:\n- |\n  # programme heading\n  programme: details\n  - programme item\n"
                "- programme  # programme comment\ncaveat: #programme\n")
        out = normalise_british_spellings(text, log=log)
        self.assertEqual(out, ("notes:\n- |\n  # program heading\n  program: details\n  - program item\n"
                               "- program  # programme comment\ncaveat: #programme\n"))
        self.assertEqual([e["slot"] for e in log], ["notes"] * 4)
        self.assertEqual(yaml.safe_load(out)["caveat"], None)

    def test_skips_reach_the_log_and_the_summary(self):
        log = []
        normalise_british_spellings("publisher:\n  name: Temerty Centre for AI\n", phase="full", log=log)
        self.assertEqual(log, [{"phase": "full", "kind": "british_spelling_skipped", "slot": "name",
                                "from": "Centre", "reason": "title-case run"}])
        summary = identifier_rewrite_summary(log)
        self.assertEqual(summary["british_skipped_count"], 1)
        self.assertEqual(summary["british_skipped"][0]["value"], "Centre")
        self.assertEqual(summary["british_occurrences"], 0)
        log = []
        normalise_british_spellings("funders:\n- name: the programme\n- name: another centre\n", phase="full", log=log)
        summary = identifier_rewrite_summary(log)
        self.assertEqual(summary["british_rewrites"],
                         [{"phase": "full", "slot": "name", "from": "programme", "to": "program"},
                          {"phase": "full", "slot": "name", "from": "centre", "to": "center"}])

    def test_verbatim_slots_sentence_boundaries_and_single_quoted_comments(self):
        """#1007: `variable_name: Haemoglobin` is the source's token; a full stop ends a title-case run;
        a `#` inside single quotes is content."""
        log = []
        out = normalise_british_spellings("variables:\n- variable_name: Haemoglobin\n  description: Haemoglobin level\n"
                                          "notes: Data were collected in Toronto. Programme staff labelled them\n"
                                          "c: 'x # programme'\n", log=log)
        doc = yaml.safe_load(out)
        self.assertEqual(doc["variables"][0], {"variable_name": "Haemoglobin", "description": "Hemoglobin level"})
        self.assertEqual(doc["notes"], "Data were collected in Toronto. Program staff labeled them")
        self.assertEqual(doc["c"], "x # program")
        self.assertEqual([(e["slot"], e["from"], e.get("reason")) for e in log if e["kind"].endswith("skipped")],
                         [("variable_name", "Haemoglobin", "verbatim slot")])

    def test_layout_is_preserved(self):
        out = normalise_british_spellings(RECORD)
        self.assertEqual([len(l) - len(l.lstrip()) for l in out.splitlines()],
                         [len(l) - len(l.lstrip()) for l in RECORD.splitlines()])
        self.assertEqual(out.count("\n"), RECORD.count("\n"))

    def test_the_record_chain_runs_it_last_and_the_summary_reports_it(self):
        out = normalise_record_text("id: doi:10.1/x\ntitle: A programme\n", phase="core")
        self.assertEqual(yaml.safe_load(out)["title"], "A program")
        summary = identifier_rewrite_summary([
            {"phase": "full", "kind": "british_spelling", "slot": "title", "from": "Programme", "to": "Program"},
            {"phase": "full", "kind": "british_spelling", "slot": "title", "from": "programme", "to": "program"},
            {"phase": "core", "kind": "british_spelling", "slot": "notes", "from": "centre", "to": "center"},
            {"phase": "full", "slot": "id", "from": "https://doi.org/10.1/x", "to": "doi:10.1/x"}])
        self.assertEqual(summary["british_occurrences"], 3)
        self.assertEqual(summary["british_distinct"], ["centre", "programme"])
        self.assertEqual(summary["british_spellings"]["full"]["title"]["occurrences"], 2)
        self.assertEqual(summary["occurrences"], 1)                    # identifier totals unchanged
        self.assertTrue(summary["british_normaliser"].startswith("v1 (#1002)"))


if __name__ == "__main__":
    unittest.main()
