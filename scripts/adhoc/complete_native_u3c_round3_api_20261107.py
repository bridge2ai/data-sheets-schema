"""Complete exact unfinished Round 3 API cases, 2026-11-07.

Inputs: full collection and interrupted API-1 XML. Outputs: disjoint selection
ledger and one bounded two-worker continuation in assigned scratch. This is
broad coverage, never a full-order claim. No tests or production code change.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u3c-r3'
roster = set(json.loads((OUT / 'rosters.json').read_text())['b-api-1'])
log = OUT / 'collect/pytest.log'
xml = OUT / 'b-api-1/pytest.xml'
selected = {line for line in log.read_text().splitlines()
            if line.split('::', 1)[0] in roster and '::' in line}
observed = {(case.attrib['classname'], case.attrib['name'])
            for case in ET.parse(xml).iter('testcase') if 'classname' in case.attrib}
def key(node):
    parts = node.split('::')
    return ('.'.join([parts[0][:-3].replace('/', '.'), *parts[1:-1]]), parts[-1])
assert selected
assert observed <= {key(node) for node in selected}
pending = sorted(node for node in selected if key(node) not in observed)
assert pending
ledger = {'selected': len(selected), 'completed': len(observed), 'pending': pending,
          'collection_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
          'prior_xml_sha256': hashlib.sha256(xml.read_bytes()).hexdigest()}
print(json.dumps(ledger, indent=2), flush=True)
if '--plan' in sys.argv:
    raise SystemExit(0)
with (OUT / 'api-continuation-selection.json').open('x') as stream:
    json.dump(ledger, stream, indent=2)
    stream.write('\n')
raise SystemExit(subprocess.call([
    sys.executable, '-S', '-P', '-B', str(ROOT / 'scripts/adhoc/run_native_u3c_round3_20261107.py'),
    '--out', str(OUT / 'b-api-unfinished'), '--workers', '2', *pending], cwd=ROOT))
