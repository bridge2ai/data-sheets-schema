"""Real legacy publishers must accept final Dataset bytes before any output."""
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication
from .test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
SENTINEL = b"previous reviewed output\n"
ID = "https://example.org/dataset/control"
SOURCE_TEXT = "Original source text.\nSecond line."


@pytest.fixture
def legacy():
    with legacy_imports():
        single = importlib.import_module("rocrate_to_d4d")
        auto = importlib.import_module("auto_process_rocrates")
        spec = importlib.util.spec_from_file_location(
            "_root_gates_transform_api", REPO / "src/transformation/transform_api.py")
        api = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        yield single, auto, api


@pytest.fixture
def mapping(tmp_path):
    path = tmp_path / "mapping.tsv"
    path.write_text(
        "D4D Property\tType\tFAIRSCAPE RO-Crate Property\t"
        "Covered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0\n"
        "id\tstr\tidentifier\t1\t1\n"
        "title\tstr\tname\t1\t1\n"
        "description\tstr\tdescription\t1\t1\n"
        "keywords\tlist[str]\tkeywords\t1\t1\n"
        "unexpected_field\tstr\tunexpected\t1\t1\n"
        "creators\tstr\tbadCreators\t1\t1\n",
        encoding="utf-8",
    )
    return path


def crate(path, kind="valid", *, title="Café control"):
    root = {"@id": "./", "@type": "Dataset", "identifier": ID,
            "name": title, "description": SOURCE_TEXT,
            "keywords": ["one", "two"]}
    if kind == "missing_id":
        del root["identifier"]
    elif kind == "unknown":
        root["unexpected"] = "must remain, never silently dropped"
    elif kind == "nested":
        root["badCreators"] = "A person string is not a Creator object list"
    path.write_text(json.dumps({"@graph": [root]}), encoding="utf-8")
    return path


def destinations(output):
    return [output, output.with_name(output.stem + "_report.txt"),
            output.with_name(output.stem + "_merge_report.txt"),
            output.with_name("transformation_report.txt"),
            output.with_name(output.stem + "_concatenated.json")]


def seed(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    for path in destinations(output):
        path.write_bytes(SENTINEL)


def preserved(output):
    assert {path: path.read_bytes() for path in destinations(output)} == {
        path: SENTINEL for path in destinations(output)}


def accepted(output, description=SOURCE_TEXT):
    raw = output.read_bytes()
    record = yaml.safe_load(raw)
    assert record == {"id": ID, "title": "Café control",
                      "description": description,
                      "keywords": ["one", "two"]}
    assert publication.prepare_dataset(record, text=raw.decode("utf-8")) == raw


@pytest.mark.parametrize("command", ["transform", "merge"])
@pytest.mark.parametrize("kind", ["valid", "missing_id", "unknown", "nested"])
def test_packaged_final_schema_gate(tmp_path, mapping, command, kind):
    from fairscape_integration.cli import cli

    source = crate(tmp_path / "crate.json", kind)
    before = source.read_bytes()
    output = tmp_path / "published" / "record.yaml"
    seed(output)
    result = CliRunner().invoke(cli, [command, str(source), "-m", str(mapping),
                                     "-o", str(output), "--report"])
    if kind == "valid":
        assert result.exit_code == 0, result.output
        accepted(output, f"## Overview\n{SOURCE_TEXT}" if command == "merge" else SOURCE_TEXT)
    else:
        assert result.exit_code == 1, result.output
        assert "Dataset publication refused" in result.output
        assert str(source) in result.output and str(output) in result.output
        assert "written to" not in result.output
        preserved(output)
    assert source.read_bytes() == before


@pytest.mark.parametrize("merge", [False, True])
@pytest.mark.parametrize("kind", ["valid", "missing_id", "unknown", "nested"])
def test_hidden_final_schema_gate(legacy, tmp_path, mapping, monkeypatch, merge, kind):
    single, _, _ = legacy
    first = crate(tmp_path / "a.json", kind)
    second = crate(tmp_path / "b.json", kind)
    output = tmp_path / "published" / "record.yaml"
    seed(output)
    args = ["transform", "-m", str(mapping), "-o", str(output)]
    args += (["--merge", "--inputs", str(first), str(second)] if merge
             else ["--input", str(first)])
    monkeypatch.setattr(sys, "argv", args)
    status = single.main()
    if kind == "valid":
        assert status == 0
        accepted(output, (f"## Overview\n{SOURCE_TEXT}\n\n## B.Json\n{SOURCE_TEXT}"
                          if merge else SOURCE_TEXT))
    else:
        assert status == 1
        preserved(output)


@pytest.mark.parametrize("strategy", ["merge", "concatenate", "hybrid"])
@pytest.mark.parametrize("kind", ["valid", "missing_id", "unknown"])
def test_auto_prepares_intermediate_and_reports_before_publication(
        legacy, tmp_path, mapping, monkeypatch, strategy, kind):
    _, auto, _ = legacy
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    first = crate(inputs / "a-ro-crate-metadata.json", kind)
    # Hybrid really prepares a secondary concatenated graph; concatenate
    # uses one complete graph because independent './' roots cannot be joined.
    sources = [first]
    if strategy == "hybrid":
        sources.append(crate(inputs / "b-ro-crate-metadata.json", kind))
    before = {path: path.read_bytes() for path in sources}
    output = tmp_path / "published" / "record.yaml"
    seed(output)
    monkeypatch.setattr(sys, "argv", ["auto", "-i", str(inputs), "-m", str(mapping),
                                    "-o", str(output), "--strategy", strategy])
    status = auto.main()
    if kind == "valid":
        assert status == 0
        description = {
            "merge": f"## Overview\n{SOURCE_TEXT}",
            "concatenate": SOURCE_TEXT,
            "hybrid": f"## Overview\n{SOURCE_TEXT}\n\n## Record Concatenated.Json\n{SOURCE_TEXT}",
        }[strategy]
        accepted(output, description)
        if strategy in ("hybrid", "concatenate"):
            intermediate = output.with_name("record_concatenated.json")
            assert json.loads(intermediate.read_bytes())["@graph"]
            assert intermediate.name in output.read_text()
    else:
        assert status == 1
        preserved(output)
    assert {path: path.read_bytes() for path in sources} == before


def transformer(api, mapping, *, provenance=False):
    return api.SemanticTransformer(api.TransformationConfig(
        mapping_file=mapping, validate_input=False, validate_output=False,
        preserve_provenance=provenance))


@pytest.mark.parametrize("operation", ["single", "merge"])
@pytest.mark.parametrize("kind", ["valid", "missing_id", "unknown", "nested"])
def test_api_file_outputs_require_validation_without_optional_validator(
        legacy, tmp_path, mapping, monkeypatch, operation, kind):
    _, _, api = legacy
    monkeypatch.setattr(api, "VALIDATION_AVAILABLE", False)
    source = crate(tmp_path / "crate.json", kind)
    output = tmp_path / "published" / "record.yaml"
    seed(output)
    instance = transformer(api, mapping)
    assert instance.validator is None
    call = (lambda **kw: instance.rocrate_to_d4d(source, validate=False, **kw)
            if operation == "single" else
            instance.merge_rocrates([source], validate=False, **kw))
    # Draft construction, including schema-invalid fields, stays available.
    draft = call()
    data = draft.data if operation == "single" else draft["d4d"]
    if kind == "unknown":
        assert data["unexpected_field"] == "must remain, never silently dropped"
    if kind == "valid":
        call(output_path=output)
        accepted(output, f"## Overview\n{SOURCE_TEXT}" if operation == "merge" else SOURCE_TEXT)
    else:
        with pytest.raises(publication.PublicationError, match="Dataset publication refused"):
            call(output_path=output)
        preserved(output)


@pytest.mark.parametrize("operation", ["single", "merge"])
def test_api_metadata_envelope_is_not_silently_repaired(
        legacy, tmp_path, mapping, operation):
    _, _, api = legacy
    source = crate(tmp_path / "crate.json")
    instance = transformer(api, mapping, provenance=True)
    call = (lambda **kw: instance.rocrate_to_d4d(source, **kw)
            if operation == "single" else instance.merge_rocrates([source], **kw))
    draft = call()
    data = draft.data if operation == "single" else draft["d4d"]
    assert data["transformation_metadata"]
    output = tmp_path / "published" / "record.yaml"
    seed(output)
    with pytest.raises(publication.PublicationError, match="transformation_metadata.*#4630"):
        call(output_path=output)
    assert data["transformation_metadata"]
    preserved(output)


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("late_invalid", [False, True])
def test_batch_validates_every_final_record_before_first_publication(
        legacy, tmp_path, mapping, monkeypatch, existing, late_invalid):
    _, _, api = legacy
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    crate(inputs / "a.json")
    crate(inputs / "z.json", "missing_id" if late_invalid else "valid")
    # This explicit configuration is the valid control. The real batch
    # producer, serialization and required validator all remain in use.
    config = api.TransformationConfig(
        mapping_file=mapping, validate_input=False, validate_output=False,
        preserve_provenance=False)
    monkeypatch.setattr(api, "TransformationConfig", lambda **_: config)
    output = tmp_path / "published"
    paths = [output / name for name in ("a_d4d.yaml", "z_d4d.yaml")]
    if existing:
        output.mkdir()
        for path in paths:
            path.write_bytes(SENTINEL)
    if late_invalid:
        with pytest.raises(publication.PublicationError, match="z.json.*id"):
            api.batch_transform_rocrates(inputs, output, validate=False)
        if existing:
            assert [path.read_bytes() for path in paths] == [SENTINEL, SENTINEL]
        else:
            assert not output.exists()
    else:
        assert len(api.batch_transform_rocrates(inputs, output, validate=False)) == 2
        for path in paths:
            accepted(path)


def test_d4d_wrapper_propagates_real_schema_refusal(legacy, tmp_path):
    from data_sheets_schema.cli import cli

    source = crate(tmp_path / "crate.json")
    output = tmp_path / "published" / "record.yaml"
    seed(output)
    result = CliRunner().invoke(cli, ["rocrate", "transform", str(source), "-o", str(output)])
    assert result.exit_code == 1, result.output
    assert "Dataset publication refused" in result.output
    preserved(output)


def test_d4d_wrapper_delegates_valid_mapping_to_real_legacy_gate(
        legacy, tmp_path, mapping, monkeypatch):
    from data_sheets_schema.cli import cli

    module = importlib.import_module("data_sheets_schema.cli.rocrate")
    config_root = tmp_path / "config"
    selected = config_root / "data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv"
    selected.parent.mkdir(parents=True)
    selected.write_bytes(mapping.read_bytes())
    # Supply a real alternate checkout mapping at the wrapper's lookup seam;
    # parser, legacy main and required validator remain the actual consumers.
    monkeypatch.setattr(module, "get_repo_root", lambda: config_root)
    source = crate(tmp_path / "crate.json")
    output = tmp_path / "published" / "record.yaml"
    result = CliRunner().invoke(cli, ["rocrate", "transform", str(source), "-o", str(output)])
    assert result.exit_code == 0, result.output
    accepted(output)


def test_packaged_required_validator_failure_preserves_all_outputs(tmp_path, mapping, monkeypatch):
    from fairscape_integration.cli import cli

    source = crate(tmp_path / "crate.json")
    output = tmp_path / "published" / "record.yaml"
    seed(output)

    def unavailable(*args):
        raise ImportError("required LinkML validator unavailable")

    monkeypatch.setattr(publication, "_validator", unavailable)
    result = CliRunner().invoke(cli, ["transform", str(source), "-m", str(mapping),
                                     "-o", str(output), "--report"])
    assert result.exit_code == 1, result.output
    assert "Required Dataset publication validation unavailable" in result.output
    preserved(output)


def test_merged_partial_draft_is_validated_only_after_final_merge(legacy, tmp_path, mapping):
    _, _, api = legacy
    incomplete = crate(tmp_path / "a.json", "missing_id")
    complete = crate(tmp_path / "b.json")
    output = tmp_path / "record.yaml"
    transformer(api, mapping).merge_rocrates(
        [incomplete, complete], output_path=output, auto_prioritize=False)
    accepted(output, f"## Overview\n{SOURCE_TEXT}\n\n## B\n{SOURCE_TEXT}")


@pytest.mark.parametrize("operation", ["batch", "convenience"])
def test_default_provenance_inherited_by_wrappers_refuses_file_publication(
        legacy, tmp_path, mapping, monkeypatch, operation):
    _, _, api = legacy
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    source = crate(inputs / "a.json")
    # Change only fixture paths and disable optional diagnostics; provenance
    # retains the actual default. This is not a metadata-envelope correction.
    config = api.TransformationConfig(
        mapping_file=mapping, validate_input=False, validate_output=False)
    assert config.preserve_provenance is True
    monkeypatch.setattr(api, "TransformationConfig", lambda **_: config)
    output = tmp_path / "published" / "a_d4d.yaml"
    seed(output)
    with pytest.raises(publication.PublicationError, match="transformation_metadata.*#4630"):
        if operation == "batch":
            api.batch_transform_rocrates(inputs, output.parent, validate=False)
        else:
            api.transform_rocrate_file(source, output, validate=False)
    preserved(output)


def test_api_configured_encoding_validates_and_publishes_same_bytes(legacy, tmp_path, mapping):
    _, _, api = legacy
    source = crate(tmp_path / "crate.json")
    output = tmp_path / "record.yaml"
    instance = transformer(api, mapping)
    instance.config.output_encoding = "utf-16"
    result = instance.rocrate_to_d4d(source, output_path=output)
    raw = output.read_bytes()
    assert raw.startswith((b"\xff\xfe", b"\xfe\xff"))
    assert yaml.safe_load(raw.decode("utf-16")) == result.data
    assert publication.prepare_dataset(
        result.data, text=raw.decode("utf-16"), encoding="utf-16") == raw


def test_strict_refusal_happens_before_hidden_dataset_or_report_writes(
        legacy, tmp_path, mapping, monkeypatch):
    single, _, _ = legacy
    source = crate(tmp_path / "crate.json")
    value = json.loads(source.read_bytes())
    del value["@graph"][0]["description"]
    source.write_text(json.dumps(value), encoding="utf-8")
    output = tmp_path / "published" / "record.yaml"
    seed(output)
    monkeypatch.setattr(sys, "argv", ["transform", "-i", str(source), "-m", str(mapping),
                                    "-o", str(output), "--strict"])
    assert single.main() == 1
    preserved(output)


def test_requested_packaged_diagnostic_failure_preserves_destinations(
        tmp_path, mapping, monkeypatch):
    module = importlib.import_module("fairscape_integration.cli")
    source = crate(tmp_path / "crate.json")
    output = tmp_path / "published" / "record.yaml"
    seed(output)
    checked = []

    class AdditionalDiagnostic:
        def __init__(self, schema):
            pass

        def validate_d4d_yaml(self, path):
            # Mandatory validation remains real; only the additional
            # requested diagnostic's failure is injected.
            checked.append(Path(path).read_bytes())
            assert yaml.safe_load(checked[-1])["id"] == ID
            preserved(output)
            return False, "additional diagnostic refusal"

    monkeypatch.setattr(module, "D4DValidator", AdditionalDiagnostic)
    result = CliRunner().invoke(module.cli, ["transform", str(source), "-m", str(mapping),
                                            "-o", str(output), "--report", "--validate"])
    assert result.exit_code == 1
    assert "additional diagnostic refusal" in result.output
    assert len(checked) == 1
    preserved(output)


@pytest.mark.parametrize("operation", ["single", "merge", "batch"])
def test_requested_api_diagnostic_refusal_preserves_all_file_destinations(
        legacy, tmp_path, mapping, monkeypatch, operation):
    _, _, api = legacy
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    source = crate(inputs / "a.json")
    crate(inputs / "z.json")
    output = tmp_path / "published" / "a_d4d.yaml"
    seed(output)
    second = output.with_name("z_d4d.yaml")
    second.write_bytes(SENTINEL)
    instance = transformer(api, mapping)
    instance.config.validate_output = True
    monkeypatch.setattr(api, "ValidationLevel", SimpleNamespace(
        PROFILE="profile", ROUNDTRIP="roundtrip"), raising=False)
    checked = []

    class AdditionalDiagnostic:
        def validate_all(self, path, **kwargs):
            # Only the optional diagnostic is injected. These mapped records
            # really pass the required schema, so the negative cannot be
            # masked by the separate missing-ID/metadata refusal controls.
            data = yaml.safe_load(Path(path).read_bytes())
            publication.prepare_dataset(data)
            checked.append(data)
            valid = operation == "batch" and len(checked) == 1
            return {"extra": SimpleNamespace(
                passed=valid, errors=[] if valid else ["requested diagnostic refusal"],
                level=SimpleNamespace(value="extra"))}

    instance.validator = AdditionalDiagnostic()
    if operation == "batch":
        monkeypatch.setattr(api, "TransformationConfig", lambda **_: instance.config)
        monkeypatch.setattr(api, "SemanticTransformer", lambda config: instance)
        call = lambda: api.batch_transform_rocrates(inputs, output.parent, validate=True)
    elif operation == "single":
        draft = instance.rocrate_to_d4d(source)
        assert draft.validation_passed is False
        call = lambda: instance.rocrate_to_d4d(source, output_path=output)
    else:
        draft = instance.merge_rocrates([source])
        assert draft["d4d"]["id"] == ID
        call = lambda: instance.merge_rocrates([source], output_path=output)
    with pytest.raises(publication.PublicationError, match="requested.*validation failed"):
        call()
    assert len(checked) == 2
    preserved(output)
    assert second.read_bytes() == SENTINEL
