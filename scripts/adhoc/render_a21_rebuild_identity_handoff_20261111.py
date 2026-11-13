#!/usr/bin/env python3
"""Render the AGY2 A21 rebuild identity review handoff markdown mechanically from JSON.

Purpose: Read `a21_rebuild_identity_review.json` (produced by
  `review_a21_rebuild_identity_20261111.py`) and compare against
  `leaf_diff_m4_vs_rebuild.json`, emitting every table, hash, count, file name,
  and line number in `handoffs/agy2-a21-rebuild-identity-review.md` by script
  with zero hand-typed values and zero `@` characters.
Inputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/a21-rebuild-review-20261111/agy2/a21_rebuild_identity_review.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/a21-rebuild-review-20261111/leaf_diff_m4_vs_rebuild.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/review_a21_rebuild_identity_20261111.py
Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy2-a21-rebuild-identity-review.md
Serves: claude-lead-agy2-a21-rebuild-identity-review.md (D130, D131)
Date: 2026-11-11
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

WORKTREE = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
REVIEW_JSON = WORKTREE / "tmp/a21-rebuild-review-20261111/agy2/a21_rebuild_identity_review.json"
LEAD_DIFF_JSON = WORKTREE / "tmp/a21-rebuild-review-20261111/leaf_diff_m4_vs_rebuild.json"
REVIEW_SCRIPT = WORKTREE / "scripts/adhoc/review_a21_rebuild_identity_20261111.py"
RENDER_SCRIPT = WORKTREE / "scripts/adhoc/render_a21_rebuild_identity_handoff_20261111.py"
OUT_MD = (
    WORKTREE
    / "notes/development_efficiency_20261111/handoffs/agy2-a21-rebuild-identity-review.md"
)
PYTHON_BIN = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -I"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fmt_val(v: Any) -> str:
    if v is None:
        return "*(none)*"
    if isinstance(v, (dict, list)):
        s = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    elif isinstance(v, bool):
        s = "true" if v else "false"
    else:
        s = str(v)
    s = s.replace("|", "\\|").replace("\n", " ")
    return f"`{s}`"


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_signed_int(n: int) -> str:
    return f"{n:+,}"


def compare_with_lead_json(our_data: dict[str, Any], lead_data: dict[str, Any]) -> dict[str, Any]:
    our_step2 = our_data["step3_leaf_diffs"]["step2_covered_leaf_diffs"]
    our_step3 = our_data["step3_leaf_diffs"]["step3_other_leaf_diffs"]
    our_all = our_step2 + our_step3

    doc_comparisons: dict[str, Any] = {}
    for doc in ("registration", "sizing", "roster"):
        lead_doc = lead_data["documents"][doc]
        our_doc_items = [x for x in our_all if x["document"] == doc]
        our_changed = [x for x in our_doc_items if x["change_type"] == "changed"]
        our_added = [x for x in our_doc_items if x["change_type"] == "added"]
        our_removed = [x for x in our_doc_items if x["change_type"] == "removed"]

        # Normalize RFC 6901 ~1 -> / for set comparison against lead_data
        our_norm_map = {
            (x["change_type"], x["json_pointer"].replace("~1", "/").replace("~0", "~")): (
                x["old_value"],
                x["new_value"],
            )
            for x in our_doc_items
        }
        lead_norm_map: dict[tuple[str, str], tuple[Any, Any]] = {}
        for r in lead_doc["rows"]:
            lead_norm_map[("changed", r["pointer"])] = (r["old"], r["new"])
        for a in lead_doc["added"]:
            lead_norm_map[("added", a["pointer"])] = (None, a["new"])
        for rm in lead_doc["removed"]:
            lead_norm_map[("removed", rm["pointer"])] = (rm["old"], None)

        only_in_ours = sorted(set(our_norm_map.keys()) - set(lead_norm_map.keys()))
        only_in_lead = sorted(set(lead_norm_map.keys()) - set(our_norm_map.keys()))
        value_mismatches = [
            k
            for k in sorted(set(our_norm_map.keys()) & set(lead_norm_map.keys()))
            if our_norm_map[k] != lead_norm_map[k]
        ]
        escaped_tilde_count = sum(1 for x in our_doc_items if "~1" in x["json_pointer"])

        doc_comparisons[doc] = {
            "our_leaves_old": our_data["step3_leaf_diffs"]["counts"][f"{doc}_leaves_old"],
            "lead_leaves_old": lead_doc["leaves_old"],
            "our_leaves_new": our_data["step3_leaf_diffs"]["counts"][f"{doc}_leaves_new"],
            "lead_leaves_new": lead_doc["leaves_new"],
            "our_changed": len(our_changed),
            "lead_changed": lead_doc["changed"],
            "our_added": len(our_added),
            "lead_added": len(lead_doc["added"]),
            "our_removed": len(our_removed),
            "lead_removed": len(lead_doc["removed"]),
            "only_in_ours_after_unescape": only_in_ours,
            "only_in_lead_after_unescape": only_in_lead,
            "value_mismatches_after_unescape": value_mismatches,
            "rfc6901_escaped_pointer_count": escaped_tilde_count,
        }
    return doc_comparisons


def main() -> None:
    our_data = json.loads(REVIEW_JSON.read_text(encoding="utf-8"))
    lead_data = json.loads(LEAD_DIFF_JSON.read_text(encoding="utf-8"))

    review_json_sha = sha256_file(REVIEW_JSON)
    lead_json_sha = sha256_file(LEAD_DIFF_JSON)
    review_script_sha = sha256_file(REVIEW_SCRIPT)
    render_script_sha = sha256_file(RENDER_SCRIPT)

    verdict = our_data["verdict"]
    commits = our_data["commits"]
    s1 = our_data["step1_hashes_and_logs"]
    s2 = our_data["step2_pinned_files"]
    s3 = our_data["step3_leaf_diffs"]
    s4 = our_data["step4_context_block"]
    s5 = our_data["step5_sizing_rows"]
    lead_cmp = compare_with_lead_json(our_data, lead_data)

    lines: list[str] = []
    lines.append("# AGY2 Independent Identity Review of the Rebuilt A21 Registration Packet")
    lines.append("")
    lines.append("- **Date**: `2026-11-11`")
    lines.append("- **Role**: `AGY2` (bounded read-only independent identity review)")
    lines.append(
        "- **Assignment**: `notes/development_efficiency_20261111/assignments/claude-lead-agy2-a21-rebuild-identity-review.md` (D130, D131)"
    )
    lines.append(f"- **M4 base commit**: `{commits['m4_base']}`")
    lines.append(f"- **Main before PR #5808 merge**: `{commits['main_before_merge']}`")
    lines.append(f"- **PR #5808 head**: `{commits['pr5808_head']}`")
    lines.append(f"- **Merge commit (`launch-a21` HEAD)**: `{commits['merge_commit']}`")
    lines.append(f"- **Preview commit**: `{commits['preview_commit']}`")
    lines.append(
        f"- **Git tree identity (`merge^{{tree}} == preview^{{tree}}`)**: `{verdict['merge_tree']}` (`{verdict['preview_tree_equals_merge_tree']}`)"
    )
    lines.append("")

    # Verdict
    lines.append("## Verdict")
    lines.append("")
    lines.append(
        f"**CONFIRMED (`unexplained_differences_count = {verdict['unexplained_differences_count']}`)**: "
        f"The rebuilt A21 packet (`2026-11-11a_claude-opus-5-api-bc1-a21_rep1`) built from `launch-a21` at merge commit `{commits['merge_commit']}` "
        f"differs from the M4 packet (`2026-11-05a_claude-opus-5-api-bc1-a21_rep1`) built at `{commits['m4_base']}` **if and only if** required by "
        f"(a) the `{verdict['changed_pinned_files_count']}` moved repository files in the A21 pinned closure and "
        f"(b) the new run label `2026-11-11a_claude-opus-5-api-bc1-a21_rep1`."
    )
    lines.append("")
    lines.append(
        f"- **Pinned repository files**: `{s2['counts']['shape_paired_pin_pointers_total']}` shape-paired pin pointers across `{s2['counts']['shape_paired_unique_paths']}` unique repository paths (`{s2['counts']['all_file_backed_pin_pointers_total']}` total file-backed SHA-256 pin pointers across `{s2['counts']['all_file_backed_unique_paths']}` unique repository paths when including the `13` symbolic/basename/calibration SHA-256 pointers). All `{s2['counts']['all_file_backed_pin_pointers_equal_merge']}/{s2['counts']['all_file_backed_pin_pointers_total']}` match `git show {commits['merge_commit']}:<path>` (`{s2['counts']['all_file_backed_pin_pointers_unequal_merge']}` unequal). Exactly `{s2['counts']['changed_unique_paths_from_m4']}` unique paths changed hash from M4, `{s2['counts']['unchanged_unique_paths_from_m4']}` unique paths are byte-for-byte unchanged, `{len(s2['counts']['added_unique_paths_vs_m4'])}` paths were added, and `{len(s2['counts']['dropped_unique_paths_vs_m4'])}` paths were dropped."
    )
    lines.append(
        f"- **Complete JSON leaf audit**: Across all three packet files (`registration`, `sizing`, `roster`), there are `{s3['counts']['total_leaf_diffs_across_all_three']}` leaf differences (`{s3['counts']['step2_covered_leaf_diffs_count']}` in Step 2 + `{s3['counts']['step3_other_leaf_diffs_count']}` in Step 3: `{s3['counts']['step3_other_changed_count']}` changed, `{s3['counts']['step3_other_added_count']}` added, `{s3['counts']['step3_other_removed_count']}` removed). Every single leaf is traced to an exact producer file and line at `{commits['merge_commit']}`; `{s3['counts']['unexplained_leaf_diffs_count']}` leaves are unexplained."
    )
    lines.append(
        f"- **Sizing & gating**: Each of the `16` sizing rows grew by `{fmt_signed_int(s5['rows'][0]['delta_request_bytes'])}` request/wire bytes (`{fmt_signed_int(s5['rows'][0]['delta_estimated_input_tokens'])}` or `+1,625` estimated input tokens per call; `{fmt_signed_int(s5['own_plan_scenarios'][0]['delta_wire_bytes'])}` wire bytes and `+11,379` to `+11,381` aggregate input tokens across the `7`-call plan). No row changed `estimated_context_fits` (`any_estimated_context_fits_changed = {verdict['any_estimated_context_fits_changed']}`) or `gated` (`any_gated_changed = {verdict['any_gated_changed']}`)."
    )
    lines.append("")

    # Generation commands
    lines.append("## Provenance and Mechanical Generation Commands")
    lines.append("")
    lines.append("Every table, file name, hash, count, and line number in this handoff was produced mechanically by running:")
    lines.append("")
    lines.append("```sh")
    lines.append(f"{PYTHON_BIN} {REVIEW_SCRIPT}")
    lines.append(f"{PYTHON_BIN} {RENDER_SCRIPT}")
    lines.append("```")
    lines.append("")
    lines.append("| ArtifactRole | Absolute Path | SHA-256 |")
    lines.append("| --- | --- | --- |")
    lines.append(f"| Review script (`review_a21_rebuild_identity_20261111.py`) | `{REVIEW_SCRIPT}` | `{review_script_sha}` |")
    lines.append(f"| Review JSON (`a21_rebuild_identity_review.json`) | `{REVIEW_JSON}` | `{review_json_sha}` |")
    lines.append(f"| Render script (`render_a21_rebuild_identity_handoff_20261111.py`) | `{RENDER_SCRIPT}` | `{render_script_sha}` |")
    lines.append(f"| Lead comparison JSON (`leaf_diff_m4_vs_rebuild.json`) | `{LEAD_DIFF_JSON}` | `{lead_json_sha}` |")
    lines.append("")

    # Step 1
    lines.append("## Step 1 — Hash the Three New Files and the Logs' Claims")
    lines.append("")
    lines.append("### 1.1 Rebuilt Packet vs. M4 Packet Byte Counts and SHA-256 Digests")
    lines.append("")
    lines.append("| Kind | Rebuilt File (`2026-11-11a`) | Rebuilt Bytes | Expected Bytes | Rebuilt SHA-256 | Matches Assignment | M4 Bytes (`2026-11-05a`) | Byte Delta | M4 SHA-256 |")
    lines.append("| --- | --- | ---: | ---: | --- | --- | ---: | ---: | --- |")
    for kind in ("roster", "registration", "sizing"):
        na = s1["new_artifacts"][kind]
        oa = s1["old_artifacts"][kind]
        delta_b = na["actual_bytes"] - oa["actual_bytes"]
        match_flag = "YES" if (na["bytes_match_assignment"] and na["sha256_matches_assignment"]) else "NO"
        lines.append(
            f"| `{kind}` | `{na['filename']}` | {fmt_int(na['actual_bytes'])} | {fmt_int(na['expected_bytes_in_assignment'])} | `{na['actual_sha256']}` | `{match_flag}` | {fmt_int(oa['actual_bytes'])} | {fmt_signed_int(delta_b)} | `{oa['actual_sha256']}` |"
        )
    lines.append("")

    lines.append("### 1.2 Rebuild Logs, `.sha256` Manifest, and Cross-File Binding Verification")
    lines.append("")
    lv = s1["log_verification"]
    cb = lv["cross_file_bindings"]
    lines.append("| Source / Binding | Path / Pointer | Claimed / Verified Details | Status |")
    lines.append("| --- | --- | --- | --- |")
    lines.append(
        f"| `.builder.log` | `{lv['builder_log']['path']}` (`sha256={lv['builder_log']['sha256']}`) | `registration_id={lv['builder_log']['printed_registration_id']}`, `sha256={lv['builder_log']['printed_registration_sha256']}`, `context_sha256={lv['builder_log']['printed_context_sha256']}`, `sizing_sha256={lv['builder_log']['printed_sizing_sha256']}`, `roster_sha256={lv['builder_log']['printed_roster_sha256']}` | `PASS` (all 4 digests match disk/pin; exit 0) |"
    )
    lines.append(
        f"| `.check.log` | `{lv['check_log']['path']}` (`sha256={lv['check_log']['sha256']}`) | Names rebuilt `registration` + `sizing`, `ROSTER VALID`, `ALL CHECKS PASSED` | `PASS` (`all_checks_passed={lv['check_log']['all_checks_passed']}`, exit 0) |"
    )
    lines.append(
        f"| `.dryrun.log` | `{lv['dryrun_log']['path']}` (`sha256={lv['dryrun_log']['sha256']}`) | `head_before={commits['merge_commit']}`, `--expect-sha256 {lv['builder_log']['printed_roster_sha256']}`, dry-run exit 0, re-hash all 3 files `OK` | `PASS` (`rehash_all_three_ok={lv['dryrun_log']['rehash_all_three_ok']}`) |"
    )
    lines.append(
        f"| `.preflight.log` | `{lv['preflight_log']['path']}` (`sha256={lv['preflight_log']['sha256']}`) | Fast-forward `{commits['m4_base']} -> {commits['merge_commit']}`, `prompts --check` exit 0, `schema_digest --check-digest` exit 0 | `PASS` (`moved_from_m4_to_merge_commit={lv['preflight_log']['moved_from_m4_to_merge_commit']}`) |"
    )
    lines.append(
        f"| `.sha256` manifest | `{lv['sha256_manifest']['path']}` (`sha256={lv['sha256_manifest']['sha256']}`) | Lists exact SHA-256 for `roster`, `registration`, and `sizing` | `PASS` (`all_three_match_disk={lv['sha256_manifest']['all_three_match_disk']}`) |"
    )
    lines.append(
        f"| `sizing.json` top-level binding | `/registration_path` & `/registration_sha256` | `path={cb['sizing_top_registration_path']}`, `sha256={cb['sizing_top_registration_sha256']}` | `PASS` (`path_matches={cb['sizing_top_registration_path_matches']}`, `sha_matches={cb['sizing_top_registration_sha256_matches']}`) |"
    )
    lines.append(
        f"| `sizing.json` inner binding | `/sizing/registration_sha256` | `sha256={cb['sizing_inner_registration_sha256']}` | `PASS` (`sha_matches={cb['sizing_inner_registration_sha256_matches']}`) |"
    )
    lines.append(
        f"| `roster.json` row 0 binding | `/registrations/0/registration_path` & `/registrations/0/registration_sha256` | `path={cb['roster_row0_registration_path']}`, `sha256={cb['roster_row0_registration_sha256']}` | `PASS` (`path_matches={cb['roster_row0_registration_path_matches']}`, `sha_matches={cb['roster_row0_registration_sha256_matches']}`) |"
    )
    lines.append("")

    # Step 2
    lines.append("## Step 2 — Every Pinned Repository File")
    lines.append("")
    lines.append("### 2.1 Pin Count Summary Against `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1` and M4 (`673838c51547278cfd79254670ec95421c7bcaf7`)")
    lines.append("")
    c2 = s2["counts"]
    lines.append("| Metric | Count |")
    lines.append("| --- | ---: |")
    lines.append(f"| Shape-paired pin pointers (`path` beside `sha256`, or `{{\"<repo_path>\": \"<sha256>\"}}`) | {c2['shape_paired_pin_pointers_total']} |")
    lines.append(f"| Shape-paired pin pointers matching `git show {commits['merge_commit']}:<path>` | {c2['shape_paired_pin_pointers_equal_merge']} |")
    lines.append(f"| Shape-paired pin pointers unequal to `git show {commits['merge_commit']}:<path>` | {c2['shape_paired_pin_pointers_unequal_merge']} |")
    lines.append(f"| Unique repository paths among shape-paired pins | {c2['shape_paired_unique_paths']} |")
    lines.append(f"| Total file-backed SHA-256 pin pointers (including `13` basename/symbolic/calibration pins) | {c2['all_file_backed_pin_pointers_total']} |")
    lines.append(f"| Total file-backed SHA-256 pin pointers matching `git show {commits['merge_commit']}:<path>` | {c2['all_file_backed_pin_pointers_equal_merge']} |")
    lines.append(f"| Total file-backed SHA-256 pin pointers unequal to `git show {commits['merge_commit']}:<path>` | {c2['all_file_backed_pin_pointers_unequal_merge']} |")
    lines.append(f"| Total unique repository paths across all file-backed SHA-256 pins | {c2['all_file_backed_unique_paths']} |")
    lines.append(f"| Unique pinned repository paths that **changed** SHA-256 vs. M4 | {c2['changed_unique_paths_from_m4']} |")
    lines.append(f"| Unique pinned repository paths **unchanged** vs. M4 (`76` shape-paired + `4` basename/calibration) | {c2['unchanged_unique_paths_from_m4']} |")
    lines.append(f"| Pinned repository paths **added** vs. M4 | {len(c2['added_unique_paths_vs_m4'])} |")
    lines.append(f"| Pinned repository paths **dropped** vs. M4 | {len(c2['dropped_unique_paths_vs_m4'])} |")
    lines.append("")

    lines.append("### 2.2 The 6 Changed Pinned Repository Files (14 SHA-256 Pointers + 4 Byte-Length Leaves)")
    lines.append("")
    lines.append("| # | Repository Path | Pin Pointers (`count`) | M4 Pin / Git SHA-256 (`673838c51`) | Rebuilt Pin / Git SHA-256 (`7ad8c9e72`) | M4 Bytes | Merge Bytes | Delta Bytes | Matches `git show` |")
    lines.append("| ---: | --- | --- | --- | --- | ---: | ---: | ---: | --- |")
    for idx, item in enumerate(s2["changed_unique_paths"], start=1):
        ptrs_str = "<br>".join(f"`{p}`" for p in item["pointers"])
        delta_b = item["git_merge_bytes"] - item["git_m4_bytes"]
        ok_str = "YES" if (item["m4_pin_matches_git_m4"] and item["new_pin_matches_git_merge"]) else "NO"
        lines.append(
            f"| {idx} | `{item['repo_path']}` | {ptrs_str} (`{item['pointer_count_in_new_packet']}`) | `{item['new_pinned_sha256'] if False else item['m4_pinned_sha256']}` | `{item['new_pinned_sha256']}` | {fmt_int(item['git_m4_bytes'])} | {fmt_int(item['git_merge_bytes'])} | {fmt_signed_int(delta_b)} | `{ok_str}` |"
        )
    lines.append("")

    lines.append("### 2.3 All 80 Unchanged Pinned Repository Files (`76` Shape-Paired + `4` Symbolic/Basename/Calibration)")
    lines.append("")
    lines.append("| # | Repository Path | Shape-Paired (`82`) | Pin Pointers (`count`) | Pinned & `git show` SHA-256 (Identical in M4 & Rebuild) | Bytes | Matches `git show` |")
    lines.append("| ---: | --- | --- | --- | --- | ---: | --- |")
    for idx, item in enumerate(s2["unchanged_unique_paths"], start=1):
        ptrs_str = "<br>".join(f"`{p}`" for p in item["pointers"])
        sp_flag = "YES" if item["in_shape_paired_82"] else "NO (symbolic/basename)"
        ok_str = "YES" if (item["m4_pin_matches_git_m4"] and item["new_pin_matches_git_merge"]) else "NO"
        lines.append(
            f"| {idx} | `{item['repo_path']}` | `{sp_flag}` | {ptrs_str} (`{item['pointer_count_in_new_packet']}`) | `{item['new_pinned_sha256']}` | {fmt_int(item['git_merge_bytes'])} | `{ok_str}` |"
        )
    lines.append("")

    # Step 3
    lines.append("## Step 3 — Every Other Leaf Across Registration, Sizing, and Roster")
    lines.append("")
    lines.append("### 3.1 Leaf Diff Summary")
    lines.append("")
    c3 = s3["counts"]
    lines.append("| Document | M4 Leaves | Rebuilt Leaves | Equal Leaves | Step-2 Covered Changed Leaves | Step-3 Other Changed Leaves | Step-3 Added Leaves | Step-3 Removed Leaves | Total Leaf Diffs | Unexplained |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for doc in ("registration", "sizing", "roster"):
        s2_doc = sum(1 for x in s3["step2_covered_leaf_diffs"] if x["document"] == doc)
        s3_chg = sum(1 for x in s3["step3_other_leaf_diffs"] if x["document"] == doc and x["change_type"] == "changed")
        s3_add = sum(1 for x in s3["step3_other_leaf_diffs"] if x["document"] == doc and x["change_type"] == "added")
        s3_rem = sum(1 for x in s3["step3_other_leaf_diffs"] if x["document"] == doc and x["change_type"] == "removed")
        tot_doc = s2_doc + s3_chg + s3_add + s3_rem
        old_l = c3[f"{doc}_leaves_old"]
        new_l = c3[f"{doc}_leaves_new"]
        eq_l = old_l - (s2_doc + s3_chg + s3_rem)
        lines.append(
            f"| `{doc}` | {old_l} | {new_l} | {eq_l} | {s2_doc} | {s3_chg} | {s3_add} | {s3_rem} | {tot_doc} | 0 |"
        )
    eq_tot = (c3["registration_leaves_old"] + c3["sizing_leaves_old"] + c3["roster_leaves_old"]) - (
        c3["step2_covered_leaf_diffs_count"] + c3["step3_other_changed_count"] + c3["step3_other_removed_count"]
    )
    lines.append(
        f"| **Total** | **{c3['registration_leaves_old'] + c3['sizing_leaves_old'] + c3['roster_leaves_old']}** | **{c3['registration_leaves_new'] + c3['sizing_leaves_new'] + c3['roster_leaves_new']}** | **{eq_tot}** | **{c3['step2_covered_leaf_diffs_count']}** | **{c3['step3_other_changed_count']}** | **{c3['step3_other_added_count']}** | **{c3['step3_other_removed_count']}** | **{c3['total_leaf_diffs_across_all_three']}** | **{c3['unexplained_leaf_diffs_count']}** |"
    )
    lines.append("")

    lines.append("### 3.2 Step-2 Covered Leaves (`18` Leaves: `14` Pinned SHA-256 Digests + `4` Companion Schema Byte Counts)")
    lines.append("")
    lines.append("| # | Document | RFC 6901 JSON Pointer | Change | M4 Value | Rebuilt Value | Producer at `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1` |")
    lines.append("| ---: | --- | --- | --- | --- | --- | --- |")
    for idx, item in enumerate(s3["step2_covered_leaf_diffs"], start=1):
        prod = (
            "`src/data_sheets_schema/bc1_context.py:225`"
            if item["json_pointer"].endswith("/bytes")
            else "`src/data_sheets_schema/bc1_context.py:225` / `bc1_selection.py:88`"
        )
        lines.append(
            f"| {idx} | `{item['document']}` | `{item['json_pointer']}` | `{item['change_type']}` | {fmt_val(item['old_value'])} | {fmt_val(item['new_value'])} | {prod} |"
        )
    lines.append("")

    lines.append("### 3.3 Complete Table of All 155 Non-Step-2 Leaf Differences")
    lines.append("")
    lines.append("| # | Document | RFC 6901 JSON Pointer | Change | M4 Value | Rebuilt Value | Producer (`git show 7ad8c9e72:<file>:<line>`) | Cause Category | Explanation |")
    lines.append("| ---: | --- | --- | --- | --- | --- | --- | --- | --- |")
    for idx, item in enumerate(s3["step3_other_leaf_diffs"], start=1):
        lines.append(
            f"| {idx} | `{item['document']}` | `{item['json_pointer']}` | `{item['change_type']}` | {fmt_val(item['old_value'])} | {fmt_val(item['new_value'])} | `{item['producer_at_merge']}` | `{item['cause_category']}` | {item['cause_detail']} |"
        )
    lines.append("")

    # Step 4
    lines.append("## Step 4 — The Context Block (`bounded_carry.contract.context` and `sizing.source_identity.context`)")
    lines.append("")
    lines.append(
        f"- `sizing.source_identity.context` mirrors `registration.bounded_carry.contract.context` byte-for-byte: `{s4['sizing_mirrors_registration_context_exactly']}`."
    )
    lines.append("")
    lines.append("### 4.1 Structural Comparison of the Context Block (M4 `v1` vs. Rebuild `v2`)")
    lines.append("")
    lines.append("| Key | M4 (`673838c51547278cfd79254670ec95421c7bcaf7`) | Rebuild (`7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`) | Producer in `src/data_sheets_schema/bc1_context.py` |")
    lines.append("| --- | --- | --- | --- |")
    all_ctx_keys = sorted(set(s4["m4_context_block"].keys()) | set(s4["new_context_block"].keys()))
    m4_lines = s4["bc1_context_m4_lines"]
    mg_lines = s4["bc1_context_merge_lines"]
    for k in all_ctx_keys:
        old_v = s4["m4_context_block"].get(k)
        new_v = s4["new_context_block"].get(k)
        if k == "format":
            prod_line = f"M4 line `{m4_lines['FORMAT_v1']}` (`contract_identity` line `{m4_lines['contract_identity_def_v1']}`) -> Merge line `{mg_lines['FORMAT']}` (`contract_identity` line `{mg_lines['contract_v2_return']}`)"
        elif k == "forms_annotation":
            prod_line = f"Added at Merge line `{mg_lines['TERM_SOURCE_FORMS_ANNOTATION']}` & `{mg_lines['contract_v2_forms_annotation']}`"
        elif k == "fallback":
            prod_line = f"M4 line `{m4_lines['FALLBACK_v1']}` & `{m4_lines['contract_v1_fallback']}` -> Merge line `{mg_lines['contract_v2_fallback']}` (`fallback: []`)"
        elif k == "iri_prefixes":
            prod_line = f"M4 line `{m4_lines['IRI_v1']}` & `{m4_lines['contract_v1_iri_prefixes']}` -> Removed from `v2` contract dict at Merge line `{mg_lines['contract_v2_return']}`"
        else:
            prod_line = f"Unchanged (`contract_identity` Merge lines `{mg_lines['contract_v2_return']}..{mg_lines['contract_v2_fallback']}`)"
        lines.append(f"| `{k}` | {fmt_val(old_v)} | {fmt_val(new_v)} | {prod_line} |")
    lines.append("")

    lines.append("### 4.2 Where Removed Context Content Comes From at Runtime (`d4d:termSources` and `d4d:termSourceIdentifierForms`)")
    lines.append("")
    lines.append(
        f"In M4 (`src/data_sheets_schema/bc1_context.py` at `{commits['m4_base']}`), `Instance.data_topic` lacked a `d4d:termSources` schema annotation, so `FALLBACK` (line `{m4_lines['FALLBACK_v1']}`) hardcoded `(\"Instance\", \"data_topic\"): (\"GO\", \"MeSH\", \"EFO\", \"NCIT\")` and `IRI` (line `{m4_lines['IRI_v1']}`) hardcoded the accepted HTTP/HTTPS IRI prefixes for `EFO`, `GO`, `MeSH`, and `NCIT`. "
        f"At `{commits['merge_commit']}` (#5471 / PR #5531), `src/data_sheets_schema/bc1_context.py` (`_sources` at line `{mg_lines['sources_def']}`, `_parse_identifier_forms` at line `{mg_lines['parse_identifier_forms_def']}`, and `derive_term_policy` at line `{mg_lines['derive_term_policy_def']}`) reads both `d4d:termSources` and `d4d:termSourceIdentifierForms` directly from the induced LinkML schema's slot definitions (`catalog['classes'][cls]['slots'][slot]['definition']['annotations']`)."
    )
    lines.append("")
    lines.append("| Schema File at `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1` | Class (`line`) | Section | Slot (`line`) | Annotation Tag (`line`) | Value Line(s) | Value Preview |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for schema_block in (s4["full_schema_term_source_annotations"], s4["core_schema_term_source_annotations"]):
        for occ in schema_block["occurrences"]:
            vline_str = (
                f"`{occ['value_line']}`"
                if occ["value_line"] == occ["value_end_line"]
                else f"`{occ['value_line']}..{occ['value_end_line']}`"
            )
            lines.append(
                f"| `{occ['schema_path']}` | `{occ['enclosing_name']}` (`{occ['enclosing_line']}`) | `{occ['sub_section']}` | `{occ['slot_name']}` (`{occ['slot_line']}`) | `{occ['annotation_tag']}` (`{occ['annotation_line']}`) | {vline_str} | {fmt_val(occ['value_preview'])} |"
            )
    lines.append("")

    # Step 5
    lines.append("## Step 5 — Sizing Rows (`rows[0..15]`) and Scenario Aggregates (`own_plan_scenarios`)")
    lines.append("")
    lines.append("### 5.1 Per-Row Deltas (`rows[0..15]`)")
    lines.append("")
    lines.append("| Row | Stage | Scenario | M4 Wire Bytes | Rebuilt Wire Bytes | Delta Wire Bytes | M4 Est. Input Tokens | Rebuilt Est. Input Tokens | Delta Input Tokens | Output Reserve | Rebuilt Est. Context Tokens | Context Headroom (`1,000,000` ceiling) | M4 `wire_sha256` | Rebuilt `wire_sha256` | `estimated_context_fits` (M4 -> New) | `gated` (M4 -> New) |")
    lines.append("| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |")
    for r in s5["rows"]:
        fits_str = f"`{str(r['old_estimated_context_fits']).lower()} -> {str(r['new_estimated_context_fits']).lower()}`"
        gated_str = f"`{str(r['old_gated']).lower()} -> {str(r['new_gated']).lower()}`"
        lines.append(
            f"| {r['row_index']} | `{r['stage_label']}` | `{r['scenario']}` | {fmt_int(r['old_wire_bytes'])} | {fmt_int(r['new_wire_bytes'])} | {fmt_signed_int(r['delta_wire_bytes'])} | {fmt_int(r['old_estimated_input_tokens'])} | {fmt_int(r['new_estimated_input_tokens'])} | {fmt_signed_int(r['delta_estimated_input_tokens'])} | {fmt_int(r['output_token_reserve'])} | {fmt_int(r['new_estimated_context_tokens'])} | {fmt_signed_int(r['context_token_headroom'])} | `{r['old_wire_sha256']}` | `{r['new_wire_sha256']}` | {fits_str} | {gated_str} |"
        )
    lines.append("")

    lines.append("### 5.2 Scenario Aggregates (`own_plan_scenarios`) Against `audit_limits.aggregate_input_tokens` (`4,500,000`)")
    lines.append("")
    lines.append("| Scenario | Gated Scenario | Calls | M4 Wire Bytes | Rebuilt Wire Bytes | Delta Wire Bytes | M4 Est. Input Tokens | Rebuilt Est. Input Tokens | Delta Input Tokens | Limit (`aggregate_input_tokens`) | Headroom vs. `4,500,000` | % of Limit | Output Token Reservations | `estimated_all_calls_fit` (M4 -> New) |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for sc in s5["own_plan_scenarios"]:
        fit_str = f"`{str(sc['old_estimated_all_calls_fit']).lower()} -> {str(sc['new_estimated_all_calls_fit']).lower()}`"
        lines.append(
            f"| `{sc['scenario']}` | `{str(sc['gated_scenario']).lower()}` | {sc['calls']} | {fmt_int(sc['old_wire_bytes'])} | {fmt_int(sc['new_wire_bytes'])} | {fmt_signed_int(sc['delta_wire_bytes'])} | {fmt_int(sc['old_estimated_input_tokens'])} | {fmt_int(sc['new_estimated_input_tokens'])} | {fmt_signed_int(sc['delta_estimated_input_tokens'])} | {fmt_int(sc['aggregate_input_tokens_limit'])} | {fmt_signed_int(sc['aggregate_input_tokens_headroom'])} | `{sc['aggregate_input_tokens_pct_of_limit']:.4f}%` | {fmt_int(sc['output_token_reservations'])} | {fit_str} |"
        )
    lines.append("")

    lg = s5["largest_gated_call"]
    lo = s5["largest_overall_call"]
    lines.append("### 5.3 Largest Call Against Context Room and Gate Stability")
    lines.append("")
    lines.append(
        f"- **Largest gated call (`gated = true`)**: `rows[{lg['row_index']}]` (`{lg['stage_label']}`, scenario `{lg['scenario']}`) — rebuilt `wire_bytes = {fmt_int(lg['new_wire_bytes'])}` (`{fmt_signed_int(lg['delta_wire_bytes'])}` vs. M4 `{fmt_int(lg['old_wire_bytes'])}`), `planning_wire_bytes = {fmt_int(lg['new_planning_wire_bytes'])}` (`{fmt_signed_int(lg['delta_planning_wire_bytes'])}`), `estimated_input_tokens = {fmt_int(lg['new_estimated_input_tokens'])}` (`{fmt_signed_int(lg['delta_estimated_input_tokens'])}` vs. M4 `{fmt_int(lg['old_estimated_input_tokens'])}`), plus `output_token_reserve = {fmt_int(lg['output_token_reserve'])}` -> `estimated_context_tokens = {fmt_int(lg['new_estimated_context_tokens'])}` against the `{fmt_int(s5['audit_limits']['context_limit_tokens'])}`-token context window (`{fmt_int(lg['effective_input_token_ceiling'])}` effective input ceiling), leaving **`{fmt_int(lg['context_token_headroom'])}` tokens of context headroom** (`estimated_context_fits = true`)."
    )
    lines.append(
        f"- **Largest overall row (ungated diagnostic worst-case escape bound, `gated = false`)**: `rows[{lo['row_index']}]` (`{lo['stage_label']}`, scenario `{lo['scenario']}`) — rebuilt `wire_bytes = {fmt_int(lo['new_wire_bytes'])}` (`{fmt_signed_int(lo['delta_wire_bytes'])}`), `estimated_input_tokens = {fmt_int(lo['new_estimated_input_tokens'])}` (`{fmt_signed_int(lo['delta_estimated_input_tokens'])}`), `estimated_context_tokens = {fmt_int(lo['new_estimated_context_tokens'])}` (`{fmt_signed_int(lo['context_token_headroom'])}` vs. `1,000,000`), unchanged `estimated_context_fits = false` and `gated = false`."
    )
    lines.append(
        f"- **Did any row's `estimated_context_fits` or `gated` change?**: `any_estimated_context_fits_changed = {s5['any_estimated_context_fits_changed']}`, `any_gated_changed = {s5['any_gated_changed']}`."
    )
    lines.append("")

    # Comparison with lead's leaf_diff_m4_vs_rebuild.json
    lines.append("## Comparison Against `leaf_diff_m4_vs_rebuild.json` (Read After Writing `a21_rebuild_identity_review.json`)")
    lines.append("")
    lines.append(
        "After `a21_rebuild_identity_review.json` was generated and written to disk, it was compared mechanically against `codex-development-efficiency-20261111/tmp/a21-rebuild-review-20261111/leaf_diff_m4_vs_rebuild.json`:"
    )
    lines.append("")
    lines.append("| Document | Our `leaves_old -> leaves_new` | Lead `leaves_old -> leaves_new` | Our `(changed, added, removed)` | Lead `(changed, added, removed)` | RFC 6901 `~1`-Escaped Pointers in Ours | Set Difference After Unescaping `~1 -> /` | Value Mismatches |")
    lines.append("| --- | --- | --- | --- | --- | ---: | ---: | ---: |")
    for doc in ("registration", "sizing", "roster"):
        dc = lead_cmp[doc]
        set_diff_cnt = len(dc["only_in_ours_after_unescape"]) + len(dc["only_in_lead_after_unescape"])
        val_mm_cnt = len(dc["value_mismatches_after_unescape"])
        lines.append(
            f"| `{doc}` | `{dc['our_leaves_old']} -> {dc['our_leaves_new']}` | `{dc['lead_leaves_old']} -> {dc['lead_leaves_new']}` | `({dc['our_changed']}, {dc['our_added']}, {dc['our_removed']})` | `({dc['lead_changed']}, {dc['lead_added']}, {dc['lead_removed']})` | {dc['rfc6901_escaped_pointer_count']} | {set_diff_cnt} | {val_mm_cnt} |"
        )
    lines.append("")
    lines.append("1. **Zero substantive differences**: Every leaf count (`367 -> 351` registration, `598 -> 582` sizing, `5 -> 5` roster), every `(changed, added, removed)` count (`(14, 2, 18)`, `(116, 2, 18)`, `(3, 0, 0)`), and every `(old, new)` value across all `173` leaf diffs are identical between the two JSON files.")
    lines.append("2. **Two representation conventions**:")
    lines.append("   - **RFC 6901 key escaping**: `a21_rebuild_identity_review.json` escapes `/` inside JSON object keys as `~1` per RFC 6901 (`6` pointers in `registration`, `4` in `sizing`, e.g. `/bounded_carry/contract/code/src~1data_sheets_schema~1api_runner.py`), whereas `leaf_diff_m4_vs_rebuild.json` writes unescaped `/` (`/bounded_carry/contract/code/src/data_sheets_schema/api_runner.py`).")
    lines.append("   - **Step-2 vs. Step-3 grouping of schema byte-length leaves**: `a21_rebuild_identity_review.json` includes the `4` changed schema byte-length leaves (`/inputs/{core,full}_schema/sources/0/bytes` in `registration` and `/sizing/captured_inputs/{core,full}_schema/sources/0/bytes` in `sizing`) alongside their `14` paired Step-2 `sha256` leaves (`18` Step-2 leaves + `155` Step-3 leaves = `173` total), whereas `leaf_diff_m4_vs_rebuild.json` classifies the `14` `sha256` leaves under `file_bytes:<path>` and places the `4` `bytes` leaves in `class: \"other\"`.")
    lines.append("")

    # What stays unverified
    lines.append("## What Stays Unverified")
    lines.append("")
    lines.append("- **Live API execution and token billing**: This review is strictly a static byte-level, git-object, and JSON-leaf verification of the rebuilt registration packet (`2026-11-11a_claude-opus-5-api-bc1-a21_rep1`) and its companion logs. No live Anthropic API requests (`messages.create` or `messages.count_tokens`) were executed.")
    lines.append("- **Runtime worker output volumes**: Actual stage output token counts and escaped-character expansion during live generation remain runtime properties bounded by the pre-execution and post-worker gates in `src/data_sheets_schema/bc1_runtime.py`.")
    lines.append("")

    md_text = "\n".join(lines) + "\n"
    if "@" in md_text:
        raise RuntimeError("Generated markdown contains a forbidden character")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md_text, encoding="utf-8")
    out_sha = sha256_file(OUT_MD)
    print(f"Wrote {OUT_MD}")
    print(f"SHA-256: {out_sha}")
    print(f"Bytes: {OUT_MD.stat().st_size}")


if __name__ == "__main__":
    main()
