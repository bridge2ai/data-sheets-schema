"""PR #5543 / D119 evidence, 2026-11-08.
Inputs: root drafts and ATTIC twins, generated TSVs. Outputs: scratch manifests.
Modes audit/snapshot/compare; no deletion, network or provider execution.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-d100-cleanup'
if (ROOT.parent / 'plans/native_quiet_window.lock').exists():
    raise SystemExit('Quiet window active')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

mode = sys.argv[1]
if mode == 'audit':
    drafts = sorted(ROOT.glob('D4D_*.yaml'))
    assert len(drafts) == 12
    rows = []
    for draft in drafts:
        twin = ROOT / 'data/ATTIC/root_schema_drafts_2026-08-08' / draft.name
        assert not draft.is_symlink() and not twin.is_symlink()
        assert digest(draft) == digest(twin), draft.name
        rows.append(dict(path=draft.name, sha256=digest(draft),
                         attic=str(twin.relative_to(ROOT)), bytes=draft.stat().st_size))
    (SCRATCH / 'pr5543-draft-twins.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(rows, indent=2))
else:
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / 'data/schema_stats').iterdir()) if p.is_file()}
    manifest = SCRATCH / 'pr5543-stats-hashes.json'
    if mode == 'snapshot':
        manifest.write_text(json.dumps(hashes, indent=2) + '\n')
    elif mode == 'compare':
        assert hashes == json.loads(manifest.read_text()), 'Export bytes changed'
        print(f'All {len(hashes)} statistics files byte-identical across working directories')
    else:
        raise SystemExit('Unknown mode')
