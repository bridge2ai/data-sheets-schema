# D4D Receipts v5 Upgrade Design Note (2026-10-23)

**Author:** `agy`
**Worktree / Branch:** `/private/tmp/d4d-receipts-v5-upgrade-20261023` (`feat/receipts-v5-upgrade`, branched from `origin/main` `0a1132ecf`)
**Coordination Reference:** Board item `A18` in `notes/coordination/STATUS.md`; guardrails in `notes/coordination/2026-10-23-agy-receipts-upgrade-guardrails.md`
**Reference Presentation:** Chris Mungall, *"Show me the receipts: patterns for truth verification in agentic knowledge generation"*, JBIMS Workshop, 23 Oct 2026 (Slides 7, 8, 13, 14).

---

## 1. Executive Summary & Versioning Guardrails

The owner requested four upgrades to the D4D receipt architecture based on the JBIMS Workshop receipts presentation:

1. **Structured Polarity, Source Type, and Explanation Fields on Receipt Entries + Fast Entailment Check (Slides 7–8)**:
   - Support `supports` (`SUPPORT | PARTIAL | REFUTE | NO_EVIDENCE | NEUTRAL`), `evidence_source` (`BUNDLE_TEXT | FILE_METADATA | SCHEMA_CONSTRAINT | EXTERNAL_AUTHORITY | COMPUTED_AGGREGATE | PUBLICATION | GOVERNANCE_DOCUMENT | README_MANIFEST | HUMAN | MODEL_ORGANISM | IN_VITRO | CLINICAL | COMPUTATIONAL | LITERATURE`), and `explanation` on receipt entries, plus a fast deterministic entailment check (`check_fast_entailment`) that distinguishes unit conversions, boolean/enum criteria mappings, and explained paraphrases from ungrounded `no_value_overlap`.
2. **Receipts for Non-Text / Tool-Computed Evidence (Slides 7 & 14)**:
   - Extend coverage and claim receipts beyond verbatim text substrings so values derived from deterministic computations (`sha256`, `md5`, `byte_length`, `line_count`, `manifest_chunk_count`, `manifest_total_bytes`, `regex_count`, `regex_matches`, `count`, `sum`, `min`, `max`, `unique_count`, `unit_convert`) carry a typed `tool` receipt that is re-verified deterministically at check time.
3. **Inline Verifiable Watermarks in Prose Reports (`provedown`, Slides 8 & 14)**:
   - Provide a deterministic inline-watermark parser and verifier (`src/data_sheets_schema/provedown.py`) supporting inline markdown claims (e.g., `` `165,051`{pd: full:/total_files} ``, `` `64/75`{pd: ratio(receipt:/coverage/with_receipt, receipt:/coverage/receiptable)} ``, `[3.82 TB]<!-- pd: chunk:c002 -->`, `` `distributions`{pd: schema:CoreDataset.distributions} ``) in `{PROJECT}_reconciliation.md`, with opt-in integration into `report_claims.check_report`.
4. **Declarative Transformation Receipts via `linkml-map` (Slide 8)**:
   - Express the `Dataset` $\rightarrow$ `CoreDataset` and `FileCollection`/`File` $\rightarrow$ `CoreDistribution` projection declaratively in `linkml_mappings/full-to-core-mapping.yaml` (using `linkml-map`'s `TransformationSpecification` datamodel) and provide deterministic transformation-receipt emission and verification (`src/data_sheets_schema/transformation_receipts.py` + `derive_core.py` / `receipts.core_path_map` parity).

### Instrument Versioning & Non-Interference Policy

Per `CLAUDE.md` and `notes/coordination/2026-10-23-agy-receipts-upgrade-guardrails.md`:
- **Existing instruments (`v3` and `v4`) are frozen:**
  - `RECEIPTS_INSTRUMENT` (`instrument_version=3`) and `RERECEIPTS_INSTRUMENT` (`instrument_version=4`) retain their exact behavior, output keys, and pin hashes across all 280+ committed records.
  - Neither the `generic_v10` CHORUS API re-canary (`A16`) nor the Track N native agentic canary (`C2`/`N2`) selects `instrument_version=5` unless the owner explicitly decides to bump both arms together.
- **New instrument (`instrument_version=5`):**
  - `RECEIPTS_V5_INSTRUMENT = "d4d_receipt_verification v5 (populated_leaves + exact_substring + 8_char_alnum_floor + no_value_overlap + never_receipted + added_after_receipt + added_after_receipt_unmatched + structured_polarity + fast_entailment + tool_receipts)"`
  - Activated only when `instrument_version=5` is explicitly passed or when a receipt document declares `receipt_format_version: 5`.
- **Non-collision with `A13` (and A13 F1 / D32):**
  - `A13` (versioned fence unwrap `#5116` in `rereceipt.parse_answers` and `coverage_floor.basis: receipted_part` gating `with_receipt / (receiptable - added_after_receipt_unmatched)`) is orthogonal to `v5`.
  - In `v5`, `slots` continues to emit `receiptable`, `with_receipt`, `never_receipted`, `added_after_receipt`, and `added_after_receipt_unmatched` with identical semantics (except that `supports: REFUTE | NO_EVIDENCE` is excluded from `with_receipt` and counted under `refuted_leaves`), and `RECEIPTS_V5_INSTRUMENT` explicitly names `+ added_after_receipt_unmatched` (which `v4` added to `slots` at `receipts.py:1717-1718` without changing `RERECEIPTS_INSTRUMENT`), so `evaluate_floor` under `basis: receipted_part` works without modification on both `v4` and `v5` blocks.

---

## 2. Detailed Design of the Four Upgrades

### 2.1 Upgrade 1: Structured Polarity (`supports`), `evidence_source`, `explanation`, and Fast Entailment (`receipts.py`)

#### Entry Schema (Instrument v5)
In `{PROJECT}_coverage_receipt.yaml`, each item in `chunks[].extracted` accepts:
```yaml
- slot: confidentiality_level
  snippet: "Controlled access via dbGaP and PhysioNet DUA"
  supports: SUPPORT                # SUPPORT | PARTIAL | REFUTE | NO_EVIDENCE | NEUTRAL
  evidence_source: GOVERNANCE_DOCUMENT
  explanation: "Controlled access via DUA maps to ConfidentialityLevelEnum.restricted per R9"
```

- **Closed Vocabularies**:
  - `SUPPORTS_VALUES = frozenset({"SUPPORT", "PARTIAL", "REFUTE", "NO_EVIDENCE", "NEUTRAL"})`
  - `EVIDENCE_SOURCE_VALUES = frozenset({`
    `"BUNDLE_TEXT", "FILE_METADATA", "SCHEMA_CONSTRAINT", "EXTERNAL_AUTHORITY",`
    `"COMPUTED_AGGREGATE", "PUBLICATION", "GOVERNANCE_DOCUMENT", "README_MANIFEST",`
    `"HUMAN", "MODEL_ORGANISM", "IN_VITRO", "CLINICAL", "COMPUTATIONAL", "LITERATURE"`
    `})`
- **Validation Rules**:
  - In `instrument_version in (3, 4)`: behavior is unchanged (extra keys are ignored by `_receipt_entries` unless `instrument_version == 5`).
  - In `instrument_version == 5` (or when `receipt_format_version == 5`):
    - If `supports` is present and not in `SUPPORTS_VALUES`, emit ` Finding(kind="invalid_supports_value", chunk=cid, slot=slot, value=...)`.
    - If `evidence_source` is present and not in `EVIDENCE_SOURCE_VALUES`, emit `Finding(kind="invalid_evidence_source", chunk=cid, slot=slot, value=...)`.
    - If `explanation` is present, it must be a non-empty string (`Finding(kind="invalid_explanation", ...)` if empty or non-string).
- **Coverage & Polarity Semantics**:
  - Affirmative coverage (`with_receipt`) counts only verified entries whose effective polarity is `SUPPORT` or `PARTIAL` (default `"SUPPORT"` when omitted).
  - Verified entries with `supports in {"REFUTE", "NO_EVIDENCE"}` are recorded under `coverage["refuted_or_negative_paths"]` and do **not** increment `with_receipt`. If a populated leaf in `full` is backed *only* by a `REFUTE` receipt, `check()` emits `Finding(kind="populated_slot_refuted_by_receipt", chunk=cid, slot=slot)`.
- **Fast Deterministic Entailment (`check_fast_entailment`)**:
  - When `_value_overlaps_snippet(val, snip)` is `False`, `v3`/`v4` unconditionally adds the pair to `snippets.no_value_overlap`.
  - In `v5`, `check_fast_entailment(val, snip, explanation=explanation, slot=slot)` runs a fast, deterministic 3-tier check:
    1. **Unit & Numeric Normalization (`unit_entailed`)**: Parses SI/IEC byte quantities (`KB`, `MB`, `GB`, `TB`, `KiB`, `MiB`, `GiB`, `TiB` $\leftrightarrow$ integer bytes), percentages (`83%` $\leftrightarrow$ `0.83`), number words (`one`..`twenty`, `hundred`, `thousand`, `million`, `billion`), and ISO dates (`October 23, 2026` $\leftrightarrow$ `2026-10-23`).
    2. **Explanation-Bridged Entailment (`explanation_entailed`)**: When `explanation` is provided, checks that `explanation` is anchored to the snippet (shares $\ge 1$ content token $\ge 4$ chars or $\ge 2$-digit number with `snip`) AND anchored to the value/slot (shares $\ge 1$ content token/number with `str(val)` or the slot/enum name).
    3. **Diagnostic Partitioning**:
       - Entailed via unit/numeric normalization or grounded explanation $\rightarrow$ recorded under `snippets["entailed_non_literal"]` (with `mode: "unit_conversion" | "explained_mapping"`), NOT `no_value_overlap`.
       - If `explanation` is supplied but shares no grounding tokens with the snippet or value $\rightarrow$ emits `Finding(kind="ungrounded_explanation", ...)` and stays in `no_value_overlap`.

---

### 2.2 Upgrade 2: Receipts for Non-Text / Tool-Computed Evidence (`receipts.py`)

#### Tool Receipt Entry Schema
In `v5`, an entry in `chunks[].extracted[]` may include a `tool` dict alongside or in place of `snippet`:
```yaml
- slot: file_collections[0].resources[0].md5
  supports: SUPPORT
  evidence_source: COMPUTED_AGGREGATE
  explanation: "MD5 digest computed over chunk c002 text"
  tool:
    name: md5
    target: chunk
    args:
      chunk: c002
    result: "9e107d9d372bb6826bd81d3542a419d6"
```

#### Closed Tool Vocabulary (`TOOL_VERIFIERS`)
All verifiers are pure, deterministic Python functions operating exclusively on the in-memory `texts`, `manifest`, and `full` objects already passed to `receipts.check()` (no shell, no filesystem, no network):
1. `md5` (`target: "chunk" | "snippet"`): hexadecimal MD5 of the target text.
2. `sha256` (`target: "chunk" | "snippet"`): hexadecimal SHA-256 of the target text.
3. `byte_length` (`target: "chunk" | "snippet"`): UTF-8 byte length of the target text.
4. `line_count` (`target: "chunk" | "snippet"`): number of lines in the target text.
5. `regex_count` (`target: "chunk"`, `args: {"pattern": ...}`): count of non-overlapping regex matches in the chunk text (bounded pattern length $\le 256$).
6. `manifest_chunk_count` (`target: "manifest"`): `len(manifest["chunks"])`.
7. `manifest_total_bytes` (`target: "manifest"`): sum of chunk byte lengths in `manifest["chunks"]`.
8. `record_count` (`target: "record"`, `args: {"path": ...}`): length of list at `path` in `full`.
9. `record_sum` (`target: "record"`, `args: {"path": ..., "field": ...}`): numeric sum of `field` across list items at `path` in `full`.
10. `unit_convert` (`target: "snippet"`, `args: {"from_value": ..., "from_unit": ..., "to_unit": ...}`): deterministic unit conversion of a numeric quantity verified to appear in `snippet`.

#### Verification & Accounting
- `verify_tool_receipt(entry, cid, texts, manifest, full)` verifies:
  1. `tool.name` is in `TOOL_VERIFIERS`;
  2. any referenced chunk/snippet exists and verifies;
  3. the deterministic computation equals `tool.result`;
  4. `tool.result` matches or entails the target slot value in `full`.
- Failures emit `Finding(kind="unverified_tool_receipt", chunk=cid, slot=slot, reason=...)`, which is gated identically to `unverified_snippet` under `canary.receipt_floors` when `v5` is active.
- `claim_receipts(receipt, full)` preserves `supports`, `evidence_source`, `explanation`, and `tool` on each inverted claim receipt entry in `{PROJECT}_receipts.yaml`.

---

### 2.3 Upgrade 3: Inline Verifiable Watermarks in Prose Reports (`provedown.py` & `report_claims.py`)

#### Motivation
As documented in `report_claims.py:24-43`, prose claims in `{PROJECT}_reconciliation.md` outside the structured disposition table and `**Action:**` lines could not previously be checked without false positives. Following `ai4curation/provedown` (Slides 8 & 14), `src/data_sheets_schema/provedown.py` checks explicit inline watermarks embedded in markdown prose.

#### Supported Watermark Grammars
1. **Inline Backtick + Brace Attribute**:
   - `` `165,051`{pd: full:/total_files} ``
   - `` `OT2OD032644`{pd: full:/funders/0/grant_id} ``
   - `` `3`{pd: count(core:/distributions)} ``
   - `` `10`{pd: sum(full:/file_collections/0/resources, bytes)} ``
   - `` `64/75`{pd: ratio(receipt:/coverage/with_receipt, receipt:/coverage/receiptable)} ``
   - `` `longitudinal, multimodal study`{pd: chunk:c002} ``
   - `` `distributions`{pd: schema:CoreDataset.distributions} ``
   - `` `nonexistent_slot`{pd: schema:!CoreDataset.nonexistent_slot} ``
2. **Bracketed Span + HTML Comment Watermark** (renders invisibly in standard Markdown viewers):
   - `[AI-READI]<!-- pd: full:/title -->`
   - `[4.5 Å]<!-- pd: chunk:c002 -->`

#### Verification Engine (`provedown.check_provedown`)
- Evaluates every watermark deterministically against `{full, core, snapshot, receipt, manifest, chunks, declared}`.
- Emits structured findings for any watermark mismatch:
  - `provedown_value_mismatch`: inline text disagrees with the resolved artifact value/count/sum/ratio;
  - `provedown_path_missing`: JSON pointer does not resolve in the named artifact;
  - `provedown_snippet_not_found`: inline text or quoted snippet does not verify in the named chunk via `receipts.snippet_in`;
  - `provedown_schema_contradicted`: inline schema claim disagrees with `declared` class/slot inventory;
  - `provedown_syntax_error`: malformed watermark expression.
- **Integration with `report_claims.py`**:
  - `check_report(..., check_watermarks: bool = False)` (or `instrument_version >= 9`) includes a `provedown` sub-block and optionally surfaces watermark mismatches.
  - Default `instrument_version=8` (and `v7`) leaves `check_report` output byte-for-byte identical for all existing corpus tests.

---

### 2.4 Upgrade 4: Declarative Transformation Receipts via `linkml-map` (`linkml_mappings/full-to-core-mapping.yaml` & `transformation_receipts.py`)

#### Declarative Specification (`linkml_mappings/full-to-core-mapping.yaml`)
- Authored as a valid `linkml_map.datamodel.transformer_model.TransformationSpecification` document mapping `Dataset` $\rightarrow$ `CoreDataset`, `FileCollection` $\rightarrow$ `CoreDistribution`, and `File` $\rightarrow$ `CoreDistribution`.
- Explicitly declares:
  - All 64 shared identity slots (`populated_from: <slot>`),
  - `conforms_to_class`: constant `CoreDataset`,
  - `distributions`: derived from `file_collections[]` (with `bytes` $\leftarrow$ `total_bytes`) followed by `file_collections[].resources[]` (projecting `CoreDistribution` slots),
  - `dialect`: conditional consensus aggregation `unique_consensus(file_collections[*].resources[*].dialect)`,
  - `resources`: recursive `Dataset` $\rightarrow$ `CoreDataset` derivation on nested dataset resources.

#### Transformation Receipt Emission & Verification (`transformation_receipts.py`)
- `load_transformation_spec()` loads `linkml_mappings/full-to-core-mapping.yaml` and validates it with `linkml_map.datamodel.transformer_model.TransformationSpecification` (importing `transformer_model` directly to avoid `ucumvert`'s Python 3.13 `KeyError: 'millimeter_Hg'` in `unit_conversion.py`).
- `derive_core_declarative(full, ps=None)` executes the declarative `TransformationSpecification` and is verified by unit tests to be 100% identical to `derive_core.derive_core(full, ps)`.
- `emit_transformation_receipt(full, core, ps=None)` emits a structured receipt documenting:
  - `instrument`: `"transformation_receipts v1 (linkml-map)"`
  - `spec_sha256`: SHA-256 of `linkml_mappings/full-to-core-mapping.yaml`
  - `source_sha256` & `target_sha256`: canonical JSON SHA-256 of `full` and `core`
  - `field_traces`: list of `{target_path, source_paths, class_derivation, slot_derivation, rule}` for every populated path in `core`
  - `core_path_map`: exact `full_path -> core_path` dictionary matching `receipts.core_path_map(full)`
- `verify_transformation_receipt(tx_receipt, full, core, ps=None)` recomputes the declarative projection and verifies that:
  1. `spec_sha256`, `source_sha256`, and `target_sha256` match;
  2. every populated field in `core` is accounted for by a declared `ClassDerivation.slot_derivations` rule in `full-to-core-mapping.yaml`;
  3. every `field_trace` holds between `full` and `core`;
  4. `core_path_map` matches `receipts.core_path_map(full)`.

---

## 3. Touchpoint Analysis (Guardrails §3)

| Subsystem | Files Touched / Affected | Impact & Compatibility Guarantees |
|---|---|---|
| **1. API receipt path** | `src/data_sheets_schema/receipts.py`, `receipt_completion.py`, `receipt_completion_policy.py`, `rereceipt.py`, `canary.py` | `v3` and `v4` code paths are untouched unless `instrument_version=5` (or `receipt_format_version: 5`) is passed. In `v5`, `unverified_tool_receipt` and `populated_slot_refuted_by_receipt` join `canary.receipt_floors` alongside `unverified_snippet`. Designed against `A13`'s versioned fence unwrap (`#5116`) and the `receipted_part` floor basis (`with_receipt / (receiptable - added_after_receipt_unmatched)` per D32 / A13 F1). **Instrument-4 counter to name in `v5`:** A13 F1 added `slots.added_after_receipt_unmatched` to instrument-4 blocks (`receipts.py:1717-1718`) without modifying `RERECEIPTS_INSTRUMENT` (`receipts.py:269-273`, which is hashed into the rereceipt-policy and receipt-completion identities); `v5`'s instrument string (`RECEIPTS_V5_INSTRUMENT`) must explicitly name `added_after_receipt_unmatched` alongside `never_receipted` and `added_after_receipt`. |
| **2. Native receipt policy v1 & receipt-origin (Track N, codex)** | `native_shared_receipts.py`, `receipt_origin.py`, `receipt_origin_record.py` | `receipt_origin.py` classifies `(chunk, snippet, slot)` triples from Write/Edit tool calls. For `v5` entries carrying `supports`/`evidence_source`/`explanation`, `(chunk, snippet, slot)` extraction remains identical. For `v5` tool-only entries without `snippet`, `receipt_origin` can either key on `(chunk, f"tool:{tool.name}:{tool.result}", slot)` in a future `receipt_origin_version=2` or leave `v1` native runs on `receipt_instrument_version=4`. Track N's current canary (`N1`/`N2`) stays on `instrument_version=4`. |
| **3. Report checks** | `src/data_sheets_schema/provedown.py` (new), `src/data_sheets_schema/report_claims.py`, `report_audit_totals.py` (`#5094`), `evidence_assertions.py` | `provedown.py` is self-contained. `report_claims.check_report` runs `provedown` only when `check_watermarks=True` or `instrument_version >= 9`, keeping `v7` and `v8` corpus inventories (`tests/data/report_claims_origins.json`, `test_report_claims_corpus.py`) 100% unchanged. Orthogonal to `report_audit_totals.py` (`#5094`), which checks finding-count tables/prose headers. |
| **4. Blind review pack & evaluation (Track E)** | `blind_review_pack.py`, `registered_eval_runner.py` | Blind review packs strip provenance/receipt sidecars before presenting `full`/`core` YAML to reviewers; `v5` receipt sidecar fields (`supports`, `evidence_source`, `explanation`, `tool`) live in `{PROJECT}_coverage_receipt.yaml` and `{PROJECT}_receipts.yaml`, so `blind_review_pack.py` requires no changes and leaks no arm fingerprint. |
| **5. Existing 280+ corpus records, `backfill-checks`, and `recheck-validation`** | `backfill_checks.py`, `tests/test_backfill_checks.py`, `tests/test_receipts.py` | `receipts.block_for` defaults to `instrument_version=4` when a run has a `phase1_snapshot` and `instrument_version=3` otherwise, unless `receipt.get("receipt_format_version") == 5`. All 280+ existing records have no `receipt_format_version: 5`, so `backfill-checks` and `recheck-validation` reproduce every stored `v3`/`v4` block byte-for-byte. |

---

## 4. Proposed Issues to File (Pending User Outbound Approval)

1. **Issue 1:** `receipts v5: support structured polarity (supports), evidence_source, explanation, and fast entailment check on receipt entries`
2. **Issue 2:** `receipts v5: deterministic tool and computation receipts for non-text evidence (checksums, byte counts, manifest/record aggregations, unit conversions)`
3. **Issue 3:** `provedown: inline verifiable watermarks for reconciliation reports (report_claims v9 opt-in)`
4. **Issue 4:** `derive_core / linkml-map: declarative Dataset -> CoreDataset TransformationSpecification and verifiable transformation receipts`
