# Absence lexicon v4: `rsn.source-ranking` finds its verb anywhere in the sentence (2026-09-30, #3791, #3792)

`absence_self_narration` v4 is registered beside v1 to v3, whose bytes and
pins are unchanged. It changes one pattern, `rsn.source-ranking`; every other
pattern, the flags, the scope and the class descriptions are v3's
(`tests/test_lexicons.py` holds v4 to that). `notes/absence_claims_baseline.md`
now counts under v4 (`LEXICON_VERSION = 4` in
`scripts/absence_claims_baseline.py`) over the same 303 pinned records
(record-set sha256 `cb4b5b8a…`), and the `d4d review absence-lint` default,
which is the newest registered version, moves from v3 to v4.

## Why

v3 (#3520) required a preference or resolution verb within 80 characters of a
ranking term, in a sentence that ended at `;` or at a `.` before whitespace.
`notes/absence_v3_recall.md` (#3705) judged all 88 v2 matches that rule drops:
35 in class, 50 borderline source statements, 3 absences asserted across the
sources. The owner opened v4 to recover what it could of the 35 (#3791), on
that evidence: let the window cross `;`, do not lift the 80-character bound on
its own, and do not cross a full stop.

## What v4 matches

- The names of the declared ranking match wherever they appear, as in v2 and
  v3. Whether they should (#3706) is a separate open decision and v4 leaves
  it untouched.
- A ranking term applied to a source matches when one of v3's verbs lies
  anywhere in the same sentence, before or after it. v3's alternatives, verb
  list and ranking terms are unchanged; only the gap between verb and term
  moves (a test holds the regex to exactly that substitution).
- The sentence ends only at a `.` followed by whitespace. `;` no longer ends
  it, and there is no length bound.
- The `.` of St., Dr., e.g., i.e. and U.S. does not end it (#3792). Those are
  the abbreviations the pinned records' free text carries mid-sentence (St.
  183 times, e.g. 87, U.S. 79, Dr. 7, i.e. 7). "No." (42) is not excepted: in
  these records it ends a sentence ("FDA Regulated: No."). Nor is "et al."
  (206): in 51 of those a capitalised title follows, where it ends a
  citation's author list. The counterexample "The higher-ranked source gives
  Washington University in St. Louis. Both values are recorded above." shows
  the full stop after "Louis" still ends the sentence.

**Which change this is.** Crossing `;` "with no length bound", as the issue
put it, is the change table's cumulative "Widen the window and cross `;`"
row, not "Cross `;` only (80-character window kept)". Only the cumulative row
recovers all 5 in-class phrases in sentences v3 counts nothing in (crossing
`;` with the bound kept recovers 2), which the owner's decision named. It
therefore also brings the `window` rows: the brief's "17 in-class phrases
(14 construction, 3 referent)" counts the `semicolon` cause row alone; with
the `window` rows it is 24 in class (21 construction, 3 referent) and 2
borderline source statements.

## Counts, v3 → v4 (303 pinned records)

| | v3 | v4 |
|---|---:|---:|
| `rsn.source-ranking` matches | 248 | 276 |
| `rsn.source-ranking` records | 95 | 96 |
| record_self_narration phrases | 1,732 | 1,757 |
| record_self_narration records | 229 | 229 |
| bundle_wide_absence phrases / records | 1,141 / 202 | 1,141 / 202 |
| records with any phrase | 252 | 252 |

By method, only `claudecode_agent` (1,400 → 1,418 record_self_narration
phrases) and `claudecode_api` (187 → 194) move. Phrases rise by 25 while
matches rise by 28: a longer verb-first match can overlap another
record_self_narration phrase in the same leaf, and overlapping spans are one
phrase. In one record (`claudecode_agent/2026-08-20b…v5_rep3` AI_READI) a
longer span joins two phrases that v3 counted apart, so its phrase count
falls by one while its matches do not move. Every v3 match of the pattern
still ends where a v4 match ends.

By label (`rsn.source-ranking` matches; record_self_narration phrases), the
twenty that move:

| label | matches | phrases |
|---|---:|---:|
| `claudecode_agent/2026-08-19_claude-opus-5-api-generic-v5_rep1` | 0 → 1 | 3 → 4 |
| `claudecode_agent/2026-08-20_claude-opus-5-api-generic-v5_rep1` | 3 → 6 | 18 → 21 |
| `claudecode_agent/2026-08-20b_claude-opus-5-api-generic-v5_rep3` | 13 → 13 | 48 → 47 |
| `claudecode_agent/2026-08-22c_claude-opus-5-api-generic-v5_rep1` | 11 → 13 | 48 → 49 |
| `claudecode_agent/2026-08-22c_claude-opus-5-api-generic-v5_rep3` | 14 → 15 | 72 → 73 |
| `claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2` | 21 → 23 | 59 → 61 |
| `claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2` | 14 → 15 | 49 → 50 |
| `claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3` | 4 → 5 | 34 → 35 |
| `claudecode_agent/2026-08-28b_claude-opus-5-api-generic-v7_rep1` | 8 → 10 | 22 → 24 |
| `claudecode_agent/2026-08-28c_claude-opus-5-api-generic-v7_rep1` | 2 → 3 | 22 → 23 |
| `claudecode_agent/2026-08-28d_claude-opus-5-api-generic-v7_rep1` | 7 → 9 | 21 → 23 |
| `claudecode_agent/2026-09-01_claude-opus-5-api-generic-v7_rep1` | 7 → 9 | 36 → 38 |
| `claudecode_agent/2026-09-01_claude-opus-5-api-generic-v7_rep2` | 8 → 9 | 55 → 56 |
| `claudecode_agent/2026-09-01_claude-opus-5-api-generic-v7_rep3` | 10 → 11 | 41 → 42 |
| `claudecode_api/2026-09-04d_claude-opus-5-api-generic-v8_rep1` | 4 → 5 | 20 → 21 |
| `claudecode_api/2026-09-04e_claude-opus-5-api-generic-v8_rep1` | 3 → 4 | 14 → 15 |
| `claudecode_api/2026-09-04f_claude-opus-5-api-generic-v8_rep1` | 6 → 9 | 26 → 29 |
| `claudecode_api/2026-09-04f_claude-opus-5-api-generic-v8_rep2` | 8 → 9 | 26 → 27 |
| `claudecode_api/2026-09-04g_claude-opus-5-api-generic-v8_rep1` | 4 → 5 | 15 → 15 |
| `claudecode_api/2026-09-04g_claude-opus-5-api-generic-v8_rep3` | 7 → 8 | 24 → 25 |

This table is a one-off reading made when v4 was registered, not a
regenerated note; the per-method table in `notes/absence_claims_baseline.md`
is the recorded instrument.

## Precision

`--sample 50 --seed 2919` under v4 draws `574f03c2…`. Its
record_self_narration phrases were read in context and judged 49 in class,
1 borderline, 0 not in class (v3: 50/0/0; v1: 47/3/0). The borderline phrase
is "input manifest" in "The PhysioNet release pages, which the input manifest
ranks higher, state no single total …": a name of the declared ranking in a
sentence that reports the sources, which v2, v3 and v4 all match without a
verb (#3706); v4's change does not reach it. The bundle_wide_absence draw is
v1's and v3's phrase for phrase, so those 50 verdicts are carried over (50/0/0),
not re-read. The verdicts are in
`notes/absence_precision_judgements_574f03c2.yaml`, written down when the
sample was checked. One rater, the implementing agent: not an independent
review (#3197's open part).

## Recall

`notes/absence_v3_recall.md` now says what v4 does with each of the 88
dropped matches, from the committed judgements (`scripts/absence_v3_recall.py`,
which loads v4 by its pinned sha256). v4 recovers 28: 24 in class (21
construction, 3 referent), 3 borderline, 1 not in class; one more
construction row (`absorbed`) lies inside a longer v4 match. It recovers all
5 in-class phrases in sentences v3 counts nothing in. If all of v3's matches
are in class, v4 keeps 272 of 283 (96.1%) of the in-class matches v2 had,
against v3's 248 (87.6%); like v3's figure, an upper bound.

What v4 admits besides:

- 2 borderline source statements through the unbounded window (judgements
  #16 and #82, caveats about a source's stability), on a listed verb the
  sentence does not turn on.
- 1 absence asserted across the sources, past a `;` (#19, "no tier-1 source
  states them").
- 1 borderline source statement past "St." (#87: "… is given as Washington
  University in St. Louis in the tier-1 FAIRhub study_description …; the two
  tier-1 sources disagree"). This is the case #3792 anticipated: the
  abbreviation rule is right, and the verb it brings into reach ("given")
  reports what a source states.

The in-class rows v4 does not recover are 8 referent sentences whose verb is
in another sentence (all in sentences `rsn.this-record` already counts), 1
`absorbed` and 2 `consumed` construction rows, which no bound decides.

## What consumes it

- `d4d review absence-lint` loads the newest registered version, so its
  output now names v4. It is read-only and never gating.
- `scripts/absence_claims_baseline.py` counts under `LEXICON_VERSION = 4`.
- `scripts/absence_v3_recall.py` still measures v3 against v2 and now also
  reports v4's recoveries; its judgements file is unchanged.
- Nothing else imports `absence_lint` or the `lexicons/` registry: not the
  q19 rationale lint (its own regexes), `scripts/arm_comparison.py`,
  `routing_diagnostics` or the self-disclaimed lint (its own
  `container_lexicons/`). `notes/matched_cborg_2026-09-13/` (audit28) imports
  neither (searched with `grep -r`, gitignored files included), so audit28 is
  unaffected.
