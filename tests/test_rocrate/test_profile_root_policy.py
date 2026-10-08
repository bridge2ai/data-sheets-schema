"""Profile coverage belongs to the authoritative crate root (#4595).

Load the source-only validator by a private module name. Neither collection
nor fixture use installs the top-level ``validation`` namespace, which is
also used by unrelated evaluation controls.
"""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


REPO = Path(__file__).resolve().parents[2]
VALIDATOR = REPO / "src/validation/unified_validator.py"
VOICE_PROVENANCE = REPO / "data/ro-crate_packages/VOICE/raw/ro-crate-prov-graph.json"


@pytest.fixture
def validator():
    name = "_d4d_test_profile_root_policy_validator"
    previous = sys.modules.get(name)
    before_path = sys.path[:]
    before_validation = {key: value for key, value in sys.modules.items()
                         if key == "validation" or key.startswith("validation.")}
    spec = importlib.util.spec_from_file_location(name, VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolves the defining module
    try:
        spec.loader.exec_module(module)
        yield module.UnifiedValidator()
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        assert sys.path == before_path
        assert {key: value for key, value in sys.modules.items()
                if key == "validation" or key.startswith("validation.")} == before_validation


FULL = {
    "@id": "#member", "@type": "Dataset", "name": "A richer member",
    "description": "Member source text", "datePublished": "2026-10-01",
    "license": "CC-BY-4.0", "keywords": ["x", "x"],
    "author": [{"@id": "#author"}], "identifier": "member-id",
}
ROOT = {"@id": "#root", "@type": "Dataset", "name": "The root"}


def descriptor(about="#root", identifier="ro-crate-metadata.json"):
    return {"@id": identifier, "@type": "CreativeWork", "about": {"@id": about}}


def report_for(tmp_path, validator, data, level="minimal", suffix=".json"):
    path = tmp_path / f"crate{suffix}"
    content = yaml.safe_dump(data) if suffix in (".yaml", ".yml") else json.dumps(data)
    path.write_text(content, encoding="utf-8")
    return validator.validate_profile(path, level=level)


def test_reordering_never_scores_a_richer_member(tmp_path, validator):
    graph = [FULL, descriptor(), ROOT]
    original = deepcopy(graph)
    reports = [report_for(tmp_path, validator, {"@graph": ordered})
               for ordered in (graph, list(reversed(graph)))]
    for report in reports:
        assert report.passed is False
        assert report.coverage_percentage == 25.0
        assert report.missing_fields == [
            "description", "datePublished", "license", "keywords", "author", "identifier",
        ]
        assert report.metadata == {"level": "minimal", "required_count": 8, "found_count": 2}
    assert reports[0] == reports[1]
    assert graph == original


@pytest.mark.parametrize("root_type", [
    "Dataset", "ROCrate", "schema:Dataset", "https://schema.org/Dataset",
    "https://w3id.org/EVI#ROCrate", ["prov:Entity", "https://w3id.org/EVI#Dataset"],
])
def test_descriptor_target_types_use_shared_contract(tmp_path, validator, root_type):
    root = dict(FULL, **{"@id": "#root", "@type": root_type})
    for graph in ([FULL, descriptor(), root], [root, descriptor(), FULL]):
        report = report_for(tmp_path, validator, {"@graph": graph})
        assert report.passed is True
        assert report.coverage_percentage == 100.0
        assert report.missing_fields == []


def test_unique_rocrate_takes_priority_over_dataset_member_without_descriptor(tmp_path, validator):
    root = dict(ROOT, **{"@type": "ROCrate"})
    for graph in ([FULL, root], [root, FULL]):
        report = report_for(tmp_path, validator, {"@graph": graph})
        assert report.coverage_percentage == 25.0
        assert "description" in report.missing_fields


INVALID_GRAPHS = [
    pytest.param([descriptor("#unresolved"), FULL], "unresolved", id="unresolved-descriptor"),
    pytest.param([descriptor(), descriptor("#member", "./ro-crate-metadata.json"), ROOT, FULL],
                 "disagree", id="conflicting-descriptors"),
    pytest.param([descriptor(), descriptor(), ROOT, FULL],
                 "duplicate entity IDs", id="duplicate-descriptor"),
    pytest.param([descriptor(), ROOT, ROOT, FULL],
                 "duplicate entity IDs", id="duplicate-root"),
    pytest.param([descriptor(), ROOT, {"@id": "#root"}, FULL],
                 "duplicate entity IDs", id="untyped-root-duplicate"),
    pytest.param([{"@id": "ro-crate-metadata.json"}, FULL],
                 "missing its about", id="missing-about"),
    pytest.param([dict(descriptor(), about=[]), FULL],
                 "empty about", id="empty-about"),
    pytest.param([dict(descriptor(), about=None), FULL],
                 "invalid about", id="invalid-about"),
    pytest.param([descriptor("ro-crate-metadata.json"), FULL],
                 "cannot select itself", id="descriptor-selects-itself"),
    pytest.param([ROOT, FULL], "multiple Dataset", id="multiple-datasets"),
    pytest.param([dict(FULL, **{"@type": "NotDataset"})],
                 "no identifiable", id="substring-is-not-type"),
    pytest.param([dict(FULL, **{"@id": []})], "invalid @id", id="malformed-root-id"),
    pytest.param([{"@id": "./", "@type": "Person"}, FULL],
                 "not typed", id="conventional-root-wrong-type"),
    pytest.param([], "no identifiable", id="empty-graph"),
    pytest.param([None, "junk", 5], "no identifiable", id="nonentities-only"),
]


@pytest.mark.parametrize("graph,reason", INVALID_GRAPHS)
@pytest.mark.parametrize("level", ["minimal", "basic", "complete"])
def test_invalid_root_refuses_before_coverage(tmp_path, validator, graph, reason, level):
    for ordered in (graph, list(reversed(graph))):
        # A complete top-level record cannot override an invalid graph.
        report = report_for(tmp_path, validator, dict(FULL, **{"@graph": ordered}), level)
        assert report.passed is False
        assert len(report.errors) == 1
        assert "No unambiguous root" in report.errors[0]
        assert reason in report.errors[0]
        assert report.coverage_percentage is None
        assert report.missing_fields is None
        assert report.metadata == {}
        assert report.info == []


@pytest.mark.parametrize("graph", [None, 5, "#root"])
def test_malformed_graph_does_not_fall_back_to_top_level_record(tmp_path, validator, graph):
    report = report_for(tmp_path, validator, dict(FULL, **{"@graph": graph}))
    assert report.passed is False
    assert "@graph must be a list" in report.errors[0]
    assert report.coverage_percentage is None
    assert report.missing_fields is None


def test_malformed_members_do_not_crash_or_change_valid_root(tmp_path, validator):
    root = dict(FULL, **{"@id": "#root"})
    graph = [None, "junk", 3, {"@id": []}, {"@id": {}, "@type": None},
             {"@id": "#bad", "@type": 5}, descriptor(), root]
    for ordered in (graph, list(reversed(graph))):
        report = report_for(tmp_path, validator, {"@graph": ordered})
        assert report.passed is True
        assert report.coverage_percentage == 100.0


@pytest.mark.parametrize("value", [False, None, [], ""])
def test_existing_presence_semantics_do_not_become_truthiness(tmp_path, validator, value):
    root = dict(FULL, **{"@id": "#root", "humanSubjectResearch": value})
    present = report_for(tmp_path, validator, {"@graph": [descriptor(), root]}, "basic")
    del root["humanSubjectResearch"]
    absent = report_for(tmp_path, validator, {"@graph": [descriptor(), root]}, "basic")
    # This profile currently measures key presence, including null/empty.
    # The root policy fix deliberately does not redefine that denominator.
    assert "humanSubjectResearch" not in present.missing_fields
    assert "humanSubjectResearch" in absent.missing_fields
    assert present.metadata["found_count"] == absent.metadata["found_count"] + 1


@pytest.mark.parametrize("suffix", [".json", ".jsonld", ".yaml", ".yml"])
def test_explicit_direct_records_keep_existing_validation(tmp_path, validator, suffix):
    record = dict(FULL, **{"@type": "PreviouslyAcceptedDirectRecord"})
    report = report_for(tmp_path, validator, record, suffix=suffix)
    assert report.passed is True
    assert report.coverage_percentage == 100.0
    assert report.missing_fields == []
    assert report.metadata == {"level": "minimal", "required_count": 8, "found_count": 8}
    del record["description"]
    report = report_for(tmp_path, validator, record, suffix=suffix)
    assert report.passed is False
    assert report.coverage_percentage == 87.5
    assert report.missing_fields == ["description"]


@pytest.mark.parametrize("data", [None, [], "record", 5, {}])
def test_non_record_documents_return_report_instead_of_type_error(tmp_path, validator, data):
    report = report_for(tmp_path, validator, data)
    assert report.passed is False
    assert report.errors == ["Cannot find Dataset entity in file"]
    assert report.coverage_percentage is None


def test_actual_voice_singleton_is_scored_as_node_not_wrapper(tmp_path, validator):
    original = VOICE_PROVENANCE.read_bytes()
    data = json.loads(original)
    node = data["@graph"]
    assert isinstance(node, dict)
    direct = report_for(tmp_path, validator, node)
    wrapped = validator.validate_profile(VOICE_PROVENANCE, level="minimal")
    listed = report_for(tmp_path, validator, {"@graph": [node]})
    assert wrapped == direct == listed
    assert wrapped.coverage_percentage == 37.5
    assert wrapped.missing_fields == ["datePublished", "license", "keywords", "author", "identifier"]
    assert VOICE_PROVENANCE.read_bytes() == original


def test_direct_script_works_outside_checkout_without_pythonpath(tmp_path):
    path = tmp_path / "crate.json"
    for graph, exit_code in (([descriptor(), dict(FULL, **{"@id": "#root"})], 0),
                             ([descriptor("#missing"), FULL], 1)):
        path.write_text(json.dumps({"@graph": graph}), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(VALIDATOR), str(path), "json", "rocrate", "minimal"],
            cwd=tmp_path, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == exit_code, result.stdout + result.stderr
        assert "Traceback" not in result.stderr
        if exit_code:
            assert "No unambiguous root" in result.stdout
            assert "unresolved" in result.stdout
            assert "Coverage:" not in result.stdout
        else:
            assert "PASS - PROFILE Validation" in result.stdout
            assert "Coverage: 100.0%" in result.stdout
