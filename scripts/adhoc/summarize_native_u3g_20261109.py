"""U3-G exact evidence reconciliation and proposed owner bundle, 2026-11-09.

Inputs: retained sequential runs, scanner JSON, raw parity and four packet files.
Outputs: counts, exact-node ledger, artifact hashes and independent gate flags
under scratch-native-u1u3/u3g. No packet installation or network/provider/native
execution. Failed and incomplete attempts remain visible, including the legacy
U5 full-array comparison separately from the saved-main exact-nine gate.
"""
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('u3g_summary_base',
    ROOT / 'scripts/adhoc/summarize_native_u3f_20261109.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
s.OUT = s.SCRATCH / 'u3g'
BASE = '77bfa23368af201b77585f334ed0456ed1d40f01'
SAVED_MAIN = 'cf50d9a1c059f3b5030103378ccef33619475dde'
TARGETS = {
    'shared_generation': 'src/data_sheets_schema/shared_generation.py',
    'api_runner_companion': 'src/data_sheets_schema/api_runner.py',
    'canonical_hashes': 'src/download/prompts/canonical_hashes.yaml',
    'run_spec_boundary_contracts': 'tests/utils/run_spec_boundary_contracts.json',
}
REQUIRED_LABELS = tuple('worktree-' + name for name in (
    'canary', 'u4', 'u4b', 'neutral', 'u5-core', 'u5-typed', 'u5-receipts',
    'u5-specificity', 'u5-delegated', 'u5-registration', 'u5-readback', 'u5-scanner',
    'parity-canary', 'parity')) + tuple('composed-' + name for name in (
    'canary', 'd114', 'f2-core', 'f2-delegated', 'f2-specificity', 'u5-core',
    'u5-typed', 'u5-receipts', 'u5-registration', 'u5-readback', 'parity-canary', 'parity'))
ENV = dict(PATH='/usr/bin:/bin', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='',
    GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null',
    GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
GIT = ['/usr/bin/git', '--no-replace-objects', '-c', 'core.hooksPath=/dev/null',
       '-c', 'core.fsmonitor=false', '-c', 'protocol.allow=never']


def need(condition, message):
    if not condition:
        raise ValueError(message)


def quiet():
    if os.path.lexists(ROOT.parent / 'plans/native_quiet_window.lock'):
        raise RuntimeError('quiet window is active')


def physical(path, within):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path
         and path.is_relative_to(within), 'nonphysical or unassigned evidence: ' + str(path))
    return path


def git(*args, cwd=ROOT):
    quiet()
    result = subprocess.run([*GIT, *args], cwd=cwd, env=ENV,
        capture_output=True, check=True, timeout=60)
    quiet()
    return result.stdout


def load(path):
    raw = Path(path).read_bytes()
    need(bool(raw), 'empty evidence: ' + str(path))
    return json.loads(raw)


def scans(before_label, after_label, composed_label):
    labels = (before_label, after_label, composed_label)
    paths = [physical(s.OUT / name / 'scanner.json', s.OUT) for name in labels]
    reports = [load(path) for path in paths]
    runs = [load(path.parent / 'run.json') for path in paths]
    need(runs[0]['source_commit'] == runs[1]['source_commit'] == SAVED_MAIN,
         'instrument comparison must use the same saved main')
    need(runs[0]['tool_commit'] == BASE, 'before scanner is not the U3-G base tool')
    need(runs[1]['tool_commit'] == runs[2]['tool_commit']
         and runs[1]['tool_sha256'] == runs[2]['tool_sha256'],
         'candidate scanner differs between saved main and composition')
    baseline_path = s.SCRATCH / 'baseline-scanner.json'
    baseline = load(baseline_path)
    before = reports[0]
    need(before['violations'] == baseline['violations'] and len(before['violations']) == 9,
         'before scanner did not retain the saved nine finding objects')
    rows = []
    for label, report, path, run in zip(labels, reports, paths, runs):
        need(run['exit_code'] in (0, 1) and run['tool_unchanged']
             and run.get('process_group_gone') is True and run['seconds'] < 3300,
             'scanner did not complete cleanly: ' + label)
        need(run['scanner_json_sha256'] == s.sha(path.read_bytes()),
             'scanner evidence changed: ' + label)
        rows.append(dict(label=label, hits=len(report['hits']), violations=len(report['violations']),
            finding_by_finding=[dict(saved=row,
                exact_matches=[actual for actual in report['violations'] if actual == row])
                for row in before['violations']],
            exact_nine_violation_parity=report['violations'] == before['violations'],
            extra_violations=[row for row in report['violations'] if row not in before['violations']],
            missing_violations=[row for row in before['violations'] if row not in report['violations']],
            full_hits_equal_to_before=report['hits'] == before['hits'],
            source_commit=run['source_commit'], tool_commit=run['tool_commit'],
            tool_sha256=run['tool_sha256'], scanner_json_sha256=s.sha(path.read_bytes()),
            run_json_sha256=s.sha((path.parent / 'run.json').read_bytes())))
    s.save('scanner-comparison.json', dict(baseline_sha256=s.sha(baseline_path.read_bytes()),
        baseline_tool=BASE, saved_main=SAVED_MAIN, results=rows,
        exact_nine_gate=all(row['exact_nine_violation_parity'] for row in rows),
        full_hits_equal_gate=all(row['full_hits_equal_to_before'] for row in rows),
        scope='Exact nine violation objects are the U3-G gate. Full hits are reported separately.'))
    print(json.dumps([{k: v for k, v in row.items() if k != 'finding_by_finding'} for row in rows]))


def completed_pass(row):
    return (row.get('returncode') == 0 and row.get('cleanup_verified') is True
        and row.get('worker', {}).get('source_origin_checks_passed') is True
        and row.get('interrupted') in (None, False) and row.get('workers', 99) <= 2
        and 0 <= row.get('seconds', 9999) < 3300
        and row['counts']['passed'] > 0
        and all(row['counts'][key] == 0 for key in ('failed', 'error', 'skipped')))


def summary():
    runs, ledger, hashes = [], [], {}
    directories = {path.parent for name in ('plan.json', 'outcome.json')
                   for path in s.OUT.glob('*/' + name)}
    for folder in sorted(directories):
        quiet()
        plan = load(folder / 'plan.json') if (folder / 'plan.json').is_file() else {}
        outcome = load(folder / 'outcome.json') if (folder / 'outcome.json').is_file() else {}
        counts = dict(passed=0, failed=0, error=0, skipped=0)
        xml = folder / 'pytest.xml'
        malformed_xml = None
        if xml.is_file():
            xml_sha256 = s.sha(xml.read_bytes())
            try:
                cases = list(ET.parse(xml).iter('testcase'))
            except ET.ParseError as error:
                cases = []
                malformed_xml = str(error)
            for case in cases:
                status, detail = 'passed', ''
                for tag, name in (('failure', 'failed'), ('error', 'error'), ('skipped', 'skipped')):
                    child = case.find(tag)
                    if child is not None:
                        status, detail = name, ET.tostring(child, encoding='unicode')
                        break
                counts[status] += 1
                parts = case.attrib.get('classname', '').split('.')
                cut = next((i for i, part in enumerate(parts) if part[:1].isupper()), len(parts))
                node = '/'.join(parts[:cut]) + '.py::' + '::'.join([*parts[cut:], case.attrib['name']])
                ledger.append(dict(run=folder.name, node=node, status=status, detail=detail,
                    xml_attributes=dict(case.attrib), xml_sha256=xml_sha256))
        row = dict(outcome, run=folder.name, source_commit=plan.get('source_commit'),
            source_root=plan.get('source_root'), deadline_seconds=plan.get('deadline_seconds'),
            workers=plan.get('workers', 99), counts=counts, malformed_xml=malformed_xml,
            missing_artifacts=[name for name in ('plan.json', 'outcome.json', 'pytest.xml')
                               if not (folder / name).is_file()])
        row['completed_pass'] = (not row['missing_artifacts'] and malformed_xml is None
                                 and completed_pass(row))
        runs.append(row)
        for name in ('outcome.json', 'pytest.xml', 'pytest.log', 'source-stability.json', 'plan.json',
                     'origins-before.json', 'origins-after.json', 'host-load.json',
                     'early-cutoff.json', 'u3g-cutoff.json'):
            path = folder / name
            if path.is_file():
                hashes[str(path)] = s.sha(path.read_bytes())
    protected = []
    for relative in (*TARGETS.values(), 'tests/utils/run_spec_boundaries.py'):
        before, after = git('show', BASE + ':' + relative), (ROOT / relative).read_bytes()
        protected.append(dict(path=relative, base=BASE, before=s.sha(before), after=s.sha(after),
                              unchanged=before == after))
    s.save('validation-summary.json', runs)
    s.save('exact-node-ledger.json', ledger)
    s.save('evidence-hashes.json', hashes)
    s.save('protected-files.json', protected)
    s.save('nonpassing-attempts.json', [row for row in runs if not row['completed_pass']])
    print(json.dumps([dict(run=row['run'], counts=row['counts'],
        completed_pass=row['completed_pass'], missing_artifacts=row['missing_artifacts']) for row in runs]))
    need(all(row['unchanged'] for row in protected), 'protected worktree bytes changed')


def parity(label):
    """Use the retained 14-file baseline and union the same-path canary/remainder.

    A repeated canary name must retain identical raw bytes; it cannot overwrite
    a differing output. This also supports a final cohort containing all 14.
    """
    need(re.fullmatch(r'(worktree|composed)(?:-r[0-9]+)?-parity', label), 'unknown U3-G parity label')
    baseline = {path.name: path for folder in ('parity2-canary-baseline', 'parity2-rest-baseline')
                for path in (s.SCRATCH / folder / 'parity').glob('*.txt')}
    actual = {}
    witnesses = {}
    for folder in (label + '-canary', label):
        for path in sorted((s.OUT / folder / 'parity').glob('*.txt')):
            if path.name in actual:
                need(actual[path.name].read_bytes() == path.read_bytes(),
                     'repeated parity output changed: ' + path.name)
            actual[path.name] = path
            witnesses[str(path)] = s.sha(path.read_bytes())
    need(len(baseline) == 14 and set(actual) == set(baseline), 'parity output roster is not 14/14')
    rows = [dict(name=name, baseline=str(before), candidate=str(actual[name]),
        baseline_sha256=s.sha(before.read_bytes()), candidate_sha256=s.sha(actual[name].read_bytes()),
        bytes=len(actual[name].read_bytes()), equal=before.read_bytes() == actual[name].read_bytes())
        for name, before in sorted(baseline.items())]
    s.save(label + '-comparison.json', rows)
    s.save(label + '-capture-hashes.json', witnesses)
    print(json.dumps(dict(label=label, total=len(rows), equal=sum(row['equal'] for row in rows))))
    need(all(row['equal'] for row in rows), 'raw instruction bytes differ')


def packets(manifest_path, *required_labels):
    quiet()
    manifest_path = physical(Path(manifest_path), s.OUT)
    manifest = load(manifest_path)
    tree = physical(manifest['tree'], s.OUT)
    bundle = physical(manifest['owner_bundle'], s.SCRATCH / 'owner-packets/u3g')
    rows = manifest['packets']
    need(len(rows) == 4 and {row['name']: row['target'] for row in rows} == TARGETS,
         'owner packet roster differs from the exact four targets')
    witnesses, patch_paths = {}, []
    for row in rows:
        name, target = row['name'], row['target']
        before, after = (ROOT / target).read_bytes(), (tree / target).read_bytes()
        frozen = load(ROOT / 'scripts/adhoc/native_u1_packets' / (name + '.json'))
        for suffix, expected in (('preimage', before), ('postimage', after)):
            path = physical(bundle / (name + '.' + suffix), bundle)
            need(path.read_bytes() == expected and s.sha(expected) == row[suffix + '_sha256'],
                 'packet ' + suffix + ' differs: ' + name)
            witnesses[str(path)] = s.sha(path.read_bytes())
        path = physical(bundle / (name + '.patch'), bundle)
        patch_paths.append(str(path))
        need(s.sha(path.read_bytes()) == row['patch_sha256'], 'packet patch changed: ' + name)
        witnesses[str(path)] = s.sha(path.read_bytes())
        metadata = physical(bundle / (name + '.json'), bundle)
        need(load(metadata) == row, 'packet metadata differs from manifest: ' + name)
        witnesses[str(metadata)] = s.sha(metadata.read_bytes())
        need(row['preimage_sha256'] == frozen['preimage_sha256']
             and row['u1_postimage_sha256'] == frozen['postimage_sha256']
             and row['u1_patch_sha256'] == frozen['patch_sha256'], 'frozen U1 identity differs: ' + name)
        need(row['changed_from_u1'] == (name == 'canonical_hashes')
             and (row['postimage_sha256'] != frozen['postimage_sha256']) == row['changed_from_u1'],
             'unexpected change from U1: ' + name)
        if not row['changed_from_u1']:
            need(path.read_bytes() == (ROOT / 'scripts/adhoc/native_u1_packets' / (name + '.patch')).read_bytes(),
                 'unchanged U1 patch was rewritten: ' + name)
    owner_review = physical(bundle / 'OWNER_REVIEW.md', bundle)
    review = owner_review.read_text()
    need(manifest['source_commit'] in review and all(name in review for name in TARGETS)
         and owner_review.stat().st_size > 0, 'owner review does not name the source and four packets')
    witnesses[str(owner_review)] = s.sha(owner_review.read_bytes())
    need(git('rev-parse', 'HEAD', cwd=tree).decode().strip() == manifest['composition_commit'],
         'private composition HEAD differs')
    git('diff-index', '--quiet', 'HEAD', '--', cwd=tree)
    git('apply', '--check', *patch_paths)
    git('apply', '--check', '--reverse', *patch_paths, cwd=tree)
    runs, ledger = load(s.OUT / 'validation-summary.json'), load(s.OUT / 'exact-node-ledger.json')
    by_label = {row['run']: row for row in runs}
    required_labels = required_labels or REQUIRED_LABELS
    required = [dict(label=label, present=label in by_label,
        completed_pass=by_label.get(label, {}).get('completed_pass', False),
        matches_current_source=by_label.get(label, {}).get('source_commit') ==
            manifest['composition_commit' if label.startswith('composed-') else 'source_commit'])
        for label in required_labels]
    comparison = load(s.OUT / 'scanner-comparison.json')
    parity = {}
    parity_labels = [label for label in required_labels if label.endswith('-parity')]
    need(len(parity_labels) == 2 and any(label.startswith('worktree-') for label in parity_labels)
         and any(label.startswith('composed-') for label in parity_labels), 'required parity pair missing')
    for label in parity_labels:
        path = s.OUT / (label + '-comparison.json')
        data = load(path) if path.is_file() else []
        parity[label] = dict(present=path.is_file(), total=len(data),
            equal=sum(row['equal'] for row in data),
            passed=len(data) == 14 and all(row['equal'] for row in data))
    legacy = [row for row in ledger if row['node'] ==
        'tests/test_native_u5_scanner_comparison.py::test_scanner_before_after_retains_complete_arrays_or_explicit_blocker']
    flags = dict(proposed_packet_artifacts_verified=True, protected_worktree_unchanged=
        all(row['unchanged'] for row in load(s.OUT / 'protected-files.json')),
        saved_main_exact_nine=comparison['exact_nine_gate'],
        scanner_composition_matches=comparison['results'][2]['source_commit'] == manifest['composition_commit'],
        raw_api_parity=parity,
        legacy_u5_full_array=dict(observed_cases=len(legacy),
            failed_cases=[row for row in legacy if row['status'] in ('failed', 'error')],
            note='Separate historical comparison; never substituted for the saved-main exact-nine gate.'),
        required_cohort_roster_supplied=bool(required_labels), required_cohorts=required,
        required_cohorts_complete=(bool(required) and all(row['present'] and row['completed_pass']
                                                       and row['matches_current_source'] for row in required)))
    evidence_names = ('validation-summary.json', 'exact-node-ledger.json', 'evidence-hashes.json',
        'protected-files.json', 'scanner-comparison.json', 'nonpassing-attempts.json',
        *(label + suffix for label in parity_labels
          for suffix in ('-comparison.json', '-capture-hashes.json')))
    witnesses.update({str(s.OUT / name): s.sha((s.OUT / name).read_bytes())
                      for name in evidence_names if (s.OUT / name).is_file()})
    result = dict(status='offline_evidence_reconciled_no_blanket_acceptance',
        native_execution_acceptance=False, provider_or_canary_acceptance=False,
        worktree_packets_installed=False, manifest=str(manifest_path),
        manifest_sha256=s.sha(manifest_path.read_bytes()), owner_bundle=str(bundle),
        source_commit=manifest['source_commit'], composition_commit=manifest['composition_commit'],
        forward_check=True, reverse_check=True, packets=rows, acceptance_flags=flags,
        all_retained_runs=runs, nonpassing_attempts=[row for row in runs if not row['completed_pass']],
        artifact_sha256=witnesses)
    with (bundle / 'validation.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    s.save('owner-packet-verification.json', result)
    print(json.dumps(dict(owner_bundle=str(bundle), acceptance_flags=flags,
                         nonpassing_attempts=[row['run'] for row in result['nonpassing_attempts']])))


if __name__ == '__main__':
    quiet()
    physical(s.OUT, s.SCRATCH)
    mode = sys.argv[1]
    if mode == 'scans':
        scans(*sys.argv[2:])
    elif mode == 'summary':
        summary()
    elif mode == 'parity':
        parity(sys.argv[2])
    elif mode == 'packets':
        packets(*sys.argv[2:])
    else:
        raise SystemExit('unknown mode')
