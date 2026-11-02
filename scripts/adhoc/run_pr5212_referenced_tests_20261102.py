#!/usr/bin/env python3
"""#5212 round 7, 2026-11-02: select every journal/ownership reference offline.

Inputs: pinned --tree, scratch --basetemp, worker count. Outputs: sorted
ignore-independent selection manifest, command, pytest log and phase ledger.
No source overlays or network. --plan records selection without running tests.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--tree', type=Path, required=True)
p.add_argument('--basetemp', type=Path, required=True)
p.add_argument('--workers', type=int, choices=(3, 4), default=3)
p.add_argument('--probe-dir', type=Path, help='Read-only directory of independent observer plugins')
p.add_argument('--plugin', action='append', default=[])
p.add_argument('--plan', action='store_true')
a = p.parse_args()
assert 'scratch-5212fix' in a.basetemp.parts
search = ['rg', '-uu', '-l', '--glob', 'test*.py',
          'pending_launch_paths|require_selected_resume_owner|refuse_legacy_execution|_events|latch_journal|output_ownership',
          'tests']
files = sorted(subprocess.check_output(search, cwd=a.tree, text=True).splitlines())
assert files and len(files) == len(set(files))
assert not a.plugin or a.probe_dir is not None
runner = ('run_pr5212_review_probes_20261102.py' if a.probe_dir
          else 'run_d68_round4_20261101.py')
command = [sys.executable, '-S', '-P', '-B', str(Path(__file__).with_name(runner)),
           *(['--probe-dir', str(a.probe_dir)] if a.probe_dir else []),
           '--tree', str(a.tree), '--basetemp', str(a.basetemp), *files,
           *(value for name in a.plugin for value in ('-p', name)),
           '-v', '-n', str(a.workers), '--dist', 'load', '--maxschedchunk=1', '--durations=25']
record = {'search': search, 'ignored_files_included': True, 'files': files,
          'observer_sha256': {name: hashlib.sha256(
              (a.probe_dir / (name + '.py')).read_bytes()).hexdigest() for name in a.plugin},
          'sha256': {name: hashlib.sha256((a.tree / name).read_bytes()).hexdigest() for name in files},
          'command': command}
manifest = a.basetemp.with_suffix('.selection.json')
manifest.write_text(json.dumps(record, indent=2))
a.basetemp.with_suffix('.files.txt').write_text('\n'.join(files) + '\n')
if a.plan:
    print(json.dumps({'files': len(files), 'manifest': str(manifest)}))
    raise SystemExit(0)
start = time.monotonic()
with a.basetemp.with_suffix('.log').open('w') as stream:
    result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
record.update(exit_code=result.returncode, wall_seconds=time.monotonic() - start)
manifest.write_text(json.dumps(record, indent=2))
print(json.dumps({'files': len(files), 'exit_code': result.returncode,
                  'wall_seconds': record['wall_seconds']}))
raise SystemExit(result.returncode)
