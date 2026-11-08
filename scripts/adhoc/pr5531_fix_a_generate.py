"""PR5531 regenerate release products with all intermediate files in scratch.

Inputs: current schema modules; outputs: generated products and 3.2.0 release
hashes, or make's test-schema products in scratch. 2026-11-08.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
SCHEMA = ROOT / 'src/data_sheets_schema/schema'
BIN = Path(sys.executable).parent

def run(name, *args):
    subprocess.run([str(BIN / name), *map(str, args)], check=True)

if len(sys.argv) > 1:
    # RUN override for the unchanged make test-schema recipe; relocate its
    # hard-coded temporary output, without changing generator arguments.
    args = sys.argv[2:]
    args = [str(SCRATCH / 'test-schema') if a == 'tmp' else a for a in args]
    run(sys.argv[1], *args)
else:
    generated = SCRATCH / 'generated'
    generated.mkdir(parents=True, exist_ok=True)
    for stem in ('data_sheets_schema', 'data_sheets_schema_core'):
        output = generated / (stem + '_all.yaml')
        run('gen-linkml', '-o', output, '-f', 'yaml', (SCHEMA / (stem + '.yaml')).relative_to(ROOT))
        raw = output.read_bytes()
        if stem == 'data_sheets_schema':
            raw = b'---\n' + raw
        (SCHEMA / output.name).write_bytes(raw)
    run('gen-project', '-I', 'python', '-I', 'jsonschema', '-I', 'jsonld', '-I', 'owl',
        '-d', generated / 'project', (SCHEMA / 'data_sheets_schema.yaml').relative_to(ROOT))
    for path in (generated / 'project').rglob('*'):
        if path.is_file():
            relative = path.relative_to(generated / 'project')
            target = (ROOT / 'src/data_sheets_schema/datamodel' / relative.name
                      if path.suffix == '.py' else ROOT / 'project' / relative)
            assert target.exists(), target
            if relative.as_posix() == 'jsonld/data_sheets_schema.jsonld':
                # Relocate the generated context reference along with its file.
                doc = json.loads(path.read_text())
                staged = (generated / 'project/jsonld/data_sheets_schema.context.jsonld').as_uri()
                assert staged in doc['@context']
                doc['@context'] = ['project/jsonld/data_sheets_schema.context.jsonld' if value == staged else value
                                  for value in doc['@context']]
                target.write_text(json.dumps(doc, indent=2) + '\n')
            else:
                shutil.copyfile(path, target)
    history = SCHEMA / 'release_history.yaml'
    text = history.read_text()
    before, current = text.split('  - version: 3.2.0\n')
    for key, name in [('full_source', 'data_sheets_schema.yaml'),
                      ('full_merged', 'data_sheets_schema_all.yaml'),
                      ('core_source', 'data_sheets_schema_core.yaml'),
                      ('core_merged', 'data_sheets_schema_core_all.yaml')]:
        import re
        current = re.sub(rf'({key}_sha256: )\w+',
                         lambda m: m[1] + hashlib.sha256((SCHEMA / name).read_bytes()).hexdigest(), current)
    history.write_text(before + '  - version: 3.2.0\n' + current)
