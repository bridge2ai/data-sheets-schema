"""Keep declared taxonomy separate from recomputed evidence and old prose."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from data_sheets_schema.semantic_evidence import EvidenceFinding, EvidenceReport
from data_sheets_schema.semantic_evidence_reporting import (
    findings_to_dict, issue_taxonomy, render_evidence_findings, render_issue_taxonomy,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def issue(**changes):
    return {"category": "attribution", "type": "content_accuracy", "severity": "high",
            "score_effect": "lowered", "item_ids": ["Q1"],
            "description": "license consent privacy: prose must not recode attribution", **changes}


def rating(*issues, version="3.0"):
    return {"version": version, "semantic_analysis": {"issues_detected": list(issues)}}


def test_structured_categories_links_and_effects_are_read_directly_without_regex():
    doc = rating(issue(item_ids=["Q1", "Q2"]), issue(score_effect="noted_only", item_ids=[]))
    before = copy.deepcopy(doc)
    def forbidden(_):
        pytest.fail("v3 must never use the legacy classifier")
    taxonomy = issue_taxonomy(doc, legacy_classifier=forbidden)
    assert taxonomy["category_counts"] == {"attribution": 2}
    assert taxonomy["item_counts"] == {"Q1": 1, "Q2": 1}
    assert taxonomy["high_severity_lowered"] == 1
    assert taxonomy["basis"] == "evaluator_declared_v3"
    taxonomy["issues"][0]["item_ids"].append("Q3")
    assert doc == before


@pytest.mark.parametrize("changes", [
    {"category": None}, {"category": "invented"}, {"category": []},
    {"type": "invented"}, {"severity": "critical"}, {"score_effect": None},
    {"item_ids": []}, {"item_ids": ["Q1", "Q1"]}, {"item_ids": [None]},
    {"score_effect": "noted_only", "item_ids": ["Q1"]},
])
def test_bad_v3_never_falls_back_to_legacy_coding(changes):
    with pytest.raises(ValueError):
        issue_taxonomy(rating(issue(**changes)), legacy_classifier=lambda _: pytest.fail("fallback"))


def test_legacy_fields_cannot_masquerade_as_v3_and_callback_is_explicit():
    doc = rating(issue(), version="2.0")
    original = copy.deepcopy(doc)
    result = issue_taxonomy(doc)
    assert result["category_counts"] == result["item_counts"] == {}
    assert result["high_severity_lowered"] is None
    def classify(entry):
        entry["description"] = "changed private copy"
        return "legacy_keyword"
    result = issue_taxonomy(doc, legacy_classifier=classify)
    assert result["category_counts"] == {"legacy_keyword": 1}
    assert result["basis"] == "legacy_caller_classification"
    assert doc == original
    assert "legacy, unstructured" in render_issue_taxonomy(doc)


def test_unknown_future_contract_and_missing_new_issue_list_are_not_clean():
    with pytest.raises(ValueError, match="unsupported"):
        issue_taxonomy(rating(version="4.0"))
    with pytest.raises(ValueError, match="recorded list"):
        issue_taxonomy({"version": "3.0"})


def test_findings_render_locations_escape_markup_and_keep_warning_nonfatal():
    finding = EvidenceFinding("warning", "uncovered_populated_field", "Q13", "version_access",
                              '<script>x</script> | [link](evil)\nnext', unit="#/resources/0", issue=0)
    report = EvidenceReport((finding,))
    encoded = findings_to_dict(report)
    assert encoded["passed"] is True
    assert encoded["findings"][0]["unit"] == "#/resources/0"
    encoded["findings"][0]["message"] = "changed"
    assert report.findings[0] == finding
    text = render_evidence_findings(report)
    assert "0 error(s), 1 warning(s)" in text
    assert "Q13" in text and "version\\_access" in text
    assert "<script>" not in text and "[link](evil)" not in text
    assert "&lt;script&gt;" in text and "&#124;" in text and "<br>next" in text
    assert "| 0 |" in text
    assert "not checked" in render_evidence_findings(None)
    assert "No mechanical evidence findings" in render_evidence_findings(EvidenceReport(()))


def _real_rating(tmp_path, *, mismatch=False):
    from data_sheets_schema.evaluation_context import load_document
    from data_sheets_schema.semantic_evidence_authority import authority_digest
    from tests.test_evaluation.test_semantic_evidence import _rating, _groups, _row, CONTEXT
    inp = tmp_path / "record.yaml"
    inp.write_text(yaml.safe_dump({"id": "test:dataset", "title": "Test", "creators": [{"name": "Ada"}]}))
    doc = _rating("rubric20", load_document(inp))
    doc["version"] = "3.0"
    doc["metadata"]["evidence_authority_sha256"] = authority_digest()
    for _group, items in _groups(doc):
        for item in items:
            for row in item["unit_scores"]:
                row.update(cited=[], absent=[], counts=[], considered=[])
    if mismatch:
        _row(doc, "Q1", counts=[{"path": "creators", "claimed": 38}])
    # A model-authored clean report is deliberately false and must be ignored.
    doc["evaluator_evidence"] = {"passed": True, "findings": []}
    path = tmp_path / "rating.json"
    path.write_text(json.dumps(doc))
    context = tmp_path / "context.yaml"
    context.write_text(yaml.safe_dump(CONTEXT))
    return path, inp, context


def test_report_recomputes_false_claim_instead_of_trusting_rating_clean_flag(tmp_path):
    from report_semantic_comparison import report
    path, inp, context = _real_rating(tmp_path, mismatch=True)
    before = [p.read_bytes() for p in (path, inp, context)]
    text = report([path], evidence_inputs={path: inp}, evidence_contexts={path: context})
    assert "1 error(s)" in text and "count\\_mismatch" in text
    assert "Q1" in text and "creators" in text
    assert hashlib.sha256(inp.read_bytes()).hexdigest() in text
    assert [p.read_bytes() for p in (path, inp, context)] == before


def test_report_missing_input_or_wrong_context_never_claims_clean(tmp_path):
    from report_semantic_comparison import report
    path, inp, context = _real_rating(tmp_path)
    assert "not checked" in report([path])
    text = report([path], evidence_inputs={path: inp})
    assert "not established" in text and "caller context" in text
    assert "No mechanical evidence findings" not in text
    inp.write_text("title: changed\n")
    text = report([path], evidence_inputs={path: inp}, evidence_contexts={path: context})
    assert "not established" in text
    assert "No mechanical evidence findings" not in text


def test_report_refuses_stray_evidence_maps(tmp_path):
    from report_semantic_comparison import report
    path, inp, context = _real_rating(tmp_path)
    with pytest.raises(ValueError, match="outside"):
        report([path], evidence_inputs={tmp_path / "other.json": inp})
    with pytest.raises(ValueError, match="requires an input"):
        report([path], evidence_contexts={path: context})


def test_report_cli_protects_inputs_contexts_and_rejects_duplicate_mappings(tmp_path):
    path, inp, context = _real_rating(tmp_path)
    before = [p.read_bytes() for p in (path, inp, context)]
    base = [sys.executable, str(ROOT / "scripts/report_semantic_comparison.py"), str(path),
            "--evidence-input", str(path), str(inp), "--evidence-context", str(path), str(context)]
    for protected in (path, inp, context):
        run = subprocess.run([*base, "--output", str(protected)], capture_output=True, text=True)
        assert run.returncode != 0 and "must not replace" in run.stderr
    run = subprocess.run([*base, "--evidence-input", str(path), str(inp),
                          "--output", str(tmp_path / "out.md")], capture_output=True, text=True)
    assert run.returncode != 0 and "duplicate" in run.stderr
    assert [p.read_bytes() for p in (path, inp, context)] == before


def test_unreadable_yaml_is_visible_as_unverified_without_overwriting_rating(tmp_path):
    from report_semantic_comparison import report
    path, inp, context = _real_rating(tmp_path)
    original = path.read_bytes()
    inp.write_text("title: [unclosed\n")
    text = report([path], evidence_inputs={path: inp}, evidence_contexts={path: context})
    assert "not established" in text and "No mechanical evidence findings" not in text
    assert path.read_bytes() == original


@pytest.mark.parametrize("index", [0, 1, 2])
def test_report_cli_rejects_hardlinked_output_without_touching_sources(tmp_path, index):
    import os
    path, inp, context = _real_rating(tmp_path)
    sources = (path, inp, context)
    before = [p.read_bytes() for p in sources]
    output = tmp_path / "report.md"
    os.link(sources[index], output)
    run = subprocess.run([sys.executable, str(ROOT / "scripts/report_semantic_comparison.py"),
                          str(path), "--evidence-input", str(path), str(inp),
                          "--evidence-context", str(path), str(context), "--output", str(output)],
                         capture_output=True, text=True)
    assert run.returncode != 0 and "must not replace" in run.stderr
    assert [p.read_bytes() for p in sources] == before
    assert output.read_bytes() == before[index]
