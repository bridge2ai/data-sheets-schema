"""Recorded-schema relationship diagnostics; no artifact or provenance writes.

This labels current captured artifact bytes under a recovered schema. Missing
historical output hashes never become an assertion of observed run identity.
The legacy inspector and CLI default remain separate instruments.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import re
from typing import Any

import yaml

from .related_datasets import inspect

INSTRUMENT = 'related_dataset_diagnostics_v2'


@dataclass(frozen=True)
class Rules:
    root: str
    owner: str
    enum: str
    target_range: str
    values: frozenset[str]
    aliases: tuple[tuple[str, str], ...]


_RULES: dict[tuple[str, str], Rules] = {}


class _RecordedLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        if any(key.tag == 'tag:yaml.org,2002:merge' for key, _value in node.value):
            raise ValueError('YAML merge declarations are unsupported in recorded inputs')
        return super().construct_mapping(node, deep=deep)


def _mapping(raw: bytes, label: str):
    from .duplicate_keys import describe, find_duplicate_keys
    text = raw.decode('utf-8')
    duplicates = find_duplicate_keys(text, strict=True)
    if duplicates:
        raise ValueError(f'{label}: {describe(duplicates)}')
    value = yaml.load(text, Loader=_RecordedLoader)
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be a YAML mapping')
    return value


def _rules(raw: bytes, kind: str) -> Rules:
    from .schema_view import version_document, version_view
    root = 'Dataset' if kind == 'full' else 'CoreDataset'
    key = (hashlib.sha256(raw).hexdigest(), root)
    if key in _RULES:
        return _RULES[key]
    with version_view(Path('recorded-related-datasets.yaml'), version_document(raw)) as view:
        if root not in view.all_classes():
            raise ValueError(f'recorded schema lacks {root}')
        slots = {str(slot.name): slot for slot in view.class_induced_slots(root)}
        related = slots.get('related_datasets')
        if related is None:
            raise ValueError(f'recorded schema lacks {root}.related_datasets')
        if any(getattr(related, field, None) for field in ('any_of', 'all_of', 'exactly_one_of', 'none_of')):
            raise ValueError('unsupported related_datasets range expression')
        owner = str(related.range or '')
        if owner not in view.all_classes():
            raise ValueError('related_datasets does not range on a declared class')
        child = {str(slot.name): slot for slot in view.class_induced_slots(owner)}
        relation, target = child.get('relationship_type'), child.get('target_dataset')
        if relation is None or target is None:
            raise ValueError('related-dataset owner lacks relationship_type or target_dataset')
        if relation.multivalued or target.multivalued:
            raise ValueError('multivalued relationship or target fields are outside this diagnostic')
        if any(getattr(slot, field, None) for slot in (relation, target)
               for field in ('any_of', 'all_of', 'exactly_one_of', 'none_of')):
            raise ValueError('unsupported relationship or target range expression')
        enum = view.get_enum(str(relation.range or ''))
        if enum is None:
            raise ValueError('relationship_type does not range on a declared enum')
        if any(getattr(enum, field, None) for field in
               ('is_a', 'mixins', 'include', 'minus', 'inherits', 'reachable_from', 'matches', 'concepts', 'pv_formula')):
            raise ValueError('unsupported inherited or dynamic relationship enum')
        if str(target.range or '') != 'string':
            raise ValueError('target_dataset is not the supported string range')
        values = frozenset(map(str, enum.permissible_values))
        aliases: dict[str, str] = {}
        for value, definition in enum.permissible_values.items():
            for alias in definition.aliases or []:
                alias, canonical = str(alias), str(value)
                if alias in values and alias != canonical:
                    raise ValueError('relationship alias conflicts with a permissible value')
                if alias in aliases and aliases[alias] != canonical:
                    raise ValueError('relationship alias has multiple targets')
                aliases[alias] = canonical
        rules = Rules(root, owner, str(enum.name), str(target.range), values, tuple(sorted(aliases.items())))
    _RULES[key] = rules
    return rules


def _capture(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    return raw, {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def _association(provenance, provenance_path, path, raw, kind):
    from .provenance import resolve_record_input
    outputs = provenance.get('outputs')
    output = outputs.get(kind) if isinstance(outputs, dict) else None
    if not isinstance(output, dict):
        raise ValueError(f'provenance has no {kind} output association')
    named = output.get('path')
    if not isinstance(named, str) or not named.strip():
        raise ValueError('output association lacks an explicit path')
    resolved = resolve_record_input(Path(named), provenance_path)
    if resolved is None or resolved.resolve() != path.resolve():
        raise ValueError('declared output path does not resolve to the selected artifact')
    if 'bytes' in output:
        size = output['bytes']
        if type(size) is not int or size < 0 or size != len(raw):
            raise ValueError('declared output byte length differs from captured artifact')
    checked = []
    for algorithm in ('sha256', 'md5'):
        if algorithm in output:
            expected = output[algorithm]
            actual = getattr(hashlib, algorithm)(raw).hexdigest()
            if type(expected) is not str or expected != actual:
                raise ValueError(f'declared output {algorithm} differs from captured artifact')
            checked.append(algorithm)
    return {'declared_path': named, 'resolved_path': str(resolved.resolve()),
            'hashes_verified': checked, 'historical_output': 'hash_verified' if checked else 'unpinned',
            'meaning': ('current artifact bytes match every supplied historical output hash' if checked else
                        'current captured artifact under the recorded schema; historical output has no hash pin')}


def _schema_declarations(provenance, kind):
    """Do not let legacy recovery discard a malformed supplied declaration."""
    declared = provenance.get('schema')
    if not isinstance(declared, dict):
        raise ValueError('provenance has no schema mapping')
    path = declared.get(f'{kind}_path')
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f'recorded {kind} schema lacks an explicit path')
    hashes = {}
    for algorithm, length in (('sha256', 64), ('md5', 32)):
        key = f'{kind}_{algorithm}'
        if key in declared:
            value = declared[key]
            if type(value) is not str or re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is None:
                raise ValueError(f'malformed recorded schema {key}')
            hashes[algorithm] = value
    if not hashes:
        raise ValueError(f'recorded {kind} schema lacks a hash declaration')
    return hashes


def check_record(record_path: Path, provenance_path: Path, *, kind: str) -> dict[str, Any]:
    """Inspect one explicitly associated artifact; unavailable is not clean.

    Capture the artifact and provenance once. All rules come from one selected
    schema byte string, and today's schema is never a recorded-mode fallback.
    """
    if kind not in ('full', 'core'):
        raise ValueError('kind must be full or core')
    path, provenance_path = Path(record_path), Path(provenance_path)
    result = {'instrument': INSTRUMENT, 'requested_policy': 'recorded', 'kind': kind,
              'path': str(path), 'checked': False, 'defects': [], 'schema_basis': None,
              'selected_schema': None, 'output_association': None}
    try:
        raw, result['artifact'] = _capture(path)
        provenance_raw, result['provenance'] = _capture(provenance_path)
        record = _mapping(raw, 'artifact')
        provenance = _mapping(provenance_raw, 'provenance')
        result['output_association'] = _association(provenance, provenance_path, path, raw, kind)
        schema_hashes = _schema_declarations(provenance, kind)
        from .run_schema import TODAY, run_schema_bytes
        schema, basis = run_schema_bytes(provenance, kind=kind)
        result['schema_basis'] = basis
        if schema is None or basis.get('source') == TODAY:
            raise ValueError('recorded schema is unavailable: ' + str(basis.get('reason', 'no historical authority')))
        if any(getattr(hashlib, algorithm)(schema).hexdigest() != expected
               for algorithm, expected in schema_hashes.items()):
            raise ValueError('recovered schema differs from a supplied schema hash')
        rules = _rules(schema, kind)
        result['selected_schema'] = {'sha256': hashlib.sha256(schema).hexdigest(),
                                     'bytes': len(schema), 'root': rules.root, 'owner': rules.owner,
                                     'enum': rules.enum, 'target_range': rules.target_range}
        result['defects'] = [asdict(d) for d in inspect(record, vocabulary=(rules.values, dict(rules.aliases)))]
        result['checked'] = True
        result['reason'] = None
    except Exception as exc:  # a diagnostic failure must remain visible per artifact
        result['reason'] = f'{type(exc).__name__}: {exc}'
    return result
