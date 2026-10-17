"""Both parser entry points share root selection without losing inspection.

The real legacy wrapper is loaded by file, so tests do not accidentally
substitute a same-named module left on sys.path by another test module.
"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from fairscape_integration.utils.rocrate_parser import ROCrateParser


REPO = Path(__file__).resolve().parents[2]
LEGACY = REPO / ".claude/agents/scripts/rocrate_parser.py"
VOICE_PROVENANCE = REPO / "data/ro-crate_packages/VOICE/raw/ro-crate-prov-graph.json"


@pytest.fixture(params=["packaged", "legacy"])
def parser_type(request):
    if request.param == "packaged":
        return ROCrateParser
    original_path = sys.path[:]
    try:
        spec = importlib.util.spec_from_file_location("legacy_root_policy_parser", LEGACY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_path
    return module.ROCrateParser


def parse(tmp_path, parser_type, graph, *, include_graph=True):
    path = tmp_path / "crate.json"
    data = {"@graph": graph} if include_graph else {}
    path.write_text(json.dumps(data), encoding="utf-8")
    return parser_type(path, verbose=False)


def descriptor(about, identifier="ro-crate-metadata.json"):
    return {"@id": identifier, "@type": "CreativeWork", "about": about}


ROOT = {"@id": "#root", "@type": "Dataset", "name": "Authoritative root"}
MEMBER = {"@id": "./", "@type": "Dataset", "name": "Member, despite its ID"}


def test_descriptor_beats_earlier_conventional_member(tmp_path, parser_type):
    graph = [MEMBER, descriptor({"@id": "#root"}), ROOT]
    for ordered in (graph, list(reversed(graph))):
        parser = parse(tmp_path, parser_type, ordered)
        assert parser.require_root_dataset() == ROOT
        assert parser.get_property("name") == "Authoritative root"
        assert parser.root_selection_reason == "metadata descriptor about reference"
        assert parser.graph == ordered


@pytest.mark.parametrize("descriptor_id", [
    "ro-crate-metadata.json", "./ro-crate-metadata.json",
    "ro-crate-metadata.jsonld", "./ro-crate-metadata.jsonld",
])
def test_descriptor_aliases_and_about_lists(tmp_path, parser_type, descriptor_id):
    parser = parse(tmp_path, parser_type, [
        MEMBER, descriptor([{"@id": "#root"}, "#root"], descriptor_id), ROOT,
    ])
    assert parser.require_root_dataset() == ROOT


INVALID_GRAPHS = [
    pytest.param([descriptor({"@id": "#missing"}), ROOT], "unresolved", id="unresolved"),
    pytest.param([descriptor({"@id": "#root"}),
                  descriptor({"@id": "./"}, "./ro-crate-metadata.json"), ROOT, MEMBER],
                 "disagree", id="conflicting-descriptors"),
    pytest.param([descriptor([{"@id": "#root"}, {"@id": "./"}]), ROOT, MEMBER],
                 "disagree", id="conflicting-about-list"),
    pytest.param([descriptor(None), ROOT], "invalid about", id="null-about"),
    pytest.param([descriptor([]), ROOT], "empty about", id="empty-about"),
    pytest.param([{"@id": "ro-crate-metadata.json"}, ROOT], "missing its about", id="missing-about"),
    pytest.param([descriptor({"@id": "#root"}), descriptor({"@id": "#root"}), ROOT],
                 "duplicate entity IDs", id="duplicate-descriptor"),
    pytest.param([descriptor({"@id": "#root"}), ROOT, ROOT],
                 "duplicate entity IDs", id="duplicate-root"),
    pytest.param([descriptor({"@id": "#root"}), ROOT, {"@id": "#root"}],
                 "duplicate entity IDs", id="untyped-root-duplicate"),
    pytest.param([descriptor({"@id": "ro-crate-metadata.json"}), ROOT],
                 "cannot select itself", id="descriptor-self-reference"),
    pytest.param([descriptor({"@id": "#person"}), {"@id": "#person", "@type": "Person"}, ROOT],
                 "not typed", id="wrong-target-type"),
    pytest.param([ROOT, {"@id": "#another", "@type": "Dataset"}],
                 "multiple Dataset", id="ambiguous-typed-fallback"),
    pytest.param([MEMBER, MEMBER], "multiple conventional", id="duplicate-conventional"),
    pytest.param([{"@id": "./", "@type": "Person"}, ROOT],
                 "not typed", id="wrong-conventional-type"),
    pytest.param([{"@id": ["#root"], "@type": "Dataset"}],
                 "invalid @id", id="list-root-id"),
    pytest.param([{"@id": "#root", "@type": "NotDataset"}],
                 "no identifiable", id="substring-type-is-not-dataset"),
]


@pytest.mark.parametrize("graph,reason", INVALID_GRAPHS)
def test_ambiguous_graph_is_inspectable_but_cannot_produce_a_dataset(
        tmp_path, parser_type, graph, reason):
    for ordered in (graph, list(reversed(graph))):
        parser = parse(tmp_path, parser_type, ordered)
        assert parser.get_root_dataset() is None
        assert parser.extract_all_properties() == {}
        assert parser.get_property("name") is None
        assert parser.graph == ordered
        with pytest.raises(ValueError, match=reason) as error:
            parser.require_root_dataset()
        assert str(parser.rocrate_path) in str(error.value)


@pytest.mark.parametrize("include_graph", [True, False])
def test_empty_or_missing_graph_remains_inspectable(tmp_path, parser_type, include_graph):
    parser = parse(tmp_path, parser_type, [], include_graph=include_graph)
    assert parser.get_root_dataset() is None
    assert parser.graph == []
    assert parser.get_all_entities() == {}
    assert parser.get_entities_by_type("Dataset") == []
    assert parser.get_entity_by_id("./") is None
    with pytest.raises(ValueError, match="no identifiable crate root"):
        parser.require_root_dataset()


@pytest.mark.parametrize("graph", [None, 5, "./"])
def test_non_graph_values_are_retained_for_inspection_but_refused_for_production(
        tmp_path, parser_type, graph):
    parser = parse(tmp_path, parser_type, graph)
    assert parser.graph == graph
    assert parser.get_all_entities() == {}
    assert parser.get_entities_by_type("Person") == []
    assert parser.get_entity_by_id("./") is None
    with pytest.raises(ValueError, match="@graph must be a list"):
        parser.require_root_dataset()


def test_root_values_keep_false_lists_and_source_text_without_member_fallback(tmp_path, parser_type):
    root = dict(ROOT, humanSubjectResearch=False,
                keywords=["a", "a", "b"], description="  Original source\ntext ©  ")
    member = dict(MEMBER, humanSubjectResearch=True, generatedBy=["member-only"])
    graph = [member, descriptor({"@id": "#root"}), root]
    for ordered in (graph, list(reversed(graph))):
        parser = parse(tmp_path, parser_type, ordered)
        assert parser.get_property("humanSubjectResearch") is False
        assert parser.get_property("generatedBy") is None
        assert parser.get_property("keywords") == ["a", "a", "b"]
        assert parser.get_property("description") == "  Original source\ntext ©  "


def test_raw_malformed_members_do_not_hide_or_crash_valid_root(tmp_path, parser_type):
    junk = [None, 5, "member", {"@id": ["invalid"]},
            {"@id": "#bad-type", "@type": 5}, {"@id": "#null-type", "@type": None}]
    graph = [*junk, descriptor({"@id": "#root"}), ROOT,
             {"@id": "#person", "@type": "Person"}]
    original = deepcopy(graph)
    parser = parse(tmp_path, parser_type, graph)
    assert parser.require_root_dataset() == ROOT
    assert parser.get_entity_by_id("#root") == ROOT
    assert parser.get_entities_by_type("Person") == [{"@id": "#person", "@type": "Person"}]
    assert set(parser.get_all_entities()) == {
        "#root", "ro-crate-metadata.json", "#person", "#bad-type", "#null-type",
    }
    assert parser.graph == original


def test_entity_index_refuses_duplicate_ids_instead_of_overwriting(tmp_path, parser_type):
    parser = parse(tmp_path, parser_type, [ROOT, {"@id": "#member"}, {"@id": "#member"}])
    assert parser.require_root_dataset() == ROOT
    with pytest.raises(ValueError, match="Duplicate entity @id '#member'"):
        parser.get_all_entities()
    assert len(parser.graph) == 3


def test_actual_voice_one_node_provenance_remains_supported(parser_type):
    raw = json.loads(VOICE_PROVENANCE.read_text(encoding="utf-8"))
    node = raw["@graph"]
    assert isinstance(node, dict)
    parser = parser_type(VOICE_PROVENANCE, verbose=False)
    assert parser.require_root_dataset() == node
    assert parser.graph == [node]
    assert parser.rocrate_data == raw
    assert parser.get_property("name") == "ppgs.parquet"
    assert parser.get_entities_by_type("prov:Entity") == [node]


def test_legacy_script_runs_from_an_unrelated_directory_without_pythonpath(tmp_path):
    crate = tmp_path / "one.json"
    crate.write_text(json.dumps({"@graph": ROOT}), encoding="utf-8")
    # Isolated mode ignores PYTHONPATH and excludes the current directory.
    # The wrapper must locate its sibling source package by its own path.
    result = subprocess.run([sys.executable, "-I", "-B", str(LEGACY), str(crate)],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "Loaded RO-Crate with 1 flattened properties" in result.stdout
    assert "name: Authoritative root" in result.stdout


def test_packaged_import_has_no_legacy_script_dependency(tmp_path):
    # -I excludes both the checkout cwd and PYTHONPATH. Only the installable
    # src tree is exposed, as it is in a wheel; .claude is not on the path.
    code = (
        "import pathlib, sys; "
        f"sys.path.insert(0, {str(REPO / 'src')!r}); "
        "from fairscape_integration.utils.rocrate_parser import ROCrateParser; "
        "assert not any('.claude' in str(path) for path in sys.path); "
        "assert hasattr(ROCrateParser, 'require_root_dataset')"
    )
    result = subprocess.run([sys.executable, "-I", "-B", "-c", code],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
