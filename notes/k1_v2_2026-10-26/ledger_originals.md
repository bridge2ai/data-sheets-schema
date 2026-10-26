# K1 v2: original-ledger and timing audit

Generated offline on 2026-10-26. Both canaries remain evidence-only; this report does not establish scientific acceptance or billing reconciliation.

## Original-row comparison

| Run / preserved snapshot | Matched rows | Changed matched rows | Added later rows |
|---|---:|---:|---:|
| 2026-10-20a / CHORUS_api_usage_8d1427f7e332bdc2.json | 8 | 0 | 3 |
| 2026-10-20a / CHORUS_api_usage_8d1427f7e332bdc2_phase5.json | 10 | 1 | 1 |
| 2026-10-22a / no verified pre-edit original | unknown | unknown | unknown |

The preserved snapshots cover 10 distinct usage IDs. There are 0 distinct changed input/output/thinking, cache read/write, maximum-output, phase, attempt, duration, timestamp, model-stop or outcome fields among matched rows. Admission/response-pin changes are listed separately below. Later rows absent from every original remain independently unverified.

Surviving ledger hashes match K1's recorded source hashes: **True**. Raw fields in the 20 settled rows and 2 abandoned rows match K1's extracted copies: **True**. That internal consistency cannot authenticate edited outcomes or substitute for the missing 10-22 original.

Every changed matched row (all raw fields; missing is distinct from null):

- `72ac7d9a77bb438798e7d8d55ff1bf0f` `/source_review_admission/response_sha256`: `{"present": true, "value": "d1df3ae1cec6402955efee391b898a01c688955b2180dce69344bbb70a829834"}` → `{"present": true, "value": "1fe397926ba14fde7d3474ec6ab0afcffa2e359c116b3feb13184061dbc4e1b6"}`.
- `72ac7d9a77bb438798e7d8d55ff1bf0f` `/source_review_admission/state`: `{"present": true, "value": "pending"}` → `{"present": true, "value": "accepted"}`.

The JSON records every comparison, including K1-versus-edited rows, all non-row ledger differences, and later additions. A later row absent from an earlier snapshot is not by itself evidence of an improper edit. The 10-20 originals already follow earlier registration/receipt re-pinning documented in review N2.

For 10-22, N1 documents a manual terminal-state reset, stage edits, deletion of a failure field and usage-ID reference, and another paid integration call. The surviving edited counters cannot independently prove that all original usage rows are unchanged. Accepted/checked states are not trusted outcomes.

## Bounded absence evidence

The ignored/hidden-inclusive inventory read all 178 regular files under `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/evidence/agy-scratch-preserved-2026-10-25`. It found 0 standalone 10-22 ledger candidates. Filename/content matches, hashes, nonregular exclusions and parsed ledger candidates are retained in the JSON. This is a subtree-limited finding, not a global absence claim.

## Worker duration and cache timing

| Run | Usage ID | Seconds | Original timing matched |
|---|---|---:|---|
| 2026-10-20a | `d2b5eed070e44b1ab99fd399dda6de1f` | 541.771 | True |
| 2026-10-20a | `4b4aaf0f017246ddbca3a614e24de8e9` | 235.708 | True |
| 2026-10-20a | `8ff30d9469e943a48916b15bd561a3a0` | 490.518 | True |
| 2026-10-22a | `3cff194dce1843749e4c376a369d2624` | 515.309 | False |
| 2026-10-22a | `c93d399370e54bf784c934c89762395c` | 436.318 | False |
| 2026-10-22a | `a5cc763e58ff48b08df90e5ebe4c4f80` | 153.741 | False |

Six completed 64k-cap workers took 153.741–541.771s (mean 395.561s). The separate truncated 25k-cap attempt is excluded from this timing sample and cannot establish ordinary retry permission.

| Run | Start-to-start seconds | Previous-end-to-start seconds |
|---|---:|---:|
| 2026-10-20a | 545.000 | 3.229 |
| 2026-10-20a | 241.000 | 5.292 |
| 2026-10-22a | 519.000 | 3.691 |
| 2026-10-22a | 440.000 | 3.682 |

A hypothetical shared-prefix cache has two cold starts across these two three-worker runs. Assuming each preceding request creates/refreshes it sometime between that request's start and end, the observed timing yields:

| Assumed TTL | Possible timing hits / six calls | Caveat |
|---|---:|---|
| 300s | 1–4 / 6 | Conditional timing bounds, not observed cache hits |
| 3600s | 4–4 / 6 | Conditional timing bounds, not observed cache hits |

All six workers recorded zero cache-read tokens. A 300s or 3600s TTL, creation/refresh timing, stable shared prefix, route support and eviction policy are scenario assumptions; no current provider fact or price is asserted. Do not credit these hypothetical savings to the baseline budget before implementation and route verification. Timestamp rounding matters near boundaries.

Input SHA256s, exact raw differences, stage timing and abandoned-attempt fields are in [ledger_originals.json](ledger_originals.json). The helper is [k1_v2_ledger_originals_20261026.py](../../scripts/adhoc/k1_v2_ledger_originals_20261026.py).
