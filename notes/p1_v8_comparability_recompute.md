# P1: v8 comparability recompute for the generic_v10 analysis plan

Step P1 of `notes/d4d_generation_plan_2026-10-09.md` ("#### P1"), recomputed on
2026-10-20 at main `0a1132ecf` (`0a1132ecf23f92c2cd128f6357f5248e57cd63f8`), the
base of branch `claude/track-p-analysis-plan`. Everything here is read from committed
records, bundles and notes by the commands in the manifest at the end. Nothing was
written to `data/`, no record or provenance block changed, and no provider was called.

The plan wrote P1 against `15d053d1a`. Where today's files differ from what the plan
states, this note gives today's value and says what changed.

## Which records are the v8 baseline

The v8 records on main are all API-runtime records under `claudecode_api/` and
`claudecode_api_core/` (`model.agent_runtime: Claude API (direct)`, provider
`LBL CBORG (proxy to Anthropic)`, model `claude-opus-5`). There is no other v8
method directory.

- **Confirmatory arm (D02's primary comparator): 12 records**, 3 per project:
  `2026-09-04f_claude-opus-5-api-generic-v8_rep{1,2,3}` for CHORUS and VOICE, and
  `2026-09-04g_claude-opus-5-api-generic-v8_rep{1,2,3}` for AI_READI and CM4AI. These
  are the records `notes/recall_target_baseline.md` and `notes/arm_comparison.md` call
  "v8 API production (2026-09-04f/g)".
- **Not in the baseline (D02 excludes them):** the canaries `2026-09-04`, `04b` and
  `04c` (CM4AI) and `04d` and `04e` (VOICE), and AI_READI `2026-09-04f` rep1, which
  `d4d runs check` reports as invalid by its own validation block (three top-level
  `source_caveats` keys, #1029).

**The coordination prompt's naming does not match the records.** It calls the arm
"v8 04f (`claudecode_assistant_agent`) and 04g (`claudecode_api_agent`)". Neither
method directory exists. `04f` and `04g` are two date-letter prefixes of one API
arm in `claudecode_api`, split by project pair rather than by method or runtime.
This note uses the records.

All 12 confirmatory records were generated under schema 2.0.0 (merged full schema
sha256 `b9b31acad29e…`) from four different dirty trees. By `repo.commit`:
- `26f7e4cd`: CHORUS and AI_READI rep1;
- `f294aeba`: VOICE rep1;
- `63d6d41c`: CM4AI rep1;
- `a2a3e157`: every rep2 and rep3.

Every record has `repo.dirty: true`. Main is at schema 3.0.0 (merged full schema
sha256 `eb543e1597b2…`).

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
today's file ("all four match today's files"; D02 lists AI_READI `d22b61a9`). That
held at `15d053d1a`. It no longer holds for AI_READI. #5042 removed the RO-Crate
source from the AI_READI corpus and rebuilt the bundle, so today's
`AI_READI_preprocessed.txt` is `1a58ad7b…` and all three AI_READI confirmatory
records (and the invalid `04f` rep1) now name a bundle whose bytes have changed. `d4d
runs check --method claudecode_api` reports the same: "4 record(s) name an input
bundle whose bytes have since changed … AI_READI_preprocessed.txt 4". CHORUS, CM4AI
and VOICE still match. Each record correctly states the bytes it consumed. A
generic_v10 AI_READI run will read different bytes, without the crate (#5042), so the
AI_READI comparison carries a bundle-scope difference the other three projects do
not.

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
are under `notes/matched_cborg_2026-09-13/kids_first/` (plan A19-reg), outside P1.

## Recall-target counts per record

From `notes/recall_target_baseline.md` (sha256 `a7f96768e976eb70594912a7f66b60fb9d4872defb0ecac35d083106ed5f48cf`), generated by
`scripts/recall_target_baseline.py` (sha256 `e89609655be029b8b562379eee898931d2c3568ea8330108d0660dd3f55fa569`). `--check` exits 0:
the committed note matches the records. The note fixes the cue patterns (sha256
`768a26a370bd…`) and the tools-version pattern (sha256 `4726c0058b01…`), the two
hashes the plan cites. Columns, in order:
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

## Receipt coverage, with denominators

| project | label | chunks reviewed | snippets verified | snippets not in the chunk cited | receiptable slots with a receipt | never receipted | added after the receipt | gated receipt findings |
|---|---|---|---|---|---|---|---|---|
| CHORUS | `2026-09-04f rep1` | 8/8 | 79/79 | 0/79 | 54/186 | 127/186 | 5/186 | 0 |
| CHORUS | `2026-09-04f rep2` | 8/8 | 87/90 | 1/90 | 83/248 | 157/248 | 8/248 | 0 |
| CHORUS | `2026-09-04f rep3` | 8/8 | 114/117 | 1/117 | 78/198 | 118/198 | 2/198 | 0 |
| VOICE | `2026-09-04f rep1` | 22/22 | 238/243 | 5/243 | 223/343 | 116/343 | 4/343 | 0 |
| VOICE | `2026-09-04f rep2` | 22/22 | 237/248 | 11/248 | 141/261 | 120/261 | 0/261 | 0 |
| VOICE | `2026-09-04f rep3` | 22/22 | 222/231 | 9/231 | 220/382 | 159/382 | 3/382 | 0 |
| AI_READI | `2026-09-04g rep1` | 28/28 | 346/351 | 5/351 | 280/480 | 192/480 | 8/480 | 0 |
| AI_READI | `2026-09-04g rep2` | 28/28 | 319/339 | 19/339 | 163/420 | 250/420 | 7/420 | 0 |
| AI_READI | `2026-09-04g rep3` | 28/28 | 310/314 | 4/314 | 251/389 | 137/389 | 1/389 | 0 |
| CM4AI | `2026-09-04g rep1` | 28/28 | 156/174 | 18/174 | 279/374 | 95/374 | 0/374 | 0 |
| CM4AI | `2026-09-04g rep2` | 28/28 | 153/186 | 33/186 | 312/424 | 109/424 | 3/424 | 0 |
| CM4AI | `2026-09-04g rep3` | 28/28 | 136/184 | 47/184 | 226/389 | 155/389 | 8/389 | 0 |
| **pooled** | 12 records | 258/258 | 2397/2556 | 153/2556 = 6.0% | 2310/4094 = 56.4% | 1735/4094 = 42.4% | 49/4094 = 1.2% | |

The pooled row reproduces `notes/arm_comparison.md` (sha256 `802e07da46e9851d880f82f2d1c1237f2a5126bcfdfb2e8b08e26b106123ac3f`,
"Receipt coverage and attribution, pooled per arm") exactly: 2310/4094 = 56.4% with a
receipt, 1735/4094 never receipted, 49/4094 added after the receipt, and 153/2556 not
in the chunk cited. Every receipts block is instrument v3, the current one (`d4d runs
check`: "receipts blocks by instrument: v3 19 (current v3)"). No confirmatory record
has a gated receipt finding.

## Validation, duplicate keys and populated leaves

| project | rep1 / rep2 / rep3 validation passed | duplicate keys (full + core) | populated leaves (full record) |
|---|---|---|---|
| CHORUS | True/True/True | 0 | [235,278,251] |
| VOICE | True/True/True | 0 | [386,297,432] |
| AI_READI | True/True/True | 0 | [525,525,449] |
| CM4AI | True/True/True | 0 | [422,473,479] |

Populated leaves use `receipts.populated_leaves` (sha256 of `receipts.py`
`7bfb84709b2e91983eae2b6dbaf8f67e13ef06b68473ad61947ebf6dd7542c9f`), the counter `scripts/arm_comparison.py` uses. The bracketed values
match the committed "populated leaves (full record)" rows of `notes/arm_comparison.md`.
`validation.passed` is the block `d4d provenance recheck-validation` wrote; it validated
each record against its run's schema.

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

`notes/arm_comparison.md` recomputes the form metrics live under the current
instruments. The figures above are the stored blocks that the gate reads; this note
did not compare the two.

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
  schema". The model-facing schema digest these runs saw cannot be re-rendered with
  today's code, which is one more reason claims stay package-level.
- **Playbooks:** all 19 records name playbooks whose bytes have since changed
  (`d4d-full-core.md`, `d4d-agent.md`). The API runtime does not consume them
  (`playbooks.consumed: false`).
- **Temperature header:** the header reads `Temperature: 0.0` while the record says
  `null`, in every v8 API record.
- **Unverifiable instructions:** the three CM4AI canaries (`04`, `04b`, `04c`) cannot be
  re-rendered, because their prompt pin was superseded on 2026-09-04. No confirmatory
  record is among the runs `runs check` could not confirm against its spec.
- **Values recorded but not observed:** `model.reasoning_effort` and
  `model.temperature`, 19 each. These are each record's `unverified` entries. For
  effort, the record states: "no effort is recorded: the header carries none and the
  route 'claude-opus-5' exposes no effort ladder, so the provider default applied".
  For temperature: "claude-opus-5 rejects `temperature` … so the 0.0 declared … is
  not sent".

## Not recomputed here

- The plan's "at 15d053d1a" base. This recompute is at `0a1132ecf`, and the only
  difference that matters is the AI_READI bundle above.
- Rubric scores and review verdicts. They are not P1 items, and E2/E5 re-measure
  them.
- Live form-instrument recomputation of British spellings and prefixes (see the note
  in the D21 section).

## Command manifest

Run from the repository root at `0a1132ecf`, with the project's environment
(`PYTHONPATH=src`). Every command is read-only.

| # | command | exit | what it gives |
|---|---|---|---|
| 1 | `PYTHONPATH=src python p1_recompute.py` (the script below) | 0 | every table in sections "Which records are the v8 baseline" to "Per-call retry tally", in about 8 s |
| 2 | `PYTHONPATH=src python scripts/recall_target_baseline.py --check` | 0 | "notes/recall_target_baseline.md matches the records" |
| 3 | `PYTHONPATH=src python -m data_sheets_schema.cli runs check --method claudecode_api` | 0 | bundle drift, report claims, instruments, profile identity |
| 4 | `md5 -q data/preprocessed/concatenated/{P}_preprocessed.txt` for AI_READI, CHORUS, CM4AI, VOICE and VOICE_PEDIATRIC | 0 | today's bundle md5s |

Inputs, by sha256:
- `notes/d4d_generation_plan_2026-10-09.md`: `fcc78fab909f94e533d2ed8e00ebc3d5165c82a9d30fcc7aa87db4541ae1266e`
- `notes/recall_target_baseline.md`: `a7f96768e976eb70594912a7f66b60fb9d4872defb0ecac35d083106ed5f48cf`
- `notes/arm_comparison.md`: `802e07da46e9851d880f82f2d1c1237f2a5126bcfdfb2e8b08e26b106123ac3f`
- `src/data_sheets_schema/canary.py`: `edc71f110f81e13e8ca3e94bbaa354d3d938962f9b3952b1928d68990ccfc447`
- `src/data_sheets_schema/replicate_structure.py`: `c3c3131e8953d15a9f845ee6398d828c536e38d985959c005e49f173a5167b0e`
- `src/data_sheets_schema/receipts.py`: `7bfb84709b2e91983eae2b6dbaf8f67e13ef06b68473ad61947ebf6dd7542c9f`
- `scripts/recall_target_baseline.py`: `e89609655be029b8b562379eee898931d2c3568ea8330108d0660dd3f55fa569`
- the script below, saved as `p1_recompute.py` with a trailing newline: `3d6e97cd3c2926cda21ad90b6aa264051daba26aaeee70e7535a5d0c0b894edd`

The record and bundle hashes are in the tables above.

```python
"""P1 comparability recompute for the v8 API arm (read-only).

Run from the repository root:
    PYTHONPATH=src python p1_recompute.py
Reads committed records and bundles only; writes nothing.
"""
import collections
import glob
import hashlib
from pathlib import Path

import yaml

from data_sheets_schema import canary
from data_sheets_schema.replicate_structure import compare_structure, dataset_slots, summarize

CONCAT = Path("data/d4d_concatenated")
BUNDLES = Path("data/preprocessed/concatenated")
# The v8 API production arm: one date-letter prefix per project pair.
V8 = {"CHORUS": "2026-09-04f", "VOICE": "2026-09-04f", "AI_READI": "2026-09-04g", "CM4AI": "2026-09-04g"}
V6 = "2026-08-28_claude-opus-5-claudecode-generic-v6"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def v8_records(project):
    pre = V8[project]
    return sorted(glob.glob(f"{CONCAT}/claudecode_api_core/{pre}_claude-opus-5-api-generic-v8_rep*/{project}_provenance.yaml"))


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


today = {p: md5(BUNDLES / f"{p}_preprocessed.txt") for p in ("AI_READI", "CHORUS", "CM4AI", "VOICE", "VOICE_PEDIATRIC")}

print("## 1. Records, hashes and bundles\n")
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

print("\n## 4. Receipt coverage, with denominators\n")
print("| project | label | chunks reviewed | snippets verified | snippets not in the chunk cited | receiptable slots with a receipt | never receipted | added after the receipt | gated receipt findings |")
print("|---|---|---|---|---|---|---|---|---|")
tot = collections.Counter()
for project in V8:
    for prov in v8_records(project):
        rec = load(prov)
        r = rec["receipts"]
        c, s, sl = r["chunks"], r["snippets"], r["slots"]
        off = int(s.get("adjacent") or 0) + int(s.get("elsewhere") or 0) + int(s.get("spans_boundary") or 0)
        tot.update({"slots": sl["receiptable"], "with": sl["with_receipt"], "never": sl["never_receipted"],
                    "added": sl["added_after_receipt"], "snip": s["total"], "ver": s["verified"], "off": off,
                    "chunks": c["total"], "rev": c["reviewed"]})
        print(f"| {project} | `{rec['run']['label'][:11]} rep{rec['run']['replicate']}` | {c['reviewed']}/{c['total']} | "
              f"{s['verified']}/{s['total']} | {off}/{s['total']} | {sl['with_receipt']}/{sl['receiptable']} | "
              f"{sl['never_receipted']}/{sl['receiptable']} | {sl['added_after_receipt']}/{sl['receiptable']} | "
              f"{r.get('findings_gated')} |")
print(f"| **pooled** | 12 records | {tot['rev']}/{tot['chunks']} | {tot['ver']}/{tot['snip']} | "
      f"{tot['off']}/{tot['snip']} = {100 * tot['off'] / tot['snip']:.1f}% | "
      f"{tot['with']}/{tot['slots']} = {100 * tot['with'] / tot['slots']:.1f}% | "
      f"{tot['never']}/{tot['slots']} = {100 * tot['never'] / tot['slots']:.1f}% | "
      f"{tot['added']}/{tot['slots']} = {100 * tot['added'] / tot['slots']:.1f}% | |")

print("\n## 4b. Validation, duplicate keys and populated leaves\n")
from data_sheets_schema.receipts import populated_leaves
print("| project | rep1 / rep2 / rep3 validation passed | duplicate keys (full + core) | populated leaves (full record) |")
print("|---|---|---|---|")
for project in V8:
    recs = [load(p) for p in v8_records(project)]
    passed = "/".join(str(r["validation"].get("passed")) for r in recs)
    dup = sum(int(v or 0) for r in recs for v in ((r["validation"].get("duplicate_keys") or {}).values()))
    leaves = ",".join(str(len(populated_leaves(load(r["outputs"]["full"]["path"])))) for r in recs)
    print(f"| {project} | {passed} | {dup} | [{leaves}] |")

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
