#!/usr/bin/env python3
"""Write the rubric10-semantic v3 evaluation of one D4D record.

Purpose: serialize the evaluator's (claude-opus-5-5) judgements for the
VOICE_PEDIATRIC record of label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3.
Inputs: the D4D YAML (hashed only), .claude/agents/d4d-rubric10-semantic.md,
data/rubric/rubric10.txt, data/rubric/semantic_evidence_authority_v3.json.
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/
VOICE_PEDIATRIC_2026-11-22b_rep3_evaluation.json
Context: caller-supplied evaluation, no applicability context (all unknown). 2026-11-22.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest  # noqa: E402

D4D = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_d4d.yaml"
OUT = "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/VOICE_PEDIATRIC_2026-11-22b_rep3_evaluation.json"
MODEL = "claude-opus-5-5"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


ALWAYS = "This item applies to every dataset"
SHARED = "shared_dataset: not declared; retained in the denominator"
COLL = "data_collection: not declared; retained in the denominator"
PROC = "data_processing: not declared; retained in the denominator"
SOFT = "processing_software: not declared; retained in the denominator"
REG = "regulated_access: not declared; retained in the denominator"
HS = "human_subjects: not declared; retained in the denominator"
HS_OR_REG = ("any: human_subjects: not declared; retained in the denominator; "
             "regulated_access: not declared; retained in the denominator")


def C(path, quote=None):
    return {"path": path, **({"quote": quote} if quote else {})}


def A(path):
    return {"path": path}


# item_id: (name, score, applicability_evidence, evidence, quality_note,
#           cited, absent, counts, considered, no_issue_reason)
ITEMS = {
 "E1.1": ("Persistent Identifier (DOI, RRID, or URI)", 1, ALWAYS,
   "doi 10.13026/mf9s-5r03 (id doi:10.13026/mf9s-5r03); PhysioNet prefix 10.13026; valid DOI syntax.",
   "Valid, plausible PhysioNet DOI. The record DOI is the latest-version DOI while the citation uses the version 1.1.0 DOI 10.13026/h995-bt35; version_access explains both, so this is noted, not deducted.",
   [C("doi", "10.13026/mf9s-5r03"), C("id", "doi:10.13026/mf9s-5r03")], [], [],
   ["version_access", "citation"], None),
 "E1.2": ("Dataset Title and Description Completeness", 1, ALWAYS,
   "Title 'Bridge2AI-Voice Pediatric Dataset'; description gives 23,533 recordings from 300 participants aged 2-18 at the Hospital for Sick Children, release contents and folder organization.",
   "Specific, well over 200 characters, explains contents and withheld raw audio.",
   [C("title", "Bridge2AI-Voice Pediatric Dataset"),
    C("description", "derived audio features for 23,533 recordings collected from 300 participants aged 2-18")], [], [], ["name"], None),
 "E1.3": ("Keywords or Tags for Searchability", 1, ALWAYS,
   "keywords: health, pediatric, biomarkers, bridge2ai, voice (5).",
   "Meets the five-keyword threshold with relevant domain terms; no method or condition terms (e.g., spectrogram, speech) so searchability is modest.",
   [C("keywords", "pediatric")], [], [{"path": "keywords", "claimed": 5}], [], None),
 "E1.4": ("Landing Page and Resources (page, hierarchical resources)", 1, ALWAYS,
   "page https://physionet.org/content/b2ai-voice-pediatric/1.1.0/; file_collections features/phenotype/metadata with file resources.",
   "Landing page plus a hierarchical file-collection structure.",
   [C("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/"), C("file_collections")], [],
   [{"path": "file_collections", "claimed": 3}], [], None),
 "E1.5": ("Hierarchical Structure (parent datasets, relationships)", 0, ALWAYS,
   "No parent_datasets or related_datasets; source_caveats acknowledges the Bridge2AI-Voice adult dataset on PhysioNet but deliberately records no relationship.",
   "No typed links to parent or related datasets.",
   [], [A("parent_datasets"), A("related_datasets")], [], ["source_caveats"], None),
 "E2.1": ("Access Policy and IP Restrictions Defined", 1, ALWAYS,
   "license_and_use_terms: Bridge2AI Voice Registered Access License; restricted access to credentialed PhysioNet users who sign the DUA; no training required.",
   "Clear access policy and licence name; ip_restrictions absent but not required when the access policy is explicit.",
   [C("license_and_use_terms.license_terms", "only credentialed PhysioNet users who sign the data use agreement"),
    C("license", "Bridge2AI Voice Registered Access License")], [A("ip_restrictions")], [], [], None),
 "E2.2": ("Regulatory Compliance and Confidentiality Classification", 0, REG,
   "regulatory_restrictions absent: no confidentiality level, HIPAA/PHIPA or other compliance statement. data_governance names DACO and gives an access-committee email inside access_review_process, but committee_contact is unpopulated.",
   "Governance committee identified, but no regulatory framework or confidentiality classification.",
   [C("data_governance.committee_name", "Data Access Compliance Office (DACO)")],
   [A("regulatory_restrictions"), A("data_governance.committee_contact")], [],
   ["data_governance.access_review_process"], None),
 "E2.3": ("Download URL or Platform Link Available", 1, ALWAYS,
   "No download_url, but the PhysioNet platform page is given and license_terms state the access route (credentialed users signing the DUA).",
   "Platform link and access instructions satisfy the item; a direct download_url is absent (noted).",
   [C("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/"),
    C("license_and_use_terms.license_terms", "credentialed users must be approved and sign the DUA")],
   [A("download_url")], [], ["raw_sources"], None),
 "E2.4": ("Distribution Formats and File Types Specified", 1, ALWAYS,
   "distribution_formats: Parquet, TSV (text/tab-separated-values), JSON (application/json); file-level TSV media types.",
   "Formats specified with MIME types for TSV/JSON; Parquet lacks a media_type.",
   [C("distribution_formats.format", "Parquet"), C("distribution_formats.media_type", "text/tab-separated-values")], [],
   [{"path": "distribution_formats", "claimed": 3}], ["file_collections.resources.format"], None),
 "E2.5": ("Related Datasets and External Resources Linked", 0, ALWAYS,
   "related_datasets absent; external_resources lists only the project website https://b2ai-voice.org/. The adult dataset acknowledged in source_caveats is not linked.",
   "Only one homepage link; no related datasets or external documentation (papers, docs) linked.",
   [C("external_resources", "https://b2ai-voice.org/")], [A("related_datasets")], [], ["source_caveats"], None),
 "E3.1": ("License Terms Allow Reuse", 1, SHARED,
   "Named registered-access licence with DUA; credentialed users may access and use the files.",
   "Reuse permitted under registered access; specific reuse permissions (redistribution, commercial use) are not enumerated.",
   [C("license_and_use_terms.name", "Bridge2AI Voice Registered Access License")], [], [], ["license"], None),
 "E3.2": ("Data Formats Are Standardized (encoding, format)", 1, SHARED,
   "Parquet, TSV and JSON data dictionaries; Parquet described as open-source column-oriented format.",
   "Standard open formats; character encoding not stated.",
   [C("distribution_formats.format", "TSV"), C("file_collections.resources.format", "TSV")], [], [], ["file_collections"], None),
 "E3.3": ("Schema or Ontology Conformance Stated", 0, SHARED,
   "conforms_to and conforms_to_schema absent. BIDS conversion is mentioned only as an internal preprocessing step, not as conformance of the release.",
   "No schema/standard conformance stated for released files.",
   [], [A("conforms_to"), A("conforms_to_schema")], [], ["preprocessing_strategies"], None),
 "E3.4": ("Variable Metadata with Identifiers Defined", 1, SHARED,
   "variables: participant_id and session_id (is_identifier true), task_name, n_frames with descriptions; JSON data dictionaries per file are described.",
   "Identifier variables defined; coverage limited to shared parquet columns, phenotype variables deferred to data dictionaries.",
   [C("variables.variable_name", "participant_id"), C("variables.is_identifier")], [],
   [{"path": "variables", "claimed": 4}], [], None),
 "E3.5": ("Use Guidance Provided (intended, prohibited uses)", 0, ALWAYS,
   "intended_uses: developmental norms, AI screening tools, clinical insight. prohibited_uses and discouraged_uses absent.",
   "Only intended uses; no prohibited or discouraged uses despite sensitive pediatric voice data.",
   [C("intended_uses.description", "create AI-driven tools for early screening")],
   [A("prohibited_uses"), A("discouraged_uses")], [{"path": "intended_uses", "claimed": 3}], [], None),
 "E4.1": ("IRB or Ethics Review and Data Protection Impact", 1, HS_OR_REG,
   "ethical_reviews: Research Ethics Board at the Hospital for Sick Children approved data collection and sharing; human_subject_research.ethics_review_board matches.",
   "Specific ethics review documented; data_protection_impacts absent.",
   [C("ethical_reviews.review_details", "Data collection and sharing was approved by the Research Ethics Board"),
    C("human_subject_research.involves_human_subjects")], [A("data_protection_impacts")], [],
   ["human_subject_research.ethics_review_board"], None),
 "E4.2": ("Deidentification Method Described", 0, HS_OR_REG,
   "is_deidentified absent. The record says raw recordings are withheld, features for sensitive records removed and free-speech tasks manually checked for PII, but no deidentification method or identifiers removed are stated.",
   "Privacy steps exist but no deidentification method for phenotype/demographic data.",
   [], [A("is_deidentified")], [], ["cleaning_strategies", "sensitive_elements"], None),
 "E4.3": ("Privacy Protections and Re-identification Risk Assessment", 1, HS,
   "participant_privacy.reidentification_risk: voice can never be fully de-identified; protections: raw audio withheld and controlled access, sensitive-record features removed, PII checks.",
   "Explicit re-identification risk plus mitigations; the risk statement is drawn from the wider study protocol (caveated).",
   [C("participant_privacy.reidentification_risk", "a voice can never be fully de-identified"),
    C("cleaning_strategies.cleaning_details", "manually checked for presence of unconsented speakers and PII")], [], [],
   ["raw_sources"], None),
 "E4.4": ("Informed Consent Obtained from Participants", 1, HS,
   "informed_consent: parental or participant consent obtained prior to data collection and data sharing (consent_obtained true); assent procedures in at_risk_populations.",
   "Consent and scope (collection and sharing) documented; consent form type and withdrawal mechanism not stated.",
   [C("informed_consent.description", "parental or participant consent was obtained prior to data collection and data sharing"),
    C("informed_consent.consent_obtained")], [], [], ["at_risk_populations.assent_procedures"], None),
 "E4.5": ("Vulnerable Populations and Compensation Documented", 0, HS,
   "at_risk_populations is detailed (guardian consent, assent, HRP-416 checklist), but participant_compensation is absent.",
   "Vulnerable-population protections strong; compensation undocumented, so the item is incomplete.",
   [C("at_risk_populations.assent_procedures", "children provide verbal assent where appropriate")],
   [A("participant_compensation")], [], ["human_subject_research.special_populations"], None),
 "E5.1": ("Cohort or Subpopulations Characteristics Described", 1, ALWAYS,
   "subpopulations: age groups Peds 2-4, 4-6, 6-10, 10+; sampling_strategies inclusion (2-18, English proficiency) and exclusion (non-verbal, >18) criteria; patients and healthy volunteers at SickKids.",
   "Inclusion/exclusion and age grouping given; no sex/ethnicity distribution.",
   [C("subpopulations.identification", "Peds 10+, Peds 6-10, Peds 4-6"),
    C("sampling_strategies.description", "Inclusion criteria were 2 to 18 years of age and English")], [], [], [], None),
 "E5.2": ("Number of Instances or Samples Reported", 1, ALWAYS,
   "instances: 23,533 recordings and 300 participants; per-file n=23533/23532.",
   "Specific counts.",
   [C("instances.counts"), C("instances.description", "Recordings were collected from 300 participants aged 2-18.")], [],
   [{"path": "instances", "claimed": 2}], [], None),
 "E5.3": ("Variable-Level Metadata, Tabular Flag, and Data Splits", 0, ALWAYS,
   "Four shared variables described and JSON data dictionaries mentioned, but is_tabular absent and no subsets with split/subpopulation flags.",
   "Partial variable metadata only; tabular flag and subset roles undocumented.",
   [C("variables.description", "A unique identifier for the participant")], [A("is_tabular"), A("subsets")],
   [{"path": "variables", "claimed": 4}], [], None),
 "E5.4": ("Data Topics or Conditions Represented", 0, ALWAYS,
   "instances describe only recording and participant counts; the clinical conditions of the SickKids patient participants (vs healthy volunteers) are never listed.",
   "For a voice-as-biomarker dataset, represented conditions/phenotypes are undocumented.",
   [C("instances.instance_type", "pediatric participant")], [], [{"path": "instances", "claimed": 2}],
   ["description", "collection_mechanisms"], None),
 "E5.5": ("Data Quality, Anomalies, and Missing Data Documented", 1, ALWAYS,
   "anomalies: some files could not generate certain features and are not included (reflected in n=23532 vs 23533); sampling_strategies; audio_quality_metrics.tsv in description.",
   "Missing-feature pattern documented; no dedicated missing_data_documentation.",
   [C("anomalies.anomaly_details", "could not generate certain features")], [A("missing_data_documentation")], [],
   ["sampling_strategies"], None),
 "E6.1": ("Dataset Version Number Provided", 1, SHARED,
   "version 1.1.0.", "Semantic version given.", [C("version", "1.1.0")], [], [], [], None),
 "E6.2": ("Version Access Methods Documented", 1, SHARED,
   "version_access: versions 1.0.0 (Dec. 17, 2025) and 1.1.0 (May 1, 2026), latest-version DOI and v1.1.0 DOI.",
   "Versions and DOIs listed; no explicit URL/DOI for 1.0.0.",
   [C("version_access.latest_version_doi", "doi:10.13026/mf9s-5r03"),
    C("version_access.versions_available", "1.0.0 (Dec. 17, 2025)")], [], [], ["distribution_dates"], None),
 "E6.3": ("Change Descriptions and Errata Provided", 1, SHARED,
   "version_access.version_details describes v1.1 changes (no new participants; free-speech features released after manual checks; audio-quality metrics and per-recording metadata added); cleaning_strategies notes removals in v1.1.",
   "Change log present though not in updates/errata fields.",
   [C("version_access.version_details", "Version 1.1 released no new participants")], [A("errata"), A("updates")], [],
   ["cleaning_strategies"], None),
 "E6.4": ("Update Schedule or Frequency Indicated", 0, SHARED,
   "updates absent; no maintenance plan or update frequency.", "No update schedule.",
   [], [A("updates")], [], ["distribution_dates"], None),
 "E6.5": ("Provenance, Source Derivation, and Raw Data Sources", 1, SHARED,
   "raw_sources: raw audio not included, controlled access via Synapse syn73617068; preprocessing_strategies describe derivation of parquet features and phenotype merge with b2aiprep.",
   "Raw source and derivation documented; was_derived_from absent.",
   [C("raw_sources.raw_data_details", "This PhysioNet project does not contain raw audio."),
    C("preprocessing_strategies.preprocessing_details", "preprocess the raw audio waveforms into the parquet file")],
   [A("was_derived_from")], [], [], None),
 "E7.1": ("Motivation or Purpose for Dataset Creation", 1, ALWAYS,
   "purposes: ethically sourced flagship voice dataset; addressing_gaps: lack of public pediatric voice datasets for ML.",
   "Clear rationale and gap.",
   [C("purposes.response", "ethically sourced flagship dataset"),
    C("addressing_gaps.response", "lack of publicly available pediatric data sets")], [], [], [], None),
 "E7.2": ("Primary Research Objectives or Tasks", 0, ALWAYS,
   "tasks absent; intended_uses give only broad aims (developmental norms, screening tools, clinical insight).",
   "No specific research questions or ML tasks.",
   [], [A("tasks")], [], ["intended_uses"], None),
 "E7.3": ("Funding Sources and Mechanisms Listed", 1, ALWAYS,
   "funders: NIH Common Fund, Bridge2AI Program (grand challenge project).", "Funder and mechanism named.",
   [C("funders.description", "funded by the NIH Common Fund Bridge2AI Program")], [], [], ["funders.grantor"], None),
 "E7.4": ("Grant IDs or Award Numbers Present", 1, ALWAYS,
   "grant_number 3OT2OD032720-01S1 (NIH: type 3 supplement, OT2, OD, serial 032720, year 01, S1).",
   "Valid NIH pattern; source_caveats discloses differing S3/S2 numbers elsewhere in the sources.",
   [C("funders.grants.grant_number", "3OT2OD032720-01S1")], [], [], ["funders.source_caveats"], None),
 "E7.5": ("Creators and Acknowledgements Documented", 1, ALWAYS,
   "creators list with roles/affiliations for many members, principal investigators Bensoussan and Elemento; funder acknowledged.",
   "Extensive creator documentation.",
   [C("creators.name", "Yael Bensoussan"), C("created_by", "Bridge2AI Voice consortium")], [], [], ["funders"], None),
 "E8.1": ("Collection Mechanisms and Settings Described", 1, COLL,
   "collection_mechanisms: age-appropriate protocol, reproschema-ui on tablets, headset or tablet microphone, pediatric acoustic tasks; single-session collection with caregivers.",
   "Detailed procedures and setting; collection timeframe not given.",
   [C("collection_mechanisms.description", "customized software (reproschema-ui)"),
    C("direct_collection.collection_details", "completed the recording and demographic data collection in one session")], [],
   [{"path": "collection_mechanisms", "claimed": 4}], [], None),
 "E8.2": ("Data Acquisition Methods Listed", 1, COLL,
   "acquisition_methods absent, but capture instruments and software (reproschema-ui on tablets, headset or built-in tablet microphone) are stated in collection_mechanisms.",
   "Acquisition instruments named, placed in collection_mechanisms rather than acquisition_methods.",
   [C("collection_mechanisms.description", "A headset was used to record most participants")],
   [A("acquisition_methods")], [], ["raw_sources"], None),
 "E8.3": ("Preprocessing, Cleaning, Labeling, and Annotation Quality", 1, PROC,
   "preprocessing_strategies (export to TSV, b2aiprep feature extraction, static features, BIDS conversion); file descriptions give spectrogram parameters; cleaning_strategies remove sensitive-record features and manual PII checks.",
   "Substantive preprocessing/cleaning; no labeling, annotation or imputation documentation.",
   [C("preprocessing_strategies.preprocessing_details", "transformed into REDCap format"),
    C("cleaning_strategies.cleaning_details", "have been removed from v1.1")],
   [A("labeling_strategies"), A("imputation_protocols")], [{"path": "preprocessing_strategies", "claimed": 4}], [], None),
 "E8.4": ("Software and Tools Documented", 1, SOFT,
   "preprocessing_strategies.used_software: b2aiprep (GitHub, Apache-2.0) produced the parquet features and phenotype files; openSMILE, Praat, parselmouth, torchaudio named for static features.",
   "Processing software that produced released data is named (slot: preprocessing_strategies); release version of b2aiprep not stated.",
   [C("preprocessing_strategies.used_software.name", "b2aiprep (Bridge2AI Data Processing Library)"),
    C("preprocessing_strategies.preprocessing_details", "openSMILE toolkit, Praat, parselmouth and torchaudio")], [], [], [], None),
 "E8.5": ("External Standards, Resources, and Imputation Protocols", 0, ALWAYS,
   "external_resources only the project homepage; conforms_to and imputation_protocols absent; no statement that imputation was not used.",
   "No standards, papers or imputation documentation.",
   [C("external_resources", "https://b2ai-voice.org/")], [A("conforms_to"), A("imputation_protocols")], [], [], None),
 "E9.1": ("Known Limitations Documented", 0, ALWAYS,
   "known_limitations absent. Single-site, English-only recruitment and withheld raw audio are not framed as limitations.",
   "No limitations section.", [], [A("known_limitations")], [], ["anomalies", "sampling_strategies"], None),
 "E9.2": ("Biases Categorized Using Standard Taxonomy (RAI-aligned)", 0, ALWAYS,
   "known_biases and future_use_impacts absent.", "No bias documentation.",
   [], [A("known_biases"), A("future_use_impacts")], [], ["sampling_strategies"], None),
 "E9.3": ("Data Anomalies and Quality Issues Noted", 1, ALWAYS,
   "anomalies: some files could not generate certain features; file-name discrepancies disclosed in file_collections source_caveats.",
   "Specific, if brief, anomaly documentation.",
   [C("anomalies.anomaly_details", "whether due to length or other issues")], [], [], ["file_collections.source_caveats"], None),
 "E9.4": ("Sensitive Content and Warnings Provided", 1, ALWAYS,
   "sensitive_elements: original voice recordings withheld; release limited to low-risk derivations; sensitive-record features removed.",
   "Sensitive content identified and handled; content_warnings absent.",
   [C("sensitive_elements.sensitivity_details", "not the original voice recordings")], [A("content_warnings")], [],
   ["cleaning_strategies"], None),
 "E9.5": ("Ethical Review and Social Impact Analysis", 0, ALWAYS,
   "ethical_reviews present (SickKids REB), but future_use_impacts absent: no downstream social impact analysis, conflicts of interest or mitigations.",
   "Ethical review only; social impact analysis missing.",
   [C("ethical_reviews.reviewing_organization", "Research Ethics Board at the Hospital for Sick Children")],
   [A("future_use_impacts")], [], [], None),
 "E10.1": ("Dataset Published on a Recognized Platform", 1, SHARED,
   "publisher field absent, but the PhysioNet landing page, PhysioNet DOI prefix and citation ('PhysioNet. RRID:SCR_007345') establish publication on PhysioNet.",
   "Recognized platform evident; structured publisher missing (noted).",
   [C("citation", "PhysioNet. RRID:SCR_007345"), C("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/")],
   [A("publisher")], [], [], None),
 "E10.2": ("Citation and DOI for Cross-referencing", 1, SHARED,
   "Full recommended citation with version-specific DOI https://doi.org/10.13026/h995-bt35; record doi 10.13026/mf9s-5r03 (latest version).",
   "Citation and DOI present; two DOIs explained by version_details.",
   [C("citation", "https://doi.org/10.13026/h995-bt35"), C("doi", "10.13026/mf9s-5r03")], [], [], ["version_access.version_details"], None),
 "E10.3": ("Community Standards or Schema Conformance", 0, SHARED,
   "conforms_to absent.", "No community standard stated for the release.",
   [], [A("conforms_to")], [], ["preprocessing_strategies"], None),
 "E10.4": ("Outreach Materials and Documentation Links", 1, SHARED,
   "PhysioNet landing page (with usage examples) and project website https://b2ai-voice.org/.",
   "Documentation links present; no tutorials/webinars.",
   [C("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/"), C("external_resources", "https://b2ai-voice.org/")],
   [], [], [], None),
 "E10.5": ("Related Datasets with Typed Relationships", 0, SHARED,
   "related_datasets absent; the adult Bridge2AI-Voice dataset is mentioned only in source_caveats.",
   "No typed relationships.", [], [A("related_datasets")], [], ["source_caveats"], None),
}

ELEMENTS = [
 (1, "Dataset Discovery and Identification", "Can a user or system discover and uniquely identify this dataset?"),
 (2, "Dataset Access and Retrieval", "Can the dataset and its associated resources be located, accessed, and downloaded?"),
 (3, "Data Reuse and Interoperability", "Is sufficient information provided to reuse and integrate the dataset with others?"),
 (4, "Ethical Use and Privacy Safeguards", "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context?"),
 (5, "Data Composition and Structure", "Can the dataset's structure, modality, and population be understood from metadata?"),
 (6, "Data Provenance and Version Tracking", "Can a user determine dataset versions, update history, and provenance?"),
 (7, "Scientific Motivation and Funding Transparency", "Does the metadata clearly state why the dataset exists and who funded it?"),
 (8, "Technical Transparency (Data Collection and Processing)", "Can data collection and processing steps be replicated or understood?"),
 (9, "Dataset Evaluation and Limitations Disclosure", "Does the metadata communicate known risks, biases, or dataset limitations?"),
 (10, "Cross-Platform and Community Integration", "Does the dataset connect to relevant repositories, communities and standards?"),
]

ISSUES = [
 (["E1.5", "E2.5", "E10.5"], "lowered", "other", "completeness",
  "No parent or related datasets are linked, although source_caveats acknowledges the Bridge2AI-Voice adult dataset on PhysioNet."),
 (["E2.2"], "lowered", "privacy_regulatory", "completeness",
  "No regulatory_restrictions: no confidentiality classification or applicable privacy framework (e.g., PHIPA/HIPAA) for pediatric clinical data; committee_contact unpopulated (email only in access_review_process)."),
 (["E3.3", "E10.3"], "lowered", "variables_metadata", "completeness",
  "No conforms_to/conforms_to_schema for the released files; BIDS appears only as an internal processing step."),
 (["E3.5"], "lowered", "license_use_terms", "completeness",
  "Only intended uses; no prohibited or discouraged uses (e.g., speaker re-identification) for a sensitive pediatric voice dataset."),
 (["E4.2"], "lowered", "privacy_regulatory", "consistency",
  "Human-subjects data released as 'low risk' derivations, yet is_deidentified is absent: no deidentification method or identifiers removed for demographic/phenotype files."),
 (["E4.5"], "lowered", "consent_ethics", "completeness",
  "participant_compensation is not documented."),
 (["E5.3"], "lowered", "variables_metadata", "completeness",
  "is_tabular and subsets (split/subpopulation flags) absent; variables cover only four shared parquet columns."),
 (["E5.4"], "lowered", "other", "semantic_understanding",
  "Health conditions/phenotypes represented among SickKids patient participants are not documented for a voice-as-biomarker dataset."),
 (["E6.4"], "lowered", "temporal_version", "completeness", "No update schedule or maintenance plan."),
 (["E7.2"], "lowered", "other", "completeness", "tasks absent; no specific research questions or ML tasks."),
 (["E8.5"], "lowered", "processing_provenance", "completeness",
  "No standards, publications or imputation protocol (or statement that imputation was not used); external_resources is only the project homepage."),
 (["E9.1"], "lowered", "bias_quality", "completeness",
  "known_limitations absent despite evident limits (single site, English-only, raw audio withheld)."),
 (["E9.2"], "lowered", "bias_quality", "completeness",
  "No known_biases or future_use_impacts; selection/representativeness bias from single-site English-proficient recruitment not categorized."),
 (["E9.5"], "lowered", "consent_ethics", "completeness",
  "No downstream social impact analysis or conflicts-of-interest statement; only the REB approval."),
 ([], "noted_only", "persistent_identifier", "consistency",
  "Record doi 10.13026/mf9s-5r03 is the latest-version DOI while the citation uses the v1.1.0 DOI 10.13026/h995-bt35; version_details explains both."),
 ([], "noted_only", "source_conflict", "content_accuracy",
  "Grant number 3OT2OD032720-01S1 differs from the S3 RePORTER record and S2 footer in the sources; disclosed in funders.source_caveats."),
 ([], "noted_only", "format_access", "completeness",
  "No download_url or structured publisher; PhysioNet platform is evident from page and citation."),
 ([], "noted_only", "scope_drift", "content_accuracy",
  "Re-identification risk, assent and guardian-consent statements come from the multi-site protocol of the wider study, as disclosed in source_caveats."),
 ([], "noted_only", "format_access", "completeness",
  "Character encoding unstated; Parquet has no media_type."),
]

# Per-issue (severity, fields_involved, recommendation), in ISSUES order.
EXTRA = [
 ("medium", ["parent_datasets", "related_datasets"], "Add a related_datasets entry for the adult Bridge2AI-Voice PhysioNet dataset with a typed relationship."),
 ("medium", ["regulatory_restrictions", "data_governance.committee_contact"], "Document confidentiality level, applicable privacy law and move the DACO address to committee_contact."),
 ("medium", ["conforms_to", "conforms_to_schema"], "State any standard the released files or dictionaries conform to, or state none applies."),
 ("medium", ["prohibited_uses", "discouraged_uses"], "Add prohibited uses from the DUA (e.g., re-identification attempts) and discouraged uses."),
 ("high", ["is_deidentified", "human_subject_research"], "Describe the deidentification method and identifiers removed from demographic and phenotype data."),
 ("low", ["participant_compensation"], "State whether participants or families were compensated."),
 ("low", ["is_tabular", "subsets", "variables"], "Add is_tabular and subsets describing folders and any splits; list phenotype variables."),
 ("medium", ["instances"], "List the clinical conditions or diagnostic groups represented among patient participants."),
 ("low", ["updates"], "Document the update or maintenance plan."),
 ("low", ["tasks"], "List intended ML tasks or research questions."),
 ("medium", ["external_resources", "imputation_protocols", "conforms_to"], "Link publications and standards; state whether imputation was used."),
 ("medium", ["known_limitations"], "Add a known_limitations section."),
 ("medium", ["known_biases", "future_use_impacts"], "Categorize selection and representativeness biases."),
 ("medium", ["future_use_impacts", "ethical_reviews"], "Add downstream social impact analysis and mitigations."),
 ("low", ["doi", "citation", "version_access"], "Keep both DOIs but state which is version-specific in the doi field context."),
 ("low", ["funders.grants"], "Confirm the supplement number with the funder record."),
 ("low", ["download_url", "publisher"], "Populate publisher (PhysioNet) and the files URL."),
 ("low", ["participant_privacy", "at_risk_populations"], "Confirm the wider-protocol statements apply to the SickKids pediatric release."),
 ("low", ["distribution_formats", "file_collections"], "State encoding and Parquet media type."),
]


def main():
    context = {}
    ctx_sha = context_digest(context)
    elements, total = [], 0
    for eid, name, desc in ELEMENTS:
        subs, esc = [], 0
        for iid, (n, s, app, ev, qn, cited, absent, counts, considered, nir) in ITEMS.items():
            if not iid.startswith(f"E{eid}."):
                continue
            status = "applicable" if app == ALWAYS else "unknown"
            row = {"path": "#", "score": s, "evidence": ev, "cited": cited, "absent": absent,
                   "counts": counts, "considered": considered}
            sub = {"name": n, "score": s, "evidence": ev, "quality_note": qn, "applicable": True,
                   "applicability_status": status, "applicability_evidence": app,
                   "unit_scores": [row], "item_id": iid}
            if nir:
                sub["no_issue_reason"] = nir
            subs.append(sub)
            esc += s
        total += esc
        elements.append({"id": eid, "name": name, "description": desc, "sub_elements": subs,
                         "element_score": esc, "element_max": 5})
    assert len(EXTRA) == len(ISSUES)
    issues = [{"item_ids": ids, "score_effect": eff, "category": cat, "type": typ, "severity": sev,
               "description": d, "fields_involved": f, "recommendation": r}
              for (ids, eff, cat, typ, d), (sev, f, r) in zip(ISSUES, EXTRA)]
    out = {
        "rubric": "rubric10-semantic", "version": "3.0", "d4d_file": D4D,
        "project": "VOICE_PEDIATRIC", "method": "claudecode_agent",
        "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3",
        "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": {"name": MODEL, "evaluator_model": MODEL, "temperature": None,
                  "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
                  "evaluation_type": "semantic_llm_judge"},
        "overall_score": {"total_points": total, "max_points": 50, "excluded_max_points": 0,
                          "adjusted_max_points": 50, "normalized_percentage": round(total / 50 * 100, 1),
                          "fixed_percentage": round(total / 50 * 100, 1), "sub_elements_not_applicable": 0,
                          "excluded_item_ids": []},
        "elements": elements,
        "semantic_analysis": {
            "issues_detected": issues,
            "semantic_insights": [
                "Strong provenance for derived features: b2aiprep and openSMILE/Praat/parselmouth/torchaudio named, with spectrogram parameters per file.",
                "Human-subjects documentation is strong on ethics review, consent and pediatric assent but lacks a deidentification method and compensation.",
                "Record carefully separates pediatric facts from the wider Bridge2AI-Voice study via source_caveats, at the cost of omitting the adult-dataset relationship.",
                "Limitations, biases, social impact, tasks and standards conformance are entirely undocumented.",
            ],
            "consistency_checks": {"passed": 5, "failed": 1, "warnings": 2},
            "correctness_validations": {
                "doi_format": "valid (10.13026 PhysioNet prefix; two version DOIs explained)",
                "grant_number_format": "valid NIH pattern 3OT2OD032720-01S1; source discrepancy disclosed",
                "rrid_format": "valid RRID:SCR_007345 in citation (PhysioNet)",
                "url_validity": "valid (physionet.org, b2ai-voice.org, synapse.org, github.com)",
            },
        },
        "applicability_context": context,
        "evaluation_scope": {"policy": "single_dataset",
                             "units": [{"path": "#", "id": "doi:10.13026/mf9s-5r03"}],
                             "collection_metadata_inherited": False},
        "metadata": {
            "instrument_sha256": sha(".claude/agents/d4d-rubric10-semantic.md"),
            "evidence_authority_sha256": sha("data/rubric/semantic_evidence_authority_v3.json"),
            "rubric_sha256": sha("data/rubric/rubric10.txt"),
            "input_sha256": sha(D4D),
            "context_sha256": ctx_sha,
        },
    }
    p = ROOT / OUT
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(p, total)


if __name__ == "__main__":
    main()
