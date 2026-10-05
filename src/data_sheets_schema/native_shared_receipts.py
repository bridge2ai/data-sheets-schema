"""Pure captured receipt accounting for native_shared_generation_v1.

The native selection is distinct from both API receipt registrations. These
functions perform no file, runtime, provider or environment operations.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from threading import Lock

import yaml

from . import audit_omissions as omissions, receipts
from . import native_shared_contract as contract
from .chunking import chunk_texts, validate_manifest_mapping
from .grounding import declared_bases_of
from .receipt_completion_policy import coverage_counts
from .schema_snapshot import SchemaSnapshot


@dataclass(frozen=True)
class ReceiptResult:
    requested_paths: tuple[str, ...]
    request_json: bytes
    effective_receipt: bytes
    result_json: bytes
    carry_json: bytes


def schema_snapshot(selection, kind='full'):
    """Reconstruct the exact captured logical closure without a live resolver."""
    rows = [schema for schema in selection.schemas if schema.kind == kind]
    if len(rows) != 1:
        raise ValueError('native stage requires exactly one selected schema closure')
    schema = rows[0]
    names = {role: name for name, role in schema.import_roles}
    sources = tuple((names[item.pin.role], Path(item.pin.path), item.raw) for item in schema.sources)
    return SchemaSnapshot(sources, (str(sources[0][1]), schema.closure_sha256))



_CATALOG_PAYLOAD_BYTES = 40_000_000
_CATALOG_DOMAIN = 'native_shared_receipt_catalog_v1'


def _catalog_key(selection, snapshot):
    """Validate immutable carrier identity before considering a pure hit."""
    rows = [item for item in selection.schemas if item.kind == 'full']
    if len(rows) != 1 or type(rows[0]) is not contract.SchemaClosureCapture:
        raise ValueError('receipt catalog requires one captured full schema')
    schema = rows[0]
    # Recheck pin integrity even if a caller has bypassed frozen dataclasses.
    sources = tuple(contract.CapturedArtifact(
        contract.ArtifactPin(item.pin.role, item.pin.path, item.pin.bytes, item.pin.sha256), item.raw)
        for item in schema.sources)
    checked = contract.SchemaClosureCapture(schema.closure_sha256, schema.import_roles,
        schema.kind, schema.root_class, schema.root_name, sources)
    names = {role: name for name, role in checked.import_roles}
    expected = tuple((names[item.pin.role], Path(item.pin.path), item.raw) for item in sources)
    if snapshot.sources != expected:
        raise ValueError('receipt catalog snapshot differs from its captured schema')
    if sum(len(item.raw) for item in sources) > omissions.MAX_SCHEMA_BYTES:
        raise ValueError('schema closure exceeds byte bound')
    metadata = contract.canonical({'domain': _CATALOG_DOMAIN, 'kind': checked.kind,
        'root_class': checked.root_class, 'root_name': checked.root_name,
        'root_path': sources[0].pin.path, 'closure_sha256': checked.closure_sha256,
        'import_roles': [list(row) for row in checked.import_roles],
        'sources': [{'name': names[item.pin.role], 'pin': contract.pin_dict(item.pin)} for item in sources],
        'declaration': selection.document()['inputs']['full_schema'],
        'mode': {'logical_paths': True, 'strict': True, 'namespace_orders': None},
        'limits': {'max_input_bytes': omissions.MAX_INPUT_BYTES,
            'max_schema_bytes': omissions.MAX_SCHEMA_BYTES, 'max_nodes': omissions.MAX_NODES,
            'max_depth': omissions.MAX_DEPTH, 'native': dict(contract.HARD_LIMITS),
            'supplied': selection.bounds()}})
    return metadata, tuple(item.raw for item in sources)


class _ReceiptCatalogContext:
    """One bounded byte-only derivation, owned by one captured transaction."""
    def __init__(self):
        self._entry = None
        self._bytes = 0
        self._lock = Lock()

    def catalog(self, selection, snapshot):
        key = _catalog_key(selection, snapshot)
        with self._lock:
            raw = self._entry[1] if self._entry is not None and self._entry[0] == key else None
        if raw is None:
            catalog = omissions._schema(snapshot.sources[0][1], schema_snapshot=snapshot, logical_paths=True)
            # LinkML URIorCURIE names have the same released JSON meaning.
            raw = omissions._json(catalog).encode('utf-8')
            result = contract.strict_json(raw, 'captured schema catalog', omissions.MAX_SCHEMA_BYTES)
            size = len(key[0]) + sum(len(item) for item in key[1]) + len(raw)
            if size <= _CATALOG_PAYLOAD_BYTES:
                with self._lock:
                    self._entry, self._bytes = (key, raw), size
            return result
        return contract.strict_json(raw, 'captured schema catalog', omissions.MAX_SCHEMA_BYTES)


def _catalog_context(value=None):
    if value is None:
        return _ReceiptCatalogContext()
    if type(value) is not _ReceiptCatalogContext:
        raise ValueError('receipt catalog context must be private derivation storage')
    return value


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


def floor(coverage, selection):
    """The released strict counters and exact fraction comparison, native authority."""
    covered, eligible = coverage_counts(coverage)
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
    chosen = selection.document()['inputs']
    bounds = selection.bounds()
    for raw in (full_raw, receipt_raw):
        if type(raw) is not bytes:
            raise ValueError('native initial inputs require captured bytes')
        if len(raw) > min(bounds['max_input_bytes'], contract.HARD_LIMITS['original_full_bytes']):
            raise ValueError('phase-1 input exceeds the supplied native byte bound')
    full = omissions._mapping(full_raw, 'sealed native full')
    receipt = omissions._mapping(receipt_raw, 'sealed native receipt')
    bundle = selection.raw(chosen['bundle']['path'])
    manifest = omissions._mapping(selection.raw(chosen['chunk_manifest']['path']), 'captured chunks')
    validate_manifest_mapping(manifest, bundle, manifest.get('bundle'))
    md5 = hashlib.md5(bundle).hexdigest()
    if receipt.get('bundle_md5') != md5:
        raise ValueError('native original receipt differs from captured bundle')
    texts = dict(zip((row['id'] for row in manifest['chunks']),
                     chunk_texts(bundle.decode('utf-8'), manifest['chunks'])))
    if len(receipts.populated_leaves(full)) > bounds['max_populated_paths']:
        raise ValueError('complete native populated inventory exceeds the global bound')
    snapshot = schema_snapshot(selection)
    # The released rule uses the selected root's declared prefixes. Explicit
    # empty bases are meaningful; never fall back to the current installation.
    bases = tuple(declared_bases_of(omissions._mapping(snapshot.sources[0][2], 'captured schema')))
    catalog = _catalog_context(_catalogs).catalog(selection, snapshot)
    context = omissions._mapping(selection.raw(chosen['context']['path']), 'scope context', json_only=True)
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
    full, receipt, manifest, texts, md5, bases, _, _ = _inputs(selection, phase1, _catalogs=catalogs)
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
        'request_sha256': contract.sha(contract.canonical(request)),
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
    return ReceiptResult(tuple(listed), contract.canonical(request), effective, result_raw, contract.canonical(carry))


def check_final(selection, execution, phase1, completion, *, final_full, final_receipt):
    """Check final coverage against the same selected original/effective bytes."""
    if (completion.selection_sha256 != selection.registration.pin.sha256
            or completion.execution_sha256 != execution.execution.pin.sha256
            or completion.phase1_seal_sha256 != phase1.seal.pin.sha256
            or final_receipt != completion.effective_receipt.raw):
        raise ValueError('final native receipt lineage differs from checked stage completion')
    original, _, manifest, texts, md5, bases, _, _ = _inputs(selection, phase1)
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
