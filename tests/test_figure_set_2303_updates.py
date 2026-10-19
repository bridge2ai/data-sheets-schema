"""Tests for the #2303 figure-set updates (#2385, #2455-#2459, #2819, #2983, #3024, #3360, #3411, #3878, #3936, #4385, #4443)."""
from __future__ import annotations

import inspect

from scripts.figures import _style as st
from scripts.figures import (
    fig02_content_coverage as f02,
    fig04_scores as f04,
    fig06_evidence_coverage as f06,
    fig08_support_fitness as f08,
    fig09_crate_vs_generation as f09,
    fig11_issue_taxonomy as f11,
    fig12_replication_stability as f12,
    fig18_vocabulary_alignment as f18,
    fig19_source_dependence as f19,
)


def test_fig02_caveat_mentions_slot_word_boundary_and_identifier_context():
    """#2459: single-token slot names require explicit slot-identifier context in source_caveats."""
    prose = (
        "No formal study protocol document or clinicaltrials.gov registration was "
        "included in the source page; see the title and role of the tasks."
    )
    for slot in ("page", "role", "tasks", "title", "type", "start", "end"):
        assert not f02.caveat_mentions_slot(slot, prose), slot

    assert f02.caveat_mentions_slot("page", "The `page` slot was omitted because no pagination exists.")
    assert f02.caveat_mentions_slot("role", "Slot role had no source evidence.")
    assert f02.caveat_mentions_slot("tasks", 'Field "tasks" could not be populated from the README.')
    assert f02.caveat_mentions_slot("ethics_review", "No ethics_review record was found in the manifest.")


def test_fig04_procedure_table_distinguishes_arm_from_header_string():
    """#2457: procedure_table row label distinguishes API arm from the raw 'Agent runtime' header string."""
    manifest, _, rows = f04.load()
    cols = f04.procedure_table(manifest, rows)
    for cohort in ("v7", "v8"):
        assert cols[cohort]["generation runtime"].startswith("API arm (header: ")
        assert "Claude API (direct)" in cols[cohort]["generation runtime"]


def test_fig06_and_fig19_use_run_source_manifest_and_origin_split():
    """#2455, #2819, #3411, #4443: fig06 and fig19 use run_source_manifest at each run's commit and split origin."""
    f06_rows, f06_support, f06_attr = f06.analyse()
    assert len(f06_rows) == 24
    assert len(f06_support) == 24
    assert len(f06_attr) > 0
    for r in f06_rows:
        assert "contemporaneous_snippets" in r and "post_draft_snippets" in r
        if r["contemporaneous_snippets"] != "":
            assert r["contemporaneous_snippets"] + r["post_draft_snippets"] == r["receipt_snippets_total"]

    runs, per_doc = f19.analyse()
    assert len(runs) == 24
    assert all("contemporaneous_snippets" in r and "post_draft_snippets" in r for r in runs)
    assert all("tier" in d and "present_in_head_manifest" in d for d in per_doc)


def test_fig08_reports_unique_judgments_and_verdict_rows():
    """#2458: fig08 module analysis distinguishes verdict rows across replicates from unique judgments."""
    src = inspect.getsource(f08)
    assert "supported_distinct_judgments" in src
    assert "unsupported_distinct_judgments" in src
    assert "distinct judgments" in src
    assert 'r["support_source"] == "judged on this replicate"' in src


def test_fig09_includes_subsumed_status_and_uri_curie_overlap():
    """#2456, #2983, #4385: fig09 includes subsumed in STATUSES, normalizes doi/id URI<->CURIE, and avoids blue/red collision."""
    assert "subsumed" in f09.STATUSES
    src = inspect.getsource(f09)
    assert '("crate_only", "crate-mapped only", st.SERIES[7], None)' in src
    assert '("generated_only", "generated only (API arm v8 rep 1)", st.SERIES[0], None)' in src

    forms = f09.dataset_identifier_forms({"id": "https://doi.org/10.13026/abc-123", "doi": "https://doi.org/10.13026/abc-123"})
    assert "doi:10.13026/abc-123" in forms
    assert "https://doi.org/10.13026/abc-123" in forms


def test_fig11_rubric20_semantic_color_avoids_green_collision():
    """#2385: rubric20-semantic in Panel A/B does not reuse the green hue used for 'passed' in Panel C."""
    assert f11.RUBRIC_COLOR["rubric20-semantic"] == st.SERIES[4]
    assert f11.RUBRIC_COLOR["rubric20-semantic"] != st.SERIES[2]
    assert f11.RUBRIC_COLOR["rubric20-semantic"] != st.STATUS["good"]


def test_fig18_keys_by_subject_id_and_handles_regenerated_structural_table():
    """#2983, #3024, #3360: fig18 keys Panel A by subject_id, distinguishes novel_d4d heuristic, and handles #2983 Panel B."""
    comp_rows, _, slot_rows, cols, _, not_in_schema, _ = f18.panel_a()
    assert len(comp_rows) == 301
    assert len(slot_rows) == 301
    assert not not_in_schema
    assert all(s["subject_id"].startswith("d4d:") for s in slot_rows if s["in_comprehensive_table"])

    novel_unmapped = ("no target recorded", "skos:exactMatch", "novel_d4d")
    assert novel_unmapped in cols
    assert f18.col_label(novel_unmapped) == "novel_d4d (heuristic, no target)"
    assert f18.marker_style(novel_unmapped)["marker"] == "D"

    s_rows, classified, summary, groups = f18.panel_b()
    assert len(s_rows) == 165
    flagged_comp = [c for c in classified if c["type_compatible"] == "False" and c["composition_path"].strip()]
    assert len(flagged_comp) == 16
    assert {c["d4d_subject_range"] for c in flagged_comp} == {"DataAnomaly", "string", "uriorcurie", "Software"}
    assert all(c["subject_multivalued"] == "True" for c in flagged_comp)
    assert all(c["written_values_are"] == "from the schema slot" for c in flagged_comp)


def test_set_2303_readme_lists_all_22_figures_and_caveat_sections():
    """#3878, #3936: README lists all 22 figures and includes release-level and top-level vs nested caveat sections."""
    readme = (st.OUT / "README.md").read_text()
    for fig_stem in (
        "fig01_pipeline",
        "fig02_content_coverage",
        "fig03_full_core",
        "fig04_scores",
        "fig05_item_heatmap",
        "fig06_evidence_coverage",
        "fig07_audit_findings",
        "fig07_typed_audits",
        "fig08_support_fitness",
        "fig09_crate_vs_generation",
        "fig09_mapping_revision",
        "fig10_cost_latency",
        "fig11_issue_taxonomy",
        "fig12_replication_stability",
        "fig13_inter_rater",
        "fig14_prompt_v7_v8",
        "fig15_arm_comparison",
        "fig16_scoring_trajectory",
        "fig17_module_balance",
        "fig18_vocabulary_alignment",
        "fig19_source_dependence",
        "fig20_attainability",
    ):
        assert f"| {fig_stem} |" in readme, fig_stem
    assert "## Release-level corpus caveats (#3878)" in readme
    assert "## Top-level vs nested replication scope (#3936)" in readme
    assert "Below the top level (#3337)" in (f12.__doc__ or "")


def test_unreachable_run_commit_resolves_only_to_the_pinned_manifest_bytes():
    """#5076: a run commit squash-merged away (absent from a CI clone) resolves to the
    version in HEAD's history with the provenance sha256, and to nothing otherwise."""
    import hashlib
    import subprocess
    rel = "data/preprocessed/chunks/CHORUS_chunks.yaml"
    old = subprocess.check_output(["git", "log", "--format=%H", "-1", "HEAD~0", "--", rel],
                                  cwd=st.ROOT, text=True).strip()
    pinned = hashlib.sha256(subprocess.check_output(["git", "show", f"{old}:{rel}"], cwd=st.ROOT)).hexdigest()
    missing = "0" * 40
    raw, ref = f06.chunk_manifest_bytes_at(missing, "CHORUS", pinned)
    assert hashlib.sha256(raw).hexdigest() == pinned and "not reachable" in ref
    assert f06.chunk_manifest_bytes_at(missing, "CHORUS", "f" * 64)[0] is None
    assert f06.chunk_manifest_bytes_at(missing, "CHORUS")[0] is None
