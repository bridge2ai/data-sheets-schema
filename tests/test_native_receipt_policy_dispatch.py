"""Mixed native/API declarations refuse before receipt I/O; offline controls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema import native_shared_contract as native_contract
from data_sheets_schema import native_shared_selection as native_selection
from data_sheets_schema import receipt_completion_policy as cp, receipts
from tests.test_evidence_generation_gate import specification
from tests.test_receipt_completion_policy import declaration as api_v1_declaration, disk
from tests.test_shared_generation_selection import (
    offline, registration_for, selected_spec as shared_spec,
)
from tests.test_source_heading_runtime_api import draft_files, selected_spec as routed_spec
from tests.test_native_shared_receipt_readers import captured
from tests.test_native_shared_selection import declaration


REFUSAL = 'receipt registration and selected version differ'


def native_identity():
    body = {'kind': native_contract.KINDS['receipt_policy'], 'version': 1,
        'registration_id': 'synthetic-mixed-family-refusal', 'condition': native_contract.CONDITION,
        'runtime_policy_sha256': native_selection.RECEIPT_POLICY_SHA256,
        'receipt_instrument_version': 4,
        'coverage_floor': {'state': 'pending', 'mode': 'diagnostic_pilot'}}
    raw = json.dumps(body, sort_keys=True, separators=(',', ':')).encode('utf-8')
    assert native_contract.parse_receipt_policy(raw, native_selection.RECEIPT_POLICY_SHA256) == body
    identity = {'sha256': hashlib.sha256(raw).hexdigest(), 'raw_json': raw.decode('utf-8')}
    assert cp._identity(identity) == body and 'format' not in body
    return identity


@pytest.fixture(params=[1, 2, 3])
def complete_api_declaration(request, tmp_path):
    if request.param == 1:
        spec = api_v1_declaration()
    else:
        if request.param == 2:
            base = specification(tmp_path)
            selected = shared_spec(base, registration_for(base))
        else:
            selected = routed_spec(tmp_path, request.getfixturevalue('draft_files'))
        selected.bind_api_header_values(api._model_settings(selected.condition))
        spec = selected.render_spec()
    # The mixed-family failure must not be explained by absent later fields.
    assert cp.select_policy(spec)['registration']['format'] == (
        cp.FORMAT if request.param == 1 else f'receipt_completion_registration_v{request.param}')
    return spec


@pytest.mark.parametrize('authority', ['explicit', 'recorded', 'both'])
def test_native_policy_under_complete_api_declaration_is_valueerror(
        complete_api_declaration, authority):
    valid = complete_api_declaration
    expected = cp.select_policy(valid)
    bad = deepcopy(valid)
    bad['receipt_completion_registration'] = native_identity()
    record = {'prompts': {'request': {'spec': bad}}}
    kwargs = ({'render_spec': bad} if authority == 'explicit' else
              {'record': record} if authority == 'recorded' else
              {'render_spec': bad, 'record': record})
    with pytest.raises(ValueError, match='^' + REFUSAL + '$'):
        cp.select_policy(**kwargs)
    assert cp.select_policy(valid) == expected


@pytest.mark.parametrize('authority', ['explicit', 'recorded'])
def test_public_block_returns_structured_refusal_before_receipt_reads(
        complete_api_declaration, disk, monkeypatch, authority):
    bad = deepcopy(complete_api_declaration)
    bad['receipt_completion_registration'] = native_identity()
    def forbidden(*args, **kwargs):
        pytest.fail('mixed policy was not refused before receipt artifact I/O')
    protected = {Path(disk[name]) for name in ('full_path', 'receipt', 'bundle', 'manifest')}
    for name in ('open', 'read_bytes', 'read_text', 'stat', 'lstat', 'exists', 'is_file'):
        original = getattr(Path, name)
        def checked(path, *args, _original=original, **kwargs):
            if path in protected:
                return forbidden()
            return _original(path, *args, **kwargs)
        monkeypatch.setattr(Path, name, checked)
    options = ({'receipt_render_spec': bad} if authority == 'explicit' else
               {'snapshot_record': {'prompts': {'request': {'spec': bad}}}})
    result = receipts.block_for(**disk, **options)
    assert result['expected'] is True and result['checked'] is False
    assert result['reason'] == 'receipt policy selection refused: ' + REFUSAL
    assert cp.BLOCK_KEY not in result and 'coverage_floor' not in result


def test_complete_native_declaration_keeps_its_separate_valid_route(declaration):
    capture = captured(declaration)
    native = cp.native_render_declaration(capture)
    selected = cp.select_policy(native)
    assert selected['registration']['kind'] == native_contract.KINDS['receipt_policy']
    assert 'format' not in selected['registration']
    assert selected['identity']['sha256'] == capture.receipt_policy.pin.sha256
    assert cp.select_policy(record={'prompts': {'request': {'spec': native}}}) == selected
    assert cp.select_policy({'native_shared_generation_version': 0}) is None
