"""Independent final-byte and preservation controls (#4629, #4631).

The successful records use the packaged Dataset schema. Failure injection is
limited to the validator-availability and filesystem-staging boundaries.
"""
from contextlib import contextmanager
from copy import deepcopy
import importlib
import importlib.util
import json
from pathlib import Path
import sys

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema import legacy_publication as publication


REPO = Path(__file__).resolve().parents[2]
SENTINEL = b"Reviewed historical artifact; preserve on refusal.\n"
LEGACY_NAMES = {
    "rocrate_to_d4d", "mapping_loader", "rocrate_parser", "d4d_builder",
    "rocrate_merger", "informativeness_scorer", "field_prioritizer", "validator",
    "_publication_adversarial_api",
}


def record():
    return {
        "id": "https://example.org/datasets/publication-control",
        "title": "A source title",
        "description": "Original source text: naïve\nSecond line, unchanged.",
        "keywords": ["first", "second", "first"],
        "is_tabular": False,
        "resources": [{"id": "https://example.org/datasets/member", "title": "Member"}],
    }


@contextmanager
def legacy_module():
    def affected(name):
        return name.split(".", 1)[0] in LEGACY_NAMES | {"validation"}

    old_path = sys.path[:]
    previous = {name: value for name, value in sys.modules.items() if affected(name)}
    for name in previous:
        del sys.modules[name]
    sys.path.insert(0, str(REPO / ".claude/agents/scripts"))
    try:
        yield importlib.import_module("rocrate_to_d4d")
    finally:
        sys.path[:] = old_path
        for name in list(sys.modules):
            if affected(name):
                del sys.modules[name]
        sys.modules.update(previous)


def cli_inputs(tmp_path):
    mapping = tmp_path / "mapping.tsv"
    mapping.write_text(
        "Class\tD4D Property\tType\tFAIRSCAPE RO-Crate Property\t"
        "Covered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0\n"
        "Dataset\tid\tstr\tidentifier\t1\t1\n"
        "Dataset\ttitle\tstr\tname\t1\t1\n",
        encoding="utf-8",
    )
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"@graph": [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": "./"}},
        {"@id": "./", "@type": "Dataset", "identifier": record()["id"], "name": "Original title"},
    ]}), encoding="utf-8")
    return source, mapping


def packaged_transform(source, mapping, output, *options):
    from fairscape_integration.cli import cli

    return CliRunner().invoke(cli, ["transform", str(source), "--mapping", str(mapping),
                                    "--output", str(output), *options])


def test_exact_validated_bytes_preserve_source_text_lists_false_and_members():
    dataset = record()
    before = deepcopy(dataset)
    text = "# Original provenance header\n" + yaml.safe_dump(dataset, allow_unicode=True, sort_keys=False)
    raw = publication.prepare_dataset(dataset, text=text)
    assert raw == text.encode("utf-8")
    assert yaml.safe_load(raw) == before
    assert type(yaml.safe_load(raw)["is_tabular"]) is bool
    assert dataset == before


@pytest.mark.parametrize("field,before,after", [
    ("is_tabular", False, 0),
    ("title", "false", False),
    ("title", "2026-10-07", "date-token"),
    ("keywords", ["one"], "one"),
    ("resources", [{"id": "https://example.org/member", "is_tabular": False}],
     [{"id": "https://example.org/member", "is_tabular": 0}]),
])
def test_readback_type_changes_refuse_before_schema_validation(monkeypatch, field, before, after):
    dataset = {"id": record()["id"], field: before}
    changed = {"id": record()["id"], field: after}
    text = yaml.safe_dump(changed)
    if after == "date-token":
        text = text.replace("date-token", "2026-10-07")

    def unexpected_validator(*args):
        pytest.fail("Changed mapped values must be refused before schema validation")

    monkeypatch.setattr(publication, "_validator", unexpected_validator)
    with pytest.raises(publication.PublicationError, match="changed mapped values or types"):
        publication.prepare_dataset(dataset, text=text)


@pytest.mark.parametrize("extra", [
    "title: overwritten\n",
    "title: A source title\n",
    "resources:\n- id: https://example.org/member\n  title: first\n  title: second\n",
])
def test_duplicate_yaml_keys_never_become_last_wins_records(extra):
    dataset = record()
    base = dict(dataset)
    if extra.startswith("resources:"):
        del base["resources"]
    text = yaml.safe_dump(base) + extra
    with pytest.raises(publication.PublicationError, match="Duplicate YAML key"):
        publication.prepare_dataset(dataset, text=text)


@pytest.mark.parametrize("dataset", [
    {"title": "Missing required id"},
    {"id": record()["id"], "invented_slot": "must not disappear"},
    {"id": record()["id"], "resources": [{"id": "https://example.org/member", "invented_slot": "nested"}]},
    {"id": record()["id"], "is_tabular": "false"},
])
def test_actual_closed_schema_rejects_missing_unknown_nested_and_wrong_type(dataset):
    before = deepcopy(dataset)
    with pytest.raises(publication.PublicationError, match="Dataset publication refused"):
        publication.prepare_dataset(dataset)
    assert dataset == before


def test_metadata_is_explicitly_blocked_without_moving_or_dropping_it():
    dataset = {"id": record()["id"], "transformation_metadata": {"source": "retained"}}
    before = deepcopy(dataset)
    with pytest.raises(publication.PublicationError, match="transformation_metadata.*#4630"):
        publication.prepare_dataset(dataset)
    assert dataset == before


def test_newline_in_legacy_provenance_cannot_inject_a_second_dataset_id(tmp_path):
    output = tmp_path / "record.yaml"
    output.write_bytes(SENTINEL)
    with legacy_module() as legacy:
        with pytest.raises(publication.PublicationError, match="Duplicate YAML key"):
            legacy.save_d4d_yaml(record(), output, Path("mapping.tsv"),
                                 rocrate_path=Path("source\nid: injected.json"))
    assert output.read_bytes() == SENTINEL


@pytest.mark.parametrize("existing", [False, True])
def test_required_validator_unavailable_preserves_real_cli_dataset_and_report(
        tmp_path, monkeypatch, existing):
    source, mapping = cli_inputs(tmp_path)
    originals = {path: path.read_bytes() for path in (source, mapping)}
    output = tmp_path / "published" / "record.yaml"
    report = output.with_name("record_report.txt")
    if existing:
        output.parent.mkdir()
        output.write_bytes(SENTINEL)
        report.write_bytes(SENTINEL)

    def unavailable(*args):
        raise ImportError("mandatory validator unavailable for this control")

    monkeypatch.setattr(publication, "_validator", unavailable)
    # No optional --validate: the mandatory publication boundary must still run.
    result = packaged_transform(source, mapping, output, "--report")
    assert result.exit_code != 0
    assert "mandatory validator unavailable" in result.output
    assert "D4D YAML written" not in result.output
    assert {path: path.read_bytes() for path in originals} == originals
    if existing:
        assert output.read_bytes() == report.read_bytes() == SENTINEL
        assert set(output.parent.iterdir()) == {output, report}
    else:
        assert not output.parent.exists()


def test_second_cli_artifact_staging_failure_cannot_replace_first(tmp_path, monkeypatch):
    source, mapping = cli_inputs(tmp_path)
    originals = {path: path.read_bytes() for path in (source, mapping)}
    output = tmp_path / "record.yaml"
    report = tmp_path / "record_report.txt"
    output.write_bytes(SENTINEL)
    report.write_bytes(SENTINEL)
    real_temporary = publication.tempfile.NamedTemporaryFile
    stages = []

    def staged(*args, **kwargs):
        stages.append(kwargs)
        if len(stages) == 2:
            raise OSError("second artifact cannot be staged")
        return real_temporary(*args, **kwargs)

    monkeypatch.setattr(publication.tempfile, "NamedTemporaryFile", staged)
    result = packaged_transform(source, mapping, output, "--report")
    assert result.exit_code != 0
    assert "second artifact cannot be staged" in result.output
    assert len(stages) == 2
    assert output.read_bytes() == report.read_bytes() == SENTINEL
    assert {path: path.read_bytes() for path in originals} == originals
    assert set(tmp_path.iterdir()) == {source, mapping, output, report}


def test_all_files_are_fully_staged_before_first_replacement(tmp_path, monkeypatch):
    paths = [tmp_path / "dataset.yaml", tmp_path / "report.txt"]
    raw = [publication.prepare_dataset(record()), b"Retained report bytes\n"]
    for path in paths:
        path.write_bytes(SENTINEL)
    real_replace = publication.os.replace
    replaced = []

    def replace(source, target):
        if not replaced:
            assert [path.read_bytes() for path in paths] == [SENTINEL, SENTINEL]
            staged = list(tmp_path.glob(".*.tmp"))
            assert len(staged) == 2
            assert {path.read_bytes() for path in staged} == set(raw)
        replaced.append(Path(target))
        return real_replace(source, target)

    monkeypatch.setattr(publication.os, "replace", replace)
    publication.publish(zip(paths, raw))
    assert replaced == paths
    assert [path.read_bytes() for path in paths] == raw
    assert set(tmp_path.iterdir()) == set(paths)


@pytest.mark.parametrize("alias", ["same", "dotdot", "symlink"])
def test_duplicate_resolved_destinations_refuse_without_staging(tmp_path, alias):
    target = tmp_path / "record.yaml"
    target.write_bytes(SENTINEL)
    if alias == "same":
        duplicate = target
    elif alias == "dotdot":
        (tmp_path / "child").mkdir()
        duplicate = tmp_path / "child" / ".." / target.name
    else:
        duplicate = tmp_path / "alias.yaml"
        duplicate.symlink_to(target)
    before = set(tmp_path.iterdir())
    with pytest.raises(publication.PublicationError, match="overlap"):
        publication.publish([(target, b"one"), (duplicate, b"two")])
    assert target.read_bytes() == SENTINEL
    assert set(tmp_path.iterdir()) == before
    if alias == "symlink":
        assert duplicate.is_symlink()


@pytest.mark.parametrize("protected_kind", ["source", "mapping"])
@pytest.mark.parametrize("destination_kind", ["dataset", "report"])
@pytest.mark.parametrize("alias", [False, True])
def test_real_cli_preserves_all_input_roles_when_outputs_alias_them(
        tmp_path, protected_kind, destination_kind, alias):
    source, mapping = cli_inputs(tmp_path)
    protected = source if protected_kind == "source" else mapping
    if destination_kind == "dataset":
        output = protected
        if alias:
            output = tmp_path / "output-alias.yaml"
            output.symlink_to(protected)
    else:
        output = tmp_path / "record.yaml"
        output.write_bytes(SENTINEL)
        report = tmp_path / "record_report.txt"
        if alias:
            report.symlink_to(protected)
        else:
            protected.rename(report)
            if protected_kind == "source":
                source = report
            else:
                mapping = report
            protected = report
    originals = {path: path.read_bytes() for path in (source, mapping)}
    before = set(tmp_path.iterdir())
    result = packaged_transform(source, mapping, output, "--report")
    assert result.exit_code != 0
    assert "overlap" in result.output.lower() or "protected" in result.output.lower()
    assert "D4D YAML written" not in result.output
    assert {path: path.read_bytes() for path in originals} == originals
    assert set(tmp_path.iterdir()) == before
    if destination_kind == "report":
        assert output.read_bytes() == SENTINEL
    if alias:
        assert (output if destination_kind == "dataset" else report).is_symlink()


@pytest.mark.parametrize("relation", ["equal", "ancestor", "descendant", "canonical_alias"])
def test_protected_input_collision_is_checked_before_any_other_output_changes(tmp_path, relation):
    source = tmp_path / "input" / "source.json"
    source.parent.mkdir()
    source.write_bytes(b"original input bytes")
    first = tmp_path / "valid-output.yaml"
    first.write_bytes(SENTINEL)
    if relation == "equal":
        colliding = source
    elif relation == "ancestor":
        colliding = source.parent
    elif relation == "descendant":
        colliding = source / "nested.yaml"
    else:
        link = tmp_path / "linked-input"
        link.symlink_to(source.parent, target_is_directory=True)
        colliding = link / source.name
    before = set(tmp_path.rglob("*"))
    with pytest.raises(publication.PublicationError):
        publication.publish([(first, b"new Dataset"), (colliding, b"new report")],
                            protected=[source])
    assert source.read_bytes() == b"original input bytes"
    assert first.read_bytes() == SENTINEL
    assert set(tmp_path.rglob("*")) == before


@pytest.mark.parametrize("reverse", [False, True])
def test_output_ancestor_collision_refuses_before_creating_any_directory(tmp_path, reverse):
    root = tmp_path / "fresh"
    paths = [(root, b"one"), (root / "nested.yaml", b"two")]
    if reverse:
        paths.reverse()
    with pytest.raises(publication.PublicationError, match="overlap"):
        publication.publish(paths)
    assert not root.exists()


def test_existing_directory_destination_cannot_publish_an_earlier_file(tmp_path):
    first = tmp_path / "record.yaml"
    first.write_bytes(SENTINEL)
    directory = tmp_path / "report.txt"
    directory.mkdir()
    child = directory / "retained.txt"
    child.write_bytes(SENTINEL)
    with pytest.raises(publication.PublicationError):
        publication.publish([(first, b"new Dataset"), (directory, b"new report")])
    assert first.read_bytes() == child.read_bytes() == SENTINEL
    assert set(tmp_path.iterdir()) == {first, directory}


def test_packaged_schema_is_implicitly_protected(tmp_path, monkeypatch):
    from data_sheets_schema import resources

    package = tmp_path / "package"
    schema = package / "schema" / "data_sheets_schema_all.yaml"
    schema.parent.mkdir(parents=True)
    schema.write_bytes(b"pinned schema control bytes")
    monkeypatch.setattr(resources, "PACKAGE_ROOT", package)
    with pytest.raises(publication.PublicationError):
        publication.publish([(schema, b"do not overwrite schema")])
    assert schema.read_bytes() == b"pinned schema control bytes"


def test_batch_cannot_publish_an_earlier_result_over_a_later_source(tmp_path, monkeypatch):
    source, mapping = cli_inputs(tmp_path)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    first = inputs / "source.json"
    second = inputs / "source_d4d.yaml"
    first.write_bytes(source.read_bytes())
    second.write_bytes(source.read_bytes())
    before = {path: path.read_bytes() for path in (first, second, mapping)}
    with legacy_module():
        spec = importlib.util.spec_from_file_location(
            "_publication_adversarial_api", REPO / "src/transformation/transform_api.py")
        api = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        # Explicitly disable the separate metadata envelope; both records pass
        # the real mandatory validator, so path protection is the refusal.
        config = api.TransformationConfig(mapping_file=mapping, validate_input=False,
                                          validate_output=False, preserve_provenance=False)
        monkeypatch.setattr(api, "TransformationConfig", lambda **kwargs: config)
        with pytest.raises(publication.PublicationError, match="overlaps protected input"):
            api.batch_transform_rocrates(inputs, inputs, pattern="source*", validate=False)
    assert {path: path.read_bytes() for path in before} == before
    assert set(inputs.iterdir()) == {first, second}
