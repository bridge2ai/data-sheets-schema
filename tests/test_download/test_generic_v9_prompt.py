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


class TestV9IsV8PlusTheAddedBlock(unittest.TestCase):
    VERSION_STAMP = re.compile(r"#\s*(?:Mode|Prompt):[^\n]*")

    def test_body_differs_from_v8_only_by_the_block(self):
        v8 = prompt_body(GENERIC_PROMPT_V8)
        v9 = prompt_body(GENERIC_PROMPT_V9)
        stripped = (v9.split(MARK_START, 1)[0] + v9.split(MARK_END, 1)[1]).strip()
        scrub = lambda t: _norm(self.VERSION_STAMP.sub("", t))  # noqa: E731
        self.assertEqual(scrub(stripped), scrub(v8))

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
            self.assertEqual(_norm(a), _norm(b), f"the {mark} block changed")

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
                      "core derivation reads to match",              # R8: the projector sentence (#803)
                      "a claim about that identifier, not a label",  # R8: the referent test (#901)
                      "labels a part of that thing, not of this one",  # R8: a fragment on another's identifier (#901)
                      "passage that states the category",            # R9: enumeration slots (#830 a)
                      "before any processing this dataset applied",  # R10: raw_data_format (#830 b)
                      "designate with that title",                   # R11: the source's own designation (#830 c)
                      "at the passage's own reach",                  # R12: consequence composed beyond the fact
                      "a line of bare terms is not one",             # R12: keyword lines (adjudication)
                      "is a member of that list",                    # R13: pointer entries
                      "An absence is not an entry, and a route is not a format"):  # R14: rule-06/07 traps
            self.assertIn(probe, block)

    def test_R8_resolves_every_referent_it_names(self):
        """#1059's lesson: a rule cannot converge while it points at
        nothing. R8 says which classes force an id; the schema must agree,
        and the projector it cites must match by id."""
        from linkml_runtime import SchemaView

        from data_sheets_schema.constants.schemas import SCHEMA_PATH
        sv = SchemaView(str(SCHEMA_PATH))
        for cls in ("File", "FileCollection", "DataSubset"):
            slot = sv.induced_slot("id", cls)
            self.assertTrue(slot.identifier or slot.required, cls)
        self.assertTrue(sv.induced_slot("id", "Person").identifier)
        for cls in ("Organization", "Grant"):                  # "where the schema does not require an id"
            slot = sv.induced_slot("id", cls)
            self.assertFalse(slot.identifier or slot.required, cls)
        from data_sheets_schema import derive_core
        import inspect
        self.assertIn('r.get("id")', inspect.getsource(derive_core._add_distributions))

    def test_R9_to_R14_name_slots_the_digest_declares(self):
        from data_sheets_schema import schema_digest
        digest = schema_digest.build("Dataset")
        known = {s.name for s in digest.slots} | {n.name for n in digest.nested}
        for n in digest.nested:
            known |= set(n.required) | set(n.optional)
        for slot in ("data_type", "collection_type", "relationship_type", "raw_data_format",
                     "principal_investigator", "scope_impact", "variables", "funders", "resources",
                     "source_caveats", "errata", "future_guarantees", "format", "prohibition_reason"):
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
