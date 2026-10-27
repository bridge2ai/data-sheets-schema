"""The optional execution block conforms without opening unrelated fields."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema.provenance import build_record, check_record


@pytest.fixture(scope='module')
def record(tmp_path_factory):
    folder = tmp_path_factory.mktemp('shared-record-conformance')
    bundle = folder / 'source.txt'
    bundle.write_text('Fictional input for metadata schema validation only.\n')
    return build_record('EXAMPLE', 'claudecode_api', 'synthetic-schema_rep1', mode='live',
        input_bundle=bundle, input_verified=True, concat_dir=folder,
        manifest=None, selected_manifest=None, outputs={}).data


def block():
    return {'protocol': 'shared_generation_v1', 'generation_id': '1' * 32,
        'assembly_sha256': '2' * 64, 'audit_sha256': '3' * 64,
        'acceptance': {'passed': True, 'scientific_support': 'unverified'},
        'authority': {'scope': 'Synthetic schema-shape fixture, not an actual runtime acceptance.'},
        'scientific_support': 'unverified evaluator declarations'}


def test_default_absence_and_explicit_block_conform_while_gate_stays_closed(record):
    assert 'shared_generation' not in record
    assert check_record(record) == ([], None)
    selected = {**record, 'shared_generation': block()}
    assert check_record(selected) == ([], None)
    for bad in ({**selected, 'unexpected_execution': {}},
                {key: value for key, value in record.items() if key != 'model'}):
        findings, failure = check_record(bad)
        assert failure is None and findings


@pytest.mark.parametrize('mutation', ['scalar', 'missing', 'null', 'extra', 'protocol', 'generation',
    'assembly', 'audit', 'approval'])
def test_shared_block_requires_its_exact_identity_and_unverified_status(record, mutation):
    value = block()
    if mutation == 'scalar': value = 'claimed success'
    elif mutation == 'missing': value.pop('acceptance')
    elif mutation == 'null': value['authority'] = None
    elif mutation == 'extra': value['passed'] = True
    elif mutation == 'protocol': value['protocol'] = 'shared_generation_v2'
    elif mutation == 'generation': value['generation_id'] = 'foreign'
    elif mutation == 'assembly': value['assembly_sha256'] = '2' * 63
    elif mutation == 'audit': value['audit_sha256'] = 'Z' * 64
    else: value['scientific_support'] = 'approved'
    findings, failure = check_record({**deepcopy(record), 'shared_generation': value})
    assert failure is None and findings


@pytest.fixture
def bc1_block(monkeypatch):
    """Use the completion writer and real selection wrapper, with no API run.

    The independently reconstructed outcome and captured authority are stubs:
    this checks provenance conformance, not runtime or scientific acceptance.
    The public BC1 pipeline separately exercises reconstruction and completion.
    """
    from data_sheets_schema import bc1_runtime as runtime, bc1_selection as selection

    registration = {'selection': {'protocol': 'shared_generation_v1'},
                    'bounded_carry': selection.registration_block()}
    outcome = runtime.Outcome('Synthetic checked audit.', '2' * 64,
                              {'passed': True, 'scientific_support': 'unverified'})
    monkeypatch.setattr(runtime, 'recover', lambda *a, **k: outcome)
    monkeypatch.setattr(runtime.sg, 'capture',
                        lambda spec: SimpleNamespace(document=lambda: registration))
    monkeypatch.setattr(runtime.sg, 'identity', lambda spec: block()['authority'])
    monkeypatch.setattr(runtime.ledger, 'generation_id', lambda spec: '1' * 32)
    return runtime.completion_check(object())


@pytest.mark.parametrize('fan_in', [1, 2])
def test_bc1_completion_writer_conforms_without_changing_legacy_modes(record, bc1_block, fan_in):
    bc1_block['bounded_carry']['fan_in'] = fan_in
    routing = {**block(), 'protocol': 'shared_generation_v2',
               'routing': {'scope': 'Synthetic routing schema-shape fixture.'}}
    for value in (block(), routing, bc1_block):
        assert check_record({**record, 'shared_generation': value}) == ([], None)


@pytest.mark.parametrize('mutation', [
    'protocol_v2', 'protocol_unknown', 'routing', 'extra',
    'bounded_scalar', 'bounded_null', 'bounded_extra',
    'version_missing', 'version_null', 'version_zero', 'version_two', 'version_bool',
    'fan_in_missing', 'fan_in_null', 'fan_in_zero', 'fan_in_three', 'fan_in_fraction',
    'fan_in_bool', 'contract_missing', 'contract_null',
    'generation_missing', 'assembly_missing', 'audit_missing',
    'acceptance_missing', 'authority_missing', 'support_missing',
])
def test_bc1_completion_rejects_wrong_modes_and_incomplete_identity(record, bc1_block, mutation):
    if mutation == 'protocol_v2': bc1_block['protocol'] = 'shared_generation_v2'
    elif mutation == 'protocol_unknown': bc1_block['protocol'] = 'bc1_claimed_success'
    elif mutation == 'routing': bc1_block['routing'] = {}
    elif mutation == 'extra': bc1_block['claimed_success'] = True
    elif mutation == 'bounded_scalar': bc1_block['bounded_carry'] = 'registered'
    elif mutation == 'bounded_null': bc1_block['bounded_carry'] = None
    elif mutation == 'bounded_extra': bc1_block['bounded_carry']['approved'] = True
    elif mutation in ('generation_missing', 'assembly_missing', 'audit_missing',
                      'acceptance_missing', 'authority_missing', 'support_missing'):
        key = {'generation': 'generation_id', 'assembly': 'assembly_sha256',
               'audit': 'audit_sha256', 'support': 'scientific_support'}.get(
                   mutation.removesuffix('_missing'), mutation.removesuffix('_missing'))
        bc1_block.pop(key)
    else:
        key, change = mutation.rsplit('_', 1)
        if change == 'missing': bc1_block['bounded_carry'].pop(key)
        else:
            bc1_block['bounded_carry'][key] = {
                'null': None, 'zero': 0, 'two': 2, 'three': 3,
                'fraction': 1.5, 'bool': True}[change]
    findings, failure = check_record({**record, 'shared_generation': bc1_block})
    assert failure is None and findings


def test_bc1_variant_requires_selection_without_disallowing_legacy_v1(record, bc1_block):
    from jsonschema.validators import validator_for
    from data_sheets_schema.record_schema import compile_record_schema

    schema = compile_record_schema(Path('src/data_sheets_schema/schema/d4d_generation_record.yaml'))
    validator = validator_for(schema)(schema)
    selected = {'$ref': '#/$defs/SharedGenerationBoundedCarryExecution'}
    assert list(validator.descend(bc1_block, selected)) == []
    bc1_block.pop('bounded_carry')
    assert list(validator.descend(bc1_block, selected))
    # Without the selection this has the unchanged legacy v1 shape; the union
    # cannot infer a missing BC1 selection from fields shared by both modes.
    assert check_record({**record, 'shared_generation': bc1_block}) == ([], None)


@pytest.mark.parametrize('protocol, extras', [
    ('shared_generation_v1', {'routing': {}}),
    ('shared_generation_v2', {}),
])
def test_shared_completion_modes_keep_their_required_selection(record, protocol, extras):
    value = {**block(), 'protocol': protocol, **extras}
    findings, failure = check_record({**record, 'shared_generation': value})
    assert failure is None and findings
