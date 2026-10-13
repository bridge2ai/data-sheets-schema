"""A mapper's provenance must bind the bytes it consumed, not later reads."""

import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import rocrate_map as mapper


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    packages = tmp_path / "packages"
    raw = packages / "P/raw"
    raw.mkdir(parents=True)
    source = raw / "ro-crate-metadata.json"
    source.write_text(json.dumps({"@graph": [{"@id": "https://example.org/p",
                                           "@type": "Dataset", "name": "old"}]}))
    table = tmp_path / "mapping.tsv"
    table.write_bytes(b"D4D_Full_Path\tRO_Crate_JSON_Path\r\nDataset.title\tname\r\n")
    schema = tmp_path / "schema.yaml"
    schema.write_bytes(b"name: captured-schema\n")
    monkeypatch.setattr(mapper, "MAPPING_TSV", table)
    monkeypatch.setattr(mapper, "FULL_SCHEMA", schema)
    view = object()
    consumed = []

    # Exercise real project I/O and provenance binding. Mapping/validation
    # themselves are covered by the mapper suite; these small seams let a
    # regression replace inputs at the exact boundary that previously lied.
    def map_snapshot(graph, rows, sv, project):
        assert sv is view  # the public supplied-view argument remains honored
        consumed.append((graph, rows))
        return mapper.MapResult(project=project, record={"title": graph[0]["name"]})

    monkeypatch.setattr(mapper, "map_crate", map_snapshot)
    monkeypatch.setattr(mapper, "validate", lambda path: "PASS")
    monkeypatch.setattr(mapper, "write_provenance",
                        lambda result, path, source: path.write_text("Validation: PASS\n"))
    return {"packages": packages, "source": source, "mapping table": table,
            "schema": schema, "view": view, "consumed": consumed,
            "processed": packages / "P/processed", "map_snapshot": map_snapshot}


def call(inputs, **kwargs):
    return mapper.map_project("P", inputs["packages"], sv=inputs["view"], **kwargs)


def test_success_binds_consumed_source_table_and_schema_bytes(inputs):
    original = {key: inputs[key].read_bytes() for key in ("source", "mapping table", "schema")}
    result = call(inputs)
    assert result.record == {"title": "old"}
    assert inputs["consumed"][0][1] == [{"D4D_Full_Path": "Dataset.title", "RO_Crate_JSON_Path": "name"}]
    for source_key, binding_key in (("source", "source"), ("mapping table", "mapping_table"),
                                    ("schema", "schema")):
        assert result.sources[binding_key]["sha256"] == hashlib.sha256(original[source_key]).hexdigest()
    assert result.sources["record_sha256"] == hashlib.sha256(result.outputs["d4d"].read_bytes()).hexdigest()
    module_dir = Path(mapper.__file__).resolve().parent
    assert result.sources["producer"]["files_sha256"] == {
        f"src/data_sheets_schema/{name}": hashlib.sha256((module_dir / name).read_bytes()).hexdigest()
        for name in mapper.PRODUCER_SOURCE_FILES}


@pytest.mark.parametrize("which", ["source", "mapping table", "schema"])
def test_drift_during_mapping_is_refused_before_any_working_output(inputs, monkeypatch, which):
    def replace_after_consuming(graph, rows, sv, project):
        result = inputs["map_snapshot"](graph, rows, sv, project)
        inputs[which].write_bytes(b"replacement bytes\n")
        return result
    monkeypatch.setattr(mapper, "map_crate", replace_after_consuming)
    with pytest.raises(ValueError, match="changed during generation"):
        call(inputs)
    assert inputs["consumed"][0][0][0]["name"] == "old"
    assert not inputs["processed"].exists()


@pytest.mark.parametrize("which", ["source", "mapping table", "schema"])
def test_drift_during_validation_cannot_publish_new_sidecar_or_success_report(inputs, monkeypatch, which):
    def validate_then_replace(path):
        inputs[which].write_bytes(b"replacement bytes\n")
        return "PASS"
    monkeypatch.setattr(mapper, "validate", validate_then_replace)
    with pytest.raises(ValueError, match="changed during generation"):
        call(inputs)
    assert (inputs["processed"] / "P_crate_mapped_d4d.yaml").exists()
    assert not (inputs["processed"] / "P_crate_mapping_sources.json").exists()
    assert not (inputs["processed"] / "P_crate_mapping_provenance.md").exists()


def test_source_deletion_is_reported_as_input_drift_before_output(inputs, monkeypatch):
    def delete_after_consuming(graph, rows, sv, project):
        result = inputs["map_snapshot"](graph, rows, sv, project)
        inputs["source"].unlink()
        return result
    monkeypatch.setattr(mapper, "map_crate", delete_after_consuming)
    with pytest.raises(ValueError, match="source changed during generation"):
        call(inputs)
    assert not inputs["processed"].exists()


def test_record_replacement_during_validation_cannot_inherit_provenance(inputs, monkeypatch):
    def validate_then_replace(path):
        path.write_text('title: replacement\n')
        return 'PASS'
    monkeypatch.setattr(mapper, 'validate', validate_then_replace)
    with pytest.raises(ValueError, match='output changed during generation'):
        call(inputs)
    assert not (inputs['processed'] / 'P_crate_mapping_sources.json').exists()
    assert not (inputs['processed'] / 'P_crate_mapping_provenance.md').exists()


def test_custom_rows_keep_their_actual_rules_binding_and_do_not_claim_shipped_table(inputs):
    rows = [{"D4D_Full_Path": "Dataset.description", "RO_Crate_JSON_Path": "name"}]
    result = call(inputs, rows=rows)
    binding = result.sources["mapping_table"]
    assert binding["path"] is None and binding["sha256"] is None
    assert binding["rules_sha256"] == hashlib.sha256(
        json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert inputs["consumed"][0][1] is not rows


def test_non_utf8_snapshot_preserves_the_established_encoding_refusal(inputs):
    inputs["source"].write_bytes(b'{"name": "\x97"}')
    with pytest.raises(mapper.CrateEncodingError, match="1 undecodable byte"):
        call(inputs)
    assert not inputs["processed"].exists()


@pytest.mark.parametrize("filename", mapper.PRODUCER_SOURCE_FILES)
def test_producer_code_drift_cannot_publish_a_record_or_binding(inputs, monkeypatch, tmp_path, filename):
    # Isolate the byte-binding seam; never mutate the executing repository's
    # producer files from a test.
    module_dir = tmp_path / "producer"
    module_dir.mkdir()
    for name in mapper.PRODUCER_SOURCE_FILES:
        (module_dir / name).write_bytes(b"captured producer bytes\n")
    monkeypatch.setattr(mapper, "__file__", str(module_dir / "rocrate_map.py"))
    def replace_after_consuming(graph, rows, sv, project):
        result = inputs["map_snapshot"](graph, rows, sv, project)
        (module_dir / filename).write_bytes(b"changed producer bytes\n")
        return result
    monkeypatch.setattr(mapper, "map_crate", replace_after_consuming)
    with pytest.raises(ValueError, match="producer .* changed during generation"):
        call(inputs)
    assert not inputs["processed"].exists()
