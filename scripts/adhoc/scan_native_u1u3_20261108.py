#!/usr/bin/env python3
"""U3-E 2026-11-08 same-tool offline scanner comparison and packet handoff.
Inputs: saved baseline and committed candidate; outputs only scratch-native-u1u3.
Retains complete arrays, source identities, deadlines and host load for PR review.
"""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
OUT = EXEC / 'scratch-native-u1u3'
spec = importlib.util.spec_from_file_location('composition', ROOT / 'scripts/adhoc/compose_native_u1u3_20261108.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
BASE = 'cf50d9a1c059f3b5030103378ccef33619475dde'

def main():
    c.quiet()
    archive = OUT / 'baseline.tar'
    c.git('archive', '--format=tar', '--output=' + str(archive), BASE)
    tree = OUT / 'baseline'
    tree.mkdir()
    c.extract(archive, tree)
    c.git('init', '-q', cwd=tree)
    objects = c.git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip()
    (tree / '.git/objects/info/alternates').write_text(objects + '\n')
    c.git('update-ref', '--no-deref', 'HEAD', BASE, cwd=tree)
    c.git('read-tree', BASE, cwd=tree)
    canary = OUT / 'canary-retry'
    plan = json.loads((canary / 'plan.json').read_text())
    tool = ROOT / '.claude/skills/d4d-generation-specificity-audit/scan.py'
    records = []
    for name, source in [('baseline', tree), ('combined', ROOT)]:
        c.quiet()
        env = plan['environment']
        env['PYTHONPATH'] = str(source / 'src') + ':' + str(source)
        cmd = ['/usr/bin/sandbox-exec', '-f', str(canary / 'network-denied.sb'),
               str(canary / 'venv/bin/python'), '-P', '-B', str(tool), '--root', str(source),
               '--report', str(OUT / (name + '-scanner.md')), '--json', str(OUT / (name + '-scanner.json')), '--full-json']
        started, wall = time.monotonic(), time.time()
        row = {'name': name, 'command': cmd, 'tool_sha256': c.file_sha(tool), 'load_start': os.getloadavg()}
        with (OUT / (name + '-scanner.log')).open('xb') as log:
            child = subprocess.Popen(cmd, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while child.poll() is None:
                    c.quiet()
                    if max(time.monotonic() - started, time.time() - wall) >= 3600:
                        raise TimeoutError('scanner deadline')
                    time.sleep(1)
            except BaseException:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=10)
                raise
        row.update(returncode=child.returncode, seconds=time.monotonic() - started, load_end=os.getloadavg())
        records.append(row)
        print(json.dumps(row), flush=True)
    (OUT / 'scanner-runs.json').write_text(json.dumps(records, indent=2) + '\n')

if __name__ == '__main__':
    main()
