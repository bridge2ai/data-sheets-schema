"""PR #5213 round-four recorder byte-evidence regressions (2026-11-02).

Inputs: synthetic corpus and real CLI instruction/recording, adapted from
Claude's unchanged test_r3_verified_basis.py witness. Outputs: temporary
records only. A bound path is not evidence of the bytes consumed earlier.
"""
import hashlib

import pytest
import yaml

from tests.test_manifest_corpus_root import project_tree  # noqa: F401
from tests.test_wave7_5213_d76_round2_recorder import _record, _render


def _md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def _record_current(rendered, monkeypatch, explicit_chunks=True):
    (root, _, manifest, bundle, chunks, spec, original, instruction, prompt, paths) = rendered
    before = {path: path.read_bytes() if path.exists() else None
              for path in (manifest, bundle, chunks, prompt)}
    monkeypatch.chdir(root)
    result = _record(spec, prompt, manifest, bundle, chunks if explicit_chunks else None, True)
    assert result.exit_code == 0, (result.output, result.exception)
    assert paths["provenance"].is_file()
    assert paths["provenance"].stat().st_size > 0
    record = yaml.safe_load(paths["provenance"].read_text())
    request = record["prompts"]["request"]
    assert request["sha256"] == hashlib.sha256(instruction.encode()).hexdigest()
    for field in ("bundle", "manifest", "chunk_manifest"):
        assert request["spec"][field] == original[field], field
    assert record["inputs"]["bundle_md5"] == _md5(bundle)
    assert {path: path.read_bytes() if path.exists() else None for path in before} == before
    return record


def _assert_gaps(record, *, bundle_unverified):
    gaps = {item["field"]: item["reason"] for item in record.get("unverified") or []}
    # A chunk manifest's bundle digest can support bundle identity, but does
    # not itself pin the earlier chunk-file or source-manifest bytes.
    expected = {"inputs.chunks.sha256", "inputs.source_manifest.md5"}
    if bundle_unverified:
        expected.add("inputs.bundle_md5")
    assert expected <= gaps.keys(), gaps
    assert all(isinstance(gaps[field], str) and gaps[field].strip() for field in expected)
    if bundle_unverified:
        assert "consumed" in gaps["inputs.bundle_md5"]
    else:
        assert "inputs.bundle_md5" not in gaps


@pytest.mark.parametrize("explicit_chunks", [True, False])
def test_in_place_bundle_edit_is_asserted_despite_absolute_bound_paths(
    project_tree, monkeypatch, explicit_chunks,
):
    rendered = _render(project_tree, monkeypatch, "nested", explicit_chunks)
    (_, _, _, bundle, chunks, _, original, instruction, _, _) = rendered
    assert original["bundle"].startswith("/")
    assert original["chunk_manifest"].startswith("/")
    assert f"Read only this source bundle: `{original['bundle']}`." in instruction
    consumed_md5 = _md5(bundle)
    assert yaml.safe_load(chunks.read_text())["bundle_md5"] == consumed_md5
    before_identity = (bundle.stat().st_dev, bundle.stat().st_ino)
    with bundle.open("ab") as stream:
        stream.write(b"A sentence the earlier run never consumed.\n")
    assert (bundle.stat().st_dev, bundle.stat().st_ino) == before_identity
    assert _md5(bundle) != consumed_md5
    record = _record_current(rendered, monkeypatch, explicit_chunks)
    assert record["inputs"]["bundle_md5"] != consumed_md5
    assert record["inputs"]["chunks"] is None
    assert "asserted" in record["inputs"]["hash_basis"]
    _assert_gaps(record, bundle_unverified=True)


@pytest.mark.parametrize("evidence", ["stale_digest", "missing_manifest", "malformed_manifest"])
def test_absolute_declarations_without_valid_chunk_byte_evidence_remain_asserted(
    project_tree, monkeypatch, evidence,
):
    rendered = _render(project_tree, monkeypatch, "nested", True)
    (_, _, _, bundle, chunks, _, original, _, _, _) = rendered
    consumed_md5 = _md5(bundle)
    manifest = yaml.safe_load(chunks.read_text())
    assert manifest["bundle_md5"] == consumed_md5
    assert original["bundle"].startswith("/") and original["chunk_manifest"].startswith("/")
    if evidence == "stale_digest":
        manifest["bundle_md5"] = "0" * 32
        assert manifest["bundle_md5"] != consumed_md5
        chunks.write_text(yaml.safe_dump(manifest))
    elif evidence == "missing_manifest":
        chunks.unlink()
    else:
        chunks.write_text("unclosed: [\n")
    record = _record_current(rendered, monkeypatch)
    assert record["inputs"]["bundle_md5"] == consumed_md5
    assert record["inputs"]["chunks"] is None
    assert "asserted" in record["inputs"]["hash_basis"]
    _assert_gaps(record, bundle_unverified=True)


@pytest.mark.parametrize("render_cwd", ["nested", "root"])
def test_matching_bound_manifest_verifies_only_the_evidenced_bundle(
    project_tree, monkeypatch, render_cwd,
):
    rendered = _render(project_tree, monkeypatch, render_cwd, True)
    (_, _, _, bundle, chunks, _, original, instruction, _, _) = rendered
    consumed_md5 = _md5(bundle)
    assert yaml.safe_load(chunks.read_text())["bundle_md5"] == consumed_md5
    assert f"Read this chunk manifest first: `{original['chunk_manifest']}`." in instruction
    record = _record_current(rendered, monkeypatch)
    assert record["inputs"]["bundle_md5"] == consumed_md5
    assert record["inputs"]["chunks"]["sha256"] == hashlib.sha256(chunks.read_bytes()).hexdigest()
    if render_cwd == "nested":
        assert original["bundle"].startswith("/") and original["chunk_manifest"].startswith("/")
        assert record["inputs"]["hash_basis"] == "verified identical to the bytes consumed"
        _assert_gaps(record, bundle_unverified=False)
    else:
        assert not original["bundle"].startswith("/")
        assert "asserted" in record["inputs"]["hash_basis"]
        _assert_gaps(record, bundle_unverified=True)
