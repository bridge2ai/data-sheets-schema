"""Real legacy entry points refuse incomplete source batches (#4588, #4591).

These tests run the legacy modules, including the argparse entry point behind
the d4d wrapper. Mock-only wrapper tests did not catch its missing mapping,
path/index mismatch or ignored failure status. Imports stay within each test
so the legacy validation namespace cannot shadow evaluation validation.
"""
from contextlib import contextmanager
import importlib
import importlib.util
import json
from pathlib import Path
import sys

from click.testing import CliRunner
import pytest
import yaml


REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / ".claude/agents/scripts"
LEGACY_NAMES = {
    "mapping_loader", "rocrate_parser", "d4d_builder", "validator",
    "rocrate_merger", "informativeness_scorer", "field_prioritizer",
    "rocrate_to_d4d", "auto_process_rocrates", "_root_gates_transform_api",
}
SENTINEL = b"existing reviewed artifact\n"


@contextmanager
def legacy_imports():
    """Load actual source-tree modules without leaking their import state."""
    before_path = sys.path[:]
    saved = {name: module for name, module in sys.modules.items()
             if name in LEGACY_NAMES or name == "validation"
             or name.startswith("validation.")}
    for name in saved:
        del sys.modules[name]
    sys.path.insert(0, str(SCRIPTS))
    try:
        yield
    finally:
        sys.path[:] = before_path
        for name in list(sys.modules):
            if (name in LEGACY_NAMES or name == "validation"
                    or name.startswith("validation.")):
                del sys.modules[name]
        sys.modules.update(saved)


@pytest.fixture
def legacy():
    with legacy_imports():
        yield {
            name: importlib.import_module(name)
            for name in ("rocrate_to_d4d", "auto_process_rocrates", "mapping_loader")
        }


@pytest.fixture
def mapping(tmp_path):
    path = tmp_path / "mapping.tsv"
    path.write_text(
        "Class\tD4D Property\tType\tFAIRSCAPE RO-Crate Property\t"
        "Covered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0\n"
        "Dataset\ttitle\tstr\tname\t1\t1\n"
        "Dataset\tid\tstr\tidentifier\t1\t1\n",
        encoding="utf-8",
    )
    return path


def crate(path, *, title="Root title", invalid=False):
    graph = [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
         "about": {"@id": "missing-root" if invalid else "./"}},
        {"@id": "./", "@type": "Dataset", "name": title,
         "identifier": "https://example.org/dataset/root"},
    ]
    path.write_text(json.dumps({"@graph": graph}), encoding="utf-8")
    return path


def artifacts(output):
    return [output, output.with_name(f"{output.stem}_merge_report.txt"),
            output.with_name("transformation_report.txt"),
            output.with_name(f"{output.stem}_concatenated.json")]


def seed_artifacts(output, existing):
    if existing:
        output.parent.mkdir()
        for path in artifacts(output):
            path.write_bytes(SENTINEL)


def assert_artifacts_preserved(output, existing):
    if existing:
        for path in artifacts(output):
            assert path.read_bytes() == SENTINEL
    else:
        assert not output.parent.exists()


@pytest.mark.parametrize("mode", ["single", "merge", "rank-and-merge"])
@pytest.mark.parametrize("existing", [False, True])
def test_legacy_transform_refuses_invalid_source_before_publication(
        legacy, mapping, tmp_path, monkeypatch, capsys, mode, existing):
    good = crate(tmp_path / "a.json")
    bad = crate(tmp_path / "z.json", invalid=True)
    output = tmp_path / "published" / "record.yaml"
    seed_artifacts(output, existing)
    args = ["legacy", "--mapping", str(mapping), "--output", str(output)]
    if mode == "single":
        args += ["--input", str(bad)]
    else:
        args += ["--merge", "--inputs", str(good), str(bad)]
        if mode == "rank-and-merge":
            args += ["--auto-prioritize"]
    monkeypatch.setattr(sys, "argv", args)
    assert legacy["rocrate_to_d4d"].main() == 1
    captured = capsys.readouterr()
    assert str(bad) in captured.err
    assert "unresolved" in captured.err
    assert "skipping" not in captured.out
    assert "D4D YAML saved" not in captured.out
    assert_artifacts_preserved(output, existing)


@pytest.mark.parametrize("strategy", ["merge", "concatenate", "hybrid"])
@pytest.mark.parametrize("existing", [False, True])
def test_auto_processing_refuses_later_invalid_source_before_ranking(
        legacy, mapping, tmp_path, monkeypatch, capsys, strategy, existing):
    crate(tmp_path / "a-ro-crate-metadata.json")
    bad = crate(tmp_path / "z-ro-crate-metadata.json", invalid=True)
    output = tmp_path / "published" / "record.yaml"
    seed_artifacts(output, existing)
    monkeypatch.setattr(sys, "argv", [
        "auto", "-i", str(tmp_path), "-o", str(output), "-m", str(mapping),
        "--strategy", strategy, "--top-n", "1",
    ])
    assert legacy["auto_process_rocrates"].main() == 1
    captured = capsys.readouterr()
    assert str(bad) in captured.err
    assert "Rankings:" not in captured.out
    assert_artifacts_preserved(output, existing)


@pytest.mark.parametrize("strategy", ["concatenate", "hybrid"])
@pytest.mark.parametrize("existing", [False, True])
def test_auto_processing_refuses_combined_root_collisions_before_artifacts(
        legacy, mapping, tmp_path, monkeypatch, capsys, strategy, existing):
    # Each source is independently valid; concatenation cannot merge their
    # separate './' roots and repeated metadata IDs into one identity.
    for name in ("a", "b", "c"):
        crate(tmp_path / f"{name}-ro-crate-metadata.json", title=name)
    output = tmp_path / "published" / "record.yaml"
    seed_artifacts(output, existing)
    monkeypatch.setattr(sys, "argv", [
        "auto", "-i", str(tmp_path), "-o", str(output), "-m", str(mapping),
        "--strategy", strategy,
    ])
    assert legacy["auto_process_rocrates"].main() == 1
    assert "duplicate entity IDs" in capsys.readouterr().err
    assert_artifacts_preserved(output, existing)


def test_direct_concatenation_preserves_existing_artifact_on_collision(legacy, tmp_path):
    paths = [crate(tmp_path / "a.json"), crate(tmp_path / "b.json")]
    before = {path: path.read_bytes() for path in paths}
    output = tmp_path / "published" / "record.yaml"
    seed_artifacts(output, True)
    with pytest.raises(ValueError, match="duplicate entity IDs"):
        legacy["auto_process_rocrates"].concatenate_rocrates(paths, output)
    assert_artifacts_preserved(output, True)
    assert {path: path.read_bytes() for path in paths} == before


@pytest.mark.parametrize("strategy", ["merge", "concatenate", "hybrid"])
def test_auto_processing_retains_valid_single_source(
        legacy, mapping, tmp_path, monkeypatch, strategy):
    source = crate(tmp_path / "a-ro-crate-metadata.json")
    before = source.read_bytes()
    output = tmp_path / "published" / "record.yaml"
    monkeypatch.setattr(sys, "argv", [
        "auto", "-i", str(tmp_path), "-o", str(output), "-m", str(mapping),
        "--strategy", strategy,
    ])
    assert legacy["auto_process_rocrates"].main() == 0
    assert yaml.safe_load(output.read_text()) == {
        "title": "Root title", "id": "https://example.org/dataset/root"}
    assert source.read_bytes() == before


@pytest.mark.parametrize("existing", [False, True])
def test_directory_batch_preflights_all_roots_before_any_output(
        legacy, tmp_path, existing):
    spec = importlib.util.spec_from_file_location(
        "_root_gates_transform_api", REPO / "src/transformation/transform_api.py")
    api = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = api
    spec.loader.exec_module(api)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    crate(inputs / "a.json")
    crate(inputs / "z.json", invalid=True)
    output_dir = tmp_path / "published"
    if existing:
        output_dir.mkdir()
        for name in ("a_d4d.yaml", "z_d4d.yaml"):
            (output_dir / name).write_bytes(SENTINEL)
    with pytest.raises(ValueError, match="unresolved"):
        api.batch_transform_rocrates(inputs, output_dir, validate=False)
    if existing:
        assert {p.name: p.read_bytes() for p in output_dir.iterdir()} == {
            "a_d4d.yaml": SENTINEL, "z_d4d.yaml": SENTINEL,
        }
    else:
        assert not output_dir.exists()


def test_d4d_default_mapping_refuses_missing_required_id(
        legacy, tmp_path, monkeypatch):
    from data_sheets_schema.cli import cli

    first = crate(tmp_path / "a.json", title="First")
    primary = crate(tmp_path / "b.json", title="Chosen primary")
    first.write_text(first.read_text().replace(
        'https://example.org/dataset/root', 'doi:10.1234/Secondary'))
    primary.write_text(json.dumps({'@graph': [
        {'@type': 'Dataset', 'name': 'Chosen anonymous primary'}]}))
    output = tmp_path / "published" / "record.yaml"
    seed_artifacts(output, True)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(cli, [
        "rocrate", "transform", "--merge", "--inputs", str(first),
        "--inputs", str(primary), "--primary", str(primary), "-o", str(output),
    ])
    # An anonymous selected primary still lacks required Dataset.id. The new
    # explicit route must not borrow the secondary's identity or invent one.
    assert result.exit_code == 1, result.output
    assert "id" in result.output and "Dataset publication refused" in result.output
    assert_artifacts_preserved(output, True)


def test_legacy_valid_mapping_preserves_selected_primary(legacy, mapping, tmp_path, monkeypatch):
    first = crate(tmp_path / "a.json", title="First")
    primary = crate(tmp_path / "b.json", title="Chosen primary")
    output = tmp_path / "record.yaml"
    monkeypatch.setattr(sys, "argv", [
        "transform", "--merge", "--inputs", str(first), str(primary),
        "--primary", "1", "-m", str(mapping), "-o", str(output),
    ])
    assert legacy["rocrate_to_d4d"].main() == 0
    assert yaml.safe_load(output.read_text())["title"] == "Chosen primary"
    assert f"# Primary source: {primary.name}\n" in output.read_text()
    report = output.with_name("record_merge_report.txt").read_text()
    assert f"2. {primary.name} (PRIMARY)\n" in report
    assert f"1. {first.name} (PRIMARY)" not in report


@pytest.mark.parametrize("merge", [False, True])
def test_d4d_transform_propagates_legacy_root_refusal(legacy, tmp_path, merge):
    from data_sheets_schema.cli import cli

    good = crate(tmp_path / "a.json")
    bad = crate(tmp_path / "z.json", invalid=True)
    output = tmp_path / "published" / "record.yaml"
    seed_artifacts(output, True)
    args = ["rocrate", "transform", "-o", str(output)]
    args += (["--merge", "--inputs", str(good), "--inputs", str(bad)]
             if merge else [str(bad)])
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 1, result.output
    assert "unresolved" in result.output
    assert "D4D YAML saved" not in result.output
    assert_artifacts_preserved(output, True)


def test_d4d_transform_rejects_primary_outside_inputs(legacy, tmp_path):
    from data_sheets_schema.cli import cli

    included = crate(tmp_path / "a.json")
    other = crate(tmp_path / "b.json")
    output = tmp_path / "published" / "record.yaml"
    result = CliRunner().invoke(cli, [
        "rocrate", "transform", "--merge", "--inputs", str(included),
        "--primary", str(other), "-o", str(output),
    ])
    assert result.exit_code == 2, result.output
    assert "--primary must name one of the --inputs files" in result.output
    assert not output.parent.exists()


@pytest.mark.parametrize("empty", [False, True])
def test_real_d4d_parse_preserves_rootless_inspection(legacy, tmp_path, empty):
    from data_sheets_schema.cli import cli

    source = crate(tmp_path / "crate.json", invalid=True)
    if empty:
        source.write_text('{"@graph": []}', encoding="utf-8")
    output = tmp_path / "entities.json"
    result = CliRunner().invoke(cli, [
        "rocrate", "parse", str(source), "--output", str(output),
    ])
    assert result.exit_code == 0, result.output
    assert "No unambiguous root" in result.output
    expected = {e["@id"]: e for e in json.loads(source.read_text())["@graph"]}
    assert json.loads(output.read_text()) == expected


def test_real_d4d_parse_preserves_destination_on_duplicate_ids(legacy, tmp_path):
    from data_sheets_schema.cli import cli

    source = tmp_path / "crate.json"
    source.write_text(json.dumps({"@graph": [
        {"@id": "./", "@type": "Dataset", "name": "First"},
        {"@id": "./", "@type": "Dataset", "name": "Second"},
    ]}), encoding="utf-8")
    output = tmp_path / "entities.json"
    output.write_bytes(SENTINEL)
    result = CliRunner().invoke(cli, [
        "rocrate", "parse", str(source), "--output", str(output),
    ])
    assert result.exit_code == 1, result.output
    assert "duplicate" in result.output.lower()
    assert output.read_bytes() == SENTINEL
