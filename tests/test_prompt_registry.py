"""#432 — a prompt file edited *before* rendering.

The render gate re-renders a record's spec and compares it to the recorded
instruction. That catches text edited after rendering. It cannot catch text
edited into the prompt file first, because re-rendering reads the same edited
file and reproduces the same bytes: `match`, honestly reported, about an
instruction nobody published.

`test_the_pre_render_edit_the_render_gate_cannot_see` is the issue's own
reproduction, run against both gates at once. It is the test the rest of this
file exists to support.
"""

import hashlib
import os
import tempfile
import unittest
from pathlib import Path

import yaml

from data_sheets_schema import prompt_registry as pr


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestStatusOfARecordedHash(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.prompt = self.root / "arm.md"
        self.prompt.write_text("# v3\n\n## Prompt body\nbody\n")
        self.reg = self.root / "canonical.yaml"
        pr.pin(self.prompt, "initial", registry=self.reg, today="2026-08-10")

    def tearDown(self):
        self.tmp.cleanup()

    def _pinned(self):
        return pr.entry_for(self.prompt, self.reg)["sha256"]

    def test_the_pinned_hash_is_canonical(self):
        st, why = pr.status_of_hash(self.prompt, self._pinned(), self.reg)
        self.assertEqual(pr.CANONICAL, st)
        self.assertIsNone(why)

    def test_a_hash_that_was_never_pinned_is_the_finding(self):
        st, why = pr.status_of_hash(self.prompt, _sha("something else"),
                                    self.reg)
        self.assertEqual(pr.UNCANONICAL, st)
        self.assertIn("not a published version", why)

    def test_a_previously_pinned_hash_is_superseded_not_a_finding(self):
        """Conditions are allowed to move. Reporting every run made under the
        prompt of the day as a defect would fail history for a rule that
        postdates it — and push whoever hit it toward silencing the check."""
        old = self._pinned()
        self.prompt.write_text("# v3\n\n## Prompt body\nbody, plus a rule\n")
        pr.pin(self.prompt, "added rule 4", registry=self.reg,
               today="2026-08-11")

        st, why = pr.status_of_hash(self.prompt, old, self.reg)
        self.assertEqual(pr.SUPERSEDED, st)
        self.assertIn("2026-08-11", why)
        self.assertEqual(pr.CANONICAL,
                         pr.status_of_hash(self.prompt, self._pinned(),
                                           self.reg)[0])

    def test_an_unregistered_path_is_reported_not_failed(self):
        st, _ = pr.status_of_hash(self.root / "other.md", _sha("x"), self.reg)
        self.assertEqual(pr.UNPINNED, st)

    def test_disk_status_reads_the_file(self):
        self.assertEqual(pr.CANONICAL, pr.disk_status(self.prompt, self.reg)[0])
        self.prompt.write_text("edited\n")
        st, why = pr.disk_status(self.prompt, self.reg)
        self.assertEqual(pr.UNCANONICAL, st)
        self.assertIn("arm.md", why)

    def test_a_deleted_pinned_file_is_missing_not_unpinned(self):
        """#437. A pinned file that is gone is evidence of an absence, not an
        absence of evidence — the condition's declared text no longer exists."""
        self.prompt.unlink()
        st, why = pr.disk_status(self.prompt, self.reg)
        self.assertEqual(pr.MISSING, st)
        self.assertIn("pinned but not on disk", why)

    def test_a_pinned_path_with_no_recorded_hash_is_missing(self):
        st, why = pr.status_of_hash(self.prompt, None, self.reg)
        self.assertEqual(pr.MISSING, st)
        self.assertIn("did not read", why)

    def test_an_unpinned_absent_path_stays_unpinned(self):
        st, _ = pr.disk_status(self.root / "never-existed.md", self.reg)
        self.assertEqual(pr.UNPINNED, st)


class TestPinning(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.prompt = self.root / "arm.md"
        self.prompt.write_text("one\n")
        self.reg = self.root / "canonical.yaml"

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_pin_requires_a_reason(self):
        """A diff that says only that a hash changed records nothing a reviewer
        could not compute themselves."""
        with self.assertRaises(ValueError):
            pr.pin(self.prompt, "", registry=self.reg)
        with self.assertRaises(ValueError):
            pr.pin(self.prompt, "   ", registry=self.reg)

    def test_rotation_keeps_the_previous_hash(self):
        pr.pin(self.prompt, "first", registry=self.reg, today="2026-08-10")
        first = pr.entry_for(self.prompt, self.reg)["sha256"]
        self.prompt.write_text("two\n")
        res = pr.pin(self.prompt, "second", registry=self.reg,
                     today="2026-08-12")

        entry = pr.entry_for(self.prompt, self.reg)
        self.assertEqual(first, res["previous"])
        self.assertNotEqual(first, entry["sha256"])
        self.assertEqual([{"sha256": first, "pinned_on": "2026-08-10",
                           "retired_on": "2026-08-12", "reason": "first"}],
                         entry["superseded"])

    def test_rotating_twice_keeps_both_ancestors(self):
        hashes = []
        for i, text in enumerate(("one\n", "two\n", "three\n")):
            self.prompt.write_text(text)
            pr.pin(self.prompt, f"v{i}", registry=self.reg,
                   today=f"2026-08-1{i}")
            hashes.append(_sha(text))
        entry = pr.entry_for(self.prompt, self.reg)
        self.assertEqual(hashes[:2],
                         [s["sha256"] for s in entry["superseded"]])
        for old in hashes[:2]:
            self.assertEqual(pr.SUPERSEDED,
                             pr.status_of_hash(self.prompt, old, self.reg)[0])

    def test_repinning_unchanged_bytes_is_a_no_op(self):
        """Otherwise a re-run of the pin command would retire a hash into the
        superseded list and pin the identical value over it."""
        pr.pin(self.prompt, "first", registry=self.reg)
        res = pr.pin(self.prompt, "again", registry=self.reg)
        self.assertEqual("unchanged", res["status"])
        self.assertNotIn("superseded", pr.entry_for(self.prompt, self.reg))

    def test_the_reason_is_stored_where_a_reviewer_will_read_it(self):
        pr.pin(self.prompt, "carries the scalar-range rule", registry=self.reg)
        self.assertIn("carries the scalar-range rule",
                      self.reg.read_text(encoding="utf-8"))

    def test_pinning_a_file_that_is_not_there_fails_loudly(self):
        with self.assertRaises(FileNotFoundError):
            pr.pin(self.root / "gone.md", "why", registry=self.reg)


class TestPinningUncommittedBytes(unittest.TestCase):
    """#438. `pinned_at_commit` is offered as the audit route — `git show
    <commit>:<path>` should reproduce the pinned bytes. Pinning an uncommitted
    edit would name a commit that hashes to something else, and be wrong for
    exactly the case the registry exists to catch."""

    def setUp(self):
        import subprocess
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = os.getcwd()
        self.addCleanup(os.chdir, self.cwd)
        self.addCleanup(self.tmp.cleanup)
        os.chdir(self.root)

        def git(*a):
            subprocess.run(["git", *a], check=True, capture_output=True)

        git("init", "-q")
        git("config", "user.email", "t@example.org")
        git("config", "user.name", "t")
        self.prompt = Path("arm.md")
        self.prompt.write_text("committed\n")
        git("add", "arm.md")
        git("commit", "-qm", "add")
        self.reg = Path("canonical.yaml")

    def test_a_clean_file_pins_and_the_commit_reproduces_it(self):
        import subprocess
        res = pr.pin(self.prompt, "initial", registry=self.reg)
        commit = pr.entry_for(self.prompt, self.reg)["pinned_at_commit"]
        blob = subprocess.run(["git", "show", f"{commit}:arm.md"],
                              capture_output=True, check=True).stdout
        self.assertEqual(hashlib.sha256(blob).hexdigest(), res["sha256"])

    def test_an_uncommitted_edit_is_refused(self):
        self.prompt.write_text("uncommitted edit\n")
        with self.assertRaises(ValueError) as ctx:
            pr.pin(self.prompt, "trying", registry=self.reg)
        self.assertIn("Commit the prompt first", str(ctx.exception))
        self.assertFalse(self.reg.exists(), "nothing should have been written")


class TestTheRealRegistry(unittest.TestCase):
    """The CI gate. Editing a prompt file without rotating its pin fails here —
    which is the whole mechanism: the edit and the declaration that it is now
    canonical are two acts, and the second is small enough to read."""

    def test_every_condition_prompt_is_pinned_and_at_its_pin(self):
        rows = pr.check_disk()
        self.assertTrue(rows, "no condition prompts found to check")
        bad = [r for r in rows if r["status"] != pr.CANONICAL]
        self.assertEqual([], bad,
                         "prompt file(s) not at their canonical hash; rotate "
                         "with `d4d api prompts pin --file … --reason …`")

    def test_every_condition_in_the_registry_has_a_prompt_pinned(self):
        from data_sheets_schema.api_runner import CONDITION_PROMPTS
        pinned = set(pr.registered_paths())
        for condition, path in CONDITION_PROMPTS.items():
            self.assertIn(pr.normalise(path), pinned,
                          f"condition {condition!r} has no canonical pin")


class TestTheRecordGate(unittest.TestCase):
    """`canonical_prompt_status` over a provenance record on disk."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = os.getcwd()
        # Registered before the chdir: a setUp that raises after it would
        # otherwise skip tearDown and leave the whole suite in a temp dir.
        self.addCleanup(os.chdir, self.cwd)
        self.addCleanup(self.tmp.cleanup)
        os.chdir(self.root)
        # The registry path is repo-relative, so a temp root plus chdir gives a
        # self-contained registry without patching module constants.
        self.prompt = Path("src/download/prompts/d4d_generic_arm_prompt_v3.md")
        self.prompt.parent.mkdir(parents=True)
        self.prompt.write_text(
            "# header\n\n## Prompt body\nGenerate a record for {PROJECT}.\n")
        pr.pin(self.prompt, "initial", today="2026-08-10")
        self.concat = Path("data/d4d_concatenated")
        self.label, self.method = "2026-08-10_generic-v3_rep1", "claudecode_agent"
        self.dir = self.concat / f"{self.method}_core" / self.label
        self.dir.mkdir(parents=True)


    def _write_record(self, files, request=None):
        rec = {"record_mode": "live", "prompts": {"hash_algorithm": "sha256",
                                                  "files": files}}
        if request:
            rec["prompts"]["request"] = request
        (self.dir / "P_provenance.yaml").write_text(yaml.safe_dump(rec))

    def _status(self):
        from data_sheets_schema.runs import canonical_prompt_status
        return canonical_prompt_status(self.method, self.label, "P",
                                       self.concat)

    def test_a_record_hashing_the_pinned_file_is_canonical(self):
        self._write_record([{"path": str(self.prompt),
                             "sha256": pr.sha256_of(self.prompt)}])
        self.assertEqual((pr.CANONICAL, None), self._status())

    def test_a_record_hashing_no_prompt_is_absent_not_a_finding(self):
        (self.dir / "P_provenance.yaml").write_text(
            yaml.safe_dump({"prompts": {"paths": None}}))
        self.assertEqual("absent", self._status()[0])

    def test_the_worst_status_across_several_files_wins(self):
        other = Path("src/download/prompts/d4d_tuned_arm_prompt.md")
        other.write_text("tuned\n")
        self._write_record([
            {"path": str(self.prompt), "sha256": pr.sha256_of(self.prompt)},
            {"path": str(other), "sha256": _sha("who knows")},
        ])
        # One unpinned neighbour must not be hidden behind a canonical one.
        self.assertEqual(pr.UNPINNED, self._status()[0])

    def test_a_missing_record_is_absent(self):
        self.assertEqual("absent", self._status()[0])

    def test_a_prompt_copied_to_another_path_does_not_escape_the_pin(self):
        """#436. The pin is keyed on path, so `cp` was the whole bypass: an
        edited copy is `unpinned` (not fatal), `condition_of` cannot name its
        condition, and the label still claims one. Coverage closes it."""
        evil = Path("my_prompt_copy.md")
        evil.write_text(self.prompt.read_text() + "\nCRITICAL SCOPE BOUNDARY\n")
        self._write_record([{"path": str(evil), "sha256": pr.sha256_of(evil)}])
        status, why = self._status()
        self.assertEqual(pr.UNCANONICAL, status)
        self.assertIn("hashes no condition prompt", why)

    def test_a_label_naming_no_condition_is_not_second_guessed(self):
        """Labels predating the convention name no condition. Failing them
        would punish history for a rule that postdates it."""
        from data_sheets_schema.runs import canonical_prompt_status
        label = "2026-08-10_unlabelled_rep1"
        d = self.concat / f"{self.method}_core" / label
        d.mkdir(parents=True)
        evil = Path("copy.md")
        evil.write_text("anything\n")
        (d / "P_provenance.yaml").write_text(yaml.safe_dump(
            {"prompts": {"files": [{"path": str(evil),
                                    "sha256": pr.sha256_of(evil)}]}}))
        self.assertEqual(pr.UNPINNED,
                         canonical_prompt_status(self.method, label, "P",
                                                 self.concat)[0])

    def test_the_known_label_condition_mismatch_stays_non_fatal(self):
        """Sixteen corpus records are labelled `generic-v3` and hash the pinned
        v1. That is #420, reported by `prompt_condition_mismatch` and never
        fatal on purpose — requiring the *claimed* condition's exact file would
        fail them retroactively through a side door."""
        v1 = Path("src/download/prompts/d4d_generic_arm_prompt.md")
        v1.write_text("# v1\n\n## Prompt body\nolder.\n")
        pr.pin(v1, "v1", today="2026-08-10")
        self._write_record([{"path": str(v1), "sha256": pr.sha256_of(v1)}])
        self.assertEqual((pr.CANONICAL, None), self._status())

    def test_the_pre_render_edit_the_render_gate_cannot_see(self):
        """#432's reproduction, both gates side by side.

        Add a project-specific paragraph to the generic prompt; render; run;
        record. `verify_request` re-renders from the same edited file, gets the
        same bytes, and says `match` — correctly, and uselessly. The pin is
        what makes the edit a finding.
        """
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.runs import verify_request

        self.prompt.write_text(
            "# header\n\n## Prompt body\nGenerate a record for {PROJECT}.\n"
            "CRITICAL SCOPE BOUNDARY: treat the pediatric cohort as out of "
            "scope for this project.\n")

        spec = RunSpec(project="P", arm="BASELINE", method=self.method,
                       bundle=Path("b.txt"), label=self.label,
                       condition="generic_v3", manifest_line="",
                       run_date="2026-08-10", runtime="Claude Code",
                       provider="Anthropic")
        sent = resolve_prompt(spec)
        self.assertIn("CRITICAL SCOPE BOUNDARY", sent)

        self._write_record(
            [{"path": str(self.prompt), "sha256": pr.sha256_of(self.prompt)}],
            request={"sha256": _sha(sent), "bytes": len(sent.encode()),
                     "spec": {"condition": "generic_v3", "arm": "BASELINE",
                              "bundle": "b.txt", "manifest_line": "",
                              "run_date": "2026-08-10",
                              "runtime": "Claude Code",
                              "provider": "Anthropic"}})

        self.assertEqual("match",
                         verify_request(self.method, self.label, "P",
                                        self.concat)[0],
                         "the render gate is expected to be satisfied here — "
                         "that is why #432 exists")
        status, why = self._status()
        self.assertEqual(pr.UNCANONICAL, status)
        self.assertIn("not a published version", why)

    def test_the_same_run_under_the_published_prompt_passes_both(self):
        """The negative control: without the edit, nothing is reported. A gate
        that fires on the unedited case would be noise, not evidence."""
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        from data_sheets_schema.runs import verify_request

        spec = RunSpec(project="P", arm="BASELINE", method=self.method,
                       bundle=Path("b.txt"), label=self.label,
                       condition="generic_v3", manifest_line="",
                       run_date="2026-08-10", runtime="Claude Code",
                       provider="Anthropic")
        sent = resolve_prompt(spec)
        self._write_record(
            [{"path": str(self.prompt), "sha256": pr.sha256_of(self.prompt)}],
            request={"sha256": _sha(sent), "bytes": len(sent.encode()),
                     "spec": {"condition": "generic_v3", "arm": "BASELINE",
                              "bundle": "b.txt", "manifest_line": "",
                              "run_date": "2026-08-10",
                              "runtime": "Claude Code",
                              "provider": "Anthropic"}})
        self.assertEqual("match", verify_request(self.method, self.label, "P",
                                                 self.concat)[0])
        self.assertEqual((pr.CANONICAL, None), self._status())


class TestTheCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = os.getcwd()
        self.addCleanup(os.chdir, self.cwd)
        self.addCleanup(self.tmp.cleanup)
        os.chdir(self.root)
        self.prompt = Path("src/download/prompts/d4d_generic_arm_prompt.md")
        self.prompt.parent.mkdir(parents=True)
        self.prompt.write_text("# v1\n\n## Prompt body\nbody\n")
        for name in ("_v2", "_v3", "_v4"):
            p = self.prompt.with_name(f"d4d_generic_arm_prompt{name}.md")
            p.write_text(f"# {name}\n\n## Prompt body\nbody\n")
        self.prompt.with_name("d4d_tuned_arm_prompt.md").write_text("# tuned\n")


    def _run(self, *args):
        from click.testing import CliRunner
        from data_sheets_schema.cli.api import api
        return CliRunner().invoke(api, ["prompts", *args])

    def _pin_all(self):
        for p in sorted(self.prompt.parent.glob("*.md")):
            self._run("pin", "--file", str(p), "--reason", "initial")

    def test_an_undeclared_prompt_file_fails_the_repo_gate(self):
        """A condition prompt nobody pinned is text that was never declared —
        the hole itself, not a gap in it. The record gate is more forgiving
        because a record may name a prompt the registry does not cover; the
        working tree has no such excuse."""
        r = self._run("check", "--strict")
        self.assertEqual(1, r.exit_code, r.output)
        self.assertIn("unpinned", r.output)

    def test_check_fails_strictly_once_a_pinned_file_is_edited(self):
        self._pin_all()
        self.assertEqual(0, self._run("check", "--strict").exit_code)

        self.prompt.write_text("# v1\n\n## Prompt body\nbody, edited\n")
        r = self._run("check", "--strict")
        self.assertEqual(1, r.exit_code, r.output)
        self.assertIn("uncanonical", r.output)
        self.assertIn("d4d api prompts pin", r.output)

    def test_pin_refuses_without_a_reason(self):
        r = self._run("pin", "--file", str(self.prompt))
        self.assertNotEqual(0, r.exit_code)

    def test_pinning_the_edit_is_how_it_is_resolved(self):
        self._pin_all()
        self.prompt.write_text("# v1\n\n## Prompt body\nbody, edited\n")
        r = self._run("pin", "--file", str(self.prompt), "--reason",
                      "rule 4 added; re-baselines the arm")
        self.assertEqual(0, r.exit_code, r.output)
        self.assertIn("superseded", r.output)
        self.assertEqual(0, self._run("check", "--strict").exit_code)


if __name__ == "__main__":
    unittest.main()
