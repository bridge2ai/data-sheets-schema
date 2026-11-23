# Purpose: serialize the manual rubric20-semantic v3 judgements for one D4D record
#   (CHORUS, claudecode_agent, 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1).
# Inputs: the D4D YAML (hashed only), data/rubric/rubric20.txt,
#   .claude/agents/d4d-rubric20-semantic.md, data/rubric/semantic_evidence_authority_v3.json.
# Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep1_evaluation.json
# Scores below are the evaluator's (claude-opus-5-5) judgements; this script only serializes them.
# Date: 2026-11-22
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from data_sheets_schema.evaluation_context import context_digest, normalize_context

ROOT = Path(__file__).resolve().parents[2]
D4D = ROOT / "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/CHORUS_d4d.yaml"
OUT = ROOT / "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep1_evaluation.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ALWAYS = ("applicable", "This item applies to every dataset")


def cond(pred):
    return ("unknown", f"{pred}: not declared by the caller (no applicability context supplied); retained in the denominator")


def q(id_, name, desc, stype, score, label, evidence, note, appl, cited=(), absent=(), counts=(), considered=(), no_issue_reason=None):
    status, appl_ev = appl
    mx = 1 if stype == "pass_fail" else 5
    item = {
        "id": id_, "name": name, "description": desc, "score_type": stype,
        "score": score, "max_score": mx, "score_label": label,
        "evidence": evidence, "quality_note": note,
        "applicable": True, "applicability_status": status,
        "applicability_evidence": appl_ev,
        "unit_scores": [{
            "path": "#", "score": score, "evidence": evidence,
            "cited": [dict(path=c[0], quote=c[1]) if len(c) > 1 and c[1] else {"path": c[0]} for c in cited],
            "absent": [{"path": a} for a in absent],
            "counts": [{"path": p, "claimed": n} for p, n in counts],
            "considered": list(considered),
        }],
    }
    if no_issue_reason:
        item["no_issue_reason"] = no_issue_reason
    return item


cat1 = [
    q(1, "Field Completeness", "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
      "numeric", 3, "Good (~64% of 14 fields)",
      "9 of 14 listed fields populated: id, title, description, keywords, license_and_use_terms, page, creators, purposes, instances. Absent: doi, resources, parent_datasets, variables, regulatory_restrictions.confidentiality_level.",
      "9/14 = 64%, nearest the ~70% band (3), well below the >=90% band. license_and_use_terms is populated but names no license; id/page reuse the project website URL.",
      ALWAYS,
      cited=[("id", "https://chorus4ai.org/"), ("title", "CHoRUS Dataset"), ("description",), ("keywords",), ("license_and_use_terms",), ("page",), ("creators",), ("purposes",), ("instances",)],
      absent=["doi", "resources", "parent_datasets", "variables", "regulatory_restrictions.confidentiality_level"]),
    q(2, "Entry Length Adequacy", "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
      "numeric", 5, "Excellent (>200 chars)",
      "description is a ~1,300-character multi-sentence narrative; the two purposes responses are each roughly 200 characters.",
      "Average narrative length is well above 200 characters and the content is substantive (scope, counts, modalities, aims).",
      ALWAYS,
      cited=[("description", "multicenter, multimodal clinical care dataset"), ("/purposes/0/response", "to develop a publicly available, AI-ready critical care dataset"), ("/purposes/1/response",)],
      counts=[("purposes", 2)]),
    q(3, "Keyword Diversity", "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply additional topic evidence where documented; no named study or disease count is presumed.",
      "numeric", 5, "Excellent (8 keywords)",
      "8 distinct keywords: Critical Care, Electronic Health Record, Electroencephalography, Machine Learning, Bridge to Artificial Intelligence, social health determinants, data standards, Telemetry.",
      "Meets the >=8 threshold; terms span clinical domain, modalities and program. Imaging/radiology and pediatric/neonatal care are not represented although described.",
      ALWAYS,
      cited=[("/keywords/0", "Critical Care")], counts=[("keywords", 8)]),
    q(4, "File Enumeration and Type Variety", "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in separate linked resources. Examine every distribution; modality breadth is distinct from suitability for machine learning.",
      "numeric", 3, "Good (2-3 formats, not enumerated as distributions)",
      "No distribution_formats, file_collections or total_file_count. Formats appear only as data standards: conforms_to_standard OMOP_CDM, DICOM, WFDB; EEG instance mentions EDF+ and Persyst.",
      "Format variety is inferable (DICOM, WFDB, EDF+ plus OMOP tables) but no distribution or file enumeration exists, so it cannot reach the >3 documented file-type band; EEG availability is itself caveated.",
      ALWAYS,
      cited=[("conforms_to_standard",), ("conforms_to", "DICOM (imaging)"), ("/instances/9/description", "with EDF+ and Persyst as its data standard")],
      absent=["distribution_formats", "file_collections", "total_file_count"],
      counts=[("conforms_to_standard", 3)]),
    q(5, "Data File Size Availability", "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
      "pass_fail", 1, "Pass",
      "instances[0].counts = 50000 patient admissions; description also reports 1.6 billion OMOP rows and 23 Tb of waveform data.",
      "A numeric instance count is present. No total_size_bytes; the '23 Tb' unit is ambiguous (terabits vs terabytes).",
      ALWAYS,
      cited=[("/instances/0/counts",), ("description", "23 Tb of waveform data")],
      absent=["total_size_bytes"]),
]

cat2 = [
    q(6, "Dataset Identification Metadata", "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or repository).",
      "pass_fail", 0, "Fail",
      "No doi or publisher. id and page are both the project website https://chorus4ai.org/, whose banner (source_caveats) says it is 'under review for potential modification'.",
      "A project homepage is not a persistent identifier, and no hosting platform/repository is named (only an unnamed 'cloud enclave').",
      ALWAYS,
      cited=[("id", "https://chorus4ai.org/"), ("page", "https://chorus4ai.org/"), ("source_caveats", "under review for potential modification")],
      absent=["doi", "publisher"]),
    q(7, "Funding and Acknowledgements Completeness", "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
      "numeric", 5, "Excellent",
      "funders: NIH with grant OT2OD032701 (title, FY2022, project period). Six creators, each with an institutional affiliation (MGH, University of Florida, UTHealth Houston, Tufts University).",
      "Grant number matches the NIH activity/IC/serial pattern (OT2 + OD + 032701); project number 1OT2OD032701-01 is consistent. All creators carry affiliations.",
      ALWAYS,
      cited=[("/funders/0/grants/0/grant_number", "OT2OD032701"), ("/creators/0/affiliations/0/name", "Massachusetts General Hospital"), ("/funders/0/grants/0/notes", "1OT2OD032701-01")],
      counts=[("creators", 6), ("funders", 1)]),
    q(8, "Ethical and Privacy Declarations", "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable.",
      "numeric", 0, "Absent",
      "None of the ethics/privacy fields are populated: no ethical_reviews, human_subject_research, is_deidentified, participant_privacy, informed_consent, data_protection_impacts, at_risk_populations, participant_compensation or regulatory_restrictions. Only passing mentions: imaging 'de-identification in process' and a purpose about promoting privacy.",
      "The record describes retrospective EHR, notes, imaging and waveform data on ICU/PICU/NICU patients from 14 hospitals, yet documents no ethics review, consent/waiver, deidentification method or privacy risk. Paediatric and neonatal patients (at-risk groups) are implied but unaddressed.",
      cond("human_subjects"),
      cited=[("/instances/7/description", "de-identification in process for a larger cohort")],
      absent=["ethical_reviews", "human_subject_research", "is_deidentified", "participant_privacy", "informed_consent", "data_protection_impacts", "at_risk_populations", "participant_compensation", "regulatory_restrictions"],
      considered=["purposes"]),
    q(9, "Access Requirements and Governance Documentation", "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts.",
      "numeric", 3, "Good (agreement + access process, no classification)",
      "license_and_use_terms: participants 'must sign a licensing agreement' (terms not named). data_governance.access_review_process: registration form, .edu email, access contacts. Description: 'controlled access'.",
      "Access tiering (registration + signed agreement, controlled) is described for the training program, but the license is unnamed, and there is no confidentiality classification, regulatory (HIPAA or equivalent) statement, IP restriction or governance committee.",
      ALWAYS,
      cited=[("/license_and_use_terms/license_terms", "must sign a licensing agreement"), ("/license_and_use_terms/source_caveats", "The bundle does not name the licensing agreement or state its terms."), ("/data_governance/access_review_process", "requires a \".edu\" email address"), ("description", "retrospective data collection with controlled access")],
      absent=["ip_restrictions", "regulatory_restrictions", "data_protection_impacts"]),
    q(10, "Interoperability, Standardization, and Cross-Platform Integration", "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures.",
      "numeric", 3, "Good (standards named, no schema reference)",
      "conforms_to: 'OMOP (structured EHR data); DICOM (imaging); WFDB (waveform telemetry)'; conforms_to_standard lists OMOP_CDM, DICOM, WFDB; preprocessing describes semantic mappings to 'international standards' in a chorus-mapping repository.",
      "Standards are named per modality, but no OMOP CDM version, vocabulary/ontology, conforms_to_schema, related_datasets or linked integration procedure is given; the mapping repository is not linked directly. Short of the 5 band.",
      cond("shared_dataset"),
      cited=[("conforms_to", "OMOP (structured EHR data)"), ("conforms_to_standard",), ("/preprocessing_strategies/1/preprocessing_details", "Validated semantic mappings connect clinical data in various source formats to international standards")],
      absent=["conforms_to_schema", "distribution_formats", "related_datasets", "file_collections"],
      considered=["external_resources"]),
]

cat3 = [
    q(11, "Tool and Software Transparency", "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs.",
      "numeric", 3, "Good (strategies, no versions)",
      "preprocessing_strategies: clinical notes tokenized with the OHNLP toolkit; validated semantic mappings with a clinical validation SOP.",
      "Tools and strategies are named but without versions or URLs; no cleaning, labeling, annotation, imputation or missing-data documentation.",
      cond("data_processing"),
      cited=[("/preprocessing_strategies/0/preprocessing_details", "OHNLP toolkit")],
      absent=["cleaning_strategies", "labeling_strategies", "machine_annotation_tools", "annotation_analyses", "imputation_protocols", "missing_data_documentation"],
      counts=[("preprocessing_strategies", 2)]),
    q(12, "Collection Protocol Clarity", "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
      "numeric", 3, "Good (partial protocol)",
      "collection_mechanisms: retrospective collection; contributing sites extract data following SOP workflows. Instance descriptions name source systems (bedside monitors, PACS, hospital EEG database).",
      "Mechanism is described, but there are no collection timeframes (admission date ranges), no data_collectors entries naming sites/roles, no acquisition_methods or structured raw_data_sources.",
      cond("data_collection"),
      cited=[("/collection_mechanisms/0/mechanism_details", "Retrospective data collection"), ("/collection_mechanisms/1/mechanism_details", "standard operating procedure (SOP)"), ("/instances/8/description", "bedside monitors")],
      absent=["acquisition_methods", "data_collectors", "collection_timeframes", "raw_data_sources"],
      counts=[("collection_mechanisms", 2)]),
    q(13, "Version History, Maintenance, and Sustainability", "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access.",
      "numeric", 0, "Absent",
      "No version, version_access, errata, updates, maintainers, doi or publisher. Only 'current released dataset' vs 'anticipated final dataset' language and a program-manager contact in notes.",
      "Without a version identifier or persistent ID the 3 band is not met; the award ends 2026-11-30 and no preservation or maintenance plan is stated.",
      cond("shared_dataset"),
      cited=[("description", "current released dataset"), ("/funders/0/grants/0/description", "project end 2026-11-30")],
      absent=["version", "version_access", "errata", "updates", "maintainers", "doi", "publisher"],
      considered=["notes"]),
    q(14, "Associated Publications", "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources.",
      "numeric", 3, "Good (one external resource, no citation)",
      "external_resources: the chorus-ai GitHub organization. No citation and no doi.",
      "One distinct non-publication resource; no formal dataset citation and no publication, so the 5 band is not met.",
      ALWAYS,
      cited=[("/external_resources/0/external_resources/0", "https://github.com/chorus-ai#table-of-contents")],
      absent=["citation", "doi"],
      counts=[("external_resources", 1)]),
    q(15, "Human Subject Representation", "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups.",
      "numeric", 3, "Good (population without subgroup detail)",
      "instances: 50,000 patient admissions from ICU, PICU and NICU across 14 hospitals; over 45K unique admissions as of August 2025.",
      "Population is characterized at the unit level only; no demographic distribution, inclusion/exclusion criteria, subpopulations or at-risk group handling despite paediatric/neonatal patients and an equity aim.",
      cond("human_subjects"),
      cited=[("/instances/0/instance_type", "Patient admissions from ICU, PICU, and NICU"), ("/instances/0/description", "over 45K unique admissions")],
      absent=["subpopulations", "subsets", "at_risk_populations", "missing_data_documentation"],
      counts=[("instances", 10)]),
]

cat4 = [
    q(16, "Findability (Persistent Links)", "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
      "pass_fail", 1, "Pass",
      "page https://chorus4ai.org/ and external resource https://github.com/chorus-ai#table-of-contents.",
      "Working external URLs are present (pass criterion), though none is a persistent identifier (see Q6).",
      ALWAYS,
      cited=[("page", "https://chorus4ai.org/"), ("/external_resources/0/external_resources/0",)],
      absent=["doi", "download_url"]),
    q(17, "Accessibility (Access Mechanism)", "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
      "numeric", 3, "Good (partially described)",
      "Training-program route: registration form, signed licensing agreement, .edu email, compute provisioned in a cloud enclave; otherwise email contacts to request access. No download_url or distribution formats.",
      "Authorization steps are stated for one route (training participants), but the general researcher path, platform name and policy document are absent.",
      cond("shared_dataset"),
      cited=[("/license_and_use_terms/license_terms", "licensing agreement, included in the registration form"), ("/data_governance/access_review_process", "an email is sent once access is granted and compute is provisioned")],
      absent=["download_url", "distribution_formats"]),
    q(18, "Reusability, Use Guidance, and Social Impact", "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis with risk identification and mitigation strategies.",
      "numeric", 3, "Good (agreement + basic use guidance)",
      "A licensing agreement is required (terms unstated); tasks list intended ML applications (characterizing illness, predicting complications, treatment response); existing_uses lists training and publications.",
      "Basic use guidance only; no prohibited/discouraged uses, no future_use_impacts or mitigation. The MIT license is correctly caveated as applying to the GitHub project, not the dataset.",
      ALWAYS,
      cited=[("/license_and_use_terms/license_terms",), ("/tasks/1/response", "Predicting complications"), ("/external_resources/0/source_caveats", "the bundle does not state it as the dataset's license")],
      absent=["intended_uses", "prohibited_uses", "discouraged_uses", "future_use_impacts"],
      considered=["existing_uses"]),
    q(19, "Data Integrity, Provenance Graph, and Quality", "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation.",
      "numeric", 3, "Partial provenance (text lineage, no graph)",
      "Textual lineage: hospital source systems -> SOP-driven site extraction -> semantic mapping to OMOP -> cloud enclave; splits records a planned holdout test set (caveated as future tense). source_caveats trace source tiers and conflicts.",
      "Some provenance metadata exists, but no version history, errata, updates, parent datasets, was_derived_from or entity-activity-agent structure. Placed in the 3 band with uncertainty, since it reflects text lineage rather than version history.",
      ALWAYS,
      cited=[("/splits/0/split_details", "holdout test set"), ("/splits/0/source_caveats",), ("/collection_mechanisms/1/mechanism_details", "Data contributing sites extract and contribute clinical data")],
      absent=["version_access", "errata", "updates", "was_derived_from", "parent_datasets", "missing_data_documentation", "raw_data_sources"]),
    q(20, "Bias Documentation and Responsible AI Alignment", "Documentation of known biases, limitations and potential effects on intended or foreseeable uses.",
      "numeric", 0, "Absent",
      "No known_biases or future_use_impacts. The grant title targets 'Equitable AI' and a purpose claims the 'most diverse' data set, but no bias, representativeness or limitation analysis is given.",
      "Equity and diversity claims are asserted without supporting bias documentation (site selection, ICU population, missingness).",
      ALWAYS,
      cited=[("/funders/0/grants/0/name", "for Equitable AI"), ("/purposes/1/response", "most diverse")],
      absent=["known_biases", "future_use_impacts"]),
]

cats = [("Structural Completeness", cat1), ("Metadata Quality & Content", cat2),
        ("Technical Documentation", cat3), ("FAIRness & Accessibility", cat4)]

issues = [
    dict(id="I1", fields_involved=['ethical_reviews', 'human_subject_research', 'informed_consent', 'is_deidentified', 'participant_privacy', 'at_risk_populations', 'instances', 'subpopulations'], recommendation='Document ethics review (or waiver), consent basis, deidentification method, reidentification risk, paediatric/neonatal protections and cohort demographics with inclusion/exclusion criteria.', item_ids=["Q8", "Q15"], score_effect="lowered", category="consent_ethics", type="consistency",
         severity="high", description="Retrospective clinical data (EHR, notes, imaging, waveforms) on ICU/PICU/NICU patients from 14 hospitals, but no ethics review, consent or waiver, deidentification method, privacy risk or at-risk population documentation; demographics and inclusion criteria absent."),
    dict(id="I2", fields_involved=['doi', 'publisher', 'citation', 'version', 'id', 'page'], recommendation='Assign or record a dataset DOI and hosting repository, a formal citation and a release version.', item_ids=["Q6", "Q13", "Q14"], score_effect="lowered", category="persistent_identifier", type="completeness",
         severity="high", description="No DOI, publisher, citation or version; id and page reuse the project website, which the record itself notes is under review for modification."),
    dict(id="I3", fields_involved=['license_and_use_terms', 'regulatory_restrictions', 'prohibited_uses', 'discouraged_uses', 'future_use_impacts'], recommendation='Name the data use agreement and its key terms, add a confidentiality classification and applicable regulatory framework, and state prohibited/discouraged uses.', item_ids=["Q9", "Q18"], score_effect="lowered", category="license_use_terms", type="completeness",
         severity="medium", description="Licensing agreement is required but unnamed and its terms unstated; no confidentiality classification, regulatory compliance statement, prohibited/discouraged uses or impact analysis."),
    dict(id="I4", fields_involved=['distribution_formats', 'file_collections', 'download_url', 'conforms_to', 'conforms_to_standard'], recommendation='Enumerate distributed files/formats with sizes and the enclave/platform access path for all users; give OMOP CDM version and vocabularies.', item_ids=["Q4", "Q10", "Q17"], score_effect="lowered", category="format_access", type="completeness",
         severity="medium", description="No distribution_formats, file enumeration or download/access platform; formats appear only as data standards without versions or schema references; access path is described only for training-program participants."),
    dict(id="I5", fields_involved=['preprocessing_strategies', 'collection_timeframes', 'data_collectors', 'raw_data_sources', 'version_access', 'updates'], recommendation='Add tool versions/URLs, admission date ranges, contributing sites and a change history.', item_ids=["Q11", "Q12", "Q19"], score_effect="lowered", category="processing_provenance", type="completeness",
         severity="medium", description="Processing tools lack versions/URLs; no collection timeframes, data collectors, raw data sources, version history or structured provenance."),
    dict(id="I6", fields_involved=['known_biases', 'future_use_impacts', 'purposes'], recommendation='Document known biases (site selection, ICU population, missingness) and their effects on intended uses.', item_ids=["Q20"], score_effect="lowered", category="bias_quality", type="semantic_understanding",
         severity="medium", description="'Equitable AI' and 'most diverse' claims are made without any known_biases or limitations documentation."),
    dict(id="I7", fields_involved=['doi', 'resources', 'parent_datasets', 'variables', 'regulatory_restrictions.confidentiality_level'], recommendation='Populate the missing core fields, especially variables for the OMOP tables.', item_ids=["Q1"], score_effect="lowered", category="variables_metadata", type="completeness",
         severity="medium", description="Core fields doi, resources, parent_datasets, variables and confidentiality_level are absent (9/14 populated)."),
    dict(id="I8", fields_involved=['instances', 'description', 'source_caveats'], recommendation='Reconcile counts to a dated release and state the size unit explicitly (TB vs Tb).', item_ids=[], score_effect="noted_only", category="count_size", type="content_accuracy",
         severity="low", description="Admission counts (50,000 on website vs over 45K in webinar) and imaging counts (1000 images vs 7,642 admissions) differ; the record explicitly retains and explains both. The '23 Tb' size unit is ambiguous."),
    dict(id="I9", fields_involved=['notes'], recommendation='Confirm the contact email domain with the project.', item_ids=[], score_effect="noted_only", category="other", type="correctness",
         severity="low", description="Contact email domain 'mgh.havard.edu' appears misspelled (likely 'harvard'); the record flags it as reproduced from source."),
]

total = sum(x["score"] for _, c in cats for x in c)
max_points = 88
ctx = normalize_context({})
model = "claude-opus-5-5"
out = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": str(D4D.relative_to(ROOT)),
    "project": "CHORUS",
    "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {
        "name": model,
        "evaluator_model": model,
        "temperature": None,
        "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
        "evaluation_type": "semantic_llm_judge",
    },
    "overall_score": {
        "total_points": total, "max_points": max_points, "excluded_max_points": 0,
        "adjusted_max_points": max_points,
        "normalized_percentage": round(total / max_points * 100, 2),
        "fixed_percentage": round(total / max_points * 100, 2),
        "questions_not_applicable": 0, "excluded_item_ids": [],
    },
    "categories": [
        {"name": n, "questions": c, "category_score": sum(x["score"] for x in c),
         "category_max": sum(x["max_score"] for x in c)} for n, c in cats
    ],
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "Record is careful about provenance of claims: future-tense grant statements, count discrepancies and the GitHub MIT license are explicitly caveated rather than overstated.",
            "Largest gaps are human-subjects protections, persistent identification/versioning and bias documentation for a multi-site clinical dataset with paediatric and neonatal patients.",
            "Access is documented as controlled with registration and a signed agreement, but only for the training-program route.",
        ],
        "consistency_checks": {"passed": 3, "failed": 2, "warnings": 2},
        "correctness_validations": {
            "doi_format": "not_applicable_no_doi",
            "grant_number_format": "valid (OT2OD032701 matches NIH activity code + IC + serial; 1OT2OD032701-01 consistent)",
            "rrid_format": "not_applicable_no_rrid",
            "url_validity": "plausible (https://chorus4ai.org/, https://github.com/chorus-ai); contact email domain likely misspelled",
        },
    },
    "applicability_context": ctx,
    "evaluation_scope": {
        "policy": "single_dataset",
        "units": [{"path": "#", "id": "https://chorus4ai.org/"}],
        "collection_metadata_inherited": False,
    },
    "metadata": {
        "instrument_sha256": sha(ROOT / ".claude/agents/d4d-rubric20-semantic.md"),
        "evidence_authority_sha256": sha(ROOT / "data/rubric/semantic_evidence_authority_v3.json"),
        "rubric_sha256": sha(ROOT / "data/rubric/rubric20.txt"),
        "input_sha256": sha(D4D),
        "context_sha256": context_digest(ctx),
        "evaluator_model": model,
    },
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n")
print(total, OUT)
