"""Canonical consumers and fresh flat records retain their artifact owner."""
from pathlib import Path
import shutil

import pytest
import yaml

from data_sheets_schema import api_runner, evaluation_plan, provenance, review_pack, runs
from tests import test_review_pack as review_fixtures
from tests.test_evaluation.test_evaluation_plan import _corpus


@pytest.mark.parametrize("all_replicates", [False, True])
@pytest.mark.parametrize("caller_copies", [False, True])
def test_canonical_evaluation_paths_belong_to_the_verified_corpus(tmp_path, monkeypatch, all_replicates, caller_copies):
    owner = tmp_path / "owner"
    corpus = _corpus(owner / "data/d4d_concatenated", ["SYNTHETIC"])
    record = next(corpus.rglob("*_provenance.yaml"))
    row = yaml.safe_load(record.read_text())
    expected = {}
    caller = tmp_path / "caller"; caller.mkdir()
    for variant, item in row["outputs"].items():
        path = Path(item["path"])
        expected[variant] = path
        relative = str(path.relative_to(owner))
        item["path"] = relative
        row["validation"]["artifacts"][variant]["path"] = relative
        if caller_copies:
            other = caller / relative
            other.parent.mkdir(parents=True, exist_ok=True)
            other.write_text("id: conflicting-caller-artifact\n")
    record.write_text(yaml.safe_dump(row))
    monkeypatch.chdir(caller)
    planned = evaluation_plan.plan(concat_dir=corpus, all_replicates=all_replicates)
    assert len(planned) == 4
    for item in planned:
        assert item.path == expected[item.variant]
        assert item.path.read_text() == "id: x\n"


def test_canonical_paths_with_an_unknown_absolute_record_base_are_unavailable(tmp_path):
    corpus = _corpus(tmp_path / "flat", ["SYNTHETIC"])
    record = next(corpus.rglob("*_provenance.yaml"))
    row = yaml.safe_load(record.read_text())
    for item in row["outputs"].values():
        item["path"] = Path(item["path"]).name
    record.write_text(yaml.safe_dump(row))
    found = runs.canonical_runs(concat_dir=corpus)["SYNTHETIC"]
    assert found["full"] is None
    assert found["core"] is None


@pytest.mark.parametrize("has_manifest", [False, True])
def test_fresh_flat_records_keep_bundle_and_chunks_for_later_review(tmp_path, monkeypatch, has_manifest):
    owner = tmp_path / "owner"; owner.mkdir()
    original, instruction = review_fixtures.Pack()._run(owner)
    old_paths = review_pack.record_paths(original)
    monkeypatch.chdir(owner)
    manifest = None
    if has_manifest:
        manifest = Path("source_manifest.yaml")
        manifest.write_text("projects:\n  P:\n    bundle: P_preprocessed.txt\n    sources: []\n")
    spec = api_runner.RunSpec(project="P", arm="BASELINE (input documents only)",
        method="external", label="fresh", condition="generic", profile="neutral",
        manifest=manifest, bundle=Path("P_preprocessed.txt"), chunk_manifest=Path("P_chunks.yaml"),
        out_dir=Path("out"))
    spec.out_dir.mkdir()
    outputs = {"full": spec.full_path, "core": spec.core_path, "report": spec.report_path}
    for key in ("full", "core"):
        shutil.copyfile(old_paths[key], outputs[key])
    spec.report_path.write_text("# Synthetic report\n")
    shutil.copyfile(old_paths["receipt"], spec.out_dir / "P_coverage_receipt.yaml")
    result = provenance.build_record(spec.project, spec.method, spec.label, mode="live",
        input_bundle=spec.bundle, input_verified=True, manifest=spec.manifest,
        selected_manifest=spec.manifest, chunk_manifest=spec.chunk_manifest,
        outputs=outputs, prompt_request=instruction.read_text(), receipt_expected=True)
    spec.provenance_path.write_text(yaml.safe_dump(result.data))
    caller = tmp_path / "later-caller"; caller.mkdir()
    monkeypatch.chdir(caller)
    pack = review_pack.build_pack(spec.provenance_path, instruction_file=instruction,
                                 write_instruction=False, instruction_out=[])
    assert pack["id_slots"]["bundle_state"] == "current"
    assert Path(pack["bundle"]["resolved_path"]) == owner / "P_preprocessed.txt"
    assert Path(pack["bundle"]["manifest"]) == owner / "P_chunks.yaml"
    assert len(pack["bundle"]["chunks"]) == 3
    assert any(item["kind"] == "chunk_nothing_relevant" for item in pack["items"])
