"""Fail-closed inputs and dependencies for one registered evaluation attempt.

This module does not create provider clients or independent acceptances. A
mechanical result and an independently reviewed canary are separate records.
"""
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Callable

HERE = Path(__file__).resolve().parent
CONTROLS = HERE.parent / 'native_controls'
for directory in (HERE.parent, CONTROLS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from budgeted_cborg import BudgetStop, Ledger
from audit_controls.transport import transport_paths, verified_context

STYLES = frozenset({'semantic_agent', 'field_agent', 'direct_api_quality',
                    'grounding', 'fitness', 'subtype'})
NATIVE_STYLES = frozenset({'semantic_agent', 'field_agent'})
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,150}')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def read_json(path):
    return strict_json(Path(path).read_bytes())


def canonical_path(value, *, exists=False):
    if not isinstance(value, str) or not value:
        raise BudgetStop('registered path must be a nonempty string')
    path = Path(value)
    if not path.is_absolute() or path.resolve(strict=exists) != path:
        raise BudgetStop('registered path is not absolute and canonical')
    return path


def pinned(manifest, value, expected=None):
    path = canonical_path(value, exists=True)
    if not path.is_file() or path.is_symlink():
        raise BudgetStop('registered input is not a regular file')
    recorded = manifest['pinned_files'].get(str(path))
    if not recorded or (expected is not None and recorded != expected) or sha(path) != recorded:
        raise BudgetStop('registered input or instrument pin changed: ' + str(path))
    return path


def required_paths(manifest):
    """Executable source closure plus every explicitly referenced instrument.

Hash the package's Python sources and each selected rubric/prompt directory,
including ignored files. This catches transitive implementation changes, not
only the outer launcher. Registration builders may pin additional resources.
"""
    repository = canonical_path(manifest['repository'], exists=True)
    paths = set((repository / 'src/data_sheets_schema').rglob('*.py'))
    paths.update(repository / name for name in ('pyproject.toml', 'poetry.lock'))
    paths.add(canonical_path(manifest['python_identity']['resolved_path'], exists=True))
    configuration = Path(manifest['python']).parent.parent / 'pyvenv.cfg'
    if configuration.exists():
        paths.add(configuration.resolve())
    paths.add(repository / '.claude/agents/_preimages.json')
    paths.update(HERE.glob('*.py'))
    paths.update(CONTROLS.glob('*.py'))
    paths.add(HERE.parent / 'budgeted_cborg.py')
    # The shared TLS factory imports only these audit-controller modules;
    # their path/hash identities are part of the evaluation implementation.
    paths.update(HERE.parent / 'audit_controls' / name
                 for name in ('__init__.py', 'transport.py', 'registration.py'))
    paths.update(transport_paths(manifest))
    # run_native_canary's imports remain part of the reused controller identity.
    for name in ('prepare_registration.py', 'run_api_canary.py'):
        paths.add(HERE.parent / name)
    for name in ('rubric_dir', 'prompts_dir'):
        if name in manifest:
            paths.update(path for path in canonical_path(manifest[name], exists=True).rglob('*') if path.is_file())
    for job in manifest['evaluation_jobs']:
        for key in ('input', 'context_path', 'schema_path', 'expected_request', 'agent_definition',
                    'instruction', 'rubric_file'):
            if job.get(key):
                paths.add(canonical_path(job[key], exists=True))
        if job.get('bundle'):
            paths.add(canonical_path(job['bundle'], exists=True))
        if job['style'] in NATIVE_STYLES:
            paths.add(canonical_path(job['native_runtime']['executable'], exists=True))
    return paths


def _budget(manifest):
    budget = manifest['budget']
    if (Decimal(str(budget['additional_usd'])) != Decimal('400') or
        Decimal(str(budget['per_attempt_usd'])) != Decimal('5') or budget.get('per_job_attempt_usd')):
        raise BudgetStop('evaluations require the shared 400 allocation and unchanged default 5 attempt cap')
    continuation = budget.get('continuation')
    if not isinstance(continuation, dict):
        raise BudgetStop('evaluations must continue the settled generation accounting')
    checkpoint = pinned(manifest, continuation['checkpoint'], continuation['sha256'])
    state = read_json(checkpoint)
    if (Decimal(str(state.get('additional_cap_usd'))) != Decimal('400') or
        Decimal(str(state.get('attempt_cap_usd'))) != Decimal('5') or
        not isinstance(state.get('requests'), list) or
        any(row.get('status') != 'settled' for row in state['requests'])):
        raise BudgetStop('generation accounting is unresolved or uses a different allocation')
    ids = [row.get('id') for row in state['requests']]
    costs = [Decimal(str(row.get('cost_usd', 'NaN'))) for row in state['requests']]
    if (len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids) or
        any(not value.is_finite() or value < 0 for value in costs) or
        sum(costs, Decimal(0)) != Decimal(str(continuation['cost_usd']))):
        raise BudgetStop('generation accounting identities or settled total differ')
    origin = manifest.get('prior_evaluation', manifest['source_generation'])
    if state.get('manifest_sha256') != origin['registration_sha256']:
        raise BudgetStop('billing checkpoint does not identify its registered predecessor')


def _prior(manifest):
    prior = manifest.get('prior_evaluation')
    if not prior:
        return None
    previous = read_json(pinned(manifest, prior['registration'], prior['registration_sha256']))
    if (previous.get('kind') != 'd4d_evaluation_registration' or
        previous.get('source_generation') != manifest['source_generation']):
        raise BudgetStop('prior evaluation does not share the accepted generation ancestry')
    if previous['budget']['ledger_path'] != prior['billing_ledger']:
        raise BudgetStop('prior evaluation billing path differs from its registration')
    if sha(canonical_path(prior['billing_ledger'], exists=True)) != manifest['budget']['continuation']['sha256']:
        raise BudgetStop('prior evaluation billing advanced after its settled checkpoint')
    # Retain the previous registration's complete immutable evidence closure.
    for filename, digest in previous['pinned_files'].items():
        pinned(manifest, filename, digest)
    return previous


def _generation(manifest):
    source = manifest['source_generation']
    generation = read_json(pinned(manifest, source['registration'], source['registration_sha256']))
    acceptance = read_json(pinned(manifest, source['acceptance'], source['acceptance_sha256']))
    if (acceptance.get('verdict') != 'accept' or
        acceptance.get('registration_sha256') != source['registration_sha256']):
        raise BudgetStop('generation has no independent acceptance of this registration')
    if acceptance.get('evaluation_sequence_state') != source.get('evaluation_sequence_state'):
        raise BudgetStop('generation acceptance does not bind the shared evaluation sequence state')
    if set(source['artifacts']) != {'full', 'core'}:
        raise BudgetStop('evaluation requires the independently accepted full/core pair')
    for artifact in source['artifacts'].values():
        pinned(manifest, artifact['path'], artifact['sha256'])
        if acceptance.get('artifacts', {}).get(artifact['path']) != artifact['sha256']:
            raise BudgetStop('generation acceptance does not bind both unchanged artifacts')
    # The immutable checkpoint must describe the final generation ledger, not
    # a pre-launch checkpoint whose budget could be spent a second time.
    live = canonical_path(source['billing_ledger'], exists=True)
    if generation['budget']['ledger_path'] != str(live):
        raise BudgetStop('source generation billing path differs from its registration')
    if sha(live) != source['billing_sha256']:
        raise BudgetStop('generation billing advanced after its settled checkpoint')
    if not manifest.get('prior_evaluation') and source['billing_sha256'] != manifest['budget']['continuation']['sha256']:
        raise BudgetStop('first evaluation does not continue final generation accounting')


def sequence_path(manifest):
    """One acceptance-bound controller file, outside frozen/attempt evidence."""
    source = manifest['source_generation']
    path = canonical_path(source['evaluation_sequence_state'])
    forbidden = [Path(source['registration']).parent, Path(source['billing_ledger']).parent,
                 canonical_path(manifest['attempts_dir'])]
    forbidden.extend(Path(value['path']).parent for value in source['artifacts'].values())
    forbidden.extend(Path(job['output']).parent for job in manifest['evaluation_jobs'])
    if any(path == directory or directory in path.parents for directory in forbidden):
        raise BudgetStop('sequence controller state must be outside frozen and per-attempt artifacts')
    if path == Path(manifest['budget']['ledger_path']) or str(path) in manifest['pinned_files']:
        raise BudgetStop('sequence controller state cannot alias a ledger or immutable evidence')
    return path


def claim_sequence(manifest, manifest_sha256):
    """Atomically hand the unchanged allocation to exactly one successor.

    The caller holds sequence_path + '.lock' for this operation AND the entire
    job. A predecessor or sibling cannot spend after this handoff. Existing
    ledgers and generation artifacts are never edited by the claim.
    """
    path = sequence_path(manifest)
    origin = manifest['source_generation']
    anchor = canonical_digest(origin)
    predecessor = manifest.get('prior_evaluation', origin)
    predecessor_sha = predecessor['registration_sha256']
    predecessor_ledger = predecessor['billing_ledger']
    tip = {'registration_sha256': manifest_sha256, 'ledger_path': manifest['budget']['ledger_path']}
    if path.exists():
        state = read_json(path)
        if state.get('version') != 1 or state.get('source_generation_sha256') != anchor:
            raise BudgetStop('evaluation sequence ancestry changed')
        if state.get('tip') == tip:
            return sha(path)
        if state.get('tip') != {'registration_sha256': predecessor_sha, 'ledger_path': predecessor_ledger}:
            raise BudgetStop('evaluation sequence already belongs to another successor; predecessor cannot resume')
    else:
        if manifest.get('prior_evaluation'):
            raise BudgetStop('prior evaluation has no durable allocation handoff evidence')
        state = {'version': 1, 'source_generation_sha256': anchor, 'handoffs': []}
    checkpoint = manifest['budget']['continuation']
    if sha(canonical_path(predecessor_ledger, exists=True)) != checkpoint['sha256']:
        raise BudgetStop('sequence predecessor changed before allocation handoff')
    state['handoffs'].append({'from_registration_sha256': predecessor_sha,
        'to_registration_sha256': manifest_sha256, 'checkpoint_sha256': checkpoint['sha256'],
        'settled_cost_usd': checkpoint['cost_usd']})
    state['tip'] = tip
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        json.dump(state, stream, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        temporary = Path(stream.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return sha(path)


def verify_sequence(manifest, manifest_sha256, claimed_sha256):
    path = sequence_path(manifest)
    if sha(path) != claimed_sha256 or read_json(path).get('tip') != {
            'registration_sha256': manifest_sha256, 'ledger_path': manifest['budget']['ledger_path']}:
        raise BudgetStop('evaluation allocation handoff changed during this attempt')


def group(job):
    return ':'.join((job['style'], job['variant'], job.get('rubric', 'slots')))


def verify_manifest(manifest, path, digest):
    if sha(path) != digest:
        raise BudgetStop('evaluation registration changed')
    if manifest.get('kind') != 'd4d_evaluation_registration' or manifest.get('schema_version') != 1:
        raise BudgetStop('unsupported evaluation registration')
    repository = canonical_path(manifest['repository'], exists=True)
    if repository != HERE.parents[2]:
        raise BudgetStop('registered repository differs from the executing adapter')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repository, text=True).strip()
    if head != manifest['repository_commit']:
        raise BudgetStop('evaluation code commit differs from registration')
    if manifest['model']['model'] != 'claude-opus-5':
        raise BudgetStop('evaluation provider/model differs from the approved CBORG instrument')
    # Validate the exact endpoint, CA pin and PEM before any client/count call.
    verified_context(manifest)
    python = Path(manifest['python'])
    identity = manifest['python_identity']
    if (not python.is_absolute() or str(python.resolve(strict=True)) != identity['resolved_path'] or
        sha(python) != identity['sha256'] or
        str(Path(sys.executable).resolve()) != identity['resolved_path'] or
        str(Path(sys.prefix).resolve()) != identity['prefix'] or
        python.parent.parent.resolve() != Path(identity['prefix'])):
        raise BudgetStop('registered Python runtime identity changed')
    for filename, expected in manifest['pinned_files'].items():
        pinned(manifest, filename, expected)
    for filename in required_paths(manifest):
        pinned(manifest, str(filename))
    _generation(manifest)
    previous = _prior(manifest)
    _budget(manifest)
    sequence_path(manifest)
    jobs = manifest['evaluation_jobs']
    if not isinstance(jobs, list) or not jobs:
        raise BudgetStop('evaluation roster is empty')
    ids, outputs, candidates, cells = set(), set(), set(), {}
    attempts = canonical_path(manifest['attempts_dir'])
    for job in jobs:
        identity = job['id']
        if not isinstance(identity, str) or not IDENTIFIER.fullmatch(identity) or identity in ids:
            raise BudgetStop('evaluation job identity is invalid or duplicated')
        ids.add(identity)
        if job['style'] not in STYLES or job['variant'] not in ('full', 'core'):
            raise BudgetStop('unknown evaluation style or variant')
        if type(job['rating']) is not int or job['rating'] < 1 or type(job['canary']) is not bool:
            raise BudgetStop('invalid evaluation rating or canary identity')
        if job['canary_group'] != group(job):
            raise BudgetStop('evaluation canary group differs from style/variant/rubric')
        source = manifest['source_generation']['artifacts'][job['variant']]
        if job['input'] != source['path'] or job['input_sha256'] != source['sha256']:
            raise BudgetStop('evaluation input is outside the independently accepted pair')
        expected_class = 'Dataset' if job['variant'] == 'full' else 'CoreDataset'
        if job['class_name'] != expected_class:
            raise BudgetStop('evaluation class differs from the selected full/core variant')
        pinned(manifest, job['context_path'])
        output = canonical_path(job['output'])
        candidate = canonical_path(job['candidate'])
        if output == candidate or output in outputs or candidate in candidates or output in candidates or candidate in outputs:
            raise BudgetStop('evaluation output/candidate paths collide')
        if candidate.parent != attempts / identity / 'output' or str(output) in manifest['pinned_files']:
            raise BudgetStop('candidate is not isolated or published output aliases a pinned input')
        if output == attempts or attempts in output.parents or candidate in map(Path, manifest['pinned_files']):
            raise BudgetStop('published output and attempt evidence must be separate')
        outputs.add(output); candidates.add(candidate)
        if job['canary']:
            if job['rating'] != 1 or job['canary_group'] in cells:
                raise BudgetStop('each evaluation group requires exactly one primary canary')
            cells[job['canary_group']] = identity
        elif not job.get('canary_acceptance'):
            raise BudgetStop('noncanary evaluation lacks independent canary acceptance path')
    if any(job['canary_group'] not in cells for job in jobs):
        raise BudgetStop('evaluation group lacks its registered canary')
    if any(job['style'] == 'subtype' for job in jobs):
        if previous is None or manifest.get('subtype_selection') != 'all_form_failures':
            raise BudgetStop('subtype requests require a reviewed prior-evaluation all-form-failures selection')
        selected = set()
        for parent in previous['evaluation_jobs']:
            if parent['style'] != 'fitness':
                continue
            receipt_path, receipt = receipt_for(previous, manifest['prior_evaluation']['registration_sha256'], parent)
            pinned(manifest, str(receipt_path))
            value = read_json(pinned(manifest, parent['output'], receipt['output_sha256']))
            if value.get('judgement', {}).get('failure') == 'form':
                selected.add(parent['id'])
        if selected != {job.get('fitness_job_id') for job in jobs if job['style'] == 'subtype'}:
            raise BudgetStop('subtype roster does not cover exactly all prior fitness form failures')
    return {job['id']: job for job in jobs}


def receipt_for(manifest, manifest_sha256, job):
    receipt_path = canonical_path(manifest['attempts_dir']) / job['id'] / 'result.json'
    receipt = read_json(receipt_path)
    if (receipt.get('status') != 'completed_pending_independent_review' or
        receipt.get('registration_sha256') != manifest_sha256 or receipt.get('job_id') != job['id'] or
        receipt.get('registered_job_sha256') != canonical_digest(job) or
        receipt.get('output') != job['output'] or receipt.get('output_sha256') != sha(job['output'])):
        raise BudgetStop('parent evaluation lacks an unchanged mechanically accepted result')
    return receipt_path, receipt


def verify_dependencies(manifest, manifest_sha256, job):
    """Bind runtime dependencies without changing the registered job payload."""
    jobs = {row['id']: row for row in manifest['evaluation_jobs']}
    bound = dict(job)
    dependencies = {}
    if not job['canary']:
        canary = next(row for row in jobs.values() if row['canary'] and row['canary_group'] == job['canary_group'])
        receipt_path, receipt = receipt_for(manifest, manifest_sha256, canary)
        acceptance_path = canonical_path(job['canary_acceptance'], exists=True)
        accepted = read_json(acceptance_path)
        if (accepted.get('verdict') != 'accept' or accepted.get('registration_sha256') != manifest_sha256 or
            accepted.get('job_id') != canary['id'] or accepted.get('canary_group') != job['canary_group'] or
            accepted.get('receipt_sha256') != sha(receipt_path) or
            accepted.get('output_sha256') != receipt['output_sha256']):
            raise BudgetStop('this evaluation group has no independent canary acceptance')
        dependencies['canary_acceptance'] = {'path': str(acceptance_path), 'sha256': sha(acceptance_path)}
    if job['style'] == 'subtype':
        previous = _prior(manifest)
        if previous is None:
            raise BudgetStop('subtype requires an explicitly registered prior evaluation')
        prior_sha = manifest['prior_evaluation']['registration_sha256']
        parent = next((row for row in previous['evaluation_jobs'] if row['id'] == job.get('fitness_job_id')), None)
        fields = ('input', 'input_sha256', 'class_name', 'unit_path', 'slot', 'value_sha256', 'profile', 'schema_path')
        if not parent or parent['style'] != 'fitness' or any(parent.get(k) != job.get(k) for k in fields):
            raise BudgetStop('subtype dependency differs from the registered fitness slot')
        receipt_path, receipt = receipt_for(previous, prior_sha, parent)
        pinned(manifest, str(receipt_path))
        value = read_json(pinned(manifest, parent['output'], receipt['output_sha256']))
        if value.get('judgement', {}).get('failure') != 'form':
            raise BudgetStop('subtype applies only to an accepted fitness form failure')
        if job['fitness_result'] != parent['output'] or (job.get('fitness_result_sha256') and
                                                      job['fitness_result_sha256'] != receipt['output_sha256']):
            raise BudgetStop('subtype fitness artifact differs from its parent receipt')
        bound['fitness_result_sha256'] = receipt['output_sha256']
        dependencies['fitness'] = {'job_id': parent['id'], 'registration_sha256': prior_sha, 'receipt': str(receipt_path),
            'receipt_sha256': sha(receipt_path), 'output': parent['output'], 'output_sha256': receipt['output_sha256']}
    return bound, dependencies


@dataclass(frozen=True)
class EvaluationContext:
    manifest: dict
    manifest_sha256: str
    job: dict
    attempt: Path
    ledger: Ledger
    verify: Callable[[], None]
