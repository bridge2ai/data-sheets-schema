# Where the British spellings in v5 records come from

- **Date:** 2026-08-21, during the v5 production arm (9 of 12 records complete;
  VOICE ×3 pending — this report covers what existed when it was written and is
  not updated as the arm finishes).
- **Question asked (Marcin):** the British–American mix appears for all GCs —
  is it LLM nondeterminism / instruction disobedience, or do the input
  documents actually carry the mix?
- **Method:** every count below is computed by the real gate instrument —
  `grounding.british_spellings` with `BRITISH_FORMS` and the `_QUOTED`
  exemption imported, not restated. (The first pass of this analysis restated
  the form list from a partial grep, got 16 where the record said 28, and had
  to be redone — the derive-don't-restate lesson applying to analysis as much
  as to code.) Counts are over full + core together, matching what the
  recorded `form.british_spellings` covers.

## Answer in one paragraph

Three sources, measured: **(1) a metric false positive dominates the v5
residual** — the checker substring-matches `analyse`, which counts
**"analyses"**, the correct American plural of "analysis"; 54 of v5's 70
counted occurrences (77%) are that word, and for CHORUS and CM4AI *every*
counted occurrence is. **(2) Source transcription explains nearly all the
rest** — the 16 genuine British occurrences in nine v5 records sit in one run
(AI_READI rep1: `enrolment` ×10, `centre(d)` ×4, `programme` ×2), and all three
forms occur in AI_READI's bundle, which the rule half-permits (quoted source
text keeps its spelling; the checker can only exempt text inside double
quotes, and near-verbatim transcription carries no quote marks). **(3) Genuine
model-authored British — the thing rule 4 exists to stop — is close to
eliminated:** v4's records carried it in bulk (`licence` ×199,
`organisation` ×71, `enrolment` ×71 across 12 records, against bundles that
barely contain those forms), and v5's nine records so far carry at most the
16 occurrences above, none outside one run. Nondeterminism shows up only as
run-to-run variance in how much source phrasing gets transcribed, not as the
rule being intermittently ignored.

## Table 1 — v5 arm (2026-08-20b, 9 of 12 records)

Per record (full + core), as the gate counts it, decomposed:

| run | project | gated total | `analyse` hits | …of which "analyses" (American, FP) | genuine British (forms) |
|---|---|---:|---:|---:|---|
| rep1 | AI_READI | 28 | 12 | 12 | 16 — `enrolment` ×10, `centre(d)` ×4, `programme` ×2 |
| rep1 | CHORUS | 4 | 4 | 4 | 0 |
| rep1 | CM4AI | 0 | 0 | 0 | 0 |
| rep2 | AI_READI | 22 | 22 | 22 | 0 |
| rep2 | CHORUS | 0 | 0 | 0 | 0 |
| rep2 | CM4AI | 2 | 2 | 2 | 0 |
| rep3 | AI_READI | 8 | 8 | 8 | 0 |
| rep3 | CHORUS | 4 | 4 | 4 | 0 |
| rep3 | CM4AI | 2 | 2 | 2 | 0 |
| **total** | | **70** | **54** | **54** | **16** |

Every `analyse` hit in every v5 record is the plural noun ("designing analyses
that depend on image volume") — American English counted as British. Eight of
nine records contain **zero** genuine British forms.

## Table 2 — v4 arm (2026-08-13, all 12 records), same decomposition

| run | project | gated total | `analyse` hits | …"analyses" | dominant genuine forms |
|---|---|---:|---:|---:|---|
| rep1 | AI_READI | 146 | 12 | 12 | `licence` ×53, `organisation` ×32, `enrolment` ×20 |
| rep1 | CHORUS | 28 | 10 | 8 | `programme` ×12, `licence` ×6 |
| rep1 | CM4AI | 55 | 8 | 6 | `licence` ×27, `organisation` ×11, `summarise` ×5 |
| rep1 | VOICE | 29 | 6 | 4 | `organisation` ×10, `standardis` ×7 |
| rep2 | AI_READI | 99 | 7 | 6 | `licence` ×44, `enrolment` ×26, `programme` ×11 |
| rep2 | CHORUS | 28 | 12 | 8 | `programme` ×8, `licence` ×6 |
| rep2 | CM4AI | 6 | 6 | 2 | — |
| rep2 | VOICE | 49 | 2 | 2 | `standardis` ×8, `licence` ×8, `organisation` ×8 |
| rep3 | AI_READI | 113 | 10 | 10 | `licence` ×45, `enrolment` ×18, `programme` ×15 |
| rep3 | CHORUS | 16 | 6 | 6 | `licence` ×10 |
| rep3 | CM4AI | 2 | 0 | 0 | `centre` ×2 |
| rep3 | VOICE | 42 | 6 | 4 | `standardis` ×15, `organisation` ×10 |
| **total** | | **613** | **85** | **68** | **~545 unambiguous** |

## Table 3 — the input bundles

| bundle | gated count | forms present | "analyses" |
|---|---:|---|---:|
| AI_READI | 28 | `programme` ×6, `analyse` ×5, `enrolment` ×4, `centre` ×4, `behaviour` ×3, `licence` ×2, `summarise` ×2, `organisation` ×1, `standardis` ×1 | 4 |
| CHORUS | 0 | — | 0 |
| CM4AI | 23 | `analyse` ×15, `licence` ×4, `labelling` ×2, `centre` ×1, `catalogue` ×1 | 8 |
| VOICE | 6 | `analyse` ×3, `enrolment` ×2, `centre` ×1 | 3 |

## What this establishes

1. **v4's British was model-authored, not source-derived.** v4 CHORUS records
   wrote `licence` and `programme` 6–12 times per run from a bundle containing
   **zero** British forms; v4 AI_READI wrote `licence` ×53 against a bundle
   containing it twice. The model's own default style supplied the British
   forms. That is precisely what rule 4 targets, and on the v5 arm it is gone —
   the ~545 unambiguous v4 occurrences fall to 16, a ~97% reduction, far
   stronger than the gated totals (613 → 70) suggest because the gated totals
   are floored by the false positive on both sides.
2. **The v5 residual is mostly the instrument, not the model.** 54 of 70 v5
   occurrences are "analyses". The FP floor scales with how often a record
   legitimately discusses *analyses* — which datasheets do constantly — so it
   will never reach zero under the current matcher, for any arm.
3. **The rest is transcription, concentrated and explicable.** AI_READI rep1's
   16 genuine occurrences use exactly the forms its bundle carries
   (`enrolment`, `programme`, `centre(d)`); replicates 2–3 of the same project
   carried none, which is nondeterminism in *how much near-verbatim source
   phrasing a run uses*, not in whether the rule is obeyed.
4. **Known instrument defects** (filed as an issue; fix is post-arm because the
   metric is gated and both arms must be measured by the same instrument):
   - substring matching: `analyse` ⊂ "analyses" (FP), and conversely a
     genuinely British "colour" observed in an AI_READI record is uncounted
     because `colour` is not in `BRITISH_FORMS` (FN);
   - the quote exemption sees only `"…"` spans, so unquoted transcription of
     source text counts against the record while the rule half-permits it.
5. **Comparisons remain internally valid.** Both arms are measured by the same
   instrument, which is the plan's standard (#602). Absolute values overstate
   British usage on both sides; the v4→v5 *change* understates the rule's
   effect.

## Prediction 5 status

"British spellings fall on the API arm" — **confirmed, and understated by the
gated metric.** Gated: 613 → 70 for 12-vs-9 records. Genuine: ~545 → 16.
Final numbers after VOICE ×3 complete belong to the arm analysis, not this
report.
