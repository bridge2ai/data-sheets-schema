# Archived runs

These runs have a gap in something that determines their output — most often an input bundle whose consumed bytes cannot be verified, because the bundles were first committed after the runs executed. Runs whose provenance was merely reconstructed, but which pin their inputs, schema, model and outputs, are NOT archived: they can be placed and reproduced, and only their hardware is unrecorded.

These are real generations, moved out of `data/d4d_concatenated/`
so `discover()` no longer finds them. Nothing was deleted, and the
layout is preserved, so restoring is the same move reversed:

```bash
d4d runs restore --label <LABEL> --execute
```

## Contents (10 run directories)

- `claudecode_agent/2026-04-10_sonnet-4.6`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast-r2`
- `claudecode_agent/2026-07-23_gpt-5.5-high-fast-r3`
- `claudecode_agent/2026-07-23_gpt-5.6-sol-ultra-fast`
- `claudecode_agent_core/2026-04-10_sonnet-4.6`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r2`
- `claudecode_agent_core/2026-07-23_gpt-5.5-high-fast-r3`
- `claudecode_agent_core/2026-07-23_gpt-5.6-sol-ultra-fast`
