"""Offline binding/coverage tests, not empirical omission recall evidence."""
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from data_sheets_schema import audit_omissions as om
from data_sheets_schema.chunking import manifest_from_bytes


def raw(value):
    return json.dumps(value, ensure_ascii=False).encode()


@pytest.fixture
def inputs(tmp_path):
    schema = {"id": "https://example.test/omissions", "name": "omissions",
              "prefixes": {"linkml": "https://w3id.org/linkml/"}, "imports": ["linkml:types"],
              "default_range": "string", "classes": {
        "Dataset": {"attributes": {
            "name": {}, "description": {}, "count": {"range": "integer"},
            "available": {"range": "boolean"}, "issued": {"range": "date"},
            "methods": {"range": "Method", "multivalued": True, "inlined_as_list": True},
            "resources": {"range": "Dataset", "multivalued": True, "inlined_as_list": True},
            "variables": {"range": "Variable", "multivalued": True, "inlined_as_list": True},
            "ambiguous": {"any_of": [{"range": "integer"}, {"range": "string"}]},
            "controlled": {"range": "string", "values_from": ["fixture_terms"]},
            "reference": {"range": "Reference"},
        }},
        "Reference": {"attributes": {"id": {"identifier": True}, "description": {}}},
        "Method": {"attributes": {"name": {}, "used_software": {
            "range": "Software", "multivalued": True, "inlined_as_list": True}}},
        "Software": {"attributes": {"name": {}, "version": {"description": "Version stated as used."}}},
        "Variable": {"attributes": {"variable_name": {"description": "Name in a data file."}}},
    }}
    path = tmp_path / "schema.yaml"
    path.write_text(yaml.safe_dump(schema))
    bundle = ("Bundle preamble\nFILE: methods.txt\nPATH: methods.txt\n"
              "The release uses Tool 2.1 for processing. It contains two named methods.\n"
              "FILE: other.txt\nPATH: other.txt\nCompanion analyses use OtherTool 9.0.\n").encode()
    manifest = manifest_from_bytes(bundle, "fixture.txt")
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": c["id"], "status": status} for c, status in zip(manifest["chunks"],
                                      ("nothing_relevant", "redundant_with", "duplicate_of"))]}
    context = {"format": "omission_context_v1", "root_class": "Dataset", "scopes": [
        {"owner": "", "referent": "Recorded release", "release": "1.0", "scope": "The released data only."}],
        "source_policy": {"priority": ["methods.txt", "other.txt"], "basis": "Caller supplied."},
        "vocabulary": {}}
    return dict(record=b"name: Example\ncount: 0\navailable: false\nissued: 2026-10-02\n",
                bundle=bundle, manifest=raw(manifest), receipt=raw(receipt), context=raw(context),
                schema_path=path, max_output_tokens=8000)


@pytest.fixture
def prepared(inputs):
    return om.prepare(**inputs)


def answer(prepared, *, candidate=True):
    request = prepared.request()
    rows = [{"chunk": c["chunk"], "status": "no_omission", "reason": "None identified.", "candidates": []}
            for c in request["payload"]["chunks"]]
    if candidate:
        rows[1].update(status="omission", reason="Proposed missing version.", candidates=[{
            "id": "candidate-1", "kind": "omission", "source": "methods.txt",
            "quote": "The release uses Tool 2.1 for processing.",
            "target": {"owner": "", "slot_chain": ["methods", "used_software", "version"]},
            "missing_information": "The stated processing version.",
            "scope_basis": "The passage names the declared release."}])
    return {"format": om.FORMAT, "request_sha256": request["request_sha256"], "chunks": rows}


def test_complete_is_only_declared_coverage_not_semantic_certification(prepared, inputs):
    snapshot = copy.deepcopy(inputs)
    request = prepared.request()
    assert len(request["payload"]["chunks"]) == 3
    assert [c["prior_receipt_status"] for c in request["payload"]["chunks"]] == [
        "nothing_relevant", "redundant_with", "duplicate_of"]
    assert "Software" in request["payload"]["schema"]["classes"]
    assert "version" in request["payload"]["schema"]["classes"]["Software"]["slots"]
    assert "count: 0" in request["payload"]["record_yaml"]
    report = prepared.check(raw(answer(prepared)), saved_request=request)
    assert report["protocol_complete"] is True
    assert report["scientific_support"] == report["novelty"] == report["exhaustive_recall"] == "unverified"
    assert report["counts"]["prior_negative_chunks"] == 2
    assert report["counts"]["declared_candidates"] == 1
    assert inputs == snapshot
    with pytest.raises(FrozenInstanceError):
        prepared.payload_json = "changed"
    request["payload"]["chunks"].clear()
    assert len(prepared.request()["payload"]["chunks"]) == 3


def test_zero_candidates_can_be_complete_but_never_proves_no_omissions(prepared):
    result = prepared.check(raw(answer(prepared, candidate=False)))
    assert result["protocol_complete"] and result["counts"]["declared_candidates"] == 0
    assert result["exhaustive_recall"] == "unverified"


@pytest.mark.parametrize("mutation", [
    lambda a: a["chunks"].pop(),
    lambda a: a["chunks"].append(copy.deepcopy(a["chunks"][0])),
    lambda a: a["chunks"][0].update(chunk="c999"),
    lambda a: a.update(request_sha256="f" * 64),
    lambda a: a["chunks"][1].update(status="no_omission"),
    lambda a: a["chunks"][0].update(status="omission"),
    lambda a: a["chunks"][1]["candidates"][0].update(kind="unsupported"),
    lambda a: a["chunks"][1]["candidates"].append(copy.deepcopy(a["chunks"][1]["candidates"][0])),
    lambda a: a["chunks"][1]["candidates"][0].update(source="other.txt"),
    lambda a: a["chunks"][1]["candidates"][0].update(quote="The release uses Tool 4.0 for processing."),
    lambda a: a["chunks"][1]["candidates"][0].update(quote="The release ... for processing."),
    lambda a: a["chunks"][1]["candidates"][0].update(quote=" "),
    lambda a: a.update(passed=True),
    lambda a: a["chunks"][1]["candidates"][0].update(id="candidate-1\n"),
])
def test_response_mutations_never_complete(prepared, mutation):
    response = answer(prepared)
    mutation(response)
    assert not prepared.check(raw(response))["protocol_complete"]


@pytest.mark.parametrize("target", [
    {"owner": "/methods/0", "slot_chain": ["used_software"]},
    {"owner": "", "slot_chain": ["was_generated_by"]},
    {"owner": "", "slot_chain": ["methods", "0", "name"]},
    {"owner": "", "slot_chain": ["methods", "version"]},
    {"owner": "", "slot_chain": ["name", "version"]},
    {"owner": "", "slot_chain": ["reference", "description"]},
    {"owner": "", "slot_chain": ["resources", "description"]},
    {"owner": "", "slot_chain": ["ambiguous"]},
    {"owner": "", "slot_chain": ["controlled"]},
    {"owner": "", "slot_chain": []},
    {"owner": "/~2", "slot_chain": ["name"]},
])
def test_invalid_target_owner_shape_and_scope_refused(prepared, target):
    response = answer(prepared)
    response["chunks"][1]["candidates"][0]["target"] = target
    assert not prepared.check(raw(response))["protocol_complete"]


def test_existing_resource_needs_its_own_caller_scope(inputs):
    inputs["record"] = b"name: Collection\nresources:\n- name: Member\n"
    first = om.prepare(**inputs)
    response = answer(first)
    response["chunks"][1]["candidates"][0]["target"] = {"owner": "/resources/0", "slot_chain": ["description"]}
    assert not first.check(raw(response))["protocol_complete"]
    context = json.loads(inputs["context"])
    context["scopes"].append({"owner": "/resources/0", "referent": "Member", "release": None, "scope": "Member only."})
    inputs["context"] = raw(context)
    second = om.prepare(**inputs)
    response["request_sha256"] = second.request()["request_sha256"]
    assert second.check(raw(response))["protocol_complete"]


@pytest.mark.parametrize("key", ["record", "bundle", "manifest", "receipt", "context"])
def test_each_raw_input_is_bound_even_when_only_whitespace_changes(inputs, key):
    before = om.prepare(**inputs)
    inputs[key] += b"\n"
    if key == "bundle":
        with pytest.raises(ValueError):
            om.prepare(**inputs)
    else:
        after = om.prepare(**inputs)
        assert after.request()["request_sha256"] != before.request()["request_sha256"]
        with pytest.raises(ValueError, match="saved request differs"):
            after.check(raw(answer(after)), saved_request=before.request())


def test_capture_is_independent_of_later_schema_edits(inputs):
    before = om.prepare(**inputs)
    identity = before.request()["request_sha256"]
    source = inputs["schema_path"].read_text()
    inputs["schema_path"].write_text(source.replace("Version stated as used.", "Different version meaning."))
    after = om.prepare(**inputs)
    assert after.request()["request_sha256"] != identity
    assert before.check(raw(answer(before)))["protocol_complete"]
    inputs["schema_path"].unlink()
    assert before.request()["request_sha256"] == identity


@pytest.mark.parametrize("bad", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{} trailing', b'[]', b'\xff', b'{' + b'"x":[' * 70 + b'0' + b']}' * 70])
def test_malformed_response_is_a_failed_report(prepared, bad):
    assert not prepared.check(bad)["protocol_complete"]


@pytest.mark.parametrize("bad", [b'name: A\nname: B\n', b'name: .nan\n', b'name: &a [*a]\n', b'<<: {name: A}\n', b'resources: {name: Bad}\n', b'unknown: fact\n', b'issued: !!timestamp x\n', b'available: !!bool maybe\n'])
def test_ambiguous_unsafe_record_preparation_refused(inputs, bad):
    inputs["record"] = bad
    with pytest.raises(ValueError):
        om.prepare(**inputs)


def test_missing_receipt_chunk_does_not_remove_it_from_inventory(inputs):
    receipt = json.loads(inputs["receipt"])
    receipt["chunks"].pop()
    inputs["receipt"] = raw(receipt)
    prepared = om.prepare(**inputs)
    assert prepared.request()["payload"]["chunks"][-1]["prior_receipt_status"] == "unreviewed"
    assert len(answer(prepared)["chunks"]) == 3


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(max_output_tokens=True),
    lambda x: x.update(max_request_bytes=100),
    lambda x: x.update(context=b'{}'),
    lambda x: x.update(receipt=b'{"bundle_md5":"wrong","chunks":[]}'),
    lambda x: x.update(manifest=b'{}'),
])
def test_preparation_refuses_invalid_identity_and_limits(inputs, mutation):
    mutation(inputs)
    with pytest.raises(ValueError):
        om.prepare(**inputs)


def test_preamble_is_not_factual_evidence(prepared):
    response = answer(prepared)
    item = response["chunks"][1]["candidates"].pop()
    response["chunks"][1].update(status="no_omission")
    item.update(source="<preamble>", quote="Bundle preamble")
    response["chunks"][0].update(status="omission", candidates=[item])
    assert not prepared.check(raw(response))["protocol_complete"]


def test_policy_and_schemas_are_frozen_and_neutral(prepared):
    payload = prepared.request()["payload"]
    for name, digest in om.ASSET_SHA256.items():
        assert hashlib.sha256((om.ASSETS / name).read_bytes()).hexdigest() == digest
    policy = payload["policy"]
    for phrase in ("complete lineage in prose", "actual role", "data dictionary", "Companion-study",
                   "non-entity multivalued", "not a verified completeness claim", "no invented array indices"):
        assert phrase in policy
    for name in ("AI_READI", "CM4AI", "CHORUS", "VOICE", "Anthropic", "OpenAI"):
        assert name not in policy


def test_matching_companion_quote_and_already_carried_fact_are_not_certified(prepared):
    response = answer(prepared)
    item = response["chunks"][1]["candidates"].pop()
    response["chunks"][1].update(status="no_omission")
    item.update(source="other.txt", quote="Companion analyses use OtherTool 9.0.")
    response["chunks"][2].update(status="omission", candidates=[item])
    report = prepared.check(raw(response))
    # Deterministic evidence presence is not a scope/entailment judgment. The
    # instruction forbids promotion; the checker does not pretend to detect it.
    assert report["protocol_complete"] and report["scientific_support"] == "unverified"
    response = answer(prepared)
    response["chunks"][1]["candidates"][0]["target"]["slot_chain"] = ["name"]
    report = prepared.check(raw(response))
    assert report["protocol_complete"] and report["novelty"] == "unverified"


@pytest.mark.parametrize("kind", ["duplicate", "unknown", "unknown_status"])
def test_bad_receipt_identity_preserved_and_refused(inputs, kind):
    receipt = json.loads(inputs["receipt"])
    if kind == "duplicate":
        receipt["chunks"].append(receipt["chunks"][0])
    elif kind == "unknown":
        receipt["chunks"][0]["id"] = "c999"
    else:
        receipt["chunks"][0]["status"] = "maybe"
    inputs["receipt"] = raw(receipt)
    before = inputs["receipt"]
    with pytest.raises(ValueError):
        om.prepare(**inputs)
    assert inputs["receipt"] == before


def test_transitive_schema_bytes_bound_without_ambient_rereads(inputs):
    path = inputs["schema_path"]
    imported = path.with_name("base.yaml")
    source = yaml.safe_load(path.read_bytes())
    source["imports"].append("base")
    source["classes"]["Dataset"]["is_a"] = "Base"
    imported.write_text("id: https://example.test/base\nname: base\nclasses:\n  Base:\n    description: First meaning.\n")
    path.write_text(yaml.safe_dump(source))
    first = om.prepare(**inputs)
    imported.write_text(imported.read_text().replace("First meaning.", "Second meaning."))
    second = om.prepare(**inputs)
    assert first.request()["request_sha256"] != second.request()["request_sha256"]
    imported.unlink()
    assert first.check(raw(answer(first)))["protocol_complete"]


@pytest.mark.parametrize("change", ["duplicate", "remote", "conditional_parent"])
def test_ambiguous_schema_authority_refused(inputs, change):
    path = inputs["schema_path"]
    if change == "duplicate":
        path.write_text(path.read_text() + "\nname: repeated\n")
    else:
        schema = yaml.safe_load(path.read_bytes())
        if change == "remote":
            schema["imports"].append("https://example.test/uncaptured")
        else:
            schema["classes"]["Parent"] = {"any_of": [{"description": "Unsupported condition"}]}
            schema["classes"]["Dataset"]["is_a"] = "Parent"
        path.write_text(yaml.safe_dump(schema))
    with pytest.raises(ValueError):
        om.prepare(**inputs)


def test_no_provider_network_or_profile_selection(inputs, monkeypatch):
    import socket
    from data_sheets_schema import profiles
    def forbidden(*args, **kwargs):
        raise AssertionError("offline inventory attempted provider/network/profile selection")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(profiles, "select_profile", forbidden)
    monkeypatch.setenv("D4D_PROFILE", "nonexistent-ambient-profile")
    prepared = om.prepare(**inputs)
    assert prepared.check(raw(answer(prepared)))["protocol_complete"]


def cli_args(inputs, tmp_path):
    args = [sys.executable, "-m", "data_sheets_schema.audit_omissions"]
    for name in ("record", "bundle", "manifest", "receipt", "context"):
        path = tmp_path / (name + ".input")
        path.write_bytes(inputs[name])
        args += ["--" + name, str(path)]
    return args + ["--schema", str(inputs["schema_path"]), "--max-output-tokens", "8000"]


def test_actual_cli_prepare_check_and_hardlink_refusal(inputs, tmp_path):
    args = cli_args(inputs, tmp_path)
    request_path = tmp_path / "request.json"
    result = subprocess.run(args + ["--output", str(request_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    request = json.loads(request_path.read_bytes())
    prepared = om.prepare(**inputs)
    assert request == prepared.request()
    response = tmp_path / "response.json"
    response.write_bytes(raw(answer(prepared)))
    output = tmp_path / "checked.json"
    result = subprocess.run(args + ["--response", str(response), "--request", str(request_path),
                                   "--output", str(output)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_bytes())["protocol_complete"]
    alias = tmp_path / "alias.json"
    alias.hardlink_to(tmp_path / "record.input")
    before = alias.read_bytes()
    result = subprocess.run(args + ["--output", str(alias)], capture_output=True, text=True)
    assert result.returncode != 0 and alias.read_bytes() == before


# Independently reproduced scope-boundary regressions (#4267).
@pytest.mark.parametrize('inheritance', ['direct', 'transitive', 'mixin'])
@pytest.mark.parametrize('existing', [False, True])
def test_dataset_subclass_requires_separate_scope(inputs, inheritance, existing):
    schema = yaml.safe_load(inputs['schema_path'].read_text())
    classes = schema['classes']
    classes['Dataset']['attributes']['resources']['range'] = 'ChildDataset'
    if inheritance == 'direct':
        classes['ChildDataset'] = {'is_a': 'Dataset'}
    elif inheritance == 'transitive':
        classes['MiddleDataset'] = {'is_a': 'Dataset'}
        classes['ChildDataset'] = {'is_a': 'MiddleDataset'}
    else:
        classes['ChildDataset'] = {'mixins': ['Dataset']}
    inputs['schema_path'].write_text(yaml.safe_dump(schema))
    if existing:
        inputs['record'] = b'name: Collection\nresources:\n- name: Member\n'
    prepared = om.prepare(**inputs)
    response = answer(prepared)
    response['chunks'][1]['candidates'][0]['target'] = {'owner': '', 'slot_chain': ['resources', 'description']}
    assert not prepared.check(raw(response))['protocol_complete']

def test_explicit_child_scope_is_allowed(inputs):
    schema = yaml.safe_load(inputs['schema_path'].read_text())
    schema['classes']['Dataset']['attributes']['resources']['range'] = 'ChildDataset'
    schema['classes']['ChildDataset'] = {'is_a': 'Dataset'}
    inputs['schema_path'].write_text(yaml.safe_dump(schema))
    inputs['record'] = b'name: Collection\nresources:\n- name: Member\n'
    context = json.loads(inputs['context'])
    context['scopes'].append({'owner':'/resources/0','referent':'Member','release':None,'scope':'Member only.'})
    inputs['context'] = raw(context)
    prepared = om.prepare(**inputs)
    response = answer(prepared)
    response['chunks'][1]['candidates'][0]['target'] = {'owner': '/resources/0', 'slot_chain': ['description']}
    assert prepared.check(raw(response))['protocol_complete']
