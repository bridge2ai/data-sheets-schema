#!/usr/bin/env python3
# Purpose: retain G1 scanner, validation and synthetic-project evidence compactly.
# Inputs: external offline check outputs; outputs: external review evidence files.
# Findings F2-F19 / D66-D67, 2026-10-29. No network, scoring or run mutation.
import argparse
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'plans/reviews/generality_g1_evidence_2026-10-29'
BASE = '55c7b94b838eb500888055da5a47acf2ee9e2e15'


def write(name, value):
    OUT.mkdir(exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    assert json.loads(path.read_bytes()) == value


def archive(source, target):
    raw = Path(source).read_bytes()
    assert raw
    output = OUT / target
    output.write_bytes(gzip.compress(raw, mtime=0))
    assert gzip.decompress(output.read_bytes()) == raw


def scan():
    summary = {}
    for stage in ('before', 'after'):
        source = Path(f'/private/tmp/g1-scan-{stage}.json')
        data = json.loads(source.read_bytes())
        summary[stage] = {'commit': data['commit'], 'exit': data['exit'],
            'totals': data['totals'], 'self_test': data['self_test'],
            'violations_by_file': dict(Counter(hit['path'] for hit in data['violations']))}
        archive(source, f'scan_{stage}.json.gz')
        archive(source.with_suffix('.md'), f'scan_{stage}.md.gz')
        if stage == 'after':
            write('remaining_scanner_hits.json', {'violations': data['violations'],
                'exceptions': data['exceptions'], 'tracked_without_reason': data['tracked_without_reason']})
    write('scanner_summary.json', summary)
    print(json.dumps(summary, indent=2))


def checks():
    # Chronological targeted runs; latest status for each exact node wins.
    stems = ['final-tests', 'review-fixes', 'context-final', 'final-remaining', 'scanner-tests', 'api-final', 'fallback-final', 'api-remainder']
    latest, runs = {}, []
    for stem in stems:
        path = Path(f'/private/tmp/g1-{stem}.xml')
        suites = ET.parse(path).getroot()
        counts = Counter()
        for case in suites.iter('testcase'):
            if not case.get('name') or not case.get('classname'):
                continue  # Interrupted test has no completed node result.
            status = ('failed' if case.find('failure') is not None else
                      'error' if case.find('error') is not None else
                      'skipped' if case.find('skipped') is not None else 'passed')
            key = case.get('classname') + '::' + case.get('name')
            parts = case.get('classname').split('.')
            module_end = max(i for i, part in enumerate(parts) if part.startswith('test_')) + 1
            source = '/'.join(parts[:module_end]) + '.py'
            latest[key] = {'status': status, 'run': stem, 'source': source}
            counts[status] += 1
        run = {'run': stem, 'counts': dict(counts)}
        if stem == 'api-remainder':
            run['session_exit_status'] = 1
            run['session_guard_note'] = (
                'All 156 test nodes passed. The notes-tree guard reported the evidence README '
                'created by the operator during the run, not by a test. '
                'The full session is not reported as a clean exit.')
        runs.append(run)
        archive(path, f'{stem}.xml.gz')
        archive(path.with_suffix('.log'), f'{stem}.log.gz')
    unresolved = {k: v for k, v in latest.items() if v['status'] in ('failed', 'error')}
    known_base = {'tests.test_download.test_api_runner.TestValidatorRepairRefreshCheckpoint::'
                  'test_missing_corrupt_or_stale_checkpoint_refuses_before_calls':
                  'G1-R10: unchanged checkpoint fixture expects the older refresh guard before the latch journal'}
    per_file = {}
    for value in latest.values():
        counts = per_file.setdefault(value['source'], {})
        counts[value['status']] = counts.get(value['status'], 0) + 1
    result = {'runs': runs, 'latest_unique_node_counts': dict(Counter(v['status'] for v in latest.values())),
              'latest_counts_by_file': per_file,
              'unresolved': unresolved, 'deferred_base_failures': known_base, 'latest_nodes': latest}
    write('validation_summary.json', result)
    for stem in ('step0-tests', 'regen', 'generated-checks'):
        archive(f'/private/tmp/g1-{stem}.log', f'{stem}.log.gz')
    print(json.dumps({k: v for k, v in result.items() if k != 'latest_nodes'}, indent=2))
    assert set(unresolved) == set(known_base), unresolved


def newproj():
    folder = Path('/private/tmp/g1-newproj-verified')
    proof = json.loads((folder / 'proof.json').read_bytes())
    assert proof['profile'] == 'neutral' and proof['vocabulary'] == {} and proof['model_calls'] == 0
    write('newproj_proof.json', proof)
    context = folder / 'contexts/newproj_omission_context.json'
    for path in (folder / 'registration.json', folder / 'manifest.yaml', context):
        archive(path, f'newproj_{path.name}.gz')
    print(json.dumps(proof, indent=2))


def protected():
    names = subprocess.check_output(['git', 'diff', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
    prohibited = [name for name in names if name in {
        'src/data_sheets_schema/shared_generation.py', 'data/generations/canonical_hashes.yaml',
        'src/download/prompts/canonical_hashes.yaml'} or Path(name).name == 'STATUS.md'
        or name.startswith(('data/ATTIC/', 'data/d4d_concatenated/')) or '/decisions/' in name]
    merges = subprocess.check_output(['git', 'rev-list', '--merges', f'{BASE}..HEAD'], cwd=ROOT, text=True).splitlines()
    result = {'step0_base': BASE, 'audited_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'prohibited_changes': prohibited, 'generality_merge_commits': merges}
    write('protected_paths.json', result)
    assert not prohibited and not merges
    print(json.dumps(result, indent=2))


def owl():
    from rdflib import Graph
    from rdflib.compare import graph_diff, to_isomorphic
    path = 'project/owl/data_sheets_schema.owl.ttl'
    before = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
    after = (ROOT / path).read_bytes()
    old = Graph().parse(data=before, format='turtle')
    new = Graph().parse(data=after, format='turtle')
    common, removed, added = graph_diff(to_isomorphic(old), to_isomorphic(new))
    result = {'before_triples': len(old), 'after_triples': len(new), 'common_triples': len(common),
        'removed': sorted(' '.join(part.n3() for part in row) for row in removed),
        'added': sorted(' '.join(part.n3() for part in row) for row in added),
        'before_sha256': hashlib.sha256(before).hexdigest(), 'after_sha256': hashlib.sha256(after).hexdigest()}
    write('owl_semantic_delta.json', result)
    print(json.dumps(result, indent=2))


def basefail():
    def source(path, before):
        return (subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
                if before else (ROOT / path).read_bytes())

    def definition(path, name, before):
        return next(node for node in ast.walk(ast.parse(source(path, before)))
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name)

    result = {'base': BASE, 'issue': 'G1-R10', 'unchanged_files': {}}
    for path in ('src/data_sheets_schema/latch_journal.py',
                 'src/data_sheets_schema/usage_ledger.py',
                 'src/data_sheets_schema/shared_generation.py', 'tests/test_report_admission.py'):
        raw = source(path, False)
        assert source(path, True) == raw, path
        result['unchanged_files'][path] = hashlib.sha256(raw).hexdigest()
    tests = 'tests/test_download/test_api_runner.py'
    name = 'TestValidatorRepairRefreshCheckpoint'
    result['checkpoint_test_class_unchanged'] = (
        ast.dump(definition(tests, name, True)) == ast.dump(definition(tests, name, False)))
    runner = 'src/data_sheets_schema/api_runner.py'
    result['unchanged_runner_paths_except_retirement'] = []
    for name in ('execute', '_execute', '__post_init__'):
        old, new = definition(runner, name, True), definition(runner, name, False)
        expected = ('self.condition == "tuned" and not self._replay_only'
                    if name == '__post_init__' else 'spec.condition == "tuned"')
        new.body = [node for node in new.body if not (
            isinstance(node, ast.If) and ast.dump(node.test) == ast.dump(ast.parse(expected, mode='eval').body))]
        assert ast.dump(old) == ast.dump(new), name
        result['unchanged_runner_paths_except_retirement'].append(name)
    assert result['checkpoint_test_class_unchanged']
    result['basis'] = ('The fixture uses condition generic, so retirement guards do not fire. '
                       'Its ledger-controller mutation is refused by the unchanged latch journal first; '
                       'this is not a timing failure. No base execution or scientific scoring is claimed.')
    write('base_checkpoint_failure.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['scan', 'checks', 'newproj', 'protected', 'owl', 'basefail'])
    globals()[parser.parse_args().stage]()
