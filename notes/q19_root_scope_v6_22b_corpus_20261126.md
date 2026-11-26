# Cumulative Q19 corpus extension for the 2026-11-22b root-scope v6 series

Purpose: record the manual sentence review and cumulative measurements for PR 6396, 2026-11-26. The [first-series note](q19_root_scope_v6_corpus_20261126.md), evaluations, and linter remain unchanged. The same [measurement helper](../scripts/adhoc/measure_q19_root_scope_v6_corpus_20261126.py) compares this corpus with Part 1 head `1cdbf0ff309e4430f8761f8ef16e973712a99228`.

The measured head was `79ab95ef7c1bd0bfa6d5b53989f507200579e550`. There are 28 added JSON documents, 15 rubric10 and 13 rubric20, and no changed baseline documents. The helper output is `.temp/ci-data-repair-20261126/part2/q19-measurement.json`, SHA256 `974dace5b6af0e18a0142c4da098343b1af458863e5b4e3f8c53420eda2e37b6`. It records every new sentence's file, JSON pointer, and containing context. Actual process niceness was 10. The unchanged helper SHA256 is `7885270d3ee9f2a148ddac4eebd2bdd12ca50526f9e57b26068015b01bb459c1`; the unchanged linter SHA256 is `74c7dbcdab98bd77ae486b9818af8fb09f81e4628987e2e4a81084b552998744`.

Reproduce from the checkout, with `SCORING_PY` naming the repository Python environment:

```sh
env PYTHONDONTWRITEBYTECODE=1 nice -n 10 "${SCORING_PY:?set the repository Python path}" -B scripts/adhoc/measure_q19_root_scope_v6_corpus_20261126.py --baseline 1cdbf0ff3
```

## Mechanical counts and scope

All 13 new rubric20 parent Q19 items parse through the unchanged reader. As before, Q19 lint reads parent `score_label`, `quality_note`, and optional `semantic_analysis`, while the separate recursive outside-field census also reads nested unit evidence and JSON pointer strings. The following are mechanical measurements, not validated charges against the ratings.

| Measurement | Part 1 | Cumulative |
| --- | ---: | ---: |
| Parsed JSON documents | 675 | 703 |
| Rubric20 ratings | 163 | 176 |
| Empty-slot reasons emitted by the linter | 89 | 90 |
| Reasons whose emptiness is in a neighboring clause | 11 | 11 |
| Q19 sentences naming a slot | 123 | 124 |
| Q19 slot sentences without an emptiness marker | 2 | 2 |
| Distinct outside-field slot sentences | 1159 | 1184 |
| Outside sentences with an emptiness marker | 875 | 898 |
| Unmarked recommendations | 127 | 128 |
| Other unmarked sentences | 157 | 158 |

No old outside sentence disappears. The original blind-reading packet and all historical and first-series reading dictionaries remain unchanged. The second-series placement and request are pinned in new `_UNRECOGNISED_PLACEMENTS_2026_11_26_22B` and `_RECOMMENDATIONS_READ_2026_11_26_22B` lists. Non-recommendation classifications become 49, including 19 placements, 32 absence-vocabulary misses, and the unchanged four bare names; 109 credit sentences remain. Recommendation classes become one named absence, 63 placements, 18 criticisms, and 46 requests. This extends the established ordered classification without broadening the vocabulary or excluding new evidence.

## The new Q19 reason is a false positive on a disclaimer

Rubric20 VOICE rep3's Q19 `semantic_analysis` says: “The deduction concerns incomplete derivation relationships, not the absence of a particular graph serialization or the was_derived_from field alone.” The linter emits an `empty_slot` reason from the clause “not the absence of a particular graph serialization or the was_derived_from field alone.” The sentence expressly contrasts the actual deduction with a representation-only or single-field absence rationale. It is therefore a false positive, not evidence that the evaluator deducted for that field's absence.

The existing `_disclaims` handling does not reject this trailing contrast after the deduction cue; the downstream reason matcher treats `not` as an emptiness marker. This task records the unchanged output of `lint_q19` as the 90th mechanical reason and leaves correction of the reader to [issue 6423](https://github.com/bridge2ai/data-sheets-schema/issues/6423). Its own clause contains the marker, so no new neighboring-clause exemption is needed.

## Manual review of all 25 added outside sentences

IDs refer to this Part 2 measurement, independently of the first note's IDs. Sources below use R10 or R20 and project/replicate. Each filename is `<PROJECT>_2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep<N>_evaluation.json`, beneath `data/evaluation_llm/rubric<R>_semantic/label_aware/2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6/`. Q1 evidence means `/categories/0/questions/0/evidence`; the JSON receipt records complete locations and every repeated occurrence.

| ID | Exact sentence | Source and classification reason |
| --- | --- | --- |
| S001 | A qualitative risk assessment and concrete mitigations are supplied, even though reidentification_risk is not populated as a dedicated slot. | R10 AI_READI rep1, E4.3 quality note. Mechanically marked by `not`; credits the risk assessment and mitigations while acknowledging an unpopulated slot. Marker presence does not establish a deduction. |
| S002 | Absence of parent_datasets does not establish that a parent relationship exists. | R20 VOICE_PEDIATRIC rep1, Q1 semantic analysis. Marked by `not`; explicitly rejects inferring an actual parent from missing metadata. |
| S003 | DOI, resources, parent_datasets, variables, and confidentiality classification are absent. | R20 CHORUS rep2, Q1 evidence. Marked by `absent`, governing the whole list. |
| S004 | Derivation and raw-audio information are acknowledged in other fields; the specified provenance fields are absent. | R10 VOICE_PEDIATRIC rep1, E6.5 unit evidence. Marked by `absent`; acknowledges alternate content while expressly naming absent fields. |
| S005 | Explicit platform access instructions, release changes, acquisition methods, research objectives, raw-source derivation, and hosting information were credited in their actual populated fields rather than requiring duplicate dedicated fields. | R10 VOICE_PEDIATRIC rep3, semantic insight 2. **Placement**, under ordered step 2: actual populated holders are contrasted with duplicate dedicated fields. Favorable credit does not override this step or require that the sentence criticize those holders. Its own E2.3/E6.3/E6.5 and acquisition accounts confirm content in alternate fields. No emptiness marker appears. |
| S006 | Four of fourteen rubric-listed root fields are absent: resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level. | R20 AI_READI rep2, issue 0 description. Marked by `absent`; the count is followed by the specific missing fields. |
| S007 | Four of the fourteen assessed root fields are absent: doi, parent_datasets, variables and confidentiality classification. | R20 CM4AI rep2, issue 0 description. Marked by `absent`; explicit enumeration rather than a count-only statement. |
| S008 | Four of the fourteen specified root fields are unpopulated: resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level. | R20 VOICE rep3, issue 0 description. Marked by `unpopulated`, governing the following list. |
| S009 | Neither parent_datasets nor related_datasets is present at the root. | R10 CM4AI rep3, E1.5 evidence. Marked by `neither`/`nor`; own-item note distinguishes nested containment from typed relationships. |
| S010 | Neither parent_datasets nor related_datasets is present. | R10 CM4AI rep1, E1.5 evidence. Marked by `neither`/`nor`; own-item note distinguishes release inventory from dataset links. |
| S011 | Neither parent_datasets nor related_datasets is supplied; subsets describes five modalities. | R10 CHORUS rep2, E1.5 evidence. Marked by `neither`/`nor`; the separate subset description does not negate the explicit relationship absence. |
| S012 | Provide complete textual or structured derivation chains for each modality, including raw-source/device associations, transformation activities, responsible agents and resulting release entities. | R20 AI_READI rep3, issue 7 recommendation. **Request**: no named absence or existing alternate holder is stated. The sentence names generic desired relationships, not a particular populated slot, entry, or quoted value, so ordered step 3a fails even though the issue and Q19 identify incomplete lineage (3b). It does not name the existing FDA/SDT caveat. |
| S013 | Root doi, instances, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent. | R20 CM4AI rep1, Q1 evidence. Marked by `absent`; the rating keeps release-specific identifiers at their actual paths. |
| S014 | Root resources, parent_datasets and regulatory_restrictions.confidentiality_level are absent. | R20 VOICE rep1 and VOICE_PEDIATRIC rep3, Q1 evidence. Marked by `absent`; both distinguish actual file-resource locations from the root fields. |
| S015 | Root resources, parent_datasets, and confidentiality classification are absent. | R20 VOICE_PEDIATRIC rep1, issue 0 description. Marked by `absent`, covering the named fields. |
| S016 | Root resources, parent_datasets, and regulatory_restrictions.confidentiality_level are absent: 11/14, approximately 78.6%. | R20 VOICE_PEDIATRIC rep1, Q1 evidence. Marked by `absent`; the coverage percentage accompanies named absences. |
| S017 | The designated provenance fields do not document release derivation. | R10 CHORUS rep3, E6.5 quality note. Marked by `not`; the own-item evidence separates absent provenance fields and a contact note from release derivation. |
| S018 | The substantive negative declaration and release boundary provide meaningful sensitivity documentation despite absent dedicated fields. | R10 AI_READI rep3, E9.4 quality note. Marked by `absent`, while crediting substantive disclosure in source caveats. This is not a statement of deduction for slot absence. |
| S019 | Their actual locations are preserved; absence of parent_datasets is not treated as proof that the dataset has an undocumented parent. | R20 VOICE rep1, Q1 semantic analysis. Marked by `not`; rejects inferring a parent relationship from missing metadata. |
| S020 | Variable metadata and confidentiality classification are missing; root doi and parent_datasets are also absent. | R20 CM4AI rep3, issue 0 description. Marked by `missing` and `absent`; both clauses assert named absences. |
| S021 | was_derived_from and raw_data_sources are absent. | R10 CM4AI rep1, E6.5 evidence. Marked by `absent`; nearby contact and schedule descriptions do not change this explicit statement. |
| S022 | was_derived_from and raw_data_sources are absent; updates.update_details supplies only a maintenance schedule. | R10 CM4AI rep3, E6.5 evidence. Marked by `absent`; the schedule clause describes the populated alternative's limitation. |
| S023 | was_derived_from, raw_data_sources and updates are absent. | R10 CHORUS rep1, E6.5 evidence. Marked by `absent`; its own context distinguishes a contact and general source categories from provenance fields. |
| S024 | was_derived_from, raw_data_sources, and updates are absent. | R10 CHORUS rep3, E6.5 evidence. Marked by `absent`; the next contact-note sentence is distinct. |
| S025 | was_derived_from, updates, notes and raw_data_sources are absent. | R10 VOICE_PEDIATRIC rep1, E6.5 evidence. Marked by `absent`; the next sentence acknowledges transformations and raw audio in other fields. |

An independent second agent reviewed the added texts and own-item contexts and agreed with S005's placement and S012's request classifications, specifically checking the ordered rule's precedence and the requirement for a named populated value. This dated review does not alter or expand the historical blind-reading packet.
