"""Report the lead's manifest helper cost ruling, 2026-11-14.

Inputs: the assigned worktree, its committed pre-ruling base and cost-* scratch
cohorts. Outputs: JSON audit/results, a review-only scanner pin patch and the
answer-first continuation in the assigned lead handoff. No GitHub or network.
"""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
BASE = '24c8774f85a75b5cdd2b69fa2b396c5e1d3304e9'
SCRATCH = ROOT.parent / 'scratch-native-manifest-integration-20261114/continuation'
HANDOFF = (ROOT.parent / 'codex-development-efficiency-20261111/notes/'
           'development_efficiency_20261111/handoffs/codex-native-manifest-integration-20261114.md')
SCAN = '.claude/skills/d4d-generation-specificity-audit/scan.py'
MANIFEST = 'src/data_sheets_schema/native_environment_manifest.py'
PROTECTED = ('src/data_sheets_schema/shared_generation.py', 'src/data_sheets_schema/api_runner.py',
             'src/download/prompts/canonical_hashes.yaml', 'tests/utils/run_spec_boundary_contracts.json')
PIN_FILES = ('src/data_sheets_schema/native_controller_sources_v1.json',
             'src/data_sheets_schema/native_controller_sources_v2.json',
             'src/data_sheets_schema/native_attribution_controller.py',
             'src/data_sheets_schema/native_attribution_controller_v2.py',
             'tests/fixtures/native_d128_approved.json')
GATES = ('ecbc7d737', '994ac2ea0', '719d2d226', '28e6d5688', '1b5629f0f')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '--no-replace-objects', *args], cwd=ROOT)


def save(name, data):
    path = SCRATCH / name
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    return path


def functions(path):
    return {node.name: node for node in ast.parse(path.read_bytes()).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def callsites():
    files = {
        MANIFEST: {'verify': ('full by default; light only explicitly', 'Pin/canonical checks always; process-only full memo'),
                   'write': ('full', 'Registration creates the manifest and retains its allowed verifying pass')},
        'src/data_sheets_schema/native_execution_registration_v2.py': {
            name: ('full; light in explicit helper scope', 'Preparation reconstruction; default remains full')
            for name in ('_environment_pin', 'prepare', '_prepare', 'verify_preparer')},
        'src/data_sheets_schema/native_shared_registration_orchestration.py': {
            '_recheck_verified': ('full', 'Launch/dispatch recheck cannot inherit light mode')},
        'src/data_sheets_schema/native_shared_capture_orchestration.py': {
            '_base': ('explicit caller mode, full default', 'Bounded context restored on every exit'),
            '_load_live': ('explicit caller mode, full default', 'Forwards helper choice; parent fallback remains full'),
            '_load': ('full', 'Independent final/gate/recorded consumers'),
            'capture_stage': ('light', 'Advance helper, including publication recapture'),
            'selected_receipt_paths': ('light', 'Live receipt helper input reconstruction'),
            'live_receipt_block': ('light', 'Live receipt helper assessment'),
            'live_provenance_block': ('full', 'Final recording exception in the ruling')},
    }
    rows = []
    for relative, owners in files.items():
        definitions = functions(ROOT / relative)
        for name, (mode, why) in owners.items():
            node = definitions[name]
            calls = [call for call in ast.walk(node) if isinstance(call, ast.Call)
                     and ((isinstance(call.func, ast.Attribute) and call.func.attr in ('verify', 'verification_scope'))
                          or isinstance(call.func, ast.Name) and call.func.id in ('generate', 'verify', '_base', '_load_live'))]
            rows.append({'file': relative, 'line': min((call.lineno for call in calls), default=node.lineno),
                         'function': name, 'mode': mode, 'why': why,
                         'calls': [ast.unparse(call) for call in calls]})
    return rows


def audit():
    git('merge-base', '--is-ancestor', BASE, 'HEAD')
    changed = git('diff', '--name-only', BASE, 'HEAD').decode().splitlines()
    assert not git('status', '--porcelain').strip(), 'commit the ruling before reporting its final head'
    preserved = {}
    for path in (*PROTECTED, *PIN_FILES):
        raw = (ROOT / path).read_bytes()
        assert raw == git('show', BASE + ':' + path), path
        preserved[path] = sha(raw)
    for commit in GATES:
        result = subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT)
        assert result.returncode == 1, commit
    # The lead owns the separate derivation-scope change. Only our manifest
    # call may differ within verify_preparer.
    path = 'src/data_sheets_schema/native_execution_registration_v2.py'
    before = ast.parse(git('show', BASE + ':' + path))
    after = ast.parse((ROOT / path).read_bytes())
    def without_manifest_call(tree):
        node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'verify_preparer')
        node.body = [item for item in node.body if not (isinstance(item, ast.Expr)
                     and isinstance(item.value, ast.Call)
                     and ast.unparse(item.value.func) == 'native_environment_manifest.verify')]
        return ast.dump(node, include_attributes=False)
    assert without_manifest_call(before) == without_manifest_call(after)
    source = (ROOT / SCAN).read_text()
    tree = ast.parse(source)
    node = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == '_NATIVE_V3_RENDER_SOURCES' for target in node.targets))
    old = next(ast.literal_eval(value) for key, value in zip(node.keys, node.values)
               if key is not None and ast.literal_eval(key) == MANIFEST)
    new = sha((ROOT / MANIFEST).read_bytes())
    assert old == sha(git('show', BASE + ':' + MANIFEST)), 'held pin must still match the pre-ruling source'
    assert old != new, 'the new scanner identity must remain a proposal for the lead'
    assert source.count(old) == 1
    proposal = ''.join(difflib.unified_diff(source.splitlines(keepends=True),
        source.replace(old, new).splitlines(keepends=True), fromfile='a/' + SCAN, tofile='b/' + SCAN))
    (SCRATCH / 'cost-ruling-pin-proposal.patch').write_text(proposal)
    helper_tree = ast.parse((ROOT / 'src/data_sheets_schema/native_shared_policy.py').read_bytes())
    roster = next(node.value.args[0] for node in helper_tree.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == 'HELPERS' for target in node.targets))
    git('diff', '--check', BASE, 'HEAD')
    return {'head': git('rev-parse', 'HEAD').decode().strip(), 'base': BASE,
            'changed_files': {path: sha((ROOT / path).read_bytes()) for path in changed},
            'preserved': preserved, 'gate_commits_excluded': list(GATES),
            'verify_preparer_only_manifest_call_changed': True,
            'scanner_pin': {'path': MANIFEST, 'before': old, 'proposed': new, 'applied': False},
            'call_sites': callsites(), 'helper_roster': sorted(ast.literal_eval(roster)),
            'commits': git('log', '--format=%H %s', BASE + '..HEAD').decode().splitlines()}


def results():
    rows = []
    for directory in sorted(SCRATCH.glob('cost-*')):
        if not directory.is_dir() or not (directory / 'outcome.json').exists():
            continue
        outcome = json.loads((directory / 'outcome.json').read_bytes())
        plan = json.loads((directory / 'plan.json').read_bytes())
        counts = dict(passed=0, failed=0, errors=0, skipped=0)
        failures, junit_seconds = [], None
        progress = re.findall(r'^\[gw\d+\].*?\b(PASSED|FAILED|ERROR|SKIPPED) (tests/[^\n]+)',
                              (directory / 'pytest.log').read_text(), re.MULTILINE)
        xml = directory / 'pytest.xml'
        if xml.exists():
            tree = ET.parse(xml)
            junit_seconds = sum(float(suite.get('time', '0')) for suite in tree.iter('testsuite'))
            for case in tree.iter('testcase'):
                status = next((tag for tag in ('failure', 'error', 'skipped') if case.find(tag) is not None), 'passed')
                counts[{'failure': 'failed', 'error': 'errors'}.get(status, status)] += 1
                if status != 'passed':
                    element = case.find(status)
                    failures.append({'case': case.get('classname', '') + '::' + case.get('name', ''),
                                     'status': status, 'message': element.get('message', ''), 'detail': element.text})
        rows.append({'name': directory.name, 'path': str(directory), 'outcome': outcome, 'counts': counts,
                     'junit_seconds': junit_seconds, 'failures': failures, 'source_commit': plan['source_commit'],
                     'workers': plan['workers'], 'junit_present': xml.exists(), 'logged_progress': progress,
                     'source_delta_to_head': git('diff', '--name-only', plan['source_commit'], 'HEAD').decode().splitlines(),
                     'production_delta_to_head': git('diff', '--name-only', plan['source_commit'], 'HEAD',
                         '--', 'src', SCAN, 'scripts/build_native_canary_packet.py',
                         'scripts/adhoc/run_manifest_continuation_tests_20261114.py').decode().splitlines()})
    costs = [{'path': str(path), **json.loads(path.read_bytes())}
             for path in sorted({path.resolve() for path in SCRATCH.glob('cost-*/cases/**/manifest-cost.json')})]
    return rows, costs


def markdown(data, cohorts, costs):
    current = [row for row in cohorts if row['name'] in (
        'cost-mode-committed', 'cost-installed-canary', 'cost-builder-prefix',
        'cost-live-boundaries', 'cost-concurrency-and-capture')]
    held = [row['name'] for row in current if row['outcome']['returncode'] != 0]
    lines = ['Continuation — explicit manifest modes and process-local full verification reuse are implemented; '
             'integration acceptance is held. '
             'Existing helper verification calls use light mode. '
             'The scanner manifest identity is a review-only proposal, not an applied rotation. '
             'D128 remains the lead’s final-head step. The retained earlier timeout and freshness failures '
             'are historical results, not silently relabeled as passes.', '',
             f"Head: `{data['head']}`. Worktree: `{ROOT}`. Evidence: `{SCRATCH}`.", '',
             'Current nonpassing cohorts: ' + ', '.join(held) + '. The builder prefix hit its unchanged '
             '180-second subprocess limit. The additional live-boundary run reached its 3600-second '
             'deadline: dependency loading logged a pass, but dispatch has no terminal result. Its '
             'cleanup flag remains false after forced cleanup, even though no observed surviving PIDs '
             'were reported. This is incomplete integration evidence, not acceptance. No timeout was relaxed.', '',
             'Full verification defaults to `mode="full"`. Its key includes the exact pin, interpreter '
             'identity/executable, prefix, import roots and process identity. Source-loaded module copies '
             'share the in-memory holder; a fork resets it before touching the inherited lock. File identities '
             'are compared before and after the initial regeneration to close the cache-admission race. Nothing is '
             'stored on disk as a verification cache. Cache hits still read the pin, validate canonical '
             'bytes, check RECORD hashes and lstat the live inventory. Changed file identities refuse '
             'without a second payload regeneration. Failed full checks remain refused for that key.', '',
             'Light mode hashes RECORD metadata, checks the distribution roster and all included RECORD '
             'and unowned lstat sizes/types, and performs no payload hashing. Same-size payload content '
             'changes are intentionally outside its guarantee. The closed v1 manifest now includes '
             '`file_stats` and unowned `stat` baselines, including explicit absence for unhashed RECORD '
             'entries. Earlier synthetic manifests require regeneration. Bytecode exclusions remain intact.', '',
             f"The checked-out `HELPERS` roster contains {len(data['helper_roster'])} names. The change routes "
             'the existing advance and live receipt reconstruction checks to light mode. Helpers that '
             'never reconstructed a manifest keep their existing command spellings; no new wrapper or '
             'validator subprocess is introduced. Final recording and independent recorded/gate consumers '
             'retain full mode. Scope decision for the lead: confirm this existing-check interpretation, or '
             'assign new wrappers for helper commands that currently have no manifest input/check. '
             'The latter would change command grammar; it is not implemented or claimed here.', '',
             'The new checks do not establish complete-helper performance under the 600-second Bash limit. '
             'Cached full checks still pay for a light census. The separate derivation-scope work remains '
             'necessary to evaluate together with this change. The earlier full registration, builder, '
             'retention and scanner matrices below predate this ruling; they are not current-head acceptance. '
             'After the failed builder canary, no builder fan-out was run. The explicit dispatch-mode '
             'unit test proves mode selection before effects; it does not replace the incomplete live test.', '',
             '| File | Line | Function | Mode | Why |', '| --- | ---: | --- | --- | --- |']
    for row in data['call_sites']:
        lines.append(f"| {row['file']} | {row['line']} | {row['function']} | {row['mode']} | {row['why']} |")
    lines += ['', '| Cohort | Workers | RC | Passed | Failed | Errors | Skipped | Parent seconds | JUnit seconds | Cleanup verified |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |']
    for row in cohorts:
        count, out = row['counts'], row['outcome']
        lines.append(f"| {row['name']} | {row['workers']} | {out['returncode']} | " + ' | '.join(str(count[key]) for key in ('passed', 'failed', 'errors', 'skipped'))
                     + f" | {out['seconds']:.2f} | {row['junit_seconds']} | {out['cleanup_verified']} |")
    lines += ['', 'All original cohort logs, JUnit, source heads, origin checks and cleanup records are retained. '
              'The early unit development cohorts predate the ruling commit; committed-source verification '
              'is identified by its recorded head in `cost-ruling-results.json`. Parent and JUnit clocks '
              'are reported separately. Counts are from completed JUnit files; zero counts on the interrupted '
              'cohort do not mean zero executed tests. Its partial progress is saved in the results JSON. '
              'No cross-environment speedup is inferred, and host load was not controlled. '
              'Source deltas in the JSON distinguish later regression-test/report edits from production changes.', '',
              '| Cost artifact | Operation | CPU seconds | Wall seconds | Full regenerations |',
              '| --- | --- | ---: | ---: | ---: |']
    for result in costs:
        for row in result['measurements']:
            lines.append(f"| {Path(result['path']).parent.name} | {row['operation']} | {row['cpu_seconds']:.6f} | "
                         f"{row['wall_seconds']:.6f} | {row['generate_calls']} |")
    for result in costs:
        lines += ['', f"Cost environment: {result['distributions']} distributions, {result['record_entries']} "
                  f"included RECORD entries and {result['unowned_files']} unowned files. Artifact: `{result['path']}`."]
    pin = data['scanner_pin']
    lines += ['', f"Scanner pin proposal for `{pin['path']}`: `{pin['before']}` → `{pin['proposed']}`. "
              f"Exact review-only patch: `{SCRATCH / 'cost-ruling-pin-proposal.patch'}`. "
              'The production scanner continues to refuse the unrotated identity. The dedicated scanner '
              'tests apply the proposed identity only in memory and exercise positive mode propagation '
              'and negative mutations. Controller manifests/pins, prompt pins, the four protected files '
              'and the D128 fixture are unchanged.', '',
              'The separate lead derivation-scope work is untouched: an AST comparison confirms that '
              '`verify_preparer` differs only at the manifest call. Owner history remains integrated; '
              'the five gate-package commits remain excluded.', '',
              'Review findings for the lead’s issue filing: the new stat inventory moved an old payload '
              'mutation refusal to an earlier diagnostic; the diagnostic now names payload changes. '
              'One mutation fixture needed to forward the explicit light-census argument. Review found '
              'a RECORD read/stat race; the RECORD identity is now bound before its read and rechecked '
              'after the census, with a passing negative canary. A second cache-admission race is covered '
              'by a negative test that mutates a payload immediately after generation; the failed result '
              'stays refused without another generation. No GitHub write was made.', '',
              'Additional findings for the lead: the builder timeout and incomplete dispatch boundary remain '
              'open. Review also tightened concurrent first-holder initialization; the added concurrency '
              'test exercises two simultaneous full calls and requires one regeneration. Recommend evaluating '
              'the remaining census cost together with the lead’s derivation-scope change before rerunning '
              'the full acceptance matrix; keep the current timeouts and freshness checks intact.', '',
              'Commits:', '', '```', *data['commits'], '```', '',
              'Report provenance (all tables are generated from saved audit/results data):', '', '```bash',
              'python -S -P -B scripts/adhoc/report_manifest_cost_ruling_20261114.py --handoff', '```', '',
              'Recorded nonpassing cases:', '']
    for row in cohorts:
        if row['outcome']['returncode'] != 0 and not row['failures']:
            lines.append(f"- {row['name']}: return code {row['outcome']['returncode']}; "
                         f"interrupted={row['outcome']['interrupted']}; completed JUnit={row['junit_present']}; "
                         f"logged progress={row['logged_progress']}.")
        for failure in row['failures']:
            message = failure['message']
            timeout = re.search(r'timed out after [0-9.]+ seconds', message)
            message = ('subprocess.TimeoutExpired: ' + timeout.group()) if timeout else message[:400]
            lines.append(f"- {row['name']}: `{failure['case']}` — {message}")
    return '\n'.join(lines).replace('@', '&#64;') + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handoff', action='store_true')
    args = parser.parse_args()
    data, (cohorts, costs) = audit(), results()
    paths = [ROOT / path for path in (*data['changed_files'], *data['preserved'])]
    paths += [ROOT / row['file'] for row in data['call_sites']]
    paths += [Path(row['path']) for row in cohorts + costs]
    paths += [Path(row['pin']['path']) for row in costs]
    assert all(path.exists() for path in paths), 'named evidence/source path is missing'
    for result in costs:
        raw = Path(result['pin']['path']).read_bytes()
        assert len(raw) == result['pin']['bytes'] and sha(raw) == result['pin']['sha256']
    save('cost-ruling-audit.json', data)
    save('cost-ruling-results.json', {'cohorts': cohorts, 'costs': costs})
    # Render from the saved data files, which are the table provenance.
    saved_data = json.loads((SCRATCH / 'cost-ruling-audit.json').read_bytes())
    saved_results = json.loads((SCRATCH / 'cost-ruling-results.json').read_bytes())
    report = markdown(saved_data, saved_results['cohorts'], saved_results['costs'])
    (SCRATCH / 'cost-ruling.md').write_text(report)
    if args.handoff:
        assert costs, 'complete the installed-environment cost canary first'
        backup = SCRATCH / 'cost-ruling-prior-handoff.md'
        if not backup.exists():
            backup.write_bytes(HANDOFF.read_bytes())
        raw = (report + '\n---\n\nEarlier continuation (historical):\n\n' + backup.read_text()).encode()
        assert b'@' not in raw
        assert all(Path(result['path']).is_file() for result in costs)
        HANDOFF.write_bytes(raw)
        stored = HANDOFF.read_bytes()
        assert stored == raw and stored
        verification = {'path': str(HANDOFF), 'sha256': sha(stored), 'bytes': len(stored),
                        'prior_sha256': sha(backup.read_bytes()), 'head': data['head']}
        save('cost-ruling-handoff-verification.json', verification)
        print(json.dumps(verification, indent=2))
    else:
        print(json.dumps({'head': data['head'], 'cohorts': [row['name'] for row in cohorts],
                          'costs': len(costs), 'pin': data['scanner_pin']}, indent=2))


if __name__ == '__main__':
    main()
