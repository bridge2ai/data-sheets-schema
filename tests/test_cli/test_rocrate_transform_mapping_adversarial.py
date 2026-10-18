"""Independent #4638 controls through the real CLI/legacy publication gate."""
import json

import pytest

from .test_rocrate_transform_mapping import (
    SENTINEL, actual_legacy_modules, inputs, invoke, mapping, report_path, seed, source,
)


@pytest.mark.parametrize("merge", [False, True])
@pytest.mark.parametrize("destination", ["dataset", "report"])
def test_selected_mapping_alias_cannot_be_replaced_by_dataset_or_report(
        tmp_path, mapping, merge, destination):
    crates = inputs(tmp_path)
    output = tmp_path / "dataset.yaml"
    alias = tmp_path / "mapping alias.tsv"
    alias.symlink_to(mapping)
    target = output if destination == "dataset" else report_path(output, merge)
    target.symlink_to(mapping)
    if destination == "report":
        output.write_bytes(SENTINEL)
    before = {path: path.read_bytes() for path in [*crates, mapping]}
    result = invoke(crates, output, merge, alias)
    assert result.exit_code == 1, result.output
    assert "protected input" in result.output
    assert "D4D YAML saved" not in result.output
    assert alias.is_symlink() and target.is_symlink()
    assert {path: path.read_bytes() for path in before} == before
    if destination == "report":
        assert output.read_bytes() == SENTINEL
    else:
        assert not report_path(output, merge).exists()


@pytest.mark.parametrize("merge", [False, True])
def test_report_destination_cannot_replace_any_selected_source(tmp_path, mapping, merge):
    output = tmp_path / "dataset.yaml"
    collided_source = source(report_path(output, merge))
    crates = [source(tmp_path / "first.json"), collided_source] if merge else [collided_source]
    output.write_bytes(SENTINEL)
    before = {path: path.read_bytes() for path in [*crates, mapping]}
    result = invoke(crates, output, merge, mapping)
    assert result.exit_code == 1, result.output
    assert "protected input" in result.output
    assert output.read_bytes() == SENTINEL
    assert {path: path.read_bytes() for path in before} == before


def test_explicit_mapping_does_not_skip_invalid_later_merge_source(tmp_path, mapping):
    crates = inputs(tmp_path)
    # Both Dataset entities are usable on their own, but no descriptor chooses
    # a root. The valid first crate must not become a partial replacement merge.
    crates[1].write_text(json.dumps({"@graph": [
        {"@id": "#first", "@type": "Dataset", "identifier": "https://example.org/first"},
        {"@id": "#second", "@type": "Dataset", "identifier": "https://example.org/second"},
    ]}), encoding="utf-8")
    output = tmp_path / "published" / "dataset.yaml"
    seed(output, True)
    before = {path: path.read_bytes() for path in [*crates, mapping]}
    result = invoke(crates, output, True, mapping)
    assert result.exit_code == 1, result.output
    assert "Error parsing RO-Crates" in result.output
    assert "D4D YAML saved" not in result.output
    assert output.read_bytes() == report_path(output, True).read_bytes() == SENTINEL
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("merge", [False, True])
def test_mapping_filename_cannot_inject_serialized_dataset_fields(tmp_path, mapping, merge):
    mapping = mapping.rename(tmp_path / "reviewed\nid: injected-id\n# mapping.tsv")
    crates = inputs(tmp_path)
    output = tmp_path / "published" / "dataset.yaml"
    seed(output, merge)
    before = {path: path.read_bytes() for path in [*crates, mapping]}
    result = invoke(crates, output, merge, mapping)
    assert result.exit_code == 1, result.output
    assert "Duplicate YAML key" in result.output
    assert output.read_bytes() == report_path(output, merge).read_bytes() == SENTINEL
    assert {path: path.read_bytes() for path in before} == before


def test_missing_root_identifier_never_falls_back_to_member_after_graph_reordering(tmp_path, mapping):
    crate = source(tmp_path / "root-has-no-identifier.json")
    document = json.loads(crate.read_bytes())
    root = next(node for node in document["@graph"] if node["@id"] == "#root")
    del root["identifier"]
    output = tmp_path / "published" / "dataset.yaml"
    seed(output, False)
    for graph in (document["@graph"], list(reversed(document["@graph"]))):
        crate.write_text(json.dumps({"@graph": graph}), encoding="utf-8")
        before = {path: path.read_bytes() for path in [crate, mapping]}
        result = invoke([crate], output, False, mapping)
        assert result.exit_code == 1, result.output
        assert "Dataset publication refused" in result.output
        assert output.read_bytes() == report_path(output, False).read_bytes() == SENTINEL
        assert {path: path.read_bytes() for path in before} == before
