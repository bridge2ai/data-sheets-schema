# Purpose: serialize the rubric10-semantic (v3.0, general context instrument v3)
#   judgements for the CHORUS record of label
#   2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1. Judgements were made
#   by the evaluating session (claude-opus-5-5); this script only writes them.
# Inputs: the D4D record, the rubric text, the agent definition and the
#   evidence authority (hashed only).
# Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/
#   CHORUS_2026-11-22b_rep1_evaluation.json
# Date: 2026-11-22
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from data_sheets_schema.evaluation_context import context_digest, normalize_context

ROOT = Path(__file__).resolve().parents[2]
INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/CHORUS_d4d.yaml"
OUT = ROOT / "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep1_evaluation.json"


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


ALWAYS = "This item applies to every dataset"
RULES = {
    "E2.2": "regulated_access",
    "E3.1": "shared_dataset", "E3.2": "shared_dataset", "E3.3": "shared_dataset", "E3.4": "shared_dataset",
    "E4.1": "any", "E4.2": "any", "E4.3": "human_subjects", "E4.4": "human_subjects", "E4.5": "human_subjects",
    "E6.1": "shared_dataset", "E6.2": "shared_dataset", "E6.3": "shared_dataset", "E6.4": "shared_dataset",
    "E6.5": "shared_dataset",
    "E8.1": "data_collection", "E8.2": "data_collection", "E8.3": "data_processing", "E8.4": "processing_software",
    "E10.1": "shared_dataset", "E10.2": "shared_dataset", "E10.3": "shared_dataset", "E10.4": "shared_dataset",
    "E10.5": "shared_dataset",
}


def app(item_id):
    rule = RULES.get(item_id)
    if rule is None:
        return "applicable", ALWAYS
    if rule == "any":
        return "unknown", ("any: human_subjects: not declared; retained in the denominator; "
                           "regulated_access: not declared; retained in the denominator")
    return "unknown", f"{rule}: not declared; retained in the denominator"


def item(item_id, name, score, evidence, note, cited=(), absent=(), counts=(), considered=(), no_issue=None):
    status, aev = app(item_id)
    out = {
        "name": name, "score": score, "evidence": evidence, "quality_note": note,
        "applicable": True, "applicability_status": status, "applicability_evidence": aev,
        "unit_scores": [{
            "path": "#", "score": score, "evidence": evidence,
            "cited": [dict(path=p, quote=q) if q else dict(path=p) for p, q in cited],
            "absent": [{"path": p} for p in absent],
            "counts": [{"path": p, "claimed": n} for p, n in counts],
            "considered": list(considered),
        }],
        "item_id": item_id,
    }
    if no_issue:
        out["no_issue_reason"] = no_issue
    return out


E = []

E.append(("Dataset Discovery and Identification",
          "Can a user or system discover and uniquely identify this dataset?", [
    item("E1.1", "Persistent Identifier (DOI, RRID, or URI)", 0,
         "id is 'https://chorus4ai.org/', the project website (identical to page); no doi or rrid.",
         "The only identifier is a project homepage URL, not a persistent, dataset-specific identifier; no DOI/RRID to validate.",
         cited=[("id", "https://chorus4ai.org/"), ("page", "https://chorus4ai.org/")], absent=["doi", "rrid"]),
    item("E1.2", "Dataset Title and Description Completeness", 1,
         "title 'CHoRUS Dataset'; description (>1,000 chars) gives modalities, 14 hospitals, counts and controlled access.",
         "Substantive, specific description with scale, modalities and access mode.",
         cited=[("title", "CHoRUS Dataset"),
                ("description", "multicenter, multimodal clinical care dataset")]),
    item("E1.3", "Keywords or Tags for Searchability", 1,
         "8 keywords including Critical Care, Electronic Health Record, Electroencephalography, Machine Learning, Telemetry.",
         "Covers domain, modalities and methods; meets the >=5 threshold.",
         cited=[("/keywords/0", "Critical Care")], counts=[("keywords", 8)]),
    item("E1.4", "Landing Page and Resources (page, hierarchical resources)", 1,
         "page: https://chorus4ai.org/ (project website). No hierarchical resources.",
         "Landing page present; resources absent but either suffices.",
         cited=[("page", "https://chorus4ai.org/")]),
    item("E1.5", "Hierarchical Structure (parent datasets, relationships)", 0,
         "No parent_datasets or related_datasets; the Bridge2AI consortium membership is stated only in prose.",
         "No typed hierarchical or relational links.",
         absent=["parent_datasets", "related_datasets"]),
]))

E.append(("Dataset Access and Retrieval",
          "Can the dataset and its associated resources be located, accessed, and downloaded?", [
    item("E2.1", "Access Policy and IP Restrictions Defined", 1,
         "license_and_use_terms: a licensing agreement must be signed before access; data_governance.access_review_process: registration form, .edu email, access contacts; description: controlled access.",
         "Controlled-access policy and access procedure are described, though the agreement itself is unnamed and ip_restrictions are absent.",
         cited=[("license_and_use_terms.license_terms", "must sign a licensing agreement"),
                ("data_governance.access_review_process", "gaining access to the dataset requires a \".edu\" email address")],
         absent=["ip_restrictions"]),
    item("E2.2", "Regulatory Compliance and Confidentiality Classification", 0,
         "No regulatory_restrictions, confidentiality_level, HIPAA status, other compliance or governance committee contact. Access contacts in data_governance are request contacts, not a governance committee.",
         "Patient clinical data from 14 US hospitals with no regulatory/HIPAA or confidentiality classification.",
         absent=["regulatory_restrictions", "data_governance.committee_contact"],
         considered=["data_governance.access_review_process"]),
    item("E2.3", "Download URL or Platform Link Available", 0,
         "No download_url; access is by registration and email contacts; the cloud enclave is mentioned without a link.",
         "No download link or named platform URL.",
         absent=["download_url"], considered=["data_governance.access_review_process", "page"]),
    item("E2.4", "Distribution Formats and File Types Specified", 0,
         "No distribution_formats or file_collections; DICOM/WFDB appear only as data standards (conforms_to).",
         "Distributed file types and media types are not specified.",
         absent=["distribution_formats", "file_collections"], considered=["conforms_to"]),
    item("E2.5", "Related Datasets and External Resources Linked", 1,
         "external_resources: chorus-ai GitHub organization (https://github.com/chorus-ai#table-of-contents) with SOPs, mappings and tooling. No related_datasets.",
         "One substantive external documentation link; related datasets absent.",
         cited=[("/external_resources/0/name", "CHoRUS for Equitable AI (chorus-ai GitHub organization)")],
         absent=["related_datasets"]),
]))

E.append(("Data Reuse and Interoperability",
          "Is sufficient information provided to reuse and integrate the dataset with others?\nNote: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.\n", [
    item("E3.1", "License Terms Allow Reuse", 0,
         "license_and_use_terms names no license; its source_caveats: 'The bundle does not name the licensing agreement or state its terms.' MIT applies to the GitHub project only.",
         "Reuse permissions cannot be determined.",
         cited=[("license_and_use_terms.source_caveats", "does not name the licensing agreement or state its terms"),
                ("license_and_use_terms.license_terms", "licensing agreement")]),
    item("E3.2", "Data Formats Are Standardized (encoding, format)", 1,
         "conforms_to_standard: OMOP_CDM, DICOM, WFDB; instances: imaging DICOM, telemetry WFDB, EEG EDF+.",
         "Standard per-modality formats are stated; character encoding and file-level formats are absent.",
         cited=[("/conforms_to_standard/1", "DICOM"), ("/conforms_to_standard/2", "WFDB"),
                ("/instances/9/description", "EDF+ and Persyst")],
         counts=[("conforms_to_standard", 3)], absent=["distribution_formats", "file_collections"]),
    item("E3.3", "Schema or Ontology Conformance Stated", 1,
         "conforms_to: 'OMOP (structured EHR data); DICOM (imaging); WFDB (waveform telemetry)'.",
         "OMOP CDM conformance for EHR data is a meaningful schema statement.",
         cited=[("conforms_to", "OMOP (structured EHR data)")], absent=["conforms_to_schema"]),
    item("E3.4", "Variable Metadata with Identifiers Defined", 0,
         "No variables; instances list data categories only.",
         "No variable-level metadata.",
         absent=["variables"]),
    item("E3.5", "Use Guidance Provided (intended, prohibited uses)", 0,
         "No intended_uses, prohibited_uses or discouraged_uses; existing_uses and tasks describe current/target uses only.",
         "No explicit allowed or prohibited use guidance.",
         absent=["intended_uses", "prohibited_uses", "discouraged_uses"], considered=["existing_uses", "tasks"]),
]))

E.append(("Ethical Use and Privacy Safeguards",
          "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.", [
    item("E4.1", "IRB or Ethics Review and Data Protection Impact", 0,
         "No ethical_reviews, human_subject_research or data_protection_impacts.",
         "Retrospective patient data with no ethics review or waiver documented.",
         absent=["ethical_reviews", "human_subject_research", "data_protection_impacts",
                 "data_governance.committee_contact"], considered=["data_governance.access_review_process"]),
    item("E4.2", "Deidentification Method Described", 0,
         "No is_deidentified; only 'de-identification in process for a larger cohort' for imaging in instances.",
         "De-identification is mentioned as in progress, with no method.",
         cited=[("/instances/7/description", "de-identification in process for a larger cohort")],
         absent=["is_deidentified"]),
    item("E4.3", "Privacy Protections and Re-identification Risk Assessment", 0,
         "No participant_privacy; enclave storage and local retention of notes are stated but without a privacy or re-identification assessment.",
         "No privacy protections or risk assessment documented.",
         absent=["participant_privacy"], considered=["/instances/6/description"]),
    item("E4.4", "Informed Consent Obtained from Participants", 0,
         "No informed_consent or consent waiver.",
         "Consent basis for retrospective patient data is undocumented.",
         absent=["informed_consent"]),
    item("E4.5", "Vulnerable Populations and Compensation Documented", 0,
         "No at_risk_populations or participant_compensation although instances include PICU and NICU admissions (children and neonates).",
         "Pediatric/neonatal patients are included with no vulnerable-population protections.",
         cited=[("/instances/0/instance_type", "Patient admissions from ICU, PICU, and NICU")],
         absent=["at_risk_populations", "participant_compensation"]),
]))

E.append(("Data Composition and Structure",
          "Can the dataset's structure, modality, and population be understood from metadata?", [
    item("E5.1", "Cohort or Subpopulations Characteristics Described", 0,
         "No subpopulations; cohort is described only as ICU/PICU/NICU admissions across 14 hospitals.",
         "No demographics or inclusion/exclusion criteria; care setting alone is marginal.",
         cited=[("/instances/0/instance_type", "ICU, PICU, and NICU")], absent=["subpopulations", "subsets"]),
    item("E5.2", "Number of Instances or Samples Reported", 1,
         "instances[0].counts 50000 admissions; webinar 'over 45K unique admissions'; 7,642 admissions with radiology; 1000 images.",
         "Specific counts with source and date reconciliation in source_caveats.",
         cited=[("/instances/0/counts", None), ("/instances/0/description", "over 45K unique admissions")],
         counts=[("instances", 10)]),
    item("E5.3", "Variable-Level Metadata, Tabular Flag, and Data Splits", 0,
         "No variables, is_tabular or subset flags; splits describe only a planned holdout set.",
         "Planned future split without variable metadata is insufficient.",
         cited=[("/splits/0/split_details", "will also provision a holdout test set")],
         absent=["variables", "is_tabular", "subsets"]),
    item("E5.4", "Data Topics or Conditions Represented", 1,
         "instances enumerate demographics, medication administration, procedures, nursing flowsheets, diagnoses, clinical notes, imaging, waveform telemetry and EEG for critically ill patients.",
         "Modalities and clinical domain (acute/critical illness) are clear.",
         cited=[("/instances/2/instance_type", "Medication administration"),
                ("/instances/8/instance_type", "Waveform telemetry")], counts=[("instances", 10)]),
    item("E5.5", "Data Quality, Anomalies, and Missing Data Documented", 0,
         "No anomalies, sampling_strategies or missing_data_documentation; only an EEG source caveat.",
         "Data quality and missingness are undocumented.",
         absent=["anomalies", "sampling_strategies", "missing_data_documentation"],
         considered=["/instances/9/source_caveats", "source_caveats"]),
]))

E.append(("Data Provenance and Version Tracking",
          "Can a user determine dataset versions, update history, and provenance?", [
    item("E6.1", "Dataset Version Number Provided", 0, "No version.",
         "Release is only described as 'current released dataset'.", absent=["version"]),
    item("E6.2", "Version Access Methods Documented", 0, "No version_access.",
         "No way to access prior releases is described.", absent=["version_access"]),
    item("E6.3", "Change Descriptions and Errata Provided", 0, "No errata or updates.",
         "No change log or errata.", absent=["errata", "updates"]),
    item("E6.4", "Update Schedule or Frequency Indicated", 0,
         "No updates; growth from 50,000 to an anticipated 100,000 admissions is stated without a schedule.",
         "No update plan or frequency.", absent=["updates"], considered=["description"]),
    item("E6.5", "Provenance, Source Derivation, and Raw Data Sources", 0,
         "No was_derived_from or raw_data_sources; notes contains only a contact; source systems (PACS, bedside monitors) appear only parenthetically in instance types.",
         "No dedicated provenance or derivation account for the release.",
         absent=["was_derived_from", "raw_data_sources", "updates"],
         considered=["notes", "/instances/7/instance_type", "collection_mechanisms"]),
]))

E.append(("Scientific Motivation and Funding Transparency",
          "Does the metadata clearly state why the dataset exists and who funded it?", [
    item("E7.1", "Motivation or Purpose for Dataset Creation", 1,
         "purposes: develop a publicly available, AI-ready critical care dataset; addressing_gaps: urgent need for AI/ML infrastructure in critical care.",
         "Clear rationale and gap.",
         cited=[("/purposes/0/response", "AI-ready critical care dataset")], counts=[("purposes", 2)]),
    item("E7.2", "Primary Research Objectives or Tasks", 1,
         "tasks: characterizing acute and critical illness, predicting complications, measuring treatment response.",
         "Specific ML/AI target tasks.",
         cited=[("/tasks/1/response", "Predicting complications")], counts=[("tasks", 3)]),
    item("E7.3", "Funding Sources and Mechanisms Listed", 1,
         "funders: NIH, Common Fund Bridge2AI program, OT2 award.",
         "Funder and program named.",
         cited=[("/funders/0/grantor", "NIH"), ("/funders/0/description", "NIH Common Fund's Bridge2AI program")]),
    item("E7.4", "Grant IDs or Award Numbers Present", 1,
         "grant_number OT2OD032701 (FY2022 project number 1OT2OD032701-01).",
         "Matches the NIH activity-code/IC/serial pattern (OT2 OD 032701); consistent across website and RePORTER.",
         cited=[("/funders/0/grants/0/grant_number", "OT2OD032701")]),
    item("E7.5", "Creators and Acknowledgements Documented", 1,
         "6 creators with affiliations (MGH, University of Florida, UTHealth Houston, Tufts); PI Eric S. Rosenthal.",
         "Named leadership team with institutions.",
         cited=[("/creators/0/name", "Eric Rosenthal")], counts=[("creators", 6)]),
]))

E.append(("Technical Transparency (Data Collection and Processing)",
          "Can data collection and processing steps be replicated or understood?\nNote: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.\n", [
    item("E8.1", "Collection Mechanisms and Settings Described", 1,
         "collection_mechanisms: retrospective collection; sites extract and contribute data via an SOP-linked step-by-step workflow (Chorus_SOP).",
         "Procedure and setting given; collection timeframes absent.",
         cited=[("/collection_mechanisms/0/mechanism_details", "Retrospective data collection"),
                ("/collection_mechanisms/1/mechanism_details", "step-by-step workflow")],
         counts=[("collection_mechanisms", 2)]),
    item("E8.2", "Data Acquisition Methods Listed", 0,
         "No acquisition_methods or raw_data_sources; instance descriptions name source systems (bedside monitors, gateway/middleware, PACS, hospital database) without describing acquisition.",
         "Source names alone do not describe acquisition methods.",
         absent=["acquisition_methods", "raw_data_sources"],
         considered=["/instances/8/description", "/instances/7/instance_type"]),
    item("E8.3", "Preprocessing, Cleaning, Labeling, and Annotation Quality", 1,
         "preprocessing_strategies: notes tokenized with OHNLP; validated semantic mappings to international standards with clinical validation SOP.",
         "Two concrete processing steps; cleaning, labeling and imputation absent.",
         cited=[("/preprocessing_strategies/0/preprocessing_details", "OHNLP toolkit"),
                ("/preprocessing_strategies/1/preprocessing_details", "Validated semantic mappings")],
         absent=["cleaning_strategies", "labeling_strategies", "imputation_protocols"]),
    item("E8.4", "Software and Tools Documented", 1,
         "preprocessing_strategies names the OHNLP toolkit, which extracted and tokenized the clinical notes in the release.",
         "Processing software named (slot: preprocessing_strategies); no version or repository.",
         cited=[("/preprocessing_strategies/0/preprocessing_details",
                 "Clinical notes are extracted and tokenized using the OHNLP toolkit.")]),
    item("E8.5", "External Standards, Resources, and Imputation Protocols", 1,
         "conforms_to OMOP/DICOM/WFDB; external_resources: chorus-ai GitHub organization. No imputation_protocols.",
         "Standards and external documentation present; imputation not addressed.",
         cited=[("conforms_to", "WFDB (waveform telemetry)"),
                ("/external_resources/0/external_resources/0", "https://github.com/chorus-ai#table-of-contents")],
         absent=["imputation_protocols"]),
]))

E.append(("Dataset Evaluation and Limitations Disclosure",
          "Does the metadata communicate known risks, biases, or dataset limitations?", [
    item("E9.1", "Known Limitations Documented", 0,
         "No known_limitations; source_caveats concern source discrepancies, not dataset limitations.",
         "Dataset limitations are not stated.", absent=["known_limitations"], considered=["source_caveats"]),
    item("E9.2", "Biases Categorized Using Standard Taxonomy (RAI-aligned)", 0,
         "No known_biases or future_use_impacts despite 'Equitable AI' goal.",
         "No bias documentation.", absent=["known_biases", "future_use_impacts"]),
    item("E9.3", "Data Anomalies and Quality Issues Noted", 0, "No anomalies.",
         "No anomalies or quality issues.", absent=["anomalies"], considered=["source_caveats"]),
    item("E9.4", "Sensitive Content and Warnings Provided", 0,
         "No sensitive_elements or content_warnings though clinical notes, diagnoses and imaging are included.",
         "Sensitive clinical content not flagged.",
         absent=["sensitive_elements", "content_warnings"], considered=["/instances/6/description"]),
    item("E9.5", "Ethical Review and Social Impact Analysis", 0,
         "No ethical_reviews or future_use_impacts.",
         "No ethics or downstream impact analysis.", absent=["ethical_reviews", "future_use_impacts"]),
]))

E.append(("Cross-Platform and Community Integration",
          "Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain.", [
    item("E10.1", "Dataset Published on a Recognized Platform", 0,
         "No publisher; hosting is an unnamed cloud enclave.",
         "No recognized repository or platform named.", absent=["publisher"], considered=["description"]),
    item("E10.2", "Citation and DOI for Cross-referencing", 0, "No citation or doi.",
         "No citation guidance.", absent=["citation", "doi"]),
    item("E10.3", "Community Standards or Schema Conformance", 1,
         "conforms_to OMOP, DICOM, WFDB.", "Recognized community standards.",
         cited=[("conforms_to", "DICOM (imaging)")]),
    item("E10.4", "Outreach Materials and Documentation Links", 1,
         "page https://chorus4ai.org/; GitHub organization with SOPs; AIM-AHEAD training program noted in existing_uses.",
         "Documentation and training outreach present.",
         cited=[("page", "https://chorus4ai.org/"),
                ("/existing_uses/1/description", "AIM-AHEAD Bridge2AI for Clinical Care Training Program")]),
    item("E10.5", "Related Datasets with Typed Relationships", 0, "No related_datasets.",
         "No typed relationships.", absent=["related_datasets"]),
]))


def issue(type_, category, severity, items, effect, desc, fields, rec):
    return {"type": type_, "category": category, "severity": severity, "item_ids": items,
            "score_effect": effect, "description": desc, "fields_involved": fields, "recommendation": rec}


ISSUES = [
    issue("completeness", "consent_ethics", "high", ["E4.1", "E4.4", "E9.5"], "lowered",
          "Retrospective clinical data from patients at 14 hospitals with no ethics review, waiver or consent basis documented.",
          ["ethical_reviews", "human_subject_research", "informed_consent"],
          "Document IRB review/waiver per contributing site and the consent basis."),
    issue("completeness", "privacy_regulatory", "high", ["E2.2", "E4.2", "E4.3", "E9.4"], "lowered",
          "No de-identification method, privacy protections, regulatory classification or sensitive-content flags for EHR, notes and imaging; imaging de-identification is only 'in process'.",
          ["is_deidentified", "participant_privacy", "regulatory_restrictions", "sensitive_elements"],
          "Describe the de-identification standard, enclave privacy controls and HIPAA status."),
    issue("consistency", "consent_ethics", "medium", ["E4.5"], "lowered",
          "Instances include PICU and NICU admissions (minors) but no at-risk population protections are documented.",
          ["instances", "at_risk_populations"], "Document protections for pediatric and neonatal patients."),
    issue("completeness", "persistent_identifier", "medium", ["E1.1", "E10.2"], "lowered",
          "id is the project homepage, not a dataset persistent identifier; no DOI or citation.",
          ["id", "doi", "citation"], "Mint a DOI or other persistent dataset identifier and a recommended citation."),
    issue("completeness", "license_use_terms", "medium", ["E3.1", "E3.5"], "lowered",
          "Licensing agreement is unnamed and its terms unstated; no intended or prohibited use guidance.",
          ["license_and_use_terms", "intended_uses", "prohibited_uses"],
          "Name the data use agreement and state permitted and prohibited uses."),
    issue("completeness", "format_access", "medium", ["E2.3", "E2.4", "E10.1"], "lowered",
          "No download/platform URL, distribution formats or publisher; the enclave is unnamed.",
          ["download_url", "distribution_formats", "publisher"], "Name the hosting enclave and distributed file formats."),
    issue("completeness", "temporal_version", "medium", ["E6.1", "E6.2", "E6.3", "E6.4"], "lowered",
          "No version, version access, change log or update schedule despite a growing dataset (50,000 now, 100,000 anticipated).",
          ["version", "version_access", "updates", "errata"], "Add release versions and an update plan."),
    issue("completeness", "processing_provenance", "medium", ["E6.5", "E8.2"], "lowered",
          "No raw data source, acquisition method or derivation account beyond parenthetical source-system names.",
          ["raw_data_sources", "acquisition_methods", "was_derived_from"],
          "Describe source EHR/PACS/monitor systems and extraction methods per site."),
    issue("completeness", "variables_metadata", "medium", ["E3.4", "E5.3", "E5.1"], "lowered",
          "No variable metadata, tabular flag, subset flags or cohort demographics.",
          ["variables", "subpopulations", "is_tabular"], "Provide a data dictionary and cohort characteristics."),
    issue("completeness", "bias_quality", "medium", ["E5.5", "E9.1", "E9.2", "E9.3"], "lowered",
          "No limitations, biases, anomalies or missing-data documentation, despite an equity-focused project goal.",
          ["known_limitations", "known_biases", "anomalies", "missing_data_documentation"],
          "Document site heterogeneity, representativeness and missingness."),
    issue("completeness", "attribution", "low", ["E1.5", "E10.5"], "lowered",
          "No parent or related datasets with typed relationships.", ["parent_datasets", "related_datasets"],
          "Link related Bridge2AI or derived datasets with relationship types."),
    issue("content_accuracy", "count_size", "low", [], "noted_only",
          "Admission counts (50,000 vs over 45K) and imaging counts (7,642 admissions vs 1000 images) differ across sources; the record flags and reconciles them in source_caveats.",
          ["instances", "source_caveats"], "Pin counts to a dated release."),
    issue("semantic_understanding", "scope_drift", "low", [], "noted_only",
          "Purpose cites a 'publicly available' dataset while access is controlled; the record correctly marks the grant abstract as future-tense plans.",
          ["purposes", "data_governance", "source_caveats"], "State current access tier explicitly."),
    issue("correctness", "other", "low", [], "noted_only",
          "Contact email domain 'mgh.havard.edu' is reproduced from the source with a likely typo; the record flags it.",
          ["notes", "source_caveats"], "Verify the contact address."),
]

total = sum(s["score"] for _, _, subs in E for s in subs)
ctx = normalize_context({})
doc = {
    "rubric": "rubric10-semantic", "version": "3.0", "d4d_file": INPUT, "project": "CHORUS",
    "method": "claudecode_agent",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {"name": "claude-opus-5-5", "evaluator_model": "claude-opus-5-5", "temperature": None,
              "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
              "evaluation_type": "semantic_llm_judge"},
    "run_label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1",
    "overall_score": {"total_points": total, "max_points": 50, "excluded_max_points": 0,
                      "adjusted_max_points": 50, "normalized_percentage": round(total / 50 * 100, 1),
                      "fixed_percentage": round(total / 50 * 100, 1), "sub_elements_not_applicable": 0,
                      "excluded_item_ids": []},
    "elements": [{"id": i + 1, "name": n, "description": d, "sub_elements": subs,
                  "element_score": sum(s["score"] for s in subs), "element_max": 5}
                 for i, (n, d, subs) in enumerate(E)],
    "semantic_analysis": {
        "issues_detected": ISSUES,
        "semantic_insights": [
            "Funding is precise and internally consistent: grantor NIH, award OT2OD032701 with FY2022 project number 1OT2OD032701-01, project dates 2022-09-01 to 2026-11-30.",
            "Source conflicts and future-tense grant statements are explicitly caveated rather than silently resolved.",
            "OMOP/DICOM/WFDB conformance is tied to specific modalities.",
        ],
        "consistency_checks": {"passed": 3, "failed": 2, "warnings": 3},
        "correctness_validations": {"doi_format": "not_present", "grant_number_format": "valid_nih",
                                    "rrid_format": "not_present", "url_validity": "all_valid"},
    },
    "recommendations": [
        "Add ethics review, consent/waiver and de-identification method documentation.",
        "Mint a DOI and provide a citation; add version and update plan.",
        "Name the data use agreement, hosting enclave and distribution formats.",
        "Add a data dictionary, cohort demographics, limitations and bias documentation.",
    ],
    "applicability_context": ctx,
    "evaluation_scope": {"policy": "single_dataset", "units": [{"path": "#", "id": "https://chorus4ai.org/"}],
                         "collection_metadata_inherited": False},
    "metadata": {
        "instrument_sha256": sha(".claude/agents/d4d-rubric10-semantic.md"),
        "evidence_authority_sha256": sha("data/rubric/semantic_evidence_authority_v3.json"),
        "rubric_sha256": sha("data/rubric/rubric10.txt"),
        "input_sha256": sha(INPUT),
        "context_sha256": context_digest(ctx),
    },
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, indent=2) + "\n")
print(OUT, total)
