#!/usr/bin/env python3
"""Serialize one rubric20-semantic v3 evaluation (judgements made by the evaluator).

Purpose: write the evaluator's rubric20-semantic (general context instrument v3)
judgements for one D4D record as the required JSON, computing digests from bytes.
Input:  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/AI_READI_d4d.yaml
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep3_evaluation.json
Serves: caller-requested single-record evaluation (rubric20-semantic v3). Date: 2026-11-22.
No applicability context file was supplied: empty context, every predicate unknown.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest, normalize_context  # noqa: E402

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/AI_READI_d4d.yaml"
OUT = "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep3_evaluation.json"
MODEL = "claude-opus-5-5"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


ALWAYS = "This item applies to every dataset"


def unknown(pred):
    return f"{pred}: not declared by the caller (no context supplied); unknown, retained in the denominator"


# (id, name, description, type, max, applies_pred_or_None, score, label, evidence, quality, cited, absent, counts, considered, no_issue_reason)
Q = []


def q(id_, name, desc, stype, mx, pred, score, label, evidence, quality, cited=(), absent=(), counts=(), considered=(), nir=None):
    Q.append(dict(id=id_, name=name, description=desc, score_type=stype, max_score=mx, pred=pred, score=score,
                  score_label=label, evidence=evidence, quality_note=quality, cited=list(cited), absent=list(absent),
                  counts=list(counts), considered=list(considered), nir=nir))


C = lambda path, quote=None: ({"path": path, "quote": quote} if quote else {"path": path})
A = lambda path: {"path": path}

q(1, "Field Completeness", "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
  "numeric", 5, None, 3, "Good (~70% populated)",
  "10 of 14 listed fields populated (id, title, description, keywords, license_and_use_terms, doi, page, creators, purposes, instances); top-level resources, parent_datasets, variables and regulatory_restrictions.confidentiality_level are absent.",
  "10/14 = 71%, matching the ~70% anchor. Missing variable-level metadata and a structured confidentiality level are substantive for a multimodal clinical dataset; file-level resources exist only nested under file_collections.",
  cited=[C("id", "doi:10.60775/fairhub.3"), C("title", "Flagship Dataset of Type 2 Diabetes"), C("description"), C("keywords"), C("license_and_use_terms"),
         C("doi", "10.60775/fairhub.3"), C("page", "https://fairhub.io/datasets/3"), C("creators"), C("purposes"), C("instances")],
  absent=[A("/resources"), A("parent_datasets"), A("variables"), A("regulatory_restrictions.confidentiality_level")],
  counts=[{"path": "creators", "claimed": 21}, {"path": "purposes", "claimed": 2}])

q(2, "Entry Length Adequacy", "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
  "numeric", 5, None, 5, "Excellent (>200 chars)",
  "description is roughly 1,000 characters covering version, cohort size, collection window, modalities, file count/size and CDS layout; both purposes have descriptions over 200 characters.",
  "Narratives are long and substantive, not padded; description content matches the referent (v3.0.0 on FAIRhub).",
  cited=[C("description", "harmonized across three data collection sites"), C("/purposes/0/description", "salutogenic pathways to return to health"),
         C("/purposes/1/description", "temporal atlas")])

q(3, "Keyword Diversity", "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply additional topic evidence where documented; no named study or disease count is presumed.",
  "numeric", 5, None, 3, "Good (3-7 keywords)",
  "7 distinct keywords: Diabetes mellitus, Machine Learning, Artificial Intelligence, Electrocardiography, Continuous Glucose Monitoring, Retinal imaging, Eye exam.",
  "Seven relevant keywords falls in the 3-7 band. Modalities such as OCT, wearables and environmental sensors are not reflected in keywords.",
  cited=[C("keywords")], counts=[{"path": "keywords", "claimed": 7}],
  nir="Score follows the keyword-count anchor (7 < 8); the keywords themselves are accurate, so no defect issue is filed.")

q(4, "File Enumeration and Type Variety", "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in separate linked resources. Examine every distribution; modality breadth is distinct from suitability for machine learning.",
  "numeric", 5, None, 5, "Excellent (>3 file types)",
  "distribution_formats lists DICOM, Markdown, CSV and JSON; file_collections add TSV and TXT resources and WFDB/Open mHealth/ESDS-conformant collections; total_file_count 356343 with per-collection file_count values.",
  "More than three file types, enumerated per data-type directory with counts and bytes; multimodality is stated in the description.",
  cited=[C("distribution_formats"), C("file_collections"), C("total_file_count")],
  counts=[{"path": "distribution_formats", "claimed": 4}, {"path": "file_collections", "claimed": 10}])

q(5, "Data File Size Availability", "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
  "pass_fail", 1, None, 1, "Pass",
  "total_size_bytes 3815969779678; per-collection total_bytes; instances counts 2280; splits 1576/352/352; subpopulation counts.",
  "Numeric size and instance counts present; the record's own arithmetic reconciling collection sums against totals is transparent.",
  cited=[C("total_size_bytes"), C("/file_collections/0/total_bytes"), C("/instances/0/counts"), C("splits"), C("subpopulations")])

q(6, "Dataset Identification Metadata", "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or repository).",
  "pass_fail", 1, None, 1, "Pass",
  "doi 10.60775/fairhub.3 (FAIRhub DataCite prefix), id doi:10.60775/fairhub.3, page https://fairhub.io/datasets/3, publisher https://fairhub.io/.",
  "Persistent identifier and hosting platform both present and mutually consistent.",
  cited=[C("doi", "10.60775/fairhub.3"), C("id"), C("page"), C("publisher", "https://fairhub.io/")])

q(7, "Funding and Acknowledgements Completeness", "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
  "numeric", 5, None, 5, "Excellent (funders with grants + affiliated creators)",
  "NIH funder with grants OT2OD032644, P30DK035816, UL1TR003096; Research to Prevent Blindness; creators with ORCIDs and ROR-identified affiliations.",
  "Grant numbers follow NIH activity/IC/serial patterns; the record even documents the OT2ODO32644 typo in a source. Two creators (Ishikawa, Nebeker) lack affiliations, with the reason stated; this does not undercut the 5-band.",
  cited=[C("/funders/0/grants/0/grant_number", "OT2OD032644"), C("/funders/0/grants/1/grant_number", "P30DK035816"), C("/funders/0/grants/2/grant_number", "UL1TR003096"),
         C("/creators/1/principal_investigator/affiliation"), C("/funders/1/name", "Research to Prevent Blindness")],
  counts=[{"path": "funders", "claimed": 2}])

q(8, "Ethical and Privacy Declarations", "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable.",
  "numeric", 5, "human_subjects", 5, "Excellent (comprehensive protections)",
  "UW IRB approval STUDY00016228 with reliance agreements; written/e-consent with scope and withdrawal; deidentification statement; four participant_privacy safeguards; $200 stipend; regulatory compliance; re-identification risk noted in future_use_impacts.",
  "Covers oversight, consent, revocation, privacy, compensation and compliance in depth. Gaps (no at_risk_populations, no data_protection_impacts field, no hipaa_compliant flag, no governance contact) and a deidentification-method tension are noted but do not reduce the comprehensive picture below the top band.",
  cited=[C("ethical_reviews"), C("human_subject_research"), C("is_deidentified"), C("participant_privacy"), C("participant_compensation"),
         C("informed_consent"), C("regulatory_restrictions.other_compliance"), C("/human_subject_research/irb_approval")],
  absent=[A("at_risk_populations"), A("data_protection_impacts"), A("regulatory_restrictions.hipaa_compliant"), A("regulatory_restrictions.governance_committee_contact")])

q(9, "Access Requirements and Governance Documentation", "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts.",
  "numeric", 5, None, 5, "Excellent (license + restrictions + confidentiality)",
  "AI-READI Data License Agreement v2.0 with detailed terms; ip_restrictions; NIH GDS-policy compliance; access review via verified ID and self-attestation; source_caveats distinguish the public set (no confidential data or PII) from the controlled-access set under a DUA.",
  "License, restrictions and a public-vs-controlled confidentiality distinction are documented in substance. The structured confidentiality_level and governance committee contact are absent; the disease-specific vs commercial-use tension is recorded transparently.",
  cited=[C("license_and_use_terms", None), C("/license_and_use_terms/license_terms", "non-exclusive"), C("ip_restrictions"), C("regulatory_restrictions"),
         C("regulatory_restrictions.other_compliance", "Genomic Data Sharing"), C("/data_governance/access_review_process", "self-attestation required"),
         C("/source_caveats", "contains no confidential data or personally identifiable information")],
  absent=[A("regulatory_restrictions.confidentiality_level"), A("regulatory_restrictions.governance_committee_contact"), A("data_protection_impacts"), A("regulatory_restrictions.hipaa_compliant")])

q(10, "Interoperability, Standardization, and Cross-Platform Integration", "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures.",
  "numeric", 5, "shared_dataset", 5, "Excellent (standards + schema conformance + integration)",
  "Collections conform to DICOM, OMOP CDM, WFDB, Open mHealth, ESDS and CDS v0.1.1; clinical CSVs map one-to-one to OMOP CDM tables with a DQD JSON; preprocessing maps data to standard terminologies.",
  "Standard formats plus explicit data-model conformance (OMOP CDM) give real integration capability. No conforms_to_schema URI or related_datasets entries.",
  cited=[C("distribution_formats"), C("conforms_to", "Clinical Data Structure (CDS) v0.1.1"), C("/file_collections/1/conforms_to", "Observational Medical Outcomes Partnership"),
         C("external_resources")],
  absent=[A("conforms_to_schema"), A("related_datasets")])

q(11, "Tool and Software Transparency", "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs.",
  "numeric", 5, "data_processing", 3, "Good (strategies listed, no versions/URLs)",
  "Preprocessing: DICOM conversion, mapping to OMOP CDM/DICOM; cleaning: site QC, internal PII review, REDCap range checks; missingness documented. No software names/versions for the conversion or mapping pipelines, no URLs.",
  "Strategies are clear but the tools that performed conversion (fda/sdt to DICOM, FIT to Open mHealth, REDCap to OMOP) are unnamed and unversioned, so the 5-band software criterion is not met.",
  cited=[C("preprocessing_strategies"), C("cleaning_strategies"), C("missing_data_documentation"), C("/preprocessing_strategies/0/preprocessing_details", "conversion to a DICOM standard format")],
  absent=[A("labeling_strategies"), A("machine_annotation_tools"), A("annotation_analyses"), A("imputation_protocols")])

q(12, "Collection Protocol Clarity", "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
  "numeric", 5, "data_collection", 5, "Excellent (full protocol)",
  "Acquisition methods (observed vs subject-reported), ~25 named instruments with protocols, data collectors with training/certification, dated timeframes, raw source formats.",
  "Full protocol: mechanisms, collectors and timeframes are specific and consistent (pilot 2023-07-18 to 2023-11-30; v3 window 2023-07-19 to 2025-05-01, issued 2025-11-17).",
  cited=[C("acquisition_methods"), C("collection_mechanisms"), C("data_collectors"), C("collection_timeframes"), C("raw_data_sources"),
         C("/collection_timeframes/2/end_date", "2025-05-01")],
  counts=[{"path": "collection_mechanisms", "claimed": 24}])

q(13, "Version History, Maintenance, and Sustainability", "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access.",
  "numeric", 5, "shared_dataset", 3, "Good (versioning + access + PID; sustainability incomplete)",
  "version 3.0.0; versions_available with DOIs for 1.0.0-3.0.0; change notes (Snellen variables dropped); yearly static releases; maintainers with contact URL; hosting on FAIRhub/Azure. Errata absent; version 2.0.0 is stated to be no longer accessible.",
  "Versioning is strong, but there is no preservation commitment for released versions (a DOI-bearing prior version is withdrawn), no errata, and no stated long-term sustainability plan beyond the project's duration.",
  cited=[C("version", "3.0.0"), C("version_access"), C("updates"), C("maintainers"), C("doi"), C("publisher"),
         C("/version_access/version_details", "version 2.0.0 is no longer accessible")],
  absent=[A("errata")])

q(14, "Associated Publications", "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources.",
  "numeric", 5, None, 3, "Good (distinct references, no formal citation)",
  "Four distinct external resources (docs.aireadi.org, aireadi.org, Zenodo community, GitHub org) and the dataset DOI; no citation field. BMJ Open and Nature Metabolism publications are mentioned by name only, without identifiers.",
  "At least one distinct reference is documented but no formal dataset citation is present, so the 5-band condition is not met.",
  cited=[C("external_resources"), C("doi")], absent=[A("citation")], counts=[{"path": "external_resources", "claimed": 4}])

q(15, "Human Subject Representation", "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups.",
  "numeric", 5, "human_subjects", 5, "Excellent (demographics + inclusion/exclusion)",
  "Subpopulation counts by race/ethnicity, diabetes status and sex with per-split breakdowns; mean age; inclusion/exclusion criteria and triple-balanced recruitment in sampling_strategies; missingness by modality.",
  "Detailed demographics and eligibility criteria; the record notes that demographics are not released in the public set and that the healthsheet denies identifying subpopulations, which it records as a caveat. at_risk_populations is absent.",
  cited=[C("instances"), C("subpopulations"), C("/subpopulations/0/distribution", "Hispanic 380, Asian 545, Black 519, White 836"), C("missing_data_documentation")],
  considered=["sampling_strategies"], absent=[A("at_risk_populations")])

q(16, "Findability (Persistent Links)", "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
  "pass_fail", 1, None, 1, "Pass",
  "page https://fairhub.io/datasets/3, DOI, and four external resource URLs.",
  "Well-formed URLs on plausible domains; DOI resolves through doi.org by format.",
  cited=[C("page"), C("doi"), C("id"), C("external_resources")], absent=[A("download_url")])

q(17, "Accessibility (Access Mechanism)", "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
  "numeric", 5, "shared_dataset", 5, "Excellent (platform, login, policy)",
  "Access via FAIRhub: verified-ID login, agreement to type 2 diabetes-only use and the license (public download with self-attestation); controlled-access tier via DUA described separately; formats listed.",
  "Access tier is stated (registration + license attestation, not unrestricted), with platform and policy. download_url is absent but the landing page gives the path.",
  cited=[C("distribution_formats"), C("license_and_use_terms"), C("/data_governance/access_review_process", "logging in through a verified ID system"), C("page")],
  absent=[A("download_url")])

q(18, "Reusability, Use Guidance, and Social Impact", "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis with risk identification and mitigation strategies.",
  "numeric", 5, None, 3, "Good (license + basic use guidance)",
  "License terms and five detailed prohibited uses; purposes/tasks indicate intended research use. intended_uses and discouraged_uses fields are absent; future_use_impacts has one entry (theoretical re-identification risk) without a mitigation in that entry.",
  "Use guidance is strong on prohibitions but the social impact analysis is minimal and lacks mitigation strategies tied to identified risks.",
  cited=[C("license_and_use_terms"), C("prohibited_uses"), C("/future_use_impacts/0/impact_details", "theoretical risk of future re-identification")],
  considered=["purposes", "tasks"], absent=[A("intended_uses"), A("discouraged_uses")], counts=[{"path": "prohibited_uses", "claimed": 5}])

q(19, "Data Integrity, Provenance Graph, and Quality", "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation.",
  "numeric", 5, None, 3, "Good (version history + partial lineage)",
  "version_access, updates, splits, missing_data_documentation and raw_data_sources (xml, csv, fda, sdt, FIT with conversion targets) are present. No was_derived_from, parent_datasets, errata or subsets; lineage for several modalities (ECG to WFDB, environment to ESDS) and the activities' tools are not stated.",
  "Textual lineage exists for some modalities with agents (site data managers, NORC), but it is not a complete entity-activity-agent provenance account.",
  cited=[C("version_access"), C("updates"), C("missing_data_documentation"), C("splits"), C("raw_data_sources"),
         C("/raw_data_sources/2/source_description", "converted to DICOM for the dataset")],
  considered=["preprocessing_strategies", "data_collectors"],
  absent=[A("errata"), A("was_derived_from"), A("parent_datasets"), A("subsets")])

q(20, "Bias Documentation and Responsible AI Alignment", "Documentation of known biases, limitations and potential effects on intended or foreseeable uses.",
  "numeric", 5, None, 3, "Good (basic bias identification)",
  "One known bias (volunteer bias, bias_type selection_bias) and four limitations (English-only, unbalanced groups, urban/hospital recruitment, missing races); balanced splits aimed at reducing disparities.",
  "Biases are identified and one is typed, but there is no systematic categorization across a standard taxonomy and no fairness analysis.",
  cited=[C("known_biases"), C("/known_biases/0/bias_type", "selection_bias"), C("future_use_impacts")],
  considered=["known_limitations", "splits"], counts=[{"path": "known_biases", "claimed": 1}])

ISSUES = [
    dict(item_ids=["Q1"], score_effect="lowered", category="variables_metadata", type="completeness",
         description="No variables, parent_datasets, top-level resources or regulatory_restrictions.confidentiality_level; ~71% of Q1 fields populated."),
    dict(item_ids=["Q11"], score_effect="lowered", category="processing_provenance", type="completeness",
         description="Processing strategies name no conversion/mapping software, versions or URLs (fda/sdt to DICOM, FIT to Open mHealth, REDCap to OMOP CDM)."),
    dict(item_ids=["Q13"], score_effect="lowered", category="temporal_version", type="completeness",
         description="No errata or long-term preservation commitment; version_details states DOI-bearing version 2.0.0 is no longer accessible."),
    dict(item_ids=["Q14"], score_effect="lowered", category="attribution", type="completeness",
         description="No formal dataset citation; associated publications (BMJ Open protocol, Nature Metabolism comment) are named without identifiers."),
    dict(item_ids=["Q18"], score_effect="lowered", category="license_use_terms", type="completeness",
         description="intended_uses and discouraged_uses absent; future_use_impacts holds one risk without mitigation."),
    dict(item_ids=["Q19"], score_effect="lowered", category="processing_provenance", type="completeness",
         description="Lineage only partial: no was_derived_from/parent links and conversion paths stated for only some modalities."),
    dict(item_ids=["Q20"], score_effect="lowered", category="bias_quality", type="completeness",
         description="Single typed bias; no standard-taxonomy categorization or fairness analysis."),
    dict(item_ids=[], score_effect="noted_only", category="privacy_regulatory", type="consistency",
         description="is_deidentified.method states NoDeIdentification (no identifiers collected) while identifiers_removed says sex, race/ethnicity and medications were removed and a source cites Safe Harbor; the record documents the conflict in source_caveats."),
    dict(item_ids=[], score_effect="noted_only", category="license_use_terms", type="consistency",
         description="data_use_permission is disease_specific_research while license_terms grant research, commercial and non-commercial use; recorded transparently as a source conflict."),
    dict(item_ids=[], score_effect="noted_only", category="consent_ethics", type="completeness",
         description="human_subject_research is true but at_risk_populations and data_protection_impacts are not populated (source_caveats says no DPIA was conducted)."),
    dict(item_ids=[], score_effect="noted_only", category="temporal_version", type="content_accuracy",
         description="Source documents disagree on year labels for releases (README 'year 3 data' vs healthsheet first/second year); recorded as caveats."),
]

CATS = [("Structural Completeness", range(1, 6)), ("Metadata Quality & Content", range(6, 11)),
        ("Technical Documentation", range(11, 16)), ("FAIRness & Accessibility", range(16, 21))]

EXTRA = [  # (severity, fields_involved, recommendation), aligned with ISSUES order
    ("medium", ["variables", "parent_datasets", "resources", "regulatory_restrictions.confidentiality_level"],
     "Add variable-level metadata (at least per modality), a structured confidentiality level and top-level resources."),
    ("medium", ["preprocessing_strategies", "cleaning_strategies"],
     "Name the conversion and ETL software with versions and repository URLs for each modality."),
    ("medium", ["version_access", "errata", "maintainers"],
     "State a preservation commitment for released versions, add errata, and explain the withdrawal of version 2.0.0."),
    ("low", ["citation", "external_resources"],
     "Add a formal dataset citation and identifiers (DOIs) for the BMJ Open protocol and Nature Metabolism comment."),
    ("medium", ["intended_uses", "discouraged_uses", "future_use_impacts"],
     "Populate intended and discouraged uses and pair each identified risk with a mitigation."),
    ("medium", ["was_derived_from", "parent_datasets", "raw_data_sources", "preprocessing_strategies"],
     "Document per-modality derivation paths (raw format, activity, agent/tool, released format)."),
    ("medium", ["known_biases", "future_use_impacts"],
     "Categorize further biases (measurement, device, site, sampling) with a standard taxonomy and add a fairness analysis."),
    ("low", ["is_deidentified", "source_caveats"],
     "Reconcile the deidentification method across sources or state which applies to the public release."),
    ("low", ["license_and_use_terms"],
     "Clarify whether the public release is limited to type 2 diabetes research or permits commercial use."),
    ("low", ["at_risk_populations", "data_protection_impacts"],
     "Populate at_risk_populations and record the DPIA status in data_protection_impacts."),
    ("low", ["version_access"],
     "Harmonize the release year labels or explain the differing conventions."),
]
assert len(EXTRA) == len(ISSUES)
for issue, (sev, fields, rec) in zip(ISSUES, EXTRA):
    issue.update(severity=sev, fields_involved=fields, recommendation=rec)

context = normalize_context({})
byid = {x["id"]: x for x in Q}
categories = []
total = 0
mx_total = 0
excluded = 0
na = 0
for cname, ids in CATS:
    qs = []
    cs = cm = 0
    for i in ids:
        x = byid[i]
        pred = x["pred"]
        row = {"path": "#", "score": x["score"], "evidence": x["evidence"], "cited": x["cited"], "absent": x["absent"],
               "counts": x["counts"], "considered": x["considered"]}
        item = {"id": i, "name": x["name"], "description": x["description"], "score_type": x["score_type"],
                "score": x["score"], "max_score": x["max_score"], "score_label": x["score_label"], "evidence": x["evidence"],
                "quality_note": x["quality_note"], "applicable": True,
                "applicability_status": "unknown" if pred else "applicable",
                "applicability_evidence": unknown(pred) if pred else ALWAYS, "unit_scores": [row]}
        if x["nir"]:
            item["no_issue_reason"] = x["nir"]
        qs.append(item)
        cs += x["score"]
        cm += x["max_score"]
    total += cs
    mx_total += cm
    categories.append({"name": cname, "questions": qs, "category_score": cs, "category_max": cm})

assert mx_total == 88
doc = {
    "rubric": "rubric20-semantic", "version": "3.0", "d4d_file": INPUT, "project": "AI_READI", "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {"name": MODEL, "evaluator_model": MODEL, "temperature": None,
              "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
              "evaluation_type": "semantic_llm_judge"},
    "overall_score": {"total_points": total, "max_points": 88, "excluded_max_points": excluded, "adjusted_max_points": 88 - excluded,
                      "normalized_percentage": round(total / (88 - excluded) * 100, 1), "fixed_percentage": round(total / 88 * 100, 1),
                      "questions_not_applicable": na, "excluded_item_ids": []},
    "categories": categories,
    "semantic_analysis": {
        "issues_detected": ISSUES,
        "semantic_insights": [
            "Record is source-transparent: conflicts (license naming, deidentification method, grant typo, version wording) are recorded in source_caveats rather than silently resolved.",
            "Temporal ordering is consistent: pilot enrollment 2023-07-18, v3 collection 2023-07-19 to 2025-05-01, release 2025-11-17; versions 1.0.0 (2024-05-03), 2.0.0 (2024-11-08), 3.0.0 (2025-11-17).",
            "Public vs controlled-access tiers are distinguished; 'public download' is correctly qualified by verified-ID login and license self-attestation.",
            "Human subjects logic holds: involves_human_subjects true with ethical_reviews and informed_consent populated.",
        ],
        "consistency_checks": {"passed": 6, "failed": 0, "warnings": 3},
        "correctness_validations": {
            "doi_format": "valid: 10.60775/fairhub.3 matches 10.XXXX/ pattern (FAIRhub DataCite prefix); prior versions 10.60775/fairhub.1 and .2",
            "grant_number_format": "valid: OT2OD032644, P30DK035816, UL1TR003096 follow NIH activity-IC-serial patterns",
            "rrid_format": "not_present: no RRIDs in the record",
            "url_validity": "valid structure: fairhub.io, docs.aireadi.org, aireadi.org, zenodo.org, github.com",
        },
    },
    "applicability_context": {},
    "evaluation_scope": {"policy": "single_dataset", "units": [{"path": "#", "id": "doi:10.60775/fairhub.3"}],
                         "collection_metadata_inherited": False},
    "metadata": {
        "instrument_sha256": sha(".claude/agents/d4d-rubric20-semantic.md"),
        "evidence_authority_sha256": sha("data/rubric/semantic_evidence_authority_v3.json"),
        "rubric_sha256": sha("data/rubric/rubric20.txt"),
        "input_sha256": sha(INPUT),
        "context_sha256": context_digest(context),
    },
}
out = ROOT / OUT
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(out, total)
