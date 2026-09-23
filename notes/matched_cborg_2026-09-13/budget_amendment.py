"""Read-only proof of one explicitly authorized increase to a sequence budget.

The origin and closed checkpoint remain unchanged. This module neither claims
ownership nor creates a ledger. Descendants inherit the same proof; the increase
is an absolute new ceiling, never an amount to add again on another retry.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

from budgeted_cborg import BudgetStop

KEY = 'budget_amendment'
KIND = 'additive_sequence_budget_v1'
REFS = ('origin_registration', 'predecessor_registration', 'predecessor_ledger',
        'predecessor_owner', 'authorization')
AMOUNTS = ('prior_total_usd', 'increase_usd', 'total_usd', 'default_attempt_usd')


def _require(ok, reason):
    if not ok:
        raise BudgetStop(reason)


def _money(value):
    try:
        _require(type(value) in (str, int, float, Decimal), 'invalid amendment amount')
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise BudgetStop('invalid amendment amount') from exc
    _require(result.is_finite() and result >= 0, 'invalid amendment amount')
    return result


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _path(value):
    _require(type(value) is str and bool(value), 'missing amendment reference path')
    path = Path(value)
    _require(path.is_absolute() and str(path) == value and str(path.resolve()) == value
             and not any(p.is_symlink() for p in (path, *path.parents)),
             'amendment reference must be canonical and nonsymlinked')
    return path


def selection(value):
    """Validate the exact optional descriptor without reading its documents."""
    _require(type(value) is dict and set(value) == {'kind', *REFS, *AMOUNTS}
             and value['kind'] == KIND, 'unsupported budget amendment selection')
    for key in REFS:
        ref = value[key]
        _require(type(ref) is dict and set(ref) == {'path', 'sha256'}
                 and type(ref['sha256']) is str
                 and re.fullmatch('[0-9a-f]{64}', ref['sha256']), 'invalid amendment reference')
        _path(ref['path'])
    for key in AMOUNTS:
        _require(type(value[key]) is str and re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?', value[key])
                 and _money(value[key]) > 0, 'amendment amounts must be positive decimal strings')
    _require(_money(value['prior_total_usd']) + _money(value['increase_usd']) == _money(value['total_usd']),
             'amendment increase does not equal its new absolute cap')
    _require(len({value[k]['path'] for k in REFS}) == len(REFS), 'amendment evidence references overlap')
    return deepcopy(value)


def paths(manifest):
    if KEY not in manifest:
        return set()
    proof = selection(manifest[KEY])
    return {Path(__file__).resolve(), *(_path(proof[key]['path']) for key in REFS)}


def inherit(source, target):
    """Carry an exact proof, refusing dropped or conflicting authority."""
    if KEY not in source:
        _require(KEY not in target, 'successor invents a budget amendment')
        return
    proof = selection(source[KEY])
    _require(KEY not in target or _canonical(selection(target[KEY])) == _canonical(proof),
             'successor changes its budget amendment')
    target[KEY] = proof


def _read(ref):
    path = _path(ref['path'])
    _require(path.is_file(), 'amendment evidence is not a regular file')
    raw = path.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'amendment evidence changed')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, 'duplicate amendment evidence key')
            result[key] = value
        return result
    try:
        document = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(BudgetStop('nonfinite amendment evidence')))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BudgetStop('malformed amendment JSON evidence') from exc
    _require(type(document) is dict, 'amendment evidence must be an object')
    return document


def _settled(ledger):
    rows = ledger.get('requests')
    _require(type(rows) is list and all(type(row) is dict and row.get('status') == 'settled' for row in rows),
             'amendment checkpoint has unresolved accounting')
    ids = [row.get('id') for row in rows]
    _require(all(type(key) is str and bool(key) for key in ids) and len(set(ids)) == len(ids),
             'amendment checkpoint request identities differ')
    return rows, sum((_money(row.get('cost_usd')) for row in rows), Decimal(0))


def _proof(value):
    try:
        return _proof_documents(value)
    except (KeyError, TypeError, AttributeError) as exc:
        raise BudgetStop('malformed amendment evidence structure') from exc


def _proof_documents(value):
    proof = selection(value)
    documents = {key: _read(proof[key]) for key in REFS}
    origin, previous, ledger, owner, authority = (documents[key] for key in REFS)
    old, new, default = (_money(proof[key]) for key in ('prior_total_usd', 'total_usd', 'default_attempt_usd'))
    _require(KEY not in origin and KEY not in previous, 'v1 budget amendment cannot chain increases')
    _require(_money(origin['budget']['additional_usd']) == old
             and _money(previous['budget']['additional_usd']) == old
             and _money(ledger['additional_cap_usd']) == old
             and all(_money(x) == default for x in (origin['budget']['per_attempt_usd'],
                 previous['budget']['per_attempt_usd'], ledger['attempt_cap_usd'])),
             'amendment changes its origin or default attempt cap')
    _require(previous.get('parent', {}).get('registration') == proof['origin_registration']['path']
             and previous['budget']['ledger_path'] == proof['predecessor_ledger']['path']
             and ledger.get('manifest_sha256') == proof['predecessor_registration']['sha256'],
             'amendment predecessor differs from its origin or ledger')
    _require(proof['predecessor_owner']['path'] != previous.get('sequence_state'),
             'amendment requires an immutable owner snapshot, not the live owner')
    expected_owner = {'schema_version': 1,
        'registration_sha256': proof['predecessor_registration']['sha256'],
        'ledger_path': proof['predecessor_ledger']['path'],
        'source_registration_sha256': proof['origin_registration']['sha256'],
        'parent_checkpoint_sha256': previous['budget']['continuation']['sha256']}
    _require(type(owner.get('schema_version')) is int and owner == expected_owner,
             'amendment owner is not its consumed predecessor')
    rows, cost = _settled(ledger)
    _require(cost <= old, 'amendment predecessor exceeds its historical ceiling')
    _require(authority.get('kind') == 'audit_sequence_additional_budget_authorization_receipt'
             and type(authority.get('schema_version')) is int and authority['schema_version'] == 1,
             'unsupported amendment authorization receipt')
    approval, predecessor = authority.get('authorization', {}), authority.get('predecessor', {})
    _require(type(approval) is dict and approval.get('additional_budget_authorized') is True
             and approval.get('currency') == 'USD' and type(approval.get('user_quote')) is str
             and bool(approval['user_quote'].strip())
             and _money(approval.get('prior_shared_cap_usd')) == old
             and _money(approval.get('additional_authorized_usd')) == _money(proof['increase_usd'])
             and _money(approval.get('new_shared_cap_usd')) == new,
             'amendment lacks the exact explicit budget authorization')
    _require(type(predecessor) is dict and all(predecessor.get(key) == value for key, value in {
        'registration_path': proof['predecessor_registration']['path'],
        'registration_sha256': proof['predecessor_registration']['sha256'],
        'ledger_path': proof['predecessor_ledger']['path'],
        'ledger_sha256': proof['predecessor_ledger']['sha256'],
        'canonical_owner_sha256': proof['predecessor_owner']['sha256']}.items())
        and type(predecessor.get('sequence_settled_rows')) is int
        and predecessor['sequence_settled_rows'] == len(rows)
        and _money(predecessor.get('sequence_accounted_usd')) == cost
        and _money(predecessor.get('registered_predecessor_shared_cap_usd')) == old,
        'authorization names another predecessor or accounting amount')
    return proof, documents


def _manifest_proof(manifest, *, require_pins):
    proof, documents = _proof(manifest[KEY])
    if require_pins:
        pins = manifest.get('pinned_files', {})
        # The caller's required_paths/implementation gate pins its helper. An
        # inherited registration may have pinned the same helper elsewhere.
        _require(all(pins.get(proof[key]['path']) == proof[key]['sha256'] for key in REFS),
                 'budget amendment authority is unpinned')
    origin = proof['origin_registration']
    if 'budget_sequence' in manifest:
        _require(manifest['budget_sequence']['origin']['registration'] == origin,
                 'budget amendment names another shared origin')
    else:
        _require(manifest.get('parent', {}).get('registration') == origin['path'],
                 'budget amendment names another audit origin')
    _require(_money(manifest['budget']['per_attempt_usd']) == _money(proof['default_attempt_usd'])
             and _money(manifest['budget']['additional_usd']) == _money(proof['total_usd']),
             'manifest changes the amended budget identity')
    return proof, documents


def effective_total(manifest, generation, *, require_pins=True):
    if KEY not in manifest:
        total = _money(generation['budget']['additional_usd'])
        _require(_money(manifest['budget']['additional_usd']) == total,
                 'budget changes its original allocation without an amendment')
        return total
    proof, documents = _manifest_proof(manifest, require_pins=require_pins)
    _require(_canonical(generation) == _canonical(documents['origin_registration']),
             'budget amendment changes original generation identity')
    return _money(proof['total_usd'])


def _checkpoint(proof, documents, previous, checkpoint_sha256):
    rows, cost = _settled(previous)
    original = documents['predecessor_ledger']['requests']
    _require(_canonical(rows[:len(original)]) == _canonical(original),
             'amendment checkpoint rewrites or drops historical rows')
    cap = _money(previous['additional_cap_usd'])
    _require(_money(previous['attempt_cap_usd']) == _money(proof['default_attempt_usd'])
             and cost <= cap, 'amendment checkpoint changes its cap or exceeds it')
    if cap == _money(proof['prior_total_usd']):
        _require(checkpoint_sha256 == proof['predecessor_ledger']['sha256']
                 and _canonical(previous) == _canonical(documents['predecessor_ledger']),
                 'budget increase is not anchored to its exact closed checkpoint')
        return True
    _require(cap == _money(proof['total_usd']), 'unsupported repeated or unrelated budget increase')
    return False


def validate_predecessor(manifest, previous, *, checkpoint_sha256, require_pins=True):
    if KEY not in manifest:
        _require(_money(previous['additional_cap_usd']) == _money(manifest['budget']['additional_usd'])
                 and _money(previous['attempt_cap_usd']) == _money(manifest['budget']['per_attempt_usd']),
                 'predecessor changes unamended budget caps')
        return
    proof, documents = _manifest_proof(manifest, require_pins=require_pins)
    _checkpoint(proof, documents, previous, checkpoint_sha256)


def ledger_bridge(manifest, previous, *, checkpoint_sha256):
    validate_predecessor(manifest, previous, checkpoint_sha256=checkpoint_sha256)
    if KEY not in manifest:
        return {}
    # Same-cap descendants retain proof so exact typed-history checks remain
    # active on reopens; validate_ledger_transition applies no second increase.
    return {'budget_amendment': deepcopy(manifest[KEY])}


def validate_ledger_transition(value, previous, *, checkpoint_sha256, total_cap, attempt_cap):
    """Return a proof digest only for the exact first cap-changing import."""
    proof, documents = _proof(value)
    _require(_money(total_cap) == _money(proof['total_usd'])
             and _money(attempt_cap) == _money(proof['default_attempt_usd']),
             'ledger differs from the authorized amendment ceiling')
    changed = _checkpoint(proof, documents, previous, checkpoint_sha256)
    return hashlib.sha256(_canonical(proof)).hexdigest() if changed else None
