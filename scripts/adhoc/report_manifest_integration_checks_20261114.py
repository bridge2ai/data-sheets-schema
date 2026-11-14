"""Summarize saved JUnit and the actual interpreter namespace for D148.

Inputs: assigned scratch logs/XML and this checkout. Outputs: JSON and generated
Markdown per-test failure ledger and counts; namespace witness when requested.
Serves the Codex 196 integration handoff, 2026-11-14. No gates are patched.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ('manifest', 'manifest-boundaries', 'registration', 'builder', 'retention', 'scanner')


def classify(detail):
    if 'own distribution exclusion requires the exact pinned project namespace' in detail:
        return 'mixed project namespace; manifest refuses before later validation'
    if 'unsupported v2 render producer: prepare' in detail:
        return 'scanner v2 producer AST rejects v3 preparation; not a pin-only failure'
    if 'unsupported v2 render producer: render_native_shared' in detail:
        return 'scanner v2 CLI AST rejects v3 CLI; not a pin-only failure'
    if 'unsupported v2 render CLI' in detail:
        return 'scanner v2 CLI AST rejects v3 CLI; not a pin-only failure'
    if 'v2 envelope authority source changed' in detail:
        return 'scanner source pin refusal; later checks unverified'
    if '00b0f717' in detail and 'f865fea7' in detail:
        return 'direct H1 authority hash assertion; unapplied pin rotation, later scanner proof unverified'
    return 'inspect saved traceback; not attributed solely to pins'


def namespace(scratch):
    import data_sheets_schema
    from data_sheets_schema import native_environment_manifest as manifest
    pth = Path(sys.prefix) / ('lib/python' + str(sys.version_info.major) + '.' + str(sys.version_info.minor)) / 'site-packages/data_sheets_schema.pth'
    try:
        manifest._own_source_authority()
        outcome = {'accepted': True}
    except ValueError as exc:
        outcome = {'accepted': False, 'exception': type(exc).__name__, 'message': str(exc)}
    result = {'python': sys.executable, 'prefix': sys.prefix,
        'package_paths': list(data_sheets_schema.__path__), 'expected_package_path': str(ROOT / 'src/data_sheets_schema'),
        'manifest_module': manifest.__file__, 'pth': {'path': str(pth), 'content': pth.read_text(),
            'sha256': hashlib.sha256(pth.read_bytes()).hexdigest()}, 'check': outcome,
        'scope': 'Read-only inspection; no import path repair or production check bypass.'}
    (scratch / 'namespace-witness.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


def summarize(scratch):
    cases, groups = [], []
    for stage in REQUIRED:
        path = scratch / (stage + '.xml')
        if not path.is_file():
            continue
        document = ET.parse(path)
        counts = Counter()
        for case in document.iter('testcase'):
            failure = case.find('failure')
            error = case.find('error')
            skip = case.find('skipped')
            state = 'failed' if failure is not None else 'error' if error is not None else 'skipped' if skip is not None else 'passed'
            detail = ''.join((entry.text or '') for entry in (failure, error) if entry is not None)
            row = {'stage': stage, 'node': case.get('classname', '') + '::' + case.get('name', ''),
                'status': state, 'seconds': float(case.get('time', 0)), 'detail': detail,
                'attribution': classify(detail) if detail else None, 'junit': str(path)}
            counts[state] += 1
            cases.append(row)
        invocation = json.loads((scratch / (stage + '-invocation.json')).read_bytes())
        groups.append({'stage': stage, 'seconds': invocation.get('seconds'), 'returncode': invocation.get('returncode'),
            **{key: counts[key] for key in ('passed', 'failed', 'error', 'skipped')}, 'cases': sum(counts.values())})
    report = {'groups': groups, 'cases': cases,
        'totals': dict(Counter(row['status'] for row in cases)),
        'failure_reasons': dict(Counter(row['attribution'] for row in cases if row['detail'])),
        'missing_stages': [name for name in REQUIRED if name not in {group['stage'] for group in groups}]}
    (scratch / 'test-results.json').write_text(json.dumps(report, indent=2) + '\n')
    (scratch / 'test-unclassified.json').write_text(json.dumps([
        row for row in cases if row['attribution'] == 'inspect saved traceback; not attributed solely to pins'], indent=2) + '\n')
    summary = ['| Stage | Passed | Failed | Errors | Skipped | Seconds |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for group in groups:
        summary.append('| ' + ' | '.join(str(group[name]) for name in ('stage', 'passed', 'failed', 'error', 'skipped')) + ' | ' + format(group['seconds'], '.2f') + ' |')
    (scratch / 'test-summary.md').write_text('\n'.join(summary) + '\n')
    reasons = ['| Failure/error attribution | Cases |', '| --- | ---: |']
    reasons.extend('| ' + name + ' | ' + str(count) + ' |' for name, count in report['failure_reasons'].items())
    (scratch / 'test-failure-summary.md').write_text('\n'.join(reasons) + '\n')
    failures = ['| Test | Result | Attribution |', '| --- | --- | --- |']
    for row in cases:
        if row['detail']:
            failures.append('| ' + row['node'].replace('|', '\\|').replace(chr(64), '&#64;') + ' | ' + row['status'] + ' | ' + row['attribution'] + ' |')
    (scratch / 'test-failures.md').write_text('\n'.join(failures) + '\n')
    print(json.dumps({key: report[key] for key in ('groups', 'totals', 'failure_reasons', 'missing_stages')}, indent=2))


def handoff(scratch, destination):
    def read(name):
        return json.loads((scratch / name).read_bytes())
    def git(*args):
        return subprocess.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout.decode().strip()
    tests = read('test-results.json')
    if tests['missing_stages']:
        raise ValueError('required test stages remain unreported')
    inventory = read('merge-file-inventory.json')
    pins = read('pin-inventory.json')
    controller = read('controller-verification.json')
    assert not controller['failures']
    conflicts = (scratch / 'conflicted-files.txt').read_text().splitlines()
    commits = git('log', '--first-parent', '--format=%H %s', inventory['candidate'] + '..HEAD')
    required = ['test-summary.md', 'test-failure-summary.md', 'test-failures.md', 'test-results.json', 'pin-inventory.md',
        'pin-inventory.json', 'pin-proposal-review-only.diff', 'excluded-files.md',
        'merge-file-inventory.json', 'merge-commit.log', 'namespace-witness.json',
        'controller-verification.json',
        'merge-canary.log', 'merge-canary.xml', 'prefix-canary.log', 'prefix-canary.xml']
    for name in required:
        assert (scratch / name).is_file() and (scratch / name).stat().st_size
    incoming_root = ROOT.parent / 'codex-native-environment-manifest-20261113'
    for row in inventory['excluded']:
        assert (incoming_root / row['path']).is_file()
        git('cat-file', '-e', inventory['incoming'] + ':' + row['path'])
    for row in pins['rows']:
        assert (ROOT / row['target']).is_file()
    rotated = pins['proposed_rotations']
    changed = rotated[0]
    status = ', '.join(str(count) + ' ' + state for state, count in tests['totals'].items())
    text = f'''Merge done: committed merge of `{inventory['incoming']}` into `{inventory['candidate']}`, with {len(conflicts)} conflicted files resolved. No pinned value was changed. Two review-only references to the authority source digest need `{changed['current_pin']}` to become `{changed['proposed_pin']}`: the integrated specificity-scanner summary and its H1 assertion. Controller manifests, SOURCES_SHA256, the wire controller pin, and CONTROL_SHA remain exact and unchanged. Version 3 is implemented in the merged constructors and adapted builder/rehearsals, but is **not end-to-end verified or ready for acceptance**: the mandated interpreter exposes two project namespaces, and the scanner has v2-only structural contracts. The observed failures are not all pin-only.

Branch: `codex/native-manifest-integration-20261114`. Worktree: `{ROOT}`. Head: `{git('rev-parse', 'HEAD')}`. Scratch: `{scratch}`. No push, PR, GitHub write, provider call or real native-binary call was made. The owner branch was only read. The four protected files match the candidate byte for byte; their full hashes are in the pin inventory.

Local commits, newest first:

```
{commits}
```

The wire conflict retains the candidate's current controller manifest pin while taking v3 document vocabulary, authority version 2, and explicit read-only historical v2 parsing. The retention conflict keeps the candidate's module isolation and adds the incoming v3 wire/carrier imports. The merge message records both. The other source changes are additive environment binding/reverification and the v3 document transition; the candidate CI roster, run limits, helper cache, power/admission and reviewed reconstruction checks are retained. This is code review evidence, not a passed dynamic gate matrix.

The builder still validates explicit project/profile, bundle/chunks, schemas, selection, receipt policy, bounds and physical paths and retains its offline audit barrier. It now captures a fresh environment manifest, records its exact pin and v3/authority-v2 contract in the inventory/status, and supplies the manifest path for saved preparation. The saved-input preparation/registration constructors produce v3 documents; the chain tests require the pin in preparation and the preparation embedded in execution. The prefix remains a dependency stop until the existing owner/runtime inputs exist. It never manufactures a preparation or authorization from missing inputs.

Verification used the assignment's interpreter, PYTHONPATH, external basetemp and at most two xdist workers per command, never more than four concurrently. Commands and durations are saved in each stage's invocation JSON. The initial merge canary passed as recorded in `merge-canary.log`. The real prefix canary persisted its refusal/status and failed before manifest output; it did not prove a valid v3 prefix. Subsequent required suite runs are diagnostic evidence, not acceptance. Required-suite totals: {status}.

{(scratch / 'test-summary.md').read_text()}
{(scratch / 'test-failure-summary.md').read_text()}
The all-project prefix tests deliberately permit production refusals; a pass there does not establish successful manifest output. Likewise a fixture error prevents the corresponding later assertions from being exercised. The complete per-test failure ledger is `{scratch / 'test-failures.md'}`; exact tracebacks and case timings are in `{scratch / 'test-results.json'}` and the named XML/log files. No failing assertion, production validation, pin, or timeout was weakened.

Read-only review findings for the lead to file/triage (GitHub writes are outside this assignment):

1. The mandated interpreter's data_sheets_schema.pth contributes the primary checkout alongside this worktree. The saved namespace witness lists both roots and the exact .pth hash. The manifest correctly refuses its own-project exclusion. Do not remove that refusal or edit the primary environment to obtain a pass. Recommendation: approve a separately isolated interpreter/import environment, as used by the manifest owner's runner, and rerun the v3 prefix, preparation, dispatch and full-chain checks there. That environment change was not made here.
2. The current scanner compares the CLI and preparer against exact v2 AST templates before checking its integrated source hashes. V3 adds the required manifest argument and field and changes the closed wire vocabulary. Recommendation: review a v3 structural proof and negative mutation tests first; then the lead can apply the identity proposal. The proposal below is a necessary identity update, not a claim that changing hashes fixes the scanner. Historical v2 summaries must remain historical.

Pin proposal (unapplied): `{scratch / 'pin-proposal-review-only.diff'}`. Full old/current/proposed values, including every controller manifest module and both effective scanner summaries, follow. The historical base summary intentionally retains its historical values even where they differ from current source. The changed authority source restores the caller's sys.path after loading the exact pinned helpers, before yielding controls; its source-only finder remains active.

The candidate's independent verifier also passed: `{scratch / 'controller-verification.json'}`, produced by the existing `scripts/adhoc/verify_controller_pin_rotation_20261113.py` with this worktree as its argument. It verifies controller modules against working bytes and their recorded source commit, controller constants, CONTROL_SHA and protected-file hashes. It reports scanner digest differences without accepting them.

{(scratch / 'pin-inventory.md').read_text()}
Excluded from the merge result: {len(inventory['excluded'])} incoming files, {inventory['excluded_lines']} lines. Retained incoming paths: {len(inventory['kept'])}. Excluded bytes remain in the merge's incoming parent and the owner worktree `{incoming_root}`; the table paths below refer to that incoming tree, where each was checked. A true merge retains that history but removes these files from the candidate diff. The two retained adhoc scripts are required by kept tests; their test cohorts were exercised, not their live gate launch paths.

{(scratch / 'excluded-files.md').read_text()}
Reproduction/provenance: all helpers below are committed on this branch. The exclusion helper was run with plan, then one canary, then apply while MERGE_HEAD existed; it must not be rerun after the merge. Its saved input inventory is `merge-file-inventory.json`.

```
scripts/adhoc/stage_manifest_code_merge_20261114.py
scripts/adhoc/run_manifest_integration_checks_20261114.py
scripts/adhoc/audit_manifest_integration_pins_20261114.py
scripts/adhoc/report_manifest_integration_checks_20261114.py
```

Commands used to generate all tables from saved JSON/XML:

```
PYTHONDONTWRITEBYTECODE=1 {ROOT.parents[1] / 'data-sheets-schema/.venv/bin/python'} scripts/adhoc/audit_manifest_integration_pins_20261114.py --candidate {inventory['candidate']} --scratch {scratch}
PYTHONDONTWRITEBYTECODE=1 {ROOT.parents[1] / 'data-sheets-schema/.venv/bin/python'} scripts/adhoc/report_manifest_integration_checks_20261114.py --scratch {scratch}
PYTHONDONTWRITEBYTECODE=1 {ROOT.parents[1] / 'data-sheets-schema/.venv/bin/python'} scripts/adhoc/report_manifest_integration_checks_20261114.py --scratch {scratch} --handoff {destination}
```

The per-test failure ledger is generated from saved JUnit by the same reporting helper, alongside test-results.json. It encodes at-sign characters in test parameter names for this handoff convention. No launch/capture/reservation acceptance is claimed.
'''
    assert chr(64) not in text
    destination.write_text(text)
    result = {'handoff': str(destination), 'bytes': destination.stat().st_size,
              'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
    (scratch / 'handoff-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--namespace', action='store_true')
    parser.add_argument('--handoff', type=Path)
    args = parser.parse_args()
    if args.handoff:
        handoff(args.scratch.resolve(strict=True), args.handoff)
    elif args.namespace:
        namespace(args.scratch.resolve(strict=True))
    else:
        summarize(args.scratch.resolve(strict=True))


if __name__ == '__main__':
    main()
