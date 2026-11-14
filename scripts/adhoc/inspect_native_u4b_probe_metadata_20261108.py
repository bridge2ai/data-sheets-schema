#!/usr/bin/env python3
"""Inspect saved U4b A2 protocol metadata, 2026-11-08 (#4354).

Inputs: explicit local JSON request or JSONL transcript paths. Output: JSON
metadata on stdout; excludes prompts, message content, headers and account data.
No executable, provider or network access. Original evidence is never changed.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    result = []
    for path in args.paths:
        limit = 8 * 1024 * 1024
        with path.open('rb') as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('metadata inspection requires bounded saved evidence')
        rows = ([(index, json.loads(line)) for index, line in enumerate(raw.splitlines(), 1)
                 if line.strip()] if path.suffix == '.jsonl' else [(1, json.loads(raw))])
        selected = []
        for index, row in rows:
            if row.get('type') == 'system' and row.get('subtype') == 'init':
                selected.append({'line': index, 'kind': 'init', 'keys': sorted(row),
                    'model': row.get('model'), 'limits': row.get('limits'),
                    'thinking': row.get('thinking'), 'session_present': bool(row.get('session_id'))})
            elif row.get('type') == 'result':
                selected.append({'line': index, 'kind': 'result', 'keys': sorted(row),
                    'subtype': row.get('subtype'), 'is_error': row.get('is_error'),
                    'modelUsage': row.get('modelUsage'), 'session_present': bool(row.get('session_id'))})
            elif path.suffix != '.jsonl':
                selected.append({'kind': 'request', 'keys': sorted(row),
                    'model': row.get('model'), 'thinking': row.get('thinking')})
        result.append({'path': str(path), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(), 'rows': len(rows), 'metadata': selected})
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
