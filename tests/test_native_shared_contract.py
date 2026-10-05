"""Malformed caller declarations cannot turn into mutable/native authority."""
from dataclasses import FrozenInstanceError, replace
import copy

import pytest

from data_sheets_schema import native_shared_contract as c


def artifact(role, path, raw=b"{}"):
    return c.CapturedArtifact(c.ArtifactPin(role, path, len(raw), c.sha(raw)), raw)


def plain_pin(a):
    return {k: getattr(a.pin, k) for k in ("path", "bytes", "sha256")}


def selection():
    descriptor = c.DescriptorCapture(c.canonical({"protocol": c.NAME}),
                                     c.sha(c.canonical({"protocol": c.NAME})))
    authorities = (
        artifact("source_bundle", "/inputs/bundle", b"A source document.\n"),
        artifact("chunk_manifest", "/inputs/chunks", b"{}\n"),
        artifact("generation_scope_context", "/inputs/context", b'{"scopes": [{"owner": ""}]}\n'),
        artifact("native_stage_policy", "/assets/native.md", b"Explicit native policy.\n"),
    )
    receipt = artifact("receipt_policy", "/inputs/receipt-policy.json", c.canonical({
        "kind": c.KINDS["receipt_policy"], "version": 1,
        "registration_id": "synthetic-software-test", "condition": "generic_v10",
        "runtime_policy_sha256": authorities[-1].pin.sha256,
        "receipt_instrument_version": 4,
        "coverage_floor": {"state": "pending", "mode": "diagnostic_pilot"}}))
    schemas, declarations = [], {}
    for kind, cls in (("full", "Dataset"), ("core", "CoreDataset")):
        source = artifact("schema:" + kind, "/schemas/" + kind + ".yaml")
        imports = ((kind, source.pin.role),)
        schemas.append(c.SchemaClosureCapture(kind=kind, root_name=kind, root_class=cls,
            sources=(source,), import_roles=imports,
            closure_sha256=c.schema_closure_sha((source,), imports)))
        declarations[kind + "_schema"] = {"root": source.pin.path, "root_class": cls,
            "sources": [{"name": kind, **plain_pin(source)}]}
    doc = {
        "kind": c.KINDS["selection"], "version": 1,
        "registration_id": "offline-only", "registration_path": "/inputs/selection.json",
        "run": {"project": "SYNTHETIC", "arm": "BASELINE", "method": "claudecode_direct", "label": "test"},
        "selection": {"protocol": c.NAME, "version": 1, "condition": "generic_v10",
            "renderer": 26, "runtime": c.RUNTIME, "native_shared_generation_version": 1,
            "native_source_attribution_version": 0, "shared_generation_version": 0,
            "api_playbook_version": 0, "receipt_completion_version": 0, "removal_repair_version": 0,
            "descriptor_sha256": descriptor.sha256,
            "assets": {"prompts/native.md": plain_pin(authorities[-1])}},
        "inputs": {"project": "SYNTHETIC", "bundle": plain_pin(authorities[0]),
            "chunk_manifest": plain_pin(authorities[1]), "context": plain_pin(authorities[2]),
            "source_manifest": None, "profile": {"name": "neutral", "basis": "caller", "vocabulary": None},
            **declarations},
        "receipt_policy": plain_pin(receipt), "bounds": dict(c.BOUND_CEILINGS),
        "stage_root": "/attempt/stages",
    }
    registration = artifact("selection", doc["registration_path"], c.canonical(doc))
    return c.NativeSelectionCapture(registration=registration, descriptor=descriptor,
        receipt_policy=receipt, authority=authorities, schemas=tuple(schemas),
        protocol=c.NAME, condition=c.CONDITION, project="SYNTHETIC", arm="BASELINE", run_id="offline-only",
        bounds_json=c.canonical(doc["bounds"]), roles=c.role_paths(doc["registration_path"], doc["stage_root"]))


def test_capture_accessors_are_offline_and_retain_exact_raw_bytes(monkeypatch):
    saved = selection()
    import pathlib
    monkeypatch.setattr(pathlib.Path, "read_bytes", lambda *a: pytest.fail("unexpected live read"))
    doc = saved.document()
    doc["inputs"]["profile"]["basis"] = "changed"
    saved.bounds()["max_workers"] = 1
    assert saved.document()["inputs"]["profile"]["basis"] == "caller"
    assert saved.bounds()["max_workers"] == 4096
    context = saved.generation_context()
    assert context["context"]["raw_json"] == '{"scopes": [{"owner": ""}]}\n'
    assert context["profile"]["vocabulary"] is None
    assert context["source_manifest"] is None
    assert saved.raw("source_bundle") == saved.raw("/inputs/bundle")
    assert saved.role("phase1_full") == "/attempt/stages/sealed/full.yaml"
    assert len(saved.roles) == 23
    with pytest.raises(ValueError, match="absent"):
        saved.raw("/ambient/not-captured")
    with pytest.raises(FrozenInstanceError):
        saved.arm = "changed"
    with pytest.raises(ValueError, match="immutable type"):
        replace(saved, authority=list(saved.authority))


@pytest.mark.parametrize("axis,value", [
    ("renderer", 25), ("renderer", True), ("version", True),
    ("native_shared_generation_version", False), ("native_source_attribution_version", 1),
    ("shared_generation_version", 1), ("api_playbook_version", 2),
    ("receipt_completion_version", 2), ("removal_repair_version", 1),
])
def test_mixed_or_boolean_selector_axes_refuse(axis, value):
    doc = selection().document()
    doc["selection"][axis] = value
    with pytest.raises(ValueError, match="axes"):
        c.parse_selection(c.canonical(doc))


@pytest.mark.parametrize("path", ["relative", "/a/../b", "/a/./b", "/a//b", "/a/", "//a/b", "/a\nb"])
def test_alias_spelling_is_never_normalized_into_authority(path):
    with pytest.raises(ValueError):
        c.canonical_path(path)


def test_selection_cannot_claim_future_authority_or_mutable_root():
    doc = selection().document()
    doc["execution_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="closed"):
        c.parse_selection(c.canonical(doc))
    del doc["execution_sha256"]
    doc["stage_root"] = "/inputs"
    with pytest.raises(ValueError, match="outside"):
        c.parse_selection(c.canonical(doc))


def test_known_authority_collision_and_declared_limits_refuse_before_io():
    doc = selection().document()
    doc["inputs"]["bundle"]["path"] = "/attempt/stages/sealed/full.yaml"
    with pytest.raises(ValueError, match="overlaps"):
        c.parse_selection(c.canonical(doc))
    doc = selection().document()
    doc["bounds"]["max_input_bytes"] = 1
    with pytest.raises(ValueError, match="supplied input"):
        c.parse_selection(c.canonical(doc))
    doc = selection().document()
    doc["inputs"]["context"]["path"] = doc["inputs"]["bundle"]["path"]
    with pytest.raises(ValueError, match="conflicting"):
        c.parse_selection(c.canonical(doc))


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'"\\ud800"', b'\xff'])
def test_json_refuses_ambiguous_or_non_utf8_values(raw):
    with pytest.raises(ValueError):
        c.strict_json(raw)


def test_json_refuses_structural_and_byte_overflow_before_use():
    with pytest.raises(ValueError, match="structural"):
        c.strict_json(b"[" * 65 + b"0" + b"]" * 65)
    with pytest.raises(ValueError, match="bounded"):
        c.strict_json(b'{"x":1}', max_bytes=5)
    with pytest.raises(ValueError, match="keys"):
        c.canonical({1: "ambiguous"})


@pytest.mark.parametrize("key,value", [
    ("max_workers", True), ("max_submissions", 2), ("max_response_bytes", 8_000_001),
    ("max_history_records", 1), ("max_history_bytes", 32_000_000),
    ("max_evidence_bytes", 32_000_000),
])
def test_supplied_bounds_preserve_complete_work_and_failure_capacity(key, value):
    limits = dict(c.BOUND_CEILINGS)
    limits[key] = value
    with pytest.raises(ValueError):
        c.parse_bounds(limits)


def test_mutable_or_mismatched_artifact_bytes_cannot_be_captured():
    good = artifact("a", "/a", b"one")
    with pytest.raises(ValueError, match="raw bytes"):
        replace(good, raw=b"two")
    with pytest.raises(ValueError, match="immutable type"):
        replace(good, raw=bytearray(b"one"))
    with pytest.raises(ValueError, match="immutable type"):
        replace(good.pin, bytes=True)


def test_proposed_request_is_not_observed_read_or_write_authority():
    request = artifact("stage_request:1", "/attempt/stages/requests/000001.json")
    proposed = c.ProposedArtifact(request.pin, request.raw)
    cursor = c.StageCursor(1, "worker", "worker-1")
    response = c.ResponseDestination(role="stage_response:1", path="/attempt/stages/responses/000001.bin",
                                     max_bytes=1024, media_type="application/json")
    ready = c.StageDecision(state="request_ready", history_sha256="a" * 64,
        request_predecessor_history_sha256="b" * 64, cursor=cursor, request=proposed,
        response=None, sealed=(), publications=(), completion=None, failure_json=None)
    with pytest.raises(ValueError, match="observed"):
        replace(ready, state="awaiting_response", response=response)
    with pytest.raises(ValueError, match="only awaiting_response"):
        replace(ready, response=response)
    observed = replace(ready, state="awaiting_response", request=request, response=response)
    assert observed.request is request
    with pytest.raises(ValueError):
        replace(observed, state="await_core")


def test_prefix_cannot_include_a_partial_or_miscounted_frame():
    raw = b'{"type":"result"}\n'
    prefix = c.EvidencePrefix("transcript", "/attempt/transcript.jsonl", raw, len(raw), c.sha(raw), 1)
    with pytest.raises(ValueError, match="boundary"):
        replace(prefix, raw=raw[:-1], bytes=len(raw) - 1, sha256=c.sha(raw[:-1]))
    with pytest.raises(ValueError, match="boundary"):
        replace(prefix, lines=2)
    with pytest.raises(ValueError, match="immutable type"):
        replace(prefix, lines=True)


def test_core_requires_a_separate_seal_and_actual_helper_observation():
    original = artifact("phase1_full", "/attempt/stages/sealed/full.yaml")
    p = c.Phase1Capture(full=original, original_receipt=original, seal=original,
        full_seal_observation=original, core=None, core_seal=None, core_seal_observation=None)
    with pytest.raises(ValueError, match="together"):
        replace(p, core=original)


def test_receipt_policy_cannot_import_api_caps_or_boolean_floors():
    raw = selection().receipt_policy.raw
    good = c.parse_receipt_policy(raw)
    assert good["coverage_floor"]["state"] == "pending"
    bad = copy.deepcopy(good)
    bad["max_output_tokens"] = 10
    with pytest.raises(ValueError, match="closed"):
        c.parse_receipt_policy(c.canonical(bad))
    bad = copy.deepcopy(good)
    bad["coverage_floor"] = {"state": "registered", "numerator": True, "denominator": 1}
    with pytest.raises(ValueError, match="nonnegative"):
        c.parse_receipt_policy(c.canonical(bad))
    with pytest.raises(ValueError, match="differs"):
        c.parse_receipt_policy(raw, policy_sha256="0" * 64)


def test_schema_capture_keeps_complete_unique_import_roles():
    captured = selection().schemas[0]
    with pytest.raises(ValueError, match="incomplete"):
        replace(captured, import_roles=captured.import_roles * 2)
    with pytest.raises(ValueError, match="bound identity"):
        replace(captured, closure_sha256="0" * 64)


def test_whole_contract_is_python39_syntax_and_imports_no_repo_runtime():
    import ast
    from pathlib import Path
    source = Path(c.__file__).read_text()
    tree = ast.parse(source, feature_version=(3, 9))
    names = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(name and name.startswith("data_sheets_schema") for name in names)
