# Absence lexicon v3: `rsn.source-ranking` needs a preference or resolution verb (2026-09-30, #3520)

`absence_self_narration` v3 is registered beside v1 and v2, whose bytes are
unchanged. It changes one pattern, `rsn.source-ranking`; every other pattern,
the flags, the scope and the class descriptions are v2's
(`tests/test_lexicons.py` holds v3 to that). `notes/absence_claims_baseline.md`
now counts under v3 (`LEXICON_VERSION = 3` in
`scripts/absence_claims_baseline.py`), over the same 303 pinned records
(record-set sha256 `cb4b5b8a…`), and the `d4d review absence-lint` default,
which is the newest registered version, moves from v2 to v3.

## Why

All three borderline phrases in the v1 precision sample were
`rsn.source-ranking` hits on source conflicts worded with the ranking
vocabulary: "Within the same tier-1 source, …", "two tier-1 sources
disagree", "The project documentation, a higher-ranked source, gives a
target of …". They say nothing about how the record was built. v2 changed no
regex, so they could not be counterexamples there.

## What v3 matches

- The names of the declared ranking (source manifest, input manifest, source
  ranking, declared ranking) match wherever they appear, as in v2.
- A ranking term applied to a source (tier-N source, higher-ranked, ranks
  higher, …) matches only when a preference or resolution verb (preferred,
  used, followed, recorded, stated, decide, settle, separate, …) lies within
  80 characters in the same sentence, before or after it. `;` and a `.`
  followed by whitespace end the sentence; a `.` inside `v3.1.0` does not.
- With the verb first, the match runs from the verb to the term, so a
  phrase's text can be longer than v2's for the same words.
- Two consequences of that span, which the pattern's comment does not state
  (#3732). A name of the declared ranking lying between a verb and a later
  ranking term is inside the verb-first span and is not a match of its own:
  "The value used from the input manifest is the higher-ranked one." gives
  one match, "used from the input manifest is the higher-ranked", where v2
  gives two. So "wherever they appear, as in v2" holds for the names' text,
  which is always inside a flagged span, but not for their count as separate
  phrases. And matches do not overlap, so a verb consumed by one span cannot
  admit a second ranking term after it: in "It was preferred over the
  lower-ranked source, the higher-ranked one being older." only "preferred
  over the lower-ranked" matches. The 80-character rule above is a condition
  a match needs, not a promise that every term meeting it matches.
  `tests/test_lexicons.py` holds both. Over the 303 pinned records (a
  reimplementation of the rule in the review round's scratch script, not a
  recorded instrument) one name is absorbed (`claudecode_agent/…v5_rep2`
  VOICE, "resolved by the input manifest's ranking, the higher-ranked
  source") and two terms the rule admits sit in no span (`claudecode_api/
  2026-09-04e…rep1` VOICE "the lower-ranked white paper" after "recorded as
  separate purposes because the higher-ranked documentation"; `2026-09-04g…
  rep3` AI_READI "tier-1 sources" after "recorded because two equally
  ranked"). The counts below are what the regex matches and do not move.

The three borderline phrases are v3 counterexamples, and v2 matches each of
them.

## Counts, v1/v2 → v3 (303 pinned records)

v1 and v2 match the same text, so their counts are the same.

| | v1/v2 | v3 |
|---|---:|---:|
| `rsn.source-ranking` matches | 336 | 248 |
| `rsn.source-ranking` records | 98 | 95 |
| record_self_narration phrases | 1,830 | 1,732 |
| record_self_narration records | 229 | 229 |
| bundle_wide_absence phrases / records | 1,141 / 202 | 1,141 / 202 |
| records with any phrase | 252 | 252 |

By method, only `claudecode_agent` (1,469 → 1,400 record_self_narration
phrases) and `claudecode_api` (216 → 187) move. Phrases fall by 98 while
matches fall by 88: a match that starts at its verb can overlap another
record_self_narration phrase in the same leaf, and overlapping spans are one
phrase.

## Precision

`--sample 50 --seed 2919` under v3 draws `bd0c63ed…`. Its
record_self_narration phrases were read in context and judged 50 in class,
0 borderline, 0 not in class (v1: 47/3/0). Its bundle_wide_absence draw is
v1's phrase for phrase (no pattern of that class moved), so those 50 verdicts
are carried over from the v1 file (50/0/0), not re-read. The verdicts are in
`notes/absence_precision_judgements_bd0c63ed.yaml`, written down when the
sample was checked. One rater, the implementing agent: not an independent
review (#3197's open part).

## What v3 gives up

This is a precision change, and it costs recall: the verb list and the
80-character, same-sentence window drop some ranking terms in sentences that
do narrate the record's construction. Reading the 88 dropped matches, the
implementing agent put roughly a fifth of them in that group: the verb more
than 80 characters away ("… the higher-ranked source in the input manifest
(tier 1, versus tier 3 …), so its expansion is preferred here"), after a `;`,
or a phrase the list does not name ("is left unpopulated"). About half of
those are referent sentences ("This record describes …, the highest-ranked
source in the bundle") that `rsn.this-record` still matches. That reading is
not a recorded judgement; the recall of the change is unmeasured. A cause
not in that reading is the non-overlap described under "What v3 matches":
two ranking terms in the pinned records whose only verb an earlier match
had already consumed.
