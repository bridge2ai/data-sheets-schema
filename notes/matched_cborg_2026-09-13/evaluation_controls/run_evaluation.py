"""Run exactly one reviewed evaluation job; preserve every attempted result.

No batch expansion, retries, or independent acceptance is performed here.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

from filelock import FileLock

from registration import (BudgetStop, EvaluationContext, NATIVE_STYLES, canonical_digest,
    canonical_path, claim_sequence, read_json, sequence_path, sha, verify_dependencies,
    verify_manifest, verify_sequence)
from budgeted_cborg import attempt_identity, open_ledger, write_new


class OwnedLedger:
    """Keep shared admission checks at reservation and settlement boundaries."""
    def __init__(self, owner):
        self.owner = owner

    def __getattr__(self, name):
        return getattr(self.owner.ledger, name)

    def reserve(self, *args, **kwargs):
        return self.owner.reserve(*args, **kwargs)

    def settle(self, *args, **kwargs):
        with self.owner._guard:
            self.owner.verify_admission()
            return self.owner.ledger.settle(*args, **kwargs)


@contextmanager
def accounting_owner(manifest, registration_path, manifest_sha256):
    if manifest.get('schema_version') == 2:
        from continuation_sequence import PROTOCOL, owned_sequence
        if manifest.get('budget_sequence', {}).get('protocol') != PROTOCOL:
            raise BudgetStop('composite evaluation requires canonical shared accounting')
        with owned_sequence(manifest, registration_path, manifest_sha256) as owner:
            yield OwnedLedger(owner), owner.state_path, owner.state_sha, owner.verify_admission
    else:
        sequence = sequence_path(manifest)
        sequence.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(sequence) + '.lock', timeout=0):
            sequence_sha256 = claim_sequence(manifest, manifest_sha256)
            yield (open_ledger(manifest, manifest_sha256), sequence, sequence_sha256,
                   lambda: verify_sequence(manifest, manifest_sha256, sequence_sha256))


def now():
    return datetime.now(timezone.utc).isoformat()


def verify_review(path, digest, manifest, manifest_sha256, job_id):
    if sha(path) != digest:
        raise BudgetStop('evaluation launch review changed')
    review = read_json(path)
    if (review.get('verdict') != 'approve' or review.get('registration_sha256') != manifest_sha256 or
        review.get('ci_conclusion') != 'success' or review.get('repository_commit') != manifest['repository_commit'] or
        job_id not in review.get('allowed_jobs', [])):
        raise BudgetStop('this evaluation registration/job requires independent review and passing CI')


def run_job(registration_path, review_path, job_id, *, adapter=None):
    """The adapter injection is only for offline lifecycle tests, never a CLI option."""
    registration_path = canonical_path(str(Path(registration_path)), exists=True)
    review_path = canonical_path(str(Path(review_path)), exists=True)
    manifest, manifest_sha256 = read_json(registration_path), sha(registration_path)
    review_sha256 = sha(review_path)
    jobs = verify_manifest(manifest, registration_path, manifest_sha256)
    if job_id not in jobs:
        raise BudgetStop('evaluation job is absent from the registration')
    registered_job = jobs[job_id]
    verify_review(review_path, review_sha256, manifest, manifest_sha256, job_id)
    bound_job, dependencies = verify_dependencies(manifest, manifest_sha256, registered_job)
    output = canonical_path(registered_job['output'])
    attempt = canonical_path(manifest['attempts_dir']) / job_id
    # A lock spanning validation, provider shutdown and publication keeps a
    # second process from opening a parallel paid job on this sequence.
    if attempt.exists() or output.exists():
        raise BudgetStop('evaluation attempt or output already exists; never resume or overwrite')
    with accounting_owner(manifest, registration_path, manifest_sha256) as (ledger, sequence, sequence_sha256, verify_owner):
        if attempt.exists() or output.exists():
            raise BudgetStop('evaluation attempt or output already exists; never resume or overwrite')
        billing_attempt = attempt_identity(manifest_sha256, job_id)
        ledger.require_resolved(billing_attempt)

        def verify_all():
            verify_owner()
            verify_manifest(manifest, registration_path, manifest_sha256)
            verify_review(review_path, review_sha256, manifest, manifest_sha256, job_id)
            current_bound, current_dependencies = verify_dependencies(manifest, manifest_sha256, registered_job)
            if current_bound != bound_job or current_dependencies != dependencies:
                raise BudgetStop('accepted evaluation dependency changed during the attempt')

        verify_all()
        attempt.mkdir(parents=True, exist_ok=False)
        canonical_path(bound_job['candidate']).parent.mkdir()
        receipt = {'version': 1, 'job_id': job_id, 'registration_sha256': manifest_sha256,
            'registered_job_sha256': canonical_digest(registered_job),
            'bound_job_sha256': canonical_digest(bound_job), 'dependencies': dependencies,
            'review_sha256': review_sha256, 'input_sha256': bound_job['input_sha256'],
            'sequence_state': str(sequence), 'sequence_state_sha256': sequence_sha256,
            'style': bound_job['style'], 'variant': bound_job['variant'],
            'canary_group': bound_job['canary_group'], 'rating': bound_job['rating'],
            'billing_attempt': billing_attempt, 'started_at': now(), 'status': 'incomplete'}
        write_new(attempt / 'started.json', receipt)
        context = EvaluationContext(manifest, manifest_sha256, bound_job, attempt, ledger, verify_all)
        if adapter is None:
            if bound_job['style'] in NATIVE_STYLES:
                from native import execute_job
            else:
                from api import execute_job
            adapter = execute_job
        error, result = None, None
        try:
            result = adapter(context)
            verify_all()
            ledger.require_resolved(billing_attempt)
            state = read_json(ledger.path)
            rows = [row for row in state['requests'] if row['attempt'] == billing_attempt]
            if not rows or any(row['status'] != 'settled' for row in rows):
                raise BudgetStop('evaluation has no fully settled model request accounting')
            if result.get('validation', {}).get('passed') is not True:
                raise BudgetStop('evaluation adapter did not validate its candidate')
            if manifest.get('schema_version') == 2:
                from adapter_closure import require_closed
                require_closed(result.get('runtime'), bound_job['style'])
            candidate = canonical_path(str(result['candidate_path']), exists=True)
            if (str(candidate) != bound_job['candidate'] or not candidate.is_file() or candidate.is_symlink() or
                candidate.stat().st_nlink != 1):
                raise BudgetStop('evaluation candidate differs from its isolated registered path')
            candidate_sha256 = sha(candidate)
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.resolve() != output:
                raise BudgetStop('evaluation output directory was redirected')
            with output.open('xb') as stream:
                stream.write(candidate.read_bytes())
            if sha(output) != candidate_sha256:
                raise BudgetStop('published evaluation differs from the validated candidate')
            verify_all()
            receipt.update(status='completed_pending_independent_review', candidate=str(candidate),
                candidate_sha256=candidate_sha256, output=str(output), output_sha256=candidate_sha256,
                validation=result['validation'], runtime=result.get('runtime'), evidence=result.get('evidence'),
                model_requests=len(rows), cost_usd=str(sum((Decimal(row['cost_usd']) for row in rows), Decimal(0))))
        except BaseException as exc:
            error = exc
            # Local BudgetStop explanations are safe; raw provider exception
            # text can carry request headers and is never copied to receipts.
            reason = str(exc) if isinstance(exc, BudgetStop) else type(exc).__name__
            receipt.update(status='stopped', error_type=type(exc).__name__, reason=reason)
            runtime = getattr(exc, 'evaluation_runtime', None)
            if runtime is None and isinstance(result, dict):
                runtime = result.get('runtime')
            if runtime is not None:
                receipt['runtime'] = runtime
            ledger.stop_attempt(billing_attempt, reason)
        finally:
            state = read_json(ledger.path)
            rows = [row for row in state['requests'] if row['attempt'] == billing_attempt]
            receipt.update(finished_at=now(), model_requests_admitted=len(rows),
                unresolved_requests=[row['id'] for row in rows if row['status'] != 'settled'])
            write_new(attempt / 'result.json', receipt)
        if error is not None:
            raise error
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--job', required=True)
    args = parser.parse_args()
    run_job(args.registration, args.review, args.job)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
