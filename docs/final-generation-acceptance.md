# Final Generation Acceptance Guide

This document defines the operator acceptance checklist for final D4D record generation on pinned `main` (`7233f193ad102a8488b31ec7333662c8fefaa996`, schema `3.2.0`). It grounds acceptance in the existing generation, validation, derivation, receipt, typed-audit, provenance, rendering, and source-review commands without introducing new scoring engines or speculative gates.

---

## 1. Source, Schema, and Registration Freeze Prerequisites

Before running any generation or acceptance step, freeze and record the exact inputs:

1. **Integrated Git Commit & Schema Release State**
   - Record the integrated `HEAD` commit SHA and verify clean schema/datamodel synchronization (`Makefile:204`, `src/data_sheets_schema/cli/schema.py:130`):
     ```bash
     make check-sync
     poetry run d4d schema check-digest --strict
     make check-sssom-comprehensive
     ```
   - Confirm `src/data_sheets_schema/schema/release_history.yaml` and merged full/Core schema artifacts (`src/data_sheets_schema/schema/data_sheets_schema_all.yaml` and `src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`) match the integrated release state (including the `#2975` `FileCollection.collection_type` prose/CHANGELOG alignment once `G2` is integrated).
2. **Prompt Registry & Source Bundle Freeze**
   - Pin the canonical prompt registry (`src/download/prompts/canonical_hashes.yaml`), project source manifest (`data/preprocessed/source_manifest.yaml`), and canonical chunk manifest (`chunks.jsonl`) for the target project (`src/data_sheets_schema/api_runner.py:4241`).
3. **Caller Registration & Dry-Run Plan (`shared_generation_registration_v1`)**
   - Verify the caller registration JSON and inspect the dry-run plan before any live execution (`docs/shared-generation-api-v1.md:107-129`, `src/data_sheets_schema/cli/api.py:884-935`):
     ```bash
     poetry run d4d api status --project "$PROJECT" --label "$RUN_LABEL"
     poetry run d4d api plan \
       --project "$PROJECT" \
       --label "$RUN_LABEL" \
       --shared-generation-version 1 \
       --shared-generation-registration /abs/path/registration.json
     ```

---

## 2. Authoritative Full D4D YAML vs. Deterministic Core Projection (`#694`)

1. **Full `Dataset` Record Is Authoritative**
   - The generated full D4D YAML (`conforms_to_class: Dataset`, `conforms_to_schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml`) is the authoritative record (`src/data_sheets_schema/schema/data_sheets_schema.yaml:222`).
2. **Deterministic `CoreDataset` Derivation**
   - `CoreDataset` (`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`) is a deterministic 40-slot projection derived from the full YAML (`src/data_sheets_schema/derive_core.py:129-249`, `src/data_sheets_schema/cli/derive.py:13-53`, `Makefile:528-534`):
     ```bash
     poetry run d4d derive core --full <full.yaml> --out <core.yaml>
     # or:
     make derive-core FULL=<full.yaml> OUT=<core.yaml>
     ```
   - `derive_core_dict` (`src/data_sheets_schema/derive_core.py:129-192`) performs four deterministic operations:
     1. Copies shared top-level slots present in `CORE_DATASET_SLOTS` (`src/data_sheets_schema/derive_core.py:21-51`).
     2. Projects `resources` by `id` (`_project_resources` at `src/data_sheets_schema/derive_core.py:86-96`), dropping full-only nested slots not in `CORE_DATASET_SLOTS`.
     3. Projects `distributions` from `file_collections` and nested `File` entries (`_project_distributions` at `src/data_sheets_schema/derive_core.py:99-126`).
     4. Derives top-level `dialect` only when all `File` entries across all collections agree on `encoding`, `delimiter`, `comment_prefix`, `double_quote`, `header`, and `quote_char` (`_derive_dialect` at `src/data_sheets_schema/derive_core.py:59-83`).
     5. Sets `conforms_to_class: CoreDataset` and `conforms_to_schema: src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml` (`src/data_sheets_schema/derive_core.py:187-191`).
3. **Full-Only Structures Omitted from `CoreDataset` (`#5787`)**
   - `CoreDataset` intentionally omits full-only analytical and structural sections, including `variables`, `splits`, `subsets`, `participant_privacy`, `parent_datasets`, and the hierarchical `file_collections` container (`src/data_sheets_schema/derive_core.py:21-51`, `notes/schema_review_20261110/issues/core_claims.md:14-44`).
   - Operators must treat `CoreDataset` as a discovery/summary projection that requires its paired authoritative full record and evidence package rather than standalone lossless parity (`#5787`).

---

## 3. Shape Validation, Linting, Pair Consistency, and Full HTML Rendering

1. **In-Process Schema Validation & Instance Linting**
   - Validate both the authoritative full record (`Dataset`) and derived Core record (`CoreDataset`) in-process (`src/data_sheets_schema/cli/validate.py:85-169`, `src/data_sheets_schema/instance_lint.py:37-132`):
     ```bash
     poetry run d4d validate --schema full <full.yaml>
     poetry run d4d validate --schema core <core.yaml>
     ```
   - `d4d validate` runs `linkml_runtime.validator.validate` (falling back to `JsonSchemaDataValidator` only if needed) followed by `lint_instance` (`src/data_sheets_schema/instance_lint.py:106-132`), which flags `placeholder-value`, `empty-value`, `missing-identifier`, `british-spelling`, and `empty-section` warnings.
   - Lint warnings are operator review signals and do not fail the exit code unless `--fail-on-warning` is passed (`src/data_sheets_schema/cli/validate.py:92-160`).
2. **Why an ID-Only Schema Pass Is Not Pipeline Acceptance**
   - In both `Dataset` and `CoreDataset`, `NamedThing.id` (`src/data_sheets_schema/schema/D4D_Base_import.yaml:95`, `src/data_sheets_schema/datamodel/data_sheets_schema.py:162`) is the only required top-level slot (`notes/schema_review_20261110/ai_readiness.md:27-35`, `notes/schema_review_20261110/validation_full.json`, `notes/schema_review_20261110/validation_core.json`).
   - Consequently, an ID-only stub (`id: d4d:stub`) passes isolated LinkML/JSON-Schema validation. Schema conformance is necessary for shape validity, **not** sufficient for generation acceptance.
3. **Current Schema `3.2.0` Shape Rules (`G1`, `G2`)**
   - Verify the generated record obeys the `3.2.0` structural boundaries (`notes/schema_review_20261110/README.md:16-39`):
     - **Scalar narrative slots:** Narrative fields (such as `purposes.response`, `tasks.response`, `addressing_gaps.response`, `preprocessing_strategies.description`, `cleaning_strategies.description`, `labeling_strategies.description`, `raw_sources.description`, `existing_uses.description`, `other_tasks.description`, `future_use_impacts.description`, and `discouraged_uses.description`) must be scalar strings, not lists.
     - **Scalar `FileCollection.collection_type` (`#2975`):** `FileCollection.collection_type` is single-valued (`CollectionTypeEnum` in `src/data_sheets_schema/schema/D4D_Composition.yaml:138-140`); list values are invalid.
     - **Inline `Person` objects:** `creators`, `maintainers`, and governance contact fields (`human_subject_research.ethics_review_board.contact_person`, `data_protection_impacts.contact_person`, etc.) must be inline `Person` mappings (for example `{id: ..., name: ...}` or `Person` fields), not bare name strings (`src/data_sheets_schema/schema/D4D_Base_import.yaml:222`).
     - **List-valued `data_use_permission`:** `DataUsePermission.data_use_permission` (`src/data_sheets_schema/schema/D4D_Governance.yaml:120-126`) is multivalued (`multivalued: true`, `DataUsePermissionEnum`) so primary DUO permissions and modifiers can be listed together.
4. **Full / Core Pair Consistency Gate**
   - Verify that the full record and derived `CoreDataset` satisfy all Phase 4 pair-consistency invariants (`src/data_sheets_schema/d4d_pair_consistency.py:873-951`, `Makefile:536-542`):
     ```bash
     make validate-d4d-pair FULL=<full.yaml> CORE=<core.yaml>
     # or with machine-readable JSON output:
     poetry run python -m data_sheets_schema.d4d_pair_consistency \
       --full <full.yaml> \
       --core <core.yaml> \
       --json
     ```
   - `evaluate_pair` (`src/data_sheets_schema/d4d_pair_consistency.py:725-870`) verifies full and Core schema validity, shared-slot equivalence, projected `resources` and `distributions`, conditional `dialect` agreement, and Core slot closure.
5. **Full-Record HTML Rendering Verification**
   - Render the authoritative full YAML to human-readable HTML (`src/data_sheets_schema/cli/render.py:88-144`, `src/data_sheets_schema/rendering/human_readable_renderer.py`, `project.Makefile:334-345`):
     ```bash
     poetry run d4d render html <full.yaml> -o <out.html>
     ```
   - Confirm `<out.html>` and `datasheet-common.css` are written on disk, non-empty, and display expected human-facing values from the full record (dataset `id`/`title`, inline `Person` names, `data_use_permission` entries, `file_collections`/standards, and populated `variables`, `splits`, or `participant_privacy` sections).

---

## 4. Existing Receipt, Typed-Audit, Report-Gate, and Provenance Checks

Pipeline acceptance uses the existing mechanical verification stack; do **not** activate receipt v5 (`D64` item 11, `D105`).

1. **Coverage Receipt Check (Instrument v3/v4)**
   - Verify non-vacuous source-chunk coverage receipts (`src/data_sheets_schema/cli/receipts.py:52-200`, `src/data_sheets_schema/receipts.py`, `src/data_sheets_schema/canary.py`):
     ```bash
     poetry run d4d receipts check \
       --label "$RUN_LABEL" \
       --project "$PROJECT" \
       --strict
     ```
   - `d4d receipts transform` (`src/data_sheets_schema/cli/receipts.py:16-40`) is an offline diagnostic for historical `v1`/`v2` transform inspection only and is **not** a generation acceptance gate (`docs/cli.md:1071`, `D105`).
2. **Offline Typed-Audit & Omission Inventory Verification (`typed_audit_protocol_v1` / Evidence v7)**
   - Verify offline typed-audit packets, worker responses, omission reconciliation (`omission_inventory_v1`), integration index, and assembled report (`src/data_sheets_schema/typed_audit.py`, `docs/typed-audit-offline.md:45-123`):
     ```bash
     poetry run python -m data_sheets_schema.typed_audit check-integration \
       --packet-dir "$PACKET_DIR"
     poetry run python -m data_sheets_schema.typed_audit check \
       --report "$AUDIT_REPORT_JSON" \
       --record "$FULL_YAML" \
       --bundle "$SOURCE_BUNDLE" \
       --chunk-manifest "$CHUNKS_JSONL"
     ```
   - Every canonical chunk in `chunks.jsonl` must have a verified worker response, and every captured omission candidate must be explicitly reconciled in `omission-reconciliation.json` as either `retain` (linked to a `record: full` omission finding) or `drop` with a verified literal source/artifact reason (`docs/typed-audit-offline.md:72-95`).
3. **Report Claims, Evidence Assertions, and Source-Attribution Preflight**
   - `_gate_report` (`src/data_sheets_schema/api_runner.py:6762-6895`) enforces four report-level checks before a run can pass:
     - `report_claims_block` (`src/data_sheets_schema/api_runner.py:4817`): cited chunks exist and literal snippets match chunk text.
     - `evidence_assertions` (`src/data_sheets_schema/api_runner.py:4982`): protocol v7 evidence assertions validate against the record, bundle, and chunk manifest.
     - `report_audit_totals_block` (`src/data_sheets_schema/api_runner.py:4882`): audit totals reconcile with finding counts.
     - `require_source_reviews` (`src/data_sheets_schema/api_runner.py:6787, 6862`): source review coverage matches the declared source manifest.
   - Operators can run the read-only source-attribution preflight directly (`src/data_sheets_schema/cli/review.py:22-41`):
     ```bash
     poetry run d4d review source-attribution-preflight \
       --report "$REPORT_JSON" \
       --record "$FULL_YAML" \
       --bundle "$SOURCE_BUNDLE" \
       --chunk-manifest "$CHUNKS_JSONL" \
       --protocol-version 7 \
       --source-manifest data/preprocessed/source_manifest.yaml \
       --project "$PROJECT"
     ```
4. **Provenance, Run Completeness, and Canary Verdict**
   - Validate provenance records, run-directory artifacts, and canary verdict against the pinned baseline (`src/data_sheets_schema/cli/provenance.py:3142-3194`, `src/data_sheets_schema/cli/runs.py:578-640`, `src/data_sheets_schema/cli/runs.py:1324-1375`, `src/data_sheets_schema/cli/api.py:1453-1510`):
     ```bash
     poetry run d4d provenance validate-records --label "$RUN_LABEL" --strict
     poetry run d4d runs check --label "$RUN_LABEL" --project "$PROJECT" --strict
     poetry run d4d runs validate --label "$RUN_LABEL" --project "$PROJECT"
     poetry run d4d api verdict \
       --method "$METHOD" \
       --label "$RUN_LABEL" \
       --project "$PROJECT" \
       --canary-baseline "$BASELINE_PREFIX"
     ```

---

## 5. Independent Source Review and Content Disposition (`variables`, `splits`, `participant_privacy`)

1. **Boundary of Mechanical Audit vs. Independent Source Review**
   - Passing schema validation, coverage receipts, and literal quote checks proves structural validity and literal snippet presence in cited chunks (`CLAUDE.md:151-154`, `src/data_sheets_schema/status_context.py:4-5`, `docs/shared-generation-api-v1.md:13-15`). It does **not** prove semantic entailment or exhaustive recall across the full source bundle.
   - Generate and verify the independent review pack (`src/data_sheets_schema/cli/review.py:49-200`, `docs/cli.md:1079-1114`):
     ```bash
     poetry run d4d review pack --label "$RUN_LABEL" --project "$PROJECT"
     poetry run d4d review check --label "$RUN_LABEL" --project "$PROJECT" --strict
     ```
2. **Required Content Disposition for Analytical & Human-Subject Sections**
   - During source review of the authoritative full `Dataset` record against the frozen source bundle, operators must explicitly disposition each of the following domain sections (`notes/schema_review_20261110/ai_readiness.md:36-74`):
     - **`variables`** (`src/data_sheets_schema/schema/D4D_Variables.yaml`, `Dataset.variables`)
     - **`splits` and `subsets`** (`src/data_sheets_schema/schema/D4D_Composition.yaml`, `Dataset.splits`, `Dataset.subsets`)
     - **`participant_privacy`** (`src/data_sheets_schema/schema/D4D_Human.yaml`, `Dataset.participant_privacy`, plus related human-subject/governance context when human data are present)
   - Each section must be recorded under one of three evidence-backed dispositions:
     1. **Represented:** Source-supported values are populated in the authoritative full YAML with verified source citations (understanding that `variables`, `splits`, `subsets`, and `participant_privacy` are intentionally omitted when projecting `CoreDataset`).
     2. **Explicitly unavailable:** The declared source bundle does not document the information; the slot is left omitted/`null` (or noted in gaps/omission findings) **without inventing values**.
     3. **Explicitly inapplicable:** The domain concept does not apply to the dataset (for example, `participant_privacy` on a non-human dataset, or `splits` on an unpartitioned release) and is documented as inapplicable rather than fabricated.
3. **No Invented Values or New 28-Criterion Scoring Gate (`#5786`, `#5787`)**
   - Acceptance must never require hallucinated fields, demand that every optional schema slot be populated, or impose a new 28-criterion AI-readiness score threshold (`notes/schema_review_20261110/ai_readiness.md:61-74`).
   - Keep the three assurance layers distinct (`#5786`, `#5787`):
     1. Schema shape conformance (`d4d validate`, `d4d_pair_consistency`),
     2. Source-supported evidence and explicit disposition per applicable section (`d4d receipts check`, `typed_audit`, `d4d review check`), and
     3. Live repository/distribution service operations (external to static YAML generation).

---

## 6. API vs. Native Stub-Refusal Boundary (`N1`)

1. **API Runner Non-Stub Floor (`_looks_like_a_record`)**
   - In the API runner, `_looks_like_a_record` (`src/data_sheets_schema/api_runner.py:3621-3653`) requires a dict containing `id` (or `Dataset`/`resources`) **and at least `MIN_RECORD_SLOTS = 5` top-level keys** (`src/data_sheets_schema/api_runner.py:3621`) before a YAML output is accepted as a record, in addition to non-vacuous receipt floors (`src/data_sheets_schema/canary.py`) and `_gate_report` (`src/data_sheets_schema/api_runner.py:6762`).
2. **Native Component Evidence vs. Whole Native Acceptance (`N1` Unverified Until `N1` Completes)**
   - In the isolated native worktree (`5f4a8e211826fe7f83ec51e6262d750687216aba` / `N1` branch `41e0d1c1330d52f4bee34d018a8a958fffb99315`), `native_shared_schema_gates.py` (`check_schemas` and `check_pair`) validates full/Core schema shape and pair consistency and enforces `MIN_SHARED_SLOTS_IN_CORE = 1`, which an ID-only stub (`id: d4d:stub`) satisfies.
   - Whether an ID-only or minimal stub is refused across the genuine native final-record completion path (`native_Agent.py` `receipt_gate`, `evidence_gate`, and fifteen-gate public completion) remains **unverified until `N1` executes its bounded verification** (`notes/final_generation_readiness_20261110/handoffs/native.md`).
   - Passing isolated native component checks (`native_shared_schema_gates` or a single final-record gate probe) is component evidence only, **not** whole native pipeline acceptance. Do not claim native final-record stub refusal is verified until `N1` completes, and do not fabricate passing stage-completion or lifecycle evidence to force a downstream gate to run. Native process-lifecycle and quiet-window gates (`#5745`, `#5746`, `#5755`, `#5775`, `#5778`–`#5785`, D127/D128 packets) remain separate prerequisites before any live native generation launch.

---

## 7. Explicit Non-Prerequisites for Final Generation

The following work items are explicitly **not** prerequisites for final D4D YAML generation and must not block generation readiness:

- **Receipt v5 (`D105`, `D64` item 11):** Inactive; generation uses existing receipt v3/v4 checks.
- **New 28-criterion AI-readiness scoring/gating engine:** Not required; existing schema, receipt, typed-audit, pair, rendering, and source-review gates govern acceptance.
- **`CoreDataset` slot expansion:** `CoreDataset` remains the frozen 40-slot discovery projection (`#694`); full-only sections stay in `Dataset` (`#5787`).
- **RO-Crate / FAIRSCAPE / SSSOM semantic-exchange follow-ups:** Issues `#4034`, `#3972`, `#3025`, `#4044`, `#2973`, `#5788`, `#5789`, and `#5790` (plus assurance documentation follow-ups `#5786` and `#5787`) affect downstream export/exchange packaging or prose, not full/Core D4D YAML generation.
- **Bulk historical corpus migration and duplicate full test suites:** Excluded from generation readiness.

---

## 8. Staged Execution Gate Sequence (`Tiny Canary -> Authorized Real Canary -> Batch`)

Final generation proceeds strictly in three gated stages:

1. **Stage 1 — Tiny Offline Canary (`<= 30s`, Serial Worker Budget)**
   - Run one minimal offline fixture canary under the single-worker serial runtime budget (`PLAN.md:53-58`):
     - `G1` offline fixture validation (`Dataset` full YAML -> `d4d derive core` -> `d4d validate` full & Core -> `d4d_pair_consistency` -> `d4d render html`, plus negative `3.2.0` drift checks).
     - `N1` bounded native final-record stub-refusal check on the genuine native gate path.
   - Verify persisted output files and exit statuses on disk before any further execution.
2. **Stage 2 — One Explicitly Authorized Real Single-Project Canary**
   - Requires a separate explicit human launch word in the active conversation naming the exact registration SHA-256 (`D07`, `D22`, `D88`, `D129`, `docs/shared-generation-api-v1.md:67-76`).
   - Run `d4d api status` and `d4d api plan` first, execute the single authorized project canary, and verify every post-run gate on disk (`d4d validate` full & Core, `d4d_pair_consistency`, `d4d receipts check --strict`, `typed_audit check`, `d4d provenance validate-records --strict`, `d4d runs check --strict`, `d4d api verdict`, `d4d render html`, and `d4d review pack` / `d4d review check --strict` with explicit dispositions for `variables`, `splits`, and `participant_privacy`).
3. **Stage 3 — Authorized Batch Fan-Out (`d4d api batch`)**
   - Only after Stage 2 passes all mechanical and source-review checks—and only after a separate explicit human batch launch word naming the closed `shared_generation_batch_roster_v1` SHA-256 (`docs/shared-generation-api-v1.md:78-84`)—may batch execution proceed.
