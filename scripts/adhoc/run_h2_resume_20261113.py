#!/usr/bin/env python3
"""Run assigned offline resume checks; issues 6193-6202, 2026-11-13.
Inputs: this worktree, explicit cohort. Outputs: exact command, log and JUnit
in sibling scratch-h2-resume-20261113. No provider or native binary calls.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-h2-resume-20261113'
PYTHON = ROOT.parent.parent / 'data-sheets-schema/.venv/bin/python'
PUBLIC = {
 'correction': 'tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion',
 'omissions': 'tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses',
 'pending': 'tests/test_native_pending_public_completion.py::test_pending_floor_public_completion_retains_diagnostic_reading',
}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('cohort')
    p.add_argument('nodes', nargs='*')
    p.add_argument('--workers', type=int, choices=range(5), default=0)
    args = p.parse_intermixed_args()
    if args.workers and args.cohort in (*PUBLIC, 'native', 'audit', 'budget'):
        p.error('public tests and exact offline lanes must run serially')
    out = OUT / args.cohort
    out.mkdir(parents=True, exist_ok=False)
    env = {k: v for k, v in os.environ.items() if not (k.endswith('_API_KEY') or k in (
        'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL'))}
    env.pop('PYTHONDONTWRITEBYTECODE', None)
    env.update(PYTHONPATH=str(ROOT / 'src'),
        TMPDIR=str(out), PYTHONPYCACHEPREFIX=str(out / 'pycache'))
    nodes = args.nodes or ([PUBLIC[args.cohort]] if args.cohort in PUBLIC else [])
    argv = ['-q', '-p', 'no:cacheprovider', *nodes]
    if args.cohort in ('native', 'audit', 'budget'):
        flow = yaml.safe_load((ROOT / '.github/workflows/main.yaml').read_text())
        job = 'offline-audit' if args.cohort == 'audit' else 'offline-canary'
        prefix = {'audit': 'Exercise native audit', 'native': 'Exercise native canary',
                  'budget': 'Exercise experimental canary'}[args.cohort]
        step = next(s for s in flow['jobs'][job]['steps'] if s.get('name', '').startswith(prefix))
        env.update({k: str(v) for k, v in step.get('env', {}).items()})
        env.pop('PYTHONPYCACHEPREFIX', None)
        if args.cohort == 'budget':
            env.pop('PYTHONPATH', None)
        argv = [a for a in shlex.split(step['run'])[5:] if not a.startswith('--junitxml=')]
        (out / 'ci-step.json').write_text(json.dumps(step, indent=2) + '\n')
    if args.workers:
        argv += ['-n', str(args.workers)]
    argv += ['--basetemp=' + str(out / 'cases'), '--junitxml=' + str(out / 'pytest.xml')]
    command = [str(PYTHON), '-m', 'pytest', *argv]
    record = {'command': command, 'cwd': str(ROOT), 'environment': {k: env[k] for k in (
        'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'PYTHONPYCACHEPREFIX', 'TMPDIR') if k in env},
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
    (out / 'command.json').write_text(json.dumps(record, indent=2) + '\n')
    start = time.monotonic()
    with (out / 'pytest.log').open('xb') as log:
        code = subprocess.call(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    result = {'returncode': code, 'seconds': time.monotonic() - start}
    (out / 'outcome.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return code

if __name__ == '__main__':
    raise SystemExit(main())
