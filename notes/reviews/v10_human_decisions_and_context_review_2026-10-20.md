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
| **AI_READI** | `data/context/ai_readi_context.yaml` | `2d3da438de3d365e54467ba5a6144b20d954198fd2e03e7b101a7b6d81880418` | `true` | `true` | `true` | `true` | `true` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **CHORUS** | `data/context/chorus_context.yaml` | `21f63f6eaaa3d236210c3f10103b0e283f8b52724b875045c9773cabf46e9c0d` | `true` | `true` | `true` | `true` | `true` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **CM4AI** | `data/context/cm4ai_context.yaml` | `9077caaaff2112c84dd3fd261eb2ce5025607eacb7f4997150cc8847660286e9` | `false` | `false` | `true` | `true` | `true` | `true` | `true` | `44 / 50` (`44.0`) | `17 / 20` (`78.0`) |
| **VOICE** | `data/context/voice_context.yaml` | `ddf1dcb4127a7d4158515c04307d8f378f5d70268b9bb17f0242af871d863ebd` | `true` | `true` | `true` | `true` | `true` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **VOICE_PEDIATRIC** | `data/context/voice_pediatric_context.yaml` | `92b9ce7c910ba310e75eb2a7f9dbdf93f161cf17d335c3c6fb0030b620ba78fc` | `true` | `true` | `true` | `true` | `true` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **KIDS_FIRST** | `data/context/kids_first_context.yaml` | `78bb4a2e161ab8c54bd7ab4966389098f888022211df0e794c4251e936bd5e32` | `true` | `true` | `true` | `true` | `true` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |

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

## 4. Owner Decisions Status (`D01`–`D25`)

| Decision ID | Status | Summary / Required Owner Action |
| --- | --- | --- |
| **`D06`** (`#1849`) | **DECIDED (2026-10-19)** | Every `generic_v10` API registration declares `{"type": "adaptive", "display": "summarized"}`; no typed-stage cache breakpoint. |
| **`D07`** (`#1763`) | **DECIDED (2026-10-19)** | Option 1: `$100` named `generic_v10` API pilot allocation (`CHORUS` pilot `$15`, contingency `$15`; `AI_READI` pilot `$35` provisional ceiling, contingency `$35`); at most 2 billed attempts per cell; explicit registration `sha256` word required per launch. |
| **`D10`** (`#4761`) | **DECIDED (2026-10-20)** | **Retire** the `v10z`/`audit_controls` native lineage and `audit28` (recorded in `notes/reviews/v10z_retirement_2026-10-20.md`). |
| **`D22`** (`#1763`, `#4761`) | **DECIDED (2026-10-20)** | **Withdraw** all `v10z` standing authorizations; every `generic_v10` generation and evaluation requires its own explicit owner word. |
| **`S7` / `G5` / `A6` (`#5072`)** | **`PENDING OWNER`** | Approve `S7` prompt/schema-carry compaction, `G5` partition (`384` paths / `65,536` B / `4` workers), report-family carry trim, and raised `A6` worker/aggregate output limits before `Step A1b` token-count verification. |
| **`D02` (`#5042`, `P2`)** | **`PENDING OWNER`** | Choose Option `(a)`, `(b)`, `(c)`, or `(d)` for the `AI_READI` `v8` comparator and canary baseline. |
| **`D04` (`#2914`)** | **`PENDING OWNER`** | Confirm `CHORUS` corpus policy (`Path B` frozen 17-file bundle `9b2ef4b6` for `v10` comparability vs `Path A` prune). |
| **`D-C` (`#5095`, `#5096`)** | **`PENDING OWNER`** | Approve API registration defaults (`64k/32k/32k/320k` tokens, `80` paths / `12,288` B, numeric `coverage_floor` `17/20 = 0.85`) and choose Option 1, 2, or 3 for `2026-10-22b` (`CHORUS` × 3) below. |
| **`D01`, `D03`, `D05`, `D08`, `D09`, `D11`–`D21`, `D23`–`D25`** | **`PENDING OWNER`** | Documented with recommendations and `[proposed; owner fixes at P4]` rules in `notes/generic_v10_analysis_plan.md`. |

---

## 5. Decision `D-C`: API Registration Limits, Numeric Coverage Floor, and `2026-10-22b` (`CHORUS` × 3) — `PENDING OWNER`

Following the two 1-replicate `CHORUS` `generic_v10` API canaries (`2026-10-20a` and `2026-10-22a`, PR `#5096`, full readout in `notes/reviews/chorus_v10_api_canaries_2026-10-22_outcome.md`), the owner must decide the production API registration defaults and whether to run `2026-10-22b` (`CHORUS` × 3 replicates).

### 5.1 D07 Budget Accounting & Money Left After `2026-10-20a` and `2026-10-22a`

| Budget Slice / Run | Allocation / Limit | Settled Spend | Total Spend (incl. Abandoned Calls) | Remaining Balance / Status |
| --- | --- | --- | --- | --- |
| **`2026-10-20a`** (`CHORUS` rep1, `25k/16k/16k/150k`) | Attempt 1 of 2 (`$15.00` pilot) | `$20.59` (11 rows) | `$21.44` (`+$0.85` abandoned `report`) | Completed (`gate.verdict: unmeasurable`, `58/63` slot receipts, `1` unverified snippet) |
| **`2026-10-22a`** (`CHORUS` rep1, `64k/32k/32k/320k`) | Attempt 2 of 2 (`$15.00` contingency) | `$15.17` (9 rows) | `$17.15` (`+$1.98` abandoned `reconcile_full`) | Completed (`gate.verdict: unmeasurable`, `64/75` slot receipts, `0` unverified snippets) |
| **`D07` `CHORUS` API Canary Slice** | **`$30.00`** (`$15 + $15`, max 2 attempts) | **`$35.76`** | **`$38.59`** | **`$0.00` left** (`-$5.76` settled / `-$8.59` total over `$30.00`; **2 of 2 allowed attempts used**) |
| **`D07` Option 1 Total API Pilot Envelope** | **`$100.00`** (`$30` `CHORUS` + `$70` `AI_READI`) | `$35.76` | `$38.59` | **`$64.24` settled / `$61.41` total** unspent (earmarked for `AI_READI` `$35 + $35` pilot slice) |
| **`D07` Overall Campaign Ceiling** | **`$420.00`** | `$35.76` | `$38.59` | **`$384.24` settled / `$381.41` total** unspent (requires explicit per-run owner word under `D22`) |

### 5.2 Projected Cost of `2026-10-22b` (`CHORUS` × 3 Replicates)

- Based on measured `CHORUS` API canary costs (`$15.17` settled on the clean 9-call `64k/32k/32k/320k` run `2026-10-22a`, up to `$20.59` settled when `report_regate` triggers as in `2026-10-20a`), running **3 replicates (`rep1..rep3`)** in `2026-10-22b` has a projected cost of:
  - **Settled ledger cost (0–1 regate/run)**: **`$45.51 – $61.77`** (`3 × $15.17` to `3 × $20.59`).
  - **Total cost including typical abandoned-call overhead**: **`$51.45 – $64.32`** (`3 × $17.15` to `3 × $21.44`).
- Because the `$30.00` `CHORUS` canary slice and its 2-attempt cap are exhausted, `2026-10-22b` cannot launch under the existing `D07` `CHORUS` pilot authorization and requires an explicit new budget slice (`~$65` ceiling) and registration `sha256` approval.

### 5.3 Proposed `D-C` Registration Defaults (Prepared on `origin/feat/v10-dc-registration-defaults` at `85698e6c9`)

- **Token & Partition Limits**: `worker_output_tokens = 64,000`, `omission_output_tokens = 32,000`, `integration_output_tokens = 32,000`, `aggregate_output_tokens = 320,000`, `max_paths = 80`, `max_inventory_bytes = 12,288` (`max_workers = 4`).
  - *Why*: Eliminates the `25,000`-token `audit_worker` truncation ceiling hit on `CHORUS` (`w2` reached `22,571` tokens in `2026-10-22a`) and the `16,000`-token `reconcile_full` truncation failure that caused the `$1.98` abandoned call in `2026-10-22a` (`reconcile_full` needed `18,412` output tokens).
- **Numeric Coverage Floor**: `coverage_floor = {"metric": "required_recommended_20", "minimum": 0.85, "minimum_numerator": 17, "denominator": 20}` (`--coverage-floor 17/20`).
  - *Why*: Replaces `{"state": "pending", "mode": "diagnostic_pilot"}` so `gate.verdict` evaluates to a determinate `pass`/`fail` instead of `unmeasurable`. Both `2026-10-20a` (`58` receipted slots) and `2026-10-22a` (`64` receipted slots) clear `17/20` (`0.85`) on `required_recommended_20`.

### 5.4 Owner Options for `D-C` and `2026-10-22b`

1. **Option 1 — Launch `2026-10-22b` (`CHORUS` × 3 API replicates) Now Under New `D-C` Defaults**:
   - **Action**: Merge `origin/feat/v10-dc-registration-defaults` (`85698e6c9`), register `CHORUS` `rep1..rep3` with `64k/32k/32k/320k` limits, `80` paths / `12,288` B, and `coverage_floor = 17/20`, authorize an explicit `$65` `D07` budget slice, and launch after owner word on the 3 registration `sha256` digests.
   - **What it would show**: 3-replicate within-condition variance (`rep1..rep3`) for `claudecode_api` `generic_v10` on `CHORUS` under a determinate gate (`gate.verdict: pass`/`fail`) and uniform token caps (`2026-10-20a` and `2026-10-22a` differed in worker/reconcile caps and had `gate.verdict: unmeasurable`).
2. **Option 2 — Defer `2026-10-22b` Until After the Native Agentic Canary (`D-A`)**:
   - **Action**: Merge the `D-C` defaults (`85698e6c9`) for future registrations, keep `2026-10-22b` on hold, and run the 1-replicate Track N native agentic canary (`D-A`, `notes/coordination/2026-10-23-codex-n1-assessment.md`) on `CHORUS` first; decide afterward whether a 3-replicate matched pair (API × 3 vs native × 3) is worth `$45–$64`.
   - **What it would show**: A direct 1-rep cross-transport comparison (`claudecode_api` `2026-10-22a` vs `claudecode_agent` `D-A`) before committing `$45–$64` to replicate expansion on `CHORUS`.
3. **Option 3 — Drop `2026-10-22b` and Use `2026-10-20a` + `2026-10-22a` as the `CHORUS` API Baseline**:
   - **Action**: Merge the `D-C` defaults (`85698e6c9`), cancel `2026-10-22b`, treat the two completed 1-rep `CHORUS` API runs in `#5096` as the `CHORUS` API pilot baseline, and reserve the remaining `$61.41–$64.24` of the `$100` `D07` pilot envelope for the `AI_READI` pilot (`$35 + $35`) once `D02` is chosen.
   - **What it would show**: Preserves the `$100` `D07` pilot budget ceiling while advancing to the larger multi-worker `AI_READI` testbed under the validated `64k/32k/32k/320k` + `17/20` registration defaults.
