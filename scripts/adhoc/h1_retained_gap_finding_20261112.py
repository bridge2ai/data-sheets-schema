#!/usr/bin/env python3
"""Classify retained F3d gap versus current scanner detection, 2026-11-12.
Inputs: fixed Git source and already completed literal F0/F5 scan artifacts.
Output: new helper-1 finding JSON. No scanner/test/code execution, no network,
no frozen fixture or D128 rewrite. Local review evidence only.
"""
from __future__ import annotations
import ast
from collections import Counter
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
REPO = EXEC / 'codex-native-main-integration-20261112'
PRIVATE = EXEC / 'scratch-native-h1-scanner-20261112/h1-b/tree'
CASES = EXEC / 'scratch-native-h1-scanner-20261112/tests/h1-ci-scanner/cases/popen-gw0'
F0 = CASES / 'test_retained_review_outcome_F0/scanner'
F5 = CASES / 'test_retained_review_outcome_F5/scanner'
OUT = ROOT / 'notes/development_efficiency_20261111/handoffs/codex-h1-retained-gap-finding-20261112.json'
SCAN = '.claude/skills/d4d-generation-specificity-audit/scan.py'
FIXTURE = 'tests/fixtures/native_u3l_review_cases.json'
TEST = 'tests/test_native_u3l_review_fixtures.py'
POSITIVE_TEST = 'tests/test_generation_specificity_skill.py'
POSITIVE_NAME = 'test_module_m_targets_and_f3d_fixture_are_model_facing_5666'
TARGET = 'src/data_sheets_schema/source_attribution_preflight.py'
RENDERER = 'src/data_sheets_schema/native_shared_render.py'
REFS = {
 'current_module_discovery_introduction': 'b85ac0fb7843866aa767f50e3e2e889ac706f8ba',
 'frozen_native_test_introduction': 'e4985c1afcef9874be1c1e25736ce9d527af1428',
 'native_parent': '1a137b58860416a31618de44173180d021dfcc61',
 'main_parent': '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1',
 'integration_merge': 'b11931410305569aba30b0f593193ae894bd0dc7',
 'prepin_candidate': '5d63d0a77dc43c064cfc2b376355f98009dd5b6e',
 'pin_update': '66fecb7be53aea49e371e224593203990f33763e',
 'tested_composition': '3a582243c4277934415bceb92cb888d617fd7a14',
}
COMMANDS = []
READS = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def enc(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def read(path):
    if path.is_symlink() or path.resolve(strict=True) != path:
        raise ValueError('literal physical evidence path required: ' + str(path))
    raw = path.read_bytes()
    READS[str(path)] = raw
    return raw


def git(repo, *parts, retain=False):
    command = ['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never', '-c', 'core.fsmonitor=false', '-C', str(repo), *parts]
    proc = subprocess.run(command, env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL=''), capture_output=True, check=True)
    row = dict(argv=command, returncode=proc.returncode, stdout_sha256=sha(proc.stdout), stdout_bytes=len(proc.stdout), stderr=proc.stderr.decode())
    if retain:
        row['stdout'] = proc.stdout.decode()
    COMMANDS.append(row)
    return proc.stdout


def extract(raw, names):
    lines = raw.splitlines(keepends=True)
    result = {}
    for node in ast.walk(ast.parse(raw)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            start = min([node.lineno] + [item.lineno for item in node.decorator_list])
            text = b''.join(lines[start-1:node.end_lineno])
            result[node.name] = dict(source_sha256=sha(text), ast_sha256=sha(ast.dump(node, include_attributes=False).encode()), source=text.decode(), start_line=start, end_line=node.end_lineno)
    return result


def main():
    if OUT.exists():
        raise SystemExit('refusing to overwrite existing finding evidence')
    runs = {name: json.loads(read(folder / 'run.json')) for name, folder in (('F0', F0), ('F3d', F5))}
    scans = {name: json.loads(read(folder / 'scan.json')) for name, folder in (('F0', F0), ('F3d', F5))}
    if runs['F0']['fixture'] != 'F0' or runs['F3d']['fixture'] != 'F3d_module_helper_print':
        raise ValueError('literal retained case identities differ')
    if not all(run['derivation_complete'] is True and run['returncode'] == 1 for run in runs.values()):
        raise ValueError('required completed actual scan evidence absent')
    before, after = scans['F0']['violations'], scans['F3d']['violations']
    if (len(before), len(after)) != (9, 11):
        raise ValueError('unexpected observed violation counts')
    baseline, observed = Counter(map(enc, before)), Counter(map(enc, after))
    extras = observed - baseline
    planted = [row for row in after if row['path'] == TARGET and row['match'] == 'CHORUS']
    if baseline - observed or len(planted) != 2 or extras != Counter(map(enc, planted)):
        raise ValueError('current delta differs from two planted occurrences')
    if not all(row['gates_in'] == ['native_agentic'] and row['violation'] is True and row['model_facing'] is True for row in planted):
        raise ValueError('current planted native-only gating differs')
    snapshots = {}
    for label, commit in REFS.items():
        repo = PRIVATE if label == 'tested_composition' else REPO
        scanner = git(repo, 'show', commit + ':' + SCAN)
        entry = dict(commit=commit, scanner_sha256=sha(scanner), functions=extract(scanner, ('discover_model_commands', '_model_command_tables', '_argv_runs', '_run_module_target', 'scan_file', 'is_violation')))
        for path, names in ((TEST, ('_require_complete_outcome', 'test_retained_review_outcome')),
                            (POSITIVE_TEST, (POSITIVE_NAME,)), (RENDERER, ('commands',)), (TARGET, ('main',))):
            if git(repo, 'ls-tree', commit, '--', path).strip():
                raw = git(repo, 'show', commit + ':' + path)
                entry[path] = dict(sha256=sha(raw), definitions=extract(raw, names))
        if git(repo, 'ls-tree', commit, '--', FIXTURE).strip():
            raw = git(repo, 'show', commit + ':' + FIXTURE)
            entry['frozen_fixture_sha256'] = sha(raw)
            entry['historical_F3d'] = next(case for case in json.loads(raw)['cases'] if case['name'] == 'F3d_module_helper_print')
        snapshots[label] = entry
    comparisons = []
    for a, b in (('native_parent', 'main_parent'), ('main_parent', 'integration_merge'),
                 ('integration_merge', 'prepin_candidate'), ('prepin_candidate', 'pin_update'), ('pin_update', 'tested_composition')):
        comparisons.append(dict(before=a, after=b, functions={name: dict(source_equal=snapshots[a]['functions'][name]['source_sha256'] == snapshots[b]['functions'][name]['source_sha256'], ast_equal=snapshots[a]['functions'][name]['ast_sha256'] == snapshots[b]['functions'][name]['ast_sha256']) for name in snapshots[a]['functions']},
            historical_fixture_equal=snapshots[a].get('frozen_fixture_sha256') == snapshots[b].get('frozen_fixture_sha256')))
    for label in ('current_module_discovery_introduction', 'frozen_native_test_introduction', 'integration_merge', 'pin_update'):
        git(REPO, 'show', '--format=fuller', '--stat', REFS[label], retain=True)
    git(REPO, 'diff', REFS['prepin_candidate'], REFS['pin_update'], '--', SCAN, retain=True)
    cohort_xml = EXEC / 'scratch-native-h1-scanner-20261112/tests/h1-scanner-cohort/pytest.xml'
    positive_results = [dict(node.attrib, failed=node.find('failure') is not None, error=node.find('error') is not None, skipped=node.find('skipped') is not None) for node in ET.fromstring(read(cohort_xml)).iter('testcase') if node.get('name') == POSITIVE_NAME]
    fixture_hashes = {row['frozen_fixture_sha256'] for row in snapshots.values() if 'frozen_fixture_sha256' in row}
    if fixture_hashes != {'2f2ef674466c3c86e84ded2f52dd61f30ec9b298e718f85c247ce7213713c552'}:
        raise ValueError('frozen fixture identities differ')
    mutated_root = Path(runs['F3d']['root'])
    mutated = read(mutated_root / TARGET)
    if sha(mutated) != runs['F3d']['mutations'][0]['after_sha256']:
        raise ValueError('retained mutation bytes differ')
    report = dict(kind='H1 retained historical gap conflicts with current module-discovery proof',
      status='open_local_test_contract_finding_no_source_change', created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      helper=str(Path(__file__).resolve()), helper_sha256=sha(Path(__file__).read_bytes()),
      scope='Read-only source/AST inspection and retained artifacts. CI scanner cohort was still running when assigned; no final cohort outcome claimed.',
      actual=dict(runs=runs, baseline_violations=before, current_violations=after,
          baseline_occurrences_preserved=not bool(baseline-observed), baseline_ordered_prefix_preserved=enc(after[:len(before)]) == enc(before),
          extra_violation_occurrences=planted, duplicate_occurrences_preserved=True,
          target_surface=scans['F3d']['surfaces'][TARGET], target_command_fact=scans['F3d']['facts']['model_commands'][TARGET],
          target_mutated_sha256=sha(mutated), current_positive_test_results_from_finished_scanner_cohort=positive_results),
      historical_contract=dict(fixture=FIXTURE, fixture_sha256=next(iter(fixture_hashes)), expected_violations=9, known_gap='N1',
          expectations='F3d planted hits must remain run_shaping, not model-facing, not violations, with gates_in empty; current test runs the frozen expected outcome against current HEAD.'),
      snapshots=snapshots, comparisons=comparisons,
      causal_explanation=[
        'Native parent command discovery only admitted __init__.py/__main__.py package targets, skipping the ordinary source_attribution_preflight.py module named by native_shared_render.commands.',
        'Main commit b85ac0fb7843866aa767f50e3e2e889ac706f8ba explicitly implements issue5666 module.py command discovery and adds a positive F3d regression for the exact planted print.',
        'Integration merge b11931410305569aba30b0f593193ae894bd0dc7 keeps main discovery semantics; the relevant functions remain byte-identical through prepin5d63, pin66fec and the tested private composition.',
        'Current scan records native_shared_render.py:278 and native_source_attribution.py:59 as -m command evidence. The target is model_facing and runs as script only in native_agentic; other listed approaches remain run_shaping.',
        'The single planted print contains CHORUS twice, producing two duplicate occurrence objects at line174. Both gate only native_agentic. The nine baseline violation objects remain unchanged.',
        'H1 pin repair permits the complete integrated scan to reach these existing discovery rules; it does not introduce the F3d recognition behavior. A stale prepin full scan might refuse earlier, so no historical fullscan pass is inferred.',
        'This closes the direct module-print fixture, not the separate imported-helper-return gap F3e. Do not infer complete native-model coverage.'
      ],
      recommendation=dict(priority='P2 current-test/historical-fixture contract mismatch',
          action='Preserve native_u3l_review_cases.json and D128 bytes as historical evidence. Add or adapt a separately versioned current-composition expectation for F3d using the existing main positive proof: baseline9 plus exactly two planted native-only violations, exact lines/snippet/duplicate count and retained source inventory.',
          existing_current_proof=POSITIVE_TEST + '::' + POSITIVE_NAME,
          restrictions='Do not rewrite historical expected9 to11, label historical N1 never existed, weaken discovery to regain the old count, or reuse D128 approval for new instrument identities.',
          pending='Current CI fixture contract needs lead-reviewed disposition. B1/B2/B3 outcomes are outside this bounded evidence snapshot; no extra cohorts or source fix performed.'),
      files=[dict(path=path, sha256=sha(raw), bytes=len(raw)) for path, raw in READS.items()], commands=COMMANDS)
    for path, raw in READS.items():
        if Path(path).read_bytes() != raw:
            raise ValueError('retained input changed while reading: ' + path)
    encoded = (json.dumps(report, indent=2, ensure_ascii=True) + '\n').replace(chr(64), '\\u0040').encode()
    with OUT.open('xb') as stream:
        stream.write(encoded)
    if OUT.read_bytes() != encoded:
        raise RuntimeError('saved finding differs')
    print(json.dumps(dict(path=str(OUT), sha256=sha(encoded), bytes=len(encoded), helper_sha256=report['helper_sha256'], positive_results=positive_results)))


if __name__ == '__main__':
    main()
