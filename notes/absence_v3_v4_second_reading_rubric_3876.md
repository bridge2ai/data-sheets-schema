# Absence lexicon judgements: rubric

Sources, at origin/main c962a6cc8: the headers of
`notes/absence_v3_recall_judgements_241e910e.yaml` and
`notes/absence_v3_precision_source_ranking_judgements_ec97ce4b.yaml`,
`scripts/absence_claims_baseline.py` and `scripts/absence_v3_recall.py`
(`READINGS`), and, for the class definition those files judge against, the
registered lexicon `src/data_sheets_schema/lexicons/absence_self_narration_v4.yaml`
(its class descriptions are v3's and v2's). The wording is theirs. No judged
example is included. The "How to answer" section is the only addition.

## The class judged

Every item is a match of a `record_self_narration` pattern.

    record_self_narration  a statement about how the record itself was built:
                           which slot holds what, what was left empty or
                           omitted, what was merged or kept apart, which
                           source was preferred.

The other class the lexicon defines, named by the `absence` reading below:

    bundle_wide_absence    an absence asserted of the bundle, the sources or
                           the documentation as a whole ("no source states X",
                           "not stated in the bundle") — found by searching,
                           not stated by a passage. An absence a passage
                           states ("the release notes state that no erratum
                           has been issued") is not in this class.

## Verdicts

Verdicts: in_class, borderline, not_in_class.

It measures class membership, not whether a statement should be removed: a
source conflict is legitimate content for `source_caveats`, and one worded
with the ranking vocabulary is still counted in `record_self_narration`, as
borderline.

## Readings

Each phrase is read in its sentence as written (to its full stop, a clause
after `;` included) and the sentences around it, against the
record_self_narration definition. A reading fixes its verdict.

    construction  the sentence says what the record did (preferred, used,
                  recorded, left a slot empty) and the ranking term bears on
                  it                                         -> in_class
    referent      the sentence says which dataset or release this record
                  describes, justified by the ranking        -> in_class
    source        the sentence reports the sources (a conflict, a rank, what a
                  source or the manifest states) and says nothing of what the
                  record did; any resolution is in another sentence
                                                             -> borderline
    absence       an absence asserted across the sources ("no tier-1 source
                  states them"), which bundle_wide_absence describes
                                                             -> not_in_class

The readings were written for matches of `rsn.source-ranking` (a ranking term
applied to a source: tier-N source, higher-ranked, ranks higher, ...).

## How to answer

For every item give a `verdict` (`in_class`, `borderline` or `not_in_class`).
Where the item's `patterns` include `rsn.source-ranking`, also give the
`reading` (`construction`, `referent`, `source` or `absence`) that fixes it.
`shown_to_judge` is the window the drawing script printed, the matched phrase
in `[[ ]]`; `sentence` is the phrase's sentence to its full stop (a `;` does
not end it); `leaf_text` is the whole record field, for the sentences around
it. Judge each item on its own: some items repeat a phrase.
