# Archived runs

Intermediate state of the 2026-08-06 schema2 debugging session, superseded by the completed rep of the same label. Archived under #408. The pre-stragglers pair additionally fails the end-of-run gate: its artifacts changed after provenance was recorded, so it cannot be placed as a run.

These are real generations, moved out of `data/d4d_concatenated/`
so `discover()` no longer finds them. Nothing was deleted, and the
layout is preserved, so restoring is the same move reversed:

```bash
d4d runs restore --label <LABEL> --execute
```

## Contents (9 run directories)

- `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/CHORUS_d4d.yaml`
- `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/CHORUS_api_progress.json`
- `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/CHORUS_d4d_core.yaml`
- `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2.superseded-dual-writer/CHORUS_reasoning.jsonl`
- `intermediate/CHORUS_audit.json`
- `intermediate/CHORUS_core.yaml`
- `intermediate/CHORUS_core_2.yaml`
- `intermediate/CHORUS_full.yaml`
- `intermediate/CHORUS_full_2.yaml`

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
