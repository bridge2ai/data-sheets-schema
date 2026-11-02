"""Round-three recorder identity regressions for PR #5213 (2026-11-02).

Inputs are synthetic corpus fixtures; outputs are temporary provenance records.
Adapted from the unchanged Codex/Claude re-check witnesses. The cross-corpus
probe uses the frozen output address, fixing the review probe's path-only error.
"""
import hashlib
import shutil

import pytest
import yaml
from click.testing import CliRunner

from data_sheets_schema.cli import cli
from tests.test_manifest_corpus_root import project_tree  # noqa: F401
from tests.test_wave7_5213_d76_round2_recorder import _record, _render


@pytest.mark.parametrize("same_bytes", [True, False])
def test_owner_counterpart_cannot_select_a_different_file(project_tree, monkeypatch, same_bytes):
    (root, nested, manifest, bundle, chunks, spec, _, _, prompt, paths) = _render(
        project_tree, monkeypatch, "nested", True)
    relative = bundle.relative_to(root)
    different = nested / relative
    different.parent.mkdir(parents=True)
    different.write_bytes(bundle.read_bytes() if same_bytes else b"DIFFERENT INPUT\n")
    monkeypatch.chdir(nested)
    assert relative.absolute() == different
    result = _record(spec, prompt, manifest, relative, chunks, True)
    assert result.exit_code != 0, (result.output, result.exception)
    assert not paths["provenance"].exists()


@pytest.mark.parametrize("alias", ["hardlink", "symlink"])
def test_owner_counterpart_cannot_replace_a_distinct_alias(project_tree, monkeypatch, alias):
    (root, nested, manifest, bundle, chunks, spec, _, _, prompt, paths) = _render(
        project_tree, monkeypatch, "nested", True)
    relative = bundle.relative_to(root)
    different = nested / relative
    different.parent.mkdir(parents=True)
    if alias == "hardlink":
        different.hardlink_to(bundle)
        assert different.stat().st_ino == bundle.stat().st_ino
        assert different.resolve() != bundle.resolve()
    else:
        different.symlink_to(bundle)
        assert different.resolve() == bundle.resolve()
        assert different.lstat().st_ino != bundle.lstat().st_ino
    monkeypatch.chdir(nested)
    result = _record(spec, prompt, manifest, relative, chunks, True)
    assert result.exit_code != 0, (result.output, result.exception)
    assert not paths["provenance"].exists()


@pytest.mark.parametrize("record_where", ["root", "nested"])
def test_cross_corpus_relative_instruction_never_verifies_consumed_bytes(
    project_tree, monkeypatch, record_where,
):
    (r1, _, manifest1, bundle1, chunks1, spec, original, instruction, _, paths) = _render(
        project_tree, monkeypatch, "root", True)
    assert not original["bundle"].startswith("/")
    consumed_md5 = hashlib.md5(bundle1.read_bytes()).hexdigest()
    record_relative = paths["provenance"].relative_to(r1)
    r2 = r1.parent / (r1.name + "_second_corpus")
    shutil.copytree(r1, r2, symlinks=True)
    bundle2 = r2 / bundle1.relative_to(r1)
    bundle2.write_bytes(bundle2.read_bytes() + b"Different second corpus bytes.\n")
    manifest2, chunks2 = (r2 / path.relative_to(r1) for path in (manifest1, chunks1))
    prompt = r2 / "instruction_from_first_corpus.txt"
    prompt.write_text(instruction)
    monkeypatch.chdir(r2 if record_where == "root" else r2 / "analysis")
    result = _record(spec, prompt, manifest2, bundle2, chunks2, True)
    if result.exit_code:
        assert not (r2 / record_relative).exists()
        return
    record = yaml.safe_load((r2 / record_relative).read_text())
    assert record["inputs"]["bundle_md5"] != consumed_md5
    assert "asserted" in record["inputs"]["hash_basis"]
    assert any(item["field"] == "inputs.bundle_md5" and "consumed" in item["reason"]
               for item in record["unverified"])


@pytest.mark.parametrize("render_cwd", ["root", "nested"])
def test_hash_basis_distinguishes_relative_assertion_from_absolute_binding(
    project_tree, monkeypatch, render_cwd,
):
    (root, _, manifest, bundle, chunks, spec, original, _, prompt, paths) = _render(
        project_tree, monkeypatch, render_cwd, True)
    monkeypatch.chdir(root)
    result = _record(spec, prompt, manifest, bundle, chunks, True)
    assert result.exit_code == 0, (result.output, result.exception)
    record = yaml.safe_load(paths["provenance"].read_text())
    assert record["inputs"]["bundle_md5"] == hashlib.md5(bundle.read_bytes()).hexdigest()
    if original["bundle"].startswith("/"):
        assert record["inputs"]["hash_basis"] == "verified identical to the bytes consumed"
    else:
        assert "asserted" in record["inputs"]["hash_basis"]
        assert any(item["field"] == "inputs.bundle_md5" for item in record["unverified"])


def test_recorder_without_instruction_does_not_claim_consumed_bytes(project_tree, monkeypatch):
    (root, _, manifest, bundle, chunks, spec, _, _, _, paths) = _render(
        project_tree, monkeypatch, "nested", True)
    monkeypatch.chdir(root)
    result = CliRunner().invoke(cli, [
        "provenance", "record", "--project", spec.project, "--method", spec.method,
        "--label", spec.label, "--manifest", str(manifest), "--input-bundle", str(bundle),
        "--chunk-manifest", str(chunks), "--runtime", spec.runtime, "--provider", "offline",
    ])
    assert result.exit_code == 0, (result.output, result.exception)
    record = yaml.safe_load(paths["provenance"].read_text())
    assert record["inputs"]["bundle_md5"] == hashlib.md5(bundle.read_bytes()).hexdigest()
    assert "asserted" in record["inputs"]["hash_basis"]
    assert any(item["field"] == "inputs.bundle_md5" and "consumed" in item["reason"]
               for item in record["unverified"])
