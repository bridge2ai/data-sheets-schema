# CHORUS v10 API Canaries Outcome (`2026-10-20a` & `2026-10-22a`)

## 1. Run Identification & Commits on `origin`

| Field | Canary 1 (`2026-10-20a`) | Canary 2 (`2026-10-22a`) |
|---|---|---|
| Label | `2026-10-20a_claude-opus-5-api-generic-v10_rep1` | `2026-10-22a_claude-opus-5-api-generic-v10_rep1` |
| Project / Arm / Replicate | `CHORUS` / `baseline` / `1` | `CHORUS` / `baseline` / `1` |
| Method / Condition | `claudecode_api` / `generic_v10` | `claudecode_api` / `generic_v10` |
| Model (recorded) | `claude-opus-5` | `claude-opus-5` |
| Provider | `LBL CBORG (proxy to Anthropic)` | `LBL CBORG (proxy to Anthropic)` |
| Registration commit (`origin`) | `8074af409c86182c4338148c8240663fc7df34a3` | `723c8ac20fc06fa63cf9ef92d74db71a7ca7aa14` |
| Run completion commit (`origin`) | `723c8ac20fc06fa63cf9ef92d74db71a7ca7aa14` | `77b94e4577de080bbbe8a645a4a0c38fa52e149b` |

## 2. Token Limits & Operational Outcome

| Parameter | `2026-10-20a` | `2026-10-22a` |
|---|---|---|
| `worker_output_tokens` | `25,000` (initial reg `57d5c842…`) → `64,000` (re-registered mid-run as `4f94102c…`) | `64,000` |
| `omission_output_tokens` | `16,000` → `32,000` | `32,000` |
| `integration_output_tokens` | `16,000` → `32,000` | `32,000` |
| `aggregate_output_tokens` | `150,000` → `320,000` | `320,000` |
| Settled ledger rows | `11` | `9` |
| Settled tokens (`in` / `cache_write` / `cache_read` / `out` / `thinking`) | `635,380` / `1,166,983` / `0` / `404,676` / `178,218` | `383,654` / `930,576` / `32,869` / `296,799` / `151,770` |
| Abandoned calls | `1` (`report`, `RemoteProtocolError`, `$0.85`; plus 1 settled typed-audit worker `eb3330ce` that hit `max_tokens` at `25,000`, `$1.50`) | `1` (`typed_audit_integration`, `ReadTimeout`, `$1.98`) |
| `report_regate` triggered | Yes (`1` regate call `a42e7689`, `$3.22`, not preserved; final `CHORUS_reconciliation.md` is an operator-edited copy of rejected response `72ac7d9a`, see §5) | No (`0` retries; initial `report` passed `report_claims` with 0 findings) |

## 3. Cost & D07 Budget Accounting

Costs computed by `data_sheets_schema.dollar_readout.price_settled_rows` (which prices `input`, `output`, `cache_read`, and `cache_write` tokens at `claude-opus-5` rates):

| Metric | `2026-10-20a` | `2026-10-22a` | Combined |
|---|---|---|---|
| Settled ledger cost | **$20.59** (11 rows) | **$15.17** (9 rows) | **$35.76** |
| Abandoned call cost | **$0.85** (`report`) | **$1.98** (`typed_audit_integration`) | **$2.83** |
| Total cost incl. abandoned calls | **$21.44** | **$17.15** | **$38.59** |

- **D07 CHORUS canary allocation**: `$15 + $15 = $30.00` across at most 2 billed attempts.
- **Status**: Both billed attempts are used, and combined spend (`$35.76` settled / `$38.59` including abandoned calls) exceeds the `$30.00` CHORUS canary allocation by `$5.76` settled (`$8.59` including abandoned calls).

## 4. Coverage, Gate Verdict & Quality Metrics

| Metric | `2026-10-20a` | `2026-10-22a` |
|---|---|---|
| Registered `coverage_floor` | `{"state": "pending", "mode": "diagnostic_pilot"}` (gated with no numeric floor) | `{"state": "pending", "mode": "diagnostic_pilot"}` (gated with no numeric floor) |
| Gate verdict (`canary.status`) | **`unmeasurable`** (regression: snippets unverified `1` vs floor `0`) | **`unmeasurable`** (no regressions) |
| Unverified snippet floor (`unverified_snippet_floor`) | `0` (observed: **`1`** unverified snippet in `receipts.snippets`, `114/115` verified; `source_caveats`, `c003`) | `0` (observed: **`0`** unverified snippets in `receipts.snippets`, `133/133` verified) |
| Record slot coverage (`receipts.slots`: `with_receipt / populated`) | **`58 / 63`** (`0.9206`; `5` slots added in Phase 3 after the Phase 1 receipt, `9` exempt) | **`64 / 75`** (`0.8533`; `11` slots added in Phase 3 after the Phase 1 receipt, `15` exempt) |
| Receipt-completion view (`receipt_completion.slots`, Phase 1 snapshot) | `51 / 58` → `58 / 58` (`1.0`) | `52 / 64` → `64 / 64` (`1.0`) |
| `validation.full` / `validation.core` | `passed: true` / `passed: true` (`32` / `31` top-level slots) | `passed: true` / `passed: true` (`36` / `35` top-level slots) |
| `pair_consistency` | `consistent: true` (`0` errors, `0` warnings, `33` identity slots) | `consistent: true` (`0` errors, `0` warnings, `33` identity slots) |
| `report_claims` (instrument `v8 (#1808)`) | `0` findings (`14` claims checked, `0` prose-retention claims, `14` disposition rows; measured on operator-edited report, see §5) | `0` findings (`19` claims checked, `1` prose-retention claim, `18` disposition rows) |
| `grounding` | `124/124` identifiers grounded (`0` ungrounded) | `122/122` identifiers grounded (`0` ungrounded) |
| `form` defects | `0` across all 5 defect classes | `0` across all 5 defect classes |

## 5. Provenance & Integrity Disclosures (`pr5096_review_2026-10-23.md` F1, F5, F6)

1. **`2026-10-20a` report is an operator-edited copy of the rejected model response (`F1`, owner decision `D-F` pending)**:
   - `CHORUS_reconciliation.md` (`sha256: 543511e9…`) equals `intermediate/CHORUS_report.md` and `intermediate/CHORUS_report_before_regate.md`. It is the rejected `report` response (`intermediate/CHORUS_report_rejected_response_72ac7d9a….txt`) with two operator edits applied after the `report_regate` call (`usage_id: a42e7689`, `$3.22`, not preserved) failed `report_evidence_2.json`: (a) 4 `source_review` rows had `source_status` flipped from `"capability"` to `"fact"` on `claim_status: "fact"` rows, and (b) `## Evidence assertions` JSON was flattened from `{text, evidence}` wrappers to flat strings.
2. **`2026-10-20a` ran across three commits and two registrations (`F5`)**:
   - The `full` phase ran at `9abe907b7`, the `receipt_completion` call ran at `8074af409`, and the saved receipt-completion response was re-parsed at `723c8ac20`. The first `typed_audit` worker (`eb3330ce`) ran under registration `57d5c842…` (`max_tokens: 25000`, `max_paths: 384`, `max_inventory_bytes: 65536`) and hit `max_tokens` with 0 visible characters; the registration was then overwritten in place as `4f94102c…` (`max_tokens: 64000`, `max_paths: 80`, `max_inventory_bytes: 12288`) and the run resumed under the same `generation_id`.
3. **Different report and typed-audit contract text between `2026-10-20a` and `2026-10-22a` (`F6`)**:
   - Commit `77b94e457` (between `2026-10-20a` and `2026-10-22a`) added report-contract and typed-audit instruction rules in `api_runner.py` and `audit_batch_format.py` without bumping `render_version: 25`.
