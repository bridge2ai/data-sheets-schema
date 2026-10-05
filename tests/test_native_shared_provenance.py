"""The in-child record cannot claim saved runtime or scientific acceptance."""
from copy import deepcopy

import pytest

from data_sheets_schema.provenance import build_record, check_record


@pytest.fixture(scope='module')
def record(tmp_path_factory):
    folder = tmp_path_factory.mktemp('native-shared-record-conformance')
    bundle = folder / 'source.txt'
    bundle.write_text('Fictional input for metadata schema validation only.\n')
    return build_record('EXAMPLE', 'claudecode_direct', 'synthetic-schema_rep1', mode='live',
        input_bundle=bundle, input_verified=True, concat_dir=folder,
        manifest=None, selected_manifest=None, outputs={}).data


def block():
    return {'protocol': 'native_shared_generation_v1',
        'selection_sha256': '1' * 64, 'execution_sha256': '2' * 64,
        'attempt_id': 'synthetic-attempt', 'session_id': 'synthetic-session',
        'assembly_sha256': '3' * 64, 'audit_sha256': '4' * 64,
        'receipt_result_sha256': '5' * 64, 'stage_completion_sha256': '6' * 64,
        'scientific_support': 'unverified evaluator declarations',
        'runtime_acceptance': 'pending independent saved readback'}


def test_absent_or_explicit_native_block_conforms_without_acceptance(record):
    assert 'native_shared_generation' not in record
    assert check_record(record) == ([], None)
    assert check_record({**record, 'native_shared_generation': block()}) == ([], None)


@pytest.mark.parametrize('mutation', ['scalar', 'missing', 'null', 'extra', 'protocol',
    'selection', 'execution', 'attempt', 'session', 'assembly', 'audit', 'receipt',
    'stage_completion', 'scientific_approval', 'runtime_approval'])
def test_native_block_refuses_missing_identity_and_premature_approval(record, mutation):
    value = block()
    if mutation == 'scalar': value = 'claimed success'
    elif mutation == 'missing': value.pop('stage_completion_sha256')
    elif mutation == 'null': value['receipt_result_sha256'] = None
    elif mutation == 'extra': value['passed'] = True
    elif mutation == 'protocol': value['protocol'] = 'shared_generation_v1'
    elif mutation == 'attempt': value['attempt_id'] = '../foreign'
    elif mutation == 'session': value['session_id'] = ''
    elif mutation == 'scientific_approval': value['scientific_support'] = 'approved'
    elif mutation == 'runtime_approval': value['runtime_acceptance'] = 'passed'
    else:
        key = 'receipt_result_sha256' if mutation == 'receipt' else mutation + '_sha256'
        value[key] = 'Z' * 64
    findings, failure = check_record({**deepcopy(record), 'native_shared_generation': value})
    assert failure is None and findings
