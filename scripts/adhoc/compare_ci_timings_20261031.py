#!/usr/bin/env python3
# Purpose: reconstruct main/#5364 assignments and verify coverage, 2026-10-31.
# Inputs: actual collections, old/new weights, saved v5 file list. Output: JSON/Markdown.
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from utils.pytest_shard import _estimates, balanced_files, partition_lanes, read_weights

COMMIT = '4c07980399d47d77b64c9f2bff7a50bfc5cc6ddf'
FOCUS = ('tests/test_report_admission.py', 'tests/test_download/test_api_runner.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_check(scratch, name):
    directory = scratch / name
    execution = json.loads((directory / 'execution.json').read_text())
    assert execution['returncode'] == 0, (name, execution['returncode'])
    assert '--collect-only' in execution['args']
    nodes = json.loads((directory / 'nodeids.json').read_text())
    assert nodes and all(n.startswith('tests/') and '::' in n for n in nodes)
    return nodes, dict(execution=execution, nodeids_sha256=sha(directory / 'nodeids.json'),
                       log_sha256=sha(scratch / f'{name}.log'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    assert path.stat().st_size


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--v5-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--validate', action='store_true')
    args = parser.parse_args()
    nodes, baseline = read_check(args.scratch, 'main-before')
    assert baseline['execution']['head'] == COMMIT
    ordinary = partition_lanes(nodes)['ordinary']
    paths = {n.split('::', 1)[0] for n in ordinary}
    v5 = json.loads(args.v5_source.read_text())
    added = set(v5['added_files'])
    assert len(added) == len(v5['added_files']) == 10
    assert not paths & added
    algorithm = ROOT / 'utils/pytest_shard.py'
    assert subprocess.check_output(['git', 'show', f'{COMMIT}:utils/pytest_shard.py'], cwd=ROOT) == algorithm.read_bytes()
    assert not subprocess.check_output(['git', 'diff', COMMIT, '--', 'tests',
        'utils/pytest_shard.py', '.github/workflows/main.yaml'], cwd=ROOT)
    old_path = args.scratch / 'old-timings.json'
    new_path = ROOT / 'utils/ci_test_durations.json'
    assert baseline['execution']['timings_sha256'] == sha(old_path)
    old, new = read_weights(old_path), read_weights(new_path)
    assert not added & (old.keys() | new.keys()), 'v5 files must use fallback'
    # Cross-check the reconstructed old main/4 layout against actual run ownership.
    recorded_nodes = Counter()
    observed_files = set()
    old_main = balanced_files(paths, 4, old)
    modules = {p[:-3].replace('/', '.'): p for p in paths}
    for i in range(1, 5):
        xml = args.scratch / 'artifacts' / f'tests-py3.12-shard{i}/pytest.xml'
        for case in ET.parse(xml).iter('testcase'):
            classname = case.attrib['classname']
            module = max((m for m in modules if classname == m or classname.startswith(m + '.')), key=len)
            path = modules[module]
            assert old_main[path] == i, (path, i, old_main[path])
            observed_files.add(path)
            # Class suffixes become pytest node-ID segments; keep parameter labels intact.
            suffix = classname[len(module):].lstrip('.').replace('.', '::')
            node = path + '::' + (suffix + '::' if suffix else '') + case.attrib['name']
            recorded_nodes[node] += 1
    assert observed_files == paths
    assert recorded_nodes == Counter(ordinary), 'saved run cases differ from main ordinary collection'
    result = dict(main_commit=COMMIT, full_cases=len(nodes), ordinary_cases=len(ordinary),
        main_files=sorted(paths), v5_added_files=sorted(added),
        source_v5_comparison_sha256=sha(args.v5_source), algorithm_sha256=sha(algorithm),
        old_weights_sha256=sha(old_path), new_weights_sha256=sha(new_path),
        observed_run_matches_old_four_shard_assignment=True,
        observed_run_matches_ordinary_nodeid_multiset=True,
        historical_v5_main=v5['main'], historical_v5_baseline_files=v5['baseline_files'],
        baseline_collection=baseline, scenarios=[],
        method='Use partition_lanes on actual main collection, then balanced_files and _estimates. '
               'The v5 scenario adds only ten file paths; it does not claim a v5 case count. '
               'Both current-weight totals and re-costing each layout with refreshed weights are reported.',
        limits=['Scheduling estimates, not wall-time predictions or proof of resolving the 45-minute timeout.',
                'New v5 files receive median fallback; their runtimes and changed cases are unmeasured.',
                'Ordinary lane excludes the four dedicated API cases before file assignment.'])
    lines = ['# Offline CI scheduling estimates for #5364', '',
        'Run 41148135309 at main `4c0798039`. Scheduling estimates in summed',
        'case-seconds, **not wall-time predictions**. Refreshed-cost columns value',
        'both layouts using the same new measurements, exposing stale-weight imbalance.', '',
        '| Collection | Shards | Weights | Own-weight estimates by shard | Refreshed-cost estimates by shard | Report admission | API runner |',
        '| --- | ---: | --- | --- | --- | ---: | ---: |']
    for label, collection in (('main', paths), ('main + v5 ten files', paths | added)):
        refreshed = _estimates(collection, new)
        for total in (4, 6):
            for weight_label, weights in (('old', old), ('new', new)):
                assignment = balanced_files(collection, total, weights)
                estimates = _estimates(collection, weights)
                rows = [dict(shard=i, files=sum(owner == i for owner in assignment.values()),
                    estimated_case_seconds=round(sum(estimates[p] for p in sorted(collection) if assignment[p] == i), 3),
                    refreshed_case_seconds=round(sum(refreshed[p] for p in sorted(collection) if assignment[p] == i), 3))
                    for i in range(1, total + 1)]
                focus = {p: dict(shard=assignment[p], recorded_weight=weights.get(p),
                                 effective_estimate=estimates[p]) for p in FOCUS}
                scenario = dict(collection=label, shard_count=total, weights=weight_label,
                    files=len(collection), untimed_files=sorted(collection - weights.keys()),
                    shards=rows, focus=focus,
                    assignment_sha256=hashlib.sha256(json.dumps(assignment, sort_keys=True).encode()).hexdigest())
                result['scenarios'].append(scenario)
                values = lambda key: ', '.join(f"{r[key]:,.1f}" for r in rows)
                lines.append(f'| {label} | {total} | {weight_label} | {values("estimated_case_seconds")} | '
                             f'{values("refreshed_case_seconds")} | {focus[FOCUS[0]]["shard"]} | {focus[FOCUS[1]]["shard"]} |')
    lines += ['', f'This main collection has {len(paths)} ordinary files; the earlier v5 investigation',
              f'used {v5["baseline_files"]} files at `{v5["main"]}`. Its shard-2-to-6 report-admission',
              'movement therefore does not describe this newer pinned collection. The old',
              'four-shard reconstruction exactly matches all four supplied XMLs, including',
              'the ordinary node-ID multiset. All ten new v5 files use fallback weights.']
    if args.validate:
        after, after_meta = read_check(args.scratch, 'main-after')
        assert Counter(after) == Counter(nodes), 'main collection multiset changed'
        expected = Counter(ordinary)
        actual = Counter()
        shard_checks = []
        assignment = balanced_files(paths, 4, new)
        for i in range(1, 5):
            selected, meta = read_check(args.scratch, f'shard{i}')
            assert f'--ci-shard={i}/4' in meta['execution']['args']
            assert '--ci-lane=ordinary' in meta['execution']['args']
            assert '--ci-shard-timings=utils/ci_test_durations.json' in meta['execution']['args']
            assert meta['execution']['timings_sha256'] == sha(new_path)
            assert Counter(selected) == Counter(n for n in ordinary if assignment[n.split('::', 1)[0]] == i)
            actual.update(selected)
            shard_checks.append(dict(shard=i, cases=len(selected), **meta))
        assert actual == expected, 'four-shard union differs from full ordinary multiset'
        assert all(after_meta['execution'][k] == baseline['execution'][k]
                   for k in ('head', 'python', 'dependencies', 'lock_sha256'))
        focused = json.loads((args.scratch / 'focused/execution.json').read_text())
        canary = json.loads((args.scratch / 'focused-canary/execution.json').read_text())
        assert canary['returncode'] == 0
        canary_xmls = sorted((args.scratch / 'focused-canary').rglob('*.xml'))
        assert len(canary_xmls) == 5 and all(p.stat().st_size for p in canary_xmls)
        focused_xml = args.scratch / 'focused.xml'
        focused_rows = list(ET.parse(focused_xml).iter('testcase'))
        focused_counts = dict(cases=len(focused_rows),
            failed=sum(c.find('failure') is not None for c in focused_rows),
            errors=sum(c.find('error') is not None for c in focused_rows),
            skipped=sum(c.find('skipped') is not None for c in focused_rows))
        focused_counts['passed'] = focused_counts['cases'] - sum(
            focused_counts[k] for k in ('failed', 'errors', 'skipped'))
        result['validation'] = dict(full_before=len(nodes), full_after=len(after),
            full_multiset_unchanged=True, ordinary_cases=len(ordinary),
            union_cases=sum(actual.values()), shard_union_equals_ordinary_multiset=True,
            duplicate_nodeid_groups=sum(c > 1 for c in expected.values()),
            missing_cases=sum((expected - actual).values()), extra_cases=sum((actual - expected).values()),
            main_after=after_meta, shard_checks=shard_checks, focused_tests=focused,
            focused_counts=focused_counts, focused_junit_sha256=sha(focused_xml),
            focused_canary=dict(returncode=canary['returncode'], args=canary['args'],
                seconds=canary['seconds'],
                artifacts=[dict(path=p.relative_to(args.scratch).as_posix(), sha256=sha(p)) for p in canary_xmls],
                proved='Nested four-worker pytest runs persist all four shard XMLs and preserve the complete 64-case synthetic multiset.'),
            focused_log_sha256=sha(args.scratch / 'focused.log'), full_shard_execution=False)
        if focused['returncode']:
            failures = [dict(name=c.attrib['name'], text=c.find('failure').text)
                        for c in focused_rows if c.find('failure') is not None]
            assert [f['name'] for f in failures] == [
                'test_one_long_case_starts_before_a_file_with_many_short_cases']
            assert focused['returncode'] == 1 and focused_counts['errors'] == 0
            root_canary = json.loads((args.scratch / 'rootdir-canary/execution.json').read_text())
            assert root_canary['returncode'] == 0 and root_canary['pytest_addopts'] == '--rootdir=.'
            result['validation']['focused_failure_diagnostic'] = dict(failures=failures,
                isolated_rerun=root_canary,
                resolution='Checkout-contained fixture inherited the repository root; PYTEST_ADDOPTS=--rootdir=. '
                           'makes each subprocess use its cwd. Only the affected case was rerun and passed; '
                           'the original focused run remains recorded.',
                rootdir_canary_log_sha256=sha(args.scratch / 'rootdir-canary.log'))
        lines += ['', f'Collection: {len(nodes):,} before and after; identical node-ID multisets.',
                  f'Ordinary union: {sum(actual.values()):,} cases across four shards; no lost or extra occurrences.',
                  f'Focused pytest: {focused_counts["passed"]} passed, {focused_counts["failed"]} failed, '
                  f'{focused_counts["errors"]} errors and {focused_counts["skipped"]} skipped '
                  f'(exit {focused["returncode"]}). Full shard execution was not run.', '',
                  'The first nested four-worker canary passed and persisted all four shard XMLs,',
                  'preserving its complete 64-case synthetic multiset before the full focused run.', '',
                  'Local checks use the existing macOS Python 3.12 dependency environment,',
                  'with versions recorded in `shard-comparison.json`; this is not Linux CI.',
                  'Scratch XMLs, raw logs and node IDs remain uncommitted in `.ci-timing-41148135309/`.']
        if focused['returncode']:
            lines += ['', 'The focused run had one fixture-path assertion failure: its nested',
                'pytest inherited the repository root because all temporary files must stay',
                'inside this checkout. The isolated case passed with `PYTEST_ADDOPTS=--rootdir=.`,',
                'which makes each subprocess use its own cwd. The original focused-run failure',
                'remains recorded; the complete suite was not rerun with that harness setting.',
                'The ordinary shard collections use the unchanged CI options without that setting.',
                'Initial failure details and hashes are retained in `shard-comparison.json`.']
    # Retain one full dependency manifest and hash repeated environment records.
    result['dependencies'] = baseline['execution']['dependencies']
    executions = [baseline['execution']]
    if args.validate:
        executions += [after_meta['execution'], focused, *(r['execution'] for r in shard_checks)]
        if focused['returncode']:
            executions.append(root_canary)
    for execution in executions:
        dependencies = execution.pop('dependencies')
        assert dependencies == result['dependencies']
        execution['dependencies_sha256'] = hashlib.sha256(json.dumps(dependencies, sort_keys=True).encode()).hexdigest()
    write(args.output, result)
    args.output.with_name('README.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
