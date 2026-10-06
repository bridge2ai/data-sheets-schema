"""Reviewed historical digest semantics, never executable historical plugins.

These six policies describe nine inspected renderer blobs. Reproducing text
under a dirty commit candidate does not attest the implementation a run used.
Generation and current-profile comparison continue to use schema_digest.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib.metadata import version
import os
from pathlib import Path
import re
import selectors
import subprocess
import time
from typing import Any


RENDERER_PATH = 'src/data_sheets_schema/schema_digest.py'
VOCABULARY_PATH = 'src/data_sheets_schema/b2ai_registry_vocabularies.yaml'
FULL_SCHEMA_PATH = 'src/data_sheets_schema/schema/data_sheets_schema_all.yaml'
RUNTIME_VERSION = '1.9.4'
VOCABULARY_SHA256 = 'e8be07eb6d5c99cdc44e10936cdfc9d4873fc812f341caf3427230d784dce914'
_UNIVERSAL = frozenset({'id', 'name', 'description', 'used_software'})
_GIT_SECONDS = 5.0
_GIT_BLOB_BYTES = 1024 * 1024


@dataclass(frozen=True)
class Policy:
    enum_limit: int = 60
    nested_enums: bool = True
    optional: bool = True
    ranges: bool = True
    vocabulary: bool = True
    canonical_path: bool = True
    depth: int = 1
    reference_labels: bool = False
    mirror_requires_truncation: bool = False


POLICIES = {
    'required_enum40': Policy(enum_limit=40, nested_enums=False, optional=False,
                              ranges=False, vocabulary=False, canonical_path=False),
    'nested_enum60': Policy(optional=False, ranges=False, vocabulary=False,
                           canonical_path=False),
    'optional_keys': Policy(ranges=False, vocabulary=False, canonical_path=False),
    'ranges_vocabulary': Policy(canonical_path=False),
    'canonical_paths': Policy(),
    'inline_depth2': Policy(depth=2, reference_labels=True, mirror_requires_truncation=True),
}

# The selector requires these exact recovered source bytes at the recorded
# commit. It never tries unrelated families until a digest happens to match.
SOURCE_FAMILIES = {
    'b900d33b1cefc5c6b021d3e2bee25fbde0595429102912a5a627ac43312fa2d3': 'required_enum40',
    '8f61dcc0cef032de6c1150da40c85036d95efcd78b9d41dbeff417f91ddb6662': 'required_enum40',
    '35c16f943677c091704cb7f802d1b49355df346c382e26b540427c9e293c3717': 'nested_enum60',
    'd23808086a0a4ca7c3e82cc5e67694a2cf87ae631ba0cca3ad939dd58882d21a': 'optional_keys',
    'bcfac7dfa5330f609d3d5120ab0efe165041dcbd49aa6db89e98451bb80c3673': 'ranges_vocabulary',
    'aa3bb9efaf05d71cc4fd1de79b300792de7f83c19722902ce7e7c78210d27364': 'canonical_paths',
    '4ca73ab4ebb623466750f51039a8477cbee8a27b1cdc46e89c54ee7a16d9288d': 'canonical_paths',
    '5b866504aa3c94fd66bcfa5a8aa8ef782ac574fdb84b1f5b07976e6ebe9d1d63': 'inline_depth2',
    '0fd427ddabae87147568af3c64afdd5dd372eda601d691b6d2db03be004311bf': 'inline_depth2',
}


def _vocabulary(raw: bytes | None, policy: Policy) -> dict[str, dict[str, str]]:
    if not policy.vocabulary:
        if raw is not None:
            raise ValueError('this historical renderer did not use a vocabulary')
        return {}
    if not isinstance(raw, bytes):
        raise ValueError('historical vocabulary bytes are required')
    from data_sheets_schema.schema_view import version_document
    tables = version_document(raw).get('vocabularies')
    if not isinstance(tables, dict):
        raise ValueError('historical vocabularies must be a mapping')
    for name, terms in tables.items():
        if (not isinstance(name, str) or not isinstance(terms, dict)
                or any(not isinstance(k, str) or not isinstance(v, str) for k, v in terms.items())):
            raise ValueError('historical vocabulary names, identifiers and labels must be strings')
    return tables


def _terms(names: list[str], vocabulary: dict[str, dict[str, str]]) -> str | None:
    parts = []
    for name in names:
        terms = vocabulary.get(name)
        if not terms:
            continue
        prefix = name + ':'
        items = ', '.join(f'{key[len(prefix):] if key.startswith(prefix) else key}={label}'
                          for key, label in terms.items())
        parts.append(f'{name} (use `{name}:<id>`) — {items}')
    return ('; '.join(parts) + '. If no term fits, omit the slot rather than approximate, and '
            'never restate the subject as prose here.') if parts else None


def _enum(view, range_name, limit: int) -> tuple[list[str], int]:
    enum = view.get_enum(range_name) if range_name else None
    values = list((enum.permissible_values or {}).keys()) if enum is not None else []
    return values[:limit], max(0, len(values) - limit)


def _inventory(view, policy: Policy) -> tuple[list[dict], list[dict]]:
    slots = []
    for slot in view.class_induced_slots('Dataset'):
        values, over = _enum(view, slot.range, policy.enum_limit)
        description = ' '.join(str(slot.description).split()) if slot.description else None
        if description and len(description) > 300:
            description = description[:299].rstrip() + '…'
        slots.append({'name': str(slot.name), 'range': str(slot.range) if slot.range else None,
                      'description': description, 'required': bool(slot.required),
                      'many': bool(slot.multivalued), 'values': values, 'over': over,
                      'values_from': [str(v) for v in (slot.values_from or [])]})
    slots.sort(key=lambda s: s['name'])
    nested, seen = [], set()
    frontier = [slot['range'] for slot in slots if slot['range']]
    for _ in range(policy.depth):
        next_frontier = []
        for name in frontier:
            if name in seen or view.get_class(name) is None:
                continue
            seen.add(name)
            item = {'name': name, 'required': [], 'optional': [], 'enums': {},
                    'enum_over': {}, 'ranges': {}, 'values_from': {}}
            for slot in view.class_induced_slots(name):
                key = str(slot.name)
                item['required' if slot.required else 'optional'].append(key)
                if policy.nested_enums:
                    enum = view.get_enum(slot.range) if slot.range else None
                    if enum is not None:
                        values, over = _enum(view, slot.range, policy.enum_limit)
                        item['enums'][key], item['enum_over'][key] = values, over
                if policy.ranges and slot.range:
                    shown = str(slot.range) + ('[]' if slot.multivalued else '')
                    if policy.reference_labels:
                        is_class = view.get_class(str(slot.range)) is not None
                        inlined = bool(is_class and view.is_inlined(slot))
                        if is_class and not inlined:
                            shown += ' (reference — a string, not an object)'
                        if inlined and key not in _UNIVERSAL:
                            next_frontier.append(str(slot.range))
                    item['ranges'][key] = shown
                if policy.vocabulary and slot.values_from:
                    item['values_from'][key] = [str(v) for v in slot.values_from]
            if item['required'] or item['optional']:
                item['required'].sort()
                item['optional'].sort()
                nested.append(item)
        frontier = next_frontier
    nested.sort(key=lambda n: n['name'])
    return slots, nested


def render_captured(raw_schema: bytes, logical_path: str, family: str, *,
                    vocabulary_bytes: bytes | None = None) -> str:
    """Render explicit data with reviewed semantics; never read historical code."""
    from data_sheets_schema.schema_view import version_document, version_view
    policy = POLICIES[family]
    if version('linkml-runtime') != RUNTIME_VERSION:
        raise ValueError('historical compatibility requires linkml-runtime ' + RUNTIME_VERSION)
    if not isinstance(raw_schema, bytes) or not isinstance(logical_path, str) or not logical_path.strip():
        raise ValueError('captured schema bytes and a nonblank logical path are required')
    document = version_document(raw_schema)
    if document.get('imports'):
        raise ValueError('historical compatibility requires an import-free captured schema')
    vocabulary = _vocabulary(vocabulary_bytes, policy)
    with version_view(Path(logical_path), document) as view:
        if view.get_class('Dataset') is None:
            raise ValueError('historical schema does not define Dataset')
        slots, nested = _inventory(view, policy)
    displayed = (FULL_SCHEMA_PATH if policy.canonical_path and
                 Path(logical_path).name == Path(FULL_SCHEMA_PATH).name else logical_path)
    lines = ['# Target class `Dataset` — slot inventory', '',
             f'Derived from `{displayed}`. Structure only: this states what '
             'shape a record takes, never what any dataset contains.', '',
             f'{len(slots)} slots. `[req]` must be populated; `[many]` takes a '
             'list. A slot with an enum range accepts only the listed values.', '']
    for slot in slots:
        flags = (' [req]' if slot['required'] else '') + (' [many]' if slot['many'] else '')
        shown_range = f" — *{slot['range']}*" if slot['range'] else ''
        lines.append(f"## `{slot['name']}`{shown_range}{flags}")
        if slot['description']:
            lines.append(slot['description'])
        if slot['values']:
            shown = ', '.join(f'`{v}`' for v in slot['values'])
            tail = f" (+{slot['over']} more)" if slot['over'] else ''
            lines.append(f'Permitted: {shown}{tail}')
        terms = _terms(slot['values_from'], vocabulary) if policy.vocabulary else None
        if terms:
            lines.append('Draw from: ' + terms)
        lines.append('')
    if nested:
        lines += ['# Object ranges — required keys', '',
                  'A slot whose range is one of these takes an object (or list of '
                  'objects). Any listed **required** key must be present on every such '
                  'object, or the record fails validation.', '']
        if policy.ranges:
            lines += ['On every object below: `id` is `uriorcurie`; `used_software` is `Software[]`. '
                      'A value of the wrong kind for its declared range is a defect even when it reads well.', '']
        top = {slot['name'] for slot in slots}
        for item in nested:
            required = ', '.join(f'`{v}`' for v in item['required']) or 'none'
            lines.append(f"- **{item['name']}** — required: {required}")
            optional = [key for key in item['optional'] if key not in _UNIVERSAL]
            if policy.optional and optional:
                own = [key for key in optional if key not in top]
                mirrors = (1 - len(own) / len(optional) >= .8 and
                           (not policy.mirror_requires_truncation or len(optional) > 24))
                if mirrors:
                    extra = ' plus ' + ', '.join(f'`{key}`' for key in own) if own else ''
                    lines.append('    - also accepts the same slots as the top-level listing above' + extra)
                else:
                    shown = ', '.join(f'`{key}`' for key in optional[:24])
                    tail = f' (+{len(optional) - 24} more)' if len(optional) > 24 else ''
                    lines.append(f'    - also accepts: {shown}{tail}')
            if policy.ranges:
                typed = {key: value for key, value in sorted(item['ranges'].items())
                         if value not in ('string', 'string[]') and key not in item['enums']
                         and key not in _UNIVERSAL}
                if typed:
                    shown = ', '.join(f'`{key}`: {value}' for key, value in list(typed.items())[:24])
                    tail = f' (+{len(typed) - 24} more)' if len(typed) > 24 else ''
                    lines.append(f'    - ranges: {shown}{tail}')
            for key, values in sorted(item['enums'].items()):
                shown = ', '.join(f'`{v}`' for v in values)
                extra = item['enum_over'][key]
                tail = f' (+{extra} more)' if extra else ''
                lines.append(f'    - `{key}` accepts only: {shown}{tail}')
            for key, names in sorted(item['values_from'].items()):
                terms = _terms(names, vocabulary)
                if terms:
                    lines.append(f'    - `{key}` draws from {terms}')
        lines.append('')
    return '\n'.join(lines)


def _git_output(arguments: list[str], root: Path, limit: int) -> bytes:
    """Read bounded local Git output without replacement, fetching or redirection."""
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('GIT_')}
    environment.update(GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1',
                       GIT_ALLOW_PROTOCOL='', GIT_TERMINAL_PROMPT='0',
                       GIT_OPTIONAL_LOCKS='0', GIT_CONFIG_NOSYSTEM='1',
                       GIT_CONFIG_GLOBAL=os.devnull)
    process = subprocess.Popen(['git', *arguments], cwd=root, env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               stdin=subprocess.DEVNULL, bufsize=0)
    deadline = time.monotonic() + _GIT_SECONDS
    output = bytearray()
    selector = selectors.DefaultSelector()
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise ValueError('historical Git read exceeded its time limit')
            chunk = os.read(process.stdout.fileno(), min(65536, limit + 1 - len(output)))
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > limit:
                raise ValueError('historical Git output exceeded its byte limit')
        try:
            code = process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired as exc:
            raise ValueError('historical Git read exceeded its time limit') from exc
        if code:
            raise ValueError('historical Git object unavailable')
        return bytes(output)
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=1)
        finally:
            process.stdout.close()


def _git_blob(commit: str, path: str, root: Path) -> tuple[bytes, str]:
    """Resolve fixed-path data at the exact commit; no code is imported."""
    identity = _git_output(['rev-parse', '--verify', f'{commit}:{path}'], root, 64)
    oid = identity.decode('ascii').strip()
    if re.fullmatch(r'[0-9a-f]{40}', oid) is None:
        raise ValueError('historical Git blob identity is malformed')
    raw = _git_output(['cat-file', 'blob', oid], root, _GIT_BLOB_BYTES)
    if hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != oid:
        raise ValueError('historical Git blob bytes do not match their object identity')
    return raw, oid


def reconstruct(record: dict[str, Any], raw_schema: bytes, logical_path: str, *,
                git_root: Path | None = None) -> dict[str, Any]:
    """Separate text agreement from unrecorded consumed implementation/profile.

    The caller supplies freshly recovered, hash-verified schema bytes. This
    function verifies their declared authority again before considering any
    renderer candidate. git_root is explicit read-only audit input; ordinary
    readers use their installed checkout, never a network or path fallback.
    """
    from copy import deepcopy
    snapshot = deepcopy(record) if isinstance(record, dict) else {}
    schema = snapshot.get('schema') if isinstance(snapshot.get('schema'), dict) else {}
    repo = snapshot.get('repo') if isinstance(snapshot.get('repo'), dict) else {}
    software = snapshot.get('software') if isinstance(snapshot.get('software'), dict) else {}
    result: dict[str, Any] = {'status': 'unavailable', 'reason': None, 'candidate': None,
                             'recorded_digest_md5': schema.get('digest_md5'),
                             'consumed_implementation_identity': 'unrecorded',
                             'historical_profile_identity': ('declared_unverified'
                                 if isinstance(schema.get('profile'), str) else 'unrecorded'),
                             'recorded_profile': schema.get('profile'),
                             'recorded_repo_dirty': repo.get('dirty'),
                             'text_sha256': None, 'candidate_digest_md5': None}
    digest = schema.get('digest_md5')
    if not digest:
        result.update(status='no_recorded_digest', reason='the record names no digest to reconstruct')
        return result
    try:
        if not isinstance(digest, str) or re.fullmatch(r'[0-9a-f]{32}', digest) is None:
            raise ValueError('recorded digest is not a lowercase MD5')
        if schema.get('full_path') != logical_path or not isinstance(raw_schema, bytes):
            raise ValueError('captured historical schema path/bytes do not match the declaration')
        hashes = {name: schema[name] for name in ('full_sha256', 'full_md5') if name in schema}
        if not hashes:
            raise ValueError('historical schema authority has no recorded hash')
        for name, value in hashes.items():
            length = 64 if name == 'full_sha256' else 32
            if not isinstance(value, str) or re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is None:
                raise ValueError('historical schema authority contains a malformed hash')
            if getattr(hashlib, name.removeprefix('full_'))(raw_schema).hexdigest() != value:
                raise ValueError('historical schema bytes do not match every recorded hash')
        if software.get('linkml_runtime') != RUNTIME_VERSION:
            raise ValueError('recorded LinkML runtime is unavailable or unsupported')
        commit = repo.get('commit')
        if not isinstance(commit, str) or re.fullmatch(r'[0-9a-f]{40}', commit) is None:
            raise ValueError('recorded repository commit is unavailable or malformed')
        root = Path(git_root) if git_root is not None else Path(__file__).resolve().parents[2]
        source, source_blob = _git_blob(commit, RENDERER_PATH, root)
        source_sha = hashlib.sha256(source).hexdigest()
        family = SOURCE_FAMILIES.get(source_sha)
        if family is None:
            raise ValueError('recorded commit renderer is not a reviewed historical family')
        candidate = {'commit': commit, 'source_path': RENDERER_PATH, 'source_blob': source_blob,
                     'source_sha256': source_sha, 'family': family,
                     'basis': 'renderer candidate at the recorded commit; consumed bytes were not pinned',
                     'vocabulary': {'source': 'historical renderer did not use a vocabulary'},
                     'linkml_runtime': version('linkml-runtime')}
        result['candidate'] = candidate
        vocabulary = None
        if POLICIES[family].vocabulary:
            vocabulary, vocab_blob = _git_blob(commit, VOCABULARY_PATH, root)
            vocab_sha = hashlib.sha256(vocabulary).hexdigest()
            if vocab_sha != VOCABULARY_SHA256:
                raise ValueError('recorded commit vocabulary is not the reviewed historical pin')
            candidate['vocabulary'] = {'source': 'candidate vocabulary at recorded commit',
                                       'path': VOCABULARY_PATH, 'blob': vocab_blob, 'sha256': vocab_sha}
        text = render_captured(raw_schema, logical_path, family, vocabulary_bytes=vocabulary)
        result.update(text_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
                      candidate_digest_md5=hashlib.md5(text.encode('utf-8')).hexdigest(),
                      schema_sha256=hashlib.sha256(raw_schema).hexdigest())
        reproduced = result['candidate_digest_md5'] == digest
        result.update(status='reproduced' if reproduced else 'not_reproduced',
                      reason=('candidate text reproduces the recorded digest; consumed implementation '
                              'and profile are not attested by this reconstruction' if reproduced else
                              'the recorded commit candidate does not reproduce the recorded digest'))
    except Exception as exc:
        result['reason'] = f'{type(exc).__name__}: {exc}'
    return result
