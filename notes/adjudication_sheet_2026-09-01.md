# Adjudication sheet: 44 rater disagreements (2026-09-01)

For each item: the pack's question context, both verdicts with each rater's evidence, and where to verify. Rule items carry the rule text.


## CHORUS 2026-08-28_claude-opus-5-claudecode-generic-v6_rep1

- bundle: data/preprocessed/concatenated/CHORUS_preprocessed.txt
- full record: data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CHORUS_d4d.yaml
- core: data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep1/CHORUS_d4d_core.yaml


### [1] CHORUS/2026-08-28 slot-014 (slot_receipted)
- slot: `missing_data_documentation[0].missing_data_patterns`
- value: Missingness falls along modality lines rather than at random: the structured OMOP domains and telemetry are present in the enclave, whereas EEG, full clinical note text and the bulk of imaging are absent from it. Published metadata schemas were marked as planned rather than delivered for clinical no
- receipt: chunk c003 lines [55, 454] snippet: 'EEG – extraction in process at this point'
- RATER A: **misread** — line 254 'EEG – extraction in process at this point' supports the EEG clause, and lines 245-252 the enclave/local split; but the value's last sentence, 'Published metadata schemas were marked as planned rather than delivered for clinical notes, telemetry and EEG', reads the degraded table backwards: the 'Published metadata schema' column (line 326)
- RATER B: **supported** — the passage around the snippet (lines 245-254) states the modality-line pattern: OMOP and telemetry in enclave, notes stored locally except tokens, 1000 images with de-id in process, EEG extraction in process; the 'Planned' metadata-schema tokens sit at lines 324, 360, 372 adjacent to the notes/telemetry/EEG rows

### [2] CHORUS/2026-08-28 slot-020 (slot_receipted)
- slot: `updates.update_details`
- value: The released dataset is growing toward the anticipated final dataset of 100,000 patient admissions across 9 data modalities: EEG extraction was in process, and imaging de-identification was in process for a cohort larger than the 1000 images then available. Data contributing sites provide regular st
- receipt: chunk c007 lines [1113, 1512] snippet: 'We have asked data contributing sites to provide regular status updates with regard to their ... progress in creating and curating a CHoRUS-specific clinical da'
- RATER A: **weak** — lines 1323-1329 describe contributing sites reporting extract-creation status to the consortium via GitHub or a Google Form; that is progress tracking on data delivery, not the planned update types, responsible parties and user-facing communication that update_details asks for. The 'growing toward 100,000' sentence rests on lines 1066-1082 (Anticip
- RATER B: **supported** — lines 1323-1334 state the status-update mechanism (GitHub interface or Google Form, landing in the Standards or Data Acquisition Project); the growth clauses are at c006 lines 1065-1069 and c003 lines 251-254

### [3] CHORUS/2026-08-28 slot-022 (slot_receipted)
- slot: `sampling_strategies[0].strategies`
- value: Federated access will enable sampling methods to ensure a balanced and diverse cohort. The project samples to ensure comprehensive sets of patient conditions and clinical treatment strategies.
- receipt: chunk c007 lines [1113, 1512] snippet: 'Federated access will enable sampling methods to ensure a balanced and diverse cohort.'
- RATER A: **weak** — line 1220 'Federated access will enable sampling methods to ensure a balanced and diverse cohort' and line 45 'sampling to ensure comprehensive sets of patient conditions and clinical treatment strategies' are both real, but both are stated aims (future tense); neither names a sampling strategy used (deterministic, random, stratified...), which is 
- RATER B: **supported** — line 1220 states sentence one verbatim; line 45 'sampling to ensure comprehensive sets of patient conditions and clinical treatment strategies' supports sentence two

### [4] CHORUS/2026-08-28 slot-023 (slot_receipted)
- slot: `external_resources[0].description`
- value: The cloud enclave in which the dataset is held and analyzed. OMOP and telemetry data are held in the enclave; clinical notes are stored locally at the contributing sites, with only tokens in the enclave. The CHoRUS team creates tools to support the cloud enclave, including a set of dockerized contai
- receipt: chunk c004 lines [455, 854] snippet: 'leverage the data and tools to create practical use cases'
- receipt: chunk c007 lines [1113, 1512] snippet: 'Set of dockerized container applications and associated configurations to be deployed to support CHoRUS ... services on Azure'
- RATER A: **weak** — line 466 'leverage the data and tools to create practical use cases' is about trainees' training, and line 1395 describes container apps 'to support CHoRUS services on Azure'; neither says the Collaborative Cloud (lines 476, 493, 768) is the enclave (lines 245, 1085) or that the Azure apps are its tooling. The passages are on topic but the identifi
- RATER B: **supported** — lines 465-467 and 491-493 name the Collaborative Cloud and the training/use-case clauses; lines 1395-1396 the dockerized container apps on Azure; lines 245-247 the enclave/local-notes split; line 1085 the team's enclave tooling

### [5] CHORUS/2026-08-28 slot-037 (slot_receiptless)
- slot: `raw_data_sources[1].source_type`
- value: imaging archive
- RATER A: **bundle_supports** — line 346 'Imaging (from PACS)'; 'imaging archive' is the category label for a picture archiving and communication system, not a dataset fact beyond the line
- RATER B: **inferred** — line 346 'Imaging (from PACS)' is all the bundle states; classifying PACS as an 'imaging archive' relies on expanding an acronym the bundle never expands — it follows from the line but is not stated

### [6] CHORUS/2026-08-28 slot-050 (slot_receiptless)
- slot: `collection_timeframes[0].end_date`
- value: 2026-11-30
- RATER A: **inferred** — line 42 'Project end: 2026-11-30T00:00:00' is the award end; the bundle states no end date for data collection, so placing it in collection_timeframes[0].end_date follows from line 42 only by the same inference as slot-038
- RATER B: **bundle_supports** — line 42 'Project end: 2026-11-30T00:00:00' — the value is that date normalized

### [7] CHORUS/2026-08-28 rule-06 (rule)
- rule text: Populate a slot with the information the field asks for, not with a pointer to where that information lives, and not with a statement that it is pending or absent. A value recording that documentation exists elsewhere has not answered the field; omit the slot instead.
- RATER A: **violated** — preprocessing_strategies[1].description ('supported by published waveform documentation and conversion scripts in the organization's chorus_waveform and chorus_waveform_resources repositories') and collection_mechanisms[1].description ('Tooling to create and upload a CHoRUS data extract is published in the organization's repositories') record where
- RATER B: **followed** — no value records that documentation exists elsewhere or is pending in place of an answer; the license slot is omitted rather than filled with 'see the LICENSE file', with the scoping stated in license_and_use_terms.source_caveats

### [8] CHORUS/2026-08-28 rule-07 (rule)
- rule text: Read the slot's description before populating it. Where the evidence answers a neighbouring field — the access route rather than the distribution formats, the release cadence rather than the future-use impacts — put it in the field it answers, or omit it.
- RATER A: **violated** — status: 'under review for potential modification in compliance with Administration directives' — line 1044/1057 is a website banner ('This repoitory is under review...'), not the dataset's status (draft, published, deprecated) that the slot asks for; it answers nothing about the dataset
- RATER B: **followed** — fields answer their own questions; the two closest strains are defensible: collection_timeframes[0] carries the NIH award period but timeframe_details/source_caveats state exactly what the slot's description asks (whether the period matches the underlying data's creation — here unknown), and maintainers[0] records the project's named contact with t

## CHORUS 2026-08-28_claude-opus-5-claudecode-generic-v6_rep2

- bundle: data/preprocessed/concatenated/CHORUS_preprocessed.txt
- full record: data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CHORUS_d4d.yaml
- core: data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/CHORUS_d4d_core.yaml


### [9] CHORUS/2026-08-28 slot-005 (slot_receipted)
- slot: `creators[4]`
- value: {'id': 'https://chorus4ai.org/#creator-rashidi', 'name': 'Bridge2AI CHoRUS leadership team member', 'description': 'Listed on the Bridge2AI CHoRUS Leadership Team slide of the AIM-AHEAD cohort 2 informational webinar.', 'principal_investigator': 'Parisa Rashidi', 'affiliations': [{'name': 'Universit
- receipt: chunk c003 lines [55, 454] snippet: 'Parisa Rashidi...University of Florida'
- RATER A: **supported** — lines 171, 186–187 'Bridge2AI CHoRUS Leadership Team … Parisa Rashidi / University of Florida'; leadership of the data generation project answers 'key individual overseeing dataset creation' and the affiliation is stated
- RATER B: **weak** — Lines 186-187 ("Parisa Rashidi / University of Florida", under "Bridge2AI CHoRUS Leadership Team" at line 171) support the name, affiliation and leadership listing, and the entry's own name says "leadership team member". But the field populated is principal_investigator, whose description asks for "the key individual (Principal Investigator) respon

### [10] CHORUS/2026-08-28 slot-011 (slot_receipted)
- slot: `creators[5]`
- value: {'id': 'https://chorus4ai.org/#creator-kwong', 'name': 'Bridge2AI CHoRUS leadership team member', 'description': 'Listed on the Bridge2AI CHoRUS Leadership Team slide of the AIM-AHEAD cohort 2 informational webinar.', 'principal_investigator': 'Manlik Kwong', 'affiliations': [{'name': 'Tufts Univers
- receipt: chunk c003 lines [55, 454] snippet: 'Manlik Kwong...Tufts University'
- RATER A: **supported** — lines 189–190 'Manlik Kwong / Tufts University' on the Bridge2AI CHoRUS Leadership Team slide (171)
- RATER B: **weak** — Lines 189-190 ("Manlik Kwong / Tufts University", leadership team slide) support name, affiliation and leadership listing, but the principal_investigator field asks for the PI overseeing dataset creation and the bundle names only Rosenthal as PI (line 37). Same structural tension as slot-005.

### [11] CHORUS/2026-08-28 slot-022 (slot_receipted)
- slot: `creators[1]`
- value: {'id': 'https://chorus4ai.org/#creator-bihorac', 'name': 'Bridge2AI CHoRUS leadership team member', 'description': 'Listed on the Bridge2AI CHoRUS Leadership Team slide of the AIM-AHEAD cohort 2 informational webinar.', 'principal_investigator': 'Azra Bihorac', 'affiliations': [{'name': 'University 
- receipt: chunk c003 lines [55, 454] snippet: 'Azra Bihorac...University of Florida'
- RATER A: **supported** — lines 177–178 'Azra Bihorac / University of Florida' on the leadership team slide (171)
- RATER B: **weak** — Lines 177-178 ("Azra Bihorac / University of Florida", leadership team slide) support name, affiliation and leadership listing, but not PI status; the principal_investigator field asks for the PI and the bundle names only Rosenthal (line 37). Same structural tension as slot-005.

### [12] CHORUS/2026-08-28 slot-028 (slot_receiptless)
- slot: `third_party_sharing[0].name`
- value: Controlled sharing beyond the contributing institutions
- RATER A: **bundle_supports** — line 240 'Controlled access'; lines 215–216 the training program 'expands access to Bridge2AI CHoRUS data' to trainees from eligible organizations (861–879) — sharing beyond the contributing sites, under control
- RATER B: **inferred** — "Controlled" access is stated (line 240) and the training program "expands access to Bridge2AI CHoRUS data" to trainees (lines 215-217) from eligible outside organizations (lines 861-879), but no line states sharing "beyond the contributing institutions"; the name's distinctive claim follows from those lines rather than being stated. An inference t

### [13] CHORUS/2026-08-28 slot-041 (slot_receiptless)
- slot: `third_party_sharing[0].description`
- value: The project's overarching goal is a publicly available, AI-ready critical care dataset. Access is controlled and is extended beyond the contributing institutions, for example to trainees on the AIM-AHEAD Bridge2AI for Clinical Care Training Program, who register and sign a licensing agreement.
- RATER A: **bundle_supports** — line 45 'publicly available, AI-ready critical care dataset'; 240 'Controlled access'; 215–216 'expands access to Bridge2AI CHoRUS data'; 444–454 registration form and licensing agreement
- RATER B: **inferred** — Line 45 states the publicly-available goal, line 240 controlled access, lines 215-217 and 444-455 the trainee access route — each sentence of the description is grounded except "extended beyond the contributing institutions", which follows from the program lines (trainees from eligible outside organizations, lines 861-879) without being stated. Sam

### [14] CHORUS/2026-08-28 rule-01 (rule)
- rule text: Populate a slot only where the declared bundle supports it. Prefer omission over inference: an absent slot is a correct answer when the evidence is absent, and a plausible guess is not.
- RATER A: **violated** — known_limitations[0].scope_impact and known_limitations[2].scope_impact are consequences the bundle never states (slot-040, slot-047); human_subject_research.special_populations ('Pediatric and neonatal patients') is expanded from the unexpanded abbreviations PICU/NICU at line 1076, which the record's own source_caveats calls an inference; maintain
- RATER B: **followed** — The reconciliation's deliberate-omissions list (collection_timeframes, known_biases, doi, version, license, publisher, citation, etc.) shows omission chosen where evidence is absent, and disagreements are caveated rather than guessed (instances[0].source_caveats). Borderline inferences exist and are disclosed where they occur: human_subject_researc

### [15] CHORUS/2026-08-28 rule-06 (rule)
- rule text: Populate a slot with the information the field asks for, not with a pointer to where that information lives, and not with a statement that it is pending or absent. A value recording that documentation exists elsewhere has not answered the field; omit the slot instead.
- RATER A: **violated** — known_limitations[3].recommended_mitigation 'Check the project website's dataset snapshot for the current released figures before sizing an analysis' is a pointer to where the information lives; distribution_formats[5].description ends 'The GitHub organization overview gives the project's public-facing webpage as www.bridge2ai.org/chorus' (line 138
- RATER B: **followed** — No slot records that documentation is pending or absent; absences are genuinely absent and explained in source_caveats or the report. machine_annotation_tools' "OHNLP toolkit unknown" follows the tools slot's own prescribed convention. Borderline but not violating: the last sentence of distribution_formats[5].description records where the public-fa

### [16] CHORUS/2026-08-28 rule-07 (rule)
- rule text: Read the slot's description before populating it. Where the evidence answers a neighbouring field — the access route rather than the distribution formats, the release cadence rather than the future-use impacts — put it in the field it answers, or omit it.
- RATER A: **violated** — distribution_formats[5] 'Cloud enclave' has no format; its description is the access route (enclave hosting at lines 245–247, trainee access via the Collaborative Cloud at 487–489, a webpage at 1385) — the rule's own example of the access route placed in distribution formats
- RATER B: **followed** — The access route (registration, licensing agreement, .edu email) sits in data_governance.access_review_process and license_and_use_terms, not in distribution_formats; the anticipated-final figures sit in updates and known_limitations[3], not in instances[0].counts; trainee program facts sit on the external resource. distribution_formats[5] "Cloud e

### [17] CHORUS/2026-08-28 rule-08 (rule)
- rule text: When a slot's declared range is a class, populate the fields that class declares. Placing the content in a free-text field such as `description` while the declared fields — a name, an identifier, dates, affiliations — stay empty produces an object of the correct shape holding none of the structure it exists to carry. Where the evidence answers a declared field, populate that field rather than restating it in prose.
- RATER A: **violated** — creators[1..5].name holds the role phrase 'Bridge2AI CHoRUS leadership team member' while the person's name (lines 177–190) is carried only in principal_investigator; the declared name field of a Creator is filled with a description rather than the creator's name; creators[0].name likewise 'Principal investigator of the CHoRUS project'
- RATER B: **followed** — funders[0].grants[0].grant_number carries 1OT2OD032701-01 (Grant declares no date or amount fields, so those correctly live in description); creators[*].affiliations[*].name carry institutions; instances[0].counts is the integer 50000; distribution_formats[*].format carry the formats. Declared fields are populated before prose throughout.

### [18] CHORUS/2026-08-28 rule-11 (rule)
- rule text: An identifier that names a part of this dataset, and exists nowhere outside this record, is a label rather than a claim about the world — so no evidence can supply it and the rule above does not reach it. Mint it as a fragment on an identifier the evidence *does* supply, so the label stays traceable to something attested. This is the only case in which minting is right, and the test is whether the thing named has a referent outside this record: if it does, the rule above governs and you take the identifier from the evidence or omit it. Never invent a prefix — one the schema does not declare resolves to nothing, and where no fragment is possible either, a resolvable URL is the better answer. A person is identified by a personal-identifier registry entry and an organisation by an organisation registry entry; a fragment appended to an organisation's identifier does not identify a person, it makes a false claim about that organisation.
- RATER A: **violated** — creators[0..5].id (https://chorus4ai.org/#creator-rosenthal … #creator-kwong) and maintainers[0].id (#maintainer-program-manager) are fragments minted for persons, who have referents outside this record; the rule reserves minting for parts of the dataset and says a person is identified by a personal-identifier registry entry or omitted; id on Creat
- RATER B: **followed** — Every minted id is a fragment on https://chorus4ai.org/, which the bundle attests (line 1041, "Source URL: https://chorus4ai.org/"); no prefix outside the schema's declared set is invented; no fragment is hung on an organization identifier to name a person — persons appear as name strings in principal_investigator per that slot's description, and n

## AI_READI 2026-08-28_claude-opus-5-claudecode-generic-v6_rep2

- bundle: data/preprocessed/concatenated/AI_READI_preprocessed.txt
- full record: data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/AI_READI_d4d.yaml
- core: data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/AI_READI_d4d_core.yaml


### [19] AI_READI/2026-08-28 rule-06 (rule)
- rule text: Populate a slot with the information the field asks for, not with a pointer to where that information lives, and not with a statement that it is pending or absent. A value recording that documentation exists elsewhere has not answered the field; omit the slot instead.
- RATER A: **followed** — existing_uses, use_repository, other_tasks and discouraged_uses are omitted rather than filled with 'No'/'see license' (report §Omissions); maintainers[0] gives the contact addresses themselves alongside the pointer
- RATER B: **violated** — data_protection_impacts[0].impact_details = 'A data protection impact analysis has not been conducted.' (record lines 1042-1045) and extension_mechanism.extension_details = 'There is currently no mechanism for others to extend or augment...' (lines 1490-1494) populate detail fields with statements of absence; the schema descriptions ask for the ana

### [20] AI_READI/2026-08-28 rule-07 (rule)
- rule text: Read the slot's description before populating it. Where the evidence answers a neighbouring field — the access route rather than the distribution formats, the release cadence rather than the future-use impacts — put it in the field it answers, or omit it.
- RATER A: **violated** — participant_compensation[0].compensation_rationale holds payment timing and proration ('provided once the final data are received ... not prorated'), not the rationale for the amount the slot asks for; participant_privacy[2].anonymization_method holds storage and access controls (encrypted servers, locked cabinets, Level 3), not an anonymization me
- RATER B: **followed** — the login-gated access route is in distribution_formats[].access_urls and data_governance.access_review_process, not download_url (omitted); release cadence is in updates.frequency (record line 1449), not future_use_impacts, which carries only the re-identification impact (lines 1285-1290); lab test detail sits on data_collectors/raw_data_sources r

### [21] AI_READI/2026-08-28 rule-14 (rule)
- rule text: Within the rule above, mint a fragment identifier for a part of this dataset only where another value in the record must point at that part — a split a task names, a subset a distribution cites, a collection a file belongs to. A part nothing points at is described in prose, not labeled: an identifier no value in the record uses is not a label, it is noise that reads as structure. Name the same part with the same fragment every time a value points at it, and mint nothing for a part that is only described.
- RATER A: **violated** — subsets[0].id #public, subsets[1].id #controlled and subsets[2].id #mini are pointed at by no value in either record; the file_collections fragments are used by the core's distributions, the subset fragments by nothing (DataSubset.id is schema-required, so recording the subsets at all forced the mint)
- RATER B: **not_applicable** — all 13 mints are forced: FileCollection.id and DataSubset.id are declared identifier+required in the schema (verified via the merged schema), so the record could not omit them given the objects; recording the nine datatype collections, the root-metadata collection and the public/controlled/mini subsets is substantive (each is source-described, e.g.

## AI_READI 2026-08-28_claude-opus-5-claudecode-generic-v6_rep3

- bundle: data/preprocessed/concatenated/AI_READI_preprocessed.txt
- full record: data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/AI_READI_d4d.yaml
- core: data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep3/AI_READI_d4d_core.yaml


### [22] AI_READI/2026-08-28 slot-004 (slot_receipted)
- slot: `license_and_use_terms.description`
- value: Access requires logging in through a verified identity system, agreeing to use the data only for type 2 diabetes-related research, and agreeing to the license terms. The access type is recorded as public download with self-attestation required. Where an agreement is entered into on behalf of an inte
- receipt: chunk c012 lines [2376, 2661] snippet: 'Licensee may use and store the data only on (i) servers and devices maintained by and located within Licensee’s Institution/Employer'
- receipt: chunk c015 lines [2814, 3213] snippet: '"rightsURI": "https://doi.org/10.5281/zenodo.17555036"'
- receipt: chunk c022 lines [5317, 5716] snippet: '"copyrightNotice": "Copyright © 2026 AI-READI"'
- receipt: chunk c022 lines [5317, 5716] snippet: '"project_name": "AI READI"'
- RATER A: **weak** — the value's first two sentences (login through a verified identity system, T2D-only use, access type public download with self-attestation) are stated at lines 2983-2985 in c015, not in any of the four receipted snippets; the c012 snippet (line 2486, permitted data storage) is on topic but its content does not appear in the value, while the 'author
- RATER B: **supported** — access steps and accessType 'PublicDownloadSelfAttestationRequired' at 2983-2990; authorized-group/legal-member/termination terms at license 2424-2437; copyright notice at 5412; value reads all three correctly. Two cited snippets are non-probative for this slot (the c012 storage line supports license_terms, and c022 'project_name: AI READI' at 5463

### [23] AI_READI/2026-08-28 slot-015 (slot_receipted)
- slot: `preprocessing_strategies[4].preprocessing_details`
- value: Software engineers on the project are responsible for designing, implementing and testing the data curation pipelines, and cloud engineers for the cloud infrastructure customization, configuration and deployment that hosts them.
- receipt: chunk c028 lines [7319, 7376] snippet: 'Software engineer: Responsible for designing, implementing, and testing the different data curation pipelines'
- RATER A: **weak** — line 7366 is the IRB protocol's staff-role list ('Software engineer: Responsible for designing, implementing, and testing the different data curation pipelines'); it names who builds pipelines, not any preprocessing step, tool, parameter or order of operations that preprocessing_details asks for
- RATER B: **supported** — 7366-7369: 'Software engineer: Responsible for designing, implementing, and testing the different data curation pipelines' and 'Cloud engineer: Responsible for cloud infrastructure customization, configuration and deployment'

### [24] AI_READI/2026-08-28 slot-026 (slot_receipted)
- slot: `conforms_to_standard`
- value: ['CDS', 'DICOM', 'OMOP_CDM', 'WFDB', 'OPEN_MHEALTH', 'ESDS', 'RO_CRATE']
- receipt: chunk c004 lines [826, 1225] snippet: 'the Observational Medical Outcomes Partnership Common Data Model for clinical data and the DICOM format for retinal imaging'
- receipt: chunk c022 lines [5317, 5716] snippet: '"conformsTo": { "@id": "https://w3id.org/ro/crate/1.2-DRAFT" }'
- receipt: chunk c022 lines [5317, 5716] snippet: '"@id": "ark:59853/rocrate-b2ai-aireadi-release-3-0-0"'
- RATER A: **weak** — the three snippets attest OMOP_CDM and DICOM (c004) and RO_CRATE (line 5339 conformsTo ro/crate/1.2-DRAFT); the ark @id snippet (5342) bears on no standard; WFDB, OPEN_MHEALTH, ESDS and CDS are stated elsewhere in the bundle (e.g. line 1911 CDS, the relatedStandard blocks in c015-c017) but no receipt for this slot cites them
- RATER B: **supported** — 1174-1176 (OMOP CDM for clinical data, DICOM for retinal imaging), 5338-5342 (crate conformsTo ro-crate 1.2-DRAFT), README standards table in c019 (WFDB, OMOP, ESDS, DICOM, Open mHealth, CDS per directory) - each enum member is bundle-attested

### [25] AI_READI/2026-08-28 slot-043 (slot_receiptless)
- slot: `variables[7].measurement_technique`
- value: Read from the electrocardiogram or blood pressure measurement device; also recorded continuously by the Garmin VivoSmart 5
- RATER A: **inferred** — line 440-441 heart rate measured with the automatic oscillometric device and lines 1372-1373 heart rate under the Garmin table support the second and third clauses; nothing states that heart rate is read from the electrocardiogram
- RATER B: **bundle_supports** — 4327 (healthsheet devices: 'Heart rate can be read from EKG or blood pressure measurement devices') and 3863 (garmin_vivosmart5 heart_rate modality directory) - both clauses stated

### [26] AI_READI/2026-08-28 rule-07 (rule)
- rule text: Read the slot's description before populating it. Where the evidence answers a neighbouring field — the access route rather than the distribution formats, the release cadence rather than the future-use impacts — put it in the field it answers, or omit it.
- RATER A: **violated** — collection_notifications[1] 'Return of individual results to participants' (record lines 778-795) describes how results are returned after the visit; notification_details asks how individuals were notified about data collection, and the content belongs to a benefits/return-of-results field, not this one
- RATER B: **followed** — access route in license_and_use_terms.description and data_governance.access_review_process; formats in distribution_formats with media_type; release cadence in updates.frequency, not future_use_impacts

### [27] AI_READI/2026-08-28 rule-14 (rule)
- rule text: Within the rule above, mint a fragment identifier for a part of this dataset only where another value in the record must point at that part — a split a task names, a subset a distribution cites, a collection a file belongs to. A part nothing points at is described in prose, not labeled: an identifier no value in the record uses is not a label, it is noise that reads as structure. Name the same part with the same fragment every time a value points at it, and mint nothing for a part that is only described.
- RATER A: **violated** — nine fragments are minted at file_collections[*].id (doi:10.60775/fairhub.3#cardiac_ecg ... #wearable_blood_glucose, record lines 1466-1605) and no other value in the record points at any of them (grep for '#' finds only those nine id lines); the v6 rule asks for minting only where another value must reference the part
- RATER B: **not_applicable** — all nine mints are forced - FileCollection.id is a required identifier (induced_slot verified; pack_version 2 has no id_slots block) - and nothing else in either record mints a fragment or urn; parts only described (access tiers, diabetes groups, split) carry no ids

## VOICE 2026-08-28_claude-opus-5-claudecode-generic-v6_rep2

- bundle: data/preprocessed/concatenated/VOICE_preprocessed.txt
- full record: data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/VOICE_d4d.yaml
- core: data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-claudecode-generic-v6_rep2/VOICE_d4d_core.yaml


### [28] VOICE/2026-08-28 slot-005 (slot_receipted)
- slot: `creators[0].name`
- value: Yael Bensoussan
- receipt: chunk c002 lines [26, 425] snippet: 'Bridge2AI-Voice Consortium'
- RATER A: **weak** — snippet 'Bridge2AI-Voice Consortium' (line 158) is a consortium author entry, not the person's name; 'Yael Bensoussan' is stated two lines later (160-165) and at 629, 2028, but the cited snippet does not name her
- RATER B: **supported** — snippet sits at line 158 in the PMC author list; the passage around it (lines 158-166, 188) names 'Yael Bensoussan' twice as author and corresponding author, supporting the creator name — though the snippet itself quotes the consortium's name, not hers, which is an odd anchor choice

### [29] VOICE/2026-08-28 slot-037 (slot_receiptless)
- slot: `creators[8].principal_investigator`
- value: Ruth Bahr
- RATER A: **inferred** — line 3067 'USF Ruth Bahr PhD, CCC-SLP Lead Voice Disorders' and 2028 list her as a lead investigator; no passage calls her a principal investigator - 2028 names only Bensoussan and Elemento as co-PIs
- RATER B: **bundle_supports** — line 3067 (c012): 'USF	Ruth Bahr PhD, CCC-SLP	Lead Voice Disorders' — her name and lead role are stated; note the bundle calls her a Lead, not a principal investigator, the same convention concern as slot-018

### [30] VOICE/2026-08-28 rule-01 (rule)
- rule text: Populate a slot only where the declared bundle supports it. Prefer omission over inference: an absent slot is a correct answer when the evidence is absent, and a plausible guess is not.
- RATER A: **violated** — creators[8].principal_investigator (and creators[5..11] likewise) reads 'lead investigator' (line 3067, 2028) as principal investigator; external_resources[3].description infers that every version is reachable from the landing page (5487); both are inferences the rule asks to omit. Elsewhere the record omits well (subsets, variables, credit_roles, 
- RATER B: **followed** — omission was preferred where evidence ran out: media_type removed in Phase 3 as an unsupported identifier, subsets/variables/total_size_bytes left absent with reasons; spot-checks of receiptless values (award amount 4660942 at 1259, project period at 1260-1261, Zenodo 13834653 at 5734, Synapse at 3611) all trace to the bundle

### [31] VOICE/2026-08-28 rule-06 (rule)
- rule text: Populate a slot with the information the field asks for, not with a pointer to where that information lives, and not with a statement that it is pending or absent. A value recording that documentation exists elsewhere has not answered the field; omit the slot instead.
- RATER A: **violated** — splits[0].split_details 'The dataset comes with predefined tasks and labeling but no predefined recommended splits ... Researchers are encouraged to create their own' is a statement that the thing the field asks for is absent (bundle line 2019); the rule says omit the slot instead
- RATER B: **followed** — values carry the asked-for information itself (access_review_process states the steps, retention_limit the periods); borderline: splits[0].split_details records that no recommended splits exist — but that is the bundle's own substantive answer at line 2019 ('no predefined recommended data splits... create their own'), not a pointer or a pending-doc

### [32] VOICE/2026-08-28 rule-07 (rule)
- rule text: Read the slot's description before populating it. Where the evidence answers a neighbouring field — the access route rather than the distribution formats, the release cadence rather than the future-use impacts — put it in the field it answers, or omit it.
- RATER A: **violated** — Creator.principal_investigator asks for 'the key individual (Principal Investigator) responsible for or overseeing dataset creation'; the record sets each of creators[3..11] as their own PI on the strength of cohort-lead roles (line 3067-3078), while line 2028 names only Bensoussan and Elemento as co-principal investigators - the evidence answers C
- RATER B: **followed** — content sits in the field it answers: release cadence in updates.frequency, access routes in license_and_use_terms/access_review_process, formats in distribution_formats[].format; minor stray — collection_timeframes[0].description carries geography ('collected in the USA and Canada') in a timeframe entry

## CHORUS 2026-08-28_claude-opus-5-api-generic-v7_rep1

- bundle: data/preprocessed/concatenated/CHORUS_preprocessed.txt
- full record: data/d4d_concatenated/claudecode_agent/2026-08-28_claude-opus-5-api-generic-v7_rep1/CHORUS_d4d.yaml
- core: data/d4d_concatenated/claudecode_agent_core/2026-08-28_claude-opus-5-api-generic-v7_rep1/CHORUS_d4d_core.yaml


### [33] CHORUS/2026-08-28 slot-003 (slot_receipted)
- slot: `ethical_reviews[0].review_details`
- value: Ethics is one of the project's three pillars (Ethical and Trustworthy AI). The consortium performs community-facing ethics focus groups to determine what data is appropriate for public sharing, and evaluates community perspectives on clinical care AI to find ways to increase trustworthiness of prove
- receipt: chunk c002 lines [19, 54] snippet: 'perform community-facing ethics focus groups to determine what data is appropriate for public sharing'
- receipt: chunk c006 lines [1032, 1112] snippet: 'evaluates community perspectives on clinical care AI to find ways to increase trustworthiness of provenance and privacy in AI'
- receipt: chunk c006 lines [1032, 1112] snippet: 'New approaches are being created as existing legal and regulatory landscape is analyzed.'
- RATER A: **weak** — line 45 'perform community-facing ethics focus groups to determine what data is appropriate for public sharing' and line 1087 'evaluates community perspectives on clinical care AI ... New approaches are being created as existing legal and regulatory landscape is analyzed' describe ethics activities of the project; review_details asks for the ethica
- RATER B: **supported** — line 45 'perform community-facing ethics focus groups to determine what data is appropriate for public sharing' and lines 1087-1088 (community perspectives; legal/regulatory landscape analyzed) say what the value says; the value's own caveat concedes no IRB or ethics committee is named, which is the gap between these activities and the class's IRB-

### [34] CHORUS/2026-08-28 slot-004 (slot_receipted)
- slot: `preprocessing_strategies[4].preprocessing_details`
- value: Geocoding of OMOP Location entities via DeGauss, supporting contextual data elements such as geographic distance to the nearest hospital and social determinants of health.
- receipt: chunk c002 lines [19, 54] snippet: 'appropriate contextual factors such as geographic distance to the nearest hospital'
- receipt: chunk c008 lines [1513, 1698] snippet: 'Open source code to geocode OMOP Location entities via DeGauss'
- RATER A: **weak** — line 1538 'Open source code to geocode OMOP Location entities via DeGauss' is a repository blurb (UF-Geocoding, forked from bihorac-LAB/Exposome) attesting that code exists; line 45 says data elements will 'feature appropriate contextual factors such as geographic distance to the nearest hospital'; neither states that geocoding was applied as a pre
- RATER B: **supported** — line 45 item C 'appropriate contextual factors such as geographic distance to the nearest hospital' and line 1538 'Open source code to geocode OMOP Location entities via DeGauss' each verbatim; the connective 'supporting contextual data elements' joins two sources but is a fair reading of the UF-Geocoding/Exposome repository purpose

### [35] CHORUS/2026-08-28 slot-007 (slot_receipted)
- slot: `data_governance.access_review_process`
- value: Access is controlled and mediated by the project: requests are directed to the named CHoRUS access contacts, prospective users register and sign a licensing agreement, and access with provisioned compute in the Bridge2AI AI/ML for Clinical Care Collaborative Cloud follows. Federated access enables s
- receipt: chunk c004 lines [455, 854] snippet: 'Bridge2AI AI/ML for Clinical Care Collaborative Cloud'
- receipt: chunk c007 lines [1113, 1512] snippet: 'Federated access will enable sampling methods to ensure a balanced and diverse cohort.'
- RATER A: **weak** — line 768 'The Bridge2AI AI/ML for Clinical Care Collaborative Cloud' is a training-program item and line 1220 'Federated access will enable sampling methods to ensure a balanced and diverse cohort' is about cohort sampling, not access review; lines 444–455 (registration form, licensing agreement) and 1383 (access-request contacts) give an access ro
- RATER B: **supported** — registration, licensing agreement, and provisioned compute are at lines 444-455 and 491-493 (c004); 'Bridge2AI AI/ML for Clinical Care Collaborative Cloud' verbatim at line 493; caveat: the final sentence (line 1220, federated access enabling sampling) answers cohort sampling rather than access review and duplicates sampling_strategies[0].strategie

### [36] CHORUS/2026-08-28 slot-009 (slot_receipted)
- slot: `existing_uses[1].examples`
- value: ['The AIM-AHEAD Bridge2AI for Clinical Care Training Program expands access to CHoRUS data for up to 30 trainees per cohort, who use the data on the Collaborative Cloud for hands-on AI/ML coursework, development of practical use cases, poster presentations, conference abstracts, and manuscripts; Coh
- receipt: chunk c004 lines [455, 854] snippet: 'Prepare a compelling poster presentation for the AIM-AHEAD and Bridge2AI Annual Meetings'
- receipt: chunk c005 lines [855, 1031] snippet: 'Up to 30 trainees will be selected'
- receipt: chunk c005 lines [855, 1031] snippet: 'Program Start Date...November 17, 2025'
- RATER A: **misread** — lines 997–999 'Program Start Date / November 17, 2025' in a webinar dated September 09, 2025 (line 74), and the bundle's latest document is a snapshot of 2025-11-14 (line 1125); the value states 'Cohort 2 began on 17 November 2025' as an existing use, reading a scheduled date as an event that occurred; 'up to 30 trainees per cohort' generalizes lin
- RATER B: **supported** — lines 216-218 (program 'expands access to Bridge2AI CHoRUS data'), line 703-704 (poster, abstract, manuscript), line 978 'Up to 30 trainees will be selected', lines 997-999 'Program Start Date / November 17, 2025' together state each element of the value

### [37] CHORUS/2026-08-28 slot-011 (slot_receipted)
- slot: `is_deidentified.deidentification_details`
- value: Clinical notes are not released; only tokens leave the contributing site. For imaging, 1000 images were available as of August 2025 with de-identification described as in process for a larger cohort, so de-identification of the wider imaging cohort was not reported as complete. Supporting tooling in
- receipt: chunk c007 lines [1113, 1512] snippet: 'privacy_scan_tool\n\nA Privacy Scan tools for medical records'
- receipt: chunk c008 lines [1513, 1698] snippet: 'CTP-deid Public'
- RATER A: **weak** — lines 1413–1415 'privacy_scan_tool / A Privacy Scan tools for medical records' and line 1522 'CTP-deid Public' are repository names attesting that tooling exists, and the value claims only that; the procedural content of the value (notes not released, 1000 images with de-id in process) rests on lines 247 and 251–252 of c003, which this slot's recei
- RATER B: **supported** — line 247 'Clinical notes - stored locally except tokens', lines 251-252 imaging 1000 images with de-id in process, lines 1413-1415 'privacy_scan_tool / A Privacy Scan tools for medical records', line 1522 'CTP-deid Public' — each sentence of the value maps to a stated line

### [38] CHORUS/2026-08-28 slot-018 (slot_receipted)
- slot: `labeling_strategies[0].labeling_details`
- value: A visualization and annotation environment is developed to label data with targets important for prediction; the project develops capabilities across the multi-center network to acquire, standardize, tokenize, store, visualize, and label data.
- receipt: chunk c002 lines [19, 54] snippet: 'acquire, standardize, tokenize, store, visualize, and label data'
- receipt: chunk c007 lines [1113, 1512] snippet: 'A visualization and annotation environment will label data with targets important for'
- RATER A: **weak** — line 45 'develop capabilities across a multi-center network to acquire, standardize, tokenize, store, visualize, and label data' and lines 1212–1214 'A visualization and annotation environment will label data with targets important for prediction' are statements of intent in future tense; labeling_details asks for annotation procedures, guidelines 
- RATER B: **supported** — line 45 'acquire, standardize, tokenize, store, visualize, and label data' and lines 1212-1214 'A visualization and annotation environment will label data with targets important for prediction'; the value's present tense ('is developed') slightly firms the source's future tense but does not change the claim

### [39] CHORUS/2026-08-28 slot-019 (slot_receipted)
- slot: `data_governance.stewardship_roles`
- value: ['The CHoRUS Network spans 20 academic centers, of which 14 contribute as data acquisition centers; more than 60 consortium members work across those institutions. Data site managers at contributing sites follow validated standard operating protocols for extraction and delivery, and report status th
- receipt: chunk c006 lines [1032, 1112] snippet: '60+\nCHoRUS consortium members across 20 different institutions'
- receipt: chunk c007 lines [1113, 1512] snippet: 'This collaboration spans 20 academic centers, of which 14 will contribute as Data'
- RATER A: **weak** — lines 1072–1073 '60+ / CHoRUS consortium members across 20 different institutions' and 1202–1204 '20 academic centers, of which 14 will contribute' attest the network's size, and lines 1254–1262 and 1323–1334 attest what site data managers do when contributing; stewardship_roles asks for named roles holding continuing responsibility for the data, a
- RATER B: **supported** — lines 1072-1073 '60+ / CHoRUS consortium members across 20 different institutions', lines 1202-1204 (20 centers, 14 contributing), and lines 1254-1262/1323-1325 (site data managers, validated SOPs, status reporting) state the roles the value names; continuing custodianship is what those lines describe

### [40] CHORUS/2026-08-28 slot-029 (slot_receiptless)
- slot: `creators[1].principal_investigator`
- value: Azra Bihorac
- RATER A: **inferred** — lines 177–178 'Azra Bihorac / University of Florida' under 'Bridge2AI CHoRUS Leadership Team' (line 171); the only principal-investigator attribution in the bundle is line 37 'Principal investigator: ROSENTHAL, ERIC S.'; that a leadership-team member is a principal_investigator follows from the listing only by inference, as the object's own caveat 
- RATER B: **bundle_supports** — lines 171-178 list 'Azra Bihorac / University of Florida' on the 'Bridge2AI CHoRUS Leadership Team'; the slot's description asks for the key individual 'responsible for or overseeing dataset creation', which a leadership-team listing supports; the entry's caveat correctly records that no credit role is stated (RePORTER at line 37 names only Rosenth

### [41] CHORUS/2026-08-28 slot-030 (slot_receiptless)
- slot: `tasks[1].response`
- value: Predicting complications and deterioration among patients with acute or critical illness.
- RATER A: **bundle_supports** — line 45 'predicting complications ... among patients with acute or critical illness'; 'Deterioration' appears in the preferred-terms list at line 50
- RATER B: **inferred** — line 45 states 'predicting complications, and measuring treatment response among patients with acute or critical illness' — without 'deterioration'; 'Deterioration' appears only as an isolated preferred term in the keyword dump at line 50, never as a prediction task; the composite task is assembled, not stated

### [42] CHORUS/2026-08-28 slot-043 (slot_receiptless)
- slot: `intended_uses[3].use_category`
- value: contextual and equity-oriented research
- RATER A: **inferred** — no passage names a use category; the label is coined for the use at intended_uses[3].examples, which is itself inferred from line 45 and lines 1206–1208 (see slot-038); 'equity' echoes only the project title's 'for Equitable AI' (line 36)
- RATER B: **exempt_by_nature** — use_category is the record's own categorization label (schema example: 'academic research'); no passage states a category name; the phrase compresses attested content (Equitable AI, SDOH data elements) into a label of the record's making

### [43] CHORUS/2026-08-28 slot-051 (slot_receiptless)
- slot: `raw_data_sources[0].raw_data_format`
- value: site-native EHR extracts, transformed to the OMOP Common Data Model
- RATER A: **inferred** — line 45 'standardize data to the OMOP Common Data Model' and line 1325 'a CHoRUS-specific clinical data extract' state the target model and that sites make extracts; raw_data_format asks for the format before preprocessing, and 'site-native EHR extracts' is the record's inference — no line names the pre-OMOP format
- RATER B: **bundle_supports** — line 45 'standardize data to the OMOP Common Data Model', lines 1234-1236 'clinical data in various source formats' (site-native), and lines 1323-1325/1612 (sites create a CHoRUS-specific clinical data extract)

### [44] CHORUS/2026-08-28 rule-06 (rule)
- rule text: Populate a slot with the information the field asks for, not with a pointer to where that information lives, and not with a statement that it is pending or absent. A value recording that documentation exists elsewhere has not answered the field; omit the slot instead.
- RATER A: **violated** — instances[5].notes 'Extraction of EEG waveforms was reported to be in process as of August 2025' populates an instance with a statement that the data are pending (line 254 'EEG – extraction in process at this point'); maintainers[3].maintainer_details 'a package status page lists versions, maintainers, and other metadata about CHoRUS packages' is a
- RATER B: **followed** — the reconciliation removed pending-status and pointer-shaped values (imaging de-id withdrawn from method, report section 2.2; at_risk_populations dropped rather than left as a caveat-only object, section 2.3); data_use_permission omitted rather than answered with 'not stated'