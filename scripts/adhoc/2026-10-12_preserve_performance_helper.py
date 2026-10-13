#!/usr/bin/env python3
# Purpose: preserve historical performance helpers with their result branches.
# Inputs: an existing helper, descriptive filename, issue, purpose and worktree.
# Outputs: identical repository helper copies and SHA-256 provenance sidecars.
# Serves: #5014 performance implementation; date: 2026-10-12.
"""Keep the original helper body intact; do not execute its historical paths."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--worktree', type=Path, required=True)
    parser.add_argument('--issue', required=True)
    parser.add_argument('--purpose', required=True)
    args = parser.parse_args()
    if Path(args.name).name != args.name or not args.name.endswith('.py'):
        parser.error('--name must be a Python filename without directories')
    original = args.source.read_bytes()
    header = (
        '# Purpose: ' + args.purpose + '\n'
        '# Inputs: historical source/worktree paths explicitly recorded below.\n'
        '# Outputs: benchmark logs/JSON beside this script (original behavior).\n'
        '# Serves: ' + args.issue + '; date: 2026-10-12.\n'
        '# Historical helper: original body preserved verbatim after this header.\n'
        '# Paths are session-specific; inspect and adapt before a future run.\n'
        '# This copy was preserved after the original measurement, not rerun.\n'
    ).encode()
    preserved = header + original
    metadata = {
        'issue': args.issue,
        'original_helper': str(args.source),
        'original_sha256': hashlib.sha256(original).hexdigest(),
        'preserved_sha256': hashlib.sha256(preserved).hexdigest(),
        'original_body_retained_verbatim': True,
        'preserved_after_original_run': True,
        'executed_during_preservation': False,
        'original_output_location': str(args.source.parent),
        'limitation': 'Historical absolute paths and __file__-relative outputs remain; inspect before reuse.',
    }
    encoded = (json.dumps(metadata, indent=2) + '\n').encode()
    roots = (Path(__file__).resolve().parents[2], args.worktree.resolve())
    outputs = []
    for root in dict.fromkeys(roots):
        folder = root / 'scripts/adhoc'
        for path, content in ((folder / args.name, preserved),
                              (folder / (args.name + '.provenance.json'), encoded)):
            if path.exists() and path.read_bytes() != content:
                raise SystemExit(f'Refusing to replace different content: {path}')
            outputs.append((path, content))
    for path, content in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open('xb') as stream:
                stream.write(content)
        print(path)


if __name__ == '__main__':
    main()
