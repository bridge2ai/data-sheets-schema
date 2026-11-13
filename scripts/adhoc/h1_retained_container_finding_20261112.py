#!/usr/bin/env python3
"""Classify retained B2 plain-container gap, 2026-11-12.
Inputs: fixed Git objects and completed literal F0/B1 artifact directories.
Output: new helper-1 finding JSON. Read-only Git/AST/artifact parsing; no new
scanner/test execution, no source, historical fixture or D128 modification.
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
B2 = CASES / 'test_retained_review_outcome_B1/scanner'
OUT = ROOT / 'notes/development_efficiency_20261111/handoffs/codex-h1-retained-container-finding-20261112.json'
SCAN = '.claude/skills/d4d-generation-specificity-audit/scan.py'
FIXTURE = 'tests/fixtures/native_u3l_review_cases.json'
TEST = 'tests/test_native_u3l_review_fixtures.py'
POSITIVE_TEST = 'tests/test_generation_specificity_skill.py'
POSITIVE_NAME = 'test_plain_alias_of_model_text_container_traces_subscript_and_update_writes_5657'
TARGET = 'src/data_sheets_schema/project_hints.py'
TYPED = 'src/data_sheets_schema/typed_audit.py'
REFS = {
 'main_alias_fix_parent': '147e66c6609885b70390a8c9c2ada79a20aad7d6',
 'main_alias_fix': 'a4270683eaeebc2f3d676e04614579e743a353e1',
 'main_precision_update': 'a939fed2eeddc1a6487269230be8b97dde8e6863',
 'main_round3': '2a5db4ac5c5f18d1397a4b0aaa17a5e1e13a4cd7',
 'historical_fixture': 'e4985c1afcef9874be1c1e25736ce9d527af1428',
 'native_parent': '1a137b58860416a31618de44173180d021dfcc61',
 'main_parent': '7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1',
 'integration_merge': 'b11931410305569aba30b0f593193ae894bd0dc7',
 'prepin_candidate': '5d63d0a77dc43c064cfc2b376355f98009dd5b6e',
 'pin_update': '66fecb7be53aea49e371e224593203990f33763e',
 'tested_composition': '3a582243c4277934415bceb92cb888d617fd7a14'}
READS, COMMANDS = {}, []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def enc(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def read(path):
    if path.is_symlink() or path.resolve(strict=True) != path:
        raise ValueError('literal physical artifact required: ' + str(path))
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
            result[node.name] = dict(source_sha256=sha(text), ast_sha256=sha(ast.dump(node, include_attributes=False).encode()), start_line=start, end_line=node.end_lineno)
            if len(text) < 90000:
                result[node.name]['source'] = text.decode()
            else:
                result[node.name]['source_retention'] = 'Large enclosing definition identified by exact source and AST hashes; relevant nested effects body retained separately.'
    return result


def main():
    if OUT.exists():
        raise SystemExit('refusing to replace finding evidence')
    runs = {key: json.loads(read(folder / 'run.json')) for key, folder in (('F0', F0), ('B2', B2))}
    scans = {key: json.loads(read(folder / 'scan.json')) for key, folder in (('F0', F0), ('B2', B2))}
    if runs['F0']['fixture'] != 'F0' or runs['B2']['fixture'] != 'B2_typed_container_alias_token':
        raise ValueError('retained case identity differs')
    if not all(value['derivation_complete'] is True and value['returncode'] == 1 for value in runs.values()):
        raise ValueError('required completed scan evidence absent')
    before, after = scans['F0']['violations'], scans['B2']['violations']
    baseline, observed = Counter(map(enc, before)), Counter(map(enc, after))
    planted = [row for row in after if row['path'] == TARGET and row['match'] == 'CHORUS']
    gates = ['api', 'deterministic', 'github_assistant', 'native_agentic']
    if (len(before), len(after), len(planted)) != (9, 10, 1) or baseline-observed or observed-baseline != Counter(map(enc, planted)):
        raise ValueError('violation delta is not exactly one planted occurrence')
    if planted[0]['gates_in'] != gates or planted[0]['model_facing'] is not True or planted[0]['violation'] is not True:
        raise ValueError('planted occurrence gates differ')
    snapshots = {}
    functions = ('_local_writes', 'text_flow', 'effects', 'derive_model_facing', 'scan_file', 'is_violation')
    for label, commit in REFS.items():
        repo = PRIVATE if label == 'tested_composition' else REPO
        raw = git(repo, 'show', commit + ':' + SCAN)
        row = dict(commit=commit, scanner_sha256=sha(raw), functions=extract(raw, functions))
        for path, names in ((TEST, ('_require_complete_outcome', 'test_retained_review_outcome')),
                            (POSITIVE_TEST, (POSITIVE_NAME,)), (TYPED, ('_derive_uncached',))):
            if git(repo, 'ls-tree', commit, '--', path).strip():
                content = git(repo, 'show', commit + ':' + path)
                row[path] = dict(sha256=sha(content), definitions=extract(content, names))
        if git(repo, 'ls-tree', commit, '--', FIXTURE).strip():
            content = git(repo, 'show', commit + ':' + FIXTURE)
            row['historical_fixture_sha256'] = sha(content)
            row['historical_B2'] = next(case for case in json.loads(content)['cases'] if case['name'] == 'B2_typed_container_alias_token')
        snapshots[label] = row
    comparisons = []
    for a, b in (('main_parent', 'integration_merge'), ('integration_merge', 'prepin_candidate'), ('prepin_candidate', 'pin_update'), ('pin_update', 'tested_composition')):
        comparisons.append(dict(before=a, after=b, functions={name: dict(source_equal=snapshots[a]['functions'][name]['source_sha256'] == snapshots[b]['functions'][name]['source_sha256'], ast_equal=snapshots[a]['functions'][name]['ast_sha256'] == snapshots[b]['functions'][name]['ast_sha256']) for name in functions}))
    for label in ('main_alias_fix', 'main_precision_update', 'main_round3', 'integration_merge', 'pin_update'):
        git(REPO, 'show', '--format=fuller', '--stat', REFS[label], retain=True)
    git(REPO, 'show', '--format=', REFS['main_alias_fix'], '--', SCAN, retain=True)
    git(REPO, 'diff', REFS['prepin_candidate'], REFS['pin_update'], '--', SCAN, retain=True)
    git(REPO, 'merge-base', '--is-ancestor', REFS['main_alias_fix'], REFS['main_parent'])
    finished_xml = EXEC / 'scratch-native-h1-scanner-20261112/tests/h1-scanner-cohort/pytest.xml'
    positive = [dict(node.attrib, failed=node.find('failure') is not None, error=node.find('error') is not None, skipped=node.find('skipped') is not None) for node in ET.fromstring(read(finished_xml)).iter('testcase') if node.get('name') == POSITIVE_NAME]
    fixture_hashes = {row['historical_fixture_sha256'] for row in snapshots.values() if 'historical_fixture_sha256' in row}
    if fixture_hashes != {'2f2ef674466c3c86e84ded2f52dd61f30ec9b298e718f85c247ce7213713c552'}:
        raise ValueError('historical fixture hash changed')
    mutated_root = Path(runs['B2']['root'])
    mutable_inputs = {}
    for path in (TARGET, TYPED):
        raw = read(mutated_root / path)
        final_mutation = [row for row in runs['B2']['mutations'] if row['path'] == path][-1]
        if sha(raw) != final_mutation['after_sha256']:
            raise ValueError('retained mutation bytes changed')
        mutable_inputs[path] = dict(sha256=sha(raw), definitions=extract(raw, ('project_hint', '_derive_uncached')))
    report = dict(kind='H1 retained B2 gap versus current plain-alias tracing', status='open_local_test_contract_finding_no_source_change',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), helper=str(Path(__file__).resolve()), helper_sha256=sha(Path(__file__).read_bytes()),
        scope='Read-only Git/AST and already completed literal B1-directory B2-case artifacts; no final active CI cohort result claimed.',
        actual=dict(runs=runs, baseline_violations=before, current_violations=after, extra_violation_occurrences=planted,
                    baseline_occurrences_preserved=not bool(baseline-observed), baseline_ordered_prefix_preserved=enc(after[:9]) == enc(before),
                    target_surface=scans['B2']['surfaces'][TARGET], target_model_facing_derivation=scans['B2']['facts']['model_facing_modules']['derived'].get('project_hints'),
                    mutant_inputs=mutable_inputs, positive_test_results_from_finished_scanner_cohort=positive),
        historical_contract=dict(fixture=FIXTURE, sha256=next(iter(fixture_hashes)), known_gap='#5657', expected_violations=9,
          required_old_behavior='One planted helper hit is run_shaping, not model-facing, not a violation, with no gates. The retained fixture test applies this historical expected behavior to current HEAD.'),
        snapshots=snapshots, comparisons=comparisons,
        explanation=[
          'The B2 fixture introduces project_hints.project_hint and stores its result via view = contracts; view[worker][hint] = project_hint(project) in typed_audit._derive_uncached.',
          'Main a4270683eaeebc2f3d676e04614579e743a353e1 intentionally addresses issue5657: _local_writes propagates stores/method arguments across plain aliases; effects walks or refuses alias/subscript writes. Later main commits refine rebinding and branch precision.',
          'Current evidence attributes helper lines4-5 to project_hint() whose value reaches _derive_uncached(); one CHORUS occurrence at line5 gates all four named generation approaches.',
          'The nine complete baseline violation occurrences are retained unchanged. The only added violation is the exact planted helper return text.',
          'The relevant alias/flow functions are compared from main through integration, prepin, pin update and tested composition. H1 changes only the authority digest and enables the integrated scanner to complete; it does not introduce alias tracking.',
          'Main already contains a positive B2 plain-alias tracing regression with a no-sink negative control, and the finished H1 scanner cohort has its actual result. This supports closure of this bounded plain-alias fixture, not all container-alias gaps.',
          'Copied aliases such as dict(contracts), contracts.copy(), or dictionary unpacking remain separately documented limitations. This report does not classify B1/B3 outcomes or claim those limitations fixed.'
        ],
        recommendation=dict(priority='P2 retained historical test/current scanner contract mismatch',
          action='Keep the frozen fixture and D128 unchanged. Add a separately versioned current-composition expectation for B2: baseline9 plus exactly the planted helper occurrence, exact source line/text/span, all four gates, and a direct-versus-plain-alias or removed-sink control. Reuse the existing main positive test as supporting evidence.',
          existing_positive_test=POSITIVE_TEST + '::' + POSITIVE_NAME,
          prohibit='Do not rewrite historical expected9 to10, remove alias tracking to retain the gap, infer broad alias soundness, or expand owner approval.',
          pending='Lead-reviewed current-test disposition; no source fix or additional test/scanner run in this assignment.'),
        files=[dict(path=path, sha256=sha(raw), bytes=len(raw)) for path, raw in READS.items()], commands=COMMANDS)
    for path, raw in READS.items():
        if Path(path).read_bytes() != raw:
            raise ValueError('retained input changed during read')
    encoded = (json.dumps(report, indent=2, ensure_ascii=True) + '\n').replace(chr(64), '\\u0040').encode()
    with OUT.open('xb') as stream:
        stream.write(encoded)
    if OUT.read_bytes() != encoded:
        raise RuntimeError('persisted evidence differs')
    print(json.dumps(dict(path=str(OUT), sha256=sha(encoded), bytes=len(encoded), helper_sha256=report['helper_sha256'], comparisons=comparisons, positive=positive)))


if __name__ == '__main__':
    main()
