# [HISTORICAL] rubric10 Evaluation Summary (Publication Exemplar Run 2026-07-22)

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

Rubric: `rubric10` | Run: `2026-07-22` | Model (agent/core rows): `claude-fable-5`

## Overall Scores by Method × Project

| Method | AI_READI | CHORUS | CM4AI | VOICE | Mean |
|---|---|---|---|---|---|
| `claudecode` | 34/50 (68.0%) | 18/50 (36.0%) | 33/50 (66.0%) | 37/50 (74.0%) | 61.0% |
| `claudecode_agent` | 46/50 (92.0%) | 41/50 (82.0%) | 46/50 (92.0%) | 49/50 (98.0%) | 91.0% |
| `claudecode_agent_core` | 46/50 (92.0%) | 41/50 (82.0%) | 46/50 (92.0%) | 49/50 (98.0%) | 91.0% |
| `claudecode_assistant` | 39/50 (78.0%) | 35/50 (70.0%) | 33/50 (66.0%) | 37/50 (74.0%) | 72.0% |
| `gpt5` | 3/50 (6.0%) | 5/50 (10.0%) | 28/50 (56.0%) | 1/50 (2.0%) | 18.5% |

claudecode_agent / claudecode_agent_core rows: claude-fable-5, temperature 0.0, evaluated 2026-07-22. Other methods: earlier evaluations (self-described in each JSON).
