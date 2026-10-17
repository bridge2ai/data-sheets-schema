"""An undefined profile cannot certify completeness (#4597).

Fixtures exercise reporting, root selection and existing field presence, not
scientific criteria or applicability judgments. No transformation is run.
"""
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


REPO = Path(__file__).resolve().parents[2]
VALIDATOR = REPO / "src/validation/unified_validator.py"


@pytest.fixture
def module():
    name = "_d4d_test_profile_unavailable_validator"
    previous = sys.modules.get(name)
    before_path = sys.path[:]
    before_validation = {key: value for key, value in sys.modules.items()
                         if key == "validation" or key.startswith("validation.")}
    spec = importlib.util.spec_from_file_location(name, VALIDATOR)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    try:
        spec.loader.exec_module(loaded)
        yield loaded
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        assert sys.path == before_path
        assert {key: value for key, value in sys.modules.items()
                if key == "validation" or key.startswith("validation.")} == before_validation


def _write(tmp_path, data, suffix=".json"):
    path = tmp_path / f"record{suffix}"
    path.write_text(yaml.safe_dump(data) if suffix == ".yaml" else json.dumps(data), encoding="utf-8")
    return path


def _descriptor(target="#root"):
    return {"@id": "ro-crate-metadata.json", "@type": "CreativeWork", "about": {"@id": target}}


def _assert_unavailable(report):
    assert report.passed is False
    assert report.coverage_percentage is None and report.missing_fields is None
    assert report.metadata == {"level": "complete", "status": "unavailable",
                               "reason": "required_fields_not_defined",
                               "required_count": None, "found_count": None}
    assert report.errors == ["Profile 'complete' validation is unavailable: required fields have not been defined."]
    assert report.info == []
    rendered = str(report)
    assert rendered.startswith("UNAVAILABLE - PROFILE Validation\n")
    assert "Coverage:" not in rendered and "PASS" not in rendered and "100" not in rendered
    serialized = json.loads(json.dumps(asdict(report), default=lambda value: value.value))
    assert serialized["coverage_percentage"] is None
    assert serialized["missing_fields"] is None
    assert serialized["metadata"]["required_count"] is None
    assert serialized["metadata"]["found_count"] is None


@pytest.mark.parametrize("suffix", [".json", ".yaml"])
@pytest.mark.parametrize("shape", ["direct", "graph", "singleton"])
def test_sparse_and_richer_records_are_unavailable_without_rewrites(tmp_path, module, suffix, shape):
    validator = module.UnifiedValidator()
    sparse = {"@id": "#root", "@type": "Dataset"}
    richer = {**sparse, "name": "Example", "description": "Source text",
              "datePublished": "2026-10-01", "license": "CC0", "keywords": ["a", "a"],
              "author": [{"@id": "#author"}], "identifier": "example-id",
              "humanSubjectResearch": False, "confidentialityLevel": None}
    for record in (sparse, richer):
        data = record if shape == "direct" else {"@graph": record if shape == "singleton" else [record]}
        path = _write(tmp_path, data, suffix)
        before = path.read_bytes()
        _assert_unavailable(validator.validate_profile(path, level="complete"))
        assert path.read_bytes() == before
    assert module.LEVEL_REQUIREMENTS["complete"]["required_count"] is None


def test_valid_graph_reordering_keeps_unavailable_and_cannot_use_member_fields(tmp_path, module):
    validator = module.UnifiedValidator()
    graph = [_descriptor(), {"@id": "#member", "@type": "Dataset", "name": "Richer member"},
             {"@id": "#root", "@type": "Dataset"}]
    reports = []
    for order in (graph, list(reversed(graph))):
        path = _write(tmp_path, {"@graph": order})
        reports.append(validator.validate_profile(path, level="complete"))
        _assert_unavailable(reports[-1])
    assert reports[0] == reports[1]


@pytest.mark.parametrize("data,reason", [
    ({"@graph": [_descriptor("#missing"), {"@id": "#root", "@type": "Dataset"}]}, "unresolved"),
    ({"@graph": [{"@id": "#root", "@type": "Dataset"}, {"@id": "#member", "@type": "Dataset"}]},
     "multiple Dataset"),
    ({"@type": "Dataset", "@graph": []}, "no identifiable"),
    (None, "Cannot find Dataset"),
])
def test_root_and_nonrecord_errors_precede_profile_availability(tmp_path, module, data, reason):
    report = module.UnifiedValidator().validate_profile(_write(tmp_path, data), level="complete")
    assert report.passed is False and len(report.errors) == 1
    assert reason in report.errors[0]
    assert report.metadata == {} and report.coverage_percentage is None and report.missing_fields is None
    assert str(report).startswith("✗ FAIL - PROFILE Validation")
    assert "UNAVAILABLE" not in str(report)


@pytest.mark.parametrize("failure", ["missing", "malformed", "unsupported"])
def test_file_errors_precede_profile_availability(tmp_path, module, failure):
    path = tmp_path / ("record.txt" if failure == "unsupported" else "record.json")
    if failure != "missing":
        path.write_text("{" if failure == "malformed" else "{}", encoding="utf-8")
    report = module.UnifiedValidator().validate_profile(path, level="complete")
    assert report.passed is False and len(report.errors) == 1
    assert ("Unsupported file format" if failure == "unsupported" else "Failed to load file") in report.errors[0]
    assert report.metadata == {} and report.coverage_percentage is None
    assert "UNAVAILABLE" not in str(report)


@pytest.mark.parametrize("value", [False, None, [], ""])
def test_minimal_and_basic_keep_presence_semantics(tmp_path, module, value):
    validator = module.UnifiedValidator()
    record = {"@type": "Dataset", "name": value, "humanSubjectResearch": value}
    path = _write(tmp_path, record)
    minimal = validator.validate_profile(path, level="minimal")
    basic = validator.validate_profile(path, level="basic")
    assert minimal.metadata == {"level": "minimal", "required_count": 8, "found_count": 2}
    assert minimal.coverage_percentage == 25.0 and "name" not in minimal.missing_fields
    assert basic.metadata == {"level": "basic", "required_count": 26, "found_count": 3}
    assert "name" not in basic.missing_fields and "humanSubjectResearch" not in basic.missing_fields
    del record["humanSubjectResearch"]
    missing = validator.validate_profile(_write(tmp_path, record), level="basic")
    assert missing.metadata["found_count"] == 2 and "humanSubjectResearch" in missing.missing_fields


def test_all_reports_fail_closed_for_unavailable_but_keep_basic_default(tmp_path, module, capsys):
    validator = module.UnifiedValidator()
    path = _write(tmp_path, {"@type": "Dataset", "name": "Example"})
    skip = [module.ValidationLevel.SEMANTIC, module.ValidationLevel.ROUNDTRIP]
    reports = validator.validate_all(path, format="json", schema="rocrate",
                                     profile_level="complete", skip_levels=skip)
    assert set(reports) == {module.ValidationLevel.SYNTAX, module.ValidationLevel.PROFILE}
    assert reports[module.ValidationLevel.SYNTAX].passed is True
    _assert_unavailable(reports[module.ValidationLevel.PROFILE])
    assert not all(report.passed for report in reports.values())
    validator.print_report(reports)
    out = capsys.readouterr().out
    assert "UNAVAILABLE - PROFILE Validation" in out and "OVERALL: ✗ FAIL" in out
    assert "Coverage:" not in out
    default = validator.validate_all(path, format="json", schema="rocrate", skip_levels=skip)
    profile = default[module.ValidationLevel.PROFILE]
    assert profile.metadata == {"level": "basic", "required_count": 26, "found_count": 2}
    assert profile.coverage_percentage is not None and "status" not in profile.metadata


def test_empty_requirements_never_create_a_percentage_for_another_profile(tmp_path, module):
    # Guard the denominator, not just the spelling "complete".
    module.LEVEL_REQUIREMENTS["minimal"]["required_fields"] = []
    report = module.UnifiedValidator().validate_profile(_write(tmp_path, {"@type": "Dataset"}), level="minimal")
    assert report.passed is False and report.coverage_percentage is None and report.missing_fields is None
    assert report.metadata["status"] == "unavailable"
    assert report.metadata["required_count"] is None


def test_explicit_profile_skip_and_existing_non_rocrate_behavior_are_preserved(tmp_path, module):
    validator = module.UnifiedValidator()
    path = _write(tmp_path, {"@type": "Dataset"})
    skip = [module.ValidationLevel.SEMANTIC, module.ValidationLevel.ROUNDTRIP]
    reports = validator.validate_all(path, format="json", schema="rocrate", profile_level="complete",
                                     skip_levels=[*skip, module.ValidationLevel.PROFILE])
    assert set(reports) == {module.ValidationLevel.SYNTAX}
    assert all(report.passed for report in reports.values())
    reports = validator.validate_all(path, format="json", schema="d4d", profile_level="complete", skip_levels=skip)
    profile = reports[module.ValidationLevel.PROFILE]
    assert profile.passed is True and profile.coverage_percentage is None
    assert profile.info == ["Profile validation only applies to RO-Crate format"]


def test_actual_singleton_voice_source_is_unavailable_and_unchanged(module):
    path = REPO / "data/ro-crate_packages/VOICE/raw/ro-crate-prov-graph.json"
    before = path.read_bytes()
    _assert_unavailable(module.UnifiedValidator().validate_profile(path, level="complete"))
    assert path.read_bytes() == before


def test_standalone_cli_exits_one_without_profile_coverage(tmp_path):
    path = _write(tmp_path, {"@type": "Dataset", "name": "Sparse source"})
    before = path.read_bytes()
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(VALIDATOR), str(path), "json", "rocrate", "complete"],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "UNAVAILABLE - PROFILE Validation" in result.stdout
    assert "OVERALL: ✗ FAIL" in result.stdout
    assert "Coverage:" not in result.stdout and "Traceback" not in result.stderr
    assert path.read_bytes() == before
