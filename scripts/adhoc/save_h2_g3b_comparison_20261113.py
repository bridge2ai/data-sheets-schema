#!/usr/bin/env python3
"""Compare retained G3b stops with H2 callback evidence, 2026-11-13.
Inputs: lead trial log/results/transcript/timing; no process or runtime inspection.
Output: scratch comparison with file hashes and ignored-independent inventory.
Serves issue 6200 and the lead's G3b hang question; no causal diagnosis invented.
"""
import json
from pathlib import Path
import report_h2_resume_20261113 as report


def main():
    trial = report.ROOT.parent / 'scratch-lead-g3b-trial-20261114'
    cases = trial / 'bt/popen-gw1'
    completed = []
    for short in ('Rea', 'Bas'):
        path = cases / ('test_denial_live_and_saved_' + short + '0/not_prescribed/actual-result.json')
        value = report.read_json(path)
        completed.append({'evidence': report.pin(path), 'state': value['state'],
                          'first_stop': value['first_stop'], 'shutdown': value.get('shutdown')})
    write = cases / 'test_denial_live_and_saved_Wri0/not_prescribed'
    transcript = write / 'native-attempt/transcript.jsonl'
    timing = write / 'native-attempt/host-controller-timing.jsonl'
    transcript_rows = [json.loads(line) for line in transcript.read_bytes().splitlines()]
    timing_rows = [json.loads(line) for line in timing.read_bytes().splitlines()]
    pending = transcript_rows[-1]
    assert pending['type'] == 'control_request'
    assert pending['request']['input']['tool_name'] == 'Read'
    assert pending['request']['input']['tool_input']['file_path'].endswith('/stages/requests/000002.json')
    cleanup = [row for row in timing_rows if row.get('boundary') == 'execute_child_cleanup_entry']
    assert cleanup
    # pathlib walks include ignored and hidden files; do not follow directory aliases.
    files = sorted(str(path.relative_to(write)) for path in write.rglob('*') if path.is_file())
    matching = [name for name in files if Path(name).name in ('actual-result.json', 'final.json', 'published.json')]
    assert not matching
    result = {
        'answer': 'The H2 callback-window evidence does not establish the cause of the G3b hang.',
        'completed_cases': completed,
        'write_case': {'transcript': report.pin(transcript), 'last_event': pending,
                      'timing': report.pin(timing), 'cleanup_entries': cleanup,
                      'inventory_scope': str(write), 'inventory_includes_ignored_and_hidden': True,
                      'inventory_follows_directory_symlinks': False,
                      'files': files, 'result_or_final_publication_files': matching},
        'trial_log': report.pin(trial / 'denials.log'),
        'interpretation': 'The Write case reached transport cleanup after a pending Read of the next stage request, but no saved result identifies its stop or what prevented final publication. The two completed cases report different stops. Ordered queued history work is a possible shared delay mechanism, not an established cause, and the pending Read does not establish that its observer or classifier began.',
        'scope': 'Read-only retained-artifact and source comparison; no CPU monitoring, runtime probing, tests or source changes. No corrective algorithmic fix is claimed.',
    }
    destination = report.SCRATCH / 'g3b-hang-comparison.json'
    with destination.open('x') as stream:
        stream.write((json.dumps(result, indent=2) + '\n').replace(chr(64), '\\u0040'))
    print(json.dumps(report.pin(destination)))


if __name__ == '__main__':
    main()
