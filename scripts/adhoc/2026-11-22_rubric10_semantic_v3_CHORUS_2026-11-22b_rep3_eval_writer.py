#!/usr/bin/env python3
"""Write the rubric10-semantic v3 evaluation of one CHORUS D4D record.

Purpose: serialize the evaluator's (claude-opus-5-5) judgements for
  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CHORUS_d4d.yaml
  under .claude/agents/d4d-rubric10-semantic.md (general context instrument v3),
  checking every cited quote against the record before writing.
Inputs: the D4D record, rubric10.txt, evidence authority, agent definition (hashed only).
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep3_evaluation.json
Context: no caller applicability context (empty; all predicates unknown).
Date: 2026-11-22
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest, normalize_context  # noqa: E402

D4D = ROOT / "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CHORUS_d4d.yaml"
OUT = ROOT / "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep3_evaluation.json"
AGENT = ROOT / ".claude/agents/d4d-rubric10-semantic.md"
RUBRIC = ROOT / "data/rubric/rubric10.txt"
AUTH = ROOT / "data/rubric/semantic_evidence_authority_v3.json"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


DOC = yaml.safe_load(D4D.read_bytes())


def resolve(path):
    node = DOC
    parts = path.strip("/").split("/") if path.startswith("/") else path.split(".")
    for p in parts:
        if isinstance(node, list):
            node = node[int(p)]
        else:
            node = node[p]
    return node


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def c(path, quote=None):
    val = resolve(path)
    assert val not in (None, "", [], {}), path
    if quote is not None:
        assert norm(quote) in norm(val), (path, quote)
        return {"path": path, "quote": quote}
    return {"path": path}


def a(path):
    try:
        resolve(path)
    except (KeyError, IndexError, TypeError):
        return {"path": path}
    raise AssertionError(f"{path} is populated")


def n(path):
    return {"path": path, "claimed": len(resolve(path))}


CONTEXT = normalize_context({})
ALWAYS = ("applicable", "This item applies to every dataset")


def unknown(pred):
    return ("unknown", f"{pred}: not declared; retained in the denominator")


def anyu(*preds):
    return ("unknown", "any: " + "; ".join(f"{p}: not declared; retained in the denominator" for p in preds))


ELEMENTS = [
    (1, "Dataset Discovery and Identification", "Can a user or system discover and uniquely identify this dataset?"),
    (2, "Dataset Access and Retrieval", "Can the dataset and its associated resources be located, accessed, and downloaded?"),
    (3, "Data Reuse and Interoperability", "Is sufficient information provided to reuse and integrate the dataset with others?"),
    (4, "Ethical Use and Privacy Safeguards", "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context?"),
    (5, "Data Composition and Structure", "Can the dataset's structure, modality, and population be understood from metadata?"),
    (6, "Data Provenance and Version Tracking", "Can a user determine dataset versions, update history, and provenance?"),
    (7, "Scientific Motivation and Funding Transparency", "Does the metadata clearly state why the dataset exists and who funded it?"),
    (8, "Technical Transparency (Data Collection and Processing)", "Can data collection and processing steps be replicated or understood?"),
    (9, "Dataset Evaluation and Limitations Disclosure", "Does the metadata communicate known risks, biases, or dataset limitations?"),
    (10, "Cross-Platform and Community Integration", "Does the dataset connect to relevant repositories, communities and standards?"),
]

# item_id: (name, applicability, score, evidence, quality_note, cited, absent, counts, considered)
ITEMS = {}


def item(iid, name, appl, score, evidence, note, cited=(), absent=(), counts=(), considered=()):
    ITEMS[iid] = dict(name=name, appl=appl, score=score, evidence=evidence, note=note,
                      cited=list(cited), absent=list(absent), counts=list(counts),
                      considered=list(considered))


# ---------------- Element 1 ----------------
item("E1.1", "Persistent Identifier (DOI, RRID, or URI)", ALWAYS, 0,
     "id is 'https://chorus4ai.org/', identical to page (the project website); doi is absent and no RRID is given.",
     "The only identifier is a project homepage URL, not a dataset-specific persistent identifier; no DOI to validate.",
     cited=[c("id", "https://chorus4ai.org/"), c("page")], absent=[a("doi")])
item("E1.2", "Dataset Title and Description Completeness", ALWAYS, 1,
     "title 'CHoRUS Dataset'; description (>1,500 chars) gives acronym expansion, 14 hospitals, 50,000 admissions, modalities, OMOP standardization and plans.",
     "Specific, source-attributed description that explains purpose, scope and modalities.",
     cited=[c("title", "CHoRUS Dataset"),
            c("description", "current released dataset of 50,000 patient admissions from ICU, PICU, and NICU")])
item("E1.3", "Keywords or Tags for Searchability", ALWAYS, 1,
     "Seven keywords: Critical Care, Critical Illness, Electronic Health Record, Electroencephalography, Machine Learning, social health determinants, data standards.",
     "Meets the >=5 threshold and covers domain, modality and method.",
     cited=[c("/keywords/0", "Critical Care")], counts=[n("keywords")])
item("E1.4", "Landing Page and Resources (page, hierarchical resources)", ALWAYS, 1,
     "page: https://chorus4ai.org/ (project landing page). No hierarchical resources.",
     "Landing page present and plausible; resources not used, which is not required for this item.",
     cited=[c("page", "https://chorus4ai.org/")], absent=[a("resources")])
item("E1.5", "Hierarchical Structure (parent datasets, relationships)", ALWAYS, 0,
     "parent_datasets and related_datasets are absent; the Bridge2AI consortium is mentioned only in description prose.",
     "No structured parent or related-dataset relationships.",
     absent=[a("parent_datasets"), a("related_datasets")], considered=["description"])

# ---------------- Element 2 ----------------
item("E2.1", "Access Policy and IP Restrictions Defined", ALWAYS, 1,
     "license_and_use_terms: participants 'must sign a licensing agreement ... before gaining access'; data_governance.access_review_process: 'Access is controlled', registration, .edu email requirement, and request contacts.",
     "A controlled-access policy with agreement requirement and request route is stated; agreement terms are not, and ip_restrictions is absent (marginal pass).",
     cited=[c("license_and_use_terms.license_terms", "must sign a licensing agreement"),
            c("data_governance.access_review_process", "Access is controlled")],
     absent=[a("ip_restrictions")], considered=["license_and_use_terms.source_caveats"])
item("E2.2", "Regulatory Compliance and Confidentiality Classification", unknown("regulated_access"), 0,
     "regulatory_restrictions (confidentiality level, HIPAA status, other compliance) and a governance committee contact are absent.",
     "Clinical EHR, notes, imaging and waveform data from 14 hospitals with no regulatory or confidentiality classification.",
     absent=[a("regulatory_restrictions"), a("data_governance.committee_contact")],
     considered=["data_governance.access_review_process"])
item("E2.3", "Download URL or Platform Link Available", ALWAYS, 0,
     "download_url absent; access_review_process gives request e-mail contacts and mentions a cloud enclave in the description without a platform link.",
     "No download URL or platform link; only request contacts.",
     absent=[a("download_url")], considered=["data_governance.access_review_process", "description"])
item("E2.4", "Distribution Formats and File Types Specified", ALWAYS, 0,
     "distribution_formats and file_collections absent; standards (OMOP, DICOM, WFDB, EDF+) appear only as data standards in conforms_to and instance descriptions.",
     "No distribution file types or media types for the release.",
     absent=[a("distribution_formats"), a("file_collections")], considered=["conforms_to", "conforms_to_standard", "instances"])
item("E2.5", "Related Datasets and External Resources Linked", ALWAYS, 1,
     "external_resources links the CHoRUS GitHub organization (https://github.com/chorus-ai#table-of-contents) describing SOPs, mappings and tooling; related_datasets absent.",
     "External documentation linked with a substantive description; related datasets missing (marginal pass).",
     cited=[c("/external_resources/0/description", "standard operating protocols for data contributing sites")],
     absent=[a("related_datasets")])

# ---------------- Element 3 ----------------
item("E3.1", "License Terms Allow Reuse", unknown("shared_dataset"), 0,
     "license_and_use_terms.source_caveats: 'The documents do not state the terms of the licensing agreement.'; source_caveats says no dataset license is stated.",
     "No license, so reuse permissions cannot be determined.",
     cited=[c("license_and_use_terms.source_caveats", "The documents do not state the terms of the licensing agreement."),
            c("source_caveats", "no document states a license for the dataset itself")],
     considered=["license_and_use_terms.license_terms"])
item("E3.2", "Data Formats Are Standardized (encoding, format)", unknown("shared_dataset"), 1,
     "conforms_to_standard lists OMOP_CDM, DICOM, WFDB; the EEG instance gives 'EDF+ and Persyst'. No file encoding.",
     "Standard clinical formats (DICOM, WFDB, EDF+, OMOP) are documented per modality; encoding and distribution_formats absent.",
     cited=[c("/conforms_to_standard/1", "DICOM"), c("/instances/10/description", "data standard EDF+ and Persyst")],
     absent=[a("distribution_formats"), a("file_collections")], considered=["conforms_to"])
item("E3.3", "Schema or Ontology Conformance Stated", unknown("shared_dataset"), 1,
     "conforms_to: 'OMOP, DICOM, WFDB'; conforms_to_standard: OMOP_CDM; description: 'standardize data to the OMOP Common Data Model'.",
     "OMOP CDM conformance explicitly stated.",
     cited=[c("conforms_to", "OMOP, DICOM, WFDB"), c("/conforms_to_standard/0", "OMOP_CDM")],
     absent=[a("conforms_to_schema")])
item("E3.4", "Variable Metadata with Identifiers Defined", unknown("shared_dataset"), 0,
     "variables absent; instances name data types (demographics, medications, flowsheets...) without variable-level metadata.",
     "No variable dictionary or identifiers.",
     absent=[a("variables")], considered=["instances"])
item("E3.5", "Use Guidance Provided (intended, prohibited uses)", ALWAYS, 0,
     "intended_uses, prohibited_uses and discouraged_uses absent; existing_uses lists training and publications and tasks list ML applications.",
     "Existing uses are not guidance on allowed, prohibited or discouraged uses.",
     absent=[a("intended_uses"), a("prohibited_uses"), a("discouraged_uses")], considered=["existing_uses", "tasks"])

# ---------------- Element 4 ----------------
item("E4.1", "IRB or Ethics Review and Data Protection Impact", anyu("human_subjects", "regulated_access"), 0,
     "ethical_reviews, human_subject_research and data_protection_impacts are absent although the record describes patient admissions from 14 hospitals.",
     "No ethics review, waiver or data protection assessment for clinical patient data.",
     absent=[a("ethical_reviews"), a("human_subject_research"), a("data_protection_impacts"), a("data_governance.committee_contact")],
     considered=["data_governance"])
item("E4.2", "Deidentification Method Described", anyu("human_subjects", "regulated_access"), 0,
     "is_deidentified.deidentification_details: 'Imaging: 1000 images are currently available, with de-identification in process for a larger cohort'.",
     "States de-identification is in process for imaging only; no method (Safe Harbor, Expert Determination, etc.) and no identifiers removed.",
     cited=[c("is_deidentified.deidentification_details", "with de-identification in process for a larger cohort")],
     absent=[a("is_deidentified.identifiers_removed")])
item("E4.3", "Privacy Protections and Re-identification Risk Assessment", unknown("human_subjects"), 0,
     "participant_privacy absent; description only states the plan to 'transform data using approaches that limit re-identification' and notes tokenization.",
     "No privacy protections or re-identification risk assessment documented.",
     absent=[a("participant_privacy")], considered=["description", "is_deidentified"])
item("E4.4", "Informed Consent Obtained from Participants", unknown("human_subjects"), 0,
     "informed_consent absent; retrospective collection is stated without consent or waiver information.",
     "No consent or waiver documentation.",
     absent=[a("informed_consent")], considered=["collection_mechanisms"])
item("E4.5", "Vulnerable Populations and Compensation Documented", unknown("human_subjects"), 0,
     "at_risk_populations and participant_compensation absent although subpopulations include PICU and NICU admissions (children, neonates) and critically ill patients.",
     "Pediatric/neonatal and critically ill populations present without protections documented.",
     absent=[a("at_risk_populations"), a("participant_compensation")], considered=["subpopulations"])

# ---------------- Element 5 ----------------
item("E5.1", "Cohort or Subpopulations Characteristics Described", ALWAYS, 1,
     "subpopulations ICU, PICU, NICU; description: critically ill patients admitted across 14 hospitals.",
     "Population characterized by care setting and acuity; no demographics, inclusion/exclusion criteria or per-unit counts (marginal pass).",
     cited=[c("/subpopulations/1/name", "PICU"),
            c("description", "acquire an AI-ready data set from more than 100,000 critically ill patients")],
     counts=[n("subpopulations")])
item("E5.2", "Number of Instances or Samples Reported", ALWAYS, 1,
     "instances: Patient admission counts 50000; Admission with radiology data counts 7642; 45K-as-of-August-2025 reconciled in source_caveats.",
     "Specific counts with units.",
     cited=[c("/instances/0/counts"), c("/instances/1/counts")], counts=[n("instances")])
item("E5.3", "Variable-Level Metadata, Tabular Flag, and Data Splits", ALWAYS, 0,
     "variables, is_tabular and subsets absent; splits records only a planned holdout test set.",
     "No variable dictionary, tabular flag or split/subpopulation flags.",
     cited=[c("/splits/0/split_details", "provision a holdout test set")],
     absent=[a("variables"), a("is_tabular"), a("subsets")])
item("E5.4", "Data Topics or Conditions Represented", ALWAYS, 1,
     "instances enumerate demographics, medication administration, procedures, nursing flowsheets, diagnoses, clinical notes, imaging, waveform telemetry and EEG for critical illness.",
     "Topics and modalities clearly represented.",
     cited=[c("/instances/7/description", "clinical notes, extracted and tokenized using the OHNLP toolkit")],
     counts=[n("instances")])
item("E5.5", "Data Quality, Anomalies, and Missing Data Documented", ALWAYS, 0,
     "anomalies, sampling_strategies and missing_data_documentation absent; only incidental status notes (EEG extraction in process).",
     "No quality, sampling or missingness documentation.",
     absent=[a("anomalies"), a("sampling_strategies"), a("missing_data_documentation")], considered=["source_caveats"])

# ---------------- Element 6 ----------------
SD = unknown("shared_dataset")
item("E6.1", "Dataset Version Number Provided", SD, 0, "version absent; only 'current released dataset' in prose.",
     "No version number.", absent=[a("version")], considered=["description"])
item("E6.2", "Version Access Methods Documented", SD, 0, "version_access absent.",
     "No information on accessing versions.", absent=[a("version_access")])
item("E6.3", "Change Descriptions and Errata Provided", SD, 0, "errata and updates absent.",
     "No change log or errata.", absent=[a("errata"), a("updates")])
item("E6.4", "Update Schedule or Frequency Indicated", SD, 0, "updates absent; growth from current to anticipated 100,000 admissions is described without a schedule.",
     "No update schedule.", absent=[a("updates")], considered=["description"])
item("E6.5", "Provenance, Source Derivation, and Raw Data Sources", SD, 1,
     "was_derived_from and raw_data_sources absent, but instances name source systems (PACS, bedside monitors and gateway/middleware, hospital EEG database) and collection_mechanisms describes site-created extracts following Chorus_SOP; notes holds only a contact.",
     "Source provenance is described in prose across instances and collection_mechanisms (marginal pass); no structured derivation.",
     cited=[c("/instances/9/description", "waveform telemetry from bedside monitors and gateway/middleware"),
            c("/instances/8/description", "imaging from PACS"),
            c("/collection_mechanisms/1/mechanism_details", "create and curate a CHoRUS-specific clinical data extract")],
     absent=[a("was_derived_from"), a("raw_data_sources"), a("updates")], considered=["notes"])

# ---------------- Element 7 ----------------
item("E7.1", "Motivation or Purpose for Dataset Creation", ALWAYS, 1,
     "purposes: 'develop a publicly available, AI-ready critical care dataset, while ensuring the methods promote privacy, accountability, and clinical benefit'; second purpose on recovery from acute illness.",
     "Clear, source-attributed rationale.",
     cited=[c("/purposes/0/response", "develop a publicly available, AI-ready critical care dataset")], counts=[n("purposes")])
item("E7.2", "Primary Research Objectives or Tasks", ALWAYS, 1,
     "tasks: characterizing acute and critical care illness; predicting complications; measuring treatment response.",
     "Specific ML/clinical tasks.",
     cited=[c("/tasks/1/response", "Predicting complications")], counts=[n("tasks")])
item("E7.3", "Funding Sources and Mechanisms Listed", ALWAYS, 1,
     "funders: grantor 'NIH Common Fund', Bridge2AI program, OT2 award with amount and project period.",
     "Funder and mechanism named.",
     cited=[c("/funders/0/grantor", "NIH Common Fund"),
            c("/funders/0/description", "within the NIH Common Fund's Bridge2AI program")])
item("E7.4", "Grant IDs or Award Numbers Present", ALWAYS, 1,
     "grant_number OT2OD032701; description gives RePORTER project number 1OT2OD032701-01.",
     "Matches NIH convention (activity OT2, institute OD, serial 032701); full project number consistent.",
     cited=[c("/funders/0/grants/0/grant_number", "OT2OD032701"),
            c("/funders/0/grants/0/description", "1OT2OD032701-01")])
item("E7.5", "Creators and Acknowledgements Documented", ALWAYS, 1,
     "creators: six Leadership Team members with affiliations, Eric S. Rosenthal as PI; source_caveats notes individual authorship roles are not stated.",
     "Named people and institutions; formal acknowledgements absent but creators adequately documented.",
     cited=[c("/creators/0/name", "Eric S. Rosenthal")], counts=[n("creators")], considered=["funders", "source_caveats"])

# ---------------- Element 8 ----------------
item("E8.1", "Collection Mechanisms and Settings Described", unknown("data_collection"), 1,
     "collection_mechanisms: 'Retrospective data collection'; sites create and curate a CHoRUS-specific extract following the Chorus_SOP workflow; setting is ICU/PICU/NICU at 14 hospitals.",
     "Procedure and setting described; collection timeframe absent.",
     cited=[c("/collection_mechanisms/0/mechanism_details", "Retrospective data collection"),
            c("/collection_mechanisms/1/mechanism_details", "step-by-step process for extracting and contributing clinical data")],
     counts=[n("collection_mechanisms")])
item("E8.2", "Data Acquisition Methods Listed", unknown("data_collection"), 1,
     "acquisition_methods and raw_data_sources absent; instance descriptions name acquisition systems: PACS imaging, bedside monitors and gateway/middleware for telemetry, hospital EEG database, time-stamped medication administration.",
     "Acquisition sources/devices identifiable from instance descriptions (marginal pass).",
     cited=[c("/instances/9/description", "bedside monitors and gateway/middleware"),
            c("/instances/3/description", "dosing time-stamped upon each infusion change or dose administration")],
     absent=[a("acquisition_methods"), a("raw_data_sources")])
item("E8.3", "Preprocessing, Cleaning, Labeling, and Annotation Quality", unknown("data_processing"), 1,
     "preprocessing_strategies: semantic mapping to international standards with clinical validation SOP; instances: notes tokenized; description: standardize to OMOP.",
     "Standardization/mapping step described at a high level; cleaning, labeling, annotation and imputation absent (marginal pass).",
     cited=[c("/preprocessing_strategies/0/preprocessing_details", "validated semantic mappings for connecting clinical data in various source formats to international standards")],
     absent=[a("cleaning_strategies"), a("labeling_strategies"), a("annotation_analyses"), a("machine_annotation_tools"), a("imputation_protocols")])
item("E8.4", "Software and Tools Documented", unknown("processing_software"), 0,
     "No used_software anywhere. preprocessing_strategies names the chorus-mapping repository as holding documentation and pooled tabular mappings (mapping content, not named transforming software); external_resources points only to the chorus-ai GitHub organization root (publisher pointer); collection_mechanisms mentions an unnamed extract/upload tool repository. The OHNLP toolkit is named only in an instances description, outside the designated software slots.",
     "No transforming software named in the designated slots; organization-root pointer neither earns nor forfeits.",
     cited=[c("/preprocessing_strategies/0/preprocessing_details", "a chorus-mapping repository holds documentation and pooled tabular mappings"),
            c("/external_resources/0/external_resources/0", "https://github.com/chorus-ai#table-of-contents")],
     absent=[a("cleaning_strategies"), a("labeling_strategies"), a("imputation_protocols"), a("machine_annotation_tools")],
     considered=["instances", "collection_mechanisms"])
item("E8.5", "External Standards, Resources, and Imputation Protocols", ALWAYS, 0,
     "conforms_to OMOP, DICOM, WFDB and the GitHub organization link are present; imputation_protocols absent and no statement on whether imputation was used.",
     "Standards and one external link present, but the imputation part of the item's scope is undocumented.",
     cited=[c("conforms_to", "OMOP, DICOM, WFDB"), c("/external_resources/0/name", "CHoRUS GitHub organization (chorus-ai)")],
     absent=[a("imputation_protocols")])

# ---------------- Element 9 ----------------
item("E9.1", "Known Limitations Documented", ALWAYS, 0,
     "known_limitations absent; source_caveats documents source-document conflicts rather than dataset limitations.",
     "No dataset limitations section.", absent=[a("known_limitations")], considered=["source_caveats"])
item("E9.2", "Biases Categorized Using Standard Taxonomy (RAI-aligned)", ALWAYS, 0,
     "known_biases and future_use_impacts absent; 'Equitable AI' in grant name and 'most diverse' in purposes are aspirations, not bias documentation.",
     "No bias categorization.", absent=[a("known_biases"), a("future_use_impacts")], considered=["purposes", "funders"])
item("E9.3", "Data Anomalies and Quality Issues Noted", ALWAYS, 0,
     "anomalies absent.", "No anomalies documented.", absent=[a("anomalies")], considered=["source_caveats"])
item("E9.4", "Sensitive Content and Warnings Provided", ALWAYS, 0,
     "sensitive_elements and content_warnings absent despite clinical notes, diagnoses and pediatric/neonatal data.",
     "Sensitive health content not flagged.", absent=[a("sensitive_elements"), a("content_warnings")], considered=["instances"])
item("E9.5", "Ethical Review and Social Impact Analysis", ALWAYS, 0,
     "ethical_reviews and future_use_impacts absent.",
     "No ethical review or downstream social impact analysis.", absent=[a("ethical_reviews"), a("future_use_impacts")])

# ---------------- Element 10 ----------------
item("E10.1", "Dataset Published on a Recognized Platform", SD, 0,
     "publisher absent; data reside in an unnamed cloud enclave per description.",
     "No hosting platform or repository named.", absent=[a("publisher")], considered=["description"])
item("E10.2", "Citation and DOI for Cross-referencing", SD, 0,
     "citation and doi absent.", "Neither citation nor DOI; scored 0 per rule.", absent=[a("citation"), a("doi")])
item("E10.3", "Community Standards or Schema Conformance", SD, 1,
     "conforms_to 'OMOP, DICOM, WFDB'; conforms_to_standard OMOP_CDM, DICOM, WFDB.",
     "Recognized community standards stated.",
     cited=[c("conforms_to", "OMOP, DICOM, WFDB"), c("/conforms_to_standard/2", "WFDB")], counts=[n("conforms_to_standard")])
item("E10.4", "Outreach Materials and Documentation Links", SD, 1,
     "page https://chorus4ai.org/; external_resources GitHub organization with SOPs; existing_uses cites the AIM-AHEAD Bridge2AI for Clinical Care Training Program and hands-on training.",
     "Landing page and documentation link plus training outreach.",
     cited=[c("page"), c("/external_resources/0/external_resources/0"),
            c("/existing_uses/0/examples/0", "AIM-AHEAD Bridge2AI for Clinical Care Training Program")])
item("E10.5", "Related Datasets with Typed Relationships", SD, 0,
     "related_datasets absent.", "No typed relationships.", absent=[a("related_datasets")])

ISSUES = [
    dict(id="I1", type="completeness", category="persistent_identifier", score_effect="lowered",
         item_ids=["E1.1", "E10.2"], severity="high",
         description="No DOI or dataset-level persistent identifier; id reuses the project homepage URL and no citation is given."),
    dict(id="I2", type="completeness", category="other", score_effect="lowered", item_ids=["E1.5", "E10.5"], severity="medium",
         description="parent_datasets and related_datasets absent; Bridge2AI consortium relationship only in prose."),
    dict(id="I3", type="completeness", category="privacy_regulatory", score_effect="lowered", item_ids=["E2.2"], severity="high",
         description="No regulatory compliance, confidentiality classification or governance committee contact for multi-hospital clinical data."),
    dict(id="I4", type="completeness", category="format_access", score_effect="lowered", item_ids=["E2.3", "E2.4", "E10.1"], severity="medium",
         description="No download URL or platform link, no distribution formats/media types, and no named publisher/hosting platform."),
    dict(id="I5", type="completeness", category="license_use_terms", score_effect="lowered", item_ids=["E3.1", "E3.5"], severity="high",
         description="Licensing agreement terms unstated and no intended/prohibited/discouraged use guidance."),
    dict(id="I6", type="completeness", category="variables_metadata", score_effect="lowered", item_ids=["E3.4", "E5.3"], severity="medium",
         description="No variable-level metadata, tabular flag or subset split/subpopulation flags."),
    dict(id="I7", type="consistency", category="consent_ethics", score_effect="lowered",
         item_ids=["E4.1", "E4.3", "E4.4", "E9.5"], severity="high",
         description="Record describes patient admissions, clinical notes and imaging from 14 hospitals (human-subjects data) yet has no human_subject_research, ethics review/waiver, consent or privacy assessment."),
    dict(id="I8", type="consistency", category="privacy_regulatory", score_effect="lowered", item_ids=["E4.2"], severity="high",
         description="is_deidentified is populated but states only that imaging de-identification is in process; no method or identifiers removed."),
    dict(id="I9", type="content_accuracy", category="consent_ethics", score_effect="lowered", item_ids=["E4.5", "E9.4"], severity="medium",
         description="PICU/NICU (pediatric, neonatal) and critically ill populations and sensitive clinical content are present without at_risk_populations, sensitive_elements or content warnings."),
    dict(id="I10", type="completeness", category="bias_quality", score_effect="lowered", item_ids=["E5.5", "E9.1", "E9.2", "E9.3"], severity="medium",
         description="No known limitations, biases, anomalies, sampling or missing-data documentation."),
    dict(id="I11", type="completeness", category="temporal_version", score_effect="lowered", item_ids=["E6.1", "E6.2", "E6.3", "E6.4"], severity="medium",
         description="No version, version access, errata/updates or update schedule though the record distinguishes a current release from an anticipated final dataset."),
    dict(id="I12", type="completeness", category="processing_provenance", score_effect="lowered", item_ids=["E8.4", "E8.5"], severity="medium",
         description="No transforming software named in the designated software slots (OHNLP toolkit appears only in an instances description) and no imputation protocol or statement that none was used."),
    dict(id="I13", type="consistency", category="count_size", score_effect="noted_only", item_ids=[], severity="low",
         description="Admissions reported as 50,000 (website, current release) and over 45K (webinar, August 2025); the record reconciles these explicitly in source_caveats."),
    dict(id="I14", type="correctness", category="attribution", score_effect="noted_only", item_ids=[], severity="low",
         description="notes contact e-mail domain 'mgh.havard.edu' appears misspelled; the record flags it as written on the source site."),
    dict(id="I15", type="semantic_understanding", category="scope_drift", score_effect="noted_only", item_ids=[], severity="low",
         description="Several statements (100,000 patients, holdout test set, final 9 modalities) are plans; the record labels them as planned, but readers must distinguish them from the current release."),
]


EXTRA = {
    "I1": (["id", "doi", "citation"], "Mint or record a dataset DOI and a recommended citation; keep the homepage in page."),
    "I2": (["parent_datasets", "related_datasets"], "Add typed relationships (e.g. part of the Bridge2AI program, related CHoRUS releases)."),
    "I3": (["regulatory_restrictions", "data_governance.committee_contact"], "State HIPAA/confidentiality classification, applicable frameworks and the governance contact, if sources support it."),
    "I4": (["download_url", "distribution_formats", "file_collections", "publisher"], "Name the hosting enclave/platform, its access URL and the released file formats and media types."),
    "I5": (["license_and_use_terms", "intended_uses", "prohibited_uses", "discouraged_uses"], "Document the data use agreement terms and allowed, prohibited and discouraged uses."),
    "I6": (["variables", "is_tabular", "subsets"], "Link the OMOP CDM data dictionary or list key variables; set tabular and split flags."),
    "I7": (["human_subject_research", "ethical_reviews", "informed_consent", "participant_privacy", "future_use_impacts"], "Record IRB/ethics oversight or waiver, consent basis for retrospective data, privacy protections and social impacts, if documented in sources."),
    "I8": (["is_deidentified"], "Describe the de-identification method and identifiers removed for each modality."),
    "I9": (["at_risk_populations", "sensitive_elements", "content_warnings", "subpopulations"], "Document protections for pediatric/neonatal and critically ill patients and flag sensitive clinical content."),
    "I10": (["known_limitations", "known_biases", "anomalies", "sampling_strategies", "missing_data_documentation"], "Add known limitations, bias categories, anomalies and missingness patterns."),
    "I11": (["version", "version_access", "errata", "updates"], "Record the release version, how to access versions and the update plan."),
    "I12": (["preprocessing_strategies", "external_resources", "imputation_protocols", "instances"], "Name transforming software (e.g. tokenization and mapping tools) under used_software and state whether imputation was used."),
    "I13": (["instances", "source_caveats"], "Keep the dated count reconciliation; attach dates to counts."),
    "I14": (["notes"], "Verify the contact address against the source before reuse."),
    "I15": (["description", "splits"], "Keep plan statements clearly marked as planned."),
}
for _iss in ISSUES:
    _iss["fields_involved"], _iss["recommendation"] = EXTRA[_iss["id"]]


def build():
    linked = {i for iss in ISSUES if iss["score_effect"] == "lowered" for i in iss["item_ids"]}
    elements = []
    total = 0
    for eid, ename, edesc in ELEMENTS:
        subs = []
        escore = 0
        for k in range(1, 6):
            iid = f"E{eid}.{k}"
            it = ITEMS[iid]
            status, aev = it["appl"]
            unit = {"path": "#", "score": it["score"], "evidence": it["evidence"],
                    "cited": it["cited"], "absent": it["absent"], "counts": it["counts"],
                    "considered": it["considered"]}
            sub = {"name": it["name"], "item_id": iid, "score": it["score"], "evidence": it["evidence"],
                   "quality_note": it["note"], "applicable": True, "applicability_status": status,
                   "applicability_evidence": aev, "unit_scores": [unit]}
            if it["score"] == 0:
                assert iid in linked, iid
            escore += it["score"]
            subs.append(sub)
        total += escore
        elements.append({"id": eid, "name": ename, "description": edesc, "sub_elements": subs,
                         "element_score": escore, "element_max": 5})
    for iss in ISSUES:
        for i in iss["item_ids"]:
            assert ITEMS[i]["score"] == 0, i
    return elements, total


def main():
    elements, total = build()
    ctx = CONTEXT
    out = {
        "rubric": "rubric10-semantic",
        "version": "3.0",
        "d4d_file": str(D4D.relative_to(ROOT)),
        "project": "CHORUS",
        "method": "claudecode_agent",
        "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3",
        "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": {"name": "claude-opus-5-5", "evaluator_model": "claude-opus-5-5", "temperature": None,
                  "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
                  "evaluation_type": "semantic_llm_judge"},
        "overall_score": {"total_points": total, "max_points": 50, "excluded_max_points": 0,
                          "adjusted_max_points": 50,
                          "normalized_percentage": round(total / 50 * 100, 1),
                          "fixed_percentage": round(total / 50 * 100, 1),
                          "sub_elements_not_applicable": 0, "excluded_item_ids": []},
        "elements": elements,
        "semantic_analysis": {
            "issues_detected": ISSUES,
            "semantic_insights": [
                "Record is strongly source-attributed and transparent about uncertainty (source_caveats), but core governance, ethics, licensing and versioning fields are empty.",
                "No caller applicability context was supplied, so all 50 items stay in the denominator; Element 4 is scored even though the record plainly describes patient data.",
                "Funding is the strongest area: grantor, program, award number OT2OD032701 and full RePORTER project number agree.",
            ],
            "consistency_checks": {"passed": 2, "failed": 2, "warnings": 2},
            "correctness_validations": {
                "doi_format": "absent: no DOI provided",
                "grant_number_format": "valid: OT2OD032701 / 1OT2OD032701-01 match NIH activity-institute-serial pattern",
                "rrid_format": "absent: no RRID provided",
                "url_validity": "valid structure: https://chorus4ai.org/ and https://github.com/chorus-ai#table-of-contents; contact domain 'mgh.havard.edu' likely misspelled (noted in record)",
            },
        },
        "applicability_context": ctx,
        "evaluation_scope": {"policy": "single_dataset", "units": [{"path": "#", "id": DOC["id"]}],
                             "collection_metadata_inherited": False},
        "metadata": {
            "instrument_sha256": sha(AGENT),
            "evidence_authority_sha256": sha(AUTH),
            "rubric_sha256": sha(RUBRIC),
            "input_sha256": sha(D4D),
            "context_sha256": context_digest(ctx),
            "evaluator_model": "claude-opus-5-5",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    assert not OUT.exists() or "--overwrite-own" in sys.argv, f"{OUT} exists"
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print("wrote", OUT, "total", total)


if __name__ == "__main__":
    main()
