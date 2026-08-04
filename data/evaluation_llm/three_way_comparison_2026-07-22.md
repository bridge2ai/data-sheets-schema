# [HISTORICAL] Three-way evaluation comparison — 2026-07-22

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

Same D4D inputs (2026-04-10 Sonnet 4.6 full + core outputs), three generations of
evaluation, per rubric:

| Layer | Location | Evaluator |
|---|---|---|
| **prior** | `_archive_2026-07-22/` | rubric10/20: hybrid-heuristic-evaluator (2025-12-08, full only); semantic rubrics: LLM judge, 2026-05-13/14 (stamped claude-sonnet-4-5; stamp is template-derived) |
| **opus** | `2026-07-22_opus-4.8/` | Claude Opus 4.8 (morning run 2026-07-22, operator-confirmed; JSON stamps are template text) |
| **fable** | top level (exemplar) | claude-fable-5 (final run 2026-07-22) |

## rubric10

| Project | Variant | prior | opus | fable | Δ fable−opus |
|---|---|---|---|---|---|
| AI_READI | full | 38/50 (76.0%) | 41/50 (82.0%) | 46/50 (92.0%) | +10.0 |
| AI_READI | core | — | 41.0/50 (82.0%) | 46/50 (92.0%) | +10.0 |
| CHORUS | full | 35/50 (70.0%) | 40.5/50 (81.0%) | 41/50 (82.0%) | +1.0 |
| CHORUS | core | — | 40.0/50 (80.0%) | 41/50 (82.0%) | +2.0 |
| CM4AI | full | 38/50 (76.0%) | 39.0/50 (78.0%) | 46/50 (92.0%) | +14.0 |
| CM4AI | core | — | 34.0/50 (68.0%) | 46/50 (92.0%) | +24.0 |
| VOICE | full | 37/50 (74.0%) | 47/50 (94.0%) | 49/50 (98.0%) | +4.0 |
| VOICE | core | — | 47.0/50 (94.0%) | 49/50 (98.0%) | +4.0 |
| **Mean** | | **74.0% (n=4)** | **82.4%** | **91.0%** | **+8.6** |

## rubric20

| Project | Variant | prior | opus | fable | Δ fable−opus |
|---|---|---|---|---|---|
| AI_READI | full | 58/84 (69.0%) | 82.0/84 (97.6%) | 83/84 (98.8%) | +1.2 |
| AI_READI | core | — | 80/84 (95.2%) | 82/84 (97.6%) | +2.4 |
| CHORUS | full | 41/84 (48.8%) | 76.0/84 (90.5%) | 78/84 (92.9%) | +2.4 |
| CHORUS | core | — | 75.0/84 (89.3%) | 77/84 (91.7%) | +2.4 |
| CM4AI | full | 53/84 (63.1%) | 80.0/84 (95.2%) | 81/84 (96.4%) | +1.2 |
| CM4AI | core | — | 78.0/84 (92.9%) | 84/84 (100.0%) | +7.1 |
| VOICE | full | 58/84 (69.0%) | 81/84 (96.4%) | 84.0/84 (100.0%) | +3.6 |
| VOICE | core | — | 82.0/84 (97.6%) | 84/84 (100.0%) | +2.4 |
| **Mean** | | **62.5% (n=4)** | **94.3%** | **97.2%** | **+2.8** |

## rubric10_semantic

| Project | Variant | prior | opus | fable | Δ fable−opus |
|---|---|---|---|---|---|
| AI_READI | full | 44/50 (88.0%) | 40.0/50 (80.0%) | 37/50 (74.0%) | -6.0 |
| AI_READI | core | 38.0/50 (76.0%) | 35.0/50 (70.0%) | 44/50 (88.0%) | +18.0 |
| CHORUS | full | 42.0/50 (84.0%) | 37.0/50 (74.0%) | 36/50 (72.0%) | -2.0 |
| CHORUS | core | 34/50 (68.0%) | 41.5/50 (83.0%) | 42/50 (84.0%) | +1.0 |
| CM4AI | full | 46/50 (92.0%) | 46.5/50 (93.0%) | 41/50 (82.0%) | -11.0 |
| CM4AI | core | 39/50 (78.0%) | 43.0/50 (86.0%) | 43/50 (86.0%) | +0.0 |
| VOICE | full | 46/50 (92.0%) | 47/50 (94.0%) | 44/50 (88.0%) | -6.0 |
| VOICE | core | 42/50 (84.0%) | 45.0/50 (90.0%) | 47/50 (94.0%) | +4.0 |
| **Mean** | | **82.8% (n=8)** | **83.8%** | **83.5%** | **-0.2** |

## rubric20_semantic

| Project | Variant | prior | opus | fable | Δ fable−opus |
|---|---|---|---|---|---|
| AI_READI | full | 79/84 (94.0%) | 79.0/84 (94.0%) | 76/84 (90.5%) | -3.5 |
| AI_READI | core | 68.0/84 (81.0%) | 77.0/84 (91.7%) | 75/84 (89.3%) | -2.4 |
| CHORUS | full | 74.0/84 (88.1%) | 73.0/84 (86.9%) | 78/84 (92.9%) | +6.0 |
| CHORUS | core | 58.0/84 (69.0%) | 75.0/84 (89.3%) | 78/84 (92.9%) | +3.6 |
| CM4AI | full | 76.0/84 (90.5%) | 80.0/84 (95.2%) | 80/84 (95.2%) | +0.0 |
| CM4AI | core | 53.0/84 (63.1%) | 69/84 (82.1%) | 81/84 (96.4%) | +14.3 |
| VOICE | full | 79.0/84 (94.0%) | 77.0/84.0 (91.7%) | 83/84 (98.8%) | +7.1 |
| VOICE | core | 68.0/84 (81.0%) | 81.0/84 (96.4%) | 83/84 (98.8%) | +2.4 |
| **Mean** | | **82.6% (n=8)** | **90.9%** | **94.3%** | **+3.4** |

## Mean percentage by rubric and judge

| Rubric | prior | opus-4.8 | fable-5 |
|---|---|---|---|
| rubric10 | 74.0 (n=4) | 82.4 | 91.0 |
| rubric20 | 62.5 (n=4) | 94.3 | 97.2 |
| rubric10_semantic | 82.8 (n=8) | 83.8 | 83.5 |
| rubric20_semantic | 82.6 (n=8) | 90.9 | 94.3 |

Notes:
- rubric10/rubric20 'prior' rows are the 2025-12-08 hybrid-heuristic evaluator, full variant only (core did not exist then) — not an LLM judge, so not directly comparable.
- rubric10_semantic/rubric20_semantic 'prior' rows are May-2026 LLM evaluations of the same D4D inputs; their model stamps (claude-sonnet-4-5) are template-derived, so the actual judge model for that layer is unverified.
- Δ fable−opus isolates the judge-model effect: identical inputs, identical rubric prompts, same day.
- Morning-run judge model relabeled from sonnet-4.5 to Claude Opus 4.8 on operator confirmation (2026-07-22): the sonnet stamps inside those JSONs are template text from the agent definitions (which also contain literal 'sha256-placeholder' values), not runtime introspection.
