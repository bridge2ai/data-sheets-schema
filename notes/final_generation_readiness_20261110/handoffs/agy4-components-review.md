# G4 Read-Only Commit Review — `tests/test_final_record_component_limits.py` (`422f79605`)

- **Reviewer**: `agy4` (`G4`, read-only reviewer; `0` executions, `0` imports, `0` GitHub writes)
- **Reviewed Worktree & Branch**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-record-components-20261110` (`codex/final-record-components-20261110`)
- **Reviewed Commit**: `422f796059402a7cf047aa05da3bcd5d6236ae2b` (`422f79605`), parent `7233f193ad102a8488b31ec7333662c8fefaa996` (`main`)
- **Changed Files**: `1 file changed, 140 insertions(+)` — adds only `tests/test_final_record_component_limits.py` (`sha256: 851acb67e7e8a7bb1a0d66d8d23393aee1eaae31833ed01c39ee4c104880f40b`)

---

## 1. Verdict

**PASS (`0` blockers, `0` P1/P2 findings, `1` optional P3 observation).**

The commit cleanly extracts two self-contained, portable component tests against `main` (`7233f193ad102a8488b31ec7333662c8fefaa996`) with no native-stack or ad-hoc helper dependencies, zero production edits, all persisted evidence confined to `tmp_path`, and explicit non-claims for whole-pipeline acceptance.

---

## 2. Source-Grounded Verification Against `main` (`7233f193ad102a8488b31ec7333662c8fefaa996`)

1. **Chunking and bundle-chunk loading (`tests/test_final_record_component_limits.py:16-20, 37-45`)**:
   - `BUNDLE` begins with `FILE: protocol.txt\nPATH: protocol.txt\n`, matching the document-boundary rule in [src/data_sheets_schema/chunking.py](../../../src/data_sheets_schema/chunking.py) (`_documents`, `lines 79–90`).
   - `chunking.manifest_from_bytes(BUNDLE, "n1-fictional-bundle.txt")` (`chunking.py:159-178`) deterministically builds a 1-chunk manifest (`c001`, `source: "protocol.txt"`), and `evidence_assertions.source_chunks_from_bytes(BUNDLE, yaml.safe_dump(manifest).encode())` ([src/data_sheets_schema/evidence_assertions.py](../../../src/data_sheets_schema/evidence_assertions.py), `lines 575–586`) validates the manifest mapping and returns `chunks["c001"]`.

2. **Receipt-v4 vacuity vs. literal identifier attestation (`tests/test_final_record_component_limits.py:48-100`)**:
   - Invokes `receipts.check(..., instrument_version=4, identifier_bases=())` ([src/data_sheets_schema/receipts.py](../../../src/data_sheets_schema/receipts.py), `lines 2025–2054`) and `canary.receipt_floors(block)` ([src/data_sheets_schema/canary.py](../../../src/data_sheets_schema/canary.py), `lines 291–334`) over `record = {"id": IDENTIFIER}`.
   - Because top-level `id` (`"https://example.org/dataset/n1-fictional"`) is neither in `EXEMPT_SLOTS`/`EXEMPT_LEAVES` nor a `#`-fragment/URN (`receipts.py:398-446, 1736-1742`), `slots.receiptable == 1`.
   - **`unattested` mode (`lines 57–61, 91–95`)**: `status: "nothing_relevant"` with a non-empty `reason` yields `chunks.total == 1`, `chunks.reviewed == 1`, `snippets.verified == 0`, and `floors["receipts vacuous"] == 1` (`canary.py:316`).
   - **`literal_identifier_only` mode (`lines 62–70, 96–100`)**: `status: "extracted"` with `slot: "id"` and the verbatim snippet `"The dataset identifier is https://example.org/dataset/n1-fictional."` satisfies `snippet_in` and `#720` length/token floors (`receipts.py:2215-2237`), yielding `snippets.verified == 1`, `slots.receiptable == 1`, `slots.with_receipt == 1`, and `not any(literal["floors"].values())` (note that `receipt_coverage_floor` returns `None` when `receipt_completion_policy.BLOCK_KEY` is absent, `canary.py:337-341`).

3. **Protocol-7 source-review coverage vs. omission recall (`tests/test_final_record_component_limits.py:103-140`)**:
   - Invokes `source_review.check(review, raw=FULL.decode(), artifact="final_full", chunks=chunks, protocol_version=7)` ([src/data_sheets_schema/source_review.py](../../../src/data_sheets_schema/source_review.py), `lines 65–188`).
   - `source_review.inventory` (`lines 32–62`) enumerates only populated scalars in `FULL` (`/id`). The single supported `fact` claim covers all characters of `/id` (`lines 106–120, 165–166`) and passes `evidence_assertions.check_assertions` (`lines 148–153`), returning `checked["findings"] == []` and `checked["claims_checked"] == 1` even though the second bundle sentence (`"The fictional dataset contains two measurement tables."`) is absent from `FULL`.

4. **Artifact confinement & non-overclaiming (`tests/test_final_record_component_limits.py:1-6, 23-35, 83-90, 129-138`)**:
   - `save_evidence` writes only `(tmp_path / (name + ".json"))` with exclusive creation mode `"x"`.
   - Both saved JSON payloads and the module docstring explicitly state `whole_native_acceptance: "unverified"`, `whole_generation_acceptance: "unverified"`, and the unexercised layers (`typed assembly reconstruction`, `registered receipt policy admission`, `omission recall`, `complete final-evidence gate`, `complete native or API acceptance`).

---

## 3. Concrete Findings

- **Blocking (`P0`/`P1`/`P2`)**: None (`0`).
- **Optional / Non-Blocking (`P3-1` -> `#5802`, fixed in `9fb93110e`)**:
  - In `test_receipt_v4_distinguishes_unattested_stub_from_identifier_attestation` (`lines 91–95`), `empty` asserts `empty["floors"]["receipts vacuous"] == 1` alongside `total == 1`, `reviewed == 1`, and `verified == 0`, but does not explicitly assert `empty["checked_block"]["findings"] == []` (or `empty["floors"]["receipt findings"] == 0`). Recorded as `#5802` and addressed in `9fb93110e` (`tests/test_final_record_component_limits.py:92, 98`).
