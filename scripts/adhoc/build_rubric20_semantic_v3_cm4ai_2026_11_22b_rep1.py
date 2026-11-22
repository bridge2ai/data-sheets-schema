#!/usr/bin/env python3
"""Serialize a manual rubric20-semantic v3 evaluation of one D4D record.

Purpose: write the judgements made by the evaluating session (claude-opus-5-5)
for data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/CM4AI_d4d.yaml
into the version-3.0 JSON contract of .claude/agents/d4d-rubric20-semantic.md.
Inputs: the D4D record (read-only), the agent definition, rubric text and
evidence authority (hashed only). Output:
data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep1_evaluation.json
Scores are hand-assigned below; the script only computes digests and sums.
Date: 2026-11-22.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")
from data_sheets_schema.evaluation_context import context_digest, dataset_units, load_document  # noqa: E402

INPUT = Path("data/d4d_concatenated/claudecode_agent/2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1/CM4AI_d4d.yaml")
OUT = Path("data/evaluation_llm/rubric20_semantic/2026-11-22_general_context_v3/CM4AI_2026-11-22b_rep1_evaluation.json")
DEFN = Path(".claude/agents/d4d-rubric20-semantic.md")
RUBRIC = Path("data/rubric/rubric20.txt")
AUTH = Path("data/rubric/semantic_evidence_authority_v3.json")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


doc, input_sha = load_document(INPUT)
units = dataset_units(doc)
U = [p for p, _ in units]  # '#/resources/0' .. '#/resources/3'
R0, R1, R2, R3 = U

ALWAYS = ("applicable", "This item applies to every dataset")


def pred(name):
    return ("unknown", f"{name}: not declared; retained in the denominator")


def row(path, score, evidence, cited=(), absent=(), counts=(), considered=()):
    return {"path": path, "score": score, "evidence": evidence,
            "cited": [dict(c) if isinstance(c, dict) else {"path": c} for c in cited],
            "absent": [{"path": a} for a in absent],
            "counts": list(counts), "considered": list(considered)}


BASIC = ["id", "title", "doi", "page"]

# ---------------------------------------------------------------- questions
Q = {}

# Q1 Field completeness (14 fields): each resource has id,title,description,doi,page (5/14 = 36%);
# its 'license' string is a related but different field from license_and_use_terms.
q1_abs = ["keywords", "license_and_use_terms", "creators", "purposes", "instances",
          "resources", "parent_datasets", "variables", "regulatory_restrictions"]
Q[1] = dict(name="Field Completeness", score_type="numeric", max=5, app=ALWAYS,
            label="Absent (<=40% of fields)",
            evidence="Each release dataset populates id, title, description, doi and page (5 of 14 listed fields, ~36%); keywords, license_and_use_terms, creators, purposes, instances, resources, parent_datasets, variables and confidentiality_level are absent at resource level.",
            note="Collection-level keywords, creators and purposes exist at the top level but are not inherited by the member release datasets under the conservative collection policy.",
            rows=[row(u, 0, "5 of 14 Q1 fields populated in this release dataset (id, title, description, doi, page); license is a plain string, not license_and_use_terms.",
                      cited=BASIC + ["description"], absent=q1_abs, considered=["license", "version"]) for u in U],
            issue=None)

# Q2 Entry length: description >200 chars in every resource; purposes absent.
Q[2] = dict(name="Entry Length Adequacy", score_type="numeric", max=5, app=ALWAYS,
            label="Good (description long, purposes missing)",
            evidence="Every release description exceeds 200 characters (e.g., March 2025: 'This Beta release includes perturb-seq data in undifferentiated KOLF2.1J iPSCs'), but no purposes statement is attached to any release; averaged over both narrative fields the entry length falls in the 50-200 band.",
            note="Descriptions are informative about contents but purposes are documented only at collection level.",
            rows=[row(u, 3, "Long description present; purposes absent, so the two-field average is in the middle band.",
                      cited=["description"], absent=["purposes"]) for u in U])

# Q3 Keywords
Q[3] = dict(name="Keyword Diversity", score_type="numeric", max=5, app=ALWAYS,
            label="Absent (<3 keywords)",
            evidence="No keywords field in any release dataset; the 29 collection-level keywords are not inherited.",
            note="Keyword discoverability exists only at the undeclared collection wrapper.",
            rows=[row(u, 0, "No keywords in this release dataset.", absent=["keywords"], considered=["title"]) for u in U])

# Q4 File types
Q[4] = dict(name="File Enumeration and Type Variety", score_type="numeric", max=5, app=ALWAYS,
            label="Absent (no file types at resource level)",
            evidence="No distribution_formats, file_collections or total_file_count inside any release dataset. The top-level file_collections enumerate ZIP/JSON/HTML files per release by id fragment but are not nested in, or linked from, the release datasets.",
            note="File enumeration is attached to the collection, not to each release; under the non-inheritance rule each release documents no file types.",
            rows=[row(u, 0, "No distribution_formats, file_collections or total_file_count in this release dataset.",
                      absent=["distribution_formats", "file_collections", "total_file_count"], considered=["description"]) for u in U])

# Q5 Size
Q[5] = dict(name="Data File Size Availability", score_type="pass_fail", max=1, app=ALWAYS,
            label="Fail",
            evidence="No total_size_bytes, instances, splits or subpopulations in any release dataset; listed sizes appear only in top-level file_collections descriptions.",
            note="Size metadata is not carried by the scored units.",
            rows=[row(u, 0, "No byte size or instance count in this release dataset.",
                      absent=["total_size_bytes", "instances", "subpopulations"], considered=["description"]) for u in U])

# Q6 Identification
Q[6] = dict(name="Dataset Identification Metadata", score_type="pass_fail", max=1, app=ALWAYS,
            label="Pass",
            evidence="Each release carries a DOI with the 10.18130 prefix (University of Virginia Dataverse) and a dataverse.lib.virginia.edu landing page, e.g., doi 10.18130/V3/HIGT4C.",
            note="Persistent identifiers valid in form; hosting platform is evident from the landing page domain (and the June 2026 citation names 'University of Virginia Dataverse'), though no publisher field is set.",
            rows=[row(R0, 1, "DOI 10.18130/V3/B35XWX and Dataverse landing page.", cited=[{"path": "doi", "quote": "10.18130/V3/B35XWX"}, "page", "id"], absent=["publisher"]),
                  row(R1, 1, "DOI 10.18130/V3/F3TD5R and Dataverse landing page.", cited=[{"path": "doi", "quote": "10.18130/V3/F3TD5R"}, "page", "id"], absent=["publisher"]),
                  row(R2, 1, "DOI 10.18130/V3/K7TGEM and Dataverse landing page.", cited=[{"path": "doi", "quote": "10.18130/V3/K7TGEM"}, "page", "id"], absent=["publisher"]),
                  row(R3, 1, "DOI 10.18130/V3/HIGT4C, landing page, and citation naming University of Virginia Dataverse.",
                      cited=[{"path": "doi", "quote": "10.18130/V3/HIGT4C"}, "page", "id", {"path": "citation", "quote": "University of Virginia Dataverse"}], absent=["publisher"])])

# Q7 Funding
Q[7] = dict(name="Funding and Acknowledgements Completeness", score_type="numeric", max=5, app=ALWAYS,
            label="Absent (minimum across releases)",
            evidence="No funders or creators in any release dataset. Only the June 2026 release lists author names inside its citation string (no affiliations). Collection-level funders (NIH 1OT2OD032742-01 etc.) and affiliated creators are not inherited.",
            note="Item score is the minimum: three releases document no funding or authorship at all.",
            rows=[row(R0, 0, "No funders or creators.", absent=["funders", "creators"]),
                  row(R1, 0, "No funders or creators.", absent=["funders", "creators"]),
                  row(R2, 0, "No funders or creators.", absent=["funders", "creators"]),
                  row(R3, 3, "Author names appear in the citation string, but no funders, grants or affiliations.",
                      cited=[{"path": "citation", "quote": "Clark T; Parker J; Al Manir S"}], absent=["funders", "creators"])])

# Q8 Ethics (human_subjects unknown)
Q[8] = dict(name="Ethical and Privacy Declarations", score_type="numeric", max=5, app=pred("human_subjects"),
            label="Absent",
            evidence="No ethical_reviews, human_subject_research, is_deidentified, informed_consent or participant_privacy fields in any release dataset. The collection-level 'Human Subjects: No' and de-identification statements are not inherited.",
            note="Applicability retained as unknown because no caller context was supplied; the record's own human_subject_research=false cannot establish N/A for the evaluator.",
            rows=[row(u, 0, "No ethics or privacy fields in this release dataset.",
                      absent=["ethical_reviews", "human_subject_research", "is_deidentified", "informed_consent", "participant_privacy", "data_protection_impacts"]) for u in U])

# Q9 Access/governance
Q[9] = dict(name="Access Requirements and Governance Documentation", score_type="numeric", max=5, app=ALWAYS,
            label="License only",
            evidence="Each release states license 'CC BY-NC-SA 4.0'; no ip_restrictions, regulatory_restrictions, confidentiality classification or governance contact at resource level.",
            note="A named NC-SA license is documented but access steps, IP holders and governance are only at collection level.",
            rows=[row(u, 3, "License string present; no restrictions or confidentiality classification.",
                      cited=[{"path": "license", "quote": "CC BY-NC-SA 4.0"}],
                      absent=["license_and_use_terms", "ip_restrictions", "regulatory_restrictions", "data_protection_impacts"]) for u in U])

# Q10 Interoperability (shared_dataset unknown)
Q[10] = dict(name="Interoperability, Standardization, and Cross-Platform Integration", score_type="numeric", max=5, app=pred("shared_dataset"),
             label="Absent (minimum across releases)",
             evidence="No distribution_formats, conforms_to, conforms_to_schema or related_datasets in any release dataset. Only the June 2025 release description mentions 'corrections to ro-crate metadata'; RO-Crate conformance is asserted only at collection level.",
             note="Standards conformance is not attached to the release units.",
             rows=[row(R0, 0, "No format or standard declared.", absent=["distribution_formats", "conforms_to", "conforms_to_schema", "related_datasets"]),
                   row(R1, 3, "Description mentions RO-Crate metadata, a standard packaging format, without schema conformance or format list.",
                       cited=[{"path": "description", "quote": "corrections to ro-crate metadata"}], absent=["distribution_formats", "conforms_to", "conforms_to_schema"]),
                   row(R2, 0, "No format or standard declared.", absent=["distribution_formats", "conforms_to", "conforms_to_schema", "related_datasets"]),
                   row(R3, 0, "No format or standard declared.", absent=["distribution_formats", "conforms_to", "conforms_to_schema", "related_datasets"])])

# Q11 Tools (data_processing unknown)
Q[11] = dict(name="Tool and Software Transparency", score_type="numeric", max=5, app=pred("data_processing"),
             label="Absent",
             evidence="No preprocessing_strategies, cleaning_strategies, labeling_strategies or annotation tools in any release dataset; MuSIC and FAIRSCAPE are described only at collection level (and stated not to apply to the June 2026 files).",
             note="Processing documentation is not attached to any release.",
             rows=[row(u, 0, "No processing or software documentation in this release dataset.",
                       absent=["preprocessing_strategies", "cleaning_strategies", "labeling_strategies", "machine_annotation_tools", "imputation_protocols"]) for u in U])

# Q12 Collection (data_collection unknown)
Q[12] = dict(name="Collection Protocol Clarity", score_type="numeric", max=5, app=pred("data_collection"),
             label="Partial (mechanism names only)",
             evidence="Each release description names the measurement techniques (Perturb-seq, SEC-MS, IF images; AP-MS in June 2026) and cell systems, but there are no acquisition_methods, collection_mechanisms, data_collectors, collection_timeframes or raw_data_sources at resource level.",
             note="Technique names give the mechanism only; collectors (Lundberg Lab, Krogan lab) and protocol detail are at collection level.",
             rows=[row(R0, 3, "Description names perturb-seq, SEC-MS and IF image data types.", cited=[{"path": "description", "quote": "SEC-MS data in undifferentiated KOLF2.1J"}],
                       absent=["collection_mechanisms", "data_collectors", "collection_timeframes", "acquisition_methods"]),
                   row(R1, 3, "Description names perturb-seq, SEC-MS and IF images.", cited=[{"path": "description", "quote": "It includes perturb-seq data in undifferentiated KOLF2.1J"}],
                       absent=["collection_mechanisms", "data_collectors", "collection_timeframes", "acquisition_methods"]),
                   row(R2, 3, "Description names Perturb-seq, SEC-MS and IF images.", cited=[{"path": "description", "quote": "It includes Perturb-seq data for MDA-MB-468"}],
                       absent=["collection_mechanisms", "data_collectors", "collection_timeframes", "acquisition_methods"]),
                   row(R3, 3, "Description names Perturb-seq, SEC-MS, AP-MS and IF images.", cited=[{"path": "description", "quote": "AP-MS data for MDA-MB-468 breast cancer cells + treatment"}],
                       absent=["collection_mechanisms", "data_collectors", "collection_timeframes", "acquisition_methods"])])

# Q13 Versioning (shared_dataset unknown)
Q[13] = dict(name="Version History, Maintenance, and Sustainability", score_type="numeric", max=5, app=pred("shared_dataset"),
             label="Version + access + persistent ID",
             evidence="Each release has a version (1.4, 2.1, 2.1, 2.0), Beta status, issued date, DOI and Dataverse page. No maintainers, updates, errata or version_access at resource level; the quarterly update plan and preservation commitment are only at collection level.",
             note="Dataverse version numbers are per-DOI, so the June 2026 release (2.0) having a lower number than the October 2025 release (2.1) is not a contradiction but can mislead readers.",
             rows=[row(R0, 3, "version 1.4, status Beta, issued 2025-03-03, DOI and page; source_caveats notes the V1 citation mismatch.",
                       cited=["version", "status", "issued", "doi", {"path": "source_caveats", "quote": "Version 1.4"}], absent=["maintainers", "updates", "errata", "version_access"]),
                   row(R1, 3, "version 2.1, Beta, issued 2025-07-01, DOI and page; description records it as a revision.",
                       cited=["version", "status", "issued", "doi", {"path": "description", "quote": "a revision of the June 2025 Data Release"}], absent=["maintainers", "updates", "errata", "version_access"]),
                   row(R2, 3, "version 2.1, Beta, issued 2025-10-31, DOI and page.", cited=["version", "status", "issued", "doi"], absent=["maintainers", "updates", "errata", "version_access"]),
                   row(R3, 3, "version 2.0, Beta, issued 2026-06-17, DOI, page and citation with V2.", cited=["version", "status", "issued", "doi"], absent=["maintainers", "updates", "errata", "version_access"])])

# Q14 Publications
Q[14] = dict(name="Associated Publications", score_type="numeric", max=5, app=ALWAYS,
             label="One reference",
             evidence="March/June/October 2025 releases have a bare dataset DOI only. The June 2026 release adds a formal data citation, but that citation names the same DOI, so only one distinct reference exists; no external_resources at resource level (the preprint and Nature paper are collection-level).",
             note="Two distinct references plus a formal citation are needed for 5.",
             rows=[row(R0, 3, "Bare dataset DOI; no citation or external resource.", cited=["doi"], absent=["citation", "external_resources"]),
                   row(R1, 3, "Bare dataset DOI; no citation or external resource.", cited=["doi"], absent=["citation", "external_resources"]),
                   row(R2, 3, "Bare dataset DOI; no citation or external resource.", cited=["doi"], absent=["citation", "external_resources"]),
                   row(R3, 3, "Formal dataset citation with the same DOI; no second distinct reference.",
                       cited=["doi", {"path": "citation", "quote": "Cell Maps for Artificial Intelligence - June 2026 Data Release"}], absent=["external_resources"])])

# Q15 Human representation (human_subjects unknown)
Q[15] = dict(name="Human Subject Representation", score_type="numeric", max=5, app=pred("human_subjects"),
             label="General human-derived data without demographics",
             evidence="Each release description names human-derived cell systems (MDA-MB-468 breast cancer cells +/- treatment, KOLF2.1J iPSCs and derived NPCs, neurons, cardiomyocytes) but gives no donor demographics or inclusion criteria; RRIDs and donor descriptions are only in collection-level subpopulations.",
             note="Cell-line groups are described by type and treatment, not by population characteristics.",
             rows=[row(u, 3, "Human cell-line sample groups named in the description; no subpopulations or demographic detail.",
                       cited=[{"path": "description", "quote": "KOLF2.1J"}], absent=["subpopulations", "instances", "at_risk_populations"]) for u in U])

# Q16 Findability
Q[16] = dict(name="Findability (Persistent Links)", score_type="pass_fail", max=1, app=ALWAYS,
             label="Pass",
             evidence="Each release has a dataverse.lib.virginia.edu page URL keyed by persistentId DOI.",
             note="URLs are well-formed; not fetched.",
             rows=[row(u, 1, "Landing page URL and DOI present.", cited=["page", "doi", "id"], absent=["download_url"]) for u in U])

# Q17 Access mechanism (shared_dataset unknown)
Q[17] = dict(name="Accessibility (Access Mechanism)", score_type="numeric", max=5, app=pred("shared_dataset"),
             label="Partial",
             evidence="Each release provides a Dataverse landing page and a CC BY-NC-SA 4.0 license, but no download_url, distribution formats, or statement of the access tier (open download, registration, or agreement).",
             note="The platform is identifiable, but the authorization steps are not stated at resource level.",
             rows=[row(u, 3, "Landing page and license; no download URL, formats or access-tier statement.",
                       cited=["page", "license"], absent=["download_url", "distribution_formats", "license_and_use_terms"]) for u in U])

# Q18 Reuse guidance
Q[18] = dict(name="Reusability, Use Guidance, and Social Impact", score_type="numeric", max=5, app=ALWAYS,
             label="License with basic terms",
             evidence="The CC BY-NC-SA 4.0 license name conveys attribution, non-commercial and share-alike conditions; no intended_uses, prohibited_uses, discouraged_uses or future_use_impacts at resource level.",
             note="Use guidance and impact analysis are absent from the release units.",
             rows=[row(u, 3, "License present; no explicit use guidance or impact analysis.",
                       cited=[{"path": "license", "quote": "CC BY-NC-SA 4.0"}],
                       absent=["intended_uses", "prohibited_uses", "discouraged_uses", "future_use_impacts"]) for u in U])

# Q19 Provenance
Q[19] = dict(name="Data Integrity, Provenance Graph, and Quality", score_type="numeric", max=5, app=ALWAYS,
             label="Version history, no provenance graph",
             evidence="Releases carry version numbers and issue dates (and the June 2025 release records what its revision changed), but no was_derived_from, parent_datasets, raw_data_sources, errata or missing_data_documentation at resource level. Provenance-graph HTML files are listed only in collection-level file_collections.",
             note="Version identifiers provide basic history; no derivation lineage is linked to the units.",
             rows=[row(R0, 3, "Version 1.4 and issue date; no lineage.", cited=["version", "issued"], absent=["was_derived_from", "parent_datasets", "errata", "raw_data_sources", "missing_data_documentation"]),
                   row(R1, 3, "Version 2.1 with change description; no lineage.", cited=["version", {"path": "description", "quote": "adds RGB immunofluorescent images"}], absent=["was_derived_from", "parent_datasets", "errata", "raw_data_sources"]),
                   row(R2, 3, "Version 2.1 and an embargo note; no lineage.", cited=["version", {"path": "notes", "quote": "Embargoed"}], absent=["was_derived_from", "parent_datasets", "errata", "raw_data_sources", "missing_data_documentation"]),
                   row(R3, 3, "Version 2.0 and issue date; no lineage.", cited=["version", "issued"], absent=["was_derived_from", "parent_datasets", "errata", "raw_data_sources", "missing_data_documentation"])])

# Q20 Bias
Q[20] = dict(name="Bias Documentation and Responsible AI Alignment", score_type="numeric", max=5, app=ALWAYS,
             label="Absent",
             evidence="No known_biases or future_use_impacts in any release dataset; the two collection-level bias statements (cell-line derivation, limited variant representation) are not inherited.",
             note="Bias documentation exists only at collection level and uses no taxonomy.",
             rows=[row(u, 0, "No bias documentation in this release dataset.", absent=["known_biases", "future_use_impacts"]) for u in U])

ISSUES = [
    dict(item_ids=["Q1", "Q2", "Q3"], score_effect="lowered", category="variables_metadata", type="completeness", severity="high",
         description="Release datasets under resources carry only identification fields and a description; keywords, creators, purposes, instances and variables are documented only at the undeclared collection level, which member datasets do not inherit.",
         fields_involved=["keywords", "creators", "purposes", "instances", "variables"],
         recommendation="Declare the record as a Dataset (conforms_to_class) if the top-level series is the unit of interest, or copy per-release descriptive metadata into each resource."),
    dict(item_ids=["Q4", "Q5", "Q10", "Q17"], score_effect="lowered", category="format_access", type="completeness", severity="high",
         description="File enumerations, formats, sizes and RO-Crate conformance are recorded in top-level file_collections and distribution_formats keyed by id fragments, not nested in the releases they describe.",
         fields_involved=["file_collections", "distribution_formats", "total_size_bytes", "conforms_to", "download_url"],
         recommendation="Nest each release's file_collections, distribution_formats, total bytes, conforms_to and access steps inside the corresponding resource."),
    dict(item_ids=["Q7"], score_effect="lowered", category="attribution", type="completeness", severity="medium",
         description="No funders or creators are attached to any release; only the June 2026 citation string lists author names, without affiliations or grants.",
         fields_involved=["funders", "creators", "citation"],
         recommendation="Attach creators with affiliations and the NIH award (1OT2OD032742-01, as listed by Dataverse) to each release."),
    dict(item_ids=["Q8", "Q15"], score_effect="lowered", category="privacy_regulatory", type="completeness", severity="medium",
         description="Ethics, de-identification and population descriptors (Human Subjects: No, de-identified cell lines, donor descriptions of MDA-MB-468 and KOLF2.1J) are recorded only at collection level; releases name cell lines without donor characterization.",
         fields_involved=["human_subject_research", "is_deidentified", "ethical_reviews", "subpopulations"],
         recommendation="Record human_subject_research, is_deidentified, ethical review and subpopulations on each release, or supply a caller context declaring human_subjects."),
    dict(item_ids=["Q9", "Q18"], score_effect="lowered", category="license_use_terms", type="completeness", severity="medium",
         description="Each release has only a license string; IP holders, commercial-license negotiation, governance contact and intended/prohibited uses are collection-level only.",
         fields_involved=["license", "license_and_use_terms", "ip_restrictions", "intended_uses", "prohibited_uses"],
         recommendation="Add license_and_use_terms, ip_restrictions and use guidance to each release."),
    dict(item_ids=["Q11", "Q12", "Q19"], score_effect="lowered", category="processing_provenance", type="completeness", severity="medium",
         description="Collection mechanisms, data collectors, processing pipelines and lineage are absent from the releases; descriptions only name data modalities, and provenance-graph files are not linked to their release.",
         fields_involved=["collection_mechanisms", "data_collectors", "preprocessing_strategies", "was_derived_from", "raw_data_sources"],
         recommendation="Attach collection, processing and derivation metadata (including the provenance-graph files) to each release."),
    dict(item_ids=["Q13"], score_effect="lowered", category="temporal_version", type="completeness", severity="low",
         description="Releases have versions and DOIs but no maintainers, update plan, errata or preservation commitment at resource level.",
         fields_involved=["maintainers", "updates", "errata", "version_access"],
         recommendation="Add maintainers and per-release errata/update notes."),
    dict(item_ids=["Q14"], score_effect="lowered", category="persistent_identifier", type="completeness", severity="low",
         description="Three releases have only a bare DOI; the June 2026 release adds a formal citation for the same DOI but no second distinct reference.",
         fields_involved=["doi", "citation", "external_resources"],
         recommendation="Add formal citations to every release and link the CM4AI preprint as an external resource."),
    dict(item_ids=["Q20"], score_effect="lowered", category="bias_quality", type="completeness", severity="medium",
         description="No known_biases at resource level; collection-level bias statements are brief and use no taxonomy.",
         fields_involved=["known_biases", "future_use_impacts"],
         recommendation="Document per-release biases (cell-line selection, protein-set overlap, embargoed data) with a standard taxonomy."),
    dict(item_ids=[], score_effect="noted_only", category="temporal_version", type="consistency", severity="low",
         description="Version numbers are not monotonic across the series (October 2025 release 2.1, June 2026 release 2.0) and the March 2025 page shows Version 1.4 while its citation ends V1; these are per-DOI Dataverse versions, as the record's own caveat partly explains.",
         fields_involved=["version", "source_caveats"],
         recommendation="State that version numbers are per-Dataverse-record and give a series-level release ordering."),
    dict(item_ids=[], score_effect="noted_only", category="source_conflict", type="consistency", severity="low",
         description="The June 2026 release's caveat records a source conflict: the release page says 'Released on: June 17, 2025' while Dataverse gives 2026-06-17; the record uses the Dataverse date and discloses the conflict.",
         fields_involved=["issued", "source_caveats"],
         recommendation="None beyond retaining the disclosed caveat."),
    dict(item_ids=[], score_effect="noted_only", category="attribution", type="content_accuracy", severity="low",
         description="The June 2026 citation contains the author name 'Ballllosero Navarro F', which looks like a transcription error (possibly present in the source).",
         fields_involved=["citation"],
         recommendation="Verify the author name against the Dataverse record."),
    dict(item_ids=[], score_effect="noted_only", category="scope_drift", type="semantic_understanding", severity="medium",
         description="The record's top-level description says it 'describes the CM4AI dataset as an ongoing series of data releases' but declares no class; with nonempty resources it is evaluated as a collection, so its extensive series-level documentation does not count toward any release.",
         fields_involved=["resources", "conforms_to_class"],
         recommendation="Declare conforms_to_class Dataset if the series is the dataset being documented."),
]

categories = [("Structural Completeness", range(1, 6)), ("Metadata Quality & Content", range(6, 11)),
              ("Technical Documentation", range(11, 16)), ("FAIRness & Accessibility", range(16, 21))]

rubric_desc = {}
# Descriptions truncated to 120 chars, as in the definition's example.
for line_q, text in {
    1: "Proportion of mandatory schema fields populated including core identification, hierarchical structure, governance, and composition metadata.",
    2: "Checks whether narrative fields (e.g., description, purposes) have meaningful content length.",
    3: "Number of distinct keywords describing the dataset.",
    4: "Number and variety of documented distribution formats and file types.",
    5: "Presence of file size or dimensional metadata (bytes, instance counts, data splits).",
    6: "Presence of unique identifiers such as DOI, RRID, or persistent URLs, AND hosting platform identification.",
    7: "Checks presence of funding sources, grants, institutional sponsors, and creator affiliations.",
    8: "Ethical oversight and privacy safeguards appropriate to the dataset.",
    9: "Documentation of access and license terms, IP restrictions, regulatory obligations, confidentiality and governance contacts.",
    10: "Documentation of standard formats, schema or ontology conformance, typed dataset relationships and integration procedures.",
    11: "Documentation of preprocessing, cleaning, labeling, annotation and imputation, including software names and versions.",
    12: "Description completeness of data collection mechanisms, acquisition methods, collectors, timeframes and raw sources.",
    13: "Documentation of version identifiers, change history, maintenance and preservation plans, contacts and durable access.",
    14: "Citation, identifiers and documentation links that let a reader identify the dataset and related publications.",
    15: "Documentation of human participant or population representation, recruitment, sampling and relevant subgroups.",
    16: "Dataset includes persistent URLs, DOI, and identifier for access and documentation.",
    17: "Describes how users can obtain the dataset (download URL, distribution formats, access policy).",
    18: "License with explicit use guidance and social impact analysis.",
    19: "Version access, errata, update plans, source derivation, parent linkages, missing data and provenance graph.",
    20: "Documentation of known biases, limitations and potential effects on intended or foreseeable uses.",
}.items():
    rubric_desc[line_q] = text[:120]

reasons = {}
cats_out = []
total = 0
for cname, ids in categories:
    qs = []
    csum = cmax = 0
    for i in ids:
        q = Q[i]
        status, app_ev = q["app"]
        score = min(r["score"] for r in q["rows"])
        csum += score
        cmax += q["max"]
        qs.append({"id": i, "name": q["name"], "description": rubric_desc[i], "score_type": q["score_type"],
                   "score": score, "max_score": q["max"], "score_label": q["label"], "evidence": q["evidence"],
                   "quality_note": q["note"], "applicable": True, "applicability_status": status,
                   "applicability_evidence": app_ev, "unit_scores": q["rows"]})
    total += csum
    cats_out.append({"name": cname, "questions": qs, "category_score": csum, "category_max": cmax})

result = {
    "rubric": "rubric20-semantic",
    "version": "3.0",
    "d4d_file": str(INPUT),
    "project": "CM4AI",
    "method": "claudecode_agent",
    "run_label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1",
    "evaluation_timestamp": "2026-11-22T08:48:03Z",
    "model": {"name": "claude-opus-5-5", "evaluator_model": "claude-opus-5-5", "temperature": None,
              "temperature_note": "Not exposed by this runtime; no deterministic-score guarantee",
              "evaluation_type": "semantic_llm_judge"},
    "overall_score": {"total_points": total, "max_points": 88, "excluded_max_points": 0,
                      "adjusted_max_points": 88, "normalized_percentage": round(100 * total / 88, 2),
                      "fixed_percentage": round(100 * total / 88, 2), "questions_not_applicable": 0,
                      "excluded_item_ids": []},
    "categories": cats_out,
    "semantic_analysis": {
        "issues_detected": ISSUES,
        "semantic_insights": [
            "Scope: the input has no class wrapper or conforms_to_class and has four resources, so it is evaluated as a collection of four release datasets (#/resources/0-3); each item score is the minimum across releases and collection metadata is not inherited.",
            "The undeclared top-level wrapper is richly documented (29 keywords, 48 affiliated creators, NIH funders, ethics reviewers, collection mechanisms, MuSIC pipeline, file enumerations with MD5 checksums), but none of it is attached to the scored release units; most deductions follow from that structure rather than from missing knowledge.",
            "Each release has a well-formed 10.18130 DOI (University of Virginia Dataverse), a persistentId landing page, a version, Beta status and an issue date.",
            "The record discloses source conflicts (release date, version label) in source_caveats rather than silently choosing a value.",
        ],
        "consistency_checks": {"passed": 4, "failed": 0, "warnings": 3},
        "correctness_validations": {
            "doi_format": "valid (10.18130 prefix, University of Virginia Dataverse) for all four release DOIs",
            "grant_number_format": "not_present at resource level (collection-level 1OT2OD032742-01, 3OT2OD032742-01S2 and 5U54HG012513-02 follow NIH patterns but are not inherited)",
            "rrid_format": "not_present at resource level",
            "url_validity": "all_valid (well-formed dataverse.lib.virginia.edu URLs; not fetched)",
        },
    },
    "applicability_context": {},
    "evaluation_scope": {"policy": "minimum_per_item_across_all_resource_datasets_v1",
                         "units": [{"path": p, "id": u.get("id")} for p, u in units],
                         "collection_metadata_inherited": False},
    "metadata": {
        "instrument_sha256": sha(DEFN),
        "evidence_authority_sha256": sha(AUTH),
        "rubric_sha256": sha(RUBRIC),
        "input_sha256": input_sha,
        "context_sha256": context_digest({}),
        "caller_context_file": None,
        "evaluator_model": "claude-opus-5-5",
        "dataset_identity": {"project": "CM4AI"},
        "method_identity": {"method": "claudecode_agent", "label": "2026-11-22b_claude-opus-5-5-claudecode-generic-v9_rep1"},
    },
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(f"wrote {OUT} total={total}")
