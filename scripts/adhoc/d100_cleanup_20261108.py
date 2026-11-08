"""D100 offline cleanup provenance, 2026-11-08.
Inputs: root drafts, ATTIC copies, repository generators. Outputs: scratch audit/logs.
Serves D100 stacked cleanup after PR #5531; no network or deletion capability.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-d100-cleanup'
LOCK = ROOT.parent / 'plans/native_quiet_window.lock'

def quiet():
    if LOCK.exists():
        raise SystemExit('Quiet window active; defer work: ' + LOCK.read_text())

def audit():
    quiet()
    listing = subprocess.run(['rg', '--files', '--hidden', '--no-ignore', '-g', '!.git/**'], cwd=ROOT, capture_output=True, text=True, check=True)
    (SCRATCH / 'inventory.txt').write_text(listing.stdout)
    paths = [p for p in listing.stdout.splitlines() if not any(part in {'.git', '.venv', 'node_modules', '__pycache__', '.aws', '.ssh'} for part in Path(p).parts) and not Path(p).name.startswith('.env') and not any(x in Path(p).name.lower() for x in ('credential', 'secret', 'token'))]
    rows = []
    for draft in sorted(ROOT.glob('D4D_*.yaml')):
        archive = ROOT / 'data/ATTIC/root_schema_drafts_2026-08-08' / draft.name
        matches = []
        for offset in range(0, len(paths), 200):
            result = subprocess.run(['rg', '--no-ignore', '--hidden', '-n', '-F', draft.name, '--', *paths[offset:offset + 200]], cwd=ROOT, capture_output=True, text=True)
            if result.returncode not in (0, 1):
                raise RuntimeError(result.stderr)
            matches.append(result.stdout)
        output = ''.join(matches)
        (SCRATCH / (draft.stem + '-references.txt')).write_text(output)
        rows.append({'path': draft.name, 'bytes': draft.stat().st_size, 'sha256': hashlib.sha256(draft.read_bytes()).hexdigest(), 'identical': archive.exists() and draft.read_bytes() == archive.read_bytes(), 'reference_lines': len(output.splitlines()), 'references': draft.stem + '-references.txt'})
    (SCRATCH / 'draft-audit.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(rows, indent=2))

def run(label, command):
    quiet()
    env = dict(os.environ)
    env.update(PYTHONPATH=f'{ROOT}/src:{ROOT}', PYTHONPYCACHEPREFIX=str(SCRATCH / 'pycache'), TMPDIR=str(SCRATCH), VIRTUAL_ENV=str(ROOT.parent.parent / 'data-sheets-schema/.venv'), POETRY_VIRTUALENVS_CREATE='false', PIP_NO_INDEX='1')
    env['PATH'] = env['VIRTUAL_ENV'] + '/bin:' + env['PATH']
    with (SCRATCH / (label + '.log')).open('w') as log:
        log.write('COMMAND: ' + repr(command) + '\n'); log.flush()
        proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL); proc.wait()
            code = 124
        log.write(f'\nEXIT: {code}\n')
    print(label, code)
    raise SystemExit(code)

if __name__ == '__main__':
    SCRATCH.mkdir(exist_ok=True)
    if sys.argv[1] == 'audit':
        audit()
    else:
        run(sys.argv[1], sys.argv[2:])
