#!/usr/bin/env python3
"""Write the rubric10-semantic v3 (general context instrument) evaluation of one D4D record.

Purpose: serialize the evaluator's own judgements for
  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/VOICE_d4d.yaml
Inputs: that D4D record, .claude/agents/d4d-rubric10-semantic.md, data/rubric/rubric10.txt,
        data/rubric/semantic_evidence_authority_v3.json (hashed only); no caller context file
        (empty applicability_context).
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/VOICE_2026-11-22b_rep2_evaluation.json
Serves: caller-requested single-record evaluation (project VOICE, method claudecode_agent,
        label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2). Date: 2026-11-22.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import applicability, context_digest  # noqa: E402

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/VOICE_d4d.yaml"
OUT = "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/VOICE_2026-11-22b_rep2_evaluation.json"
AGENT = ".claude/agents/d4d-rubric10-semantic.md"
RUBRIC = "data/rubric/rubric10.txt"
AUTHORITY = "data/rubric/semantic_evidence_authority_v3.json"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


CONTEXT = {}
ANY_GOV = {"any": ["human_subjects", "regulated_access"]}
RULES = {
    "E2.2": "regulated_access",
    "E3.1": "shared_dataset", "E3.2": "shared_dataset", "E3.3": "shared_dataset", "E3.4": "shared_dataset",
    "E4.1": ANY_GOV, "E4.2": ANY_GOV,
    "E4.3": "human_subjects", "E4.4": "human_subjects", "E4.5": "human_subjects",
    "E6.1": "shared_dataset", "E6.2": "shared_dataset", "E6.3": "shared_dataset",
    "E6.4": "shared_dataset", "E6.5": "shared_dataset",
    "E8.1": "data_collection", "E8.2": "data_collection",
    "E8.3": "data_processing", "E8.4": "processing_software",
    "E10.1": "shared_dataset", "E10.2": "shared_dataset", "E10.3": "shared_dataset",
    "E10.4": "shared_dataset", "E10.5": "shared_dataset",
}


def C(path, quote=None):
    return {"path": path, "quote": quote} if quote else {"path": path}


def item(iid, name, score, evidence, quality, cited=(), absent=(), counts=(), considered=(), reason=None):
    a = applicability(RULES.get(iid), CONTEXT)
    row = {
        "path": "#", "score": score if a.applicable else None, "evidence": evidence,
        "cited": list(cited), "absent": [{"path": p} for p in absent],
        "counts": [{"path": p, "claimed": n} for p, n in counts], "considered": list(considered),
    }
    out = {
        "name": name, "score": score if a.applicable else None, "evidence": evidence,
        "quality_note": quality, "applicable": a.applicable, "applicability_status": a.status,
        "applicability_evidence": a.evidence, "unit_scores": [row], "item_id": iid,
    }
    if reason:
        out["no_issue_reason"] = reason
    return out


E = []

E.append(("Dataset Discovery and Identification",
          "Can a user or system discover and uniquely identify this dataset?", [
    item("E1.1", "Persistent Identifier (DOI, RRID, or URI)", 1,
         "doi: 10.13026/37yb-1t42 and id: doi:10.13026/37yb-1t42 (project-level DOI). Prefix 10.13026 is PhysioNet's registrar prefix, consistent with page https://physionet.org/content/b2ai-voice/.",
         "Valid DOI format with a plausible PhysioNet prefix; id and doi agree.",
         cited=[C("doi", "10.13026/37yb-1t42"), C("id", "doi:10.13026/37yb-1t42")],
         considered=["citation"]),
    item("E1.2", "Dataset Title and Description Completeness", 1,
         "title: 'Bridge2AI-Voice: An ethically-sourced, diverse voice dataset linked to health information'; description (>600 chars) states the release (3.1.0, May 1 2026), 833 participants, five North American sites, derived features only (no raw recordings), and 3.1.0 changes.",
         "Clear title and a specific, substantive description of content, scope and release.",
         cited=[C("title", "An ethically-sourced, diverse voice dataset linked to health information"),
                C("description", "contains data for 833 participants across five sites in North America")]),
    item("E1.3", "Keywords or Tags for Searchability", 0,
         "keywords lists only four terms: health, biomarkers, bridge2ai, voice. No method (e.g. acoustic features, speech), condition (voice/neurological/mood/respiratory disorders) or modality terms.",
         "Below the threshold of at least five keywords covering domain, methods and conditions.",
         cited=[C("keywords", "biomarkers")], counts=[("keywords", 4)]),
    item("E1.4", "Landing Page and Resources (page, hierarchical resources)", 1,
         "page: https://physionet.org/content/b2ai-voice/ (PhysioNet landing page). No hierarchical resources block, but file_collections give the release's file structure.",
         "Accessible, plausible landing page URL.",
         cited=[C("page", "https://physionet.org/content/b2ai-voice/")], absent=["resources"],
         considered=["file_collections"],
         reason="The landing page satisfies the item; the absent resources block is an alternative representation, so no issue is raised."),
    item("E1.5", "Hierarchical Structure (parent datasets, relationships)", 0,
         "Neither parent_datasets nor related_datasets is populated. source_caveats explains the deliberate omission: the Pediatric dataset is a separate PhysioNet project and no typed relation is stated.",
         "Omission is transparently explained but no hierarchical or related-dataset links are documented.",
         absent=["parent_datasets", "related_datasets"],
         cited=[C("source_caveats", "no related_datasets entry is recorded because no passage states a typed relation")]),
]))

E.append(("Dataset Access and Retrieval",
          "Can the dataset and its associated resources be located, accessed, and downloaded?", [
    item("E2.1", "Access Policy and IP Restrictions Defined", 1,
         "license_and_use_terms: 'Only credentialed users who sign the DUA can access the files'; Registered Access Agreement requiring respect for the Fort Lauderdale Agreement. ip_restrictions: IP/database rights may not restrict access; sale of data not permitted.",
         "Access policy and IP restrictions are explicit and actionable.",
         cited=[C("license_and_use_terms.description", "Only credentialed users who sign the DUA can access the files."),
                C("ip_restrictions.restrictions", "Sale of all or part of the Data on any media is not permitted."),
                C("license", "Bridge2AI Voice Registered Access License")]),
    item("E2.2", "Regulatory Compliance and Confidentiality Classification", 0,
         "regulatory_restrictions only carries other_compliance (Certificate of Confidentiality under the DTUA). data_governance names the Data Access Compliance Office (DACO) and its review process, but no committee_contact, no confidentiality_level and no hipaa_compliant status are recorded.",
         "Partial: a regulatory protection and a governance body are named, but the classification and the governance contact required by this item's scope are missing.",
         cited=[C("regulatory_restrictions.other_compliance", "covered by a Certificate of Confidentiality"),
                C("data_governance.committee_name", "Data Access Compliance Office (DACO)")],
         absent=["regulatory_restrictions.confidentiality_level", "regulatory_restrictions.hipaa_compliant",
                 "data_governance.committee_contact"],
         considered=["data_governance.access_review_process", "data_governance.description"]),
    item("E2.3", "Download URL or Platform Link Available", 1,
         "No download_url field, but page gives the PhysioNet platform link and license_and_use_terms gives the platform access route (credentialed users who sign the DUA); raw_sources.access_url gives the Synapse controlled-access link for raw audio.",
         "Platform link plus access instructions are present; a direct download URL field is absent.",
         cited=[C("page", "https://physionet.org/content/b2ai-voice/"),
                C("/raw_sources/0/access_url", "https://www.synapse.org/Synapse:syn72370534/")],
         absent=["download_url"], considered=["license_and_use_terms"]),
    item("E2.4", "Distribution Formats and File Types Specified", 1,
         "distribution_formats: Parquet and TSV with descriptions; file_collections resources give format TSV and media_type text/tab-separated-values for TSV files.",
         "Specific formats and MIME types are stated.",
         cited=[C("/distribution_formats/0/format", "Parquet"), C("/distribution_formats/1/format", "TSV"),
                C("/file_collections/0/resources/9/media_type", "text/tab-separated-values")],
         counts=[("distribution_formats", 2)]),
    item("E2.5", "Related Datasets and External Resources Linked", 1,
         "external_resources lists six resources: feasibility paper (doi:10.3389/fdgth.2025.1514971), REDCap data dictionary and protocols (GitHub, Zenodo), JAMA Otolaryngology viewpoint, Interspeech 2024 protocol paper, training site, and bridge2ai-docs. related_datasets is absent.",
         "External documentation is well linked; related datasets are not.",
         cited=[C("/external_resources/1/name", "Bridge2AI-Voice REDCap data dictionary and protocols")],
         counts=[("external_resources", 6)], absent=["related_datasets"],
         reason="External resources meet the item; the related_datasets gap is accounted for under the issue lowering E1.5 and E10.5."),
]))

E.append(("Data Reuse and Interoperability",
          "Is sufficient information provided to reuse and integrate the dataset with others?", [
    item("E3.1", "License Terms Allow Reuse", 1,
         "Bridge2AI Voice Registered Access Agreement: research use (commercial and non-commercial) by Authorized Researchers under a DUA, Fort Lauderdale Agreement terms.",
         "Not an open licence, but reuse permissions and conditions are clearly stated.",
         cited=[C("license_and_use_terms.description", "intended solely for commercial and non-commercial research purposes by Authorized Researchers"),
                C("license_and_use_terms.license_terms", "respect the Fort Lauderdale Agreement")],
         considered=["license"]),
    item("E3.2", "Data Formats Are Standardized (encoding, format)", 1,
         "Standard open formats: Parquet (column-oriented) and TSV with media types; JSON data dictionaries accompany files. No character encoding is stated.",
         "Standardized formats are clear; encoding is missing (noted).",
         cited=[C("/distribution_formats/0/description", "an open-source column-oriented data file format"),
                C("/file_collections/0/resources/10/format", "TSV")],
         absent=["file_collections.resources.encoding"], considered=["file_collections"]),
    item("E3.3", "Schema or Ontology Conformance Stated", 0,
         "No conforms_to or conforms_to_schema. raw_sources mentions BIDS v1.9.0 conversion for raw audio, which is not part of this release.",
         "No standard/schema conformance is declared for the released data.",
         absent=["conforms_to", "conforms_to_schema"],
         cited=[C("/raw_sources/0/raw_data_details", "Brain Imaging Data Structure v1.9.0")]),
    item("E3.4", "Variable Metadata with Identifiers Defined", 0,
         "No variables block. file_collections mention per-file JSON data dictionaries and parquet element structure, but no variable-level names, identifiers or descriptions are given in the record.",
         "Variable-level metadata is delegated to external dictionaries and not documented.",
         absent=["variables"], considered=["file_collections"]),
    item("E3.5", "Use Guidance Provided (intended, prohibited uses)", 1,
         "intended_uses (AI/ML research for healthcare, pretraining/fine-tuning/benchmarking/validation); four prohibited_uses (re-identification, harm/stigmatization, non-research uses, contacting subjects); discouraged_uses (hiring, insurance, surveillance).",
         "All three kinds of use guidance are present and specific.",
         cited=[C("/intended_uses/0/description", "the development of AI and machine-learning models for healthcare"),
                C("/prohibited_uses/0/description", "attempt to re-identify research participants"),
                C("/discouraged_uses/0/description", "hiring decisions, insurance premium adjustments")],
         counts=[("prohibited_uses", 4)]),
]))

E.append(("Ethical Use and Privacy Safeguards",
          "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.", [
    item("E4.1", "IRB or Ethics Review and Data Protection Impact", 1,
         "ethical_reviews: University of South Florida IRB approved data collection and sharing via the Single IRB process; human_subject_research.irb_approval agrees. involves_human_subjects: true.",
         "Ethics review is documented and consistent with the human-subjects flag.",
         cited=[C("/ethical_reviews/0/reviewing_organization", "University of South Florida Institutional Review Board"),
                C("human_subject_research.irb_approval", "approved by the USF Single IRB and subsite IRBs"),
                C("human_subject_research.involves_human_subjects")],
         absent=["data_protection_impacts"]),
    item("E4.2", "Deidentification Method Described", 1,
         "is_deidentified.method: only derived features released, raw audio removed, transcripts reviewed, free-speech spectrograms excluded, ethicist-identified sensitive fields removed; identifiers_removed: HIPAA Safe Harbor identifiers.",
         "Specific method and identifier list, appropriate to voice data.",
         cited=[C("is_deidentified.method", "Only derived audio features are released and all raw voice data was removed"),
                C("is_deidentified.identifiers_removed", "HIPAA Safe Harbor identifiers were removed.")],
         considered=["is_deidentified.deidentification_details"]),
    item("E4.3", "Privacy Protections and Re-identification Risk Assessment", 1,
         "participant_privacy: raw audio only under controlled access; reidentification_risk states the dataset does not achieve k-anonymization (k>=2) and that a voice is always potentially recognizable; secure https transfer to HIPAA-compliant storage.",
         "Explicit, candid re-identification risk assessment with mitigations.",
         cited=[C("/participant_privacy/0/reidentification_risk", "does not achieve k-anonymization (k>=2)"),
                C("/participant_privacy/0/privacy_techniques", "Raw audio data is disseminated through controlled access only")]),
    item("E4.4", "Informed Consent Obtained from Participants", 1,
         "informed_consent: consent sought for collection and sharing; paper, electronic (app/REDCap) or video consent; consent_scope ties tiers of access to risk. consent_revocations documents withdrawal and its limits.",
         "Consent procedure, type and withdrawal mechanism are described.",
         cited=[C("/informed_consent/0/consent_documentation", "participants may consent by signing a physical paper copy"),
                C("/consent_revocations/0/description", "they may withdraw from the study at any point")],
         considered=["informed_consent", "collection_notifications"]),
    item("E4.5", "Vulnerable Populations and Compensation Documented", 0,
         "participant_compensation is detailed (electronic gift cards, $40/$80 per session, max $120). at_risk_populations is absent although the cohort is recruited for neurological, mood and respiratory disorders, and no protections for vulnerable participants are described.",
         "Compensation present; vulnerable-population documentation absent.",
         cited=[C("/participant_compensation/0/compensation_amount", "maximum of $120")],
         absent=["at_risk_populations"], considered=["sampling_strategies"]),
]))

E.append(("Data Composition and Structure",
          "Can the dataset's structure, modality, and population be understood from metadata?", [
    item("E5.1", "Cohort or Subpopulations Characteristics Described", 1,
         "subpopulations only names dimensions (Age, Gender, Sex, Ethnicity, Socioeconomic status), but sampling_strategies characterizes the cohort: participants with voice, neurological, mood and respiratory disorders recruited from high-volume expert clinics; description gives 833 participants at five sites in the USA and Canada.",
         "Population characteristics are described; no demographic distributions (noted).",
         cited=[C("/subpopulations/0/identification", "Age, Gender, Sex, Ethnicity, Socioeconomic status"),
                C("/sampling_strategies/0/description", "voice disorders, neurological disorders, mood disorders, and respiratory disorders")],
         considered=["description"]),
    item("E5.2", "Number of Instances or Samples Reported", 1,
         "instances: Participant, counts 833; per-file record counts (e.g. ppgs.parquet n=29289). Version history sums 306 + 136 + 391 = 833, consistent.",
         "Specific, internally consistent counts.",
         cited=[C("/instances/0/counts"), C("/file_collections/0/resources/0/description", "n=29289")],
         considered=["version_access.version_details"]),
    item("E5.3", "Variable-Level Metadata, Tabular Flag, and Data Splits", 0,
         "No variables, is_tabular or subsets (split/subpopulation flags). Only prose structure of parquet elements and phenotype TSV groups (confounders, demographics, diagnosis, enrollment, questionnaire, task).",
         "Structure is described at file level only; variable metadata, tabular flag and split flags are missing.",
         absent=["variables", "is_tabular", "subsets"],
         cited=[C("/file_collections/2/description", "grouped under confounders, demographics, diagnosis, enrollment, questionnaire, and task")]),
    item("E5.4", "Data Topics or Conditions Represented", 1,
         "Conditions represented: vocal pathologies, neurological disorders, psychiatric/mood conditions and respiratory disorders (labeling_strategies, sampling_strategies); ICD-10 coded diagnoses. The instances entry itself only states that each instance is a person.",
         "Condition categories are clear, though specific diseases are not enumerated.",
         cited=[C("/labeling_strategies/0/labeling_details", "vocal pathologies, neurological disorders, psychiatric conditions, and respiratory disorders")],
         considered=["instances"]),
    item("E5.5", "Data Quality, Anomalies, and Missing Data Documented", 1,
         "anomalies (site configuration differences, protocol changes, removed/failed features); sampling_strategies (non-probability, not representative); missing_data_documentation (missingness table, causes, patterns).",
         "All three aspects are documented specifically.",
         cited=[C("/anomalies/0/description", "the collection protocol changed over the course of the study"),
                C("/missing_data_documentation/0/description", "a missingness table is included with the dataset"),
                C("/sampling_strategies/0/strategies", "Non-probability sample.")]),
]))

E.append(("Data Provenance and Version Tracking",
          "Can a user determine dataset versions, update history, and provenance?", [
    item("E6.1", "Dataset Version Number Provided", 1, "version: 3.1.0",
         "Semantic version number provided and consistent with description and citation.",
         cited=[C("version", "3.1.0")]),
    item("E6.2", "Version Access Methods Documented", 1,
         "version_access: latest_version_doi plus six versions with platform, date and (mostly) DOIs; older versions remain supported.",
         "Version access is clearly documented; 2.0.0 and 2.0.1 lack DOIs (noted).",
         cited=[C("version_access.latest_version_doi", "doi:10.13026/37yb-1t42"),
                C("/version_access/versions_available/5", "3.1.0 (PhysioNet, May 1, 2026, doi:10.13026/8xbn-nq66)")],
         counts=[("version_access.versions_available", 6)]),
    item("E6.3", "Change Descriptions and Errata Provided", 1,
         "No errata field, but version_access.version_details gives a change log (v2.0 +136 participants, v3.0.0 +391, 3.1.0 minor update fixing broken parquet files) and description lists 3.1.0 additions.",
         "Per-version change descriptions are present; errata absent.",
         cited=[C("version_access.version_details", "version 3.1.0 is a minor update with no new participants"),
                C("description", "Release 3.1.0 adds files related to audio quality metrics and per-audio metadata")],
         absent=["errata"], considered=["updates"]),
    item("E6.4", "Update Schedule or Frequency Indicated", 1,
         "updates.frequency: semi-annual (twice a year), as planned in the healthsheet; update_details: static versions released semi-annually.",
         "Schedule stated, attributed to an older healthsheet (noted).",
         cited=[C("updates.frequency", "semi-annual (twice a year)"),
                C("updates.update_details", "further versions will be released on a semi-annual basis")]),
    item("E6.5", "Provenance, Source Derivation, and Raw Data Sources", 1,
         "raw_sources: released features derive from raw audio held on Synapse under controlled access; preprocessing_strategies: release 3.1.0 generated with b2aiprep v3.0.0 from REDCap exports and raw audio.",
         "Source and derivation are traceable; was_derived_from not used.",
         cited=[C("/raw_sources/0/description", "raw audio for the adult cohort is made available via Synapse under controlled access"),
                C("/preprocessing_strategies/0/preprocessing_details", "release 3.1.0 was generated with b2aiprep v3.0.0")],
         absent=["was_derived_from"], considered=["updates.update_details"]),
]))

E.append(("Scientific Motivation and Funding Transparency",
          "Does the metadata clearly state why the dataset exists and who funded it?", [
    item("E7.1", "Motivation or Purpose for Dataset Creation", 1,
         "Four purposes (ethically sourced voice database, 30,000-voice deliverable flagged as a goal not the release size, Specific Aim 1, clinical AI/ML development) plus addressing_gaps.",
         "Specific rationale and research gaps.",
         cited=[C("/purposes/0/description", "ethically sourced voice, speech, and cough database linked to health metadata"),
                C("/addressing_gaps/1/description", "Existing open-source voice datasets are limited in size, quality, and diversity.")],
         counts=[("purposes", 4)]),
    item("E7.2", "Primary Research Objectives or Tasks", 1,
         "tasks: predictive models for screening, diagnosis and treatment; disease detection and classification from voice.",
         "Concrete ML/clinical tasks.",
         cited=[C("/tasks/1/description", "training machine-learning models for disease detection and classification using voice data")]),
    item("E7.3", "Funding Sources and Mechanisms Listed", 1,
         "funders: NIH Common Fund Bridge2AI Program, grantor The NIH Common Fund, OT2 award mechanism.",
         "Named funder and mechanism; aligns with purposes.",
         cited=[C("/funders/0/name", "NIH Common Fund Bridge2AI Program"), C("/funders/0/grantor", "The NIH Common Fund")]),
    item("E7.4", "Grant IDs or Award Numbers Present", 1,
         "grant_number OT2OD032720 (NIH OT2 + OD + serial, valid pattern) and 3OT2OD032720-01S1 (valid NIH supplement form). source_caveats notes the 01S3 FY2025 variant.",
         "Award identifiers match the NIH convention.",
         cited=[C("/funders/0/grants/0/grant_number", "OT2OD032720"), C("/funders/0/grants/1/grant_number", "3OT2OD032720-01S1")]),
    item("E7.5", "Creators and Acknowledgements Documented", 1,
         "creators: full author list with co-PIs Yael Bensoussan (USF Health Morsani College of Medicine) and Olivier Elemento (Weill Cornell Medicine) identified; funder acknowledged.",
         "Creators and roles documented.",
         cited=[C("/creators/0/description", "Co-principal investigator of the project"),
                C("/creators/3/principal_investigator/affiliation/0/name", "Weill Cornell Medicine")],
         considered=["funders"]),
]))

E.append(("Technical Transparency (Data Collection and Processing)",
          "Can data collection and processing steps be replicated or understood?", [
    item("E8.1", "Collection Mechanisms and Settings Described", 1,
         "collection_mechanisms: prospective cohort via the Bridge2AI-Voice App with 22 acoustic tasks, questionnaires; in-clinic collection with trained research assistants (data_collectors); remote collection not yet used.",
         "Procedures and settings described; collection timeframes absent (noted).",
         cited=[C("/collection_mechanisms/0/mechanism_details", "a total of 22 acoustic tasks are recorded through the app"),
                C("/data_collectors/0/description", "collected in the clinic with the assistance of a trained research assistant")]),
    item("E8.2", "Data Acquisition Methods Listed", 1,
         "acquisition_methods: directly observed and self-reported, clinician-verified diagnoses; instruments: iPad 9th/10th gen, iPad Air 5th gen, Avid AE-36 microphone.",
         "Methods and devices are specific.",
         cited=[C("/acquisition_methods/0/description", "Clinical diagnoses were verified by clinicians"),
                C("/collection_mechanisms/1/description", "using an Avid AE-36 microphone")],
         absent=["raw_data_sources"], considered=["raw_sources"]),
    item("E8.3", "Preprocessing, Cleaning, Labeling, and Annotation Quality", 1,
         "preprocessing (mono, 16 kHz resampling with Butterworth anti-aliasing; STFT parameters; feature extraction), cleaning (distribution/outlier checks, schema checks, audio QC), labeling (clinician diagnosis, ICD-10), machine annotation (Whisper transcription, not audited).",
         "Detailed pipeline; imputation and annotation-quality analyses not documented (noted).",
         cited=[C("/preprocessing_strategies/2/description", "resampling to 16 kHz with a Butterworth anti-aliasing filter applied"),
                C("/cleaning_strategies/0/cleaning_details", "for audio tasks, run quality control metrics"),
                C("/labeling_strategies/0/data_annotation_protocol", "Per Bridge2AI Protocols and ICD-10 codes.")],
         absent=["imputation_protocols", "annotation_analyses"], considered=["machine_annotation_tools"]),
    item("E8.4", "Software and Tools Documented", 1,
         "preprocessing_strategies.used_software names b2aiprep v3.0.0 (which generated release 3.1.0) and senselab with repository URLs; preprocessing_details names OpenSMILE, Parselmouth/Praat, torchaudio, sparc and ppgs; machine_annotation_tools names OpenAI Whisper Large. These transformed or produced the released data.",
         "Processing software is named with version and repository (evidence in preprocessing_strategies).",
         cited=[C("/preprocessing_strategies/0/used_software/0/name", "b2aiprep"),
                C("/preprocessing_strategies/0/used_software/0/version", "3.0.0"),
                C("/machine_annotation_tools/0/tools/0", "OpenAI Whisper Large")]),
    item("E8.5", "External Standards, Resources, and Imputation Protocols", 0,
         "external_resources provide papers and protocol documentation, but no conforms_to standard and no imputation_protocols (neither imputation method nor an explicit statement that no imputation was done) are given.",
         "External resources present; standards and the imputation-protocol component of this item are absent.",
         counts=[("external_resources", 6)], absent=["conforms_to", "imputation_protocols"],
         cited=[C("/external_resources/3/name", "Developing Multi-Disorder Voice Protocols")],
         considered=["missing_data_documentation"]),
]))

E.append(("Dataset Evaluation and Limitations Disclosure",
          "Does the metadata communicate known risks, biases, or dataset limitations?", [
    item("E9.1", "Known Limitations Documented", 1,
         "known_limitations: unequal disease distribution, device/microphone differences across sites, site-dependent screening, confounders (noise, diagnostic practice variation, inaccurate responses).",
         "Specific, actionable limitations.",
         cited=[C("/known_limitations/0/description", "do not contain an equal distribution of the disease categories")],
         counts=[("known_limitations", 4)]),
    item("E9.2", "Biases Categorized Using Standard Taxonomy (RAI-aligned)", 1,
         "known_biases: recruitment/selection bias (less trust in medical system or AI, distance from sites) and sample skew by disorder, site and demographics, with a mitigation strategy. No bias_type labels.",
         "Representativeness limitations are identified concretely; formal taxonomy labels absent (noted).",
         cited=[C("/known_biases/0/bias_description", "less likely to be recruited"),
                C("/known_biases/1/mitigation_strategy", "consider the multivariate distribution")],
         absent=["future_use_impacts"]),
    item("E9.3", "Data Anomalies and Quality Issues Noted", 1,
         "anomalies: site configuration differences, protocol changes, removed features for sensitive records, files that failed feature generation.",
         "Concrete anomalies documented.",
         cited=[C("/anomalies/1/description", "some files could not generate certain features")]),
    item("E9.4", "Sensitive Content and Warnings Provided", 1,
         "sensitive_elements: race, sexual orientation, socioeconomic and health information; content_warnings: free-speech transcriptions may contain offensive content.",
         "Sensitive elements and warnings are explicit.",
         cited=[C("/sensitive_elements/1/sensitivity_details", "sexual orientation information"),
                C("/content_warnings/0/description", "offensive content is unlikely but cannot be completely avoided")]),
    item("E9.5", "Ethical Review and Social Impact Analysis", 0,
         "ethical_reviews documents USF IRB approval, but future_use_impacts is absent; downstream social impact appears only as a one-line prohibition_reason, with no impact analysis or conflicts-of-interest statement.",
         "Ethical review present; social-impact analysis missing.",
         cited=[C("/ethical_reviews/0/description", "Data collection and sharing was approved by the University of South Florida Institutional Review Board"),
                C("/prohibited_uses/2/prohibition_reason", "prevent unethical or biased outcomes")],
         absent=["future_use_impacts"]),
]))

E.append(("Cross-Platform and Community Integration",
          "Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain.", [
    item("E10.1", "Dataset Published on a Recognized Platform", 1,
         "No publisher field, but the record consistently names PhysioNet as the host: page on physionet.org, PhysioNet DOI prefix, citation 'PhysioNet. RRID:SCR_007345'.",
         "Recognized platform evident; publisher slot not populated (noted).",
         cited=[C("citation", "PhysioNet. RRID:SCR_007345."), C("page", "https://physionet.org/content/b2ai-voice/")],
         absent=["publisher"]),
    item("E10.2", "Citation and DOI for Cross-referencing", 1,
         "citation in author-year form with version 3.1.0 and version DOI 10.13026/8xbn-nq66; doi gives the project DOI 10.13026/37yb-1t42 (difference explained in source_caveats).",
         "Recommended citation and DOI present.",
         cited=[C("citation", "https://doi.org/10.13026/8xbn-nq66"), C("doi", "10.13026/37yb-1t42")]),
    item("E10.3", "Community Standards or Schema Conformance", 0,
         "conforms_to absent; BIDS v1.9.0 is mentioned only for raw audio outside this release.",
         "No community standard declared for the released data.",
         absent=["conforms_to"], considered=["raw_sources"]),
    item("E10.4", "Outreach Materials and Documentation Links", 1,
         "external_resources include training opportunities (b2aivoicescholars.org), project docs (Zenodo bridge2ai-docs), protocols; page gives the landing page.",
         "Outreach/training and documentation links present.",
         cited=[C("/external_resources/4/name", "Training opportunities for using the dataset"),
                C("/external_resources/5/external_resources/0", "https://zenodo.org/doi/10.5281/zenodo.13834653")]),
    item("E10.5", "Related Datasets with Typed Relationships", 0,
         "related_datasets absent; the Pediatric dataset is deliberately not linked (source_caveats).",
         "No typed relationships.",
         absent=["related_datasets"], considered=["source_caveats"]),
]))

elements = []
for i, (name, desc, subs) in enumerate(E, 1):
    app = [s for s in subs if s["applicable"]]
    elements.append({"id": i, "name": name, "description": desc, "sub_elements": subs,
                     "element_score": sum(s["score"] for s in app), "element_max": len(app)})

allsubs = [s for e in elements for s in e["sub_elements"]]
total = sum(s["score"] for s in allsubs if s["applicable"])
excluded = sum(1 for s in allsubs if not s["applicable"])
adj = 50 - excluded

issues = [
    {"id": "I1", "item_ids": ["E1.3"], "score_effect": "lowered", "category": "other", "type": "completeness",
     "description": "Only four keywords (health, biomarkers, bridge2ai, voice); no method, modality or condition terms."},
    {"id": "I2", "item_ids": ["E1.5", "E10.5"], "score_effect": "lowered", "category": "other", "type": "completeness",
     "description": "No parent_datasets or related_datasets; omission of the Pediatric dataset relation is explained in source_caveats but no typed relationships are documented."},
    {"id": "I3", "item_ids": ["E2.2"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "completeness",
     "description": "No confidentiality_level, hipaa_compliant status or governance committee_contact; only a Certificate of Confidentiality and the DACO name are recorded."},
    {"id": "I4", "item_ids": ["E3.3", "E10.3"], "score_effect": "lowered", "category": "format_access", "type": "completeness",
     "description": "No conforms_to/conforms_to_schema for the released data; BIDS v1.9.0 is cited only for raw audio not in this release."},
    {"id": "I5", "item_ids": ["E3.4", "E5.3"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "description": "No variables, is_tabular or subsets split/subpopulation flags; variable definitions are delegated to JSON data dictionaries not summarized in the record."},
    {"id": "I6", "item_ids": ["E4.5"], "score_effect": "lowered", "category": "consent_ethics", "type": "completeness",
     "description": "at_risk_populations absent although participants are recruited for neurological, mood and respiratory disorders; only compensation is documented."},
    {"id": "I7", "item_ids": ["E8.5"], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
     "description": "No imputation_protocols (nor a statement that imputation was not used) and no conforms_to standard; only external papers and protocol links."},
    {"id": "I8", "item_ids": ["E9.5"], "score_effect": "lowered", "category": "consent_ethics", "type": "completeness",
     "description": "future_use_impacts absent; no analysis of downstream social impacts or conflicts of interest beyond a one-line prohibition rationale."},
    {"id": "N1", "item_ids": [], "score_effect": "noted_only", "category": "source_conflict", "type": "consistency",
     "description": "license 'Bridge2AI Voice Registered Access License' and license_and_use_terms.name 'Registered Access Agreement' versus 'Only credentialed users' in the same block; the record acknowledges the registered/credentialed terminology conflict in source_caveats."},
    {"id": "N2", "item_ids": [], "score_effect": "noted_only", "category": "persistent_identifier", "type": "consistency",
     "description": "doi/id carry the project (latest-version) DOI 10.13026/37yb-1t42 while the citation uses the 3.1.0 version DOI 10.13026/8xbn-nq66; explained in source_caveats and consistent with version_access."},
    {"id": "N3", "item_ids": [], "score_effect": "noted_only", "category": "source_conflict", "type": "consistency",
     "description": "Grant numbers appear in several forms (OT2OD032720, 3OT2OD032720-01S1, 01S3); both recorded numbers are valid NIH forms and the variants are disclosed."},
    {"id": "N4", "item_ids": [], "score_effect": "noted_only", "category": "temporal_version", "type": "content_accuracy",
     "description": "Update schedule and several governance statements come from the v2.0.0-era healthsheet; versions 2.0.0 and 2.0.1 lack DOIs despite the claim that each version has a unique DOI."},
    {"id": "N5", "item_ids": [], "score_effect": "noted_only", "category": "license_use_terms", "type": "consistency",
     "description": "discouraged_uses repeats the non-research prohibitions (hiring, insurance, surveillance) also listed under prohibited_uses, blurring the prohibited/discouraged distinction."},
    {"id": "N6", "item_ids": [], "score_effect": "noted_only", "category": "format_access", "type": "completeness",
     "description": "download_url, publisher and character encoding are not populated; PhysioNet hosting and formats are evident from other fields."},
    {"id": "N7", "item_ids": [], "score_effect": "noted_only", "category": "bias_quality", "type": "completeness",
     "description": "known_biases are described in prose without bias_type categories."},
]

EXTRA = {
    "I1": ("low", ["keywords"], "Add method, modality and condition keywords (e.g. acoustic features, speech, voice disorders, neurological disorders, mood disorders, respiratory disorders)."),
    "I2": ("medium", ["parent_datasets", "related_datasets"], "Record related datasets (earlier versions, raw-audio Synapse release, pediatric dataset) with typed relationships where sources support them."),
    "I3": ("medium", ["regulatory_restrictions", "data_governance.committee_contact"], "State a confidentiality level, HIPAA status and a DACO contact."),
    "I4": ("medium", ["conforms_to", "conforms_to_schema"], "Declare any schema or community standard the released files follow."),
    "I5": ("medium", ["variables", "is_tabular", "subsets"], "Summarize key variables from the data dictionaries and set the tabular and split/subpopulation flags."),
    "I6": ("medium", ["at_risk_populations"], "Document whether vulnerable participants (e.g. cognitively impaired or psychiatric patients) are included and how they are protected."),
    "I7": ("low", ["imputation_protocols", "conforms_to"], "State whether missing values were imputed (or explicitly that they were not)."),
    "I8": ("medium", ["future_use_impacts"], "Add an analysis of anticipated downstream social impacts and mitigations."),
    "N1": ("low", ["license", "license_and_use_terms"], "Harmonize access-tier terminology with the current PhysioNet release."),
    "N2": ("low", ["doi", "citation"], "None required; the concept/version DOI split is documented."),
    "N3": ("low", ["funders"], "None required; variants are disclosed."),
    "N4": ("low", ["updates", "version_access"], "Confirm the update schedule and missing version DOIs against the current release."),
    "N5": ("low", ["discouraged_uses", "prohibited_uses"], "Keep prohibited and discouraged uses distinct."),
    "N6": ("low", ["download_url", "publisher", "file_collections"], "Populate download_url, publisher and encoding."),
    "N7": ("low", ["known_biases"], "Label biases with bias_type categories."),
}
for iss in issues:
    sev, fields, rec = EXTRA[iss["id"]]
    iss.update({"severity": sev, "fields_involved": fields, "recommendation": rec})

out = {
    "rubric": "rubric10-semantic",
    "version": "3.0",
    "d4d_file": INPUT,
    "project": "VOICE",
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
        "total_points": total, "max_points": 50, "excluded_max_points": excluded,
        "adjusted_max_points": adj,
        "normalized_percentage": round(total / adj * 100, 1) if adj else None,
        "fixed_percentage": round(total / 50 * 100, 1),
        "sub_elements_not_applicable": excluded,
        "excluded_item_ids": [s["item_id"] for s in allsubs if not s["applicable"]],
    },
    "elements": elements,
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "Version history is arithmetically consistent: 306 (v1.0) + 136 (v2.0) + 391 (v3.0.0) = 833 participants, matching instances.counts and the description.",
            "Human-subjects logic passes: involves_human_subjects true with IRB approval, informed consent, withdrawal limits and a candid re-identification risk statement (no k-anonymity).",
            "Deidentification is appropriate to voice data: raw audio withheld, free-speech-derived spectrograms/EMA/PPG removed, static features retained.",
            "Source conflicts (access tier terminology, grant number variants, concept vs version DOI, healthsheet era) are disclosed in source_caveats rather than silently resolved.",
        ],
        "consistency_checks": {"passed": 6, "failed": 0, "warnings": 4},
        "correctness_validations": {
            "doi_format": "valid (10.13026 PhysioNet prefix; version DOIs 10.13026/8xbn-nq66, 10.13026/k81f-qr68, 10.13026/249v-w155; HDN 10.57764)",
            "grant_number_format": "valid (OT2OD032720; supplement 3OT2OD032720-01S1)",
            "rrid_format": "valid (RRID:SCR_007345 in citation, PhysioNet platform RRID)",
            "url_validity": "plausible (physionet.org, synapse.org, github.com, zenodo.org, isca-archive.org)",
        },
    },
    "applicability_context": CONTEXT,
    "evaluation_scope": {
        "policy": "single_dataset",
        "units": [{"path": "#", "id": "doi:10.13026/37yb-1t42"}],
        "collection_metadata_inherited": False,
    },
    "metadata": {
        "instrument_sha256": sha(AGENT),
        "evidence_authority_sha256": sha(AUTHORITY),
        "rubric_sha256": sha(RUBRIC),
        "input_sha256": sha(INPUT),
        "context_sha256": context_digest(CONTEXT),
    },
}

p = ROOT / OUT
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(OUT, total, adj)
