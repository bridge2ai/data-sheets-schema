# Canonical selection, agentic route, 2026-11-22

From 2026-11-22 the canonical agentic datasheet for each project is one replicate of the
series `2026-11-22b_claude-opus-5-5-claudecode-generic-v9` (generic_v9 prompt,
claude-opus-5-5 at effort high, schema 3.2.1, advisor tool off, no MCP servers).

| Project | Canonical record | Superseded agentic canonical |
|---|---|---|
| AI_READI | `2026-11-22b_…_rep2` | `2026-08-28_claude-opus-5-claudecode-generic-v6_rep1` |
| CHORUS | `2026-11-22b_…_rep2` | `2026-08-28_claude-opus-5-claudecode-generic-v6_rep3` |
| CM4AI | `2026-11-22b_…_rep1` | `2026-08-28_claude-opus-5-claudecode-generic-v6_rep3` |
| VOICE | `2026-11-22b_…_rep3` | `2026-08-28_claude-opus-5-claudecode-generic-v6_rep3` |
| VOICE_PEDIATRIC | `2026-11-22b_…_rep2` | `2026-08-11_claude-opus-5-claudecode-generic_rep2` |

## How it was chosen

Recorded with `d4d runs select --project P --config 2026-11-22b_claude-opus-5-5-claudecode-generic-v9 --execute`.
Each pick is the command's own rule: both records validate, then most populated slots, then
lowest label. The command calls every margin here thin. The API-route canonicals are untouched.

The owner approved these five on 2026-11-22 after seeing the semantic rubric scores for all
fifteen replicates (`rubric_scores.tsv`). The rubrics agree with the rule within noise for
four projects. For CM4AI the rubrics put rep 3 ahead (35 against 29 of 88 on rubric20); rep 1
was kept because it carries the most content, because the CM4AI records were scored as
collections (minimum per item across four component datasets, parent metadata not inherited),
and because the selection command cannot record a choice other than its rule's.

## What a reader should know

- No one has reviewed these records for content. The checks behind them show that each value
  points at real source text, not that each value is right.
- Two of the five have values without a receipt: CHORUS rep 2 (12 of 96) and VOICE_PEDIATRIC
  rep 2 (23 of 306). Both pass the registered receipt floor.
- The superseded records stay on disk, marked in their own provenance.

## Comparisons made before this date

Arm-comparison tables computed before 2026-11-22 used the superseded records above as the
agentic arm. The new canonicals differ from them in three ways at once: prompt version
(v9 against v6, and the original generic prompt for VOICE_PEDIATRIC), model (Opus 5.5 against
Opus 5) and schema (3.2.1 against 2.0.0). Do not regenerate an earlier table against the new
canonicals without saying so, and do not read a difference between these records and an API
arm as the effect of the runtime alone.
