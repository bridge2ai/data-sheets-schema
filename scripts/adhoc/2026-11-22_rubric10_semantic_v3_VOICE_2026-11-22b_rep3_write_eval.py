#!/usr/bin/env python3
"""Write the rubric10-semantic v3 evaluation for VOICE, label 2026-11-22b rep3.

Purpose: serialize the evaluator's (claude-opus-5-5) judgements on
  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_d4d.yaml
into the version-3.0 JSON contract of .claude/agents/d4d-rubric10-semantic.md.
Inputs: that D4D record, data/rubric/rubric10.txt, the evidence authority JSON,
  and the agent definition (hashed only). No caller applicability context.
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/VOICE_2026-11-22b_rep3_evaluation.json
Date: 2026-11-22. Scores are the evaluator's judgements, hard-coded below.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest  # noqa: E402

INPUT = ROOT / "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_d4d.yaml"
OUT = ROOT / "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/VOICE_2026-11-22b_rep3_evaluation.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ALWAYS = "This item applies to every dataset"


def unk(pred):
    return f"{pred}: not declared by the caller (no applicability context supplied); unknown, retained in the denominator"


def C(path, quote=None):
    d = {"path": path}
    if quote is not None:
        d["quote"] = quote
    return d


def A(path):
    return {"path": path}


# item_id -> (name, score, pred or None, evidence, quality_note, cited, absent, counts, considered, no_issue_reason)
ITEMS = {}


def item(iid, name, score, pred, evidence, note, cited, absent=(), counts=(), considered=(), nir=None):
    ITEMS[iid] = dict(name=name, score=score, pred=pred, evidence=evidence, note=note,
                      cited=list(cited), absent=list(absent), counts=list(counts),
                      considered=list(considered), nir=nir)


# ---------------- Element 1 ----------------
item("E1.1", "Persistent Identifier (DOI, RRID, or URI)", 1, None,
     "doi: 10.13026/37yb-1t42 and id: doi:10.13026/37yb-1t42 (PhysioNet 10.13026 prefix); version_access.latest_version_doi repeats it.",
     "Valid DOI syntax with a plausible PhysioNet prefix. The citation names the version-specific DOI 10.13026/8xbn-nq66, which version_access lists for 3.1.0; the id/doi value is recorded as the latest-version DOI, so the two are compatible but should be stated explicitly.",
     [C("doi", "10.13026/37yb-1t42"), C("id", "doi:10.13026/37yb-1t42"), C("version_access.latest_version_doi")],
     considered=["citation", "version_access.versions_available"])
item("E1.2", "Dataset Title and Description Completeness", 1, None,
     "title: 'Bridge2AI-Voice: An ethically-sourced, diverse voice dataset linked to health information'; description (~900 chars) gives version, 833 participants, five sites, released content (derived features, not raw audio).",
     "Specific title and a substantive description of scope, population and content.",
     [C("title", "Bridge2AI-Voice"), C("description", "Version 3.1.0 contains data for 833 participants across five sites in North America")])
item("E1.3", "Keywords or Tags for Searchability", 0, None,
     "keywords lists only four terms: health, biomarkers, bridge2ai, voice.",
     "Below the >=5 threshold and missing method/condition terms (e.g., acoustic features, voice disorders, respiratory, neurological, machine learning).",
     [C("/keywords/3", "voice")], counts=[{"path": "keywords", "claimed": 4}])
item("E1.4", "Landing Page and Resources (page, hierarchical resources)", 1, None,
     "page: https://physionet.org/content/b2ai-voice/3.1.0/; file_collections give a features/metadata/phenotype hierarchy with per-file resources.",
     "Version-specific landing page plus a hierarchical file structure; no top-level resources slot, which is not required.",
     [C("page", "https://physionet.org/content/b2ai-voice/3.1.0/"), C("/file_collections/0/resources/0/name", "ppgs.parquet")],
     absent=[A("resources")])
item("E1.5", "Hierarchical Structure (parent datasets, relationships)", 1, None,
     "related_datasets[0]: Bridge2AI-Voice Pediatric Dataset, relationship_type: references, target https://doi.org/10.13026/mf9s-5r03.",
     "One typed relationship to a sibling PhysioNet dataset; no parent_datasets, and the record notes no stronger relation is stated by sources.",
     [C("/related_datasets/0/relationship_type", "references"), C("/related_datasets/0/target_dataset")],
     absent=[A("parent_datasets")])

# ---------------- Element 2 ----------------
item("E2.1", "Access Policy and IP Restrictions Defined", 1, None,
     "license_and_use_terms.license_terms: registration on PhysioNet and signing the Bridge2AI Voice Registered Access Agreement; ip_restrictions lists four restrictions (no IP claims, no sale, Fort Lauderdale Agreement).",
     "Clear access policy and explicit IP terms. license_terms says 'Only credentialed users' while the license is a registered-access agreement with no training required; minor wording tension noted.",
     [C("license_and_use_terms.license_terms", "Bridge2AI Voice Registered Access Agreement"),
      C("/ip_restrictions/restrictions/1", "Sale of all or part of the Data on any media is not permitted."), C("license")],
     considered=["ip_restrictions.notes"])
item("E2.2", "Regulatory Compliance and Confidentiality Classification", 1, "regulated_access",
     "regulatory_restrictions.other_compliance: Certificate of Confidentiality; data_governance names the Data Access Compliance Office with a DARF/DUA/DTUA review process; tiered sensitivity classification (registered vs controlled access) in informed_consent.consent_scope; DACO contact email given in raw_sources.",
     "Regulatory framework, sensitivity tiers and governance body with contact are documented. Structured confidentiality_level/hipaa_compliant and data_governance.committee_contact are not populated; HIPAA de-identification is stated in is_deidentified.method.",
     [C("regulatory_restrictions.other_compliance", "Certificate of Confidentiality"),
      C("data_governance.committee_name", "Data Access Compliance Office (DACO)"),
      C("data_governance.access_review_process"),
      C("/informed_consent/0/consent_scope", "Data that poses a low risk of re-identification will be shared in registered access"),
      C("/raw_sources/0/raw_data_details", "DACO@b2ai-voice.org")],
     absent=[A("regulatory_restrictions.confidentiality_level"), A("regulatory_restrictions.hipaa_compliant"),
             A("data_governance.committee_contact")],
     considered=["data_governance.notes", "is_deidentified.method"])
item("E2.3", "Download URL or Platform Link Available", 1, None,
     "No download_url, but page gives the PhysioNet platform link and license_terms give platform access instructions (register on PhysioNet, sign the agreement); raw audio route via Synapse access_url.",
     "Platform link with access instructions satisfies the item; a direct files URL would be better.",
     [C("page"), C("license_and_use_terms.license_terms", "Access requires registration on PhysioNet")],
     absent=[A("download_url")], considered=["/raw_sources/0/access_url"])
item("E2.4", "Distribution Formats and File Types Specified", 1, None,
     "file_collections: features in Parquet with JSON data dictionaries; audio_quality_metrics.tsv and static_features.tsv have format TSV and media_type text/tab-separated-values; phenotype TSV with JSON dictionaries.",
     "Formats are identified; only two of eleven feature resources carry structured format/media_type, the Parquet ones are described in prose.",
     [C("/file_collections/0/resources/9/format", "TSV"), C("/file_collections/0/resources/9/media_type", "text/tab-separated-values"),
      C("/file_collections/0/description", "Binary files are made available as Parquet")],
     absent=[A("distribution_formats")], considered=["/file_collections/2/description"])
item("E2.5", "Related Datasets and External Resources Linked", 1, None,
     "related_datasets (pediatric dataset) and four external_resources entries (GitHub REDCap protocols, Zenodo docs, Front Digit Health paper, Interspeech 2024 paper).",
     "Both related dataset and external documentation are linked.",
     [C("/related_datasets/0/name", "Bridge2AI-Voice Pediatric Dataset"), C("/external_resources/0/external_resources/0", "https://github.com/eipm/bridge2ai-redcap")],
     counts=[{"path": "external_resources", "claimed": 4}])

# ---------------- Element 3 ----------------
item("E3.1", "License Terms Allow Reuse", 1, "shared_dataset",
     "license: Bridge2AI Voice Registered Access License; license_terms: 'intended solely for commercial and non-commercial research purposes by Authorized Researchers'.",
     "Reuse permitted under registered access for research; not an open license, but the reuse terms are explicit.",
     [C("license", "Bridge2AI Voice Registered Access License"),
      C("license_and_use_terms.license_terms", "The dataset is intended solely for commercial and non-commercial research purposes by Authorized Researchers.")])
item("E3.2", "Data Formats Are Standardized (encoding, format)", 1, "shared_dataset",
     "Parquet, TSV (text/tab-separated-values) and JSON data dictionaries.",
     "Standard open formats; character encoding is not stated for the TSV/JSON files.",
     [C("/file_collections/0/resources/10/format", "TSV"), C("/file_collections/2/description", "TSV data files with JSON data dictionaries")],
     absent=[A("/file_collections/0/resources/10/encoding")])
item("E3.3", "Schema or Ontology Conformance Stated", 0, "shared_dataset",
     "No conforms_to or conforms_to_schema. BIDS v1.9.0 is mentioned only for the controlled-access raw audio (raw_sources), and ICD-10 only for labeling protocol.",
     "No schema/standard conformance declared for the released feature data.",
     [C("/raw_sources/0/raw_data_details", "Brain Imaging Data Structure v1.9.0")],
     absent=[A("conforms_to"), A("conforms_to_schema")],
     considered=["/labeling_strategies/0/data_annotation_protocol"])
item("E3.4", "Variable Metadata with Identifiers Defined", 0, "shared_dataset",
     "No variables slot. The record only says JSON data dictionaries accompany each file and that parquet elements carry participant/session/task identifiers.",
     "Existence of external dictionaries is noted but no variable-level metadata is documented in the record.",
     [C("/file_collections/0/description", "All files are associated with a data dictionary file")],
     absent=[A("variables")], considered=["/file_collections/2/description"])
item("E3.5", "Use Guidance Provided (intended, prohibited uses)", 1, None,
     "intended_uses (2, ML development/benchmarking, clinical research), prohibited_uses (3, re-identification, harm/stigmatization, contacting subjects), discouraged_uses (non-research hiring/insurance/surveillance).",
     "All three use-guidance categories documented with rationale.",
     [C("/intended_uses/0/description"), C("/prohibited_uses/0/description", "Attempting to re-identify research participants"),
      C("/discouraged_uses/0/description", "hiring decisions, insurance premium")],
     counts=[{"path": "prohibited_uses", "claimed": 3}, {"path": "intended_uses", "claimed": 2}])

# ---------------- Element 4 ----------------
G = "any(human_subjects, regulated_access): neither predicate declared by the caller (no applicability context supplied); unknown, retained in the denominator"
H = "human_subjects: not declared by the caller (no applicability context supplied); unknown, retained in the denominator"
item("E4.1", "IRB or Ethics Review and Data Protection Impact", 1, G,
     "ethical_reviews: University of South Florida IRB approved data collection and sharing, single IRB with subsite IRBs; human_subject_research.irb_approval repeats it.",
     "Ethics review documented and consistent with involves_human_subjects: true. No data_protection_impacts assessment.",
     [C("/ethical_reviews/0/reviewing_organization", "University of South Florida Institutional Review Board"),
      C("/human_subject_research/irb_approval/0", "USF Single IRB"), C("human_subject_research.involves_human_subjects")],
     absent=[A("data_protection_impacts")], considered=["human_subject_research.description", "/ethical_reviews/0/review_details"])
item("E4.2", "Deidentification Method Described", 1, G,
     "is_deidentified.method: HIPAA Safe Harbor identifiers removed; removal of all audio data and sensitive fields identified by ethicists; identifiers_removed and detailed deidentification_details.",
     "Named method, identifiers listed and release-specific removals described; appropriate for derived voice features.",
     [C("is_deidentified.method", "HIPAA Safe Harbor identifiers were removed"), C("is_deidentified.identifiers_removed"),
      C("is_deidentified.deidentification_details", "All raw voice data was removed")])
item("E4.3", "Privacy Protections and Re-identification Risk Assessment", 1, H,
     "participant_privacy: dates rebased, geography generalized, narrative text removed; reidentification_risk: K-anonymity (k>=2) not achieved; voice can never be fully de-identified.",
     "Explicit techniques and honest residual-risk statement.",
     [C("/participant_privacy/0/privacy_techniques", "Dates rebased"),
      C("/participant_privacy/0/reidentification_risk", "does not achieve")])
item("E4.4", "Informed Consent Obtained from Participants", 1, H,
     "informed_consent: prospective informed consent, scope of sharing tiers, documentation modes (paper, in-app electronic, REDCap, video); consent_revocations describes withdrawal limits.",
     "Consent procedure, scope and withdrawal mechanism all documented.",
     [C("/informed_consent/0/consent_obtained"), C("/informed_consent/0/consent_documentation", "signing a physical paper copy"),
      C("/consent_revocations/0/revocation_details", "may withdraw from the study at any point")],
     considered=["/collection_notifications/0/notification_details"])
item("E4.5", "Vulnerable Populations and Compensation Documented", 0, H,
     "participant_compensation is detailed ($40/$80 gift cards, max $120, adults only), but at_risk_populations is absent and no protections are described for clinical cohorts that include neurological and psychiatric disorders.",
     "Compensation half is strong; the vulnerable-population half is missing, so the item is incomplete.",
     [C("/participant_compensation/0/compensation_amount", "maximum compensation of $120"),
      C("/participant_compensation/0/notes", "compensation is provided to the adult population only")],
     absent=[A("at_risk_populations")], considered=["/sampling_strategies/0/description", "/participant_compensation/0/compensation_type", "/participant_compensation/0/compensation_provided"])

# ---------------- Element 5 ----------------
item("E5.1", "Cohort or Subpopulations Characteristics Described", 1, None,
     "sampling_strategies describes disease-based recruitment (voice, neurological, mood, respiratory disorders) from high-volume expert clinics, age 18-120, healthy volunteers accepted, exclusion criteria; subpopulations lists Age, Gender, Sex, Ethnicity, Socioeconomic status.",
     "Inclusion/exclusion criteria and cohort composition described; no demographic distributions given and subpopulations only names dimensions.",
     [C("/sampling_strategies/0/description", "minimum age of 18 years"), C("/subpopulations/0/identification", "Age, Gender, Sex, Ethnicity, Socioeconomic status")],
     absent=[A("subsets")])
item("E5.2", "Number of Instances or Samples Reported", 1, None,
     "instances[0]: instance_type person, counts 833; per-file record counts (e.g., n=29289 for ppgs.parquet).",
     "Participant count and per-feature record counts given.",
     [C("/instances/0/counts"), C("/file_collections/0/resources/0/description", "n=29289")])
item("E5.3", "Variable-Level Metadata, Tabular Flag, and Data Splits", 0, None,
     "No variables, is_tabular or subsets (split/subpopulation flags). Only prose mention of JSON data dictionaries.",
     "No variable-level metadata, tabular indicator or split documentation in the record.",
     [C("/file_collections/2/description", "Dictionary entries give a one-sentence description of each column")],
     absent=[A("variables"), A("is_tabular"), A("subsets")])
item("E5.4", "Data Topics or Conditions Represented", 1, None,
     "instances[0].label_description: vocal pathologies, neurological disorders, psychiatric conditions, respiratory disorders.",
     "Condition categories named.",
     [C("/instances/0/label_description", "vocal pathologies, neurological disorders, psychiatric conditions, and respiratory disorders")],
     considered=["/instances/0/notes", "/instances/0/label"])
item("E5.5", "Data Quality, Anomalies, and Missing Data Documented", 1, None,
     "anomalies (site configuration and protocol changes), sampling_strategies (non-probability, not representative), missing_data_documentation (causes, patterns, handling).",
     "All three facets present with specific content.",
     [C("/anomalies/0/anomaly_details", "the collection protocol changed over the course of the study"),
      C("/sampling_strategies/0/strategies", "Non-probability sample"),
      C("/missing_data_documentation/0/handling_strategy")])

# ---------------- Element 6 ----------------
S = "shared_dataset"
item("E6.1", "Dataset Version Number Provided", 1, S, "version: 3.1.0", "Semantic version given, consistent with page and citation.",
     [C("version", "3.1.0")])
item("E6.2", "Version Access Methods Documented", 1, S,
     "version_access: latest_version_doi and versions_available with DOIs for 1.0 (Health Data Nexus), 1.1, 3.0.0 and 3.1.0; policy that older versions remain hosted with unique DOIs.",
     "Version access well documented; 2.0.0 and 2.0.1 appear in distribution_dates but have no DOI listed.",
     [C("/version_access/versions_available/3", "3.1.0: https://doi.org/10.13026/8xbn-nq66"),
      C("version_access.version_details", "each version has a unique DOI")],
     counts=[{"path": "version_access.versions_available", "claimed": 4}], considered=["/distribution_dates/0/release_dates"])
item("E6.3", "Change Descriptions and Errata Provided", 1, S,
     "errata: 'Release 3.1.0 fixed broken parquet files from the previous release'; version_details gives release notes for v1.1 through v3.1.0.",
     "Errata and per-version change log present.",
     [C("/errata/0/erratum_details", "fixed broken parquet files"), C("version_access.version_details", "v3.1.0 was a minor update")])
item("E6.4", "Update Schedule or Frequency Indicated", 1, S,
     "updates.frequency: semi-annual (twice a year); updates.update_details: static versioned releases.",
     "Schedule stated; caveat about Health Data Nexus vs PhysioNet platform recorded.",
     [C("updates.frequency", "semi-annual"), C("updates.update_details")], considered=["updates.source_caveats"])
item("E6.5", "Provenance, Source Derivation, and Raw Data Sources", 1, S,
     "raw_sources: raw audio recordings, held under controlled access, from which released features are derived; preprocessing documents derivation; version_details describes per-release derivation.",
     "Raw source and derivation documented via raw_sources (schema spelling); was_derived_from not populated.",
     [C("/raw_sources/0/description", "contains derived features from the audio waveforms"),
      C("/preprocessing_strategies/0/description", "Features were extracted from the raw audio")],
     absent=[A("was_derived_from"), A("raw_data_sources")], considered=["updates.update_details"])

# ---------------- Element 7 ----------------
item("E7.1", "Motivation or Purpose for Dataset Creation", 1, None,
     "purposes (4 entries) and addressing_gaps (3 entries): ethically sourced voice database linked to health data; gaps in size, multimodality and standards.",
     "Clear rationale; conflicting target sizes (10,000 vs 30,000) are transparently caveated.",
     [C("/purposes/0/response", "ethically"), C("/addressing_gaps/0/response")], considered=["/purposes/1/source_caveats"])
item("E7.2", "Primary Research Objectives or Tasks", 1, None,
     "tasks: training ML models for disease detection and classification using voice data; intended_uses add benchmarking/validation.",
     "Single task statement, but specific to ML disease detection/classification.",
     [C("/tasks/0/response", "disease detection and classification")])
item("E7.3", "Funding Sources and Mechanisms Listed", 1, None,
     "funders: NIH Common Fund Bridge2AI Program, grantor NIH Common Fund (OT2 mechanism).",
     "Funder and programme named; purposes align with Bridge2AI goals.",
     [C("/funders/0/name", "NIH Common Fund Bridge2AI Program"), C("/funders/0/grantor", "NIH Common Fund")],
     considered=["/funders/0/description"])
item("E7.4", "Grant IDs or Award Numbers Present", 1, None,
     "grants: OT2OD032720 and 3OT2OD032720-01S1.",
     "Both follow NIH activity-code/IC/serial convention (OT2 OD); supplement suffix -01S1 valid; caveat explains -01S3 RePORTER record.",
     [C("/funders/0/grants/0/grant_number", "OT2OD032720"), C("/funders/0/grants/1/grant_number", "3OT2OD032720-01S1")],
     considered=["/funders/0/source_caveats"])
item("E7.5", "Creators and Acknowledgements Documented", 1, None,
     "creators: full author list matching the citation, with PIs Yael Bensoussan (USF) and Olivier Elemento (Weill Cornell) and affiliations; funders acknowledged.",
     "Comprehensive creator list; affiliations only for PIs.",
     [C("/creators/0/name", "Yael Bensoussan"), C("/creators/3/principal_investigator/affiliation/0/name", "Weill Cornell Medicine")],
     counts=[{"path": "creators", "claimed": 122}])

# ---------------- Element 8 ----------------
item("E8.1", "Collection Mechanisms and Settings Described", 1, "data_collection",
     "collection_mechanisms: Bridge2AI-Voice App (22 acoustic tasks, questionnaires, EHR linkage) and recording hardware; data_collectors: clinic with trained research assistant; collection_timeframes: 12 months.",
     "Procedures, setting and timeframe described; no dated start/end for release 3.1.0 (caveated).",
     [C("/collection_mechanisms/0/mechanism_details", "A total of 22 acoustic tasks"), C("/data_collectors/0/description", "in the clinic"),
      C("/collection_timeframes/0/timeframe_details", "12 months")])
item("E8.2", "Data Acquisition Methods Listed", 1, "data_collection",
     "acquisition_methods: directly observed and subject-reported, clinically validated; hardware: iPad 9th/10th gen and iPad Air with Avid AE-36 microphone.",
     "Instruments and acquisition/validation methods specified.",
     [C("/acquisition_methods/0/acquisition_details", "Clinical validation"), C("/collection_mechanisms/1/mechanism_details", "Avid AE-36 microphone")],
     considered=["/direct_collection/0/collection_details"])
item("E8.3", "Preprocessing, Cleaning, Labeling, and Annotation Quality", 1, "data_processing",
     "preprocessing_strategies (monaural, 16 kHz resampling, STFT parameters, feature extraction), cleaning_strategies (audit protocol, missingness tables), labeling_strategies (clinician diagnosis, ICD-10), machine_annotation_tools (Whisper transcription).",
     "Detailed and reproducible processing; no inter-annotator agreement (one annotation per item) and no imputation protocol.",
     [C("/preprocessing_strategies/2/description", "resampling to 16 kHz"), C("/cleaning_strategies/0/cleaning_details", "generate missingness tables"),
      C("/labeling_strategies/0/labeling_details", "a local clinician provided the diagnosis"), C("/machine_annotation_tools/0/tool_descriptions")],
     absent=[A("annotation_analyses"), A("imputation_protocols")])
item("E8.4", "Software and Tools Documented", 1, "processing_software",
     "preprocessing_strategies[0].used_software: b2aiprep v3.0.0 (https://github.com/sensein/b2aiprep) - 'release 3.1.0 was generated with b2aiprep v3.0.0'; SenseLab; prose names OpenSMILE, Parselmouth/Praat, Torchaudio, sparc, ppgs.",
     "Processing software that produced the released features is named with version and repository (slot: preprocessing_strategies.used_software). The iPad app (capture) is not counted.",
     [C("/preprocessing_strategies/0/used_software/0/name", "b2aiprep"), C("/preprocessing_strategies/0/used_software/0/version", "3.0.0"),
      C("/preprocessing_strategies/2/preprocessing_details", "Acoustic features were extracted using OpenSMILE")],
     considered=["/machine_annotation_tools/0/tools"])
item("E8.5", "External Standards, Resources, and Imputation Protocols", 0, None,
     "external_resources are strong (protocols on GitHub/Zenodo, two publications), but there is no conforms_to and no imputation_protocols, nor an explicit statement that imputation was not used (missing_data handling only says rows are dropped when all columns are missing).",
     "Imputation, part of this item's source scope, is undocumented; standards conformance is absent.",
     [C("/external_resources/1/external_resources/0", "10.3389/fdgth.2025.1514971")],
     absent=[A("imputation_protocols"), A("conforms_to")], considered=["/missing_data_documentation/0/handling_strategy", "external_resources"])

# ---------------- Element 9 ----------------
item("E9.1", "Known Limitations Documented", 1, None,
     "known_limitations: 5 entries (unequal disease distribution, unaudited off-the-shelf transcription, device/microphone variation, diagnostic drift, confounders).",
     "Specific, actionable limitations.",
     [C("/known_limitations/1/limitation_description", "off-the-shelf models that have not been audited")],
     counts=[{"path": "known_limitations", "claimed": 5}])
item("E9.2", "Biases Categorized Using Standard Taxonomy (RAI-aligned)", 1, None,
     "known_biases: recruitment/selection bias (trust, proximity), site-device confounding, skews by disorder/site/demographics with mitigation advice.",
     "Each bias states the representativeness or measurement limitation; no bias_type taxonomy labels, and no future_use_impacts.",
     [C("/known_biases/0/bias_description", "less likely to be recruited"), C("/known_biases/2/mitigation_strategy")],
     absent=[A("/known_biases/0/bias_type"), A("future_use_impacts")], counts=[{"path": "known_biases", "claimed": 3}])
item("E9.3", "Data Anomalies and Quality Issues Noted", 1, None,
     "anomalies: different collection configurations by site and protocol change over time; missing_data notes feature-generation failures; errata notes broken parquet files.",
     "Single anomaly entry but meaningful, supported by related quality notes.",
     [C("/anomalies/0/anomaly_details", "Different sites have different collection configurations")],
     considered=["/missing_data_documentation/1/missing_data_causes"])
item("E9.4", "Sensitive Content and Warnings Provided", 1, None,
     "sensitive_elements: race, sexual orientation, socioeconomic and health information; content_warnings about free-speech transcriptions with caveat on presence in 3.1.0.",
     "Sensitive elements and content warning documented.",
     [C("/sensitive_elements/1/sensitivity_details", "sexual orientation"), C("/content_warnings/0/warnings/0")])
item("E9.5", "Ethical Review and Social Impact Analysis", 0, None,
     "ethical_reviews documents USF IRB approval, but there is no future_use_impacts analysis and no conflicts-of-interest statement; harm-related use restrictions appear only as discouraged/prohibited uses.",
     "Ethical review half present; downstream social impact analysis with mitigations is missing.",
     [C("/ethical_reviews/0/review_details", "Data collection and sharing was approved")],
     absent=[A("future_use_impacts")], considered=["/discouraged_uses/0/notes"])

# ---------------- Element 10 ----------------
item("E10.1", "Dataset Published on a Recognized Platform", 1, S,
     "No publisher field, but citation names PhysioNet (RRID:SCR_007345) and page is physionet.org; earlier version on Health Data Nexus.",
     "Recognized platform documented, though not in the structured publisher slot.",
     [C("citation", "PhysioNet. RRID:SCR_007345"), C("page", "physionet.org")], absent=[A("publisher")])
item("E10.2", "Citation and DOI for Cross-referencing", 1, S,
     "citation with full author list, version, PhysioNet and DOI 10.13026/8xbn-nq66; doi field 10.13026/37yb-1t42.",
     "Recommended citation and DOIs present; the citation uses the version DOI while doi/id hold the latest-version DOI.",
     [C("citation", "https://doi.org/10.13026/8xbn-nq66"), C("doi")])
item("E10.3", "Community Standards or Schema Conformance", 0, S,
     "No conforms_to; BIDS mentioned only for controlled-access raw audio.",
     "No community standard declared for the released data.",
     [C("/raw_sources/0/raw_data_details", "Brain Imaging Data Structure")], absent=[A("conforms_to")])
item("E10.4", "Outreach Materials and Documentation Links", 1, S,
     "external_resources: protocols/REDCap dictionary (GitHub, Zenodo), documentation source (Zenodo), two publications; page landing page.",
     "Documentation links present; no tutorials/webinars, which are not required.",
     [C("/external_resources/3/external_resources/0", "https://zenodo.org/doi/10.5281/zenodo.13834653"), C("page")])
item("E10.5", "Related Datasets with Typed Relationships", 1, S,
     "related_datasets[0] relationship_type: references (pediatric dataset).",
     "Typed relationship present, though only one and of a weak type.",
     [C("/related_datasets/0/relationship_type", "references")], counts=[{"path": "related_datasets", "claimed": 1}],
     considered=["/related_datasets/0/notes"])

ELEMENTS = [
    (1, "Dataset Discovery and Identification", "Can a user or system discover and uniquely identify this dataset?"),
    (2, "Dataset Access and Retrieval", "Can the dataset and its associated resources be located, accessed, and downloaded?"),
    (3, "Data Reuse and Interoperability", "Is sufficient information provided to reuse and integrate the dataset with others?"),
    (4, "Ethical Use and Privacy Safeguards", "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement."),
    (5, "Data Composition and Structure", "Can the dataset's structure, modality, and population be understood from metadata?"),
    (6, "Data Provenance and Version Tracking", "Can a user determine dataset versions, update history, and provenance?"),
    (7, "Scientific Motivation and Funding Transparency", "Does the metadata clearly state why the dataset exists and who funded it?"),
    (8, "Technical Transparency (Data Collection and Processing)", "Can data collection and processing steps be replicated or understood?"),
    (9, "Dataset Evaluation and Limitations Disclosure", "Does the metadata communicate known risks, biases, or dataset limitations?"),
    (10, "Cross-Platform and Community Integration", "Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain."),
]

ISSUES = [
    dict(item_ids=["E1.3"], score_effect="lowered", category="variables_metadata", type="completeness",
         description="Only four keywords (health, biomarkers, bridge2ai, voice); no method or condition terms.", fields_involved=["keywords"], recommendation='Add condition, modality and method keywords (e.g., voice disorders, acoustic features, machine learning).', severity="low"),
    dict(item_ids=["E3.3", "E10.3"], score_effect="lowered", category="format_access", type="completeness",
         description="No conforms_to/conforms_to_schema for the released feature data; BIDS is cited only for controlled-access raw audio.", fields_involved=["conforms_to", "conforms_to_schema"], recommendation='Declare the standards the released files conform to (e.g., data dictionary schema, BIDS where applicable).', severity="medium"),
    dict(item_ids=["E3.4", "E5.3"], score_effect="lowered", category="variables_metadata", type="completeness",
         description="No variables, is_tabular or subsets; the record only notes that JSON data dictionaries exist.", fields_involved=["variables", "is_tabular", "subsets"], recommendation='Populate variables from the JSON data dictionaries and set is_tabular and subset flags.', severity="medium"),
    dict(item_ids=["E4.5"], score_effect="lowered", category="consent_ethics", type="completeness",
         description="at_risk_populations absent although cohorts include neurological and psychiatric disorders; only compensation is documented.", fields_involved=["at_risk_populations", "participant_compensation"], recommendation='Document at-risk populations and the protections applied to them.', severity="medium"),
    dict(item_ids=["E8.5"], score_effect="lowered", category="processing_provenance", type="completeness",
         description="No imputation protocol or explicit no-imputation statement, and no standards conformance; external resources alone do not cover the item scope.", fields_involved=["imputation_protocols", "conforms_to", "external_resources"], recommendation='State whether imputation was used and, if so, its protocol.', severity="low"),
    dict(item_ids=["E9.5"], score_effect="lowered", category="consent_ethics", type="completeness",
         description="No future_use_impacts social impact analysis or conflict-of-interest statement accompanying the IRB review.", fields_involved=["future_use_impacts", "ethical_reviews"], recommendation='Add an analysis of downstream social impacts and mitigations, and any conflicts of interest.', severity="low"),
    dict(item_ids=[], score_effect="noted_only", category="persistent_identifier", type="consistency",
         description="doi/id 10.13026/37yb-1t42 (latest-version DOI) differs from the citation's version DOI 10.13026/8xbn-nq66; compatible but the distinction is implicit.", fields_involved=["doi", "id", "citation", "version_access.latest_version_doi"], recommendation='Label the concept/latest DOI and the version-specific DOI explicitly.', severity="low"),
    dict(item_ids=[], score_effect="noted_only", category="license_use_terms", type="consistency",
         description="license_terms says 'Only credentialed users who sign the DUA' while describing a registered-access agreement with no training required.", fields_involved=["license_and_use_terms.license_terms", "license"], recommendation="Reconcile 'credentialed' wording with the registered-access tier.", severity="low"),
    dict(item_ids=[], score_effect="noted_only", category="temporal_version", type="completeness",
         description="distribution_dates list releases 2.0.0 and 2.0.1, but versions_available gives no DOI for them.", fields_involved=["distribution_dates", "version_access.versions_available"], recommendation='List DOIs for releases 2.0.0 and 2.0.1.', severity="low"),
    dict(item_ids=[], score_effect="noted_only", category="processing_provenance", type="correctness",
         description="machine_annotation_tools lists 'OpenAI Whisper Large unknown' (version unknown), and the record itself caveats whether transcriptions are in release 3.1.0.", fields_involved=["machine_annotation_tools", "content_warnings"], recommendation="Give the Whisper model version or remove the placeholder 'unknown' from the tool name.", severity="low"),
    dict(item_ids=[], score_effect="noted_only", category="privacy_regulatory", type="completeness",
         description="Governance contact (DACO@b2ai-voice.org) appears only in raw_sources prose; data_governance.committee_contact and structured confidentiality_level/hipaa_compliant are not populated.", fields_involved=["data_governance.committee_contact", "regulatory_restrictions", "raw_sources"], recommendation='Move the DACO contact into data_governance.committee_contact and populate structured regulatory fields.', severity="low"),
]


def main():
    input_sha = sha(INPUT)
    context = {}
    elements = []
    total = 0
    linked = {i for iss in ISSUES for i in iss["item_ids"]}
    for eid, ename, edesc in ELEMENTS:
        subs = []
        escore = 0
        for k in range(1, 6):
            iid = f"E{eid}.{k}"
            it = ITEMS[iid]
            status = "applicable" if it["pred"] is None else "unknown"
            if it["pred"] is None:
                ev = ALWAYS
            elif it["pred"].startswith("any("):
                ev = it["pred"]
            elif it["pred"].startswith("human_subjects:"):
                ev = it["pred"]
            else:
                ev = unk(it["pred"])
            sub = {
                "name": it["name"], "score": it["score"], "evidence": it["evidence"],
                "quality_note": it["note"], "applicable": True, "applicability_status": status,
                "applicability_evidence": ev,
                "unit_scores": [{"path": "#", "score": it["score"], "evidence": it["evidence"],
                                 "cited": it["cited"], "absent": it["absent"], "counts": it["counts"],
                                 "considered": it["considered"]}],
                "item_id": iid,
            }
            if it["score"] < 1 and iid not in linked:
                sub["no_issue_reason"] = it["nir"] or "Deduction explained in quality_note."
            subs.append(sub)
            escore += it["score"]
        total += escore
        elements.append({"id": eid, "name": ename, "description": edesc, "sub_elements": subs,
                         "element_score": escore, "element_max": 5})
    doc = {
        "rubric": "rubric10-semantic",
        "version": "3.0",
        "d4d_file": str(INPUT.relative_to(ROOT)),
        "project": "VOICE",
        "method": "claudecode_agent",
        "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3",
        "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": {"name": "claude-opus-5-5", "evaluator_model": "claude-opus-5-5", "temperature": None,
                  "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
                  "evaluation_type": "semantic_llm_judge"},
        "overall_score": {"total_points": total, "max_points": 50, "excluded_max_points": 0,
                          "adjusted_max_points": 50, "normalized_percentage": round(total / 50 * 100, 1),
                          "fixed_percentage": round(total / 50 * 100, 1), "sub_elements_not_applicable": 0,
                          "excluded_item_ids": []},
        "elements": elements,
        "semantic_analysis": {
            "issues_detected": ISSUES,
            "semantic_insights": [
                "Ethics, privacy and consent documentation is internally consistent: involves_human_subjects true with IRB, consent, withdrawal and de-identification method all present.",
                "Processing provenance is strong: b2aiprep v3.0.0 is named as producing release 3.1.0, with explicit signal-processing parameters.",
                "Gaps are structural metadata: no variables, schema conformance, subsets or imputation documentation.",
                "Source conflicts (target cohort sizes, language eligibility, transcript presence) are transparently caveated rather than silently resolved.",
            ],
            "consistency_checks": {"passed": 6, "failed": 0, "warnings": 3},
            "correctness_validations": {"doi_format": "valid (10.13026 PhysioNet prefix)",
                                        "grant_number_format": "valid (NIH OT2OD032720, 3OT2OD032720-01S1)",
                                        "rrid_format": "valid (RRID:SCR_007345 in citation)",
                                        "url_validity": "valid (physionet.org, github.com, zenodo.org, synapse.org)"},
        },
        "applicability_context": context,
        "evaluation_scope": {"policy": "single_dataset", "units": [{"path": "#", "id": "doi:10.13026/37yb-1t42"}],
                             "collection_metadata_inherited": False},
        "metadata": {
            "instrument_sha256": sha(ROOT / ".claude/agents/d4d-rubric10-semantic.md"),
            "evidence_authority_sha256": sha(ROOT / "data/rubric/semantic_evidence_authority_v3.json"),
            "rubric_sha256": sha(ROOT / "data/rubric/rubric10.txt"),
            "input_sha256": input_sha,
            "context_sha256": context_digest(context),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(OUT, total)


if __name__ == "__main__":
    main()
