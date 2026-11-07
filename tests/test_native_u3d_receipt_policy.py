"""Native receipt policy selection must not change API/v5 semantics (D95)."""
from copy import deepcopy
from pathlib import Path

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_selection as native
from data_sheets_schema import receipt_completion_policy as policy
from data_sheets_schema.cli.receipts import strict_failure
from tests.test_native_shared_selection import declaration, pin, save
from tests.test_receipt_completion_policy import declaration as api_declaration


def selected(declaration, registered=False):
    if registered:
        path = Path(declaration['receipt_policy']['path'])
        value = c.strict_json(path.read_bytes())
        value['coverage_floor'] = {'state': 'registered', 'numerator': 2, 'denominator': 3}
        raw = c.canonical(value)
        path.write_bytes(raw)
        declaration['receipt_policy'] = pin(path, raw)
        save(declaration)
    capture = native.capture(declaration['registration_path'])
    return policy.native_render_declaration(capture)


def test_pending_native_floor_never_becomes_strict_success(declaration):
    spec = selected(declaration)
    chosen = policy.select_policy(spec)
    counts = {'with_receipt': 3, 'receiptable': 3}
    floor = policy.evaluate_floor(counts, chosen)
    assert floor['state'] == 'pending' and floor['passed'] is False
    block = {'expected': True, 'checked': True, 'slots': counts,
        policy.BLOCK_KEY: policy.block_identity(chosen), 'coverage_floor': floor}
    assert strict_failure(block)


def test_native_registered_floor_uses_exact_counts_and_recorded_identity(declaration):
    spec = selected(declaration, registered=True)
    record = {'prompts': {'request': {'spec': spec}}}
    chosen = policy.select_policy(spec, record)
    assert chosen == policy.select_policy(record=record)
    assert policy.evaluate_floor({'with_receipt': 2, 'receiptable': 3}, chosen)['passed']
    assert not policy.evaluate_floor({'with_receipt': 1, 'receiptable': 3}, chosen)['passed']
    assert policy.evaluate_floor({'with_receipt': 0, 'receiptable': 0}, chosen)['state'] == 'not_applicable'
    changed = deepcopy(spec)
    changed['native_shared_receipt_policy']['raw_json'] += '\n'
    with pytest.raises(ValueError):
        policy.select_policy(changed, record)


@pytest.mark.parametrize('axis,value', [('native_shared_generation_version', True),
    ('receipt_completion_version', 1), ('bounded_carry_version', 1),
    ('shared_generation_version', 2), ('render_version', 27)])
def test_native_policy_rejects_mixed_axes(declaration, axis, value):
    spec = selected(declaration)
    spec[axis] = value
    with pytest.raises(ValueError):
        policy.select_policy(spec)


def test_explicit_disabled_native_axis_preserves_api_policy():
    ordinary = api_declaration()
    assert policy.select_policy(ordinary) == policy.select_policy(
        {**ordinary, 'native_shared_generation_version': 0})


@pytest.mark.parametrize('registered', [False, True])
def test_actual_cli_refuses_pending_initial_floor(tmp_path, monkeypatch, declaration, registered):
    """CLI exit contract only; the native assessment is independently tested.

    A supplied structural assessment cannot turn a pending floor into strict
    success merely because its stage is initial and its floor is registered.
    """
    from click.testing import CliRunner
    from data_sheets_schema import receipts as receipt_lib
    from data_sheets_schema.cli import receipts as cli
    spec = selected(declaration, registered=registered)
    chosen = policy.select_policy(spec)
    counts = {'with_receipt': 3, 'receiptable': 3}
    floor = policy.evaluate_floor(counts, chosen)
    floor.update(state='pending', passed=False)
    assessment = {'expected': True, 'checked': True, 'passed': True,
        'native_receipt_stage': 'phase1_initial', 'final_stage_complete': False,
        'slots': counts, policy.BLOCK_KEY: policy.block_identity(chosen),
        'coverage_floor': floor, 'summary': 'initial structural check only',
        'findings': [], 'non_checks': []}
    root = tmp_path / 'cli'; root.mkdir()
    full = root / 'full.yaml'; full.write_text('id: test\n')
    bundle = root / 'bundle.md'; bundle.write_text('source\n')
    paths = {'core_dir': root, 'full': full, 'provenance': root / 'record.yaml'}
    monkeypatch.setattr(cli, '_run_paths', lambda *_: paths)
    monkeypatch.setattr(receipt_lib, 'block_for', lambda *a, **k: deepcopy(assessment))
    result = CliRunner().invoke(cli.receipts, ['check', '--method', 'native-test',
        '--label', 'local', '--project', 'NEUTRAL', '--bundle', str(bundle), '--strict'])
    assert result.exit_code == 1, result.output
    assert 'registered receipt coverage: pending' in result.output
    assert isinstance(result.exception, SystemExit)
    assert not paths['provenance'].exists()
