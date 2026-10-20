# P1: v8 comparability recompute for the generic_v10 analysis plan

Step P1 of `notes/d4d_generation_plan_2026-10-09.md` ("#### P1"), recomputed on
2026-10-20 at main `0a1132ecf` (`0a1132ecf23f92c2cd128f6357f5248e57cd63f8`), the
base of branch `claude/track-p-analysis-plan`. It was revised the same day after an
independent read-only review.

Everything here is read from committed records, bundles, notes and git objects by the
commands in the manifest at the end. Nothing was written to `data/`, no record or
provenance block changed, and no provider was called.

The plan wrote P1 against `15d053d1a`. Where today's files differ from what the plan
states, this note gives today's value and says what changed.

## Which records are the v8 baseline

On main, the v8 records are all API-runtime records under `claudecode_api/` and
`claudecode_api_core/`:
- runtime `model.agent_runtime: Claude API (direct)`;
- provider `LBL CBORG (proxy to Anthropic)`;
- model `claude-opus-5`.

Main has no other v8 method directory. Outside main there are untracked agentic
generic-v8 AI_READI runs (`claudecode_agent`, runtime `Claude Code`, rep1–3 each):
- `2026-10-14a_…` in `d4d-executions/aireadi-v8-a`, which read bundle `d22b61a9`, the
  one with the crate;
- `2026-10-14b_…` in `d4d-executions/aireadi-v8-b`, which read `1a58ad7b`, the one
  without it.

**Proposed confirmatory arm (D02 recommends it; D02 is pending): 12 records**, 3 per
project:
- `2026-09-04f_claude-opus-5-api-generic-v8_rep{1,2,3}` for CHORUS and VOICE;
- `2026-09-04g_claude-opus-5-api-generic-v8_rep{1,2,3}` for AI_READI and CM4AI.

These are the records `notes/recall_target_baseline.md` and `notes/arm_comparison.md`
call "v8 API production (2026-09-04f/g)". D02 recommends excluding:
- the canaries `2026-09-04`, `04b` and `04c` (CM4AI) and `04d` and `04e` (VOICE);
- AI_READI `2026-09-04f` rep1, which `d4d runs check` reports as invalid by its own
  validation block (three top-level `source_caveats` keys, #1029).

**Each rep1 is a canary that passed the gate; rep2 and rep3 are not.**
- rep1:
  - CHORUS and VOICE under `04f`. VOICE's passed after the `04d` and `04e` canaries
    regressed.
  - AI_READI and CM4AI under `04g` (commits `586a34b9f` and `ffe71d9e1`, 2026-09-06).
    AI_READI's came after `04f` rep1, which passed and was later found invalid. CM4AI's
    came after `04`, `04b` and `04c`.
- rep2 and rep3: the eight records of the v8 fill (`805e6ac7b`, 2026-09-07, #1049),
  run without a per-run gate verdict.

Only the rep1 records carry a `canary` block, and those blocks are offline
re-verdicts from 2026-09-10/11 (section "Validation, duplicate keys…"). That
selection is a comparability fact for P2: v8 rep1 survived a gate, and its rep2 and
rep3 were never gated.

**The coordination prompt's naming does not match the records.** It calls the arm
"v8 04f (`claudecode_assistant_agent`) and 04g (`claudecode_api_agent`)". Neither
method directory exists anywhere. `04f` and `04g` are two date-letter prefixes of
one API arm in `claudecode_api`, split by project pair rather than by method or
runtime. This note uses the records.

## Record identity and provenance pins

every module used resolves under this tree's `src/` (asserted): `data_sheets_schema.backfill_checks`, `data_sheets_schema.canary`, `data_sheets_schema.receipts`, `data_sheets_schema.replicate_structure`

| project | rep | provenance sha256 | repo.commit | dirty | dirty files | dirty paths recorded | schema | full schema sha256 |
|---|---|---|---|---|---|---|---|---|
| CHORUS | 1 | `49e29d0b9882e27a` | `26f7e4cd` | True | 15 | 15 | 2.0.0 | `b9b31acad29e` |
| CHORUS | 2 | `fde00d1d09ce32b8` | `a2a3e157` | True | 10 | 10 | 2.0.0 | `b9b31acad29e` |
| CHORUS | 3 | `fbafb60adb190e40` | `a2a3e157` | True | 10 | 10 | 2.0.0 | `b9b31acad29e` |
| VOICE | 1 | `c8536ee18cdbef98` | `f294aeba` | True | 3 | not recorded | 2.0.0 | `b9b31acad29e` |
| VOICE | 2 | `ff69edd52fb5448c` | `a2a3e157` | True | 6 | 6 | 2.0.0 | `b9b31acad29e` |
| VOICE | 3 | `fb6cf4554e84b6a7` | `a2a3e157` | True | 10 | 10 | 2.0.0 | `b9b31acad29e` |
| AI_READI | 1 | `25b431b81c48245d` | `26f7e4cd` | True | 18 | 18 | 2.0.0 | `b9b31acad29e` |
| AI_READI | 2 | `9debb857c95777de` | `a2a3e157` | True | 6 | 6 | 2.0.0 | `b9b31acad29e` |
| AI_READI | 3 | `a3b311e5f7cd59f3` | `a2a3e157` | True | 10 | 10 | 2.0.0 | `b9b31acad29e` |
| CM4AI | 1 | `ac9f6dedd874e6ff` | `63d6d41c` | True | 15 | 15 | 2.0.0 | `b9b31acad29e` |
| CM4AI | 2 | `1d4a520f503ab481` | `a2a3e157` | True | 10 | 10 | 2.0.0 | `b9b31acad29e` |
| CM4AI | 3 | `63a8d3adf1bf650c` | `a2a3e157` | True | 10 | 10 | 2.0.0 | `b9b31acad29e` |

distinct recorded dirty states (commit, dirty paths): 6; today's schema 3.0.0, merged full schema sha256 `eb543e1597b2`

What these rows show:
- The 12 records come from four commits and six distinct recorded dirty states.
- VOICE rep1 records `dirty_file_count: 3` but no `dirty_paths`; that record predates
  #1023, which added the path list.
- All 12 ran under schema 2.0.0. Main is at schema 3.0.0.
- The provenance sha256s pin the record blocks the tables below read. Those blocks
  have been rewritten in place before. AI_READI 04g rep2's was created by the fill
  commit `805e6ac7b` on 2026-09-07 and rewritten by 26 later commits from 2026-09-07
  to 2026-09-11 (`git log` on the file). A later rewrite changes these hashes.

`data_sheets_schema` is a namespace package. With the primary checkout's virtualenv,
its `__path__` lists that checkout's `src/` as well as this tree's, so the script
asserts that every module it uses resolves under this tree's `src/` (plan risk 10). It
prints no machine paths.

## Records, hashes and bundles

| project | label | canonical | full sha256 | core sha256 | bundle md5 (recorded) | today's bundle md5 | same bytes |
|---|---|---|---|---|---|---|---|
| CHORUS | `2026-09-04f_claude-opus-5-api-generic-v8_rep1` |  | `f2a4d6229e5b4188` | `1b87f1cadd813358` | `9b2ef4b6` | `9b2ef4b6` | yes |
| CHORUS | `2026-09-04f_claude-opus-5-api-generic-v8_rep2` | api | `960c3500b4c6b43b` | `a3a5a4a04f2311ed` | `9b2ef4b6` | `9b2ef4b6` | yes |
| CHORUS | `2026-09-04f_claude-opus-5-api-generic-v8_rep3` |  | `82963f6ea262f9cf` | `3d0b83ca30a5d4a9` | `9b2ef4b6` | `9b2ef4b6` | yes |
| VOICE | `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | api | `6ad8a47eab05cc4f` | `a5415bcd54bf7eef` | `9193c3cb` | `9193c3cb` | yes |
| VOICE | `2026-09-04f_claude-opus-5-api-generic-v8_rep2` |  | `0766cb45aa40e355` | `1343d4c23c815980` | `9193c3cb` | `9193c3cb` | yes |
| VOICE | `2026-09-04f_claude-opus-5-api-generic-v8_rep3` |  | `ba8876a62b15682a` | `f273871ea84dd3f2` | `9193c3cb` | `9193c3cb` | yes |
| AI_READI | `2026-09-04g_claude-opus-5-api-generic-v8_rep1` |  | `4f09d95003ba1f3f` | `a5d80f898c56a8df` | `d22b61a9` | `1a58ad7b` | no |
| AI_READI | `2026-09-04g_claude-opus-5-api-generic-v8_rep2` | api | `225e5fd96d959960` | `2f67a66b6ba0afb3` | `d22b61a9` | `1a58ad7b` | no |
| AI_READI | `2026-09-04g_claude-opus-5-api-generic-v8_rep3` |  | `01e3ef504db5ba6f` | `8243704192050cf3` | `d22b61a9` | `1a58ad7b` | no |
| CM4AI | `2026-09-04g_claude-opus-5-api-generic-v8_rep1` |  | `b14858313cb86f69` | `c24069404bf8af1c` | `50037fc6` | `50037fc6` | yes |
| CM4AI | `2026-09-04g_claude-opus-5-api-generic-v8_rep2` |  | `9fce395dfcba6684` | `9639140a3a3be545` | `50037fc6` | `50037fc6` | yes |
| CM4AI | `2026-09-04g_claude-opus-5-api-generic-v8_rep3` | api | `e3311d40121521b8` | `20c9276b95567525` | `50037fc6` | `50037fc6` | yes |

**What changed since the plan.** The plan says every v8 baseline bundle matches
today's file:
- "all four match today's files";
- D02's option text: "bundles byte-identical to today's for all four projects".

That held at `15d053d1a`. It no longer holds for AI_READI. #5042 removed the RO-Crate
source from the AI_READI corpus and rebuilt the bundle, so today's
`AI_READI_preprocessed.txt` is `1a58ad7b…`. `d4d runs check --method claudecode_api`
reports the same: "4 record(s) name an input bundle whose bytes have since changed …
AI_READI_preprocessed.txt 4". CHORUS, CM4AI and VOICE still match.

## AI_READI: the v8 comparator records were generated with the crate

**What this means: by the owner's own ruling, the three AI_READI v8 records are
with-crate results.** The issue is not only that the bundle has since changed. The
records were generated with the RO-Crate in their input, and the owner has ruled that
crate content is a separate arm. `data/_wcrate/README.md` (on main) states:

> On 2026-10-14 the owner ruled that generation runs read no RO-Crate content.
> Crates are the input of the separate with-crate and crate-only arms only.

It lists the "4 under `claudecode_api`: v8, 2026-09-04f rep1 and 2026-09-04g rep1–3"
among the 30 with-crate AI_READI records it keeps. Issue #5042's body records the same
ruling on GitHub: "**Owner decision (2026-10-14):** the current generation runs should
not include RO-Crate content. RO-Crates belong only to the separate with-crate and
crate-only arms."

**The crate was in their input, and it reached their content.** All three records pin
the chunk manifest as it was before #5042 (sha256 `a7b083727b56…`, recovered with
`git show 1c4debbae^:data/preprocessed/chunks/AI_READI_chunks.yaml`). In that
manifest, chunks c022–c024 are the RO-Crate document. Today's manifest differs
(`fc3631ad7e8d…`). Each record's coverage receipt marks those chunks `extracted`:

pre-#5042 chunk manifest (`git show 1c4debbae^:data/preprocessed/chunks/AI_READI_chunks.yaml`): sha256 `a7b083727b56f9cf`, 28 chunks; RO-Crate chunks: c022, c023, c024

| rep | pinned chunk manifest is the pre-#5042 one | receipted snippets | citing a crate chunk | top-level slots receipted from the crate | crate-chunk statuses |
|---|---|---|---|---|---|
| 1 | True | 351 | 32 | 17 | {'c022': 'extracted', 'c023': 'extracted', 'c024': 'extracted'} |
| 2 | True | 339 | 33 | 19 | {'c022': 'extracted', 'c023': 'extracted', 'c024': 'extracted'} |
| 3 | True | 314 | 37 | 22 | {'c022': 'extracted', 'c023': 'extracted', 'c024': 'extracted'} |

So about a tenth of each AI_READI v8 replicate's receipted snippets come from the
crate, spread over 17–22 top-level slots. That includes 2 of AI_READI rep2's 17
`variables` receipts, which cite c023 and c024. Most `variables` receipts cite
non-crate chunks, so the recall target largely survives.

**Consequences for P2.** P1 does not choose a comparator; that choice is the owner's
(P2 item 2). The consequences:
- **Package effect.** An AI_READI v10 run reads `1a58ad7b`, without the crate.
  Measured against these records, the AI_READI difference crosses an input-arm
  boundary the owner has defined, as well as the package.
- **The AI_READI pilot's baseline.** Plan A14-reg plans the pilot with
  `--canary-baseline 2026-09-04g_claude-opus-5-api-generic-v8`, but
  `canary.baseline_for` checks no bundle. It reads the stored check blocks of every
  record whose label matches the prefix. So that baseline would silently compare a
  run without the crate against records that had it.
- **E2's blind batch** would mix crate-derived v8 AI_READI content with no-crate v10
  records.
- **Plan gates that cannot pass as written** (agy and the owner to amend; this note
  does not edit the plan):
  - A4's gate: "The CHORUS and AI_READI bundle md5s equal the comparators'
    (9b2ef4b6, d22b61a9)";
  - A14-reg's gate: "the bundle md5 is d22b61a9";
  - the plan's run tables, which say the AI_READI comparators read "the identical
    bundle d22b61a9".

  Today's AI_READI bundle is `1a58ad7b`.

## v8 attempts per comparator cell (for P2's Set A)

comparator prompt pin (`d4d_generic_arm_prompt_v8.md`): `506af01bc9ab`; every comparator record is its cell's final attempt

| project | cell | label | prompt pin | commit | validation | duplicate keys | floors above 0 | coverage | leaves | lineage | variables | tools+ver | lexical |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CHORUS | rep1 | `2026-09-04f` | `506af01b` | `26f7e4cd` | True | 0 | none | 54/186 | 235 | 1 | 0 | 0 | 0 |
| CHORUS | rep2 | `2026-09-04f` | `506af01b` | `a2a3e157` | True | 0 | snippets unverified 2 | 83/248 | 278 | 1 | 0 | 0 | 0 |
| CHORUS | rep3 | `2026-09-04f` | `506af01b` | `a2a3e157` | True | 0 | snippets unverified 1 | 78/198 | 251 | 0 | 0 | 0 | 0 |
| VOICE | rep1 | `2026-09-04d` | `506af01b` | `b86a729a` | True | 0 | none | 187/343 | 398 | 1 | 9 | 0 | 2 |
| VOICE | rep1 | `2026-09-04e` | `506af01b` | `b1c5db83` | True | 0 | chunks unreviewed 15 | 7/354 | 452 | 0 | 5 | 0 | 1 |
| VOICE | rep1 | `2026-09-04f` | `506af01b` | `f294aeba` | True | 0 | none | 223/343 | 386 | 1 | 4 | 0 | 3 |
| VOICE | rep2 | `2026-09-04f` | `506af01b` | `a2a3e157` | True | 0 | none | 141/261 | 297 | 1 | 4 | 0 | 0 |
| VOICE | rep3 | `2026-09-04f` | `506af01b` | `a2a3e157` | True | 0 | none | 220/382 | 432 | 1 | 4 | 0 | 1 |
| AI_READI | rep1 | `2026-09-04f` | `506af01b` | `554edcba` | False | 1 | none | 151/431 | 523 | 0 | 25 | 0 | 2 |
| AI_READI | rep1 | `2026-09-04g` | `506af01b` | `26f7e4cd` | True | 0 | none | 280/480 | 525 | 0 | 20 | 0 | 3 |
| AI_READI | rep2 | `2026-09-04g` | `506af01b` | `a2a3e157` | True | 0 | snippets unverified 1 | 163/420 | 525 | 1 | 13 | 0 | 2 |
| AI_READI | rep3 | `2026-09-04g` | `506af01b` | `a2a3e157` | True | 0 | none | 251/389 | 449 | 0 | 20 | 0 | 0 |
| CM4AI | rep1 | `2026-09-04_` | `06666c4d` | `4138bfea` | True | 0 | receipt findings 1 | 206/342 | 384 | 0 | 0 | 0 | 5 |
| CM4AI | rep1 | `2026-09-04b` | `06666c4d` | `a844827e` | True | 0 | none | 288/407 | 455 | 1 | 0 | 0 | 6 |
| CM4AI | rep1 | `2026-09-04c` | `06666c4d` | `48f49106` | True | 0 | none | 292/415 | 470 | 0 | 0 | 0 | 7 |
| CM4AI | rep1 | `2026-09-04g` | `506af01b` | `63d6d41c` | True | 0 | none | 279/374 | 422 | 0 | 0 | 0 | 9 |
| CM4AI | rep2 | `2026-09-04g` | `506af01b` | `a2a3e157` | True | 0 | none | 312/424 | 473 | 0 | 0 | 0 | 5 |
| CM4AI | rep3 | `2026-09-04g` | `506af01b` | `a2a3e157` | True | 0 | snippets unverified 1 | 226/389 | 479 | 0 | 0 | 0 | 3 |

| definition | project | records | pooled coverage | mean populated leaves | D02 recall targets (mean) | Set B (common gate) records |
|---|---|---|---|---|---|---|
| one record per cell (the final attempt) | CHORUS | 3 | 215/632 = 0.340 | 254.7 | lineage 0.67 | 1 of 3 |
| one record per cell (the final attempt) | VOICE | 3 | 584/986 = 0.592 | 371.7 | variables 4.00; lineage 1.00; lexical 1.33; tools_versioned 0.00 | 3 of 3 |
| one record per cell (the final attempt) | AI_READI | 3 | 694/1289 = 0.538 | 499.7 | variables 17.67 | 2 of 3 |
| one record per cell (the final attempt) | CM4AI | 3 | 817/1187 = 0.688 | 458.0 | lexical 5.67 | 2 of 3 |
| every attempt under the comparator's pin | CHORUS | 3 | 215/632 = 0.340 | 254.7 | lineage 0.67 | 1 of 3 |
| every attempt under the comparator's pin | VOICE | 5 | 778/1683 = 0.462 | 393.0 | variables 5.20; lineage 0.80; lexical 1.40; tools_versioned 0.00 | 4 of 5 |
| every attempt under the comparator's pin | AI_READI | 4 | 845/1720 = 0.491 | 505.5 | variables 19.50 | 2 of 4 |
| every attempt under the comparator's pin | CM4AI | 3 | 817/1187 = 0.688 | 458.0 | lexical 5.67 | 2 of 3 |
| every attempt, any pin (sensitivity) | CHORUS | 3 | 215/632 = 0.340 | 254.7 | lineage 0.67 | 1 of 3 |
| every attempt, any pin (sensitivity) | VOICE | 5 | 778/1683 = 0.462 | 393.0 | variables 5.20; lineage 0.80; lexical 1.40; tools_versioned 0.00 | 4 of 5 |
| every attempt, any pin (sensitivity) | AI_READI | 4 | 845/1720 = 0.491 | 505.5 | variables 19.50 | 2 of 4 |
| every attempt, any pin (sensitivity) | CM4AI | 6 | 1603/2351 = 0.682 | 447.2 | lexical 5.83 | 4 of 6 |

**What this shows.** The 12 comparator records are each cell's final attempt.
- Three cells also hold earlier attempts that left full records:
  - VOICE rep1 (`04d`, `04e`);
  - AI_READI rep1 (`04f` rep1);
  - CM4AI rep1 (`04`, `04b`, `04c`).
- VOICE's and AI_READI's earlier attempts ran the same prompt pin as the comparator
  (`506af01b…`). CM4AI's ran an earlier pin (`06666c4d…`).
- The comparator records themselves span four runner commits, so a runner commit does
  not set the earlier attempts apart.

**The definition moves the comparator.** Counting every attempt under the
comparator's pin moves:
- VOICE's pooled coverage from 0.592 to 0.462;
- AI_READI's from 0.538 to 0.491.

Both shifts are larger than any tolerance P2 proposes for coverage. Which definition
P2 uses is the owner's choice (P2 item 3).

**Replicate structure is unaffected.** The #2932 rows below are computed over exactly
three records per project, one per cell, under either definition.

## v6 drift

| project | v6 bundle md5 (recorded, rep1–3) | today's bundle md5 | same bytes |
|---|---|---|---|
| AI_READI | `0f3abb51` | `1a58ad7b` | no |
| CHORUS | `9b2ef4b6` | `9b2ef4b6` | yes |
| CM4AI | `1dfd34e5` | `50037fc6` | no |
| VOICE | `dcd71717` | `9193c3cb` | no |

Matches the plan for AI_READI `0f3abb51`, CM4AI `1dfd34e5` and VOICE `dcd71717`.
Today's AI_READI value is `1a58ad7b`, not the `d22b61a9` the plan compares against,
because of #5042. CHORUS has not drifted.

## VOICE_PEDIATRIC

today's bundle md5 `03502237`; provenance records: 6; their bundle md5s: {'327c2920': 3, '008212ac': 3}; consumed today's bytes: 0

The plan's "VOICE_PEDIATRIC's bundle 03502237, which has no record" is true of that
bundle. Six earlier VOICE_PEDIATRIC records exist (`claudecode_agent`,
`2026-08-07_…generic-v3_rep{1,2,3}` and `2026-08-11_…generic_rep{1,2,3}`). They pin
older bundles, and no record consumed today's bytes. None is a generic_v8 record, so
VOICE_PEDIATRIC has no v8 comparator on any arm, as D02 says.

KIDS_FIRST has no `data/preprocessed/concatenated/` bundle on main. Its frozen inputs
are under `notes/matched_cborg_2026-09-13/kids_first/` (plan A19-reg). Its bundle,
`KIDS_FIRST_preprocessed.txt`, is 541,184 bytes, now the largest of the six projects;
AI_READI is 430,393 since #5042.

## Recall-target counts per record

These rows are copied from the committed `notes/recall_target_baseline.md` (sha256
`a7f96768e976eb70594912a7f66b60fb9d4872defb0ecac35d083106ed5f48cf`), which `scripts/recall_target_baseline.py` (sha256
`e89609655be029b8b562379eee898931d2c3568ea8330108d0660dd3f55fa569`) generates. The recompute script does not print them. What
reproduces them is that `recall_target_baseline.py --check` exits 0, meaning the
committed note matches the records (command 2).

The note fixes the cue patterns (sha256 `768a26a370bd…`) and the tools-version pattern
(sha256 `4726c0058b01…`), the two hashes the plan cites. Columns, in order:
- lineage entries, `was_derived_from`, `parent_datasets`;
- variables entries;
- `used_software` with a version, `used_software`;
- tools with a version token, tools;
- receipt chunks marked `nothing_relevant`, `redundant_with`;
- lexical candidates;
- the record sha256 and the receipt sha256 (each a 16-hex prefix).

| arm | record | lineage | wdf | parent | variables | sw+ver | sw | tools+ver | tools | nothing_relevant | redundant_with | lexical | record sha256 | receipt sha256 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| v8prod | `claudecode_api/2026-09-04f_claude-opus-5-api-generic-v8_rep1/CHORUS_d4d.yaml` | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | `f2a4d6229e5b4188` | `4849792f64b7c317` |
| v8prod | `claudecode_api/2026-09-04f_claude-opus-5-api-generic-v8_rep1/VOICE_d4d.yaml` | 1 | 1 | 0 | 4 | 0 | 0 | 0 | 9 | 3 | 2 | 3 | `6ad8a47eab05cc4f` | `9ffe181580be46bc` |
| v8prod | `claudecode_api/2026-09-04f_claude-opus-5-api-generic-v8_rep2/CHORUS_d4d.yaml` | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | `960c3500b4c6b43b` | `fe640454761c9ba8` |
| v8prod | `claudecode_api/2026-09-04f_claude-opus-5-api-generic-v8_rep2/VOICE_d4d.yaml` | 1 | 1 | 0 | 4 | 0 | 0 | 0 | 8 | 2 | 0 | 0 | `0766cb45aa40e355` | `663009757730ecd8` |
| v8prod | `claudecode_api/2026-09-04f_claude-opus-5-api-generic-v8_rep3/CHORUS_d4d.yaml` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | `82963f6ea262f9cf` | `861d0abb5b679952` |
| v8prod | `claudecode_api/2026-09-04f_claude-opus-5-api-generic-v8_rep3/VOICE_d4d.yaml` | 1 | 1 | 0 | 4 | 0 | 0 | 0 | 8 | 3 | 0 | 1 | `ba8876a62b15682a` | `1aef6730cd90233d` |
| v8prod | `claudecode_api/2026-09-04g_claude-opus-5-api-generic-v8_rep1/AI_READI_d4d.yaml` | 0 | 0 | 0 | 20 | 0 | 0 | 0 | 0 | 2 | 2 | 3 | `4f09d95003ba1f3f` | `645b00ded6ebbce5` |
| v8prod | `claudecode_api/2026-09-04g_claude-opus-5-api-generic-v8_rep1/CM4AI_d4d.yaml` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 | 3 | 9 | `b14858313cb86f69` | `09a51cae6cd21a4b` |
| v8prod | `claudecode_api/2026-09-04g_claude-opus-5-api-generic-v8_rep2/AI_READI_d4d.yaml` | 1 | 1 | 0 | 13 | 0 | 0 | 0 | 0 | 2 | 1 | 2 | `225e5fd96d959960` | `eb9c2737178609f6` |
| v8prod | `claudecode_api/2026-09-04g_claude-opus-5-api-generic-v8_rep2/CM4AI_d4d.yaml` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 5 | `9fce395dfcba6684` | `a9e8d454a16f655d` |
| v8prod | `claudecode_api/2026-09-04g_claude-opus-5-api-generic-v8_rep3/AI_READI_d4d.yaml` | 0 | 0 | 0 | 20 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | `01e3ef504db5ba6f` | `cca232f11853fc7e` |
| v8prod | `claudecode_api/2026-09-04g_claude-opus-5-api-generic-v8_rep3/CM4AI_d4d.yaml` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 2 | 3 | `e3311d40121521b8` | `7218afd40dde3572` |

Arm totals: 12 records; lineage entries 6, variables entries 65, `used_software` with
a version 0, tools with a version token 0 of 26 tools, 12 receipts; 57
`nothing_relevant`/`redundant_with` chunks, of which 26 are lexical candidates (14
with a lineage cue, 13 with a variables cue, 20 with a version cue).

D02's recall predictions read their targets from these rows. Each was checked against
the table above and matches:
- AI_READI variables 20/13/20.
- CM4AI lexical candidates 9/5/3.
- VOICE:
  - variables 4/4/4;
  - lineage entries 1/1/1;
  - lexical candidates 3/0/1;
  - tools with a version token 0/0/0. The plain tools column is 9/8/8.
- CHORUS variables and lexical candidates are 0/0/0 each, and its lineage is 1/1/0.

For AI_READI the receipts above include crate chunks (previous section). The
lexical-candidate and `nothing_relevant` counts are over the pre-#5042 chunking.

## Receipt coverage, with denominators, and the receipt floors

| project | label | chunks reviewed | snippets verified | snippets not in the chunk cited | mismatched / unattesting | receiptable slots with a receipt | never receipted | added after the receipt | receipt floors above 0 (`canary.receipt_floors`) |
|---|---|---|---|---|---|---|---|---|---|
| CHORUS | `2026-09-04f rep1` | 8/8 | 79/79 | 0/79 | 0 / 0 | 54/186 | 127/186 | 5/186 | none |
| CHORUS | `2026-09-04f rep2` | 8/8 | 87/90 | 1/90 | 2 / 0 | 83/248 | 157/248 | 8/248 | snippets unverified 2 |
| CHORUS | `2026-09-04f rep3` | 8/8 | 114/117 | 1/117 | 1 / 1 | 78/198 | 118/198 | 2/198 | snippets unverified 1 |
| VOICE | `2026-09-04f rep1` | 22/22 | 238/243 | 5/243 | 0 / 0 | 223/343 | 116/343 | 4/343 | none |
| VOICE | `2026-09-04f rep2` | 22/22 | 237/248 | 11/248 | 0 / 0 | 141/261 | 120/261 | 0/261 | none |
| VOICE | `2026-09-04f rep3` | 22/22 | 222/231 | 9/231 | 0 / 0 | 220/382 | 159/382 | 3/382 | none |
| AI_READI | `2026-09-04g rep1` | 28/28 | 346/351 | 5/351 | 0 / 0 | 280/480 | 192/480 | 8/480 | none |
| AI_READI | `2026-09-04g rep2` | 28/28 | 319/339 | 19/339 | 1 / 0 | 163/420 | 250/420 | 7/420 | snippets unverified 1 |
| AI_READI | `2026-09-04g rep3` | 28/28 | 310/314 | 4/314 | 0 / 0 | 251/389 | 137/389 | 1/389 | none |
| CM4AI | `2026-09-04g rep1` | 28/28 | 156/174 | 18/174 | 0 / 0 | 279/374 | 95/374 | 0/374 | none |
| CM4AI | `2026-09-04g rep2` | 28/28 | 153/186 | 33/186 | 0 / 0 | 312/424 | 109/424 | 3/424 | none |
| CM4AI | `2026-09-04g rep3` | 28/28 | 136/184 | 47/184 | 1 / 0 | 226/389 | 155/389 | 8/389 | snippets unverified 1 |
| **pooled** | 12 records | 258/258 | 2397/2556 | 153/2556 = 6.0% | 5 / 1 | 2310/4094 = 56.4% | 1735/4094 = 42.4% | 49/4094 = 1.2% | 4 of 12 |

records with a receipt floor above 0: CHORUS 2026-09-04f rep2; CHORUS 2026-09-04f rep3; AI_READI 2026-09-04g rep2; CM4AI 2026-09-04g rep3

The coverage columns reproduce `notes/arm_comparison.md` (sha256 `802e07da46e9851d880f82f2d1c1237f2a5126bcfdfb2e8b08e26b106123ac3f`,
"Receipt coverage and attribution, pooled per arm") exactly:
- 2310/4094 = 56.4% with a receipt;
- 1735/4094 never receipted;
- 49/4094 added after the receipt;
- 153/2556 not in the chunk cited.

Every receipts block is instrument v3, the current one (`d4d runs check`: "receipts
blocks by instrument: v3 19 (current v3)").

**Four of the 12 records fail a receipt floor today: "snippets unverified".**
- CHORUS `04f` rep2: 2 mismatched snippets.
- CHORUS `04f` rep3: 1.
- AI_READI `04g` rep2: 1.
- CM4AI `04g` rep3: 1.

`canary.receipt_floors` computes each floor from the stored block. The "receipt
findings" floor is 0 everywhere, but that is only one of the five floors.

Six snippets are neither verified nor attributed to another chunk:
- five mismatched (the four records above);
- one unattesting, in CHORUS rep3.

The other unverified snippets are verbatim in the bundle but in a chunk other than the
one cited. Those are reported and never gated (#763).

## Validation, duplicate keys and populated leaves

| project | rep1 / rep2 / rep3 validation passed | duplicate keys (`canary.duplicate_key_count`) | populated leaves (full record) | gate verdict block (`canary`) |
|---|---|---|---|---|
| CHORUS | True/True/True | 0/0/0 | [235,278,251] | rep1: d4d api verdict (offline) |
| VOICE | True/True/True | 0/0/0 | [386,297,432] | rep1: d4d api verdict (offline) |
| AI_READI | True/True/True | 0/0/0 | [525,525,449] | rep1: d4d api verdict (offline) |
| CM4AI | True/True/True | 0/0/0 | [422,473,479] | rep1: d4d api verdict (offline) |

- **Populated leaves** use `receipts.populated_leaves` (sha256 of `receipts.py`
  `7bfb84709b2e91983eae2b6dbaf8f67e13ef06b68473ad61947ebf6dd7542c9f`), the counter `scripts/arm_comparison.py` uses. The bracketed
  values match the committed "populated leaves (full record)" rows of
  `notes/arm_comparison.md`.
- **Duplicate keys** are counted with `canary.duplicate_key_count`, the gate's own
  counter.
- **`validation.passed`** is the block `d4d provenance recheck-validation` wrote. It
  validated each record against its run's schema.
- **Gate verdict block:** the `canary` block, where one exists. All four are offline
  re-verdicts (`recorded_by: d4d api verdict (offline)`) of the retained rep1
  canaries.

## Replicate structure (#2932)

slot universe: 97 slots (`replicate_structure.dataset_slots`)

| project | all / some / none | identical | nested in all: with a count / counts differ / max/min >= 2 | intermittent slots |
|---|---|---|---|---|
| CHORUS | 46 / 14 / 37 | 6 | 34: 27 / 17 / 10 | 14 |
| VOICE | 74 / 9 / 14 | 12 | 56: 47 / 27 / 14 | 9 |
| AI_READI | 74 / 8 / 15 | 17 | 51: 41 / 19 / 6 | 8 |
| CM4AI | 51 / 17 / 29 | 14 | 32: 24 / 14 / 9 | 17 |

Computed with `replicate_structure.compare_structure` and `summarize` (sha256 of
`replicate_structure.py` `c3c3131e8953d15a9f845ee6398d828c536e38d985959c005e49f173a5167b0e`) over `dataset_slots()`, today's merged schema,
which is how `scripts/arm_comparison.py` builds its "Replicate structure (#2932)"
section. Every figure equals the committed v8 rows there. Today's merged schema is
3.0.0, so a slot schema 2.0.0 did not declare counts as unfilled. The intermittent
counts (AI_READI 8, CHORUS 14, CM4AI 17, VOICE 9) are the v8 column of #2932's table.

## Report findings and the seven D21 defect metrics

| project | label | report claims checked | pair errors | report findings | ungrounded identifiers | resolver URLs in identifier slots | organisational fragments | undeclared prefixes | British spellings |
|---|---|---|---|---|---|---|---|---|---|
| CHORUS | `2026-09-04f rep1` | 46 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CHORUS | `2026-09-04f rep2` | 33 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| CHORUS | `2026-09-04f rep3` | 57 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| VOICE | `2026-09-04f rep1` | 48 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| VOICE | `2026-09-04f rep2` | 35 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| VOICE | `2026-09-04f rep3` | 43 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| AI_READI | `2026-09-04g rep1` | 42 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| AI_READI | `2026-09-04g rep2` | 47 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| AI_READI | `2026-09-04g rep3` | 22 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| CM4AI | `2026-09-04g rep1` | 11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CM4AI | `2026-09-04g rep2` | 38 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CM4AI | `2026-09-04g rep3` | 47 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Per-project worst (`canary.baseline_for`, the `--canary-baseline` reader):

| project | prefix | pair errors | report findings | ungrounded identifiers | resolver URLs in identifier slots | organisational fragments | undeclared prefixes | British spellings |
|---|---|---|---|---|---|---|---|---|
| CHORUS | `2026-09-04f` | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| VOICE | `2026-09-04f` | 0 | 1 | 0 | 0 | 0 | 0 | 2 |
| AI_READI | `2026-09-04g` | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| CM4AI | `2026-09-04g` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Read through `canary.counts_from` and `canary.baseline_for` (sha256 of `canary.py`
`edc71f110f81e13e8ca3e94bbaa354d3d938962f9b3952b1928d68990ccfc447`), from the stored check blocks, which are what `--canary-baseline`
reads. They reproduce D21's "recomputed on 2026-10-09" values exactly:
- report findings: CHORUS 2, VOICE 1, AI_READI 1, CM4AI 0;
- British spellings: VOICE 2;
- pair errors, ungrounded identifiers, resolver URLs, organisational fragments and
  undeclared prefixes: 0 everywhere.

`d4d runs check` names the same three report findings among the confirmatory records:
CHORUS rep2 2 claims, VOICE rep2 1 and AI_READI rep3 1.

**Three caveats on instruments:**
- **Grounding.** "Ungrounded identifiers" and "resolver URLs in identifier slots"
  read the grounding block. `d4d runs check` reports "grounding blocks by instrument:
  none declared 19 (current v1)". The v8 blocks were written by the unversioned
  checker, while v10 records will carry v1 (#4090). So a pilot's baseline comparison
  on those two rows crosses instruments.
- **Report claims.** Every stored v8 `report_claims` block is instrument v7, but new
  API records are checked under v8. `check_report` defaults to
  `instrument_version=8` (`report_claims.py:903`), and the runner calls it without a
  version (`api_runner.py:4304`).
  - Under v8, a report that says a slot was removed when the slot was already absent
    from both records is a finding.
  - `d4d runs check` reports no report-claims instrument, so this crossing appears in
    no check output.
  - The next section recomputes the 12 blocks under both versions.
- **Form.** The form blocks are current (British v4, prefix v3), so the other form
  rows do not cross instruments. `notes/arm_comparison.md` recomputes the form
  metrics live under the current instruments. The figures above are the stored
  blocks that the gate reads, and this note did not compare the two.

## Report claims recomputed under v7 and v8

Recomputed read-only with `backfill_checks.compute(..., only={'report_claims'}, report_claims_version=v)`, which uses each record's recorded full and core schema bytes and writes nothing.

| project | label | stored block | stored findings | recomputed v7 findings | recomputed v8 findings | claims checked (v7 / v8) |
|---|---|---|---|---|---|---|
| CHORUS | `2026-09-04f rep1` | v7 | 0 | 0 | 0 | 46 / 46 |
| CHORUS | `2026-09-04f rep2` | v7 | 2 | 2 | 2 | 33 / 33 |
| CHORUS | `2026-09-04f rep3` | v7 | 0 | 0 | 1 | 57 / 57 |
| VOICE | `2026-09-04f rep1` | v7 | 0 | 0 | 0 | 48 / 48 |
| VOICE | `2026-09-04f rep2` | v7 | 1 | 1 | 1 | 35 / 35 |
| VOICE | `2026-09-04f rep3` | v7 | 0 | 0 | 0 | 43 / 43 |
| AI_READI | `2026-09-04g rep1` | v7 | 0 | 0 | 0 | 42 / 42 |
| AI_READI | `2026-09-04g rep2` | v7 | 0 | 0 | 0 | 47 / 47 |
| AI_READI | `2026-09-04g rep3` | v7 | 1 | 1 | 1 | 22 / 22 |
| CM4AI | `2026-09-04g rep1` | v7 | 0 | 0 | 0 | 11 / 11 |
| CM4AI | `2026-09-04g rep2` | v7 | 0 | 0 | 0 | 38 / 38 |
| CM4AI | `2026-09-04g rep3` | v7 | 0 | 0 | 0 | 47 / 47 |

per-project worst report findings: CHORUS v7 2, v8 2; VOICE v7 1, v8 1; AI_READI v7 1, v8 1; CM4AI v7 0, v8 0

**Results:**
- **v7 replay:** it reproduces every stored block exactly, which is the check that the
  replay is faithful.
- **v8:** it changes one record. CHORUS `04f` rep3 gains one finding,
  `removal_of_absent_slot` on `related_datasets`: the report says the slot was removed
  from the full record, but the key was already absent from the original full
  snapshot.
- **Totals:** the per-project worsts are the same under both versions, and the
  12-record total goes from 5 to 6.
- **What gets compared:** a v10 pilot's report findings, checked under v8, are compared
  by `--canary-baseline` with v8's stored v7 counts. That is a v7→v8 crossing, small
  on these records. Nothing here wrote to any provenance record.

## Per-call retry tally

calls 92; transport errors 5; answer-level retries after end_turn 3; calls retried 8 of 92

The 8 retried calls, from each record's `api_usage`:
- **5 transport errors**, each re-sent as the same attempt:
  - VOICE `04f` rep2 `full` (`RemoteProtocolError`);
  - VOICE `04f` rep3 `repair_full` (`RemoteProtocolError`);
  - AI_READI `04g` rep1 `reconcile_full` (`ReadError`);
  - AI_READI `04g` rep3 `repair_full` (`RemoteProtocolError`);
  - CM4AI `04g` rep1 `full` (`RemoteProtocolError`).
- **3 answer-level retries**, where an attempt ended `end_turn`, was rejected and the
  next attempt was requested:
  - CHORUS `04f` rep2 `full`, attempts 1→2 and 2→3;
  - AI_READI `04g` rep2 `audit`, attempts 1→2.

This matches the plan's "92 calls, 5 transport errors, 3 answer-level retries after
end_turn" (8 of 92).

## Other comparability facts `d4d runs check` reports for these records

From `d4d runs check --method claudecode_api` (exit 0: 19 runs checked, 0 failing).
All of these are reported and never fatal:
- **Profile identity:** for all 19 v8/v9 API records, "the recorded digest is not
  reproduced by the current renderer and profile vocabularies over the recorded
  schema".
- **Digest reconstruction:** the same check reports "19 historical digest-text
  reconstruction(s)", each "reproduced: candidate text reproduces the recorded
  digest; consumed implementation and profile are not attested by this
  reconstruction". So the digest text the v8 runs saw can be re-derived with
  historical code, but not with today's renderer.
- **Playbooks:** all 19 records name playbooks whose bytes have since changed
  (`d4d-full-core.md`, `d4d-agent.md`). The API runtime does not consume them
  (`playbooks.consumed: false`).
- **Temperature header:** in every v8 API record the header reads `Temperature: 0.0`
  while the record says `null`.
- **Output sizes:** one confirmatory record, VOICE `04f` rep1, records output sizes
  that differ from its files: full 64790→64794, core 57326→57348, report
  15667→17679. They were sized before a later phase rewrote the file (#1021). Its
  full record's sha256 equals that of its `intermediate/VOICE_repair_full_r1.yaml`, so
  its identity holds.
- **Unverifiable instructions:** the three CM4AI canaries (`04`, `04b`, `04c`) cannot
  be re-rendered, because their prompt pin was superseded on 2026-09-04. No
  confirmatory record is among the runs `runs check` could not confirm against its
  spec.
- **Values recorded but not observed:** `model.reasoning_effort` and
  `model.temperature`, 19 each. These are each record's `unverified` entries. For
  effort, the record states: "no effort is recorded: the header carries none and the
  route 'claude-opus-5' exposes no effort ladder, so the provider default applied".
  For temperature: "claude-opus-5 rejects `temperature` … so the 0.0 declared … is
  not sent".

## Not recomputed here

- The plan's "at 15d053d1a" base. This recompute is at `0a1132ecf`, and the only
  differences that matter are AI_READI's bundle and the crate classification above.
- Rubric scores and review verdicts. They are not P1 items, and E2/E5 re-measure
  them.
- Live form-instrument recomputation of British spellings and prefixes (see the
  caveats in the D21 section).

## Command manifest

Run from the repository root at `0a1132ecf`, with the project's environment. Every
command is read-only.

| # | command | exit | what it gives |
|---|---|---|---|
| 1 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python p1_recompute.py` (the script below) | 0 | every table in this note except the recall rows of the "Recall-target counts" section:<br>- the import check;<br>- record identity and provenance pins;<br>- records and bundles;<br>- the AI_READI crate citations;<br>- the attempts per cell and Set A definitions;<br>- the v6 drift and VOICE_PEDIATRIC;<br>- receipts and floors, validation and leaves;<br>- structure;<br>- the D21 metrics;<br>- the v7/v8 report-claims recompute;<br>- the retry tally.<br>About 1 minute. It runs `git show` on historical blobs and recovers drifted bundles from git; it writes nothing. |
| 2 | `PYTHONPATH=src python scripts/recall_target_baseline.py --check` | 0 | "notes/recall_target_baseline.md matches the records": the recall rows are that committed note's rows |
| 3 | `PYTHONPATH=src python -m data_sheets_schema.cli runs check --method claudecode_api` | 0 | bundle drift, report claims, instruments, profile identity, digest reconstruction, output sizes |
| 4 | `md5 -q data/preprocessed/concatenated/{P}_preprocessed.txt` for AI_READI, CHORUS, CM4AI, VOICE and VOICE_PEDIATRIC; `wc -c notes/matched_cborg_2026-09-13/kids_first/KIDS_FIRST_preprocessed.txt` | 0 | today's bundle md5s and the Kids First bundle size |

Inputs, by sha256:
- `notes/d4d_generation_plan_2026-10-09.md`: `fcc78fab909f94e533d2ed8e00ebc3d5165c82a9d30fcc7aa87db4541ae1266e`
- `notes/recall_target_baseline.md`: `a7f96768e976eb70594912a7f66b60fb9d4872defb0ecac35d083106ed5f48cf`
- `notes/arm_comparison.md`: `802e07da46e9851d880f82f2d1c1237f2a5126bcfdfb2e8b08e26b106123ac3f`
- `data/_wcrate/README.md`: `a66c66563e0288be9840e7e66808a8967b780a4689f0448028539786c97aed50`
- `src/data_sheets_schema/canary.py`: `edc71f110f81e13e8ca3e94bbaa354d3d938962f9b3952b1928d68990ccfc447`
- `src/data_sheets_schema/replicate_structure.py`: `c3c3131e8953d15a9f845ee6398d828c536e38d985959c005e49f173a5167b0e`
- `src/data_sheets_schema/receipts.py`: `7bfb84709b2e91983eae2b6dbaf8f67e13ef06b68473ad61947ebf6dd7542c9f`
- `scripts/recall_target_baseline.py`: `e89609655be029b8b562379eee898931d2c3568ea8330108d0660dd3f55fa569`
- the 12 provenance records: in the identity table above;
- the script below, saved as `p1_recompute.py` with a trailing newline: `fea66c6e53ee7cac48cd8a97dbae0da974c2f067cd719725eefd56c5ab750bfa`

The record and bundle hashes are in the tables above.

```python
"""P1 comparability recompute for the v8 API arm (read-only).

Run from the repository root:
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python p1_recompute.py
Reads committed records, bundles and git objects only; writes nothing.
"""
import collections
import glob
import hashlib
import subprocess
from pathlib import Path

import yaml

import importlib.util

from data_sheets_schema import backfill_checks, canary, receipts, replicate_structure
from data_sheets_schema.receipts import populated_leaves
from data_sheets_schema.replicate_structure import compare_structure, dataset_slots, summarize

CONCAT = Path("data/d4d_concatenated")
BUNDLES = Path("data/preprocessed/concatenated")
# The v8 API production arm: one date-letter prefix per project pair.
V8 = {"CHORUS": "2026-09-04f", "VOICE": "2026-09-04f", "AI_READI": "2026-09-04g", "CM4AI": "2026-09-04g"}
V6 = "2026-08-28_claude-opus-5-claudecode-generic-v6"
# The AI_READI chunk manifest as it was before #5042 removed the RO-Crate (1c4debbae).
PRE_5042_CHUNKS = "1c4debbae^:data/preprocessed/chunks/AI_READI_chunks.yaml"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def v8_records(project):
    pre = V8[project]
    return sorted(glob.glob(f"{CONCAT}/claudecode_api_core/{pre}_claude-opus-5-api-generic-v8_rep*/{project}_provenance.yaml"))


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


src = (Path.cwd() / "src").resolve()
print("## 0. Import check and record identity\n")
used = {m.__name__: Path(m.__file__).resolve() for m in (backfill_checks, canary, receipts, replicate_structure)}
assert all(src in p.parents for p in used.values()), "a module was imported from another checkout"
print("every module used resolves under this tree's `src/` (asserted): "
      + ", ".join(f"`{n}`" for n in sorted(used)))
print("\n| project | rep | provenance sha256 | repo.commit | dirty | dirty files | dirty paths recorded | schema | full schema sha256 |")
print("|---|---|---|---|---|---|---|---|---|")
states = set()
for project in V8:
    for prov in v8_records(project):
        rec = load(prov)
        repo, schema = rec["repo"], rec["schema"]
        paths = repo.get("dirty_paths")
        states.add((repo["commit"], tuple(sorted(paths)) if paths is not None else ("<not recorded>", repo.get("dirty_file_count"))))
        print(f"| {project} | {rec['run']['replicate']} | `{sha256(prov)[:16]}` | `{repo['commit_short']}` | {repo['dirty']} | "
              f"{repo.get('dirty_file_count')} | {len(paths) if paths is not None else 'not recorded'} | "
              f"{schema['declared_version']} | `{schema['full_sha256'][:12]}` |")
today_version = next(line.split(":", 1)[1].strip() for line in
                     Path("src/data_sheets_schema/schema/data_sheets_schema.yaml").read_text().splitlines()
                     if line.startswith("version:"))
print(f"\ndistinct recorded dirty states (commit, dirty paths): {len(states)}; today's schema "
      f"{today_version}, merged full schema sha256 "
      f"`{sha256('src/data_sheets_schema/schema/data_sheets_schema_all.yaml')[:12]}`")

today = {p: md5(BUNDLES / f"{p}_preprocessed.txt") for p in ("AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC")}

print("\n## 1. Records, hashes and bundles\n")
print("| project | label | canonical | full sha256 | core sha256 | bundle md5 (recorded) | today's bundle md5 | same bytes |")
print("|---|---|---|---|---|---|---|---|")
for project in V8:
    for prov in v8_records(project):
        rec = load(prov)
        out = rec["outputs"]
        b = rec["inputs"]["bundle_md5"]
        can = (rec.get("canonical") or {}).get("runtime") or ""
        print(f"| {project} | `{rec['run']['label']}` | {can} | `{sha256(out['full']['path'])[:16]}` | "
              f"`{sha256(out['core']['path'])[:16]}` | `{b[:8]}` | `{today[project][:8]}` | {'yes' if b == today[project] else 'no'} |")

print("\n## 1b. AI_READI: receipts that cite the RO-Crate chunks\n")
old = subprocess.run(["git", "show", PRE_5042_CHUNKS], capture_output=True, check=True).stdout
manifest = yaml.safe_load(old)
crate = [c["id"] for c in manifest["chunks"] if "ro_crate" in str(c.get("source", ""))]
print(f"pre-#5042 chunk manifest (`git show {PRE_5042_CHUNKS}`): sha256 `{hashlib.sha256(old).hexdigest()[:16]}`, "
      f"{len(manifest['chunks'])} chunks; RO-Crate chunks: {', '.join(crate)}\n")
print("| rep | pinned chunk manifest is the pre-#5042 one | receipted snippets | citing a crate chunk | top-level slots receipted from the crate | crate-chunk statuses |")
print("|---|---|---|---|---|---|")
for prov in v8_records("AI_READI"):
    rec = load(prov)
    pinned = (rec["inputs"].get("chunks") or {}).get("sha256") == hashlib.sha256(old).hexdigest()
    receipt = load(Path(prov).parent / "AI_READI_coverage_receipt.yaml")
    total = cited = 0
    slots, status = set(), {}
    for ch in receipt["chunks"]:
        entries = ch.get("extracted") or []
        total += len(entries)
        if ch["id"] in crate:
            cited += len(entries)
            status[ch["id"]] = ch.get("status")
            slots.update(str(e.get("slot", "")).split("[")[0].split(".")[0] for e in entries)
    print(f"| {rec['run']['replicate']} | {pinned} | {total} | {cited} | {len(slots)} | {status} |")

print("\n## 1c. v8 attempts per comparator cell, and two Set A definitions\n")
spec = importlib.util.spec_from_file_location("recall_target_baseline", "scripts/recall_target_baseline.py")
rtb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rtb)


def prompt_pin(rec):
    return next(f["sha256"] for f in rec["prompts"]["files"] if "generic_arm_prompt_v8" in f["path"])


def gates_pass(rec):
    floors = canary.receipt_floors(rec["receipts"])
    return bool(rec["validation"].get("passed")) and canary.duplicate_key_count(rec["validation"]) == 0 \
        and not any(floors.values())


attempts = collections.defaultdict(list)
for prov in sorted(glob.glob(f"{CONCAT}/claudecode_api_core/*_claude-opus-5-api-generic-v8_rep*/*_provenance.yaml")):
    rec = load(prov)
    full = load(rec["outputs"]["full"]["path"])
    receipt = load(Path(prov).parent / f"{rec['run']['project']}_coverage_receipt.yaml")
    texts, _basis = rtb.chunk_texts_for(rec["inputs"], Path("."))
    cand = rtb.receipt_candidates(receipt, texts)["candidates"]
    counts = rtb.target_counts(full)
    sl = rec["receipts"]["slots"]
    attempts[(rec["run"]["project"], rec["run"]["replicate"])].append({
        "label": rec["run"]["label"], "pin": prompt_pin(rec), "commit": rec["repo"]["commit_short"],
        "valid": rec["validation"].get("passed"), "dup": canary.duplicate_key_count(rec["validation"]),
        "floors": {k: v for k, v in canary.receipt_floors(rec["receipts"]).items() if v},
        "gates": gates_pass(rec), "with": sl["with_receipt"], "receiptable": sl["receiptable"],
        "leaves": len(populated_leaves(full)), "lineage": counts["lineage"], "variables": counts["variables"],
        "tools_versioned": counts["tools_versioned"], "lexical": None if cand is None else len(cand)})
comparator = {(proj, rep): next(a for a in attempts[(proj, rep)] if a["label"].startswith(V8[proj]))
              for proj in V8 for rep in (1, 2, 3)}
pins = {a["pin"] for a in comparator.values()}
assert len(pins) == 1, "the comparator records do not share one prompt pin"
PIN = pins.pop()
assert all(attempts[c][-1] is comparator[c] for c in comparator), "a comparator record is not its cell's final attempt"
print(f"comparator prompt pin (`d4d_generic_arm_prompt_v8.md`): `{PIN[:12]}`; every comparator record is its cell's final attempt\n")
print("| project | cell | label | prompt pin | commit | validation | duplicate keys | floors above 0 | coverage | leaves | lineage | variables | tools+ver | lexical |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for (proj, rep), rows in sorted(attempts.items(), key=lambda kv: (list(V8).index(kv[0][0]), kv[0][1])):
    for a in rows:
        print(f"| {proj} | rep{rep} | `{a['label'][:11]}` | `{a['pin'][:8]}` | `{a['commit']}` | {a['valid']} | {a['dup']} | "
              f"{', '.join(f'{k} {v}' for k, v in a['floors'].items()) or 'none'} | {a['with']}/{a['receiptable']} | "
              f"{a['leaves']} | {a['lineage']} | {a['variables']} | {a['tools_versioned']} | {a['lexical']} |")
DEFS = {
    "one record per cell (the final attempt)": lambda proj: [comparator[(proj, r)] for r in (1, 2, 3)],
    "every attempt under the comparator's pin": lambda proj: [a for r in (1, 2, 3) for a in attempts[(proj, r)] if a["pin"] == PIN],
    "every attempt, any pin (sensitivity)": lambda proj: [a for r in (1, 2, 3) for a in attempts[(proj, r)]],
}
TARGETS = {"AI_READI": ("variables",), "CM4AI": ("lexical",), "VOICE": ("variables", "lineage", "lexical", "tools_versioned"),
           "CHORUS": ("lineage",)}


def mean(values):
    return sum(values) / len(values)


print("\n| definition | project | records | pooled coverage | mean populated leaves | D02 recall targets (mean) | Set B (common gate) records |")
print("|---|---|---|---|---|---|---|")
for name, pick in DEFS.items():
    for proj in V8:
        rows = pick(proj)
        w, n = sum(a["with"] for a in rows), sum(a["receiptable"] for a in rows)
        targets = "; ".join(f"{k} {mean([a[k] for a in rows]):.2f}" for k in TARGETS[proj])
        print(f"| {name} | {proj} | {len(rows)} | {w}/{n} = {w / n:.3f} | {mean([a['leaves'] for a in rows]):.1f} | "
              f"{targets} | {sum(a['gates'] for a in rows)} of {len(rows)} |")

print("\n## 2. v6 drift (2026-08-28 agentic arm)\n")
print("| project | v6 bundle md5 (recorded, rep1–3) | today's bundle md5 | same bytes |")
print("|---|---|---|---|")
for project in ("AI_READI", "CHORUS", "CM4AI", "VOICE"):
    pins = sorted({load(p)["inputs"]["bundle_md5"] for p in
                   glob.glob(f"{CONCAT}/claudecode_agent_core/{V6}_rep*/{project}_provenance.yaml")})
    print(f"| {project} | {', '.join(f'`{x[:8]}`' for x in pins)} | `{today[project][:8]}` | "
          f"{'yes' if pins == [today[project]] else 'no'} |")

print("\n## 3. VOICE_PEDIATRIC\n")
vp = sorted(glob.glob(f"{CONCAT}/*_core/*/VOICE_PEDIATRIC_provenance.yaml"))
pins = collections.Counter(load(p)["inputs"]["bundle_md5"][:8] for p in vp)
print(f"today's bundle md5 `{today['VOICE_PEDIATRIC'][:8]}`; provenance records: {len(vp)}; "
      f"their bundle md5s: {dict(pins)}; consumed today's bytes: "
      f"{sum(1 for p in vp if load(p)['inputs']['bundle_md5'] == today['VOICE_PEDIATRIC'])}")

print("\n## 4. Receipt coverage, with denominators, and the receipt floors\n")
print("| project | label | chunks reviewed | snippets verified | snippets not in the chunk cited | mismatched / unattesting | receiptable slots with a receipt | never receipted | added after the receipt | receipt floors above 0 (`canary.receipt_floors`) |")
print("|---|---|---|---|---|---|---|---|---|---|")
tot = collections.Counter()
failing = []
for project in V8:
    for prov in v8_records(project):
        rec = load(prov)
        r = rec["receipts"]
        c, s, sl = r["chunks"], r["snippets"], r["slots"]
        off = int(s.get("adjacent") or 0) + int(s.get("elsewhere") or 0) + int(s.get("spans_boundary") or 0)
        floors = {k: v for k, v in canary.receipt_floors(r).items() if v}
        if floors:
            failing.append(f"{project} {rec['run']['label'][:11]} rep{rec['run']['replicate']}")
        tot.update({"slots": sl["receiptable"], "with": sl["with_receipt"], "never": sl["never_receipted"],
                    "added": sl["added_after_receipt"], "snip": s["total"], "ver": s["verified"], "off": off,
                    "chunks": c["total"], "rev": c["reviewed"], "mis": int(s.get("mismatched") or 0),
                    "una": int(s.get("unattesting") or 0)})
        print(f"| {project} | `{rec['run']['label'][:11]} rep{rec['run']['replicate']}` | {c['reviewed']}/{c['total']} | "
              f"{s['verified']}/{s['total']} | {off}/{s['total']} | {s.get('mismatched')} / {s.get('unattesting')} | "
              f"{sl['with_receipt']}/{sl['receiptable']} | "
              f"{sl['never_receipted']}/{sl['receiptable']} | {sl['added_after_receipt']}/{sl['receiptable']} | "
              f"{', '.join(f'{k} {v}' for k, v in floors.items()) or 'none'} |")
print(f"| **pooled** | 12 records | {tot['rev']}/{tot['chunks']} | {tot['ver']}/{tot['snip']} | "
      f"{tot['off']}/{tot['snip']} = {100 * tot['off'] / tot['snip']:.1f}% | {tot['mis']} / {tot['una']} | "
      f"{tot['with']}/{tot['slots']} = {100 * tot['with'] / tot['slots']:.1f}% | "
      f"{tot['never']}/{tot['slots']} = {100 * tot['never'] / tot['slots']:.1f}% | "
      f"{tot['added']}/{tot['slots']} = {100 * tot['added'] / tot['slots']:.1f}% | {len(failing)} of 12 |")
print(f"\nrecords with a receipt floor above 0: {'; '.join(failing)}")

print("\n## 4b. Validation, duplicate keys and populated leaves\n")
print("| project | rep1 / rep2 / rep3 validation passed | duplicate keys (`canary.duplicate_key_count`) | populated leaves (full record) | gate verdict block (`canary`) |")
print("|---|---|---|---|---|")
for project in V8:
    recs = [load(p) for p in v8_records(project)]
    passed = "/".join(str(r["validation"].get("passed")) for r in recs)
    dup = "/".join(str(canary.duplicate_key_count(r["validation"])) for r in recs)
    leaves = ",".join(str(len(populated_leaves(load(r["outputs"]["full"]["path"])))) for r in recs)
    gate = "; ".join(f"rep{r['run']['replicate']}: {(r.get('canary') or {}).get('recorded_by')}"
                     for r in recs if r.get("canary")) or "none"
    print(f"| {project} | {passed} | {dup} | [{leaves}] | {gate} |")

print("\n## 5. Replicate structure (#2932)\n")
slots = dataset_slots()
print(f"slot universe: {len(slots)} slots (`replicate_structure.dataset_slots`)\n")
print("| project | all / some / none | identical | nested in all: with a count / counts differ / max/min >= 2 | intermittent slots |")
print("|---|---|---|---|---|")
for project in V8:
    recs = {}
    for prov in v8_records(project):
        rec = load(prov)
        recs[f"rep{rec['run']['replicate']}"] = load(rec["outputs"]["full"]["path"])
    s = summarize(compare_structure(recs, slots))
    print(f"| {project} | {s['all']} / {s['some']} / {s['none']} | {s['identical']} | "
          f"{s['nested_in_all']}: {s['nested_counted']} / {len(s['counts_differ'])} / {len(s['ratio_ge_2'])} | "
          f"{len(s['intermittent'])} |")

print("\n## 6. Report findings and the seven D21 defect metrics\n")
names = [n for n, _, _ in canary.METRICS]
print("| project | label | report claims checked | " + " | ".join(names) + " |")
print("|---|---|---|" + "---|" * len(names))
for project in V8:
    for prov in v8_records(project):
        rec = load(prov)
        counts = canary.counts_from({"pair": rec.get("pair_consistency"), "report": rec.get("report_claims"),
                                     "grounding": rec.get("grounding"), "form": rec.get("form")})
        print(f"| {project} | `{rec['run']['label'][:11]} rep{rec['run']['replicate']}` | "
              f"{(rec.get('report_claims') or {}).get('claims_checked')} | " + " | ".join(str(counts[n]) for n in names) + " |")
print("\nPer-project worst (`canary.baseline_for`, the `--canary-baseline` reader):\n")
print("| project | prefix | " + " | ".join(names) + " |")
print("|---|---|" + "---|" * len(names))
for project, pre in V8.items():
    worst = canary.baseline_for(project, pre, method="claudecode_api")
    print(f"| {project} | `{pre}` | " + " | ".join(str(worst[n]) for n in names) + " |")

print("\n## 6b. Report claims under instrument v7 and v8\n")
print("Recomputed read-only with `backfill_checks.compute(..., only={'report_claims'}, report_claims_version=v)`, "
      "which uses each record's recorded full and core schema bytes and writes nothing.\n")
print("| project | label | stored block | stored findings | recomputed v7 findings | recomputed v8 findings | claims checked (v7 / v8) |")
print("|---|---|---|---|---|---|---|")
worst = {7: collections.Counter(), 8: collections.Counter()}
for project in V8:
    for prov in v8_records(project):
        rec = load(prov)
        stored = rec["report_claims"]
        got = {v: backfill_checks.compute(Path(prov), only={"report_claims"}, report_claims_version=v)["report_claims"]
               for v in (7, 8)}
        for v in (7, 8):
            worst[v][project] = max(worst[v][project], len(got[v].get("findings") or []))
        print(f"| {project} | `{rec['run']['label'][:11]} rep{rec['run']['replicate']}` | {str(stored.get('instrument'))[:2]} | "
              f"{len(stored.get('findings') or [])} | {len(got[7].get('findings') or [])} | {len(got[8].get('findings') or [])} | "
              f"{got[7].get('claims_checked')} / {got[8].get('claims_checked')} |")
print("\nper-project worst report findings: "
      + "; ".join(f"{p} v7 {worst[7][p]}, v8 {worst[8][p]}" for p in V8))

print("\n## 7. Per-call retry tally (`api_usage`)\n")
calls = transport = answer = 0
for project in V8:
    for prov in v8_records(project):
        rows = load(prov).get("api_usage") or []
        calls += len(rows)
        transport += sum(1 for r in rows if str(r.get("outcome") or "").startswith("transport error"))
        by_phase = collections.defaultdict(list)
        for r in rows:
            by_phase[r["phase"]].append(r)
        for rs in by_phase.values():
            # An answer-level retry: the phase's next attempt number after an
            # attempt that ended end_turn (a transport re-send keeps its number).
            answer += sum(1 for prev, nxt in zip(rs, rs[1:])
                          if prev.get("stop_reason") == "end_turn" and nxt["attempt"] > prev["attempt"])
print(f"calls {calls}; transport errors {transport}; answer-level retries after end_turn {answer}; "
      f"calls retried {transport + answer} of {calls}")
```
