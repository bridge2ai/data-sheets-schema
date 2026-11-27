# Q19 corpus completion for the 2026-11-22b root-scope v6 series

Purpose: record Part 3's cumulative measurements and manual review for PR 6396, 2026-11-27. The two completion ratings add no new distinct sentence to the measured slot-name corpus. All earlier classification lists, the linter, and the [Part 1](q19_root_scope_v6_corpus_20261126.md) and [Part 2](q19_root_scope_v6_22b_corpus_20261126.md) notes remain unchanged.

The unchanged [measurement helper](../scripts/adhoc/measure_q19_root_scope_v6_corpus_20261126.py) compared baseline `b9a4dc35dadb47232eed161f6a653247d9fa2303` with head `93707dc3230fc7db0678fade30e585fba7988c5c`, at verified process niceness 10. Its output is `.temp/ci-data-repair-20261127/part3/q19-measurement.json`, SHA256 `48512bcc0e8c049d4cf4f3bf852549222e09a53cc6e51ac180721d46173804c2`. The helper SHA256 remains `7885270d3ee9f2a148ddac4eebd2bdd12ca50526f9e57b26068015b01bb459c1`; the linter SHA256 remains `74c7dbcdab98bd77ae486b9818af8fb09f81e4628987e2e4a81084b552998744`.

Reproduce from the checkout, with `SCORING_PY` naming the repository Python environment:

```sh
env PYTHONDONTWRITEBYTECODE=1 nice -n 10 "${SCORING_PY:?set the repository Python path}" -B scripts/adhoc/measure_q19_root_scope_v6_corpus_20261126.py --baseline b9a4dc35dadb47232eed161f6a653247d9fa2303
```

## Files and mechanical measurements

The only added JSON documents are the two files below; no baseline JSON document changed. Both are under `data/evaluation_llm/rubric20_semantic/label_aware/2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6/`.

| File | SHA256 |
| --- | --- |
| `CHORUS_2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1_evaluation.json` | `2cb44f0f61b7c65b4c8b5742ea4502dc33eee94d5d68226025022f0c0f1b20f9` |
| `CHORUS_2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3_evaluation.json` | `0415ca98b46ba89b8bbeb267cff7ec57df4e31b442fc8c9e918ce61433801f5e` |

| Measurement | Part 2 | Completed corpus |
| --- | ---: | ---: |
| Parsed JSON documents | 703 | 705 |
| Rubric20 ratings | 176 | 178 |
| Empty-slot reasons emitted by the linter | 90 | 90 |
| Reasons whose emptiness is in a neighboring clause | 11 | 11 |
| Q19 sentences naming a slot | 124 | 124 |
| Q19 slot sentences without an emptiness marker | 2 | 2 |
| Distinct outside-field slot sentences | 1184 | 1184 |
| Outside sentences with an emptiness marker | 898 | 898 |
| Unmarked recommendations | 128 | 128 |
| Other unmarked sentences | 158 | 158 |

The measurement's added and removed outside-sentence lists, new Q19 slot-sentence list, and new empty-slot-reason list are all empty. This is a deduplicated sentence result, not a claim that the new files contain no slot names. Their repeated occurrences were read explicitly below. The previous 49 classified non-recommendations, 32 vocabulary misses, 109 credits, and recommendation classes (one named absence, 63 placements, 18 criticisms, 46 requests) are unchanged. No artificial extension list is introduced.

These counts describe the existing reader, not validated deductions. The Part 2 disclaimer false positive tracked in [issue 6423](https://github.com/bridge2ai/data-sheets-schema/issues/6423) remains part of the unchanged total of 90.

## Manual review of the two parent Q19 rationales

The parent-field contract is unchanged: `score_label`, `quality_note`, and optional `semantic_analysis`. Nested `unit_scores` evidence and pointer strings participate in the separate recursive outside-field census, not in this parent rationale projection. Both completion ratings parse successfully. Every parent rationale field below was read; neither record contains an `empty_slot` cue in those fields.

| Replicate and field | Exact text | Reading |
| --- | --- | --- |
| rep1 `score_label` | No qualifying version history or complete lineage | Substantive history/lineage deficiency; no empty-slot cue. |
| rep1 `quality_note` | Neither the 3-point version-history anchor nor the 5-point complete-provenance anchor is satisfied. | Addresses the stated score anchors, not absence of a named slot or required representation. |
| rep1 `semantic_analysis` | Source-document attribution is distinct from dataset processing provenance. A proposed split does not identify current split membership, release lineage or entity-activity-agent relationships. | Distinguishes documentation attribution and a proposed split from current lineage; no empty-slot cue. |
| rep3 `score_label` | Insufficient — no version history or established provenance lineage | Substantive history/lineage deficiency; no empty-slot cue. |
| rep3 `quality_note` | A planned split does not establish version history or provenance. General extraction and mapping descriptions do not meet the anchored three-point version-history condition or the complete-lineage condition. | Explains why the supplied process context and plan do not meet the history/lineage anchors. No empty-slot cue. |
| rep3 `semantic_analysis` | The record supplies process context, but does not connect identified source entities through specific activities and responsible agents to a defined dataset release. Documentation-source attribution is distinct from data derivation. | Identifies missing substantive connections rather than a slot or serialization requirement; no empty-slot cue. |

## Manual review of every slot-cue occurrence in the new files

An explicit case-insensitive search using the unchanged `REPRESENTATION_CONCERNS["empty_slot"]` alternatives found the following occurrences. The file line numbers refer to the exact file hashes above. Each matching string was read in its enclosing question or issue; all measured sentences already occur in the Part 2 corpus.

| Measured string | rep1 locations | rep3 locations | Existing classification and reason |
| --- | --- | --- | --- |
| `/parent_datasets` | lines 33 and 980: Q1 and Q19 `unit_scores[0].absent` paths | lines 33 and 940: corresponding absent paths | First-series bare-name pin. The string is only a JSON pointer; its container carries separate structural meaning. |
| `/was_derived_from` | line 977: Q19 absent path | line 937: Q19 absent path | First-series bare-name pin, for the same reason. |
| `parent_datasets` | lines 1184 and 1369: issue `fields_involved` lists | lines 1162 and 1380: corresponding issue lists | Historical bare-name pin. A list label does not itself assert absence, placement, criticism, or credit. |
| `was_derived_from` | line 1368: provenance issue `fields_involved` | line 1379: provenance issue `fields_involved` | Historical bare-name pin, unchanged. |
| DOI, resources, parent_datasets, variables and confidentiality classification are absent. | None | line 14: second sentence of Q1 evidence | The exact marked sentence already recorded as Part 1 S005. `absent` governs the list; no new distinct sentence or neighboring-clause exemption. |

The complete Q1 evidence string at rep3 line 14 begins with a different coverage sentence, but the unchanged sentence splitter separates it from the exact previously recorded slot-name sentence. Broad phrases such as “structured instance counts” and “structured provenance” do not match the reader's more specific empty-slot alternatives and are not silently promoted into new slot cues.
