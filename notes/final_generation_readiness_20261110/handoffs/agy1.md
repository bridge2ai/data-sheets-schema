# G1 Final-Generation Acceptance Handoff (`agy1` / `window 3155`)

**`RELEASE BUDGET`** — G1 canary and serial focused cohort execution complete; runtime budget is released.

---

## 1. Branch, Commit, and Verification Identities

- **G1 branch worktree**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-final-generation-shapes-20261110`
- **G1 branch**: `agy/final-generation-shapes-20261110`
- **G1 commit SHA**: `58159488d3eac210130e9e980cef1ebf5b1163bb` (parent `7233f193ad102a8488b31ec7333662c8fefaa996`, addressing `#5798`)
- **Changed paths on G1 branch**:
  - `tests/test_final_generation_acceptance.py` (303 lines at integrated verification head `2e9469852b09150a998793a552ffe8926bf95754`)
  - `scripts/adhoc/run_g1_final_generation_acceptance_20261110.py` (168 lines at integrated verification head `2e9469852b09150a998793a552ffe8926bf95754`)
- **Frozen integrated verification checkout**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/final-generation-readiness-verification-20261110`
- **Integrated verification commit SHA**: `2e9469852b09150a998793a552ffe8926bf95754` (clean detached HEAD; zero source edits made in frozen tree; handoff byte/line counts reconciled under `#5806`)
- **Verified schema identities (3.2.1)**:
  - Full schema (`src/data_sheets_schema/schema/data_sheets_schema_all.yaml`): version `3.2.1`, SHA-256 `bc560a3cd5d04c49e95fcbf33fa8ac349171df1a877e7e0882827bd526a95214`
  - Core schema (`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`): version `3.2.1`, SHA-256 `e174a7a6ec1b5eccef5ee4a8b9f8f773f48243c2d6012ff8a1b846b45a40d088`
- **Interpreter**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python` (`Python 3.13.12`)

---

## 2. Executed Commands and Outcomes

### 2.1 Positive-Only Helper Canary (`<=30s`)

- **Command**:
  ```bash
  cd /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/final-generation-readiness-verification-20261110 && GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 git rev-parse HEAD && PYTHONPATH=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/final-generation-readiness-verification-20261110/src:/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/final-generation-readiness-verification-20261110 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/final-generation-readiness-verification-20261110/scripts/adhoc/run_g1_final_generation_acceptance_20261110.py --mode positive-canary --timeout-seconds 30 --work-dir /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/work --evidence-json /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/evidence.json
  ```
- **Outcome**: Exit code `0` (`checks_passed: ["test_positive_full_to_core_pair_and_html_acceptance"]`, ~7s wall time).

### 2.2 Serial Focused Pytest Cohort (`<=300s`, `addopts` overridden, no `xdist`)

- **Command**:
  ```bash
  cd /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/final-generation-readiness-verification-20261110 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/final-generation-readiness-verification-20261110/src:/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/final-generation-readiness-verification-20261110 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -B -m pytest -o addopts= -p no:cacheprovider -x -v --basetemp=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/pytest-basetemp --junitxml=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/focused-cohort.junit.xml tests/test_final_generation_acceptance.py::test_positive_full_to_core_pair_and_html_acceptance tests/test_final_generation_acceptance.py::test_negative_shape_mutations_fail_for_exact_field tests/test_final_record_component_limits.py::test_receipt_v4_distinguishes_unattested_stub_from_identifier_attestation tests/test_final_record_component_limits.py::test_source_review_covers_id_claim_without_proving_omission_recall tests/test_pr5531_regressions.py::test_scalar_permission_normalises_and_linkml_validates tests/test_cli/test_render.py::TestRenderCLI::test_render_html_honors_output_path_and_copies_css
  ```
- **Outcome**: Exit code `0` — **`6 passed, 13 warnings in 12.89s`**:
  1. `tests/test_final_generation_acceptance.py::test_positive_full_to_core_pair_and_html_acceptance` — `PASSED` (`5.245s`)
  2. `tests/test_final_generation_acceptance.py::test_negative_shape_mutations_fail_for_exact_field` — `PASSED` (`0.050s`)
  3. `tests/test_final_record_component_limits.py::test_receipt_v4_distinguishes_unattested_stub_from_identifier_attestation` — `PASSED` (`0.032s`)
  4. `tests/test_final_record_component_limits.py::test_source_review_covers_id_claim_without_proving_omission_recall` — `PASSED` (`0.006s`)
  5. `tests/test_pr5531_regressions.py::test_scalar_permission_normalises_and_linkml_validates` — `PASSED` (`5.292s`)
  6. `tests/test_cli/test_render.py::TestRenderCLI::test_render_html_honors_output_path_and_copies_css` — `PASSED` (`1.423s`)

---

## 3. Persisted Durable Artifacts & Digests

All artifacts are persisted under `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/`:

| Artifact | Path | Bytes | SHA-256 |
|---|---|---:|---|
| Helper canary evidence JSON | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/evidence.json` | 3669 | *(see JSON payload)* |
| Canary full Dataset YAML | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/work/synthetic_acceptance_full.yaml` | 2831 | `9d21d213722f7f8050f8718d64a7d68f24faaf685d16e8ccb2d802ef2fcfd6cb` |
| Canary derived CoreDataset YAML | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/work/synthetic_acceptance_core.yaml` | 2511 | `c7ad763aa0ce4e619cf933b3c1e6d47d6a83bb484d329b913fb0186c5e718373` |
| Canary rendered full HTML | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/work/rendered/synthetic_acceptance_full.html` | 12374 | `2de9c3fff5f68a04148a9ed0a1f97b85421fa1d92c2d2b2b9c155c450dc817e1` |
| Canary copied CSS | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/work/rendered/datasheet-common.css` | 9893 | `0e4525b56114355cf0cc51c24e98fd8a7b0bba3d6fe59de3031b8bd43f797cd0` |
| Focused cohort JUnit XML | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/focused-cohort.junit.xml` | 1081 | *(6 tests, 0 failures, 0 errors)* |
| Focused cohort console log | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/focused-cohort.log` | 2570 | *(full pytest `-v` output)* |
| Focused cohort pytest basetemp | `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-g1-final-generation-20261110/combined-canary-1/pytest-basetemp/` | — | Includes `test_positive_full_to_core_pai0/g1_acceptance_evidence.json`, `test_receipt_v4_distinguishes_0/receipt-v4.json`, and `test_source_review_covers_id_c0/source-review.json` |
| Preserved initial failed canary (`#5798`) | `/private/var/folders/7w/ksxs106s7_sg14v6cb2y70vr0000gn/T/pytest-of-marcin/pytest-5682/test_positive_full_to_core_pai0` | — | Retained untouched |

---

## 4. What Was Proven vs. Preserved Limitations

- **Proven at `2e9469852b09150a998793a552ffe8926bf95754` (schema `3.2.1`)**:
  - Positive synthetic full `Dataset` with scalar narratives, inline identified `Person` (`NamedThing.id`), normalized DUO permission list (`data_use_permission`), scalar `collection_type` (`processed_data`, `raw_data`), identified `FileCollection` and `File` (`sha256`, `format`, `conforms_to`, `conforms_to_standard`, `bytes`), and synthetic `variables` (`variable_name`), `splits` (`split_details`), and `participant_privacy` (`privacy_techniques`, `reidentification_risk`) validates cleanly under LinkML `Dataset` (`3.2.1`), derives a valid `CoreDataset` (`3.2.1`), passes `validate_pair_data` with zero errors, preserves both in-memory dict immutability and on-disk full YAML byte immutability across `write_core` and `render_yaml_file`, preserves exact nested `Person` and DUO lists and `id`-matched `distributions` in Core while omitting `file_collections`, `participant_privacy`, `splits`, and `variables`, and renders distinctive human-facing values (including `variables`, `splits`, and `participant_privacy` values) into full HTML with copied CSS.
  - Four single-field negative mutations on independent copies of the valid fixture fail `lint_instance` exclusively with `("schema-violation", expected_path)` at `/description` (narrative array), `/creators/0/principal_investigator` (bare `Person` string), `/license_and_use_terms/data_use_permission` (unnormalized scalar permission), and `/file_collections/0/collection_type` (`collection_type` list).
  - Existing `test_scalar_permission_normalises_and_linkml_validates`, `test_render_html_honors_output_path_and_copies_css`, and both `tests/test_final_record_component_limits.py` component checks pass serially under schema `3.2.1`.
- **Preserved limitations**:
  - These synthetic fixture and component checks establish offline schema, projection, pair-consistency, HTML rendering, and isolated receipt/source-review component boundaries only. They do **not** claim scientific adequacy, omission recall, or live native/API whole-route generation acceptance.

**`RELEASE BUDGET`**
