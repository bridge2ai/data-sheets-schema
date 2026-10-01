# Absence lexicon v5: a verb for the ranking's names, a verb `use`, one sentence end (2026-09-30, #3875, #3887, #3874, #3706)

`absence_self_narration` v5 is registered beside v1 to v4, whose bytes and
pins are unchanged. It changes four patterns: `rsn.source-ranking` and the
three bundle-wide patterns with a bounded window (`bwa.not-by-any-source`,
`bwa.not-in-bundle`, `bwa.not-in-the-sources`). Every other pattern, the
flags, the scope and the class descriptions are v4's (`tests/test_lexicons.py`
holds v5 to that). `notes/absence_claims_baseline.md` now counts under v5
(`LEXICON_VERSION = 5` in `scripts/absence_claims_baseline.py`) over the same
303 pinned records (record-set sha256 `cb4b5b8a…`), and the
`d4d review absence-lint` default, which is the newest registered version,
moves from v4 to v5.

## Why

The owner decided all four on 2026-09-30, in one version:

- #3875: kept match #48 of the #3793 precision draw matched because v4 took
  the `use` of "data transfer and use agreement" for a preference verb.
- #3887: v4 (#3792) exempted St., Dr., e.g., i.e. and U.S. from ending a
  sentence in `rsn.source-ranking` only. The three bundle-wide windows still
  stopped at any `.`.
- #3874 with #3706: v1 to v4 matched the names of the declared ranking
  (source manifest, input manifest, source ranking, declared ranking)
  anywhere. Three of the five borderline phrases in the #3793 draw, and the one
  borderline phrase in v4's own precision sample, are sentences that cite the
  manifest as the carrier of a fact ("The source manifest records pediatric raw
  audio as syn73617068."). The decision is the one v3 made for the ranking
  vocabulary (#3520): such a sentence reports a source, so the names need a
  preference or resolution verb in the sentence, as the ranking terms do.

#3886 is not part of this version.

## What v5 matches

- **The names of the declared ranking are ranking terms** (#3874, #3706).
  They match only with one of the pattern's verbs in the same sentence, before
  or after them, under v4's window: no length bound, `;` crossed, a full stop
  not crossed. v4's own example "The source manifest records the release date."
  is now a counterexample. A test holds the regex to exactly v4's with the
  names moved into the term list on both branches.
- **`use` and `uses` count as the verb only where the text does not mark them
  as a noun** (#3875). They are not a verb after *the, a, an, its, their, any,
  no, for, of, in* or *data*, or before *agreement(s), of, case(s),
  limitation(s), restriction(s), condition(s), terms* or *policy (policies)*.
  `used` and `using` are unchanged. Over the pinned records' free text bare
  `use`/`uses` occurs 2,916 times, overwhelmingly as a noun: "use agreement(s)"
  733 times, "use of" 387, "data use" 504. The guard is a list, not a parser,
  so a noun `use` after an adjective ("secondary use") still counts as a verb.
  The test shows each guard deciding on its own, with one word changed at a
  time. No other pattern has this verb list (`rsn.recorded-here` has `used`
  only), so no other pattern changes on this account.
- **The bundle-wide windows end where `rsn.source-ranking`'s sentence ends**
  (#3887). In each of the three patterns, only the window's character class
  changes, to `(?:[^.;:]|\.(?!\s)|(?<=\bSt)\.(?=\s)|…|(?<=\bU\.S)\.(?=\s))`. A
  `.` not followed by whitespace, and the `.` of St., Dr., e.g., i.e. and U.S.
  before whitespace, no longer end it. Every other `.` still ends it, as `;`
  and `:` do, and it is still at most 80 characters. These are #3894's
  disjoint alternatives, and a test shows that no character of a dense
  abbreviation text can be taken two ways. The window is bounded, and the lint's
  linear-time test now includes a bundle-wide sentence with 20 to 40 "e.g.," and
  no partner. Sharing the sentence end brings the in-token `.` as well: the
  first `.` of "e.g." needs it, so the abbreviations cannot be excepted without
  it.

## Counts, v4 → v5 (303 pinned records)

| | v4 | v5 |
|---|---:|---:|
| `rsn.source-ranking` matches | 276 | 241 |
| `rsn.source-ranking` records | 96 | 83 |
| `bwa.not-in-the-sources` matches | 167 | 168 |
| record_self_narration phrases | 1,757 | 1,718 |
| record_self_narration records | 229 | 229 |
| bundle_wide_absence phrases / records | 1,141 / 202 | 1,142 / 202 |
| records with any phrase | 252 | 252 |

No other pattern's count moves. By method: `claudecode_agent` record_self_narration
1,418 → 1,386 and bundle_wide_absence 994 → 995, `claudecode_agent_merged`
24 → 19, and `claudecode_api` 194 → 192. No method's record counts move.

**`rsn.source-ranking`.** 36 v4 matches lose their end and 1 v5 match ends where
no v4 match did, so the net change is −35.

- 35 are a name of the declared ranking with no listed verb in its sentence.
- 1 is the #3875 mechanism: "the two equally ranked sources characterize …
  the data transfer and use agreement states …", whose only listed verb was
  the noun `use`.
- The new end is in `claudecode_agent/2026-08-24…v5_rep2` VOICE
  `/source_caveats`. There v4's single span "resolved by the input manifest's
  ranking, the higher-ranked" becomes two v5 matches, "resolved by the input
  manifest" and "higher-ranked", because a name now ends a verb-first span.

Phrases fall by 39 while matches fall by 35. The 36 lost matches and the split
give −35. In four leaves a v5 verb-first span ("recorded here … input manifest")
now reaches a name and overlaps a `rsn.recorded-here` phrase, joining two
phrases into one, which gives −4.

My one-off reading of the 36 lost matches finds 31 source statements
(borderline: the manifest cited as the carrier of a fact, or "which the input
manifest ranks higher, state …") and 1 referent sentence ("which the declared
source ranking treats as the current release"). The other 4 are construction:
"The declared source ranking was applied." and "which the input manifest
retains as the only record", whose verbs the list lacks; the #3875 sentence,
which `rsn.left-empty` still counts; and one name whose verb a verb-first span
to an earlier tier term consumed (#3732's non-overlap), in a sentence the v5
span still flags. This reading is not a judgement file: one rater, made while
writing this note.

**Bundle-wide windows.** One new match:
`claudecode_agent/2026-07-31…api-generic_rep2` CM4AI
`/regulatory_restrictions/description`, "No export control designations (e.g.
ITAR or EAR) are stated in the available sources", in class, and the case
#3887 anticipated. Two v4 matches keep their end but start earlier.

- One crosses `.json` in "ro-crate-metadata.json, so it is not established
  from the sources". That is the right sentence.
- One crosses the `."` that closes a quoted source sentence: "not constitute
  human subjects research." No IRB protocol number is reported …". It now
  starts inside the quotation. `\.(?!\s)` takes a `.` followed by a closing
  quote, as `rsn.source-ranking`'s window has since v4. The phrase count does
  not move, but the span is wrong (filed as a follow-up).

No pinned match was cut short by "St." (#3887's question): the abbreviation
cases in the pinned records are this "e.g." and the in-token dots above.

By label (`rsn.source-ranking` matches; record_self_narration phrases;
bundle_wide_absence phrases), the 23 that move:

| label | `rsn.source-ranking` matches | record_self_narration phrases | bundle_wide_absence phrases |
|---|---:|---:|---:|
| `claudecode_agent/2026-07-27_claude-opus-5_rep1` | 1 → 0 | 9 → 8 | 11 → 11 |
| `claudecode_agent/2026-07-27_claude-opus-5_rep2` | 1 → 0 | 5 → 4 | 11 → 11 |
| `claudecode_agent/2026-07-28_claude-opus-5-generic_rep1` | 3 → 0 | 12 → 9 | 14 → 14 |
| `claudecode_agent/2026-07-28_claude-opus-5-generic_rep2` | 3 → 0 | 21 → 18 | 16 → 16 |
| `claudecode_agent/2026-07-28_claude-opus-5-generic_rep3` | 3 → 0 | 10 → 7 | 8 → 8 |
| `claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep2` | 0 → 0 | 16 → 16 | 35 → 36 |
| `claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep1` | 3 → 2 | 80 → 79 | 70 → 70 |
| `claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep2` | 1 → 0 | 35 → 34 | 31 → 31 |
| `claudecode_agent/2026-08-07_claude-opus-5-claudecode-generic-v3_rep3` | 1 → 0 | 54 → 53 | 38 → 38 |
| `claudecode_agent/2026-08-11_claude-opus-5-claudecode-generic_rep1` | 1 → 1 | 45 → 44 | 48 → 48 |
| `claudecode_agent/2026-08-20b_claude-opus-5-api-generic-v5_rep1` | 5 → 4 | 42 → 41 | 26 → 26 |
| `claudecode_agent/2026-08-22c_claude-opus-5-api-generic-v5_rep3` | 15 → 15 | 73 → 72 | 21 → 21 |
| `claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep1` | 10 → 7 | 58 → 55 | 22 → 22 |
| `claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep2` | 23 → 18 | 61 → 56 | 22 → 22 |
| `claudecode_agent/2026-08-24_claude-opus-5-claudecode-generic-v5_rep3` | 16 → 15 | 56 → 54 | 16 → 16 |
| `claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1` | 6 → 5 | 25 → 24 | 4 → 4 |
| `claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2` | 15 → 13 | 50 → 48 | 14 → 14 |
| `claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3` | 5 → 5 | 35 → 34 | 15 → 15 |
| `claudecode_agent/2026-09-01_claude-opus-5-api-generic-v7_rep3` | 11 → 10 | 42 → 41 | 29 → 29 |
| `claudecode_agent_merged/2026-07-29_coverage-union` | 2 → 0 | 8 → 6 | 3 → 3 |
| `claudecode_agent_merged/2026-07-29_guarded-union` | 3 → 0 | 16 → 13 | 11 → 11 |
| `claudecode_api/2026-09-04e_claude-opus-5-api-generic-v8_rep1` | 4 → 3 | 15 → 14 | 3 → 3 |
| `claudecode_api/2026-09-04f_claude-opus-5-api-generic-v8_rep2` | 9 → 8 | 27 → 26 | 2 → 2 |

This table is a one-off reading made when v5 was registered, not a
regenerated note. The per-method and per-pattern tables in
`notes/absence_claims_baseline.md` are the recorded instrument.

## Precision

`--sample 50 --seed 2919` under v5 draws `d36dc003…`. v5 changes three
bundle_wide_absence patterns, so that class's population is no longer v4's
and the seeded draw changed for both classes: 8 of the bundle_wide_absence
phrases and 2 of the record_self_narration phrases are in v4's draw. Every
phrase was read in context, to its sentence's end, including those 10, and
judged:

| class | v5 in / borderline / not | v4 |
|---|---|---|
| bundle_wide_absence | 49 / 1 / 0 (Wilson 95% 89.5% to 99.6%) | 50 / 0 / 0 |
| record_self_narration | 50 / 0 / 0 (92.9% to 100%) | 49 / 1 / 0 |

- v4's borderline record_self_narration phrase was a name of the declared
  ranking with no verb, the case v5 removes. Of the 8 phrases in v5's draw
  that `rsn.source-ranking` matches, 2 are names. Each now carries a verb, and
  both were judged construction: "which the input manifest declares a distinct
  dataset; it is represented here only through `related_datasets`", and "Where
  the input manifest ranks one source above the other, the higher-ranked value
  was used".
- The borderline bundle_wide_absence phrase is "the project documentation does
  not describe it as cleaning". It asserts an absence of one named source, not
  of the sources as a whole. `bwa.sources-do-not` admits any one-word
  qualifier before `documentation`, and v5 does not change that pattern.

The verdicts are in `notes/absence_precision_judgements_d36dc003.yaml`, written
down when the sample was checked. One rater, the implementing agent: not an
independent review (#3197's open part).

## Recall

`notes/absence_v3_recall.md` has a new section, "What v5 gives up relative to
v4". It works from the committed #3705 judgements (the 88 v2 matches v3 drops)
and the #3793 kept-match draw (50 of v3's 248), and
`scripts/absence_v3_recall.py --check` stays green.

- Of the 28 dropped rows v4 recovers, v5 gives up 1: dropped #58
  (construction), the #3875 sentence above, whose only verb was the noun
  `use`.
- Of the 50 kept matches drawn, v5 gives up 6:
  - kept #17, #26 and #36 (source): exactly #3874's three;
  - kept #25 (source);
  - kept #34 (referent: "which the declared source ranking treats as the
    current release");
  - kept #38 (construction: "which the input manifest retains").

  Four of the five borderline kept matches go.
- So 3 in-class judged rows are lost (dropped #58, kept #34, kept #38) and 4
  borderline ones. v5 gains dropped #85 (construction), the name v4 absorbed
  into a longer span, which now ends a match of its own.
- Kept #48, the match #3875 was filed from, is still matched in v5. It no
  longer rests on `use`: the same term's sentence carries "the ranking cannot
  settle between them" past a `;`, and `settle` is a listed resolution verb.
  The issue's mechanism is fixed and the match stands on another verb. Its
  verdict (borderline: a source conflict) is unchanged.

v4's precision is not restated for v5 at the kept draw's rate. v5 drops matches
by what their sentences say, so the v3 matches it keeps are not a random subset
of those the kept draw was made of. v5's precision is its own draw, above.

`scripts/absence_v3_recall.py`'s `_sentence` still ends a sentence at the `.`
of "St." (#3887 named it). That is deliberate: it is the sentence the #3705
judgements were read to, and each judgement's computed `flagged` field must
equal what the script computes, so changing it would invalidate the committed
judgements rather than measure v5.

## What consumes it

- `d4d review absence-lint` loads the newest registered version, so its output
  now names v5. It is read-only and never gating.
- `scripts/absence_claims_baseline.py` counts under `LEXICON_VERSION = 5`.
- `scripts/absence_v3_recall.py` measures v3 against v2. It reports v4's
  recoveries and now v5's losses relative to v4, and its judgement files are
  unchanged.
- Nothing else imports `absence_lint` or the `lexicons/` registry. That was
  checked with `grep -r` over the whole worktree outside `data/`, and over the
  primary checkout's `notes/matched_cborg_2026-09-13/`, gitignored files
  included. audit28 runs from its own frozen copy, and the only repository
  files its registration checks are `api_runner.py`, `evidence_assertions.py`
  and, from protocol 5, `source_review.py`
  (`audit_controls/registration.py` `VERSIONED_SCIENTIFIC_FILES`); v5 touches
  none of them.
