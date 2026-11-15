#!/usr/bin/env python3
"""Summarize the v3 merge-fix focused evidence for PR 5968, 2026-11-15.

Inputs: saved run plans, JUnit-derived results and Git source identities.
Outputs: scratch evidence ledger and the assigned answer-first handoff.
No network, source modification, publication or approval-pin rotation.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
E = ROOT.parent
SCRATCH = E / 'scratch-v3-merge-fix-20261115'
REPORT = E / 'codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/codex196-v3-merge-fix-20261115.md'
BASE = 'f10e8ae20d5450d1933e624c6cb88bdd98900c9b'
PROTECTED = ['src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json']
SCANNER = '.claude/skills/d4d-generation-specificity-audit/scan.py'
MANIFEST = 'src/data_sheets_schema/native_environment_manifest.py'
CONTRACT = 'src/data_sheets_schema/native_shared_contract.py'


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True).stdout


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    if path.exists():
        assert load(path) == value, 'refusing changed evidence: ' + str(path)
        return
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def ledger(*, persist=True):
    assert git('branch', '--show-current').decode().strip() == 'codex/v3-merge-fix-20261115'
    data = dict(base=BASE, head=git('rev-parse', 'HEAD').decode().strip(), runs={}, identities={})
    data['code_patch_sha256'] = sha(git('diff', '--binary', BASE, '--', MANIFEST,
        'tests/test_native_environment_manifest.py', 'tests/test_native_u3d_round9_boundaries.py'))
    for path in [*PROTECTED, SCANNER, CONTRACT, MANIFEST]:
        before, after = git('show', BASE + ':' + path), (ROOT / path).read_bytes()
        data['identities'][path] = dict(base_sha256=sha(before), current_sha256=sha(after), unchanged=before == after)
    tree = ast.parse((ROOT / SCANNER).read_text())
    binding = next(node for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == '_NATIVE_V3_RENDER_SOURCES'
                           for target in node.targets))
    old = next(value.value for key, value in zip(binding.value.keys, binding.value.values)
               if isinstance(key, ast.Constant) and key.value == MANIFEST)
    assert old == data['identities'][MANIFEST]['base_sha256']
    data['pin_proposals'] = [dict(file=SCANNER,
        constant="_NATIVE_V3_RENDER_SOURCES['" + MANIFEST + "']",
        old=old, new=data['identities'][MANIFEST]['current_sha256'])]
    command = ['rg', '--hidden', '--no-ignore', '-n', '-F', old, '.', '-g', '!.git']
    references = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert references.returncode == 0
    data['pin_reference_search'] = dict(command=command, stdout=references.stdout)
    for outcome in sorted(SCRATCH.glob('*/outcome.json')):
        directory = outcome.parent
        if not (directory / 'results.json').is_file():
            continue
        value = dict(outcome=load(outcome), plan=load(directory / 'plan.json'),
                     results=load(directory / 'results.json'), origins=[], files={})
        for case in value['results']['cases']:
            if case['category'] != 'other':
                continue
            if 'native shared JSON exceeds its structural bound' in case['detail']:
                case['category'] = 'manifest_capacity_fixed'
            elif 'consumed source differs from the reviewed commit' in case['detail']:
                case['category'] = 'uncommitted_source_refusal_resolved_by_commit'
        recorded = value['plan'].get('code_patch_sha256', value['plan'].get('tracked_diff_sha256'))
        value['matches_delivery_code_patch'] = recorded == data['code_patch_sha256'] if recorded else None
        for path in sorted(directory.glob('origins-*.json')):
            value['origins'].append(dict(path=str(path), **load(path)))
        grouped = defaultdict(Counter)
        for case in value['results']['cases']:
            grouped[case['classname']][case['state']] += 1
        value['files'] = {name: dict(counts) for name, counts in sorted(grouped.items())}
        data['runs'][directory.name] = value
    if 'final-shared-venv' in data['runs']:
        validated = data['runs']['final-shared-venv']['plan']['source_commit']
        data['post_validation_changes'] = git('diff', '--name-only', validated, data['head']).decode().splitlines()
        assert set(data['post_validation_changes']) <= {
            'scripts/adhoc/report_v3_merge_fix_20261115.py', 'scripts/adhoc/run_v3_merge_fix_20261115.py'}
    if persist:
        write(SCRATCH / 'evidence-ledger.json', data)
    return data


def manifest_capacity():
    sys.path.insert(0, str(ROOT / 'src'))
    from data_sheets_schema import native_shared_contract as contract
    current = next((SCRATCH / 'isolated-canary/bt').rglob('environment-manifest.json'))
    prior = E / 'scratch-native-manifest-integration-20261114/continuation/cost-installed-canary/cases/popen-gw0/test_installed_manifest_modes_0/environment-manifest.json'
    normalize = lambda name: re.sub(r'[-_.]+', '-', name).lower()
    lock_names = {normalize(item['name']) for item in tomllib.loads((ROOT / 'poetry.lock').read_text())['package']}
    data = {}
    for label, path in (('current', current), ('previous_passed_cost_canary', prior)):
        raw = path.read_bytes()
        value = json.loads(raw)
        try:
            contract.strict_json(raw, 'saved manifest diagnostic', 8_000_000)
            parsed = 'passed'
        except ValueError as exc:
            parsed = str(exc)
        values = 0
        keys = 0
        pending = [value]
        while pending:
            item = pending.pop()
            values += 1
            if isinstance(item, dict):
                keys += len(item)
                pending.extend(item.values())
            elif isinstance(item, list):
                pending.extend(item)
        distributions = {item['name']: dict(version=item['version'],
            file_stats=len(item.get('file_stats', {})), verified_files=item['verified_files'],
            keys=sorted(item)) for item in value['distributions']}
        data[label] = dict(path=str(path), sha256=sha(raw), bytes=len(raw),
            parsed=parsed, value_nodes=values, object_keys=keys,
            lexical_value_and_key_starts=values + keys,
            node_bound=contract.HARD_LIMITS['json_yaml_nodes_per_document'],
            distributions=distributions, unowned_files=len(value['unowned_files']),
            outside_lock=sorted(set(distributions) - lock_names))
    old = data['previous_passed_cost_canary']['distributions']
    new = data['current']['distributions']
    data['inventory_changes'] = {name: dict(before=old.get(name), after=new.get(name))
        for name in sorted(set(old) | set(new)) if old.get(name) != new.get(name)}
    write(SCRATCH / 'manifest-capacity.json', data)
    print(json.dumps({label: {k: v for k, v in data[label].items() if k != 'distributions'}
        for label in ('current', 'previous_passed_cost_canary')}, indent=2))


def compact_capacity():
    sys.path.insert(0, str(ROOT / 'src'))
    from data_sheets_schema import native_environment_manifest as manifest
    current = next((SCRATCH / 'compact-canary/bt').rglob('environment-manifest.json'))
    raw = current.read_bytes()
    value = manifest.validate(manifest.c.strict_json(raw, 'compact capacity diagnostic', manifest.MAX_BYTES))
    expanded = json.loads(raw)
    for row in expanded['distributions']:
        row['file_stats'] = {name: {'type': pair[0], 'bytes': pair[1]}
                             for name, pair in row['file_stats'].items()}
    original = load(Path(load(SCRATCH / 'manifest-capacity.json')['current']['path']))
    assert expanded == original, 'compact encoding changed captured semantic information'
    pairs = sum(len(row['file_stats']) for row in value['distributions'])
    initial = load(SCRATCH / 'manifest-capacity.json')['current']
    data = dict(path=str(current), bytes=len(raw), sha256=sha(raw),
        stat_pairs=pairs, restored_document_equals_original=True,
        lexical_value_and_key_starts=initial['lexical_value_and_key_starts'] - 2 * pairs,
        value_nodes=initial['value_nodes'], parser='passed',
        unchanged_parser_bound=manifest.c.HARD_LIMITS['json_yaml_nodes_per_document'])
    write(SCRATCH / 'compact-manifest-capacity.json', data)
    print(json.dumps(data, indent=2))


def report(data):
    runs = data['runs']
    final = runs['final-shared-venv']
    assert final['matches_delivery_code_patch'] is True
    assert all(case['category'] in (None, 'shared_editable_namespace') for case in final['results']['cases'])
    assert runs['committed-canary']['results']['totals'] == dict(passed=1, failed=0, errors=0, skipped=0)
    counts = final['results']['totals']
    capacity = load(SCRATCH / 'manifest-capacity.json')
    lines = ['Fixes are committed. The final requested cohort has '
             + str(counts['passed']) + ' passed, ' + str(counts['failed']) + ' failed and '
             + str(counts['errors']) + ' setup errors; every non-pass is the expected shared-editable '
             'namespace refusal. The committed preparation canary passes after isolating that '
             'foreign import path. One scanner pin update is proposed and has not been applied.', '',
             'The stale version assertion and synthetic namespace fixtures are fixed. '
             'A further real capacity defect is fixed by losslessly compacting RECORD lstat '
             'identities; all existing verification and JSON bounds remain in place. '
             'These results do not certify all setup-blocked test bodies or Linux CI.', '',
             'Branch: `codex/v3-merge-fix-20261115`. Base: `' + data['base'] + '`. '
             'Delivery head: `' + data['head'] + '`.', '',
             'Source/tests were validated at `' + final['plan']['source_commit'] + '`. '
             'Any subsequent delivery changes contain only the two retained provenance helpers; '
             'the source/test patch hash is checked against the saved final run plan.', '',
             'Changes and classification:', '',
             '- The registration, shared-registration, execution-failure and callback-preloading '
             'setup errors arise from two real package namespace roots: the assigned worktree '
             'and the primary checkout. The primary environment’s data_sheets_schema.pth '
             'points at the latter. The manifest’s exact-root refusal is correct; no production '
             'namespace check or manifest verification mode was relaxed.',
             '- The builder subprocess inherits the same shared installation. Its production_refusal '
             'is an environment failure before the expected offline dependency_stop. The builder '
             'test and its expected exit status were retained.',
             '- The two synthetic manifest tests provided invented distribution metadata but '
             'implicitly used the host namespace. They now explicitly provide the matching synthetic '
             'namespace. The exclusion test still rejects a foreign-only namespace and additionally '
             'rejects a mixed pinned-plus-foreign namespace. The unrelated-payload test retains its '
             'original refusal assertion.',
             '- The round-9 assertion incorrectly equated current schema version with authority '
             'version. It now checks schema version 3 against the producer and authority version 2 '
             'against the producer separately. Historical-v2 refusal cases and authority-version-2 '
             'assertions remain intentional.', '',
             'The diagnostic canary uncovered a real manifest-capacity mismatch after removing '
             'the foreign import path. The emitted manifest passed canonical value validation '
             'but failed strict_json because its lexical count includes object keys. '
             'The full shared environment has more installed development dependencies than '
             'the earlier declared-dependency canary. Only pip is outside the current lock '
             'among its distribution names; the earlier successful result therefore did not '
             'establish capacity for this larger main-plus-dev environment.', '',
             'The fix changes each distribution file_stats value from a closed '
             '{type, bytes} object to a fixed [type, bytes] pair. Both integers retain the '
             'same type, value, size and absence checks through _stat_shape. RECORD hashes, '
             'payload hashing, complete path inventory, lstat identity, full/light modes and '
             'per-process verification reuse are unchanged. Unowned-file stat objects are '
             'unchanged. Existing synthetic manifests with the earlier object encoding must '
             'be regenerated under the existing v1 refinement policy; the registration schema '
             'stays v3 and authority version stays 2.', '',
             'Saved capacity evidence:', '',
             '| Manifest | Bytes | Value nodes | Object keys | Lexical starts | Parser |',
             '| --- | ---: | ---: | ---: | ---: | --- |']
    for label in ('current', 'previous_passed_cost_canary'):
        row = capacity[label]
        lines.append('| ' + label + ' | ' + ' | '.join(str(row[key]) for key in
            ('bytes', 'value_nodes', 'object_keys', 'lexical_value_and_key_starts', 'parsed')) + ' |')
    compact = load(SCRATCH / 'compact-manifest-capacity.json')
    lines.append('| compact_current | ' + ' | '.join(str(item) for item in (
        compact['bytes'], compact['value_nodes'],
        compact['lexical_value_and_key_starts'] - compact['value_nodes'],
        compact['lexical_value_and_key_starts'], compact['parser'])) + ' |')
    lines += ['', 'Expanding the ' + str(compact['stat_pairs']) + ' compact stat pairs '
              'reproduced the complete original saved manifest exactly. The parser bound '
              'remains ' + str(compact['unchanged_parser_bound']) + '.', '']
    lines += ['',
             'CI installation difference: `.github/workflows/main.yaml` uses '
             '`.github/actions/setup-project/action.yml`; the latter always runs '
             '`poetry install --with dev --no-interaction`, including cache hits, to install '
             'the current checkout. This host deliberately uses the primary checkout’s existing '
             'environment with `PYTHONPATH` pointing at the assigned worktree. These saved local '
             'results do not constitute a Linux CI run.', '',
             'Focused results generated from saved JUnit records:', '',
             '| Run | Passed | Failed | Errors | Skipped | Delivery code patch |',
             '| --- | ---: | ---: | ---: | ---: | --- |']
    for name, run in runs.items():
        counts = run['results']['totals']
        lines.append('| ' + name + ' | ' + ' | '.join(str(counts[key]) for key in ('passed', 'failed', 'errors', 'skipped'))
                     + ' | ' + str(run['matches_delivery_code_patch']) + ' |')
    lines += ['', 'True in the delivery-patch column means the saved source/test patch matches '
              'the delivered code; None means that earlier plan predates patch-hash recording.', '',
              'The earlier shared-venv run preceded the compact encoding. isolated-canary '
              'exposed the structural bound. compact-canary then passed manifest creation and '
              'hit the unchanged committed-source check because the production edit had not '
              'yet been committed. committed-canary reran the same case after the code commit '
              'and passed. All earlier refusals and their artifacts are retained.', '',
              'The raw single-test canary established the offline launcher, four-worker mode, '
              'JUnit persistence and process-group cleanup before the full cohort. The committed '
              'canary additionally verified the full installed census, compact manifest, actual '
              'preparation and verify_preparer path. Neither canary establishes CI or the bodies '
              'of other setup-blocked tests.']
    lines += ['', 'Per-file counts:', '', '| Run | File | Passed | Failed | Errors | Skipped |',
              '| --- | --- | ---: | ---: | ---: | ---: |']
    for name, run in runs.items():
        for filename, counts in run['files'].items():
            lines.append('| ' + name + ' | ' + filename + ' | ' + ' | '.join(str(counts.get(key, 0)) for key in ('passed', 'failed', 'errors', 'skipped')) + ' |')
    lines += ['', 'Failure classifications and exact nodes:', '']
    listed = {}
    for name, run in runs.items():
        categories = defaultdict(list)
        for case in run['results']['cases']:
            if case['category']:
                categories[case['category']].append(case['classname'] + '::' + case['name'])
        if not categories:
            lines.append('- ' + name + ': no failures or errors.')
        for category, nodes in sorted(categories.items()):
            key = (category, tuple(sorted(nodes)))
            if key in listed:
                lines += ['', name + ': the same ' + str(len(nodes)) + ' ' + category
                          + ' nodes listed under ' + listed[key] + '.', '']
                continue
            listed[key] = name
            lines += ['', name + ': ' + category + ' (' + str(len(nodes)) + ').', '', '```text', *nodes, '```']
    lines += ['', 'The explicit path-isolation diagnostic removes only the primary src path '
              'from pytest processes and records before/after import paths. It keeps the required '
              'primary Python and worktree PYTHONPATH and runs the unchanged production namespace '
              'guard. Ordinary builder children still start with the shared editable installation. '
              'This diagnostic is not an installation change or CI acceptance.', '',
              'The diagnostic node list in each saved plan defines its coverage. Setup-blocked '
              'test bodies absent from those plans remain unverified here. No live matrix or '
              'Linux CI run was performed.', '',
              'The requested cohort has zero scanner-template failures; all of its non-passes '
              'are the namespace guard. The independently assigned scanner producer-template repair remains outside '
              'this branch; scan.py was not edited.', '',
              'Pin proposal only; the scanner file was not edited:', '',
              '| File | Constant or entry | Old | Proposed new |',
              '| --- | --- | --- | --- |']
    for proposal in data['pin_proposals']:
        lines.append('| ' + ' | '.join('`' + proposal[key] + '`' for key in
            ('file', 'constant', 'old', 'new')) + ' |')
    lines += ['', 'No controller, prompt, scanner or approval-fixture pin changed. '
              'The evidence ledger records baseline/current hashes of all four protected '
              'files, the scanner, the unchanged JSON contract and the changed manifest module.', '',
              'An ignore-independent search of the assigned worktree found the current scanner '
              'entry and a historical assertion in scripts/adhoc/merge_manifest_final_20261115.py. '
              'The dated prior-merge helper remains historical provenance and is not rotated.', '',
              'Execution and evidence:', '',
              '- Runner: `' + str(ROOT / 'scripts/adhoc/run_v3_merge_fix_20261115.py') + '`.',
              '- Report generator: `' + str(Path(__file__).resolve()) + '`.',
              '- Ledger: `' + str(SCRATCH / 'evidence-ledger.json') + '`.',
              '- Capacity diagnosis: `' + str(SCRATCH / 'manifest-capacity.json') + '`.',
              '- Lossless encoding check: `' + str(SCRATCH / 'compact-manifest-capacity.json') + '`.',
              '- Run plans contain exact commands, source head, helper hash, deadline and mode. '
              'Each run directory retains stdout, stderr, JUnit, classified results and import witnesses. '
              'The watchdog owns the process group externally and records cleanup; no inherited alarm.',
              '- Offline OS sandbox denies networking and native command execution. No GitHub write, '
              'push, provider call or Claude invocation was performed.', '',
              'Read-only review found no further source/test defect after these changes. '
              'The newly discovered full-environment manifest-capacity defect is recorded here '
              'for the lead to file; GitHub writes are prohibited by this assignment.', '',
              'Reproduce the report from saved evidence:', '', '```text',
              str(E.parent / 'data-sheets-schema/.venv/bin/python') + ' -B ' + str(Path(__file__).resolve()),
              '```', '']
    text = '\n'.join(lines)
    assert chr(64) not in text
    for target in re.findall(r'`([^`]+)`', text):
        if target.startswith('/'):
            assert Path(target).exists(), 'handoff names a missing path: ' + target
    additions = [line[1:] for line in git('diff', BASE, '--').decode().splitlines()
                 if line.startswith('+') and not line.startswith('+++')]
    assert chr(64) not in '\n'.join(additions)
    assert all(entry['unchanged'] for path, entry in data['identities'].items() if path != MANIFEST)
    assert all(run['outcome']['process_group_gone'] for run in runs.values())
    if not REPORT.exists():
        with REPORT.open('x') as stream:
            stream.write(text)
    assert REPORT.read_text() == text
    value = dict(path=str(REPORT), sha256=sha(REPORT.read_bytes()), bytes=REPORT.stat().st_size, head=data['head'])
    write(SCRATCH / 'handoff-identity.json', value)
    print(json.dumps(dict(**value, pin_proposals=data['pin_proposals']), indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['--manifest-capacity']:
        manifest_capacity()
    elif sys.argv[1:] == ['--compact-capacity']:
        compact_capacity()
    elif sys.argv[1:] == ['--inspect']:
        for name, run in ledger(persist=False)['runs'].items():
            failures = [case for case in run['results']['cases'] if case['category']]
            print(json.dumps(dict(run=name, totals=run['results']['totals'], files=run['files'],
                categories=dict(Counter(case['category'] for case in failures)),
                other_failures=[case for case in failures if case['category'] == 'other']), indent=2))
    else:
        report(ledger())
