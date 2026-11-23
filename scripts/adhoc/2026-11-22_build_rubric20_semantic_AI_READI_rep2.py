# Purpose: serialize a manual rubric20-semantic (v3.0, general context instrument v3)
# evaluation of one D4D record into JSON. Judgements were made by the evaluating
# session (claude-opus-5-5); this script only encodes them and computes digests.
# Inputs: data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/AI_READI_d4d.yaml,
#         .claude/agents/d4d-rubric20-semantic.md, data/rubric/rubric20.txt,
#         data/rubric/semantic_evidence_authority_v3.json
# Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep2_evaluation.json
# Date: 2026-11-22
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from data_sheets_schema.evaluation_context import context_digest

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/AI_READI_d4d.yaml"
AGENT = ".claude/agents/d4d-rubric20-semantic.md"
RUBRIC = "data/rubric/rubric20.txt"
AUTH = "data/rubric/semantic_evidence_authority_v3.json"
OUT = "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep2_evaluation.json"
MODEL = "claude-opus-5-5"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ALWAYS = "This item applies to every dataset"


def unknown(pred):
    return f"{pred}: not declared by the caller (no applicability context supplied); unknown, retained in the denominator"


def q(id_, name, desc, stype, score, label, evidence, note, cited=(), absent=(), counts=(), considered=(),
      pred=None, no_issue_reason=None):
    mx = 1 if stype == "pass_fail" else 5
    item = {
        "id": id_, "name": name, "description": desc[:120], "score_type": stype,
        "score": score, "max_score": mx, "score_label": label, "evidence": evidence,
        "quality_note": note, "applicable": True,
        "applicability_status": "unknown" if pred else "applicable",
        "applicability_evidence": unknown(pred) if pred else ALWAYS,
        "unit_scores": [{
            "path": "#", "score": score, "evidence": evidence,
            "cited": [dict(c) for c in cited],
            "absent": [{"path": a} for a in absent],
            "counts": [{"path": p, "claimed": n} for p, n in counts],
            "considered": list(considered),
        }],
    }
    if no_issue_reason:
        item["no_issue_reason"] = no_issue_reason
    return item


def c(path, quote=None):
    d = {"path": path}
    if quote:
        d["quote"] = quote
    return d


cat1 = [
    q(1, "Field Completeness",
      "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
      "numeric", 3, "Good (~70% populated)",
      "10 of 14 listed fields populated (id, title, description, keywords, license_and_use_terms, doi, page, creators, purposes, instances); top-level resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent (71%).",
      "71% of the listed fields populated sits in the ~70% band, below the >=90% anchor for 5. No variable-level dictionary is documented.",
      cited=[c("/id", "doi:10.60775/fairhub.3"), c("/title", "Flagship Dataset of Type 2 Diabetes from the AI-READI Project"),
             c("/doi", "10.60775/fairhub.3"), c("/page", "https://fairhub.io/datasets/3"), c("/description"),
             c("/keywords"), c("/license_and_use_terms/license_terms"), c("/creators"), c("/purposes"), c("/instances")],
      absent=["resources", "parent_datasets", "variables", "regulatory_restrictions.confidentiality_level"],
      considered=["/regulatory_restrictions", "/file_collections"]),
    q(2, "Entry Length Adequacy",
      "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
      "numeric", 5, "Excellent (>200 chars)",
      "description is ~1,400 characters; three purposes each carry a ~150-200 character description; the average narrative length exceeds 200 characters.",
      "Narrative content is substantive and specific (participant count, collection dates, modalities, file count, size, structure standard).",
      cited=[c("/description", "This version contains data from 2280 participants collected between July 19, 2023 and May 1, 2025."),
             c("/purposes/1/description", "The primary goal of the AI-READI project is to collect and publicly share a multimodal, AI-ready dataset")],
      counts=[("/purposes", 3)],
      no_issue_reason="Maximum score; no deduction."),
    q(3, "Keyword Diversity",
      "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply additional topic evidence where documented; no named study or disease count is presumed.",
      "numeric", 5, "Excellent (>=8 keywords)",
      "9 distinct keywords, spanning condition (Diabetes mellitus), methods (Machine Learning, Artificial Intelligence) and modalities (Electrocardiography, Continuous Glucose Monitoring, Retinal imaging, Eye exam).",
      "Keywords are free text rather than controlled-vocabulary terms, but distinct and topical.",
      cited=[c("/keywords/0", "Diabetes mellitus"), c("/keywords/4", "Continuous Glucose Monitoring")],
      counts=[("/keywords", 9)],
      no_issue_reason="Maximum score; no deduction."),
    q(4, "File Enumeration and Type Variety",
      "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in separate linked resources. Examine every distribution; modality breadth is distinct from suitability for machine learning.",
      "numeric", 5, "Excellent (>3 file types)",
      "distribution_formats lists DICOM, Markdown, CSV and JSON; file_collections add TSV and TXT resources and per-modality standards (WFDB, OMOP CDM, ESDS, Open mHealth); total_file_count 356343.",
      "More than three file types across ten file collections that cover imaging, waveform, wearable, environmental and clinical modalities, consistent with the multimodal description.",
      cited=[c("/distribution_formats/0/media_type", "application/dicom"), c("/distribution_formats/2/media_type", "text/csv"),
             c("/file_collections/0/resources/0/media_type", "text/tab-separated-values"), c("/total_file_count")],
      counts=[("/distribution_formats", 4), ("/file_collections", 10)],
      no_issue_reason="Maximum score; no deduction."),
    q(5, "Data File Size Availability",
      "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
      "pass_fail", 1, "Pass",
      "total_size_bytes 3815969779678, per-collection total_bytes, instance count 2280 and a 1576/352/352 split are documented.",
      "Byte and instance metadata both present; the record itself reconciles per-directory sums against the totals.",
      cited=[c("/total_size_bytes"), c("/file_collections/0/total_bytes"), c("/instances/0/counts"),
             c("/splits/0/split_details", "1576 participants in train, 352 in validation and 352 in test")],
      no_issue_reason="Pass; no deduction."),
]

cat2 = [
    q(6, "Dataset Identification Metadata",
      "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or repository).",
      "pass_fail", 1, "Pass",
      "DOI 10.60775/fairhub.3 (FAIRhub DataCite prefix), id doi:10.60775/fairhub.3, landing page https://fairhub.io/datasets/3 and publisher https://fairhub.io/.",
      "Persistent identifier and hosting platform both identified and mutually consistent.",
      cited=[c("/doi", "10.60775/fairhub.3"), c("/publisher", "https://fairhub.io/"), c("/page", "https://fairhub.io/datasets/3"), c("/id")],
      no_issue_reason="Pass; no deduction."),
    q(7, "Funding and Acknowledgements Completeness",
      "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
      "numeric", 5, "Excellent (funders with grants + affiliated creators)",
      "NIH with grants OT2OD032644, P30DK035816, UL1TR003096 (all match NIH activity-code/IC/serial patterns); Research to Prevent Blindness; 17 creators, 16 with ORCID and ROR-identified affiliations.",
      "Grant numbers are well-formed and their provenance is caveated (OT2ODO32644 typo variant reconciled). The Research to Prevent Blindness funder has no award number, a minor gap.",
      cited=[c("/funders/0/grants/0/grant_number", "OT2OD032644"), c("/funders/0/grants/1/grant_number", "P30DK035816"),
             c("/funders/0/grants/2/grant_number", "UL1TR003096"), c("/creators/0/principal_investigator/affiliation/0/id", "ROR:01yc7t268")],
      counts=[("/creators", 17), ("/funders", 2)],
      considered=["/funders/0/source_caveats", "/creators/0/source_caveats"],
      no_issue_reason="Maximum score; no deduction."),
    q(8, "Ethical and Privacy Declarations",
      "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable.",
      "numeric", 3, "Good (IRB + deidentification, not comprehensive)",
      "UW IRB STUDY00016228 with reliance agreements, involves_human_subjects true, e-consent with withdrawal terms, $200 stipend, privacy techniques and deidentification statement are documented. at_risk_populations and data_protection_impacts are absent (the latter only noted as 'no data protection impact analysis has been conducted' in source_caveats); no HIPAA compliance flag or governance-committee contact; deidentification method is internally conflicting (NoDeIdentification vs Safe Harbor).",
      "Strong IRB/consent/compensation coverage, but the 5 anchor requires all protections and data protection impacts; vulnerable-population and impact documentation are missing and the deidentification method is unresolved.",
      cited=[c("/ethical_reviews/0/name", "University of Washington IRB approval STUDY00016228"),
             c("/human_subject_research/involves_human_subjects"), c("/informed_consent/0/withdrawal_mechanism"),
             c("/participant_compensation/0/compensation_amount", "$200"),
             c("/is_deidentified/method", "No active de-identification"),
             c("/is_deidentified/source_caveats", "via the Safe Harbor method"),
             c("/participant_privacy/0/privacy_techniques")],
      absent=["at_risk_populations", "data_protection_impacts", "regulatory_restrictions.hipaa_compliant",
              "regulatory_restrictions.governance_committee_contact", "regulatory_restrictions.other_compliance"],
      considered=["/future_use_impacts", "/source_caveats", "/regulatory_restrictions/regulatory_restrictions"],
      pred="human_subjects"),
    q(9, "Access Requirements and Governance Documentation",
      "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts.",
      "numeric", 3, "Good (license + restrictions, no confidentiality classification)",
      "Detailed AI-READI Data License Agreement v2.0 terms, data_use_permission disease_specific_research, IP restriction (title remains with Licensor), regulatory restrictions (HIPAA BAA storage, NIH GDS security), access review process. No confidentiality_level classification or governance committee contact; license text (commercial use allowed) conflicts with consent metadata (T2D-only research), disclosed in source_caveats.",
      "License and restrictions are well documented; the 5 anchor's confidentiality classification is missing, so 3.",
      cited=[c("/license_and_use_terms/license_terms", "AI-READI Data License Agreement (Version 2.0)"),
             c("/license_and_use_terms/data_use_permission/0", "disease_specific_research"),
             c("/ip_restrictions/restrictions/0"), c("/regulatory_restrictions/regulatory_restrictions/1"),
             c("/data_governance/access_review_process", "logging in through a verified ID system"),
             c("/license_and_use_terms/source_caveats", "only be used for type 2 diabetes related research")],
      absent=["regulatory_restrictions.confidentiality_level", "regulatory_restrictions.governance_committee_contact",
              "data_protection_impacts"],
      considered=["/license"]),
    q(10, "Interoperability, Standardization, and Cross-Platform Integration",
      "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures.",
      "numeric", 5, "Excellent (standards + schema conformance + integration)",
      "Standard formats (DICOM, CSV, JSON, TSV); dataset conforms_to Clinical Dataset Structure v0.1.1; collections conform to OMOP CDM, WFDB, Open mHealth, ESDS and DICOM; OMOP mapping documented; typed related_datasets (is_new_version_of) with DOIs; external resources.",
      "Strong standard-model conformance per modality enabling cross-platform integration. conforms_to_schema and compression are absent, which does not undercut the 5 anchor.",
      cited=[c("/conforms_to", "Clinical Dataset Structure (CDS) v0.1.1"),
             c("/file_collections/1/conforms_to", "The Observational Medical Outcomes Partnership (OMOP) Common Data Model (CDM)"),
             c("/file_collections/7/conforms_to", "Open mHealth"),
             c("/related_datasets/0/relationship_type", "is_new_version_of"), c("/distribution_formats")],
      absent=["conforms_to_schema", "compression"],
      considered=["/external_resources", "/conforms_to_standard"],
      pred="shared_dataset", no_issue_reason="Maximum score; no deduction."),
]

cat3 = [
    q(11, "Tool and Software Transparency",
      "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs.",
      "numeric", 3, "Good (strategies listed, no versions/URLs)",
      "Preprocessing (conversion to DICOM, mapping to OMOP CDM) and cleaning (site QC, REDCap range checks, internal PII review) are described; REDCap and OMOP DQD are named but no software versions, conversion tool names or code URLs are given; labeling, machine annotation and imputation are not documented.",
      "At least one strategy documented, but the 5 anchor requires software versions/URLs.",
      cited=[c("/preprocessing_strategies/0/preprocessing_details", "some images required conversion to the DICOM standard format"),
             c("/preprocessing_strategies/1/name", "Mapping to OMOP CDM"),
             c("/cleaning_strategies/1/cleaning_details", "flagged in REDCap reports")],
      absent=["labeling_strategies", "machine_annotation_tools", "imputation_protocols", "annotation_analyses"],
      considered=["/missing_data_documentation", "/cleaning_strategies"],
      pred="data_processing"),
    q(12, "Collection Protocol Clarity",
      "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
      "numeric", 5, "Excellent (full collection protocol)",
      "Acquisition methods (direct observation, subject-reported with verification); 25 named collection mechanisms/devices; data collectors (trained site personnel, UAB, UCSD, UW); timeframes with dates (pilot 2023-07-18 to 2023-11-30, v3.0.0 2023-07-19 to 2025-05-01); raw data sources with formats.",
      "Full protocol with methods, collectors and timeframes. A one-day discrepancy in collection start dates is disclosed in source_caveats.",
      cited=[c("/collection_mechanisms/11/name", "Dexcom G6 continuous glucose monitor"),
             c("/data_collectors/0/collector_details"), c("/collection_timeframes/2/end_date", "2025-05-01"),
             c("/acquisition_methods/1/acquisition_details"), c("/raw_data_sources/0/raw_data_format", ".xml")],
      counts=[("/collection_mechanisms", 25), ("/data_collectors", 4)],
      pred="data_collection", no_issue_reason="Maximum score; no deduction."),
    q(13, "Version History, Maintenance, and Sustainability",
      "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access.",
      "numeric", 3, "Good (version + access + persistent ID)",
      "version 3.0.0 with DOIs for all three versions, change notes (participant counts, Snellen variables dropped), annual update cadence, maintainers (WashU, AI-READI team, contact URL), DOI and publisher. No errata; no explicit long-term preservation commitment for released versions, and v2.0.0 is stated to be no longer accessible despite its DOI.",
      "Comprehensive versioning but sustainability is incomplete: no preservation commitment and withdrawal of a DOI-registered version undermines durable access.",
      cited=[c("/version", "3.0.0"), c("/version_access/versions_available/1", "2.0.0 (doi:10.60775/fairhub.2, Nov 8, 2024)"),
             c("/version_access/version_details", "The version 2.0.0 documentation states that version is no longer accessible."),
             c("/updates/frequency"), c("/maintainers/1/maintainer_details", "https://aireadi.org/contact")],
      absent=["errata"],
      considered=["/doi", "/publisher", "/raw_sources"],
      pred="shared_dataset"),
    q(14, "Associated Publications",
      "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources.",
      "numeric", 3, "Good (references, no formal dataset citation)",
      "Five distinct external resources (docs.aireadi.org, aireadi.org, Zenodo community, GitHub organization, ClinicalTrials.gov NCT06002048) and a dataset DOI, but no citation field with a formal dataset citation; the BMJ Open and Nature Metabolism papers are mentioned only in caveats without identifiers.",
      "The 5 anchor requires a formal dataset citation, which is absent.",
      cited=[c("/external_resources/0/external_resources/0", "https://docs.aireadi.org/"),
             c("/external_resources/4/external_resources/0", "https://classic.clinicaltrials.gov/ct2/show/NCT06002048"),
             c("/doi")],
      absent=["citation"],
      counts=[("/external_resources", 5)]),
    q(15, "Human Subject Representation",
      "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups.",
      "numeric", 5, "Excellent (demographic design + inclusion/exclusion criteria)",
      "2280 participant instances; four diabetes-status subpopulations; triple-balanced recruitment by race/ethnicity (Asian, Black, White, Hispanic), sex and T2DM status; inclusion (>=40, English, consent) and exclusion (pregnancy, gestational/type 1 diabetes, >85) criteria; EHR-based wave recruitment; representation limitations.",
      "Detailed recruitment demographics and eligibility criteria. Realized per-group counts in this release are not given (sex/race withheld from the public release), noted without lowering.",
      cited=[c("/instances/0/counts"), c("/subpopulations/0/identification", "Pre-diabetes/Lifestyle Controlled"),
             c("/sampling_strategies/0/strategies", "four race/ethnic groups (Asian, Black, White, Hispanic)"),
             c("/sampling_strategies/1/strategies", "40 years or older"),
             c("/known_limitations/3/limitation_description")],
      absent=["at_risk_populations"],
      considered=["/missing_data_documentation", "/splits"],
      pred="human_subjects", no_issue_reason="Maximum score; the realized-demographics gap is a noted-only issue."),
]

cat4 = [
    q(16, "Findability (Persistent Links)",
      "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
      "pass_fail", 1, "Pass",
      "DOI, FAIRhub landing page and five external resource URLs are present.",
      "Persistent links are present and well-formed; no download_url, but the landing page serves access.",
      cited=[c("/page", "https://fairhub.io/datasets/3"), c("/doi"), c("/external_resources")],
      absent=["download_url"],
      no_issue_reason="Pass; no deduction."),
    q(17, "Accessibility (Access Mechanism)",
      "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
      "numeric", 5, "Excellent (platform, login, policy)",
      "Platform FAIRhub (Azure-hosted), login through a verified ID system, agreement to T2D-only research use and the license (a signed agreement tier); controlled-access data governed separately by a Data Access Committee; distribution formats listed.",
      "Access tier (registration with verified ID + license agreement) is stated without implying unrestricted access. No direct download_url.",
      cited=[c("/data_governance/access_review_process", "agreeing to the license terms"),
             c("/third_party_sharing/0/description", "available to the public for download upon agreement with a license"),
             c("/distribution_formats")],
      absent=["download_url"],
      considered=["/license_and_use_terms"],
      pred="shared_dataset", no_issue_reason="Maximum score; no deduction."),
    q(18, "Reusability, Use Guidance, and Social Impact",
      "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis with risk identification and mitigation strategies.",
      "numeric", 3, "Good (license + basic use guidance)",
      "License terms and five specific prohibited uses (clinical decisions, re-identification, vendor training, reproduction, transfer) are documented; intended_uses and discouraged_uses are absent; future_use_impacts has a single entry stating no anticipated harm beyond theoretical re-identification risk, without a linked mitigation analysis.",
      "Use guidance is partial and social-impact analysis is minimal, below the 5 anchor.",
      cited=[c("/prohibited_uses/0/description", "Licensees shall not make clinical treatment decisions based on the Data."),
             c("/future_use_impacts/0/impact_details", "there is a theoretical risk of future re-identification"),
             c("/license_and_use_terms/license_terms")],
      absent=["intended_uses", "discouraged_uses"],
      counts=[("/prohibited_uses", 5), ("/future_use_impacts", 1)],
      considered=["/purposes", "/tasks", "/participant_privacy"]),
    q(19, "Data Integrity, Provenance Graph, and Quality",
      "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation.",
      "numeric", 3, "Good (version history, no full provenance graph)",
      "version_access, updates, missing_data_documentation, splits and raw_data_sources are documented, with textual lineage (raw export -> DICOM conversion -> OMOP mapping -> QC -> FAIRhub upload). No was_derived_from, parent_datasets or errata; no entity-activity-agent provenance graph.",
      "Version history and partial textual lineage meet the 3 anchor; not a full provenance graph.",
      cited=[c("/version_access/latest_version_doi"), c("/updates/update_details"),
             c("/missing_data_documentation/0/missing_data_causes"), c("/splits/0/name"),
             c("/raw_data_sources/2/source_description")],
      absent=["was_derived_from", "parent_datasets", "errata"],
      considered=["/preprocessing_strategies", "/related_datasets"]),
    q(20, "Bias Documentation and Responsible AI Alignment",
      "Documentation of known biases, limitations and potential effects on intended or foreseeable uses.",
      "numeric", 3, "Good (basic bias identification)",
      "One known bias (volunteer bias, bias_type selection_bias) and four representation limitations (English-only eligibility, imbalanced releases, urban hospital recruitment, excluded races/ethnicities); no multi-category taxonomy or fairness analysis.",
      "Basic bias identification with a single typed entry; the 5 anchor's comprehensive categorization and fairness analysis are absent.",
      cited=[c("/known_biases/0/bias_type", "selection_bias"), c("/known_limitations/0/name", "English-language eligibility requirement"),
             c("/future_use_impacts/0/impact_details")],
      counts=[("/known_biases", 1), ("/known_limitations", 4)]),
]

categories = [
    {"name": "Structural Completeness", "questions": cat1},
    {"name": "Metadata Quality & Content", "questions": cat2},
    {"name": "Technical Documentation", "questions": cat3},
    {"name": "FAIRness & Accessibility", "questions": cat4},
]
for cat in categories:
    cat["category_score"] = sum(x["score"] for x in cat["questions"] if x["score"] is not None)
    cat["category_max"] = sum(x["max_score"] for x in cat["questions"])

total = sum(cat["category_score"] for cat in categories)
max_points = sum(cat["category_max"] for cat in categories)

issues = [
    {"item_ids": ["Q1"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "description": "Top-level resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent; no variable-level dictionary is documented."},
    {"item_ids": ["Q8"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "completeness",
     "description": "at_risk_populations and data_protection_impacts are not documented (only an absence statement inside source_caveats); no HIPAA compliance flag or governance-committee contact."},
    {"item_ids": ["Q8"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "consistency",
     "description": "is_deidentified.method states no active de-identification (NoDeIdentification) while its caveat cites a Nature Metabolism statement of HIPAA Safe Harbor de-identification; also states sex/race/medication were removed. The method is unresolved."},
    {"item_ids": ["Q9"], "score_effect": "lowered", "category": "license_use_terms", "type": "consistency",
     "description": "No confidentiality classification; license text permits research, commercial and non-commercial use while consent metadata restricts public use to type 2 diabetes research (disclosed, not reconciled)."},
    {"item_ids": ["Q11"], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
     "description": "Processing strategies name REDCap and OMOP DQD but give no software versions, conversion tool names or code URLs; no labeling/annotation/imputation documentation."},
    {"item_ids": ["Q13"], "score_effect": "lowered", "category": "temporal_version", "type": "completeness",
     "description": "No errata and no explicit long-term preservation commitment; version 2.0.0 is stated to be no longer accessible despite a registered DOI, weakening durable access."},
    {"item_ids": ["Q14"], "score_effect": "lowered", "category": "attribution", "type": "completeness",
     "description": "No formal dataset citation (citation field absent); protocol papers are mentioned only in caveats without identifiers."},
    {"item_ids": ["Q18"], "score_effect": "lowered", "category": "license_use_terms", "type": "completeness",
     "description": "intended_uses and discouraged_uses absent; future_use_impacts is a single statement without a mitigation analysis."},
    {"item_ids": ["Q19"], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
     "description": "No was_derived_from or parent_datasets linkage and no entity-activity-agent provenance representation; lineage is textual only."},
    {"item_ids": ["Q20"], "score_effect": "lowered", "category": "bias_quality", "type": "completeness",
     "description": "Only one typed bias (selection/volunteer bias); no multi-category bias taxonomy or fairness analysis."},
    {"item_ids": [], "score_effect": "noted_only", "category": "source_conflict", "type": "consistency",
     "description": "Record discloses source conflicts: v3.0 About page says pilot-phase data only vs 2280 participants; pilot start July 18 vs July 19, 2023; Aaron Lee affiliation WashU vs UW; healthsheet 'first year' wording. Each is caveated with a stated preference."},
    {"item_ids": [], "score_effect": "noted_only", "category": "bias_quality", "type": "semantic_understanding",
     "description": "Realized demographic distribution of the 2280 released participants is not given (sex/race withheld from the public release); design targets only."},
    {"item_ids": [], "score_effect": "noted_only", "category": "count_size", "type": "content_accuracy",
     "description": "Per-directory file counts sum to 356,334 vs stated 356,343 (9 root files) and bytes differ by 419,614; the record documents this reconciliation itself."},
]

EXTRA = [  # (severity, fields_involved, recommendation), aligned with `issues`
    ("medium", ["resources", "parent_datasets", "variables", "regulatory_restrictions.confidentiality_level"],
     "Add a variable dictionary, top-level resources, parent dataset links and a confidentiality classification."),
    ("medium", ["at_risk_populations", "data_protection_impacts", "regulatory_restrictions"],
     "Document vulnerable-population handling and state the data protection impact position in its own field."),
    ("high", ["is_deidentified.method", "is_deidentified.source_caveats"],
     "Resolve which de-identification method applied to the public release and state it once."),
    ("medium", ["license_and_use_terms", "regulatory_restrictions.confidentiality_level"],
     "Add a confidentiality level and reconcile the license scope with the consent-based T2D-only restriction."),
    ("medium", ["preprocessing_strategies", "cleaning_strategies"],
     "Name conversion/mapping tools with versions and link code repositories."),
    ("medium", ["errata", "version_access", "updates"],
     "Add errata and an explicit preservation commitment covering earlier DOI-registered versions."),
    ("medium", ["citation"], "Add a formal dataset citation (authors/organization, title, version, DOI)."),
    ("medium", ["intended_uses", "discouraged_uses", "future_use_impacts"],
     "Document intended and discouraged uses and pair each impact with a mitigation."),
    ("low", ["was_derived_from", "parent_datasets"],
     "Add derivation links and a structured entity-activity-agent provenance description."),
    ("medium", ["known_biases"],
     "Categorize further biases (measurement, sampling, device) with a standard taxonomy and add a fairness analysis."),
    ("low", ["version_access.source_caveats", "collection_timeframes", "creators"],
     "None required; conflicts are disclosed."),
    ("low", ["sampling_strategies", "subpopulations"],
     "Report realized per-group counts where release policy allows."),
    ("low", ["total_file_count", "total_size_bytes", "file_collections"],
     "Record the size of root-level metadata files to close the byte reconciliation."),
]
assert len(EXTRA) == len(issues)
for issue, (sev, fields, rec) in zip(issues, EXTRA):
    issue.update({"severity": sev, "fields_involved": fields, "recommendation": rec})

authority_sha = sha(AUTH)
out = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": INPUT,
    "project": "AI_READI",
    "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {
        "name": MODEL,
        "evaluator_model": MODEL,
        "temperature": None,
        "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
        "evaluation_type": "semantic_llm_judge",
    },
    "overall_score": {
        "total_points": total,
        "max_points": max_points,
        "excluded_max_points": 0,
        "adjusted_max_points": max_points,
        "normalized_percentage": round(total / max_points * 100, 1),
        "fixed_percentage": round(total / max_points * 100, 1),
        "questions_not_applicable": 0,
        "excluded_item_ids": [],
    },
    "categories": categories,
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "Rich, source-caveated record: conflicts between sources are disclosed with an explicit preference rather than silently resolved.",
            "Strongest areas: collection protocol, interoperability standards per modality, access mechanism and funding/attribution identifiers.",
            "Weakest areas: formal dataset citation, provenance graph, confidentiality classification, bias taxonomy and social-impact analysis.",
            "Temporal ordering is consistent: IRB approval 2022-12-20 precedes collection (2023-07-18/19 to 2025-05-01), which precedes v3.0.0 issue 2025-11-17.",
        ],
        "consistency_checks": {"passed": 5, "failed": 2, "warnings": 2},
        "correctness_validations": {
            "doi_format": "valid (10.60775/fairhub.3; FAIRhub DataCite prefix; related versions fairhub.1/.2 consistent)",
            "grant_number_format": "valid (OT2OD032644, P30DK035816, UL1TR003096 match NIH patterns)",
            "rrid_format": "not_applicable (no RRIDs present)",
            "url_validity": "valid structure (fairhub.io, docs.aireadi.org, aireadi.org, zenodo.org, github.com, clinicaltrials.gov)",
        },
    },
    "applicability_context": {},
    "evaluation_scope": {
        "policy": "single_dataset",
        "units": [{"path": "#", "id": "doi:10.60775/fairhub.3"}],
        "collection_metadata_inherited": False,
    },
    "metadata": {
        "instrument_sha256": sha(AGENT),
        "evidence_authority_sha256": authority_sha,
        "rubric_sha256": sha(RUBRIC),
        "input_sha256": sha(INPUT),
        "context_sha256": context_digest({}),
    },
}
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
Path(OUT).write_text(json.dumps(out, indent=2) + "\n")
print(OUT, total, max_points)
