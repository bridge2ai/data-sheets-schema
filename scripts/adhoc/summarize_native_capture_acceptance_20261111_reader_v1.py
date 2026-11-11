#!/usr/bin/env python3
"""Read retained S382f capture evidence into a new summary; 2026-11-11.

Inputs: fixed preparation, equivalence and capture artifacts for #5838/#5847.
Output: exclusive JSON beside review reports. No tests, imports from project
source, configuration changes, process execution or network operations.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[3]
SCRATCH = BASE / 'scratch-native-u1u3/u3m'
SOURCE = '382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b'
CONTRACT_SHA = 'df9eb421572b3a9ca578adfe1664cd23b372c61f315d6c191d3eba4e57eeda4e'
CAPTURE_NODE = 'test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root'
OUTPUT = BASE / 'plans/reviews/native_capture_acceptance_20261111.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    files = {}
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    def read(path):
        if path.resolve(strict=True) != path or not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError('physical regular evidence required: ' + str(path))
        with path.open('rb') as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError('evidence exceeds bounded reader: ' + str(path))
        files[str(path)] = dict(bytes=len(raw), sha256=sha(raw))
        return raw

    def load(path):
        return json.loads(read(path))

    composition_path = SCRATCH / ('composition-' + SOURCE[:12]) / 'composition.json'
    composition = load(composition_path)
    contract_path = SCRATCH / ('wp1-contract-' + SOURCE[:12] + '.json')
    contract = load(contract_path)
    check(files[str(contract_path)]['sha256'] == CONTRACT_SHA, 'contract hash differs')
    check(contract['source_commit'] == composition['source_commit'] == SOURCE,
          'source identity differs')
    check(contract['composition_manifest_sha256'] == files[str(composition_path)]['sha256'],
          'composition pin differs')
    runs = {}
    for kind, node, module, limit in (
            ('canary', 'test_consumer_observer_equivalence_canary', 'tests.test_native_u3k_profile', 60),
            ('capture-recheck', CAPTURE_NODE, 'tests.test_native_subscription_capture', 900)):
        out = SCRATCH / ('wp1-' + SOURCE[:12] + '-' + kind + '-capture-ast-20261111')
        outer = load(Path(str(out) + '.outer.json'))
        supervisor = load(Path(str(out) + '.supervisor.json'))
        outcome = load(out / 'outcome.json')
        cutoff = load(out / 'wp1-cutoff.json')
        stability = load(out / 'source-stability.json')
        network = load(out / 'network.json')
        plan = load(out / 'plan.json')
        harness = load(out / 'wp1-harness.json')
        expected_class = ('equivalence_canary' if kind == 'canary'
                          else 'capture_readback_integration_canary')
        check(harness['source_commit'] == SOURCE and harness['manifest_sha256'] == CONTRACT_SHA
              and harness['source_unchanged'] is True and harness['kind'] == kind
              and harness['invocation_limit_seconds'] == limit
              and harness['node'] == module.replace('.', '/') + '.py::' + node,
              kind + ': final harness differs')
        xml = ET.fromstring(read(out / 'pytest.xml'))
        cases = list(xml.iter('testcase'))
        failures = list(xml.iter('failure')) + list(xml.iter('error')) + list(xml.iter('skipped'))
        check(len(cases) == 1 and not failures and cases[0].get('name') == node
              and cases[0].get('classname') == module, kind + ': exact singleton did not pass')
        for name, row in (('outer', outer), ('supervisor', supervisor)):
            check(row['manifest_sha256'] == CONTRACT_SHA and row['kind'] == kind
                  and row['limit_seconds'] == limit, kind + ': ' + name + ' identity differs')
            check(row['returncode'] == 0 and row['cleanup_verified'] is True
                  and not row.get('forced_cleanup') and not row.get('interrupted')
                  and not row.get('timed_out') and not row.get('errors')
                  and not row.get('cleanup_errors') and not row.get('observation_errors')
                  and not row.get('observed_surviving_pids') and row['seconds'] <= limit,
                  kind + ': ' + name + ' terminal certification failed')
            check(row['host_qualified'] is False and row['wall_time_freshness_qualified'] is False,
                  kind + ': unsupported qualification')
        for name, row in (('outer', outer), ('supervisor', supervisor), ('harness', harness)):
            check(row['measurement_class'] == expected_class
                  and row['accepted_quiet_host_timing'] is False,
                  kind + ': classification differs: ' + name)
        handoff = supervisor['sandbox_handoff']
        check(handoff['admitted'] is True and not handoff['errors']
              and not handoff['observed_surviving_pids']
              and outer['observer_joined'] is True and not outer['post_observer_cleanup_pids']
              and not cutoff['events'] and cutoff['invocation_limit_seconds'] == limit,
              kind + ': nested cleanup or cutoff contradicts certification')
        check(outer['source_commit'] == SOURCE, kind + ': outer source differs')
        check(outcome['returncode'] == 0 and outcome['cleanup_verified'] is True
              and not outcome['forced_cleanup'] and not outcome['interrupted']
              and not outcome['observation_errors'] and not outcome['observed_surviving_pids'],
              kind + ': inner outcome failed')
        check(stability['unchanged'] is True and network['network_bind_denied'] is True,
              kind + ': source stability or network denial failed')
        env = plan['environment']
        check(env['GIT_CONFIG_GLOBAL'] == env['GIT_CONFIG_SYSTEM'] == '/dev/null'
              and env['HOME'] == str(out / 'home'), kind + ': child config environment differs')
        check(not any(key.endswith('_API_KEY') for key in env), kind + ': API key in environment')
        origins = {name: load(out / name) for name in
                   ('origins-before.json', 'origins-after.json', 'subprocess-origins.json')}
        expected_package = str(Path(composition['test_root']) / 'src/data_sheets_schema')
        for name in ('origins-before.json', 'origins-after.json'):
            check(origins[name]['package_paths'] == [expected_package],
                  kind + ': package origin differs: ' + name)
        nested = origins['subprocess-origins.json']
        check(nested['origins']['package_paths'] == [expected_package]
              and nested['network']['network_bind_denied'] is True,
              kind + ': nested child origin or network differs')
        measurements = []
        for path in sorted((out / 'phase-metrics').glob('*-measurement.json')):
            measurements.append(dict(path=str(path), data=load(path)))
        check(bool(measurements), kind + ': measurement evidence missing')
        runs[kind] = dict(outer=outer, supervisor=supervisor, outcome=outcome,
            source_stability=stability, network=network, harness=harness, cutoff=cutoff,
            junit_cases=[case.attrib for case in cases],
            junit_suites=[suite.attrib for suite in xml.iter('testsuite')],
            origins=origins, measurements=measurements)
        if kind == 'canary':
            paths = list((out / 'phase-metrics').glob('*-consumer-observer-equivalence.json'))
            check(len(paths) == 1, 'equivalence evidence not singleton')
            if len(paths) == 1:
                equivalence = load(paths[0])
                check(equivalence['recorder_functional_after_cleanup'] is True
                      and equivalence['open_call_rows'] == equivalence['open_thread_stacks'] == 0,
                      'Recorder did not close cleanly')
                guards = equivalence['profile_stability_guards']
                check(equivalence['general_replacement_equivalence'] is False
                      and all(guards[name] is True for name in
                              ('future_thread_default_restored', 'monitoring_slots_restored',
                               'profile_hook_restored'))
                      and bool(guards['cases'])
                      and all(row['state']['restored'] is True for row in guards['cases']),
                      'equivalence guard-restoration evidence differs')
                runs[kind]['equivalence'] = equivalence

    capture = SCRATCH / ('wp1-' + SOURCE[:12] + '-capture-recheck-capture-ast-20261111')
    claim = load(SCRATCH / ('capture-recheck-' + SOURCE + '-' + CONTRACT_SHA + '.once.json'))
    check(claim == dict(node='tests/test_native_subscription_capture.py::' + CAPTURE_NODE,
                        source_commit=SOURCE, manifest_sha256=CONTRACT_SHA, output=str(capture)),
          'once-only capture claim differs')
    fixture = capture / 'cases/popen-gw0/test_genuine_registration_read0/case'
    fixture_files = []
    for path in sorted(fixture.rglob('*')):
        if path.is_symlink():
            raise ValueError('unexpected fixture symlink: ' + str(path))
        if path.is_file():
            read(path)
            fixture_files.append(str(path))
            if len(fixture_files) > 1000:
                raise ValueError('fixture census exceeds 1000 files')
    check(bool(fixture_files), 'fixture artifacts missing')
    capture_paths = list(fixture.rglob('capture.json'))
    check(len(capture_paths) == 1, 'saved capture not singleton')
    capture_document = load(capture_paths[0]) if len(capture_paths) == 1 else None
    stage_path = fixture / 'fresh-attempt/stages'
    selection = load(fixture / 'authority/selection.json')
    stage_raw = read(stage_path)
    check(selection['stage_root'] == str(stage_path)
          and stage_raw == b'regular file blocking stage root\n',
          'retained stage-root mutation does not match selected exact path/bytes')
    private = composition['private_config']
    configured = read(Path(private['path']))
    backup = read(Path(private['backup']))
    config_state = ('held_configured' if sha(configured) == private['configured_sha256']
                    else 'restored' if configured == backup else 'unexpected')
    check(config_state != 'unexpected', 'private config neither configured nor original')
    check(sha(backup) == private['original_sha256'], 'config backup changed')
    result = dict(source_commit=SOURCE, contract_sha256=CONTRACT_SHA,
        composition=composition, runs=runs, fixture_files=fixture_files,
        capture_document=capture_document, stage_root_mutation=str(stage_path),
        private_config_state=config_state, errors=errors,
        software_capture_evidence_passes=not errors,
        native_acceptance=False, wall_time_freshness_qualified=False,
        scope='Read-only saved software evidence; invented authorities and lifecycle are not native execution.',
        files=files, helper_sha256=sha(Path(__file__).read_bytes()))
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    with OUTPUT.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if OUTPUT.read_bytes() != raw:
        raise ValueError('summary readback differs')
    print(json.dumps(dict(path=str(OUTPUT), sha256=sha(raw), errors=errors,
                          private_config_state=config_state)), flush=True)
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
