# K1: offline generation cost and size model — 2026-10-25

This is an offline planning model on A16 `56c41163f`, composed with the two #5087 sizing files from `4c52b8e6f`. No provider calls, token-count calls or live runs occurred. It is not a launch registration or a budget guarantee.

The expected column is a two-CHORUS transfer scenario. It includes the observed one-in-two report-regate frequency; the ordinary partial retry tail is separate. Other projects' outputs and cache behavior have not been observed under v10. Context failures and aggregate-input refusals prevent these arithmetic totals from authorizing a runnable matrix.

The selected partition minimizes each indivisible-root path/byte bound, then uses the worker count needed by production packing. It does not minimize dollars: larger per-worker bounds can reduce workers but require new output-cap and request sizing. A17 may change these costs; this report does not assume its unmerged behavior.

## Generation matrix

| Cell | Runs | Expected, cache-aware | Observed ordinary tail extrapolation | One pass uncached at caps | One pass all-cache-write stress | Conditional controller retry/repair envelope |
|---|---:|---:|---:|---:|---:|---:|
| Re-canary | 1 | $19.31 | $0.50 | $26.35 | $28.91 | $375.75 |
| AI_READI pilot | 1 | $54.70 | $0.76 | $62.04 | $71.93 | $559.24 |
| CHORUS production | 3 | $57.92 | $1.49 | $79.04 | $86.72 | $1,127.24 |
| CM4AI production | 3 | $118.70 | $1.98 | $143.48 | $163.67 | $1,481.81 |
| VOICE production | 3 | $183.23 | $2.36 | $211.91 | $244.41 | $1,758.56 |
| AI_READI production | 3 | $164.10 | $2.29 | $186.13 | $215.78 | $1,677.71 |
| VOICE_PEDIATRIC | 1 | $53.07 | $0.74 | $63.48 | $72.52 | $549.46 |
| KIDS_FIRST | 1 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Total before D04 B | 16 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| Subtotal of priced cells (excludes unknown cells) | — | $651.01 | $10.13 | $772.42 | $883.95 | $7,529.77 |
| Conditional 16-run total using old draft-context KIDS_FIRST proxy | 16 | $708.00 | $10.95 | $836.75 | $958.74 | $8,112.17 |
| D04 B only: with-crate CHORUS | 4 | $247.33 | $3.30 | $307.56 | $347.55 | $2,413.23 |
| Total if D04 B (actual contexts) | 20 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |

The matrix excludes prior sunk costs, evaluation ratings, native subscription/runtime cost and discretionary reruns. D04 B is conditional; a with-crate proxy is not baseline CHORUS multiplied by four.

Budget implication: priced cells already total $651.01 before unknown cells, the separate ordinary tail and evaluation, against the stated $420 campaign ceiling. Resolve partition/carry/aggregate-input limits before choosing a launch allocation. This is not proof that a different validated partition could not lower cost.

KIDS_FIRST's AI_READI proxy contains `/instances/0/data_topic: B2AI_TOPIC:43`; the actual neutral omission context supplies no B2AI_TOPIC vocabulary, so typed preparation refuses. This is a proxy incompatibility, not an established production defect. The old A1 draft-context cost is retained only as a conditional sensitivity; an actual-context typed cost and complete matrix total remain UNKNOWN.

## Primary scenario constraints

| Project / arm | Actual workers | Typed input, expected / cap-scenario | Registered aggregate | Requests exceeding 1M at caps |
|---|---:|---:|---:|---|
| CHORUS / baseline | 3 | 1,004,114 / 1,110,641 | 4000000 | None among constructed requests |
| AI_READI / baseline | 7 | 5,131,559 / 5,450,401 | 4000000 | report, report_after_repair, report_regate, typed_audit_integration |
| CM4AI / baseline | 6 | 3,220,497 / 3,474,496 | 4000000 | report_regate |
| VOICE / baseline | 10 | 5,668,906 / 6,029,421 | 4000000 | reconcile_full, report, report_after_repair, report_regate, typed_audit_integration |
| VOICE_PEDIATRIC / baseline | 10 | 4,582,643 / 4,881,343 | 4000000 | reconcile_full, report, report_after_repair, report_regate, typed_audit_integration |
| KIDS_FIRST / baseline_draft_context_proxy | 7 | 5,343,231 / 5,728,302 | 4000000 | reconcile_full, report, report_after_repair, report_regate, typed_audit_integration |
| KIDS_FIRST / baseline | UNKNOWN | UNKNOWN / UNKNOWN | 4000000 | reconcile_full, report, report_after_repair, report_regate |
| CHORUS / with_crate | 16 | 4,898,425 / 5,199,326 | 4000000 | reconcile_full, report, report_after_repair, report_regate, typed_audit_integration |

These are token estimates, including future cap-sized carries. A failure identifies exposure; a fit does not clear a production request. The detailed sections include every worker, optional request, clearance and the stricter report margin.

## Method and limits

- Actual context tokens are input_tokens + cache_read + cache_write. Dollars price those categories at 5e-6, 0.5e-6 and 6.25e-6 respectively; output is 25e-6. Thinking is already in output tokens.
- Production request builders are used with historical records and explicit synthetic carries. The retained JSON records every source pin, normalization/conformance edit, proxy and indivisible root. Future model-written records can exceed these planning bounds.
- For full, receipt, workers and omission (no synthetic carry), expected input applies the fitted historical payload token/byte ratio to current A16 bytes, preserving the cost of new fixed text. Carry-dependent integration/reconcile/report use a separate mean observed-input/scenario-input transfer factor, floored at the estimated current non-placeholder input so mandatory text cannot disappear. That transfer cannot isolate new fixed prompt/schema cost from future carry size: these stages remain a conditional scenario, not a calibrated production forecast. Every row records its basis and whether this floor applied.
- Expected output uses the completed-call mean fraction of the phase cap. For report this transfers historical 96k-cap utilization to the new 128k cap, rather than holding output at its historical token mean. This is an explicit low-information transfer assumption, not a claim that cap-sized thinking is carried as text.
- Matrix primary records are the first listed scenario per project/arm (10-22a for CHORUS); they are disclosed stand-ins, not newly selected scientific representatives. Other historical replicates and future output variation are not automatically bounded by this point forecast.
- The uncached at-cap column takes the larger of A1 input estimates and fitted historical payload-byte estimates plus cap placeholders, then charges one cap per base stage. It is a scenario envelope, not a mathematical upper bound on arbitrary future text or billable usage. Cache writes cost more than uncached input, hence the separate stress column.
- Retry/repair exposure permits 25 controller attempts each for full/reconcile, five for each report-family call, 25 readdress dispatches across five usable-body attempts, four repair rounds × five transport attempts, plus one typed/receipt call each. SDK retries and unbounded changed/error text prevent interpreting that finite scenario as a complete invoice ceiling. No retry probabilities were inferred from two runs.
- Both the actual 1M context threshold and the older A1 850k report margin are shown. Report-family output caps are 128,000. Typed aggregate input is checked separately against the registered 4M allowance (#5155).

## Archived ledger calibration

| Run | Settled token-accounted cost | Partial abandoned usage | Observed sum |
|---|---:|---:|---:|
| 2026-10-20a | $20.59 | $0.85 | $21.44 |
| 2026-10-22a | $15.17 | $1.98 | $17.15 |

Abandoned counters are partial observations. The historical low-cap worker truncation and manual typed-stage recovery are not ordinary retry frequencies. Detailed exact-byte calibration and every joined input pin are in `ledger_calibration.json` and `ledger_calibration.md`.

| Stage | Exact/reconstructed payload pairs | A1 byte error % | Other-canary max absolute error % |
|---|---:|---|---|
| full | 2 | [0.20140034062339218, 0.24128867021635525] | 0.03919872401394464 |
| full_receipt_completion | 2 | [2.123634529191487, 2.2316705591153063] | 0.10679282192547213 |
| reconcile_full | 0 | None | None |
| report | 0 | None | None |
| report_regate | 0 | None | None |
| typed_audit_integration | 2 | [-28.00948737134871, -23.401147659412036] | 6.400772256800624 |
| typed_audit_omission | 2 | [-4.762204592200813, -4.514938239052391] | 0.2596190901162254 |
| typed_audit_worker | 6 | [1.8517445649812503, 2.199303276911291] | 0.3150210738235626 |

`None` means no exact historical payload calibration; it is not zero error. The following target-builder scenario errors are distinct from exact-request calibration:

| Canary | Stage | Raw scenario error % | Held-out calibrated error % |
|---|---|---:|---:|
| 2026-10-22a | typed_audit_worker | 4.43 | 0.3601004824336673 |
| 2026-10-22a | full | 10.89 | -0.2736402237649149 |
| 2026-10-22a | full_receipt_completion | 10.73 | -0.024732060797316713 |
| 2026-10-22a | reconcile_full | 135.19 | 8.051774787188926 |
| 2026-10-22a | report | 107.47 | 6.660857150166555 |
| 2026-10-22a | typed_audit_integration | 20.27 | 13.366132482604453 |
| 2026-10-22a | typed_audit_omission | 131.89 | -1.1473406288533994 |
| 2026-10-20a | typed_audit_worker | 4.06 | -0.3588084116124324 |
| 2026-10-20a | full | 11.20 | 0.2743910680976347 |
| 2026-10-20a | full_receipt_completion | 10.76 | 0.024738179058814147 |
| 2026-10-20a | reconcile_full | 117.66 | -7.451774672879862 |
| 2026-10-20a | report | 94.51 | -6.244893701528021 |
| 2026-10-20a | report_regate | 94.29 | UNKNOWN (one observation) |
| 2026-10-20a | typed_audit_integration | 6.09 | -11.790234164207213 |
| 2026-10-20a | typed_audit_omission | 134.58 | 1.1606573218689409 |

## Per-record planning bounds and requests

### CHORUS / baseline / 2026-10-22a_claude-opus-5-api-generic-v10_rep1

Selected bounds: `{'max_inventory_bytes': 12288, 'max_paths': 80, 'max_workers': 4}`. Componentwise minimum: `{'max_inventory_bytes': 2118, 'max_paths': 18, 'max_workers': 16}`. Four-worker lexicographic point: `{'actual_workers': 4, 'limits': {'max_inventory_bytes': 8982, 'max_paths': 26, 'max_workers': 4}, 'plan_sha256': '61b2bf9c2929dd72d2c0805e2f19c8a686485375f6516b43de5ed6b5c9a8bd67'}`.

Record proxy: `None`. Conformance edits: `[]`.

Additional scenario qualifications: `{}`.

| Indivisible root | Paths | Canonical inventory bytes |
|---|---:|---:|
| /acquisition_methods | 1 | 234 |
| /addressing_gaps | 1 | 397 |
| /collection_mechanisms | 7 | 1719 |
| /conforms_to | 1 | 648 |
| /conforms_to_class | 1 | 109 |
| /conforms_to_schema | 1 | 148 |
| /conforms_to_standard | 3 | 337 |
| /creators | 4 | 797 |
| /data_governance | 1 | 720 |
| /description | 1 | 1950 |
| /existing_uses | 5 | 1151 |
| /extension_mechanism | 2 | 892 |
| /external_resources | 2 | 804 |
| /funders | 4 | 817 |
| /id | 1 | 110 |
| /instances | 14 | 2118 |
| /intended_uses | 4 | 979 |
| /is_deidentified | 1 | 402 |
| /keywords | 18 | 1993 |
| /labeling_strategies | 1 | 472 |
| /license_and_use_terms | 1 | 408 |
| /name | 1 | 104 |
| /notes | 1 | 918 |
| /page | 1 | 112 |
| /preprocessing_strategies | 3 | 952 |
| /purposes | 3 | 1062 |
| /regulatory_restrictions | 2 | 420 |
| /sampling_strategies | 2 | 612 |
| /sensitive_elements | 1 | 319 |
| /source_caveats | 1 | 1406 |
| /splits | 1 | 436 |
| /subpopulations | 3 | 716 |
| /tasks | 3 | 770 |
| /updates | 1 | 488 |
| /was_derived_from | 1 | 795 |

| Request | A1 cap-scenario input | Calibrated expected input | Input used for cap fit | Output cap | 1M clearance | At-cap 1M fit | 850k report margin |
|---|---:|---:|---:|---:|---:|---|---|
| worker_0001 | 146,005 | 143,093 | 146,005 | 64,000 | 789,995 | fits estimate | None |
| worker_0002 | 145,620 | 142,715 | 145,620 | 64,000 | 790,380 | fits estimate | None |
| worker_0003 | 143,214 | 140,357 | 143,214 | 64,000 | 792,786 | fits estimate | None |
| full | 82,267 | 82,086 | 82,267 | 128,000 | 789,733 | fits estimate | None |
| full_readdress | 95,597 | UNKNOWN | 95,597 | 8,000 | 896,403 | fits estimate | None |
| full_receipt_completion | 114,138 | 111,706 | 114,138 | 4,000 | 881,862 | fits estimate | None |
| full_receipt_completion_after_readdress | 122,494 | 112,055 | 122,494 | 4,000 | 873,506 | fits estimate | None |
| reconcile_full | 348,887 | 154,316 | 348,887 | 128,000 | 523,113 | fits estimate | None |
| repair_full | 36,045 | UNKNOWN | 36,045 | 96,000 | 867,955 | fits estimate | None |
| report | 393,176 | 195,825 | 393,176 | 128,000 | 478,824 | fits estimate | True |
| report_after_repair | 393,176 | 195,825 | 393,176 | 128,000 | 478,824 | fits estimate | True |
| report_regate | 520,560 | 267,925 | 520,560 | 128,000 | 351,440 | fits estimate | True |
| typed_audit_integration | 381,258 | 338,178 | 436,031 | 32,000 | 531,969 | fits estimate | None |
| typed_audit_omission | 228,653 | 239,771 | 239,771 | 32,000 | 728,229 | fits estimate | None |

Typed aggregate: expected 1,004,114; cap scenario 1,110,641; registered allowance 4000000; cap-scenario fit `True`.
Typed construction status: `MEASURED`; refusal: `None`.
Every non-fitting request: `[]`. Complete stage roster: `True`.

### CHORUS / baseline / 2026-10-20a_claude-opus-5-api-generic-v10_rep1

Selected bounds: `{'max_inventory_bytes': 12288, 'max_paths': 80, 'max_workers': 4}`. Componentwise minimum: `{'max_inventory_bytes': 8347, 'max_paths': 78, 'max_workers': 5}`. Four-worker lexicographic point: `{'actual_workers': 4, 'limits': {'max_inventory_bytes': 9529, 'max_paths': 78, 'max_workers': 4}, 'plan_sha256': 'e0163c1516104003997100577518938d7c85e69352e4532e2f4a9b123c57d0d2'}`.

Record proxy: `None`. Conformance edits: `[]`.

Additional scenario qualifications: `{}`.

| Indivisible root | Paths | Canonical inventory bytes |
|---|---:|---:|
| /acquisition_methods | 1 | 219 |
| /addressing_gaps | 1 | 405 |
| /conforms_to | 1 | 865 |
| /conforms_to_class | 1 | 109 |
| /conforms_to_schema | 1 | 148 |
| /conforms_to_standard | 4 | 448 |
| /data_governance | 1 | 676 |
| /description | 1 | 1706 |
| /existing_uses | 2 | 403 |
| /extension_mechanism | 2 | 1258 |
| /external_resources | 2 | 688 |
| /funders | 3 | 863 |
| /id | 1 | 110 |
| /instances | 14 | 2670 |
| /intended_uses | 6 | 1576 |
| /is_deidentified | 1 | 480 |
| /keywords | 78 | 8347 |
| /labeling_strategies | 1 | 532 |
| /license_and_use_terms | 1 | 371 |
| /name | 1 | 104 |
| /notes | 1 | 991 |
| /page | 1 | 112 |
| /preprocessing_strategies | 3 | 945 |
| /purposes | 4 | 1514 |
| /raw_data_sources | 3 | 512 |
| /regulatory_restrictions | 1 | 141 |
| /sampling_strategies | 2 | 654 |
| /source_caveats | 1 | 1884 |
| /splits | 1 | 364 |
| /subpopulations | 3 | 391 |
| /tasks | 3 | 449 |
| /updates | 1 | 593 |

| Request | A1 cap-scenario input | Calibrated expected input | Input used for cap fit | Output cap | 1M clearance | At-cap 1M fit | 850k report margin |
|---|---:|---:|---:|---:|---:|---|---|
| worker_0001 | 144,767 | 141,879 | 144,767 | 64,000 | 791,233 | fits estimate | None |
| worker_0002 | 142,356 | 139,516 | 142,356 | 64,000 | 793,644 | fits estimate | None |
| worker_0003 | 143,521 | 140,658 | 143,521 | 64,000 | 792,479 | fits estimate | None |
| full | 82,267 | 82,086 | 82,267 | 128,000 | 789,733 | fits estimate | None |
| full_readdress | 94,105 | UNKNOWN | 94,105 | 8,000 | 897,895 | fits estimate | None |
| full_receipt_completion | 110,972 | 108,608 | 110,972 | 4,000 | 885,028 | fits estimate | None |
| full_receipt_completion_after_readdress | 119,329 | 108,957 | 119,329 | 4,000 | 876,671 | fits estimate | None |
| reconcile_full | 345,506 | 152,821 | 345,506 | 128,000 | 526,494 | fits estimate | None |
| repair_full | 35,757 | UNKNOWN | 35,757 | 96,000 | 868,243 | fits estimate | None |
| report | 390,009 | 194,247 | 390,009 | 128,000 | 481,991 | fits estimate | True |
| report_after_repair | 390,009 | 194,247 | 390,009 | 128,000 | 481,991 | fits estimate | True |
| report_regate | 517,392 | 266,294 | 517,392 | 128,000 | 354,608 | fits estimate | True |
| typed_audit_integration | 375,733 | 333,277 | 428,582 | 32,000 | 539,418 | fits estimate | None |
| typed_audit_omission | 223,533 | 234,402 | 234,402 | 32,000 | 733,598 | fits estimate | None |

Typed aggregate: expected 989,731; cap scenario 1,093,628; registered allowance 4000000; cap-scenario fit `True`.
Typed construction status: `MEASURED`; refusal: `None`.
Every non-fitting request: `[]`. Complete stage roster: `True`.

### AI_READI / baseline / 2026-09-04g_claude-opus-5-api-generic-v8_rep2

Selected bounds: `{'max_inventory_bytes': 23876, 'max_paths': 144, 'max_workers': 7}`. Componentwise minimum: `{'max_inventory_bytes': 23876, 'max_paths': 144, 'max_workers': 7}`. Four-worker lexicographic point: `{'actual_workers': 4, 'limits': {'max_inventory_bytes': 43909, 'max_paths': 144, 'max_workers': 4}, 'plan_sha256': '87c68f75fd16bdd502e7678e4b967dbc376a5aeb7e5f6e885b719d93aa56df86'}`.

Record proxy: `None`. Conformance edits: `['/instances/0/missing_information/0/missing (wrapped)', '/is_deidentified/identifiers_removed (joined)', '/sampling_strategies/0/strategies (joined)', '/missing_data_documentation/0/missing_data_patterns (joined)', '/missing_data_documentation/0/missing_data_causes (joined)', '/license_and_use_terms/license_terms (joined)', '/participant_compensation/0/retention_incentives (joined)', '/participant_privacy/0/privacy_techniques (joined)']`.

Additional scenario qualifications: `{}`.

| Indivisible root | Paths | Canonical inventory bytes |
|---|---:|---:|
| /acquisition_methods | 5 | 1240 |
| /addressing_gaps | 3 | 928 |
| /anomalies | 5 | 1344 |
| /at_risk_populations | 3 | 1445 |
| /citation | 1 | 248 |
| /cleaning_strategies | 2 | 1366 |
| /collection_consents | 1 | 666 |
| /collection_mechanisms | 22 | 10321 |
| /collection_notifications | 1 | 694 |
| /collection_timeframes | 4 | 1362 |
| /confidential_elements | 2 | 519 |
| /conforms_to | 1 | 997 |
| /conforms_to_class | 1 | 109 |
| /conforms_to_schema | 1 | 148 |
| /conforms_to_standard | 7 | 788 |
| /consent_revocations | 1 | 406 |
| /content_warnings | 2 | 460 |
| /created_by | 1 | 115 |
| /creators | 16 | 3701 |
| /data_collectors | 9 | 2716 |
| /data_governance | 10 | 2725 |
| /description | 1 | 1573 |
| /direct_collection | 2 | 679 |
| /distribution_dates | 4 | 830 |
| /distribution_formats | 13 | 2776 |
| /doi | 1 | 107 |
| /ethical_reviews | 7 | 2324 |
| /extension_mechanism | 1 | 374 |
| /external_resources | 13 | 3004 |
| /file_collections | 144 | 23876 |
| /funders | 12 | 2489 |
| /future_use_impacts | 2 | 1289 |
| /human_subject_research | 7 | 2111 |
| /id | 1 | 110 |
| /informed_consent | 5 | 1855 |
| /instances | 8 | 2037 |
| /intended_uses | 8 | 2130 |
| /ip_restrictions | 5 | 1304 |
| /is_deidentified | 5 | 1863 |
| /is_tabular | 1 | 100 |
| /issued | 1 | 112 |
| /keywords | 7 | 787 |
| /known_biases | 11 | 2827 |
| /known_limitations | 12 | 2800 |
| /language | 1 | 96 |
| /license | 1 | 121 |
| /license_and_use_terms | 3 | 2781 |
| /maintainers | 4 | 1180 |
| /missing_data_documentation | 3 | 1281 |
| /name | 1 | 151 |
| /notes | 1 | 1240 |
| /page | 1 | 119 |
| /participant_compensation | 6 | 1645 |
| /participant_privacy | 4 | 2220 |
| /preprocessing_strategies | 5 | 2434 |
| /prohibited_uses | 8 | 3496 |
| /publisher | 1 | 114 |
| /purposes | 3 | 1075 |
| /raw_data_sources | 6 | 1476 |
| /raw_sources | 1 | 1042 |
| /regulatory_restrictions | 7 | 2178 |
| /related_datasets | 6 | 1427 |
| /relationships | 1 | 315 |
| /retention_limit | 1 | 486 |
| /sampling_strategies | 7 | 2469 |
| /sensitive_elements | 4 | 1027 |
| /source_caveats | 1 | 3601 |
| /splits | 1 | 857 |
| /status | 1 | 101 |
| /subpopulations | 10 | 2459 |
| /subsets | 12 | 2124 |
| /tasks | 2 | 560 |
| /third_party_sharing | 2 | 729 |
| /title | 1 | 152 |
| /total_file_count | 1 | 107 |
| /total_size_bytes | 1 | 114 |
| /updates | 2 | 691 |
| /variables | 68 | 11290 |
| /version | 1 | 98 |
| /version_access | 6 | 1901 |
| /was_derived_from | 1 | 241 |

| Request | A1 cap-scenario input | Calibrated expected input | Input used for cap fit | Output cap | 1M clearance | At-cap 1M fit | 850k report margin |
|---|---:|---:|---:|---:|---:|---|---|
| worker_0001 | 514,714 | 529,387 | 529,387 | 64,000 | 406,613 | fits estimate | None |
| worker_0002 | 515,413 | 530,105 | 530,105 | 64,000 | 405,895 | fits estimate | None |
| worker_0003 | 513,709 | 528,353 | 528,353 | 64,000 | 407,647 | fits estimate | None |
| worker_0004 | 514,914 | 529,592 | 529,592 | 64,000 | 406,408 | fits estimate | None |
| worker_0005 | 515,113 | 529,797 | 529,797 | 64,000 | 406,203 | fits estimate | None |
| worker_0006 | 513,468 | 528,105 | 528,105 | 64,000 | 407,895 | fits estimate | None |
| worker_0007 | 512,298 | 526,902 | 526,902 | 64,000 | 409,098 | fits estimate | None |
| full | 216,209 | 228,779 | 228,779 | 128,000 | 643,221 | fits estimate | None |
| full_readdress | 261,666 | UNKNOWN | 261,666 | 8,000 | 730,334 | fits estimate | None |
| full_receipt_completion | 331,507 | 333,021 | 333,021 | 4,000 | 662,979 | fits estimate | None |
| full_receipt_completion_after_readdress | 339,854 | 333,370 | 341,370 | 4,000 | 654,630 | fits estimate | None |
| reconcile_full | 870,687 | 390,687 | 870,687 | 128,000 | 1,313 | fits estimate | None |
| repair_full | 61,782 | UNKNOWN | 61,782 | 96,000 | 842,218 | fits estimate | None |
| report | 1,025,543 | 545,543 | 1,025,543 | 128,000 | -153,543 | EXCEEDS estimate | False |
| report_after_repair | 1,025,543 | 545,543 | 1,025,543 | 128,000 | -153,543 | EXCEEDS estimate | False |
| report_regate | 1,152,958 | 593,410 | 1,152,958 | 128,000 | -280,958 | EXCEEDS estimate | False |
| typed_audit_integration | 981,179 | 870,311 | 1,189,152 | 32,000 | -221,152 | EXCEEDS estimate | None |
| typed_audit_omission | 519,205 | 559,007 | 559,007 | 32,000 | 408,993 | fits estimate | None |

Typed aggregate: expected 5,131,559; cap scenario 5,450,401; registered allowance 4000000; cap-scenario fit `False`.
Typed construction status: `MEASURED`; refusal: `None`.
Every non-fitting request: `['report', 'report_after_repair', 'report_regate', 'typed_audit_integration']`. Complete stage roster: `True`.

### CM4AI / baseline / 2026-09-04g_claude-opus-5-api-generic-v8_rep1

Selected bounds: `{'max_inventory_bytes': 16800, 'max_paths': 133, 'max_workers': 6}`. Componentwise minimum: `{'max_inventory_bytes': 16800, 'max_paths': 133, 'max_workers': 6}`. Four-worker lexicographic point: `{'actual_workers': 4, 'limits': {'max_inventory_bytes': 29709, 'max_paths': 146, 'max_workers': 4}, 'plan_sha256': 'ca7c322fa3e7380632a5e43b23445ce60ebc26758587bec8843452f027fd424b'}`.

Record proxy: `None`. Conformance edits: `['/sampling_strategies/0/strategies (joined)', '/sampling_strategies/1/strategies (unwrapped)']`.

Additional scenario qualifications: `{}`.

| Indivisible root | Paths | Canonical inventory bytes |
|---|---:|---:|
| /acquisition_methods | 6 | 1541 |
| /addressing_gaps | 2 | 993 |
| /citation | 1 | 764 |
| /collection_mechanisms | 4 | 1186 |
| /collection_timeframes | 1 | 506 |
| /compression | 1 | 100 |
| /confidential_elements | 2 | 533 |
| /conforms_to | 1 | 197 |
| /conforms_to_class | 1 | 109 |
| /conforms_to_schema | 1 | 148 |
| /conforms_to_standard | 1 | 116 |
| /created_on | 1 | 116 |
| /creators | 133 | 16800 |
| /data_collectors | 11 | 2725 |
| /data_governance | 7 | 1600 |
| /description | 1 | 1346 |
| /direct_collection | 2 | 491 |
| /distribution_dates | 2 | 388 |
| /distribution_formats | 3 | 719 |
| /doi | 1 | 107 |
| /ethical_reviews | 11 | 2533 |
| /existing_uses | 2 | 761 |
| /external_resources | 10 | 2498 |
| /file_collections | 107 | 16166 |
| /funders | 9 | 1832 |
| /human_subject_research | 3 | 654 |
| /id | 1 | 110 |
| /instances | 15 | 2436 |
| /intended_uses | 4 | 701 |
| /ip_restrictions | 3 | 1020 |
| /is_deidentified | 2 | 511 |
| /issued | 1 | 112 |
| /keywords | 30 | 3282 |
| /known_biases | 3 | 854 |
| /known_limitations | 12 | 2306 |
| /license | 1 | 108 |
| /license_and_use_terms | 6 | 1568 |
| /maintainers | 4 | 862 |
| /name | 1 | 159 |
| /notes | 1 | 678 |
| /page | 1 | 174 |
| /preprocessing_strategies | 2 | 696 |
| /prohibited_uses | 1 | 286 |
| /purposes | 3 | 1082 |
| /raw_data_sources | 6 | 1437 |
| /raw_sources | 5 | 1458 |
| /related_datasets | 3 | 664 |
| /retention_limit | 1 | 226 |
| /sampling_strategies | 6 | 1450 |
| /sensitive_elements | 2 | 502 |
| /source_caveats | 1 | 1152 |
| /status | 1 | 96 |
| /tasks | 2 | 513 |
| /third_party_sharing | 2 | 514 |
| /title | 1 | 160 |
| /total_file_count | 1 | 103 |
| /updates | 2 | 490 |
| /version | 1 | 96 |
| /version_access | 7 | 1485 |

| Request | A1 cap-scenario input | Calibrated expected input | Input used for cap fit | Output cap | 1M clearance | At-cap 1M fit | 850k report margin |
|---|---:|---:|---:|---:|---:|---|---|
| worker_0001 | 359,283 | 352,116 | 359,283 | 64,000 | 576,717 | fits estimate | None |
| worker_0002 | 358,852 | 351,694 | 358,852 | 64,000 | 577,148 | fits estimate | None |
| worker_0003 | 360,987 | 353,785 | 360,987 | 64,000 | 575,013 | fits estimate | None |
| worker_0004 | 359,792 | 352,615 | 359,792 | 64,000 | 576,208 | fits estimate | None |
| worker_0005 | 361,470 | 354,259 | 361,470 | 64,000 | 574,530 | fits estimate | None |
| worker_0006 | 361,196 | 353,991 | 361,196 | 64,000 | 574,804 | fits estimate | None |
| full | 188,266 | 187,851 | 188,266 | 128,000 | 683,734 | fits estimate | None |
| full_readdress | 212,988 | UNKNOWN | 212,988 | 8,000 | 779,012 | fits estimate | None |
| full_receipt_completion | 248,690 | 243,391 | 248,690 | 4,000 | 747,310 | fits estimate | None |
| full_receipt_completion_after_readdress | 257,046 | 243,740 | 257,046 | 4,000 | 738,954 | fits estimate | None |
| reconcile_full | 697,324 | 308,433 | 697,324 | 128,000 | 174,676 | fits estimate | None |
| repair_full | 42,937 | UNKNOWN | 42,937 | 96,000 | 861,063 | fits estimate | None |
| report | 776,269 | 386,627 | 776,269 | 128,000 | 95,731 | fits estimate | False |
| report_after_repair | 776,269 | 386,627 | 776,269 | 128,000 | 95,731 | fits estimate | False |
| report_regate | 903,719 | 465,131 | 903,719 | 128,000 | -31,719 | EXCEEDS estimate | False |
| typed_audit_integration | 771,240 | 684,094 | 894,973 | 32,000 | 73,027 | fits estimate | None |
| typed_audit_omission | 398,564 | 417,943 | 417,943 | 32,000 | 550,057 | fits estimate | None |

Typed aggregate: expected 3,220,497; cap scenario 3,474,496; registered allowance 4000000; cap-scenario fit `True`.
Typed construction status: `MEASURED`; refusal: `None`.
Every non-fitting request: `['report_regate']`. Complete stage roster: `True`.

### VOICE / baseline / 2026-09-04f_claude-opus-5-api-generic-v8_rep1

Selected bounds: `{'max_inventory_bytes': 11652, 'max_paths': 63, 'max_workers': 10}`. Componentwise minimum: `{'max_inventory_bytes': 11652, 'max_paths': 63, 'max_workers': 10}`. Four-worker lexicographic point: `{'actual_workers': 4, 'limits': {'max_inventory_bytes': 26234, 'max_paths': 110, 'max_workers': 4}, 'plan_sha256': 'b6e801d66e8f53d79c798d0a0ba3cd1237bdab76d6ce7a7a5aefa82bf00c94e7'}`.

Record proxy: `None`. Conformance edits: `['/sampling_strategies/0/strategies (joined)', '/instances/0/missing_information/0/missing (wrapped)', '/instances/0/missing_information/1/missing (wrapped)', '/machine_annotation_tools/0/tool_descriptions (joined)', '/participant_privacy/0/privacy_techniques (joined)', '/external_resources/0/external_resources (wrapped)', '/external_resources/1/external_resources (wrapped)', '/external_resources/2/external_resources (wrapped)', '/external_resources/3/external_resources (wrapped)', '/external_resources/4/external_resources (wrapped)']`.

Additional scenario qualifications: `{}`.

| Indivisible root | Paths | Canonical inventory bytes |
|---|---:|---:|
| /acquisition_methods | 6 | 1226 |
| /addressing_gaps | 3 | 946 |
| /anomalies | 3 | 890 |
| /at_risk_populations | 3 | 957 |
| /citation | 1 | 534 |
| /cleaning_strategies | 2 | 797 |
| /collection_consents | 2 | 744 |
| /collection_mechanisms | 2 | 757 |
| /collection_notifications | 1 | 362 |
| /collection_timeframes | 2 | 588 |
| /confidential_elements | 2 | 493 |
| /conforms_to | 1 | 139 |
| /conforms_to_class | 1 | 109 |
| /conforms_to_schema | 1 | 148 |
| /conforms_to_standard | 1 | 112 |
| /consent_revocations | 1 | 661 |
| /content_warnings | 4 | 1222 |
| /created_by | 1 | 122 |
| /creators | 54 | 8479 |
| /data_collectors | 6 | 1331 |
| /data_governance | 13 | 3371 |
| /description | 1 | 1379 |
| /direct_collection | 2 | 397 |
| /discouraged_uses | 1 | 468 |
| /distribution_dates | 6 | 1023 |
| /distribution_formats | 10 | 2041 |
| /doi | 1 | 107 |
| /errata | 2 | 938 |
| /ethical_reviews | 8 | 1779 |
| /existing_uses | 1 | 228 |
| /extension_mechanism | 2 | 656 |
| /external_resources | 9 | 2555 |
| /file_collections | 63 | 11652 |
| /funders | 6 | 1455 |
| /future_use_impacts | 2 | 763 |
| /human_subject_research | 4 | 1368 |
| /id | 1 | 110 |
| /informed_consent | 5 | 1769 |
| /instances | 14 | 3030 |
| /intended_uses | 8 | 1350 |
| /ip_restrictions | 4 | 1307 |
| /is_deidentified | 4 | 2004 |
| /issued | 1 | 112 |
| /keywords | 4 | 408 |
| /known_biases | 9 | 2010 |
| /known_limitations | 13 | 3133 |
| /labeling_strategies | 6 | 1388 |
| /language | 1 | 101 |
| /last_updated_on | 1 | 121 |
| /license | 1 | 134 |
| /license_and_use_terms | 2 | 1021 |
| /machine_annotation_tools | 11 | 2021 |
| /maintainers | 7 | 1518 |
| /missing_data_documentation | 3 | 1079 |
| /name | 1 | 105 |
| /other_tasks | 1 | 263 |
| /page | 1 | 137 |
| /participant_compensation | 4 | 848 |
| /participant_privacy | 4 | 1743 |
| /preprocessing_strategies | 8 | 2475 |
| /prohibited_uses | 3 | 992 |
| /publisher | 1 | 117 |
| /purposes | 3 | 998 |
| /raw_data_sources | 8 | 1607 |
| /regulatory_restrictions | 5 | 1550 |
| /related_datasets | 12 | 2132 |
| /relationships | 2 | 704 |
| /retention_limit | 2 | 1060 |
| /sampling_strategies | 6 | 1490 |
| /sensitive_elements | 6 | 1225 |
| /source_caveats | 1 | 1819 |
| /splits | 1 | 268 |
| /status | 1 | 101 |
| /subpopulations | 3 | 817 |
| /subsets | 0 | 3 |
| /tasks | 2 | 523 |
| /third_party_sharing | 2 | 675 |
| /title | 1 | 180 |
| /updates | 2 | 663 |
| /variables | 14 | 1934 |
| /version | 1 | 98 |
| /version_access | 7 | 1430 |
| /was_derived_from | 1 | 334 |

| Request | A1 cap-scenario input | Calibrated expected input | Input used for cap fit | Output cap | 1M clearance | At-cap 1M fit | 850k report margin |
|---|---:|---:|---:|---:|---:|---|---|
| worker_0001 | 430,445 | 421,858 | 430,445 | 64,000 | 505,555 | fits estimate | None |
| worker_0002 | 427,968 | 419,431 | 427,968 | 64,000 | 508,032 | fits estimate | None |
| worker_0003 | 429,995 | 421,418 | 429,995 | 64,000 | 506,005 | fits estimate | None |
| worker_0004 | 427,126 | 418,606 | 427,126 | 64,000 | 508,874 | fits estimate | None |
| worker_0005 | 428,041 | 419,502 | 428,041 | 64,000 | 507,959 | fits estimate | None |
| worker_0006 | 429,223 | 420,661 | 429,223 | 64,000 | 506,777 | fits estimate | None |
| worker_0007 | 429,126 | 420,565 | 429,126 | 64,000 | 506,874 | fits estimate | None |
| worker_0008 | 429,181 | 420,620 | 429,181 | 64,000 | 506,819 | fits estimate | None |
| worker_0009 | 429,421 | 420,854 | 429,421 | 64,000 | 506,579 | fits estimate | None |
| worker_0010 | 428,605 | 420,055 | 428,605 | 64,000 | 507,395 | fits estimate | None |
| full | 207,893 | 207,435 | 207,893 | 128,000 | 664,107 | fits estimate | None |
| full_readdress | 244,568 | UNKNOWN | 244,568 | 8,000 | 747,432 | fits estimate | None |
| full_receipt_completion | 294,181 | 287,914 | 294,181 | 4,000 | 701,819 | fits estimate | None |
| full_receipt_completion_after_readdress | 302,538 | 288,262 | 302,538 | 4,000 | 693,462 | fits estimate | None |
| reconcile_full | 1,014,268 | 448,621 | 1,014,268 | 128,000 | -142,268 | EXCEEDS estimate | None |
| repair_full | 52,171 | UNKNOWN | 52,171 | 96,000 | 851,829 | fits estimate | None |
| report | 1,121,651 | 558,648 | 1,121,651 | 128,000 | -249,651 | EXCEEDS estimate | False |
| report_after_repair | 1,121,651 | 558,648 | 1,121,651 | 128,000 | -249,651 | EXCEEDS estimate | False |
| report_regate | 1,249,131 | 642,909 | 1,249,131 | 128,000 | -377,131 | EXCEEDS estimate | False |
| typed_audit_integration | 1,103,434 | 978,752 | 1,253,705 | 32,000 | -285,705 | EXCEEDS estimate | None |
| typed_audit_omission | 464,023 | 486,585 | 486,585 | 32,000 | 481,415 | fits estimate | None |

Typed aggregate: expected 5,668,906; cap scenario 6,029,421; registered allowance 4000000; cap-scenario fit `False`.
Typed construction status: `MEASURED`; refusal: `None`.
Every non-fitting request: `['reconcile_full', 'report', 'report_after_repair', 'report_regate', 'typed_audit_integration']`. Complete stage roster: `True`.

### VOICE_PEDIATRIC / baseline / 2026-09-04f_claude-opus-5-api-generic-v8_rep1

Selected bounds: `{'max_inventory_bytes': 11652, 'max_paths': 63, 'max_workers': 10}`. Componentwise minimum: `{'max_inventory_bytes': 11652, 'max_paths': 63, 'max_workers': 10}`. Four-worker lexicographic point: `{'actual_workers': 4, 'limits': {'max_inventory_bytes': 26234, 'max_paths': 110, 'max_workers': 4}, 'plan_sha256': 'b6e801d66e8f53d79c798d0a0ba3cd1237bdab76d6ce7a7a5aefa82bf00c94e7'}`.

Record proxy: `VOICE`. Conformance edits: `['/sampling_strategies/0/strategies (joined)', '/instances/0/missing_information/0/missing (wrapped)', '/instances/0/missing_information/1/missing (wrapped)', '/machine_annotation_tools/0/tool_descriptions (joined)', '/participant_privacy/0/privacy_techniques (joined)', '/external_resources/0/external_resources (wrapped)', '/external_resources/1/external_resources (wrapped)', '/external_resources/2/external_resources (wrapped)', '/external_resources/3/external_resources (wrapped)', '/external_resources/4/external_resources (wrapped)']`.

Additional scenario qualifications: `{}`.

| Indivisible root | Paths | Canonical inventory bytes |
|---|---:|---:|
| /acquisition_methods | 6 | 1226 |
| /addressing_gaps | 3 | 946 |
| /anomalies | 3 | 890 |
| /at_risk_populations | 3 | 957 |
| /citation | 1 | 534 |
| /cleaning_strategies | 2 | 797 |
| /collection_consents | 2 | 744 |
| /collection_mechanisms | 2 | 757 |
| /collection_notifications | 1 | 362 |
| /collection_timeframes | 2 | 588 |
| /confidential_elements | 2 | 493 |
| /conforms_to | 1 | 139 |
| /conforms_to_class | 1 | 109 |
| /conforms_to_schema | 1 | 148 |
| /conforms_to_standard | 1 | 112 |
| /consent_revocations | 1 | 661 |
| /content_warnings | 4 | 1222 |
| /created_by | 1 | 122 |
| /creators | 54 | 8479 |
| /data_collectors | 6 | 1331 |
| /data_governance | 13 | 3371 |
| /description | 1 | 1379 |
| /direct_collection | 2 | 397 |
| /discouraged_uses | 1 | 468 |
| /distribution_dates | 6 | 1023 |
| /distribution_formats | 10 | 2041 |
| /doi | 1 | 107 |
| /errata | 2 | 938 |
| /ethical_reviews | 8 | 1779 |
| /existing_uses | 1 | 228 |
| /extension_mechanism | 2 | 656 |
| /external_resources | 9 | 2555 |
| /file_collections | 63 | 11652 |
| /funders | 6 | 1455 |
| /future_use_impacts | 2 | 763 |
| /human_subject_research | 4 | 1368 |
| /id | 1 | 110 |
| /informed_consent | 5 | 1769 |
| /instances | 14 | 3030 |
| /intended_uses | 8 | 1350 |
| /ip_restrictions | 4 | 1307 |
| /is_deidentified | 4 | 2004 |
| /issued | 1 | 112 |
| /keywords | 4 | 408 |
| /known_biases | 9 | 2010 |
| /known_limitations | 13 | 3133 |
| /labeling_strategies | 6 | 1388 |
| /language | 1 | 101 |
| /last_updated_on | 1 | 121 |
| /license | 1 | 134 |
| /license_and_use_terms | 2 | 1021 |
| /machine_annotation_tools | 11 | 2021 |
| /maintainers | 7 | 1518 |
| /missing_data_documentation | 3 | 1079 |
| /name | 1 | 105 |
| /other_tasks | 1 | 263 |
| /page | 1 | 137 |
| /participant_compensation | 4 | 848 |
| /participant_privacy | 4 | 1743 |
| /preprocessing_strategies | 8 | 2475 |
| /prohibited_uses | 3 | 992 |
| /publisher | 1 | 117 |
| /purposes | 3 | 998 |
| /raw_data_sources | 8 | 1607 |
| /regulatory_restrictions | 5 | 1550 |
| /related_datasets | 12 | 2132 |
| /relationships | 2 | 704 |
| /retention_limit | 2 | 1060 |
| /sampling_strategies | 6 | 1490 |
| /sensitive_elements | 6 | 1225 |
| /source_caveats | 1 | 1819 |
| /splits | 1 | 268 |
| /status | 1 | 101 |
| /subpopulations | 3 | 817 |
| /subsets | 0 | 3 |
| /tasks | 2 | 523 |
| /third_party_sharing | 2 | 675 |
| /title | 1 | 180 |
| /updates | 2 | 663 |
| /variables | 14 | 1934 |
| /version | 1 | 98 |
| /version_access | 7 | 1430 |
| /was_derived_from | 1 | 334 |

| Request | A1 cap-scenario input | Calibrated expected input | Input used for cap fit | Output cap | 1M clearance | At-cap 1M fit | 850k report margin |
|---|---:|---:|---:|---:|---:|---|---|
| worker_0001 | 336,898 | 330,177 | 336,898 | 64,000 | 599,102 | fits estimate | None |
| worker_0002 | 334,421 | 327,750 | 334,421 | 64,000 | 601,579 | fits estimate | None |
| worker_0003 | 336,448 | 329,737 | 336,448 | 64,000 | 599,552 | fits estimate | None |
| worker_0004 | 333,579 | 326,925 | 333,579 | 64,000 | 602,421 | fits estimate | None |
| worker_0005 | 334,494 | 327,821 | 334,494 | 64,000 | 601,506 | fits estimate | None |
| worker_0006 | 335,676 | 328,980 | 335,676 | 64,000 | 600,324 | fits estimate | None |
| worker_0007 | 335,579 | 328,884 | 335,579 | 64,000 | 600,421 | fits estimate | None |
| worker_0008 | 335,634 | 328,939 | 335,634 | 64,000 | 600,366 | fits estimate | None |
| worker_0009 | 335,874 | 329,174 | 335,874 | 64,000 | 600,126 | fits estimate | None |
| worker_0010 | 335,058 | 328,374 | 335,058 | 64,000 | 600,942 | fits estimate | None |
| full | 144,443 | 144,125 | 144,443 | 128,000 | 727,557 | fits estimate | None |
| full_readdress | 167,737 | UNKNOWN | 167,737 | 8,000 | 824,263 | fits estimate | None |
| full_receipt_completion | 203,849 | 199,506 | 203,849 | 4,000 | 792,151 | fits estimate | None |
| full_receipt_completion_after_readdress | 212,205 | 199,855 | 212,205 | 4,000 | 783,795 | fits estimate | None |
| reconcile_full | 949,132 | 419,810 | 949,132 | 128,000 | -77,132 | EXCEEDS estimate | None |
| repair_full | 52,116 | UNKNOWN | 52,116 | 96,000 | 851,884 | fits estimate | None |
| report | 1,056,950 | 526,423 | 1,056,950 | 128,000 | -184,950 | EXCEEDS estimate | False |
| report_after_repair | 1,056,950 | 526,423 | 1,056,950 | 128,000 | -184,950 | EXCEEDS estimate | False |
| report_regate | 1,184,409 | 609,598 | 1,184,409 | 128,000 | -312,409 | EXCEEDS estimate | False |
| typed_audit_integration | 1,009,887 | 895,775 | 1,127,575 | 32,000 | -159,575 | EXCEEDS estimate | None |
| typed_audit_omission | 381,554 | 400,107 | 400,107 | 32,000 | 567,893 | fits estimate | None |

Typed aggregate: expected 4,582,643; cap scenario 4,881,343; registered allowance 4000000; cap-scenario fit `False`.
Typed construction status: `MEASURED`; refusal: `None`.
Every non-fitting request: `['reconcile_full', 'report', 'report_after_repair', 'report_regate', 'typed_audit_integration']`. Complete stage roster: `True`.

### KIDS_FIRST / baseline_draft_context_proxy / 2026-09-04g_claude-opus-5-api-generic-v8_rep2

Selected bounds: `{'max_inventory_bytes': 23876, 'max_paths': 144, 'max_workers': 7}`. Componentwise minimum: `{'max_inventory_bytes': 23876, 'max_paths': 144, 'max_workers': 7}`. Four-worker lexicographic point: `{'actual_workers': 4, 'limits': {'max_inventory_bytes': 43909, 'max_paths': 144, 'max_workers': 4}, 'plan_sha256': '87c68f75fd16bdd502e7678e4b967dbc376a5aeb7e5f6e885b719d93aa56df86'}`.

Record proxy: `AI_READI`. Conformance edits: `['/instances/0/missing_information/0/missing (wrapped)', '/is_deidentified/identifiers_removed (joined)', '/sampling_strategies/0/strategies (joined)', '/missing_data_documentation/0/missing_data_patterns (joined)', '/missing_data_documentation/0/missing_data_causes (joined)', '/license_and_use_terms/license_terms (joined)', '/participant_compensation/0/retention_incentives (joined)', '/participant_privacy/0/privacy_techniques (joined)']`.

Additional scenario qualifications: `{'context_basis': 'Superseded inherited A1 draft context, not actual A16 Kids First context; cost sensitivity only.'}`.

| Indivisible root | Paths | Canonical inventory bytes |
|---|---:|---:|
| /acquisition_methods | 5 | 1240 |
| /addressing_gaps | 3 | 928 |
| /anomalies | 5 | 1344 |
| /at_risk_populations | 3 | 1445 |
| /citation | 1 | 248 |
| /cleaning_strategies | 2 | 1366 |
| /collection_consents | 1 | 666 |
| /collection_mechanisms | 22 | 10321 |
| /collection_notifications | 1 | 694 |
| /collection_timeframes | 4 | 1362 |
| /confidential_elements | 2 | 519 |
| /conforms_to | 1 | 997 |
| /conforms_to_class | 1 | 109 |
| /conforms_to_schema | 1 | 148 |
| /conforms_to_standard | 7 | 788 |
| /consent_revocations | 1 | 406 |
| /content_warnings | 2 | 460 |
| /created_by | 1 | 115 |
| /creators | 16 | 3701 |
| /data_collectors | 9 | 2716 |
| /data_governance | 10 | 2725 |
| /description | 1 | 1573 |
| /direct_collection | 2 | 679 |
| /distribution_dates | 4 | 830 |
| /distribution_formats | 13 | 2776 |
| /doi | 1 | 107 |
| /ethical_reviews | 7 | 2324 |
| /extension_mechanism | 1 | 374 |
| /external_resources | 13 | 3004 |
| /file_collections | 144 | 23876 |
| /funders | 12 | 2489 |
| /future_use_impacts | 2 | 1289 |
| /human_subject_research | 7 | 2111 |
| /id | 1 | 110 |
| /informed_consent | 5 | 1855 |
| /instances | 8 | 2037 |
| /intended_uses | 8 | 2130 |
| /ip_restrictions | 5 | 1304 |
| /is_deidentified | 5 | 1863 |
| /is_tabular | 1 | 100 |
| /issued | 1 | 112 |
| /keywords | 7 | 787 |
| /known_biases | 11 | 2827 |
| /known_limitations | 12 | 2800 |
| /language | 1 | 96 |
| /license | 1 | 121 |
| /license_and_use_terms | 3 | 2781 |
| /maintainers | 4 | 1180 |
| /missing_data_documentation | 3 | 1281 |
| /name | 1 | 151 |
| /notes | 1 | 1240 |
| /page | 1 | 119 |
| /participant_compensation | 6 | 1645 |
| /participant_privacy | 4 | 2220 |
| /preprocessing_strategies | 5 | 2434 |
| /prohibited_uses | 8 | 3496 |
| /publisher | 1 | 114 |
| /purposes | 3 | 1075 |
| /raw_data_sources | 6 | 1476 |
| /raw_sources | 1 | 1042 |
| /regulatory_restrictions | 7 | 2178 |
| /related_datasets | 6 | 1427 |
| /relationships | 1 | 315 |
| /retention_limit | 1 | 486 |
| /sampling_strategies | 7 | 2469 |
| /sensitive_elements | 4 | 1027 |
| /source_caveats | 1 | 3601 |
| /splits | 1 | 857 |
| /status | 1 | 101 |
| /subpopulations | 10 | 2459 |
| /subsets | 12 | 2124 |
| /tasks | 2 | 560 |
| /third_party_sharing | 2 | 729 |
| /title | 1 | 152 |
| /total_file_count | 1 | 107 |
| /total_size_bytes | 1 | 114 |
| /updates | 2 | 691 |
| /variables | 68 | 11290 |
| /version | 1 | 98 |
| /version_access | 6 | 1901 |
| /was_derived_from | 1 | 241 |

| Request | A1 cap-scenario input | Calibrated expected input | Input used for cap fit | Output cap | 1M clearance | At-cap 1M fit | 850k report margin |
|---|---:|---:|---:|---:|---:|---|---|
| worker_0001 | 561,548 | 550,346 | 561,548 | 64,000 | 374,452 | fits estimate | None |
| worker_0002 | 562,280 | 551,064 | 562,280 | 64,000 | 373,720 | fits estimate | None |
| worker_0003 | 560,493 | 549,312 | 560,493 | 64,000 | 375,507 | fits estimate | None |
| worker_0004 | 561,757 | 550,551 | 561,757 | 64,000 | 374,243 | fits estimate | None |
| worker_0005 | 561,967 | 550,756 | 561,967 | 64,000 | 374,033 | fits estimate | None |
| worker_0006 | 560,239 | 549,064 | 560,239 | 64,000 | 375,761 | fits estimate | None |
| worker_0007 | 559,012 | 547,861 | 559,012 | 64,000 | 376,988 | fits estimate | None |
| full | 267,824 | 267,234 | 267,824 | 128,000 | 604,176 | fits estimate | None |
| full_readdress | 304,053 | UNKNOWN | 304,053 | 8,000 | 687,947 | fits estimate | None |
| full_receipt_completion | 358,774 | 351,131 | 358,774 | 4,000 | 637,226 | fits estimate | None |
| full_receipt_completion_after_readdress | 367,131 | 351,479 | 367,131 | 4,000 | 628,869 | fits estimate | None |
| reconcile_full | 925,225 | 445,225 | 925,225 | 128,000 | -53,225 | EXCEEDS estimate | None |
| repair_full | 62,612 | UNKNOWN | 62,612 | 96,000 | 841,388 | fits estimate | None |
| report | 1,086,413 | 606,413 | 1,086,413 | 128,000 | -214,413 | EXCEEDS estimate | False |
| report_after_repair | 1,086,413 | 606,413 | 1,086,413 | 128,000 | -214,413 | EXCEEDS estimate | False |
| report_regate | 1,213,947 | 624,801 | 1,213,947 | 128,000 | -341,947 | EXCEEDS estimate | False |
| typed_audit_integration | 1,027,343 | 911,259 | 1,217,986 | 32,000 | -249,986 | EXCEEDS estimate | None |
| typed_audit_omission | 555,986 | 583,020 | 583,020 | 32,000 | 384,980 | fits estimate | None |

Typed aggregate: expected 5,343,231; cap scenario 5,728,302; registered allowance 4000000; cap-scenario fit `False`.
Typed construction status: `MEASURED`; refusal: `None`.
Every non-fitting request: `['reconcile_full', 'report', 'report_after_repair', 'report_regate', 'typed_audit_integration']`. Complete stage roster: `True`.

### KIDS_FIRST / baseline / 2026-09-04g_claude-opus-5-api-generic-v8_rep2

Selected bounds: `{'max_inventory_bytes': 23876, 'max_paths': 144, 'max_workers': 7}`. Componentwise minimum: `{'max_inventory_bytes': 23876, 'max_paths': 144, 'max_workers': 7}`. Four-worker lexicographic point: `{'actual_workers': 4, 'limits': {'max_inventory_bytes': 43909, 'max_paths': 144, 'max_workers': 4}, 'plan_sha256': '87c68f75fd16bdd502e7678e4b967dbc376a5aeb7e5f6e885b719d93aa56df86'}`.

Record proxy: `AI_READI`. Conformance edits: `['/instances/0/missing_information/0/missing (wrapped)', '/is_deidentified/identifiers_removed (joined)', '/sampling_strategies/0/strategies (joined)', '/missing_data_documentation/0/missing_data_patterns (joined)', '/missing_data_documentation/0/missing_data_causes (joined)', '/license_and_use_terms/license_terms (joined)', '/participant_compensation/0/retention_incentives (joined)', '/participant_privacy/0/privacy_techniques (joined)']`.

Additional scenario qualifications: `{'context_basis': 'Exact committed A16 Kids First omission context; replaces inherited A1 draft.'}`.

| Indivisible root | Paths | Canonical inventory bytes |
|---|---:|---:|
| /acquisition_methods | 5 | 1240 |
| /addressing_gaps | 3 | 928 |
| /anomalies | 5 | 1344 |
| /at_risk_populations | 3 | 1445 |
| /citation | 1 | 248 |
| /cleaning_strategies | 2 | 1366 |
| /collection_consents | 1 | 666 |
| /collection_mechanisms | 22 | 10321 |
| /collection_notifications | 1 | 694 |
| /collection_timeframes | 4 | 1362 |
| /confidential_elements | 2 | 519 |
| /conforms_to | 1 | 997 |
| /conforms_to_class | 1 | 109 |
| /conforms_to_schema | 1 | 148 |
| /conforms_to_standard | 7 | 788 |
| /consent_revocations | 1 | 406 |
| /content_warnings | 2 | 460 |
| /created_by | 1 | 115 |
| /creators | 16 | 3701 |
| /data_collectors | 9 | 2716 |
| /data_governance | 10 | 2725 |
| /description | 1 | 1573 |
| /direct_collection | 2 | 679 |
| /distribution_dates | 4 | 830 |
| /distribution_formats | 13 | 2776 |
| /doi | 1 | 107 |
| /ethical_reviews | 7 | 2324 |
| /extension_mechanism | 1 | 374 |
| /external_resources | 13 | 3004 |
| /file_collections | 144 | 23876 |
| /funders | 12 | 2489 |
| /future_use_impacts | 2 | 1289 |
| /human_subject_research | 7 | 2111 |
| /id | 1 | 110 |
| /informed_consent | 5 | 1855 |
| /instances | 8 | 2037 |
| /intended_uses | 8 | 2130 |
| /ip_restrictions | 5 | 1304 |
| /is_deidentified | 5 | 1863 |
| /is_tabular | 1 | 100 |
| /issued | 1 | 112 |
| /keywords | 7 | 787 |
| /known_biases | 11 | 2827 |
| /known_limitations | 12 | 2800 |
| /language | 1 | 96 |
| /license | 1 | 121 |
| /license_and_use_terms | 3 | 2781 |
| /maintainers | 4 | 1180 |
| /missing_data_documentation | 3 | 1281 |
| /name | 1 | 151 |
| /notes | 1 | 1240 |
| /page | 1 | 119 |
| /participant_compensation | 6 | 1645 |
| /participant_privacy | 4 | 2220 |
| /preprocessing_strategies | 5 | 2434 |
| /prohibited_uses | 8 | 3496 |
| /publisher | 1 | 114 |
| /purposes | 3 | 1075 |
| /raw_data_sources | 6 | 1476 |
| /raw_sources | 1 | 1042 |
| /regulatory_restrictions | 7 | 2178 |
| /related_datasets | 6 | 1427 |
| /relationships | 1 | 315 |
| /retention_limit | 1 | 486 |
| /sampling_strategies | 7 | 2469 |
| /sensitive_elements | 4 | 1027 |
| /source_caveats | 1 | 3601 |
| /splits | 1 | 857 |
| /status | 1 | 101 |
| /subpopulations | 10 | 2459 |
| /subsets | 12 | 2124 |
| /tasks | 2 | 560 |
| /third_party_sharing | 2 | 729 |
| /title | 1 | 152 |
| /total_file_count | 1 | 107 |
| /total_size_bytes | 1 | 114 |
| /updates | 2 | 691 |
| /variables | 68 | 11290 |
| /version | 1 | 98 |
| /version_access | 6 | 1901 |
| /was_derived_from | 1 | 241 |

| Request | A1 cap-scenario input | Calibrated expected input | Input used for cap fit | Output cap | 1M clearance | At-cap 1M fit | 850k report margin |
|---|---:|---:|---:|---:|---:|---|---|
| full | 265,591 | 265,006 | 265,591 | 128,000 | 606,409 | fits estimate | None |
| full_readdress | 301,828 | UNKNOWN | 301,828 | 8,000 | 690,172 | fits estimate | None |
| full_receipt_completion | 356,487 | 348,891 | 356,487 | 4,000 | 639,513 | fits estimate | None |
| full_receipt_completion_after_readdress | 364,843 | 349,240 | 364,843 | 4,000 | 631,157 | fits estimate | None |
| reconcile_full | 922,933 | 442,933 | 922,933 | 128,000 | -50,933 | EXCEEDS estimate | None |
| repair_full | 60,111 | UNKNOWN | 60,111 | 96,000 | 843,889 | fits estimate | None |
| report | 1,084,136 | 604,136 | 1,084,136 | 128,000 | -212,136 | EXCEEDS estimate | False |
| report_after_repair | 1,084,136 | 604,136 | 1,084,136 | 128,000 | -212,136 | EXCEEDS estimate | False |
| report_regate | 1,211,669 | 623,628 | 1,211,669 | 128,000 | -339,669 | EXCEEDS estimate | False |

Typed aggregate: expected UNKNOWN; cap scenario UNKNOWN; registered allowance 4000000; cap-scenario fit `None`.
Typed construction status: `REFUSED`; refusal: `ValueError: missing explicitly supplied vocabulary`.
Every non-fitting request: `['reconcile_full', 'report', 'report_after_repair', 'report_regate']`. Complete stage roster: `False`.

### CHORUS / with_crate / 2026-07-31_claude-opus-5-api-generic_rep1

Selected bounds: `{'max_inventory_bytes': 3895, 'max_paths': 18, 'max_workers': 16}`. Componentwise minimum: `{'max_inventory_bytes': 3895, 'max_paths': 18, 'max_workers': 16}`. Four-worker lexicographic point: `{'actual_workers': 4, 'limits': {'max_inventory_bytes': 16929, 'max_paths': 47, 'max_workers': 4}, 'plan_sha256': 'a838734c7c92126d934cd4ce1bfeefb7ebf1fd2235dd9862044f7da3e3701483'}`.

Record proxy: `None`. Conformance edits: `[]`.

Additional scenario qualifications: `{'proxy_basis': 'July31 final full/core used as phase1 originals; no original phase1/receipt evidence.', 'receipt_basis': 'Synthetic nothing_relevant receipt for all target chunks; understates real receipt.', 'future_output_basis': 'Unknown v10 output; one historical crate-final record scenario.', 'conditional_decision': 'D04 B only'}`.

| Indivisible root | Paths | Canonical inventory bytes |
|---|---:|---:|
| /acquisition_methods | 4 | 1065 |
| /addressing_gaps | 4 | 1340 |
| /anomalies | 5 | 1216 |
| /citation | 1 | 301 |
| /cleaning_strategies | 3 | 905 |
| /collection_mechanisms | 2 | 889 |
| /collection_timeframes | 1 | 503 |
| /confidential_elements | 1 | 323 |
| /conforms_to_schema | 1 | 375 |
| /created_by | 1 | 328 |
| /creators | 8 | 2517 |
| /data_collectors | 3 | 1046 |
| /data_protection_impacts | 1 | 439 |
| /description | 1 | 2126 |
| /direct_collection | 1 | 419 |
| /discouraged_uses | 3 | 686 |
| /distribution_dates | 1 | 322 |
| /distribution_formats | 2 | 900 |
| /doi | 1 | 107 |
| /ethical_reviews | 3 | 1160 |
| /existing_uses | 2 | 700 |
| /extension_mechanism | 1 | 705 |
| /external_resources | 7 | 1830 |
| /file_collections | 4 | 1049 |
| /funders | 1 | 661 |
| /future_use_impacts | 3 | 1109 |
| /human_subject_research | 1 | 459 |
| /id | 1 | 110 |
| /informed_consent | 1 | 379 |
| /instances | 1 | 728 |
| /intended_uses | 10 | 1713 |
| /ip_restrictions | 1 | 566 |
| /is_deidentified | 1 | 745 |
| /issued | 1 | 112 |
| /keywords | 5 | 544 |
| /known_biases | 7 | 1455 |
| /known_limitations | 8 | 1792 |
| /labeling_strategies | 2 | 647 |
| /license | 1 | 157 |
| /license_and_use_terms | 1 | 1273 |
| /machine_annotation_tools | 7 | 1624 |
| /maintainers | 4 | 956 |
| /missing_data_documentation | 1 | 448 |
| /name | 1 | 125 |
| /other_tasks | 2 | 537 |
| /page | 1 | 120 |
| /participant_privacy | 3 | 1039 |
| /preprocessing_strategies | 5 | 1323 |
| /prohibited_uses | 4 | 1104 |
| /purposes | 5 | 1691 |
| /raw_data_sources | 5 | 1171 |
| /raw_sources | 1 | 417 |
| /regulatory_restrictions | 1 | 624 |
| /sampling_strategies | 1 | 468 |
| /sensitive_elements | 3 | 1011 |
| /splits | 1 | 321 |
| /status | 1 | 471 |
| /subpopulations | 3 | 966 |
| /subsets | 18 | 3895 |
| /tasks | 5 | 987 |
| /third_party_sharing | 1 | 620 |
| /title | 1 | 208 |
| /total_size_bytes | 1 | 114 |
| /updates | 1 | 639 |
| /version | 1 | 101 |
| /version_access | 1 | 369 |
| /was_derived_from | 1 | 347 |

| Request | A1 cap-scenario input | Calibrated expected input | Input used for cap fit | Output cap | 1M clearance | At-cap 1M fit | 850k report margin |
|---|---:|---:|---:|---:|---:|---|---|
| worker_0001 | 218,987 | 214,618 | 218,987 | 64,000 | 717,013 | fits estimate | None |
| worker_0002 | 219,313 | 214,938 | 219,313 | 64,000 | 716,687 | fits estimate | None |
| worker_0003 | 218,791 | 214,427 | 218,791 | 64,000 | 717,209 | fits estimate | None |
| worker_0004 | 218,929 | 214,562 | 218,929 | 64,000 | 717,071 | fits estimate | None |
| worker_0005 | 219,436 | 215,058 | 219,436 | 64,000 | 716,564 | fits estimate | None |
| worker_0006 | 219,025 | 214,656 | 219,025 | 64,000 | 716,975 | fits estimate | None |
| worker_0007 | 219,000 | 214,631 | 219,000 | 64,000 | 717,000 | fits estimate | None |
| worker_0008 | 219,161 | 214,789 | 219,161 | 64,000 | 716,839 | fits estimate | None |
| worker_0009 | 219,060 | 214,690 | 219,060 | 64,000 | 716,940 | fits estimate | None |
| worker_0010 | 218,835 | 214,469 | 218,835 | 64,000 | 717,165 | fits estimate | None |
| worker_0011 | 219,086 | 214,716 | 219,086 | 64,000 | 716,914 | fits estimate | None |
| worker_0012 | 218,800 | 214,435 | 218,800 | 64,000 | 717,200 | fits estimate | None |
| worker_0013 | 218,948 | 214,580 | 218,948 | 64,000 | 717,052 | fits estimate | None |
| worker_0014 | 219,253 | 214,879 | 219,253 | 64,000 | 716,747 | fits estimate | None |
| worker_0015 | 218,755 | 214,391 | 218,755 | 64,000 | 717,245 | fits estimate | None |
| worker_0016 | 219,225 | 214,852 | 219,225 | 64,000 | 716,775 | fits estimate | None |
| full | 93,566 | 93,360 | 93,566 | 128,000 | 778,434 | fits estimate | None |
| full_readdress | 109,652 | UNKNOWN | 109,652 | 8,000 | 882,348 | fits estimate | None |
| full_receipt_completion | 133,465 | 130,621 | 133,465 | 4,000 | 862,535 | fits estimate | None |
| full_receipt_completion_after_readdress | 141,821 | 130,970 | 141,821 | 4,000 | 854,179 | fits estimate | None |
| reconcile_full | 1,251,703 | 553,641 | 1,251,703 | 128,000 | -379,703 | EXCEEDS estimate | None |
| repair_full | 42,943 | UNKNOWN | 42,943 | 96,000 | 861,057 | fits estimate | None |
| report | 1,319,980 | 657,427 | 1,319,980 | 128,000 | -447,980 | EXCEEDS estimate | False |
| report_after_repair | 1,319,980 | 657,427 | 1,319,980 | 128,000 | -447,980 | EXCEEDS estimate | False |
| report_regate | 1,447,397 | 744,954 | 1,447,397 | 128,000 | -575,397 | EXCEEDS estimate | False |
| typed_audit_integration | 1,298,070 | 1,151,395 | 1,382,384 | 32,000 | -414,384 | EXCEEDS estimate | None |
| typed_audit_omission | 297,856 | 312,338 | 312,338 | 32,000 | 655,662 | fits estimate | None |

Typed aggregate: expected 4,898,425; cap scenario 5,199,326; registered allowance 4000000; cap-scenario fit `False`.
Typed construction status: `MEASURED`; refusal: `None`.
Every non-fitting request: `['reconcile_full', 'report', 'report_after_repair', 'report_regate', 'typed_audit_integration']`. Complete stage roster: `True`.

## Known-record planning sensitivity

These envelopes plan every listed schema-conformed stand-in, not unseen v10 records. The cost matrix above uses the explicitly measured primary record. CHORUS retains its required 80 / 12,288 / 4 profile; the historical envelope is an A17 diagnostic, not an authorized replacement.

| Project | Staged records | Known-record envelope paths / bytes / workers |
|---|---:|---|
| AI_READI | 3 | 144 / 23876 / 7 |
| CHORUS | 6 | 78 / 9186 / 9 |
| CM4AI | 3 | 150 / 19447 / 6 |
| KIDS_FIRST | 3 | 144 / 23876 / 7 |
| VOICE | 3 | 63 / 12102 / 12 |
| VOICE_PEDIATRIC | 3 | 63 / 12102 / 12 |

## Provenance

Scripts are retained in `scripts/adhoc/` on the K1 branch. Inputs below are SHA256-pinned; no upstream ledger or source bundle was edited.

- `/private/tmp/d4d-codex-k1-20261025/notes/k1_cost_model_2026-10-25/request-sizing-primary.json` — `c85d5eab1e7f9c6394719be0e8e46573c7f2f00a7d14415782a81fb28ec85df3` (1290928 bytes)
- `/private/tmp/d4d-codex-k1-20261025/notes/k1_cost_model_2026-10-25/request-sizing-kids-current-context.json` — `0d782c4e6b1550cf65293ca4dd7e8254ccab8ec10e828df65180a096684fbb38` (295838 bytes)
- `/private/tmp/d4d-codex-k1-20261025/notes/k1_cost_model_2026-10-25/request-sizing-crate-proxy.json` — `71739696e2697d69b5b198625b4223bc95c915a689f8ed959d544f60ea91d4ea` (168467 bytes)
- `/private/tmp/d4d-codex-k1-20261025/notes/k1_cost_model_2026-10-25/ledger_calibration.json` — `928d4f2dae73ab9d94a1d6552c4e31651c43aef2ab7f12be5ea2c327a2fadadd` (44926 bytes)
- `/private/tmp/d4d-codex-k1-20261025/scripts/adhoc/k1_build_cost_report_20261025.py` — `c9f1f63778551788db1fdc801da6624fb817ebe64126eb8210a16c1cef253a12` (28732 bytes)
- `/private/tmp/d4d-codex-k1-20261025/notes/k1_cost_model_2026-10-25/plan-sensitivity.json` — `82eb256457be2d084ca858cf4619d2d250c3f8db48c064e4ea142df6f700ec0a` (3859487 bytes)
