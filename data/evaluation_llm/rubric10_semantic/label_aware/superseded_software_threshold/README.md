# Superseded under the software-threshold statement (#1059)

One evaluation, kept because it is the outlier that made the threshold worth
stating rather than an error to be hidden.

Across the 24 live rubric10 evaluations of the v7 and v8 arms, 23 already
applied one consistent rule to Element 8's Software and Tools sub-element:
score 1 where the record names its tooling in a slot whose purpose is tooling
(`machine_annotation_tools`, `preprocessing_strategies`, or
`external_resources` pointing at a resolvable repository), and 0 where
software appears only incidentally in a slot about something else, or is
named in prose with no resolvable pointer. The rule was never written down,
so one evaluation went the other way:

- `AI_READI_2026-09-04gapi_rep3` scored 1 where its five siblings scored 0,
  on a record with no tooling slot at all, whose tools (REDCap, a tablet
  application, a quality dashboard) appear only inside collection mechanisms.

**#1059's premise was wrong about the second case it named.** CM4AI
`2026-09-04g_rep1` scored 0 where its two siblings scored 1, and that is
correct: rep2 and rep3 name the Cell Mapping Toolkit with the repository URL
`github.com/idekerlab/cellmaps_pipeline`, while rep1 names it in prose as
"released via GitHub" with no URL, no version and no tooling slot. The
difference is in the records, not in the reading, so nothing about that
evaluation is superseded and it was restored after being briefly moved here.

## Second round: the rule was restated, and CM4AI's six with it (#1079)

The first statement of the threshold listed the slots that qualify. A review
showed it contradicted three CHORUS scores — records whose tooling is named
in `preprocessing_strategies` prose with only an organisation-root link — and
that the point turned on an applicability sentence the fix had not touched.

The rule is now written around the question the sub-element asks: can a reader
tell what produced the distributed data. A name in a processing or tooling
slot is enough; a publisher-level pointer neither earns nor forfeits the
point; and three failure cases are named, the third being a record that
documents a pipeline and then says that pipeline's outputs are not in this
release. That third case is CM4AI's, on all six records, so all six were
rescored. The copies here are what they scored under the previous statement.
