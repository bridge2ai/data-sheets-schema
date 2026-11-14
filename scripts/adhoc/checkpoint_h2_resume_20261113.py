#!/usr/bin/env python3
"""Save resumable H2 validation state for issues 6193-6202, 2026-11-13.
Inputs: saved cohort artifacts, current branch and active tool-session identity.
Output: exclusive timestamped scratch checkpoint. Not a final handoff; no tests,
process signals, source changes or external writes.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import report_h2_resume_20261113 as report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--active-cohort', required=True)
    parser.add_argument('--session', required=True)
    args = parser.parse_args()
    cohorts = [report.load_cohort(path) for path in sorted(report.SCRATCH.iterdir())
               if path.is_dir() and (path / 'command.json').is_file()]
    cohorts.append(report.load_cohort(report.SCRATCH, preload=True))
    proofs = {issue: [report.test_proof(cohorts, name, expected) for name, expected in requirements]
              for issue, requirements in report.PROOFS.items()}
    record = {
        'not_final_handoff': True,
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=report.ROOT, text=True).strip(),
        'status': subprocess.check_output(['git', 'status', '--short'], cwd=report.ROOT, text=True),
        'active_cohort': args.active_cohort, 'active_tool_session': args.session,
        'cohorts': [{key: row[key] for key in ('name', 'counts', 'complete', 'passed', 'evidence')}
                    | {'outcome': row.get('outcome')} for row in cohorts],
        'public_paths': report.PUBLIC,
        'regression_proofs': proofs,
        'next_actions': [
            'Finish current four-worker queue: failure, guards, dependents; inspect and triage any nonzero result without overwriting artifacts.',
            'After all queued groups end, run correction-isolated with the explicit correction public node and no xdist; run check_h2_public_isolation_20261113.py verify. The initial correction setup overlapped preload and is retained as historical failed evidence.',
            'After all tests finish, run preserve_h2_generated_bytecode_20261113.py canary, verify, then remaining; keep all bytes in scratch.',
            'Commit any remaining own helpers; refresh commit-map-source.txt; run final source audit at final HEAD.',
            'Run report_h2_resume_20261113.py; verify named Markdown and JSON, paths, hashes, no literal at signs; print handoff path and SHA256.',
            'Re-read the resume assignment: it queues G2 launch-path issues after the H2 handoff, on this same branch with a separate handoff.',
        ],
        'constraints': [
            'No push, PR, GitHub write, provider/native binary call, real capture/reservation or CPU-monitoring diagnostic.',
            'Protected files and guard v1 unchanged; controller source changes require review-only proposals.',
            'Use primary .venv interpreter from assigned worktree; outputs only in assigned sibling scratch; never poetry or tmp_path_retention_policy=none.',
        ],
        'report_producer': report.pin(Path(report.__file__)),
        'queue_control': report.pin(report.SCRATCH / 'acceptance-queue-control.json'),
    }
    directory = report.SCRATCH / 'checkpoints'
    directory.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = directory / ('resume-' + stamp + '.json')
    raw = (json.dumps(record, indent=2) + '\n').replace(chr(64), '\\u0040')
    with destination.open('x') as stream:
        stream.write(raw)
    print(json.dumps({'checkpoint': report.pin(destination),
                      'regression_statuses': {issue: report.status_for(rows) for issue, rows in proofs.items()}}))


if __name__ == '__main__':
    main()
