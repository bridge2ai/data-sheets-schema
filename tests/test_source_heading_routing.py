"""Offline mechanics only; invented examples are not empirical routing evidence."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import zipfile

import pytest

from data_sheets_schema import source_heading_routing as routing
from semantic_exchange.generate_comprehensive_sssom import ComprehensiveSSSOMGenerator


def encoded(value):
    return json.dumps(value, ensure_ascii=False).encode()


@pytest.fixture
def inputs(tmp_path):
    schema = tmp_path / 'schema.yaml'
    schema.write_text('''id: https://example.org/schema
name: example
prefixes:
  linkml: https://w3id.org/linkml/
  d4d: https://w3id.org/bridge2ai/data-sheets-schema/
  rai: http://mlcommons.org/croissant/RAI/
imports: [linkml:types]
classes:
  Dataset:
    attributes:
      missing_data_documentation:
        range: string
      known_limitations:
        range: string
      sensitive_elements:
        range: string
      confidential_elements:
        range: string
''')
    ttl = b'''@prefix rai: <http://mlcommons.org/croissant/RAI/> .
@prefix d4d: <https://w3id.org/bridge2ai/data-sheets-schema/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
d4d:missing_data_documentation skos:exactMatch rai:dataCollectionMissingData .
d4d:known_limitations skos:broadMatch rai:dataLimitations .
d4d:sensitive_elements skos:exactMatch rai:personalSensitiveInformation .
d4d:confidential_elements skos:relatedMatch rai:personalSensitiveInformation .
'''
    recs = b'attribute\tsuggested_uri\tconfidence\n'
    ttl_path, rec_path = tmp_path / 'authority.ttl', tmp_path / 'recommendations.tsv'
    ttl_path.write_bytes(ttl)
    rec_path.write_bytes(recs)
    comprehensive = ComprehensiveSSSOMGenerator(schema, ttl_path, rec_path).render_sssom('2026-10-02').encode()
    source = {'@context': {'rai': routing.RAI}, '@graph': [{'@id': 'urn:example:one',
              'completeness': 'Some observations are not yet complete. Café 🧪',
              'rai:dataCollectionMissingData': 'Some observations are not yet complete.'},
             {'@id': 'urn:example:two', 'other': 'not the selected entity'}]}
    raw = encoded(source)
    row = {'id': 'route-1', 'heading': 'Completeness', 'profile_id': 'example-profile',
           'local_property': 'completeness', 'external_property': 'rai:dataCollectionMissingData',
           'external_uri': routing.RAI + 'dataCollectionMissingData'}
    binding = {'row_id': row['id'], 'source_sha256': routing._sha(raw), 'entity_pointer': '/@graph/0',
               'entity_id': 'urn:example:one', 'local_value_sha256': routing._sha(source['@graph'][0]['completeness'].encode()),
               'external_value_sha256': routing._sha(source['@graph'][0]['rai:dataCollectionMissingData'].encode()),
               'evidence_id': 'declared-evidence-1'}
    profile = {'format': 'source_heading_profile_v1', 'id': 'example-profile', 'authority_status': 'draft/unreviewed',
               'prefixes': {'rai': routing.RAI}, 'bindings': [binding]}
    crosswalk = {'format': 'source_heading_crosswalk_v1', 'authority_status': 'draft/unreviewed', 'rows': [row]}
    return dict(base=b'Original neutral prompt.\r\n', source=raw, profile=encoded(profile),
                crosswalk=encoded(crosswalk), scope=encoded({'source_sha256': routing._sha(raw), 'entity_pointers': ['/@graph/0']}),
                schema_path=schema, ttl=ttl, recommendations=recs, comprehensive=comprehensive)


def evidence(files):
    return json.loads(files['evidence.json'])


def revise(inputs, key, change):
    out = dict(inputs)
    value = json.loads(out[key])
    change(value)
    out[key] = encoded(value)
    return out


def updated_source(inputs, change, *, rebind=False):
    out = revise(inputs, 'source', change)
    out = revise(out, 'scope', lambda s: s.update(source_sha256=routing._sha(out['source'])))
    if rebind:
        out = revise(out, 'profile', lambda p: p['bindings'][0].update(source_sha256=routing._sha(out['source'])))
    return out


def test_full_draft_roundtrip_keeps_context_out_of_neutral_instructions(inputs, tmp_path):
    files = routing.prepare(**inputs)
    report = routing.check_files(files)
    assert report['passed']
    one = evidence(files)['records'][0]
    assert one['match_state'] == 'matched' and one['authority_status'] == 'draft/unreviewed'
    assert one['values_equal'] is False
    assert one['values']['local']['decoded_codepoint_span'] == [0, len(one['values']['local']['text'])]
    assert one['values']['local']['pointer'] == '/@graph/0/completeness'
    assert [r['slot'] for r in one['candidates']] == ['missing_data_documentation']
    assert files['base.txt'] == inputs['base']
    assert files['prompt.txt'] == inputs['base'] + routing.SEPARATOR + files['supplement.txt']
    assert files['supplement.txt'].endswith(b'\n') and not files['supplement.txt'].endswith(b'\n\n')
    assert b'urn:example:one' not in files['supplement.txt']
    assert b'Caf' not in files['supplement.txt']
    assert b'example-profile' not in files['supplement.txt']
    manifest = json.loads(files['manifest.json'])
    assert manifest['artifact_kind'] == 'prompt_text_draft'
    assert manifest['readiness'] == 'offline_draft_not_registered'
    assert manifest['execution'] == 'not_supported'
    directory = tmp_path / 'draft'
    routing.write_new(directory, files)
    assert routing.check_directory(directory) == report
    with pytest.raises(FileExistsError):
        routing.write_new(directory, files)


@pytest.mark.parametrize('base', [b'', b'prompt without newline', b'line\r\n', 'Café 🧪'.encode()])
def test_disabled_and_enabled_preserve_base_bytes_exactly(base):
    assert routing.append_prompt(base, b'unused', enabled=False) == base
    assert routing.append_prompt(base, b'new\n') == base + routing.SEPARATOR + b'new\n'


@pytest.mark.parametrize('mutation,expected', [
    ('same-heading-new-source', 'unmatched'), ('wrong-entity', 'unmatched'),
    ('wrong-id', 'unmatched'), ('outside-scope', 'unmatched'), ('sibling-property', 'unmatched'),
    ('changed-value', 'unmatched'), ('array-value', 'unsupported'), ('prefix-conflict', 'ambiguous'),
])
def test_source_identity_entity_scope_value_and_prefix_discrimination(inputs, mutation, expected):
    if mutation == 'same-heading-new-source':
        args = updated_source(inputs, lambda s: s.update(publisher='different publisher'))
    elif mutation == 'wrong-entity':
        args = revise(inputs, 'profile', lambda p: p['bindings'][0].update(entity_pointer='/@graph/1'))
    elif mutation == 'wrong-id':
        args = revise(inputs, 'profile', lambda p: p['bindings'][0].update(entity_id='urn:example:wrong'))
    elif mutation == 'outside-scope':
        args = revise(inputs, 'scope', lambda s: s.update(entity_pointers=['/@graph/1']))
    elif mutation == 'sibling-property':
        def move(s):
            s['@graph'][1]['rai:dataCollectionMissingData'] = s['@graph'][0].pop('rai:dataCollectionMissingData')
        args = updated_source(inputs, move, rebind=True)
    elif mutation == 'changed-value':
        args = updated_source(inputs, lambda s: s['@graph'][0].update(completeness='Different scientific statement'), rebind=True)
    elif mutation == 'array-value':
        args = updated_source(inputs, lambda s: s['@graph'][0].update(completeness=['not supported']), rebind=True)
    else:
        args = updated_source(inputs, lambda s: s['@context'].update(rai='https://other.example/'), rebind=True)
    assert evidence(routing.prepare(**args))['records'][0]['match_state'] == expected


def test_conflicting_duplicate_and_unknown_profile_declarations(inputs):
    profile = json.loads(inputs['profile'])
    profile['bindings'].append(copy.deepcopy(profile['bindings'][0]))
    with pytest.raises(ValueError, match='duplicate profile binding'):
        routing.prepare(**{**inputs, 'profile': encoded(profile)})
    profile['bindings'][1]['entity_id'] = 'urn:example:other'
    values = evidence(routing.prepare(**{**inputs, 'profile': encoded(profile)}))['records']
    assert [v['match_state'] for v in values] == ['ambiguous', 'ambiguous']
    assert all(not v['candidates'] for v in values)
    duplicate = json.loads(inputs['crosswalk'])
    duplicate['rows'].append(duplicate['rows'][0])
    with pytest.raises(ValueError, match='duplicate crosswalk'):
        routing.prepare(**{**inputs, 'crosswalk': encoded(duplicate)})


def test_unbound_crosswalk_no_match_and_no_route_are_explicit(inputs):
    args = revise(inputs, 'profile', lambda p: p.update(bindings=[]))
    files = routing.prepare(**args)
    assert evidence(files)['unbound_crosswalk_rows'] == ['route-1']
    assert evidence(files)['scoped_entities_without_bindings'] == ['/@graph/0']
    assert b'No supported route' in files['supplement.txt']


def test_replay_only_reads_captured_schema_and_never_original_sources(inputs, tmp_path):
    files = routing.prepare(**inputs)
    inputs['schema_path'].unlink()
    (tmp_path / 'authority.ttl').write_text('CHANGED original authority')
    (tmp_path / 'recommendations.tsv').unlink()
    with patch.object(routing, '_capture_schema', side_effect=AssertionError('reopened capture source')):
        assert routing.check_files(files)['passed']
    copied = tmp_path / 'renamed-source.json'
    copied.write_bytes(inputs['source'])
    assert copied.read_bytes() == inputs['source']  # source identity ignores filename


@pytest.mark.parametrize('name', ['base.txt', 'prompt.txt', 'supplement.txt', 'catalog.json', 'evidence.json', 'manifest.json'])
def test_checker_rejects_tampered_outputs_even_after_outer_manifest_rehash(inputs, name):
    files = routing.prepare(**inputs)
    files[name] += b' '
    if name != 'manifest.json':
        files['manifest.json'] = routing._json(routing._manifest({k: v for k, v in files.items() if k != 'manifest.json'}))
    with pytest.raises(ValueError, match='independent reconstruction'):
        routing.check_files(files)


@pytest.mark.parametrize('part', ['schema', 'ttl', 'comprehensive', 'profile', 'crosswalk', 'source', 'scope', 'code'])
def test_changed_captured_authority_or_input_cannot_keep_old_derived_artifacts(inputs, part):
    files = routing.prepare(**inputs)
    captured = json.loads(files['inputs.json'])
    if part == 'schema':
        captured['authority']['schema'][0]['content'] = routing._blob(b'name: changed\nid: https://example.org/changed\n')
    elif part in ('ttl', 'comprehensive'):
        captured['authority'][part] = routing._blob(b'changed')
    elif part == 'code':
        captured['code'][next(iter(captured['code']))] = routing._blob(b'changed')
    else:
        captured[part] = routing._blob(b'{"changed":true}')
    files['inputs.json'] = routing._json(captured)
    files['manifest.json'] = routing._json(routing._manifest({k: v for k, v in files.items() if k != 'manifest.json'}))
    with pytest.raises((ValueError, TypeError, KeyError)):
        routing.check_files(files)


def test_missing_transitive_import_is_refused_even_if_ambient_copy_exists(inputs):
    files = routing.prepare(**inputs)
    captured = json.loads(files['inputs.json'])
    assert len(captured['authority']['schema']) > 1
    captured['authority']['schema'].pop()
    files['inputs.json'] = routing._json(captured)
    with pytest.raises(ValueError, match='outside captured closure'):
        routing.check_files(files)


def test_archive_member_binding_and_original_bytes_are_preserved(inputs):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as stream:
        stream.writestr('original/source.json', inputs['source'])
    raw = archive.getvalue()
    files = routing.prepare(**inputs, archive=raw, archive_member='original/source.json')
    assert evidence(files)['archive'] == {'archive_sha256': routing._sha(raw), 'member_name': 'original/source.json', 'member_sha256': routing._sha(inputs['source'])}
    with pytest.raises(ValueError, match='member missing'):
        routing.prepare(**inputs, archive=raw, archive_member='not-present.json')
    with pytest.raises(ValueError, match='differ from original archive'):
        routing.prepare(**{**inputs, 'source': b'{}'}, archive=raw, archive_member='original/source.json')


def test_many_slot_candidates_keep_predicate_direction_and_related_strength(inputs):
    source = json.loads(inputs['source'])
    source['@graph'][0]['rai:personalSensitiveInformation'] = source['@graph'][0].pop('rai:dataCollectionMissingData')
    raw = encoded(source)
    profile = json.loads(inputs['profile']);profile['bindings'][0]['source_sha256'] = routing._sha(raw)
    crosswalk = json.loads(inputs['crosswalk']);crosswalk['rows'][0].update(external_property='rai:personalSensitiveInformation', external_uri=routing.RAI+'personalSensitiveInformation')
    scope = json.loads(inputs['scope']);scope['source_sha256'] = routing._sha(raw)
    files = routing.prepare(**{**inputs, 'source': raw, 'profile': encoded(profile), 'crosswalk': encoded(crosswalk), 'scope': encoded(scope)})
    rows = evidence(files)['records'][0]['candidates']
    assert {(r['slot'], r['predicate']) for r in rows} == {('confidential_elements','skos:relatedMatch'),('sensitive_elements','skos:exactMatch')}
    assert {r['direction'] for r in rows} == {'Dataset slot to external property'}
    assert b'confidential_elements [skos:relatedMatch]' in files['supplement.txt']
    catalog = json.loads(files['catalog.json'])
    broad = next(r for r in catalog['rows'] if r['slot'] == 'known_limitations')
    assert broad['predicate'] == 'skos:broadMatch'


def test_induced_range_and_other_owner_are_not_guessed_from_bare_slot_name(inputs, tmp_path):
    schema = inputs['schema_path']
    schema.write_text(schema.read_text() + '''  DifferentOwner:
    attributes:
      missing_data_documentation:
        range: integer
''')
    comp = ComprehensiveSSSOMGenerator(schema, tmp_path/'authority.ttl', tmp_path/'recommendations.tsv').render_sssom('2026-10-02').encode()
    files = routing.prepare(**{**inputs, 'comprehensive': comp})
    assert evidence(files)['records'][0]['match_state'] == 'unmatched'
    excluded = json.loads(files['catalog.json'])['excluded']
    assert any(r['slot'] == 'missing_data_documentation' and 'owners outside' in r['reason'] for r in excluded)


def test_invalid_utf8_duplicate_json_and_bounds_fail_before_output(inputs, tmp_path):
    for part, raw in [('base', b'\xff'), ('source', b'{"x":1,"x":2}'), ('profile', b'{"x":NaN}'), ('base', b'x'*(routing.MAX_INPUT+1))]:
        with pytest.raises((ValueError, UnicodeError)):
            routing.prepare(**{**inputs, part: raw})
    assert not (tmp_path/'output').exists()


def test_real_cli_roundtrip_and_existing_destination_refusal(inputs, tmp_path):
    argv = ['prepare']
    for key, value in inputs.items():
        if key == 'schema_path':
            argv += ['--schema', str(value)]
        else:
            path = tmp_path / (key + '.input')
            path.write_bytes(value)
            argv += ['--' + key, str(path)]
    out = tmp_path / 'out'
    assert routing.main([*argv, '--output', str(out)]) == 0
    assert routing.main(['check', str(out)]) == 0
    assert routing.main([*argv, '--output', str(out)]) == 2
    result = subprocess.run([sys.executable, '-m', 'data_sheets_schema.source_heading_routing', 'check', str(out)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['passed'] is True


def test_rendered_instructions_keep_known_project_names_and_source_prose_out(inputs):
    from tests.test_neutral_generation_schema import PATTERN
    from tests.british_sweep import british_forms
    args = updated_source(inputs, lambda s: s.update(title='CM4AI, CHORUS, VOICE_PEDIATRIC'), rebind=True)
    files = routing.prepare(**args)
    text = files['supplement.txt'].decode()
    assert PATTERN.search(text) is None
    assert not british_forms(text, exempt_quotes=False)
    captured = json.loads(files['inputs.json'])
    assert b'CM4AI' in routing._unblob(captured['source'])
    assert b'CM4AI' not in files['supplement.txt']


def test_symlink_and_hardlink_output_artifacts_are_refused(inputs, tmp_path):
    import os
    files = routing.prepare(**inputs)
    directory = tmp_path/'out';routing.write_new(directory, files)
    target = directory/'base.txt'
    preserved = tmp_path/'base-copy.txt';preserved.write_bytes(target.read_bytes())
    target.unlink();target.symlink_to(preserved)
    with pytest.raises(ValueError):routing.check_directory(directory)
    target.unlink();os.link(preserved, target)
    with pytest.raises(ValueError, match='single-link'):routing.check_directory(directory)


@pytest.mark.parametrize('context', [None, 'https://example.org/remote-context', {'rai': {'unhandled': True}}])
def test_profile_prefix_never_substitutes_for_absent_source_namespace(inputs, context):
    def change(source):
        if context is None:
            source.pop('@context')
        else:
            source['@context'] = context
    args = updated_source(inputs, change, rebind=True)
    one = evidence(routing.prepare(**args))['records'][0]
    assert one['match_state'] == 'unsupported'
    assert 'source-local prefix' in one['reason']
    assert not one['candidates']


def test_supported_local_prefix_object_and_conflicting_entity_context(inputs):
    args = updated_source(inputs, lambda s: s.update({'@context': {'rai': {'@id': routing.RAI, '@prefix': True}}}), rebind=True)
    assert evidence(routing.prepare(**args))['records'][0]['match_state'] == 'matched'
    args = updated_source(inputs, lambda s: s['@graph'][0].update({'@context': {'rai': 'https://wrong.example/'}}), rebind=True)
    assert evidence(routing.prepare(**args))['records'][0]['match_state'] == 'ambiguous'


def test_full_property_uri_needs_no_inferred_source_prefix(inputs):
    source = json.loads(inputs['source']); source.pop('@context')
    external = routing.RAI + 'dataCollectionMissingData'
    source['@graph'][0][external] = source['@graph'][0].pop('rai:dataCollectionMissingData')
    raw = encoded(source)
    profile = json.loads(inputs['profile']); profile['prefixes'] = {}; profile['bindings'][0]['source_sha256'] = routing._sha(raw)
    crosswalk = json.loads(inputs['crosswalk']); crosswalk['rows'][0]['external_property'] = external
    scope = json.loads(inputs['scope']); scope['source_sha256'] = routing._sha(raw)
    files = routing.prepare(**{**inputs, 'source': raw, 'profile': encoded(profile), 'crosswalk': encoded(crosswalk), 'scope': encoded(scope)})
    one = evidence(files)['records'][0]
    assert one['match_state'] == 'matched'
    assert one['source_prefix_basis'] == 'source property key is the explicit full URI'


@pytest.mark.parametrize('case,expected', [
    ('entity-reset', 'unsupported'), ('ancestor-reset', 'unsupported'),
    ('ancestor-override', 'ambiguous'), ('remote-after-local', 'unsupported'),
    ('remote-before-local', 'unsupported'), ('reset-then-local', 'unsupported'),
    ('scoped-property', 'unsupported'), ('scoped-type', 'unsupported'),
    ('context-import', 'unsupported'), ('propagation', 'unsupported'),
    ('unknown-operation', 'unsupported'), ('exact-term-override', 'unsupported'),
    ('keyword-alias', 'unsupported'), ('ordered-local', 'matched'),
    ('ancestor-local', 'matched'), ('root-entity', 'matched'),
    ('sibling-reset-and-override', 'matched'), ('escaped-pointer', 'matched'),
])
def test_complete_selected_context_path_governs_compact_namespace(inputs, case, expected):
    source = json.loads(inputs['source'])
    entity = source['@graph'][0]
    pointer = '/@graph/0'
    local = {'rai': routing.RAI}
    if case == 'entity-reset':
        entity['@context'] = None
    elif case in ('ancestor-reset', 'ancestor-override', 'ancestor-local', 'escaped-pointer'):
        key = 'enclosing/~scope' if case == 'escaped-pointer' else 'container'
        context = (None if case == 'ancestor-reset' else
                   {'rai': 'https://different.example/'} if case == 'ancestor-override' else local)
        source = {'@context': local, key: {'@context': context, 'children': [entity]}}
        if case == 'ancestor-local':
            source.pop('@context')
        pointer = '/' + key.replace('~', '~0').replace('/', '~1') + '/children/0'
    elif case in ('remote-after-local', 'remote-before-local', 'reset-then-local'):
        remote = 'https://unknown.example/context.jsonld'
        source['@context'] = ([local, remote] if case == 'remote-after-local' else
                              [remote, local] if case == 'remote-before-local' else [None, local])
    elif case in ('scoped-property', 'scoped-type'):
        term = '@graph' if case == 'scoped-property' else 'SelectedType'
        source['@context'][term] = {'@id': 'https://example.org/term', '@context': {'rai': 'https://different.example/'}}
        if case == 'scoped-type':
            entity['@type'] = term
    elif case in ('context-import', 'propagation', 'unknown-operation'):
        key, value = {'context-import': ('@import', 'https://unknown.example/context'),
                      'propagation': ('@propagate', False), 'unknown-operation': ('@future', True)}[case]
        source['@context'][key] = value
    elif case == 'exact-term-override':
        source['@context']['rai:dataCollectionMissingData'] = 'https://different.example/property'
    elif case == 'keyword-alias':
        source['@context']['kind'] = '@type'
    elif case == 'ordered-local':
        source['@context'] = [local, {'@vocab': 'https://schema.org/'},
                              {'rai': {'@id': routing.RAI, '@prefix': True}}]
    elif case == 'root-entity':
        source = {**entity, '@context': local}
        pointer = ''
    else:
        source['@graph'][1]['@context'] = [None, {'rai': 'https://different.example/'}]
    raw = encoded(source)
    profile = json.loads(inputs['profile'])
    profile['bindings'][0].update(source_sha256=routing._sha(raw), entity_pointer=pointer)
    args = {**inputs, 'source': raw, 'profile': encoded(profile),
            'scope': encoded({'source_sha256': routing._sha(raw), 'entity_pointers': [pointer]})}
    files = routing.prepare(**args)
    assert routing.check_files(files)['passed']
    one = evidence(files)['records'][0]
    assert one['match_state'] == expected, one
    assert bool(one['candidates']) == (expected == 'matched')
    assert (b'Dataset.missing_data_documentation' in files['supplement.txt']) == (expected == 'matched')
    assert routing._unblob(json.loads(files['inputs.json'])['source']) == raw
    if expected == 'unsupported':
        assert 'source-local prefix' in one['reason']


@pytest.mark.parametrize('context', [None, ['https://unknown.example/context', {'rai': 'https://different.example/'}]])
def test_explicit_full_uri_is_literal_binding_despite_unsupported_compact_context(inputs, context):
    source = json.loads(inputs['source'])
    external = routing.RAI + 'dataCollectionMissingData'
    entity = source['@graph'][0]
    entity[external] = entity.pop('rai:dataCollectionMissingData')
    entity['@context'] = context
    raw = encoded(source)
    profile = json.loads(inputs['profile'])
    profile['prefixes'] = {}
    profile['bindings'][0]['source_sha256'] = routing._sha(raw)
    crosswalk = json.loads(inputs['crosswalk'])
    crosswalk['rows'][0]['external_property'] = external
    files = routing.prepare(**{**inputs, 'source': raw, 'profile': encoded(profile), 'crosswalk': encoded(crosswalk),
        'scope': encoded({'source_sha256': routing._sha(raw), 'entity_pointers': ['/@graph/0']})})
    assert routing.check_files(files)['passed']
    one = evidence(files)['records'][0]
    assert one['match_state'] == 'matched'
    assert one['source_prefix_basis'] == 'source property key is the explicit full URI'


def test_authority_newline_handling_matches_existing_compiler_but_preserves_bytes(inputs):
    original = routing.prepare(**inputs)
    changed = {**inputs, **{name: inputs[name].replace(b'\n', b'\r\n') for name in ('ttl','recommendations','comprehensive')}}
    made = routing.prepare(**changed)
    assert made['catalog.json'] == original['catalog.json']
    assert made['prompt.txt'] == original['prompt.txt']
    captured = json.loads(made['inputs.json'])
    assert routing._unblob(captured['authority']['comprehensive']) == changed['comprehensive']
    assert json.loads(made['manifest.json'])['request_sha256'] != json.loads(original['manifest.json'])['request_sha256']


def test_source_budget_is_explicit_and_independent_of_smaller_prompt_budget(inputs):
    args = updated_source(inputs, lambda s: s.update(padding='x' * routing.MAX_INPUT), rebind=True)
    # Source capture, parsing, and reconstruction all use the source bound.
    files = routing.prepare(**args)
    assert routing.check_files(files)['passed']
    assert len(args['source']) > routing.MAX_INPUT
    with pytest.raises(ValueError, match='bound'):
        routing.append_prompt(b'x' * (routing.MAX_INPUT + 1), b'policy')


def test_source_graph_node_budget_does_not_borrow_smaller_record_limit():
    raw = encoded({'values': [None] * 221116})
    assert len(routing._parse_source(raw)['values']) == 221116
    with pytest.raises(ValueError, match='traversal limits'):
        routing._parse_source(encoded({'values': [None] * routing.MAX_SOURCE_NODES}))
    with pytest.raises(ValueError):
        routing._parse_source(b'{"same":1,"same":2}')
    with pytest.raises(ValueError):
        routing._parse_source(b'{"number":NaN}')
