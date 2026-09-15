"""Anonymous child removals need a structural proof, never an index guess (#1839)."""
import copy
from dataclasses import replace
import json

import pytest
import yaml

from data_sheets_schema import api_runner as api
from data_sheets_schema.evidence_assertions import check_relationship_removals, check_audit
from tests.test_evidence_assertions import artifact, appendix
from tests.test_evidence_generation_gate import specification, run
from tests.test_download.test_api_runner import FakeMessages, FakeResponse


def example():
    original = {"instances": [
        {"instance_type": "clinical record", "counts": 12, "data_substrate": "urn:unsupported",
         "notes": "Original narrative"},
        {"instance_type": "image", "counts": 30, "data_substrate": "urn:supported"},
    ]}
    audit = {"findings": [{"severity": "medium", "record": "full", "slot": "instances[0].data_substrate",
        "issue": "The source does not support this assignment.",
        "evidence": [artifact(path="/instances/0/data_substrate", quote="urn:unsupported")],
        "remove_relationship": {"path": "/instances/0/data_substrate"}}], "summary": "One medium finding."}
    final = copy.deepcopy(original)
    final["instances"][0].pop("data_substrate")
    final["instances"][0]["notes"] = "Corrected narrative"
    return audit, original, final


def check(audit, original, final):
    return check_relationship_removals(audit, original, final, protocol_version=2)


def test_anonymous_child_removal_is_opt_in_and_survives_reordering():
    audit, original, final = example()
    before = copy.deepcopy((audit, original, final))
    assert check_relationship_removals(audit, original, final)[0]["kind"] == "evidence_contract"
    assert check(audit, original, final) == []
    assert (audit, original, final) == before
    final["instances"].reverse()
    assert check(audit, original, final) == []
    final["instances"][1]["data_substrate"] = "urn:unsupported"
    assert check(audit, original, final)[0]["kind"] == "unsupported_relationship_retained"


@pytest.mark.parametrize("mutation", ["rename", "count", "new_id", "replace", "drop", "duplicate",
                                      "other_endpoint", "other_removal", "shape", "empty_container"])
def test_anonymous_proof_rejects_undeclared_changes(mutation):
    audit, original, final = example()
    members = final["instances"]
    if mutation == "rename": members[0]["instance_type"] = "renamed record"
    elif mutation == "count": members[0]["counts"] = 13
    elif mutation == "new_id": members[0]["id"] = "urn:invented"
    elif mutation == "replace": members[0] = {"instance_type": "different record", "counts": 12}
    elif mutation == "drop": members.pop(0)
    elif mutation == "duplicate": members[1] = copy.deepcopy(members[0])
    elif mutation == "other_endpoint": members[1]["data_substrate"] = "urn:unsupported"
    elif mutation == "other_removal": members[1].pop("data_substrate")
    elif mutation == "shape": final["instances"] = {"0": members[0]}
    else: final.pop("instances")
    assert check(audit, original, final)[0]["kind"] == "evidence_contract"


@pytest.mark.parametrize("value", [None, "urn:replacement", "urn:unsupported", ""])
def test_changed_or_null_relationship_is_still_retained(value):
    audit, original, final = example()
    final["instances"][0]["data_substrate"] = value
    assert check(audit, original, final)[0]["kind"] == "unsupported_relationship_retained"


def test_all_declared_child_removals_are_bound_to_their_original_member():
    audit, original, final = example()
    original["instances"][0]["data_topic"] = "urn:other-unsupported"
    audit["findings"] += [{"remove_relationship": {"path": "/instances/0/data_topic"}},
                          {"remove_relationship": {"path": "/instances/1/data_substrate"}}]
    final["instances"][1].pop("data_substrate")
    final["instances"].reverse()
    assert check(audit, original, final) == []
    final["instances"][1]["data_topic"] = "urn:other-unsupported"
    problems = check(audit, original, final)
    assert len(problems) == 1
    assert problems[0]["kind"] == "unsupported_relationship_retained"
    assert problems[0]["finding"] == 1


@pytest.mark.parametrize("members", [
    [{"counts": 1, "data_substrate": "urn:a"}, {"counts": 1, "data_substrate": "urn:b"}],
    [{"notes": "only narrative", "data_substrate": "urn:a"}],
    [{"id": None, "counts": 1, "data_substrate": "urn:a"}],
])
def test_ambiguous_or_malformed_originals_stop_at_audit_admission(members):
    audit, _, _ = example()
    audit["findings"][0]["evidence"][0]["quote"] = "urn:a"
    result = check_audit(audit, artifacts={"original_full": yaml.safe_dump({"instances": members})},
                         chunks={}, protocol_version=2)
    assert result["instrument"] == "evidence_assertions v2 (#1839)"
    assert result["findings"][0]["kind"] == "evidence_contract"


def test_nested_object_child_and_identified_outer_ancestor_can_be_reordered():
    original = {"groups": [{"id": "first", "members": []}, {"id": "second", "members": [
        {"counts": 1, "properties": {"target": "urn:bad", "retained": "value"}},
        {"counts": 2, "properties": {"target": "urn:good"}}]}]}
    audit = {"findings": [{"remove_relationship": {"path": "/groups/1/members/0/properties/target"}}]}
    final = copy.deepcopy(original)
    final["groups"][1]["members"][0]["properties"].pop("target")
    final["groups"][1]["members"].reverse()
    final["groups"].reverse()
    assert check(audit, original, final) == []


def test_anonymous_whole_member_or_nested_list_removal_remains_unverified():
    original = {"members": [{"counts": 1, "children": [{"id": "urn:rejected"}]}]}
    for rule in ({"path": "/members/0"}, {"path": "/members/0/children/0", "identity": "/id"}):
        audit = {"findings": [{"remove_relationship": rule}]}
        assert check(audit, original, {"members": [{"counts": 1, "children": []}]})


@pytest.mark.parametrize("runtime", ["Claude API (direct)", "Claude Code"])
def test_renderer11_selects_and_replays_v2_for_both_arms(tmp_path, runtime):
    spec = replace(specification(tmp_path, runtime), render_version=11)
    assert "## Evidence protocol v2" in spec.instruction
    assert "Evidence protocol v1" not in spec.instruction
    for phase in api.EVIDENCE_PHASE_CONTRACTS:
        assert api.evidence_phase_contract(phase, 11) in spec.instruction
        assert api.evidence_phase_contract(phase, 11) in api.phase_instruction(phase, 11)
    if spec.is_agentic:
        assert "--protocol-version 2" in api.native_evidence_instructions(spec)
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                         method=spec.method, label=spec.label)
    assert replay.instruction == spec.instruction
    assert api.assembly_digest(11) != api.assembly_digest(10)


class AnonymousFake(FakeMessages):
    def __init__(self, ambiguous=False):
        super().__init__()
        self.audit, self.original, self.final = example()
        if ambiguous:
            self.original["instances"][1] = {**self.original["instances"][0], "notes": "different prose"}

    def create(self, **kwargs):
        self.calls.append(kwargs)
        terminal = kwargs["messages"][0]["content"][-1]["text"]
        if terminal.startswith("Phase 3."):
            return FakeResponse(json.dumps(self.audit))
        if terminal.startswith(("Phase 4c.", "Report re-check.")):
            report = "# Reconciliation\n\nRemoved the unsupported instance substrate.\n\n"
            report += appendix([self.audit["findings"][0]["evidence"][0]])
            report += ("\n## Dispositions\n| slot | disposition | record | reason |\n"
                       "|---|---|---|---|\n| `instances[0].data_substrate` | removed | both | unsupported |\n")
            return FakeResponse(report)
        record = self.final if terminal.startswith("Phase 4a.") else self.original
        return FakeResponse(yaml.safe_dump({"id": "urn:example", "title": "Example", "name": "example",
                                           "description": "Synthetic fixture", **record}))


def test_actual_v11_flow_completes_and_records_v2(tmp_path, monkeypatch):
    spec = replace(specification(tmp_path), render_version=11)
    result = run(spec, AnonymousFake(), monkeypatch)
    assert [u["phase"] for u in result["usage"]] == ["full", "audit", "reconcile_full", "report"]
    reading = json.loads((spec.metadata_dir / "intermediate/EXAMPLE_reconcile_evidence.json").read_text())
    assert reading["instrument"] == "evidence_assertions v2 (#1839)"
    assert reading["findings"] == []
    assert yaml.safe_load(spec.provenance_path.read_text())["prompts"]["assembly"] == api.assembly_digest(11)


def test_unactionable_v11_audit_stops_before_reconciliation(tmp_path, monkeypatch):
    spec = replace(specification(tmp_path), render_version=11)
    fake = AnonymousFake(ambiguous=True)
    with pytest.raises(RuntimeError, match="audit evidence assertions failed"):
        run(spec, fake, monkeypatch)
    assert len(fake.calls) == 2
    before = {p: p.read_bytes() for p in spec.metadata_dir.rglob("*") if p.is_file()}
    with pytest.raises(RuntimeError, match="evidence assertions failed"):
        run(spec, fake, monkeypatch)
    assert len(fake.calls) == 2
    assert before == {p: p.read_bytes() for p in spec.metadata_dir.rglob("*") if p.is_file()}
