"""Append the requested U3-C Round 3 handoff and one STATUS entry, 2026-11-07.

Inputs: final evidence.json, verified cleanup log, clean committed checkout.
Outputs: append-only review section and one entry under ### codex; no commit,
network, test launch or notification. Run only as the final task operation.
"""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent / 'scratch-native-u3c-r3'
REPORT = ROOT.parent / 'plans/reviews/native_u3c_2026-11-07.md'
STATUS = ROOT.parent.parent / 'data-sheets-schema/notes/coordination/STATUS.md'
MARKER = '## Round 3 — B round 2 integration and bounded validation'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

head = git('rev-parse', 'HEAD')
assert git('branch', '--show-current') == 'codex/native-u3c-controller-20261107'
assert not git('status', '--short')
evidence = json.loads((OUT / 'evidence.json').read_text())
assert evidence['head'] == head and not evidence['git_status']
assert not evidence['both_side_paths']
assert all(evidence['donor_paths_preserved'].values())
assert evidence['bc1_baseline_comparison']['matches']
for name in ('launcher-canary', 'launcher-final', 'b-schema-remaining', 'collect'):
    assert evidence['runs'][name]['outcome']['returncode'] == 0, name
assert 'b-api-unfinished' in evidence['runs']
for name, run in evidence['runs'].items():
    assert run['outcome']['cleanup_verified'], name
    assert run['outcome']['seconds'] < 3600, name
    path = OUT / name / 'cases'
    assert not path.exists() and not path.is_symlink(), path
cleanup = list(csv.DictReader((OUT / 'cleanup.tsv').open(), delimiter='\t'))
assert cleanup and all(row['result'] == 'absent' for row in cleanup)
api = evidence['api_effective']
continuation = json.loads((OUT / 'api-continuation-selection.json').read_text())
unfinished_names = ', '.join('`' + node + '`' for node in continuation['pending'])
now = datetime.now(timezone.utc).isoformat(timespec='seconds')
table = '\n'.join('| ' + name + ' | ' + run['summary'][-1].replace('|', '\\|') +
                  ' | ' + f"{run['outcome']['seconds']:.3f}" + ' |'
                  for name, run in evidence['runs'].items())
api_summary = ', '.join(f'{count} {state}' for state, count in sorted(api['counts'].items()))
api_summary += f"; {len(api['missing'])} unfinished of {api['selected']} selected nodes"
free_gib = shutil.disk_usage(OUT).free / 2**30
section = f'''

{MARKER}

**Final local checkpoint: `{head}`.** Authority is
`notes/coordination/2026-11-07-codex-native-u3c-r3.md`; this section supersedes
the earlier handoff state while preserving its evidence. Written {now}.
Worktree and branch remain the explicitly assigned U3-C checkout and
`codex/native-u3c-controller-20261107`. No C-to-D integration was performed.

### Merge identity and resolutions

Merge **`11d6b77fc2c29815e08fc7ea6aac366e3b3de47a`** was made with `--no-ff`.
Its parents are `{evidence['merge_parents'][0]}` and
`{evidence['merge_parents'][1]}`. The second parent is the exact requested
U3-B repair `35d1aae4a631ce55660c45f838c6f03688ea38d3`.

The actual starting C head was `b9c144a182ccba84fac27e3b5717363c769d4a97`,
one documentation-only commit after the brief's `42e16482543d7e0269bd4a7b91445c11b7729063`.
That existing work was preserved. The merge-base comparison finds **zero
both-side changed paths**, and Git reported no conflicts. There were therefore
no overlap resolutions to make. All twelve B repair paths remain byte-identical
to the donor. In particular, B's smoke writes to `tmp_path`; retained smoke
evidence is copied by the evidence recorder after the test finishes.

Only `native_catalog_initialization.py` and `native_schema_event_reuse.py`
change in production relative to the actual starting head. The remaining
round-three additions are validation/evidence provenance. Protected files,
frozen v1, U2, U1 selection and launch-a21 were not edited in this round.
Final `src/` and `tests/` bytes equal those validated at `1e784ed91`.

### Bounded validation

Every executing invocation used at most two xdist workers, with one invocation
at a time and a 3,600-second deadline. Collection used zero workers.
`PYTHONPATH` was exactly `<assigned-worktree>/src:<assigned-worktree>`.
The physical dependency Python bootstrapped a fresh test-only environment;
dependency editable-install hooks were not executed. OS network denial,
native-agent executable denial, credential-free child environments and
own-checkout import witnesses were retained. The runner checked the quiet lock
before launch and checked for acquisition while running, pausing observed
descendants and checking a held lock no more than once per minute.
Elapsed times below are execution records, not quiet-host timing evidence.

All run directories are children of `scratch-native-u3c-r3/`. Exact commands,
rosters, bootstrap/environment identities, logs, XML and process outcomes are
retained there. Counts overlap across canaries and reruns and must not be summed.

| Run | Literal pytest result | Supervisor seconds |
| --- | --- | ---: |
{table}

The initial two-worker canary exercised B's actual owner-context typed
receipt-to-record reconstruction. Its 198,056-byte assembly, smoke JSON,
nonempty log/XML and source/network witnesses were verified before widening.
It proves the tested synthetic path and persistence, not admitted native
execution, concurrency generality or a performance improvement.

### Findings and incomplete-run accounting

**U3C-R3-H1 — nested test environment dependencies.** The first API group
recorded eight launcher failures: each failed while importing `api_runner`
because a test-created nested virtual environment could not import `yaml`.
Its fixture appends the outer site directory without processing that directory's
`.pth` dependency paths. The original red XML/log and the nested dependency
path file are retained. The optional `--nested-dependencies` harness mode links
installed dependency entries into the isolated test site while excluding
startup hooks, editable-install hooks and project code. No production code,
test body or assertion was changed. A single affected node was verified before
the complete launcher-file rerun; both retain their source-origin witnesses.
This finding is recorded locally because GitHub/network operations are forbidden.

API group 1 was **gracefully interrupted before its deadline**, retaining
**130 passed, 8 failed and {len(continuation['pending'])} unfinished case**. The verified owned controller
PID 68956 received SIGINT; pytest finished in 3,531.43 seconds and the supervisor
completed in 3,533.196 seconds with observed cleanup verified. This invocation
is incomplete, not a passing suite or a deadline extension. Full collection
and its XML identify the exact unfinished node: {unfinished_names}.
Both long completed-capture cases were recorded as passing before the stop
completed. The initial live-fixture estimate of two unfinished cases was
corrected by collection/XML reconciliation; synthetic interruption diagnostics
are retained but are not treated as collected test nodes. The continuation selection ledger
records their identities and input hashes; no completed node is silently dropped.

Effective API coverage, replacing only the corresponding launcher outcomes and
adding the exact continuation outcomes: **{api_summary}**.
This is separate-process broad coverage. It does not close B's original
full-order investigation or identify its historical `F.F` indicators.

BC1's **15 setup errors** match B's retained exact-base evidence by node and
error message; its one expected failure remains separately counted. The scanner
reports `shared selector call guards/order changed`. No scanner, guard or test
assertion was weakened, and BC1 is not a clean passing gate. The baseline
comparison and full error details are in the evidence manifest. Collection
results are collection only, not execution of the entire repository suite.

Read-only review found no additional production change required by this merge.
Native execution admission, the complete C/D publication lifetime and U0 timing
acceptance remain separate gates. No new native execution or timing claim is made.

### Evidence, cleanup and stop

- [Evidence manifest](../../scratch-native-u3c-r3/evidence.json), SHA-256
  `{sha(OUT / 'evidence.json')}`.
- [Cleanup log](../../scratch-native-u3c-r3/cleanup.tsv), SHA-256
  `{sha(OUT / 'cleanup.tsv')}`.
- Exact initial rosters, continuation selection, per-run logs/XML, bootstrap
  and origin witnesses, smoke copies and the interrupted relocated capture
  remain under the single assigned scratch directory.
- All {len(cleanup)} recorded transient basetemps were removed after inventories
  and retained copies were verified. The canary deletion was verified before
  widening cleanup. Inventories include hidden/ignored entries; explicit checks
  confirm every recorded run's `cases` path is absent. Per-target sizes and
  filesystem free-space readings are retained in the cleanup log; concurrent
  host activity prevents treating those deltas as exclusive recovery measurements.
  Filesystem free space at handoff: {free_gib:.2f} GiB.
- Helper provenance is committed under `scripts/adhoc/`: the round-three
  runner, roster driver, exact API continuation selector, evidence recorder,
  cleanup commands and this handoff writer. The final checkout is clean.

All owned test jobs have ended with observed descendant cleanup verified.
No fetch, push, gh, provider/network call, real native agent executable,
protected edit, main merge or merge into U3-D occurred. One STATUS entry is
added under `### codex`, then this task stops as instructed.
'''
old_report = REPORT.read_text()
assert MARKER not in old_report
REPORT.write_text(old_report + section)
assert REPORT.read_text() == old_report + section
report_sha = sha(REPORT)
entry = (f'- **{now} — Native U3-C Round 3 completed; stopped.** '
         f'Branch `codex/native-u3c-controller-20261107`, clean head **`{head}`**. '
         'Merged exact B repair `35d1aae4a` with no-ff merge `11d6b77fc`; zero overlaps/conflicts; '
         'all twelve donor paths preserved, including basetemp-only smoke output. '
         'C/A **742 passed**; B shared/S7/typed **677 passed**; BC1 **257 passed, 1 expected failure, '
         '15 exact-baseline setup errors**. Effective API: **' + api_summary + '**. '
         'Initial API interruption and eight harness-only missing-yaml failures remain retained; '
         'nested dependency harness repair and exact continuation are documented. '
         f'All runs bounded below 3600 seconds, at most two workers; {len(cleanup)} basetemps removed after evidence retention. '
         'Protected/frozen-v1/U2/launch-a21 unchanged; offline, no native executable or C-to-D merge. '
         '[Round 3 report](../../../d4d-executions/plans/reviews/native_u3c_2026-11-07.md), '
         f'SHA-256 `{report_sha}`. No further work started.\n\n')
old_status = STATUS.read_text()
anchor = '### codex\n\n'
assert old_status.count(anchor) == 1
assert 'Native U3-C Round 3 completed; stopped.' not in old_status
new_status = old_status.replace(anchor, anchor + entry, 1)
assert STATUS.read_text() == old_status, 'concurrent STATUS edit; preserve and retry deliberately'
STATUS.write_text(new_status)
assert STATUS.read_text() == new_status
assert not git('status', '--short')
print(json.dumps({'head': head, 'report_sha256': report_sha, 'status_entries_added': 1,
                  'api': api, 'removed_basetemps': len(cleanup), 'stopped': True}, indent=2))
