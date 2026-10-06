"""Read-only profile identity from a record's hash-matched schema (#4061).

Historical schema bytes are necessary but not sufficient: today's renderer and
profile vocabulary may not reproduce the recorded digest. Unmatched candidates
therefore establish unknown identity, never agreement or a replacement digest.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from importlib.metadata import version
from pathlib import Path
import re
from typing import Any


def _choose(context: dict[str, Any], candidates: dict[str, str], *, historical: bool) -> None:
    recorded, effective = context['recorded_digest_md5'], context['effective_profile']
    context['candidate_digests'] = candidates
    if candidates.get(effective) == recorded:
        context.update(status='match', reason='the stated profile reproduces the recorded digest')
        return
    matches = [name for name, digest in candidates.items() if digest == recorded]
    if matches:
        stated = context['stated_profile']
        basis = f" (read as {effective!r})" if stated is None else ''
        scope = 'digest rendered from the recorded schema' if historical else 'current digest'
        context.update(status='mismatch', matched_profiles=matches,
                       reason='another profile reproduces the recorded digest',
                       finding=(f"schema.profile is {stated!r}{basis} but schema.digest_md5 "
                                f"{recorded[:12]}… is the {matches[0]} profile's {scope}"))
        return
    context['reason'] = ('the recorded digest is not reproduced by the current renderer and '
                         'profile vocabularies over the recorded schema' if historical else
                         'the recorded digest matches neither current profile candidate')


def _current(context: dict[str, Any]) -> dict[str, Any]:
    """Preserve the historical authority-free comparison and its failure rule."""
    from data_sheets_schema.profiles import MissingVocabulary, PROFILES
    context['comparison_basis'] = 'current schema comparison; no recorded full-schema authority'
    try:
        from data_sheets_schema import schema_digest
        current = {name: schema_digest.fingerprint(schema_digest.digest_text('Dataset', profile=profile))
                   for name, profile in PROFILES.items()}
    except Exception as exc:  # no available instrument to compare
        context['reason'] = f'current profile comparison unavailable: {type(exc).__name__}: {exc}'
        if isinstance(exc, MissingVocabulary):
            context['finding'] = f"the record's profile cannot be checked here: {exc}"
        return context
    _choose(context, current, historical=False)
    return context


def _vocabulary(profile) -> tuple[dict, dict]:
    """Capture a profile's selected vocabulary once, without ambient selection."""
    from data_sheets_schema.schema_view import version_document
    pin = profile.pin_path
    if pin is None:
        return {}, {'path': None, 'sha256': None, 'bytes': 0, 'source': 'profile declares no vocabulary'}
    raw = pin.read_bytes()
    document = version_document(raw)
    vocabulary = document.get('vocabularies')
    if not isinstance(vocabulary, dict):
        raise ValueError('profile vocabulary must be a mapping')
    for name, terms in vocabulary.items():
        if not isinstance(name, str) or not isinstance(terms, dict):
            raise ValueError('each named profile vocabulary must be a mapping')
        if any(not isinstance(key, str) or not isinstance(label, str) for key, label in terms.items()):
            raise ValueError('profile vocabulary identifiers and labels must be strings')
    return vocabulary, {'path': str(pin), 'sha256': hashlib.sha256(raw).hexdigest(),
                        'bytes': len(raw), 'source': 'current profile vocabulary'}


def capture(record: dict[str, Any]) -> dict[str, Any]:
    """Describe an exact-match comparison without changing recorded evidence.

    A supplied but unusable full-schema path or hash never enables today's
    fallback. Context values are detached from the caller's record. Neither
    this function nor its callers treat an unknown result as scientific proof.
    """
    from data_sheets_schema import profiles

    schema = record.get('schema') if isinstance(record, dict) else None
    schema = deepcopy(schema) if isinstance(schema, dict) else {}
    stated, recorded = schema.get('profile'), schema.get('digest_md5')
    effective = profiles.for_record({'schema': schema}).name if stated is None else stated
    context: dict[str, Any] = {
        'status': 'unknown', 'recorded_digest_md5': recorded if isinstance(recorded, str) else None,
        'stated_profile': stated if isinstance(stated, str) else None,
        'effective_profile': effective if isinstance(effective, str) else None,
        'profile_basis': 'historical study fallback' if stated is None else 'recorded schema.profile',
        'comparison_basis': None, 'schema_basis': None, 'candidate_digests': {},
        'vocabularies': {}, 'renderer': None, 'finding': None, 'reason': None,
    }
    if not recorded:
        context.update(status='no_recorded_digest', reason='the record names no digest to compare')
        return context
    if not isinstance(effective, str) or not isinstance(recorded, str):
        context['reason'] = 'malformed profile or digest; handled by record structural validation'
        return context

    fields = ('full_path', 'full_sha256', 'full_md5')
    declared = [name for name in fields if name in schema]
    if not declared:
        return _current(context)
    context['comparison_basis'] = 'recorded full-schema bytes with current renderer and profile vocabularies'
    context['declared_authority_fields'] = declared
    path = schema.get('full_path')
    hashes = {name: schema[name] for name in fields[1:] if name in schema}
    if not isinstance(path, str) or not path.strip() or not hashes:
        context['reason'] = 'recorded full-schema authority requires a nonblank path and at least one hash'
        return context
    for name, value in hashes.items():
        length = 64 if name == 'full_sha256' else 32
        if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{' + str(length) + '}', value) is None:
            context['reason'] = f'recorded {name} is not a valid lowercase hexadecimal hash'
            return context
    registered_profiles = tuple(profiles.PROFILES.items())
    if effective not in dict(registered_profiles):
        context['reason'] = 'the recorded profile is not available in this renderer'
        return context
    try:
        from data_sheets_schema import run_schema, schema_digest
        from data_sheets_schema.schema_view import version_document, version_view
        raw, basis = run_schema.run_schema_bytes({'schema': schema})
        context['schema_basis'] = deepcopy(basis)
        if raw is None:
            context['reason'] = 'recorded full-schema bytes unavailable: ' + str(basis.get('reason', 'not recovered'))
            return context
        if type(raw) is not bytes or any(getattr(hashlib, name.removeprefix('full_'))(raw).hexdigest() != value
                                         for name, value in hashes.items()):
            context['reason'] = 'recovered full-schema bytes do not match every recorded hash'
            return context
        context['schema_sha256'] = hashlib.sha256(raw).hexdigest()
        renderer_raw = Path(schema_digest.__file__).read_bytes()
        context['renderer'] = {'module': 'data_sheets_schema.schema_digest',
                               'source_sha256': hashlib.sha256(renderer_raw).hexdigest(),
                               'linkml_runtime_version': version('linkml-runtime'),
                               'basis': 'current installed renderer, not a recovered historical renderer'}
        document = version_document(raw)
        with version_view(Path(path), document) as view:
            if view.get_class('Dataset') is None:
                raise ValueError('recorded schema does not define Dataset')
            inventory = schema_digest._build_from_view('Dataset', Path(path), view)
        candidates = {}
        for name, profile in registered_profiles:
            try:
                vocabulary, identity = _vocabulary(profile)
            except Exception as exc:
                context['vocabularies'][name] = {
                    'source': 'unavailable current profile vocabulary',
                    'reason': f'{type(exc).__name__}: {exc}',
                }
                raise
            context['vocabularies'][name] = identity
            text = schema_digest.render(inventory, vocabulary=vocabulary)
            candidates[name] = schema_digest.fingerprint(text)
        _choose(context, candidates, historical=True)
    except Exception as exc:  # malformed or unavailable history is a disclosed unknown
        context['reason'] = f'historical profile identity unavailable: {type(exc).__name__}: {exc}'
    return context
