"""D109 pending native coverage is diagnostic, while structural floors still gate.

The CLI tests use real native selection/policy capture, receipts.check,
receipts.block_for, strict predicates and printing. They replace only the live
orchestrator's path lookup and final-assessment delivery; they do not prove
observed stage history. The phase test joins that real CLI result to synthetic
prior events and a synthetic command map. The independent gate fixture replaces
assembly reconstruction with a checked spy and uses real final receipt checking.
No executable, provider, full public completion or scientific acceptance is
claimed here. API controls use real disk receipt assessment and registration.
"""
from copy import deepcopy
from pathlib import Path
import json
import shlex

import pytest
from click.testing import CliRunner

from data_sheets_schema import canary
from data_sheets_schema import native_shared_capture_orchestration as capture
from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_gates as gates
from data_sheets_schema import native_shared_receipts as native_receipts
from data_sheets_schema import native_shared_selection as native_selection
from data_sheets_schema import receipt_completion_policy as policy
from data_sheets_schema import receipts as rc
from data_sheets_schema.cli import receipts as cli
from tests.test_native_initial_structure_mode import assessment
from tests.test_native_shared_gates import captured_run, receipt_prepared  # noqa: F401
from tests.test_native_shared_phase import Trace
from tests.test_native_shared_selection import declaration  # noqa: F401
from tests.test_receipt_completion_policy import declaration as api_declaration
from tests.test_receipt_completion_policy import disk as api_disk  # noqa: F401
from tests.test_receipt_completion_policy import registration as api_registration
from tests.test_source_attribution_preflight import inputs  # noqa: F401


PENDING = {'state': 'pending', 'mode': 'diagnostic_pilot'}


@pytest.fixture
def native_strict_case(declaration, monkeypatch):
    """Real selected CLI assessment; only live-controller history is supplied."""
    selected = native_selection.capture(declaration['registration_path'])
    chosen = policy.select_policy(policy.native_render_declaration(selected))
    assert chosen['registration']['coverage_floor'] == PENDING
    root = Path(declaration['stage_root']).parent
    paths = {'full': root / 'supplied-final.yaml',
             'receipt': root / 'supplied-original-receipt.yaml',
             'provenance': root / 'never-written-provenance.yaml', 'core_dir': root}
    calls = []
    delivered = []

    def selected_paths(path):
        assert str(path) == declaration['registration_path']
        calls.append('paths')
        return paths

    def supplied_final(path, *, full_path, receipt_path):
        assert str(path) == declaration['registration_path']
        assert full_path == paths['full'] and receipt_path == paths['receipt']
        calls.append('assessment')
        result = deepcopy(delivered[-1])
        # The surrounding block_for independently validates this against the
        # native selection carried by the actual CLI recovery declaration.
        policy.policy_from_block(result, policy=chosen)
        return result

    monkeypatch.setattr(capture, 'selected_receipt_paths', selected_paths)
    monkeypatch.setattr(capture, 'live_receipt_block', supplied_final)
    args = ['check', '--label', declaration['run']['label'],
            '--project', declaration['run']['project'],
            '--native-shared-selection', declaration['registration_path'], '--strict']

    def invoke(*, mutation=None, change=None):
        block = assessment(mutation)  # Uses the real rc.check on receipt/source/full bytes.
        block.pop('passed')
        block.pop('structural_receipt_floors')
        block.update(native_receipt_stage='final', final_stage_complete=True,
                     coverage_floor=native_receipts.floor(block['slots'], selected),
                     native_stage_completion_history_sha256='a' * 64)
        block[policy.BLOCK_KEY] = policy.block_identity(chosen)
        block['native_shared_receipt_policy'] = dict(chosen['identity'])
        if change == 'initial':
            block.update(native_receipt_stage='phase1_initial', final_stage_complete=False)
        elif change == 'incomplete':
            block['final_stage_complete'] = False
        elif change == 'unchecked':
            block.update(checked=False, reason='Supplied unready final assessment.')
        elif change == 'forged-passed':
            block['coverage_floor']['passed'] = True
        elif change == 'forged-state':
            block['coverage_floor']['state'] = 'passed'
        elif change is not None:
            raise ValueError('unknown test mutation')
        delivered.append(deepcopy(block))
        before = len(calls)
        result = CliRunner().invoke(cli.receipts, args)
        assert calls[before:] == ['paths', 'assessment'], result.output
        assert delivered[-1] == block  # Neither CLI nor floor checking rewrites our evidence.
        assert not paths['provenance'].exists()
        return result, block

    return invoke


def test_pending_native_final_cli_reports_pending_without_strict_failure(native_strict_case):
    result, block = native_strict_case()
    assert block['coverage_floor']['state'] == 'pending'
    assert block['coverage_floor']['passed'] is False
    # The shared/API predicate stays strict; only selected native final routing
    # can apply D109's diagnostic exception.
    assert cli.strict_failure(block) is True
    assert canary.receipt_floors(block)['registered receipt coverage'] == 1
    assert result.exit_code == 0 and result.exception is None, result.output
    assert 'registered receipt coverage: pending' in result.output
    assert '· native receipt stage: final' in result.stdout.splitlines()


def test_pending_native_actual_cli_result_earns_final_phase_milestone(native_strict_case):
    result, block = native_strict_case()
    trace = Trace()
    trace.assembly()
    for name in ('derive_final_core', 'full_schema', 'full_terms', 'core_schema', 'pair'):
        trace.helper(name)
    identity = trace.call('Bash', {'command': shlex.join(trace.commands['final_receipts'])})
    trace.result(identity, code=result.exit_code, text=result.stdout)
    assert 'final_receipts' in trace.state.report()['current_checks'], result.output
    assert block['coverage_floor']['state'] == 'pending'
    assert block['coverage_floor']['passed'] is False
    trace.helper('final_scope')
    trace.finish()
    report = trace.state.report(complete=True)
    assert report['passed'] is True and report['problems'] == []
    # Detached phase replay consumes the same actual CLI outcome; it does not
    # turn this synthetic phase test into public execution acceptance.
    replay = Trace()
    for event, decision in trace.events:
        replay.state.observe(json.loads(json.dumps(event)), stage_decision=decision)
    assert replay.state.report(complete=True) == report


@pytest.mark.parametrize('mutation', ['missing', 'open', 'duplicate', 'snippet', 'date'])
def test_pending_native_final_keeps_structural_refusals(native_strict_case, mutation):
    result, block = native_strict_case(mutation=mutation)
    structural = {key: value for key, value in canary.receipt_floors(block).items()
                  if key != 'registered receipt coverage'}
    assert any(structural.values())
    assert block['coverage_floor']['state'] == 'pending'
    assert block['coverage_floor']['passed'] is False
    assert result.exit_code == 1 and isinstance(result.exception, SystemExit), result.output
    trace = Trace()
    trace.assembly()
    for name in ('derive_final_core', 'full_schema', 'full_terms', 'core_schema', 'pair'):
        trace.helper(name)
    identity = trace.call('Bash', {'command': shlex.join(trace.commands['final_receipts'])})
    trace.result(identity, code=result.exit_code, text=result.stdout)
    assert 'final_receipts' not in trace.state.report()['current_checks']
    with pytest.raises(ValueError, match='current final checks'):
        trace.helper('final_source_inventory')


@pytest.mark.parametrize('change', ['initial', 'incomplete', 'unchecked', 'forged-passed', 'forged-state'])
def test_pending_native_final_does_not_accept_unready_or_forged_assessment(native_strict_case, change):
    result, _ = native_strict_case(change=change)
    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit), repr(result.exception)


@pytest.mark.parametrize('captured_run', [PENDING], indirect=True)
def test_pending_native_independent_receipt_gate_is_structural(receipt_prepared):
    prepared, calls = receipt_prepared
    original = prepared['run'].phase1.original_receipt.raw
    result = gates.receipt_gate(prepared)
    assert calls == ['fresh reconstruction']
    assert result['receipts']['checked'] is True
    assert result['receipts']['final_stage_complete'] is True
    assert result['receipts']['coverage_floor']['state'] == 'pending'
    assert result['receipts']['coverage_floor']['passed'] is False
    assert prepared['run'].phase1.original_receipt.raw == original
    assert result['passed'] is True
    assert 'registered receipt coverage' not in result['floors']
    assert not any(result['floors'].values())


def test_api_pending_real_disk_cli_still_fails_strict(api_disk, tmp_path, monkeypatch):
    """No native selector or supplied native assessment on the API control."""
    paths = {'core_dir': tmp_path, 'full': api_disk['full_path'],
             'provenance': tmp_path / 'P_provenance.yaml'}
    monkeypatch.setattr(cli, '_run_paths', lambda *_: paths)
    registration = api_registration(dict(PENDING))
    registration_path = tmp_path / 'api-pending-registration.json'
    registration_path.write_text(json.dumps(registration))
    block = rc.block_for(**api_disk, receipt_render_spec=api_declaration(registration))
    assert block['checked'] is True
    assert block['coverage_floor']['state'] == 'pending'
    assert block['coverage_floor']['passed'] is False
    assert cli.strict_failure(block) is True
    assert canary.receipt_floors(block)['registered receipt coverage'] == 1
    preserved = {path: path.read_bytes() for path in
                 (api_disk['full_path'], api_disk['receipt'], api_disk['bundle'],
                  api_disk['manifest'], registration_path)}
    result = CliRunner().invoke(cli.receipts, ['check', '--method', 'claudecode_api',
        '--label', 'L', '--project', 'P', '--strict', '--bundle', str(api_disk['bundle']),
        '--chunk-manifest', str(api_disk['manifest']),
        '--receipt-completion-registration', str(registration_path)])
    assert result.exit_code == 1 and isinstance(result.exception, SystemExit), result.output
    assert 'registered receipt coverage: pending' in result.output
    assert 'native receipt stage' not in result.output
    assert {path: path.read_bytes() for path in preserved} == preserved
    assert not paths['provenance'].exists()
