"""Opt-in receipt history from sealed native evidence, without gate authority.

Registrations supply identities; this module never reads or resolves a path.
Saved readers independently reconstruct the informational report from the same
bytes they verified against the final capture, including for failed attempts.
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
}


def _path(value):
    if (type(value) is not str or not value.startswith('/') or value.startswith('//')
            or '\x00' in value or str(PurePosixPath(value)) != value
            or '..' in PurePosixPath(value).parts):
        raise ValueError('receipt-origin identity requires a canonical recorded absolute path')
    return value


def declaration(attempt_directory, artifact_paths):
    """Derive the only supported identities from an already verified selection."""
    return {
        'version': 1,
        'transcript_path': _path(str(PurePosixPath(_path(attempt_directory)) / 'transcript.jsonl')),
        'receipt_path': _path(artifact_paths['receipt']),
        'full_path': _path(artifact_paths['full']),
    }


def version(value):
    """An omitted declaration is legacy version 0; only explicit v1 is valid."""
    if type(value) is not dict:
        raise ValueError('receipt-origin reporting requires a registration mapping')
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
    if type(target) is not str:
        return None, None
    try:
        _path(target)
    except ValueError:
        return None, None
    if aliases.get(target, target) != target or (path in metadata and path != target):
        return None, None
    meta, body = metadata.get(target), raw.get(target)
    if (type(meta) is not dict or meta.get('exists') is not True
            or meta.get('regular') is not True or type(body) is not bytes
            or ('size' in meta and (type(meta['size']) is not int or meta['size'] != len(body)))):
        return None, None
    return {
        'path': path, 'captured_path': target, 'bytes': len(body),
        'sha256': hashlib.sha256(body).hexdigest(),
    }, body


def required_paths(value, gate, aliases):
    """Select captured physical bodies needed by this version, without I/O."""
    if not version(value):
        return ()
    declared = value[KEY]
    paths = (declared[key] for key in ('transcript_path', 'receipt_path', 'full_path'))
    return tuple(sorted({target for path in paths
                         if type(target := aliases.get(path, path)) is str}))


def report(value, gate, *, raw, aliases, metadata):
    """Classify original receipt history; the supplied gate has no authority here."""
    if version(value) != 1:
        raise ValueError('receipt-origin report was not explicitly registered')
    from data_sheets_schema import receipt_origin as instrument
    declared = value[KEY]
    inputs, bodies = {}, {}
    for name, key in (('transcript', 'transcript_path'), ('full', 'full_path'),
                      ('original_receipt', 'receipt_path')):
        inputs[name], bodies[name] = _member(declared[key], raw, aliases, metadata)

    def unknown(reason):
        return {'instrument': instrument.INSTRUMENT, 'status': 'unknown',
                'reasons': [reason], 'transcripts': []}

    if any(member is None for member in inputs.values()):
        original = unknown('Selected transcript, full record or original receipt is unavailable or inconsistent in the captured basis.')
    else:
        try:
            # Include recorded physical identities as well as aliases. Do not
            # overwrite conflicting pairs: the classifier must see conflicts.
            identities = tuple(sorted(set(
                [(path, path) for path in metadata] + list(aliases.items()))))
            original = instrument.origin_captured(
                ((declared['transcript_path'], bodies['transcript']),),
                receipt_raw=bodies['original_receipt'],
                receipt_path=declared['receipt_path'], full_path=declared['full_path'],
                aliases=identities)
        except (ValueError, TypeError, UnicodeError) as exc:
            original = unknown('Captured history could not be classified: ' + type(exc).__name__)
    return {
        'version': 1, 'family': FAMILIES[value['kind']], 'scope': SCOPE,
        'declaration': deepcopy(declared), 'inputs': inputs,
        'original_receipt': original,
    }


def attach(value, gate, *, raw, aliases, metadata):
    if not version(value):
        if REPORT_KEY in gate:
            raise ValueError('undeclared receipt-origin gate extension')
        return gate
    if REPORT_KEY in gate:
        raise ValueError('receipt-origin gate is already decorated')
    return {**deepcopy(gate), REPORT_KEY: report(
        value, gate, raw=raw, aliases=aliases, metadata=metadata)}


def attach_prepared(value, gates, prepared):
    if not version(value):
        return gates
    snapshot = prepared['snapshot'] if prepared is not None else None
    # Failed acquisition can retain a partially populated snapshot. Its bytes
    # are not a fixed evidence basis until sealing completed with exact True.
    if snapshot is not None and getattr(snapshot, 'sealed', None) is not True:
        snapshot = None
    return {**gates, 'receipts': attach(
        value, gates['receipts'], raw=snapshot.raw if snapshot is not None else {},
        aliases=snapshot.aliases if snapshot is not None else {},
        metadata=snapshot.metadata if snapshot is not None else {})}


def check_saved(value, gate, *, raw, aliases, metadata):
    if not version(value):
        if REPORT_KEY in gate:
            raise ValueError('undeclared receipt-origin gate extension')
        return
    expected = report(value, gate, raw=raw, aliases=aliases, metadata=metadata)
    encoded = lambda obj: json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if encoded(gate.get(REPORT_KEY)) != encoded(expected):
        raise ValueError('saved receipt-origin report differs from its registered captured basis')
