"""Settle a stopped audit's one unconfirmed charge under the standing authorization (#2467).

When a native audit stops with one request whose charge the provider never
confirmed, the next registration can continue only from a reconciled
checkpoint. On 2026-09-25 the maintainer authorized such charges, once for all
stops, at their whole reservation with the provider fee left unknown. The
authorization is the committed record `STANDING_AUTHORIZATION`, pinned here by
its hash.

This tool writes the receipt and the reconciled checkpoint in exactly the form
`registration.validate_audit_reconciliation` recomputes. It runs that
validator on them before publishing. Holding the lineage's sequence lock, it
first requires:
- the stopped audit to be the live tip, so no successor has continued from it;
- no reconciliation of that audit to have been recorded before.

The recording is an exclusive marker beside the sequence state. It is written
after the staged files validate and before they are published, so a crash
leaves a marker that names what to inspect. Only this tool writes markers: a
reconciliation made any other way, such as audit27's by hand, carries none, so
do not run the tool on a stop that already has one. The stopped audit's
registration, ledger, result and evidence are never modified.

  python -m audit_controls.reconcile_stopped --registration STOPPED/registration.json --out NEW_DIR

The printed paths and hashes are what the next preparation passes as
`--continuation-checkpoint`, `--continuation-source-registration` and
`--continuation-reconciliation-receipt`. The tool never claims the sequence
and never contacts a provider.
"""
import argparse
import copy
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from filelock import Timeout

from budgeted_cborg import BudgetStop, attempt_identity
from . import registration as r

KIND = 'user_authorized_full_reservation_debit'
AUTHORIZATION_KIND = 'standing_full_reservation_debit_authorization'
STANDING_AUTHORIZATION = Path(__file__).resolve().with_name('standing_full_reservation_debit_2026-09-25.json')
STANDING_AUTHORIZATION_SHA256 = '5e5baa54f34e359e07a6ffb2ad8743bf1aabe41950e07dc9f672f9479b9d578d'
QUOTE_FIELDS = ('exact_response', 'quoted_request', 'recorded_at')
MARKERS = 'reconciliations'


def standing_authorization():
    """The committed record of the maintainer's standing authorization, exactly as pinned."""
    path, expected = STANDING_AUTHORIZATION, STANDING_AUTHORIZATION_SHA256
    if path.is_symlink() or not path.is_file() or r.sha(path) != expected:
        raise BudgetStop('the standing authorization record is missing or changed')
    value = r.read_json(path)
    if (not isinstance(value, dict) or set(value) != {'kind', *QUOTE_FIELDS} or value['kind'] != AUTHORIZATION_KIND
            or any(not isinstance(value[k], str) or not value[k].strip() for k in QUOTE_FIELDS)):
        raise BudgetStop('standing authorization needs its kind, exact response, quoted request and time')
    return value, {'path': str(path), 'sha256': expected}


def request_folder(attempt_dir, request_id):
    """The one evidence folder of the pending request, in a single or batch attempt."""
    matches = []
    for root, directories, _ in os.walk(attempt_dir, followlinks=False):
        for name in directories:
            if name == request_id and Path(root).name == 'requests':
                matches.append(Path(root) / name)
    if len(matches) != 1 or matches[0].is_symlink():
        raise BudgetStop('the pending request has no single evidence folder')
    return matches[0]


def evidence(folder, row):
    """The request bytes the ledger names, and its provider-side record."""
    request = folder / 'request.json'
    if request.is_symlink() or not request.is_file() or r.sha(request) != row['request_sha256']:
        raise BudgetStop('the evidence folder does not hold the pending request')
    for name in ('http_status.json', 'admission.json'):
        path = folder / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise BudgetStop('the pending request\'s evidence is not a regular file')
        if path.is_file():
            return {'file': name, 'sha256': r.sha(path)}
    raise BudgetStop('the pending request has no accounting observation')


def _write(path, value):
    """Exclusive, durable write of a new file; a failed write removes what it created."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(json.dumps(value, indent=2) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


def _sync(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def previous_reconciliation(marker):
    """Why an earlier run blocks this one, naming whether it published."""
    try:
        record = r.read_json(marker)
        out = Path(record['out'])
        published = all((out / name).is_file() and r.sha(out / name) == record[key] for name, key in (
            ('charge_reconciliation_receipt.json', 'receipt_sha256'), ('reconciled_billing.json', 'checkpoint_sha256')))
    except Exception:
        return f'this stopped audit has an unreadable reconciliation marker; inspect {marker}'
    if published:
        return f'this stopped audit was already reconciled; its checkpoint is in {out}'
    return (f'an earlier reconciliation of this stopped audit was recorded but not published; '
            f'inspect {marker} and its staged files in {record.get("staged")}')


def reconcile(source_path, out, *, recorded_at=None):
    source_path = r.canonical_path(str(Path(source_path).resolve()), exists=True)
    if Path(out).is_symlink():
        raise BudgetStop('the reconciliation directory is a symlink')
    out = Path(out).resolve()
    if source_path.parent == out or source_path.parent in out.parents:
        raise BudgetStop('the reconciliation is written outside the stopped audit\'s tree')
    source = r.read_json(source_path)
    if source.get('kind') != 'd4d_native_audit_continuation':
        raise BudgetStop('only a native audit registration is reconciled here')
    quote, reference = standing_authorization()
    source_sha, job = r.sha(source_path), source['job']
    ledger_path = r.canonical_path(source['budget']['ledger_path'], exists=True)
    result_path = Path(job['attempt_dir']) / 'result.json'
    state_path = r.canonical_path(source['sequence_state'], exists=True)
    markers = state_path.parent / MARKERS
    if out == state_path.parent or state_path.parent in out.parents:
        raise BudgetStop('the reconciliation is written outside the sequence state\'s directory')
    if out.exists():
        # A rerun into the same directory says what an earlier run left.
        earlier = markers / f'{source_sha}.json'
        raise BudgetStop(previous_reconciliation(earlier) if earlier.exists() else
                         'reconciliation directory already exists; a reconciliation is written once')
    try:
        lock = r.SequenceLock(str(state_path) + '.lock').acquire(timeout=0)
    except Timeout as error:
        raise BudgetStop('the sequence lock is held; another registration or reconciliation is running') from error
    with lock:
        tip = r.read_json(state_path)
        if tip.get('registration_sha256') != source_sha or tip.get('ledger_path') != str(ledger_path):
            raise BudgetStop('the stopped audit is no longer the sequence tip; a successor has continued from it')
        # The marker directory is checked before anything is staged, so a
        # refusal there cannot leave a validated pair without a marker.
        markers.mkdir(exist_ok=True)
        if markers.is_symlink() or not markers.is_dir() or not os.access(markers, os.W_OK):
            raise BudgetStop('the reconciliation marker directory is not a writable directory')
        marker = markers / f'{source_sha}.json'
        if marker.exists() or marker.is_symlink():
            raise BudgetStop(previous_reconciliation(marker))
        ledger, result = r.read_json(ledger_path), r.read_json(result_path)
        pending = [row for row in ledger['requests'] if row.get('status') != 'settled']
        if (len(pending) != 1 or pending[0].get('status') != 'pending'
                or pending[0].get('attempt') != attempt_identity(source_sha, job['id'])
                or result.get('unresolved_requests') != [pending[0]['id']]):
            raise BudgetStop('the stopped audit does not have exactly one pending charge of its own')
        row = pending[0]
        observation = evidence(request_folder(job['attempt_dir'], row['id']), row)
        recorded_at = recorded_at or datetime.now(timezone.utc).isoformat()
        receipt = {'kind': KIND, 'source_attempt_kind': 'phase3_audit_only',
                   'source_registration_sha256': source_sha, 'source_ledger_sha256': r.sha(ledger_path),
                   'stopped_result_sha256': r.sha(result_path), 'request_id': row['id'], 'attempt': row['attempt'],
                   'request_sha256': row['request_sha256'], 'previous_reservation_usd': row['reserved_usd'],
                   'budget_debit_usd': row['reserved_usd'], 'released_excess_reservation_usd': '0',
                   'provider_charge_confirmed': False, 'provider_charge_usd': None, 'provider_usage_is_final': False,
                   'source_attempt_completed': False, 'scientific_acceptance': False,
                   'source_ledger_modified': False, 'new_provider_requests': 0,
                   'accounting_observation_sha256': observation['sha256'], 'accounting_observation': observation,
                   'recorded_at': recorded_at,
                   'user_authorization': {**{k: quote[k] for k in QUOTE_FIELDS}, 'standing': True,
                                          'source_record': reference}}
        # Stage and validate first: a refusal leaves nothing behind.
        scratch = Path(tempfile.mkdtemp(prefix='.' + out.name + '-', dir=out.parent)).resolve()
        try:
            staged = {'receipt': scratch / 'charge_reconciliation_receipt.json',
                      'checkpoint': scratch / 'reconciled_billing.json'}
            _write(staged['receipt'], receipt)
            reconciled = copy.deepcopy(ledger)
            target = next(x for x in reconciled['requests'] if x['id'] == row['id'])
            target.update(status='settled', cost_usd=row['reserved_usd'], settled_at=recorded_at,
                          settlement_basis=KIND, reconciliation_receipt_sha256=r.sha(staged['receipt']),
                          accounting_observation_sha256=observation['sha256'],
                          provider_charge_confirmed=False, provider_charge_usd=None, provider_usage_is_final=False,
                          released_excess_reservation_usd='0', source_attempt_kind='phase3_audit_only',
                          source_attempt_outcome='stopped')
            reconciled['reconciled_from'] = {'checkpoint_sha256': r.sha(ledger_path),
                                             'receipt_sha256': r.sha(staged['receipt']), 'request_id': row['id'],
                                             'previous_status': 'pending', 'budget_debit_usd': row['reserved_usd'],
                                             'settlement_basis': KIND, 'provider_charge_confirmed': False,
                                             'source_attempt_completed': False}
            _write(staged['checkpoint'], reconciled)
            # The successor's own check. Neither file names its own path, so
            # the staged bytes are the published bytes.
            verify(source, source_path, ledger_path, result_path, staged['receipt'], staged['checkpoint'])
            hashes = {name: r.sha(path) for name, path in staged.items()}
            # The output directory is created before the marker, so a
            # directory someone else made meanwhile refuses without a marker.
            os.mkdir(out)
        except BaseException:
            shutil.rmtree(scratch, ignore_errors=True)
            raise
        # Record the reconciliation before publishing it, so a crash from
        # here fails closed: the marker names what a person must inspect.
        try:
            _write(marker, {'source_registration': str(source_path), 'source_registration_sha256': source_sha,
                            'request_id': row['id'], 'out': str(out), 'staged': str(scratch),
                            'checkpoint_sha256': hashes['checkpoint'], 'receipt_sha256': hashes['receipt'],
                            'recorded_at': recorded_at})
        except BaseException:
            try:
                os.rmdir(out)
            except OSError:
                pass
            shutil.rmtree(scratch, ignore_errors=True)
            raise
        _sync(markers)
        final = {name: out / path.name for name, path in staged.items()}
        for name in staged:
            os.link(staged[name], final[name], follow_symlinks=False)
        _sync(out)
        shutil.rmtree(scratch, ignore_errors=True)
    if any(r.sha(final[name]) != hashes[name] for name in final):
        raise BudgetStop('the published reconciliation differs from the validated bytes')
    return {'checkpoint': str(final['checkpoint']), 'checkpoint_sha256': hashes['checkpoint'],
            'cost_usd': str(sum((Decimal(x['cost_usd']) for x in reconciled['requests']), Decimal(0))),
            'source_registration': str(source_path), 'receipt': str(final['receipt']),
            'receipt_sha256': hashes['receipt'], 'request_id': row['id'], 'budget_debit_usd': row['reserved_usd'],
            'marker': str(marker)}


#: The registration block that applies the standing debit when the audit stops (#2467).
SELECTION_KIND = 'standing_full_reservation_debit_at_stop_v1'
SELECTION_KEY = 'automatic_stop_reconciliation'
#: Beside the stopped audit's own directory: outside its tree and, for every
#: registration layout in use, outside the sequence state's directory.
AUTOMATIC_SUFFIX = '_stop_reconciliation'


def selection():
    """The exact block a registration carries to opt in; it names the pinned authorization record."""
    _, reference = standing_authorization()
    return {'kind': SELECTION_KIND, 'authorization': reference}


def validated_selection(value):
    if value != selection():
        raise BudgetStop('automatic stop reconciliation must name the pinned standing authorization exactly')
    return dict(value)


def automatic_out(registration_path):
    folder = Path(registration_path).resolve().parent
    return folder.with_name(folder.name + AUTOMATIC_SUFFIX)


def reconcile_at_stop(registration_path, manifest):
    """Apply the standing debit to an audit that just stopped, once its sequence lock is released.

    Never raises: a stop the debit does not cover, or any refusal, is
    reported and left to a person, exactly as without this selection. The
    reviewed `reconcile` does every check, including the successor's own
    validator, before it publishes anything.
    """
    try:
        validated_selection(manifest.get(SELECTION_KEY))
        result_path = Path(manifest['job']['attempt_dir']) / 'result.json'
        if not result_path.is_file():
            return {'status': 'not_applicable', 'reason': 'the audit wrote no result'}
        result = r.read_json(result_path)
        if result.get('status') != 'stopped' or len(result.get('unresolved_requests') or []) != 1:
            return {'status': 'not_applicable', 'reason': 'the stop left no single unconfirmed charge'}
        return {'status': 'reconciled', **reconcile(registration_path, automatic_out(registration_path))}
    except BudgetStop as error:
        return {'status': 'refused', 'reason': str(error)}
    except Exception as error:
        return {'status': 'refused', 'reason': type(error).__name__}


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
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    print(json.dumps(reconcile(args.registration, args.out), indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
