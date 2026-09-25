"""Settle a stopped audit's one unconfirmed charge under a standing authorization (#2467).

When a native audit stops with one request whose charge the provider never
confirmed, the next registration can continue only from a reconciled
checkpoint. The maintainer has authorized that charge, once for all such
stops, at its whole reservation with the provider fee left unknown. This tool
writes the receipt and the reconciled checkpoint in exactly the form
`registration.validate_audit_reconciliation` recomputes. It then runs that
validator on them and publishes the pair only if it accepts. The stopped
audit's ledger, result and evidence are never modified.

  python -m audit_controls.reconcile_stopped --registration STOPPED/registration.json \\
      --authorization STANDING.json --out NEW_DIR

The printed paths and hashes are what the next preparation passes as
`--continuation-checkpoint`, `--continuation-source-registration` and
`--continuation-reconciliation-receipt`. The tool neither claims the sequence
nor contacts a provider.
"""
import argparse
import copy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import shutil
import sys
import tempfile

from budgeted_cborg import BudgetStop, attempt_identity
from . import registration as r

KIND = 'user_authorized_full_reservation_debit'
AUTHORIZATION_KIND = 'standing_full_reservation_debit_authorization'
QUOTE_FIELDS = ('exact_response', 'quoted_request', 'recorded_at')


def standing_authorization(path):
    value = r.read_json(path)
    if (not isinstance(value, dict) or set(value) != {'kind', *QUOTE_FIELDS} or value['kind'] != AUTHORIZATION_KIND
            or any(not isinstance(value[k], str) or not value[k].strip() for k in QUOTE_FIELDS)):
        raise BudgetStop('standing authorization needs its kind, exact response, quoted request and time')
    return value


def request_folder(attempt_dir, request_id):
    """The one evidence folder of the pending request, in a single or batch attempt."""
    matches = [p for p in Path(attempt_dir).rglob(request_id)
               if p.is_dir() and not p.is_symlink() and p.parent.name == 'requests']
    if len(matches) != 1:
        raise BudgetStop('the pending request has no single evidence folder')
    return matches[0]


def observation(folder):
    """The provider-side record of the stopped request: its HTTP status where one arrived."""
    for name in ('http_status.json', 'admission.json'):
        if (folder / name).is_file():
            return r.sha(folder / name)
    raise BudgetStop('the pending request has no accounting observation')


def reconcile(source_path, authorization_path, out, *, recorded_at=None):
    source_path = r.canonical_path(str(Path(source_path).resolve()), exists=True)
    out = Path(out).resolve()
    if out.exists():
        raise BudgetStop('reconciliation directory already exists; a reconciliation is written once')
    source = r.read_json(source_path)
    if source.get('kind') != 'd4d_native_audit_continuation':
        raise BudgetStop('only a native audit registration is reconciled here')
    quote = standing_authorization(authorization_path)
    source_sha, job = r.sha(source_path), source['job']
    ledger_path = r.canonical_path(source['budget']['ledger_path'], exists=True)
    result_path = Path(job['attempt_dir']) / 'result.json'
    ledger, result = r.read_json(ledger_path), r.read_json(result_path)
    pending = [row for row in ledger['requests'] if row.get('status') != 'settled']
    if (len(pending) != 1 or pending[0].get('status') != 'pending'
            or pending[0].get('attempt') != attempt_identity(source_sha, job['id'])
            or result.get('unresolved_requests') != [pending[0]['id']]):
        raise BudgetStop('the stopped audit does not have exactly one pending charge of its own')
    row = pending[0]
    folder = request_folder(job['attempt_dir'], row['id'])
    recorded_at = recorded_at or datetime.now(timezone.utc).isoformat()
    receipt = {'kind': KIND, 'source_attempt_kind': 'phase3_audit_only',
               'source_registration_sha256': source_sha, 'source_ledger_sha256': r.sha(ledger_path),
               'stopped_result_sha256': r.sha(result_path), 'request_id': row['id'], 'attempt': row['attempt'],
               'request_sha256': row['request_sha256'], 'previous_reservation_usd': row['reserved_usd'],
               'budget_debit_usd': row['reserved_usd'], 'released_excess_reservation_usd': '0',
               'provider_charge_confirmed': False, 'provider_charge_usd': None, 'provider_usage_is_final': False,
               'source_attempt_completed': False, 'scientific_acceptance': False, 'source_ledger_modified': False,
               'new_provider_requests': 0, 'accounting_observation_sha256': observation(folder),
               'recorded_at': recorded_at,
               'user_authorization': {'exact_response': quote['exact_response'],
                                      'quoted_request': quote['quoted_request'],
                                      'recorded_at': quote['recorded_at'], 'standing': True,
                                      'source_record': str(Path(authorization_path).resolve())}}
    scratch = Path(tempfile.mkdtemp(prefix='.' + out.name + '-', dir=out.parent)).resolve()
    try:
        receipt_path = scratch / 'charge_reconciliation_receipt.json'
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
        reconciled = copy.deepcopy(ledger)
        target = next(x for x in reconciled['requests'] if x['id'] == row['id'])
        target.update(status='settled', cost_usd=row['reserved_usd'], settled_at=recorded_at,
                      settlement_basis=KIND, reconciliation_receipt_sha256=r.sha(receipt_path),
                      accounting_observation_sha256=receipt['accounting_observation_sha256'],
                      provider_charge_confirmed=False, provider_charge_usd=None, provider_usage_is_final=False,
                      released_excess_reservation_usd='0', source_attempt_kind='phase3_audit_only',
                      source_attempt_outcome='stopped')
        reconciled['reconciled_from'] = {'checkpoint_sha256': r.sha(ledger_path), 'receipt_sha256': r.sha(receipt_path),
                                         'request_id': row['id'], 'previous_status': 'pending',
                                         'budget_debit_usd': row['reserved_usd'], 'settlement_basis': KIND,
                                         'provider_charge_confirmed': False, 'source_attempt_completed': False}
        checkpoint_path = scratch / 'reconciled_billing.json'
        checkpoint_path.write_text(json.dumps(reconciled, indent=2) + '\n')
        # The successor's own check. Neither file names its own path, so the
        # staged bytes are the published bytes.
        verify(source, source_path, ledger_path, result_path, receipt_path, checkpoint_path)
        scratch.rename(out)
    except BaseException:
        shutil.rmtree(scratch, ignore_errors=True)
        raise
    checkpoint, receipt_final = out / 'reconciled_billing.json', out / 'charge_reconciliation_receipt.json'
    return {'checkpoint': str(checkpoint), 'checkpoint_sha256': r.sha(checkpoint),
            'cost_usd': str(sum((Decimal(x['cost_usd']) for x in reconciled['requests']), Decimal(0))),
            'source_registration': str(source_path), 'receipt': str(receipt_final),
            'receipt_sha256': r.sha(receipt_final), 'request_id': row['id'], 'budget_debit_usd': row['reserved_usd']}


def verify(source, source_path, ledger_path, result_path, receipt_path, checkpoint_path):
    """Run `validate_audit_reconciliation` exactly as the next registration will."""
    pins = {str(p): r.sha(p) for p in (source_path, ledger_path, result_path, receipt_path, checkpoint_path)}
    if 'audit_batches' in source:
        from .batch_native import require_closed_batch_runtime
        pins.update(source['pinned_files'])
        pins.update({str(p): r.sha(p) for p in require_closed_batch_runtime(source, r.read_json(result_path))})
    candidate = {'parent': {'registration': source['parent']['registration']},
                 'budget': {'continuation': {'checkpoint': str(checkpoint_path), 'sha256': r.sha(checkpoint_path),
                                             'reconciliation': {'source_registration': str(source_path),
                                                                'source_ledger': str(ledger_path),
                                                                'receipt': str(receipt_path),
                                                                'result': str(result_path)}}},
                 'pinned_files': pins}
    r.validate_audit_reconciliation(candidate)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--registration', required=True)
    parser.add_argument('--authorization', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    print(json.dumps(reconcile(args.registration, args.authorization, args.out), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
