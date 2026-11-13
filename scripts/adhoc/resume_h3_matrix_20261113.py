"""Resume assignment codex197, 2026-11-13: run a fresh fixed offline cohort.

Inputs: committed gate source and existing stage orchestrator. Outputs: saved
command logs and verified stage outcomes in owned sibling scratch. Stops at any
failed stage; reference canary precedes all remaining packet builds.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

N = Path(__file__).resolve().parents[2]
E = N.parent
G = E / 'codex-native-pin-comparison-20261113'
S = E / 'scratch-h3-resume-matrix-20261113/attempt04'
C = E / 'scratch-h3-gate-refinements-20261113/tests/final-format-07'


def main():
    S.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=G, text=True).strip()
    stages = [('bootstrap', None), ('setup-peer', None), ('build', 'reference'),
              ('canary', None), ('private-controls', None)]
    stages += [('build', role) for role in ('later', 'AI_READI', 'CM4AI', 'VOICE',
                                          'VOICE_PEDIATRIC', 'registered', 'expired')]
    stages += [('snapshots', None), ('assemble-report', None), ('full', None)]
    for stage, role in stages:
        name = stage + ('-' + role if role else '')
        command = [sys.executable, '-S', '-P', '-B',
                   str(N / 'scripts/adhoc/run_h3_gate_stages_20261113.py'),
                   '--cohort', str(C), '--source-commit', commit,
                   '--stage', stage, '--timeout-seconds', '14400']
        if role:
            command += ['--role', role]
        with (S / (name + '-command.json')).open('x') as stream:
            json.dump({'command': command, 'cwd': str(N)}, stream, indent=2)
        print('Starting ' + name, flush=True)
        with (S / (name + '.log')).open('xb') as stream:
            result = subprocess.run(command, cwd=N, stdout=stream, stderr=subprocess.STDOUT)
        outcome = C / 'stages' / name / 'outcome.json'
        record = {'returncode': result.returncode, 'outcome_path': str(outcome)}
        if outcome.is_file():
            raw = outcome.read_bytes()
            record.update(outcome=json.loads(raw), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        with (S / (name + '-readback.json')).open('x') as stream:
            json.dump(record, stream, indent=2)
        if result.returncode or record.get('outcome', {}).get('status') != 'passed' or not record['outcome'].get('cleanup_verified'):
            print('HELD ' + name + ': ' + str(S / (name + '.log')), flush=True)
            return 1
        print('Verified ' + name, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
