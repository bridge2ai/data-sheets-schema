"""PR #5532/#5517, 2026-11-08: apply R6 context edits and D102 pins.

Inputs: declared bundles and current context YAML. Outputs: edited contexts,
committed D103 search record, live pin table and scratch digest ledger. Offline.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import yaml
from data_sheets_schema.evaluation_context import context_digest, load_context

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-5517'
assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
bundle = 'data/preprocessed/concatenated/CM4AI_preprocessed.txt'
pattern = r'access|credential|embargo|agreement|committee|restricted|controlled|permission|license|licensing|\bDUA\b|\bDAC\b|\bMTA\b|regulated'
command = ['python', 'scripts/adhoc/context_evidence_5517_search.py', pattern, bundle]
result = subprocess.run([sys.executable, *command[1:]], cwd=ROOT, capture_output=True, text=True, check=True, timeout=60)
digest = hashlib.sha256((ROOT / bundle).read_bytes()).hexdigest()
record = 'scripts/adhoc/context_evidence_5517_r6_cm4ai_search.txt'
(ROOT / record).write_text(
    '# #5517 D103 bundle search, 2026-11-08\n'
    '# Scope: complete declared bundle; direct read includes ignored/hidden files.\n'
    f'# Bundle: {bundle}\n# SHA256: {digest}\n'
    '# Original command (JSON argv): ' + json.dumps(['rg', '--hidden', '--no-ignore', '-n', '-i', pattern, bundle]) + '\n'
    '# Python reproduction: case-insensitive regex; LF-only lines.\n'
    '# Command (JSON argv): ' + json.dumps(command) + '\n'
    f'# Matching lines: {len(result.stdout.splitlines())}\n' + result.stdout)

for name in ('cm4ai', 'ai_readi', 'voice_pediatric', 'chorus', 'kids_first'):
    path = ROOT / f'data/context/{name}_context.yaml'
    raw = path.read_text()
    entries = yaml.safe_load(raw)
    for pred, entry in entries.items():
        old = entry['evidence']
        new = old
        if name == 'cm4ai' and pred == 'regulated_access':
            notes, end = json.JSONDecoder().raw_decode(old[len('[search_notes] '):])
            notes = (f'D103: complete declared bundle {bundle}; SHA256 {digest}; '
                     f'case-insensitive terms {pattern}; ignored/hidden files included by direct read. '
                     f'{len(result.stdout.splitlines())} matching lines; full output and argv in {record}. '
                     'No positive research-access gate established by these hits. ' + notes)
            new = '[absence_supported: true] [search_notes] ' + json.dumps(notes) + old[len('[search_notes] ') + end:]
        elif name == 'ai_readi' and pred in ('data_processing', 'processing_software'):
            new = old.replace('[search_notes]', '[context_note: D120]')
            if pred == 'data_processing':
                new = new.replace(' D104 direct software evidence remains in c018.', '')
        elif name == 'voice_pediatric' and pred == 'data_processing':
            _, end = json.JSONDecoder().raw_decode(old[len('[search_notes] '):])
            new = old[len('[search_notes] ') + end:].lstrip()
        elif name == 'chorus' and pred == 'processing_software':
            new = old.replace('who have produced', r'We have software contributors within CHoRUS who have a broad range of expertise, and\n\nwho have produced')
        elif name == 'kids_first' and pred == 'human_subjects':
            new = old.replace('is a single individual', r'A\nparticipant\nis a single individual')
        if new != old:
            old_line = next(line for line in raw.splitlines() if line.startswith('  evidence: ') and yaml.safe_load(line)['evidence'] == old)
            raw = raw.replace(old_line, '  evidence: ' + json.dumps(new, ensure_ascii=False))
    path.write_text(raw)

note = ROOT / 'notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md'
text = note.read_text()
ledger = {}
for path in sorted((ROOT / 'data/context').glob('*_context.yaml')):
    digest = context_digest(load_context(path))
    ledger[path.stem.removesuffix('_context').upper()] = digest
    text, count = re.subn(r'(`data/context/' + path.name + r'` \| `)[a-f0-9]{64}', lambda m: m[1] + digest, text)
    assert count == 1
note.write_text(text)
OUT.mkdir(exist_ok=True)
(OUT / 'r6-digests.json').write_text(json.dumps(ledger, indent=2) + '\n')
print(json.dumps(ledger, indent=2))
