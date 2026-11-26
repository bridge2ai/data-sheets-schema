# Canonical selection, release runtime, 2026-11-26

Dates here are UTC. From 2026-11-26 the canonical datasheet of the release runtime (`Claude Code (release)`,
method `claudecode_release`) for each project is one replicate of the series
`2026-11-25c_claude-fable-5-2-claudecode-generic-v9` (generic_v9 prompt, claude-fable-5-2, headless
Claude Code; reasoning effort recorded as high, asserted by the launcher and not observed). No release-runtime canonical existed before.

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

- When the marks were recorded no one had reviewed these records for content. All 15 were
  reviewed afterwards (see "Content reviews" below); no record was changed in response.
- AI_READI rep1 has 39 receiptable values without a receipt (README, item 1). Four of them
  are free-text statements. A text search of the bundle the record read finds each of the
  four stated there; that was a search by the session that prepared this change, not an
  independent review, and the other 35 were not checked: 29 names, three booleans, two
  enumerated values and one short free-text category (`use_category`). Rep2,
  which ties rep1 on populated slots, has a receipt on every receiptable value.
- Three of the five picks were decided by the label alone. On the command's criterion the
  choice between the tied replicates is arbitrary.
- CM4AI rep1 and rep3 list component `resources`; rep2, the canonical, does not.

## Content reviews (after the marks)

Each of the 15 records has one `d4d-review-record` review: `<PROJECT>_review.yaml` beside the
core record, its pack and instruction, and a `review` block in the provenance record.
`content_reviews.tsv` lists the verdict counts and the pack, review and reviewer-definition
hashes for each. Adverse verdicts, rep1 / rep2 / rep3:

| Project | rep1 | rep2 | rep3 |
|---|---|---|---|
| AI_READI | 3 | 1 | 2 |
| CHORUS | 4 | 4 | 4 |
| CM4AI | 0 | 1 | 1 |
| VOICE | 2 | 4 | 6 |
| VOICE_PEDIATRIC | 0 | 4 | 4 |

- Every item of every pack was answered; no verdict is `cannot_tell`, and none says a value is
  unsupported, misread or not in the bundle.
- **The counts are not comparable between replicates.** Each review samples its own record, and
  the same value was judged differently by different reviews. Checked against the sibling
  records: all three VOICE records list version 1.1 under `versions_available` (the source says
  its files are no longer available; rep3 says so in the entry) and only rep2 was charged; VOICE
  rep2 and rep3 both state `language: English` and only rep3 was charged; the
  `relationship_type: references` of the related dataset is the same in all three
  VOICE_PEDIATRIC records and was ruled a violation in rep2 and followed in rep1 and rep3.
  The counts are reported only, as the selection policy says (#835); they were not used to
  choose or to revisit a mark.
- One finding was checked as a difference between records: VOICE_PEDIATRIC rep3 names the
  SenseLab software on the strength of passages about the adult dataset; rep1 and rep2 do not
  name it.
- The reviews were given the reviewer definition as a file to follow
  (`.claude/agents/d4d-review-record.md` at main `483bed03b`) and ran as a general subagent on
  claude-opus-5-5, not as the typed agent whose front matter names another model. Each review
  file says so. Eleven reviews wrote the model id followed by a description in their `model`
  field; the field was reduced to the bare id so that one reviewer does not read as eleven
  (`tests/test_reviewer_basis.py`, #1058), and `review_model_field_as_written.tsv` keeps what
  each review wrote. The arm's reviewer is declared in `tests/data/reviewer_basis.json`.
- The packs committed are not byte for byte the packs the reviewers read: two absolute paths
  were removed by regenerating each pack with the fixed generator (#6379, PR #6380), after
  checking that nothing else differs; `review_pack_repin.tsv` gives both hashes and the
  generator behind each. Main's generator reproduces the committed packs only once PR #6380
  is merged. The `definition_sha256` column of `content_reviews.tsv` is the hash of the
  definition file when the table was made, which is the file every review was given.

## Presence evaluation

`data/evaluation/label_aware_release_2026-11-25c/` holds the presence-based scores (field
existence, deterministic, no model) of the full and core records, made with
`scripts/adhoc/run_presence_evaluation_release_series_20261126.sh`. 28 of 30 records are
scored. The full records of CM4AI rep1 and rep3 list component `resources`; the presence
evaluator validates them as a collection, the validation fails, and it skips them (#6377).
These scores are not comparable with the semantic rubric scores above.

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
- The site is deployed by `.github/workflows/deploy-docs.yaml` on every push to main, so the
  merge of this change is also the publication of these five pages.
- Beside each `<PROJECT>_d4d.html` the site's `html_output/` still holds older pages of the
  same project from earlier runs (`_d4d_human_readable`, `_d4d_interleaved`,
  `_evaluation_rubric10`, `_evaluation_rubric20`). They are not of this series and are not
  changed here.
