"""Explicit one-hop, all-worker provenance for a fresh integration (#2386).

Read-only proof and opaque freeze checks. This does not accept worker science,
claim ownership, import money, run a checker, or execute a child. Typed worker
closure is separately verified under each worker's original registration.
"""
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from budgeted_cborg import BudgetStop, STALL_DEBIT_BASIS, attempt_identity

KEY = 'audit_worker_checkpoint'
KIND = 'collective_closed_workers_v1'
BATCH_KIND = 'closed_worker_checkpoint_integrated_v1'
INVENTORY_KIND = 'audit_batch_checkpoint_inventory_v1'
REFS = ('source_registration', 'source_ledger', 'source_owner', 'source_claim',
        'source_result', 'source_inventory')
MAX_DOCUMENT = 64 * 1024 * 1024
SCIENTIFIC_MODULES = ('audit_batches.py', 'audit_batch_context.py', 'audit_batch_format.py',
                      'audit_grammar.py', 'evidence_assertions.py', 'api_runner.py')
CONTROL_RELATIVE = Path(__file__).resolve().parent.parent.relative_to(Path(__file__).resolve().parents[3])
HEX = re.compile('[0-9a-f]{64}')


def _require(ok, message):
    if not ok:
        raise BudgetStop('worker checkpoint: ' + message)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def _same(left, right):
    return _canonical(left) == _canonical(right)


def _path(value):
    _require(type(value) is str and bool(value), 'missing absolute path')
    path = Path(value)
    _require(path.is_absolute() and str(path) == value and path.resolve() == path
             and not any(p.is_symlink() for p in (path, *path.parents)),
             'path is not canonical or has a symlink')
    return path


def _relative(value):
    _require(type(value) is str and bool(value), 'missing relative path')
    path = PurePosixPath(value)
    _require(not path.is_absolute() and str(path) == value
             and all(p not in ('.', '..') for p in path.parts), 'invalid relative path')
    return value


def _ref(value):
    _require(type(value) is dict and set(value) == {'path', 'sha256'}
             and type(value['sha256']) is str and HEX.fullmatch(value['sha256']),
             'invalid document reference')
    _path(value['path'])
    return value


def selection(value):
    """Strict detached descriptor; path metadata only, no document reads or implicit selection."""
    _require(type(value) is dict and set(value) == {'kind', *REFS, 'workers'}
             and value['kind'] == KIND, 'unsupported selection')
    for key in REFS:
        _ref(value[key])
    _require(len({value[k]['path'] for k in REFS}) == len(REFS), 'overlapping references')
    workers = value['workers']
    _require(type(workers) is list and bool(workers), 'missing collective worker roster')
    for worker in workers:
        _require(type(worker) is dict and set(worker) == {'id', 'closure'}
                 and type(worker['id']) is str and re.fullmatch(r'worker_[0-9]{4}', worker['id']),
                 'invalid worker reference')
        _ref(worker['closure'])
    _require(len({w['id'] for w in workers}) == len(workers)
             and len({w['closure']['path'] for w in workers}) == len(workers), 'duplicate worker')
    return deepcopy(value)


def _raw(path, maximum=MAX_DOCUMENT):
    path = _path(str(path))
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            _require(stat.S_ISREG(info.st_mode) and 0 <= info.st_size <= maximum,
                     'document is not a bounded regular file')
            raw = stream.read(maximum + 1)
            _require(len(raw) == info.st_size, 'document changed while reading')
            return raw
    except OSError:
        raise BudgetStop('worker checkpoint: document unavailable') from None


def _digest(path):
    path = _path(str(path))
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            _require(stat.S_ISREG(before.st_mode), 'nonregular frozen file')
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
            after = os.fstat(stream.fileno())
            _require((before.st_size, before.st_mtime_ns, before.st_nlink)
                     == (after.st_size, after.st_mtime_ns, after.st_nlink), 'frozen file changed')
            return digest.hexdigest()
    except OSError:
        raise BudgetStop('worker checkpoint: frozen file unavailable') from None


def _json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            _require(key not in value, 'duplicate JSON field')
            value[key] = item
        return value
    try:
        value = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(BudgetStop('worker checkpoint: nonfinite JSON')))
    except (ValueError, UnicodeError):
        raise BudgetStop('worker checkpoint: malformed JSON') from None
    _require(type(value) is dict, 'document must be an object')
    return value


def _read(ref):
    raw = _raw(ref['path'])
    _require(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'document digest changed')
    return _json(raw)


def _money(value):
    try:
        _require(type(value) in (str, int, float), 'invalid accounting amount')
        result = Decimal(str(value))
        _require(result.is_finite() and result >= 0, 'invalid accounting amount')
        return result
    except (InvalidOperation, ValueError):
        raise BudgetStop('worker checkpoint: invalid accounting amount') from None


def _inventory(value, root):
    _require(type(value) is dict and set(value) == {'kind', 'root', 'files', 'directories', 'hardlink_groups'}
             and value['kind'] == INVENTORY_KIND and value['root'] == str(root), 'invalid frozen inventory')
    files = value['files']
    _require(type(files) is dict and bool(files), 'empty frozen inventory')
    for name, record in files.items():
        _relative(name)
        _require(type(record) is dict and set(record) == {'sha256', 'bytes', 'links'}
                 and type(record['sha256']) is str and HEX.fullmatch(record['sha256'])
                 and type(record['bytes']) is int and record['bytes'] >= 0
                 and type(record['links']) is int and record['links'] >= 1, 'invalid frozen file')
    dirs, groups = value['directories'], value['hardlink_groups']
    _require(type(dirs) is list and dirs == sorted(set(dirs))
             and all(_relative(d) for d in dirs), 'invalid frozen directories')
    _require(type(groups) is list and all(type(g) is list and len(g) >= 2
             and g == sorted(set(g)) and all(n in files for n in g) for g in groups)
             and groups == sorted(groups), 'invalid frozen hardlink groups')
    _require(len([n for g in groups for n in g]) == len({n for g in groups for n in g}),
             'overlapping frozen hardlink groups')
    return value


def verify_freeze(value):
    """Opaque exact tree including hidden/ignored entries and all internal links."""
    root = _path(value['root']); _require(root.is_dir(), 'missing frozen root')
    value = _inventory(value, root)
    found, directories, inodes = {}, [], {}
    for folder, names, leaves in os.walk(root, followlinks=False):
        for name in names:
            p = Path(folder) / name
            _require(stat.S_ISDIR(p.lstat().st_mode), 'linked frozen directory')
            directories.append(str(p.relative_to(root)))
        for name in leaves:
            p = Path(folder) / name; info = p.lstat(); rel = str(p.relative_to(root))
            _require(stat.S_ISREG(info.st_mode), 'special frozen entry')
            found[rel] = {'sha256': _digest(p), 'bytes': info.st_size, 'links': info.st_nlink}
            inodes.setdefault((info.st_dev, info.st_ino), []).append(rel)
    groups = sorted(sorted(names) for names in inodes.values() if len(names) > 1)
    _require(_same(found, value['files']) and sorted(directories) == value['directories']
             and groups == value['hardlink_groups'], 'frozen tree changed')
    _require(all(found[n]['links'] == len(names) for names in inodes.values() for n in names),
             'frozen evidence has external hardlinks')


@dataclass(frozen=True)
class CheckpointSource:
    manifest: dict
    registration_path: Path
    sha256: str
    workers: tuple
    closure_refs: dict
    proposal_refs: dict
    proof_sha256: str
    evidence_paths: frozenset


def proof_paths(manifest):
    try:
        return _proof_paths(manifest)
    except (KeyError, TypeError, AttributeError, ValueError, OSError):
        raise BudgetStop('worker checkpoint: malformed proof path closure') from None


def _proof_paths(manifest):
    if KEY not in manifest:
        return set()
    proof = selection(manifest[KEY]); source = _read(proof['source_registration'])
    root = Path(proof['source_registration']['path']).parent
    inventory = _inventory(_read(proof['source_inventory']), root)
    from . import checkpoint_eligibility
    return {Path(__file__).resolve(), Path(checkpoint_eligibility.__file__).resolve(),
            *(_path(proof[k]['path']) for k in REFS),
            *(_path(w['closure']['path']) for w in proof['workers']),
            *(_path(p) for p in source['pinned_files']),
            *(root / name for name in inventory['files'])}


def validate(manifest, *, require_pins=True):
    """Verify one-hop metadata/freeze/zero-check proof; never replay worker science."""
    try:
        return _validate(manifest, require_pins=require_pins)
    except (KeyError, TypeError, AttributeError, ValueError, OSError, ArithmeticError):
        raise BudgetStop('worker checkpoint: malformed or unavailable proof') from None


def _validate(manifest, *, require_pins):
    proof = selection(manifest[KEY]); source = _read(proof['source_registration'])
    path = _path(proof['source_registration']['path']); root = path.parent
    identity = proof['source_registration']['sha256']
    _require(path.name == 'registration.json' and KEY not in source
             and source.get('kind') == 'd4d_native_audit_continuation'
             and type(source.get('protocol_version')) is int and source['protocol_version'] == 7
             and type(source.get('render_version')) is int and source['render_version'] == 23
             and source['audit_batches']['kind'] == 'fresh_context_integrated_v1', 'source is not a fresh one-hop 7/23 batch')
    inventory = _inventory(_read(proof['source_inventory']), root)
    _require(root not in Path(proof['source_inventory']['path']).parents,
             'inventory must be outside frozen source')
    verify_freeze(inventory)
    paths = proof_paths(manifest)
    for name, digest in source['pinned_files'].items():
        _require(_digest(name) == digest, 'source registration pin changed')
    for key in REFS[:-1]:
        p = _path(proof[key]['path'])
        _require(p.is_relative_to(root) and inventory['files'][str(p.relative_to(root))]['sha256']
                 == proof[key]['sha256'], 'source reference is not frozen in the condition')
    job, budget = source['job'], source['budget']
    _require(proof['source_ledger']['path'] == budget['ledger_path'] == str(root / 'billing.json')
             and proof['source_result']['path'] == str(Path(job['attempt_dir']) / 'result.json')
             and proof['source_owner']['path'] == str(root / 'sequence_claim/owner.json')
             and proof['source_claim']['path'] == str(root / 'sequence_claim/manifest.json'), 'source paths differ from registered layout')
    ledger, owner, claim, result = (_read(proof[k]) for k in ('source_ledger', 'source_owner', 'source_claim', 'source_result'))
    expected_owner = {'schema_version': 1, 'registration_sha256': identity,
        'ledger_path': budget['ledger_path'], 'parent_checkpoint_sha256': budget['continuation']['sha256'],
        'source_registration_sha256': _digest(source['parent']['registration'])}
    _require(_same(owner, expected_owner) and source.get('sequence_claim') == {'protocol': 'durable_sequence_claim_v1'},
             'source owner/claim differs')
    generation = _json(_raw(source['parent']['registration']))
    origin_ledger = Path(generation['budget']['ledger_path'])
    if not origin_ledger.is_absolute():
        origin_ledger = Path(source['parent']['repository']) / origin_ledger
    origin_ledger = _path(str(origin_ledger))
    implementation = Path(source['repository']) / CONTROL_RELATIVE / 'sequence_claim.py'
    expected_claim_fields = {'schema_version', 'kind', 'protocol', 'stage', 'claiming_registration_path',
        'claiming_registration_sha256', 'canonical_state_path', 'owner_sha256', 'predecessor_absent',
        'predecessor_sha256', 'origin', 'implementation_sha256'}
    _require(set(claim) == expected_claim_fields
                 and source['sequence_state'] == str(origin_ledger.with_name('audit_sequence.json'))
                 and _same(claim['origin'], {'registration_sha256': expected_owner['source_registration_sha256'],
                     'ledger_path': str(origin_ledger)})
                 and claim['implementation_sha256'] == source['pinned_files'].get(str(implementation))
                 == _digest(implementation), 'source durable claim origin or implementation differs')
    _require(claim.get('kind') == 'observed_sequence_owner_transition'
             and claim.get('protocol') == 'durable_sequence_claim_v1' and type(claim.get('schema_version')) is int
             and claim['schema_version'] == 1 and claim.get('stage') == 'audit'
             and claim.get('claiming_registration_path') == str(path)
             and claim.get('claiming_registration_sha256') == identity
             and claim.get('canonical_state_path') == source['sequence_state']
             and claim.get('owner_sha256') == proof['source_owner']['sha256']
             and claim.get('predecessor_absent') is False
             and claim.get('predecessor_sha256') == _digest(root / 'sequence_claim/predecessor.json')
             and os.path.samefile(root / 'sequence_claim/manifest.json', root / 'sequence_claim/ready.json'),
             'source durable claim is incomplete')
    rows = ledger['requests']; _require(type(rows) is list and bool(rows), 'empty source accounting')
    _require(all(type(r) is dict and r.get('status') == 'settled' and type(r.get('id')) is str
                 and bool(r['id']) for r in rows) and len({r['id'] for r in rows}) == len(rows), 'source accounting is unresolved or duplicated')
    cost = sum((_money(r['cost_usd']) for r in rows), Decimal(0))
    _require(ledger.get('manifest_sha256') == identity
             and _money(ledger['additional_cap_usd']) == _money(budget['additional_usd'])
             and _money(ledger['attempt_cap_usd']) == _money(budget['per_attempt_usd'])
             and cost <= _money(budget['additional_usd']), 'source ledger identity or ceiling differs')
    owner_id = attempt_identity(identity, job['id'])
    _require(_money(ledger['attempt_caps_usd'][owner_id]) == _money(budget['per_job_attempt_usd'][job['id']]),
             'source attempt cap differs')
    _require(result.get('status') == 'stopped' and result.get('registration_sha256') == identity
             and result.get('job_id') == job['id'] and result.get('scope') == 'phase3_audit_only'
             and result.get('error_type') == 'BudgetStop'
             and result.get('runtime', {}).get('proxy_shutdown_complete') is True
             and type(result['runtime'].get('unfinished_handlers')) is int
             and result['runtime']['unfinished_handlers'] == 0, 'source runtime is not a closed stopped audit')
    denied = ledger.get('stopped_attempts', {}).get(owner_id, {})
    _require(denied.get('paid_request') is False and _money(denied.get('denied_reservation_usd')) > 0,
             'source did not stop at unpaid budget admission')
    own = [r for r in rows if r.get('attempt') == owner_id]
    own_cap = _money(budget['per_job_attempt_usd'][job['id']])
    from budgeted_cborg import attempt_spend, validated_stall_allowance
    allowance = validated_stall_allowance(source.get('native_stall_policy', {}).get('stall_allowance_usd'))
    _require(bool(own) and attempt_spend(own, allowance or Decimal(0)) <= own_cap
             and all(_money(r.get('attempt_cap_usd')) == own_cap for r in own),
             'source own accounting exceeds or changes its attempt ceiling')
    maximum = source.get('native_stall_policy', {}).get('max_stall_debits', 0)
    _require(type(maximum) is int and maximum >= 0
             and sum(r.get('settlement_basis') == STALL_DEBIT_BASIS for r in own) <= maximum,
             'source exceeded its registered stall-debit count')
    children = source['audit_batches']['children']
    _require(type(children) is list and len(children) >= 2
             and children[-1]['id'] == 'integration' and children[-1]['kind'] == 'integration'
             and all(w['kind'] == 'worker' for w in children[:-1]), 'source roster is not complete')
    workers = children[:-1]
    plan_path = source['audit_batches']['plan_path']; plan = _json(_raw(plan_path))
    _require(_digest(plan_path) == source['pinned_files'][plan_path]
             and [w['id'] for w in workers] == [w['id'] for w in plan['workers']]
             == [w['id'] for w in proof['workers']], 'collective worker selection differs from complete plan')
    closures, proposals, worker_rows, worker_ids = {}, {}, [], set()
    for row, ref in zip(workers, proof['workers']):
        expected = Path(row['attempt_dir']) / 'closed.json'
        _require(ref['closure']['path'] == str(expected) and expected.is_relative_to(root), 'foreign worker closure path')
        receipt = _read(ref['closure'])
        _require(receipt.get('status') == 'completed_proposal' and receipt.get('registration_sha256') == identity
                 and receipt.get('job_id') == job['id'] and receipt.get('child_id') == row['id']
                 and receipt.get('billing_attempt') == owner_id, 'worker closure identity differs')
        runtime = receipt.get('runtime', {})
        _require(type(runtime.get('exit_code')) is int and runtime['exit_code'] == 0
                 and runtime.get('proxy_initialized') is True and runtime.get('proxy_shutdown_complete') is True
                 and type(runtime.get('unfinished_handlers')) is int and runtime['unfinished_handlers'] == 0,
                 'worker lacks successful closed runtime evidence')
        selected = receipt['request_rows']
        _require(type(selected) is list and bool(selected), 'worker has no settled request rows')
        selected_ids = [r['id'] for r in selected]
        _require(len(set(selected_ids)) == len(selected_ids) and not worker_ids.intersection(selected_ids)
                 and _same([r for r in own if r['id'] in selected_ids], selected),
                 'worker request membership is changed or duplicated')
        worker_ids.update(selected_ids); worker_rows.extend(selected)
        proposal = _path(row['proposal_path']); relative = str(proposal.relative_to(root))
        _require(relative in inventory['files'], 'worker proposal is not frozen')
        closures[row['id']] = deepcopy(ref['closure'])
        proposals[row['id']] = {'path': str(proposal), 'sha256': inventory['files'][relative]['sha256']}
    worker_cap = _money(source['audit_batches']['worker_total_cap_usd'])
    _require(0 < worker_cap < own_cap
             and sum((_money(r['cost_usd']) for r in worker_rows), Decimal(0)) <= worker_cap
             and all(_money(r.get('stage_cap_usd')) == worker_cap for r in worker_rows),
             'source workers exceed or change their cumulative reservation ceiling')
    current = manifest['budget']; previous = current['continuation']
    _require(set(previous) == {'checkpoint', 'sha256', 'cost_usd'}
             and previous['checkpoint'] == proof['source_ledger']['path']
             and previous['sha256'] == proof['source_ledger']['sha256']
             and _money(previous['cost_usd']) == cost, 'source is not the ordinary immediate checkpoint')
    _require(_money(current['additional_usd']) == _money(budget['additional_usd'])
             and _money(current['per_attempt_usd']) == _money(budget['per_attempt_usd'])
             and _same(manifest.get('budget_amendment'), source.get('budget_amendment'))
             and _same(current['prices_per_token'], budget['prices_per_token']), 'checkpoint changes budget authority or pricing')
    _require(0 < _money(current['per_job_attempt_usd'][manifest['job']['id']])
             <= _money(budget['per_job_attempt_usd'][job['id']]), 'checkpoint increases prior attempt allowance')
    for key in ('kind', 'protocol_version', 'render_version', 'scientific_contract_transition',
                'audit_batch_navigation', 'model', 'native_runtime', 'profile', 'provider_base_url',
                'provider_context_policy', 'provider_transport', 'native_stall_policy',
                'native_upstream_read_timeout_seconds', 'native_response_buffer', 'native_history_control', 'sequence_state',
                'python', 'python_identity', 'python_version'):
        _require(_same(manifest.get(key), source.get(key)), 'checkpoint changes registered scientific/runtime settings')
    _require(_same({k:v for k,v in manifest['parent'].items() if k != 'phase2_proof'},
                   {k:v for k,v in source['parent'].items() if k != 'phase2_proof'})
             and set(manifest['inputs']) == set(source['inputs']), 'checkpoint changes original lineage or inputs')
    if 'phase2_proof' in source['parent']:
        _require(_digest(manifest['parent']['phase2_proof']) == _digest(source['parent']['phase2_proof']),
                 'checkpoint changes immutable parent proof')
    _require(_digest(manifest['audit_batches']['plan_path']) == _digest(plan_path),
             'checkpoint changes complete original worker plan')
    old_repository, new_repository = _path(source['repository']), _path(manifest['repository'])
    mandatory = {old_repository / 'src/data_sheets_schema' / name for name in SCIENTIFIC_MODULES}
    mandatory.update(old_repository / name for name in ('pyproject.toml', 'poetry.lock'))
    _require(all(str(p) in source['pinned_files'] for p in mandatory), 'source scientific implementation closure is incomplete')
    for name, digest in source['pinned_files'].items():
        old_path = _path(name)
        if old_path.is_relative_to(old_repository):
            relative = old_path.relative_to(old_repository)
            if relative.parts[0] in ('src', '.claude') or str(relative) in ('pyproject.toml', 'poetry.lock'):
                _require(_digest(new_repository / relative) == digest, 'checkpoint changes scientific implementation bytes')
    for role, name in manifest['inputs'].items():
        original = _path(source['inputs'][role]); current_path = _path(name)
        allowed = {original}
        if original.is_relative_to(old_repository):
            allowed.add(new_repository / original.relative_to(old_repository))
        if role == 'source_inventory':
            allowed.add(Path(manifest['job']['attempt_dir']).parent.parent / 'source_inventory.json')
        _require(current_path in allowed and _digest(current_path) == _digest(original),
                 'checkpoint changes scientific input bytes or origin paths')
    from . import checkpoint_eligibility
    checkpoint_eligibility.verify(source, path, inventory)
    if require_pins:
        # Historical accepted manifests cannot pin a later checkout's helper
        # paths. The caller pins current implementations via required_paths;
        # immutable descriptor/source evidence stays pinned in this manifest.
        local_implementations = {Path(__file__).resolve(), Path(checkpoint_eligibility.__file__).resolve()}
        _require(all(manifest['pinned_files'].get(str(p)) == _digest(p)
                     for p in paths - local_implementations),
                 'checkpoint evidence or implementation is unpinned')
    verify_freeze(inventory)
    return CheckpointSource(source, path, identity, tuple(deepcopy(workers)), closures,
        proposals, hashlib.sha256(_canonical(proof)).hexdigest(), frozenset(paths))
