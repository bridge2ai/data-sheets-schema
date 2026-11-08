"""U1 #4354 2026-11-06: load exact M7 API/schema modules for parity only.
Inputs: local Git M7 blobs. Output: imported modules, no source-tree edits.
Registration/source hashes still reflect working files; instruction comparison
uses the same fixed fixture paths and records this baseline limitation.
"""
from pathlib import Path
import importlib.util
import subprocess
import sys
import data_sheets_schema
ROOT = Path(__file__).resolve().parents[2]
for leaf in ('schema_snapshot', 'api_runner'):
    name = 'data_sheets_schema.' + leaf
    source = ROOT / ('src/data_sheets_schema/' + leaf + '.py')
    raw = subprocess.check_output(['git', 'show', '8bc90e93d:' + str(source.relative_to(ROOT))], cwd=ROOT)
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    setattr(data_sheets_schema, leaf, module)
    exec(compile(raw, str(source) + ' [M7 baseline]', 'exec'), module.__dict__)
