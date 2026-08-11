# [HISTORICAL] rubric20 Evaluation Summary (Publication Exemplar Run 2026-07-22)

> ⚠️  **Historical. These figures score records the study has since excluded.**
>
> The inputs were `data/d4d_concatenated/claudecode_agent/2026-04-10_sonnet-4.6/` and the
> flat pre-run-label layout. That label was archived as **unattestable** by
> `d4d runs archive --unattested` — its bundles were first committed after the
> runs executed, so the bytes those runs consumed cannot be verified. The records
> survive under `data/ATTIC/d4d_concatenated_archived/`, so every number here
> remains traceable to its input; none of it describes the current corpus.
>
> Do not cite these as current results. See #286.

Rubric: `rubric20` | Run: `2026-07-22` | Model (agent/core rows): `claude-fable-5`

## Overall Scores by Method × Project

| Method | AI_READI | CHORUS | CM4AI | VOICE | Mean |
|---|---|---|---|---|---|
| `claudecode` | 49/84 (58.3%) | 16/84 (19.0%) | 46/84 (54.8%) | 54/84 (64.3%) | 49.1% |
| `claudecode_agent` | 83/84 (98.8%) | 78/84 (92.9%) | 81/84 (96.4%) | 84.0/84 (100.0%) | 97.0% |
| `claudecode_agent_core` | 82/84 (97.6%) | 77/84 (91.7%) | 84/84 (100.0%) | 84/84 (100.0%) | 97.3% |
| `claudecode_assistant` | 56/84 (66.7%) | 41/84 (48.8%) | 46/84 (54.8%) | 54/84 (64.3%) | 58.6% |
| `gpt5` | 3/84 (3.6%) | 10/84 (11.9%) | 28/84 (33.3%) | 0/84 (0.0%) | 12.2% |

claudecode_agent / claudecode_agent_core rows: claude-fable-5, temperature 0.0, evaluated 2026-07-22. Other methods: earlier evaluations (self-described in each JSON).
