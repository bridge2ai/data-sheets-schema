"""Renderer 14's advertised audit must pass the actual admission gates (#2078)."""
import copy
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import pytest
import yaml

from data_sheets_schema import api_runner as api, chunking, evidence_assertions as evidence
from tests.test_evidence_generation_gate import specification


def rendered_example(tmp_path, runtime):
    spec = replace(specification(tmp_path, runtime), render_version=14)
    if spec.is_agentic:
        text = spec.instruction
    else:
        request = api.build_phase(spec, "audit", carry={
            "Completed full record": "description: The service is deployed.\n"})
        text = request.messages[0]["content"][-1]["text"]
        assert text.startswith("Phase 3.")
    assert api.AUDIT_RECORD_CONTRACT_V14 in text
    example = text.split("### Synthetic audit namespace example\n\n", 1)[1]
    raw = re.search(r"```yaml\n(.*?)```", example, re.S).group(1)
    audit = json.loads(re.search(r"```json\n(.*?)```", example, re.S).group(1))
    return spec, raw, audit


def fixture_files(tmp_path, raw, audit):
    original = tmp_path / "original_full.yaml"
    original.write_bytes(raw.encode("utf-8"))
    bundle = tmp_path / "sources.txt"
    bundle.write_text("FILE: protocol.txt\nPATH: protocol.txt\nThe service is planned.\n")
    manifest = tmp_path / "source_chunks.yaml"
    manifest.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    audit_file = tmp_path / "audit.json"
    audit_file.write_text(json.dumps(audit))
    kwargs = dict(audit=audit_file, bundle=bundle, manifest=manifest,
                  artifacts={"original_full": original}, protocol_version=3)
    argv = ["--audit", str(audit_file), "--bundle", str(bundle),
            "--manifest", str(manifest), "--original-full", str(original),
            "--protocol-version", "3"]
    return kwargs, argv


@pytest.mark.parametrize("runtime", ["Claude Code", "Claude API (direct)"])
def test_actual_advertised_example_passes_api_extraction_and_native_cli(tmp_path, capsys, runtime):
    spec, raw, audit = rendered_example(tmp_path, runtime)
    assert raw == "description: The service is deployed.\n"
    assert audit["source_review"]["sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert json.loads(api._extract(json.dumps(audit), "json")) == audit
    kwargs, argv = fixture_files(tmp_path, raw, audit)
    before = {p: p.read_bytes() for p in (kwargs["audit"], kwargs["bundle"],
              kwargs["manifest"], kwargs["artifacts"]["original_full"])}
    result = evidence.check_files(**kwargs)
    assert result["checked"] and result["findings"] == []
    assert result["assertions_checked"] == 2
    assert result["source_review_original"]["values_required"] == 1
    assert evidence.main(argv) == 0
    assert json.loads(capsys.readouterr().out)["findings"] == []
    assert before == {p: p.read_bytes() for p in before}
    # Replaying the selected condition keeps the exact instruction; defaults
    # stay unchanged and the new contract has its own assembly identity.
    replay = api.RunSpec.from_render_spec(spec.render_spec(), project=spec.project,
                                         method=spec.method, label=spec.label)
    assert replay.instruction == spec.instruction
    assert replace(spec, render_version=api.AUTO).render_version == (7 if spec.is_agentic else 8)
    assert api.AUDIT_RECORD_CONTRACT_V14 not in replace(spec, render_version=13).instruction
    assert api.assembly_digest(14) != api.assembly_digest(13)


@pytest.mark.parametrize("record", ["original_full", "original_core", "final_full", "final_core"])
def test_artifact_names_remain_invalid_finding_records_in_both_gates(tmp_path, capsys, record):
    _, raw, audit = rendered_example(tmp_path, "Claude Code")
    audit["findings"][0]["record"] = record
    with pytest.raises(RuntimeError, match="record must name full, core or both"):
        api._extract(json.dumps(audit), "json")
    kwargs, argv = fixture_files(tmp_path, raw, audit)
    with pytest.raises(ValueError, match="record must name full, core or both"):
        evidence.check_files(**kwargs)
    before = kwargs["audit"].read_bytes()
    assert evidence.main(argv) == 1
    result = json.loads(capsys.readouterr().out)
    assert not result["checked"]
    assert result["findings"] == [{"kind": "evidence_inputs_unusable",
        "detail": "audit.findings[0].record must name full, core or both"}]
    assert kwargs["audit"].read_bytes() == before


@pytest.mark.parametrize("name", ["full", "core", "both"])
@pytest.mark.parametrize("location", ["evidence", "source_review"])
def test_record_names_cannot_replace_evidence_or_review_artifact_names(tmp_path, name, location):
    _, raw, audit = rendered_example(tmp_path, "Claude Code")
    if location == "evidence":
        audit["findings"][0]["evidence"][0]["artifact"] = name
    else:
        audit["source_review"]["artifact"] = name
    kwargs, _ = fixture_files(tmp_path, raw, audit)
    result = evidence.check_files(**kwargs)
    assert result["findings"]


@pytest.mark.parametrize("damage", ["hash", "quote", "review_path", "unavailable_artifact"])
def test_complete_example_still_requires_exact_originals_sources_and_review_coverage(tmp_path, damage):
    _, raw, audit = rendered_example(tmp_path, "Claude API (direct)")
    if damage == "hash":
        audit["source_review"]["sha256"] = "0" * 64
    elif damage == "quote":
        audit["findings"][0]["evidence"][1]["quote"] = "The service was never deployed."
    elif damage == "review_path":
        audit["findings"][0]["review_paths"] = []
    else:
        audit["findings"][0]["evidence"][0]["artifact"] = "original_core"
    kwargs, _ = fixture_files(tmp_path, raw, audit)
    result = evidence.check_files(**kwargs)
    assert result["findings"]


def test_new_contract_is_bound_to_assembly_without_changing_historical_versions(monkeypatch):
    historical = {v: api.assembly_digest(v) for v in range(1, 14)}
    current = api.assembly_digest(14)
    monkeypatch.setattr(api, "AUDIT_RECORD_CONTRACT_V14", api.AUDIT_RECORD_CONTRACT_V14 + "\nChanged namespace rule.")
    assert api.assembly_digest(14) != current
    assert {v: api.assembly_digest(v) for v in range(1, 14)} == historical


@pytest.mark.parametrize("runtime", ["Claude Code", "Claude API (direct)"])
def test_registration_selects_the_new_contract_and_retains_default(tmp_path, runtime):
    path = Path(__file__).resolve().parents[1] / "notes/matched_cborg_2026-09-13/prepare_registration.py"
    module_spec = importlib.util.spec_from_file_location("audit_record_registration", path)
    registration = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(registration)
    parser = registration.build_parser()
    assert parser.parse_args([]).render_version == 9
    selected = parser.parse_args(["--render-version", "14"]).render_version
    base = specification(tmp_path, runtime)
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(yaml.safe_dump({"profile": "neutral", "projects": {
        base.project: {"bundle": str(base.bundle), "sources": []}}}))
    job = dict(project=base.project, method=base.method, bundle=str(base.bundle),
               label=base.label, manifest=str(manifest), chunks=str(base.chunk_manifest),
               profile=base.profile, runtime=runtime, render_version=selected)
    spec = registration.spec_for(job)
    assert spec.render_version == 14
    assert api.AUDIT_RECORD_CONTRACT_V14 in spec.instruction
    replay = api.RunSpec.from_render_spec(copy.deepcopy(spec.render_spec()),
        project=spec.project, method=spec.method, label=spec.label)
    assert replay.instruction == spec.instruction
