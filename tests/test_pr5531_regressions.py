"""Offline 3.2.0 review regressions (PR5531, D98/D99)."""
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from data_sheets_schema import api_runner as api, bc1_context as bc
from data_sheets_schema import bc1_audit as audit, bc1_selection as selected
from data_sheets_schema import bc1_registration as reg, schema_digest, profiles
from data_sheets_schema.schema_snapshot import capture_schema
from tests.test_bc1_context import fixture  # noqa: F401
from tests.test_bc1_registration import sizing_fixture, context_fixture  # noqa: F401
from scripts import build_api_registrations as builder

SCHEMA = Path(__file__).resolve().parents[1] / 'src/data_sheets_schema/schema'


def test_scalar_permission_normalises_and_linkml_validates(tmp_path):
    original = '# preserved provenance\nlicense_and_use_terms:\n  data_use_permission: general_research_use\n'
    result = api.normalise_record_text(original)
    assert result.startswith('# preserved provenance\n')
    assert yaml.safe_load(result)['license_and_use_terms']['data_use_permission'] == ['general_research_use']
    record = tmp_path / 'permission.yaml'
    # Validate the affected class directly: unrelated Dataset requirements are
    # outside this scalar-to-list migration regression.
    record.write_text(yaml.safe_dump(yaml.safe_load(result)['license_and_use_terms']))
    command = [str(Path(sys.executable).parent / 'linkml-validate'), '-s',
               str(SCHEMA / 'data_sheets_schema_all.yaml'), '-C', 'LicenseAndUseTerms', str(record)]
    checked = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    record.write_text('data_use_permission: general_research_use\n')
    rejected = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert rejected.returncode != 0


@pytest.mark.parametrize('slot', ['data_use_permission', 'credit_roles', 'conforms_to_standard'])
def test_enum_multivalued_slots_are_discovered(slot):
    assert slot in api._multivalued_slots()


@pytest.mark.parametrize('profile', [profiles.NEUTRAL, profiles.BRIDGE2AI])
def test_nested_enum_digest_states_list_cardinality(profile):
    text = schema_digest.digest_text('Dataset', profile=profile)
    assert '`data_use_permission` [many] accepts only:' in text
    assert '`credit_roles` [many] accepts only:' in text
    assert '`conforms_to_standard` [many] accepts only:' in text


def test_selection_drives_legacy_policy_and_audit_acceptance(fixture):
    selection, inputs = fixture
    selection['bounded_carry'] = selected.registration_block(fan_in=2)
    selection['bounded_carry']['contract']['context'] = bc.contract_identity(1)
    schema = yaml.safe_load(inputs['schema_path'].read_bytes())
    schema['classes']['Instance']['attributes']['data_topic']['annotations'] = {'d4d:termSources': 'GO, GO'}
    inputs['schema_path'].write_text(yaml.safe_dump(schema))
    snapshot = capture_schema(inputs['schema_path'], strict=True)
    selection['inputs']['full_schema'] = bc._schema_pin(snapshot)
    policy = bc.derive_term_policy(selection=selection, context_raw=inputs['context'], schema_snapshot=snapshot)
    assert policy['format'] == bc.LEGACY_FORMAT
    assert policy['external_terms']['Instance']['data_topic']['sources'] == ['GO']
    audit._selection(selection, 2)
    for value in ('GO:abc\u200ddef', 'GO:abc\x00def'):
        bc.validate_term_value(value, policy=policy, cls='Instance', field='data_topic')
    with pytest.raises(ValueError, match='source syntax'):
        bc.derive_term_policy(selection=selection, context_raw=inputs['context'],
                              schema_snapshot=snapshot, contract_version=2)


def test_legacy_annotation_without_value_uses_original_fallback():
    catalog = {'classes': {'Instance': {'slots': {'data_topic': {
        'definition': {'annotations': {'d4d:termSources': {'tag': 'd4d:termSources'}}}}}}}}
    result = bc._sources(catalog, contract_version=1)
    assert result['Instance']['data_topic']['sources'] == sorted(bc.FALLBACK['Instance', 'data_topic'])
    with pytest.raises(ValueError, match='explicit source names'):
        bc._sources(catalog, contract_version=2)


def test_legacy_curie_helper_invalidates_derivation_cache(monkeypatch):
    before = audit._cache_dependency_token()
    assert before is not None
    monkeypatch.setattr(bc, '_curie_prefixes', lambda source: ('DIFFERENT',))
    assert audit._cache_dependency_token() != before


@pytest.mark.parametrize('character', ['\x00', '\u200d', '\u2028', '\u2029'])
def test_v2_still_rejects_control_and_separator_characters(fixture, character):
    selection, inputs = fixture
    policy = bc.derive_term_policy(selection=selection, context_raw=inputs['context'],
                                  schema_snapshot=inputs['schema_snapshot'])
    with pytest.raises(ValueError, match='controlled term'):
        bc.validate_term_value('GO:abc' + character + 'def', policy=policy, cls='Instance', field='data_topic')


@pytest.mark.parametrize('base', ['urn:example:', 'ftp://example.test/', 'https://example.test'])
def test_iri_base_does_not_choose_owner_scheme_policy(base):
    result = bc._validate_identifier_form_entries([
        {'id': 'example', 'label': 'Example', 'curies': [], 'iri_bases': [base]}],
        declared_labels=['Example'], cls='Instance', slot='data_topic')
    assert result['iri_prefixes'] == [base]


@pytest.mark.parametrize('term', ['EDAM:format_1915', 'mediatypes:text/csv'])
def test_real_schema_neutral_sizing_and_audit(sizing_fixture, term, tmp_path):
    registration, files, inputs = sizing_fixture
    snapshot = capture_schema(SCHEMA / 'data_sheets_schema_all.yaml', strict=True)
    core = capture_schema(SCHEMA / 'data_sheets_schema_core_all.yaml', strict=True)
    registration['inputs']['full_schema'] = bc._schema_pin(snapshot)
    registration['inputs']['core_schema'] = bc._schema_pin(core)
    record = ('# D4D Datasheet for KIDS_FIRST Dataset\n# Arm: de novo\n'
              'id: example:dataset\nname: Example\ninstances:\n'
              f'- data_substrate: {term}\n  data_topic: GO:0008150\n')
    files.full.write_text(record)
    files.core.write_text('# D4D Datasheet for KIDS_FIRST Dataset\n# Arm: de novo\nid: example:dataset\nname: Example\n')
    for path in (files.full, files.core):
        path.write_text(path.read_text().replace('# Arm: de novo', '# Arm: ' + builder.ARMS['baseline'][0]))
    record = files.full.read_text()
    limits = {k: registration['audit_limits'][k] for k in builder.PARTITION_KEYS}
    limits['aggregate_input_tokens'] = 40_000_000
    actual, outputs, result = builder.prepare_registration('KIDS_FIRST', 'real-schema-sizing',
        arm='baseline', bounded_carry_version=1, profile_name='neutral', audit_limits=limits,
        source_manifest_path=registration['inputs']['source_manifest']['path'],
        context_path=registration['inputs']['context']['path'],
        bundle_path=registration['inputs']['bundle']['path'],
        chunk_manifest_path=registration['inputs']['chunk_manifest']['path'],
        sizing_record=builder.SizingRecord(files.full, files.core, files.receipt, files.receipt_result),
        registration_path=tmp_path / 'real-registration.json')
    assert actual['inputs']['profile']['name'] == 'neutral'
    assert actual['inputs']['full_schema'] == bc._schema_pin(snapshot)
    assert outputs
    reg.check_sizing_record(actual, result)
    assert result['plan_workers'] > 0
    assert any(row['stage'].get('stage_id') == 'final' for row in result['rows'])
    assert all(row['wire_bytes'] > 0 for row in result['rows'])
    assert files.full.read_text() == record
