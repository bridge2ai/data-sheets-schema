"""Native recorder declarations conform without implying saved acceptance."""
from copy import deepcopy

import pytest

from data_sheets_schema import provenance
from tests.test_record_required_values import record as minimal_record


def native_block():
    return {
        'protocol': 'native_shared_generation_v1',
        'selection_sha256': 'a' * 64,
        'execution_sha256': 'b' * 64,
        'attempt_id': 'software-test',
        'session_id': 'software-test-session',
        'assembly_sha256': 'c' * 64,
        'audit_sha256': 'd' * 64,
        'receipt_result_sha256': 'e' * 64,
        'stage_completion_sha256': 'f' * 64,
        'scientific_support': 'unverified evaluator declarations',
        'runtime_acceptance': 'pending independent saved readback',
    }


def test_record_allows_exact_native_declaration_without_runtime_acceptance():
    record = minimal_record()
    record['native_shared_generation'] = native_block()
    assert provenance.check_record(record) == ([], None)


@pytest.mark.parametrize('field,value', [
    ('protocol', 'shared_generation_v1'),
    ('execution_sha256', 'short'),
    ('scientific_support', 'accepted'),
    ('runtime_acceptance', 'passed'),
])
def test_record_refuses_misleading_native_completion_declarations(field, value):
    record = minimal_record()
    record['native_shared_generation'] = deepcopy(native_block())
    record['native_shared_generation'][field] = value
    findings, failure = provenance.check_record(record)
    assert failure is None
    assert findings
