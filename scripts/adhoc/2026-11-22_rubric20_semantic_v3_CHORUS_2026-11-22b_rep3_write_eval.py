#!/usr/bin/env python3
"""Write the rubric20-semantic v3 (general context instrument) evaluation of one CHORUS record.

Purpose: serialize the judgements made by the evaluating session (claude-opus-5-5) for
  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CHORUS_d4d.yaml
Inputs: that D4D record (hashed only), .claude/agents/d4d-rubric20-semantic.md,
  data/rubric/rubric20.txt, data/rubric/semantic_evidence_authority_v3.json (hashed).
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep3_evaluation.json
No caller applicability context: empty context, all conditional predicates unknown.
Date: 2026-11-22.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest, normalize_context  # noqa: E402

D4D = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CHORUS_d4d.yaml"
OUT = ROOT / "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep3_evaluation.json"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


ALWAYS = ("applicable", "This item applies to every dataset")


def unknown(pred):
    return ("unknown", f"{pred}: not declared (no caller applicability context); retained in the denominator")


DESC = {
    1: "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and c",
    2: "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
    3: "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply addit",
    4: "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in sep",
    5: "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
    6: "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or ",
    7: "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
    8: "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks,",
    9: "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confid",
    10: "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedure",
    11: "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versio",
    12: "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timef",
    13: "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durab",
    14: "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resourc",
    15: "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups. Evaluate ",
    16: "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
    17: "Describes how users can obtain the dataset (download URL, distribution formats, access policy).\nNote: \"Public\" does not ",
    18: "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND co",
    19: "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation",
    20: "Documentation of known biases, limitations and potential effects on intended or foreseeable uses. Every dataset has a sc",
}


def q(qid, name, stype, score, label, evidence, quality, semantic, app, cited=(), absent=(), counts=(), considered=(),
      no_issue_reason=None):
    status, app_ev = app
    item = {
        "id": qid, "name": name, "description": DESC[qid], "score_type": stype, "score": score,
        "max_score": 1 if stype == "pass_fail" else 5, "score_label": label, "evidence": evidence,
        "quality_note": quality, "semantic_analysis": semantic, "applicable": True,
        "applicability_status": status, "applicability_evidence": app_ev,
        "unit_scores": [{
            "path": "#", "score": score, "evidence": evidence,
            "cited": [dict(c) if isinstance(c, dict) else {"path": c} for c in cited],
            "absent": [{"path": a} for a in absent],
            "counts": [{"path": p, "claimed": n} for p, n in counts],
            "considered": list(considered),
        }],
    }
    if no_issue_reason:
        item["no_issue_reason"] = no_issue_reason
    return item


C1 = [
    q(1, "Field Completeness", "numeric", 3, "Good (about 64% of listed fields populated)",
      "Populated: id, title, description, keywords, license_and_use_terms, page, creators, purposes, instances (9 of 14). "
      "Absent: doi, resources, parent_datasets, variables, regulatory_restrictions.confidentiality_level.",
      "9/14 = 64%, above the 40% floor and nearest the ~70% anchor; well short of 90%.",
      "license_and_use_terms is populated but states that the agreement's terms are unknown, so its content is thin; "
      "id reuses the project website URL rather than a dataset identifier.",
      ALWAYS,
      cited=["id", "title", "description", "keywords", "license_and_use_terms", "page", "creators", "purposes", "instances"],
      absent=["doi", "resources", "parent_datasets", "variables", "regulatory_restrictions.confidentiality_level"]),
    q(2, "Entry Length Adequacy", "numeric", 5, "Excellent (>200 chars)",
      "description is about 1,830 characters; the two purposes responses are about 221 and 258 characters.",
      "All narrative fields exceed 200 characters and carry specific content (counts, modalities, standards, plans).",
      "Description distinguishes current release figures from planned figures and attributes each to its source.",
      ALWAYS,
      cited=[{"path": "description", "quote": "1.6 billion rows of EHR OMOP data"},
             {"path": "/purposes/0/response", "quote": "develop a publicly available, AI-ready critical care dataset"}],
      counts=[("purposes", 2)]),
    q(3, "Keyword Diversity", "numeric", 3, "Good (3-7 keywords)",
      "keywords lists 7 terms: Critical Care, Critical Illness, Electronic Health Record, Electroencephalography, "
      "Machine Learning, social health determinants, data standards.",
      "Seven distinct keywords sits in the 3-7 band; imaging, waveform telemetry, OMOP, ICU/PICU/NICU and pediatrics are not keywords.",
      "Keywords match the documented content; capitalization is inconsistent but terms are relevant.",
      ALWAYS, cited=["keywords"], counts=[("keywords", 7)]),
    q(4, "File Enumeration and Type Variety", "numeric", 3, "Good (2-3 file types, inferred from standards)",
      "No distribution_formats, file_collections or total_file_count. conforms_to: 'OMOP, DICOM, WFDB'; instances name "
      "DICOM imaging, WFDB waveform telemetry and EDF+ EEG.",
      "File types are only implied by data standards (DICOM, WFDB, EDF+; OMOP is a data model, not a file format); "
      "no distribution format, media type or file enumeration is documented.",
      "The record describes multi-modal data (EHR, notes, imaging, telemetry, EEG) consistent with the implied formats, "
      "but it never states what files a user receives from the enclave.",
      ALWAYS,
      cited=[{"path": "conforms_to", "quote": "OMOP, DICOM, WFDB"},
             {"path": "/instances/10/description", "quote": "with data standard EDF+ and Persyst"}],
      absent=["distribution_formats", "file_collections", "total_file_count"],
      considered=["conforms_to_standard", "instances"]),
    q(5, "Data File Size Availability", "pass_fail", 1, "Pass",
      "instances counts 50000 patient admissions and 7642 admissions with radiology data; description reports "
      "'23 Tb of waveform data' and '1.6 billion rows of EHR OMOP data'.",
      "Instance counts and a waveform volume are present; no total_size_bytes.",
      "'23 Tb' is ambiguous (terabits vs terabytes); the record flags it as the website's unit as written.",
      ALWAYS,
      cited=[{"path": "/instances/0/counts"}, {"path": "/instances/1/counts"},
             {"path": "description", "quote": "23 Tb of waveform data"}],
      counts=[("instances", 11)], considered=["splits", "subpopulations"]),
]

C2 = [
    q(6, "Dataset Identification Metadata", "pass_fail", 1, "Pass (link only)",
      "id and page are https://chorus4ai.org/; no doi and no publisher.",
      "A resolvable project link is present, which meets the pass criterion, but it is a project website rather than a "
      "persistent dataset identifier, and no hosting platform/publisher is named.",
      "id identifies the project, not a versioned dataset; no DOI or RRID.",
      ALWAYS, cited=["id", "page"], absent=["doi", "publisher"]),
    q(7, "Funding and Acknowledgements Completeness", "numeric", 5, "Excellent",
      "funders: NIH Common Fund with grant OT2OD032701 ('Bridge2AI: Patient-Focused Collaborative Hospital Repository "
      "Uniting Standards (CHoRUS) for Equitable AI'); six creators each with an institutional affiliation.",
      "Funder, award number, award title, dates and amount are documented; every creator has an affiliation.",
      "OT2OD032701 matches the NIH activity/IC/serial pattern and agrees with '1OT2OD032701-01'. The record itself notes "
      "the creators are the leadership team, not stated dataset authors.",
      ALWAYS,
      cited=[{"path": "/funders/0/grants/0/grant_number", "quote": "OT2OD032701"},
             {"path": "/creators/0/affiliations/0/name", "quote": "Massachusetts General Hospital"}],
      counts=[("creators", 6)]),
    q(8, "Ethical and Privacy Declarations", "numeric", 3, "Basic (partial deidentification only)",
      "is_deidentified covers imaging only ('de-identification in process for a larger cohort'); description cites "
      "planned 'approaches that limit re-identification'; clinical notes are tokenized. No ethical_reviews, "
      "human_subject_research, informed_consent, participant_privacy or data_protection_impacts.",
      "An ethics/privacy field is present, so the 0 anchor does not hold; the 3 anchor (IRB + deidentification) is only "
      "half met because no ethics review is documented. Scored 3 with that uncertainty recorded; nowhere near 5.",
      "Data from 50,000 patient admissions are plainly human-subject clinical data, yet no review board, consent/waiver, "
      "or HIPAA status is stated; deidentification is described only for imaging and as in process.",
      unknown("human_subjects"),
      cited=[{"path": "is_deidentified.deidentification_details", "quote": "de-identification in process for a larger cohort"},
             {"path": "description", "quote": "transform data using approaches that limit re-identification"}],
      absent=["ethical_reviews", "human_subject_research", "informed_consent", "participant_privacy",
              "data_protection_impacts", "participant_compensation", "at_risk_populations", "regulatory_restrictions"]),
    q(9, "Access Requirements and Governance Documentation", "numeric", 3, "Good (agreement and access process, no classification)",
      "license_and_use_terms: participants 'must sign a licensing agreement' whose terms are not stated; "
      "data_governance.access_review_process: controlled access, registration form, .edu email, access contacts.",
      "Access tiering (controlled; registration plus signed agreement) is described, but no license name or terms, IP "
      "restrictions, regulatory obligations or confidentiality classification.",
      "The record correctly declines to apply the GitHub MIT license to the dataset (source_caveats).",
      ALWAYS,
      cited=[{"path": "license_and_use_terms.license_terms", "quote": "must sign a licensing agreement"},
             {"path": "license_and_use_terms.source_caveats", "quote": "The documents do not state the terms of the licensing agreement."},
             {"path": "data_governance.access_review_process", "quote": "Access is controlled"}],
      absent=["ip_restrictions", "regulatory_restrictions", "data_protection_impacts"],
      considered=["source_caveats"]),
    q(10, "Interoperability, Standardization, and Cross-Platform Integration", "numeric", 5, "Excellent",
      "conforms_to_standard: OMOP_CDM, DICOM, WFDB; EEG in EDF+; preprocessing describes 'validated semantic mappings for "
      "connecting clinical data in various source formats to international standards' and SOPs for interoperable delivery.",
      "Standard formats plus common data model conformance (OMOP CDM) and a documented mapping/integration route meet the 5 anchor, "
      "though no distribution_formats, schema URI/version or related_datasets are given.",
      "conforms_to is a free-text string, and OMOP CDM version and vocabularies are unspecified; the strength is in "
      "the documented standardization process rather than machine-readable conformance.",
      unknown("shared_dataset"),
      cited=["conforms_to", "conforms_to_standard",
             {"path": "/preprocessing_strategies/0/preprocessing_details", "quote": "validated semantic mappings"},
             "external_resources"],
      absent=["distribution_formats", "conforms_to_schema", "related_datasets"],
      no_issue_reason="Scored at maximum."),
]

C3 = [
    q(11, "Tool and Software Transparency", "numeric", 3, "Good (strategies listed, no versions)",
      "preprocessing_strategies: semantic mapping and clinical validation via the chorus-mapping repository; instances "
      "note clinical notes 'extracted and tokenized using the OHNLP toolkit' and EEG with Persyst.",
      "At least one strategy and tool are named, but no versions, tool URLs, cleaning, labeling, imputation or "
      "missing-data documentation.",
      "Tools are named only within free-text descriptions; Persyst is listed as a 'data standard' though it is software.",
      unknown("data_processing"),
      cited=["preprocessing_strategies", {"path": "/instances/7/description", "quote": "OHNLP toolkit"}],
      absent=["cleaning_strategies", "labeling_strategies", "machine_annotation_tools", "imputation_protocols",
              "missing_data_documentation", "annotation_analyses"]),
    q(12, "Collection Protocol Clarity", "numeric", 3, "Partial",
      "collection_mechanisms: retrospective collection; sites create CHoRUS-specific extracts following the Chorus_SOP workflow. "
      "Description: 14 contributing hospitals.",
      "Mechanism and contributing sites are described; no acquisition_methods, named data_collectors, "
      "collection_timeframes or raw_data_sources fields (sources such as PACS and bedside monitors appear only in instances).",
      "No date range for the retrospective extraction is given, so temporal coverage of admissions is unknown.",
      unknown("data_collection"),
      cited=[{"path": "/collection_mechanisms/0/mechanism_details", "quote": "Retrospective data collection"},
             "/collection_mechanisms/1/mechanism_details"],
      absent=["acquisition_methods", "data_collectors", "collection_timeframes", "raw_data_sources"],
      counts=[("collection_mechanisms", 2)], considered=["instances", "description"]),
    q(13, "Version History, Maintenance, and Sustainability", "numeric", 0, "Absent",
      "No version, version_access, errata, updates, maintainers, doi or publisher. Only 'current released dataset' in "
      "description and access contacts in data_governance.",
      "No version identifier, change history, maintenance or preservation plan.",
      "source_caveats quotes a banner that the site is 'under review for potential modification', which is a "
      "sustainability risk left unaddressed by any maintenance documentation.",
      unknown("shared_dataset"),
      absent=["version", "version_access", "errata", "updates", "maintainers", "doi", "publisher"],
      considered=["description", "data_governance", "source_caveats", "notes"]),
    q(14, "Associated Publications", "numeric", 3, "One external resource, no formal citation",
      "external_resources: CHoRUS GitHub organization (https://github.com/chorus-ai#table-of-contents). No citation, no doi.",
      "One distinct non-publication reference is documented; no formal dataset citation or second reference.",
      "existing_uses mentions 'Publications' without naming any.",
      ALWAYS,
      cited=["external_resources"], absent=["citation", "doi"], considered=["existing_uses", "page"]),
    q(15, "Human Subject Representation", "numeric", 3, "General population, units only",
      "instances count 50000 admissions; subpopulations ICU, PICU, NICU.",
      "Care-unit subgroups are named but there are no demographics, age/sex/race distributions, or inclusion/exclusion criteria; "
      "per-unit counts are not given.",
      "The project aims at a 'most diverse' dataset (purposes) but no representation data supports it.",
      unknown("human_subjects"),
      cited=["/instances/0/counts", "subpopulations"],
      absent=["at_risk_populations", "missing_data_documentation", "subsets"],
      counts=[("subpopulations", 3)], considered=["purposes"]),
]

C4 = [
    q(16, "Findability (Persistent Links)", "pass_fail", 1, "Pass",
      "page https://chorus4ai.org/; external resource https://github.com/chorus-ai#table-of-contents.",
      "External URLs are present; none is a persistent identifier (no DOI).",
      "URLs are well formed on plausible domains.",
      ALWAYS, cited=["page", "id", "external_resources"], absent=["doi", "download_url"]),
    q(17, "Accessibility (Access Mechanism)", "numeric", 3, "Partial",
      "data_governance.access_review_process: controlled access; trainees register via a form, need a .edu address, "
      "sign a licensing agreement; contacts dbold@emory.edu or jared.houghtaling@tuftsmedicine.org.",
      "The tier (controlled; registration plus agreement) is stated, but the path is described for training-program "
      "participants only; the enclave platform is unnamed, and there is no download_url or distribution format.",
      "Correctly avoids implying public access; access route for non-trainee researchers is unstated.",
      unknown("shared_dataset"),
      cited=[{"path": "data_governance.access_review_process", "quote": "registration through a form collecting name, email, and"},
             "license_and_use_terms"],
      absent=["download_url", "distribution_formats"]),
    q(18, "Reusability, Use Guidance, and Social Impact", "numeric", 3, "Agreement + basic use guidance",
      "license_and_use_terms: unspecified licensing agreement; tasks list three ML applications; existing_uses: training and publications.",
      "Basic use guidance exists through tasks and existing uses, but no named license, intended/prohibited/discouraged "
      "uses, or social-impact analysis.",
      "Grant title mentions 'Equitable AI' but no impact or mitigation is documented.",
      ALWAYS,
      cited=["license_and_use_terms", "tasks", "existing_uses"],
      absent=["intended_uses", "prohibited_uses", "discouraged_uses", "future_use_impacts"],
      counts=[("tasks", 3)]),
    q(19, "Data Integrity, Provenance Graph, and Quality", "numeric", 3, "Partial textual lineage, no version history",
      "Textual lineage: site extracts via SOP -> semantic mapping and clinical validation -> OMOP; notes tokenized; imaging "
      "deidentification in process. splits: planned holdout test set. source_caveats reconcile source figures.",
      "No version history (the 3 anchor's exemplar) and no derivation graph, but provenance metadata is not absent; the "
      "textual processing lineage is scored 3 with that uncertainty recorded.",
      "The split is a plan, not an existing partition; no parent datasets or raw source fields.",
      ALWAYS,
      cited=[{"path": "/splits/0/split_details", "quote": "Planned"}, "collection_mechanisms", "preprocessing_strategies",
             "source_caveats"],
      absent=["version_access", "errata", "updates", "was_derived_from", "parent_datasets", "missing_data_documentation",
              "raw_data_sources"]),
    q(20, "Bias Documentation and Responsible AI Alignment", "numeric", 0, "Absent",
      "No known_biases or future_use_impacts.",
      "No bias, limitation or impact documentation for the dataset; source_caveats concern source reconciliation, not dataset bias.",
      "Retrospective data from 14 academic hospitals with ICU/PICU/NICU units has evident site and selection-bias questions left undocumented.",
      ALWAYS,
      absent=["known_biases", "future_use_impacts"], considered=["source_caveats", "purposes"]),
]

issues = [
    dict(type="completeness", category="consent_ethics", severity="high", score_effect="lowered", item_ids=["Q8"],
         description="Clinical data from about 50,000 patient admissions, but no ethics review, consent or waiver, "
                     "human_subject_research or participant_privacy declaration; deidentification is stated only for imaging, in process.",
         fields_involved=["ethical_reviews", "informed_consent", "human_subject_research", "is_deidentified", "participant_privacy"],
         recommendation="Document IRB/ethics oversight, consent or waiver basis, HIPAA status and the deidentification method for all modalities."),
    dict(type="completeness", category="persistent_identifier", severity="medium", score_effect="lowered", item_ids=["Q1", "Q13", "Q14"],
         description="No DOI, citation, version or publisher; id is the project website URL rather than a dataset identifier.",
         fields_involved=["doi", "id", "citation", "version", "publisher"],
         recommendation="Add a persistent dataset identifier, version, publisher and a formal dataset citation."),
    dict(type="completeness", category="format_access", severity="medium", score_effect="lowered", item_ids=["Q4", "Q17"],
         description="No distribution_formats, file enumeration or download/enclave access URL; file types are only implied by data standards, "
                     "and the access path is described only for training-program participants.",
         fields_involved=["distribution_formats", "file_collections", "download_url", "data_governance"],
         recommendation="Enumerate the delivered file formats and name the enclave platform and general researcher access route."),
    dict(type="completeness", category="license_use_terms", severity="medium", score_effect="lowered", item_ids=["Q9", "Q18"],
         description="A licensing agreement is required but its terms are unstated; no IP restrictions, confidentiality level, "
                     "intended/prohibited uses or impact analysis.",
         fields_involved=["license_and_use_terms", "regulatory_restrictions", "intended_uses", "prohibited_uses", "future_use_impacts"],
         recommendation="State the data use agreement terms, confidentiality classification and use restrictions."),
    dict(type="completeness", category="bias_quality", severity="medium", score_effect="lowered", item_ids=["Q20", "Q15"],
         description="No known biases, demographics or inclusion/exclusion criteria for a multi-site retrospective critical-care cohort.",
         fields_involved=["known_biases", "subpopulations", "instances"],
         recommendation="Document demographic distributions, per-site/per-unit counts, inclusion criteria and known biases."),
    dict(type="completeness", category="processing_provenance", severity="medium", score_effect="lowered", item_ids=["Q11", "Q12", "Q19"],
         description="Processing and collection are described in text only, without tool versions, collection timeframes, raw source fields, "
                     "missing-data documentation or version history.",
         fields_involved=["preprocessing_strategies", "collection_timeframes", "raw_data_sources", "updates", "missing_data_documentation"],
         recommendation="Add collection date ranges, tool versions, raw sources and a change log."),
    dict(type="completeness", category="variables_metadata", severity="low", score_effect="lowered", item_ids=["Q1", "Q3"],
         description="No variables, resources or parent_datasets; seven keywords omit imaging, waveform and OMOP terms.",
         fields_involved=["variables", "resources", "parent_datasets", "keywords"],
         recommendation="Describe key variables/tables and add modality keywords."),
    dict(type="correctness", category="other", severity="low", score_effect="noted_only", item_ids=[],
         description="notes gives the contact address with domain 'mgh.havard.edu', an apparent misspelling of harvard; the record flags it as written on the site.",
         fields_involved=["notes"],
         recommendation="Verify the contact address before relying on it."),
    dict(type="consistency", category="count_size", severity="low", score_effect="noted_only", item_ids=[],
         description="Admission counts differ by source (50,000 on the website vs over 45K as of August 2025), and '23 Tb' is an ambiguous unit; "
                     "both are disclosed in source_caveats.",
         fields_involved=["instances", "description", "source_caveats"],
         recommendation="Give a dated count for a named release and a byte unit."),
    dict(type="semantic_understanding", category="attribution", severity="low", score_effect="noted_only", item_ids=[],
         description="creators are the project leadership team; the record discloses that dataset authorship roles are not stated.",
         fields_involved=["creators", "source_caveats"],
         recommendation="Record credit roles or authorship when documented."),
]

ctx = normalize_context({})
cats = [("Structural Completeness", C1), ("Metadata Quality & Content", C2),
        ("Technical Documentation", C3), ("FAIRness & Accessibility", C4)]
categories = []
total = 0
for name, qs in cats:
    s = sum(x["score"] for x in qs)
    total += s
    categories.append({"name": name, "questions": qs, "category_score": s,
                       "category_max": sum(x["max_score"] for x in qs)})

result = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": D4D,
    "project": "CHORUS",
    "method": "claudecode_agent",
    "evaluation_timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {
        "name": "claude-opus-5-5",
        "evaluator_model": "claude-opus-5-5",
        "temperature": None,
        "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
        "evaluation_type": "semantic_llm_judge",
    },
    "overall_score": {
        "total_points": total, "max_points": 88, "excluded_max_points": 0, "adjusted_max_points": 88,
        "normalized_percentage": round(total / 88 * 100, 1), "fixed_percentage": round(total / 88 * 100, 1),
        "questions_not_applicable": 0, "excluded_item_ids": [],
    },
    "categories": categories,
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "Strong funding attribution (valid NIH OT2 award number) and documented OMOP/DICOM/WFDB/EDF+ standardization.",
            "Careful source attribution: current versus planned figures and conflicting counts are distinguished and disclosed.",
            "Major gaps in ethics/privacy, versioning, persistent identification, bias and distribution-format documentation.",
        ],
        "consistency_checks": {"passed": 3, "failed": 1, "warnings": 2},
        "correctness_validations": {
            "doi_format": "not_applicable_no_doi",
            "grant_number_format": "valid (OT2OD032701, NIH OT2 activity, OD institute)",
            "rrid_format": "not_applicable_no_rrid",
            "url_validity": "page and GitHub URLs well formed; contact email domain 'mgh.havard.edu' appears misspelled",
        },
    },
    "assessment": {
        "strengths": ["Funding and creator affiliations", "Data standards and semantic mapping process",
                      "Explicit source caveats and controlled-access description"],
        "weaknesses": ["No ethics/IRB/consent documentation", "No version, DOI or citation",
                       "No bias or demographic documentation", "No distribution formats"],
        "recommendations": ["Document ethics oversight and deidentification for all modalities",
                            "Assign a DOI and version with a citation", "Add demographics and known biases",
                            "List delivered file formats and the enclave access route"],
    },
    "applicability_context": ctx,
    "evaluation_scope": {"policy": "single_dataset", "units": [{"path": "#", "id": "https://chorus4ai.org/"}],
                         "collection_metadata_inherited": False},
    "metadata": {
        "instrument_sha256": sha(".claude/agents/d4d-rubric20-semantic.md"),
        "evidence_authority_sha256": sha("data/rubric/semantic_evidence_authority_v3.json"),
        "rubric_sha256": sha("data/rubric/rubric20.txt"),
        "input_sha256": sha(D4D),
        "context_sha256": context_digest(ctx),
        "evaluator_model": "claude-opus-5-5",
        "method_label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3",
    },
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2) + "\n")
print(OUT, total)
