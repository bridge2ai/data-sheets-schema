#!/usr/bin/env python3
"""Serialize one rubric20-semantic v3 evaluation (judgements made by the evaluator).

Purpose: write the manually judged rubric20-semantic (general context instrument v3)
evaluation of VOICE_PEDIATRIC, label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2,
as JSON, computing digests and totals mechanically.
Inputs: the D4D record, .claude/agents/d4d-rubric20-semantic.md, data/rubric/rubric20.txt,
data/rubric/semantic_evidence_authority_v3.json.
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/
VOICE_PEDIATRIC_2026-11-22b_rep2_evaluation.json
Date: 2026-11-22. Evaluator: claude-opus-5-5 (Claude Code session). No caller context.
"""
import datetime
import hashlib
import json
from pathlib import Path

from data_sheets_schema.evaluation_context import context_digest, normalize_context

D4D = Path("data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/VOICE_PEDIATRIC_d4d.yaml")
OUT = Path("data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/VOICE_PEDIATRIC_2026-11-22b_rep2_evaluation.json")
AGENT = Path(".claude/agents/d4d-rubric20-semantic.md")
RUBRIC = Path("data/rubric/rubric20.txt")
AUTH = Path("data/rubric/semantic_evidence_authority_v3.json")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


ALWAYS = "This item applies to every dataset"


def unk(pred):
    return f"{pred}: not declared by the caller (no context file supplied); unknown, retained in the denominator"


def c(path, quote=None):
    d = {"path": path}
    if quote:
        d["quote"] = quote
    return d


def a(path):
    return {"path": path}


# id, name, desc, score_type, score, max, label, evidence, quality_note, status, appl_ev, cited, absent, counts, considered, no_issue_reason
Q = []


def q(id_, name, desc, stype, score, mx, label, evidence, note, status, appl_ev,
      cited=(), absent=(), counts=(), considered=(), no_issue_reason=None):
    item = {
        "id": id_, "name": name, "description": desc, "score_type": stype,
        "score": score, "max_score": mx, "score_label": label, "evidence": evidence,
        "quality_note": note, "applicable": True, "applicability_status": status,
        "applicability_evidence": appl_ev,
        "unit_scores": [{"path": "#", "score": score, "evidence": evidence,
                         "cited": list(cited), "absent": list(absent),
                         "counts": list(counts), "considered": list(considered)}],
    }
    if no_issue_reason:
        item["no_issue_reason"] = no_issue_reason
    Q.append(item)


q(1, "Field Completeness", "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
  "numeric", 3, 5, "Good (~79% populated)",
  "11 of 14 listed fields populated: id 'doi:10.13026/h995-bt35', title, description, keywords, license_and_use_terms, doi, page, creators (121), purposes (2), instances (2), variables (4). Absent: top-level resources, parent_datasets, regulatory_restrictions.confidentiality_level.",
  "78.6% populated is above the ~70% anchor but below the >=90% anchor for 5.",
  "applicable", ALWAYS,
  cited=[c("id", "doi:10.13026/h995-bt35"), c("title", "Bridge2AI-Voice Pediatric Dataset"), c("doi", "10.13026/h995-bt35"),
         c("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/"), c("description"), c("keywords"),
         c("license_and_use_terms"), c("creators"), c("purposes"), c("instances"), c("variables")],
  absent=[a("resources"), a("parent_datasets"), a("regulatory_restrictions")],
  counts=[{"path": "creators", "claimed": 121}, {"path": "variables", "claimed": 4}])

q(2, "Entry Length Adequacy", "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
  "numeric", 5, 5, "Excellent (>200 chars)",
  "description is 731 characters; the two purposes responses are 212 and 277 characters, all above the 200-character anchor, and they are substantive (counts, age range, site, release organization, raw-audio exclusion).",
  "Narrative fields are long and specific to the pediatric release.",
  "applicable", ALWAYS,
  cited=[c("description", "contains derived audio features for 23,533 recordings collected from 300 participants aged 2-18 at the Hospital for Sick Children"),
         c("/purposes/1/response", "to build a large multi-institutional database of human voices, speech and respiratory sounds")],
  counts=[{"path": "purposes", "claimed": 2}])

q(3, "Keyword Diversity", "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply additional topic evidence where documented; no named study or disease count is presumed.",
  "numeric", 3, 5, "Good (3-7 keywords)",
  "5 keywords: health, pediatric, biomarkers, bridge2ai, voice. No controlled-vocabulary terms; 'health' is generic and terms for the data types (spectrogram, acoustic features, speech) are absent.",
  "Keyword count falls in the 3-7 band.",
  "applicable", ALWAYS,
  cited=[c("/keywords/0", "health"), c("/keywords/1", "pediatric")],
  counts=[{"path": "keywords", "claimed": 5}])

q(4, "File Enumeration and Type Variety", "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in separate linked resources. Examine every distribution; modality breadth is distinct from suitability for machine learning.",
  "numeric", 3, 5, "Good (2-3 file types)",
  "file_collections enumerates 11 files in features: 9 Parquet files (spectrograms, mel spectrograms, MFCC, pitch, EMA, loudness, periodicity, SPARC pitch, PPGs) and 2 TSV files; JSON data dictionaries are described. Phenotype and metadata collections list no files or formats. No distribution_formats or total_file_count; the Parquet resources carry no format/media_type field.",
  "Three file types (Parquet, TSV, JSON) are documented; enumeration covers only the features folder.",
  "applicable", ALWAYS,
  cited=[c("/file_collections/0/description", "Binary files are made available as Parquet"),
         c("/file_collections/0/resources/9/format", "TSV"),
         c("/file_collections/0/description", "a JSON suffix"),
         c("/file_collections/1/description", "Phenotypic information acquired during data collection.")],
  absent=[a("distribution_formats"), a("total_file_count")],
  counts=[{"path": "file_collections", "claimed": 3}, {"path": "/file_collections/0/resources", "claimed": 11}])

q(5, "Data File Size Availability", "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
  "pass_fail", 1, 1, "Pass",
  "instances gives counts 23533 recordings and 300 participants; per-file n values (23533/23532) and tensor dimensions (201xT, 60xT, Tx12, 40xT) are given. No byte sizes.",
  "Instance counts satisfy the pass condition; byte sizes are absent.",
  "applicable", ALWAYS,
  cited=[c("/instances/0/counts"), c("/instances/1/counts"), c("/file_collections/0/resources/0/description", "Spectrograms of dimension 201xT")],
  absent=[a("total_size_bytes")], counts=[{"path": "instances", "claimed": 2}])

q(6, "Dataset Identification Metadata", "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or repository).",
  "pass_fail", 1, 1, "Pass",
  "doi 10.13026/h995-bt35 (PhysioNet registrar prefix), id doi:10.13026/h995-bt35, page on physionet.org; the citation names PhysioNet and RRID:SCR_007345. The publisher slot itself is empty.",
  "Persistent identifier and hosting platform are identifiable; publisher should be populated as a field.",
  "applicable", ALWAYS,
  cited=[c("doi", "10.13026/h995-bt35"), c("id"), c("page", "physionet.org"), c("citation", "PhysioNet. RRID:SCR_007345")],
  absent=[a("publisher")])

q(7, "Funding and Acknowledgements Completeness", "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
  "numeric", 5, 5, "Excellent (funder + grant + affiliations)",
  "funders: NIH with grant 3OT2OD032720-01S1 (valid NIH pattern: application type 3, activity OT2, IC OD, serial 032720, year 01, supplement S1) and award title; the RePORTER discrepancy (-01S3) is disclosed. 14 of 121 creators carry institutional affiliations, including PIs (USF Health Morsani College of Medicine, Weill Cornell Medicine).",
  "Funder, award number and creator affiliations are all present; most consortium authors lack affiliations.",
  "applicable", ALWAYS,
  cited=[c("/funders/0/grants/0/grant_number", "3OT2OD032720-01S1"), c("/funders/0/name", "NIH"),
         c("/creators/0/affiliations/0/name", "USF Health Morsani College of Medicine"), c("/funders/0/source_caveats", "3OT2OD032720-01S3")],
  counts=[{"path": "funders", "claimed": 1}, {"path": "creators", "claimed": 121}])

q(8, "Ethical and Privacy Declarations", "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable. Accept equivalent jurisdiction-appropriate ethics review and data protection frameworks.",
  "numeric", 3, 5, "Good (ethics review, consent, privacy; incomplete data protection)",
  "ethical_reviews: SickKids Research Ethics Board approved collection and sharing; human_subject_research.involves_human_subjects true; informed_consent (parental or participant, collection and sharing); at_risk_populations with assent procedures and guardian consent; participant_privacy with raw audio withheld and reidentification_risk; participant_compensation (adult only, from the umbrella protocol). Absent: is_deidentified, any deidentification method for the pediatric derived data, data_protection_impacts, regulatory_restrictions (no Canadian/Ontario compliance framework; the HIPAA wording is from the US umbrella protocol).",
  "Strong human-subjects coverage, but the 5 anchor requires data protection impacts and full privacy protections, which are missing.",
  "unknown", unk("human_subjects"),
  cited=[c("/ethical_reviews/0/reviewing_organization", "Research Ethics Board at the Hospital for Sick Children"),
         c("human_subject_research.involves_human_subjects"), c("/informed_consent/0/consent_scope", "data collection and data sharing"),
         c("at_risk_populations.assent_procedures", "children will provide verbal assent where appropriate"),
         c("/participant_privacy/0/reidentification_risk", "a voice can never be fully de-identified"),
         c("/participant_compensation/0/description", "compensation will be provided to the adult population only")],
  absent=[a("is_deidentified"), a("data_protection_impacts"), a("regulatory_restrictions")],
  considered=["data_governance", "collection_consents", "consent_revocations"])

q(9, "Access Requirements and Governance Documentation", "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts. Distinguish unrestricted access, registration, an agreement and committee approval. A named license does not by itself imply unrestricted reuse.",
  "numeric", 3, 5, "Good (license + access terms; no confidentiality classification)",
  "license_and_use_terms names the Bridge2AI Voice Registered Access License and Agreement, credentialed access and DUA; data_governance distinguishes registered (features) from controlled (raw audio, DARF + DUA + DTUA, DACO review) access with contact DACO@b2ai-voice.org. Absent: regulatory_restrictions (confidentiality_level, compliance, governance_committee_contact), ip_restrictions, data_protection_impacts. Low risk is stated only in sensitive_elements prose.",
  "Access and governance routes are well described, but the 5 anchor's confidentiality classification and the regulatory/IP fields are missing.",
  "applicable", ALWAYS,
  cited=[c("license_and_use_terms.license_terms", "Bridge2AI Voice Registered Access License"),
         c("data_governance.access_review_process", "Data Access Compliance Office"),
         c("/sensitive_elements/0/sensitivity_details", "The release contains data considered low risk")],
  absent=[a("regulatory_restrictions"), a("ip_restrictions"), a("data_protection_impacts")],
  considered=["license"])

q(10, "Interoperability, Standardization, and Cross-Platform Integration", "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures. Assess suitability for the declared uses; machine-learning use and any study-specific readiness framework must not be assumed.",
  "numeric", 3, 5, "Good (standard formats, no schema reference)",
  "Standard open formats (Parquet, TSV, JSON data dictionaries) are documented; preprocessing mentions conversion to REDCap format and BIDS, but no conforms_to/conforms_to_schema entry, no distribution_formats, no related_datasets (the adult dataset relation is deliberately left unrecorded) and only one external_resources link.",
  "Standard formats without a declared schema or typed dataset relationships.",
  "unknown", unk("shared_dataset"),
  cited=[c("/file_collections/0/description", "Parquet, an open-source column-oriented data file format"),
         c("/preprocessing_strategies/0/preprocessing_details", "Brain Imaging Data Structure (BIDS)"),
         c("external_resources")],
  absent=[a("conforms_to"), a("conforms_to_schema"), a("distribution_formats"), a("related_datasets")])

q(11, "Tool and Software Transparency", "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs. Structured text and provenance graphs are both valid evidence. Data processing is relevant independently of whether software is a released dataset output.",
  "numeric", 5, 5, "Excellent (strategies + versioned software with URL)",
  "preprocessing_strategies: export/format conversion (ReproSchema-UI -> REDCap -> BIDS), b2aiprep version 3.0.0 with GitHub URL and Apache-2.0 license, feature extraction with openSMILE, Praat, parselmouth, torchaudio; feature parameters (25ms window, 10ms hop, 400-point FFT, 60 Mel bins) per file; cleaning_strategies (manual check for unconsented speakers and PII; caregiver voice); missing_data_documentation. Labeling, annotation and imputation are absent; openSMILE/Praat/parselmouth/torchaudio lack versions and the EMA deep learning model is unnamed.",
  "Comprehensive processing workflow with the main library versioned and linked; secondary tools unversioned.",
  "unknown", unk("data_processing"),
  cited=[c("/preprocessing_strategies/1/used_software/0/version", "3.0.0"),
         c("/preprocessing_strategies/1/used_software/0/url", "https://github.com/sensein/b2aiprep"),
         c("/cleaning_strategies/0/cleaning_details", "manually checked for presence of unconsented speakers"),
         c("/missing_data_documentation/0/missing_data_causes")],
  absent=[a("labeling_strategies"), a("machine_annotation_tools"), a("imputation_protocols")])

q(12, "Collection Protocol Clarity", "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
  "numeric", 3, 5, "Good (mechanism + collectors, no timeframe)",
  "collection_mechanisms: reproschema-ui on tablets, headset vs built-in microphone, age-appropriate tasks; data_collectors: Hospital for Sick Children; raw_sources: Synapse syn73617068; direct_collection: single session. collection_timeframes absent: no collection start/end dates; acquisition_methods absent as a field.",
  "The 5 anchor requires timeframes, which are not documented.",
  "unknown", unk("data_collection"),
  cited=[c("/collection_mechanisms/0/mechanism_details", "customized software, reproschema-ui, on"),
         c("/data_collectors/0/name", "Hospital for Sick Children"),
         c("/raw_sources/0/access_url", "https://www.synapse.org/Synapse:syn73617068")],
  absent=[a("collection_timeframes"), a("acquisition_methods")],
  considered=["direct_collection", "sampling_strategies"])

q(13, "Version History, Maintenance, and Sustainability", "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access. Assess the preservation route appropriate to the domain and access conditions.",
  "numeric", 3, 5, "Good (version + access + persistent ID)",
  "version 1.1.0; version_access lists 1.0.0 and 1.1.0 with change summary and latest_version_doi doi:10.13026/mf9s-5r03; distribution_dates 2025-12-17 and 2026-05-01; DOI on PhysioNet. Absent: errata, updates plan, maintainers, publisher; no maintenance or preservation commitment. The latest_version_doi differs from the record DOI without explanation.",
  "Version history and persistent ID present; sustainability documentation missing.",
  "unknown", unk("shared_dataset"),
  cited=[c("version", "1.1.0"), c("version_access.version_details", "minor update with no new participants"),
         c("version_access.latest_version_doi", "doi:10.13026/mf9s-5r03"), c("doi")],
  absent=[a("errata"), a("updates"), a("maintainers"), a("publisher")],
  considered=["distribution_dates"])

q(14, "Associated Publications", "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources. The dataset need not belong to a named study or have a publication to document how it should be cited.",
  "numeric", 5, 5, "Excellent (formal citation + 2 distinct references)",
  "Formal dataset citation with authors, year, title, version, PhysioNet and DOI; distinct references: the dataset DOI and the project website https://b2ai-voice.org/ in external_resources. No associated journal publications.",
  "Meets the 5 anchor: formal dataset citation and at least two distinct references.",
  "applicable", ALWAYS,
  cited=[c("citation", "Bridge2AI-Voice Pediatric Dataset"), c("/external_resources/0/external_resources/0", "https://b2ai-voice.org/"), c("doi")])

q(15, "Human Subject Representation", "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups. Evaluate the represented population and stated use, not a predetermined clinical cohort.",
  "numeric", 3, 5, "Good (population + criteria, no demographics)",
  "instances: 300 participants aged 2-18; subpopulations: age groups Peds 10+, 6-10, 4-6, 2-4 (no counts); sampling_strategies: inclusion (2-18, English proficiency) and exclusion (over 18, non-verbal), patients and healthy volunteers; at_risk_populations: children. No distribution by sex, gender, race/ethnicity, diagnosis or patient vs volunteer, and no per-age-group counts, although demographic data are said to be released.",
  "Inclusion/exclusion criteria are present but demographic composition is not characterized, as the 5 anchor requires.",
  "unknown", unk("human_subjects"),
  cited=[c("/instances/1/description", "Participants aged 2-18"),
         c("/subpopulations/0/description", "Peds 10+, Peds 6-10, Peds 4-6 and Peds 2-4"),
         c("/sampling_strategies/0/strategies", "exclusion criteria included participants over 18 years of age"),
         c("at_risk_populations.description")],
  absent=[a("subsets")],
  considered=["missing_data_documentation"])

q(16, "Findability (Persistent Links)", "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
  "pass_fail", 1, 1, "Pass",
  "page https://physionet.org/content/b2ai-voice-pediatric/1.1.0/, DOI 10.13026/h995-bt35, external resource https://b2ai-voice.org/.",
  "Well-formed persistent and external URLs present.",
  "applicable", ALWAYS,
  cited=[c("page"), c("doi"), c("id"), c("external_resources")],
  absent=[a("download_url")])

q(17, "Accessibility (Access Mechanism)", "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
  "numeric", 5, 5, "Excellent (platform, login, policy)",
  "Platform PhysioNet (page); authorization: credentialed/registered user who signs the Bridge2AI Voice Registered Access Agreement, no training; raw audio via Synapse controlled access (DARF, DUA, DTUA signed by institutional official, DACO approval, DACO@b2ai-voice.org). The record uses both 'credentialed' and 'registered' for the PhysioNet tier; no download_url or distribution_formats.",
  "Access path fully defined across both tiers; tier terminology is mixed.",
  "unknown", unk("shared_dataset"),
  cited=[c("license_and_use_terms.license_terms", "only credentialed users who sign the data use agreement can"),
         c("data_governance.access_review_process", "register on PhysioNet and confirm"),
         c("/raw_sources/0/raw_data_details", "requires institutional sign-off")],
  absent=[a("download_url"), a("distribution_formats")])

q(18, "Reusability, Use Guidance, and Social Impact", "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis with risk identification and mitigation strategies (CROISSANT RAI aligned).",
  "numeric", 3, 5, "Good (license + basic use guidance)",
  "Named registered-access license and DUA; intended_uses lists three one-line uses (developmental norms, AI-driven early screening tools, clinical insight). No prohibited_uses, discouraged_uses or future_use_impacts; no social impact or mitigation analysis.",
  "License and basic intended uses only.",
  "applicable", ALWAYS,
  cited=[c("license_and_use_terms.license_terms"), c("/intended_uses/1/description", "AI-driven tools for early screening")],
  absent=[a("prohibited_uses"), a("discouraged_uses"), a("future_use_impacts")],
  counts=[{"path": "intended_uses", "claimed": 3}])

q(19, "Data Integrity, Provenance Graph, and Quality", "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation.",
  "numeric", 3, 5, "Good (version history, partial textual lineage)",
  "version_access with change summary; missing_data_documentation (removed features for sensitive records; ungenerated features); raw_sources (raw audio on Synapse); textual lineage raw audio -> b2aiprep -> Parquet and ReproSchema-UI -> REDCap -> BIDS. Absent: errata, updates, was_derived_from, parent_datasets, splits; no entity-activity-agent structure or derivation links.",
  "Version history and some textual lineage, but no full provenance graph.",
  "applicable", ALWAYS,
  cited=[c("version_access.versions_available"), c("/missing_data_documentation/0/missing_data_patterns", "have been removed from v1.1"),
         c("/raw_sources/0/raw_data_details", "This PhysioNet project does not contain raw audio.")],
  absent=[a("errata"), a("updates"), a("was_derived_from"), a("parent_datasets"), a("splits")],
  considered=["preprocessing_strategies"])

q(20, "Bias Documentation and Responsible AI Alignment", "Documentation of known biases, limitations and potential effects on intended or foreseeable uses. Every dataset has a scope that can be documented; absent bias fields do not make this question inapplicable.",
  "numeric", 0, 5, "Absent",
  "known_biases and future_use_impacts are absent. Facts with bias implications appear only incidentally (single-site recruitment at SickKids, English proficiency requirement, non-verbal children excluded, mixed headset/built-in tablet microphones) and are not identified as biases or limitations or linked to effects on use.",
  "No bias documentation.",
  "applicable", ALWAYS,
  absent=[a("known_biases"), a("future_use_impacts")],
  considered=["collection_mechanisms", "sampling_strategies"])

ISSUES = [
    dict(item_ids=["Q1"], score_effect="lowered", category="other", type="completeness",
         description="Top-level resources, parent_datasets and regulatory_restrictions.confidentiality_level are not populated (11/14 Q1 fields)."),
    dict(item_ids=["Q3"], score_effect="lowered", category="variables_metadata", type="completeness",
         description="Only 5 keywords, one generic ('health'); no terms for data types (spectrograms, acoustic features, speech) or controlled vocabulary."),
    dict(item_ids=["Q4"], score_effect="lowered", category="format_access", type="completeness",
         description="No distribution_formats or total_file_count; Parquet resources lack format/media_type; phenotype and metadata collections list no files or formats."),
    dict(item_ids=["Q8"], score_effect="lowered", category="privacy_regulatory", type="completeness",
         description="No is_deidentified, deidentification method for the pediatric derived data, data_protection_impacts or jurisdiction-appropriate compliance (data collected in Ontario, Canada; HIPAA phrasing is from the US umbrella protocol)."),
    dict(item_ids=["Q9"], score_effect="lowered", category="license_use_terms", type="completeness",
         description="No confidentiality classification (regulatory_restrictions.confidentiality_level), ip_restrictions or regulatory obligations; low-risk status appears only in sensitive_elements prose."),
    dict(item_ids=["Q10"], score_effect="lowered", category="format_access", type="completeness",
         description="No conforms_to/conforms_to_schema (BIDS/REDCap mentioned only in preprocessing prose) and no typed related_datasets."),
    dict(item_ids=["Q12"], score_effect="lowered", category="temporal_version", type="completeness",
         description="collection_timeframes absent; no collection start/end dates for the pediatric cohort."),
    dict(item_ids=["Q13"], score_effect="lowered", category="temporal_version", type="completeness",
         description="No errata, updates plan, maintainers or publisher; no maintenance or preservation commitment."),
    dict(item_ids=["Q15"], score_effect="lowered", category="bias_quality", type="completeness",
         description="No demographic composition (sex/gender, race/ethnicity, diagnosis, patient vs volunteer, per-age-group counts) despite stating that demographic data are released."),
    dict(item_ids=["Q18"], score_effect="lowered", category="license_use_terms", type="completeness",
         description="No prohibited_uses, discouraged_uses or future_use_impacts; intended uses are one-line statements with no social impact or mitigation analysis."),
    dict(item_ids=["Q19"], score_effect="lowered", category="processing_provenance", type="completeness",
         description="No was_derived_from, parent_datasets, errata, updates or splits; lineage is prose only, without entity-activity-agent structure."),
    dict(item_ids=["Q20"], score_effect="lowered", category="bias_quality", type="completeness",
         description="No known_biases or future_use_impacts; single-site recruitment, English-proficiency and non-verbal exclusions and mixed microphones are not identified as biases."),
    dict(item_ids=[], score_effect="noted_only", category="format_access", type="consistency",
         description="Access tier terminology is mixed: license_terms says 'only credentialed users' while data_governance describes registered access (register and confirm identity) with no training."),
    dict(item_ids=[], score_effect="noted_only", category="scope_drift", type="consistency",
         description="Compensation, retention, consent revocation, assent and reidentification-risk statements come from the US umbrella (USF) protocol rather than the pediatric SickKids release; attribution is disclosed but applicability to this cohort is unconfirmed."),
    dict(item_ids=[], score_effect="noted_only", category="persistent_identifier", type="consistency",
         description="version_access.latest_version_doi (10.13026/mf9s-5r03) differs from the record DOI (10.13026/h995-bt35) without explanation (possibly an all-versions DOI)."),
    dict(item_ids=[], score_effect="noted_only", category="source_conflict", type="content_accuracy",
         description="Grant 3OT2OD032720-01S1 (PhysioNet) vs 3OT2OD032720-01S3 (NIH RePORTER); the conflict is disclosed in funders source_caveats and both match the NIH pattern."),
    dict(item_ids=[], score_effect="noted_only", category="processing_provenance", type="completeness",
         description="openSMILE, Praat, parselmouth and torchaudio have no versions, and the deep learning model used for EMA estimation is unnamed."),
]

EXTRAS = [
    ("medium", ["resources", "parent_datasets", "regulatory_restrictions"], "Populate regulatory_restrictions.confidentiality_level and link resources/parent_datasets where the sources support them."),
    ("low", ["keywords"], "Add data-type and domain terms (e.g., acoustic features, spectrograms, speech, pediatric voice) from a controlled vocabulary."),
    ("medium", ["distribution_formats", "total_file_count", "file_collections"], "Declare distribution_formats and per-resource format/media_type, total file count, and enumerate phenotype/metadata files."),
    ("high", ["is_deidentified", "data_protection_impacts", "regulatory_restrictions", "participant_privacy"], "Document the deidentification method for the pediatric release, a data protection impact assessment, and the applicable Canadian/Ontario framework."),
    ("medium", ["regulatory_restrictions", "ip_restrictions", "data_protection_impacts"], "Record a confidentiality classification, IP restrictions and regulatory obligations as structured fields."),
    ("medium", ["conforms_to", "conforms_to_schema", "related_datasets"], "State schema conformance (e.g., BIDS, data dictionaries) and typed relationships to related datasets when the sources establish them."),
    ("medium", ["collection_timeframes"], "Add the pediatric collection period from the sources."),
    ("medium", ["errata", "updates", "maintainers", "publisher"], "Add maintainers, publisher, an update plan and an errata route."),
    ("medium", ["instances", "subpopulations", "subsets"], "Characterize participant demographics and per-age-group counts."),
    ("high", ["prohibited_uses", "discouraged_uses", "future_use_impacts"], "Document prohibited and discouraged uses (e.g., re-identification attempts) and foreseeable impacts with mitigations."),
    ("medium", ["was_derived_from", "parent_datasets", "errata", "updates", "splits"], "Represent derivation from raw audio and the processing chain as structured provenance."),
    ("high", ["known_biases", "future_use_impacts"], "Document known biases (single-site, English-only, non-verbal exclusion, device heterogeneity) and their effects on uses."),
    ("low", ["license_and_use_terms", "data_governance"], "Use one access-tier term consistent with the PhysioNet access policy."),
    ("low", ["participant_compensation", "retention_limit", "consent_revocations", "participant_privacy"], "Confirm whether umbrella-protocol statements apply to the SickKids pediatric cohort."),
    ("low", ["version_access", "doi"], "Explain the role of latest_version_doi relative to the versioned DOI."),
    ("low", ["funders"], "Resolve which supplement award funded the pediatric release."),
    ("low", ["preprocessing_strategies"], "Add versions for feature extraction tools and name the EMA model."),
]
for _i, (_sev, _f, _r) in zip(ISSUES, EXTRAS):
    _i.update(severity=_sev, fields_involved=_f, recommendation=_r)
assert len(EXTRAS) == len(ISSUES)


def main():
    by_cat = [("Structural Completeness", 1, 5, 21), ("Metadata Quality & Content", 6, 10, 21),
              ("Technical Documentation", 11, 15, 25), ("FAIRness & Accessibility", 16, 20, 21)]
    cats = []
    for name, lo, hi, mx in by_cat:
        qs = [x for x in Q if lo <= x["id"] <= hi]
        cats.append({"name": name, "questions": qs,
                     "category_score": sum(x["score"] for x in qs if x["score"] is not None),
                     "category_max": mx})
    total = sum(c_["category_score"] for c_ in cats)
    excluded = sum(x["max_score"] for x in Q if not x["applicable"])
    adj = 88 - excluded
    ctx = normalize_context({})
    out = {
        "rubric": "rubric20-semantic", "version": "3.0", "d4d_file": str(D4D),
        "project": "VOICE_PEDIATRIC", "method": "claudecode_agent",
        "evaluation_timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": {"name": "claude-opus-5-5", "temperature": None,
                  "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
                  "evaluation_type": "semantic_llm_judge"},
        "overall_score": {"total_points": total, "max_points": 88, "excluded_max_points": excluded,
                          "adjusted_max_points": adj,
                          "normalized_percentage": round(total / adj * 100, 2),
                          "fixed_percentage": round(total / 88 * 100, 2),
                          "questions_not_applicable": sum(1 for x in Q if not x["applicable"])},
        "categories": cats,
        "semantic_analysis": {
            "issues_detected": ISSUES,
            "semantic_insights": [
                "Record is explicit about source scope: adult-dataset and umbrella-protocol facts are flagged in source_caveats rather than silently merged.",
                "Human-subjects logic holds: involves_human_subjects true with ethical_reviews and informed_consent populated, pediatric assent and guardian consent documented.",
                "Temporal ordering is consistent: v1.0.0 2025-12-17, v1.1.0 2026-05-01 matches issued; raw-audio announcement 2026-03-09 between releases.",
                "Two-tier access (registered features vs controlled raw audio with DACO review) is coherent with the low-risk derived-feature release and the voice reidentification risk.",
                "Largest gaps are responsible-AI content (biases, prohibited/discouraged uses, impacts) and structured governance/regulatory classification.",
            ],
            "consistency_checks": {"passed": 6, "failed": 0, "warnings": 4},
            "correctness_validations": {
                "doi_format": "valid: 10.13026/h995-bt35 (PhysioNet prefix); latest_version_doi 10.13026/mf9s-5r03 also well-formed",
                "grant_number_format": "valid NIH pattern: 3OT2OD032720-01S1 (supplement to OT2OD032720); RePORTER conflict with -01S3 disclosed",
                "rrid_format": "valid: RRID:SCR_007345 in citation",
                "url_validity": "valid structure: physionet.org, b2ai-voice.org, github.com/sensein/b2aiprep, synapse.org",
            },
        },
        "applicability_context": ctx,
        "evaluation_scope": {"policy": "single_dataset",
                             "units": [{"path": "#", "id": "doi:10.13026/h995-bt35"}],
                             "collection_metadata_inherited": False},
        "metadata": {
            "evaluator_id": "claude-opus-5-5",
            "evaluator_model": "claude-opus-5-5",
            "method_label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2",
            "instrument_sha256": sha(AGENT),
            "evidence_authority_sha256": sha(AUTH),
            "rubric_sha256": sha(RUBRIC),
            "input_sha256": sha(D4D),
            "context_sha256": context_digest(ctx),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(OUT, total, adj)


if __name__ == "__main__":
    main()
