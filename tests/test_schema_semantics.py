"""Synthetic structural-guidance tests: no provider or scientific source data."""
from __future__ import annotations

import copy
import datetime
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import schema_digest, schema_semantics as semantics
from data_sheets_schema.evidence_score import slot_spec
from data_sheets_schema.profiles import NEUTRAL, Profile
from data_sheets_schema.schema_snapshot import SchemaSnapshot, capture_schema


@pytest.fixture
def schema(tmp_path):
    data = {
        "id": "https://example.invalid/gallery", "name": "gallery",
        "prefixes": {"ex": "https://example.invalid/gallery/", "xsd": "http://www.w3.org/2001/XMLSchema#"},
        "default_prefix": "ex", "default_range": "string",
        "types": {"string": {"base": "str", "uri": "xsd:string"},
                  "integer": {"base": "int", "uri": "xsd:integer"}},
        "classes": {
            "Card": {"description": "Root exhibit operating card.", "attributes": {
                "caption": {"description": "Public sign wording."},
                "settings": {"range": "Envelope", "multivalued": True, "inlined_as_list": True,
                             "description": "Motor settings only."},
                "empty_optional": {"description": "Unused optional sibling."},
                "required_hint": {"required": True, "description": "Required curator acknowledgement."}}},
            "BaseEnvelope": {"description": "Applies to electrical operating settings, not visitor instructions.",
                             "attributes": {"channel_a": {"description": "Upper continuous current in amperes."}}},
            "Envelope": {"is_a": "BaseEnvelope", "description": "Normal operation, not calibration.",
                         "attributes": {"channel_b": {"description": "Cooldown duration in seconds."}}},
        },
    }
    path = tmp_path / "schema.yaml"
    def save():
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        return path
    save()
    return data, path, save


def build(schema, record=None, **kwargs):
    return semantics.build_record({"settings": [{"channel_a": "SECRET_CURRENT", "channel_b": "SECRET_DURATION"}]} if record is None else record,
                                  "Card", schema[1], profile=NEUTRAL, **kwargs)


def test_full_semantics_inheritance_required_siblings_without_values(schema):
    data, _, save = schema
    long = "Complete semantic clause. " * 25 + "TAIL_MUST_REMAIN"
    data["classes"]["Envelope"]["attributes"]["channel_b"]["description"] = long
    save()
    result = build(schema)
    rendered = json.dumps(result)
    assert "SECRET_CURRENT" not in rendered and "SECRET_DURATION" not in rendered
    assert result["classes"]["Envelope"]["slots"]["channel_b"]["description"] == long
    assert result["classes"]["Envelope"]["slots"]["channel_a"]["description"] == "Upper continuous current in amperes."
    assert result["classes"]["Envelope"]["ancestors"][0]["description"].startswith("Applies to electrical")
    assert result["classes"]["Envelope"]["description"] == "Normal operation, not calibration."
    assert set(result["classes"]["Card"]["slots"]) == {"settings", "required_hint"}
    assert result["contexts"] == [
        {"path": "", "class": "Card", "occupied_slots": ["settings"]},
        {"path": "/settings/0", "class": "Envelope", "occupied_slots": ["channel_a", "channel_b"]}]


def test_meaning_changes_move_new_render_without_changing_legacy_render(schema):
    data, path, save = schema
    first = build(schema)
    old_digest = schema_digest.digest_text("Card", path, profile=NEUTRAL)
    old_spec = slot_spec("settings", "Card", path, profile=NEUTRAL)
    data["classes"]["Envelope"]["attributes"]["channel_b"]["description"] = "Minimum idle interval; no temperature value."
    data["classes"]["Envelope"]["description"] = "Only settings during calibration."
    save()
    second = build(schema)
    assert first["classes"] != second["classes"]
    assert first["schema"] != second["schema"]
    assert schema_digest.digest_text("Card", path, profile=NEUTRAL) == old_digest
    assert slot_spec("settings", "Card", path, profile=NEUTRAL) == old_spec


def test_contextual_override_and_mixins(schema):
    data, _, save = schema
    data["classes"]["Safety"] = {"mixin": True, "description": "Safety framing.", "attributes": {
        "permit": {"required": True, "description": "Supervisor authorization."}}}
    data["classes"]["Envelope"].update({"mixins": ["Safety"], "slot_usage": {
        "channel_a": {"description": "Override means peak current for this subclass."}}})
    save();result = build(schema)
    assert result["classes"]["Envelope"]["slots"]["channel_a"]["description"].startswith("Override")
    assert result["classes"]["Envelope"]["slots"]["permit"]["required"]
    assert {x["name"] for x in result["classes"]["Envelope"]["ancestors"]} == {"BaseEnvelope", "Safety"}


def test_deep_actual_objects_enum_and_profile_vocabulary(schema, tmp_path):
    data, path, save = schema
    data["classes"]["Envelope"]["attributes"]["inner"] = {"range": "Level2", "inlined": True}
    data["classes"]["Level2"] = {"attributes": {"inner": {"range": "Level3", "inlined": True}}}
    data["classes"]["Level3"] = {"attributes": {"mode": {"range": "Mode", "description": "Deep mode obligation."},
                                               "term": {"values_from": ["EX"], "description": "Use the declared term vocabulary."}}}
    data["enums"] = {"Mode": {"description": "Only operating modes.", "permissible_values": {
        "slow": {"description": "Low-speed rotation."}, "fast": {"description": "High-speed rotation."}}}}
    save()
    pin = tmp_path / "terms.yaml";pin.write_text("vocabularies:\n  EX:\n    EX:1: calibrated\n    EX:2: uncalibrated\n")
    record = {"settings": [{"inner": {"inner": {"mode": "slow", "term": "EX:1"}}}]}
    result = semantics.build_record(record, "Card", path, profile=Profile("test", vocabulary_pin=pin))
    assert len(result["contexts"]) == 4
    slots = result["classes"]["Level3"]["slots"]
    assert slots["mode"]["enum"]["permissible_values"]["slow"]["description"] == "Low-speed rotation."
    assert slots["term"]["vocabulary"]["pinned_terms"]["EX"] == {"EX:1": "calibrated", "EX:2": "uncalibrated"}
    assert result["profile_vocabulary_sha256"]


def test_pointers_escaped_and_record_order_deterministic(schema):
    data, path, save = schema
    data["classes"]["Card"]["attributes"]["a/b~c"] = {"range": "Envelope", "inlined": True}
    save()
    one = {"a/b~c": {"channel_b": "sensitive_b", "channel_a": "sensitive_a"}, "caption": "sensitive_caption"}
    two = {"caption": "sensitive_caption", "a/b~c": {"channel_a": "sensitive_a", "channel_b": "sensitive_b"}}
    first = semantics.render_record(one, "Card", path, profile=NEUTRAL)
    assert first == semantics.render_record(two, "Card", path, profile=NEUTRAL)
    assert '/a~1b~0c' in first and 'sensitive_' not in first


@pytest.mark.parametrize("raw,code", [
    ("caption: first\ncaption: second\n", "duplicate_record_key"),
    ("settings: [{channel_a: one, channel_a: two}]", "duplicate_record_key"),
    ("caption: .nan", "unsupported_record_scalar"),
    ("caption: .inf", "unsupported_record_scalar"),
    ("1: value", "record_keys_must_be_strings"),
    ("caption: !!binary YQ==", "unsupported_record_scalar"),
    ("a: &a {caption: x}\n<<: *a", "record_keys_must_be_strings_no_merges"),
    ("caption: \"\\uD800\"", "invalid_record_structure"),
    (b"\xff", "invalid_record_yaml"),
    ("[]", "record_root_must_be_mapping"),
])
def test_strict_record_input(schema, raw, code):
    with pytest.raises(semantics.SemanticGuidanceError, match=code):build(schema, raw)


@pytest.mark.parametrize("record,code", [
    ({"unknown_secret": "secret"}, "unknown_record_slot"),
    ({"settings": ["scalar"]}, "inline_object_must_be_mapping"),
    ({"settings": [{"channel_a": "x"}, 7]}, "inline_object_must_be_mapping"),
    ({"settings": {"secret_identifier": {"channel_a": "x"}}}, "multivalued_slot_requires_list"),
    ({"caption": []}, "single_slot_has_list"),
    ({"caption": {}}, "scalar_or_reference_has_object"),
])
def test_unsupported_record_paths(schema, record, code):
    with pytest.raises(semantics.SemanticGuidanceError, match=code) as exc:build(schema, record)
    assert "secret" not in str(exc.value)


def test_unknown_and_ambiguous_range_fail_closed(schema):
    data, _, save = schema
    data["classes"]["Card"]["attributes"]["caption"]["range"] = "Unknown"
    save()
    with pytest.raises(semantics.SemanticGuidanceError, match="unknown_or_ambiguous_schema_range"):build(schema, {"caption": "x"})
    data["classes"]["Card"]["attributes"]["caption"] = {"any_of": [{"range": "string"}, {"range": "Envelope"}]}
    save()
    with pytest.raises(semantics.SemanticGuidanceError, match="unsupported_schema_range_branch"):build(schema, {"caption": "x"})


def test_reference_boundary(schema):
    data, _, save = schema
    data["classes"]["NamedPart"] = {"description": "A referenced component, not embedded configuration.",
        "attributes": {"serial": {"identifier": True}, "hidden_setting": {"description": "Not reached through a reference."}}}
    data["classes"]["Card"]["attributes"]["part"] = {"range": "NamedPart"}
    save(); result = build(schema, {"part": "SECRET_SERIAL"})
    assert result["classes"]["Card"]["slots"]["part"]["representation"] == "reference"
    assert "NamedPart" not in result["classes"]
    assert 'hidden_setting' not in json.dumps(result) and 'SECRET_SERIAL' not in json.dumps(result)
    with pytest.raises(semantics.SemanticGuidanceError, match="scalar_or_reference_has_object"):build(schema, {"part": {"serial": "x"}})


def test_finite_recursive_objects_allowed_but_record_cycles_rejected(schema):
    data, _, save = schema
    data["classes"]["Envelope"]["attributes"]["next"] = {"range": "Envelope", "inlined": True}
    save()
    assert len(build(schema, {"settings": [{"next": {"channel_a": "x"}}]})["contexts"]) == 3
    cyclic = {};cyclic['next'] = cyclic
    with pytest.raises(semantics.SemanticGuidanceError, match="cyclic_record"):build(schema, {"settings": [cyclic]})
    with pytest.raises(semantics.SemanticGuidanceError):build(schema, "settings: [&a {next: *a}]")


def test_class_ancestry_cycle_rejected_before_induction(schema):
    data, _, save = schema
    data["classes"]["BaseEnvelope"]["is_a"] = "Envelope";save()
    with pytest.raises(semantics.SemanticGuidanceError, match="cyclic_class_ancestry"):build(schema)


def test_type_ancestry_semantics(schema):
    data, _, save = schema
    data["types"]["Duration"] = {"typeof": "string", "description": "Duration notation, not a label.", "pattern": "[0-9]+s"}
    data["classes"]["Card"]["attributes"]["caption"]["range"] = "Duration";save()
    typ = build(schema, {"caption": "SECRET"})["classes"]["Card"]["slots"]["caption"]["range_type"]
    assert typ["description"].startswith("Duration") and typ["parent"]["name"] == "string"
    data["types"]["string"]["typeof"] = "Duration";save()
    with pytest.raises(semantics.SemanticGuidanceError, match="cyclic_type_ancestry"):build(schema, {"caption": "x"})


def test_explicit_snapshot_is_frozen_and_bound(schema, tmp_path):
    data, path, save = schema
    snapshot = capture_schema(path, strict=True)
    original = build(schema, snapshot=snapshot)
    data["classes"]["Envelope"]["description"] = "Changed later";save()
    assert build(schema, snapshot=snapshot) == original
    assert build(schema) != original
    wrong = SchemaSnapshot(snapshot.sources, (snapshot.key[0], "bad"))
    with pytest.raises(semantics.SemanticGuidanceError, match="schema_snapshot_identity_mismatch"):build(schema, snapshot=wrong)
    other = tmp_path / 'other.yaml';other.write_bytes(path.read_bytes())
    with pytest.raises(semantics.SemanticGuidanceError, match="schema_snapshot_root_mismatch"):build(schema, snapshot=capture_schema(other))


def test_parsed_binding_has_no_cross_type_collisions(schema):
    date = build(schema, {"caption": datetime.date(2024, 1, 2)})["record_binding"]
    # Both are accepted record structures under a list of scalar values.
    data, _, save = schema;data["classes"]["Card"]["attributes"]["caption"]["multivalued"] = True;save()
    array = build(schema, {"caption": ["date", "2024-01-02"]})["record_binding"]
    assert date != array
    assert build(schema, {"caption": [True]})["record_binding"] != build(schema, {"caption": [1]})["record_binding"]


def test_raw_bytes_binding_and_no_scalar_echo(schema):
    raw = 'caption: NEVER_RENDER_THIS_VALUE\n'
    result = build(schema, raw)
    import hashlib
    assert result["record_binding"] == {"kind": "exact_record_bytes", "sha256": hashlib.sha256(raw.encode()).hexdigest()}
    assert 'NEVER_RENDER_THIS_VALUE' not in json.dumps(result)


def test_missing_profile_rejected(schema):
    with pytest.raises(semantics.SemanticGuidanceError, match="explicit_profile_required"):
        semantics.render_record({}, "Card", schema[1])


@pytest.mark.parametrize('name,value,code', [
    ('MAX_RENDER_BYTES', 30, 'guidance_byte_bound'),
    ('MAX_INPUT_BYTES', 10, 'record_byte_bound'),
    ('MAX_NODES', 2, 'record_structure_bound'),
    ('MAX_CONTEXTS', 1, 'schema_context_bound'),
    ('MAX_SLOTS', 1, 'schema_slot_bound'),
    ('MAX_CLASSES', 1, 'schema_class_bound'),
    ('MAX_DEPTH', 0, 'record_structure_bound'),
])
def test_bounds_fail_instead_of_truncating(schema, monkeypatch, name, value, code):
    monkeypatch.setattr(semantics, name, value)
    with pytest.raises(semantics.SemanticGuidanceError, match=code):build(schema)


def test_new_result_is_mutable_without_poisoning_later_guidance(schema):
    result = build(schema);result['classes']['Envelope']['slots']['channel_a']['description'] = 'CORRUPT'
    assert 'CORRUPT' not in json.dumps(build(schema))


def test_all_enum_values_and_structural_constraints_survive(schema):
    data, _, save = schema
    data['enums'] = {'Mode': {'permissible_values': {
        f'mode_{i}': {'description': f'Schema mode meaning {i}.'} for i in range(85)}}}
    data['classes']['Envelope']['attributes']['channel_b'] = {
        'range': 'Mode', 'multivalued': True, 'minimum_cardinality': 1,
        'maximum_cardinality': 3, 'description': 'Select declared operating modes.'}
    data['classes']['BaseEnvelope']['attributes']['channel_a']['pattern'] = '[0-9]+A'
    save()
    fields = build(schema, {'settings': [{'channel_a': '8A', 'channel_b': ['mode_84']}]})['classes']['Envelope']['slots']
    assert len(fields['channel_b']['enum']['permissible_values']) == 85
    assert fields['channel_b']['enum']['permissible_values']['mode_84']['description'] == 'Schema mode meaning 84.'
    assert fields['channel_b']['constraints']['minimum_cardinality'] == 1
    assert fields['channel_b']['constraints']['maximum_cardinality'] == 3
    assert fields['channel_a']['constraints']['pattern'] == '[0-9]+A'


def test_imported_meanings_and_frozen_closure(schema):
    data, path, save = schema
    imported = path.parent / 'parent.yaml'
    parent = data['classes'].pop('BaseEnvelope')
    data['imports'] = ['parent'];save()
    def write_parent(description):
        changed = copy.deepcopy(parent);changed['description'] = description
        imported.write_text(yaml.safe_dump({'id': 'https://example.invalid/parent', 'name': 'parent',
                                          'classes': {'BaseEnvelope': changed}}))
    write_parent('Imported ancestral motor meaning.')
    frozen = capture_schema(path, strict=True)
    original = build(schema, snapshot=frozen)
    assert len(original['schema']['sources']) == 2
    assert original['classes']['Envelope']['ancestors'][0]['description'] == 'Imported ancestral motor meaning.'
    write_parent('A different imported ancestral meaning.')
    assert build(schema) != original
    imported.unlink()
    assert build(schema, snapshot=frozen) == original


def test_vocabulary_bytes_are_bound_and_refresh(schema, tmp_path):
    data, path, save = schema
    data['classes']['Envelope']['attributes']['channel_b']['values_from'] = ['EX'];save()
    pin = tmp_path / 'vocab.yaml'
    profile = Profile('synthetic', vocabulary_pin=pin)
    pin.write_text('vocabularies: {EX: {EX:one: First schema term}}\n')
    a = semantics.build_record({'settings': [{'channel_b': 'private term'}]}, 'Card', path, profile=profile)
    pin.write_text('vocabularies: {EX: {EX:one: Other schema term}}\n')
    b = semantics.build_record({'settings': [{'channel_b': 'private term'}]}, 'Card', path, profile=profile)
    assert a['profile_vocabulary_sha256'] != b['profile_vocabulary_sha256']
    assert a['classes'] != b['classes']
    assert 'private term' not in json.dumps(b)


def test_exact_render_limit_includes_newline(schema, monkeypatch):
    raw = semantics.render_record({}, 'Card', schema[1], profile=NEUTRAL)
    size = len(raw.encode())
    monkeypatch.setattr(semantics, 'MAX_RENDER_BYTES', size)
    assert semantics.render_record({}, 'Card', schema[1], profile=NEUTRAL) == raw
    monkeypatch.setattr(semantics, 'MAX_RENDER_BYTES', size - 1)
    with pytest.raises(semantics.SemanticGuidanceError, match='guidance_byte_bound'):
        semantics.render_record({}, 'Card', schema[1], profile=NEUTRAL)


def pair_schema(schema):
    data, full, save = schema
    data['classes']['Dataset'] = data['classes'].pop('Card')
    data['classes']['CoreDataset'] = copy.deepcopy(data['classes']['Dataset'])
    save()
    core = full.parent / 'core.yaml'
    core.write_bytes(full.read_bytes())
    return data, full, core


def reconstruct(pair, role):
    record = copy.deepcopy(pair['records'][role])
    record['classes'] = {name: copy.deepcopy(pair['definitions'][reference])
                         for name, reference in record.pop('class_definition_refs').items()}
    return record


def test_pair_pooling_exactly_reconstructs_records_and_preserves_metadata(schema):
    _, full, core = pair_schema(schema)
    record = {'settings': [{'channel_a': 'PRIVATE_FULL', 'channel_b': 'PRIVATE_CORE'}]}
    expected_full = semantics.build_record(record, 'Dataset', full, profile=NEUTRAL)
    expected_core = semantics.build_record(record, 'CoreDataset', core, profile=NEUTRAL)
    before_single = semantics.render_record(record, 'Dataset', full, profile=NEUTRAL)
    raw = semantics.render_pair(record, record, schema_paths=(full, core), profile=NEUTRAL)
    pair = json.loads(raw)
    assert reconstruct(pair, 'original_full') == expected_full
    assert reconstruct(pair, 'original_core') == expected_core
    assert pair['records']['original_full']['class_definition_refs']['Envelope'] == pair['records']['original_core']['class_definition_refs']['Envelope']
    assert len(pair['definitions']) == 3  # two differently named roots, one identical child
    assert raw == semantics.render_pair(record, record, schema_paths=(full, core), profile=NEUTRAL)
    assert 'PRIVATE_FULL' not in raw and 'PRIVATE_CORE' not in raw
    assert semantics.render_record(record, 'Dataset', full, profile=NEUTRAL) == before_single


def test_pair_same_named_unequal_definitions_stay_separate(schema):
    data, full, core = pair_schema(schema)
    changed = copy.deepcopy(data)
    changed['classes']['Envelope']['attributes']['channel_b']['description'] = 'Different core-only semantic obligation.'
    core.write_text(yaml.safe_dump(changed, sort_keys=False))
    record = {'settings': [{'channel_b': 'PRIVATE'}]}
    pair = json.loads(semantics.render_pair(record, record, schema_paths=(full, core), profile=NEUTRAL))
    full_ref = pair['records']['original_full']['class_definition_refs']['Envelope']
    core_ref = pair['records']['original_core']['class_definition_refs']['Envelope']
    assert full_ref != core_ref
    assert pair['definitions'][full_ref]['slots']['channel_b']['description'] == 'Cooldown duration in seconds.'
    assert pair['definitions'][core_ref]['slots']['channel_b']['description'] == 'Different core-only semantic obligation.'
    for role, cls, path in [('original_full', 'Dataset', full), ('original_core', 'CoreDataset', core)]:
        assert reconstruct(pair, role) == semantics.build_record(record, cls, path, profile=NEUTRAL)


def test_pair_preserves_different_occupied_slot_subsets(schema):
    _, full, core = pair_schema(schema)
    a, b = {'settings': [{'channel_a': 'one'}]}, {'settings': [{'channel_b': 'two'}]}
    pair = json.loads(semantics.render_pair(a, b, schema_paths=(full, core), profile=NEUTRAL))
    assert pair['records']['original_full']['class_definition_refs']['Envelope'] != pair['records']['original_core']['class_definition_refs']['Envelope']
    assert reconstruct(pair, 'original_full') == semantics.build_record(a, 'Dataset', full, profile=NEUTRAL)
    assert reconstruct(pair, 'original_core') == semantics.build_record(b, 'CoreDataset', core, profile=NEUTRAL)


def test_pair_bounds_and_frozen_snapshots(schema, monkeypatch):
    data, full, core = pair_schema(schema)
    snapshots = (capture_schema(full, strict=True), capture_schema(core, strict=True))
    args = {'schema_paths': (full, core), 'profile': NEUTRAL, 'snapshots': snapshots}
    raw = semantics.render_pair({}, {}, **args)
    data['classes']['Dataset']['description'] = 'Changed later.'
    full.write_text(yaml.safe_dump(data, sort_keys=False))
    assert semantics.render_pair({}, {}, **args) == raw
    monkeypatch.setattr(semantics, 'MAX_PAIR_RENDER_BYTES', len(raw.encode()))
    assert semantics.render_pair({}, {}, **args) == raw
    monkeypatch.setattr(semantics, 'MAX_PAIR_RENDER_BYTES', len(raw.encode()) - 1)
    with pytest.raises(semantics.SemanticGuidanceError, match='pair_guidance_byte_bound'):
        semantics.render_pair({}, {}, **args)


@pytest.mark.parametrize('kwargs,code', [
    ({'schema_paths': ('only',)}, 'pair_requires_two_schema_paths'),
    ({'schema_paths': 'not_a_pair'}, 'pair_requires_two_schema_paths'),
    ({'snapshots': ()}, 'pair_requires_two_snapshots'),
])
def test_pair_configuration_shape_is_explicit(kwargs, code):
    with pytest.raises(semantics.SemanticGuidanceError, match=code):
        semantics.render_pair({}, {}, profile=NEUTRAL, **kwargs)


@pytest.mark.parametrize('field,value', [
    ('inherits', ['ParentMode']), ('is_a', 'ParentMode'), ('mixins', ['ParentMode']),
    ('include', [{'permissible_values': {'added': {'description': 'Additional declared option.'}}}]),
    ('minus', [{'permissible_values': {'local': {}}}]),
    ('matches', {'identifier_pattern': '^permitted', 'source_ontology': 'https://example.invalid/modes'}),
    ('reachable_from', {'source_ontology': 'https://example.invalid/modes', 'source_nodes': ['ex:root']}),
    ('values_from', ['https://example.invalid/modes']),
    ('code_set', 'https://example.invalid/modes'), ('code_set_tag', 'stable'),
    ('code_set_version', '2'), ('pv_formula', 'CODE'), ('concepts', ['ex:mode']),
])
def test_enum_expressions_never_masquerade_as_complete_local_values(schema, field, value):
    """#2184: local PVs cannot stand in for inherited/dynamic enum meaning."""
    data, _, save = schema
    data['classes']['Card']['attributes']['caption']['range'] = 'Mode'
    data['enums'] = {'Mode': {'permissible_values': {'local': {'description': 'Local option.'}}},
                     'ParentMode': {'permissible_values': {'parent': {'description': 'Parent option.'}}}}
    save()
    assert set(build(schema, {'caption': 'PRIVATE'})['classes']['Card']['slots']['caption']['enum']['permissible_values']) == {'local'}
    data['enums']['Mode'][field] = value;save()
    with pytest.raises(semantics.SemanticGuidanceError, match='unsupported_schema_enum_expression'):
        build(schema, {'caption': 'PRIVATE'})


@pytest.mark.parametrize('field,value', [
    ('any_of', [{'pattern': '^A$'}]), ('all_of', [{'pattern': '^A$'}]),
    ('none_of', [{'pattern': '^A$'}]), ('exactly_one_of', [{'pattern': '^A$'}]),
    ('union_of', ['string', 'integer']),
])
def test_type_branches_fail_instead_of_rendering_unconstrained_base(schema, field, value):
    """#2185: logical and union type semantics are explicitly unsupported."""
    data, _, save = schema
    data['classes']['Card']['attributes']['caption']['range'] = 'Restricted'
    data['types']['Restricted'] = {'typeof': 'string', field: value};save()
    with pytest.raises(semantics.SemanticGuidanceError, match='unsupported_schema_type_branch'):
        build(schema, {'caption': 'PRIVATE'})


@pytest.mark.parametrize('field,value', [
    ('equals_string', 'SCHEMA_FIXED_CODE'), ('equals_string_in', ['A', 'B']),
    ('equals_number', 0), ('structured_pattern', {'syntax': '[A-Z]+', 'interpolated': False}),
    ('unit', {'symbol': 's'}), ('implicit_prefix', 'ex'), ('repr', 'str(%s)'),
    ('minimum_value', 0), ('maximum_value', 12),
])
def test_type_constraints_and_ancestor_constraints_are_exact(schema, field, value):
    data, _, save = schema
    data['classes']['Card']['attributes']['caption']['range'] = 'Restricted'
    data['types']['Restricted'] = {'typeof': 'string', 'description': 'Restricted electrical notation.'}
    save();before = build(schema, {'caption': 'PRIVATE'})
    data['types']['string'][field] = value;save()
    after = build(schema, {'caption': 'PRIVATE'})
    actual = after['classes']['Card']['slots']['caption']['range_type']['parent'][field]
    assert actual == value
    assert before['classes'] != after['classes']
    assert 'PRIVATE' not in json.dumps(after)


def test_slot_ancestor_meanings_constraints_and_mixins_survive_induction(schema):
    """#2186: LinkML induced slots omit descriptions of is_a ancestors."""
    data, _, save = schema
    data['classes']['Card']['slots'] = ['operating_code']
    data['slots'] = {
        'base_code': {'description': 'Equipment operator, never supplier.', 'range': 'string', 'pattern': '^OP-',
                      'values_from': ['EX'], 'notes': ['Applies to the current operating role.']},
        'specialized_code': {'is_a': 'base_code', 'description': 'Operator certified for this gallery.',
                             'equals_string_in': ['OP-A', 'OP-B']},
        'safety_role': {'mixin': True, 'description': 'Authorized safety responsibility.', 'recommended': True},
        'operating_code': {'is_a': 'specialized_code', 'mixins': ['safety_role'], 'description': 'Local operating label.'},
    }
    data['classes']['Card']['slot_usage'] = {'operating_code': {'description': 'Context-specific operating label.'}}
    save()
    result = build(schema, {'operating_code': 'PRIVATE_OPERATOR'})
    slot = result['classes']['Card']['slots']['operating_code']
    assert slot['description'] == 'Context-specific operating label.'
    assert slot['is_a'] == 'specialized_code' and slot['mixins'] == ['safety_role']
    ancestors = {item['name']: item for item in slot['slot_ancestors']}
    assert set(ancestors) == {'base_code', 'specialized_code', 'safety_role'}
    assert ancestors['base_code']['description'] == data['slots']['base_code']['description']
    assert ancestors['base_code']['constraints']['pattern'] == '^OP-'
    assert ancestors['base_code']['vocabulary']['values_from'] == ['EX']
    assert ancestors['base_code']['notes'] == data['slots']['base_code']['notes']
    assert ancestors['specialized_code']['is_a'] == 'base_code'
    assert ancestors['specialized_code']['constraints']['equals_string_in'] == ['OP-A', 'OP-B']
    assert ancestors['safety_role']['description'] == 'Authorized safety responsibility.'
    assert 'PRIVATE_OPERATOR' not in json.dumps(result)
    first = result['classes']
    data['slots']['base_code']['description'] = 'An independently changed base role.';save()
    assert first != build(schema, {'operating_code': 'PRIVATE_OPERATOR'})['classes']


@pytest.mark.parametrize('edge', ['is_a', 'mixins'])
def test_slot_cycles_rejected_before_linkml_induction(schema, edge, monkeypatch):
    from linkml_runtime.utils.schemaview import SchemaView
    data, _, save = schema
    data['classes']['Card']['slots'] = ['cycle_a']
    data['slots'] = {'cycle_a': {edge: ['cycle_b'] if edge == 'mixins' else 'cycle_b'},
                     'cycle_b': {edge: ['cycle_a'] if edge == 'mixins' else 'cycle_a'}}
    save()
    def forbidden(*args, **kwargs):
        pytest.fail('LinkML induction reached before slot cycle was rejected')
    monkeypatch.setattr(SchemaView, 'class_induced_slots', forbidden)
    with pytest.raises(semantics.SemanticGuidanceError, match='cyclic_slot_ancestry'):
        build(schema, {'cycle_a': 'PRIVATE'})


def test_missing_slot_ancestor_and_slot_union_fail_closed(schema):
    data, _, save = schema
    data['classes']['Card']['slots'] = ['selected']
    data['slots'] = {'selected': {'is_a': 'missing'}};save()
    with pytest.raises(semantics.SemanticGuidanceError, match='unknown_slot_ancestor'):
        build(schema, {'selected': 'PRIVATE'})
    data['slots'] = {'selected': {'range': 'string', 'union_of': ['caption']}};save()
    with pytest.raises(semantics.SemanticGuidanceError, match='unsupported_schema_range_branch'):
        build(schema, {'selected': 'PRIVATE'})


def test_unsupported_constraints_on_ancestor_cannot_be_hidden_by_override(schema):
    data, _, save = schema
    data['classes']['Card']['slots'] = ['selected']
    data['slots'] = {'base': {'range': 'string', 'union_of': ['caption']},
                     'selected': {'is_a': 'base', 'range': 'string'}};save()
    with pytest.raises(semantics.SemanticGuidanceError, match='unsupported_schema_range_branch'):
        build(schema, {'selected': 'PRIVATE'})


@pytest.mark.parametrize('owner', ['slot', 'type'])
def test_interpolated_patterns_fail_instead_of_omitting_schema_settings(schema, owner):
    data, _, save = schema
    data['settings'] = {'letter': {'setting_value': '[A-Z]'}}
    declaration = data['classes']['Card']['attributes']['caption'] if owner == 'slot' else data['types']['string']
    declaration['structured_pattern'] = {'syntax': '{letter}+', 'interpolated': True};save()
    with pytest.raises(semantics.SemanticGuidanceError, match='unsupported_interpolated_schema_pattern'):
        build(schema, {'caption': 'PRIVATE'})


def test_unoccupied_optional_range_branch_is_not_added_to_guidance(schema):
    data, _, save = schema
    data['classes']['Card']['attributes']['empty_optional']['union_of'] = ['caption'];save()
    result = build(schema, {'caption': 'PRIVATE'})
    assert set(result['classes']['Card']['slots']) == {'caption', 'required_hint'}


def test_schema_notes_stay_schema_guidance_without_record_values(schema):
    data, _, save = schema
    data['classes']['BaseEnvelope']['notes'] = ['Laboratory operation only.']
    data['classes']['Envelope']['attributes']['channel_b']['notes'] = ['Current operation, not a future plan.']
    data['types']['string']['notes'] = ['Schema-authored scalar convention.'];save()
    result = build(schema)
    envelope = result['classes']['Envelope']
    assert envelope['ancestors'][0]['notes'] == ['Laboratory operation only.']
    assert envelope['slots']['channel_b']['notes'] == ['Current operation, not a future plan.']
    assert envelope['slots']['channel_b']['range_type']['notes'] == ['Schema-authored scalar convention.']
    assert 'SECRET_' not in json.dumps(result)


def test_namespace_only_change_preserves_tokens_but_changes_interpretation_context(schema):
    data, _, save = schema
    data['prefixes']['mode'] = 'https://example.invalid/device/'
    data['enums'] = {'Mode': {'permissible_values': {'ready': {'meaning': 'mode:ready'}}}}
    data['classes']['Card']['attributes']['caption']['range'] = 'Mode';save()
    first = build(schema, {'caption': 'PRIVATE'})
    data['prefixes']['mode'] = 'https://example.invalid/sample/';save()
    second = build(schema, {'caption': 'PRIVATE'})
    assert first['classes'] == second['classes']
    assert first['schema']['namespaces']['mode'] == 'https://example.invalid/device/'
    assert second['schema']['namespaces']['mode'] == 'https://example.invalid/sample/'
    assert first['schema']['default_prefix'] == second['schema']['default_prefix'] == 'ex'
    assert first['schema']['default_range'] == 'string'
    assert 'PRIVATE' not in json.dumps(first)


def test_imported_namespace_binding_is_captured_and_frozen(schema):
    data, path, save = schema
    imported = path.parent / 'meaning.yaml'
    data['imports'] = ['meaning'];save()
    imported.write_text(yaml.safe_dump({'id': 'https://example.invalid/meaning', 'name': 'meaning',
                                       'prefixes': {'meaning': 'https://example.invalid/meaning/'}}))
    snapshot = capture_schema(path, strict=True)
    initial = build(schema, snapshot=snapshot)
    assert initial['schema']['namespaces']['meaning'] == 'https://example.invalid/meaning/'
    imported.write_text(yaml.safe_dump({'id': 'https://example.invalid/meaning', 'name': 'meaning',
                                       'prefixes': {'meaning': 'https://example.invalid/other/'}}))
    assert build(schema, snapshot=snapshot) == initial
    assert build(schema)['schema']['namespaces']['meaning'] == 'https://example.invalid/other/'


def test_pair_pooling_preserves_per_record_namespace_interpretation(schema):
    data, full, core = pair_schema(schema)
    data['prefixes']['ex'] = 'https://example.invalid/full/'
    full.write_text(yaml.safe_dump(data, sort_keys=False))
    data['prefixes']['ex'] = 'https://example.invalid/core/'
    core.write_text(yaml.safe_dump(data, sort_keys=False))
    value = {'settings': [{'channel_a': 'PRIVATE'}]}
    pair = json.loads(semantics.render_pair(value, value, schema_paths=(full, core), profile=NEUTRAL))
    records = pair['records']
    assert records['original_full']['class_definition_refs']['Envelope'] == records['original_core']['class_definition_refs']['Envelope']
    assert records['original_full']['schema']['namespaces']['ex'] == 'https://example.invalid/full/'
    assert records['original_core']['schema']['namespaces']['ex'] == 'https://example.invalid/core/'
    assert 'namespace interpretations' in pair['scope']
    for role, cls, path in [('original_full', 'Dataset', full), ('original_core', 'CoreDataset', core)]:
        assert reconstruct(pair, role) == semantics.build_record(value, cls, path, profile=NEUTRAL)


@pytest.mark.parametrize('field,raw_value,context_value', [
    ('is_a', 'base_role', 'context_role'),
    ('mixins', ['base_role'], ['context_role']),
])
def test_contextual_slot_ancestry_is_not_mislabeled_as_raw_ancestry(schema, field, raw_value, context_value):
    """#2186: class slot_usage can override is_a/mixins during induction."""
    data, _, save = schema
    data['classes']['Card']['slots'] = ['selected']
    data['slots'] = {
        'base_role': {'description': 'Base operating responsibility.', 'range': 'string'},
        'context_role': {'description': 'Different contextual responsibility.', 'range': 'string'},
        'selected': {field: raw_value, 'range': 'string'},
    }
    save()
    before = build(schema, {'selected': 'PRIVATE'})
    assert before['classes']['Card']['slots']['selected']['slot_ancestors'][0]['name'] == 'base_role'
    data['classes']['Card']['slot_usage'] = {'selected': {field: context_value}};save()
    from data_sheets_schema.schema_view import shared_view
    induced = shared_view(schema[1]).induced_slot('selected', 'Card')
    assert getattr(induced, field) == context_value
    with pytest.raises(semantics.SemanticGuidanceError, match='unsupported_contextual_slot_ancestry'):
        build(schema, {'selected': 'PRIVATE'})


def test_contextual_description_with_unchanged_ancestry_still_renders(schema):
    data, _, save = schema
    data['classes']['Card']['slots'] = ['selected']
    data['slots'] = {
        'base_role': {'description': 'Base operating responsibility.', 'range': 'string'},
        'safety_role': {'description': 'Safety responsibility.', 'mixin': True},
        'selected': {'is_a': 'base_role', 'mixins': ['safety_role']},
    }
    data['classes']['Card']['slot_usage'] = {'selected': {
        'is_a': 'base_role', 'mixins': ['safety_role'], 'description': 'Explicit contextual wording.'}}
    save()
    selected = build(schema, {'selected': 'PRIVATE'})['classes']['Card']['slots']['selected']
    assert selected['description'] == 'Explicit contextual wording.'
    assert {item['name'] for item in selected['slot_ancestors']} == {'base_role', 'safety_role'}
