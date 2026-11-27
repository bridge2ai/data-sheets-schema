# Q19 corpus extension for the first root-scope v6 series

Purpose: record the manual sentence review and exact corpus measurements supporting PR 6372's test update, 2026-11-26. No evaluation or linter bytes are changed by this work.

The [measurement helper](../scripts/adhoc/measure_q19_root_scope_v6_corpus_20261126.py) compares the tracked JSON corpus with `396f1114e827b39f10928e856250d5851bad59c9`. The measured checkout head was `fcacd9a28f65e3caf7102145c0507f18e62ab4a7`; it adds 30 documents and changes none of the baseline documents. The saved JSON is `.temp/ci-data-repair-20261126/part1/q19-measurement.json`, SHA256 `084696fb0cebcdbed3e0ea5ff8cd275699f10c784857d6407ffd0a8bfcb9ed0c`. It records every new sentence's file, JSON pointer, and containing-item context. The helper SHA256 is `7885270d3ee9f2a148ddac4eebd2bdd12ca50526f9e57b26068015b01bb459c1`; actual process niceness was 10.

Reproduce from the checkout, with `SCORING_PY` naming the repository Python environment:

```sh
env PYTHONDONTWRITEBYTECODE=1 nice -n 10 "${SCORING_PY:?set the repository Python path}" -B scripts/adhoc/measure_q19_root_scope_v6_corpus_20261126.py --baseline 396f1114e
```

## Scope and measurements

The historical linter reads the parent Q19 item's `score_label`, `quality_note`, and optional `semantic_analysis`. It does not recursively lint `unit_scores`. The v6 schema retains these parent fields, and all 15 new rubric20 evaluations parse through the existing reader. The separate outside-field measurement recursively collects every string in the committed evaluations; it therefore includes nested unit evidence and JSON pointer values. This distinction is unchanged. The linter SHA256 remains `74c7dbcdab98bd77ae486b9818af8fb09f81e4628987e2e4a81084b552998744`.

| Measurement | Baseline | Extended corpus |
| --- | ---: | ---: |
| Parsed JSON documents | 645 | 675 |
| Rubric20 ratings | 148 | 163 |
| Empty-slot reasons | 89 | 89 |
| Reasons whose emptiness is in a neighboring clause | 11 | 11 |
| Q19 sentences naming a slot | 122 | 123 |
| Q19 slot sentences without an emptiness marker | 2 | 2 |
| Distinct outside-field slot sentences | 1131 | 1159 |
| Outside sentences with an emptiness marker | 849 | 875 |
| Unmarked recommendations | 127 | 127 |
| Other unmarked sentences | 155 | 157 |

No old outside sentence disappears. No recommendation is added: the 122-entry blind-reading packet and the separate five-entry November 22 extension remain unchanged. Their classes remain one named absence, 63 placements, 18 criticisms, and 45 requests. The only new unmarked strings are two bare names, recorded separately in `_HAND_READ_NOT_CREDIT_2026_11_26`; the original hand-read dictionaries are not rewritten. Classified non-recommendations rise from 46 to 48, while 31 absence misses and 109 credit sentences remain unchanged.

The one added parent Q19 slot sentence, from rubric20 VOICE rep2 `semantic_analysis`, is: “A formal PROV-O serialization or a populated was_derived_from field is not required when the lineage is supplied in prose.” Its `not` matches the vocabulary, but it disclaims a representation requirement; that Q19 has full marks. It adds no empty-slot reason. Marker presence is a mechanical census, not a claim that every sentence describes a deduction.

## Manual sentence review of all 28 new outside sentences

The IDs below are those in the saved measurement. Sources use `R10` or `R20` for the rubric and the project/replicate. Each filename is `<PROJECT>_2026-11-25c_claude-fable-5-2-claudecode-generic-v9_rep<N>_evaluation.json`, under `data/evaluation_llm/rubric<R>_semantic/label_aware/2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6/`. `Q1 evidence` means `/categories/0/questions/0/evidence`; `Q1 unit` adds `/unit_scores/0/evidence` instead. The saved JSON records every occurrence where a sentence repeats.

The established ordered reading is retained: first an absence named as a noun/state, then content located elsewhere, then criticism of a populated value supported by its own rating, otherwise a request for recommendation sentences. A bare field identifier makes none of those assertions. All 26 mechanically marked sentences were also read; none is an added unmarked recommendation requiring a new recommendation pin.

| ID | Exact sentence | Source and classification reason |
| --- | --- | --- |
| S001 | `/parent_datasets` | 42 occurrences in nested `absent` paths and issue `fields_involved`. **Bare name**: the measured string is only a JSON pointer. Its container supplies structural meaning, which the sentence projection does not concatenate into the string. |
| S002 | `/was_derived_from` | 20 occurrences in nested `absent` paths and issue `fields_involved`. **Bare name**, for the same reason. Neither pointer is prose credit, an imperative, or an assertion of absence. |
| S003 | 12 of 14 rubric-listed root fields are populated; root resources and parent_datasets are absent. | R20 VOICE rep3, Q1 unit. Marked by `absent`; explicitly names the missing root fields alongside a count. |
| S004 | 12/14 rubric fields are populated; root resources and parent_datasets are absent. | R20 VOICE_PEDIATRIC rep1, Q1 unit. Marked by `absent`; the numerical coverage does not replace the explicit absence clause. |
| S005 | DOI, resources, parent_datasets, variables and confidentiality classification are absent. | R20 CHORUS rep2, Q1 evidence. Marked by `absent`, governing every named item. |
| S006 | DOI, resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent. | R20 CHORUS rep3, Q1 evidence. Marked by `absent`, governing the list. |
| S007 | Four of fourteen rubric-listed root fields are absent: doi, parent_datasets, variables and confidentiality classification. | R20 CM4AI rep3, issue 0 description. Marked by `absent`; the following list names the counted absent fields. |
| S008 | Four of the fourteen specified root fields are absent: doi, parent_datasets, variables, and confidentiality classification. | R20 CM4AI rep1, issue 0 description. Marked by `absent`; explicit absence rather than a count-only statement. |
| S009 | Four of the fourteen specified root fields are absent: resources, parent_datasets, variables, and regulatory_restrictions.confidentiality_level. | R20 AI_READI rep2, issue 0 description. Marked by `absent`; each missing field is enumerated. |
| S010 | Neither parent_datasets nor related_datasets is provided. | R10 AI_READI rep1, E1.5 evidence. Marked by `neither`/`nor`; the own-item note distinguishes participant relationships and release-history prose from dataset links. |
| S011 | Neither parent_datasets nor related_datasets is supplied. | R10 CHORUS reps1–3, E1.5 evidence. Marked by `neither`/`nor`; the notes identify consortium/software links as insufficient dataset relationships. |
| S012 | No parent_datasets or related_datasets relationships are supplied. | R10 CM4AI rep2, E1.5 evidence. Marked by `No`; the own-item note distinguishes file inventory and release history from typed relationships. |
| S013 | Platform access, repository identity, release changes, and raw-source derivation are documented in meaningful alternative fields; missing dedicated slots alone did not cause deductions. | R10 VOICE rep3, semantic insight 6. Mechanically marked by `missing`/`not`, but **credits alternate evidence and explicitly disclaims deductions for missing slots alone**. It is not counted as a new charged absence. |
| S014 | Release changes, hosting, and quality issues are supported by substantive evidence at their actual record locations even where dedicated fields are absent. | R10 VOICE_PEDIATRIC rep1, semantic insight 6. Marked by `absent`, while **crediting substantive evidence at alternate locations**. Marker presence does not imply a deduction. |
| S015 | Release resources and subsets are present, but parent_datasets and related_datasets are absent. | R10 CM4AI rep3, E1.5 evidence. Marked by `absent`; credit for resources/subsets is distinguished from the missing relationships. |
| S016 | Root doi, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent. | R20 CM4AI rep3, Q1 evidence. Marked by `absent`; own-item note keeps release DOIs at their component paths. |
| S017 | Root doi, parent_datasets, variables, and regulatory_restrictions.confidentiality_level are absent. | R20 CM4AI rep1, Q1 evidence. Marked by `absent`; the own-item analysis distinguishes component identifiers and the root field. |
| S018 | Root resources and parent_datasets are absent. | R20 VOICE rep3 and VOICE_PEDIATRIC rep1, Q1 evidence. Marked by `absent`; both own-item accounts distinguish nested file resources from root fields. |
| S019 | Root resources and parent_datasets are absent: 85.7% coverage. | R20 VOICE rep2, Q1 evidence. Marked by `absent`; the percentage accompanies the named missing fields. |
| S020 | Root resources and parent_datasets are absent; regulatory_restrictions.confidentiality_level is restricted. | R20 VOICE rep1, Q1 evidence. Marked by `absent`; the separate confidentiality clause reports a populated value. |
| S021 | Root resources and parent_datasets are absent; resources nested within file_collections do not populate the root resources field. | R20 VOICE_PEDIATRIC rep2, Q1 evidence. Marked by `absent`/`not`; explicitly distinguishes nested content from root fields. |
| S022 | Root resources, parent_datasets, and regulatory_restrictions.confidentiality_level are absent. | R20 VOICE_PEDIATRIC rep3, Q1 evidence. Marked by `absent`; the own-item analysis does not infer that a parent dataset actually exists. |
| S023 | Root resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent. | R20 AI_READI rep3 and CM4AI rep2, Q1 evidence. Marked by `absent`; both ratings retain the actual locations of nested resources. |
| S024 | Root resources, parent_datasets, variables, and regulatory_restrictions.confidentiality_level are absent. | R20 AI_READI reps1–2, Q1 evidence. Marked by `absent`; notes distinguish narrative or nested information from the specifically enumerated fields. |
| S025 | The record identifies earlier releases but supplies no parent_datasets or related_datasets entries with typed dataset relationships. | R10 AI_READI rep1, issue 0 description. Marked by `no`; prior-release credit does not negate the expressly absent typed entries. |
| S026 | The root contains 12 of 14 rubric-listed fields; resources and parent_datasets are absent. | R20 VOICE rep1, Q1 unit. Marked by `absent`; explicit missing fields accompany coverage. |
| S027 | Twelve of fourteen rubric-listed fields are populated; root hierarchy fields resources and parent_datasets are absent. | R20 VOICE rep2, Q1 unit. Marked by `absent`; the two hierarchy fields are named. |
| S028 | was_derived_from, raw_data_sources, and notes are absent; updates.update_details contains only a schedule. | R10 CM4AI rep3, E6.5 evidence. Marked by `absent`; the neighboring schedule statement describes the populated alternative's limitation. |

An independent second agent read the 28 texts and representative own-item contexts and agreed with the two new bare-name classifications, while specifically distinguishing the credit/disclaimer sentences S013 and S014. This is not an expansion of the historical blind-reading packet.
