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
    topic_forms = json.dumps({"version": 1, "sources": [
        {"id": "go", "label": "GO", "curies": [{"prefix": "GO", "local_prefix": ""}],
         "iri_bases": ["http://purl.obolibrary.org/obo/GO_"]},
        {"id": "ncit", "label": "NCIT", "curies": [{"prefix": "NCIT", "local_prefix": ""}],
         "iri_bases": ["http://purl.obolibrary.org/obo/NCIT_"]},
    ]})
    custom_forms = json.dumps({"version": 1, "sources": [
        {"id": "custom", "label": "CUSTOM", "curies": [{"prefix": "CUSTOM", "local_prefix": ""}],
         "iri_bases": ["https://example.test/custom/"]},
    ]})
    schema = {"id": "https://example.test/bc1", "name": "bc1", "prefixes": {
        "linkml": "https://w3id.org/linkml/",
        "GO": "http://purl.obolibrary.org/obo/GO_",
        "NCIT": "http://purl.obolibrary.org/obo/NCIT_",
        "CUSTOM": "https://example.test/custom/"}, "imports": ["linkml:types"], "default_range": "string",
        "classes": {"CoreDataset": {"description": "Complete core semantics.", "attributes": {
            "core_only": {"description": "Core-only full description must not be truncated."}}},
            "Dataset": {"description": "Complete dataset semantics.", "attributes": {
            "name": {}, "available": {"range": "boolean"}, "count": {"range": "integer"},
            "description": {}, "instances": {"range": "Instance", "multivalued": True,
                                             "inlined_as_list": True}}},
            "Instance": {"description": "Instance semantics must survive.", "attributes": {
                "data_topic": {"range": "uriorcurie", "values_from": ["B2AI_TOPIC"],
                               "description": "Exact source topic, never guessed.",
                               "annotations": {"d4d:termSources": "GO, NCIT",
                                               "d4d:termSourceIdentifierForms": topic_forms}},
                "data_substrate": {"range": "uriorcurie", "values_from": ["B2AI_SUBSTRATE"]},
                "other_topic": {"range": "uriorcurie", "values_from": ["unused_registry"],
                                "annotations": {"d4d:termSources": "CUSTOM",
                                                "d4d:termSourceIdentifierForms": custom_forms}}}}}}
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


def test_domain_inverse_is_the_only_catalog_content_removed():
    catalog = {"classes": {"domain_of": {"slots": {"example": {"definition": {
        "domain_of": ["A", "B"], "description": "Keep this verbatim.",
        "annotations": {"domain_of": "Not an inverse list."}}}}}},
        "enums": {"domain_of": {"permissible_values": {"domain_of": {"text": "domain_of"}}}}}
    before = deepcopy(catalog)
    result = bc.model_catalog(catalog)
    assert catalog == before
    expected = deepcopy(before)
    del expected["classes"]["domain_of"]["slots"]["example"]["definition"]["domain_of"]
    assert result == expected


@pytest.mark.parametrize("name", ["bridge2ai", "synthetic-pinned-profile"])
def test_pinned_profile_requires_its_declared_vocabulary_and_does_not_use_neutral_policy(fixture, name, monkeypatch, tmp_path):
    from data_sheets_schema import profiles
    if name not in profiles.PROFILES:
        monkeypatch.setitem(profiles.PROFILES, name, profiles.Profile(name, vocabulary_pin=tmp_path / "vocabulary.yaml"))
    selection, inputs = fixture
    selection["inputs"]["profile"]["name"] = name
    with pytest.raises(ValueError, match="vocabulary pin"):
        policy(fixture)
    selection["inputs"]["profile"]["vocabulary"] = {}
    with pytest.raises(ValueError, match="vocabulary pin"):
        policy(fixture)
    selection["inputs"]["profile"]["vocabulary"] = {
        "path": str(profiles.profile_named(name).pin_path.absolute()), "sha256": "a" * 64}
    with pytest.raises(ValueError, match="missing a declared"):
        policy(fixture)
    context = json.loads(inputs["context"])
    context["vocabulary"] = {name: {"X:1": "term"} for name in ("B2AI_TOPIC", "B2AI_SUBSTRATE", "unused_registry")}
    inputs["context"] = raw(context)
    selection["inputs"]["context"].update(sha256=hashlib.sha256(inputs["context"]).hexdigest(), bytes=len(inputs["context"]))
    assert policy(fixture) is None


@pytest.mark.parametrize("name", ["neutral", "synthetic-unpinned-profile"])
def test_unpinned_profile_uses_neutral_checks_independent_of_name(fixture, name, monkeypatch):
    from data_sheets_schema import profiles
    monkeypatch.setitem(profiles.PROFILES, name, profiles.Profile(name))
    selection, inputs = fixture
    selection["inputs"]["profile"]["name"] = name
    derived = policy(fixture)
    assert derived["profile"]["name"] == name
    om.prepare(**inputs, term_policy=derived)


@pytest.mark.parametrize("name", [None, "", " ", 3])
def test_profile_authority_still_requires_a_nonempty_name(fixture, name):
    selection, _ = fixture
    selection["inputs"]["profile"]["name"] = name
    with pytest.raises(ValueError, match="explicit captured profile"):
        policy(fixture)


@pytest.mark.parametrize("annotation", [
    "EDAM Data, EDAM Format, IANA media types",
    "EDAM Data; EDAM Format and IANA media types",
    "Étiquettes de données, Format (v2)",
])
def test_source_labels_with_spaces_in_captured_schema(fixture, annotation):
    selection, inputs = fixture
    schema = yaml.safe_load(inputs["schema_path"].read_bytes())
    schema["classes"]["Instance"]["attributes"]["data_substrate"]["annotations"] = {"d4d:termSources": annotation}
    inputs["schema_path"].write_text(yaml.safe_dump(schema))
    inputs["schema_snapshot"] = capture_schema(inputs["schema_path"], strict=True)
    selection["inputs"]["full_schema"] = bc._schema_pin(inputs["schema_snapshot"])
    sources = bc._sources(om._schema(inputs["schema_path"], schema_snapshot=inputs["schema_snapshot"]))
    assert all(label.strip() == label and label for label in sources["Instance"]["data_substrate"]["sources"])
    with pytest.raises(ValueError, match="no accepted identifier form"):
        policy(fixture)


@pytest.mark.parametrize("annotation", ["", "A,,B", "A;", "A, ;B", "A\x00B", "A\x7fB", "A\x85B", "A\nB", "A\tB"])
def test_source_labels_refuse_empty_items_and_controls(annotation):
    catalog = {"classes": {"Instance": {"slots": {"data_substrate": {"definition": {
        "annotations": {"d4d:termSources": annotation}}}}}}}
    with pytest.raises(ValueError, match="source"):
        bc._sources(catalog)


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


def test_real_schema_substrate_and_topic_identifier_forms_accept_and_reject(fixture):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "src" / "data_sheets_schema" / "schema" / "data_sheets_schema_all.yaml"
    snapshot = capture_schema(schema_path, strict=True)
    selection, inputs = fixture
    selection = deepcopy(selection)
    selection["inputs"]["full_schema"] = bc._schema_pin(snapshot)
    derived = bc.derive_term_policy(selection=selection, context_raw=inputs["context"], schema_snapshot=snapshot)
    assert derived["format"] == "bc1_neutral_term_policy_v2"
    substrate = derived["external_terms"]["Instance"]["data_substrate"]
    assert substrate["sources"] == ["EDAM Data", "EDAM Format", "IANA media types"]
    assert substrate["curie_prefixes"] == ["EDAM:data_", "EDAM:format_", "mediatypes:"]
    assert substrate["iri_prefixes"] == [
        "http://edamontology.org/data_",
        "http://edamontology.org/format_",
        "https://www.iana.org/assignments/media-types/",
    ]
    topic = derived["external_terms"]["Instance"]["data_topic"]
    assert topic["sources"] == ["EFO", "GO", "MeSH", "NCIT"]
    assert topic["curie_prefixes"] == ["EFO:", "GO:", "MESH:", "NCIT:"]
    for good in (
        "EDAM:data_0006", "EDAM:format_1915", "EDAM:format_3752",
        "http://edamontology.org/data_0006", "http://edamontology.org/format_3752",
        "mediatypes:text/csv", "mediatypes:application/vnd.apache.parquet",
        "https://www.iana.org/assignments/media-types/text/csv",
    ):
        bc.validate_term_value(good, policy=derived, cls="Instance", field="data_substrate")
    for bad in (
        "EDAM_Data:0006", "EDAM Format:3752", "IANA_media_types:text/csv",
        "EDAM:0006", "EDAM:topic_0003", "EDAM:operation_0004",
        "https://edamontology.org/data_0006", "http://www.iana.org/assignments/media-types/text/csv",
        "EDAM:data_", "EDAM:format_", "mediatypes:",
        "http://edamontology.org/data_", "https://www.iana.org/assignments/media-types/",
        "B2AI_SUBSTRATE:43", "CSV file",
    ):
        with pytest.raises(ValueError, match="controlled term"):
            bc.validate_term_value(bad, policy=derived, cls="Instance", field="data_substrate")
    for good_topic in (
        "GO:0008150", "MESH:D012640", "EFO:0000001", "NCIT:C12345",
        "http://purl.obolibrary.org/obo/GO_0008150", "https://purl.obolibrary.org/obo/GO_0008150",
        "http://id.nlm.nih.gov/mesh/D012640", "https://id.nlm.nih.gov/mesh/D012640",
        "http://purl.bioontology.org/ontology/MESH/D012640", "https://purl.bioontology.org/ontology/MESH/D012640",
        "http://www.ebi.ac.uk/efo/EFO_0000001", "https://www.ebi.ac.uk/efo/EFO_0000001",
        "http://purl.obolibrary.org/obo/EFO_0000001", "https://purl.obolibrary.org/obo/EFO_0000001",
        "http://purl.obolibrary.org/obo/NCIT_C12345", "https://purl.obolibrary.org/obo/NCIT_C12345",
    ):
        bc.validate_term_value(good_topic, policy=derived, cls="Instance", field="data_topic")
    for bad_topic in (
        "MeSH:D012640", "B2AI_TOPIC:1", "EDAM:data_0006", "GO:", "http://purl.obolibrary.org/obo/GO_", "Genomics",
    ):
        with pytest.raises(ValueError, match="controlled term"):
            bc.validate_term_value(bad_topic, policy=derived, cls="Instance", field="data_topic")


@pytest.mark.parametrize("bad_forms,match", [
    ("", "JSON string"),
    ("not json", r"^BC1 term-source identifier forms cannot be read safely \(JSONDecodeError\)$"),
    ('{"version": 1, "version": 1, "sources": []}', r"^BC1 term-source identifier forms cannot be read safely \(ValueError\)$"),
    ('{"version": 2, "sources": []}', "version 1"),
    ('{"version": 1, "sources": [], "extra": 1}', "exact version and sources"),
    ('{"version": 1, "sources": []}', "nonempty sources list"),
    (json.dumps({"version": 1, "sources": [{"id": "Bad_ID", "label": "CUSTOM", "curies": [{"prefix": "CUSTOM", "local_prefix": ""}], "iri_bases": []}]}), "invalid id"),
    (json.dumps({"version": 1, "sources": [
        {"id": "dup", "label": "CUSTOM", "curies": [{"prefix": "CUSTOM", "local_prefix": ""}], "iri_bases": []},
        {"id": "dup", "label": "OTHER", "curies": [{"prefix": "OTHER", "local_prefix": ""}], "iri_bases": []},
    ]}), "duplicate term-source id"),
    (json.dumps({"version": 1, "sources": [
        {"id": "one", "label": "CUSTOM", "curies": [{"prefix": "CUSTOM", "local_prefix": ""}], "iri_bases": []},
        {"id": "two", "label": "CUSTOM", "curies": [{"prefix": "OTHER", "local_prefix": ""}], "iri_bases": []},
    ]}), "duplicate term-source label"),
    (json.dumps({"version": 1, "sources": [{"id": "custom", "label": "CUSTOM", "curies": [], "iri_bases": []}]}), "nonempty curies or iri_bases"),
    (json.dumps({"version": 1, "sources": [{"id": "custom", "label": "CUSTOM", "curies": [{"prefix": "http", "local_prefix": ""}], "iri_bases": []}]}), "invalid CURIE prefix"),
    (json.dumps({"version": 1, "sources": [{"id": "custom", "label": "CUSTOM", "curies": [{"prefix": "CUSTOM", "local_prefix": "a:b"}], "iri_bases": []}]}), "invalid CURIE local_prefix"),
    (json.dumps({"version": 1, "sources": [{"id": "custom", "label": "CUSTOM", "curies": [], "iri_bases": ["://example.test/"]}]}), "invalid IRI base"),
    (json.dumps({"version": 1, "sources": [
        {"id": "one", "label": "CUSTOM", "curies": [{"prefix": "CUSTOM", "local_prefix": ""}], "iri_bases": []},
        {"id": "two", "label": "OTHER", "curies": [{"prefix": "CUSTOM", "local_prefix": "sub_"}], "iri_bases": []},
    ]}), "conflicting CURIE"),
    (json.dumps({"version": 1, "sources": [
        {"id": "one", "label": "CUSTOM", "curies": [], "iri_bases": ["https://example.test/base/"]},
        {"id": "two", "label": "OTHER", "curies": [], "iri_bases": ["https://example.test/base/sub/"]},
    ]}), "conflicting IRI base"),
    (json.dumps({"version": 1, "sources": [{"id": "custom", "label": "UNDECLARED", "curies": [{"prefix": "CUSTOM", "local_prefix": ""}], "iri_bases": []}]}), "no accepted identifier form"),
    (json.dumps({"version": 1, "sources": [
        {"id": "custom", "label": "CUSTOM", "curies": [{"prefix": "CUSTOM", "local_prefix": ""}], "iri_bases": []},
        {"id": "extra", "label": "EXTRA", "curies": [{"prefix": "NCIT", "local_prefix": ""}], "iri_bases": []},
    ]}), "undeclared label"),
])
def test_identifier_forms_parser_rejects_malformed_declarations(bad_forms, match):
    with pytest.raises(ValueError, match=match) as exc_info:
        bc._parse_identifier_forms(bad_forms, declared_labels=["CUSTOM"], cls="Instance", slot="other_topic")
    if '"version": 1, "version": 1' in bad_forms:
        assert exc_info.value.__cause__ is not None
        assert "duplicate evidence JSON key: version" in str(exc_info.value.__cause__)


def test_identifier_forms_accept_self_contained_prefix(fixture):
    selection, inputs = fixture
    schema = yaml.safe_load(inputs["schema_path"].read_bytes())
    schema["classes"]["Instance"]["attributes"]["other_topic"]["annotations"]["d4d:termSourceIdentifierForms"] = json.dumps({
        "version": 1, "sources": [
            {"id": "custom", "label": "CUSTOM", "curies": [{"prefix": "MISSING_PREFIX", "local_prefix": ""}], "iri_bases": ["https://example.test/custom/"]}
        ]})
    inputs["schema_path"].write_text(yaml.safe_dump(schema))
    inputs["schema_snapshot"] = capture_schema(inputs["schema_path"], strict=True)
    selection["inputs"]["full_schema"] = bc._schema_pin(inputs["schema_snapshot"])
    derived = policy(fixture)
    for value in ("MISSING_PREFIX:123", "https://example.test/custom/123"):
        bc.validate_term_value(value, policy=derived, cls="Instance", field="other_topic")


def test_identifier_forms_reject_conflicting_schema_expansion(fixture):
    selection, inputs = fixture
    schema = yaml.safe_load(inputs["schema_path"].read_bytes())
    schema["classes"]["Instance"]["attributes"]["other_topic"]["annotations"]["d4d:termSourceIdentifierForms"] = json.dumps({
        "version": 1, "sources": [
            {"id": "custom", "label": "CUSTOM", "curies": [{"prefix": "CUSTOM", "local_prefix": "sub_"}],
             "iri_bases": ["https://example.test/custom/other_"]}
        ]})
    inputs["schema_path"].write_text(yaml.safe_dump(schema))
    inputs["schema_snapshot"] = capture_schema(inputs["schema_path"], strict=True)
    selection["inputs"]["full_schema"] = bc._schema_pin(inputs["schema_snapshot"])
    with pytest.raises(ValueError, match="not in declared iri_bases"):
        policy(fixture)


def test_tampered_identifier_form_prefixes_cannot_replay_or_validate(fixture):
    _, inputs = fixture
    derived = policy(fixture)
    for key, tampered in (
        ("curie_prefixes", ["CUSTOM:", "EVIL:"]),
        ("iri_prefixes", ["https://evil.test/"]),
        ("identifier_forms", []),
    ):
        bad = deepcopy(derived)
        bad["external_terms"]["Instance"]["other_topic"][key] = tampered
        with pytest.raises(ValueError, match="BC1"):
            om.prepare(**inputs, term_policy=bad)
        with pytest.raises(ValueError, match="BC1"):
            bc.validate_term_value("CUSTOM:001", policy=bad, cls="Instance", field="other_topic")


def test_label_rename_and_legacy_v1_replay_work_without_code_changes(fixture):
    selection, inputs = fixture
    schema = yaml.safe_load(inputs["schema_path"].read_bytes())
    schema["classes"]["Instance"]["attributes"]["other_topic"]["annotations"] = {
        "d4d:termSources": "Renamed Custom Ontology (v2)",
        "d4d:termSourceIdentifierForms": json.dumps({"version": 1, "sources": [
            {"id": "custom", "label": "Renamed Custom Ontology (v2)",
             "curies": [{"prefix": "CUSTOM", "local_prefix": ""}],
             "iri_bases": ["https://example.test/custom/"]},
        ]}),
    }
    inputs["schema_path"].write_text(yaml.safe_dump(schema))
    inputs["schema_snapshot"] = capture_schema(inputs["schema_path"], strict=True)
    selection["inputs"]["full_schema"] = bc._schema_pin(inputs["schema_snapshot"])
    derived = policy(fixture)
    bc.validate_term_value("CUSTOM:42", policy=derived, cls="Instance", field="other_topic")
    bc.validate_term_value("https://example.test/custom/42", policy=derived, cls="Instance", field="other_topic")
    # Legacy v1 contract replay continues to work for historical v1 captures.
    schema["classes"]["Instance"]["attributes"]["other_topic"]["annotations"] = {"d4d:termSources": "CUSTOM"}
    del schema["classes"]["Instance"]["attributes"]["data_topic"]["annotations"]
    inputs["schema_path"].write_text(yaml.safe_dump(schema))
    inputs["schema_snapshot"] = capture_schema(inputs["schema_path"], strict=True)
    selection["inputs"]["full_schema"] = bc._schema_pin(inputs["schema_snapshot"])
    legacy = bc.derive_term_policy(selection=selection, context_raw=inputs["context"],
                                   schema_snapshot=inputs["schema_snapshot"], contract_version=1)
    assert legacy["format"] == "bc1_neutral_term_policy_v1"
    bc.validate_term_value("GO:0008150", policy=legacy, cls="Instance", field="data_topic")
    bc.validate_term_value("CUSTOM:42", policy=legacy, cls="Instance", field="other_topic")


def test_data_use_permission_is_multivalued_in_full_and_core_schemas():
    from pathlib import Path
    from linkml_runtime.utils.schemaview import SchemaView
    root = Path(__file__).resolve().parents[1]
    for filename in ("D4D_Data_Governance.yaml", "data_sheets_schema_all.yaml", "data_sheets_schema_core_all.yaml"):
        view = SchemaView(str(root / "src" / "data_sheets_schema" / "schema" / filename))
        slot = view.induced_slot("data_use_permission", "LicenseAndUseTerms")
        assert slot.multivalued is True
        assert str(slot.range) == "DataUsePermissionEnum"
