#!/usr/bin/env python3
"""Record and repair G2-REVIEW-RUNNER-F1, 2026-11-14.
Inputs: assigned G2 runner. Outputs: immutable prior-source snapshot and review
record in sibling scratch, plus ignored-inclusive Python source validation.
No tests, commits, project imports or provider calls are performed.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-g2-20261114'
runner = ROOT / 'scripts/adhoc/run_g2_checks_20261114.py'
raw = runner.read_bytes()
snapshot = SCRATCH / 'review-runner-before.txt'
review = SCRATCH / 'review-runner.json'
with snapshot.open('xb') as stream:
    stream.write(raw)
record = {
    'finding_id': 'G2-REVIEW-RUNNER-F1', 'severity': 'P2',
    'status': 'recorded-before-fix',
    'finding': 'git diff HEAD ignores untracked files, so the runner can execute an uncommitted selected test or Python import while recording only HEAD.',
    'repair': 'Inventory source/test Python with ignored and hidden files included, compare to tracked files, and require selected files to be tracked; directories must stay within tests.',
    'lead_filing_needed': True, 'github_issue_number': None,
    'filing_reason': 'Helper GitHub writes are prohibited.',
    'head_before': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'prior_runner': {'path': str(snapshot), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
    'verification': 'Not yet run; use verify_g2_runner_inventory_20261114.py after the coordinated source freeze.',
}
with review.open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
source = raw.decode()
anchor = '\n\ndef main():\n'
assert source.count(anchor) == 1
addition = '''

def python_inventory(root, selectors):
    """Read ignored and hidden Python paths; selected test files must be tracked."""
    root = Path(root).resolve(strict=True)
    tracked_command = ['git', 'ls-files', '-z']
    tracked_raw = subprocess.check_output(tracked_command, cwd=root)
    tracked = {os.fsdecode(path) for path in tracked_raw.split(b'\\0') if path}
    inventory_command = ['rg', '--files', '--hidden', '--no-ignore', '--null',
                         'src', 'tests', '-g', '*.py', '-g', '*.pyi']
    inventory = subprocess.run(inventory_command, cwd=root, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
    if inventory.returncode not in (0, 1):
        raise RuntimeError('ignored-inclusive Python inventory failed')
    found = {os.fsdecode(path) for path in inventory.stdout.split(b'\\0') if path}
    untracked = sorted(found - tracked)
    if untracked:
        raise ValueError('untracked source/test Python (ignored files included): '
                         + ', '.join(untracked))
    selected = []
    for selector in selectors:
        path_text, separator, _node = selector.partition('::')
        candidate = Path(os.path.abspath(root / path_text))
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError('selected test must stay inside the assigned checkout') from exc
        if not candidate.exists() or candidate.resolve(strict=True) != candidate:
            raise ValueError('selected test must be an existing physical checkout path: ' + path_text)
        if candidate.is_dir():
            if separator or not (relative == Path('tests') or Path('tests') in relative.parents):
                raise ValueError('directory selectors are allowed only within tests')
        elif not candidate.is_file() or relative.as_posix() not in tracked:
            raise ValueError('selected test file must be tracked: ' + path_text)
        selected.append(relative.as_posix())
    return {'inventory_command': inventory_command, 'tracked_command': tracked_command,
            'ignored_and_hidden_files_included': True, 'python_files': len(found),
            'selected_paths': selected}
'''
source = source.replace(anchor, addition + anchor)
old = '''    # Synthetic authority must see committed implementation and tests.
    subprocess.check_call(['git', 'diff', '--exit-code', 'HEAD', '--', 'src', 'tests'], cwd=ROOT)
'''
new = '''    # A diff alone misses untracked imports/conftest files, including ignored
    # ones. Helpers/proposals outside src/tests may remain untracked.
    source_inventory = python_inventory(ROOT, args.nodes)
    subprocess.check_call(['git', 'diff', '--exit-code', 'HEAD', '--', 'src', 'tests',
                           *source_inventory['selected_paths']], cwd=ROOT)
'''
assert source.count(old) == 1
source = source.replace(old, new)
old = "        'status_before': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True)}"
new = "        'status_before': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),\n        'source_inventory': source_inventory}"
assert source.count(old) == 1
source = source.replace(old, new)
runner.write_text(source)
print(json.dumps({'review': str(review), 'sha256': hashlib.sha256(review.read_bytes()).hexdigest(),
                  'prior_runner': record['prior_runner']}))
