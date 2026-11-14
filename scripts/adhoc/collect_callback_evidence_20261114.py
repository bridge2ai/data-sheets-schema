"""Issue 6233/6234, 2026-11-14: summarize saved offline latency evidence.

Input: task scratch directory. Outputs: evidence-summary.json and Markdown.
Reads saved JUnit, profiles, callback spans, results and pin verification; never
launches tests or changes authority. Missing completion is never a passing gate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('scratch', type=Path)
    args = parser.parse_args()
    root = args.scratch.resolve()
    suites = []
    for path in sorted(root.glob('*/junit.xml')):
        tree = ET.parse(path)
        for suite in tree.iter('testsuite'):
            suites.append({'case': path.parent.name, 'path': str(path),
                           **{key: suite.get(key) for key in
                              ('tests', 'failures', 'errors', 'skipped', 'time')}})
    attempts = []
    for path in sorted(root.glob('*/cases/**/actual-result.json')):
        body = json.loads(path.read_text())
        gates = {name: {'checked': gate.get('checked'), 'passed': gate.get('passed')}
                 for name, gate in body.get('gates', {}).items()}
        final = path.parent / 'native-evidence' / 'final.json'
        marker = final.with_name('published.json')
        publication = None
        if final.exists() and marker.exists():
            final_raw = final.read_bytes()
            publication = {'final_path': str(final), 'marker_path': str(marker),
                           'final_sha256': hashlib.sha256(final_raw).hexdigest(),
                           'result_matches_final': body == json.loads(final_raw),
                           'marker': json.loads(marker.read_text())}
        attempts.append({'path': str(path), 'state': body.get('state'),
                         'first_stop': body.get('first_stop'),
                         'shutdown': body.get('shutdown'),
                         'runtime_gates_passed': body.get('runtime_gates_passed'),
                         'gates': gates, 'publication': publication,
                         'dispatched': body.get('subscription_guard', {}).get('dispatched')})
    profiles = []
    for path in sorted(root.glob('*/profile.json')):
        body = json.loads(path.read_text())
        profiles.append({'path': str(path), 'wall_seconds': body.get('wall_seconds'),
                         'error': body.get('error')})
    result = {'suites': suites, 'attempts': attempts, 'profiles': profiles}
    (root / 'evidence-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['Saved pytest outcomes; incomplete runs without JUnit are excluded.', '',
             '| Run | Tests | Failures | Errors | Skipped | Seconds |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for row in suites:
        lines.append('| ' + ' | '.join(str(row[key]) for key in
                     ('case', 'tests', 'failures', 'errors', 'skipped', 'time')) + ' |')
    lines += ['', '| Attempt result | State | First stop | Shutdown complete | Unfinished workers |',
              '| --- | --- | --- | --- | ---: |']
    for row in attempts:
        shutdown = row['shutdown'] or {}
        relative = str(Path(row['path']).relative_to(root))
        lines.append(f"| {relative} | {row['state']} | {row['first_stop']} | "
                     f"{shutdown.get('control_shutdown_complete')} | "
                     f"{shutdown.get('unfinished_control_workers')} |")
    lines += ['', '| Isolated profile | Wall seconds | Outcome |', '| --- | ---: | --- |']
    for row in profiles:
        lines.append(f"| {Path(row['path']).parent.name} | {row['wall_seconds']} | {row['error']} |")
    (root / 'evidence-summary.md').write_text('\n'.join(lines) + '\n')
    print(json.dumps({'suites': len(suites), 'attempts': len(attempts), 'profiles': len(profiles)}))


if __name__ == '__main__':
    main()
