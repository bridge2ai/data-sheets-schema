"""A transport probe as an audit's immediate predecessor (#2469).

The probe (#2463, `native_controls/transport_probe.py`) is a lineage link: it
claims the audit sequence tip, continues the prior tip's settled checkpoint
into its own ledger and leaves either that ledger settled or one pending row
debited at its whole reservation in `reconciled_billing.json`. An audit that
follows it continues from that checkpoint. This module checks the link
through to the audit before the probe, one hop, as audit successors check
each other: the probe's own predecessor is an audit on the same origin, its
ledger carries that audit's checkpoint unchanged, it claimed the tip, and the
checkpoint the successor names is the one its settlement produced, recomputed
from the ledger and the debit receipt. It reads only; it writes nothing.

The names below are the probe's; a test pins them to `transport_probe`, which
this module does not import (that would pull the proxy into every audit).
"""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from budgeted_cborg import BudgetStop

from .registration import canonical_json, canonical_path, pinned as _pinned, read_json, sha

KIND = 'd4d_native_transport_probe_v1'
RESULT_KIND = 'd4d_native_transport_probe_result_v1'
AUDIT_KIND = 'd4d_native_audit_continuation'
ATTEMPT = 'transport_probe'
DEBIT_KIND = 'user_authorized_full_reservation_debit'
HANDLER_RUNNING = 'a proxy handler was still running at shutdown'
BRIDGE = ('source_registration', 'source_ledger', 'receipt', 'result')


def _require(ok, reason):
    if not ok:
        raise BudgetStop(reason)


def predecessor_path(manifest):
    """The registration the audit's continuation names, whether or not it exists."""
    continuation = manifest['budget']['continuation']
    bridge = continuation.get('reconciliation')
    if isinstance(bridge, dict) and 'source_registration' in bridge:
        return canonical_path(bridge['source_registration'])
    return canonical_path(continuation['checkpoint']).with_name('registration.json')


def is_probe_predecessor(manifest):
    path = predecessor_path(manifest)
    return path.is_file() and read_json(path).get('kind') == KIND


def _files(root):
    return {name: root / name for name in ('registration.json', 'billing.json', 'result.json',
                                           'reconciled_billing.json', 'debit_receipt.json',
                                           'settlement_after_exit.json')}


_MALFORMED = (KeyError, TypeError, AttributeError, ValueError, OSError, ArithmeticError)


def paths(manifest):
    """What an audit following a probe pins: the probe's link and the audit before it."""
    try:
        return _paths(manifest)
    except _MALFORMED as error:
        # The predecessor may be an ordinary audit; say only what failed (#2513).
        raise BudgetStop('audit predecessor evidence is malformed or unavailable') from error


def _paths(manifest):
    if not is_probe_predecessor(manifest):
        return set()
    files = _files(predecessor_path(manifest).parent)
    probe = read_json(files['registration.json'])
    found = {path for path in files.values() if path.is_file()}
    source, checkpoint = _probe_source(probe)
    return found | {source, checkpoint}


def _probe_source(probe):
    """The probe's own predecessor registration and the checkpoint it continued."""
    continuation = probe['budget']['continuation']
    bridge = continuation.get('reconciliation')
    checkpoint = canonical_path(continuation['checkpoint'], exists=True)
    source = (canonical_path(bridge['source_registration'], exists=True) if bridge is not None
              else checkpoint.with_name('registration.json'))
    return source, checkpoint


def _settlement(files, result, pinned):
    """The settlement that decided the successor checkpoint: the deferred one, when `settle` applied it."""
    after = files['settlement_after_exit.json']
    settlement = result.get('settlement')
    if after.is_file():
        _require(isinstance(settlement, dict) and settlement.get('reason') == HANDLER_RUNNING,
                 'probe settlement after exit without a deferred settlement')
        later = read_json(pinned(None, str(after)))
        _require(isinstance(later, dict), 'probe settlement after exit is malformed')
        _require(later.get('result_sha256') == sha(files['result.json']),
                 'probe settlement after exit names another result')
        return later, True
    return settlement, False


def _reconciled(probe, identity, files, deferred):
    """Recompute the probe's reconciled checkpoint from its ledger and debit receipt (`settle_pending`)."""
    from .registration import _full_reservation_debit
    ledger_path, receipt_path = files['billing.json'], files['debit_receipt.json']
    ledger, receipt = read_json(ledger_path), read_json(receipt_path)
    attempt = f'{identity}:{ATTEMPT}'
    rows = ledger.get('requests')
    _require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), 'probe ledger is malformed')
    pending = [row for row in rows if row.get('status') != 'settled']
    _require(len(pending) == 1 and pending[0].get('status') == 'pending' and pending[0].get('attempt') == attempt,
             'a probe reconciliation resolves exactly its own one pending request')
    row = dict(pending[0])
    quote = probe['authorization']['full_reservation_debit']
    runtime = receipt.get('runtime_at_settlement')
    closed = (isinstance(runtime, dict) and runtime.get('unfinished_handlers') == 0
              and runtime.get('proxy_shutdown_complete') is True)
    _require(receipt.get('kind') == DEBIT_KIND and receipt.get('attempt') == attempt
             and receipt.get('request_id') == row.get('id')
             and receipt.get('previous_reservation_usd') == row.get('reserved_usd')
             and receipt.get('source_attempt_kind') == ATTEMPT
             and receipt.get('source_registration_sha256') == identity
             and receipt.get('source_ledger_sha256') == sha(ledger_path)
             and receipt.get('source_ledger_modified') is False
             and receipt.get('new_provider_requests') == 0
             and receipt.get('user_authorization') == {**quote, 'standing': True},
             'probe debit receipt does not bind the probe\'s pending request and standing authorization')
    # A handler still running could have held the request: either the proxy
    # closed with none running, or `settle` inferred closure after exit.
    _require(('closure_basis' in receipt) == deferred and (deferred or closed),
             'probe debit was applied without a closed runtime')
    cost = _full_reservation_debit(receipt, row)
    row.update(status='settled', cost_usd=row['reserved_usd'], settled_at=receipt['recorded_at'],
               settlement_basis=DEBIT_KIND, reconciliation_receipt_sha256=sha(receipt_path),
               accounting_observation_sha256=receipt['accounting_observation_sha256'],
               provider_charge_confirmed=False, provider_charge_usd=None, provider_usage_is_final=False,
               released_excess_reservation_usd='0', source_attempt_kind=ATTEMPT, source_attempt_outcome='stopped')
    expected = {**ledger, 'requests': [row if r.get('id') == row['id'] else r for r in rows],
                'reconciled_from': {'checkpoint_sha256': sha(ledger_path), 'receipt_sha256': sha(receipt_path),
                                    'request_id': row['id'], 'previous_status': 'pending',
                                    'budget_debit_usd': row['reserved_usd'], 'settlement_basis': DEBIT_KIND,
                                    'provider_charge_confirmed': False, 'source_attempt_completed': False}}
    _require(cost == Decimal(row['reserved_usd']), 'probe debit differs from its reservation')
    return expected


def validate_predecessor(manifest, *, require_pins=True):
    """Validate the link when the audit's predecessor is a probe; None otherwise."""
    try:
        probe = is_probe_predecessor(manifest)
    except _MALFORMED as error:
        raise BudgetStop('audit predecessor registration is malformed or unavailable') from error
    return validate_link(manifest, require_pins=require_pins) if probe else None


def validate_link(manifest, *, require_pins=True):
    try:
        return _validate_link(manifest, require_pins=require_pins)
    except _MALFORMED as error:
        raise BudgetStop('probe predecessor is malformed or unavailable') from error


def _validate_link(manifest, *, require_pins=True):
    """Validate the probe named by an audit's continuation; return its settled checkpoint.

    Every file read is pinned in the audit's registration, so a successor
    audit binds the exact link it follows. Preparation checks the same link
    before any pins exist (`require_pins=False`).
    """
    audit = manifest
    def pinned(_, value):
        return (_pinned(audit, value) if require_pins else canonical_path(value, exists=True))
    continuation = manifest['budget']['continuation']
    bridge = continuation.get('reconciliation')
    registration = pinned(manifest, str(predecessor_path(manifest)))
    files = _files(registration.parent)
    probe = read_json(registration)
    identity = sha(registration)
    _require(probe.get('kind') == KIND and type(probe.get('schema_version')) is int
             and probe['schema_version'] == 1 and registration.name == 'registration.json',
             'audit predecessor is not a transport probe registration')
    _require(isinstance(manifest.get('sequence_state'), str) and bool(manifest['sequence_state']),
             'audit names no sequence state to check its probe predecessor against')
    _require(probe.get('parent', {}).get('registration') == manifest['parent']['registration']
             and probe.get('sequence_state') == manifest['sequence_state']
             and canonical_path(probe['budget']['ledger_path']) == files['billing.json'],
             'probe predecessor names another origin, sequence or ledger')
    ledger_path = pinned(manifest, str(files['billing.json']))
    result_path = pinned(manifest, str(files['result.json']))
    ledger, result = read_json(ledger_path), read_json(result_path)
    _require(isinstance(ledger, dict) and isinstance(result, dict), 'probe ledger or result is malformed')
    _require(result.get('kind') == RESULT_KIND and result.get('registration_sha256') == identity
             and result.get('tip_claimed') is True,
             'probe predecessor did not claim the tip it would hand on')
    # One hop further: the probe continued an audit on the same origin, and
    # its ledger carries that checkpoint's rows unchanged.
    source_path, before = _probe_source(probe)
    source_path, before = pinned(manifest, str(source_path)), pinned(manifest, str(before))
    source = read_json(source_path)
    _require(source.get('kind') == AUDIT_KIND
             and sha(source['parent']['registration']) == sha(manifest['parent']['registration']),
             'probe predecessor did not follow an audit of this origin')
    probe_pins = probe.get('pinned_files', {})
    _require(probe_pins.get(str(source_path)) == sha(source_path)
             and probe_pins.get(str(before)) == sha(before) == probe['budget']['continuation']['sha256'],
             'probe predecessor\'s own predecessor changed since the probe was registered')
    carried = read_json(before)['requests']
    rows = ledger.get('requests')
    _require(ledger.get('manifest_sha256') == identity
             and isinstance(ledger.get('continued_from'), dict)
             and ledger['continued_from'].get('checkpoint_sha256') == probe['budget']['continuation']['sha256']
             and isinstance(rows, list) and canonical_json(rows[:len(carried)]) == canonical_json(carried)
             and all(isinstance(row, dict) and row.get('attempt') == f'{identity}:{ATTEMPT}'
                     for row in rows[len(carried):]) and len(rows) - len(carried) <= 1,
             'probe ledger does not carry its predecessor checkpoint and at most its one request')
    for field in ('additional_cap_usd', 'attempt_cap_usd'):
        _require(ledger.get(field) == read_json(before).get(field), 'probe ledger changes the lineage caps')
    settlement, deferred = _settlement(files, result, pinned)
    status = settlement.get('status') if isinstance(settlement, dict) else None
    checkpoint = canonical_path(continuation['checkpoint'], exists=True)
    if status == 'settled':
        _require(bridge is None and checkpoint == ledger_path
                 and all(row.get('status') == 'settled' for row in rows),
                 'a settled probe is continued from its own ledger, with no reconciliation')
        state = ledger
    elif status == 'reconciled':
        expected_bridge = {'source_registration': str(registration), 'source_ledger': str(ledger_path),
                           'receipt': str(files['debit_receipt.json']), 'result': str(result_path)}
        _require(bridge == expected_bridge and checkpoint == files['reconciled_billing.json']
                 and settlement.get('path') == str(checkpoint) and settlement.get('sha256') == sha(checkpoint),
                 'a reconciled probe is continued from the checkpoint its settlement wrote')
        pinned(manifest, str(files['debit_receipt.json']))
        expected = _reconciled(probe, identity, files, deferred)
        state = read_json(checkpoint)
        _require(canonical_json(state) == canonical_json(expected),
                 'probe reconciled checkpoint changes its ledger beyond the one debit')
    else:
        raise BudgetStop('probe predecessor has no settled checkpoint; its settlement needs a person')
    _require(sha(checkpoint) == continuation['sha256'], 'probe checkpoint differs from the registered continuation')
    return deepcopy(state)
