# 2026-08-28 agentic v6 arm results

- **Arm:** `2026-08-28_claude-opus-5-claudecode-generic-v6` — 12 runs (4 projects
  × 3 replicates), condition `generic_v6` (pinned), runtime Claude Code, model
  `claude-opus-5` (subagent model override), four-phase project-agent mode.
  **The first arm under the receipt protocol (#709) and the derived-core
  playbook (#750)**, and the first under a receipt-gated canary (#708).
- **Launch path:** each run's instruction rendered by `d4d prompt render
  --condition generic_v6 --runtime 'Claude Code'`; the canary (CHORUS rep1)
  received it inline, the 11 fan-out runs read the rendered bytes from a file
  — the same one mechanical difference as the 2026-08-24 arm. Waves of four.
  Wave-1 agents recorded without `--condition`, so their specs were attached
  afterwards by `d4d provenance backfill-spec`, which writes only what
  re-renders to the recorded hash (#772); every record now passes the render
  gate. VOICE rep2's agent lost its connection after Phase 1 and resumed under
  the same label with its receipt intact (#735's rule, exercised).
- **Outcome: 12 succeeded, 0 failed.** `d4d runs check --strict` exit 0 on all
  three labels. Reasoning effort is absent on every record: the launcher had no
  way to set it and asserted nothing (#397's third case).

## Per run

| rep | project | chunks | snippets verified | slots with a receipt | unopened | absent | minted | pair | British | undeclared | Mtok | min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | AI_READI | 28/28 | 580/580 | 348/639 | **2** | 0 | 10 | 0 | 0 | 0 | 41.2 | 41 |
| 1 | CHORUS | 8/8 | 106/106 | 86/190 | 0 | 0 | 0 | 0 | 0 | 0 | 14.3 | 138 |
| 1 | CM4AI | 28/28 | 367/367 | 245/753 | 0 | 0 | 51 | 0 | 0 | **2** | 42.5 | 46 |
| 1 | VOICE | 22/22 | 199/199 | 140/587 | 0 | 0 | 19 | 0 | 0 | 0 | 26.7 | 35 |
| 2 | AI_READI | 28/28 | 328/328 | 222/536 | 0 | 0 | 13 | 0 | 0 | 0 | 35.8 | 39 |
| 2 | CHORUS | 8/8 | 109/109 | 136/194 | 0 | 0 | 0 | 0 | 0 | 0 | 13.2 | 26 |
| 2 | CM4AI | 28/28 | 328/328 | 209/472 | 0 | 0 | 15 | 0 | 2 | 0 | 41.5 | 40 |
| 2 | VOICE | 22/22 | 271/271 | 184/432 | 0 | 0 | 8 | 0 | **35** | 0 | 27.5 | 75 |
| 3 | AI_READI | 28/28 | 415/415 | 236/567 | 0 | 0 | 9 | 0 | 0 | 0 | 41.1 | 45 |
| 3 | CHORUS | 8/8 | 108/108 | 96/182 | 0 | 0 | 0 | 0 | 0 | 0 | 16.1 | 27 |
| 3 | CM4AI | 28/28 | 313/313 | 724/763 | 0 | 0 | 51 | 0 | 0 | 0 | 41.8 | 46 |
| 3 | VOICE | 22/22 | 276/276 | 194/531 | 0 | 0 | 14 | 0 | 0 | 0 | 37.0 | 41 |

Mtok and min are `run_observed` from the transcripts (per-message usage,
successful file-tool reads only; #703). CHORUS rep1's 138 min is the canary's
wall time from launch, most of it before its first receipt entry.

## Gate

Canary (CHORUS rep1) `ok` on all eleven floors. Of the eleven fan-out runs,
nine `ok`; two regressed on a per-project v5 worst: CM4AI rep1 on undeclared
prefixes (2 — a `mailto:` URI in an identifier slot, one distinct value) and
VOICE rep2 on British spellings (35 against 4). Both are recorded and neither
touches the receipt.

## The receipt, measured for the first time on the agentic arm

- **Coverage:** every manifest chunk reviewed on every run — 12/12 at 100%,
  where the 2026-08-24 arm never opened roughly a fifth of AI_READI, CM4AI and
  VOICE (#700). `bundle_lines_read` is 100% on eleven runs. AI_READI rep1 is
  the exception and the detector caught it: it opened c019 with 200 of 400
  lines and c026 with 150 of 296, receipted both as reviewed (c019
  `extracted`, 40 snippets — all from the read half; c026 `nothing_relevant`,
  and the unread half is indeed more of the same blank IRB form), and its
  report says all 28 chunks were read in full. `bundle_lines_read` 7030/7376
  is exactly the two missing halves, and `receipt_chunks_unopened: 2` is the
  receipt claiming what the transcript does not show (#775). No snippet rests
  on an unread line, so the record is not wrong; the claim of coverage is.
  Its one `sed -n` read was of c023/c024, both also opened in full, and is
  irrelevant to the two.
- **Support:** 3,400 of 3,400 snippets verify verbatim against the chunk
  cited. Zero mismatched, zero in another chunk. The API arm's v7 canaries
  cite the neighbouring chunk for ~2% (#763); the agentic arm, which reads a
  chunk and writes its entry before the next, does not — with one protocol
  deviation the transcripts show: CM4AI rep3 added and removed receipt
  entries by script after running the check, rather than only as it read
  (#776). Two runs (AI_READI rep2, CM4AI rep3) also ran the validator's own
  functions against their receipt from a shell — verification, not
  extraction.
- **Slots with a receipt:** 45–95% of receiptable leaves, highly variable
  (CM4AI rep3 724/763; CHORUS rep1 86/190). The residue is mostly nested
  leaves under entries the agent receipted at the leaf it copied rather than
  at the entry — a reporting convention, not a coverage gap, and the first
  number to read per slot when comparing arms (#708's prediction 5 on the API
  side).

- **Report claims:** `claims_checked` is 0 on 10 of 12 reports (VOICE rep2
  and CM4AI rep3 have 1), so the arm's "report findings 0" is the #684
  vacuity, not a measured clean — as on the 2026-08-24 arm. Pair warnings
  (`semantic-review-required`, 1) on 7 of 12; errors 0 on all.

## Predictions of `notes/generic_v6_analysis_plan.md`

| # | prediction | result |
|---|---|---|
| 1 | minted fragments fall on VOICE/CM4AI and the within-project spread collapses to ≤5 | **Half.** VOICE 19/8/14 (v5: 3/14/130) — the 130 is gone and the spread is 11, not ≤5. CM4AI 51/15/51 (v5: 42/55/51) — no fall, spread 36. AI_READI 10/13/9, CHORUS 0/0/0. The norm removed the outlier and did not converge CM4AI; falsified as stated, on CM4AI. |
| 2 | ungrounded identifiers stay 0 | **Held.** 0 on 12/12. |
| 3 | pair errors 0 by construction | **Held.** 0 on 12/12 (derived core). |
| 4 | no run exceeds its v5 British-spelling worst | **Falsified once.** VOICE rep2 35 against 4; the other 11 at 0–2. |
| 5 | populated slots do not fall | Deferred to the arm comparison (`scripts/arm_comparison.py`). |
| 6 | core-only content zero | **Held** by construction; every core is a projection. |

## What is not yet done

- Semantic evaluations (rubric10/rubric20) and the cross-arm comparison
  against 2026-08-24 (v5) and the v7 API arm, once that arm exists.
- Canonical selection: #677 is fixed, so `d4d runs select` can now run without
  severing the chain; not run here — a decision for the arm comparison.
- The 12 records carry no reasoning effort and `model.temperature` asserted,
  as before.
