#!/usr/bin/env python3
"""Serialize a manual rubric10-semantic (v3.0) evaluation of one D4D record.

Purpose: write the evaluator's judgements (made by reading the record) as the
v3 JSON contract. Scores below are the evaluator's manual judgements; the script
only computes digests, list lengths and totals.
Inputs: data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/AI_READI_d4d.yaml
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep2_evaluation.json
Context: caller-requested single-record rubric10-semantic evaluation, 2026-11-22.
"""
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest  # noqa: E402

INPUT = ROOT / "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/AI_READI_d4d.yaml"
OUTPUT = ROOT / "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep2_evaluation.json"
AGENT = ROOT / ".claude/agents/d4d-rubric10-semantic.md"
RUBRIC = ROOT / "data/rubric/rubric10.txt"
AUTHORITY = ROOT / "data/rubric/semantic_evidence_authority_v3.json"

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
doc = yaml.safe_load(INPUT.read_bytes())
n = lambda key: len(doc[key])

CONTEXT = {}
ALWAYS = "This item applies to every dataset"
def undeclared(*preds, op=None):
    parts = [f"{p}: not declared; retained in the denominator" for p in preds]
    return f"{op}: " + "; ".join(parts) if op else parts[0]

SHARED = undeclared("shared_dataset")
HS_OR_REG = undeclared("human_subjects", "regulated_access", op="any")
HS = undeclared("human_subjects")

def c(path, quote=None):
    return {"path": path, "quote": quote} if quote else {"path": path}

# (item_id, name, score, rule_evidence, evidence, quality_note, cited, absent, counts, considered, no_issue_reason)
ELEMENTS = [
 (1, "Dataset Discovery and Identification", "Can a user or system discover and uniquely identify this dataset?", [
  ("E1.1", "Persistent Identifier (DOI, RRID, or URI)", 1, ALWAYS,
   "doi: 10.60775/fairhub.3; id: doi:10.60775/fairhub.3. Valid 10.XXXX/ DOI syntax; prefix 10.60775 is the FAIRhub registrant prefix, consistent with publisher https://fairhub.io/ and page https://fairhub.io/datasets/3.",
   "Well-formed DOI with a plausible repository prefix that agrees with publisher and landing page.",
   [c("doi", "10.60775/fairhub.3"), c("id", "doi:10.60775/fairhub.3")], [], [], [], None),
  ("E1.2", "Dataset Title and Description Completeness", 1, ALWAYS,
   "title: 'Flagship Dataset of Type 2 Diabetes from the AI-READI Project'; description (>1,000 chars) gives purpose, 3 sites, 2280 participants, collection period July 19 2023-May 1 2025, modalities, 356,343 files / ~3.82 TB, CDS v0.1.1 layout.",
   "Specific, quantitative and purpose-bearing description.",
   [c("title", "Flagship Dataset of Type 2 Diabetes from the AI-READI Project"), c("description", "This version contains data from 2280 participants collected between July 19, 2023 and May 1, 2025.")], [], [], [], None),
  ("E1.3", "Keywords or Tags for Searchability", 1, ALWAYS,
   "9 keywords covering condition (Diabetes mellitus), methods (Machine Learning, Artificial Intelligence) and modalities (Electrocardiography, Continuous Glucose Monitoring, Retinal imaging, Eye exam).",
   "Meets the >=5 threshold with domain, method and modality coverage.",
   [c("keywords", "Continuous Glucose Monitoring")], [], [{"path": "keywords", "claimed": n("keywords")}], [], None),
  ("E1.4", "Landing Page and Resources (page, hierarchical resources)", 1, ALWAYS,
   "page: https://fairhub.io/datasets/3; file_collections give a hierarchical per-datatype structure (cardiac_ecg, clinical_data, environment, retinal_*, wearable_*, root metadata) each with nested file resources.",
   "Landing page plus a hierarchical resource structure.",
   [c("page", "https://fairhub.io/datasets/3"), c("file_collections")], [], [{"path": "file_collections", "claimed": n("file_collections")}], [], None),
  ("E1.5", "Hierarchical Structure (parent datasets, relationships)", 1, ALWAYS,
   "related_datasets: doi:10.60775/fairhub.2 and doi:10.60775/fairhub.1, both relationship_type is_new_version_of with version notes; parent_datasets absent (no parent is implied for a versioned release).",
   "Typed version relationships, direction correct (v3 is a new version of v2/v1).",
   [c("/related_datasets/0/relationship_type", "is_new_version_of"), c("/related_datasets/0/target_dataset", "doi:10.60775/fairhub.2")], ["parent_datasets"], [{"path": "related_datasets", "claimed": n("related_datasets")}], ["relationships"], None),
 ]),
 (2, "Dataset Access and Retrieval", "Can the dataset and its associated resources be located, accessed, and downloaded?", [
  ("E2.1", "Access Policy and IP Restrictions Defined", 1, ALWAYS,
   "license_and_use_terms.license_terms: AI-READI Data License Agreement (Version 2.0), Washington University in St. Louis as Licensor, non-exclusive/non-transferable, termination on breach; data_use_permission disease_specific_research; ip_restrictions: title and IP rights remain with the Licensor.",
   "Clear access policy and IP restriction.",
   [c("license_and_use_terms.license_terms", "AI-READI Data License Agreement (Version 2.0)"), c("ip_restrictions.restrictions"), c("license")], [], [], ["license_and_use_terms.data_use_permission", "data_governance.access_review_process"], None),
  ("E2.2", "Regulatory Compliance and Confidentiality Classification", 0, undeclared("regulated_access"),
   "regulatory_restrictions lists HIPAA-BAA storage and NIH GDS Policy security standards, but there is no confidentiality_level, no hipaa_compliant status, no other_compliance entry, and no governance committee contact (data_governance has only access_review_process; the Data Access Committee is named only in source_caveats without contact). The public/controlled tiering appears in sensitive_elements but is not stated as a confidentiality classification.",
   "Regulatory obligations named, but the classification and governance-contact components of the item are absent.",
   [c("regulatory_restrictions.regulatory_restrictions", "HIPAA-approved Business Associate Agreement")],
   ["regulatory_restrictions.confidentiality_level", "regulatory_restrictions.hipaa_compliant", "regulatory_restrictions.other_compliance", "data_governance.committee_contact", "regulatory_restrictions.governance_committee_contact"],
   [], ["data_governance", "sensitive_elements", "source_caveats"], None),
  ("E2.3", "Download URL or Platform Link Available", 1, ALWAYS,
   "download_url is absent, but platform access instructions are given: third_party_sharing says data are available for download through FAIRhub upon license agreement; data_governance.access_review_process describes verified-ID login and license agreement; page https://fairhub.io/datasets/3 is the platform link.",
   "Platform route and access steps present; no direct download URL.",
   [c("/third_party_sharing/0/description", "through the FAIRhub platform"), c("data_governance.access_review_process", "logging in through a verified ID system"), c("page")], ["download_url"], [], [], "Rubric accepts platform access instructions; the missing direct URL did not lower the score."),
  ("E2.4", "Distribution Formats and File Types Specified", 1, ALWAYS,
   "distribution_formats: DICOM (application/dicom), Markdown, CSV, JSON with MIME types; file_collections resources carry format TSV/JSON/MD/TXT with media types (text/tab-separated-values etc.).",
   "Specific formats with MIME types.",
   [c("/distribution_formats/0/media_type", "application/dicom"), c("/file_collections/0/resources/0/media_type", "text/tab-separated-values")], [], [{"path": "distribution_formats", "claimed": n("distribution_formats")}], [], None),
  ("E2.5", "Related Datasets and External Resources Linked", 1, ALWAYS,
   "related_datasets link v2 and v1 DOIs; external_resources link docs.aireadi.org, aireadi.org, Zenodo community, GitHub organization and ClinicalTrials.gov NCT06002048.",
   "Both related datasets and external documentation linked.",
   [c("related_datasets"), c("/external_resources/0/external_resources/0", "https://docs.aireadi.org/")], [], [{"path": "external_resources", "claimed": n("external_resources")}], [], None),
 ]),
 (3, "Data Reuse and Interoperability", "Is sufficient information provided to reuse and integrate the dataset with others?", [
  ("E3.1", "License Terms Allow Reuse", 1, SHARED,
   "license_terms grant a license 'to download, reproduce and use the Data and create derivative works for research, commercial and non-commercial purposes' with security and sharing obligations; source_caveats records the FAIRhub restriction to type 2 diabetes research.",
   "Reuse permissions are explicit; a scope tension is transparently recorded (see issues).",
   [c("license_and_use_terms.license_terms", "create derivative works for research, commercial and non-commercial purposes")], [], [], ["license_and_use_terms.source_caveats"], None),
  ("E3.2", "Data Formats Are Standardized (encoding, format)", 1, SHARED,
   "Standard formats: DICOM for retinal imaging, WFDB for ECG, Open mHealth for wearables, OMOP-mapped CSV, TSV manifests, JSON metadata. No character encoding is stated for text files.",
   "Standard formats documented; encoding absent but secondary for these self-describing standards.",
   [c("/file_collections/0/conforms_to", "WaveForm DataBase (WFDB)"), c("/file_collections/3/conforms_to", "Digital Imaging and Communications in Medicine (DICOM)"), c("distribution_formats")], ["file_collections.resources.encoding"], [], [], "Formats are standardized; absent encoding recorded but not judged decisive."),
  ("E3.3", "Schema or Ontology Conformance Stated", 1, SHARED,
   "conforms_to: Clinical Dataset Structure (CDS) v0.1.1; per collection conformance to OMOP CDM, DICOM, WFDB, Open mHealth, ESDS.",
   "Named community schemas at dataset and collection level.",
   [c("conforms_to", "Clinical Dataset Structure (CDS) v0.1.1"), c("/file_collections/1/conforms_to", "The Observational Medical Outcomes Partnership (OMOP) Common Data Model (CDM)")], ["conforms_to_schema"], [], ["conforms_to_standard"], None),
  ("E3.4", "Variable Metadata with Identifiers Defined", 0, SHARED,
   "No variables block. participants.tsv/participants.json are listed only as file names; collection descriptions name measured domains (e.g., heart rate, sleep) but no variable identifiers, units or definitions are given.",
   "Variable-level metadata absent.",
   [], ["variables"], [], ["/file_collections/7/description", "/file_collections/9/resources/6/path"], None),
  ("E3.5", "Use Guidance Provided (intended, prohibited uses)", 1, ALWAYS,
   "prohibited_uses: 5 specific prohibitions (clinical treatment decisions, re-identification, sharing with model vendors for training, reproduction in publications, transfer to non-licensees) with reasons; allowed use is stated in license_terms and data_use_permission (disease_specific_research). intended_uses and discouraged_uses absent.",
   "Prohibited and permitted uses are clear; intended/discouraged slots unused.",
   [c("/prohibited_uses/0/description", "Licensees shall not make clinical treatment decisions based on the Data."), c("license_and_use_terms.data_use_permission")], ["intended_uses", "discouraged_uses"], [{"path": "prohibited_uses", "claimed": n("prohibited_uses")}], [], "Allowed and prohibited uses are documented; the empty slots did not lower the score."),
 ]),
 (4, "Ethical Use and Privacy Safeguards", "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.", [
  ("E4.1", "IRB or Ethics Review and Data Protection Impact", 1, HS_OR_REG,
   "ethical_reviews: University of Washington IRB approval STUDY00016228 with reliance agreements (UAB, UCSD), initial approval Dec 20 2022, annual renewal; human_subject_research.involves_human_subjects true with irb_approval. data_protection_impacts absent; source_caveats records the healthsheet statement that no DPIA was conducted.",
   "Concrete IRB documentation consistent with the human-subjects flag.",
   [c("/ethical_reviews/0/review_details", "approval number STUDY00016228"), c("human_subject_research.involves_human_subjects"), c("human_subject_research.irb_approval")], ["data_protection_impacts"], [], ["source_caveats"], None),
  ("E4.2", "Deidentification Method Described", 1, HS_OR_REG,
   "is_deidentified.method: no active de-identification (FAIRhub type NoDeIdentification), data checked for identifiable data per US HIPAA; deidentification_details: sex, race/ethnicity and medication removed; source_caveats records the Safe Harbor statement of the Nature Metabolism commentary.",
   "Method stated and its source conflict disclosed (see noted issue).",
   [c("is_deidentified.method", "checked for identifiable data per US HIPAA"), c("is_deidentified.deidentification_details", "information related to participants' sex and race/ethnicity and medication used has been removed")], ["is_deidentified.identifiers_removed"], [], ["is_deidentified.source_caveats", "is_deidentified.identifiable_elements_present"], None),
  ("E4.3", "Privacy Protections and Re-identification Risk Assessment", 1, HS,
   "participant_privacy: privacy-preserving device selection (no audio/video/GPS), data watermarking to deter reidentification, encrypted/locked storage. Re-identification risk is acknowledged in future_use_impacts ('theoretical risk of future re-identification') and mitigated by license prohibitions and withholding of zip code/sex/race to controlled access. No formal reidentification_risk field.",
   "Protections and acknowledged risk with mitigations; no formal assessment slot.",
   [c("/participant_privacy/1/privacy_techniques", "data watermarking to prevent reidentification"), c("/future_use_impacts/0/impact_details", "theoretical risk of future")], ["participant_privacy.reidentification_risk"], [{"path": "participant_privacy", "claimed": n("participant_privacy")}], [], "Risk and mitigations are documented in other slots; the missing structured field did not lower the score."),
  ("E4.4", "Informed Consent Obtained from Participants", 1, HS,
   "informed_consent: consent_obtained true; written electronic (e-signature in UW ITHS REDCap) or in-person consent; withdrawal_mechanism and consent_revocations state data already shared stays in the dataset.",
   "Consent type, documentation and withdrawal limits documented.",
   [c("/informed_consent/0/consent_type", "Written informed consent"), c("/informed_consent/0/withdrawal_mechanism", "Participants may withdraw consent at any time")], [], [], ["collection_consents", "consent_revocations"], None),
  ("E4.5", "Vulnerable Populations and Compensation Documented", 0, HS,
   "participant_compensation: $200 stipend after device return plus travel costs. at_risk_populations is absent and no protection for potentially vulnerable participants (e.g., adults up to 85 undergoing cognitive screening) is described; only eligibility exclusions (pregnancy, >85) appear in sampling_strategies.",
   "Compensation well documented; the vulnerable-population half of the item is missing.",
   [c("/participant_compensation/0/compensation_amount", "$200")], ["at_risk_populations"], [], ["/sampling_strategies/1/strategies"], None),
 ]),
 (5, "Data Composition and Structure", "Can the dataset's structure, modality, and population be understood from metadata?", [
  ("E5.1", "Cohort or Subpopulations Characteristics Described", 1, ALWAYS,
   "subpopulations: four diabetes-status study groups; sampling_strategies: triple-balanced design (four race/ethnic groups, four T2DM categories, sex), inclusion (>=40, English) and exclusion (pregnancy, gestational/type 1 diabetes, >85).",
   "Cohort characteristics and eligibility detailed.",
   [c("/subpopulations/0/identification", "Participants belong to one of four study groups"), c("/sampling_strategies/0/strategies", "triple-balanced")], ["subsets.is_subpopulation"], [], [], None),
  ("E5.2", "Number of Instances or Samples Reported", 1, ALWAYS,
   "instances.counts 2280 participants; splits 1576/352/352 sum to 2280; version_details 204 + 863 = 1067 and 1067 + 1213 = 2280 are arithmetically consistent.",
   "Specific counts, internally consistent.",
   [c("/instances/0/counts"), c("/splits/0/split_details", "1576 participants in train, 352 in validation and 352 in")], [], [], ["version_access.version_details"], None),
  ("E5.3", "Variable-Level Metadata, Tabular Flag, and Data Splits", 0, ALWAYS,
   "Splits are documented (70/15/15 train/validation/test in participants.tsv), but there is no variables block, no is_tabular flag and no subsets with split/subpopulation flags.",
   "Data splits present; variable-level metadata, the core of the item, is absent.",
   [c("/splits/0/description", "70%/15%/15%")], ["variables", "is_tabular", "subsets.is_data_split", "subsets.is_subpopulation"], [], [], None),
  ("E5.4", "Data Topics or Conditions Represented", 1, ALWAYS,
   "instances describe individual participants; conditions are stated in description (individuals with and without T2DM) and subpopulations (healthy, pre-diabetes, oral-medication, insulin-dependent), with modality topics in file_collections.",
   "Condition and topic coverage clear.",
   [c("/instances/0/instance_type", "Individual participant"), c("description", "individuals with and without type 2 diabetes mellitus (T2DM)")], [], [], ["subpopulations"], None),
  ("E5.5", "Data Quality, Anomalies, and Missing Data Documented", 1, ALWAYS,
   "anomalies: 6 modality-specific entries (survey nonresponse, wearable failure, imaging noise, handheld fundus quality, Spectralis operator dependence, FLIO compliance); missing_data_documentation: patterns and causes; sampling_strategies: 4 entries.",
   "Specific anomalies, missingness and sampling.",
   [c("/anomalies/3/anomaly_details", "Optomed Aurora"), c("/missing_data_documentation/0/missing_data_causes", "battery died")], [], [{"path": "anomalies", "claimed": n("anomalies")}, {"path": "sampling_strategies", "claimed": n("sampling_strategies")}], [], None),
 ]),
 (6, "Data Provenance and Version Tracking", "Can a user determine dataset versions, update history, and provenance?", [
  ("E6.1", "Dataset Version Number Provided", 1, SHARED,
   "version: 3.0.0, consistent with title/description and version_access.",
   "Semantic version present.", [c("version", "3.0.0")], [], [], [], None),
  ("E6.2", "Version Access Methods Documented", 1, SHARED,
   "version_access: latest_version_doi doi:10.60775/fairhub.3; versions_available with DOIs and dates for 3.0.0/2.0.0/1.0.0; states v2.0.0 is no longer accessible.",
   "Per-version DOIs and accessibility status.",
   [c("version_access.latest_version_doi", "doi:10.60775/fairhub.3"), c("/version_access/versions_available/1", "2.0.0 (doi:10.60775/fairhub.2, Nov 8, 2024)")], [], [{"path": "version_access.versions_available", "claimed": len(doc["version_access"]["versions_available"])}], [], None),
  ("E6.3", "Change Descriptions and Errata Provided", 1, SHARED,
   "updates.update_details and version_access.version_details describe changes (participant increments, Snellen acuity variables dropped in 3.0.0); CHANGELOG.md is a listed resource. errata absent.",
   "Concrete change descriptions; no errata entries.",
   [c("version_access.version_details", "the Snellen visual acuity variables were dropped"), c("updates.update_details")], ["errata"], [], [], "Change descriptions satisfy the item; absent errata did not lower the score."),
  ("E6.4", "Update Schedule or Frequency Indicated", 1, SHARED,
   "updates.frequency: approximately once a year, new versions with additional participants.",
   "Explicit schedule.", [c("updates.frequency", "Approximately once a year")], [], [], [], None),
  ("E6.5", "Provenance, Source Derivation, and Raw Data Sources", 1, SHARED,
   "raw_data_sources: ECG XML export, MoCA Duo CSV, NORC laboratory CSV; raw_sources: retained raw data not shared; updates.update_details explains static versions built from new participant visits. was_derived_from absent.",
   "Raw sources and derivation described.",
   [c("/raw_data_sources/0/source_description", "ECG data exported from the device in raw format"), c("/raw_sources/0/raw_data_details"), c("updates.update_details")], ["was_derived_from"], [{"path": "raw_data_sources", "claimed": n("raw_data_sources")}], [], None),
 ]),
 (7, "Scientific Motivation and Funding Transparency", "Does the metadata clearly state why the dataset exists and who funded it?", [
  ("E7.1", "Motivation or Purpose for Dataset Creation", 1, ALWAYS,
   "purposes (3): salutogenesis in T2DM, collecting/sharing an AI-ready multimodal dataset, enabling future AI/ML research; addressing_gaps (3) give rationale.",
   "Clear scientific rationale.",
   [c("/purposes/0/description", "salutogenesis"), c("addressing_gaps")], [], [{"path": "purposes", "claimed": n("purposes")}], [], None),
  ("E7.2", "Primary Research Objectives or Tasks", 1, ALWAYS,
   "tasks: pseudotime manifold analysis to predict disease trajectories from multimodal data.",
   "One specific intended analysis.",
   [c("/tasks/0/description", "pseudotime manifold analysis")], [], [], [], None),
  ("E7.3", "Funding Sources and Mechanisms Listed", 1, ALWAYS,
   "funders: National Institutes of Health via the Bridge2AI Program (grantor stated); Research to Prevent Blindness with source caveat.",
   "Named funders with mechanism.",
   [c("/funders/0/description", "through its Bridge2AI Program"), c("/funders/1/name", "Research to Prevent Blindness")], [], [{"path": "funders", "claimed": n("funders")}], [], None),
  ("E7.4", "Grant IDs or Award Numbers Present", 1, ALWAYS,
   "grants: OT2OD032644 (OT2 activity, OD institute), P30DK035816 (P30, NIDDK), UL1TR003096 (UL1, NCATS); all follow NIH activity-IC-serial convention. Typographical variants (1OT2OD032644, OT2ODO32644) are disclosed.",
   "Valid NIH-pattern award identifiers with provenance notes.",
   [c("/funders/0/grants/0/grant_number", "OT2OD032644"), c("/funders/0/grants/1/grant_number", "P30DK035816"), c("/funders/0/grants/2/grant_number", "UL1TR003096")], [], [{"path": "/funders/0/grants", "claimed": len(doc["funders"][0]["grants"])}], [], None),
  ("E7.5", "Creators and Acknowledgements Documented", 1, ALWAYS,
   "creators: Aaron Lee (designated PI), AI-READI Consortium, and 15 further investigators with ORCIDs and ROR affiliations; affiliation discrepancy for Aaron Lee disclosed in source_caveats.",
   "Comprehensive, identifier-backed attribution.",
   [c("/creators/0/name", "Aaron Lee"), c("/creators/1/name", "AI-READI Consortium")], [], [{"path": "creators", "claimed": n("creators")}], ["funders", "maintainers"], None),
 ]),
 (8, "Technical Transparency (Data Collection and Processing)", "Can data collection and processing steps be replicated or understood?", [
  ("E8.1", "Collection Mechanisms and Settings Described", 1, undeclared("data_collection"),
   "collection_mechanisms name REDCap, questionnaires, and specific devices (Philips PageWriter TC30, Dexcom G6, Garmin Vivosmart 5, Heidelberg Spectralis, Topcon Maestro2, Zeiss Cirrus 5000, etc.); collection_timeframes and data_collectors give dates and three sites.",
   "Detailed mechanisms, settings and timeframes.",
   [c("/collection_mechanisms/2/name", "Philips PageWriter TC30 Cardiograph"), c("collection_timeframes")], [], [{"path": "collection_mechanisms", "claimed": n("collection_mechanisms")}], ["data_collectors", "direct_collection"], None),
  ("E8.2", "Data Acquisition Methods Listed", 1, undeclared("data_collection"),
   "acquisition_methods: directly observed (labs, vitals, retinal imaging) and subject-reported with verification (medication cross-referencing); raw_data_sources give device export formats.",
   "Acquisition types with verification and raw formats.",
   [c("/acquisition_methods/1/acquisition_details", "cross-referencing entered medications"), c("raw_data_sources")], [], [{"path": "acquisition_methods", "claimed": n("acquisition_methods")}], [], None),
  ("E8.3", "Preprocessing, Cleaning, Labeling, and Annotation Quality", 1, undeclared("data_processing"),
   "preprocessing_strategies: DICOM conversion, OMOP CDM mapping; cleaning_strategies: site data-manager QC, REDCap range checks/edits under PI guidance, internal PII review. No labeling (source_caveats: no labels provided); imputation not documented.",
   "Preprocessing and cleaning described concretely; labeling N/A by statement.",
   [c("/preprocessing_strategies/1/preprocessing_details", "Observational Medical Outcomes Partnership (OMOP) Common Data Model"), c("/cleaning_strategies/1/cleaning_details", "credibility range checks")], ["labeling_strategies", "annotation_analyses", "machine_annotation_tools", "imputation_protocols"], [{"path": "cleaning_strategies", "claimed": n("cleaning_strategies")}], [], "Preprocessing and cleaning satisfy the item; missing imputation is scored under E8.5."),
  ("E8.4", "Software and Tools Documented", 0, undeclared("processing_software"),
   "No software that produced or transformed the released data is named. preprocessing_strategies describe DICOM conversion and OMOP mapping without naming tools; REDCap (cleaning_strategies/collection_mechanisms) is the data-entry/capture application whose reports flagged out-of-range values for human correction - roles (a) capture and (d) validation; MoCA Duo is capture (a); the OMOP Data Quality Dashboard (dqd_omop.json) is quality assessment (d); external_resources GitHub organization is a publisher account root only.",
   "Score 0: no processing/transformation software named; documented software falls under roles (a) and (d).",
   [c("/cleaning_strategies/1/name", "REDCap range checks and edits"), c("/file_collections/1/resources/0/description", "OMOP CDM Data Quality Dashboard (DQD)"), c("/external_resources/3/external_resources/0", "https://github.com/AI-READI")],
   ["preprocessing_strategies.used_software", "cleaning_strategies.used_software", "machine_annotation_tools", "labeling_strategies", "imputation_protocols"], [],
   ["preprocessing_strategies", "cleaning_strategies", "external_resources", "collection_mechanisms"], None),
  ("E8.5", "External Standards, Resources, and Imputation Protocols", 0, ALWAYS,
   "external_resources (documentation site, project site, Zenodo community, GitHub, ClinicalTrials.gov) and conforms_to CDS v0.1.1 are present, but there is no imputation protocol nor any statement that imputation was not used, although missing_data_documentation reports modality-level missingness.",
   "External resources and standards present; the imputation-protocol component is absent.",
   [c("external_resources"), c("conforms_to", "Clinical Dataset Structure (CDS) v0.1.1")], ["imputation_protocols"], [{"path": "external_resources", "claimed": n("external_resources")}], ["missing_data_documentation"], None),
 ]),
 (9, "Dataset Evaluation and Limitations Disclosure", "Does the metadata communicate known risks, biases, or dataset limitations?", [
  ("E9.1", "Known Limitations Documented", 1, ALWAYS,
   "known_limitations: English-language eligibility, unbalanced interim releases, urban hospital-based recruitment, missing races/ethnicities (Pacific Islanders, Native Americans).",
   "Specific limitations with consequences.",
   [c("/known_limitations/0/limitation_description", "Participants were required to speak, read and understand English")], [], [{"path": "known_limitations", "claimed": n("known_limitations")}], [], None),
  ("E9.2", "Biases Categorized Using Standard Taxonomy (RAI-aligned)", 1, ALWAYS,
   "known_biases: volunteer bias categorized as bias_type selection_bias with generalizability impact; representativeness limits in known_limitations and sampling why_not_representative.",
   "One categorized bias with standard type; representativeness covered.",
   [c("/known_biases/0/bias_type", "selection_bias"), c("/known_biases/0/bias_description", "volunteer bias")], [], [{"path": "known_biases", "claimed": n("known_biases")}], ["future_use_impacts"], None),
  ("E9.3", "Data Anomalies and Quality Issues Noted", 1, ALWAYS,
   "anomalies: 6 modality-specific quality issues; source_caveats records file/byte total discrepancies (356,334 vs 356,343 files).",
   "Concrete anomalies plus self-checked totals.",
   [c("/anomalies/4/anomaly_details", "quality issues may arise"), c("source_caveats", "9 fewer than the stated 356,343")], [], [{"path": "anomalies", "claimed": n("anomalies")}], [], None),
  ("E9.4", "Sensitive Content and Warnings Provided", 1, ALWAYS,
   "sensitive_elements: controlled-access data (5-digit zip, sex, race, ethnicity, genetic sequencing, health records, medications, accident reports) withheld from the public release. content_warnings absent; source_caveats notes the healthsheet's 'nothing offensive' statement.",
   "Sensitive content documented; no content warnings needed for this content.",
   [c("/sensitive_elements/0/sensitivity_details", "5-digit zip code")], ["content_warnings"], [], ["source_caveats"], "Sensitive elements documented; missing content_warnings did not lower the score."),
  ("E9.5", "Ethical Review and Social Impact Analysis", 1, ALWAYS,
   "ethical_reviews: UW IRB STUDY00016228; future_use_impacts: no anticipated unfair-treatment uses, theoretical re-identification risk; mitigations appear in participant_privacy and prohibited_uses. No conflict-of-interest statement.",
   "Ethics review and a brief impact statement with mitigations elsewhere.",
   [c("/ethical_reviews/0/reviewing_organization", "University of Washington Institutional Review Board"), c("/future_use_impacts/0/impact_details", "do not currently anticipate uses that could result in")], [], [], [], None),
 ]),
 (10, "Cross-Platform and Community Integration", "Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain.", [
  ("E10.1", "Dataset Published on a Recognized Platform", 1, SHARED,
   "publisher: https://fairhub.io/ (FAIRhub), with DOI under FAIRhub prefix and landing page.",
   "Recognized repository.", [c("publisher", "https://fairhub.io/")], [], [], [], None),
  ("E10.2", "Citation and DOI for Cross-referencing", 1, SHARED,
   "doi 10.60775/fairhub.3 present for cross-referencing; no recommended citation string (citation absent).",
   "DOI present; citation text missing.",
   [c("doi", "10.60775/fairhub.3")], ["citation"], [], [], "A DOI provides cross-referencing; the missing citation text is a noted gap."),
  ("E10.3", "Community Standards or Schema Conformance", 1, SHARED,
   "conforms_to CDS v0.1.1; collections conform to OMOP CDM, DICOM, WFDB, Open mHealth.",
   "Community standards stated.", [c("conforms_to", "Clinical Dataset Structure (CDS) v0.1.1")], [], [], ["conforms_to_standard"], None),
  ("E10.4", "Outreach Materials and Documentation Links", 1, SHARED,
   "external_resources: docs.aireadi.org documentation, aireadi.org, Zenodo community, GitHub org, ClinicalTrials.gov; page FAIRhub landing page.",
   "Documentation and landing links present.",
   [c("/external_resources/0/name", "AI-READI dataset documentation"), c("page")], [], [], [], None),
  ("E10.5", "Related Datasets with Typed Relationships", 1, SHARED,
   "related_datasets: two entries typed is_new_version_of with DOIs and notes.",
   "Typed relationships.", [c("/related_datasets/1/relationship_type", "is_new_version_of")], [], [{"path": "related_datasets", "claimed": n("related_datasets")}], [], None),
 ]),
]

ISSUES = [
 {"description": "No confidentiality classification, HIPAA-compliance status or governance committee contact; only storage/NIH GDS obligations are listed.",
  "severity": "medium", "item_ids": ["E2.2"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "completeness",
  "fields_involved": ["regulatory_restrictions", "data_governance"], "recommendation": "Add confidentiality_level, hipaa_compliant status and a data_governance.committee_contact for the Data Access Committee."},
 {"description": "No variable-level metadata (variables), tabular flag or subset flags, although participants.tsv and OMOP-mapped CSV tables are distributed.",
  "severity": "high", "item_ids": ["E3.4", "E5.3"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
  "fields_involved": ["variables", "is_tabular", "subsets"], "recommendation": "Add a variables block (identifiers, descriptions, units) for participants.tsv and the OMOP-mapped tables, plus is_tabular and subset flags."},
 {"description": "at_risk_populations absent: no statement on protections for potentially vulnerable participants (older adults to age 85, cognitive screening).",
  "severity": "medium", "item_ids": ["E4.5"], "score_effect": "lowered", "category": "consent_ethics", "type": "completeness",
  "fields_involved": ["at_risk_populations"], "recommendation": "Populate at_risk_populations describing any protections for older or cognitively impaired participants, or state that none were enrolled."},
 {"description": "No software that produced or transformed the released data (DICOM conversion, OMOP mapping, CDS packaging) is named; REDCap, MoCA Duo and the OMOP DQD serve capture or validation roles.",
  "severity": "medium", "item_ids": ["E8.4"], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
  "fields_involved": ["preprocessing_strategies", "cleaning_strategies"], "recommendation": "Name the software used for DICOM conversion, OMOP mapping and CDS packaging in used_software, with versions or repositories."},
 {"description": "No imputation protocol or explicit statement that imputation was not used, despite documented modality-level missingness.",
  "severity": "low", "item_ids": ["E8.5"], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
  "fields_involved": ["imputation_protocols", "missing_data_documentation"], "recommendation": "Add imputation_protocols, or state explicitly that no imputation was performed."},
 {"description": "De-identification method 'no identifiers were collected / NoDeIdentification' coexists with removal of sex, race/ethnicity and medication and with a Safe Harbor statement from another source; the record discloses the conflict in source_caveats.",
  "severity": "low", "item_ids": [], "score_effect": "noted_only", "category": "source_conflict", "type": "consistency",
  "fields_involved": ["is_deidentified"], "recommendation": "Reconcile or explain the de-identification method across sources and list identifiers_removed."},
 {"description": "License text grants research, commercial and non-commercial use while FAIRhub consent metadata restricts the public version to type 2 diabetes research; both recorded.",
  "severity": "low", "item_ids": [], "score_effect": "noted_only", "category": "license_use_terms", "type": "consistency",
  "fields_involved": ["license_and_use_terms"], "recommendation": "State which use scope governs the public release (T2D-only vs general research) in license_and_use_terms."},
 {"description": "No recommended citation text; only the DOI supports citation.",
  "severity": "low", "item_ids": [], "score_effect": "noted_only", "category": "persistent_identifier", "type": "completeness",
  "fields_involved": ["citation"], "recommendation": "Add a recommended citation string in citation."},
]

elements, total = [], 0
for eid, ename, edesc, items in ELEMENTS:
    subs, escore = [], 0
    for (iid, name, score, appl, ev, qn, cited, absent, counts, considered, nir) in items:
        status = "applicable" if appl == ALWAYS else "unknown"
        sub = {"name": name, "score": score, "evidence": ev, "quality_note": qn,
               "applicable": True, "applicability_status": status, "applicability_evidence": appl,
               "unit_scores": [{"path": "#", "score": score, "evidence": ev, "cited": cited,
                                "absent": [{"path": p} for p in absent], "counts": counts,
                                "considered": considered}],
               "item_id": iid}
        if nir:
            sub["no_issue_reason"] = nir
        subs.append(sub)
        escore += score
    total += escore
    elements.append({"id": eid, "name": ename, "description": edesc, "sub_elements": subs,
                     "element_score": escore, "element_max": 5})

result = {
 "rubric": "rubric10-semantic", "version": "3.0",
 "d4d_file": str(INPUT.relative_to(ROOT)),
 "project": "AI_READI", "method": "claudecode_agent",
 "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2",
 "evaluation_timestamp": "2026-11-22T00:00:00Z",
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
     "Identifiers validate: DOI 10.60775/fairhub.3 matches FAIRhub publisher/page; NIH awards OT2OD032644, P30DK035816, UL1TR003096 follow activity-IC-serial patterns; ORCIDs and ROR IDs well-formed.",
     "Counts are internally consistent: splits 1576+352+352 = 2280 = instances.counts; version increments 204+863 = 1067 and 1067+1213 = 2280.",
     "Temporal order is coherent: IRB approval Dec 20 2022 precedes collection (July 2023 - May 2025) and release (Nov 17 2025).",
     "Human-subjects flag true is matched by IRB approval and informed consent documentation.",
     "Weakest areas: variable-level metadata, named processing software, imputation, vulnerable-population protections and governance contact."],
   "consistency_checks": {"passed": 5, "failed": 0, "warnings": 2},
   "correctness_validations": {"doi_format": "valid", "grant_number_format": "valid", "rrid_format": "not_applicable", "url_validity": "valid"}},
 "applicability_context": CONTEXT,
 "evaluation_scope": {"policy": "single_dataset", "units": [{"path": "#", "id": doc["id"]}],
                      "collection_metadata_inherited": False},
 "metadata": {"instrument_sha256": sha(AGENT), "evidence_authority_sha256": sha(AUTHORITY),
              "rubric_sha256": sha(RUBRIC), "input_sha256": sha(INPUT),
              "context_sha256": context_digest(CONTEXT)},
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(total, OUTPUT)
