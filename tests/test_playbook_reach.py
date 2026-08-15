"""A record says whether its runtime read the playbooks (#545).

The four uniform decision rules reach the API path only because each condition
*prompt* carries its own copy of them. The two added to the playbook since —
American English (#502) and the CURIE rule — reach it not at all, which is how
the v4 arm came to carry 135 British spellings.

Playbooks are hashed for every run deliberately: an unchanged hash on an API
record is how you can tell it did not read them. But that inference requires
already knowing the API path skips them, and the obvious reading of "three
files with hashes" is that the run followed them. So the record now says which
case it is.
"""

import re
import unittest
from pathlib import Path

from data_sheets_schema.provenance import (AGENT_PLAYBOOKS, playbook_facts,
                                           runtime_reads_playbooks)

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / ".claude/commands/d4d-full-core.md"
PROMPTS = ROOT / "src/download/prompts"


class TestRuntimeClassification(unittest.TestCase):
    def test_the_agentic_runtime_reads_them(self):
        self.assertTrue(runtime_reads_playbooks("Claude Code"))

    def test_the_api_runtime_does_not(self):
        self.assertFalse(runtime_reads_playbooks("Claude API (direct)"))

    def test_an_unstated_runtime_is_neither(self):
        """None is a third case. Recording False for a run that never said
        what it was would assert something nobody established."""
        self.assertIsNone(runtime_reads_playbooks(None))
        self.assertIsNone(runtime_reads_playbooks(""))


class TestTheRecordSaysWhich(unittest.TestCase):
    def test_a_consuming_run_records_it(self):
        block = playbook_facts(consumed=True)
        self.assertIs(block["consumed"], True)
        self.assertIn("opens these files itself", block["consumed_basis"])

    def test_a_non_consuming_run_records_it_and_why_they_are_hashed(self):
        """Otherwise the block reads as an unexplained inconsistency: files
        hashed but not read, with nothing saying that is deliberate."""
        block = playbook_facts(consumed=False)
        self.assertIs(block["consumed"], False)
        self.assertIn("not read", block["consumed_basis"])

    def test_an_unstated_runtime_omits_the_claim(self):
        """Silence rather than a guess — the field is absent, not False."""
        self.assertNotIn("consumed", playbook_facts())

    def test_the_files_are_hashed_either_way(self):
        """The hashes are the evidence; `consumed` only interprets them."""
        for flag in (True, False, None):
            with self.subTest(consumed=flag):
                block = playbook_facts(consumed=flag)
                self.assertEqual(len(block["files"]), len(AGENT_PLAYBOOKS))


class TestTheRuleSetsDoNotSilentlyDiverge(unittest.TestCase):
    """The duplication that caused this.

    The four original rules are maintained byte-identically in the playbook and
    in every condition prompt. That is the pattern #518 and #521 kept finding in
    the build — one list of content, several hand-kept copies — and it diverged
    the moment two rules were added to one copy only.

    This does not forbid divergence; a rule may legitimately be
    playbook-scope. It requires that any rule present in the playbook and
    absent from the prompts is one somebody chose, by listing it here.
    """

    #: Rules the playbook carries that the condition prompts deliberately do
    #: not, each with the reason. Emptying this list is the goal, and v5 is
    #: where the two below are expected to move into the prompt (#547).
    PLAYBOOK_ONLY = {
        "American English": "#502 — added to the playbook to avoid rotating "
                            "pins mid-arm; reaches the agentic path only",
        "CURIE": "same, added this session; reaches the agentic path only",
    }

    def _rule_bullets(self, text, start, end):
        block = text[text.index(start):text.index(end)]
        return [b.strip() for b in re.findall(r"^- (.+?)(?=\n- |\n\n)",
                                              block, re.S | re.M)]

    def test_every_playbook_only_rule_is_declared_here(self):
        """A rule that reaches one path and not the other is a decision. If a
        third appears without being listed, this fails and someone has to say
        whether that was intended."""
        playbook = PLAYBOOK.read_text(encoding="utf-8")
        rules = self._rule_bullets(playbook, "### Uniform decision rules",
                                   "### Recording the condition")
        v4 = (PROMPTS / "d4d_generic_arm_prompt_v4.md").read_text(
            encoding="utf-8")
        undeclared = []
        for rule in rules:
            head = rule.split(".")[0][:60]
            key = next((k for k in self.PLAYBOOK_ONLY if k in rule), None)
            if key:
                continue
            # a shared rule: some distinctive phrase of it must appear in v4
            probe = re.sub(r"[*`]", "", rule).split(".")[0][:40]
            if probe and probe not in re.sub(r"[*`]", "", v4):
                undeclared.append(head)
        self.assertEqual(undeclared, [],
                         "playbook rules absent from the v4 prompt and not "
                         "declared as playbook-only")

    def test_the_declared_ones_really_are_absent_from_the_prompts(self):
        """If a listed rule reaches the prompts after all, the entry is stale
        and should be removed rather than left asserting a gap that closed."""
        v4 = (PROMPTS / "d4d_generic_arm_prompt_v4.md").read_text(
            encoding="utf-8")
        for key in self.PLAYBOOK_ONLY:
            with self.subTest(rule=key):
                self.assertNotIn(key, v4)
