```markdown
# CM4AI D4D Reconciliation Report

**Version label:** 2026-08-13_claude-opus-5-api-generic-v4_rep3
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
**Full record:** `data/d4d_concatenated/claudecode_agent/2026-08-13_claude-opus-5-api-generic-v4_rep3/CM4AI_d4d.yaml`
**Core record:** `data/d4d_concatenated/claudecode_agent_core/2026-08-13_claude-opus-5-api-generic-v4_rep3/CM4AI_d4d_core.yaml`
**Phase 4 completed:** yes

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle contains material at two scopes: the CM4AI project as a programme (NIH RePORTER project page, cm4ai.org portal, the 2024 bioRxiv preprint describing goals and modules) and four discrete quarterly Dataverse releases with distinct DOIs.

**Decision: the referent is the June 2026 Data Release (`doi:10.18130/V3/HIGT4C`), the most recent release in the bundle.** This is the only scope for which the bundle supplies a DOI, a file manifest with checksums, a license, a publisher, a version, and an explicit statement of contents. Project-level material is retained only where it describes the release's provenance (funders, purposes, collection mechanisms) or its relationships (`related_datasets` to prior releases).

The audit correctly identified that the pre-reconciliation records oscillated between these two scopes. Section 3.2 records what was done about it.

---

## 2. Audit findings accepted and corrected

### 2.1 `distributions` block removed from the core record — HIGH

**Finding:** the core record emitted a `distributions` slot containing ten objects with keys `path`, `format`, `media_type`, `compression`, `md5`, `notes`, `conforms_to_standard`. No such slot appears in the schema digest's 98-slot inventory for `Dataset`/`CoreDataset`, and `md5` and `path` are not attested keys on any listed range class.

**Action:** the `distributions` block was removed from the core record in its entirety. The file-level content it carried (names, formats, sizes, MD5 checksums) is bundle-supported and has been redirected:

- File names, formats and per-file descriptions are retained in the full record's `file_collections`, whose `FileCollection` range does accept `path`, `file_count` and `total_bytes` per the digest.
- MD5 checksums have no attested home in either schema. They are not restated in `notes`; a checksum list is file-level metadata that the schema does not model, and inventing a key for it would be a worse defect than omitting it. This is disclosed in `source_caveats`.
- `compression` is now emitted only as the top-level `Dataset`/`CoreDataset` slot with value `zip`, which is a permitted `CompressionEnum` value and is supported by every archive in the release being a `.zip`.

**Rationale:** a slot absent from the digest cannot be validated and may fail outright. Populating it would have produced a record that reads well and does not load.

### 2.2 Grant `name` field unpacked — HIGH

**Finding:** `funders[0].grants[0].name` carried `'(1OT2OD032742-01; core project OT2OD032742; award 3OT2OD032742-01S2 for fiscal year 2025, USD 5,289,382)'` — three identifiers and a dollar amount embedded in a name string.

**Action:** the `name` value now carries only the grant title, `Bridge2AI: Cell Maps for AI (CM4AI) Data Generation Project`, which is the title the NIH RePORTER page states. The grant `id` carries the single identifier the cm4ai.org portal and Dataverse funding field both cite, `1OT2OD032742-01`. The supplementary award number, core project number, fiscal year and award amount — all of which are bundle-supported but none of which are a name — moved to `funders[0].grants[0].notes`, and the fact that three distinct grant numbers appear across sources moved to `funders[0].source_caveats`.

**Rationale:** the evidence boundary is explicit that identifier and amount content does not belong inside a name value, and that source commentary belongs in `source_caveats`.

### 2.3 Pipeline-vs-release mismatch resolved — MEDIUM

**Finding:** `preprocessing_strategies` (four objects), `labeling_strategies` (two objects), `machine_annotation_tools`, and `acquisition_methods[2].was_validated_verified` all described the MuSIC embedding / co-embedding / community-detection / GO-alignment / LLM-naming pipeline. The bundle states without qualification: *"Computed cell maps not included in this release."*

**Action:**

- `preprocessing_strategies` reduced to the steps the bundle attests were applied to the *released* data: DIA-NN-style search and protein-level quantification for the SEC-MS and AP-MS outputs, and the CRISPRi guide-assignment and expression-matrix generation for perturb-seq. The four MuSIC-pipeline objects were removed.
- `labeling_strategies` removed entirely. Both objects described annotation of cell-map assemblies; no assemblies are in this release.
- `machine_annotation_tools` removed for the same reason (GPT-4 assembly naming operates on maps).
- `acquisition_methods[2].was_validated_verified` set to `false` and the validation prose removed from `acquisition_details`. The GO/Reactome alignment and LLM-confidence scoring it cited apply to map outputs that this release does not contain.
- The existence of the MuSIC pipeline as a downstream CM4AI component is retained once, in `notes`, framed explicitly as a project capability whose outputs are absent here.

**Rationale:** these slots describe operations performed on the dataset being documented. Describing a pipeline that has not been run over the released artefacts populates the slots with content that is true of the project and false of the record's referent.

### 2.4 Collection timeframe corrected — MEDIUM

**Finding:** `collection_timeframes[0]` carried `start_date: 2022-09-01` / `end_date: 2026-08-31`, transcribed from the NIH RePORTER project period. An award window is not a collection window, and the bundle states no collection dates.

**Action:** `start_date` and `end_date` removed. The object retains `timeframe_details` describing what the bundle actually supports — that the release notes commit to quarterly updates through project end, and that Dataverse records a data creation date of 2025-02-27 and per-file publication dates from 2026-06-17 to 2026-07-15. `source_caveats` on the object now states plainly that no data collection start or end date is attested anywhere in the bundle and that the NIH award period was **not** used as a substitute.

### 2.5 `regulatory_restrictions.hipaa_compliant` populated — MEDIUM

**Finding:** the slot was omitted despite `not_applicable` being a permitted enum value directly supported by the bundle (Human Subjects: No; de-identified samples; commercially available cell lines; non-clinical origin).

**Action:** set to `not_applicable`.

### 2.6 `regulatory_restrictions.confidentiality_level` corrected — LOW→MEDIUM

**Finding:** `unrestricted` overstated openness against a CC BY-NC-SA license with a commercial-use bar, a named Data Access Committee, and embargoed perturb-seq components.

**Action:** changed to `restricted`. `notes` on the object records the three specific constraints (non-commercial clause, Data Access Committee supervision of dual licensing, temporary pre-publication embargo on two perturb-seq deposits).

### 2.7 Full/core asymmetries closed — MEDIUM

**Finding:** `relationships`, `file_collections`, `total_file_count`, `citation`, `subsets`, `third_party_sharing` and `direct_collection` were present in the full record and absent from the core; `citation` had been relocated into core `notes` as prose.

**Action:** every one of these slots appears in the schema digest's inventory and is therefore admissible on `CoreDataset` under the digest as supplied.

- `citation` restored to the core record as a structured slot; the citation prose removed from core `notes`.
- `third_party_sharing`, `direct_collection` and `total_file_count` added to the core record, matching the full record.
- `file_collections` and `relationships` deliberately **not** added to core — see §3.3.
- `subsets` — see §3.4.

### 2.8 Creator list expanded — MEDIUM

**Finding:** sixteen `Creator` objects were emitted against approximately forty-six named contributors with ORCIDs and affiliations in the Dataverse author list. Subsetting without a bundle-stated selection rule is an editorial reduction of clearly-supported evidence.

**Action:** all contributors named in the June 2026 Dataverse author list are now emitted, one `Creator` per named person, each with `id` (ORCID where the bundle supplies one), `name`, and `affiliations`. Where the bundle gives no ORCID (Axelsson, Chinn, Fall, Johannesson, Khaliq, Muralidharan, Pan, Polacco, Zhang) the `id` is omitted rather than minted — see §2.10.

### 2.9 Sali affiliation conflict represented on both sides — MEDIUM

**Finding:** the Sali `Creator` carried a `source_caveats` disclosing an affiliation conflict, then resolved it silently by emitting only one affiliation.

**Action:** both Organization objects are now listed in `affiliations` — UCSF (as stated in the Nature 2025 author affiliations and the bioRxiv preprint) and UCSD (as stated in the Dataverse author list for this release). The `source_caveats` retained and reworded to state that the sources disagree and that both are recorded rather than one being selected.

### 2.10 Minted identifiers removed — LOW

**Finding:** roughly thirty `urn:cm4ai:creator:*`, `urn:cm4ai:org:*`, `urn:cm4ai:subset:*`, `urn:cm4ai:filecollection:*`, `urn:nih:grant:*` and `urn:uva:grant:*` identifiers appear nowhere in the bundle.

**Action:** distinguished by whether the schema requires the key.

- **Removed where optional.** `Creator.id` and `Organization.id` are optional; minted URNs deleted. Creators with ORCIDs in the bundle now carry the ORCID as `id`; those without carry `name` and `affiliations` only. Organizations carry `name` only.
- **Retained where required.** `id` is a required key on `DataSubset` and `FileCollection`. These now use a documented local-identifier convention rooted in the release DOI (`doi:10.18130/V3/HIGT4C#subset-<condition>`, `doi:10.18130/V3/HIGT4C#files-<group>`) so the identifier is at least derived from an attested persistent identifier rather than invented wholesale. `source_caveats` at dataset level discloses that these fragment identifiers are constructed for this record and are not minted by the data provider.
- Grant `id` now carries the bundle-attested award number `1OT2OD032742-01` rather than a URN wrapper.

### 2.11 Transcription commentary moved out of content fields — LOW

**Finding:** inline source commentary in `is_deidentified.deidentification_details` (*"The June 2026 release records De-identified Samples: Yes."*), `human_subject_research.regulatory_compliance` (*"The release records Human Subjects: No and FDA Regulated: No"*), and `confidential_elements[0].confidentiality_details` (*"All files in the release are marked File Access: Public"*).

**Action:** all three fragments moved to `source_caveats` on their respective objects. The content fields now carry substantive statements about the data rather than statements about what a Dataverse UI field said.

### 2.12 `instances[0].counts` removed — MEDIUM

**Finding:** `counts: 53788` on the immunofluorescence instance is the cm4ai.org portal's project-wide image tally, not a count for this release.

**Action:** `counts` removed from that instance. The 53,788 figure, along with the portal's other project-wide statistics (1,374 protein interactions; 7,023 proteins investigated; 11,739 genes targeted; 21.4 TB), moved to `notes` in a single sentence explicitly labelled as project-cumulative and out of scope for this release. The one count the bundle does state per-release — 464 proteins imaged per condition — is retained on the instance.

### 2.13 `related_datasets` relationship types corrected — MEDIUM

**Finding:** all three prior releases were typed `is_new_version_of`, flattening a version chain.

**Action:** the immediately preceding release (October 2025, `doi:10.18130/V3/K7TGEM`) retains `is_new_version_of`. The June 2025 and March 2025 releases are retyped `continues`, which the digest permits and which correctly describes non-adjacent links in a release series without asserting direct supersession.

### 2.14 `distribution_dates[0].release_dates` value shape — MEDIUM

**Finding:** `'May 2024'` sat alongside ISO dates in the same multivalued slot.

**Action:** `'May 2024'` retained as the value the bundle states — the source gives no day-precision date for that release and fabricating `2024-05-01` would be worse — but moved into a `notes` annotation on the object explaining the mixed precision, with `source_caveats` recording that the May 2024 release date is attested only to month precision. The ISO-dated entries are unchanged.

### 2.15 `errata[0].erratum_url` removed — LOW

**Finding:** the URL pointed to the June 2025 release DOI, which resolves to the corrected dataset, not to an erratum notice. No erratum document exists in the bundle.

**Action:** `erratum_url` removed. `erratum_details` retains the correction description transcribed from the June 2025 record's own text (RGB immunofluorescent images added, RO-Crate metadata corrected, naming conventions changed).

### 2.16 `subsets` flags corrected — MEDIUM

**Finding:** seven `DataSubset` objects each carried `is_data_split: false` and `is_subpopulation: false`, asserting they were neither and leaving their status unexplained.

**Action:** both flags removed from all seven objects. Each retains `id`, `name` and `description` identifying the cell line / treatment / differentiation-state arm it represents. The digest makes both flags optional; omitting them is more honest than asserting a double negative. `source_caveats` at dataset level notes that these are experimental condition arms, not statistical partitions.

### 2.17 `known_biases[1].mitigation_strategy` softened — MEDIUM

**Finding:** the claim that proteome-wide SEC-MS and genome-scale CRISPRi "broaden coverage beyond the targeted panel" as mitigation for selection bias sits against the record's own limitation that the three modalities interrogate incompletely overlapping protein sets.

**Action:** reworded to state what the bundle supports — that SEC-MS is proteome-wide and the KOLF2.1J CRISPRi screen is genome-scale (11,739 genes), while noting in the same field that this does not produce matched coverage across modalities and that the incomplete overlap is recorded under `known_limitations`.

### 2.18 `existing_uses[0].examples` scoped — LOW

**Finding:** '38 participants registered' describes CodeFest attendance, not dataset use.

**Action:** the attendance figure moved to `notes` on the object. `examples` now carries only the use claim the bundle supports: that CodeFest participants were given the data with tutorials explaining derivation and integration, together with production-ready software.

### 2.19 `data_governance.accountable_organization` qualified — MEDIUM

**Finding:** UCSD asserted as accountable organization; the bundle names a UCSD-affiliated governance contact but never states which organization is accountable over time.

**Action:** `accountable_organization` removed. `committee_contact` (Jillian Parker, jillianparker@health.ucsd.edu) and `stewardship_roles` are retained as directly attested. `source_caveats` records that the bundle names a UCSD governance contact but does not designate an accountable organization, and that copyright is variously held by the Regents of the University of California, Stanford, and UCSF while the deposit is hosted by the University of Virginia.

### 2.20 `ethical_reviews.reviewing_organization` corrected — MEDIUM

**Finding:** the field named the contacts' employing institutions (The Hastings Center, Simon Fraser University) as reviewing organizations. The bundle names Ravitsky and Bélisle-Pipon as ethical review *contacts*; it attests no IRB, no ethics committee, no approval number, and the record itself sets `involves_human_subjects: false`.

**Action:** `reviewing_organization` removed from both objects. `contact_person` retained on both. `review_details` reworded to state that the release designates these two individuals as ethical review contacts and that no institutional review board approval is recorded, consistent with the release's declaration that the work does not involve human subjects.

### 2.21 `external_resources[*].archival` narrowed — LOW

**Finding:** `archival: true` asserted for MassIVE, NCBI SRA, Figshare and LibraData; only the LibraData claim is explicit in the bundle.

**Action:** `archival: true` retained for the LibraData / University of Virginia Dataverse entry, which the bundle states is under long-term preservation with committed institutional funds. Removed from the MassIVE, SRA and Figshare entries, where the bundle records deposit but makes no preservation guarantee.

### 2.22 `external_resources[9]` (Nature 2025 U2OS study) trimmed — LOW

**Finding:** the entry carried a full paragraph summarising the U2OS study's findings, reading as imported out-of-scope content.

**Action:** reduced to a reference: title, DOI, and a one-clause statement that it reports a U2OS cell map produced by the same investigators using the same MuSIC methodology on a different cell line and different data, and that none of its findings describe this dataset. The portal and NDEx URLs retained. The pre-existing `source_caveats` policing the U2OS boundary is unchanged and remains the record's strongest provenance control.

### 2.23 `description` de-duplicated — MEDIUM

**Finding:** three of four paragraphs restated content already held in `purposes`, `collection_mechanisms`, `preprocessing_strategies` and `conforms_to`.

**Action:** `description` reduced to what the structured slots cannot hold: a statement of what the June 2026 release contains, by modality and cell-line condition, and its position as one in a series of quarterly beta releases. Project scope moved to / retained in `purposes`; assay descriptions retained in `collection_mechanisms`; packaging retained in `conforms_to` and `conforms_to_standard`.

### 2.24 `was_derived_from` — LOW

**Finding:** a prose sentence naming two cell lines with RRIDs packed into a string-ranged slot.

**Action:** `was_derived_from` set to the single most specific resource reference the bundle supports for the primary source material, `RRID:CVCL_0419` (MDA-MB-468). The KOLF2.1J line (`RRID:CVCL_B5P3`), its HipSci provenance and its donor description moved to `raw_data_sources`, which is multivalued and whose `RawDataSource` range takes `source_description` — the correct home for both lines. `source_caveats` notes that the release draws on two cell lines and that the scalar slot admits one.

### 2.25 `source_caveats` gaps closed — MEDIUM

**Action:** the dataset-level `source_caveats` now additionally records:

- that no data collection start or end date is attested and the NIH award period was not substituted for one;
- that the MuSIC pipeline described in the project literature has not been applied to the artefacts in this release, and that computed cell maps are absent;
- that `DataSubset` and `FileCollection` identifiers are locally constructed fragments of the release DOI;
- that MD5 checksums present in the source have no schema home and are not carried.

---

## 3. Findings acknowledged but not acted on, with reasons

### 3.1 `instances[2].data_topic` — Protein vs. Proteome split (LOW)

Left as-is. `B2AI_TOPIC:26` (Protein) for the AP-MS bait-prey instance and `B2AI_TOPIC:28` (Proteome) for SEC-MS is an editorial distinction the bundle does not draw, as the audit says. But AP-MS in this release targets a defined bait set (tagged genes in MDA-MB-468) while SEC-MS is described in the bundle as proteome-wide complex mapping. The distinction tracks a real difference the bundle does state, even if it does not label it. Harmonising both to one term would lose information; the alternative reading is disclosed in `source_caveats`.

### 3.2 Residual project-vs-release scope in `purposes`, `addressing_gaps`, `tasks`, `funders` (MEDIUM)

Partially acted on, deliberately not fully. `description` and `notes` were rescoped (§2.23, §2.12) and pipeline content removed (§2.3). But `purposes`, `addressing_gaps`, `tasks` and `funders` are retained at project scope, because the questions these slots ask — why was this created, what gap does it fill, what tasks does it support, who paid — have no release-specific answer in the bundle. The June 2026 release was created because CM4AI commits to quarterly releases; its purpose is CM4AI's purpose. Scoping these down would require inventing release-specific motivations. The dataset-level `source_caveats` states that these four slots answer at project scope.

### 3.3 `file_collections` and `relationships` still absent from core (MEDIUM)

Acknowledged as an asymmetry; retained deliberately. Both were reviewed against the digest and both are admissible. They were left out of the core record on the reading that the core/full distinction is a granularity distinction: `file_collections` is a per-file manifest and `relationships` describes inter-instance graph structure, and both are the kind of detail a core record exists to omit. This is a judgement call and it is recorded here as such rather than presented as forced. `citation`, `total_file_count`, `third_party_sharing` and `direct_collection` were restored (§2.7) because each is a single scalar or short object answering a question a core record should answer.

Note that `relationships` in the full record describes the cell-map DAG — assemblies as nodes, containment as edges. Given §2.3, this is now the one remaining slot in the full record describing map structure absent from the release. It is retained because the DAG structure is a property of what the project produces from these inputs and the slot is the correct home for it, but its `notes` now state that no such graph ships in this release.

### 3.4 `subsets` still absent from core (MEDIUM)

Same reasoning as §3.3. The seven condition arms are equally supported for both records. They are retained in full and omitted from core as a granularity decision. The four modalities and the treatment/differentiation conditions are named in the core `description`, so the core reader is not left unaware that the release is stratified.

### 3.5 `anomalies` still omitted (MEDIUM)

The audit flags the 563→464 protein-count change between March 2025 and June 2025 IF images as a candidate `DataAnomaly`. Left omitted. The bundle presents this as a change between releases, not as an error, irregularity or quality issue in the June 2026 data — and the June 2025 record's own description characterises that release as a revision adding RGB images and correcting metadata, not as a correction to protein coverage. Recording a version difference as an anomaly would assert a defect the bundle does not assert. The count change remains disclosed in `source_caveats` and in `errata`, which is where a between-version change belongs.

### 3.6 `download_url` still omitted (MEDIUM)

Left omitted. The Dataverse Data Access API base `https://dataverse.lib.virginia.edu/api/access/datafile/` is a template requiring a per-file numeric id that the bundle never supplies. It is not a URL from which the data can be downloaded. `page` carries the landing page, which is the correct slot for the access route the bundle does supply.

### 3.7 `conforms_to` / `conforms_to_standard` = RO-Crate (MEDIUM)

Left as-is. The audit is right that RO-Crate packaging is closer to a metadata-packaging statement than a content standard. But `RO_CRATE` is an explicit member of `DataStandardEnum`, which means the schema authors contemplated exactly this case, and the bundle states that CM4AI outputs are "packaged with provenance graphs and rich metadata as AI-ready datasets in RO-Crate format." Placing it in `conforms_to_schema` would be wrong — that slot is reserved for the schema this datasheet is written in. The paired `conforms_to` prose was trimmed to name RO-Crate and its JSON-LD/EVI/ARK components without the surrounding explanation, which moved to `notes`.

### 3.8 `created_on` and `last_updated_on` (LOW)

Left as-is with disclosure. `created_on: 2025-02-27T00:00:00Z` is the Dataverse Data Creation Date and Deposit Date for the record, carried forward unchanged from the March 2025 deposit; `last_updated_on: 2026-07-15T00:00:00Z` is the publication date of the three IF image files, the latest per-file date in the June 2026 record. Both are accurately transcribed and both are the only dates of their kind the bundle offers. `source_caveats` records that the creation date predates the June 2026 release by sixteen months and that the update date is a per-file rather than dataset-level timestamp.

### 3.9 `publisher` as repository URL (LOW)

Left as-is. Range is `uriorcurie`; `https://dataverse.lib.virginia.edu/` resolves, is stable, and identifies the publishing venue the bundle names. No organizational identifier (ROR, etc.) for University of Virginia Dataverse appears in the bundle.

### 3.10 `subpopulations[0]` (LOW)

Left as-is with the boolean retained. The audit is right that cell-line donor demographics are not a subpopulation structure *within* the data in the sense the slot primarily intends. But the bundle states donor characteristics for both lines (51-year-old Black female, metastatic mammary adenocarcinoma; healthy male Northern European donor) and explicitly connects them to representativeness in `Potential Sources of Bias`. There is no better home in the schema, and omitting the only demographic information the bundle supplies — on a dataset whose own release notes flag population representativeness as a limitation — would suppress relevant evidence. `notes` on the object states that these describe source cell-line donors rather than partitions of the released data.

### 3.11 `status: beta` (LOW)

Left as-is. Range is string, not enum. Every release in the bundle is titled "(Beta)". `beta` is the value the source states.

### 3.12 `license` as label rather than URL (LOW)

Left as-is. `CC BY-NC-SA 4.0` is verbatim from the Dataverse License/Data Use Agreement field. The canonical URL is carried in `license_and_use_terms.license_terms`, so the resolvable form is present in the record.

### 3.13 `existing_uses[1]` (Nourreddine et al.) (MEDIUM)

Left as-is with tightened caveat. The audit is right that this describes the atlas dataset's own validation rather than third-party use, and that the preprint's full text is not in the bundle. But the March 2025 Dataverse abstract — which *is* in the bundle — states the validation, and the June 2026 record lists the preprint under Related Publication. The entry is retained as an existing use with `source_caveats` stating that the claim is transcribed from the Dataverse abstract, not from the preprint, and that it describes validation of the atlas rather than downstream reuse.

### 3.14 Correct omissions confirmed

The following were reviewed and confirmed correctly omitted from both records, on the grounds that the bundle attests `involves_human_subjects: false`, de-identified commercially-available cell lines, and no content of the relevant kind: `collection_consents`, `collection_notifications`, `consent_revocations`, `informed_consent`, `participant_privacy`, `participant_compensation`, `at_risk_populations`, `data_protection_impacts`, `content_warnings`, `splits`, `use_repository`, `variables`, `annotation_analyses`, `imputation_protocols`, `raw_sources` (superseded by `raw_data_sources`), `discouraged_uses` (the bundle states prohibitions, which are in `prohibited_uses`, and no separate discouragements), `total_size_bytes` (per-file sizes are rounded in the source; summing them would fabricate precision — disclosed in `source_caveats`).

---

## 4. Provenance controls verified

- No previously generated D4D record was read, opened, grepped or consulted at any phase.
- Every populated slot traces to the declared bundle. No external knowledge of CM4AI, Bridge2AI, the cell lines, the assays or the publications was introduced.
- The Nature 2025 U2OS study is present in the bundle and is the single largest source document by size. **No U2OS finding, protein count, assembly count, structural model, cancer analysis or portal statistic is attributed to this dataset.** The U2OS study is referenced once, as an external resource, with an explicit non-attribution statement. This boundary is restated in dataset-level `source_caveats`.
- Both header blocks were written verbatim as specified. The core header carries `# Sources:` naming both the bundle and the full record, and `# Phase 4 reconciliation: completed`, written only after this phase ran.
- Live provenance recorded via `d4d provenance record`.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Populated top-level slots | 61 | 44 |
| Slots changed in Phase 4 | 24 | 26 |
| Slots removed in Phase 4 | 5 | 6 |
| Slots added in Phase 4 | 1 | 5 |
| `linkml-validate` | pass | pass |

**Net effect of reconciliation:** one HIGH-severity validation risk eliminated (the unattested `distributions` block), one HIGH-severity shape defect corrected (identifiers and amount embedded in a grant name), and the record's largest substantive misalignment resolved — the removal of seven objects across four slots describing a cell-map construction pipeline whose outputs the bundle states are not in this release. Thirty creators restored. Five inferences beyond the evidence withdrawn (award period as collection period, single accountable organization, institutional ethical review, blanket archival guarantees, `unrestricted` confidentiality). Roughly thirty minted identifiers removed or re-rooted in the release DOI. Full/core asymmetry reduced from seven slots to three, each of the remaining three recorded here as a deliberate granularity judgement rather than an oversight.

The pre-reconciliation records contained no fabricated dataset facts, and the dataset-level `source_caveats` was already policing the U2OS boundary correctly. The defects were of scope, shape and inference rather than invention.
```