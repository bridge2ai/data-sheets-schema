"""Purpose: write the Claude lead handoff for review fixes, 2026-11-16.

Inputs: scratch root with saved lane evidence and pin proposals, handoff path.
Outputs: Markdown handoff and printed SHA256. Serves issues 6263 through 6272.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

scratch, handoff = map(Path, sys.argv[1:])
root = Path(__file__).resolve().parents[2]
def git(*args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()

lines = [
    'Review fixes for the Claude lead', '',
    'Implemented: 6263, 6265, 6266, 6271, 6272, 6264 and 6268. '
    'Deferred before merge: 6267, 6269 and 6270, with reasons below. '
    'Pins remain unchanged apart from the explicitly assigned H1 test constant; '
    'the lead must apply the proposal and rerun affected checks.', '',
    'Issue disposition:', '',
    '- 6263: fixed. Mark proceed as possibly visible before publication starts. '
    'After that point, failed sequence cleanup requests SIGTERM and waits for '
    'the worker to finish transport cleanup before reaping. Immediate group kill '
    'is restricted to pre-proceed. The regression injects directory persistence '
    'failure after proceed is linked and after a separately sessioned Python '
    'child starts, using the real transport and worker signal context.',
    '- 6265: fixed. Elapsed-clock sampling, admission deadline checking and child '
    'deadline calculation precede the final subscription hook; Popen follows '
    'the hook. The existing guard saves dispatched_at from its final sample. '
    'A regression advances wall time during the elapsed-clock call and requires '
    'refusal before spawn. OS scheduling between check and syscall remains.',
    '- 6266: fixed. H1 REVIEWED matches the current authority bytes and the '
    'scanner comment names the current authority. No scanner pin was edited.',
    '- 6271: fixed. Recheck exact prepared bytes, worker liveness and age '
    'immediately before capture and again before proceed. Sequence regressions '
    'require zero capture dispatches after worker death or expiry following ready. '
    'A worker can still fail after the check; this is a liveness observation, '
    'not an atomic guarantee across processes.',
    '- 6272: fixed by comparison, not field removal. On proceed, compare both '
    'prepared hashes against dependencies and environment identity returned by '
    'the fresh recheck. Regression changes each hash independently.',
    '- 6264: fixed. The capture-order helper derives its checkout from its '
    'script location and requires the execution root as an argument. Historical '
    'review artifacts were not rewritten.',
    '- 6268: fixed. Take fresh directory lstat immediately before enumeration. '
    'The regression changes directory metadata after the resolver cache was '
    'seeded and verifies the fresh snapshot. Entry and final stability checks remain.',
    '- 6267: not before the merge, because binding the implementation memo key '
    'to executed bytes needs a supported loader-source contract across ordinary '
    'and verified loaders. The current loader exposes raw internally, but '
    'coupling the census to that private attribute needs broader loader tests. '
    'The narrow import-time disk-read residual remains.',
    '- 6269: not before the merge, because this is the approved D156 trade. '
    'Equality is retained as a tripwire; detection rests on the fresh source, '
    'input, HEAD, runtime and environment checks, not independent full derivation.',
    '- 6270: not before the merge, because hoisting imports across a scope that '
    'replaces module classes risks the exact-class lifetime mismatch fixed in '
    'the assigned base. The extended finder lifetime remains fail-closed and '
    'needs a dedicated loader-lifetime change.', '',
    'Validation interpretation: the initial focused controller checks refuse '
    'the changed transport bytes because controller pins deliberately remain '
    'unchanged. Scanner refusals name the changed environment-manifest source. '
    'Both need the lead pin rotation and a rerun. Initial native-controls '
    'failures include sandbox denial of local server binding; the loopback '
    'canary and repeat below use the same offline lane with that restriction '
    'lifted, still using mocked upstream traffic.', '',
    'The initial sequence signal failures exposed an overly broad test mock '
    'introduced here; it is now confined to the synthetic prepared owner. '
    'An existing start-retry test still expected a single command after D156 '
    'introduced the prepared worker. It now asserts the exact launch-then-capture '
    'order, preserving the refusal and journal assertions. Lead issue filing '
    'needed for that inherited stale test expectation; GitHub writes are forbidden '
    'for this helper. The sequence rerun below covers both corrections.', '',
    'Saved test evidence:', '',
]
for name in ('canary', 'canary-three-workers', 'focused', 'controls', 'scanners',
             'collection', 'sequence-rerun', 'controls-loopback-canary', 'controls-loopback'):
    directory = scratch / name
    summary_path = directory / 'lane_summary.json'
    if not summary_path.is_file():
        lines.append('- ' + name + ': no saved lane summary; not verified.')
        continue
    summary = json.loads(summary_path.read_text())
    lines.append('- ' + name + ': launcher return code ' + str(summary['overall_returncode'])
                 + '; evidence ' + str(summary_path) + '.')
    for xml in sorted((directory / 'results').glob('*.xml')):
        suites = ET.parse(xml).getroot()
        values = list(suites) if suites.tag == 'testsuites' else [suites]
        totals = {key: sum(int(value.get(key, '0')) for value in values)
                  for key in ('tests', 'failures', 'errors', 'skipped')}
        lines.append('  JUnit ' + xml.name + ': ' + ', '.join(
            str(value) + ' ' + key for key, value in totals.items()) + '.')
    for step in summary['steps']:
        path = Path(step['log_path'])
        assert path.is_file() and path.stat().st_size
        if name == 'collection':
            collected = re.search(r'(\d+) tests collected', path.read_text(errors='replace'))
            if collected:
                lines.append('  Full collection: ' + collected.group(1) + ' tests.')
        if step['returncode']:
            tail = path.read_text(errors='replace').splitlines()[-10:]
            lines.extend(['', 'Failure evidence from ' + str(path) + ':', '```',
                          *[line.replace(chr(64), '[at]') for line in tail], '```', ''])

proposal_path = scratch / 'pin-proposals.txt'
proposal = json.loads(proposal_path.read_text())
lines.extend(['', 'Pin proposals (read-only calculator output):', '',
              'Source commit used: ' + proposal['head_commit'] + '.',
              'Protected files verified: ' + str(proposal['protected_files_ok']) + '.', ''])
for item in proposal['proposed_edits']:
    lines.append('- ' + item['path'] + ': ' + item['after_sha256'] + '; ' + item['summary'] + '.')
for item in proposal['manual_review_actions']:
    lines.append('- Manual action: ' + json.dumps(item, sort_keys=True) + '.')
scanner = root / '.claude/skills/d4d-generation-specificity-audit/scan.py'
lines.extend(['', 'Actual comment-only scanner SHA256 before lead pin rotation: '
    + hashlib.sha256(scanner.read_bytes()).hexdigest() + '.',
    'Authority SHA256: ' + hashlib.sha256((root /
        'src/data_sheets_schema/native_execution_authority_v2.py').read_bytes()).hexdigest() + '.',
    'Full proposal evidence: ' + str(proposal_path) + '.', '',
    'Branch: ' + git('branch', '--show-current') + '.',
    'Head: ' + git('rev-parse', 'HEAD') + '.', '',
    'Commits, oldest first:', '```',
    git('log', '--reverse', '--format=%h %s', '24c55a9a1..HEAD'), '```', '',
    'Reproduction: python3 scripts/adhoc/run_review_fixes_20261116.py PRIMARY SCRATCH. '
    'The runner uses the assigned isolated interpreter, required host gate and '
    'three workers for the native controls suite, with persisted canary cleanup '
    'evidence required before the batch. No public case or Claude binary was run.', '',
    'Read-only GitHub issue reads failed because api.github.com was unreachable. '
    'Both assigned local reviews were read. No GitHub write, push or PR was made; '
    'the lead owns publication and any review issue filing. '
    'The four protected files were not edited.', '',
    'Helpers committed on this branch: scripts/adhoc/synthetic_prepared_cleanup_6263_20261116.py, '
    'scripts/adhoc/run_review_fixes_20261116.py and scripts/adhoc/report_review_fixes_20261116.py.',
])
raw = ('\n'.join(lines) + '\n').encode()
assert bytes([64]) not in raw
handoff.write_bytes(raw)
assert handoff.read_bytes() == raw
print(str(handoff))
print(hashlib.sha256(raw).hexdigest())
