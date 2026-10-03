"""Content-bound offline routing prompt drafts (#4293), never a model executor.

A structural profile match remains an unreviewed caller declaration. It is not
publisher authentication, semantic equivalence, or a scientific routing verdict.
The opaque UTF-8 base is not checked for source context or provider suitability.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

from . import audit_omissions as bounds
from .schema_snapshot import capture_schema
from .schema_view import captured_view

FORMAT = 'source_heading_routing_request_v1'
RAI = 'http://mlcommons.org/croissant/RAI/'
MAX_INPUT = 8_000_000
MAX_SOURCE = 16_000_000  # the preserved public source member is 12,242,926 bytes
MAX_SOURCE_NODES = 300_000  # that member has 221,116 JSON values, depth 5
MAX_CAPTURE = 64_000_000
MAX_FILES = 256
MAX_ROWS = 512
SEPARATOR = b'\n\n--- OFFLINE SOURCE-HEADING ROUTING DRAFT v1 ---\n'
POLICY = '''This is draft routing guidance for independent review, not an execution instruction.
The supplied profile and crosswalk are draft and unreviewed. A structural match
only binds declared source bytes, entity, properties and full string values.
It does not authenticate a publisher, establish synonym equivalence or decide
correct placement. Consider every listed slot candidate using its own meaning;
retain the original direction and strength of each mapping. Source quotations,
entity scope and qualifications remain in the separate evidence payload.

Audit duty: release timing, embargo or availability alone does not establish
confidential or sensitive contents. Check what a passage affirms about content,
including legitimate mixed timing and sensitivity, negative claims and entity
scope. Preserve supported content and report a placement concern precisely;
do not recast it as an unsupported claim merely because its placement is wrong.
No lexical match or structural profile match establishes scientific acceptance.
'''
LIMITATIONS = [
    'Scientific crosswalk validity, source interpretation and slot placement are unverified.',
    'Caller-supplied profiles are declarations, not authenticated publisher assertions.',
    'No provider request, executor, live registration, model judgment or record modification.',
    'The opaque base prompt is not checked for source context, transport or model suitability.',
    'Full string spans use decoded Unicode code points, not raw JSON byte offsets.',
]
ROOT = Path(__file__).resolve().parents[2]
CODE_PATHS = (
    'src/data_sheets_schema/source_heading_routing.py',
    'src/semantic_exchange/generate_comprehensive_sssom.py',
    'src/data_sheets_schema/schema_snapshot.py',
    'src/data_sheets_schema/schema_view.py',
    'src/data_sheets_schema/audit_omissions.py',
    'src/data_sheets_schema/evidence_assertions.py',
    'src/data_sheets_schema/support_targets.py',
    'src/data_sheets_schema/duplicate_keys.py',
)
FILES = ('inputs.json', 'catalog.json', 'evidence.json', 'base.txt', 'supplement.txt', 'prompt.txt')


class _PrefixConflict(ValueError):
    pass


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def _exact(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f'invalid {label} fields')


def _text(value, label, limit=1024):
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValueError(f'invalid {label}')
    return value


def _digest(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('invalid SHA256')
    return value


def _raw(raw, label, limit=MAX_INPUT, empty=False):
    if type(raw) is not bytes or len(raw) > limit or (not raw and not empty):
        raise ValueError(f'{label} bytes outside declared bound')
    return raw


def _utf8(raw, label, empty=False):
    return _raw(raw, label, empty=empty).decode('utf-8', errors='strict')


def _authority_text(raw, label, empty=False):
    # Match the compiler's ordinary Path.read_text universal-newline semantics;
    # the original byte blob remains pinned separately, without normalization.
    return _utf8(raw, label, empty=empty).replace('\r\n', '\n').replace('\r', '\n')


def _parse(raw, label, limit=MAX_INPUT):
    return bounds._mapping(raw, label, json_only=True, limit=limit)


def _parse_source(raw):
    # A structured source graph is larger than a generated record. Preserve the
    # existing duplicate, nonfinite and nesting refusals with an explicit source
    # budget; do not change the released record/omission parsers' limits.
    from .evidence_assertions import load_json
    from .support_targets import _validate_json
    text = _raw(raw, 'source', MAX_SOURCE).decode('utf-8', errors='strict')
    try:
        if bounds.nesting_exceeds(text, bounds.yaml.SafeLoader, bounds.MAX_DEPTH):
            raise ValueError('source depth bound exceeded')
        value = load_json(text)
        _validate_json(value, max_nodes=MAX_SOURCE_NODES, max_depth=bounds.MAX_DEPTH)
        if type(value) is not dict:
            raise ValueError('structured source must be a JSON object')
        return value
    except (RecursionError, TypeError) as exc:
        raise ValueError('structured source exceeds safe JSON limits') from exc


def _blob(raw, limit=MAX_INPUT):
    _raw(raw, 'capture', limit, empty=True)
    return {'sha256': _sha(raw), 'bytes': len(raw), 'base64': base64.b64encode(raw).decode('ascii')}


def _unblob(blob, limit=MAX_INPUT):
    _exact(blob, {'sha256', 'bytes', 'base64'}, 'byte capture')
    if (type(blob['bytes']) is not int or not 0 <= blob['bytes'] <= limit
            or type(blob['base64']) is not str or len(blob['base64']) > 4 * ((limit + 2) // 3)):
        raise ValueError('capture size exceeds bound')
    try:
        raw = base64.b64decode(blob['base64'], validate=True)
    except (ValueError, UnicodeError) as exc:
        raise ValueError('invalid base64 capture') from exc
    if _blob(raw, limit) != blob:
        raise ValueError('captured byte identity differs')
    return raw


def _file(path, limit=MAX_INPUT):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'input is not a regular non-symlink file: {path}')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    return _raw(raw, 'file', limit, empty=True)


def _compiler():
    # This authority is a checkout tool, not an installed-package resolver.
    try:
        from semantic_exchange import generate_comprehensive_sssom as compiler
    except ImportError as exc:
        raise ValueError('routing preparation requires the checkout authority compiler on PYTHONPATH=src') from exc
    if Path(compiler.__file__).resolve() != ROOT / CODE_PATHS[1]:
        raise ValueError('authority compiler is not the selected checkout module')
    return compiler


def _code():
    return {name: _blob(_file(ROOT / name)) for name in CODE_PATHS}


def _capture_schema(path):
    total = 0

    def read(selected):
        nonlocal total
        raw = _file(selected)
        total += len(raw)
        if total > bounds.MAX_SCHEMA_BYTES:
            raise ValueError('schema closure exceeds bound')
        bounds._mapping(raw, 'schema')
        return raw

    snapshot = capture_schema(Path(path).absolute(), read_bytes=read, strict=True)
    if len(snapshot.sources) > MAX_FILES:
        raise ValueError('schema file count exceeds bound')
    return [{'name': str(n), 'path': str(p), 'content': _blob(raw)} for n, p, raw in snapshot.sources]


def _snapshot(rows):
    if type(rows) is not list or not 0 < len(rows) <= MAX_FILES:
        raise ValueError('invalid schema closure')
    frozen, sources, total = {}, [], 0
    for row in rows:
        _exact(row, {'name', 'path', 'content'}, 'schema capture')
        name = _text(row['name'], 'schema name')
        path = Path(_text(row['path'], 'schema path', 8192))
        if not path.is_absolute() or '..' in path.parts or path in frozen:
            raise ValueError('invalid or duplicate schema path')
        raw = _unblob(row['content'])
        total += len(raw)
        if total > bounds.MAX_SCHEMA_BYTES:
            raise ValueError('schema closure exceeds bound')
        bounds._mapping(raw, 'schema')
        frozen[path] = raw
        sources.append((name, path, raw))

    def read(selected):
        if selected not in frozen:
            raise ValueError('schema import outside captured closure')
        return frozen[selected]

    replay = capture_schema(sources[0][1], read_bytes=read, strict=True)
    if replay.sources != tuple(sources):
        raise ValueError('schema capture is not its complete exact declared import closure')
    return replay


def _tabular_unique(text, key):
    import csv
    reader = csv.DictReader(io.StringIO(''.join(s for s in text.splitlines(keepends=True) if not s.startswith('#'))), delimiter='\t')
    seen = set()
    for row in reader:
        if not row.get(key) or row[key] in seen or None in row:
            raise ValueError('duplicate or malformed authority table row')
        seen.add(row[key])


def _catalog(authority):
    _exact(authority, {'schema', 'ttl', 'recommendations', 'comprehensive'}, 'authority')
    compiler = _compiler()
    ttl = _authority_text(_unblob(authority['ttl']), 'TTL')
    recommendations = _authority_text(_unblob(authority['recommendations']), 'recommendations', empty=True)
    comprehensive = _authority_text(_unblob(authority['comprehensive']), 'comprehensive table')
    _tabular_unique(recommendations, 'attribute')
    _tabular_unique(comprehensive, 'subject_id')
    dates = re.findall(r'^# Date: (\d{4}-\d{2}-\d{2})$', comprehensive, flags=re.M)
    if len(dates) != 1:
        raise ValueError('comprehensive table must declare one exact mapping date')
    mapping_date = compiler.iso_date(dates[0])
    with captured_view(_snapshot(authority['schema'])) as view:
        generator = compiler.ComprehensiveSSSOMGenerator.from_captured(view, ttl, recommendations)
        # Same deterministic regeneration as the compiler's --check, no file writes.
        if generator.render_sssom(mapping_date) != comprehensive:
            raise ValueError('comprehensive authority drift: existing no-write regeneration differs')
        if view.get_class('Dataset') is None:
            raise ValueError('selected schema has no Dataset class')
        ancestry = set(map(str, view.class_ancestors('Dataset')))
        carried = set(map(str, view.class_slots('Dataset')))
        rows, excluded = [], []
        for name, resolution in sorted(generator.resolutions.items()):
            reason = None
            target = resolution.object
            if resolution.status != 'mapped' or resolution.source not in compiler.CURATED_SOURCES:
                reason = 'not a resolved curated mapping'
            elif not target.startswith('rai:') or generator.namespaces.get('rai') != RAI:
                reason = 'not the declared RAI vocabulary'
            elif re.fullmatch(r'rai:[A-Za-z][A-Za-z0-9_]*', target) is None:
                reason = 'unsupported RAI property spelling'
            elif name not in carried:
                reason = 'slot is not carried by Dataset'
            elif resolution.disagreement in {'open', 'changed', 'unlisted'}:
                reason = 'unresolved authority disagreement'
            elif set(resolution.owners) - ancestry:
                reason = 'same-name declarations have owners outside Dataset ancestry'
            slot = view.induced_slot(name, 'Dataset') if name in carried else None
            if reason is None and resolution.source == 'schema':
                visible = set()
                for key, predicate in compiler.SCHEMA_MAPPING_KINDS:
                    value = getattr(slot, key, None)
                    values = [value] if isinstance(value, str) else list(value or [])
                    visible.update((predicate, str(v)) for v in values)
                if (resolution.predicate, target) not in visible:
                    reason = 'compiler primary comes from a declaration invisible to Dataset'
            if reason is None and resolution.source == 'ttl' and resolution.origin != f'd4d:{name}':
                allowed = {f'd4d:{cls}_{name}' for cls in ancestry}
                if resolution.origin not in allowed:
                    reason = 'class-scoped TTL primary names another owner'
            if reason:
                excluded.append({'slot': name, 'reason': reason, 'mapping_source': resolution.source,
                                 'property': target, 'origin': resolution.origin})
                continue
            rows.append({'slot': name, 'owner': 'Dataset', 'declaring_owners': sorted(resolution.owners),
                'range': str(slot.range) if slot.range else None, 'multivalued': bool(slot.multivalued),
                'inlined': bool(view.is_inlined(slot)), 'property': target,
                'property_uri': RAI + target.split(':', 1)[1], 'predicate': resolution.predicate,
                'direction': 'Dataset slot to external property', 'mapping_source': resolution.source,
                'origin': resolution.origin, 'secondary_declarations': list(resolution.others),
                'disagreement': resolution.disagreement})
        return {'format': 'source_heading_catalog_v1', 'mapping_date': mapping_date,
                'root_class': 'Dataset', 'rows': rows, 'excluded': excluded,
                'authority_warnings': list(generator.warnings())}


def _tokens(pointer):
    from .support_targets import pointer_tokens
    if type(pointer) is not str or len(pointer) > 4096:
        raise ValueError('invalid JSON pointer')
    return pointer_tokens(pointer)


def _entity_path(value, pointer):
    """Keep every enclosing object on the exact pointer path, in source order."""
    path = [('', value)]
    current = ''
    for token in _tokens(pointer):
        if type(value) is dict:
            if token not in value:
                raise ValueError('pointer is absent')
            value = value[token]
        elif type(value) is list and re.fullmatch('0|[1-9][0-9]*', token):
            index = int(token)
            if index >= len(value):
                raise ValueError('pointer is absent')
            value = value[index]
        else:
            raise ValueError('pointer cannot traverse this value')
        current = _pointer(current, token)
        path.append((current, value))
    return path


def _pointer(base, key):
    return base + '/' + key.replace('~', '~0').replace('/', '~1')


def _profile(profile, crosswalk):
    _exact(profile, {'format', 'id', 'authority_status', 'prefixes', 'bindings'}, 'profile')
    _exact(crosswalk, {'format', 'authority_status', 'rows'}, 'crosswalk')
    if (profile['format'] != 'source_heading_profile_v1' or crosswalk['format'] != 'source_heading_crosswalk_v1'
            or profile['authority_status'] != 'draft/unreviewed' or crosswalk['authority_status'] != 'draft/unreviewed'):
        raise ValueError('only the explicitly draft profile/crosswalk versions are supported')
    _text(profile['id'], 'profile id')
    if type(profile['prefixes']) is not dict or len(profile['prefixes']) > 64:
        raise ValueError('invalid captured prefix declarations')
    for key, value in profile['prefixes'].items():
        if re.fullmatch('[A-Za-z][A-Za-z0-9_]*', key) is None:
            raise ValueError('invalid prefix name')
        _text(value, 'prefix URI')
    if any(type(v) is not list or len(v) > MAX_ROWS for v in (profile['bindings'], crosswalk['rows'])):
        raise ValueError('profile/crosswalk row bound exceeded')
    rows = {}
    for row in crosswalk['rows']:
        _exact(row, {'id', 'heading', 'profile_id', 'local_property', 'external_property', 'external_uri'}, 'crosswalk row')
        for key, value in row.items():
            _text(value, key)
        if row['id'] in rows:
            raise ValueError('duplicate crosswalk row id')
        if row['profile_id'] != profile['id']:
            raise ValueError('crosswalk names another profile')
        external = row['external_property']
        if external.startswith(RAI):
            expanded = external
        elif ':' in external:
            prefix, suffix = external.split(':', 1)
            if prefix not in profile['prefixes']:
                raise ValueError('external property lacks captured local prefix resolution')
            expanded = profile['prefixes'][prefix] + suffix
        else:
            raise ValueError('external property is not an explicit URI or CURIE')
        if expanded != row['external_uri'] or not expanded.startswith(RAI) or not expanded[len(RAI):]:
            raise ValueError('external property URI disagrees with declared RAI binding')
        rows[row['id']] = row
    seen = set()
    for binding in profile['bindings']:
        _exact(binding, {'row_id', 'source_sha256', 'entity_pointer', 'entity_id',
                        'local_value_sha256', 'external_value_sha256', 'evidence_id'}, 'profile binding')
        if binding['row_id'] not in rows:
            raise ValueError('binding names an undeclared crosswalk row')
        _tokens(binding['entity_pointer'])
        if binding['entity_id'] is not None:
            _text(binding['entity_id'], 'entity id', 8192)
        for key in ('source_sha256', 'local_value_sha256', 'external_value_sha256'):
            _digest(binding[key])
        _text(binding['evidence_id'], 'evidence id')
        stamp = _json(binding)
        if stamp in seen:
            raise ValueError('duplicate profile binding')
        seen.add(stamp)
    return rows


def _context_prefixes(path):
    """Resolve only simple captured local contexts, never partial JSON-LD.

    A reset, remote context or scoped/unsupported declaration anywhere along
    this entity's path prevents claiming an inherited compact-key namespace.
    Sibling objects are not on the path and cannot supply or override it.
    """
    prefixes, unsupported = {}, []
    for pointer, obj in path:
        if type(obj) is not dict or '@context' not in obj:
            continue
        context = obj['@context']
        items = context if type(context) is list else [context]
        for item in items:
            if type(item) is not dict:
                unsupported.append(f'reset, remote or unsupported context at {pointer or "/"}')
                continue  # capture identity, but do not fetch or ignore its effects
            for key, value in item.items():
                if key.startswith('@'):
                    # These two simple settings cannot rebind an absolute
                    # compact prefix. Import, propagation and other context
                    # operations are outside this bounded structural resolver.
                    if key not in ('@base', '@vocab') or type(value) is not str:
                        unsupported.append(f'unsupported context operation {key} at {pointer or "/"}')
                    continue
                if ':' in key:
                    # Exact compact-IRI term definitions can override prefix
                    # expansion; this subset must not ignore such a binding.
                    unsupported.append(f'explicit IRI term definition at {pointer or "/"}')
                if type(value) is dict and set(value) == {'@id', '@prefix'} and value['@prefix'] is True:
                    value = value['@id']
                if type(value) is not str:
                    unsupported.append(f'unsupported or scoped context declaration at {pointer or "/"}')
                    value = None
                elif value.startswith('@'):
                    unsupported.append(f'unsupported context keyword alias at {pointer or "/"}')
                if key in prefixes and prefixes[key] != value:
                    raise _PrefixConflict('conflicting captured local source prefix declarations')
                prefixes[key] = value
    return prefixes, unsupported


def _inventory(source_raw, profile, crosswalk, scope, catalog):
    source = _parse_source(source_raw)
    _exact(scope, {'source_sha256', 'entity_pointers'}, 'source scope')
    if _digest(scope['source_sha256']) != _sha(source_raw):
        raise ValueError('scope names different source bytes')
    pointers = scope['entity_pointers']
    if type(pointers) is not list or len(pointers) > MAX_ROWS or any(type(p) is not str for p in pointers) or len(set(pointers)) != len(pointers):
        raise ValueError('invalid or duplicate scoped entity pointers')
    for pointer in pointers:
        _tokens(pointer)
    rows = _profile(profile, crosswalk)
    records = []
    for binding in profile['bindings']:
        row = rows[binding['row_id']]
        record = {'row_id': row['id'], 'evidence_id': binding['evidence_id'],
                  'authority_status': 'draft/unreviewed', 'source_sha256': _sha(source_raw),
                  'entity_pointer': binding['entity_pointer'], 'heading': row['heading'],
                  'profile_id': profile['id'], 'property_uri': row['external_uri'],
                  'match_state': 'unmatched', 'reason': '', 'values': {}, 'candidates': []}
        if binding['source_sha256'] != _sha(source_raw):
            record['reason'] = 'source identity is not bound by this profile row'
        elif binding['entity_pointer'] not in pointers:
            record['reason'] = 'entity is outside caller-declared exact scope'
        else:
            try:
                path = _entity_path(source, binding['entity_pointer'])
                entity = path[-1][1]
                if type(entity) is not dict:
                    record.update(match_state='unsupported', reason='entity is not an object')
                elif binding['entity_id'] != entity.get('@id'):
                    record['reason'] = 'entity identifier differs from the binding'
                elif row['local_property'] not in entity or row['external_property'] not in entity:
                    record['reason'] = 'both properties must be in the same exact entity object'
                else:
                    local, external = entity[row['local_property']], entity[row['external_property']]
                    prefix = row['external_property'].split(':', 1)[0]
                    compact = not row['external_property'].startswith(RAI)
                    # An explicit URI is bound by its literal source key, not
                    # by an inferred JSON-LD expansion or profile declaration.
                    prefixes, unsupported = _context_prefixes(path) if compact else ({}, [])
                    if compact and (unsupported or prefix not in prefixes or prefixes[prefix] is None):
                        reason = 'compact property lacks a supported captured source-local prefix declaration'
                        if unsupported:
                            reason += ': ' + unsupported[0]
                        record.update(match_state='unsupported', reason=reason)
                    elif compact and prefixes[prefix] != profile['prefixes'].get(prefix):
                        record.update(match_state='ambiguous', reason='source and profile prefix declarations conflict')
                    elif any(type(value) is not str or not value.strip() for value in (local, external)):
                        record.update(match_state='unsupported', reason='only complete nonblank string property values are supported')
                    elif _sha(local.encode()) != binding['local_value_sha256'] or _sha(external.encode()) != binding['external_value_sha256']:
                        record['reason'] = 'full property value hashes differ from the binding'
                    else:
                        for label, key, value in (('local', row['local_property'], local), ('external', row['external_property'], external)):
                            record['values'][label] = {'pointer': _pointer(binding['entity_pointer'], key), 'text': value,
                                'decoded_codepoint_span': [0, len(value)], 'utf8_sha256': _sha(value.encode())}
                        record['candidates'] = [r for r in catalog['rows'] if r['property_uri'] == row['external_uri']]
                        record.update(match_state='matched', reason='exact declared source/entity/property/value recipe matched')
                        record['values_equal'] = local == external
                        record['source_prefix_basis'] = ('captured source-local prefix agrees with declared draft profile' if compact
                                                         else 'source property key is the explicit full URI')
                        if not record['candidates']:
                            record.update(match_state='unmatched', reason='no eligible resolved Dataset slot mapping')
            except _PrefixConflict as exc:
                record.update(match_state='ambiguous', reason=str(exc))
            except ValueError as exc:
                record.update(match_state='unmatched', reason=str(exc))
        records.append(record)
    # Competing declarations for the same source/entity/local property cannot
    # acquire authority by row order. Separate exact entries remain visible.
    groups = {}
    for index, binding in enumerate(profile['bindings']):
        row = rows[binding['row_id']]
        key = (binding['source_sha256'], binding['entity_pointer'], row['local_property'])
        groups.setdefault(key, []).append(index)
    for indices in groups.values():
        if len(indices) > 1:
            for index in indices:
                records[index].update(match_state='ambiguous', reason='multiple bindings compete for the same scoped local property', candidates=[])
    return {'format': 'source_heading_evidence_v1', 'authority_status': 'draft/unreviewed',
            'scope': scope, 'profile_id': profile['id'], 'records': records,
            'counts': {state: sum(r['match_state'] == state for r in records) for state in ('matched', 'unmatched', 'ambiguous', 'unsupported')},
            'unbound_crosswalk_rows': sorted(set(rows) - {b['row_id'] for b in profile['bindings']}),
            'scoped_entities_without_bindings': sorted(set(pointers) - {b['entity_pointer'] for b in profile['bindings'] if b['source_sha256'] == _sha(source_raw)})}


def render_supplement(catalog, evidence):
    """Only neutral instructions and authority-derived candidate triples enter text."""
    selected = {r['property_uri'] for r in evidence['records'] if r['match_state'] == 'matched'}
    lines = [POLICY.rstrip(), '', 'Declared mapping candidates (slot to external property direction):']
    for uri in sorted(selected):
        candidates = [r for r in catalog['rows'] if r['property_uri'] == uri]
        lines.append(uri + ': ' + '; '.join('Dataset.' + r['slot'] + ' [' + r['predicate'] + ']' for r in candidates))
    if not selected:
        lines.append('No supported route was established by the declared structural recipe.')
    lines.extend(['', 'Use the separate captured source/evidence payload for scope and quotations.',
                  'This draft does not establish that the base prompt contains that payload.'])
    return ('\n'.join(lines) + '\n').encode()


def append_prompt(base, supplement, *, enabled=True):
    _utf8(base, 'base prompt', empty=True)
    if type(enabled) is not bool:
        raise ValueError('enabled must be explicit bool')
    if not enabled:
        return base
    _utf8(supplement, 'supplement')
    return base + SEPARATOR + supplement


def _archive(inputs, source_raw):
    archive, member = inputs['archive'], inputs['archive_member']
    if archive is None and member is None:
        return None
    if archive is None or member is None:
        raise ValueError('archive and exact member must be supplied together')
    raw = _unblob(archive, MAX_CAPTURE)
    _text(member, 'archive member', 4096)
    with zipfile.ZipFile(io.BytesIO(raw)) as stream:
        matches = [r for r in stream.infolist() if r.filename == member]
        if len(matches) != 1 or matches[0].file_size > MAX_SOURCE or matches[0].is_dir():
            raise ValueError('archive member missing, duplicated or outside bound')
        if stream.read(matches[0]) != source_raw:
            raise ValueError('declared source bytes differ from original archive member')
    return {'archive_sha256': _sha(raw), 'member_name': member, 'member_sha256': _sha(source_raw)}


def _derive(inputs):
    _exact(inputs, {'format', 'base', 'source', 'profile', 'crosswalk', 'scope', 'authority', 'code', 'archive', 'archive_member'}, 'captured inputs')
    if inputs['format'] != FORMAT or inputs['code'] != _code():
        raise ValueError('capture protocol or current implementation/compiler bytes differ')
    if len(_json(inputs)) > MAX_CAPTURE:
        raise ValueError('total capture exceeds byte bound')
    base, source = _unblob(inputs['base']), _unblob(inputs['source'], MAX_SOURCE)
    _utf8(base, 'base prompt', empty=True)
    profile, crosswalk, scope = (_parse(_unblob(inputs[key]), key) for key in ('profile', 'crosswalk', 'scope'))
    archive = _archive(inputs, source)
    catalog = _catalog(inputs['authority'])
    evidence = _inventory(source, profile, crosswalk, scope, catalog)
    evidence['archive'] = archive
    supplement = render_supplement(catalog, evidence)
    return {'inputs.json': _json(inputs), 'catalog.json': _json(catalog), 'evidence.json': _json(evidence),
            'base.txt': base, 'supplement.txt': supplement, 'prompt.txt': append_prompt(base, supplement)}


def _manifest(files):
    payload = {'format': FORMAT, 'artifact_kind': 'prompt_text_draft', 'readiness': 'offline_draft_not_registered',
        'execution': 'not_supported', 'recipe': {'version': 1, 'separator_utf8': SEPARATOR.decode(), 'supplement_final_newline': True},
        'artifacts': {name: {'sha256': _sha(raw), 'bytes': len(raw)} for name, raw in sorted(files.items())},
        'additional_prompt_bytes': len(files['prompt.txt']) - len(files['base.txt']),
        'limitations': list(LIMITATIONS)}
    return {**payload, 'request_sha256': _sha(_json(payload))}


def prepare(*, base, source, profile, crosswalk, scope, schema_path, ttl, recommendations,
            comprehensive, archive=None, archive_member=None):
    """Capture and derive a reviewable draft, without modifying any input."""
    inputs = {'format': FORMAT, **{key: _blob(raw, MAX_SOURCE if key == 'source' else MAX_INPUT) for key, raw in dict(base=base, source=source,
              profile=profile, crosswalk=crosswalk, scope=scope).items()},
              'authority': {'schema': _capture_schema(schema_path), 'ttl': _blob(ttl),
                  'recommendations': _blob(recommendations), 'comprehensive': _blob(comprehensive)},
              'archive': _blob(archive, MAX_CAPTURE) if archive is not None else None,
              'archive_member': archive_member, 'code': _code()}
    files = _derive(inputs)
    files['manifest.json'] = _json(_manifest(files))
    return files


def check_files(files):
    """Reconstruct every emitted artifact from captured inputs, not trusted hashes."""
    if type(files) is not dict or set(files) != {*FILES, 'manifest.json'}:
        raise ValueError('unexpected or missing draft artifacts')
    for raw in files.values():
        _raw(raw, 'artifact', MAX_CAPTURE, empty=True)
    inputs = _parse(files['inputs.json'], 'captured inputs', MAX_CAPTURE)
    expected = _derive(inputs)
    expected['manifest.json'] = _json(_manifest(expected))
    if files != expected:
        raise ValueError('draft artifacts differ from independent reconstruction')
    return {'passed': True, 'request_sha256': _manifest({k: v for k, v in expected.items() if k != 'manifest.json'})['request_sha256'],
            'acceptance_scope': 'captured identity, declared structural match and deterministic rendering only',
            'limitations': list(LIMITATIONS)}


def write_new(output, files):
    check_files(files)
    output = Path(output)
    output.mkdir(exist_ok=False)
    # Exclusive publication. A failed partial directory is retained for review;
    # its absent final manifest cannot be mistaken for a completed draft.
    for name in (*FILES, 'manifest.json'):
        with (output / name).open('xb') as stream:
            stream.write(files[name])


def check_directory(path):
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError('draft is not a non-symlink directory')
    names = {p.name for p in path.iterdir()}
    if names != {*FILES, 'manifest.json'}:
        raise ValueError('unexpected or missing draft directory entries')
    files = {}
    for name in sorted(names):
        selected = path / name
        if selected.stat().st_nlink != 1:
            raise ValueError('draft artifact is not a single-link file')
        files[name] = _file(selected, MAX_CAPTURE)
    return check_files(files)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('prepare', help='write a new offline draft directory; no model call')
    for key in ('base', 'source', 'profile', 'crosswalk', 'scope', 'schema', 'ttl', 'recommendations', 'comprehensive', 'output'):
        create.add_argument('--' + key, required=True, type=Path)
    create.add_argument('--archive', type=Path)
    create.add_argument('--archive-member')
    verify = sub.add_parser('check', help='independently reconstruct a saved draft')
    verify.add_argument('directory', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            result = check_directory(args.directory)
        else:
            values = {key: _file(getattr(args, key), MAX_SOURCE if key == 'source' else MAX_INPUT)
                      for key in ('base', 'source', 'profile', 'crosswalk', 'scope', 'ttl', 'recommendations', 'comprehensive')}
            files = prepare(**values, schema_path=args.schema,
                            archive=_file(args.archive, MAX_CAPTURE) if args.archive else None,
                            archive_member=args.archive_member)
            write_new(args.output, files)
            result = {'output': str(args.output), **check_files(files)}
        print(_json(result).decode(), end='')
        return 0
    except (ValueError, OSError, TypeError, KeyError, zipfile.BadZipFile) as exc:
        print(f'offline routing draft refused: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
