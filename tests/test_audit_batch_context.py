"""Generic scientific-context preservation; no provider or actual audit data."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from data_sheets_schema import audit_batch_context as context, audit_batches, chunking
from data_sheets_schema.profiles import NEUTRAL


@pytest.fixture
def staged(tmp_path):
    schema = {
        'id': 'https://example.invalid/display', 'name': 'display',
        'prefixes': {'ex': 'https://example.invalid/display/', 'xsd': 'http://www.w3.org/2001/XMLSchema#'},
        'default_prefix': 'ex', 'default_range': 'string',
        'types': {'string': {'base': 'str', 'uri': 'xsd:string'}},
        'classes': {
            'Dataset': {'description': 'Complete operating card.', 'attributes': {
                'caption': {'description': 'Wording displayed on the sign.'},
                'settings': {'range': 'Setting', 'inlined_as_list': True, 'multivalued': True,
                             'description': 'Normal operating settings, not calibration.'},
                'required_hint': {'required': True, 'description': 'Supervisor acknowledgement.'},
                'unused': {'description': 'Source-supported supplemental information when available.'}}},
            'CoreDataset': {'is_a': 'Dataset', 'description': 'Projected operating card.'},
            'BaseSetting': {'description': 'Electrical operation only.', 'attributes': {
                'channel_a': {'description': 'Upper current in amperes.'}}},
            'Setting': {'is_a': 'BaseSetting', 'description': 'Continuous use, not a calibration test.',
                        'attributes': {'channel_b': {'description': 'Cooldown duration in seconds.'}},
                        'slot_usage': {'channel_a': {'description': 'Peak current for this controller.'}}},
        }}
    record = {'caption': 'PRIVATE_VALUE_CAPTION', 'settings': [{'channel_a': 'PRIVATE_A', 'channel_b': 'PRIVATE_B'}]}
    files = {role: tmp_path / (role + '.yaml') for role in context.REQUIRED_INPUTS}
    files['full_schema'].write_text(yaml.safe_dump(schema, sort_keys=False))
    files['core_schema'].write_text(yaml.safe_dump(schema, sort_keys=False))
    files['original_full'].write_text(yaml.safe_dump(record, sort_keys=False))
    files['original_core'].write_text(yaml.safe_dump(record, sort_keys=False))
    bundle = 'FILE: manual.txt\nPATH: evidence/manual.txt\nScope: prototype only.\nThe display has two channels.\nFILE: supplement.txt\nPATH: evidence/supplement.txt\nSecond source context remains available.\n'
    files['bundle'].write_text(bundle)
    manifest = chunking.manifest_from_bytes(bundle.encode(), files['bundle'].name)
    files['chunk_manifest'].write_text(yaml.safe_dump(manifest, sort_keys=False))
    files['source_manifest'].write_text(yaml.safe_dump({'profile': 'neutral', 'source_priority': {2: ['documentation']},
        'curation_note': 'HELDOUT_SOURCE_NOTE', 'projects': {'example': [
            {'id': 'manual', 'source_type': 'documentation', 'processed_file': 'manual.txt'},
            {'id': 'supplement', 'source_type': 'documentation', 'processed_file': 'supplement.txt'}]}}))
    files['protocol'].write_text('Exact registered protocol placeholder; provided in persistent system.\n')
    plan = audit_batches.make_plan(files['original_full'].read_text(), max_paths=2)
    return {'files': files, 'plan': plan, 'schema': schema, 'record': record, 'tmp': tmp_path}


def render(s, worker=0):
    return context.render_worker_context(inputs=s['files'], profile=NEUTRAL, project='example',
                                        plan=s['plan'], worker_id=s['plan']['workers'][worker]['id'])


def save_schema(s):
    for role in ['full_schema', 'core_schema']:
        s['files'][role].write_text(yaml.safe_dump(s['schema'], sort_keys=False))


def repin_record(s, record):
    for role in ['original_full', 'original_core']:
        s['files'][role].write_text(yaml.safe_dump(record, sort_keys=False))
    s['plan'] = audit_batches.make_plan(s['files']['original_full'].read_text(), max_paths=8)


def proposals(s):
    paths, data, rows = {}, {}, {}
    for worker in s['plan']['workers']:
        selected = [row for row in s['plan']['inventory']['values'] if row['path'] in worker['paths']]
        values = []
        for row in selected:
            value = {'path': row['path'], 'claims': [{'text': row['text'], 'verdict': 'supported',
                'attributed_to': [], 'claim_status': 'fact', 'source_status': 'fact',
                'evidence': [{'source': 'manual.txt', 'chunk': 'c001', 'quote': 'The display has two channels.'}],
                'reason': 'Synthetic proposed judgment, not checked source support.'}]}
            values.append(value)
            row_path = s['tmp'] / (audit_batches.object_sha256(value) + '.json')
            row_path.write_bytes(audit_batches.canonical_bytes(value));rows[row['path']] = row_path
        value = {'findings': [{'severity': 'low', 'record': 'full', 'slot': 'unused',
                    'issue': 'Synthetic source-supported omission for integration consideration.',
                    'evidence': [{'source': 'supplement.txt', 'chunk': 'c002', 'quote': 'Second source context remains available.'}]}],
                 'summary': 'Synthetic worker proposal.', 'source_review': {
                     'artifact': 'original_full', 'sha256': s['plan']['original_full_sha256'], 'values': values}}
        raw = audit_batches.canonical_bytes(value)
        path = s['tmp'] / (worker['id'] + '.json');path.write_bytes(raw)
        paths[worker['id']] = path;data[worker['id']] = raw
    return paths, audit_batches.build_index(s['plan'], data), rows


def test_complete_sources_originals_and_scoped_return_roster(staged):
    result = json.loads(render(staged))
    assert result['original_full'] == staged['files']['original_full'].read_text()
    assert result['original_core'] == staged['files']['original_core'].read_text()
    assert result['complete_source_bundle'] == staged['files']['bundle'].read_text()
    assert 'Second source context remains available.' in result['complete_source_bundle']
    assert result['assignment']['paths'] == ['/caption']
    assert [r['path'] for r in result['assigned_inventory']['values']] == ['/caption']
    assert len(result['inventory_path_index']) == 3
    assert 'HELDOUT_SOURCE_NOTE' not in render(staged)
    assert 'Exact registered protocol placeholder' not in render(staged)  # persistent once, no duplicate
    assert result['input_authority']['protocol']['sha256'] == hashlib.sha256(staged['files']['protocol'].read_bytes()).hexdigest()
    assert result['profile_vocabulary_authority'] is None


def test_scoped_semantics_keep_ancestors_required_siblings_and_full_core(staged):
    result = json.loads(render(staged, 1))
    full = result['schema_guidance']['original_full']
    assert full['classes']['Setting']['slots']['channel_a']['description'] == 'Peak current for this controller.'
    assert full['classes']['Setting']['ancestors'][0]['description'] == 'Electrical operation only.'
    assert full['classes']['Dataset']['slots']['required_hint']['required']
    assert 'PRIVATE_' not in json.dumps(result['schema_guidance'])
    assert full['original_record_binding']['sha256'] == staged['plan']['original_full_sha256']
    assert result['schema_guidance']['original_core']['schema']['root_class'] == 'CoreDataset'
    assert {f['name'] for f in full['all_root_fields']} == {'caption', 'settings', 'required_hint', 'unused'}
    assert 'Setting' in full['all_schema_classes']


def test_unassigned_nested_meaning_not_upfront_but_still_discoverable(staged):
    staged['schema']['classes']['Setting']['attributes']['channel_b']['description'] = 'X' * 600 + 'UNASSIGNED_DEEP_MEANING'
    save_schema(staged)
    first = json.loads(render(staged))
    second = json.loads(render(staged, 1))
    assert 'UNASSIGNED_DEEP_MEANING' not in json.dumps(first['schema_guidance'])
    assert 'UNASSIGNED_DEEP_MEANING' in json.dumps(second['schema_guidance'])
    assert first['input_authority']['full_schema']['path'] == str(staged['files']['full_schema'])
    assert 'settings' in {f['name'] for f in first['schema_guidance']['original_full']['all_root_fields']}


def test_schema_meaning_change_changes_selected_guidance_without_truncation(staged):
    first = json.loads(render(staged, 1))['schema_guidance']
    long = 'Complete declaration. ' * 40 + 'TAIL_OBLIGATION'
    staged['schema']['classes']['Setting']['attributes']['channel_b']['description'] = long
    save_schema(staged)
    second = json.loads(render(staged, 1))['schema_guidance']
    assert second != first
    assert second['original_full']['classes']['Setting']['slots']['channel_b']['description'] == long


def test_unknown_and_bad_shape_values_remain_exact_audit_targets(staged):
    record = {'caption': {'wrong': 'PRIVATE_WRONG'}, 'unknown': 'PRIVATE_UNKNOWN', 'settings': ['PRIVATE_BAD_MEMBER']}
    repin_record(staged, record)
    result = json.loads(render(staged))
    assert result['original_full'] == staged['files']['original_full'].read_text()
    assert 'PRIVATE_WRONG' in result['original_full'] and 'PRIVATE_UNKNOWN' in result['original_full']
    marked = result['schema_guidance']['original_full']['unprojected_structure']
    assert {r['kind'] for r in marked} == {'unknown_schema_slot', 'scalar_or_reference_has_object', 'inline_object_must_be_mapping'}
    assert 'PRIVATE_' not in json.dumps(result['schema_guidance'])
    assert {r['path'] for r in result['assigned_inventory']['values']} == {'/caption/wrong', '/unknown', '/settings/0'}


def test_empty_original_still_has_omission_scope(staged):
    repin_record(staged, {})
    result = json.loads(render(staged))
    assert result['assignment']['paths'] == []
    assert result['schema_guidance']['original_full']['all_root_fields']
    base = context.render_integration_base_context(inputs=staged['files'], profile='neutral', project='example', plan=staged['plan'])
    assert 'identify supported information omitted' in base
    assert 'optional fields alone are not defects' in base


def test_reference_identifier_meaning_is_included_without_inline_expansion(staged):
    staged['schema']['classes']['Dataset']['attributes']['caption'] = {'range': 'Part'}
    staged['schema']['classes']['Part'] = {'description': 'Identified external component.', 'attributes': {
        'serial': {'identifier': True, 'pattern': '^PART:[0-9]+$', 'description': 'Component serial identifier.'},
        'detail': {'description': 'UNRELATED_INLINE_DETAIL'}}}
    save_schema(staged)
    first = json.loads(render(staged))['schema_guidance']['original_full']['classes']['Dataset']['slots']['caption']
    assert first['representation'] == 'reference'
    assert first['reference_identifier']['constraints']['pattern'] == '^PART:[0-9]+$'
    assert 'UNRELATED_INLINE_DETAIL' not in json.dumps(first)
    staged['schema']['classes']['Part']['attributes']['serial']['pattern'] = '^ITEM:[0-9]+$';save_schema(staged)
    second = json.loads(render(staged))['schema_guidance']['original_full']['classes']['Dataset']['slots']['caption']
    assert first != second and second['reference_identifier']['constraints']['pattern'] == '^ITEM:[0-9]+$'


def test_ambiguous_schema_branch_is_not_guessed(staged):
    staged['schema']['classes']['Dataset']['attributes']['caption'] = {'any_of': [{'range': 'string'}, {'range': 'Setting'}]}
    save_schema(staged)
    with pytest.raises(ValueError, match='unsupported_schema_range_branch'):render(staged)


@pytest.mark.parametrize('damage', ['missing_source', 'foreign_role', 'plan', 'chunks', 'profile', 'worker'])
def test_registration_context_errors_fail_closed(staged, damage):
    if damage == 'missing_source': staged['files'].pop('bundle')
    elif damage == 'foreign_role': staged['files']['held_out_review'] = staged['files']['protocol']
    elif damage == 'plan': staged['plan']['original_full_sha256'] = '0' * 64
    elif damage == 'chunks': staged['files']['bundle'].write_text('Different exact source bytes')
    elif damage == 'profile':
        with pytest.raises(ValueError):context.render_worker_context(inputs=staged['files'], profile=None, project='example', plan=staged['plan'], worker_id=staged['plan']['workers'][0]['id'])
        return
    elif damage == 'worker':
        with pytest.raises(ValueError, match='unknown_registered_worker'):context.render_worker_context(inputs=staged['files'], profile=NEUTRAL, project='example', plan=staged['plan'], worker_id='worker_foreign')
        return
    with pytest.raises(ValueError):render(staged)


def test_source_inventory_must_match_original_plan(staged):
    path = staged['tmp'] / 'inventory.json';path.write_text(json.dumps(staged['plan']['inventory']))
    staged['files']['source_inventory'] = path
    render(staged)
    bad = deepcopy(staged['plan']['inventory']);bad['values'][0]['text'] = 'Different literal original value'
    path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match='source_inventory_plan_mismatch'):render(staged)


def test_historical_parent_text_and_ambient_files_never_enter_context(staged):
    old = staged['tmp'] / 'old.md';old.write_text('HELDOUT_PARENT_PAYLOAD')
    staged['files']['parent_instruction'] = old
    ignored = staged['tmp'] / '.local_drafts';ignored.mkdir();(ignored / 'review.json').write_text('HELDOUT_NEIGHBOR_PAYLOAD')
    text = render(staged)
    assert 'HELDOUT_PARENT_PAYLOAD' not in text and 'HELDOUT_NEIGHBOR_PAYLOAD' not in text
    assert str(old) in text  # pinned provenance locator only


def test_deterministic_global_prefix_and_complete_findings(staged):
    artifacts, index, rows = proposals(staged)
    args = dict(inputs=staged['files'], profile=NEUTRAL, project='example', plan=staged['plan'])
    base = context.render_integration_base_context(**args)
    text = context.render_integration_context(**args, worker_index=index, worker_artifacts=artifacts, row_artifacts=rows)
    assert text.startswith(base + '\n# Immutable worker proposals:')
    assert text == context.render_integration_context(**args, worker_index=index, worker_artifacts=artifacts, row_artifacts=rows)
    appendix = json.loads(text[len(base):].split('\n', 2)[2])
    assert len(appendix['complete_worker_findings']) == len(index['findings'])
    assert all('Synthetic source-supported omission' in r['finding']['issue'] for r in appendix['complete_worker_findings'])
    assert all('row_artifact' in row for row in appendix['rows'])
    assert 'canonical row view' in base and 'complete old source-review row' in base
    assert 'including every row you will retain unchanged' in base
    assert 'including rows retained unchanged' in appendix['required_read_rule']
    assert 'explicit retention decision' in appendix['required_read_rule']
    assert 'every dropped/replaced worker concern' in base
    assert all('claims' not in row for row in appendix['rows'])  # index is navigation, not substitute judgments


@pytest.mark.parametrize('damage', ['worker', 'index', 'row', 'missing_row', 'no_rows'])
def test_integration_refuses_stale_or_foreign_navigation(staged, damage):
    artifacts, index, rows = proposals(staged)
    if damage == 'worker':next(iter(artifacts.values())).write_bytes(b'{}')
    elif damage == 'index':index['rows'][0]['sha256'] = '0' * 64
    elif damage == 'row':next(iter(rows.values())).write_bytes(b'{}')
    elif damage == 'missing_row':rows.pop(next(iter(rows)))
    else:rows = None
    with pytest.raises(ValueError):context.render_integration_context(inputs=staged['files'], profile=NEUTRAL,
        project='example', plan=staged['plan'], worker_index=index, worker_artifacts=artifacts, row_artifacts=rows)


def test_context_bound_refuses_instead_of_truncating(staged, monkeypatch):
    monkeypatch.setattr(context, 'MAX_CONTEXT_BYTES', 100)
    with pytest.raises(ValueError, match='scientific_context_byte_bound'):render(staged)


def test_no_provider_or_registered_source_validator(staged, monkeypatch):
    from data_sheets_schema import evidence_assertions, source_review
    def forbidden(*a, **kw):raise AssertionError('scientific validator must not run')
    monkeypatch.setattr(source_review, 'check', forbidden)
    monkeypatch.setattr(evidence_assertions, 'check_files', forbidden)
    monkeypatch.setattr(evidence_assertions, 'check_assertions', forbidden)
    assert render(staged)
    artifacts, index, rows = proposals(staged)
    assert context.render_integration_context(inputs=staged['files'], profile=NEUTRAL, project='example',
        plan=staged['plan'], worker_index=index, worker_artifacts=artifacts, row_artifacts=rows)


def test_protocol_seven_preserves_science_and_leaves_six_unchanged():
    prompts = Path(__file__).resolve().parents[1] / 'src/download/prompts'
    six = (prompts / 'evidence_protocol_v6.md').read_bytes()
    assert hashlib.sha256(six).hexdigest() == 'a75d30e2830e2fcf25079dab8ca3809e5e6e7f8b77db58f23913fc9aa416414b'
    seven = (prompts / 'evidence_protocol_v7.md').read_text()
    tail = six.decode().split('### Relationships and document attribution', 1)[1]
    tail = tail.replace('### Required source review (v6 /', '### Required source review (v7 /')
    assert seven.split('### Relationships and document attribution', 1)[1] == tail
    assert 'at most two immutable grammar drafts **per child**' in seven
    assert 'one separately registered native integration' in seven
    assert 'single terminal full-original source/evidence validator once' in seven
    assert 'Do not call canonical serialization a scientific repair' in seven
    assert 'successfully Read every complete immutable worker row' in seven
    assert 'including every row retained unchanged' in seven
    assert 'retaining unread rows or regenerating them' in seven
    assert 'integration-delta shape specified here specialize the Phase 3 complete-audit' in seven
    assert 'new model request is admitted while the terminal result is pending, failed,' in seven
    assert "permits only the model's terminal status response" in seven
    assert 'classification, repair, reassembly, validation retry or new child is permitted.' in seven


def test_explicit_profile_vocabulary_and_changed_meaning(staged):
    from data_sheets_schema.profiles import Profile
    pin = staged['tmp'] / 'terms.yaml'
    pin.write_text('vocabularies:\n  EX:\n    EX:1: running\n')
    staged['schema']['classes']['Dataset']['attributes']['caption']['values_from'] = ['EX']
    save_schema(staged)
    profile = Profile('synthetic', vocabulary_pin=pin)
    args = dict(inputs=staged['files'], profile=profile, project='example', plan=staged['plan'],
                worker_id=staged['plan']['workers'][0]['id'])
    one = json.loads(context.render_worker_context(**args))
    assert one['profile_vocabulary_authority'] == {'path': str(pin), 'bytes': len(pin.read_bytes()),
                                                 'sha256': hashlib.sha256(pin.read_bytes()).hexdigest()}
    meaning = one['schema_guidance']['original_full']['classes']['Dataset']['slots']['caption']['vocabulary']
    assert meaning['pinned_terms']['EX'] == {'EX:1': 'running'}
    pin.write_text('vocabularies:\n  EX:\n    EX:1: stopped\n')
    two = json.loads(context.render_worker_context(**args))
    assert one['profile_vocabulary_sha256'] != two['profile_vocabulary_sha256']
    assert two['schema_guidance']['original_full']['classes']['Dataset']['slots']['caption']['vocabulary']['pinned_terms']['EX']['EX:1'] == 'stopped'


def test_vocabulary_locator_cannot_change_even_to_identical_bytes(staged, monkeypatch):
    from data_sheets_schema import schema_digest
    from data_sheets_schema.profiles import Profile
    first, second = staged['tmp'] / 'first-vocabulary.yaml', staged['tmp'] / 'second-vocabulary.yaml'
    first.write_text('vocabularies: {}\n');second.write_bytes(first.read_bytes())
    profile = Profile('synthetic', vocabulary_pin=first, tracks_digest_pin=True)
    monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN', first)
    original = context._schema_guidance

    def changing(*args, **kwargs):
        result = original(*args, **kwargs)
        monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN', second)
        return result

    monkeypatch.setattr(context, '_schema_guidance', changing)
    with pytest.raises(ValueError, match='authority_changed_during_context_render'):
        context.render_worker_context(inputs=staged['files'], profile=profile, project='example',
            plan=staged['plan'], worker_id=staged['plan']['workers'][0]['id'])


def test_imported_meanings_and_authority_change_together(staged):
    base = staged['schema']['classes'].pop('BaseSetting')
    imp = staged['tmp'] / 'common.yaml'
    imported = {'id': 'https://example.invalid/common', 'name': 'common', 'classes': {'BaseSetting': base}}
    imp.write_text(yaml.safe_dump(imported))
    staged['schema']['imports'] = ['common'];save_schema(staged)
    first = json.loads(render(staged, 1))['schema_guidance']['original_full']
    assert str(imp) in {s['path'] for s in first['schema']['sources']}
    imported['classes']['BaseSetting']['description'] = 'Changed inherited operating condition.'
    imp.write_text(yaml.safe_dump(imported))
    second = json.loads(render(staged, 1))['schema_guidance']['original_full']
    assert first['schema']['sources'] != second['schema']['sources']
    assert second['classes']['Setting']['ancestors'][0]['description'] == 'Changed inherited operating condition.'


@pytest.mark.parametrize('point', ['between_snapshots', 'between_guidance', 'after_guidance'])
def test_shared_schema_import_change_during_pair_render_is_rejected(staged, monkeypatch, point):
    base = staged['schema']['classes'].pop('BaseSetting')
    imp = staged['tmp'] / 'common.yaml'
    imported = {'id': 'https://example.invalid/common', 'name': 'common', 'classes': {'BaseSetting': base}}
    imp.write_text(yaml.safe_dump(imported))
    staged['schema']['imports'] = ['common'];save_schema(staged)
    target = 'capture_schema' if point == 'between_snapshots' else '_schema_guidance'
    original = getattr(context, target)
    count = 0

    def changing(*args, **kwargs):
        nonlocal count
        result = original(*args, **kwargs)
        count += 1
        if count == (2 if point == 'after_guidance' else 1):
            imported['classes']['BaseSetting']['description'] = 'A DIFFERENT inherited meaning.'
            imp.write_text(yaml.safe_dump(imported))
        return result

    monkeypatch.setattr(context, target, changing)
    with pytest.raises(ValueError, match='schema_changed_during_context_render'):
        render(staged, 1)


def test_empty_integration_still_requires_explicit_empty_row_view_roster(staged):
    repin_record(staged, {})
    artifacts, index, rows = proposals(staged)
    args = dict(inputs=staged['files'], profile=NEUTRAL, project='example', plan=staged['plan'],
                worker_index=index, worker_artifacts=artifacts)
    assert rows == {}
    with pytest.raises(ValueError, match='row_artifact_roster_mismatch'):
        context.render_integration_context(**args)
    assert context.render_integration_context(**args, row_artifacts={})


@pytest.mark.parametrize('damage', ['duplicate', 'boolean_limit', 'wrong_bundle_name'])
def test_manifest_declaration_ambiguity_is_rejected(staged, damage):
    path = staged['files']['chunk_manifest']
    if damage == 'duplicate':path.write_text(path.read_text() + 'chunk_count: 999\n')
    else:
        value = yaml.safe_load(path.read_text())
        if damage == 'boolean_limit':value['rule']['max_lines'] = True
        else:value['bundle'] = 'different-source.txt'
        path.write_text(yaml.safe_dump(value))
    with pytest.raises(ValueError):render(staged)


def test_named_checkout_profile_keeps_absolute_vocabulary_authority(staged, monkeypatch):
    from data_sheets_schema import profiles, schema_digest
    monkeypatch.chdir(Path(context.__file__).resolve().parents[2])
    monkeypatch.setattr(schema_digest, 'VOCABULARY_PIN', profiles.STUDY_VOCABULARY_PIN)
    profile = profiles.profile_named('bridge2ai')
    assert not profile.pin_path.is_absolute()  # resource resolver preserves checkout spelling
    pin = profile.pin_path.absolute()
    args = dict(inputs=staged['files'], profile='bridge2ai', project='example', plan=staged['plan'])
    worker = json.loads(context.render_worker_context(**args, worker_id=staged['plan']['workers'][0]['id']))
    integration = json.loads(context.render_integration_base_context(**args))
    expected = {'path': str(pin), 'bytes': len(pin.read_bytes()),
                'sha256': hashlib.sha256(pin.read_bytes()).hexdigest()}
    for result in (worker, integration):
        assert result['profile_vocabulary_authority'] == expected
        assert result['profile_vocabulary_sha256'] == expected['sha256']
        assert result['complete_source_bundle'] == staged['files']['bundle'].read_text()


@pytest.mark.parametrize('alias_kind', ['file', 'parent'])
def test_relative_profile_pin_still_rejects_symlink_alias(staged, monkeypatch, alias_kind):
    from data_sheets_schema.profiles import Profile
    monkeypatch.chdir(staged['tmp'])
    real = staged['tmp'] / 'real'
    real.mkdir()
    (real / 'terms.yaml').write_text('vocabularies: {}\n')
    if alias_kind == 'file':
        Path('terms.yaml').symlink_to(real / 'terms.yaml')
        pin = Path('terms.yaml')
    else:
        Path('alias').symlink_to(real, target_is_directory=True)
        pin = Path('alias/terms.yaml')
    profile = Profile('synthetic', vocabulary_pin=pin)
    with pytest.raises(ValueError, match='input_requires_canonical_regular_file'):
        context.render_worker_context(inputs=staged['files'], profile=profile, project='example',
            plan=staged['plan'], worker_id=staged['plan']['workers'][0]['id'])
