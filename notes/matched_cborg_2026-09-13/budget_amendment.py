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
SECOND_KIND = 'additive_sequence_budget_v2'
#: One further increase after any earlier ones, each link naming its
#: predecessor proof (#2468). v1 and v2 proofs validate exactly as before.
CHAIN_KIND = 'additive_sequence_budget_chain_v1'
CHAIN_RECEIPT_VERSION = 3
#: A bound on validation work; a real lineage adds one link per authorization.
MAX_CHAIN_LINKS = 16
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
    if type(value) is dict and value.get('kind') == SECOND_KIND:
        return _second_selection(value)
    if type(value) is dict and value.get('kind') == CHAIN_KIND:
        return _chain_selection(value)
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
    if proof['kind'] == SECOND_KIND:
        return {Path(__file__).resolve(), *(Path(path) for path in _second_refs(proof))}
    if proof['kind'] == CHAIN_KIND:
        return {Path(__file__).resolve(), *(Path(path) for path in _chain_refs(proof))}
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
    if proof['kind'] == SECOND_KIND:
        return _second_documents(proof)
    if proof['kind'] == CHAIN_KIND:
        proof, documents = _increase_documents(proof, 'chained', CHAIN_RECEIPT_VERSION)
        _distinct_receipt_quotes(proof)
        return proof, documents
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
        if proof['kind'] == SECOND_KIND:
            _require(all(pins.get(path) == identity for path, identity in _second_refs(proof).items()),
                     'prior budget amendment authority is unpinned')
        if proof['kind'] == CHAIN_KIND:
            _require(all(pins.get(path) == identity for path, identity in _chain_refs(proof).items()),
                     'prior budget amendment authority is unpinned')
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


def _second_selection(value):
    """Select exactly a second increase, never a recursive amendment chain."""
    _require(set(value) == {'kind', *REFS, *AMOUNTS, 'prior_amendment', 'authorization_quote'},
             'unsupported second budget amendment selection')
    prior = value['prior_amendment']
    _require(type(prior) is dict and prior.get('kind') == KIND,
             'second amendment requires exactly one prior v1 amendment')
    prior = selection(prior)
    base = {key: value[key] for key in ('kind', *REFS, *AMOUNTS)}
    base['kind'] = KIND
    selection(base)
    _require(type(value['authorization_quote']) is str and bool(value['authorization_quote'].strip()),
             'second amendment quote must be exact nonblank text')
    _require(_canonical(value['origin_registration']) == _canonical(prior['origin_registration'])
             and _money(value['default_attempt_usd']) == _money(prior['default_attempt_usd'])
             and _money(value['prior_total_usd']) == _money(prior['total_usd']),
             'second amendment changes origin, prior allocation or default cap')
    _second_refs(value)
    return deepcopy(value)


def _second_refs(proof):
    references = {}
    for node in (proof['prior_amendment'], proof):
        for key in REFS:
            ref = node[key]
            _require(ref['path'] not in references or
                     (key == 'origin_registration' and references[ref['path']] == ref['sha256']),
                     'second amendment reuses or conflicts with earlier evidence')
            references[ref['path']] = ref['sha256']
    for key in REFS[1:]:
        _require(proof[key]['sha256'] != proof['prior_amendment'][key]['sha256'],
                 'second amendment reuses earlier authority or predecessor identity')
    return references


def _second_documents(proof):
    """Bind a new quoted authority to the full immediate audit checkpoint.

    The prior proof is v1 only. Its origin and every earlier accounting row
    stay unchanged. The caller still owns live-owner freshness and claims;
    this read-only proof never grants any per-attempt exception.
    """
    return _increase_documents(proof, 'second', 2)


def _increase_documents(proof, name, receipt_version):
    """The documents of one increase after an earlier proof: v2 after v1, or a
    chained link after any proof (#2468). Only the receipt version and the
    wording of refusals differ."""
    prior, prior_documents = _proof(proof['prior_amendment'])
    documents = {key: _read(proof[key]) for key in REFS}
    origin, previous, ledger, owner, authority = (documents[key] for key in REFS)
    old, new, default = (_money(proof[key]) for key in ('prior_total_usd', 'total_usd', 'default_attempt_usd'))
    _require(_canonical(origin) == _canonical(prior_documents['origin_registration'])
             and KEY not in origin and previous.get('kind') == 'd4d_native_audit_continuation'
             and _canonical(previous.get(KEY)) == _canonical(prior),
             f'{name} amendment changes its original allocation or exact prior authority')
    _require(_money(previous['budget']['additional_usd']) == old
             and _money(ledger['additional_cap_usd']) == old
             and all(_money(x) == default for x in (origin['budget']['per_attempt_usd'],
                 previous['budget']['per_attempt_usd'], ledger['attempt_cap_usd']))
             and type(origin['budget'].get('prices_per_token')) is dict
             and bool(origin['budget']['prices_per_token'])
             and type(previous['budget'].get('prices_per_token')) is dict
             and _canonical(previous['budget'].get('prices_per_token')) ==
                 _canonical(origin['budget'].get('prices_per_token')),
             f'{name} amendment changes historical caps or prices')
    _require(previous.get('parent', {}).get('registration') == proof['origin_registration']['path']
             and previous['budget']['ledger_path'] == proof['predecessor_ledger']['path']
             and ledger.get('manifest_sha256') == proof['predecessor_registration']['sha256'],
             f'{name} amendment does not name its exact immediate ledger')
    _require(proof['predecessor_owner']['path'] != previous.get('sequence_state'),
             'amendment requires an immutable owner snapshot, not the live owner')
    expected_owner = {'schema_version': 1,
        'registration_sha256': proof['predecessor_registration']['sha256'],
        'ledger_path': proof['predecessor_ledger']['path'],
        'source_registration_sha256': proof['origin_registration']['sha256'],
        'parent_checkpoint_sha256': previous['budget']['continuation']['sha256']}
    _require(_canonical(owner) == _canonical(expected_owner),
             f'{name} amendment owner is not its consumed immediate predecessor')
    _checkpoint(prior, prior_documents, ledger, proof['predecessor_ledger']['sha256'])
    rows, cost = _settled(ledger)
    _require(type(authority.get('schema_version')) is int and authority['schema_version'] == receipt_version
             and authority.get('kind') == 'audit_sequence_additional_budget_authorization_receipt',
             f'unsupported {name} amendment authorization receipt')
    expected_authorization = {'additional_budget_authorized': True, 'currency': 'USD',
        'user_quote': proof['authorization_quote'], 'prior_shared_cap_usd': proof['prior_total_usd'],
        'additional_authorized_usd': proof['increase_usd'], 'new_shared_cap_usd': proof['total_usd']}
    _require(_canonical(authority.get('authorization')) == _canonical(expected_authorization),
             f'{name} amendment lacks exact quoted budget authorization')
    expected_lineage = {'origin_registration': proof['origin_registration'],
        'prior_amendment_sha256': hashlib.sha256(_canonical(prior)).hexdigest(),
        'original_shared_cap_usd': str(_money(origin['budget']['additional_usd']))}
    _require(_canonical(authority.get('lineage')) == _canonical(expected_lineage),
             f'{name} authorization changes the immutable prior amendment')
    expected_predecessor = {'registration_path': proof['predecessor_registration']['path'],
        'registration_sha256': proof['predecessor_registration']['sha256'],
        'ledger_path': proof['predecessor_ledger']['path'], 'ledger_sha256': proof['predecessor_ledger']['sha256'],
        'canonical_owner_sha256': proof['predecessor_owner']['sha256'],
        'registered_predecessor_shared_cap_usd': proof['prior_total_usd'],
        'sequence_settled_rows': len(rows), 'sequence_accounted_usd': str(cost)}
    _require(_canonical(authority.get('predecessor')) == _canonical(expected_predecessor),
             f'{name} authorization names another full accounting checkpoint')
    return proof, documents


def _chain_selection(value):
    """Select one increase after earlier ones (#2468), up to MAX_CHAIN_LINKS proofs in all.

    The prior proof may be v1, v2 or another chained link, and is validated
    recursively. Each link is one quoted authorization: its quote states the
    increase or the new cap in dollars, and no earlier link's proof or receipt
    quotes the same message (whitespace and case aside). The new cap is its
    prior's total plus this increase, never an amount to add again.
    """
    _require(set(value) == {'kind', *REFS, *AMOUNTS, 'prior_amendment', 'authorization_quote'},
             'unsupported chained budget amendment selection')
    depth, node = 0, value
    while type(node) is dict and node.get('kind') == CHAIN_KIND:
        depth += 1
        _require(depth < MAX_CHAIN_LINKS, 'budget amendment chain is longer than its bound')
        node = node.get('prior_amendment')
    prior = selection(value['prior_amendment'])
    base = {key: value[key] for key in ('kind', *REFS, *AMOUNTS)}
    base['kind'] = KIND
    selection(base)
    _require(type(value['authorization_quote']) is str and bool(value['authorization_quote'].strip()),
             'chained amendment quote must be exact nonblank text')
    # The quote must state this increase or the cap it reaches, so one
    # message cannot be recorded as a larger or a different one (#2488).
    stated = {_money(amount.replace(',', '')) for amount in
              re.findall(r'\$\s?([0-9][0-9,]*(?:\.[0-9]+)?)', value['authorization_quote'])}
    _require(bool(stated & {_money(value['increase_usd']), _money(value['total_usd'])}),
             'chained amendment quote does not state its increase or new cap')
    _require(_canonical(value['origin_registration']) == _canonical(prior['origin_registration'])
             and _money(value['default_attempt_usd']) == _money(prior['default_attempt_usd'])
             and _money(value['prior_total_usd']) == _money(prior['total_usd']),
             'chained amendment changes origin, prior allocation or default cap')
    _chain_refs(value)
    return deepcopy(value)


def _links(proof):
    """Every proof in the chain, oldest first."""
    links = [proof]
    while links[-1]['kind'] != KIND:
        _require(len(links) < MAX_CHAIN_LINKS, 'budget amendment chain is longer than its bound')
        links.append(links[-1]['prior_amendment'])
    return links[::-1]


def _quote(text):
    return ' '.join(text.split()).casefold()


def _chain_refs(proof):
    """Every document the chain names. Only the origin is shared; no later
    link reuses an earlier link's path or the identity of its authority,
    predecessor, ledger or owner."""
    references, identities = {}, set()
    for link in _links(proof):
        for key in REFS:
            ref = link[key]
            _require(ref['path'] not in references or
                     (key == 'origin_registration' and references[ref['path']] == ref['sha256']),
                     'chained amendment reuses or conflicts with earlier evidence')
            references[ref['path']] = ref['sha256']
        current = {link[key]['sha256'] for key in REFS[1:]}
        _require(not current & identities, 'chained amendment reuses earlier authority or predecessor identity')
        identities |= current
    # One quoted authorization funds one increase (#2488): each chained link
    # quotes a message no earlier link quoted. Earlier v1/v2 history is taken
    # as it was validated.
    _chain_quotes_are_new([(link['kind'], link.get('authorization_quote')) for link in _links(proof)])
    return references


def _chain_quotes_are_new(quotes):
    seen = set()
    for kind, quote in quotes:
        normal = _quote(quote) if isinstance(quote, str) else None
        _require(kind != CHAIN_KIND or normal not in seen, 'chained amendment reuses an earlier authorization quote')
        if normal is not None:
            seen.add(normal)


def _distinct_receipt_quotes(proof):
    """Every link's receipt quotes a different message, the v1 receipt included (#2488)."""
    quotes = []
    for link in _links(proof):
        authorization = _read(link['authorization']).get('authorization')
        _require(type(authorization) is dict and type(authorization.get('user_quote')) is str,
                 'amendment receipt lacks its quoted authorization')
        quotes.append((link['kind'], authorization['user_quote']))
    _chain_quotes_are_new(quotes)
