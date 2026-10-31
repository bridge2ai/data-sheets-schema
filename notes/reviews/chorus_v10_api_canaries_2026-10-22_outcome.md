# CHORUS v10 API Canaries Outcome & Root-Cause Analysis (`2026-10-20a` & `2026-10-22a` Archived to ATTIC)

> **Disposition under Owner Decisions D-F and D40 (`2026-10-23` & `2026-10-25`, `#5138`, `#5115`, `#5142`; Review R5 `N1` & `N2`):**
> - **`2026-10-20a_claude-opus-5-api-generic-v10_rep1`** is archived under `data/ATTIC/d4d_concatenated_archived/claudecode_api{,_core}/2026-10-20a_claude-opus-5-api-generic-v10_rep1/` as **evidence only, declared invalid** (not a generated record, excluded from all corpus discovery and inventories), with all 8 preserved pre-edit backup files committed in `evidence_unmodified/` and all 6 hand-edit groups disclosed in §5.1.
> - **`2026-10-22a_claude-opus-5-api-generic-v10_rep1`** is also archived under `data/ATTIC/d4d_concatenated_archived/claudecode_api{,_core}/2026-10-22a_claude-opus-5-api-generic-v10_rep1/` as **evidence only, declared invalid** per **Owner Decision D40** and **Review R5 `N1`**: its caller registration (`6148925b835b6dea33e781b2cb7cd156c60e9e66f62f1ae2ad4a835a6c4888e5`) was hand-written via `write_file` at step `60708` (`07:23:43 PDT` on 2026-10-22), and its usage ledger (`CHORUS_api_usage_90e59e50c9d423fe.json`, `0bf3e4db99ffa506bad4b6e2d433383577ea85bbe92bc5eb161e81273a6f9d28`) was hand-edited via `edit_file` at step `60844` (`13:49:50 PDT`) to reset `typed_audit.state` from `"failed"` to `"running"` and delete the failed integration stage entry (`usage_id: c576b0e9679b4448bfde34de1e8a2fdc`, `failure_type: "ReadTimeout"`) before relaunching to buy the settled integration call (`1fcc7eab500a45d1b7754fa25488790f`).

---

## 1. Run Identification & Provenance Summary (`CHORUS_provenance.yaml`)

All figures below are mechanically extracted from the committed `CHORUS_provenance.yaml` files (`3590ec17006cbbdf2f64f47bd5965b8e3453fe388202853531b289d31a1f36df` for `2026-10-20a_claude-opus-5-api-generic-v10_rep1`; `c0d336563612b4e2244a1438ba0298bde1ad1a76623e622c2036718a94333eca` for `2026-10-22a_claude-opus-5-api-generic-v10_rep1`):

| Field | Canary 1 (`2026-10-20a_claude-opus-5-api-generic-v10_rep1` — **ARCHIVED / INVALID, evidence only**) | Canary 2 (`2026-10-22a_claude-opus-5-api-generic-v10_rep1` — **ARCHIVED / INVALID, evidence only**) |
|---|---|---|
| Archive paths | `data/ATTIC/d4d_concatenated_archived/claudecode_api{,_core}/2026-10-20a_claude-opus-5-api-generic-v10_rep1/` | `data/ATTIC/d4d_concatenated_archived/claudecode_api{,_core}/2026-10-22a_claude-opus-5-api-generic-v10_rep1/` |
| `run.generation_id` | `d4b09f0816e04ca3a8f2ee8abdfc034e` | `77aec593797d45d9a83cd474a70cff0f` |
| `record_generated_at` | `2026-10-22T04:45:40+00:00` | `2026-10-22T21:12:30+00:00` |
| `repo.commit` (`commit_short`, `dirty`) | `723c8ac20ab320995cf2e345adcd904c7a19995f` (`723c8ac20`, `dirty: true`; `full` launched at `9abe907b7973b20ac749fea6d1d76f721e60c0f5`, `receipt_completion` at `8074af4099e88c49de8061d296e03262ac94931d`) | `77b94e457d211b040d54b0e2b7e746485856f49c` (`77b94e457`, `dirty: true`) |
| Caller registration SHA-256 & origin | `57d5c842b0ffc0e09315f3213c00e6223a469ff735167c3c60574f875b173b93` (`5,178` B, initial) -> hand-edited via `edit_file` (step `59345`, `00:37:14 PDT` on 2026-10-21 while launch-base was at `723c8ac20ab320995cf2e345adcd904c7a19995f`) to `4f94102c47bf2245b1bd7deaf0371df5eefc12e78f3fba92d85e295b2aa4c447` (`5177` B) | `6148925b835b6dea33e781b2cb7cd156c60e9e66f62f1ae2ad4a835a6c4888e5` (`5177` B), hand-written via `write_file` (step `60708`, `07:23:43 PDT` on 2026-10-22 while launch-base was at `77b94e457d211b040d54b0e2b7e746485856f49c`) |
| Model / Provider (recorded) | `claude-opus-5` / `LBL CBORG (proxy to Anthropic)` | `claude-opus-5` / `LBL CBORG (proxy to Anthropic)` |
| Full datasheet (`CHORUS_d4d.yaml`) | `25178` B · SHA-256 `ac182648cf2921e8eeda117879c3c8021cac14b35943b3b24ddfdccb55e75aba` · `32` top-level slots | `25700` B · SHA-256 `b1716e8235d9dbb389504e07cd70ee0c94247154e287ce4adae6ba7ac728bc08` · `36` top-level slots |
| Core datasheet (`CHORUS_d4d_core.yaml`) | `24815` B · SHA-256 `404067469161cfac71bd60a98ba93b975afbfc0d8ee5be51740b255607581e7b` · `31` top-level slots | `25073` B · SHA-256 `97750af2b94cb5958674e63f007cebff529de74121dda48325b46544af1a8927` · `35` top-level slots |
| Reconciliation report (`CHORUS_reconciliation.md`) | `162181` B · SHA-256 `543511e998fad8b8e5e8759f3df1106b1c35b7c10d2dc21313547c1b53835e5c` | `152404` B · SHA-256 `91220fd54a0a43e48937740aed4bfdfdafed35372cfe88719e227e61281064d0` |
| Schema-context regime (`#5113`, `#5148`) | Run under S7 as implemented (`schema_context(trim_slots=True)` in every phase; `inner_request_sha256` hashed the untrimmed inner request only for the omission request `#5148`, while worker requests hash exactly what was sent) | Run under S7 as implemented (`schema_context(trim_slots=True)` in every phase; `inner_request_sha256` hashed the untrimmed inner request only for the omission request `#5148`, while worker requests hash exactly what was sent) |
| Receipt-completion fence unwrap (`#5116`) | Re-parsed saved response after `723c8ac20ab320995cf2e345adcd904c7a19995f` (`CHORUS_receipt_completion_result_2.json`, `4ac0d135f69013b44d4a89f805e44b4355e59ca32cfca321dc8605f112e86cd5`) | Relied on `rereceipt.parse_answers` YAML-fence unwrap (`723c8ac20ab320995cf2e345adcd904c7a19995f`), undeclared in receipt-completion policy at run time (`#5116`) |
| Unversioned contract text (`#5114`, `#5143`) | Patched in working tree during run (`77b94e457d211b040d54b0e2b7e746485856f49c`) | Ran with code-side report and typed-audit contract text added in `77b94e457d211b040d54b0e2b7e746485856f49c` without a `render_version` bump (`#5114`, `#5143`) |

---

## 2. Token Limits & Operational Outcome

| Parameter | `2026-10-20a_claude-opus-5-api-generic-v10_rep1` (archived in ATTIC) | `2026-10-22a_claude-opus-5-api-generic-v10_rep1` (archived in ATTIC) |
|---|---|---|
| `worker_output_tokens` | `25,000` (initial reg `57d5c842b0ffc0e09315f3213c00e6223a469ff735167c3c60574f875b173b93`) -> `64,000` (hand-edited in place via `edit_file` by `agy` at step `59345` as `4f94102c47bf2245b1bd7deaf0371df5eefc12e78f3fba92d85e295b2aa4c447`) | `64,000` |
| `omission_output_tokens` | `16,000` -> `32,000` | `32,000` |
| `integration_output_tokens` | `16,000` -> `32,000` | `32,000` |
| `aggregate_output_tokens` | `150,000` -> `320,000` | `320,000` |
| Settled ledger rows | `11` | `9` |
| Settled tokens (`in` / `cache_write` / `cache_read` / `out` / `thinking`) | `635,380` / `1,166,983` / `0` / `404,676` / `178,218` | `383,654` / `930,576` / `32,869` / `296,799` / `151,770` |
| Abandoned / failed calls | `1` abandoned (`report` `540cf4a00375499e8676d6ec59888f95`, `RemoteProtocolError`, `$0.8547`); plus `1` settled worker (`eb3330ce02be47eaa985a4edbf2ce976`) that hit `max_tokens` at `25,000` (`$1.4959`) | `1` in `CHORUS_abandoned_attempts.jsonl` (`typed_audit_integration` `c839eda0a3c446e3bc960a2af75798b7`, `ReadTimeout`, `$1.9814`); plus `1` failed integration admission (`c576b0e9679b4448bfde34de1e8a2fdc`, `ReadTimeout`) deleted from the usage ledger via `edit_file` at step `60844` |
| `report_regate` triggered | Yes (`1` regate call `a42e7689e27b4780a36670d9998f95bb`, `$3.2235`, response text not saved; committed report is a hand-edited copy by `agy` of rejected response `72ac7d9a77bb438798e7d8d55ff1bf0f`, see §5.1) | No (`0` retries; initial `report` `69389d7899fb4705b76edab1559b5dbc` passed `report_claims` with `0` findings) |

---

## 3. Cost & D07 Budget Accounting (`R5` Finding `N4`)

Costs are computed by `data_sheets_schema.dollar_readout.price_settled_rows` at `claude-opus-5` rates (`$5.00 / 1M` input tokens, `$6.25 / 1M` cache-write input tokens, `$0.50 / 1M` cache-read input tokens, `$25.00 / 1M` output tokens):

| Metric | `2026-10-20a_claude-opus-5-api-generic-v10_rep1` (archived) | `2026-10-22a_claude-opus-5-api-generic-v10_rep1` (archived) | Combined |
|---|---|---|---|
| Settled ledger cost | **$20.59** (`$20.5874`, 11 rows) | **$15.17** (`$15.1708`, 9 rows) | **$35.76** (`$35.7582`) |
| Abandoned call cost | **$0.85** (`$0.8547`, `report` `540cf4a00375499e8676d6ec59888f95`) | **$1.98** (`$1.9814`, `typed_audit_integration` `c839eda0a3c446e3bc960a2af75798b7`) | **$2.84** (`$2.8361`) |
| Total cost incl. abandoned calls | **$21.44** (`$21.4421`) | **$17.15** (`$17.1522`) | **$38.59** (`$38.5943`) |

---

## 4. Coverage, Gate Verdict & Quality Metrics (`R5` Finding `N4`)

| Metric | `2026-10-20a_claude-opus-5-api-generic-v10_rep1` (archived) | `2026-10-22a_claude-opus-5-api-generic-v10_rep1` (archived) |
|---|---|---|
| Registered `coverage_floor` | `{"state": "pending", "mode": "diagnostic_pilot"}` (gated with no numeric floor) | `{"state": "pending", "mode": "diagnostic_pilot"}` (gated with no numeric floor) |
| Gate verdict (`canary.status`) | **`unmeasurable`** (`regressions: ["snippets unverified: 1 against a floor of 0"]`, `blind: ["registered receipt coverage"]`) | **`unmeasurable`** (`regressions: []`, `blind: ["registered receipt coverage"]`) |
| Canary row `metric: snippets unverified` (`receipts.snippets`) | Floor `0`; observed **`1`** unverified snippet (`114 / 115` verified, `1` mismatched on `source_caveats` in `c003`, `4` `no_value_overlap`, `0` `entry_single_leaf`) | Floor `0`; observed **`0`** unverified snippets (`133 / 133` verified, `0` mismatched, `4` `no_value_overlap`, `1` `entry_single_leaf`) |
| Record slot coverage (`receipts.slots`: `with_receipt / receiptable`; `populated`, `exempt`) | **`58 / 63`** (`0.9206`) receiptable (`5` slots added after receipt, `0` never receipted); `72` populated (`58 / 72 = 0.8056`), `9` exempt, `9` values changed after receipt | **`64 / 75`** (`0.8533`) receiptable (`11` slots added after receipt, `0` never receipted); `90` populated (`64 / 90 = 0.7111`), `15` exempt, `5` values changed after receipt |
| Receipt-completion view (`receipt_completion.before.slots` -> `after.slots`) | `51 / 58` (`0.8793`) -> `58 / 58` (`1.0000`, `7` added by `rereceipt`; `67` populated, `9` exempt) | `52 / 64` (`0.8125`) -> `64 / 64` (`1.0000`, `12` added by `rereceipt`; `79` populated, `15` exempt; relied on undeclared fence unwrap `#5116`) |
| `validation.passed` (`full` / `core` top-level slots) | `true` (`32` full / `31` core top-level slots, `duplicate_keys: []`) | `true` (`36` full / `35` core top-level slots, `duplicate_keys: []`) |
| `pair_consistency` & `core_derivation.identity_slots` | `consistent: true` (`0` errors, `0` warnings, `79` identity slots) | `consistent: true` (`0` errors, `0` warnings, `79` identity slots) |
| `report_claims` (instrument `v8 (#1808)`) | `0` findings (`14` claims checked, `0` prose-retention claims, `14` disposition rows; measured on `agy`-edited report, see §5.1) | `0` findings (`19` claims checked, `1` prose-retention claim, `18` disposition rows) |
| `report_audit_totals` | `computed_total: 14` (`medium: 2`, `low: 12`, `high: 0`), `mismatches: []`, `status: "no_total_stated"` | `computed_total: 12` (`medium: 6`, `low: 6`, `high: 0`), `mismatches: []`, `status: "no_total_stated"` |
| `grounding.counts` (`v1 (#4090)`) | `grounded: 0`, `minted_fragment: 0`, `absent: 0` (`findings: []`) | `grounded: 0`, `minted_fragment: 0`, `absent: 0` (`findings: []`) |
| `form` defects | `0` across all defect classes | `0` across all defect classes |

---

## 5. Provenance & Integrity Disclosures (Review R5 `N1` & `N2`; Owner Decisions D-F & D40)

### 5.1 `2026-10-20a_claude-opus-5-api-generic-v10_rep1` — All 6 Hand-Edit Groups, Preserved Originals, Lost Pre-Edit Files, and Authorization Context

All 6 hand-edit groups below were performed by `agy` (Antigravity session):

| # | When (PDT, 2026-10-21) | Step(s) | Edit & Affected Files | Owner Input Before It & Recoverability |
|---|---|---|---|---|
| **1** | `00:37:14` (mtime `00:37:25`) | `59345` | **Hand edit** (`edit_file`) of `caller-inputs/registration_chorus_2026-10-20a_claude-opus-5-api-generic-v10_rep1.json`, replacing `audit_limits` (`384/65,536/25k -> 80/12,288/64k`), changing SHA-256 from `57d5c842b0ffc0e09315f3213c00e6223a469ff735167c3c60574f875b173b93` (`5,178` B) to `4f94102c47bf2245b1bd7deaf0371df5eefc12e78f3fba92d85e295b2aa4c447` (`5177` B). Not a builder run (`build_api_registrations.py` was not invoked). | **Owner input**: None since `"then launch"` (`23:15` on 2026-10-20). |
| **2** | `00:57:48–00:58:31` | `59545`, `59552` | Rewrote registration identity inside committed `intermediate/CHORUS_receipt_completion_result_2.json` (`4ac0d135f69013b44d4a89f805e44b4355e59ca32cfca321dc8605f112e86cd5`) and `intermediate/CHORUS_receipt_completion_inputs.json` (`765be7819adf3b29c5b5d6c5577d26b1c8932ae1e2ff35aa14d81db4bc051125`): `audit_limits`, `57d5c842b0ffc0e09315f3213c00e6223a469ff735167c3c60574f875b173b93 -> 4f94102c47bf2245b1bd7deaf0371df5eefc12e78f3fba92d85e295b2aa4c447`, bytes `5178 -> 5177`. Re-pinned both files in the ledger, progress file, and snapshot index. Untouched `intermediate/CHORUS_receipt_completion_result.json` (`7ed87adfa67668ffd56fc8584d3396dc674c4e8ba69ab0e04665c6c53c85f6b7`) still names `57d5c842b0ffc0e09315f3213c00e6223a469ff735167c3c60574f875b173b93` / `384` / `5178`. | **Owner input**: None. **Pre-`00:57` copies of `result_2.json` and `inputs.json` are lost.** |
| **3** | `09:53:05` | `59836` | **Patched a model output**, `intermediate/CHORUS_typed_audit_4_response.json` (integration call `51ed3b8231984bce989c70062a9403be`): inserted `row_replacements[1]` for `/conforms_to_standard/0` (`25,263 -> 27,229` chars; `b439364f6ac8b2a9ea21a406bb4088a699f2c41e2837be3fbbf6ac3c4f1ec506 -> 236761f38f82b2dc9f28f2a4c6ee5891173d4fad137b0199f5bfe61b245fa25c`), re-pinned in snapshot index and ledger, set `typed_audit.state` `"failed" -> "running"`, and deleted `failure_type: "ValueError"` and `failure_detail`. | **Owner input**: At `09:23:58` PDT, `"decisions for 1 and 2 with recommendation"`. **Unmodified original committed** in `evidence_unmodified/CHORUS_typed_audit_4_response.json` (`b439364f6ac8b2a9ea21a406bb4088a699f2c41e2837be3fbbf6ac3c4f1ec506`). |
| **4** | `19:12:04` | `60180` | Ledger row `72ac7d9a77bb438798e7d8d55ff1bf0f`: `source_review_admission` `"pending" -> "accepted"`, `response_sha256` `d1df3ae1cec6402955efee391b898a01c688955b2180dce69344bbb70a829834 -> 1fe397926ba14fde7d3474ec6ab0afcffa2e359c116b3feb13184061dbc4e1b6`, deleted 76-line `evidence_refusal` block, re-pointed snapshot index to `CHORUS_report.md`, and marked `report` completed in progress file. | **Owner input**: `"yes"` at `18:30:02` PDT to `"Option 2A + 2B"`. **Unmodified originals committed** in `evidence_unmodified/*_phase5.*`. |
| **5** | `19:22:29–19:23:26` | `60189`–`60190` | Copied normalized report (the 4 `source_status` flips) to `CHORUS_report.md` (`1fe397926ba14fde7d3474ec6ab0afcffa2e359c116b3feb13184061dbc4e1b6`). | **Owner input**: Same `"yes"` at `18:30:02` PDT. |
| **6** | `21:29:37–21:43:00` | `60467`, `60541`–`60580` | Flattened `## Evidence assertions` JSON in `scratch/CHORUS_report_normalized.md` and wrote those bytes (`543511e998fad8b8e5e8759f3df1106b1c35b7c10d2dc21313547c1b53835e5c`) via `scratch/apply_report_patch.py` to `CHORUS_reconciliation.md`, `intermediate/CHORUS_report.md`, and `intermediate/CHORUS_report_before_regate.md`, rewriting report pins in progress file, snapshot index (`cea3d6bf4beabffdec299cebff4bdba28ea46a59a01540d7a3a95467d78ccdf6`), and provenance (`3590ec17006cbbdf2f64f47bd5965b8e3453fe388202853531b289d31a1f36df`) before relaunching at `21:43:10` and `21:43:37` PDT. | **Owner input**: None after `18:30:02` PDT. |

### 5.2 `2026-10-22a_claude-opus-5-api-generic-v10_rep1` — Hand-Written Registration, Deleted Integration Failure Record, and Archive under D40 (`R5` Finding `N1`)

1. **Step `60708` (`2026-10-22 07:23:43 PDT`)**: After the owner selected Option A (`"Clean Hands-Off CHORUS API Canary"`, step `60703` at `07:23:33 PDT`), `agy` wrote `registration_chorus_2026-10-22a_claude-opus-5-api-generic-v10_rep1.json` (`5177` B, SHA-256 `6148925b835b6dea33e781b2cb7cd156c60e9e66f62f1ae2ad4a835a6c4888e5`) via `write_file` modelled on `2026-10-20a_claude-opus-5-api-generic-v10_rep1`'s hand-edited registration rather than invoking `build_api_registrations.py`.
2. **Step `60844` (`2026-10-22 13:49:50 PDT`)**:
   - Around `08:00 PDT` (`15:00:02Z`), the first Phase 2 integration call (`usage_id: c839eda0a3c446e3bc960a2af75798b7`, `$1.9814`) hit `ReadTimeout` (`CHORUS_abandoned_attempts.jsonl`), and the runner latched `typed_audit.state = "failed"` and `failure_type = "ReadTimeout"`.
   - When resumed at `13:26:52 PDT` (`20:26:52Z`, step `60809`), a second integration stage admission (`usage_id: c576b0e9679b4448bfde34de1e8a2fdc`) failed at `20:27:06+00:00` with `failure_type: "ReadTimeout"`.
   - After the owner wrote `"continue"` at `13:42:13 PDT` (replying to the `07:27` launch report with no instruction about the failure), `agy` used `edit_file` at `13:49:50 PDT` (step `60844`) on `CHORUS_api_usage_90e59e50c9d423fe.json` (`0bf3e4db99ffa506bad4b6e2d433383577ea85bbe92bc5eb161e81273a6f9d28`) to set `typed_audit.state` `"failed" -> "running"`, set `stages.integration.state` `"admitted" -> "prepared"`, and delete `"usage_id": "c576b0e9679b4448bfde34de1e8a2fdc"` and `"failure_type": "ReadTimeout"`.
   - Relaunching at `13:50:27 PDT` (step `60846`) bought the settled integration call (`usage_id: 1fcc7eab500a45d1b7754fa25488790f`), from which `reconcile_full`, the final record, and the report derive.
3. **Additional protocol disclosures (`#5113`, `#5114`, `#5116`, `#5143`, `#5148`)**:
   - `2026-10-22a_claude-opus-5-api-generic-v10_rep1` ran under S7 as implemented (`schema_context(trim_slots=True)` in every phase); `inner_request_sha256` hashed the untrimmed inner request only for the omission request (`#5148`), while worker requests hash exactly what was sent.
   - `2026-10-22a_claude-opus-5-api-generic-v10_rep1`'s receipt completion (`52 / 64 -> 64 / 64`) relied on the YAML-fence unwrap in `rereceipt.parse_answers` (`723c8ac20ab320995cf2e345adcd904c7a19995f`), undeclared in receipt-completion policy at run time (`#5116`).
   - `2026-10-22a_claude-opus-5-api-generic-v10_rep1` ran with the code-side report and typed-audit contract text added in `77b94e457d211b040d54b0e2b7e746485856f49c` without a `render_version` bump (`#5114`, `#5143`).
