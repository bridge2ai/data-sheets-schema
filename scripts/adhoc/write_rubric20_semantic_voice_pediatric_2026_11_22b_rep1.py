"""Write the rubric20-semantic v3 evaluation of one D4D record.

Purpose: serialize the manual (agent) judgements for
  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/VOICE_PEDIATRIC_d4d.yaml
Inputs: that record, the agent definition, rubric text, evidence authority (hashed only).
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/VOICE_PEDIATRIC_2026-11-22b_rep1_evaluation.json
Date: 2026-11-22. No caller applicability context (empty context, all predicates unknown).
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest, normalize_context  # noqa: E402

INPUT = ROOT / "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/VOICE_PEDIATRIC_d4d.yaml"
AGENT = ROOT / ".claude/agents/d4d-rubric20-semantic.md"
RUBRIC = ROOT / "data/rubric/rubric20.txt"
AUTH = ROOT / "data/rubric/semantic_evidence_authority_v3.json"
OUT = ROOT / "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/VOICE_PEDIATRIC_2026-11-22b_rep1_evaluation.json"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


CTX = normalize_context(None)
ALWAYS = ("applicable", "This item applies to every dataset")


def unk(pred):
    return ("unknown", f"{pred}: not declared; retained in the denominator")


def q(id_, name, desc, stype, score, label, evidence, note, appl, cited=(), absent=(), counts=(),
      considered=(), no_issue_reason=None):
    status, appl_ev = appl
    mx = 1 if stype == "pass_fail" else 5
    item = {
        "id": id_, "name": name, "description": desc, "score_type": stype, "score": score,
        "max_score": mx, "score_label": label, "evidence": evidence, "quality_note": note,
        "applicable": True, "applicability_status": status, "applicability_evidence": appl_ev,
        "unit_scores": [{
            "path": "#", "score": score, "evidence": evidence,
            "cited": [dict(path=c[0], **({"quote": c[1]} if len(c) > 1 else {})) for c in cited],
            "absent": [{"path": a} for a in absent],
            "counts": [{"path": p, "claimed": n} for p, n in counts],
            "considered": list(considered),
        }],
    }
    if no_issue_reason:
        item["no_issue_reason"] = no_issue_reason
    return item


Q = []
Q.append(q(1, "Field Completeness",
    "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
    "numeric", 3, "Good (~79% of listed fields)",
    "11 of 14 listed fields populated (id, title, description, keywords, license_and_use_terms, doi, page, creators, purposes, instances, variables). Absent: top-level resources, parent_datasets, regulatory_restrictions.confidentiality_level.",
    "78.6% lies between the ~70% (3) and >=90% (5) anchors; does not reach 90%.",
    ALWAYS,
    cited=[("id", "doi:10.13026/mf9s-5r03"), ("title", "Bridge2AI-Voice Pediatric Dataset"), ("description",),
           ("keywords",), ("license_and_use_terms",), ("doi", "10.13026/h995-bt35"), ("page",), ("creators",),
           ("purposes",), ("instances",), ("variables",)],
    absent=["resources", "parent_datasets", "regulatory_restrictions"],
    counts=[("variables", 4), ("instances", 2)]))
Q.append(q(2, "Entry Length Adequacy",
    "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
    "numeric", 5, "Excellent (>200 chars)",
    "description is a ~900-character paragraph covering access, content, organization and raw-audio exclusion; purposes[0].response is ~210 characters.",
    "Both narrative fields exceed 200 characters on average and are substantive.",
    ALWAYS,
    cited=[("description", "contains derived audio features for 23,533 recordings"),
           ("purposes", "create an ethically sourced flagship dataset")]))
Q.append(q(3, "Keyword Diversity",
    "Number of distinct keywords describing the dataset.",
    "numeric", 3, "Good (3-7 keywords)",
    "Five keywords: health, pediatric, biomarkers, bridge2ai, voice.",
    "Five distinct keywords fall in the 3-7 band; no modality terms (audio features, spectrogram, speech) or condition lists add discoverability.",
    ALWAYS,
    cited=[("keywords", "pediatric")], counts=[("keywords", 5)]))
Q.append(q(4, "File Enumeration and Type Variety",
    "Number and variety of documented distribution formats and file types.",
    "numeric", 3, "Good (2-3 file types)",
    "file_collections enumerate 11 named files in the features folder: nine .parquet files, two TSV files (format: TSV), plus per-file JSON data dictionaries. phenotype and metadata folders are listed without file types. No distribution_formats or total_file_count.",
    "Three formats (Parquet, TSV, JSON) documented; >3 types required for 5. File count and phenotype/metadata file types missing.",
    ALWAYS,
    cited=[("file_collections",), ("/file_collections/0/resources/9/format", "TSV"),
           ("/file_collections/0/description", "Binary files are made available as Parquet")],
    absent=["distribution_formats", "total_file_count"],
    counts=[("/file_collections/0/resources", 11), ("file_collections", 3)]))
Q.append(q(5, "Data File Size Availability",
    "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
    "pass_fail", 1, "Pass",
    "instances give counts 23533 recordings and 300 participants; per-file n= counts in resource descriptions. No byte sizes.",
    "Instance counts present; byte sizes (total_size_bytes) absent but pass criterion is met.",
    ALWAYS,
    cited=[("/instances/0/counts",), ("/instances/1/counts",)],
    absent=["total_size_bytes"]))
Q.append(q(6, "Dataset Identification Metadata",
    "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification.",
    "pass_fail", 1, "Pass",
    "Version DOI 10.13026/h995-bt35 and latest-version DOI doi:10.13026/mf9s-5r03 (id); PhysioNet landing page. publisher field absent but PhysioNet identified in page/description/citation.",
    "Valid PhysioNet DOI prefix 10.13026; hosting platform identified in text though not as publisher field.",
    ALWAYS,
    cited=[("doi", "10.13026/h995-bt35"), ("page", "physionet.org"), ("id",)],
    absent=["publisher"]))
Q.append(q(7, "Funding and Acknowledgements Completeness",
    "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
    "numeric", 5, "Excellent",
    "funders: NIH with grant 3OT2OD032720-01S1 and grant title; creators include affiliations for key investigators (USF, Weill Cornell, Vanderbilt, OHSU, SickKids, MIT, etc.) and PI designations.",
    "Funder + valid-format NIH award number + affiliated creators meets the 5 anchor; most of the ~160 creators lack affiliations and the grant-number variants across sources are disclosed in source_caveats.",
    ALWAYS,
    cited=[("/funders/0/grants/0/grant_number", "3OT2OD032720-01S1"), ("funders",),
           ("/creators/0/affiliations/0/name", "USF Health Morsani College of Medicine"), ("creators",)]))
Q.append(q(8, "Ethical and Privacy Declarations",
    "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable.",
    "numeric", 3, "Good (basic ethics)",
    "SickKids REB approval, human_subject_research true, parental/participant consent, detailed at_risk_populations (guardian consent, assent), participant_privacy (raw audio withheld). No is_deidentified, reidentification_risk, data_protection_impacts, participant_compensation or regulatory_restrictions.",
    "Good consent/assent and ethics review; but de-identification status, re-identification risk assessment, data protection impacts and pediatric compensation are not documented, so not comprehensive.",
    unk("human_subjects"),
    cited=[("ethical_reviews", "Research Ethics Board at the Hospital for Sick Children"), ("human_subject_research",),
           ("informed_consent", "parental or participant consent"), ("at_risk_populations",),
           ("participant_privacy", "no raw audio")],
    absent=["is_deidentified", "data_protection_impacts", "participant_compensation", "regulatory_restrictions",
            "/participant_privacy/0/reidentification_risk"],
    considered=["source_caveats"]))
Q.append(q(9, "Access Requirements and Governance Documentation",
    "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts.",
    "numeric", 3, "Good (license + access terms, no confidentiality classification)",
    "license: Bridge2AI Voice Registered Access License; license_terms describes credentialed users signing a DUA; Synapse raw-audio access committee contact in external_resources. No regulatory_restrictions, confidentiality_level, ip_restrictions or data_protection_impacts.",
    "License and access tier are described, with a governance contact for raw audio only; no confidentiality classification or regulatory obligations, so the 5 anchor is not met.",
    ALWAYS,
    cited=[("license", "Bridge2AI Voice Registered Access License"),
           ("license_and_use_terms", "only credentialed users who sign the data use agreement"),
           ("/external_resources/0/restrictions", "DACO@b2ai-voice.org")],
    absent=["regulatory_restrictions", "ip_restrictions", "data_protection_impacts"]))
Q.append(q(10, "Interoperability, Standardization, and Cross-Platform Integration",
    "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures.",
    "numeric", 3, "Good (standard formats, no schema conformance)",
    "Parquet and TSV with per-file JSON data dictionaries; BIDS v1.9.0 conversion mentioned for the processing pipeline; Synapse link for raw audio. No conforms_to, conforms_to_schema, distribution_formats or typed related_datasets.",
    "Standard open formats and data dictionaries support reuse, but the release does not declare schema/ontology conformance and the adult/raw-audio relationships are untyped.",
    unk("shared_dataset"),
    cited=[("/file_collections/0/description", "whose keys are the column names"),
           ("/preprocessing_strategies/2/preprocessing_details", "Brain Imaging Data Structure v1.9.0"),
           ("external_resources",), ("file_collections",)],
    absent=["conforms_to", "conforms_to_schema", "distribution_formats", "related_datasets",
            "file_collections.compression"]))
Q.append(q(11, "Tool and Software Transparency",
    "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs.",
    "numeric", 5, "Excellent",
    "preprocessing_strategies name b2aiprep v3.0.0 (Apache-2.0, GitHub URL), torchaudio, openSMILE, Praat, parselmouth, SPARC, ReproSchema-UI->REDCap->BIDS v1.9.0; cleaning_strategies (feature removal, manual PII check); missing_data_documentation; feature parameters (window, hop, FFT) in resource descriptions.",
    "Comprehensive processing description with a versioned, URL-linked software package; secondary tools lack versions and no labeling/annotation is described, noted but not lowering.",
    unk("data_processing"),
    cited=[("/preprocessing_strategies/1/used_software/0/version", "3.0.0"),
           ("/preprocessing_strategies/1/used_software/0/url", "https://github.com/sensein/b2aiprep"),
           ("preprocessing_strategies",), ("cleaning_strategies",), ("missing_data_documentation",)]))
Q.append(q(12, "Collection Protocol Clarity",
    "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
    "numeric", 3, "Good (partial protocol)",
    "collection_mechanisms (reproschema-ui on tablets, headset vs built-in microphone, single session, parent surveys) and acquisition_methods (age-appropriate protocol). No data_collectors, collection_timeframes or raw_data_sources.",
    "Mechanism and method are well described, but collectors and the collection period are missing, so not a full protocol.",
    unk("data_collection"),
    cited=[("collection_mechanisms", "reproschema-ui"), ("acquisition_methods", "standardized age-appropriate protocol")],
    absent=["data_collectors", "collection_timeframes", "raw_data_sources"],
    considered=["sampling_strategies"]))
Q.append(q(13, "Version History, Maintenance, and Sustainability",
    "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access.",
    "numeric", 3, "Good (versioning + PID)",
    "version 1.1.0; version_access lists 1.0.0 and 1.1.0 with change details and version/latest DOIs; distribution_dates. No maintainers, publisher, updates plan or errata.",
    "Good version history and persistent IDs, but no maintenance commitment, maintainer contact or update plan.",
    unk("shared_dataset"),
    cited=[("version", "1.1.0"), ("version_access", "Version 1.1 is a minor update"), ("doi",)],
    absent=["maintainers", "publisher", "updates", "errata"],
    considered=["distribution_dates"]))
Q.append(q(14, "Associated Publications",
    "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources.",
    "numeric", 5, "Excellent",
    "Formal dataset citation with authors, year, title, version, PhysioNet, RRID and DOI; external resources Synapse raw audio and b2ai-voice.org website.",
    "Formal citation plus at least two distinct references meets the 5 anchor; no peer-reviewed publication is cited.",
    ALWAYS,
    cited=[("citation", "Bridge2AI-Voice Pediatric Dataset (version 1.1.0)"), ("external_resources",), ("doi",)],
    counts=[("external_resources", 2)]))
Q.append(q(15, "Human Subject Representation",
    "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups.",
    "numeric", 3, "Good (subgroups, limited demographics)",
    "300 participants aged 2-18; age-group protocols (Peds 2-4, 4-6, 6-10, 10+); single-site SickKids recruitment; inclusion/exclusion criteria (age, English proficiency, non-verbal). No sex/gender, ethnicity or per-age-group counts or patient vs healthy breakdown.",
    "Recruitment and inclusion/exclusion are clear, but demographic detail is limited to the age range; 'detailed demographics' for 5 is not met. Uncertainty: between bands, resolved conservatively.",
    unk("human_subjects"),
    cited=[("instances", ), ("subpopulations", "Peds 2-4, Peds 4-6, Peds 6-10 and Peds 10+"),
           ("sampling_strategies", "exclusion criteria were age over 18 and being non-verbal"),
           ("at_risk_populations",), ("missing_data_documentation",)],
    absent=["subsets"],
    counts=[("subpopulations", 1)]))
Q.append(q(16, "Findability (Persistent Links)",
    "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
    "pass_fail", 1, "Pass",
    "PhysioNet page URL, DOI 10.13026/h995-bt35, id doi:10.13026/mf9s-5r03, Synapse and project website URLs.",
    "Multiple well-formed persistent links.",
    ALWAYS,
    cited=[("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/"), ("doi",), ("id",), ("external_resources",)]))
Q.append(q(17, "Accessibility (Access Mechanism)",
    "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
    "numeric", 5, "Excellent",
    "PhysioNet platform; credentialed users must be approved and sign the Bridge2AI Voice Registered Access Agreement; no training required; raw audio via Synapse with institutional sign-off and access committee contact.",
    "Platform, login/credentialing, DUA and a separate controlled tier for raw audio are stated. download_url and distribution_formats absent; 'registered' vs 'credentialed' wording is noted as a minor inconsistency.",
    unk("shared_dataset"),
    cited=[("license_and_use_terms", "No training is required"), ("page",),
           ("/external_resources/0/restrictions", "requires institutional sign-off")],
    absent=["download_url", "distribution_formats"]))
Q.append(q(18, "Reusability, Use Guidance, and Social Impact",
    "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis.",
    "numeric", 3, "Good (license + basic use guidance)",
    "Named license and three one-line intended_uses (developmental norms, early screening tools, clinical insight). No prohibited_uses, discouraged_uses or future_use_impacts.",
    "Basic use guidance only; no prohibitions (e.g., re-identification) or social impact / mitigation analysis for a pediatric voice dataset.",
    ALWAYS,
    cited=[("license",), ("license_and_use_terms",), ("intended_uses", "early screening")],
    absent=["prohibited_uses", "discouraged_uses", "future_use_impacts"],
    counts=[("intended_uses", 3)]))
Q.append(q(19, "Data Integrity, Provenance Graph, and Quality",
    "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation.",
    "numeric", 3, "Good (version history, partial lineage)",
    "version_access with change history; missing_data_documentation; text lineage ReproSchema-UI -> REDCap -> BIDS -> b2aiprep features; cleaning steps. No was_derived_from, parent_datasets, raw_data_sources, errata, updates or splits.",
    "Version history and a textual processing chain exist, but no derivation link to the raw-audio source dataset and no agent attribution per activity; not a full provenance graph.",
    ALWAYS,
    cited=[("version_access",), ("missing_data_documentation", "could not generate certain features"),
           ("preprocessing_strategies",)],
    absent=["was_derived_from", "parent_datasets", "raw_data_sources", "errata", "updates", "splits"]))
Q.append(q(20, "Bias Documentation and Responsible AI Alignment",
    "Documentation of known biases, limitations and potential effects on intended or foreseeable uses.",
    "numeric", 0, "Absent",
    "No known_biases or future_use_impacts. Evident limitations (single-site SickKids recruitment, English-proficiency requirement, mixed headset/tablet microphones) are not framed as biases or limitations.",
    "No bias documentation; source_caveats describe source conflicts, not dataset biases.",
    ALWAYS,
    absent=["known_biases", "future_use_impacts", "known_limitations"],
    considered=["source_caveats", "sampling_strategies", "collection_mechanisms"]))

CATS = [("Structural Completeness", Q[0:5]), ("Metadata Quality & Content", Q[5:10]),
        ("Technical Documentation", Q[10:15]), ("FAIRness & Accessibility", Q[15:20])]
categories = [{"name": n, "questions": qs, "category_score": sum(x["score"] for x in qs),
               "category_max": sum(x["max_score"] for x in qs)} for n, qs in CATS]
total = sum(x["score"] for x in Q)
mx = sum(x["max_score"] for x in Q)
assert mx == 88

issues = [
    {"type": "completeness", "category": "variables_metadata", "item_ids": ["Q1"], "score_effect": "lowered",
     "description": "Top-level resources, parent_datasets and regulatory_restrictions.confidentiality_level are absent."},
    {"type": "completeness", "category": "other", "item_ids": ["Q3"], "score_effect": "lowered",
     "description": "Only five keywords; no modality or method terms (audio features, spectrogram, speech)."},
    {"type": "completeness", "category": "format_access", "item_ids": ["Q4", "Q10"], "score_effect": "lowered",
     "description": "No distribution_formats, file count or schema conformance; phenotype and metadata folders lack file types."},
    {"type": "completeness", "category": "privacy_regulatory", "item_ids": ["Q8", "Q9"], "score_effect": "lowered",
     "description": "No is_deidentified, reidentification_risk, data_protection_impacts, confidentiality_level or regulatory_restrictions for a pediatric human-subjects dataset."},
    {"type": "completeness", "category": "processing_provenance", "item_ids": ["Q12", "Q19"], "score_effect": "lowered",
     "description": "No collection timeframes, data collectors, raw_data_sources or typed derivation link to the Synapse raw-audio source."},
    {"type": "completeness", "category": "temporal_version", "item_ids": ["Q13"], "score_effect": "lowered",
     "description": "No maintainers, publisher, update plan or errata; sustainability commitment not documented."},
    {"type": "completeness", "category": "bias_quality", "item_ids": ["Q15"], "score_effect": "lowered",
     "description": "Demographic composition beyond the 2-18 age range (sex, ethnicity, per-age-group or patient/healthy counts) is not documented."},
    {"type": "completeness", "category": "license_use_terms", "item_ids": ["Q18"], "score_effect": "lowered",
     "description": "No prohibited or discouraged uses and no social impact analysis or mitigations."},
    {"type": "completeness", "category": "bias_quality", "item_ids": ["Q20"], "score_effect": "lowered",
     "description": "No known_biases or limitations despite single-site recruitment, English-only inclusion and mixed microphone hardware."},
    {"type": "consistency", "category": "format_access", "item_ids": [], "score_effect": "noted_only",
     "description": "Access tier wording mixes 'credentialed access' (description, license_terms) with 'Registered Access' license and 'registered access' availability; the DUA requirement is consistent."},
    {"type": "consistency", "category": "source_conflict", "item_ids": [], "score_effect": "noted_only",
     "description": "Grant number variants (-01S1, -01S3, 3Tf-OTOD03272001S2) across sources; record keeps the release's own number and discloses the conflict in source_caveats."},
    {"type": "consistency", "category": "persistent_identifier", "item_ids": [], "score_effect": "noted_only",
     "description": "id uses the latest-version DOI (mf9s-5r03) while doi holds the v1.1.0 release DOI (h995-bt35); explained in version_access, not an error."},
]

EXTRA = [
    ("medium", ["resources", "parent_datasets", "regulatory_restrictions"], "Add top-level resources/parent_datasets links and a confidentiality_level."),
    ("low", ["keywords"], "Add modality and method keywords (speech, audio features, spectrogram, pediatric voice disorders)."),
    ("medium", ["distribution_formats", "total_file_count", "conforms_to", "file_collections"], "Declare distribution_formats, file counts and the data-dictionary/BIDS conformance of released files."),
    ("high", ["is_deidentified", "participant_privacy", "data_protection_impacts", "regulatory_restrictions"], "Document de-identification method, re-identification risk of derived voice features, and confidentiality/regulatory classification."),
    ("medium", ["collection_timeframes", "data_collectors", "raw_data_sources", "was_derived_from"], "State the collection period, who collected data, and a typed derivation link to the raw-audio source."),
    ("medium", ["maintainers", "publisher", "updates", "errata"], "Name maintainers and publisher and state an update/errata policy."),
    ("medium", ["subpopulations", "instances"], "Report sex/gender, ethnicity and per-age-group and patient/healthy counts."),
    ("medium", ["prohibited_uses", "discouraged_uses", "future_use_impacts"], "Add prohibited uses (e.g., re-identification) and a social impact analysis with mitigations."),
    ("high", ["known_biases", "known_limitations"], "Document single-site, English-only and hardware-related biases and limitations."),
    ("low", ["description", "license_and_use_terms"], "Use one consistent PhysioNet access-tier term."),
    ("low", ["funders", "source_caveats"], "None needed beyond the existing disclosure; confirm the release grant number with the publisher."),
    ("low", ["id", "doi", "version_access"], "None needed; optionally record the latest-version DOI explicitly as such."),
]
for issue, (sev, fields, rec) in zip(issues, EXTRA):
    issue.update(severity=sev, fields_involved=fields, recommendation=rec)
assert len(EXTRA) == len(issues)

record = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": str(INPUT.relative_to(ROOT)),
    "project": "VOICE_PEDIATRIC",
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
        "total_points": total, "max_points": mx, "excluded_max_points": 0, "adjusted_max_points": mx,
        "normalized_percentage": round(total / mx * 100, 2), "fixed_percentage": round(total / mx * 100, 2),
        "questions_not_applicable": 0, "excluded_item_ids": [],
    },
    "categories": categories,
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "Record carefully separates the pediatric PhysioNet release from the adult dataset and the parent USF protocol, attributing statements to their source.",
            "Ethics coverage is strong on consent/assent and vulnerable-population protections but silent on de-identification method and re-identification risk for derived voice features.",
            "Processing transparency is high (versioned b2aiprep, feature parameters), while bias, social impact and sustainability documentation are missing.",
        ],
        "consistency_checks": {"passed": 5, "failed": 1, "warnings": 2},
        "consistency_check_details": [
            "PASS: involves_human_subjects=true with ethical_reviews populated.",
            "PASS: involves_human_subjects=true with informed_consent described.",
            "PASS: funders present with grant number.",
            "PASS: DOI present with PhysioNet landing page.",
            "PASS: temporal order v1.0.0 (2025-12-17) before v1.1.0 (2026-05-01).",
            "FAIL: pediatric human data with privacy techniques but no is_deidentified / deidentification method or reidentification risk.",
            "WARN: credentialed vs registered access wording.",
            "WARN: grant-number variants across sources (disclosed).",
        ],
        "correctness_validations": {
            "doi_format": "valid (10.13026 PhysioNet prefix for both DOIs)",
            "grant_number_format": "valid NIH pattern (3OT2OD032720-01S1: supplement to OT2 OD award)",
            "rrid_format": "valid (RRID:SCR_007345 in citation)",
            "url_validity": "plausible (physionet.org, synapse.org, github.com, b2ai-voice.org)",
        },
    },
    "applicability_context": CTX,
    "evaluation_scope": {
        "policy": "single_dataset",
        "units": [{"path": "#", "id": "doi:10.13026/mf9s-5r03"}],
        "collection_metadata_inherited": False,
    },
    "metadata": {
        "instrument_sha256": sha(AGENT),
        "evidence_authority_sha256": sha(AUTH),
        "rubric_sha256": sha(RUBRIC),
        "input_sha256": sha(INPUT),
        "context_sha256": context_digest(CTX),
    },
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
print(OUT, total, mx)
