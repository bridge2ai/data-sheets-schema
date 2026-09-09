"""generic-v9 must stay generic, and must be v8 plus its block.

Mirrors `test_generic_v8_prompt.py`. v9 adds **one block of nine rules** and
nothing else changes but the version stamp: R6, that a value in the
referent's own slots is supported by a passage about the referent, binding
the reconcile phase (#913); R7, that a list entry names exactly one
entity, with the signature of a merged one (#911); and, added before the
first v9 run, R8 (the fragment rule's carve-out for schema-forced ids and
the referent test for every other mint — #803, #901) and R9–R14, one per
slot-level trap that recurred in three or more independent reviews across
the v6–v8 arms (#830): enumeration slots, `raw_data_format`,
`principal_investigator`, consequence and keyword lines, list membership,
absence and route.

The runner-side half of v9 is the scope declaration itself (#932), rendered
by `api_runner.scope_block` and tested in `tests/test_scope_block.py`. R6
is the obligation that pairs with it: v8 told the model what to do with a
passage about another dataset and never showed it which datasets those were.
"""

import re
import unittest

from data_sheets_schema.api_runner import (
    CONDITION_AXES,
    CONDITION_PROMPTS,
    GENERIC_PROMPT_V8,
    GENERIC_PROMPT_V9,
    PHASE_INSTRUCTIONS,
    RECEIPT_CONDITIONS,
    comparable_conditions,
    condition_delta,
    prompt_body,
)

MARK_START = "--- ADDED IN v9 ---"
MARK_END = "--- END ADDED IN v9 ---"


def _added_block(text):
    return text.split(MARK_START, 1)[1].split(MARK_END, 1)[0]


def _norm(text):
    return re.sub(r"\s+", " ", text).strip()


# v9 corrected the spelling of the text it inherits (#1134): "organisation" and
# "recognise" stood in the v5 block and R7 while the same body says "Write
# American English throughout" and the runner rewrites British forms out of
# every record (#1002). v8 keeps them because its records were generated under
# those bytes and its pin is theirs; v9 had no record when it was corrected.
# The inheritance tests apply this to the v8 side only, so any other difference
# between the two still fails them.
SPELLING_CORRECTED_IN_V9 = {"organisation": "organization", "recognise": "recognize",
                            "neighbouring": "neighboring"}          # #1137 review, M1


def _as_v9_spells(text):
    for british, american in SPELLING_CORRECTED_IN_V9.items():
        text = text.replace(british, american)
    return text


# The sweep is the repository's own instrument (#1137 review, M2): the
# patterns `grounding.british_spellings` counts, the canary metric reads and
# the normaliser rewrites (#1002), under its declared version — not a second
# hand-written list, which omitted the v3 half and re-admitted `analyses`.
def british_forms(text):
    from data_sheets_schema import grounding
    text = grounding._QUOTED.sub("", text)
    return sorted({m.group(0).lower() for rx in grounding.BRITISH_PATTERNS for m in rx.finditer(text)})


class TestV9IsV8PlusTheAddedBlock(unittest.TestCase):
    VERSION_STAMP = re.compile(r"#\s*(?:Mode|Prompt):[^\n]*")

    def test_body_differs_from_v8_only_by_the_block(self):
        v8 = prompt_body(GENERIC_PROMPT_V8)
        v9 = prompt_body(GENERIC_PROMPT_V9)
        stripped = (v9.split(MARK_START, 1)[0] + v9.split(MARK_END, 1)[1]).strip()
        scrub = lambda t: _norm(self.VERSION_STAMP.sub("", t))  # noqa: E731
        self.assertEqual(scrub(stripped), scrub(_as_v9_spells(v8)))

    def test_the_version_stamp_names_v9(self):
        v9 = prompt_body(GENERIC_PROMPT_V9)
        self.assertIn("generic-v9 prompt", v9)
        self.assertIn("d4d_generic_arm_prompt_v9.md", v9)
        self.assertNotIn("generic-v8 prompt", v9)

    def test_the_earlier_additions_survive_intact(self):
        v8 = GENERIC_PROMPT_V8.read_text()
        v9 = GENERIC_PROMPT_V9.read_text()
        for mark in ("v2", "v3", "v4", "v5", "v6", "v8"):
            a = v8.split(f"--- ADDED IN {mark} ---", 1)[1].split(f"--- END ADDED IN {mark} ---", 1)[0]
            b = v9.split(f"--- ADDED IN {mark} ---", 1)[1].split(f"--- END ADDED IN {mark} ---", 1)[0]
            self.assertEqual(_norm(_as_v9_spells(a)), _norm(b), f"the {mark} block changed")

    def test_the_whole_file_writes_american_english(self):
        """The prompt's own prose is the example the model copies (#1134),
        and the rationale is what the next prompt is written from. The rule
        and the normaliser (#1002) both say American; the v9 body said
        "organisation" eight times, "recognise" once and "neighbouring" once
        while saying so, and the rationale two more (one the plural).
        Swept with the declared instrument, so the guard moves with it."""
        from data_sheets_schema import grounding
        text = GENERIC_PROMPT_V9.read_text()
        self.assertTrue(grounding.BRITISH_INSTRUMENT.startswith("v3"))
        found = british_forms(text)
        self.assertEqual(found, [], f"British forms in the v9 prompt file: {found}")
        self.assertEqual(grounding.british_spellings(prompt_body(GENERIC_PROMPT_V9)), 0)

    def test_the_sweep_sees_what_the_first_version_missed(self):
        """The first sweep was a hand-written list that passed on
        "neighbouring" (#1137 review, M1) and would have flagged the
        American plural "analyses" (M2)."""
        self.assertEqual(british_forms("a neighbouring field"), ["neighbouring"])
        self.assertEqual(british_forms("two analyses were run; the judgement stands"), [])
        self.assertEqual(british_forms('the "organisation" quoted from a source'), [])

    def test_the_corrected_spellings_are_the_only_ones_the_v8_side_needs(self):
        """Every entry of the correction table is a word v8 actually carries
        and v9 does not — a table entry nothing uses would let a future
        drift hide under it."""
        v8 = GENERIC_PROMPT_V8.read_text()
        v9 = GENERIC_PROMPT_V9.read_text()
        for british, american in SPELLING_CORRECTED_IN_V9.items():
            self.assertIn(british, v8)
            self.assertNotIn(british, v9)
            self.assertIn(american, v9)

    def test_the_block_carries_the_nine_registered_rules(self):
        block = _added_block(GENERIC_PROMPT_V9.read_text())
        bullets = re.findall(r"^- ", block, re.M)
        self.assertEqual(len(bullets), 9)                      # R6 (#913), R7 (#911), R8 (#803/#901), R9–R14 (#830)
        block = _norm(block)                                   # the file wraps at 78 columns
        for probe in ("subject is the referent",                    # R6: whose passage supports it
                      "reconcile phase",                             # R6: where the leaks survived
                      "not an assurance",                            # R6: an empty declaration promises nothing (#1072)
                      "names exactly one entity",                    # R7: the rule
                      "names a class of things",                     # R7: the signature
                      "is one entity, and splitting it",             # R7: the carve-out (#1072)
                      "does not reach an id the schema forces",      # R8: the carve-out (#803)
                      "software tool under `used_software`",         # R8: the Software hole (review finding 4)
                      "ORCID the evidence states first",             # R8 defers to the person rule (finding 5)
                      "the base to prefer",                          # R8: own id first (round 2, finding 4)
                      "finds its parts under it",                    # R8: the traceability reason, not a receipt cost (#1147)
                      "component dataset under `resources`",        # R8: a nested Dataset id is forced (round 2, finding 3)
                      "matched to the core by id",                   # R8: the projector, both facts (finding 9)
                      "a claim about that identifier, not a label",  # R8: the referent test (#901)
                      "is a role this record asserts",               # R8: creators/maintainers (finding 13)
                      "refines the rule that mints a label on an identifier the evidence supplies",  # R8 vs v5 (finding 6)
                      "labels a part of that entity, not of this one",  # R8: a fragment on another's identifier (#901)
                      "passage that states the category",            # R9: enumeration slots (#830 a)
                      "except where the schema requires the slot",   # R9: relationship_type (finding 1)
                      "read from the file the bundle names",         # R9: format/media_type/encoding/compression (finding 3)
                      "before any processing this dataset applied",  # R10: raw_data_format (#830 b)
                      "raw form and the released form are the same",  # R10: coincidence (finding 15)
                      "designate with that title",                   # R11: the source's own designation (#830 c)
                      "at the passage's own reach",                  # R12: consequence composed beyond the fact
                      "`keywords` is the one slot whose subject",    # R12: the keywords carve-out (finding 2)
                      "is a member of that list",                    # R13: pointer entries
                      "the `resources` of a file collection",        # R13: which resources (finding 7)
                      "An absence is not an entry, and a route is not a format",  # R14: rule-06/07 traps
                      "the `format` of a distribution"):             # R14: which format (finding 17)
            self.assertIn(probe, block)

    def test_R8_resolves_every_referent_it_names(self):
        """#1059's lesson: a rule cannot converge while it points at
        nothing. R8 says which classes force an id; the schema must agree,
        and the projector it cites must match by id."""
        from linkml_runtime import SchemaView

        from data_sheets_schema.constants.schemas import SCHEMA_PATH
        sv = SchemaView(str(SCHEMA_PATH))
        # every class with a forced id that some slot reachable from Dataset
        # ranges to must be named in R8, by its phrase (review finding 18:
        # the first version asserted the named classes only, and missed
        # Software, reachable from every object through used_software)
        phrases = {"File": "a file,", "FileCollection": "a file collection",
                   "DataSubset": "a data subset", "Person": "a person given as an object",
                   "Software": "software tool under `used_software`",
                   "Dataset": "component dataset under `resources`"}   # a nested Dataset (resources, parent_datasets) is forced too
        reachable, todo = set(), ["Dataset"]
        while todo:
            cls = todo.pop()
            if cls in reachable or not sv.get_class(cls, strict=False):
                continue
            reachable.add(cls)
            for sn in sv.class_slots(cls):
                rng = sv.induced_slot(sn, cls).range
                if rng and sv.get_class(rng, strict=False):
                    todo.append(rng)
        forced = set()
        for cls in reachable:                                  # Dataset included: it is reachable as a nested object
            try:
                slot = sv.induced_slot("id", cls)
            except Exception:                                 # noqa: BLE001
                continue
            if slot.identifier or slot.required:
                forced.add(cls)
        self.assertEqual(forced, set(phrases), "R8 must name every reachable forced-id class")
        block = _norm(_added_block(GENERIC_PROMPT_V9.read_text()))
        for cls, phrase in phrases.items():
            self.assertIn(phrase, block, cls)
        for cls in ("Organization", "Grant", "Creator"):      # "where the schema does not require an id"
            slot = sv.induced_slot("id", cls)
            self.assertFalse(slot.identifier or slot.required, cls)
        # R9's required-enum exemption has a referent: relationship_type is required
        self.assertTrue(sv.induced_slot("relationship_type", "DatasetRelationship").required)
        from data_sheets_schema import derive_core
        import inspect
        self.assertIn('r.get("id")', inspect.getsource(derive_core._add_distributions))
        # collection and file ids are copied into the core's distributions:
        # `id` is in both shared slot sets (review finding 9)
        from data_sheets_schema.d4d_pair_consistency import load_pair_schema
        from data_sheets_schema.derive_core import _distribution_slots
        slots = _distribution_slots(load_pair_schema())
        self.assertIn("id", slots["collection"]); self.assertIn("id", slots["file"])

    def test_R9_to_R14_name_slots_the_digest_declares(self):
        from data_sheets_schema import schema_digest
        digest = schema_digest.build("Dataset")
        known = {s.name for s in digest.slots} | {n.name for n in digest.nested}
        for n in digest.nested:
            known |= set(n.required) | set(n.optional)
        for slot in ("data_type", "collection_type", "raw_data_format", "used_software",
                     "principal_investigator", "scope_impact", "variables", "funders", "resources",
                     "source_caveats", "errata", "future_guarantees", "format", "prohibition_reason",
                     "keywords", "media_type", "encoding", "compression", "description",
                     "creators", "maintainers", "file_collections"):
            self.assertIn(slot, known, slot)

    def test_the_rules_name_no_value_from_a_record_they_will_be_scored_against(self):
        """R12–R14 were drafted from named verdicts (#830); the strings those
        verdicts quote must not appear, for the reason #1072 gave R7."""
        block = _norm(_added_block(GENERIC_PROMPT_V9.read_text())).lower()
        for lifted in ("representative subset marker", "deterioration", "no formal erratum",
                       "temerty", "co-principal", "lead investigators"):
            self.assertNotIn(lifted, block)

    def test_R7_names_no_value_from_a_record_it_will_be_scored_against(self):
        """The first draft used two grantor and collector strings verbatim
        from the AI_READI v7 violations (#1072). A canary scored on rule-05
        against examples taken from its own arm is partly self-confirming."""
        block = _norm(_added_block(GENERIC_PROMPT_V9.read_text())).lower()
        for lifted in ("device manufacturers", "study staff",
                       "phlebotomist", "laboratory assistant"):
            self.assertNotIn(lifted, block)

    def test_R6_pairs_with_the_declaration_the_runner_sends(self):
        """The rule refers to the scope block (#932). If the rule shipped
        without it — or the block were dropped — the model would be told to
        consult a declaration it never receives, which is the defect the
        rule exists to close."""
        from data_sheets_schema.api_runner import scope_block
        block = _norm(_added_block(GENERIC_PROMPT_V9.read_text()))
        self.assertIn("You are given a declared scope", block)
        rendered = scope_block("VOICE")
        self.assertIsNotNone(rendered)
        self.assertIn("DECLARED SCOPE", rendered)

    def test_no_project_is_named(self):
        from data_sheets_schema.constants import PROJECTS
        body = prompt_body(GENERIC_PROMPT_V9)
        for p in PROJECTS:
            self.assertNotIn(p, body)


class TestV9IsRegistered(unittest.TestCase):
    def test_condition_and_axes(self):
        self.assertIs(CONDITION_PROMPTS["generic_v9"], GENERIC_PROMPT_V9)
        self.assertEqual(CONDITION_AXES["generic_v9"], {"base": "v9", "tuned": False})
        self.assertIn("generic_v9", RECEIPT_CONDITIONS)                # the receipt rule carries over
        self.assertTrue(comparable_conditions("generic_v8", "generic_v9"))
        self.assertEqual(condition_delta("generic_v8", "generic_v9"), ["base"])


class TestTheBlockStaysGeneric(unittest.TestCase):
    """v8's guards, carried forward. R6 and R7 name no slot at all: R6
    speaks of "the slot that declaration names" because the declaration
    supplies the slot per project, and R7 of "one name, one role, one
    grantor, one system" because the shape is what recurs, not the slot.
    R8–R14 name slots, because each is keyed to where a trap recurred, and
    every backticked name must be one the digest renders (#742)."""

    def setUp(self):
        self.block = _added_block(GENERIC_PROMPT_V9.read_text())

    def test_no_dataset_identifiers(self):
        self.assertIsNone(re.search(r"10\.\d{4,}/|ror\.org/|orcid\.org/|\bdoi:", self.block))

    def test_no_expected_quantities(self):
        text = re.sub(r"\[\d+\]", "[]", self.block)
        self.assertIsNone(re.search(r"\b\d+\b", text), "a quantity in the rule is an outcome expectation")

    def test_no_reference_to_prior_runs(self):
        low = self.block.lower()
        for word in ("replicate", "earlier run", "previous", "arm ", "v8", "v6", "#708", "#710", "#805", "#916"):
            self.assertNotIn(word, low)

    def test_backticks_name_digest_vocabulary_only(self):
        """Slot names and class names the digest renders, plus the marker
        text: nothing else may be backticked (the #742 concern, narrowed)."""
        from data_sheets_schema import schema_digest
        digest = schema_digest.build("Dataset")
        known = {s.name for s in digest.slots} | {n.name for n in digest.nested}
        for n in digest.nested:
            known |= set(n.required) | set(n.optional)
        known |= {"(reference — a string, not an object)"}
        for tok in re.findall(r"`([^`]+)`", self.block):
            tok = _norm(tok)                                   # the file wraps at 78 columns
            self.assertIn(tok, known, f"`{tok}` is neither a digest name nor the marker")

    def test_v8_is_untouched_by_v9(self):
        v8 = GENERIC_PROMPT_V8.read_text()
        self.assertNotIn("ADDED IN v9", v8)
        self.assertIn("generic-v8 prompt", prompt_body(GENERIC_PROMPT_V8))


class TestTheConditionIsWiredComparably(unittest.TestCase):
    def test_v9_is_launchable_from_the_cli(self):
        import click.testing

        from data_sheets_schema.cli.api import api
        r = click.testing.CliRunner().invoke(api, ["batch", "--help"])
        self.assertIn("generic_v9", r.output)

    def test_r1s_example_agrees_with_the_digest(self):
        """R1 says a `Person` under `principal_investigator` takes an object.
        That is true only once #805 (PR #927) has inlined the slot — on a
        main that still marks it a reference, R1 contradicts the digest it
        defers to (#573 class). This is the merge-order assertion: it
        fails until #927 lands."""
        from data_sheets_schema import schema_digest
        digest = schema_digest.build("Dataset")
        creator = next(n for n in digest.nested if n.name == "Creator")
        self.assertEqual(creator.ranges["principal_investigator"], "Person")
        gov = next(n for n in digest.nested if n.name == "DataGovernance")
        self.assertEqual(gov.ranges["committee_contact"], "Person")

    def test_the_audit_phase_carries_the_e2_flags(self):
        audit = PHASE_INSTRUCTIONS["audit"]
        for probe in ("absent, pending or held elsewhere", "neighbouring field", "`prohibition_reason`",
                      "earlier release stated as the dataset's current state",
                      "computed from other figures"):
            self.assertIn(probe, audit)
        self.assertNotIn("v9 plan", audit)                     # nothing the model cannot read


if __name__ == "__main__":
    unittest.main()
