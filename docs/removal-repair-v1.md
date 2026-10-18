# Opt-in restore-only removal repair

`removal_repair_version=1` closes the API runner's software gap in #2923:
the existing removals-v3 detector can report a deleted phase-1 value with no
covering audit finding, but schema repair and report dispositions do not
restore that value. This policy checks the record itself after normal
reconciliation and schema repair.

The policy is a separate runtime condition. It supports API renderer 8 only;
native/direct arms and later evidence-protocol renderers are refused. The
default is 0, omitted from historical render specs. Existing templates,
renderer output, cache keys, source bundles and registered audit28 conditions
are unchanged. The independent `api_playbook_version=1` option may be selected
alongside it; neither option implies the other.

The CLI exposes the option on `api render-prompt`, `api plan`, `api run` and
`api batch`. A free inspection example is:

```bash
poetry run d4d api plan --project EXTERNAL --bundle /path/to/source.txt \
  --manifest none --label new-removal-condition --condition generic \
  --removal-repair-version 1 --json
```

The plan names the conditional repair and subsequent report refresh; their
input sizes depend on the actual generated records and are not included in
the unconditional phase token estimate. A study run requires its own new
condition registration and label. This software change authorizes no paid
canary or release of held runs (#2605, #2714).

The frozen `src/download/prompts/removal_repair_v1.md` artifact is recorded
with its SHA256 and version in the render spec, prompt-file inventory,
generation input identity and assembly digest. Comparisons therefore expose
the changed assembly; a resume cannot silently add/remove the policy. Prompt
pin ancestry must survive merging this branch.

The runner reads the original full record and audit from generation-attested
snapshots, never a directory glob. Receipt-bearing conditions also require
the attested receipt. It retains the existing detector's counts and
limitations. Diagnostic output normally lists at most 50 paths; this runtime
requests the complete list without changing classification or counts.

If unfounded removals remain, the generation ledger admits one restore-only
repair. Its request contains the schema digest, original/current records,
unchanged audit, receipt when applicable, and removed paths with their exact
original values. It asks for a complete candidate full record. The response
cannot amend the audit or clear the check through disposition prose.

Before replacing either output, the runner requires exact typed restoration
at each original structural role, using the existing identity join for list
entries. It preserves populated current values, rejects novel material or
restoration of founded deletions, validates the candidate and derived core,
and rechecks that the request inputs did not change. Ambiguous identity joins
are refused. Accepted changes re-derive the core and refresh the report;
later schema repair cannot remove the restored values again.

The optional `removal_repair` provenance block records policy, attempt,
before/final detector readings, response hash, usage identity and actual
findings. `removals` carries the final reading where one could be obtained.
Unusable evidence is unverified. A rejected/truncated/failed response retains
the prior outputs and remaining counts. The ledger preserves the attempt
allowance and terminal refusal even if progress or a response is lost. A
later local edit or passing check cannot erase that terminal generation.
Completed runs recompute the check against their attested snapshot bytes.
An interruption between restoration and completed report refresh blocks
automatic continuation; it cannot skip the refresh or buy a second one
(#4250). A failed refresh remains terminal with its recorded charge. Once
the refresh and its progress pins are saved, later recovery retains the
accepted repair's before-count, response identity and derivation without
repeating either call. The final removal reading is still recomputed.
The verified full/core SHA256 pins also survive in the accepted outcome.
Both outputs must still match at resume and immediately before final
provenance is written; zero remaining removals cannot excuse an unrelated
rewrite, added fact or changed core (#4255). Missing, unreadable or incomplete
progress after an accepted repair requires recovery or an explicitly fresh
generation. The ledger independently refuses original generation and shape
repair calls after that admission, so loss of progress cannot spend them
again (#4256).
Rejected responses and failed report refreshes also reread the actual final
record before recording residual counts (#4257). A later clean reading never
clears the original refusal; unavailable evidence produces an unavailable
final reading, not a reused pre-call count.

The original #2923 software and replay criteria are
[complete](https://github.com/bridge2ai/data-sheets-schema/issues/2923#issuecomment-5965432187).
Restoring an original value does not establish that it is supported by a
source. Evidence-backed audit amendments, independent curation, native/direct
integration and empirical acceptance of a freshly registered condition remain
separate extensions and scientific decisions. The independent
self-disclaimer (#2913) and name-grounding (#2918) instruments retain their
own runtime/canary scope. No historical record or block is backfilled here.
