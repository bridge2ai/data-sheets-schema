# Reconciliation Report — CHoRUS

Version label: `2026-09-04f_claude-opus-5-api-generic-v8_rep2`
Records reconciled: full (`CHORUS_d4d.yaml`) and core (`CHORUS_d4d_core.yaml`)

## What the audit found

The Phase 3 audit returned fourteen findings against the full record, none of them high severity: five medium and nine low. No enum violations, no scalar/object range violations and no invented identifiers were reported, and the record's central factual spine — 14 contributing hospitals within 20 academic centers, 9 modalities under controlled access, 50,000 released admissions with the webinar's 45K figure disclosed as a ranked disagreement, 1.6 billion OMOP rows, 7,642 admissions with radiology, 23 Tb of waveforms, the OMOP/DICOM/WFDB/EDF+/OHNLP standards, and NIH award OT2OD032701 to Massachusetts General Hospital — was found well supported and correctly attributed.

The medium findings clustered into four kinds: unsupported inference from adjacent evidence (CTP-deid characterized as imaging de-identification tooling; an affiliation inferred from an email domain), an internal inconsistency between the record's own caveat and its per-subset schema claims, a plan written as a current state (the Cohort 2 training program), and a neighbouring-field placement (community engagement and legal analysis recorded as an institutional ethical review, under a workstream named as a reviewing organization). A sixth finding, on `labeling_strategies`, was of the same plan-as-state kind.

The low findings concerned shape and placement rather than fact: entity collapse in `maintainers`, resource URLs held in prose rather than in the class's own pointer field, narrative prose in `status`, a source-page observation in `notes`, an unflagged expansion of an approximate count, a supported boolean omitted from `is_deidentified`, a cross-source bridge in the geocoding preprocessing entry, two `distribution_formats` entries naming standards rather than delivery formats, and asymmetric structuring of the two access contacts.

## Changes made

### Medium findings

**`preprocessing_strategies[2].preprocessing_details` — changed (both).** The parenthetical attributing imaging de-identification to CTP-deid was removed. The entry now reads "Transformation of data using approaches that limit re-identification; imaging de-identification was in process for the larger cohort as of September 2025." The bundle lists `CTP-deid Public` in the repository roster with no description and no stated role, so the attribution was inference; the attested claim about limiting re-identification and the attested September 2025 status are retained. The reference to CTP-deid was likewise dropped from `is_deidentified.method`, which had carried "supported by a CTP-based de-identification repository". The repository name survives only in the neutral repository roster inside `external_resources[1].description`, where the bundle does list it.

**`data_governance.committee_contact.affiliation` — removed (both).** The `Tufts Medicine` affiliation object was deleted. The bundle names Jared Houghtaling as a webinar lecturer under host "Tufts" and gives his email address; it never states his organization, and deriving one from the email domain is inference. The `id`, `name` and `email` remain.

**`subsets[*].conforms_to` and `subsets[*].description` — changed (full).** The per-modality metadata-schema claims reconstructed from the interleaved webinar table were withdrawn from all nine subsets. Specifically: `#subset-nursing-flowsheets` `conforms_to` changed from "OMOP Common Data Model with extensions" to "OMOP Common Data Model"; `#subset-clinical-notes` from "OHNLP open source schema" to "OHNLP"; `#subset-waveform-telemetry` from "WFDB, PhysioNet schema extended" to "WFDB". The phrases "with a published metadata schema", "with a published OMOP metadata schema", "with a published DICOM metadata schema", "described as the PhysioNet schema extended" and "described as the open source EDF+ and Persyst schema" were removed from the several `description` fields. Each subset now carries only the table's unambiguous Data standard column. The corresponding extended-schema phrasing was also removed from the top-level `conforms_to`, from `raw_data_sources[3].raw_data_format` (now plain "WFDB.") and from `distribution_formats` notes, so that the record no longer asserts the reconstruction anywhere. `source_caveats` was extended to say that the table has both a Metadata status column and a schema column, that neither can be reliably assigned to individual data types, and that only the Data standard column is used.

**`existing_uses[1]` — removed from `existing_uses`, added to `intended_uses[2]` (both).** The Cohort 2 training program was moved. `existing_uses` now holds a single entry, the attested "The datasets are being used for training activities and publications." The program is restated in the source's own tense as a second example under `intended_uses` `use_category: Education and workforce development`: "announced Cohort 2 in a September 2025 informational webinar: up to 30 trainees were to be selected, with notice of award on 10 November 2025 and the program running from 17 November 2025 to 31 July 2026, and would receive hands-on training…". A `usage_notes` was added recording that at source time the deadline had not passed and no trainees had been selected. The `third_party_sharing[0].notes` clause "including by trainees in the AIM-AHEAD Bridge2AI for Clinical Care Training Program" was also removed, since it asserted the same use as current.

**`ethical_reviews[0].reviewing_organization` — removed (both).** The value "CHoRUS Ethics pillar (Ethical and Trustworthy AI)" was deleted; the workstream is not a reviewing body. `review_details` was trimmed to the two attested ethics activities (community-facing focus groups on what data is appropriate for public sharing; evaluation of community perspectives to increase trustworthiness of provenance and privacy), and the legal-framework clause was dropped from this entry. A `source_caveats` was added stating that the bundle names no IRB, ethics committee or compliance certification and that no reviewing organization is asserted. The legal and regulatory landscape analysis remains in `regulatory_restrictions.regulatory_restrictions` and in `future_use_impacts[1]`, where it was already carried.

**`labeling_strategies` — removed (both).** The slot was deleted in full. Its single entry described a planned visualization and annotation environment rather than any labeling procedure applied to the data. The same forward-looking statement is carried by `purposes` ("…acquire, standardize, tokenize, store, visualize and label…").

### Low findings

**`maintainers` — changed (both).** The consortium entry was reduced to the consortium alone. A new second `Maintainer` was added for Ciera McCrary, Program Manager, MGH, with the published address `cmccrary@mgh.havard.edu` in `maintainer_details` and the transcription note about the apparent typographic domain error moved to that object's `source_caveats`. The GitHub organization entry is unchanged and is now third.

**`external_resources[0..2]` — changed (both).** Each entry now carries its pointer in the class's own `external_resources` field (`https://chorus4ai.org/`, `https://github.com/chorus-ai`, `www.bridge2ai.org/chorus`) with `description` holding the characterization only. The URLs were removed from the descriptions.

**`status` — changed (both).** Reduced from the two-clause narrative to the single term `released`. The project-period narrative was folded into `description`, which now closes with "Data acquisition, standardization and modality expansion continue within the NIH project period 2022-09-01 through 2026-11-30." The dates remain in `funders[0].grants[0].description` as before.

**`notes` — removed (both).** The site-wide banner observation was deleted from `notes` and moved verbatim into `source_caveats`, where it now appears as a sentence about the source page's transcription. The `notes` slot is absent from both reconciled records.

**`instances[1].description` — changed (both).** The description now reads "Rows of EHR OMOP data in the current released dataset. The project website states the figure as \"1.6 Billion\"; the integer recorded here is that approximate magnitude expanded to units." The `counts` value of `1600000000` is unchanged; the rendering is now disclosed.

**`is_deidentified.identifiable_elements_present` — added (both).** Set to `true`, on the evidence that clinical note text remains stored locally at contributing sites (only tokens shared) and that imaging de-identification was in process as of September 2025. `deidentification_details` was extended with a sentence recording that identifiable source material remains at the contributing sites.

**`preprocessing_strategies[4].preprocessing_details` — changed (both).** The cross-source bridge was cut. The entry now states only the geocoding capability: "Geocoding of OMOP Location entities via DeGauss, using open source code maintained in the UF-Geocoding repository." The contextual-factor aim was moved to `purposes` as a fifth entry, in the abstract's own words ("To ensure that data elements feature appropriate contextual factors such as geographic distance to the nearest hospital"). The same bridge in `acquisition_methods[1].acquisition_details` was trimmed to "OMOP Location entities are geocoded with open source code via DeGauss."

**`distribution_formats` — changed (both).** The list was reordered so the three true format names (DICOM, WFDB, EDF+ and Persyst) come first. The two non-format entries were retained rather than dropped, but relabeled and caveated: `OMOP Common Data Model tables` became `OMOP Common Data Model` and `OHNLP tokenized clinical notes` became `OHNLP`, each carrying a `source_caveats` stating that the source names a data standard rather than a file format, media type or packaging, and that no delivery format is stated in the bundle. This is the second of the two repairs the audit offered.

**`data_governance.access_review_process` — retained, with a caveat added (both).** The prose is unchanged; a `source_caveats` was added to `data_governance` recording that the README lists two co-equal access addresses, that only one can be carried in the single-valued `committee_contact`, that the other is therefore held in prose, and that the README gives no name, role or organization for either address. This is the second repair the audit offered; the alternative (moving both to `committee_members`) would have required asserting committee membership the bundle does not state.

### Incidental correction

`distribution_dates[0].release_dates` was changed from a scalar string to a single-item list, matching the plural form of the field. This was not an audit finding.

## What was left as-is

No finding was left wholly unaddressed. Two were addressed by the audit's alternative repair rather than by deletion:

- **`distribution_formats[0].format`, `distribution_formats[1].format`** — the two standard-naming entries were kept and caveated rather than dropped, since `conforms_to` and `conforms_to_standard` carry the standards in term form while these entries carry the per-modality access notes that would otherwise be lost.
- **`data_governance.access_review_process`** — the asymmetry between the two access contacts was disclosed in `source_caveats` rather than resolved, because resolving it would require a claim about committee membership the bundle does not support.

The record's admission-count disagreement handling (50,000 from the higher-ranked website, 45K from the webinar, both disclosed) was not questioned by the audit and is unchanged. The `Dataset` referent remains the CHoRUS dataset itself — the multicenter critical care data collection described by the project website — rather than the NIH project or the training program; both records hold to that consistently.

## Core record

The core record was reprojected from the reconciled full record. Every change above that touches a slot the core schema declares is reflected there identically. Two changed slots have no core counterpart: `subsets` and `third_party_sharing` are not present in the core record, so the subset schema withdrawal and the training-program clause removal are full-record only. `labeling_strategies` was present in the original core record and is absent from the reconciled one. `notes` was present in the original core record and is absent from the reconciled one. The core header now carries `# Phase 4 reconciliation: completed`.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `preprocessing_strategies[2].preprocessing_details` | changed | both | CTP-deid attribution removed; bundle states no function for that repository |
| `is_deidentified.method` | changed | both | CTP reference dropped for the same reason |
| `data_governance.committee_contact.affiliation` | removed | both | affiliation inferred from an email domain, not stated |
| `subsets` | changed | full | per-modality metadata-schema reconstruction withdrawn; only the unambiguous Data standard column retained |
| `conforms_to` | changed | both | extended-schema phrasing withdrawn with the subset reconstruction |
| `raw_data_sources[3].raw_data_format` | changed | both | "extended PhysioNet schema" withdrawn; plain WFDB retained |
| `source_caveats` | changed | both | caveat extended to cover the schema column; site banner note relocated here |
| `existing_uses` | changed | both | reduced to the one attested current use |
| `intended_uses[2]` | changed | both | Cohort 2 program restated in the source's tense as an announced program |
| `third_party_sharing[0].notes` | changed | full | trainee-use clause removed as a plan written as current state |
| `ethical_reviews[0].reviewing_organization` | removed | both | a project workstream is not a reviewing body |
| `ethical_reviews[0].review_details` | changed | both | trimmed to attested ethics activity; legal analysis carried elsewhere |
| `ethical_reviews[0].source_caveats` | added | both | records that no IRB or ethics committee is named in the bundle |
| `labeling_strategies` | removed | both | held a planned annotation environment, not an applied labeling procedure |
| `maintainers[0].maintainer_details` | changed | both | reduced to the consortium alone after entity split |
| `maintainers[1]` | added | both | Ciera McCrary given her own Maintainer entry |
| `maintainers[1].source_caveats` | added | both | transcription note on the published address moved out of the details field |
| `external_resources` | changed | both | pointers moved from prose into the class's `external_resources` field |
| `status` | changed | both | reduced to a status term; narrative moved to `description` |
| `description` | changed | both | absorbed the project-period narrative from `status` |
| `notes` | removed | both | source-page observation relocated to `source_caveats` |
| `instances[1].description` | changed | both | discloses that the integer expands the website's "1.6 Billion" |
| `is_deidentified.identifiable_elements_present` | added | both | supported by local note storage and in-process imaging de-identification |
| `is_deidentified.deidentification_details` | changed | both | extended to state where identifiable material remains |
| `preprocessing_strategies[4].preprocessing_details` | changed | both | cross-source bridge cut; geocoding capability stated alone |
| `acquisition_methods[1].acquisition_details` | changed | both | same bridge removed |
| `purposes[4]` | added | both | contextual-factor aim restored to the slot where the abstract attests it |
| `distribution_formats` | changed | both | reordered; the two standard-naming entries relabeled and caveated |
| `data_governance.access_review_process` | retained | both | both contacts remain; asymmetry disclosed rather than resolved |
| `data_governance.source_caveats` | added | both | records the two co-equal contacts and the absent affiliation evidence |
| `distribution_dates[0].release_dates` | changed | both | scalar corrected to a single-item list |