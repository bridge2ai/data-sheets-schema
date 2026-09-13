"""Review evidence resolves from the recorded corpus, never a caller's copy."""
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import review_pack
from tests import test_review_pack as review_fixtures


@pytest.mark.parametrize("caller_location", ["nested", "unrelated"])
@pytest.mark.parametrize("caller_copies", [False, True])
def test_review_pack_keeps_its_recorded_bundle_and_chunk_map(tmp_path, monkeypatch, caller_location, caller_copies):
    owner = tmp_path / "owner"
    data = owner / "data"; data.mkdir(parents=True)
    record, instruction = review_fixtures.Pack()._run(data)
    source_manifest = data / "preprocessed/source_manifest.yaml"
    source_manifest.parent.mkdir()
    source_manifest.write_text("projects:\n  P:\n    sources: []\n")
    row = yaml.safe_load(record.read_text())
    bundle = Path(row["inputs"]["bundle_path"])
    chunks = Path(row["inputs"]["chunks"]["path"])
    expected = yaml.safe_load(chunks.read_text())["chunks"]
    row["inputs"]["bundle_path"] = str(bundle.relative_to(owner))
    row["inputs"]["chunks"]["path"] = str(chunks.relative_to(owner))
    record.write_text(yaml.safe_dump(row))
    caller = owner / "analysis" if caller_location == "nested" else tmp_path / "other"
    caller.mkdir()
    if caller_copies:
        local_bundle = caller / bundle.relative_to(owner)
        local_bundle.parent.mkdir(parents=True, exist_ok=True)
        local_bundle.write_bytes(bundle.read_bytes())
        mapping = yaml.safe_load(chunks.read_text())
        for chunk in mapping["chunks"]:
            chunk["source"] = "unrelated.txt"; chunk["lines"] = [70, 90]
        (caller / chunks.relative_to(owner)).write_text(yaml.safe_dump(mapping))
    monkeypatch.chdir(caller)
    pack = review_pack.build_pack(record, instruction_file=instruction,
                                 write_instruction=False, instruction_out=[])
    assert pack["id_slots"]["bundle_state"] == "current"
    assert Path(pack["bundle"]["resolved_path"]) == bundle
    assert pack["bundle"].get("chunks") == [
        {key: chunk[key] for key in ("id", "lines", "source")} for chunk in expected]
    assert Path(pack["bundle"]["manifest"]) == chunks
    assert any(item["kind"] == "chunk_nothing_relevant" for item in pack["items"])


def test_absolute_flat_record_does_not_guess_a_base_for_relative_inputs(tmp_path, monkeypatch):
    original = tmp_path / "original"; original.mkdir()
    record, instruction = review_fixtures.Pack()._run(original)
    row = yaml.safe_load(record.read_text())
    caller = tmp_path / "caller"; caller.mkdir()
    for field in ("bundle_path", "chunks"):
        path = Path(row["inputs"][field] if field == "bundle_path" else row["inputs"][field]["path"])
        (caller / path.name).write_bytes(path.read_bytes())
        if field == "bundle_path": row["inputs"][field] = path.name
        else: row["inputs"][field]["path"] = path.name
    record.write_text(yaml.safe_dump(row))
    monkeypatch.chdir(caller)
    pack = review_pack.build_pack(record, instruction_file=instruction,
                                 write_instruction=False, instruction_out=[])
    assert pack["id_slots"]["bundle_state"] != "current"
    assert "chunks" not in pack["bundle"]
    assert any("base" in gap for gap in pack["gaps"])
