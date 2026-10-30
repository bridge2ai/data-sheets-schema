#!/usr/bin/env python3
# Purpose: close G1 review acceptance with reproducible history/CI/byte evidence.
# Inputs: external evidence directory and requested report; outputs: final manifest,
# commit map and replacement of this task's appended report section. G1 step 10, 2026-10-30.
import json
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
evidence, report = map(Path, sys.argv[1:])
assert not evidence.resolve().is_relative_to(root)
assert report.name == 'generality_g1_2026-10-29.md'
base = '55c7b94b838eb500888055da5a47acf2ee9e2e15'
original = '0ba88ba120aa29b86a885aaaa579b8bf59148d3a'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()

head = git('rev-parse', 'HEAD')
assert git('branch', '--show-current') == 'codex/wave7-generality-g1-20261029'
assert not git('status', '--porcelain')
assert git('rev-parse', 'codex/wave7-generality-g1-orig-20261029') == original
assert git('merge-base', base, head) == base
assert not git('rev-list', '--merges', base + '..' + head)
assert not git('log', '--diff-filter=A', '--format=', '--name-only', base + '..' + head, '--', '*.gz')
changed = git('diff', '--name-only', base, head).splitlines()
protected = [p for p in changed if Path(p).name in
             {'shared_generation.py', 'canonical_hashes.yaml', 'STATUS.md'}
             or p.startswith(('data/ATTIC/', 'data/d4d_concatenated/'))
             or set(Path(p).parts) & {'decisions', 'decision_records', 'decision-records'}]
assert not protected, protected
comparison = json.loads((evidence / 'failure-comparison-final.json').read_text())
assert comparison['counts'] == {'resolved-passed': 92, 'resolved-skipped': 1, 'same-base-failure': 123}
assert not comparison['unexpected_replay_failures']
collection = json.loads((evidence / 'final-collection/collect-all.result.json').read_text())
assert collection['returncode'] == 0 and collection['head'] == head
collection_text = (evidence / 'final-collection/collect-all.log').read_text()
assert re.search(r'25030 tests collected', collection_text), collection_text[-500:]
byte_delta = json.loads((evidence / 'bytes-delta-acceptance.json').read_text())
prior_delta = json.loads((evidence / 'bytes-delta-final.json').read_text())
assert byte_delta == prior_delta, 'acceptance work changed a proven model-facing byte'
history_map = json.loads((evidence / 'commit-map.json').read_text())
assert git('rev-parse', head + '^') == history_map['new_head']
history_map['final_head'] = head
history_map['post_rewrite_commits'] = [{'commit': head, 'finding': 'Step 10 complete acceptance corrections'}]
(evidence / 'commit-map-final.json').write_text(json.dumps(history_map, indent=2) + '\n')
manifest = {'head': head, 'base': base, 'original_recovery_ref': original,
            'commits': int(git('rev-list', '--count', base + '..' + head)),
            'merges': 0, 'gzip_additions': 0, 'protected_path_changes': protected,
            'collection': collection, 'failure_counts': comparison['counts'],
            'coverage': comparison['coverage'], 'payloads': byte_delta['phases']}
(evidence / 'acceptance-final.json').write_text(json.dumps(manifest, indent=2) + '\n')

# Preserve the previous report and every earlier author's section. Replace only
# this task's appended progress narrative with its completed acceptance result.
marker = '## Independent-review corrections and complete acceptance rerun'
text = report.read_text()
before, current = text.split(marker, 1)
backup = evidence / 'report-before-final-acceptance.md'
if not backup.exists():
    backup.write_text(text)
current = marker + current
start = current.index('**Acceptance ')
end = current.index('\n\nAll new evidence', start)
current = current[:start] + (
    f'**Acceptance complete.** Final head: `{head}`. The original `{original[:9]}` is retained '
    'as `codex/wave7-generality-g1-orig-20261029`. All required CI units ran, every '
    'remaining failure was reproduced on the exact base, and no G1-introduced failure '
    'remains. No network/provider call, push, GitHub operation or merge occurred.') + current[end:]
current = current.replace('bytes-after-final.json', 'bytes-after-acceptance.json').replace(
    'bytes-delta-final.json', 'bytes-delta-acceptance.json').replace('bytes-delta-final.log', 'bytes-delta-acceptance.log')
current = re.split(r'### (?:Full acceptance execution|Completed whole-tree collection)', current, maxsplit=1)[0]
relative = evidence.name
lines = ['### Completed whole-tree collection and CI-layout execution', '',
    f'Final whole-tree collection on `{head[:9]}`: **25,030 tests, zero errors**, '
    f'{collection["seconds"]:.2f} seconds including launcher '
    f'([log]({relative}/final-collection/collect-all.log)). '
    'The workflow partition covers all **21,037 collected tests/ instances**, with no missing '
    'or unexpected instances and no cross-unit overlap. One pre-existing pytest-7 parameter '
    'ID is emitted twice; multiplicity is preserved. Separate offline jobs also ran completely.', '',
    'Across all CI units: **24,909 instances**. Initial results were **24,634 passed, '
    '59 skipped, 187 failed and 29 setup errors**. Replaying every failed node after corrections '
    'gives **24,726 passed, 60 skipped, 123 pre-existing failures**. These are combined original '
    'and replay results, not a claim that the entire matrix was executed twice.', '',
    '| Unit | Initial pass / skip / failure+error | After replays: pass / skip / base failure |',
    '|---|---|---|']
for unit, row in comparison['units'].items():
    old, new = row['initial'], row['after_failed_node_replays']
    lines.append(f"| {unit} | {old['passed']} / {old['skipped']} / {old['failures'] + old['errors']} | "
                 f"{new['passed']} / {new['skipped']} / {new['pre_existing_failures']} |")
lines += ['',
    'The full run exposed **28 additional G1 fixture/metadata failures**, all repaired: '
    'dated historical records (including observer discovery); existing condition fields in historical '
    'renderer stubs; recorded headers for tuned replay; a supported fresh identity-change condition; '
    'an explicit input allowance for the cap-only test; exact 3.0.0 identity for retained mapper '
    'sidecars; agent preimage registration; and the F11 crate-manifest hash in the current comparison. '
    'The remaining 65 resolved nodes were harness/environment cases (64 passes and one existing '
    'missing-example skip). Shared-fixture follow-up passed **53 tests**; the complete failed-node '
    'head replay passed 166, skipped one and initially failed 128, of which five were fixed in that follow-up.', '',
    'The corrected offline launcher preserves explicit Python flags, import guards, direct-script '
    'import paths and test-created local credentials. Actual provider keys are removed before '
    'tests start, and remote sockets remain blocked. Three causal launcher canaries passed '
    '(4 core, 3 native, 2 audit/finalization cases) before the batch replay. All tests ran serially '
    'at the top level with external basetemp and worktree src; the existing CI-partition test '
    'exercised its own nested xdist control.', '',
    '### Every remaining failure and exact-base evidence', '',
    f'The clean exact-base replay at `{base}` ran all **216 original failed nodes**: '
    '**123 failed, 92 passed, one skipped**, 668.14 seconds of pytest time '
    f'([base log]({relative}/base-replay-final/base-failures.log), '
    f'[JUnit]({relative}/base-replay-final/base-failures.xml)). '
    'All 123 residuals reproduce the same exception/assertion and guard outcome. '
    '113 failure messages are identical; ten differ only in generated generation/event/snapshot '
    'identities or the displayed instruction hash. The ledger retains both unmodified traces '
    'and names the narrowly normalized fields.', '',
    f'**Every node, head trace and base trace:** [complete ledger]({relative}/failure-comparison-final.md) '
    f'and [raw comparisons]({relative}/failure-comparison-final.json). '
    'The 123 comprise 99 relative-registration-path refusals, 14 latch-journal/guard-order '
    'expectations (including G1-R10), seven native instruction/backfill mismatches, two request '
    'stubs missing metadata_dir, and G1-R1 (match versus expected unknown).', '',
    '| Test file | Remaining nodes, all reproduced on base |', '|---|---:|']
for filename, count in comparison['remaining_by_file'].items():
    lines.append(f'| `{filename}` | {count} |')
lines += ['', '### Final byte identities and commit map', '',
    'The final head recapture equals the previously proven corrected payloads exactly. '
    'No acceptance fix added another model-facing delta. The exhaustive comparison asserts '
    'all 22 changed leaves and the four exact byte deltas; raw merged schema remains '
    '**+320 bytes = F6 +241 + N7 +79**.', '',
    '| Payload | Base SHA-256 | Final SHA-256 |', '|---|---|---|']
for phase, row in byte_delta['phases'].items():
    lines.append(f"| {phase} | `{row['before_sha256']}` | `{row['after_sha256']}` |")
lines += ['', f'Final head: `{head}`; **28 merge-free commits** above the same base. '
    'The 27 rewritten commits retain their old-to-new map; the final acceptance commit is new. '
    f'[Full map]({relative}/commit-map-final.json); [final verification]({relative}/acceptance-final.json). '
    'The original branch remains at 0ba88ba12. No new-range commit adds gzip evidence; '
    'protected paths are unchanged and the worktree is clean.', '', '| Old | Rewritten |', '|---|---|']
for old, new in history_map['commits'].items():
    lines.append(f'| `{old[:9]}` | `{new[:9]}` |')
lines += [f'| new step-10 acceptance commit | `{head[:9]}` |', '']
report.write_text(before + current + '\n'.join(lines))
assert report.stat().st_size and (evidence / 'acceptance-final.json').stat().st_size
print(json.dumps(manifest, indent=2))
