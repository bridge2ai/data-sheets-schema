"""Native policy checks and reader routing; fake readers are not native evidence."""
import copy
import hashlib
import importlib
from pathlib import Path
import types

from click.testing import CliRunner
import pytest

import data_sheets_schema
from data_sheets_schema import canary, native_shared_contract as c
from data_sheets_schema import native_shared_selection as native
from data_sheets_schema import receipt_completion_policy as cp, receipts
from tests.test_native_shared_selection import declaration, pin, save
from tests.test_receipt_completion_policy import block


def captured(declaration, floor=None):
    if floor is not None:
        path = Path(declaration['receipt_policy']['path'])
        policy = c.strict_json(path.read_bytes())
        policy['coverage_floor'] = floor
        raw = c.canonical(policy)
        path.write_bytes(raw)
        declaration['receipt_policy'] = pin(path, raw)
        save(declaration)
    return native.capture(declaration['registration_path'])


def test_native_recorded_policy_is_pure_distinct_and_recomputed(declaration, monkeypatch):
    cap = captured(declaration, {'state': 'registered', 'numerator': 2, 'denominator': 3})
    spec = cp.native_render_declaration(cap)
    def blocked(*args, **kwargs):
        pytest.fail('recorded native policy attempted current-file discovery')
    monkeypatch.setattr(Path, 'read_bytes', blocked)
    monkeypatch.setattr(Path, 'resolve', blocked)
    monkeypatch.setattr(native, 'resource_path', blocked)
    policy = cp.select_policy(spec)
    assert policy['registration']['kind'] == c.KINDS['receipt_policy']
    assert 'format' not in policy['registration']
    checked = block(policy, 1, 3)
    checked['coverage_floor'] = {'passed': True, 'state': 'passed'}
    record = {'prompts': {'request': {'spec': spec}}, 'receipts': checked}
    assert cp.select_policy(record=record) == policy
    assert cp.policy_from_block(checked, policy=policy) == policy
    assert canary.receipt_coverage_floor(canary.checks_from_record(record)['receipts'])['passed'] is False
    assert canary.receipt_coverage_floor(block(policy, 2, 3))['passed'] is True
    assert canary.receipt_coverage_floor(block(policy, 0, 0))['state'] == 'not_applicable'


@pytest.mark.parametrize('field', sorted(cp.NATIVE_SPEC_KEYS))
def test_partial_native_render_selection_never_falls_back(declaration, field):
    spec = cp.native_render_declaration(captured(declaration))
    del spec[field]
    with pytest.raises(ValueError):
        cp.select_policy(spec)


@pytest.mark.parametrize('change', ['axis', 'renderer', 'runtime', 'condition', 'api_receipt',
                                  'registration', 'policy_path', 'context', 'descriptor'])
def test_native_reader_refuses_changed_authority(declaration, change):
    spec = cp.native_render_declaration(captured(declaration))
    if change == 'axis': spec['native_shared_generation_version'] = True
    elif change == 'renderer': spec['render_version'] = 25
    elif change == 'runtime': spec['runtime'] = 'Claude API'
    elif change == 'condition': spec['condition'] = 'generic_v9'
    elif change == 'api_receipt': spec['receipt_completion_version'] = 2
    elif change == 'registration': spec['native_shared_generation_registration']['raw_json'] += '\n'
    elif change == 'policy_path': spec['native_shared_receipt_policy']['path'] += '.other'
    elif change == 'context': spec['native_shared_generation_context']['context']['raw_json'] += '\n'
    else: spec['native_shared_generation_descriptor']['receipt_policy']['sha256'] = 'f' * 64
    with pytest.raises(ValueError):
        cp.select_policy(spec)


def test_same_floor_cannot_hide_different_native_selection(declaration):
    spec = cp.native_render_declaration(captured(declaration))
    other = copy.deepcopy(spec)
    doc = c.strict_json(other['native_shared_generation_registration']['raw_json'].encode())
    doc['registration_id'] += '-other'
    raw = c.canonical(doc)
    other['native_shared_generation_registration'] = {'sha256': c.sha(raw), 'raw_json': raw.decode()}
    assert cp.select_policy(spec) == cp.select_policy(other)
    with pytest.raises(ValueError, match='native receipt selection differs'):
        cp.select_policy(spec, {'prompts': {'request': {'spec': other}}})


def test_receipt_marker_and_native_zero_axis_cannot_activate_policy():
    assert cp.select_policy({'native_shared_generation_version': 0}) is None
    assert cp.select_policy(record={'native_receipt_stage': 'final', 'receipts': {'checked': True}}) is None
    with pytest.raises(ValueError, match='integer'):
        cp.select_policy({'native_shared_generation_version': False})
    with pytest.raises(ValueError, match='byte bound'):
        cp.policy_from_block({cp.BLOCK_KEY: {'registration': {'sha256': 'a' * 64,
            'raw_json': ' ' * 2_000_001}, 'runtime_policy_sha256': native.RECEIPT_POLICY_SHA256}})


@pytest.fixture
def routed(declaration, tmp_path, monkeypatch):
    cap = captured(declaration)
    spec = cp.native_render_declaration(cap)
    cli = importlib.import_module('data_sheets_schema.cli.receipts')
    provenance = importlib.import_module('data_sheets_schema.cli.provenance')
    root = tmp_path / 'outputs'
    root.mkdir()
    paths = {'core_dir': root, 'full': root / 'SYNTHETIC_d4d.yaml',
             'provenance': root / 'SYNTHETIC_provenance.yaml'}
    paths['full'].write_bytes(b'name: Synthetic\n')
    receipt = receipts.receipt_path(root, 'SYNTHETIC')
    receipt.write_bytes(b'fixture: current receipt\n')
    monkeypatch.setattr(provenance, '_require_repo_root_cwd', lambda *args: None)
    monkeypatch.setattr(cli, '_run_paths', lambda *args: paths)
    calls = []
    result = block(cp.select_policy(spec))
    result.update(summary='Synthetic reader-routing result, no callback proof.',
        non_checks=['No native observation was exercised by this routing fixture.'],
        native_receipt_stage='phase1_initial', final_stage_complete=False, passed=True,
        coverage_floor={'state': 'pending', 'passed': False, 'with_receipt': 2, 'receiptable': 3,
                        'registration_sha256': cap.receipt_policy.pin.sha256},
        identity_rules={'identifier_bases': []})
    def live(path, **kwargs):
        calls.append(('live', str(path), kwargs))
        return copy.deepcopy(result)
    def recorded(specification, **kwargs):
        calls.append(('recorded', specification, kwargs))
        return copy.deepcopy(result)
    monkeypatch.setattr(data_sheets_schema, 'native_shared_capture',
        types.SimpleNamespace(live_receipt_block=live, recorded_receipt_block=recorded), raising=False)
    monkeypatch.setattr(receipts, 'phase1_snapshot_state', lambda *a, **k: pytest.fail('native reader used API snapshots'))
    return cap, spec, cli, paths, receipt, calls, result


def test_native_cli_initial_and_final_use_observed_reader_and_explicit_paths(routed):
    cap, spec, cli, paths, receipt, calls, result = routed
    originals = {p: p.read_bytes() for p in (paths['full'], receipt)}
    args = ['--native-shared-selection', cap.registration.pin.path,
            '--label', 'offline-test', '--project', 'SYNTHETIC', '--strict']
    initial = CliRunner().invoke(cli.check, args)
    assert initial.exit_code == 0, initial.output
    assert calls == [('live', cap.registration.pin.path, {'full_path': paths['full'], 'receipt_path': receipt})]
    assert 'pending' in initial.output
    result.update(native_receipt_stage='final', final_stage_complete=True)
    final = CliRunner().invoke(cli.check, args)
    assert final.exit_code == 1  # The declared pending floor is not final success.
    assert {p: p.read_bytes() for p in originals} == originals


@pytest.mark.parametrize('value', [False, 1, None])
def test_initial_receipt_strict_requires_actual_boolean_pass(routed, value):
    cap, _, cli, _, _, _, result = routed
    result['passed'] = value
    actual = CliRunner().invoke(cli.check, ['--native-shared-selection', cap.registration.pin.path,
        '--label', 'offline-test', '--project', 'SYNTHETIC', '--strict'])
    assert actual.exit_code == 1, actual.output


def test_explicit_record_native_reader_does_not_discover_live_index(routed):
    _, spec, _, paths, receipt, calls, _ = routed
    record = {'prompts': {'request': {'spec': spec}}}
    result = receipts.block_for(paths['full'], receipt, None, None, True, snapshot_record=record)
    assert result['checked'] is True
    assert calls == [('recorded', None, {'record': record, 'full_path': paths['full'], 'receipt_path': receipt})]


def test_native_cli_foreign_project_and_api_registration_conflict_before_reader(routed):
    cap, _, cli, _, _, calls, _ = routed
    base = ['--native-shared-selection', cap.registration.pin.path, '--label', 'offline-test']
    foreign = CliRunner().invoke(cli.check, base + ['--project', 'OTHER'])
    assert foreign.exit_code != 0 and 'another project' in foreign.output
    conflict = CliRunner().invoke(cli.check, base + ['--project', 'SYNTHETIC',
        '--receipt-completion-registration', cap.receipt_policy.pin.path])
    assert conflict.exit_code != 0 and 'mutually exclusive' in conflict.output
    assert calls == []
