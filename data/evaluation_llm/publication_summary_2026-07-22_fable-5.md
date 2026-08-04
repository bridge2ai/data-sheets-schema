# [HISTORICAL] D4D Publication Summary — Exemplar Run 2026-07-22 (claude-fable-5)

> ⚠️ **Historical. These figures score records the study has since excluded.**
>
> The inputs were `data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/`
> and the flat pre-run-label layout. That label was archived as **unattestable**
> by `d4d runs archive --unattested` — its bundles were first committed after the
> runs executed, so the bytes those runs consumed cannot be verified. The records
> survive at `data/ATTIC/d4d_concatenated_archived/claudecode_agent/2026-04-10_sonnet-4.6/`,
> so every number here remains traceable to its input; none of it describes the
> current corpus.
>
> Do not cite these as current results. See #286.

Final claudecode_agent scores across the four rubrics for both full D4D and
D4D-core outputs, per Grand Challenge project. All 32 evaluations produced by
the four `d4d-rubric*` agents running `claude-fable-5` at git commit `0e19e85f`.

Supersedes the same-day Claude Opus 4.8 run (archived under
`{rubric}/concatenated/2026-07-22_opus-4.8/` and
`publication_summary_2026-07-22_opus-4.8.*`).

Input D4D file hashes and agent-prompt hashes: see `run_manifest_2026-07-22_fable-5.json`.

## Overall scores (percent)

| Project | rubric10 full | rubric10 core | rubric20 full | rubric20 core | rubric10_semantic full | rubric10_semantic core | rubric20_semantic full | rubric20_semantic core |
|---|---|---|---|---|---|---|---|---|
| AI_READI | 92.0 | 92.0 | 98.8 | 97.6 | 74.0 | 88.0 | 90.5 | 89.3 |
| CHORUS | 82.0 | 82.0 | 92.9 | 91.7 | 72.0 | 84.0 | 92.9 | 92.9 |
| CM4AI | 92.0 | 92.0 | 96.4 | 100.0 | 82.0 | 86.0 | 95.2 | 96.4 |
| VOICE | 98.0 | 98.0 | 100.0 | 100.0 | 88.0 | 94.0 | 98.8 | 98.8 |
| **Mean** | **91.0** | **91.0** | **97.0** | **97.3** | **79.0** | **88.0** | **94.3** | **94.3** |

Percentages above are raw (total/max). Some semantic evaluations exclude
not-applicable questions and report a normalized percentage against an adjusted
maximum (e.g. AI_READI rubric20_semantic full: 76/79 applicable = 96.2%); the
`normalized_percentage` column in `publication_summary_2026-07-22_fable-5.tsv`
carries those values.

## Raw points (total / max)

| Project | rubric10 full | rubric10 core | rubric20 full | rubric20 core | rubric10_semantic full | rubric10_semantic core | rubric20_semantic full | rubric20_semantic core |
|---|---|---|---|---|---|---|---|---|
| AI_READI | 46/50 | 46/50 | 83/84 | 82/84 | 37/50 | 44/50 | 76/84 | 75/84 |
| CHORUS | 41/50 | 41/50 | 78/84 | 77/84 | 36/50 | 42/50 | 78/84 | 78/84 |
| CM4AI | 46/50 | 46/50 | 81/84 | 84/84 | 41/50 | 43/50 | 80/84 | 81/84 |
| VOICE | 49/50 | 49/50 | 84.0/84 | 84/84 | 44/50 | 47/50 | 83/84 | 83/84 |
