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
    ("absence_self_narration", 2): "e5f35547ca9862c8dc7d5f8996e0e67712549591334b9f726003fd4b3c257708",
}

MINIMAL = """name: tiny
version: 1
instrument: tiny lexicon v1
counterexamples_required: true
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

    def test_which_v1_patterns_carry_no_counterexample(self):
        """Every v1 pattern has an example; five have no counterexample, so
        for those the self-test shows what they match, not what they miss.
        v1's bytes are fixed, so this list can only shrink in a new version."""
        lexicon = lx.load("absence_self_narration", 1)
        self.assertEqual(len(lexicon.patterns), 18)
        self.assertTrue(all(p.examples for p in lexicon.patterns))
        self.assertEqual(sorted(p.id for p in lexicon.patterns if not p.counterexamples), [
            "bwa.bundle-does-not", "bwa.bundle-silent", "bwa.none-of-the-sources",
            "rsn.omitted-here", "rsn.source-ranking"])

    def test_the_v1_recorded_under_slot_counterexample_guards_only_the_verb(self):
        """What `rsn.recorded-under-slot`'s one counterexample does and does
        not guard (#3213).

        "The authors are listed in the kickoff_webinar." misses because
        `listed` is not one of the pattern's verbs, not because
        `kickoff_webinar` is not a slot: the regex cannot tell a slot name
        from any other snake_case word, so after one of its verbs every
        underscored token counts as a slot. The counterexample therefore
        guards only that `listed` stays out of the verb list. v1's bytes are
        pinned, so a counterexample that tests slot-shape discrimination (and
        a pattern able to pass it) waits for a new lexicon version. This test
        fails when the loaded pattern stops behaving as described here, so
        the account cannot outlive the bytes it describes."""
        pattern = {p.id: p for p in lx.load("absence_self_narration", 1).patterns}["rsn.recorded-under-slot"]

        def hits(text):
            return bool(pattern.regex.search(text))

        self.assertEqual(pattern.counterexamples, ("The authors are listed in the kickoff_webinar.",))
        # The miss is the verb: a real slot after `listed` misses too ...
        self.assertFalse(hits("The authors are listed in the kickoff_webinar."))
        self.assertFalse(hits("The authors are listed in the related_datasets."))
        # ... and a non-slot snake_case word after one of the pattern's verbs matches.
        self.assertTrue(hits("The authors are recorded in the kickoff_webinar."))
        self.assertTrue(hits("Consent was given in the consent_form."))

    def test_v2_gives_every_pattern_a_counterexample_and_declares_the_rule(self):
        """#3132: the five v1 patterns without one gain one, and the file
        declares the rule `parse` holds it to."""
        lexicon = lx.load("absence_self_narration", 2)
        self.assertTrue(lexicon.counterexamples_required)
        self.assertEqual([p.id for p in lexicon.patterns if not p.counterexamples], [])
        self.assertFalse(lx.load("absence_self_narration", 1).counterexamples_required)

    def test_v2_matches_exactly_what_v1_matches(self):
        """v2 changes self-test texts only: the same pattern ids, classes,
        regexes, flags, class descriptions and scope, so a count under either
        is the same count. A regex edit belongs in a version that says so."""
        v1, v2 = (lx.load("absence_self_narration", v) for v in (1, 2))

        def compiled(lexicon):
            return [(p.id, p.cls, p.regex.pattern, p.regex.flags) for p in lexicon.patterns]

        self.assertEqual(compiled(v2), compiled(v1))
        self.assertEqual((v2.classes, v2.scope), (v1.classes, v1.scope))
        for a, b in zip(v1.patterns, v2.patterns):
            with self.subTest(pattern=a.id):
                self.assertEqual(b.examples, a.examples)
                if a.id != "rsn.recorded-under-slot":        # replaced in v2 (#3213)
                    self.assertEqual(b.counterexamples[:len(a.counterexamples)], a.counterexamples)

    def test_the_v2_recorded_under_slot_counterexamples_each_miss_for_their_stated_reason(self):
        """#3213: each counterexample misses for the one reason its comment
        names, shown by changing only that part and watching it match. The
        pattern cannot tell a slot from another snake_case word (#3224), so
        no counterexample claims to guard that."""
        pattern = {p.id: p for p in lx.load("absence_self_narration", 2).patterns}["rsn.recorded-under-slot"]
        verb_guard, shape_guard = pattern.counterexamples
        self.assertEqual(verb_guard, "The authors are listed in related_datasets.")
        self.assertEqual(shape_guard, "The approval was recorded in the minutes.")
        self.assertFalse(pattern.regex.search(verb_guard))
        self.assertTrue(pattern.regex.search(verb_guard.replace("listed", "recorded")))       # the verb decides
        self.assertFalse(pattern.regex.search(shape_guard))
        self.assertTrue(pattern.regex.search(shape_guard.replace("the minutes", "the meeting_minutes")))  # the shape
        self.assertTrue(pattern.regex.search(shape_guard.replace("the minutes", "`minutes`")))
        self.assertTrue(pattern.regex.search("Consent was given in the consent_form."))       # #3224, unchanged

    def test_every_result_identity_names_the_bytes(self):
        """The newest registered version by default, and the one named."""
        for version, want in [(None, 2), (1, 1), (2, 2)]:
            with self.subTest(version=version):
                lexicon = lx.load("absence_self_narration", version)
                self.assertEqual(lexicon.identity(), {
                    "name": "absence_self_narration", "version": want,
                    "instrument": f"absence_self_narration lexicon v{want} (#{2919 if want == 1 else 3132})",
                    "file": f"absence_self_narration_v{want}.yaml",
                    "sha256": REGISTERED[("absence_self_narration", want)]})


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

    def test_a_pattern_with_no_example_cannot_be_registered(self):
        """The review's case (#3093): a pattern matching every string, with no
        example and no counterexample, passed `check_registry`, which then
        attested nothing about it. It is now refused at load and reported."""
        raw = (b"name: tiny\nversion: 1\ninstrument: tiny lexicon v1\nclasses:\n  a: the a class\n"
               b"patterns:\n  - {id: a.any, class: a, regex: '.'}\n")
        (self.dir / "tiny_v1.yaml").write_bytes(raw)
        self._register([{"version": 1, "file": "tiny_v1.yaml", "sha256": hashlib.sha256(raw).hexdigest()}])
        with self.assertRaisesRegex(lx.LexiconError, "'a.any' lists no examples"):
            lx.load("tiny", directory=self.dir)
        problems = lx.check_registry(self.dir)
        self.assertTrue(any("'a.any' lists no examples" in p for p in problems), problems)

    def test_a_registered_lexicon_without_the_declaration_is_reported(self):
        """#3132: every lexicon registered after absence_self_narration v1
        declares `counterexamples_required`; one that does not is reported
        even when each of its patterns happens to carry a counterexample."""
        raw = self.raw.replace(b"counterexamples_required: true\n", b"")
        self.assertNotEqual(raw, self.raw)
        (self.dir / "tiny_v1.yaml").write_bytes(raw)
        self._register([{"version": 1, "file": "tiny_v1.yaml", "sha256": hashlib.sha256(raw).hexdigest()}])
        self.assertEqual(lx.check_registry(self.dir), [
            "tiny v1: does not declare `counterexamples_required: true`; every lexicon registered after "
            "absence_self_narration v1 must (#3132)"])
        self.assertEqual(lx.load("tiny", directory=self.dir).version, 1)     # reported, still loadable

    def test_the_exemption_is_v1_of_the_absence_lexicon_alone(self):
        self.assertEqual(lx.COUNTEREXAMPLES_OPTIONAL, frozenset({("absence_self_narration", 1)}))

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

    def test_a_pattern_without_an_example_or_with_a_blank_one_is_refused(self):
        """Without an example the self-test cannot fail for a pattern (#3093)."""
        for old, new, message in [
            ("    examples: [one word here]\n", "", "'a.word' lists no examples"),
            ("[one word here]", "[]", "'a.word' lists no examples"),
            ("[one word here]", "['one word here', '  ']", "blank entry in examples"),
            ("[wordy]", "['']", "blank entry in counterexamples"),
        ]:
            with self.subTest(new=new):
                text = MINIMAL.replace(old, new)
                self.assertNotEqual(text, MINIMAL)
                self._refused(text, message)

    def test_a_declared_lexicon_needs_a_counterexample_for_every_pattern(self):
        """#3132: with `counterexamples_required: true`, a pattern without a
        counterexample is refused; without the declaration it parses."""
        text = MINIMAL.replace("    counterexamples: [wordy]\n", "")
        self.assertNotEqual(text, MINIMAL)
        self._refused(text, "'a.word' lists no counterexamples, and this lexicon declares counterexamples_required")
        empty = MINIMAL.replace("[wordy]", "[]")                 # the key present, its list empty
        self.assertNotEqual(empty, MINIMAL)
        self._refused(empty, "'a.word' lists no counterexamples, and this lexicon declares counterexamples_required")
        undeclared = text.replace("counterexamples_required: true\n", "")
        self.assertNotEqual(undeclared, text)
        self.assertEqual(lx.parse(undeclared.encode(), file="t.yaml").patterns[0].counterexamples, ())
        self.assertFalse(lx.parse(undeclared.encode(), file="t.yaml").counterexamples_required)

    def test_the_declaration_must_be_a_boolean(self):
        for value in ("yes-please", "1", "null", "[true]"):
            with self.subTest(value=value):
                self._refused(MINIMAL.replace("counterexamples_required: true", f"counterexamples_required: {value}"),
                              "counterexamples_required must be true or false")


if __name__ == "__main__":
    unittest.main()
