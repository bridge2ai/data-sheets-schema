#!/usr/bin/env python3
"""Serialize one rubric10-semantic v3 evaluation (manual LLM judgements).

Purpose: write the evaluator's own judgements for VOICE_PEDIATRIC (method
claudecode_agent, label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1)
as the instrument's JSON. Scores below are the evaluator's judgements; this
script only serializes them and computes digests and totals.
Inputs: the D4D record, the agent definition, rubric10.txt, the evidence authority.
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/
        VOICE_PEDIATRIC_2026-11-22b_rep1_evaluation.json
Date: 2026-11-22. No caller applicability context (empty context).
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest  # noqa: E402

D4D = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/VOICE_PEDIATRIC_d4d.yaml"
OUT = "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/VOICE_PEDIATRIC_2026-11-22b_rep1_evaluation.json"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


ALWAYS = ("applicable", "This item applies to every dataset")


def unk(pred):
    return ("unknown", f"{pred}: not declared; retained in the denominator")


ANY_HR = ("unknown", "any: human_subjects: not declared; regulated_access: not declared; retained in the denominator")


def item(iid, name, score, evidence, note, app, cited=(), absent=(), counts=(), considered=(), nir=None):
    status, app_ev = app
    row = {
        "path": "#", "score": score, "evidence": evidence,
        "cited": [dict(path=c[0], quote=c[1]) if len(c) > 1 else {"path": c[0]} for c in cited],
        "absent": [{"path": a} for a in absent],
        "counts": [{"path": c[0], "claimed": c[1]} for c in counts],
        "considered": list(considered),
    }
    d = {"name": name, "score": score, "evidence": evidence, "quality_note": note,
         "applicable": True, "applicability_status": status, "applicability_evidence": app_ev,
         "unit_scores": [row], "item_id": iid}
    if nir:
        d["no_issue_reason"] = nir
    return d


E = []

E.append(("Dataset Discovery and Identification",
          "Can a user or system discover and uniquely identify this dataset?", [
    item("E1.1", "Persistent Identifier (DOI, RRID, or URI)", 1,
         "doi: 10.13026/h995-bt35 (version DOI); id: doi:10.13026/mf9s-5r03 (latest-version DOI). Both use the PhysioNet prefix 10.13026.",
         "Valid DOI format with a plausible PhysioNet registrar prefix; version and latest-version DOIs are distinguished consistently in version_access.",
         ALWAYS, cited=[("doi", "10.13026/h995-bt35"), ("id", "doi:10.13026/mf9s-5r03")]),
    item("E1.2", "Dataset Title and Description Completeness", 1,
         "title 'Bridge2AI-Voice Pediatric Dataset'; description (>600 chars) gives counts, ages, folder organisation and that raw audio is excluded.",
         "Specific and actionable description of content, scope and what is not included.",
         ALWAYS, cited=[("title", "Bridge2AI-Voice Pediatric Dataset"),
                        ("description", "contains derived audio features for 23,533 recordings collected from 300 participants aged 2-18")]),
    item("E1.3", "Keywords or Tags for Searchability", 1,
         "keywords: health, pediatric, biomarkers, bridge2ai, voice (5).",
         "Meets the >=5 threshold and covers domain and population; no method terms (e.g. acoustic features, spectrogram) are included, so searchability is modest.",
         ALWAYS, cited=[("/keywords/1", "pediatric")], counts=[("keywords", 5)]),
    item("E1.4", "Landing Page and Resources (page, hierarchical resources)", 1,
         "page: https://physionet.org/content/b2ai-voice-pediatric/1.1.0/ ; file_collections give a features/phenotype/metadata hierarchy with per-file resources.",
         "Landing page plus a hierarchical file structure.",
         ALWAYS, cited=[("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/"), ("file_collections",)],
         counts=[("file_collections", 3)]),
    item("E1.5", "Hierarchical Structure (parent datasets, relationships)", 0,
         "No parent_datasets or related_datasets. source_caveats explains that no typed relationship to the separate adult dataset was recorded.",
         "No dataset-level relationships are recorded; the raw-audio Synapse resource is listed only as an external resource.",
         ALWAYS, absent=["parent_datasets", "related_datasets"], considered=["source_caveats", "external_resources"]),
]))

E.append(("Dataset Access and Retrieval",
          "Can the dataset and its associated resources be located, accessed, and downloaded?", [
    item("E2.1", "Access Policy and IP Restrictions Defined", 1,
         "license_and_use_terms.license_terms: only credentialed users who sign the DUA (Bridge2AI Voice Registered Access Agreement) can access files; file license Bridge2AI Voice Registered Access License.",
         "Clear access policy and licence; ip_restrictions not populated, but the access policy is explicit.",
         ALWAYS, cited=[("license_and_use_terms.license_terms", "only credentialed users who sign the data use agreement (Bridge2AI Voice Registered Access Agreement) can access the files")],
         considered=["license"]),
    item("E2.2", "Regulatory Compliance and Confidentiality Classification", 0,
         "No regulatory_restrictions (confidentiality level, HIPAA/PHIPA or other compliance) and no data_governance block. A DACO contact appears only for raw audio on Synapse.",
         "For a pediatric clinical voice dataset collected in Canada, no regulatory framework or confidentiality classification is stated.",
         unk("regulated_access"), absent=["regulatory_restrictions", "data_governance"],
         considered=["external_resources", "license_and_use_terms"]),
    item("E2.3", "Download URL or Platform Link Available", 0,
         "download_url is absent. Only the landing page and the access policy are given; no direct file or download link for this release.",
         "The landing page is credited under E1.4/E10.4; no download or file-access URL is recorded.",
         ALWAYS, absent=["download_url"], considered=["page", "license_and_use_terms"]),
    item("E2.4", "Distribution Formats and File Types Specified", 1,
         "file_collections resources: static_features.tsv and audio_quality_metrics.tsv with format TSV; feature files described as Parquet; JSON data dictionaries.",
         "Formats are specific (Parquet, TSV, JSON). No media_type values and no format field on the Parquet resources.",
         ALWAYS, cited=[("/file_collections/0/resources/9/format", "TSV"),
                        ("/file_collections/0/description", "Binary files are made available as Parquet")],
         absent=["distribution_formats"]),
    item("E2.5", "Related Datasets and External Resources Linked", 1,
         "external_resources: raw pediatric audio on Synapse (syn73617068) with access restrictions, and the project website.",
         "External resources are linked with their purpose; related_datasets is empty.",
         ALWAYS, cited=[("/external_resources/0/external_resources/0", "https://www.synapse.org/Synapse:syn73617068")],
         absent=["related_datasets"]),
]))

E.append(("Data Reuse and Interoperability",
          "Is sufficient information provided to reuse and integrate the dataset with others?", [
    item("E3.1", "License Terms Allow Reuse", 1,
         "Bridge2AI Voice Registered Access License; reuse permitted for credentialed users who sign the DUA.",
         "A named restrictive licence with stated conditions for reuse; specific permitted/forbidden reuse terms of the DUA are not summarised.",
         unk("shared_dataset"), cited=[("license", "Bridge2AI Voice Registered Access License")],
         considered=["license_and_use_terms"]),
    item("E3.2", "Data Formats Are Standardized (encoding, format)", 1,
         "Parquet and TSV data files with JSON data dictionaries sharing the file stem.",
         "Standard open formats; character encoding is not stated.",
         unk("shared_dataset"), cited=[("/file_collections/0/resources/10/format", "TSV"),
                                       ("/file_collections/0/description", "an open-source column-oriented data file format")],
         absent=["distribution_formats"]),
    item("E3.3", "Schema or Ontology Conformance Stated", 0,
         "conforms_to and conforms_to_schema are absent. BIDS v1.9.0 appears only in a preprocessing step about the raw ReproSchema-UI data.",
         "No conformance statement for the released files.",
         unk("shared_dataset"), absent=["conforms_to", "conforms_to_schema"], considered=["preprocessing_strategies"]),
    item("E3.4", "Variable Metadata with Identifiers Defined", 1,
         "variables: participant_id and session_id (is_identifier: true), task_name, n_frames, each described.",
         "Identifier variables are defined; coverage is limited to the common Parquet columns (phenotype and static-feature columns are left to external data dictionaries).",
         unk("shared_dataset"), cited=[("/variables/0/is_identifier",), ("/variables/0/variable_name", "participant_id")],
         counts=[("variables", 4)]),
    item("E3.5", "Use Guidance Provided (intended, prohibited uses)", 0,
         "intended_uses lists three brief uses (developmental norms, early-screening tools, clinical insight). prohibited_uses and discouraged_uses are absent.",
         "Only generic intended uses; no prohibited or discouraged uses for a pediatric voice dataset (e.g. re-identification, speaker identification).",
         ALWAYS, cited=[("/intended_uses/1/description", "intended to create AI-driven tools for early screening")],
         absent=["prohibited_uses", "discouraged_uses"], counts=[("intended_uses", 3)]),
]))

E.append(("Ethical Use and Privacy Safeguards",
          "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context?", [
    item("E4.1", "IRB or Ethics Review and Data Protection Impact", 1,
         "ethical_reviews: data collection and sharing approved by the Research Ethics Board at the Hospital for Sick Children; human_subject_research.ethics_review_board matches.",
         "Named ethics board and scope (collection and sharing). No data protection impact assessment.",
         ANY_HR, cited=[("/ethical_reviews/0/review_details", "Data collection and sharing was approved by the Research Ethics Board at the Hospital for Sick Children."),
                        ("human_subject_research.ethics_review_board", "Research Ethics Board at the Hospital for Sick Children")],
         absent=["data_protection_impacts"]),
    item("E4.2", "Deidentification Method Described", 0,
         "is_deidentified is absent. Privacy is handled by withholding raw audio and manually checking free speech for PII, but no deidentification method for phenotype/demographic data is stated.",
         "Human-subjects data with detailed demographic and clinical questionnaires, but no deidentification method.",
         ANY_HR, absent=["is_deidentified"], considered=["participant_privacy", "cleaning_strategies"]),
    item("E4.3", "Privacy Protections and Re-identification Risk Assessment", 1,
         "participant_privacy: release contains derived features and no raw audio; raw audio disseminated through controlled access only. Cleaning removed features for sensitive records and manually checked free speech for unconsented speakers and PII.",
         "Concrete privacy protections and mitigations; no explicit reidentification_risk assessment (the description only notes the publishers consider the data low risk).",
         unk("human_subjects"), cited=[("/participant_privacy/0/privacy_techniques", "raw audio data is disseminated through controlled access only, to protect participants' privacy")],
         absent=["participant_privacy.reidentification_risk"], considered=["cleaning_strategies", "description"]),
    item("E4.4", "Informed Consent Obtained from Participants", 1,
         "informed_consent: consent_obtained true; parental or participant consent obtained prior to data collection and data sharing; assent procedures in at_risk_populations.",
         "Consent type and timing given, covering sharing; no withdrawal mechanism.",
         unk("human_subjects"), cited=[("/informed_consent/0/description", "parental or participant consent was obtained prior to data collection and data sharing"),
                                       ("/informed_consent/0/consent_obtained",)],
         considered=["at_risk_populations"]),
    item("E4.5", "Vulnerable Populations and Compensation Documented", 0,
         "at_risk_populations documents children, guardian consent and assent, but every protection is quoted from the parent USF protocol, which source_caveats says SickKids did not follow (separate REB). participant_compensation is absent; source_caveats says pediatric compensation is not stated.",
         "Compensation is undocumented, and the pediatric protections are attributed to a protocol of uncertain applicability to this cohort.",
         unk("human_subjects"), cited=[("at_risk_populations.at_risk_groups_included",),
                                       ("at_risk_populations.assent_procedures", "children will provide verbal assent where appropriate")],
         absent=["participant_compensation"], considered=["source_caveats", "human_subject_research"]),
]))

E.append(("Data Composition and Structure",
          "Can the dataset's structure, modality, and population be understood from metadata?", [
    item("E5.1", "Cohort or Subpopulations Characteristics Described", 1,
         "subpopulations: age groups Peds 2-4, 4-6, 6-10, 10+; sampling_strategies give inclusion (2-18, English proficiency) and exclusion (over 18, non-verbal) criteria, patients and healthy volunteers at SickKids.",
         "Inclusion/exclusion and age structure are clear; no sex, diagnosis or per-group counts.",
         ALWAYS, cited=[("/subpopulations/0/description", "Peds 2-4, Peds 4-6, Peds 6-10 and Peds 10+"),
                        ("/sampling_strategies/0/strategies", "Inclusion criteria were 2 to 18 years of age and English proficiency")]),
    item("E5.2", "Number of Instances or Samples Reported", 1,
         "instances: 23533 recordings; 300 participants. Per-file n is also given (23533 or 23532).",
         "Specific counts consistent with the description and per-file counts.",
         ALWAYS, cited=[("/instances/0/counts",), ("/instances/1/counts",)], counts=[("instances", 2)]),
    item("E5.3", "Variable-Level Metadata, Tabular Flag, and Data Splits", 0,
         "Four variables are described, but is_tabular and subsets (split/subpopulation flags) are absent, and phenotype columns are not described.",
         "Partial variable metadata with no tabular flag or subset roles.",
         ALWAYS, cited=[("/variables/2/variable_name", "task_name")], absent=["is_tabular", "subsets"],
         counts=[("variables", 4)]),
    item("E5.4", "Data Topics or Conditions Represented", 0,
         "instances name only recordings and participants. No diagnoses, conditions or phenotypes in the cohort are listed; the description mentions 'clinical' data and sampling includes 'Patients' without saying which conditions.",
         "A pediatric patient cohort is described without the conditions represented.",
         ALWAYS, cited=[("/instances/0/instance_type", "recording with derived audio features")],
         considered=["description", "sampling_strategies", "subpopulations"]),
    item("E5.5", "Data Quality, Anomalies, and Missing Data Documented", 1,
         "missing_data_documentation: some files could not generate certain features and are not bundled (matches n=23532 vs 23533); sampling_strategies describe recruitment; audio_quality_metrics.tsv released.",
         "Missing-data cause documented and consistent with per-file counts; no anomalies section.",
         ALWAYS, cited=[("/missing_data_documentation/0/missing_data_causes", "could not generate certain features and so are not included in the bundled data")],
         absent=["anomalies"], considered=["sampling_strategies"]),
]))

E.append(("Data Provenance and Version Tracking",
          "Can a user determine dataset versions, update history, and provenance?", [
    item("E6.1", "Dataset Version Number Provided", 1, "version: 1.1.0", "Semantic version given and consistent with page URL and citation.",
         unk("shared_dataset"), cited=[("version", "1.1.0")]),
    item("E6.2", "Version Access Methods Documented", 1,
         "version_access: latest_version_doi, versions_available 1.0.0 (Dec. 17, 2025) and 1.1.0 (May 1, 2026), version DOI vs latest-version DOI explained.",
         "Readers can locate specific and latest versions.",
         unk("shared_dataset"), cited=[("version_access.latest_version_doi", "doi:10.13026/mf9s-5r03"), ("/version_access/versions_available/0", "1.0.0 (Dec. 17, 2025)")]),
    item("E6.3", "Change Descriptions and Errata Provided", 1,
         "version_access.version_details describes v1.1 changes (no new participants; free speech features after manual PII check; audio quality metrics and per-recording metadata added); cleaning_strategies note features removed in v1.1.",
         "Substantive change description; no errata or updates block.",
         unk("shared_dataset"), cited=[("version_access.version_details", "Version 1.1 is a minor update with no new participants")],
         absent=["errata", "updates"]),
    item("E6.4", "Update Schedule or Frequency Indicated", 0,
         "updates is absent; no maintenance plan or update frequency.",
         "Only past release dates are known.", unk("shared_dataset"), absent=["updates"],
         considered=["distribution_dates", "version_access"]),
    item("E6.5", "Provenance, Source Derivation, and Raw Data Sources", 1,
         "Derivation from raw audio waveforms into Parquet features (b2aiprep), merging of source data into phenotype files, and raw audio location on Synapse are documented; release notes in version_access.",
         "Derivation is clear; was_derived_from and raw_data_sources are not populated as structured slots.",
         unk("shared_dataset"), cited=[("/preprocessing_strategies/1/preprocessing_details", "Raw audio waveforms were preprocessed into Parquet feature files"),
                                       ("/external_resources/0/description", "raw audio for the Bridge2AI Voice pediatric cohort is accessed via Synapse")],
         absent=["was_derived_from", "raw_data_sources", "updates", "notes"]),
]))

E.append(("Scientific Motivation and Funding Transparency",
          "Does the metadata clearly state why the dataset exists and who funded it?", [
    item("E7.1", "Motivation or Purpose for Dataset Creation", 1,
         "purposes: ethically sourced flagship dataset for AI research on voice as a biomarker; addressing_gaps: lack of open pediatric voice datasets.",
         "Purpose and research gap are specific to pediatric voice.",
         ALWAYS, cited=[("/purposes/0/response", "create an ethically sourced flagship dataset"),
                        ("/addressing_gaps/0/name", "Lack of open pediatric voice datasets for machine learning")]),
    item("E7.2", "Primary Research Objectives or Tasks", 0,
         "tasks is absent; intended_uses are generic statements (developmental norms, early screening, clinical insight) without specific research questions or ML tasks.",
         "No specific tasks or analyses.", ALWAYS, absent=["tasks"], considered=["intended_uses", "purposes"]),
    item("E7.3", "Funding Sources and Mechanisms Listed", 1,
         "funders: NIH with grant 'Bridge2AI: Voice as a Biomarker of Health ...'.",
         "Named funder and award; mechanism (OT2 other transaction, supplement) is recoverable from the number.",
         ALWAYS, cited=[("/funders/0/grantor", "NIH"), ("/funders/0/grants/0/name", "Voice as a Biomarker of Health")]),
    item("E7.4", "Grant IDs or Award Numbers Present", 1,
         "grant_number: 3OT2OD032720-01S1, consistent with funders.description.",
         "Matches the NIH pattern (type 3 supplement, OT2, OD institute, serial 032720, -01S1). source_caveats discloses that other bundle sources cite -01S3 and a malformed -01S2 variant.",
         ALWAYS, cited=[("/funders/0/grants/0/grant_number", "3OT2OD032720-01S1"), ("/funders/0/description", "3OT2OD032720-01S1")]),
    item("E7.5", "Creators and Acknowledgements Documented", 1,
         "creators: full author list with affiliations for key investigators, principal investigators identified, and the Bridge2AI Voice consortium.",
         "Extensive attribution; most contributors lack affiliations.",
         ALWAYS, cited=[("/creators/0/name", "Yael Bensoussan")], considered=["funders"]),
]))

E.append(("Technical Transparency (Data Collection and Processing)",
          "Can data collection and processing steps be replicated or understood?", [
    item("E8.1", "Collection Mechanisms and Settings Described", 1,
         "collection_mechanisms: reproschema-ui on tablets, headset or built-in tablet microphone, single session, parents completing surveys on a separate tablet.",
         "Procedures and setting are specific; collection timeframe is not given.",
         unk("data_collection"), cited=[("/collection_mechanisms/0/mechanism_details", "All data were collected through customized software (reproschema-ui) on tablets")]),
    item("E8.2", "Data Acquisition Methods Listed", 1,
         "acquisition_methods: standardized age-appropriate protocol with demographic, voice/speech and medical-history questionnaires; devices (headset, tablet microphone) in collection_mechanisms.",
         "Methods and instruments are named.", unk("data_collection"),
         cited=[("/acquisition_methods/0/acquisition_details", "a standardized age-appropriate protocol was adopted")],
         absent=["raw_data_sources"]),
    item("E8.3", "Preprocessing, Cleaning, Labeling, and Annotation Quality", 1,
         "preprocessing_strategies (TSV export, feature derivation with parameters, ReproSchema-UI to REDCap to BIDS); cleaning_strategies (removal of sensitive-record features, manual PII check).",
         "Detailed processing and cleaning; no labeling, annotation or imputation documentation.",
         unk("data_processing"), cited=[("/cleaning_strategies/1/cleaning_details", "manually checked for presence of unconsented speakers and PII")],
         considered=["preprocessing_strategies"], absent=["labeling_strategies", "imputation_protocols"]),
    item("E8.4", "Software and Tools Documented", 1,
         "preprocessing_strategies[1].used_software: b2aiprep 3.0.0 (Apache-2.0, GitHub repo); openSMILE, Praat, parselmouth, torchaudio named as producing the released features.",
         "Software that transformed the released data is named with version and repository (slot preprocessing_strategies.used_software).",
         unk("processing_software"), cited=[("/preprocessing_strategies/1/used_software/0/name", "Bridge2AI Data Processing Library (b2aiprep)"),
                                            ("/preprocessing_strategies/1/used_software/0/version", "3.0.0")]),
    item("E8.5", "External Standards, Resources, and Imputation Protocols", 0,
         "external_resources link only the Synapse raw-audio location and the project website; no papers or standards documents; conforms_to and imputation_protocols absent; imputation neither described nor ruled out.",
         "No external standards documentation and no imputation statement.",
         ALWAYS, absent=["conforms_to", "imputation_protocols"], considered=["external_resources", "missing_data_documentation"]),
]))

E.append(("Dataset Evaluation and Limitations Disclosure",
          "Does the metadata communicate known risks, biases, or dataset limitations?", [
    item("E9.1", "Known Limitations Documented", 0,
         "known_limitations is absent. source_caveats concerns record construction, not dataset limitations.",
         "Obvious limitations (single site, English-only, mixed microphones, no raw audio) are not stated as limitations.",
         ALWAYS, absent=["known_limitations"], considered=["source_caveats", "collection_mechanisms"]),
    item("E9.2", "Biases Categorized Using Standard Taxonomy (RAI-aligned)", 0,
         "known_biases and future_use_impacts absent.", "No bias categorisation.",
         ALWAYS, absent=["known_biases", "future_use_impacts"]),
    item("E9.3", "Data Anomalies and Quality Issues Noted", 0,
         "anomalies absent; only a missing-feature note and an audio_quality_metrics file without characterised quality issues.",
         "Quality issues and outliers are not described.",
         ALWAYS, absent=["anomalies"], considered=["missing_data_documentation", "file_collections"]),
    item("E9.4", "Sensitive Content and Warnings Provided", 0,
         "sensitive_elements and content_warnings absent; cleaning mentions 'sensitive records' without describing them.",
         "Pediatric medical-history and voice data are sensitive but undeclared.",
         ALWAYS, absent=["sensitive_elements", "content_warnings"], considered=["cleaning_strategies"]),
    item("E9.5", "Ethical Review and Social Impact Analysis", 0,
         "ethical_reviews documents the SickKids REB approval, but future_use_impacts, social-impact analysis and conflicts of interest are absent.",
         "Ethics review only; no downstream impact analysis.",
         ALWAYS, cited=[("/ethical_reviews/0/reviewing_organization", "Research Ethics Board at the Hospital for Sick Children")],
         absent=["future_use_impacts"]),
]))

E.append(("Cross-Platform and Community Integration",
          "Does the dataset connect to relevant repositories, communities and standards?", [
    item("E10.1", "Dataset Published on a Recognized Platform", 1,
         "publisher field absent, but description, page and citation all state PhysioNet.",
         "Recognized platform is clearly documented, though not in the structured publisher slot.",
         unk("shared_dataset"), cited=[("description", "published on PhysioNet"), ("page", "physionet.org")],
         absent=["publisher"]),
    item("E10.2", "Citation and DOI for Cross-referencing", 1,
         "citation with authors, year, version, PhysioNet, RRID:SCR_007345 and https://doi.org/10.13026/h995-bt35; doi field matches.",
         "Complete citation consistent with the DOI.",
         unk("shared_dataset"), cited=[("citation", "https://doi.org/10.13026/h995-bt35"), ("doi", "10.13026/h995-bt35")]),
    item("E10.3", "Community Standards or Schema Conformance", 0,
         "conforms_to absent.", "No community standard declared for the release.",
         unk("shared_dataset"), absent=["conforms_to"], considered=["preprocessing_strategies"]),
    item("E10.4", "Outreach Materials and Documentation Links", 1,
         "page (PhysioNet landing page) and external_resources project website https://b2ai-voice.org/.",
         "Landing page and project website; no tutorials or webinars.",
         unk("shared_dataset"), cited=[("/external_resources/1/external_resources/0", "https://b2ai-voice.org/"), ("page",)]),
    item("E10.5", "Related Datasets with Typed Relationships", 0,
         "related_datasets absent; source_caveats states no typed relationship to the adult dataset was recorded.",
         "No typed relationships.", unk("shared_dataset"), absent=["related_datasets"], considered=["source_caveats"]),
]))

ISSUES = [
    dict(item_ids=["E4.2"], score_effect="lowered", category="privacy_regulatory", type="consistency", severity="high",
         description="human_subject_research.involves_human_subjects is true and detailed demographic/clinical questionnaires are released, but is_deidentified (method, identifiers removed) is absent.",
         fields_involved=["human_subject_research", "is_deidentified", "participant_privacy"],
         recommendation="State the deidentification method and identifiers removed for phenotype and metadata files."),
    dict(item_ids=["E2.2"], score_effect="lowered", category="privacy_regulatory", type="completeness", severity="medium",
         description="No regulatory_restrictions or data_governance: no confidentiality level, applicable privacy law (e.g. PHIPA/PIPEDA for Ontario data) or governance contact for the PhysioNet release.",
         fields_involved=["regulatory_restrictions", "data_governance"],
         recommendation="Add confidentiality classification, applicable compliance frameworks and the governance committee contact."),
    dict(item_ids=["E4.5"], score_effect="lowered", category="consent_ethics", type="content_accuracy", severity="medium",
         description="at_risk_populations protections are quoted from the parent USF protocol, which source_caveats says SickKids did not follow (separate REB); participant_compensation is absent.",
         fields_involved=["at_risk_populations", "participant_compensation", "source_caveats"],
         recommendation="Document pediatric protections and compensation from the SickKids REB-approved protocol."),
    dict(item_ids=["E1.5", "E10.5"], score_effect="lowered", category="other", type="completeness", severity="medium",
         description="No parent_datasets or related_datasets; the companion adult dataset and the Synapse raw-audio collection are not linked with typed relationships.",
         fields_involved=["parent_datasets", "related_datasets", "external_resources"],
         recommendation="Record typed relationships where a source states them."),
    dict(item_ids=["E2.3"], score_effect="lowered", category="format_access", type="completeness", severity="low",
         description="download_url absent; only a landing page is recorded.",
         fields_involved=["download_url", "page"], recommendation="Add the PhysioNet files/download URL."),
    dict(item_ids=["E3.3", "E10.3", "E8.5"], score_effect="lowered", category="variables_metadata", type="completeness", severity="medium",
         description="No conforms_to/conforms_to_schema for the released files; no external standards or papers; imputation neither described nor ruled out.",
         fields_involved=["conforms_to", "conforms_to_schema", "imputation_protocols", "external_resources"],
         recommendation="Declare format/standard conformance and state whether imputation was used."),
    dict(item_ids=["E3.5", "E7.2"], score_effect="lowered", category="license_use_terms", type="completeness", severity="medium",
         description="No prohibited or discouraged uses and no tasks; intended uses are generic.",
         fields_involved=["prohibited_uses", "discouraged_uses", "tasks", "intended_uses"],
         recommendation="Document DUA prohibitions (e.g. re-identification) and concrete research/ML tasks."),
    dict(item_ids=["E5.3", "E5.4"], score_effect="lowered", category="variables_metadata", type="completeness", severity="medium",
         description="No is_tabular or subsets flags, phenotype variables undescribed, and the clinical conditions of the patient cohort are not listed.",
         fields_involved=["variables", "is_tabular", "subsets", "instances"],
         recommendation="Describe phenotype variables, tabular status and the conditions represented."),
    dict(item_ids=["E6.4"], score_effect="lowered", category="temporal_version", type="completeness", severity="low",
         description="No update schedule or maintenance plan.", fields_involved=["updates"],
         recommendation="State the expected update frequency or maintenance policy."),
    dict(item_ids=["E9.1", "E9.2", "E9.3", "E9.4", "E9.5"], score_effect="lowered", category="bias_quality", type="completeness", severity="high",
         description="Element 9 is unpopulated: no known_limitations, known_biases, anomalies, sensitive_elements/content_warnings or future_use_impacts, despite single-site English-only recruitment, mixed microphones and sensitive pediatric data.",
         fields_involved=["known_limitations", "known_biases", "anomalies", "sensitive_elements", "content_warnings", "future_use_impacts"],
         recommendation="Add limitations, categorised biases, data-quality anomalies, sensitivity declarations and a social-impact analysis."),
    dict(item_ids=[], score_effect="noted_only", category="source_conflict", type="correctness", severity="low",
         description="Grant number 3OT2OD032720-01S1 is well-formed for NIH, but source_caveats reports RePORTER describes -01S3 and project documentation cites a malformed 3Tf-OTOD03272001S2; the recorded number follows the release itself.",
         fields_involved=["funders", "source_caveats"],
         recommendation="Confirm the supplement suffix against NIH RePORTER."),
    dict(item_ids=[], score_effect="noted_only", category="privacy_regulatory", type="semantic_understanding", severity="low",
         description="Access terminology mixes 'credentialed access', 'registered access' and 'restricted-access'; participant_privacy has no explicit reidentification_risk assessment.",
         fields_involved=["description", "license_and_use_terms", "participant_privacy"],
         recommendation="Use one access tier term and add a reidentification risk statement."),
]

total = 0
elements = []
for i, (name, desc, subs) in enumerate(E, start=1):
    s = sum(x["score"] for x in subs)
    total += s
    elements.append({"id": i, "name": name, "description": desc, "sub_elements": subs,
                     "element_score": s, "element_max": 5})

ctx = {}
doc = {
    "rubric": "rubric10-semantic", "version": "3.0", "d4d_file": D4D,
    "project": "VOICE_PEDIATRIC", "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {"name": "claude-opus-5-5", "evaluator_model": "claude-opus-5-5", "temperature": None,
              "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
              "evaluation_type": "semantic_llm_judge"},
    "overall_score": {"total_points": total, "max_points": 50, "excluded_max_points": 0,
                      "adjusted_max_points": 50, "normalized_percentage": round(total / 50 * 100, 1),
                      "fixed_percentage": round(total / 50 * 100, 1), "sub_elements_not_applicable": 0,
                      "excluded_item_ids": []},
    "elements": elements,
    "semantic_analysis": {
        "issues_detected": ISSUES,
        "semantic_insights": [
            "Strong discovery, versioning, funding and processing documentation: PhysioNet DOIs, NIH award, b2aiprep 3.0.0 with feature parameters.",
            "Human-subjects logic: ethics review (SickKids REB) and consent are present; deidentification method is missing.",
            "Element 9 (limitations, biases, anomalies, sensitivity, social impact) is entirely unpopulated.",
            "source_caveats transparently records source conflicts (grant suffix, protocol applicability, name spellings).",
        ],
        "consistency_checks": {"passed": 5, "failed": 2, "warnings": 2},
        "correctness_validations": {
            "doi_format": "valid: 10.13026/h995-bt35 and 10.13026/mf9s-5r03 (PhysioNet prefix)",
            "grant_number_format": "valid NIH pattern: 3OT2OD032720-01S1 (suffix conflicts noted in source_caveats)",
            "rrid_format": "valid: RRID:SCR_007345 in citation (PhysioNet platform RRID)",
            "url_validity": "valid: physionet.org, synapse.org, b2ai-voice.org, github.com/sensein/b2aiprep",
        },
    },
    "applicability_context": ctx,
    "evaluation_scope": {"policy": "single_dataset", "units": [{"path": "#", "id": "doi:10.13026/mf9s-5r03"}],
                         "collection_metadata_inherited": False},
    "metadata": {
        "instrument_sha256": sha(".claude/agents/d4d-rubric10-semantic.md"),
        "evidence_authority_sha256": sha("data/rubric/semantic_evidence_authority_v3.json"),
        "rubric_sha256": sha("data/rubric/rubric10.txt"),
        "input_sha256": sha(D4D),
        "context_sha256": context_digest(ctx),
    },
}
out = ROOT / OUT
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(out, total)
