#!/usr/bin/env python3
"""Build the rubric20-semantic v3 evaluation of CM4AI (2026-11-22b rep2).

Purpose: serialize the judgements made by the evaluating session (claude-opus-5-5)
  for data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CM4AI_d4d.yaml
  under .claude/agents/d4d-rubric20-semantic.md (general context instrument v3).
Inputs: the D4D record, data/rubric/rubric20.txt, the agent definition,
  data/rubric/semantic_evidence_authority_v3.json. No caller context (empty).
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep2_evaluation.json
Date: 2026-11-22. Scores are hand judgements encoded below; this script only
  computes hashes, character lengths and totals.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import (  # noqa: E402
    context_digest, dataset_units, load_document, normalize_context)

D4D = ROOT / "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2/CM4AI_d4d.yaml"
RUBRIC = ROOT / "data/rubric/rubric20.txt"
AGENT = ROOT / ".claude/agents/d4d-rubric20-semantic.md"
AUTH = ROOT / "data/rubric/semantic_evidence_authority_v3.json"
OUT = ROOT / "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep2_evaluation.json"
MODEL = "claude-opus-5-5"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


doc, input_sha = load_document(D4D)
units = dataset_units(doc)
assert [u[0] for u in units] == [f"#/resources/{i}" for i in range(4)], units
R = [u[1] for u in units]
dlen = [len(" ".join(r["description"].split())) for r in R]
ctx = normalize_context({})

U = [u[0] for u in units]
REL = ["March 2025", "June 2025", "October 2025", "June 2026"]


def row(i, score, evidence, cited=(), absent=(), counts=(), considered=()):
    return {"path": U[i], "score": score, "evidence": evidence,
            "cited": [dict(c) for c in cited], "absent": [{"path": a} for a in absent],
            "counts": [dict(c) for c in counts], "considered": list(considered)}


def C(path, quote=None):
    return {"path": path, **({"quote": quote} if quote else {})}


ALWAYS = "This item applies to every dataset"


def unk(pred):
    return f"{pred}: not declared by the caller (no context supplied); unknown, retained in the denominator"


questions = []


def q(qid, name, desc, stype, maxs, label, evidence, note, rows, status="applicable",
      appl_ev=ALWAYS, no_issue=None):
    scores = [r["score"] for r in rows]
    item = min(scores)
    d = {"id": qid, "name": name, "description": desc[:120], "score_type": stype,
         "score": item, "max_score": maxs, "score_label": label, "evidence": evidence,
         "quality_note": note, "applicable": True, "applicability_status": status,
         "applicability_evidence": appl_ev, "unit_scores": rows}
    if no_issue:
        d["no_issue_reason"] = no_issue
    questions.append(d)


core = lambda i: [C("/id"), C("/title"), C("/description"), C("/doi")]  # noqa: E731

# Q1 Field completeness
q(1, "Field Completeness",
  "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
  "numeric", 5, "Absent (<=40% populated per release unit)",
  "Each release unit populates id, title, description and doi (4 of 14 listed fields, ~29%); keywords, license_and_use_terms (only a bare `license` string), page, creators, purposes, instances, resources, parent_datasets, variables and confidentiality_level are not populated at release level.",
  "Collection interpretation: the record has no class declaration and four resources, so each release is scored on its own fields; top-level metadata is not inherited.",
  [row(i, 0, f"{REL[i]} release: 4/14 fields (id, title, description, doi); license is a bare string, not license_and_use_terms.",
       cited=core(i) + [C("/license", "CC BY-NC-SA 4.0")],
       absent=["keywords", "license_and_use_terms", "page", "creators", "purposes", "instances",
               "resources", "parent_datasets", "variables", "regulatory_restrictions.confidentiality_level"])
   for i in range(4)])

# Q2 Entry length
q(2, "Entry Length Adequacy",
  "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
  "numeric", 5, "Good (one adequate narrative field, purposes absent)",
  f"Release descriptions are {dlen} characters long, but no release unit has purposes; averaged over the two narrative fields the length falls near the 200-character boundary.",
  "Descriptions are substantive (modalities, cell lines, treatments); purposes is missing in every unit, so the 5 band is not reached.",
  [row(i, 3, f"{REL[i]} description {dlen[i]} chars; purposes absent.",
       cited=[C("/description")], absent=["purposes"]) for i in range(4)])

# Q3 Keywords
q(3, "Keyword Diversity",
  "Number of distinct keywords describing the dataset. Domain-specific controlled terms or condition lists may supply additional topic evidence where documented.",
  "numeric", 5, "Absent (<3 keywords per release unit)",
  "No release unit carries keywords; the 29 top-level keywords belong to the collection mapping and are not inherited.",
  "Release-level discoverability terms are missing.",
  [row(i, 0, f"{REL[i]}: no keywords.", absent=["keywords"], considered=["/title"]) for i in range(4)])

# Q4 File types
fr = lambda i: f"/file_collections/0/resources"  # noqa: E731
q(4, "File Enumeration and Type Variety",
  "Number and variety of documented distribution formats and file types. Modalities may occur within one resource or in separate linked resources.",
  "numeric", 5, "Absent for the October 2025 and June 2026 units (ZIP only)",
  "March 2025: JSON + ZIP (2 types); June 2025: HTML + JSON + ZIP (3 types); October 2025 and June 2026: every listed file is ZIP (1 type). Item score is the minimum across units.",
  "ZIP is a container; the formats of the images, mass-spec and sequence files inside are not documented for the two latest releases.",
  [row(0, 3, "6 files: ro-crate-metadata.json (JSON) x3, IF image ZIPs x3.",
       cited=[C("/file_collections/0/file_count"), C("/file_collections/0/resources/0/format", "JSON"),
              C("/file_collections/0/resources/2/format", "ZIP")],
       counts=[{"path": "/file_collections/0/resources", "claimed": 6}]),
   row(1, 3, "10 of 21 files listed: HTML datasheet/provenance graphs, JSON RO-Crate metadata, IF image ZIPs.",
       cited=[C("/file_collections/0/file_count"), C("/file_collections/0/resources/0/format", "HTML"),
              C("/file_collections/0/resources/1/format", "JSON"), C("/file_collections/0/resources/2/format", "ZIP"),
              C("/file_collections/0/description", "the captured page shows the first 10")],
       counts=[{"path": "/file_collections/0/resources", "claimed": 10}]),
   row(2, 0, "8 files, all ZIP archives.",
       cited=[C("/file_collections/0/file_count"), C("/file_collections/0/resources/0/format", "ZIP")],
       counts=[{"path": "/file_collections/0/resources", "claimed": 8}], absent=["total_file_count"]),
   row(3, 0, "10 files, all ZIP archives; no descriptions of contents.",
       cited=[C("/file_collections/0/file_count"), C("/file_collections/0/resources/0/format", "ZIP")],
       counts=[{"path": "/file_collections/0/resources", "claimed": 10}], absent=["total_file_count"])])

# Q5 Size
q(5, "Data File Size Availability",
  "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
  "pass_fail", 1, "Fail (June 2026 unit has no size or instance metadata)",
  "No unit gives bytes. March/June/October 2025 file descriptions give protein or gene counts (563, 464 proteins; 11,739 genes); the June 2026 unit gives only file_count 10 and no dimensional metadata.",
  "A file count is not a size or instance count; minimum across units is fail.",
  [row(0, 1, "File descriptions state 563 proteins of interest per IF archive.",
       cited=[C("/file_collections/0/resources/2/description", "563 proteins of interest")]),
   row(1, 1, "File descriptions state 464 proteins of interest per IF archive.",
       cited=[C("/file_collections/0/resources/2/description", "464 proteins of interest")]),
   row(2, 1, "Perturb-seq atlas file states 11,739 targeted genes.",
       cited=[C("/file_collections/0/resources/2/description", "11,739 targeted genes")]),
   row(3, 0, "Only file_count 10; no bytes, instances, splits or subpopulations.",
       cited=[C("/file_collections/0/file_count")],
       absent=["total_size_bytes", "file_collections.total_bytes", "instances", "splits", "subpopulations"])])

# Q6 Identification
q(6, "Dataset Identification Metadata",
  "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification (publisher or repository).",
  "pass_fail", 1, "Pass",
  "Each release has a DataCite DOI under prefix 10.18130 (University of Virginia Dataverse). publisher is absent in every unit; the June 2026 citation names the University of Virginia Dataverse.",
  "Persistent identifiers present; hosting platform only implicit except in the June 2026 citation.",
  [row(i, 1, f"{REL[i]} DOI {R[i]['doi']}.", cited=[C("/doi"), C("/id")], absent=["publisher"]) for i in range(3)]
  + [row(3, 1, "DOI 10.18130/V3/HIGT4C; citation names University of Virginia Dataverse.",
         cited=[C("/doi"), C("/id"), C("/citation", "University of Virginia Dataverse")], absent=["publisher"])],
  no_issue="Maximum score reached.")

# Q7 Funding
q(7, "Funding and Acknowledgements Completeness",
  "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
  "numeric", 5, "Absent (no funding data in release units)",
  "No release unit has funders or creators. The June 2026 citation lists author names without affiliations; the NIH award (1OT2OD032742-01) appears only at collection level.",
  "Collection-level funders/creators are not inherited by the release datasets.",
  [row(i, 0, f"{REL[i]}: no funders or creators.", absent=["funders", "creators"]) for i in range(3)]
  + [row(3, 0, "No funders; author names only inside the citation string, no affiliations.",
         absent=["funders", "creators"], considered=["/citation"])])

# Q8 Ethics
q(8, "Ethical and Privacy Declarations",
  "Ethical oversight and privacy safeguards appropriate to the dataset, including consent, deidentification, privacy risks, compensation and vulnerable populations where applicable.",
  "numeric", 5, "Absent (no ethics fields in release units)",
  "No release unit populates ethical_reviews, human_subject_research, is_deidentified, informed_consent or data_protection_impacts. The collection-level 'Human Subjects: No' statement is not inherited and is not a caller declaration.",
  "human_subjects is unknown, so the item stays scored.",
  [row(i, 0, f"{REL[i]}: no ethics or privacy fields.",
       absent=["ethical_reviews", "human_subject_research", "is_deidentified", "participant_privacy",
               "informed_consent", "data_protection_impacts", "at_risk_populations", "participant_compensation"])
   for i in range(4)], status="unknown", appl_ev=unk("human_subjects"))

# Q9 Access/governance
q(9, "Access Requirements and Governance Documentation",
  "Documentation of access and license terms, intellectual-property restrictions, applicable regulatory obligations, confidentiality and governance contacts.",
  "numeric", 5, "Good (license only)",
  "Every release states license 'CC BY-NC-SA 4.0'; no ip_restrictions, regulatory_restrictions, confidentiality level or governance contact at release level.",
  "License only matches the 3 band.",
  [row(i, 3, f"{REL[i]}: license CC BY-NC-SA 4.0 only.", cited=[C("/license", "CC BY-NC-SA 4.0")],
       absent=["license_and_use_terms", "ip_restrictions", "regulatory_restrictions", "data_protection_impacts"])
   for i in range(4)])

# Q10 Interoperability
q(10, "Interoperability, Standardization, and Cross-Platform Integration",
  "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures.",
  "numeric", 5, "Good (standard formats, no schema conformance declared)",
  "Files carry standard formats and IANA media types (JSON, HTML, ZIP with compression zip); March/June 2025 list RO-Crate metadata files, but no unit declares conforms_to or related_datasets.",
  "RO-Crate conformance is declared only at collection level.",
  [row(0, 3, "JSON/ZIP media types; RO-Crate metadata files described.",
       cited=[C("/file_collections/0/resources/0/media_type", "application/json"),
              C("/file_collections/0/resources/0/description", "RO-Crate metadata"),
              C("/file_collections/0/resources/2/compression", "zip")],
       absent=["conforms_to", "conforms_to_schema", "related_datasets", "external_resources"]),
   row(1, 3, "Release RO-Crate with pointers to sub-RO-Crates; HTML/JSON/ZIP media types.",
       cited=[C("/file_collections/0/resources/1/description", "Release RO-Crate with pointers to sub-RO-Crates"),
              C("/file_collections/0/resources/2/compression", "zip")],
       absent=["conforms_to", "conforms_to_schema", "related_datasets", "external_resources"]),
   row(2, 3, "ZIP archives (application/zip, compression zip) only.",
       cited=[C("/file_collections/0/resources/0/media_type", "application/zip"),
              C("/file_collections/0/resources/0/compression", "zip")],
       absent=["conforms_to", "conforms_to_schema", "related_datasets", "external_resources"]),
   row(3, 3, "ZIP archives (application/zip, compression zip) only.",
       cited=[C("/file_collections/0/resources/0/media_type", "application/zip"),
              C("/file_collections/0/resources/0/compression", "zip")],
       absent=["conforms_to", "conforms_to_schema", "related_datasets", "external_resources"])],
  status="unknown", appl_ev=unk("shared_dataset"))

# Q11 Tools
q(11, "Tool and Software Transparency",
  "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including relevant software names, versions and workflow inputs/outputs.",
  "numeric", 5, "Absent (no processing strategy or tool in release units)",
  "No release unit documents preprocessing, cleaning, labeling or annotation; the MuSIC pipeline appears only at collection level and is stated not to apply to the released files. June 2025 lists provenance-graph HTML files without describing their content.",
  "data_processing is unknown, so the item stays scored.",
  [row(i, 0, f"{REL[i]}: no processing documentation.",
       absent=["preprocessing_strategies", "cleaning_strategies", "labeling_strategies",
               "machine_annotation_tools", "imputation_protocols", "missing_data_documentation"],
       considered=["/description"]) for i in range(4)],
  status="unknown", appl_ev=unk("data_processing"))

# Q12 Collection
q(12, "Collection Protocol Clarity",
  "Evaluates description completeness of data collection mechanisms, acquisition methods, data collectors, collection timeframes, and raw data sources.",
  "numeric", 5, "Good (partial: assay/mechanism named in descriptions)",
  "Release descriptions and file descriptions name assays (ICC-IF confocal microscopy, SEC-MS, Perturb-seq, AP-MS) and, for 2025 releases, the producing labs; no collection fields, timeframes or raw sources at release level. created_on 2025-02-27 is the only date.",
  "Mechanism-only description matches the 3 band.",
  [row(0, 3, "ICC-IF confocal microscopy in the Lundberg Lab; SEC-MS in the Krogan lab.",
       cited=[C("/file_collections/0/resources/4/description", "Lundberg Lab at Stanford University"),
              C("/file_collections/0/resources/5/description", "Nevan Krogan laboratory")],
       absent=["collection_mechanisms", "data_collectors", "collection_timeframes", "raw_data_sources"],
       considered=["/description", "/created_on"]),
   row(1, 3, "IF images by ICC-IF and confocal microscopy.",
       cited=[C("/file_collections/0/resources/2/description", "imaged by ICC-IF and confocal microscopy")],
       absent=["collection_mechanisms", "data_collectors", "collection_timeframes", "raw_data_sources"],
       considered=["/description", "/created_on"]),
   row(2, 3, "SEC-MS generated in the Nevan Krogan laboratory.",
       cited=[C("/file_collections/0/resources/0/description", "generated in the Nevan Krogan laboratory")],
       absent=["collection_mechanisms", "data_collectors", "collection_timeframes", "raw_data_sources"],
       considered=["/description", "/created_on"]),
   row(3, 3, "Description names Perturb-seq, SEC-MS, AP-MS and IF image modalities only.",
       cited=[C("/description", "AP-MS data for treated MDA-MB-468 cells")],
       absent=["collection_mechanisms", "data_collectors", "collection_timeframes", "raw_data_sources"],
       considered=["/created_on"])],
  status="unknown", appl_ev=unk("data_collection"))

# Q13 Version
q(13, "Version History, Maintenance, and Sustainability",
  "Documentation of version identifiers, change history, maintenance and preservation plans, responsible contacts and durable access.",
  "numeric", 5, "Good (version + DOI, no sustainability plan)",
  "Each release has a version string and DOI; June 2025 describes its revision changes; no maintainers, update plan or preservation commitment at release level (the quarterly plan and Dataverse preservation are collection-level only).",
  "Version labels conflict with citation version numbers (e.g. 1.4 vs V1), as the record itself notes.",
  [row(i, 3, f"{REL[i]}: version {R[i]['version']}, DOI {R[i]['doi']}.",
       cited=[C("/version"), C("/doi"), C("/issued")],
       absent=["maintainers", "updates", "errata", "version_access", "publisher"],
       considered=["/source_caveats", "/description"]) for i in range(4)],
  status="unknown", appl_ev=unk("shared_dataset"))

# Q14 Publications
q(14, "Associated Publications",
  "Citation, identifiers and documentation links that let a reader identify the dataset and related publications or resources.",
  "numeric", 5, "Good (one distinct reference)",
  "March/June/October 2025 units give only their DOI (one reference). The June 2026 unit adds a formal citation, but it identifies the same DOI, so it is still one distinct reference; no external_resources at release level.",
  "Two distinct references plus a formal citation are needed for 5.",
  [row(i, 3, f"{REL[i]}: bare DOI only.", cited=[C("/doi")], absent=["citation", "external_resources"])
   for i in range(3)]
  + [row(3, 3, "Formal citation with authors, title, DOI and Dataverse; same resource as the DOI.",
         cited=[C("/citation", "https://doi.org/10.18130/V3/HIGT4C"), C("/doi")], absent=["external_resources"])])

# Q15 Human subjects
q(15, "Human Subject Representation",
  "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups.",
  "numeric", 5, "Absent (no human population information in release units)",
  "Release units name cell lines (MDA-MB-468, KOLF2.1J iPSCs) and treatment conditions but give no donor/population representation, instances or subpopulations; the donor descriptions exist only at collection level.",
  "human_subjects is unknown, so the item stays scored.",
  [row(i, 0, f"{REL[i]}: cell-line names only; no population fields.",
       absent=["instances", "subpopulations", "at_risk_populations", "missing_data_documentation"],
       considered=["/description"]) for i in range(4)],
  status="unknown", appl_ev=unk("human_subjects"))

# Q16 Findability
q(16, "Findability (Persistent Links)",
  "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
  "pass_fail", 1, "Pass",
  "Each release has a resolvable DOI (10.18130/...); the June 2026 citation includes https://doi.org/10.18130/V3/HIGT4C. Unit ids for the doi-prefixed releases are CURIEs; file ids are synthetic cm4ai.org fragment URIs.",
  "No page or download_url at release level, but DOIs provide persistent links.",
  [row(i, 1, f"{REL[i]} DOI {R[i]['doi']}.", cited=[C("/doi"), C("/id")], absent=["page", "download_url"])
   for i in range(4)], no_issue="Maximum score reached.")

# Q17 Access
q(17, "Accessibility (Access Mechanism)",
  "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
  "numeric", 5, "Good (partially described)",
  "DOI-resolved Dataverse records, licensed CC BY-NC-SA 4.0, with file formats and MD5 checksums; no download_url, access tier (open download vs registration) or embargo handling at release level.",
  "Partially described access path.",
  [row(i, 3, f"{REL[i]}: DOI + license + per-file format/md5.",
       cited=[C("/doi"), C("/license", "CC BY-NC-SA 4.0"), C("/file_collections/0/resources/0/md5")],
       absent=["download_url", "license_and_use_terms", "distribution_formats"]) for i in range(4)],
  status="unknown", appl_ev=unk("shared_dataset"))

# Q18 Reuse
q(18, "Reusability, Use Guidance, and Social Impact",
  "License is clearly defined with explicit use guidance including intended uses, prohibited uses, discouraged uses, AND comprehensive social impact analysis.",
  "numeric", 5, "Good (license conveys basic non-commercial/share-alike terms)",
  "Each release names CC BY-NC-SA 4.0, whose identifier conveys basic non-commercial and share-alike terms; no intended, prohibited or discouraged uses or future-use impacts at release level.",
  "Borderline between 0 and 3: a license is present, so the 0 anchor (no license) does not fit; no explicit use guidance.",
  [row(i, 3, f"{REL[i]}: license only.", cited=[C("/license", "CC BY-NC-SA 4.0")],
       absent=["intended_uses", "prohibited_uses", "discouraged_uses", "future_use_impacts", "license_and_use_terms"])
   for i in range(4)])

# Q19 Provenance
q(19, "Data Integrity, Provenance Graph, and Quality",
  "Presence of version access, errata, update plans, source derivation, parent dataset linkages, missing data documentation, data split indicators, AND provenance graph representation.",
  "numeric", 5, "Good (version history only)",
  "Release units carry version numbers, issue dates and supersession notes (June 2025 describes its revision: RGB images added, RO-Crate metadata corrected). June 2025 lists provenance-graph HTML files, but no lineage (was_derived_from, parent_datasets, raw_data_sources) is represented in the record.",
  "Version history without a represented provenance graph matches the 3 band.",
  [row(i, 3, f"{REL[i]}: version {R[i]['version']}; issued {R[i]['issued'][:10]}.",
       cited=[C("/version"), C("/issued"), C("/source_caveats")]
       + ([C("/file_collections/0/resources/5/name", "Images-paclitaxel-provenance-graph.html"),
           C("/description", "correcting RO-Crate metadata")] if i == 1 else []),
       absent=["version_access", "errata", "updates", "was_derived_from", "parent_datasets",
               "raw_data_sources", "missing_data_documentation"]) for i in range(4)])

# Q20 Bias
q(20, "Bias Documentation and Responsible AI Alignment",
  "Documentation of known biases, limitations and potential effects on intended or foreseeable uses.",
  "numeric", 5, "Absent (no bias documentation in release units)",
  "No release unit populates known_biases or future_use_impacts; the collection-level biases are not inherited.",
  "No release-level bias documentation.",
  [row(i, 0, f"{REL[i]}: no bias fields.", absent=["known_biases", "future_use_impacts", "known_limitations"])
   for i in range(4)])

cats = [("Structural Completeness", range(0, 5)), ("Metadata Quality & Content", range(5, 10)),
        ("Technical Documentation", range(10, 15)), ("FAIRness & Accessibility", range(15, 20))]
categories = []
for name, rng in cats:
    qs = [questions[k] for k in rng]
    categories.append({"name": name, "questions": qs,
                       "category_score": sum(x["score"] for x in qs),
                       "category_max": sum(x["max_score"] for x in qs)})
total = sum(c["category_score"] for c in categories)

issues = [
    {"id": "I1", "type": "completeness", "category": "variables_metadata", "score_effect": "lowered",
     "item_ids": ["Q1", "Q2", "Q3"],
     "description": "Release datasets lack keywords, purposes, creators, page and composition fields; descriptive metadata lives only on the undeclared top-level mapping, which is not inherited under the collection interpretation."},
    {"id": "I2", "type": "completeness", "category": "format_access", "score_effect": "lowered",
     "item_ids": ["Q4", "Q5", "Q17"],
     "description": "October 2025 and June 2026 releases list only ZIP archives with no inner formats, byte sizes or download URLs; June 2026 files carry no descriptions or dimensional metadata."},
    {"id": "I3", "type": "completeness", "category": "attribution", "score_effect": "lowered",
     "item_ids": ["Q7", "Q14"],
     "description": "No release records funders or creators with affiliations; the June 2026 citation and DOI identify the same resource, so no release documents a second distinct reference."},
    {"id": "I4", "type": "completeness", "category": "consent_ethics", "score_effect": "lowered",
     "item_ids": ["Q8", "Q15"],
     "description": "No release records ethics review, human-subject status, deidentification or cell-line donor/population information."},
    {"id": "I5", "type": "completeness", "category": "license_use_terms", "score_effect": "lowered",
     "item_ids": ["Q9", "Q18"],
     "description": "Releases give only a bare license string; no IP restrictions, confidentiality classification, governance contact or intended/prohibited uses at release level."},
    {"id": "I6", "type": "completeness", "category": "processing_provenance", "score_effect": "lowered",
     "item_ids": ["Q10", "Q11", "Q12", "Q19"],
     "description": "Releases declare no schema conformance, processing tools, collection fields, timeframes or lineage; provenance-graph files in June 2025 are listed but not represented."},
    {"id": "I7", "type": "completeness", "category": "temporal_version", "score_effect": "lowered",
     "item_ids": ["Q13"],
     "description": "Release units have version and DOI but no maintainers, update plan or preservation commitment."},
    {"id": "I8", "type": "completeness", "category": "bias_quality", "score_effect": "lowered",
     "item_ids": ["Q20"],
     "description": "No release-level known_biases or future_use_impacts."},
    {"id": "I9", "type": "consistency", "category": "temporal_version", "score_effect": "noted_only", "item_ids": [],
     "description": "Version strings disagree with citation versions (1.4 vs V1; 2.1 vs V2 in two releases); all four releases share created_on 2025-02-27; the data-releases page and Dataverse disagree on the June 2026 release year (record documents and resolves it)."},
    {"id": "I10", "type": "consistency", "category": "count_size", "score_effect": "noted_only", "item_ids": [],
     "description": "IF protein counts differ across releases and summaries (563, 464, 523); the June 2025 file_count 21 exceeds the 10 files listed. Both are acknowledged in source_caveats."},
    {"id": "I11", "type": "correctness", "category": "persistent_identifier", "score_effect": "noted_only", "item_ids": [],
     "description": "File ids are minted cm4ai.org fragment URIs (e.g. https://cm4ai.org/#release-2026-06-files) that are not resolvable identifiers; release DOIs (10.18130, UVA Dataverse) are well formed."},
    {"id": "I12", "type": "semantic_understanding", "category": "privacy_regulatory", "score_effect": "noted_only", "item_ids": [],
     "description": "At collection level, 'derived from commercially available de-identified human cell lines' is recorded as a known bias although it is a provenance statement; deidentification is asserted while human-subject involvement is false. Neither affects release-unit scores."},
    {"id": "I13", "type": "content_accuracy", "category": "attribution", "score_effect": "noted_only", "item_ids": [],
     "description": "Creator name 'Ballllosero Navarro F' (also in the June 2026 citation) appears to contain a transcription error; not verifiable from the record."},
]

EXTRA = {
    "I1": ("high", ["keywords", "purposes", "creators", "page", "resources"], "Declare the top-level record as a Dataset (conforms_to_class) or repeat keywords, purposes and creators on each release."),
    "I2": ("medium", ["file_collections", "total_size_bytes", "download_url"], "List inner file formats, byte sizes and download URLs for each release archive."),
    "I3": ("high", ["funders", "creators", "citation", "external_resources"], "Record funders/creators with affiliations and the related preprints on each release."),
    "I4": ("high", ["ethical_reviews", "human_subject_research", "is_deidentified", "subpopulations"], "Carry the ethics, deidentification and cell-line donor statements onto each release."),
    "I5": ("medium", ["license", "license_and_use_terms", "ip_restrictions", "intended_uses", "prohibited_uses"], "Use license_and_use_terms with full terms, IP holders and use guidance per release."),
    "I6": ("medium", ["conforms_to", "preprocessing_strategies", "collection_mechanisms", "was_derived_from"], "Declare RO-Crate conformance and collection/processing lineage on each release."),
    "I7": ("medium", ["maintainers", "updates", "version_access"], "Add maintainers and the maintenance/preservation plan to each release."),
    "I8": ("medium", ["known_biases", "future_use_impacts"], "Record release-specific biases and limitations."),
    "I9": ("low", ["version", "created_on", "issued"], "Use the Dataverse citation version consistently and give release-specific creation dates."),
    "I10": ("low", ["file_collections", "file_count"], "List all files or state the unlisted ones explicitly."),
    "I11": ("low", ["id"], "Use resolvable Dataverse file identifiers where available."),
    "I12": ("low", ["known_biases", "is_deidentified", "human_subject_research"], "Move provenance statements out of known_biases."),
    "I13": ("low", ["creators", "citation"], "Check the creator name against the Dataverse author list."),
}
for _i in issues:
    _sev, _f, _r = EXTRA[_i["id"]]
    _i["severity"], _i["fields_involved"], _i["recommendation"] = _sev, _f, _r

for qq in questions:
    linked = [i["id"] for i in issues if f"Q{qq['id']}" in i["item_ids"]]
    if qq["score"] < qq["max_score"]:
        assert linked, qq["id"]

out = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": str(D4D.relative_to(ROOT)),
    "project": "CM4AI",
    "method": "claudecode_agent",
    "run_label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep2",
    "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {"name": MODEL, "evaluator_model": MODEL, "temperature": None,
              "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
              "evaluation_type": "semantic_llm_judge"},
    "overall_score": {"total_points": total, "max_points": 88, "excluded_max_points": 0,
                      "adjusted_max_points": 88,
                      "normalized_percentage": round(total / 88 * 100, 2),
                      "fixed_percentage": round(total / 88 * 100, 2),
                      "questions_not_applicable": 0, "excluded_item_ids": []},
    "categories": categories,
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "The record has no conforms_to_class and four nonempty resources, so it is scored as a collection of four release datasets; the rich top-level metadata (creators, funders, ethics, uses, biases, collection protocol) is not inherited, which drives most low scores.",
            "Each item score is the minimum across the four releases; the October 2025 and June 2026 releases are the weakest units (ZIP-only file lists, June 2026 without file descriptions).",
            "Top-level content (not scored here) is detailed and well caveated: NIH award 1OT2OD032742-01 matches the NIH OT2 pattern, ORCIDs are well formed, and release DOIs share the 10.18130 Dataverse prefix.",
            "Declaring the top level as a Dataset (conforms_to_class) or repeating key metadata on each release would let the documentation be credited under this instrument."],
        "consistency_checks": {"passed": 3, "failed": 0, "warnings": 4},
        "correctness_validations": {"doi_format": "valid (10.18130/V3/... for all four releases)",
                                    "grant_number_format": "not present in release units; top-level 1OT2OD032742-01 matches NIH OT2 pattern",
                                    "rrid_format": "not present in release units",
                                    "url_validity": "DOI URL in June 2026 citation well formed; file ids are non-resolvable fragment URIs"}},
    "applicability_context": {},
    "evaluation_scope": {"policy": "minimum_per_item_across_all_resource_datasets_v1",
                         "units": [{"path": p, "id": r["id"]} for p, r in units],
                         "collection_metadata_inherited": False},
    "metadata": {"instrument_sha256": sha(AGENT), "evidence_authority_sha256": sha(AUTH),
                 "rubric_sha256": sha(RUBRIC), "input_sha256": input_sha,
                 "context_sha256": context_digest(ctx), "evaluator_model": MODEL,
                 "builder_script": str(Path(__file__).resolve().relative_to(ROOT))},
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(OUT, total)
