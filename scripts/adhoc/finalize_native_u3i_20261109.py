#!/usr/bin/env python3
"""Reconcile U3-I registry rerun and owner note, 2026-11-09 (U3H-E1/P3-1).

Inputs: immutable H facts/composition and fresh I canary/registry evidence.
Outputs: retained pre-I facts, I validation, updated FACTS status, report section 7.
No source/packet updates or acceptance waivers. Standard library, offline only.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
EXEC = ROOT.parent
SCRATCH = EXEC / 'scratch-native-u1u3'
OUT = SCRATCH / 'u3i'
H = SCRATCH / 'u3h'
BUNDLE = SCRATCH / 'owner-packets/u3h/e0b964b0e182'
TREE = H / 'composition-e0b964b0e182/tree'
SOURCE = 'e0b964b0e182548411045c5f6186b7d4ee64b8ec'
COMPOSITION = '660b2d884c3032f0eca61fcfd3ae523fcbbe9614'
HARNESS = '4504d6e7de9a4b0f0c72a7a9fea4f57faafd470a'
ENV = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'GIT_NO_LAZY_FETCH': '1',
       'GIT_ALLOW_PROTOCOL': '', 'GIT_CONFIG_GLOBAL': '/dev/null',
       'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'}


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(path):
    return dict(path=str(path), sha256=digest(path), bytes=path.stat().st_size)


def load(path):
    return json.loads(path.read_bytes())


def fresh(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return identity(path)


def git(root, *args):
    return subprocess.check_output(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', *args], cwd=root, env=ENV,
        text=True, timeout=30).strip()


def nodes(path):
    rows = []
    for case in ET.parse(path).getroot().iter('testcase'):
        status = 'passed'
        detail = None
        for tag in ('error', 'failure', 'skipped'):
            element = case.find(tag)
            if element is not None:
                status = {'failure': 'failed', 'error': 'error', 'skipped': 'skipped'}[tag]
                detail = dict(message=element.get('message'), text=element.text)
                break
        rows.append(dict(node=case.get('classname') + '::' + case.get('name'),
                         status=status, detail=detail, xml_attributes=case.attrib))
    return rows


def verify_run(label, expected_passed, expected_skipped):
    path = OUT / label
    plan = load(path / 'plan.json')
    outcome = load(path / 'outcome.json')
    stable = load(path / 'source-stability.json')
    harness = load(path / 'u3i-harness.json')
    rows = nodes(path / 'pytest.xml')
    counts = {key: sum(row['status'] == key for row in rows)
              for key in ('passed', 'failed', 'error', 'skipped')}
    need(counts == dict(passed=expected_passed, failed=0, error=0, skipped=expected_skipped),
         label + ': unexpected node outcomes')
    need(plan['source_commit'] == COMPOSITION and plan['source_root'] == str(TREE)
         and plan['workers'] == 2 and plan['deadline_seconds'] == 3200,
         label + ': source/worker/deadline identity')
    need(harness['commit'] == HARNESS and harness['composition'] == COMPOSITION
         and harness['sha256'] == digest(ROOT / 'scripts/adhoc/run_native_u3i_20261109.py'),
         label + ': harness identity')
    need(outcome['returncode'] == 0 and outcome['cleanup_verified']
         and not outcome['observed_surviving_pids'] and not outcome['observation_errors']
         and outcome['interrupted'] is None and outcome['seconds'] < 3300
         and outcome['worker']['source_origin_checks_passed'],
         label + ': execution/cleanup/origin bound')
    need(stable['unchanged'] and stable['before'] == stable['after']
         and stable['before']['head'] == COMPOSITION and not stable['before']['status'],
         label + ': source stability')
    need(load(path / 'network.json')['network_bind_denied']
         and load(path / 'subprocess-origins.json')['network']['network_bind_denied'],
         label + ': network denial')
    need(not load(path / 'u3g-cutoff.json')['events']
         and not load(path / 'early-cutoff.json')['events'], label + ': deadline cutoff')
    links = load(path / 'dependency-links.json')
    need('yaml' in links['links'] and 'fairscape_models' in links['links'],
         label + ': required dependency links')
    names = ('plan.json', 'outcome.json', 'worker-outcome.json', 'source-stability.json',
        'network.json', 'origins-before.json', 'origins-after.json', 'subprocess-origins.json',
        'u3i-harness.json', 'dependency-links.json', 'bootstrap.json', 'pytest.log',
        'pytest.xml', 'pytest-command.json', 'u3g-cutoff.json', 'early-cutoff.json')
    return dict(label=label, counts=counts, nodes=rows, seconds=outcome['seconds'],
                artifacts=[identity(path / name) for name in names],
                source_origin_and_cleanup_verified=True)


def main():
    need(not os.path.lexists(EXEC / 'plans/native_quiet_window.lock'), 'quiet window active')
    need(not git(ROOT, 'status', '--porcelain'), 'helper tree must be committed/clean')
    head = git(ROOT, 'rev-parse', 'HEAD')
    need(git(TREE, 'rev-parse', 'HEAD') == COMPOSITION and
         not git(TREE, 'status', '--porcelain'), 'composition changed')
    changed = git(ROOT, 'diff', '--name-only', SOURCE, 'HEAD').splitlines()
    need(changed == ['scripts/adhoc/finalize_native_u3i_20261109.py',
                     'scripts/adhoc/run_native_u3i_20261109.py'], 'out-of-scope branch changes')
    facts_path = BUNDLE / 'FACTS.json'
    old_raw = facts_path.read_bytes()
    need(digest(facts_path) == '4eaf7baa5d59200fb762a6d6896d9f7a41d6f2dae275b62a770cb058e2067f3a',
         'historical FACTS changed')
    need(digest(BUNDLE / 'validation.json') ==
         '03687eb34d73dccb226c0b3cf5121fdf705588435bb572816667401cd47e331f',
         'historical validation changed')
    manifest = load(H / 'composition-e0b964b0e182/composition.json')
    packets = []
    for packet in manifest['packets']:
        for suffix, key in [('patch', 'patch_sha256'), ('preimage', 'preimage_sha256'),
                            ('postimage', 'postimage_sha256')]:
            path = BUNDLE / (packet['name'] + '.' + suffix)
            need(digest(path) == packet[key], 'packet changed: ' + str(path))
        need(digest(ROOT / packet['target']) == packet['preimage_sha256'],
             'packet installed in worktree')
        need(digest(TREE / packet['target']) == packet['postimage_sha256'],
             'composed packet changed')
        packets.append(packet)
    canary = verify_run('canary-r1', 1, 0)
    registry = verify_run('registry-r1', 460, 11)
    old = nodes(H / 'composed-r1-registry/pytest.xml')
    need(Counter(row['node'] for row in old) == Counter(row['node'] for row in registry['nodes']),
         'registry node roster changed')
    old_skips = sorted((row['node'], row['detail']) for row in old if row['status'] == 'skipped')
    new_skips = sorted((row['node'], row['detail']) for row in registry['nodes'] if row['status'] == 'skipped')
    need(old_skips == new_skips, 'skip roster/reasons changed')
    old_failures = [row['node'] for row in old if row['status'] in ('failed', 'error')]
    passed = {row['node'] for row in registry['nodes'] if row['status'] == 'passed'}
    need(len(old_failures) == 8 and all(node in passed for node in old_failures),
         'eight previous failures not all resolved')
    old_args = load(H / 'composed-r1-registry/pytest-command.json')['args']
    new_args = load(OUT / 'registry-r1/pytest-command.json')['args']
    need([v for v in old_args if v.startswith('tests/')] ==
         [v for v in new_args if v.startswith('tests/')], 'full cohort selection changed')
    decision = identity(BUNDLE / 'P3-1_DECISION.md')
    facts = json.loads(old_raw)
    flags = facts['acceptance_flags']
    current = dict(label='u3i-registry-r1', counts=registry['counts'], executed=True,
        all_nodes_passed=False, present=True, matches_current_source=True,
        missing_artifacts=[], failed_nodes=[],
        skipped_nodes=[row for row in registry['nodes'] if row['status'] == 'skipped'],
        replaces='composed-r1-registry', source_commit=COMPOSITION, harness_commit=HARNESS)
    flags['required_cohorts'] = [current if row['label'] == 'composed-r1-registry' else row
                                for row in flags['required_cohorts']]
    flags['required_cohorts_all_nodes_passed'] = all(row['all_nodes_passed']
                                                   for row in flags['required_cohorts'])
    flags['required_cohorts_no_failed_executed_nodes'] = all(
        row['executed'] and row['counts']['failed'] == 0 and row['counts']['error'] == 0
        for row in flags['required_cohorts'])
    flags['u3h_e1_eight_launcher_failures_resolved'] = True
    flags['p3_1_decision_note'] = 'prepared_owner_decision_pending_gate_not_retired'
    facts['unmet_gates'] = [
        'Required registry cohort retains 11 skips (9 installed-wheel, 1 symlinked-venv traversal, 1 Poetry metadata); these are not acceptance.'
        if item == 'Required cohort contains failures or skips: composed-r1-registry' else item
        for item in facts['unmet_gates']]
    backup = BUNDLE / 'FACTS.pre-u3i.json'
    validation = dict(scope='U3-I supplement; all other U3-H evidence retained without rerun',
        utc=datetime.now(timezone.utc).isoformat(), source_commit=SOURCE,
        composition_commit=COMPOSITION, harness_commit=HARNESS, finalizer_commit=head,
        helper=identity(Path(__file__)), previous_facts=identity(facts_path),
        previous_validation=identity(BUNDLE / 'validation.json'),
        canary=canary, registry=registry, previous_failed_nodes_now_passed=old_failures,
        exact_node_roster_and_skip_reasons_retained=True, packets_unchanged=packets,
        owner_decision_note=decision, acceptance_flags=flags,
        unmet_gates=facts['unmet_gates'])
    fresh_validation = fresh(OUT / 'validation.json', validation)
    with backup.open('xb') as stream:
        stream.write(old_raw)
    facts['u3i_validation'] = fresh_validation
    facts['u3i_previous_facts'] = identity(backup)
    facts['u3i_owner_decision_note'] = decision
    facts['u3i_status_note'] = ('The 8 failures are resolved; 460 pass and 11 skip. '
        'All-nodes-passed remains false. Original validation.json is immutable historical evidence; '
        'u3i_validation supersedes only its registry run/status.')
    facts['u3i_finalizer_commit'] = head
    staged = BUNDLE / 'FACTS.u3i-staged.json'
    fresh(staged, facts)
    need(facts_path.read_bytes() == old_raw, 'concurrent FACTS edit')
    os.replace(staged, facts_path)
    need(load(facts_path) == facts, 'FACTS write verification failed')
    summary = dict(finalizer_commit=head, harness_commit=HARNESS,
        facts=identity(facts_path), facts_before=identity(backup), validation=fresh_validation,
        decision=decision, canary=canary['counts'], registry=registry['counts'],
        required_cohorts_all_nodes_passed=flags['required_cohorts_all_nodes_passed'])
    fresh(OUT / 'summary.json', summary)
    report = EXEC / 'plans/reviews/native_u3h_2026-11-09.md'
    need('\n## 7. U3-I' not in report.read_text(), 'report section already exists')
    lines = [
        '', '## 7. U3-I — nested dependency repair and P3-1 owner decision', '',
        'Completed offline on ' + validation['utc'] + '.',
        'U3H-E1 is resolved: the unchanged full registry-reader cohort now has **460 passed, '
        '0 failed, 0 errors, 11 skipped**. All eight prior launcher failures passed. '
        'The exact 471-node roster and skip reasons are unchanged.', '',
        '**Identity and scope.** Harness commit: `' + HARNESS + '`; final helper head: `' + head +
        '`. Tested composition: `' + COMPOSITION + '`, unchanged from U3-H source `' + SOURCE +
        '`. Only two scripts/adhoc helpers changed on the branch. All four packet artifacts, '
        'worktree preimages and composition postimages match their retained SHA-256 values. '
        'No packet was installed in the worktree.', '',
        '**Repair.** Adapted the C3 nested-dependency layout: the disposable outer venv now links '
        'ordinary dependency entries declared by installed distribution RECORDs. External paths, '
        'startup hooks, editable markers, project code/metadata and foreign FAIRSCAPE are excluded. '
        'Only independently blob-verified pinned FAIRSCAPE is exposed. Distribution RECORD and '
        'METADATA hashes are recorded; this is installed-dependency provenance and physical-path '
        'validation, not a recursive package-byte audit. Production/test fixture semantics and the '
        'launcher import-isolation check are unchanged.', '',
        '**Canary and full run.** The real import-isolation canary passed with -n 2 in %.3f s '
        '(supervisor), followed sequentially by the same harness full cohort in %.3f s. '
        'Both have persisted XML, logs, dependency inventories, source-origin witnesses, OS '
        'network-denial witnesses and verified cleanup of observed descendants. No deadline '
        'cutoff, forced cleanup or source mutation occurred. No claim is made about never-observed '
        'orphans.' % (canary['seconds'], registry['seconds']), '',
        '**Remaining coverage.** Nine installed-wheel nodes require the installation opt-in '
        '(not enabled offline); one resource node lacks a symlinked-venv fixture; one Poetry '
        'lock/metadata check lacks Poetry. These 11 skips are not passing acceptance evidence. '
        '`required_cohorts_all_nodes_passed` remains **false**; '
        '`required_cohorts_no_failed_executed_nodes` is **true**. FACTS.pre-u3i.json retains the '
        'original bytes. Historical validation.json remains unchanged; the I supplement explicitly '
        'supersedes only the registry outcome/status.', '',
        '**P3-1.** The one-page P3-1_DECISION.md presents the historical refusal, exact accounting '
        '(5,229 exact, 57 relocations, six field changes, one addition, zero removed), and proposed '
        'replacement. Independent read-only review checked that accounting and the distinction '
        'between the historical alias refusal and F2 unsupported-producer refusals. No gate was '
        'retired; owner review prose, the historical gate, F2 comparison, installed-wheel acceptance '
        'and real native/provider acceptance remain pending.', '',
        '**Artifact identities (SHA-256).**', '',
    ]
    for name in ('facts', 'facts_before', 'validation', 'decision'):
        entry = summary[name]
        lines.append('- ' + entry['path'] + ': `' + entry['sha256'] + '`.')
    lines += ['', 'Exact node outcomes, all eight resolved node identities, artifact hashes and '
              'unchanged packet identities: `' + str(OUT / 'validation.json') + '`.',
              'No push, GitHub operation, provider/account access or native executable. Stopped after '
              'the requested report and STATUS entry.', '']
    with report.open('a', encoding='utf-8') as stream:
        stream.write('\n'.join(lines))
    print(json.dumps(dict(**summary, report=identity(report)), indent=2))


if __name__ == '__main__':
    main()

