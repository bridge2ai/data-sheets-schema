"""The American-English rule is stated where it does not redefine a condition (#502).

From Camille Nebeker's review. The rule itself is uncontroversial; *where* it is
written is the decision, because editing a condition prompt rotates its pin and
v1's pin is what the fifteen records of the 2026-08-11 canonical arm hashed.
Rotating it would move all fifteen from `canonical` to `superseded`.

So the rule lives in the playbook, and these tests hold both halves: that it is
stated there, and that stating it disturbed no pin.
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
#: The rules live in one file since #563; before that they were inside
#: d4d-full-core.md, where /d4d-agent could not see them.
PLAYBOOK = ROOT / ".claude/commands/d4d-uniform-rules.md"
PROMPTS = ROOT / "src/download/prompts"


class TestTheRuleIsStated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAYBOOK.read_text(encoding="utf-8")

    def test_the_playbook_states_american_english(self):
        self.assertIn("American English", self.text)

    def test_it_sits_among_the_uniform_decision_rules(self):
        """Not in a section a run might skip. The uniform rules are the ones
        the playbook says to enforce whether or not a prompt file was used."""
        # The rules are a file of their own since #563, so the section is the
        # file below its heading rather than a span between two headings.
        start = self.text.index("Uniform decision rules")
        self.assertIn("American English", self.text[start:])

    def test_the_three_carve_outs_are_present(self):
        """Without them the rule instructs a run to corrupt evidence — the
        bundles contain `licence` 13 times and `programme` 6."""
        section = self.text[self.text.index("American English"):]
        for phrase in ("Quoted source text", "Proper nouns",
                       "Identifiers copied from a source"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_the_load_bearing_rule_is_named_not_positional(self):
        """It used to read "the last rule", which a later insertion would
        silently repoint at something else."""
        self.assertNotIn("The last rule is the load-bearing", self.text)
        self.assertIn("no target slot count is the load-bearing", self.text)


class TestTheRunnerSendsWhatItAsksFor(unittest.TestCase):
    """Every piece of prose the runner writes into a request — the phase
    instructions and layout the assembly digest hashes, and the system
    prompt, repair prompts, core inventory block and headers it does not —
    writes the American English the rule asks for and the normaliser
    enforces (#1138): the audit phase said "neighbouring field" on every API
    run while #1002 rewrote the same word out of every record. Swept with
    the declared instrument as the instrument applies it — lower-cased, and
    with no quotation exemption, since text the repository authors quotes no
    source and an example the model is told to copy is the surface that
    matters (#1151 review, M1/S1/S2)."""

    def test_no_sent_surface_carries_a_british_form(self):
        from data_sheets_schema import api_runner
        from tests.british_sweep import british_forms
        surfaces = api_runner.sent_text_surfaces()
        # Exact, not a floor (#1151 round 2, S1): deleting a surface from the
        # map is the regression this guard exists to catch. Nine phase
        # instructions, the layout, and ten authored surfaces.
        self.assertEqual(len(surfaces), 20, sorted(surfaces))
        for name, text in surfaces.items():
            with self.subTest(surface=name):
                found = british_forms(text, exempt_quotes=False)
                self.assertEqual(found, [], f"British forms in {name}: {found}")

    def test_the_sweep_sees_a_capitalised_form_and_a_quoted_example(self):
        """What the first version missed: the patterns are case-sensitive and
        the instrument lower-cases; a double-quoted example is authored."""
        from tests.british_sweep import british_forms
        self.assertEqual(british_forms("Neighbouring fields are read together."), ["neighbouring"])
        self.assertEqual(british_forms('write it exactly as "the programme centre"', exempt_quotes=False),
                         ["centre", "programme"])
        self.assertEqual(british_forms('write it exactly as "the programme centre"'), [])

    def test_the_sent_surfaces_are_the_request_text(self):
        """Lifting the literals into constants must not change a byte of
        what is sent — pinned exactly, trailing newlines included, since
        these constants are now the only definition (#1151 round 2, S2)."""
        from data_sheets_schema import api_runner
        self.assertEqual(api_runner.PHASE_SYSTEM,
                         "You generate Datasheets-for-Datasets records. The declared input bundle is your "
                         "only source of dataset facts. The schema digest defines structure, never content. "
                         "Never consult a previously generated D4D record.")
        self.assertEqual(api_runner.CHUNK_MARKER_NOTE,
                         "# Chunk markers: a line of the form [cNNN] opens each chunk; the markers are not "
                         "part of the bundle's text.\n\n")
        self.assertEqual(api_runner.READDRESS_HEADER, "# Receipt entries whose slot is not a path in the record above\n\n")
        self.assertEqual(api_runner.REGATE_HEADERS, ("# Reconciliation report as written\n\n",
                                                     "# Claims the records do not show\n\n"))
        self.assertEqual(api_runner.REPAIR_HEADERS, ("# Record that failed validation\n\n", "# Validator findings\n\n"))
        self.assertEqual(api_runner.CARRY_LABEL.format(name="Audit findings"), "# Audit findings\n\n")
        self.assertEqual(api_runner.BUNDLE_HEAD.format(bundle="b.txt") + "\n", "# Declared input bundle — b.txt\n\n")
        self.assertEqual(api_runner.BUNDLE_MD5_LINE.format(md5="x"), "# bundle_md5: x\n")


class TestItDidNotRedefineACondition(unittest.TestCase):
    """The reason it is in the playbook rather than the prompts."""

    #: The conditions created *with* the rule, so they re-baseline nothing:
    #: v5 introduced it and every later version inherits v5's block.
    NEW_CONDITIONS = ("d4d_generic_arm_prompt_v5.md", "d4d_generic_arm_prompt_v6.md",
                      "d4d_generic_arm_prompt_v7.md", "d4d_generic_arm_prompt_v8.md",
                      "d4d_generic_arm_prompt_v9.md")
    #: Listed by hand, not globbed: the guard is that a *human* declares each
    #: new condition as one born with the rule. A derived list would pass for
    #: any prompt that acquired it, which is the thing being forbidden.

    def test_no_existing_condition_prompt_acquired_the_rule(self):
        """#502's actual constraint, which v5 does not breach.

        The rule went into the playbook rather than the prompts because adding
        it to a prompt that had already been run would change what that
        condition means for every record naming it, and require a pin rotation
        mid-arm. That is still forbidden, and it is about *existing* conditions.

        v5 carries the rule from birth (#545). No record names generic_v5 yet,
        so nothing is re-baselined — which is exactly why a version boundary is
        where a playbook-only rule is allowed to move.
        """
        for path in sorted(PROMPTS.glob("d4d_*_arm_prompt*.md")):
            if path.name in self.NEW_CONDITIONS:
                continue
            with self.subTest(prompt=path.name):
                self.assertNotIn("American English",
                                 path.read_text(encoding="utf-8"))

    def test_the_new_condition_does_carry_it(self):
        """Otherwise the exemption above is an unguarded hole rather than a
        statement about one file."""
        for name in self.NEW_CONDITIONS:
            with self.subTest(prompt=name):
                self.assertIn("American English", (PROMPTS / name).read_text(encoding="utf-8"))
        text = (PROMPTS / self.NEW_CONDITIONS[0]).read_text(encoding="utf-8")
        self.assertIn("American English", text)

    def test_no_record_yet_names_the_new_condition(self):
        """The premise of the exemption, asserted rather than assumed.

        The moment a run is generated under generic_v5, this test should be
        deleted — not because the rule changed, but because from then on the
        prompt may not be edited at all, which is a stronger guarantee than
        this one and is enforced by the pin.
        """
        import yaml
        from data_sheets_schema.provenance import CONCAT_DIR
        named = []
        for rec in CONCAT_DIR.glob("*_core/*/*_provenance.yaml"):
            data = yaml.safe_load(rec.read_text(encoding="utf-8")) or {}
            if "generic_v5" in str(data.get("condition") or ""):
                named.append(rec.parts[-2])
        self.assertEqual(named, [])

    def test_every_pinned_prompt_is_still_at_its_pin(self):
        import subprocess
        result = subprocess.run(
            ["poetry", "run", "d4d", "api", "prompts", "check", "--strict"],
            capture_output=True, text=True, check=False, cwd=ROOT)
        self.assertEqual(result.returncode, 0,
                         (result.stdout + result.stderr)[-600:])

    def test_the_canonical_arm_is_not_uncanonical(self):
        """The property that would have been lost by editing v1 *for this rule*.

        The arm reads `superseded` since #515 deliberately rotated the pins
        ahead of a re-baselining. That is the state this test was written to
        avoid reaching *accidentally* — and reaching it by decision, with the
        rotation recorded and the previous hash retained, is a different thing.
        `uncanonical` remains the failure: it would mean the text was never a
        published version of its condition.
        """
        from data_sheets_schema.runs import (canonical_prompt_status,
                                             canonical_runs)
        from data_sheets_schema.runs import canonical_sets
        runs = {(rt, p): i for rt, found in canonical_sets().items() for p, i in found.items()}
        if not runs:
            self.skipTest("no canonical records on disk")
        for (_rt, project), info in runs.items():
            with self.subTest(project=project):
                status, why = canonical_prompt_status(
                    info["method"], info["label"], project)
                self.assertIn(status, ("canonical", "superseded"), why)
