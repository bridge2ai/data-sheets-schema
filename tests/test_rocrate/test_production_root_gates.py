"""No Dataset, merge, or score may be produced from an ambiguous root (#4588)."""

import contextlib
import copy
import csv
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from click.testing import CliRunner


REPO = Path(__file__).resolve().parents[2]
LEGACY_NAMES = {
    "mapping_loader", "rocrate_parser", "d4d_builder", "validator",
    "rocrate_merger", "informativeness_scorer", "field_prioritizer",
    "validation", "root_gate_transform_api",
}
SENTINEL = b"Existing reviewed output\nDo not overwrite.\n"


@contextlib.contextmanager
def isolated_legacy_imports():
    """Restore namespaces the source-tree API imports, including validation."""
    def affected(name):
        return name.split(".", 1)[0] in LEGACY_NAMES

    previous_path = sys.path[:]
    previous_modules = {name: module for name, module in sys.modules.items()
                        if affected(name)}
    for name in previous_modules:
        del sys.modules[name]
    sys.path.insert(0, str(REPO / ".claude/agents/scripts"))
    try:
        yield
    finally:
        sys.path[:] = previous_path
        for name in list(sys.modules):
            if affected(name):
                del sys.modules[name]
        sys.modules.update(previous_modules)


@pytest.fixture(params=["packaged", "hidden"])
def consumers(request):
    names = {
        "Parser": ("rocrate_parser", "ROCrateParser"),
        "Mapping": ("mapping_loader", "MappingLoader"),
        "Builder": ("d4d_builder", "D4DBuilder"),
        "Merger": ("rocrate_merger", "ROCrateMerger"),
        "Scorer": ("informativeness_scorer", "InformativenessScorer"),
    }
    context = isolated_legacy_imports() if request.param == "hidden" else contextlib.nullcontext()
    prefix = "" if request.param == "hidden" else "fairscape_integration.utils."
    with context:
        yield SimpleNamespace(**{
            key: getattr(importlib.import_module(prefix + module), cls)
            for key, (module, cls) in names.items()
        })


@pytest.fixture
def mapping_file(tmp_path):
    path = tmp_path / "mapping.tsv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(["D4D Property", "FAIRSCAPE RO-Crate Property", "Type",
                         "Covered by FAIRSCAPE? Yes =1; No = 0",
                         "Direct mapping? Yes =1; No = 0"])
        writer.writerows([
            ["title", "name", "string", "1", "1"],
            ["description", "description", "string", "1", "1"],
            ["keywords", "keywords", "list", "1", "1"],
        ])
    return path


def valid_crate():
    # The conventional './' Dataset is a member here. Only the descriptor's
    # explicit target is authoritative, regardless of graph order.
    return {"@context": "https://w3id.org/ro/crate/1.1/context", "@graph": [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
         "about": {"@id": "#root"}},
        {"@id": "./", "@type": "Dataset", "name": "Wrong member title"},
        {"@id": "#root", "@type": "Dataset", "name": "Authoritative root",
         "description": "Original root text.", "keywords": ["root", "shared"]},
    ]}


@pytest.fixture(params=["conflicting", "unresolved", "duplicate_root", "empty"])
def invalid_crate(request):
    crate = valid_crate()
    graph = crate["@graph"]
    if request.param == "conflicting":
        graph.append({"@id": "ro-crate-metadata.jsonld", "@type": "CreativeWork",
                      "about": {"@id": "./"}})
    elif request.param == "unresolved":
        graph[0]["about"] = {"@id": "#missing"}
    elif request.param == "duplicate_root":
        graph.append({"@id": "#root", "@type": "Dataset", "name": "Other root"})
    else:
        crate["@graph"] = []
    return crate


def write_crate(tmp_path, name, crate):
    path = tmp_path / (name + ".json")
    path.write_text(json.dumps(crate), encoding="utf-8")
    return path


def parser_pair(consumers, tmp_path, invalid_crate):
    good = consumers.Parser(str(write_crate(tmp_path, "valid", valid_crate())))
    bad = consumers.Parser(str(write_crate(tmp_path, "invalid", invalid_crate)))
    return good, bad


def assert_preserved(path, existed):
    if existed:
        assert path.read_bytes() == SENTINEL
    else:
        assert not path.exists()


@pytest.mark.parametrize("reverse", [False, True])
def test_descriptor_root_builds_without_member_leakage(consumers, tmp_path, mapping_file, reverse):
    crate = valid_crate()
    if reverse:
        crate["@graph"].reverse()
    parsed = consumers.Parser(str(write_crate(tmp_path, "source", crate)))
    mapping = consumers.Mapping(str(mapping_file))
    assert consumers.Builder(mapping).build_dataset(parsed) == {
        "title": "Authoritative root", "description": "Original root text.",
        "keywords": ["root", "shared"],
    }
    assert consumers.Scorer().score_rocrate(parsed, mapping)["d4d_coverage"] == 3


@pytest.mark.parametrize("reverse", [False, True])
def test_invalid_build_preserves_previous_dataset(consumers, tmp_path, mapping_file,
                                                  invalid_crate, reverse):
    if reverse:
        invalid_crate["@graph"].reverse()
    good, bad = parser_pair(consumers, tmp_path, invalid_crate)
    # Inspection itself remains available for empty or ambiguous graphs.
    assert bad.get_root_dataset() is None
    builder = consumers.Builder(consumers.Mapping(str(mapping_file)))
    previous = copy.deepcopy(builder.build_dataset(good))
    with pytest.raises(ValueError, match="(?i)root"):
        builder.build_dataset(bad)
    assert builder.d4d_data == previous


def test_later_invalid_merge_preserves_dataset_provenance_and_statistics(
        consumers, tmp_path, mapping_file, invalid_crate, capsys):
    good, bad = parser_pair(consumers, tmp_path, invalid_crate)
    merger = consumers.Merger(consumers.Mapping(str(mapping_file)))
    merger.merge_rocrates([good])
    previous = copy.deepcopy((merger.get_merged_dataset(), merger.get_provenance(),
                              merger.get_merge_stats()))
    capsys.readouterr()
    with pytest.raises(ValueError, match="(?i)root"):
        merger.merge_rocrates([good, bad])
    assert (merger.get_merged_dataset(), merger.get_provenance(),
            merger.get_merge_stats()) == previous
    assert "Merging" not in capsys.readouterr().out


@pytest.mark.parametrize("operation", ["comparison", "rank"])
def test_later_invalid_source_prevents_any_scoring(
        consumers, tmp_path, mapping_file, invalid_crate, operation, capsys, monkeypatch):
    good, bad = parser_pair(consumers, tmp_path, invalid_crate)
    mapping = consumers.Mapping(str(mapping_file))
    scorer = consumers.Scorer()
    # Real parsers and real mapping; spy only on property consumption to detect
    # a partial score produced before the invalid comparison source is refused.
    accessed = Mock(wraps=good.get_property)
    monkeypatch.setattr(good, "get_property", accessed)
    capsys.readouterr()
    with pytest.raises(ValueError, match="(?i)root"):
        if operation == "comparison":
            scorer.score_rocrate(good, mapping, [bad])
        else:
            scorer.rank_rocrates([good, bad], mapping)
    accessed.assert_not_called()
    output = capsys.readouterr().out
    assert "Scored" not in output
    assert "Ranked" not in output


@pytest.mark.parametrize("command", ["transform", "merge"])
@pytest.mark.parametrize("existing", [False, True])
def test_cli_refusal_preserves_dataset_and_report(
        tmp_path, mapping_file, invalid_crate, command, existing):
    from fairscape_integration.cli import cli

    good = write_crate(tmp_path, "valid", valid_crate())
    bad = write_crate(tmp_path, "invalid", invalid_crate)
    output = tmp_path / "record.yaml"
    report = tmp_path / ("record_report.txt" if command == "transform"
                         else "record_merge_report.txt")
    if existing:
        output.write_bytes(SENTINEL)
        report.write_bytes(SENTINEL)
    inputs = [str(bad)] if command == "transform" else [str(good), str(bad)]
    result = CliRunner().invoke(cli, [command, *inputs, "-m", str(mapping_file),
                                     "-o", str(output), "--report"])
    assert result.exit_code == 1, result.output
    assert "root" in result.output.lower()
    assert "written to" not in result.output
    assert_preserved(output, existing)
    assert_preserved(report, existing)


def test_cli_rank_refuses_entire_batch(tmp_path, mapping_file, invalid_crate):
    from fairscape_integration.cli import cli

    good = write_crate(tmp_path, "valid", valid_crate())
    bad = write_crate(tmp_path, "invalid", invalid_crate)
    result = CliRunner().invoke(cli, ["rank", str(good), str(bad),
                                     "-m", str(mapping_file)])
    assert result.exit_code == 1, result.output
    assert "root" in result.output.lower()
    assert "Recommendation:" not in result.output
    assert "score:" not in result.output


@pytest.fixture
def api():
    # Load a fresh API module so unrelated tests' cached top-level legacy
    # imports cannot decide which parser/builder this integration test uses.
    with isolated_legacy_imports():
        spec = importlib.util.spec_from_file_location(
            "root_gate_transform_api", REPO / "src/transformation/transform_api.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        assert module.SCRIPTS_AVAILABLE
        yield module


def transformer(api, mapping_file):
    return api.SemanticTransformer(api.TransformationConfig(
        mapping_file=mapping_file, validate_input=False, validate_output=False,
        preserve_provenance=False))


@pytest.mark.parametrize("input_kind", ["str", "path", "dict"])
@pytest.mark.parametrize("existing", [False, True])
def test_api_transform_refuses_invalid_root_without_publication(
        api, tmp_path, mapping_file, invalid_crate, input_kind, existing):
    bad = write_crate(tmp_path, "invalid", invalid_crate)
    given = {"str": str(bad), "path": bad, "dict": invalid_crate}[input_kind]
    output = tmp_path / "record.yaml"
    if existing:
        output.write_bytes(SENTINEL)
    with pytest.raises(ValueError, match="(?i)root"):
        transformer(api, mapping_file).rocrate_to_d4d(given, output_path=output)
    assert_preserved(output, existing)


@pytest.mark.parametrize("auto_prioritize", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_api_merge_refuses_later_invalid_source_without_publication(
        api, tmp_path, mapping_file, invalid_crate, auto_prioritize, existing, capsys):
    good = write_crate(tmp_path, "valid", valid_crate())
    bad = write_crate(tmp_path, "invalid", invalid_crate)
    output = tmp_path / "record.yaml"
    if existing:
        output.write_bytes(SENTINEL)
    instance = transformer(api, mapping_file)
    capsys.readouterr()
    with pytest.raises(ValueError, match="(?i)root"):
        instance.merge_rocrates([good, bad], output_path=output,
                                auto_prioritize=auto_prioritize)
    assert_preserved(output, existing)
    progress = capsys.readouterr().out
    assert "Scored" not in progress
    assert "Merging" not in progress
