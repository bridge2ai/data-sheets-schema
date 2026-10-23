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
| `worker_output_tokens` | `25,000` | `64,000` |
| `omission_output_tokens` | `16,000` | `32,000` |
| `integration_output_tokens` | `16,000` | `32,000` |
| `aggregate_output_tokens` | `150,000` | `320,000` |
| Settled ledger rows | `11` | `9` |
| Settled tokens (`in` / `out` / `cache_read` / `cache_write` / `thinking`) | `70,928` / `101,852` / `326,396` / `146,593` / `9,106` | `64,458` / `88,979` / `205,280` / `96,731` / `12,186` |
| Abandoned calls | `1` (`report`, network drop) | `1` (`reconcile_full`, `max_tokens` hit at `16,000` before raise to `32,000`) |
| `report_regate` triggered | Yes (`1` retry; disposition table missing on initial `report`) | No (`0` retries; initial `report` passed `report_claims` with 0 findings) |

## 3. Cost & D07 Budget Accounting

Costs computed by `data_sheets_schema.dollar_readout.price_settled_rows` (which prices `input`, `output`, `cache_read`, and `cache_write` tokens at `claude-opus-5` rates):

| Metric | `2026-10-20a` | `2026-10-22a` | Combined |
|---|---|---|---|
| Settled ledger cost | **$20.59** (11 rows) | **$15.17** (9 rows) | **$35.76** |
| Abandoned call cost | **$0.85** (`report`) | **$1.98** (`reconcile_full`) | **$2.83** |
| Total cost incl. abandoned calls | **$21.44** | **$17.15** | **$38.59** |

- **D07 CHORUS canary allocation**: `$15 + $15 = $30.00` across at most 2 billed attempts.
- **Status**: Both billed attempts are used, and combined spend (`$35.76` settled / `$38.59` including abandoned calls) exceeds the `$30.00` CHORUS canary allocation by `$5.76` settled (`$8.59` including abandoned calls).

## 4. Coverage, Gate Verdict & Quality Metrics

| Metric | `2026-10-20a` | `2026-10-22a` |
|---|---|---|
| Registered `coverage_floor` | `{"state": "pending", "mode": "diagnostic_pilot"}` (gated with no numeric floor) | `{"state": "pending", "mode": "diagnostic_pilot"}` (gated with no numeric floor) |
| Gate verdict (`gate.verdict`) | **`unmeasurable`** | **`unmeasurable`** |
| Unverified snippet floor (`unverified_snippet_floor`) | `0` (observed: **`1`** unverified snippet in `receipts.snippets`, `114/115` verified) | `0` (observed: **`0`** unverified snippets in `receipts.snippets`, `133/133` verified) |
| Record slot coverage (`receipts.slots`: `with_receipt / populated`) | **`58 / 63`** (`0.9206`; `5` slots added in Phase 3 after the Phase 1 receipt) | **`64 / 75`** (`0.8533`; `11` slots added in Phase 3 after the Phase 1 receipt) |
| Receipt-completion view (`receipt_completion.slots`, Phase 1 snapshot) | `58 / 58` (`1.0`) | `64 / 64` (`1.0`) |
| `validation.full` / `validation.core` | `passed: true` / `passed: true` | `passed: true` / `passed: true` |
| `pair_consistency` | `consistent: true` (`0` errors, `0` warnings, `33` identity slots) | `consistent: true` (`0` errors, `0` warnings, `33` identity slots) |
| `report_claims` (instrument `v8 (#1808)`) | `0` findings (`14` claims checked, `0` prose-retention claims, `14` disposition rows) | `0` findings (`19` claims checked, `1` prose-retention claim, `18` disposition rows) |
| `grounding` | `124/124` identifiers grounded (`0` ungrounded) | `122/122` identifiers grounded (`0` ungrounded) |
| `form` defects | `0` across all 5 defect classes | `0` across all 5 defect classes |
