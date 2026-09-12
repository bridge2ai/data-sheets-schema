# CBORG rescore and v9 generation canary — 2026-09-12

The user requested “rescore with CBORG API” and separately approved adding a v9 generation canary using existing source bundles. This is a new provider condition beside the completed September 11 reference run. Earlier evaluations, failed attempts and semantic errata remain unchanged.

## Evaluation registration

- Cohort: the same 24 public v7/v8 full D4Ds, both semantic rubrics; 48 primary ratings plus eight rubric10 repeat ratings (56 planned).
- Manifest: `notes/reference_rescore_2026-09-12_cborg/manifest.json`; SHA256 `ab13d9e824a47a70ff741372e8ac6a7abc1873b0b487959b04f01bdd00f0ee54`.
- Definitions, rubric text, schemas, complete scoring prompts and 24 input byte hashes match the prior registered instrument. The new manifest preserves 258 prior evaluation files.
- Model selector: `claude-opus-5[1m]`, effort high, temperature unspecified. The accepted runtime must identify `claude-opus-5` with the same existing alias-evidence checks.
- Transport: Claude Code 2.1.269 with the existing isolated runner through `https://api.cborg.lbl.gov`. The adapter uses `CBORG_API_KEY` in memory, selects the CBORG base URL explicitly, and clears inherited Anthropic model/auth overrides and alternate cloud-provider switches. Bare mode excludes keychain/OAuth discovery; safe/restricted modes and exact-validator tool permissions remain.
- Budget: the registered CLI maximum remains $5 per attempt. Original usage and excluded attempts will be retained; CLI-reported cost is not an independently reconciled CBORG invoice.
- Canary: CHORUS v7 rep1, rubric10, rating1. It uses the same adapter, foreground shell environment, sequential launch mode and output locations as the fill. No remaining rating starts until exact output, schema, arithmetic, source-aligned item identities, runtime identity, quoted definition, final Write binding and an inspected review pass.
- No automatic retries. A failed attempt stops new launches and is retained. A diagnosed retry is a fresh original measurement under its registered condition.
- The fill remains sequential so the canary exercises the same launch/concurrency mode. The planned output paths are separate from every prior condition.
- Rubric20 Q19 still allows complete textual provenance or a graph. The old semantic errata are preserved and do not prejudge the new measurements. Mechanical acceptance alone cannot make a score rubric-conformant; inspect new Q19 rationales before final manuscript interpretation.

## Generation registration

- One CHORUS record only, condition `generic_v9`, baseline arm, label `2026-09-12_claude-opus-5-api-generic-v9_rep1`.
- Use the existing `data/preprocessed/concatenated/CHORUS_preprocessed.txt` bundle and recorded chunk/source metadata. No downloads or factual reuse from an earlier D4D.
- Use the generic v9 prompt already on main, current schemas and current check instruments. Do not change prompt/schema/checker content during this canary.
- Use CBORG's unprefixed `claude-opus-5` route and the generation runner's recorded adaptive-thinking/default-effort configuration. This differs from the evaluation CLI's requested high effort and will not be conflated with it.
- Run through `d4d api batch` restricted to one project and one replicate, with the current v7 baseline `2026-09-01_claude-opus-5-api-generic-v7`. Retain artifacts and the actual gate verdict even if the canary fails.
- The current offline plan and model catalogue observation are in [v9_generation_plan.json](v9_generation_plan.json). Listed input-token counts are estimates; conditional repair/re-address/report calls and returned usage will be recorded by the existing runner.
- The user approved a canary only. Do not expand to a v9 production cohort without further scope authorization. A generated canary record is not a released manuscript cohort.

## Commands

Run in the project Poetry environment, from the repository root. The CBORG key must be inherited as an environment variable, never written to a command, manifest or log.

```bash
python scripts/reference_rescore_cborg.py canary
# Inspect the original output and trace; write the canary review before acceptance.
python scripts/reference_rescore_cborg.py accept-canary
python scripts/reference_rescore_cborg.py remaining
python scripts/reference_rescore_cborg.py report
python scripts/reference_rescore_cborg.py audit
```

The generation launch clears a potentially inherited direct Anthropic key so the existing API client's credential precedence selects CBORG:

```bash
env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN d4d api batch --projects CHORUS --replicates 1 --condition generic_v9 --label-prefix 2026-09-12_claude-opus-5-api-generic-v9 --canary-baseline 2026-09-01_claude-opus-5-api-generic-v7 --yes
```

## Pre-spend checks

The CBORG model catalogue lists `claude-opus-5`; its observed route is `vertex_ai/claude-opus-5`, with 1,000,000 input and 128,000 output token limits. These are pre-run catalogue observations, not a guarantee about the identity returned by a later request. Endpoint/auth setup follows [CBORG's Claude Code documentation](https://cborg.lbl.gov/tools_claudecode/).

The new evaluation registration exactly matches both prior instrument definitions and all 24 input hashes. The generation batch dry-run resolves exactly one CHORUS job and makes no model calls. Offline provider-selection and inherited-runner tests are required before the paid canaries.
