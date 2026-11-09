"""Read-only PR5531 review checks; save evidence in scratch (2026-11-08).

Inputs: reviewed 5d6dd97c2 baseline and current files. Outputs: verification
JSON with OWL semantic equality, historical-entry preservation and byte deltas.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import yaml
from rdflib import Graph, Literal
from rdflib.compare import isomorphic

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-pr5531-fix'
BASE = '5d6dd97c2'

def original(name):
    return subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=ROOT)

def preserved_entries(name, key):
    before = yaml.safe_load(original(name))
    after = yaml.safe_load((ROOT / name).read_bytes())
    if key == 'digests':
        assert all(after[key][k] == v for k, v in before[key].items())
    else:
        assert before[key][:-1] == after[key][:-1]

def main():
    owl = 'project/owl/data_sheets_schema.owl.ttl'
    expected = Graph().parse(data=original(owl), format='turtle')
    replacements = 0
    for s, p, o in list(expected):
        if isinstance(o, Literal) and str(o) == 'health_medical_biomedical_research, no_commercial_use':
            expected.remove((s, p, o))
            expected.add((s, p, Literal('health_medical_biomedical_research', lang=o.language, datatype=o.datatype)))
            replacements += 1
    assert replacements > 0
    assert isomorphic(expected, Graph().parse(ROOT / owl, format='turtle'))
    preserved_entries('src/data_sheets_schema/schema/digest_inventory.yaml', 'digests')
    history_path = 'src/data_sheets_schema/schema/release_history.yaml'
    before = yaml.safe_load(original(history_path))
    after = yaml.safe_load((ROOT / history_path).read_bytes())
    # Preserve every historical release irrespective of the history's envelope.
    for key, value in before.items():
        if isinstance(value, list):
            assert value[:-1] == after[key][:-1]
    protected = ['src/data_sheets_schema/shared_generation.py',
                 'src/download/prompts/canonical_hashes.yaml',
                 'src/data_sheets_schema/schema/D4D_Base_import.yaml']
    for path in protected:
        assert (ROOT / path).read_bytes() == original(path)
    changed = subprocess.check_output(['git', 'diff', BASE, '--name-only'], cwd=ROOT, text=True).splitlines()
    assert not any('sidecar' in p.lower() or 'd76' in p.lower() or p.startswith('.github/') for p in changed)
    measurements = {name: json.loads((SCRATCH / f'bytes-{name}/measurements.json').read_text())
                    for name in ('main', 'before', 'after')}
    deltas = {key: measurements['after'][key]['bytes'] - row['bytes']
              for key, row in measurements['before'].items()}
    tests = {}
    for path in sorted(SCRATCH.glob('*.xml')):
        suites = ET.parse(path).getroot().iter('testsuite')
        tests[path.name] = [s.attrib for s in suites]
    result = dict(python=sys.version, executable=sys.executable,
        packages={name: importlib.metadata.version(name) for name in
                  ('pytest', 'pytest-xdist', 'linkml', 'linkml-runtime', 'rdflib')},
        owl_expected_literal_replacements=replacements, owl_semantics_match=True,
        historical_entries_preserved=True, protected_and_prefix_files_unchanged=True,
        changed_tracked_files=changed, measurements=measurements, fix_a_byte_deltas=deltas,
        tests=tests)
    (SCRATCH / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
