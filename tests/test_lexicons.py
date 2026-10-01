"""Registered lexicons are pinned by their bytes and changed only by a new version (#2919).

The registry pins each file's sha256 and `load` refuses a file whose bytes are
not its pin. That alone would let an edit through: change the file and the
registry's sha together and every check passes while counts made under "v1"
now describe other patterns. So the pins are held here as well, append-only.
A changed v1 pin in this file is the edit a reviewer must refuse; a new
version is a new line.
"""
import hashlib
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import lexicon as lx
from data_sheets_schema import self_disclaimed as sd

#: Append-only. Never change a line: a registered lexicon's bytes are fixed,
#: and a change is a new version with a new line here.
REGISTERED = {
    ("absence_self_narration", 1): "7b5c2237df5a0c2fa71446f472abb8aefc7458ea5c9d9f15228f172b5325ef1e",
    ("absence_self_narration", 2): "e5f35547ca9862c8dc7d5f8996e0e67712549591334b9f726003fd4b3c257708",
    ("absence_self_narration", 3): "f1657b94067ebb8fbdfd83bccdad1780b83d1b9e8dba245664b9fe54d41df7b6",
    ("absence_self_narration", 4): "8e2c25be9a6cb5374652a095f8f1749cd8e5ec82852f5394d0526fee5fb7bfec",
    ("absence_self_narration", 5): "d1134fd779a6940d0b214fcc514f0298b3712a97bb8877eb80c625c6d76bcab0",
}

#: v4's `rsn.source-ranking` gap between verb and term (#3791, #3792): any
#: character but a full stop, where an abbreviation's `.` before whitespace
#: is not one. Each `.` has exactly one alternative that can take it (#3894).
V4_GAP = (r"(?:[^.]|\.(?!\s)|(?<=\bSt)\.(?=\s)|(?<=\bDr)\.(?=\s)|(?<=\be\.g)\.(?=\s)|(?<=\bi\.e)\.(?=\s)"
          r"|(?<=\bU\.S)\.(?=\s))*?")
#: The gap as first written, whose abbreviation alternatives also took a `.`
#: that `\.(?!\s)` takes: the same language, matched in exponential time.
V4_GAP_OVERLAPPING = r"(?:[^.]|\.(?!\s)|(?<=\bSt)\.|(?<=\bDr)\.|(?<=\be\.g)\.|(?<=\bi\.e)\.|(?<=\bU\.S)\.)*?"
#: v1-v4's window in the three bundle-wide patterns that bound one, and
#: v5's (#3887): the same 80 characters ending at `;` and `:`, which now end
#: at a full stop only where V4_GAP's sentence ends.
BWA_GAP = r"[^.;:]{0,80}?"
V5_BWA_GAP = (r"(?:[^.;:]|\.(?!\s)|(?<=\bSt)\.(?=\s)|(?<=\bDr)\.(?=\s)|(?<=\be\.g)\.(?=\s)|(?<=\bi\.e)\.(?=\s)"
              r"|(?<=\bU\.S)\.(?=\s)){0,80}?")
V5_BWA_PATTERNS = ("bwa.not-by-any-source", "bwa.not-in-bundle", "bwa.not-in-the-sources")
#: v1-v4's names of the declared ranking, an alternative that needs no verb,
#: and v4's ranking terms; v5 makes the names terms (#3874, #3706).
NAMES = r"\b(?:source manifest|input manifest|source ranking|declared (?:source )?ranking)\b|"
V4_TERM = r"\b(?:tier[- ]?[0-9] sources?|(?:highest|lowest|higher|lower|equally)[- ]ranked|ranks? (?:higher|lower|highest|lowest))\b"
V5_TERM = (r"\b(?:source manifest|input manifest|source ranking|declared (?:source )?ranking|tier[- ]?[0-9] sources?"
           r"|(?:highest|lowest|higher|lower|equally)[- ]ranked|ranks? (?:higher|lower|highest|lowest))\b")
#: v4's `use` in the verb list, and v5's (#3875): not where the text marks a
#: noun, by a determiner, preposition or "data" before it or a noun or "of"
#: after it. `used` stays a verb of its own.
V4_USE = r"|use[sd]?|"
V5_USE = (r"|(?<!\bthe )(?<!\ba )(?<!\ban )(?<!\bits )(?<!\btheir )(?<!\bany )(?<!\bno )(?<!\bfor )(?<!\bof )"
          r"(?<!\bin )(?<!\bdata )uses?\b(?! (?:agreements?|of|cases?|limitations?|restrictions?|conditions?|terms"
          r"|polic(?:y|ies))\b)|used|")

#: Append-only, as REGISTERED: the container lexicons read by
#: `self_disclaimed` (#2913), pinned in container_lexicons/registry.yaml and
#: held here since #3040 (they were `LEXICON_PINS` in
#: tests/test_self_disclaimed.py, whose history follows). v1 was revised in
#: review before it first merged (#3029), so that PR's commits carry seven
#: earlier byte versions under `version: 1`:
#:   9b1f536ba02afc9971bbe9e28da316ea1c3c90e356bdbcc2c200400259521b04 (e00711d21, first commit)
#:   728e4e8b87aeefce7c2de27541392e53ee11cbf8d74fe7587309abf227a24a6d (387e20653, review round 1)
#:   14428534895e1cec840dde5eec6eb0d06bbeac50e89007573611d89c79d14c35 (cf3d16cb3, review round 2)
#:   56c9abda1c6fea3dcbd5b44372e2e85a5fc38d50c65bffdad4f8f3791f1b54e4 (df35537aa, review round 2)
#:   3b2949e29c7aebef79c6e77894d735c6fa2ce1a0ae8800463374d63fe45a5f3a (7e327b512, review round 3)
#:   626edd8708b519819c3be5f999e638cd18467b5ea857b1beb2fd2b854ab0f0a6 (5705a4f3f, review round 4)
#:   d1628c7e4b574b40c59113969747fc17b7155205668a1d48f28fbeb684994f4c (9607a6416, review round 5)
#: Every output names the sha it ran under, and no committed output, record
#: or note cites any of them (#3161). v2 (#3131, #3244, #3261, #3273) is a
#: new file beside v1, whose bytes are unchanged. v2 was revised in review
#: before it first merged, so its PR's commits carry eight earlier byte
#: versions under `version: 2`:
#:   6d232ed346308bd7cf97b262aff47cefb869673c55d72fb994411f2c2d34e09a (389436318, first commit)
#:   520e2779966f84a827ef0b6f9fdab3a6457cf85cce177a13291661453918dd7d (3a9d8198d, review round 1)
#:   aff86697da6e3713dc6925d851840d581eabf76a76aed100a909d32982468a73 (e3e1ca227, review round 2)
#:   15e9ed95b55fa9e60d8d557d6c4ae87cdc2bcf32b0ba7f09d676e842f713a4d9 (0d1ada61e, review round 3)
#:   63cc268b0d296ae3e2d35e4c0ae7a513f0adacf46a82a84529e60feb816901f9 (4cf8faa65, review round 4)
#:   2edac57763fddb717a237e3fe4d0444526f93fcbc5dfe286e5584ca676f3aa24 (348526f6e, review round 5)
#:   560b1c55b406ad9df6e5c03dfd35c9c020f9173f2fceaf11234679acb8b03757 (f59a0827d, review round 6)
#:   741e0834f79bc20e4a5aea65870380e8df23deefd6125b19b5d95bcefd2fe888 (bbd955fb9, review round 6)
CONTAINER_REGISTERED = {
    ("self_disclaimed", 1): "15a1b7ddfa9fa0677d1ab1075dfd2485b5920c32a59cf23d6108fb94b7afcb3a",
    ("self_disclaimed", 2): "e05cfaf00a62c042c120542b19317b286c6fa2c03223fe79d6566c6fe79834d4",
}

#: Every registered directory (#3040): its append-only pins and the check
#: that holds its files to them — `lexicon.check_pins` under each reader.
#: A new registry is a new row here, so its pins are held the same way.
REGISTRIES = {
    "lexicons": (lx.LEXICON_DIR, REGISTERED, lx.check_registry),
    "container_lexicons": (sd.LEXICON_DIR, CONTAINER_REGISTERED, sd.check_registry),
}

#: The v1 precision sample's three borderline phrases (#3520), in their
#: sentences: source conflicts worded with the ranking vocabulary.
RANKING_BORDERLINE = (
    'Within the same tier-1 source, the healthsheet answers "No" to whether the dataset identifies '
    "demographic sub-populations.",
    "Publisher: two tier-1 sources disagree.",
    "The project documentation, a higher-ranked source, gives a target of 10,000 voices.",
)

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


class EveryRegistry(unittest.TestCase):
    """One pin rule for every registered directory (#3040)."""

    def test_every_registry_checks_clean(self):
        for kind, (directory, _pins, check) in REGISTRIES.items():
            with self.subTest(registry=kind):
                self.assertEqual(check(directory), [])

    def test_every_registry_pins_are_the_append_only_pins(self):
        for kind, (directory, pins, _check) in REGISTRIES.items():
            with self.subTest(registry=kind):
                pinned = {(name, e["version"]): e["sha256"]
                          for name, versions in lx.registered(directory).items() for e in versions}
                self.assertEqual(pinned, pins,
                                 "a registered lexicon's pin changed or a version disappeared: "
                                 "register a new version instead of editing a registered one")

    def test_every_pin_is_the_sha256_of_the_file_bytes(self):
        for kind, (directory, pins, _check) in REGISTRIES.items():
            for (name, version), sha in pins.items():
                with self.subTest(registry=kind, name=name, version=version):
                    raw = (directory / f"{name}_v{version}.yaml").read_bytes()
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), sha)
                    self.assertEqual(lx.registered_bytes(name, version, directory=directory)[1], raw)

    def test_the_container_lexicons_load_through_their_pins(self):
        for (name, version), sha in CONTAINER_REGISTERED.items():
            with self.subTest(version=version):
                self.assertEqual(sd.load_registered(version, name=name).describe(), {
                    "path": f"{sd.LEXICON_RESOURCE_DIR}/{name}_v{version}.yaml", "version": version,
                    "sha256": sha})


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

    def test_v3_changes_only_the_source_ranking_pattern(self):
        """#3520: one regex and its self-test texts move; every other pattern,
        the flags, the class descriptions, the scope and the declaration are
        v2's, so a count under v3 differs from v2's in record_self_narration
        alone."""
        v2, v3 = (lx.load("absence_self_narration", v) for v in (2, 3))
        self.assertTrue(v3.counterexamples_required)
        self.assertEqual((v3.classes, v3.scope), (v2.classes, v2.scope))
        self.assertEqual([p.id for p in v3.patterns], [p.id for p in v2.patterns])
        for a, b in zip(v2.patterns, v3.patterns):
            with self.subTest(pattern=a.id):
                same = (a.cls, a.regex.pattern, a.regex.flags, a.examples, a.counterexamples)
                moved = (b.cls, b.regex.pattern, b.regex.flags, b.examples, b.counterexamples)
                if a.id == "rsn.source-ranking":
                    self.assertEqual(b.cls, a.cls)
                    self.assertEqual(b.regex.flags, a.regex.flags)
                    self.assertNotEqual(b.regex.pattern, a.regex.pattern)
                    self.assertEqual(b.examples[:len(a.examples)], a.examples)
                    self.assertEqual(b.counterexamples[:len(a.counterexamples)], a.counterexamples)
                else:
                    self.assertEqual(moved, same)

    def test_v3_source_ranking_misses_the_borderline_conflicts_v2_matched(self):
        """#3520: the three borderline phrases are v3 counterexamples, and v2
        matched each, so each is a change v3 makes rather than a text neither
        version matches."""
        v2, v3 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                  for v in (2, 3))
        for text in RANKING_BORDERLINE:
            with self.subTest(text=text):
                self.assertIn(text, v3.counterexamples)
                self.assertTrue(v2.regex.search(text))
                self.assertFalse(v3.regex.search(text))

    def test_v3_source_ranking_needs_a_verb_in_the_sentence_and_names_of_the_ranking_need_none(self):
        """The rule the pattern's comment states, shown by changing one part
        of a sentence at a time."""
        pattern = {p.id: p for p in lx.load("absence_self_narration", 3).patterns}["rsn.source-ranking"]

        def match(text):
            m = pattern.regex.search(text)
            return m.group() if m else None

        # A ranking term with no verb, then with one after it and before it.
        self.assertIsNone(match("Two tier-1 sources disagree on the date."))
        self.assertEqual(match("Two tier-1 sources disagree, so both dates are recorded."), "tier-1 sources")
        self.assertEqual(match("The date is preferred as the higher-ranked source."),
                         "preferred as the higher-ranked")
        # The verb must be in the same sentence: `;` and `. ` end it, a `.` inside a token does not.
        # The pattern has two branches — verb after the term (a lookahead) and verb before it (a
        # consuming span) — and each boundary is shown on both (#3759).
        self.assertIsNone(match("Two tier-1 sources disagree; both dates are recorded."))
        self.assertIsNone(match("Two tier-1 sources disagree. Both dates are recorded."))
        self.assertIsNone(match("Both dates are recorded; two tier-1 sources disagree."))
        self.assertIsNone(match("Both dates are recorded. Two tier-1 sources disagree."))
        self.assertEqual(match("Counts are taken from the v3.1.0 record, the highest-ranked source."),
                         "taken from the v3.1.0 record, the highest-ranked")
        self.assertEqual(match("The higher-ranked source, v3.1.0 of the record, is used."), "higher-ranked")
        # ... and within 80 characters, on either side.
        near = "The higher-ranked source " + "x" * 50 + " is used."
        far = "The higher-ranked source " + "x" * 80 + " is used."
        self.assertEqual(match(near), "higher-ranked")
        self.assertIsNone(match(far))
        near = "The date is used " + "x" * 50 + " as the higher-ranked source."
        far = "The date is used " + "x" * 80 + " as the higher-ranked source."
        self.assertEqual(match(near), "used " + "x" * 50 + " as the higher-ranked")
        self.assertIsNone(match(far))
        # A verb the list does not name is no verb: the source's own statement.
        self.assertIsNone(match("The higher-ranked source gives a later date."))
        # A name of the declared ranking matches as in v2.
        for text in ("The source manifest records the release date.", "the input manifest ranks it first",
                     "under the declared source ranking", "The source ranking cannot separate them."):
            with self.subTest(text=text):
                self.assertIsNotNone(match(text))

    def test_v3_verb_first_span_absorbs_a_name_and_consumes_its_verb(self):
        """#3732: the two consequences of the verb-first span that the dated
        note states. A name of the declared ranking between a verb and a later
        term is inside that span, not a match of its own (v2 gives two); and a
        verb one span consumed cannot admit a second term after it, so the
        80-character rule is a condition a match needs, not a promise."""
        v2, v3 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                  for v in (2, 3))

        def matches(pattern, text):
            return [m.group() for m in pattern.regex.finditer(text)]

        absorbed = "The value used from the input manifest is the higher-ranked one."
        self.assertEqual(matches(v3, absorbed), ["used from the input manifest is the higher-ranked"])
        self.assertEqual(matches(v2, absorbed), ["input manifest", "higher-ranked"])
        consumed = "It was preferred over the lower-ranked source, the higher-ranked one being older."
        self.assertEqual(matches(v3, consumed), ["preferred over the lower-ranked"])
        self.assertEqual(matches(v2, consumed), ["lower-ranked", "higher-ranked"])

    def test_every_v3_source_ranking_match_ends_at_a_v2_match(self):
        """v3 narrows v2: over v3's own self-test texts and the sentences
        above, each v3 match ends where a v2 match of the same text ends."""
        v2, v3 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                  for v in (2, 3))
        texts = v3.examples + v3.counterexamples + v2.examples + v2.counterexamples + (
            "Two tier-1 sources disagree, so both dates are recorded.",
            "The date is preferred as the higher-ranked source, and the lower-ranked one is noted.")
        for text in texts:
            ends = {m.end() for m in v2.regex.finditer(text)}
            for m in v3.regex.finditer(text):
                with self.subTest(text=text, match=m.group()):
                    self.assertIn(m.end(), ends)

    def test_v4_changes_only_the_source_ranking_pattern(self):
        """#3791: one regex and its self-test texts move; every other pattern,
        the flags, the class descriptions, the scope and the declaration are
        v3's. v4 keeps v3's examples and counterexamples and adds to them."""
        v3, v4 = (lx.load("absence_self_narration", v) for v in (3, 4))
        self.assertTrue(v4.counterexamples_required)
        self.assertEqual((v4.classes, v4.scope), (v3.classes, v3.scope))
        self.assertEqual([p.id for p in v4.patterns], [p.id for p in v3.patterns])
        for a, b in zip(v3.patterns, v4.patterns):
            with self.subTest(pattern=a.id):
                if a.id == "rsn.source-ranking":
                    self.assertEqual((b.cls, b.regex.flags), (a.cls, a.regex.flags))
                    self.assertNotEqual(b.regex.pattern, a.regex.pattern)
                    self.assertEqual(b.examples[:len(a.examples)], a.examples)
                    self.assertEqual(b.counterexamples[:len(a.counterexamples)], a.counterexamples)
                else:
                    self.assertEqual((b.cls, b.regex.pattern, b.regex.flags, b.examples, b.counterexamples),
                                     (a.cls, a.regex.pattern, a.regex.flags, a.examples, a.counterexamples))

    def test_v4_source_ranking_is_v3s_with_only_the_window_changed(self):
        """#3791: the three alternatives, the verb list and the ranking terms
        are v3's. Only the gap between verb and term moves: v3's
        80-character window that stops at `;` and at a `.` before whitespace
        becomes an unbounded one that stops only at such a `.`, except after
        St., Dr., e.g., i.e. and U.S. (#3792)."""
        v3, v4 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                  for v in (3, 4))
        v3_gap = r"(?:[^.;]|\.(?!\s)){0,80}?"
        self.assertEqual(v3.regex.pattern.count(v3_gap), 2)
        self.assertEqual(v4.regex.pattern, v3.regex.pattern.replace(v3_gap, V4_GAP))

    def test_no_character_of_the_v4_gap_can_be_taken_two_ways(self):
        """#3894: at every position of text dense with abbreviations, dots in
        tokens and full stops, at most one of the gap's alternatives matches.
        Where two could take one `.` ("e.g.,"), a failing match was tried 2^k
        ways. The disjoint form matches what the overlapping one did."""
        alternatives = [re.compile(a) for a in V4_GAP[len("(?:"):-len(")*?")].split("|")]
        self.assertEqual(len(alternatives), 7)
        texts = ("See e.g., x and i.e., y; U.S.-based St. Louis, Dr. Smith, v3.1.0 and No. 5 et al. end. "
                 "U.S. data, e.g. these, i.e. those.\nSt.\tDr.  e.g.x i.e.x U.S.x St.x Dr.x",)
        for text in texts:
            for i in range(len(text)):
                with self.subTest(i=i, at=text[max(0, i - 5):i + 2]):
                    self.assertLessEqual(sum(bool(a.match(text, i)) for a in alternatives), 1)
        v4 = {p.id: p for p in lx.load("absence_self_narration", 4).patterns}["rsn.source-ranking"]
        overlapping = re.compile(v4.regex.pattern.replace(V4_GAP, V4_GAP_OVERLAPPING), v4.regex.flags)
        self.assertNotEqual(overlapping.pattern, v4.regex.pattern)
        samples = v4.examples + v4.counterexamples + texts + tuple(
            f"The higher-ranked source gives {a} Smith{p} and that value is used."
            for a in ("St.", "Dr.", "e.g.", "i.e.", "U.S.", "No.", "et al.") for p in (",", ".", "-x", ""))
        for text in samples:
            with self.subTest(text=text):
                self.assertEqual([m.span() for m in v4.regex.finditer(text)],
                                 [m.span() for m in overlapping.finditer(text)])

    def test_v4_source_ranking_finds_the_verb_anywhere_in_the_sentence_and_never_past_it(self):
        """The rule the v4 pattern's comment states, one boundary at a time,
        on both branches: verb after the term (a lookahead) and before it (a
        consuming span)."""
        v3, v4 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                  for v in (3, 4))

        def match(pattern, text):
            m = pattern.regex.search(text)
            return m.group() if m else None

        # Past a `;`: v3 stops there, v4 does not.
        for text, want in [("Two tier-1 sources disagree; both dates are recorded.", "tier-1 sources"),
                           ("Both dates are recorded; two tier-1 sources disagree.",
                            "recorded; two tier-1 sources")]:
            with self.subTest(text=text):
                self.assertIsNone(match(v3, text))
                self.assertEqual(match(v4, text), want)
        # More than 80 characters away, in the same sentence: v4 has no bound.
        far = "The higher-ranked source " + "x" * 300 + " is used."
        self.assertIsNone(match(v3, far))
        self.assertEqual(match(v4, far), "higher-ranked")
        far = "The date is used " + "x" * 300 + " as the higher-ranked source."
        self.assertEqual(match(v4, far), "used " + "x" * 300 + " as the higher-ranked")
        # A full stop still ends the sentence, on both branches, with or without a `;` before it.
        for text in ("Two tier-1 sources disagree. Both dates are recorded.",
                     "Both dates are recorded. Two tier-1 sources disagree.",
                     "Two tier-1 sources disagree; they differ. Both dates are recorded.",
                     "Two tier-1 sources disagree.\nBoth dates are recorded."):
            with self.subTest(text=text):
                self.assertIsNone(match(v4, text))
        # A `.` inside a token never ended one; a verb the list lacks is still no verb.
        self.assertEqual(match(v4, "The higher-ranked source, v3.1.0 of the record, is used."), "higher-ranked")
        self.assertIsNone(match(v4, "The higher-ranked source gives a later date; it is the release page."))
        # The v1 sample's borderline conflicts stay unmatched, and names still need no verb.
        for text in RANKING_BORDERLINE:
            with self.subTest(text=text):
                self.assertIsNone(match(v4, text))
        self.assertEqual(match(v4, "The source manifest records the release date."), "source manifest")

    def test_v4_abbreviations_do_not_end_the_sentence(self):
        """#3792: the `.` of St., Dr., e.g., i.e. and U.S. is not a full stop,
        so "Washington University in St. Louis" does not cut the sentence; the
        full stop after the next word still does, and "No." and "et al." are
        not excepted. Each case is shown by changing only the abbreviation."""
        v3, v4 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                  for v in (3, 4))
        example = "The higher-ranked source names Washington University in St. Louis as the sponsor, and that name is used."
        self.assertIn(example, v4.examples)
        self.assertIsNone(v3.regex.search(example))
        self.assertEqual(v4.regex.search(example).group(), "higher-ranked")
        counterexample = "The higher-ranked source gives Washington University in St. Louis. Both values are recorded above."
        self.assertIn(counterexample, v4.counterexamples)
        self.assertIsNone(v4.regex.search(counterexample))
        for abbreviation in ("St.", "Dr.", "e.g.", "i.e.", "U.S."):
            text = f"The higher-ranked source gives {abbreviation} Smith as contact, and that value is used."
            with self.subTest(abbreviation=abbreviation):
                self.assertEqual(v4.regex.search(text).group(), "higher-ranked")
                # verb first, across the abbreviation
                text = f"The value used names {abbreviation} Smith, the higher-ranked source."
                self.assertEqual(v4.regex.search(text).group(), f"used names {abbreviation} Smith, the higher-ranked")
        for word in ("Louis.", "No.", "et al.", "first.", "est."):
            text = f"The higher-ranked source gives {word} Smith is the contact, and that value is used."
            with self.subTest(word=word):
                self.assertIsNone(v4.regex.search(text))
        self.assertIn("Two tier-1 sources answer: No. Both values are recorded above.", v4.counterexamples)

    def test_every_v4_source_ranking_match_ends_at_a_v2_match_and_keeps_v3s(self):
        """v4 matches only terms v2 matched, and over the self-test texts
        every v3 match still ends where a v4 match ends."""
        v2, v3, v4 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                      for v in (2, 3, 4))
        texts = v4.examples + v4.counterexamples + v3.examples + v2.examples + (
            "Two tier-1 sources disagree, so both dates are recorded.",
            "The date is preferred as the higher-ranked source, and the lower-ranked one is noted.",
            "The value used from the input manifest is the higher-ranked one.",
            "It was preferred over the lower-ranked source, the higher-ranked one being older.")
        for text in texts:
            ends = {v: {m.end() for m in p.regex.finditer(text)} for v, p in ((2, v2), (3, v3), (4, v4))}
            with self.subTest(text=text):
                self.assertLessEqual(ends[4], ends[2])
                self.assertLessEqual(ends[3], ends[4])

    def test_v5_changes_only_the_four_patterns_it_names(self):
        """#3875: rsn.source-ranking and the three bundle-wide patterns with a
        bounded window move; every other pattern, the flags, the class
        descriptions, the scope and the declaration are v4's. The four keep
        v4's self-test texts and add to them, except the one v4 example that
        is now a counterexample (#3874, #3706)."""
        v4, v5 = (lx.load("absence_self_narration", v) for v in (4, 5))
        self.assertTrue(v5.counterexamples_required)
        self.assertEqual((v5.classes, v5.scope), (v4.classes, v4.scope))
        self.assertEqual([p.id for p in v5.patterns], [p.id for p in v4.patterns])
        moved = "The source manifest records the release date."
        for a, b in zip(v4.patterns, v5.patterns):
            with self.subTest(pattern=a.id):
                if a.id in V5_BWA_PATTERNS + ("rsn.source-ranking",):
                    self.assertEqual((b.cls, b.regex.flags), (a.cls, a.regex.flags))
                    self.assertNotEqual(b.regex.pattern, a.regex.pattern)
                    self.assertGreater(len(b.examples), len([t for t in a.examples if t != moved]))
                    self.assertEqual([t for t in b.examples if t in a.examples],
                                     [t for t in a.examples if t != moved])
                    self.assertEqual(b.counterexamples[:len(a.counterexamples)], a.counterexamples)
                    self.assertGreater(len(b.counterexamples), len(a.counterexamples))
                else:
                    self.assertEqual((b.cls, b.regex.pattern, b.regex.flags, b.examples, b.counterexamples),
                                     (a.cls, a.regex.pattern, a.regex.flags, a.examples, a.counterexamples))
        ranking = {p.id: p for p in v5.patterns}["rsn.source-ranking"]
        self.assertIn(moved, ranking.counterexamples)

    def test_v5_bundle_wide_windows_are_v4s_with_the_source_ranking_sentence_end(self):
        """#3887: in the three patterns, only the window's character class
        moves, to the one v4's rsn.source-ranking gap uses, bounded as
        before and still ending at `;` and `:`."""
        v4, v5 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns} for v in (4, 5))
        for pid in V5_BWA_PATTERNS:
            with self.subTest(pattern=pid):
                self.assertEqual(v4[pid].regex.pattern.count(BWA_GAP), 1)
                self.assertEqual(v5[pid].regex.pattern, v4[pid].regex.pattern.replace(BWA_GAP, V5_BWA_GAP))
        self.assertEqual(V5_BWA_GAP, V4_GAP.replace("[^.]", "[^.;:]").replace(")*?", "){0,80}?"))
        no_window = [p.id for p in v5.values() if p.id not in V5_BWA_PATTERNS and "{0,80}" in p.regex.pattern]
        self.assertEqual(no_window, [])

    def test_no_character_of_the_v5_bundle_wide_window_can_be_taken_two_ways(self):
        """#3894's rule for the new windows: at every position at most one
        alternative matches, and the overlapping form would match the same."""
        alternatives = [re.compile(a) for a in V5_BWA_GAP[len("(?:"):-len("){0,80}?")].split("|")]
        self.assertEqual(len(alternatives), 7)
        text = ("See e.g., x and i.e., y; U.S.-based St. Louis, Dr. Smith, v3.1.0 and No. 5 et al. end: "
                "U.S. data, e.g. these, i.e. those.\nSt.\tDr.  e.g.x i.e.x U.S.x St.x Dr.x")
        for i in range(len(text)):
            with self.subTest(i=i, at=text[max(0, i - 5):i + 2]):
                self.assertLessEqual(sum(bool(a.match(text, i)) for a in alternatives), 1)
        v5 = {p.id: p for p in lx.load("absence_self_narration", 5).patterns}
        overlapping = V4_GAP_OVERLAPPING.replace("[^.]", "[^.;:]").replace(")*?", "){0,80}?")
        for pid in V5_BWA_PATTERNS:
            pattern = v5[pid]
            other = re.compile(pattern.regex.pattern.replace(V5_BWA_GAP, overlapping), pattern.regex.flags)
            self.assertNotEqual(other.pattern, pattern.regex.pattern)
            for sample in pattern.examples + pattern.counterexamples + (text,):
                with self.subTest(pattern=pid, text=sample):
                    self.assertEqual([m.span() for m in pattern.regex.finditer(sample)],
                                     [m.span() for m in other.finditer(sample)])

    def test_v5_bundle_wide_windows_cross_an_abbreviation_and_stop_at_a_full_stop(self):
        """#3887, one change at a time: the abbreviation's `.` no longer ends
        the window (v4 stopped there); the full stop after the next word, "No."
        and "et al." still do, as do `;` and `:`; and 80 characters still
        bound it."""
        v4, v5 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns} for v in (4, 5))
        tails = {"bwa.not-by-any-source": "given by any source", "bwa.not-in-bundle": "given in the bundle",
                 "bwa.not-in-the-sources": "given in the sources"}
        for pid, tail in tails.items():
            for abbreviation in ("St.", "Dr.", "e.g.", "i.e.", "U.S."):
                text = f"No address for {abbreviation} Smith is {tail}."
                with self.subTest(pattern=pid, abbreviation=abbreviation):
                    self.assertIsNone(v4[pid].regex.search(text))
                    self.assertEqual(v5[pid].regex.search(text).group(), text[:-1])
            for word in ("Louis.", "No.", "et al.", "first.", "Smith;", "Smith:"):
                text = f"No address for {word} Smith is {tail}."
                with self.subTest(pattern=pid, word=word):
                    self.assertIsNone(v5[pid].regex.search(text))
            near = f"No {'x' * 60} is {tail}."
            far = f"No {'x' * 90} is {tail}."
            self.assertIsNotNone(v5[pid].regex.search(near))
            self.assertIsNone(v5[pid].regex.search(far))

    def test_v5_source_ranking_is_v4s_with_names_as_terms_and_use_guarded(self):
        """#3875, #3874, #3706: the names' verb-free alternative is gone, the
        names join the ranking terms on both branches, and `use[sd]?` becomes
        a guarded `uses?` beside `used`. The window is v4's."""
        v4, v5 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                  for v in (4, 5))
        self.assertTrue(v4.regex.pattern.startswith(NAMES))
        rest = v4.regex.pattern[len(NAMES):]
        self.assertEqual((rest.count(V4_TERM), rest.count(V4_USE), rest.count(V4_GAP)), (2, 2, 2))
        self.assertEqual(v5.regex.pattern, rest.replace(V4_TERM, V5_TERM).replace(V4_USE, V5_USE))

    def test_v5_use_counts_as_the_verb_only_where_it_is_one(self):
        """#3875, shown by changing one word at a time: the document name
        "data transfer and use agreement" carries no verb in v5 (v4 took its
        `use`), and `use` after a subject or "to" still counts."""
        v4, v5 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                  for v in (4, 5))

        def match(pattern, text):
            m = pattern.regex.search(text)
            return m.group() if m else None

        issue = ("Attachment 2 of the data transfer and use agreement, an equally ranked source, states that the "
                 "data are identifiable.")
        self.assertIn(issue, v5.counterexamples)
        self.assertEqual(match(v4, issue), "use agreement, an equally ranked")
        self.assertIsNone(match(v5, issue))
        example = "The record does not use the lower-ranked source's date."
        self.assertIn(example, v5.examples)
        self.assertEqual(match(v5, example), "use the lower-ranked")
        for verb in ("We use the higher-ranked source.", "The record uses the higher-ranked source.",
                     "The higher-ranked source is used.", "It chose to use the higher-ranked source."):
            with self.subTest(verb=verb):
                self.assertIsNotNone(match(v5, verb))
        # Each guard alone decides: a noun after `use`, and a word before it.
        base = "The higher-ranked source permits use {}to research."
        self.assertIsNotNone(match(v5, base.format("")))
        for noun in ("agreement ", "agreements ", "of the data ", "cases ", "limitations ", "restrictions ",
                     "conditions ", "terms ", "policy ", "policies "):
            with self.subTest(after=noun):
                self.assertIsNone(match(v5, base.format(noun)))
                self.assertIsNotNone(match(v4, base.format(noun)))
        for word in ("the", "a", "an", "its", "their", "any", "no", "for", "of", "in", "data"):
            text = f"The higher-ranked source permits {word} use to research."
            with self.subTest(before=word):
                self.assertIsNone(match(v5, text))
                self.assertIsNotNone(match(v5, text.replace(f" {word} use", " use")))
        # A noun after an adjective is not guarded: the list is not a parser.
        self.assertIsNotNone(match(v5, "The higher-ranked source permits secondary use."))

    def test_v5_names_of_the_declared_ranking_need_a_verb(self):
        """#3874, #3706: a name with no listed verb in its sentence, which v4
        matched, does not match in v5; with one, before or after it and past
        `;` as for the other terms, it does. The full stop still ends it."""
        v4, v5 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                  for v in (4, 5))

        def match(pattern, text):
            m = pattern.regex.search(text)
            return m.group() if m else None

        for name in ("source manifest", "input manifest", "source ranking", "declared ranking",
                     "declared source ranking"):
            with self.subTest(name=name):
                bare = f"The {name} records the release date."
                self.assertEqual(match(v4, bare), name)
                self.assertIsNone(match(v5, bare))
                self.assertEqual(match(v5, f"The {name} ranks the page first; its date is used."), name)
                self.assertEqual(match(v5, f"The date is preferred under the {name}."),
                                 f"preferred under the {name}")
                self.assertIsNone(match(v5, f"The {name} ranks the page first. Its date is used."))
        for text in ("The source manifest records the release date.",
                     "The release pages, which the input manifest ranks higher, state no single total."):
            with self.subTest(text=text):
                self.assertIn(text, v5.counterexamples)
                self.assertIsNotNone(match(v4, text))

    def test_every_v5_source_ranking_match_ends_at_a_v2_term(self):
        """v5 matches only terms v2 matched; a name inside a v4 verb-first
        span can now end a span of its own, so a v5 match need not end where
        a v4 match does (the absorbed case of #3732)."""
        v2, v4, v5 = ({p.id: p for p in lx.load("absence_self_narration", v).patterns}["rsn.source-ranking"]
                      for v in (2, 4, 5))
        texts = v5.examples + v5.counterexamples + v4.examples + v2.examples + (
            "Two tier-1 sources disagree, so both dates are recorded.",
            "The value used from the input manifest is the higher-ranked one.",
            "It was preferred over the lower-ranked source, the higher-ranked one being older.")
        for text in texts:
            with self.subTest(text=text):
                self.assertLessEqual({m.end() for m in v5.regex.finditer(text)},
                                     {m.end() for m in v2.regex.finditer(text)})
        absorbed = "The value used from the input manifest is the higher-ranked one."
        self.assertEqual([m.group() for m in v4.regex.finditer(absorbed)],
                         ["used from the input manifest is the higher-ranked"])
        self.assertEqual([m.group() for m in v5.regex.finditer(absorbed)], ["used from the input manifest"])

    def test_every_result_identity_names_the_bytes(self):
        """The newest registered version by default, and the one named."""
        issue = {1: 2919, 2: 3132, 3: 3520, 4: 3791, 5: 3875}
        for version, want in [(None, 5), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]:
            with self.subTest(version=version):
                lexicon = lx.load("absence_self_narration", version)
                self.assertEqual(lexicon.identity(), {
                    "name": "absence_self_narration", "version": want,
                    "instrument": f"absence_self_narration lexicon v{want} (#{issue[want]})",
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
