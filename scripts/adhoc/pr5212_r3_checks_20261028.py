#!/usr/bin/env python3
"""#5212 R1-R9, 2026-10-28: serial offline acceptance and retained evidence.

Inputs: selected current worktree and explicit test groups (including saved F2
nodes). Outputs: external pytest logs/XML, commands and source identity JSON.
Run canary first with the same launcher, then the remaining groups serially.
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


def source_pins():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ('src/data_sheets_schema', 'tests', 'scripts/adhoc')
            for path in sorted((ROOT / folder).rglob('*.py'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('groups', nargs='+')
    args = parser.parse_args()
    from scripts.adhoc.pr5212_d55_checks_20261028 import ROUTING
    groups = {
        'canary': ['tests/test_pr5212_r3_fixes.py::test_refused_forgery_cannot_supply_the_next_monitored_resume_head'],
        'core': ['tests/test_latch_journal.py', 'tests/test_api_latch_guard.py',
                 'tests/test_pr5212_d55_fixes.py', 'tests/test_pr5212_r3_fixes.py'],
        'f2': (ROOT / 'notes/reviews/pr5212_d55_f2_nodes.txt').read_text().splitlines(),
        'routing': ROUTING,
        'parity': ['tests/test_d41_request_parity.py'],
        'report': ['tests/test_report_gate.py', 'tests/test_report_admission.py'],
        'provenance': [str(p.relative_to(ROOT)) for p in sorted((ROOT / 'tests').rglob('test*provenance*.py'))],
        'a13': ['tests/test_receipt_floor_basis.py', 'tests/test_receipt_completion_policy.py',
                'tests/test_receipt_completion_runtime.py', 'tests/test_rereceipt_completion.py',
                'tests/test_receipts.py', 'tests/test_receipt_rereceipt.py'],
        'options': ['tests/test_api_launcher.py', 'tests/test_shared_generation_cli.py',
                    'tests/test_shared_generation_batch_authority.py'],
    }
    if set(args.groups) - groups.keys():
        parser.error('unknown group')
    args.out.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k not in {
        'ANTHROPIC_API_KEY', 'CBORG_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_BASE_URL'}}
    env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
    for group in args.groups:
        out = args.out / group
        out.mkdir(exist_ok=False)
        command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '-o', 'addopts=',
                   '--basetemp=' + str(Path(env.get('TMPDIR', '/private/tmp')) / 'codex-5212r3-pt'),
                   '--junitxml=' + str(out / 'results.xml'), *groups[group]]
        before = source_pins()
        (out / 'source-pins.json').write_text(json.dumps(before, indent=2) + '\n')
        (out / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
        print(f'START {group}: {len(groups[group])} selections; {out}', flush=True)
        with (out / 'pytest.log').open('x') as stream:
            completed = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        same = before == source_pins()
        outcome = {'group': group, 'returncode': completed.returncode, 'source_unchanged': same,
                   'python': sys.version, 'executable': sys.executable,
                   'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
        if (out / 'results.xml').is_file():
            suites = ET.parse(out / 'results.xml').getroot()
            cases = list(suites.iter('testcase'))
            outcome.update(tests=len(cases), failures=sum(c.find('failure') is not None for c in cases),
                           errors=sum(c.find('error') is not None for c in cases),
                           skipped=sum(c.find('skipped') is not None for c in cases))
        (out / 'outcome.json').write_text(json.dumps(outcome, indent=2) + '\n')
        print(json.dumps(outcome), flush=True)
        print('\n'.join((out / 'pytest.log').read_text().splitlines()[-5:]), flush=True)
        if completed.returncode or not same:
            return completed.returncode or 1
    return 0


if __name__ == '__main__':
    # Direct script execution needs this checkout's scripts package, not an
    # editable installation from another worktree.
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
