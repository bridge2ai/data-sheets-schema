"""Real converter controls for explicit parents (#4047) and output IDs (#4946)."""
import contextlib
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import zipfile

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_sheets_schema.rocrate_parent_admission import ParentAdmission
from data_sheets_schema.rocrate_assertions import typed_parent_values
from data_sheets_schema.rocrate_sources import select_root
from src.fairscape_integration.fairscape_to_d4d import (
    FairscapeToD4DConverter, main, resolvable_id,
)


ABSENT = object()
DATASET_TYPES = ("Dataset", "schema:Dataset", "http://schema.org/Dataset",
                 "https://schema.org/Dataset", "evi:Dataset", "https://w3id.org/EVI#Dataset")


def crate(parent=ABSENT, *, root_id="./", identifier=ABSENT, nodes=()):
    root = {"@id": root_id, "@type": "Dataset", "name": "Root identity probe"}
    if parent is not ABSENT:
        root["isPartOf"] = parent
    if identifier is not ABSENT:
        root["identifier"] = identifier
    return {"@context": {"@vocab": "https://schema.org/"}, "@graph": [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": root_id}},
        root, *nodes]}


def convert(value, converter=None):
    converter = converter or FairscapeToD4DConverter()
    with contextlib.redirect_stdout(io.StringIO()):
        record = converter.convert(value)
    return record, converter


def refusals(dropped):
    return [json.loads(text.split("; parent_evidence=", 1)[1])
            for _, text in dropped if "; parent_evidence=" in text]


def typed(value):
    if type(value) is dict:
        return (dict, tuple((key, typed(child)) for key, child in value.items()))
    if type(value) is list:
        return (list, tuple(typed(child) for child in value))
    return (type(value), value.hex() if type(value) is float else value)


@pytest.mark.parametrize("token", DATASET_TYPES)
@pytest.mark.parametrize("type_list", [False, True])
@pytest.mark.parametrize("graph_type", [False, True])
def test_explicit_type_spelling_and_source(token, type_list, graph_type):
    typ = [token] if type_list else token
    inline = {"@id": "#parent", "name": "Inline name", "keywords": ["one", "one"]}
    node = {"@id": "#parent", "name": "Graph name never copied", "description": "Graph text"}
    (node if graph_type else inline)["@type"] = typ
    value = crate(inline, nodes=[node])
    before = typed(value)
    record, converter = convert(value)
    assert record["parent_datasets"] == [{"id": "#parent", "name": "Inline name", "keywords": ["one", "one"]}]
    assert "Graph text" not in json.dumps(record)
    assert not converter.dropped and typed(value) == before
    evidence = converter.parent_evidence[0]
    assert evidence["decision"] == "admitted" and evidence["output_id"] == "#parent"
    assert evidence["matches"][0]["value"] == node


@pytest.mark.parametrize("cotype", ["ROCrate", "evi:ROCrate", "https://w3id.org/EVI#ROCrate",
                                     "prov:Entity", "http://www.w3.org/ns/prov#Entity"])
def test_compatible_cotypes_require_dataset(cotype):
    assert "parent_datasets" in convert(crate({"@id": "#p", "@type": ["Dataset", cotype]}))[0]
    record, converter = convert(crate({"@id": "#p", "@type": cotype}))
    assert "parent_datasets" not in record
    assert "unsupported" in converter.parent_evidence[0]["reason"]


@pytest.mark.parametrize("typ", [None, False, 0, "", [], ["Dataset", "Organization"],
    ["Dataset", "Unknown"], ["Dataset", None], [["Dataset"]], "Organization", "Project",
    "Person", "File", "DataSubset", "https://example.org/Dataset", " Dataset "])
@pytest.mark.parametrize("source", ["inline", "graph"])
def test_unsupported_explicit_type_cannot_be_hidden(typ, source):
    inline = {"@id": "#p", "@type": "Dataset"}
    node = {"@id": "#p", "@type": "Dataset", "extra": [False, 0]}
    (inline if source == "inline" else node)["@type"] = typ
    record, converter = convert(crate(inline, nodes=[node]))
    assert "parent_datasets" not in record
    evidence = refusals(converter.dropped)[0]
    assert evidence["reason"] == "explicit type or co-type is unsupported by the finite converter policy"
    assert typed(evidence["raw"]) == typed(inline)
    assert typed(evidence["matches"][0]["value"]) == typed(node)


@pytest.mark.parametrize("other", [{"@id": "#p", "@type": "Dataset"},
    {"@id": "#p", "@type": "Organization"}, {"@id": "#p", "name": "untyped duplicate"}])
def test_duplicate_identity_precedes_type_selection(other):
    first = {"@id": "#p", "@type": "Dataset"}
    record, converter = convert(crate({"@id": "#p", "@type": "Dataset"}, nodes=[first, other]))
    assert "parent_datasets" not in record
    evidence = converter.parent_evidence[0]
    assert evidence["reason"] == "parent identity has multiple exact graph matches"
    assert [row["value"] for row in evidence["matches"]] == [first, other]
    assert [row["pointer"] for row in evidence["matches"]] == ["/@graph/2", "/@graph/3"]


@pytest.mark.parametrize("value", [False, 0, "", {}, ["nested"], {"@id": None}, {"@id": ""}, "#p"])
def test_malformed_immediate_occurrences_remain_typed_evidence(value):
    record, converter = convert(crate([value], nodes=[{"@id": "#p", "@type": "Dataset"}]))
    assert "parent_datasets" not in record
    assert typed(refusals(converter.dropped)[0]["raw"]) == typed(value)
    assert converter.dropped[0][0] == "isPartOf[0]"


@pytest.mark.parametrize("value", [ABSENT, None, []])
def test_absent_null_empty_have_no_occurrences(value):
    record, converter = convert(crate(value))
    assert "parent_datasets" not in record and converter.parent_evidence == []
    assert converter.dropped == []


def test_scalar_pointer_root_permutation_and_member_isolation():
    value = crate({"@id": "#p"}, nodes=[{"@id": "#p", "@type": "Dataset"},
        {"@id": "#member", "@type": "Dataset", "isPartOf": {"@id": "#leak", "@type": "Dataset"}}])
    records = []
    for graph in (value["@graph"], list(reversed(value["@graph"]))):
        record, converter = convert({"@graph": graph})
        records.append(record)
        root, _ = select_root(graph)
        index = next(i for i, node in enumerate(graph) if node is root)
        assert converter.parent_evidence[0]["source_pointer"] == f"/@graph/{index}/isPartOf"
        assert converter.parent_evidence[0]["occurrence"] == 0
    assert records[0] == records[1]
    no_parent = crate(nodes=value["@graph"][2:])
    assert "parent_datasets" not in convert(no_parent)[0]


@pytest.mark.parametrize("root_id,identifier,parent_id", [
    ("./", "ark:59853/root", "https://n2t.net/ark:59853/root"),
    ("ark:59853/root", ABSENT, "https://n2t.net/ark:59853/root"),
    ("./", "https://example.org/root", "https://example.org/root"),
    ("./", "doi:10.1000/example", "doi:10.1000/example"),
    ("./", "https://doi.org/10.1000/example", "doi:10.1000/example"),
    (" https://example.org/root ", ABSENT, "https://example.org/root")])
def test_actual_produced_root_identity_refused_once(root_id, identifier, parent_id, monkeypatch):
    converter = FairscapeToD4DConverter()
    original_id, original_object = converter._record_id, converter._object
    calls = {"root": 0, "parent": 0}
    def record_id(root):
        calls["root"] += 1
        return original_id(root)
    def shape(item, cls, slot, path):
        if path.startswith("parent_datasets["):
            calls["parent"] += 1
        return original_object(item, cls, slot, path)
    monkeypatch.setattr(converter, "_record_id", record_id)
    monkeypatch.setattr(converter, "_object", shape)
    value = crate({"@id": parent_id, "@type": "Dataset", "name": "Explicit typed parent"},
                  root_id=root_id, identifier=identifier)
    record, _ = convert(value, converter)
    assert "parent_datasets" not in record and calls == {"root": 1, "parent": 1}
    evidence = refusals(converter.dropped)[0]
    assert evidence["reason"] == "produced parent id equals the produced root id"
    assert evidence["output_id"] == record["id"]
    assert evidence["raw"] == value["@graph"][1]["isPartOf"]


def test_distinct_parent_control_and_exact_output_identity_policy():
    record, _ = convert(crate({"@id": "https://example.org/parent", "@type": "Dataset"},
                             identifier="https://example.org/root"))
    assert record["id"] != record["parent_datasets"][0]["id"]
    # Both allowed own-id forms still take the ordinary URI-slot shaping path.
    for own_id in ("ark:59853/p", "https://n2t.net/ark:59853/p"):
        record, _ = convert(crate({"@id": "ark:59853/p", "id": own_id, "@type": "Dataset"}))
        assert record["parent_datasets"][0]["id"] == "https://n2t.net/ark:59853/p"


@pytest.mark.parametrize("own_id", ["ark:59853/root", "https://n2t.net/ark:59853/root"])
def test_output_collision_after_ordinary_own_id_fitting(own_id):
    record, converter = convert(crate({"@id": "ark:59853/root", "id": own_id, "@type": "Dataset"},
                                     identifier="ark:59853/root"))
    assert "parent_datasets" not in record
    decision = refusals(converter.dropped)[0]
    assert decision["output_id"] == record["id"] == "https://n2t.net/ark:59853/root"
    assert decision["reason"] == "produced parent id equals the produced root id"


@pytest.mark.parametrize("own_id", ["#wrong", "", None, False, 0, ["ark:59853/p"]])
def test_conflicting_inline_id_is_not_fitted(own_id):
    record, converter = convert(crate({"@id": "ark:59853/p", "id": own_id, "@type": "Dataset"}))
    assert "parent_datasets" not in record
    assert "inline id conflicts" in converter.parent_evidence[0]["reason"]
    assert not any(source.startswith("parent_datasets") for source, _ in converter.dropped)


def test_parent_whitespace_refused_without_global_identity_trimming():
    raw = {"@id": " #p ", "@type": "Dataset"}
    record, converter = convert(crate(raw, nodes=[{"@id": "#p", "@type": "Dataset"}]))
    assert "parent_datasets" not in record
    evidence = converter.parent_evidence[0]
    assert evidence["matches"] == [] and evidence["raw"] == raw
    assert "whitespace" in evidence["reason"]


@pytest.mark.parametrize("case", ["self", "inline_root", "graph_root", "deeper_cycle", "duplicate_ancestor"])
def test_known_parent_ancestry_refuses_with_consulted_evidence(case):
    parent = {"@id": "#p", "@type": "Dataset"}
    nodes = []
    if case == "self":
        parent["@id"] = "./"
    elif case == "inline_root":
        parent["isPartOf"] = {"@id": "./"}
    elif case == "graph_root":
        parent["isPartOf"] = []  # Cannot conceal the graph's edge.
        nodes = [{"@id": "#p", "@type": "Dataset", "isPartOf": {"@id": "./"}}]
    elif case == "deeper_cycle":
        parent["isPartOf"] = {"@id": "#a"}
        nodes = [{"@id": "#a", "isPartOf": {"@id": "#b"}}, {"@id": "#b", "isPartOf": {"@id": "#a"}}]
    else:
        parent["isPartOf"] = {"@id": "#a"}
        nodes = [{"@id": "#a", "name": "First"}, {"@id": "#a", "name": "Second"}]
    record, converter = convert(crate(parent, nodes=nodes))
    assert "parent_datasets" not in record
    evidence = refusals(converter.dropped)[0]
    assert evidence["raw"] == parent
    assert "cycle" in evidence["reason"] or "duplicate" in evidence["reason"]
    if case in ("deeper_cycle", "duplicate_ancestor"):
        assert evidence["ancestry"] and evidence["ancestry"][0]["reference_id"] == "#a"


def test_shared_ancestor_external_leaf_order_duplicates_and_indices():
    parent = {"@id": "#p", "@type": "Dataset", "version": 2,
              "isPartOf": [{"@id": "#a"}, {"@id": "#b"}]}
    nodes = [{"@id": "#a", "isPartOf": {"@id": "#shared"}},
             {"@id": "#b", "isPartOf": {"@id": "#shared"}},
             {"@id": "#shared", "isPartOf": "https://example.org/unresolved"}]
    record, converter = convert(crate([False, parent, deepcopy(parent)], nodes=nodes))
    assert record["parent_datasets"] == [{"id": "#p"}, {"id": "#p"}]
    sources = [source for source, _ in converter.dropped]
    assert "isPartOf[0]" in sources
    assert "parent_datasets[1].version" in sources and "parent_datasets[2].version" in sources
    assert [row["occurrence"] for row in converter.parent_evidence] == [0, 1, 2]
    assert converter.parent_evidence[1]["decision"] == "admitted"


@pytest.mark.parametrize("length,accepted", [(10000, True), (10001, False)])
def test_original_exact_ancestry_visit_bound(length, accepted):
    parent = {"@id": "#p0", "@type": "Dataset"}
    nodes = [{"@id": f"#p{i}", "isPartOf": {"@id": f"#p{i+1}"}}
             for i in range(length - 1)] + [{"@id": f"#p{length-1}"}]
    value = crate(parent, nodes=nodes)
    policy = ParentAdmission(value["@graph"][1], value["@graph"], resolvable_id)
    refs, evidence = policy.prepare(parent)
    assert (refs[0] is not None) is accepted
    assert ("10000-visit" in evidence[0]["reason"]) is not accepted


def test_evidence_and_output_detach_and_state_resets():
    raw = {"@id": "#p", "name": "Inline", "keywords": ["one"]}
    node = {"@id": "#p", "@type": "Dataset", "name": "Graph"}
    value = crate(raw, nodes=[node])
    record, converter = convert(value)
    saved = converter.parent_evidence
    raw["keywords"].append("source edit"); node["name"] = "changed"
    record["parent_datasets"][0]["keywords"].append("output edit")
    assert converter.parent_evidence == saved
    saved[0]["matches"][0]["value"]["name"] = "evidence edit"
    assert converter.parent_evidence[0]["matches"][0]["value"]["name"] == "Graph"
    with pytest.raises(ValueError):
        converter.convert(123)
    assert converter.parent_evidence == [] and converter.dropped == []
    assert convert(crate(), converter)[1].parent_evidence == []


@pytest.mark.parametrize("bad", [float("inf"), {1: "coerced key"}, object()])
def test_non_json_consulted_evidence_refuses_before_file_write(bad, tmp_path):
    value = crate({"@id": "#p", "@type": "Dataset", "unknown": bad})
    path = tmp_path / "not-created.yaml"
    with pytest.raises(ValueError, match="parent evidence"):
        FairscapeToD4DConverter().convert_and_save(value, path)
    assert not path.exists()


def test_cyclic_parent_evidence_refused_but_unrelated_exotic_value_not_newly_serialized(tmp_path):
    parent = {"@id": "#p", "@type": "Dataset"}; parent["unknown"] = parent
    with pytest.raises(ValueError, match="parent evidence"):
        FairscapeToD4DConverter().convert_and_save(crate(parent), tmp_path / "absent.yaml")
    assert not (tmp_path / "absent.yaml").exists()
    value = crate(); value["@graph"][1]["unmapped_new_key"] = object()
    assert convert(value)[0]["id"] == "./"


@pytest.mark.parametrize("route", ["save", "module_cli", "fairscape_cli"])
def test_full_unicode_refusal_transport_real_writers(route, tmp_path, monkeypatch, capsys):
    raw = {"@id": "#unknown", "unknown": {"text": "é😀\ud800\r\n" + "long" * 200, "items": [False, 0, -0.0]}}
    value = crate(raw)
    source = tmp_path / "crate.json"; source.write_text(json.dumps(value, ensure_ascii=True))
    original = source.read_bytes(); output = tmp_path / "out.yaml"
    if route == "save":
        _, valid = FairscapeToD4DConverter().convert_and_save(source, output)
        assert valid
        text = capsys.readouterr().out
    elif route == "module_cli":
        monkeypatch.setattr(sys, "argv", ["fairscape_to_d4d", "-i", str(source), "-o", str(output)])
        assert main() == 0
        text = capsys.readouterr().out
    else:
        from click.testing import CliRunner
        from src.fairscape_integration.cli import cli
        result = CliRunner().invoke(cli, ["rocrate-to-d4d", str(source), "-o", str(output)])
        assert result.exit_code == 0, result.output
        text = result.output
    line = next(line for line in text.splitlines() if "; parent_evidence=" in line)
    evidence = json.loads(line.split("; parent_evidence=", 1)[1])
    assert typed(evidence["raw"]) == typed(raw)
    assert "parent_datasets" not in yaml.safe_load(output.read_bytes())
    assert source.read_bytes() == original


def test_shared_static_policy_is_unchanged():
    root = {"@id": "./", "isPartOf": ["#p", "#p"]}
    graph = [root, {"@id": "#p", "@type": ["Dataset", "Organization"]}]
    values, note = typed_parent_values(root, graph)
    assert values == [{"@id": "#p"}] and "duplicate reference subsumed" in note
    record, converter = convert(crate(["#p", {"@id": "#p"}], nodes=graph[1:]))
    assert "parent_datasets" not in record and len(refusals(converter.dropped)) == 2


REAL_FORMS = [
    ("data/ro-crate/profiles/fairscape/full-ro-crate-metadata.json", 2),
    ("data/ro-crate/examples/CM4AI_roundtrip.json", 0),
    ("data/ro-crate/examples/voice_d4d_to_fairscape.json", 0),
    ("data/ro-crate/examples/voice_fairscape_test.json", 0),
    ("data/ro-crate_packages/CHORUS/raw/ro-crate-metadata.json", 1),
    ("data/ro-crate_packages/VOICE/raw/ro-crate-metadata.json", 0),
    ("data/ro-crate_packages/CM4AI/processed/CM4AI_crate_metadata_reduced.json", 2),
    ("data/ro-crate_packages/CM4AI/raw/cm4ai_release_metadata.zip", 2),
]


@pytest.mark.parametrize("relative,count", REAL_FORMS)
def test_real_unchanged_forms_retain_unresolved_root_references(relative, count):
    path = ROOT / relative; before = path.read_bytes()
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            value = json.loads(archive.read("cm4ai_release_metadata/ro-crate-metadata.json"))
    else:
        value = json.loads(before)
    saved = typed(value)
    record, converter = convert(value)
    assert "parent_datasets" not in record
    rows = refusals(converter.dropped)
    assert len(rows) == count
    root, _ = select_root(value["@graph"])
    if count:
        assert [row["raw"] for row in rows] == root["isPartOf"]
        assert all("no explicit Dataset" in row["reason"] for row in rows)
    assert typed(value) == saved and path.read_bytes() == before
