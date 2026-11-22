# Purpose: serialize the manual rubric20-semantic (v3, general context) judgements for
#   VOICE_PEDIATRIC, method claudecode_agent, label 2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3.
# Inputs: the D4D record (hashed only; scores below are the evaluator's manual judgements),
#   .claude/agents/d4d-rubric20-semantic.md, data/rubric/rubric20.txt,
#   data/rubric/semantic_evidence_authority_v3.json.
# Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/
#   VOICE_PEDIATRIC_2026-11-22b_rep3_evaluation.json
# Serves: rubric20 semantic evaluation request (no caller applicability context). Date: 2026-11-22.
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest, normalize_context  # noqa: E402

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/VOICE_PEDIATRIC_d4d.yaml"
OUT = "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/VOICE_PEDIATRIC_2026-11-22b_rep3_evaluation.json"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


ALWAYS = "This item applies to every dataset"


def unk(pred):
    return f"{pred}: not declared by the caller (no context supplied); unknown, retained in the denominator"


def q(id_, name, desc, stype, score, max_score, label, evidence, note, appl_ev, status,
      cited=(), absent=(), counts=(), considered=(), no_issue_reason=None):
    item = {
        "id": id_, "name": name, "description": desc[:120], "score_type": stype,
        "score": score, "max_score": max_score, "score_label": label,
        "evidence": evidence, "quality_note": note, "applicable": True,
        "applicability_status": status, "applicability_evidence": appl_ev,
        "unit_scores": [{
            "path": "#", "score": score, "evidence": evidence,
            "cited": [dict(c) for c in cited],
            "absent": [{"path": a} for a in absent],
            "counts": [{"path": p, "claimed": n} for p, n in counts],
            "considered": list(considered),
        }],
    }
    if no_issue_reason:
        item["no_issue_reason"] = no_issue_reason
    return item


def c(path, quote=None):
    d = {"path": path}
    if quote:
        d["quote"] = quote
    return d


AT_MAX = "Item scored at its maximum; no deduction to account for."

cat1 = [
    q(1, "Field Completeness",
      "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
      "numeric", 3, 5, "Good (~79% populated)",
      "11 of 14 listed fields populated: id, title, description, keywords, license_and_use_terms, doi, page, creators, purposes, instances, variables. Absent: top-level resources, parent_datasets, regulatory_restrictions.confidentiality_level.",
      "11/14 = 78.6%, above the ~70% anchor but below the >=90% anchor; scored 3.",
      ALWAYS, "applicable",
      cited=[c("id", "doi:10.13026/mf9s-5r03"), c("title", "Bridge2AI-Voice Pediatric Dataset"), c("description"),
             c("license_and_use_terms.name", "Bridge2AI Voice Registered Access License"), c("doi", "10.13026/mf9s-5r03"),
             c("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/"), c("purposes"), c("instances"), c("variables")],
      absent=["resources", "parent_datasets", "regulatory_restrictions"],
      counts=[("keywords", 5), ("creators", 121)], considered=["keywords", "creators"]),
    q(2, "Entry Length Adequacy",
      "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
      "numeric", 5, 5, "Excellent (>200 chars)",
      "description is 675 characters; the single purposes response is 212 characters; both exceed 200.",
      "Average narrative length is well above 200 characters and the content is specific (counts, age range, site, release structure).",
      ALWAYS, "applicable",
      cited=[c("description", "contains derived audio features for 23,533 recordings collected from 300 participants aged 2-18"),
             c("purposes.response", "ethically sourced flagship dataset")],
      counts=[("purposes", 1)], no_issue_reason=AT_MAX),
    q(3, "Keyword Diversity",
      "Number of distinct keywords describing the dataset.",
      "numeric", 3, 5, "Good (3-7 keywords)",
      "Five keywords: health, pediatric, biomarkers, bridge2ai, voice.",
      "5 distinct keywords falls in the 3-7 band; generic terms (health, biomarkers) and no feature/modality terms (spectrogram, acoustic features, speech).",
      ALWAYS, "applicable", counts=[("keywords", 5)], considered=["keywords"]),
    q(4, "File Enumeration and Type Variety",
      "Number and variety of documented distribution formats and file types.",
      "numeric", 3, 5, "Good (2-3 file types)",
      "distribution_formats lists Parquet, TSV and JSON (data dictionaries); file_collections enumerate 9 parquet feature files, static_features.tsv and demographics.tsv; the metadata collection lists no files.",
      "Three formats places this in the 2-3 band. total_file_count is absent; metadata folder files and audio_quality_metrics.tsv are not enumerated.",
      ALWAYS, "applicable",
      cited=[c("distribution_formats.format", "Parquet"), c("/file_collections/0/resources/9/format", "TSV"),
             c("/distribution_formats/2/media_type", "application/json")],
      absent=["total_file_count"],
      counts=[("distribution_formats", 3), ("file_collections", 3), ("/file_collections/0/resources", 10)]),
    q(5, "Data File Size Availability",
      "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
      "pass_fail", 1, 1, "Pass",
      "instances give counts 23533 recordings and 300 participants; per-file n (23533 / 23532) and tensor dimensions are given.",
      "Instance counts present; byte sizes (total_size_bytes, file_collections.total_bytes) absent, which does not fail this pass/fail item.",
      ALWAYS, "applicable",
      cited=[c("/instances/0/counts"), c("/instances/1/counts")],
      absent=["total_size_bytes"], counts=[("instances", 2)], no_issue_reason=AT_MAX),
]

cat2 = [
    q(6, "Dataset Identification Metadata",
      "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification.",
      "pass_fail", 1, 1, "Pass",
      "doi 10.13026/mf9s-5r03 (PhysioNet prefix); page on physionet.org; citation names PhysioNet and RRID:SCR_007345.",
      "Persistent ID and hosting platform both identifiable, although the publisher field itself is absent.",
      ALWAYS, "applicable",
      cited=[c("doi", "10.13026/mf9s-5r03"), c("page"), c("id"), c("citation", "PhysioNet. RRID:SCR_007345")],
      absent=["publisher"], no_issue_reason=AT_MAX),
    q(7, "Funding and Acknowledgements Completeness",
      "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
      "numeric", 5, 5, "Excellent (funder + grant + affiliations)",
      "Funder NIH Common Fund with grant 3OT2OD032720-01S1 (valid NIH supplement pattern); 26 of 121 creators carry institutional affiliations, including all named leads and PIs.",
      "Meets the 5 anchor. Many contributors lack affiliations, and the grant number differs from other bundle sources (S2/S3), which the record transparently caveats.",
      ALWAYS, "applicable",
      cited=[c("/funders/0/grants/0/grant_number", "3OT2OD032720-01S1"), c("/funders/0/name", "NIH Common Fund"),
             c("/creators/0/affiliations/0/name", "USF Health Morsani College of Medicine")],
      counts=[("creators", 121), ("funders", 1)], no_issue_reason=AT_MAX),
    q(8, "Ethical and Privacy Declarations",
      "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable.",
      "numeric", 3, 5, "Good (ethics review + consent, partial privacy)",
      "ethical_reviews names the SickKids Research Ethics Board; human_subject_research true with special population children 2-18; informed_consent (parental or participant); at_risk_populations with assent procedures; participant_privacy re-identification risk for voice. No is_deidentified, deidentification method, participant_compensation, data_protection_impacts or regulatory compliance fields.",
      "Strong ethics/consent/assent coverage, but deidentification method, compensation, data-protection impact and compliance framework are absent, so not comprehensive.",
      unk("human_subjects"), "unknown",
      cited=[c("/ethical_reviews/0/reviewing_organization", "Research Ethics Board at the Hospital for Sick Children"),
             c("human_subject_research.involves_human_subjects"), c("/informed_consent/0/consent_obtained"),
             c("at_risk_populations.assent_procedures", "children provide verbal assent where appropriate"),
             c("/participant_privacy/0/reidentification_risk", "a voice can never be fully de-identified")],
      absent=["is_deidentified", "participant_compensation", "data_protection_impacts", "regulatory_restrictions"],
      considered=["sensitive_elements", "cleaning_strategies"]),
    q(9, "Access Requirements and Governance Documentation",
      "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts.",
      "numeric", 3, 5, "Good (license and access terms, no confidentiality classification)",
      "license_and_use_terms: Bridge2AI Voice Registered Access License, credentialed PhysioNet users who sign the DUA; data_governance names DACO with contact for raw audio. No regulatory_restrictions (confidentiality_level, HIPAA/other compliance), ip_restrictions or data_protection_impacts.",
      "More than a bare license (DUA and committee contact), but the 5 anchor requires a confidentiality classification and restrictions, which are absent.",
      ALWAYS, "applicable",
      cited=[c("license_and_use_terms.license_terms", "only credentialed PhysioNet users who sign the data use agreement"),
             c("data_governance.committee_name", "Data Access Compliance Office (DACO)")],
      absent=["regulatory_restrictions", "ip_restrictions", "data_protection_impacts"]),
    q(10, "Interoperability, Standardization, and Cross-Platform Integration",
      "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures.",
      "numeric", 3, 5, "Good (standard formats, no schema conformance)",
      "Standard open formats (Parquet, TSV, JSON data dictionaries) with loader guidance (HuggingFace datasets). BIDS conversion is mentioned only as an internal processing step; no conforms_to/conforms_to_schema; related_datasets deliberately not recorded; external_resources only the project website.",
      "Standard formats but no declared schema/ontology conformance or typed relationships; scored 3.",
      unk("shared_dataset"), "unknown",
      cited=[c("/distribution_formats/0/description", "HuggingFace datasets library"), c("external_resources")],
      absent=["conforms_to", "conforms_to_schema", "related_datasets"],
      considered=["/preprocessing_strategies/3/preprocessing_details", "file_collections"]),
]

cat3 = [
    q(11, "Tool and Software Transparency",
      "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs.",
      "numeric", 3, 5, "Good (strategies and tools listed, versions missing)",
      "Four preprocessing strategies (TSV export, b2aiprep feature extraction, static features with openSMILE/Praat/parselmouth/torchaudio, ReproSchema-UI -> REDCap -> BIDS) and two cleaning strategies; b2aiprep has a GitHub URL and license, but its release version is explicitly not stated; openSMILE, Praat, parselmouth, torchaudio have no versions or URLs. Feature parameters (window, hop, FFT size) are given per file.",
      "Strategy coverage is good, but software versions are absent for every tool and URLs exist for only one, so the 5 anchor (versions/URLs) is not met.",
      unk("data_processing"), "unknown",
      cited=[c("/preprocessing_strategies/1/used_software/0/url", "https://github.com/sensein/b2aiprep"),
             c("/preprocessing_strategies/1/used_software/0/description", "the version used for this release is not stated"),
             c("/preprocessing_strategies/2/preprocessing_details", "openSMILE toolkit, Praat, parselmouth and torchaudio"),
             c("/cleaning_strategies/1/cleaning_details", "manually checked for presence of unconsented speakers")],
      absent=["labeling_strategies", "imputation_protocols", "missing_data_documentation", "machine_annotation_tools"],
      counts=[("preprocessing_strategies", 4), ("cleaning_strategies", 2)],
      considered=["anomalies"]),
    q(12, "Collection Protocol Clarity",
      "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
      "numeric", 3, 5, "Good (mechanisms documented, timeframes absent)",
      "collection_mechanisms: reproschema-ui on tablets, headset or tablet microphone, age-appropriate protocol, pediatric task list; direct_collection single session with caregiver support; raw_sources points to Synapse. No collection_timeframes, data_collectors or acquisition_methods.",
      "Mechanisms are detailed, but the 5 anchor requires collectors and timeframes, which are absent.",
      unk("data_collection"), "unknown",
      cited=[c("/collection_mechanisms/1/description", "reproschema-ui"),
             c("/collection_mechanisms/2/description", "built-in tablet microphone"),
             c("/direct_collection/0/collection_details", "completed the recording and demographic data collection in one session"),
             c("/raw_sources/0/access_url")],
      absent=["collection_timeframes", "data_collectors", "acquisition_methods"],
      counts=[("collection_mechanisms", 4)], considered=["sampling_strategies"]),
    q(13, "Version History, Maintenance, and Sustainability",
      "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access.",
      "numeric", 3, 5, "Good (version + access + persistent ID)",
      "version 1.1.0; version_access lists 1.0.0 and 1.1.0 with dates and the changes in 1.1; DOI on PhysioNet. No maintainers, updates plan, errata or publisher; no preservation/commitment statement.",
      "Versioning is well described, but there is no maintenance plan, responsible maintainer or sustainability commitment. The doi field holds the latest-version DOI while version is 1.1.0 (whose DOI is h995-bt35); explained in version_details.",
      unk("shared_dataset"), "unknown",
      cited=[c("version", "1.1.0"), c("version_access.version_details", "Version 1.1.0 has the DOI 10.13026/h995-bt35"),
             c("doi")],
      absent=["maintainers", "updates", "errata", "publisher"],
      counts=[("version_access.versions_available", 2)], considered=["distribution_dates"]),
    q(14, "Associated Publications",
      "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources.",
      "numeric", 5, 5, "Excellent (formal citation + >=2 references)",
      "Formal dataset citation with authors, title, version, PhysioNet and DOI 10.13026/h995-bt35; additional distinct references: dataset DOI 10.13026/mf9s-5r03 and project website b2ai-voice.org.",
      "At least two distinct references and a formal dataset citation; no peer-reviewed article is cited, which this item does not require.",
      ALWAYS, "applicable",
      cited=[c("citation", "Bridge2AI-Voice Pediatric Dataset (version 1.1.0). PhysioNet."), c("doi"),
             c("/external_resources/0/external_resources/0", "https://b2ai-voice.org/")],
      no_issue_reason=AT_MAX),
    q(15, "Human Subject Representation",
      "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups.",
      "numeric", 3, 5, "Good (population and age groups, no detailed demographics)",
      "300 participants aged 2-18 from the Hospital for Sick Children; subpopulation age groups (Peds 2-4, 4-6, 6-10, 10+); inclusion/exclusion criteria in sampling_strategies; at_risk_populations documents children. No sex/gender, race/ethnicity, diagnosis or per-group counts.",
      "Subgroups and eligibility are described, but detailed demographics are absent, so the 5 anchor is not met.",
      unk("human_subjects"), "unknown",
      cited=[c("/instances/1/description", "300 participants aged 2-18"),
             c("/subpopulations/0/identification", "Peds 10+, Peds 6-10, Peds 4-6 and Peds 2-4"),
             c("/sampling_strategies/0/description", "Inclusion criteria were 2 to 18 years of age and English proficiency"),
             c("at_risk_populations.at_risk_groups_included")],
      absent=["missing_data_documentation", "subsets"],
      counts=[("subpopulations", 1)]),
]

cat4 = [
    q(16, "Findability (Persistent Links)",
      "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
      "pass_fail", 1, 1, "Pass",
      "PhysioNet landing page URL, DOI 10.13026/mf9s-5r03, project website and Synapse raw-audio URL.",
      "Multiple plausible persistent links; download_url absent but not required for a pass.",
      ALWAYS, "applicable",
      cited=[c("page", "https://physionet.org/content/b2ai-voice-pediatric/1.1.0/"), c("doi"), c("external_resources")],
      absent=["download_url"], no_issue_reason=AT_MAX),
    q(17, "Accessibility (Access Mechanism)",
      "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
      "numeric", 5, 5, "Excellent (platform, login, policy)",
      "Platform PhysioNet; access requires a credentialed PhysioNet account and signing the Bridge2AI Voice Registered Access Agreement (no training); formats Parquet/TSV/JSON; raw audio separately via Synapse after DACO institutional sign-off.",
      "Access tier and authorization steps are explicit for both the derived release and the withheld raw audio. Minor wording ambiguity between a 'Registered Access' license name and 'credentialed' users is noted but does not obscure the path.",
      unk("shared_dataset"), "unknown",
      cited=[c("license_and_use_terms.license_terms", "No training is required."),
             c("/raw_sources/0/raw_data_details", "requires institutional sign off"),
             c("distribution_formats")],
      absent=["download_url"], no_issue_reason=AT_MAX),
    q(18, "Reusability, Use Guidance, and Social Impact",
      "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis.",
      "numeric", 3, 5, "Good (license + basic intended uses)",
      "License named with DUA terms; three brief intended uses (developmental norms, AI screening tools, clinical insight). No prohibited_uses, discouraged_uses or future_use_impacts.",
      "License plus basic use guidance; no prohibited/discouraged uses or social-impact analysis.",
      ALWAYS, "applicable",
      cited=[c("license_and_use_terms.name"), c("/intended_uses/1/description", "AI-driven tools for early screening")],
      absent=["prohibited_uses", "discouraged_uses", "future_use_impacts"],
      counts=[("intended_uses", 3)]),
    q(19, "Data Integrity, Provenance Graph, and Quality",
      "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation.",
      "numeric", 3, 5, "Good (version history and textual lineage, no full provenance graph)",
      "version_access with release history; raw_sources documents withheld raw audio on Synapse; textual lineage ReproSchema-UI -> REDCap -> BIDS -> b2aiprep -> parquet; anomalies note missing features. No was_derived_from, parent_datasets, errata, updates, splits or missing_data_documentation.",
      "Version history and partial textual lineage, without explicit entity-activity-agent derivation links; scored 3.",
      ALWAYS, "applicable",
      cited=[c("version_access.versions_available"),
             c("/preprocessing_strategies/3/preprocessing_details", "extracted and transformed into REDCap format"),
             c("/anomalies/0/anomaly_details", "could not generate certain features")],
      absent=["was_derived_from", "parent_datasets", "errata", "updates", "splits", "missing_data_documentation"],
      considered=["raw_sources"]),
    q(20, "Bias Documentation and Responsible AI Alignment",
      "Documentation of known biases, limitations and potential effects on intended or foreseeable uses.",
      "numeric", 0, 5, "Absent",
      "known_biases and future_use_impacts are absent. Bias-relevant facts (single recruitment site, English-proficiency requirement, non-verbal children excluded, mixed headset/tablet microphones) appear only as collection details, never identified as biases or limitations.",
      "No bias documentation; scored 0.",
      ALWAYS, "applicable",
      absent=["known_biases", "future_use_impacts"],
      considered=["/collection_mechanisms/2/description", "sampling_strategies", "anomalies"]),
]


def tot(qs):
    return sum(x["score"] for x in qs), sum(x["max_score"] for x in qs)


cats = []
for nm, qs in [("Structural Completeness", cat1), ("Metadata Quality & Content", cat2),
               ("Technical Documentation", cat3), ("FAIRness & Accessibility", cat4)]:
    s, m = tot(qs)
    cats.append({"name": nm, "questions": qs, "category_score": s, "category_max": m})
total = sum(x["category_score"] for x in cats)
maxp = sum(x["category_max"] for x in cats)


FIELDS = {
    "I1": ["resources", "parent_datasets", "regulatory_restrictions.confidentiality_level"],
    "I2": ["keywords"], "I3": ["distribution_formats", "file_collections", "total_file_count"],
    "I4": ["is_deidentified", "participant_compensation", "data_protection_impacts", "participant_privacy"],
    "I5": ["regulatory_restrictions", "ip_restrictions", "data_protection_impacts", "license_and_use_terms"],
    "I6": ["conforms_to", "conforms_to_schema", "related_datasets"],
    "I7": ["preprocessing_strategies", "cleaning_strategies"],
    "I8": ["collection_timeframes", "data_collectors", "acquisition_methods"],
    "I9": ["maintainers", "updates", "errata", "publisher"],
    "I10": ["instances", "subpopulations"],
    "I11": ["prohibited_uses", "discouraged_uses", "future_use_impacts"],
    "I12": ["was_derived_from", "parent_datasets", "errata", "missing_data_documentation"],
    "I13": ["known_biases", "future_use_impacts"],
    "I14": ["doi", "id", "citation", "version_access"], "I15": ["funders"],
    "I16": ["ethical_reviews", "human_subject_research"], "I17": ["description", "file_collections", "variables"],
    "I18": ["license_and_use_terms"],
}
SEV = {"I13": "high", "I4": "medium", "I5": "medium", "I11": "medium", "I7": "medium", "I8": "medium",
       "I9": "medium", "I12": "medium", "I10": "medium"}
DEFAULT_REC = {
    "I3": "Enumerate the metadata collection files and audio_quality_metrics.tsv and state total_file_count.",
    "I4": "Declare is_deidentified with the method (feature-only release, manual PII review) and any compensation or data-protection assessment.",
    "I5": "Add regulatory_restrictions with a confidentiality level and applicable compliance framework.",
    "I6": "Declare conformance (e.g. data dictionary schema, BIDS) and typed links to related releases.",
    "I7": "Record the versions of b2aiprep, openSMILE, Praat, parselmouth and torchaudio used for this release.",
    "I8": "State the enrollment/collection period and who collected the data.",
    "I9": "Name maintainers and state an update/errata and preservation policy.",
    "I10": "Add demographic distributions (sex, age-group counts, diagnoses) for the 300 participants.",
    "I11": "Add prohibited uses (e.g. re-identification attempts) and a social-impact analysis.",
    "I12": "Add explicit derivation links (raw audio -> features) with agents and missing-data documentation.",
    "I13": "Document known biases (single site, English only, non-verbal excluded, microphone variation) and their effects.",
    "I14": "Record the version-specific DOI in doi for version 1.1.0 or state explicitly which DOI is canonical.",
    "I15": "Keep the caveat; confirm the award number with the funder.",
    "I16": "Keep the caveat; state which board approved the pediatric release.",
    "I17": "List the clinical/questionnaire phenotype files or temper the description.",
    "I18": "Use the PhysioNet access-tier term consistently.",
}


def issue(iid, items, effect, cat, typ, desc, rec=None):
    return {"id": iid, "item_ids": items, "score_effect": effect, "category": cat, "type": typ,
            "severity": SEV.get(iid, "low"), "description": desc,
            "fields_involved": FIELDS[iid],
            "recommendation": rec or DEFAULT_REC.get(iid, "Add the missing documentation.")}


issues = [
    issue("I1", ["Q1"], "lowered", "other", "completeness",
          "Three of fourteen Q1 fields are absent: top-level resources, parent_datasets and regulatory_restrictions.confidentiality_level.",
          "Add a confidentiality classification and, where applicable, parent dataset links."),
    issue("I2", ["Q3"], "lowered", "variables_metadata", "completeness",
          "Only five generic keywords; no modality or feature terms (acoustic features, spectrogram, speech, pediatric voice disorders)."),
    issue("I3", ["Q4"], "lowered", "format_access", "completeness",
          "Only three formats documented; total_file_count absent; files in the metadata collection and audio_quality_metrics.tsv are not enumerated."),
    issue("I4", ["Q8"], "lowered", "privacy_regulatory", "completeness",
          "No is_deidentified flag or deidentification method, compensation, data_protection_impacts or regulatory compliance framework, although a voice re-identification risk is acknowledged."),
    issue("I5", ["Q9"], "lowered", "license_use_terms", "completeness",
          "No regulatory_restrictions (confidentiality level, compliance framework), ip_restrictions or data_protection_impacts accompany the license."),
    issue("I6", ["Q10"], "lowered", "format_access", "completeness",
          "No conforms_to/conforms_to_schema declaration; BIDS is mentioned only as an internal processing step; no typed dataset relationships."),
    issue("I7", ["Q11"], "lowered", "processing_provenance", "completeness",
          "No software versions are given (b2aiprep version explicitly unknown; openSMILE, Praat, parselmouth, torchaudio unversioned and without URLs)."),
    issue("I8", ["Q12"], "lowered", "temporal_version", "completeness",
          "Collection timeframes, data collectors and acquisition methods are absent."),
    issue("I9", ["Q13"], "lowered", "temporal_version", "completeness",
          "No maintainers, update plan, errata or preservation/sustainability commitment."),
    issue("I10", ["Q15"], "lowered", "bias_quality", "completeness",
          "Population described only by age range and age-group labels; no sex/gender, race/ethnicity, diagnostic or per-group counts."),
    issue("I11", ["Q18"], "lowered", "license_use_terms", "completeness",
          "No prohibited or discouraged uses and no social-impact analysis, despite a re-identifiable modality and a pediatric population."),
    issue("I12", ["Q19"], "lowered", "processing_provenance", "completeness",
          "No was_derived_from, parent_datasets, errata, splits or missing_data_documentation; lineage is textual and partial, without agents per activity."),
    issue("I13", ["Q20"], "lowered", "bias_quality", "completeness",
          "No known_biases or future_use_impacts, although single-site recruitment, English-proficiency inclusion, exclusion of non-verbal children and mixed microphones are evident sources of bias."),
    issue("I14", [], "noted_only", "persistent_identifier", "consistency",
          "doi/id hold the latest-version DOI 10.13026/mf9s-5r03 while version is 1.1.0 and the citation uses the version DOI 10.13026/h995-bt35; explained in version_details."),
    issue("I15", [], "noted_only", "source_conflict", "consistency",
          "Grant number 3OT2OD032720-01S1 differs from the RePORTER record (-01S3) and site footer (S2); the record caveats this and keeps the release-stated number."),
    issue("I16", [], "noted_only", "source_conflict", "consistency",
          "Ethics oversight sources differ (USF single IRB revision including the pediatric cohort vs a separate SickKids REB); the record names the SickKids REB and caveats the conflict."),
    issue("I17", [], "noted_only", "variables_metadata", "content_accuracy",
          "The description says detailed demographic, clinical and validated questionnaire data are available, but the phenotype collection lists only demographics.tsv and variables list only four structural identifiers."),
    issue("I18", [], "noted_only", "license_use_terms", "semantic_understanding",
          "License name says 'Registered Access' while terms require credentialed PhysioNet users; the access tier is stated but the wording mixes two PhysioNet tier names."),
]

ctx = normalize_context({})
doc = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": INPUT,
    "project": "VOICE_PEDIATRIC",
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
        "total_points": total, "max_points": maxp, "excluded_max_points": 0,
        "adjusted_max_points": maxp,
        "normalized_percentage": round(total / maxp * 100, 2),
        "fixed_percentage": round(total / maxp * 100, 2),
        "questions_not_applicable": 0,
        "excluded_item_ids": [],
    },
    "categories": cats,
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "Strong on identification, access path, consent/assent and release history; weakest on bias, use restrictions and sustainability.",
            "The record carefully separates pediatric-release facts from the wider multi-site study and caveats source conflicts rather than resolving them silently.",
            "Human-subjects logic holds: involves_human_subjects true with ethical_reviews and informed_consent populated; deidentification is implied (raw audio withheld, manual PII checks) but no method is declared.",
            "Temporal ordering is consistent: v1.0.0 2025-12-17, Synapse notice 2026-03-09, v1.1.0 and issued 2026-05-01; collection dates are absent.",
        ],
        "consistency_checks": {"passed": 5, "failed": 0, "warnings": 4},
        "correctness_validations": {
            "doi_format": "valid: 10.13026 (PhysioNet) for both mf9s-5r03 and h995-bt35; doi field is the latest-version DOI rather than the 1.1.0 DOI",
            "grant_number_format": "valid NIH supplement pattern 3OT2OD032720-01S1; conflicting suffixes in other sources are caveated",
            "rrid_format": "valid: RRID:SCR_007345 (in citation)",
            "url_validity": "plausible: physionet.org, b2ai-voice.org, github.com/sensein/b2aiprep, synapse.org",
        },
    },
    "applicability_context": {},
    "evaluation_scope": {
        "policy": "single_dataset",
        "units": [{"path": "#", "id": "doi:10.13026/mf9s-5r03"}],
        "collection_metadata_inherited": False,
    },
    "metadata": {
        "instrument_sha256": sha(".claude/agents/d4d-rubric20-semantic.md"),
        "evidence_authority_sha256": sha("data/rubric/semantic_evidence_authority_v3.json"),
        "rubric_sha256": sha("data/rubric/rubric20.txt"),
        "input_sha256": sha(INPUT),
        "context_sha256": context_digest(ctx),
    },
}

out = ROOT / OUT
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(out, total, maxp)
