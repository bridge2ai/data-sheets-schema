#!/usr/bin/env python3
"""Write the rubric20-semantic v3 evaluation of one AI_READI D4D record.

Purpose: serialize the judgements of a manual (conversational) rubric20-semantic
evaluation, with digests computed from the actual bytes and quotes/counts
self-checked against the evaluated record before writing.
Input:  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/AI_READI_d4d.yaml
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep1_evaluation.json
Instrument: .claude/agents/d4d-rubric20-semantic.md (general context instrument v3).
Date: 2026-11-22. Evaluator runtime model: claude-opus-5-5.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest, field_values, load_document  # noqa: E402

INPUT = ROOT / "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/AI_READI_d4d.yaml"
OUTPUT = ROOT / "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep1_evaluation.json"
AGENT = ROOT / ".claude/agents/d4d-rubric20-semantic.md"
RUBRIC = ROOT / "data/rubric/rubric20.txt"
AUTHORITY = ROOT / "data/rubric/semantic_evidence_authority_v3.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


DOC, INPUT_SHA = load_document(INPUT)


def resolve(path: str):
    node = DOC
    parts = path[1:].split("/") if path.startswith("/") else path.split(".")
    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            node = node[int(part)]
        else:
            node = node[part]
    return node


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def c(path, quote=None):
    value = resolve(path)
    assert value not in (None, "", [], {}), path
    if quote is not None:
        assert norm(quote) in norm(value), (path, quote)
        return {"path": path, "quote": quote}
    return {"path": path}


def a(path):
    found = [v for _, v in field_values(DOC, path) if v not in (None, "", [], {})]
    assert not found, f"{path} is populated"
    return {"path": path}


def n(path, claimed):
    actual = len(resolve(path))
    assert actual == claimed, (path, actual, claimed)
    return {"path": path, "claimed": claimed}


ALWAYS = ("applicable", "This item applies to every dataset")


def unknown(pred):
    return ("unknown", f"{pred}: not declared; retained in the denominator")


Q = []


def q(qid, name, desc, stype, score, maxs, label, evidence, note, appl, cited=(), absent=(), counts=(),
      considered=(), no_issue_reason=None):
    status, appl_ev = appl
    item = {
        "id": qid, "name": name, "description": desc, "score_type": stype, "score": score,
        "max_score": maxs, "score_label": label, "evidence": evidence, "quality_note": note,
        "applicable": True, "applicability_status": status, "applicability_evidence": appl_ev,
        "unit_scores": [{"path": "#", "score": score, "evidence": evidence, "cited": list(cited),
                         "absent": list(absent), "counts": list(counts), "considered": list(considered)}],
    }
    if no_issue_reason:
        item["no_issue_reason"] = no_issue_reason
    Q.append(item)


# ---------------- Category 1 ----------------
q(1, "Field Completeness",
  "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
  "numeric", 3, 5, "Good (~70% populated)",
  "10 of 14 listed fields populated (id, title, description, keywords, license_and_use_terms, doi, page, creators, purposes, instances); top-level resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent (71%).",
  "71% of the listed fields carry meaningful content, which matches the ~70% band, not >=90%. No variable-level dictionary is given despite a multi-domain tabular release.",
  ALWAYS,
  cited=[c("id", "doi:10.60775/fairhub.3"), c("title", "Flagship Dataset of Type 2 Diabetes from the AI-READI Project"),
         c("description"), c("keywords"), c("license_and_use_terms"), c("doi", "10.60775/fairhub.3"),
         c("page", "https://fairhub.io/datasets/3"), c("creators"), c("purposes"), c("/instances/0/counts")],
  absent=[a("resources"), a("parent_datasets"), a("variables"), a("regulatory_restrictions.confidentiality_level")],
  counts=[n("creators", 17), n("purposes", 2)],
  considered=["regulatory_restrictions"])

q(2, "Entry Length Adequacy",
  "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
  "numeric", 5, 5, "Excellent (>200 chars)",
  "description is a multi-paragraph narrative (>1,500 chars) covering version, sites, participants, modalities and CDS structure; both purposes responses exceed 200 chars.",
  "Narrative fields are long and substantive, specific to this release (v3.0.0, 2280 participants, July 2023-May 2025).",
  ALWAYS,
  cited=[c("description", "this version contains data from 2280 participants collected between July 19, 2023 and May 1, 2025"),
         c("/purposes/0/response", "The purpose for creating the dataset was to enable future generations of artificial intelligence/machine learning (AI/ML) research"),
         c("/purposes/1/response")],
  counts=[n("purposes", 2)])

q(3, "Keyword Diversity",
  "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply additional topic evidence where documented; no named study or disease count is presumed.",
  "numeric", 3, 5, "Good (3-7 keywords)",
  "keywords lists 7 distinct terms: Diabetes mellitus, Machine Learning, Artificial Intelligence, Electrocardiography, Continuous Glucose Monitoring, Retinal imaging, Eye exam.",
  "7 keywords falls in the 3-7 band. Major documented modalities (OCT/OCTA, wearable activity, environmental sensors, clinical/lab data, salutogenesis) are not represented as keywords.",
  ALWAYS,
  cited=[c("/keywords/0", "Diabetes mellitus"), c("/keywords/6", "Eye exam")],
  counts=[n("keywords", 7)])

q(4, "File Enumeration and Type Variety",
  "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in separate linked resources. Examine every distribution; modality breadth is distinct from suitability for machine learning.",
  "numeric", 5, 5, "Excellent (>3 file types)",
  "distribution_formats lists DICOM, Markdown, CSV and JSON; file_collections add TSV and TXT metadata resources across 10 collections (9 modality directories + root metadata); total_file_count 356343.",
  "More than three file types, consistent with the multimodal description (imaging, waveform, tabular, sensor). distribution_formats omits TSV and the WFDB waveform format that the file collections document (noted, not lowered).",
  ALWAYS,
  cited=[c("/distribution_formats/0/format", "DICOM"), c("/distribution_formats/2/format", "CSV"),
         c("/distribution_formats/3/format", "JSON"), c("/distribution_formats/1/format", "Markdown"),
         c("/file_collections/0/resources/0/format", "TSV"), c("/file_collections/9/resources/4/format", "TXT"),
         c("total_file_count")],
  counts=[n("distribution_formats", 4), n("file_collections", 10)])

q(5, "Data File Size Availability",
  "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
  "pass_fail", 1, 1, "Pass",
  "total_size_bytes 3815969779678; per-collection total_bytes and file_count; instances counts 2280; splits 1576/352/352; subpopulation counts.",
  "Numeric sizes and counts are present and internally consistent: per-collection file_count sums to 356334 plus 9 root metadata files = 356343; per-collection bytes sum to 3,815,969,360,064, 419,614 bytes below the total (root metadata files carry no byte counts).",
  ALWAYS,
  cited=[c("total_size_bytes"), c("/file_collections/0/total_bytes"), c("/instances/0/counts"),
         c("/splits/0/split_details", "1576 / 352 / 352 participants"), c("subpopulations")],
  counts=[n("subpopulations", 10)])

# ---------------- Category 2 ----------------
q(6, "Dataset Identification Metadata",
  "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or repository).",
  "pass_fail", 1, 1, "Pass",
  "doi 10.60775/fairhub.3, id doi:10.60775/fairhub.3, page https://fairhub.io/datasets/3, publisher https://fairhub.io/.",
  "Persistent DOI plus hosting platform (FAIRhub). DOI syntax is valid; prefix 10.60775 is FAIRhub's own DataCite prefix rather than one of the commonly cited repositories, plausible but not independently verified.",
  ALWAYS,
  cited=[c("doi", "10.60775/fairhub.3"), c("id"), c("page"), c("publisher", "https://fairhub.io/")])

q(7, "Funding and Acknowledgements Completeness",
  "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
  "numeric", 5, 5, "Excellent (funders with grants + affiliated creators)",
  "NIH Bridge2AI grant OT2OD032644 (with RePORTER project 1OT2OD032644-01), additional NIH grants P30DK035816 and UL1TR003096, Research to Prevent Blindness; 16 named PIs each with ORCID and ROR-identified affiliation plus the AI-READI Consortium.",
  "Grant numbers match NIH activity/IC/serial patterns (OT2 OD, P30 DK, UL1 TR). A source typo (OT2ODO32644) is detected and corrected with a caveat. Affiliation conflict for Aaron Lee (FAIRhub: Washington University in St. Louis; NIH RePORTER: University of Washington) is flagged but the Cecilia Lee entry carries the same unflagged affiliation (noted only).",
  ALWAYS,
  cited=[c("/funders/0/grants/0/grant_number", "OT2OD032644"), c("/funders/1/grants/0/grant_number", "P30DK035816"),
         c("/funders/1/grants/1/grant_number", "UL1TR003096"), c("/funders/2/grantor", "Research to Prevent Blindness"),
         c("/creators/1/principal_investigator/affiliation/0/name", "Washington University in St. Louis"),
         c("/creators/1/source_caveats", "lists the principal investigator as LEE, AARON with the organization UNIVERSITY OF WASHINGTON"),
         c("/funders/0/source_caveats", "OT2ODO32644")],
  counts=[n("funders", 3), n("creators", 17)])

q(8, "Ethical and Privacy Declarations",
  "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable.",
  "numeric", 3, 5, "Good (IRB + deidentification, not all protections)",
  "UW IRB STUDY00016228 with reliance agreements; involves_human_subjects true; detailed e-consent/in-person consent and withdrawal; $200 compensation; four participant_privacy entries; is_deidentified with method; NIH GDS compliance. Absent: data_protection_impacts, at_risk_populations, reidentification_risk, hipaa_compliant, governance_committee_contact.",
  "Well beyond basic, but the 5-point anchor requires all protections and data protection impacts: no DPIA field (the top-level caveat states none was conducted), no at-risk/vulnerable population statement for a 40-85 cohort, and no explicit re-identification risk assessment field. The de-identification method ('no identifiers were collected, so no active de-identification was necessary') is in tension with identifiers_removed (sex, race/ethnicity, medication removed) and with the Safe Harbor and IRB identifier statements in its own caveat.",
  unknown("human_subjects"),
  cited=[c("/ethical_reviews/0/review_details", "approval number STUDY00016228"),
         c("human_subject_research.involves_human_subjects"),
         c("/informed_consent/0/consent_documentation", "Informed consent was required before participation in any part of the protocol"),
         c("/participant_compensation/0/compensation_amount", "$200"),
         c("/participant_privacy/1/privacy_techniques", "data watermarking"),
         c("is_deidentified.method", "no identifiers were collected, so no active de-identification was necessary"),
         c("is_deidentified.identifiers_removed", "Information related to the sex and race/ethnicity of the participants as well as medication used has been removed."),
         c("is_deidentified.source_caveats", "via the Safe Harbor method"),
         c("regulatory_restrictions.other_compliance", "Genomic Data Sharing (GDS) Policy"),
         c("source_caveats", "that no data protection impact analysis has been conducted")],
  absent=[a("data_protection_impacts"), a("at_risk_populations"), a("participant_privacy.reidentification_risk"),
          a("regulatory_restrictions.hipaa_compliant"), a("regulatory_restrictions.governance_committee_contact")],
  counts=[n("participant_privacy", 4)],
  considered=["ethical_reviews", "human_subject_research", "is_deidentified", "participant_privacy",
              "participant_compensation", "informed_consent", "regulatory_restrictions.other_compliance"])

q(9, "Access Requirements and Governance Documentation",
  "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts.",
  "numeric", 5, 5, "Excellent (license + restrictions + tiered confidentiality)",
  "AI-READI Data License Agreement v2.0 (doi:10.5281/zenodo.17555036) with detailed terms (licensor, storage/BAA requirements, termination); ip_restrictions; NIH GDS compliance; public vs controlled-access tiers with listed sensitive elements; verified-ID login + self-attestation for public, DUA + committee approval for controlled.",
  "License, restrictions and a confidentiality classification (public tier vs controlled tier holding zip code, race/ethnicity, genomic data, accident reports) are all documented in substance, although the confidentiality_level field itself is not populated and no governance contact is given. The license's commercial-use grant vs the T2D-only access condition is a documented, unresolved conflict (lowers Q18).",
  ALWAYS,
  cited=[c("license_and_use_terms.name", "AI-READI Data License Agreement (Version 2.0)"),
         c("license_and_use_terms.license_terms", "The licensor is Washington University in St. Louis."),
         c("/ip_restrictions/restrictions/0", "Title to the Data and all industrial and intellectual property rights therein remain solely and exclusively with the Licensor"),
         c("regulatory_restrictions.other_compliance"),
         c("/sensitive_elements/0/sensitivity_details", "the controlled access dataset will contain data regarding racial and ethnic origins, location (5-digit zip code) and motor vehicle accident reports"),
         c("data_governance.access_review_process", "Access type for the FAIRhub release is public download with self-attestation required.")],
  absent=[a("regulatory_restrictions.confidentiality_level"), a("regulatory_restrictions.governance_committee_contact"),
          a("data_protection_impacts"), a("regulatory_restrictions.hipaa_compliant")])

q(10, "Interoperability, Standardization, and Cross-Platform Integration",
  "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures.",
  "numeric", 5, 5, "Excellent (standard formats + standards conformance + integration)",
  "conforms_to and conforms_to_standard: CDS v0.1.1, WFDB, OMOP CDM, ESDS, DICOM, Open mHealth, mapped per directory; preprocessing maps clinical data to OMOP and imaging to DICOM; OMOP DQD file supplied.",
  "Standard formats with explicit per-modality standard conformance and documented mapping procedures support integration with OMOP/DICOM tooling. No compression, related_datasets or formal conforms_to_schema reference (not decisive).",
  unknown("shared_dataset"),
  cited=[c("conforms_to", "clinical_data follows the Observational Medical Outcomes Partnership (OMOP) Common Data Model (CDM)"),
         c("conforms_to_standard"), c("/file_collections/1/resources/0/description", "OMOP CDM Data Quality Dashboard"),
         c("/preprocessing_strategies/0/preprocessing_details", "all data were mapped to standardized terminologies when possible"),
         c("distribution_formats"), c("external_resources")],
  absent=[a("conforms_to_schema"), a("file_collections.compression"), a("related_datasets")],
  counts=[n("conforms_to_standard", 6)])

# ---------------- Category 3 ----------------
q(11, "Tool and Software Transparency",
  "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs.",
  "numeric", 3, 5, "Good (strategies listed, no versions/URLs)",
  "Preprocessing (mapping to OMOP/DICOM; proprietary .fda/.sdt to DICOM, .FIT to mHealth) and cleaning (REDCap range checks, skip-pattern checks, internal PII review) are described; REDCap and OMOP DQD are named. No software versions, conversion tool names or URLs; no imputation protocol.",
  "At least one strategy and tool are listed, but the 5-point anchor needs software versions/URLs; the conversion pipeline tools are unnamed and the format-to-device attribution is explicitly left unresolved.",
  unknown("data_processing"),
  cited=[c("/preprocessing_strategies/1/preprocessing_details", "imaging exports in .fda and .sdt file formats converted to DICOM"),
         c("/preprocessing_strategies/1/source_caveats"),
         c("/cleaning_strategies/0/cleaning_details", "Clinical data outside expected min/max ranges were flagged in REDCap reports"),
         c("/cleaning_strategies/1/cleaning_details")],
  absent=[a("imputation_protocols"), a("machine_annotation_tools"), a("labeling_strategies"), a("annotation_analyses")],
  considered=["preprocessing_strategies", "cleaning_strategies", "missing_data_documentation"])

q(12, "Collection Protocol Clarity",
  "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
  "numeric", 5, 5, "Excellent (full protocol)",
  "25 collection mechanisms with named device models (Philips PageWriter TC30, Dexcom G6, Garmin Vivosmart 5, Heidelberg Spectralis, Topcon Maestro2, etc.); acquisition methods; collectors with roles and training; timeframes with dates (2023-07-19 to 2025-05-01 for v3.0.0; 10-day at-home period); raw sources (EHR, DOL records, Dexcom Clarity).",
  "Methods, collectors and timeframes are all specific. Temporal ordering is logical (IRB approval 2022-12-20, enrollment July 2023, collection cutoff 2025-05-01, release 2025-11-17); the 18 vs 19 July start-date discrepancy is documented.",
  unknown("data_collection"),
  cited=[c("/collection_mechanisms/2/mechanism_details", "Philips PageWriter TC30"),
         c("/acquisition_methods/0/acquisition_details"),
         c("/data_collectors/0/collector_details", "underwent training by the data manager at UAB and used a detailed Manual of Procedures"),
         c("/collection_timeframes/3/end_date"), c("/raw_data_sources/0/source_description")],
  counts=[n("collection_mechanisms", 25), n("data_collectors", 4), n("collection_timeframes", 5), n("raw_data_sources", 3)])

q(13, "Version History, Maintenance, and Sustainability",
  "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access.",
  "numeric", 3, 5, "Good (versions + access + PID, limited sustainability)",
  "version 3.0.0; versions_available with DOIs for 1.0.0, 2.0.0, 3.0.0; change note (Snellen acuity dropped); yearly static releases; maintainer 'AI-READI team' hosted on FAIRhub/Azure. No errata, no maintainer contact, no preservation commitment beyond the project; v2.0.0 stated as no longer accessible.",
  "Versioning is strong, but full sustainability (governance + repository + commitment) is not met: no long-term preservation or funding commitment, no contact point, and a prior DOI-identified version was withdrawn, which undermines durable access.",
  unknown("shared_dataset"),
  cited=[c("version", "3.0.0"), c("version_access.versions_available"),
         c("version_access.version_details", "its documentation and landing page state that it is no longer accessible"),
         c("updates.update_details", "new versions are released approximately once a year"),
         c("/maintainers/0/maintainer_details", "The AI-READI team will be supporting and maintaining the dataset."),
         c("doi"), c("publisher")],
  absent=[a("errata")],
  counts=[n("version_access.versions_available", 3)],
  considered=["version_access", "updates", "maintainers"])

q(14, "Associated Publications",
  "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources.",
  "numeric", 3, 5, "Good (multiple references, no formal dataset citation)",
  "8 distinct external resources (Nature Metabolism comment DOI, BMJ Open protocol DOI, Zenodo license record, docs.aireadi.org, aireadi.org, Zenodo community, GitHub, ClinicalTrials.gov NCT06002048) plus the dataset DOI; no citation field.",
  "At least two distinct references exist, but no formal citation for this dataset is given, so the 5-point condition is not met.",
  ALWAYS,
  cited=[c("/external_resources/0/external_resources/0", "https://doi.org/10.1038/s42255-024-01165-x"),
         c("/external_resources/7/external_resources/0", "https://doi.org/10.1136/bmjopen-2024-097449"),
         c("doi")],
  absent=[a("citation")],
  counts=[n("external_resources", 8)],
  considered=["external_resources"])

q(15, "Human Subject Representation",
  "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups.",
  "numeric", 5, 5, "Excellent (demographics + inclusion/exclusion)",
  "2280 participants, mean age 60.8 +/- 11.3; 10 subpopulations by race/ethnicity, sex and diabetes status with split-level counts; triple-balanced sampling with inclusion (>=40, English, consent) and exclusion (pregnancy, gestational/type 1 diabetes, >85) criteria; site recruitment priorities.",
  "Detailed and arithmetically consistent: race groups, sex groups and diabetes groups each sum to 2280, and their train/validation/test counts sum to 1576/352/352. The record notes that race/sex are withheld from the public release. at_risk_populations is not populated.",
  unknown("human_subjects"),
  cited=[c("/instances/0/notes", "Mean age of the 2280 participants is 60.8"),
         c("/subpopulations/0/distribution", "380 of 2280 participants"),
         c("/sampling_strategies/0/strategies", "Exclusion criteria: pregnancy, gestational diabetes, type 1 diabetes"),
         c("splits"), c("missing_data_documentation")],
  absent=[a("at_risk_populations")],
  counts=[n("subpopulations", 10)])

# ---------------- Category 4 ----------------
q(16, "Findability (Persistent Links)",
  "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
  "pass_fail", 1, 1, "Pass",
  "page https://fairhub.io/datasets/3, DOI 10.60775/fairhub.3, and 8 external resource URLs including DOIs.",
  "Persistent and well-formed external links are present (not live-checked).",
  ALWAYS,
  cited=[c("page"), c("doi"), c("/external_resources/2/external_resources/0", "https://docs.aireadi.org/")])

q(17, "Accessibility (Access Mechanism)",
  "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
  "numeric", 5, 5, "Excellent (platform, login, policy)",
  "FAIRhub landing page; access requires login through a verified ID system, agreement to T2D-only use and acceptance of the license (self-attestation); controlled-access tier requires a DUA and committee approval; distribution formats listed.",
  "Access tiers are distinguished correctly (verified login + license agreement for the public set; DUA/approval for controlled data) without implying unrestricted access. No direct download_url, but the platform path is clear.",
  unknown("shared_dataset"),
  cited=[c("data_governance.access_review_process", "Accessing the dataset requires logging in through a verified ID system"),
         c("license_and_use_terms.description", "the full dataset is accessible by entering into a data use agreement"),
         c("distribution_formats"), c("page")],
  absent=[a("download_url")])

q(18, "Reusability, Use Guidance, and Social Impact",
  "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis with risk identification and mitigation strategies.",
  "numeric", 3, 5, "Good (license + use guidance, limited impact analysis)",
  "License v2.0 with terms; 2 intended uses; 5 prohibited uses (clinical decisions, re-identification, third-party sharing, vendor training, reproduction); 3 future_use_impacts. No discouraged_uses; impacts carry no mitigation strategies.",
  "Use guidance is strong, but the social-impact analysis is brief (re-identification noted as theoretical, commercial products possible) with no linked mitigation, and discouraged uses are missing. The license grants research, commercial and non-commercial use while access to the public version requires T2D-only research; the record surfaces this conflict but leaves reusers without a resolved rule.",
  ALWAYS,
  cited=[c("license_and_use_terms.license_terms", "for research, commercial and non-commercial purposes"),
         c("license_and_use_terms.source_caveats", "the public version can only be used for type 2 diabetes related research"),
         c("intended_uses"), c("prohibited_uses"),
         c("/future_use_impacts/1/impact_details", "there is a theoretical risk of future re-identification")],
  absent=[a("discouraged_uses")],
  counts=[n("intended_uses", 2), n("prohibited_uses", 5), n("future_use_impacts", 3)],
  considered=["license_and_use_terms", "intended_uses", "prohibited_uses", "future_use_impacts"])

q(19, "Data Integrity, Provenance Graph, and Quality",
  "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation.",
  "numeric", 3, 5, "Good (version history, partial lineage)",
  "version_access with three DOIs, updates, splits, missing_data_documentation, raw_data_sources and raw_sources; textual lineage (site collection -> site data manager QC -> central mapping to OMOP/DICOM/mHealth -> FAIRhub). No was_derived_from, parent_datasets or errata; per-device format lineage is explicitly unresolved.",
  "Version history and partial textual lineage are present, but there is no entity-activity-agent provenance with derivation paths per modality, so the full provenance graph anchor is not met.",
  ALWAYS,
  cited=[c("version_access"), c("updates"), c("splits"), c("missing_data_documentation"), c("raw_data_sources"),
         c("/raw_sources/0/raw_data_details", "has not been mapped to standardized terminologies"),
         c("/preprocessing_strategies/1/source_caveats", "does not make explicit which imaging device or monitoring device each export format belongs to")],
  absent=[a("was_derived_from"), a("parent_datasets"), a("errata")],
  considered=["version_access", "updates", "missing_data_documentation", "splits", "raw_data_sources"])

q(20, "Bias Documentation and Responsible AI Alignment",
  "Documentation of known biases, limitations and potential effects on intended or foreseeable uses.",
  "numeric", 3, 5, "Good (basic bias identification)",
  "known_biases: volunteer bias (bias_type selection_bias) and urban/hospital-based recruitment (no type); known_limitations include English-only enrollment, unachieved group balance and missing Pacific Islander/Native American groups (one typed representativeness_limitation); splits balanced to reduce disparities.",
  "Biases are identified and relevant, but only one carries a taxonomy type and there is no fairness analysis (e.g., subgroup performance or representativeness assessment beyond design intent).",
  ALWAYS,
  cited=[c("/known_biases/0/bias_type", "selection_bias"),
         c("/known_biases/1/bias_description", "may not fully capture diverse cultural and socioeconomic backgrounds"),
         c("/known_limitations/3/limitation_type", "representativeness_limitation"),
         c("future_use_impacts")],
  counts=[n("known_biases", 2), n("known_limitations", 4)],
  considered=["known_biases", "future_use_impacts"])

# ---------------- Issues ----------------
ISSUES = [
    {"item_ids": ["Q1"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "description": "Top-level resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent; no variable dictionary for the tabular domains."},
    {"item_ids": ["Q3"], "score_effect": "lowered", "category": "other", "type": "completeness",
     "description": "Only 7 keywords; OCT/OCTA, wearables, environmental sensors, clinical/lab data and salutogenesis are not represented."},
    {"item_ids": ["Q8"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "completeness",
     "description": "No data_protection_impacts, at_risk_populations, reidentification_risk or hipaa_compliant fields; the absence of a DPIA appears only in a top-level caveat."},
    {"item_ids": ["Q8"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "consistency",
     "description": "is_deidentified.method says no identifiers were collected and no active de-identification was needed, while identifiers_removed lists removed sex/race/medication data and the caveat cites Safe Harbor de-identification and IRB-held identifiers (name, MRN, DOB, ZIP)."},
    {"item_ids": ["Q11"], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
     "description": "Processing strategies name REDCap and OMOP DQD but give no software versions, URLs or conversion tool names; no imputation protocol."},
    {"item_ids": ["Q13"], "score_effect": "lowered", "category": "temporal_version", "type": "completeness",
     "description": "No errata, maintainer contact or long-term preservation commitment; v2.0.0 is recorded as no longer accessible despite its DOI."},
    {"item_ids": ["Q14"], "score_effect": "lowered", "category": "attribution", "type": "completeness",
     "description": "No formal dataset citation (citation field absent) although title, creators, publisher and DOI are available to compose one."},
    {"item_ids": ["Q18"], "score_effect": "lowered", "category": "license_use_terms", "type": "completeness",
     "description": "discouraged_uses absent; future_use_impacts give no mitigation strategies."},
    {"item_ids": ["Q18"], "score_effect": "lowered", "category": "license_use_terms", "type": "consistency",
     "description": "License grants research, commercial and non-commercial use, while public-version access requires T2D-only research use; the conflict is documented in a caveat but unresolved."},
    {"item_ids": ["Q19"], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
     "description": "No was_derived_from, parent_datasets or errata; lineage is textual and does not attribute export formats to devices."},
    {"item_ids": ["Q20"], "score_effect": "lowered", "category": "bias_quality", "type": "completeness",
     "description": "Only one of two biases carries a bias_type; no fairness analysis beyond split balancing intent."},
    {"item_ids": [], "score_effect": "noted_only", "category": "source_conflict", "type": "content_accuracy",
     "description": "PI affiliations and the licensor/accountable organization are recorded as Washington University in St. Louis (ROR 01yc7t268) while NIH RePORTER, the IRB and the recruiting site are the University of Washington; the conflict is flagged only for Aaron Lee, not for Cecilia Lee or the licensor."},
    {"item_ids": [], "score_effect": "noted_only", "category": "format_access", "type": "consistency",
     "description": "distribution_formats (DICOM, Markdown, CSV, JSON) omits TSV and WFDB, which the file collections and conforms_to document."},
    {"item_ids": [], "score_effect": "noted_only", "category": "persistent_identifier", "type": "correctness",
     "description": "Two different Zenodo license DOIs appear (license_and_use_terms.id 10.5281/zenodo.17555036 for v2.0; external resource 10.5281/zenodo.10642459 cited by the 2024 comment); plausibly different license versions but not labeled as such."},
    {"item_ids": [], "score_effect": "noted_only", "category": "temporal_version", "type": "consistency",
     "description": "Source disagreements on enrollment start (18 vs 19 July 2023) and on whether v3.0 is pilot-phase data are documented in source_caveats and resolved to FAIRhub metadata."},
]

# Severity, fields involved and recommendation per issue, in ISSUES order.
EXTRA = [
    ("medium", ["resources", "parent_datasets", "variables", "regulatory_restrictions.confidentiality_level"],
     "Add a variable dictionary (or link to the data dictionary), a confidentiality_level classification and typed parent/related dataset links."),
    ("low", ["keywords"],
     "Add keywords for the remaining modalities and themes (OCT, OCTA, wearable sensors, environmental sensors, clinical laboratory data, salutogenesis)."),
    ("medium", ["data_protection_impacts", "at_risk_populations", "participant_privacy.reidentification_risk", "regulatory_restrictions.hipaa_compliant"],
     "Record the absence of a DPIA in data_protection_impacts, state whether vulnerable populations are included, and give an explicit re-identification risk assessment."),
    ("medium", ["is_deidentified.method", "is_deidentified.identifiers_removed", "is_deidentified.source_caveats"],
     "Reconcile the de-identification method with the removal of sex/race/medication data and the Safe Harbor statement; describe the released-data method separately from study-internal identifiers."),
    ("medium", ["preprocessing_strategies", "cleaning_strategies", "imputation_protocols"],
     "Name the conversion and mapping software with versions and repository URLs (e.g. the project's GitHub pipelines) and state whether any imputation was applied."),
    ("medium", ["errata", "maintainers", "version_access.version_details"],
     "Add a maintainer contact, an errata/changelog pointer and a preservation commitment, and explain the status of the withdrawn v2.0.0 DOI."),
    ("low", ["citation"],
     "Add a formal dataset citation (creators/publisher, year, title, version, DOI)."),
    ("medium", ["discouraged_uses", "future_use_impacts"],
     "Add discouraged uses and pair each future-use impact with a mitigation strategy."),
    ("high", ["license_and_use_terms.license_terms", "license_and_use_terms.source_caveats", "intended_uses"],
     "State which rule governs the public release (T2D-only research vs the license's commercial and non-commercial grant) so reusers have one operative use condition."),
    ("medium", ["was_derived_from", "parent_datasets", "errata", "preprocessing_strategies"],
     "Document per-modality lineage (device export -> conversion tool -> standard format) and derivation links between versions."),
    ("low", ["known_biases"],
     "Type every bias with a standard taxonomy term and add a fairness/representativeness analysis of the released cohort."),
    ("medium", ["creators", "license_and_use_terms.license_terms", "data_governance.accountable_organization"],
     "Verify the institution for the Lee PIs, the licensor and the accountable organization against the IRB and RePORTER records and flag every affected entry."),
    ("low", ["distribution_formats", "file_collections", "conforms_to"],
     "List TSV and WFDB in distribution_formats so the format inventory matches the file collections."),
    ("low", ["license_and_use_terms.id", "external_resources"],
     "Label the two Zenodo license DOIs with their license versions."),
    ("low", ["collection_timeframes", "source_caveats"],
     "No change needed beyond keeping the documented source disagreements."),
]
assert len(EXTRA) == len(ISSUES)
for i, (issue, (severity, fields, rec)) in enumerate(zip(ISSUES, EXTRA), 1):
    issue["id"] = f"I{i}"
    issue["severity"] = severity
    issue["fields_involved"] = fields
    issue["recommendation"] = rec

categories = []
names = ["Structural Completeness", "Metadata Quality & Content", "Technical Documentation", "FAIRness & Accessibility"]
for k, name in enumerate(names):
    qs = Q[k * 5:(k + 1) * 5]
    categories.append({"name": name, "questions": qs,
                       "category_score": sum(x["score"] for x in qs),
                       "category_max": sum(x["max_score"] for x in qs)})

total = sum(x["score"] for x in Q)
maxp = sum(x["max_score"] for x in Q)
assert maxp == 88

out = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": str(INPUT.relative_to(ROOT)),
    "project": "AI_READI",
    "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1",
    "evaluation_timestamp": "2026-11-22T00:00:00Z",
    "model": {
        "name": "claude-opus-5-5",
        "evaluator_model": "claude-opus-5-5",
        "temperature": None,
        "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
        "evaluation_type": "semantic_llm_judge",
    },
    "overall_score": {
        "total_points": total, "max_points": maxp, "excluded_max_points": 0, "adjusted_max_points": maxp,
        "normalized_percentage": round(total / maxp * 100, 2), "fixed_percentage": round(total / maxp * 100, 2),
        "questions_not_applicable": 0, "excluded_item_ids": [],
    },
    "categories": categories,
    "semantic_analysis": {
        "issues_detected": ISSUES,
        "semantic_insights": [
            "Counts are internally consistent: subpopulation groups and split counts sum to 2280 and 1576/352/352; collection file counts plus 9 root files equal total_file_count.",
            "Source conflicts are surfaced in source_caveats rather than silently resolved, which aids review but leaves two substantive conflicts (license scope, de-identification method) unresolved.",
            "Grant numbers follow NIH patterns; a source typo (letter O for zero) was detected and corrected.",
            "Ethics, collection and population documentation are strong; provenance, software versioning, bias taxonomy and sustainability are the main gaps.",
        ],
        "consistency_checks": {"passed": 11, "failed": 2, "warnings": 3},
        "correctness_validations": {
            "doi_format": "valid (10.60775/fairhub.3; FAIRhub prefix plausible, not independently verified)",
            "grant_number_format": "valid (OT2OD032644, P30DK035816, UL1TR003096 match NIH patterns)",
            "rrid_format": "not_applicable (no RRIDs present)",
            "url_validity": "well-formed (not live-checked)",
        },
    },
    "applicability_context": {},
    "evaluation_scope": {
        "policy": "single_dataset",
        "units": [{"path": "#", "id": DOC["id"]}],
        "collection_metadata_inherited": False,
    },
    "metadata": {
        "instrument_sha256": sha(AGENT),
        "evidence_authority_sha256": sha(AUTHORITY),
        "rubric_sha256": sha(RUBRIC),
        "input_sha256": INPUT_SHA,
        "context_sha256": context_digest({}),
    },
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(OUTPUT, total, maxp)
