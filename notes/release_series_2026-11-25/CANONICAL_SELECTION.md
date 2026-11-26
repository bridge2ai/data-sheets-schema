# Canonical selection, release runtime, 2026-11-26

From 2026-11-26 the canonical datasheet of the release runtime (`Claude Code (release)`,
method `claudecode_release`) for each project is one replicate of the series
`2026-11-25c_claude-fable-5-2-claudecode-generic-v9` (generic_v9 prompt, claude-fable-5-2 at
effort high, headless Claude Code). No release-runtime canonical existed before.

| Project | Canonical record | Populated slots (rep1 / rep2 / rep3) | Margin | Receipts |
|---|---|---|---|---|
| AI_READI | `2026-11-25c_…_rep1` | 69 / 69 / 65 | 0, the label broke the tie with rep2 | 414 of 453 |
| CHORUS | `2026-11-25c_…_rep2` | 30 / 33 / 27 | 3 | 99 of 99 |
| CM4AI | `2026-11-25c_…_rep2` | 39 / 43 / 32 | 4 | 342 of 342 |
| VOICE | `2026-11-25c_…_rep2` | 65 / 70 / 70 | 0, the label broke the tie with rep3 | 914 of 914 |
| VOICE_PEDIATRIC | `2026-11-25c_…_rep2` | 43 / 44 / 44 | 0, the label broke the tie with rep3 | 378 of 378 |

## How it was chosen

Recorded with
`d4d runs select --method claudecode_release --project P --config 2026-11-25c_claude-fable-5-2-claudecode-generic-v9 --execute`.
Each pick is the command's own rule: full and core both validate, then most populated slots,
then lowest label. The command calls every margin here thin or a tie. A mark is scoped to its
runtime: the agentic canonicals (series 2026-11-22b) and the API canonicals are untouched and
are named as kept in the command's output.

The owner approved these five on 2026-11-26 after seeing the semantic rubric scores of all
fifteen replicates. The scores are reported only and did not decide a pick (selection policy
`reported_only_pending_calibration_v1`, #835).

## Rubric scores

`rubric_scores_root_scope_v6.tsv` (written by
`scripts/adhoc/tabulate_root_scope_scores_20261126.py`) has one row per evaluation file with
its sha256. Rubric10 is out of 50, rubric20 out of 88. The canonical record is in bold.

| Project | rep1 | rep2 | rep3 |
|---|---|---|---|
| AI_READI | **45, 70** | 45, 68 | 42, 68 |
| CHORUS | 28, 51 | **26, 55** | 21, 50 |
| CM4AI | 32, 64 | **32, 61** | 27, 64 |
| VOICE | 42, 66 | **45, 72** | 46, 70 |
| VOICE_PEDIATRIC | 35, 61 | **38, 65** | 39, 59 |

- Instrument: `2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6` (scorer gpt-6-astra
  through the Codex CLI at effort ultra). It scores the whole record as one unit, whether or
  not the record lists component resources (#6358).
- The 30 evaluation files are not in this change. They are in PR #6372, which depends on the
  instrument's own PR #6366; main's validator does not accept them until that merges. The
  files PR #6372 held at `eca8eae45` are byte-identical to the ones tabulated here.
- One run per record. There is no repeat, so the size of run-to-run variation is unknown, and
  a difference of a few points between replicates is not evidence that one is better.
- No canonical record is the lowest of its project on both rubrics. CM4AI rep2 is the lowest
  on rubric20 (61 against 64 and 64) and ties for the highest on rubric10.
- These scores are not comparable with the 2026-11-22b series' scores: another instrument,
  and for CM4AI another unit of scoring (that series' CM4AI records were scored as
  collections, minimum per component).

## What a reader should know

- No one has reviewed these records for content. The checks behind them show that each
  receipted value points at real source text, not that each value is right.
- AI_READI rep1 has 39 receiptable values without a receipt (README, item 1). Four of them
  are free-text statements. A text search of the bundle the record read finds each of the
  four stated there; that was a search by the session that prepared this change, not an
  independent review, and the other 35 (names and enumerated values) were not checked. Rep2,
  which ties rep1 on populated slots, has a receipt on every receiptable value.
- Three of the five picks were decided by the label alone. On the command's criterion the
  choice between the tied replicates is arbitrary.
- CM4AI rep1 and rep3 list component `resources`; rep2, the canonical, does not.

## HTML

- Canonical pages: `data/d4d_html/concatenated/claudecode_release/<label>/<PROJECT>_d4d.html`
  and the flat `data/d4d_html/concatenated/claudecode_release/<PROJECT>_d4d.html`
  (`d4d render generate-all --method claudecode_release --label L --project P --publish --execute`).
- Previews of all 15 runs: `html/` (see its README).
- The documentation build (`make gendoc`) now copies the flat release pages after the flat
  agentic pages, so the site's `html_output/<PROJECT>_d4d.html` is this series' page and no
  longer the 2026-11-22b agentic page (the owner's decision of 2026-11-26). The agentic pages
  stay in `data/d4d_html/concatenated/claudecode_agent/`. The site's home page links the
  `curated` pages and is unchanged.
