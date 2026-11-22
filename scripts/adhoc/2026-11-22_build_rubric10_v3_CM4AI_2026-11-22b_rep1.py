#!/usr/bin/env python3
"""Serialize one rubric10-semantic v3 evaluation of a single D4D record.

Purpose: turn the evaluator's per-release judgements (encoded below) for
  data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/CM4AI_d4d.yaml
  into the version-3.0 JSON the agent definition specifies, with digests,
  applicability (empty caller context -> unknown) and per-resource unit rows.
Inputs: the D4D record, data/rubric/rubric10.txt, the evidence authority,
  .claude/agents/d4d-rubric10-semantic.md (all read for hashes/names only).
Output: data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep1_evaluation.json
Serves: caller-requested single-record evaluation (instrument v3, #1061/#1058). Date: 2026-11-22.
The judgements (scores, evidence, issues) are the evaluator's; this script only
serializes them and filters `absent` names to those really unpopulated in a unit.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from data_sheets_schema.evaluation_context import (  # noqa: E402
    applicability, context_digest, dataset_units, load_document, normalize_context)

D4D = "data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/CM4AI_d4d.yaml"
OUT = "data/evaluation_llm/rubric10_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep1_evaluation.json"
RUBRIC = "data/rubric/rubric10.txt"
AUTH = "data/rubric/semantic_evidence_authority_v3.json"
AGENT = ".claude/agents/d4d-rubric10-semantic.md"
MODEL = "claude-opus-5-5"


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


doc, input_sha = load_document(ROOT / D4D)
units = dataset_units(doc)
UP = [p for p, _ in units]
U = dict(units)
context = normalize_context(None)
spec = yaml.safe_load((ROOT / RUBRIC).read_bytes())["d4d_complex_proxy_rubric"]["rubric"]


def populated(v):
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, dict)):
        vals = v.values() if isinstance(v, dict) else v
        return any(populated(c) for c in vals)
    return True


def is_absent(unit, name):
    node = unit
    for part in name.split("."):
        if not isinstance(node, dict) or part not in node:
            return True
        node = node[part]
    return not populated(node)


def row(i, score, evidence, cited=(), absent=(), considered=()):
    unit = U[UP[i]]
    return {"path": UP[i], "score": score, "evidence": evidence,
            "cited": [dict(path=p, quote=q) if q else dict(path=p) for p, q in cited],
            "absent": [{"path": a} for a in absent if is_absent(unit, a)],
            "counts": [], "considered": list(considered)}


ALL = range(4)
NOT_INHERITED = ("this release resource does not carry the field itself; the record's collection-level "
                 "values are not inherited by a member dataset under the instrument's scope rule")


def uniform(score, evidence, absent=(), considered=(), cited_fn=None):
    return [row(i, score, evidence, cited_fn(i) if cited_fn else (), absent, considered) for i in ALL]


def val(i, k):
    return U[UP[i]][k]


J = {}  # item_id -> (rows, quality_note, no_issue_reason or None)

# Element 1
J["E1.1"] = ([row(i, 1, f"doi {val(i, 'doi')} matches 10.XXXX/...; prefix 10.18130 is the University of Virginia Dataverse prefix the record names on its page URL.",
                  [("doi", val(i, "doi")), ("id", None)]) for i in ALL],
             "Every release carries a well-formed Dataverse DOI (10.18130/V3/...) also used as its id.")
J["E1.2"] = ([row(i, 1, f"title '{val(i, 'title')}' plus a release description over 200 characters naming the data modalities and cell lines.",
                  [("title", val(i, "title")), ("description", None)]) for i in ALL],
             "Each release has a specific title and a substantive description of its contents.")
J["E1.3"] = (uniform(0, "No keywords on this release; " + NOT_INHERITED + ".", ["keywords"], ["description"]),
             "Keywords exist only at collection level; no release carries its own.")
J["E1.4"] = ([row(i, 1, f"page {val(i, 'page')} is the release's Dataverse landing page.", [("page", "dataverse.lib.virginia.edu")]) for i in ALL],
             "Each release has its own Dataverse landing page.")
J["E1.5"] = (uniform(0, "No parent_datasets or related_datasets with typed relationships; the description only says the release is listed on the project's release page (untyped).",
                     ["parent_datasets", "related_datasets"], ["description"]),
             "Release-to-release and release-to-collection relationships are not encoded.")
# Element 2
J["E2.1"] = ([row(i, 1, "license 'CC BY-NC-SA 4.0' states the licensing terms governing access and reuse.", [("license", "CC BY-NC-SA 4.0")],
                  ["license_and_use_terms", "ip_restrictions"]) for i in ALL],
             "A named Creative Commons licence is recorded on every release; no IP restriction is attached at release level.")
J["E2.2"] = (uniform(0, "No regulatory, confidentiality, compliance or governance-contact field on this release; " + NOT_INHERITED + ".",
                     ["regulatory_restrictions", "data_governance", "confidentiality_level", "hipaa_compliant", "other_compliance"]),
             "Regulatory and governance documentation is absent from each release.")
J["E2.3"] = ([row(i, 1, "No download_url, but page is the release's Dataverse dataset page, a platform link from which its files are obtained.",
                  [("page", "persistentId=doi:10.18130")], ["download_url"]) for i in ALL],
             "Platform access link present on every release; no direct file download URL.")
J["E2.4"] = (uniform(0, "No distribution_formats, format or media_type on this release; file-level formats sit in the collection-level file_collections, outside the resource.",
                     ["distribution_formats", "format", "media_type", "file_collections"], ["description"]),
             "Formats are not attached to the release datasets.")
J["E2.5"] = (uniform(0, "No related_datasets or external_resources on this release.", ["related_datasets", "external_resources"],
                     ["description"]),
             "No links to related datasets or external documentation at release level.")
# Element 3
J["E3.1"] = ([row(i, 1, "license 'CC BY-NC-SA 4.0' is a clear reuse licence (attribution, non-commercial, share-alike).",
                  [("license", "CC BY-NC-SA 4.0")], ["license_and_use_terms"]) for i in ALL],
             "Clear Creative Commons reuse licence on each release.")
J["E3.2"] = (uniform(0, "No format or encoding stated on this release.", ["format", "encoding", "distribution_formats", "file_collections"], ["description"]),
             "Standard formats/encodings are not stated at release level.")
J["E3.3"] = (uniform(0, "No conforms_to or conforms_to_schema on this release.", ["conforms_to", "conforms_to_schema"], ["description"]),
             "No schema conformance on any release.")
J["E3.4"] = (uniform(0, "No variables on this release.", ["variables"]), "No variable-level metadata.")
J["E3.5"] = (uniform(0, "No intended, prohibited or discouraged uses on this release; " + NOT_INHERITED + ".",
                     ["intended_uses", "prohibited_uses", "discouraged_uses"], ["license"]),
             "Use guidance exists only at collection level.")
# Element 4
J["E4.1"] = (uniform(0, "No ethical_reviews, human_subject_research or data_protection_impacts on this release; " + NOT_INHERITED + ".",
                     ["ethical_reviews", "human_subject_research", "data_protection_impacts"]),
             "Ethics review documentation absent at release level.")
J["E4.2"] = (uniform(0, "No is_deidentified on this release.", ["is_deidentified"]), "De-identification not documented per release.")
J["E4.3"] = (uniform(0, "No participant_privacy or reidentification risk on this release.", ["participant_privacy"]),
             "No privacy/re-identification assessment per release.")
J["E4.4"] = (uniform(0, "No informed_consent on this release.", ["informed_consent"]), "Consent not documented per release.")
J["E4.5"] = (uniform(0, "No at_risk_populations or participant_compensation on this release.", ["at_risk_populations", "participant_compensation"]),
             "Not documented per release.")
# Element 5
q51 = {0: "undifferentiated KOLF2.1J iPSCs", 1: "undifferentiated KOLF2.1J iPSCs", 2: "undifferentiated (parental) KOLF2.1J iPSCs", 3: "undifferentiated (parental) KOLF2.1J iPSCs"}
J["E5.1"] = ([row(i, 1, "No subpopulations field, but the description states which cell lines, differentiation states and treatment conditions each data modality covers.",
                  [("description", q51[i]), ("description", "MDA-MB-468 breast cancer cells")], ["subpopulations"]) for i in ALL],
             "Cell-line/condition composition is stated per release in prose; cell-line provenance (RRID, donor) is only at collection level.")
J["E5.2"] = (uniform(0, "No instances and no counts of proteins, images, genes or cells in this release's own fields.", ["instances", "subsets"], ["description"]),
             "No per-release instance counts.")
J["E5.3"] = (uniform(0, "No variables, is_tabular or split/subpopulation flags on this release.", ["variables", "is_tabular", "subsets"]),
             "No variable metadata or split flags.")
J["E5.4"] = ([row(i, 1, "Description names the condition and data topics covered (breast cancer cells with/without chemotherapy, iPSC-derived lineages; Perturb-seq, SEC-MS, IF images).",
                  [("description", "MDA-MB-468 breast cancer cells")], ["instances"]) for i in ALL],
             "Topics/conditions are evident from each release description.")
J["E5.5"] = ([row(i, 0, "No anomalies, sampling_strategies or missing_data_documentation on this release" +
                  ("; the notes record an embargoed Perturb-seq data link, a single missing-data fact without a pattern or handling statement." if i == 2 else "."),
                  [], ["anomalies", "sampling_strategies", "missing_data_documentation"], ["notes"] if i == 2 else ["description"]) for i in ALL],
             "Data-quality and missing-data documentation is absent from the releases (one embargo note on the October 2025 release).")
# Element 6
J["E6.1"] = ([row(i, 1, f"version '{val(i, 'version')}' recorded.", [("version", val(i, "version"))]) for i in ALL],
             "Each release has a version number (Dataverse dataset versions, independent per release DOI).")
J["E6.2"] = (uniform(0, "No version_access on this release; " + NOT_INHERITED + ".", ["version_access"], ["doi"]),
             "Version-access guidance only at collection level.")
J["E6.3"] = ([row(1, 1, "Description states this release is a revision adding RGB IF images, ro-crate metadata corrections and naming-convention changes.",
                  [("description", "corrections to ro-crate metadata")], ["errata", "updates"])] +
             [row(i, 0, "No errata, updates or change description on this release.", [], ["errata", "updates"], ["description"]) for i in (0, 2, 3)],
             "Only the June 2025 release describes its changes; the minimum across releases is 0.")
J["E6.4"] = (uniform(0, "No updates/frequency on this release; " + NOT_INHERITED + ".", ["updates"]),
             "Update schedule only at collection level.")
J["E6.5"] = ([row(1, 1, "Description identifies this release as a revision of the June 2025 Data Release and states what changed.",
                  [("description", "a revision of the June 2025 Data Release")], ["was_derived_from", "raw_data_sources", "release_notes"])] +
             [row(i, 0, "No was_derived_from, raw_data_sources or release notes stating derivation for this release.", [],
                  ["was_derived_from", "raw_data_sources", "release_notes", "updates"], ["description"]) for i in (0, 2, 3)],
             "Derivation information only for the June 2025 release.")
# Element 7
J["E7.1"] = (uniform(0, "No purposes on this release; " + NOT_INHERITED + ".", ["purposes"], ["description"]),
             "Motivation only at collection level.")
J["E7.2"] = (uniform(0, "No tasks on this release.", ["tasks"]), "Tasks only at collection level.")
J["E7.3"] = (uniform(0, "No funders on this release; " + NOT_INHERITED + ".", ["funders"]), "Funding only at collection level.")
J["E7.4"] = (uniform(0, "No funders/grant numbers on this release.", ["funders"]), "Grant numbers only at collection level.")
J["E7.5"] = ([row(3, 1, "The citation lists the release's authors (Clark T ... Ideker T).", [("citation", "Ideker T")], ["creators", "funders"])] +
             [row(i, 0, "No creators, funders or author-bearing citation on this release.", [], ["creators", "funders", "citation"], ["description"]) for i in (0, 1, 2)],
             "Only the June 2026 release names its authors (via its citation).")
# Element 8
J["E8.1"] = (uniform(0, "No collection_mechanisms on this release; the description names data modalities, not collection procedures or settings.",
                     ["collection_mechanisms"], ["description"]), "Collection mechanisms only at collection level.")
J["E8.2"] = (uniform(0, "No acquisition_methods or raw_data_sources; modality labels (SEC-MS, Perturb-seq, IF images) do not describe instruments or capture methods.",
                     ["acquisition_methods", "raw_data_sources"], ["description"]), "Acquisition methods not described per release.")
J["E8.3"] = (uniform(0, "No preprocessing, cleaning, labeling, annotation or imputation fields on this release.",
                     ["preprocessing_strategies", "cleaning_strategies", "labeling_strategies", "annotation_analyses", "machine_annotation_tools", "imputation_protocols"]),
             "Processing not documented per release.")
J["E8.4"] = (uniform(0, "Nothing named: no software appears in any processing slot of this release (the collection-level MuSIC pipeline is not inherited, and the record itself says its outputs are not in the current release - role (e)).",
                     ["preprocessing_strategies", "cleaning_strategies", "labeling_strategies", "imputation_protocols", "machine_annotation_tools", "external_resources"],
                     ["description"]),
             "No processing software named at release level.")
J["E8.5"] = (uniform(0, "No external_resources, conforms_to or imputation_protocols on this release.", ["external_resources", "conforms_to", "imputation_protocols"]),
             "No standards or external documentation per release.")
# Element 9
J["E9.1"] = (uniform(0, "No known_limitations on this release; status 'Beta' alone is not a limitations statement.", ["known_limitations"], ["status"]),
             "Limitations only at collection level.")
J["E9.2"] = (uniform(0, "No known_biases or future_use_impacts on this release.", ["known_biases", "future_use_impacts"]), "No bias documentation per release.")
J["E9.3"] = ([row(i, 0, "No anomalies on this release" + ("; the embargo note is an availability fact, not a data-quality issue." if i == 2 else "."),
                  [], ["anomalies"], ["notes"] if i == 2 else []) for i in ALL],
             "No anomaly documentation per release.")
J["E9.4"] = (uniform(0, "No sensitive_elements or content_warnings on this release.", ["sensitive_elements", "content_warnings"]), "Not documented.")
J["E9.5"] = (uniform(0, "No ethical_reviews or future_use_impacts on this release.", ["ethical_reviews", "future_use_impacts"]), "Not documented per release.")
# Element 10
J["E10.1"] = ([row(i, 1, "No publisher field, but the page is on dataverse.lib.virginia.edu (University of Virginia Dataverse), a recognized repository" +
                   (" and the citation names 'University of Virginia Dataverse'." if i == 3 else "."),
                   [("page", "dataverse.lib.virginia.edu")] + ([("citation", "University of Virginia Dataverse")] if i == 3 else []), ["publisher"]) for i in ALL],
              "Each release is hosted on the UVA Dataverse, shown by its landing-page URL.")
J["E10.2"] = ([row(i, 1, "DOI present for cross-referencing" + ("; a full recommended citation is also given." if i == 3 else "; no citation string on this release."),
                   [("doi", val(i, "doi"))] + ([("citation", "https://doi.org/10.18130/V3/HIGT4C")] if i == 3 else []), ["citation"]) for i in ALL],
              "DOI on every release; formatted citation only on the June 2026 release.")
J["E10.3"] = (uniform(0, "No conforms_to on this release.", ["conforms_to"], ["description"]), "No community-standard conformance per release.")
J["E10.4"] = ([row(i, 1, "page is a documentation landing page for the release; no external_resources.", [("page", "dataverse.lib.virginia.edu")], ["external_resources"]) for i in ALL],
              "Landing pages present; no tutorials or other outreach links at release level.")
J["E10.5"] = (uniform(0, "No related_datasets with typed relationships on this release.", ["related_datasets"], ["description"]),
              "No typed relationships.")

ISSUES = [
    dict(type="completeness", category="scope_drift", severity="high",
         description="The record is an undeclared mapping with four release resources, so the instrument scores each release as a member dataset. The rich discovery, use-guidance, motivation, funding and attribution metadata is written only at collection level and is not inherited by the releases.",
         fields_involved=["keywords", "related_datasets", "intended_uses", "purposes", "tasks", "funders", "creators", "resources"],
         recommendation="Declare the parent as a Dataset (conforms_to_class) if it is the dataset to score, or attach the shared metadata to each release resource.",
         item_ids=["E1.3", "E1.5", "E2.5", "E3.5", "E7.1", "E7.2", "E7.3", "E7.4", "E7.5", "E10.5"], score_effect="lowered"),
    dict(type="completeness", category="format_access", severity="medium",
         description="File formats and media types are recorded in top-level file_collections and distribution_formats, outside the release resources; no release states its formats, encoding or standard conformance.",
         fields_involved=["file_collections", "distribution_formats", "conforms_to"],
         recommendation="Nest each release's file collection and formats (ZIP, JSON, HTML, RO-Crate) inside the release resource and state conformance there.",
         item_ids=["E2.4", "E3.2", "E3.3", "E8.5", "E10.3"], score_effect="lowered"),
    dict(type="completeness", category="consent_ethics", severity="medium",
         description="Ethics review, human-subjects status, de-identification, governance contact and regulatory statements are absent from every release resource.",
         fields_involved=["ethical_reviews", "human_subject_research", "is_deidentified", "data_governance", "regulatory_restrictions"],
         recommendation="Record each release's Data Governance & Ethics fields on the release itself.",
         item_ids=["E2.2", "E4.1", "E4.2", "E4.3", "E4.4", "E4.5", "E9.4", "E9.5"], score_effect="lowered"),
    dict(type="completeness", category="variables_metadata", severity="medium",
         description="No release reports instance counts, variables, tabular flags or split/subpopulation flags.",
         fields_involved=["instances", "variables", "is_tabular", "subsets"],
         recommendation="Add per-release counts (proteins, images, perturbed genes) and variable-level metadata.",
         item_ids=["E3.4", "E5.2", "E5.3"], score_effect="lowered"),
    dict(type="completeness", category="processing_provenance", severity="medium",
         description="Collection mechanisms, acquisition methods, processing steps and processing software are not documented on any release; derivation is stated only for the June 2025 release.",
         fields_involved=["collection_mechanisms", "acquisition_methods", "preprocessing_strategies", "was_derived_from", "raw_data_sources"],
         recommendation="Attach collection/acquisition methods, processing steps with named software, and derivation to each release.",
         item_ids=["E6.5", "E8.1", "E8.2", "E8.3", "E8.4"], score_effect="lowered"),
    dict(type="completeness", category="temporal_version", severity="medium",
         description="Version-access guidance, errata/change descriptions and update schedule are absent on the releases; only the June 2025 release describes its changes.",
         fields_involved=["version_access", "errata", "updates"],
         recommendation="Add change descriptions and version-access guidance to each release.",
         item_ids=["E6.2", "E6.3", "E6.4"], score_effect="lowered"),
    dict(type="completeness", category="bias_quality", severity="medium",
         description="Known limitations, biases, anomalies and missing-data documentation are absent from the releases (one embargo note on the October 2025 release).",
         fields_involved=["known_limitations", "known_biases", "anomalies", "missing_data_documentation"],
         recommendation="Record release-specific limitations, embargoes and quality issues on each release.",
         item_ids=["E5.5", "E9.1", "E9.2", "E9.3"], score_effect="lowered"),
    dict(type="consistency", category="temporal_version", severity="low",
         description="The June 2026 release carries version '2.0' while the earlier June and October 2025 releases carry '2.1'; the March 2025 release shows version 1.4 against a citation ending V1 (disclosed in source_caveats). Versions are per-DOI Dataverse versions, so they do not order the releases.",
         fields_involved=["resources", "version"], recommendation="State that version numbers are per-release Dataverse versions, not a series order.",
         item_ids=[], score_effect="noted_only"),
    dict(type="consistency", category="temporal_version", severity="low",
         description="The project's release page dates the June 2026 release 'June 17, 2025' while Dataverse gives 2026-06-17; the record discloses the conflict and uses the Dataverse date, which is consistent with the distribution_dates list.",
         fields_involved=["resources", "distribution_dates", "source_caveats"], recommendation="None beyond the existing caveat.",
         item_ids=[], score_effect="noted_only"),
    dict(type="content_accuracy", category="attribution", severity="low",
         description="Creator name 'Ballllosero Navarro F' contains an implausible run of four l characters, probably transcribed from the source author list.",
         fields_involved=["creators", "resources"], recommendation="Verify the spelling against the source author list.",
         item_ids=[], score_effect="noted_only"),
]

SKIP_REASON = None
elements, total = [], 0
for element in spec:
    subs, escore, emax = [], 0, 0
    for idx, sub in enumerate(element["sub_elements"], 1):
        key = f"E{element['id']}.{idx}"
        assert sub["item_id"] == key
        app = applicability(sub.get("applies_to"), context)
        rows, note = J[key]
        rows = sorted(rows, key=lambda r: UP.index(r["path"]))
        score = min(r["score"] for r in rows)
        escore += score
        emax += 1
        best = max(rows, key=lambda r: (r["score"], len(r["cited"])))
        subs.append({"name": sub["name"], "item_id": key, "score": score,
                     "evidence": "; ".join(f"{r['path']}: {r['evidence']}" for r in rows),
                     "quality_note": note, "applicable": app.applicable, "applicability_status": app.status,
                     "applicability_evidence": app.evidence, "unit_scores": rows})
    total += escore
    elements.append({"id": element["id"], "name": element["name"], "description": element["description"],
                     "sub_elements": subs, "element_score": escore, "element_max": emax})

result = {
    "rubric": "rubric10-semantic", "version": "3.0", "d4d_file": D4D, "project": "CM4AI",
    "method": "claudecode_agent", "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1",
    "evaluation_timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "model": {"name": MODEL, "evaluator_model": MODEL, "temperature": None,
              "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
              "evaluation_type": "semantic_llm_judge"},
    "overall_score": {"total_points": total, "max_points": 50, "excluded_max_points": 0, "adjusted_max_points": 50,
                      "normalized_percentage": round(100 * total / 50, 1), "fixed_percentage": round(100 * total / 50, 1),
                      "sub_elements_not_applicable": 0, "excluded_item_ids": []},
    "elements": elements,
    "semantic_analysis": {
        "issues_detected": ISSUES,
        "semantic_insights": [
            "Scope: the input has no class wrapper or conforms_to_class and has four nonempty resources, so the instrument's collection interpretation applies; each item score is the minimum over the four Dataverse releases, judged on each release's own fields.",
            "The collection-level record is far richer than its releases (keywords, use guidance, ethics review contacts, de-identification, subpopulations with RRIDs, collection mechanisms, MuSIC pipeline, funders with NIH award numbers, 47 creators, limitations, biases, missing-data patterns, quarterly update schedule); none of it is inherited by the releases, which explains the low score.",
            "Release resources carry title, DOI, version, issue date, landing page, licence and a modality/cell-line description; the June 2025 release adds a change description and the June 2026 release a full citation.",
            "Top-level ethics logic is internally consistent: human_subject_research.involves_human_subjects is false, the data come from commercially available de-identified cell lines, and two ethical-review contacts are named.",
            "Top-level grant numbers 1OT2OD032742-01, 3OT2OD032742-01S2 and 5U54HG012513-02 follow the NIH activity/institute/serial pattern; they are not credited to the releases.",
            "The record itself states that the MuSIC pipeline and LLM-based labeling apply to cell maps not included in the June 2026 release (role (e) for software evidence).",
        ],
        "consistency_checks": {"passed": 4, "failed": 0, "warnings": 2,
                               "details": ["passed: human subjects false with de-identified cell lines and no consent expected",
                                           "passed: licence CC BY-NC-SA 4.0 matches the no_commercial_use permission and the commercial prohibited use",
                                           "passed: grant numbers in funders.grants match funders.source_caveats",
                                           "passed: release issue dates ascend with release names (Dataverse dates)",
                                           "warning: per-release version numbers are not monotonic",
                                           "warning: release page and Dataverse disagree on the June 2026 release year (disclosed)"]},
        "correctness_validations": {"doi_format": "valid: four 10.18130/V3/* DOIs (University of Virginia Dataverse prefix)",
                                    "grant_number_format": "valid NIH patterns at collection level; none on release units",
                                    "rrid_format": "cell-line RRIDs (RRID:CVCL_0419, RRID:CVCL_B5P3) appear only in collection-level subpopulations; none on release units",
                                    "url_validity": "valid: Dataverse persistentId landing pages on dataverse.lib.virginia.edu"},
    },
    "applicability_context": context,
    "evaluation_scope": {"policy": "minimum_per_item_across_all_resource_datasets_v1",
                         "units": [{"path": p, "id": u.get("id")} for p, u in units],
                         "collection_metadata_inherited": False},
    "metadata": {"instrument_sha256": sha(AGENT), "evidence_authority_sha256": sha(AUTH),
                 "rubric_sha256": sha(RUBRIC), "input_sha256": input_sha, "context_sha256": context_digest(context),
                 "evaluator_model": MODEL, "caller_context_file": None},
}
out = ROOT / OUT
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(out, total)
