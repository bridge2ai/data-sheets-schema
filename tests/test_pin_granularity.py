"""A rationale edit and an instruction edit must not cost the same (#560).

The pin hashed the whole prompt file, including the rationale sections that
`prompt_body` never sends to the model. Correcting a sentence of documentation
therefore failed `check --strict` exactly as changing a decision rule does, and
resolving it rotated the pin — leaving a history that reads as a condition
re-baselined when the instruction had not moved by a byte.

The predictable consequence is the one the rule was written against: rationale
errors go uncorrected during an arm, because correcting them looks like
tampering.
"""

import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import prompt_registry as pr

PROMPT = """# A condition

## Why it exists

Rationale the model never sees.

## Prompt body

Do the thing.
"""


class BodyHashTest(unittest.TestCase):

    def test_only_the_body_is_hashed(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.md"
            b = Path(d) / "b.md"
            a.write_text(PROMPT, encoding="utf-8")
            b.write_text(PROMPT.replace("Rationale the model never sees.",
                                        "Different rationale entirely."),
                         encoding="utf-8")
            self.assertNotEqual(pr.sha256_of(a), pr.sha256_of(b))
            self.assertEqual(pr.body_sha256_of(a), pr.body_sha256_of(b))

    def test_a_body_change_changes_the_body_hash(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / "a.md"
            b = Path(d) / "b.md"
            a.write_text(PROMPT, encoding="utf-8")
            b.write_text(PROMPT.replace("Do the thing.", "Do another thing."),
                         encoding="utf-8")
            self.assertNotEqual(pr.body_sha256_of(a), pr.body_sha256_of(b))

    def test_a_file_with_no_body_section_has_no_body_hash(self):
        """Component files and the tuned block send every byte, so for them the
        whole-file hash is the only correct check."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.md"
            p.write_text("# just a component\n\nSome text.\n", encoding="utf-8")
            self.assertIsNone(pr.body_sha256_of(p))


class StatusTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.prompt = self.root / "p.md"
        self.prompt.write_text(PROMPT, encoding="utf-8")
        self.registry = self.root / "hashes.yaml"
        self.registry.write_text(yaml.safe_dump({
            "hash_algorithm": "sha256",
            "files": {pr.normalise(self.prompt): {
                "sha256": pr.sha256_of(self.prompt),
                "body_sha256": pr.body_sha256_of(self.prompt),
                "pinned_on": "2026-01-01", "reason": "test"}}}),
            encoding="utf-8")
        pr._REGISTRY_CACHE.clear()
        self.addCleanup(pr._REGISTRY_CACHE.clear)

    def test_untouched_is_canonical(self):
        self.assertEqual(pr.disk_status(self.prompt, self.registry)[0],
                         pr.CANONICAL)

    def test_a_rationale_edit_is_annotated(self):
        self.prompt.write_text(
            PROMPT.replace("Rationale the model never sees.", "Corrected."),
            encoding="utf-8")
        status, why = pr.disk_status(self.prompt, self.registry)
        self.assertEqual(status, pr.ANNOTATED)
        self.assertIn("the model is never sent", why)

    def test_a_body_edit_is_uncanonical(self):
        self.prompt.write_text(PROMPT.replace("Do the thing.", "Do otherwise."),
                               encoding="utf-8")
        self.assertEqual(pr.disk_status(self.prompt, self.registry)[0],
                         pr.UNCANONICAL)

    def test_a_pin_with_no_body_hash_still_fails_closed(self):
        """A pin taken before #560 cannot tell rationale from instruction.

        Guessing would turn an unchecked file into a passing one, so those keep
        the old whole-file behaviour.
        """
        data = yaml.safe_load(self.registry.read_text(encoding="utf-8"))
        del data["files"][pr.normalise(self.prompt)]["body_sha256"]
        self.registry.write_text(yaml.safe_dump(data), encoding="utf-8")
        pr._REGISTRY_CACHE.clear()
        self.prompt.write_text(
            PROMPT.replace("Rationale the model never sees.", "Corrected."),
            encoding="utf-8")
        self.assertEqual(pr.disk_status(self.prompt, self.registry)[0],
                         pr.UNCANONICAL)


class RealRegistryTest(unittest.TestCase):

    def test_every_condition_prompt_now_carries_a_body_hash(self):
        """Without this the feature is inert for the files it was built for."""
        missing = []
        for path, entry in pr.pins().items():
            p = Path(path)
            if pr.body_sha256_of(p) and not entry.get("body_sha256"):
                missing.append(path)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()


class RecordGateIsNotSoftenedTest(unittest.TestCase):
    """The body check belongs to the disk gate alone.

    `status_of_hash` judges a hash a *record* wrote, for bytes that need not
    exist any more. Those bytes cannot be decomposed into body and rationale,
    so comparing today's on-disk body against the pin would let a record whose
    prompt hash matches nothing pass as `annotated` merely because an unrelated
    file on disk happens to agree.

    The first version of #560 did exactly that, and
    `test_a_hash_that_was_never_pinned_is_the_finding` caught it.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.prompt = root / "p.md"
        self.prompt.write_text(PROMPT, encoding="utf-8")
        self.registry = root / "hashes.yaml"
        self.registry.write_text(yaml.safe_dump({
            "hash_algorithm": "sha256",
            "files": {pr.normalise(self.prompt): {
                "sha256": pr.sha256_of(self.prompt),
                "body_sha256": pr.body_sha256_of(self.prompt),
                "pinned_on": "2026-01-01", "reason": "test"}}}),
            encoding="utf-8")
        pr._REGISTRY_CACHE.clear()
        self.addCleanup(pr._REGISTRY_CACHE.clear)

    def test_an_unknown_recorded_hash_stays_uncanonical(self):
        import hashlib
        stranger = hashlib.sha256(b"bytes nobody pinned").hexdigest()
        status, _ = pr.status_of_hash(self.prompt, stranger, self.registry)
        self.assertEqual(status, pr.UNCANONICAL,
                         "a record gate must not be softened by what happens "
                         "to be on disk today")
