"""Copy bounded offline native failure diagnostics relative to pytest basetemp.

Inputs: basetemp and output directory. Outputs: allowlisted files and manifest.
Variant advance assignment, 2026-11-15. Excludes configs, environment and caches.
"""
import argparse
import json
import os
from pathlib import Path

FILE_LIMIT = 2 * 1024 * 1024
TOTAL_LIMIT = 24 * 1024 * 1024
COUNT_LIMIT = 128
NAMES = {'stderr.txt', 'control.jsonl', 'transcript.jsonl', 'host-controller-timing.jsonl'}


def candidates(base):
    for root, directories, files in os.walk(base, followlinks=False):
        directories.sort()
        path = Path(root)
        if path.name != 'native-attempt':
            continue
        directories.clear()
        for name in sorted(files, key=lambda name: (name not in NAMES, name)):
            yield path / name


def collect(base, destination):
    base = Path(base).resolve()
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    rows, used = [], 0
    for path in candidates(base):
        relative = path.relative_to(base)
        if path.parent.name != 'native-attempt':
            continue
        if path.name not in NAMES and not (path.name.startswith('host-clock-') and path.suffix == '.json'):
            continue
        if any(parent.is_symlink() for parent in (path, *path.parents)) or not path.is_file():
            continue
        if len(rows) >= COUNT_LIMIT or used >= TOTAL_LIMIT:
            break
        size = path.stat().st_size
        limit = min(FILE_LIMIT, TOTAL_LIMIT - used)
        with path.open('rb') as stream:
            # Tail retains the failing helper and its timing, not just startup.
            stream.seek(max(0, size - limit))
            raw = stream.read(limit)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        used += len(raw)
        rows.append({'path': relative.as_posix(), 'source_bytes': size,
                     'saved_bytes': len(raw), 'tail_truncated': size > len(raw)})
    manifest = {'file_limit': FILE_LIMIT, 'total_limit': TOTAL_LIMIT, 'count_limit': COUNT_LIMIT,
                'saved_bytes': used, 'files': rows,
                'scope': 'Allowlisted offline diagnostics only; truncated tails are not replay evidence.'}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('basetemp')
    parser.add_argument('destination')
    args = parser.parse_args()
    collect(args.basetemp, args.destination)
