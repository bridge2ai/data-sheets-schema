# Schema history and meeting-era publication review — 2026-11-10

The schema has expanded modestly in scientific scope since April, while its accepted representations have changed substantially. Current full/core schema 3.2.0 adds governance, explicit data-standard terms, source caveats and stronger exchange support. It preserves the existing classes and top-level fields, but old narrative arrays, person references and some identifiers cannot be assumed to validate unchanged.

The meeting-era hosted D4Ds need a different historical label from the April generation. **The public Synapse snapshot created April 24 Pacific contains December 2025 v4 HTML, byte-for-byte. It does not contain the April 10 regenerated YAML or the poster's new core records.** That distinction matters when interpreting apparent improvements since the meeting.

This report reviews frozen remote main `7233f193ad102a8488b31ec7333662c8fefaa996`. The primary local checkout is dirty/diverged and was not used as the current schema. No schemas, historical records or publication rows were changed. The exact meeting date and the browser content seen by a particular attendee have not been established.

## Three different historical objects

| Object | Verified identity | What it establishes |
|---|---|---|
| April regenerated full/core records | [`9912ac2379b1a5b747c6b3941a32a18968dbd07d`](https://github.com/bridge2ai/data-sheets-schema/commit/9912ac2379b1a5b747c6b3941a32a18968dbd07d), April 10, 2026 | Regeneration of four Grand Challenge full records and four separate core records. It does not prove these records replaced portal content. |
| Poster development and final April schema | Poster assets begin April 24 at [`b0714477d884c6a868b5844795107a2965f7ff98`](https://github.com/bridge2ai/data-sheets-schema/commit/b0714477d884c6a868b5844795107a2965f7ff98); schema checkpoint [`e141852f532e6a0cea47992ffe9afc0f20a7c6a5`](https://github.com/bridge2ai/data-sheets-schema/commit/e141852f532e6a0cea47992ffe9afc0f20a7c6a5), April 28 | Core thumbnails, exchange diagrams, mapping refinements and renderer guidance developed for the April face-to-face poster. April 28 is a reproducible schema checkpoint, not proof of the precise poster file shown. |
| Hosted table during the late-April/May window | Public `D4D_content`, `syn68885644`, snapshot 13; timestamp `2026-04-25T03:51:39.846Z` | Four HTML rows exactly match the v4 publication files already committed December 10, 2025 at [`91881c4fb99540fff02fa53fbbd8b052da5b54d4`](https://github.com/bridge2ai/data-sheets-schema/commit/91881c4fb99540fff02fa53fbbd8b052da5b54d4). This is direct table evidence, not an inference from a configured filename. |

The April 28 uploader explicitly selects `D4D_-_{project}_v4_human_readable.html` from `src/html/output`, with `datasheet-common.css`: [historical uploader](https://github.com/bridge2ai/data-sheets-schema/blob/e141852f532e6a0cea47992ffe9afc0f20a7c6a5/utils/d4d_to_synapse_table.py). Its workflow is triggered by changes under that publication directory; generation elsewhere does not automatically replace those selected files. Git history shows the four v4 HTML files unchanged between their December introduction and April 28.

The anonymous [Synapse snapshot history](https://repo-prod.prod.sagebase.org/repo/v1/entity/syn68885644/version?limit=100&offset=0) records snapshot 12 on April 23, snapshot 13 on April 25 UTC, then snapshots 14 and 15 on October 17. The captured response has no intervening version. The snapshot-13 query returned five rows, comprising four HTML documents and one stylesheet. Exact source/table comparisons are in [history_hosted_snapshot13.json](history_hosted_snapshot13.json), including the captured response with email-address strings redacted and SHA-256 digests of the original bytes:

| Project | HTML bytes | Source and snapshot SHA-256 |
|---|---:|---|
| AI-READI | 41,081 | `f83df0e1b7c6fe78b96611a106881e728010a8d609933bdae52cbdbf650bfb07` |
| CHORUS | 38,363 | `afbe2112b329d756049b9fe28584142bac5b168f218ec5a01dbcf76cda76a083` |
| CM4AI | 45,106 | `d2c7fd89b728a02617089f3de88997193e7d911c22a07755921549e38d6fba50` |
| VOICE | 60,021 | `ff82d0ee188561ed9d06dc04df547faaa45b531d620eed10bcf1651b2b970768` |

The stylesheet differs only by collapsing consecutive newlines: source 9,893 bytes, snapshot 9,842 bytes. This matches the later documented CSV/S3 transport behavior. The four HTML comparisons themselves are exact, without normalization. These findings pin the table snapshot; they do not establish which materialized-view revision or cached browser rendering was visible at each moment. A snapshot list also cannot rule out unsnapshotted intermediate edits.

Current publication documentation describes a later, distinct cohort: selected API v8 records with September 2026 run labels and historical schema 2.0.0, rendered October 16. Their exact source and output hashes are in [v8-publication.json](../../src/html/output/v8-publication.json). The manifest records selection on September 8; the actual generation timestamps range from September 5 to September 7. Rendering these records does not migrate them to schema 3.2.0. Neither current HTML nor a schema version alone should be used as a substitute for the meeting-era snapshot.

## Measured schema changes

The helper [schema_history_review_20261110.py](../../scripts/adhoc/schema_history_review_20261110.py) reads each frozen Git tree, extracts disposable schema copies and resolves imports/inheritance with the same LinkML Runtime 1.9.4 and PyYAML 6.0.2. It does not reproduce the historical compiler environment. Source and generated schema files are hashed separately; generated merged-file line counts are not treated as new scientific fields.

| Measure | April full | Current full | April core | Current core |
|---|---:|---:|---:|---:|
| Root properties after inheritance | 94 | 98 | 79 | 84 |
| Classes in imported schema closure | 78 | 79 | 76 | 77 |
| Enums in imported schema closure | 17 | 18 | 15 | 16 |
| Permissible enum values | 210 | 242 | 191 | 223 |
| Global slot declarations | 33 | 34 | 31 | 32 |
| Class/property pairs after inheritance | 764 | 946 | 604 | 781 |
| Declared entry-point schema version | unset | 3.2.0 | unset | 3.2.0 |

Both April snapshots have identical counts. A root property means one induced property on `Dataset` or `CoreDataset`. Imported classes include supporting definitions, not just objects reached by a particular record. Global slots exclude class-local attributes. Class/property pairs count an inherited property once for every receiving class; their increase is largely inherited `notes` and `source_caveats`, not hundreds of independent concepts.

There is one added class, `DataGovernance`, and no removed classes or root properties in either import closure. Full adds `conforms_to_standard`, `data_governance`, `notes` and `source_caveats`; core adds those four plus `related_datasets`. The new `DataStandardEnum` has ten values; the relationship vocabulary adds 22 values. Full detail is in [history_comparison.json](history_comparison.json) and the three `history_*2026*.json` inventories.

The poster's Fig. 1 at `b7f14709b:data/poster_assets/figures/fig1_semantic_exchange.mmd` displays “10 modules / 76 classes / 272 slots / 15 enums” and “161 slot_uri (41.5% URI coverage).” Those numbers use different or undocumented denominators from the table above; for example, 76/15 matches the April core import closure rather than full. They should not be used to infer full-schema growth without recreating their counting method. The source prose still mentioning “284 attributes” likewise is not a current count of root properties.

No existing induced full-schema `slot_uri` is replaced between April 28 and current in this inventory. Between April 10 and April 28, `FileCollection.total_bytes` changes from `dcat:byteSize` to `d4d:total_bytes`, and `FundingMechanism.grantor` from `schema:funder` to `d4d:grantor`. This does not imply unchanged semantics overall: new properties, prefix corrections, mapping annotations, object shapes and cardinalities also affect exchange.

## Changes that affect users and downstream tooling

| Change since the April schema | Consequence |
|---|---|
| **63 string attributes and one enum attribute lose `multivalued: true`.** | Narrative fields such as preprocessing details, sampling strategies, consent, privacy, retention and update details now take scalar text. The enum is `FileCollection.collection_type`. These 64 declarations all belong to the full schema's imported classes; this count excludes evaluation-summary changes and does not multiply inherited occurrences. Old arrays are not generally backward compatible. |
| **Organization and grant identifiers become recommended rather than required.** | `Organization` and `Grant` no longer inherit the required identifier from `NamedThing`; `Grantor` inherits the relaxed organization definition. This reduces pressure to invent identifiers absent from sources. `FundingMechanism.grantor` and `EthicalReview.reviewing_organization` become strings. |
| **Person references become inline objects.** | Principal-investigator and contact slots accept `Person` objects, with the class's identifying field, rather than bare name/reference strings. Old strings cannot be assumed to migrate automatically. |
| **Governance becomes a first-class object in full and core.** | Committee, access-review process, contact, review timing, appeals, stewardship roles and accountable organization have explicit homes. The old regulatory committee-contact field remains deprecated, rather than being removed. |
| **Data standards are distinguished from serialization and metadata conformance.** | `conforms_to_standard` records controlled terms alongside source wording in `conforms_to`; `conforms_to_schema` and `conforms_to_class` describe the datasheet record. Core distributions retain data-standard information. DICOM/OMOP/BIDS are not collapsed into CSV/JSON-style serialization choices. |
| **File and distribution representation becomes more practical.** | `DistributionFormat` adds download URL, format, media type and checksum. `FileCollection.resources` changes from the ineffective Dataset-plus-union constraint to explicit `File` items; nested collections are not supported by that property. `DatasetCollection.resources` explicitly carries a list of `Dataset` objects. |
| **Relationships become more expressive.** | DataCite-aligned relationship terms and aliases extend the vocabulary, and core retains typed related datasets separately from contained resources and distributions. |
| **Evidence limits have explicit homes.** | Inherited `notes` retains residual content; `source_caveats` records uncertainty, contradictions and provenance commentary. These are not substitutes for filling fitting structured fields or proving a claim from sources. |
| **Identifiers and vocabulary guidance tighten or broaden in specific places.** | DOI validation requires an anchored bare DOI; resolver URLs are no longer accepted by a substring match. Registry prefixes are corrected; ROR/ORCID/DOI and EDAM namespaces are explicit. `VariableMetadata.unit` broadens from `uriorcurie` to string. MD5 remains for compatibility but is deprecated. |
| **Study-specific examples move out of shared generation schemas.** | Neutral generation schemas and profile-selected vocabulary guidance replace active Grand Challenge examples. Schema 3.1 adds EDAM Data/Format and IANA media-type sources; 3.2 declares identifier forms for substrate/topic terms. Annotation changes can affect generation even when they do not impose JSON Schema constraints. |
| **Data-use permission cardinality is restored in 3.2.0.** | Current `LicenseAndUseTerms.data_use_permission` is multivalued, supporting one primary DUO permission plus modifiers. This agrees with the April list shape; scalar values valid under the intervening 3.0/3.1 schemas need a list migration. The older September count of 65 removed multivalued declarations is therefore not the current comparison. |

The full root explicitly requires `id`. The core root marks `id` as an identifier without an explicit induced `required` flag; compiler semantics must be considered before calling it optional. All other induced root properties have no required flag. Thus preservation or expansion of AI-readiness documentation fields does not itself make schema validation a test of readiness or documentary completeness.

Separate operational schemas were added for generation records and run telemetry, plus digest and release inventories. Those describe execution provenance and versioning rather than additional scientific fields that every dataset record must populate. The evaluation-summary module also changed, but is not imported by the two generation roots. The large diff in generated `*_all.yaml` files should not be represented as proportional growth in scientific complexity.

## Compatibility and chronology

The largest representation changes began with schema 2.0.0 on August 6 (`52a0e1732`, followed by `4d2232560`), then governance and standards in August, anchored DOI validation on August 21 (`9f2339746`), and Person inlining on September 3 (`816b44025`). The 2.0.0 label persisted through multiple structural changes. Schema 3.0.0 on September 16 synchronizes full/core release identities and neutralizes model-facing study examples; 3.1.0 is dated October 29 and 3.2.0 November 8 in [release_history.yaml](../../src/data_sheets_schema/schema/release_history.yaml). Exact hashes therefore remain necessary alongside version labels.

Generation workflow changed separately: April generated core independently, whereas the August 27 change (`1c78625fe`) derives core deterministically from the audited full record. An April/current core comparison must disclose both this workflow change and the schema change.

The September 16 review retained structural validation of the original eight April records against April and then-current definitions. All eight passed both April schemas; four full records and AI-READI core failed the September definitions because of narrative-array shapes. That historical result is available in [the September comparison](../schema_changes_since_april_2026-09-16.md), but **its precise error counts were not rerun or presented as November results here**. Current compatibility risks follow directly from the measured cardinality/range changes. A current migration should produce a separately identified derivative, preserving original bytes, original validation identity and original scores.

The most immediate existing issue in this lane is [#2975](https://github.com/bridge2ai/data-sheets-schema/issues/2975): current `FileCollection.collection_type` is scalar while its description still says a collection can list multiple types. At the reviewed revision this contradiction remains at [D4D_FileCollection.yaml lines 134–140](../../src/data_sheets_schema/schema/D4D_FileCollection.yaml). Decide the intended contract before generation or exchange consumers rely on the prose; reuse the existing issue rather than filing a duplicate.

## Evidence limits and reproduction

Git history supplied tracked poster figures and thumbnails. April 28 deliberately deletes `data/poster_assets` from the repository, with the commit message stating that poster artifacts should remain local. A direct ignored-inclusive `rg --files --no-ignore --hidden data/poster_assets` search of the primary checkout found only June slide/diagram assets; filesystem birth/modification timestamps were June 12–24, not April. Those local files do not establish the April poster freeze. Initial broader candidate searches excluded nested `.local_worktrees` and `.local_drafts` mirrors; no claim of machine-wide absence is made.

One current-schema inventory was run first, its nonempty output checked, then the same path was applied serially to the two historical snapshots. Each finished before the first follow-up poll and within the 30-second bound. The comparison then took about 0.24 seconds. No model calls, full test cohorts or historical-record validation batch ran. The first anonymous snapshot helper attempt failed to recognize a successful asynchronous response because it assumed HTTP 200; it was corrected to recognize the completed query payload, then completed and verified five rows on the next bounded attempt. This was a read-only query, with no authentication or table writes.

From the dedicated review checkout, using the existing repository environment:

```bash
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python scripts/adhoc/schema_history_review_20261110.py --revision 7233f193ad102a8488b31ec7333662c8fefaa996 --label current_2026_11_10
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python scripts/adhoc/schema_history_review_20261110.py --revision 9912ac2379b1a5b747c6b3941a32a18968dbd07d --label generation_2026_04_10
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python scripts/adhoc/schema_history_review_20261110.py --revision e141852f532e6a0cea47992ffe9afc0f20a7c6a5 --label poster_2026_04_28
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python scripts/adhoc/schema_history_review_20261110.py --compare generation_2026_04_10 poster_2026_04_28 current_2026_11_10
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python scripts/adhoc/schema_history_review_20261110.py --capture-hosted
```

The final command reads public Synapse data anonymously and writes the captured evidence locally. All other commands read frozen local Git objects. This report supplies the historical and compatibility part of the review; the companion readiness and semantic-exchange assessments determine whether the represented concepts and actual exports meet their respective external criteria.

Before publication, the five evidence JSON files were processed locally with the helper's `--redact-existing` option. The original files are preserved byte-for-byte in the ignored `.temp/schema-review-raw/` directory. Fifteen email-address occurrences were replaced in the publishable copies: two in the comparison, four in the current inventory, one in the April 10 inventory, four in the hosted snapshot response and four in the April 28 inventory. No schema inventory or network read was repeated for this preparation. Numeric counts, byte lengths, SHA-256 values and equality results were independently checked unchanged; the recorded source and response hashes continue to describe the original bytes. Published response text is therefore not itself a byte-identical copy of the original HTML. Fresh helper runs compute original-byte identities and comparisons first, retain local raw evidence, then redact only the saved publication strings. Comparison mode reads the retained raw inventories so redaction does not hide differences between historical inputs.

Lead validation addendum: the subsequent [Core probe](validation_core.json) confirms that the generated JSON Schema accepts an id-only CoreDataset and rejects an empty object for missing id. The [full probe](validation_full.json) gives the same result for Dataset. These are current shape checks, not historical-corpus or readiness validation. To reproduce comparison in a fresh checkout, run the three inventory commands first; the comparison deliberately uses their locally retained, ignored raw copies, which are not included in the published evidence package.
