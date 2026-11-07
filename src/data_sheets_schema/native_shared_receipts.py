"""U3-C receipt delivery; U3-B supplies the owner context at integration.

This fragment intentionally does not define the owner-context functions.
It must be combined with the committed U3-B section before stage validation.
"""
from __future__ import annotations

# BEGIN U3-C RECEIPT DELIVERY
from dataclasses import dataclass
import hashlib

import yaml

from . import audit_omissions as omissions, receipts
from . import native_shared_contract as contract
from .chunking import chunk_texts, validate_manifest_mapping

@dataclass(frozen=True)
class ReceiptResult:
    requested_paths: tuple[str, ...]
    request_json: bytes
    effective_receipt: bytes
    result_json: bytes
    carry_json: bytes


def omission_assets(selection):
    selected = selection.document()['selection']['assets']
    prefix = 'src/data_sheets_schema/omission_inventory_v1/'
    rows = []
    for name in omissions.ASSET_SHA256:
        pin = selected.get(prefix + name)
        if pin is None:
            raise ValueError('native selection omits the captured omission contract')
        raw = selection.raw(pin['path'])
        if len(raw) != pin['bytes'] or contract.sha(raw) != pin['sha256']:
            raise ValueError('native omission asset capture differs from selection')
        rows.append((name, raw))
    captured = tuple(rows)
    omissions.captured_asset_bytes(captured)
    return captured


def output_ceiling(execution):
    """Sole R assertion; no per-stage enforcement or session token budget."""
    if execution.runtime_declaration.pin.sha256 != execution.runtime_declaration_sha256:
        raise ValueError('native runtime declaration identity differs')
    runtime = contract.strict_json(execution.runtime_declaration.raw, 'runtime declaration')
    limits = runtime.get('limits')
    if type(limits) is not dict:
        raise ValueError('native runtime declaration lacks asserted output ceiling')
    return contract.positive_int(limits.get('maxOutputTokens'), 'asserted runtime output ceiling')


def policy(selection):
    descriptor = contract.strict_json(selection.descriptor.raw, 'native descriptor')
    expected = descriptor.get('receipt_policy')
    contract.exact(expected, {'path', 'sha256'}, 'native descriptor receipt policy')
    selected = selection.document()['selection']['assets'].get(expected['path'])
    if selected is None or selected['sha256'] != expected['sha256']:
        raise ValueError('native receipt policy is outside its exact selected asset role')
    raw = selection.raw(selected['path'])
    if len(raw) != selected['bytes'] or contract.sha(raw) != expected['sha256']:
        raise ValueError('native receipt policy asset bytes differ from the descriptor')
    return contract.parse_receipt_policy(selection.receipt_policy.raw, expected['sha256'])


def _coverage_integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer, not a boolean')
    return value


def _coverage_counts(coverage):
    """Native copy of the released counter checks, without API policy selection.

    The current API module exposes these only inside evaluate_floor. Keep its
    policy route untouched; the native registration selects a different floor.
    """
    if not isinstance(coverage, dict):
        raise ValueError('receipt coverage must be a mapping')
    eligible = _coverage_integer(coverage.get('receiptable'), 'receiptable')
    covered = _coverage_integer(coverage.get('with_receipt'), 'with_receipt')
    if covered > eligible:
        raise ValueError('with_receipt exceeds receiptable')
    for key, value in coverage.items():
        if not isinstance(key, str):
            raise ValueError('coverage keys must be strings')
        if value is not None and (key.endswith('_count') or key in {'receipt_paths', 'exempt_on_carried_identifier'}):
            _coverage_integer(value, key)
    if 'populated' in coverage or 'exempt' in coverage:
        populated = _coverage_integer(coverage.get('populated'), 'populated')
        exempt = _coverage_integer(coverage.get('exempt'), 'exempt')
        if populated != eligible + exempt:
            raise ValueError('coverage populated/exempt/receiptable counters disagree')
        if coverage.get('exempt_on_carried_identifier') is not None and coverage['exempt_on_carried_identifier'] > exempt:
            raise ValueError('carried-identifier exemptions exceed all exempt leaves')
    missing = eligible - covered
    truncated = coverage.get('without_receipt_truncated')
    if truncated is not None:
        _coverage_integer(truncated, 'without_receipt_truncated')
        if truncated > missing or 'without_receipt' not in coverage:
            raise ValueError('coverage truncation count lacks consistent missing paths')
    if 'without_receipt' in coverage:
        paths = coverage['without_receipt']
        truncated = 0 if truncated is None else truncated
        if not isinstance(paths, list) or any(not isinstance(p, str) for p in paths) or len(set(paths)) != len(paths) or len(paths) + truncated != missing:
            raise ValueError('coverage missing paths/counters disagree')
    for key in ('never_receipted', 'added_after_receipt'):
        if coverage.get(key) is not None:
            _coverage_integer(coverage[key], key)
            if coverage[key] > missing:
                raise ValueError(f'coverage {key} exceeds uncovered leaves')
    if all(coverage.get(k) is not None for k in ('never_receipted', 'added_after_receipt')):
        if coverage['never_receipted'] + coverage['added_after_receipt'] != missing:
            raise ValueError('coverage phase-1 missing counters disagree')
    return covered, eligible


def floor(coverage, selection):
    """The released strict counters and exact fraction comparison, native authority."""
    covered, eligible = _coverage_counts(coverage)
    chosen = policy(selection)['coverage_floor']
    result = {'with_receipt': covered, 'receiptable': eligible, 'floor': chosen,
              'passed': False, 'registration_sha256': selection.receipt_policy.pin.sha256}
    if chosen['state'] == 'pending':
        return {**result, 'state': 'pending', 'reason': 'diagnostic pilot; coverage floor not registered'}
    if eligible == 0:
        return {**result, 'state': 'not_applicable', 'reason': 'no eligible leaves; coverage unmeasurable'}
    passed = covered * chosen['denominator'] >= eligible * chosen['numerator']
    return {**result, 'state': 'passed' if passed else 'failed', 'passed': passed}


def _inputs(selection, phase1, *, _catalogs=None):
    return _raw_inputs(selection, phase1.full.raw, phase1.original_receipt.raw, _catalogs=_catalogs)


def _raw_inputs(selection, full_raw, receipt_raw, *, _catalogs=None):
    """Validate each occurrence; only U3-B's schema catalog may be reused."""
    chosen = selection.document()['inputs']
    bounds = selection.bounds()
    for raw in (full_raw, receipt_raw):
        if type(raw) is not bytes:
            raise ValueError('native initial inputs require captured bytes')
        if len(raw) > min(bounds['max_input_bytes'], contract.HARD_LIMITS['original_full_bytes']):
            raise ValueError('phase-1 input exceeds the supplied native byte bound')
    bundle = selection.raw(chosen['bundle']['path'])
    manifest_raw = selection.raw(chosen['chunk_manifest']['path'])
    context_raw = selection.raw(chosen['context']['path'])
    snapshot = schema_snapshot(selection)
    bases, catalog = _catalog_context(_catalogs).schema_data(selection, snapshot)
    full = omissions._mapping(full_raw, 'sealed native full')
    receipt = omissions._mapping(receipt_raw, 'sealed native receipt')
    manifest = omissions._mapping(manifest_raw, 'captured chunks')
    validate_manifest_mapping(manifest, bundle, manifest.get('bundle'))
    md5 = hashlib.md5(bundle).hexdigest()
    if receipt.get('bundle_md5') != md5:
        raise ValueError('native original receipt differs from captured bundle')
    texts = dict(zip((row['id'] for row in manifest['chunks']),
                     chunk_texts(bundle.decode('utf-8'), manifest['chunks'])))
    if len(receipts.populated_leaves(full)) > bounds['max_populated_paths']:
        raise ValueError('complete native populated inventory exceeds the global bound')
    context = omissions._mapping(context_raw, 'scope context', json_only=True)
    owners = omissions._owners(full, catalog, context['vocabulary'])
    scopes = [row['owner'] for row in context['scopes']]
    if scopes.count('') != 1 or len(set(scopes)) != len(scopes) or any(p not in owners for p in scopes):
        raise ValueError('native scope must name distinct existing full-record owners and root once')
    return full, receipt, manifest, texts, md5, bases, catalog, owners


def check_initial(selection, *, full_raw, receipt_raw):
    """Check actual initial bytes without inventing future seals or completion.

    The caller owns initialized execution/call/path authority. ``passed`` is
    only the released initial receipt checks; a final registered coverage floor
    cannot be certified before receipt completion and final reconstruction.
    """
    from .canary import receipt_floors

    full, receipt, manifest, texts, md5, bases, _, _ = _raw_inputs(selection, full_raw, receipt_raw)
    block = receipts.check(receipt, manifest, texts, full, md5, full,
                           instrument_version=4, identifier_bases=bases)
    # Compute ordinary structural/source-text gates before adding the selected
    # final-floor registration. Missing quotes/chunks and vacuity still refuse.
    structural = receipt_floors(block)
    selected_policy = policy(selection)
    pending = {**floor(block['slots'], selection), 'state': 'pending', 'passed': False,
        'reason': 'initial receipt check precedes completion and final stage reconstruction'}
    return {**block, 'expected': True, 'checked': True,
        'passed': not any(structural.values()), 'structural_receipt_floors': structural,
        'native_receipt_stage': 'phase1_initial', 'final_stage_complete': False,
        'coverage_floor': pending,
        'receipt_completion_policy': {
            'registration': {'sha256': selection.receipt_policy.pin.sha256,
                'raw_json': selection.receipt_policy.raw.decode('utf-8')},
            'runtime_policy_sha256': selected_policy['runtime_policy_sha256']},
        'native_shared_receipt_policy': {'sha256': selection.receipt_policy.pin.sha256,
            'raw_json': selection.receipt_policy.raw.decode('utf-8')},
        'identity_rules': {'basis': 'captured native full schema', 'identifier_bases': [list(p) for p in bases]},
        'native_initial_inputs': {'selection_sha256': selection.registration.pin.sha256,
            'full_sha256': contract.sha(full_raw), 'receipt_sha256': contract.sha(receipt_raw)}}


def prepare(selection, execution, phase1):
    return _prepare(selection, execution, phase1, _ReceiptCatalogContext())


def _prepare(selection, execution, phase1, catalogs):
    full, receipt, manifest, texts, md5, bases, catalog, owners = _inputs(selection, phase1, _catalogs=catalogs)
    chosen = selection.document()['inputs']
    paths = receipts.uncovered_receiptable_leaves(receipt, manifest, texts, full, md5,
                                                  original=full, identifier_bases=bases)
    return {'protocol': contract.NAME, 'stage': 'receipt',
        'selection_sha256': selection.registration.pin.sha256,
        'receipt_policy': policy(selection),
        'phase1_seal_sha256': phase1.seal.pin.sha256,
        'original_full_sha256': phase1.full.pin.sha256,
        'original_receipt_sha256': phase1.original_receipt.pin.sha256,
        'record_yaml': phase1.full.raw.decode('utf-8'),
        'receipt_yaml': phase1.original_receipt.raw.decode('utf-8'),
        'bundle': selection.raw(chosen['bundle']['path']).decode('utf-8'),
        'manifest': selection.raw(chosen['chunk_manifest']['path']).decode('utf-8'),
        'schema': catalog, 'owner_classes': owners, 'requested_paths': paths,
        'max_output_tokens': output_ceiling(execution),
        'output_limit_basis': 'asserted runtime output ceiling; not per-stage enforcement or a whole-session token budget',
        'response_contract': 'Return only {rereceipt: [...]}; exactly one existing path and receipt {chunk,snippet} or unsupported:true with reason per requested leaf. Verified quotes do not establish semantic support.'}


def complete(selection, execution, phase1, response_raw):
    return _complete(selection, execution, phase1, response_raw, _ReceiptCatalogContext())


def _complete(selection, execution, phase1, response_raw, catalogs):
    request = _prepare(selection, execution, phase1, catalogs)
    request_raw = contract.canonical(request)
    listed = request['requested_paths']
    if response_raw is None:
        if listed:
            raise ValueError('receipt response is mandatory for every uncovered leaf')
        answers, problem = [], None
    else:
        if not listed:
            raise ValueError('zero-work receipt cannot consume a model response')
        if type(response_raw) is not bytes or len(response_raw) > min(
                selection.bounds()['max_response_bytes'], omissions.MAX_RESPONSE_BYTES):
            raise ValueError('receipt response exceeds the supplied bound')
        problem = None
        try:
            parsed = omissions._mapping(response_raw, 'native receipt response')
            contract.exact(parsed, {'rereceipt'}, 'native receipt answer')
            answers = parsed['rereceipt']
            if type(answers) is not list:
                raise ValueError('rereceipt must be a list')
        except ValueError as exc:
            answers, problem = [], str(exc)
    full, receipt, manifest, texts, md5, bases, _, _ = _inputs(selection, phase1, _catalogs=catalogs)
    before = receipts.check(receipt, manifest, texts, full, md5, full,
                             instrument_version=4, identifier_bases=bases)
    merged = receipts.apply_rereceipt(receipt, full, answers, texts, listed=listed, instrument_version=4)
    after = receipts.check(merged['receipt'], manifest, texts, full, md5, full,
                            instrument_version=4, identifier_bases=bases)
    supplied = {row['path'] for row in answers if type(row) is dict and type(row.get('path')) is str and row['path'] in listed}
    rejected = {row['path'] for row in merged['rejections'] if type(row.get('path')) is str and row['path'] in listed}
    unanswered = [path for path in listed if path not in supplied]
    pending = receipts.uncovered_receiptable_leaves(merged['receipt'], manifest, texts, full, md5,
                                                    original=full, identifier_bases=bases)
    accepted = merged['added'] + merged['already_present'] + merged['unsupported']
    effective = (phase1.original_receipt.raw if response_raw is None else
        yaml.safe_dump(merged['receipt'], sort_keys=False, allow_unicode=True, width=10000).encode('utf-8'))
    result = {'protocol': contract.NAME, 'receipt_instrument_version': 4,
        'selection_sha256': selection.registration.pin.sha256,
        'policy_sha256': selection.receipt_policy.pin.sha256,
        'request_sha256': contract.sha(request_raw),
        'response_sha256': None if response_raw is None else contract.sha(response_raw),
        'original_receipt_sha256': phase1.original_receipt.pin.sha256,
        'effective_receipt_sha256': contract.sha(effective),
        'state': 'answers_complete' if accepted == len(listed) and not merged['rejected'] and not problem else 'answers_incomplete',
        'response_problem': problem, 'requested_paths': listed, 'unanswered_paths': unanswered,
        'rejected_paths': [path for path in listed if path in rejected], 'still_uncovered_paths': pending,
        'counts': {'requested': len(listed), 'answers_received': len(answers), 'accepted': accepted,
            'unanswered': len(unanswered), 'rejected_answers': merged['rejected'], 'rejected_paths': len(rejected),
            'receipts_added': merged['added'], 'already_present': merged['already_present'],
            'unsupported': merged['unsupported'], 'never_receipted_before': len(listed),
            'never_receipted_after': len(pending), 'status_reversals_added': len(merged['status_changed'])},
        'unsupported_audit_candidates': merged['unsupported_paths'], 'rejections': merged['rejections'],
        'added_pairs': merged['added_pairs'], 'before': before, 'after': after,
        'coverage_floor': floor(after['slots'], selection), 'semantic_support': 'unverified'}
    result_raw = contract.canonical(result)
    carry = {'selection_sha256': selection.registration.pin.sha256,
        'original_full_sha256': phase1.full.pin.sha256,
        'original_receipt_sha256': phase1.original_receipt.pin.sha256,
        'effective_receipt_sha256': contract.sha(effective), 'result_sha256': contract.sha(result_raw),
        'response_sha256': result['response_sha256'],
        'unsupported_audit_candidates': merged['unsupported_paths'],
        'unanswered_paths': unanswered, 'rejected_paths': result['rejected_paths'],
        'rejections': merged['rejections'], 'added_pairs': merged['added_pairs'],
        'scientific_support': 'unverified; independent audit required, no deletion instruction'}
    built = ReceiptResult(tuple(listed), request_raw, effective, result_raw, contract.canonical(carry))
    return built


def check_final(selection, execution, phase1, completion, *, final_full, final_receipt):
    """Check final coverage against the same selected original/effective bytes."""
    return _check_final(selection, execution, phase1, completion,
                        final_full=final_full, final_receipt=final_receipt, _catalogs=None)


def _check_final(selection, execution, phase1, completion, *, final_full, final_receipt, _catalogs=None):
    if (completion.selection_sha256 != selection.registration.pin.sha256
            or completion.execution_sha256 != execution.execution.pin.sha256
            or completion.phase1_seal_sha256 != phase1.seal.pin.sha256
            or final_receipt != completion.effective_receipt.raw):
        raise ValueError('final native receipt lineage differs from checked stage completion')
    original, _, manifest, texts, md5, bases, _, _ = _inputs(selection, phase1, _catalogs=_catalogs)
    full = omissions._mapping(final_full, 'native final full')
    receipt = omissions._mapping(final_receipt, 'native effective receipt')
    block = receipts.check(receipt, manifest, texts, full, md5, original,
                           instrument_version=4, identifier_bases=bases)
    selected_policy = policy(selection)
    return {**block, 'expected': True, 'checked': True,
            'native_receipt_stage': 'final', 'final_stage_complete': True,
            'coverage_floor': floor(block['slots'], selection),
            'receipt_completion_policy': {
                'registration': {'sha256': selection.receipt_policy.pin.sha256,
                    'raw_json': selection.receipt_policy.raw.decode('utf-8')},
                'runtime_policy_sha256': selected_policy['runtime_policy_sha256']},
            'native_shared_receipt_policy': {'sha256': selection.receipt_policy.pin.sha256,
                'raw_json': selection.receipt_policy.raw.decode('utf-8')},
            'identity_rules': {'basis': 'captured native full schema', 'identifier_bases': [list(p) for p in bases]},
            'native_stage_completion_history_sha256': completion.history_sha256}


_DEFAULT_CHECK_FINAL = check_final
# END U3-C RECEIPT DELIVERY
