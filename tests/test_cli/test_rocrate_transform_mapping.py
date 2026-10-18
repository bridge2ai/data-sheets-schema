"""Real d4d wrapper → legacy producer → required Dataset gate (#4638)."""
import json
from pathlib import Path
import sys

from click.testing import CliRunner
import pytest
import yaml

from data_sheets_schema.cli import cli
from tests.test_rocrate.test_legacy_root_gates import legacy_imports


REPO = Path(__file__).resolve().parents[2]
DEFAULT = REPO / "data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv"
SENTINEL = b"Previously reviewed artifact; preserve on refusal.\n"
TEXT = "Source text: café.\nA second line, intact."
IDENTIFIER = "https://example.org/datasets/explicit-mapping"


@pytest.fixture(autouse=True)
def actual_legacy_modules(monkeypatch):
    # Only isolate legacy imports and choose the repository context. The CLI,
    # producer, mapping loader, builder, merger and schema gate all run for real.
    monkeypatch.chdir(REPO)
    with legacy_imports():
        yield


@pytest.fixture
def mapping(tmp_path):
    path = tmp_path / "selected mapping.tsv"
    path.write_text(
        "D4D Property\tType\tFAIRSCAPE RO-Crate Property\t"
        "Covered by FAIRSCAPE? Yes =1; No = 0\tDirect mapping? Yes =1; No = 0\n"
        "id\tstr\tidentifier\t1\t1\n"
        "title\tstr\tselectedTitle\t1\t1\n"
        "description\tstr\tdescription\t1\t1\n"
        "keywords\tlist[str]\tkeywords\t1\t1\n"
        "is_tabular\tbool\ttabular\t1\t1\n",
        encoding="utf-8",
    )
    return path


def source(path, *, title="Selected root title", tabular=False):
    root = {"@id": "#root", "@type": "Dataset", "identifier": IDENTIFIER,
            "name": "Default route must not replace selectedTitle", "selectedTitle": title,
            "description": TEXT, "keywords": ["second", "first", "second"]}
    if tabular is not None:
        root["tabular"] = tabular
    path.write_text(json.dumps({"@graph": [
        {"@id": "./", "@type": "Dataset", "selectedTitle": "Member title",
         "tabular": True, "identifier": "https://example.org/member"},
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": "#root"}},
        root,
    ]}), encoding="utf-8")
    return path


def inputs(tmp_path):
    return [source(tmp_path / "first.json", title="First selected title"),
            source(tmp_path / "second.json", title="Second selected title")]


def report_path(output, merge):
    return (output.with_name(output.stem + "_merge_report.txt") if merge
            else output.with_name("transformation_report.txt"))


def seed(output, merge):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(SENTINEL)
    report_path(output, merge).write_bytes(SENTINEL)


def invoke(sources, output, merge, mapping=None):
    args = ["rocrate", "transform", "-o", str(output)]
    if mapping is not None:
        args += ["--mapping", str(mapping)]
    if merge:
        args += ["--merge", "--inputs", str(sources[0]), "--inputs", str(sources[1]),
                 "--primary", str(sources[1])]
    else:
        args += [str(sources[0])]
    previous = sys.argv
    result = CliRunner().invoke(cli, args)
    assert sys.argv is previous
    return result


@pytest.mark.parametrize("merge", [False, True])
@pytest.mark.parametrize("relative", [False, True])
def test_selected_mapping_reaches_actual_single_and_merge_producers(
        tmp_path, mapping, monkeypatch, merge, relative):
    sources = inputs(tmp_path)
    before = {path: path.read_bytes() for path in [*sources, mapping, DEFAULT]}
    output = tmp_path / "published" / "dataset.yaml"
    selected = mapping
    if relative:
        monkeypatch.chdir(tmp_path)
        selected = mapping.relative_to(tmp_path)
    result = invoke(sources, output, merge, selected)
    assert result.exit_code == 0, result.output
    data = yaml.safe_load(output.read_bytes())
    assert data["id"] == IDENTIFIER
    assert data["title"] == ("Second selected title" if merge else "First selected title")
    assert data["is_tabular"] is False
    if merge:
        # Existing merger decorates/combines descriptions and unions keywords.
        assert TEXT in data["description"]
        assert data["keywords"] == ["second", "first"]
        assert "# Primary source: second.json" in output.read_text()
    else:
        assert data["description"] == TEXT
        assert data["keywords"] == ["second", "first", "second"]
    assert f"# Mapping: {mapping.name}" in output.read_text()
    assert "transformation_metadata" not in data
    assert report_path(output, merge).is_file()
    assert {path: path.read_bytes() for path in before} == before


def test_missing_root_value_is_not_taken_from_member(tmp_path, mapping):
    crate = source(tmp_path / "missing-root-value.json", tabular=None)
    output = tmp_path / "dataset.yaml"
    result = invoke([crate], output, False, mapping)
    assert result.exit_code == 0, result.output
    assert "is_tabular" not in yaml.safe_load(output.read_bytes())


@pytest.mark.parametrize("merge", [False, True])
def test_omitted_and_explicit_default_keep_refusing_without_output_changes(tmp_path, merge):
    sources = inputs(tmp_path)
    before = {path: path.read_bytes() for path in [*sources, DEFAULT]}
    output = tmp_path / "published" / "dataset.yaml"
    seed(output, merge)
    for selected in (None, DEFAULT):
        result = invoke(sources, output, merge, selected)
        assert result.exit_code == 1, result.output
        assert "Dataset publication refused" in result.output
        assert "D4D YAML saved" not in result.output
        assert output.read_bytes() == report_path(output, merge).read_bytes() == SENTINEL
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("merge", [False, True])
@pytest.mark.parametrize("invalid", ["missing_id", "unknown_field"])
def test_selected_invalid_candidate_preserves_outputs_and_input_files(tmp_path, mapping, merge, invalid):
    text = mapping.read_text()
    if invalid == "missing_id":
        text = text.replace("id\tstr\tidentifier\t1\t1\n", "")
    else:
        text += "unsupported_field\tstr\tselectedTitle\t1\t1\n"
    mapping.write_text(text)
    sources = inputs(tmp_path)
    before = {path: path.read_bytes() for path in [*sources, mapping]}
    output = tmp_path / "published" / "dataset.yaml"
    seed(output, merge)
    result = invoke(sources, output, merge, mapping)
    assert result.exit_code == 1, result.output
    assert "Dataset publication refused" in result.output
    assert output.read_bytes() == report_path(output, merge).read_bytes() == SENTINEL
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("merge", [False, True])
@pytest.mark.parametrize("collision", ["dataset", "report"])
def test_selected_mapping_cannot_be_overwritten_by_either_publication(tmp_path, mapping, merge, collision):
    sources = inputs(tmp_path)
    output = mapping if collision == "dataset" else tmp_path / "dataset.yaml"
    if collision == "report":
        mapping = mapping.rename(report_path(output, merge))
        output.write_bytes(SENTINEL)
    before = {path: path.read_bytes() for path in [*sources, mapping]}
    result = invoke(sources, output, merge, mapping)
    assert result.exit_code == 1, result.output
    assert "protected input" in result.output
    assert {path: path.read_bytes() for path in before} == before
    if collision == "report":
        assert output.read_bytes() == SENTINEL
    else:
        assert not report_path(output, merge).exists()


@pytest.mark.parametrize("kind", ["missing", "directory"])
def test_mapping_path_is_checked_before_source_parsing(tmp_path, kind):
    broken = tmp_path / "not-json.json"
    broken.write_text("not JSON")
    selected = tmp_path / "invalid-mapping"
    if kind == "directory":
        selected.mkdir()
    output = tmp_path / "dataset.yaml"
    output.write_bytes(SENTINEL)
    result = invoke([broken], output, False, selected)
    assert result.exit_code == 2, result.output
    assert "--mapping" in result.output
    assert "Error parsing" not in result.output
    assert output.read_bytes() == SENTINEL
