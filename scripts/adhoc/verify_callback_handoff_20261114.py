"""Issue 6233, 2026-11-14: check local handoff references and protected bytes.

Inputs: handoff, worktree, scratch, output JSON. Outputs: existence checks,
protected-file comparison with the assigned base, and a printed handoff hash.
No referenced evidence or Git state is changed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser()
    for name in ('handoff', 'worktree', 'scratch', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    raw = args.handoff.read_bytes()
    text = raw.decode()
    references = set()
    for alias, rest in re.findall(r'\b(W|S)/([^\s`;,]+)', text):
        references.add((args.worktree if alias == 'W' else args.scratch) / rest.rstrip('.'))
    for absolute in re.findall(r'`(/[^`]+)`', text):
        references.add(Path(absolute))
    paths = []
    for path in sorted(references):
        # Table generators accept an output prefix whose actual artifacts have
        # .md/.json suffixes; report that distinction explicitly.
        prefix = not path.exists() and path.with_suffix('.md').is_file() and path.with_suffix('.json').is_file()
        paths.append({'path': str(path), 'exists': path.exists(), 'artifact_prefix': prefix})
    protected = []
    for relative in ('src/data_sheets_schema/shared_generation.py',
                     'src/data_sheets_schema/api_runner.py',
                     'src/download/prompts/canonical_hashes.yaml',
                     'tests/utils/run_spec_boundary_contracts.json'):
        before = subprocess.run(['git', '-C', str(args.worktree), 'show',
                                 'f498f82d6:' + relative], check=True, capture_output=True).stdout
        current = (args.worktree / relative).read_bytes()
        protected.append({'path': relative, 'unchanged': before == current,
                          'sha256': hashlib.sha256(current).hexdigest()})
    result = {'handoff_sha256': hashlib.sha256(raw).hexdigest(),
              'no_at_signs': chr(64) not in text, 'references': paths, 'protected': protected}
    result['passed'] = (result['no_at_signs'] and all(row['unchanged'] for row in protected)
                        and all(row['exists'] or row['artifact_prefix'] for row in paths))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
