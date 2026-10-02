"""Invented offline packets exercise real checkers; these are not recall data."""
from copy import deepcopy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from data_sheets_schema import typed_audit as ta, audit_batches as b, audit_omissions as om
from data_sheets_schema.chunking import manifest_from_bytes
from data_sheets_schema.schema_snapshot import capture_schema


@pytest.fixture
def supplied(tmp_path):
    root = tmp_path / "schema.yaml"
    root.write_text("id: https://example.test/typed\nname: typed\nimports: [child]\n")
    (tmp_path / "child.yaml").write_text("""id: https://example.test/child
name: child
prefixes: {linkml: 'https://w3id.org/linkml/'}
imports: [linkml:types]
default_range: string
classes:
  Dataset:
    attributes:
      name: {}
      description: {}
      issued: {range: date}
""")
    bundle = b"Preamble\nFILE: manual.txt\nPATH: manual.txt\nExample release provides a complete description.\nFILE: other.txt\nPATH: other.txt\nAdditional source.\n"
    manifest = manifest_from_bytes(bundle, "invented")
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": row["id"], "status": status} for row, status in zip(manifest["chunks"],
                                      ("nothing_relevant", "redundant_with", "duplicate_of"))]}
    context = {"format": "omission_context_v1", "root_class": "Dataset", "scopes": [
        {"owner": "", "referent": "Example", "release": "1", "scope": "This release only."}],
        "source_policy": {"priority": ["manual.txt", "other.txt"], "basis": "Invented fixture."}, "vocabulary": {}}
    return dict(protocol="typed_audit_protocol_v1", original_full=b"name: Example\n",
        bundle=bundle, manifest=b.canonical_bytes(manifest), receipt=b.canonical_bytes(receipt),
        context=b.canonical_bytes(context), schema_path=root, max_output_tokens=4000)


@pytest.fixture
def packet(supplied):
    return ta.prepare(**supplied)


def replies(packet, count=1):
    request = packet["omission_request"]
    chunk = next(row for row in request["payload"]["chunks"] if row["source"] == "manual.txt")
    quote = {"source": "manual.txt", "chunk": chunk["chunk"], "quote": "Example release provides a complete description."}
    rows = [{"chunk": row["chunk"], "status": "no_omission", "reason": "No candidate declared.", "candidates": []}
            for row in request["payload"]["chunks"]]
    candidates = [{"id": f"candidate-{i}", "kind": "omission", "source": "manual.txt", "quote": quote["quote"],
        "target": {"owner": "", "slot_chain": ["description"]}, "missing_information": "The description.",
        "scope_basis": "The passage names this release."} for i in range(count)]
    if count:
        next(row for row in rows if row["chunk"] == chunk["chunk"]).update(status="omission", candidates=candidates)
    omission = {"format": "omission_inventory_v1", "request_sha256": request["request_sha256"], "chunks": rows}
    plan = packet["plan"]
    workers = {}
    for worker in plan["workers"]:
        values = []
        for row in plan["inventory"]["values"]:
            if row["path"] in worker["paths"]:
                values.append({"path": row["path"], "claims": [{"text": row["text"], "verdict": "supported",
                    "attributed_to": [], "claim_status": "fact", "source_status": "fact",
                    "evidence": [quote], "reason": "The source states this value."}]})
        workers[worker["id"]] = b.canonical_bytes({"findings": [], "summary": "No populated-field concern.",
            "source_review": {"artifact": "original_full", "sha256": plan["original_full_sha256"], "values": values}})
    index = b.build_index(plan, workers, version=2)
    delta = {"kind": "audit_integration_v2", "proposal_index_sha256": index["sha256"],
        "retain_other_rows_from_index_sha256": index["sha256"], "row_replacements": [], "finding_decisions": [],
        "new_findings": [], "summary": "Declared candidates require scientific review.",
        "omission_dispositions": [{"candidate_id": c["id"], "action": "retain", "reason": "Retain for review.",
                                    "evidence": []} for c in candidates]}
    if count:
        delta["new_findings"] = [{"severity": "medium", "record": "full", "slot": "description",
            "issue": "A source-stated description is a proposed omission.", "kind": "omission",
            "omission_candidates": [c["id"] for c in candidates], "evidence": [quote]}]
    return workers, omission, delta, quote


def seal(packet, workers, omission, delta):
    return ta.assemble(packet, workers, b.canonical_bytes(omission), b.canonical_bytes(delta))


@pytest.mark.parametrize("count", [0, 1, 2])
def test_real_roundtrip_and_candidate_merge(packet, count):
    workers, omission, delta, _ = replies(packet, count)
    result = seal(packet, workers, omission, delta)
    checked = ta.check(result)
    assert checked["passed"] and checked["independently_reconstructed"]
    assert checked["scientific_support"] == checked["novelty"] == checked["exhaustive_recall"] == "unverified"
    assert checked["omission_counts"]["prior_negative_chunks"] == 2
    assert checked["omission_counts"]["retained"] == count
    assert len(result["lineage"]["omission_candidates"]) == count
    assert all(row["final_finding_ordinal"] == 0 for row in result["lineage"]["omission_candidates"])
    assert checked["finding_counts"]["omission"] == bool(count)
    assert checked["finding_counts"]["untyped"] == checked["revised_rows"] == 0
    for key, raw in workers.items():
        assert ta.check_worker(packet, key, raw)["passed"]
    assert ta.index(packet, workers, b.canonical_bytes(omission))["omission_check"]["protocol_complete"]


def test_explicit_drop_is_retained_with_exact_evidence(packet):
    workers, omission, delta, quote = replies(packet)
    delta["new_findings"] = []
    delta["omission_dispositions"][0].update(action="drop", reason="A human should evaluate this refusal.", evidence=[quote])
    result = seal(packet, workers, omission, delta)
    assert ta.check(result)["omission_counts"]["dropped"] == 1
    row = result["lineage"]["omission_candidates"][0]
    assert row["candidate"] == {"chunk": quote["chunk"], **omission["chunks"][1]["candidates"][0]}
    assert row["final_finding_ordinal"] is None


def test_missing_kind_is_explicitly_counted_untyped(packet):
    workers, omission, delta, quote = replies(packet, 0)
    delta["new_findings"] = [{"severity": "low", "record": "full", "slot": "name",
        "issue": "An untyped editorial concern.", "evidence": [quote]}]
    assert ta.check(seal(packet, workers, omission, delta))["finding_counts"]["untyped"] == 1


@pytest.mark.parametrize("reference", [None, "foreign"])
def test_worker_omission_requires_refs_and_captured_membership_even_if_later_dropped(packet, reference):
    workers, omission, _, quote = replies(packet)
    key = next(iter(workers))
    worker = json.loads(workers[key])
    finding = {"severity": "medium", "record": "full", "slot": "description", "kind": "omission",
               "issue": "Proposed omission.", "evidence": [quote]}
    if reference:
        finding["omission_candidates"] = [reference]
    worker["findings"] = [finding]
    workers[key] = b.canonical_bytes(worker)
    if reference is None:
        assert not ta.check_worker(packet, key, workers[key])["passed"]
    else:
        assert ta.check_worker(packet, key, workers[key])["passed"]  # Membership needs omission response.
    with pytest.raises(ValueError):
        ta.index(packet, workers, b.canonical_bytes(omission))


@pytest.mark.parametrize("mutation", ["loss", "foreign", "double_link", "linked_drop", "retained_unlinked", "missing_refs", "core"])
def test_all_candidate_allocation_failures(packet, mutation):
    workers, omission, delta, quote = replies(packet)
    if mutation == "loss":
        delta["omission_dispositions"] = []
    elif mutation == "foreign":
        delta["new_findings"][0]["omission_candidates"] = ["foreign"]
    elif mutation == "double_link":
        delta["new_findings"].append(deepcopy(delta["new_findings"][0]))
    elif mutation == "linked_drop":
        delta["omission_dispositions"][0].update(action="drop", evidence=[quote])
    elif mutation == "retained_unlinked":
        delta["new_findings"] = []
    elif mutation == "missing_refs":
        del delta["new_findings"][0]["omission_candidates"]
    else:
        delta["new_findings"][0]["record"] = "core"
    with pytest.raises(ValueError):
        seal(packet, workers, omission, delta)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "foreign", "quote", "source", "target", "request", "forged_report"])
def test_actual_omission_response_rechecked(packet, mutation):
    workers, omission, delta, _ = replies(packet)
    row = omission["chunks"][1]
    if mutation == "missing":
        omission["chunks"].pop(0)  # Prior negative preamble still mandatory.
    elif mutation == "duplicate":
        omission["chunks"].append(deepcopy(row))
    elif mutation == "foreign":
        row["chunk"] = "foreign"
    elif mutation == "quote":
        row["candidates"][0]["quote"] = "Unobserved statement."
    elif mutation == "source":
        row["candidates"][0]["source"] = "other.txt"
    elif mutation == "target":
        row["candidates"][0]["target"]["slot_chain"] = ["undeclared"]
    elif mutation == "request":
        omission["request_sha256"] = "0" * 64
    else:
        omission = {"protocol_complete": True, "declared_candidates": []}
    with pytest.raises(ValueError):
        seal(packet, workers, omission, delta)


@pytest.mark.parametrize("mutation", ["finding_quote", "drop_quote", "missing_core", "final_artifact", "revised_row", "provenance"])
def test_real_evidence_checker_refuses_unsupported_evidence(packet, mutation):
    workers, omission, delta, quote = replies(packet)
    if mutation == "finding_quote":
        delta["new_findings"][0]["evidence"][0]["quote"] = "Not in the source."
    elif mutation == "drop_quote":
        delta["new_findings"] = []
        delta["omission_dispositions"][0].update(action="drop", evidence=[{**quote, "quote": "Absent."}])
    elif mutation in {"missing_core", "final_artifact"}:
        delta["new_findings"][0]["evidence"] = [{"artifact": "original_core" if mutation == "missing_core" else "final_full",
                                                "path": "/name", "op": "contains", "quote": "Example"}]
    else:
        key = next(iter(workers))
        worker = json.loads(workers[key])
        claim = worker["source_review"]["values"][0]["claims"][0]
        if mutation == "revised_row":
            claim["verdict"] = "revise"
        else:
            claim["evidence"] = [{"provenance": "source_manifest", "source": "manual.txt", "source_id": "manual",
                "field": "source_type", "value": "article", "sha256": "0" * 64}]
        workers[key] = b.canonical_bytes(worker)
        try:
            idx = b.build_index(packet["plan"], workers, version=2)
        except ValueError:
            with pytest.raises(ValueError):
                seal(packet, workers, omission, delta)
            return
        delta.update(proposal_index_sha256=idx["sha256"], retain_other_rows_from_index_sha256=idx["sha256"])
    if mutation in {"final_artifact", "revised_row"}:
        with pytest.raises(ValueError):
            seal(packet, workers, omission, delta)
        return
    report = ta.check_integration(packet, workers, b.canonical_bytes(omission), b.canonical_bytes(delta))
    assert not report["passed"] and report["problem_count"] > 0
    with pytest.raises(ValueError):
        seal(packet, workers, omission, delta)


def test_explicit_captured_core_is_available_and_bound(supplied):
    supplied["original_core"] = b"name: Core Example\n"
    packet = ta.prepare(**supplied)
    workers, omission, delta, _ = replies(packet)
    delta["new_findings"][0]["evidence"].append({"artifact": "original_core", "path": "/name", "op": "contains", "quote": "Core Example"})
    result = seal(packet, workers, omission, delta)
    assert ta.check(result)["passed"]
    result["packet"]["inputs"]["original_core"] = ta._blob(b"name: Changed\n")
    with pytest.raises(ValueError):
        ta.check(result)


@pytest.mark.parametrize("change", [None, "sha256", "source_id", "value", "project"])
def test_registered_provenance_uses_only_captured_exact_authority(supplied, change):
    supplied.update(original_full=b"name: article\n", project="EXAMPLE",
        source_manifest=b"projects:\n  EXAMPLE:\n    sources:\n    - id: manual\n      processed_file: manual.txt\n      source_type: article\n")
    packet = ta.prepare(**supplied)
    workers, omission, delta, _ = replies(packet, 0)
    key = next(iter(workers))
    worker = json.loads(workers[key])
    assertion = {"provenance": "source_manifest", "sha256": packet["inputs"]["source_manifest"]["sha256"],
        "source_id": "manual", "source": "manual.txt", "field": "source_type", "value": "article"}
    worker["source_review"]["values"][0]["claims"][0]["evidence"] = [assertion]
    if change in {"sha256", "source_id", "value"}:
        assertion[change] = "0" * 64 if change == "sha256" else "foreign"
    workers[key] = b.canonical_bytes(worker)
    idx = b.build_index(packet["plan"], workers, version=2)
    delta.update(proposal_index_sha256=idx["sha256"], retain_other_rows_from_index_sha256=idx["sha256"])
    if change == "project":
        packet["project"] = "FOREIGN"
        with pytest.raises(ValueError):
            seal(packet, workers, omission, delta)
    elif change:
        report = ta.check_integration(packet, workers, b.canonical_bytes(omission), b.canonical_bytes(delta))
        assert not report["passed"]
    else:
        assert ta.check(seal(packet, workers, omission, delta))["passed"]
        supplied["source_manifest"] += b"\n"
        changed = ta.prepare(**supplied)
        assert changed["registered_provenance"]["sha256"] != packet["registered_provenance"]["sha256"]


@pytest.mark.parametrize("protocol", [None, "audit_protocol_v1", "typed_audit_protocol_v2", True, {}, []])
def test_consumer_requires_explicit_supported_selection(supplied, protocol):
    supplied["protocol"] = protocol
    with pytest.raises(ValueError):
        ta.prepare(**supplied)


def test_descriptor_numeric_versions_cannot_be_float_substituted(packet):
    packet["protocol"]["grammar_version"] = 2.0
    packet = ta._seal({key: value for key, value in packet.items() if key != "sha256"})
    with pytest.raises(ValueError):
        ta._open(packet)


def test_released_omission_request_bytes_preserved(supplied):
    saved = json.loads((Path(__file__).parent / "fixtures/typed_audit_omission_v1_baseline.json").read_bytes())
    args = {key: value for key, value in supplied.items() if key not in {"protocol", "original_full"}}
    args["record"] = supplied["original_full"]
    assert b.canonical_bytes(om.prepare(**args).request()) == b.canonical_bytes(saved["request"])
    assert b.canonical_bytes(ta.prepare(**supplied)["omission_request"]) == b.canonical_bytes(saved["request"])


def test_original_typed_yaml_date_is_preserved_as_request_bytes(supplied):
    supplied["original_full"] += b"issued: 2026-10-02\n"
    supplied["bundle"] = supplied["bundle"].replace(b"Example release", b"2026-10-02 Example release")
    manifest = manifest_from_bytes(supplied["bundle"], "invented")
    supplied["manifest"] = b.canonical_bytes(manifest)
    receipt = json.loads(supplied["receipt"]); receipt["bundle_md5"] = manifest["bundle_md5"]
    supplied["receipt"] = b.canonical_bytes(receipt)
    packet = ta.prepare(**supplied)
    assert "issued: 2026-10-02\n" in packet["omission_request"]["payload"]["record_yaml"]
    assert next(row for row in packet["plan"]["inventory"]["values"] if row["path"] == "/issued")["whole_value_required"]


@pytest.mark.parametrize("raw", [b"classes: [\n", b"name: one\nname: two\n", b"[]\n", b"!!python/object:foo {}\n"])
def test_malformed_schema_refused_before_capture(supplied, raw):
    supplied["schema_path"].write_bytes(raw)
    with pytest.raises(ValueError):
        ta.prepare(**supplied)


@pytest.mark.parametrize("field", ["original_full", "bundle", "manifest", "receipt", "context"])
def test_each_capture_identity_mutation_refused(packet, field):
    packet["inputs"][field] = ta._blob(ta._unblob(packet["inputs"][field]) + b"\n")
    workers, omission, delta, _ = replies(packet)
    with pytest.raises(ValueError):
        seal(packet, workers, omission, delta)


@pytest.mark.parametrize("field", ["plan", "contracts", "omission_request", "requests", "protocol", "limitations"])
def test_forged_packet_derived_parts_refused_even_if_resealed(packet, field):
    packet[field] = {}
    packet = ta._seal({key: value for key, value in packet.items() if key != "sha256"})
    with pytest.raises(ValueError):
        ta._open(packet)


@pytest.mark.parametrize("field", ["audit", "lineage", "acceptance", "index"])
def test_terminal_report_cannot_override_reconstruction(packet, field):
    workers, omission, delta, _ = replies(packet)
    assembly = seal(packet, workers, omission, delta)
    assembly[field] = {"passed": True}
    assembly = ta._seal({key: value for key, value in assembly.items() if key != "sha256"})
    with pytest.raises(ValueError):
        ta.check(assembly)


def test_schema_replay_preserves_default_request_and_never_reads_changed_files(supplied, monkeypatch):
    args = {key: value for key, value in supplied.items() if key not in {"protocol", "original_full"}}
    args["record"] = supplied["original_full"]
    baseline = om.prepare(**args).request()
    snapshot = capture_schema(args["schema_path"], strict=True)
    assert om.prepare(**args, schema_snapshot=snapshot).request() == baseline
    args["schema_path"].unlink()
    args["schema_path"].with_name("child.yaml").write_text("changed: true\n")
    original = Path.open

    def guarded(path, *a, **kw):
        if path in {row[1] for row in snapshot.sources}:
            pytest.fail("ambient captured schema file was read")
        return original(path, *a, **kw)

    monkeypatch.setattr(Path, "open", guarded)
    assert om.prepare(**args, schema_snapshot=snapshot).request() == baseline
    with pytest.raises(ValueError):
        om.prepare(**args, schema_snapshot=replace(snapshot, sources=snapshot.sources[:-1]))
    with pytest.raises(ValueError):
        om.prepare(**args, schema_snapshot={"sources": snapshot.sources})


@pytest.mark.parametrize("change", ["root", "import", "path", "extra", "duplicate"])
def test_schema_closure_mutations_are_bound(packet, change):
    rows = packet["schema_sources"]
    if change in {"root", "import"}:
        row = rows[0 if change == "root" else 1]
        row["content"] = ta._blob(ta._unblob(row["content"]) + b"\n# changed\n")
    elif change == "path":
        rows[1]["path"] += ".different"
    elif change == "extra":
        row = deepcopy(rows[-1]); row["path"] += ".extra"; rows.append(row)
    else:
        rows.append(deepcopy(rows[-1]))
    with pytest.raises(ValueError):
        ta._open(packet)


def test_cli_full_saved_response_roundtrip_and_no_overwrite(supplied, tmp_path):
    def run(*args):
        return subprocess.run([sys.executable, "-m", "data_sheets_schema.typed_audit", *map(str, args)],
            capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    paths = {}
    for key in ("original_full", "bundle", "manifest", "receipt", "context"):
        paths[key] = tmp_path / f"{key}.input"
        paths[key].write_bytes(supplied[key])
    destination = tmp_path / "packet.json"
    command = ["prepare", "--protocol", supplied["protocol"], "--schema", supplied["schema_path"],
               "--max-output-tokens", "4000", "--output", destination]
    for key, path in paths.items():
        command.extend(["--" + key.replace("_", "-"), path])
    result = run(*command)
    assert result.returncode == 0, result.stderr
    packet = json.loads(destination.read_bytes())
    workers, omission, delta, _ = replies(packet)
    args = ["--packet", destination]
    for key, response in workers.items():
        path = tmp_path / f"{key}.json"; path.write_bytes(response)
        checked = run("check-worker", "--packet", destination, "--worker-id", key, "--response", path,
                      "--output", tmp_path / f"{key}.checked.json")
        assert checked.returncode == 0, checked.stderr
        args.extend(["--worker", f"{key}={path}"])
    omission_path = tmp_path / "omission.json"; omission_path.write_bytes(b.canonical_bytes(omission))
    delta_path = tmp_path / "integration.json"; delta_path.write_bytes(b.canonical_bytes(delta))
    args.extend(["--omission-response", omission_path])
    indexed = run("index", *args, "--output", tmp_path / "index.json")
    assert indexed.returncode == 0, indexed.stderr
    args.extend(["--integration-response", delta_path])
    for operation in ("check-integration", "assemble"):
        result = run(operation, *args, "--output", tmp_path / f"{operation}.json")
        assert result.returncode == 0, result.stderr
    checked = run("check", "--assembly", tmp_path / "assemble.json", "--output", tmp_path / "check.json")
    assert checked.returncode == 0, checked.stderr
    assert json.loads((tmp_path / "check.json").read_bytes())["independently_reconstructed"]
    before = destination.read_bytes()
    assert run(*command).returncode == 2
    assert destination.read_bytes() == before
    for alias in (tmp_path / "symlink.json", tmp_path / "hardlink.json", tmp_path / "dangling.json"):
        if "hardlink" in alias.name:
            os.link(destination, alias)
        else:
            alias.symlink_to(destination if "symlink" in alias.name else tmp_path / "absent.json")
        changed = list(command); changed[changed.index("--output") + 1] = alias
        assert run(*changed).returncode == 2
    assert destination.read_bytes() == before
