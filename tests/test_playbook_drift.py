"""A playbook edit is visible in the records that read the old one (#525).

Every agentic record hashes the playbooks it read, and until this nothing ever
compared those hashes to the files again. `runs check` reported bundle drift,
render-gate status, prompt pins, verdict schema pins and schema straddle — and
said nothing about the files the decision rules actually live in.

Found by editing one. #524 adds the American-English rule to
`.claude/commands/d4d-full-core.md`; the 15 records of the canonical arm hash
the previous bytes, and `runs check --strict` still exited 0 with nothing said.
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.runs import (PLAYBOOK_ABSENT, PLAYBOOK_CURRENT,
                                     PLAYBOOK_DRIFTED, PLAYBOOK_UNRECORDED,
                                     playbook_drift)


class TestOnFixtures(unittest.TestCase):
    """Synthetic records, so these keep working where the corpus does not."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.book = self.dir / "playbook.md"
        self.book.write_text("prefer omission over inference\n",
                             encoding="utf-8")

    def _record(self, entries, label="s_rep1", project="P"):
        path = self.dir / "m_core" / label / f"{project}_provenance.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(
            {"playbooks": {"hash_algorithm": "sha256", "files": entries}}),
            encoding="utf-8")
        return ("m", label, project)

    def _digest(self):
        return hashlib.sha256(self.book.read_bytes()).hexdigest()

    def test_an_unedited_playbook_is_current(self):
        args = self._record([{"path": str(self.book),
                              "sha256": self._digest()}])
        self.assertEqual(playbook_drift(*args, self.dir)[0], PLAYBOOK_CURRENT)

    def test_an_edited_playbook_is_drifted(self):
        args = self._record([{"path": str(self.book),
                              "sha256": self._digest()}])
        self.book.write_text("prefer inference over omission\n",
                             encoding="utf-8")
        status, why = playbook_drift(*args, self.dir)
        self.assertEqual(status, PLAYBOOK_DRIFTED)
        self.assertIn("playbook.md", why)

    def test_the_reason_names_both_hashes(self):
        """So a reader can tell which edit, not merely that there was one."""
        old = self._digest()
        args = self._record([{"path": str(self.book), "sha256": old}])
        self.book.write_text("changed\n", encoding="utf-8")
        _status, why = playbook_drift(*args, self.dir)
        self.assertIn(old[:8], why)
        self.assertIn(self._digest()[:8], why)

    def test_a_deleted_playbook_is_absent_not_drifted(self):
        """A rename is a different diagnosis from an edit — #431 exists
        because a renamed playbook silently became `exists: false`."""
        args = self._record([{"path": str(self.book),
                              "sha256": self._digest()}])
        self.book.unlink()
        self.assertEqual(playbook_drift(*args, self.dir)[0], PLAYBOOK_ABSENT)

    def test_a_record_with_no_playbook_block_is_unrecorded(self):
        path = self.dir / "m_core" / "s_rep1" / "P_provenance.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump({"run": {}}), encoding="utf-8")
        self.assertEqual(
            playbook_drift("m", "s_rep1", "P", self.dir)[0],
            PLAYBOOK_UNRECORDED)

    def test_a_missing_record_is_unrecorded_rather_than_a_crash(self):
        self.assertEqual(
            playbook_drift("m", "absent", "P", self.dir)[0],
            PLAYBOOK_UNRECORDED)

    def test_one_drifted_file_among_several_is_reported(self):
        """A run reads three playbooks; editing any one changes the method."""
        other = self.dir / "second.md"
        other.write_text("one referent per Dataset\n", encoding="utf-8")
        args = self._record([
            {"path": str(self.book), "sha256": self._digest()},
            {"path": str(other),
             "sha256": hashlib.sha256(other.read_bytes()).hexdigest()}])
        other.write_text("two referents\n", encoding="utf-8")
        status, why = playbook_drift(*args, self.dir)
        self.assertEqual(status, PLAYBOOK_DRIFTED)
        self.assertIn("second.md", why)
        self.assertNotIn("playbook.md", why)

    def test_an_entry_without_a_hash_is_skipped_not_fatal(self):
        args = self._record([{"path": str(self.book)}])
        self.assertEqual(playbook_drift(*args, self.dir)[0], PLAYBOOK_CURRENT)


class TestAgainstTheCorpus(unittest.TestCase):
    def test_it_is_reported_and_never_fatal(self):
        """Playbooks are meant to evolve. A gate would turn every improvement
        to the method into a corpus-wide failure, which is why this is drift
        detection and not prompt-style pinning."""
        import subprocess

        result = subprocess.run(
            ["poetry", "run", "d4d", "runs", "check", "--strict"],
            capture_output=True, text=True, check=False)
        if "read a playbook" not in result.stdout:
            self.skipTest("no drifted playbooks in corpus")
        self.assertEqual(result.returncode, 0)

    def test_the_real_records_carry_playbook_hashes_to_check(self):
        """If this ever finds none, the guard above is vacuous."""
        from data_sheets_schema.runs import canonical_runs
        runs = canonical_runs()
        if not runs:
            self.skipTest("no canonical records")
        statuses = {playbook_drift("claudecode_agent", i["label"], p)[0]
                    for p, i in runs.items()}
        self.assertTrue(statuses - {PLAYBOOK_UNRECORDED},
                        "no canonical record records a playbook hash")
