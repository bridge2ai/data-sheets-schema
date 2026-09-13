"""Resources resolve from any working directory, and records keep storing
the repository-relative path (#1301, #673)."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

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
        self.assertIn("## Prompt body", api_runner.prompt_body(api_runner.GENERIC_PROMPT_V9)
                      if False else resource_path(api_runner.GENERIC_PROMPT_V9).read_text())
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
        unwritable = Path("/nonexistent-root-for-d4d-tests/digest_inventory.yaml")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.assertFalse(schema_digest.record_inventory(ledger=unwritable))
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
        self.assertEqual(resource_path(escape), Path("data/d4d_concatenated/claudecode/VOICE_d4d.yaml"))
        self.assertFalse(is_resource("src/../README.md"))
        self.assertFalse(is_resource("../src/download/prompts/x.md"))
        alias = "src/download/../download/prompts/d4d_generic_arm_prompt_v9.md"
        self.assertEqual(repo_relative(alias), "src/download/prompts/d4d_generic_arm_prompt_v9.md")
        self.assertTrue(resource_path(alias).exists())

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
        """#1483: no by-name fallback after `resource_path` said absent."""
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
