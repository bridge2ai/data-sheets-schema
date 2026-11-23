# Purpose: serialize the rubric10-semantic (general context instrument v3) judgements
#   made by the evaluating session for one D4D record into the required JSON.
# Inputs: data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/AI_READI_d4d.yaml
#   (hashed only), data/rubric/rubric10.txt, .claude/agents/d4d-rubric10-semantic.md,
#   data/rubric/semantic_evidence_authority_v3.json (hashed only).
# Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep3_evaluation.json
# Serves: rubric10-semantic v3 evaluation request of 2026-11-22. Date: 2026-11-22.
# Scores below are the evaluator's manual judgements; this script only serializes them.
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "src")
from data_sheets_schema.evaluation_context import context_digest, normalize_context  # noqa: E402

INPUT = Path("data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/AI_READI_d4d.yaml")
OUT = Path("data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/AI_READI_2026-11-22b_rep3_evaluation.json")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


ALWAYS = "This item applies to every dataset"


def unknown(pred):
    return f"{pred}: not declared; retained in the denominator"


def item(item_id, name, score, evidence, note, applicability=ALWAYS, status="applicable",
         cited=(), absent=(), counts=(), considered=(), no_issue_reason=None):
    sub = {
        "item_id": item_id,
        "name": name,
        "score": score,
        "evidence": evidence,
        "quality_note": note,
        "applicable": True,
        "applicability_status": status,
        "applicability_evidence": applicability,
        "unit_scores": [{
            "path": "#",
            "score": score,
            "evidence": evidence,
            "cited": [dict(path=p, **({"quote": q} if q else {})) for p, q in cited],
            "absent": [{"path": p} for p in absent],
            "counts": [{"path": p, "claimed": n} for p, n in counts],
            "considered": list(considered),
        }],
    }
    if no_issue_reason:
        sub["no_issue_reason"] = no_issue_reason
    return sub


def u(pred):
    return dict(applicability=unknown(pred), status="unknown")


AT_MAX = "Item scored at its maximum; no deduction to account for."

E = []
E.append(("Dataset Discovery and Identification",
          "Can a user or system discover and uniquely identify this dataset?", [
    item("E1.1", "Persistent Identifier (DOI, RRID, or URI)", 1,
         "doi: 10.60775/fairhub.3; id: doi:10.60775/fairhub.3. Valid 10.XXXX/ DOI syntax; prefix 10.60775 is consistent with the stated publisher https://fairhub.io/ and the record's own version DOIs (fairhub.1, fairhub.2).",
         "Well-formed dataset-level DOI used consistently as id and doi. Prefix is not one of the rubric's example registrars but is plausible for the named FAIRhub platform (noted, not deducted).",
         cited=[("doi", "10.60775/fairhub.3"), ("id", "doi:10.60775/fairhub.3"), ("publisher", "https://fairhub.io/")],
         no_issue_reason=AT_MAX),
    item("E1.2", "Dataset Title and Description Completeness", 1,
         "title: 'Flagship Dataset of Type 2 Diabetes from the AI-READI Project'; description (>900 chars) gives version, platform, 2280 participants, collection period, modalities, file count/size and CDS directory organisation.",
         "Specific, informative title and description exceeding the 200-character threshold with concrete counts and structure.",
         cited=[("title", "Flagship Dataset of Type 2 Diabetes from the AI-READI Project"),
                ("description", "contains data from 2280 participants")],
         no_issue_reason=AT_MAX),
    item("E1.3", "Keywords or Tags for Searchability", 1,
         "7 keywords: Diabetes mellitus, Machine Learning, Artificial Intelligence, Electrocardiography, Continuous Glucose Monitoring, Retinal imaging, Eye exam.",
         "Seven relevant keywords covering condition, methods and modalities (>=5).",
         cited=[("keywords", None)], counts=[("keywords", 7)], no_issue_reason=AT_MAX),
    item("E1.4", "Landing Page and Resources (page, hierarchical resources)", 1,
         "page: https://fairhub.io/datasets/3. No top-level resources list; hierarchical structure is given instead by 10 file_collections (one per CDS data-type directory plus root metadata).",
         "Dataset-specific landing page present; hierarchical file organisation documented via file_collections.",
         cited=[("page", "https://fairhub.io/datasets/3")], absent=["resources"],
         counts=[("file_collections", 10)], considered=["file_collections"], no_issue_reason=AT_MAX),
    item("E1.5", "Hierarchical Structure (parent datasets, relationships)", 0,
         "parent_datasets and related_datasets are absent. Earlier versions (10.60775/fairhub.1, fairhub.2) appear only as strings in version_access/distribution_dates; 'relationships' describes instance relationships, not dataset relationships.",
         "No typed parent/related dataset links; the separate controlled-access set is mentioned only in source_caveats.",
         absent=["parent_datasets", "related_datasets"],
         considered=["version_access.versions_available", "relationships", "source_caveats"]),
]))
E.append(("Dataset Access and Retrieval",
          "Can the dataset and its associated resources be located, accessed, and downloaded?", [
    item("E2.1", "Access Policy and IP Restrictions Defined", 1,
         "license_and_use_terms: AI-READI Data License Agreement v2.0 (Zenodo DOI 10.5281/zenodo.17555036) with grant scope, storage, model-sharing and acknowledgement terms; ip_restrictions: title and IP remain with licensor (Washington University in St. Louis).",
         "Detailed access policy and explicit IP retention clause.",
         cited=[("license_and_use_terms.license_terms", "grants a non-exclusive, non-transferable license"),
                ("ip_restrictions.restrictions", None), ("license_and_use_terms.id", "doi:10.5281/zenodo.17555036")],
         no_issue_reason=AT_MAX),
    item("E2.2", "Regulatory Compliance and Confidentiality Classification", 1,
         "regulatory_restrictions.other_compliance: licensees must meet NIH Genomic Data Sharing policy security/privacy standards; human_subject_research.regulatory_compliance: not an FDA-regulated study; license requires HIPAA BAA cloud storage; data_governance.access_review_process describes verified-ID login and self-attestation. Public vs controlled-access tiers are distinguished (no confidential data/PII in public set, per source_caveats).",
         "Regulatory frameworks and access governance are documented. No formal confidentiality_level, hipaa_compliant flag or governance committee contact (data_governance.notes names UCSD HDOC but no contact) - noted gaps, but the regulatory and tiered-confidentiality content is meaningful.",
         applicability=unknown("regulated_access"), status="unknown",
         cited=[("regulatory_restrictions.other_compliance", "Genomic Data Sharing (GDS) Policy"),
                ("data_governance.access_review_process", "logging in through a verified ID system"),
                ("license_and_use_terms.license_terms", "HIPAA Business Associate Agreement")],
         absent=["regulatory_restrictions.confidentiality_level", "regulatory_restrictions.hipaa_compliant",
                 "data_governance.committee_contact"],
         considered=["human_subject_research.regulatory_compliance", "data_governance.notes", "source_caveats"],
         no_issue_reason=AT_MAX),
    item("E2.3", "Download URL or Platform Link Available", 1,
         "download_url is absent, but page https://fairhub.io/datasets/3 is the dataset's platform page and data_governance.access_review_process gives platform access instructions (verified ID login, license agreement; 'public download, self-attestation required').",
         "Platform link plus access instructions satisfy the item; a direct download_url would strengthen it (noted).",
         cited=[("page", "https://fairhub.io/datasets/3"),
                ("data_governance.access_review_process", "public download, self-attestation required")],
         absent=["download_url"], no_issue_reason=AT_MAX),
    item("E2.4", "Distribution Formats and File Types Specified", 1,
         "distribution_formats: DICOM (application/dicom), Markdown, CSV, JSON with MIME types; file_collections resources give TSV (text/tab-separated-values), JSON, MD, TXT.",
         "Formats and media types specified at dataset and file level.",
         cited=[("distribution_formats", None), ("/distribution_formats/0/media_type", "application/dicom"),
                ("/file_collections/0/resources/0/media_type", "text/tab-separated-values")],
         counts=[("distribution_formats", 4)], no_issue_reason=AT_MAX),
    item("E2.5", "Related Datasets and External Resources Linked", 1,
         "external_resources: docs.aireadi.org, aireadi.org, Zenodo community, GitHub organisation; prior-version DOIs (10.60775/fairhub.1, .2) listed in version_access. related_datasets field absent.",
         "External documentation well linked; related datasets only as prior-version DOIs (no typed related_datasets) - acceptable for this item, deducted under E1.5/E10.5.",
         cited=[("/external_resources/0/external_resources/0", "https://docs.aireadi.org/"),
                ("version_access.versions_available", None)],
         absent=["related_datasets"], counts=[("external_resources", 4)], no_issue_reason=AT_MAX),
]))
E.append(("Data Reuse and Interoperability",
          "Is sufficient information provided to reuse and integrate the dataset with others?", [
    item("E3.1", "License Terms Allow Reuse", 1,
         "License grants download, reproduction, use and derivative works 'for research, commercial and non-commercial purposes', with security and secondary-sharing restrictions.",
         "Clear reuse permissions under a custom license; tension with data_use_permission 'disease_specific_research' is acknowledged in source_caveats (noted).",
         cited=[("license_and_use_terms.license_terms", "for research, commercial and non-commercial purposes"),
                ("license_and_use_terms.data_use_permission", None)],
         considered=["license_and_use_terms.source_caveats"], no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E3.2", "Data Formats Are Standardized (encoding, format)", 1,
         "Standard formats: DICOM for retinal imaging, WFDB for ECG, OMOP CDM CSV for clinical data, Open mHealth JSON for wearables, ESDS for environment, TSV manifests. Character encoding not stated.",
         "Strongly standardized formats per modality; encoding absent (noted).",
         cited=[("/file_collections/0/conforms_to", "WaveForm DataBase (WFDB)"),
                ("/file_collections/3/conforms_to", "Digital Imaging and Communications in Medicine (DICOM)"),
                ("distribution_formats", None)],
         absent=["file_collections.resources.encoding"], no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E3.3", "Schema or Ontology Conformance Stated", 1,
         "conforms_to: Clinical Data Structure (CDS) v0.1.1; collections conform to OMOP CDM, DICOM, WFDB, Open mHealth, ESDS.",
         "Explicit dataset- and collection-level standard conformance.",
         cited=[("conforms_to", "Clinical Data Structure (CDS) v0.1.1"),
                ("/file_collections/1/conforms_to", "Observational Medical Outcomes Partnership")],
         absent=["conforms_to_schema"], no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E3.4", "Variable Metadata with Identifiers Defined", 0,
         "variables is absent. Only modality names (e.g. heart_rate, oxygen_saturation) and file names (participants.tsv, manifest.tsv) are given; no variable identifiers or descriptions.",
         "No variable-level metadata or data dictionary.",
         absent=["variables"], considered=["file_collections"], **u("shared_dataset")),
    item("E3.5", "Use Guidance Provided (intended, prohibited uses)", 1,
         "prohibited_uses: 5 entries (third-party sharing, model-vendor training, reproduction in publications, clinical treatment decisions, re-identification). Allowed uses stated in license_terms; intended_uses and discouraged_uses fields absent.",
         "Concrete prohibited uses and allowed scope; dedicated intended/discouraged-use fields absent (noted).",
         cited=[("/prohibited_uses/3/description", "Licensees may not make clinical treatment decisions based on the data."),
                ("license_and_use_terms.license_terms", None)],
         absent=["intended_uses", "discouraged_uses"], counts=[("prohibited_uses", 5)],
         no_issue_reason=AT_MAX),
]))
E.append(("Ethical Use and Privacy Safeguards",
          "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement.", [
    item("E4.1", "IRB or Ethics Review and Data Protection Impact", 1,
         "human_subject_research.involves_human_subjects: true; irb_approval: University of Washington IRB, STUDY00016228, with reliance by UAB and UCSD; ethical_reviews: initial approval 2022-12-20, annual renewal. data_protection_impacts absent (source_caveats states no DPIA was conducted).",
         "Specific IRB approval number, dates and reliance arrangements; consistent with involves_human_subjects=true.",
         applicability=f"any: {unknown('human_subjects')}; {unknown('regulated_access')}", status="unknown",
         cited=[("/human_subject_research/irb_approval/0", "STUDY00016228"),
                ("/ethical_reviews/0/review_details", "December 20, 2022"),
                ("human_subject_research.involves_human_subjects", None)],
         absent=["data_protection_impacts"], considered=["source_caveats"], no_issue_reason=AT_MAX),
    item("E4.2", "Deidentification Method Described", 1,
         "is_deidentified.method: FAIRhub 'NoDeIdentification' (no identifiers collected); details: team checked no HIPAA identifiers present; identifiers_removed: sex, race/ethnicity and medication removed; source_caveats records the conflicting Safe Harbor statement from Nature Metabolism.",
         "Method, verification and removed quasi-identifiers are stated with the source conflict disclosed. Semantic tension with participant_privacy (identifiers kept separately with a linking code) is noted, not deducted.",
         applicability=f"any: {unknown('human_subjects')}; {unknown('regulated_access')}", status="unknown",
         cited=[("is_deidentified.method", "NoDeIdentification"),
                ("is_deidentified.identifiers_removed", "sex and race/ethnicity"),
                ("is_deidentified.source_caveats", "Safe Harbor method")],
         considered=["is_deidentified.deidentification_details", "participant_privacy"], no_issue_reason=AT_MAX),
    item("E4.3", "Privacy Protections and Re-identification Risk Assessment", 1,
         "participant_privacy (4 entries): privacy-conscious devices (no audio/video/GPS), re-identification safeguards (dissemination system, strict license, watermarking), coded identifier storage, encrypted storage at Level 3 protections; future_use_impacts acknowledges theoretical re-identification risk.",
         "Concrete protections and mitigation; explicit reidentification_risk subfield absent but risk is acknowledged.",
         cited=[("/participant_privacy/1/privacy_techniques", "data watermarking"),
                ("/future_use_impacts/0/impact_details", "theoretical risk of future re-identification")],
         counts=[("participant_privacy", 4)], no_issue_reason=AT_MAX, **u("human_subjects")),
    item("E4.4", "Informed Consent Obtained from Participants", 1,
         "informed_consent: written consent via REDCap e-consent or in person; scope covers secondary use, banking and future sharing; withdrawal mechanism stated; consent_revocations explains data already shared remains.",
         "Complete consent documentation consistent with human-subjects status.",
         cited=[("/informed_consent/0/consent_type", "Written informed consent"),
                ("/informed_consent/0/withdrawal_mechanism", "withdraw consent at any time")],
         considered=["consent_revocations"], no_issue_reason=AT_MAX, **u("human_subjects")),
    item("E4.5", "Vulnerable Populations and Compensation Documented", 0,
         "participant_compensation: $200 stipend, conditions and travel reimbursement. at_risk_populations is absent; no protections for vulnerable groups are described (only exclusion criteria such as pregnancy in sampling_strategies).",
         "Compensation well documented, but the vulnerable-population half of the item is not addressed.",
         cited=[("/participant_compensation/0/compensation_amount", "$200 for the study visit")],
         absent=["at_risk_populations"], considered=["sampling_strategies"], **u("human_subjects")),
]))
E.append(("Data Composition and Structure",
          "Can the dataset's structure, modality, and population be understood from metadata?", [
    item("E5.1", "Cohort or Subpopulations Characteristics Described", 1,
         "subpopulations: race/ethnicity, diabetes status (No DM, Lifestyle, Oral, Insulin) and biological sex with counts and split breakdowns; sampling_strategies gives inclusion/exclusion criteria (age >=40, English, no T1D/pregnancy).",
         "Rich cohort characterisation with counts; caveat that the healthsheet answers 'No' on demographic subpopulations is disclosed.",
         cited=[("/subpopulations/1/distribution", "No DM 776, Lifestyle 560, Oral 686, Insulin 258")],
         absent=["subsets"], counts=[("subpopulations", 3)], considered=["sampling_strategies"], no_issue_reason=AT_MAX),
    item("E5.2", "Number of Instances or Samples Reported", 1,
         "instances: participant, counts 2280; total_file_count 356343; splits 1576/352/352.",
         "Specific instance counts, consistent across description, subpopulations and splits (2280).",
         cited=[("/instances/0/counts", None), ("total_file_count", None)], absent=["subsets"],
         no_issue_reason=AT_MAX),
    item("E5.3", "Variable-Level Metadata, Tabular Flag, and Data Splits", 0,
         "variables, is_tabular and subsets are absent. A recommended 70/15/15 split is documented in 'splits' (participants.tsv), but there is no variable/column dictionary or tabular flag.",
         "Split documentation exists, but the item's core variable-level metadata is missing.",
         absent=["variables", "is_tabular", "subsets"], considered=["splits", "file_collections"]),
    item("E5.4", "Data Topics or Conditions Represented", 1,
         "instances: each instance an individual participant; topic T2DM with diabetes severity groups, multimodal data (survey, clinical, retinal imaging, environmental, CGM, wearable).",
         "Condition and topics clearly represented.",
         cited=[("/instances/0/instance_type", "individual patient"),
                ("description", "individuals with and without type 2 diabetes mellitus")],
         considered=["subpopulations"], no_issue_reason=AT_MAX),
    item("E5.5", "Data Quality, Anomalies, and Missing Data Documented", 1,
         "anomalies (5: survey, wearables, imaging, undilated handheld photography, FLIO compliance); sampling_strategies (triple-balanced non-probability); missing_data_documentation (modality-level missingness, causes, Spectralis patterns).",
         "All three components present with modality-specific detail.",
         cited=[("/missing_data_documentation/0/missing_data_causes", "battery died, data lost"),
                ("/sampling_strategies/0/name", "Triple-balanced non-probability recruitment")],
         counts=[("anomalies", 5)], no_issue_reason=AT_MAX),
]))
E.append(("Data Provenance and Version Tracking",
          "Can a user determine dataset versions, update history, and provenance?", [
    item("E6.1", "Dataset Version Number Provided", 1, "version: 3.0.0.", "Semantic version given.",
         cited=[("version", None)], no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E6.2", "Version Access Methods Documented", 1,
         "version_access: latest_version_doi doi:10.60775/fairhub.3; versions_available lists 3.0.0, 2.0.0, 1.0.0 with DOIs and dates; states v2.0.0 is no longer accessible.",
         "Version DOIs and accessibility status documented.",
         cited=[("version_access.latest_version_doi", None),
                ("version_access.version_details", "version 2.0.0 is no longer accessible")],
         no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E6.3", "Change Descriptions and Errata Provided", 1,
         "version_details: participants added per version, Snellen acuity dropped in 3.0.0; updates.update_details; CHANGELOG.md listed. errata absent.",
         "Concrete change descriptions; no errata field (noted).",
         cited=[("version_access.version_details", "Snellen visual acuity variables were dropped in version 3.0.0"),
                ("updates.update_details", None)],
         absent=["errata"], no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E6.4", "Update Schedule or Frequency Indicated", 1,
         "updates.frequency: 'Approximately yearly; new static versions are released approximately once a year.'",
         "Clear update cadence.", cited=[("updates.frequency", "Approximately yearly")],
         no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E6.5", "Provenance, Source Derivation, and Raw Data Sources", 1,
         "raw_data_sources (7): ECG .xml, lab .csv, retinal .fda/.sdt converted to DICOM, Garmin .FIT converted to mHealth, MoCA .csv; raw_sources: raw data retained but not shared; updates.update_details explains derivation of each static release. was_derived_from absent.",
         "Raw source formats and conversion paths documented.",
         cited=[("/raw_data_sources/2/source_description", "converted to DICOM for the dataset")],
         absent=["was_derived_from"], counts=[("raw_data_sources", 7)], considered=["raw_sources", "updates.update_details"],
         no_issue_reason=AT_MAX, **u("shared_dataset")),
]))
E.append(("Scientific Motivation and Funding Transparency",
          "Does the metadata clearly state why the dataset exists and who funded it?", [
    item("E7.1", "Motivation or Purpose for Dataset Creation", 1,
         "purposes: enable AI/ML research into T2DM salutogenesis; foundational dataset for a temporal atlas of T2DM; addressing_gaps adds diversity and AI-readiness gaps.",
         "Specific scientific rationale.", cited=[("/purposes/0/description", "salutogenesis")],
         counts=[("purposes", 2)], no_issue_reason=AT_MAX),
    item("E7.2", "Primary Research Objectives or Tasks", 1,
         "tasks: pseudotime manifold analysis to predict disease trajectories.",
         "One concrete intended analysis; source_caveats notes the dataset is hypothesis-agnostic.",
         cited=[("/tasks/0/name", "Pseudotime manifold analysis")], no_issue_reason=AT_MAX),
    item("E7.3", "Funding Sources and Mechanisms Listed", 1,
         "funders: NIH through the Common Fund Bridge2AI Program; Research to Prevent Blindness.",
         "Named funders with mechanism (Bridge2AI program).",
         cited=[("/funders/0/grantor", "NIH Common Fund Bridge2AI Program")], counts=[("funders", 2)],
         no_issue_reason=AT_MAX),
    item("E7.4", "Grant IDs or Award Numbers Present", 1,
         "grants: OT2OD032644 (Bridge2AI Salutogenesis Data Generation Project), P30DK035816, UL1TR003096; typo OT2ODO32644 in the healthsheet corrected and disclosed.",
         "All three follow the NIH activity-code/IC/serial pattern (OT2 OD, P30 DK, UL1 TR).",
         cited=[("/funders/0/grants/0/grant_number", "OT2OD032644"), ("/funders/0/grants/1/grant_number", "P30DK035816"),
                ("/funders/0/grants/2/grant_number", "UL1TR003096")], no_issue_reason=AT_MAX),
    item("E7.5", "Creators and Acknowledgements Documented", 1,
         "creators: AI-READI Consortium plus 20 named principal investigators, most with ORCID and ROR affiliations; affiliation conflicts documented in source_caveats.",
         "Extensive creator attribution.", cited=[("/creators/0/name", "AI-READI Consortium")],
         counts=[("creators", 21)], considered=["funders"], no_issue_reason=AT_MAX),
]))
E.append(("Technical Transparency (Data Collection and Processing)",
          "Can data collection and processing steps be replicated or understood?", [
    item("E8.1", "Collection Mechanisms and Settings Described", 1,
         "collection_mechanisms (24): REDCap, Philips PageWriter TC30 ECG, Dexcom G6, Garmin Vivosmart 5, imaging devices with scan protocols, specimen handling; collection_timeframes give dates.",
         "Detailed devices, settings and protocols.", cited=[("/collection_mechanisms/1/name", "Philips PageWriter TC30 Cardiograph")],
         counts=[("collection_mechanisms", 24)], no_issue_reason=AT_MAX, **u("data_collection")),
    item("E8.2", "Data Acquisition Methods Listed", 1,
         "acquisition_methods: directly observed (labs, vitals, retinal imaging) and subject-reported with verification; raw_data_sources give device export formats.",
         "Acquisition methods and instruments documented.",
         cited=[("/acquisition_methods/1/acquisition_details", "cross-referencing entered medications")],
         considered=["raw_data_sources"], no_issue_reason=AT_MAX, **u("data_collection")),
    item("E8.3", "Preprocessing, Cleaning, Labeling, and Annotation Quality", 1,
         "preprocessing_strategies: DICOM conversion, mapping to OMOP CDM/DICOM; cleaning_strategies: site QC, internal PII review, REDCap range checks, skip-pattern and duplicate checks. No labels (hypothesis-agnostic, per source_caveats); imputation not documented.",
         "Preprocessing and cleaning concretely described; labeling/imputation absent (noted).",
         cited=[("/preprocessing_strategies/1/preprocessing_details", "OMOP Common Data Model"),
                ("/cleaning_strategies/2/cleaning_details", "range checks")],
         absent=["labeling_strategies", "imputation_protocols", "annotation_analyses", "machine_annotation_tools"],
         no_issue_reason=AT_MAX, **u("data_processing")),
    item("E8.4", "Software and Tools Documented", 0,
         "No software that produced or transformed the released data is named in preprocessing_strategies (DICOM conversion and OMOP mapping name no tool), cleaning_strategies, or any used_software slot. REDCap is capture/data-entry software (role a) and its range-check reports are validation (role d); MoCA Duo and Dexcom Clarity are capture apps (a); the OMOP DQD file is quality assessment (d); external_resources https://github.com/AI-READI is an organisation-root pointer identifying the publisher only.",
         "Score 0: nothing in the processing roles is named; named software falls under roles (a) and (d).",
         absent=["preprocessing_strategies.used_software", "cleaning_strategies.used_software",
                 "machine_annotation_tools", "labeling_strategies", "imputation_protocols"],
         considered=["preprocessing_strategies", "cleaning_strategies", "external_resources", "collection_mechanisms",
                     "file_collections"], **u("processing_software")),
    item("E8.5", "External Standards, Resources, and Imputation Protocols", 1,
         "external_resources: documentation site (CC-BY 4.0), project website, Zenodo community, GitHub; conforms_to CDS v0.1.1 and per-collection standards. imputation_protocols absent.",
         "External documentation and standards present; imputation neither described nor explicitly ruled out (noted).",
         cited=[("/external_resources/0/description", "relies on the dataset documentation"),
                ("conforms_to", None)], absent=["imputation_protocols"], no_issue_reason=AT_MAX),
]))
E.append(("Dataset Evaluation and Limitations Disclosure",
          "Does the metadata communicate known risks, biases, or dataset limitations?", [
    item("E9.1", "Known Limitations Documented", 1,
         "known_limitations (4): English-language requirement, group balance not yet achieved, urban/hospital-based recruitment, races/ethnicities not included.",
         "Specific limitations with impact.", cited=[("/known_limitations/0/name", "English-language requirement")],
         counts=[("known_limitations", 4)], no_issue_reason=AT_MAX),
    item("E9.2", "Biases Categorized Using Standard Taxonomy (RAI-aligned)", 1,
         "known_biases: volunteer bias, bias_type selection_bias, with generalizability impact.",
         "Typed bias using a standard category; only one bias listed, but representativeness limitations are covered in known_limitations.",
         cited=[("/known_biases/0/bias_type", "selection_bias")], considered=["future_use_impacts"],
         no_issue_reason=AT_MAX),
    item("E9.3", "Data Anomalies and Quality Issues Noted", 1,
         "anomalies: 5 modality-specific entries (survey skips, wearable failures, imaging noise/transfer failures, handheld photo quality, FLIO compliance).",
         "Concrete, modality-specific anomaly documentation.",
         cited=[("/anomalies/3/anomaly_details", "image quality varies")], counts=[("anomalies", 5)],
         no_issue_reason=AT_MAX),
    item("E9.4", "Sensitive Content and Warnings Provided", 0,
         "sensitive_elements and content_warnings are absent. The statement that the public set contains no sensitive data, and the list of sensitive elements in the controlled-access set, appear only in the top-level source_caveats provenance note.",
         "No structured sensitive-content documentation or warnings.",
         absent=["sensitive_elements", "content_warnings"], considered=["source_caveats", "is_deidentified"]),
    item("E9.5", "Ethical Review and Social Impact Analysis", 1,
         "ethical_reviews: UW IRB review with dates and renewal; future_use_impacts: no anticipated unfair treatment, theoretical re-identification risk; prohibited uses and watermarking act as mitigations.",
         "Ethical review documented; social impact analysis brief but present.",
         cited=[("/ethical_reviews/0/name", "University of Washington IRB review"),
                ("/future_use_impacts/0/impact_details", "unfair treatment or harm")], no_issue_reason=AT_MAX),
]))
E.append(("Cross-Platform and Community Integration",
          "Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain.", [
    item("E10.1", "Dataset Published on a Recognized Platform", 1, "publisher: https://fairhub.io/ (FAIRhub).",
         "Recognized data platform.", cited=[("publisher", "https://fairhub.io/")], no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E10.2", "Citation and DOI for Cross-referencing", 1,
         "doi 10.60775/fairhub.3 present; no recommended citation string (citation absent).",
         "DOI enables cross-referencing; a citation string would strengthen it (noted).",
         cited=[("doi", None)], absent=["citation"], no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E10.3", "Community Standards or Schema Conformance", 1,
         "conforms_to CDS v0.1.1; OMOP CDM, DICOM, WFDB, Open mHealth in file_collections.",
         "Multiple community standards.", cited=[("conforms_to", None), ("/file_collections/7/conforms_to", "Open mHealth")],
         no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E10.4", "Outreach Materials and Documentation Links", 1,
         "external_resources: docs.aireadi.org, aireadi.org, Zenodo community, GitHub org; page: FAIRhub landing page.",
         "Documentation and landing pages linked.", cited=[("page", None), ("/external_resources/1/external_resources/0", "https://aireadi.org/")],
         no_issue_reason=AT_MAX, **u("shared_dataset")),
    item("E10.5", "Related Datasets with Typed Relationships", 0,
         "related_datasets is absent; prior versions appear only as untyped strings in version_access and the controlled-access set only in source_caveats.",
         "No typed dataset relationships.", absent=["related_datasets"],
         considered=["version_access.versions_available", "source_caveats"], **u("shared_dataset")),
]))

elements = []
total = 0
for i, (name, desc, subs) in enumerate(E, 1):
    s = sum(x["score"] for x in subs if x["score"] is not None)
    total += s
    elements.append({"id": i, "name": name, "description": desc, "sub_elements": subs,
                     "element_score": s, "element_max": sum(1 for x in subs if x["applicable"])})

issues = [
    {"id": "I1", "severity": 'medium', "fields_involved": ['parent_datasets', 'related_datasets'], "recommendation": 'Add related_datasets entries with typed relationships for prior versions (fairhub.1, fairhub.2) and the controlled-access set.', "item_ids": ["E1.5", "E10.5"], "score_effect": "lowered", "category": "other", "type": "completeness",
     "description": "No parent_datasets or related_datasets with typed relationships; prior versions and the controlled-access set are not linked as related datasets."},
    {"id": "I2", "severity": 'high', "fields_involved": ['variables', 'is_tabular', 'subsets'], "recommendation": 'Add a variable dictionary (at least for participants.tsv and OMOP tables), set is_tabular and subset split/subpopulation flags.', "item_ids": ["E3.4", "E5.3"], "score_effect": "lowered", "category": "variables_metadata", "type": "completeness",
     "description": "No variable-level metadata (variables), no is_tabular flag and no subsets flags, despite tabular OMOP CSV and TSV files."},
    {"id": "I3", "severity": 'medium', "fields_involved": ['at_risk_populations', 'participant_compensation'], "recommendation": 'Document whether vulnerable populations were included and any protections applied.', "item_ids": ["E4.5"], "score_effect": "lowered", "category": "consent_ethics", "type": "completeness",
     "description": "at_risk_populations absent: no protections for vulnerable groups are described although compensation is documented."},
    {"id": "I4", "severity": 'medium', "fields_involved": ['preprocessing_strategies', 'cleaning_strategies', 'external_resources'], "recommendation": 'Name the software (with versions or repositories) used for DICOM conversion, OMOP mapping and FIT-to-mHealth conversion in used_software.', "item_ids": ["E8.4"], "score_effect": "lowered", "category": "processing_provenance", "type": "completeness",
     "description": "No software that produced or transformed the released data (DICOM conversion, OMOP mapping, FIT-to-mHealth conversion) is named; only capture (REDCap, MoCA Duo, Clarity) and validation (REDCap range checks, OMOP DQD) tools appear."},
    {"id": "I5", "severity": 'medium', "fields_involved": ['sensitive_elements', 'content_warnings', 'source_caveats'], "recommendation": 'Move sensitivity statements into sensitive_elements and add content warnings where relevant.', "item_ids": ["E9.4"], "score_effect": "lowered", "category": "privacy_regulatory", "type": "completeness",
     "description": "sensitive_elements and content_warnings absent; sensitivity statements exist only inside the top-level source_caveats note."},
    {"id": "N1", "severity": 'low', "fields_involved": ['is_deidentified', 'participant_privacy'], "recommendation": 'Explain that NoDeIdentification refers to released data while study identifiers are held separately.', "item_ids": [], "score_effect": "noted_only", "category": "source_conflict", "type": "consistency",
     "description": "is_deidentified records NoDeIdentification ('no identifiers were collected') while participant_privacy describes identifiers stored separately via a linking code and identifiers_removed lists removed sex/race/medication; the Safe Harbor alternative is disclosed in source_caveats. Plausibly reconcilable (released data vs internal study records) but not explained."},
    {"id": "N2", "severity": 'low', "fields_involved": ['license_and_use_terms'], "recommendation": 'Reconcile the disease-specific use restriction with the license grant in one statement.', "item_ids": [], "score_effect": "noted_only", "category": "license_use_terms", "type": "consistency",
     "description": "license_terms grants research, commercial and non-commercial use while data_use_permission is disease_specific_research and access requires agreeing to T2DM-only research; the record discloses both."},
    {"id": "N3", "severity": 'low', "fields_involved": ['download_url', 'citation', 'intended_uses', 'errata', 'imputation_protocols', 'regulatory_restrictions'], "recommendation": 'Populate the dedicated fields where source information exists.', "item_ids": [], "score_effect": "noted_only", "category": "format_access", "type": "completeness",
     "description": "download_url, citation, file encoding, intended_uses, discouraged_uses, errata, imputation_protocols, confidentiality_level and a governance committee contact are absent; the corresponding items were satisfied by other evidence."},
    {"id": "N4", "severity": 'low', "fields_involved": ['version_access', 'instances'], "recommendation": 'State which study years each version covers once, with the conflict resolved or attributed.', "item_ids": [], "score_effect": "noted_only", "category": "temporal_version", "type": "consistency",
     "description": "Version year labels conflict between README ('year 3 data') and healthsheet (first/second year), and instances caveat notes carried-over 'first year' wording; disclosed in caveats."},
    {"id": "N5", "severity": 'low', "fields_involved": ['doi'], "recommendation": 'None required; prefix is plausible for FAIRhub.', "item_ids": [], "score_effect": "noted_only", "category": "persistent_identifier", "type": "correctness",
     "description": "DOI prefix 10.60775 is not among the rubric's example registrars; it is syntactically valid and consistent with the named FAIRhub publisher and version DOIs, so it was accepted."},
]

ctx = normalize_context({})
out = {
    "rubric": "rubric10-semantic",
    "version": "3.0",
    "d4d_file": str(INPUT),
    "project": "AI_READI",
    "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3",
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
            "Strong collection, consent, IRB, versioning and funding documentation with source conflicts explicitly disclosed in source_caveats.",
            "Main gaps are structural: no variable dictionary, no typed related datasets, no named processing software, no structured sensitive-content fields, no at-risk population documentation.",
            "No caller applicability context was supplied; all conditional items remained applicable (unknown) and in the denominator.",
        ],
        "consistency_checks": {"passed": 5, "failed": 0, "warnings": 3},
        "correctness_validations": {
            "doi_format": "valid (10.60775/fairhub.3; license DOI 10.5281/zenodo.17555036)",
            "grant_number_format": "valid NIH patterns (OT2OD032644, P30DK035816, UL1TR003096)",
            "rrid_format": "not_applicable (no RRID present)",
            "url_validity": "valid structure (fairhub.io, docs.aireadi.org, aireadi.org, zenodo.org, github.com)",
        },
    },
    "applicability_context": ctx,
    "evaluation_scope": {
        "policy": "single_dataset",
        "units": [{"path": "#", "id": "doi:10.60775/fairhub.3"}],
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
OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(OUT, total)
