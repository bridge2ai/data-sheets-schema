"""Diagnose D156 receipt census, 2026-11-16, PR 5968.

Inputs: saved preparation manifest and the current interpreter environment.
Outputs: scratch JSON comparison, including full census data and compact summary.
Diagnostic tracing is confined to this standalone harness, never production.
"""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--replay-prepared-roots', action='store_true')
    args = parser.parse_args()
    sys.path[0] = str(Path.cwd())
    from tests.utils.native_helper_environment import helper_import_paths
    sys.path = helper_import_paths(Path.cwd())
    from data_sheets_schema import native_environment_manifest as env
    expected = json.loads(args.manifest.read_text())
    if args.replay_prepared_roots:
        sys.path.extend(sorted({row['root'] for key in ('excluded_roots', 'unowned_files')
                                for row in expected[key]} - set(sys.path)))
    report = {'executable': sys.executable, 'sys_path': sys.path.copy(),
              'prepared_manifest': str(args.manifest)}

    def trace(frame, event, arg):
        if frame.f_code.co_name != '_light_census':
            return None
        if event in ('exception', 'return') and 'current' in frame.f_locals:
            current = frame.f_locals['current']
            report['component_equal'] = {key: expected[key] == current[key] for key in expected}
            report['helper_current'] = current
            for key in ('excluded_roots', 'unowned_files'):
                before = {json.dumps(row, sort_keys=True) for row in expected[key]}
                after = {json.dumps(row, sort_keys=True) for row in current[key]}
                report[key + '_removed'] = [json.loads(row) for row in sorted(before - after)]
                report[key + '_added'] = [json.loads(row) for row in sorted(after - before)]
        return trace

    sys.settrace(trace)
    try:
        env._light_live(expected)
        report['result'] = 'pass'
    except Exception as exc:
        report['result'] = str(exc)
    finally:
        sys.settrace(None)
    summary = {key: value for key, value in report.items()
               if key in ('executable', 'sys_path', 'component_equal', 'result')}
    summary['unowned_removed_by_root'] = {}
    for row in report.get('unowned_files_removed', []):
        root = row['root']
        summary['unowned_removed_by_root'][root] = summary['unowned_removed_by_root'].get(root, 0) + 1
    summary['unowned_added_count'] = len(report.get('unowned_files_added', []))
    summary['excluded_removed'] = report.get('excluded_roots_removed', [])
    report['summary'] = summary
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
