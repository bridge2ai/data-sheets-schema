"""The render gate: does a record's instruction match what its spec produces?

Rendering the instruction (#425) made hand-editing avoidable. This makes it
detectable, which is the difference between a convention and a control — and
the intervention it catches is the real one: a `CRITICAL SCOPE BOUNDARY`
paragraph appended to a VOICE launch prompt, naming the project, the pediatric
dataset and issue #292, while the provenance recorded the base file and the
header said "identical for all projects" (#419, #422).
"""

import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.api_runner import RunSpec
from data_sheets_schema.runs import verify_request

BUNDLE = Path("data/preprocessed/concatenated/VOICE_preprocessed.txt")


@unittest.skipUnless(BUNDLE.exists(), "bundles not present")
class TestTheGate(unittest.TestCase):
    LABEL, METHOD, PROJECT = "2026-08-10_gate_rep1", "claudecode_agent", "VOICE"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.concat = Path(self.tmp.name) / "data/d4d_concatenated"
        (self.concat / f"{self.METHOD}_core" / self.LABEL).mkdir(parents=True)
        self.spec = RunSpec(
            project=self.PROJECT, arm="BASELINE (input documents only)",
            method=self.METHOD, bundle=BUNDLE, label=self.LABEL,
            condition="generic_v3", runtime="Claude Code", provider="Anthropic")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, prompts):
        (self.concat / f"{self.METHOD}_core" / self.LABEL
         / f"{self.PROJECT}_provenance.yaml").write_text(
            yaml.safe_dump({"prompts": prompts}, sort_keys=False))

    PROMPT = Path("src/download/prompts/d4d_generic_arm_prompt_v3.md")

    def _request(self, text, spec=True, pin=True):
        from data_sheets_schema.provenance import _sha256
        r = {"sha256": hashlib.sha256(text.encode()).hexdigest(),
             "bytes": len(text.encode())}
        if spec:
            r["spec"] = self.spec.render_spec()
        files = ([{"path": str(self.PROMPT), "sha256": _sha256(self.PROMPT)}]
                 if pin else [])
        return {"files": files, "request": r}

    def _verify(self):
        return verify_request(self.METHOD, self.LABEL, self.PROJECT, self.concat)

    def test_an_unedited_rendered_instruction_matches(self):
        self._write(self._request(self.spec.instruction))
        self.assertEqual("match", self._verify()[0])

    def test_the_scope_paragraph_that_started_this_is_caught(self):
        tampered = self.spec.instruction + (
            "\n\nCRITICAL SCOPE BOUNDARY: this run covers the adult dataset "
            "ONLY. VOICE_PEDIATRIC is a separate project (#292).\n")
        self._write(self._request(tampered))
        status, why = self._verify()
        self.assertEqual("mismatch", status)
        self.assertIn("not the one this spec produces", why)

    def test_even_one_character_is_caught(self):
        self._write(self._request(self.spec.instruction + " "))
        self.assertEqual("mismatch", self._verify()[0])

    def test_a_hash_without_a_spec_is_unverifiable_not_a_mismatch(self):
        """The two say different things. "Cannot check" must not be reported as
        "checked and wrong"."""
        self._write(self._request(self.spec.instruction, spec=False))
        status, why = self._verify()
        self.assertEqual("unverifiable", status)
        self.assertIn("without the spec", why)

    def test_no_request_hash_is_absent_not_a_mismatch(self):
        """Every record written before #425. Failing history for a field that
        postdates it is the error the live-provenance cutoff exists to avoid."""
        self._write({"files": []})
        self.assertEqual("absent", self._verify()[0])

    def test_a_missing_record_is_absent(self):
        self.assertEqual("absent", verify_request(
            self.METHOD, "2099-01-01_nope_rep1", self.PROJECT, self.concat)[0])

    def test_an_unrenderable_spec_is_unverifiable_not_a_crash(self):
        p = self._request(self.spec.instruction)
        p["request"]["spec"] = dict(p["request"]["spec"], condition="no-such")
        self._write(p)
        self.assertEqual("unverifiable", self._verify()[0])

    def test_a_changed_condition_in_the_spec_changes_the_verdict(self):
        """The spec is what the claim is checked against, so editing it is the
        one way to make a tampered instruction pass — and it changes the
        condition the record asserts, which the label check then catches."""
        p = self._request(self.spec.instruction)
        p["request"]["spec"] = dict(p["request"]["spec"], condition="generic")
        self._write(p)
        self.assertEqual("mismatch", self._verify()[0])


class TestAChangedPromptFileIsNotATamperedInstruction(unittest.TestCase):
    """Raised reviewing the gate. A differing hash has two causes and they are
    not the same finding.

    The instruction may have been edited, or the prompt file may have moved
    since the run so that re-rendering no longer reproduces what was sent. The
    second is ordinary evolution — v4 exists, v5 will — and reporting it as
    `mismatch` would make `--strict` fail every historical record the first time
    anyone edited a prompt.
    """

    LABEL, METHOD, PROJECT = "2026-08-10_drift_rep1", "claudecode_agent", "VOICE"
    PROMPT = Path("src/download/prompts/d4d_generic_arm_prompt_v3.md")

    def setUp(self):
        if not (BUNDLE.exists() and self.PROMPT.exists()):
            self.skipTest("corpus not present")
        self.tmp = tempfile.TemporaryDirectory()
        self.concat = Path(self.tmp.name) / "data/d4d_concatenated"
        (self.concat / f"{self.METHOD}_core" / self.LABEL).mkdir(parents=True)
        self.spec = RunSpec(
            project=self.PROJECT, arm="BASELINE (input documents only)",
            method=self.METHOD, bundle=BUNDLE, label=self.LABEL,
            condition="generic_v3", runtime="Claude Code", provider="Anthropic")
        self.backup = self.PROMPT.read_bytes()

    def tearDown(self):
        self.PROMPT.write_bytes(self.backup)
        self.tmp.cleanup()

    def _write(self, text, pin=True):
        from data_sheets_schema.provenance import _sha256
        files = ([{"path": str(self.PROMPT), "sha256": _sha256(self.PROMPT)}]
                 if pin else [])
        (self.concat / f"{self.METHOD}_core" / self.LABEL
         / f"{self.PROJECT}_provenance.yaml").write_text(yaml.safe_dump(
            {"prompts": {"files": files, "request": {
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "bytes": len(text.encode()),
                "spec": self.spec.render_spec()}}}, sort_keys=False))

    def _verify(self):
        return verify_request(self.METHOD, self.LABEL, self.PROJECT, self.concat)

    def test_an_edited_instruction_is_still_a_mismatch(self):
        """The discrimination must not be bought by weakening the real case."""
        self._write(self.spec.instruction + "\nEDITED\n")
        self.assertEqual("mismatch", self._verify()[0])

    def test_a_changed_prompt_file_is_unverifiable_not_a_mismatch(self):
        self._write(self.spec.instruction)
        self.PROMPT.write_bytes(self.backup + b"\n- a rule added later\n")
        status, why = self._verify()
        self.assertEqual("unverifiable", status)
        self.assertIn("prompt file has changed", why)

    def test_without_a_pinned_file_it_will_not_guess(self):
        """If the record does not pin the prompt, an edited instruction cannot
        be told from a changed one — say so rather than pick."""
        self._write(self.spec.instruction + "\nEDITED\n", pin=False)
        status, why = self._verify()
        self.assertEqual("unverifiable", status)
        self.assertIn("does not pin the prompt file", why)

    def test_the_mismatch_message_says_the_file_was_unchanged(self):
        """So a reader knows the verdict rests on having ruled drift out."""
        self._write(self.spec.instruction + "\nEDITED\n")
        self.assertIn("unchanged prompt file", self._verify()[1])


if __name__ == "__main__":
    unittest.main()
