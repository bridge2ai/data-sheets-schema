"""#5517 D102 live-pin inventory/rotation, 2026-11-08.
Inputs: six contexts, Git round-1/pre-proposal versions and decision table.
Outputs: ignore-independent rg search evidence and old/new digest ledger in scratch;
--apply updates only the six live table hashes. Historical/protected files untouched.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
import yaml
from data_sheets_schema.evaluation_context import context_digest
ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-codex-5517'
assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
note = ROOT / 'notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md'
text = note.read_text()
rows = []
patterns = []
for path in sorted((ROOT / 'data/context').glob('*_context.yaml')):
    name = path.stem.removesuffix('_context').upper()
    original_note = subprocess.check_output(['git', 'show', '5ab230659:' + str(note.relative_to(ROOT))], text=True)
    line = next(line for line in original_note.splitlines() if line.startswith('| **' + name + '**'))
    old = re.search(r'`([a-f0-9]{64})`', line)[1]
    new = context_digest(yaml.safe_load(path.read_text()))
    patterns.extend([old, str(path.relative_to(ROOT)), path.name])
    for rev in ('5ab230659', 'cf50d9a1c'):
        raw = subprocess.check_output(['git', 'show', rev + ':' + str(path.relative_to(ROOT))])
        patterns += [hashlib.sha256(raw).hexdigest(), context_digest(yaml.safe_load(raw))]
    rows.append(dict(project=name, file=str(path.relative_to(ROOT)), old=old, new=new, old_line=line, new_line=line.replace(old, new)))
    if '--apply' in sys.argv:
        current = next(row for row in text.splitlines() if row.startswith('| **' + name + '**'))
        current_hash = re.search(r'`([a-f0-9]{64})`', current)[1]
        assert current.replace(current_hash, old) == line
        assert text.count(current) == 1
        text = text.replace(current, line.replace(old, new))
(SCRATCH / 'r2-pin-patterns.txt').write_text('\n'.join(sorted(set(patterns))) + '\n')
if '--search' in sys.argv:
    with (SCRATCH / 'r2-pin-search.txt').open('w') as out:
        result = subprocess.run(['rg', '--hidden', '--no-ignore', '--text', '-n', '-F', '-f', str(SCRATCH / 'r2-pin-patterns.txt'), '.'], cwd=ROOT, stdout=out)
    assert result.returncode in (0, 1)
(SCRATCH / 'r2-pin-ledger.json').write_text(json.dumps(rows, indent=2) + '\n')
if '--apply' in sys.argv:
    note.write_text(text)
    assert note.read_text() == text
print('\n'.join(f'{r["project"]}: {r["old"]} -> {r["new"]}' for r in rows))
