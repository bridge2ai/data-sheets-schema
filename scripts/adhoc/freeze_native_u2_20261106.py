# Purpose: freeze #5508 v2 helper closure. Input: helper source commit argument.
# Outputs: v2 JSON and literal consumer pins. Date: 2026-11-06.
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
commit = subprocess.check_output(['git', 'rev-parse', sys.argv[1]], cwd=ROOT, text=True).strip()
pkg = ROOT/'src/data_sheets_schema'
manifest = json.loads((pkg/'native_controller_sources_v1.json').read_bytes())
manifest.update(version=2, source_commit=commit)
path = 'notes/matched_cborg_2026-09-13/prepare_registration_v2.py'
raw = subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=ROOT)
assert raw == (ROOT/path).read_bytes()
pin = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest()}
manifest['modules']['prepare_registration'] = pin
manifest['modules']['prepare_registration_v2'] = pin
raw = (json.dumps(manifest, indent=2)+'\n').encode()
(pkg/'native_controller_sources_v2.json').write_bytes(raw)
path = pkg/'native_attribution_controller_v2.py'
text = path.read_text().replace('V2_MANIFEST_DIGEST_PENDING', hashlib.sha256(raw).hexdigest())
path.write_text(text)
helper = 'notes/claudecode_direct/prepare_direct_v2.py'
raw = subprocess.check_output(['git', 'show', f'{commit}:{helper}'], cwd=ROOT)
assert raw == (ROOT/helper).read_bytes()
path = pkg/'native_supervisor_authority_v2.py'
path.write_text(path.read_text().replace('V2_DIRECT_DIGEST_PENDING', hashlib.sha256(raw).hexdigest()))
