#!/usr/bin/env python3
"""Write one rubric10-semantic v3 evaluation (general context instrument v3).

Purpose: serialize the evaluator's own judgements for the VOICE_PEDIATRIC record of
label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2 (method claudecode_agent).
Inputs: the D4D record, data/rubric/rubric10.txt, the agent definition, the evidence
authority JSON (hashed only). Empty caller applicability context (all predicates unknown).
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/
        VOICE_PEDIATRIC_2026-11-22b_rep2_evaluation.json
Date: 2026-11-22. Evaluator: claude-opus-5-5 (Claude Code session).
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from data_sheets_schema.evaluation_context import applicability, context_digest

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/VOICE_PEDIATRIC_d4d.yaml"
OUT = ROOT / "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/VOICE_PEDIATRIC_2026-11-22b_rep2_evaluation.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


CONTEXT = {}
ALWAYS = "This item applies to every dataset"
RULES = {
    "E2.2": "regulated_access",
    "E3.1": "shared_dataset", "E3.2": "shared_dataset", "E3.3": "shared_dataset", "E3.4": "shared_dataset",
    "E4.1": {"any": ["human_subjects", "regulated_access"]},
    "E4.2": {"any": ["human_subjects", "regulated_access"]},
    "E4.3": "human_subjects", "E4.4": "human_subjects", "E4.5": "human_subjects",
    "E6.1": "shared_dataset", "E6.2": "shared_dataset", "E6.3": "shared_dataset",
    "E6.4": "shared_dataset", "E6.5": "shared_dataset",
    "E8.1": "data_collection", "E8.2": "data_collection",
    "E8.3": "data_processing", "E8.4": "processing_software",
    "E10.1": "shared_dataset", "E10.2": "shared_dataset", "E10.3": "shared_dataset",
    "E10.4": "shared_dataset", "E10.5": "shared_dataset",
}


def C(path, quote=None):
    d = {"path": path}
    if quote is not None:
        d["quote"] = quote
    return d


def A(path):
    return {"path": path}


ELEMENTS = [
    (1, "Dataset Discovery and Identification",
     "Can a user or system discover and uniquely identify this dataset?"),
    (2, "Dataset Access and Retrieval",
     "Can the dataset and its associated resources be located, accessed, and downloaded?"),
    (3, "Data Reuse and Interoperability",
     "Is sufficient information provided to reuse and integrate the dataset with others?\nNote: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.\n"),
    (4, "Ethical Use and Privacy Safeguards",
     "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement."),
    (5, "Data Composition and Structure",
     "Can the dataset's structure, modality, and population be understood from metadata?"),
    (6, "Data Provenance and Version Tracking",
     "Can a user determine dataset versions, update history, and provenance?"),
    (7, "Scientific Motivation and Funding Transparency",
     "Does the metadata clearly state why the dataset exists and who funded it?"),
    (8, "Technical Transparency (Data Collection and Processing)",
     "Can data collection and processing steps be replicated or understood?\nNote: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.\n"),
    (9, "Dataset Evaluation and Limitations Disclosure",
     "Does the metadata communicate known risks, biases, or dataset limitations?"),
    (10, "Cross-Platform and Community Integration",
     "Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain."),
]

# item_id: (name, score, evidence, quality_note, cited, absent, counts, considered, no_issue_reason)
ITEMS = {
    "E1.1": ("Persistent Identifier (DOI, RRID, or URI)", 1,
             "doi: 10.13026/h995-bt35; id: doi:10.13026/h995-bt35. Prefix 10.13026 is PhysioNet's, consistent with the PhysioNet page and citation.",
             "Valid DOI format with a plausible PhysioNet prefix; id reuses the DOI as a CURIE.",
             [C("doi", "10.13026/h995-bt35"), C("id", "doi:10.13026/h995-bt35")], [], [], ["citation"], None),
    "E1.2": ("Dataset Title and Description Completeness", 1,
             "title 'Bridge2AI-Voice Pediatric Dataset'; description (>600 chars) states release date, 23,533 recordings, 300 participants aged 2-18 at the Hospital for Sick Children, folder organization, and that raw audio is excluded.",
             "Specific, quantitative, release-scoped description.",
             [C("title", "Bridge2AI-Voice Pediatric Dataset"),
              C("description", "contains derived audio features for 23,533 recordings collected from 300 participants aged 2-18 at the Hospital for Sick Children")],
             [], [], ["name"], None),
    "E1.3": ("Keywords or Tags for Searchability", 1,
             "keywords: health, pediatric, biomarkers, bridge2ai, voice (5 entries).",
             "Meets the >=5 threshold and covers domain/population; no method or condition terms (e.g. acoustic features, speech) so searchability is basic.",
             [C("keywords", "pediatric")], [], [{"path": "keywords", "claimed": 5}], [], None),
    "E1.4": ("Landing Page and Resources (page, hierarchical resources)", 1,
             "page: https://physionet.org/content/b2ai-voice-pediatric/1.1.0/ (version-specific PhysioNet landing page). No resources hierarchy, but file_collections organizes features/phenotype/metadata.",
             "Accessible, version-specific landing page.",
             [C("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/")], [A("resources")], [], ["file_collections"], None),
    "E1.5": ("Hierarchical Structure (parent datasets, relationships)", 0,
             "parent_datasets and related_datasets absent. source_caveats mentions the Bridge2AI-Voice Adult Dataset on PhysioNet but explicitly declines to record a relationship; raw audio on Synapse is described only as an access route.",
             "No typed parent or related dataset links; the omission is transparently justified but the sub-element is unmet.",
             [C("source_caveats", "no related_datasets entry is recorded")], [A("parent_datasets"), A("related_datasets")], [], ["raw_sources"], None),
    "E2.1": ("Access Policy and IP Restrictions Defined", 1,
             "license_and_use_terms.license_terms: credentialed users who sign the data use agreement; Bridge2AI Voice Registered Access License and Agreement; restricted-access resource. data_governance describes registered vs controlled access tiers.",
             "Clear, actionable access policy. ip_restrictions absent but not needed for a pass.",
             [C("license_and_use_terms.license_terms", "only credentialed users who sign the data use agreement can access the files"),
              C("license", "Bridge2AI Voice Registered Access License")],
             [A("ip_restrictions")], [], ["data_governance"], None),
    "E2.2": ("Regulatory Compliance and Confidentiality Classification", 0,
             "regulatory_restrictions absent (no confidentiality_level, hipaa_compliant or other_compliance); data_governance.committee_contact absent. data_governance names the Data Access Compliance Office and its review process, and its prose gives DACO@b2ai-voice.org.",
             "Governance process is described, but no regulatory framework compliance (e.g. Canadian PHIPA/PIPEDA, HIPAA) or confidentiality classification is stated.",
             [C("data_governance.committee_name", "Data Access Compliance Office")],
             [A("regulatory_restrictions"), A("data_governance.committee_contact")], [],
             ["data_governance.access_review_process"], None),
    "E2.3": ("Download URL or Platform Link Available", 1,
             "download_url absent, but page gives the PhysioNet platform link and license_and_use_terms/data_governance give platform access instructions (register on PhysioNet, confirm identity, sign the agreement); raw audio route via Synapse syn73617068.",
             "Credited for a platform link plus access instructions (registered-access data cannot have an open direct download link).",
             [C("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/"),
              C("data_governance.access_review_process", "register on PhysioNet and confirm identity")],
             [A("download_url")], [], ["raw_sources"], None),
    "E2.4": ("Distribution Formats and File Types Specified", 1,
             "file_collections: static_features.tsv and audio_quality_metrics.tsv carry format TSV and media_type text/tab-separated-values; features description states binary files are Parquet with JSON data dictionaries.",
             "Formats are specified; the nine Parquet resources lack structured format/media_type fields and distribution_formats is absent.",
             [C("/file_collections/0/resources/9/media_type", "text/tab-separated-values"),
              C("/file_collections/0/description", "Binary files are made available as Parquet")],
             [A("distribution_formats")], [], ["file_collections"], None),
    "E2.5": ("Related Datasets and External Resources Linked", 1,
             "external_resources: https://b2ai-voice.org/; raw_sources links the controlled-access raw audio on Synapse. related_datasets absent.",
             "Minimal pass: one external documentation link and the raw-audio source link; no typed related datasets.",
             [C("/external_resources/0/external_resources/0", "https://b2ai-voice.org/"),
              C("/raw_sources/0/access_url", "https://www.synapse.org/Synapse:syn73617068")],
             [A("related_datasets")], [], [], None),
    "E3.1": ("License Terms Allow Reuse", 1,
             "Bridge2AI Voice Registered Access License; reuse by credentialed users after signing the Registered Access Agreement; no training required.",
             "Reuse is permitted under a named registered-access licence and DUA; the specific permitted/prohibited reuse terms are not summarized.",
             [C("license_and_use_terms.license_terms", "License for files: Bridge2AI Voice Registered Access License")],
             [], [], ["license"], None),
    "E3.2": ("Data Formats Are Standardized (encoding, format)", 1,
             "Parquet (open column-oriented format), TSV with media type, JSON data dictionaries.",
             "Standard open formats; character encoding is not stated.",
             [C("/file_collections/0/resources/9/format", "TSV"),
              C("/file_collections/0/description", "Parquet, an open-source column-oriented data file format")],
             [A("distribution_formats")], [], ["file_collections"], None),
    "E3.3": ("Schema or Ontology Conformance Stated", 0,
             "conforms_to and conforms_to_schema absent. Preprocessing mentions conversion through REDCap format to BIDS, but the released Parquet/TSV files are not stated to conform to BIDS or any schema.",
             "No conformance claim for the distributed data.",
             [C("/preprocessing_strategies/0/preprocessing_details", "Brain Imaging Data Structure (BIDS)")],
             [A("conforms_to"), A("conforms_to_schema")], [], [], None),
    "E3.4": ("Variable Metadata with Identifiers Defined", 1,
             "variables: participant_id and session_id (is_identifier: true), task_name, n_frames with descriptions; per-file JSON data dictionaries described.",
             "Linking identifiers are defined; phenotype variables are not enumerated but the data dictionaries are referenced.",
             [C("/variables/0/variable_name", "participant_id"), C("/variables/0/is_identifier")],
             [], [{"path": "variables", "claimed": 4}], [], None),
    "E3.5": ("Use Guidance Provided (intended, prohibited uses)", 0,
             "intended_uses lists three one-line uses (developmental norms, early screening tools, clinical insight); prohibited_uses and discouraged_uses absent.",
             "Intended uses are generic restatements; no prohibited or discouraged use guidance (e.g. re-identification or speaker identification), which matters for pediatric voice data.",
             [C("/intended_uses/1/description", "create AI-driven tools for early screening")],
             [A("prohibited_uses"), A("discouraged_uses")], [{"path": "intended_uses", "claimed": 3}], [], None),
    "E4.1": ("IRB or Ethics Review and Data Protection Impact", 1,
             "ethical_reviews: Research Ethics Board at the Hospital for Sick Children approved data collection and sharing; human_subject_research.ethics_review_board matches.",
             "Consistent with involves_human_subjects: true. data_protection_impacts absent.",
             [C("/ethical_reviews/0/review_details", "Data collection and sharing was approved by the Research Ethics Board at the Hospital for Sick Children"),
              C("human_subject_research.involves_human_subjects")],
             [A("data_protection_impacts")], [], ["human_subject_research.ethics_review_board"], None),
    "E4.2": ("Deidentification Method Described", 0,
             "is_deidentified absent. participant_privacy describes withholding raw audio (release of derived features only), but no de-identification method, standard or list of removed identifiers is given for the phenotype/demographic files.",
             "Human-subjects data with demographic and clinical questionnaires but no deidentification method.",
             [C("/participant_privacy/0/privacy_techniques", "The PhysioNet project does not contain raw audio")],
             [A("is_deidentified")], [], ["source_caveats"], None),
    "E4.3": ("Privacy Protections and Re-identification Risk Assessment", 1,
             "participant_privacy: raw audio disseminated via controlled access only; reidentification_risk: a voice can never be fully de-identified.",
             "Protection plus an explicit re-identification risk statement; the risk statement comes from the umbrella protocol and is attributed as such.",
             [C("/participant_privacy/0/reidentification_risk", "a voice can never be fully de-identified")],
             [], [], ["/participant_privacy/0/privacy_techniques"], None),
    "E4.4": ("Informed Consent Obtained from Participants", 1,
             "informed_consent: consent_obtained true, parental or participant consent, scope data collection and data sharing; consent_revocations and assent_procedures documented.",
             "Consent type, scope, assent and withdrawal are covered.",
             [C("/informed_consent/0/consent_type", "parental or participant consent"),
              C("/consent_revocations/0/revocation_details", "if participants withdraw")],
             [], [], ["collection_consents", "at_risk_populations.assent_procedures"], None),
    "E4.5": ("Vulnerable Populations and Compensation Documented", 1,
             "at_risk_populations: children 2-18, special protections, assent procedures, guardian consent; participant_compensation: protocol provides compensation to the adult population only.",
             "Pediatric protections are well documented; compensation statement implies no pediatric compensation (from the umbrella protocol).",
             [C("at_risk_populations.assent_procedures", "children will provide verbal assent where appropriate"),
              C("/participant_compensation/0/description", "compensation will be provided to the adult population only")],
             [], [], ["human_subject_research.special_populations"], None),
    "E5.1": ("Cohort or Subpopulations Characteristics Described", 1,
             "subpopulations: age groups Peds 10+, 6-10, 4-6, 2-4 at SickKids; sampling_strategies gives inclusion (2-18, English proficiency) and exclusion (non-verbal) criteria; patients and healthy volunteers.",
             "Inclusion/exclusion and age grouping given; no sex/diagnosis distribution or per-group counts.",
             [C("/subpopulations/0/description", "Peds 10+, Peds 6-10, Peds 4-6 and Peds 2-4"),
              C("/sampling_strategies/0/strategies", "eligible if they were 2 to 18 years of age")],
             [], [], [], None),
    "E5.2": ("Number of Instances or Samples Reported", 1,
             "instances: 23,533 recordings and 300 participants; per-file n (23,533 or 23,532) in resource descriptions.",
             "Specific counts, consistent with description.",
             [C("/instances/0/counts"), C("/instances/1/counts")], [], [{"path": "instances", "claimed": 2}], [], None),
    "E5.3": ("Variable-Level Metadata, Tabular Flag, and Data Splits", 0,
             "variables lists only four shared key columns; is_tabular absent; no subsets with is_data_split/is_subpopulation flags. JSON data dictionaries are mentioned but not summarized.",
             "Variable coverage is minimal for the feature and phenotype tables, and tabular/split flags are missing.",
             [C("/variables/3/variable_name", "n_frames")],
             [A("is_tabular"), A("subsets")], [{"path": "variables", "claimed": 4}], [], None),
    "E5.4": ("Data Topics or Conditions Represented", 0,
             "instances describe recordings and participants aged 2-18 only; the record mentions medical-history questionnaires and patients vs healthy volunteers but never names the conditions, diagnoses or phenotype categories represented.",
             "For a voice-as-biomarker health dataset the represented conditions are a core gap.",
             [C("/instances/1/description", "Participants aged 2-18")],
             [], [], ["/data_collectors/0/description", "/collection_mechanisms/0/description"], None),
    "E5.5": ("Data Quality, Anomalies, and Missing Data Documented", 1,
             "missing_data_documentation: features removed for sensitive records in v1.1; some files could not generate certain features; sampling_strategies documents recruitment; audio_quality_metrics.tsv released.",
             "Missing-data patterns and causes plus sampling documented; anomalies slot absent.",
             [C("/missing_data_documentation/0/missing_data_causes", "could not generate certain features")],
             [A("anomalies")], [], ["sampling_strategies"], None),
    "E6.1": ("Dataset Version Number Provided", 1,
             "version: 1.1.0, consistent with name, page URL and citation.",
             "Semantic version present and consistent.",
             [C("version", "1.1.0")], [], [], ["page"], None),
    "E6.2": ("Version Access Methods Documented", 1,
             "version_access: versions_available 1.0.0, 1.1.0; latest_version_doi doi:10.13026/mf9s-5r03; distribution_dates gives release dates.",
             "Versions and a latest-version DOI are given; no per-version URLs. The latest_version_doi differs from the record DOI (plausibly PhysioNet's all-versions DOI; not explained).",
             [C("version_access.latest_version_doi", "doi:10.13026/mf9s-5r03")],
             [], [{"path": "version_access.versions_available", "claimed": 2}], ["distribution_dates"], None),
    "E6.3": ("Change Descriptions and Errata Provided", 1,
             "errata and updates absent, but version_access.version_details gives the v1.1 change description (no new participants; features for manually checked free-speech tasks; audio quality metrics; per-recording metadata) and missing_data_documentation notes removals in v1.1.",
             "Actual release change log present outside the listed slots; no errata.",
             [C("version_access.version_details", "v1.1 is a minor update with no new participants")],
             [A("errata"), A("updates")], [], [], None),
    "E6.4": ("Update Schedule or Frequency Indicated", 0,
             "updates absent; no maintenance plan or frequency stated.",
             "Unmet.",
             [], [A("updates")], [], ["distribution_dates"], None),
    "E6.5": ("Provenance, Source Derivation, and Raw Data Sources", 1,
             "raw_sources: raw audio withheld from PhysioNet, available via Synapse syn73617068 under controlled access; preprocessing_strategies documents derivation from raw waveforms via b2aiprep.",
             "Raw source and derivation path documented; was_derived_from absent.",
             [C("/raw_sources/0/raw_data_details", "raw audio data access for the Bridge2AI Voice pediatric cohort is via Synapse")],
             [A("was_derived_from")], [], ["preprocessing_strategies"], None),
    "E7.1": ("Motivation or Purpose for Dataset Creation", 1,
             "purposes: ethically sourced flagship dataset for voice as a biomarker; addressing_gaps: lack of public pediatric voice datasets.",
             "Clear rationale and gap.",
             [C("/purposes/0/response", "support critical insights into the use of voice as a biomarker of health"),
              C("/addressing_gaps/0/response", "lack of publicly available pediatric data sets")],
             [], [], [], None),
    "E7.2": ("Primary Research Objectives or Tasks", 0,
             "tasks absent. purposes and intended_uses give only broad aims; no specific research questions or ML tasks.",
             "Unmet.",
             [], [A("tasks")], [], ["intended_uses", "purposes"], None),
    "E7.3": ("Funding Sources and Mechanisms Listed", 1,
             "funders: NIH; description: NIH Common Fund Bridge2AI Program, OT2 award.",
             "Named funder and programme.",
             [C("/funders/0/description", "funded by the NIH Common Fund Bridge2AI Program")],
             [], [], ["/funders/0/grantor"], None),
    "E7.4": ("Grant IDs or Award Numbers Present", 1,
             "grants.grant_number 3OT2OD032720-01S1, matching NIH convention (application type 3 supplement, OT2 activity, OD institute, serial 032720, -01S1). source_caveats transparently notes a RePORTER page for -01S3.",
             "Valid NIH-pattern award number, consistent between structured grant and prose.",
             [C("/funders/0/grants/0/grant_number", "3OT2OD032720-01S1")],
             [], [], ["/funders/0/source_caveats"], None),
    "E7.5": ("Creators and Acknowledgements Documented", 1,
             "creators: full author list (~140) with affiliations for leads and principal_investigator entries for Bensoussan and Elemento.",
             "Comprehensive creator listing; no separate acknowledgements.",
             [C("/creators/0/name", "Yael Bensoussan")], [], [], ["funders"], None),
    "E8.1": ("Collection Mechanisms and Settings Described", 1,
             "collection_mechanisms: reproschema-ui on tablets, headset vs built-in microphone, standardized age-appropriate protocol, task list; direct_collection: single session, parents completing surveys.",
             "Procedures and setting described; collection timeframe not given.",
             [C("/collection_mechanisms/0/mechanism_details", "A headset was used to record most participants")],
             [], [], ["direct_collection", "data_collectors"], None),
    "E8.2": ("Data Acquisition Methods Listed", 1,
             "acquisition_methods absent; acquisition devices and software are named in collection_mechanisms (reproschema-ui, tablets, headset or built-in microphone) and direct_collection states participants/parents reported questionnaire data in one session. raw_sources gives only the access route.",
             "Credited on semantic equivalence; device models and recording parameters are not given.",
             [C("/collection_mechanisms/0/mechanism_details", "customized software, reproschema-ui, on tablets"),
              C("/direct_collection/0/collection_details", "parents or decision-makers completed the survey")],
             [A("acquisition_methods")], [], ["raw_sources"], None),
    "E8.3": ("Preprocessing, Cleaning, Labeling, and Annotation Quality", 1,
             "preprocessing_strategies: export/conversion (REDCap, BIDS), waveform feature extraction with b2aiprep, feature derivation with openSMILE/Praat/parselmouth/torchaudio; resource descriptions give STFT parameters; cleaning_strategies: manual check of free-speech tasks for unconsented speakers and PII.",
             "Detailed preprocessing and cleaning; no labeling/annotation analyses.",
             [C("/cleaning_strategies/0/cleaning_details", "manually checked for presence of unconsented speakers and PII")],
             [A("labeling_strategies")], [{"path": "preprocessing_strategies", "claimed": 3}], ["cleaning_strategies"], None),
    "E8.4": ("Software and Tools Documented", 1,
             "preprocessing_strategies[1].used_software: b2aiprep 3.0.0 (Apache-2.0, GitHub) produced the parquet files and phenotype merges; preprocessing_strategies[2].used_software: openSMILE, Praat, parselmouth, torchaudio derived the features. reproschema-ui (collection_mechanisms) is capture software, role (a), neither adds nor subtracts.",
             "Processing software that produced the released data is named with version and repository.",
             [C("/preprocessing_strategies/1/used_software/0/version", "3.0.0"),
              C("/preprocessing_strategies/2/used_software/0/name", "openSMILE")],
             [], [], ["/collection_mechanisms/0/used_software"], None),
    "E8.5": ("External Standards, Resources, and Imputation Protocols", 0,
             "external_resources has only the project homepage; conforms_to absent; imputation_protocols absent and no statement that imputation was not used; no published papers or standards documents linked.",
             "A homepage alone does not meet the external standards/resources scope.",
             [C("/external_resources/0/name", "Bridge2AI-Voice project website")],
             [A("conforms_to"), A("imputation_protocols")], [], [], None),
    "E9.1": ("Known Limitations Documented", 0,
             "known_limitations absent. Limitations such as single-site recruitment, English-only eligibility, mixed headset/built-in microphone recording and absence of raw audio appear only implicitly in other slots.",
             "No explicit limitations section.",
             [], [A("known_limitations")], [], ["sampling_strategies", "collection_mechanisms", "source_caveats"], None),
    "E9.2": ("Biases Categorized Using Standard Taxonomy (RAI-aligned)", 0,
             "known_biases and future_use_impacts absent.",
             "Unmet; evident selection/representation biases (single pediatric hospital, English proficiency) are not categorized.",
             [], [A("known_biases"), A("future_use_impacts")], [], [], None),
    "E9.3": ("Data Anomalies and Quality Issues Noted", 1,
             "anomalies absent, but missing_data_documentation notes files that could not generate certain features due to length or other issues (sparc files n=23532 vs 23533) and removal of sensitive records; audio_quality_metrics.tsv documents recording quality; microphone heterogeneity noted.",
             "Quality issues are documented substantively outside the anomalies slot.",
             [C("/missing_data_documentation/0/missing_data_causes", "whether due to length or other issues"),
              C("/file_collections/0/resources/4/description", "(n=23532)")],
             [A("anomalies")], [], [], None),
    "E9.4": ("Sensitive Content and Warnings Provided", 1,
             "sensitive_elements: release is low risk; derived features only, not original voice recordings. content_warnings absent.",
             "Sensitivity is characterized; brief.",
             [C("/sensitive_elements/0/sensitivity_details", "not the original voice recordings")],
             [A("content_warnings")], [], [], None),
    "E9.5": ("Ethical Review and Social Impact Analysis", 0,
             "ethical_reviews present (SickKids REB), but future_use_impacts absent; no downstream social-impact analysis or conflicts of interest.",
             "Source rubric scope includes social impact; only the ethics review half is met.",
             [C("/ethical_reviews/0/reviewing_organization", "Research Ethics Board at the Hospital for Sick Children")],
             [A("future_use_impacts")], [], [], None),
    "E10.1": ("Dataset Published on a Recognized Platform", 1,
             "publisher slot absent, but description states 'published on PhysioNet on May 1, 2026', citation names PhysioNet, and page and DOI are PhysioNet's.",
             "Recognized platform unambiguously identified; structured publisher field missing.",
             [C("description", "published on PhysioNet on May 1, 2026"), C("citation", "PhysioNet")],
             [A("publisher")], [], ["page"], None),
    "E10.2": ("Citation and DOI for Cross-referencing", 1,
             "citation with authors, year, version, PhysioNet, RRID:SCR_007345 and DOI URL; doi field consistent.",
             "Complete recommended citation; RRID:SCR_007345 is PhysioNet's platform RRID (valid format).",
             [C("citation", "https://doi.org/10.13026/h995-bt35"), C("doi", "10.13026/h995-bt35")],
             [], [], [], None),
    "E10.3": ("Community Standards or Schema Conformance", 0,
             "conforms_to absent; no community standard stated for the release.",
             "Unmet.",
             [], [A("conforms_to")], [], ["preprocessing_strategies"], None),
    "E10.4": ("Outreach Materials and Documentation Links", 1,
             "page (PhysioNet landing page) and external_resources (b2ai-voice.org).",
             "Documentation links present; no tutorials or webinars.",
             [C("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/"),
              C("/external_resources/0/external_resources/0", "https://b2ai-voice.org/")],
             [], [], [], None),
    "E10.5": ("Related Datasets with Typed Relationships", 0,
             "related_datasets absent; the adult dataset relation is deliberately left unrecorded (source_caveats).",
             "Unmet.",
             [C("source_caveats", "no related_datasets entry is recorded")], [A("related_datasets")], [], [], None),
}

ISSUES = [
    {"item_ids": ["E4.2"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "consistency",
     "severity": "high", "fields_involved": ["human_subject_research", "is_deidentified", "participant_privacy"], "recommendation": "Add is_deidentified with the method and identifiers removed from phenotype and metadata files.",
     "description": "human_subject_research.involves_human_subjects is true and demographic/clinical questionnaire data are released, but is_deidentified is absent; no deidentification method or removed identifiers are documented for the phenotype files."},
    {"item_ids": ["E2.2"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "completeness",
     "severity": "medium", "fields_involved": ["regulatory_restrictions", "data_governance"], "recommendation": "State applicable regulatory frameworks and confidentiality level; put the DACO address in data_governance.committee_contact.",
     "description": "No regulatory compliance statement or confidentiality classification (regulatory_restrictions absent; data_governance.committee_contact absent although a DACO address appears in prose)."},
    {"item_ids": ["E1.5", "E10.5"], "score_effect": "lowered", "category": "scope_drift", "type": "completeness",
     "severity": "medium", "fields_involved": ["parent_datasets", "related_datasets", "source_caveats"], "recommendation": "Record typed relationships to the adult dataset and Synapse raw-audio cohort when sources support them.",
     "description": "No parent_datasets or related_datasets; the adult Bridge2AI-Voice dataset and the Synapse raw-audio cohort are not linked as typed relationships (the record explains its decision in source_caveats)."},
    {"item_ids": ["E3.3", "E8.5", "E10.3"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "severity": "medium", "fields_involved": ["conforms_to", "conforms_to_schema", "external_resources", "imputation_protocols"], "recommendation": "State format/standard conformance, link papers or protocols, and say whether imputation was used.",
     "description": "No conforms_to/conforms_to_schema for the released data, no imputation statement, and external resources limited to the project homepage."},
    {"item_ids": ["E3.5", "E7.2"], "score_effect": "lowered", "category": "license_use_terms", "type": "completeness",
     "severity": "medium", "fields_involved": ["intended_uses", "prohibited_uses", "discouraged_uses", "tasks"], "recommendation": "Summarize DUA-prohibited uses and specific research or ML tasks.",
     "description": "No prohibited or discouraged uses and no tasks; intended uses are three generic one-line statements."},
    {"item_ids": ["E5.3", "E5.4"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "severity": "medium", "fields_involved": ["variables", "is_tabular", "subsets", "instances"], "recommendation": "Describe phenotype variables, set is_tabular, and name represented conditions.",
     "description": "Variable metadata covers only four key columns; no is_tabular flag or subset/split flags; conditions or diagnoses represented among patients are never named."},
    {"item_ids": ["E6.4"], "score_effect": "lowered", "category": "temporal_version", "type": "completeness",
     "severity": "low", "fields_involved": ["updates"], "recommendation": "Add an updates block with maintenance plan or expected frequency.",
     "description": "No update schedule or maintenance plan (updates absent)."},
    {"item_ids": ["E9.1", "E9.2", "E9.5"], "score_effect": "lowered", "category": "bias_quality", "type": "completeness",
     "severity": "high", "fields_involved": ["known_limitations", "known_biases", "future_use_impacts"], "recommendation": "Document limitations, categorized biases and social impacts.",
     "description": "known_limitations, known_biases and future_use_impacts absent despite evident single-site, English-proficiency and mixed-microphone constraints."},
    {"item_ids": [], "score_effect": "noted_only", "category": "persistent_identifier", "type": "consistency",
     "severity": "low", "fields_involved": ["version_access.latest_version_doi", "doi"], "recommendation": "Explain what the latest_version_doi identifies.",
     "description": "version_access.latest_version_doi (doi:10.13026/mf9s-5r03) differs from the record DOI (10.13026/h995-bt35) without explanation; plausibly PhysioNet's all-versions DOI."},
    {"item_ids": [], "score_effect": "noted_only", "category": "scope_drift", "type": "content_accuracy",
     "severity": "low", "fields_involved": ["participant_privacy", "participant_compensation", "consent_revocations"], "recommendation": "Keep attribution; prefer pediatric-specific sources where available.",
     "description": "Re-identification risk, compensation, withdrawal and some assent/consent statements come from the umbrella multi-site acquisition protocol rather than the pediatric release; the record attributes them explicitly."},
    {"item_ids": [], "score_effect": "noted_only", "category": "source_conflict", "type": "correctness",
     "severity": "low", "fields_involved": ["funders"], "recommendation": "No change needed beyond confirming the award number with the funder.",
     "description": "Award 3OT2OD032720-01S1 (PhysioNet) vs 3OT2OD032720-01S3 (RePORTER page) discrepancy is flagged transparently in funders source_caveats; the recorded number follows NIH format."},
    {"item_ids": [], "score_effect": "noted_only", "category": "format_access", "type": "completeness",
     "severity": "low", "fields_involved": ["file_collections", "distribution_formats", "download_url"], "recommendation": "Add format/media_type for Parquet resources and state encoding.",
     "description": "Parquet resources lack structured format/media_type fields and no character encoding is stated; distribution_formats and download_url absent."},
]


def main():
    record_id = "doi:10.13026/h995-bt35"
    elements = []
    total = 0
    for eid, ename, edesc in ELEMENTS:
        subs = []
        escore = 0
        emax = 0
        for iid in [f"E{eid}.{k}" for k in range(1, 6)]:
            name, score, ev, qn, cited, absent, counts, considered, nir = ITEMS[iid]
            rule = RULES.get(iid)
            if rule is None:
                status, appl_ev, applicable = "applicable", ALWAYS, True
            else:
                a = applicability(rule, CONTEXT)
                status, appl_ev, applicable = a.status, a.evidence, a.applicable
            assert applicable
            emax += 1
            escore += score
            sub = {
                "name": name, "score": score, "evidence": ev, "quality_note": qn,
                "applicable": applicable, "applicability_status": status,
                "applicability_evidence": appl_ev,
                "unit_scores": [{"path": "#", "score": score, "evidence": ev,
                                 "cited": cited, "absent": absent, "counts": counts,
                                 "considered": considered}],
                "item_id": iid,
            }
            if nir:
                sub["no_issue_reason"] = nir
            subs.append(sub)
        total += escore
        elements.append({"id": eid, "name": ename, "description": edesc,
                         "sub_elements": subs, "element_score": escore, "element_max": emax})
    max_points = 50
    excluded = 0
    adjusted = max_points - excluded
    out = {
        "rubric": "rubric10-semantic",
        "version": "3.0",
        "d4d_file": str(INPUT.relative_to(ROOT)),
        "project": "VOICE_PEDIATRIC",
        "method": "claudecode_agent",
        "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2",
        "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": {
            "name": "claude-opus-5-5",
            "evaluator_model": "claude-opus-5-5",
            "temperature": None,
            "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
            "evaluation_type": "semantic_llm_judge",
        },
        "overall_score": {
            "total_points": total, "max_points": max_points,
            "excluded_max_points": excluded, "adjusted_max_points": adjusted,
            "normalized_percentage": round(total / adjusted * 100, 1),
            "fixed_percentage": round(total / max_points * 100, 1),
            "sub_elements_not_applicable": 0,
            "excluded_item_ids": [],
        },
        "elements": elements,
        "semantic_analysis": {
            "issues_detected": ISSUES,
            "semantic_insights": [
                "Release-scoped record: it explicitly separates pediatric v1.1.0 facts from adult-dataset and umbrella-protocol documentation and attributes protocol-derived statements.",
                "Strong technical transparency: feature-level STFT/Mel/MFCC parameters, b2aiprep 3.0.0 and openSMILE/Praat/parselmouth/torchaudio named as producers of released files.",
                "Main gaps are Responsible-AI slots (limitations, biases, social impact), deidentification method, conformance standards and typed dataset relationships.",
            ],
            "consistency_checks": {"passed": 5, "failed": 1, "warnings": 2},
            "correctness_validations": {
                "doi_format": "valid (10.13026 PhysioNet prefix)",
                "grant_number_format": "valid NIH pattern (3OT2OD032720-01S1)",
                "rrid_format": "valid (RRID:SCR_007345 in citation)",
                "url_validity": "plausible (physionet.org, synapse.org, github.com, b2ai-voice.org)",
            },
        },
        "applicability_context": CONTEXT,
        "evaluation_scope": {
            "policy": "single_dataset",
            "units": [{"path": "#", "id": record_id}],
            "collection_metadata_inherited": False,
        },
        "metadata": {
            "instrument_sha256": sha(ROOT / ".claude/agents/d4d-rubric10-semantic.md"),
            "evidence_authority_sha256": sha(ROOT / "data/rubric/semantic_evidence_authority_v3.json"),
            "rubric_sha256": sha(ROOT / "data/rubric/rubric10.txt"),
            "input_sha256": sha(INPUT),
            "context_sha256": context_digest(CONTEXT),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(OUT, total, adjusted)


if __name__ == "__main__":
    main()
