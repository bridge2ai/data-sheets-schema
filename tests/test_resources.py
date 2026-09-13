"""Resources resolve from any working directory, and records keep storing
the repository-relative path (#1301, #673)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class TestResourcesFromElsewhere(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="d4d-resources-")
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._cwd)

    def test_the_checkout_is_recognised(self):
        from data_sheets_schema import resources
        self.assertEqual(resources.CHECKOUT_ROOT, ROOT)
        self.assertTrue(resources.is_checkout())

    def test_a_prompt_resolves_from_another_directory(self):
        from data_sheets_schema.resources import resource_path
        p = resource_path("src/download/prompts/d4d_generic_arm_prompt_v9.md")
        self.assertTrue(p.is_absolute())
        self.assertTrue(p.exists(), p)
        self.assertEqual(p, ROOT / "src/download/prompts/d4d_generic_arm_prompt_v9.md")

    def test_the_runner_constants_are_usable_from_another_directory(self):
        """The constants keep their repository-relative spelling — what a
        record stores — and every reader resolves them when it reads."""
        from data_sheets_schema import api_runner, prompt_registry, provenance, schema_digest
        from data_sheets_schema.resources import resource_path
        self.assertFalse(api_runner.GENERIC_PROMPT_V9.is_absolute())
        self.assertTrue(resource_path(api_runner.GENERIC_PROMPT_V9).exists())
        self.assertTrue(resource_path(prompt_registry.REGISTRY).exists())
        self.assertTrue(schema_digest.resolve_schema(provenance.FULL_SCHEMA).exists())
        self.assertTrue(provenance.record_schema_path().exists())
        self.assertIn("## Prompt body", resource_path(api_runner.GENERIC_PROMPT_V9).read_text())
        self.assertTrue(api_runner.prompt_body(api_runner.GENERIC_PROMPT_V9))
        facts = provenance.playbook_facts()
        self.assertTrue(all(f["exists"] and f["sha256"] for f in facts["files"]), facts)
        self.assertTrue(all(not Path(f["path"]).is_absolute() for f in facts["files"]))

    def test_a_staged_tree_is_authoritative_for_what_it_lacks(self):
        """A fixture that carries the prompts directory but not one prompt
        reads that prompt as absent — never the checkout's copy."""
        from data_sheets_schema import prompt_registry as pr
        from data_sheets_schema.resources import resource_path
        (Path(self.tmp) / "src/download/prompts").mkdir(parents=True)
        rel = Path("src/download/prompts/d4d_generic_arm_prompt_v9.md")
        self.assertEqual(resource_path(rel), rel)
        self.assertFalse(resource_path(rel).exists())
        self.assertIsNone(pr.sha256_of(rel))

    def test_the_recorded_form_stays_repository_relative(self):
        """A pin key or a record path never depends on where the process ran."""
        from data_sheets_schema import prompt_registry, provenance
        from data_sheets_schema.resources import repo_relative
        absolute = ROOT / "src/download/prompts/d4d_generic_arm_prompt_v9.md"
        self.assertEqual(repo_relative(absolute), "src/download/prompts/d4d_generic_arm_prompt_v9.md")
        self.assertEqual(prompt_registry.normalise(absolute), "src/download/prompts/d4d_generic_arm_prompt_v9.md")
        self.assertEqual(provenance.repo_relative(absolute), "src/download/prompts/d4d_generic_arm_prompt_v9.md")
        # Under the working directory but outside every root: relative to
        # the working directory, as the registry always keyed a staged
        # fixture; under none of them: absolute, as before.
        here = Path(self.tmp) / "x.md"
        here.write_text("x")
        self.assertEqual(repo_relative(here), "x.md")
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "y.md"
            outside.write_text("y")
            self.assertEqual(Path(repo_relative(outside)), outside.resolve())

    def test_the_corpus_is_not_a_resource(self):
        """A record or bundle missing from the working directory must not
        silently resolve to the checkout's copy."""
        from data_sheets_schema.resources import is_resource, resource_path
        rel = Path("data/d4d_concatenated/claudecode_api/x/P_d4d.yaml")
        self.assertFalse(is_resource(rel))
        self.assertEqual(resource_path(rel), rel)
        self.assertTrue(is_resource("src/download/prompts/x.md"))
        self.assertTrue(is_resource(".claude/commands/d4d-full-core.md"))
        self.assertTrue(is_resource("data/rubric/rubric10.txt"))

    def test_a_staged_copy_in_the_working_directory_wins(self):
        """A fixture tree staged where the process runs is read — and written
        — in preference to the checkout's file (the failure the import-time
        form had: a test's `pin` rewrote the real registry)."""
        from data_sheets_schema.resources import resource_path
        staged = Path(self.tmp) / "src/download/prompts/canonical_hashes.yaml"
        staged.parent.mkdir(parents=True)
        staged.write_text("files: {}\n")
        got = resource_path("src/download/prompts/canonical_hashes.yaml")
        self.assertFalse(got.is_absolute())
        self.assertEqual(got.resolve(), staged.resolve())

    def test_the_validator_command_does_not_need_poetry(self):
        from data_sheets_schema.resources import linkml_validate
        cmd = linkml_validate()
        self.assertNotEqual(cmd[0], "poetry")
        self.assertTrue(Path(cmd[0]).exists(), cmd)

    def test_a_pinned_prompt_is_canonical_from_another_directory(self):
        from data_sheets_schema import prompt_registry as pr
        st, why = pr.disk_status(pr.normalise(ROOT / "src/download/prompts/d4d_generic_arm_prompt_v9.md"))
        self.assertEqual(st, pr.CANONICAL, why)

    def test_the_digest_renders_from_another_directory(self):
        from data_sheets_schema import schema_digest
        self.assertIn("## `title`", schema_digest.digest_text("Dataset"))

    def test_an_unwritable_ledger_is_reported_not_fatal(self):
        """Under site-packages the digest inventory may be read-only; a run
        must not die on it, and the non-recording must be said."""
        import warnings
        from data_sheets_schema import schema_digest
        from unittest import mock
        ledger = Path(self.tmp) / "digest_inventory.yaml"        # not on disk yet
        with warnings.catch_warnings(record=True) as caught, \
                mock.patch.object(Path, "write_text", side_effect=PermissionError("read-only")):
            warnings.simplefilter("always")
            self.assertFalse(schema_digest.record_inventory(ledger=ledger))
        self.assertTrue(any("digest inventory not recorded" in str(w.message) for w in caught), caught)


class TestRoundOne(unittest.TestCase):
    """The #1455 round-1 findings, each pinned."""

    def setUp(self):
        self._cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="d4d-resources-")
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._cwd)

    def test_dotdot_never_reaches_the_checkout_corpus(self):
        """#1482: `src/../data/…` is the corpus, not a resource; #1481: a
        `..` spelling of a prompt normalizes to its canonical form."""
        from data_sheets_schema.resources import is_resource, repo_relative, resource_path
        escape = Path("src/../data/d4d_concatenated/claudecode/VOICE_d4d.yaml")
        self.assertFalse(is_resource(escape))
        self.assertEqual(resource_path(escape), escape)                  # the caller's path, as given
        self.assertFalse(is_resource("src/../README.md"))
        self.assertFalse(is_resource("../src/download/prompts/x.md"))
        # A `..` spelling is canonicalized by the filesystem, never lexically
        # (#1528): from the checkout it names the canonical prompt; from here
        # it names nothing, and says so.
        alias = "src/download/../download/prompts/d4d_generic_arm_prompt_v9.md"
        self.assertFalse(resource_path(alias).exists())
        os.chdir(ROOT)
        self.assertEqual(repo_relative(alias), "src/download/prompts/d4d_generic_arm_prompt_v9.md")
        self.assertTrue(resource_path(alias).exists())
        os.chdir(self.tmp)

    def test_dotdot_follows_the_filesystem_not_the_spelling(self):
        """#1528: `.venv/../pyproject.toml` through a symlinked `.venv` is the
        other checkout's file, and the readers hash that file."""
        import hashlib
        from data_sheets_schema import prompt_registry
        os.chdir(ROOT)
        link = ROOT / ".venv"
        if not link.is_symlink():
            self.skipTest("no symlinked .venv to walk through")
        p = Path(".venv/../pyproject.toml")
        self.assertEqual(prompt_registry.sha256_of(p), hashlib.sha256(p.read_bytes()).hexdigest())

    def test_a_staged_file_has_one_recorded_identity(self):
        """#1536"""
        from data_sheets_schema.resources import repo_relative
        staged = Path(self.tmp) / "src/download/prompts/x.md"
        staged.parent.mkdir(parents=True)
        staged.write_text("x")
        rel = "src/download/prompts/x.md"
        self.assertEqual(repo_relative(rel, cwd=False), repo_relative(staged, cwd=False))
        self.assertEqual(Path(repo_relative(rel, cwd=False)), staged.resolve())
        self.assertEqual(repo_relative(rel, cwd=True), rel)              # the registry's key
        # A shipped file read through the fallback keeps its logical spelling.
        self.assertEqual(repo_relative("src/download/prompts/d4d_generic_arm_prompt_v9.md", cwd=False),
                         "src/download/prompts/d4d_generic_arm_prompt_v9.md")

    def test_a_directory_and_its_files_answer_alike(self):
        """#1535: a depth-two marker establishes nothing; a staged depth-three
        directory is authoritative for itself and everything under it."""
        from data_sheets_schema.resources import resource_path
        (Path(self.tmp) / "src/data_sheets_schema").mkdir(parents=True)          # the old root marker only
        d = Path("src/data_sheets_schema/schema")
        self.assertTrue(resource_path(d).is_dir())                              # falls back
        self.assertTrue(resource_path(d / "data_sheets_schema_all.yaml").exists())
        (Path(self.tmp) / "src/download/prompts").mkdir(parents=True)          # a staged prompts tree
        c = Path("src/download/prompts/components")
        self.assertFalse(resource_path(c).exists())
        self.assertFalse(resource_path(c / "CHORUS.md").exists())
        from data_sheets_schema import prompt_registry as pr
        self.assertEqual([f for f in pr.prompt_files() if "components/" in f.as_posix()], [])

    def test_a_resource_directory_resolves_like_its_files(self):
        """#1488"""
        from data_sheets_schema.resources import is_resource, resource_path
        self.assertTrue(is_resource("data/rubric"))
        self.assertTrue(resource_path("data/rubric").is_dir())
        self.assertTrue(resource_path("project").is_dir())
        self.assertFalse(is_resource("data/rubrics"))
        self.assertFalse(is_resource("data"))

    def test_an_unrelated_installed_file_stays_absolute(self):
        """#1487"""
        import linkml_runtime
        from data_sheets_schema.resources import repo_relative
        other = Path(linkml_runtime.__file__).resolve()
        self.assertEqual(Path(repo_relative(other)), other)
        self.assertEqual(Path(repo_relative(other, cwd=False)), other)

    def test_prompt_facts_and_playbooks_are_present_from_elsewhere(self):
        """#1479: presence and size are read where the file is, and drift is
        checked there."""
        from data_sheets_schema import api_runner, provenance, runs
        facts = provenance.prompt_facts([api_runner.GENERIC_PROMPT_V9])["files"][0]
        self.assertTrue(facts["exists"]); self.assertGreater(facts["bytes"], 0)
        self.assertEqual(facts["path"], "src/download/prompts/d4d_generic_arm_prompt_v9.md")
        self.assertTrue(provenance.referenced_playbooks())
        import yaml
        rec = Path(self.tmp) / "data/d4d_concatenated/claudecode_api_core/L/P_provenance.yaml"
        rec.parent.mkdir(parents=True)
        rec.write_text(yaml.safe_dump({"playbooks": provenance.playbook_facts()}), encoding="utf-8")
        status, why = runs.playbook_drift("claudecode_api", "L", "P", Path("data/d4d_concatenated"))
        self.assertEqual(status, runs.PLAYBOOK_UNCHANGED if hasattr(runs, "PLAYBOOK_UNCHANGED") else status, why)
        self.assertNotIn("no longer present", why or "")
        self.assertNotIn("drift", status)

    def test_the_strict_prompt_check_sees_the_components_from_elsewhere(self):
        """#1480"""
        from data_sheets_schema import prompt_registry as pr
        files = pr.prompt_files()
        self.assertTrue(any("components/" in f.as_posix() for f in files), files)
        self.assertTrue(all(not f.is_absolute() for f in files))
        rows = pr.check_disk()
        self.assertEqual([r["path"] for r in rows if r["status"] != pr.CANONICAL], [])

    def test_pin_refuses_a_registry_that_is_not_in_the_working_tree(self):
        """#1484"""
        from data_sheets_schema import prompt_registry as pr
        with self.assertRaises(ValueError) as caught:
            pr.pin("src/download/prompts/d4d_generic_arm_prompt_v9.md", "must not write the checkout's registry")
        self.assertIn("not in the working tree", str(caught.exception))

    def test_readers_agree_on_an_authoritative_absence(self):
        """#1483: no by-name fallback after `resource_path` said absent (a
        staged depth-three schema directory is authoritative)."""
        from data_sheets_schema import provenance, schema_digest
        from data_sheets_schema.resources import resource_path
        (Path(self.tmp) / "src/data_sheets_schema/schema").mkdir(parents=True)
        rel = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
        self.assertEqual(resource_path(rel), rel)
        self.assertEqual(schema_digest.resolve_schema(rel), rel)
        self.assertFalse(provenance.record_schema_path().exists())

    def test_the_sync_gate_reads_in_sync_from_elsewhere(self):
        """#1478"""
        from data_sheets_schema import schema_sync
        rows = schema_sync.check()
        self.assertTrue(all(r["status"] == schema_sync.IN_SYNC for r in rows), rows)

    def test_the_validator_command_never_searches_the_path(self):
        """#1486"""
        import sys
        from unittest import mock
        from data_sheets_schema import resources
        with mock.patch.object(Path, "exists", return_value=False):
            cmd = resources.linkml_validate()
        self.assertEqual(cmd[0], sys.executable)
        self.assertIn("linkml.validator.cli", cmd[-1])

    def test_the_recorder_guard_refuses_only_a_subdirectory_of_the_checkout(self):
        """#1502 (the #672 guard as narrowed by #1301)."""
        import click
        from data_sheets_schema.cli.provenance import _require_repo_root_cwd
        _require_repo_root_cwd("t")                                   # a directory outside the checkout
        os.chdir(ROOT)
        _require_repo_root_cwd("t")                                   # the root
        os.chdir(ROOT / "tests")
        with self.assertRaises(click.ClickException) as caught:
            _require_repo_root_cwd("t")
        self.assertIn("not a directory inside it", str(caught.exception))

    def test_a_validator_that_says_nothing_or_cannot_start_is_a_failure(self):
        """#1524, #1525"""
        from subprocess import CompletedProcess
        from unittest import mock
        from data_sheets_schema import api_runner as a
        schema = "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
        with mock.patch.object(a.subprocess, "run", return_value=CompletedProcess([], -9, "", "")):
            lines, failure = a._validator_lines(Path("r.yaml"), schema, "Dataset")
        self.assertIsNone(lines); self.assertIn("no output", failure)
        finding = "[ERROR] [r.yaml/0] 'does not exist.' is not of type 'object' in /creators/0"
        with mock.patch.object(a.subprocess, "run", return_value=CompletedProcess([], 1, finding, "")):
            lines, failure = a._validator_lines(Path("r.yaml"), schema, "Dataset")
        self.assertEqual(lines, [finding]); self.assertIsNone(failure)
        crash = "Traceback (most recent call last):\n  File x\nModuleNotFoundError: No module named 'linkml'"
        with mock.patch.object(a.subprocess, "run", return_value=CompletedProcess([], 1, "", crash)):
            lines, failure = a._validator_lines(Path("r.yaml"), schema, "Dataset")
        self.assertIsNone(lines); self.assertIn("did not run", failure)

    def test_the_deterministic_config_is_a_resource_and_its_absence_is_said(self):
        """#1529"""
        from unittest import mock
        from data_sheets_schema import api_runner, provenance
        self.assertTrue(provenance.load_generation_config())                       # from here: shipped copy
        s = api_runner._model_settings()
        self.assertEqual(s["config_path"], str(provenance.DETERMINISTIC_CONFIG))
        with mock.patch.object(api_runner, "load_generation_config", return_value={}):
            s = api_runner._model_settings()
        self.assertIsNone(s["config_path"]); self.assertIn("not found", s["config_note"])

    def test_the_record_names_the_resource_root_not_the_working_directorys_repository(self):
        """#1550"""
        import subprocess
        from data_sheets_schema import provenance
        from data_sheets_schema.resources import CHECKOUT_ROOT
        subprocess.run(["git", "init", "-q"], cwd=self.tmp, check=True)
        subprocess.run(["git", "-c", "user.email=t@example.org", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "x"],
                       cwd=self.tmp, check=True)
        other = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.tmp, capture_output=True, text=True).stdout.strip()
        facts = provenance.repo_facts()
        self.assertEqual(facts["resource_kind"], "checkout")
        self.assertEqual(Path(facts["resource_root"]), CHECKOUT_ROOT)
        self.assertNotEqual(facts["commit"], other)
        here = subprocess.run(["git", "rev-parse", "HEAD"], cwd=CHECKOUT_ROOT, capture_output=True, text=True).stdout.strip()
        self.assertEqual(facts["commit"], here)

    def test_agent_definitions_resolve_from_elsewhere(self):
        """#1553"""
        from data_sheets_schema import agent_pin
        p = agent_pin.agent_path("d4d-review-record")
        self.assertTrue(p.exists())


class TestRoundThree(unittest.TestCase):
    """The #1455 round-3 findings (#1570–#1579)."""

    def setUp(self):
        self._cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="d4d-resources-")
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._cwd)

    def test_schema_readers_follow_the_filesystem_through_a_symlink(self):
        """#1570"""
        import hashlib
        from data_sheets_schema.schema_snapshot import capture_schema
        os.chdir(ROOT)
        if not (ROOT / ".venv").is_symlink():
            self.skipTest("no symlinked .venv to walk through")
        p = Path(".venv/../src/data_sheets_schema/schema/d4d_generation_record.yaml")
        if not p.exists():
            self.skipTest("the other checkout carries no record schema")
        snap = capture_schema(p)
        self.assertEqual(Path(snap.key[0]).resolve(), p.resolve())
        self.assertEqual(hashlib.sha256(snap.sources[0][2]).hexdigest(), hashlib.sha256(p.read_bytes()).hexdigest())

    def test_a_crash_after_findings_is_still_a_crash(self):
        """#1572"""
        from data_sheets_schema.api_runner import _validator_did_not_run
        self.assertTrue(_validator_did_not_run("[ERROR] [r/0] invalid\nTraceback (most recent call last):\nRuntimeError: boom"))
        self.assertTrue(_validator_did_not_run("Usage: -c [OPTIONS] [DATA_SOURCES]...\nError: Invalid value"))
        self.assertFalse(_validator_did_not_run("[ERROR] [r/0] 'does not exist.' is not of type 'object' in /creators/0"))

    def test_a_staged_symlinked_prompt_has_one_identity_for_registry_and_record(self):
        """#1573"""
        from data_sheets_schema import prompt_registry as pr, provenance
        # The alias points at a third tree — outside the checkout, the
        # package and this directory — so the branch #1573 changed is the
        # one exercised: both spellings must resolve to that tree's file
        # (#1624; the first version aliased the checkout, which the pre-fix
        # fast path satisfied too).
        elsewhere = Path(self.tmp) / "elsewhere" / "prompts"; elsewhere.mkdir(parents=True)
        (elsewhere / "d4d_generic_arm_prompt_v9.md").write_text("# staged\n\n## Prompt body\nbody\n", encoding="utf-8")
        (Path(self.tmp) / "src/download").mkdir(parents=True)
        os.symlink(elsewhere, Path(self.tmp) / "src/download/prompts")
        rel = "src/download/prompts/d4d_generic_arm_prompt_v9.md"
        physical = (elsewhere / "d4d_generic_arm_prompt_v9.md").resolve()
        # The registry keys a staged tree's file relative to the working
        # directory (#1536); the record stores it absolute (`cwd=False`);
        # each identity is the same for both spellings, and neither is the
        # shipped file's relative spelling.
        self.assertEqual(pr.normalise(rel), pr.normalise(Path(self.tmp) / rel))
        self.assertEqual(pr.normalise(rel), physical.relative_to(Path(self.tmp).resolve()).as_posix())
        self.assertEqual(provenance.repo_relative(rel), provenance.repo_relative(Path(self.tmp) / rel))
        self.assertEqual(provenance.repo_relative(rel), physical.as_posix())
        self.assertNotEqual(pr.normalise(rel), rel)

    def test_an_implicit_registry_that_resolves_to_the_checkouts_is_refused(self):
        """#1576"""
        from data_sheets_schema import prompt_registry as pr
        (Path(self.tmp) / "src/download").mkdir(parents=True)
        os.symlink(ROOT / "src/download/prompts", Path(self.tmp) / "src/download/prompts")
        with self.assertRaises(ValueError) as caught:
            pr.pin("src/download/prompts/d4d_generic_arm_prompt_v9.md", "must not write through the alias")
        self.assertIn("not in the working tree", str(caught.exception))

    def test_pin_metadata_names_the_blob_and_refuses_untracked_files(self):
        """#1574, #1575"""
        import subprocess
        from data_sheets_schema import prompt_registry as pr
        repo = Path(self.tmp) / "repo"; repo.mkdir()
        git = lambda *a: subprocess.run(["git", "-c", "user.email=t@example.org", "-c", "user.name=t", *a], cwd=repo, check=True, capture_output=True)
        git("init", "-q")
        (repo / "nested").mkdir(); (repo / "nested" / "p.md").write_text("# x\n\n## Prompt body\nbody\n")
        (repo / ".gitignore").write_text("ignored/\n")
        git("add", "."); git("commit", "-q", "-m", "x")
        # An *ignored* file: status reads clean, yet git holds no blob for it
        # (an untracked one reads dirty and is refused as an uncommitted edit).
        (repo / "nested" / "ignored").mkdir(); (repo / "nested" / "ignored" / "loose.md").write_text("never in history\n")
        reg = Path(self.tmp) / "registry.yaml"
        entry = pr.pin(repo / "nested" / "p.md", "tracked", registry=reg)
        pinned = pr.entry_for(repo / "nested" / "p.md", reg)
        self.assertIsNotNone(pinned["pinned_at_commit"])
        self.assertEqual(pinned["pinned_blob_path"], "nested/p.md")
        self.assertEqual(Path(pinned["pinned_in_repository"]).resolve(), repo.resolve())
        blob = subprocess.run(["git", "show", f"{pinned['pinned_at_commit']}:{pinned['pinned_blob_path']}"],
                              cwd=repo, capture_output=True, text=True, check=True).stdout
        self.assertEqual(blob, "# x\n\n## Prompt body\nbody\n")                   # the audit route works
        pr.pin(repo / "nested" / "ignored" / "loose.md", "ignored", registry=reg)
        loose = pr.entry_for(repo / "nested" / "ignored" / "loose.md", reg)
        self.assertIsNone(loose["pinned_at_commit"])
        self.assertIn("not tracked", loose["commit_unavailable"])

    def test_a_foreign_pyproject_is_not_this_checkout(self):
        """#1577"""
        from data_sheets_schema.resources import _is_our_checkout
        other = Path(self.tmp) / "proj"; (other / "src" / "data_sheets_schema").mkdir(parents=True)
        (other / "pyproject.toml").write_text('[tool.poetry]\nname = "someone-elses"\n')
        self.assertFalse(_is_our_checkout(other))
        self.assertTrue(_is_our_checkout(ROOT))


class TestClaudeRoundThree(unittest.TestCase):
    """The Claude round-3 findings on #1455 (#1588–#1593)."""

    def setUp(self):
        self._cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="d4d-resources-")
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._cwd)

    def _stage_checkout(self, name: str, *, git: bool) -> Path:
        """A second checkout of this project: our `pyproject.toml`, the source
        layout, one playbook — and its own repository when `git`."""
        import subprocess
        repo = Path(self.tmp) / name
        (repo / "src" / "data_sheets_schema").mkdir(parents=True)
        (repo / ".claude" / "commands").mkdir(parents=True)
        (repo / "pyproject.toml").write_text('[tool.poetry]\nname = "data-sheets-schema"\n', encoding="utf-8")
        (repo / ".claude" / "commands" / "d4d-uniform-rules.md").write_text("# the worktree's rules\n", encoding="utf-8")
        if git:
            run = lambda *a: subprocess.run(["git", "-c", "user.email=t@example.org", "-c", "user.name=t", *a],
                                            cwd=repo, check=True, capture_output=True)
            run("init", "-q"); run("add", "."); run("commit", "-q", "-m", "x")
        return repo

    def test_a_second_checkout_as_the_working_directory_is_the_resource_root(self):
        """#1588: code from one checkout, cwd another — the record names the
        cwd's commit, keeps its files repository-relative, and the root guard
        refuses a subdirectory of it."""
        import hashlib
        import subprocess
        import click
        from data_sheets_schema import provenance
        from data_sheets_schema.cli._repo_utils import get_repo_root
        from data_sheets_schema.cli.provenance import _require_repo_root_cwd
        from data_sheets_schema.resources import CHECKOUT_ROOT, cwd_checkout, repo_relative, resource_root
        repo = self._stage_checkout("wt", git=True)
        os.chdir(repo)
        self.assertEqual(cwd_checkout(), repo.resolve())
        self.assertEqual(resource_root(), (repo.resolve(), "checkout"))
        self.assertEqual(get_repo_root(), repo.resolve())
        facts = provenance.repo_facts()
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
        self.assertEqual((facts["commit"], facts["dirty"], Path(facts["resource_root"])), (head, False, repo.resolve()))
        self.assertNotEqual(facts["commit"],
                            subprocess.run(["git", "rev-parse", "HEAD"], cwd=CHECKOUT_ROOT, capture_output=True, text=True).stdout.strip())
        # The playbook is the cwd's, hashed as the cwd's bytes, recorded relative — the
        # commit the record names reproduces the hash it records.
        rel = ".claude/commands/d4d-uniform-rules.md"
        self.assertEqual(repo_relative(rel, cwd=False), rel)
        self.assertEqual(repo_relative(str(repo / rel), cwd=False), rel)
        entry = next(e for e in provenance.playbook_facts()["files"] if e["path"].endswith("d4d-uniform-rules.md"))
        self.assertEqual(entry["path"], rel)
        self.assertEqual(entry["sha256"], hashlib.sha256(b"# the worktree's rules\n").hexdigest())
        blob = subprocess.run(["git", "show", f"{facts['commit']}:{rel}"], cwd=repo, capture_output=True, text=True).stdout
        self.assertEqual(hashlib.sha256(blob.encode()).hexdigest(), entry["sha256"])
        _require_repo_root_cwd("t")                                   # the root of a second checkout
        (repo / "sub").mkdir(); os.chdir(repo / "sub")
        with self.assertRaises(click.ClickException):
            _require_repo_root_cwd("t")                               # inside it (#672, generalised)

    def test_a_checkout_git_cannot_answer_for_records_unknown_not_clean(self):
        """#1591"""
        from data_sheets_schema import provenance
        repo = self._stage_checkout("exported", git=False)
        os.chdir(repo)
        facts = provenance.repo_facts()
        self.assertEqual((facts["commit"], facts["dirty"], facts["dirty_file_count"], facts["resource_kind"]),
                         (None, None, None, "checkout"))
        self.assertIn("unknown, not clean", facts["note"])

    def test_a_validator_crash_on_the_record_is_a_finding_about_the_record(self):
        """#1589: a YAML the loader rejects names the file in the traceback —
        the validator ran, on that record; a crash that never opened it did not."""
        from data_sheets_schema.api_runner import FULL_SCHEMA_PATH, _validator_did_not_run, _validator_lines
        bad = Path(self.tmp) / "bad.yaml"
        bad.write_text("id: x\ntitle: [unclosed\n", encoding="utf-8")
        parser = ("Traceback (most recent call last):\n  File \"x.py\", line 1, in <module>\n"
                  "yaml.parser.ParserError: while parsing a flow sequence\n"
                  f"  in \"{bad}\", line 2, column 8\nexpected ',' or ']', but got '<stream end>'\n")
        self.assertFalse(_validator_did_not_run(parser, bad))
        self.assertTrue(_validator_did_not_run(parser))                # no record named: as before
        self.assertTrue(_validator_did_not_run("Traceback (most recent call last):\nModuleNotFoundError: No module named 'linkml'\n", bad))
        self.assertTrue(_validator_did_not_run(f"Traceback (most recent call last):\nFileNotFoundError: [Errno 2] No such file or directory: '{bad}'\n", bad))
        os.chdir(ROOT)
        findings, failure = _validator_lines(bad, FULL_SCHEMA_PATH, "Dataset")
        self.assertIsNone(failure, failure)
        self.assertTrue(findings and any("ParserError" in l or "while parsing" in l for l in findings), findings)

    def test_rocrate_normalize_and_map_keep_their_help(self):
        """#1590"""
        from click.testing import CliRunner
        from data_sheets_schema.cli.rocrate import rocrate
        for name, text in (("normalize", "Normalize upstream RO-Crate packages"), ("map", "Map a crate to D4D")):
            r = CliRunner().invoke(rocrate, [name, "--help"])
            self.assertEqual(r.exit_code, 0, r.output)
            self.assertIn(text, r.output)

    @unittest.skipUnless(__import__("shutil").which("poetry"), "poetry is not installed")
    def test_the_lock_and_the_metadata_agree(self):
        """#1593: no extra names a dependency the main table does not declare."""
        import subprocess
        r = subprocess.run(["poetry", "check", "--lock"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class TestCodexRoundFour(unittest.TestCase):
    """The Codex round-4 findings on #1455 (#1617–#1625)."""

    def setUp(self):
        self._cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="d4d-resources-")
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._cwd)

    def _second_checkout(self, name="wt", *, git=True) -> Path:
        import subprocess
        repo = Path(self.tmp) / name
        (repo / "src" / "data_sheets_schema").mkdir(parents=True)
        (repo / ".claude" / "commands").mkdir(parents=True)
        (repo / "pyproject.toml").write_text('[tool.poetry]\nname = "data-sheets-schema"\n', encoding="utf-8")
        (repo / ".claude" / "commands" / "d4d-uniform-rules.md").write_text("# the second checkout's rules\n", encoding="utf-8")
        if git:
            run = lambda *a: subprocess.run(["git", "-c", "user.email=t@example.org", "-c", "user.name=t", *a],
                                            cwd=repo, check=True, capture_output=True)
            run("init", "-q"); run("add", "."); run("commit", "-q", "-m", "x")
        return repo

    def test_a_checkout_is_authoritative_for_its_absences(self):
        """#1617: from a second checkout no resource is read from the importing one."""
        from data_sheets_schema import provenance
        from data_sheets_schema.resources import resource_path
        repo = self._second_checkout(); os.chdir(repo)
        for rel in (".claude/commands/d4d-full-core.md", "src/download/prompts/d4d_generic_arm_prompt_v9.md",
                    "data/rubric/rubric10.txt", ".github/workflows/d4d_assistant_deterministic.config"):
            self.assertEqual(resource_path(rel), Path(rel))
            self.assertFalse(resource_path(rel).exists(), rel)
        entries = {e["path"]: e for e in provenance.playbook_facts()["files"]}
        self.assertTrue(entries[".claude/commands/d4d-uniform-rules.md"]["exists"])
        absent = [p for p, e in entries.items() if not e["exists"]]
        self.assertTrue(absent and all(e["sha256"] is None for p, e in entries.items() if p in absent), entries)
        self.assertEqual(len(entries), len(provenance.playbook_facts()["files"]))

    def test_another_checkouts_absolute_file_keeps_its_identity(self):
        """#1618"""
        from data_sheets_schema import provenance
        from data_sheets_schema.resources import CHECKOUT_ROOT
        repo = self._second_checkout(); os.chdir(repo)
        rel = Path(".claude/commands/d4d-uniform-rules.md")
        mine, theirs = repo / rel, CHECKOUT_ROOT / rel
        self.assertEqual(provenance.repo_relative(mine), rel.as_posix())
        self.assertEqual(provenance.repo_relative(theirs), theirs.resolve().as_posix())
        paths = [e["path"] for e in provenance.prompt_facts([mine, theirs])["files"]]
        self.assertEqual(len(set(paths)), 2, paths)

    def test_an_unreadable_marker_is_refused_not_read_as_no_checkout(self):
        """#1619"""
        import click
        from data_sheets_schema import resources
        from data_sheets_schema.cli.provenance import _require_repo_root_cwd
        repo = self._second_checkout(); (repo / "sub").mkdir()
        real = Path.read_text
        def unreadable(path, *a, **kw):
            if Path(path).resolve() == (repo / "pyproject.toml").resolve():
                raise PermissionError(13, "Permission denied", str(path))
            return real(path, *a, **kw)
        os.chdir(repo / "sub")
        with mock.patch.object(Path, "read_text", unreadable):
            with self.assertRaises(resources.ResourceRootError):
                resources.checkout_at(Path.cwd())
            with self.assertRaises(click.ClickException):
                _require_repo_root_cwd("t")
            os.chdir(repo)
            with self.assertRaises(resources.ResourceRootError):
                resources.cwd_checkout()

    def test_the_data_diagnostic_is_the_path_as_named_not_a_basename(self):
        """#1620"""
        from data_sheets_schema.api_runner import FULL_SCHEMA_PATH, _validator_did_not_run, _validator_lines
        tb = "Traceback (most recent call last):\n"
        self.assertTrue(_validator_did_not_run(tb + 'yaml.parser.ParserError: bad schema\n  in "/env/schema/x.yaml", line 2, column 1\n', "x.yaml"))
        self.assertTrue(_validator_did_not_run(tb + "ValueError: No such class: Dataset\n", "Dataset"))
        self.assertTrue(_validator_did_not_run(tb + "NotADirectoryError: [Errno 20] Not a directory: '/tmp/notadir/r.yaml'\n", "/tmp/notadir/r.yaml"))
        self.assertTrue(_validator_did_not_run(tb + "OSError: [Errno 62] Too many levels of symbolic links: '/tmp/r.yaml'\n", "/tmp/r.yaml"))
        self.assertFalse(_validator_did_not_run(tb + 'yaml.parser.ParserError: while parsing\n  in "/tmp/r.yaml", line 2, column 8\n', "/tmp/r.yaml"))
        # A schema that fails to parse, sharing the record's basename, is the validator not running.
        a = Path(self.tmp) / "a"; b = Path(self.tmp) / "b"; a.mkdir(); b.mkdir()
        (a / "bad.yaml").write_text("id: x\ntitle: [unclosed\n", encoding="utf-8")
        (b / "bad.yaml").write_text("id: x\ntitle: [unclosed\n", encoding="utf-8")
        os.chdir(ROOT)
        findings, failure = _validator_lines(b / "bad.yaml", str(a / "bad.yaml"), "Dataset")
        self.assertIsNone(findings); self.assertIsNotNone(failure)
        findings, failure = _validator_lines(b / "bad.yaml", FULL_SCHEMA_PATH, "Dataset")
        self.assertIsNone(failure, failure); self.assertTrue(findings)

    def test_a_failed_status_is_unknown_and_a_failed_command_yields_nothing(self):
        """#1621"""
        import subprocess
        from data_sheets_schema import provenance as p
        real = p.subprocess.run
        def status_fails(args, **kw):
            if args[:2] == ["git", "status"]:
                return subprocess.CompletedProcess(args, 128, b"", b"fatal: unable to read index\n")
            return real(args, **kw)
        os.chdir(ROOT)
        with mock.patch.object(p.subprocess, "run", status_fails):
            facts = p.repo_facts()
        self.assertIsNotNone(facts["commit"])
        self.assertEqual((facts["dirty"], facts["dirty_file_count"]), (None, None))
        self.assertIn("unknown, not clean", facts["note"])
        with mock.patch.object(p.subprocess, "run", return_value=subprocess.CompletedProcess([], 128, b"HEAD\n", b"")):
            self.assertIsNone(p._run(["git", "rev-parse", "HEAD"]))

    def test_an_implicit_registry_aliasing_another_checkout_is_refused_from_a_checkout_root(self):
        """#1622"""
        from data_sheets_schema import prompt_registry as pr
        from data_sheets_schema.resources import CHECKOUT_ROOT
        repo = self._second_checkout()
        (repo / "src/download").mkdir(parents=True)
        os.symlink(CHECKOUT_ROOT / "src/download/prompts", repo / "src/download/prompts")
        os.chdir(repo)
        with self.assertRaises(ValueError) as caught:
            pr.pin(".claude/commands/d4d-uniform-rules.md", "must not write the other checkout's registry")
        self.assertIn("not in the working tree", str(caught.exception))

    def test_trap_inventory_keeps_parser_findings(self):
        """#1623"""
        from data_sheets_schema import api_runner as a, run_telemetry as t
        bad = Path(self.tmp) / "bad.yaml"; bad.write_text("id: x\ntitle: [unclosed\n", encoding="utf-8")
        os.chdir(ROOT)
        lines, failure = a._validator_lines(bad, a.FULL_SCHEMA_PATH, "Dataset")
        self.assertIsNone(failure)
        base = Path(self.tmp) / "corpus"; rec = base / "api" / "run" / "P_d4d.yaml"; rec.parent.mkdir(parents=True)
        rec.write_text("id: x\n", encoding="utf-8")
        with mock.patch.object(a, "_validator_lines", return_value=(lines, failure)):
            result = t.trap_inventory(base)
        self.assertEqual((result["records_scanned"], result["records_with_errors"], result["records_with_unparsed_findings"]), (1, 1, 1))
        self.assertEqual(result["unparsed_findings"][0]["record"], str(rec))
        self.assertTrue(any("ParserError" in l or "parsing" in l for l in result["unparsed_findings"][0]["lines"]))

    def test_semantic_scope_reads_the_rubric_through_the_resolver(self):
        """#1625: the committed rubric example validates with the module placed
        where an install puts it — the rubric is found through `resource_path`,
        not two directories above the module."""
        import inspect
        import json
        import re
        from data_sheets_schema import semantic_scope as scope
        src = inspect.getsource(scope.validate_scope)
        self.assertIn("resource_path(", src)
        text = (ROOT / ".claude/agents/d4d-rubric10-semantic.md").read_text(encoding="utf-8")
        block = re.search(r"```json\n(.*?)\n```", text, re.S)
        if not block:
            self.skipTest("no example result in the rubric10-semantic definition")
        try:
            result = json.loads(block.group(1))
        except ValueError:
            self.skipTest("the example block is not JSON")
        os.chdir(ROOT)
        scope.validate_scope(result)                                           # from the checkout
        elsewhere = Path(self.tmp) / "site" / "data_sheets_schema"; elsewhere.mkdir(parents=True)
        with mock.patch.object(scope, "__file__", str(elsewhere / "semantic_scope.py")):
            scope.validate_scope(result)                                       # from an install-shaped location


class TestClaudeRoundFour(unittest.TestCase):
    """The Claude round-4 findings on #1455 (#1635–#1643)."""

    def setUp(self):
        self._cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="d4d-resources-")
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._cwd)

    def _git(self, repo, *a):
        import subprocess
        return subprocess.run(["git", "-c", "user.email=t@example.org", "-c", "user.name=t", *a],
                              cwd=repo, check=True, capture_output=True, text=True).stdout.strip()

    def _checkout(self, at: Path, *, git: bool) -> Path:
        (at / "src" / "data_sheets_schema").mkdir(parents=True)
        (at / ".claude" / "agents").mkdir(parents=True)
        (at / "pyproject.toml").write_text('[tool.poetry]\nname = "data-sheets-schema"\n', encoding="utf-8")
        (at / ".claude" / "agents" / "d4d-review-record.md").write_text(
            "---\nname: d4d-review-record\n---\n\n## Rules\n\nThe first version of this sentence is long enough to discriminate a version.\n", encoding="utf-8")
        if git:
            self._git(at, "init", "-q"); self._git(at, "add", "."); self._git(at, "commit", "-q", "-m", "one")
        return at

    def test_git_must_answer_for_the_resource_root_itself(self):
        """#1635: an export inside another repository is not that repository's commit."""
        from data_sheets_schema import provenance
        outer = Path(self.tmp) / "outer"; outer.mkdir()
        self._git(outer, "init", "-q"); (outer / "README").write_text("x\n"); self._git(outer, "add", "."); self._git(outer, "commit", "-q", "-m", "outer")
        export = self._checkout(outer / "export", git=False)
        os.chdir(export)
        facts = provenance.repo_facts()
        self.assertEqual((facts["commit"], facts["dirty"], facts["resource_kind"]), (None, None, "checkout"))
        self.assertIn("not the resource root", facts["note"])
        self.assertEqual(Path(facts["resource_root"]), export.resolve())

    def test_the_agent_definitions_history_is_read_where_the_definition_is(self):
        """#1638"""
        from data_sheets_schema import agent_pin
        repo = self._checkout(Path(self.tmp) / "wt", git=True)
        p = repo / ".claude" / "agents" / "d4d-review-record.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nA second version adds this sentence, absent from the first one entirely.\n", encoding="utf-8")
        self._git(repo, "add", "."); self._git(repo, "commit", "-q", "-m", "two")
        os.chdir(repo)
        self.assertEqual(agent_pin.agent_path("d4d-review-record").resolve(), p.resolve())
        self.assertEqual(agent_pin._history_root(p), repo.resolve())
        previous = agent_pin._previous_text("d4d-review-record")
        self.assertIsNotNone(previous)
        self.assertIn("The first version", previous); self.assertNotIn("A second version", previous)

    def test_a_crash_on_the_record_is_reduced_to_its_diagnostic(self):
        """#1639"""
        from data_sheets_schema.api_runner import FULL_SCHEMA_PATH, _crash_diagnostic, _validator_lines
        bad = Path(self.tmp) / "bad.yaml"; bad.write_text("id: x\ntitle: [unclosed\n", encoding="utf-8")
        os.chdir(ROOT)
        findings, failure = _validator_lines(bad, FULL_SCHEMA_PATH, "Dataset")
        self.assertIsNone(failure)
        self.assertLessEqual(len(findings), 6, findings)
        self.assertTrue(any("ParserError" in l for l in findings), findings)
        self.assertTrue(any(l.startswith("in ") and str(bad) in l for l in findings), findings)
        self.assertEqual(_crash_diagnostic("Traceback (most recent call last):\n  File \"x\", line 1\n    y()\nValueError: boom\n"), ["ValueError: boom"])

    def test_the_corpus_anchors_on_the_resource_root(self):
        """#1640: from a second checkout the corpus and the manifest are its own."""
        from data_sheets_schema import chunking, registry
        repo = self._checkout(Path(self.tmp) / "wt", git=True)
        (repo / "data" / "preprocessed").mkdir(parents=True)
        (repo / "data" / "preprocessed" / "source_manifest.yaml").write_text("projects: {}\n", encoding="utf-8")
        os.chdir(repo)
        self.assertEqual(chunking.corpus_root(), repo.resolve())
        self.assertEqual(chunking.anchored(chunking.CONCAT_DIR), Path(chunking.CONCAT_DIR))           # relative at the root
        self.assertEqual(registry._concat_dir().resolve(), (repo / chunking.CONCAT_DIR).resolve())
        self.assertEqual(Path(registry.default_manifest_path()).resolve(), (repo / "data/preprocessed/source_manifest.yaml").resolve())
        # A copy of the tree nested inside a checkout is part of that checkout,
        # not a root of its own (#1545): its manifest is not the registry.
        from data_sheets_schema.resources import checkout_at, cwd_checkout
        nested = self._checkout(repo / "notes" / "registration" / "files", git=False)
        os.chdir(nested)
        self.assertIsNone(cwd_checkout()); self.assertEqual(checkout_at(nested), repo.resolve())

    def test_an_install_measures_its_files_against_the_record(self):
        """#1641"""
        import base64, hashlib
        from types import SimpleNamespace
        from data_sheets_schema import provenance
        good = Path(self.tmp) / "good.txt"; good.write_text("bytes\n", encoding="utf-8")
        bad = Path(self.tmp) / "bad.txt"; bad.write_text("bytes\n", encoding="utf-8")
        def entry(path, digest_of):
            value = base64.urlsafe_b64encode(hashlib.sha256(digest_of).digest()).rstrip(b"=").decode()
            return SimpleNamespace(hash=SimpleNamespace(mode="sha256", value=value), locate=lambda: path, __str__=lambda self: path.name)
        entries = [entry(good, b"bytes\n"), entry(bad, b"other\n")]
        with mock.patch("importlib.metadata.files", return_value=entries):
            changed, measured, unmeasured = provenance._installed_files_changed()
        self.assertTrue(measured); self.assertEqual(len(changed), 1); self.assertEqual(unmeasured, [])
        with mock.patch("importlib.metadata.files", return_value=[]):
            self.assertEqual(provenance._installed_files_changed(), ([], False, []))
        with mock.patch("data_sheets_schema.resources.resource_root", return_value=(Path(self.tmp), "install")), \
                mock.patch("importlib.metadata.files", return_value=[entry(good, b"bytes\n")]):
            facts = provenance.repo_facts()
        self.assertEqual((facts["resource_kind"], facts["dirty"], facts["dirty_file_count"]), ("install", False, 0))
        with mock.patch("data_sheets_schema.resources.resource_root", return_value=(Path(self.tmp), "install")), \
                mock.patch("importlib.metadata.files", return_value=[]):
            facts = provenance.repo_facts()
        self.assertEqual((facts["dirty"], facts["dirty_file_count"]), (None, None))
        self.assertIn("unknown, not clean", facts["note"])

    def test_trap_inventory_lists_what_it_could_not_check(self):
        """#1642"""
        from data_sheets_schema import api_runner as a, run_telemetry as t
        base = Path(self.tmp) / "corpus"; rec = base / "api" / "run" / "P_d4d.yaml"; rec.parent.mkdir(parents=True)
        rec.write_text("id: x\n", encoding="utf-8")
        with mock.patch.object(a, "_validator_lines", return_value=(None, "linkml-validate did not run: boom")):
            result = t.trap_inventory(base)
        self.assertEqual((result["records_scanned"], result["records_unchecked"]), (0, 1))
        self.assertEqual(result["unchecked"][0]["record"], str(rec))

    def test_api_run_and_batch_refuse_a_subdirectory_of_a_checkout(self):
        """#1643"""
        import click.testing
        from data_sheets_schema.cli.api import api
        os.chdir(ROOT / "tests")
        for args in (["run", "--project", "CHORUS", "--label", "x"], ["batch", "--label-prefix", "x"]):
            r = click.testing.CliRunner().invoke(api, args)
            self.assertNotEqual(r.exit_code, 0)
            self.assertIn("repository root", r.output, args[0])


class TestCodexRoundFive(unittest.TestCase):
    """The Codex round-5 findings on #1455 (#1663–#1674)."""

    def setUp(self):
        self._cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp(prefix="d4d-resources-")
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self._cwd)

    def _checkout(self, at: Path) -> Path:
        (at / "src" / "data_sheets_schema").mkdir(parents=True)
        (at / "pyproject.toml").write_text('[tool.poetry]\nname = "data-sheets-schema"\n', encoding="utf-8")
        return at

    def test_an_implicit_chunk_write_is_refused_from_a_subdirectory(self):
        """#1663"""
        import click.testing
        from data_sheets_schema.cli.bundle import bundle
        repo = self._checkout(Path(self.tmp) / "wt"); os.chdir(repo / "src")
        r = click.testing.CliRunner().invoke(bundle, ["chunk", "--project", "CHORUS", "--max-lines", "7"])
        self.assertNotEqual(r.exit_code, 0); self.assertIn("repository root", r.output)

    def test_agent_lookup_honours_an_authoritative_absence(self):
        """#1664"""
        from data_sheets_schema import agent_pin
        repo = self._checkout(Path(self.tmp) / "wt"); os.chdir(repo)
        with self.assertRaises(FileNotFoundError):
            agent_pin.agent_path("d4d-rubric10-semantic")

    def _install(self):
        site = Path(self.tmp) / "site"
        (site / "data_sheets_schema" / "schema").mkdir(parents=True)
        (site / "data_sheets_schema" / "schema" / "x.yaml").write_text("a: 1\n", encoding="utf-8")
        (site / ".claude" / "agents").mkdir(parents=True)
        (site / ".claude" / "agents" / "d4d-review-record.md").write_text("---\nname: d4d-review-record\n---\n\nbody\n", encoding="utf-8")
        (site / "other_package").mkdir(); (site / "other_package" / "__init__.py").write_text("", encoding="utf-8")
        return site

    def test_installed_package_data_has_one_identity(self):
        """#1665"""
        from data_sheets_schema import resources
        site = self._install(); os.chdir(Path(self.tmp) / "work" if (Path(self.tmp) / "work").mkdir() is None else self.tmp)
        with mock.patch.multiple(resources, CHECKOUT_ROOT=None, INSTALL_ROOT=site, PACKAGE_ROOT=site / "data_sheets_schema"):
            self.assertEqual(resources.resource_root(), (site, "install"))
            physical = site / "data_sheets_schema" / "schema" / "x.yaml"
            self.assertEqual(resources.repo_relative(physical, cwd=False), "src/data_sheets_schema/schema/x.yaml")
            self.assertEqual(resources.resource_path(resources.repo_relative(physical, cwd=False)), physical)
            self.assertTrue(Path(resources.repo_relative(site / "other_package" / "__init__.py", cwd=False)).is_absolute())

    def test_the_agents_cli_enumerates_the_resolvers_definitions(self):
        """#1666"""
        from data_sheets_schema import resources
        from data_sheets_schema.cli import agents as ca
        site = self._install(); os.chdir(self.tmp)
        with mock.patch.multiple(resources, CHECKOUT_ROOT=None, INSTALL_ROOT=site, PACKAGE_ROOT=site / "data_sheets_schema"):
            self.assertEqual(ca._names(), ["d4d-review-record"])

    def test_a_partially_unhashed_record_is_not_a_clean_install(self):
        """#1667"""
        import base64, hashlib
        from types import SimpleNamespace
        from data_sheets_schema import provenance
        good = Path(self.tmp) / "good.py"; good.write_text("good", encoding="utf-8")
        h = SimpleNamespace(mode="sha256", value=base64.urlsafe_b64encode(hashlib.sha256(b"good").digest()).rstrip(b"=").decode())
        class Entry:
            def __init__(self, name, hash_value, path): self.name, self.hash, self.path = name, hash_value, path
            def __str__(self): return self.name
            def locate(self): return self.path
        g = Entry("good.py", h, good)
        missing = Entry("data_sheets_schema/schema/missing.yaml", None, Path(self.tmp) / "absent.yaml")
        pth = Entry("startup.pth", None, good)
        unhashed = Entry("data_sheets_schema/schema/x.yaml", None, good)
        with mock.patch("importlib.metadata.files", return_value=[g, missing]):
            self.assertEqual(provenance._installed_files_changed(), (["data_sheets_schema/schema/missing.yaml"], True, []))
        with mock.patch("importlib.metadata.files", return_value=[g, pth]):
            self.assertEqual(provenance._installed_files_changed(), ([], True, []))
        with mock.patch("importlib.metadata.files", return_value=[g, unhashed]):
            changed, measured, unmeasured = provenance._installed_files_changed()
            self.assertEqual((changed, measured, unmeasured), ([], False, ["data_sheets_schema/schema/x.yaml"]))

    def test_the_last_traceback_decides_and_a_quoted_name_keeps_its_marker(self):
        """#1668, #1672"""
        from data_sheets_schema.api_runner import _crash_diagnostic, _validator_did_not_run
        tb = "Traceback (most recent call last):\n  File \"validator.py\", line 1\n    parse()\n"
        chained = (tb + 'yaml.parser.ParserError: invalid\n  in "record.yaml", line 2, column 1\n\n'
                   "During handling of the above exception, another exception occurred:\n\n"
                   + tb + "RuntimeError: validator configuration broke\n")
        self.assertTrue(_validator_did_not_run(chained, "record.yaml"))
        quoted = tb + 'yaml.parser.ParserError: while parsing\n  in "a"b.yaml", line 2, column 1\n'
        self.assertFalse(_validator_did_not_run(quoted, 'a"b.yaml'))
        self.assertIn('in "a"b.yaml", line 2, column 1', _crash_diagnostic(quoted))

    def test_findings_emitted_before_a_crash_survive_it(self):
        """#1669"""
        import subprocess
        from data_sheets_schema import api_runner as a, run_telemetry as t
        out = "[ERROR] [r.yaml/0] ['not', 'string'] is not of type 'string' in /title\n"
        err = "Traceback (most recent call last):\n  File \"v.py\", line 1\n    go()\nyaml.parser.ParserError: while parsing\n  in \"/tmp/r.yaml\", line 5, column 8\n"
        with mock.patch.object(a.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, out, err)):
            findings, failure = a._validator_lines(Path("/tmp/r.yaml"), "schema.yaml", "Dataset")
        self.assertIsNone(failure)
        self.assertTrue(any(t.parse_validator_line(l) for l in findings), findings)
        self.assertTrue(any("ParserError" in l for l in findings), findings)
        base = Path(self.tmp) / "corpus"; rec = base / "api" / "run" / "P_d4d.yaml"; rec.parent.mkdir(parents=True)
        rec.write_text("id: x\n", encoding="utf-8")
        with mock.patch.object(a, "_validator_lines", return_value=(findings, None)):
            report = t.trap_inventory(base)
        self.assertEqual(report["records_with_unparsed_findings"], 1)
        self.assertTrue(report["traps"])

    def test_a_change_of_diagnostic_class_is_progress(self):
        """#1670"""
        from data_sheets_schema.api_runner import _finding_class
        parser = ["yaml.parser.ParserError: while parsing", 'in "P_d4d.yaml", line 2, column 8']
        shape = [f"[ERROR] [P_d4d.yaml/0] 12 is not of type object in /creators/{i}" for i in range(5)]
        self.assertEqual((_finding_class(parser), _finding_class(shape)), ("diagnostic", "structured"))
        self.assertNotEqual(_finding_class(parser), _finding_class(shape))     # the counts are not compared across classes

    def test_a_hard_linked_implicit_registry_is_refused(self):
        """#1671"""
        from data_sheets_schema import prompt_registry as pr
        staged = Path(self.tmp) / "staged"; (staged / "src" / "download" / "prompts").mkdir(parents=True)
        reg = staged / pr.REGISTRY; reg.write_text("prompts: {}\n", encoding="utf-8")
        other = Path(self.tmp) / "elsewhere.yaml"
        try:
            os.link(reg, other)
        except OSError:
            self.skipTest("hard links unavailable here")
        (staged / "src" / "download" / "prompts" / "p.md").write_text("# x\n\n## Prompt body\nbody\n", encoding="utf-8")
        os.chdir(staged)
        with self.assertRaises(ValueError) as caught:
            pr.pin("src/download/prompts/p.md", "must not write through the link")
        self.assertIn("hard-linked", str(caught.exception))
        self.assertEqual(other.read_text(encoding="utf-8"), "prompts: {}\n")

    def test_the_root_error_is_a_click_error(self):
        """#1673"""
        import click
        from data_sheets_schema.resources import ResourceRootError
        self.assertTrue(issubclass(ResourceRootError, click.ClickException))
        self.assertTrue(issubclass(ResourceRootError, RuntimeError))
        self.assertEqual(ResourceRootError("x").message, "x")

    def test_the_telemetry_schema_declares_the_new_fields(self):
        """#1674"""
        import json
        import subprocess
        from data_sheets_schema import run_telemetry as t
        from data_sheets_schema.resources import linkml_validate, resource_path
        os.chdir(ROOT)
        report = t.trap_inventory(Path(self.tmp) / "absent")
        schema = str(resource_path(t.SCHEMA_PATH))

        def validate(doc):                       # the command's own path (`d4d runs trap-inventory --validate`)
            f = Path(self.tmp) / "report.json"; f.write_text(json.dumps(doc, default=str), encoding="utf-8")
            return subprocess.run([*linkml_validate(), "-s", schema, "-C", "TrapSlotInventoryReport", str(f)],
                                  capture_output=True, text=True)
        good = validate(report)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        bad = validate(dict(report, records_unchecked="not an integer", unchecked=42))
        self.assertNotEqual(bad.returncode, 0)
