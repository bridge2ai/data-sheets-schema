#!/usr/bin/env python3
# Purpose: portable historical-byte assertions for the G1 instrument change.
# Inputs: step-0 Git objects; output: six predecessor hashes in a test fixture.
# Generality F8, review G1-R4, 2026-10-29. Offline; historical assets are read only.
import hashlib
import json
from pathlib import Path
import subprocess
from data_sheets_schema.semantic_instrument import select_semantic_instrument

ROOT = Path(__file__).resolve().parents[2]
BASE = '55c7b94b838eb500888055da5a47acf2ee9e2e15'
hashes = {}
for family, version in [('rubric10', '3.0'), ('rubric20', '4.0')]:
    instrument = select_semantic_instrument(family, version)
    for field in ('definition_path', 'rubric_path', 'schema_path'):
        path = getattr(instrument, field)
        raw = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
        assert (ROOT / path).read_bytes() == raw
        hashes[path] = hashlib.sha256(raw).hexdigest()
output = ROOT / 'tests/fixtures/generality/semantic_predecessors.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({'captured_at_base': BASE, 'sha256': hashes}, indent=2) + '\n')
assert json.loads(output.read_bytes())['sha256'] == hashes
print(output)
