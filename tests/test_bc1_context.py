"""BC1 captured context and term-policy regressions (offline, 2026-10-27)."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import audit_omissions as om, bc1_context as bc
from data_sheets_schema.chunking import manifest_from_bytes
from data_sheets_schema.schema_snapshot import capture_schema


def raw(value):
    return json.dumps(value, ensure_ascii=False).encode()


@pytest.fixture
def fixture(tmp_path):
    schema = {"id": "https://example.test/bc1", "name": "bc1", "prefixes": {
        "linkml": "https://w3id.org/linkml/"}, "imports": ["linkml:types"], "default_range": "string",
        "classes": {"CoreDataset": {"description": "Complete core semantics.", "attributes": {
            "core_only": {"description": "Core-only full description must not be truncated."}}},
            "Dataset": {"description": "Complete dataset semantics.", "attributes": {
            "name": {}, "available": {"range": "boolean"}, "count": {"range": "integer"},
            "description": {}, "instances": {"range": "Instance", "multivalued": True,
                                             "inlined_as_list": True}}},
            "Instance": {"description": "Instance semantics must survive.", "attributes": {
                "data_topic": {"range": "uriorcurie", "values_from": ["B2AI_TOPIC"],
                               "description": "Exact source topic, never guessed."},
                "data_substrate": {"range": "uriorcurie", "values_from": ["B2AI_SUBSTRATE"]},
                "other_topic": {"range": "uriorcurie", "values_from": ["unused_registry"],
                                "annotations": {"d4d:termSources": "CUSTOM"}}}}}}
    path = tmp_path / "schema.yaml"
    path.write_text(yaml.safe_dump(schema))
    snapshot = capture_schema(path, strict=True)
    context = {"format": "omission_context_v1", "root_class": "Dataset", "scopes": [
        {"owner": "", "referent": "Pediatric resource", "release": None, "scope": "Supplied resource only."}],
        "source_policy": {"priority": ["source.txt"], "basis": "Caller declaration."}, "vocabulary": {}}
    context_raw = raw(context)
    selection = {"bounded_carry": {"version": 1}, "inputs": {
        "profile": {"name": "neutral", "basis": "explicit fixture", "vocabulary": None},
        "context": {"path": str(tmp_path / "omission.json"), "sha256": hashlib.sha256(context_raw).hexdigest(),
                    "bytes": len(context_raw)}, "full_schema": bc._schema_pin(snapshot)}}
    bundle = b"FILE: source.txt\nPATH: source.txt\nSix Bridges literal source text; GenotypeGVCFs is mentioned.\n"
    manifest = manifest_from_bytes(bundle, "fixture.txt")
    receipt = {"bundle_md5": manifest["bundle_md5"], "chunks": [
        {"id": chunk["id"], "status": "nothing_relevant"} for chunk in manifest["chunks"]]}
    inputs = dict(record=b"name: Example\navailable: false\ncount: 0\ndescription: null\ninstances:\n- data_topic: GO:0008150\n",
                  bundle=bundle, manifest=raw(manifest), receipt=raw(receipt), context=context_raw,
                  schema_path=path, schema_snapshot=snapshot, max_output_tokens=8000)
    return selection, inputs


def policy(fixture):
    selection, inputs = fixture
    return bc.derive_term_policy(selection=selection, context_raw=inputs["context"],
                                 schema_snapshot=inputs["schema_snapshot"])


def test_neutral_policy_preserves_record_and_source_and_targets(fixture):
    selection, inputs = fixture
    original = deepcopy(inputs)
    prepared = om.prepare(**inputs, term_policy=policy(fixture))
    payload = prepared.request()["payload"]
    assert payload["record_yaml"].encode() == inputs["record"]
    assert payload["context"]["vocabulary"] == {}
    assert any("Six Bridges literal source text; GenotypeGVCFs" in chunk["text"] for chunk in payload["chunks"])
    assert inputs == original
    assert om._target({"owner": "", "slot_chain": ["instances", "data_topic"]}, payload)
    with pytest.raises(ValueError, match="vocabulary"):
        om._target({"owner": "", "slot_chain": ["instances", "data_substrate"]}, payload)
    with pytest.raises(ValueError, match="missing explicitly supplied vocabulary"):
        om.prepare(**inputs)


@pytest.mark.parametrize("value", ["B2AI_TOPIC:43", "OTHER:1", "prose description", False, 0,
                                   "https://evil.test/GO_1", "GO:"])
def test_undeclared_terms_do_not_gain_neutral_escape(fixture, value):
    _, inputs = fixture
    document = yaml.safe_load(inputs["record"])
    document["instances"][0]["data_topic"] = value
    inputs["record"] = yaml.safe_dump(document).encode()
    with pytest.raises(ValueError, match="controlled term"):
        om.prepare(**inputs, term_policy=policy(fixture))


def test_null_is_not_false_and_unknown_null_still_refuses(fixture):
    _, inputs = fixture
    inputs["record"] = b"name: Example\ninstances:\n- data_substrate: null\n- other_topic: CUSTOM:001\n"
    result = om.prepare(**inputs, term_policy=policy(fixture))
    assert result.request()["payload"]["record_yaml"].encode() == inputs["record"]
    inputs["record"] = b"name: Example\nunknown: null\n"
    with pytest.raises(ValueError, match="undeclared slot"):
        om.prepare(**inputs, term_policy=policy(fixture))


def test_list_order_unicode_and_original_lexical_text_survive(fixture):
    _, inputs = fixture
    inputs["record"] = ("name: Café dataset\navailable: false\ncount: 0\ndescription: null\n"
                        "instances:\n- data_topic: NCIT:C123\n- data_topic: GO:0008150\n").encode()
    result = om.prepare(**inputs, term_policy=policy(fixture)).request()["payload"]
    assert result["record_yaml"].encode() == inputs["record"]
    parsed = yaml.safe_load(result["record_yaml"])
    assert parsed["available"] is False and parsed["description"] is None and parsed["count"] == 0
    assert [r["data_topic"] for r in parsed["instances"]] == ["NCIT:C123", "GO:0008150"]


def test_legacy_none_is_byte_identical_and_does_not_add_policy(fixture):
    _, inputs = fixture
    inputs["record"] = b"name: Example\navailable: false\ncount: 0\ndescription: null\n"
    ordinary = om.prepare(**inputs)
    explicit = om.prepare(**inputs, term_policy=None)
    assert ordinary.payload_json == explicit.payload_json
    assert "term_policy" not in ordinary.request()["payload"]


@pytest.mark.parametrize("field", ["schema_catalog_sha256", "context_sha256", "external_terms", "profile"])
def test_tampered_policy_cannot_replay(fixture, field):
    _, inputs = fixture
    selected = policy(fixture)
    selected[field] = {} if field in {"external_terms", "profile"} else "0" * 64
    with pytest.raises(ValueError, match="BC1"):
        om.prepare(**inputs, term_policy=selected)


def test_direct_prepared_replay_checks_exact_context_byte_identity(fixture):
    _, inputs = fixture
    prepared = om.prepare(**inputs, term_policy=policy(fixture))
    payload = json.loads(prepared.payload_json)
    payload["term_policy"]["context_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="captured context byte identity"):
        om.Prepared(om._json(payload)).check(b"{}")


def test_evaluation_rationale_cannot_replace_or_influence_context(fixture, tmp_path, monkeypatch):
    selection, inputs = fixture
    selection["inputs"]["source_manifest"] = None
    captured = SimpleNamespace(full_schema=inputs["schema_snapshot"], core_schema=inputs["schema_snapshot"], document=lambda: deepcopy(selection),
                               raw=lambda path: inputs["context"])
    before = bc.schema_context(captured, inputs["record"].decode())
    before_generation = bc.generation_context(captured)
    before_policy = policy(fixture)
    eval_path = tmp_path / "data" / "context" / "kids_first_context.yaml"
    eval_path.parent.mkdir(parents=True)
    eval_path.write_text("format: d4d-evaluation-context-1\nhuman_subjects: POISON_EVALUATION_RATIONALE\n")
    monkeypatch.chdir(tmp_path)
    assert bc.schema_context(captured, inputs["record"].decode()) == before
    assert bc.generation_context(captured) == before_generation
    assert policy(fixture) == before_policy
    assert "POISON_EVALUATION_RATIONALE" not in before
    assert "Complete dataset semantics." in before and "Exact source topic, never guessed." in before
    assert "Complete core semantics." in before and "Core-only full description must not be truncated." in before
    assert json.loads(before.split(bc.SCHEMA_HEADER)[1])["record_yaml"].encode() == inputs["record"]
    poisoned = raw({"format": "d4d-evaluation-context-1", "human_subjects": True})
    selection["inputs"]["context"].update(sha256=hashlib.sha256(poisoned).hexdigest(), bytes=len(poisoned))
    with pytest.raises(ValueError, match="authentic omission_context"):
        bc.derive_term_policy(selection=selection, context_raw=poisoned, schema_snapshot=inputs["schema_snapshot"])


def test_bridge2ai_requires_its_declared_vocabulary_and_does_not_use_neutral_policy(fixture):
    selection, inputs = fixture
    selection["inputs"]["profile"]["name"] = "bridge2ai"
    with pytest.raises(ValueError, match="vocabulary pin"):
        policy(fixture)
    selection["inputs"]["profile"]["vocabulary"] = {"sha256": "a" * 64}
    with pytest.raises(ValueError, match="missing a declared"):
        policy(fixture)
    context = json.loads(inputs["context"])
    context["vocabulary"] = {name: {"X:1": "term"} for name in ("B2AI_TOPIC", "B2AI_SUBSTRATE", "unused_registry")}
    inputs["context"] = raw(context)
    selection["inputs"]["context"].update(sha256=hashlib.sha256(inputs["context"]).hexdigest(), bytes=len(inputs["context"]))
    assert policy(fixture) is None


def test_core_context_uses_captured_bytes_and_requires_core_root(fixture, tmp_path):
    _, inputs = fixture
    captured = SimpleNamespace(full_schema=inputs["schema_snapshot"], core_schema=inputs["schema_snapshot"])
    before = bc.schema_context(captured, None)
    schema = yaml.safe_load(inputs["schema_path"].read_bytes())
    schema["classes"]["CoreDataset"]["description"] = "Ambient changed core semantics"
    inputs["schema_path"].write_text(yaml.safe_dump(schema))
    assert bc.schema_context(captured, None) == before
    del schema["classes"]["CoreDataset"]
    missing = tmp_path / "missing_core.yaml"
    missing.write_text(yaml.safe_dump(schema))
    captured.core_schema = capture_schema(missing, strict=True)
    with pytest.raises(ValueError, match="missing class CoreDataset"):
        bc.schema_context(captured, None)
