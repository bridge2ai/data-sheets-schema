"""Later local process closure never rewrites the stopped runtime snapshot (#2136).

For legacy launches without host identifiers, same-host provenance is an explicit
independent review assertion, not a machine identity inferred from a path or PID.
The validator checks its exact evidence bindings and chronology, not the physical
truth of that assertion. Registration review must assess the provenance itself.
"""
from datetime import datetime, timezone
import re
from uuid import UUID

from .registration import BudgetStop, attempt_identity, canonical_path, pinned, read_json, sha


def descriptor_path(value):
    if (not isinstance(value, dict) or set(value) != {'path', 'sha256'} or
            not isinstance(value['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', value['sha256'])):
        raise BudgetStop('runtime closure evidence needs an exact path and SHA-256')
    try:
        path = canonical_path(value['path'], exists=True)
        if not path.is_file() or sha(path) != value['sha256']:
            raise BudgetStop('runtime closure evidence changed')
    except OSError as error:
        raise BudgetStop('runtime closure evidence is unavailable') from error
    return path


def closure_paths(receipt):
    """Used by offline preparation as well as admission; no new CLI override."""
    if 'runtime_closure' not in receipt:
        return set()
    path = descriptor_path(receipt['runtime_closure'])
    proof = read_json(path)
    if not isinstance(proof, dict):
        raise BudgetStop('runtime closure proof must be an object')
    return {path, *(descriptor_path(proof.get(key)) for key in ('observation', 'launch_observation'))}


def timestamp(value):
    try:
        if not isinstance(value, str):
            raise ValueError('not text')
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError('timezone missing')
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError) as error:
        raise BudgetStop('runtime closure requires timezone-aware timestamps') from error


def require_closed_runtime(manifest, source_paths, source_registration, result, receipt):
    """Gate both financial variants; return supplemental provenance hash or None."""
    if 'audit_batches' in source_registration:
        from .batch_native import require_closed_batch_runtime
        for value in source_registration['pinned_files']:
            pinned(manifest, value, source_registration['pinned_files'][value])
        for path in require_closed_batch_runtime(source_registration, result):
            pinned(manifest, str(path))
    runtime = result.get('runtime')
    if (not isinstance(runtime, dict) or runtime.get('proxy_shutdown_complete') is not True or
            ('proxy_initialized' in runtime and runtime['proxy_initialized'] is not True) or
            type(runtime.get('unfinished_handlers')) is not int or runtime['unfinished_handlers'] < 0):
        raise BudgetStop('audit reconciliation needs a closed runtime or completed frozen shutdown evidence')
    if 'runtime_closure' not in receipt:
        if runtime['unfinished_handlers'] != 0:
            raise BudgetStop('audit reconciliation needs a closed runtime; later closure evidence is missing')
        return None
    for path in closure_paths(receipt):
        pinned(manifest, str(path))
    path = descriptor_path(receipt['runtime_closure'])
    proof = read_json(path)
    keys = {'schema_version', 'kind', 'source_registration_sha256', 'source_ledger_sha256',
            'stopped_result_sha256', 'job_id', 'billing_attempt', 'execution_repository',
            'execution_commit', 'observation', 'launch_observation', 'review'}
    source_sha = sha(source_paths['source_registration'])
    job = source_registration['job']
    if (set(proof) != keys or type(proof['schema_version']) is not int or proof['schema_version'] != 1 or
            proof['kind'] != 'independently_reviewed_host_reboot_closure' or
            proof['source_registration_sha256'] != source_sha or
            proof['source_ledger_sha256'] != sha(source_paths['source_ledger']) or
            proof['stopped_result_sha256'] != sha(source_paths['result']) or
            proof['job_id'] != job['id'] or proof['billing_attempt'] != attempt_identity(source_sha, job['id']) or
            not isinstance(proof['execution_repository'], str) or not proof['execution_repository'] or
            not isinstance(proof['execution_commit'], str) or not re.fullmatch(r'[0-9a-f]{40}', proof['execution_commit']) or
            proof['execution_repository'] != source_registration.get('repository') or
            proof['execution_commit'] != source_registration.get('repository_commit')):
        raise BudgetStop('runtime closure does not bind the exact stopped execution')
    canonical_path(proof['execution_repository'])  # The old checkout may have vanished during reboot.
    review = proof['review']
    review_keys = {'verdict', 'reviewer', 'observer', 'reviewed_at', 'same_execution_host',
                   'host_identity_basis', 'historical_host_identity', 'basis'}
    if (not isinstance(review, dict) or set(review) != review_keys or review['verdict'] != 'accept' or
            review['same_execution_host'] is not True or
            review['host_identity_basis'] != 'independently_reviewed_local_provenance' or
            review['historical_host_identity'] != 'not_recorded' or
            any(not isinstance(review[key], str) or not review[key].strip()
                for key in ('reviewer', 'observer', 'basis')) or
            any(review[key] != review[key].strip() for key in ('reviewer', 'observer')) or
            review['reviewer'].casefold() == review['observer'].casefold()):
        raise BudgetStop('runtime closure lacks independent same-host provenance review')
    launch = read_json(descriptor_path(proof['launch_observation']))
    if (not isinstance(launch, dict) or launch.get('registration_sha256') != source_sha or
            launch.get('job_id') != job['id'] or launch.get('launch_observed') is not True or
            launch.get('execution_repository') != proof['execution_repository'] or
            launch.get('repository_commit') != proof['execution_commit']):
        raise BudgetStop('runtime closure launch observation differs from the stopped execution')
    observation = read_json(descriptor_path(proof['observation']))
    if not isinstance(observation, dict):
        raise BudgetStop('runtime closure boot observation must be an object')
    # The raw macOS output is retained in the pinned observation. Its timestamp,
    # including microseconds, must agree with the normalized boot time.
    raw = observation.get('sysctl_boottime')
    match = re.fullmatch(r'\{ sec = ([0-9]+), usec = ([0-9]+) \}[^\r\n]*', raw) if isinstance(raw, str) else None
    try:
        if match is None or not 0 <= int(match[2]) < 1000000:
            raise ValueError('invalid boot clock')
        boot = datetime.fromtimestamp(int(match[1]), timezone.utc).replace(microsecond=int(match[2]))
        boot_uuid = observation.get('boot_session_uuid')
        if not isinstance(boot_uuid, str) or str(UUID(boot_uuid)) != boot_uuid.lower():
            raise ValueError('invalid boot UUID')
    except (ValueError, OverflowError, OSError) as error:
        raise BudgetStop('runtime closure lacks a valid raw boot observation') from error
    # Some collectors record whole seconds. Require agreement at that precision;
    # always use the full raw timestamp when proving that reboot followed stop.
    normalized = timestamp(observation.get('boot_at'))
    if normalized not in (boot, boot.replace(microsecond=0)):
        raise BudgetStop('runtime closure boot timestamps disagree')
    if not (timestamp(result.get('started_at')) <= timestamp(launch.get('recorded_at')) <=
            timestamp(result.get('finished_at')) < boot <= timestamp(observation.get('observed_at')) <=
            timestamp(review.get('reviewed_at')) <= datetime.now(timezone.utc)):
        raise BudgetStop('runtime closure chronology does not prove a later host reboot')
    return sha(path)
