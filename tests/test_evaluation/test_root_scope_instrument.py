"""Offline root-scope and exact-validator controls, issues 6358/6360, 2026-11-25.

Inputs are synthetic datasheets and caller declarations. Outputs remain in the
pytest scratch directory; no scorer executable, credential or provider is used.
"""
import copy
import hashlib
import json

import pytest

from data_sheets_schema.evaluation.validate import classify, load_schema, validate_outputs
from data_sheets_schema.evaluation_context import dataset_units, load_document
from data_sheets_schema.root_scope import (
    assert_portable_output, load_root_scope, parse_root_scope, resolve_root_units,
)
from data_sheets_schema.root_scope_definition import compose_definition
from data_sheets_schema.semantic_evidence import check_evidence
from data_sheets_schema.semantic_instrument import select_semantic_instrument
from tests.test_evaluation.test_semantic_context_scope import ROOT, record


def scope_bytes(digest):
    return (json.dumps({"policy": "root_dataset_v1", "input_sha256": digest,
                       "reason": "Assess this submitted full datasheet as the registered unit."},
                      sort_keys=True) + "\n").encode()


def root_fixture(directory, rubric):
    directory.mkdir()
    result, source = record(directory, rubric, {})
    source.write_text("id: example:parent\ntitle: Parent documentation\nresources:\n"
                      "- id: example:child1\n- id: example:child2\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    declaration = directory / "scope.json"
    declaration.write_bytes(scope_bytes(digest))
    instrument = select_semantic_instrument(rubric, "6.0")
    definition = directory / "composed-definition.md"
    definition.write_bytes(compose_definition(rubric, repo_root=ROOT)[0])
    result.update(version="6.0", d4d_file="data/d4d_concatenated/synthetic/rep1/Toy_d4d.yaml",
                  evaluation_scope={"policy": "single_dataset", "selection_policy": "root_dataset_v1",
                                    "units": [{"path": "#", "id": "example:parent"}],
                                    "collection_metadata_inherited": False})
    result["metadata"].update(input_sha256=digest,
                              instrument_sha256=hashlib.sha256(definition.read_bytes()).hexdigest(),
                              scope_context_sha256=hashlib.sha256(declaration.read_bytes()).hexdigest())
    for group in result["elements" if rubric == "rubric10" else "categories"]:
        for item in group["sub_elements" if rubric == "rubric10" else "questions"]:
            item["unit_scores"] = [{**item["unit_scores"][0], "path": "#",
                                    "cited": [{"path": "title", "quote": "Parent documentation"}]}]
    output = directory / "evaluation.json"
    output.write_text(json.dumps(result))
    kwargs = {"input_path": source, "definition_path": definition, "scope_context_path": declaration,
              "semantic_version": "6.0"}
    return result, source, declaration, output, kwargs


def test_closed_scope_input_rejects_missing_unknown_duplicate_or_malformed_fields(tmp_path):
    valid = json.loads(scope_bytes("a" * 64))
    mutations = []
    for field in valid:
        modified = dict(valid)
        del modified[field]
        mutations.append(modified)
    mutations += [{**valid, "extra": "unregistered"}, {**valid, "reason": "  "},
                  {**valid, "reason": False}, {**valid, "reason": "x" * 4097},
                  {**valid, "policy": "single_dataset"}, {**valid, "input_sha256": "A" * 64},
                  {**valid, "input_sha256": 3}, [], None]
    for value in mutations:
        with pytest.raises(ValueError):
            parse_root_scope(json.dumps(value).encode())
    for raw in (b"", b"x" * 65537, b"\xff", b"{", b'{"policy": 1, "policy": 2}', b"NaN"):
        with pytest.raises(ValueError):
            parse_root_scope(raw)
    source = tmp_path / "scope.json"
    source.write_bytes(scope_bytes("a" * 64))
    declaration, digest = load_root_scope(source)
    assert declaration == valid
    assert digest == hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="independent"):
        load_root_scope(None)
    link = tmp_path / "link.json"
    link.symlink_to(source)
    with pytest.raises(ValueError, match="regular"):
        load_root_scope(link)


def test_root_scope_keeps_parent_and_still_validates_all_children():
    declaration = parse_root_scope(scope_bytes("a" * 64))
    document = {"id": "parent", "resources": [{"id": "child1"}, {"id": "child2"}]}
    before = copy.deepcopy(document)
    assert len(dataset_units(document)) == 2
    assert resolve_root_units(document, "a" * 64, declaration) == [("#", document)]
    assert document == before
    with pytest.raises(ValueError, match="another input"):
        resolve_root_units(document, "b" * 64, declaration)
    for kind in ("DatasetCollection", "CoreDatasetCollection"):
        for value in ({kind: document}, {**document, "conforms_to_class": kind},
                      {**document, "conforms_to_class": "https://example.org/schema/" + kind}):
            with pytest.raises(ValueError, match="explicit DatasetCollection"):
                resolve_root_units(value, "a" * 64, declaration)
    for kind in ("Dataset", "CoreDataset"):
        assert resolve_root_units({kind: document}, "a" * 64, declaration)[0][0] == "#"
    bad = [
        {"Dataset": {**document, "conforms_to_class": "DatasetCollection"}},
        {"DatasetCollection": {**document, "conforms_to_class": "Dataset"}},
        {"resources": [{"Dataset": {"conforms_to_class": "DatasetCollection"}}]},
        {**document, "conforms_to_class": "unknown"},
        {"conforms_to_class": "Dataset", "resources": ["bad"]},
        {"conforms_to_class": "Dataset", "resources": "bad"},
    ]
    for value in bad:
        with pytest.raises(ValueError):
            resolve_root_units(value, "a" * 64, declaration)


def test_v6_both_rubrics_accept_root_evidence_and_require_independent_scope(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        result, source, declaration, output, kwargs = root_fixture(tmp_path / rubric, rubric)
        raw = source.read_bytes()
        assert validate_outputs([output], **kwargs) == 0
        assert source.read_bytes() == raw
        assert len(dataset_units(load_document(source)[0])) == 2
        missing = {**kwargs, "scope_context_path": None}
        assert validate_outputs([output], **missing) == 1
        assert validate_outputs([output], **{**kwargs, "semantic_version": "3.0"}) == 1
        original = declaration.read_bytes()
        declaration.write_bytes(scope_bytes("b" * 64))
        assert validate_outputs([output], **kwargs) == 1
        result["metadata"]["scope_context_sha256"] = hashlib.sha256(declaration.read_bytes()).hexdigest()
        output.write_text(json.dumps(result))
        assert validate_outputs([output], **kwargs) == 1
        declaration.write_bytes(original)


def test_v6_refuses_forged_units_policy_digest_and_root_evidence(tmp_path):
    for rubric in ("rubric10", "rubric20"):
        for mutation in ("child_scope", "selection_policy", "scope_digest", "parent_id", "unknown_evidence"):
            result, _, _, output, kwargs = root_fixture(tmp_path / (rubric + "-" + mutation), rubric)
            if mutation == "child_scope":
                result["evaluation_scope"]["units"] = [{"path": "#/resources/0", "id": "example:child1"}]
                for group in result["elements" if rubric == "rubric10" else "categories"]:
                    for item in group["sub_elements" if rubric == "rubric10" else "questions"]:
                        item["unit_scores"][0]["path"] = "#/resources/0"
            elif mutation == "selection_policy":
                result["evaluation_scope"]["selection_policy"] = "evaluator_selected"
            elif mutation == "scope_digest":
                result["metadata"]["scope_context_sha256"] = "b" * 64
            elif mutation == "parent_id":
                result["evaluation_scope"]["units"][0]["id"] = "example:forged"
            else:
                first = result["elements"][0]["sub_elements"][0] if rubric == "rubric10" else result["categories"][0]["questions"][0]
                first["unit_scores"][0]["cited"] = [{"path": "/resources/9/title", "quote": "Parent documentation"}]
            output.write_text(json.dumps(result))
            assert validate_outputs([output], **kwargs) == 1


def test_v6_structural_classification_is_not_input_acceptance(tmp_path):
    result, source, declaration, output, kwargs = root_fixture(tmp_path / "classification", "rubric10")
    schema = load_schema(ROOT / select_semantic_instrument("rubric10", "6.0").schema_path)
    assert classify(result, schema) == ("valid", [])
    assert validate_outputs([output], semantic_version="6.0", scope_context_path=declaration) == 1
    document, _ = load_document(source)
    with pytest.raises(ValueError, match="independently resolved"):
        check_evidence(result, document, "rubric10")
    assert check_evidence(result, document, "rubric10", unit_map={"#": document}).passed
    with pytest.raises(ValueError, match="independently resolved"):
        check_evidence(result, document, "rubric10", unit_map={"#": {"id": "fabricated"}})
    assert validate_outputs([output], **kwargs) == 0


def test_legacy_still_scores_the_original_collection_and_refuses_scope_argument(tmp_path):
    result, source = record(tmp_path, "rubric10", {})
    original = copy.deepcopy(result)
    output = tmp_path / "legacy.json"
    output.write_text(json.dumps(result))
    definition = ROOT / ".claude/agents/d4d-rubric10-semantic.md"
    assert validate_outputs([output], input_path=source, definition_path=definition) == 0
    declaration = tmp_path / "scope.json"
    declaration.write_bytes(scope_bytes(hashlib.sha256(source.read_bytes()).hexdigest()))
    assert validate_outputs([output], input_path=source, definition_path=definition,
                            scope_context_path=declaration) == 1
    assert result == original
    assert len(result["evaluation_scope"]["units"]) == 2


def test_portability_refuses_local_paths_but_keeps_urls_and_evidence_pointers():
    valid = {"d4d_file": "data/d4d_concatenated/method/label/Toy_d4d.yaml",
             "citation": "https://example.org/home/resource", "evidence": {"path": "/creators/0/name"},
             "evaluation_model": {"session_logs": [{"path": "codex-home/sessions/session.jsonl", "sha256": "a" * 64}]}}
    assert_portable_output(valid)
    for path in ("/Users/person/run/log", "/home/person/run/log", "/root/run/log", "/tmp/log",
                 "/private/var/folders/abc/log", "file:///var/run/log", "file:/Users/person/log",
                 "source:/Users/person/log", "C:\\Users\\person\\log", "/opt/build/file",
                 "/mnt/work/file", "/var/run/file", "/private/work/file", "/usr/local/tool"):
        with pytest.raises(ValueError, match="local absolute"):
            assert_portable_output({**valid, "arbitrary_metadata": "retained at " + path})
    for path in ("../session.jsonl", "codex-home/../session.jsonl", "/var/run/session.jsonl", "https://example.org/log"):
        result = copy.deepcopy(valid)
        result["evaluation_model"]["session_logs"][0]["path"] = path
        with pytest.raises(ValueError):
            assert_portable_output(result)
    with pytest.raises(ValueError):
        assert_portable_output({**valid, "d4d_file": "/var/data/Toy_d4d.yaml"})


def test_portability_rejects_unknown_absolute_provenance_paths_without_retyping_evidence():
    valid = {"d4d_file": "data/d4d_concatenated/method/label/Toy_d4d.yaml",
             "unit_scores": [{"path": "#", "cited": [{"path": "/custom-build/file"}]}]}
    assert_portable_output(valid)
    for section in ("metadata", "evaluation_model", "scorer_instrument", "model"):
        for path in ("/opt/build/file", "/custom-build/file", "  /nonstandard-home/person/file", "/"):
            value = {**valid, section: {"nested": [{"source_path": path}]}}
            with pytest.raises(ValueError, match="absolute"):
                assert_portable_output(value)
        assert_portable_output({**valid, section: {"source_url": "https://example.org/opt/build/file"}})
