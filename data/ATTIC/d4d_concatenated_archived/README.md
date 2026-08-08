# Archived runs

Real generations, moved out of `data/d4d_concatenated/` so `discover()`
no longer finds them. Nothing was deleted, and the layout is preserved,
so restoring is the same move reversed:

```bash
d4d runs restore --label <LABEL> --execute
```

One section per archiving run, appended in order. The reason is a claim
about the runs it names and only about those, so the sections are kept
separate rather than merged into a running total.

## Archived before 2026-08-08 — 85 file(s) in 16 run directories

These runs have a gap in something that determines their output — most often an input bundle whose consumed bytes cannot be verified, because the bundles were first committed after the runs executed. Runs whose provenance was merely reconstructed, but which pin their inputs, schema, model and outputs, are NOT archived: they can be placed and reproduced, and only their hardware is unrecorded.

*(Reconstructed 2026-08-08. The per-invocation detail for these was lost: the writer overwrote this file on every run until #408 fixed it. The directories themselves are intact and listed below.)*

- `claudecode_agent/2026-04-10_sonnet-4.6/AI_READI_d4d.yaml`
- `claudecode_agent/2026-04-10_sonnet-4.6/CHORUS_d4d.yaml`
- `claudecode_agent/2026-04-10_sonnet-4.6/CM4AI_d4d.yaml`
- `claudecode_agent/2026-04-10_sonnet-4.6/VOICE_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast/AI_READI_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast/CHORUS_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast/CM4AI_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast/VOICE_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast-r2/AI_READI_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast-r2/CHORUS_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast-r2/CM4AI_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast-r2/VOICE_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast-r3/AI_READI_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast-r3/CHORUS_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast-r3/CM4AI_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast-r3/VOICE_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d.yaml`
- `claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d.yaml`
- `claudecode_agent_core/2026-04-10_sonnet-4.6/AI_READI_d4d_core.yaml`
- `claudecode_agent_core/2026-04-10_sonnet-4.6/AI_READI_provenance.yaml`
- `claudecode_agent_core/2026-04-10_sonnet-4.6/CHORUS_d4d_core.yaml`
- `claudecode_agent_core/2026-04-10_sonnet-4.6/CHORUS_provenance.yaml`
- `claudecode_agent_core/2026-04-10_sonnet-4.6/CM4AI_d4d_core.yaml`
- `claudecode_agent_core/2026-04-10_sonnet-4.6/CM4AI_provenance.yaml`
- `claudecode_agent_core/2026-04-10_sonnet-4.6/VOICE_d4d_core.yaml`
- `claudecode_agent_core/2026-04-10_sonnet-4.6/VOICE_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/AI_READI_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/AI_READI_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/AI_READI_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/CHORUS_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/CHORUS_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/CHORUS_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/CM4AI_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/CM4AI_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/CM4AI_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/VOICE_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/VOICE_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast/VOICE_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/AI_READI_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/AI_READI_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/CHORUS_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/CHORUS_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/CM4AI_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/CM4AI_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/CM4AI_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/VOICE_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2/VOICE_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/AI_READI_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/AI_READI_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/AI_READI_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/CHORUS_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/CHORUS_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/CHORUS_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/CM4AI_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/CM4AI_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/CM4AI_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/VOICE_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/VOICE_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3/VOICE_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/AI_READI_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CHORUS_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/CM4AI_reconciliation.md`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_d4d_core.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_provenance.yaml`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast/VOICE_reconciliation.md`
- `claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_d4d.yaml`
- `claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d.yaml`
- `claudecode_agent_crate_only/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_d4d.yaml`
- `claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_d4d_core.yaml`
- `claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_provenance.yaml`
- `claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_reconciliation.md`
- `claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d_core.yaml`
- `claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_provenance.yaml`
- `claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_reconciliation.md`
- `claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_d4d_core.yaml`
- `claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_provenance.yaml`
- `claudecode_agent_crate_only_core/2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_reconciliation.md`

## Archived 2026-08-08 — 46 file(s) in 9 run directories

Intermediate state of the 2026-08-06 schema2 debugging session, superseded by the completed rep of the same label. Archived under #408. The pre-stragglers pair additionally fails the end-of-run gate: its artifacts changed after provenance was recorded, so it cannot be placed as a run. Also here, outside the run layout, the three `.failed-core-degeneration` files from `2026-08-05_claude-opus-5-generic-v3_rep1`.

- `claudecode_agent/2026-08-05_claude-opus-5-generic-v3_rep1/AI_READI_d4d.yaml.failed-core-degeneration`
- `claudecode_agent/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-notes/CHORUS_d4d.yaml`
- `claudecode_agent/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/CHORUS_d4d.yaml`
- `claudecode_agent/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/CHORUS_d4d.yaml`
- `claudecode_agent_core/2026-08-05_claude-opus-5-generic-v3_rep1/AI_READI_api_progress.json.failed-core-degeneration`
- `claudecode_agent_core/2026-08-05_claude-opus-5-generic-v3_rep1/AI_READI_reasoning.jsonl.failed-core-degeneration`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/CHORUS_api_progress.json`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/CHORUS_d4d_core.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/CHORUS_provenance.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/CHORUS_reasoning.jsonl`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/CHORUS_reconciliation.md`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/intermediate/CHORUS_reconcile_core.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/intermediate/CHORUS_repair_core_r1.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/intermediate/CHORUS_repair_core_r1_2.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/intermediate/CHORUS_repair_core_r2.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/intermediate/CHORUS_repair_core_r2_2.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-dual-writer/intermediate/CHORUS_report.md`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-notes/CHORUS_api_progress.json`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-notes/CHORUS_d4d_core.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-notes/CHORUS_reasoning.jsonl`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-notes/intermediate/CHORUS_audit.json`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-notes/intermediate/CHORUS_core.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-notes/intermediate/CHORUS_full.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-notes/intermediate/CHORUS_reconcile_full.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/CHORUS_d4d_core.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/CHORUS_provenance.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/CHORUS_reasoning.jsonl`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/CHORUS_reconciliation.md`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/intermediate/CHORUS_audit.json`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/intermediate/CHORUS_core.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/intermediate/CHORUS_full.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/intermediate/CHORUS_reconcile_core.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/intermediate/CHORUS_reconcile_full.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/intermediate/CHORUS_repair_core_r1.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/intermediate/CHORUS_repair_core_r2.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/intermediate/CHORUS_repair_full_r1.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/intermediate/CHORUS_repair_full_r2.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1.superseded-pre-stragglers/intermediate/CHORUS_report.md`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/CHORUS_api_progress.json`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/CHORUS_d4d_core.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/CHORUS_reasoning.jsonl`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/intermediate/CHORUS_audit.json`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/intermediate/CHORUS_core.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/intermediate/CHORUS_core_2.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/intermediate/CHORUS_full.yaml`
- `claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/intermediate/CHORUS_full_2.yaml`

## Two ad-hoc conventions, retired 2026-08-08 (#408)

Before this directory was used for them, intermediate states were kept in place
under `data/d4d_concatenated/` with a dotted suffix on the run directory or the
file. Two such conventions grew up, neither documented anywhere, and nothing
read either of them:

| suffix | what it meant |
|---|---|
| `.superseded-<reason>` on a run directory | a mid-debugging state of a label, kept while the completed rep was produced |
| `.failed-core-degeneration` on a file | an output from an attempt that failed core generation |

They caused two problems. `discover()` walks `data/d4d_concatenated`, so a
suffixed run directory is still a run as far as every analysis path is
concerned — and one of them,
`2026-08-06_..._rep1.superseded-pre-stragglers`, had artifacts that changed
after its provenance was recorded, so it failed the end-of-run gate. Every
local `make test` reported two failures that had nothing to do with the change
under test, which is how a real failure gets ignored. They also sat untracked
in `git status` indefinitely, since committing a state the repository's own
test rejects is not an option either.

Everything under both conventions is now here. **Use `d4d runs archive`
instead**: it moves rather than renames, records a reason in this file, and is
reversed exactly by `d4d runs restore`.

Also archived here, outside the run layout, are the three
`.failed-core-degeneration` files from
`2026-08-05_claude-opus-5-generic-v3_rep1`, under their original method and
label path.

One thing was deleted rather than archived:
`claudecode_agent_core/2026-08-07_test_rep1/TESTPROJ_provenance.yaml`, a
smoke-test record for a fake project written three minutes before
`d4d provenance record --prompt` was committed. It is regenerable in one
command and describes no real generation.
