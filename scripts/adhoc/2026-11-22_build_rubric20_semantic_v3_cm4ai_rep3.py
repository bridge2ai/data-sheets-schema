#!/usr/bin/env python3
"""Assemble a rubric20-semantic v3 evaluation JSON for one CM4AI D4D record.

Purpose: serialize the evaluator's (claude-opus-5-5) manual judgements for
  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CM4AI_d4d.yaml
  under the general-context instrument v3 (.claude/agents/d4d-rubric20-semantic.md).
Inputs: the D4D record, data/rubric/rubric20.txt, the agent definition, the frozen
  evidence authority. No caller context file (empty applicability_context).
Output: data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep3_evaluation.json
Scores and evidence below are the evaluator's judgements; this script only computes
hashes, totals and the JSON structure. Date: 2026-11-22.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import yaml  # noqa: E402
from data_sheets_schema.evaluation_context import context_digest, dataset_units, load_document  # noqa: E402

INPUT = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3/CM4AI_d4d.yaml"
OUT = "data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep3_evaluation.json"
DEF = ".claude/agents/d4d-rubric20-semantic.md"
RUBRIC = "data/rubric/rubric20.txt"
AUTH = "data/rubric/semantic_evidence_authority_v3.json"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


document, input_sha = load_document(ROOT / INPUT)
units = [{"path": p, "id": u.get("id")} for p, u in dataset_units(document)]
assert [u["path"] for u in units] == [f"#/resources/{i}" for i in range(4)], units
R = [u["path"] for u in units]
spec = yaml.safe_load((ROOT / RUBRIC).read_bytes())["d4d_evaluation_rubric"]["rubric"]
rub = {q["id"]: q for q in spec}

context = {}
GATE = {8: "human_subjects", 10: "shared_dataset", 11: "data_processing", 12: "data_collection",
        13: "shared_dataset", 15: "human_subjects", 17: "shared_dataset"}


def row(path, score, evidence, cited=(), absent=(), counts=(), considered=()):
    return {"path": path, "score": score, "evidence": evidence,
            "cited": [dict(c) for c in cited], "absent": [{"path": a} for a in absent],
            "counts": [{"path": p, "claimed": n} for p, n in counts], "considered": list(considered)}


def same(score, evidence, cited=(), absent=(), counts=(), considered=()):
    return [row(p, score, evidence, cited, absent, counts, considered) for p in R]


def q(cid, score_label, evidence, quality_note, rows, no_issue_reason=None):
    return dict(id=cid, score_label=score_label, evidence=evidence, quality_note=quality_note,
                rows=rows, no_issue_reason=no_issue_reason)


DOI_Q = ["10.18130/V3/B35XWX", "10.18130/V3/F3TD5R", "10.18130/V3/K7TGEM", "10.18130/V3/HIGT4C"]
NOT_INHERITED = ("Scored on this resource's own fields; the parent mapping's metadata is not inherited "
                 "(collection_metadata_inherited: false).")

Q = []
# ---------------- Q1
q1_absent = ["keywords", "license_and_use_terms", "page", "creators", "purposes", "instances", "resources",
             "parent_datasets", "variables", "regulatory_restrictions"]
Q.append(q(1, "Absent (<=40% of declared fields)",
           "Each resource populates id, title, description and doi (4 of 14 declared fields, 29%); keywords, "
           "license_and_use_terms, page, creators, purposes, instances, resources, parent_datasets, variables and "
           "confidentiality_level are absent at every resource.",
           "The parent mapping is rich, but under the collection policy each Dataverse release is a scored unit "
           "and none carries the core descriptive fields itself.",
           [row(p, 0, f"{NOT_INHERITED} Populated: id, title, description, doi (4/14).",
                cited=[{"path": "id"}, {"path": "title"}, {"path": "description"}, {"path": "doi", "quote": d}],
                absent=q1_absent) for p, d in zip(R, DOI_Q)]))
# ---------------- Q2
Q.append(q(2, "Good (50-200 average)",
           "Each resource description exceeds 200 characters (release content summary), but purposes is absent "
           "at every resource, so the narrative-field average falls in the middle band.",
           "Descriptions are specific (assays, cell lines, conditions) but no resource states a purpose.",
           [row(p, 3, f"description has {len(document['resources'][i]['description'])} characters; purposes absent.",
                cited=[{"path": "description", "quote": qt}], absent=["purposes"])
            for i, (p, qt) in enumerate(zip(R, ["Historical release. This Beta release includes perturb-seq data",
                                                "A revision of the June 2025 Data Release",
                                                "Superseded release.", "Current release."]))]))
# ---------------- Q3
Q.append(q(3, "Absent (<3 keywords)", "No resource has keywords.",
           "Keywords exist only on the parent mapping, which is not inherited.",
           same(0, f"{NOT_INHERITED} keywords absent.", absent=["keywords"], considered=["title"])))
# ---------------- Q4
Q.append(q(4, "Absent (1 file type at worst resource)",
           "March 2025: JSON + ZIP (2 types); June 2025: JSON + HTML + ZIP (3); October 2025 and June 2026: ZIP "
           "only (1 type). Minimum across resources is the single-type band.",
           "The current release enumerates ten ZIP archives with md5 checksums, but only one container type is "
           "documented; inner file types of the archives are not described.",
           [row(R[0], 3, "Four file collections listing ro-crate-metadata.json (JSON) and three IF image ZIPs; "
                         "total_file_count 6.",
                cited=[{"path": "file_collections.resources.format", "quote": "JSON"},
                       {"path": "file_collections.resources.format", "quote": "ZIP"},
                       {"path": "total_file_count", "quote": "6"}],
                counts=[("file_collections", 4)], absent=["distribution_formats"]),
            row(R[1], 3, "Three collections: HTML datasheet/provenance graphs, JSON RO-Crate metadata, ZIP image "
                         "archives; total_file_count 21 but only 10 described.",
                cited=[{"path": "file_collections.resources.format", "quote": "HTML"},
                       {"path": "file_collections.resources.format", "quote": "JSON"},
                       {"path": "file_collections.resources.format", "quote": "ZIP"},
                       {"path": "total_file_count", "quote": "21"},
                       {"path": "source_caveats", "quote": "only those 10 are described in file_collections"}],
                counts=[("file_collections", 3)], absent=["distribution_formats"]),
            row(R[2], 0, "All eight listed files are ZIP archives; one file type.",
                cited=[{"path": "file_collections.resources.format", "quote": "ZIP"},
                       {"path": "total_file_count", "quote": "8"}],
                counts=[("file_collections", 2)], absent=["distribution_formats"]),
            row(R[3], 0, "Ten ZIP archives only; one file type.",
                cited=[{"path": "file_collections.resources.format", "quote": "ZIP"},
                       {"path": "total_file_count", "quote": "10"}],
                counts=[("file_collections", 1), ("/file_collections/0/resources", 10)],
                absent=["distribution_formats"])]))
# ---------------- Q5
q5_abs = ["total_size_bytes", "file_collections.total_bytes", "instances", "splits", "subpopulations"]
Q.append(q(5, "Fail", "No resource gives byte sizes or instance counts; only total_file_count is given.",
           "A file count is neither a size nor an instance count; the parent's instance counts and 21.4 TB volume "
           "are not inherited.",
           [row(p, 0, f"{NOT_INHERITED} No bytes or instance count; total_file_count {n} only.",
                cited=[{"path": "total_file_count", "quote": str(n)}], absent=q5_abs)
            for p, n in zip(R, [6, 21, 8, 10])]))
# ---------------- Q6
Q.append(q(6, "Pass", "Every resource carries a DataCite DOI with the 10.18130 (University of Virginia Dataverse) "
                      "prefix as doi and id.",
           "Publisher is not a field of the resources, but the citation names University of Virginia Dataverse.",
           [row(p, 1, f"doi {d}; citation names University of Virginia Dataverse.",
                cited=[{"path": "doi", "quote": d}, {"path": "id"},
                       {"path": "citation", "quote": "University of Virginia Dataverse"}])
            for p, d in zip(R, DOI_Q)]))
# ---------------- Q7
Q.append(q(7, "Good (creator info without funding/affiliations)",
           "Resources have no funders or creators fields; each citation names authors (Clark T; Parker J; Al Manir "
           "S; et al.; Ideker T) without affiliations or grants.",
           "Creator information is present only as an abbreviated citation author list; no funding data.",
           same(3, f"{NOT_INHERITED} Authors only in the citation string; funders and creators absent.",
                cited=[{"path": "citation", "quote": "Parker"}], absent=["funders", "creators"])))
# ---------------- Q8
q8_abs = ["ethical_reviews", "human_subject_research", "is_deidentified", "participant_privacy",
          "informed_consent", "data_protection_impacts", "at_risk_populations", "participant_compensation"]
Q.append(q(8, "Absent", "No resource carries any ethics or privacy declaration.",
           "The parent's human_subject_research (false), de-identification statement and ethics contacts are not "
           "inherited; human_subjects is undeclared, so the item stays applicable.",
           same(0, f"{NOT_INHERITED} No ethics/privacy fields.", absent=q8_abs, considered=["description"])))
# ---------------- Q9
Q.append(q(9, "Good (license only)", "Each resource states license CC BY-NC-SA 4.0; no ip_restrictions, "
                                     "regulatory_restrictions or confidentiality classification.",
           "The noncommercial restriction is implied by the license name only; access tier is not described.",
           same(3, "license CC BY-NC-SA 4.0; no restrictions or confidentiality level.",
                cited=[{"path": "license", "quote": "CC BY-NC-SA 4.0"}],
                absent=["license_and_use_terms", "ip_restrictions", "regulatory_restrictions"])))
# ---------------- Q10
Q.append(q(10, "Good (standard formats, no schema reference)",
           "Resources list standard formats (ZIP, JSON, HTML with media types); RO-Crate metadata files appear in the "
           "March and June 2025 file lists, but no resource declares conforms_to or conforms_to_schema.",
           "Standard container formats; schema conformance and integration capability are not declared per release.",
           [row(p, 3, ev, cited=c, absent=["conforms_to", "conforms_to_schema", "external_resources",
                                           "related_datasets", "distribution_formats"])
            for p, ev, c in [
                (R[0], "ZIP/JSON formats; ro-crate-metadata.json files listed but no declared conformance.",
                 [{"path": "file_collections.resources.media_type", "quote": "application/json"},
                  {"path": "file_collections.resources.name", "quote": "ro-crate-metadata.json"}]),
                (R[1], "ZIP/JSON/HTML; release RO-Crate described but no declared conformance.",
                 [{"path": "file_collections.resources.description",
                   "quote": "Release RO-Crate with pointers to sub RO-Crates."}]),
                (R[2], "ZIP archives (application/zip); no schema reference.",
                 [{"path": "file_collections.resources.media_type", "quote": "application/zip"}]),
                (R[3], "ZIP archives (application/zip); no schema reference.",
                 [{"path": "file_collections.resources.media_type", "quote": "application/zip"}])]]))
# ---------------- Q11
q11_abs = ["preprocessing_strategies", "cleaning_strategies", "labeling_strategies", "machine_annotation_tools",
           "annotation_analyses", "imputation_protocols"]
Q.append(q(11, "Absent", "No resource documents preprocessing, cleaning, labeling or annotation tools.",
           "The parent's MuSIC and FAIRSCAPE descriptions are not inherited; the June 2025 description mentions "
           "metadata corrections and renaming without naming a tool.",
           same(0, f"{NOT_INHERITED} No processing strategies or tools.", absent=q11_abs,
                considered=["description"])))
# ---------------- Q12
q12_abs = ["collection_timeframes", "acquisition_methods", "collection_mechanisms", "data_collectors",
           "raw_data_sources"]
Q.append(q(12, "Good (partial protocol)",
           "Resources name assays (Perturb-seq, SEC-MS, AP-MS, IF imaging) and, in file descriptions, the Lundberg "
           "and Krogan laboratories; no collection timeframes or structured collection fields.",
           "Mechanism and collector names appear only in narrative; timeframes are missing.",
           [row(R[0], 3, "Mechanism (ICC-IF confocal microscopy) and collector (Lundberg Lab) in file description.",
                cited=[{"path": "file_collections.description",
                        "quote": "immunofluorescence-based staining (ICC-IF) and confocal microscopy in the Lundberg Lab"}],
                absent=q12_abs),
            row(R[1], 3, "Mechanisms named in release description; no collectors or timeframes.",
                cited=[{"path": "description", "quote": "SEC-MS data in undifferentiated"}], absent=q12_abs),
            row(R[2], 3, "SEC-MS by the Krogan laboratory in file descriptions; no timeframes.",
                cited=[{"path": "file_collections.resources.description", "quote": "in the Nevan Krogan laboratory"}],
                absent=q12_abs),
            row(R[3], 3, "Assay types named only in the release description.",
                cited=[{"path": "description", "quote": "AP-MS data for MDA-MB-468 breast cancer cells + treatment"}],
                absent=q12_abs)]))
# ---------------- Q13
Q.append(q(13, "Good (version + persistent ID)",
           "Each resource gives a version, issued date, DOI and release status (historical/superseded/current); "
           "no maintainers, update plan, errata or version_access at resource level.",
           "Version header vs citation version mismatches are disclosed in source_caveats (e.g. 2.1 vs V2).",
           [row(p, 3, f"version {v}; doi {d}; no maintenance or sustainability fields.",
                cited=[{"path": "version", "quote": v}, {"path": "doi", "quote": d}, {"path": "issued"},
                       {"path": "source_caveats", "quote": "while the citation reads"}],
                absent=["maintainers", "updates", "errata", "version_access", "publisher"])
            for p, v, d in zip(R, ["1.4", "2.1", "2.1", "2.0"], DOI_Q)]))
# ---------------- Q14
Q.append(q(14, "Good (one distinct reference + formal citation)",
           "Each resource has a formal Dataverse citation (authors, year, title, DOI URL, publisher, version); the "
           "DOI and citation identify the same resource, and no external_resources are given at resource level.",
           "Formal dataset citation present, but only one distinct reference per resource.",
           [row(p, 3, "Formal citation present; DOI counts as the same reference; no external resources.",
                cited=[{"path": "citation", "quote": f"https://doi.org/{d}"}, {"path": "doi", "quote": d}],
                absent=["external_resources"]) for p, d in zip(R, DOI_Q)]))
# ---------------- Q15
Q.append(q(15, "Good (general human-derived material, no demographics)",
           "Resources name human-derived cell lines (MDA-MB-468 breast cancer cells, KOLF2.1J iPSCs and derived NPCs, "
           "neurons, cardiomyocytes) and treatment conditions, without donor demographics or selection criteria.",
           "Population characterization is limited to cell-line names and conditions; the parent's RRID and donor "
           "descriptions are in subpopulations, which is not inherited.",
           [row(p, 3, "Cell lines and conditions named; no demographics or subgroup fields.",
                cited=[{"path": "description", "quote": qt}],
                absent=["subpopulations", "instances", "at_risk_populations", "missing_data_documentation"])
            for p, qt in zip(R, ["KOLF2.1J iPSCs", "MDA-MB-468 breast cancer cells", "MDA-MB-468 breast cancer cells",
                                 "KOLF2.1J iPSCs"])]))
# ---------------- Q16
Q.append(q(16, "Pass", "Each resource has a resolvable DOI and a https://doi.org/ URL in its citation.",
           "DOI prefix 10.18130 matches the University of Virginia Dataverse registrant.",
           [row(p, 1, f"doi {d}.", cited=[{"path": "doi", "quote": d}, {"path": "id"}]) for p, d in zip(R, DOI_Q)]))
# ---------------- Q17
Q.append(q(17, "Good (partial access mechanism)",
           "Resources give license, ZIP formats and a DOI landing page via the citation; no download_url, "
           "registration or agreement steps.",
           "Access tier (open download vs registration) is not stated per release.",
           same(3, "License and formats present; access path only implied by Dataverse DOI.",
                cited=[{"path": "license", "quote": "CC BY-NC-SA 4.0"},
                       {"path": "file_collections.resources.media_type", "quote": "application/zip"}],
                absent=["download_url", "license_and_use_terms", "distribution_formats"])))
# ---------------- Q18
Q.append(q(18, "Good (license without explicit use guidance)",
           "Each resource names CC BY-NC-SA 4.0; intended, prohibited and discouraged uses and future-use impacts are "
           "absent at resource level.",
           "The license name conveys noncommercial/share-alike terms; no explicit use guidance or impact analysis.",
           same(3, "license only; no use guidance or social impact fields.",
                cited=[{"path": "license", "quote": "CC BY-NC-SA 4.0"}],
                absent=["license_and_use_terms", "intended_uses", "prohibited_uses", "discouraged_uses",
                        "future_use_impacts"])))
# ---------------- Q19
q19_abs = ["version_access", "errata", "updates", "was_derived_from", "parent_datasets", "raw_data_sources",
           "missing_data_documentation"]
Q.append(q(19, "Good (version information, no provenance graph)",
           "Resources give version numbers, issue dates and release status; the June 2025 release describes its "
           "revision and lists per-condition provenance-graph HTML files, but no resource documents entity-activity-"
           "agent lineage.",
           "Version history is fragmentary per release; provenance graphs are referenced as files, not represented.",
           [row(R[0], 3, "version 1.4, historical release; no derivation fields.",
                cited=[{"path": "version", "quote": "1.4"}, {"path": "description", "quote": "Historical release."}],
                absent=q19_abs),
            row(R[1], 3, "Revision notes and provenance-graph files listed; graph content not documented.",
                cited=[{"path": "description",
                        "quote": "adds RGB immunofluorescent images, corrects RO-Crate metadata, and changes naming conventions"},
                       {"path": "file_collections.resources.name", "quote": "Images-paclitaxel-provenance-graph.html"}],
                absent=q19_abs),
            row(R[2], 3, "version 2.1, superseded release.",
                cited=[{"path": "version", "quote": "2.1"}, {"path": "description", "quote": "Superseded release."}],
                absent=q19_abs),
            row(R[3], 3, "version 2.0, current release; created_on and issued dates.",
                cited=[{"path": "version", "quote": "2.0"}, {"path": "created_on"}, {"path": "issued"}],
                absent=q19_abs)]))
# ---------------- Q20
Q.append(q(20, "Absent", "No resource documents known biases or future-use impacts.",
           "The parent's two known_biases entries are not inherited.",
           same(0, f"{NOT_INHERITED} known_biases and future_use_impacts absent.",
                absent=["known_biases", "future_use_impacts", "known_limitations"])))

# ---------------- issues
issues = [
    {"type": "completeness", "category": "scope_drift", "severity": "high", "score_effect": "lowered",
     "item_ids": ["Q1", "Q3", "Q5", "Q7", "Q8", "Q11", "Q20"],
     "description": "The record is an undeclared mapping whose four Dataverse releases sit under resources, so each "
                    "release is a scored unit; the descriptive, funding, ethics, processing and bias metadata live only "
                    "on the parent mapping and are not inherited by any release.",
     "fields_involved": ["resources", "keywords", "creators", "funders", "ethical_reviews", "known_biases",
                         "preprocessing_strategies", "instances"],
     "recommendation": "Declare the record as a Dataset (conforms_to_class) if the series is the dataset to score, "
                       "or give each release its own descriptive, governance and bias metadata."},
    {"type": "completeness", "category": "format_access", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["Q4", "Q10", "Q17"],
     "description": "The October 2025 and June 2026 releases list only ZIP archives with no inner file types, "
                    "conformance declaration or download/access steps.",
     "fields_involved": ["file_collections", "distribution_formats", "conforms_to", "download_url"],
     "recommendation": "Document the file types inside each archive, the RO-Crate conformance and the access path."},
    {"type": "completeness", "category": "temporal_version", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["Q13", "Q19"],
     "description": "Release-level versioning is limited to a version number and dates; maintenance, errata and "
                    "derivation links between successive releases are not recorded on the releases.",
     "fields_involved": ["version", "version_access", "errata", "was_derived_from", "updates"],
     "recommendation": "Record per-release change notes, derivation from the prior release and maintainers."},
    {"type": "completeness", "category": "license_use_terms", "severity": "medium", "score_effect": "lowered",
     "item_ids": ["Q9", "Q18"],
     "description": "Each release gives only the license name; no restrictions, confidentiality level or explicit "
                    "use guidance.",
     "fields_involved": ["license", "license_and_use_terms", "ip_restrictions", "intended_uses"],
     "recommendation": "Attach license_and_use_terms, ip_restrictions and use guidance to each release."},
    {"type": "completeness", "category": "processing_provenance", "severity": "low", "score_effect": "lowered",
     "item_ids": ["Q2", "Q12", "Q14", "Q15"],
     "description": "Release descriptions are specific but no release states a purpose, collection timeframe, "
                    "second reference or donor characterization.",
     "fields_involved": ["purposes", "collection_timeframes", "external_resources", "subpopulations"],
     "recommendation": "Add purposes, collection timeframes, related publications and cell-line characterization "
                       "per release."},
    {"type": "consistency", "category": "source_conflict", "severity": "low", "score_effect": "noted_only",
     "item_ids": [],
     "description": "Version headers disagree with citation versions (1.4 vs V1, 2.1 vs V2, 2.0 vs V2), and the "
                    "June 2026 release date conflicts between cm4ai.org (2025) and Dataverse (2026); both are "
                    "disclosed in source_caveats.",
     "fields_involved": ["version", "citation", "issued", "source_caveats"],
     "recommendation": "Keep the disclosed caveats; prefer the repository's version identifier consistently."},
    {"type": "consistency", "category": "count_size", "severity": "low", "score_effect": "noted_only",
     "item_ids": [],
     "description": "The June 2025 release declares 21 files but describes only 10 (disclosed); image-protein counts "
                    "differ across releases (563, 464).",
     "fields_involved": ["total_file_count", "file_collections"],
     "recommendation": "Enumerate all files or state the omission in total_file_count context."},
]

cat_names = ["Structural Completeness", "Metadata Quality & Content", "Technical Documentation",
             "FAIRness & Accessibility"]
categories = []
total = 0
for ci, name in enumerate(cat_names):
    questions = []
    cs = cmax = 0
    for item in Q[ci * 5:(ci + 1) * 5]:
        r = rub[item["id"]]
        pf = item["id"] in (5, 6, 16)
        mx = 1 if pf else 5
        score = min(x["score"] for x in item["rows"])
        gate = GATE.get(item["id"])
        qd = {"id": item["id"], "name": r["name"], "description": " ".join(r["description"].split())[:120],
              "score_type": "pass_fail" if pf else "numeric", "score": score, "max_score": mx,
              "score_label": item["score_label"], "evidence": item["evidence"],
              "quality_note": item["quality_note"], "applicable": True,
              "applicability_status": "unknown" if gate else "applicable",
              "applicability_evidence": (f"{gate}: not declared; retained in the denominator" if gate
                                         else "This item applies to every dataset"),
              "unit_scores": item["rows"]}
        if item["no_issue_reason"]:
            qd["no_issue_reason"] = item["no_issue_reason"]
        questions.append(qd)
        cs += score
        cmax += mx
    total += cs
    categories.append({"name": name, "questions": questions, "category_score": cs, "category_max": cmax})

model = "claude-opus-5-5"
result = {
    "rubric": "rubric20-semantic", "version": "3.0",
    "d4d_file": INPUT, "project": "CM4AI", "method": "claudecode_agent",
    "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep3",
    "evaluation_timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {"name": model, "evaluator_model": model, "temperature": None,
              "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
              "evaluation_type": "semantic_llm_judge"},
    "overall_score": {"total_points": total, "max_points": 88, "excluded_max_points": 0,
                      "adjusted_max_points": 88, "normalized_percentage": round(100 * total / 88, 2),
                      "fixed_percentage": round(100 * total / 88, 2), "questions_not_applicable": 0,
                      "excluded_item_ids": []},
    "categories": categories,
    "semantic_analysis": {
        "issues_detected": issues,
        "semantic_insights": [
            "Scope: the input has no Dataset/CoreDataset declaration and four nonempty resources, so the four "
            "Dataverse releases are the scored units and each item score is the minimum across them.",
            "The parent mapping documents creators with ORCIDs, NIH award OT2OD032742, ethics contacts, governance, "
            "intended/prohibited uses, known biases and processing pipelines; none of this is scored because it is "
            "not inherited by the releases.",
            "Release-level DOIs (10.18130 prefix, UVA Dataverse) are well-formed and match formal citations.",
            "human_subjects, shared_dataset, data_collection and data_processing are undeclared by the caller, so "
            "Q8, Q10-Q13, Q15 and Q17 stay applicable.",
        ],
        "consistency_checks": {"passed": 3, "failed": 0, "warnings": 2},
        "correctness_validations": {"doi_format": "valid", "grant_number_format": "not_present",
                                    "rrid_format": "not_present", "url_validity": "all_valid"},
    },
    "assessment": {
        "strengths": ["Every release has a DOI, version, issue date and formal citation",
                      "Release file lists carry md5 checksums and media types"],
        "weaknesses": ["Releases carry no descriptive, funding, ethics, use-guidance or bias metadata of their own",
                       "Recent releases document only ZIP containers"],
        "recommendations": ["Declare the series as a Dataset or populate per-release metadata",
                            "Describe archive contents, sizes and conformance per release"],
    },
    "applicability_context": context,
    "evaluation_scope": {"policy": "minimum_per_item_across_all_resource_datasets_v1", "units": units,
                         "collection_metadata_inherited": False},
    "metadata": {"instrument_sha256": sha(DEF), "evidence_authority_sha256": sha(AUTH),
                 "rubric_sha256": sha(RUBRIC), "input_sha256": input_sha,
                 "context_sha256": context_digest(context)},
}
out = ROOT / OUT
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(out, total)
