"""The terminal request contract must agree with the strict evidence gate (#1834)."""
from dataclasses import replace
import hashlib
import json
import re

import pytest
import yaml

from data_sheets_schema import api_runner as api
from tests.test_download.test_api_runner import FakeResponse
from tests.test_evidence_generation_gate import EvidenceFake, run, specification


@pytest.mark.parametrize("version", range(1, 13))
@pytest.mark.parametrize("phase", ["audit", "report"])
def test_complete_source_review_output_room_preserves_historical_limits(tmp_path, version, phase):
    spec = replace(specification(tmp_path), render_version=version)
    expected = 96000 if version == 12 else 24000
    assert api.phase_max_tokens(spec, phase, 16000, model="claude-opus-5") == expected
    assert api.phase_max_tokens(spec, "reconcile_full", 16000, model="claude-opus-5") == 96000


def test_complete_source_review_output_room_respects_route_limit(tmp_path, monkeypatch):
    spec = replace(specification(tmp_path), render_version=12)
    monkeypatch.setitem(api.MODEL_OUTPUT_LIMIT, "small-offline-route", 12000)
    for phase in ("audit", "report"):
        assert api.phase_max_tokens(spec, phase, 16000, model="small-offline-route") == 12000


@pytest.mark.parametrize("runtime", ["Claude API (direct)", "Claude Code"])
def test_both_arms_deliver_and_replay_the_complete_contract(tmp_path, runtime):
    spec = replace(specification(tmp_path, runtime), render_version=10)
    text = spec.instruction
    for contract in api.EVIDENCE_PHASE_CONTRACTS.values():
        assert contract in text
    assert "a nonempty evidence array" in text
    assert "Quotations embedded in issue do not replace that array" in text
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                         method=spec.method, label=spec.label)
    assert replay.instruction == text
    # Selecting v10 for a new condition does not silently change old defaults.
    default = replace(spec, render_version=api.AUTO)
    assert default.render_version == (7 if spec.is_agentic else 8)


@pytest.mark.parametrize("phase", ["audit", "reconcile_full", "report"])
def test_actual_phase_payload_ends_with_its_complete_output_contract(tmp_path, phase):
    spec = replace(specification(tmp_path), render_version=10)
    carry = {name: "Frozen input: " + name for name in api.PHASE_NEEDS[phase]}
    if "Audit findings" in carry:
        carry["Audit findings"] = '{"findings": [], "summary": "No findings."}'
    request = api.build_phase(spec, phase, carry=carry)
    blocks = request.messages[0]["content"]
    terminal = blocks[-1]["text"]
    assert terminal.endswith(api.EVIDENCE_PHASE_CONTRACTS[phase])
    for name in carry:
        assert any(api.CARRY_LABEL.format(name=name) in block["text"] for block in blocks[:-1])
    if phase in {"audit", "reconcile_full"}:
        assert "The core record supplied above" not in terminal
    if phase == "audit":
        # Read the advertised finding fields from the real final instruction,
        # where the stopped canary received the incompatible four-field shape.
        fields = re.search(r"a list of \{([^}]+)\}", terminal).group(1)
        assert {field.strip() for field in fields.split(",")} == {
            "severity", "record", "slot", "issue", "evidence"}
        assert api.CARRY_LABEL.format(name="Completed core record") not in "\n".join(
            block["text"] for block in blocks)


def test_assembly_identity_binds_the_selected_contract_without_changing_v9(monkeypatch):
    historical = api.assembly_digest(9)
    assert historical == api.assembly_digest()
    assert historical["sha256"] == "39fadef4fcbd7d25c9e494abd8671d319897ba72ed89d7fa87617e47654285c3"
    current = api.assembly_digest(10)
    assert current != historical
    monkeypatch.setitem(api.EVIDENCE_PHASE_CONTRACTS, "audit",
                        api.EVIDENCE_PHASE_CONTRACTS["audit"] + " Changed contract.")
    assert api.assembly_digest(10) != current
    assert api.assembly_digest(9) == historical


@pytest.mark.parametrize("version,digest", [
    (9, "9e050248abda069ce3ceb4b5a343baae4c8bf7f04d7b61778ea2179d9c3307ac"),
    (10, "6320736dbdb48a20be3c808fabb642bb0e0f359c63879dc031545b743ea2083d"),
    (11, "2adb35bc2336aa0b5fd6e8f2aa3b617af925f2bb7c9d08b2cd17604213571320"),
])
def test_historical_renderer_replays_its_pre_fix_instruction_bytes(version, digest):
    recorded = {"condition": "generic_v9", "arm": "baseline", "bundle": "/input/demo.txt",
        "manifest": None, "manifest_line": "# Source manifest: not used", "chunk_manifest": None,
        "run_date": "2026-09-15", "runtime": api.RUNTIME, "provider": "offline",
        "profile": "neutral", "profile_basis": "explicit", "render_version": version,
        "api_header_values": {"Model": "synthetic-model", "Temperature": "not sent",
                              "Reasoning effort": "adaptive (provider default)"}}
    replay = api.RunSpec.from_render_spec(recorded, project="EXTERNAL",
        method="external_api", label="synthetic")
    assert hashlib.sha256(replay.instruction.encode()).hexdigest() == digest
    assert api.assembly_digest(10)["sha256"] == "efd42e290b8fa347d663fd7953d896d45a12827bca0049df64d9b74dd48c4eba"
    assert api.assembly_digest(11)["sha256"] == "b7e2f4dcd2db81121c03204f1ce1171682f5e1894b7164f9e37a4d2e6810578d"


class PhaseContractFake(EvidenceFake):
    def __init__(self, *, omit_evidence=False):
        super().__init__()
        self.omit_evidence = omit_evidence

    def create(self, **kwargs):
        terminal = kwargs["messages"][0]["content"][-1]["text"]
        if terminal.startswith("Phase 3."):
            self.calls.append(kwargs)
            findings = ([{"severity": "low", "record": "full", "slot": "keywords",
                          "issue": "A prose quote alone does not meet the contract."}]
                        if self.omit_evidence else [])
            return FakeResponse(json.dumps({"findings": findings, "summary": "Fixture audit."}))
        if terminal.startswith("Phase 4a."):
            # The shared historical fake matches an entire old paragraph.
            # Identify this phase from the actual final block instead.
            self.calls.append(kwargs)
            return FakeResponse("# reconcile_full\nid: x\ntitle: T\nname: n\n"
                                "description: d\nkeywords: [a]\n")
        return super().create(**kwargs)


def test_missing_evidence_still_stops_v10_before_reconciliation_and_resume(tmp_path, monkeypatch):
    spec = replace(specification(tmp_path), render_version=10)
    fake = PhaseContractFake(omit_evidence=True)
    with pytest.raises(RuntimeError, match="audit evidence assertions failed"):
        run(spec, fake, monkeypatch)
    assert len(fake.calls) == 2
    terminal = fake.calls[-1]["messages"][0]["content"][-1]["text"]
    assert "evidence array on every finding" in terminal
    evidence = json.loads((spec.metadata_dir / "intermediate/EXAMPLE_audit_evidence.json").read_text())
    assert evidence["findings"][0]["kind"] == "evidence_contract"
    originals = {p: p.read_bytes() for p in spec.metadata_dir.rglob("*") if p.is_file()}
    with pytest.raises(RuntimeError, match="evidence assertions failed"):
        run(spec, fake, monkeypatch)
    assert len(fake.calls) == 2
    assert originals == {p: p.read_bytes() for p in spec.metadata_dir.rglob("*") if p.is_file()}
    assert not spec.report_path.exists()


def test_actual_report_recheck_keeps_evidence_contract_and_records_v10_identity(tmp_path, monkeypatch):
    spec = replace(specification(tmp_path), render_version=10)
    fake = PhaseContractFake()
    result = run(spec, fake, monkeypatch)
    assert [row["phase"] for row in result["usage"]] == [
        "full", "audit", "reconcile_full", "report", "report_regate"]
    terminal = fake.calls[-1]["messages"][0]["content"][-1]["text"]
    assert terminal.startswith("Report re-check.")
    assert terminal.endswith(api.EVIDENCE_PHASE_CONTRACTS["report"])
    assert "## Evidence assertions" in terminal and "## Dispositions" in terminal
    record = yaml.safe_load(spec.provenance_path.read_text())
    assert record["prompts"]["assembly"] == api.assembly_digest(10)
    assert record["report_gate"]["evidence_assertions_after"]["findings"] == []
