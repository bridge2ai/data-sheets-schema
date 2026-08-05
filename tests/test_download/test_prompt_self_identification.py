"""Each condition's prompt must stamp its own file, not the one it was copied from (#337).

`d4d_generic_arm_prompt_v3.md` was created by copying v2, and its HEADER BLOCK
came with it:

    # Mode: four-phase project agent, generic-v2 prompt
    # Prompt: src/download/prompts/d4d_generic_arm_prompt_v2.md

Byte-identical to what the 2026-07-31 generic-v2 records already carry. Every
record the v3 arm produced would have claimed to be a v2 record, and
`api_runner` does not repair it — its only header rewrite is
`"generic prompt"` → `"tuned prompt"`.

That is not cosmetic. The comparison v3 exists to make is v2 against v3, the
header is the human-readable provenance, and it is what a reader checks first —
the paired agent/API comparison in `notes/enumeration_depth_2026-08-04.md` was
established from exactly these two lines. A v3 corpus stamped v2 makes that check
return the wrong answer.

The condition metadata was right all along (`CONDITION_AXES['generic_v3']` is
`{'base': 'v3', 'tuned': False}`), so nothing but the header was wrong. The
header is the part a person reads.

Copy-paste is how the next `vN` would inherit it too, so this checks every
condition rather than v3 alone.
"""

import re
import unittest

from data_sheets_schema.api_runner import CONDITION_PROMPTS


class TestEachPromptNamesItself(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.bodies = {}
        for condition, path in CONDITION_PROMPTS.items():
            text = path.read_text(encoding="utf-8")
            # Only the text after `## Prompt body` reaches the model; the
            # rationale above it legitimately discusses other versions.
            body = text.split("## Prompt body", 1)[-1]
            cls.bodies[condition] = (path, body)

    def test_the_prompt_line_names_the_file_it_is_in(self):
        """The defect exactly: v3's body pointed at v2's path."""
        for condition, (path, body) in self.bodies.items():
            stamped = re.findall(r"^\s*#\s*Prompt:\s*(\S+)", body, re.M)
            with self.subTest(condition=condition):
                self.assertTrue(stamped, f"{path.name} stamps no prompt path")
                for named in stamped:
                    self.assertTrue(
                        named.endswith(path.name),
                        f"{path.name} tells the model to stamp records with "
                        f"`{named}` — records would misattribute their own arm")

    def test_no_prompt_stamps_another_conditions_file(self):
        """The complement, and the sharper statement: a body naming *any* other
        condition's file is wrong even if it also names its own."""
        filenames = {p.name for p in CONDITION_PROMPTS.values()}
        for condition, (path, body) in self.bodies.items():
            others = filenames - {path.name}
            stamped = " ".join(re.findall(r"^\s*#\s*Prompt:.*", body, re.M))
            for other in sorted(others):
                with self.subTest(condition=condition, other=other):
                    self.assertNotIn(other, stamped)

    def test_the_mode_line_matches_the_prompt_line(self):
        """Both header lines name the version, and both were copied.

        `api_runner` rewrites `"generic prompt"` to `"tuned prompt"` for the
        tuned arm, so that one is expected to differ from its filename; every
        other condition must be self-consistent.
        """
        for condition, (path, body) in self.bodies.items():
            if condition == "tuned":
                continue
            modes = re.findall(r"^\s*#\s*Mode:.*?,\s*(\S+)\s+prompt", body, re.M)
            with self.subTest(condition=condition):
                self.assertTrue(modes, f"{path.name} stamps no mode")
                stem = path.stem.replace("d4d_", "").replace("_arm_prompt", "")
                # `d4d_generic_arm_prompt.md` -> `generic`; `..._v3.md` -> `generic_v3`
                expected = stem.replace("_", "-")
                for mode in modes:
                    self.assertEqual(mode, expected,
                                     f"{path.name} stamps mode `{mode}`")


class TestThePremise(unittest.TestCase):
    """Why the prompt body is the only place a generic version can be fixed.

    `resolve_prompt` *does* correct the header for the tuned arm — it rewrites
    both the Mode and the Prompt lines, because `tuned` deliberately shares
    v1's file and adds a project block. That is why `tuned` is skipped above.

    It performs no equivalent rewrite for the generic versions, so whatever
    `d4d_generic_arm_prompt_v3.md` says about itself is what the corpus gets.
    Asserted by running the resolver rather than reading its source, so a
    rewrite added later makes these tests fail loudly rather than sit stale.
    """

    def _resolve(self, condition):
        from pathlib import Path

        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        spec = RunSpec(project="CHORUS", arm="BASELINE",
                       method="claudecode_agent",
                       bundle=Path("data/preprocessed/concatenated/"
                                   "CHORUS_preprocessed.txt"),
                       label="2026-08-05_test", condition=condition)
        return resolve_prompt(spec)

    def test_the_tuned_arm_has_its_header_corrected_by_the_runner(self):
        body = self._resolve("tuned")
        self.assertIn("tuned prompt", body)
        self.assertIn("d4d_tuned_arm_prompt.md", body)

    def test_a_generic_version_gets_no_such_correction(self):
        """So the body's own stamp is load-bearing (#337)."""
        body = self._resolve("generic_v3")
        self.assertIn("d4d_generic_arm_prompt_v3.md", body)
        self.assertNotIn("d4d_generic_arm_prompt_v2.md", body)
        self.assertIn("generic-v3 prompt", body)


if __name__ == "__main__":
    unittest.main()
