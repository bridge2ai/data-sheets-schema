#!/usr/bin/env python3
"""Write the rubric20-semantic v3 evaluation of one CHORUS D4D record.

Purpose: serialize the judgements made by a conversational rubric20-semantic
(general context instrument v3) evaluation of
data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CHORUS_d4d.yaml
Inputs: that D4D record, data/rubric/rubric20.txt,
data/rubric/semantic_evidence_authority_v3.json, .claude/agents/d4d-rubric20-semantic.md
(hashed only). No caller applicability context: empty context.
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep2_evaluation.json
Evaluator: claude-opus-5-5 (Claude Code session). Date: 2026-11-22.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest  # noqa: E402

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CHORUS_d4d.yaml"
OUT = "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep2_evaluation.json"
MODEL = "claude-opus-5-5"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


ALWAYS = "This item applies to every dataset"


def unknown(pred):
    return f"{pred}: not declared by the caller (no applicability context supplied); unknown, retained in the denominator"


Q = []  # (category index, dict)


def q(cat, id_, name, desc, stype, score, maxs, label, evidence, note, sem,
      status_ev, cited=(), absent=(), counts=(), considered=(), no_issue=None):
    applicable_status = "applicable" if status_ev == ALWAYS else "unknown"
    row = {
        "path": "#", "score": score, "evidence": evidence,
        "cited": [dict(c) for c in cited],
        "absent": [{"path": a} for a in absent],
        "counts": [{"path": p, "claimed": n} for p, n in counts],
        "considered": list(considered),
    }
    d = {
        "id": id_, "name": name, "description": desc, "score_type": stype,
        "score": score, "max_score": maxs, "score_label": label,
        "evidence": evidence, "quality_note": note, "semantic_analysis": sem,
        "applicable": True, "applicability_status": applicable_status,
        "applicability_evidence": status_ev, "unit_scores": [row],
    }
    if no_issue:
        d["no_issue_reason"] = no_issue
    Q.append((cat, d))


# ---------------- Category 1 ----------------
q(0, 1, "Field Completeness",
  "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
  "numeric", 3, 5, "Good (~64% populated)",
  "Populated: id, title, description, keywords, license_and_use_terms, page, creators, purposes, instances (9 of 14). Absent: doi, resources, parent_datasets, variables, regulatory_restrictions.confidentiality_level.",
  "9/14 = 64% of listed fields, nearest the ~70% band; no DOI, no variable-level metadata and no confidentiality classification.",
  "license_and_use_terms is populated but names no license (a signed licensing agreement for a training program), so its semantic contribution is partial.",
  ALWAYS,
  cited=[{"path": "id", "quote": "https://chorus4ai.org/"}, {"path": "title", "quote": "CHoRUS Dataset"},
         {"path": "page"}, {"path": "description"}, {"path": "keywords"},
         {"path": "license_and_use_terms"}, {"path": "creators"}, {"path": "purposes"}, {"path": "instances"}],
  absent=["doi", "resources", "parent_datasets", "variables", "regulatory_restrictions"])

q(0, 2, "Entry Length Adequacy",
  "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
  "numeric", 5, 5, "Excellent (>200 chars)",
  "description is a multi-paragraph narrative (~2,000 chars) covering modalities, counts and plans; both purposes entries have descriptions >200 chars quoting the grant abstract and GitHub overview.",
  "Narrative fields are long and substantive, with source attribution.",
  "Content matches the purpose of the fields; planned versus achieved states are distinguished.",
  ALWAYS,
  cited=[{"path": "description", "quote": "multicenter, multimodal, high-resolution clinical care dataset"},
         {"path": "/purposes/0/description", "quote": "develop a publicly available, AI-ready critical care dataset"}],
  no_issue=None)

q(0, 3, "Keyword Diversity",
  "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply additional topic evidence where documented; no named study or disease count is presumed.",
  "numeric", 3, 5, "Good (3-7 keywords)",
  "keywords lists 7 distinct terms: Critical Care, Critical Illness, Electroencephalography, Electronic Health Record, Machine Learning, social health determinants, AI for Clinical Care.",
  "7 keywords falls in the 3-7 band; modality terms such as imaging/DICOM, waveform/telemetry, ICU/NICU/PICU or OMOP are not keywords.",
  "Keywords are relevant and partly MeSH-like but casing is inconsistent and modalities described elsewhere are not represented.",
  ALWAYS,
  cited=[{"path": "keywords"}], counts=[("keywords", 7)])

q(0, 4, "File Enumeration and Type Variety",
  "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in separate linked resources. Examine every distribution; modality breadth is distinct from suitability for machine learning.",
  "numeric", 3, 5, "Good (2-3 file types)",
  "distribution_formats has one entry, 'Cloud enclave' (an access route, not a file type). Subsets declare DICOM, WFDB and EDF+ (with Persyst) data standards and OMOP CDM for structured EHR. file_collections and total_file_count are absent.",
  "Three file-format standards (DICOM, WFDB, EDF+) are identifiable from subset standards; OMOP CDM is a data model rather than a file format. No file enumeration or counts.",
  "distribution_formats is semantically misused for an access environment rather than a format; file types must be inferred from subset conforms_to_standard values.",
  ALWAYS,
  cited=[{"path": "distribution_formats"}, {"path": "/distribution_formats/0/name", "quote": "Cloud enclave"},
         {"path": "conforms_to_standard"}, {"path": "/subsets/4/conforms_to", "quote": "EDF+ and Persyst"},
         {"path": "subsets"}],
  absent=["file_collections", "total_file_count"],
  counts=[("distribution_formats", 1)])

q(0, 5, "Data File Size Availability",
  "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
  "pass_fail", 1, 1, "Pass",
  "instances[0].counts = 50000 patient admissions; description also reports 1.6 billion rows of EHR OMOP data and 23 Tb of waveform data. total_size_bytes and file_collections absent.",
  "Numeric instance count present.",
  "The 50,000 count is reconciled with the webinar's 'over 45K' figure in source_caveats. '23 Tb' is ambiguous (terabits vs terabytes) and is not structured byte metadata.",
  ALWAYS,
  cited=[{"path": "/instances/0/counts"}, {"path": "description", "quote": "23 Tb of waveform data"}],
  absent=["total_size_bytes"],
  no_issue=None)

# ---------------- Category 2 ----------------
q(1, 6, "Dataset Identification Metadata",
  "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or repository).",
  "pass_fail", 1, 1, "Pass (URL only)",
  "id and page are https://chorus4ai.org/ (project website). doi and publisher are absent; the hosting enclave is unnamed.",
  "Passes on a stable project URL used as identifier; no DOI and no hosting platform/publisher, so identification is weak.",
  "The project website carries a banner that it is under review for modification (source_caveats), which weakens its persistence as an identifier.",
  ALWAYS,
  cited=[{"path": "id", "quote": "https://chorus4ai.org/"}, {"path": "page"}],
  absent=["doi", "publisher"])

q(1, 7, "Funding and Acknowledgements Completeness",
  "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
  "numeric", 5, 5, "Excellent",
  "funders: NIH with grant 'Bridge2AI: Patient-Focused Collaborative Hospital Repository Uniting Standards (CHoRUS) for Equitable AI', grant_number OT2OD032701, award amount, project period 2022-09-01 to 2026-11-30. Six creators each with an institutional affiliation (MGH, University of Florida, UTHealth Houston, Tufts University).",
  "Funder, grant number, project period and creator affiliations all documented.",
  "OT2OD032701 matches the NIH activity/IC/serial pattern (OT2 + OD + 6 digits); 1OT2OD032701-01 is a consistent full project number. Award amount lacks a currency unit. Creator roles are inferred from a webinar leadership slide rather than dataset authorship.",
  ALWAYS,
  cited=[{"path": "/funders/0/grants/0/grant_number", "quote": "OT2OD032701"}, {"path": "funders"},
         {"path": "creators"}, {"path": "/creators/0/affiliations/0/name", "quote": "Massachusetts General Hospital"}],
  counts=[("creators", 6)])

q(1, 8, "Ethical and Privacy Declarations",
  "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable.",
  "numeric", 3, 5, "Basic (partial)",
  "participant_privacy records a planned re-identification limitation and imaging de-identification 'in process'; data_governance mentions community ethics focus groups. ethical_reviews, human_subject_research, is_deidentified, informed_consent, participant_compensation, at_risk_populations, data_protection_impacts and regulatory_restrictions are all absent.",
  "Some privacy content exists, so the 0 anchor ('no ethics fields') does not hold, but even the 3 anchor (IRB + deidentification) is only partially met: no IRB/ethics review and only planned or in-process de-identification. Scored 3 as the nearest anchor; this is a generous placement.",
  "Patient-level ICU, PICU and NICU EHR, notes, imaging and waveform data are human-subjects data involving minors/neonates, yet no ethics review, consent or waiver, HIPAA status or at-risk population declaration is given — a significant cross-field consistency failure.",
  unknown("human_subjects"),
  cited=[{"path": "participant_privacy"}, {"path": "/participant_privacy/0/description", "quote": "de-identification of imaging was in process for a larger cohort"},
         {"path": "/data_governance/description", "quote": "community-facing ethics focus groups"}],
  absent=["ethical_reviews", "human_subject_research", "is_deidentified", "informed_consent",
          "participant_compensation", "at_risk_populations", "data_protection_impacts", "regulatory_restrictions"])

q(1, 9, "Access Requirements and Governance Documentation",
  "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts.",
  "numeric", 3, 5, "License/terms only",
  "license_and_use_terms: participants must sign a licensing agreement in the registration form. data_governance.access_review_process: controlled access, registration (name, email, institution), .edu email, access-request contacts. ip_restrictions, regulatory_restrictions (confidentiality_level, hipaa_compliant, governance_committee_contact) and data_protection_impacts are absent.",
  "Access tier (registration + signed agreement, controlled access) is described, but there is no confidentiality classification, IP or regulatory documentation, so the 5 anchor is not met.",
  "The record correctly declines to apply the GitHub MIT license to the dataset. Terms described are scoped to the AIM-AHEAD training program; general research access terms are not stated.",
  ALWAYS,
  cited=[{"path": "/license_and_use_terms/license_terms", "quote": "must sign a licensing agreement"},
         {"path": "/data_governance/access_review_process", "quote": "Controlled access (AIM-AHEAD webinar)."},
         {"path": "data_governance"}],
  absent=["ip_restrictions", "regulatory_restrictions", "data_protection_impacts"])

q(1, 10, "Interoperability, Standardization, and Cross-Platform Integration",
  "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures.",
  "numeric", 5, 5, "Excellent",
  "conforms_to_standard: OMOP_CDM, DICOM, WFDB; subsets map each modality to its standard (OMOP, DICOM, WFDB, EDF+); preprocessing_strategies describe standardization to OMOP CDM and validated semantic mappings to international standards (chorus-mapping repository with SOP).",
  "Standard formats, a common data model and a documented harmonization/mapping capability across 14 sites are present.",
  "Standards are declared as bare tokens without versions or vocabularies, 'Persyst' is a proprietary format, distribution_formats names an enclave rather than a format, and conforms_to_schema, related_datasets and external_resources are absent; these are noted but do not drop the content below the 5 anchor.",
  unknown("shared_dataset"),
  cited=[{"path": "conforms_to_standard"}, {"path": "/subsets/0/conforms_to_standard"},
         {"path": "/preprocessing_strategies/2/preprocessing_details", "quote": "validated semantic mappings"},
         {"path": "/preprocessing_strategies/0/preprocessing_details", "quote": "OMOP Common Data Model"}],
  absent=["conforms_to_schema", "related_datasets", "external_resources"],
  considered=["distribution_formats", "/subsets/4/conforms_to"])

# ---------------- Category 3 ----------------
q(2, 11, "Tool and Software Transparency",
  "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs.",
  "numeric", 3, 5, "Partial",
  "preprocessing_strategies: OMOP standardization, clinical note extraction/tokenization with the OHNLP toolkit, semantic mapping (chorus-mapping repository). labeling_strategies: planned visualization/annotation environment. cleaning_strategies, machine_annotation_tools, annotation_analyses, imputation_protocols, missing_data_documentation absent.",
  "Strategies and one named tool are listed, but there are no software versions or URLs and no cleaning/imputation/missing-data documentation.",
  "Labeling is correctly marked as planned rather than performed; repository names are given without links.",
  unknown("data_processing"),
  cited=[{"path": "preprocessing_strategies"}, {"path": "/preprocessing_strategies/1/preprocessing_details", "quote": "OHNLP toolkit"},
         {"path": "labeling_strategies"}],
  absent=["cleaning_strategies", "machine_annotation_tools", "annotation_analyses", "imputation_protocols", "missing_data_documentation"])

q(2, 12, "Collection Protocol Clarity",
  "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
  "numeric", 3, 5, "Partial",
  "collection_mechanisms: retrospective multicenter collection across 14 hospitals; site extraction under SOPs. raw_data_sources: PACS, bedside monitors and gateway/middleware, hospital EEG database. acquisition_methods, data_collectors and collection_timeframes are absent.",
  "Mechanism and sources are described, but contributing sites are not named, no collector roles are given, and no clinical encounter date range is stated.",
  "Retrospective design is coherent with an EHR-derived dataset; the absence of any patient-encounter timeframe limits temporal interpretation.",
  unknown("data_collection"),
  cited=[{"path": "collection_mechanisms"}, {"path": "/collection_mechanisms/0/description", "quote": "retrospective data collection"},
         {"path": "raw_data_sources"}],
  absent=["acquisition_methods", "data_collectors", "collection_timeframes"],
  counts=[("raw_data_sources", 3)])

q(2, 13, "Version History, Maintenance, and Sustainability",
  "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access.",
  "numeric", 0, 5, "Absent",
  "updates distinguishes the current released dataset (50,000 admissions) from an anticipated final dataset (100,000) and notes in-process imaging de-identification and EEG extraction. version, version_access, errata, maintainers, doi and publisher are absent.",
  "No version identifier, no persistent ID, no maintainer and no preservation/sustainability plan; the 3 anchor (version number + access + persistent ID) is not met.",
  "The grant period ends 2026-11-30 and the website banner states the repository is under review for modification, which makes the missing sustainability plan material.",
  unknown("shared_dataset"),
  cited=[{"path": "/updates/update_details", "quote": "anticipated final dataset"}],
  absent=["version", "version_access", "errata", "maintainers", "doi", "publisher"],
  considered=["source_caveats", "notes"])

q(2, 14, "Associated Publications",
  "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources.",
  "numeric", 3, 5, "One reference, no formal citation",
  "citation, external_resources and doi are absent. The record names its sources (NIH RePORTER award OT2OD032701, an AIM-AHEAD webinar of September 2025, the CHoRUS GitHub organization) in narrative text without links, and gives the project website as page.",
  "At least one identifiable resource (project website / NIH award record) is documented, but there is no formal dataset citation and no linked publications, so 5 is not met.",
  "Sources are attributed inline but not as resolvable references; the GitHub organization and webinar lack URLs.",
  ALWAYS,
  cited=[{"path": "page"}, {"path": "/funders/0/grants/0/description", "quote": "NIH RePORTER lists project number 1OT2OD032701-01"}],
  absent=["citation", "external_resources", "doi"])

q(2, 15, "Human Subject Representation",
  "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups.",
  "numeric", 3, 5, "General human data",
  "instances: 50,000 patient admissions from ICU, PICU and NICU across 14 hospitals; sampling_strategies records planned balanced/diverse sampling. subpopulations, at_risk_populations and missing_data_documentation absent; demographics are listed as a data type but no distribution is given.",
  "Population is characterized only at the care-setting level; no age/sex/race distributions, inclusion/exclusion criteria or subgroup counts.",
  "Pediatric and neonatal units imply vulnerable populations, yet at_risk_populations is absent.",
  unknown("human_subjects"),
  cited=[{"path": "/instances/0/description", "quote": "50,000 patient admissions from ICU, PICU, and NICU"},
         {"path": "sampling_strategies"}],
  absent=["subpopulations", "at_risk_populations", "missing_data_documentation"],
  considered=["subsets"])

# ---------------- Category 4 ----------------
q(3, 16, "Findability (Persistent Links)",
  "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
  "pass_fail", 1, 1, "Pass",
  "page and id: https://chorus4ai.org/. download_url, external_resources and doi absent.",
  "One well-formed external URL on a plausible project domain; no DOI or download link.",
  "URL syntax is valid; not resolved during evaluation.",
  ALWAYS,
  cited=[{"path": "page", "quote": "https://chorus4ai.org/"}],
  absent=["download_url", "external_resources", "doi"])

q(3, 17, "Accessibility (Access Mechanism)",
  "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
  "numeric", 3, 5, "Partially described",
  "Access is controlled, via a cloud enclave; for the AIM-AHEAD training program participants register (name, email, institution), need a .edu email, sign a licensing agreement, and are emailed when access and compute are provisioned; access-request contacts are listed. download_url absent; enclave platform unnamed.",
  "Authorization steps (registration + signed agreement) are stated without implying open access, but the platform is unnamed and the route documented is a training-program route; a general researcher access path is not given.",
  "Access tier is correctly characterized as controlled/DUA-like rather than public, consistent with the grant's 'publicly available' goal being recorded as a goal.",
  unknown("shared_dataset"),
  cited=[{"path": "/data_governance/access_review_process", "quote": "participants fill out a registration form with name, email, and institution"},
         {"path": "distribution_formats"}, {"path": "license_and_use_terms"}],
  absent=["download_url"])

q(3, 18, "Reusability, Use Guidance, and Social Impact",
  "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis.",
  "numeric", 3, 5, "License terms + basic guidance",
  "license_and_use_terms records a signed licensing agreement (no license named). tasks (characterizing illness, predicting complications, measuring treatment response), purposes and existing_uses give basic use guidance. intended_uses, prohibited_uses, discouraged_uses and future_use_impacts are absent.",
  "Basic use guidance via tasks/purposes; no prohibited or discouraged uses and no social impact analysis or mitigations.",
  "Use guidance is derived from grant aims; the agreement's actual terms are not summarized.",
  ALWAYS,
  cited=[{"path": "license_and_use_terms"}, {"path": "tasks"}, {"path": "existing_uses"}],
  absent=["intended_uses", "prohibited_uses", "discouraged_uses", "future_use_impacts"],
  considered=["purposes"])

q(3, 19, "Data Integrity, Provenance Graph, and Quality",
  "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation.",
  "numeric", 3, 5, "Partial lineage, no graph",
  "raw_data_sources (PACS, bedside monitors, EEG database), preprocessing steps (OMOP standardization, OHNLP tokenization), updates (current vs anticipated release) and a planned holdout split are documented. version_access, errata, was_derived_from, parent_datasets and missing_data_documentation are absent.",
  "Textual source-to-processing lineage and update notes exist, but no entity-activity-agent provenance graph or derivation links.",
  "The holdout split is correctly labeled as planned. Extensive source_caveats document source conflicts, a provenance strength not captured by these fields.",
  ALWAYS,
  cited=[{"path": "raw_data_sources"}, {"path": "updates"}, {"path": "splits"},
         {"path": "/splits/0/split_details", "quote": "holdout test set"}],
  absent=["version_access", "errata", "was_derived_from", "parent_datasets", "missing_data_documentation"],
  considered=["source_caveats", "preprocessing_strategies"])

q(3, 20, "Bias Documentation and Responsible AI Alignment",
  "Documentation of known biases, limitations and potential effects on intended or foreseeable uses.",
  "numeric", 0, 5, "Absent",
  "known_biases and future_use_impacts are absent. Diversity and balanced sampling appear only as goals (purposes, sampling_strategies); source_caveats address source discrepancies, not dataset bias.",
  "No bias identification for a multi-site ICU dataset (site selection, academic-center bias, pediatric/adult mix, missingness).",
  "The grant title references 'Equitable AI' and the purposes emphasize diversity, yet no bias or limitation analysis is documented.",
  ALWAYS,
  absent=["known_biases", "future_use_impacts"],
  considered=["sampling_strategies", "purposes", "source_caveats"])

# ---------------- Issues ----------------
issues = [
    {"type": "consistency", "category": "consent_ethics", "severity": "high", "score_effect": "lowered",
     "item_ids": ["Q8"],
     "description": "Patient-level ICU/PICU/NICU clinical data are described, but ethical_reviews, human_subject_research, informed_consent (or waiver) and is_deidentified are absent; only a planned re-identification limitation and in-process imaging de-identification are recorded.",
     "fields_involved": ["ethical_reviews", "human_subject_research", "informed_consent", "is_deidentified", "participant_privacy", "instances"],
     "recommendation": "Document IRB/ethics review (or reliance agreement), consent or waiver basis, and the de-identification standard applied to each released modality."},
    {"type": "completeness", "category": "privacy_regulatory", "severity": "high", "score_effect": "lowered",
     "item_ids": ["Q8", "Q9", "Q15"],
     "description": "No regulatory_restrictions (HIPAA status, confidentiality_level, governance contact), data_protection_impacts or at_risk_populations, despite pediatric and neonatal patients and controlled-access EHR data.",
     "fields_involved": ["regulatory_restrictions", "data_protection_impacts", "at_risk_populations"],
     "recommendation": "Add confidentiality classification, HIPAA/limited-data-set status, governance committee contact and a vulnerable-population statement for PICU/NICU patients."},
    {"type": "completeness", "category": "persistent_identifier", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["Q1", "Q13", "Q14"],
     "description": "No DOI, publisher, version identifier, maintainer or formal dataset citation; the only identifier is the project website, which carries a banner that it is under review for modification.",
     "fields_involved": ["doi", "publisher", "version", "maintainers", "citation", "page"],
     "recommendation": "Assign a versioned persistent identifier, name the hosting repository/enclave and maintainers, and provide a formal dataset citation."},
    {"type": "completeness", "category": "temporal_version", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["Q13", "Q19"],
     "description": "Release state is described only narratively (current 50,000 vs anticipated 100,000 admissions); no version labels, version_access, errata or sustainability plan, although the grant period ends 2026-11-30.",
     "fields_involved": ["updates", "version", "version_access", "errata", "maintainers"],
     "recommendation": "Record release versions with dates, a change log and a post-award preservation commitment."},
    {"type": "completeness", "category": "bias_quality", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["Q20", "Q18"],
     "description": "known_biases, future_use_impacts, prohibited_uses and discouraged_uses are absent; diversity is stated only as a goal.",
     "fields_involved": ["known_biases", "future_use_impacts", "prohibited_uses", "discouraged_uses"],
     "recommendation": "Document site/population selection biases, missingness patterns and foreseeable misuse with mitigations."},
    {"type": "semantic_understanding", "category": "format_access", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["Q4", "Q17"],
     "description": "distribution_formats contains 'Cloud enclave', an access environment rather than a file format; the enclave platform is unnamed and no download_url or file enumeration is given.",
     "fields_involved": ["distribution_formats", "download_url", "file_collections"],
     "recommendation": "List actual file formats per modality in distribution_formats and name the enclave platform and its login/authorization path."},
    {"type": "completeness", "category": "processing_provenance", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["Q11", "Q12"],
     "description": "Processing and collection are described without software versions/URLs, cleaning or missing-data handling, named contributing sites, or a patient-encounter timeframe.",
     "fields_involved": ["preprocessing_strategies", "cleaning_strategies", "collection_timeframes", "data_collectors", "acquisition_methods"],
     "recommendation": "Add tool versions and repository links, cleaning/QC steps, the list of contributing sites and the admission date range."},
    {"type": "completeness", "category": "variables_metadata", "severity": "low", "score_effect": "lowered",
     "item_ids": ["Q1", "Q3", "Q15"],
     "description": "No variables, subpopulations or demographic distributions; keywords omit imaging, waveform, OMOP and ICU/PICU/NICU terms.",
     "fields_involved": ["variables", "subpopulations", "keywords"],
     "recommendation": "Add variable-level metadata, demographic breakdowns by care unit and modality keywords."},
    {"type": "completeness", "category": "license_use_terms", "severity": "low", "score_effect": "lowered",
     "item_ids": ["Q9", "Q18"],
     "description": "license_and_use_terms describes only that training-program participants sign a licensing agreement; no dataset license or summary of agreement terms is provided, and general (non-training) access terms are not stated.",
     "fields_involved": ["license_and_use_terms", "data_governance"],
     "recommendation": "Name the data use agreement and summarize its permitted and prohibited uses for all access routes."},
    {"type": "correctness", "category": "attribution", "severity": "low", "score_effect": "noted_only", "item_ids": [],
     "description": "The contact email domain 'mgh.havard.edu' (sic) is reproduced from the website and flagged in source_caveats; '23 Tb' is ambiguous between terabits and terabytes; the award amount lacks a currency unit.",
     "fields_involved": ["notes", "description", "funders"],
     "recommendation": "Confirm the contact address and use unambiguous units (bytes, USD)."},
    {"type": "content_accuracy", "category": "count_size", "severity": "low", "score_effect": "noted_only", "item_ids": [],
     "description": "Counts are internally reconciled: 50,000 admissions (website) vs 'over 45K' (August 2025 webinar) are treated as compatible, and 1000 images vs 7,642 radiology admissions are noted as different units. No conflict detected.",
     "fields_involved": ["instances", "source_caveats"],
     "recommendation": "None required; keep explicit units for each count."},
]

# link Q2, Q5/6/7/10/16 at max: fine. Q6 is pass but noted.
issues.append({"type": "completeness", "category": "persistent_identifier", "severity": "low", "score_effect": "noted_only", "item_ids": [],
               "description": "Q6/Q16 pass only on the project website URL; no DOI, RRID or named hosting platform.",
               "fields_involved": ["id", "page", "doi", "publisher"],
               "recommendation": "Register a DOI on a named repository landing page."})

CAT_NAMES = ["Structural Completeness", "Metadata Quality & Content", "Technical Documentation", "FAIRness & Accessibility"]
cats = []
for i, nm in enumerate(CAT_NAMES):
    qs = [d for c, d in Q if c == i]
    cats.append({"name": nm, "questions": qs,
                 "category_score": sum(d["score"] for d in qs if d["score"] is not None),
                 "category_max": sum(d["max_score"] for d in qs)})
total = sum(c["category_score"] for c in cats)
maxp = 88
assert sum(c["category_max"] for c in cats) == maxp

ctx = {}
out = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": INPUT,
    "project": "CHORUS",
    "method": "claudecode_agent",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {"name": MODEL, "evaluator_model": MODEL, "temperature": None,
              "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
              "evaluation_type": "semantic_llm_judge"},
    "overall_score": {"total_points": total, "max_points": maxp, "excluded_max_points": 0,
                      "adjusted_max_points": maxp,
                      "normalized_percentage": round(total / maxp * 100, 2),
                      "fixed_percentage": round(total / maxp * 100, 2),
                      "questions_not_applicable": 0, "excluded_item_ids": []},
    "categories": cats,
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "Record carefully separates planned (grant abstract) from achieved states and documents source conflicts in source_caveats.",
            "Strong funding/creator attribution and modality-to-standard mapping (OMOP CDM, DICOM, WFDB, EDF+).",
            "Ethics, regulatory, versioning and bias documentation are the dominant gaps for a controlled-access clinical dataset including pediatric and neonatal patients.",
            "All conditional items were scored because no caller applicability context was supplied (predicates unknown).",
        ],
        "consistency_checks": {"passed": 4, "failed": 3, "warnings": 3},
        "correctness_validations": {
            "doi_format": "not_applicable: no DOI present",
            "grant_number_format": "valid: OT2OD032701 matches NIH activity (OT2) + IC (OD) + 6-digit serial; full number 1OT2OD032701-01 consistent",
            "rrid_format": "not_applicable: no RRIDs present",
            "url_validity": "valid syntax: https://chorus4ai.org/ (not resolved); contact email domain 'mgh.havard.edu' appears misspelled (flagged by the record itself)",
        },
    },
    "assessment": {
        "strengths": ["Detailed description and purposes", "Grant number and creator affiliations", "Modality-level standards", "Explicit access steps for the training program", "Source caveats reconciling counts"],
        "weaknesses": ["No ethics review, consent, de-identification status or regulatory classification", "No DOI, version or sustainability plan", "No bias or social impact documentation", "No file-level enumeration"],
        "recommendations": ["Add ethical_reviews, informed_consent, is_deidentified and regulatory_restrictions", "Assign a versioned DOI with maintainers", "Document known_biases and prohibited uses", "Enumerate file formats and sizes per modality"],
    },
    "applicability_context": ctx,
    "evaluation_scope": {"policy": "single_dataset",
                         "units": [{"path": "#", "id": "https://chorus4ai.org/"}],
                         "collection_metadata_inherited": False},
    "metadata": {
        "evaluator_id": MODEL,
        "instrument_sha256": sha(".claude/agents/d4d-rubric20-semantic.md"),
        "evidence_authority_sha256": sha("data/rubric/semantic_evidence_authority_v3.json"),
        "rubric_sha256": sha("data/rubric/rubric20.txt"),
        "input_sha256": sha(INPUT),
        "context_sha256": context_digest(ctx),
    },
}
p = ROOT / OUT
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(OUT, total, maxp)
