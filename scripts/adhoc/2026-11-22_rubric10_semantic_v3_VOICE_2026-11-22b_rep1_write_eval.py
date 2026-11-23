#!/usr/bin/env python3
"""Write the rubric10-semantic (general context instrument v3) evaluation of one VOICE record.

Purpose: serialize the judgements made by the evaluating session (claude-opus-5-5) for
  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/VOICE_d4d.yaml
Inputs: that D4D record (hashed only), .claude/agents/d4d-rubric10-semantic.md, data/rubric/rubric10.txt,
  data/rubric/semantic_evidence_authority_v3.json. No caller applicability context (empty context).
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/VOICE_2026-11-22b_rep1_evaluation.json
Date: 2026-11-22. Scores are the evaluator's judgements; this script only serializes them.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest, normalize_context  # noqa: E402

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/VOICE_d4d.yaml"
OUT = ROOT / "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/VOICE_2026-11-22b_rep1_evaluation.json"
AGENT = ".claude/agents/d4d-rubric10-semantic.md"
RUBRIC = "data/rubric/rubric10.txt"
AUTH = "data/rubric/semantic_evidence_authority_v3.json"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


ALWAYS = ("applicable", "This item applies to every dataset")


def unk(pred):
    return ("unknown", f"{pred}: not declared; retained in the denominator")


def anyunk(*preds):
    return ("unknown", "any: " + "; ".join(f"{p}: not declared; retained in the denominator" for p in preds))


def C(path, quote=None):
    d = {"path": path}
    if quote is not None:
        d["quote"] = quote
    return d


# (item_id, name, score, applicability(status, evidence), evidence, quality_note, cited, absent, counts, considered, no_issue_reason)
E = {}

E[1] = ("Dataset Discovery and Identification", "Can a user or system discover and uniquely identify this dataset?", [
    ("E1.1", "Persistent Identifier (DOI, RRID, or URI)", 1, ALWAYS,
     "doi: 10.13026/37yb-1t42 and id: doi:10.13026/37yb-1t42; 10.13026 is the PhysioNet DOI prefix.",
     "Well-formed DOI with a plausible registrar prefix (PhysioNet), used consistently as id and doi; the citation carries the version DOI 10.13026/8xbn-nq66, which version_access explains as the 3.1.0 release DOI.",
     [C("doi", "10.13026/37yb-1t42"), C("id", "doi:10.13026/37yb-1t42")], [], [], [], None),
    ("E1.2", "Dataset Title and Description Completeness", 1, ALWAYS,
     "Title 'Bridge2AI-Voice: An ethically-sourced, diverse voice dataset linked to health information'; description (>200 chars) states release, participant count, sites and the derived-feature content.",
     "Clear title and a specific description (release 3.1.0, 833 participants, five North American sites, low-risk derived features, no raw recordings).",
     [C("title", "An ethically-sourced, diverse voice dataset linked to health information"),
      C("description", "Release 3.1.0 (v3.1) contains data for 833 participants across five sites in North America.")], [], [], [], None),
    ("E1.3", "Keywords or Tags for Searchability", 0, ALWAYS,
     "keywords lists only four terms: health, biomarkers, bridge2ai, voice.",
     "Below the five-keyword threshold and no method, modality (e.g. spectrogram, acoustic features) or condition terms (voice, neurological, mood, respiratory disorders).",
     [C("/keywords/0", "health")], [], [{"path": "keywords", "claimed": 4}], [], None),
    ("E1.4", "Landing Page and Resources (page, hierarchical resources)", 1, ALWAYS,
     "page: https://physionet.org/content/b2ai-voice/ ; file_collections (features, metadata, phenotype) give the hierarchical file structure.",
     "Accessible PhysioNet landing page plus a structured file-collection hierarchy; no top-level resources slot, which is not required here.",
     [C("page", "https://physionet.org/content/b2ai-voice/"), C("/file_collections/0/name", "features")], [], [], [], None),
    ("E1.5", "Hierarchical Structure (parent datasets, relationships)", 1, ALWAYS,
     "related_datasets: Health Data Nexus v1.0 (has_version) and the Pediatric dataset (references), each with notes.",
     "Typed relationships to the first release and to the sibling pediatric dataset; no parent_datasets, which is acceptable since related datasets with typed relationships are given.",
     [C("/related_datasets/0/relationship_type", "has_version"), C("/related_datasets/1/relationship_type", "references")],
     [], [], [], None),
])

E[2] = ("Dataset Access and Retrieval", "Can the dataset and its associated resources be located, accessed, and downloaded?", [
    ("E2.1", "Access Policy and IP Restrictions Defined", 1, ALWAYS,
     "license_and_use_terms: credentialed access requiring a signed DUA under the Bridge2AI Voice Registered Access License; ip_restrictions lists three IP/sale restrictions.",
     "Clear access policy and explicit IP restrictions (no sale, no IP claims, no IP protection that blocks access).",
     [C("/license_and_use_terms/license_terms", "only credentialed users who sign the data use agreement"),
      C("/ip_restrictions/restrictions/0", "Sale of all or part of the Data on any media is not permitted.")], [], [], [], None),
    ("E2.2", "Regulatory Compliance and Confidentiality Classification", 0, unk("regulated_access"),
     "regulatory_restrictions names only a Certificate of Confidentiality, and its own caveat says this is from the DTUA for the controlled raw-audio route and is not stated for the released features; data_governance names DACO but gives no committee contact; no confidentiality_level or hipaa_compliant/other_compliance classification.",
     "Regulatory content is thin and, by the record's own caveat, scoped to a different access route; no confidentiality classification and no governance contact for the released data.",
     [C("/regulatory_restrictions/regulatory_restrictions/0", "Certificate of Confidentiality"),
      C("/regulatory_restrictions/source_caveats", "the release page does not state it for the credentialed-access feature release"),
      C("/data_governance/committee_name", "Data Access Compliance Office (DACO)")],
     [{"path": "regulatory_restrictions.confidentiality_level"}, {"path": "regulatory_restrictions.hipaa_compliant"},
      {"path": "data_governance.committee_contact"}],
     [], ["data_governance.access_review_process", "is_deidentified.method"], None),
    ("E2.3", "Download URL or Platform Link Available", 1, ALWAYS,
     "No download_url, but page gives the PhysioNet platform link and license_and_use_terms gives the access route (credentialed users who sign the DUA); raw audio route via Synapse in external_resources.",
     "Platform link and access instructions are available; a direct download_url is absent (noted).",
     [C("page", "https://physionet.org/content/b2ai-voice/"),
      C("/license_and_use_terms/license_terms", "can access the files")], [{"path": "download_url"}], [], [], None),
    ("E2.4", "Distribution Formats and File Types Specified", 1, ALWAYS,
     "file_collections describe Parquet feature files, TSV files with media_type text/tab-separated-values and JSON data dictionaries.",
     "Specific formats and MIME types are given for the TSV resources; Parquet stated in descriptions; distribution_formats absent but file-level formats suffice.",
     [C("/file_collections/0/resources/9/format", "TSV"),
      C("/file_collections/0/resources/9/media_type", "text/tab-separated-values"),
      C("/file_collections/0/description", "Dense binary files are distributed as Parquet")], [], [], [], None),
    ("E2.5", "Related Datasets and External Resources Linked", 1, ALWAYS,
     "related_datasets (2 entries) and external_resources (REDCap data dictionary on GitHub/Zenodo; Synapse raw-audio route).",
     "Concrete links to related datasets and external documentation.",
     [C("/external_resources/0/external_resources/0", "https://github.com/eipm/bridge2ai-redcap"),
      C("/related_datasets/1/target_dataset", "https://doi.org/10.13026/mf9s-5r03")], [], [], [], None),
])

E[3] = ("Data Reuse and Interoperability", "Is sufficient information provided to reuse and integrate the dataset with others?\nNote: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.\n", [
    ("E3.1", "License Terms Allow Reuse", 1, unk("shared_dataset"),
     "license: Bridge2AI Voice Registered Access License; license_terms describe credentialed access under a signed agreement; intended uses (pretraining, fine-tuning, benchmarking, validation) are permitted.",
     "A named access license with reuse conditions; it is a custom registered-access license rather than an open license, and redistribution terms are not stated.",
     [C("license", "Bridge2AI Voice Registered Access License"),
      C("/license_and_use_terms/license_terms", "under the Bridge2AI Voice Registered Access License")], [], [], [], None),
    ("E3.2", "Data Formats Are Standardized (encoding, format)", 1, unk("shared_dataset"),
     "Parquet, TSV and JSON data dictionaries in file_collections; TSV resources carry format and media type.",
     "Standard open formats; character encoding is not stated, a minor gap.",
     [C("/file_collections/0/resources/10/format", "TSV"),
      C("/file_collections/2/description", "as TSV data files each with a JSON data dictionary")],
     [{"path": "distribution_formats"}], [], [], None),
    ("E3.3", "Schema or Ontology Conformance Stated", 0, unk("shared_dataset"),
     "No conforms_to or conforms_to_schema; the only standard mentioned (BIDS v1.9.0) applies to the raw data, which the record says is not part of this release.",
     "No schema or ontology conformance is declared for the released files.",
     [C("/raw_data_sources/0/source_description", "The raw audio is not part of this release.")],
     [{"path": "conforms_to"}, {"path": "conforms_to_schema"}], [], [], None),
    ("E3.4", "Variable Metadata with Identifiers Defined", 1, unk("shared_dataset"),
     "variables: participant_id and session_id flagged is_identifier: true, plus task_name and n_frames, each with descriptions; each file has a JSON data dictionary.",
     "Identifier variables are defined, enabling joins across feature files; coverage is minimal (no phenotype columns), noted.",
     [C("/variables/0/variable_name", "participant_id"), C("/variables/0/is_identifier"),
      C("/variables/1/description", "Unique identifier for the recording session")], [], [{"path": "variables", "claimed": 4}], [], None),
    ("E3.5", "Use Guidance Provided (intended, prohibited uses)", 1, ALWAYS,
     "intended_uses (AI pretraining/fine-tuning/benchmarking/validation), prohibited_uses (re-identification, harm/stigmatization, contacting subjects) and discouraged_uses (hiring, insurance, surveillance).",
     "All three categories of use guidance are present and specific.",
     [C("/intended_uses/0/description", "AI model pretraining, fine-tuning, benchmarking, or validation."),
      C("/prohibited_uses/0/description", "Attempting to re-identify research participants"),
      C("/discouraged_uses/0/description", "hiring decisions, insurance premium")], [], [], [], None),
])

E[4] = ("Ethical Use and Privacy Safeguards", "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.", [
    ("E4.1", "IRB or Ethics Review and Data Protection Impact", 1, anyunk("human_subjects", "regulated_access"),
     "human_subject_research.involves_human_subjects: true; ethical_reviews: USF IRB approval via the single IRB process, plus separate Canadian REB review for MSH, SickKids and UofT.",
     "Named reviewing body and process, consistent with the human-subjects flag; no data_protection_impacts assessment, but the ethics review satisfies the item.",
     [C("/ethical_reviews/0/reviewing_organization", "University of South Florida Institutional Review Board"),
      C("/human_subject_research/involves_human_subjects")], [{"path": "data_protection_impacts"}], [], [], None),
    ("E4.2", "Deidentification Method Described", 1, anyunk("human_subjects", "regulated_access"),
     "is_deidentified.method: HIPAA Safe Harbor identifiers removed; identifiers_removed lists direct identifiers, state/province and raw voice; details describe transcript review and feature exclusion.",
     "Named method, enumerated identifiers removed, and voice-specific steps; appropriate for derived acoustic features.",
     [C("/is_deidentified/method", "HIPAA Safe Harbor identifiers were removed"),
      C("/is_deidentified/identifiers_removed", "all raw voice data")], [], [], [], None),
    ("E4.3", "Privacy Protections and Re-identification Risk Assessment", 1, unk("human_subjects"),
     "participant_privacy.reidentification_risk acknowledges residual voice re-identification risk; mitigations: release of derived features only, removal of spectrograms for free speech and sensitive records, controlled access for raw audio, prohibition of re-identification.",
     "Explicit risk statement with concrete mitigation measures elsewhere in the record.",
     [C("/participant_privacy/0/reidentification_risk", "a voice can never be fully de-identified"),
      C("/is_deidentified/deidentification_details", "Spectrograms and similar features were excluded if the audio contained free speech")], [], [], [], None),
    ("E4.4", "Informed Consent Obtained from Participants", 1, unk("human_subjects"),
     "informed_consent: consent_obtained true, prospective consent covering collection and sharing, scope (registered-access sharing), documentation modes (paper, electronic, video); consent_revocations describes withdrawal.",
     "Consent procedure, scope, modes and withdrawal mechanism are all documented.",
     [C("/informed_consent/0/consent_documentation", "by signing a physical paper copy"),
      C("/consent_revocations/0/description", "they may withdraw from the study at any point")], [], [], [], None),
    ("E4.5", "Vulnerable Populations and Compensation Documented", 0, unk("human_subjects"),
     "participant_compensation is detailed ($40/$80 gift cards, max $120, adults only), but at_risk_populations is absent although the cohorts include mood/psychiatric and neurological disorder participants.",
     "Compensation half is well documented; no protections or statement about vulnerable/at-risk participants, so the item is incomplete.",
     [C("/participant_compensation/0/compensation_amount", "maximum compensation of $120"),
      C("/subpopulations/3/description", "Participants selected for known mood disorders.")],
     [{"path": "at_risk_populations"}], [], [], None),
])

E[5] = ("Data Composition and Structure", "Can the dataset's structure, modality, and population be understood from metadata?", [
    ("E5.1", "Cohort or Subpopulations Characteristics Described", 1, ALWAYS,
     "subpopulations: identification by age, gender, sex, ethnicity, SES and four disorder cohorts; sampling_strategies: recruitment from high-volume expert clinics on inclusion/exclusion criteria.",
     "Cohort structure and population characteristics are described; demographic distributions are not given.",
     [C("/subpopulations/0/identification", "Age, Gender, Sex, Ethnicity, Socioeconomic status"),
      C("/subpopulations/1/name", "Voice disorders")], [{"path": "subsets.is_subpopulation"}], [], [], None),
    ("E5.2", "Number of Instances or Samples Reported", 1, ALWAYS,
     "instances.counts: 833 participants; per-file recording counts (e.g. n=29289) in file descriptions.",
     "Specific participant count with per-file sample sizes.",
     [C("/instances/0/counts"), C("/instances/0/instance_type", "person")], [], [], [], None),
    ("E5.3", "Variable-Level Metadata, Tabular Flag, and Data Splits", 0, ALWAYS,
     "Only four variables documented; is_tabular absent; no subsets with is_data_split or is_subpopulation flags.",
     "Variable coverage is minimal for a release with phenotype tables, and neither the tabular flag nor subset-role flags are documented.",
     [C("/variables/2/variable_name", "task_name")],
     [{"path": "is_tabular"}, {"path": "subsets"}], [{"path": "variables", "claimed": 4}], [], None),
    ("E5.4", "Data Topics or Conditions Represented", 1, ALWAYS,
     "Instances are participants; the record names voice, neurological, mood and respiratory disorder cohorts and the clinical/questionnaire data topics.",
     "Conditions represented are explicit.",
     [C("/instances/0/description", "Each instance represents a person (participant)."),
      C("/subpopulations/2/name", "Neurological disorders"),
      C("/subpopulations/4/name", "Respiratory disorders")], [], [], [], None),
    ("E5.5", "Data Quality, Anomalies, and Missing Data Documented", 1, ALWAYS,
     "anomalies (site configurations, protocol change), sampling_strategies (non-probability, not representative), missing_data_documentation (causes, patterns, handling, missingness table).",
     "All three facets documented with specifics.",
     [C("/anomalies/0/anomaly_details", "the collection protocol changed over the course of the study"),
      C("/missing_data_documentation/0/handling_strategy", "a missingness table is included with the dataset"),
      C("/sampling_strategies/0/strategies", "Non-probability sample.")], [], [], [], None),
])

E[6] = ("Data Provenance and Version Tracking", "Can a user determine dataset versions, update history, and provenance?", [
    ("E6.1", "Dataset Version Number Provided", 1, unk("shared_dataset"),
     "version: 3.1.0, consistent with description and distribution_dates.",
     "Clear semantic version.",
     [C("version", "3.1.0")], [], [], [], None),
    ("E6.2", "Version Access Methods Documented", 1, unk("shared_dataset"),
     "version_access: latest_version_doi, versions_available (1.1 to 3.1.0), each version has a unique DOI, earlier version on Health Data Nexus.",
     "How to reach versions is documented with DOIs.",
     [C("/version_access/version_details", "each version has a unique DOI"),
      C("/version_access/latest_version_doi", "doi:10.13026/37yb-1t42")], [], [{"path": "/version_access/versions_available", "claimed": 5}], [], None),
    ("E6.3", "Change Descriptions and Errata Provided", 1, unk("shared_dataset"),
     "errata: 3.1.0 fixed broken parquet files; version_details: minor update, no new participants, some additional data; sensitive features removed from v3.1.",
     "Specific change descriptions and an erratum.",
     [C("/errata/0/erratum_details", "Release 3.1.0 fixed broken parquet files from the previous release."),
      C("/version_access/version_details", "minor update with no new participants")], [], [], [], None),
    ("E6.4", "Update Schedule or Frequency Indicated", 1, unk("shared_dataset"),
     "updates.frequency: planned semi-annual releases (from the v2.0.0 healthsheet naming Health Data Nexus).",
     "An explicit frequency is stated; it is caveated as from an earlier version's documentation.",
     [C("/updates/frequency", "Planned semi-annual (twice a year) releases")], [], [], [], None),
    ("E6.5", "Provenance, Source Derivation, and Raw Data Sources", 1, unk("shared_dataset"),
     "raw_data_sources: raw audio and questionnaires from ReproSchema-UI/REDCap converted to BIDS v1.9.0, WAV format, controlled access; preprocessing describes derivation of features.",
     "Source provenance and derivation are described; was_derived_from absent but not required.",
     [C("/raw_data_sources/0/source_description", "converted to be compliant with the Brain Imaging Data Structure (BIDS) v1.9.0"),
      C("/raw_data_sources/0/raw_data_format", "WAV")], [{"path": "was_derived_from"}], [], [], None),
])

E[7] = ("Scientific Motivation and Funding Transparency", "Does the metadata clearly state why the dataset exists and who funded it?", [
    ("E7.1", "Motivation or Purpose for Dataset Creation", 1, ALWAYS,
     "purposes: ethically sourced, diverse voice database linked to health biomarkers; addressing_gaps lists four research gaps.",
     "Clear scientific rationale and gaps addressed.",
     [C("/purposes/0/description", "linked to multimodal health biomarkers to fuel voice AI research")], [], [], [], None),
    ("E7.2", "Primary Research Objectives or Tasks", 1, ALWAYS,
     "tasks: training ML models for disease detection and classification using voice data; purposes add clinically applicable diagnostic models.",
     "A single but specific ML task aligned with purposes and funding goals.",
     [C("/tasks/0/description", "disease detection and classification using voice data")], [], [], [], None),
    ("E7.3", "Funding Sources and Mechanisms Listed", 1, ALWAYS,
     "funders: NIH Common Fund Bridge2AI Program, grantor NIH Common Fund, OT2 award mechanism.",
     "Named funder and programme with mechanism.",
     [C("/funders/0/name", "NIH Common Fund Bridge2AI Program"), C("/funders/0/grantor", "NIH Common Fund")], [], [], [], None),
    ("E7.4", "Grant IDs or Award Numbers Present", 1, ALWAYS,
     "grant_number OT2OD032720 and 3OT2OD032720-01S1 (NIH OT2, Office of the Director).",
     "Both follow the NIH convention (activity code OT2, IC OD, serial; full application number with supplement suffix). The caveat notes a different supplement (01S3) in RePORTER, recorded transparently.",
     [C("/funders/0/grants/0/grant_number", "OT2OD032720"), C("/funders/0/grants/1/grant_number", "3OT2OD032720-01S1")], [], [], [], None),
    ("E7.5", "Creators and Acknowledgements Documented", 1, ALWAYS,
     "creators: full author list matching the citation, with PI roles and affiliations for Bensoussan (USF) and Elemento (Weill Cornell); funder acknowledgement.",
     "Comprehensive creator list with PI designation.",
     [C("/creators/0/name", "Yael Bensoussan"),
      C("/creators/3/principal_investigator/affiliation/0/name", "Weill Cornell Medicine")], [], [], [], None),
])

E[8] = ("Technical Transparency (Data Collection and Processing)", "Can data collection and processing steps be replicated or understood?\nNote: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.\n", [
    ("E8.1", "Collection Mechanisms and Settings Described", 1, unk("data_collection"),
     "collection_mechanisms: Bridge2AI-Voice App on iPad with headset, Avid AE-36 microphone, REDCap; direct_collection: in clinic with a trained research assistant.",
     "Procedures and setting are described; collection timeframes are not given beyond release dates.",
     [C("/collection_mechanisms/0/description", "data collection was conducted using the application on a tablet, with a headset when possible"),
      C("/direct_collection/0/collection_details", "Data is collected in the clinic")], [], [], [], None),
    ("E8.2", "Data Acquisition Methods Listed", 1, unk("data_collection"),
     "acquisition_methods: directly observed and subject-reported, clinically verified diagnoses; devices listed in collection_mechanisms; raw sources ReproSchema-UI/REDCap.",
     "Methods and instruments are named.",
     [C("/acquisition_methods/0/acquisition_details", "Clinical diagnoses were verified by clinicians"),
      C("/collection_mechanisms/3/name", "Avid AE-36 microphone")], [], [], [], None),
    ("E8.3", "Preprocessing, Cleaning, Labeling, and Annotation Quality", 1, unk("data_processing"),
     "preprocessing_strategies (REDCap export, mono 16 kHz resampling with Butterworth filter, feature extraction parameters), cleaning_strategies (audit protocol), labeling_strategies (clinician diagnosis, ICD-10), machine_annotation_tools (Whisper).",
     "Detailed, replicable pipeline description; no imputation protocol and no annotation-agreement analysis (single annotator).",
     [C("/preprocessing_strategies/1/description", "resampling to 16 kHz with a Butterworth anti-aliasing filter applied"),
      C("/cleaning_strategies/0/cleaning_details", "Check distributions and outliers"),
      C("/labeling_strategies/0/data_annotation_protocol", "Per Bridge2AI Protocols and ICD-10 codes.")], [], [], [], None),
    ("E8.4", "Software and Tools Documented", 1, unk("processing_software"),
     "preprocessing_strategies.used_software: b2aiprep v3.0.0 (release 3.1.0 generated with it) and SenseLab; preprocessing_details name OpenSMILE, Parselmouth/Praat, sparc, ppgs, torchaudio; machine_annotation_tools: OpenAI Whisper Large.",
     "Software that transformed the released data is named, with a version and repository for b2aiprep (slot: preprocessing_strategies.used_software).",
     [C("/preprocessing_strategies/0/used_software/0/name", "b2aiprep"),
      C("/preprocessing_strategies/0/used_software/0/version", "3.0.0"),
      C("/machine_annotation_tools/0/tools/0", "OpenAI Whisper Large")], [], [], [], None),
    ("E8.5", "External Standards, Resources, and Imputation Protocols", 0, ALWAYS,
     "external_resources give the REDCap data dictionary (GitHub, Zenodo) and the Synapse raw-audio route, but conforms_to is absent and there is no imputation protocol or statement that imputation was not used.",
     "External documentation present; standards and the imputation component are missing, so the item is incomplete.",
     [C("/external_resources/0/name", "Bridge2AI REDCap data dictionary and metadata")],
     [{"path": "imputation_protocols"}, {"path": "conforms_to"}], [], [], None),
])

E[9] = ("Dataset Evaluation and Limitations Disclosure", "Does the metadata communicate known risks, biases, or dataset limitations?", [
    ("E9.1", "Known Limitations Documented", 1, ALWAYS,
     "known_limitations: five entries (unequal disease distribution, unaudited transcription models, site-device confounding, confounders, inconsistent responses across visits).",
     "Explicit and specific limitations.",
     [C("/known_limitations/1/limitation_description", "off-the-shelf models that have not been audited for correctness")],
     [], [{"path": "known_limitations", "claimed": 5}], [], None),
    ("E9.2", "Biases Categorized Using Standard Taxonomy (RAI-aligned)", 0, ALWAYS,
     "known_biases: two free-text descriptions (skews by disorder/site/demographics; recruitment less likely for groups with less trust or proximity) with one mitigation; no bias_type and no future_use_impacts.",
     "Biases are described but not categorized against any bias taxonomy.",
     [C("/known_biases/0/bias_description", "skews based on disorder category, site, and other demographic factors"),
      C("/known_biases/1/bias_description", "less likely to be")], [{"path": "bias_type"}, {"path": "future_use_impacts"}], [], [], None),
    ("E9.3", "Data Anomalies and Quality Issues Noted", 1, ALWAYS,
     "anomalies: different site collection configurations and protocol changes; missing features for some files; errata on broken parquet files.",
     "Quality issues documented.",
     [C("/anomalies/0/anomaly_details", "Different sites have different collection configurations"),
      C("/missing_data_documentation/1/missing_data_causes", "could not generate certain features")], [], [], [], None),
    ("E9.4", "Sensitive Content and Warnings Provided", 1, ALWAYS,
     "sensitive_elements: race, sexual orientation, socioeconomic and health information; content_warnings: possible offensive content in free-speech transcriptions.",
     "Both sensitive elements and a content warning are given; caveated as from the v2.0.0 healthsheet.",
     [C("/sensitive_elements/1/name", "Sexual orientation information"),
      C("/content_warnings/0/warnings/0", "inclusion of offensive or unsafe content is unlikely")], [], [], [], None),
    ("E9.5", "Ethical Review and Social Impact Analysis", 1, ALWAYS,
     "ethical_reviews (USF IRB, Canadian REBs); downstream social harms named with mitigations in discouraged_uses (hiring, insurance, surveillance leading to discrimination) and prohibited_uses (stigmatization, re-identification).",
     "Ethics review documented and anticipated social harms with mitigations present; no future_use_impacts slot or conflict-of-interest statement (noted).",
     [C("/ethical_reviews/0/review_details", "Data collection and sharing was approved"),
      C("/discouraged_uses/0/description", "surveillance that could lead to discrimination or harm")], [{"path": "future_use_impacts"}], [], [], None),
])

E[10] = ("Cross-Platform and Community Integration", "Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain.", [
    ("E10.1", "Dataset Published on a Recognized Platform", 1, unk("shared_dataset"),
     "No publisher slot, but the citation names PhysioNet, the page is physionet.org and the DOI uses the PhysioNet prefix.",
     "Publication on PhysioNet is clear from citation, page and DOI; the structured publisher field is absent (noted).",
     [C("citation", "PhysioNet. RRID:SCR_007345."), C("page", "https://physionet.org/content/b2ai-voice/")],
     [{"path": "publisher"}], [], [], None),
    ("E10.2", "Citation and DOI for Cross-referencing", 1, unk("shared_dataset"),
     "citation with authors, year, title, version, PhysioNet RRID and DOI https://doi.org/10.13026/8xbn-nq66; doi field 10.13026/37yb-1t42 (project-level, latest version).",
     "Recommended citation and DOIs present; the two DOIs differ (version vs project) and version_access explains the relationship.",
     [C("citation", "https://doi.org/10.13026/8xbn-nq66"), C("doi", "10.13026/37yb-1t42")], [], [], [], None),
    ("E10.3", "Community Standards or Schema Conformance", 0, unk("shared_dataset"),
     "conforms_to absent; BIDS is mentioned only for the raw data not in this release.",
     "No community standard declared for the released data.",
     [C("/raw_data_sources/0/source_description", "Brain Imaging Data Structure (BIDS) v1.9.0")],
     [{"path": "conforms_to"}], [], [], None),
    ("E10.4", "Outreach Materials and Documentation Links", 1, unk("shared_dataset"),
     "page (PhysioNet landing) and external_resources (REDCap data dictionary, metadata and instrument PDFs on GitHub and Zenodo).",
     "Documentation links present; no tutorials or webinars, but existing_uses mentions the summer school/hackathon.",
     [C("/external_resources/0/external_resources/1", "https://zenodo.org/records/14989503"),
      C("page", "https://physionet.org/content/b2ai-voice/")], [], [], [], None),
    ("E10.5", "Related Datasets with Typed Relationships", 1, unk("shared_dataset"),
     "related_datasets: has_version (Health Data Nexus v1.0) and references (Pediatric dataset) with DOIs and notes.",
     "Typed relationships with resolvable DOIs; 'references' for the sibling pediatric dataset is a weak type, transparently caveated.",
     [C("/related_datasets/0/target_dataset", "https://doi.org/10.57764/qb6h-em84"),
      C("/related_datasets/1/source_caveats", "no source states a more specific relation")], [], [], [], None),
])

ISSUES = [
    {"item_ids": ["E1.3"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "severity": "medium", "fields_involved": ["keywords"], "recommendation": "Add modality, method and condition keywords (e.g. acoustic features, spectrogram, voice disorders).",
     "description": "Only four keywords (health, biomarkers, bridge2ai, voice); no modality, method or condition terms."},
    {"item_ids": ["E2.2"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "consistency",
     "severity": "medium", "fields_involved": ["regulatory_restrictions", "data_governance"], "recommendation": "State the regulatory status and confidentiality level of the released features and give the governance committee contact.",
     "description": "The only regulatory restriction (Certificate of Confidentiality) is caveated as applying to the controlled raw-audio route, not the released features; no confidentiality classification and no governance committee contact."},
    {"item_ids": ["E3.3", "E10.3"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "severity": "medium", "fields_involved": ["conforms_to", "conforms_to_schema", "raw_data_sources"], "recommendation": "Declare the standards or schemas the released files conform to.",
     "description": "No conforms_to/conforms_to_schema for the released Parquet/TSV files; BIDS v1.9.0 is stated only for raw data excluded from this release."},
    {"item_ids": ["E4.5"], "score_effect": "lowered", "category": "consent_ethics", "type": "completeness",
     "severity": "medium", "fields_involved": ["at_risk_populations", "participant_compensation", "subpopulations"], "recommendation": "Document whether vulnerable populations are included and the protections applied.",
     "description": "at_risk_populations absent although cohorts include mood/psychiatric and neurological disorder participants; compensation alone is documented."},
    {"item_ids": ["E5.3"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "severity": "medium", "fields_involved": ["variables", "is_tabular", "subsets"], "recommendation": "Document phenotype variables, the tabular flag and subset roles.",
     "description": "Variable metadata covers four feature-file keys only; is_tabular and subset split/subpopulation flags are absent."},
    {"item_ids": ["E8.5"], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
     "severity": "low", "fields_involved": ["imputation_protocols", "conforms_to", "external_resources"], "recommendation": "State whether imputation was used and how.",
     "description": "No imputation protocol or statement that imputation was not used, and no standards conformance, despite documented missingness."},
    {"item_ids": ["E9.2"], "score_effect": "lowered", "category": "bias_quality", "type": "completeness",
     "severity": "low", "fields_involved": ["known_biases"], "recommendation": "Categorize biases with bias_type and describe future-use impacts.",
     "description": "Known biases are free text without bias_type categorization or future_use_impacts."},
    {"item_ids": [], "score_effect": "noted_only", "category": "persistent_identifier", "type": "consistency",
     "severity": "low", "fields_involved": ["citation", "doi", "version_access"], "recommendation": "No change required; optionally state which DOI to cite.",
     "description": "Citation DOI (10.13026/8xbn-nq66, version 3.1.0) differs from doi/id (10.13026/37yb-1t42, project latest); version_access explains the relationship, so consistent."},
    {"item_ids": [], "score_effect": "noted_only", "category": "license_use_terms", "type": "consistency",
     "severity": "low", "fields_involved": ["license", "license_and_use_terms"], "recommendation": "Align the license name with the access tier stated on the release page.",
     "description": "Top-level license names a 'Registered Access License' while license_terms describe credentialed access; the record caveats the tier-1 vs tier-2 source disagreement."},
    {"item_ids": [], "score_effect": "noted_only", "category": "source_conflict", "type": "content_accuracy",
     "severity": "low", "fields_involved": ["purposes"], "recommendation": "No change required beyond the existing caveat.",
     "description": "Purpose target size conflicts (30 000 vs 10,000 voices) across sources; recorded transparently as targets, not achieved counts."},
    {"item_ids": [], "score_effect": "noted_only", "category": "format_access", "type": "completeness",
     "severity": "low", "fields_involved": ["download_url", "publisher", "page"], "recommendation": "Populate publisher and a download/access URL.",
     "description": "No download_url or publisher slot; the PhysioNet page and citation carry this information."},
    {"item_ids": [], "score_effect": "noted_only", "category": "consent_ethics", "type": "consistency",
     "severity": "low", "fields_involved": ["consent_revocations"], "recommendation": "No change required beyond the existing caveat.",
     "description": "Withdrawal terms differ between the IRB protocol (data kept until study completion) and the healthsheet (data cannot be removed); caveated in the record."},
]


def build():
    ctx = normalize_context({})
    elements = []
    total = 0
    for eid in range(1, 11):
        name, desc, subs = E[eid]
        out = []
        esum = 0
        for (iid, sname, score, (status, aev), ev, qn, cited, absent, counts, considered, nir) in subs:
            row = {"name": sname, "score": score, "evidence": ev, "quality_note": qn, "applicable": True,
                   "applicability_status": status, "applicability_evidence": aev,
                   "unit_scores": [{"path": "#", "score": score, "evidence": ev, "cited": cited, "absent": absent,
                                    "counts": counts, "considered": considered}],
                   "item_id": iid}
            if nir:
                row["no_issue_reason"] = nir
            out.append(row)
            esum += score
        total += esum
        elements.append({"id": eid, "name": name, "description": desc, "sub_elements": out,
                         "element_score": esum, "element_max": 5})
    return {
        "rubric": "rubric10-semantic",
        "version": "3.0",
        "d4d_file": INPUT,
        "project": "VOICE",
        "method": "claudecode_agent",
        "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1",
        "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": {"name": "claude-opus-5-5", "evaluator_model": "claude-opus-5-5", "temperature": None,
                  "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
                  "evaluation_type": "semantic_llm_judge"},
        "overall_score": {"total_points": total, "max_points": 50, "excluded_max_points": 0,
                          "adjusted_max_points": 50, "normalized_percentage": round(total / 50 * 100, 1),
                          "fixed_percentage": round(total / 50 * 100, 1), "sub_elements_not_applicable": 0},
        "elements": elements,
        "semantic_analysis": {
            "issues_detected": ISSUES,
            "semantic_insights": [
                "Record is transparent about source conflicts and version-specific values via source_caveats.",
                "Strong ethics, consent, deidentification and processing-software documentation; gaps are in standards conformance, bias categorization, at-risk populations and imputation.",
                "No caller applicability context: all conditional items are unknown and retained in the denominator; no items excluded.",
            ],
            "consistency_checks": {"passed": 6, "failed": 1, "warnings": 4},
            "correctness_validations": {
                "doi_format": "valid (10.13026 PhysioNet prefix for doi, citation and related dataset; 10.57764 for Health Data Nexus)",
                "grant_number_format": "valid NIH pattern (OT2OD032720; 3OT2OD032720-01S1)",
                "rrid_format": "valid (RRID:SCR_007345 in citation, PhysioNet)",
                "url_validity": "plausible (physionet.org, github.com, zenodo.org, synapse.org, doi.org)",
            },
        },
        "applicability_context": ctx,
        "evaluation_scope": {"policy": "single_dataset",
                             "units": [{"path": "#", "id": "doi:10.13026/37yb-1t42"}],
                             "collection_metadata_inherited": False},
        "metadata": {"instrument_sha256": sha(AGENT), "evidence_authority_sha256": sha(AUTH),
                     "rubric_sha256": sha(RUBRIC), "input_sha256": sha(INPUT),
                     "context_sha256": context_digest(ctx)},
    }


if __name__ == "__main__":
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(OUT, doc["overall_score"])
