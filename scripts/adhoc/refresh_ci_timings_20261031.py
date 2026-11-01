#!/usr/bin/env python3
# Purpose: verify and record run 41148135309 timing inputs for #5364, 2026-10-31.
# Inputs: saved run metadata/roster/XML, old/new snapshots. Outputs: scratch/evidence JSON.
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '4c07980399d47d77b64c9f2bff7a50bfc5cc6ddf'
RUN = 41148135309


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert path.stat().st_size


def prepare(source, scratch):
    metadata = json.loads((source / 'run_metadata.json').read_text())
    expected = dict(id=RUN, head_sha=COMMIT, head_branch='main', run_attempt=1,
                    status='completed', conclusion='success', event='push',
                    path='.github/workflows/main.yaml')
    assert all(metadata.get(k) == v for k, v in expected.items()), metadata
    roster = json.loads((source / 'artifacts_roster.json').read_text())
    core = [a for a in roster if re.fullmatch(r'tests-py[^/]+-shard\d+', a['name'])]
    names = [f'tests-py3.12-shard{i}' for i in range(1, 5)]
    assert sorted(a['name'] for a in core) == names
    assert {p.relative_to(source).as_posix() for p in source.rglob('pytest.xml')} == {
        f'shard{i}/pytest.xml' for i in range(1, 5)}
    assert not scratch.exists(), 'scratch must be fresh'
    artifacts = []
    for i, name in enumerate(names, 1):
        artifact = next(a for a in core if a['name'] == name)
        assert re.fullmatch(r'sha256:[0-9a-f]{64}', artifact['digest'])
        xml = source / f'shard{i}/pytest.xml'
        assert xml.stat().st_size and ET.parse(xml).find('.//testcase') is not None
        artifacts.append(dict(name=name, id=artifact['id'],
            archive_digest=artifact['digest'], archive_sha256=artifact['digest'][7:],
            archive_size=artifact['size_in_bytes'], created_at=artifact['created_at'],
            xml=[dict(path=f'{name}/pytest.xml', source_path=f'shard{i}/pytest.xml',
                      bytes=xml.stat().st_size, sha256=digest(xml))]))
    assert len({a['xml'][0]['sha256'] for a in artifacts}) == 4
    # Canary: copy one shard through the same path, verify bytes, then the other three.
    for i, artifact in enumerate(artifacts, 1):
        target = scratch / 'artifacts' / artifact['name']
        shutil.copytree(source / f'shard{i}', target)
        assert digest(target / 'pytest.xml') == artifact['xml'][0]['sha256']
    old = subprocess.check_output(['git', 'show', f'{COMMIT}:utils/ci_test_durations.json'], cwd=ROOT)
    assert old == (ROOT / 'utils/ci_test_durations.json').read_bytes()
    (scratch / 'old-timings.json').write_bytes(old)
    write(scratch / 'provenance.json', dict(metadata=metadata, core_artifacts=artifacts,
        input_metadata_sha256=digest(source / 'run_metadata.json'),
        input_roster_sha256=digest(source / 'artifacts_roster.json'),
        total_roster_artifacts=len(roster), core_artifact_count=len(core)))
    print('Verified successful main run, four unique XMLs, and byte-identical scratch copies.')


def evidence(scratch, output, comparison=None):
    provenance = json.loads((scratch / 'provenance.json').read_text())
    metadata = provenance['metadata']
    old = json.loads((scratch / 'old-timings.json').read_text())['file_seconds']
    new_path = ROOT / 'utils/ci_test_durations.json'
    new = json.loads(new_path.read_text())
    assert new['source']['run_id'] == RUN and new['source']['commit'] == COMMIT
    weights, occurrences, counts = defaultdict(Decimal), defaultdict(list), Counter()
    modules = {p[:-3].replace('/', '.'): p for p in new['file_seconds']}
    per_artifact = []
    for artifact in provenance['core_artifacts']:
        xml = artifact['xml'][0]
        path = scratch / 'artifacts' / xml['path']
        assert digest(path) == xml['sha256']
        assert dict(path=xml['path'], sha256=xml['sha256']) in new['source']['artifacts']
        rows = list(ET.parse(path).iter('testcase'))
        seconds = Decimal(0)
        for index, case in enumerate(rows):
            classname, name = case.attrib['classname'], case.attrib['name']
            candidates = [m for m in modules if classname == m or classname.startswith(m + '.')]
            assert candidates, (classname, name)
            file = modules[max(candidates, key=len)]
            duration = Decimal(case.attrib['time'])
            assert duration.is_finite() and duration >= 0
            weights[file] += duration
            seconds += duration
            for kind in ('failure', 'error', 'skipped'):
                counts[kind] += case.find(kind) is not None
            occurrences[classname, name].append(dict(file=file, classname=classname,
                name=name, seconds=str(duration), skipped=case.find('skipped') is not None,
                shard=artifact['name'], case_element_index=index))
        per_artifact.append(dict(name=artifact['name'], case_records=len(rows),
                                 total_case_seconds=str(seconds)))
    duplicates = [dict(classname=c, name=n, occurrences=rows)
                  for (c, n), rows in occurrences.items() if len(rows) > 1]
    cross = sum(len({r['shard'] for r in d['occurrences']}) > 1 for d in duplicates)
    assert counts['failure'] == counts['error'] == cross == 0
    assert {p: float(max(s, Decimal('0.001'))) for p, s in weights.items()} == new['file_seconds']
    cases = sum(len(rows) for rows in occurrences.values())
    assert cases == new['source']['test_cases']
    added = sorted(weights.keys() - old.keys())
    out = dict(purpose='Verified saved successful-run inputs and CI timing refresh for #5364',
        run_url=new['source']['url'], run_id=RUN, commit=COMMIT, run_attempt=1,
        event=metadata['event'], branch=metadata['head_branch'], status=metadata['status'],
        conclusion=metadata['conclusion'], created_at=metadata['created_at'],
        updated_at=metadata['updated_at'], workflow_path=metadata['path'], interpreter='3.12',
        core=dict(artifacts=[a['xml'][0]['path'] for a in provenance['core_artifacts']],
            case_records=cases, unique_classname_name_pairs=len(occurrences),
            mapped_files=len(weights), duplicate_id_groups=len(duplicates),
            cross_artifact_duplicate_id_groups=cross, unmapped_cases=0,
            failures=counts['failure'], errors=counts['error'], skipped=counts['skipped'],
            total_case_seconds=str(sum(weights.values())), new_weighted_files=len(added),
            new_weighted_file_seconds=str(sum(weights[p] for p in added)),
            old_weighted_files_missing_from_current=sorted(old.keys() - weights.keys())),
        core_artifacts=provenance['core_artifacts'], per_artifact=per_artifact,
        saved_metadata={k: v for k, v in provenance.items() if k not in ('metadata', 'core_artifacts')},
        duplicate_occurrences=duplicates,
        largest_files=[dict(file=p, seconds=str(weights[p]), old_seconds=old.get(p))
                       for p in sorted(weights, key=weights.get, reverse=True)[:10]],
        focus={p: dict(seconds=str(weights[p]), old_seconds=old.get(p),
            cases=sum(r['file'] == p for rows in occurrences.values() for r in rows))
            for p in ('tests/test_report_admission.py', 'tests/test_download/test_api_runner.py')},
        validation=dict(output_sha256=digest(new_path), exact_core_xml_hashes_verified=True),
        limits=['Provenance verified against supplied saved metadata, without network access.',
                'Archive digests are copied from the saved roster; ZIP archives were not supplied for independent hashing.',
                'JUnit times sum case phases across workers; scheduling estimates are not wall-time predictions.',
                'Same-artifact parameter-label collisions retain every occurrence; updater inputs were not edited.'])
    if comparison:
        compared = json.loads(comparison.read_text())
        assert compared['new_weights_sha256'] == digest(new_path)
        checked = compared['validation']
        out['validation'].update(
            comparison_path=comparison.name, comparison_sha256=digest(comparison),
            full_cases_before=checked['full_before'], full_cases_after=checked['full_after'],
            full_multiset_unchanged=checked['full_multiset_unchanged'],
            ordinary_cases=checked['ordinary_cases'], shard_union_cases=checked['union_cases'],
            shard_union_equals_ordinary_multiset=checked['shard_union_equals_ordinary_multiset'],
            per_shard_cases=[row['cases'] for row in checked['shard_checks']],
            focused_tests=checked['focused_counts'],
            focused_exit_code=checked['focused_tests']['returncode'],
            full_shard_execution=False, ci_speedup='not measured',
            observed_run_matches_old_four_shard_assignment=compared['observed_run_matches_old_four_shard_assignment'],
            observed_run_matches_ordinary_nodeid_multiset=compared['observed_run_matches_ordinary_nodeid_multiset'])
    write(output, out)
    print(json.dumps(out['core'], indent=2))
    print(json.dumps(out['focus'], indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'evidence'))
    parser.add_argument('--source', type=Path)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--comparison', type=Path)
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.source, args.scratch)
    else:
        evidence(args.scratch, args.output, args.comparison)


if __name__ == '__main__':
    main()
