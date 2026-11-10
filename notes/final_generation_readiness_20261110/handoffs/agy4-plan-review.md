# G4 Independent Plan & Dependency Review — Final-Generation Readiness (2026-11-10)

- **Reviewer**: `agy4` (`G4`, read-only reviewer)
- **Reviewed Plan Commit**: `9bcfe7872f9c522dc76b22a4ec3bebfc39539bbc` (`9bcfe7872`, [PLAN.md](../PLAN.md), [assignments/agy1.md](../assignments/agy1.md), [assignments/agy2.md](../assignments/agy2.md), [assignments/agy3.md](../assignments/agy3.md), [assignments/agy4.md](../assignments/agy4.md), [assignments/native.md](../assignments/native.md), [scripts/adhoc/dispatch_generation_readiness_20261110.applescript](../../../scripts/adhoc/dispatch_generation_readiness_20261110.applescript), [scripts/adhoc/message_readiness_worker_20261110.applescript](../../../scripts/adhoc/message_readiness_worker_20261110.applescript))
- **Verified Base Commits**:
  - Main-line base (`G1`–`G3`): `7233f193ad102a8488b31ec7333662c8fefaa996` (schema `3.2.0`)
  - Native base (`N1`, separately owned): `5f4a8e211826fe7f83ec51e6262d750687216aba` (`N1` prepared head `41e0d1c1330d52f4bee34d018a8a958fffb99315`, [handoffs/native.md](native.md))
  - Schema/exchange review baseline (PR `#5791`): `0eaa7ab78ac38881baf14430bda832a1a7e38be1` (`notes/schema_review_20261110/`)
- **Review-Report Corrections Tracking**: GitHub `#5794` (tracks exact deferred-issue titles from `notes/schema_review_20261110/README.md:73-86`, `pyproject.toml:3` package `version = "0.1.0"`, and `tests/test_derive_core.py:24,41`)

---

## 1. Verdict on Plan Scope, Efficiency, and Execution Safety

**Verdict: PASS with four cross-unit dependencies (`D-1`–`D-4`) to check on worker commits.**

1. **Scope discipline**: The plan and unit briefs stay within the authorized 2026-11-10 scope—generating and verifying full D4D YAML, derived Core YAML, and full-record HTML—while keeping broader 28-criterion AI-readiness machinery, `CoreDataset` expansion, historical `v4`/`v8` migration, receipt `v5`, and RO-Crate/FAIRSCAPE export refactors out of the generation critical path.
2. **Serialized execution budget**: Single-worker serialized execution (`<=30s` single-node canary with persisted artifact inspection before `<=300s` serial focused checks, no `xdist`, no whole-suite runs, and sparse worktrees reusing the existing `.venv`) is well-matched to the 10-core host and ~23 GiB free disk budget.
3. **Import-path isolation**: Because the shared `.venv` has editable `.pth` links into the dirty primary checkout, every test/helper invocation in `G1`, `G2`, and `N1` must enforce worktree-first module resolution (`PYTHONPATH=<worktree>/src` or `-I -S -B` with explicit site/worktree path ordering) and record `data_sheets_schema.__file__` in saved evidence.

---

## 2. Cross-Unit Technical Dependencies & Review Checkpoints (`D-1` to `D-4`)

### `D-1`: `G2` Patch Identity `3.2.1` (`#2975`) and Schema Release Parity

- **Lead decision & scope**: `G2` uses schema patch identity `3.2.1` so the released `3.2.0` entry (`cf4e0992a807...` / `db4c4fa49c33...`) remains frozen in [src/data_sheets_schema/schema/release_history.yaml](../../../src/data_sheets_schema/schema/release_history.yaml). Scope is strictly `#2975` wording in [src/data_sheets_schema/schema/D4D_FileCollection.yaml](../../../src/data_sheets_schema/schema/D4D_FileCollection.yaml) (`collection_type`, lines `134–140`) plus required generated/release/mapping products; the Python package version in [pyproject.toml](../../../pyproject.toml) (`line 3`, `version = "0.1.0"`) stays unchanged.
- **Required artifact closure for `G2` / integration**:
  1. **Neutrality**: Replacement prose in `D4D_FileCollection.yaml:135-138` must keep `multivalued: false` and `FileCollectionTypeEnum`, and contain zero `B2AI_*` (`STUDY_IDENTITY`, `STUDY_DESIGN`, `PROSE_ONLY`) tokens enforced by [tests/test_neutral_generation_schema.py](../../../tests/test_neutral_generation_schema.py).
  2. **Schema & Core artifacts**: Moving schema `version:` to `3.2.1` across `data_sheets_schema.yaml`, `data_sheets_schema_core.yaml`, and `D4D_Core.yaml` requires `make regen-all`, rebuilding `data_sheets_schema_core_all.yaml` (`make gen-core-schema` after removing the stale file, since `make regen-all` does not rebuild `data_sheets_schema_core_all.yaml`), and appending `3.2.1` hashes to `release_history.yaml`.
  3. **Comprehensive SSSOM TSVs**: [src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv](../../../src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_comprehensive.tsv) (`line 53`) embeds the verbatim `FileCollection.collection_type` description (`Type(s) of content in this file collection...`), so `make gen-sssom-comprehensive gen-sssom-uri-comprehensive` is required (do **not** run `make gen-sssom-structural`, `#3967`).
  4. **Release-identity test & citation parity**: At integration time, check [tests/test_schema_release_identity.py](../../../tests/test_schema_release_identity.py) (`RELEASE = "3.2.0"` at `line 31`, `lines 106–143, 400, 421–428`) and [CITATION.cff](../../../CITATION.cff) (`line 6`, which PR `#5709` coupled to `RELEASE` in `test_schema_release_identity.py:428`), while keeping `pyproject.toml` package `version = "0.1.0"` untouched.

### `D-2`: `G1` Positive-Fixture Validation Trap (`FileCollectionTypeEnum`) & Dynamic Schema Identity

- **Existing fixture trap**: Older `derive_core` unit tests (e.g., [tests/test_derive_core.py](../../../tests/test_derive_core.py) `lines 24, 41`) use unvalidated `collection_type: "raw"` / `"processed"` strings, whereas [src/data_sheets_schema/schema/D4D_FileCollection.yaml](../../../src/data_sheets_schema/schema/D4D_FileCollection.yaml) (`lines 188–220`) defines `FileCollectionTypeEnum` permissible values as `raw_data`, `processed_data`, `training_split`, `test_split`, `validation_split`, `documentation`, `metadata`, `code`, `supplementary`, and `other`.
- **Checkpoints for `G1` (`tests/test_final_generation_acceptance.py`)**:
  1. Validate the positive full fixture and derived Core record against real LinkML `Dataset` and `CoreDataset` schemas **first** (using valid `FileCollectionTypeEnum` values such as `raw_data` / `processed_data`), before running negative mutations, so negative failures are caused solely by the single injected mutation.
  2. Read the current schema version/hashes dynamically from `provenance.schema_facts()` / `release_history.yaml[-1]` rather than hardcoding `"3.2.0"`, so `G1` integrates cleanly with `G2`'s `3.2.1` update.
  3. Test raw LinkML `Dataset` / `CoreDataset` rejection of all four negative shapes (narrative array, bare `Person` string, unnormalized scalar `data_use_permission`, and `collection_type` list) separately from `api_runner.normalise_record_text` (which wraps scalar `data_use_permission` as a compatibility step, covered in [tests/test_pr5531_regressions.py](../../../tests/test_pr5531_regressions.py)).

### `D-3`: `N1` Native Stub-Refusal Characterization (`41e0d1c1330d52f4bee34d018a8a958fffb99315`)

- **Observed canary result & source boundary ([handoffs/native.md](native.md))**:
  1. `api_runner.py:3621-3653` defines `_looks_like_a_record` (`MIN_RECORD_SLOTS = 5`), whereas `native_shared_schema_gates.py:23-52` (`check_schemas`, `check_pair`) runs closed LinkML validation and pair projection without calling that API stub predicate.
  2. `N1`'s executed 1-node receipt canary (`n1-receipt-canary-1` at `41e0d1c1330d52f4bee34d018a8a958fffb99315`, `1 passed` in `0.779s` outer / `0.151s` pytest) verified **both** expected component behaviors over a nonempty 1-chunk bundle:
     - **Unattested ID-only stub**: `0` verified snippets (`1` receiptable / `0` with receipt) -> refused by `receipts vacuous = 1` in `canary.receipt_floors`.
     - **Source-quoted ID-only stub**: `1` verified snippet (`1` receiptable / `1` with receipt) -> `receipts vacuous = 0` and all component floors in `canary.receipt_floors` are `0`.
  3. **Strict interpretation boundary**: Do **not** infer whole-pipeline stub refusal from unrun gates. `N1`'s receipt canary proves both that vacuity refuses an unattested stub and that receipt-v4 component floors alone do **not** refuse an ID-only record when the identifier string itself is quoted from the source (`N1-F1` component-boundary finding). The `schema` and `evidence` nodes (`source_review.check`) await separate budget grants, and full 15-gate native execution (`StageCompletion`, registered policy admission, typed assembly reconstruction, `evidence_gate` audit-count reconstruction, `#5755`) remains unrun (`whole_native_acceptance: unverified`).
  4. When `G2` advances main-line schema identity to `3.2.1`, the separately owned native branch (`5f4a8e211826fe7f83ec51e6262d750687216aba`, currently on `3.2.0`) will require schema-pin alignment at later `main` -> `native` integration time.

### `D-4`: `G3` Operational Acceptance Checklist (`docs/final-generation-acceptance.md`)

- **Checkpoints for `G3` commit review**:
  1. Commands and module paths must match actual repository entry points (`d4d schema check-digest --strict`, `linkml-validate` / `d4d validate`, `d4d derive core`, `python -m data_sheets_schema.d4d_pair_consistency`, `d4d render html`, `receipts.check`, `evidence_assertions`, `report_claims`, `report_audit_totals`).
  2. Must state clearly that isolated schema/pair validity accepts `{id: ...}` and is not pipeline acceptance; that `Full` is authoritative while `Core` is a deterministic projection omitting `variables`, `splits`, `subsets`, and `participant_privacy`; and that independent source review dispositions applicable missing variables/splits/privacy facts as represented, unavailable in sources, or inapplicable (without inventing values, activating receipt `v5`, or requiring a new 28-criterion gating engine).

---

## 3. Confirmed Non-Prerequisites & Deferred Issues (Cross-Checked Against `notes/schema_review_20261110/README.md`)

Per [PLAN.md](../PLAN.md) (`lines 62–65`) and `notes/schema_review_20261110/README.md` (`lines 73–88`), the following issues are **not** prerequisites for final D4D YAML/Core/HTML generation (with `#5786`/`#5787` addressed only via assurance-boundary wording in `G3`):

| Issue | Exact Finding in `notes/schema_review_20261110/README.md` | Disposition for This Run |
|---|---|---|
| `#5786` | Invalid AI-readiness denominator and stale crosswalk paths | Clarify assurance wording in `G3` checklist; no new rubric engine |
| `#5787` | Unsupported universal Core alignment/lossless claims and unclear Core input boundary (related `#160`/`#136`) | State Full-authoritative / Core-projection boundary in `G3`; no `CoreDataset` expansion |
| `#5788` | Forward exporter ignores nested Creator `Person` (emits `Unknown`) | Deferred RO-Crate export work |
| `#5789` | Model-valid export can omit required RO-Crate date (`datePublished`) | Deferred RO-Crate export work |
| `#5790` | Unimplemented round-trip/SHACL checks return success-shaped reports | Deferred exchange/validation work; do not treat stubbed checks as proof |
| `#4034` | Full `Dataset` has distribution/download semantic type (`dcat:Distribution` / `schema:DataDownload`) | Deferred semantic-release work |
| `#3972` | Core retains nonexistent RAI targets | Deferred semantic-release work |
| `#3025` | Wrong conformance predicate (`conformsTo` expanding to Schema.org rather than Dublin Core), including observed runtime context | Deferred RO-Crate context/export work |
| `#4044` | Source identity loss and undeclared RAI export properties | Deferred RO-Crate export work |
| `#2973` | Open TTL/schema disagreements on identity, creators, URLs and hashes | Deferred ontology/TTL alignment work |
| `#44`, `#23` | Readiness assessment and remaining representational gaps | Deferred assessment profile work |
| `#160`, `#136` | Round-trip/conformance acceptance | Deferred exchange acceptance work |

---

## 4. G4 Status

- Revised `G4` plan and dependency review is complete (`0` tests/builds run, `0` source edits), incorporating all `#5794` factual corrections.
- Standing by for commit SHAs from Lead to conduct read-only commit/report reviews.
