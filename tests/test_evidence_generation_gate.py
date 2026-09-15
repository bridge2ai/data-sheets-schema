"""Offline executions prove the new evidence checks gate real phase flow."""
import json
import hashlib
import re
import shlex
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner, chunking
from tests.test_download.test_api_runner import FakeMessages, FakeResponse
from tests.test_evidence_assertions import appendix, artifact


def specification(tmp_path, runtime="Claude API (direct)"):
    bundle = tmp_path / "documents.txt"
    bundle.write_text("FILE: protocol.txt\nPATH: protocol.txt\nA sample dataset is planned.\n")
    manifest = tmp_path / "chunks.yaml"
    manifest.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    return api_runner.RunSpec(
        project="EXAMPLE", arm="baseline", method="claudecode_api" if runtime == "Claude API (direct)" else "claudecode_agent",
        bundle=bundle, label="2026-09-15_evidence-canary_rep1", condition="generic",
        manifest=None, chunk_manifest=manifest, profile="neutral",
        render_version=9, out_dir=tmp_path / "output", runtime=runtime)


def test_both_arms_receive_the_same_protocol_and_replay_it(tmp_path):
    for runtime in ("Claude API (direct)", "Claude Code"):
        spec = specification(tmp_path, runtime)
        text = spec.instruction
        assert "## Evidence protocol v1" in text
        assert "remove_relationship" in text
        assert "not to the overview" in text
        if spec.is_agentic:
            assert "data_sheets_schema.evidence_assertions" in text
            assert "original_core.yaml" in text
        replay = api_runner.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                                     method=spec.method, label=spec.label)
        assert replay.instruction == text


def test_native_freeze_command_copies_exact_bytes_and_refuses_overwrite(tmp_path):
    directory = tmp_path / "run with ' quotes"
    directory.mkdir()
    spec = specification(directory, "Claude Code")
    spec.full_path.parent.mkdir(parents=True)
    spec.full_path.write_bytes(b"# Original full\r\nid: example\r\n")
    spec.core_path.write_bytes(b"# Derived core\nid: example\n")
    instructions = api_runner.native_evidence_instructions(spec)
    command = re.search(r"\n\n([^\n]* -c [\s\S]+?)\n\n", instructions).group(1)
    completed = subprocess.run(shlex.split(command), capture_output=True, text=True, check=True)
    pins = json.loads(completed.stdout)["original_sha256"]
    assert len(pins) == 2
    for path, digest in pins.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    original = spec.metadata_dir / "evidence/original_full.yaml"
    assert original.read_bytes() == spec.full_path.read_bytes()
    spec.full_path.write_text("id: changed\n")
    repeated = subprocess.run(shlex.split(command), capture_output=True, text=True)
    assert repeated.returncode != 0
    assert original.read_bytes() == b"# Original full\r\nid: example\r\n"


class EvidenceFake(FakeMessages):
    def __init__(self, *, bad_audit=False, retained_role=False, repair_report=True):
        super().__init__()
        self.bad_audit = bad_audit
        self.retained_role = retained_role
        self.repair_report = repair_report

    def create(self, **kw):
        text = " ".join(p.get("text", "") for p in kw["messages"][0]["content"])
        instruction = api_runner.PHASE_INSTRUCTIONS
        phase = next((p for p in ("report_regate", "audit", "report") if instruction[p] in text), None)
        if phase:
            self.calls.append(kw)
        if phase == "audit":
            findings = []
            if self.bad_audit:
                findings = [{"severity": "medium", "record": "full", "slot": "keywords",
                             "issue": "The original lost a keyword.",
                             "evidence": [artifact(path="/keywords", op="lacks", quote="a")]}]
            if self.retained_role:
                findings = [{"severity": "medium", "record": "full", "slot": "creators[1]",
                             "issue": "Leadership membership does not establish creation.",
                             "evidence": [artifact(path="/creators/1/name", quote="Team Member")],
                             "remove_relationship": {"path": "/creators/1", "identity": "/name"}}]
            return FakeResponse(json.dumps({"findings": findings, "summary": "Fixture audit"}))
        if phase in {"report", "report_regate"}:
            op = "lacks" if phase == "report_regate" and self.repair_report else "contains"
            claim = artifact("original_core", "@header", op, "# Phase 4 reconciliation: completed")
            tick = chr(96)
            report = "# Reconciliation\n\n" + appendix([claim])
            report += "\n## Dispositions\n| slot | disposition | record | reason |\n|---|---|---|---|\n"
            report += f"| {tick}keywords{tick} | retained | full | kept |\n"
            return FakeResponse(report)
        if self.retained_role:
            self.calls.append(kw)
            members = [{"name": "Established Creator"}, {"name": "Team Member"}]
            if instruction["reconcile_full"] in text:
                members.reverse()
                members[0]["notes"] = "The source does not state a creation role."
            return FakeResponse(yaml.safe_dump({"id": "x", "title": "T", "name": "n",
                "description": "d", "keywords": ["a"], "creators": members}))
        return super().create(**kw)


def run(spec, fake, monkeypatch):
    monkeypatch.setattr(api_runner, "_client", lambda: SimpleNamespace(messages=fake))
    monkeypatch.setattr(api_runner, "_validator_lines", lambda *args: ([], None))
    return api_runner.execute(spec)


def test_bad_audit_stops_before_reconciliation_and_preserves_evidence(tmp_path, monkeypatch):
    spec = specification(tmp_path)
    fake = EvidenceFake(bad_audit=True)
    with pytest.raises(RuntimeError, match="audit evidence assertions failed"):
        run(spec, fake, monkeypatch)
    assert len(fake.calls) == 2  # full and audit; core is derived without a call
    assert (spec.metadata_dir / "intermediate/EXAMPLE_audit.json").is_file()
    reading = json.loads((spec.metadata_dir / "intermediate/EXAMPLE_audit_evidence.json").read_text())
    assert reading["findings"][0]["kind"] == "artifact_assertion_contradicted"
    assert not spec.report_path.exists()


def test_false_header_history_uses_existing_single_report_recheck(tmp_path, monkeypatch):
    spec = specification(tmp_path)
    result = run(spec, EvidenceFake(), monkeypatch)
    assert [u["phase"] for u in result["usage"]] == ["full", "audit", "reconcile_full", "report", "report_regate"]
    record = yaml.safe_load(spec.provenance_path.read_text())
    gate = record["report_gate"]
    assert gate["evidence_assertions_before"]["findings"][0]["kind"] == "artifact_assertion_contradicted"
    assert gate["evidence_assertions_after"]["findings"] == []
    assert record["report_claims"]["instrument"].startswith("v8")
    assert record["report_claims"]["findings"] == []  # historical checker has not been relabeled
    assert (spec.metadata_dir / "intermediate/EXAMPLE_report_evidence.json").is_file()


def test_rejected_role_stops_before_report_even_after_reordering(tmp_path, monkeypatch):
    spec = specification(tmp_path)
    fake = EvidenceFake(retained_role=True)
    with pytest.raises(RuntimeError, match="reconcile evidence assertions failed"):
        run(spec, fake, monkeypatch)
    assert len(fake.calls) == 3
    evidence = json.loads((spec.metadata_dir / "intermediate/EXAMPLE_reconcile_evidence.json").read_text())
    assert evidence["findings"][0]["kind"] == "unsupported_relationship_retained"
    assert not spec.report_path.exists()


def test_uncorrected_header_history_stops_completion(tmp_path, monkeypatch):
    spec = specification(tmp_path)
    fake = EvidenceFake(repair_report=False)
    with pytest.raises(RuntimeError, match="report evidence assertions failed"):
        run(spec, fake, monkeypatch)
    assert len(fake.calls) == 5
    assert (spec.metadata_dir / "intermediate/EXAMPLE_report_before_regate.md").is_file()


@pytest.mark.parametrize("options", [
    {"bad_audit": True}, {"retained_role": True}, {"repair_report": False},
])
def test_evidence_refusal_cannot_spend_again_on_resume(tmp_path, monkeypatch, options):
    spec = specification(tmp_path)
    fake = EvidenceFake(**options)
    with pytest.raises(RuntimeError, match="evidence assertions failed"):
        run(spec, fake, monkeypatch)
    calls = len(fake.calls)
    with pytest.raises(RuntimeError, match="evidence assertions failed"):
        run(spec, fake, monkeypatch)
    assert len(fake.calls) == calls


def test_completed_resume_rechecks_without_calls_or_writes(tmp_path, monkeypatch):
    spec = specification(tmp_path)
    fake = EvidenceFake()
    run(spec, fake, monkeypatch)
    calls = len(fake.calls)
    files = {p: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in spec.metadata_dir.rglob("*") if p.is_file()}
    result = run(spec, fake, monkeypatch)
    assert result["already_complete"]
    assert result["checks"]["evidence_assertions"]["findings"] == []
    assert len(fake.calls) == calls
    assert files == {p: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in spec.metadata_dir.rglob("*") if p.is_file()}
