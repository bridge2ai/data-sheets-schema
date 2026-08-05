# Six rubric20 questions score identically on every record

**Recommended wording for the manuscript is in the last section.** The rest is
the measurement behind it.

Measured 2026-08-04 over the 25 current `claudecode_agent` records
(`2026-07-31`, generic and generic-v2), scored with the hybrid scorer as
corrected in #319. **These figures are not comparable to any rubric20 number
reported before that date** — six of 88 points were unearnable by any record
until it landed.

## What saturates

Six of twenty questions award the same score to all 25 records:

| | question | score | of |
|---|---|---|---|
| Q2 | Entry Length Adequacy | 5 | 5 |
| Q6 | Dataset Identification Metadata | 1 | 1 |
| Q7 | Funding and Acknowledgements Completeness | 5 | 5 |
| Q9 | Access Requirements and Governance Documentation | **3** | 5 |
| Q12 | Collection Protocol Clarity | 5 | 5 |
| Q16 | Findability (Persistent Links) | 1 | 1 |

**20 of 88 points are awarded unconditionally.** An earlier note in #325 said
"11 points across five questions"; both figures were wrong — it omitted Q9 and
the arithmetic did not add up. The measured figure is six questions and 20
points.

Q9 is the one that differs in kind. The other five saturate *at their maximum*:
every datasheet in the corpus genuinely answers them well. Q9 saturates at 3 of
5 because its top band requires a confidentiality classification and a governance
contact, and no record populates `regulatory_restrictions.confidentiality_level`,
`.hipaa_compliant`, `.other_compliance` or `.governance_committee_contact` —
0 of 25. Until #329 the digest never named those fields, so no run was told they
existed. Whether the next generation fills them is open.

## Why this does not affect comparisons

The saturated questions contribute a constant to every record, so they move the
mean and leave the variance untouched. Removing them changes nothing about how
records rank or how far apart they are:

```
full 88-point score      mean 68.9   sd 11.0413
66-point subscore        mean 48.9   sd 11.0413
```

The standard deviations are identical to four decimal places — not
approximately, but by construction. **Every point of between-record variation
comes from the 14 discriminating questions.**

So the saturated questions are not a confound for any between-method or
between-condition comparison. What they do is inflate the absolute percentage:
68.9/88 is 78.3%, of which 22.7 percentage points are awarded before any
datasheet is read.

## Recommended wording

> Scores are reported against the full 88-point rubric20 instrument. Six of its
> twenty questions (Q2, Q6, Q7, Q9, Q12, Q16) awarded an identical score to all
> 25 records in this corpus, contributing 20 points unconditionally. Because
> these contribute a constant, they do not affect any comparison reported here —
> the standard deviation of the 66-point discriminating subscore is identical to
> that of the full score (11.04 in both cases) — but absolute percentages should
> be read with the 20-point floor in mind. Five of the six saturate at their
> maximum, indicating questions the corpus answers uniformly well; Q9 saturates
> at 3 of 5 because no record populates the governance sub-fields its top band
> requires.

## What not to do

**Do not drop the saturated questions from the instrument.** rubric20 is the
published rubric; a 66-point variant would not be comparable to anything already
scored, including the presence path and the manuscript's own earlier figures, and
the saturation is a property of *this corpus* rather than of the questions. Four
projects is a small sample: a fifth that omits its funders would un-saturate Q7
immediately.

**Do not report the subscore as the headline.** It is a diagnostic, not a
result. Reporting it as the score would silently change the instrument between
this paper and the next.
