"""AGENT_PLAYBOOKS must match the files a run is actually told to read (#431).

The list is a claim about which files carry decision rules, and it was
maintained by hand with nothing checking it against the tree. Two failures
follow, and they are the same defect:

- a **renamed** playbook silently becomes `exists: false`, so the record
  attests that a file the agent actually read was absent;
- a **new** playbook is invisible — add a fourth instruction file, tell the
  agent to read it, and no record mentions it.

Both reproduce the original problem one level up: instructions reaching the
model through files nobody tracks, which is what hashing playbooks exists to
stop (#394, #420).
"""

import tempfile
import unittest
from pathlib import Path

from data_sheets_schema.provenance import (
    AGENT_PLAYBOOKS,
    playbook_facts,
    referenced_playbooks,
)


class TestPlaybookClosure(unittest.TestCase):
    def test_the_declared_list_is_the_referenced_closure(self):
        """The assertion the whole issue asks for."""
        self.assertEqual(set(AGENT_PLAYBOOKS), set(referenced_playbooks()))

    def test_every_declared_playbook_exists(self):
        """A renamed playbook would otherwise be recorded `exists: false`,
        which is an attestation that the agent read nothing."""
        missing = [str(p) for p in AGENT_PLAYBOOKS if not Path(p).exists()]
        self.assertEqual(missing, [])

    def test_the_closure_is_sorted_for_determinism(self):
        derived = [str(p) for p in referenced_playbooks()]
        self.assertEqual(derived, sorted(derived))

    def test_a_new_reference_is_picked_up(self):
        """The invisible-fourth-playbook case, exercised rather than argued."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "root.md"
            root.write_text(
                "read `.claude/commands/d4d-full-core.md` and also "
                "`.claude/commands/d4d-brand-new.md`\n", encoding="utf-8")
            derived = [str(p) for p in referenced_playbooks((root,))]
        self.assertIn(".claude/commands/d4d-brand-new.md", derived)

    def test_references_are_followed_transitively(self):
        """d4d-agent.md is reached only through d4d-full-core.md, so a
        one-level scan would miss the file carrying the slot-filling rules."""
        self.assertIn(Path(".claude/commands/d4d-agent.md"),
                      referenced_playbooks())

    def test_a_missing_root_does_not_raise(self):
        self.assertEqual(referenced_playbooks((Path("nope/absent.md"),)), ())

    def test_the_facts_record_the_declared_set_not_the_derived_one(self):
        """Records stay stable while the closure is the *check*.

        Deriving at record time would make a record's playbook list change
        whenever the prompt's wording changed, which is not what it attests.
        """
        recorded = {f["path"] for f in playbook_facts()["files"]}
        self.assertEqual(recorded, {str(p) for p in AGENT_PLAYBOOKS})

    def test_the_slot_filling_playbook_is_tracked(self):
        """`.claude/commands/d4d-agent.md` is where v2/v3 behaviour reaches the
        agentic path (#394). It is the file this whole mechanism exists for, so
        its presence is asserted by name rather than only by closure."""
        tracked = {str(p) for p in AGENT_PLAYBOOKS}
        self.assertIn(".claude/commands/d4d-agent.md", tracked)
