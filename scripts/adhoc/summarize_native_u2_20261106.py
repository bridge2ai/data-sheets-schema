# Purpose: summarize #5508 validation without rerunning tests.
# Inputs: scratch XML/JSON and local Git sources. Output: scratch summary.json.
# Date: 2026-11-06.
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent/'scratch-native-u2'
BASE = '8bc90e93d736d464f98e9eedffee45f0ad8e5d3f'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
summary = {'head': git('rev-parse', 'HEAD').decode().strip(), 'runs': {}}
for path in sorted(OUT.glob('*.execution.json')):
    row = json.loads(path.read_bytes())
    xml = path.with_name(path.name.replace('.execution.json', '.xml'))
    if xml.exists():
        cases = ET.parse(xml).getroot().findall('.//testcase')
        row['counts'] = dict(Counter('failed' if c.find('failure') is not None else
            'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None
            else 'passed' for c in cases))
        row['failed_nodes'] = [c.attrib.get('classname', '')+'::'+c.attrib['name'] for c in cases
                               if c.find('failure') is not None or c.find('error') is not None]
    summary['runs'][path.name.removesuffix('.execution.json')] = row
v1 = ['src/data_sheets_schema/native_controller_sources_v1.json',
      'src/data_sheets_schema/native_attribution_controller.py',
      'src/data_sheets_schema/native_attribution_registration.py',
      'src/data_sheets_schema/native_supervisor_authority.py',
      'notes/matched_cborg_2026-09-13/prepare_registration.py',
      'notes/claudecode_direct/prepare_direct.py']
summary['unchanged_v1'] = {}
for name in v1:
    raw = (ROOT/name).read_bytes()
    assert raw == git('show', BASE+':'+name), name
    summary['unchanged_v1'][name] = sha(raw)
manifest = json.loads((ROOT/'src/data_sheets_schema/native_controller_sources_v2.json').read_bytes())
for name, pin in manifest['modules'].items():
    assert sha((ROOT/pin['path']).read_bytes()) == pin['sha256'], name
    assert sha(git('show', manifest['source_commit']+':'+pin['path'])) == pin['sha256'], name
summary['v2_manifest'] = {'source_commit': manifest['source_commit'], 'sha256': sha(
    (ROOT/'src/data_sheets_schema/native_controller_sources_v2.json').read_bytes())}
summary['changed_paths'] = git('diff', '--name-only', BASE, 'HEAD').decode().splitlines()
assert not any(p.startswith('data/') or p.endswith(('shared_generation.py', 'canonical_hashes.yaml'))
               for p in summary['changed_paths'])
if (OUT/'scan.json').exists() and (OUT/'baseline-scan.json').exists():
    before, after = [json.loads((OUT/p).read_bytes()) for p in ('baseline-scan.json', 'scan.json')]
    summary['scanner_keys'] = list(after)
    # Store full scanner objects in separate retained files, never lose fields here.
    for key in ('violations', 'listed_not_derived', 'derived_not_listed'):
        if key in before and key in after:
            summary['scanner_'+key] = {'equal': before[key] == after[key],
                                      'before': before[key], 'after': after[key]}
(OUT/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps({'head': summary['head'], 'counts': {k:v.get('counts', {}) for k,v in summary['runs'].items()}}, indent=2))
