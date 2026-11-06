# Purpose: export exact M7 sources for #5508 historical replay, offline.
# Inputs: local Git objects. Outputs: scratch baseline and detached local Git metadata.
# Date: 2026-11-06. Creates no commit, fetch, checkout or shared worktree mutation.
import io
from pathlib import Path
import shutil
import subprocess
import tarfile
ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT.parent/'plans/native_quiet_window.lock'
if LOCK.exists():
    raise SystemExit('quiet window: export not started')
BASE = ROOT.parent/'scratch-native-u2/baseline'
BASE.mkdir()
commit = '8bc90e93d736d464f98e9eedffee45f0ad8e5d3f'
raw = subprocess.check_output(['git', 'archive', commit], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
    archive.extractall(BASE, filter='data')
subprocess.run(['git', 'init', '-q', str(BASE)], check=True)
objects = subprocess.check_output(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], cwd=ROOT, text=True).strip()
(BASE/'.git/objects/info/alternates').write_text(str(Path(objects)/'objects')+'\n')
(BASE/'.git/HEAD').write_text(commit+'\n')
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BASE, text=True).strip() == commit
shutil.copyfile(ROOT/'tests/test_native_authority_replay_v1.py', BASE/'tests/test_native_authority_replay_v1.py')
print(BASE)
