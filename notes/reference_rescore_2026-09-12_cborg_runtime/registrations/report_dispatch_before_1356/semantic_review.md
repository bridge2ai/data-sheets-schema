# Q19 inspection of the CBORG reference measurements

Inspect all 24 accepted rubric20 Q19 objects in this CBORG condition against their own frozen input records, focusing on the frozen rule allowing complete textual provenance or PROV-O. This is not a full semantic re-evaluation or external-source fact check.

**Semantic inspection — Q19:** 9 of 24 original Q19 rationales require adjudication because they add representation or field-placement requirements despite the frozen text-or-graph rule. Their containing recorded totals are qualified. No original score, candidate or rationale is edited and no replacement score is assigned. Unflagged cases are not certified correct; other substantive completeness concerns remain unadjudicated. Do not use small differences in these qualified totals to select generation runs. See the [24-rating inspection](semantic_review.md).

**Execution boundary:** Five accepted ratings precede the validator-status permission extension and 51 follow it. Scoring prompts, definitions and inputs are unchanged, but execution permissions differ. Cohort comparisons and repeat panels spanning this boundary do not isolate permission effects; small differences cannot be attributed solely to generation version or evaluator variability. Repeat panels spanning it: AI_READI, CHORUS. See [the dated registration](validator_status_registration.json).

**Execution deadline:** Seventeen accepted ratings precede the execution deadline increase from 900 to 1800 seconds; 39 follow it. Scoring prompts, definitions, inputs and the $5 CLI cap are unchanged. This execution boundary can affect completion/selection, so cohort and repeat comparisons do not isolate generation-version or evaluator effects. See [the deadline registration](deadline_registration_1351.json).

**Incomplete cost accounting:** 2 retained interrupted evaluator sessions have unknown cost. The known terminal CLI subtotal excludes their unreported usage; total expenditure is unknown. CLI estimates are not reconciled CBORG charges. Measurement/session completion does not imply complete cost accounting.

**Evaluation prose:** Evaluation narratives describe model judgments about the supplied documentation and are not verified facts about the underlying datasets. The CHORUS retry canary overstates missing license information as absence of a governing license and alleges conflation despite an explicit software/data distinction in the input. Keep its original score and prose, and do not repeat those statements as dataset facts. Other narrative claims remain unadjudicated. See [the original statements and interpretation](canary_narrative_qualification.json).

**CM4AI pilot judgments:** The CM4AI retry pilot overlooks the explicit per-deposit scope of release version numbers when reducing Q13 and qualifying Q19. Its containing total and related version-consistency findings require semantic adjudication. Additional narrative claims overstate the impossibility of participant-related documentation for cell-line work, credit donor age for both lines where the cited text supplies only one, and undercount creator entries. Keep all original scores and prose; do not repeat these statements as verified dataset facts or use small differences in the qualified total to select a generation run. No replacement scores are assigned. See [the original statements and input evidence](cm4ai_pilot_narrative_qualification_1355.json).

**Evaluation timing:** Execution times and condition boundaries use launcher receipt started_at/completed_at, with original receipt hashes recorded in results.json. Model-written evaluation_timestamp values remain unchanged and are not independently verified, including values inside the recorded interval. Of 56 accepted ratings, 23 metadata timestamps lie outside their session intervals and 0 cannot be compared as timezone-aware timestamps. An interval mismatch alone does not establish fabrication; approximations and timezone errors can also cause it.

The frozen rule permits complete textual provenance as well as W3C PROV-O graphs. A representation-related objection is flagged for adjudication; this inspection does not assign replacement scores or certify other judgments or external source truth.

## AI_READI_v7_rep1_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

The original 5/5 rationale explicitly accepts text or PROV-O and credits named source entities, format conversions, destination collections and responsible roles. The input identifies REDCap-to-OMOP, native retinal exports-to-DICOM, wearable exports-to-Open mHealth and ECG-to-WFDB processing, with site data managers, site PI approval and the central team supplying agent/authority relationships. The rationale distinguishes these derivation chains from version history and accepts equivalent content outside was_derived_from/parent_datasets. No requirement for a particular graph serialization was found. This inspection does not certify every completeness claim or other rubric judgment.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/AI_READI_v7_rep1_r20_rating1_evaluation.json); SHA256 `2f9de22877fbfe1cc1e785790c9042ba864d0f08aebcff6b395bc33772353cd2`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Full lineage with entity-activity-agent relationships, processing lineage and derivation paths",
  "evidence": "Derivation paths, per modality, from raw_data_sources plus preprocessing_strategies: REDCap export \u2192 one-to-one OMOP CDM table mapping \u2192 CSV in clinical_data; Philips TC30 .xml \u2192 WFDB conversion \u2192 cardiac_ecg; Topcon .fda and Heidelberg FLIO .sdt \u2192 DICOM conversion \u2192 retinal_oct / retinal_octa / retinal_flio, with Optomed, Eidon, Spectralis and Cirrus 'exported directly in DICOM'; Garmin .FIT and Dexcom .csv \u2192 Open mHealth \u2192 wearable directories; LeeLab Anura .csv \u2192 NASA ESDS \u2192 environment. Agents: 'A Data Manager at each data site was responsible for quality control of all data before uploading to FAIRhub'; 'Editing was only done under the guidance and approval of the site principal investigator'; 'Once data were sent from each study site to the central project team, all data were mapped to standardized terminologies'. Version lineage: version_access with three versioned DOIs and dates; related_datasets with typed is_new_version_of relationships; updates describing static re-release rather than in-place update; errata recorded as none. Quality and integrity: missing_data_documentation (patterns, causes, handling), anomalies (six modality-specific entries including FLIO photon-distribution limits and Garmin charging gaps), cleaning_strategies with four named check classes, the OMOP Data Quality Dashboard with 3,500+ checks, splits with per-stratum counts, and raw_sources explaining why raw data are retained but not shared.",
  "quality_note": "The rubric accepts text or PROV-O and asks for entity-activity-agent relationships, processing lineage and derivation paths. All three are present and complete for every one of the nine modalities: each source entity is named with its native format, each transforming activity is named, the destination is named, and the responsible agents and their decision authority are identified. The distinction the rubric draws \u2014 version history alone is 3, full lineage is 5 \u2014 is decided here by the per-modality derivation chains, which go well beyond version history.",
  "semantic_analysis": "was_derived_from and parent_datasets are not populated as named fields, but the information they would carry is present and typed elsewhere (raw_data_sources for source derivation, related_datasets for version ancestry), and this question is scored from record content rather than field presence. Lineage is internally consistent: the source formats named in raw_data_sources match the conversion steps in preprocessing_strategies, which in turn match the conforms_to_standard values on the destination file_collections, so the chain can be traced end to end without contradiction. Integrity is further supported by the arithmetic checks that hold across file counts, byte totals and demographic tables."
}
```

## AI_READI_v7_rep2_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

Q19 awards5 and explicitly accepts text-form lineage under the frozen text-or-graph rule. The input identifies Philips XML to WFDB, Topcon .fda/Heidelberg .sdt to DICOM and Garmin .FIT to Open mHealth, alongside processing steps, site data-manager quality control before FAIRhub upload and site-PI approval of edits. The rationale credits these paths outside was_derived_from and does not deduct for absent machine-actionable PROV relations. This inspection addresses representation bias; it does not independently certify the stronger claim that every activity has a uniquely assigned agent or adjudicate other quality judgments.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/AI_READI_v7_rep2_r20_rating1_evaluation.json); SHA256 `a803649ca0d07c30ea1745f088e27e70ef4f53d5bafbe1f06d8d2589c2e20f44`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Full lineage in text form: entities, activities, agents and derivation paths",
  "evidence": "Entities and derivation paths: raw_data_sources gives eight native sources with formats and their fate - Philips XML 'released as WFDB after conversion', Topcon .fda and Heidelberg .sdt 'Converted to DICOM for the dataset', Garmin .FIT 'Converted to the Open mHealth standard', REDCap exports, central laboratory CSV. Activities: preprocessing_strategies enumerates the mapping, conversion, organization, watermarking and PHI-removal steps; cleaning_strategies enumerates range flagging, credibility and skip-pattern checks, and OMOP DQD analysis. Agents: data_collectors names six roles with responsibilities, site data managers perform 'quality control of all data before uploading to FAIRhub', and edits are made 'only under the guidance and approval of the site principal investigator'. Dataset lineage: related_datasets is_new_version_of doi:10.60775/fairhub.2 and .1; version_access and updates document what each version contains. Quality and completeness: missing_data_documentation (patterns, causes, handling), anomalies (six device- and participant-level failure modes), splits, and raw_sources on the retention and non-release of raw data.",
  "quality_note": "This is lineage rather than a changelog: for every modality one can trace native export to conversion activity to released standard, name the agent responsible at each stage, and see the quality checks applied. The rubric accepts text-form provenance with complete lineage, which this meets.",
  "semantic_analysis": "The provenance is auditable against itself - the conversion targets named in raw_data_sources match the conforms_to_standard values of the corresponding file_collections in every case. Two integrity gaps keep this from being unimprovable rather than from being a 5: there are no file-level checksums or fixity information anywhere in the record, and no was_derived_from or errata slot is populated, so the version lineage and the derivation paths are expressed in prose and in related_datasets rather than as machine-actionable PROV relations. The inaccessibility of version 2.0.0 also breaks the retrievability of one node in that lineage."
}
```

## AI_READI_v7_rep3_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

Q19 awards5 and explicitly states that absent was_derived_from/parent_datasets are a machine-readability issue without reducing the score because textual lineage is permitted. The input names native exports and standards conversions, site/coordinator QC, PI approval of edits, central-team processing and version links; it also distinguishes recruitment-only EHR from released prospectively collected data. The rationale follows the frozen representation rule on these inspected points. No independent certification of every activity-to-agent relationship or other Q19 factual claim is made.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/AI_READI_v7_rep3_r20_rating1_evaluation.json); SHA256 `3839068ada7e6483de6b40fe5a8d5ac028a1de4ee7f187bb363a123fde5e5713`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Full lineage with entity-activity-agent relationships, processing lineage and derivation paths",
  "evidence": "Entities: raw_data_sources enumerates nine origin systems with source_type, native raw_data_format and access_details \u2014 REDCap capture; imaging device exports ('Topcon .fda files from the Maestro2 and Triton and Heidelberg .sdt files from FLIO'); Philips TC30 .xml; Garmin .FIT; Dexcom .csv; LeeLab Anura .csv; MoCA Duo .csv; laboratory results; and EHR used for screening only, with the explicit note that 'the EHR content itself is not the source of the released instance data, which was collected prospectively'. Activities: preprocessing_strategies gives the derivation paths (.fda/.sdt to DICOM, .FIT to Open mHealth, ECG to WFDB, clinical to OMOP CDM, Safe Harbor stripping, CDS reorganization); cleaning_strategies gives the two QC stages. Agents: data_collectors (trained, certified coordinators and site data managers), cleaning_strategies (site data managers, site principal investigators approving every edit, central project team), data_governance.stewardship_roles. Version lineage: version_access with three DOIs and version_details; related_datasets is_new_version_of to doi:10.60775/fairhub.2 and doi:10.60775/fairhub.1. Quality: missing_data_documentation (patterns, causes, handling_strategy); anomalies (seven modality-specific entries); dqd_omop.json supporting 3,500-plus OMOP quality checks. splits fully specified; subsets.is_data_split false on the three access tiers. raw_sources records that raw data are preserved but not shared, with the reason.",
  "quality_note": "Top band. The rubric accepts textual provenance, and what is here is a complete lineage rather than a version history: for every modality a reuser can trace the originating device, its native format, the transformation applied, the standard it lands in, who performed and who authorized the quality control, and which prior release the version descends from. The disclosure that raw data are withheld, with the reason (unmapped terminologies and possible PHI in free text), completes the picture by stating where the traceable chain stops.",
  "semantic_analysis": "Provenance is corroborated by arithmetic rather than asserted: the nine file_collections that the derivation paths terminate in reconcile exactly to the reported file count, and their byte totals reconcile to within the 419,614 bytes the record itself discloses. The empty was_derived_from and parent_datasets slots are a machine-readability gap \u2014 a consumer querying those fields gets nothing even though the lineage exists in related_datasets and raw_data_sources \u2014 and that gap is recorded as a low-severity completeness issue; it does not reduce the score because the question directs scoring from content rather than field presence, and the content is complete. errata is likewise empty with no erratum recorded as issued."
}
```

## AI_READI_v8_rep1_r20_rating1

Recorded Q19: 4/5. Status: `requires_adjudication`.

Q19 records4/5 while explicitly saying the full entity-activity-agent derivation path is recoverable in text and accepted by the rubric. Its stated reason for withholding5 is that was_derived_from, parent_datasets and errata are empty and lineage spans sections rather than being read as a graph. The input supplies device exports and named conversions, central-team mapping/processing, site-manager QC before FAIRhub upload and PI-approved edits. This deduction adds a field-placement/graph-presentation requirement beyond the frozen text-or-graph rule. Flag the original Q19 and its containing total for adjudication; no replacement score is assigned, and the inspection does not certify every asserted relationship.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/AI_READI_v8_rep1_r20_rating1_evaluation.json); SHA256 `2fc9e55cddda9c8814d7ea2d3ad9fffa4e8c7598511e72a746b119b3bedfe24e`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Substantial processing lineage in text, but not expressed through the provenance fields",
  "evidence": "version_access and updates fully populated. raw_data_sources (2): EHR screening source used for recruitment only and not released; device-native exports with formats (.xml, .csv, .fda, .sdt, .FIT, DICOM) and an access statement that raw data are retained for the project duration but not shared because they are unmapped and may contain free-text PHI. preprocessing_strategies describes the transformation chain to DICOM, Open mHealth and OMOP CDM. data_collectors names the agents in sequence: site coordinators, site data managers responsible for QC before upload, and the central project team performing further processing. missing_data_documentation: patterns, causes, handling_strategy. splits with per-set counts. related_datasets: typed is_new_version_of links to v2.0.0 and v1.0.0 and has_part to the mini-subset. conforms_to records RO-Crate 1.2-DRAFT with FAIRscape profile 0.1 and one subcrate per data type. Absent: was_derived_from, parent_datasets, errata.",
  "quality_note": "This clearly exceeds version history alone. A complete derivation path is recoverable \u2014 device-native export, format conversion, terminology mapping, site QC, central processing, FAIRhub release \u2014 with named agents and named activities, which the rubric accepts in textual form. It falls short of 5 because the three fields that would carry derivation (was_derived_from, parent_datasets, errata) are all empty, so the lineage must be reassembled by the reader across four unrelated sections rather than read as a graph.",
  "semantic_analysis": "The entity-activity-agent triad is present in substance: entities are the raw exports and released collections, activities are conversion, mapping, cleaning and QC, and agents are the coordinators, site data managers and central team. The RO-Crate and FAIRscape packaging indicates a machine-readable provenance representation exists in the release, but the record references it as a packaging standard rather than exposing derivation relations. Data integrity is otherwise well supported: quality control is documented at entry and at site level, the OMOP Data Quality Dashboard artifact is shipped, anomalies are enumerated per modality with causes, and the unreconciled file-count and byte-total arithmetic is disclosed rather than smoothed over."
}
```

## AI_READI_v8_rep2_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

Q19 awards5 under the explicitly permitted text-form representation. The input identifies study/device sources, format conversions to DICOM/Open mHealth/WFDB and OMOP mapping, site data-manager QC, PI approval and central-team standardization; typed version links supply release lineage. The rationale cross-checks these textual paths and credits them despite missing parent_datasets/errata rather than imposing a dedicated-field or PROV-O gate. This inspection does not adjudicate source-level EHR assertions, every claimed correspondence or other completeness judgments.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/AI_READI_v8_rep2_r20_rating1_evaluation.json); SHA256 `b72eba592255d4f480b0d896512e50ce2588bd3347f6ed7b679b343b21e42fa1`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Full provenance with entity-activity-agent relationships, processing lineage and derivation paths",
  "evidence": "was_derived_from: the AI-READI observational study. raw_data_sources: two typed sources \u2014 direct prospective collection from participants, and the three health systems' electronic health records with access_details for the controlled tier. raw_sources: raw device and system exports enumerated by format (.xml ECG, MoCA .csv, Topcon .fda, Heidelberg .sdt, Garmin .FIT, Dexcom and sensor .csv, laboratory .csv, REDCap exports) with a retention and non-sharing statement and the reasons (not mapped to standard terminologies; may contain PHI in free text). Derivation paths: preprocessing_strategies traces each raw format to its released standard (.fda \u2192 DICOM, .sdt \u2192 DICOM, .FIT \u2192 Open mHealth, .xml \u2192 WFDB, clinical \u2192 OMOP CDM). Agents: data_collectors (coordinators, site data managers, central laboratory, CLIA laboratories), cleaning_strategies (site PI approval for edits and removals), data_governance.stewardship_roles (data manager QC before upload; central team standardization). version_access with three DOIs; updates with CHANGELOG; related_datasets with typed is_new_version_of and is_source_of links. missing_data_documentation with patterns, causes and handling_strategy; anomalies with five entries. splits and three subsets with is_data_split true. conforms_to describes an RO-Crate 1.2-DRAFT package under FAIRSCAPE profile 0.1 with nine sub-crates. Unpopulated: errata, parent_datasets.",
  "quality_note": "Top band met. The rubric explicitly accepts text-form provenance where it supplies complete lineage, and this record does: entities (raw device exports, processed collections), activities (standardization to OMOP and DICOM, per-format conversion, range-check cleaning, Safe Harbor removal, CDS organization) and agents (named collector roles, data managers, site PIs, central team) are all identified, and the derivation path from each raw format to each released format is traceable per modality. A machine-readable RO-Crate/FAIRSCAPE package is additionally referenced. Quality documentation is substantive \u2014 range checks, skip-pattern validation, duplicate detection, PI adjudication, and an OMOP Data Quality Dashboard configuration running 3,500+ checks.",
  "semantic_analysis": "Lineage is corroborated across fields rather than asserted once: device formats in collection_mechanisms match the raw formats in raw_sources, which match the conversion steps in preprocessing_strategies, which match the per-collection conforms_to_standard values in file_collections. Two gaps limit but do not lower the band: errata is empty despite the Snellen variable removal, and parent_datasets is unused, though related_datasets carries the version lineage with typed relationships. The RO-Crate is described as distributed outside the release, so the machine-readable provenance is referenced rather than shipped."
}
```

## AI_READI_v8_rep3_r20_rating1

Recorded Q19: 4/5. Status: `requires_adjudication`.

Q19 records4/5 and acknowledges an end-to-end textual account, but its withholding rationale requires was_derived_from links and addressable activity nodes. The frozen rule permits complete textual lineage without those serialization/field-placement requirements. It also says the central standardization agent cannot be determined, while data_governance.stewardship_roles explicitly assigns standardization and dissemination processing to the central project team. Preprocessing supplies native formats and conversion targets; cleaning supplies site QC followed by transfer/central review. The claimed lack of detailed step ordering may still need substantive adjudication, so this flag does not assign5 or certify complete lineage; it identifies the added representation demands and overlooked role evidence.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/AI_READI_v8_rep3_r20_rating1_evaluation.json); SHA256 `eeb9f97b0889a300a2601a4353028cc0298223b1de5f88d997ba5306ec559db3`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Well beyond version history, with textual processing lineage, but short of a full provenance graph",
  "evidence": "Present: version_access (three versions with DOIs and dates, latest_version_doi, version_details); updates (static-version model, CHANGELOG, approximately annual); missing_data_documentation (patterns, causes, handling_strategy); subsets with is_data_split true \u00d73 and splits.split_details describing the 70/15/15 assignment in participants.tsv; raw_sources describing retained device and REDCap exports and why they are not shared. Lineage in text: preprocessing_strategies traces device-native exports (.fda, .sdt, .FIT, XML, CSV) through conversion to DICOM and mHealth and mapping to OMOP, DICOM, WFDB and Open mHealth; cleaning_strategies names the agents at each stage ('The data manager at each collection site was responsible for the quality control of all data before upload to FAIRhub. After transfer to the central project team, the dataset was additionally reviewed internally'); related_datasets gives the derivation chain v1.0.0 \u2192 v2.0.0 \u2192 v3.0.0 via is_new_version_of and is_source_of for the mini-subset; anomalies documents modality-specific quality failure modes; known_limitations records the v3.0.0 removal of Snellen acuity variables. Absent: errata; was_derived_from; parent_datasets; no PROV-O or other graph serialisation.",
  "quality_note": "This is clearly more than the version history that defines the 3 band: there is an end-to-end textual account of how raw device output became released files, who performed each transformation, and how releases derive from one another, plus quality documentation at modality level. It falls short of the 5 band because the lineage is narrated at the level of strategies rather than resolved into entity\u2013activity\u2013agent relationships over identified artifacts: no was_derived_from links a released collection to the raw export it came from, no activity is identified as an addressable node, and the derivation path exists only as a relationship type between version DOIs. Errata is also absent.",
  "semantic_analysis": "The instrument accepts text in place of a PROV-O serialisation where the text provides complete lineage, so the question is whether the lineage is complete, not whether it is RDF. It is not quite complete: a reader can say that .sdt files became DICOM and that site data managers ran QC, but cannot determine which activity produced a given released collection, in what order the mapping and conversion steps ran, or which agent performed the central standardisation. The RO-Crate packaging noted in conforms_to would be a natural carrier for exactly this graph, which makes its absence from the record conspicuous rather than unavoidable. Integrity-side evidence is strong and independently checkable \u2014 the file-count and byte-total reconciliations and the split arithmetic all hold \u2014 which is why this sits at 4 rather than 3."
}
```

## CHORUS_v7_rep1_r20_rating1

Recorded Q19: 4/5. Status: `requires_adjudication`.

Q19 records4/5 and credits source-system to extraction/transform to released-format lineage for each modality, but explicitly withholds5 partly because was_derived_from and parent_datasets are empty and the text is human-readable rather than machine-readable. That adds a representation requirement beyond the frozen text-or-graph rule. The input connects hospital sources, site acquisition roles and SOPs, OHNLP tokenization, waveform conversion, OMOP mapping and DeGauss geocoding. The rationale also cites missing version access, errata and missingness documentation, which may be substantive independent grounds; those are not adjudicated here and this flag does not assign a replacement5.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CHORUS_v7_rep1_r20_rating1_evaluation.json); SHA256 `d9dc9d3e86843f2c227909609606a1997317bba2f158c8ec25c566f6b23aa574`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Strong textual lineage; no version history and no formal derivation linkage",
  "evidence": "raw_data_sources: six entries each pairing a source_description with source_type and raw_data_format \u2014 hospital EHR (site formats mapped to OMOP), EHR free text ('extracted and tokenized with the OHNLP toolkit', access_details 'Notes are stored locally at the contributing site; only tokens are made available centrally'), hospital PACS (DICOM), bedside monitoring infrastructure (WFDB), hospital EEG database (EDF+ and Persyst), and contextual/geospatial data linked to OMOP Location entities. updates.update_details present. splits documents the sequestered holdout. Agents identified in data_collectors (14 Data Acquisition centers; site managers under Chorus_SOP). Activities identified in preprocessing_strategies and cleaning_strategies (OMOP mapping, tokenization, waveform conversion, DeGauss geocoding, characterization reports, validated semantic mappings). Absent: version_access, errata, was_derived_from, parent_datasets, missing_data_documentation.",
  "quality_note": "The lineage this record does provide is unusually complete in text form: for every modality one can trace source system, to extracting agent, to transforming activity and named tool, to released format. Entity, activity, and agent are all identifiable even though no PROV-O serialization exists, and the rubric accepts textual provenance. What keeps it from 5 is that the formal derivation fields are empty \u2014 was_derived_from and parent_datasets record nothing, so the derivation paths are readable by a human and not by a machine \u2014 and the integrity half of the question is bare: no version_access, no errata channel, and no missing_data_documentation for a dataset built on high-frequency flowsheet and telemetry streams where missingness is pervasive and informative.",
  "semantic_analysis": "This record inverts the usual pattern the scoring bands anticipate. The 3 band describes version history without provenance; here provenance lineage is strong and version history is absent entirely, which is why the score sits above 3 despite the empty integrity fields. Derivation is coherent and checkable: each of the six raw_data_sources maps onto exactly one acquisition_method, one or more preprocessing_strategies, and one distribution_format, with no orphaned source and no format lacking an origin. The quality-control loop is real and documented rather than asserted \u2014 characterization reports returned to sites via CHoRUSReports, and semantic mappings validated under a clinical validation SOP \u2014 which is evidence of integrity practice even though no integrity artifacts (checksums, errata, validation reports) are exposed to reusers. The note-token architecture is provenance-relevant and correctly recorded: the released entity is derived from, and is not, the source note."
}
```

## CHORUS_v7_rep2_r20_rating1

Recorded Q19: 4/5. Status: `not_flagged_by_this_inspection`.

Q19 records4/5 and explicitly accepts and credits textual modality-level lineage with source systems, processing tools, site/consortium agents and QC. Its remaining concerns include traceability from a specific released file to a specific input/processing run, plus version access, errata and missingness documentation. Those are substantive granularity/completeness concerns that could apply to either text or a graph. Although it names empty dedicated fields and contrasts narrative with per-artifact provenance, this rationale does not clearly require machine-readable serialization itself; the supplied input primarily documents general per-modality workflows. This scoped inspection therefore does not establish a representation-only deduction and does not certify the score, the granularity demanded or the other absence claims.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CHORUS_v7_rep2_r20_rating1_evaluation.json); SHA256 `597deffef75a4a792e67b01c2f5285e68a2ceb0d827c70205d37ad1e39b936e4`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Strong textual lineage across sources, activities and agents; no versioning, errata or missing-data record",
  "evidence": "raw_data_sources \u00d75 with source_type, format and access details (hospital EHR; unstructured notes 'Notes remain stored locally at contributing sites; only tokenized output is moved into the enclave'; PACS/DICOM; bedside monitoring telemetry; EEG database/EDF+ and Persyst). Activities: acquisition under validated SOPs with chorus-extract-upload, OMOP standardization with flowsheet extensions, OHNLP tokenization, imaging de-identification (CTP-deid, privacy_scan_tool), waveform conversion scripts. Agents: 14 contributing hospitals, CHoRUS Standards/Data Acquisition/Tooling sub-teams, clinical collaborators validating chorus-mapping. Quality controls: CHoRUSReports characterization returned per submission; mapping review under a clinical validation SOP. splits: sequestered holdout test set. updates present. Absent: version_access; errata; was_derived_from; parent_datasets; missing_data_documentation.",
  "quality_note": "The rubric accepts textual provenance, and the record supplies a traceable path from each source system through named processing activities to the enclave, with responsible agents attached and two independent quality-control mechanisms \u2014 well past band 3, which describes version history without lineage. Held at 4 because derivation is narrative rather than recorded per artifact: no was_derived_from links, no parent dataset identifiers, no errata or version access, and no missing-data documentation, so a specific released file cannot be traced to a specific input or processing run.",
  "semantic_analysis": "Derivation paths are individually reconstructable per modality (EHR\u2192OMOP+extensions; notes\u2192OHNLP tokens with source text withheld; PACS\u2192DICOM\u2192de-identification; monitors\u2192gateway\u2192WFDB; EEG\u2192EDF+/Persyst) and the agent assignments are consistent with the collectors named under Q12, so the lineage is coherent rather than decorative. Integrity evidence is process-level only: characterization reporting and mapping validation are real controls, but no checksums, no record counts per submission and no validation results are given. Missing-data documentation is a notable omission precisely because high-frequency flowsheet and telemetry data are characteristically gappy, and its absence also cost a point under Q11."
}
```

## CHORUS_v7_rep3_r20_rating1

Recorded Q19: 4/5. Status: `not_flagged_by_this_inspection`.

Q19 records4/5, expressly accepts textual provenance and credits the modality-level entity/activity/agent chains. It then asks for traceability from specific source records to a specific released artifact/table and cites version, errata and missingness gaps. Its addressability objection is explained in terms of source-to-output granularity rather than an explicit demand for RDF, typed serialization or machine traversal. The input supplies general source/tool/site-role workflows; this inspection does not establish a representation-only penalty. Empty dedicated fields are mentioned, so the granularity threshold and other absence claims remain matters for semantic adjudication rather than certified correct findings.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CHORUS_v7_rep3_r20_rating1_evaluation.json); SHA256 `43a228dea6b422492527832d6227aac6ce3bae93b479765fa14dbfb2273e11a6`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Strong textual lineage across sources, activities and agents; no version history or explicit derivation paths",
  "evidence": "raw_data_sources (5) as entities, each with source_description, source_type, raw_data_format and access_details. Activities: acquisition_methods (2, the second flagged was_inferred_derived: true \u2014 'clinical notes are tokenized, source data are mapped to the OMOP Common Data Model, and data are transformed using approaches that limit re-identification') and preprocessing_strategies (5, each naming the implementing repository). Agents: data_collectors (3 roles) and maintainers (2). splits records the sequestered holdout test set. updates is populated. Absent: version_access, errata, was_derived_from, parent_datasets, missing_data_documentation.",
  "quality_note": "Four of nine fields populated, but the question is scored on provenance substance and the rubric expressly accepts a textual representation. Entity, activity and agent are all recoverable and can be chained per modality \u2014 for example hospital PACS (entity) to de-identification and DICOM release (activity) by site data managers (agent). That is more than the 3 band, which describes version history without provenance; this record is the mirror image, with lineage but no versioning. Held at 4 because the 5 band needs a complete graph: there is no was_derived_from linking a specific released artefact to a specific source, no parent_datasets, and no missing-data documentation.",
  "semantic_analysis": "The lineage is consistent wherever it can be cross-checked \u2014 the five raw_data_sources correspond one-to-one with the five collection_mechanisms and the five distribution_formats, and each preprocessing step names the repository that implements it, which is stronger evidence of a real pipeline than prose alone. Two integrity gaps matter for reuse. First, no errata or version access means a data defect discovered after release has no documented channel to reach users, which interacts badly with the growing partial release described in status. Second, missing_data_documentation is absent for modalities where missingness is structurally informative: nursing flowsheets and waveform telemetry are irregularly sampled by nature, and the record acknowledges elsewhere that imaging and EEG coverage is partial, so completeness varies by modality in ways a consumer cannot quantify. The derivation is directionally clear but not addressable: one cannot ask which source records produced a given released table."
}
```

## CHORUS_v8_rep1_r20_rating1

Recorded Q19: 4/5. Status: `requires_adjudication`.

Q19 records4/5 and explicitly withholds5 partly because no collection carries a machine-readable derivation link, even while crediting a reader-traceable source-system to mechanism to transformation to released-collection path with named responsible agents. That adds a representation requirement beyond the frozen text-or-graph rule. The input provides was_derived_from, five modality-level raw sources, named OMOP/OHNLP/waveform transformations, site-manager and sub-team roles, and characterization/SOP validation. Missing version access, errata and finer artifact-level relationships may be independent substantive concerns; they are not adjudicated here. Flag the original Q19 and total without assigning a replacement5 or certifying complete lineage.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CHORUS_v8_rep1_r20_rating1_evaluation.json); SHA256 `79fa60b8bd5f77f0c649c55fb8b36447699b9ccef7c96d968466acee652b6ab2`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Strong textual lineage with entities, activities and agents; no versioning and no per-collection derivation identifiers",
  "evidence": "was_derived_from: 'Clinical source systems at the 14 CHoRUS data contributing hospitals, comprising electronic health records, PACS imaging archives, bedside monitors with gateway/middleware, and hospital EEG databases.' raw_data_sources: 5 entries each with source_description, source_type, raw_data_format and access_details (e.g. 'Continuous bedside physiologic monitoring at contributing hospitals' / 'Bedside monitors with gateway/middleware' / 'Waveform telemetry, converted to WFDB'). Activities: acquisition_methods (observed / derived / validated), preprocessing_strategies (OMOP semantic mapping via chorus-mapping, OHNLP tokenization, chorus_waveform conversion), cleaning_strategies (CHoRUSReports characterization returned to sites; clinical validation SOP). Agents: data_collectors ('Data site managers at each contributing site extract and submit...'; Standards, Data Acquisition and Tooling sub-teams), created_by 'CHoRUS Consortium'. Quality/missingness: instances[].missing_information with why_missing for imaging ('De-identification was in process for a larger imaging cohort') and notes ('Clinical notes are stored locally at contributing sites; only tokens leave the site'); known_limitations (4 typed). updates populated; splits describes a planned holdout. Absent: version_access, errata, parent_datasets, missing_data_documentation, subsets.is_data_split.",
  "quality_note": "The rubric permits provenance as text, and as text this is close to complete: for each of the five modalities a reader can trace source system to acquisition mechanism to transformation tool to released collection, with the responsible agent named and the validation step identified. That is entity\u2013activity\u2013agent lineage with derivation paths. Held at 4 rather than 5 because the lineage is narrative and unidentified \u2014 no collection carries a machine-readable derivation link to its inputs or to the activity that produced it \u2014 and because the integrity half of the question is weak: version_access, errata and parent_datasets are all absent, so there is no mechanism to learn that a released record changed or was corrected.",
  "semantic_analysis": "Scoring here inverts the usual pattern the bands anticipate: version history is nearly absent while lineage is strong, the opposite of the 3-band description. The 4 reflects the rubric's explicit allowance that 'provenance may be represented as text OR as W3C PROV-O graphs'. Quality assurance is genuinely evidenced rather than asserted \u2014 characterization reports returned to contributing sites form a feedback loop, and semantic mappings pass through a clinical validation SOP with internal review. Missingness is documented where it exists, at instance level with reasons, though not in the field the rubric names. The provenance narrative also correctly captures a subtle point: acquisition_methods.was_inferred_derived explains that 'delivered records are derived from rather than identical to the site source records', which is exactly the derivation semantics PROV-O would encode."
}
```

## CHORUS_v8_rep2_r20_rating1

Recorded Q19: 4/5. Status: `requires_adjudication`.

Q19 records4/5, credits a substantially complete textual entity-activity-agent account, and says each modality is traceable by a reader. It then states that5 is blocked because lineage cannot be traced mechanically and lacks an identifier for graph reconstruction. Those are representation requirements beyond the frozen text-or-graph rule. The input supplies source-system descriptions, OMOP mapping, OHNLP tokenization, waveform conversion, DeGauss geocoding, de-identification and site-manager roles. Missing version access/errata and the precise source-to-artifact granularity remain independent unadjudicated concerns. Preserve the original score and qualify its containing total; no replacement score or exhaustive completeness judgment is made.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CHORUS_v8_rep2_r20_rating1_evaluation.json); SHA256 `42f528657bc887998e2f6ededdfa15ea2be7f3d7df07083dae0c60423940116d`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Strong textual lineage with entity-activity-agent structure; no version access or errata",
  "evidence": "was_derived_from: 'Routine clinical documentation and device data from the electronic health record, PACS imaging archives, bedside monitor gateway/middleware, and hospital EEG databases of 14 contributing hospitals.' raw_data_sources (5) each with source_description, source_type, raw_data_format and access_details. acquisition_methods with was_directly_observed / was_inferred_derived flags. preprocessing_strategies (5) tracing each modality's transformation: source EHR \u2192 OMOP via validated semantic mappings; notes \u2192 OHNLP tokens; monitor capture \u2192 WFDB via chorus_waveform scripts; OMOP Location \u2192 geocoded via DeGauss; imaging \u2192 de-identification. cleaning_strategies describing characterization reports returned to sites. subsets.is_data_split=false across all 9 subsets; splits describing a planned sequestered holdout. Absent: version_access; errata; parent_datasets; missing_data_documentation.",
  "quality_note": "The rubric permits provenance as text, and the textual lineage here is substantially complete: entities (five raw sources per modality), activities (extraction, standardization, tokenization, waveform conversion, geocoding, de-identification), and agents (14 contributing hospitals, site data managers, and named tools/repositories) are all identifiable and connected modality by modality. Held at 4 rather than 5 because the version/integrity limb is largely empty and the derivation paths are narrative rather than systematically linked.",
  "semantic_analysis": "This record inverts the usual pattern the bands assume: it is weak on version history (no version_access, no errata) yet strong on lineage, so band 3's description does not fit it well. Assessed on substance, the entity-activity-agent triad is genuinely present and each modality's path from source system to released form can be traced by a reader. What blocks 5 is that the lineage cannot be traced mechanically \u2014 no released artifact is linked to the specific activity that produced it, no parent_datasets exist, and there is no identifier on which a provenance graph could be reconstructed. missing_data_documentation is absent despite obvious incompleteness in the data (imaging de-identification and EEG extraction both in process), which is a quality-documentation gap on top of the provenance one."
}
```

## CHORUS_v8_rep3_r20_rating1

Recorded Q19: 3/5. Status: `not_flagged_by_this_inspection`.

Q19 records 3/5 and explicitly credits complete modality-level textual entity/activity/agent paths as permitted by the rubric. Its stated limiting concern is that those paths terminate in an unidentified, unversioned release, with no version access or errata. The input supplies source systems, transformations, site-manager/sub-team roles, missingness documentation and QC, while its update caveat explicitly says no versioning policy is stated. The rationale also calls the absent was_derived_from field a machine-traversability gap, but does not clearly make that representation objection the score-limiting condition; the identified-release concern could apply equally to text or a graph. This scoped inspection therefore does not establish a representation-only deduction. It does not certify the score of 3, the requested artifact granularity or the other absence claims.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CHORUS_v8_rep3_r20_rating1_evaluation.json); SHA256 `8e952fc6f6c445a3b2af84320ec98bdbff40c849d43f593ca9c20f3d5778dbbd`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 3,
  "max_score": 5,
  "score_label": "Substantial textual lineage, but no versioning anchor and no complete derivation graph",
  "evidence": "Present: raw_data_sources \u2014 five typed origin systems with native formats ('Structured electronic health record systems at 14 data contributing hospitals'; unstructured notes; 'Hospital picture archiving and communication systems (PACS)' in DICOM; 'Bedside physiologic monitors and their gateway/middleware'; 'Hospital EEG databases' as EDF+/Persyst). updates.update_details (expansion plan). missing_data_documentation with both missing_data_patterns and missing_data_causes. splits (holdout intention, composition unstated). Quality control via cleaning_strategies: 'Characterization reports are produced and returned to contributing sites following their data submissions'. Absent: version_access; errata; was_derived_from; parent_datasets.",
  "quality_note": "An unusual profile: lineage is strong where versioning is absent. Read across raw_data_sources \u2192 acquisition_methods \u2192 collection_mechanisms \u2192 preprocessing_strategies \u2192 cleaning_strategies \u2192 distribution_formats, the record does supply entities (source systems, site extracts, the enclave holdings), activities (extraction, OMOP mapping, OHNLP tokenization, WFDB conversion, de-identification, DeGauss geocoding) and agents (14 acquisition centers, site data managers, Standards/Data Acquisition/Tooling sub-teams) \u2014 which is the textual form of provenance the question expressly permits. What prevents a higher score is that this lineage is not anchored to any identified released artifact: there is no version, no version_access, no errata, no was_derived_from and no parent_datasets, so derivation paths terminate in an unversioned, unidentified 'current release'. Equally, the 3 band's own descriptor \u2014 version history \u2014 is itself not met, since no version number or erratum exists. Scored 3 as the balance of a well-documented process lineage against an absent integrity and versioning layer.",
  "semantic_analysis": "Consistency pass: the lineage is internally coherent at every hop \u2014 each raw source's native format matches the mechanism that extracts it and the preprocessing that transforms it into the stated output format. Quality signals are real: CHoRUSReports characterization returned to sites is a genuine data-quality feedback loop, and missing_data_documentation distinguishes data availability from metadata publication per modality, which is precisely the integrity information an AI/ML user needs. Structural gap: was_derived_from is unpopulated even though raw_data_sources contains exactly the derivation content it would carry, so the provenance is human-readable but not machine-traversable. Compounding issue already raised: with no DOI and no version, no analysis performed on this data can be pinned to a reproducible state of it."
}
```

## CM4AI_v7_rep1_r20_rating1

Recorded Q19: 4/5. Status: `not_flagged_by_this_inspection`.

Q19 records 4/5, credits textual entities, activities and laboratory agents, and distinguishes a packaged graph claim from lineage actually recoverable in the record. Its limiting concern is linking a particular released archive to its particular raw deposit, whose accession is not supplied in raw_sources; that is a traceability/content concern that can apply to either text or graphs. The input contains named archives, checksums, lab roles, the MuSIC embedding/annotation workflow and release-version links, but the four external raw-deposit descriptions give repository names rather than accessions. Although the rationale names absent was_derived_from edges and the graph being outside the record, it does not clearly demand machine-readable serialization when equivalent complete text is available. This scoped inspection does not establish a representation-only deduction, certify the score or adjudicate its artifact-granularity, missingness and errata expectations.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CM4AI_v7_rep1_r20_rating1_evaluation.json); SHA256 `b3b32ffa0b6d5d119177308cb90d59bece05202e64b9e58144489d91ed63d1a3`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Version access, errata, update plans, source derivation, parent linkages, missing data documentation, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Substantial lineage and integrity metadata; full provenance graph asserted rather than exhibited",
  "evidence": "version_access with the full release series and latest_version_doi; updates with quarterly frequency; raw_data_sources: two entries ('Protein-protein interaction networks generated by SEC-MS and AP-MS, downloaded from the Krogan Laboratory's deposition archive'; immunofluorescence images from the Lundberg Laboratory's archive, with raw_data_format). raw_sources: four external deposits (MassIVE for iPSC and cancer-cell MS, SRA via NCBI BioProject, Figshare). Derivation lineage across releases via four is_new_version_of relationships with DOIs. Integrity: MD5 checksums for all ten archives (e.g. 6c1a86520eec2696ec19444eb8a8b428) plus per-file publication dates. Provenance packaging: description states output data are 'packaged with provenance graphs and rich metadata as AI-ready datasets in RO-Crate format using the FAIRSCAPE framework', and file_collections includes cm4ai_release_metadata.zip 'including RO-Crate metadata and provenance graphs'. Absent: errata, was_derived_from, parent_datasets, missing_data_documentation, splits/is_data_split.",
  "quality_note": "Entity\u2013activity\u2013agent structure is recoverable in substance \u2014 entities (raw sources, ten named archives), activities (four acquisition methods and processing steps), agents (three named laboratories, maintainers, creators) \u2014 and file-level checksums give real integrity verification. It stays at 4 because the PROV-O graph itself lives inside a packaged metadata archive rather than in the record: no was_derived_from edges connect individual released archives to their raw sources, and errata, missing-data documentation and split indicators are absent.",
  "semantic_analysis": "The provenance claim is credible and consistently expressed \u2014 FAIRSCAPE/RO-Crate is the right vehicle, and the release metadata archive is actually enumerated with a size and checksum rather than merely alluded to. What a consumer cannot do from this record alone is trace a specific archive to its specific raw deposit, since the raw deposits lack accessions; that combination of an asserted graph plus unresolvable endpoints is what separates this from the top band."
}
```

## CM4AI_v7_rep2_r20_rating1

Recorded Q19: 4/5. Status: `requires_adjudication`.

Q19 records 4/5 while crediting reconstructable textual entities, activities and laboratory agents, then withholds 5 because the graph is not explicitly expressed and collections lack was_generated_by. Its broader statement that acquisition-to-archive mapping is unavailable except through filenames overlooks file_collections.description: the IF archives explicitly name assay, cell line, treatment, lab and institution, and SEC-MS/AP-MS descriptions identify their assays and source material. These observations support a representation/field-placement flag under the frozen text-or-graph rule. The input does not necessarily provide all processing-run or raw-accession detail, so complete lineage and a replacement 5 are not certified. The additional non-monotonic-version objection overlooks the explicit separate-deposit/internal-version scope in version_access.version_details; that scoring qualification is separately recorded under issue 1355. Preserve and qualify the original Q19 and containing total.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CM4AI_v7_rep2_r20_rating1_evaluation.json); SHA256 `b0e22af2feab2fff686eea1bc702e62cf184b101c418930e72536bc5a91286e1`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Well beyond version history, with a declared provenance graph, short of an explicit graph in the record",
  "evidence": "was_derived_from: 'Multimodal experimental interrogation of the MDA-MB-468 breast cancer cell line and the KOLF2.1J induced pluripotent stem cell line and their differentiated derivatives, by AP-MS, SEC-MS, CRISPRi Perturb-seq, and immunofluorescence confocal microscopy.' Provenance packaging declared twice: description states 'CM4AI output data are packaged with provenance graphs and rich metadata as AI-ready datasets in RO-Crate format using the FAIRSCAPE framework', and cm4ai_release_metadata.zip is described as 'comprising RO-Crate metadata and provenance graphs', with conforms_to 'RO-Crate' and conforms_to_standard [RO_CRATE]; distribution_formats notes that earlier releases 'exposed RO-Crate metadata as individual ro-crate-metadata.json files and HTML provenance graph renderings'; notes records FAIRSCAPE ARK persistent identifiers. raw_data_sources: four entries with source_type and destination repositories. version_access and updates as cited in Q13. related_datasets supplies release lineage by DOI. Per-file MD5 checksums on all ten archives. Absent: errata, parent_datasets, missing_data_documentation, splits / is_data_split.",
  "quality_note": "Clearly exceeds the 3 band, which is version history alone: a provenance-graph artifact is declared and shipped as a release component, and the textual lineage supplies the three PROV roles in reconstructable form \u2014 entities (checksummed, DOI-addressed file collections), activities (four acquisition_methods and five preprocessing_strategies) and agents (named labs in data_collectors, 38 ORCID-identified creators, four maintainers). Integrity is independently supported by MD5 checksums.",
  "semantic_analysis": "Held to 4 because the graph is asserted rather than expressed here. The record never wires specific activities to specific outputs \u2014 no collection carries a was_generated_by, and a reader cannot tell from this datasheet which acquisition produced which of the ten archives, even though the filenames imply it. Three quality slots are also empty: missing_data_documentation is absent although known_limitations concedes incompletely overlapping protein sets across modalities, and no data-split indicators are given for a dataset explicitly intended for model training. Version-history provenance is itself degraded by the non-monotonic version sequence flagged at Q13."
}
```

## CM4AI_v7_rep3_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

Q19 awards 5/5 and explicitly accepts textual provenance despite absent was_derived_from and parent_datasets. The input names cell-line materials, assay activities, producing laboratories, enumerated archives, release versions and the UVA packaging/deposit role. It distinguishes the MuSIC cell-map workflow from the artifacts actually released, provides missingness documentation and describes the RO-Crate/EVI provenance packaging. The rationale acknowledges the excluded cell-map outputs and does not make a graph serialization or dedicated-field requirement a reason to reduce Q19. This scoped inspection does not independently certify complete released-artifact lineage, the source-level checksum interpretation or external ontology claims.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CM4AI_v7_rep3_r20_rating1_evaluation.json); SHA256 `1a4dd709685209dd8570047fd73458560669a16bef5ee87964df09e95f4251e0`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Full provenance graph with entity-activity-agent relationships, processing lineage, and derivation paths",
  "evidence": "Provenance graph: conforms_to states that each RO-Crate 'carries an end-to-end provenance record expressed in the EVI Evidence Graph Ontology, serialized as JSON-LD and RDF-XML, with dataset schemas expressed in JSON-Schema', and that 'each RO-Crate is assigned an ARK persistent identifier'; intended_uses adds that 'inputs, computations, software and outputs are machine-resolvable'; file_collections includes a 'Release metadata archive... including RO-Crate metadata and provenance material for the June 2026 release'; cleaning_strategies describes per-segment crate generation by the FAIRSCAPE client. Entities, activities and agents are separately identified: archives (file_collections), assays (acquisition_methods, collection_mechanisms) and producing laboratories (data_collectors \u2014 Lundberg Lab, Krogan laboratory, UCSD, UVA). Derivation paths: raw_data_sources gives four upstream sources with RRIDs and repository deposits; related_datasets gives four is_new_version_of edges; version_access lists five releases with DOIs. Quality and integrity: cleaning_strategies QC and JSON-Schema validation; source_caveats records an MD5 comparison \u2014 'the three immunofluorescence image archives in the June 2026 release report the same file sizes as those in the October 2025 release but different MD5 checksums, indicating the archives were regenerated'. missing_data_documentation gives patterns, causes and handling_strategy. Absent: errata, was_derived_from, parent_datasets, splits.",
  "quality_note": "This clears the rubric's distinction between version history alone (3) and a full provenance graph (5). Version history is present, but so is a named provenance ontology with a declared serialization and per-package persistent identifiers, a processing lineage in which each pipeline segment emits a validated crate, and derivation paths running from identified upstream materials through named producing laboratories to enumerated archives. The rubric accepts provenance as text or as W3C PROV-O graphs provided the lineage is complete, and the lineage here is complete for what is released.",
  "semantic_analysis": "EVI is a genuine PROV-derived evidence graph ontology and JSON-LD/RDF-XML are the correct serializations to claim for it, so the assertion is technically coherent rather than a standards name-drop. Two deductions were considered and judged insufficient to drop a band. First, was_derived_from and parent_datasets are unpopulated, so the derivation is expressed narratively and via related_datasets rather than in the designated typed fields \u2014 a machine-readability gap, already logged against Q1 where field completeness is the operative criterion. Second, the most elaborate provenance description attaches to the MuSIC pipeline whose outputs are excluded from this release; but the released artifacts' own lineage (source material \u2192 assay \u2192 producing laboratory \u2192 packaged archive) is fully traceable from the record, and the exclusion is disclosed. The MD5 observation deserves specific credit: the author performed an actual integrity comparison across releases, detected regenerated archives, and then declined to carry forward the earlier per-file protein counts \u2014 provenance reasoning applied rather than merely described. The absence of splits is not penalised, since no train/test partition is claimed."
}
```

## CM4AI_v8_rep1_r20_rating1

Recorded Q19: 4/5. Status: `requires_adjudication`.

The original Q19 credits a recoverable entity-activity-agent triad but explicitly withholds 5 because derivation paths are not encoded in was_derived_from/parent_datasets, and says a machine cannot reconstruct links that live in prose. The input names source cell lines, assay activities, producing laboratories and archive collections in text; acquisition_methods and preprocessing_strategies also explicitly describe the KOLF2.1J raw-sequence-to-atlas relationship, with its filename-based inference caveat. Requiring the same content in designated graph fields adds a representation requirement beyond the frozen text-or-graph rule. The independent concerns about inferred processing, unidentified RO-Crate artifacts and thin missing-data/split documentation remain unadjudicated; this inspection does not establish complete lineage or a replacement score.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CM4AI_v8_rep1_r20_rating1_evaluation.json); SHA256 `3760295a52cb901e9700b6f31a0d87c16c4fcd5c485e14634caaa1bb1b1f1634`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Rich narrative provenance and integrity; graph claimed but not evidenced, structured derivation fields empty",
  "evidence": "Integrity: an MD5 checksum on every one of the ten resources (e.g. '8642317c321126213240af4837030a53'), with distribution_formats noting 'MD5 checksums are published for each archive'; the record uses checksum comparison substantively, observing that 'The June 2026 archives carry different MD5 checksums from the October 2025 archives of the same names'. Provenance elements: version_access with a five-release lineage and per-release DOIs; updates with a quarterly cadence; raw_data_sources naming both origin cell lines with RRIDs and repositories; raw_sources listing five upstream raw deposits (MassIVE for SEC-MS KOLF2.1J, SEC-MS MDA-MB-468, AP-MS paclitaxel, AP-MS vorinostat; the raw SRA archive for the CRISPRi screen); acquisition_methods typing one path as was_directly_observed and another as was_inferred_derived; data_collectors assigning each modality to a producing institution and laboratory (agents); collection_mechanisms describing the generating activities; related_datasets typing the link to the predecessor release as is_new_version_of; conforms_to asserting 'RO-Crate packaging with provenance graphs'. Absent or empty: errata; was_derived_from; parent_datasets; missing_data_documentation; subsets.is_data_split; splits.",
  "quality_note": "The entity-activity-agent triad is recoverable in substance \u2014 producing laboratories as agents, named assay mechanisms as activities, raw deposits and derived archives as entities \u2014 and integrity is verifiable per file rather than asserted, which is more than the 3-band's version history alone. It falls short of 5 because the derivation paths that would make this a graph are not encoded: was_derived_from and parent_datasets are empty, the one derivation asserted (atlas from raw sequence) is admittedly inferred from filenames, and the claimed RO-Crate provenance graph is not identifiable among the shipped resources. Data-quality documentation is also thin \u2014 no missing-data documentation and no split indicators for a dataset offered for model training.",
  "semantic_analysis": "This is the strongest gap between claim and encoding in the record. A machine consuming this datasheet could not reconstruct which archive derives from which raw deposit, because the structured fields for that are empty and the linkage lives in prose and in filename parallelism. Set against that, the integrity story is exemplary in a way that deserves credit: checksums exist for every file and are actually used to reason about what changed between releases, which is provenance work rather than provenance assertion. Temporal ordering across the lineage is coherent (created_on 2025-02-27 \u2192 issued 2026-06-17 \u2192 amended file publication 2026-07-15), with the last of these flagged by the record itself as anomalous relative to the version date."
}
```

## CM4AI_v8_rep2_r20_rating1

Recorded Q19: 4/5. Status: `requires_adjudication`.

The original Q19 explicitly reserves the top band because the reader must assemble links by matching prose across four fields and because was_derived_from is empty. Its own input identifies cell-line entities and acquisition activities, names performing laboratories, and binds released archive collections to modalities and material in descriptions; the SEC-MS collection directly names its producing laboratory. Penalizing textual links for their placement adds a representation/field-placement condition not required by the frozen text-or-graph rule. The distinct concerns about undescribed current image-archive contents, missingness and coverage information remain unadjudicated, and no completeness certification or replacement score is assigned.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CM4AI_v8_rep2_r20_rating1_evaluation.json); SHA256 `ae7a6916fec053e1a6c2637594db2080b1cf405fc66a71aada18f07cb159b598`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Substantially more than version history, short of a full provenance graph",
  "evidence": "version_access lists five releases with DOIs and names the latest; errata records one erratum with a URL; updates gives a quarterly cadence to November 2026. Derivation beyond version history: raw_data_sources identifies both source cell lines with Cellosaurus RRIDs, donor origin and access routes; data_collectors names the performing laboratories (agents); acquisition_methods names the four measurement activities with was_directly_observed: true; file_collections bind entities to those activities by name and collection_type: raw_data; related_datasets encodes the derivation chain to four predecessor releases as typed is_new_version_of relationships. Integrity: MD5 checksums for all ten files, and the record uses checksum difference as evidence that the June 2026 image archives are not the October 2025 files. conforms_to: RO-Crate declares provenance-capable packaging; FAIRSCAPE is named in external_resources. Absent: was_derived_from, parent_datasets, missing_data_documentation, splits (subsets.is_data_split is present and false).",
  "quality_note": "Above the version-history band on several independent counts \u2014 named source entities with persistent identifiers, named agents, named activities, file-level fixity and a dated release lineage \u2014 but the top band requires the entity-activity-agent links to be represented, and here the reader must assemble them by matching prose across four fields. Three designated fields are empty, including was_derived_from, which is exactly the field that would carry the derivation path.",
  "semantic_analysis": "Quality documentation is asymmetric: fixity and lineage are strong, while completeness metadata is absent \u2014 missing_data_documentation is empty and no instance counts are given, so a reuser cannot assess coverage gaps within a modality, only across modalities via the integration_limitation note. The RO-Crate conformance claim sits oddly beside the absent was_derived_from, since the packaging standard the record declares is designed to express precisely the derivation links the metadata leaves implicit. The record's own caveat that the June 2026 image archives differ in checksum from their October 2025 counterparts, and that their contents are undescribed, is an honest but real provenance gap for the largest three files in the release."
}
```

## CM4AI_v8_rep3_r20_rating1

Recorded Q19: 4/5. Status: `requires_adjudication`.

The original Q19 says entity-activity-agent elements are present but scattered across fields, then explicitly requires relationships expressed as a graph for full marks and credits an ID graph fragment for the fourth point. The own input names upstream raw modalities, material and origin repositories; acquisition_methods describes generating assays and data_collectors names the performing laboratories. Those textual relationships are relevant under the frozen text-or-graph rule and cannot be rejected merely because a standalone encoded graph is absent. Whether this record fully documents all processing paths, whether its RO-Crate/EVI claims are supported, and its missingness/QC gaps remain unadjudicated. This flags the representation-dependent rationale without assigning a replacement score or certifying complete lineage.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/CM4AI_v8_rep3_r20_rating1_evaluation.json); SHA256 `1da34cd91d5e2d756533c113568cb0c20935a1f85682d3a01c7db04f01aa2b23`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 4,
  "max_score": 5,
  "score_label": "Very good \u2014 version history plus derivation and fixity, short of an explicit provenance graph",
  "evidence": "version_access lists the full predecessor lineage with DOIs and latest_version_doi. updates gives a quarterly cadence through November 2026. raw_data_sources enumerates seven upstream sources with type and access_details, mapping each released modality to its origin repository (MassIVE, Figshare) or embargo state. related_datasets supplies typed lineage (three is_new_version_of links, is_described_by, is_referenced_by, references). subsets record is_data_split: false explicitly for all nine entries, and each subset names the file_collection that distributes it while each file_collection names the subset it contains. Every file_collection carries an MD5 checksum. conforms_to describes FAIRSCAPE RO-Crate packaging with 'provenance graphs and rich metadata', and notes describes ARK identifiers with 'provenance entailments expressed in the EVI Evidence Graph Ontology'. Absent: errata, was_derived_from, parent_datasets, missing_data_documentation, splits.",
  "quality_note": "This goes well past 'version history only'. Derivation is documented in two directions \u2014 upstream to the raw acquisitions and their repositories, and laterally to predecessor releases through typed relations \u2014 and file-level MD5 fixity gives integrity checking that most records omit entirely. The elements of an entity-activity-agent structure are all present but scattered across fields: entities in subsets and file_collections, activities in acquisition_methods, agents in data_collectors and creators.",
  "semantic_analysis": "Full marks require a provenance graph with those relationships expressed as such, and this record describes one rather than containing one: the RO-Crate and EVI Evidence Graph claims are narrative, carried from the preprint and earlier releases, and the record itself concedes that the June 2026 release page does not restate the packaging format. The explicit subset\u2194file_collection ID linkage is a genuine in-record graph fragment and is why this sits at 4 rather than 3. Quality documentation is the weaker half: missing_data_documentation is empty and no QC metrics are reported for any modality, so integrity is well evidenced at the byte level and unevidenced at the measurement level."
}
```

## VOICE_v7_rep1_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

The original Q19 awards 5 and expressly accepts lineage expressed as text. Its own input connects participant-recorded raw WAV and REDCap/ReproSchema sources, computational derivation, parameterized preprocessing steps, released formats and clinician/research-team roles, with version access and correction history. The rationale mentions empty structured derivation fields as an informational issue and explicitly says it is not a deduction. No representation-dependent score limit is identified in this inspection. The ancillary challenge to the consortium self-assessment, full completeness of the lineage and external source truth are not independently adjudicated or certified.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/VOICE_v7_rep1_r20_rating1_evaluation.json); SHA256 `db3a18828b9a1b6042585790d6917a35e4342569c313636cbf701460ab6446f9`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Full provenance with entity-activity-agent relationships, processing lineage and derivation paths (expressed as text)",
  "evidence": "Entities: raw_data_sources names 'Raw audio waveforms of the acoustic tasks... recorded from participants with the Bridge2AI-Voice application' (WAV under BIDS) and 'Demographic, confounder, clinical validation and validated questionnaire responses captured in REDCap... and in ReproSchema-UI' (REDCap export to TSV with JSON dictionaries), each with source_type and access_details. Activities: acquisition_methods.was_inferred_derived ('The released acoustic features... were derived computationally from the raw audio waveforms') plus the eight-step preprocessing_strategies chain from resampling through feature extraction to BIDS v1.9.0 conversion, and the de-identification activity in is_deidentified.deidentification_details. Agents: named software (b2aiprep 'used to organize and preprocess the dataset, convert the raw audio waveforms into the Parquet feature files and merge the source data into the phenotype files', senselab, sparc, openSMILE, Parselmouth, Praat, ppgs, Whisper Large) and human agents (research teams, site clinicians, the ethics working group). Version integrity: version_access, three errata including 'Version 3.1.0 fixed broken Parquet files carried in the version 3.0.0 release', updates with semi-annual cadence. Quality: missing_data_documentation (causes, patterns, handling), cleaning_strategies audit protocol, anomalies (three entries). splits: 'No recommended training, validation or test splits are provided.' Derivation linkage: related_datasets.is_new_version_of -> doi:10.57764/qb6h-em84.",
  "quality_note": "This exceeds version history alone, which is the rubric's 3 band. The full path from participant to released artefact is recoverable: which entity was collected, by which agent, through which activity with which parameters, into which released format, under which version. The rubric expressly accepts text provenance where lineage is complete, and it is complete here.",
  "semantic_analysis": "The lineage is internally consistent - the raw WAV entity named in raw_data_sources is the input to the preprocessing chain, whose outputs are exactly the Parquet and TSV products enumerated in distribution_formats, and the withheld-audio policy is stated identically in raw_data_sources.access_details, distribution_formats and is_deidentified. Quality documentation is unusually candid: anomalies concede protocol drift across sites and time and that some audio could not generate features, and that concession is consistent with missing_data_documentation and with the measurement_bias entry. The structural weakness, recorded as an issue rather than a deduction, is that was_derived_from and parent_datasets are empty, so the derivation path is machine-readable only through the typed is_new_version_of link and must otherwise be reconstructed by a human reading four separate prose fields - which also undercuts the description's claim of 100 percent on provenance in the consortium self-assessment."
}
```

## VOICE_v7_rep2_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

The original Q19 awards 5 for textual entity-activity-agent lineage and explicitly states that neither an empty parent_datasets field nor the lack of PROV-O serialization changes the band. Its own input has an explicit was_derived_from statement, source formats and access, parameterized transformations, b2aiprep v3.0.0 tied to release v3.1.0, clinician/research-team roles and version/correction history. This inspection finds no representation-dependent score limit. The broader claim that every variable-level linkage and quality assertion is complete and internally consistent, and external source truth, are not independently certified.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/VOICE_v7_rep2_r20_rating1_evaluation.json); SHA256 `80e212fd41a26832519d9b73ec0d23f5b7199c1a4bd774d8d04924d58300b76b`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance graph representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Excellent - complete lineage with entities, activities, agents and derivation paths",
  "evidence": "was_derived_from: 'Raw voice, speech, breathing and cough audio recordings captured with the Bridge2AI-Voice application, together with questionnaire and clinical data exported from REDCap'. raw_data_sources: source_description, source_type, raw_data_format ('WAV audio, converted to monaural and resampled to 16 kHz before feature extraction; REDCap and ReproSchema exports converted to tab-delimited phenotype tables') and access_details. Processing lineage: eight preprocessing_strategies steps in order, each with parameters, terminating in 'version 3.1.0 was generated with b2aiprep v3.0.0'. Agents: b2aiprep v3.0.0, senselab, sparc, ppgs, torchaudio, openSMILE, Praat, parselmouth, Whisper Large, and human clinicians in labeling_strategies. Per-entity derivation: nine variables carry an explicit derivation plus measurement_technique (e.g. sparc_pitch 'Estimated fundamental frequency ... computed with a different algorithm from the torchaudio pitch, over a range of 50 to 550 Hz'). version_access, errata (4), updates, missing_data_documentation and splits are all populated; anomalies records five quality issues. parent_datasets is empty, with version lineage carried instead in related_datasets (is_new_version_of, is_version_of) with DOIs.",
  "quality_note": "This exceeds the 3-band, which is version history alone, on every axis. The chain from raw WAV through each named transformation to each released column is traceable end to end, with the transforming agent and its version identified and the derivation recorded per released variable \u2014 the entity-activity-agent structure the 5-band describes, expressed in text, which the rubric expressly accepts.",
  "semantic_analysis": "Lineage integrity holds under cross-checking: the tools named in preprocessing_strategies match the measurement_technique values in variables without contradiction, and the de-identification step that removes free-speech-derived features is reflected consistently in variables.quality_notes, missing_data_documentation.missing_data_causes and instances' differing per-feature record counts \u2014 three independent fields telling the same story about why counts diverge. Quality is documented rather than asserted, including audio QC metrics released from v3.1.0. Two residual gaps, both low severity and neither band-changing: parent_datasets as a named field is empty though its content sits in related_datasets, and no machine-readable PROV-O serialization is offered \u2014 which the rubric does not require."
}
```

## VOICE_v7_rep3_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

The original Q19 awards 5 and explicitly accepts text-form lineage despite absent was_derived_from/parent_datasets fields and PROV-O serialization. Its own input identifies raw WAV, questionnaire and clinical sources; parameterized transformations and de-identification; b2aiprep v3.0.0 for the release; clinician and research-team roles; and version-specific changes and corrections. The rationale does not impose a representation-dependent score limit. This inspection does not certify every artifact-level derivation, the full completeness claim, or the truth and resolvability of external sources.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/VOICE_v7_rep3_r20_rating1_evaluation.json); SHA256 `6258a153ee329ecba3c80f5795e9e5fb6e301e4f4989a5f746e42efbfad162cc`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, split indicators and provenance representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Full provenance with entity-activity-agent relationships, processing lineage and derivation paths",
  "evidence": "Entities: raw WAV recordings (raw_data_sources 'Raw audio waveforms recorded during the acoustic tasks', format WAV), REDCap exports, and released Parquet/TSV artefacts enumerated in file_collections. Activities: the preprocessing_strategies chain from standardisation (monaural, 16 kHz, Butterworth) through STFT/Mel/MFCC derivation, sparc articulatory coding, openSMILE and ppgs extraction, de-identification transforms, and BIDS v1.9.0 conversion. Agents: b2aiprep version 3.0.0 and senselab as software agents, site clinicians as labelling agents (labeling_strategies), and research teams as collection agents (data_collectors). Derivation paths: related_datasets derives_from https://www.synapse.org/Synapse:syn72370534/ with the description 'The released features were derived from the raw audio recordings of the adult cohort'; acquisition_methods was_inferred_derived 'All features distributed in the release were derived computationally from the standardized audio'. Version lineage: version_access with six versions and DOIs, errata with three corrections, updates with a v3.1.0 changelog. Quality: missing_data_documentation (patterns, causes, handling), anomalies (six entries), splits with split_details, and eight subsets carrying explicit is_data_split and is_subpopulation flags.",
  "quality_note": "Provenance goes well beyond version history. The three PROV-O components are recoverable in text, the derivation target is an addressable identifier rather than prose, and quality documentation (anomalies, missingness, audit metrics released as a file) accompanies the lineage.",
  "semantic_analysis": "No was_derived_from field and no PROV-O serialisation are present, and parent_datasets is empty; the rubric accepts text-form lineage where it is complete, and here it is - each released artefact can be traced to a source, an activity with parameters, and a responsible agent. The provenance is also self-correcting: the v1.1 versus v3.1.0 FFT parameter change and the v2.0 removal of free-speech spectrograms are recorded, so a user of an older version can tell what changed and why."
}
```

## VOICE_v8_rep1_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

The original Q19 expressly awards 5 on the textual route and says that absent PROV-O serialization and a top-level parent_datasets entry do not reduce the score. Its own input has a was_derived_from statement, raw WAV and REDCap origins with access details, parameterized signal-processing transformations, b2aiprep/SenseLab audit activity, clinician and research-team roles, and version/correction history. No representation-dependent score limit is identified. The claim of complete file-by-file lineage and external identifier resolvability is not independently certified by this focused inspection.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/VOICE_v8_rep1_r20_rating1_evaluation.json); SHA256 `cbf9cd3c0930953db2e328a8a81316e2240d439d86ec99240537e54002c23f54`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, split indicators and provenance graph representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Full provenance with entity-activity-agent relationships, processing lineage and derivation paths",
  "evidence": "was_derived_from: 'Raw audio recordings of standardized acoustic tasks captured by the Bridge2AI-Voice tablet application, together with questionnaire and clinical data captured in REDCap, collected under the Bridge2AI Voice Data Acquisition protocol.' Entities: raw_data_sources gives WAV audio (Synapse syn72370534, controlled access) and REDCap exports; file_collections names the eleven derived outputs. Activities: preprocessing_strategies give the ordered transformation chain (mono conversion and 16 kHz resampling with Butterworth filter -> STFT spectrogram at 25 ms/10 ms/400-point -> Mel and MFCC -> sparc articulatory estimates at 50 Hz -> ppgs at 100 Hz -> openSMILE/Praat/parselmouth static features -> Whisper transcription), with cleaning_strategies giving the audit activity. Agents: b2aiprep 'version 3.0.0 generated this release', SenseLab, the data release team, and clinicians as labelling agents. Derivation path: related_datasets derives_from syn72370534 and is_new_version_of 10.13026/k81f-qr68; version_access, errata and updates give version lineage; missing_data_documentation gives patterns, causes and handling; splits records that none are predefined.",
  "quality_note": "Meets the 5 band on the textual route the rubric expressly permits. The lineage is complete in both directions: upstream to the named raw-audio and REDCap sources with their access regimes, and downstream to specific named output files, with the transforming software and its version identified for the orchestrating tool. Version-history elements (errata, updates, version_access) are present in addition to, not instead of, the derivation graph.",
  "semantic_analysis": "The lineage can be traversed file by file rather than only in the abstract, which is what distinguishes it from version history alone: file names encode their producing tool (torchaudio_*, sparc_*, ppgs) and each corresponding preprocessing_strategies entry supplies that tool's parameters, so a reader can reconstruct which activity produced which entity. Quality is carried through the same graph: audio_quality_metrics.tsv is itself released as a derived entity, and the reasons some entities are absent are stated (sensitive-record and free-speech exclusions, generation failures). The absence of a machine-readable PROV-O serialisation and of a top-level parent_datasets entry are noted as issues but do not reduce the score, since the rubric accepts complete textual lineage and the derivation targets are given as resolvable identifiers."
}
```

## VOICE_v8_rep2_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

The original Q19 awards 5 and explicitly accepts the entity-activity-agent relationships rendered as text, without penalizing the lack of PROV serialization or a populated parent_datasets field. Its own input identifies waveform and questionnaire origins, parameterized feature transformations using b2aiprep 3.0.0 and senselab, clinical and collection roles, and a release/correction history. The rationale therefore has no identified representation-dependent score limit. This inspection does not independently certify every feature-file derivation, completeness assertion, quality artifact or external source claim.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/VOICE_v8_rep2_r20_rating1_evaluation.json); SHA256 `8fd40a53387d47c13e2427e632d170075e200628c81a16c9b543c75b10853945`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Version access, errata, updates, source derivation, parent linkages, missing data documentation, split indicators and provenance graph representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Full lineage with entity, activity and agent relationships and derivation paths",
  "evidence": "was_derived_from: 'Raw voice, speech and respiratory audio recordings and questionnaire responses collected under the Bridge2AI Voice Data Acquisition protocol and exported from REDCap'. raw_sources: the same entities with access_url https://www.synapse.org/Synapse:syn72370534/ and the note that the release contains derived features only. related_datasets: derives_from syn72370534, is_new_version_of 10.13026/k81f-qr68, is_version_of the concept DOI. preprocessing_strategies: the activity chain from waveform standardisation through each feature extractor, with b2aiprep 3.0.0 and senselab as the executing software. data_collectors, creators and maintainers identify the human and institutional agents; machine_annotation_tools identifies the software agents. version_access, errata (three) and updates give the release lineage. missing_data_documentation gives patterns, causes and handling. cleaning_strategies gives the QC protocol and audio_quality_metrics.tsv ships quality metrics per recording. splits: users are directed to construct their own; notes confirms no recommended splits are supplied.",
  "quality_note": "This is more than version history. A reader can trace any released feature file back through a named tool with named parameters to a named source entity held at a named location, with the responsible agents identified at each step \u2014 the three PROV-O elements the rubric asks for, rendered as text, which it expressly permits.",
  "semantic_analysis": "Derivation is stated in the right direction and with the right scope: the release derives from the waveforms, the waveforms are not in it, and the BIDS conversion is attributed to the audio dataset rather than claimed here. Quality is evidenced by artefact (audio_quality_metrics.tsv, missingness tables) rather than assertion, and anomalies frankly records protocol drift, inter-site diagnostic variation and unaudited transcription. Nothing is machine-readable as a PROV graph, and parent_datasets is unpopulated with the linkage carried by related_datasets instead, but the lineage information itself is complete."
}
```

## VOICE_v8_rep3_r20_rating1

Recorded Q19: 5/5. Status: `not_flagged_by_this_inspection`.

The original Q19 awards 5 on the textual route and does not deduct for missing PROV-O serialization or parent_datasets. Its own input describes audio, questionnaire and clinical origins, parameterized transformations, clinical/collection actors and release history. The b2aiprep version 3.0.0 statement is supported in machine_annotation_tools.tool_descriptions and external_resources, rather than the cleaning_strategies field to which the rationale attributes that phrase. The graph-serialization remark is informational at this recorded score, so no representation-dependent score limit is identified. This focused inspection does not certify full artifact-level completeness, every citation location or external source truth.

Original output: [evaluation](../../data/evaluation_llm/rubric20_semantic/reference_2026-09-12_cborg_runtime/VOICE_v8_rep3_r20_rating1_evaluation.json); SHA256 `4f427e6db8b56700f4966fd2c1d53bfdbbe182792e5c5c8576e0e60781145b5f`.

Original Q19 object:

```json
{
  "id": 19,
  "name": "Data Integrity, Provenance Graph, and Quality",
  "applicable": true,
  "applicability_status": "always_applicable",
  "applicability_evidence": "",
  "description": "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, and provenance representation.",
  "score_type": "numeric",
  "score": 5,
  "max_score": 5,
  "score_label": "Complete lineage in text: entities, activities, agents and derivation paths",
  "evidence": "was_derived_from: 'Raw voice, speech, breath and cough audio recordings, together with questionnaire responses retrieved from ReproSchema-UI or exported from REDCap, collected prospectively from consented participants'. raw_data_sources: three sources typed as primary prospective collection, electronic data capture and retrospective EHR extraction, each with format and access route. related_datasets.derives_from names the upstream controlled-access raw audio collection (Synapse syn72370534) and its BIDS 1.9.0 layout; is_new_version_of names the Health Data Nexus v1.0 (doi 10.57764/qb6h-em84). Activities and agents: preprocessing_strategies give the transformation chain and cleaning_strategies name the executing toolkits with 'this release was generated with b2aiprep version 3.0.0'; labeling_strategies name the clinician agents. version_access, errata and updates supply the release-to-release lineage with per-version DOIs. missing_data_documentation gives patterns, causes and handling; anomalies record reprocessing events and per-feature count variation; subsets carry is_data_split false and splits explains that no predefined splits are provided.",
  "quality_note": "Scored 5 because the lineage is complete in the text form the rubric explicitly permits: source entities (WAV audio, REDCap exports), processing activities with parameters, responsible agents (consortium, site clinicians, b2aiprep/SenseLab), and an end-to-end derivation path from raw collection through a versioned pipeline to a version-pinned PhysioNet release. Quality control is documented alongside provenance via the audit protocol and the new per-recording audio quality metrics file.",
  "semantic_analysis": "No formal W3C PROV-O serialisation is present and parent_datasets is empty, so the graph must be reconstructed from several fields rather than read from one - a machine-readability gap recorded as a completeness issue. The lineage is nonetheless internally consistent: withheld free-speech-derived features appear identically in the deidentification account, the limitations and the missing-data causes, so the derivation story does not contradict itself at any point."
}
```
