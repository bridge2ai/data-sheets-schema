# K1 archived usage and calibration

Compare A1's byte estimate with observed input+cache-read+cache-write; fit same-stage total tokens/payload-byte, cross-validate on the other CHORUS canary.

| Run | Settled calls | Settled usage cost | Abandoned partial usage | Sum (observed lower bound) |
|---|---:|---:|---:|---:|
| 2026-10-20a | 11 | $20.587444 | $0.854704 | $21.442148 |
| 2026-10-22a | 9 | $15.170780 | $1.981379 | $17.152158 |

| Stage | Joined requests / settled calls | Fitted tokens/byte | Raw A1 error % range | Other-canary max absolute error % | Completed output mean |
|---|---:|---:|---|---:|---:|
| full | 2 / 2 | 0.36058085429483683 | [0.20140034062339218, 0.24128867021635525] | 0.03919872401394464 | 44965 |
| full_receipt_completion | 2 / 2 | 0.3623903586964273 | [2.123634529191487, 2.2316705591153063] | 0.10679282192547213 | 1651.5 |
| reconcile_full | 0 / 2 | UNKNOWN | UNKNOWN | UNKNOWN | 12184.5 |
| report | 0 / 2 | UNKNOWN | UNKNOWN | UNKNOWN | 81147.5 |
| report_regate | 0 / 1 | UNKNOWN | UNKNOWN | UNKNOWN | 74038 |
| typed_audit_integration | 2 / 2 | 0.5531286082446614 | [-28.00948737134871, -23.401147659412036] | 6.400772256800624 | 23168.5 |
| typed_audit_omission | 2 / 2 | 0.3989170083590331 | [-4.762204592200813, -4.514938239052391] | 0.2596190901162254 | 22656.5 |
| typed_audit_worker | 6 / 7 | 0.4020558297339848 | [1.8517445649812503, 2.199303276911291] | 0.3150210738235626 | 38481.666666666664 |

- Only two CHORUS runs; not evidence of cross-project output/caching behavior.
- Reported output_tokens already includes thinking; do not add thinking_tokens again.
- Historical full envelope reconstructed from retained exchange; other calibrated stages have pinned logical payloads.
- Reconcile/report/regate have observed token usage but no retained request-body join; their byte error is UNKNOWN.
- 10-20a includes one paid typed worker truncated at an earlier 25,000-token cap; this is not evidence for ordinary-phase retry probability or authorization for typed retries.
- Abandoned rows are observed partial charges, not final invoices or a measured retry distribution.
