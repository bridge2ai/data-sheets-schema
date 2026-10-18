"""The optional execution block conforms without opening unrelated fields."""
from copy import deepcopy

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
