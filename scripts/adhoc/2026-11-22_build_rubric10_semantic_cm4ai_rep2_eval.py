#!/usr/bin/env python3
"""Serialize one rubric10-semantic v3 evaluation of a single D4D record.

Purpose: write the evaluator's (claude-opus-5-5) per-resource judgements for
  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CM4AI_d4d.yaml
  under the general-context instrument v3 (.claude/agents/d4d-rubric10-semantic.md).
Inputs: that D4D record (hashed only; judgements below are the evaluator's),
  data/rubric/rubric10.txt, data/rubric/semantic_evidence_authority_v3.json,
  the agent definition. No caller applicability context (empty => unknown).
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep2_evaluation.json
Date: 2026-11-22. Serves the caller's single-record evaluation request.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import context_digest, dataset_units, load_document  # noqa: E402
from data_sheets_schema.judge_contract import evaluation_contract  # noqa: E402

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CM4AI_d4d.yaml"
OUTPUT = "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep2_evaluation.json"
DEFINITION = ".claude/agents/d4d-rubric10-semantic.md"
RUBRIC = "data/rubric/rubric10.txt"
AUTHORITY = "data/rubric/semantic_evidence_authority_v3.json"
MODEL = "claude-opus-5-5"


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


document, input_sha = load_document(ROOT / INPUT)
units = [{"path": p, "id": u.get("id")} for p, u in dataset_units(document)]
P = [u["path"] for u in units]
assert len(P) == 4, P
CONTEXT = {}
spec = yaml.safe_load((ROOT / RUBRIC).read_bytes())
rules = evaluation_contract("rubric10", spec, CONTEXT, {"id": "build"})["items"]

LBL = ["March 2025 release", "June 2025 release", "October 2025 release", "June 2026 release"]


def r(score, evidence, cited=(), absent=(), considered=(), counts=()):
    return {"score": score, "evidence": evidence,
            "cited": [c if isinstance(c, dict) else {"path": c} for c in cited],
            "absent": [{"path": a} for a in absent], "counts": list(counts),
            "considered": list(considered)}


def same(score, evidence, **kw):
    """Same judgement for all four release units."""
    return [r(score, f"{LBL[i]}: {evidence}", **kw) for i in range(4)]


FC_DESC = "file_collections.resources.description"
ITEMS = {}
NOTES = {}
REASONS = {}

# ---------------- Element 1 ----------------
dois = ["10.18130/V3/B35XWX", "10.18130/V3/F3TD5R", "10.18130/V3/K7TGEM", "10.18130/V3/HIGT4C"]
ITEMS["E1.1"] = [r(1, f"{LBL[i]}: doi {dois[i]} is a well-formed DOI with the University of Virginia Dataverse prefix 10.18130; id repeats it as doi:{dois[i]}.",
                   cited=[{"path": "doi", "quote": dois[i]}, "id"]) for i in range(4)]
NOTES["E1.1"] = "Every release unit carries a valid, plausible Dataverse DOI."
titles = ["March 2025 Data Release (Beta)", "June 2025 Data Release (Beta)", "October 2025 Data Release (Beta)", "June 2026 Data Release (Beta)"]
dq = ["It includes Perturb-seq data in undifferentiated KOLF2.1J iPSCs",
      "adding RGB immunofluorescent images, correcting RO-Crate metadata and changing naming conventions",
      "Its external Perturb-seq data links are marked embargoed.",
      "AP-MS data for treated MDA-MB-468 cells"]
ITEMS["E1.2"] = [r(1, f"{LBL[i]}: specific title ('{titles[i]}') and a >200-character description naming modalities, cell lines and treatment conditions of the release; purpose is not restated at release level but the content is actionable.",
                   cited=[{"path": "title", "quote": titles[i]}, {"path": "description", "quote": dq[i]}]) for i in range(4)]
NOTES["E1.2"] = "Release titles and descriptions are specific about content; motivation sits only at collection level."
ITEMS["E1.3"] = same(0, "no keywords at release level; the collection's 29 keywords are not inherited under the collection policy.", absent=["keywords"])
ITEMS["E1.4"] = [r(1, f"{LBL[i]}: no page URL, but the release has a hierarchical file_collections structure listing its member files (and a DOI that resolves to its Dataverse landing page).",
                   cited=["file_collections"], absent=["page"]) for i in range(4)]
NOTES["E1.4"] = "Credited for hierarchical file_collections structure; no release-level page URL."
ITEMS["E1.5"] = same(0, "no parent_datasets or related_datasets links; the series relationship between releases is described only in prose source_caveats.",
                     absent=["parent_datasets", "related_datasets"], considered=["source_caveats"])

# ---------------- Element 2 ----------------
ITEMS["E2.1"] = same(1, "license 'CC BY-NC-SA 4.0' is a clear, recognised licensing term defining access and reuse conditions; no license_and_use_terms or ip_restrictions block at release level.",
                     cited=[{"path": "license", "quote": "CC BY-NC-SA 4.0"}], absent=["license_and_use_terms", "ip_restrictions"])
NOTES["E2.1"] = "Licensing term present in every release; detailed terms and copyright holders only at collection level."
ITEMS["E2.2"] = same(0, "no regulatory_restrictions, confidentiality classification or governance committee contact at release level.",
                     absent=["regulatory_restrictions", "data_governance"])
ITEMS["E2.3"] = [r(0, f"{LBL[i]}: no download_url; only a bare DOI identifies the release, and no platform is named in this unit.",
                   absent=["download_url", "publisher"], considered=["doi"]) for i in range(3)] + [
    r(1, "June 2026 release: no download_url, but its citation gives the resolvable platform link https://doi.org/10.18130/V3/HIGT4C on the University of Virginia Dataverse.",
      cited=[{"path": "citation", "quote": "https://doi.org/10.18130/V3/HIGT4C"}], absent=["download_url"])]
fcount = [len(u["file_collections"][0]["resources"]) for _, u in dataset_units(document)]
ITEMS["E2.4"] = [r(1, f"{LBL[i]}: each of the {fcount[i]} listed files has a format and MIME type (ZIP/application/zip, JSON/application/json, HTML/text/html).",
                   cited=["file_collections.resources.format", "file_collections.resources.media_type"],
                   counts=[{"path": "/file_collections/0/resources", "claimed": fcount[i]}]) for i in range(4)]
NOTES["E2.4"] = "File-level formats and media types are given for every listed file."
ITEMS["E2.5"] = same(0, "no related_datasets or external_resources at release level (the MassIVE/Figshare links and publications are recorded only at collection level).",
                     absent=["related_datasets", "external_resources"])

# ---------------- Element 3 ----------------
ITEMS["E3.1"] = same(1, "CC BY-NC-SA 4.0 permits sharing and adaptation with attribution, non-commercial and share-alike conditions.",
                     cited=[{"path": "license", "quote": "CC BY-NC-SA 4.0"}], absent=["license_and_use_terms"])
NOTES["E3.1"] = "A standard reuse licence is attached to every release."
ITEMS["E3.2"] = same(0, "file formats are packaging/container types (ZIP archives, JSON metadata, HTML); the formats of the image, mass-spectrometry and sequencing payloads inside the archives are not stated and no character encoding is given.",
                     cited=["file_collections.resources.format"], absent=["encoding"])
rocrate_q = ["RO-Crate metadata for raw sequence data", "Release RO-Crate with pointers to sub-RO-Crates."]
ITEMS["E3.3"] = [r(1, f"{LBL[i]}: file descriptions state that the release carries RO-Crate metadata, a recognised packaging/metadata standard.",
                   cited=[{"path": FC_DESC, "quote": rocrate_q[i]}], absent=["conforms_to", "conforms_to_schema"]) for i in range(2)] + [
    r(0, f"{LBL[i]}: no conforms_to statement and no file description naming a schema or standard (the metadata archive cm4ai_release_metadata.zip is undescribed).",
      absent=["conforms_to", "conforms_to_schema"], considered=["file_collections.resources.name"]) for i in (2, 3)]
ITEMS["E3.4"] = same(0, "no variable-level metadata.", absent=["variables"])
ITEMS["E3.5"] = same(0, "no intended, prohibited or discouraged uses at release level (they are recorded only for the collection).",
                     absent=["intended_uses", "prohibited_uses", "discouraged_uses"])

# ---------------- Element 4 ----------------
ITEMS["E4.1"] = same(0, "no ethical_reviews, human_subject_research or data_protection_impacts at release level; the collection's ethics contacts and 'Human Subjects: No' statement are not inherited.",
                     absent=["ethical_reviews", "human_subject_research", "data_protection_impacts"])
ITEMS["E4.2"] = same(0, "no is_deidentified statement at release level.", absent=["is_deidentified"])
ITEMS["E4.3"] = same(0, "no participant_privacy or re-identification risk assessment at release level.", absent=["participant_privacy"])
ITEMS["E4.4"] = same(0, "no informed_consent statement (nor a statement that consent is inapplicable to cell-line data) at release level.", absent=["informed_consent"])
ITEMS["E4.5"] = same(0, "no at_risk_populations or participant_compensation documentation.", absent=["at_risk_populations", "participant_compensation"])
for k in ("E4.3", "E4.4", "E4.5"):
    REASONS[k] = None  # linked to the ethics issue below

# ---------------- Element 5 ----------------
ITEMS["E5.1"] = same(0, "no subpopulations entry; the description names cell lines, differentiation states and drug treatments but does not characterise them (line origin, subtype, donor) at release level.",
                     absent=["subpopulations"], considered=["description"])
cnt_q = ["11,739 targeted genes", "464 proteins of interest", "11,739 targeted genes"]
ITEMS["E5.2"] = [r(1, f"{LBL[i]}: no instances block, but file descriptions give specific counts ('{cnt_q[i]}'; IF images of 563/464 proteins).",
                   cited=[{"path": FC_DESC, "quote": cnt_q[i]}], absent=["instances"]) for i in range(3)] + [
    r(0, "June 2026 release: no instances and no counts of samples, proteins, genes or images; only file_count (10) counts files, not instances.",
      absent=["instances"], considered=["file_collections.file_count", "description"])]
ITEMS["E5.3"] = same(0, "no variables, is_tabular flag or subset split/subpopulation flags.", absent=["variables", "is_tabular", "subsets"])
topics = ["MDA-MB-468 breast cancer cells in the presence and absence of chemotherapy",
          "IF images in MDA-MB-468 cells in the presence and absence of vorinostat and paclitaxel",
          "Perturb-seq data for MDA-MB-468 breast cancer cells with or without treatment",
          "SEC-MS data for MDA-MB-468 cells with or without treatment"]
ITEMS["E5.4"] = [r(1, f"{LBL[i]}: description names the biological topics and conditions represented (breast cancer cell line with drug treatment, iPSC differentiation states, PPI/localization/perturbation modalities).",
                   cited=[{"path": "description", "quote": topics[i]}], absent=["instances"]) for i in range(4)]
NOTES["E5.4"] = "Conditions and topics are named in every release description, not in an instances block."
ITEMS["E5.5"] = same(0, "no anomalies, sampling_strategies or missing_data_documentation; release caveats concern metadata (version header vs citation) rather than data quality.",
                     absent=["anomalies", "sampling_strategies", "missing_data_documentation"], considered=["source_caveats"])

# ---------------- Element 6 ----------------
vers = ["1.4", "2.1", "2.1", "2.0"]
ITEMS["E6.1"] = [r(1, f"{LBL[i]}: version '{vers[i]}' (Dataverse dataset version; source_caveats note the citation reads V{vers[i][0]}).",
                   cited=[{"path": "version", "quote": vers[i]}], considered=["source_caveats"]) for i in range(4)]
NOTES["E6.1"] = "Each release carries a Dataverse version number; header/citation version mismatches are disclosed in source_caveats."
ITEMS["E6.2"] = same(0, "no version_access at release level; the version list and latest_version_doi exist only at collection level.", absent=["version_access"])
ITEMS["E6.3"] = [r(0, f"{LBL[i]}: no errata or updates; source_caveats only say the release is superseded, without describing changes.",
                   absent=["errata", "updates"], considered=["source_caveats"]) for i in (0,)] + [
    r(1, "June 2025 release: description states the changes in this revision ('adding RGB immunofluorescent images, correcting RO-Crate metadata and changing naming conventions').",
      cited=[{"path": "description", "quote": "adding RGB immunofluorescent images, correcting RO-Crate metadata and changing naming conventions"}],
      absent=["errata", "updates"])] + [
    r(0, f"{LBL[i]}: no errata or updates; no change description relative to the previous release.",
      absent=["errata", "updates"], considered=["source_caveats", "description"]) for i in (2, 3)]
ITEMS["E6.4"] = same(0, "no updates/frequency at release level (quarterly schedule recorded only for the collection).", absent=["updates"])
prov = {0: "generated in the Nevan Krogan laboratory at the University of California San Francisco",
        2: "generated in the Nevan Krogan laboratory at the University of California San Francisco"}
ITEMS["E6.5"] = [
    r(1, "March 2025 release: file descriptions give the source laboratories of the SEC-MS (Krogan Lab, UCSF) and IF (Lundberg Lab, Stanford) data and identify a raw-sequence RO-Crate.",
      cited=[{"path": FC_DESC, "quote": prov[0]}], absent=["was_derived_from", "raw_data_sources"]),
    r(0, "June 2025 release: provenance-graph HTML files are listed but their content is not described, and no source laboratory or derivation is stated.",
      absent=["was_derived_from", "raw_data_sources"], considered=["file_collections.resources.name", FC_DESC]),
    r(1, "October 2025 release: file descriptions state the SEC-MS data were generated in the Krogan laboratory at UCSF.",
      cited=[{"path": FC_DESC, "quote": prov[2]}], absent=["was_derived_from", "raw_data_sources"]),
    r(0, "June 2026 release: no source, derivation or raw-data provenance; its files carry no descriptions.",
      absent=["was_derived_from", "raw_data_sources", "updates"], considered=["description"])]

# ---------------- Element 7 ----------------
ITEMS["E7.1"] = same(0, "no purposes at release level.", absent=["purposes"])
ITEMS["E7.2"] = same(0, "no tasks.", absent=["tasks"])
ITEMS["E7.3"] = same(0, "no funders at release level (NIH funding is recorded only for the collection).", absent=["funders"])
ITEMS["E7.4"] = same(0, "no grant/award identifier at release level.", absent=["funders"])
ITEMS["E7.5"] = [r(0, f"{LBL[i]}: no creators, funders or citation naming contributors.", absent=["creators", "funders", "citation"]) for i in range(3)] + [
    r(1, "June 2026 release: no creators block, but the release citation lists all 47 authors (Clark T ... Ideker T) and the University of Virginia Dataverse.",
      cited=[{"path": "citation", "quote": "Ideker T, 2026"}], absent=["creators", "funders"])]

# ---------------- Element 8 ----------------
ITEMS["E8.1"] = [
    r(1, "March 2025 release: file descriptions state the collection procedure and setting (ICC-IF staining and confocal microscopy in the Lundberg Lab; SEC-MS in the Krogan lab).",
      cited=[{"path": FC_DESC, "quote": "imaged by immunofluorescence-based staining (ICC-IF) and confocal microscopy"}], absent=["collection_mechanisms"]),
    r(1, "June 2025 release: file descriptions state the IF images were acquired by ICC-IF and confocal microscopy.",
      cited=[{"path": FC_DESC, "quote": "imaged by ICC-IF and confocal microscopy"}], absent=["collection_mechanisms"]),
    r(1, "October 2025 release: file descriptions state the SEC-MS data were generated in the Krogan laboratory following drug treatment.",
      cited=[{"path": FC_DESC, "quote": "SEC-MS data following treatment of MDA-MB-468 cells with vorinostat or paclitaxel"}], absent=["collection_mechanisms"]),
    r(0, "June 2026 release: only assay names (Perturb-seq, SEC-MS, AP-MS, IF) appear in the description; no procedures, settings or timeframes.",
      absent=["collection_mechanisms"], considered=["description"])]
ITEMS["E8.2"] = [
    r(1, "March 2025 release: acquisition method and instrument class named (immunofluorescence-based staining and confocal microscopy).",
      cited=[{"path": FC_DESC, "quote": "confocal microscopy"}], absent=["acquisition_methods"]),
    r(1, "June 2025 release: acquisition method named (ICC-IF and confocal microscopy).",
      cited=[{"path": FC_DESC, "quote": "imaged by ICC-IF and confocal microscopy"}], absent=["acquisition_methods"]),
    r(0, "October 2025 release: only assay names and a producing laboratory; no instruments, devices or acquisition protocol.",
      absent=["acquisition_methods", "raw_data_sources"], considered=[FC_DESC]),
    r(0, "June 2026 release: only assay names in the description; no instruments, devices or acquisition protocol.",
      absent=["acquisition_methods", "raw_data_sources"], considered=["description"])]
ITEMS["E8.3"] = same(0, "no preprocessing, cleaning, labeling or annotation documentation at release level (the MuSIC pipeline is described only at collection level, for cell maps not in the releases).",
                     absent=["preprocessing_strategies", "cleaning_strategies", "labeling_strategies", "annotation_analyses", "machine_annotation_tools", "imputation_protocols"])
ITEMS["E8.4"] = same(0, "no software that produced or transformed the released data is named in any release-level slot; nothing named (RO-Crate is a packaging standard, role (c), not processing software).",
                     absent=["preprocessing_strategies", "cleaning_strategies", "labeling_strategies", "imputation_protocols", "machine_annotation_tools", "external_resources"])
ITEMS["E8.5"] = same(0, "no external_resources, conforms_to or imputation_protocols at release level.",
                     absent=["external_resources", "conforms_to", "imputation_protocols"])

# ---------------- Element 9 ----------------
ITEMS["E9.1"] = [r(0, f"{LBL[i]}: no known_limitations; source_caveats only mark the release as superseded.", absent=["known_limitations"], considered=["source_caveats"]) for i in (0, 1)] + [
    r(1, "October 2025 release: description discloses a concrete limitation, that external Perturb-seq data links are embargoed.",
      cited=[{"path": "description", "quote": "Its external Perturb-seq data links are marked embargoed."}], absent=["known_limitations"]),
    r(0, "June 2026 release: no known_limitations at release level (embargo and interim status recorded only at collection level).",
      absent=["known_limitations"], considered=["source_caveats"])]
ITEMS["E9.2"] = same(0, "no known_biases or future_use_impacts.", absent=["known_biases", "future_use_impacts"])
ITEMS["E9.3"] = same(0, "no anomalies; caveats address metadata discrepancies (Dataverse version header vs citation, a file-description wording issue), not data anomalies.",
                     absent=["anomalies"], considered=["source_caveats"])
ITEMS["E9.4"] = same(0, "no sensitive_elements or content_warnings.", absent=["sensitive_elements", "content_warnings"])
ITEMS["E9.5"] = same(0, "no ethical_reviews or future_use_impacts at release level.", absent=["ethical_reviews", "future_use_impacts"])

# ---------------- Element 10 ----------------
ITEMS["E10.1"] = [r(0, f"{LBL[i]}: no publisher; the hosting platform is not named in this unit (only inferable from the DOI prefix).",
                    absent=["publisher"], considered=["doi"]) for i in range(3)] + [
    r(1, "June 2026 release: no publisher slot, but its citation names the University of Virginia Dataverse, a recognised repository.",
      cited=[{"path": "citation", "quote": "University of Virginia Dataverse, V2"}], absent=["publisher"])]
ITEMS["E10.2"] = [r(1, f"{LBL[i]}: valid DOI {dois[i]} supports cross-referencing; no recommended citation string at this release.",
                    cited=[{"path": "doi", "quote": dois[i]}], absent=["citation"]) for i in range(3)] + [
    r(1, "June 2026 release: full recommended citation with authors, year, title, DOI URL and repository, plus DOI 10.18130/V3/HIGT4C.",
      cited=[{"path": "citation", "quote": "University of Virginia Dataverse, V2"}, {"path": "doi", "quote": dois[3]}])]
NOTES["E10.2"] = "Every release has a DOI; only the June 2026 release has a formatted citation."
ITEMS["E10.3"] = [r(1, f"{LBL[i]}: file descriptions identify RO-Crate metadata, a community packaging standard (no conforms_to slot).",
                    cited=[{"path": FC_DESC, "quote": rocrate_q[i]}], absent=["conforms_to"]) for i in range(2)] + [
    r(0, f"{LBL[i]}: no conforms_to and no statement of a community standard.", absent=["conforms_to"], considered=["file_collections.resources.name"]) for i in (2, 3)]
ITEMS["E10.4"] = [r(0, f"{LBL[i]}: no external_resources or page link; no documentation or outreach link for this release.",
                    absent=["external_resources", "page"], considered=["file_collections.resources.name"]) for i in range(3)] + [
    r(1, "June 2026 release: its citation supplies the landing-page link https://doi.org/10.18130/V3/HIGT4C; no other documentation links.",
      cited=[{"path": "citation", "quote": "https://doi.org/10.18130/V3/HIGT4C"}], absent=["external_resources", "page"])]
ITEMS["E10.5"] = same(0, "no related_datasets with typed relationships (e.g. isVersionOf between releases).", absent=["related_datasets"])

# ---------------- Issues ----------------
ISSUES = [
    {"type": "completeness", "category": "attribution", "severity": "high", "score_effect": "lowered",
     "item_ids": ["E7.1", "E7.2", "E7.3", "E7.4", "E7.5"],
     "description": "Release resources carry no purposes, tasks, funders, grant numbers or creators; NIH award 1OT2OD032742-01, creators and purposes are documented only at collection level, which the collection policy does not inherit. Only the June 2026 release names its authors (via citation).",
     "fields_involved": ["resources.purposes", "resources.tasks", "resources.funders", "resources.creators"],
     "recommendation": "Declare the record as a Dataset (conforms_to_class) if the series is the unit of scoring, or repeat funders/creators/purposes on each release resource."},
    {"type": "completeness", "category": "consent_ethics", "severity": "high", "score_effect": "lowered",
     "item_ids": ["E4.1", "E4.2", "E4.3", "E4.4", "E4.5", "E9.5"],
     "description": "No release resource documents human-subject status, ethics review, de-identification, privacy, consent or at-risk populations; the collection-level 'Human Subjects: No' statement, de-identification rationale and ethics reviewers are not inherited, and no caller context declares human_subjects false.",
     "fields_involved": ["resources.human_subject_research", "resources.ethical_reviews", "resources.is_deidentified", "resources.informed_consent", "resources.participant_privacy"],
     "recommendation": "Record per-release human_subject_research (involves_human_subjects: false), is_deidentified and explicit consent/privacy non-applicability statements, or supply caller applicability context."},
    {"type": "completeness", "category": "privacy_regulatory", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["E2.2"],
     "description": "No regulatory or confidentiality classification and no governance committee contact on any release resource.",
     "fields_involved": ["resources.regulatory_restrictions", "resources.data_governance"],
     "recommendation": "Add regulatory_restrictions and data_governance.committee_contact to each release."},
    {"type": "completeness", "category": "processing_provenance", "severity": "high", "score_effect": "lowered",
     "item_ids": ["E6.5", "E8.1", "E8.2", "E8.3", "E8.4", "E8.5"],
     "description": "Collection, acquisition, processing, software and provenance are described only at collection level (MuSIC pipeline, node2vec, Perturb-seq kit). The June 2026 release names assays but no procedures, instruments, processing steps or software, and its files have no descriptions.",
     "fields_involved": ["resources.collection_mechanisms", "resources.acquisition_methods", "resources.preprocessing_strategies", "resources.raw_data_sources", "resources.file_collections.resources.description"],
     "recommendation": "Describe collection mechanisms, instruments, processing software and raw sources per release, at least for the current release."},
    {"type": "completeness", "category": "temporal_version", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["E6.2", "E6.3", "E6.4", "E10.5"],
     "description": "Release resources lack version_access, errata/updates, update frequency and typed version relationships; only the June 2025 release describes its changes. The ordering of releases is recoverable only from titles and prose.",
     "fields_involved": ["resources.version_access", "resources.updates", "resources.errata", "resources.related_datasets"],
     "recommendation": "Add per-release change descriptions and typed related_datasets (isVersionOf / isPreviousVersionOf) linking the releases."},
    {"type": "completeness", "category": "format_access", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["E1.3", "E1.5", "E2.3", "E2.5", "E10.1", "E10.4"],
     "description": "Release resources have no keywords, download_url, publisher, page, external_resources or related/parent dataset links; the March, June and October 2025 releases do not name their hosting platform at all.",
     "fields_involved": ["resources.keywords", "resources.download_url", "resources.publisher", "resources.page", "resources.external_resources"],
     "recommendation": "Give each release a download_url or landing page, publisher (University of Virginia Dataverse), keywords and links to the related MassIVE/Figshare deposits."},
    {"type": "completeness", "category": "variables_metadata", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["E3.2", "E3.4", "E5.3"],
     "description": "Files are characterised only as ZIP/JSON/HTML containers; the payload formats (image, mass-spectrometry, sequencing files) inside the archives, character encoding, variables, tabular flags and split/subpopulation flags are not documented.",
     "fields_involved": ["resources.file_collections.resources.format", "resources.variables", "resources.is_tabular", "resources.subsets"],
     "recommendation": "State inner data formats (e.g. TIFF/PNG, mzML, FASTQ/H5AD), encoding and variable dictionaries for tabular components."},
    {"type": "consistency", "category": "other", "severity": "low", "score_effect": "lowered",
     "item_ids": ["E3.3", "E10.3"],
     "description": "RO-Crate conformance is stated at collection level and implied by RO-Crate metadata files in the March and June 2025 releases, but the October 2025 and June 2026 releases state no schema or standard conformance (the collection's own caveat says the June 2026 page does not state its packaging format).",
     "fields_involved": ["conforms_to", "resources.conforms_to", "resources.file_collections.resources.description"],
     "recommendation": "Record conforms_to per release where the packaging standard is known."},
    {"type": "completeness", "category": "count_size", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["E5.1", "E5.2"],
     "description": "No release has subpopulations or instances. The current June 2026 release gives no counts at all (only file_count 10), and the collection-level 'Data Insights' counts are not tied to any release (as the record itself notes).",
     "fields_involved": ["resources.instances", "resources.subpopulations", "instances"],
     "recommendation": "Report per-release instance counts (proteins imaged, genes perturbed, interactions) and cell-line characteristics."},
    {"type": "completeness", "category": "bias_quality", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["E5.5", "E9.1", "E9.2", "E9.3", "E9.4"],
     "description": "Limitations, biases, anomalies, missing-data and sensitive-content documentation are absent from the releases (the collection lists limitations and two bias statements; only the October 2025 release mentions embargoed links).",
     "fields_involved": ["resources.known_limitations", "resources.known_biases", "resources.anomalies", "resources.sensitive_elements"],
     "recommendation": "Carry limitations (embargo, interim status, incomplete overlap of protein sets) and bias statements onto each release."},
    {"type": "completeness", "category": "license_use_terms", "severity": "low", "score_effect": "lowered",
     "item_ids": ["E3.5"],
     "description": "Releases carry a licence string but no intended, prohibited or discouraged uses; the clinical-use prohibition exists only at collection level.",
     "fields_involved": ["resources.intended_uses", "resources.prohibited_uses"],
     "recommendation": "Attach use guidance to each release or declare the series a single Dataset."},
    {"type": "consistency", "category": "source_conflict", "severity": "low", "score_effect": "noted_only", "item_ids": [],
     "description": "Disclosed source conflicts: the data-releases page dates the June 2026 release to June 17, 2025 while Dataverse gives 2026-06-17; Dataverse page headers (1.4, 2.1) disagree with citation versions (V1, V2); IF protein counts differ by release (563, 464, 523). All are documented in source_caveats rather than silently reconciled.",
     "fields_involved": ["resources.issued", "resources.version", "resources.source_caveats", "source_caveats"],
     "recommendation": "No change needed beyond keeping the caveats; consider recording the version scheme explicitly."},
    {"type": "correctness", "category": "persistent_identifier", "severity": "low", "score_effect": "noted_only", "item_ids": [],
     "description": "Identifier checks: all release DOIs use prefix 10.18130 (University of Virginia Dataverse, correctly named in the citation); the top-level id is a project homepage URL (https://cm4ai.org/) rather than a DOI; NIH award 1OT2OD032742-01 matches the NIH activity-code pattern; Cellosaurus RRIDs (RRID:CVCL_0419, RRID:CVCL_B5P3) are well formed though outside the SCR/AB patterns the rubric lists.",
     "fields_involved": ["resources.doi", "id", "funders.grants.grant_number", "subpopulations.identification"],
     "recommendation": "Optionally use the series' concept DOI or latest release DOI as the collection id."},
    {"type": "content_accuracy", "category": "attribution", "severity": "low", "score_effect": "noted_only", "item_ids": [],
     "description": "Creator name 'Ballllosero Navarro F' (four l's) appears in both creators and the June 2026 citation; it may be a transcription of the source spelling or a typo. Uncertain; not verifiable from the record alone.",
     "fields_involved": ["creators.name", "resources.citation"],
     "recommendation": "Check the spelling against the Dataverse author list."},
]

linked = {k for issue in ISSUES if issue["score_effect"] == "lowered" for k in issue["item_ids"]}

ELEMENTS = [
    (1, "Dataset Discovery and Identification", "Can a user or system discover and uniquely identify this dataset?"),
    (2, "Dataset Access and Retrieval", "Can the dataset and its associated resources be located, accessed, and downloaded?"),
    (3, "Data Reuse and Interoperability", "Is sufficient information provided to reuse and integrate the dataset with others?\nNote: Evaluate whether the dataset is designed for integration with similar datasets, including: common identifiers for cross-dataset linking, standardized formats for data harmonization, and documented integration procedures.\n"),
    (4, "Ethical Use and Privacy Safeguards", "Does the dataset document the ethical oversight, privacy, consent and safeguards that apply to its subjects and governance context? Equivalent local ethics and regulatory frameworks are accepted; HIPAA or an IRB is not a universal requirement."),
    (5, "Data Composition and Structure", "Can the dataset's structure, modality, and population be understood from metadata?"),
    (6, "Data Provenance and Version Tracking", "Can a user determine dataset versions, update history, and provenance?"),
    (7, "Scientific Motivation and Funding Transparency", "Does the metadata clearly state why the dataset exists and who funded it?"),
    (8, "Technical Transparency (Data Collection and Processing)", "Can data collection and processing steps be replicated or understood?\nNote: Preprocessing and collection metadata may be represented as structured text descriptions OR as machine-readable provenance graphs (e.g., W3C PROV-O, workflow graphs). Evaluation should check for: (1) structured text descriptions OR (2) graph representations with entity-activity-agent relationships. Both formats are acceptable.\n"),
    (9, "Dataset Evaluation and Limitations Disclosure", "Does the metadata communicate known risks, biases, or dataset limitations?"),
    (10, "Cross-Platform and Community Integration", "Does the dataset connect to relevant repositories, communities and standards? A shared dataset needs citation or identifier guidance and a named hosting or preservation route appropriate to its domain."),
]

elements = []
total = 0
for eid, ename, edesc in ELEMENTS:
    subs = []
    escore = emax = 0
    for idx in range(1, 6):
        key = f"E{eid}.{idx}"
        rule = rules[key]
        rows = ITEMS[key]
        assert len(rows) == 4 and rule["applicable"], key
        for path, row in zip(P, rows):
            row["path"] = path
        rows = [{"path": row.pop("path"), **row} for row in rows]
        score = min(row["score"] for row in rows)
        per = "; ".join(f"{LBL[i]}={rows[i]['score']}" for i in range(4))
        sub = {
            "name": rule["name"], "item_id": key, "score": score,
            "evidence": f"Minimum across release units ({per}). " + rows[[x['score'] for x in rows].index(score)]["evidence"],
            "quality_note": NOTES.get(key, "Scored per release resource; collection-level content is not inherited by the release units."),
            "applicable": True, "applicability_status": rule["status"], "applicability_evidence": rule["evidence"],
            "unit_scores": rows,
        }
        if score < 1 and key not in linked:
            raise SystemExit(f"{key} deducted with no linked issue")
        subs.append(sub)
        escore += score
        emax += rule["max_score"]
    elements.append({"id": eid, "name": ename, "description": edesc, "sub_elements": subs,
                     "element_score": escore, "element_max": emax})
    total += escore

result = {
    "rubric": "rubric10-semantic",
    "version": "3.0",
    "d4d_file": INPUT,
    "project": "CM4AI",
    "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {"name": MODEL, "evaluator_model": MODEL, "temperature": None,
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
            "The record has no conforms_to_class declaration and a nonempty resources list, so under this instrument it is a collection of four release datasets scored by the per-item minimum; rich collection-level documentation (ethics, funding, creators, processing, limitations, use guidance) is not inherited by the releases and therefore earns no credit. The low total reflects this scope rule more than the overall quality of the record.",
            "Release units are well identified: each has a valid UVA Dataverse DOI, a Dataverse version, a CC BY-NC-SA 4.0 licence and file-level formats, MIME types and MD5 checksums.",
            "The June 2026 (current) release is the weakest unit: its ten files are undescribed, so assay procedures, counts, provenance and standards cannot be read from it; it does carry the only full citation.",
            "Source conflicts (release date year, Dataverse version header vs citation, IF protein counts) are disclosed in source_caveats rather than silently resolved, which is good documentation practice.",
            "Collection-level human_subject_research states involves_human_subjects: false with a de-identification rationale; because the caller supplied no applicability context, Element 4 stays in the denominator and is scored on the release units.",
        ],
        "consistency_checks": {"passed": 6, "failed": 0, "warnings": 3},
        "correctness_validations": {
            "doi_format": "valid (10.18130 University of Virginia Dataverse, all four releases)",
            "grant_number_format": "valid_nih at collection level (1OT2OD032742-01); not present on release units",
            "rrid_format": "valid Cellosaurus RRIDs at collection level (RRID:CVCL_0419, RRID:CVCL_B5P3); none on release units",
            "url_validity": "valid (doi.org URL in the June 2026 citation; file ids are cm4ai.org fragment URIs, not download links)",
        },
    },
    "applicability_context": CONTEXT,
    "evaluation_scope": {"policy": "minimum_per_item_across_all_resource_datasets_v1", "units": units,
                         "collection_metadata_inherited": False},
    "metadata": {
        "instrument_sha256": sha(DEFINITION),
        "evidence_authority_sha256": sha(AUTHORITY),
        "rubric_sha256": sha(RUBRIC),
        "input_sha256": input_sha,
        "context_sha256": context_digest(CONTEXT),
        "caller_context_file": None,
        "evaluator_model": MODEL,
    },
}

out = ROOT / OUTPUT
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {out} total={total}")
