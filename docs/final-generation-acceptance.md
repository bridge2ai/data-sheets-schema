# Final Generation Acceptance Guide

Operator acceptance checklist for final D4D record generation on the pinned integrated schema. Acceptance combines shape validation, full-to-Core derivation consistency, existing coverage/audit/provenance gates, rendered HTML inspection, and independent source review.

## 1. Freeze Prerequisites Before Generation

Run every command from the pinned checkout. When reusing an environment, record imported-module and resolved-schema paths to verify that they also point into that checkout (#5803).


1. **Schema and synchronization state:** Confirm the repository is on the pinned release commit and schema artifacts are synchronized:
   ```bash
   make check-sync
   poetry run d4d schema check-digest --strict
   make check-sssom-comprehensive
   ```
2. **Inputs and registration preflight:** Freeze `src/download/prompts/canonical_hashes.yaml`, `data/preprocessed/source_manifest.yaml`, canonical `chunks.jsonl`, and caller registration JSON, then verify environment and dry-run plan:
   ```bash
   poetry run d4d api status
   poetry run d4d api plan \
     --project "$PROJECT" \
     --label "$RUN_LABEL" \
     --shared-generation-version 1 \
     --shared-generation-registration /abs/path/registration.json
   ```

## 2. Authoritative Full Record vs. Derived Core Projection (`#694`, `#5787`)

1. **Full `Dataset` YAML is authoritative:** The generated full record (`conforms_to_class: Dataset`, `conforms_to_schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml`) holds the complete dataset metadata.
2. **Deterministic `CoreDataset` derivation:** Derive `CoreDataset` (`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`) from the authoritative full record:
   ```bash
   poetry run d4d derive core --full <full.yaml> --out <core.yaml>
   ```
   Derivation copies shared top-level slots, projects `resources` and derives `distributions` from `file_collections` and nested `File` entries, sets `conforms_to_class: CoreDataset` and `conforms_to_schema`, and omits full-only sections (`variables`, `splits`, `subsets`, `participant_privacy`, `parent_datasets`, and the `file_collections` hierarchy). `CoreDataset` is a summary/discovery projection and requires its paired full record and evidence package (`#5787`).

## 3. Shape Validation, Pair Consistency, and HTML Rendering

1. **Separate full and Core shape validation:** Validate both records and review lint warnings (`placeholder-value`, `empty-value`, `missing-identifier`, `british-spelling`, `empty-section`):
   ```bash
   poetry run d4d validate --schema full <full.yaml>
   poetry run d4d validate --schema core <core.yaml>
   ```
   Because `id` (`NamedThing.id`) is the only required top-level field on `Dataset` and `CoreDataset`, an ID-only stub passes isolated schema validation. Schema validity is required for shape conformance, not sufficient for pipeline acceptance.
2. **Pinned integrated schema structural boundaries:**
   - `creators` is a list of `Creator` containers (`Creator.principal_investigator` takes a nested `Person` object) and `maintainers` is a list of `Maintainer` containers (`role` plus scalar string `maintainer_details`, with no nested `Person`). Explicit `Person` object paths (`Creator.principal_investigator`, `LicenseAndUseTerms.contact_person`, and `DataGovernance.committee_contact`) must be inline `Person` mappings, never bare name strings.
   - Scalar narrative slots (for example `Purpose.response`) and `FileCollection.collection_type` (`#2975`) must be scalar strings, while `LicenseAndUseTerms.data_use_permission` is a list.
3. **Full/Core pair consistency (does not replace schema validation):** The pair checker verifies full-to-Core projection consistency only, not LinkML schema validity, so run it after separate full and Core `d4d validate` checks:
   ```bash
   make validate-d4d-pair FULL=<full.yaml> CORE=<core.yaml>
   ```
4. **Full HTML rendering:** Render the authoritative full YAML and confirm that human-facing values (title, nested `Person` names, `data_use_permission`, `file_collections`, and populated analytical sections) appear in the output alongside `datasheet-common.css`:
   ```bash
   poetry run d4d render html <full.yaml> -o <out.html>
   ```

## 4. Existing Receipt, Typed-Audit, Report, and Provenance Checks

Use the existing mechanical gates; do **not** activate receipt v5 (`D105`; `d4d receipts transform` is a non-gating diagnostic only).

1. **Coverage receipts, provenance, and run gates:**
   ```bash
   poetry run d4d receipts check --label "$RUN_LABEL" --project "$PROJECT" --strict
   poetry run d4d provenance validate-records --label "$RUN_LABEL" --strict
   poetry run d4d runs check --label "$RUN_LABEL" --project "$PROJECT" --strict
   poetry run d4d runs validate --label "$RUN_LABEL" --project "$PROJECT"
   ```
2. **Offline typed-audit and source-attribution checks:** Follow the verified packet, worker, omission-reconciliation (`omission_inventory_v1`), integration, assembly, and verification workflow in [typed-audit-offline.md](typed-audit-offline.md) (where every `typed_audit` subcommand writes `--output` and `check` validates `--assembly`). For read-only report preflight against the bundle and chunk manifest:
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

## 5. Independent Source Review and Content Disposition

Mechanical receipt and quote checks confirm literal snippet presence in cited chunks, not semantic entailment or complete recall. Generate the review bundle, then have an **independent reviewer populate `<PROJECT>_review.yaml`** before running `review check` (generating a pack alone does not create an accepted review):
```bash
poetry run d4d review pack --label "$RUN_LABEL" --project "$PROJECT"
# Independent reviewer completes <PROJECT>_review.yaml before verification:
poetry run d4d review check --label "$RUN_LABEL" --project "$PROJECT" --strict
```
The independent review must disposition `variables`, `splits`/`subsets`, and `participant_privacy` in the full record against the declared source bundle as **represented** (with verified source evidence), **explicitly unavailable** (not stated in sources; left omitted/`null` without invented values), or **explicitly inapplicable** (for example non-human data or unpartitioned release), and must refuse visibly incomplete or stub output regardless of automated component passes.

## 6. API vs. Native Stub-Refusal Boundary (`N1` Is Component-Only)

- **API runner guard:** The API record check requires top-level `id`, rejects every unknown top-level key, and requires at least five top-level keys (`>= 5` keys) in addition to non-vacuous receipt floors and report gates.
- **Native boundary (`N1`):** `N1` exercises isolated receipt, schema/pair, and source-review components without composing the full native admission, process-lifecycle, typed-assembly, and fifteen-gate completion path. Its executed receipt check shows that an accurately quoted `id` alone can satisfy those component floors. **Completing `N1` is always component-only evidence and does not establish whole-native stub refusal or whole-native acceptance.** Operator source review and native process-lifecycle/quiet-window gates (`#5745`, `#5746`, `#5755`, `#5775`, `#5778`–`#5785`, D127/D128) remain separate prerequisites.

## 7. Non-Prerequisites and Staged Execution Sequence

- **Outside generation prerequisites:** Receipt v5 (`D105`), any new 28-criterion AI-readiness scoring rubric, `CoreDataset` slot expansion, bulk corpus migration, and RO-Crate / FAIRSCAPE / SSSOM export issues (`#4034`, `#3972`, `#3025`, `#4044`, `#2973`, `#5788`–`#5790`, plus `#5786`, `#5787`) are not prerequisites for final D4D YAML generation.
- **Staged execution (`tiny canary -> authorized real canary -> batch`):**
  1. **Tiny offline canary (`<= 30s`):** Run one bounded offline fixture check under the serial worker budget and verify persisted outputs on disk.
  2. **One authorized real single-project canary:** Requires an explicit human launch word naming the registration SHA-256 (`D07`, `D22`, `D88`, `D129`), followed by all post-run validation, receipt, typed-audit, provenance, HTML rendering, `d4d api verdict`, and completed independent `d4d review check --strict` gates.
  3. **Authorized batch (`d4d api batch`):** Requires Stage 2 acceptance plus a separate explicit human batch launch word naming the closed `shared_generation_batch_roster_v1` SHA-256 (`docs/shared-generation-api-v1.md`).
