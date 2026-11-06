"""#4354 U1 2026-11-06: append exact round-two handoff and one own STATUS row.
Inputs: committed worktree, packet metadata and scratch evidence; outputs: the
assigned external report and coordination entry. No network or protected edits.
"""
from datetime import datetime, timezone
import json
import re
from native_u1_round2_20261106 import ROOT, SCRATCH, OUT, COMPOSED, HEAD, run

report=ROOT.parent/'plans/reviews/native_u1_2026-11-06.md'
status=ROOT.parent.parent/'data-sheets-schema/notes/coordination/STATUS.md'
commit=run(['git','rev-parse','HEAD']).decode().strip()
assert commit!=HEAD
assert not run(['git','status','--porcelain'])
evidence=json.loads((OUT/'round2_evidence.json').read_text())
sidecar_meta=next(p for p in evidence['packets'] if p['target']=='tests/utils/run_spec_boundary_contracts.json')
select_change=next(p for p in sidecar_meta['function_pin_updates'] if p['body_changed'])
roster=next(item for item in evidence['logs'] if item['path'].endswith('r2-api-regressions-retry2.log'))
summaries=[line.strip('= ') for line in roster['tail'] if re.search(r'\d+ (?:failed|passed).* in [0-9]',line)]
roster_note=('Full 66-file roster terminal result: **'+summaries[-1]+'**.' if summaries else
    'Full 66-file roster did not complete: **'+roster['tail'][-1]+'**. '
    'Partial terminal test events (not a complete suite result): '+str(roster.get('terminal_test_event_counts',{}))+'.')
roster_status=summaries[-1] if summaries else 'incomplete ('+roster['tail'][-1]+')'
rows=[]
for meta in evidence['packets']:
    rows.append(f"| `{meta['target']}` | `{meta['preimage_sha256']}` | `{meta['postimage_sha256']}` |")
logs=[]
for item in evidence['logs']:
    name=item['path'].rsplit('/',1)[1]
    tail='; '.join(line for line in item['tail'] if line and not line.startswith('-- Docs:'))
    logs.append(f'| `{name}` | {tail.replace("|", "/")} |')
failures=[]
for name in ('r2-api-regressions-retry2','r2-specificity-guards','r2-d76-inventory'):
    path=SCRATCH/(name+'.log')
    if path.exists():
        failed=[line for line in path.read_text(errors='replace').splitlines() if line.startswith(('FAILED ', 'ERROR '))]
        if not failed:
            failed=[line for line in path.read_text(errors='replace').splitlines()
                    if line.startswith('[gw') and (' FAILED ' in line or ' ERROR ' in line)]
        failures.append('**'+name+':**\n\n```text\n'+'\n'.join(failed)+'\n```')
text=f'''

## Round 2 — corrected packets, scratch composition, remaining acceptance failures

**BLOCKED for integration.** The two assigned packet gaps are corrected. All four
patches apply together, their scratch postimages match their JSON hashes, strict
prompt checking passes, all 14 API instruction renders match M7 byte-for-byte,
and the corrected focused native suite passes 194 tests. Acceptance remains
blocked by the D76 public-boundary inventory and a scanner exit 2; neither is
represented as a passing gate or a no-new-findings result.

Local round-two commit: `{commit}`. Source archive: `{HEAD}` at
`{COMPOSED}`. The archive has private Git metadata with a read-only local object
alternate for real registry commit/blob checks; no remote is configured or used.
The only test overlays are the two committed test updates (hashes in
`round2_evidence.json`) and the parity fixture plugin. The FAIRSCAPE gitlink
`8c80311d7d8b0fadac07dca9567d632103691f48` was populated from an exact local
submodule archive after collection exposed three missing-import errors; no
download or installation was used. Production bytes are the
U1 archive plus the four explicit packets. Worktree protected files and checker
remain byte-identical to M7. No production source was edited in round two.

### Corrected proposal packets

Packet directory: `scripts/adhoc/native_u1_packets/` in the U1 worktree.
The hook and caller companion are unchanged from round one. JSON metadata and
patches provide the exact proposals; scratch execution does not authorize AGY
to install them or constitute independent approval.

| Target | Preimage SHA-256 | Scratch-validated postimage SHA-256 |
|---|---|---|
{chr(10).join(rows)}

- **Prompt pins:** the real `d4d api prompts pin --file ... --reason ...` CLI ran
  in `scratch-native-u1/pins-41b7169f6`. Both new records pin
  `41b7169f6296c69201fc46389082c441e7d7165c`; their committed blobs match their
  declared hashes. All existing pin records remain identical. The CLI also
  records body hashes, actual local date and scratch repository provenance.
  Remote reachability was not checked: AGY must publish the U1 ancestry with the
  integration branch. The old unpushed donor commit is no longer used.
- **D76 rebind:** proposal-only producer
  `scripts/adhoc/native_u1_round2_20261106.py`, adapted from the reviewed
  `04c40b517` / `1222b8ce3` procedure. It preserves all 21 identities, source paths,
  modes, caller preconditions, approval and historical provenance. Only
  `data_sheets_schema.shared_generation.select` changes its function hash;
  every function's source offsets and length are recomputed from its decorated
  AST extent. Metadata records each before/after pin, module identities,
  baseline sidecar hash and producer hash. No new function exemption is added.
  The checker remains `a379e93a0065dc927835b1417cabcb926e33eeb333416c768237bc50d2dc6237`.
  The `select` function hash changes from
  `{select_change['before']['function_sha256']}` to
  `{select_change['after']['function_sha256']}`; its extent changes from
  lines {select_change['before']['function_start_line']}–{select_change['before']['function_end_line']}
  to {select_change['after']['function_start_line']}–{select_change['after']['function_end_line']}.
- `git apply --check` accepts all four packets together in the untouched
  worktree. Actual application occurred only under the authorized scratch root.
  `native_u1_round2_evidence_20261106.py` rechecks protected preimages, all four
  composed postimages, patch hashes, retained contract fields and checker bytes.

### Validation and evidence

Every pytest launch used the existing Python 3.13.12 environment, at most two
xdist workers and a 3,600-second timeout with process-group termination. No
provider credentials/endpoints were inherited through the launcher; its Python
audit guard denies network and named native executables. No native executable,
provider call, fetch, push, gh command, PR or merge occurred. This is not the
Python 3.12 CI matrix. The full explicit regression roster remains the 66 files
recorded in `scratch-native-u1/regression-roster.txt`.

{roster_note}

The canary used the same bounded launcher and `-n 2` path as the regression
commands and persisted a nonempty passing log. It proves synthetic native
render/replay, not a native execution or performance result.
Ordering limitation: the canary log closed at 02:13:41Z, before the first
regression started at 02:14:10Z, but the nonempty log was inspected just after
that regression launch. Thus the initial launch missed the strict
verify-before-fan-out order; all later validation used the inspected canary.

| Evidence log under scratch-native-u1 | Actual terminal result |
|---|---|
{chr(10).join(logs)}

Raw render comparison: `r2-api-render-parity.json`, **14/14 identical**, without
normalization. Actual M7 archive `baseline-8bc90e93d` and the composed tree used
the same per-node synthetic input paths; all 14 tests passed on each tree.
Coverage: generic, retired tuned replay, generic_v2–v9, shared-v1 generic_v10,
both shared-v2 routing modes, and BC1. Both trees used their own installed source
and assets; no baseline module swapping was used in round two.

Focused suites: contract, evidence, selection, render, schema-metadata reuse and
selector refusals. Added 26 isolated rejection cases start with a valid captured
selection: enabled/True/False for each of six companion axes, five invalid native
selector values, and three incompatible old registration fields. The original
six probes remain. Valid-native construction/replay now verifies the exact
shared admission and a `None` API-mode result; mixed axes must refuse before
that call. These test overlays do not change production behavior.
Full `pytest tests --collect-only -q` passed with **23,196 tests collected**
after the exact local FAIRSCAPE gitlink was populated.

### Findings and disposition

1. **R2-F1, fixed test assumption:** the first focused run was 193 passed /
   1 failed because the donor test forbade any shared-selector call. The packet
   intentionally restores that call. Updated the test to observe validated
   dispatch, no selected API mode, and early mixed-axis refusal; rerun 194 passed.
2. **R2-F2, unresolved D76 contracts:** the rebound protected source/function
   tests pass, but the closed inventory reports six unclassified public helpers
   in `native_shared_render.py`: `validate_spec`, `bind_selection`, `metadata`,
   `restore`, `commands`, `instruction`. The standalone inventory is 27 passed /
   1 failed. Rebinding the original 21 contracts cannot grant these new helpers
   exemptions. Their actual caller/entry contracts need a bounded implementation
   and review, followed by unchanged-checker validation.
3. **R2-F3, unresolved scanner admission:** the composed scanner exits **2** with
   `separate native shared render route (unsupported delegated admission prefix)`.
   `derive_native_shared_route` hardcodes five companion axes; U1 also rejects
   `bounded_carry_version`. The BC1 refusal was retained, and scanner code was
   not relaxed. Separate source inspection shows the derivation also requires
   the later `render_native_shared` CLI consumer, absent from this U1 committed
   tree; that is an anticipated next boundary, not a second observed scanner
   run. M7's retained baseline has nine violations, but there is no completed
   after scan, so **no no-new-findings claim** is possible. The lead must resolve
   staged U1 versus U4/U5 scanner acceptance without weakening admission.
4. **R2-F4, unresolved guard-suite failures:** 463 passed, 9 failed, 21 setup
   errors. The retained log includes the native admission-prefix ConfigError,
   the model-facing closure's missing `native_shared_stage` and
   `native_shared_receipts`, and a deterministic sys.path expectation mismatch.
   The latter was not compared against a fresh M7 test run and is not labelled
   inherited. The complete final failure/error node lists follow; no failed
   guard was removed or relaxed.
5. **R2-F5, unresolved historical BC1 source pin:**
   `test_bc1_selection.py::test_proposal_is_exact_and_does_not_modify_protected_source`
   fails in the composed tree. Its applied-proposal branch requires the old
   `notes/bc1_shared_generation_patch_2026-10-27.json` whole-source postimage,
   while this composition adds the native hook. That historical manifest and
   its test were not silently rotated; the integration needs an explicit
   reviewed disposition preserving the historical proposal evidence.
6. **R2-F6, full-roster deadline:** the final 66-file / 1,570-node attempt
   reached the fixed 3,600-second deadline and was terminated with exit 124.
   Its completed test events are 1,280 passed, 1 failed, 16 errors and
   1 xfailed; these are partial events, not a completed pytest summary. The
   uncompleted remainder is not credited. No deadline extension, worker
   increase or test exclusion was used. The retained log identifies completed
   nodes and errors; it does not diagnose the remaining cases' runtime cause.

{chr(10).join(failures)}

No GitHub issues were filed because this task explicitly prohibits network and
gh. The local findings above are the handoff records for AGY's issue workflow.
The corrected packets are reviewable, not accepted integration. A21 rebuild,
independent review, later native units and any executable/launch remain outside
this task.

### Quiet-window accounting

No lock was present when preparation, canary and the first full regression
started. U0 created a lock at **2026-11-06T02:15:15.737617Z**, expected end
02:50:15.737617Z. A subsequent prompt-check launch refused immediately. On
noticing the lock, U1 inspected its own process group and terminated group 18279
at approximately **02:16:08Z**; the original regression log records exit -15 at
22% progress and is not credited. There was therefore approximately 53 seconds
of overlap after lock creation; this is disclosed, not claimed quiet compliance
for that interval. No other session's process or lock was changed. After a
60-second wait, the lock was observed absent at **02:17:34Z**, before resuming
validation. The full roster was restarted under a separate retained log.

A second U0 lock began at **02:35:34.834198Z**, with expected end 03:11:04Z.
The next scheduled check detected it, and U1 terminated its verified group
70253 at approximately **02:36:33Z** (about 58 seconds of overlap). The retry
log is retained with exit -15, one failure marker and setup-error markers but
no completed suite summary. It is not credited as a complete run. Both quiet
window overlaps are reported for the lead's timing-evidence disposition.
The second lock was observed absent at **02:38:30Z** before short checks resumed.

Evidence/producer paths: `scripts/adhoc/native_u1_round2_20261106.py`,
`native_u1_round2_checks_20261106.py`, `native_u1_round2_parity_plugin_20261106.py`,
`native_u1_round2_evidence_20261106.py`, `native_u1_round2_report_20261106.py`, and
`native_u1_packets/round2_evidence.json`. The pin producer was updated so it
cannot silently recreate the old donor pins. One round-two STATUS entry is
added under codex, then this task stops.
'''
old=report.read_text()
assert '\n## Round 2 —' not in old
report.write_text(old+text)
assert report.read_text()==old+text
stamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
entry=f'\n- **{stamp} — Native U1 round 2, `{commit[:9]}`: corrected pins and D76 sidecar proposals; all four patches apply and protected worktree/checker unchanged. Scratch: 14/14 API render byte parity, 194 focused native passes, strict pins pass, 23,196 tests collected. Roster: {roster_status}. D76 inventory still fails on six new native helper contracts and scanner exits 2 (five-axis prefix versus BC1 refusal); historical BC1 source-pin and guard failures retained. Report: `d4d-executions/plans/reviews/native_u1_2026-11-06.md`, Round 2. Two quiet-lock overlaps and initial canary inspection-order lapse disclosed; interrupted runs retained. BLOCKED for integration; no network/native execution. AGY/lead disposition next; stopped.**\n'
current=status.read_text(); start=current.index('\n### codex\n'); end=current.find('\n### ',start+1)
if end<0: end=len(current)
assert f'Native U1 round 2, `{commit[:9]}`' not in current
updated=current[:end]+entry+current[end:]
status.write_text(updated)
assert status.read_text()==updated
print(str(report)); print('One STATUS entry written; stop.')
