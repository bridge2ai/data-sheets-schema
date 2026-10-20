# Step A1 offline sizing for generic_v10 API requests (2026-10-20)

Issues: #5072, #4829, #4830. Plan: `notes/d4d_generation_plan_2026-10-09.md`,
step A1, with A1b, A6, D07, risk 6 and open question 6. Branch
`fix/5072-offline-sizing-recovery` (PR #5087).

No provider was contacted, billed or unbilled: sockets were blocked, and the
sweep recorded no connection attempt. Every token figure below is an
**estimate from bytes, not a count**. None of them can clear a request; only
the unbilled A1b `messages.count_tokens` count can, read through
`offline_sizing check` (see "What this does not establish").

This revision replaces the note's first version (`64082b98d`, `e6d46f3a3`).
Its recommendation was wrong, and so were three of its claims; "Corrections"
lists what changed.

## Answer

Four results, in the order a run would meet them.

**1. No partition makes a typed-audit worker's input fit**, for any of the six
projects, under the current protocol.
- **CHORUS.** A1b counted its largest worker at 1,009,249 input tokens, on the
  same record at the same grid (2,460,146 B then, 2,461,837 B now). That is
  over the 1,000,000-token window before the 4,000-token output cap is added.
- **The other five** are an estimated 24–60% over.
- **Partitioning** changes how many workers there are, not how large each one
  is. On each project's primary record the largest worker moved by at most
  0.5% across the valid grids.

**2. No worker's answer fits its output cap, at any grid.**
- **The cap.** The registered `worker_output_tokens` is 4,000, and thinking
  draws on the same `max_tokens`.
- **The smallest answer.** The runtime's own worker check accepts nothing
  smaller than one row per assigned path, each claim quoting its value. With
  every other string one character long, that is already at least:
  - 10,949–11,861 tokens for the largest worker at G2 (4 bytes a token), 2.7–3.0
    times the cap;
  - 13,827–24,456 tokens at G5.
- **What happens.** A response cut off at `max_tokens` does not end with
  `end_turn`. The runtime refuses it ("typed response did not finish normally;
  allowance remains consumed"). The typed audit is then terminal, after full,
  receipt completion and the first worker have been billed.
- **No option helps.** This is output, not input, so no compaction option
  changes it.

**3. Under S7, the report family still exceeds for Kids First.** S7 is the
compaction option that came closest. A completed audit carries every row, so
the audit the report family carries is at least the workers' smallest answers
assembled.
- **With that audit:**
  - Kids First's regate is 880,265, 3.6% over 850,000 (853,936 at the lower
    calibrated ratio);
  - AI_READI's is 816,145, 4.0% under.
- **Every other request** fits on every project under S7.
- **The partition** hardly changes the carry, so no grid fixes this.

**4. The typed input aggregate rules out G2 under S7.** The registered
`aggregate_input_tokens` is 4,000,000.
- At G2, AI_READI needs 4.24M and Kids First 4.61M.
- With three workers (G3, G5), they need 2.60M and 2.83M.

**Why the inputs are so large.** The schema is carried twice in every typed
request.
1. **The typed request's own catalog.** It covers every class reachable from
   `Dataset`, with every induced slot's full LinkML definition
   (`audit_omissions._schema`), whatever the record holds. Its size is the same
   in all six projects:
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
- the worker's own assignment, 0.2–0.3%, the only part partitioning controls.

This answers the plan's open question 6 and confirms risk 6.

## Recommended configuration

**Nothing launches as registered.** Under the current protocol, every worker's
input (result 1) and output (result 2) fail at every partition. What follows
depends on decisions that belong to others:
- the owner: S7 and a report-family change;
- A6: the output limits.

**The compaction options.** Seven were measured by removing parts from the
actual requests: exact for bytes, estimated for tokens. The table shows the
primary records at G2, with the audit at its floor; the complete tables are in
the appendix. None of the options touches result 2, the output cap.

| Option | What changes | What still exceeds |
|---|---|---|
| S1 | typed requests stop carrying their own schema catalog; the schema context stays | the report family for AI_READI, VOICE, VOICE_PEDIATRIC and Kids First; Kids First's integration (1,007,605) |
| S2 | the schema context's induced-slot `classes` dropped; the typed catalog stays | workers and integration for AI_READI, VOICE and Kids First; Kids First's regate (885,418) |
| S3 | S1 plus the full-record inventory dropped from each worker | as S1 |
| S4 | S1 plus owners without their typed trees | the report family for AI_READI, VOICE and Kids First; VOICE_PEDIATRIC's regate |
| S5 | induced-slot definitions trimmed to name, description, range, cardinality and inlining | workers and integration for every project but CHORUS; AI_READI's regate; Kids First's report and regate |
| S6 | S1 plus S5 | AI_READI's regate (890,487); Kids First's report (861,976) and regate (957,564) |
| **S7** | **S6 plus owners without their typed trees** | **Kids First's regate (880,265)** |

**Partition: G5** (`max_paths` 384, `max_inventory_bytes` 65,536, `max_workers`
4), if S7 or S6 is adopted. Under either, the report family still needs the
change described below. Under S6 it exceeds for AI_READI as well.
- **Valid everywhere.** It is valid for every project, with 1–3 workers. G1,
  `typed_audit.prepare`'s default, is refused for AI_READI, CM4AI and Kids
  First with `indivisible_field_bound`.
- **Inside the aggregate.** It stays inside the registered typed input
  aggregate: at most 2.83M under S7 and 3.23M under S6 (Kids First in both).
  G2 does not, for AI_READI and Kids First.
- **A cheaper failure.** `max_workers` 4 makes the planner
  (`prepare_packet`) refuse a record that would need more workers before any
  typed stage is billed. Without it, the runtime refuses the first typed stage
  that would pass the aggregate, after the earlier workers are billed. G3
  gives the same partitions on these records without that guard.
- **Headroom.** AI_READI's record uses 554 of G5's nominal 1,536 paths and
  142,895 of its 262,144 inventory bytes. Workers are packed by whole
  top-level field, so the usable capacity is somewhat less.
- **The cost is longer answers.** The largest worker's smallest answer is at
  least:
  - 22,481 tokens for AI_READI and Kids First;
  - 24,456 tokens for CM4AI;
  - against 11,464–11,861 tokens at G2.
- **The window does not limit the cap.** Under S7, the largest worker request
  at G5 is 601,570 tokens in flight with the 4,000 cap. A 128,000 cap, the
  full phase's, would give 725,570. The output limits, not the window, set the
  worker cap.

**The alternative is G2.** It needs A6 to raise `aggregate_input_tokens` to at
least 4.61M plus a margin. It halves each worker's answer. In exchange it
repeats the shared content in twice as many workers: 4.24M against 2.60M of
typed input for AI_READI, and 4.61M against 2.83M for Kids First.

**Output limits (for A6), at G5:**
- **`worker_output_tokens`** must hold the largest worker's whole answer plus
  its thinking. That is at least 24,456 tokens on these records at 4 bytes a
  token, and more in a real answer, which cites real sources, quotes and
  reasons. Sizing one needs a measured answer; this note has only a floor.
- **`aggregate_output_tokens` (100,000)** must hold every worker's answer plus
  the omission and integration outputs.
  - **The floor.** It is at most 48,906 tokens (AI_READI, Kids First) at 4
    bytes a token.
  - **At A1b's ratios.** It is 66,000–80,000 at the 0.34–0.41 tokens a byte
    A1b counted on other requests, before thinking or real content.
  - **So** 100,000 is likely too small for AI_READI and Kids First.
- **Not floored.** The omission and integration outputs were not measured
  from below (see "What this does not establish").

**The report family needs one more change for Kids First under S7.** The
excess is 30,265 tokens at the audit's floor, and more with a real audit. In
Kids First's regate (S7, primary record, G2), each of these parts is larger
than that excess:
- **the assembled audit:** 218,230 B as carried, about 80,000 tokens;
- **the induced-slot classes S5 keeps:** 195,717 B, about 72,000;
- **the source-review inventory:** 164,691 B, about 61,000.

So any one of these changes would clear the excess at the floor:
- carry only the audit's findings and revised rows;
- drop the remaining classes from the report family's schema context;
- stop repeating the inventory there.

AI_READI's regate has 33,855 tokens of room at the floor. It would need the
same change if its real audit outgrows the floor by more than that.

**S7 and these changes are not decided here.** Each changes model-facing text,
which makes it a new shared-generation version at a condition boundary (D17).
It touches:
- `shared_generation.py`, which only agy edits;
- the typed audit (`typed_audit.py`, `audit_omissions.py`);
- receipt completion;
- an asset and prompt pin review.

It needs the owner's decision. Four design questions stand out:
- **The catalog's role.** The typed audit's code keeps using its catalog for
  its own checks; S1 removes only the model-facing copy.
- **S5's key list** (`domain_of`, `from_schema`, `alias`, `owner`, `@type`,
  `slot_uri`, `annotations`, `exact_mappings`). It is a candidate; whether
  `slot_uri` and mappings must stay model-facing is a design question.
- **The owners' typed trees** (`whole_value_identity`). They duplicate each
  owner's YAML in another form; whether relationship review needs them is
  also open.
- **What the report family needs from the audit.** Today it carries every
  row.

Under D07 the AI_READI lines are already provisional, and they are re-planned
before A14 when a request does not fit. This is that evidence, and it reaches
Kids First too.

## Results (generated)

The output of `summary` for the results file named under "Method",
unedited. Estimated tokens in flight are input plus the request's
`max_tokens`. The ceilings are 1,000,000 for a worker and every other request,
and 850,000 for the report family.

Current protocol, G2, primary records (estimated tokens in flight; "over" passes the request's ceiling; † carries the audit at the workers' smallest responses, which here exceed the registered output caps' bound):

| Project | Largest worker | Largest worker, every record at G2 | Omission | Integration | Receipt completion (with a re-address turn) | Report | Regate (report at its 96k cap) |
|---|---|---|---|---|---|---|---|
| AI_READI | 1,503,806 over | 1,415,387–1,503,806 (3) | 1,214,709 over | 1,521,378 over † | 915,389 | 1,057,817 over † | 1,153,281 over † |
| CHORUS | 1,013,943 over | 1,013,943–1,098,807 (4) | 806,740 | 1,023,351 over † | 714,131 | 480,428 † | 575,886 † |
| CM4AI | 1,244,897 over | 1,244,897–1,276,331 (3) | 986,524 | 1,260,100 over † | 847,690 | 740,168 † | 835,715 † |
| KIDS_FIRST (proxy) | 1,599,185 over | 1,503,462–1,599,185 (3) | 1,269,832 over | 1,617,427 over † | 957,757 | 1,135,129 over † | 1,230,811 over † |
| VOICE | 1,447,146 over | 1,430,519–1,513,279 (3) | 1,163,032 over | 1,462,768 over † | 893,182 | 946,062 over † | 1,041,679 over † |
| VOICE_PEDIATRIC (proxy) | 1,353,599 over | 1,337,447–1,422,906 (3) | 1,080,563 over | 1,369,221 over † | 802,850 | 881,361 over † | 976,957 over † |

Under S7, G2, primary records:

| Project | Largest worker | Omission | Integration | Receipt completion (with a re-address turn) | Report | Regate (report at its 96k cap) |
|---|---|---|---|---|---|---|
| AI_READI | 551,313 | 400,843 | 568,884 † | 343,186 | 720,721 † | 816,145 † |
| CHORUS | 187,244 | 131,433 | 196,652 † | 126,800 | 303,542 † | 398,939 † |
| CM4AI | 381,345 | 277,043 | 396,549 † | 260,360 | 511,512 † | 606,981 † |
| KIDS_FIRST (proxy) | 599,600 | 434,205 | 617,841 † | 370,427 | 784,703 † | 880,265 over † |
| VOICE | 463,668 | 342,342 | 479,290 † | 305,852 | 605,436 † | 700,937 † |
| VOICE_PEDIATRIC (proxy) | 370,122 | 259,873 | 385,743 † | 215,520 | 540,736 † | 636,214 † |

Under S7 plus each project's largest record difference at G2 (another record's current figure minus the primary's, where positive), the conservative reading:

| Project | Largest worker | Omission | Integration | Receipt completion (with a re-address turn) | Report | Regate (report at its 96k cap) |
|---|---|---|---|---|---|---|
| AI_READI | 551,313 (+0) | 400,843 (+0) | 568,884 (+0) | 343,186 (+0) | 720,721 (+0) | 816,145 (+0) |
| CHORUS | 272,108 (+84,864) | 196,871 (+65,438) | 283,827 (+87,175) | 141,535 (+14,735) | 415,422 (+111,880) | 510,857 (+111,918) |
| CM4AI | 412,779 (+31,434) | 305,445 (+28,402) | 428,231 (+31,682) | 267,046 (+6,686) | 531,036 (+19,524) | 626,512 (+19,531) |
| KIDS_FIRST (proxy) | 599,600 (+0) | 434,205 (+0) | 617,841 (+0) | 370,427 (+0) | 784,703 (+0) | 880,265 (+0) over |
| VOICE | 529,801 (+66,133) | 394,234 (+51,892) | 546,225 (+66,935) | 312,627 (+6,775) | 665,775 (+60,339) | 761,297 (+60,360) |
| VOICE_PEDIATRIC (proxy) | 439,429 (+69,307) | 313,894 (+54,021) | 455,852 (+70,109) | 225,938 (+10,418) | 601,075 (+60,339) | 696,573 (+60,359) |

Typed input across every typed call of a run, current / S6 / S7, against `aggregate_input_tokens` (4,000,000); the options use the G2 components, since a worker's shared content does not depend on the partition:

| Project | G1 | G2 | G3 | G4 | G5 | G6 |
|---|---|---|---|---|---|---|
| AI_READI | refused | 11.72M* / 4.85M* / 4.24M* | 7.23M* / 2.99M / 2.60M | 11.72M* / 4.85M* / 4.24M* | 7.23M* / 2.99M / 2.60M | 5.73M* / 2.37M / 2.06M |
| CHORUS | 4.85M* / 0.96M / 0.87M | 3.84M / 0.76M / 0.68M | 2.83M / 0.56M / 0.50M | 3.84M / 0.76M / 0.68M | 2.83M / 0.56M / 0.50M | 2.83M / 0.56M / 0.50M |
| CM4AI | refused | 5.96M* / 2.00M / 1.80M | 4.72M* / 1.59M / 1.42M | 5.96M* / 2.00M / 1.80M | 4.72M* / 1.59M / 1.42M | 3.48M / 1.17M / 1.05M |
| KIDS_FIRST (proxy) | refused | 12.44M* / 5.25M* / 4.61M* | 7.67M* / 3.23M / 2.83M | 12.44M* / 5.25M* / 4.61M* | 7.67M* / 3.23M / 2.83M | 6.07M* / 2.56M / 2.24M |
| VOICE | 14.15M* / 5.04M* / 4.48M* | 8.39M* / 2.99M / 2.65M | 5.51M* / 1.96M / 1.74M | 8.39M* / 2.99M / 2.65M | 5.51M* / 1.96M / 1.74M | 4.07M* / 1.45M / 1.28M |
| VOICE_PEDIATRIC (proxy) | 13.23M* / 4.12M* / 3.55M | 7.84M* / 2.44M / 2.10M | 5.14M* / 1.60M / 1.37M | 7.84M* / 2.44M / 2.10M | 5.14M* / 1.60M / 1.37M | 3.80M / 1.18M / 1.01M |

\* passes the allowance.

Worker output: the smallest response the worker check accepts, largest worker / all workers, in tokens at 4 bytes a token (at least), with the largest assignment's paths. The registered worker cap is 4,000; `aggregate_output_tokens` is 100,000:

| Project | G1 | G2 | G3 | G4 | G5 | G6 |
|---|---|---|---|---|---|---|
| AI_READI | refused | 11,464 / 48,906 (171) | 22,481 / 48,731 (277) | 11,464 / 48,906 (171) | 22,481 / 48,731 (277) | 43,464 / 48,698 (478) |
| CHORUS | 6,079 / 13,966 (81) | 10,949 / 13,907 (138) | 13,827 / 13,827 (188) | 10,949 / 13,907 (138) | 13,827 / 13,827 (188) | 13,827 / 13,827 (188) |
| CM4AI | refused | 11,861 / 30,946 (182) | 24,456 / 30,912 (383) | 11,861 / 30,946 (182) | 24,456 / 30,912 (383) | 30,832 / 30,832 (456) |
| KIDS_FIRST (proxy) | refused | 11,464 / 48,906 (171) | 22,481 / 48,731 (277) | 11,464 / 48,906 (171) | 22,481 / 48,731 (277) | 43,464 / 48,698 (478) |
| VOICE | 5,701 / 35,190 (77) | 11,473 / 35,042 (142) | 21,919 / 34,956 (278) | 11,473 / 35,042 (142) | 21,919 / 34,956 (278) | 34,903 / 34,903 (426) |
| VOICE_PEDIATRIC (proxy) | 5,701 / 35,190 (77) | 11,473 / 35,042 (142) | 21,919 / 34,956 (278) | 11,473 / 35,042 (142) | 21,919 / 34,956 (278) | 34,903 / 34,903 (426) |

Staging of each stand-in record (conformance edits to the current schema's cardinality):

| Record | Edits | Undeclared slots removed | Bytes before → after |
|---|---|---|---|
| AI_READI `2026-09-04g_claude-opus-5-api-generic-v8_rep1` | 5 | — | 72,929 → 72,954 (+25, +0.03%) |
| AI_READI `2026-09-04g_claude-opus-5-api-generic-v8_rep2` | 8 | — | 94,536 → 94,145 (-391, -0.41%) |
| AI_READI `2026-09-04g_claude-opus-5-api-generic-v8_rep3` | 10 | `/data_governance/accountable_organization_notes` | 80,148 → 80,149 (+1, +0.00%) |
| CHORUS `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | 3 | — | 36,574 → 36,579 (+5, +0.01%) |
| CHORUS `2026-09-04f_claude-opus-5-api-generic-v8_rep2` | 3 | — | 36,459 → 36,554 (+95, +0.26%) |
| CHORUS `2026-09-04f_claude-opus-5-api-generic-v8_rep3` | 11 | — | 39,118 → 39,134 (+16, +0.04%) |
| CHORUS `2026-09-12_claude-opus-5-api-generic-v9_rep1` | 6 | — | 23,618 → 23,643 (+25, +0.11%) |
| CM4AI `2026-09-04g_claude-opus-5-api-generic-v8_rep1` | 2 | — | 41,316 → 41,203 (-113, -0.27%) |
| CM4AI `2026-09-04g_claude-opus-5-api-generic-v8_rep2` | 11 | `/instances/0/instance_details`, `/instances/1/instance_details`, `/instances/2/instance_details` | 40,423 → 39,830 (-593, -1.47%) |
| CM4AI `2026-09-04g_claude-opus-5-api-generic-v8_rep3` | 9 | `/instances/0/instance_type_notes` | 44,850 → 44,850 (+0, +0.00%) |
| VOICE `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | 10 | — | 62,431 → 62,329 (-102, -0.16%) |
| VOICE `2026-09-04f_claude-opus-5-api-generic-v8_rep2` | 9 | — | 67,715 → 67,431 (-284, -0.42%) |
| VOICE `2026-09-04f_claude-opus-5-api-generic-v8_rep3` | 8 | — | 75,714 → 75,633 (-81, -0.11%) |

## Method

**Tree measured.** `8ea7986160a5b0a3079f64c12f9d59074ff564af`
(`origin/feat/v10-preflight-scripts`, PR #5095: main with #5093, #5094 and
#5095, the pre-launch stack).
- It was checked out detached in a scratch worktree, with no dirty tracked
  paths, and was unchanged afterwards.
- `data_sheets_schema` and `scripts` are namespace packages. The sweep
  removed every other checkout from the import path and recorded that no
  module came from outside the tree.
- It ran from the tree, which it checked was where resources resolve.
- It cleared `D4D_RECEIPT_FULL_MAX_TOKENS`.

**Registrations.** Each run used the A3 draft builder
(`scripts/build_api_registrations.build_registration`) with the A5d omission
contexts:
- **Selection:** `shared_generation_v1`, renderer 25, `Claude API (direct)`,
  playbook v2, receipt completion v2.
- **Runtime:** claude-opus-5, thinking `{adaptive, summarized}` (D06).
- **Audit limits.** These are the builder's defaults, with each grid's
  partition values:
  - worker, omission and integration output: 4,000 each;
  - aggregate input: 4,000,000;
  - aggregate output: 100,000;
  - `max_calls`: 18.

Kids First has no A5d context. Its root-only draft context was synthesized
by the same builder's `build_draft_context` from its own source manifest
(`notes/matched_cborg_2026-09-13/kids_first/manifest.yaml`). It runs with:
- the neutral profile (A19-reg);
- its bundle (541,184 B, md5 `93b80751`);
- its 58-chunk manifest (`chunks.yaml`).

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

The re-address turn and receipt completion carry the full phase's whole
delivered body: the record, the receipt mark, then the receipt. Receipt
completion is also sized after a re-address, when its transcript is the
re-address exchange.

**Caps** come from the payloads themselves and `phase_max_tokens`:

| Request | Cap (tokens) |
|---|---|
| full | 128,000 |
| re-address | 8,000 |
| `reconcile_full`, report, regate, repair | 96,000 |
| typed stages, receipt completion | 4,000 |

As in the A1 harness, receipt recovery and the integration index are inert
stand-ins.

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
- **The proxies** use the stand-in project's records with the proxy project's
  own bundle and chunk manifest. VOICE_PEDIATRIC uses its own context; Kids
  First uses the synthesized draft. Each proxy's receipt is minimal (every
  chunk `nothing_relevant`), which understates a real receipt by about
  33–37 KB.

**Conformance.** Each record passes through the runner's write-time
normaliser, and is then conformed to the current schema's cardinality (see
Finding 2).
- **Edits.** The 13 records needed 95 edits, 2–11 each:
  - 65 scalars wrapped into lists;
  - 25 lists in single-valued slots joined;
  - 5 undeclared slots removed from 3 records.
- **The removals delete model content.** The staging table under "Results"
  lists them.
- **Bytes.** The edits go through a round-trip YAML dump, so a record's bytes
  change by −593 to +95 (−1.47% to +0.26%). A plain re-dump shrank them by
  7–8%.

**The AI_READI receipts.** AI_READI's v8 receipts pin bundle `d22b61a9`,
which #5042 replaced with `1a58ad7b`. They were carried onto today's manifest
by chunk sha256, using the manifest at `1cde41f59`:
- 25 entries moved;
- the three RO-Crate chunks `c022`–`c024` were dropped.

**Placeholders and floors.** Content that does not exist before a run is
sized from above, at its cap, in tokens:
- **The report as written**, carried in the regate, at 96,000. The appendix
  also sizes it with the v8 report text.
- **The re-address response**, at 8,000.
- **The omission response** that integration carries, at 4,000.

The typed workers' answers are sized from below:
- **Each worker's smallest valid answer** (`response_floor`). It has one
  source-review row per assigned path, each claim quoting its whole value, and
  every other string one character long. It is put through the runtime's own
  `audit_batches.check_worker` (grammar v2).
- **The variants.** Two variants are built: every claim supported with one
  assertion, or every claim revised with one linking finding. Every worker in
  every run had a passing variant, and the smaller passing one is the floor.
- **Tokens.** The floor uses 4 bytes a token (0.25 a byte). That is an
  assumption, not a count. It is below every ratio A1b counted (0.34–0.41), so
  the floor errs low unless this JSON tokenizes unusually well.

Two carries take the larger of two figures, because a completed audit
carries every row whatever the caps:
- **The assembled audit** that `reconcile_full` and the report family carry.
  - The registered caps' bound is (W + 1) × 4,000 tokens.
  - The other figure is the workers' smallest answers assembled by
    `audit_batches.assemble`, the bytes the runner carries (`floor_assembly`).
  - The floor was the larger in all 46 measured runs.
- **The worker answers integration carries.** Their caps against their
  smallest answers: again the floor, in all 46.

**Calibration.** Tokens are payload bytes times the tokens-per-byte ratio A1b
counted for the same project and stage on 2026-10-12.
- **Source.** `notes/.local_drafts/a1b_calibrated_tokens.json` at local commit
  `10dee83fe`, a commit on no remote branch, sha256
  `3146ef36c265d4d06058da242c49ccd3804d24b771cc4fe43a1d7496c5924186`. The
  figures are copied into the script.
- **Projects A1b did not count** (CM4AI, VOICE, VOICE_PEDIATRIC, Kids First)
  get the higher of the CHORUS and AI_READI ratios.
- **Ranges.** Each estimate's range uses the lower and higher ratio.
- **Ratios.** The calibrated ratios run 0.34–0.41.
- **Placeholder correction.** A1b's report-family payloads carried
  `'x' * (4 × cap)` placeholders, and the endpoint counted about one token per
  `x`.
  - Regate minus report is +382,173 B and +383,458 tokens in both projects.
  - The clean ratios remove the placeholders.
  - Report and regate then agree to within 0.00013 (CHORUS 0.368501/0.368627,
    AI_READI 0.354484/0.354525), which checks the correction.

**Verdicts.** Rows read `estimate_fits` or `estimate_exceeds` against these
ceilings:
- 1,000,000 for a worker;
- 850,000 for report, regate and the after-repair report;
- 1,000,000 for everything else.

They never read `PASS`. The evidence reader now enforces the same ceilings on
saved counts, whatever window or margin a caller declares.

**Reproducibility.** Every figure in this note comes from one sweep:

| Item | Value |
|---|---|
| script `scripts/offline_sizing.py` at this commit, sha256 | `48f49c59b37dbb4191e4ecd116aafde3af10a588da5db73908f3125e194f1fc9` |
| results file, sha256 | `b2cc6f0b8f2ee7fa35a0b76823bdbfe6a6ce84b1e69109ea70fadf17d9bfc4a6` |
| connection attempts | none |
| modules from outside the tree | none |

- **Earlier sweep.** An earlier sweep with the previous script (`a42b47a7…`)
  gave byte-identical figures for every request and every worker except the
  six that carry the audit or the workers' answers. Its results sha256 was
  `adb3e32a…`.
- **The run directory.** It reaches each typed request three times (plan risk
  7). Here it was 221 characters; a production run directory is 88 when
  relative. So the typed figures overstate by up to about 400 B a request,
  about 160 tokens.
- **Not committed.** The results file is not committed. The commands under
  "Reproduce" regenerate it from tracked files.

## Corrections to the earlier A1, A1b and first-version record

1. **The A1b report-family counts are inflated by the placeholders.**
   - **CHORUS's regate** was recorded as "879,597 total, 12.0% headroom, FAIL".
     Recomputed from A1b's own numbers, it is about 579,597: placeholders out,
     the report at its 96k cap, findings at their 4k cap.
   - **Today**, with the audit at its floor, the builders give 575,886. That is
     32.2% under the 850,000 ceiling, or 42.4% under the 1,000,000 window A1b's
     12.0% was measured against. The CHORUS regate is not a binding constraint.
   - **AI_READI's report and regate failures are real**: about 1.02M and 1.11M
     on A1b's numbers, 1,057,817 and 1,153,281 today.
   - **Still on record.** The A1b draft on local `main` (`10dee83fe`) still
     lists the CHORUS regate as a FAIL.
2. **A1b's worker "Output Cap" column (16,000) was a constant** in its report
   formatter. The registration's worker cap is 4,000. This changes no input
   verdict, and result 2 shows the registered cap is far too small anyway.
3. **The AI_READI A1b counts predate #5042.** Today's largest AI_READI worker
   is 146,531 B smaller (3,836,681 against 3,983,212), and still about 50% over
   the ceiling.
4. **This note's first version** (`64082b98d`, `e6d46f3a3`) had four errors,
   found in review:
   - **The recommendation.** It recommended G2, which fails the registered
     typed input aggregate under S6 and S7 for AI_READI and Kids First.
   - **The audit carry.** It sized the audit the report family carries at
     4,000 tokens. The caps' bound is (W + 1) × 4,000, and a completed audit
     carries at least the workers' smallest answers, which are larger still.
   - **S7.** It said S7 fits every stage for all six projects. With the audit
     at its floor, Kids First's regate does not.
   - **Its Finding 1** misplaced the normaliser's gap and the point where the
     run stops. Finding 2 below corrects it.

   It also had smaller errors:
   - It called CHORUS "at the edge" against A1b's count.
   - The grid spread was "0.4%"; it is 0.5%.
   - It reported one slot removed; five were, in three records.
   - The byte range went down to −391; it goes down to −593.
   - The ratios agree to three decimals, not four.
   - Its 34.5% headroom was against 850,000, not the window.
   - The path overstatement is about 400 B, not "a few dozen bytes".
   - Two snapshots were said to differ "only in reporting", which was untrue.
   - It said the catalog S6 removes does not depend on the record. S5's half
     does, so record differences are added unscaled as a conservative reading.

## Findings for the integrator

I can't file issues; agy files these.

1. **Launch blocker: no typed worker can return a valid answer inside the
   registered output cap.**
   - **The rule.** `audit_batches.check_worker` requires a source-review row,
     with nonempty claims quoting the value, for every assigned path.
   - **The numbers.** Even the smallest such answer exceeds the A3 draft's
     `worker_output_tokens` of 4,000 (`DEFAULT_AUDIT_LIMITS`) for every
     project at every grid: 2.7–3.0 times at G2, and 3.5–6.1 times at G5.
   - **What happens.** The answer is cut off at `max_tokens`. The runtime
     refuses a response that did not end with `end_turn`, and the typed audit
     is terminal.
   - **For A6.** It must size `worker_output_tokens` and
     `aggregate_output_tokens` from a measured worker answer. This note gives
     only floors.
2. **Possible launch risk: record shapes that no runtime step repairs stop
   the run at receipt completion.**
   - **The requirement.** `audit_omissions._owners` requires a value's
     list-ness to match the slot's `multivalued`, and so does schema
     validation.
   - **What the normaliser covers.** It lists scalars in every class's induced
     multivalued string slots (`_multivalued_of`), at any indentation
     (`_SCALAR_LINE`). It misses one shape: a scalar on a line that opens a
     sequence item, `- slot: value`. CHORUS v9 rep1 has it at lines 290, 373
     and 412:
     - `- tools: OHNLP toolkit`;
     - `- examples: …`;
     - `- external_resources: >-`.
   - **What no normaliser does.** None joins a list written in a single-valued
     slot. 25 of the 95 conformance edits were such joins, for example CHORUS
     v8 `/sampling_strategies/0/strategies`.
   - **Where the run stops.** In a generic_v10 run, receipt completion runs
     before the typed audit. Its `_validate_record` runs linkml-validate on
     the persisted full record before its count or its call. A record with
     either shape fails there, after full (and any re-address) is billed.
   - **No repair comes first.** `_repair_invalid` runs only after the phase
     loop, so nothing repairs cardinality before the originals freeze.
   - **How far this reaches.** The stand-ins were written against earlier
     schemas, so their 95 edits do not predict v10's rate. They show that the
     shapes occur and that only the normaliser stands between them and a stop.
   - **Not tested here.** The sweep conforms its stand-ins itself and
     bypasses `_validate_record`, so it does not test that gate. CM4AI 04g
     rep2 would still fail five ORCID patterns.
3. **The A1b placeholder method.** Runs of `x` count about one token each,
   not a quarter. `build_phase`'s dry-run source-review placeholder
   (`'x' * (2 * len + 1024)`) would overcount the same way if it were ever
   counted.
4. **Old receipts and today's bundle.** AI_READI's v8 receipts name the
   pre-#5042 bundle, so receipt validation refuses them against today's. An
   A1b recount on today's bundle needs a carried receipt (as here) or a fresh
   run.
5. **Kids First is the largest case, and its inputs are incomplete.**
   - **Where they are.** Its bundle (541,184 B) and its chunk and source
     manifests are tracked under `notes/matched_cborg_2026-09-13/kids_first/`,
     not `data/preprocessed/`.
   - **What is missing.** It has no A5d omission context in #5095 and no
     record, so here it is sized by proxy.
   - **Why it matters.** Its requests are the largest of the six, and its S7
     regate is the one that exceeds.
   - **Before an A1b count.** That count needs an A5d context first.
6. **The report family carries the whole assembled audit.** That is every
   source-review row, not only the findings. It is the largest lever on Kids
   First's S7 regate (result 3). What the report family needs from the audit
   is a design question for the owner.
7. **The integration figure is only partly bounded.** It counts:
   - the workers' answers, at the larger of their caps and their floors;
   - the omission response, at its cap.

   It does not count the proposal index derived from them, so it understates.
8. **`typed_audit.prepare`'s default limits** (96 paths, 16,384 B) are refused
   for AI_READI, CM4AI and Kids First. G2–G6 are valid.
9. **Run-specific strings reach typed-stage text.** The run directory appears
   three times in every typed request, which confirms plan risk 7 for these
   stages.
10. **The regate's contradiction listing is not sized.** No cap bounds it, and
    a regate happens only when the listing is non-empty.

## What this does not establish

- **Token counts.** Every figure is bytes times a ratio. Ratios differ by
  content, so a request whose mix differs from what A1b counted carries more
  uncertainty than its range shows. That applies above all to the S1–S7 rows,
  which remove one kind of content and keep the request's ratio, and to the
  floors' assumed 4 bytes a token.
- **Fit.** Nothing here makes a request fit, or makes a launch acceptable.
- **A real worker answer.** Only its floor is measured. Real sources, quotes,
  reasons and thinking make it larger.
- **The omission and integration outputs.** They were not floored.
  - The omission response has one row per chunk, plus any candidates.
  - Integration's has a decision per finding, plus any replacements.
  - Either could exceed its 4,000 cap.
- **The report as v10 will write it.** The report-family estimates use the v8
  reconciled records and, at worst, the 96k cap.
- **The proxies.** VOICE_PEDIATRIC and Kids First are proxies, and Kids First's
  record and context are stand-ins.
- **The provider side.** Provider support, billing and the thinking display on
  count calls are not checked here; agy's A1b count settles them.

## Reproduce

The sweep needs a checkout of #5095 (the A3 builder and A5d contexts) and
this branch's script. Make no provider call; the script blocks sockets.

```sh
git -C <repository> worktree add --detach <tree> 8ea7986160a5b0a3079f64c12f9d59074ff564af
P="PYTHONPATH=<tree>/src:<tree>"
env $P python <branch>/scripts/offline_sizing.py sweep --root <tree> \
  --workdir <new dir> --out results.json
python <branch>/scripts/offline_sizing.py summary results.json   # "Results"
python <branch>/scripts/offline_sizing.py table results.json     # the appendix
```

How it runs:
- **Where.** The sweep changes into `--root` itself, and refuses to run if
  resources resolve elsewhere.
- **How long.** It took about 25 minutes offline.
- **What shifts.** Typed-stage bytes move by three times any difference in
  the work directory's length. Everything else is byte-identical.

## Appendix: complete tables (generated)

The output of `table` for the same results file, unedited.

Ceilings: worker 1,000,000; report family 850,000; every other request 1,000,000 (tokens in flight: input plus `max_tokens`).

### AI_READI

Primary record `2026-09-04g_claude-opus-5-api-generic-v8_rep2`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict | Assigned inventory per worker B | Typed input, all calls: current / S6 / S7 |
|---|---|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | refused | | | AuditBatchError: indivisible_field_bound | | |
| G2 | 192 / 32,768 / 16 | 6 | 3,836,681 | 1,503,806 | estimate_exceeds | 11,653–32,258 | 11,719,242 over / 4,852,926 over / 4,237,924 over |
| G3 | 384 / 65,536 / 16 | 3 | 3,841,486 | 1,505,685 | estimate_exceeds | 33,927–65,061 | 7,228,138 over / 2,987,159 / 2,604,297 |
| G4 | 192 / 32,768 / 8 | 6 | 3,836,679 | 1,503,805 | estimate_exceeds | 11,653–32,258 | 11,719,237 over / 4,852,918 over / 4,237,917 over |
| G5 | 384 / 65,536 / 4 | 3 | 3,841,484 | 1,505,684 | estimate_exceeds | 33,927–65,061 | 7,228,134 over / 2,987,154 / 2,604,294 |
| G6 | 768 / 131,072 / 2 | 2 | 3,851,015 | 1,509,410 | estimate_exceeds | 13,524–129,371 | 5,731,143 over / 2,365,278 / 2,059,796 |

"Over" in the last column passes the registered typed `aggregate_input_tokens` (4,000,000). The assigned inventory is what a worker must answer for, one row per path with complete claims, inside its output cap of 4,000 tokens.

Worker output: the smallest response the worker check accepts (`response_floor`), against the registered caps. Tokens are at 4 bytes a token, so they err low, and thinking draws on the same `max_tokens`. "Over" on the largest worker passes its cap (4,000). "Over" on the sum means the workers' smallest responses plus integration's cap (4,000) pass `aggregate_output_tokens` (100,000); the runtime admits a stage only while the output already spent plus that stage's `max_tokens` stays inside it.

| Grid | Workers | Largest assignment (paths) | Largest worker's smallest response B | Its tokens, at least | All workers' smallest responses, tokens at least |
|---|---|---|---|---|---|
| G2 | 6 | 171 | 45,854 | 11,464 over | 48,906 |
| G3 | 3 | 277 | 89,922 | 22,481 over | 48,731 |
| G4 | 6 | 171 | 45,854 | 11,464 over | 48,906 |
| G5 | 3 | 277 | 89,922 | 22,481 over | 48,731 |
| G6 | 2 | 478 | 173,856 | 43,464 over | 48,698 |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 3,836,681 | 0.3909 (A1b AI_READI typed_audit_worker) | 0 | 4,000 | 1,503,806 (1,503,806–1,577,958) | 1,000,000 | estimate_exceeds |
| full | 677,021 | 0.3408 (A1b AI_READI full) | 0 | 128,000 | 358,708 (358,708–372,660) | 1,000,000 | estimate_fits |
| full_readdress | 810,806 | 0.3406 (A1b AI_READI full_readdress) | 0 | 8,000 | 284,157 (284,157–300,042) | 1,000,000 | estimate_fits |
| full_receipt_completion | 2,503,286 | 0.3607 (A1b AI_READI full_receipt_completion) | 0 | 4,000 | 907,042 (907,042–930,915) | 1,000,000 | estimate_fits |
| full_receipt_completion_after_readdress | 2,504,248 | 0.3607 (A1b AI_READI full_receipt_completion) | 8,000 | 4,000 | 915,389 (915,389–939,272) | 1,000,000 | estimate_fits |
| reconcile_full (audit carried at: workers' smallest responses, assembled) | 2,266,873 | 0.3573 (A1b AI_READI reconcile_full) | 0 | 96,000 | 905,924 (905,924–936,967) | 1,000,000 | estimate_fits |
| repair_full | 165,675 | 0.3738 (A1b AI_READI repair_full) | 0 | 96,000 | 157,926 (157,926–163,065) | 1,000,000 | estimate_fits |
| report (audit carried at: workers' smallest responses, assembled) | 2,713,286 | 0.3545 (A1b AI_READI report) | 0 | 96,000 | 1,057,817 (1,057,817–1,095,847) | 850,000 | estimate_exceeds |
| report_regate (audit carried at: workers' smallest responses, assembled) | 2,711,459 | 0.3545 (A1b AI_READI report_regate) | 96,000 | 96,000 | 1,153,281 (1,153,281–1,191,516) | 850,000 | estimate_exceeds |
| report_regate_with_v8_report (audit carried at: workers' smallest responses, assembled) | 2,729,794 | 0.3545 (A1b AI_READI report_regate) | 0 | 96,000 | 1,063,781 (1,063,781–1,102,275) | 850,000 | estimate_exceeds |
| typed_audit_integration (audit carried at: workers' smallest responses) | 3,675,784 | 0.3909 (A1b AI_READI typed_audit_worker) | 80,468 | 4,000 | 1,521,378 (1,521,378–1,592,420) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 3,267,655 | 0.3705 (A1b AI_READI typed_audit_omission) | 0 | 4,000 | 1,214,709 (1,214,709–1,247,081) | 1,000,000 | estimate_exceeds |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04g_claude-opus-5-api-generic-v8_rep1` | 72,954 | 5 | 4 | 1,415,387 | 1,145,773 | 1,432,692 | 892,636 | 959,683 | 1,055,135 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep2` | 94,145 | 8 | 6 | 1,503,806 | 1,214,709 | 1,521,378 | 907,042 | 1,057,817 | 1,153,281 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep3` | 80,149 | 10 | 4 | 1,448,509 | 1,176,904 | 1,465,183 | 893,711 | 972,946 | 1,068,400 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (3,836,681 B): m0.6: # Exact typed stage request 2,435,486 (63%); inside: shared.schema 1,486,502 (39%); m0.3: # Shared generation: captured schema owners and complete containing va 1,351,652 (35%); schema context: classes 949,673 (25%); inside: shared.bundle 496,003 (13%); schema context: owners 401,167 (10%); schema context: nested_owners 203,349 (5%); schema context: owner_typed_tree 197,947 (5%); schema context: owner_yaml 183,437 (5%)
- **typed_audit_omission** (3,267,655 B): m0.6: # Exact typed stage request 1,866,488 (57%); m0.3: # Shared generation: captured schema owners and complete containing va 1,351,652 (41%); inside: payload.schema 1,246,504 (38%); schema context: classes 949,673 (29%); inside: payload.chunks 463,549 (14%); schema context: owners 401,167 (12%); schema context: nested_owners 203,349 (6%); schema context: owner_typed_tree 197,947 (6%); schema context: owner_yaml 183,437 (6%)
- **full_receipt_completion** (2,503,286 B): m2.0: {"input_sha256":{"bundle":"b4a282fd5c44bc93a3bcd71a4c3ee53b36a0de31d10 1,690,125 (68%); inside: json.schema 1,542,013 (62%); m0.1: # Declared input bundle — <path> 443,225 (18%); inside: json.record_yaml 97,505 (4%); m0.5: ## API factual and phase policy v2 88,100 (4%); m0.6: # Shared generation: captured schema owners and complete containing va 76,978 (3%); schema context: classes 76,166 (3%); m0.0: # Target class `Dataset` — slot inventory 45,592 (2%); inside: json.receipt_yaml 38,193 (2%)
- **report_regate** (2,711,459 B): m0.14: # Shared generation: captured schema owners and complete containing va 1,361,964 (50%); schema context: classes 936,972 (35%); m0.1: # Declared input bundle — <path> 443,225 (16%); schema context: owners 424,180 (16%); m0.6: # Audit findings 218,230 (8%); schema context: nested_owners 213,250 (8%); schema context: owner_typed_tree 209,695 (8%); schema context: owner_yaml 194,815 (7%); m0.13: # Required source-review inventory 164,691 (6%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 922,714 (fits) | 752,863 (fits) | 940,286 (fits) | 350,772 (fits) | 1,057,817 (exceeds) | 1,153,281 (exceeds) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 1,132,567 (exceeds) | 862,843 (fits) | 1,150,139 (exceeds) | 879,566 (fits) | 725,676 (fits) | 821,101 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 858,887 (fits) | 752,863 (fits) | 940,286 (fits) | 350,772 (fits) | 1,057,817 (exceeds) | 1,153,281 (exceeds) |
| S4: S1 plus owners without their typed trees | 845,334 (fits) | 679,521 (fits) | 862,906 (fits) | 350,772 (fits) | 983,484 (exceeds) | 1,078,939 (exceeds) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 1,209,785 (exceeds) | 936,031 (fits) | 1,227,356 (exceeds) | 891,109 (fits) | 795,054 (fits) | 890,487 (exceeds) |
| S6: S1 plus S5 | 628,693 (fits) | 474,185 (fits) | 646,264 (fits) | 334,839 (fits) | 795,054 (fits) | 890,487 (exceeds) |
| S7: S6 plus owners without their typed trees | 551,313 (fits) | 400,843 (fits) | 568,884 (fits) | 334,839 (fits) | 720,721 (fits) | 816,145 (fits) |

### CHORUS

Primary record `2026-09-12_claude-opus-5-api-generic-v9_rep1`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict | Assigned inventory per worker B | Typed input, all calls: current / S6 / S7 |
|---|---|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | 3 | 2,458,921 | 1,012,746 | estimate_exceeds | 8,608–16,191 | 4,847,463 over / 964,244 / 865,360 |
| G2 | 192 / 32,768 / 16 | 2 | 2,461,837 | 1,013,943 | estimate_exceeds | 8,608–30,422 | 3,840,022 / 763,435 / 684,618 |
| G3 | 384 / 65,536 / 16 | 1 | 2,463,399 | 1,014,584 | estimate_exceeds | 39,028–39,028 | 2,832,545 / 562,587 / 503,840 |
| G4 | 192 / 32,768 / 8 | 2 | 2,461,835 | 1,013,942 | estimate_exceeds | 8,608–30,422 | 3,840,019 / 763,431 / 684,615 |
| G5 | 384 / 65,536 / 4 | 1 | 2,463,397 | 1,014,583 | estimate_exceeds | 39,028–39,028 | 2,832,542 / 562,585 / 503,837 |
| G6 | 768 / 131,072 / 2 | 1 | 2,463,399 | 1,014,584 | estimate_exceeds | 39,028–39,028 | 2,832,545 / 562,587 / 503,840 |

"Over" in the last column passes the registered typed `aggregate_input_tokens` (4,000,000). The assigned inventory is what a worker must answer for, one row per path with complete claims, inside its output cap of 4,000 tokens.

Worker output: the smallest response the worker check accepts (`response_floor`), against the registered caps. Tokens are at 4 bytes a token, so they err low, and thinking draws on the same `max_tokens`. "Over" on the largest worker passes its cap (4,000). "Over" on the sum means the workers' smallest responses plus integration's cap (4,000) pass `aggregate_output_tokens` (100,000); the runtime admits a stage only while the output already spent plus that stage's `max_tokens` stays inside it.

| Grid | Workers | Largest assignment (paths) | Largest worker's smallest response B | Its tokens, at least | All workers' smallest responses, tokens at least |
|---|---|---|---|---|---|
| G1 | 3 | 81 | 24,316 | 6,079 over | 13,966 |
| G2 | 2 | 138 | 43,795 | 10,949 over | 13,907 |
| G3 | 1 | 188 | 55,306 | 13,827 over | 13,827 |
| G4 | 2 | 138 | 43,795 | 10,949 over | 13,907 |
| G5 | 1 | 188 | 55,306 | 13,827 over | 13,827 |
| G6 | 1 | 188 | 55,306 | 13,827 over | 13,827 |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 2,461,837 | 0.4102 (A1b CHORUS typed_audit_worker) | 0 | 4,000 | 1,013,943 (966,363–1,013,943) | 1,000,000 | estimate_exceeds |
| full | 270,195 | 0.3614 (A1b CHORUS full) | 0 | 128,000 | 225,642 (220,074–225,642) | 1,000,000 | estimate_fits |
| full_readdress | 308,921 | 0.3602 (A1b CHORUS full_readdress) | 0 | 8,000 | 119,269 (113,217–119,269) | 1,000,000 | estimate_fits |
| full_receipt_completion | 1,895,256 | 0.3703 (A1b CHORUS full_receipt_completion) | 0 | 4,000 | 705,774 (687,700–705,774) | 1,000,000 | estimate_fits |
| full_receipt_completion_after_readdress | 1,896,218 | 0.3703 (A1b CHORUS full_receipt_completion) | 8,000 | 4,000 | 714,131 (696,047–714,131) | 1,000,000 | estimate_fits |
| reconcile_full (audit carried at: workers' smallest responses, assembled) | 999,927 | 0.371 (A1b CHORUS reconcile_full) | 0 | 96,000 | 466,954 (453,261–466,954) | 1,000,000 | estimate_fits |
| repair_full | 86,395 | 0.4048 (A1b CHORUS repair_full) | 0 | 96,000 | 130,973 (128,293–130,973) | 1,000,000 | estimate_fits |
| report (audit carried at: workers' smallest responses, assembled) | 1,043,222 | 0.3685 (A1b CHORUS report) | 0 | 96,000 | 480,428 (465,806–480,428) | 850,000 | estimate_fits |
| report_regate (audit carried at: workers' smallest responses, assembled) | 1,041,395 | 0.3686 (A1b CHORUS report_regate) | 96,000 | 96,000 | 575,886 (561,201–575,886) | 850,000 | estimate_fits |
| report_regate_with_v8_report (audit carried at: workers' smallest responses, assembled) | 1,056,408 | 0.3686 (A1b CHORUS report_regate) | 0 | 96,000 | 485,420 (470,523–485,420) | 850,000 | estimate_fits |
| typed_audit_integration (audit carried at: workers' smallest responses) | 2,419,396 | 0.4102 (A1b CHORUS typed_audit_worker) | 26,819 | 4,000 | 1,023,351 (976,591–1,023,351) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 2,110,143 | 0.3804 (A1b CHORUS typed_audit_omission) | 0 | 4,000 | 806,740 (785,836–806,740) | 1,000,000 | estimate_fits |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | 36,579 | 3 | 2 | 1,062,166 | 835,465 | 1,071,102 | 715,114 | 564,649 | 660,136 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep2` | 36,554 | 3 | 2 | 1,098,807 | 872,178 | 1,110,526 | 716,351 | 592,308 | 687,804 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep3` | 39,134 | 11 | 3 | 1,087,301 | 858,202 | 1,099,184 | 720,510 | 585,692 | 681,186 |
| `2026-09-12_claude-opus-5-api-generic-v9_rep1` | 23,643 | 6 | 2 | 1,013,943 | 806,740 | 1,023,351 | 705,774 | 480,428 | 575,886 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (2,461,837 B): m0.6: # Exact typed stage request 1,694,727 (69%); inside: shared.schema 1,486,502 (60%); m0.3: # Shared generation: captured schema owners and complete containing va 717,668 (29%); schema context: classes 615,443 (25%); schema context: owners 101,413 (4%); schema context: nested_owners 50,909 (2%); schema context: owner_typed_tree 48,920 (2%); inside: stage.inventory 45,817 (2%); inside: shared.bundle 42,716 (2%)
- **typed_audit_omission** (2,110,143 B): m0.6: # Exact typed stage request 1,343,061 (64%); inside: payload.schema 1,246,504 (59%); m0.3: # Shared generation: captured schema owners and complete containing va 717,668 (34%); schema context: classes 615,443 (29%); schema context: owners 101,413 (5%); schema context: nested_owners 50,909 (2%); schema context: owner_typed_tree 48,920 (2%); schema context: owner_yaml 42,295 (2%); inside: payload.chunks 40,404 (2%)
- **full_receipt_completion** (1,895,256 B): m2.0: {"input_sha256":{"bundle":"27625709112a7b7796f4e778fcc33df9f908ba95e47 1,583,980 (84%); inside: json.schema 1,542,013 (81%); m0.5: ## API factual and phase policy v2 86,816 (5%); m0.6: # Shared generation: captured schema owners and complete containing va 76,978 (4%); schema context: classes 76,166 (4%); m0.0: # Target class `Dataset` — slot inventory 45,592 (2%); m0.1: # Declared input bundle — <path> 38,088 (2%); inside: json.record_yaml 24,539 (1%); m0.7: # Shared generation: captured generation scope and vocabulary 16,427 (1%)
- **report_regate** (1,041,395 B): m0.14: # Shared generation: captured schema owners and complete containing va 656,834 (63%); schema context: classes 562,536 (54%); schema context: owners 93,486 (9%); m0.5: ## API factual and phase policy v2 79,809 (8%); m0.6: # Audit findings 63,792 (6%); m0.0: # Target class `Dataset` — slot inventory 45,592 (4%); schema context: owner_typed_tree 45,244 (4%); schema context: nested_owners 44,952 (4%); m0.13: # Required source-review inventory 39,892 (4%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 404,121 (fits) | 332,545 (fits) | 413,529 (fits) | 134,799 (fits) | 480,428 (fits) | 575,886 (fits) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 761,464 (fits) | 572,614 (fits) | 770,872 (fits) | 677,572 (fits) | 273,133 (fits) | 368,520 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 385,325 (fits) | 332,545 (fits) | 413,529 (fits) | 134,799 (fits) | 480,428 (fits) | 575,886 (fits) |
| S4: S1 plus owners without their typed trees | 384,052 (fits) | 313,935 (fits) | 393,460 (fits) | 134,799 (fits) | 463,755 (fits) | 559,208 (fits) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 817,134 (fits) | 624,238 (fits) | 826,542 (fits) | 689,420 (fits) | 320,214 (fits) | 415,617 (fits) |
| S6: S1 plus S5 | 207,313 (fits) | 150,043 (fits) | 216,721 (fits) | 118,444 (fits) | 320,214 (fits) | 415,617 (fits) |
| S7: S6 plus owners without their typed trees | 187,244 (fits) | 131,433 (fits) | 196,652 (fits) | 118,444 (fits) | 303,542 (fits) | 398,939 (fits) |

### CM4AI

Primary record `2026-09-04g_claude-opus-5-api-generic-v8_rep1`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict | Assigned inventory per worker B | Typed input, all calls: current / S6 / S7 |
|---|---|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | refused | | | AuditBatchError: indivisible_field_bound | | |
| G2 | 192 / 32,768 / 16 | 3 | 3,024,811 | 1,244,897 | estimate_exceeds | 22,349–30,447 | 5,959,637 over / 2,002,189 / 1,795,951 |
| G3 | 384 / 65,536 / 16 | 2 | 3,032,164 | 1,247,913 | estimate_exceeds | 18,217–63,889 | 4,721,741 over / 1,585,988 / 1,421,607 |
| G4 | 192 / 32,768 / 8 | 3 | 3,024,809 | 1,244,896 | estimate_exceeds | 22,349–30,447 | 5,959,635 over / 2,002,185 / 1,795,946 |
| G5 | 384 / 65,536 / 4 | 2 | 3,032,162 | 1,247,913 | estimate_exceeds | 18,217–63,889 | 4,721,739 over / 1,585,985 / 1,421,603 |
| G6 | 768 / 131,072 / 2 | 1 | 3,035,621 | 1,249,332 | estimate_exceeds | 82,104–82,104 | 3,483,771 / 1,169,712 / 1,047,187 |

"Over" in the last column passes the registered typed `aggregate_input_tokens` (4,000,000). The assigned inventory is what a worker must answer for, one row per path with complete claims, inside its output cap of 4,000 tokens.

Worker output: the smallest response the worker check accepts (`response_floor`), against the registered caps. Tokens are at 4 bytes a token, so they err low, and thinking draws on the same `max_tokens`. "Over" on the largest worker passes its cap (4,000). "Over" on the sum means the workers' smallest responses plus integration's cap (4,000) pass `aggregate_output_tokens` (100,000); the runtime admits a stage only while the output already spent plus that stage's `max_tokens` stays inside it.

| Grid | Workers | Largest assignment (paths) | Largest worker's smallest response B | Its tokens, at least | All workers' smallest responses, tokens at least |
|---|---|---|---|---|---|
| G2 | 3 | 182 | 47,441 | 11,861 over | 30,946 |
| G3 | 2 | 383 | 97,823 | 24,456 over | 30,912 |
| G4 | 3 | 182 | 47,441 | 11,861 over | 30,946 |
| G5 | 2 | 383 | 97,823 | 24,456 over | 30,912 |
| G6 | 1 | 456 | 123,327 | 30,832 over | 30,832 |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 3,024,811 | 0.4102 (no A1b count for CM4AI: higher of CHORUS/AI_READI typed_audit_worker) | 0 | 4,000 | 1,244,897 (1,186,436–1,244,897) | 1,000,000 | estimate_exceeds |
| full | 563,514 | 0.3614 (no A1b count for CM4AI: higher of CHORUS/AI_READI full) | 0 | 128,000 | 331,641 (320,028–331,641) | 1,000,000 | estimate_fits |
| full_readdress | 633,874 | 0.3602 (no A1b count for CM4AI: higher of CHORUS/AI_READI full_readdress) | 0 | 8,000 | 236,313 (223,895–236,313) | 1,000,000 | estimate_fits |
| full_receipt_completion | 2,255,956 | 0.3703 (no A1b count for CM4AI: higher of CHORUS/AI_READI full_receipt_completion) | 0 | 4,000 | 839,334 (817,820–839,334) | 1,000,000 | estimate_fits |
| full_receipt_completion_after_readdress | 2,256,918 | 0.3703 (no A1b count for CM4AI: higher of CHORUS/AI_READI full_receipt_completion) | 8,000 | 4,000 | 847,690 (826,167–847,690) | 1,000,000 | estimate_fits |
| reconcile_full (audit carried at: workers' smallest responses, assembled) | 1,526,612 | 0.371 (no A1b count for CM4AI: higher of CHORUS/AI_READI reconcile_full) | 0 | 96,000 | 662,344 (641,438–662,344) | 1,000,000 | estimate_fits |
| repair_full | 106,453 | 0.4048 (no A1b count for CM4AI: higher of CHORUS/AI_READI repair_full) | 0 | 96,000 | 139,092 (135,790–139,092) | 1,000,000 | estimate_fits |
| report (audit carried at: workers' smallest responses, assembled) | 1,748,080 | 0.3685 (no A1b count for CM4AI: higher of CHORUS/AI_READI report) | 0 | 96,000 | 740,168 (715,667–740,168) | 850,000 | estimate_fits |
| report_regate (audit carried at: workers' smallest responses, assembled) | 1,746,253 | 0.3686 (no A1b count for CM4AI: higher of CHORUS/AI_READI report_regate) | 96,000 | 96,000 | 835,715 (811,091–835,715) | 850,000 | estimate_fits |
| report_regate_with_v8_report (audit carried at: workers' smallest responses, assembled) | 1,756,967 | 0.3686 (no A1b count for CM4AI: higher of CHORUS/AI_READI report_regate) | 0 | 96,000 | 743,665 (718,889–743,665) | 850,000 | estimate_fits |
| typed_audit_integration (audit carried at: workers' smallest responses) | 2,928,342 | 0.4102 (no A1b count for CM4AI: higher of CHORUS/AI_READI typed_audit_worker) | 54,779 | 4,000 | 1,260,100 (1,203,504–1,260,100) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 2,582,736 | 0.3804 (no A1b count for CM4AI: higher of CHORUS/AI_READI typed_audit_omission) | 0 | 4,000 | 986,524 (960,938–986,524) | 1,000,000 | estimate_fits |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04g_claude-opus-5-api-generic-v8_rep1` | 41,203 | 2 | 3 | 1,244,897 | 986,524 | 1,260,100 | 839,334 | 740,168 | 835,715 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep2` | 39,830 | 11 | 3 | 1,276,234 | 1,014,926 | 1,291,782 | 837,674 | 759,692 | 855,246 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep3` | 44,850 | 9 | 3 | 1,276,331 | 1,013,541 | 1,291,380 | 846,020 | 756,248 | 851,800 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (3,024,811 B): m0.6: # Exact typed stage request 2,122,987 (70%); inside: shared.schema 1,486,502 (49%); m0.3: # Shared generation: captured schema owners and complete containing va 852,312 (28%); schema context: classes 644,761 (21%); inside: shared.bundle 354,248 (12%); schema context: owners 206,739 (7%); schema context: nested_owners 114,564 (4%); schema context: owner_typed_tree 102,029 (3%); inside: stage.inventory 98,721 (3%)
- **typed_audit_omission** (2,582,736 B): m0.6: # Exact typed stage request 1,680,940 (65%); inside: payload.schema 1,246,504 (48%); m0.3: # Shared generation: captured schema owners and complete containing va 852,312 (33%); schema context: classes 644,761 (25%); inside: payload.chunks 341,147 (13%); schema context: owners 206,739 (8%); schema context: nested_owners 114,564 (4%); schema context: owner_typed_tree 102,029 (4%); schema context: owner_yaml 82,010 (3%)
- **full_receipt_completion** (2,255,956 B): m2.0: {"input_sha256":{"bundle":"5f81bb53f43f9ec6debc3ab7297bb3897d30c675888 1,619,727 (72%); inside: json.schema 1,542,013 (68%); m0.1: # Declared input bundle — <path> 329,577 (15%); m0.5: ## API factual and phase policy v2 88,133 (4%); m0.6: # Shared generation: captured schema owners and complete containing va 76,978 (3%); schema context: classes 76,166 (3%); m0.0: # Target class `Dataset` — slot inventory 45,592 (2%); inside: json.record_yaml 43,181 (2%); inside: json.receipt_yaml 28,640 (1%)
- **report_regate** (1,746,253 B): m0.14: # Shared generation: captured schema owners and complete containing va 856,373 (49%); schema context: classes 644,761 (37%); m0.1: # Declared input bundle — <path> 329,577 (19%); schema context: owners 210,800 (12%); m0.6: # Audit findings 144,428 (8%); schema context: nested_owners 116,544 (7%); schema context: owner_typed_tree 104,041 (6%); m0.13: # Required source-review inventory 92,682 (5%); schema context: owner_yaml 83,913 (5%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 635,075 (fits) | 512,329 (fits) | 650,279 (fits) | 268,358 (fits) | 740,168 (fits) | 835,715 (fits) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 980,390 (fits) | 741,244 (fits) | 995,594 (fits) | 811,131 (fits) | 502,574 (fits) | 598,039 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 594,576 (fits) | 512,329 (fits) | 650,279 (fits) | 268,358 (fits) | 740,168 (fits) | 835,715 (fits) |
| S4: S1 plus owners without their typed trees | 593,219 (fits) | 473,515 (fits) | 608,422 (fits) | 268,358 (fits) | 701,829 (fits) | 797,363 (fits) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 1,033,023 (exceeds) | 790,051 (fits) | 1,048,227 (exceeds) | 822,980 (fits) | 549,852 (fits) | 645,333 (fits) |
| S6: S1 plus S5 | 423,202 (fits) | 315,856 (fits) | 438,405 (fits) | 252,004 (fits) | 549,852 (fits) | 645,333 (fits) |
| S7: S6 plus owners without their typed trees | 381,345 (fits) | 277,043 (fits) | 396,549 (fits) | 252,004 (fits) | 511,512 (fits) | 606,981 (fits) |

### KIDS_FIRST

Proxy: AI_READI's records with KIDS_FIRST's own bundle and chunk manifest, a root-only draft context synthesized by the A3 builder, and a minimal receipt; an estimate for a run that has no record yet.

Primary record `2026-09-04g_claude-opus-5-api-generic-v8_rep2`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict | Assigned inventory per worker B | Typed input, all calls: current / S6 / S7 |
|---|---|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | refused | | | AuditBatchError: indivisible_field_bound | | |
| G2 | 192 / 32,768 / 16 | 6 | 3,888,424 | 1,599,185 | estimate_exceeds | 11,653–32,258 | 12,442,307 over / 5,253,326 over / 4,609,584 over |
| G3 | 384 / 65,536 / 16 | 3 | 3,893,229 | 1,601,156 | estimate_exceeds | 33,927–65,061 | 7,665,477 over / 3,231,633 / 2,831,508 |
| G4 | 192 / 32,768 / 8 | 6 | 3,888,422 | 1,599,184 | estimate_exceeds | 11,653–32,258 | 12,442,302 over / 5,253,319 over / 4,609,576 over |
| G5 | 384 / 65,536 / 4 | 3 | 3,893,227 | 1,601,155 | estimate_exceeds | 33,927–65,061 | 7,665,472 over / 3,231,630 / 2,831,504 |
| G6 | 768 / 131,072 / 2 | 2 | 3,902,758 | 1,605,065 | estimate_exceeds | 13,524–129,371 | 6,073,243 over / 2,557,780 / 2,238,860 |

"Over" in the last column passes the registered typed `aggregate_input_tokens` (4,000,000). The assigned inventory is what a worker must answer for, one row per path with complete claims, inside its output cap of 4,000 tokens.

Worker output: the smallest response the worker check accepts (`response_floor`), against the registered caps. Tokens are at 4 bytes a token, so they err low, and thinking draws on the same `max_tokens`. "Over" on the largest worker passes its cap (4,000). "Over" on the sum means the workers' smallest responses plus integration's cap (4,000) pass `aggregate_output_tokens` (100,000); the runtime admits a stage only while the output already spent plus that stage's `max_tokens` stays inside it.

| Grid | Workers | Largest assignment (paths) | Largest worker's smallest response B | Its tokens, at least | All workers' smallest responses, tokens at least |
|---|---|---|---|---|---|
| G2 | 6 | 171 | 45,854 | 11,464 over | 48,906 |
| G3 | 3 | 277 | 89,922 | 22,481 over | 48,731 |
| G4 | 6 | 171 | 45,854 | 11,464 over | 48,906 |
| G5 | 3 | 277 | 89,922 | 22,481 over | 48,731 |
| G6 | 2 | 478 | 173,856 | 43,464 over | 48,698 |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 3,888,424 | 0.4102 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI typed_audit_worker) | 0 | 4,000 | 1,599,185 (1,524,033–1,599,185) | 1,000,000 | estimate_exceeds |
| full | 783,618 | 0.3614 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI full) | 0 | 128,000 | 411,182 (395,033–411,182) | 1,000,000 | estimate_fits |
| full_readdress | 886,652 | 0.3602 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI full_readdress) | 0 | 8,000 | 327,361 (309,990–327,361) | 1,000,000 | estimate_fits |
| full_receipt_completion | 2,553,209 | 0.3703 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI full_receipt_completion) | 0 | 4,000 | 949,401 (925,052–949,401) | 1,000,000 | estimate_fits |
| full_receipt_completion_after_readdress | 2,554,171 | 0.3703 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI full_receipt_completion) | 8,000 | 4,000 | 957,757 (933,399–957,757) | 1,000,000 | estimate_fits |
| reconcile_full (audit carried at: workers' smallest responses, assembled) | 2,373,470 | 0.371 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI reconcile_full) | 0 | 96,000 | 976,512 (944,009–976,512) | 1,000,000 | estimate_fits |
| repair_full | 155,010 | 0.4048 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI repair_full) | 0 | 96,000 | 158,748 (153,940–158,748) | 1,000,000 | estimate_fits |
| report (audit carried at: workers' smallest responses, assembled) | 2,819,883 | 0.3685 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI report) | 0 | 96,000 | 1,135,129 (1,095,604–1,135,129) | 850,000 | estimate_exceeds |
| report_regate (audit carried at: workers' smallest responses, assembled) | 2,818,056 | 0.3686 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI report_regate) | 96,000 | 96,000 | 1,230,811 (1,191,072–1,230,811) | 850,000 | estimate_exceeds |
| report_regate_with_v8_report (audit carried at: workers' smallest responses, assembled) | 2,836,391 | 0.3686 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI report_regate) | 0 | 96,000 | 1,141,569 (1,101,572–1,141,569) | 850,000 | estimate_exceeds |
| typed_audit_integration (audit carried at: workers' smallest responses) | 3,727,527 | 0.4102 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI typed_audit_worker) | 84,248 | 4,000 | 1,617,427 (1,545,385–1,617,427) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 3,327,460 | 0.3804 (no A1b count for KIDS_FIRST: higher of CHORUS/AI_READI typed_audit_omission) | 0 | 4,000 | 1,269,832 (1,236,868–1,269,832) | 1,000,000 | estimate_exceeds |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04g_claude-opus-5-api-generic-v8_rep1` | 72,954 | 5 | 4 | 1,503,462 | 1,197,605 | 1,521,425 | 934,050 | 1,033,114 | 1,128,761 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep2` | 94,145 | 8 | 6 | 1,599,185 | 1,269,832 | 1,617,427 | 949,401 | 1,135,129 | 1,230,811 |
| `2026-09-04g_claude-opus-5-api-generic-v8_rep3` | 80,149 | 10 | 4 | 1,542,181 | 1,231,964 | 1,559,481 | 938,677 | 1,046,901 | 1,142,553 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (3,888,424 B): m0.6: # Exact typed stage request 2,496,031 (64%); inside: shared.schema 1,486,502 (38%); m0.3: # Shared generation: captured schema owners and complete containing va 1,351,652 (35%); schema context: classes 949,673 (24%); inside: shared.bundle 574,250 (15%); schema context: owners 401,167 (10%); schema context: nested_owners 203,349 (5%); schema context: owner_typed_tree 197,947 (5%); schema context: owner_yaml 183,437 (5%)
- **typed_audit_omission** (3,327,460 B): m0.6: # Exact typed stage request 1,935,095 (58%); m0.3: # Shared generation: captured schema owners and complete containing va 1,351,652 (41%); inside: payload.schema 1,246,504 (37%); schema context: classes 949,673 (29%); inside: payload.chunks 563,582 (17%); schema context: owners 401,167 (12%); schema context: nested_owners 203,349 (6%); schema context: owner_typed_tree 197,947 (6%); schema context: owner_yaml 183,437 (6%)
- **full_receipt_completion** (2,553,209 B): m2.0: {"input_sha256":{"bundle":"cc45c89548158a7a909699fbf1f75e6cc88c32ac848 1,664,202 (65%); inside: json.schema 1,542,013 (60%); m0.1: # Declared input bundle — <path> 549,154 (22%); inside: json.record_yaml 97,505 (4%); m0.5: ## API factual and phase policy v2 97,239 (4%); m0.6: # Shared generation: captured schema owners and complete containing va 76,978 (3%); schema context: classes 76,166 (3%); m0.0: # Target class `Dataset` — slot inventory 42,964 (2%); inside: json.requested_paths 15,728 (1%)
- **report_regate** (2,818,056 B): m0.14: # Shared generation: captured schema owners and complete containing va 1,361,964 (48%); schema context: classes 936,972 (33%); m0.1: # Declared input bundle — <path> 549,154 (19%); schema context: owners 424,180 (15%); m0.6: # Audit findings 218,230 (8%); schema context: nested_owners 213,250 (8%); schema context: owner_typed_tree 209,695 (7%); schema context: owner_yaml 194,815 (7%); m0.13: # Required source-review inventory 164,691 (6%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 989,363 (fits) | 795,637 (fits) | 1,007,605 (exceeds) | 378,425 (fits) | 1,135,129 (exceeds) | 1,230,811 (exceeds) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 1,209,592 (exceeds) | 908,557 (fits) | 1,227,833 (exceeds) | 921,198 (fits) | 789,854 (fits) | 885,418 (exceeds) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 922,380 (fits) | 795,637 (fits) | 1,007,605 (exceeds) | 378,425 (fits) | 1,135,129 (exceeds) | 1,230,811 (exceeds) |
| S4: S1 plus owners without their typed trees | 908,158 (fits) | 720,334 (fits) | 926,399 (fits) | 378,425 (fits) | 1,057,856 (exceeds) | 1,153,512 (exceeds) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 1,290,627 (exceeds) | 983,702 (fits) | 1,308,869 (exceeds) | 933,046 (fits) | 861,976 (exceeds) | 957,564 (exceeds) |
| S6: S1 plus S5 | 680,805 (fits) | 509,508 (fits) | 699,047 (fits) | 362,071 (fits) | 861,976 (exceeds) | 957,564 (exceeds) |
| S7: S6 plus owners without their typed trees | 599,600 (fits) | 434,205 (fits) | 617,841 (fits) | 362,071 (fits) | 784,703 (fits) | 880,265 (exceeds) |

### VOICE

Primary record `2026-09-04f_claude-opus-5-api-generic-v8_rep1`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict | Assigned inventory per worker B | Typed input, all calls: current / S6 / S7 |
|---|---|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | 8 | 3,514,840 | 1,445,926 | estimate_exceeds | 3,790–15,415 | 14,150,150 over / 5,043,074 over / 4,478,159 over |
| G2 | 192 / 32,768 / 16 | 4 | 3,517,814 | 1,447,146 | estimate_exceeds | 4,451–32,290 | 8,387,910 over / 2,987,126 / 2,649,830 |
| G3 | 384 / 65,536 / 16 | 2 | 3,523,909 | 1,449,647 | estimate_exceeds | 36,732–62,809 | 5,506,767 over / 1,959,126 / 1,735,643 |
| G4 | 192 / 32,768 / 8 | 4 | 3,517,812 | 1,447,145 | estimate_exceeds | 4,451–32,290 | 8,387,904 over / 2,987,122 / 2,649,827 |
| G5 | 384 / 65,536 / 4 | 2 | 3,523,907 | 1,449,646 | estimate_exceeds | 36,732–62,809 | 5,506,763 over / 1,959,123 / 1,735,639 |
| G6 | 768 / 131,072 / 2 | 1 | 3,531,122 | 1,452,606 | estimate_exceeds | 99,539–99,539 | 4,066,180 over / 1,445,112 / 1,278,534 |

"Over" in the last column passes the registered typed `aggregate_input_tokens` (4,000,000). The assigned inventory is what a worker must answer for, one row per path with complete claims, inside its output cap of 4,000 tokens.

Worker output: the smallest response the worker check accepts (`response_floor`), against the registered caps. Tokens are at 4 bytes a token, so they err low, and thinking draws on the same `max_tokens`. "Over" on the largest worker passes its cap (4,000). "Over" on the sum means the workers' smallest responses plus integration's cap (4,000) pass `aggregate_output_tokens` (100,000); the runtime admits a stage only while the output already spent plus that stage's `max_tokens` stays inside it.

| Grid | Workers | Largest assignment (paths) | Largest worker's smallest response B | Its tokens, at least | All workers' smallest responses, tokens at least |
|---|---|---|---|---|---|
| G1 | 8 | 77 | 22,803 | 5,701 over | 35,190 |
| G2 | 4 | 142 | 45,891 | 11,473 over | 35,042 |
| G3 | 2 | 278 | 87,673 | 21,919 over | 34,956 |
| G4 | 4 | 142 | 45,891 | 11,473 over | 35,042 |
| G5 | 2 | 278 | 87,673 | 21,919 over | 34,956 |
| G6 | 1 | 426 | 139,612 | 34,903 over | 34,903 |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 3,517,814 | 0.4102 (no A1b count for VOICE: higher of CHORUS/AI_READI typed_audit_worker) | 0 | 4,000 | 1,447,146 (1,379,157–1,447,146) | 1,000,000 | estimate_exceeds |
| full | 617,826 | 0.3614 (no A1b count for VOICE: higher of CHORUS/AI_READI full) | 0 | 128,000 | 351,268 (338,536–351,268) | 1,000,000 | estimate_fits |
| full_readdress | 721,550 | 0.3602 (no A1b count for VOICE: higher of CHORUS/AI_READI full_readdress) | 0 | 8,000 | 267,893 (253,757–267,893) | 1,000,000 | estimate_fits |
| full_receipt_completion | 2,378,814 | 0.3703 (no A1b count for VOICE: higher of CHORUS/AI_READI full_receipt_completion) | 0 | 4,000 | 884,826 (862,140–884,826) | 1,000,000 | estimate_fits |
| full_receipt_completion_after_readdress | 2,379,776 | 0.3703 (no A1b count for VOICE: higher of CHORUS/AI_READI full_receipt_completion) | 8,000 | 4,000 | 893,182 (870,487–893,182) | 1,000,000 | estimate_fits |
| reconcile_full (audit carried at: workers' smallest responses, assembled) | 1,995,697 | 0.371 (no A1b count for VOICE: higher of CHORUS/AI_READI reconcile_full) | 0 | 96,000 | 836,366 (809,036–836,366) | 1,000,000 | estimate_fits |
| repair_full | 129,264 | 0.4048 (no A1b count for VOICE: higher of CHORUS/AI_READI repair_full) | 0 | 96,000 | 148,326 (144,316–148,326) | 1,000,000 | estimate_fits |
| report (audit carried at: workers' smallest responses, assembled) | 2,306,813 | 0.3685 (no A1b count for VOICE: higher of CHORUS/AI_READI report) | 0 | 96,000 | 946,062 (913,729–946,062) | 850,000 | estimate_exceeds |
| report_regate (audit carried at: workers' smallest responses, assembled) | 2,304,986 | 0.3686 (no A1b count for VOICE: higher of CHORUS/AI_READI report_regate) | 96,000 | 96,000 | 1,041,679 (1,009,176–1,041,679) | 850,000 | estimate_exceeds |
| report_regate_with_v8_report (audit carried at: workers' smallest responses, assembled) | 2,320,771 | 0.3686 (no A1b count for VOICE: higher of CHORUS/AI_READI report_regate) | 0 | 96,000 | 951,498 (918,772–951,498) | 850,000 | estimate_exceeds |
| typed_audit_integration (audit carried at: workers' smallest responses) | 3,405,981 | 0.4102 (no A1b count for VOICE: higher of CHORUS/AI_READI typed_audit_worker) | 61,500 | 4,000 | 1,462,768 (1,396,940–1,462,768) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 3,046,718 | 0.3804 (no A1b count for VOICE: higher of CHORUS/AI_READI typed_audit_omission) | 0 | 4,000 | 1,163,032 (1,132,849–1,163,032) | 1,000,000 | estimate_exceeds |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | 62,329 | 10 | 4 | 1,447,146 | 1,163,032 | 1,462,768 | 884,826 | 946,062 | 1,041,679 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep2` | 67,431 | 9 | 4 | 1,430,519 | 1,147,762 | 1,445,064 | 887,656 | 908,366 | 1,003,970 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep3` | 75,633 | 8 | 4 | 1,513,279 | 1,214,924 | 1,529,703 | 891,601 | 1,006,401 | 1,102,039 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (3,517,814 B): m0.6: # Exact typed stage request 2,235,436 (64%); inside: shared.schema 1,486,502 (42%); m0.3: # Shared generation: captured schema owners and complete containing va 1,232,804 (35%); schema context: classes 949,641 (27%); inside: shared.bundle 400,770 (11%); schema context: owners 282,351 (8%); schema context: nested_owners 149,957 (4%); schema context: owner_typed_tree 138,712 (4%); schema context: owner_yaml 124,041 (4%)
- **typed_audit_omission** (3,046,718 B): m0.6: # Exact typed stage request 1,764,368 (58%); inside: payload.schema 1,246,504 (41%); m0.3: # Shared generation: captured schema owners and complete containing va 1,232,804 (40%); schema context: classes 949,641 (31%); inside: payload.chunks 391,486 (13%); schema context: owners 282,351 (9%); schema context: nested_owners 149,957 (5%); schema context: owner_typed_tree 138,712 (5%); schema context: owner_yaml 124,041 (4%)
- **full_receipt_completion** (2,378,814 B): m2.0: {"input_sha256":{"bundle":"7c4f71ab2e85d70396e479d39cb5db9454bd9f13c72 1,654,909 (70%); inside: json.schema 1,542,013 (65%); m0.1: # Declared input bundle — <path> 383,053 (16%); m0.5: ## API factual and phase policy v2 88,276 (4%); m0.6: # Shared generation: captured schema owners and complete containing va 76,978 (3%); schema context: classes 76,166 (3%); inside: json.record_yaml 64,857 (3%); m0.0: # Target class `Dataset` — slot inventory 45,592 (2%); inside: json.receipt_yaml 40,791 (2%)
- **report_regate** (2,304,986 B): m0.14: # Shared generation: captured schema owners and complete containing va 1,251,114 (54%); schema context: classes 961,830 (42%); m0.1: # Declared input bundle — <path> 383,053 (17%); schema context: owners 288,472 (13%); m0.6: # Audit findings 157,324 (7%); schema context: nested_owners 151,567 (7%); schema context: owner_typed_tree 141,684 (6%); schema context: owner_yaml 127,709 (6%); m0.13: # Required source-review inventory 110,667 (5%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 837,324 (fits) | 688,837 (fits) | 852,946 (fits) | 313,850 (fits) | 946,062 (exceeds) | 1,041,679 (exceeds) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 1,057,566 (exceeds) | 801,770 (fits) | 1,073,188 (exceeds) | 856,623 (fits) | 591,627 (fits) | 687,123 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 790,111 (fits) | 688,837 (fits) | 852,946 (fits) | 313,850 (fits) | 946,062 (exceeds) | 1,041,679 (exceeds) |
| S4: S1 plus owners without their typed trees | 780,419 (fits) | 636,068 (fits) | 796,041 (fits) | 313,850 (fits) | 893,851 (exceeds) | 989,451 (exceeds) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 1,130,395 (exceeds) | 869,305 (fits) | 1,146,017 (exceeds) | 868,471 (fits) | 657,647 (fits) | 753,166 (fits) |
| S6: S1 plus S5 | 520,574 (fits) | 395,110 (fits) | 536,195 (fits) | 297,496 (fits) | 657,647 (fits) | 753,166 (fits) |
| S7: S6 plus owners without their typed trees | 463,668 (fits) | 342,342 (fits) | 479,290 (fits) | 297,496 (fits) | 605,436 (fits) | 700,937 (fits) |

### VOICE_PEDIATRIC

Proxy: VOICE's records with VOICE_PEDIATRIC's own bundle and chunk manifest, its own context, and a minimal receipt; an estimate for a run that has no record yet.

Primary record `2026-09-04f_claude-opus-5-api-generic-v8_rep1`.

| Grid | max_paths / inventory B / max_workers | Workers | Largest worker B | Est. in flight | Verdict | Assigned inventory per worker B | Typed input, all calls: current / S6 / S7 |
|---|---|---|---|---|---|---|---|
| G1 | 96 / 16,384 / 16 | 8 | 3,286,810 | 1,352,379 | estimate_exceeds | 3,790–15,415 | 13,225,758 over / 4,118,684 over / 3,553,768 |
| G2 | 192 / 32,768 / 16 | 4 | 3,289,784 | 1,353,599 | estimate_exceeds | 4,451–32,290 | 7,837,706 over / 2,436,922 / 2,099,629 |
| G3 | 384 / 65,536 / 16 | 2 | 3,295,879 | 1,356,100 | estimate_exceeds | 36,732–62,809 | 5,143,657 over / 1,596,016 / 1,372,533 |
| G4 | 192 / 32,768 / 8 | 4 | 3,289,782 | 1,353,598 | estimate_exceeds | 4,451–32,290 | 7,837,700 over / 2,436,919 / 2,099,623 |
| G5 | 384 / 65,536 / 4 | 2 | 3,295,877 | 1,356,099 | estimate_exceeds | 36,732–62,809 | 5,143,653 over / 1,596,014 / 1,372,529 |
| G6 | 768 / 131,072 / 2 | 1 | 3,303,092 | 1,359,059 | estimate_exceeds | 99,539–99,539 | 3,796,617 / 1,175,549 / 1,008,971 |

"Over" in the last column passes the registered typed `aggregate_input_tokens` (4,000,000). The assigned inventory is what a worker must answer for, one row per path with complete claims, inside its output cap of 4,000 tokens.

Worker output: the smallest response the worker check accepts (`response_floor`), against the registered caps. Tokens are at 4 bytes a token, so they err low, and thinking draws on the same `max_tokens`. "Over" on the largest worker passes its cap (4,000). "Over" on the sum means the workers' smallest responses plus integration's cap (4,000) pass `aggregate_output_tokens` (100,000); the runtime admits a stage only while the output already spent plus that stage's `max_tokens` stays inside it.

| Grid | Workers | Largest assignment (paths) | Largest worker's smallest response B | Its tokens, at least | All workers' smallest responses, tokens at least |
|---|---|---|---|---|---|
| G1 | 8 | 77 | 22,803 | 5,701 over | 35,190 |
| G2 | 4 | 142 | 45,891 | 11,473 over | 35,042 |
| G3 | 2 | 278 | 87,673 | 21,919 over | 34,956 |
| G4 | 4 | 142 | 45,891 | 11,473 over | 35,042 |
| G5 | 2 | 278 | 87,673 | 21,919 over | 34,956 |
| G6 | 1 | 426 | 139,612 | 34,903 over | 34,903 |

Every request at G2 (largest worker shown for the typed workers):

| Request | Payload B | Tokens/B (basis) | Placeholder tok | max_tokens | Est. in flight (range) | Ceiling | Verdict |
|---|---|---|---|---|---|---|---|
| typed_audit_worker (largest) | 3,289,784 | 0.4102 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI typed_audit_worker) | 0 | 4,000 | 1,353,599 (1,290,017–1,353,599) | 1,000,000 | estimate_exceeds |
| full | 442,248 | 0.3614 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI full) | 0 | 128,000 | 287,818 (278,705–287,818) | 1,000,000 | estimate_fits |
| full_readdress | 508,240 | 0.3602 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI full_readdress) | 0 | 8,000 | 191,062 (181,105–191,062) | 1,000,000 | estimate_fits |
| full_receipt_completion | 2,134,857 | 0.3703 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI full_receipt_completion) | 0 | 4,000 | 794,494 (774,134–794,494) | 1,000,000 | estimate_fits |
| full_receipt_completion_after_readdress | 2,135,819 | 0.3703 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI full_receipt_completion) | 8,000 | 4,000 | 802,850 (782,481–802,850) | 1,000,000 | estimate_fits |
| reconcile_full (audit carried at: workers' smallest responses, assembled) | 1,820,119 | 0.371 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI reconcile_full) | 0 | 96,000 | 771,230 (746,304–771,230) | 1,000,000 | estimate_fits |
| repair_full | 129,128 | 0.4048 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI repair_full) | 0 | 96,000 | 148,271 (144,265–148,271) | 1,000,000 | estimate_fits |
| report (audit carried at: workers' smallest responses, assembled) | 2,131,235 | 0.3685 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI report) | 0 | 96,000 | 881,361 (851,489–881,361) | 850,000 | estimate_exceeds |
| report_regate (audit carried at: workers' smallest responses, assembled) | 2,129,408 | 0.3686 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI report_regate) | 96,000 | 96,000 | 976,957 (946,929–976,957) | 850,000 | estimate_exceeds |
| report_regate_with_v8_report (audit carried at: workers' smallest responses, assembled) | 2,145,193 | 0.3686 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI report_regate) | 0 | 96,000 | 886,775 (856,525–886,775) | 850,000 | estimate_exceeds |
| typed_audit_integration (audit carried at: workers' smallest responses) | 3,177,951 | 0.4102 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI typed_audit_worker) | 61,500 | 4,000 | 1,369,221 (1,307,800–1,369,221) | 1,000,000 | estimate_exceeds |
| typed_audit_omission | 2,829,934 | 0.3804 (no A1b count for VOICE_PEDIATRIC: higher of CHORUS/AI_READI typed_audit_omission) | 0 | 4,000 | 1,080,563 (1,052,528–1,080,563) | 1,000,000 | estimate_exceeds |

Record sensitivity at G2 (estimated tokens in flight):

| Record | Staged full B | Edits | Workers | Largest worker | Omission | Integration | Receipt completion | Report | Regate (cap) |
|---|---|---|---|---|---|---|---|---|---|
| `2026-09-04f_claude-opus-5-api-generic-v8_rep1` | 62,329 | 10 | 4 | 1,353,599 | 1,080,563 | 1,369,221 | 794,494 | 881,361 | 976,957 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep2` | 67,431 | 9 | 4 | 1,337,447 | 1,065,708 | 1,351,992 | 796,920 | 843,665 | 939,248 |
| `2026-09-04f_claude-opus-5-api-generic-v8_rep3` | 75,633 | 8 | 4 | 1,422,906 | 1,134,584 | 1,439,330 | 804,911 | 941,700 | 1,037,316 |

What the largest requests carry (bytes, by emptying each part):

- **typed_audit_worker (largest)** (3,289,784 B): m0.6: # Exact typed stage request 2,007,292 (61%); inside: shared.schema 1,486,502 (45%); m0.3: # Shared generation: captured schema owners and complete containing va 1,232,804 (37%); schema context: classes 949,641 (29%); schema context: owners 282,351 (9%); inside: shared.bundle 218,527 (7%); schema context: nested_owners 149,957 (5%); schema context: owner_typed_tree 138,712 (4%); schema context: owner_yaml 124,041 (4%)
- **typed_audit_omission** (2,829,934 B): m0.6: # Exact typed stage request 1,547,470 (55%); inside: payload.schema 1,246,504 (44%); m0.3: # Shared generation: captured schema owners and complete containing va 1,232,804 (44%); schema context: classes 949,641 (34%); schema context: owners 282,351 (10%); inside: payload.chunks 214,030 (8%); schema context: nested_owners 149,957 (5%); schema context: owner_typed_tree 138,712 (5%); schema context: owner_yaml 124,041 (4%)
- **full_receipt_completion** (2,134,857 B): m2.0: {"input_sha256":{"bundle":"eb823708a16342a3b12cc1dabb57529cea4f95fd596 1,624,262 (76%); inside: json.schema 1,542,013 (72%); m0.1: # Declared input bundle — <path> 209,634 (10%); m0.4: ## API factual and phase policy v2 87,245 (4%); m0.5: # Shared generation: captured schema owners and complete containing va 76,978 (4%); schema context: classes 76,166 (4%); inside: json.record_yaml 64,857 (3%); m0.0: # Target class `Dataset` — slot inventory 45,592 (2%); m0.6: # Shared generation: captured generation scope and vocabulary 16,442 (1%)
- **report_regate** (2,129,408 B): m0.13: # Shared generation: captured schema owners and complete containing va 1,251,114 (59%); schema context: classes 961,830 (45%); schema context: owners 288,472 (14%); m0.1: # Declared input bundle — <path> 209,634 (10%); m0.5: # Audit findings 157,324 (7%); schema context: nested_owners 151,567 (7%); schema context: owner_typed_tree 141,684 (7%); schema context: owner_yaml 127,709 (6%); m0.12: # Required source-review inventory 110,667 (5%)

Compaction options (protocol changes nobody has made; estimated tokens in flight after removing the parts, with the request's own tokens-per-byte ratio):

| Option | typed_audit_worker (largest) | typed_audit_omission | typed_audit_integration | full_receipt_completion | report | report_regate |
|---|---|---|---|---|---|---|
| S1: schema carried once: the typed request's own schema copy dropped, the schema context kept | 743,777 (fits) | 606,368 (fits) | 759,399 (fits) | 223,518 (fits) | 881,361 (exceeds) | 976,957 (exceeds) |
| S2: schema carried once: the schema context's induced-slot `classes` dropped, the typed copy kept | 964,019 (fits) | 719,301 (fits) | 979,641 (fits) | 766,291 (fits) | 526,926 (fits) | 622,400 (fits) |
| S3: S1 plus the full-record inventory repeated in every worker dropped | 696,564 (fits) | 606,368 (fits) | 759,399 (fits) | 223,518 (fits) | 881,361 (exceeds) | 976,957 (exceeds) |
| S4: S1 plus owners without their typed trees | 686,872 (fits) | 553,599 (fits) | 702,494 (fits) | 223,518 (fits) | 829,151 (fits) | 924,728 (exceeds) |
| S5: induced-slot definitions trimmed to name, description, range, cardinality and inlining | 1,036,848 (exceeds) | 786,836 (fits) | 1,052,470 (exceeds) | 778,139 (fits) | 592,946 (fits) | 688,443 (fits) |
| S6: S1 plus S5 | 427,027 (fits) | 312,641 (fits) | 442,648 (fits) | 207,163 (fits) | 592,946 (fits) | 688,443 (fits) |
| S7: S6 plus owners without their typed trees | 370,122 (fits) | 259,873 (fits) | 385,743 (fits) | 207,163 (fits) | 540,736 (fits) | 636,214 (fits) |

