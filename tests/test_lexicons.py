"""Registered lexicons are pinned by their bytes and changed only by a new version (#2919).

The registry pins each file's sha256 and `load` refuses a file whose bytes are
not its pin. That alone would let an edit through: change the file and the
registry's sha together and every check passes while counts made under "v1"
now describe other patterns. So the pins are held here as well, append-only.
A changed v1 pin in this file is the edit a reviewer must refuse; a new
version is a new line.
"""
import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import lexicon as lx

#: Append-only. Never change a line: a registered lexicon's bytes are fixed,
#: and a change is a new version with a new line here.
REGISTERED = {
    ("absence_self_narration", 1): "7b5c2237df5a0c2fa71446f472abb8aefc7458ea5c9d9f15228f172b5325ef1e",
}

MINIMAL = """name: tiny
version: 1
instrument: tiny lexicon v1
flags: [IGNORECASE]
classes:
  a: the a class
patterns:
  - id: a.word
    class: a
    regex: '\\bword\\b'
    examples: [one word here]
    counterexamples: [wordy]
"""


def _registry_text(entries):
    return yaml.safe_dump({"lexicons": entries}, sort_keys=False)


class TheRegistry(unittest.TestCase):
    def test_every_registered_lexicon_checks_clean(self):
        """Pins match bytes, file names carry the version, every pattern
        matches its examples and none of its counterexamples, and no lexicon
        file sits in the directory unregistered."""
        self.assertEqual(lx.check_registry(), [])

    def test_the_registry_pins_are_the_append_only_pins(self):
        pinned = {(name, e["version"]): e["sha256"]
                  for name, versions in lx.registered().items() for e in versions}
        self.assertEqual(pinned, REGISTERED,
                         "a registered lexicon's pin changed or a version disappeared: "
                         "register a new version instead of editing a registered one")

    def test_the_pin_is_the_sha256_of_the_file_bytes(self):
        for (name, version), sha in REGISTERED.items():
            with self.subTest(name=name, version=version):
                raw = (lx.LEXICON_DIR / f"{name}_v{version}.yaml").read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), sha)
                self.assertEqual(lx.load(name, version).sha256, sha)

    def test_every_result_identity_names_the_bytes(self):
        lexicon = lx.load("absence_self_narration")
        self.assertEqual(lexicon.identity(), {
            "name": "absence_self_narration", "version": 1,
            "instrument": "absence_self_narration lexicon v1 (#2919)",
            "file": "absence_self_narration_v1.yaml", "sha256": REGISTERED[("absence_self_narration", 1)]})


class Pinning(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        self.raw = MINIMAL.encode()
        (self.dir / "tiny_v1.yaml").write_bytes(self.raw)
        self._register([{"version": 1, "file": "tiny_v1.yaml", "sha256": hashlib.sha256(self.raw).hexdigest()}])

    def _register(self, versions):
        (self.dir / lx.REGISTRY_FILE).write_text(_registry_text({"tiny": versions}), encoding="utf-8")

    def test_a_registered_file_loads(self):
        lexicon = lx.load("tiny", directory=self.dir)
        self.assertEqual((lexicon.version, lexicon.sha256), (1, hashlib.sha256(self.raw).hexdigest()))
        self.assertEqual(lx.check_registry(self.dir), [])

    def test_an_edited_registered_file_is_refused(self):
        """A comment is part of the bytes: any edit, however small, is refused."""
        (self.dir / "tiny_v1.yaml").write_bytes(self.raw + b"# a comment\n")
        with self.assertRaisesRegex(lx.LexiconError, "never edited — add tiny_v2.yaml"):
            lx.load("tiny", directory=self.dir)
        self.assertTrue(any("not the registered" in p for p in lx.check_registry(self.dir)))

    def test_a_new_version_is_the_route_and_the_old_bytes_stay_loadable(self):
        raw2 = MINIMAL.replace("version: 1", "version: 2").replace("v1", "v2").encode()
        (self.dir / "tiny_v2.yaml").write_bytes(raw2)
        self._register([{"version": 1, "file": "tiny_v1.yaml", "sha256": hashlib.sha256(self.raw).hexdigest()},
                        {"version": 2, "file": "tiny_v2.yaml", "sha256": hashlib.sha256(raw2).hexdigest()}])
        self.assertEqual(lx.load("tiny", directory=self.dir).version, 2)          # newest by default
        self.assertEqual(lx.load("tiny", 1, directory=self.dir).sha256, hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(lx.check_registry(self.dir), [])

    def test_a_file_declaring_another_version_than_its_entry_is_refused(self):
        raw = MINIMAL.replace("version: 1", "version: 3").encode()
        (self.dir / "tiny_v1.yaml").write_bytes(raw)
        self._register([{"version": 1, "file": "tiny_v1.yaml", "sha256": hashlib.sha256(raw).hexdigest()}])
        with self.assertRaisesRegex(lx.LexiconError, "declares tiny v3"):
            lx.load("tiny", directory=self.dir)

    def test_a_file_name_without_its_version_is_reported(self):
        shutil.move(self.dir / "tiny_v1.yaml", self.dir / "tiny.yaml")
        self._register([{"version": 1, "file": "tiny.yaml", "sha256": hashlib.sha256(self.raw).hexdigest()}])
        self.assertTrue(any("is not tiny_v1.yaml" in p for p in lx.check_registry(self.dir)))

    def test_an_unregistered_lexicon_file_is_reported(self):
        (self.dir / "stray_v1.yaml").write_bytes(self.raw)
        self.assertEqual(lx.check_registry(self.dir), ["stray_v1.yaml is in " + str(self.dir) + " but not registered"])

    def test_a_pattern_that_misses_its_example_or_matches_its_counterexample_is_reported(self):
        raw = MINIMAL.replace("[one word here]", "[no match]").replace("[wordy]", "[a word]").encode()
        (self.dir / "tiny_v1.yaml").write_bytes(raw)
        self._register([{"version": 1, "file": "tiny_v1.yaml", "sha256": hashlib.sha256(raw).hexdigest()}])
        problems = lx.check_registry(self.dir)
        self.assertTrue(any("does not match its example 'no match'" in p for p in problems), problems)
        self.assertTrue(any("matches its counterexample 'a word'" in p for p in problems), problems)

    def test_an_unregistered_name_or_version_is_refused(self):
        with self.assertRaisesRegex(lx.LexiconError, "no lexicon 'other'"):
            lx.load("other", directory=self.dir)
        with self.assertRaisesRegex(lx.LexiconError, "no registered version 7"):
            lx.load("tiny", 7, directory=self.dir)


class Shape(unittest.TestCase):
    def _refused(self, text, message):
        with self.assertRaisesRegex(lx.LexiconError, message):
            lx.parse(text.encode(), file="t.yaml")

    def test_a_pattern_naming_an_undeclared_class_is_refused(self):
        self._refused(MINIMAL.replace("class: a\n", "class: b\n"), "undeclared class 'b'")

    def test_a_declared_class_with_no_pattern_is_refused(self):
        self._refused(MINIMAL.replace("  a: the a class\n", "  a: the a class\n  b: unused\n"),
                      r"classes with no pattern: \['b'\]")

    def test_a_pattern_id_used_twice_is_refused(self):
        dup = MINIMAL + "  - id: a.word\n    class: a\n    regex: 'x'\n"
        self._refused(dup, "used twice")

    def test_an_unknown_flag_or_key_is_refused(self):
        self._refused(MINIMAL.replace("[IGNORECASE]", "[VERBOSE]"), "unknown flag 'VERBOSE'")
        self._refused(MINIMAL + "extra: 1\n", r"unknown keys \['extra'\]")

    def test_an_example_yaml_read_as_a_mapping_is_refused(self):
        """An unquoted example containing ': ' parses as a mapping, and a
        self-test that calls .split() on it would crash, not report."""
        self._refused(MINIMAL.replace("[one word here]", "\n      - Regulated: No"), "list of strings")

    def test_a_regex_that_does_not_compile_is_refused(self):
        text = MINIMAL.replace("'\\bword\\b'", "'(unclosed'")
        self.assertNotEqual(text, MINIMAL)
        self._refused(text, "does not compile")


if __name__ == "__main__":
    unittest.main()
