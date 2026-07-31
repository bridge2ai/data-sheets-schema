# Archived runs

These runs have a gap in something that determines their output — most often an input bundle whose consumed bytes cannot be verified, because the bundles were first committed after the runs executed. Runs whose provenance was merely reconstructed, but which pin their inputs, schema, model and outputs, are NOT archived: they can be placed and reproduced, and only their hardware is unrecorded.

These are real generations, moved out of `data/d4d_concatenated/`
so `discover()` no longer finds them. Nothing was deleted, and the
layout is preserved, so restoring is the same move reversed:

```bash
d4d runs restore --label <LABEL> --execute
```

## Contents (12 run directories)

- `2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_d4d.yaml`
- `2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d.yaml`
- `2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_d4d.yaml`
- `2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_d4d_core.yaml`
- `2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_provenance.yaml`
- `2026-07-28_claude-opus-5-crateonly_rep1/CM4AI_reconciliation.md`
- `2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_d4d_core.yaml`
- `2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_provenance.yaml`
- `2026-07-28_claude-opus-5-crateonly_rep2/CM4AI_reconciliation.md`
- `2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_d4d_core.yaml`
- `2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_provenance.yaml`
- `2026-07-28_claude-opus-5-crateonly_rep3/CM4AI_reconciliation.md`
