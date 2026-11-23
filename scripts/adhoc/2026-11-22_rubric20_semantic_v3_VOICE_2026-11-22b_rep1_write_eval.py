#!/usr/bin/env python3
"""Write the rubric20-semantic v3 evaluation of one VOICE D4D record.

Purpose: serialize the judgements of a manual rubric20-semantic (general
context instrument v3) evaluation made by the evaluating session, computing the
input/rubric/instrument/authority/context digests from the actual bytes.
Input:  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/VOICE_d4d.yaml
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/VOICE_2026-11-22b_rep1_evaluation.json
Context: no caller applicability context (empty; all predicates unknown).
Date: 2026-11-22. Evaluator runtime model: claude-opus-5-5.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest  # noqa: E402

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/VOICE_d4d.yaml"
OUTPUT = "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/VOICE_2026-11-22b_rep1_evaluation.json"


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


ALWAYS = "This item applies to every dataset"


def unk(pred):
    return f"{pred}: not declared by the caller (no context supplied); retained in the denominator"


def C(path, quote=None):
    return {"path": path, "quote": quote} if quote else {"path": path}


def A(path):
    return {"path": path}


def N(path, n):
    return {"path": path, "claimed": n}


def q(qid, name, desc, stype, score, mx, label, evidence, note, status, app_ev,
      cited=(), absent=(), counts=(), considered=(), no_issue_reason=None):
    item = {
        "id": qid, "name": name, "description": desc, "score_type": stype,
        "score": score, "max_score": mx, "score_label": label,
        "evidence": evidence, "quality_note": note, "applicable": True,
        "applicability_status": status, "applicability_evidence": app_ev,
        "unit_scores": [{
            "path": "#", "score": score, "evidence": evidence,
            "cited": list(cited), "absent": list(absent),
            "counts": list(counts), "considered": list(considered),
        }],
    }
    if no_issue_reason:
        item["no_issue_reason"] = no_issue_reason
    return item


cat1 = [
    q(1, "Field Completeness",
      "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
      "numeric", 3, 5, "Good (about 79% of listed fields populated)",
      "11 of 14 listed fields are populated: id 'doi:10.13026/37yb-1t42', title, description, keywords, license_and_use_terms, doi, page 'https://physionet.org/content/b2ai-voice/', creators, purposes, instances (counts 833) and variables. Absent: top-level resources (file entries exist only nested under file_collections), parent_datasets and regulatory_restrictions.confidentiality_level.",
      "11/14 = 79% sits between the ~70% (3) and >=90% (5) anchors, so the 3 band applies. The missing confidentiality classification is a governance gap, not only a structural one.",
      "applicable", ALWAYS,
      cited=[C("id"), C("title"), C("description"), C("keywords"), C("license_and_use_terms"), C("doi"),
             C("page"), C("creators"), C("purposes"), C("instances"), C("variables"), C("file_collections")],
      absent=[A("resources"), A("parent_datasets"), A("regulatory_restrictions.confidentiality_level")]),
    q(2, "Entry Length Adequacy",
      "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
      "numeric", 5, 5, "Excellent (narratives well over 200 characters)",
      "description is ~430 characters ('Release 3.1.0 (v3.1) contains data for 833 participants across five sites in North America'); the first purpose description exceeds 500 characters and the target-size purpose records conflicting sources with a caveat.",
      "Both narrative fields are substantive and dataset-specific; average length is well above 200 characters.",
      "applicable", ALWAYS,
      cited=[C("description", "contains data for 833 participants across five sites in North America"),
             C("purposes.description", "Build a large multi-institutional database of human voices")],
      counts=[N("purposes", 3)]),
    q(3, "Keyword Diversity",
      "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply additional topic evidence where documented; no named study or disease count is presumed.",
      "numeric", 3, 5, "Good (4 keywords)",
      "keywords: health, biomarkers, bridge2ai, voice (4 distinct). Condition cohorts (voice, neurological, mood, respiratory disorders) appear only under subpopulations, not as keywords.",
      "4 keywords falls in the 3-7 band. Terms are generic; no acoustic/modality terms (spectrogram, MFCC) or condition terms are keywords.",
      "applicable", ALWAYS,
      cited=[C("keywords", "biomarkers"), C("subpopulations")], counts=[N("keywords", 4)]),
    q(4, "File Enumeration and Type Variety",
      "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in separate linked resources. Examine every distribution; modality breadth is distinct from suitability for machine learning.",
      "numeric", 3, 5, "Good (3 released file types)",
      "file_collections enumerate 11 feature files: 9 Parquet and 2 TSV ('format: TSV', 'text/tab-separated-values'), each with a JSON data dictionary; metadata collection is Parquet, phenotype is TSV with JSON dictionaries. Raw WAV is explicitly not part of this release. distribution_formats and total_file_count are absent.",
      "Released types are Parquet, TSV and JSON (3), the 2-3 band. WAV is documented only as a controlled-access raw source, so it does not count as a distributed type. Parquet resources carry no format/media_type values of their own.",
      "applicable", ALWAYS,
      cited=[C("file_collections.description", "Dense binary files are distributed as Parquet"),
             C("file_collections.resources.media_type", "text/tab-separated-values"),
             C("raw_data_sources.raw_data_format", "WAV"),
             C("raw_data_sources.source_description", "The raw audio is not part of this release.")],
      absent=[A("distribution_formats"), A("total_file_count")],
      counts=[N("file_collections", 3)]),
    q(5, "Data File Size Availability",
      "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
      "pass_fail", 1, 1, "Pass",
      "instances.counts: 833 participants; per-file record counts in resource descriptions (e.g. 'n=29289' for ppgs.parquet). No byte sizes.",
      "Instance count and per-file record counts are present; byte sizes (total_size_bytes, file_collections.total_bytes) are absent, so only an estimate of size is possible.",
      "applicable", ALWAYS,
      cited=[C("instances.counts"), C("file_collections.resources.description", "n=29289")],
      absent=[A("total_size_bytes"), A("file_collections.total_bytes"), A("splits")]),
]

cat2 = [
    q(6, "Dataset Identification Metadata",
      "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or repository). Note: Dataset identification should include both persistent identifiers AND hosting platform information (e.g., PhysioNet, Dataverse, Zenodo, institutional repositories).",
      "pass_fail", 1, 1, "Pass",
      "doi '10.13026/37yb-1t42' (PhysioNet prefix 10.13026, valid format), page on physionet.org, citation names 'PhysioNet. RRID:SCR_007345'. publisher field is absent.",
      "A valid persistent DOI and the hosting platform (via page URL and citation) are present. The citation DOI (8xbn-nq66) differs from id/doi (37yb-1t42); version_access explains this as the version-specific vs latest-version DOI, which is consistent.",
      "applicable", ALWAYS,
      cited=[C("doi"), C("id"), C("page"), C("citation", "PhysioNet. RRID:SCR_007345."),
             C("version_access.latest_version_doi")],
      absent=[A("publisher")]),
    q(7, "Funding and Acknowledgements Completeness",
      "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
      "numeric", 5, 5, "Excellent (funder with valid grant numbers + PI affiliations)",
      "funders: NIH Common Fund Bridge2AI Program with grants OT2OD032720 and 3OT2OD032720-01S1 (supplement), with a caveat reconciling the two. creators: ~140 named authors; principal investigators carry affiliations (USF Health Morsani College of Medicine; Weill Cornell Medicine).",
      "Grant numbers follow the NIH activity/institute pattern (OT2 + OD + serial; supplement suffix -01S1). Affiliations are given only for the two PIs, not for the other authors, which is a limitation but meets the funder-with-grants + creator-affiliation anchor.",
      "applicable", ALWAYS,
      cited=[C("funders.grants.grant_number", "OT2OD032720"), C("funders.grantor", "NIH Common Fund"),
             C("creators.principal_investigator.affiliation.name", "Weill Cornell Medicine"),
             C("funders.source_caveats")],
      counts=[N("funders", 1)]),
    q(8, "Ethical and Privacy Declarations",
      "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable. Accept equivalent jurisdiction-appropriate ethics review and data protection frameworks.",
      "numeric", 3, 5, "Good (IRB, consent, deidentification, compensation; no data protection impacts or at-risk populations)",
      "human_subject_research.involves_human_subjects: true; ethical_reviews: USF IRB single-IRB approval plus separate Canadian REB review; informed_consent with scope and documentation; is_deidentified with HIPAA Safe Harbor method; participant_privacy.reidentification_risk ('a voice can never be fully de-identified'); participant_compensation $40/$80, max $120; consent_revocations. Absent: data_protection_impacts, at_risk_populations, regulatory_restrictions.hipaa_compliant, other_compliance, governance_committee_contact.",
      "Cross-field logic passes: human subjects -> ethics review and consent present; deidentification -> method and privacy risk present. It exceeds 'basic', but the 5 anchor requires data protection impacts, which are not documented, and vulnerable populations (e.g. pediatric relation, psychiatric cohort) are not addressed, so the score stays at 3.",
      "unknown", unk("human_subjects"),
      cited=[C("human_subject_research.involves_human_subjects"),
             C("ethical_reviews.reviewing_organization", "University of South Florida Institutional Review Board"),
             C("is_deidentified.method", "HIPAA Safe Harbor identifiers were removed"),
             C("participant_privacy.reidentification_risk", "a voice can never be fully de-identified"),
             C("informed_consent.consent_scope"), C("participant_compensation.compensation_amount"),
             C("consent_revocations"), C("data_governance.committee_name"), C("sensitive_elements")],
      absent=[A("data_protection_impacts"), A("at_risk_populations"),
              A("regulatory_restrictions.hipaa_compliant"), A("regulatory_restrictions.other_compliance"),
              A("regulatory_restrictions.governance_committee_contact")]),
    q(9, "Access Requirements and Governance Documentation",
      "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts. Distinguish unrestricted access, registration, an agreement and committee approval. A named license does not by itself imply unrestricted reuse.",
      "numeric", 3, 5, "Good (license, IP and regulatory restrictions; no confidentiality classification)",
      "license_and_use_terms: credentialed access with signed Bridge2AI Voice Registered Access Agreement; ip_restrictions (no sale, no IP claims); regulatory_restrictions: Certificate of Confidentiality (caveated as governing the controlled raw-audio route); data_governance: DACO review for raw audio. Absent: confidentiality_level, governance_committee_contact, data_protection_impacts.",
      "Access tiers are distinguished (credentialed + DUA for features; DACO approval for raw audio). The 5 anchor requires a confidentiality classification, which is absent. Tension: top-level license is 'Registered Access License' while license_terms says 'Credentialed access'; the record flags the source disagreement in a caveat.",
      "applicable", ALWAYS,
      cited=[C("license_and_use_terms.license_terms", "only credentialed users who sign the data use"),
             C("license", "Bridge2AI Voice Registered Access License"),
             C("ip_restrictions.restrictions"), C("regulatory_restrictions.regulatory_restrictions"),
             C("data_governance.access_review_process")],
      absent=[A("regulatory_restrictions.confidentiality_level"),
              A("regulatory_restrictions.governance_committee_contact"), A("data_protection_impacts")],
      considered=["license_and_use_terms.source_caveats", "regulatory_restrictions.source_caveats"]),
    q(10, "Interoperability, Standardization, and Cross-Platform Integration",
      "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures. Assess suitability for the declared uses; machine-learning use and any study-specific readiness framework must not be assumed.",
      "numeric", 3, 5, "Good (standard formats; no schema conformance for the release)",
      "Parquet/TSV with per-file JSON data dictionaries; typed related_datasets (has_version, references); external REDCap data dictionary on GitHub/Zenodo; raw data described as BIDS v1.9.0 compliant; labels 'Per Bridge2AI Protocols and ICD-10 codes'. conforms_to, conforms_to_schema and distribution_formats absent.",
      "Formats are standard and data dictionaries aid integration, but no schema/ontology conformance is declared for the released files (BIDS applies to the unreleased raw data; ICD-10 is mentioned only for labels), so the 5 anchor is not met.",
      "unknown", unk("shared_dataset"),
      cited=[C("related_datasets.relationship_type", "has_version"),
             C("raw_data_sources.source_description", "Brain Imaging"),
             C("labeling_strategies.data_annotation_protocol", "ICD-10"),
             C("external_resources"), C("file_collections.description", "JSON data dictionary")],
      absent=[A("conforms_to"), A("conforms_to_schema"), A("distribution_formats"),
              A("file_collections.compression")],
      counts=[N("related_datasets", 2)]),
]

cat3 = [
    q(11, "Tool and Software Transparency",
      "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs. Structured text and provenance graphs are both valid evidence. Data processing is relevant independently of whether software is a released dataset output.",
      "numeric", 5, 5, "Excellent (strategies with software, versions, URLs and parameters)",
      "preprocessing_strategies: b2aiprep v3.0.0 (https://github.com/sensein/b2aiprep), audio standardization (mono, 16 kHz, Butterworth filter), feature extraction with parameters (25 ms window, 10 ms hop, 400-point FFT, 60 MFCCs) via SenseLab, sparc, OpenSMILE eGeMAPS, Parselmouth/Praat, ppgs, torchaudio; machine_annotation_tools: OpenAI Whisper Large; cleaning_strategies audit protocol; labeling_strategies; missing_data_documentation. imputation_protocols and annotation_analyses absent.",
      "Comprehensive and parameterized; a version is given for b2aiprep and URLs for the main libraries. SenseLab and most feature libraries lack versions, and Whisper is noted elsewhere as unaudited, but the 5 anchor is met.",
      "unknown", unk("data_processing"),
      cited=[C("preprocessing_strategies.used_software.version", "3.0.0"),
             C("preprocessing_strategies.used_software.url", "https://github.com/sensein/b2aiprep"),
             C("preprocessing_strategies.preprocessing_details", "400-point FFT"),
             C("machine_annotation_tools.tools", "OpenAI Whisper Large"),
             C("cleaning_strategies.cleaning_details"), C("labeling_strategies"),
             C("missing_data_documentation")],
      absent=[A("imputation_protocols"), A("annotation_analyses")],
      no_issue_reason="Item is at its maximum score."),
    q(12, "Collection Protocol Clarity",
      "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
      "numeric", 3, 5, "Good (mechanisms, methods, collectors described; no collection timeframe)",
      "collection_mechanisms: Bridge2AI-Voice App on iPad with Avid AE-36 microphone, REDCap; acquisition_methods (directly observed, self-reported, clinician-verified); direct_collection 'with the assistance of a trained research assistant'; sampling_strategies at high-volume expert clinics; raw_data_sources (ReproSchema-UI/REDCap, BIDS). collection_timeframes and data_collectors fields absent.",
      "Methods and collectors are well described, but no collection period is given anywhere (only release dates), so the full-protocol anchor requiring timeframes is not met. Several device details are caveated as from the v2.0.0 healthsheet.",
      "unknown", unk("data_collection"),
      cited=[C("collection_mechanisms.name", "Bridge2AI-Voice App"),
             C("acquisition_methods.acquisition_details"),
             C("direct_collection.collection_details", "trained research"),
             C("sampling_strategies.strategies"), C("raw_data_sources.source_description")],
      absent=[A("collection_timeframes"), A("data_collectors")],
      considered=["distribution_dates"], counts=[N("collection_mechanisms", 5)]),
    q(13, "Version History, Maintenance, and Sustainability",
      "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access. Assess the preservation route appropriate to the domain and access conditions.",
      "numeric", 5, 5, "Excellent (versioned DOIs, history, errata, update plan, retention, governance)",
      "version 3.1.0; version_access lists 1.1, 2.0.0, 2.0.1, 3.0.0, 3.1.0 with 'each version has a unique DOI' and 'Older versions are supported by default'; distribution_dates per version; errata (3.1.0 fixed broken parquet files); updates semi-annual; retention_limit indefinite; data_governance DACO; PhysioNet repository with DOI. maintainers and publisher absent.",
      "Comprehensive versioning plus repository, retention commitment and governance meet the 5 anchor. Gaps noted without lowering: no maintainers entry (only a PI email under creators), the semi-annual plan comes from the v2.0.0 healthsheet for Health Data Nexus, and versions_available omits the 1.0 Health Data Nexus release named in related_datasets.",
      "unknown", unk("shared_dataset"),
      cited=[C("version"), C("version_access.version_details", "each version has a unique DOI"),
             C("errata.erratum_details"), C("updates.frequency"), C("retention_limit.retention_details"),
             C("distribution_dates.release_dates"), C("doi")],
      absent=[A("maintainers"), A("publisher")],
      counts=[N("version_access.versions_available", 5)],
      considered=["updates.source_caveats", "related_datasets.notes"],
      no_issue_reason="Item is at its maximum score; the version-list omission is recorded as a noted-only issue."),
    q(14, "Associated Publications",
      "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources. The dataset need not belong to a named study or have a publication to document how it should be cited.",
      "numeric", 5, 5, "Excellent (formal dataset citation + several distinct references)",
      "citation: authors, year, title, version 3.1.0, PhysioNet, https://doi.org/10.13026/8xbn-nq66; external_resources: github.com/eipm/bridge2ai-redcap, zenodo.org/records/14989503, Synapse syn72370534; dataset DOI.",
      "Formal citation identifying title, authors and publisher plus at least two distinct further references meets the 5 anchor. No associated journal article is cited, which the item does not require.",
      "applicable", ALWAYS,
      cited=[C("citation", "Bridge2AI-Voice: An ethically-sourced"),
             C("external_resources.external_resources", "https://zenodo.org/records/14989503"), C("doi")],
      counts=[N("external_resources", 2)],
      no_issue_reason="Item is at its maximum score."),
    q(15, "Human Subject Representation",
      "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups. Evaluate the represented population and stated use, not a predetermined clinical cohort.",
      "numeric", 3, 5, "Good (participants and cohorts described; no demographic detail or explicit criteria)",
      "instances: 833 persons, multiple sessions possible; subpopulations: identification 'Age, Gender, Sex, Ethnicity, Socioeconomic status' and four disorder cohorts (voice, neurological, mood, respiratory); sampling_strategies refer to 'inclusion/exclusion criteria' without stating them; compensation only for adults; at_risk_populations absent.",
      "Subgroup dimensions and cohorts are named, but no demographic distributions and no actual inclusion/exclusion criteria are given, so the detailed-demographics anchor is not met. The demographic subpopulation entry is caveated as v2.0.0 information.",
      "unknown", unk("human_subjects"),
      cited=[C("instances.counts"), C("subpopulations.identification", "Age, Gender, Sex, Ethnicity"),
             C("subpopulations.name", "Mood disorders"),
             C("sampling_strategies.strategies", "inclusion/exclusion criteria")],
      absent=[A("at_risk_populations"), A("subsets")],
      counts=[N("subpopulations", 5)],
      considered=["missing_data_documentation", "known_biases"]),
]

cat4 = [
    q(16, "Findability (Persistent Links)",
      "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
      "pass_fail", 1, 1, "Pass",
      "page https://physionet.org/content/b2ai-voice/, DOI 10.13026/37yb-1t42, external resources on GitHub, Zenodo and Synapse. download_url absent.",
      "Well-formed persistent URL and DOI present on plausible domains; links were not live-checked.",
      "applicable", ALWAYS,
      cited=[C("page"), C("doi"), C("external_resources")], absent=[A("download_url")]),
    q(17, "Accessibility (Access Mechanism)",
      "Describes how users can obtain the dataset (download URL, distribution formats, access policy).\nNote: \"Public\" does not mean \"no restrictions.\" Even openly accessible datasets may require signed Data Use Agreements (DUAs). Distinguish between access tiers: (1) No authentication required (truly public), (2) Registration required (email/account), (3) DUA required (signed agreement), (4) IRB/committee approval required (restricted access). State the actual authorization steps, including registration or a signed agreement, without implying unrestricted access.",
      "numeric", 5, 5, "Excellent (platform, login tier and policy for each route)",
      "PhysioNet page; license_terms: 'only credentialed users who sign the data use agreement ... can access the files' and 'No training is required'; raw audio via Synapse 'after institutional sign-off' and DACO review with a separate DTUA; file formats in file_collections. download_url absent.",
      "Both access tiers are explicit (credentialed + DUA for derived features; institutional sign-off + committee approval for raw audio), naming platform, authorization and policy. The registered-vs-credentialed label disagreement is surfaced by the record's own caveat, not hidden.",
      "unknown", unk("shared_dataset"),
      cited=[C("license_and_use_terms.license_terms", "No training is"),
             C("external_resources.description", "after institutional sign-off"),
             C("data_governance.access_review_process"), C("page")],
      absent=[A("download_url"), A("distribution_formats")],
      no_issue_reason="Item is at its maximum score; the access-label tension is a noted-only issue."),
    q(18, "Reusability, Use Guidance, and Social Impact",
      "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis with risk identification and mitigation strategies (CROISSANT RAI aligned).",
      "numeric", 3, 5, "Good (license + intended/prohibited/discouraged uses; no social impact analysis)",
      "license and license_terms; intended_uses (AI pretraining, fine-tuning, benchmarking, validation); prohibited_uses (re-identification, harm/stigmatization, contacting subjects); discouraged_uses (hiring, insurance, surveillance). future_use_impacts absent.",
      "Use guidance is explicit, but there is no future-use/social impact analysis with mitigations, which the 5 anchor requires. One prohibited use is caveated as stated only for the controlled-access route.",
      "applicable", ALWAYS,
      cited=[C("intended_uses.description"), C("prohibited_uses.description", "Attempting to re-identify"),
             C("discouraged_uses.description", "insurance premium"), C("license_and_use_terms")],
      absent=[A("future_use_impacts")],
      considered=["prohibited_uses.source_caveats"]),
    q(19, "Data Integrity, Provenance Graph, and Quality",
      "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation. Note: Provenance is a transparent graph of origins and processing of data (W3C PROV-O standard: https://www.w3.org/TR/prov-o/), NOT just version changes. Evaluation checks for: (1) Entity-activity-agent relationships, (2) Processing lineage, (3) Derivation paths. Scoring distinction: - Version history alone (version numbers, errata, updates) = 3 points - Full provenance graph (W3C PROV-O with entity-activity-agent relationships, processing   lineage, derivation paths) = 5 points  Provenance may be represented as text OR as W3C PROV-O graphs. Both formats are acceptable if they provide complete lineage information.",
      "numeric", 5, 5, "Excellent (complete textual lineage with entities, activities and agents)",
      "Textual lineage: raw audio and questionnaires from ReproSchema-UI/REDCap converted to BIDS v1.9.0 (raw_data_sources) -> exported/converted by b2aiprep v3.0.0, developed by the project team -> monaural 16 kHz resampling -> feature extraction (SenseLab etc.) -> deidentification removal of sensitive records -> released Parquet/TSV; agents: trained research assistants (collection), clinicians (labels), data release team (audit). Version history (versions_available, errata, updates), missing_data_documentation. was_derived_from, parent_datasets and splits absent.",
      "Scored on content: the record gives entities, activities, agents and derivation paths from raw source to released features, plus version-to-version changes, which the text-or-graph clause accepts as complete lineage.",
      "applicable", ALWAYS,
      cited=[C("raw_data_sources.source_description", "ReproSchema-UI"),
             C("preprocessing_strategies.description", "open source library developed by the project team"),
             C("is_deidentified.deidentification_details"), C("version_access.version_details"),
             C("errata.erratum_details"), C("updates.update_details"),
             C("missing_data_documentation.handling_strategy", "data release team")],
      absent=[A("was_derived_from"), A("parent_datasets"), A("splits")],
      no_issue_reason="Item is at its maximum score."),
    q(20, "Bias Documentation and Responsible AI Alignment",
      "Documentation of known biases, limitations and potential effects on intended or foreseeable uses. Every dataset has a scope that can be documented; absent bias fields do not make this question inapplicable.",
      "numeric", 3, 5, "Good (specific biases and limitations; no taxonomy or fairness analysis)",
      "known_biases: skews by disorder category, site and demographics (with a mitigation note) and recruitment bias against groups with less trust or proximity; known_limitations (unequal disease distribution, unaudited transcription models, site-device confounding); anomalies (site configurations and protocol changes). bias_type and future_use_impacts absent.",
      "Bias identification is concrete but untyped against any taxonomy (AIO/Croissant RAI) and there is no fairness analysis or future-use impact statement, so the 5 anchor is not met.",
      "applicable", ALWAYS,
      cited=[C("known_biases.bias_description", "skews based on disorder category"),
             C("known_biases.mitigation_strategy"), C("known_limitations"), C("anomalies.anomaly_details")],
      absent=[A("future_use_impacts"), A("known_biases.bias_type")],
      counts=[N("known_biases", 2), N("known_limitations", 5)]),
]

issues = [
    {"item_ids": [1, 9], "score_effect": "lowered", "category": "privacy_regulatory", "type": "completeness",
     "description": "regulatory_restrictions.confidentiality_level is absent; the release has credentialed access and a Certificate of Confidentiality but no confidentiality classification.",
     "severity": "medium"},
    {"item_ids": [1], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
     "description": "parent_datasets and a top-level resources list are absent (files are enumerated only under file_collections).",
     "severity": "low"},
    {"item_ids": [3], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "description": "Only 4 generic keywords; modality and condition terms are not keywords.", "severity": "low"},
    {"item_ids": [4, 10], "score_effect": "lowered", "category": "format_access", "type": "completeness",
     "description": "No distribution_formats or conforms_to/conforms_to_schema; Parquet resources carry no format or media_type; only Parquet, TSV and JSON are released.",
     "severity": "medium"},
    {"item_ids": [8], "score_effect": "lowered", "category": "consent_ethics", "type": "completeness",
     "description": "data_protection_impacts and at_risk_populations are absent although the cohort includes psychiatric and neurological patients and a related pediatric dataset; HIPAA compliance is mentioned only inside the deidentification method.",
     "severity": "medium"},
    {"item_ids": [12], "score_effect": "lowered", "category": "temporal_version", "type": "completeness",
     "description": "No collection timeframe is given anywhere; only release dates are recorded.", "severity": "medium"},
    {"item_ids": [15], "score_effect": "lowered", "category": "bias_quality", "type": "completeness",
     "description": "Demographic dimensions are named but no distributions are given, and inclusion/exclusion criteria are referenced but not stated.",
     "severity": "medium"},
    {"item_ids": [18, 20], "score_effect": "lowered", "category": "bias_quality", "type": "completeness",
     "description": "future_use_impacts absent and biases are not typed against a standard taxonomy; no fairness analysis.",
     "severity": "medium"},
    {"item_ids": [], "score_effect": "noted_only", "category": "license_use_terms", "type": "consistency",
     "description": "Top-level license names a 'Registered Access License' while license_terms states 'Credentialed access'; the record's caveat explains the source disagreement and prefers the release page.",
     "severity": "low"},
    {"item_ids": [], "score_effect": "noted_only", "category": "temporal_version", "type": "consistency",
     "description": "versions_available begins at 1.1 while related_datasets describes a Version 1.0 on Health Data Nexus as the first release; the semi-annual update plan is from the v2.0.0 healthsheet.",
     "severity": "low"},
    {"item_ids": [], "score_effect": "noted_only", "category": "source_conflict", "type": "content_accuracy",
     "description": "Enrollment targets conflict (30 000 vs 10,000) across sources; the record reports both with a caveat rather than resolving, which is appropriate.",
     "severity": "low"},
    {"item_ids": [], "score_effect": "noted_only", "category": "attribution", "type": "completeness",
     "description": "Affiliations are given only for the two principal investigators, not for the other ~140 creators.",
     "severity": "low"},
]
EXTRA = [
    (["regulatory_restrictions.confidentiality_level"], "State a confidentiality classification for the credentialed release."),
    (["parent_datasets", "resources"], "Link the raw-audio controlled-access dataset as a parent and list released files as resources."),
    (["keywords"], "Add modality and condition keywords (e.g. spectrogram, MFCC, voice disorders)."),
    (["distribution_formats", "conforms_to_schema", "file_collections.resources.format"], "Declare distribution formats and media types for every file and any schema conformance."),
    (["data_protection_impacts", "at_risk_populations", "regulatory_restrictions.hipaa_compliant"], "Document a data protection impact assessment and vulnerable-population safeguards."),
    (["collection_timeframes"], "Record the data collection start and end dates for the release."),
    (["subpopulations", "sampling_strategies"], "Give demographic distributions and the actual inclusion/exclusion criteria."),
    (["future_use_impacts", "known_biases.bias_type"], "Add future-use impacts with mitigations and type biases against a standard taxonomy."),
    (["license", "license_and_use_terms.license_terms"], "Use one access-tier label consistently once the source disagreement is resolved."),
    (["version_access.versions_available", "related_datasets", "updates"], "Include version 1.0 in the version list and confirm the update plan for the current platform."),
    (["purposes"], "Keep both targets with caveats until an authoritative source resolves them."),
    (["creators"], "Add affiliations for all creators where sources provide them."),
]
for i, (fields, rec) in zip(issues, EXTRA):
    i["item_ids"] = [f"Q{n}" for n in i["item_ids"]]
    i["fields_involved"] = fields
    i["recommendation"] = rec


def catsum(qs):
    return sum(x["score"] for x in qs if x["score"] is not None)


cats = [
    {"name": "Structural Completeness", "questions": cat1, "category_score": catsum(cat1), "category_max": 21},
    {"name": "Metadata Quality & Content", "questions": cat2, "category_score": catsum(cat2), "category_max": 21},
    {"name": "Technical Documentation", "questions": cat3, "category_score": catsum(cat3), "category_max": 25},
    {"name": "FAIRness & Accessibility", "questions": cat4, "category_score": catsum(cat4), "category_max": 21},
]
total = sum(c["category_score"] for c in cats)
ctx = {}
out = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": INPUT,
    "project": "VOICE",
    "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {
        "name": "claude-opus-5-5",
        "evaluator_model": "claude-opus-5-5",
        "temperature": None,
        "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
        "evaluation_type": "semantic_llm_judge",
    },
    "overall_score": {
        "total_points": total, "max_points": 88, "excluded_max_points": 0,
        "adjusted_max_points": 88,
        "normalized_percentage": round(total / 88 * 100, 2),
        "fixed_percentage": round(total / 88 * 100, 2),
        "questions_not_applicable": 0,
        "excluded_item_ids": [],
    },
    "categories": cats,
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "Source disagreements (enrollment targets, access label, grant numbers, consent revocation) are surfaced with caveats rather than silently resolved.",
            "Version-specific statements taken from the v2.0.0 healthsheet are marked, keeping current-release claims distinct.",
            "Processing lineage from raw audio to released features is detailed with software, versions and parameters.",
            "Gaps concentrate in governance classification (confidentiality level, data protection impacts), collection timeframe and social impact analysis.",
        ],
        "consistency_checks": {"passed": 6, "failed": 0, "warnings": 3},
        "correctness_validations": {
            "doi_format": "valid: 10.13026/37yb-1t42 and 10.13026/8xbn-nq66 (PhysioNet prefix); related 10.57764 and 10.13026 DOIs well formed",
            "grant_number_format": "valid: OT2OD032720 and supplement 3OT2OD032720-01S1 match the NIH pattern",
            "rrid_format": "valid: RRID:SCR_007345 in citation",
            "url_validity": "well-formed URLs on plausible domains (physionet.org, github.com, zenodo.org, synapse.org); not live-checked",
        },
    },
    "applicability_context": ctx,
    "evaluation_scope": {
        "policy": "single_dataset",
        "units": [{"path": "#", "id": "doi:10.13026/37yb-1t42"}],
        "collection_metadata_inherited": False,
    },
    "metadata": {
        "instrument_sha256": sha(".claude/agents/d4d-rubric20-semantic.md"),
        "evidence_authority_sha256": sha("data/rubric/semantic_evidence_authority_v3.json"),
        "rubric_sha256": sha("data/rubric/rubric20.txt"),
        "input_sha256": sha(INPUT),
        "context_sha256": context_digest(ctx),
    },
}
path = ROOT / OUTPUT
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(path, total)
