# Human Review & Owner Decision Package for `generic_v10` D4D Generation and Evaluation

- **Date**: 2026-10-20
- **Status**: `PENDING HUMAN REVIEW` (no paid API, native, or LLM evaluation runs have been launched; no agent-invented pre-approval is claimed)
- **Target Worktree**: `/private/tmp/d4d-v10-readiness-20261019` (`feat/v10-preflight-scripts`, PR `#5095`)
- **Related Issues**: `#1763`, `#2911`, `#2912`, `#2914`, `#2918`, `#2926`, `#2932`, `#4345`, `#4758`, `#4759`, `#4761`, `#4829`, `#4830`

---

## 1. Canonical Project Evaluation Contexts (`Step E3` / `#2912`) — `PENDING HUMAN REVIEW`

All 6 project applicability context files under `data/context/` (`schema_version: d4d-evaluation-context-1`) have been prepared and verified against `src/data_sheets_schema/evaluation_context.py` and `tests/test_evaluation_context_files.py`.

### 1.1 Context Files, Digests, and Rubric Denominator Calibration

| Project | Context File | Normalized Context Digest (`SHA-256`) | `human_subjects` | `regulated_access` | `clinical` | `pediatric` | `training` | `software` | Rubric 10 Applicable (`max`) | Rubric 20 Applicable (`max`) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **AI_READI** | `data/context/ai_readi_context.yaml` | `2d3da438de3d365e54467ba5a6144b20d954198fd2e03e7b101a7b6d81880418` | `true` | `true` | `true` | `false` | `true` | `true` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **CHORUS** | `data/context/chorus_context.yaml` | `21f63f6eaaa3d236210c3f10103b0e283f8b52724b875045c9773cabf46e9c0d` | `true` | `true` | `true` | `true` | `true` | `false` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **CM4AI** | `data/context/cm4ai_context.yaml` | `9077caaaff2112c84dd3fd261eb2ce5025607eacb7f4997150cc8847660286e9` | `false` | `false` | `false` | `false` | `true` | `false` | `44 / 50` (`44.0`) | `17 / 20` (`78.0`) |
| **VOICE** | `data/context/voice_context.yaml` | `ddf1dcb4127a7d4158515c04307d8f378f5d70268b9bb17f0242af871d863ebd` | `true` | `true` | `true` | `false` | `true` | `false` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **VOICE_PEDIATRIC** | `data/context/voice_pediatric_context.yaml` | `92b9ce7c910ba310e75eb2a7f9dbdf93f161cf17d335c3c6fb0030b620ba78fc` | `true` | `true` | `true` | `true` | `true` | `false` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |
| **KIDS_FIRST** | `data/context/kids_first_context.yaml` | `78bb4a2e161ab8c54bd7ab4966389098f888022211df0e794c4251e936bd5e32` | `true` | `true` | `true` | `true` | `true` | `false` | `50 / 50` (`50.0`) | `19 / 20` (`88.0`) |

### 1.2 The 5 Hold Questions Requiring Human Confirmation (`#2912`)

1. **`CM4AI` `human_subjects: false` and `regulated_access: false`**:
   - **Proposed Setting**: `human_subjects: false`, `regulated_access: false`.
   - **Rationale**: CM4AI generates multiscale cell-architecture maps from established human cell lines (`KOLF2.1J` iPSCs, `MDA-MB-468`, `U2OS`) in vitro with open CC BY-NC-SA 4.0 Dataverse releases and no human subjects IRB protocol or controlled-access tier.
   - **Effect on Scoring**: Excludes non-applicable human-subject/PHI sub-elements (`E4.6` IRB/consent, `E6.1`–`E6.4` regulatory restrictions, `E10.3` privacy/re-identification, `Q10` IRB/ethics, `Q12` data protection impact), reducing CM4AI's maximum denominator from `50`/`88` to `44`/`78`.
2. **`training: true` Across All Bridge2AI Projects (`AI_READI`, `CHORUS`, `CM4AI`, `VOICE`, `VOICE_PEDIATRIC`) and `KIDS_FIRST`**:
   - **Proposed Setting**: `training: true`.
   - **Rationale**: Bridge2AI flagship datasets and the Kids First congenital heart defect cohort are explicitly curated and released for AI/ML training and benchmarking, keeping `Q17` (training data anomalies) applicable.
3. **`AI_READI` `software: true` vs Other Cohorts `software: false`**:
   - **Proposed Setting**: `software: true` for `AI_READI`; `software: false` for `CHORUS`, `CM4AI`, `VOICE`, `VOICE_PEDIATRIC`, and `KIDS_FIRST`.
   - **Rationale**: `AI_READI` distributes companion preprocessing/harmonization software alongside its dataset release, whereas the remaining bundles document dataset releases rather than standalone software distributions.
4. **Data Governance & Committee Contact Equivalence (`#2911`)**:
   - **Proposed Setting**: `evaluate_d4d.py` recognizes both `data_governance.committee_contact` and `regulatory_restrictions.governance_committee_contact`, and excludes the 4 regulatory restriction subfields of `Q9` when `regulated_access: false`.
5. **Adult vs Pediatric Cohort Separation (`VOICE` vs `VOICE_PEDIATRIC`, `CHORUS`, `KIDS_FIRST`)**:
   - **Proposed Setting**: `VOICE` sets `pediatric: false` (adult cohort, ages 18–98); `VOICE_PEDIATRIC`, `CHORUS`, and `KIDS_FIRST` set `pediatric: true`.

---

## 2. Draft Omission Contexts (`Step A5d` / `#1763`) — `PENDING HUMAN REVIEW`

Six draft `omission_context_v1` files have been generated in `data/omission_contexts/` via `scripts/build_draft_contexts.py`:

| Project | Draft Omission Context File | `parent_collection_title` | `dataset_or_release_id` | `project_vocabulary` Count |
| --- | --- | --- | --- | --- |
| **CHORUS** | `data/omission_contexts/chorus_omission_context.json` | `"CHORUS"` | `null` (reconciled multi-source corpus) | `21` |
| **AI_READI** | `data/omission_contexts/ai_readi_omission_context.json` | `"AI-READI"` | `"v3.0.0"` (`10.60775/fairhub.3`) | `36` |
| **CM4AI** | `data/omission_contexts/cm4ai_omission_context.json` | `"CM4AI"` | `"June 2025 Beta Release"` | `28` |
| **VOICE** | `data/omission_contexts/voice_omission_context.json` | `"Bridge2AI-Voice"` | `"v2.0.1"` (`10.57895/rdp.2025.02.v2`) | `27` |
| **VOICE_PEDIATRIC** | `data/omission_contexts/voice_pediatric_omission_context.json` | `"Bridge2AI-Voice"` | `"v1.0.0"` | `22` |
| **KIDS_FIRST** | `data/omission_contexts/kids_first_omission_context.json` | `"Kids First Pediatric Research Program"` | `"phs001138.v4.p2"` | `14` |

- **Review Question**: Confirm whether the `parent_collection_title`, `dataset_or_release_id`, `source_policy` tiers, and `project_vocabulary` lists in `data/omission_contexts/*_omission_context.json` are approved for promotion from `draft` to registered `Step A5d` (`CHORUS`) and `Step A19` (fan-out) runs.

---

## 3. Ten Owner Decisions (`D1`–`D10`) — `PENDING HUMAN APPROVAL`

| Decision ID | Topic & Related Issues | Options / Proposed Resolution | Status |
| --- | --- | --- | --- |
| **`D1`** | **Execution Path for Typed-Audit Runs (`#2926`, `#5072`)** | **Path 1 (Recommended)**: Run `generic_v10` via CBORG API (`d4d api batch --shared-generation-version 1`) with bounded per-stage audit limits (`max_workers=8`, `max_paths=80`, `max_calls=10`) so every stage stays within the 200K effective CBORG context window.<br>**Path 2**: Native Claude Code CLI (`claude-opus-5[1m]`) for oversized multi-stage runs. | `PENDING` |
| **`D2`** | **`CHORUS` Corpus Policy (`#2914`)** | **Path B (Recommended)**: Keep the current frozen 17-file `CHORUS` preprocessed bundle (`d475e424...`, 125,847 bytes) with `dataset_or_release_id: null` for `generic_v10` comparability against `v6`–`v9`, and evaluate any corpus prune (`Path A`) only as a separate registered post-baseline experiment. | `PENDING` |
| **`D3`** | **`VOICE` Adult vs Pediatric Bundle Scope (`#2918`, `#2932`)** | Keep `VOICE` (`data/preprocessed/individual/VOICE`, adult v2.0.1) and `VOICE_PEDIATRIC` (`data/preprocessed/individual/VOICE_PEDIATRIC`, pediatric v1.0.0) as distinct registered cohorts in `source_manifest.yaml`. | `PENDING` |
| **`D4`** | **`KIDS_FIRST` Neutral Profile Registration (`Step A21`)** | Run `KIDS_FIRST` under `data/preprocessed/kids_first_manifest.yaml` (`neutral_generic`, `source_manifest` basis) as an out-of-sample neutral external validation cohort. | `PENDING` |
| **`D5`** | **Direct Arm (`claudecode_direct`) & `v10z` Retirement (`#4758`, `#4761`)** | Retire `v10z` (`generic_v10_zero_shot`) as superseded by `generic_v10` (`API25` + `receipt2`), and defer new `claudecode_direct` runs until the host Claude Code binary (`Step N4b`, `#4759`) is installed and pinned. | `PENDING` |
| **`D6`** | **Paid API Budget Caps & Operator Stop Triggers (`#4829`, `#4830`)** | Enforce `--max-cost-dollars` on every `d4d api batch` launch (e.g., `$15.00` per single-run pilot/canary with `$11.50` operator trigger; `$45.00` per 3-replicate project batch). | `PENDING` |
| **`D7`** | **Receipt Completion Coverage Floor Policy (`#2917`)** | Use `coverage_floor: "pending"` for initial diagnostic pilot/canary runs (`Step A5d` / `Step A6`), then freeze the measured rational floor (`NUM/DEN` or `0.05`-step decimal) before 3-replicate fan-out (`Step A8` / `Step A14`–`A22`). | `PENDING` |
| **`D8`** | **Historical Reference Rescore v2 Execution (`#2912`, `Step E4`)** | After human approval of Section 1 (`data/context/*.yaml`), freeze `notes/reference_rescore_v2/manifest.json` (66 ratings across 24 `v7`/`v8` records: 48 primary + 18 repeatability) and run the single canary (`CHORUS_v7_rep1_r10_rating1`, `$5` cap) before the remaining 65 jobs. | `PENDING` |
| **`D9`** | **Historical Deterministic Rescoring (`Step E2`)** | Re-run deterministic Rubric 10 and Rubric 20 (`evaluate_d4d.py` with dynamic `Q9` and `CM4AI` context applicability) across historical `v7`/`v8`/`v9` records into a versioned output subdirectory without overwriting archived evaluation artifacts. | `PENDING` |
| **`D10`** | **Pre-Registered `v10` Primary Inferential Contrasts (`Track P`)** | Pre-register the primary paired contrasts (`v10` vs `v9` API on `CHORUS`; `v10` vs `v8` API across the 4 core Bridge2AI projects; omission-context vs neutral `v10` ablation; `KIDS_FIRST` external generalization) before launching paid `v10` replicates. | `PENDING` |
