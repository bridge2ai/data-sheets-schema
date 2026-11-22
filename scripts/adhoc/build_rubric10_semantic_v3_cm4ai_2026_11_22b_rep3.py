#!/usr/bin/env python3
"""Serialize one rubric10-semantic v3 evaluation (CM4AI, label 2026-11-22b ... rep3).

Purpose: write the evaluator's manual judgements (made by reading the record) as
the version-3 JSON contract, computing digests from the actual bytes.
Inputs: data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CM4AI_d4d.yaml,
        data/rubric/rubric10.txt, data/rubric/semantic_evidence_authority_v3.json,
        .claude/agents/d4d-rubric10-semantic.md
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep3_evaluation.json
Context: no caller applicability context (empty; conditional predicates unknown).
Date: 2026-11-22. Evaluator: claude-opus-5-5 (Claude Code session).
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest  # noqa: E402

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CM4AI_d4d.yaml"
OUT = "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep3_evaluation.json"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


UNITS = [
    ("#/resources/0", "doi:10.18130/V3/B35XWX", "B35XWX", "March 2025"),
    ("#/resources/1", "doi:10.18130/V3/F3TD5R", "F3TD5R", "June 2025"),
    ("#/resources/2", "doi:10.18130/V3/K7TGEM", "K7TGEM", "October 2025"),
    ("#/resources/3", "doi:10.18130/V3/HIGT4C", "HIGT4C", "June 2026"),
]
VERSIONS = ["1.4", "2.1", "2.1", "2.0"]
CITE_AUTH = ["Clark T; Parker J; Al Manir S; et al.; Ideker T"] * 2 + \
    ["Clark, T; Parker, J; Al Manir, S; et al.; Ideker, T", "Clark T; Parker J; Al Manir S; et al.; Ideker T"]
DESC_Q = [
    "This Beta release includes perturb-seq data in undifferentiated KOLF2.1J iPSCs",
    "A revision of the June 2025 Data Release that adds RGB immunofluorescent images",
    "This Beta release includes Perturb-seq data for MDA-MB-468 breast cancer cells +/- treatment",
    "This Beta release includes Perturb-seq data for MDA-MB-468 breast cancer cells +/- treatment",
]


def row(score, evidence, cited=(), absent=(), considered=(), counts=()):
    return {"score": score, "evidence": evidence,
            "cited": [dict(c) if isinstance(c, dict) else {"path": c} for c in cited],
            "absent": [{"path": a} for a in absent],
            "counts": list(counts), "considered": list(considered)}


def same(score, evidence, cited=(), absent=(), considered=()):
    return [row(score, evidence, cited, absent, considered) for _ in UNITS]


def per(fn):
    return [fn(i, u) for i, u in enumerate(UNITS)]


ITEMS = {}
NOTES = {}

# ---------------- Element 1 ----------------
ITEMS["E1.1"] = per(lambda i, u: row(1, f"doi {u[1][4:]} follows the 10.18130 (University of Virginia Dataverse) prefix; id is the matching doi: URI.",
                                     [{"path": "doi", "quote": u[1][4:]}, {"path": "id"}]))
NOTES["E1.1"] = "Every release dataset carries a well-formed DOI with the plausible 10.18130 Dataverse prefix."
ITEMS["E1.2"] = per(lambda i, u: row(1, f"Title names the {u[3]} release; the description (>200 characters) states which modalities, cell lines and conditions the release contains.",
                                     [{"path": "title"}, {"path": "description", "quote": DESC_Q[i]}]))
NOTES["E1.2"] = "Each release has a specific title and a content-level description; purpose is not restated per release but the contents are explained concretely."
ITEMS["E1.3"] = same(0, "No keywords on this release dataset; collection-level keywords are not inherited.",
                     absent=["keywords"], considered=["title", "description"])
NOTES["E1.3"] = "Keywords exist only at collection level, which the scope policy does not inherit."
ITEMS["E1.4"] = per(lambda i, u: row(1, "No page field, but the release has a hierarchical file_collections structure (collections containing file resources with paths and checksums).",
                                     [{"path": "file_collections"}], absent=["page"]))
NOTES["E1.4"] = "Satisfied through hierarchical file_collections; no landing page field on any release."
ITEMS["E1.5"] = per(lambda i, u: row(0, "No parent_datasets or related_datasets; the release is not linked to the series or to its predecessor by a typed relationship." +
                                     (" The description says it revises the June 2025 release, but only in prose." if i == 1 else ""),
                                     [{"path": "description", "quote": "A revision of the June 2025 Data Release"}] if i == 1 else [],
                                     ["parent_datasets", "related_datasets"], [] if i == 1 else ["description"]))
NOTES["E1.5"] = "No typed parent or related links on any release."

# ---------------- Element 2 ----------------
ITEMS["E2.1"] = per(lambda i, u: row(1, "license states CC BY-NC-SA 4.0, a clear licensing term; no release-level license_and_use_terms or ip_restrictions.",
                                     [{"path": "license", "quote": "CC BY-NC-SA 4.0"}], ["license_and_use_terms", "ip_restrictions"]))
NOTES["E2.1"] = "A named standard licence on each release defines access/use terms; the IP restrictions are collection-level only."
ITEMS["E2.2"] = same(0, "No regulatory, confidentiality or governance-contact information on this release dataset.",
                     absent=["regulatory_restrictions", "data_governance"], considered=["license"])
NOTES["E2.2"] = "Governance contact (collection-level data_governance) is not inherited; releases carry no regulatory classification."
ITEMS["E2.3"] = per(lambda i, u: row(1, "No download_url, but the citation gives the resolvable DOI link to the University of Virginia Dataverse release page.",
                                     [{"path": "citation", "quote": f"https://doi.org/10.18130/V3/{u[2]}, University of Virginia Dataverse"}],
                                     ["download_url"]))
NOTES["E2.3"] = "Platform link through the DOI URL in each citation; no direct download URL."
ITEMS["E2.4"] = per(lambda i, u: row(1, "File resources declare format and MIME type (e.g. ZIP / application/zip" + (", JSON / application/json" if i in (0, 1) else "") + (", HTML / text/html" if i == 1 else "") + ").",
                                     [{"path": "file_collections.resources.format"},
                                      {"path": "file_collections.resources.media_type", "quote": "application/zip"}]))
NOTES["E2.4"] = "Formats and media types are stated per file."
ITEMS["E2.5"] = same(0, "No related_datasets or external_resources on this release; external MassIVE/Figshare/preprint links are collection-level only.",
                     absent=["related_datasets", "external_resources"], considered=["description"])
NOTES["E2.5"] = "No release links to related datasets or external documentation."

# ---------------- Element 3 ----------------
ITEMS["E3.1"] = per(lambda i, u: row(1, "CC BY-NC-SA 4.0 permits reuse with attribution, non-commercial use and share-alike.",
                                     [{"path": "license", "quote": "CC BY-NC-SA 4.0"}]))
NOTES["E3.1"] = "Recognised Creative Commons licence permitting non-commercial reuse."
ITEMS["E3.2"] = per(lambda i, u: row(0, "Formats listed are ZIP containers" + (", JSON RO-Crate metadata" if i in (0, 1) else "") + (" and HTML" if i == 1 else "") +
                                     "; the formats of the data inside the archives (images, sequences, mass-spec tables) and any character encoding are not stated.",
                                     [{"path": "file_collections.resources.format"}], ["file_collections.resources.encoding"],
                                     ["file_collections.resources.media_type"]))
NOTES["E3.2"] = "Only container and metadata formats; data-bearing formats and encodings are unstated."
ITEMS["E3.3"] = per(lambda i, u: row(0, "No conforms_to or conforms_to_schema on the release; RO-Crate is implied only by metadata file names" +
                                     (" and the note that the revision corrects RO-Crate metadata." if i == 1 else "."),
                                     [{"path": "description", "quote": "corrects RO-Crate metadata"}] if i == 1 else [],
                                     ["conforms_to", "conforms_to_schema"], ["file_collections.resources.name"]))
NOTES["E3.3"] = "Collection-level RO-Crate conformance is not inherited; releases state none."
ITEMS["E3.4"] = same(0, "No variable-level metadata.", absent=["variables"], considered=["file_collections"])
NOTES["E3.4"] = "No variables anywhere in the release datasets."
ITEMS["E3.5"] = same(0, "No intended, prohibited or discouraged uses on this release dataset.",
                     absent=["intended_uses", "prohibited_uses", "discouraged_uses"], considered=["license"])
NOTES["E3.5"] = "Use guidance is collection-level only."

# ---------------- Element 4 ----------------
ITEMS["E4.1"] = same(0, "No ethics review, human-subjects statement, data-protection impact or governance contact on this release.",
                     absent=["ethical_reviews", "human_subject_research", "data_protection_impacts", "data_governance"])
NOTES["E4.1"] = "Applicability unknown (no caller context); the release carries no oversight documentation."
ITEMS["E4.2"] = same(0, "No deidentification statement on this release.", absent=["is_deidentified"])
NOTES["E4.2"] = "Applicability unknown; no deidentification documentation at release level."
ITEMS["E4.3"] = same(0, "No participant privacy or re-identification risk statement.", absent=["participant_privacy"])
NOTES["E4.3"] = "Applicability unknown; nothing documented."
ITEMS["E4.4"] = same(0, "No informed consent statement (e.g. for the donor-derived cell lines).", absent=["informed_consent"])
NOTES["E4.4"] = "Applicability unknown; nothing documented."
ITEMS["E4.5"] = same(0, "No at-risk population or compensation statement.", absent=["at_risk_populations", "participant_compensation"])
NOTES["E4.5"] = "Applicability unknown; nothing documented."

# ---------------- Element 5 ----------------
ITEMS["E5.1"] = per(lambda i, u: row(0, "The description names the cell lines and treatment conditions, but no subpopulation characteristics (line origin, donor characteristics, differentiation state definitions) are given at release level.",
                                     [{"path": "description", "quote": "MDA-MB-468"}], ["subpopulations", "subsets"], ["file_collections.description"]))
NOTES["E5.1"] = "Naming cell lines identifies subsets but does not describe their characteristics; the subpopulations block is collection-level."
_counts = {0: ("11,739 targeted genes", "file_collections.description"),
           1: ("464 proteins of interest", "file_collections.description"),
           2: ("464 proteins of interest", "file_collections.description")}
ITEMS["E5.2"] = per(lambda i, u: row(1, f"File-collection description reports a count ({_counts[i][0]}); total_file_count is also given.",
                                     [{"path": _counts[i][1], "quote": _counts[i][0]}, {"path": "total_file_count"}], ["instances"])
                    if i in _counts else
                    row(0, "Only total_file_count (10 ZIP archives) is reported; no count of samples, images, proteins or cells for the current release.",
                        [{"path": "total_file_count"}], ["instances"], ["description", "file_collections.description"]))
NOTES["E5.2"] = "Older releases give protein/gene counts in file descriptions; the current June 2026 release gives only a file count."
ITEMS["E5.3"] = same(0, "No variables, tabular flag or split/subpopulation flags.",
                     absent=["variables", "is_tabular", "subsets"], considered=["file_collections"])
NOTES["E5.3"] = "No variable or structural flags on any release."
ITEMS["E5.4"] = per(lambda i, u: row(1, "Description states the data topics: Perturb-seq, SEC-MS" + (", AP-MS" if i == 3 else "") +
                                     " and IF imaging in breast cancer cells (+/- paclitaxel/vorinostat) and iPSC-derived cells.",
                                     [{"path": "description", "quote": DESC_Q[i]}], ["instances"]))
NOTES["E5.4"] = "Topics, cell types and treatment conditions are clear in each description."
ITEMS["E5.5"] = per(lambda i, u: row(0, "No anomalies, sampling or missing-data documentation on the release." +
                                     (" source_caveats concern the record's capture (first 10 of 21 files), not data quality." if i == 1 else ""),
                                     [], ["anomalies", "sampling_strategies", "missing_data_documentation"], ["source_caveats"]))
NOTES["E5.5"] = "No data quality documentation at release level."

# ---------------- Element 6 ----------------
ITEMS["E6.1"] = per(lambda i, u: row(1, f"version is {VERSIONS[i]}; source_caveats disclose that the Dataverse citation shows a different major label.",
                                     [{"path": "version", "quote": VERSIONS[i]}, {"path": "source_caveats", "quote": f"Version {VERSIONS[i]}"}]))
NOTES["E6.1"] = "Version numbers present; header/citation discrepancy is transparently noted."
ITEMS["E6.2"] = same(0, "No version_access on the release; how to reach other versions is documented only at collection level.",
                     absent=["version_access"], considered=["citation", "version"])
NOTES["E6.2"] = "No per-release version access method."
ITEMS["E6.3"] = per(lambda i, u: row(1, "Description lists the changes in this revision: adds RGB IF images, corrects RO-Crate metadata, changes naming conventions.",
                                     [{"path": "description", "quote": "corrects RO-Crate metadata, and changes naming conventions"}], ["errata", "updates"])
                    if i == 1 else
                    row(0, "Description labels the release (historical/superseded/current) but gives no change log or errata.",
                        [], ["errata", "updates"], ["description"]))
NOTES["E6.3"] = "Only the June 2025 release documents what changed."
ITEMS["E6.4"] = same(0, "No update schedule on the release dataset; the quarterly schedule is collection-level only.",
                     absent=["updates"], considered=["description"])
NOTES["E6.4"] = "No update frequency at release level."
_prov = {0: ("file_collections.description", "in the Lundberg Lab at Stanford University", "File-collection descriptions name the generating labs and include a raw-sequence collection."),
         1: ("file_collections.description", "with per-condition provenance graph files", "Images collection ships per-condition provenance graphs; description states the revision's derivation."),
         2: ("file_collections.resources.description", "in the Nevan Krogan laboratory", "SEC-MS archives are described by generating laboratory and treatment.")}
ITEMS["E6.5"] = per(lambda i, u: row(1, _prov[i][2], [{"path": _prov[i][0], "quote": _prov[i][1]}], ["was_derived_from", "raw_data_sources"])
                    if i in _prov else
                    row(0, "The current release lists only archive file names (e.g. cm4ai_perturb-seq_KOLF2_raw_sra.zip); no provenance, derivation or raw-source description.",
                        [{"path": "file_collections.resources.name", "quote": "cm4ai_perturb-seq_KOLF2_raw_sra.zip"}],
                        ["was_derived_from", "raw_data_sources", "notes"], ["description"]))
NOTES["E6.5"] = "Earlier releases carry lab-level provenance; the current release carries none."

# ---------------- Element 7 ----------------
ITEMS["E7.1"] = same(0, "No purposes on the release dataset.", absent=["purposes"], considered=["description"])
NOTES["E7.1"] = "Purpose is collection-level only."
ITEMS["E7.2"] = same(0, "No tasks on the release dataset.", absent=["tasks"], considered=["description"])
NOTES["E7.2"] = "No tasks anywhere at release level."
ITEMS["E7.3"] = same(0, "No funders on the release dataset.", absent=["funders"])
NOTES["E7.3"] = "NIH funding is recorded only at collection level."
ITEMS["E7.4"] = same(0, "No award numbers on the release dataset.", absent=["funders"])
NOTES["E7.4"] = "Grant numbers are collection-level only."
ITEMS["E7.5"] = per(lambda i, u: row(0, "No creators list; the citation names four authors and truncates the rest with 'et al.'; no acknowledgements.",
                                     [{"path": "citation", "quote": CITE_AUTH[i]}], ["creators", "funders"]))
NOTES["E7.5"] = "Truncated citation authorship is not a creators record."

# ---------------- Element 8 ----------------
_coll = {0: ("file_collections.description", "immunofluorescence-based staining (ICC-IF) and confocal microscopy in the Lundberg Lab"),
         2: ("file_collections.resources.description", "in the Nevan Krogan laboratory at the University of California San Francisco")}
ITEMS["E8.1"] = per(lambda i, u: row(1, "File descriptions state the collection procedure and the laboratory setting.",
                                     [{"path": _coll[i][0], "quote": _coll[i][1]}], ["collection_mechanisms"])
                    if i in _coll else
                    row(0, "Only modality names; no collection procedure, setting or timeframe on this release.",
                        [{"path": "description", "quote": DESC_Q[i]}], ["collection_mechanisms"], ["file_collections.description"]))
NOTES["E8.1"] = "March and October 2025 releases describe procedure/setting; June 2025 and June 2026 do not."
ITEMS["E8.2"] = per(lambda i, u: row(1, "The description lists the acquisition methods (Perturb-seq, SEC-MS" + (", AP-MS" if i == 3 else "") + ", immunofluorescence imaging).",
                                     [{"path": "description", "quote": "SEC-MS data"}], ["acquisition_methods", "raw_data_sources"]))
NOTES["E8.2"] = "Acquisition methods are named per release."
ITEMS["E8.3"] = same(0, "No preprocessing, cleaning, labeling, annotation or imputation documentation on the release.",
                     absent=["preprocessing_strategies", "cleaning_strategies", "labeling_strategies", "annotation_analyses",
                             "machine_annotation_tools", "imputation_protocols"], considered=["description"])
NOTES["E8.3"] = "The MuSIC pipeline is collection-level and, by the record's own caveat, did not produce this release."
ITEMS["E8.4"] = same(0, "No software that produced or transformed the released data is named; ro-crate metadata files are packaging/metadata outputs (role c).",
                     absent=["preprocessing_strategies", "machine_annotation_tools", "external_resources"],
                     considered=["file_collections.resources.name"])
NOTES["E8.4"] = "Nothing named at release level; collection-level FAIRSCAPE is packaging (c) and MuSIC is a pipeline whose outputs are not in the release (e)."
ITEMS["E8.5"] = same(0, "No external resources, standards or imputation protocol on the release.",
                     absent=["external_resources", "conforms_to", "imputation_protocols"], considered=["description"])
NOTES["E8.5"] = "No external documentation linked per release."

# ---------------- Element 9 ----------------
ITEMS["E9.1"] = same(0, "No known_limitations on the release; 'Beta' in the title is not a limitation statement.",
                     absent=["known_limitations"], considered=["title", "description"])
NOTES["E9.1"] = "Limitations are collection-level only."
ITEMS["E9.2"] = same(0, "No bias documentation on the release.", absent=["known_biases", "future_use_impacts"])
NOTES["E9.2"] = "Collection-level biases are also uncategorized."
ITEMS["E9.3"] = same(0, "No anomalies on the release.", absent=["anomalies"], considered=["source_caveats"])
NOTES["E9.3"] = "No data anomalies documented."
ITEMS["E9.4"] = same(0, "No sensitive-element or content-warning statement on the release.",
                     absent=["sensitive_elements", "content_warnings"])
NOTES["E9.4"] = "Not addressed."
ITEMS["E9.5"] = same(0, "No ethical review or future-use impact analysis on the release.",
                     absent=["ethical_reviews", "future_use_impacts"])
NOTES["E9.5"] = "Collection-level ethics contacts are not inherited and are contacts, not an impact analysis."

# ---------------- Element 10 ----------------
ITEMS["E10.1"] = per(lambda i, u: row(1, "No publisher field, but the citation names the University of Virginia Dataverse, a recognised institutional repository.",
                                      [{"path": "citation", "quote": "University of Virginia Dataverse"}], ["publisher"]))
NOTES["E10.1"] = "Recognised platform identified through the citation."
ITEMS["E10.2"] = per(lambda i, u: row(1, "Recommended citation string with DOI URL and a DOI field.",
                                      [{"path": "citation", "quote": f"https://doi.org/10.18130/V3/{u[2]}"}, {"path": "doi"}]))
NOTES["E10.2"] = "Citation and DOI present for every release."
ITEMS["E10.3"] = same(0, "No conforms_to statement on the release.", absent=["conforms_to"], considered=["file_collections.resources.name"])
NOTES["E10.3"] = "RO-Crate conformance is collection-level only."
ITEMS["E10.4"] = per(lambda i, u: row(0, "No page or external documentation links" +
                                      ("; an HTML datasheet file is packaged in the release but not linked." if i == 1 else "."),
                                      [{"path": "file_collections.resources.name", "quote": "release-ro-crate-datasheet.html"}] if i == 1 else [],
                                      ["external_resources", "page"]))
NOTES["E10.4"] = "No outreach or documentation links per release."
ITEMS["E10.5"] = same(0, "No related_datasets with typed relationships.", absent=["related_datasets"], considered=["description"])
NOTES["E10.5"] = "Releases are not typed as versions of one another."

ISSUES = [
    {"item_ids": ["E1.5", "E2.5", "E6.2", "E10.5"], "category": "temporal_version", "type": "completeness",
     "description": "The four Dataverse releases are versions of one series, yet none carries parent_datasets, related_datasets or version_access linking it to the series or its predecessor; the June 2025 revision relation exists only in prose."},
    {"item_ids": ["E1.3"], "category": "variables_metadata", "type": "completeness",
     "description": "Release datasets carry no keywords; discovery terms exist only at collection level, which is not inherited."},
    {"item_ids": ["E2.2", "E4.1", "E4.2", "E4.3", "E9.4"], "category": "privacy_regulatory", "type": "completeness",
     "description": "No release states regulatory/confidentiality status, governance contact, human-subjects status, deidentification, privacy or sensitivity; these appear only at collection level. With no caller context these items remain applicable."},
    {"item_ids": ["E4.4", "E4.5", "E9.5"], "category": "consent_ethics", "type": "completeness",
     "description": "No release documents consent (e.g. for donor-derived iPSC lines), at-risk populations, compensation, ethical review or downstream social impact."},
    {"item_ids": ["E3.2", "E3.3", "E10.3"], "category": "format_access", "type": "completeness",
     "description": "Release formats are ZIP containers and RO-Crate JSON/HTML metadata only; data-bearing formats and encodings are unstated, and no release states schema/standard conformance (RO-Crate is implied by file names only)."},
    {"item_ids": ["E3.4", "E5.3"], "category": "variables_metadata", "type": "completeness",
     "description": "No variable-level metadata, tabular flag or split/subpopulation flags in any release."},
    {"item_ids": ["E3.5"], "category": "license_use_terms", "type": "completeness",
     "description": "No release-level intended, prohibited or discouraged uses."},
    {"item_ids": ["E5.1", "E5.2"], "category": "count_size", "type": "completeness",
     "description": "Cell lines are named but not characterized at release level, and the current June 2026 release reports only a file count (10), no counts of samples, images, proteins or genes."},
    {"item_ids": ["E5.5", "E9.1", "E9.2", "E9.3"], "category": "bias_quality", "type": "completeness",
     "description": "No release documents data quality, missing data, limitations, categorized biases or anomalies."},
    {"item_ids": ["E6.3", "E6.4", "E6.5"], "category": "processing_provenance", "type": "consistency",
     "description": "Change descriptions and provenance are uneven across releases: only June 2025 lists its changes, no release states an update schedule, and the current June 2026 release lists archive names without any provenance or raw-source description."},
    {"item_ids": ["E7.1", "E7.2", "E7.3", "E7.4", "E7.5"], "category": "attribution", "type": "completeness",
     "description": "Purpose, tasks, funders, award numbers and creators are recorded only at collection level; each release offers only a citation truncated with 'et al.'."},
    {"item_ids": ["E8.1", "E8.3", "E8.4", "E8.5"], "category": "processing_provenance", "type": "completeness",
     "description": "June 2025 and June 2026 releases name modalities without collection procedures or settings; no release documents processing, software that transformed the data, external resources or imputation."},
    {"item_ids": ["E10.4"], "category": "format_access", "type": "completeness",
     "description": "No release links a landing page, tutorial or documentation; the June 2025 HTML datasheet is packaged but not linked."},
    {"item_ids": [], "score_effect": "noted_only", "category": "scope_drift", "type": "semantic_understanding",
     "description": "The record has no Dataset/DatasetCollection declaration and four resources, so it is scored as a collection of four release datasets with minimum-per-item aggregation. Its rich top-level documentation (purposes, funders with OT2OD032742/U54HG012513 awards, governance, limitations, RO-Crate conformance, collection mechanisms) is not inherited, which is the main driver of the low score."},
    {"item_ids": [], "score_effect": "noted_only", "category": "temporal_version", "type": "consistency",
     "description": "Each release's page-header version (1.4, 2.1, 2.1, 2.0) differs from the citation's V1/V2 label, and the June 2026 release date conflicts with a 'Released on: June 17, 2025' display; the record discloses both discrepancies in source_caveats."},
    {"item_ids": [], "score_effect": "noted_only", "category": "count_size", "type": "consistency",
     "description": "Protein counts for IF images differ by release (563, 464) and from the collection page (523); the record discloses this rather than reconciling it."},
    {"item_ids": [], "score_effect": "noted_only", "category": "privacy_regulatory", "type": "content_accuracy",
     "description": "At collection level, human_subject_research.involves_human_subjects is false while samples are described as de-identified human cell lines; consistent, but is_deidentified gives no method beyond 'cannot be matched to a human subject'. Not scored because collection metadata is not inherited."},
]
EXTRA = [
    ("high", ["parent_datasets", "related_datasets", "version_access"],
     "Give each release a typed relationship to the series (parent) and to the release it supersedes or revises, and state how to reach other versions."),
    ("medium", ["keywords"], "Add release-level keywords covering modality, cell line and treatment."),
    ("medium", ["regulatory_restrictions", "data_governance", "human_subject_research", "is_deidentified", "participant_privacy", "sensitive_elements"],
     "Record each release's governance contact, human-subjects status, deidentification basis and sensitivity, or declare applicability context explicitly."),
    ("medium", ["informed_consent", "at_risk_populations", "participant_compensation", "ethical_reviews", "future_use_impacts"],
     "State the consent basis of the donor-derived cell lines and an ethical/social-impact review per release, or declare non-applicability through caller context."),
    ("medium", ["file_collections.resources.format", "file_collections.resources.encoding", "conforms_to"],
     "Describe the formats inside each ZIP (e.g. TIFF/PNG images, FASTQ/SRA, mass-spec tables) and state RO-Crate conformance per release."),
    ("high", ["variables", "is_tabular", "subsets"], "Provide a data dictionary and structural flags for each release's tabular outputs."),
    ("medium", ["intended_uses", "prohibited_uses", "discouraged_uses"], "Attach intended and prohibited uses to each release."),
    ("high", ["subpopulations", "instances", "total_file_count"],
     "Characterize the cell lines per release and report sample, image, protein and gene counts for the current release."),
    ("high", ["anomalies", "missing_data_documentation", "known_limitations", "known_biases"],
     "Document per-release limitations (e.g. embargoed Perturb-seq data), categorized biases and quality issues."),
    ("medium", ["errata", "updates", "was_derived_from", "raw_data_sources"],
     "Give every release a change log, the update schedule, and a provenance description of each archive."),
    ("high", ["purposes", "tasks", "funders", "creators"],
     "Carry purpose, funders/award numbers and the full creator list on each release (or declare explicit Dataset scope)."),
    ("high", ["collection_mechanisms", "preprocessing_strategies", "external_resources", "imputation_protocols"],
     "Describe collection procedures and the processing software that produced each released archive, with links to external protocols."),
    ("low", ["page", "external_resources"], "Link each release's landing page and its HTML datasheet or tutorials."),
    ("medium", ["resources", "conforms_to_class"],
     "Declare the top-level class (Dataset or DatasetCollection) so the intended scoring scope is explicit."),
    ("low", ["version", "citation", "source_caveats"], "Reconcile version labels with Dataverse citation versions where possible."),
    ("low", ["file_collections.description", "source_caveats"], "State which protein count applies to which release snapshot."),
    ("low", ["human_subject_research", "is_deidentified"], "State the deidentification basis (commercial cell lines, no linkage) explicitly as a method."),
]
for issue, (sev, fields, rec) in zip(ISSUES, EXTRA, strict=True):
    issue.setdefault("score_effect", "lowered")
    issue.update({"severity": sev, "fields_involved": fields, "recommendation": rec})

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


def main():
    import yaml
    from data_sheets_schema.judge_contract import evaluation_contract
    spec = yaml.safe_load((ROOT / "data/rubric/rubric10.txt").read_bytes())
    rules = evaluation_contract("rubric10", spec, {}, {"id": "build"})["items"]
    elements, total = [], 0
    for eid, ename, edesc in ELEMENTS:
        subs, escore = [], 0
        for n in range(1, 6):
            key = f"E{eid}.{n}"
            rule = rules[key]
            rows = ITEMS[key]
            for r, u in zip(rows, UNITS):
                r["path"] = u[0]
            rows = [{"path": r["path"], **{k: v for k, v in r.items() if k != "path"}} for r in rows]
            score = min(r["score"] for r in rows)
            escore += score
            subs.append({
                "name": rule["name"], "score": score,
                "evidence": " | ".join(f"{r['path']}: {r['evidence']}" for r in rows),
                "quality_note": NOTES[key], "applicable": True,
                "applicability_status": rule["status"], "applicability_evidence": rule["evidence"],
                "unit_scores": rows, "item_id": key,
            })
        total += escore
        elements.append({"id": eid, "name": ename, "description": edesc, "sub_elements": subs,
                         "element_score": escore, "element_max": 5})
    result = {
        "rubric": "rubric10-semantic", "version": "3.0",
        "d4d_file": INPUT, "project": "CM4AI", "method": "claudecode_agent",
        "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3",
        "evaluation_timestamp": "2026-11-22T00:00:00Z",
        "model": {"name": "claude-opus-5-5", "evaluator_model": "claude-opus-5-5", "temperature": None,
                  "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
                  "evaluation_type": "semantic_llm_judge"},
        "overall_score": {"total_points": total, "max_points": 50, "excluded_max_points": 0,
                          "adjusted_max_points": 50, "normalized_percentage": round(100 * total / 50, 1),
                          "fixed_percentage": round(100 * total / 50, 1), "sub_elements_not_applicable": 0,
                          "excluded_item_ids": []},
        "elements": elements,
        "semantic_analysis": {
            "issues_detected": ISSUES,
            "semantic_insights": [
                "Scored as an undeclared collection of four Dataverse releases; item score is the minimum across releases, and collection-level fields are not inherited.",
                "The June 2026 (current) release is the thinnest unit: archive names, MD5s and a file count, with no per-file descriptions; it sets the minimum on E5.2, E6.5 and E8.1.",
                "Identifiers, licence, citation, formats and version labels are consistently strong in every release.",
                "The collection-level documentation (purposes, NIH OT2OD032742 funding, governance contact, limitations, RO-Crate conformance) is substantially richer than any release unit.",
            ],
            "consistency_checks": {"passed": 5, "failed": 1, "warnings": 3},
            "correctness_validations": {
                "doi_format": "valid: 10.18130/V3/B35XWX, F3TD5R, K7TGEM, HIGT4C (University of Virginia Dataverse prefix)",
                "grant_number_format": "not_applicable_at_unit_level: release units carry no awards; collection-level 1OT2OD032742-01 and 5U54HG012513-02 match NIH patterns",
                "rrid_format": "not_present_at_unit_level: collection-level cell-line RRIDs (CVCL_0419, CVCL_B5P3) are Cellosaurus RRIDs",
                "url_validity": "valid: doi.org URLs in every release citation are well formed",
            },
        },
        "applicability_context": {},
        "evaluation_scope": {"policy": "minimum_per_item_across_all_resource_datasets_v1",
                             "units": [{"path": u[0], "id": u[1]} for u in UNITS],
                             "collection_metadata_inherited": False},
        "metadata": {
            "instrument_sha256": sha(".claude/agents/d4d-rubric10-semantic.md"),
            "evidence_authority_sha256": sha("data/rubric/semantic_evidence_authority_v3.json"),
            "rubric_sha256": sha("data/rubric/rubric10.txt"),
            "input_sha256": sha(INPUT),
            "context_sha256": context_digest({}),
        },
    }
    out = ROOT / OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(out, total)


if __name__ == "__main__":
    main()
