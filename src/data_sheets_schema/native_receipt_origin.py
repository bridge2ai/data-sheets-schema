"""Explicit v1 native receipt-origin reporting from already captured bytes.

This module does not read paths, reconstruct authority, or change gate verdicts.
Registrations opt in; every saved reader compares the report independently.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath

KEY = 'receipt_origin_reporting'
REPORT_KEY = 'receipt_origin'
SCOPE = 'Reported history only; no semantic support, scientific acceptance or gate decision.'
FAMILIES = {
    'd4d_native_attribution_execution_registration': 'native_attribution',
    'd4d_native_neutral_attempt_supervisor': 'neutral_supervisor',
    'd4d_native_shared_execution_registration': 'native_shared',
}


def _path(value):
    if (type(value) is not str or not value.startswith('/') or '\x00' in value
            or str(PurePosixPath(value)) != value or '..' in PurePosixPath(value).parts):
        raise ValueError('receipt-origin identity requires a canonical recorded absolute path')
    return value


def declaration(attempt_directory, artifact_paths):
    """Derive identity only from the constructor's already verified selection."""
    return {'version': 1,
            'transcript_path': _path(str(PurePosixPath(_path(attempt_directory)) / 'transcript.jsonl')),
            'receipt_path': _path(artifact_paths['receipt']),
            'full_path': _path(artifact_paths['full'])}


def version(value):
    if KEY not in value:
        return 0
    declared = value[KEY]
    if (type(declared) is not dict or set(declared) != {
            'version', 'transcript_path', 'receipt_path', 'full_path'}
            or type(declared['version']) is not int or declared['version'] != 1):
        raise ValueError('unsupported or malformed explicit receipt-origin reporting declaration')
    for key in ('transcript_path', 'receipt_path', 'full_path'):
        _path(declared[key])
    if value.get('kind') not in FAMILIES:
        raise ValueError('receipt-origin reporting requires a fixed native registration family')
    return 1


def _member(path, raw, aliases, metadata):
    target = aliases.get(path, path)
    meta = metadata.get(target)
    body = raw.get(target)
    if (type(target) is not str or type(meta) is not dict
            or meta.get('exists') is not True or meta.get('regular') is not True
            or type(body) is not bytes):
        return None, None
    return {'path': path, 'captured_path': target, 'bytes': len(body),
            'sha256': hashlib.sha256(body).hexdigest()}, body


def required_paths(value, gate, aliases):
    """Names whose bytes an existing saved-file validation loop should retain."""
    if not version(value):
        return ()
    declared = value[KEY]
    paths = [declared[k] for k in ('transcript_path', 'receipt_path', 'full_path')]
    if FAMILIES[value['kind']] == 'native_shared':
        effective = gate.get('effective_receipt')
        if type(effective) is dict and type(effective.get('path')) is str:
            paths.append(effective['path'])
    return tuple(sorted({aliases.get(path, path) for path in paths}))


def report(value, gate, *, raw, aliases, metadata):
    """Build the same pure envelope for finalization and saved reconstruction."""
    if version(value) != 1:
        raise ValueError('receipt-origin report was not explicitly registered')
    from . import receipt_origin as instrument
    declared = value[KEY]
    family = FAMILIES[value['kind']]
    inputs, bodies = {}, {}
    for name, key in (('transcript', 'transcript_path'), ('full', 'full_path'),
                      ('original_receipt', 'receipt_path')):
        inputs[name], bodies[name] = _member(declared[key], raw, aliases, metadata)
    unknown = lambda reason: {'instrument': instrument.INSTRUMENT, 'status': 'unknown',
                              'reasons': [reason], 'transcripts': []}
    if any(inputs[name] is None for name in inputs):
        original = unknown('Selected transcript, full record or original receipt is absent from the captured basis.')
    else:
        identities = tuple(sorted(set(
            [(path, path) for path in metadata] + list(aliases.items()))))
        try:
            original = instrument.origin_captured(
                ((declared['transcript_path'], bodies['transcript']),),
                receipt_raw=bodies['original_receipt'], receipt_path=declared['receipt_path'],
                full_path=declared['full_path'], aliases=identities)
        except (ValueError, TypeError, UnicodeError) as exc:
            original = unknown('Captured history could not be classified: ' + type(exc).__name__)
    result = {'version': 1, 'family': family, 'scope': SCOPE,
              'declaration': deepcopy(declared), 'inputs': inputs, 'original_receipt': original}
    if family == 'native_shared':
        # The existing native gate validates original/sealed and effective/assembly
        # equality. These identities remain separate even for equal raw bytes.
        expected = gate.get('effective_receipt')
        effective = None
        if type(expected) is dict and type(expected.get('path')) is str:
            candidate, _ = _member(expected['path'], raw, aliases, metadata)
            if candidate is not None and all(candidate[k] == expected.get(k) for k in ('bytes', 'sha256')):
                effective = candidate
        result['inputs']['effective_receipt'] = effective
        result['effective_receipt'] = unknown(
            'Helper-reconstructed effective receipt history is not classified by this instrument; '
            'original-receipt classification does not describe effective counts.')
    return result


def attach(value, gate, *, raw, aliases, metadata):
    if not version(value):
        if REPORT_KEY in gate:
            raise ValueError('undeclared receipt-origin gate extension')
        return gate
    if REPORT_KEY in gate:
        raise ValueError('receipt-origin gate is already decorated')
    return {**gate, REPORT_KEY: report(value, gate, raw=raw, aliases=aliases, metadata=metadata)}


def attach_prepared(value, gates, prepared):
    """Fixed finalizer adapter; an unavailable capture stays unavailable."""
    snapshot = prepared['snapshot'] if prepared is not None else None
    raw = snapshot.raw if snapshot is not None else {}
    aliases = snapshot.aliases if snapshot is not None else {}
    metadata = snapshot.metadata if snapshot is not None else {}
    return {**gates, 'receipts': attach(value, gates['receipts'], raw=raw,
                                      aliases=aliases, metadata=metadata)}


def check_saved(value, gate, *, raw, aliases, metadata):
    """Called even on incomplete results before any shared-reader early return."""
    if not version(value):
        if REPORT_KEY in gate:
            raise ValueError('undeclared receipt-origin gate extension')
        return
    expected = report(value, gate, raw=raw, aliases=aliases, metadata=metadata)
    encoded = lambda obj: json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if encoded(gate.get(REPORT_KEY)) != encoded(expected):
        raise ValueError('saved receipt-origin report differs from its registered captured basis')
