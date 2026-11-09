"""U3-F evidence reconciliation, 2026-11-09.

Inputs: retained scanner JSON, sandboxed XML/outcomes and raw parity artifacts.
Outputs: exact findings comparison, per-node ledger, hashes and parity evidence
under the assigned scratch root. Local offline handoff, no remote operations.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u1u3'
OUT = SCRATCH / 'u3f'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')

def scans(baseline, candidate):
    before = json.loads((SCRATCH / 'baseline-scanner.json').read_bytes())
    after = json.loads((OUT / baseline).read_bytes())
    combined = json.loads((OUT / candidate).read_bytes())
    assert all(isinstance(row.get('hits'), list) for row in (before, after, combined))
    old = before['violations']
    assert len(old) == 9 and all(row['category'] == 'gc_project' for row in old)
    results = []
    for label, document in [('saved_main_after_instrument_change', after), ('composed_candidate', combined)]:
        actual = document['violations']
        comparisons = [dict(saved=row, exact_matches=[n for n in actual if n == row]) for row in old]
        extras = [row for row in actual if row not in old]
        results.append(dict(basis=label, findings=len(document['hits']), violations=len(actual),
            finding_by_finding=comparisons, extra_violations=extras,
            exact_nine_violation_parity=actual == old))
    save('scanner-comparison.json', dict(before_tool='U3-E retained unchanged scanner',
        before_sha256=sha((SCRATCH / 'baseline-scanner.json').read_bytes()),
        after_sha256=sha((OUT / baseline).read_bytes()), candidate_sha256=sha((OUT / candidate).read_bytes()),
        results=results))
    print(json.dumps([{k:v for k,v in row.items() if k != 'finding_by_finding'} for row in results]))

def parity(label):
    baseline = {p.name:p for folder in ('parity2-canary-baseline', 'parity2-rest-baseline')
                for p in (SCRATCH / folder / 'parity').glob('*.txt')}
    actual = {p.name:p for p in (OUT / label / 'parity').glob('*.txt')}
    assert len(baseline) == 14 and set(actual) == set(baseline)
    result = [dict(name=name, baseline=str(path), candidate=str(actual[name]),
        baseline_sha256=sha(path.read_bytes()), candidate_sha256=sha(actual[name].read_bytes()),
        bytes=len(actual[name].read_bytes()), equal=path.read_bytes() == actual[name].read_bytes())
        for name,path in sorted(baseline.items())]
    save(label+'-comparison.json', result)
    print(json.dumps(dict(label=label, equal=sum(row['equal'] for row in result), total=len(result))))

def packets(manifest_path):
    if os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'):
        raise RuntimeError('quiet window is active')
    manifest = json.loads(Path(manifest_path).read_bytes())
    tree, bundle = Path(manifest['tree']), Path(manifest['owner_bundle'])
    paths = [str(bundle / (row['name']+'.patch')) for row in manifest['packets']]
    env = {**os.environ, 'GIT_NO_LAZY_FETCH':'1', 'GIT_CONFIG_GLOBAL':'/dev/null', 'GIT_CONFIG_SYSTEM':'/dev/null'}
    base = ['git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null', '-c', 'protocol.allow=never', 'apply', '--check']
    subprocess.run(base+paths, cwd=ROOT, env=env, check=True, timeout=60)
    subprocess.run(base+['--reverse']+paths, cwd=tree, env=env, check=True, timeout=60)
    for row in manifest['packets']:
        assert sha((ROOT / row['target']).read_bytes()) == row['preimage_sha256']
        assert sha((tree / row['target']).read_bytes()) == row['postimage_sha256']
        assert sha((bundle / (row['name']+'.patch')).read_bytes()) == row['patch_sha256']
        assert row['changed_from_u1'] == (row['name'] == 'run_spec_boundary_contracts')
    result = dict(manifest=str(Path(manifest_path).resolve()), owner_bundle=str(bundle),
        forward_check=True, reverse_check=True, packet_hashes_verified=True,
        worktree_packets_installed=False, packets=manifest['packets'])
    save('owner-packet-verification.json', result)
    (SCRATCH / 'owner-packets/u3f-current.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(owner_bundle=str(bundle), verified_packets=len(paths))))

def summary():
    runs, ledger, hashes = [], [], {}
    for path in sorted(OUT.glob('*/outcome.json')):
        folder = path.parent
        outcome = json.loads(path.read_bytes())
        plan = json.loads((folder / 'plan.json').read_bytes())
        counts = dict(passed=0, failed=0, error=0, skipped=0)
        xml = folder / 'pytest.xml'
        if xml.is_file():
            for case in ET.parse(xml).iter('testcase'):
                status = 'passed'
                for tag, name in [('failure', 'failed'), ('error', 'error'), ('skipped', 'skipped')]:
                    child = case.find(tag)
                    if child is not None:
                        status = name
                        break
                counts[status] += 1
                parts = case.attrib.get('classname','').split('.')
                cut = next((i for i, part in enumerate(parts) if part[:1].isupper()), len(parts))
                node = '/'.join(parts[:cut])+'.py::'+'::'.join([*parts[cut:], case.attrib['name']])
                ledger.append(dict(run=folder.name, node=node, status=status,
                    detail='' if status == 'passed' else ET.tostring(child, encoding='unicode')))
        runs.append(dict(run=folder.name, source_commit=plan['source_commit'], source_root=plan['source_root'],
            deadline_seconds=plan['deadline_seconds'], workers=plan['workers'], counts=counts, **outcome))
        for name in ('outcome.json', 'pytest.xml', 'pytest.log', 'source-stability.json', 'plan.json',
                     'origins-before.json', 'origins-after.json', 'host-load.json'):
            artifact = folder / name
            if artifact.is_file():
                hashes[str(artifact)] = sha(artifact.read_bytes())
    protected = []
    for relative in ('src/data_sheets_schema/api_runner.py', 'src/data_sheets_schema/shared_generation.py',
                     'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json',
                     'tests/utils/run_spec_boundaries.py'):
        original = subprocess.check_output(['git', 'show', '49a5f2b74:'+relative], cwd=ROOT)
        current = (ROOT / relative).read_bytes()
        protected.append(dict(path=relative, before=sha(original), after=sha(current), unchanged=original == current))
    save('validation-summary.json', runs)
    save('exact-node-ledger.json', ledger)
    save('evidence-hashes.json', hashes)
    save('protected-files.json', protected)
    print(json.dumps([dict(run=row['run'], counts=row['counts'], seconds=row['seconds'], cleanup=row['cleanup_verified']) for row in runs], indent=2))
    assert all(row['unchanged'] for row in protected)

if __name__ == '__main__':
    if sys.argv[1] == 'scans':
        scans(*sys.argv[2:])
    elif sys.argv[1] == 'parity':
        parity(sys.argv[2])
    elif sys.argv[1] == 'summary':
        summary()
    elif sys.argv[1] == 'packets':
        packets(sys.argv[2])
