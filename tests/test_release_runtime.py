"""The runtime key of a release series (#6324, 2026-11-24).

The 15 runs of series 2026-11-22b ran headless Claude Code on the maintainer's
subscription with no native controller. They were recorded as plain
`Claude Code` under `claudecode_agent`, so `d4d runs select` scoped their
canonical marks to the agentic runtime and superseded the agentic arm's. A
release series now has its own runtime string, key and method directory.

Offline; synthetic corpus only. Inputs: generated fixture; outputs: temporary records.
"""
import tempfile
import unittest
from pathlib import Path

import yaml
from click.testing import CliRunner

from tests.test_manifest_corpus_root import project_tree  # noqa: F401

RELEASE = "Claude Code (release)"


class ReleaseRuntimeRegistry(unittest.TestCase):
    def test_the_runtime_string_folds_to_its_own_key_and_is_a_claude_code_runtime(self):
        from data_sheets_schema.runs import (CANONICAL_RUNTIMES, CLAUDE_CODE_KEYS, RUNTIME_CHOICES, canonical_runtime,
                                             is_claude_code_runtime, runtime_of)
        self.assertEqual(runtime_of({"model": {"agent_runtime": RELEASE}}), "release")
        self.assertEqual(canonical_runtime("  claude code (RELEASE) "), RELEASE)
        self.assertEqual(CANONICAL_RUNTIMES["release"], RELEASE)
        self.assertIn("release", RUNTIME_CHOICES)
        self.assertEqual(RUNTIME_CHOICES[:3], ("api", "agentic", "direct"))      # the existing order is kept
        self.assertIn("release", CLAUDE_CODE_KEYS)
        self.assertTrue(is_claude_code_runtime(RELEASE))
        # It is neither of the two arms it resembles.
        self.assertNotEqual(runtime_of({"model": {"agent_runtime": RELEASE}}),
                            runtime_of({"model": {"agent_runtime": "Claude Code"}}))
        self.assertNotEqual(runtime_of({"model": {"agent_runtime": RELEASE}}),
                            runtime_of({"model": {"agent_runtime": "Claude Code (direct)"}}))

    def test_the_method_and_its_core_twin_are_a_baseline_agent_family(self):
        from data_sheets_schema.constants import METHODS
        from data_sheets_schema.runs import AGENT_FAMILY, ARM_BY_METHOD
        self.assertIn("claudecode_release", METHODS)
        self.assertIn("claudecode_release_core", METHODS)
        self.assertEqual(ARM_BY_METHOD["claudecode_release"], "baseline")
        self.assertEqual(ARM_BY_METHOD["claudecode_release_core"], "baseline")
        self.assertIn("claudecode_release", AGENT_FAMILY)

    def test_the_renderer_treats_it_as_an_agentic_claude_code_runtime(self):
        """A runtime outside these sets renders API text with agentic paths (#5089)."""
        from data_sheets_schema.api_runner import AGENTIC_RUNTIMES, CLAUDE_CODE_RUNTIMES
        from data_sheets_schema.provenance import runtime_reads_playbooks
        self.assertIn(RELEASE, AGENTIC_RUNTIMES)
        self.assertIn(RELEASE, CLAUDE_CODE_RUNTIMES)
        self.assertTrue(runtime_reads_playbooks(RELEASE))

    def test_an_omitted_method_follows_the_runtime(self):
        from data_sheets_schema.cli.api import _ARM_FOR_METHOD, _runtime_method
        self.assertEqual(_runtime_method("baseline", RELEASE, "generic_v9"), "claudecode_release")
        self.assertEqual(_runtime_method("baseline", "claude code (release)", None), "claudecode_release")
        self.assertEqual(_ARM_FOR_METHOD["claudecode_release"], "baseline")


class ReleaseCanonicalsAreScopedApart(unittest.TestCase):
    """The defect itself: a release-series mark must not touch another runtime's."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.corpus = Path(self.tmp.name)
        for method, label, runtime in (("claudecode_agent", "2026-08-28_a_rep1", "Claude Code"),
                                       ("claudecode_direct", "2026-09-22_d_rep1", "Claude Code (direct)"),
                                       ("claudecode_release", "2026-11-25a_r_rep1", RELEASE)):
            folder = self.corpus / f"{method}_core" / label
            folder.mkdir(parents=True)
            for name in ("CHORUS_d4d.yaml", "CHORUS_d4d_core.yaml"):
                (folder / name).write_text("id: https://example.org/x\n")
            (folder / "CHORUS_provenance.yaml").write_text(yaml.safe_dump({
                "run": {"project": "CHORUS", "label": label, "method": method},
                "model": {"agent_runtime": runtime},
                "canonical": {"criterion": "validity → coverage → label", "selected_from": [label]},
                "outputs": {"full": {"path": str(folder / "CHORUS_d4d.yaml")},
                            "core": {"path": str(folder / "CHORUS_d4d_core.yaml")}}}))

    def test_each_runtime_keeps_its_own_canonical(self):
        from data_sheets_schema.runs import canonical_runs, canonical_sets
        sets = canonical_sets(concat_dir=self.corpus)
        self.assertEqual({rt: found["CHORUS"]["label"] for rt, found in sets.items() if found},
                         {"agentic": "2026-08-28_a_rep1", "direct": "2026-09-22_d_rep1", "release": "2026-11-25a_r_rep1"})
        self.assertEqual(canonical_runs(concat_dir=self.corpus, runtime="release")["CHORUS"]["label"], "2026-11-25a_r_rep1")
        self.assertEqual(canonical_runs(concat_dir=self.corpus, runtime="agentic")["CHORUS"]["label"], "2026-08-28_a_rep1")

    def test_method_resolution_finds_a_label_under_the_release_family(self):
        from data_sheets_schema.runs import method_for_label
        self.assertEqual(method_for_label("2026-11-25a_r_rep1", concat_dir=self.corpus), "claudecode_release")


def test_prompt_render_names_release_paths_for_the_release_runtime(project_tree, monkeypatch):
    """Render with the runtime alone: the method, the output paths and the agentic text follow it."""
    from data_sheets_schema import chunking
    from data_sheets_schema.cli import cli

    root, manifest, bundle = project_tree
    monkeypatch.chdir(root)
    chunks, _ = chunking.write_manifest_for(bundle)
    out = root / "rendered.md"
    result = CliRunner().invoke(cli, ["prompt", "render", "--project", "CLINICAL_X", "--label", "external_run",
                                      "--condition", "generic_v9", "--bundle", str(bundle), "--manifest", str(manifest),
                                      "--chunk-manifest", str(chunks.absolute()), "--runtime", "claude code (release)",
                                      "--provider", "offline", "--out", str(out)])
    assert result.exit_code == 0, (result.output, result.exception)
    assert "runtime=Claude Code (release)" in result.output
    assert "⚠️" not in result.output, result.output                 # no method/runtime warning: the method followed the runtime
    text = out.read_text()
    assert "# Agent runtime: Claude Code (release)" in text
    assert "data/d4d_concatenated/claudecode_release/external_run/CLINICAL_X_d4d.yaml" in text
    assert "claudecode_agent/" not in text and "claudecode_direct/" not in text
    assert "## Installed agentic execution (renderer v6)" in text   # the agentic text, not the API's (#5089)
    assert " provenance record --project CLINICAL_X --method claudecode_release " in text


# Review 2 of #6325, SF3: a release series does not use native source attribution.

def test_native_attribution_runtimes_are_the_claude_code_runtimes_less_the_release_series():
    """Pins the relation of the two sets; RunSpec construction reads the narrower one."""
    from data_sheets_schema.api_runner import CLAUDE_CODE_RUNTIMES
    from data_sheets_schema.native_source_attribution import NATIVE_RUNTIMES
    assert CLAUDE_CODE_RUNTIMES - NATIVE_RUNTIMES == {RELEASE}
    assert NATIVE_RUNTIMES <= CLAUDE_CODE_RUNTIMES


def _attribution_spec(tmp_path, runtime, version):
    from dataclasses import replace

    from tests.test_source_metadata_renderer import fixture
    spec, _ = fixture(tmp_path, runtime)
    if not version:
        return replace(spec, render_version=16)
    return replace(spec, render_version=16, native_source_attribution_version=1, native_source_attribution_max_checks=2)


def test_release_runtime_with_native_attribution_is_refused_at_construction(tmp_path):
    import pytest
    with pytest.raises(ValueError, match=r"requires a native source-attribution runtime .*'Claude Code \(release\)' is not one"):
        _attribution_spec(tmp_path, RELEASE, 1)
    assert _attribution_spec(tmp_path, RELEASE, 0).native_source_attribution_version == 0   # without it, unchanged


def test_native_attribution_is_unchanged_for_the_other_claude_code_runtimes(tmp_path):
    for runtime in ("Claude Code", "Claude Code (direct)"):
        root = tmp_path / runtime.replace(" ", "_").replace("(", "").replace(")", "")
        root.mkdir()
        spec = _attribution_spec(root, runtime, 1)
        assert spec.native_source_attribution_version == 1
        assert "Native source-attribution draft preflight v1" in spec.instruction
