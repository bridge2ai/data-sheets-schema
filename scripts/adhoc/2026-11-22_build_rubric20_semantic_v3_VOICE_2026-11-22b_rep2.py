#!/usr/bin/env python3
"""Build the rubric20-semantic v3 evaluation JSON for one VOICE D4D record.

Purpose: serialize the evaluator's (claude-opus-5-5) manual rubric20-semantic
judgements for data/d4d_concatenated/claudecode_agent/
2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/VOICE_d4d.yaml.
Inputs: that D4D record, .claude/agents/d4d-rubric20-semantic.md,
data/rubric/rubric20.txt, data/rubric/semantic_evidence_authority_v3.json.
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/
VOICE_2026-11-22b_rep2_evaluation.json
No caller applicability context was supplied (empty context; all conditional
predicates unknown). Date: 2026-11-22.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest, normalize_context  # noqa: E402

INPUT = ROOT / "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/VOICE_d4d.yaml"
AGENT = ROOT / ".claude/agents/d4d-rubric20-semantic.md"
RUBRIC = ROOT / "data/rubric/rubric20.txt"
AUTH = ROOT / "data/rubric/semantic_evidence_authority_v3.json"
OUT = ROOT / "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/VOICE_2026-11-22b_rep2_evaluation.json"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


DOC = yaml.safe_load(INPUT.read_text())


def norm(s):
    return " ".join(str(s).split())


def resolve(path):
    node = DOC
    for part in path.split("."):
        if isinstance(node, list):
            node = node[int(part)]
        else:
            node = node[part]
    return node


def emit(path):
    parts = path.split(".")
    if any(x.isdigit() for x in parts):
        return "/" + "/".join(parts)
    return path


def c(path, quote=None):
    val = resolve(path)
    if quote is not None:
        assert norm(quote) in norm(val), (path, quote)
        return {"path": emit(path), "quote": quote}
    return {"path": emit(path)}


def n(path):
    return {"path": emit(path), "claimed": len(resolve(path))}


def a(path):
    try:
        resolve(path)
    except (KeyError, IndexError, TypeError):
        return {"path": path}
    raise AssertionError(f"{path} is populated")


ALWAYS = "This item applies to every dataset"


def unk(pred):
    return f"{pred}: not declared by the caller; status unknown and retained in the denominator"


Q = []


def q(qid, name, desc, stype, score, maxs, label, evidence, note, status_pred,
      cited=(), absent=(), counts=(), considered=(), no_issue_reason=None):
    row = {
        "path": "#", "score": score, "evidence": evidence,
        "cited": list(cited), "absent": list(absent),
        "counts": list(counts), "considered": list(considered),
    }
    item = {
        "id": qid, "name": name, "description": desc[:120], "score_type": stype,
        "score": score, "max_score": maxs, "score_label": label,
        "evidence": evidence, "quality_note": note, "applicable": True,
        "applicability_status": "applicable" if status_pred is None else "unknown",
        "applicability_evidence": ALWAYS if status_pred is None else unk(status_pred),
        "unit_scores": [row],
    }
    if no_issue_reason:
        item["no_issue_reason"] = no_issue_reason
    Q.append(item)


# ---------------- Category 1 ----------------
q(1, "Field Completeness",
  "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
  "numeric", 3, 5, "Good (~70% populated)",
  "10 of 14 listed fields populated (id, title, description, keywords, license_and_use_terms, doi, page, creators, purposes, instances); top-level resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent (71%).",
  "71% populated sits at the ~70% anchor; below the >=90% needed for 5. Per-file resources exist only nested under file_collections, not as dataset-level resources; no variable-level metadata.",
  None,
  cited=[c("id"), c("title"), c("description"), c("keywords"), c("license_and_use_terms"),
         c("doi"), c("page"), c("creators"), c("purposes"), c("instances")],
  absent=[a("resources"), a("parent_datasets"), a("variables"),
          a("regulatory_restrictions.confidentiality_level")],
  considered=["file_collections", "regulatory_restrictions"])

q(2, "Entry Length Adequacy",
  "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
  "numeric", 5, 5, "Excellent (>200 chars)",
  "description is ~900 characters; each of the 4 purposes has a description of roughly 200-370 characters.",
  "Narrative fields are long and substantive, distinguishing the stated 30,000-voice goal from the current release size.",
  None,
  cited=[c("description", "contains data for 833 participants across five sites in North America"),
         c("purposes.1.description", "This is a stated project goal, not the size of the current release.")],
  counts=[n("purposes")])

q(3, "Keyword Diversity",
  "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply additional topic evidence where documented; no named study or disease count is presumed.",
  "numeric", 3, 5, "Good (3-7 keywords)",
  "keywords: health, biomarkers, bridge2ai, voice (4 distinct).",
  "Four keywords fall in the 3-7 band; terms such as acoustic features, speech, voice disorders, machine learning, or the disorder categories named in sampling_strategies are not listed as keywords. One keyword is a program name rather than a topic.",
  None,
  cited=[c("keywords")], counts=[n("keywords")],
  considered=["sampling_strategies"])

q(4, "File Enumeration and Type Variety",
  "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in separate linked resources. Examine every distribution; modality breadth is distinct from suitability for machine learning.",
  "numeric", 3, 5, "Good (2-3 file types)",
  "distribution_formats lists Parquet and TSV; file_collections additionally mention JSON data dictionaries accompanying each file; 10 feature files are enumerated with n counts. total_file_count is absent.",
  "Three file types (Parquet, TSV, JSON data dictionaries) meet the 2-3 band. Raw audio (BIDS on Synapse) is a controlled raw source, not a distributed format of this release. No total file count.",
  None,
  cited=[c("distribution_formats"),
         c("file_collections.0.description", "Every file is accompanied by a JSON data dictionary with the same file stem"),
         c("file_collections.0.resources")],
  counts=[n("distribution_formats"), n("file_collections"), n("file_collections.0.resources")],
  absent=[a("total_file_count")],
  considered=["raw_sources"])

q(5, "Data File Size Availability",
  "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
  "pass_fail", 1, 1, "Pass",
  "instances.0.counts = 833 participants; per-feature-file record counts (e.g. ppgs.parquet n=29289).",
  "Instance counts are present; byte sizes (total_size_bytes) and splits are not documented, which limits storage estimates.",
  None,
  cited=[c("instances.0.counts"), c("file_collections.0.resources.0.description", "n=29289")],
  absent=[a("total_size_bytes"), a("splits")])

# ---------------- Category 2 ----------------
q(6, "Dataset Identification Metadata",
  "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or repository).",
  "pass_fail", 1, 1, "Pass",
  "doi 10.13026/37yb-1t42 (PhysioNet prefix), id doi:10.13026/37yb-1t42, page https://physionet.org/content/b2ai-voice/.",
  "Valid PhysioNet DOI plus a PhysioNet landing page identify the hosting repository; the publisher slot itself is not populated (PhysioNet is named only in the citation and page URL).",
  None,
  cited=[c("doi"), c("id"), c("page"), c("citation", "PhysioNet. RRID:SCR_007345.")],
  absent=[a("publisher")])

q(7, "Funding and Acknowledgements Completeness",
  "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
  "numeric", 5, 5, "Excellent (funders with grants + creator affiliations)",
  "funders: NIH Common Fund Bridge2AI Program with grants OT2OD032720 and 3OT2OD032720-01S1; creators include PIs Yael Bensoussan (USF Health Morsani College of Medicine) and Olivier Elemento (Weill Cornell Medicine).",
  "Both grant numbers match the NIH pattern (OT2 activity, OD institute; 3...-01S1 a supplement). Affiliations are given only for the 2 principal investigators among 122 creators (noted, not lowered).",
  None,
  cited=[c("funders.0.grants.0.grant_number"), c("funders.0.grants.1.grant_number"),
         c("creators.0.principal_investigator.affiliation"),
         c("creators.3.principal_investigator.affiliation")],
  counts=[n("creators"), n("funders.0.grants")])

q(8, "Ethical and Privacy Declarations",
  "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable.",
  "numeric", 3, 5, "Good (IRB + deidentification, not comprehensive)",
  "USF IRB (single IRB) review; involves_human_subjects true; informed consent with scope and documentation; deidentification method (HIPAA Safe Harbor, feature-only release); reidentification risk (no k-anonymity, voice uniqueness); compensation ($40/$80, max $120); Certificate of Confidentiality. Absent: data_protection_impacts, at_risk_populations, hipaa_compliant, governance_committee_contact.",
  "Strong human-subjects documentation, but the 5 anchor requires all protections and data protection impacts; no data protection impact assessment and no vulnerable-population statement although participants are recruited for mood, neurological and other disorders. HIPAA Safe Harbor removal is claimed yet regulatory_restrictions.hipaa_compliant is unset.",
  "human_subjects",
  cited=[c("ethical_reviews.0.reviewing_organization"),
         c("human_subject_research.involves_human_subjects"),
         c("informed_consent.0.consent_scope", "shared through a controlled access mechanism"),
         c("is_deidentified.identifiers_removed", "HIPAA Safe Harbor identifiers were removed."),
         c("participant_privacy.0.reidentification_risk", "does not achieve k-anonymization"),
         c("participant_compensation.0.compensation_amount"),
         c("regulatory_restrictions.other_compliance", "Certificate of Confidentiality")],
  absent=[a("data_protection_impacts"), a("at_risk_populations"),
          a("regulatory_restrictions.hipaa_compliant"),
          a("regulatory_restrictions.governance_committee_contact")],
  considered=["human_subject_research", "informed_consent", "is_deidentified",
              "participant_privacy", "participant_compensation", "ethical_reviews",
              "regulatory_restrictions", "sampling_strategies"])

q(9, "Access Requirements and Governance Documentation",
  "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts.",
  "numeric", 3, 5, "Good (license + restrictions, no confidentiality classification)",
  "license_and_use_terms (credentialed users sign the DUA; Fort Lauderdale Agreement IP terms), ip_restrictions (no sale; IP may not restrict access), regulatory_restrictions.other_compliance (Certificate of Confidentiality), data_governance (DACO review for raw audio). No confidentiality_level, governance contact, hipaa_compliant or data_protection_impacts.",
  "Access tiers are distinguished (credentialed DUA for features vs DACO-approved DTUA for raw audio), but the 5 anchor needs a confidentiality classification, which is absent; the governance committee is named without a contact.",
  None,
  cited=[c("license_and_use_terms.description", "Only credentialed users who sign the DUA can access the files."),
         c("ip_restrictions.restrictions"),
         c("regulatory_restrictions.other_compliance"),
         c("data_governance.committee_name")],
  absent=[a("regulatory_restrictions.confidentiality_level"),
          a("regulatory_restrictions.governance_committee_contact"),
          a("regulatory_restrictions.hipaa_compliant"),
          a("data_protection_impacts")],
  considered=["license", "license_and_use_terms", "ip_restrictions",
              "regulatory_restrictions", "data_governance"])

q(10, "Interoperability, Standardization, and Cross-Platform Integration",
  "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures.",
  "numeric", 3, 5, "Good (standard formats, no schema conformance declared)",
  "Parquet and TSV standard formats with JSON data dictionaries; labels per ICD-10 codes; raw audio (not this release) converted to BIDS v1.9.0; external_resources link the REDCap data dictionary. conforms_to, conforms_to_schema and related_datasets are absent.",
  "Standard open formats are documented, but no formal schema/ontology conformance is declared for the released files; BIDS applies to the controlled raw audio only. No typed related_datasets (the pediatric dataset is deliberately not linked).",
  "shared_dataset",
  cited=[c("distribution_formats"),
         c("raw_sources.0.raw_data_details", "Brain Imaging Data Structure v1.9.0"),
         c("labeling_strategies.0.data_annotation_protocol", "ICD-10 codes"),
         c("external_resources")],
  absent=[a("conforms_to"), a("conforms_to_schema"), a("related_datasets")],
  considered=["file_collections"])

# ---------------- Category 3 ----------------
q(11, "Tool and Software Transparency",
  "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs.",
  "numeric", 5, 5, "Excellent (strategies with software versions/URLs)",
  "Preprocessing with b2aiprep v3.0.0 (GitHub URL) and senselab (URL); OpenSMILE eGeMAPS, Parselmouth/Praat, torchaudio, sparc, ppgs; audio standardization parameters (16 kHz, 25ms window, 10ms hop, 400-point FFT); cleaning (distribution/outlier/schema checks, QC metrics); labeling by clinicians per ICD-10; machine annotation with OpenAI Whisper Large; missingness tables.",
  "Comprehensive processing documentation with the release-generating library versioned and linked; several feature extractors lack versions and imputation is not documented (minor).",
  "data_processing",
  cited=[c("preprocessing_strategies.0.used_software.0.version"),
         c("preprocessing_strategies.0.used_software.0.url"),
         c("preprocessing_strategies.2.preprocessing_details", "400-point FFT"),
         c("cleaning_strategies.0.cleaning_details"),
         c("machine_annotation_tools.0.tools"),
         c("labeling_strategies.0.labeling_details"),
         c("missing_data_documentation.0.description")],
  counts=[n("preprocessing_strategies")])

q(12, "Collection Protocol Clarity",
  "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
  "numeric", 3, 5, "Good (methods and collectors, no timeframes)",
  "collection_mechanisms (Bridge2AI-Voice App, 22 acoustic tasks; iPad + Avid AE-36 microphone), data_collectors (trained research assistants in clinic), acquisition_methods (directly observed, self-reported, clinician-verified), raw_sources (Synapse controlled access). collection_timeframes is absent.",
  "The 5 anchor requires methods, collectors and timeframes; no collection period is stated (only release dates), so the full-protocol band is not met.",
  "data_collection",
  cited=[c("collection_mechanisms.0.mechanism_details", "a total of 22 acoustic tasks are recorded through the app"),
         c("collection_mechanisms.1.description", "Avid AE-36 microphone"),
         c("data_collectors.0.description"),
         c("acquisition_methods.0.description"),
         c("raw_sources.0.access_url")],
  absent=[a("collection_timeframes"), a("raw_data_sources")],
  considered=["direct_collection", "version_access"])

q(13, "Version History, Maintenance, and Sustainability",
  "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access.",
  "numeric", 3, 5, "Good (versioning + access + persistent ID; sustainability incomplete)",
  "version 3.1.0; version_access lists six versions with dates and DOIs and per-version changes; updates semi-annual; retention possibly indefinite; DOI 10.13026/37yb-1t42. maintainers, errata and publisher are absent.",
  "Versioning is thorough, but no maintainer or responsible contact, no errata record (the fixed broken parquet files are mentioned only in version_details), and the update cadence is taken from the v2.0.0-era healthsheet rather than a current commitment.",
  "shared_dataset",
  cited=[c("version"), c("version_access.versions_available"),
         c("version_access.version_details", "fixed broken parquet files"),
         c("updates.frequency"), c("doi"),
         c("retention_limit.retention_details", "possibly indefinitely")],
  counts=[n("version_access.versions_available")],
  absent=[a("maintainers"), a("errata"), a("publisher")],
  considered=["updates", "extension_mechanism"])

q(14, "Associated Publications",
  "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources.",
  "numeric", 5, 5, "Excellent (formal citation + multiple references)",
  "Formal citation with authors, title, version, PhysioNet and DOI; six distinct external resources (Frontiers feasibility paper, REDCap protocols GitHub/Zenodo, JAMA Otolaryngology viewpoint, Interspeech 2024 paper, training site, bridge2ai-docs).",
  "At least two distinct references plus a formal dataset citation meet the 5 anchor. The citation uses the version DOI (8xbn-nq66) while doi/id carry the concept DOI; source_caveats explains the difference.",
  None,
  cited=[c("citation", "Bridge2AI-Voice: An ethically-sourced, diverse voice dataset linked to health information (version 3.1.0)"),
         c("external_resources"), c("doi")],
  counts=[n("external_resources")])

q(15, "Human Subject Representation",
  "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups.",
  "numeric", 3, 5, "Good (population described, no detailed demographics)",
  "833 participants; subpopulations names Age, Gender, Sex, Ethnicity, Socioeconomic status; non-probability clinic-based sampling across voice, neurological, mood and respiratory disorders; not representative. No demographic distributions, inclusion/exclusion criteria referenced but not stated, at_risk_populations absent.",
  "Subgroup axes are named without counts or proportions, and inclusion/exclusion criteria are mentioned only by reference, so detailed demographics required for 5 are missing.",
  "human_subjects",
  cited=[c("instances.0.counts"), c("subpopulations.0.identification"),
         c("sampling_strategies.0.description", "based on diagnosis and inclusion/exclusion criteria"),
         c("sampling_strategies.0.why_not_representative"),
         c("missing_data_documentation.0.missing_data_patterns")],
  absent=[a("at_risk_populations")],
  considered=["instances", "subpopulations", "missing_data_documentation", "known_biases"])

# ---------------- Category 4 ----------------
q(16, "Findability (Persistent Links)",
  "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
  "pass_fail", 1, 1, "Pass",
  "page https://physionet.org/content/b2ai-voice/, DOI 10.13026/37yb-1t42, external resource URLs.",
  "Well-formed PhysioNet landing page and DOI; download_url is not given (the landing page serves as the access point).",
  None,
  cited=[c("page"), c("doi"), c("external_resources")],
  absent=[a("download_url")])

q(17, "Accessibility (Access Mechanism)",
  "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
  "numeric", 5, 5, "Excellent (platform, login and policy defined)",
  "Platform PhysioNet (page), credentialed users signing the DUA for the feature release, Parquet/TSV formats; raw audio via Synapse under a DACO-reviewed DTUA with institutional sign-off.",
  "The access path is defined per tier (credentialed + DUA vs controlled DTUA). The top-level license is still named 'Registered Access License' while the operative tier is credentialed access; source_caveats documents and resolves this (noted, not lowered). No download_url.",
  "shared_dataset",
  cited=[c("page"),
         c("license_and_use_terms.description", "Only credentialed users who sign the DUA can access the files."),
         c("distribution_formats"),
         c("data_governance.access_review_process", "submit the application to the Data Access Compliance Office for review"),
         c("raw_sources.0.access_url")],
  absent=[a("download_url")],
  considered=["license", "source_caveats"])

q(18, "Reusability, Use Guidance, and Social Impact",
  "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis with risk identification and mitigation strategies.",
  "numeric", 3, 5, "Good (license + use guidance, no social impact analysis)",
  "License/DUA; intended_uses (AI/ML research, pretraining, benchmarking); four prohibited_uses with a prohibition reason; one discouraged use. future_use_impacts absent.",
  "Use guidance is solid, but there is no social impact analysis with mitigation strategies (future_use_impacts absent); the discouraged use duplicates a prohibited use, so the two categories are not clearly differentiated.",
  None,
  cited=[c("license_and_use_terms.license_terms"),
         c("intended_uses.0.description"),
         c("prohibited_uses.2.prohibition_reason"),
         c("discouraged_uses.0.description", "hiring decisions, insurance premium adjustments")],
  counts=[n("prohibited_uses")],
  absent=[a("future_use_impacts")],
  considered=["license", "license_and_use_terms", "intended_uses", "prohibited_uses", "discouraged_uses", "known_biases"])

q(19, "Data Integrity, Provenance Graph, and Quality",
  "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation.",
  "numeric", 3, 5, "Good (version history, textual lineage; no full provenance graph)",
  "version_access history with DOIs; updates plan; missing_data_documentation; raw_sources (Synapse raw audio); textual lineage REDCap/raw audio -> b2aiprep v3.0.0 -> released features and phenotype files. errata, was_derived_from, parent_datasets and splits absent.",
  "Version history and a partial textual processing lineage are present, but derivation links are not structured, agents per processing step and dates are not given, and no errata or parent linkages exist, so a full entity-activity-agent provenance is not reached.",
  None,
  cited=[c("version_access.versions_available"), c("updates.update_details"),
         c("missing_data_documentation.0.missing_data_causes"),
         c("raw_sources.0.description", "raw audio for the adult cohort is made available via Synapse under controlled access"),
         c("preprocessing_strategies.0.preprocessing_details", "release 3.1.0 was generated with b2aiprep v3.0.0")],
  absent=[a("errata"), a("was_derived_from"), a("parent_datasets"), a("splits"), a("raw_data_sources")],
  considered=["version_access", "updates", "missing_data_documentation", "anomalies"])

q(20, "Bias Documentation and Responsible AI Alignment",
  "Documentation of known biases, limitations and potential effects on intended or foreseeable uses.",
  "numeric", 3, 5, "Good (basic bias identification, no taxonomy)",
  "Two known_biases (recruitment trust/proximity; skews by disorder, site, demographics, with a mitigation note); four known_limitations (unequal disease distribution, device/site confounding); non-representative sampling.",
  "Biases are identified in prose without a standard taxonomy (no bias_type) or fairness analysis, and future_use_impacts is absent.",
  None,
  cited=[c("known_biases.0.bias_description", "less trust in the medical system or AI"),
         c("known_biases.1.mitigation_strategy"),
         c("known_limitations.0.description")],
  counts=[n("known_biases"), n("known_limitations")],
  absent=[a("future_use_impacts")],
  considered=["known_biases", "known_limitations", "sampling_strategies"])

# ---------------- Issues ----------------
ISSUES = [
    {"id": "I1", "item_ids": ["Q1"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "severity": "medium",
     "description": "Dataset-level resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent; no variable-level metadata despite phenotype TSVs with data dictionaries."},
    {"id": "I2", "item_ids": ["Q3"], "score_effect": "lowered", "category": "other", "type": "completeness",
     "severity": "low",
     "description": "Only four keywords, one a program name; disorder categories and modality terms are not used as keywords."},
    {"id": "I3", "item_ids": ["Q4"], "score_effect": "lowered", "category": "format_access", "type": "completeness",
     "severity": "low",
     "description": "Distribution formats limited to Parquet and TSV (plus JSON dictionaries); total_file_count absent."},
    {"id": "I4", "item_ids": ["Q8"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "consistency",
     "severity": "medium",
     "description": "HIPAA Safe Harbor deidentification is claimed but regulatory_restrictions.hipaa_compliant is unset; data_protection_impacts and at_risk_populations are absent although participants are recruited for mood and neurological disorders."},
    {"id": "I5", "item_ids": ["Q9"], "score_effect": "lowered", "category": "license_use_terms", "type": "completeness",
     "severity": "medium",
     "description": "No confidentiality_level classification or governance committee contact; DACO is named without a contact route."},
    {"id": "I6", "item_ids": ["Q10"], "score_effect": "lowered", "category": "format_access", "type": "completeness",
     "severity": "medium",
     "description": "No conforms_to/conforms_to_schema for the released files; BIDS conformance applies only to controlled raw audio; no typed related_datasets."},
    {"id": "I7", "item_ids": ["Q12"], "score_effect": "lowered", "category": "temporal_version", "type": "completeness",
     "severity": "medium",
     "description": "collection_timeframes absent; only release dates are given, so the data collection period cannot be determined."},
    {"id": "I8", "item_ids": ["Q13"], "score_effect": "lowered", "category": "temporal_version", "type": "completeness",
     "severity": "medium",
     "description": "No maintainers, errata or publisher fields; the semi-annual update cadence is attributed to a v2.0.0-era healthsheet rather than a current maintenance commitment."},
    {"id": "I9", "item_ids": ["Q15"], "score_effect": "lowered", "category": "bias_quality", "type": "completeness",
     "severity": "medium",
     "description": "Subpopulation axes are listed without distributions; inclusion/exclusion criteria are referenced but not stated; at_risk_populations absent."},
    {"id": "I10", "item_ids": ["Q18"], "score_effect": "lowered", "category": "license_use_terms", "type": "completeness",
     "severity": "medium",
     "description": "future_use_impacts absent: no social impact analysis with mitigation strategies."},
    {"id": "I11", "item_ids": ["Q19"], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
     "severity": "medium",
     "description": "No was_derived_from, parent_datasets, errata or splits; lineage is textual and partial (no per-step agents or dates)."},
    {"id": "I12", "item_ids": ["Q20"], "score_effect": "lowered", "category": "bias_quality", "type": "completeness",
     "severity": "medium",
     "description": "Biases described in prose without a standard taxonomy (bias_type) or fairness analysis."},
    {"id": "I13", "item_ids": [], "score_effect": "noted_only", "category": "license_use_terms", "type": "consistency",
     "severity": "low",
     "description": "Top-level license 'Bridge2AI Voice Registered Access License' and license_and_use_terms name 'Registered Access Agreement' coexist with the operative statement that only credentialed users who sign the DUA can access the files; source_caveats documents the terminology conflict and prefers the 3.1.0 page."},
    {"id": "I14", "item_ids": [], "score_effect": "noted_only", "category": "license_use_terms", "type": "consistency",
     "severity": "low",
     "description": "Hiring decisions, insurance premium adjustments and surveillance appear both as a prohibited use ('non-research applications') and as a discouraged use ('non-clinical applications'), blurring the two categories."},
    {"id": "I15", "item_ids": [], "score_effect": "noted_only", "category": "persistent_identifier", "type": "consistency",
     "severity": "low",
     "description": "doi/id carry the concept DOI 10.13026/37yb-1t42 while the citation cites the version DOI 10.13026/8xbn-nq66; both are valid PhysioNet DOIs and source_caveats explains the distinction."},
    {"id": "I16", "item_ids": [], "score_effect": "noted_only", "category": "attribution", "type": "completeness",
     "severity": "low",
     "description": "Affiliations are recorded only for 2 of 122 creators (the principal investigators)."},
    {"id": "I17", "item_ids": [], "score_effect": "noted_only", "category": "license_use_terms", "type": "semantic_understanding",
     "severity": "low",
     "description": "license_and_use_terms.description says the dataset is 'intended solely for commercial and non-commercial research purposes', an awkward phrasing whose restrictiveness ('solely' yet including commercial) is unclear."},
]

FIX = {
    "I1": (["resources", "parent_datasets", "variables", "regulatory_restrictions.confidentiality_level"],
           "Add dataset-level resources, variable definitions for phenotype/feature files, and a confidentiality level."),
    "I2": (["keywords"], "Add topical keywords (speech, acoustic features, voice disorders, neurological, mood, respiratory disorders, machine learning)."),
    "I3": (["distribution_formats", "total_file_count"], "List JSON data dictionaries as a distribution format and record the total file count."),
    "I4": (["regulatory_restrictions.hipaa_compliant", "data_protection_impacts", "at_risk_populations", "is_deidentified"],
           "Set hipaa_compliant consistent with the Safe Harbor claim, document data protection impacts, and state whether vulnerable populations are included."),
    "I5": (["regulatory_restrictions.confidentiality_level", "regulatory_restrictions.governance_committee_contact", "data_governance"],
           "Add a confidentiality classification and a contact for the Data Access Compliance Office."),
    "I6": (["conforms_to", "conforms_to_schema", "related_datasets"],
           "Declare the data dictionary/schema the released files conform to and add typed relations to related datasets where sources state them."),
    "I7": (["collection_timeframes"], "Record the data collection start and end dates for the release."),
    "I8": (["maintainers", "errata", "publisher", "updates"],
           "Name maintainers with contact, record errata (e.g. the fixed broken parquet files) and set publisher to PhysioNet."),
    "I9": (["subpopulations", "sampling_strategies", "at_risk_populations"],
           "Provide demographic distributions and state the inclusion/exclusion criteria explicitly."),
    "I10": (["future_use_impacts"], "Document foreseeable social impacts of reuse and mitigation strategies."),
    "I11": (["was_derived_from", "parent_datasets", "errata", "splits"],
            "Add structured derivation links (raw audio and REDCap sources to released features) with responsible agents and dates."),
    "I12": (["known_biases"], "Classify biases with a standard taxonomy (bias_type) and add a fairness analysis across subgroups."),
    "I13": (["license", "license_and_use_terms"], "Align the license name and access-tier wording with the credentialed-access tier."),
    "I14": (["prohibited_uses", "discouraged_uses"], "Keep each use restriction in a single category matching its source force."),
    "I15": (["doi", "id", "citation"], "Optionally record the version DOI explicitly alongside the concept DOI."),
    "I16": (["creators"], "Add affiliations for creators where sources provide them."),
    "I17": (["license_and_use_terms.description"], "Clarify whether commercial research use is permitted."),
}
for issue in ISSUES:
    issue["fields_involved"], issue["recommendation"] = FIX[issue["id"]]

total = sum(x["score"] for x in Q)
cats = []
for name, ids in [("Structural Completeness", range(1, 6)), ("Metadata Quality & Content", range(6, 11)),
                  ("Technical Documentation", range(11, 16)), ("FAIRness & Accessibility", range(16, 21))]:
    qs = [x for x in Q if x["id"] in ids]
    cats.append({"name": name, "questions": qs,
                 "category_score": sum(x["score"] for x in qs),
                 "category_max": sum(x["max_score"] for x in qs)})
max_points = sum(x["max_score"] for x in Q)
assert max_points == 88

ctx = normalize_context({})
out = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": str(INPUT.relative_to(ROOT)),
    "project": "VOICE",
    "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2",
    "evaluation_timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {
        "name": "claude-opus-5-5",
        "evaluator_model": "claude-opus-5-5",
        "temperature": None,
        "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
        "evaluation_type": "semantic_llm_judge",
    },
    "overall_score": {
        "total_points": total,
        "max_points": max_points,
        "excluded_max_points": 0,
        "adjusted_max_points": max_points,
        "normalized_percentage": round(total / max_points * 100, 2),
        "fixed_percentage": round(total / max_points * 100, 2),
        "questions_not_applicable": 0,
        "excluded_item_ids": [],
    },
    "categories": cats,
    "semantic_analysis": {
        "issues_detected": ISSUES,
        "semantic_insights": [
            "Grant numbers OT2OD032720 and 3OT2OD032720-01S1 follow NIH activity/institute/serial patterns (the latter a supplement); source_caveats records the RePORTER and acknowledgement variants.",
            "DOI prefix 10.13026 matches PhysioNet; the concept DOI, version DOI and historical version DOIs are distinguished; RRID:SCR_007345 (PhysioNet) is well formed.",
            "Human-subjects logic is consistent: involves_human_subjects true with ethical_reviews, informed_consent, deidentification method and privacy protections populated.",
            "Temporal ordering of releases (1.1 Jan 2025 -> 2.0.0 Apr 2025 -> 2.0.1 Aug 2025 -> 3.0.0 Dec 2025 -> 3.1.0 May 2026) is consistent with issued 2026-05-01; no collection period is given.",
            "The record carefully separates stated goals (30,000 voices) from current release size (833 participants) and attributes healthsheet statements to their v2.0.0 context.",
        ],
        "consistency_checks": {"passed": 6, "failed": 1, "warnings": 4},
        "correctness_validations": {
            "doi_format": "valid (10.13026/37yb-1t42, PhysioNet registrar prefix)",
            "grant_number_format": "valid NIH format (OT2OD032720; supplement 3OT2OD032720-01S1)",
            "rrid_format": "valid (RRID:SCR_007345 in citation)",
            "url_validity": "well-formed (physionet.org, github.com, zenodo.org, synapse.org, isca-archive.org); not fetched",
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
        "evidence_authority_sha256": sha(AUTH),
        "rubric_sha256": sha(RUBRIC),
        "input_sha256": sha(INPUT),
        "context_sha256": context_digest(ctx),
    },
}
OUT.parent.mkdir(parents=True, exist_ok=True)
assert not OUT.exists() or "--overwrite-own" in sys.argv, "refusing to replace an existing evaluation"
OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(OUT, total, max_points)
