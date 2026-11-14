"""D109 native final receipt gates: diagnostic pending is not coverage acceptance.

Receipt assessments use rc.check on real fixture bytes and real native policy
capture. Carrier mutation cases intentionally bypass frozen construction to
exercise revalidation. Recorder tests isolate routing: the run, phase/evidence
results, assessment delivery and provenance result are supplied stubs. The
recorder function and final receipt-floor helper execute unchanged. These tests
make no claim of observed history, public completion, native execution or launch.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import canary
from data_sheets_schema import native_shared_capture_orchestration as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_gates as gates
from data_sheets_schema import native_shared_receipts as native_receipts
from data_sheets_schema import native_shared_selection as native_selection
from data_sheets_schema import receipt_completion_policy as policy
from data_sheets_schema import receipts as rc
from tests.test_native_shared_selection import declaration, pin, save  # noqa: F401
from tests.test_receipts import FULL, _manifest_and_texts, _receipt


PENDING = {'state': 'pending', 'mode': 'diagnostic_pilot'}


@pytest.fixture
def receipt_case(declaration):
    """Capture a real native policy after constructing a real v4 assessment."""
    def build(*, mutation=None, threshold_delta=None, empty=False):
        manifest, texts = _manifest_and_texts()
        receipt = _receipt(manifest['bundle_md5'])
        # The extra genuine unreceipted leaf leaves room for threshold tests
        # above and below actual coverage without inventing coverage counters.
        full = {} if empty else {**deepcopy(FULL), 'license': 'Unreceipted synthetic licence'}
        if mutation == 'chunks':
            receipt['chunks'].pop()
        elif mutation == 'snippets':
            receipt['chunks'][1]['extracted'][0]['snippet'] = 'Invented passage entirely absent from these sources.'
        elif mutation == 'vacuous':
            for chunk in receipt['chunks']:
                chunk.pop('extracted', None)
                chunk.update(status='nothing_relevant', reason='Synthetic nonextracting receipt.')
        elif mutation == 'addressing':
            receipt['chunks'][1]['extracted'].extend([
                {'slot': 'funders[9].grant_id', 'snippet': 'Grant OT2OD032644'},
                {'slot': 'funders[10].grant_id', 'snippet': 'Grant OT2OD032644'},
            ])
        elif mutation == 'finding':
            receipt['chunks'][1]['extracted'].append({
                'slot': 'totally.fabricated[3].slot', 'snippet': 'Grant OT2OD032644'})
        elif mutation is not None:
            raise ValueError('unknown receipt mutation')
        block = rc.check(receipt, manifest, texts, full, manifest['bundle_md5'],
                         full, instrument_version=4)
        floor = dict(PENDING)
        if threshold_delta is not None:
            covered, eligible = (block['slots']['with_receipt_at_receipt'],
                                 block['slots']['receiptable_at_receipt'])
            if empty:
                floor = {'state': 'registered', 'numerator': 1, 'denominator': 1,
                         'basis': 'receipted_part'}
            else:
                assert 0 < covered < eligible
                floor = {'state': 'registered', 'numerator': covered + threshold_delta,
                         'denominator': eligible, 'basis': 'receipted_part'}
        path = Path(declaration['receipt_policy']['path'])
        registered = c.strict_json(path.read_bytes())
        registered['coverage_floor'] = floor
        raw = c.canonical(registered)
        path.write_bytes(raw)
        declaration['receipt_policy'] = pin(path, raw)
        save(declaration)
        selected = native_selection.capture(declaration['registration_path'])
        chosen = policy.select_policy(policy.native_render_declaration(selected))
        block.update(expected=True, native_receipt_stage='final', final_stage_complete=True,
                     coverage_floor=native_receipts.floor(block['slots'], selected),
                     native_stage_completion_history_sha256='a' * 64,
                     native_shared_receipt_policy=dict(chosen['identity']))
        block[policy.BLOCK_KEY] = policy.block_identity(chosen)
        return selected, block
    return build


def test_pending_clean_gate_retains_false_diagnostic_and_does_not_mutate(receipt_case):
    selected, block = receipt_case()
    before = deepcopy(block)
    generic = canary.receipt_floors(block)
    assert generic['registered receipt coverage'] == 1
    assert not any(value for key, value in generic.items() if key != 'registered receipt coverage')
    floors = native_receipts.final_receipt_floors(block, selected)
    assert floors == {key: value for key, value in generic.items() if key != 'registered receipt coverage'}
    assert block == before
    assert block['coverage_floor']['state'] == 'pending'
    assert block['coverage_floor']['passed'] is False
    # Returned gate diagnostics cannot mutate the assessment or later verdict.
    floors['receipt findings'] = 900
    assert native_receipts.final_receipt_floors(block, selected)['receipt findings'] == 0
    assert block == before


@pytest.mark.parametrize('mutation,expected_floor', [
    ('chunks', 'chunks unreviewed'),
    ('snippets', 'snippets unverified'),
    ('vacuous', 'receipts vacuous'),
    ('addressing', 'addressing slips over tolerance'),
    ('finding', 'receipt findings'),
])
def test_pending_keeps_every_real_structural_floor(receipt_case, mutation, expected_floor):
    selected, block = receipt_case(mutation=mutation)
    generic = canary.receipt_floors(block)
    assert generic[expected_floor] > 0  # Proves this mutation reaches its named floor.
    floors = native_receipts.final_receipt_floors(block, selected)
    assert floors == {key: value for key, value in generic.items() if key != 'registered receipt coverage'}
    assert floors[expected_floor] > 0
    assert block['coverage_floor']['state'] == 'pending'
    assert block['coverage_floor']['passed'] is False


@pytest.mark.parametrize('threshold_delta,passed', [(-1, True), (0, True), (1, False)])
def test_registered_fraction_retains_exact_boundary_and_all_generic_floors(receipt_case, threshold_delta, passed):
    selected, block = receipt_case(threshold_delta=threshold_delta)
    assert block['coverage_floor']['passed'] is passed
    assert native_receipts.final_receipt_floors(block, selected) == canary.receipt_floors(block)
    assert native_receipts.final_receipt_floors(block, selected)['registered receipt coverage'] == int(not passed)


def test_registered_empty_scope_keeps_unmeasurable_failure(receipt_case):
    selected, block = receipt_case(threshold_delta=0, empty=True)
    assert block['coverage_floor']['state'] == 'not_applicable'
    assert block['coverage_floor']['passed'] is False
    result = native_receipts.final_receipt_floors(block, selected)
    assert result == canary.receipt_floors(block)
    assert result['registered receipt coverage'] == 1


@pytest.mark.parametrize('field,value', [
    ('expected', False), ('expected', 1),
    ('checked', False), ('checked', 1),
    ('final_stage_complete', False), ('final_stage_complete', 1),
    ('native_receipt_stage', 'phase1_initial'),
    ('native_stage_completion_history_sha256', None),
    ('native_stage_completion_history_sha256', 'a' * 63),
])
def test_final_gate_refuses_unready_or_untyped_assessment(receipt_case, field, value):
    selected, block = receipt_case()
    block[field] = value
    with pytest.raises(ValueError):
        native_receipts.final_receipt_floors(block, selected)


def test_final_gate_requires_completion_history_identity(receipt_case):
    selected, block = receipt_case()
    del block['native_stage_completion_history_sha256']
    with pytest.raises(ValueError):
        native_receipts.final_receipt_floors(block, selected)


@pytest.mark.parametrize('field,value', [
    ('passed', True), ('passed', 0), ('state', 'passed'),
    ('registration_sha256', '0' * 64), ('receiptable', False),
])
def test_pending_gate_refuses_forged_coverage_including_false_equals_zero(receipt_case, field, value):
    selected, block = receipt_case()
    block['coverage_floor'][field] = value
    with pytest.raises(ValueError):
        native_receipts.final_receipt_floors(block, selected)


def test_registered_floor_cannot_be_demoted_by_a_stored_pending_marker(receipt_case):
    selected, block = receipt_case(threshold_delta=1)
    assert canary.receipt_floors(block)['registered receipt coverage'] == 1
    block['coverage_floor'].update(state='pending', passed=False, floor=dict(PENDING))
    with pytest.raises(ValueError):
        native_receipts.final_receipt_floors(block, selected)


@pytest.mark.parametrize('field,value', [
    ('with_receipt', True), ('with_receipt', -1), ('receiptable', False),
    ('addressing_slips_count', -1), ('populated', 0),
])
def test_pending_gate_recomputes_and_rejects_invalid_counters(receipt_case, field, value):
    selected, block = receipt_case()
    block['slots'][field] = value
    with pytest.raises(ValueError):
        native_receipts.final_receipt_floors(block, selected)


@pytest.mark.parametrize('mutation', [
    'policy-missing', 'policy-hash', 'policy-runtime-hash', 'native-missing',
    'native-hash', 'native-whitespace', 'policy-mode',
])
def test_native_gate_revalidates_both_policy_identities(receipt_case, mutation):
    selected, block = receipt_case()
    if mutation == 'policy-missing':
        del block[policy.BLOCK_KEY]
    elif mutation == 'policy-hash':
        block[policy.BLOCK_KEY]['registration']['sha256'] = '0' * 64
    elif mutation == 'policy-runtime-hash':
        block[policy.BLOCK_KEY]['runtime_policy_sha256'] = '0' * 64
    elif mutation == 'native-missing':
        del block['native_shared_receipt_policy']
    elif mutation == 'native-hash':
        block['native_shared_receipt_policy']['sha256'] = '0' * 64
    elif mutation == 'native-whitespace':
        block['native_shared_receipt_policy']['raw_json'] += '\n'
    elif mutation == 'policy-mode':
        document = c.strict_json(block[policy.BLOCK_KEY]['registration']['raw_json'].encode())
        document['coverage_floor']['mode'] = 'invented_coverage_bypass'
        raw = c.canonical(document)
        block[policy.BLOCK_KEY]['registration'] = {'sha256': c.sha(raw), 'raw_json': raw.decode()}
    with pytest.raises(ValueError):
        native_receipts.final_receipt_floors(block, selected)


@pytest.mark.parametrize('replacement', ['none', 'dictionary', 'duck'])
def test_native_gate_requires_the_actual_capture_type(receipt_case, replacement):
    selected, block = receipt_case()
    replacement = {'none': None, 'dictionary': selected.document(),
                   'duck': SimpleNamespace(**vars(selected))}[replacement]
    with pytest.raises(ValueError):
        native_receipts.final_receipt_floors(block, replacement)


@pytest.mark.parametrize('member', ['receipt_policy', 'registration'])
def test_native_gate_refuses_capture_bytes_changed_after_construction(receipt_case, member):
    selected, block = receipt_case()
    selected = deepcopy(selected)
    artifact = getattr(selected, member)
    object.__setattr__(artifact, 'raw', artifact.raw + b'\n')
    with pytest.raises(ValueError):
        native_receipts.final_receipt_floors(block, selected)


@pytest.mark.parametrize('mutation', [None, 'chunks', 'snippets', 'vacuous'])
def test_recorder_routes_through_real_native_floor_and_preserves_structural_refusals(
        receipt_case, monkeypatch, mutation):
    selected, block = receipt_case(mutation=mutation)
    paths = {'full': '/synthetic/final-full.yaml', 'receipt': '/synthetic/original-receipt.yaml'}
    run = SimpleNamespace(selection=selected, spec=SimpleNamespace(_agentic_artifact_paths=paths))
    calls = []
    required = {'draft', 'final_evidence', 'final_source_inventory', 'final_receipts', 'final_scope',
                'derive_final_core', 'core_schema', 'pair', 'full_schema', 'full_terms', 'audit_evidence'}
    result_document = {'routing_only': 'Invented provenance delivery; no actual recorder acceptance.'}

    def load(path):
        assert path == selected.registration.pin.path
        calls.append('load')
        return run

    def phase(current):
        assert current is run
        calls.append('phase')
        return {'passed': True, 'current_checks': sorted(required)}, None

    def evidence(current):
        assert current is run
        calls.append('evidence')
        return {'checked': True, 'findings': []}

    def assessment(current, *, full_path, receipt_path):
        assert current is run
        assert (full_path, receipt_path) == (paths['full'], paths['receipt'])
        calls.append('assessment')
        return block, None, None

    actual_floors = native_receipts.final_receipt_floors

    def checked_floors(actual_block, actual_selection):
        assert actual_block is block and actual_selection is selected
        calls.append('floors')
        return actual_floors(actual_block, actual_selection)

    def provenance(current):
        assert current is run
        calls.append('provenance')
        return result_document

    monkeypatch.setattr(capture, '_load_live', load)
    monkeypatch.setattr(capture, 'phase_replay', phase)
    monkeypatch.setattr(gates, 'current_evidence', evidence)
    monkeypatch.setattr(capture, '_receipt_assessment', assessment)
    monkeypatch.setattr(capture, '_provenance_block', provenance)
    monkeypatch.setattr(native_receipts, 'final_receipt_floors', checked_floors)
    if mutation is None:
        assert capture.live_provenance_block(selected.registration.pin.path) == result_document
        assert calls == ['load', 'phase', 'evidence', 'assessment', 'floors', 'provenance']
    else:
        with pytest.raises(ValueError, match='receipt floors'):
            capture.live_provenance_block(selected.registration.pin.path)
        assert calls == ['load', 'phase', 'evidence', 'assessment', 'floors']
    assert block['coverage_floor']['state'] == 'pending'
    assert block['coverage_floor']['passed'] is False
