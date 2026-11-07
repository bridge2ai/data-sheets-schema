"""Prepare exact offline M8/base controls, 2026-11-07.

Input: local M8 Git tree. Output: scratch archive with local read-only object
alternate and the existing U1 parity test copied unchanged. No fetch or push.
"""
from pathlib import Path
import io
import argparse
import os
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3b'
parser = argparse.ArgumentParser()
parser.add_argument('--revision', default='cf50d9a1c059f3b5030103378ccef33619475dde')
parser.add_argument('--target', choices=('m8', 'base'), default='m8')
args = parser.parse_args()
BASE = args.revision
target = SCRATCH / args.target
if (ROOT.parent / 'plans/native_quiet_window.lock').exists():
    raise SystemExit('Quiet window active')
env = {**os.environ, 'GIT_NO_LAZY_FETCH': '1'}
def run(args, cwd=ROOT):
    return subprocess.check_output(args, cwd=cwd, env=env)
target.mkdir()
with tarfile.open(fileobj=io.BytesIO(run(['git', 'archive', BASE]))) as tar:
    tar.extractall(target, filter='data')
run(['git', 'init', '-q'], target)
objects = run(['git', 'rev-parse', '--path-format=absolute', '--git-path', 'objects']).decode().strip()
(target / '.git/objects/info/alternates').write_text(objects + '\n')
run(['git', 'update-ref', '--no-deref', 'HEAD', BASE], target)
run(['git', 'read-tree', BASE], target)
shutil.copyfile(ROOT / 'tests/test_native_u1_api_parity.py', target / 'tests/test_native_u1_api_parity.py')
assert (target / 'src/data_sheets_schema/api_runner.py').stat().st_size
print(target)
