"""Tests for #5139: repo-relative provenance paths and worktree-prefixed arm_comparison."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

import data_sheets_schema.api_launcher as api_launcher
import data_sheets_schema.api_runner as api
import data_sheets_schema.chunking as chunking
import data_sheets_schema.provenance as provenance
from data_sheets_schema.evaluation import arm_comparison


def _md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_arm_comparison_resolves_historical_worktree_preprocessed_paths(tmp_path: Path) -> None:
    """Historical provenance records with worktree-prefixed paths resolve under active root."""
    bundle_rel = Path("data/preprocessed/individual/AI_READI/AI_READI_preprocessed.txt")
    chunks_rel = Path("data/preprocessed/individual/AI_READI/AI_READI_preprocessed.chunks.yaml")
    manifest_rel = Path("data/preprocessed/source_manifest.yaml")

    bundle_file = tmp_path / bundle_rel
    chunks_file = tmp_path / chunks_rel
    manifest_file = tmp_path / manifest_rel
    bundle_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.parent.mkdir(parents=True, exist_ok=True)

    bundle_bytes = b"=== FILE: README.md ===\nHello AI_READI\n"
    bundle_file.write_bytes(bundle_bytes)
    bundle_md5 = _md5_bytes(bundle_bytes)

    chunks_doc = {
        "schema_version": "1.0",
        "bundle": bundle_rel.as_posix(),
        "bundle_md5": bundle_md5,
        "chunks": [
            {
                "id": "c001",
                "source_file": "README.md",
                "md5": _md5_bytes(bundle_bytes),
            }
        ],
    }
    chunks_bytes = yaml.safe_dump(chunks_doc).encode("utf-8")
    chunks_file.write_bytes(chunks_bytes)

    manifest_bytes = b"project: AI_READI\nsources: []\n"
    manifest_file.write_bytes(manifest_bytes)

    old_wt = Path("/Users/example/d4d-executions/claude-canary1")
    record = {
        "run": {"project": "AI_READI", "label": "claudecode_opus46_generic_r1"},
        "inputs": {
            "bundle_path": str(old_wt / bundle_rel),
            "bundle_md5": bundle_md5,
            "chunks": {
                "path": str(old_wt / chunks_rel),
                "md5": _md5_bytes(chunks_bytes),
                "sha256": _sha256_bytes(chunks_bytes),
            },
            "source_manifest": {
                "path": str(old_wt / manifest_rel),
                "md5": _md5_bytes(manifest_bytes),
            },
        },
    }

    # Verify _path resolves the historical worktree path to tmp_path / ...
    resolved = arm_comparison._path(tmp_path, str(old_wt / bundle_rel))
    assert resolved == bundle_file.resolve()

    # Verify paths outside data/preprocessed/ on another root are still rejected
    outside = arm_comparison._path(tmp_path, str(old_wt / "secret/other.txt"))
    assert outside is None

    # Verify bundle_drift succeeds with worktree-prefixed paths on disk
    drift = arm_comparison.bundle_drift(record, tmp_path)
    assert drift["disk_status"] == "match"
    assert drift["manifest_status"] == "match"
    assert drift["manifest_basis"] == "pinned manifest on disk"

    # Also verify historical git recovery receives the repo-relative path when on-disk bytes differ
    chunks_file.write_bytes(b"modified on disk\n")
    recovered_paths: list[str] = []

    def _fake_recover(rel_path: str, *, md5: str | None = None, sha256: str | None = None):
        recovered_paths.append(rel_path)
        return (chunks_bytes, "deadbeef" * 5)

    drift_recovered = arm_comparison.bundle_drift(record, tmp_path, recover=_fake_recover)
    assert drift_recovered["manifest_status"] == "match"
    assert drift_recovered["manifest_basis"] == "pinned manifest recovered from history"
    assert recovered_paths == [chunks_rel.as_posix()]


def test_runspec_relativizes_in_checkout_absolute_input_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RunSpec normalizes absolute in-checkout bundle/manifest/chunk_manifest paths when cwd is root."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "src" / "data_sheets_schema").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('name = "data-sheets-schema"\n', encoding="utf-8")

    bundle_rel = Path("data/preprocessed/individual/CM4AI/CM4AI_preprocessed.txt")
    chunks_rel = Path("data/preprocessed/individual/CM4AI/CM4AI_preprocessed.chunks.yaml")
    manifest_rel = Path("data/preprocessed/source_manifest.yaml")

    for rel in (bundle_rel, chunks_rel):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("placeholder\n", encoding="utf-8")
    manifest_p = tmp_path / manifest_rel
    manifest_p.parent.mkdir(parents=True, exist_ok=True)
    manifest_p.write_text("projects: {}\n", encoding="utf-8")

    spec = api.RunSpec(
        project="CM4AI",
        arm="Claude Opus 4.6",
        method="claudecode_agent",
        label="claudecode_opus46_generic",
        bundle=(tmp_path / bundle_rel).resolve(),
        chunk_manifest=(tmp_path / chunks_rel).resolve(),
        manifest=(tmp_path / manifest_rel).resolve(),
    )

    assert spec.bundle == bundle_rel
    assert spec.chunk_manifest == chunks_rel
    assert spec.manifest == manifest_rel


def test_build_record_relativizes_in_checkout_absolute_paths_when_not_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """provenance.build_record records repo-relative paths for in-checkout absolute inputs."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()

    bundle_rel = Path("data/preprocessed/individual/VOICE/VOICE_preprocessed.txt")
    chunks_rel = Path("data/preprocessed/individual/VOICE/VOICE_preprocessed.chunks.yaml")
    manifest_rel = Path("data/preprocessed/source_manifest.yaml")

    bundle_abs = tmp_path / bundle_rel
    chunks_abs = tmp_path / chunks_rel
    manifest_abs = tmp_path / manifest_rel
    bundle_abs.parent.mkdir(parents=True, exist_ok=True)
    manifest_abs.parent.mkdir(parents=True, exist_ok=True)

    bundle_bytes = b"FILE: voice.txt\nPATH: voice.txt\nVoice content\n"
    bundle_abs.write_bytes(bundle_bytes)

    chunks_doc = chunking.build_manifest(bundle_abs)
    chunks_abs.write_text(chunking.dump_manifest(chunks_doc), encoding="utf-8")
    manifest_abs.write_text("projects: {}\n", encoding="utf-8")

    yaml_out = tmp_path / "data/d4d_concatenated/claudecode_agent/claudecode_opus46_generic/VOICE_d4d.yaml"
    core_out = tmp_path / "data/d4d_concatenated/claudecode_agent_core/claudecode_opus46_generic/VOICE_d4d_core.yaml"
    yaml_out.parent.mkdir(parents=True, exist_ok=True)
    core_out.parent.mkdir(parents=True, exist_ok=True)
    yaml_out.write_text("id: VOICE\n", encoding="utf-8")
    core_out.write_text("id: VOICE\n", encoding="utf-8")

    rec = provenance.build_record(
        "VOICE",
        "claudecode_agent",
        "claudecode_opus46_generic",
        mode="live",
        input_bundle=bundle_abs,
        input_verified=True,
        manifest=manifest_abs,
        chunk_manifest=chunks_abs,
        outputs={"full": yaml_out, "core": core_out},
    )

    assert rec.data["inputs"]["bundle_path"] == bundle_rel.as_posix()
    assert rec.data["inputs"]["chunks"]["path"] == chunks_rel.as_posix()
    assert rec.data["inputs"]["source_manifest"]["path"] == manifest_rel.as_posix()


def test_find_worktree_root_rejects_non_root_checkout_subdir(tmp_path: Path) -> None:
    """find_worktree_root refuses a directory whose checkout_at root is an ancestor."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "src" / "data_sheets_schema").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('name = "data-sheets-schema"\n', encoding="utf-8")

    # Checkout root itself is accepted
    assert api_launcher.find_worktree_root(tmp_path) == tmp_path.resolve()

    # Subdirectory that happens to have src/data_sheets_schema inside the same checkout is rejected
    sub = tmp_path / "nested"
    (sub / "src" / "data_sheets_schema").mkdir(parents=True)
    with pytest.raises(api_launcher.LauncherError, match="is not the checkout root"):
        api_launcher.find_worktree_root(sub)
