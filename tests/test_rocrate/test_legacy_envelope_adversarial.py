"""Independent compatibility and provenance controls for dataset_v1 (#4630)."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from .test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
STAMP = "2026-10-07T12:34:56"
ID = "https://example.org/dataset/envelope-control"
SENTINEL = b"Previously reviewed output\n"


@pytest.fixture
def api(monkeypatch):
    with legacy_imports():
        spec = importlib.util.spec_from_file_location(
            "_root_gates_transform_api", REPO / "src/transformation/transform_api.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        # Exact legacy shape comparisons need a stable time, not a changed
        # builder, serializer or schema validator.
        class FixedDateTime:
            @classmethod
            def now(cls):
                return cls()

            def isoformat(self):
                return STAMP

        monkeypatch.setattr(module, "datetime", FixedDateTime)
        monkeypatch.setattr(sys.modules["rocrate_merger"], "datetime", FixedDateTime)
        yield module


@pytest.fixture
def mapping(tmp_path):
    path = tmp_path / "custom.tsv"
    path.write_text(
        "D4D Property\tType\tFAIRSCAPE RO-Crate Property\t"
        "Covered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0\n"
        "id\tstr\tidentifier\t1\t1\n"
        "title\tstr\tname\t1\t1\n"
        "description\tstr\tdescription\t1\t1\n"
        "keywords\tlist[str]\tkeywords\t1\t1\n"
        "is_tabular\tbool\ttabular\t1\t1\n"
        "unknown_slot\tstr\tunknown\t1\t1\n",
        encoding="utf-8",
    )
    return path


def graph(*, unknown=False, title="Authoritative root"):
    root = {"@id": "#root", "@type": "Dataset", "identifier": ID,
            "name": title, "description": "Intact source: café\nA second line.",
            "keywords": ["first", "second"], "tabular": False}
    if unknown:
        root["unknown"] = "unrecognized source value must survive"
    return {"@graph": [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": "#root"}},
        {"@id": "./", "@type": "Dataset", "name": "Member cannot replace the root"},
        root,
    ]}


def source(tmp_path, name="source.json", **kwargs):
    path = tmp_path / name
    path.write_text(json.dumps(graph(**kwargs)), encoding="utf-8")
    return path


def transformer(api, mapping, *, contract="legacy", provenance=True):
    return api.SemanticTransformer(api.TransformationConfig(
        mapping_file=mapping, validate_input=False, validate_output=False,
        preserve_provenance=provenance, result_contract=contract))


def assert_published(result, output, mapping, encoding):
    data = result.data if hasattr(result, "data") else result["data"]
    metadata = (result.transformation_metadata if hasattr(result, "data")
                else result["transformation_metadata"])
    raw = output.read_bytes()
    assert yaml.safe_load(raw.decode(encoding)) == data
    assert "transformation_metadata" not in data
    assert "format" not in data
    assert publication.prepare_dataset(data, text=raw.decode(encoding), encoding=encoding) == raw
    assert metadata["mapping"] == {"path": str(mapping.resolve()),
        "sha256": sha256(mapping.read_bytes()).hexdigest(), "bytes": mapping.stat().st_size}
    assert metadata["mapping_version"] == "sha256:" + sha256(mapping.read_bytes()).hexdigest()
    assert metadata["publication"] == {
        "format": "d4d_dataset_publication_v1", "path": str(output.resolve()),
        "sha256": sha256(raw).hexdigest(), "bytes": len(raw),
        "encoding": encoding, "root_class": "Dataset"}
    assert metadata["result_contract"] == "dataset_v1"


@pytest.mark.parametrize("provenance", [False, True])
def test_default_legacy_single_shape_and_embedded_alias_remain_exact(api, mapping, tmp_path, provenance):
    path = source(tmp_path)
    instance = transformer(api, mapping, provenance=provenance)
    result = instance.rocrate_to_d4d(path)
    expected_data = {"id": ID, "title": "Authoritative root",
        "description": "Intact source: café\nA second line.",
        "keywords": ["first", "second"], "is_tabular": False}
    metadata = None
    if provenance:
        metadata = {"source": str(path), "source_type": "rocrate",
            "transformation_date": STAMP, "mapping_version": "v2_semantic",
            "profile_level": "basic", "coverage_percentage": 5 / 6 * 100,
            "unmapped_fields": ["unknown_slot"], "transformer_version": "semantic_transformer_1.0"}
        expected_data["transformation_metadata"] = metadata
        assert result.transformation_metadata is result.data["transformation_metadata"]
    assert asdict(result) == {"data": expected_data, "source": str(path), "target": "d4d",
        "timestamp": STAMP, "mapping_version": "v2_semantic", "coverage_percentage": 5 / 6 * 100,
        "unmapped_fields": ["unknown_slot"], "validation_passed": None,
        "validation_errors": None, "transformation_metadata": metadata,
        "coverage_basis": {"kind": "constructed_field_presence", "count_rule": "non_null_mapped_value",
            "numerator": 5, "denominator": 6, "is_source_coverage": False,
            "is_validation_success": False},
        "source_presence": {"format": "legacy_author_source_presence_v1", "status": "not_measured",
            "reason": "no_covered_creators_route", "target": "creators", "source_property": "author",
            "root_scope": "selected_root", "sources": []}}


@pytest.mark.parametrize("provenance", [False, True])
def test_default_legacy_merge_keeps_data_and_adds_explicit_source_diagnostic(api, mapping, tmp_path, provenance):
    path = source(tmp_path)
    result = transformer(api, mapping, provenance=provenance).merge_rocrates([path], auto_prioritize=False)
    assert set(result) == {"d4d", "merge_report", "source_presence"}
    assert result["source_presence"] == {"format": "legacy_author_source_presence_v1",
        "status": "not_measured", "reason": "no_covered_creators_route", "target": "creators",
        "source_property": "author", "root_scope": "selected_root", "sources": []}
    assert bool(result["merge_report"])
    if provenance:
        assert result["d4d"]["transformation_metadata"] == {
            "sources": [str(path)], "source_type": "rocrate_merge", "merge_strategy": "merge",
            "transformation_date": STAMP, "mapping_version": "v2_semantic", "profile_level": "basic",
            "transformer_version": "semantic_transformer_1.0"}
    else:
        assert "transformation_metadata" not in result["d4d"]


@pytest.mark.parametrize("given", ["path", "string", "dict"])
@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_opted_in_exact_file_bytes_and_source_identity(api, mapping, tmp_path, given, encoding):
    path = source(tmp_path)
    original = path.read_bytes()
    supplied = {"path": path, "string": str(path), "dict": graph()}[given]
    instance = transformer(api, mapping, contract="dataset_v1")
    instance.config.output_encoding = encoding
    draft = instance.rocrate_to_d4d(supplied, validate=False)
    assert draft.transformation_metadata["publication"] is None
    assert draft.timestamp == draft.transformation_metadata["transformation_date"]
    assert draft.source == ("dict" if given == "dict" else str(path))
    output = tmp_path / "published.yaml"
    result = instance.rocrate_to_d4d(supplied, output_path=output, validate=False)
    assert_published(result, output, mapping, encoding)
    assert result.source == result.transformation_metadata["source"] == draft.source
    assert result.data == draft.data
    assert type(result.data["is_tabular"]) is bool and result.data["is_tabular"] is False
    assert path.read_bytes() == original


@pytest.mark.parametrize("operation", ["single", "merge"])
def test_versioned_contract_never_strips_unrelated_unknown_fields(api, mapping, tmp_path, operation):
    path = source(tmp_path, unknown=True)
    instance = transformer(api, mapping, contract="dataset_v1")
    call = (lambda **kw: instance.rocrate_to_d4d(path, **kw) if operation == "single"
            else instance.merge_rocrates([path], auto_prioritize=False, **kw))
    draft = call()
    data = draft.data if operation == "single" else draft["data"]
    assert data["unknown_slot"] == "unrecognized source value must survive"
    output = tmp_path / "reviewed.yaml"
    output.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError, match="unknown_slot"):
        call(output_path=output)
    assert output.read_bytes() == SENTINEL
    metadata = draft.transformation_metadata if operation == "single" else draft["transformation_metadata"]
    assert metadata["publication"] is None


@pytest.mark.parametrize("operation", ["single", "merge"])
def test_mapping_drift_cannot_be_labeled_as_the_loaded_mapping(api, mapping, tmp_path, operation):
    path = source(tmp_path)
    instance = transformer(api, mapping)
    # The legacy loader has already consumed this mapping. Its loaded title
    # still comes from name, not the new custom property below.
    mapping.write_text(mapping.read_text().replace("title\tstr\tname", "title\tstr\tdescription"))
    legacy = instance.rocrate_to_d4d(path)
    assert legacy.data["title"] == "Authoritative root"
    output = tmp_path / "reviewed.yaml"
    output.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError, match="[Mm]apping.*changed"):
        if operation == "single":
            instance.rocrate_to_d4d(path, output_path=output, result_contract="dataset_v1")
        else:
            instance.merge_rocrates([path], output_path=output, result_contract="dataset_v1")
    assert output.read_bytes() == SENTINEL


def test_versioned_merge_keeps_report_text_and_only_changes_selected_envelope(api, mapping, tmp_path):
    paths = [source(tmp_path, "a.json"), source(tmp_path, "z.json", title="Secondary")]
    instance = transformer(api, mapping)
    legacy = instance.merge_rocrates(paths, auto_prioritize=False)
    output = tmp_path / "merged.yaml"
    versioned = instance.merge_rocrates(paths, auto_prioritize=False,
        result_contract="dataset_v1", output_path=output)
    assert set(versioned) == {
        "format", "data", "transformation_metadata", "merge_report", "source_presence"}
    assert versioned["source_presence"] == legacy["source_presence"] == {
        "format": "legacy_author_source_presence_v1",
        "status": "not_measured",
        "reason": "no_covered_creators_route",
        "target": "creators",
        "source_property": "author",
        "root_scope": "selected_root",
        "sources": [],
    }
    assert versioned["format"] == "d4d_transformation_result_v1"
    assert versioned["merge_report"] == legacy["merge_report"]
    expected = dict(legacy["d4d"])
    del expected["transformation_metadata"]
    assert versioned["data"] == expected
    assert_published(versioned, output, mapping, "utf-8")
    assert instance.config.result_contract == "legacy"


@pytest.mark.parametrize("operation", ["single", "merge"])
def test_provenance_off_stays_off_when_dataset_only_output_is_selected(api, mapping, tmp_path, operation):
    path = source(tmp_path)
    instance = transformer(api, mapping, contract="dataset_v1", provenance=False)
    output = tmp_path / "dataset.yaml"
    if operation == "single":
        result = instance.rocrate_to_d4d(path, output_path=output)
        data, metadata = result.data, result.transformation_metadata
        assert result.mapping_version == "sha256:" + sha256(mapping.read_bytes()).hexdigest()
    else:
        result = instance.merge_rocrates([path], output_path=output)
        data, metadata = result["data"], result["transformation_metadata"]
    assert metadata is None
    assert yaml.safe_load(output.read_bytes()) == data
    assert "transformation_metadata" not in data


def test_genuine_unknown_mapped_metadata_field_is_not_removed_for_api_provenance(api, mapping, tmp_path):
    mapping.write_text(mapping.read_text() + "transformation_metadata\tstr\tsourceMetadata\t1\t1\n")
    value = graph()
    value["@graph"][-1]["sourceMetadata"] = "A real mapped source value, not API-generated metadata"
    instance = transformer(api, mapping, contract="dataset_v1")
    draft = instance.rocrate_to_d4d(value)
    assert draft.data["transformation_metadata"] == value["@graph"][-1]["sourceMetadata"]
    assert isinstance(draft.transformation_metadata, dict)
    output = tmp_path / "retained.yaml"
    output.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError, match="transformation_metadata"):
        instance.rocrate_to_d4d(value, output_path=output)
    assert output.read_bytes() == SENTINEL


def test_new_result_mutations_cannot_change_future_provenance_or_data(api, mapping, tmp_path):
    path = source(tmp_path)
    instance = transformer(api, mapping, contract="dataset_v1")
    first = instance.rocrate_to_d4d(path)
    before = deepcopy(asdict(first))
    first.data["keywords"].clear()
    first.transformation_metadata["mapping"]["sha256"] = "forged"
    first.transformation_metadata["unmapped_fields"].append("forged")
    fresh = instance.rocrate_to_d4d(path)
    assert asdict(fresh) == before
    assert fresh.transformation_metadata["publication"] is None


def test_mapping_change_during_validation_is_refused_before_publication(api, mapping, tmp_path, monkeypatch):
    path = source(tmp_path)
    output = tmp_path / "reviewed.yaml"
    output.write_bytes(SENTINEL)
    instance = transformer(api, mapping, contract="dataset_v1")
    real_prepare = api.prepare_dataset

    def validate_then_change(*args, **kwargs):
        raw = real_prepare(*args, **kwargs)
        mapping.write_bytes(mapping.read_bytes() + b"\n# changed after validation\n")
        return raw

    monkeypatch.setattr(api, "prepare_dataset", validate_then_change)
    with pytest.raises(publication.PublicationError, match="Mapping bytes changed"):
        instance.rocrate_to_d4d(path, output_path=output)
    assert output.read_bytes() == SENTINEL


def test_publication_identity_cannot_describe_intended_but_replaced_bytes(api, mapping, tmp_path, monkeypatch):
    path = source(tmp_path)
    output = tmp_path / "published.yaml"
    instance = transformer(api, mapping, contract="dataset_v1")
    real_publish = api.publish

    def publish_then_replace(files, **kwargs):
        # Model an external write after the publisher returns. The contract
        # must refuse a success claim; it does not promise filesystem rollback.
        real_publish(files, **kwargs)
        output.write_bytes(b"different bytes after publication\n")

    monkeypatch.setattr(api, "publish", publish_then_replace)
    with pytest.raises(publication.PublicationError, match="Published Dataset bytes changed"):
        instance.rocrate_to_d4d(path, output_path=output)
    assert output.read_bytes() == b"different bytes after publication\n"


@pytest.mark.parametrize("late_invalid", [False, True])
def test_versioned_batch_publishes_only_after_all_candidates_pass(api, mapping, tmp_path, monkeypatch,
                                                               late_invalid):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    paths = [source(inputs, "a.json"), source(inputs, "z.json", unknown=late_invalid, title="Second")]
    original = {path: path.read_bytes() for path in paths}
    config = api.TransformationConfig(mapping_file=mapping, validate_input=False,
        validate_output=False, preserve_provenance=True, result_contract="dataset_v1")
    requested = []

    def configured(**kwargs):
        requested.append(kwargs)
        assert kwargs["result_contract"] == "dataset_v1"
        return config

    monkeypatch.setattr(api, "TransformationConfig", configured)
    output = tmp_path / "outputs"
    output.mkdir()
    destinations = [output / "a_d4d.yaml", output / "z_d4d.yaml"]
    for destination in destinations:
        destination.write_bytes(SENTINEL)
    if late_invalid:
        with pytest.raises(publication.PublicationError, match="unknown_slot"):
            api.batch_transform_rocrates(inputs, output, validate=False, result_contract="dataset_v1")
        assert [path.read_bytes() for path in destinations] == [SENTINEL, SENTINEL]
    else:
        results = api.batch_transform_rocrates(inputs, output, validate=False, result_contract="dataset_v1")
        assert isinstance(results, list) and [item.source for item in results] == [str(path) for path in paths]
        for result, destination in zip(results, destinations):
            assert_published(result, destination, mapping, "utf-8")
        retained_second = deepcopy(asdict(results[1]))
        results[0].transformation_metadata["mapping"].clear()
        results[0].transformation_metadata["publication"].clear()
        results[0].data["keywords"].clear()
        assert asdict(results[1]) == retained_second
    assert len(requested) == 1
    assert {path: path.read_bytes() for path in paths} == original
    assert set(output.iterdir()) == set(destinations)


@pytest.mark.parametrize("bad", ["dataset_v2", False, 1, [], {}])
def test_bad_contract_refuses_before_source_parsing(api, mapping, tmp_path, monkeypatch, bad):
    instance = transformer(api, mapping)
    output = tmp_path / "reviewed.yaml"
    output.write_bytes(SENTINEL)

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid contract reached source parsing")

    monkeypatch.setattr(api, "_parse_rocrate", forbidden)
    for operation in (lambda: instance.rocrate_to_d4d(tmp_path / "absent.json", output_path=output,
                                                     result_contract=bad),
                      lambda: instance.merge_rocrates([tmp_path / "absent.json"], output_path=output,
                                                     result_contract=bad)):
        with pytest.raises(ValueError, match="result_contract"):
            operation()
    assert output.read_bytes() == SENTINEL
