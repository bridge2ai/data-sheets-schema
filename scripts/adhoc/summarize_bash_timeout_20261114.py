"""6233, 2026-11-14: derive the timeout handoff evidence without running a model.

Inputs: assigned scratch logs, saved results, cProfile JSON, repository bytes.
Outputs: evidence.json, generated tables, and an unapplied scanner pin proposal.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import xml.etree.ElementTree as ET


def label(command):
    if 'native_shared_stage' in command:
        return 'stage advance'
    if '--initial-structure' in command:
        return 'initial receipt check'
    if ' derive core ' in command:
        return 'derive core'
    if 'd4d_pair_consistency' in command:
        return 'pair consistency'
    if 'linkml_term_validator' in command:
        return 'term validation'
    if 'linkml.validator' in command:
        return 'core validation' if 'CoreDataset' in command else 'full validation'
    if 'source_review' in command:
        return 'source review'
    words = shlex.split(command)
    return ' '.join(words[3:5])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('scratch', type=Path)
    args = parser.parse_args()
    scratch = args.scratch.resolve(strict=True)
    root = Path(__file__).resolve().parents[2]
    cases = []
    for name in ('correction', 'omissions', 'pending'):
        directory = scratch / name
        results = list(directory.rglob('actual-result.json'))
        assert len(results) == 1, (name, results)
        result = json.loads(results[0].read_text())
        attempt = results[0].parent / 'native-attempt'
        registration = json.loads((attempt / 'registration.json').read_text())['registration']
        metrics = []
        for line in (attempt / 'stderr.txt').read_text().splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and 'helper_timing' in row:
                metric = row['helper_timing']
                metric['ordinal'] = len(metrics) + 1
                metric['label'] = label(metric['command'])
                metric['cpu_seconds'] = metric['user_seconds'] + metric['system_seconds']
                metrics.append(metric)
        requests = []
        for line in (attempt / 'transcript.jsonl').read_text().splitlines():
            event = json.loads(line)
            if event.get('type') == 'assistant':
                for block in event.get('message', {}).get('content', []):
                    if block.get('type') == 'tool_use' and block.get('name') == 'Bash':
                        requests.append({'id': block['id'], 'command': block['input']['command']})
        assert len(requests) >= len(metrics)
        for metric, request in zip(metrics, requests):
            assert metric['command'] == request['command']
            metric['tool_use_id'] = request['id']
        junit = ET.parse(directory / 'junit.xml').getroot().find('testsuite')
        env = registration['environment']
        timeout_env = {key: env[key] for key in ('BASH_DEFAULT_TIMEOUT_MS', 'BASH_MAX_TIMEOUT_MS')}
        assert set(timeout_env.values()) == {'600000'}
        cases.append({'case': name, 'result_path': str(results[0]),
            'state': result['state'], 'first_stop': result['first_stop'],
            'runtime_gates_passed': result['runtime_gates_passed'],
            'shutdown': result['shutdown'], 'junit_seconds': float(junit.attrib['time']),
            'exit_status': int((directory / 'exit-status.txt').read_text()),
            'timeout_environment': timeout_env,
            'deadline_seconds': registration['runtime']['deadline_seconds'],
            'source_commit': registration['dependencies']['base']['source_commit'],
            'metrics': metrics, 'requests_without_timing': requests[len(metrics):]})
    profile = json.loads((scratch / 'stage-profile/profile.json').read_text())
    pin_paths = ['src/data_sheets_schema/native_shared_runtime_values.py',
                 'src/data_sheets_schema/native_runtime_profiles.py']
    pins = {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in pin_paths}
    scanner_path = '.claude/skills/d4d-generation-specificity-audit/scan.py'
    before = (root / scanner_path).read_text()
    after = before
    for path, digest in pins.items():
        pattern = r"('" + re.escape(path) + r"': ')[a-f0-9]{64}(')"
        after, count = re.subn(pattern, lambda m: m[1] + digest + m[2], after)
        assert count == 1, (path, count)
    (scratch / 'scanner-pin-proposal.patch').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile='a/' + scanner_path, tofile='b/' + scanner_path)))
    evidence = {'cases': cases, 'profile': profile, 'scanner_pins': pins,
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'synthetic_peer_sha256': hashlib.sha256(
            (root / 'tests/fixtures/native_shared_execution/fake_cli.py').read_bytes()).hexdigest()}
    data_path = scratch / 'evidence.json'
    data_path.write_text(json.dumps(evidence, indent=2) + '\n')
    # Every table below is rendered from the saved data file.
    data = json.loads(data_path.read_text())
    lines = ['| Case | Outcome / first stop | JUnit seconds | Unfinished workers |',
             '| --- | --- | ---: | ---: |']
    for case in data['cases']:
        lines.append(f"| {case['case']} | {case['first_stop']} | {case['junit_seconds']:.3f} | {case['shutdown']['unfinished_control_workers']} |")
    lines += ['', 'Correction: five slowest completed helper invocations, ranked by CPU seconds.', '',
              '| Tool ID | Helper | CPU seconds | Wall seconds | Exit |',
              '| --- | --- | ---: | ---: | ---: |']
    top = sorted(data['cases'][0]['metrics'], key=lambda x: -x['cpu_seconds'])[:5]
    for row in top:
        lines.append(f"| {row['tool_use_id']} | {row['label']} | {row['cpu_seconds']:.6f} | {row['wall_seconds']:.6f} | {row['exit_code']} |")
    lines += ['', 'Read-only partial cProfile: inclusive CPU-clock seconds overlap and must not be summed.', '',
              '| Function | Calls | Inclusive CPU seconds |', '| --- | ---: | ---: |']
    wanted = {'_load_live', '_base', 'verify_preparer', '_schemas', 'load_native'}
    for row in data['profile']['functions']:
        if row['name'] in wanted and '/src/data_sheets_schema/' in row['file']:
            lines.append(f"| {Path(row['file']).name}:{row['name']} | {row['calls']} | {row['inclusive']:.6f} |")
    (scratch / 'tables.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'head': data['head'], 'cases': [{k: case[k] for k in (
        'case', 'first_stop', 'junit_seconds', 'shutdown')} for case in data['cases']],
        'profile_wall': profile['wall_seconds'], 'profile_cpu': profile['cpu_seconds'],
        'scanner_pins': pins, 'synthetic_peer_sha256': data['synthetic_peer_sha256']}, indent=2))


if __name__ == '__main__':
    main()
