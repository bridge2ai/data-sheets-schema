#!/usr/bin/env python3
"""Record H2-RESUME-HARNESS-F1 and its pre-run correction, 2026-11-13.
Inputs: runner, alignment script, workflow, budget test imports and primary
interpreter editable-install path. Output: scratch budget-origin-review.json.
Read-only review provenance; no tests, package imports or external writes.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-h2-resume-20261113'
PRIMARY = ROOT.parent.parent / 'data-sheets-schema'


def pin(path):
    assert path.is_file(), str(path)
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    runner = ROOT / 'scripts/adhoc/run_h2_resume_20261113.py'
    align = ROOT / 'scripts/adhoc/align_h2_resume_cache_20261113.py'
    workflow = ROOT / '.github/workflows/main.yaml'
    test = ROOT / 'notes/matched_cborg_2026-09-13/test_budgeted_cborg.py'
    pth = PRIMARY / '.venv/lib/python3.13/site-packages/data_sheets_schema.pth'
    raw = runner.read_text()
    assert "env.pop('PYTHONPATH', None)" not in raw
    assert "env.update(PYTHONPATH=str(ROOT / 'src')," in raw
    assert "env.pop('PYTHONPYCACHEPREFIX', None)" in raw
    assert "env.update({k: str(v) for k, v in step.get('env', {}).items()})" in raw
    # The assigned supplemental cohort has not started; this review itself
    # never launches Python package code or tests to establish module origin.
    assert not (SCRATCH / 'budget/command.json').exists(), 'Budget cohort already has launch evidence.'
    imports = [{'line': number, 'text': line.strip()}
               for number, line in enumerate(test.read_text().splitlines(), 1)
               if re.match(r'\s*(?:from data_sheets_schema\b|import data_sheets_schema\b)', line)]
    assert imports
    editable_source = pth.read_text().strip()
    assert Path(editable_source).is_dir() and Path(editable_source) == PRIMARY / 'src'
    record = {
        'finding_id': 'H2-RESUME-HARNESS-F1',
        'status': 'corrected-before-run',
        'review_type': 'read-only static review',
        'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'finding': 'The supplemental budget launcher cleared PYTHONPATH although its tests import project modules and the primary interpreter editable install points to the primary checkout.',
        'effect': 'Without a worktree source override, the local budget run could mix worktree controls with primary-checkout project modules.',
        'evidence': {'editable_install': {**pin(pth), 'source_directory': editable_source},
                     'budget_test_imports': {**pin(test), 'lines': imports},
                     'corrected_runner': pin(runner), 'correction_producer': pin(align),
                     'workflow': pin(workflow)},
        'correction': 'Retain the assigned worktree src PYTHONPATH for supplemental budget. Preserve workflow DONTWRITEBYTECODE and file list, remove the cache prefix, and leave native/audit explicit CI environments unchanged.',
        'verification': {'tests_run': [], 'budget_launch_evidence_present': False,
                         'scope': 'Static corrected-launcher inspection only; runtime origin and outcomes remain for the later run.'},
        'reporting': 'Budget has an explicit local package-origin override and is supplemental to the native and audit issue lanes; it is not literal CI-environment equivalence.',
        'github_issue_number': None,
        'lead_filing_needed': True,
        'filing_reason': 'The assignment prohibits all helper GitHub writes. The lead must file the finding despite its correction before the run.',
        'causal_limit': 'No public-test failure or elapsed duration is attributed to this budget-only origin correction.'
    }
    destination = SCRATCH / 'budget-origin-review.json'
    content = (json.dumps(record, indent=2) + '\n').encode()
    assert bytes([64]) not in content
    with destination.open('xb') as stream:
        stream.write(content)
    print(json.dumps(pin(destination)))


if __name__ == '__main__':
    main()
