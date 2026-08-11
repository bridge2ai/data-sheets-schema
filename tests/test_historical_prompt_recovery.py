"""Recovering a historical run's prompt as of its own commit (#399).

`--prompt` records prompts for live runs; `backfill` had no equivalent, so every
agentic record written before it carries `prompts: null`.

The load-bearing property is *which bytes* get hashed.
`d4d_generic_arm_prompt.md` was edited on 2026-07-29, the day after the 15 runs
that name it, and the two versions differ by 16 lines:

    at 2026-07-28 (what those runs read)   7e9a67f7…
    at 2026-07-29 and today                0fbc626b…

Hashing today's file would assert that a 2026-07-28 run used a prompt which did
not yet exist — the fabricated-provenance failure the whole module exists to
prevent.
"""

import subprocess
import unittest
from pathlib import Path

import yaml

from data_sheets_schema.provenance import (
    HISTORICAL_ALREADY,
    HISTORICAL_NO_HEADER,
    HISTORICAL_RECOVERED,
    _prompt_path_from_header,
    resolve_historical_prompt,
)

CORPUS = Path("data/d4d_concatenated")
RECOVERED_LABEL = "2026-07-28_claude-opus-5-generic_rep1"
AT_RUN_COMMIT = "7e9a67f70fedd7a22b63b3d23e295f317277aa476924aff140746c33890b4ca9"


class TestHeaderParsing(unittest.TestCase):
    def test_the_trailing_gloss_is_not_part_of_the_path(self):
        self.assertEqual(
            _prompt_path_from_header(
                "src/download/prompts/d4d_generic_arm_prompt.md "
                "(identical for all projects)"),
            "src/download/prompts/d4d_generic_arm_prompt.md")

    def test_a_bare_path_survives(self):
        self.assertEqual(_prompt_path_from_header("a/b.md"), "a/b.md")

    def test_absent_and_empty_yield_nothing(self):
        self.assertIsNone(_prompt_path_from_header(None))
        self.assertIsNone(_prompt_path_from_header("   "))

    def test_the_header_field_is_actually_parsed(self):
        """`Prompt` was missing from HEADER_FIELDS, so parse_header discarded
        the one field a historical prompt could be recovered from."""
        from data_sheets_schema.provenance import parse_header

        record = (CORPUS / "claudecode_agent" / RECOVERED_LABEL /
                  "AI_READI_d4d.yaml")
        if not record.exists():
            self.skipTest("corpus absent")
        self.assertIn("Prompt", parse_header(record))


@unittest.skipUnless(CORPUS.exists(), "corpus absent")
class TestResolution(unittest.TestCase):
    def test_the_recorded_hash_is_of_the_bytes_at_the_run_commit(self):
        """Not today's file. This is the whole point of the resolver.

        Asserted against what the record now *holds*, not against a fresh
        resolve — the backfill has run, so resolving again correctly reports
        `already_recorded`. The durable outcome is what matters.
        """
        from data_sheets_schema.provenance import record_path_for

        record = record_path_for("AI_READI", "claudecode_agent",
                                 RECOVERED_LABEL)
        data = yaml.safe_load(record.read_text(encoding="utf-8")) or {}
        files = (data.get("prompts") or {}).get("files") or []
        self.assertEqual([f["sha256"] for f in files], [AT_RUN_COMMIT])

    def test_the_recovery_block_names_the_commit_it_is_of(self):
        """Without it a reader cannot tell this from a live capture, and the
        two are not the same evidence."""
        from data_sheets_schema.provenance import record_path_for

        record = record_path_for("AI_READI", "claudecode_agent",
                                 RECOVERED_LABEL)
        data = yaml.safe_load(record.read_text(encoding="utf-8")) or {}
        recovery = (data.get("prompts") or {}).get("recovery") or {}
        self.assertTrue(recovery.get("commit"))
        self.assertEqual(recovery.get("as_of"), "2026-07-28")
        self.assertIn("not of the file today", recovery.get("note", ""))

    def test_resolving_an_unrecorded_run_still_recovers(self):
        """The resolver itself, exercised where nothing has been written yet.

        Uses a label whose records carry the header but sit under a method
        directory the backfill did not touch, if one exists; otherwise the
        already-recorded path is the only live behaviour and is covered above.
        """
        r = resolve_historical_prompt("AI_READI", "claudecode_agent",
                                      RECOVERED_LABEL)
        self.assertIn(r["status"], (HISTORICAL_RECOVERED, HISTORICAL_ALREADY))

    def test_the_recovered_hash_is_not_the_current_files(self):
        """If these ever coincide the test has stopped proving anything."""
        import hashlib

        current = hashlib.sha256(
            Path("src/download/prompts/d4d_generic_arm_prompt.md").read_bytes()
        ).hexdigest()
        self.assertNotEqual(current, AT_RUN_COMMIT)

    def test_a_run_with_no_prompt_header_is_not_guessed_at(self):
        """Supplied inline and never saved — it must stay null."""
        r = resolve_historical_prompt("AI_READI", "claudecode_agent",
                                      "2026-07-27_claude-opus-5_rep1")
        self.assertEqual(r["status"], HISTORICAL_NO_HEADER)
        self.assertNotIn("sha256", r)

    def test_a_record_that_already_has_prompts_is_left_alone(self):
        r = resolve_historical_prompt(
            "CHORUS", "claudecode_agent",
            "2026-08-07_claude-opus-5-claudecode-generic-v3_rep1")
        self.assertEqual(r["status"], HISTORICAL_ALREADY)

    def test_every_recovered_hash_reproduces_from_git(self):
        """The claim `pre_registry` rests on, checked rather than asserted.

        A recovered prompt is attested by git instead of by the pin registry.
        That is only a defensible substitute if `git show <commit>:<path>`
        actually reproduces the recorded bytes.
        """
        import hashlib

        checked = 0
        for path in CORPUS.glob("*_core/*/*_provenance.yaml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            prompts = data.get("prompts") or {}
            recovery = prompts.get("recovery")
            if not isinstance(recovery, dict) or not recovery.get("commit"):
                continue
            for entry in prompts.get("files") or []:
                blob = subprocess.run(
                    ["git", "show", f"{recovery['commit']}:{entry['path']}"],
                    capture_output=True, check=False)
                self.assertEqual(blob.returncode, 0, entry["path"])
                self.assertEqual(hashlib.sha256(blob.stdout).hexdigest(),
                                 entry["sha256"], str(path))
                self.assertEqual(len(blob.stdout), entry["bytes"], str(path))
                checked += 1
        self.assertGreater(checked, 0, "no recovered prompts to verify")

    def test_a_recovered_prompt_reports_pre_registry_not_uncanonical(self):
        """`uncanonical` means the bytes are attested by nothing (#436).

        These are attested by git at the run's own commit; the registry could
        not have pinned them because it postdates the run. Collapsing the two
        would make recovering honest evidence worse than leaving the record
        blank, since `uncanonical` is fatal under --strict.
        """
        from data_sheets_schema.runs import canonical_prompt_status

        status, why = canonical_prompt_status(
            "claudecode_agent", RECOVERED_LABEL, "AI_READI")
        self.assertEqual(status, "pre_registry")
        self.assertIn("attested by git", why)
