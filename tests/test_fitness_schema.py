"""Source-independent selected fitness instrument: no provider or study data."""
import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from types import SimpleNamespace

import pytest
import yaml

from data_sheets_schema import api_runner, fitness_schema as fs, schema_digest
from data_sheets_schema.evidence_score import LLMSlotFitnessScorer, slot_specification_snapshot
from data_sheets_schema.form_defects import FormFailure, FormSubtypeClassifier, OfflineCacheMiss, load_form_failures, VALUE_CHARS
from data_sheets_schema.profiles import NEUTRAL, Profile


@pytest.fixture
def schema(tmp_path):
    data = {
        'id': 'https://example.invalid/loom', 'name': 'loom', 'default_prefix': 'ex',
        'prefixes': {'ex': 'https://example.invalid/loom/', 'xsd': 'http://www.w3.org/2001/XMLSchema#'},
        'default_range': 'string',
        'types': {'string': {'base': 'str', 'uri': 'xsd:string'}},
        'classes': {
            'Record': {'description': 'Settings for the running loom.', 'attributes': {
                'caption': {'description': 'Visible title.'},
                'settings': {'range': 'Settings', 'multivalued': True, 'inlined_as_list': True,
                             'description': 'Mechanical operating settings.'}}},
            'Ancestor': {'description': 'Conditions during operation, never repair.', 'attributes': {
                'first': {'description': 'Maximum thread tension.', 'required': True}}},
            'Settings': {'is_a': 'Ancestor', 'description': 'Safe steady-state settings.', 'attributes': {
                'second': {'description': 'Minimum idle duration.'}}},
        }}
    path = tmp_path / 'schema.yaml'
    def save():
        path.write_text(yaml.safe_dump(data, sort_keys=False))
    save()
    return data, path, save


def captured(schema, **kwargs):
    return fs.capture('Record', schema[1], profile=kwargs.pop('profile', NEUTRAL), **kwargs)


def slot_definition(guide, cls, slot):
    return guide['slot_definitions'][guide['inline_classes'][cls]['slot_definition_refs'][slot]]


def fake_calls(monkeypatch):
    calls = []
    def call(client, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type='text', text=json.dumps({
            'fitness': 0, 'failure': 'form', 'reason': 'Synthetic form failure.',
            'subtype': 'hollow_object'}))], usage=None, stop_reason='end_turn')
    monkeypatch.setattr(api_runner, '_call_with_retry', call)
    return calls


def test_complete_declared_guidance_changes_while_legacy_nested_meaning_does_not(schema):
    data, path, save = schema
    first = captured(schema)
    old = slot_specification_snapshot('Record', path, profile=NEUTRAL)
    text = first.spec('settings')
    assert 'Maximum thread tension.' in text and 'Minimum idle duration.' in text
    assert 'Conditions during operation, never repair.' in text
    assert slot_definition(json.loads(text), 'Settings', 'first')['required'] is True
    data['classes']['Settings']['attributes']['second']['description'] = 'Other semantic obligation. ' * 200
    save()
    second = captured(schema)
    assert old[3] == slot_specification_snapshot('Record', path, profile=NEUTRAL)[3]
    assert first.specification != second.specification
    assert ('Other semantic obligation. ' * 200) in second.spec('settings')
    # The whole class is the instrument even when the changed slot isn't sent.
    assert json.loads(first.spec('caption'))['slot'] == json.loads(second.spec('caption'))['slot']


@pytest.mark.parametrize('value', [{}, [{}], 'wrong object', [{'first': 'x'}, False],
                                  {'unknown_child': 'RAW_SECRET'}, [{'second': 'RAW_SECRET'}], False, 0])
def test_malformed_values_remain_unchanged_and_never_select_guide(schema, monkeypatch, value):
    snap = captured(schema)
    calls = fake_calls(monkeypatch)
    scorer = LLMSlotFitnessScorer(client=object(), model='synthetic', class_name='Record',
        schema_path=schema[1], profile=NEUTRAL, schema_guidance=fs.GUIDANCE, schema_snapshot=snap)
    scorer(project='synthetic', slot='settings', value=value)
    message = calls[0]['messages'][0]['content']
    assert message.startswith(snap.spec('settings') + '\n\nValue supplied:')
    encoded = message.split('```yaml\n', 1)[1].split('```', 1)[0]
    assert yaml.safe_load(encoded) == {'settings': value}
    assert 'RAW_SECRET' not in snap.spec('settings')


def test_capture_is_immutable_and_prompt_does_not_recapture(schema, monkeypatch, tmp_path):
    snap = captured(schema)
    calls = fake_calls(monkeypatch)
    cache = tmp_path / 'selected_fitness.jsonl'
    scorer = LLMSlotFitnessScorer(client=object(), model='synthetic', class_name='Record', schema_path=schema[1],
        profile=NEUTRAL, schema_guidance=fs.GUIDANCE, schema_snapshot=snap, cache_path=cache)
    schema[1].write_text('invalid: [')
    monkeypatch.setattr(fs, 'capture', lambda *a, **k: pytest.fail('recaptured selected schema'))
    scorer(project='synthetic', slot='settings', value=[{}])
    assert calls[0]['messages'][0]['content'].startswith(snap.spec('settings'))
    row = json.loads(cache.read_text())
    assert row['specification'] == snap.specification and row['fitness_schema_guidance'] == fs.GUIDANCE
    assert row['class_name'] == 'Record'
    with pytest.raises(FrozenInstanceError):
        snap.specification = 'mutated'


def test_deep_enum_vocabulary_cycles_and_reference_boundary(schema, tmp_path):
    data, _, save = schema
    data['classes']['Settings']['attributes']['inner'] = {'range': 'Inner', 'inlined': True}
    data['classes']['Inner'] = {'attributes': {'leaf': {'range': 'Leaf', 'inlined': True}}}
    data['classes']['Leaf'] = {'description': 'Deep meaning.', 'attributes': {
        'mode': {'range': 'Mode'}, 'term': {'values_from': ['VOC']},
        'again': {'range': 'Settings', 'inlined': True}, 'ref': {'range': 'Reference'}}}
    data['classes']['Reference'] = {'description': 'Only the reference role.', 'attributes': {
        'id': {'identifier': True}, 'hidden': {'description': 'NOT_INLINE_CHILD'}}}
    data['enums'] = {'Mode': {'description': 'Deep enum meaning.', 'permissible_values': {
        'ready': {'description': 'Safe running mode.', 'meaning': 'ex:ready'}}}}
    save()
    pin = tmp_path / 'vocab.yaml'; pin.write_text('vocabularies:\n  VOC:\n    VOC:1: Nested term\n')
    prof = Profile('synthetic', vocabulary_pin=pin)
    snap = captured(schema, profile=prof)
    text = snap.spec('settings'); guide = json.loads(text)
    assert set(guide['inline_classes']) == {'Settings', 'Inner', 'Leaf'}
    assert all(x in text for x in ('Deep meaning.', 'Deep enum meaning.', 'Safe running mode.', 'Nested term'))
    assert 'NOT_INLINE_CHILD' not in text and 'Only the reference role.' in text
    assert slot_definition(guide, 'Leaf', 'ref')['representation'] == 'reference'
    pin.write_text(pin.read_text().replace('Nested term', 'Changed term'))
    assert captured(schema, profile=prof).specification != snap.specification
    data['prefixes']['ex'] = 'https://example.invalid/changed/'
    save()
    assert json.loads(captured(schema, profile=prof).spec('settings'))['namespaces']['ex'].endswith('changed/')


@pytest.mark.parametrize('kind', ['enum', 'type', 'slot', 'contextual_parent', 'cycle'])
def test_unsupported_schema_refused_before_provider_resolution(schema, monkeypatch, kind):
    data, _, save = schema
    if kind == 'enum':
        data['enums'] = {'Mode': {'include': [{'permissible_values': ['x']}]}}
        data['classes']['Settings']['attributes']['second']['range'] = 'Mode'
    elif kind == 'type':
        data['types']['string']['union_of'] = ['string']
    elif kind == 'slot':
        data['classes']['Settings']['attributes']['second']['any_of'] = [{'range': 'string'}]
    elif kind == 'contextual_parent':
        data['slots'] = {'base': {'description': 'Base'}, 'alternate': {'description': 'Alternate'}}
        data['classes']['Settings']['attributes']['second']['is_a'] = 'base'
        data['classes']['Settings']['slot_usage'] = {'second': {'is_a': 'alternate'}}
    else:
        data['classes']['Ancestor']['is_a'] = 'Settings'
    save()
    monkeypatch.setattr(api_runner, '_client', lambda: pytest.fail('provider resolved before schema refusal'))
    scorer = LLMSlotFitnessScorer(model='synthetic', class_name='Record', schema_path=schema[1],
                                 profile=NEUTRAL, schema_guidance=fs.GUIDANCE)
    with pytest.raises((ValueError, TypeError)):
        scorer(project='synthetic', slot='settings', value=[{}])


def test_import_closure_duplicate_keys_and_bounds(schema, tmp_path, monkeypatch):
    data, path, save = schema
    imported = tmp_path / 'base.yaml'
    base = {'id': 'https://example.invalid/base', 'name': 'base', 'classes': {'Ancestor': data['classes'].pop('Ancestor')}}
    imported.write_text(yaml.safe_dump(base)); data['imports'] = ['base']; save()
    before = captured(schema)
    assert imported in dict(before.sources)
    imported.write_text(imported.read_text().replace('Maximum thread tension.', 'Minimum thread tension.'))
    assert captured(schema).specification != before.specification
    path.write_text(path.read_text() + '\nname: repeated\n')
    with pytest.raises(ValueError, match='duplicate_schema_key'):
        captured(schema)
    save()
    monkeypatch.setattr(fs, 'MAX_SPEC_BYTES', 80)
    with pytest.raises(ValueError, match='byte_bound'):
        captured(schema)


@pytest.mark.parametrize('selected', [None, False, 1, '', 'unknown'])
def test_selector_rejects_invalid_explicit_values(selected):
    with pytest.raises(ValueError): fs.validate_selection({fs.SELECTOR: selected})
    assert fs.validate_selection({}) is None


def test_manifest_selector_applies_only_to_fitness_and_subtype():
    manifest = {fs.SELECTOR: fs.GUIDANCE, 'evaluation_jobs': [
        {'style': 'fitness', fs.SELECTOR: fs.GUIDANCE}, {'style': 'grounding'}]}
    assert fs.validate_manifest_selection(manifest) == fs.GUIDANCE
    for change in ('dropped', 'other_style', 'manifest_dropped'):
        bad = copy.deepcopy(manifest)
        if change == 'dropped': bad['evaluation_jobs'][0].pop(fs.SELECTOR)
        elif change == 'other_style': bad['evaluation_jobs'][1][fs.SELECTOR] = fs.GUIDANCE
        else: bad.pop(fs.SELECTOR)
        with pytest.raises(ValueError): fs.validate_manifest_selection(bad)


def test_selected_subtype_parent_checks_precede_memo_and_replay_is_explicit(schema, monkeypatch, tmp_path):
    snap = captured(schema); calls = fake_calls(monkeypatch)
    cache = tmp_path / 'subtype.jsonl'
    opts = dict(client=object(), model='synthetic', class_name='Record', schema_path=schema[1],
                profile=NEUTRAL, schema_guidance=fs.GUIDANCE, schema_snapshot=snap, cache_path=cache)
    failure = FormFailure('synthetic', 'settings', '[{}]', 'Missing child.', 0,
                          schema=snap.schema, specification=snap.specification,
                          schema_guidance=fs.GUIDANCE, class_name='Record')
    classifier = FormSubtypeClassifier(**opts)
    expected = classifier(failure)
    assert calls[0]['messages'][0]['content'].startswith(snap.spec('settings'))
    for bad in (replace(failure, schema_guidance=None), replace(failure, class_name='Other'),
                replace(failure, schema='other'), replace(failure, specification='other'),
                replace(failure, schema=''), replace(failure, value='x' * (VALUE_CHARS + 1))):
        with pytest.raises(ValueError): classifier(bad)
    assert len(calls) == 1
    replay = FormSubtypeClassifier(**{**opts, 'offline': True})
    assert replay(failure) == expected
    for bad in (replace(failure, reason='Different reason'), replace(failure, value='[{"first":1}]')):
        with pytest.raises(OfflineCacheMiss): replay(bad)
    assert json.loads(cache.read_text())[fs.SELECTOR] == fs.GUIDANCE
    schema[1].unlink()
    # Frozen selected replay needs no schema, but requires explicit version and class.
    frozen = FormSubtypeClassifier(model='synthetic', class_name='Record', schema_guidance=fs.GUIDANCE,
                                  schema=snap.schema, specification=snap.specification, cache_path=cache, offline=True)
    assert frozen(failure) == expected
    legacy = FormSubtypeClassifier(model='synthetic', class_name='Record', schema=snap.schema,
                                  specification=snap.specification, cache_path=cache, offline=True)
    with pytest.raises(ValueError): legacy(failure)


def test_selected_fitness_cache_carries_parent_selector_without_old_new_pooling(schema, tmp_path, monkeypatch):
    snap = captured(schema); fake_calls(monkeypatch)
    cache = tmp_path / 'example_fitness.jsonl'
    scorer = LLMSlotFitnessScorer(client=object(), model='synthetic', class_name='Record', schema_path=schema[1],
        profile=NEUTRAL, schema_guidance=fs.GUIDANCE, schema_snapshot=snap, cache_path=cache)
    scorer(project='synthetic', slot='settings', value=[{}])
    failures = load_form_failures(tmp_path)
    assert len(failures) == 1 and failures[0].schema_guidance == fs.GUIDANCE
    assert failures[0].class_name == 'Record'
    row = json.loads(cache.read_text()); row.pop(fs.SELECTOR)
    with cache.open('a') as stream: stream.write(json.dumps(row) + '\n')
    with pytest.raises(ValueError, match='different instruments'): load_form_failures(tmp_path)


def test_exact_slot_pool_reconstructs_and_never_merges_similar_declarations():
    classes = {'One': {'description': 'One role', 'slots': {'x': {'description': 'Same', 'required': True}}},
               'Two': {'description': 'Other role', 'slots': {'x': {'description': 'Same', 'required': True},
                                                            'y': {'description': 'Same', 'required': False}}}}
    pooled, definitions = fs._pool_slots(classes)
    rebuilt = {name: {**{k: v for k, v in cls.items() if k != 'slot_definition_refs'},
                      'slots': {k: definitions[ref] for k, ref in cls['slot_definition_refs'].items()}}
               for name, cls in pooled.items()}
    assert rebuilt == classes
    assert len(definitions) == 2


def test_profile_object_identity_agrees_without_rereading_captured_pin(schema, tmp_path):
    pin = tmp_path / 'vocab.yaml'; pin.write_text('vocabularies: {}\n')
    profile = Profile('custom', vocabulary_pin=pin, arm_projects={'arm': ['synthetic']})
    snap = captured(schema, profile=profile)
    same = Profile('custom', vocabulary_pin=pin, arm_projects={'arm': ['synthetic']})
    assert snap.assert_context('Record', schema[1], same) is snap
    pin.write_text('vocabularies: {UNREAD: {x: altered}}\n')
    assert snap.assert_context('Record', schema[1], same) is snap
    same.arm_projects['arm'].append('different-config')
    with pytest.raises(ValueError, match='context mismatch'):
        snap.assert_context('Record', schema[1], same)


def test_authored_scope_surface_is_complete_and_american_english(schema):
    from tests.british_sweep import british_forms
    assert british_forms(fs.SCOPE, exempt_quotes=False) == []
    assert json.loads(captured(schema).spec('settings'))['scope'] == fs.SCOPE
    assert 'slot_definition_refs' in fs.SCOPE and 'not dataset facts' in fs.SCOPE


def test_full_repository_declared_projection_is_bounded():
    # Schema declarations only; no dataset, generated output, or paid request.
    from data_sheets_schema.profiles import BRIDGE2AI
    for cls in ('Dataset', 'CoreDataset'):
        snapshot = fs.capture(cls, profile=BRIDGE2AI)
        assert snapshot.specifications
        assert max(len(text.encode()) for _, text in snapshot.specifications) <= fs.MAX_SPEC_BYTES


def test_class_constraints_are_declared_and_class_union_refuses(schema):
    data, _, save = schema
    data['classes']['Settings'].update({'abstract': True, 'unique_keys': {'pair': {'unique_key_slots': ['first', 'second']}}})
    save()
    guide = json.loads(captured(schema).spec('settings'))
    assert guide['inline_classes']['Settings']['abstract'] is True
    assert guide['inline_classes']['Settings']['unique_keys']['pair']['unique_key_slots'] == ['first', 'second']
    data['classes']['Settings']['union_of'] = ['Ancestor']
    save()
    with pytest.raises(ValueError, match='class_branch'):
        captured(schema)


def test_legacy_request_and_cache_bytes_match_pre_activation_instrument(tmp_path, monkeypatch):
    # Captured independently from bb336b7e, before the opt-in implementation.
    path = tmp_path / 'data_sheets_schema_all.yaml'
    path.write_text('id: https://example.invalid/stable\nname: stable\ndefault_range: string\ntypes:\n  string: {base: str}\nclasses:\n  Dataset:\n    attributes:\n      item: {description: Operating condition., range: Item, inlined: true}\n  Item:\n    attributes:\n      label: {description: Catalog title.}\n')
    calls = []
    def fake(client, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(type='text', text='{"fitness":0,"failure":"form","reason":"synthetic","subtype":"hollow_object"}')], usage=None, stop_reason='end_turn')
    monkeypatch.setattr(api_runner, '_call_with_retry', fake)
    fitness_cache, subtype_cache = tmp_path / 'fit.jsonl', tmp_path / 'sub.jsonl'
    scorer = LLMSlotFitnessScorer(client=object(), model='synthetic', class_name='Dataset', schema_path=path,
                                 profile=NEUTRAL, cache_path=fitness_cache)
    scorer(project='synthetic', slot='item', value=[{}])
    row = json.loads(fitness_cache.read_text())
    classifier = FormSubtypeClassifier(client=object(), model='synthetic', class_name='Dataset', schema_path=path,
                                       profile=NEUTRAL, cache_path=subtype_cache)
    classifier(FormFailure('synthetic', 'item', json.dumps([{}]), 'synthetic', 0,
                           schema=row['schema'], specification=row['specification']))
    sha = lambda data: hashlib.sha256(data).hexdigest()
    assert [sha(json.dumps(call, sort_keys=True).encode()) for call in calls] == [
        'f36075a9e36f6419a4d5b35be214919cf105b542b366c42abfb6b4325d515976',
        'ceb867b5ee313c01218f9dee211b95227420a2e4f07860e6482495090cf4a1ef']
    assert sha(fitness_cache.read_bytes()) == '94726d7021c3037c47349c35215fb5e387eddc73eb28d0ab96444eac67cb0c5f'
    assert sha(subtype_cache.read_bytes()) == 'faa4e8f70089b4de885f21b370b66e3070e98fb9751f858b78e80d27a1bc7f62'
    assert row['schema'] == '05db576091889da8dc9b6ea9a4002774'
    assert row['specification'] == '89faf5db31eb95ab16462fba08afd335c133fa9bdb48ec41f64e632626e9de2b'


def test_subtype_cli_selected_frozen_replay_preserves_explicit_class(schema, monkeypatch, tmp_path):
    from data_sheets_schema import form_defects
    snap = captured(schema); fake_calls(monkeypatch)
    fitness_cache = tmp_path / 'example_fitness.jsonl'; subtype_cache = tmp_path / 'subtype.jsonl'
    common = dict(client=object(), model='synthetic', class_name='Record', schema_path=schema[1],
                  profile=NEUTRAL, schema_guidance=fs.GUIDANCE, schema_snapshot=snap)
    LLMSlotFitnessScorer(**common, cache_path=fitness_cache)(project='synthetic', slot='settings', value=[{}])
    failure = load_form_failures(tmp_path)[0]
    FormSubtypeClassifier(**common, cache_path=subtype_cache)(failure)
    monkeypatch.setattr(form_defects, 'attribute', lambda failures, **kwargs: failures)
    monkeypatch.setattr(api_runner, '_call_with_retry', lambda *a, **k: pytest.fail('offline replay attempted a model'))
    assert form_defects.main(['--judgement-cache', str(tmp_path), '--cache', str(subtype_cache), '--offline',
                              '--fitness-schema-guidance', fs.GUIDANCE, '--class-name', 'Record',
                              '--profile', 'neutral']) == 0


def test_subtype_cache_hit_still_checks_captured_profile_object(schema, monkeypatch, tmp_path):
    profile = Profile('custom', arm_projects={'arm': ['synthetic']})
    snap = captured(schema, profile=profile); fake_calls(monkeypatch)
    classifier = FormSubtypeClassifier(client=object(), model='synthetic', class_name='Record', schema_path=schema[1],
        profile=profile, schema_guidance=fs.GUIDANCE, schema_snapshot=snap)
    failure = FormFailure('synthetic', 'settings', '[{}]', 'Synthetic', 0, schema=snap.schema,
                          specification=snap.specification, schema_guidance=fs.GUIDANCE, class_name='Record')
    classifier(failure)
    profile.arm_projects['arm'].append('changed')
    with pytest.raises(ValueError, match='context mismatch'):
        classifier(failure)
    assert classifier.memo_hits == 0


def test_relocated_schema_imports_and_profile_have_identical_selected_instrument(schema, tmp_path):
    import shutil
    data, path, save = schema
    imported = path.parent / 'base.yaml'
    imported.write_text(yaml.safe_dump({'id': 'https://example.invalid/base', 'name': 'base',
                                       'classes': {'Ancestor': data['classes'].pop('Ancestor')}}))
    data['imports'] = ['base']; save()
    pin = tmp_path / 'vocab.yaml'; pin.write_text('vocabularies: {VOC: {"VOC:1": First}}\n')
    first = fs.capture('Record', path, profile=Profile('relocated', vocabulary_pin=pin))
    other = tmp_path / 'other'; other.mkdir()
    for item in (path, imported, pin): shutil.copyfile(item, other / item.name)
    second = fs.capture('Record', other / path.name, profile=Profile('relocated', vocabulary_pin=other / pin.name))
    assert first.sources != second.sources and first.profile_sources != second.profile_sources
    assert first.instrument() == second.instrument()
    assert first.specifications == second.specifications
    assert str(tmp_path) not in first.spec('settings')
    (other / 'base.yaml').write_text((other / 'base.yaml').read_text().replace('Maximum thread tension.', 'Changed inherited meaning.'))
    changed = fs.capture('Record', other / path.name, profile=Profile('relocated', vocabulary_pin=other / pin.name))
    assert changed.specification != first.specification
    assert changed.spec('settings') != first.spec('settings')


@pytest.mark.parametrize('identifier_kind', ['inherited_type', 'enum', 'slot_ancestry'])
def test_reference_identifier_semantics_visible_in_actual_selected_prompt(schema, monkeypatch, identifier_kind):
    # #2189: a reference's identifier constrains the scalar value without
    # making the class's non-identifier child fields inline requirements.
    data, _, save = schema
    data['classes']['Record']['attributes']['contact'] = {'range': 'Contact'}
    data['classes']['ContactBase'] = {'description': 'Contact role.', 'attributes': {
        'id': {'identifier': True, 'description': 'Stable registry identifier.', 'pattern': '^REF-[0-9]+$'}}}
    data['classes']['Contact'] = {'is_a': 'ContactBase', 'attributes': {
        'private_note': {'description': 'UNRELATED_CHILD_MUST_STAY_ABSENT', 'required': True}}}
    if identifier_kind == 'inherited_type':
        data['types']['RegistryCode'] = {'typeof': 'string', 'description': 'Registry code, not a label.',
                                         'pattern': '^REF-[0-9]+$'}
        data['classes']['ContactBase']['attributes']['id']['range'] = 'RegistryCode'
    elif identifier_kind == 'enum':
        data['enums'] = {'Codes': {'description': 'Registered identifiers.', 'permissible_values': {
            'REF-1': {'description': 'Primary registry entry.', 'meaning': 'ex:primary'}}}}
        data['classes']['ContactBase']['attributes']['id']['range'] = 'Codes'
    else:
        data['slots'] = {'identity_rule': {'description': 'Identifier ancestor obligation.',
                                         'pattern': '^REF-[0-9]+$'}}
        data['classes']['ContactBase']['attributes']['id']['is_a'] = 'identity_rule'
    save()
    snap = captured(schema); guide = json.loads(snap.spec('contact'))
    assert guide['slot']['representation'] == 'reference' and guide['inline_classes'] == {}
    identifier = guide['slot']['reference_identifier']
    assert identifier['description'] == 'Stable registry identifier.'
    assert identifier['constraints']['pattern'] == '^REF-[0-9]+$'
    assert identifier['constraints']['identifier'] is True
    text = snap.spec('contact')
    assert 'UNRELATED_CHILD_MUST_STAY_ABSENT' not in text
    if identifier_kind == 'inherited_type':
        assert identifier['range_type']['description'] == 'Registry code, not a label.'
        assert identifier['range_type']['parent']['name'] == 'string'
    elif identifier_kind == 'enum':
        assert identifier['enum']['permissible_values']['REF-1']['description'] == 'Primary registry entry.'
    else:
        assert identifier['slot_ancestors'][0]['description'] == 'Identifier ancestor obligation.'
    calls = fake_calls(monkeypatch)
    LLMSlotFitnessScorer(client=object(), model='synthetic', class_name='Record', schema_path=schema[1],
        profile=NEUTRAL, schema_guidance=fs.GUIDANCE, schema_snapshot=snap)(
            project='synthetic', slot='contact', value='INVALID_RAW_REFERENCE')
    assert '^REF-[0-9]+$' in calls[0]['messages'][0]['content']
    assert 'INVALID_RAW_REFERENCE' not in text
    data['classes']['ContactBase']['attributes']['id']['pattern'] = '^ORG-[A-Z]+$'
    save(); changed = captured(schema)
    assert changed.specification != snap.specification
    assert json.loads(changed.spec('contact'))['slot']['reference_identifier']['constraints']['pattern'] == '^ORG-[A-Z]+$'
    assert 'UNRELATED_CHILD_MUST_STAY_ABSENT' not in changed.spec('contact')


@pytest.mark.parametrize('problem', ['multiple', 'multivalued', 'class_range'])
def test_ambiguous_or_structured_reference_identifier_refuses_before_provider(schema, monkeypatch, problem):
    data, _, save = schema
    data['classes']['Record']['attributes']['contact'] = {'range': 'Contact'}
    data['classes']['Contact'] = {'attributes': {'id': {'identifier': True}}}
    if problem == 'multiple':
        data['classes']['Contact']['attributes']['another'] = {'identifier': True}
    elif problem == 'multivalued':
        data['classes']['Contact']['attributes']['id']['multivalued'] = True
    else:
        data['classes']['Contact']['attributes']['id']['range'] = 'Settings'
    save()
    monkeypatch.setattr(api_runner, '_client', lambda: pytest.fail('provider resolved before schema refusal'))
    scorer = LLMSlotFitnessScorer(model='synthetic', class_name='Record', schema_path=schema[1],
                                 profile=NEUTRAL, schema_guidance=fs.GUIDANCE)
    with pytest.raises(ValueError, match='reference_identifier'):
        scorer(project='synthetic', slot='contact', value='wrong')
