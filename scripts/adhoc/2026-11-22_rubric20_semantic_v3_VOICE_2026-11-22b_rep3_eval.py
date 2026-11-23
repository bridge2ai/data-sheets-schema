#!/usr/bin/env python3
"""Write the rubric20-semantic v3 evaluation of one VOICE D4D record.

Purpose: serialize the evaluator's own judgements (made by reading the record)
for VOICE, label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3, into
the version-3.0 JSON contract of .claude/agents/d4d-rubric20-semantic.md.
Inputs: the D4D record (hashed only), the agent definition, rubric20.txt and the
evidence authority (hashed only). No caller context: empty applicability_context.
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/
VOICE_2026-11-22b_rep3_evaluation.json
Date: 2026-11-22. Evaluator: claude-opus-5-5 (Claude Code session).
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_d4d.yaml"
OUT = ROOT / "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/VOICE_2026-11-22b_rep3_evaluation.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


CONTEXT = {}
CONTEXT_SHA = hashlib.sha256(json.dumps({"version": "d4d-evaluation-context-1", "predicates": CONTEXT},
                                        sort_keys=True).encode()).hexdigest()

ALWAYS = ("applicable", "This item applies to every dataset")


def unk(pred):
    return ("unknown", f"{pred}: not declared by the caller (no context supplied); retained in the denominator")


def c(path, quote=None):
    return {"path": path, "quote": quote} if quote else {"path": path}


def a(path):
    return {"path": path}


def n(path, claimed):
    return {"path": path, "claimed": claimed}


# (id, name, desc, type, score, label, evidence, note, applicability, cited, absent, counts, considered, no_issue_reason)
Q = []


def q(i, name, desc, stype, score, label, evidence, note, appl, cited=(), absent=(), counts=(), considered=(), reason=None):
    Q.append(dict(id=i, name=name, description=desc, stype=stype, score=score, label=label, evidence=evidence,
                  note=note, appl=appl, cited=list(cited), absent=list(absent), counts=list(counts),
                  considered=list(considered), reason=reason))


q(1, "Field Completeness",
  "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and c",
  "numeric", 3, "Good (~71% populated)",
  "Populated: id, title, description, keywords, license_and_use_terms, doi, page, creators, purposes, instances (10/14). "
  "Absent: top-level resources, parent_datasets, variables, regulatory_restrictions.confidentiality_level.",
  "10 of 14 listed fields carry meaningful content (71%), the ~70% band. Files are enumerated under file_collections "
  "rather than resources, and no variable-level schema or confidentiality classification is given.",
  ALWAYS,
  [c("id", "doi:10.13026/37yb-1t42"), c("title"), c("description"), c("keywords"), c("license_and_use_terms"),
   c("doi"), c("page"), c("creators"), c("purposes"), c("instances"), c("regulatory_restrictions")],
  [a("resources"), a("parent_datasets"), a("variables"), a("regulatory_restrictions.confidentiality_level")],
  [n("keywords", 4), n("creators", 122), n("purposes", 4)],
  ["file_collections"])

q(2, "Entry Length Adequacy", "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
  "numeric", 5, "Excellent (>200 chars)",
  "description is ~766 characters; the four purposes responses are 157-239 characters each (mean ~200), e.g. "
  "'Bridge2AI-Voice seeks to create a flagship, standardized, and ethically sourced dataset of 10,000 voices'.",
  "Narrative fields are substantive; combined average well above 200 characters, and content is dataset-specific "
  "(release version, participant count, sites, derived-feature-only content).",
  ALWAYS,
  [c("description", "Version 3.1.0 contains data for 833 participants across five sites in North America"),
   c("/purposes/1/response", "dataset of 10,000 voices linked to health information")],
  [], [n("purposes", 4)], [])

q(3, "Keyword Diversity",
  "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply addit",
  "numeric", 3, "Good (3-7 keywords)",
  "keywords: health, biomarkers, bridge2ai, voice (4 terms).",
  "Four generic keywords; no condition, modality (e.g. spectrogram, acoustic features) or method terms despite rich "
  "content elsewhere. Falls in the 3-7 band.",
  ALWAYS,
  [c("/keywords/3", "voice")], [], [n("keywords", 4)], [])

q(4, "File Enumeration and Type Variety",
  "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in sep",
  "numeric", 3, "Good (2-3 file types)",
  "file_collections: features (9 Parquet files + 2 TSV, format TSV / text/tab-separated-values), metadata (Parquet + "
  "data dictionary), phenotype ('TSV data files with JSON data dictionaries'). distribution_formats and "
  "total_file_count absent.",
  "Three file types are documented (Parquet, TSV, JSON dictionaries). Parquet files have no format/media_type field; "
  "formats are given only in prose. Raw audio (BIDS) is a separate controlled-access resource, not part of this release.",
  ALWAYS,
  [c("/file_collections/0/resources/9/format", "TSV"),
   c("/file_collections/0/description", "Binary files are made available as Parquet"),
   c("/file_collections/2/description", "in TSV data files with JSON data dictionaries")],
  [a("distribution_formats"), a("total_file_count")],
  [n("file_collections", 3), n("/file_collections/0/resources", 11)],
  ["file_collections"])

q(5, "Data File Size Availability", "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
  "pass_fail", 1, "Pass",
  "instances[0].counts: 833 persons; per-file record counts in file descriptions (e.g. ppgs.parquet n=29289). No byte sizes.",
  "Instance counts present (pass). No total_size_bytes or per-file bytes, so download size cannot be determined.",
  ALWAYS,
  [c("/instances/0/counts"), c("/file_collections/0/resources/0/description", "n=29289")],
  [a("total_size_bytes")], [], [])

q(6, "Dataset Identification Metadata",
  "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or ",
  "pass_fail", 1, "Pass",
  "doi: 10.13026/37yb-1t42 (PhysioNet prefix); page: https://physionet.org/content/b2ai-voice/3.1.0/; citation includes "
  "'PhysioNet. RRID:SCR_007345'. publisher field absent.",
  "Valid PhysioNet DOI and hosting platform identifiable from page/citation. Minor: publisher not a structured field; "
  "the citation's DOI (8xbn-nq66) differs from the record DOI (37yb-1t42), explained only implicitly by latest_version_doi.",
  ALWAYS,
  [c("doi", "10.13026/37yb-1t42"), c("page", "physionet.org"), c("id"), c("citation", "RRID:SCR_007345")],
  [a("publisher")], [], [])

q(7, "Funding and Acknowledgements Completeness",
  "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
  "numeric", 3, "Good (funders with grants; creator affiliations largely missing)",
  "funders: NIH Common Fund Bridge2AI Program, grants OT2OD032720 and 3OT2OD032720-01S1. creators: 122 names; only "
  "the two principal investigators carry affiliations (University of South Florida; Weill Cornell Medicine).",
  "Grant numbers match the NIH OT2 activity-code pattern and the supplement suffix is explained. However 120 of 122 "
  "creators have no affiliation, so the 'creators with affiliations' half of the 5-point anchor is not met. "
  "Borderline between 3 and 5; recorded as 3.",
  ALWAYS,
  [c("/funders/0/grants/0/grant_number", "OT2OD032720"), c("/funders/0/grantor", "NIH Common Fund"),
   c("/creators/0/principal_investigator/affiliation/0/name", "University of South Florida"),
   c("/creators/3/principal_investigator/affiliation/0/name", "Weill Cornell Medicine")],
  [], [n("creators", 122), n("/funders/0/grants", 2)], ["funders", "creators"])

q(8, "Ethical and Privacy Declarations",
  "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks,",
  "numeric", 5, "Excellent (comprehensive human-subjects protections)",
  "involves_human_subjects: true; ethical_reviews: USF IRB (single IRB with subsites); informed_consent with scope and "
  "documentation modes; consent_revocations; is_deidentified with HIPAA Safe Harbor method and removed identifiers; "
  "participant_privacy.reidentification_risk ('does not achieve K-anonymization (k>=2)'); participant_compensation "
  "($40/$80, max $120); regulatory_restrictions.other_compliance (Certificate of Confidentiality).",
  "Comprehensive and internally consistent: human-subjects flag aligns with IRB, consent and deidentification; "
  "residual re-identification risk is candidly stated and matches the registered/controlled access split. Gaps noted "
  "without deduction: at_risk_populations and a formal data_protection_impacts entry are absent; hipaa_compliant not "
  "stated as a field.",
  unk("human_subjects"),
  [c("/human_subject_research/involves_human_subjects"),
   c("/ethical_reviews/0/reviewing_organization", "University of South Florida Institutional Review Board"),
   c("/is_deidentified/method", "HIPAA Safe Harbor identifiers were removed"),
   c("/participant_privacy/0/reidentification_risk", "does not achieve K-anonymization (k>=2)"),
   c("/informed_consent/0/consent_scope"), c("/participant_compensation/0/compensation_amount"),
   c("/regulatory_restrictions/other_compliance", "Certificate of Confidentiality")],
  [a("at_risk_populations"), a("data_protection_impacts"), a("regulatory_restrictions.hipaa_compliant")],
  [], ["consent_revocations", "sensitive_elements"])

q(9, "Access Requirements and Governance Documentation",
  "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confid",
  "numeric", 3, "Good (license and restrictions; no confidentiality classification)",
  "license: Bridge2AI Voice Registered Access License; license_terms describe registration + Registered Access "
  "Agreement; ip_restrictions (4 items); data_governance (DACO, DARF/DUA/DTUA for raw audio); "
  "regulatory_restrictions.other_compliance: Certificate of Confidentiality. confidentiality_level and "
  "governance_committee_contact absent (DACO email appears only in raw_sources.raw_data_details).",
  "Licence and restrictions are well documented, but the 5-point anchor requires a confidentiality classification, "
  "which is not given as a field; the governance contact is not structured. Licence text also mixes tiers "
  "('Only credentialed users who sign the DUA' vs registration with 'no training is required').",
  ALWAYS,
  [c("license", "Bridge2AI Voice Registered Access License"),
   c("/license_and_use_terms/license_terms", "Only credentialed users who sign the DUA can access the files"),
   c("/ip_restrictions/restrictions/1", "Sale of all or part of the Data on any media is not permitted."),
   c("/data_governance/committee_name", "Data Access Compliance Office (DACO)"),
   c("/regulatory_restrictions/other_compliance")],
  [a("regulatory_restrictions.confidentiality_level"), a("regulatory_restrictions.governance_committee_contact"),
   a("data_protection_impacts"), a("regulatory_restrictions.hipaa_compliant")],
  [], ["raw_sources"])

q(10, "Interoperability, Standardization, and Cross-Platform Integration",
  "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedure",
  "numeric", 3, "Good (standard formats, no schema conformance for the release)",
  "Parquet and TSV with JSON data dictionaries; related_datasets typed 'references' (pediatric dataset); external "
  "resources include the REDCap data dictionary; BIDS v1.9.0 stated only for the controlled-access raw audio; "
  "labels 'Per Bridge2AI Protocols and ICD-10 codes'. conforms_to, conforms_to_schema, distribution_formats absent.",
  "Open standard formats and per-file dictionaries support reuse, but the released feature files declare no schema "
  "or ontology conformance; BIDS applies to a different (raw) resource. 3-point band.",
  unk("shared_dataset"),
  [c("/file_collections/0/description", "All files are associated with a data dictionary file"),
   c("/related_datasets/0/relationship_type", "references"),
   c("/raw_sources/0/raw_data_details", "Brain Imaging Data Structure v1.9.0"),
   c("/external_resources/0/external_resources/0")],
  [a("conforms_to"), a("conforms_to_schema"), a("distribution_formats"), a("compression")],
  [], ["labeling_strategies"])

q(11, "Tool and Software Transparency",
  "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versio",
  "numeric", 5, "Excellent (strategies with versions/URLs)",
  "preprocessing_strategies: b2aiprep v3.0.0 (https://github.com/sensein/b2aiprep), SenseLab URL, OpenSMILE, "
  "Parselmouth/Praat, torchaudio, sparc, ppgs, with signal parameters (16 kHz, 25ms window, 10ms hop, 400-point FFT, "
  "60 MFCCs); cleaning_strategies audit protocol; labeling_strategies (clinician diagnosis, ICD-10); "
  "machine_annotation_tools: Whisper Large.",
  "Comprehensive and reproducible-level processing documentation with a versioned, linked pipeline. Minor: Whisper "
  "version recorded as 'unknown'; several feature libraries unversioned; no imputation protocol (handling of missing "
  "rows is described).",
  unk("data_processing"),
  [c("/preprocessing_strategies/0/used_software/0/version", "3.0.0"),
   c("/preprocessing_strategies/0/used_software/0/url", "https://github.com/sensein/b2aiprep"),
   c("/preprocessing_strategies/2/preprocessing_details", "400-point FFT"),
   c("/cleaning_strategies/0/cleaning_details"), c("/labeling_strategies/0/data_annotation_protocol"),
   c("/machine_annotation_tools/0/tools/0", "OpenAI Whisper Large unknown")],
  [a("imputation_protocols"), a("annotation_analyses")],
  [n("preprocessing_strategies", 3)], ["missing_data_documentation"])

q(12, "Collection Protocol Clarity",
  "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timef",
  "numeric", 5, "Excellent (methods, collectors, timeframe)",
  "collection_mechanisms: Bridge2AI-Voice App (22 acoustic tasks, questionnaires, EHR link) and hardware (iPad models, "
  "Avid AE-36 microphone); data_collectors: trained research assistants in clinic; acquisition_methods (directly "
  "observed, self-reported, clinician-validated); collection_timeframes: 12 months; raw_sources: raw audio via Synapse.",
  "Full protocol present. Weakness noted: the 12-month timeframe is caveated as not tied to release 3.1.0 and gives no "
  "dates; a two-sentence app/tablet discrepancy is acknowledged in the record.",
  unk("data_collection"),
  [c("/collection_mechanisms/0/mechanism_details", "A total of 22 acoustic tasks are recorded through the app."),
   c("/collection_mechanisms/1/mechanism_details", "Avid AE-36 microphone"),
   c("/data_collectors/0/description", "trained research assistant"),
   c("/collection_timeframes/0/timeframe_details", "collected over a period of 12 months"),
   c("/acquisition_methods/0/acquisition_details"), c("/raw_sources/0/access_url")],
  [a("raw_data_sources")], [], ["direct_collection", "sampling_strategies"])

q(13, "Version History, Maintenance, and Sustainability",
  "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durab",
  "numeric", 5, "Excellent (versioning + repository + commitment)",
  "version 3.1.0; distribution_dates for 1.1-3.1.0; version_access with per-version DOIs and release notes; errata "
  "(broken parquet files fixed); updates semi-annual; retention 'possibly indefinitely'; 'older versions continue to "
  "be supported, hosted'; DACO governance. maintainers and publisher absent.",
  "Versioning and sustainability are comprehensive. Noted without deduction: no maintainer contact; version DOIs "
  "for 2.0.0/2.0.1 missing; healthsheet points to Health Data Nexus while releases are on PhysioNet (caveated).",
  unk("shared_dataset"),
  [c("version", "3.1.0"), c("/version_access/latest_version_doi"),
   c("/version_access/version_details", "older versions continue to be supported, hosted, and made available"),
   c("/errata/0/erratum_details"), c("/updates/frequency"), c("doi")],
  [a("maintainers"), a("publisher")],
  [n("/version_access/versions_available", 4), n("/distribution_dates/0/release_dates", 5)],
  ["retention_limit", "data_governance"])

q(14, "Associated Publications",
  "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resourc",
  "numeric", 5, "Excellent (formal citation + multiple references)",
  "citation: 'Bensoussan, Y., ... (2026). Bridge2AI-Voice: An ethically-sourced, diverse voice dataset linked to "
  "health information (version 3.1.0). PhysioNet. ...'; external_resources: GitHub REDCap repo, Zenodo DOIs, Front "
  "Digit Health 2025 paper (10.3389/fdgth.2025.1514971), Interspeech 2024 paper.",
  "Formal dataset citation with title, authors, publisher and DOI plus several distinct references. Note: the "
  "citation DOI differs from the record DOI (see issue); the publication DOI lacks a resolver prefix.",
  ALWAYS,
  [c("citation", "Bridge2AI-Voice: An ethically-sourced, diverse voice dataset linked to health information (version 3.1.0)"),
   c("/external_resources/1/external_resources/0", "10.3389/fdgth.2025.1514971"),
   c("/external_resources/2/external_resources/0")],
  [], [n("external_resources", 4)], ["doi"])

q(15, "Human Subject Representation",
  "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups. Evaluate ",
  "numeric", 3, "Good (inclusion/exclusion given; no demographic distributions)",
  "instances: 833 persons with diagnostic-category labels; subpopulations.identification: 'Age, Gender, Sex, "
  "Ethnicity, Socioeconomic status'; sampling_strategies gives recruitment from high-volume expert clinics, age "
  "18-120, healthy volunteers accepted, English and surgical-intervention exclusions.",
  "Recruitment and inclusion/exclusion are well described, but subgroups are only named, with no counts or "
  "distributions by age, sex, race/ethnicity or disease cohort, so 'detailed demographics' is not met. "
  "at_risk_populations absent.",
  unk("human_subjects"),
  [c("/instances/0/counts"), c("/subpopulations/0/identification", "Age, Gender, Sex, Ethnicity, Socioeconomic status"),
   c("/sampling_strategies/0/description", "a minimum age of 18 years, a maximum age of 120 years"),
   c("/missing_data_documentation/0/missing_data_patterns")],
  [a("at_risk_populations"), a("subsets")],
  [], ["known_biases", "sensitive_elements"])

q(16, "Findability (Persistent Links)", "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
  "pass_fail", 1, "Pass",
  "page https://physionet.org/content/b2ai-voice/3.1.0/; doi 10.13026/37yb-1t42; external_resources URLs.",
  "Well-formed PhysioNet URL and DOI present. download_url absent.",
  ALWAYS,
  [c("page"), c("doi"), c("/external_resources/0/external_resources/0", "https://github.com/eipm/bridge2ai-redcap")],
  [a("download_url")], [], [])

q(17, "Accessibility (Access Mechanism)",
  "Describes how users can obtain the dataset (download URL, distribution formats, access policy).\nNote: \"Public\" does not ",
  "numeric", 3, "Good (access path described but tier statements conflict)",
  "license_terms: 'Only credentialed users who sign the DUA can access the files. Access requires registration on "
  "PhysioNet and signing the Bridge2AI Voice Registered Access Agreement ... no training is required.' Raw audio: "
  "DARF + DUA to DACO, DTUA, Synapse. download_url and distribution_formats absent.",
  "Platform, agreement and the separate controlled-access route are described, but the same field calls the "
  "requirement both 'credentialed' and registration-only, which are distinct access tiers; no download URL. "
  "Not a fully defined access path.",
  unk("shared_dataset"),
  [c("/license_and_use_terms/license_terms", "Access requires registration on PhysioNet"),
   c("/data_governance/access_review_process", "complete the Data Access Request Form (DARF)"),
   c("/raw_sources/0/access_url")],
  [a("download_url"), a("distribution_formats")], [], ["page", "license"])

q(18, "Reusability, Use Guidance, and Social Impact",
  "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND co",
  "numeric", 3, "Good (license + use guidance; no social impact analysis)",
  "intended_uses (2), prohibited_uses (3: re-identification, harm/stigmatization, contacting subjects), "
  "discouraged_uses (hiring, insurance, surveillance). future_use_impacts absent.",
  "Use guidance is explicit across intended/prohibited/discouraged uses, but there is no structured social-impact "
  "analysis with risks and mitigations (future_use_impacts absent); only a one-line rationale under discouraged uses.",
  ALWAYS,
  [c("/intended_uses/0/description"), c("/prohibited_uses/0/description", "Attempting to re-identify research participants"),
   c("/discouraged_uses/0/description", "hiring decisions, insurance premium"), c("license_and_use_terms")],
  [a("future_use_impacts")], [n("prohibited_uses", 3), n("intended_uses", 2)], ["license"])

q(19, "Data Integrity, Provenance Graph, and Quality",
  "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation",
  "numeric", 3, "Good (version history + textual lineage; incomplete derivation paths)",
  "version_access, errata, updates; raw_sources (raw audio, controlled access) and preprocessing lineage (REDCap export "
  "via b2aiprep, monaural/16 kHz, feature extraction); missing_data_documentation (2). was_derived_from, "
  "parent_datasets, splits absent.",
  "Strong version history and a partial textual processing lineage, but no explicit derivation links, agents for "
  "processing activities are not identified beyond 'the data release team', and the record itself states it cannot "
  "establish whether 3.1.0 contains transcriptions. Not a complete provenance account.",
  ALWAYS,
  [c("/version_access/version_details", "v3.1.0 was a minor update with no new participants"),
   c("/errata/0/erratum_details"), c("/raw_sources/0/description"),
   c("/content_warnings/0/source_caveats", "whether release 3.1.0 contains any transcriptions is not established"),
   c("/missing_data_documentation/1/missing_data_causes")],
  [a("was_derived_from"), a("parent_datasets"), a("splits"), a("raw_data_sources")],
  [n("missing_data_documentation", 2)], ["updates", "preprocessing_strategies", "cleaning_strategies"])

q(20, "Bias Documentation and Responsible AI Alignment",
  "Documentation of known biases, limitations and potential effects on intended or foreseeable uses. Every dataset has a sc",
  "numeric", 3, "Good (bias identification without taxonomy)",
  "known_biases (3): recruitment trust/proximity, site-device confounding, skews by disorder/site/demographics (with "
  "mitigation advice); known_limitations (5). No bias_type taxonomy; future_use_impacts absent.",
  "Concrete, dataset-specific biases are identified but not categorized with a standard taxonomy and without a "
  "fairness analysis.",
  ALWAYS,
  [c("/known_biases/0/bias_description", "less trust in the medical system"),
   c("/known_biases/2/mitigation_strategy"), c("/known_limitations/1/limitation_description")],
  [a("future_use_impacts"), a("bias_type")], [n("known_biases", 3), n("known_limitations", 5)], [])

ISSUES = [
    dict(item_ids=["Q1"], score_effect="lowered", category="variables_metadata", type="completeness",
         description="No variables, parent_datasets, top-level resources or confidentiality_level fields."),
    dict(item_ids=["Q3"], score_effect="lowered", category="variables_metadata", type="completeness",
         description="Only four generic keywords; no condition, modality or method terms."),
    dict(item_ids=["Q4"], score_effect="lowered", category="format_access", type="completeness",
         description="Only Parquet, TSV and JSON are documented; distribution_formats absent and Parquet files lack format/media_type fields."),
    dict(item_ids=["Q7"], score_effect="lowered", category="attribution", type="completeness",
         description="120 of 122 creators lack affiliations; only the two PIs are affiliated."),
    dict(item_ids=["Q9"], score_effect="lowered", category="license_use_terms", type="completeness",
         description="No confidentiality classification or structured governance contact (DACO email only inside raw_sources)."),
    dict(item_ids=["Q9", "Q17"], score_effect="lowered", category="license_use_terms", type="consistency",
         description="license_terms says 'Only credentialed users who sign the DUA' and also registration-only with 'no training is required'; credentialed and registered are different access tiers."),
    dict(item_ids=["Q10"], score_effect="lowered", category="format_access", type="completeness",
         description="Released feature files declare no schema/ontology conformance; BIDS applies only to controlled-access raw audio."),
    dict(item_ids=["Q15"], score_effect="lowered", category="bias_quality", type="completeness",
         description="Subpopulations are named but no demographic counts or distributions are given."),
    dict(item_ids=["Q18"], score_effect="lowered", category="license_use_terms", type="completeness",
         description="No future_use_impacts / social-impact analysis with mitigations."),
    dict(item_ids=["Q19"], score_effect="lowered", category="processing_provenance", type="completeness",
         description="No explicit derivation links or processing agents; record cannot establish whether 3.1.0 contains transcriptions."),
    dict(item_ids=["Q20"], score_effect="lowered", category="bias_quality", type="completeness",
         description="Biases not categorized with a standard taxonomy; no fairness analysis."),
    dict(item_ids=[], score_effect="noted_only", category="persistent_identifier", type="consistency",
         description="Record doi/id is 10.13026/37yb-1t42 while the citation and versions_available give 10.13026/8xbn-nq66 for 3.1.0; plausibly latest-version vs version DOI, but not stated explicitly."),
    dict(item_ids=[], score_effect="noted_only", category="temporal_version", type="consistency",
         description="Collection timeframe '12 months' is untied to a release; releases span 2024-2026 with 833 participants accumulated across versions."),
    dict(item_ids=[], score_effect="noted_only", category="privacy_regulatory", type="completeness",
         description="at_risk_populations, data_protection_impacts and hipaa_compliant absent despite HIPAA Safe Harbor deidentification."),
    dict(item_ids=[], score_effect="noted_only", category="temporal_version", type="completeness",
         description="No maintainers; version DOIs for 2.0.0 and 2.0.1 missing."),
]

EXTRA = [
    ("medium", ["variables", "parent_datasets", "resources", "regulatory_restrictions.confidentiality_level"],
     "Add a variables list (or link to the data dictionaries), structured resources and a confidentiality level."),
    ("low", ["keywords"], "Add condition-category, modality and method keywords (e.g. voice disorders, spectrogram, acoustic features)."),
    ("low", ["distribution_formats", "file_collections"], "Declare distribution_formats and give format/media_type for every Parquet and JSON file."),
    ("medium", ["creators"], "Add affiliations for all creators."),
    ("medium", ["regulatory_restrictions.confidentiality_level", "regulatory_restrictions.governance_committee_contact"],
     "State the confidentiality level and move the DACO contact into governance_committee_contact."),
    ("high", ["license_and_use_terms.license_terms", "license"],
     "Resolve whether access is credentialed or registered and state a single tier."),
    ("medium", ["conforms_to", "conforms_to_schema"], "Declare the data-dictionary schema or standard the released feature files conform to."),
    ("medium", ["subpopulations", "instances"], "Report participant counts by age, sex, race/ethnicity and disease cohort."),
    ("medium", ["future_use_impacts"], "Add a social-impact analysis with risks and mitigation strategies."),
    ("medium", ["was_derived_from", "parent_datasets", "raw_sources"], "Link the release to its raw source and prior version and name processing agents."),
    ("low", ["known_biases"], "Classify biases with a standard taxonomy (bias_type) and add fairness analysis."),
    ("low", ["doi", "id", "citation", "version_access.versions_available"], "State explicitly which DOI is the version DOI and which is the latest-version DOI."),
    ("low", ["collection_timeframes"], "Give collection start/end dates for the participants in release 3.1.0."),
    ("low", ["at_risk_populations", "data_protection_impacts", "regulatory_restrictions.hipaa_compliant"], "Document vulnerable populations, a data protection impact assessment and HIPAA status."),
    ("low", ["maintainers", "version_access"], "Name maintainers and list DOIs for every version."),
]
for issue, (sev, fields, rec) in zip(ISSUES, EXTRA, strict=True):
    issue.update(severity=sev, fields_involved=fields, recommendation=rec)

CATS = [("Structural Completeness", range(1, 6)), ("Metadata Quality & Content", range(6, 11)),
        ("Technical Documentation", range(11, 16)), ("FAIRness & Accessibility", range(16, 21))]

byid = {x["id"]: x for x in Q}
categories = []
total = 0
for cname, ids in CATS:
    qs, cs, cm = [], 0, 0
    for i in ids:
        x = byid[i]
        mx = 1 if x["stype"] == "pass_fail" else 5
        status, aev = x["appl"]
        row = {"path": "#", "score": x["score"], "evidence": x["evidence"], "cited": x["cited"],
               "absent": x["absent"], "counts": x["counts"], "considered": x["considered"]}
        item = {"id": i, "name": x["name"], "description": x["description"], "score_type": x["stype"],
                "score": x["score"], "max_score": mx, "score_label": x["label"], "evidence": x["evidence"],
                "quality_note": x["note"], "applicable": True, "applicability_status": status,
                "applicability_evidence": aev, "unit_scores": [row]}
        if x["reason"]:
            item["no_issue_reason"] = x["reason"]
        qs.append(item)
        cs += x["score"]
        cm += mx
    total += cs
    categories.append({"name": cname, "questions": qs, "category_score": cs, "category_max": cm})

result = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": str(REC.relative_to(ROOT)),
    "project": "VOICE",
    "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {"name": "claude-opus-5-5", "evaluator_model": "claude-opus-5-5", "temperature": None,
              "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
              "evaluation_type": "semantic_llm_judge"},
    "overall_score": {"total_points": total, "max_points": 88, "excluded_max_points": 0,
                      "adjusted_max_points": 88, "normalized_percentage": round(total / 88 * 100, 1),
                      "fixed_percentage": round(total / 88 * 100, 1), "questions_not_applicable": 0,
                      "excluded_item_ids": []},
    "categories": categories,
    "semantic_analysis": {
        "issues_detected": ISSUES,
        "semantic_insights": [
            "Human-subjects logic is consistent: involves_human_subjects=true is backed by IRB review, consent scope, revocation, deidentification method and an explicit residual re-identification risk.",
            "Processing documentation is unusually concrete (versioned b2aiprep pipeline, signal-processing parameters), but provenance remains textual without derivation links.",
            "Source conflicts (target sizes, transcription inclusion, platform) are surfaced as caveats rather than silently resolved.",
            "Access tier wording conflicts (credentialed vs registered) in the licence terms.",
        ],
        "consistency_checks": {"passed": 6, "failed": 1, "warnings": 3},
        "correctness_validations": {
            "doi_format": "valid (10.13026/ PhysioNet prefix; record DOI differs from citation DOI, see issue)",
            "grant_number_format": "valid (OT2OD032720 matches NIH OT2 pattern; 3OT2OD032720-01S1 supplement form)",
            "rrid_format": "valid (RRID:SCR_007345 in citation)",
            "url_validity": "plausible (physionet.org, github.com, zenodo.org, synapse.org, isca-archive.org)",
        },
    },
    "applicability_context": CONTEXT,
    "evaluation_scope": {"policy": "single_dataset", "units": [{"path": "#", "id": "doi:10.13026/37yb-1t42"}],
                         "collection_metadata_inherited": False},
    "metadata": {
        "instrument_sha256": sha(ROOT / ".claude/agents/d4d-rubric20-semantic.md"),
        "evidence_authority_sha256": sha(ROOT / "data/rubric/semantic_evidence_authority_v3.json"),
        "rubric_sha256": sha(ROOT / "data/rubric/rubric20.txt"),
        "input_sha256": sha(REC),
        "context_sha256": CONTEXT_SHA,
    },
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(OUT, total)
