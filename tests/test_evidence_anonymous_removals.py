"""Exact-original-bound whole-member proofs; no model or provider calls."""
import copy
import datetime
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import chunking, evidence_assertions as evidence, source_review


def encoded(value):
    return yaml.safe_dump(value, sort_keys=False).encode()


def rule(raw, path="/roles/0", **extra):
    return {"path": path, "match": "anonymous_structure_v1",
            "original_full_sha256": hashlib.sha256(raw).hexdigest(), **extra}


def declarations(raw, *paths):
    return {"findings": [{"remove_relationship": rule(raw, path)} for path in paths]}


def check(original, final, *paths, raw=None, audit=None, version=4):
    raw = encoded(original) if raw is None else raw
    audit = declarations(raw, *(paths or ("/roles/0",))) if audit is None else audit
    return evidence.check_relationship_removals(audit, original, final,
        protocol_version=version, original_raw=raw)


def assert_contract(problems, text=None):
    assert problems and all(p["kind"] == "evidence_contract" for p in problems)
    if text:
        assert any(text in p["detail"] for p in problems)


def test_valid_anonymous_removal_retains_other_member_and_inputs():
    original = {"roles": [{"role": "rejected", "description": "prose"}, {"role": "kept"}]}
    final = {"roles": [{"role": "kept", "notes": "corrected prose"}]}
    raw = encoded(original)
    audit = declarations(raw, "/roles/0")
    before = copy.deepcopy((original, final, audit))
    assert check(original, final, raw=raw, audit=audit) == []
    assert (original, final, audit) == before
    assert encoded(original) == raw


def test_grouped_removals_use_original_positions_and_allow_survivor_reordering():
    original = {"roles": [{"role": name} for name in ("drop-a", "keep-a", "drop-b", "keep-b")]}
    final = {"roles": [original["roles"][3], original["roles"][1]]}
    assert check(original, final, "/roles/2", "/roles/0") == []


def test_independent_containers_and_escaped_dictionary_keys():
    original = {"outer/key": {"roles~": [{"role": "drop"}, {"role": "keep"}]},
                "other": [{"role": "remove"}, {"role": "retain"}]}
    final = {"outer/key": {"roles~": [{"role": "keep"}]}, "other": [{"role": "retain"}]}
    assert check(original, final, "/outer~1key/roles~0/0", "/other/0") == []


def test_unselected_named_peers_keep_all_nested_identity_fields():
    peer = {"name": "Kept", "person": {"id": "urn:kept", "orcid": "kept-orcid"}, "count": 0}
    original = {"roles": [{"role": "drop"}, peer]}
    survivor = copy.deepcopy(peer)
    survivor["person"]["notes"] = "new narrative"
    assert check(original, {"roles": [survivor]}) == []
    survivor["person"]["id"] = "urn:changed"
    assert_contract(check(original, {"roles": [survivor]}), "new, changed")


@pytest.mark.parametrize("value", [0, False, 0.0, -0.0, "anchor", {"nested": 0}, [False]])
def test_nonempty_typed_anchors(value):
    original = {"roles": [{"value": value}, {"value": "other"}]}
    assert check(original, {"roles": [original["roles"][1]]}) == []


@pytest.mark.parametrize("unanchored", [{}, {"description": "Only prose"}, {"value": None},
    {"value": ""}, {"value": "  "}, {"value": []}, {"value": [{}, []]}])
@pytest.mark.parametrize("position", [0, 1])
def test_every_original_member_requires_anchor(unanchored, position):
    original = {"roles": [{"role": "drop"}, {"role": "keep"}]}
    original["roles"][position] = unanchored
    assert_contract(check(original, {"roles": [original["roles"][1]]}), "structural anchor")


@pytest.mark.parametrize("paths", [("/roles/0",), ("/roles/0", "/roles/1")])
def test_original_structural_duplicates_rejected_even_if_both_selected(paths):
    original = {"roles": [{"role": "same", "notes": "Alice"}, {"role": "same", "notes": "Bob"}]}
    assert_contract(check(original, {"roles": []}, *paths), "duplicated or ambiguous")


@pytest.mark.parametrize("final", [
    {"roles": []},  # Undeclared sibling deletion.
    {"roles": [{"role": "keep"}, {"role": "keep"}]},
    {"roles": [{"role": "keep"}, {"role": "new"}]},
    {"roles": [{"role": "keep", "id": "manufactured"}]},
    {"roles": [{"role": "changed"}]},
    {"roles": [{"role": "keep", "endpoint": None}]},
    {"roles": ["keep"]},
    {}, {"roles": None}, {"roles": {}},
])
def test_no_undeclared_deletions_additions_mutations_or_container_replacement(final):
    original = {"roles": [{"role": "drop"}, {"role": "keep"}]}
    assert_contract(check(original, final))


def test_retained_or_narratively_disclaimed_target_is_explicitly_rejected():
    original = {"roles": [{"role": "drop"}, {"role": "keep"}]}
    final = {"roles": [{"role": "keep"}, {"role": "drop", "notes": "not established"}]}
    assert check(original, final)[0]["kind"] == "unsupported_relationship_retained"
    assert check(original, original)[0]["kind"] == "unsupported_relationship_retained"


def test_all_selected_requires_explicit_empty_list():
    original = {"roles": [{"role": "a"}, {"role": "b"}]}
    paths = ("/roles/0", "/roles/1")
    assert check(original, {"roles": []}, *paths) == []
    for final in ({}, {"roles": None}):
        assert_contract(check(original, final, *paths), "container" if "roles" in final else "ancestors")


@pytest.mark.parametrize("before,after", [(True, 1), (1, 1.0), (-0.0, 0.0),
    (["a", "b"], ["b", "a"]), ({"x": None}, {}), ({}, {"x": None})])
def test_scalar_types_sign_and_nested_structure_are_bound(before, after):
    original = {"roles": [{"role": "drop"}, {"role": "keep", "value": before}]}
    final = {"roles": [{"role": "keep", "value": after}]}
    assert_contract(check(original, final), "new, changed")


@pytest.mark.parametrize("before,after", [({"code": "a"}, {"code": "b"}),
    (["a"], ["b"]), ({"code": "a"}, '{"code":"a"}')])
def test_narrative_keys_do_not_hide_structured_values(before, after):
    original = {"roles": [{"role": "drop"}, {"role": "keep", "description": before}]}
    final = {"roles": [{"role": "keep", "description": after}]}
    assert_contract(check(original, final), "new, changed")


@pytest.mark.parametrize("identity", ["id", "name", "orcid", "target_dataset"])
@pytest.mark.parametrize("value", [None, "", "usable", 0])
@pytest.mark.parametrize("nested", [False, True])
def test_any_selected_identity_key_presence_prevents_anonymous_fallback(identity, value, nested):
    member = {"role": "drop", identity: value}
    if nested:
        member = {"role": "drop", "person": member}
    original = {"roles": [member, {"role": "keep"}]}
    assert_contract(check(original, {"roles": [original["roles"][1]]}), "identity fields")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"),
    datetime.date(2026, 1, 1), datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
    b"binary", {"set-member"}])
def test_nonfinite_and_yaml_only_scalar_types_fail_closed(value):
    original = {"roles": [{"value": value}, {"role": "keep"}]}
    assert_contract(check(original, {"roles": [original["roles"][1]]}))


@pytest.mark.parametrize("key", [True, 1, None])
def test_nonstring_mapping_keys_fail_closed(key):
    original = {"roles": [{key: "drop"}, {"role": "keep"}]}
    assert_contract(check(original, {"roles": [original["roles"][1]]}), "string keys")


def test_cycle_rejected_without_recursion_failure():
    cyclic = {"role": "drop"}
    cyclic["self"] = cyclic
    original = {"roles": [cyclic, {"role": "keep"}]}
    assert_contract(check(original, {"roles": [original["roles"][1]]}), "cyclic")


@pytest.mark.parametrize("path", ["/roles", "/roles/-1", "/roles/01", "/roles/3",
    "/roles/no", "roles/0", "/roles/~2", "/missing/0", "/roles/0/value/0"])
def test_invalid_or_nested_indexed_paths_fail_closed(path):
    original = {"roles": [{"value": [{"role": "drop"}]}, {"role": "keep"}]}
    assert_contract(check(original, {"roles": [original["roles"][1]]}, path))


def test_indexed_ancestor_is_not_mistaken_for_a_dictionary_key():
    original = {"groups": [{"roles": [{"role": "drop"}, {"role": "keep"}]}]}
    final = {"groups": [{"roles": [{"role": "keep"}]}]}
    assert_contract(check(original, final, "/groups/0/roles/0"), "dictionary-only")


@pytest.mark.parametrize("other", [
    {"path": "/roles"}, {"path": "/roles/0/value"}, {"path": "/roles/1/value"},
    {"path": "/roles/1", "identity": "/name"},
])
def test_whole_member_and_other_actions_in_same_container_do_not_mix(other):
    original = {"roles": [{"value": "drop"}, {"name": "keep", "value": "keep"}]}
    raw = encoded(original)
    audit = declarations(raw, "/roles/0")
    audit["findings"].append({"remove_relationship": other})
    result = check(original, {"roles": [original["roles"][1]]}, raw=raw, audit=audit)
    assert any("overlap" in p["detail"] for p in result)


def test_anonymous_and_legacy_actions_in_disjoint_containers_are_allowed():
    original = {"roles": [{"role": "drop"}, {"role": "keep"}],
                "people": [{"name": "remove"}, {"name": "retain"}]}
    raw = encoded(original)
    audit = declarations(raw, "/roles/0")
    audit["findings"].append({"remove_relationship": {"path": "/people/0", "identity": "/name"}})
    final = {"roles": [original["roles"][1]], "people": [original["people"][1]]}
    assert check(original, final, raw=raw, audit=audit) == []


def test_duplicate_whole_member_action_is_rejected():
    original = {"roles": [{"role": "drop"}, {"role": "keep"}]}
    assert_contract(check(original, {"roles": [original["roles"][1]]}, "/roles/0", "/roles/0"), "duplicate")


@pytest.mark.parametrize("change", [
    {"match": "other"}, {"identity": "/role"}, {"extra": True},
    {"original_full_sha256": "0" * 64}, {"original_full_sha256": None},
])
def test_exact_rule_shape_and_digest(change):
    original = {"roles": [{"role": "drop"}, {"role": "keep"}]}
    raw = encoded(original)
    audit = {"findings": [{"remove_relationship": rule(raw, **change)}]}
    assert_contract(check(original, {"roles": [original["roles"][1]]}, raw=raw, audit=audit))


def test_raw_binding_is_required_and_checks_bytes_not_reserialization():
    original = {"roles": [{"role": "drop"}, {"role": "keep"}]}
    raw = encoded(original)
    audit = declarations(raw, "/roles/0")
    final = {"roles": [original["roles"][1]]}
    assert_contract(evidence.check_relationship_removals(audit, original, final,
        protocol_version=4), "raw bytes")
    assert_contract(check(original, final, raw=b"# Changed bytes\n" + raw, audit=audit), "digest")
    assert check(original, final, raw=raw.decode(), audit=audit) == []


@pytest.mark.parametrize("before,after", [(True, 1), (1, 1.0), (-0.0, 0.0),
    ("original", "changed"), (datetime.date(2026, 1, 1), datetime.date(2026, 1, 2))])
def test_passed_original_tree_cannot_differ_from_raw_artifact(before, after):
    original = {"outside_list": before, "roles": [{"role": "drop"}, {"role": "keep"}]}
    raw = encoded(original)
    changed = copy.deepcopy(original)
    changed["outside_list"] = after
    assert_contract(check(changed, {"roles": [original["roles"][1]]}, raw=raw), "parsed original differs")


def test_passed_original_mapping_keys_cannot_exploit_python_bool_int_equality():
    original = {"outside_list": {True: "value"}, "roles": [{"role": "drop"}, {"role": "keep"}]}
    raw = encoded(original)
    changed = copy.deepcopy(original)
    changed["outside_list"] = {1: "value"}
    assert_contract(check(changed, {"roles": [original["roles"][1]]}, raw=raw), "parsed original differs")


def test_duplicate_yaml_keys_and_duplicate_json_operation_keys_are_not_last_wins():
    raw = b"roles: [{role: first, role: second}, {role: keep}]\n"
    original = yaml.safe_load(raw)
    assert_contract(check(original, {"roles": [original["roles"][1]]}, raw=raw), "duplicate")
    with pytest.raises(ValueError, match="duplicate"):
        evidence.load_json('{"path":"/roles/0","path":"/roles/1"}')


@pytest.mark.parametrize("version", [1, 2, 3])
def test_new_rule_is_rejected_and_legacy_outcomes_unchanged(version):
    original = {"roles": [{"role": "drop"}, {"role": "keep"}]}
    assert_contract(check(original, {"roles": [original["roles"][1]]}, version=version))
    named = {"roles": [{"name": "drop"}, {"name": "keep"}]}
    legacy = {"findings": [{"remove_relationship": {"path": "/roles/0", "identity": "/name"}}]}
    # This historically accepts loss of an unselected sibling. The new strict
    # survivor requirement does not silently change that legacy behavior.
    assert evidence.check_relationship_removals(legacy, named, {"roles": []},
        protocol_version=version) == []
    assert evidence.check_relationship_removals(legacy, named, {"roles": []},
        protocol_version=4) == []


@pytest.mark.parametrize("renderer,version", [(10, 1), (11, 2), (12, 3), (14, 3), (15, 4)])
def test_renderer_dispatch_is_explicit(renderer, version):
    assert evidence.protocol_for_renderer(renderer) == version
    assert evidence.instrument(version)


def reviewed(raw, *, artifact="original_full", chunks=None, rejected=()):
    """Synthetic mechanical source-review fixture, not semantic endorsement."""
    chunks = chunks or {"c001": {"source": "source.txt", "text": "Synthetic source."}}
    chunk, source = next(iter(chunks.items()))
    inventory = source_review.inventory(raw, artifact)
    rows = []
    for row in inventory["values"]:
        if row["record_metadata_allowed"]:
            rows.append({"path": row["path"], "metadata_reason": "Synthetic fixture metadata."})
            continue
        revise = any(row["path"].startswith(path + "/") for path in rejected)
        rows.append({"path": row["path"], "claims": [{
            "text": row["text"], "verdict": "revise" if revise else "supported", "attributed_to": [],
            "claim_status": "fact", "source_status": "unstated" if revise else "fact",
            "evidence": [] if revise else [{"source": source["source"], "chunk": chunk, "quote": source["text"]}],
            "reason": "Synthetic structural fixture; semantic support is outside this test."}]})
    return {"artifact": artifact, "sha256": inventory["sha256"], "values": rows}


def complete_audit(raw, paths=("/roles/0",), chunks=None):
    audit = declarations(raw.encode(), *paths)
    audit["summary"] = "Synthetic removal findings."
    audit["source_review"] = reviewed(raw, chunks=chunks, rejected=paths)
    for finding in audit["findings"]:
        path = finding["remove_relationship"]["path"]
        value_path = path + "/role"
        original = evidence.load_record(raw)
        quote = evidence._at(original, evidence._tokens(value_path))
        finding.update({"severity": "low", "record": "full", "slot": "roles",
                        "issue": "Synthetic unsupported relationship.", "review_paths": [value_path],
                        "evidence": [{"artifact": "original_full", "path": value_path,
                                      "op": "contains", "quote": quote}]})
    return audit


def test_audit_admission_checks_original_then_simultaneous_projected_removals():
    original = {"roles": [{"role": "drop-a"}, {"role": "keep"}, {"role": "drop-b"}]}
    raw = encoded(original).decode()
    audit = complete_audit(raw, ("/roles/0", "/roles/2"))
    chunks = {"c001": {"source": "source.txt", "text": "Synthetic source."}}
    result = evidence.check_audit(audit, artifacts={"original_full": raw}, chunks=chunks, protocol_version=4)
    assert result["findings"] == []
    assert result["source_review_original"]["claims_checked"] == 3
    audit["findings"][0]["remove_relationship"]["original_full_sha256"] = "0" * 64
    result = evidence.check_audit(audit, artifacts={"original_full": raw}, chunks=chunks, protocol_version=4)
    assert any("digest" in p["detail"] for p in result["findings"])


def file_fixture(tmp_path):
    bundle = tmp_path / "bundle.txt"
    bundle.write_text("FILE: source.txt\nPATH: source.txt\nSynthetic source.\n")
    manifest = tmp_path / "chunks.yaml"
    manifest.write_text(chunking.dump_manifest(chunking.build_manifest(bundle)))
    chunks, _ = evidence.source_chunks(bundle, manifest)
    original = tmp_path / "original.yaml"
    original.write_bytes(encoded({"roles": [{"role": "drop"}, {"role": "keep"}]}))
    final = tmp_path / "final.yaml"
    final.write_bytes(encoded({"roles": [{"role": "keep"}]}))
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps(complete_audit(original.read_text(), chunks=chunks)))
    report = tmp_path / "report.md"
    report.write_text("## Evidence assertions\n```json\n" + json.dumps({"claims": [],
        "source_review": reviewed(final.read_text(), artifact="final_full", chunks=chunks)}) + "\n```\n")
    return dict(audit=audit, bundle=bundle, manifest=manifest,
                artifacts={"original_full": original, "final_full": final}, report=report, protocol_version=4)


def test_real_file_audit_final_and_report_checks_bind_actual_bytes(tmp_path):
    args = file_fixture(tmp_path)
    paths = [args[k] for k in ("audit", "bundle", "manifest", "report")] + list(args["artifacts"].values())
    before = {path: path.read_bytes() for path in paths}
    result = evidence.check_files(**args)
    assert result["findings"] == []
    assert result["source_review_final"]["claims_checked"] == 1
    assert result["artifact_sha256"]["original_full"] == hashlib.sha256(before[args["artifacts"]["original_full"]]).hexdigest()
    assert {path: path.read_bytes() for path in paths} == before
    args["artifacts"]["final_full"].write_text("roles: []\n")
    result = evidence.check_files(**args)
    assert any("unselected" in p["detail"] for p in result["findings"])


def test_changed_original_header_fails_actual_file_digest_binding(tmp_path):
    args = file_fixture(tmp_path)
    original = args["artifacts"]["original_full"]
    original.write_bytes(b"# changed exact original\n" + original.read_bytes())
    result = evidence.check_files(**args)
    assert any("digest" in p["detail"] for p in result["findings"])


def test_read_only_cli_accepts_protocol_four_and_returns_failure_for_retention(tmp_path, capsys):
    args = file_fixture(tmp_path)
    argv = ["--protocol-version", "4", "--audit", str(args["audit"]), "--bundle", str(args["bundle"]),
            "--manifest", str(args["manifest"]), "--original-full", str(args["artifacts"]["original_full"]),
            "--final-full", str(args["artifacts"]["final_full"]), "--report", str(args["report"])]
    assert evidence.main(argv) == 0
    assert json.loads(capsys.readouterr().out)["findings"] == []
    args["artifacts"]["final_full"].write_bytes(args["artifacts"]["original_full"].read_bytes())
    assert evidence.main(argv) == 1
    assert any(p["kind"] == "unsupported_relationship_retained" for p in json.loads(capsys.readouterr().out)["findings"])
