# Step A1 offline sizing for generic_v10 API requests (2026-10-20)

Issues: #5072, #4829, #4830. Plan: `notes/d4d_generation_plan_2026-10-09.md`,
step A1, with A1b, D07, risk 6 and open question 6. Branch
`fix/5072-offline-sizing-recovery` (PR #5087).

No provider was contacted, billed or unbilled: sockets were blocked and the
sweep recorded 0 network calls. Every token figure below is an **estimate
from bytes, not a count**. None of them can clear a request; only the unbilled
A1b `messages.count_tokens` count can, read through `offline_sizing check`
(see "What this does not establish").

## Answer

**No `max_paths` / `max_workers` setting makes a generic_v10 typed-audit
worker fit the 1,000,000-token window, for any of the six projects.**
Partitioning changes how many workers there are, not how large each one is.
Every worker request repeats the same shared content. On each project's
primary record the largest worker moved by at most 0.4% across six grids:
- CHORUS: 2,458,942–2,463,420 B;
- AI_READI: 3,836,702–3,851,036 B.

Estimated tokens in flight, as input plus the request's `max_tokens`, at the
A3 draft grid G2 (`max_paths` 192, `max_inventory_bytes` 32,768,
`max_workers` 16). "Over" marks a value above its ceiling: 1,000,000 for a
worker and every other request, 850,000 for the report family.

| Project | Largest worker | Largest worker across records at G2 | Omission | Integration | Receipt completion | Report | Regate (report at its 96k cap) |
|---|---|---|---|---|---|---|---|
| CHORUS | 1,013,951 over | 1,013,951–1,098,816 (4 records) | 806,748 | 1,008,540 over | 700,719 | 460,895 | 556,346 |
| AI_READI | 1,503,814 over | 1,415,395–1,503,814 (3) | 1,214,717 over | 1,468,918 over | 893,690 | 984,434 over | 1,079,889 over |
| CM4AI | 1,244,905 over | 1,244,905–1,276,340 (3) | 986,532 | 1,221,330 over | 829,263 | 690,922 | 786,450 |
| VOICE | 1,447,155 over | 1,430,528–1,513,288 (3) | 1,163,040 over | 1,421,276 over | 870,319 | 892,063 over | 987,660 over |
| VOICE_PEDIATRIC (proxy) | 1,353,608 over | 1,337,456–1,422,915 (3) | 1,080,571 over | 1,327,730 over | 793,958 | 827,362 | 922,938 over |
| KIDS_FIRST (proxy) | 1,599,199 over | 1,503,476–1,599,199 (3) | 1,269,845 over | 1,561,193 over | 947,084 | 1,058,687 over | 1,154,342 over |

How far over:
- **CHORUS** is at the edge. Its largest worker estimate is 1.4% over, and
  the range of calibrated ratios (966,371–1,013,951) straddles the ceiling.
  Its v8 records are larger, up to 1,098,816.
- **Every other project** is 24–60% over, beyond any ratio uncertainty.
- **Kids First** now has the largest bundle (541,184 B against AI_READI's
  430,393 since #5042), and so the largest requests. It is sized by proxy:
  no record exists.

Full, the re-address turn, receipt completion, `reconcile_full` and repair fit
for every project; Kids First's receipt completion (947,084) and
`reconcile_full` (899,562) fit narrowly. CM4AI's omission stage fits on its
primary record but not on its other two (1,014,934 and 1,013,549).

**Why.** The schema is carried twice in every typed request:
1. **The typed request's own catalog.** It covers every class reachable from
   `Dataset`, with every induced slot's full LinkML definition
   (`audit_omissions._schema`), whatever the record holds. Its size is
   identical in all six projects:
   - 1,486,502 B in every worker and in integration: 60% of CHORUS's largest
     worker, 39% of AI_READI's and 38% of Kids First's;
   - 1,246,504 B in the omission request;
   - 1,542,013 B inside receipt completion's inputs.
2. **The schema context's induced-slot `classes`** for the classes the record
   occupies: 615,443 B for CHORUS and 949,673 B for AI_READI.

Next to these, the rest is small:
- the bundle: 15% of Kids First's worker, 13% of AI_READI's, 2% of CHORUS's;
- the owners' YAML and typed trees;
- the full-record inventory, repeated in every worker (2–4%);
- the worker's own assignment, 0.1–0.3%, the only part partitioning controls.

This answers the plan's open question 6 and confirms risk 6.

## Recommended configuration

**Partition: keep G2 (`max_paths` 192, `max_inventory_bytes` 32,768,
`max_workers` 16), the A3 draft default.**
- It is valid for every project. G1, `typed_audit.prepare`'s own default
  (96 / 16,384), is refused for AI_READI, CM4AI and Kids First with
  `indivisible_field_bound`.
- It gives 2–6 workers, inside `max_calls` 18 (W + 2).
- Larger grids save calls but make every worker slightly larger.

It does not make a worker fit, and no partition does.

**To meet the A1 rule, the shared payload must shrink.** Seven options were
measured by removing parts from the actual requests: exact for bytes,
estimated for tokens. The complete table for each project is in the
appendix.

| Option | What changes | Result on the primary records |
|---|---|---|
| S1 | typed requests stop carrying their own schema catalog; the schema context stays | every typed stage fits for every project (Kids First's worker by 1.1%); the report family still exceeds for AI_READI, VOICE and Kids First, and VOICE_PEDIATRIC's regate |
| S2 | the schema context's induced-slot `classes` dropped; the typed catalog stays | the report family fits everywhere; workers and integration still exceed for AI_READI, VOICE and Kids First |
| S3 | S1 plus the full-record inventory dropped from each worker | as S1, slightly smaller workers |
| S4 | S1 plus owners without their typed trees | as S1; VOICE's report fits, but its regate and AI_READI's and Kids First's report and regate still exceed |
| S5 | induced-slot definitions trimmed to name, description, range, cardinality and inlining | the report family fits except Kids First's regate; workers still exceed for every project but CHORUS |
| S6 | S1 plus S5 | every stage fits for every project except Kids First's regate (881,096, 3.7% over) |
| **S7** | **S6 plus owners without their typed trees** | **every stage fits for all six projects** |

Under S7, on the primary records:

| Project | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|
| CHORUS | 187,252 | 131,441 | 181,841 | 113,389 | 284,009 | 379,399 |
| AI_READI | 551,321 | 400,851 | 516,425 | 321,487 | 647,337 | 742,753 |
| CM4AI | 381,354 | 277,051 | 357,778 | 241,932 | 462,266 | 557,716 |
| VOICE | 463,677 | 342,350 | 437,799 | 282,989 | 551,437 | 646,918 |
| VOICE_PEDIATRIC (proxy) | 370,130 | 259,881 | 344,252 | 206,628 | 486,737 | 582,195 |
| KIDS_FIRST (proxy) | 599,614 | 434,218 | 561,608 | 359,754 | 708,262 | 803,796 |

The closest are Kids First's regate (803,796, 5.4% under 850,000) and
AI_READI's (742,753, 12.6% under). Both are estimates, and Kids First's rests
on a stand-in record.

The other records can be larger than the primary, as the record-sensitivity
tables show:
- CHORUS's v8 records: up to 84,865 tokens more on the largest worker and
  99,136 more on the regate;
- VOICE_PEDIATRIC (VOICE's records): 69,307 and 52,535 more;
- VOICE rep3: 66,133 and 52,536 more;
- CM4AI: 31,435 and 16,532 more.

AI_READI's primary is its largest record, and Kids First's proxy uses the
same records. Adding each project's largest difference to its S7 figures
keeps every one under its ceiling. The catalog S7 removes does not depend on
the record, so a larger record adds about the same absolute amount with or
without S7. That is why the differences are added rather than scaled.

**S7 is not decided here.** It changes model-facing text, which makes it a
new shared-generation version at a condition boundary (D17). It touches:
- `shared_generation.py`, which only agy edits;
- the typed audit (`typed_audit.py`, `audit_omissions.py`);
- receipt completion;
- an asset and prompt pin review.

It needs the owner's decision. Three design questions stand out:
- **The catalog's role.** The typed audit's code keeps using its catalog for
  its own checks; S1 removes only the model-facing copy.
- **S5's key list** (`domain_of`, `from_schema`, `alias`, `owner`, `@type`,
  `slot_uri`, `annotations`, `exact_mappings`). It is a candidate; whether
  `slot_uri` and mappings must stay model-facing is a design question.
- **The owners' typed trees** (`whole_value_identity`). They duplicate each
  owner's YAML in another form; whether relationship review needs them is
  also open.

Under D07 the AI_READI lines are already provisional and re-planned before
A14 when a request does not fit. This is that evidence, and it reaches Kids
First too.

## Method

**Tree measured.** `8ea7986160a5b0a3079f64c12f9d59074ff564af`
(`origin/feat/v10-preflight-scripts`, PR #5095: main with #5093, #5094 and
#5095, the pre-launch stack). It was checked out detached in a scratch
worktree, and was unchanged afterwards. `data_sheets_schema` and `scripts`
are namespace packages. The sweep removed every other checkout from the
import path and recorded that no module came from outside the tree.

**Registrations.** Each run used the A3 draft builder
(`scripts/build_api_registrations.build_registration`) with the A5d omission
contexts:
- selection: `shared_generation_v1`, renderer 25, `Claude API (direct)`,
  playbook v2, receipt completion v2;
- runtime: claude-opus-5, thinking `{adaptive, summarized}` (D06);
- audit limits: the builder's defaults (worker, omission and integration
  output 4,000 each; `max_calls` 18), with each grid's partition values.

Kids First has no A5d context. Its root-only draft context was synthesized
by the same builder's `build_draft_context` from its own source manifest
(`notes/matched_cborg_2026-09-13/kids_first/manifest.yaml`). It runs with
the neutral profile (A19-reg), its bundle (541,184 B, md5 `93b80751`) and
its 58-chunk manifest (`chunks.yaml`).

The run specification is read back from the registration, as
`offline_sizing._spec_from_registration` does.

**Requests.** Each was built by the production code, as plan step A1
prescribes:
- `typed_audit_runtime.prepare_packet` and `build_request` for every worker,
  the omission stage and integration;
- `receipt_completion.build_request` and `request_payload`;
- `api_runner.build_phase` for full, `build_readdress`, `reconcile_full` and
  report, with the `PHASE_NEEDS` carries;
- `_append_regate` for the regate;
- `build_repair` plus the generation context.

Caps come from the payloads themselves and `phase_max_tokens`: full 128,000;
re-address 8,000; `reconcile_full`, report, regate and repair 96,000; typed
stages and receipt completion 4,000. As in the A1 harness, receipt
recovery and the integration index are inert stand-ins.

**Stand-in records.** generic_v10 has no records, so historical phase-1
originals stand in:

| Project | Primary record | Other records |
|---|---|---|
| CHORUS | v9 `2026-09-12` rep1 (named by the plan) | v8 `2026-09-04f` rep1–rep3 |
| AI_READI | v8 `2026-09-04g` rep2 (named by the plan) | rep1, rep3 |
| CM4AI | v8 `2026-09-04g` rep1 | rep2, rep3 |
| VOICE | v8 `2026-09-04f` rep1 | rep2, rep3 |
| VOICE_PEDIATRIC | proxy: VOICE's records | as VOICE |
| KIDS_FIRST | proxy: AI_READI's records, the largest | as AI_READI |

Notes on the stand-ins:
- **AI_READI `2026-09-04f` rep1** is left out. It carries three top-level
  `source_caveats` and is declared invalid by its own validation block
  (#1029).
- **The proxies** use the stand-in project's records with the proxy
  project's own bundle and chunk manifest. VOICE_PEDIATRIC uses its own
  context; Kids First uses the synthesized draft. Each proxy's receipt is
  minimal (every chunk `nothing_relevant`), which understates a real receipt
  by about 33–37 KB.

Each record passes through the runner's write-time normaliser. It is then
conformed to the current schema's cardinality, which the typed audit's owner
traversal enforces (see Finding 1):
- **Edits.** Every one of the 13 records needed 2–11 edits: scalars wrapped,
  single items unwrapped, several scalars in a single-valued slot joined.
  One slot the schema does not declare was removed, AI_READI `04g` rep3
  `data_governance.accountable_organization_notes`.
- **Bytes.** The edits use a round-trip YAML dump. Records stay within −391
  to +95 bytes; a plain re-dump shrank them by 7–8%.

AI_READI's v8 receipts pin bundle `d22b61a9`, which #5042 replaced with
`1a58ad7b`. They were carried onto today's manifest by chunk sha256, using
the manifest at `1cde41f59`: 25 entries moved, and the three RO-Crate chunks
`c022`–`c024` were dropped.

**Placeholders.** Content that cannot exist before a run is sized at its cap,
in tokens:
- the audit findings, at 4,000;
- the report as written in the regate, at 96,000. The appendix also sizes it
  with the v8 report text;
- each worker and omission response that integration carries, at 4,000.

**Calibration.** Tokens are payload bytes times the tokens-per-byte ratio
A1b counted for the same project and stage on 2026-10-12. The source is
`notes/.local_drafts/a1b_calibrated_tokens.json` at local commit `10dee83fe`,
sha256 `3146ef36c265d4d06058da242c49ccd3804d24b771cc4fe43a1d7496c5924186`.
- **Projects A1b did not count** (CM4AI, VOICE, VOICE_PEDIATRIC, Kids First)
  get the higher of the CHORUS and AI_READI ratios.
- **Ranges.** Each estimate's range uses the lower and higher ratio.
- **Ratios.** The calibrated ratios run 0.34–0.41.
- **Placeholder correction.** A1b's report-family payloads carried
  `'x' * (4 × cap)` placeholders, and the endpoint counted about one token
  per `x`. Regate minus report is +382,173 B and +383,458 tokens in both
  projects. The clean ratios remove the placeholders. Report and regate then
  agree to four decimals (CHORUS 0.3685/0.3686, AI_READI 0.3545/0.3545),
  which checks the correction.

**Verdicts.** Rows read `estimate_fits` or `estimate_exceeds` against:
- 1,000,000 for a worker;
- 850,000 for report, regate and the after-repair report;
- 1,000,000 for everything else.

They never read `PASS`. The evidence reader now enforces the same ceilings
on saved counts, whatever window or margin a caller declares.

**Reproducibility.** Three sweeps were run:

| Sweep | Script snapshot (sha256) |
|---|---|
| full sweep | `19c54ebe…` |
| primary-record component rerun | `e9f2b22b…` |
| Kids First sweep | the committed script before the `S7` option was added |

The committed script differs from those only in reporting: the `table` and
`merge` subcommands, the options and path tidying.

Merging refuses any difference except one uniform byte offset on typed
stages:
- **Ordinary phases** matched exactly between the full sweep and the rerun.
- **Typed stages** differed by +18 B in every project. The run directory's
  path reaches typed-stage text (plan risk 7), and the rerun's scratch
  directory name was 6 characters longer.
- **Kids First** was measured only by its own sweep, which the full sweep
  could not stage.

Scratch paths are longer than the launch base's, so the figures overstate by
a few dozen bytes per request.

Results files:

| File | sha256 |
|---|---|
| full sweep | `1991d8625724526fa4cd596051af45ab15278d104ff0f56c1964ca1e964577d1` |
| rerun | `54075fcf98f2a111eb225352947464cfff6d167fcb6080b3fb9648a855b9133b` |
| Kids First | `c8d1c25b638004ae81d8f06488396f116f22e914c76ecc52286c89aa46917d5a` |
| merged | `1310952d9067103b0a2bfa5ee65a9a72330ffc46342fdd03c8de85fb7c63309d` |

They are not committed. The commands below regenerate them from tracked
files.

## Corrections to the earlier A1 and A1b record

1. **The A1b report-family counts are inflated by the placeholders.** CHORUS's
   regate "879,597 total, 12.0% headroom, FAIL" becomes about 579,597 when
   recomputed from A1b's own numbers: placeholders out, the report at its
   96k cap, findings at their 4k cap. Today's builders give 556,346, 34.5%
   headroom. The CHORUS regate is not a binding constraint.

   AI_READI's report and regate failures are real: about 1.02M and 1.11M on
   A1b's numbers, 984,434 and 1,079,889 today. The A1b draft on local `main`
   (`10dee83fe`) still lists the CHORUS regate as a FAIL.
2. **A1b's worker "Output Cap" column (16,000) was a constant** in its report
   formatter. The registration's worker cap is 4,000. No verdict changes.
3. **The AI_READI A1b counts predate #5042.** Today's AI_READI largest worker
   is 146,510 B smaller (3,836,702 against 3,983,212), and still about 50%
   over the ceiling.

## Findings for the integrator

I can't file issues; agy files these.

1. **Possible launch risk: the typed audit refuses records with scalars in
   nested multivalued slots.**
   - `audit_omissions._owners` requires a value's list-ness to match the
     slot's `multivalued`.
   - The write-time normaliser lists scalars only for slots in its table, and
     nested inlined slots are not covered.
   - All 13 historical v8/v9 records would have been refused as written. For
     example, CHORUS v9 rep1 `/machine_annotation_tools/0/tools`,
     `/existing_uses/0/examples` and `/external_resources/0/external_resources`;
     CHORUS v8 `/sampling_strategies/0/strategies`, which is two strings in a
     single-valued slot.

   If a generic_v10 phase-1 original has the same shape, `prepare_packet`
   raises "record cardinality prevents unambiguous owner traversal". That
   happens after full and receipt completion are billed.

   Not verified here: whether validation and repair settle cardinality
   before the originals are frozen.
2. **The A1b placeholder method.** Runs of `x` count about one token each, not
   a quarter. `build_phase`'s dry-run source-review placeholder
   (`'x' * (2 * len + 1024)`) would overcount the same way if it were ever
   counted.
3. **Old receipts and today's bundle.** AI_READI's v8 receipts name the
   pre-#5042 bundle, so receipt validation refuses them against today's. An
   A1b recount on today's bundle needs a carried receipt (as here) or a fresh
   run.
4. **Kids First is the largest case, and its inputs are incomplete.** Its
   bundle (541,184 B) and chunk and source manifests are tracked under
   `notes/matched_cborg_2026-09-13/kids_first/`, not `data/preprocessed/`.
   It has no A5d omission context in #5095 and no record, so here it is
   sized by proxy. Its A1b count needs an A5d context first, and its
   requests are the largest of the six.
5. **The integration figure is only partly bounded.** It counts each worker
   and omission response at its cap, but not the proposal index derived from
   them, so it understates.
6. **`typed_audit.prepare`'s default limits** (96 paths, 16,384 B) are refused
   for AI_READI, CM4AI and Kids First. The A3 default (G2) is valid.
7. **Run-specific strings reach typed-stage text.** A 6-character longer run
   directory adds 18 B to every typed request, which confirms plan risk 7 for
   these stages.

## What this does not establish

- **Token counts.** Every figure is bytes times a ratio. Ratios differ by
  content, so a request whose mix differs from what A1b counted carries more
  uncertainty than its range shows. That applies to the S1–S7 rows above
  all, since they remove one kind of content and keep the request's ratio.
- **Fit.** Nothing here makes a request fit, or makes a launch acceptable.
- **The report as v10 will write it.** The report-family estimates use the
  v8 reconciled records and, at worst, the 96k cap.
- **The proxies.** VOICE_PEDIATRIC and Kids First are proxies, and Kids
  First's record and context are stand-ins.
- **The provider side.** Provider support, billing and the thinking display
  on count calls are not checked here; agy's A1b count settles them.

## Reproduce

The sweep needs a checkout of #5095 (the A3 builder and A5d contexts) and
this branch's script. Make no provider call; the script blocks sockets.

```sh
git -C <repository> worktree add --detach <tree> 8ea7986160a5b0a3079f64c12f9d59074ff564af
cd <tree>
P="PYTHONPATH=<tree>/src:<tree>"
env $P python <branch>/scripts/offline_sizing.py sweep --root <tree> \
  --workdir <new dir A> --out full.json
env $P python <branch>/scripts/offline_sizing.py sweep --root <tree> \
  --workdir <new dir B> --out rerun.json --grid G2 --primary-only \
  --projects CHORUS AI_READI CM4AI VOICE VOICE_PEDIATRIC
env $P python <branch>/scripts/offline_sizing.py sweep --root <tree> \
  --workdir <new dir C> --out kids_first.json --projects KIDS_FIRST
python <branch>/scripts/offline_sizing.py merge full.json rerun.json --out merged.json
python <branch>/scripts/offline_sizing.py merge merged.json kids_first.json --out final.json
python <branch>/scripts/offline_sizing.py table final.json
```

Today the full sweep also measures Kids First, because the committed script
knows its inputs. The separate Kids First sweep reproduces how these results
were made.

The appendix is the last command's output.

## Appendix: complete tables (generated)

Ceilings: worker 1,000,000; report family 850,000; every other request 1,000,000 (tokens in flight: input plus `max_tokens`).

#### AI_READI

Primary record `2026-09-04g_claude-opus-5-api-generic-v8_rep2`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict |
|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | refused | | | AuditBatchError: indivisible_field_bound |
| G2 | 192 / 32,768 / 16 | 6 | 3,836,702 | 1,503,814 | estimate_exceeds |
| G3 | 384 / 65,536 / 16 | 3 | 3,841,507 | 1,505,693 | estimate_exceeds |
| G4 | 192 / 32,768 / 8 | 6 | 3,836,700 | 1,503,814 | estimate_exceeds |
| G5 | 384 / 65,536 / 4 | 3 | 3,841,505 | 1,505,692 | estimate_exceeds |
| G6 | 768 / 131,072 / 2 | 2 | 3,851,036 | 1,509,418 | estimate_exceeds |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 3,836,702 | 0.3909 (A1b AI_READI typed_audit_worker) | 0 | 4,000 | 1,503,814 (1,503,814–1,577,967) | 1,000,000 | estimate_exceeds |
| full | 677,021 | 0.3408 (A1b AI_READI full) | 0 | 128,000 | 358,708 (358,708–372,660) | 1,000,000 | estimate_fits |
| full_readdress | 773,768 | 0.3406 (A1b AI_READI full_readdress) | 0 | 8,000 | 271,542 (271,542–286,701) | 1,000,000 | estimate_fits |
| full_receipt_completion | 2,466,273 | 0.3607 (A1b AI_READI full_receipt_completion) | 0 | 4,000 | 893,690 (893,690–917,210) | 1,000,000 | estimate_fits |
| reconcile_full | 2,048,663 | 0.3573 (A1b AI_READI reconcile_full) | 4,000 | 96,000 | 831,960 (831,960–860,015) | 1,000,000 | estimate_fits |
| repair_full | 165,675 | 0.3738 (A1b AI_READI repair_full) | 0 | 96,000 | 157,926 (157,926–163,065) | 1,000,000 | estimate_fits |
| report | 2,494,988 | 0.3545 (A1b AI_READI report) | 4,000 | 96,000 | 984,434 (984,434–1,019,405) | 850,000 | estimate_exceeds |
| report_regate | 2,493,161 | 0.3545 (A1b AI_READI report_regate) | 100,000 | 96,000 | 1,079,889 (1,079,889–1,115,046) | 850,000 | estimate_exceeds |
| report_regate_with_v8_report | 2,511,496 | 0.3545 (A1b AI_READI report_regate) | 4,000 | 96,000 | 990,389 (990,389–1,025,804) | 850,000 | estimate_exceeds |
| typed_audit_integration | 3,675,805 | 0.3909 (A1b AI_READI typed_audit_worker) | 28,000 | 4,000 | 1,468,918 (1,468,918–1,539,960) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 3,267,676 | 0.3705 (A1b AI_READI typed_audit_omission) | 0 | 4,000 | 1,214,717 (1,214,717–1,247,089) | 1,000,000 | estimate_exceeds |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04g_claude-opus-5-api-generic-v8_rep1` | 72,954 | 5 | 4 | 1,415,395 | 1,145,781 | 1,381,106 | 878,517 | 894,324 | 989,768 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep2` | 94,145 | 8 | 6 | 1,503,814 | 1,214,717 | 1,468,918 | 893,690 | 984,434 | 1,079,889 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep3` | 80,149 | 10 | 4 | 1,448,517 | 1,176,912 | 1,415,140 | 881,254 | 909,813 | 1,005,259 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (3,836,720 B): m0.6: # Exact typed stage request 2,435,486 (63%); inside: shared.schema 1,486,502 (39%); m0.3: # Shared generation: captured schema owners and complete containing va 1,351,652 (35%); schema context: classes 949,673 (25%); inside: shared.bundle 496,003 (13%); schema context: owners 401,167 (10%); schema context: nested_owners 203,349 (5%); schema context: owner_typed_tree 197,947 (5%); schema context: owner_yaml 183,437 (5%)
- **typed_audit_omission** (3,267,694 B): m0.6: # Exact typed stage request 1,866,488 (57%); m0.3: # Shared generation: captured schema owners and complete containing va 1,351,652 (41%); inside: payload.schema 1,246,504 (38%); schema context: classes 949,673 (29%); inside: payload.chunks 463,549 (14%); schema context: owners 401,167 (12%); schema context: nested_owners 203,349 (6%); schema context: owner_typed_tree 197,947 (6%); schema context: owner_yaml 183,437 (6%)
- **full_receipt_completion** (2,466,273 B): m2.0: {"input_sha256":{"bundle":"b4a282fd5c44bc93a3bcd71a4c3ee53b36a0de31d10 1,690,125 (69%); inside: json.schema 1,542,013 (63%); m0.1: # Declared input bundle — <path> 443,225 (18%); inside: json.record_yaml 97,505 (4%); m1.0: # D4D Datasheet for AI_READI Dataset 95,787 (4%); m0.5: ## API factual and phase policy v2 88,100 (4%); m0.6: # Shared generation: captured schema owners and complete containing va 76,978 (3%); schema context: classes 76,166 (3%); m0.0: # Target class `Dataset` — slot inventory 45,592 (2%)
- **report_regate** (2,493,161 B): m0.13: # Shared generation: captured schema owners and complete containing va 1,361,964 (55%); schema context: classes 936,972 (38%); m0.1: # Declared input bundle — <path> 443,225 (18%); schema context: owners 424,180 (17%); schema context: nested_owners 213,250 (9%); schema context: owner_typed_tree 209,695 (8%); schema context: owner_yaml 194,815 (8%); m0.12: # Required source-review inventory 164,691 (7%); m0.9: # Reconciled full record 102,602 (4%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 922,722 (fits) | 752,871 (fits) | 887,826 (fits) | 337,420 (fits) | 984,434 (exceeds) | 1,079,889 (exceeds) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 1,132,575 (exceeds) | 862,851 (fits) | 1,097,679 (exceeds) | 866,214 (fits) | 652,292 (fits) | 747,708 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 858,895 (fits) | 752,871 (fits) | 887,826 (fits) | 337,420 (fits) | 984,434 (exceeds) | 1,079,889 (exceeds) |
| S4: S1 plus owners without their typed trees | 845,342 (fits) | 679,529 (fits) | 810,446 (fits) | 337,420 (fits) | 910,101 (exceeds) | 1,005,547 (exceeds) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 1,209,793 (exceeds) | 936,039 (fits) | 1,174,897 (exceeds) | 877,757 (fits) | 721,671 (fits) | 817,095 (fits) |
| S6: S1 plus S5 | 628,701 (fits) | 474,193 (fits) | 593,804 (fits) | 321,487 (fits) | 721,671 (fits) | 817,095 (fits) |
| S7: S6 plus owners without their typed trees | 551,321 (fits) | 400,851 (fits) | 516,425 (fits) | 321,487 (fits) | 647,337 (fits) | 742,753 (fits) |

#### CHORUS

Primary record `2026-09-12_claude-opus-5-api-generic-v9_rep1`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict |
|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | 3 | 2,458,942 | 1,012,755 | estimate_exceeds |
| G2 | 192 / 32,768 / 16 | 2 | 2,461,858 | 1,013,951 | estimate_exceeds |
| G3 | 384 / 65,536 / 16 | 1 | 2,463,420 | 1,014,592 | estimate_exceeds |
| G4 | 192 / 32,768 / 8 | 2 | 2,461,856 | 1,013,951 | estimate_exceeds |
| G5 | 384 / 65,536 / 4 | 1 | 2,463,418 | 1,014,591 | estimate_exceeds |
| G6 | 768 / 131,072 / 2 | 1 | 2,463,420 | 1,014,592 | estimate_exceeds |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 2,461,858 | 0.4102 (A1b CHORUS typed_audit_worker) | 0 | 4,000 | 1,013,951 (966,371–1,013,951) | 1,000,000 | estimate_exceeds |
| full | 270,195 | 0.3614 (A1b CHORUS full) | 0 | 128,000 | 225,642 (220,074–225,642) | 1,000,000 | estimate_fits |
| full_readdress | 295,244 | 0.3602 (A1b CHORUS full_readdress) | 0 | 8,000 | 114,343 (108,559–114,343) | 1,000,000 | estimate_fits |
| full_receipt_completion | 1,881,604 | 0.3703 (A1b CHORUS full_receipt_completion) | 0 | 4,000 | 700,719 (682,775–700,719) | 1,000,000 | estimate_fits |
| reconcile_full | 936,155 | 0.371 (A1b CHORUS reconcile_full) | 4,000 | 96,000 | 447,296 (434,476–447,296) | 1,000,000 | estimate_fits |
| repair_full | 86,395 | 0.4048 (A1b CHORUS repair_full) | 0 | 96,000 | 130,973 (128,293–130,973) | 1,000,000 | estimate_fits |
| report | 979,362 | 0.3685 (A1b CHORUS report) | 4,000 | 96,000 | 460,895 (447,169–460,895) | 850,000 | estimate_fits |
| report_regate | 977,535 | 0.3686 (A1b CHORUS report_regate) | 100,000 | 96,000 | 556,346 (542,561–556,346) | 850,000 | estimate_fits |
| report_regate_with_v8_report | 992,548 | 0.3686 (A1b CHORUS report_regate) | 4,000 | 96,000 | 465,880 (451,883–465,880) | 850,000 | estimate_fits |
| typed_audit_integration | 2,419,417 | 0.4102 (A1b CHORUS typed_audit_worker) | 12,000 | 4,000 | 1,008,540 (961,780–1,008,540) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 2,110,164 | 0.3804 (A1b CHORUS typed_audit_omission) | 0 | 4,000 | 806,748 (785,844–806,748) | 1,000,000 | estimate_fits |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | 36,579 | 3 | 2 | 1,062,175 | 835,473 | 1,046,106 | 711,014 | 535,009 | 630,485 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep2` | 36,554 | 3 | 2 | 1,098,816 | 872,186 | 1,083,365 | 711,809 | 559,998 | 655,482 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep3` | 39,134 | 11 | 3 | 1,087,310 | 858,210 | 1,074,592 | 714,698 | 552,431 | 647,913 |
| `2026-09-12_claude-opus-5-api-generic-v9_rep1` | 23,643 | 6 | 2 | 1,013,951 | 806,748 | 1,008,540 | 700,719 | 460,895 | 556,346 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (2,461,876 B): m0.6: # Exact typed stage request 1,694,727 (69%); inside: shared.schema 1,486,502 (60%); m0.3: # Shared generation: captured schema owners and complete containing va 717,668 (29%); schema context: classes 615,443 (25%); schema context: owners 101,413 (4%); schema context: nested_owners 50,909 (2%); schema context: owner_typed_tree 48,920 (2%); inside: stage.inventory 45,817 (2%); inside: shared.bundle 42,716 (2%)
- **typed_audit_omission** (2,110,182 B): m0.6: # Exact typed stage request 1,343,061 (64%); inside: payload.schema 1,246,504 (59%); m0.3: # Shared generation: captured schema owners and complete containing va 717,668 (34%); schema context: classes 615,443 (29%); schema context: owners 101,413 (5%); schema context: nested_owners 50,909 (2%); schema context: owner_typed_tree 48,920 (2%); schema context: owner_yaml 42,295 (2%); inside: payload.chunks 40,404 (2%)
- **full_receipt_completion** (1,881,604 B): m2.0: {"input_sha256":{"bundle":"27625709112a7b7796f4e778fcc33df9f908ba95e47 1,583,980 (84%); inside: json.schema 1,542,013 (82%); m0.5: ## API factual and phase policy v2 86,816 (5%); m0.6: # Shared generation: captured schema owners and complete containing va 76,978 (4%); schema context: classes 76,166 (4%); m0.0: # Target class `Dataset` — slot inventory 45,592 (2%); m0.1: # Declared input bundle — <path> 38,088 (2%); inside: json.record_yaml 24,539 (1%); m1.0: # D4D Datasheet for CHORUS Dataset 24,089 (1%)
- **report_regate** (977,535 B): m0.13: # Shared generation: captured schema owners and complete containing va 656,834 (67%); schema context: classes 562,536 (58%); schema context: owners 93,486 (10%); m0.5: ## API factual and phase policy v2 79,809 (8%); m0.0: # Target class `Dataset` — slot inventory 45,592 (5%); schema context: owner_typed_tree 45,244 (5%); schema context: nested_owners 44,952 (5%); m0.12: # Required source-review inventory 39,892 (4%); schema context: owner_yaml 39,644 (4%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 404,130 (fits) | 332,553 (fits) | 398,719 (fits) | 129,744 (fits) | 460,895 (fits) | 556,346 (fits) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 761,472 (fits) | 572,622 (fits) | 756,061 (fits) | 672,517 (fits) | 253,601 (fits) | 348,980 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 385,334 (fits) | 332,553 (fits) | 398,719 (fits) | 129,744 (fits) | 460,895 (fits) | 556,346 (fits) |
| S4: S1 plus owners without their typed trees | 384,061 (fits) | 313,943 (fits) | 378,650 (fits) | 129,744 (fits) | 444,223 (fits) | 539,667 (fits) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 817,143 (fits) | 624,246 (fits) | 811,732 (fits) | 684,365 (fits) | 300,682 (fits) | 396,077 (fits) |
| S6: S1 plus S5 | 207,321 (fits) | 150,051 (fits) | 201,910 (fits) | 113,389 (fits) | 300,682 (fits) | 396,077 (fits) |
| S7: S6 plus owners without their typed trees | 187,252 (fits) | 131,441 (fits) | 181,841 (fits) | 113,389 (fits) | 284,009 (fits) | 379,399 (fits) |

#### CM4AI

Primary record `2026-09-04g_claude-opus-5-api-generic-v8_rep1`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict |
|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | refused | | | AuditBatchError: indivisible_field_bound |
| G2 | 192 / 32,768 / 16 | 3 | 3,024,832 | 1,244,905 | estimate_exceeds |
| G3 | 384 / 65,536 / 16 | 2 | 3,032,185 | 1,247,922 | estimate_exceeds |
| G4 | 192 / 32,768 / 8 | 3 | 3,024,830 | 1,244,905 | estimate_exceeds |
| G5 | 384 / 65,536 / 4 | 2 | 3,032,183 | 1,247,921 | estimate_exceeds |
| G6 | 768 / 131,072 / 2 | 1 | 3,035,642 | 1,249,340 | estimate_exceeds |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 3,024,832 | 0.4102 (no A1b count for CM4AI: higher of CHORUS/AI_READI typed_audit_worker) | 0 | 4,000 | 1,244,905 (1,186,444–1,244,905) | 1,000,000 | estimate_exceeds |
| full | 563,514 | 0.3614 (no A1b count for CM4AI: higher of CHORUS/AI_READI full) | 0 | 128,000 | 331,641 (320,028–331,641) | 1,000,000 | estimate_fits |
| full_readdress | 606,649 | 0.3602 (no A1b count for CM4AI: higher of CHORUS/AI_READI full_readdress) | 0 | 8,000 | 226,507 (214,622–226,507) | 1,000,000 | estimate_fits |
| full_receipt_completion | 2,228,756 | 0.3703 (no A1b count for CM4AI: higher of CHORUS/AI_READI full_receipt_completion) | 0 | 4,000 | 829,263 (808,008–829,263) | 1,000,000 | estimate_fits |
| reconcile_full | 1,382,204 | 0.371 (no A1b count for CM4AI: higher of CHORUS/AI_READI reconcile_full) | 4,000 | 96,000 | 612,772 (593,843–612,772) | 1,000,000 | estimate_fits |
| repair_full | 106,453 | 0.4048 (no A1b count for CM4AI: higher of CHORUS/AI_READI repair_full) | 0 | 96,000 | 139,092 (135,790–139,092) | 1,000,000 | estimate_fits |
| report | 1,603,584 | 0.3685 (no A1b count for CM4AI: higher of CHORUS/AI_READI report) | 4,000 | 96,000 | 690,922 (668,445–690,922) | 850,000 | estimate_fits |
| report_regate | 1,601,757 | 0.3686 (no A1b count for CM4AI: higher of CHORUS/AI_READI report_regate) | 100,000 | 96,000 | 786,450 (763,863–786,450) | 850,000 | estimate_fits |
| report_regate_with_v8_report | 1,612,471 | 0.3686 (no A1b count for CM4AI: higher of CHORUS/AI_READI report_regate) | 4,000 | 96,000 | 694,400 (671,662–694,400) | 850,000 | estimate_fits |
| typed_audit_integration | 2,928,363 | 0.4102 (no A1b count for CM4AI: higher of CHORUS/AI_READI typed_audit_worker) | 16,000 | 4,000 | 1,221,330 (1,164,733–1,221,330) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 2,582,757 | 0.3804 (no A1b count for CM4AI: higher of CHORUS/AI_READI typed_audit_omission) | 0 | 4,000 | 986,532 (960,946–986,532) | 1,000,000 | estimate_fits |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04g_claude-opus-5-api-generic-v8_rep1` | 41,203 | 2 | 3 | 1,244,905 | 986,532 | 1,221,330 | 829,263 | 690,922 | 786,450 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep2` | 39,830 | 11 | 3 | 1,276,242 | 1,014,934 | 1,250,360 | 827,926 | 707,447 | 802,982 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep3` | 44,850 | 9 | 3 | 1,276,340 | 1,013,549 | 1,250,048 | 834,195 | 703,962 | 799,495 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (3,024,850 B): m0.6: # Exact typed stage request 2,122,987 (70%); inside: shared.schema 1,486,502 (49%); m0.3: # Shared generation: captured schema owners and complete containing va 852,312 (28%); schema context: classes 644,761 (21%); inside: shared.bundle 354,248 (12%); schema context: owners 206,739 (7%); schema context: nested_owners 114,564 (4%); schema context: owner_typed_tree 102,029 (3%); inside: stage.inventory 98,721 (3%)
- **typed_audit_omission** (2,582,775 B): m0.6: # Exact typed stage request 1,680,940 (65%); inside: payload.schema 1,246,504 (48%); m0.3: # Shared generation: captured schema owners and complete containing va 852,312 (33%); schema context: classes 644,761 (25%); inside: payload.chunks 341,147 (13%); schema context: owners 206,739 (8%); schema context: nested_owners 114,564 (4%); schema context: owner_typed_tree 102,029 (4%); schema context: owner_yaml 82,010 (3%)
- **full_receipt_completion** (2,228,756 B): m2.0: {"input_sha256":{"bundle":"5f81bb53f43f9ec6debc3ab7297bb3897d30c675888 1,619,727 (73%); inside: json.schema 1,542,013 (69%); m0.1: # Declared input bundle — <path> 329,577 (15%); m0.5: ## API factual and phase policy v2 88,133 (4%); m0.6: # Shared generation: captured schema owners and complete containing va 76,978 (3%); schema context: classes 76,166 (3%); m0.0: # Target class `Dataset` — slot inventory 45,592 (2%); inside: json.record_yaml 43,181 (2%); m1.0: # D4D Datasheet for CM4AI Dataset 42,175 (2%)
- **report_regate** (1,601,757 B): m0.13: # Shared generation: captured schema owners and complete containing va 856,373 (53%); schema context: classes 644,761 (40%); m0.1: # Declared input bundle — <path> 329,577 (21%); schema context: owners 210,800 (13%); schema context: nested_owners 116,544 (7%); schema context: owner_typed_tree 104,041 (6%); m0.12: # Required source-review inventory 92,682 (6%); schema context: owner_yaml 83,913 (5%); m0.5: ## API factual and phase policy v2 81,126 (5%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 635,084 (fits) | 512,337 (fits) | 611,508 (fits) | 258,287 (fits) | 690,922 (fits) | 786,450 (fits) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 980,399 (fits) | 741,252 (fits) | 956,824 (fits) | 801,060 (fits) | 453,327 (fits) | 548,774 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 594,584 (fits) | 512,337 (fits) | 611,508 (fits) | 258,287 (fits) | 690,922 (fits) | 786,450 (fits) |
| S4: S1 plus owners without their typed trees | 593,227 (fits) | 473,523 (fits) | 569,652 (fits) | 258,287 (fits) | 652,582 (fits) | 748,098 (fits) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 1,033,032 (exceeds) | 790,059 (fits) | 1,009,457 (exceeds) | 812,908 (fits) | 500,605 (fits) | 596,068 (fits) |
| S6: S1 plus S5 | 423,210 (fits) | 315,864 (fits) | 399,635 (fits) | 241,932 (fits) | 500,605 (fits) | 596,068 (fits) |
| S7: S6 plus owners without their typed trees | 381,354 (fits) | 277,051 (fits) | 357,778 (fits) | 241,932 (fits) | 462,266 (fits) | 557,716 (fits) |

#### KIDS_FIRST

Proxy: AI_READI's records with KIDS_FIRST's own bundle and chunk manifest, a root-only draft context synthesized by the A3 builder, and a minimal receipt; an estimate for a run that has no record yet.

Primary record `2026-09-04g_claude-opus-5-api-generic-v8_rep2`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict |
|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | refused | | | AuditBatchError: indivisible_field_bound |
| G2 | 192 / 32,768 / 16 | 6 | 3,888,459 | 1,599,199 | estimate_exceeds |
| G3 | 384 / 65,536 / 16 | 3 | 3,893,264 | 1,601,171 | estimate_exceeds |
| G4 | 192 / 32,768 / 8 | 6 | 3,888,457 | 1,599,199 | estimate_exceeds |
| G5 | 384 / 65,536 / 4 | 3 | 3,893,262 | 1,601,170 | estimate_exceeds |
| G6 | 768 / 131,072 / 2 | 2 | 3,902,793 | 1,605,080 | estimate_exceeds |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 3,888,459 | 0.4102 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI typed_audit_worker) | 0 | 4,000 | 1,599,199 (1,524,047–1,599,199) | 1,000,000 | estimate_exceeds |
| full | 783,623 | 0.3614 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI full) | 0 | 128,000 | 411,184 (395,035–411,184) | 1,000,000 | estimate_fits |
| full_readdress | 880,370 | 0.3602 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI full_readdress) | 0 | 8,000 | 325,098 (307,851–325,098) | 1,000,000 | estimate_fits |
| full_receipt_completion | 2,546,952 | 0.3703 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI full_receipt_completion) | 0 | 4,000 | 947,084 (922,794–947,084) | 1,000,000 | estimate_fits |
| reconcile_full | 2,155,265 | 0.371 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI reconcile_full) | 4,000 | 96,000 | 899,562 (870,048–899,562) | 1,000,000 | estimate_fits |
| repair_full | 155,015 | 0.4048 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI repair_full) | 0 | 96,000 | 158,750 (153,941–158,750) | 1,000,000 | estimate_fits |
| report | 2,601,590 | 0.3685 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI report) | 4,000 | 96,000 | 1,058,687 (1,022,223–1,058,687) | 850,000 | estimate_exceeds |
| report_regate | 2,599,763 | 0.3686 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI report_regate) | 100,000 | 96,000 | 1,154,342 (1,117,682–1,154,342) | 850,000 | estimate_exceeds |
| report_regate_with_v8_report | 2,618,098 | 0.3686 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI report_regate) | 4,000 | 96,000 | 1,065,101 (1,028,182–1,065,101) | 850,000 | estimate_exceeds |
| typed_audit_integration | 3,727,562 | 0.4102 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI typed_audit_worker) | 28,000 | 4,000 | 1,561,193 (1,489,150–1,561,193) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 3,327,495 | 0.3804 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI typed_audit_omission) | 0 | 4,000 | 1,269,845 (1,236,881–1,269,845) | 1,000,000 | estimate_exceeds |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04g_claude-opus-5-api-generic-v8_rep1` | 72,954 | 5 | 4 | 1,503,476 | 1,197,619 | 1,466,503 | 931,734 | 965,014 | 1,060,636 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep2` | 94,145 | 8 | 6 | 1,599,199 | 1,269,845 | 1,561,193 | 947,084 | 1,058,687 | 1,154,342 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep3` | 80,149 | 10 | 4 | 1,542,195 | 1,231,978 | 1,506,180 | 936,360 | 981,115 | 1,076,744 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (3,888,459 B): m0.6: # Exact typed stage request 2,496,031 (64%); inside: shared.schema 1,486,502 (38%); m0.3: # Shared generation: captured schema owners and complete containing va 1,351,652 (35%); schema context: classes 949,673 (24%); inside: shared.bundle 574,250 (15%); schema context: owners 401,167 (10%); schema context: nested_owners 203,349 (5%); schema context: owner_typed_tree 197,947 (5%); schema context: owner_yaml 183,437 (5%)
- **typed_audit_omission** (3,327,495 B): m0.6: # Exact typed stage request 1,935,095 (58%); m0.3: # Shared generation: captured schema owners and complete containing va 1,351,652 (41%); inside: payload.schema 1,246,504 (37%); schema context: classes 949,673 (29%); inside: payload.chunks 563,582 (17%); schema context: owners 401,167 (12%); schema context: nested_owners 203,349 (6%); schema context: owner_typed_tree 197,947 (6%); schema context: owner_yaml 183,437 (6%)
- **full_receipt_completion** (2,546,952 B): m2.0: {"input_sha256":{"bundle":"cc45c89548158a7a909699fbf1f75e6cc88c32ac848 1,664,202 (65%); inside: json.schema 1,542,013 (61%); m0.1: # Declared input bundle — <path> 549,154 (22%); inside: json.record_yaml 97,505 (4%); m0.5: ## API factual and phase policy v2 97,239 (4%); m1.0: # D4D Datasheet for AI_READI Dataset 95,787 (4%); m0.6: # Shared generation: captured schema owners and complete containing va 76,978 (3%); schema context: classes 76,166 (3%); m0.0: # Target class `Dataset` — slot inventory 42,964 (2%)
- **report_regate** (2,599,763 B): m0.13: # Shared generation: captured schema owners and complete containing va 1,361,964 (52%); schema context: classes 936,972 (36%); m0.1: # Declared input bundle — <path> 549,154 (21%); schema context: owners 424,180 (16%); schema context: nested_owners 213,250 (8%); schema context: owner_typed_tree 209,695 (8%); schema context: owner_yaml 194,815 (7%); m0.12: # Required source-review inventory 164,691 (6%); m0.9: # Reconciled full record 102,602 (4%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 989,378 (fits) | 795,650 (fits) | 951,371 (fits) | 376,108 (fits) | 1,058,687 (exceeds) | 1,154,342 (exceeds) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 1,209,606 (exceeds) | 908,571 (fits) | 1,171,600 (exceeds) | 918,881 (fits) | 713,413 (fits) | 808,949 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 922,394 (fits) | 795,650 (fits) | 951,371 (fits) | 376,108 (fits) | 1,058,687 (exceeds) | 1,154,342 (exceeds) |
| S4: S1 plus owners without their typed trees | 908,172 (fits) | 720,347 (fits) | 870,166 (fits) | 376,108 (fits) | 981,415 (exceeds) | 1,077,043 (exceeds) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 1,290,641 (exceeds) | 983,716 (fits) | 1,252,635 (exceeds) | 930,729 (fits) | 785,535 (fits) | 881,096 (exceeds) |
| S6: S1 plus S5 | 680,820 (fits) | 509,521 (fits) | 642,813 (fits) | 359,754 (fits) | 785,535 (fits) | 881,096 (exceeds) |
| S7: S6 plus owners without their typed trees | 599,614 (fits) | 434,218 (fits) | 561,608 (fits) | 359,754 (fits) | 708,262 (fits) | 803,796 (fits) |

#### VOICE

Primary record `2026-09-04f_claude-opus-5-api-generic-v8_rep1`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict |
|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | 8 | 3,514,861 | 1,445,935 | estimate_exceeds |
| G2 | 192 / 32,768 / 16 | 4 | 3,517,835 | 1,447,155 | estimate_exceeds |
| G3 | 384 / 65,536 / 16 | 2 | 3,523,930 | 1,449,655 | estimate_exceeds |
| G4 | 192 / 32,768 / 8 | 4 | 3,517,833 | 1,447,154 | estimate_exceeds |
| G5 | 384 / 65,536 / 4 | 2 | 3,523,928 | 1,449,654 | estimate_exceeds |
| G6 | 768 / 131,072 / 2 | 1 | 3,531,143 | 1,452,614 | estimate_exceeds |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 3,517,835 | 0.4102 (no A1b count for VOICE: higher of CHORUS/AI_READI typed_audit_worker) | 0 | 4,000 | 1,447,155 (1,379,165–1,447,155) | 1,000,000 | estimate_exceeds |
| full | 617,826 | 0.3614 (no A1b count for VOICE: higher of CHORUS/AI_READI full) | 0 | 128,000 | 351,268 (338,536–351,268) | 1,000,000 | estimate_fits |
| full_readdress | 682,346 | 0.3602 (no A1b count for VOICE: higher of CHORUS/AI_READI full_readdress) | 0 | 8,000 | 253,772 (240,404–253,772) | 1,000,000 | estimate_fits |
| full_receipt_completion | 2,339,635 | 0.3703 (no A1b count for VOICE: higher of CHORUS/AI_READI full_receipt_completion) | 0 | 4,000 | 870,319 (848,006–870,319) | 1,000,000 | estimate_fits |
| reconcile_full | 1,838,393 | 0.371 (no A1b count for VOICE: higher of CHORUS/AI_READI reconcile_full) | 4,000 | 96,000 | 782,009 (756,833–782,009) | 1,000,000 | estimate_fits |
| repair_full | 129,264 | 0.4048 (no A1b count for VOICE: higher of CHORUS/AI_READI repair_full) | 0 | 96,000 | 148,326 (144,316–148,326) | 1,000,000 | estimate_fits |
| report | 2,149,421 | 0.3685 (no A1b count for VOICE: higher of CHORUS/AI_READI report) | 4,000 | 96,000 | 892,063 (861,936–892,063) | 850,000 | estimate_exceeds |
| report_regate | 2,147,594 | 0.3686 (no A1b count for VOICE: higher of CHORUS/AI_READI report_regate) | 100,000 | 96,000 | 987,660 (957,376–987,660) | 850,000 | estimate_exceeds |
| report_regate_with_v8_report | 2,163,379 | 0.3686 (no A1b count for VOICE: higher of CHORUS/AI_READI report_regate) | 4,000 | 96,000 | 897,479 (866,973–897,479) | 850,000 | estimate_exceeds |
| typed_audit_integration | 3,406,002 | 0.4102 (no A1b count for VOICE: higher of CHORUS/AI_READI typed_audit_worker) | 20,000 | 4,000 | 1,421,276 (1,355,448–1,421,276) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 3,046,739 | 0.3804 (no A1b count for VOICE: higher of CHORUS/AI_READI typed_audit_omission) | 0 | 4,000 | 1,163,040 (1,132,857–1,163,040) | 1,000,000 | estimate_exceeds |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | 62,329 | 10 | 4 | 1,447,155 | 1,163,040 | 1,421,276 | 870,319 | 892,063 | 987,660 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep2` | 67,431 | 9 | 4 | 1,430,528 | 1,147,770 | 1,407,728 | 873,532 | 859,316 | 954,903 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep3` | 75,633 | 8 | 4 | 1,513,288 | 1,214,932 | 1,480,307 | 878,764 | 944,580 | 1,040,196 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (3,517,853 B): m0.6: # Exact typed stage request 2,235,436 (64%); inside: shared.schema 1,486,502 (42%); m0.3: # Shared generation: captured schema owners and complete containing va 1,232,804 (35%); schema context: classes 949,641 (27%); inside: shared.bundle 400,770 (11%); schema context: owners 282,351 (8%); schema context: nested_owners 149,957 (4%); schema context: owner_typed_tree 138,712 (4%); schema context: owner_yaml 124,041 (4%)
- **typed_audit_omission** (3,046,757 B): m0.6: # Exact typed stage request 1,764,368 (58%); inside: payload.schema 1,246,504 (41%); m0.3: # Shared generation: captured schema owners and complete containing va 1,232,804 (40%); schema context: classes 949,641 (31%); inside: payload.chunks 391,486 (13%); schema context: owners 282,351 (9%); schema context: nested_owners 149,957 (5%); schema context: owner_typed_tree 138,712 (5%); schema context: owner_yaml 124,041 (4%)
- **full_receipt_completion** (2,339,635 B): m2.0: {"input_sha256":{"bundle":"7c4f71ab2e85d70396e479d39cb5db9454bd9f13c72 1,654,909 (71%); inside: json.schema 1,542,013 (66%); m0.1: # Declared input bundle — <path> 383,053 (16%); m0.5: ## API factual and phase policy v2 88,276 (4%); m0.6: # Shared generation: captured schema owners and complete containing va 76,978 (3%); schema context: classes 76,166 (3%); inside: json.record_yaml 64,857 (3%); m1.0: # D4D Datasheet for VOICE Dataset 63,560 (3%); m0.0: # Target class `Dataset` — slot inventory 45,592 (2%)
- **report_regate** (2,147,594 B): m0.13: # Shared generation: captured schema owners and complete containing va 1,251,114 (58%); schema context: classes 961,830 (45%); m0.1: # Declared input bundle — <path> 383,053 (18%); schema context: owners 288,472 (13%); schema context: nested_owners 151,567 (7%); schema context: owner_typed_tree 141,684 (7%); schema context: owner_yaml 127,709 (6%); m0.12: # Required source-review inventory 110,667 (5%); m0.5: ## API factual and phase policy v2 81,269 (4%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 837,333 (fits) | 688,845 (fits) | 811,455 (fits) | 299,343 (fits) | 892,063 (exceeds) | 987,660 (exceeds) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 1,057,575 (exceeds) | 801,778 (fits) | 1,031,696 (exceeds) | 842,116 (fits) | 537,628 (fits) | 633,104 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 790,119 (fits) | 688,845 (fits) | 811,455 (fits) | 299,343 (fits) | 892,063 (exceeds) | 987,660 (exceeds) |
| S4: S1 plus owners without their typed trees | 780,428 (fits) | 636,076 (fits) | 754,550 (fits) | 299,343 (fits) | 839,852 (fits) | 935,432 (exceeds) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 1,130,404 (exceeds) | 869,313 (fits) | 1,104,526 (exceeds) | 853,964 (fits) | 603,648 (fits) | 699,147 (fits) |
| S6: S1 plus S5 | 520,582 (fits) | 395,118 (fits) | 494,704 (fits) | 282,989 (fits) | 603,648 (fits) | 699,147 (fits) |
| S7: S6 plus owners without their typed trees | 463,677 (fits) | 342,350 (fits) | 437,799 (fits) | 282,989 (fits) | 551,437 (fits) | 646,918 (fits) |

#### VOICE_PEDIATRIC

Proxy: VOICE's records with VOICE_PEDIATRIC's own bundle and chunk manifest, its own context, and a minimal receipt; an estimate for a run that has no record yet.

Primary record `2026-09-04f_claude-opus-5-api-generic-v8_rep1`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict |
|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | 8 | 3,286,831 | 1,352,388 | estimate_exceeds |
| G2 | 192 / 32,768 / 16 | 4 | 3,289,805 | 1,353,608 | estimate_exceeds |
| G3 | 384 / 65,536 / 16 | 2 | 3,295,900 | 1,356,108 | estimate_exceeds |
| G4 | 192 / 32,768 / 8 | 4 | 3,289,803 | 1,353,607 | estimate_exceeds |
| G5 | 384 / 65,536 / 4 | 2 | 3,295,898 | 1,356,107 | estimate_exceeds |
| G6 | 768 / 131,072 / 2 | 1 | 3,303,113 | 1,359,067 | estimate_exceeds |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 3,289,805 | 0.4102 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI typed_audit_worker) | 0 | 4,000 | 1,353,608 (1,290,026–1,353,608) | 1,000,000 | estimate_exceeds |
| full | 442,248 | 0.3614 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI full) | 0 | 128,000 | 287,818 (278,705–287,818) | 1,000,000 | estimate_fits |
| full_readdress | 506,768 | 0.3602 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI full_readdress) | 0 | 8,000 | 190,531 (180,603–190,531) | 1,000,000 | estimate_fits |
| full_receipt_completion | 2,133,410 | 0.3703 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI full_receipt_completion) | 0 | 4,000 | 793,958 (773,612–793,958) | 1,000,000 | estimate_fits |
| reconcile_full | 1,662,815 | 0.371 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI reconcile_full) | 4,000 | 96,000 | 716,873 (694,102–716,873) | 1,000,000 | estimate_fits |
| repair_full | 129,128 | 0.4048 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI repair_full) | 0 | 96,000 | 148,271 (144,265–148,271) | 1,000,000 | estimate_fits |
| report | 1,973,843 | 0.3685 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI report) | 4,000 | 96,000 | 827,362 (799,696–827,362) | 850,000 | estimate_fits |
| report_regate | 1,972,016 | 0.3686 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI report_regate) | 100,000 | 96,000 | 922,938 (895,130–922,938) | 850,000 | estimate_exceeds |
| report_regate_with_v8_report | 1,987,801 | 0.3686 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI report_regate) | 4,000 | 96,000 | 832,757 (804,726–832,757) | 850,000 | estimate_fits |
| typed_audit_integration | 3,177,972 | 0.4102 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI typed_audit_worker) | 20,000 | 4,000 | 1,327,730 (1,266,309–1,327,730) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 2,829,955 | 0.3804 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI typed_audit_omission) | 0 | 4,000 | 1,080,571 (1,052,536–1,080,571) | 1,000,000 | estimate_exceeds |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | 62,329 | 10 | 4 | 1,353,608 | 1,080,571 | 1,327,730 | 793,958 | 827,362 | 922,938 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep2` | 67,431 | 9 | 4 | 1,337,456 | 1,065,716 | 1,314,656 | 796,384 | 794,616 | 890,180 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep3` | 75,633 | 8 | 4 | 1,422,915 | 1,134,592 | 1,389,933 | 804,376 | 879,880 | 975,473 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (3,289,823 B): m0.6: # Exact typed stage request 2,007,292 (61%); inside: shared.schema 1,486,502 (45%); m0.3: # Shared generation: captured schema owners and complete containing va 1,232,804 (37%); schema context: classes 949,641 (29%); schema context: owners 282,351 (9%); inside: shared.bundle 218,527 (7%); schema context: nested_owners 149,957 (5%); schema context: owner_typed_tree 138,712 (4%); schema context: owner_yaml 124,041 (4%)
- **typed_audit_omission** (2,829,973 B): m0.6: # Exact typed stage request 1,547,470 (55%); inside: payload.schema 1,246,504 (44%); m0.3: # Shared generation: captured schema owners and complete containing va 1,232,804 (44%); schema context: classes 949,641 (34%); schema context: owners 282,351 (10%); inside: payload.chunks 214,030 (8%); schema context: nested_owners 149,957 (5%); schema context: owner_typed_tree 138,712 (5%); schema context: owner_yaml 124,041 (4%)
- **full_receipt_completion** (2,133,410 B): m2.0: {"input_sha256":{"bundle":"eb823708a16342a3b12cc1dabb57529cea4f95fd596 1,624,262 (76%); inside: json.schema 1,542,013 (72%); m0.1: # Declared input bundle — <path> 209,634 (10%); m0.4: ## API factual and phase policy v2 87,245 (4%); m0.5: # Shared generation: captured schema owners and complete containing va 76,978 (4%); schema context: classes 76,166 (4%); inside: json.record_yaml 64,857 (3%); m1.0: # D4D Datasheet for VOICE Dataset 63,560 (3%); m0.0: # Target class `Dataset` — slot inventory 45,592 (2%)
- **report_regate** (1,972,016 B): m0.12: # Shared generation: captured schema owners and complete containing va 1,251,114 (63%); schema context: classes 961,830 (49%); schema context: owners 288,472 (15%); m0.1: # Declared input bundle — <path> 209,634 (11%); schema context: nested_owners 151,567 (8%); schema context: owner_typed_tree 141,684 (7%); schema context: owner_yaml 127,709 (6%); m0.11: # Required source-review inventory 110,667 (6%); m0.4: ## API factual and phase policy v2 80,238 (4%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 743,786 (fits) | 606,376 (fits) | 717,908 (fits) | 222,982 (fits) | 827,362 (fits) | 922,938 (exceeds) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 964,028 (fits) | 719,309 (fits) | 938,149 (fits) | 765,755 (fits) | 472,927 (fits) | 568,382 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 696,572 (fits) | 606,376 (fits) | 717,908 (fits) | 222,982 (fits) | 827,362 (fits) | 922,938 (exceeds) |
| S4: S1 plus owners without their typed trees | 686,881 (fits) | 553,607 (fits) | 661,003 (fits) | 222,982 (fits) | 775,152 (fits) | 870,709 (exceeds) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 1,036,857 (exceeds) | 786,844 (fits) | 1,010,979 (exceeds) | 777,603 (fits) | 538,947 (fits) | 634,424 (fits) |
| S6: S1 plus S5 | 427,035 (fits) | 312,649 (fits) | 401,157 (fits) | 206,628 (fits) | 538,947 (fits) | 634,424 (fits) |
| S7: S6 plus owners without their typed trees | 370,130 (fits) | 259,881 (fits) | 344,252 (fits) | 206,628 (fits) | 486,737 (fits) | 582,195 (fits) |

