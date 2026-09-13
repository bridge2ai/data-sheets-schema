"""A provenance reconstruction cannot replace the chunk instrument (#1454)."""
from functools import partial
import hashlib
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import chunking, provenance as pv, runs
from data_sheets_schema.cli import cli
from tests.test_generation_manifest_identity import external, offline  # noqa: F401


@pytest.fixture
def prior(external, monkeypatch):
    spec = external
    # Discovery still finds the fixture's one-chunk sidecar; the run actually
    # selected four chunks from a different manifest location.
    selected = spec.bundle.parent / "selected chunks.yaml"
    selected.write_text(chunking.dump_manifest(chunking.build_manifest(
        spec.bundle, {**chunking.DEFAULT_RULE, "max_lines": 3})))
    full = spec.out_dir / spec.method / spec.label / f"{spec.project}_d4d.yaml"
    full.parent.mkdir(parents=True)
    full.write_text(f"# Source bundle: {spec.bundle}\nid: https://example.org/cohort\n")
    build = partial(pv.build_record, concat_dir=spec.out_dir)
    path_for = partial(pv.record_path_for, concat_dir=spec.out_dir)
    path = path_for(spec.project, spec.method, spec.label)
    record = build(spec.project, spec.method, spec.label, mode="live",
                   input_bundle=spec.bundle, input_verified=True,
                   manifest=spec.manifest, chunk_manifest=selected)
    record.write(path)
    assert record.data["inputs"]["chunks"]["chunk_count"] == 4
    monkeypatch.setattr(pv, "build_record", build)
    monkeypatch.setattr(pv, "record_path_for", path_for)
    monkeypatch.setattr(runs, "discover", lambda: [SimpleNamespace(
        is_core=False, deterministic=False, projects=[spec.project],
        method=spec.method, label=spec.label)])
    return spec, selected, path


def test_verified_backfill_preserves_the_selected_chunk_instrument(prior):
    spec, selected, path = prior
    original = yaml.safe_load(path.read_text())["inputs"]
    result = CliRunner().invoke(cli, ["provenance", "backfill", "--verified-label", spec.label])
    assert result.exit_code == 0, result.output
    restored = yaml.safe_load(path.read_text())["inputs"]
    assert restored["chunks"] == original["chunks"]
    assert restored["bundle_md5"] == original["bundle_md5"]
    assert restored["chunks"]["sha256"] == hashlib.sha256(selected.read_bytes()).hexdigest()


@pytest.mark.parametrize("damage", ["missing", "changed", "bundle", "unverified", "hashless", "rule"])
def test_backfill_refuses_to_erase_or_replace_unreproduced_chunk_evidence(prior, damage):
    spec, selected, path = prior
    if damage == "missing":
        selected.unlink()
    elif damage == "changed":
        selected.write_text(selected.read_text() + "\n# changed bytes\n")
    elif damage == "bundle":
        spec.bundle.write_text(spec.bundle.read_text() + "changed input\n")
    elif damage in {"hashless", "rule"}:
        data = yaml.safe_load(path.read_text())
        if damage == "hashless":
            data["inputs"]["chunks"].pop("sha256")
        else:
            data["inputs"]["chunks"]["rule"]["max_lines"] = 9
        path.write_text(yaml.safe_dump(data))
    original = path.read_bytes()
    args = ["provenance", "backfill"]
    if damage != "unverified":
        args += ["--verified-label", spec.label]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code != 0, result.output
    assert "chunk" in result.output.lower()
    assert path.read_bytes() == original


@pytest.mark.parametrize("has_chunks_key", [True, False])
def test_backfill_does_not_retroactively_discover_unrecorded_chunks(prior, has_chunks_key):
    spec, selected, path = prior
    data = yaml.safe_load(path.read_text())
    data["inputs"].pop("chunks")
    if has_chunks_key:
        data["inputs"]["chunks"] = None
    path.write_text(yaml.safe_dump(data))
    result = CliRunner().invoke(cli, ["provenance", "backfill", "--verified-label", spec.label])
    assert result.exit_code == 0, result.output
    restored = yaml.safe_load(path.read_text())["inputs"]
    assert restored.get("chunks") is None


def test_backfill_can_discover_chunks_for_a_new_verified_record(prior):
    spec, selected, path = prior
    path.unlink()
    result = CliRunner().invoke(cli, ["provenance", "backfill", "--verified-label", spec.label])
    assert result.exit_code == 0, result.output
    restored = yaml.safe_load(path.read_text())["inputs"]
    assert restored["chunks"]["path"] == str(spec.chunk_manifest)
    assert restored["chunks"]["chunk_count"] == 1


def test_backfill_rechecks_the_builders_actual_chunk_bytes_before_writing(prior, monkeypatch):
    spec, selected, path = prior
    original = path.read_bytes()
    build = pv.build_record

    def changed_between_reads(*args, **kwargs):
        selected.write_text(selected.read_text() + "\n# changed during reconstruction\n")
        return build(*args, **kwargs)

    monkeypatch.setattr(pv, "build_record", changed_between_reads)
    result = CliRunner().invoke(cli, ["provenance", "backfill", "--verified-label", spec.label])
    assert result.exit_code != 0, result.output
    assert "chunk evidence changed during reconstruction" in result.output
    assert path.read_bytes() == original
