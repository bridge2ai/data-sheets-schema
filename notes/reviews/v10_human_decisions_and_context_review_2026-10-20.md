# Human Review & Owner Decision Package for `generic_v10` D4D Generation and Evaluation

- **Date**: 2026-10-20
- **Status**: `PENDING HUMAN REVIEW` (no paid API, native, or LLM evaluation runs have been launched; no agent-invented pre-approval is claimed)
- **Branches & Lanes**:
  - **AGY + Codex Lane X1 Integrated**: `/private/tmp/d4d-v10-readiness-20261019` (`feat/v10-preflight-scripts`, PR `#5095`, plus `codex/track-e-eval-runner`)
  - **Codex Lane X2**: `/private/tmp/d4d-codex-track-n-20261020` (`codex/track-n-direct-adapter`, HEAD `3bcde8004`)
  - **Claude Lane C1**: `/private/tmp/d4d-sizing-recovery-20261019` (`fix/5072-offline-sizing-recovery`, PR `#5087`, HEAD `0d45c1ec8`)
  - **Claude Lane C2**: `/private/tmp/d4d-claude-track-p-20261020` (`claude/track-p-analysis-plan`, HEAD `705ac83de`)
- **Related Issues**: `#1763`, `#1849`, `#2911`, `#2912`, `#2914`, `#2917`, `#2918`, `#2920`, `#2921`, `#2922`, `#2926`, `#2929`, `#2932`, `#4345`, `#4757`, `#4758`, `#4759`, `#4760`, `#4761`, `#4762`, `#4829`, `#4830`, `#5042`, `#5072`

---

## 1. Canonical Project Evaluation Contexts (`Step E3` / `#2912`) — `PENDING HUMAN REVIEW`

All 6 project applicability context files under `data/context/` (`schema_version: d4d-evaluation-context-1`) have been prepared and verified against `src/data_sheets_schema/evaluation_context.py` and `tests/test_evaluation_context_files.py`.

### 1.1 Context Files, Digests, and Rubric Denominator Calibration

| Project | Context File | Normalized Context Digest (`SHA-256`) | `human_subjects` | `regulated_access` | `shared_dataset` | `data_collection` | `data_processing` | `processing_software` | `ml_training_dataset` | Rubric 10 Applicable (`max`) | Rubric 20 Applicable (`max`) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **AI_READI** | `data/context/ai_readi_context.yaml` | `5fc990f05f39be4b4e86215c099c86c7300680b2709064bc379490253353a83b` | `true` | `true` | `true` | `true` | `true` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **CHORUS** | `data/context/chorus_context.yaml` | `126982f8a89f36a06f992304f527c03c4fa249ebff91886f361b8d3f1a7f08e2` | `true` | `true` | `true` | `true` | `true` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **CM4AI** | `data/context/cm4ai_context.yaml` | `97047473e7e4f2b8c7fa78169f52be33be2a67e70a287ca1d4c9b2e66540eb76` | `false` | `false` | `true` | `true` | `true` | `true` | `true` | `44 / 50` (`44.0`) | `17 / 20` (`78.0`) |
| **VOICE** | `data/context/voice_context.yaml` | `0dc82e8f96455552ed52feef1f6a00dd0cfbd691bed08019741ce81999b7b2e9` | `true` | `true` | `true` | `true` | `true` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **VOICE_PEDIATRIC** | `data/context/voice_pediatric_context.yaml` | `f934c7151d85b309ae33d76bb03473b485d0c5f81f38cb28a931756cccecdb2c` | `true` | `true` | `true` | `true` | `true` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **KIDS_FIRST** | `data/context/kids_first_context.yaml` | `e75fffe74fa0350f9fc46e90ca3ecaab7b6d5855eca3ce0e182afb70377e207d` | `true` | `true` | `true` | `true` | `true` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |

### 1.2 The 5 Hold Questions Requiring Human Confirmation (`#2912`)

1. **`CM4AI` `human_subjects: false` and `regulated_access: false`**:
   - **Proposed Setting**: `human_subjects: false`, `regulated_access: false`.
   - **Rationale**: CM4AI generates multiscale cell-architecture maps from established human cell lines (`KOLF2.1J` iPSCs, `MDA-MB-468`, `U2OS`) in vitro with open CC BY-NC-SA 4.0 Dataverse releases and no human subjects IRB protocol or controlled-access tier.
   - **Effect on Scoring**: Excludes non-applicable human-subject/PHI sub-elements (`E4.6` IRB/consent, `E6.1`–`E6.4` regulatory restrictions, `E10.3` privacy/re-identification, `Q10` IRB/ethics, `Q12` data protection impact), reducing CM4AI's maximum denominator from `50`/`88` to `44`/`78`.
2. **`ml_training_dataset: true` Across All Bridge2AI Projects (`AI_READI`, `CHORUS`, `CM4AI`, `VOICE`, `VOICE_PEDIATRIC`) and `KIDS_FIRST`**:
   - **Proposed Setting**: `ml_training_dataset: true`.
   - **Rationale**: Bridge2AI flagship datasets and the Kids First congenital heart defect cohort are explicitly curated and released for AI/ML training and benchmarking, keeping `Q17` (training data anomalies) applicable.
3. **`processing_software: true` Across All 6 Projects (`AI_READI`, `CHORUS`, `CM4AI`, `VOICE`, `VOICE_PEDIATRIC`, `KIDS_FIRST`)**:
   - **Proposed Setting**: `processing_software: true` across all 6 context files (`data_collection: true`, `data_processing: true`, `shared_dataset: true`).
   - **Rationale**: Each corpus documents preprocessing, harmonization, or pipeline software used to produce the dataset (`E5.4`), while `Q7` (preprocessing/cleaning/labeling software availability) remains applicable across all 6 cohorts.
4. **Data Governance & Committee Contact Equivalence (`#2911`)**:
   - **Proposed Setting**: `evaluate_d4d.py` recognizes both `data_governance.committee_contact` and `regulatory_restrictions.governance_committee_contact`, and excludes the 4 regulatory restriction subfields of `Q9` when `regulated_access: false`.
5. **Adult vs Pediatric Cohort Contexts (`VOICE` vs `VOICE_PEDIATRIC`, `CHORUS`, `KIDS_FIRST`)**:
   - **Proposed Setting**: Both `VOICE` (`voice_context.yaml`) and `VOICE_PEDIATRIC` (`voice_pediatric_context.yaml`), along with `CHORUS` and `KIDS_FIRST`, have all 7 boolean applicability flags (`human_subjects`, `regulated_access`, `shared_dataset`, `data_collection`, `data_processing`, `processing_software`, `ml_training_dataset`) set to `true` (`50/50` on Rubric 10, `19/20` (`88.0`) on Rubric 20), with cohort-specific `rationale` entries distinguishing adult vs pediatric scope.

---

## 2. Draft Omission Contexts (`Step A5d` / `#1763`) — `PENDING HUMAN REVIEW`

Six draft `omission_context_v1` files have been generated in `data/omission_contexts/` via `scripts/build_draft_contexts.py`:

| Project | Draft Omission Context File | `scopes[0].referent` | `scopes[0].release` | `source_policy.basis` | `vocabulary` |
| --- | --- | --- | --- | --- | --- |
| **CHORUS** | `data/omission_contexts/chorus_omission_context.json` | `"CHORUS dataset"` | `null` (`D04` website-only URL mapped to `null`) | `"Declared source_manifest.yaml tier hierarchy."` | `B2AI_SUBSTRATE` (`81`), `B2AI_TOPIC` (`56`) |
| **AI_READI** | `data/omission_contexts/ai_readi_omission_context.json` | `"AI-READI Flagship Dataset"` | `"https://doi.org/10.60775/fairhub.3"` | `"Declared source_manifest.yaml tier hierarchy."` | `B2AI_SUBSTRATE` (`81`), `B2AI_TOPIC` (`56`) |
| **CM4AI** | `data/omission_contexts/cm4ai_omission_context.json` | `"CM4AI Flagship Dataset"` | `"https://cm4ai.org/"` | `"Declared source_manifest.yaml tier hierarchy."` | `B2AI_SUBSTRATE` (`81`), `B2AI_TOPIC` (`56`) |
| **VOICE** | `data/omission_contexts/voice_omission_context.json` | `"Bridge2AI-Voice Adult Dataset"` | `"https://doi.org/10.13026/37yb-1t42"` | `"Declared source_manifest.yaml tier hierarchy."` | `B2AI_SUBSTRATE` (`81`), `B2AI_TOPIC` (`56`) |
| **VOICE_PEDIATRIC** | `data/omission_contexts/voice_pediatric_omission_context.json` | `"Bridge2AI-Voice Pediatric Dataset"` | `"https://doi.org/10.13026/mf9s-5r03"` | `"Declared source_manifest.yaml tier hierarchy."` | `B2AI_SUBSTRATE` (`81`), `B2AI_TOPIC` (`56`) |
| **KIDS_FIRST** | `data/omission_contexts/kids_first_omission_context.json` | `"Kids First Congenital Heart Defects Dataset"` | `"https://kidsfirstdrc.org/"` | `"Declared source types from project manifest (no tier hierarchy declared)."` | `{}` (`0` terms; neutral profile) |

- **Review Question**: Confirm whether `scopes[0].referent`, `scopes[0].release`, `source_policy` tiers, and `vocabulary` in `data/omission_contexts/*_omission_context.json` are approved for promotion from `draft` to registered `Step A5d` (`CHORUS`) and `Step A19` (fan-out) runs.

---

## 3. Critical Technical Findings from `Step A1` & `Step P1`/`P2` Blocking Launch Until Owner Decision

### 3.1 `Step A1` Offline Sizing (`notes/a1_offline_sizing_2026-10-20.md`, `#5072`)

1. **Duplicate Schema Carry Exceeds the 1,000,000-Token Input Window**:
   - Under the current protocol, every typed-audit request carries the schema twice: `audit_omissions._schema` (~1.49 MB) plus the schema context's induced-slot `classes` (615–950 KB).
   - No partition grid (`G1`–`G6`) makes a typed-audit worker's input fit for any of the 6 projects (`CHORUS` was counted at 1,009,249 input tokens in A1b; the other 5 projects are estimated 24–60% over).
2. **Registered `worker_output_tokens: 4,000` Is Below the Terminal Source-Review Floor**:
   - `source_review.check` (at assembly) requires one row per assigned path quoting and covering each value. That minimum valid output floor is `10,854–11,816` tokens at `G2` and `13,732–24,290` tokens at `G5` (before thinking tokens).
   - Meanwhile `audit_batches.check_worker` currently accepts an all-metadata row (`{"path", "metadata_reason"}`) on any path (`1,282–3,852` tokens for `CHORUS`/`VOICE`/`VOICE_PEDIATRIC`), which passes the worker stage and fails only at terminal assembly after all workers, omission, and integration have been billed.
3. **Recommended Compaction & Partition (`S7` + `G5` + `A6` Output Caps + Report-Family Trim)**:
   - **Compaction `S7`**: Drop the duplicate model-facing typed catalog (`S1`), trim induced-slot definitions to `name`, `description`, `range`, `cardinality`, `inlining` (`S5`), and omit duplicate typed trees (`whole_value_identity`) from owners.
   - **Partition `G5` (`max_paths=384, max_inventory_bytes=65536, max_workers=4`)**: Valid for all 6 projects (1–3 workers) and keeps typed aggregate input within `2.93M` (under the `4.0M` cap, whereas `G2` reaches `4.33M`–`4.71M` on `AI_READI` and `KIDS_FIRST`).
   - **Report-Family Carry Trim**: Even under `S7`, `KIDS_FIRST` regate is `880,265` tokens at the 96k report cap (over the 850k ceiling) and `AI_READI` regate is `816,145` at the audit floor (only 172 B/row headroom). Trimming the report family's carry (carrying only findings/revised rows from the assembled audit, or dropping classes/inventory from the report family's schema context) clears the 850k ceiling.
   - **Output Caps (`Step A6`)**: Raise `worker_output_tokens` and `aggregate_output_tokens` above the `G5` terminal floor (`24,290` tokens at 4 B/token, `33,035–39,836` at A1b ratios) plus thinking allowance, and enforce `record_metadata_allowed` in `audit_batches.check_worker`.

### 3.2 `Step P1`/`P2` `AI_READI` Comparator Boundary (`notes/p1_v8_comparability_recompute.md`, `D02`, `#5042`)

- Following `#5042` (owner ruling of 2026-10-14 that standard generation runs read no RO-Crate content), today's `AI_READI_preprocessed.txt` is `1a58ad7b`, whereas the three `v8` `04g` `AI_READI` records were generated from bundle `d22b61a9` (which included RO-Crate chunks `c022`–`c024`, cited in 32–37 of 314–351 receipted snippets across 17–22 top-level slots).
- The owner must select one of four options for `D02` (`notes/generic_v10_analysis_plan.md` Section 2):
  - **`(a)`**: Keep `v8` `04g` rep1–3, **explicitly labelled cross-arm** (crossing the with-crate/no-crate boundary) and stratified in analysis.
  - **`(b)`**: **Exclude `AI_READI`** from the confirmatory `v8` contrast (`CHORUS`, `CM4AI`, `VOICE`, 9 + 9 records) and report `AI_READI` `v10` descriptively.
  - **`(c)`**: Use the **2026-10-14b no-crate agentic rerun** (`claudecode_agent`, bundle `1a58ad7b`, after a data PR), labelled as a joint runtime/provider/transport/effort/package contrast.
  - **`(d)`**: Commission a **new no-crate `v8` API run** of `AI_READI` under a separate registration and budget allocation.

---

## 4. Owner Decisions Status (`D01`–`D32`)

| Decision ID | Status | Summary / Owner Ruling |
| --- | --- | --- |
| **`D06`** (`#1849`) | **DECIDED (2026-10-19)** | Every `generic_v10` API registration declares `{"type": "adaptive", "display": "summarized"}`; no typed-stage cache breakpoint. |
| **`D07`** (`#1763`) | **DECIDED (2026-10-19)** | Option 1: `$100` named `generic_v10` API pilot allocation (`CHORUS` pilot `$15`, contingency `$15`; `AI_READI` pilot `$35` provisional ceiling, contingency `$35`); at most 2 billed attempts per cell; explicit registration `sha256` word required per launch. |
| **`D10`** (`#4761`) | **DECIDED (2026-10-20)** | **Retire** the `v10z`/`audit_controls` native lineage and `audit28` (recorded in `notes/reviews/v10z_retirement_2026-10-20.md`). |
| **`D22`** (`#1763`, `#4761`) | **DECIDED (2026-10-20)** | **Withdraw** all `v10z` standing authorizations; every `generic_v10` generation and evaluation requires its own explicit owner word. |
| **`D26` (`D-A`)** (`#1763`) | **DECIDED (2026-10-23T23:35Z)** | **Track N is the native agentic path** (`"focus the canary on the native agentic approach not api"`, `"next address these based on current recommendations"`). Uses the **default runtime profile** (not `profile1`), aligns scientific prompt bytes with the API arm after `D30` (`D-E`), and declares procedure differences before comparison. |
| **`D27` (`D-B`)** (`#1763`) | **DECIDED (2026-10-23T23:35Z)** | **Direct-arm directory and prose naming** (follows from `D26`/`D-A`): Track N writes `claudecode_direct{,_core}/<label>/`; in prose the route is called `"native agentic (direct arm)"` (not `claudecode_agent`). |
| **`D28` (`D-C`, `S7`/`G5`/`A6`)** (`#5072`, `#5095`, `#5096`, `#5112`–`#5116`, `#5148`) | **DECIDED (2026-10-23T23:35Z; refined by `D32` 2026-10-24)** | **Void `2026-10-22b` (`CHORUS` × 3); run 1 clean `CHORUS` API re-canary after fixes** (`"next address these based on current recommendations"`). Stage output caps `64k/32k/32k` with derived aggregate (`max_workers × worker + omission + integration`) and `128k` `report`/`report_regate`/`reconcile_full` cap; no global partition default (`--partition chorus` sets `80 / 12,288 / 4` for `CHORUS` only); coverage floor gates the receipted part `with_receipt / (receiptable − added_after_receipt_unmatched)` (`coverage_floor.basis: receipted_part` per `D32`, `19/20` on the re-canary, builder default `pending`, `added_after_receipt` reported and ungated per `#742`, fence unwrap versioned per `#5116`); `S7` reworked so generation gets full descriptions, typed-audit workers keep their own slot descriptions, omission gets slot definitions, wire bytes are hashed (`#5148`), and registration identity covers trim, code-side contracts, and wire format (`#5113`, `#5114`). |
| **`D29` (`D-D`)** | **`PENDING OWNER` (at native launch)** | Effort level and first-party `claude.ai` subscription/login account for the Claude Code native canary (Track N requires a first-party `claude.ai` login and no API key). |
| **`D30` (`D-E`)** (`#5048`, `#5093`, `#5097`–`#5099`, `#5102`, `#5103`) | **DECIDED (2026-10-23T23:35Z; J3′/J5/J6 confirmed 2026-10-24T00:48Z)** | **Fix `generic_v10` R9 criteria-defined enumeration rule text with a new pin rotation on `#5093`** (`"next address these based on current recommendations"`, `"confirm"` on J3′ tier names as prose, J5 access facts only, J6 open licence/guestbook not restricting access). Scope R9 criteria clause strictly to `confidentiality_level` and `hipaa_compliant`. |
| **`D31` (`D-F`)** (`#5096`, `#5115`, `#5138`, `#5142`) | **DECIDED (2026-10-23T23:35Z)** | **`2026-10-20a` is kept as evidence only, marked invalid** (`"next address these based on current recommendations"`). Archived via `d4d runs archive` under `data/ATTIC/d4d_concatenated_archived/` with a `README.md` and removed from corpus inventories; `2026-10-22a` lands as a generated record after its fixes and disclosures. |
| **`D32` (`D-C refinement, A13 F1`)** (`#5095`, `A13`) | **DECIDED (2026-10-24)** | **Option `(a)` (`"decision 1 = a"`)**: Under `coverage_floor.basis: receipted_part`, the gated formula is **`with_receipt / (receiptable − added_after_receipt_unmatched)`**, where `added_after_receipt_unmatched` (instrument v4 only) counts uncovered leaves whose path the phase-1 snapshot lacks **and** whose canonical leaf value is not among `populated_leaves(original)`. Moved/renamed/shifted never-receipted phase-1 values stay in the gated denominator; `added_after_receipt` stays as the reported `#807` counter. Canary effect: unchanged (`58/58` on `10-20a`, `5/5` unmatched; `64/64` on `10-22a`, `11/11` unmatched). |
| **`D02` (`#5042`, `P2`)** | **`PENDING OWNER`** | Choose Option `(a)`, `(b)`, `(c)`, or `(d)` for the `AI_READI` `v8` comparator and canary baseline. |
| **`D04` (`#2914`)** | **`PENDING OWNER`** | Confirm `CHORUS` corpus policy (`Path B` frozen 17-file bundle `9b2ef4b6` for `v10` comparability vs `Path A` prune). |
| **`D01`, `D03`, `D05`, `D08`, `D09`, `D11`–`D21`, `D23`–`D25`** | **`PENDING OWNER`** | Documented with recommendations and `[proposed; owner fixes at P4]` rules in `notes/generic_v10_analysis_plan.md`. |

---

## 5. Decided Rulings of 2026-10-23 & 2026-10-24 (`D26`/`D-A`, `D27`/`D-B`, `D28`/`D-C`, `D30`/`D-E`, `D31`/`D-F`, `D32`/`A13 F1`)

On **2026-10-23T23:35Z**, the owner directed `"next address these based on current recommendations"` across `D-A`, `D-B`, `D-C`, `D-E`, and `D-F` (supplementing the earlier 2026-10-23 direction `"focus the canary on the native agentic approach not api"`, followed on **2026-10-24T00:48Z** by `"confirm"` on the three R9 judgement calls `J3′`, `J5`, and `J6`, and on **2026-10-24** by `"decision 1 = a"` for the `D-C` / `A13 F1` floor-subtraction refinement). Because the `notes/coordination/` directory is untracked, the authoritative record of each decision is preserved here under `D26`–`D32`.

### 5.1 `D28` (`D-C`): Void `2026-10-22b` (`CHORUS` × 3), Run One Clean `CHORUS` API Re-Canary After Fixes, and Update Registration/Runtime Rules

#### 5.1.1 D07 Budget Accounting & Why `2026-10-22b` Is Voided

| Budget Slice / Run | Allocation / Limit | Settled Spend | Total Spend (incl. Abandoned Calls) | Remaining Balance / Status |
| --- | --- | --- | --- | --- |
| **`2026-10-20a`** (`CHORUS` rep1, mid-run `25k` → `64k`) | Attempt 1 of 2 (`$15.00` pilot) | `$20.59` (11 rows) | `$21.44` (`+$0.85` abandoned `report`) | **Archived to `data/ATTIC/` as invalid evidence only (`D31`/`D-F`, `#5138`, `#5115`, `#5142`)** |
| **`2026-10-22a`** (`CHORUS` rep1, `64k/32k/32k/320k`) | Attempt 2 of 2 (`$15.00` contingency) | `$15.17` (9 rows) | `$17.15` (`+$1.98` abandoned `reconcile_full`) | **Retained generated canary (`gate.verdict: unmeasurable`, `64/75` slot receipts, `0` unverified snippets; ran under `S7` as implemented and undeclared fence unwrap `#5116`)** |
| **`D07` `CHORUS` API Canary Slice** | **`$30.00`** (`$15 + $15`, max 2 attempts) | **`$35.76`** | **`$38.59`** | **`$0.00` left** (`-$5.76` settled / `-$8.59` total over `$30.00`; **2 of 2 allowed attempts used**) |
| **`D07` Option 1 Total API Pilot Envelope** | **`$100.00`** (`$30` `CHORUS` + `$70` `AI_READI`) | `$35.76` | `$38.59` | **`$64.24` settled / `$61.41` total** unspent (**AI_READI's `$70` stays whole**) |
| **`D07` Overall Campaign Ceiling** | **`$420.00`** | `$35.76` | `$38.59` | **`$384.24` settled / `$381.41` total** unspent (**`~$25` slice allocated for 1 clean `CHORUS` API re-canary; launch still requires explicit owner word naming the registration `sha256` per `D07`/`D22`**) |

- **Why `2026-10-22b` (`CHORUS` × 3) is voided and never launched**:
  1. Neither `2026-10-20a` nor `2026-10-22a` was a clean, measured-pass run of a fixed registration (`2026-10-20a` changed registration mid-run and had hand-edited report files; `2026-10-22a` ran `77b94e457` code-side contract text not captured in its v1 registration identity, ran under `S7` as implemented, and relied on an undeclared YAML-fence unwrap in `rereceipt.parse_answers`).
  2. Per the owner's canary rule (*"If the canary needed a fix, re-canary; do not fix and fan out in the same step"*), the three `2026-10-22b` registration files (`f11fea22…`, `0b9e1a94…`, `6d5ae9fc…`) and roster (`7e946b33…`) in `d4d-executions/caller-inputs/` are left byte-for-byte untouched alongside `VOID.md` (`"voided by the owner's D-C decision, 2026-10-23; never launched"`).
  3. Instead, after `D30` (`D-E` R9 fix) and `D28` (`D-C` floor, caps, and `S7` fixes) land on one pushed head, **one** clean `CHORUS` API re-canary registration will be built on the exact same R9 scientific bytes as the Track N native canary (`D26`/`D-A`), budgeted at at most `$25` from the `$420` ceiling while leaving `AI_READI`'s `$70` untouched. Launching that re-canary still requires an explicit owner word naming its registration `sha256` (`D07`, `D22`).

#### 5.1.2 Decided `D28` (`D-C`) Technical Specifications (Replacing the Superseded Draft of `bb47ac648`)

1. **Output Token Caps (`A12`)**:
   - Keep typed-audit stage caps at `worker_output_tokens = 64,000`, `omission_output_tokens = 32,000`, `integration_output_tokens = 32,000`.
   - Derive `aggregate_output_tokens` mechanically as `max_workers × worker_output_tokens + omission_output_tokens + integration_output_tokens` (`320,000` for 4 workers), and `max_calls` from the worker count (`max_workers + 2`).
   - Raise the runner cap (`api_runner.py`) for `report`, `report_regate`, and `reconcile_full` from `96,000` to **`128,000`** tokens (`2026-10-22a` used `83,367 / 96,000` tokens on `report`, 87% of cap).
2. **Partition Bounds (`A12` & `A17`) — Correction to `bb47ac648`**:
   - *Correction*: `max_paths = 80, max_inventory_bytes = 12,288, max_workers = 4` is **not a valid global default**. It refuses every `AI_READI`, `CM4AI`, `VOICE`, and `v8` `CHORUS` full record on `indivisible_field_bound` (`/creators` has 133–184 paths; `/file_collections` has 99–144 paths) and `worker_count_bound`. Conversely, `384 / 65,536 / 4` plans all projects but can assign a single worker an inventory requiring `230k–300k` output tokens (exceeding the `64k` cap and `128k` model ceiling).
   - **Ruling**: `scripts/build_api_registrations.py` has **no global partition default** and refuses to build unless explicit bounds (`--max-paths`, `--max-inventory-bytes`, `--max-workers`) or the CHORUS-only `--partition chorus` profile (`80 / 12,288 / 4`, valid only for `--project CHORUS`) are supplied. Before any non-CHORUS `v10` run (`A17`), `make_plan` will split large top-level lists across workers and scale `max_workers`, `aggregate_output_tokens`, and `max_calls` so each worker's inventory stays at ~12 KB or less.
3. **Receipt Coverage Floor Basis & Versioned Fence Unwrap (`A13`, `D32`, `#5116`, `#742`) — Correction to `bb47ac648`**:
   - *Correction*: The metric name `required_recommended_20` cited in `bb47ac648` **does not exist in the codebase**. In `receipt_completion.py`, `evaluate_floor` compares `minimum_numerator / denominator` against `with_receipt / receiptable`. In both `2026-10-20a` and `2026-10-22a`, `never_receipted == 0` (100% of slots present at receipt time received a receipt); all unreceipted slots (`5` in `10-20a`, `11` in `10-22a`) were `added_after_receipt` during reconciliation, which `#742` specifies are reported under `slots.without_receipt` and never gated.
   - **Ruling (`D28`, refined by `D32` on 2026-10-24)**:
     - First (`#5116`), record `answer_envelope` (`bare` or `yaml_fence`) and `answer_parser` (`v2`) in receipt-completion results so fence unwrapping is explicitly declared and versioned.
     - Second, add `coverage_floor.basis: receipted_part` to gate **`with_receipt / (receiptable − added_after_receipt_unmatched)`** (`D32`, `"decision 1 = a"`, on which `2026-10-20a` is `58/58` with `5/5` unmatched and `2026-10-22a` is `64/64` with `11/11` unmatched), while reporting `added_after_receipt` beside it ungated. Existing v2 floors without `basis` keep their exact `all_receiptable` meaning byte-for-byte.
     - Keep the builder default `coverage_floor` as `pending` (`diagnostic_pilot`) so fan-out stays blocked by default (`cli/api.py`), and register `19/20` (`basis: receipted_part`) specifically on the `CHORUS` re-canary registration.
4. **`S7` Schema-Context Rework & Registration Identity Coverage (`A14`, `#5113`, `#5114`, `#5148`)**:
   - **Generation phases** (`full`, `reconcile_full`, `report`, repair) send the untrimmed schema context with slot `description` and `comments` restored (~`+$0.30`/run).
   - **Typed-audit workers** keep the `S7` trim on non-assigned classes/slots, but retain `description` for the slots in each worker's own assigned inventory.
   - **Omission stage** receives the induced slot definitions (`classes` with slot `description`) required by the frozen omission policy.
   - **Wire-byte hashing (`#5148`)**: Every declared request hash (`inner_request_sha256` and stage request digests) hashes the exact wire bytes sent.
   - **Registration identity (`#5113`, `#5114`)**: Registration identity covers the schema-context trim parameters, code-side instruction text (`77b94e457` contract paragraphs), and wire format, under a bumped shared-generation renderer/protocol version so older registrations cannot validate against new bytes.
   - Both `2026-10-20a` and `2026-10-22a` are explicitly labelled `"run under S7 as implemented (descriptions trimmed in every phase)"`.

---

### 5.2 `D26` (`D-A`) & `D27` (`D-B`): Native Agentic (Direct Arm) Path via Track N

- **Ruling (`D26` / `D-A`, 2026-10-23T23:35Z)**: Track N (`codex/track-n-direct-adapter`) is the chosen path for the `generic_v10` native agentic canary on `CHORUS`, running under the **supported default runtime profile** (not `profile1`), aligned to the post-`D30` (`D-E`) R9 prompt pins, with all runtime and procedure differences between the API package and the native package explicitly declared before comparison (`notes/coordination/2026-10-23-codex-n1-assessment.md` §§5.1–5.2).
- **Ruling (`D27` / `D-B`, 2026-10-23T23:35Z)**: Track N writes to `data/d4d_concatenated/claudecode_direct{,_core}/<label>/` (per `D09` and `native_shared_contract.py`), and in prose the route is referred to as **"native agentic (direct arm)"** (correcting the earlier reference to `claudecode_agent` in `bb47ac648`).

---

### 5.3 `D30` (`D-E`): Corrected `generic_v10` R9 Criteria-Defined Enumeration Rule Text (`#5048`, `#5093`, `#5097`–`#5099`, `#5102`, `#5103`)

- **Ruling (`D30` / `D-E`, 2026-10-23T23:35Z; `J3′`, `J5`, `J6` confirmed 2026-10-24T00:48Z)**: Replace the R9 criteria-defined enumeration paragraph in `src/download/prompts/d4d_generic_arm_prompt_v10.md` and `.claude/commands/d4d-uniform-rules-v2.md` on PR `#5093` and rotate both prompt pins (`canonical_hashes.yaml` and `shared_generation.ASSET_HASHES`):
  1. **Closed scope (`#5099`)**: Only two enumeration slots — `confidentiality_level` (`ConfidentialityLevelEnum`) and `hipaa_compliant` (`ComplianceStatusEnum`) — use the criteria-defined passage rule; `data_type`, `collection_type`, and all other enumerations remain under standard literal/normalized token matching.
  2. **`confidentiality_level` criteria & precedence (`#5098`, `J1`, `J2`, `J3′`, `J5`, `J6`)**:
     - Public download without account/registration/approval/signed agreement supports `unrestricted`; Creative Commons licences, licence confirmations, citation requests, and download guestbooks are not access restrictions (`J6`, preserving `CM4AI` as `unrestricted`).
     - Registration/account, verified identity/credentials, request approval, institutional sign-off, or a signed/accepted DUA or dataset-specific licence supports `restricted` (`J1`).
     - Individual request review before access is granted by a DAC/office or an IRB/ethics committee approving the requester's own use (not the study's own data-collection IRB) supports `confidential`, taking precedence over `restricted` conditions on the same route (`J1`).
     - Multi-tier datasets record the **least restrictive tier** through which any of the dataset's own data (excluding metadata, documentation, code, samples, or synthetic copies) can be obtained, with all tiers described in `data_governance.access_review_process` (`J2`).
     - Tier names (`"controlled access"`, `"registered access"`, `"credentialed access"`) state no conditions, are recorded as prose, and are never the coverage receipt (`J3′`, `#5102`). Statements of data sensitivity do not decide `confidentiality_level` (`J5`).
  3. **`hipaa_compliant` criteria (`#5097`, `J4`)**:
     - Passages stating the dataset holds no data about human participants (e.g., cell lines, model organisms, simulated data) support `not_applicable`.
     - Passages stating the data were de-identified under HIPAA (naming HIPAA, Safe Harbor, or Expert Determination) support `compliant`; `"no PHI"` or `"de-identified"` without naming HIPAA or either method supports neither value.

---

### 5.4 `D31` (`D-F`): Archive `2026-10-20a` to `data/ATTIC/` as Invalid Evidence Only (`#5096`, `#5115`, `#5138`, `#5142`)

- **Ruling (`D31` / `D-F`, 2026-10-23T23:35Z)**:
  1. `2026-10-20a_claude-opus-5-api-generic-v10_rep1` (`CHORUS`) is archived via `d4d runs archive` to `data/ATTIC/d4d_concatenated_archived/claudecode_api{,_core}/2026-10-20a_claude-opus-5-api-generic-v10_rep1/` with a companion `README.md` declaring it **evidence-only and invalid as a generated D4D record** (documenting the `agy` session's 19:23 PDT and 21:43 PDT hand edits to the rejected `72ac7d9a…` report response after unsaved regate `a42e7689…`, and the mid-run registration overwrite `57d5c842…` → `4f94102c…`), and is removed from all active corpus inventories (`tests/data/report_claims_origins.json`, `tests/test_report_claims_corpus.py`, `tests/test_status_context.py`).
  2. `2026-10-22a_claude-opus-5-api-generic-v10_rep1` (`CHORUS`) remains in `data/d4d_concatenated/` on PR `#5096` with explicit outcome-note disclosures that its receipt completion relied on the then-undeclared YAML-fence unwrap (`#5116`) and that it ran under `S7` as implemented (`#5113`, `#5114`, `#5148`).

---

### 5.5 `D32` (`D-C refinement, A13 F1`): Subtract `added_after_receipt_unmatched` in the Receipted-Part Floor (`2026-10-24`)

- **Owner words**: `"decision 1 = a"`
- **Date**: `2026-10-24`
- **Coordination label**: `D-C refinement, A13 F1`
- **Formula**:
  $$\frac{\text{with\_receipt}}{\text{receiptable} - \text{added\_after\_receipt\_unmatched}}$$
- **Specification**:
  1. The independent review of `A13` (`60634b0c2`, Finding `F1`) demonstrated that the path-only counter `added_after_receipt` (`#{p in without : not resolve(original, p)}`) can include never-receipted phase-1 values that a later phase renamed, moved, reshaped, or shifted to a path the phase-1 snapshot lacks (e.g., renaming a never-receipted `license` to `license_and_use_terms.description`, reordering keyless entries, or inserting a new list entry ahead of a never-receipted entry). Subtracting `added_after_receipt` directly would allow those unreceipted phase-1 values to escape the `19/20` floor.
  2. Under Option `(a)` (`"decision 1 = a"`), `receipts.check` emits `slots.added_after_receipt_unmatched` under `instrument_version == 4` (`None` when there is no phase-1 snapshot): the count of uncovered leaves in `without_receipt` whose path does not resolve in `original` **and** whose canonical leaf value (`_leaf_value_key(v)`) does not occur among `populated_leaves(original)`.
  3. `receipt_completion_policy.evaluate_floor` under `basis: receipted_part` subtracts `added_after_receipt_unmatched` from `receiptable`, returns `unmeasurable` when `added_after_receipt` or `added_after_receipt_unmatched` is `None`, and refuses inconsistent counters (`added_after_receipt_unmatched > added_after_receipt`). The path-based `added_after_receipt` remains the reported `#807` counter alongside `added_after_receipt_unmatched`.
- **Canary effect**: **Unchanged** — `58/58` on `2026-10-20a` (`5/5` unmatched) and `64/64` on `2026-10-22a` (`11/11` unmatched). All 16 added paths across the two `CHORUS` canaries sit under entries absent from the phase-1 snapshot and none of their values appear in `populated_leaves(original)`.
