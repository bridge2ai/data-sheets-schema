"""Read-only ownership admission for explicitly selected shared generations.

This does not replace receipt/accounting/hash validation or reserve files against
an unrelated concurrent writer. The caller rechecks inside its real output lock.
Selected batches conservatively disallow case-only or delimiter-nested project
names in one physical metadata container; ordinary distinct projects may share
that container. Legacy runs retain their existing restart/resume behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
import unicodedata

import yaml

from . import usage_ledger, snapshot_store

MAX_ENTRIES = 100_000
MAX_STATE_BYTES = 64 * 1024 * 1024
MAX_RUNS = 1024


@dataclass(frozen=True)
class _Footprint:
    mutable: tuple[tuple[str, Path], ...]
    evidence: tuple[Path, ...]
    namespaces: tuple[tuple[Path, str], ...]
    declarations: tuple[tuple[str, Path], ...]


@dataclass(frozen=True)
class _Point:
    owner: int | None
    role: str
    path: Path


def _selected(spec):
    return bool(getattr(spec, 'shared_generation_version', 0))


def _fold(value):
    return unicodedata.normalize('NFC', value).casefold()


def _exists(path):
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False


def _location(path):
    """Physical existing ancestor plus prospective suffix, with no writes."""
    try:
        resolved = Path(path).resolve()
        ancestor = resolved.parent
        suffix = [resolved.name]
        while not _exists(ancestor):
            suffix.insert(0, ancestor.name)
            ancestor = ancestor.parent
        info = ancestor.stat()
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError(f'output parent is not a directory: {ancestor}')
        return (info.st_dev, info.st_ino, tuple(map(_fold, suffix)))
    except RuntimeError as exc:
        raise ValueError(f'cannot resolve selected output: {path}') from exc


def _inode(path):
    if not _exists(path):
        return None
    try:
        info = path.stat()
    except FileNotFoundError as exc:
        raise ValueError(f'dangling selected output alias: {path}') from exc
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f'selected output is not a regular file: {path}')
    return info.st_dev, info.st_ino


def _spelling(path):
    # Resolve the container, not a final symlink (or a case-different leaf).
    # Only this exact intended artifact can repeat as harmless evidence.
    path = Path(path)
    return path.parent.resolve() / path.name


def _entries(directory, prefix, budget):
    """Only the existing project-owned leaves; do not follow directory links."""
    directory = Path(directory).resolve()
    if not _exists(directory):
        return ()
    if not directory.is_dir():
        raise ValueError(f'selected evidence container is not a directory: {directory}')
    found = []
    with os.scandir(directory) as entries:
        for entry in entries:
            budget[0] += 1
            if budget[0] > MAX_ENTRIES:
                raise ValueError('selected output inventory exceeds its entry limit')
            name = _fold(entry.name)
            if not (name.startswith(prefix) or name.startswith('.' + prefix)):
                continue
            path = Path(entry.path)
            # The active writers publish leaves, not project-named subtrees.
            # Unknown/nested directory state cannot establish safe ownership.
            _inode(path)
            found.append(path)
    return tuple(found)


def _describe(spec, budget):
    from . import api_runner as api
    project = spec.project
    if (type(project) is not str or not project or project in ('.', '..')
            or any(c in project for c in ('/', '\\', '\x00'))):
        raise ValueError('selected project must name one output component')
    primary = tuple(map(Path, (spec.full_path, spec.core_path,
                              spec.report_path, spec.provenance_path)))
    locks = tuple(lock for _, lock in usage_ledger.output_locks(primary))
    progress = api._progress_path(spec)
    index = snapshot_store.index_path(spec.metadata_dir, project)
    ledger = usage_ledger.ledger_path(spec)
    points = (*zip(('full', 'core', 'report', 'provenance'), primary),
              ('receipt', api._receipt_path(spec)), ('progress', progress),
              ('reasoning', api._reasoning_path(spec)),
              ('abandoned', usage_ledger.abandoned_journal_path(spec)),
              ('ledger', ledger), ('index', index),
              *((f'output-lock:{number}', lock) for number, lock in enumerate(locks)))
    prefix = _fold(project + '_')
    namespaces = tuple(dict.fromkeys((Path(p).resolve(), prefix)
                      for p in (spec.metadata_dir, index.parent)))
    evidence = tuple(dict.fromkeys(p for directory, name in namespaces
                                  for p in _entries(directory, name, budget)))
    lock_spellings = {_spelling(p) for p in locks}
    # Persistent lock files alone are harmless; do not classify them as spent.
    evidence = tuple(p for p in evidence if _spelling(p) not in lock_spellings)
    for _, point in points:
        _inode(point)
    declarations = [('ledger', ledger), ('progress', progress),
                    ('provenance', Path(spec.provenance_path)), ('index', index)]
    # Another identity-keyed live ledger is ownership evidence too. Previous
    # archives deliberately retain superseded generations and are not live.
    active_ledger = re.compile(re.escape(project) + r'_api_usage_[0-9a-f]{16}\.json', re.IGNORECASE)
    for path in evidence:
        if (path.parent == Path(spec.metadata_dir).resolve()
                and active_ledger.fullmatch(path.name)
                and _location(path) != _location(ledger)):
            declarations.append(('ledger', path))
    return _Footprint(points, evidence, namespaces, tuple(declarations))


def _check_points(points):
    """Keep writer roles distinct while allowing exact evidence enumeration."""
    locations, inodes = {}, {}
    for point in points:
        for seen, key in ((locations, _location(point.path)), (inodes, _inode(point.path))):
            if key is None:
                continue
            representatives = seen.setdefault(key, [])
            for other in representatives:
                evidence = point.role == 'evidence'
                other_evidence = other.role == 'evidence'
                if (point.owner == other.owner and
                        ((evidence and other_evidence) or
                         ((evidence or other_evidence) and
                          _spelling(point.path) == _spelling(other.path)))):
                    continue
                raise ValueError('selected outputs have conflicting output ownership: '
                                 f'{other.role} {other.path} and {point.role} {point.path}')
            if point.role != 'evidence':
                # Do not let later evidence conceal an existing writer role.
                representatives[:] = [point]
            elif (not any(p.role != 'evidence' for p in representatives)
                  and len(representatives) < 2
                  and all(_spelling(p.path) != _spelling(point.path) for p in representatives)):
                # Two different same-owner immutable leaves suffice: a later
                # writer cannot be the exact intended artifact of both leaves.
                representatives.append(point)


def _check_roles(footprints, control_paths=()):
    from .resources import resource_path
    from .schema_digest import INVENTORY_LEDGER

    def points():
        for owner, footprint in enumerate(footprints):
            for role, path in footprint.mutable:
                yield _Point(owner, role, path)
            for path in footprint.evidence:
                yield _Point(owner, 'evidence', path)
        # The inventory is one genuinely shared writer, never per-run state.
        yield _Point(None, 'shared-inventory', Path(resource_path(INVENTORY_LEDGER)))
        controls = set()
        for path in control_paths:
            path = Path(path)
            spelling = _spelling(path)
            if spelling not in controls:
                controls.add(spelling)
                yield _Point(None, 'batch-control', path)

    _check_points(points())


def require_disjoint_selected_outputs(specs, *, control_paths=()) -> None:
    """Reject selected artifact/control aliases before any locking or dispatch.

    The case-fold and delimiter-prefix rules are conservative compatibility
    limits, not claims that an exclusive numbered snapshot overwrites a leaf.
    The resource-resolved digest inventory is shared bookkeeping, but cannot
    alias run data or controls. Reusable read-only inputs are not run outputs.
    Batch callers supply their actual derived control paths at every check.
    """
    selected = []
    for spec in specs:
        if _selected(spec):
            selected.append(spec)
            if len(selected) > MAX_RUNS:
                raise ValueError('selected batch exceeds output ownership run limit')
    if not selected:
        return
    budget = [0]
    footprints = [_describe(spec, budget) for spec in selected]
    _check_roles(footprints, control_paths)
    namespaces = []
    for owner, footprint in enumerate(footprints):
        for directory, prefix in footprint.namespaces:
            physical = _location(directory / '__selected_namespace__')[:-1]
            # Preserve the suffix too for a not-yet-created container.
            physical += (_location(directory / '__selected_namespace__')[-1][:-1],)
            for previous, name, other_owner in namespaces:
                if (other_owner != owner and previous == physical
                        and (prefix.startswith(name) or name.startswith(prefix))):
                    raise ValueError('selected project evidence namespaces overlap '
                                     '(case-only or delimiter-nested names require distinct containers)')
            namespaces.append((physical, prefix, owner))


def _json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key in selected ownership declaration')
        result[key] = value
    return result


def _read_declaration(path, *, yaml_format=False):
    if _inode(path) is None:
        return None
    with path.open('rb') as stream:
        raw = stream.read(MAX_STATE_BYTES + 1)
    if len(raw) > MAX_STATE_BYTES:
        raise ValueError(f'selected ownership declaration exceeds byte limit: {path}')
    try:
        text = raw.decode('utf-8')
        if yaml_format:
            from .duplicate_keys import find_duplicate_keys
            if find_duplicate_keys(text, strict=True):
                raise ValueError('duplicate selected ownership key')
            value = yaml.safe_load(text)
        else:
            def invalid_constant(value):
                raise ValueError(f'invalid JSON constant: {value}')
            value = json.loads(text, object_pairs_hook=_json_pairs, parse_constant=invalid_constant)
    except (ValueError, yaml.YAMLError, RecursionError) as exc:
        raise ValueError(f'unreadable selected ownership declaration: {path}: {exc}') from exc
    if type(value) is not dict:
        raise ValueError(f'selected ownership declaration must be a mapping: {path}')
    return value


def require_selected_resume_owner(spec, *, resume: bool) -> None:
    """Check every supplied live owner; leave detailed recovery to its validators.

    Missing optional state is allowed. Existing project evidence without any
    usable owner is not a fresh run. Only stable run/generation fields are read:
    automatic run-date recovery and full input identity checks happen later.
    """
    if not _selected(spec):
        return
    if type(resume) is not bool:
        raise ValueError('selected resume must be a boolean')
    footprint = _describe(spec, [0])
    _check_roles((footprint,))
    expected = usage_ledger.run_identity(spec)
    generations = set()
    present = []
    for kind, path in footprint.declarations:
        if not _exists(path):
            continue
        present.append(path)
        value = _read_declaration(path, yaml_format=kind == 'provenance')
        identity = value.get('identity' if kind == 'ledger' else
                             'run' if kind == 'provenance' else 'run_identity')
        if (type(identity) is not dict or any(type(identity.get(key)) is not str
                or identity[key] != wanted for key, wanted in expected.items())):
            raise ValueError(f'selected output has foreign or unknown {kind} ownership: {path}')
        generation = identity.get('generation_id') if kind == 'provenance' else value.get('generation_id')
        if type(generation) is not str or not generation:
            raise ValueError(f'selected output has unknown {kind} generation: {path}')
        if kind in ('ledger', 'index') and (type(value.get('version')) is not int or value['version'] != 1):
            raise ValueError(f'selected output has invalid {kind} version: {path}')
        if kind == 'progress' and value.get('label') != spec.label:
            raise ValueError(f'selected progress label differs from owner: {path}')
        generations.add(generation)
    if len(generations) > 1:
        raise ValueError('selected live ownership declarations disagree on generation')
    # Primary records can live outside the metadata container in split layout.
    locks = {lock for _, lock in usage_ledger.output_locks(
        (spec.full_path, spec.core_path, spec.report_path, spec.provenance_path))}
    spent = bool(footprint.evidence or present or any(
        _exists(path) for _, path in footprint.mutable if path not in locks))
    if spent and not resume:
        raise ValueError('selected outputs are already spent; no-resume requires a fresh run')
    if spent and not generations:
        raise ValueError('selected output evidence has no usable live ownership')
