"""Refresh successful ordinary shards via the unchanged updater (#6230).

2026-11-14. Inputs: run 43536007079 XML, lead job metadata, current durations.
Outputs: lossless compressed XML fixtures, filtered scratch XML, candidate,
provenance summary. Run --canary first; inspect it before --apply.
"""
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.pytest_shard import DEDICATED_CASE_LANES
from utils.update_ci_shard_timings import build

RUN = 43536007079
COMMIT = '6ed891e845c1a46282338794dadb342a6fa6f261'
KEY = 'successful_ordinary_refresh_43536007079_20261114'
SELECTED = [2, 3, 4, 5, 7, 9, 11, 12]
FIXTURES = ROOT / 'tests/fixtures/ci_timings/43536007079'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('metadata', type=Path)
    parser.add_argument('scratch', type=Path)
    parser.add_argument('--canary', action='store_true')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    assert not (args.canary and args.apply)
    metadata_raw = args.metadata.read_bytes()
    metadata = json.loads(metadata_raw)
    assert metadata['run_id'] == str(RUN) and metadata['head'] == COMMIT
    jobs = {int(j['name'].rsplit(' ', 1)[1]): j for j in metadata['jobs']
            if j['name'].startswith('Python 3.12 / shard ')}
    assert sorted(n for n, j in jobs.items() if j['conclusion'] == 'success') == SELECTED
    FIXTURES.mkdir(parents=True, exist_ok=True)
    staging = args.scratch / 'successful-ordinary-inputs'
    staging.mkdir(exist_ok=True)
    modules = {p[:-3].replace('/', '.'): p for p in subprocess.check_output(
        ['git', 'ls-files', 'tests'], cwd=ROOT, text=True).splitlines() if p.endswith('.py')}
    dedicated = set(DEDICATED_CASE_LANES.values())
    originals = []
    first = FIXTURES / f'shard{SELECTED[0]}.xml.gz'
    if not args.canary:
        canary = json.loads((args.scratch / 'timing-canary.json').read_text())
        assert canary['fixture_sha256'] == sha(first.read_bytes())
        assert canary['raw_sha256'] == sha(gzip.decompress(first.read_bytes()))
    for n in SELECTED[:1] if args.canary else SELECTED:
        relative = Path(f'tests-py3.12-shard{n}/pytest.xml')
        raw = (args.artifacts / relative).read_bytes()
        tree = ET.fromstring(raw)
        cases = list(tree.iter('testcase'))
        assert cases and all(c.find('failure') is None and c.find('error') is None for c in cases)
        fixture = FIXTURES / f'shard{n}.xml.gz'
        compressed = gzip.compress(raw, mtime=0)
        if fixture.exists():
            assert gzip.decompress(fixture.read_bytes()) == raw
        else:
            fixture.write_bytes(compressed)
        assert fixture.stat().st_size and gzip.decompress(fixture.read_bytes()) == raw
        kept, excluded = [], []
        for case in cases:
            cls = case.attrib['classname']
            module = max((m for m in modules if cls == m or cls.startswith(m + '.')), key=len)
            node = modules[module] + '::' + cls[len(module):].lstrip('.').replace('.', '::')
            node += ('::' if cls != module else '') + case.attrib['name']
            if node in dedicated:
                excluded.append(node)
            else:
                kept.append(case)
        filtered = ET.Element('testsuite', tests=str(len(kept)))
        filtered.extend(kept)
        target = staging / relative
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(ET.tostring(filtered, encoding='utf-8', xml_declaration=True))
        assert target.stat().st_size and len(list(ET.parse(target).iter('testcase'))) == len(kept)
        originals.append(dict(shard=n, job_id=jobs[n]['id'], conclusion='success',
            original_path=str(relative), raw_sha256=sha(raw),
            fixture=str(fixture.relative_to(ROOT)), fixture_sha256=sha(fixture.read_bytes()),
            original_cases=len(cases), retained_cases=len(kept), excluded_nodes=excluded,
            filtered_sha256=sha(target.read_bytes())))
    if args.canary:
        measured = build(staging, ROOT, RUN, COMMIT)
        assert measured['source']['test_cases'] == originals[0]['retained_cases']
        originals[0]['updater_files'] = len(measured['file_seconds'])
        originals[0]['updater_test_cases'] = measured['source']['test_cases']
        (args.scratch / 'timing-canary.json').write_text(json.dumps(originals[0], indent=2) + '\n')
        print(json.dumps(originals[0], indent=2))
        return
    # No relaxation or exception handling around the original updater.
    measured = build(staging, ROOT, RUN, COMMIT)
    path = ROOT / 'utils/ci_test_durations.json'
    old_raw = path.read_bytes()
    old = json.loads(old_raw)
    assert KEY not in old['source'], 'already applied'
    new = deepcopy(old)
    new['source'][KEY] = dict(
        kind='Partial successful ordinary-shard JUnit refresh; overall run failed',
        measurement=measured['source'], selected_shards=SELECTED,
        excluded_shards={'1': 'failure', '6': 'cancelled; no JUnit', '8': 'failure', '10': 'failure'},
        originals=originals, dedicated_nodes=sorted(dedicated),
        metadata_sha256=sha(metadata_raw), previous_snapshot_sha256=sha(old_raw),
        previous_file_seconds=old['file_seconds'], file_seconds=measured['file_seconds'],
        method=measured['method'],
        limits='Original XML retained losslessly. Dedicated cases removed before updater. Unmeasured files and all historical provenance retained. No wall-time or successful-run claim.')
    new['file_seconds'].update(measured['file_seconds'])
    assert all(new[k] == v for k, v in old.items() if k not in ('source', 'file_seconds'))
    assert all(new['source'][k] == v for k, v in old['source'].items())
    summary = dict(run_id=RUN, selected_shards=SELECTED, artifacts=len(originals),
        test_cases=measured['source']['test_cases'], excluded_cases=sum(len(r['excluded_nodes']) for r in originals),
        measured_files=len(measured['file_seconds']),
        retained_unmeasured_files=len(set(old['file_seconds']) - set(measured['file_seconds'])),
        added_files=len(set(measured['file_seconds']) - set(old['file_seconds'])),
        fixture_bytes=sum((ROOT / r['fixture']).stat().st_size for r in originals))
    candidate = args.scratch / 'timings-candidate.json'
    candidate.write_text(json.dumps(new, indent=2) + '\n')
    summary['candidate_sha256'] = sha(candidate.read_bytes())
    (args.scratch / 'timings-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    if args.apply:
        path.write_bytes(candidate.read_bytes())
        assert path.read_bytes() == candidate.read_bytes()
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
