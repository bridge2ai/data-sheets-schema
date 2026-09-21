"""Shared accounting ownership after an independently accepted native audit.

This foundation does not launch a model, accept scientific work, authorize a
job, or resume an attempt. Its caller must enforce reviewed registration and
attempt lifecycle gates. Historical audit controllers see a permanent
non-ledger seal under their existing state path and lock.
"""
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading

from filelock import FileLock

from budgeted_cborg import BudgetStop, Ledger

PROTOCOL = 'shared_sequence_v2'
KIND = 'd4d_shared_budget_sequence'
SEAL_KIND = 'd4d_audit_budget_handoff_seal'
PREDECESSORS = {'reconciliation': 'audit', 'evaluation': 'reconciliation',
                'evaluation_subtype': 'evaluation'}


def _require(condition, reason):
    if not condition:
        raise BudgetStop(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, 'duplicate accounting JSON key')
            result[key] = value
        return result
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(BudgetStop('nonfinite accounting JSON')))


def path(value):
    _require(isinstance(value, str) and bool(value), 'missing canonical accounting path')
    result = Path(value)
    _require(result.is_absolute() and str(result.resolve()) == value and not result.is_symlink(),
             'accounting path must be absolute, canonical and nonsymlinked')
    return result


def _ref(manifest, value):
    _require(isinstance(value, dict) and set(value) == {'path', 'sha256'}, 'invalid accounting reference')
    result = path(value['path'])
    _require(result.is_file() and manifest['pinned_files'].get(str(result)) == value['sha256']
             and sha(result) == value['sha256'], 'accounting evidence is unpinned or changed')
    return result


def _money(value):
    result = Decimal(str(value))
    _require(result.is_finite() and result >= 0, 'invalid accounting amount')
    return result


def _rows(state):
    rows = state.get('requests')
    _require(isinstance(rows, list) and all(isinstance(row, dict) and row.get('status') == 'settled'
             for row in rows), 'predecessor has unresolved accounting')
    ids = [row.get('id') for row in rows]
    _require(all(isinstance(value, str) and value for value in ids) and len(ids) == len(set(ids)),
             'predecessor request identities are missing or duplicated')
    return sum((_money(row.get('cost_usd')) for row in rows), Decimal(0))


def _origin(manifest):
    block = manifest['budget_sequence']
    origin = block['origin']
    _require(set(origin) == {'registration', 'ledger_path'}, 'invalid sequence origin')
    registration = _ref(manifest, origin['registration'])
    record = read(registration)
    ledger = path(origin['ledger_path'])
    declared = Path(record['budget']['ledger_path'])
    if not declared.is_absolute():
        declared = path(record['repository']) / declared
    _require(declared.resolve() == ledger, 'origin ledger differs from original registration')
    state_path = ledger.with_name('audit_sequence.json')
    _require(path(block['state_path']) == state_path, 'sequence path differs from original audit lock namespace')
    return origin, record, state_path, digest(origin)


def _check_mutable_paths(manifest, registration_path, state_path):
    """Reject aliases before even acquiring a lock that can truncate its file."""
    target = path(manifest['budget']['ledger_path'])
    mutable = [state_path, path(str(state_path) + '.lock'), target,
               path(str(target) + '.lock'), target.with_suffix('.tmp')]
    immutable = [path(name) for name in manifest['pinned_files']]
    immutable.extend([registration_path, path(manifest['budget_sequence']['origin']['ledger_path'])])
    pending = [manifest['budget_sequence']]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if set(item) == {'path', 'sha256'}:
                immutable.append(path(item['path']))
            else:
                pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    def overlap(left, right):
        return (left == right or left in right.parents or right in left.parents
                or (left.exists() and right.exists() and os.path.samefile(left, right)))
    for index, destination in enumerate(mutable):
        for other in mutable[index + 1:]:
            _require(not overlap(destination, other), 'mutable accounting destinations overlap')
        for frozen in immutable:
            _require(not overlap(destination, frozen),
                     'mutable accounting destination overlaps immutable evidence')


def seal_document(manifest):
    """Deterministic immutable seal; deliberately never a ledger/registration."""
    block = manifest['budget_sequence']
    origin, generation, state_path, lineage = _origin(manifest)
    first = block['audit_origin']
    _require(first['stage'] == 'audit', 'seal must close an audit predecessor')
    return {'kind': SEAL_KIND, 'schema_version': 1, 'lineage_id': lineage,
        'origin_generation_registration_sha256': origin['registration']['sha256'],
        'sequence_state': str(state_path), 'closed_audit_registration': first['registration'],
        'closed_audit_ledger': first['ledger'], 'predecessor_state_snapshot': first['state'],
        'acceptance': first['acceptance'], 'result': first['result'],
        'allocation_usd': str(generation['budget']['additional_usd']),
        'default_attempt_usd': str(generation['budget']['per_attempt_usd']),
        'closed_scope': 'phase3_audit_only',
        'purpose': 'Permanent legacy audit admission barrier; not a billing ledger'}


def _closure(manifest, predecessor, lineage):
    _require(predecessor['stage'] in {'audit', 'reconciliation', 'evaluation'}, 'unsupported predecessor closure stage')
    refs = {key: _ref(manifest, predecessor[key]) for key in
            ('registration', 'ledger', 'state', 'result', 'acceptance')}
    registration, ledger, result, acceptance = (read(refs[key]) for key in
                                               ('registration', 'ledger', 'result', 'acceptance'))
    identity = predecessor['registration']['sha256']
    _require(path(registration['budget']['ledger_path']) == refs['ledger']
             and ledger.get('manifest_sha256') == identity,
             'predecessor ledger does not belong to its registration')
    if predecessor['stage'] == 'evaluation':
        _require(registration.get('schema_version') == 2
                 and registration.get('budget_sequence', {}).get('stage') == 'evaluation'
                 and digest(registration['budget_sequence']['origin']) == lineage,
                 'evaluation predecessor changes sequence ancestry')
        from evaluation_controls.closure import validate_aggregate
        _require(manifest['pinned_files'].get(str(Path(__file__).parent / 'evaluation_controls/closure.py'))
                 == sha(Path(__file__).parent / 'evaluation_controls/closure.py'),
                 'aggregate closure implementation is unpinned or changed')
        validate_aggregate(registration, refs['registration'], result, ledger)
        artifacts = result['artifacts']
    elif predecessor['stage'] == 'audit':
        _require(registration.get('kind') == 'd4d_native_audit_continuation'
                 and sha(registration['parent']['registration']) == manifest['budget_sequence']['origin']['registration']['sha256'],
                 'audit predecessor differs from original generation')
        runtime = result.get('runtime')
        _require(isinstance(runtime, dict) and type(runtime.get('exit_code')) is int
                 and runtime['exit_code'] == 0,
                 'audit predecessor lacks successful native integer-zero exit')
        expected_scope = 'phase3_audit_only'
        artifacts = {result.get('audit_path'): result.get('audit_sha256')}
        if 'audit_output' in registration:
            from audit_controls import output_parts
            implementation = Path(output_parts.__file__).resolve()
            _require(manifest['pinned_files'].get(str(implementation)) == sha(implementation),
                     'staged audit closure implementation is unpinned or changed')
            for evidence_path in output_parts.closure_paths(registration, refs['registration'], result):
                _require(manifest['pinned_files'].get(str(evidence_path)) == sha(evidence_path),
                         'staged audit closure evidence is unpinned or changed')
        if 'audit_drafting' in registration:
            from audit_controls import draft_output
            implementation = Path(draft_output.__file__).resolve()
            _require(manifest['pinned_files'].get(str(implementation)) == sha(implementation),
                     'drafted audit closure implementation is unpinned or changed')
            for evidence_path in draft_output.closure_paths(registration, refs['registration'], result):
                _require(manifest['pinned_files'].get(str(evidence_path)) == sha(evidence_path),
                         'drafted audit closure evidence is unpinned or changed')
        validation = result.get('validation', {})
        _require(isinstance(validation, dict) and validation.get('checked') is True
                 and validation.get('findings') == [] and validation.get('errors') == []
                 and validation.get('job_id') == registration['job']['id']
                 and validation.get('audit_sha256') == result.get('audit_sha256')
                 and result.get('audit_path') == registration['job']['audit_path'],
                 'audit validator closure is unchecked, contradictory or names another artifact')
    else:
        _require(registration['budget_sequence']['stage'] == 'reconciliation'
                 and digest(registration['budget_sequence']['origin']) == lineage,
                 'reconciliation predecessor changes sequence ancestry')
        expected_scope = 'phase4_reconciliation'
        artifacts = result.get('artifacts')
    runtime = result.get('runtime', {})
    _require(predecessor['stage'] == 'evaluation' or (result.get('status') == 'completed_pending_independent_review'
             and result.get('scope') == expected_scope and result.get('registration_sha256') == identity
             and result.get('job_id') == registration['job']['id']
             and result.get('unresolved_requests') == []
             and result.get('validation', {}).get('passed') is True
             and runtime.get('proxy_shutdown_complete') is True
             and type(runtime.get('unfinished_handlers')) is int and runtime['unfinished_handlers'] == 0),
             'predecessor lacks successful complete controller closure')
    _require(isinstance(artifacts, dict) and bool(artifacts), 'predecessor lacks closed artifacts')
    for name, value in artifacts.items():
        _ref(manifest, {'path': name, 'sha256': value})
    _require(acceptance.get('verdict') == 'accept'
             and acceptance.get('registration_sha256') == identity
             and acceptance.get('result_sha256') == predecessor['result']['sha256']
             and acceptance.get('ledger_sha256') == predecessor['ledger']['sha256']
             and canonical(acceptance.get('artifacts')) == canonical(artifacts),
             'predecessor lacks independent acceptance of exact closed evidence')
    return ledger, _rows(ledger), read(refs['state'])


def _legacy_fields(manifest, lineage):
    block = manifest['budget_sequence']
    return {'kind': KIND, 'schema_version': 2, 'lineage_id': lineage,
        'registration_sha256': block['seal']['sha256'], 'ledger_path': block['seal']['path'],
        'source_registration_sha256': block['origin']['registration']['sha256'],
        'parent_checkpoint_sha256': block['audit_origin']['ledger']['sha256'],
        'audit_seal': block['seal']}


def _tip(manifest, registration_path, registration_sha):
    return {'registration_sha256': registration_sha, 'registration_path': str(registration_path),
            'ledger_path': manifest['budget']['ledger_path'], 'stage': manifest['budget_sequence']['stage']}


def _activation_state(manifest, registration_path, registration_sha):
    """Reconstruct every transfer from pinned predecessor evidence, not live state.

    The bounded stage order has at most three activations. Historical predecessor
    registrations supply their own immutable references; their code is not run.
    """
    block = manifest['budget_sequence']
    stage, predecessor = block['stage'], block['predecessor']
    _require(stage in PREDECESSORS and predecessor['stage'] == PREDECESSORS[stage], 'unsupported activation ancestry')
    _, _, _, lineage = _origin(manifest)
    _require(canonical(read(_ref(manifest, block['seal']))) == canonical(seal_document(manifest)),
             'activation seal differs from pinned origin')
    previous, cost, snapshot = _closure(manifest, predecessor, lineage)
    legacy = _legacy_fields(manifest, lineage)
    if stage == 'reconciliation':
        _require(snapshot.get('schema_version') == 1
                 and snapshot.get('registration_sha256') == predecessor['registration']['sha256']
                 and snapshot.get('ledger_path') == predecessor['ledger']['path']
                 and snapshot.get('source_registration_sha256') == block['origin']['registration']['sha256'],
                 'legacy audit snapshot differs from accepted predecessor')
        transfers = []
    else:
        prior_path = _ref(manifest, predecessor['registration'])
        prior = read(prior_path)
        _require(canonical(prior['budget_sequence']['origin']) == canonical(block['origin'])
                 and canonical(prior['budget_sequence']['audit_origin']) == canonical(block['audit_origin'])
                 and canonical(prior['budget_sequence']['seal']) == canonical(block['seal']),
                 'prior activation changes immutable audit ancestry')
        expected_prior = _activation_state(prior, prior_path, predecessor['registration']['sha256'])
        _require(canonical(snapshot) == canonical(expected_prior), 'predecessor activation history is incomplete or changed')
        transfers = deepcopy(expected_prior['transfers'])
    tip = _tip(manifest, registration_path, registration_sha)
    transfers.append({'predecessor': deepcopy(predecessor), 'successor': tip,
        'checkpoint_sha256': predecessor['ledger']['sha256'],
        'requests_sha256': digest(previous['requests']), 'settled_cost_usd': str(cost)})
    return {**legacy, 'transfers': transfers, 'active_tip': tip}


def _validate(manifest, registration_path, registration_sha):
    _require(sha(registration_path) == registration_sha and canonical(read(registration_path)) == canonical(manifest),
             'successor registration changed')
    _require(manifest['pinned_files'].get(str(Path(__file__).resolve())) == sha(__file__),
             'shared accounting implementation is unpinned or changed')
    if 'sequence_claim' in manifest:
        import sequence_claim
        sequence_claim.enabled(manifest)
        _require(all(manifest['pinned_files'].get(str(p)) == sha(p) for p in sequence_claim.IMPLEMENTATIONS),
                 'durable sequence claim implementation is unpinned or changed')
    for name, value in manifest['pinned_files'].items():
        _require(sha(path(name)) == value, 'registered immutable evidence changed')
    block, budget = manifest['budget_sequence'], manifest['budget']
    _require(block['protocol'] == PROTOCOL and block['stage'] in PREDECESSORS,
             'unsupported shared accounting protocol or stage')
    origin, generation, state_path, lineage = _origin(manifest)
    _check_mutable_paths(manifest, registration_path, state_path)
    seal = read(_ref(manifest, block['seal']))
    _require(canonical(seal) == canonical(seal_document(manifest)), 'legacy audit seal differs from exact origin')
    _closure(manifest, block['audit_origin'], lineage)
    previous, cost, snapshot = _closure(manifest, block['predecessor'], lineage)
    expected_predecessor = PREDECESSORS[block['stage']]
    _require(block['predecessor']['stage'] == expected_predecessor, 'successor stage skips its required predecessor')
    _require(block['predecessor']['stage'] != 'audit'
             or canonical(block['predecessor']) == canonical(block['audit_origin']), 'first transfer changes audit origin')
    checkpoint = budget['continuation']
    _require(checkpoint['checkpoint'] == block['predecessor']['ledger']['path']
             and checkpoint['sha256'] == block['predecessor']['ledger']['sha256']
             and _money(checkpoint['cost_usd']) == cost, 'handoff does not carry its exact real predecessor ledger')
    for key, old_key in (('additional_usd', 'additional_cap_usd'), ('per_attempt_usd', 'attempt_cap_usd')):
        _require(_money(budget[key]) > 0 and str(budget[key]) == str(generation['budget'][key])
                 and str(budget[key]) == str(previous[old_key]), 'handoff changes original budget caps')
    _require(cost <= _money(budget['additional_usd']), 'predecessor exceeds approved allocation')
    target = path(budget['ledger_path'])
    _require(target == registration_path.parent / 'billing.json' and str(target) not in manifest['pinned_files']
             and target != path(block['predecessor']['ledger']['path']), 'successor ledger must be an isolated new destination')
    rows = manifest.get('evaluation_jobs') if block['stage'] in {'evaluation', 'evaluation_subtype'} else [manifest['job']]
    _require(isinstance(rows, list) and bool(rows), 'successor lacks a job roster')
    jobs = [row['id'] for row in rows]
    _require(all(isinstance(job, str) and bool(job) and ':' not in job for job in jobs)
             and len(jobs) == len(set(jobs)), 'invalid successor job identities')
    overrides = budget.get('per_job_attempt_usd', {})
    _require(isinstance(overrides, dict) and set(overrides) <= set(jobs), 'attempt-cap exception names an unregistered job')
    return state_path, lineage, previous, snapshot, jobs, _activation_state(manifest, registration_path, registration_sha)


def _sync(pathname):
    descriptor = os.open(pathname, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _replace_state(state_path, value):
    with tempfile.NamedTemporaryFile(mode='wb', prefix='.handoff-', dir=state_path.parent, delete=False) as output:
        temporary = Path(output.name)
        output.write(canonical(value) + b'\n'); output.flush(); os.fsync(output.fileno())
    try:
        os.replace(temporary, state_path)
        _sync(state_path.parent)
    finally:
        temporary.unlink(missing_ok=True)


class SequenceOwner:
    def __init__(self, manifest, registration_path, registration_sha, lock, state_path, state_sha, ledger, previous, jobs):
        self.manifest, self.registration_path, self.registration_sha = manifest, registration_path, registration_sha
        self.lock, self.state_path, self.state_sha = lock, state_path, state_sha
        self.ledger, self.previous, self.jobs, self.active = ledger, previous, jobs, True
        self._guard = threading.RLock()

    def verify_admission(self):
        with self._guard:
            try:
                self._verify_admission()
            except (OSError, KeyError, TypeError, ValueError, ArithmeticError) as error:
                raise BudgetStop('active accounting evidence is unusable: ' + type(error).__name__) from error

    def _verify_admission(self):
        _require(self.active and self.lock.is_locked, 'shared accounting ownership is no longer held')
        expected = _validate(self.manifest, self.registration_path, self.registration_sha)[-1]
        _require(sha(self.state_path) == self.state_sha and canonical(read(self.state_path)) == canonical(expected),
                 'shared accounting owner changed')
        if 'sequence_claim' in self.manifest:
            import sequence_claim
            claim = _claim_context(self.manifest, self.registration_path, self.registration_sha, self.state_path)
            predecessor = Path(self.manifest['budget_sequence']['predecessor']['state']['path']).read_bytes()
            sequence_claim.verify(claim, expected, predecessor)
        state = read(self.ledger.path)
        _require(all(state.get(key) == value for key, value in self.ledger.identity.items())
                 and state.get('attempt_caps_usd', {}) == self.ledger.identity.get('attempt_caps_usd', {}),
                 'active ledger identity changed')
        prefix = self.previous['requests']
        _require(isinstance(state.get('requests'), list) and canonical(state['requests'][:len(prefix)]) == canonical(prefix)
                 and state.get('continued_from') == {
                     'checkpoint_sha256': self.manifest['budget']['continuation']['sha256'],
                     'manifest_sha256': self.previous['manifest_sha256'],
                     'cost_usd': str(_rows(self.previous)), 'requests': len(prefix)},
                 'active ledger lost its unchanged carried history')
        rows = state['requests']
        identifiers = [row.get('id') for row in rows]
        _require(all(isinstance(value, str) and value for value in identifiers)
                 and len(identifiers) == len(set(identifiers)), 'active ledger request identities changed')
        for row in rows[len(prefix):]:
            _require(row.get('attempt') in {self.registration_sha + ':' + job for job in self.jobs},
                     'active ledger contains an unregistered attempt')
            _require(row.get('status') in {'settled', 'pending', 'protocol_failure', 'over_reservation'},
                     'active ledger request status is invalid')
            if row['status'] == 'settled':
                _money(row.get('cost_usd'))
            else:
                _require(_money(row.get('reserved_usd')) > 0, 'active ledger reservation is invalid')

    def reserve(self, attempt, estimate, request_sha256):
        with self._guard:
            self.verify_admission()
            _require(attempt in {self.registration_sha + ':' + job for job in self.jobs},
                     'reservation names an unregistered successor job')
            return self.ledger.reserve(attempt, estimate, request_sha256)


def _claim_context(manifest, registration_path, registration_sha, state_path):
    if 'sequence_claim' not in manifest:
        return None
    import sequence_claim
    origin = manifest['budget_sequence']['origin']
    return sequence_claim.context(manifest, registration_path, registration_sha, state_path,
        {'registration_sha256': origin['registration']['sha256'], 'ledger_path': origin['ledger_path']},
        manifest['budget_sequence']['stage'])


@contextmanager
def owned_sequence(manifest, registration_path, registration_sha):
    """Hold legacy lock through handoff, caller admission and bounded shutdown.

    Reentry recognizes only this exact owner and existing intact ledger. It
    does not permit retrying a consumed attempt; the caller owns that gate.
    """
    registration_path = path(str(registration_path))
    body_started = False
    try:
        state_path = _origin(manifest)[2]
        _check_mutable_paths(manifest, registration_path, state_path)
        claim = _claim_context(manifest, registration_path, registration_sha, state_path)
        if claim is not None:
            import sequence_claim
            lock = sequence_claim.ClaimLock(str(state_path) + '.lock')
        else:
            lock = FileLock(str(state_path) + '.lock', timeout=0, thread_local=False)
        with lock:
            state_path, lineage, previous, snapshot, jobs, activated = _validate(manifest, registration_path, registration_sha)
            current_raw = state_path.read_bytes()
            current = read(state_path)  # Missing state is never a fresh allocation.
            expected_tip = _tip(manifest, registration_path, registration_sha)
            legacy = _legacy_fields(manifest, lineage)
            owns = current.get('active_tip') == expected_tip
            if owns or current.get('kind') == KIND:
                _require(all(current.get(key) == value for key, value in legacy.items()), 'permanent legacy audit seal changed')
            if owns:
                _require(canonical(current) == canonical(activated), 'activation history is incomplete or changed')
            if not owns:
                predecessor = manifest['budget_sequence']['predecessor']
                _require(sha(state_path) == predecessor['state']['sha256'] and canonical(current) == canonical(snapshot),
                         'predecessor state changed or another successor owns the allocation')
                if predecessor['stage'] == 'audit':
                    _require(current.get('schema_version') == 1 and current.get('registration_sha256') == predecessor['registration']['sha256']
                             and current.get('ledger_path') == predecessor['ledger']['path']
                             and current.get('source_registration_sha256') == manifest['budget_sequence']['origin']['registration']['sha256'],
                             'legacy audit tip differs from accepted predecessor')
                else:
                    expected = {'registration_sha256': predecessor['registration']['sha256'],
                        'registration_path': predecessor['registration']['path'],
                        'ledger_path': predecessor['ledger']['path'], 'stage': predecessor['stage']}
                    _require(current.get('kind') == KIND and current.get('active_tip') == expected,
                             'transfer does not consume the active predecessor')
            budget = manifest['budget']
            ledger = Ledger(budget['ledger_path'], manifest_sha256=registration_sha,
                total_cap=budget['additional_usd'], attempt_cap=budget['per_attempt_usd'],
                attempt_caps_usd={registration_sha + ':' + job: value for job, value in budget.get('per_job_attempt_usd', {}).items()})
            if not owns:
                # Exclusive creation prevents adopting an unactivated orphan ledger.
                with ledger.path.open('x', encoding='utf-8') as output:
                    json.dump({**ledger.identity, 'requests': []}, output); output.flush(); os.fsync(output.fileno())
                checkpoint = budget['continuation']
                ledger.continue_from(checkpoint['checkpoint'], expected_sha256=checkpoint['sha256'], expected_cost_usd=checkpoint['cost_usd'])
                _sync(ledger.path); _sync(ledger.path.parent)
                _replace_state(state_path, activated)
                if claim is not None:
                    import sequence_claim
                    sequence_claim.record(claim, activated, current_raw)
            owner = SequenceOwner(manifest, registration_path, registration_sha, lock, state_path,
                                  sha(state_path), ledger, previous, jobs)
            try:
                owner.verify_admission()
                body_started = True
                yield owner
            finally:
                with owner._guard:
                    owner.active = False
    except (OSError, KeyError, TypeError, ValueError, ArithmeticError) as error:
        if body_started:
            raise
        raise BudgetStop('shared accounting evidence or durable transition is unusable: ' + type(error).__name__) from error
