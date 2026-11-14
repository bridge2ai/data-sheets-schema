"""Retain code/tests and exclude incoming saved evidence for the v3 merge.

2026-11-14 Claude-lead assignment. Inputs: HEAD, MERGE_HEAD, kept test sources.
Outputs: exclusion inventory in external scratch; --apply restores excluded
paths to HEAD in this worktree/index only. Incoming commits remain untouched.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scratch', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--canary', action='store_true')
    args = parser.parse_args()
    assert not (args.apply and args.canary)
    ours, theirs = (git('rev-parse', ref).decode().strip() for ref in ('HEAD', 'MERGE_HEAD'))
    base = git('merge-base', ours, theirs).decode().strip()
    incoming = git('diff', '--name-only', base, theirs).decode().splitlines()
    required = set()
    for path in (ROOT / 'tests').rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                literal = node.value
                if literal.startswith('scripts/adhoc/') and literal.endswith('.py'):
                    required.add(literal)
    kept, excluded = [], []
    for relative in incoming:
        keep = relative.startswith(('src/', 'tests/')) or relative == 'scripts/native_environment_manifest.py' or relative in required
        raw = git('show', theirs + ':' + relative)
        row = dict(path=relative, bytes=len(raw), lines=len(raw.splitlines()),
                   incoming_sha256=hashlib.sha256(raw).hexdigest())
        if keep:
            row['reason'] = 'test-imported helper' if relative in required else 'production code or tests'
            kept.append(row)
        else:
            assert relative.startswith('scripts/adhoc/'), relative
            row['reason'] = 'unneeded adhoc producer' if relative.endswith('.py') else 'saved evidence or draft'
            row['action'] = 'restore candidate version' if git('ls-tree', ours, '--', relative) else 'exclude incoming addition'
            excluded.append(row)
    report = dict(candidate=ours, incoming=theirs, merge_base=base,
                  kept=kept, excluded=excluded,
                  excluded_lines=sum(row['lines'] for row in excluded),
                  required_incoming_helpers=sorted(set(incoming) & required))
    args.scratch.mkdir(exist_ok=True)
    (args.scratch / 'merge-file-inventory.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['| Excluded file | Lines | Reason |', '| --- | ---: | --- |']
    lines.extend(f"| `{row['path']}` | {row['lines']} | {row['reason']} |" for row in excluded)
    (args.scratch / 'excluded-files.md').write_text('\n'.join(lines) + '\n')
    targets = excluded[:1] if args.canary else excluded
    if args.apply or args.canary:
        changed = [row['path'] for row in targets if git('diff', '--cached', ours, '--', row['path'])]
        if changed:
            subprocess.run(['git', 'restore', '--source', ours, '--staged', '--worktree', '--',
                            *changed], cwd=ROOT, check=True)
        for row in targets:
            assert not git('diff', '--cached', ours, '--', row['path'])
            assert not git('diff', '--', row['path'])
            if row['action'] == 'exclude incoming addition':
                assert not (ROOT / row['path']).exists()
            assert hashlib.sha256(git('show', theirs + ':' + row['path'])).hexdigest() == row['incoming_sha256']
    print(json.dumps(dict(candidate=ours, incoming=theirs, merge_base=base,
        kept_files=len(kept), excluded_files=len(excluded), excluded_lines=report['excluded_lines'],
        kept_helpers=report['required_incoming_helpers'], applied=args.apply,
        canary=args.canary, verified_exclusions=[row['path'] for row in targets] if args.apply or args.canary else []), indent=2))


if __name__ == '__main__':
    main()
