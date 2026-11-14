"""Summarize registration-builder adaptation evidence, 2026-11-13, PR 5968.

Inputs: completed scratch JUnit/logs and the synthetic chain's saved artifacts.
Outputs: summary.json and stdout, with computed hashes and exact Git checks.
No provider, native binary, reservation, capture, or external service is used.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('scratch', type=Path)
args = parser.parse_args()


def pin(path):
    raw = path.read_bytes()
    assert raw
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def git(*arguments):
    result = subprocess.run(['git', *arguments], cwd=ROOT, capture_output=True, text=True)
    return dict(command=['git', *arguments], returncode=result.returncode,
                stdout=result.stdout, stderr=result.stderr)


cohorts = {}
for name in ('focused', 'chain-canary', 'builder', 'registration'):
    path = args.scratch / (name + '.xml')
    counts = defaultdict(lambda: dict(tests=0, failures=0, errors=0, skipped=0))
    for case in ET.parse(path).iter('testcase'):
        row = counts[case.attrib['classname']]
        row['tests'] += 1
        for tag, key in [('failure', 'failures'), ('error', 'errors'), ('skipped', 'skipped')]:
            row[key] += case.find(tag) is not None
    cohorts[name] = dict(xml=pin(path), log=pin(args.scratch / (name + '.log')),
                         counts=dict(counts))
chains = [path for path in (args.scratch / 'chain-canary-tmp').glob(
    'test_full_chain_canary*/SYNTHETIC-chain/chain-progress.json')
    if not path.parent.parent.is_symlink()]
assert len(chains) == 1, chains
progress = json.loads(chains[0].read_bytes())
assert progress['status'] == 'registration_and_current_review_validated_no_reservation'
assert not progress['reservation_performed']
for item in progress['completed']:
    assert pin(Path(item['path'])) == {key: item[key] for key in ('path', 'bytes', 'sha256')}
root = chains[0].parent
assert not (root / 'native-attempt').exists()
assert not (root / 'NEVER-RESERVED-EVIDENCE').exists()
assert not (root / 'synthetic-capture').exists()
registration = json.loads((root / 'synthetic-registration.json').read_bytes())
prefixes = {}
for path in (args.scratch / 'builder-tmp').glob('test_project_prefix*/project-evidence.json'):
    if path.parent.is_symlink():
        continue
    value = json.loads(path.read_bytes())
    prefixes[value['project']] = dict(returncode=value['builder']['returncode'],
        status=value['builder']['status'], evidence=pin(path))
result = dict(cohorts=cohorts, chain_progress=pin(chains[0]),
              project_prefixes=prefixes,
              registration_kind=registration['registration']['kind'],
              registration_schema_version=registration['registration']['schema_version'],
              version3_done=False, reservation_performed=False,
              source_unchanged=git('diff', '--exit-code', '13b633df5', '--', 'src'),
              protected_unchanged=git('diff', '--exit-code', '13b633df5', '--',
                  'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json'),
              status=git('status', '--short'),
              commits=git('log', '--format=%H %s', '13b633df5..HEAD'),
              merge_conflict_evidence=pin(args.scratch / 'manifest-merge-conflicts.diff'))
raw = json.dumps(result, indent=2) + '\n'
(args.scratch / 'summary.json').write_text(raw)
print(raw, end='')
