"""Oversized top-level lists are planned entry by entry (A17, #5112, #5155).

A record whose fields all fit a worker must plan byte for byte as it did
before list splitting: the digests below were computed at f8c5ac73c, the
commit before it. The large-project records are the tracked v8 API records.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import audit_batches as b, shared_generation as sg, typed_audit as ta
from data_sheets_schema.chunking import manifest_from_bytes

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "audit_batches"
RUNS = ROOT / "data" / "d4d_concatenated"
V8 = "_claude-opus-5-api-generic-v8_rep"
CHORUS = dict(max_paths=80, max_inventory_bytes=12288, max_workers=4)  # the `chorus` partition profile
# The 2026-10-22a run's own intermediate directory (claudecode_api_core/
# 2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate). Untracked run
# data, so the replay below runs only when this names it.
V10_RUN = os.environ.get("D4D_CHORUS_V10_TYPED_RUN")


def bounds(workers, paths=80, size=12288):
    return dict(max_paths=paths, max_inventory_bytes=size, max_workers=workers)


def digest(plan):
    return hashlib.sha256(b.canonical_bytes(plan)).hexdigest()


def encode(value):
    return b.canonical_bytes(value)


def assertion():
    return {"source": "manual.txt", "chunk": "c003", "quote": "A synthetic source passage."}


def proposals(plan, findings=None):
    rows = {r["path"]: r for r in plan["inventory"]["values"]}
    return {w["id"]: encode({"findings": (findings or {}).get(w["id"], []), "summary": "Synthetic worker proposal.",
        "source_review": {"artifact": "original_full", "sha256": plan["original_full_sha256"],
            "values": [{"path": p, "claims": [{"text": rows[p]["text"], "verdict": "supported", "attributed_to": [],
                "claim_status": "fact", "source_status": "fact", "evidence": [assertion()],
                "reason": "An explicit synthetic judgment."}]} for p in w["paths"]]}}) for w in plan["workers"]}


def integration(plan, workers, new_findings=()):
    index = b.build_index(plan, workers)
    return {"kind": b.INTEGRATION_KIND, "proposal_index_sha256": index["sha256"],
            "retain_other_rows_from_index_sha256": index["sha256"], "row_replacements": [],
            "finding_decisions": [{"id": f["id"], "previous_sha256": f["sha256"], "action": "retain",
                                   "reason": "Retain this explicit judgment.", "evidence": []} for f in index["findings"]],
            "new_findings": list(new_findings), "summary": "The integration model's final summary."}


def removal_finding(path, removal):
    return {"severity": "medium", "record": "full", "slot": path, "issue": "A model-authored synthetic finding.",
            "evidence": [assertion()], "remove_relationship": {"path": removal}}


def rebind(plan):
    plan["sha256"] = b.object_sha256({k: v for k, v in plan.items() if k != "sha256"})
    return plan


def creators(count, extra=0):
    entries = [{"name": f"Person {i}", "affiliation": f"Institute {i}"} for i in range(count)]
    entries[-1].update({f"note_{j}": f"Detail {j}" for j in range(extra)})
    return yaml.safe_dump({"title": "Example", "creators": entries, "zeta": "last"}, sort_keys=False)


def owners(plan):
    return {path: w["id"] for w in plan["workers"] for path in w["paths"]}


def assert_partition(plan, limits):
    """Every path once, roots disjoint, every entry whole, every worker within its bounds."""
    paths = [p for w in plan["workers"] for p in w["paths"]]
    assert sorted(paths) == sorted(r["path"] for r in plan["inventory"]["values"]) and len(set(paths)) == len(paths)
    roots = [r for w in plan["workers"] for r in w["roots"]]
    assert roots == plan["field_roots"]
    assert len(plan["workers"]) <= limits["max_workers"]
    by_path = {r["path"]: r for r in plan["inventory"]["values"]}
    for worker in plan["workers"]:
        rows = [by_path[p] for p in worker["paths"]]
        assert len(rows) <= limits["max_paths"]
        assert worker["inventory_bytes"] == len(b.canonical_bytes(rows)) <= limits["max_inventory_bytes"]
        for path in worker["paths"]:
            assert b._owner(b._tokens(path), plan["field_roots"]) in worker["roots"]


# --- byte identity where every field fits -----------------------------------------------

def test_chorus_v10_phase1_plans_exactly_as_its_registered_run():
    raw = (FIXTURES / "chorus_v10_2026-10-22a_full.yaml").read_text(encoding="utf-8")
    plan = b.make_plan(raw, version=2, **CHORUS)
    # The plan sha256 the 2026-10-22a typed packet recorded; canonical bytes at f8c5ac73c.
    assert plan["sha256"] == "c0ed88e1380e2602b86faa7e39c1ad645bc91b7e0885d750dcbc7d39db9e676d"
    assert digest(plan) == "a9ffe6c4598ad3caf958a0c5bbc7a05ebe6e2da5838611b9aa639f14693239c6"
    assert [len(w["paths"]) for w in plan["workers"]] == [35, 54, 9]
    assert all(len(b._tokens(root)) == 1 for root in plan["field_roots"])
    b.validate_plan(plan, raw, version=2)
    expected = {(1, 80, 12288, 4): "cebfa107ff00a71e7c50b85452a0a3db0e4fb9411a9ef6543e74fe9888ef2531",
                (1, 96, 16384, 16): "0820a51b2698db41eb220841f2424c87a134309cf4f2f8c7e6e0b3e9b7d4dbc1",
                (2, 96, 16384, 16): "febf49c5e11841fdd0dae24c4175175172c3c6b2caa743056196965aab7677f7"}
    for (version, paths, size, workers), value in expected.items():
        assert digest(b.make_plan(raw, version=version, **bounds(workers, paths, size))) == value


@pytest.mark.skipif(not V10_RUN, reason="set D4D_CHORUS_V10_TYPED_RUN to the 2026-10-22a intermediate directory")
def test_chorus_v10_saved_packet_worker_wires_and_assembly_rederive_unchanged():
    run = Path(V10_RUN)
    packet = json.loads((run / "CHORUS_typed_audit_packet.json").read_bytes())
    cache = ta.DerivationCache()
    ta._open(packet, derivations=cache)  # re-derives plan, worker requests and contracts, compared byte for byte
    fixture = (FIXTURES / "chorus_v10_2026-10-22a_full.yaml").read_text(encoding="utf-8")
    assert packet["plan"] == b.make_plan(fixture, version=2, **CHORUS)
    for i, worker in enumerate(packet["plan"]["workers"]):
        request = ta.worker_request(packet, worker["id"], derivations=cache)
        wire = json.loads((run / f"CHORUS_typed_audit_{i}_request.json").read_bytes())
        texts = [part["text"] for message in wire["messages"] for part in message["content"] if part.get("type") == "text"]
        assert texts.count("# Exact typed stage request\n\n" + sg.canonical(request).decode()) == 1
    checked = ta.check(json.loads((run / "CHORUS_typed_audit_assembly.json").read_bytes()), derivations=ta.DerivationCache())
    assert checked["passed"] and checked["independently_reconstructed"]


@pytest.mark.parametrize("path,eight,sixteen", [
    (f"claudecode_api/2026-09-04f{V8}1/CHORUS_d4d.yaml",
     "a92272d9cd8dc4df277033ad7bdacd94eccf903347cad7a3f395ab7a01fb0036",
     "7f61526530b567e53672e6dc83c7699dc26abe213588a63fa69d54d1a4f661b7"),
    (f"claudecode_api/2026-09-04f{V8}2/CHORUS_d4d.yaml",
     "9c94d6675bb80561281af4b7079793a544c8d9c6c678e850843d2248bb7365b4",
     "cd1b7208fcc971fecb6e86e2059e668ab670c75f8f09589b24e571b780340e52"),
    (f"claudecode_api/2026-09-04f{V8}3/CHORUS_d4d.yaml",
     "45f83bf44065e178bc1454400ce16f03945fd0bde40fd8d6e6be31e377aca0c0",
     "7a4881428019e175bf322381ecbe9dc6a0ab627b37ac238af7e8d753ea1872dd"),
    (f"claudecode_api_core/2026-09-04f{V8}1/intermediate/CHORUS_full.yaml",
     "e8ea1ef2bf376b83ef5e4ac360551fbccbd8fecc2cf91560aa26c1f464b0b0ab",
     "0dfce6f3a2bd19a035b9b1ca2236f91f7729087ce0ad9a4074f173556229ef46"),
    (f"claudecode_api_core/2026-09-04f{V8}2/intermediate/CHORUS_full.yaml",
     "8d8efe4758a8789bd07db137a43673823ee13ef831696f29bd94a09eede27451",
     "8993c750ef8171ddda9bd99f39b030d2b613e4b06e336e6dbcf6da3b091f0a5f"),
    (f"claudecode_api_core/2026-09-04f{V8}3/intermediate/CHORUS_full.yaml",
     "394aebf7d589f9b794371d5bdb1e1bb7ec79c1437b2f7013d3f17ce16807bac0",
     "abfe8a1fb743eeba441b7a90b8ad7cbd1fdb6277c39c9f5a905d9bf5d52f4eaf"),
    (f"claudecode_api/2026-09-04f{V8}1/VOICE_d4d.yaml", None,
     "666f942b905d4b98b94b8b1c0b5199aa44c9c61e629c139b07b1f0e89a8f9a7c"),
    (f"claudecode_api/2026-09-04f{V8}2/VOICE_d4d.yaml", None,
     "376ad0385cd189c5a551d1363a92b46d9799206b6f82179c03b59157c9a36337"),
    (f"claudecode_api/2026-09-04f{V8}3/VOICE_d4d.yaml", None,
     "ded49b7bce2cc9b9b48d25c72b65843c092a575b604851dee4cc94eaf6939ad3"),
])
def test_v8_records_whose_fields_fit_plan_exactly_as_before(path, eight, sixteen):
    raw = (RUNS / path).read_text(encoding="utf-8")
    # No field of these records outgrows a worker; four workers refused them before and still do.
    with pytest.raises(b.AuditBatchError, match="^worker_count_bound$"):
        b.make_plan(raw, version=2, **CHORUS)
    if eight is None:
        with pytest.raises(b.AuditBatchError, match="^worker_count_bound$"):
            b.make_plan(raw, version=2, **bounds(8))
    else:
        assert digest(b.make_plan(raw, version=2, **bounds(8))) == eight
    plan = b.make_plan(raw, version=2, **bounds(16))
    assert digest(plan) == sixteen
    assert all(len(b._tokens(root)) == 1 for root in plan["field_roots"])


# --- the large projects ------------------------------------------------------------------

@pytest.mark.parametrize("path,workers,largest,split", [
    (f"claudecode_api/2026-09-04g{V8}1/AI_READI_d4d.yaml", 12, 12119, ["file_collections", "variables"]),
    (f"claudecode_api/2026-09-04g{V8}2/AI_READI_d4d.yaml", 15, 12193, ["file_collections"]),
    (f"claudecode_api/2026-09-04g{V8}3/AI_READI_d4d.yaml", 12, 12188, ["file_collections"]),
    (f"claudecode_api/2026-09-04g{V8}1/CM4AI_d4d.yaml", 8, 12129, ["creators", "file_collections"]),
    (f"claudecode_api/2026-09-04g{V8}2/CM4AI_d4d.yaml", 8, 12266, ["creators", "file_collections"]),
    (f"claudecode_api/2026-09-04g{V8}3/CM4AI_d4d.yaml", 9, 11929, ["creators"]),
    (f"claudecode_api/2026-09-04f{V8}1/VOICE_d4d.yaml", 10, 12211, []),
    (f"claudecode_api/2026-09-04f{V8}2/VOICE_d4d.yaml", 9, 12208, []),
    (f"claudecode_api/2026-09-04f{V8}3/VOICE_d4d.yaml", 11, 12102, []),
])
def test_large_v8_records_plan_within_eighty_paths_and_twelve_kilobytes(path, workers, largest, split):
    raw = (RUNS / path).read_text(encoding="utf-8")
    limits = bounds(16)
    plan = b.make_plan(raw, version=2, **limits)
    assert len(plan["workers"]) == workers
    assert max(w["inventory_bytes"] for w in plan["workers"]) == largest
    assert sorted({b._tokens(r)[0] for r in plan["field_roots"] if len(b._tokens(r)) == 2}) == split
    assert_partition(plan, limits)
    b.validate_plan(plan, raw, version=2)
    assert b.make_plan(raw, version=2, **limits) == plan
    # Splitting removes the field refusal; what remains under the CHORUS profile is the count.
    with pytest.raises(b.AuditBatchError, match="^worker_count_bound$"):
        b.make_plan(raw, version=2, **CHORUS)


def test_the_duplicate_key_ai_readi_record_is_refused_before_planning():
    raw = (RUNS / f"claudecode_api/2026-09-04f{V8}1/AI_READI_d4d.yaml").read_text(encoding="utf-8")
    with pytest.raises(b.AuditBatchError, match="^record_duplicate_key$"):
        b.make_plan(raw, version=2, **bounds(16))


# --- the rule ----------------------------------------------------------------------------

def test_an_oversized_list_is_split_between_whole_entries_in_index_order():
    raw = creators(12)
    limits = bounds(16, paths=6)
    plan = b.make_plan(raw, **limits)
    assert plan["field_roots"] == [f"/creators/{i}" for i in range(12)] + ["/title", "/zeta"]
    assert [w["roots"] for w in plan["workers"]] == [
        ["/creators/0", "/creators/1", "/creators/2"], ["/creators/3", "/creators/4", "/creators/5"],
        ["/creators/6", "/creators/7", "/creators/8"], ["/creators/9", "/creators/10", "/creators/11"],
        ["/title", "/zeta"]]
    assert plan["workers"][3]["paths"] == ["/creators/9/affiliation", "/creators/9/name", "/creators/10/affiliation",
                                           "/creators/10/name", "/creators/11/affiliation", "/creators/11/name"]
    assert_partition(plan, limits)
    b.validate_plan(plan, raw)
    # The inventory itself is untouched: same rows, same order as an unsplit plan of the same record.
    assert plan["inventory"] == b.make_plan(raw, max_paths=96)["inventory"]


def test_lists_that_fit_and_other_fields_stay_whole():
    raw = yaml.safe_dump({"keywords": ["a", "b"], "study": {f"k{i}": i for i in range(3)},
                          "creators": [{"name": f"P{i}"} for i in range(5)]})
    plan = b.make_plan(raw, max_paths=4)
    assert plan["field_roots"] == [f"/creators/{i}" for i in range(5)] + ["/keywords", "/study"]


def test_empty_entries_are_owned_like_empty_fields():
    raw = yaml.safe_dump({"creators": [{"name": "A"}, None, {}, {"name": "B"}, {"name": "C"}]})
    plan = b.make_plan(raw, max_paths=2)
    assert plan["field_roots"] == [f"/creators/{i}" for i in range(5)]
    assert [w["roots"] for w in plan["workers"]] == [["/creators/0", "/creators/1", "/creators/2", "/creators/3"],
                                                     ["/creators/4"]]
    b.validate_plan(plan, raw)


@pytest.mark.parametrize("raw,limits,code", [
    (creators(3, extra=5), dict(max_paths=6), "indivisible_list_entry_bound"),
    (yaml.safe_dump({"creators": [{"name": "A"}, {"name": "x" * 400}]}), dict(max_inventory_bytes=300),
     "indivisible_list_entry_bound"),
    (yaml.safe_dump({"study": {f"k{i}": i for i in range(7)}}), dict(max_paths=6), "indivisible_field_bound"),
    (yaml.safe_dump({"name": "x" * 400}), dict(max_inventory_bytes=300), "indivisible_field_bound"),
    (creators(12), dict(max_paths=6, max_workers=4), "worker_count_bound"),
], ids=["entry_paths", "entry_bytes", "mapping_paths", "scalar_bytes", "worker_count"])
def test_an_entry_or_field_larger_than_a_worker_is_refused_not_divided(raw, limits, code):
    with pytest.raises(b.AuditBatchError, match=f"^{code}$"):
        b.make_plan(raw, **limits)


def test_split_plans_are_a_pure_function_of_the_record_and_bounds():
    raw = creators(12)
    reordered = yaml.safe_dump({"zeta": "last", "creators": [{"affiliation": f"Institute {i}", "name": f"Person {i}"}
                                                             for i in range(12)], "title": "Example"}, sort_keys=False)
    first, second = b.make_plan(raw, max_paths=6), b.make_plan(raw, max_paths=6)
    assert b.canonical_bytes(first) == b.canonical_bytes(second)
    other = b.make_plan(reordered, max_paths=6)
    assert other["field_roots"] == first["field_roots"] and other["workers"] == first["workers"]
    assert other["sha256"] != first["sha256"]  # the original bytes still differ
    with pytest.raises(b.AuditBatchError, match="plan_original_mismatch"):
        b.validate_plan(first, reordered)


@pytest.mark.parametrize("forge,code", [
    ("whole_and_entries", "plan_roots"), ("unneeded_split", "plan_roots"), ("missing_entry", "plan_roots"),
    ("lexicographic_order", "plan_roots"), ("leading_zero", "plan_roots"), ("deeper_root", "plan_roots"),
    ("missing_last_entry", "plan_path_owner_missing")])
def test_forged_split_roots_are_refused_without_the_original(forge, code):
    raw = creators(12)
    plan = b.make_plan(raw, max_paths=6)
    roots = plan["field_roots"]
    if forge == "whole_and_entries":
        roots.insert(0, "/creators")
    if forge == "unneeded_split":
        plan = b.make_plan(raw, max_paths=96)
        plan["field_roots"] = [f"/creators/{i}" for i in range(12)] + ["/title", "/zeta"]
    if forge == "missing_entry":
        roots.remove("/creators/5")
    if forge == "missing_last_entry":
        roots.remove("/creators/11")
    if forge == "lexicographic_order":
        plan["field_roots"] = sorted(roots)
    if forge == "leading_zero":
        roots[1] = "/creators/01"
    if forge == "deeper_root":
        roots[0] = "/creators/0/name"
    rebind(plan)
    workers = proposals(b.make_plan(raw, max_paths=6))
    report = b.check_worker(next(iter(workers.values())), plan, "worker_0001")
    assert not report["passed"] and {e["code"] for e in report["errors"]} == {code}
    with pytest.raises(b.AuditBatchError):
        b.validate_plan(plan, raw)


# --- downstream consumers ----------------------------------------------------------------

def test_worker_removals_are_scoped_to_its_own_entries():
    plan = b.make_plan(creators(12), max_paths=6)
    first = plan["workers"][0]
    assert first["roots"] == ["/creators/0", "/creators/1", "/creators/2"]
    for removal, passed in [("/creators/1", True), ("/creators/2/affiliation", True),
                            ("/creators/3/affiliation", False), ("/creators", False), ("/title", False)]:
        workers = proposals(plan, {first["id"]: [removal_finding("/creators/1/name", removal)]})
        value = json.loads(workers[first["id"]])
        row = next(r for r in value["source_review"]["values"] if r["path"] == "/creators/1/name")
        row["claims"][0]["verdict"] = "revise"
        value["findings"][0]["review_paths"] = ["/creators/1/name"]
        report = b.check_worker(encode(value), plan, first["id"])
        assert report["passed"] is passed, (removal, report)
        if not passed:
            assert {e["code"] for e in report["errors"]} == {"worker_removal_owner"}


def test_split_plan_assembles_every_row_once_in_inventory_order():
    raw = creators(12)
    plan = b.make_plan(raw, max_paths=6)
    workers = proposals(plan)
    assert set(workers) == {w["id"] for w in plan["workers"]}
    for key, proposal in workers.items():
        assert b.check_worker(proposal, plan, key)["passed"]
    audit, lineage = b.assemble(plan, workers, encode(integration(plan, workers)))
    rows = json.loads(audit)["source_review"]["values"]
    assert [r["path"] for r in rows] == [r["path"] for r in plan["inventory"]["values"]]
    assert {r["path"]: r["origin"]["worker_id"] for r in lineage["rows"]} == owners(plan)


@pytest.mark.parametrize("removal,code", [("/creators", None), ("/creators/7", None), ("/absent", "removal_root_unknown")])
def test_integration_removals_are_judged_by_field_not_worker_split(removal, code):
    plan = b.make_plan(creators(12), max_paths=6)
    workers = proposals(plan)
    report = b.check_integration(encode(integration(plan, workers, [removal_finding("/creators", removal)])), plan, workers)
    if code is None:
        assert report["passed"], report
    else:
        assert not report["passed"] and code in {e["code"] for e in report["errors"]}


# --- the typed consumer, end to end ------------------------------------------------------

@pytest.fixture
def typed_inputs(tmp_path):
    root = tmp_path / "schema.yaml"
    root.write_text("id: https://example.test/typed\nname: typed\nimports: [child]\n")
    (tmp_path / "child.yaml").write_text("""id: https://example.test/child
name: child
prefixes: {linkml: 'https://w3id.org/linkml/'}
imports: [linkml:types]
default_range: string
classes:
  Creator:
    attributes:
      name: {}
      affiliation: {}
  Dataset:
    attributes:
      title: {}
      zeta: {}
      creators: {range: Creator, multivalued: true, inlined_as_list: true}
""")
    bundle = b"Preamble\nFILE: manual.txt\nPATH: manual.txt\nExample release provides a complete description.\nFILE: other.txt\nPATH: other.txt\nAdditional source.\n"
    manifest = manifest_from_bytes(bundle, "invented")
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": row["id"], "status": status} for row, status in zip(manifest["chunks"],
                                      ("nothing_relevant", "redundant_with", "duplicate_of"))]}
    context = {"format": "omission_context_v1", "root_class": "Dataset", "scopes": [
        {"owner": "", "referent": "Example", "release": "1", "scope": "This release only."}],
        "source_policy": {"priority": ["manual.txt", "other.txt"], "basis": "Invented fixture."}, "vocabulary": {}}
    return dict(protocol="typed_audit_protocol_v1", original_full=creators(12).encode(),
        bundle=bundle, manifest=b.canonical_bytes(manifest), receipt=b.canonical_bytes(receipt),
        context=b.canonical_bytes(context), schema_path=root, max_output_tokens=4000,
        max_paths=6, max_workers=8)


def test_typed_packet_checks_and_assembles_a_split_plan(typed_inputs):
    packet = ta.prepare(**typed_inputs)
    plan = packet["plan"]
    assert len(plan["workers"]) == 5 and plan["workers"][0]["roots"] == ["/creators/0", "/creators/1", "/creators/2"]
    request = packet["omission_request"]
    chunk = next(row for row in request["payload"]["chunks"] if row["source"] == "manual.txt")
    quote = {"source": "manual.txt", "chunk": chunk["chunk"], "quote": "Example release provides a complete description."}
    omission = b.canonical_bytes({"format": "omission_inventory_v1", "request_sha256": request["request_sha256"],
        "chunks": [{"chunk": row["chunk"], "status": "no_omission", "reason": "No candidate declared.", "candidates": []}
                   for row in request["payload"]["chunks"]]})
    rows = {r["path"]: r for r in plan["inventory"]["values"]}
    saved = {}
    for worker in plan["workers"]:
        raw = b.canonical_bytes({"findings": [], "summary": "No populated-field concern.", "source_review": {
            "artifact": "original_full", "sha256": plan["original_full_sha256"],
            "values": [{"path": p, "claims": [{"text": rows[p]["text"], "verdict": "supported", "attributed_to": [],
                "claim_status": "fact", "source_status": "fact", "evidence": [quote],
                "reason": "The source states this value."}]} for p in worker["paths"]]}})
        saved[worker["id"]] = ta.capture_response(ta.worker_request(packet, worker["id"]), raw)
        assert ta.check_worker(packet, worker["id"], saved[worker["id"]])["passed"]
    index = ta.index(packet, saved, omission)
    inner = index["index"]
    delta = {"kind": "audit_integration_v2", "proposal_index_sha256": inner["sha256"],
             "retain_other_rows_from_index_sha256": inner["sha256"], "row_replacements": [], "finding_decisions": [],
             "new_findings": [], "summary": "No finding.", "omission_dispositions": []}
    assembly = ta.assemble(packet, saved, omission, ta.capture_response(index, b.canonical_bytes(delta)))
    checked = ta.check(assembly, derivations=ta.DerivationCache())
    assert checked["passed"] and checked["independently_reconstructed"]
    assert checked["source_review"]["values_required"] == checked["source_review"]["values_reviewed"] == len(rows) == 26
    assert [r["path"] for r in json.loads(ta._unblob(assembly["audit"], ta.audit_grammar.MAX_BYTES))["source_review"]["values"]] \
        == [r["path"] for r in plan["inventory"]["values"]]
