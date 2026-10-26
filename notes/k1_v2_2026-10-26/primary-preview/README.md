# K1 v2: A17 granularity, cache scenarios and context exposure

Offline decision evidence; **not launch clearance**. All costs transfer two assisted CHORUS histories to conformed old records. Actual v10 outputs and tokenization are unknown. Actual Kids First context rejects the AI-READI proxy, so its typed total stays UNKNOWN.

## Decision implications

D33's no-trim admission decision has exposure beyond Kids First. The table and complete component TSV distinguish expected-size failures from at-cap scenarios. Adding a cache breakpoint changes billing, not context admission. Finer workers reduce assigned inventory but repeat shared inputs and increase aggregate carry.

Recommendation: retain the fail-closed admission check and hold A21 while the owner chooses a bounded integration/carry design for the exposed projects. Reducing duplicated fixed context, constraining the worker response contract, or staged integration each changes model-facing inputs and needs a reviewed implementation before the D35 freeze. Raising aggregate budget or enabling cache alone cannot make an oversized individual request fit. Do not silently trim source or audit evidence.

The measured composition is A16 plus exact A17 partitioning and inherited #5087 sizing, not the later D39 launch contract. #5155's separate max-roster allowance uses its exact cached sizing functions; it is not the actual-roster expected cost.

## Cost against granularity

Costs include a 0.5 report-regate scenario from assisted history; this is not an estimated clean retry probability or authorization to repeat typed calls. Ordinary partial retry allowance is separate in JSON.

| Project / retained record | Plan | Workers | Largest assigned bytes / 12,288 | Expected dollars | Typed expected input | Typed at-cap input |
|---|---|---:|---:|---:|---:|---:|
| CHORUS / 2026-10-22a_claude-opus-5-api-generic-v10_rep1 | a17 | 3 | 12,249 | $19.31 | 1,004,610 | 1,111,192 |
| CHORUS / 2026-10-20a_claude-opus-5-api-generic-v10_rep1 | a17 | 3 | 12,116 | $19.18 | 990,227 | 1,094,177 |
| AI_READI / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | a17 | 14 | 12,008 | $89.39 | 9,205,235 | 9,574,750 |
| CM4AI / 2026-09-04g_claude-opus-5-api-generic-v8_rep1 | a17 | 8 | 12,071 | $47.36 | 4,036,028 | 4,318,821 |
| VOICE / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | a17 | 10 | 12,274 | $61.08 | 5,670,107 | 6,030,690 |
| VOICE_PEDIATRIC / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | a17 | 10 | 12,274 | $53.07 | 4,583,843 | 4,882,613 |
| KIDS_FIRST / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | a17 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

For the same 15-run known subtotal (4 CHORUS, 4 AI-READI, 3 CM4AI, 3 VOICE, 1 pediatric; primary retained record per project), excluding actual-context Kids First and optional crate arm:
- a17: $813.20 plus $10.86 ordinary partial-usage scenario.

12,288 bytes bounds assigned inventory, not response tokens. Each request also repeats the full inventory. A 64k output cap has no proven semantic adequacy guarantee; the JSON includes each worker's schema-valid response floor at four bytes/token, which is only a lower-size scenario.

## Hypothetical typed shared-prefix cache

The current wire puts worker-specific schema before the late shared_context. It cannot cache the requested whole bundle/records/receipt/manifest/schema content by merely marking the last block. A reorder/split is required and must be reviewed before D35. These numbers allocate a token proxy to that proposed common prefix; they do not implement or price a captured new request.

Existing cache-aware stage input rates are preserved outside that prefix. First call writes; later writes cost $6.25/M and reads $0.50/M using the historical K1 rate schedule. These scenarios change worker input billing only; omission/integration costs, output charges, context size and aggregate input stay fixed. The six completed 64k workers took 153.741–541.771s; start gaps 545/241/519/440s imply only one of four later calls within 300s if TTL starts at request start. A late-refresh interpretation gives four of four, but is unverified. Observed worker cache reads were zero. The 25% transfer and 100% later-hit cases are scenarios, not predictions. 3600s is unpriced; the pinned notes/matched_cborg_2026-09-13/budgeted_cborg.py _prepare guard rejects 1h on that registered pricing path.

| Project (primary A17) | Current cache-aware baseline | 300s start-clock transfer | All later hits, upper scenario |
|---|---:|---:|---:|
| CHORUS | $19.31 | $19.08 | $18.41 |
| AI_READI | $89.39 | $83.24 | $64.76 |
| CM4AI | $47.36 | $45.04 | $38.11 |
| VOICE | $61.08 | $57.61 | $47.18 |
| VOICE_PEDIATRIC | $53.07 | $50.78 | $43.91 |
| KIDS_FIRST | UNKNOWN | UNKNOWN | UNKNOWN |

## Every nonfitting measured request

Token shares are disjoint allocations of calibrated input estimates by serialized byte contribution, plus separately assigned future-response carries. They are not tokenizer measurements. `nonfitting_components.tsv` has every component and input percentage, including bundle, records, schema, worker outputs, audit/evidence carry and rejected report. Output reserve is separate. `report_after_repair` repeats the report proxy; future repaired record growth is unknown. Unbounded contradiction-list growth is not covered by a hard bound.

| Project / plan / retained record | Request | Scenario | Input | Output reserve | Total | Largest input components |
|---|---|---|---:|---:|---:|---|
| AI_READI / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | reconcile_full | at_cap_input_estimate | 1,318,697 | 128,000 | 1,446,697 | audit_carry 928,007 (70.4%); bundle 158,314 (12.0%); schema_context 157,228 (11.9%) |
| AI_READI / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | report | at_cap_input_estimate | 1,473,553 | 128,000 | 1,601,553 | audit_carry 928,007 (63.0%); schema_context 159,355 (10.8%); bundle 157,072 (10.7%) |
| AI_READI / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | report_after_repair | at_cap_input_estimate | 1,473,553 | 128,000 | 1,601,553 | audit_carry 928,007 (63.0%); schema_context 159,355 (10.8%); bundle 157,072 (10.7%) |
| AI_READI / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | report_regate | at_cap_input_estimate | 1,600,968 | 128,000 | 1,728,968 | audit_carry 928,007 (58.0%); schema_context 159,373 (10.0%); bundle 157,090 (9.8%) |
| AI_READI / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | typed_audit_integration | expected_input_tokens | 1,267,777 | 32,000 | 1,299,777 | worker_outputs 539,227 (42.5%); bundle 274,351 (21.6%); schema_context 245,490 (19.4%) |
| AI_READI / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | typed_audit_integration | at_cap_input_estimate | 1,637,292 | 32,000 | 1,669,292 | worker_outputs 896,000 (54.7%); bundle 274,351 (16.8%); schema_context 245,490 (15.0%) |
| CM4AI / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep1 | report | at_cap_input_estimate | 904,279 | 128,000 | 1,032,279 | audit_carry 544,007 (60.2%); bundle 121,403 (13.4%); schema_context 100,984 (11.2%) |
| CM4AI / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep1 | report_after_repair | at_cap_input_estimate | 904,279 | 128,000 | 1,032,279 | audit_carry 544,007 (60.2%); bundle 121,403 (13.4%); schema_context 100,984 (11.2%) |
| CM4AI / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep1 | report_regate | at_cap_input_estimate | 1,031,729 | 128,000 | 1,159,729 | audit_carry 544,007 (52.7%); rejected_report 128,014 (12.4%); bundle 121,445 (11.8%) |
| CM4AI / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep1 | typed_audit_integration | at_cap_input_estimate | 1,023,113 | 32,000 | 1,055,113 | worker_outputs 512,000 (50.0%); bundle 195,942 (19.2%); schema_context 152,542 (14.9%) |
| VOICE / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | reconcile_full | at_cap_input_estimate | 1,014,278 | 128,000 | 1,142,278 | audit_carry 672,007 (66.3%); bundle 142,059 (14.0%); schema_context 133,776 (13.2%) |
| VOICE / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | report | at_cap_input_estimate | 1,121,661 | 128,000 | 1,249,661 | audit_carry 672,007 (59.9%); bundle 141,109 (12.6%); schema_context 134,687 (12.0%) |
| VOICE / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | report_after_repair | at_cap_input_estimate | 1,121,661 | 128,000 | 1,249,661 | audit_carry 672,007 (59.9%); bundle 141,109 (12.6%); schema_context 134,687 (12.0%) |
| VOICE / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | report_regate | at_cap_input_estimate | 1,249,141 | 128,000 | 1,377,141 | audit_carry 672,007 (53.8%); bundle 141,157 (11.3%); schema_context 134,733 (10.8%) |
| VOICE / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | typed_audit_integration | expected_input_tokens | 978,843 | 32,000 | 1,010,843 | worker_outputs 378,095 (38.6%); bundle 221,675 (22.6%); schema_context 201,538 (20.6%) |
| VOICE / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | typed_audit_integration | at_cap_input_estimate | 1,253,844 | 32,000 | 1,285,844 | worker_outputs 640,000 (51.0%); bundle 221,675 (17.7%); schema_context 201,538 (16.1%) |
| VOICE_PEDIATRIC / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | reconcile_full | at_cap_input_estimate | 949,142 | 128,000 | 1,077,142 | audit_carry 672,007 (70.8%); schema_context 133,776 (14.1%); bundle 77,724 (8.2%) |
| VOICE_PEDIATRIC / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | report | at_cap_input_estimate | 1,056,960 | 128,000 | 1,184,960 | audit_carry 672,007 (63.6%); schema_context 134,686 (12.7%); records 89,854 (8.5%) |
| VOICE_PEDIATRIC / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | report_after_repair | at_cap_input_estimate | 1,056,960 | 128,000 | 1,184,960 | audit_carry 672,007 (63.6%); schema_context 134,686 (12.7%); records 89,854 (8.5%) |
| VOICE_PEDIATRIC / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | report_regate | at_cap_input_estimate | 1,184,419 | 128,000 | 1,312,419 | audit_carry 672,007 (56.7%); schema_context 134,733 (11.4%); rejected_report 128,014 (10.8%) |
| VOICE_PEDIATRIC / a17 / 2026-09-04f_claude-opus-5-api-generic-v8_rep1 | typed_audit_integration | at_cap_input_estimate | 1,127,714 | 32,000 | 1,159,714 | worker_outputs 640,000 (56.8%); schema_context 201,538 (17.9%); bundle 120,871 (10.7%) |
| KIDS_FIRST / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | reconcile_full | at_cap_input_estimate | 1,498,956 | 128,000 | 1,626,956 | audit_carry 1,056,007 (70.4%); bundle 203,679 (13.6%); schema_context 162,279 (10.8%) |
| KIDS_FIRST / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | report | at_cap_input_estimate | 1,660,159 | 128,000 | 1,788,159 | audit_carry 1,056,007 (63.6%); bundle 202,318 (12.2%); schema_context 164,687 (9.9%) |
| KIDS_FIRST / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | report_after_repair | at_cap_input_estimate | 1,660,159 | 128,000 | 1,788,159 | audit_carry 1,056,007 (63.6%); bundle 202,318 (12.2%); schema_context 164,687 (9.9%) |
| KIDS_FIRST / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | report_regate | expected_input_tokens | 920,099 | 128,000 | 1,048,099 | audit_carry 282,208 (30.7%); bundle 202,387 (22.0%); schema_context 164,744 (17.9%) |
| KIDS_FIRST / a17 / 2026-09-04g_claude-opus-5-api-generic-v8_rep2 | report_regate | at_cap_input_estimate | 1,787,692 | 128,000 | 1,915,692 | audit_carry 1,056,007 (59.1%); bundle 202,387 (11.3%); schema_context 164,744 (9.2%) |

## #5155 aggregate allowances

Per-record actual roster expected/at-cap totals appear above and in JSON. The JSON separately retains the #5155 builder allowance and formula inputs: max permitted workers, largest request, omission, and integration empty body plus 3.5 input tokens per worker/omission response token at two bytes per input token. A permitted max roster is not an observed roster and is not a hard bound on arbitrary output expansion.

| Project (primary A17) | Actual / max workers | #5155 integration input allowance | #5155 aggregate input allowance |
|---|---:|---:|---:|
| CHORUS | 3 / 4 | 1,200,339 | 2,092,040 |
| AI_READI | 14 / 16 | 4,389,270 | 15,820,433 |
| CM4AI | 8 / 16 | 4,175,926 | 11,778,931 |
| VOICE | 10 / 16 | 4,267,189 | 13,586,914 |
| VOICE_PEDIATRIC | 10 / 16 | 4,157,853 | 11,622,110 |
| KIDS_FIRST | 14 / 16 | 4,419,379 | 16,362,585 |

## Ledger integrity and retained uncertainty

See `ledger_originals.md` and its JSON pins. Ten matched 10-20 usage rows preserve numeric counters/caps/phase/stop reason, while report 72ac… changed admission and response hash. Later additions lack an original counterpart. No standalone 10-22 original was found in the ignored-inclusive 178-file preserved subtree; its edited outcomes cannot be authenticated independently. Both runs are evidence-only. Historical K1 outputs remain unchanged.

All inputs, composition and helper identities are pinned in JSON. No provider or tokenizer calls, live registrations, prompt edits or launch authorization. Offline scratch registrations are construction fixtures only.
