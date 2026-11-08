"""#4354 U1 2026-11-06: populate the archived FAIRSCAPE gitlink offline.
Input: exact locally available submodule commit; output: scratch-only subtree
and identity record. No install, remote access, or parent-worktree mutation.
"""
import io
import json
import tarfile
from native_u1_round2_20261106 import ROOT, COMPOSED, SCRATCH, HEAD, quiet, run, sha

quiet()
row=run(['git','ls-tree',HEAD,'fairscape_models']).decode().split()
assert row[:2]==['160000','commit']
commit=row[2]
source=ROOT.parent.parent/'data-sheets-schema/fairscape_models'
assert run(['git','rev-parse','HEAD'],source).decode().strip()==commit
raw=run(['git','archive',commit],source)
target=COMPOSED/'fairscape_models'
assert target.is_dir() and not list(target.iterdir())
with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
    tar.extractall(target,filter='data')
assert (target/'fairscape_models/rocrate.py').stat().st_size
record=dict(commit=commit,source=str(source),target=str(target),archive_sha256=sha(raw),
    file_count=sum(p.is_file() for p in target.rglob('*')))
(SCRATCH/'r2-fairscape-submodule.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
