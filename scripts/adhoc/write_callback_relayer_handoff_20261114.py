"""Issue 6233, 2026-11-14: write lead handoff from saved validation evidence.

Inputs: assigned scratch and current Git commit. Output: named report handoff.
No tests, providers or outbound messages are invoked.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


def main():
    scratch, destination = map(Path, sys.argv[1:])
    root = Path.cwd()
    summary = json.loads((scratch / 'summary.json').read_text())
    validation = json.loads((scratch / 'validation.json').read_text())
    pins = json.loads((scratch / 'pins.json').read_text())
    assert [row['name'] for row in validation] == ['suite-canary', 'native', 'scanner']
    assert all(row['exit_code'] == 0 for row in validation)
    assert all(row['matches'] for row in pins['controllers'])
    assert all(row['current'] == row['pinned'] for row in pins['constants'])
    assert not any(row['moved_here'] for row in pins['scanner_mismatches'])
    assert all(row['base'] == row['current'] for row in pins['protected'].values())
    run = summary['runs']['correction-committed']
    baseline = summary['baseline']
    common_index = min(run['fit']['last_index'], baseline['fit']['last_index'])
    pair = [next(row['thread_cpu'] for row in item['rows'] if row['calls'] == common_index)
            for item in (baseline, run)]
    base_failures = []
    for case in ET.parse(scratch / 'base-regressions/junit.xml').getroot().iter('testcase'):
        failure = case.find('failure')
        if failure is not None:
            base_failures.append('- ' + case.get('name') + ': '
                                 + failure.get('message', '').splitlines()[0])
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    assert pins['head'] == head
    for item in (baseline, run):
        assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    files = [scratch / name for name in (
        'summary.json', 'summary.log', 'callback-cpu.md', 'validation.json',
        'native.log', 'native.xml', 'native-command.json', 'scanner.log',
        'scanner.xml', 'scanner-command.json', 'suite-canary.xml',
        'base-canary/junit.xml', 'base-regressions.log', 'base-regressions/junit.xml',
        'extra-tests.log', 'extra-fixed.log', 'correction/run.log',
        'pins.json', 'pins.log', 'roster-comparison/comparison.json',
        'correction-committed/callback-cpu.jsonl',
        'correction-committed/case/actual-result.json',
        'correction-committed/largest-0.txt', 'correction-committed/largest-1.txt',
    )]
    files += [root / 'notes/reviews/callback-prefix-relayer-20261114.md',
        root / 'scripts/adhoc/verify_callback_relayer_20261114.py',
        root / 'scripts/adhoc/test_callback_prefix_base_20261114.py',
        root / 'scripts/adhoc/summarize_callback_relayer_20261114.py',
        root / 'scripts/adhoc/audit_callback_prefix_pins_20261114.py',
        root / 'scripts/adhoc/compare_callback_roster_20261114.py',
        root / 'scripts/adhoc/measure_callback_growth_20261114.py',
        root / 'scripts/adhoc/write_callback_relayer_handoff_20261114.py',
        Path(baseline['path'])]
    for path in files:
        assert path.is_file() and path.stat().st_size, path
    assert not destination.exists(), destination
    counts = '; '.join(row['name'] + ': ' + json.dumps(row['counts'], sort_keys=True)
                       for row in validation)
    text = f'''# Callback prefix relayer handoff

The scanner roster derivation passes with the scanner unchanged. Total
per-callback CPU is **not flat**: growth is reduced, but the performance target
is not established. Final validation counts: {counts}.

The native count includes the migrated prefix regressions and the added scanner,
changed-input/guard, and storage tests. Counts are JUnit totals; failures, errors
and skips are shown explicitly above. The broader performance issue remains open.

## Implementation and review boundary

Local implementation commit: 71a327bcd. Final provenance/test commit: {head}.
Branch: codex/native-callback-prefix-relayer-20261114; assignment base: 6802d5987.
The entire stage module is restored byte-for-byte to the pre-prefix source.
There are no stage producer hooks or cache arguments. The unchanged scanner
rejects the assignment-base producer shape and derives R+W+2 from this source;
the saved roster comparison contains both outcomes and source hashes.

Capture owns whole-decision and whole-acknowledgement reuse. Fingerprints cover
all input bytes and bounds; changed whole units replay fresh. Compact decisions
omit predicted journal bytes, which are reconstructed and checked against their
exact stored pin. Observation-prefix reuse remains in capture. Fresh admission,
source/pin checks, old-byte rereads/hashes, exact extension anchors, the closed
effective-binding guard, sticky disablement and failed-suffix transactionality
remain. Standalone, saved evidence and final completion retain full replay.

The former stage-transition test now checks the approved whole-unit boundary:
identical units skip replay; a core transition changes the unit and replays it.
It does not claim individual receipt-producer reuse. The suffix regression
separately checks old observation work is skipped. The forty-input storage test
is a storage regression, not forty admitted callbacks or CPU evidence.

## Measurement and limits

The fresh offline synthetic API diagnostic ended with:
{json.dumps(run['outcomes'], sort_keys=True)}

Current permission-callback fit: {json.dumps(run['fit'], sort_keys=True)}.
Historical fit: {json.dumps(baseline['fit'], sort_keys=True)}.
At common callback index {common_index}, historical/current observer CPU seconds
were {pair[0]} and {pair[1]}; equal indices alone do not establish matched host load.
The generated callback-cpu.md contains every permission callback and all ordered
assistant/user observer barriers. Function spans overlap and must not be added.
The total CPU trend remains positive; fresh stage transitions have visible spikes.
This supports reduced repeated-verification cost, not a flat-CPU claim. The host
was heavily loaded and these are not matched-load experiments. The attempt did
not complete; no successful public pytest launch or final-completion performance
claim is made. The assignment's fresh-run measurement option was used, not the
alternative forty-callback fixture option. Windows and deadlines were unchanged.

Both optional retained-capture post-run profiles refused schema-snapshot
validation; one also reports a negative aggregate timer. They are unusable for
CPU attribution. Live observer JSONL was recorded before those replay attempts.
No new matched full-launch baseline was run: the supplied historical measurement
is the performance comparator. The deadline failure is therefore not presented
as a newly isolated regression relative to 6802d5987.

## Validation and failures

The saved command JSON files give exact current-suite invocations. The validation
runner used the assigned interpreter and source path, scratch basetemps and two
workers; its one-test canary passed before suite fanout. The base component
canary also passed before the base regression module was run.

The base component comparison has seven failures and ten passes: five failures
are the missing capture _stage_decision API; one is the old semantic namespaces;
one is the old stage _prefix signature. The log lists each test and traceback.
This substitutes base modules for component tests; it is not a verified-loader
or public-launch baseline. The separate unchanged-scanner comparison demonstrates
the actual base unsupported-producer refusal and current structural success.

The saved base-component failures were:

{chr(10).join(base_failures)}

An earlier added-test run had one IndexError from assuming a nonempty observation
fixture. It was corrected to use the supplied full-seal observation; the focused
rerun passed. This was a new-test fixture error, not a base production failure.
The first synthetic diagnostic refused uncommitted consumed source before any
callback; committing the reviewed source enabled the fresh diagnostic. The final
deadline stop and unusable optional profiles are reported above, not concealed
as successful validation.

## Pins, scope and recommendation

The final pins.json audit compares against 6802d5987 and includes controller
manifests, control/source constants, scanner pin tables and protected-file hashes.
No pin rotation was made. Searches for references to old source hashes included
hidden and ignored files. Scanner and protected files are unchanged. Historical
pin-table mismatches are distinguished from changes introduced here in the audit.

The separate read-only review is saved in the review note. Its findings for the
lead's issue ledger are the corrected live-file hash race, corrected absent-span
display, unresolved total-CPU growth, and unusable post-run profiles. This helper
did not file GitHub issues because the assignment forbids GitHub writes. Please
file/triage those findings. Recommend accepting the structural repair separately
from any performance closure, and profiling remaining live observer work before
authorizing broader reuse. No scanner, deadline, window, freshness or acceptance
rule was weakened. No provider, real native binary, push, PR or GitHub write ran.

## Reproduction and saved artifacts

From the assigned worktree, the summary command is:

```
PYTHONPATH=$PWD/src /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python scripts/adhoc/summarize_callback_relayer_20261114.py {scratch} {baseline['path']}
```

The completed diagnostic used this command against the committed production
source; a new run would require a fresh scratch destination:

```
PYTHONPATH=$PWD/src CALLBACK_METRICS={scratch}/correction-committed/callback-cpu.jsonl /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python scripts/adhoc/measure_callback_growth_20261114.py --standalone-correction
```

Every table is generated by that saved script from saved JSONL. Source and metric
digests are in the audit/comparison/summary files. The following artifact paths
were checked to exist and be nonempty when this handoff was written:

'''
    text += '\n'.join('- ' + str(path) for path in files) + '\n'
    assert chr(64) not in text
    destination.write_text(text)
    actual = destination.read_bytes()
    assert actual == text.encode() and actual
    print(str(destination))
    print(hashlib.sha256(actual).hexdigest())


if __name__ == '__main__':
    main()
