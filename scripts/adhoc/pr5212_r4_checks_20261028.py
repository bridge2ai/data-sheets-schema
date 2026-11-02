#!/usr/bin/env python3
"""#5212 R2, 2026-10-28: serial offline regression launcher and evidence.

Inputs: this worktree, named test groups, existing project Python environment.
Outputs: commands, source/dependency identity, pytest logs/XML and outcomes in
--out; pytest fixtures exclusively in $TMPDIR/codex-5212r4-pt. Run canary first.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.adhoc.pr5212_d55_checks_20261028 import ROUTING

CORE = ['tests/test_latch_journal.py', 'tests/test_api_latch_guard.py',
        'tests/test_pr5212_d55_fixes.py', 'tests/test_pr5212_r3_fixes.py',
        'tests/test_pr5212_r4_fixes.py']
F2 = [f'tests/test_{name}.py' for name in (
    'anonymous_relationship_evidence', 'canary_gate', 'evidence_generation_gate',
    'evidence_phase_contract', 'generation_snapshot_ownership',
    'receipt_completion_runtime', 'report_gate', 'snapshot_attempt_recovery',
    'source_review', 'unusable_snapshot', 'usage_ledger')]
GROUPS = {
    'canary': ['tests/test_pr5212_r3_fixes.py::test_refused_forgery_cannot_supply_the_next_monitored_resume_head'],
    'r2-focused': ['tests/test_pr5212_d55_fixes.py::test_resume_needs_external_head_before_recovery_or_dispatch',
                   'tests/test_pr5212_r4_fixes.py::test_cli_refusal_redacts_heads_in_output_exception_and_logs'],
    'core-f2': CORE + F2,
    'routing': ROUTING,
    'parity': ['tests/test_d41_request_parity.py'],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--collect-only', action='store_true')
    parser.add_argument('groups', nargs='+', choices=GROUPS)
    args = parser.parse_args()
    env = {k: v for k, v in os.environ.items() if k not in {
        'ANTHROPIC_API_KEY', 'CBORG_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_BASE_URL'}}
    env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
    for group in args.groups:
        out = args.out / group
        out.mkdir(parents=True, exist_ok=False)
        command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-o', 'addopts=',
                   '--basetemp=' + str(Path(env['TMPDIR']) / 'codex-5212r4-pt'),
                   '--junitxml=' + str(out.resolve() / 'results.xml'), *GROUPS[group]]
        if args.collect_only:
            command.append('--collect-only')
        pins = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
            'src/data_sheets_schema/latch_journal.py', 'poetry.lock', *CORE,
            str(Path(__file__).relative_to(ROOT)))}
        (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
        print(f'START {group}: {out}', flush=True)
        with (out / 'pytest.log').open('x') as stream:
            completed = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        outcome = {'group': group, 'returncode': completed.returncode,
                   'collect_only': args.collect_only, 'python': sys.version, 'executable': sys.executable,
                   'base_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   'source_sha256': pins,
                   'source_unchanged': all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h
                                           for p, h in pins.items())}
        if (out / 'results.xml').is_file():
            cases = list(ET.parse(out / 'results.xml').getroot().iter('testcase'))
            outcome.update(tests=len(cases), failures=sum(c.find('failure') is not None for c in cases),
                           errors=sum(c.find('error') is not None for c in cases),
                           skipped=sum(c.find('skipped') is not None for c in cases))
        (out / 'outcome.json').write_text(json.dumps(outcome, indent=2) + '\n')
        assert (out / 'pytest.log').stat().st_size > 0
        print('\n'.join((out / 'pytest.log').read_text().splitlines()[-8:]), flush=True)
        if completed.returncode or not outcome['source_unchanged']:
            return completed.returncode or 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
