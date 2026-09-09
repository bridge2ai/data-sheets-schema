"""A subagent's reply is evidence of which definition it was given (#1077).

The incident: the Element 8 software threshold was written into
`d4d-rubric10-semantic.md`, verified on disk, and a subagent spawned
afterwards reported the pre-edit criteria verbatim. Intermittent, so worse
than consistent — a rescore can silently measure the old instrument.

`instrument_sha256` (#1099) does not detect it: the agent computes that by
reading the file from disk, which is current, while the definition it was
handed may be stale.

Two properties carry the whole mechanism, and the first version of it had
neither (#1102):

1. **The answer is not in the question.** The first version printed the
   challenge sentence in the preamble, so echoing the preamble passed —
   including for the stale agent the check exists to catch.
2. **The expected text is absent from the previous version.** The first
   version asked only whether a diff was non-empty, which a reformat
   satisfies, and its diff query was one commit wide so it went blind for
   all twelve definitions the moment anything else was committed.
"""
import subprocess
import unittest
from pathlib import Path

from data_sheets_schema.agent_pin import (AGENT_DIR, MIN_CHALLENGE,
                                          NoDiscriminatingChallenge,
                                          StaleAgentDefinition, _normalise,
                                          _usable, agent_digest, challenge,
                                          challenge_between, discriminates,
                                          echoed, sentences_by_section, spawn_preamble,
                                          verify_echo)

REPO = Path(__file__).resolve().parents[1]
AGENT = "d4d-rubric10-semantic"
AGENT_REL = f".claude/agents/{AGENT}.md"


def _at(commit):
    got = subprocess.run(["git", "show", f"{commit}:{AGENT_REL}"],
                         capture_output=True, cwd=REPO)
    return None if got.returncode else got.stdout.decode("utf-8", "replace")


class TestTheAnswerIsNotInTheQuestion(unittest.TestCase):
    """#1102's first finding, demonstrated end to end by the reviewer:
    `preamble | check-echo` returned a tick."""

    def setUp(self):
        if not discriminates(AGENT):
            self.skipTest(f"{AGENT} has no discriminating challenge here")

    def test_echoing_the_preamble_does_not_pass(self):
        self.assertFalse(echoed(AGENT, spawn_preamble(AGENT)))

    def test_the_expected_text_is_absent_from_the_preamble(self):
        self.assertNotIn(_normalise(challenge(AGENT)["expected"]),
                         _normalise(spawn_preamble(AGENT)))

    def test_the_preamble_carries_the_locator_instead(self):
        ask = challenge(AGENT)
        self.assertIn(ask["locator"], spawn_preamble(AGENT))

    def test_the_preamble_says_why_the_sentence_is_withheld(self):
        self.assertIn("deliberately not", spawn_preamble(AGENT))

    def test_a_genuine_quote_passes(self):
        self.assertTrue(echoed(AGENT, "Quoting: " + challenge(AGENT)["expected"]))


class TestTheQuestionAndTheAnswerAreOneUnit(unittest.TestCase):
    """#1145: the preamble asked for the section's longest sentence while
    the verifier held the longest fresh line. On the review-record
    definition the sentence carrying that line ranked 2nd of 38, so an
    agent that did exactly as asked was told it was stale."""

    SHARED = ("This long sentence about model identity is present in every version of the definition and "
              "is the longest one in its section by a wide margin, as the shared paragraph was.")
    FRESH = "Among the mints, judge a fragment on another entity's identifier by its referent, not its base."
    OLD = f"---\n---\n## Procedure\n\n{SHARED}\n\nSome other sentence that is short.\n"
    NEW = f"## Procedure\n\n{SHARED} {FRESH}\n"

    def test_the_expected_sentence_is_the_fresh_one_not_the_longest(self):
        ask = challenge_between(self.NEW, self.OLD)
        self.assertEqual(ask["expected"], self.FRESH)
        self.assertNotEqual(ask["expected"], self.SHARED)

    def test_the_preamble_points_at_it_by_its_opening_words(self):
        ask = challenge_between(self.NEW, self.OLD)
        self.assertEqual(ask["prefix"], "Among the mints,")
        self.assertTrue(self.FRESH.startswith(ask["prefix"]))
        self.assertNotIn(self.FRESH, ask["prefix"])                     # the prefix is not the answer

    def test_an_agent_that_does_as_asked_passes_and_the_old_rule_would_have_failed_it(self):
        """The honest reply: find the section, quote the sentence that begins
        with the prefix. Under the previous rule the honest reply to
        "quote the longest sentence" was SHARED, which the verifier would
        have refused."""
        ask = challenge_between(self.NEW, self.OLD)
        section = [sent for h, sent in sentences_by_section(self.NEW) if h == "Procedure"]
        honest = next(sent for sent in section if sent.startswith(ask["prefix"]))
        self.assertIn(_normalise(ask["expected"]), _normalise("Quoting: " + honest))
        longest = max(section, key=len)
        self.assertNotIn(_normalise(ask["expected"]), _normalise("Quoting: " + longest))

    def test_the_prefix_is_unique_within_the_section(self):
        twin = "Among the mints, a second and deliberately longer sentence with the same opening words but a different ending."
        new = f"## Procedure\n\n{self.SHARED} {twin} {self.FRESH}\n"
        ask = challenge_between(new, self.OLD)
        self.assertEqual(ask["expected"], twin)                          # the longest fresh sentence
        self.assertEqual(ask["prefix"], "Among the mints, a")            # four words: three are shared with FRESH
        others = [sent for h, sent in sentences_by_section(new) if h == "Procedure" and sent != twin]
        self.assertFalse(any(_normalise(o).startswith(_normalise(ask["prefix"])) for o in others))

    def test_a_prefix_is_never_the_whole_sentence(self):
        """#1149 review, M1: a sibling sharing every word but the last would
        have made the prefix the answer, and copying the preamble would have
        passed — #1102 again. Such a sentence is skipped for the next
        fresh one, or the challenge is refused."""
        base = "Among the mints, judge a fragment on another entity's identifier by its referent, not its"
        near = f"{base} base."; other = f"{base} host."
        new = f"## Procedure\n\n{self.SHARED} {near} {other}\n"
        old = f"---\n---\n## Procedure\n\n{self.SHARED} {other}\n"      # only `near` is fresh
        self.assertIsNone(challenge_between(new, old))
        new2 = new + f"\n{self.FRESH.replace('Among the mints', 'Elsewhere in the record')}\n"
        ask = challenge_between(new2, old)
        self.assertTrue(ask["expected"].startswith("Elsewhere in the record"))
        self.assertLess(len(ask["prefix"]), len(ask["expected"]))

    def test_a_prefix_reveals_at_most_half_the_sentence(self):
        """#1149 round 2, S1: a sibling sharing a long opening would have
        left one word hidden — "not the whole sentence" is not "not the
        answer". Such a sentence is skipped like an unnameable one."""
        opening = "Among the mints, judge a fragment on another entity's identifier by its referent and never by"
        near = f"{opening} its base, which decides nothing."; other = f"{opening} its host, which decides nothing."
        new = f"## Procedure\n\n{self.SHARED} {near} {other}\n"
        old = f"---\n---\n## Procedure\n\n{self.SHARED} {other}\n"
        self.assertIsNone(challenge_between(new, old))
        from data_sheets_schema.agent_pin import MAX_PREFIX_SHARE
        for path in sorted(AGENT_DIR.glob("*.md")):
            ask = challenge(path.stem)
            if ask is not None:
                self.assertLessEqual(len(ask["prefix"].split()), max(3, int(len(ask["expected"].split()) * MAX_PREFIX_SHARE)), path.stem)

    def test_a_candidate_that_is_two_sentences_is_never_asked_for(self):
        """#1149 round 2, S2: a lower-case or digit-led continuation, or an
        abbreviation that really ended a sentence, left `expected` spanning
        two sentences and the honest one-sentence quote refused. The
        post-condition is form-independent."""
        from data_sheets_schema.agent_pin import _one_sentence
        self.assertFalse(_one_sentence("It stands on its own account. forced settles the presence of the rest."))
        self.assertFalse(_one_sentence("Count them in the records it read. 953 of them are schema-forced ids."))
        self.assertFalse(_one_sentence("List them, and so on, etc. The next rule is about identifiers."))
        self.assertTrue(_one_sentence("Take the identifier, e.g. DOI or ROR, exactly as written (never today's file)."))
        self.assertTrue(_one_sentence("Cite Smith et al. and Fig. 3 in the U.S. edition."))
        body = ("## H\n\nIt stands on its own account. forced settles the presence of every remaining "
                "value in the section and nothing else does.\nA second fresh sentence that is one sentence "
                "and long enough to be asked for on its own.\n")
        ask = challenge_between(body, "---\n---\n## H\n\nnothing\n")
        self.assertTrue(ask["expected"].startswith("A second fresh sentence"))

    def test_every_live_prefix_is_shorter_than_its_sentence(self):
        for path in sorted(AGENT_DIR.glob("*.md")):
            ask = challenge(path.stem)
            if ask is not None:
                with self.subTest(agent=path.stem):
                    self.assertLess(len(ask["prefix"]), len(ask["expected"]))
                    self.assertTrue(ask["expected"].startswith(ask["prefix"]))

    def test_a_sentence_closed_inside_a_bracket_or_quote_is_one_sentence(self):
        """#1149 review, S2: `.)` and `.”` merged two sentences, and the
        honest one-sentence quote was refused."""
        body = ("## H\n\nThe first sentence ends inside a parenthesis (never today's file.) "
                "Report the outcome of every check in the section that follows this one. "
                "The second ends in a quotation \u201cthe identifier field.\u201d "
                "Report every disagreement you find between the two records in full.\n")
        sents = [s for _, s in sentences_by_section(body)]
        self.assertEqual(len(sents), 4)
        self.assertTrue(sents[1].startswith("Report the outcome")); self.assertTrue(sents[3].startswith("Report every"))

    def test_an_abbreviation_or_a_broken_paragraph_does_not_yield_a_fragment(self):
        """#1149 review, S3: `e.g. DOI` is not a sentence start, and the
        tail of a paragraph a bullet list interrupted starts lower-case."""
        body = ("## H\n\nTake the identifier the evidence supplies, e.g. DOI or ROR or an accession, "
                "exactly as it is written in the bundle you read and nowhere else at all.\n"
                "- a bullet\n\nand to constructed identifiers the same rule applies without exception "
                "whatever the slot, because the referent decides it.\n")
        old = "---\n---\n## H\n\nnothing\n"
        sents = [s for _, s in sentences_by_section(body)]
        self.assertTrue(any(s.startswith("Take the identifier") and "e.g. DOI" in s for s in sents))
        ask = challenge_between(body, old)
        self.assertTrue(ask["expected"].startswith("Take the identifier"))
        self.assertIn("and to constructed identifiers", " ".join(sents).lower())   # the fragment exists in the section …
        self.assertFalse(ask["expected"].lower().startswith("and to constructed"))  # … and is never the one asked for

    def test_quotes_dashes_and_backticks_do_not_decide_a_match(self):
        """#1149 review, S4: half a kilobyte quoted verbatim may straighten a
        quote, retype an em dash or drop a backtick; none of those is a
        stale definition."""
        a = "Judge \u201cthe `id` slot\u201d \u2014 not its base \u2013 by the referent."
        b = 'Judge "the id slot" -- not its base - by the referent.'
        self.assertEqual(_normalise(a), _normalise(b))

    def test_a_fenced_block_is_not_prose(self):
        """The rubric agents' Output Format sections are JSON templates; a
        "sentence" cut from one is not something an agent can be asked for."""
        fence = "```json\n{\n  \"scores\": \"(repeat for all ten elements, each with evidence quotes and a verdict line)\"\n}\n```\n"
        new = f"## Output Format\n\n{fence}\n## Rules\n\n{self.FRESH}\n"
        ask = challenge_between(new, "---\n---\n## Rules\n\nnothing here\n")
        self.assertEqual(ask["expected"], self.FRESH)
        self.assertEqual([h for h, _ in sentences_by_section(new)], ["Rules"])

    def test_the_preamble_asks_for_the_sentence_that_begins_with_the_prefix(self):
        if not discriminates(AGENT):
            self.skipTest(f"{AGENT} has no discriminating challenge here")
        ask = challenge(AGENT)
        text = spawn_preamble(AGENT)
        self.assertIn(ask["prefix"], text)
        self.assertNotIn(ask["expected"], text)
        self.assertIn("begins", text)


class TestTheChallengeDiscriminates(unittest.TestCase):
    def test_it_catches_the_incident_that_filed_the_issue(self):
        """`8813c8e6` is the text the stale subagent held; `119e3171` added
        the #1059 threshold."""
        pre, post = _at("8813c8e6"), _at("119e3171")
        if pre is None or post is None:
            self.skipTest("that history is not in this checkout")
        ask = challenge_between(post.split("---", 2)[2], pre)
        self.assertIsNotNone(ask)
        self.assertNotIn(_normalise(ask["expected"]), _normalise(pre))

    def test_the_longest_line_rule_would_not_have(self):
        """Why the rule is what it is: the first version took the longest
        line of the *current* definition, and on the real pair that line is
        one both versions shared — so it discriminated nothing."""
        pre, post = _at("8813c8e6"), _at("119e3171")
        if pre is None or post is None:
            self.skipTest("that history is not in this checkout")
        longest_of_post = max(_usable(post.split("---", 2)[2].splitlines()), key=len)
        self.assertIn(_normalise(longest_of_post), _normalise(pre))

    def test_identical_versions_yield_no_challenge(self):
        """A reformat, or no change at all, must not produce a challenge that
        cannot fail — the check would then be reported as a pass."""
        body = "## H\n\n" + "x" * (MIN_CHALLENGE + 10) + "\n"
        self.assertIsNone(challenge_between(body, "---\n---\n" + body))

    def test_whitespace_only_changes_yield_no_challenge(self):
        line = "y" * (MIN_CHALLENGE + 10)
        self.assertIsNone(challenge_between(f"## H\n\n   {line}   \n",
                                            f"---\n---\n## H\n\n{line}\n"))

    def test_a_challenge_is_long_enough_that_echoing_it_is_not_luck(self):
        if not discriminates(AGENT):
            self.skipTest("no challenge here")
        self.assertGreaterEqual(len(challenge(AGENT)["expected"]), MIN_CHALLENGE)


class TestItRefusesRatherThanWeakens(unittest.TestCase):
    """A check that cannot fail is worse than no check, because it is
    reported as a pass."""

    def _undiscriminating(self):
        for name in ("d4d-mapper", "d4d-rocrate", "schema-stats"):
            if not discriminates(name):
                return name
        return None

    def test_no_challenge_means_no_preamble(self):
        name = self._undiscriminating()
        if name is None:
            self.skipTest("every definition discriminates in this checkout")
        with self.assertRaises(NoDiscriminatingChallenge):
            spawn_preamble(name)

    def test_no_challenge_means_no_verification_either_way(self):
        name = self._undiscriminating()
        if name is None:
            self.skipTest("every definition discriminates in this checkout")
        with self.assertRaises(NoDiscriminatingChallenge):
            verify_echo(name, "anything at all")
        self.assertFalse(echoed(name, "anything at all"),
                         "cannot-be-verified is not verified")


class TestVerification(unittest.TestCase):
    def setUp(self):
        if not discriminates(AGENT):
            self.skipTest("no challenge here")

    def test_a_reply_without_the_text_is_refused(self):
        with self.assertRaises(StaleAgentDefinition):
            verify_echo(AGENT, "I applied the rubric as given.")

    def test_whitespace_and_case_do_not_decide_it(self):
        noisy = "  ".join(challenge(AGENT)["expected"].upper().split())
        self.assertTrue(echoed(AGENT, f"> {noisy}\n"))

    def test_the_refusal_says_what_it_means(self):
        with self.assertRaises(StaleAgentDefinition) as caught:
            verify_echo(AGENT, "nothing relevant")
        self.assertIn("#1077", str(caught.exception))
        self.assertIn("stale", str(caught.exception))

    def test_the_preamble_carries_the_digest_and_the_stop_instruction(self):
        text = spawn_preamble(AGENT)
        self.assertIn(agent_digest(AGENT), text)
        self.assertIn("instrument_sha256", text)
        self.assertIn("stop rather than proceeding", text)


if __name__ == "__main__":
    unittest.main()
