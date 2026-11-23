# Purpose: serialize the rubric10-semantic (v3, general context instrument) judgements made by the
#   evaluating session (claude-opus-5-5) for one D4D record into the required JSON structure.
# Input: data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CHORUS_d4d.yaml
#   (hashed only; the scores below are the evaluator's manual judgements), rubric10.txt, agent definition,
#   semantic_evidence_authority_v3.json.
# Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep2_evaluation.json
# Date: 2026-11-22. No caller applicability context was supplied (empty context; all predicates unknown).
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from data_sheets_schema.evaluation_context import context_digest, normalize_context

ROOT = Path(__file__).resolve().parents[2]
INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CHORUS_d4d.yaml"
OUT = ROOT / "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CHORUS_2026-11-22b_rep2_evaluation.json"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


ALWAYS = ("applicable", "This item applies to every dataset")


def unk(pred):
    return ("unknown", f"{pred}: not declared; retained in the denominator")


def anyunk(*preds):
    return ("unknown", "any: " + "; ".join(f"{p}: not declared; retained in the denominator" for p in preds))


def item(iid, name, score, evidence, note, appl, cited=(), absent=(), counts=(), considered=(), nir=None):
    status, aev = appl
    d = {
        "item_id": iid,
        "name": name,
        "score": score,
        "evidence": evidence,
        "quality_note": note,
        "applicable": True,
        "applicability_status": status,
        "applicability_evidence": aev,
        "unit_scores": [{
            "path": "#",
            "score": score,
            "evidence": evidence,
            "cited": [dict(path=p, **({"quote": q} if q else {})) for p, q in cited],
            "absent": [{"path": p} for p in absent],
            "counts": [{"path": p, "claimed": c} for p, c in counts],
            "considered": list(considered),
        }],
    }
    if nir:
        d["no_issue_reason"] = nir
    return d


E = []

E.append(("Dataset Discovery and Identification", "Can a user or system discover and uniquely identify this dataset?", [
    item("E1.1", "Persistent Identifier (DOI, RRID, or URI)", 0,
         "id is 'https://chorus4ai.org/', the project website root, identical to page; no doi field.",
         "A project homepage URL is not a persistent dataset identifier; no DOI or RRID is given.", ALWAYS,
         cited=[("id", "https://chorus4ai.org/")], absent=["doi"], considered=["page"]),
    item("E1.2", "Dataset Title and Description Completeness", 1,
         "title 'CHoRUS Dataset'; description is a long, specific account of scope, counts (50,000 admissions, 1.6 billion OMOP rows, 23 Tb waveform), modalities and purpose.",
         "Clear title and comprehensive, source-attributed description well over 200 characters.", ALWAYS,
         cited=[("title", "CHoRUS Dataset"), ("description", "multicenter, multimodal, high-resolution clinical care dataset")]),
    item("E1.3", "Keywords or Tags for Searchability", 1,
         "Seven keywords: Critical Care, Critical Illness, Electroencephalography, Electronic Health Record, Machine Learning, social health determinants, AI for Clinical Care.",
         "At least five relevant keywords spanning domain, modality and method.", ALWAYS,
         cited=[("/keywords/0", "Critical Care")], counts=[("keywords", 7)]),
    item("E1.4", "Landing Page and Resources (page, hierarchical resources)", 1,
         "page: https://chorus4ai.org/ (project landing page).",
         "Accessible landing page URL present; no hierarchical resources, which are not required.", ALWAYS,
         cited=[("page", "https://chorus4ai.org/")], absent=["resources"]),
    item("E1.5", "Hierarchical Structure (parent datasets, relationships)", 0,
         "No parent_datasets or related_datasets. Subsets describe modalities within the dataset, not parent/related datasets; the Bridge2AI consortium is mentioned only in prose.",
         "No typed hierarchical relationships documented.", ALWAYS,
         absent=["parent_datasets", "related_datasets"], considered=["subsets", "description"]),
], 5))

E.append(("Dataset Access and Retrieval", "Can the dataset and its associated resources be located, accessed, and downloaded?", [
    item("E2.1", "Access Policy and IP Restrictions Defined", 1,
         "license_and_use_terms: participants 'must sign a licensing agreement' before access; data_governance.access_review_process: 'Controlled access', registration form, .edu requirement, access request contacts.",
         "A controlled-access policy with a signed licensing agreement is described, though only for the training-program route; ip_restrictions absent.", ALWAYS,
         cited=[("license_and_use_terms.license_terms", "must sign a licensing agreement"),
                ("data_governance.access_review_process", "Controlled access (AIM-AHEAD webinar).")],
         absent=["ip_restrictions"]),
    item("E2.2", "Regulatory Compliance and Confidentiality Classification", 0,
         "No regulatory_restrictions (no HIPAA status, confidentiality level or other compliance framework) and no governance committee contact, although the data are multi-hospital EHR, notes and imaging.",
         "Regulatory compliance and confidentiality classification undocumented.", unk("regulated_access"),
         absent=["regulatory_restrictions", "data_governance.committee_contact"],
         considered=["data_governance.access_review_process", "data_governance.description"]),
    item("E2.3", "Download URL or Platform Link Available", 0,
         "No download_url and no enclave/platform URL; access is by registration form and email request to named contacts.",
         "Access request contacts are given, but no download link or platform link.", ALWAYS,
         absent=["download_url"], considered=["data_governance.access_review_process", "distribution_formats"]),
    item("E2.4", "Distribution Formats and File Types Specified", 0,
         "distribution_formats has one entry, 'Cloud enclave', describing where data reside; no format or media_type. Modality standards (OMOP_CDM, DICOM, WFDB, EDF+) appear on subsets but no delivered file types are stated.",
         "Distribution entry names an access environment, not file formats or MIME types.", ALWAYS,
         cited=[("/distribution_formats/0/name", "Cloud enclave")],
         absent=["distribution_formats.format", "distribution_formats.media_type", "file_collections"],
         considered=["subsets", "conforms_to_standard"]),
    item("E2.5", "Related Datasets and External Resources Linked", 0,
         "No related_datasets or external_resources; the webinar, grant abstract and GitHub organization are cited in prose without links.",
         "No linked related datasets or external documentation.", ALWAYS,
         absent=["related_datasets", "external_resources"], considered=["description"]),
], 5))

E.append(("Data Reuse and Interoperability",
          "Is sufficient information provided to reuse and integrate the dataset with others?\nNote: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.\n", [
    item("E3.1", "License Terms Allow Reuse", 0,
         "license_and_use_terms names only an unspecified licensing agreement; source_caveats states that 'no source states a license for the dataset'.",
         "No named licence or stated reuse permissions.", unk("shared_dataset"),
         cited=[("license_and_use_terms.license_terms", "must sign a licensing agreement"),
                ("source_caveats", "no source states a license for the dataset")]),
    item("E3.2", "Data Formats Are Standardized (encoding, format)", 1,
         "Subsets declare standard data formats per modality: OMOP_CDM (structured EHR), DICOM (imaging), WFDB (waveform telemetry), 'EDF+ and Persyst' (EEG); top-level conforms_to_standard lists OMOP_CDM, DICOM, WFDB.",
         "Standard formats are named per modality; character encoding and file-level format fields are absent.", unk("shared_dataset"),
         cited=[("/subsets/2/conforms_to_standard/0", "DICOM"), ("/subsets/3/conforms_to_standard/0", "WFDB"),
                ("/subsets/4/conforms_to", "EDF+ and Persyst")],
         absent=["file_collections"], considered=["distribution_formats", "conforms_to_standard"]),
    item("E3.3", "Schema or Ontology Conformance Stated", 1,
         "conforms_to_standard: OMOP_CDM, DICOM, WFDB; the structured EHR subset conforms to OMOP_CDM.",
         "Conformance to the OMOP Common Data Model and modality standards is stated.", unk("shared_dataset"),
         cited=[("/conforms_to_standard/0", "OMOP_CDM"), ("/subsets/0/conforms_to_standard/0", "OMOP_CDM")],
         counts=[("conforms_to_standard", 3)], absent=["conforms_to_schema"]),
    item("E3.4", "Variable Metadata with Identifiers Defined", 0,
         "No variables field; the data-type table's metadata columns were explicitly not recorded (source_caveats).",
         "No variable-level metadata.", unk("shared_dataset"),
         absent=["variables"], considered=["subsets", "source_caveats"]),
    item("E3.5", "Use Guidance Provided (intended, prohibited uses)", 0,
         "No intended_uses, prohibited_uses or discouraged_uses; existing_uses (training, publications) and tasks describe current/planned uses but give no allowed/prohibited guidance.",
         "Use guidance absent.", ALWAYS,
         absent=["intended_uses", "prohibited_uses", "discouraged_uses"], considered=["existing_uses", "tasks"]),
], 5))

E.append(("Ethical Use and Privacy Safeguards",
          "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.", [
    item("E4.1", "IRB or Ethics Review and Data Protection Impact", 0,
         "No ethical_reviews, human_subject_research or data_protection_impacts. data_governance.description reports planned community ethics focus groups, which is not an ethics review or impact assessment.",
         "Ethics oversight for retrospective patient data from 14 hospitals is not documented.", anyunk("human_subjects", "regulated_access"),
         absent=["ethical_reviews", "human_subject_research", "data_protection_impacts", "data_governance.committee_contact"],
         considered=["data_governance.description"]),
    item("E4.2", "Deidentification Method Described", 0,
         "No is_deidentified; participant_privacy states only that imaging de-identification was 'in process' and a planned approach to limit re-identification.",
         "No de-identification method (e.g., Safe Harbor, Expert Determination) is described.", anyunk("human_subjects", "regulated_access"),
         cited=[("/participant_privacy/0/description", "de-identification of imaging was in process")],
         absent=["is_deidentified"]),
    item("E4.3", "Privacy Protections and Re-identification Risk Assessment", 0,
         "participant_privacy records a plan 'to transform data using approaches that limit re-identification' and in-process imaging de-identification; no re-identification risk assessment or concrete protections.",
         "Privacy entry is planned/in-process only; no risk assessment.", unk("human_subjects"),
         cited=[("/participant_privacy/0/description", "approaches that limit re-identification")],
         absent=["participant_privacy.reidentification_risk"]),
    item("E4.4", "Informed Consent Obtained from Participants", 0,
         "No informed_consent field; neither consent nor a waiver for retrospective EHR use is documented.",
         "Consent or waiver undocumented.", unk("human_subjects"),
         absent=["informed_consent"]),
    item("E4.5", "Vulnerable Populations and Compensation Documented", 0,
         "No at_risk_populations or participant_compensation, although the description includes PICU and NICU admissions (children, neonates).",
         "Vulnerable populations evidently present but unaddressed.", unk("human_subjects"),
         cited=[("description", "50,000 patient admissions from ICU, PICU, and NICU")],
         absent=["at_risk_populations", "participant_compensation"]),
], 5))

E.append(("Data Composition and Structure", "Can the dataset's structure, modality, and population be understood from metadata?", [
    item("E5.1", "Cohort or Subpopulations Characteristics Described", 0,
         "No subpopulations; population is characterised only as ICU/PICU/NICU admissions across 14 hospitals. Subsets are modality partitions, not cohort characteristics; no demographics or inclusion/exclusion criteria.",
         "Cohort characteristics limited to care setting.", ALWAYS,
         absent=["subpopulations", "subsets.is_subpopulation"], considered=["subsets", "instances", "description"]),
    item("E5.2", "Number of Instances or Samples Reported", 1,
         "instances: 'Patient admissions', counts 50000, with source caveats reconciling the webinar's 'over 45K' and the 100,000 targets.",
         "Specific count with clear unit and reconciled sources.", ALWAYS,
         cited=[("/instances/0/counts", None), ("/instances/0/instance_type", "patient admission")]),
    item("E5.3", "Variable-Level Metadata, Tabular Flag, and Data Splits", 0,
         "No variables, is_tabular, or subset split/subpopulation flags; splits contains only a planned holdout test set.",
         "No data dictionary or flags; split is a plan.", ALWAYS,
         absent=["variables", "is_tabular", "subsets.is_data_split", "subsets.is_subpopulation"],
         considered=["splits", "subsets"]),
    item("E5.4", "Data Topics or Conditions Represented", 1,
         "instances describe patient admissions from ICU, PICU and NICU and 'critically ill patients'; description and tasks frame the topic as acute and critical illness, with modalities enumerated.",
         "Topic (critical and acute illness in intensive care) is clear, though specific diagnoses are not enumerated.", ALWAYS,
         cited=[("/instances/0/description", "50,000 patient admissions from ICU, PICU, and NICU")], considered=["tasks", "keywords"]),
    item("E5.5", "Data Quality, Anomalies, and Missing Data Documented", 0,
         "No anomalies or missing_data_documentation; the only sampling_strategies entry is 'Planned, not described as performed'.",
         "Quality issues and missing data undocumented; sampling is a plan.", ALWAYS,
         cited=[("/sampling_strategies/0/strategies", "Planned, not described as performed")],
         absent=["anomalies", "missing_data_documentation"]),
], 5))

E.append(("Data Provenance and Version Tracking", "Can a user determine dataset versions, update history, and provenance?", [
    item("E6.1", "Dataset Version Number Provided", 0,
         "No version field; 'current released dataset' is described without a version identifier.",
         "No version number.", unk("shared_dataset"), absent=["version"], considered=["updates.update_details"]),
    item("E6.2", "Version Access Methods Documented", 0,
         "No version_access.", "No method to access prior or alternative versions.", unk("shared_dataset"),
         absent=["version_access"]),
    item("E6.3", "Change Descriptions and Errata Provided", 0,
         "No errata; updates.update_details contrasts the current and anticipated final dataset and in-process imaging/EEG work, but no change log between releases.",
         "Roadmap status rather than change descriptions.", unk("shared_dataset"),
         cited=[("updates.update_details", "distinguishes the current released dataset")], absent=["errata"]),
    item("E6.4", "Update Schedule or Frequency Indicated", 0,
         "updates.update_details gives no schedule, frequency or maintenance plan.",
         "No update schedule.", unk("shared_dataset"),
         cited=[("updates.update_details", "EEG extraction was in process")]),
    item("E6.5", "Provenance, Source Derivation, and Raw Data Sources", 1,
         "raw_data_sources names PACS (imaging), bedside monitors and gateway/middleware (telemetry), and a hospital EEG database; collection_mechanisms states multi-modal collection from 14 hospitals.",
         "Raw sources mapped to modalities; no was_derived_from.", unk("shared_dataset"),
         cited=[("/raw_data_sources/1/source_description", "bedside monitors and gateway/middleware")],
         counts=[("raw_data_sources", 3)], absent=["was_derived_from"], considered=["updates.update_details", "notes"]),
], 5))

E.append(("Scientific Motivation and Funding Transparency", "Does the metadata clearly state why the dataset exists and who funded it?", [
    item("E7.1", "Motivation or Purpose for Dataset Creation", 1,
         "purposes quote the grant abstract ('publicly available, AI-ready critical care dataset') and GitHub overview; addressing_gaps states the need for AI/ML infrastructure in critical care.",
         "Clear, sourced rationale.", ALWAYS,
         cited=[("/purposes/0/description", "publicly available, AI-ready critical care")], considered=["addressing_gaps"]),
    item("E7.2", "Primary Research Objectives or Tasks", 1,
         "tasks: characterizing acute and critical care illness, predicting complications, measuring treatment response.",
         "Specific ML application tasks.", ALWAYS,
         cited=[("/tasks/1/name", "Predicting complications")], counts=[("tasks", 3)]),
    item("E7.3", "Funding Sources and Mechanisms Listed", 1,
         "funders: NIH, NIH Common Fund Bridge2AI program, OT2 award; MGH as awardee organization.",
         "Named funder and mechanism.", ALWAYS,
         cited=[("/funders/0/grantor", "NIH"), ("/funders/0/description", "NIH Common Fund's Bridge2AI program")]),
    item("E7.4", "Grant IDs or Award Numbers Present", 1,
         "grant_number OT2OD032701 (NIH RePORTER project 1OT2OD032701-01), consistent with funders.description.",
         "Award identifier follows the NIH activity-code/institute/serial pattern (OT2 OD 032701).", ALWAYS,
         cited=[("/funders/0/grants/0/grant_number", "OT2OD032701")]),
    item("E7.5", "Creators and Acknowledgements Documented", 1,
         "Six creators with affiliations (MGH, University of Florida, UTHealth Houston, Tufts); Eric Rosenthal identified as PI.",
         "Creators documented as the project leadership team.", ALWAYS,
         counts=[("creators", 6)], cited=[("/creators/0/name", "Eric Rosenthal")]),
], 5))

E.append(("Technical Transparency (Data Collection and Processing)",
          "Can data collection and processing steps be replicated or understood?\nNote: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.\n", [
    item("E8.1", "Collection Mechanisms and Settings Described", 1,
         "collection_mechanisms: retrospective multicenter collection across 14 hospitals; site extraction and contribution under SOPs with extract/upload tools and characterization reports.",
         "Procedure and setting described; collection timeframe absent.", unk("data_collection"),
         cited=[("/collection_mechanisms/0/description", "retrospective data collection")], counts=[("collection_mechanisms", 2)]),
    item("E8.2", "Data Acquisition Methods Listed", 0,
         "No acquisition_methods; raw_data_sources name source systems (PACS, bedside monitors/gateway, hospital EEG database) without capture instruments, extraction methods or parameters.",
         "Source-system names do not describe acquisition methods.", unk("data_collection"),
         absent=["acquisition_methods"], considered=["raw_data_sources", "collection_mechanisms"]),
    item("E8.3", "Preprocessing, Cleaning, Labeling, and Annotation Quality", 1,
         "preprocessing_strategies: OMOP standardization, clinical note extraction and tokenization with OHNLP, semantic mappings with a clinical validation SOP; labeling is only planned.",
         "Concrete preprocessing steps documented; cleaning, annotation quality and imputation absent.", unk("data_processing"),
         cited=[("/preprocessing_strategies/1/preprocessing_details", "extracted and tokenized using the OHNLP toolkit")],
         counts=[("preprocessing_strategies", 3)],
         absent=["cleaning_strategies", "annotation_analyses", "machine_annotation_tools", "imputation_protocols"],
         considered=["labeling_strategies"]),
    item("E8.4", "Software and Tools Documented", 1,
         "preprocessing_strategies names the OHNLP toolkit as the software that extracted and tokenized clinical notes; the tokens are the part of the notes held in the enclave, so the software transformed released data.",
         "Processing software named (slot: preprocessing_strategies); no version or repository link.", unk("processing_software"),
         cited=[("/preprocessing_strategies/1/preprocessing_details", "OHNLP toolkit")],
         absent=["preprocessing_strategies.used_software", "external_resources"], considered=["subsets"]),
    item("E8.5", "External Standards, Resources, and Imputation Protocols", 0,
         "No external_resources, conforms_to or imputation_protocols at dataset level; standards appear only as conforms_to_standard labels (credited under E3.3/E10.3) and source documents are cited in prose without links; imputation is not addressed.",
         "External documentation and imputation statement absent.", ALWAYS,
         absent=["external_resources", "conforms_to", "imputation_protocols"], considered=["conforms_to_standard"]),
], 5))

E.append(("Dataset Evaluation and Limitations Disclosure", "Does the metadata communicate known risks, biases, or dataset limitations?", [
    item("E9.1", "Known Limitations Documented", 0,
         "No known_limitations; source_caveats addresses source reconciliation, not dataset limitations; in-process imaging/EEG coverage is mentioned only in updates.",
         "No limitations section.", ALWAYS, absent=["known_limitations"], considered=["source_caveats", "updates.update_details"]),
    item("E9.2", "Biases Categorized Using Standard Taxonomy (RAI-aligned)", 0,
         "No known_biases or future_use_impacts.", "Biases undocumented.", ALWAYS,
         absent=["known_biases", "future_use_impacts"]),
    item("E9.3", "Data Anomalies and Quality Issues Noted", 0,
         "No anomalies field.", "Anomalies undocumented.", ALWAYS, absent=["anomalies"]),
    item("E9.4", "Sensitive Content and Warnings Provided", 0,
         "No sensitive_elements or content_warnings although the dataset contains clinical notes, diagnoses and pediatric/neonatal records.",
         "Sensitive content not described.", ALWAYS, absent=["sensitive_elements", "content_warnings"]),
    item("E9.5", "Ethical Review and Social Impact Analysis", 0,
         "No ethical_reviews or future_use_impacts; data_governance.description mentions planned ethics focus groups and evaluation of community perspectives without results or impact analysis.",
         "No ethics review documentation or social impact analysis.", ALWAYS,
         absent=["ethical_reviews", "future_use_impacts"], considered=["data_governance.description"]),
], 5))

E.append(("Cross-Platform and Community Integration",
          "Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain.", [
    item("E10.1", "Dataset Published on a Recognized Platform", 0,
         "No publisher; data are said to be in an unnamed cloud enclave.", "No named hosting platform.", unk("shared_dataset"),
         absent=["publisher"], considered=["distribution_formats"]),
    item("E10.2", "Citation and DOI for Cross-referencing", 0,
         "Neither citation nor doi present.", "No citation guidance or DOI.", unk("shared_dataset"),
         absent=["citation", "doi"]),
    item("E10.3", "Community Standards or Schema Conformance", 1,
         "conforms_to_standard: OMOP_CDM, DICOM, WFDB (community standards).",
         "Community standards named.", unk("shared_dataset"),
         cited=[("/conforms_to_standard/2", "WFDB")], absent=["conforms_to"]),
    item("E10.4", "Outreach Materials and Documentation Links", 1,
         "page https://chorus4ai.org/; existing_uses describes the AIM-AHEAD Bridge2AI for Clinical Care Training Program and hands-on training opportunities.",
         "Landing page and training outreach present; no linked tutorials or documentation (external_resources absent).", unk("shared_dataset"),
         cited=[("page", "https://chorus4ai.org/"), ("/existing_uses/1/name", "AIM-AHEAD Bridge2AI for Clinical Care Training Program")],
         absent=["external_resources"]),
    item("E10.5", "Related Datasets with Typed Relationships", 0,
         "No related_datasets.", "No typed relationships.", unk("shared_dataset"), absent=["related_datasets"]),
], 5))

issues = [
    dict(type="correctness", category="persistent_identifier", severity="medium", score_effect="lowered",
         item_ids=["E1.1", "E10.2"],
         description="id is the project website root (identical to page) rather than a persistent dataset identifier, and no DOI or citation is provided.",
         fields_involved=["id", "page", "doi", "citation"],
         recommendation="Register a DOI or other persistent identifier for the released dataset and add a recommended citation."),
    dict(type="consistency", category="consent_ethics", severity="high", score_effect="lowered",
         item_ids=["E4.1", "E4.4", "E9.5"],
         description="Retrospective multi-hospital patient data (EHR, clinical notes, imaging) are described, but no human_subject_research, ethics review, consent or waiver is documented.",
         fields_involved=["human_subject_research", "ethical_reviews", "informed_consent", "collection_mechanisms"],
         recommendation="Document IRB/ethics oversight and the consent basis or waiver for retrospective use."),
    dict(type="completeness", category="privacy_regulatory", severity="high", score_effect="lowered",
         item_ids=["E2.2", "E4.2", "E4.3"],
         description="Privacy documentation consists of a planned approach and in-process imaging de-identification; no de-identification method, re-identification risk assessment, HIPAA status or confidentiality classification.",
         fields_involved=["participant_privacy", "is_deidentified", "regulatory_restrictions"],
         recommendation="State the de-identification standard applied to each modality, the re-identification risk assessment, and the regulatory framework and confidentiality level."),
    dict(type="consistency", category="consent_ethics", severity="medium", score_effect="lowered",
         item_ids=["E4.5"],
         description="The description includes PICU and NICU admissions (children and neonates), but at_risk_populations is absent.",
         fields_involved=["description", "at_risk_populations"],
         recommendation="Document pediatric/neonatal inclusion and the protections applied."),
    dict(type="completeness", category="license_use_terms", severity="high", score_effect="lowered",
         item_ids=["E3.1", "E3.5"],
         description="No dataset licence is named (the record itself notes none is stated) and no intended/prohibited use guidance is given; only an unspecified licensing agreement for the training program.",
         fields_involved=["license_and_use_terms", "intended_uses", "prohibited_uses"],
         recommendation="Name the data use agreement or licence and state permitted and prohibited uses."),
    dict(type="semantic_understanding", category="format_access", severity="medium", score_effect="lowered",
         item_ids=["E2.3", "E2.4", "E10.1"],
         description="distribution_formats names an access environment ('Cloud enclave') rather than file formats; no platform URL or named host/publisher is given.",
         fields_involved=["distribution_formats", "download_url", "publisher"],
         recommendation="Name the enclave/platform and its URL, and list delivered file formats and media types."),
    dict(type="completeness", category="temporal_version", severity="medium", score_effect="lowered",
         item_ids=["E6.1", "E6.2", "E6.3", "E6.4"],
         description="A 'current released dataset' is distinguished from an anticipated final dataset, but no version number, version access, change log or update schedule is given.",
         fields_involved=["version", "version_access", "errata", "updates"],
         recommendation="Assign release versions and document changes between them and the update cadence."),
    dict(type="completeness", category="variables_metadata", severity="medium", score_effect="lowered",
         item_ids=["E3.4", "E5.3"],
         description="No variable-level metadata, tabular flag or split/subpopulation flags; only a planned holdout split.",
         fields_involved=["variables", "is_tabular", "splits", "subsets"],
         recommendation="Reference the OMOP tables/fields delivered and document split roles."),
    dict(type="completeness", category="bias_quality", severity="medium", score_effect="lowered",
         item_ids=["E5.1", "E5.5", "E9.1", "E9.2", "E9.3", "E9.4"],
         description="No cohort demographics, limitations, biases, anomalies, missing-data or sensitive-content documentation for a multi-site clinical dataset that includes clinical notes.",
         fields_involved=["subpopulations", "known_limitations", "known_biases", "anomalies", "missing_data_documentation", "sensitive_elements"],
         recommendation="Add cohort characteristics, known limitations (e.g., incomplete imaging/EEG coverage), site and representativeness biases, and missing-data patterns."),
    dict(type="completeness", category="processing_provenance", severity="low", score_effect="lowered",
         item_ids=["E1.5", "E2.5", "E8.2", "E8.5", "E10.5"],
         description="Source documents (webinar, grant abstract, GitHub organization) are cited in prose without linked external_resources; no related datasets, acquisition methods or imputation statement.",
         fields_involved=["external_resources", "related_datasets", "acquisition_methods", "imputation_protocols"],
         recommendation="Link the source documents and SOP repositories, and describe acquisition and imputation."),
    dict(type="correctness", category="other", severity="low", score_effect="noted_only", item_ids=[],
         description="notes gives the contact email domain 'mgh.havard.edu' (likely a typo for harvard); the record flags it as reproduced from the website.",
         fields_involved=["notes", "source_caveats"],
         recommendation="Verify the contact address against the source."),
]

total = sum(s["score"] for _, _, subs, _ in E for s in subs)
elements = []
for i, (name, desc, subs, mx) in enumerate(E, 1):
    elements.append(dict(id=i, name=name, description=desc, sub_elements=subs,
                         element_score=sum(s["score"] for s in subs), element_max=mx))

ctx = normalize_context({})
doc = {
    "rubric": "rubric10-semantic",
    "version": "3.0",
    "d4d_file": INPUT,
    "project": "CHORUS",
    "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {
        "name": "claude-opus-5-5",
        "evaluator_model": "claude-opus-5-5",
        "temperature": None,
        "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
        "evaluation_type": "semantic_llm_judge",
    },
    "overall_score": {
        "total_points": total, "max_points": 50, "excluded_max_points": 0, "adjusted_max_points": 50,
        "normalized_percentage": round(total / 50 * 100, 1), "fixed_percentage": round(total / 50 * 100, 1),
        "sub_elements_not_applicable": 0, "excluded_item_ids": [],
    },
    "elements": elements,
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "Counts are reconciled with explicit units: 50,000 released admissions vs. 'over 45K' (earlier lower bound) vs. 100,000 targets, with images vs. admissions kept separate.",
            "Planned activities (sampling, labeling, holdout split, re-identification limitation) are explicitly marked as plans rather than performed steps.",
            "Funding is internally consistent: grant OT2OD032701 matches the funder description and the PI listed among creators; award dates (2022-09-01 to 2026-11-30) are consistent with the September 2025 webinar.",
            "Modality-level standards (OMOP CDM, DICOM, WFDB, EDF+) are attached to the corresponding subsets.",
        ],
        "consistency_checks": {"passed": 4, "failed": 2, "warnings": 1},
        "correctness_validations": {
            "doi_format": "not_present",
            "grant_number_format": "valid_nih",
            "rrid_format": "not_present",
            "url_validity": "all_valid",
        },
    },
    "applicability_context": ctx,
    "evaluation_scope": {
        "policy": "single_dataset",
        "units": [{"path": "#", "id": "https://chorus4ai.org/"}],
        "collection_metadata_inherited": False,
    },
    "metadata": {
        "instrument_sha256": sha(".claude/agents/d4d-rubric10-semantic.md"),
        "evidence_authority_sha256": sha("data/rubric/semantic_evidence_authority_v3.json"),
        "rubric_sha256": sha("data/rubric/rubric10.txt"),
        "input_sha256": sha(INPUT),
        "context_sha256": context_digest(ctx),
    },
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(OUT, total)
