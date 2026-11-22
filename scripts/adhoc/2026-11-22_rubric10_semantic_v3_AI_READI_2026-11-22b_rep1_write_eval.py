# Purpose: serialize the rubric10-semantic (general context v3) judgements for one D4D record.
# Inputs: data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/AI_READI_d4d.yaml
#         .claude/agents/d4d-rubric10-semantic.md, data/rubric/rubric10.txt,
#         data/rubric/semantic_evidence_authority_v3.json (hashed only)
# Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep1_evaluation.json
# Judgements were made by the evaluating session (claude-opus-5-5) reading the record; this script only
# records them and computes digests. No caller applicability context was supplied (empty context).
# Date: 2026-11-22
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import applicability, context_digest, normalize_context  # noqa: E402

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/AI_READI_d4d.yaml"
OUT = "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep1_evaluation.json"
AGENT = ".claude/agents/d4d-rubric10-semantic.md"
RUBRIC = "data/rubric/rubric10.txt"
AUTHORITY = "data/rubric/semantic_evidence_authority_v3.json"
MODEL = "claude-opus-5-5"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


CONTEXT = normalize_context({})
RULES = {
    "E2.2": "regulated_access",
    "E3.1": "shared_dataset", "E3.2": "shared_dataset", "E3.3": "shared_dataset", "E3.4": "shared_dataset",
    "E4.1": {"any": ["human_subjects", "regulated_access"]},
    "E4.2": {"any": ["human_subjects", "regulated_access"]},
    "E4.3": "human_subjects", "E4.4": "human_subjects", "E4.5": "human_subjects",
    "E6.1": "shared_dataset", "E6.2": "shared_dataset", "E6.3": "shared_dataset", "E6.4": "shared_dataset",
    "E6.5": "shared_dataset",
    "E8.1": "data_collection", "E8.2": "data_collection", "E8.3": "data_processing",
    "E8.4": "processing_software",
    "E10.1": "shared_dataset", "E10.2": "shared_dataset", "E10.3": "shared_dataset", "E10.4": "shared_dataset",
    "E10.5": "shared_dataset",
}


def c(path, quote=None):
    d = {"path": path}
    if quote is not None:
        d["quote"] = quote
    return d


def a(path):
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
             "doi: 10.60775/fairhub.3; id: doi:10.60775/fairhub.3. Valid 10.XXXX/ DOI syntax; prefix 10.60775 is used by the FAIRhub repository named in publisher (https://fairhub.io/) and is consistent across version_access DOIs.",
             "Valid, plausible repository DOI; no RRID (not expected for a dataset).",
             [c("doi", "10.60775/fairhub.3"), c("id", "doi:10.60775/fairhub.3")], [], [], ["publisher"], None),
    "E1.2": ("Dataset Title and Description Completeness", 1,
             "title: 'Flagship Dataset of Type 2 Diabetes from the AI-READI Project'; description (>1,500 chars) states version, platform, 2280 participants, collection period, 3 US sites, data modalities, CDS organization and purpose.",
             "Specific, actionable title and description.",
             [c("title", "Flagship Dataset of Type 2 Diabetes from the AI-READI Project"),
              c("description", "this version contains data from 2280 participants collected between July 19, 2023 and May 1, 2025")],
             [], [], [], None),
    "E1.3": ("Keywords or Tags for Searchability", 1,
             "7 keywords covering condition (Diabetes mellitus), methods (Machine Learning, Artificial Intelligence) and modalities (Electrocardiography, Continuous Glucose Monitoring, Retinal imaging, Eye exam).",
             "Meets the >=5 relevant keyword threshold.",
             [c("keywords", "Continuous Glucose Monitoring")], [], [{"path": "keywords", "claimed": 7}], [], None),
    "E1.4": ("Landing Page and Resources (page, hierarchical resources)", 1,
             "page: https://fairhub.io/datasets/3 (dataset-specific FAIRhub landing page). No nested resources, but file_collections documents the directory hierarchy.",
             "Landing page present; hierarchy carried by file_collections rather than resources.",
             [c("page", "https://fairhub.io/datasets/3")], [a("resources")], [], ["file_collections"], None),
    "E1.5": ("Hierarchical Structure (parent datasets, relationships)", 0,
             "Neither parent_datasets nor related_datasets is populated. Prior versions (fairhub.1, fairhub.2) appear only as strings in version_access.versions_available, not as typed relationships; relationships describes instance relationships (one visit per participant), not dataset relationships.",
             "No dataset-level hierarchy or typed relationships recorded.",
             [], [a("parent_datasets"), a("related_datasets")], [], ["version_access", "relationships"], None),
    "E2.1": ("Access Policy and IP Restrictions Defined", 1,
             "license_and_use_terms names 'AI-READI Data License Agreement (Version 2.0)' (doi:10.5281/zenodo.17555036) with detailed license_terms (licensor, permitted uses, storage, termination); ip_restrictions states title and IP rights remain with the Licensor.",
             "Clear access policy and IP terms.",
             [c("license_and_use_terms.name", "AI-READI Data License Agreement (Version 2.0)"),
              c("ip_restrictions.restrictions", "all industrial and intellectual property rights therein remain"),
              c("license", "AI-READI custom license v2.0")], [], [], [], None),
    "E2.2": ("Regulatory Compliance and Confidentiality Classification", 0,
             "regulatory_restrictions contains only other_compliance (NIH Genomic Data Sharing Policy standards). No confidentiality_level classification, no hipaa_compliant status, and no governance committee contact (data_governance names a 'Data Access Committee' and UCSD HDOC but gives no contact). HIPAA appears only in is_deidentified and in the license's BAA storage requirement.",
             "One compliance framework named; confidentiality classification and governance contact absent.",
             [c("regulatory_restrictions.other_compliance", "Genomic Data Sharing (GDS) Policy"),
              c("data_governance.committee_name", "Data Access Committee")],
             [a("regulatory_restrictions.confidentiality_level"), a("regulatory_restrictions.hipaa_compliant"),
              a("data_governance.committee_contact")],
             [], ["is_deidentified", "license_and_use_terms", "data_governance"], None),
    "E2.3": ("Download URL or Platform Link Available", 0,
             "download_url is absent. The record gives the landing page and describes access steps (login via verified ID, T2D-only attestation, license agreement) in data_governance.access_review_process, but no direct download link or download endpoint is given.",
             "Access route described in prose; dedicated download link missing.",
             [c("data_governance.access_review_process", "Accessing the dataset requires logging in through a verified ID system")],
             [a("download_url")], [], ["page"], None),
    "E2.4": ("Distribution Formats and File Types Specified", 1,
             "distribution_formats lists DICOM (application/dicom), Markdown, CSV, JSON with media types; file_collections resources give TSV (text/tab-separated-values), JSON, MD, TXT with media types.",
             "Formats and MIME types specified; WFDB/Open mHealth files are described via conforms_to rather than distribution_formats.",
             [c("/distribution_formats/0/media_type", "application/dicom"),
              c("/file_collections/0/resources/0/media_type", "text/tab-separated-values")],
             [], [{"path": "distribution_formats", "claimed": 4}], ["file_collections"], None),
    "E2.5": ("Related Datasets and External Resources Linked", 1,
             "external_resources links 8 resources: Nature Metabolism comment (doi:10.1038/s42255-024-01165-x), BMJ Open protocol, license Zenodo record, docs.aireadi.org, project website, Zenodo community, GitHub org, ClinicalTrials.gov NCT06002048. related_datasets is absent.",
             "Strong external documentation links; related datasets not typed (scored under E10.5).",
             [c("/external_resources/0/external_resources/0", "https://doi.org/10.1038/s42255-024-01165-x")],
             [a("related_datasets")], [{"path": "external_resources", "claimed": 8}], [], None),
    "E3.1": ("License Terms Allow Reuse", 1,
             "license_terms grant a non-exclusive license 'to download, reproduce and use the Data, and to create derivative works of the Data, for research, commercial and non-commercial purposes', with conditions; the T2D-only restriction on the public version is recorded and its conflict explained in source_caveats.",
             "Reuse permissions clear, with restrictions disclosed.",
             [c("license_and_use_terms.license_terms", "for research, commercial and non-commercial purposes"),
              c("license_and_use_terms.data_use_permission", "disease_specific_research")],
             [], [], ["license_and_use_terms.source_caveats"], None),
    "E3.2": ("Data Formats Are Standardized (encoding, format)", 1,
             "Standard formats: DICOM for retinal imaging, WFDB for ECG, OMOP CDM CSV for clinical data, Open mHealth for wearables, TSV manifests, JSON metadata. Character encoding is not stated.",
             "Standardized formats well documented; encoding absent.",
             [c("/distribution_formats/0/format", "DICOM"),
              c("/file_collections/0/conforms_to", "WaveForm DataBase (WFDB)")],
             [a("file_collections.resources.encoding")], [], ["distribution_formats", "file_collections"], None),
    "E3.3": ("Schema or Ontology Conformance Stated", 1,
             "conforms_to: CDS v0.1.1, WFDB, OMOP CDM, ESDS, DICOM, Open mHealth, mapped to each data directory; conforms_to_standard lists the same six standards.",
             "Explicit, per-modality standards conformance.",
             [c("conforms_to", "Observational Medical Outcomes Partnership (OMOP) Common Data Model (CDM)"),
              c("conforms_to_standard", "OMOP_CDM")], [], [{"path": "conforms_to_standard", "claimed": 6}], [], None),
    "E3.4": ("Variable Metadata with Identifiers Defined", 0,
             "variables is absent. Directory-level modality descriptions in file_collections exist, but there is no variable/column-level metadata with identifiers or descriptions.",
             "No variable-level metadata.",
             [], [a("variables")], [], ["file_collections"], None),
    "E3.5": ("Use Guidance Provided (intended, prohibited uses)", 1,
             "intended_uses (AI/ML T2D research; distributing models without contained data) and 5 prohibited_uses (clinical treatment decisions, re-identification, third-party sharing, vendor training, reproduction in publications). discouraged_uses absent.",
             "Clear allowed and prohibited uses.",
             [c("/prohibited_uses/0/description", "The license prohibits making clinical treatment decisions based on the Data."),
              c("/intended_uses/0/name", "AI/ML research on type 2 diabetes")],
             [a("discouraged_uses")], [{"path": "intended_uses", "claimed": 2}, {"path": "prohibited_uses", "claimed": 5}], [], None),
    "E4.1": ("IRB or Ethics Review and Data Protection Impact", 1,
             "ethical_reviews: UW IRB approval STUDY00016228 with reliance agreements for UAB and UCSD, initial approval 2022-12-20; human_subject_research.involves_human_subjects true with irb_approval. data_protection_impacts is absent (source_caveats notes none was conducted).",
             "IRB review documented consistently with involves_human_subjects=true.",
             [c("/ethical_reviews/0/review_details", "approval number STUDY00016228"),
              c("human_subject_research.involves_human_subjects")],
             [a("data_protection_impacts")], [], ["human_subject_research.irb_approval", "data_governance"], None),
    "E4.2": ("Deidentification Method Described", 1,
             "is_deidentified.method: 'no identifiers were collected, so no active de-identification was necessary, but the data were checked to confirm that no identifiable data per US HIPAA were present'; identifiers_removed: sex, race/ethnicity and medication. source_caveats records the conflicting Safe Harbor statement and the IRB protocol's collection of identifiers.",
             "Method stated (HIPAA-identifier verification) with removed elements; tension with IRB protocol is disclosed rather than resolved.",
             [c("is_deidentified.method", "checked to confirm that no identifiable data per US HIPAA were present"),
              c("is_deidentified.identifiers_removed", "sex and race/ethnicity")],
             [], [], ["is_deidentified.source_caveats"], None),
    "E4.3": ("Privacy Protections and Re-identification Risk Assessment", 1,
             "participant_privacy lists privacy-conscious device selection (no audio/video/GPS), license restrictions and watermarking 'to prevent re-identification attempts', coded separation of identifiers, and Level 3 data security. Re-identification risk is acknowledged ('theoretical risk of future re-identification') in future_use_impacts; no dedicated reidentification_risk field.",
             "Protections and mitigations documented; risk assessment is brief.",
             [c("/participant_privacy/1/privacy_techniques", "to prevent re-identification attempts"),
              c("/future_use_impacts/1/impact_details", "there is a theoretical risk of future re-identification")],
             [a("participant_privacy.reidentification_risk")], [{"path": "participant_privacy", "claimed": 4}], [], None),
    "E4.4": ("Informed Consent Obtained from Participants", 1,
             "informed_consent: written consent via REDCap e-consent or in person; consent_scope (public vs controlled tiers) and withdrawal_mechanism; consent_revocations notes data already shared remain.",
             "Thorough consent documentation.",
             [c("/informed_consent/0/consent_type", "Written informed consent, obtained electronically (e-consent) or in person"),
              c("/informed_consent/0/withdrawal_mechanism", "Participants were permitted to withdraw consent at any time")],
             [], [], ["consent_revocations"], None),
    "E4.5": ("Vulnerable Populations and Compensation Documented", 0,
             "participant_compensation documents a $200 stipend plus travel costs. at_risk_populations is absent and no statement addresses whether vulnerable populations were included or protected (only exclusion criteria such as pregnancy appear inside sampling_strategies).",
             "Compensation documented; vulnerable-population half absent.",
             [c("/participant_compensation/0/compensation_amount", "$200")],
             [a("at_risk_populations")], [], ["sampling_strategies"], None),
    "E5.1": ("Cohort or Subpopulations Characteristics Described", 1,
             "subpopulations: 10 groups (race/ethnicity, sex, diabetes status) with counts and split distribution; sampling_strategies gives inclusion (age >=40, English) and exclusion criteria; mean age 60.8 ± 11.3.",
             "Rich cohort characterization.",
             [c("/subpopulations/0/distribution", "380 of 2280 participants")],
             [], [{"path": "subpopulations", "claimed": 10}], ["sampling_strategies"], None),
    "E5.2": ("Number of Instances or Samples Reported", 1,
             "instances: Participant, counts 2280; split counts 1576/352/352; total_file_count 356343.",
             "Specific counts given.",
             [c("/instances/0/counts"), c("total_file_count")], [], [], ["splits"], None),
    "E5.3": ("Variable-Level Metadata, Tabular Flag, and Data Splits", 0,
             "variables and is_tabular are absent; subsets flags absent. A recommended 70/15/15 split is documented in splits, but no variable/column descriptions or data dictionary are given.",
             "Split documented; variable-level metadata and tabular flag missing.",
             [c("/splits/0/split_details", "70%/15%/15% for training/validation/testing")],
             [a("variables"), a("is_tabular"), a("subsets")], [], [], None),
    "E5.4": ("Data Topics or Conditions Represented", 1,
             "Condition is T2DM across a severity spectrum (no diabetes, lifestyle-controlled, oral, insulin) with modalities listed in description; instances describe each instance as all data for one participant, with no labels.",
             "Conditions and topics clear.",
             [c("/instances/0/description", "Each instance consists of all of the data available for an individual participating in the study"),
              c("/subpopulations/9/identification", "Participants with Type 2 Diabetes whose blood sugar is controlled by insulin.")],
             [], [], ["description"], None),
    "E5.5": ("Data Quality, Anomalies, and Missing Data Documented", 1,
             "anomalies (survey nonresponse, wearable failures, imaging noise, Optomed variability), missing_data_documentation (Marijuana not assessed in Alabama, unavailable modalities, skipped Spectralis), sampling_strategies (non-probability triple-balanced design).",
             "All three components documented specifically.",
             [c("/missing_data_documentation/0/missing_data_patterns", "Marijuana use was not assessed for participants living in Alabama.")],
             [], [{"path": "anomalies", "claimed": 4}, {"path": "missing_data_documentation", "claimed": 3}], ["sampling_strategies"], None),
    "E6.1": ("Dataset Version Number Provided", 1,
             "version: 3.0.0 (semantic version), consistent with description and version_access.",
             "Version present and consistent.",
             [c("version", "3.0.0")], [], [], [], None),
    "E6.2": ("Version Access Methods Documented", 1,
             "version_access lists 3.0.0, 2.0.0 and 1.0.0 with distinct DOIs and dates, latest_version_doi, and notes v2.0.0 is no longer accessible.",
             "Per-version DOIs and availability documented.",
             [c("version_access.versions_available", "2.0.0 (DOI 10.60775/fairhub.2, Nov 8, 2024)"),
              c("version_access.latest_version_doi", "doi:10.60775/fairhub.3")], [], [], [], None),
    "E6.3": ("Change Descriptions and Errata Provided", 1,
             "updates.update_details describes static yearly releases with additional participants; version_access.version_details records per-version participant counts and that Snellen visual acuity variables were dropped in 3.0.0. CHANGELOG.md is listed. errata absent.",
             "Change descriptions present; no errata.",
             [c("version_access.version_details", "the Snellen visual acuity variables were dropped in version 3.0.0"),
              c("updates.update_details", "new versions are released approximately once a year")],
             [a("errata")], [], [], None),
    "E6.4": ("Update Schedule or Frequency Indicated", 1,
             "updates.frequency: 'Approximately yearly'; maintainers: AI-READI team.",
             "Schedule and maintainer given.",
             [c("updates.frequency", "Approximately yearly")], [], [], ["maintainers"], None),
    "E6.5": ("Provenance, Source Derivation, and Raw Data Sources", 1,
             "raw_data_sources: EMR extraction, Department of Licensing records, Dexcom Clarity; raw_sources describes raw data retention; updates.update_details explains release derivation. was_derived_from absent.",
             "Raw sources and release provenance documented.",
             [c("/raw_data_sources/0/source_description", "medical records will be extracted"),
              c("updates.update_details", "Version 3.0.0 is the third version")],
             [a("was_derived_from")], [{"path": "raw_data_sources", "claimed": 3}], ["raw_sources"], None),
    "E7.1": ("Motivation or Purpose for Dataset Creation", 1,
             "purposes: enable AI/ML research into T2DM pathogenesis and salutogenesis; foundational dataset for a temporal atlas; addressing_gaps lists five gaps.",
             "Clear scientific rationale.",
             [c("/purposes/0/response", "salutogenesis")], [], [], ["addressing_gaps"], None),
    "E7.2": ("Primary Research Objectives or Tasks", 1,
             "tasks: pseudotime manifold analysis to predict disease trajectories from multimodal data.",
             "Specific analytical task.",
             [c("/tasks/0/name", "Pseudotime manifold analysis")], [], [], [], None),
    "E7.3": ("Funding Sources and Mechanisms Listed", 1,
             "funders: NIH Bridge2AI program (NIH Common Fund), additional NIH grants, Research to Prevent Blindness.",
             "Funders and mechanism named.",
             [c("/funders/0/description", "through its Bridge2AI Program (NIH Common Fund)")],
             [], [{"path": "funders", "claimed": 3}], [], None),
    "E7.4": ("Grant IDs or Award Numbers Present", 1,
             "Grant numbers OT2OD032644, P30DK035816, UL1TR003096 follow NIH activity-code/IC/serial conventions; the healthsheet typo 'OT2ODO32644' is noted and corrected in source_caveats. Research to Prevent Blindness has no award number.",
             "Valid NIH-format award numbers.",
             [c("/funders/0/grants/0/grant_number", "OT2OD032644"),
              c("/funders/1/grants/0/grant_number", "P30DK035816"),
              c("/funders/1/grants/1/grant_number", "UL1TR003096")], [], [], ["/funders/0/source_caveats"], None),
    "E7.5": ("Creators and Acknowledgements Documented", 1,
             "creators: AI-READI Consortium plus 16 named PIs with ORCIDs and ROR affiliations; funders acknowledged; data_collectors describe site staff.",
             "Creators richly identified.",
             [c("/creators/0/name", "AI-READI Consortium"), c("/creators/1/principal_investigator/orcid", "0000-0002-7452-1648")],
             [], [{"path": "creators", "claimed": 17}], ["funders", "data_collectors"], None),
    "E8.1": ("Collection Mechanisms and Settings Described", 1,
             "collection_mechanisms: 25 entries covering the single 2.5-4 h site visit, REDCap questionnaires, ECG, imaging devices, wearables (10 days at home), lab specimens; collection_timeframes give dates.",
             "Detailed procedures, settings and timeframes.",
             [c("/collection_mechanisms/0/mechanism_details", "single visit lasting between 2.5 and 4 hours")],
             [], [{"path": "collection_mechanisms", "claimed": 25}], ["collection_timeframes"], None),
    "E8.2": ("Data Acquisition Methods Listed", 1,
             "acquisition_methods: direct observation and self-report with verification of data entry; named instruments (Philips PageWriter TC30, Dexcom G6, Garmin Vivosmart 5, Heidelberg Spectralis, Topcon, Zeiss Cirrus) in collection_mechanisms; raw_data_sources describe EMR and Clarity app.",
             "Methods and instruments listed.",
             [c("/acquisition_methods/0/acquisition_details", "Verification of data entry was performed when possible")],
             [], [], ["collection_mechanisms", "raw_data_sources", "direct_collection"], None),
    "E8.3": ("Preprocessing, Cleaning, Labeling, and Annotation Quality", 1,
             "preprocessing_strategies: mapping to OMOP/DICOM, conversion from proprietary .fda/.sdt/.FIT formats; cleaning_strategies: range checks, skip-pattern checks, duplication checks, internal PII review. No labels are provided (instances label false), so labeling/annotation is not expected.",
             "Preprocessing and cleaning concretely described.",
             [c("/cleaning_strategies/0/cleaning_details", "data were checked for credibility (range checks)"),
              c("/preprocessing_strategies/1/preprocessing_details", "converted to DICOM")],
             [a("labeling_strategies"), a("imputation_protocols")], [], ["instances"], None),
    "E8.4": ("Software and Tools Documented", 0,
             "No software that produced or transformed the released data is named. preprocessing_strategies describes OMOP/DICOM/mHealth conversion without naming the converter. Software that is named falls in excluded roles: REDCap (capture, role a; its range-check reports are validation, role d), OMOP Data Quality Dashboard via dqd_omop.json (validation, role d), FAIRhub/Microsoft Azure (hosting, role b), Dexcom Clarity and MoCA Duo app (capture, role a); external_resources' GitHub organization is a publisher root pointer only.",
             "Score 0: no processing software named; named tools are capture (a), hosting (b) or validation (d).",
             [c("/preprocessing_strategies/0/preprocessing_details", "some images required conversion to a DICOM standard format before upload"),
              c("/cleaning_strategies/0/cleaning_details", "flagged in REDCap reports")],
             [a("preprocessing_strategies.used_software"), a("cleaning_strategies.used_software"),
              a("machine_annotation_tools")], [],
             ["external_resources", "file_collections", "maintainers", "collection_mechanisms"], None),
    "E8.5": ("External Standards, Resources, and Imputation Protocols", 0,
             "external_resources (8 links incl. BMJ Open protocol and Nature Metabolism comment) and conforms_to standards are strong, but imputation_protocols is absent and no statement documents whether imputation was or was not used; cleaning_strategies mentions only checking for 'missing data that can be filled from other portions of a record' without a protocol.",
             "Standards/resources present; imputation component absent.",
             [c("conforms_to", "Digital Imaging and Communications in Medicine (DICOM)"),
              c("/cleaning_strategies/0/cleaning_details", "missing data that can be filled from other portions of a record")],
             [a("imputation_protocols")], [], ["external_resources"], None),
    "E9.1": ("Known Limitations Documented", 1,
             "known_limitations: finite biorepository, English-language requirement, unachieved group balance, Pacific Islanders/Native Americans not included.",
             "Specific limitations.",
             [c("/known_limitations/1/limitation_description", "Participants are required to speak, read and understand English")],
             [], [{"path": "known_limitations", "claimed": 4}], [], None),
    "E9.2": ("Biases Categorized Using Standard Taxonomy (RAI-aligned)", 1,
             "known_biases: volunteer bias with bias_type selection_bias; urban/hospital-based recruitment bias; known_limitations adds limitation_type representativeness_limitation.",
             "At least one bias typed; second bias untyped.",
             [c("/known_biases/0/bias_type", "selection_bias"),
              c("/known_limitations/3/limitation_type", "representativeness_limitation")],
             [], [{"path": "known_biases", "claimed": 2}], ["future_use_impacts"], None),
    "E9.3": ("Data Anomalies and Quality Issues Noted", 1,
             "anomalies: survey nonresponse, wearable device failures, imaging noise/failures, variable Optomed image quality.",
             "Modality-specific quality issues.",
             [c("/anomalies/3/anomaly_details", "the quality of the images varies from patient to patient")],
             [], [{"path": "anomalies", "claimed": 4}], [], None),
    "E9.4": ("Sensitive Content and Warnings Provided", 1,
             "sensitive_elements: sensitive data (zip code, sex, race, ethnicity, genetic data, health records, accident reports) held under controlled access; public set excludes them. content_warnings absent (not needed for this content).",
             "Sensitive elements documented with access tiering.",
             [c("/sensitive_elements/0/sensitivity_details", "motor vehicle accident reports")],
             [a("content_warnings")], [], [], None),
    "E9.5": ("Ethical Review and Social Impact Analysis", 1,
             "ethical_reviews (UW IRB) plus future_use_impacts: model for AI-ready datasets, theoretical re-identification risk, possible commercial products/patents (conflict-of-interest relevant).",
             "Review and downstream impact both addressed, though mitigations are brief.",
             [c("/future_use_impacts/2/impact_details", "no plans for the researchers collecting the data set to develop commercial products or file patents")],
             [], [{"path": "future_use_impacts", "claimed": 3}], ["ethical_reviews"], None),
    "E10.1": ("Dataset Published on a Recognized Platform", 1,
             "publisher: https://fairhub.io/ (FAIRhub), with landing page https://fairhub.io/datasets/3.",
             "Recognized repository.",
             [c("publisher", "https://fairhub.io/")], [], [], ["page"], None),
    "E10.2": ("Citation and DOI for Cross-referencing", 1,
             "doi 10.60775/fairhub.3 supports cross-referencing; no recommended citation string is provided.",
             "DOI present; citation text absent.",
             [c("doi", "10.60775/fairhub.3")], [a("citation")], [], [], None),
    "E10.3": ("Community Standards or Schema Conformance", 1,
             "conforms_to: OMOP CDM, DICOM, WFDB, Open mHealth, ESDS, CDS v0.1.1.",
             "Multiple community standards.",
             [c("conforms_to", "wearable_activity_monitor and wearable_blood_glucose follow Open mHealth")],
             [], [], ["conforms_to_standard"], None),
    "E10.4": ("Outreach Materials and Documentation Links", 1,
             "external_resources: docs.aireadi.org documentation, project website, Zenodo community, GitHub organization, publications; page: FAIRhub landing page.",
             "Documentation and outreach links present.",
             [c("/external_resources/2/external_resources/0", "https://docs.aireadi.org/"), c("page")],
             [], [], [], None),
    "E10.5": ("Related Datasets with Typed Relationships", 0,
             "related_datasets is absent; prior versions and the controlled-access dataset are described only in prose, without typed relationships.",
             "No typed dataset relationships.",
             [], [a("related_datasets")], [], ["version_access", "data_governance"], None),
}

ISSUES = [
    {"id": "I1", "item_ids": ["E1.5", "E10.5"], "score_effect": "lowered", "category": "persistent_identifier",
     "type": "completeness", "severity": "medium",
     "description": "No parent_datasets or related_datasets; prior versions (fairhub.1, fairhub.2) and the controlled-access dataset are not linked with typed relationships."},
    {"id": "I2", "item_ids": ["E2.2"], "score_effect": "lowered", "category": "privacy_regulatory",
     "type": "completeness", "severity": "medium",
     "description": "regulatory_restrictions has only other_compliance (NIH GDS Policy); no confidentiality_level, hipaa_compliant status or governance committee contact, although the record describes HIPAA checks, BAA requirements and a Data Access Committee."},
    {"id": "I3", "item_ids": ["E2.3"], "score_effect": "lowered", "category": "format_access",
     "type": "completeness", "severity": "low",
     "description": "download_url absent; access steps are described in data_governance prose and only the landing page URL is given."},
    {"id": "I4", "item_ids": ["E3.4", "E5.3"], "score_effect": "lowered", "category": "variables_metadata",
     "type": "completeness", "severity": "high",
     "description": "No variables (data dictionary) or is_tabular flag for a dataset with substantial tabular OMOP/survey data."},
    {"id": "I5", "item_ids": ["E4.5"], "score_effect": "lowered", "category": "consent_ethics",
     "type": "completeness", "severity": "medium",
     "description": "at_risk_populations absent; inclusion of or protections for vulnerable participants (e.g., older adults up to 85, people with cognitive impairment screened by MoCA) are not addressed."},
    {"id": "I6", "item_ids": ["E8.4"], "score_effect": "lowered", "category": "processing_provenance",
     "type": "completeness", "severity": "medium",
     "description": "No software that transformed the released data (format converters to DICOM/OMOP/Open mHealth) is named; only capture (REDCap), validation (OMOP DQD) and hosting (FAIRhub/Azure) tools appear."},
    {"id": "I7", "item_ids": ["E8.5"], "score_effect": "lowered", "category": "processing_provenance",
     "type": "completeness", "severity": "low",
     "description": "imputation_protocols absent and no explicit statement that imputation was not used; cleaning mentions filling missing data from other record portions without a protocol."},
    {"id": "I8", "item_ids": [], "score_effect": "noted_only", "category": "source_conflict",
     "type": "consistency", "severity": "medium",
     "description": "is_deidentified.method states no identifiers were collected, while the IRB protocol (per source_caveats) obtains name, MRN, DOB, address and ZIP, and the Nature Metabolism comment describes HIPAA Safe Harbor removal. The record discloses the conflict and scopes the statement to the released data."},
    {"id": "I9", "item_ids": [], "score_effect": "noted_only", "category": "license_use_terms",
     "type": "consistency", "severity": "low",
     "description": "License grants research, commercial and non-commercial use, while access steps restrict the public version to type 2 diabetes research; the record labels the license both 'AI-READI custom license v2.0' and 'Health Data License'. Disclosed in source_caveats."},
    {"id": "I10", "item_ids": [], "score_effect": "noted_only", "category": "attribution",
     "type": "content_accuracy", "severity": "low",
     "description": "Aaron Lee and Cecilia Lee are affiliated with Washington University in St. Louis per FAIRhub, while NIH RePORTER lists University of Washington; the conflict is disclosed for Aaron Lee only."},
    {"id": "I11", "item_ids": [], "score_effect": "noted_only", "category": "temporal_version",
     "type": "consistency", "severity": "low",
     "description": "Collection start 2023-07-19 (FAIRhub) vs 18 July 2023 (BMJ Open), and v3.0 described as pilot/first-year data in some sources vs 2280 participants through May 2025; disclosed in top-level source_caveats. Temporal order collection (2023-2025) -> release (2025-11-17) is consistent."},
]

ISSUE_DETAILS = {
    "I1": (["parent_datasets", "related_datasets", "version_access"],
           "Add related_datasets entries with relationship types (e.g., is version of fairhub.1/fairhub.2; controlled-access counterpart)."),
    "I2": (["regulatory_restrictions", "data_governance"],
           "State confidentiality_level, hipaa_compliant status and a contact for the Data Access Committee."),
    "I3": (["download_url", "page", "data_governance"],
           "Provide the FAIRhub download/access URL in download_url."),
    "I4": (["variables", "is_tabular"],
           "Add a variable-level data dictionary (or a link to it) and set is_tabular for the tabular components."),
    "I5": (["at_risk_populations", "participant_compensation"],
           "Document whether vulnerable populations were included and what protections applied."),
    "I6": (["preprocessing_strategies", "cleaning_strategies"],
           "Name the conversion/mapping software (and versions or repositories) used to produce the DICOM, OMOP and Open mHealth files."),
    "I7": (["imputation_protocols", "cleaning_strategies"],
           "Add imputation_protocols, or state explicitly that no imputation was performed."),
    "I8": (["is_deidentified", "human_subject_research"],
           "Clarify that identifiers were held only in internal study records and name the method applied to the release (e.g., Safe Harbor)."),
    "I9": (["license_and_use_terms", "license", "data_governance"],
           "Reconcile the license's permitted purposes with the T2D-only attestation and use one license name."),
    "I10": (["creators"],
            "Verify and harmonize PI affiliations across sources."),
    "I11": (["collection_timeframes", "description", "version_access"],
            "No action needed beyond the existing disclosure."),
}
for _issue in ISSUES:
    _issue["fields_involved"], _issue["recommendation"] = ISSUE_DETAILS[_issue["id"]]


def main():
    units_id = "doi:10.60775/fairhub.3"
    elements = []
    total = 0
    excluded = []
    for eid, ename, edesc in ELEMENTS:
        subs = []
        escore = 0
        emax = 0
        for iid in [k for k in ITEMS if k.split(".")[0] == f"E{eid}"]:
            name, score, ev, qn, cited, absent, counts, considered, nir = ITEMS[iid]
            app = applicability(RULES.get(iid, "always"), CONTEXT)
            assert app.applicable
            emax += 1
            escore += score
            sub = {
                "name": name, "score": score, "evidence": ev, "quality_note": qn,
                "applicable": app.applicable, "applicability_status": app.status,
                "applicability_evidence": app.evidence,
                "unit_scores": [{"path": "#", "score": score, "evidence": ev, "cited": cited,
                                 "absent": absent, "counts": counts, "considered": considered}],
                "item_id": iid,
            }
            if score == 0 and not any(iid in i["item_ids"] for i in ISSUES):
                sub["no_issue_reason"] = nir or "Deduction explained in evidence."
            subs.append(sub)
        total += escore
        elements.append({"id": eid, "name": ename, "description": edesc, "sub_elements": subs,
                         "element_score": escore, "element_max": emax})
    max_points = 50
    adj = max_points - len(excluded)
    out = {
        "rubric": "rubric10-semantic",
        "version": "3.0",
        "d4d_file": INPUT,
        "project": "AI_READI",
        "method": "claudecode_agent",
        "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1",
        "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": {
            "name": MODEL,
            "evaluator_model": MODEL,
            "temperature": None,
            "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
            "evaluation_type": "semantic_llm_judge",
        },
        "overall_score": {
            "total_points": total, "max_points": max_points,
            "excluded_max_points": len(excluded), "adjusted_max_points": adj,
            "normalized_percentage": round(total / adj * 100, 1) if adj else None,
            "fixed_percentage": round(total / max_points * 100, 1),
            "sub_elements_not_applicable": len(excluded),
            "excluded_item_ids": excluded,
        },
        "elements": elements,
        "semantic_analysis": {
            "issues_detected": ISSUES,
            "semantic_insights": [
                "Record is semantically coherent for a multimodal human-subjects T2DM cohort: involves_human_subjects=true is matched by IRB approval, informed consent and a deidentification statement.",
                "Source conflicts (deidentification method, license scope, enrollment dates, PI affiliation, grant-number typo) are disclosed in source_caveats rather than silently resolved.",
                "Main gaps are structural: no variable-level metadata, no typed related datasets, no download_url, no named processing software, no imputation statement.",
            ],
            "consistency_checks": {"passed": 6, "failed": 0, "warnings": 3},
            "correctness_validations": {
                "doi_format": "valid (10.60775/fairhub.3; license 10.5281/zenodo.17555036)",
                "grant_number_format": "valid NIH patterns (OT2OD032644, P30DK035816, UL1TR003096)",
                "rrid_format": "not_present",
                "url_validity": "valid structure (fairhub.io, docs.aireadi.org, doi.org, github.com, clinicaltrials.gov)",
            },
        },
        "applicability_context": CONTEXT,
        "evaluation_scope": {
            "policy": "single_dataset",
            "units": [{"path": "#", "id": units_id}],
            "collection_metadata_inherited": False,
        },
        "metadata": {
            "instrument_sha256": sha(AGENT),
            "evidence_authority_sha256": sha(AUTHORITY),
            "rubric_sha256": sha(RUBRIC),
            "input_sha256": sha(INPUT),
            "context_sha256": context_digest(CONTEXT),
        },
    }
    p = ROOT / OUT
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(total, max_points, adj)


if __name__ == "__main__":
    main()
