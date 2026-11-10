"""PR5531 fix C, 2026-11-08: regenerate from modules; stage only in scratch.

Inputs: schema sources. Outputs: release products and four 3.2.0 hashes.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
SCHEMA = ROOT / 'src/data_sheets_schema/schema'
BIN = Path(sys.executable).parent
stage = SCRATCH / 'fix-c-generated'
stage.mkdir(exist_ok=True)
run = f'{sys.executable} {ROOT}/scripts/adhoc/pr5531_fix_a_generate.py'
def make(*args):
    subprocess.run(['make', f'RUN={run}', *args], check=True)

make('regen-all', f'SOURCE_SCHEMA_ALL={stage}/data_sheets_schema_all.yaml', f'DEST={stage}/project')
shutil.copyfile(stage / 'data_sheets_schema_all.yaml', SCHEMA / 'data_sheets_schema_all.yaml')
for path in (stage / 'project').rglob('*'):
    if path.is_file():
        relative = path.relative_to(stage / 'project')
        target = ROOT / 'project' / relative
        assert target.exists(), target
        if relative.as_posix() == 'jsonld/data_sheets_schema.jsonld':
            doc = json.loads(path.read_text())
            doc['@context'] = ['project/jsonld/data_sheets_schema.context.jsonld' if str(v).endswith('/data_sheets_schema.context.jsonld') else v for v in doc['@context']]
            target.write_text(json.dumps(doc, indent=2) + '\n')
        else:
            shutil.copyfile(path, target)
(SCHEMA / 'data_sheets_schema_core_all.yaml').unlink()
make('gen-core-schema')
make('gen-sssom-comprehensive', 'gen-sssom-uri-comprehensive')
history = SCHEMA / 'release_history.yaml'
before, current = history.read_text().split('  - version: 3.2.0\n')
for key, name in [('full_source', 'data_sheets_schema.yaml'), ('full_merged', 'data_sheets_schema_all.yaml'), ('core_source', 'data_sheets_schema_core.yaml'), ('core_merged', 'data_sheets_schema_core_all.yaml')]:
    current = re.sub(rf'({key}_sha256: )\w+', lambda m: m[1] + hashlib.sha256((SCHEMA / name).read_bytes()).hexdigest(), current)
history.write_text(before + '  - version: 3.2.0\n' + current)
make('check-digest', 'check-sync')
