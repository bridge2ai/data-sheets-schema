"""An audit whose immediate predecessor is a transport probe (#2469); synthetic lineages only."""
import copy
import json
from pathlib import Path

import httpx
import pytest

from budgeted_cborg import BudgetStop
from audit_controls import probe_predecessor
from audit_controls import registration as r
import transport_probe as probe
from test_transport_probe import (Upstream, lineage, prepared, run, save, sha, ok_stream,  # noqa: F401  (fixtures)
                                  accounting)


def completed(lin):
    return run(lin, Upstream(ok_stream))


def refused(lin):
    """A 400 leaves the probe's one row pending; the standing debit reconciles it."""
    return run(lin, Upstream(lambda request, clock: httpx.Response(400, json={'error': 'synthetic'})))


def successor(lin, result):
    """The next audit: the first audit's registration, continued from the probe's checkpoint."""
    first = r.read_json(lin.source)
    manifest = copy.deepcopy(first)
    manifest['job'] = {**first['job'], 'id': 'after_probe', 'attempt_dir': str(lin.root / 'after' / 'attempts' / 'after_probe')}
    checkpoint = Path(result['successor_continues_from'])
    continuation = {'checkpoint': str(checkpoint), 'sha256': sha(checkpoint), 'cost_usd': result['successor_cost_usd']}
    out = lin.root / 'probe'
    if checkpoint.name == 'reconciled_billing.json':
        continuation['reconciliation'] = {'source_registration': str(out / 'registration.json'),
                                          'source_ledger': str(out / 'billing.json'),
                                          'receipt': str(out / 'debit_receipt.json'),
                                          'result': str(out / 'result.json')}
    manifest['budget'] = {**first['budget'], 'per_job_attempt_usd': {'after_probe': 20},
                          'ledger_path': str(lin.root / 'after' / 'billing.json'), 'continuation': continuation}
    repin(manifest)
    return manifest, lin.root / 'after' / 'registration.json'


def repin(manifest):
    bridge = manifest['budget']['continuation'].get('reconciliation') or {}
    names = {manifest['budget']['continuation']['checkpoint'], *bridge.values(),
             *map(str, probe_predecessor.paths(manifest))}
    manifest['pinned_files'].update({name: sha(name) for name in names})


def continue_after(lin, manifest, path):
    save(path, manifest)
    identity = r.sha(path)
    with r.sequence_guard(manifest, identity):
        ledger = r.open_audit_ledger(manifest, path, identity)
    return identity, r.read_json(ledger.path)


@pytest.mark.parametrize('outcome', [completed, refused])
def test_an_audit_continues_from_the_probe_and_takes_the_tip(prepared, outcome):
    result = outcome(prepared)
    manifest, path = successor(prepared, result)
    assert probe_predecessor.is_probe_predecessor(manifest)
    identity, state = continue_after(prepared, manifest, path)
    carried = r.read_json(result['successor_continues_from'])['requests']
    assert state['requests'] == carried and state['continued_from']['manifest_sha256'] == prepared.identity
    tip = json.loads(prepared.state.read_text())
    assert tip['registration_sha256'] == identity and tip['ledger_path'] == manifest['budget']['ledger_path']
    # The debit's receipt and the probe's link are pinned by the successor's registration.
    assert {str(prepared.root / 'probe' / name) for name in ('registration.json', 'billing.json', 'result.json')} \
        <= set(manifest['pinned_files'])


def test_an_audit_from_the_tip_before_the_probe_is_a_fork(prepared):
    completed(prepared)
    first = r.read_json(prepared.source)
    manifest = copy.deepcopy(first)
    manifest['job'] = {**first['job'], 'id': 'forked'}
    reconciliation = {'source_registration': str(prepared.source), 'source_ledger': str(prepared.tip_ledger),
                      'receipt': str(prepared.receipt),
                      'result': str(Path(first['job']['attempt_dir']) / 'result.json')}
    manifest['budget'] = {**first['budget'], 'per_job_attempt_usd': {'forked': 20},
                          'ledger_path': str(prepared.root / 'fork' / 'billing.json'),
                          'continuation': {'checkpoint': str(prepared.checkpoint), 'sha256': sha(prepared.checkpoint),
                                           'cost_usd': '0', 'reconciliation': reconciliation}}
    repin(manifest)
    path = save(prepared.root / 'fork' / 'registration.json', manifest)
    with pytest.raises(BudgetStop, match='current sequence tip'):
        with r.sequence_guard(manifest, r.sha(path)):
            pass


def _tamper(lin, manifest, name, change):
    target = lin.root / 'probe' / name
    value = r.read_json(target)
    change(value)
    save(target, value)
    if name == 'reconciled_billing.json':
        # Rebind the result to the changed file, so only the recomputation can refuse it.
        result = lin.root / 'probe' / 'result.json'
        recorded = r.read_json(result)
        recorded['settlement']['sha256'] = sha(target)
        save(result, recorded)
    if name in ('billing.json', 'reconciled_billing.json'):
        manifest['budget']['continuation']['sha256'] = sha(manifest['budget']['continuation']['checkpoint'])
    repin(manifest)


@pytest.mark.parametrize('name, change, match', [
    ('reconciled_billing.json', lambda v: v['requests'][-1].update(cost_usd='0.01'), 'beyond the one debit'),
    ('reconciled_billing.json', lambda v: v['requests'][0].update(cost_usd='0'), 'beyond the one debit'),
    ('debit_receipt.json', lambda v: v['user_authorization'].update(exact_response='another'), 'standing authorization'),
    ('debit_receipt.json', lambda v: v['runtime_at_settlement'].update(unfinished_handlers=1), 'closed runtime'),
    ('result.json', lambda v: v.update(tip_claimed=False), 'did not claim the tip'),
    ('result.json', lambda v: v['settlement'].update(status='needs_person'), 'needs a person'),
])
def test_a_changed_probe_link_is_refused(prepared, name, change, match):
    manifest, path = successor(prepared, refused(prepared))
    _tamper(prepared, manifest, name, change)
    save(path, manifest)
    with pytest.raises(BudgetStop, match=match):
        r.validate_audit_reconciliation(manifest)


@pytest.mark.parametrize('change, match', [
    (lambda v: v['requests'].append({**v['requests'][-1], 'id': 'extra'}), 'at most its one request'),
    (lambda v: v['requests'][0].update(cost_usd='0'), 'carry its predecessor checkpoint'),
    (lambda v: v.update(additional_cap_usd='800'), 'changes the lineage caps'),
])
def test_a_settled_probe_ledger_must_carry_its_predecessor_and_one_request(prepared, change, match):
    manifest, path = successor(prepared, completed(prepared))
    _tamper(prepared, manifest, 'billing.json', change)
    with pytest.raises(BudgetStop, match=match):
        probe_predecessor.validate_link(manifest)


def test_an_unpinned_probe_link_is_refused(prepared):
    manifest, _ = successor(prepared, completed(prepared))
    del manifest['pinned_files'][str(prepared.root / 'probe' / 'result.json')]
    with pytest.raises(BudgetStop, match='registered input'):
        probe_predecessor.validate_link(manifest)


def test_a_reconciled_probe_is_continued_only_through_its_bridge_and_a_settled_one_without(prepared):
    manifest, _ = successor(prepared, refused(prepared))
    del manifest['budget']['continuation']['reconciliation']
    with pytest.raises(BudgetStop, match='checkpoint its settlement wrote'):
        probe_predecessor.validate_link(manifest)


def test_a_reconciled_checkpoint_not_the_one_the_result_names_is_refused(prepared):
    manifest, _ = successor(prepared, refused(prepared))
    target = prepared.root / 'probe' / 'reconciled_billing.json'
    save(target, {**r.read_json(target), 'note': 'changed'})
    manifest['budget']['continuation']['sha256'] = sha(target)
    repin(manifest)
    with pytest.raises(BudgetStop, match='checkpoint its settlement wrote'):
        r.validate_audit_reconciliation(manifest)


def test_a_settled_probe_is_not_continued_through_a_bridge(prepared):
    result = completed(prepared)
    manifest, _ = successor(prepared, result)
    out = prepared.root / 'probe'
    manifest['budget']['continuation']['reconciliation'] = {
        'source_registration': str(out / 'registration.json'), 'source_ledger': str(out / 'billing.json'),
        'receipt': str(out / 'result.json'), 'result': str(out / 'result.json')}
    repin(manifest)
    with pytest.raises(BudgetStop, match='own ledger, with no reconciliation'):
        probe_predecessor.validate_link(manifest)


@pytest.mark.parametrize('change, match', [
    (lambda v: v.update(kind='something_else'), 'did not follow an audit of this origin'),
    (lambda v: v.update(note='edited after the probe'), 'own predecessor changed'),
])
def test_the_probes_own_predecessor_must_be_an_unchanged_audit_of_the_origin(prepared, change, match):
    manifest, _ = successor(prepared, completed(prepared))
    source = r.read_json(prepared.source)
    change(source)
    save(prepared.source, source)
    repin(manifest)
    with pytest.raises(BudgetStop, match=match):
        probe_predecessor.validate_link(manifest)


def test_the_names_are_the_probes():
    assert (probe_predecessor.KIND, probe_predecessor.RESULT_KIND, probe_predecessor.ATTEMPT,
            probe_predecessor.DEBIT_KIND, probe_predecessor.HANDLER_RUNNING, probe_predecessor.AUDIT_KIND) == (
        probe.KIND, probe.RESULT_KIND, probe.ATTEMPT, probe.DEBIT_KIND, probe.HANDLER_RUNNING, probe.AUDIT_KIND)


def test_an_audit_continues_after_a_debit_settle_applied_once_the_probe_exited(prepared, monkeypatch):
    from test_transport_probe import _unfinished
    from decimal import Decimal
    _unfinished(monkeypatch)
    result = refused(prepared)
    assert result['settlement']['reason'] == probe.HANDLER_RUNNING and result['successor_continues_from'] is None
    # Before `settle`, the link has no settled checkpoint to hand on.
    manifest, _ = successor(prepared, {**result, 'successor_continues_from': str(prepared.root / 'probe' / 'billing.json'),
                                       'successor_cost_usd': '0'})
    with pytest.raises(BudgetStop, match='needs a person'):
        probe_predecessor.validate_link(manifest)
    settlement = probe.settle(prepared.registration, prepared.identity)
    cost = str(sum((Decimal(row['cost_usd']) for row in r.read_json(settlement['path'])['requests']), Decimal(0)))
    manifest, path = successor(prepared, {'successor_continues_from': settlement['path'], 'successor_cost_usd': cost})
    assert str(prepared.root / 'probe' / 'settlement_after_exit.json') in manifest['pinned_files']
    continue_after(prepared, manifest, path)
    # A settlement-after-exit that names another result is refused.
    after = prepared.root / 'probe' / 'settlement_after_exit.json'
    save(after, {**r.read_json(after), 'result_sha256': '0' * 64})
    repin(manifest)
    with pytest.raises(BudgetStop, match='names another result'):
        probe_predecessor.validate_link(manifest)


# --- the wiring, each through its real caller (#2506) ------------------------------------------

def test_the_sequence_guard_refuses_a_changed_settled_probe_link(prepared):
    manifest, path = successor(prepared, completed(prepared))
    _tamper(prepared, manifest, 'billing.json', lambda v: v['requests'][0].update(cost_usd='0'))
    save(path, manifest)
    before = prepared.state.read_bytes()
    with pytest.raises(BudgetStop, match='carry its predecessor checkpoint'):
        with r.sequence_guard(manifest, r.sha(path)):
            pass
    assert prepared.state.read_bytes() == before


@pytest.mark.parametrize('outcome', [completed, refused])
def test_the_registration_pins_every_file_of_the_probe_link(prepared, outcome):
    manifest, _ = successor(prepared, outcome(prepared))
    out = prepared.root / 'probe'
    expected = {out / 'registration.json', out / 'billing.json', out / 'result.json', prepared.source}
    if outcome is refused:
        expected |= {out / 'reconciled_billing.json', out / 'debit_receipt.json'}
    assert expected <= r.continuation_paths(manifest)


def test_the_settlement_after_exit_is_pinned_and_checked(prepared, monkeypatch):
    from test_transport_probe import _unfinished
    from decimal import Decimal
    _unfinished(monkeypatch)
    refused(prepared)
    settlement = probe.settle(prepared.registration, prepared.identity)
    cost = str(sum((Decimal(row['cost_usd']) for row in r.read_json(settlement['path'])['requests']), Decimal(0)))
    manifest, _ = successor(prepared, {'successor_continues_from': settlement['path'], 'successor_cost_usd': cost})
    after = prepared.root / 'probe' / 'settlement_after_exit.json'
    assert after in r.continuation_paths(manifest)
    save(after, {**r.read_json(after), 'closure_basis': 'edited'})
    with pytest.raises(BudgetStop, match='registered input'):
        probe_predecessor.validate_link(manifest)


def test_prepare_bridges_to_the_probes_own_result(prepared):
    from audit_controls.prepare import _bridge_result
    refused(prepared)
    registration = prepared.root / 'probe' / 'registration.json'
    assert _bridge_result(registration, r.read_json(registration)) == str(prepared.root / 'probe' / 'result.json')
    first = r.read_json(prepared.source)
    assert _bridge_result(prepared.source, first) == str(Path(first['job']['attempt_dir']) / 'result.json')


def test_the_amendment_candidate_names_the_sequence_state_the_registration_will(tmp_path):
    from audit_controls.prepare import amendment_candidate
    ledger = save(tmp_path / 'origin' / 'billing.json', {'requests': [{'cost_usd': '1.5'}]})
    origin = save(tmp_path / 'origin' / 'registration.json',
                  {'budget': {'ledger_path': str(ledger), 'per_attempt_usd': '5'}})
    candidate = amendment_candidate(origin, {'total_usd': '600'}, ledger)
    assert candidate['sequence_state'] == str(ledger.with_name('audit_sequence.json'))
    assert candidate['budget']['continuation']['cost_usd'] == '1.5'
    # A relative origin ledger resolves against the origin's repository, as the registration's does.
    relative = save(tmp_path / 'origin' / 'relative.json',
                    {'repository': str(tmp_path / 'repo'), 'budget': {'ledger_path': 'runs/billing.json',
                                                                      'per_attempt_usd': '5'}})
    assert amendment_candidate(relative, {'total_usd': '600'}, ledger)['sequence_state'] == str(
        tmp_path / 'repo' / 'runs' / 'audit_sequence.json')


def _v1_on(reference, total='400'):
    """A v1 selection whose predecessor is `reference`; its other documents are never read here."""
    ref = {'path': str(reference), 'sha256': sha(reference)}
    other = lambda name: {'path': str(reference.parent / name), 'sha256': '0' * 64}
    return {'kind': 'additive_sequence_budget_v1', 'origin_registration': other('origin.json'),
            'predecessor_registration': ref, 'predecessor_ledger': other('ledger.json'),
            'predecessor_owner': other('owner.json'), 'authorization': other('authority.json'),
            'prior_total_usd': total, 'increase_usd': '200', 'total_usd': str(int(total) + 200),
            'default_attempt_usd': '5'}


@pytest.mark.parametrize('outcome', [completed, refused])
def test_an_amended_audit_may_name_the_probe_as_its_predecessor(prepared, outcome):
    manifest, _ = successor(prepared, outcome(prepared))
    registration = prepared.root / 'probe' / 'registration.json'
    candidate = {key: manifest[key] for key in ('kind', 'parent', 'budget', 'sequence_state')}
    candidate.update(budget_amendment=_v1_on(registration), pinned_files={})
    previous = r.read_json(manifest['budget']['continuation']['checkpoint'])
    assert r.validate_budget_amendment_predecessor(candidate, previous, require_pins=False) == registration
    # Naming the audit before the probe as the predecessor is refused.
    candidate['budget_amendment'] = _v1_on(prepared.source)
    with pytest.raises(BudgetStop, match='authorized predecessor'):
        r.validate_budget_amendment_predecessor(candidate, previous, require_pins=False)
    # A candidate that names no sequence state is refused, never a KeyError (#2504).
    del candidate['sequence_state']
    with pytest.raises(BudgetStop, match='no sequence state'):
        r.validate_budget_amendment_predecessor(candidate, previous, require_pins=False)


def test_a_malformed_probe_ledger_is_a_budget_stop(prepared):
    manifest, _ = successor(prepared, completed(prepared))
    (prepared.root / 'probe' / 'billing.json').write_text('[]\n')
    repin(manifest)
    with pytest.raises(BudgetStop, match='malformed'):
        probe_predecessor.validate_link(manifest)


def test_a_settlement_after_exit_without_a_deferred_settlement_is_refused(prepared):
    manifest, _ = successor(prepared, completed(prepared))
    save(prepared.root / 'probe' / 'settlement_after_exit.json', {'status': 'settled'})
    repin(manifest)
    with pytest.raises(BudgetStop, match='without a deferred settlement'):
        probe_predecessor.validate_link(manifest)


def test_a_malformed_settlement_after_exit_is_a_budget_stop(prepared, monkeypatch):
    from test_transport_probe import _unfinished
    from decimal import Decimal
    _unfinished(monkeypatch)
    refused(prepared)
    settlement = probe.settle(prepared.registration, prepared.identity)
    cost = str(sum((Decimal(row['cost_usd']) for row in r.read_json(settlement['path'])['requests']), Decimal(0)))
    manifest, _ = successor(prepared, {'successor_continues_from': settlement['path'], 'successor_cost_usd': cost})
    (prepared.root / 'probe' / 'settlement_after_exit.json').write_text('[]\n')
    repin(manifest)
    with pytest.raises(BudgetStop, match='settlement after exit is malformed'):
        probe_predecessor.validate_link(manifest)
