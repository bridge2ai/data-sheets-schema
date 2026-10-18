"""Metadata-only isolation of selected generation authority from its writers.

The roots cover dynamic evidence names; fixed points cover writers outside
those roots. No payload is read here, and no successful scan is cached.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat

MAX_ENTRIES = 100_000
MAX_DEPTH = 64


@dataclass(frozen=True)
class Footprint:
    roots: tuple[Path, ...]
    points: tuple[Path, ...]


def for_run(spec) -> Footprint:
    """Use the same output/lock/resource derivations as the actual writers."""
    from .usage_ledger import output_locks
    from .schema_digest import INVENTORY_LEDGER
    from .resources import resource_path
    outputs = (spec.full_path, spec.core_path, spec.report_path, spec.provenance_path)
    return Footprint(
        (Path(spec.metadata_dir), spec.full_path.parent, spec.core_path.parent),
        (*outputs, *(lock for _output, lock in output_locks(outputs)),
         resource_path(INVENTORY_LEDGER)))


def require_separate(authorities, footprints, *, extra_points=()) -> None:
    """Refuse containment/inode aliases before any selected writer starts.

    Top-level roots retain ordinary resolved-path semantics. Nested directory
    symlinks are unsupported: following them would inspect unrelated trees.
    File symlinks are checked as points. Errors and scan bounds fail closed.
    """
    authorities = tuple(dict.fromkeys(Path(path) for path in authorities))
    resolved_authorities = set()
    authority_inodes = set()
    for path in authorities:
        resolved = path.resolve(strict=True)
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f'shared authority is not a regular file: {path}')
        resolved_authorities.add(resolved)
        authority_inodes.add((info.st_dev, info.st_ino))

    footprints = tuple(footprints)
    roots = sorted({path.resolve() for footprint in footprints for path in footprint.roots},
                   key=lambda path: (len(path.parts), str(path)))
    # An overlapping declared root is not a cycle, and needs no second walk.
    selected_roots = []
    for root in roots:
        if not any(root == parent or parent in root.parents for parent in selected_roots):
            selected_roots.append(root)
    for path in resolved_authorities:
        if any(path == root or root in path.parents for root in selected_roots):
            raise ValueError(f'shared authority must be outside run-owned output directories: {path}')

    def check_point(path, info=None):
        path = Path(path)
        if info is None:
            try:
                info = path.lstat()
            except FileNotFoundError:
                return
        if stat.S_ISLNK(info.st_mode):
            # Broken or inaccessible links are not silently treated as fresh.
            info = path.stat()
            resolved = path.resolve(strict=True)
        else:
            resolved = path.absolute()
        if (resolved in resolved_authorities or
                (info.st_dev, info.st_ino) in authority_inodes):
            raise ValueError(f'shared authority aliases a run output/write destination: {path}')
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f'unsupported shared write destination: {path}')

    points = {Path(path) for path in extra_points}
    points.update(path for footprint in footprints for path in footprint.points)
    for path in sorted(points):
        check_point(path)

    visited, active = set(), set()
    entries = 0

    def walk(directory, depth):
        nonlocal entries
        if depth > MAX_DEPTH:
            raise ValueError('shared write footprint exceeds directory depth bound')
        try:
            info = directory.lstat()
        except FileNotFoundError:
            if depth == 0:
                return
            raise
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError(f'unsupported shared output directory: {directory}')
        inode = (info.st_dev, info.st_ino)
        if inode in active:
            raise ValueError(f'cycle in shared write footprint: {directory}')
        if inode in visited:
            return
        active.add(inode)
        visited.add(inode)
        try:
            with os.scandir(directory) as children:
                for child in children:
                    entries += 1
                    if entries > MAX_ENTRIES:
                        raise ValueError('shared write footprint exceeds entry bound')
                    path = Path(child.path)
                    child_info = child.stat(follow_symlinks=False)
                    if stat.S_ISDIR(child_info.st_mode):
                        walk(path, depth + 1)
                    elif stat.S_ISLNK(child_info.st_mode):
                        target = path.stat()
                        if stat.S_ISDIR(target.st_mode):
                            raise ValueError(f'nested directory symlink in shared write footprint: {path}')
                        check_point(path, child_info)
                    else:
                        check_point(path, child_info)
        finally:
            active.remove(inode)

    for root in selected_roots:
        walk(root, 0)
