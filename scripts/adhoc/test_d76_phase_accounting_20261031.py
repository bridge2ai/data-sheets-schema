# Purpose: regression tests for interrupted/duplicate pytest occurrence accounting.
# Inputs: synthetic phase ledgers and retained stopped-run nodes; outputs: pytest evidence.
# Serves #5213/D76 H4, 2026-10-31. No provider/network/source/evidence mutations.
import hashlib
import importlib.util
import json
from pathlib import Path

MODULE = Path(__file__).with_name('d76_phase_accounting_20261031.py')
SPEC = importlib.util.spec_from_file_location('d76_phase_unit', MODULE)
PHASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PHASE)


def report(node='node', phase='setup', outcome='passed', index=0, xfail=None):
    return {'nodeid': node, 'when': phase, 'outcome': outcome, 'item_index': index, 'xfail': xfail}


def complete(node='node', index=0):
    return [report(node, phase, index=index) for phase in ('setup', 'call', 'teardown')]


def test_setup_only_is_interrupted_not_passed():
    value = PHASE.phase_accounting(['node'], [report()])
    assert value['counts']['passed'] == 0
    assert value['counts']['interrupted'] == 1
    assert value['all_selected_completed'] is False


def test_missing_teardown_is_interrupted_not_passed():
    value = PHASE.phase_accounting(['node'], complete()[:2])
    assert value['counts']['passed'] == 0 and value['counts']['interrupted'] == 1


def test_indexed_duplicate_occurrences_each_count_once():
    first, second = complete(index=1), complete(index=4)
    phases = [phase for pair in zip(first, second) for phase in pair]
    value = PHASE.phase_accounting(['node', 'node'], phases)
    assert value['counts']['passed'] == 2 and value['all_selected_completed'] is True


def test_duplicate_occurrences_cannot_borrow_passing_phases():
    phases = [report(index=1), report(outcome='failed', index=4),
              report(phase='call', index=1), report(phase='teardown', index=4),
              report(phase='teardown', outcome='failed', index=1)]
    value = PHASE.phase_accounting(['node', 'node'], phases)
    assert value['counts']['passed'] == 0 and value['counts']['errors'] == 2
    assert value['all_selected_completed'] is True


def test_setup_skip_is_complete_skip():
    value = PHASE.phase_accounting(['node'], [report(outcome='skipped'), report(phase='teardown')])
    assert value['counts']['skipped'] == 1 and value['all_selected_completed'] is True


def test_unexpected_nodes_never_cover_unstarted_selection():
    value = PHASE.phase_accounting(['expected'], complete('unexpected'))
    assert value['counts']['unexpected'] == 1
    assert value['counts']['not_started'] == 1
    assert value['all_selected_completed'] is False


def test_unindexed_legacy_duplicates_remain_ambiguous():
    phases = complete() + complete()
    for row in phases:
        row.pop('item_index')
    value = PHASE.phase_accounting(['node', 'node'], phases)
    assert value['counts']['passed'] == 0 and value['counts']['interrupted'] == 2
    assert value['ambiguous_legacy_duplicate_nodes'] == ['node']


def test_xpass_even_without_reason_is_not_counted_as_pass():
    phases = complete()
    phases[1]['xfail'] = ''
    value = PHASE.phase_accounting(['node'], phases)
    assert value['counts']['passed'] == 0 and value['counts']['xpassed'] == 1


def test_call_failure_with_teardown_is_complete_failure():
    phases = complete()
    phases[1]['outcome'] = 'failed'
    value = PHASE.phase_accounting(['node'], phases)
    assert value['counts']['failed'] == 1 and value['all_selected_completed'] is True


def test_retained_interrupted_probe_ledger_has_only_two_complete_passes():
    evidence = Path(__file__).resolve().parents[3] / 'plans/reviews/pr5213_d76_2026-10-31/baseline-reviewer-probes/nodes.json'
    before = evidence.read_bytes()
    assert hashlib.sha256(before).hexdigest() == '15d814261a6343dcb351d9c1cd8d2027e1811410ad015a8b61f3fc244fe10807'
    nodes = json.loads(before)
    value = PHASE.phase_accounting(nodes['selected'], nodes['reports'])
    assert value['counts'] == {'passed': 2, 'failed': 4, 'errors': 0, 'skipped': 0,
        'xpassed': 0, 'interrupted': 3, 'not_started': 13, 'unexpected': 0}
    assert value['all_selected_completed'] is False
    assert evidence.read_bytes() == before
