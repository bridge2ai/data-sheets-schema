#!/usr/bin/env python3
"""Independent mechanical identity review of the rebuilt A21 registration packet.

Purpose: Verify from raw bytes and `git show` at the merge commit
  `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1` and M4 commit
  `673838c51547278cfd79254670ec95421c7bcaf7` whether the rebuilt A21 packet
  (`2026-11-11a_claude-opus-5-api-bc1-a21_rep1`) differs from the M4 packet
  (`2026-11-05a_claude-opus-5-api-bc1-a21_rep1`) only where the six moved
  pinned files and the new label require.
Inputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_2026-11-11a_claude-opus-5-api-bc1-a21_rep1/
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_2026-11-05a_claude-opus-5-api-bc1-a21_rep1/
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_2026-11-11a_claude-opus-5-api-bc1-a21_rep1.{preflight,builder,check,dryrun}.log and .sha256
  - Git object store via `git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21 show`
Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/a21-rebuild-review-20261111/agy2/a21_rebuild_identity_review.json
Serves: claude-lead-agy2-a21-rebuild-identity-review.md (D130, D131)
Date: 2026-11-11
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

LAUNCH_A21 = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21")
PLANS_DIR = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans")
WORKTREE = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
OUT_DIR = WORKTREE / "tmp/a21-rebuild-review-20261111/agy2"
OUT_JSON = OUT_DIR / "a21_rebuild_identity_review.json"

M4_COMMIT = "673838c51547278cfd79254670ec95421c7bcaf7"
MAIN_BEFORE_MERGE = "925d726d67cdd03fe28fdeafdde60fa27df57205"
PR5808_HEAD = "6792947ea6558d10c85106065b023cb57838835a"
PREVIEW_COMMIT = "44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9"
MERGE_COMMIT = "7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1"

OLD_LABEL = "2026-11-05a_claude-opus-5-api-bc1-a21_rep1"
NEW_LABEL = "2026-11-11a_claude-opus-5-api-bc1-a21_rep1"

OLD_PACKET_DIR = PLANS_DIR / f"a21_registration_{OLD_LABEL}"
NEW_PACKET_DIR = PLANS_DIR / f"a21_registration_{NEW_LABEL}"

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
PATHLIKE_RE = re.compile(r"^[A-Za-z0-9_.\-]+(/[A-Za-z0-9_.\- ]+)+\.[A-Za-z0-9]+$")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def git_show_bytes(commit: str, rel_path: str) -> bytes | None:
    proc = subprocess.run(
        ["git", "-C", str(LAUNCH_A21), "show", f"{commit}:{rel_path}"],
        capture_output=True,
        check=False,
        env=_git_env(),
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def git_tree_id(commit: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(LAUNCH_A21), "rev-parse", f"{commit}^{{tree}}"],
        capture_output=True,
        text=True,
        check=True,
        env=_git_env(),
    )
    return proc.stdout.strip()


def escape_ptr(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def flatten_leaves(node: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(node, dict):
        if not node:
            out[prefix] = {}
        else:
            for k, v in node.items():
                out.update(flatten_leaves(v, f"{prefix}/{escape_ptr(str(k))}"))
    elif isinstance(node, list):
        if not node:
            out[prefix] = []
        else:
            for idx, v in enumerate(node):
                out.update(flatten_leaves(v, f"{prefix}/{idx}"))
    else:
        out[prefix] = node
    return out


def to_repo_rel(raw_path: str) -> str:
    prefix = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/"
    if raw_path.startswith(prefix):
        return raw_path[len(prefix) :]
    m = re.search(
        r"/(src|data|\.claude|\.github|notes|scripts|tests|utils|config|project)/",
        raw_path,
    )
    if m and raw_path.startswith("/"):
        return raw_path[m.start() + 1 :]
    return raw_path


def extract_shape_paired_pins(doc: Any, doc_name: str) -> list[dict[str, Any]]:
    """Extract every place that pairs a repository path with a sha256 by shape."""
    pins: list[dict[str, Any]] = []

    def walk(node: Any, ptr: str) -> None:
        if isinstance(node, dict):
            p, s = node.get("path"), node.get("sha256")
            if isinstance(p, str) and isinstance(s, str) and HEX64_RE.match(s):
                rel = to_repo_rel(p)
                if not p.startswith(str(PLANS_DIR)):
                    pins.append(
                        {
                            "document": doc_name,
                            "sha256_pointer": f"{ptr}/sha256",
                            "path_pointer": f"{ptr}/path",
                            "bytes_pointer": f"{ptr}/bytes" if "bytes" in node else None,
                            "raw_path": p,
                            "repo_path": rel,
                            "pinned_sha256": s,
                            "pinned_bytes": node.get("bytes"),
                            "pin_kind": "path_and_sha256_object",
                        }
                    )
            for k, v in node.items():
                child_ptr = f"{ptr}/{escape_ptr(str(k))}"
                if isinstance(v, str) and HEX64_RE.match(v) and PATHLIKE_RE.match(k):
                    pins.append(
                        {
                            "document": doc_name,
                            "sha256_pointer": child_ptr,
                            "path_pointer": child_ptr,
                            "bytes_pointer": None,
                            "raw_path": k,
                            "repo_path": to_repo_rel(k),
                            "pinned_sha256": v,
                            "pinned_bytes": None,
                            "pin_kind": "path_keyed_sha256_map",
                        }
                    )
                walk(v, child_ptr)
        elif isinstance(node, list):
            for idx, v in enumerate(node):
                walk(v, f"{ptr}/{idx}")

    walk(doc, "")
    return pins


def extract_non_shape_file_pins(doc: Any, doc_name: str) -> list[dict[str, Any]]:
    """Extract file-backed SHA-256 pins whose keys are basenames or symbolic keys."""
    extra: list[dict[str, Any]] = []
    if doc_name == "registration":
        # 1. omission_assets_sha256
        om_assets = (
            doc.get("selection", {})
            .get("stage_contracts", {})
            .get("omission_assets_sha256", {})
        )
        for k, v in sorted(om_assets.items()):
            extra.append(
                {
                    "document": doc_name,
                    "sha256_pointer": f"/selection/stage_contracts/omission_assets_sha256/{escape_ptr(k)}",
                    "repo_path": f"src/data_sheets_schema/omission_inventory_v1/{k}",
                    "pinned_sha256": v,
                    "pin_kind": "omission_inventory_basename_key",
                }
            )
        # 2. bounded_carry.contract.audit.omission_contract_sha256
        bc1_om = (
            doc.get("bounded_carry", {})
            .get("contract", {})
            .get("audit", {})
            .get("omission_contract_sha256", {})
        )
        for k, v in sorted(bc1_om.items()):
            extra.append(
                {
                    "document": doc_name,
                    "sha256_pointer": f"/bounded_carry/contract/audit/omission_contract_sha256/{escape_ptr(k)}",
                    "repo_path": f"src/data_sheets_schema/omission_inventory_v1/{k}",
                    "pinned_sha256": v,
                    "pin_kind": "omission_inventory_basename_key",
                }
            )
        # 3. evidence_protocol_sha256
        ev_sha = (
            doc.get("selection", {})
            .get("stage_contracts", {})
            .get("evidence_protocol_sha256")
        )
        if ev_sha:
            extra.append(
                {
                    "document": doc_name,
                    "sha256_pointer": "/selection/stage_contracts/evidence_protocol_sha256",
                    "repo_path": "src/download/prompts/evidence_protocol_v7.md",
                    "pinned_sha256": ev_sha,
                    "pin_kind": "symbolic_file_sha256_key",
                }
            )
        # 4. receipt.runtime_policy_sha256
        rp_sha = doc.get("receipt", {}).get("runtime_policy_sha256")
        if rp_sha:
            extra.append(
                {
                    "document": doc_name,
                    "sha256_pointer": "/receipt/runtime_policy_sha256",
                    "repo_path": "src/download/prompts/receipt_completion_runtime_v2.md",
                    "pinned_sha256": rp_sha,
                    "pin_kind": "symbolic_file_sha256_key",
                }
            )
        # 5. d63_count_tokens_request_2026-10-28.json
        d63_sha = (
            doc.get("bounded_carry", {})
            .get("contract", {})
            .get("sizing_calibration", {})
            .get("request_measurement", {})
            .get("request_sha256")
        )
        if d63_sha:
            extra.append(
                {
                    "document": doc_name,
                    "sha256_pointer": "/bounded_carry/contract/sizing_calibration/request_measurement/request_sha256",
                    "repo_path": "notes/reviews/d63_count_tokens_request_2026-10-28.json",
                    "pinned_sha256": d63_sha,
                    "pin_kind": "calibration_request_sha256_key",
                }
            )
    elif doc_name == "sizing":
        # 1. sizing.source_identity.audit.omission_contract_sha256
        sz_om = (
            doc.get("sizing", {})
            .get("source_identity", {})
            .get("audit", {})
            .get("omission_contract_sha256", {})
        )
        for k, v in sorted(sz_om.items()):
            extra.append(
                {
                    "document": doc_name,
                    "sha256_pointer": f"/sizing/source_identity/audit/omission_contract_sha256/{escape_ptr(k)}",
                    "repo_path": f"src/data_sheets_schema/omission_inventory_v1/{k}",
                    "pinned_sha256": v,
                    "pin_kind": "omission_inventory_basename_key",
                }
            )
        # 2. sizing.calibration.request_measurement.request_sha256
        d63_sha = (
            doc.get("sizing", {})
            .get("calibration", {})
            .get("request_measurement", {})
            .get("request_sha256")
        )
        if d63_sha:
            extra.append(
                {
                    "document": doc_name,
                    "sha256_pointer": "/sizing/calibration/request_measurement/request_sha256",
                    "repo_path": "notes/reviews/d63_count_tokens_request_2026-10-28.json",
                    "pinned_sha256": d63_sha,
                    "pin_kind": "calibration_request_sha256_key",
                }
            )
    return extra


def find_line_numbers_in_commit(commit: str, rel_path: str, patterns: dict[str, str]) -> dict[str, int]:
    raw = git_show_bytes(commit, rel_path)
    if raw is None:
        raise RuntimeError(f"Cannot git show {commit}:{rel_path}")
    lines = raw.decode("utf-8").splitlines()
    found: dict[str, int] = {}
    for key, regex in patterns.items():
        pat = re.compile(regex)
        matches = [i + 1 for i, line in enumerate(lines) if pat.search(line)]
        if not matches:
            raise RuntimeError(f"Pattern {key!r} ({regex!r}) not found in {commit}:{rel_path}")
        found[key] = matches[0]
    return found


def find_term_source_slots_in_schema(commit: str, rel_path: str) -> dict[str, Any]:
    raw = git_show_bytes(commit, rel_path)
    if raw is None:
        raise RuntimeError(f"Cannot git show {commit}:{rel_path}")
    lines = raw.decode("utf-8").splitlines()

    # Locate top-level `slots:` section and `classes:` section
    slots_header_line = None
    classes_header_line = None
    for idx, line in enumerate(lines):
        if line == "slots:":
            slots_header_line = idx + 1
        elif line == "classes:":
            classes_header_line = idx + 1

    # Walk lines to find every occurrence of d4d:termSources and d4d:termSourceIdentifierForms
    # and the enclosing 2-space-indented slot/class definition and 6-space slot_usage if applicable.
    current_top_section = None
    current_indent2_name = None
    current_indent2_line = None
    current_indent4_section = None
    current_indent6_name = None
    current_indent6_line = None

    occurrences: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        lineno = idx + 1
        if re.match(r"^[a-z_]+:\s*$", line):
            current_top_section = line.split(":")[0]
            current_indent2_name = None
            current_indent4_section = None
            current_indent6_name = None
            continue
        m2 = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if m2:
            current_indent2_name = m2.group(1)
            current_indent2_line = lineno
            current_indent4_section = None
            current_indent6_name = None
            continue
        m4 = re.match(r"^    ([a-z_]+):\s*$", line)
        if m4:
            current_indent4_section = m4.group(1)
            if current_indent4_section not in ("slot_usage", "attributes"):
                current_indent6_name = None
                current_indent6_line = None
            continue
        m6 = re.match(r"^      ([A-Za-z0-9_]+):\s*$", line)
        if m6 and current_indent4_section in ("slot_usage", "attributes"):
            current_indent6_name = m6.group(1)
            current_indent6_line = lineno
            continue

        if "d4d:termSources:" in line or "d4d:termSourceIdentifierForms:" in line:
            tag = (
                "d4d:termSourceIdentifierForms"
                if "d4d:termSourceIdentifierForms:" in line
                else "d4d:termSources"
            )
            # Look ahead a few lines for `value:` if tag/value dict form
            val_line = lineno
            val_end_line = lineno
            val_preview = line.strip()
            for look in range(idx + 1, min(idx + 5, len(lines))):
                if "value:" in lines[look]:
                    val_line = look + 1
                    val_end_line = val_line
                    val_preview = lines[look].strip()
                    for cont in range(look + 1, min(look + 25, len(lines))):
                        if lines[cont].startswith("              "):
                            val_end_line = cont + 1
                        else:
                            break
                    break
            occurrences.append(
                {
                    "schema_path": rel_path,
                    "top_section": current_top_section,
                    "enclosing_name": current_indent2_name,
                    "enclosing_line": current_indent2_line,
                    "sub_section": current_indent4_section,
                    "slot_name": current_indent6_name,
                    "slot_line": current_indent6_line,
                    "annotation_tag": tag,
                    "annotation_line": lineno,
                    "value_line": val_line,
                    "value_end_line": val_end_line,
                    "value_preview": val_preview[:160],
                }
            )
    return {
        "schema_path": rel_path,
        "slots_header_line": slots_header_line,
        "classes_header_line": classes_header_line,
        "occurrences": occurrences,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Verify tree equality between preview commit and merge commit
    preview_tree = git_tree_id(PREVIEW_COMMIT)
    merge_tree = git_tree_id(MERGE_COMMIT)

    # Step 1: Hash the three new files, three old files, and parse logs
    new_files_spec = [
        ("roster", NEW_PACKET_DIR / f"roster_{NEW_LABEL}.json", 447, "d49cc3529a11e60716cde4affc6f5deec521b861576fcae6b961e2f74060dd63"),
        ("registration", NEW_PACKET_DIR / f"registration_chorus_{NEW_LABEL}.json", 26284, "55691023e1d75c3bf5f9df09dcb524b4536870b93a4a3dde67306276f082aa1a"),
        ("sizing", NEW_PACKET_DIR / f"registration_chorus_{NEW_LABEL}.sizing.json", 32182, "0ae32356404e52d28acf0ff9ae8e39707947664df7506104a52fbab438465c87"),
    ]
    old_files_spec = [
        ("roster", OLD_PACKET_DIR / f"roster_{OLD_LABEL}.json"),
        ("registration", OLD_PACKET_DIR / f"registration_chorus_{OLD_LABEL}.json"),
        ("sizing", OLD_PACKET_DIR / f"registration_chorus_{OLD_LABEL}.sizing.json"),
    ]

    new_artifacts: dict[str, dict[str, Any]] = {}
    for kind, path, expected_bytes, expected_sha in new_files_spec:
        raw = path.read_bytes()
        actual_sha = sha256_bytes(raw)
        new_artifacts[kind] = {
            "kind": kind,
            "path": str(path),
            "filename": path.name,
            "actual_bytes": len(raw),
            "expected_bytes_in_assignment": expected_bytes,
            "bytes_match_assignment": len(raw) == expected_bytes,
            "actual_sha256": actual_sha,
            "expected_sha256_in_assignment": expected_sha,
            "sha256_matches_assignment": actual_sha == expected_sha,
        }

    old_artifacts: dict[str, dict[str, Any]] = {}
    for kind, path in old_files_spec:
        raw = path.read_bytes()
        old_artifacts[kind] = {
            "kind": kind,
            "path": str(path),
            "filename": path.name,
            "actual_bytes": len(raw),
            "actual_sha256": sha256_bytes(raw),
        }

    new_reg = json.loads((NEW_PACKET_DIR / f"registration_chorus_{NEW_LABEL}.json").read_text(encoding="utf-8"))
    new_sizing = json.loads((NEW_PACKET_DIR / f"registration_chorus_{NEW_LABEL}.sizing.json").read_text(encoding="utf-8"))
    new_roster = json.loads((NEW_PACKET_DIR / f"roster_{NEW_LABEL}.json").read_text(encoding="utf-8"))

    old_reg = json.loads((OLD_PACKET_DIR / f"registration_chorus_{OLD_LABEL}.json").read_text(encoding="utf-8"))
    old_sizing = json.loads((OLD_PACKET_DIR / f"registration_chorus_{OLD_LABEL}.sizing.json").read_text(encoding="utf-8"))
    old_roster = json.loads((OLD_PACKET_DIR / f"roster_{OLD_LABEL}.json").read_text(encoding="utf-8"))

    # Parse logs
    builder_log_path = PLANS_DIR / f"a21_registration_{NEW_LABEL}.builder.log"
    check_log_path = PLANS_DIR / f"a21_registration_{NEW_LABEL}.check.log"
    dryrun_log_path = PLANS_DIR / f"a21_registration_{NEW_LABEL}.dryrun.log"
    preflight_log_path = PLANS_DIR / f"a21_registration_{NEW_LABEL}.preflight.log"
    sha256_file_path = PLANS_DIR / f"a21_registration_{NEW_LABEL}.sha256"

    builder_text = builder_log_path.read_text(encoding="utf-8")
    check_text = check_log_path.read_text(encoding="utf-8")
    dryrun_text = dryrun_log_path.read_text(encoding="utf-8")
    preflight_text = preflight_log_path.read_text(encoding="utf-8")
    sha256_text = sha256_file_path.read_text(encoding="utf-8")

    m_reg = re.search(r"registration_id=(\S+)\s+sha256=([0-9a-f]{64})\s+context_sha256=([0-9a-f]{64})", builder_text)
    m_sz = re.search(r"sizing record (\S+)\s+sha256=([0-9a-f]{64})", builder_text)
    m_rst = re.search(r"Roster with 1 rows: (\S+)\s+\(sha256=([0-9a-f]{64})\)", builder_text)

    sha256_lines = {}
    for line in sha256_text.strip().splitlines():
        parts = line.split()
        if len(parts) == 2:
            sha256_lines[parts[1]] = parts[0]

    log_verification = {
        "builder_log": {
            "path": str(builder_log_path),
            "sha256": sha256_bytes(builder_log_path.read_bytes()),
            "printed_registration_id": m_reg.group(1) if m_reg else None,
            "printed_registration_sha256": m_reg.group(2) if m_reg else None,
            "printed_context_sha256": m_reg.group(3) if m_reg else None,
            "printed_sizing_filename": m_sz.group(1) if m_sz else None,
            "printed_sizing_sha256": m_sz.group(2) if m_sz else None,
            "printed_roster_path": m_rst.group(1) if m_rst else None,
            "printed_roster_sha256": m_rst.group(2) if m_rst else None,
            "registration_sha256_matches_disk": (m_reg.group(2) if m_reg else None)
            == new_artifacts["registration"]["actual_sha256"],
            "context_sha256_matches_registration_pin": (m_reg.group(3) if m_reg else None)
            == new_reg["inputs"]["context"]["sha256"],
            "sizing_sha256_matches_disk": (m_sz.group(2) if m_sz else None)
            == new_artifacts["sizing"]["actual_sha256"],
            "roster_sha256_matches_disk": (m_rst.group(2) if m_rst else None)
            == new_artifacts["roster"]["actual_sha256"],
            "exit_zero": "builder exit=0" in builder_text,
        },
        "check_log": {
            "path": str(check_log_path),
            "sha256": sha256_bytes(check_log_path.read_bytes()),
            "names_registration_and_sizing": (
                f"CHORUS: registration_chorus_{NEW_LABEL}.json (sized: registration_chorus_{NEW_LABEL}.sizing.json)"
                in check_text
            ),
            "names_roster_valid": f"Roster valid: roster_{NEW_LABEL}.json" in check_text,
            "all_checks_passed": "All checks passed." in check_text,
            "exit_zero": "check exit=0" in check_text,
        },
        "dryrun_log": {
            "path": str(dryrun_log_path),
            "sha256": sha256_bytes(dryrun_log_path.read_bytes()),
            "expect_sha256_matches_roster": f"expect-sha256={new_artifacts['roster']['actual_sha256']}"
            in dryrun_text,
            "head_before_is_merge_commit": f"HEAD {MERGE_COMMIT}" in dryrun_text,
            "dryrun_exit_zero": "dry-run exit=0" in dryrun_text,
            "rehash_all_three_ok": all(
                f"{new_artifacts[k]['path']}: OK" in dryrun_text
                for k in ("roster", "registration", "sizing")
            ),
        },
        "preflight_log": {
            "path": str(preflight_log_path),
            "sha256": sha256_bytes(preflight_log_path.read_bytes()),
            "moved_from_m4_to_merge_commit": (
                f"before: {M4_COMMIT}" in preflight_text
                and f"after:  {MERGE_COMMIT}" in preflight_text
            ),
            "prompts_check_exit_zero": "28 prompt file(s), 0 not at their pin\n  exit=0"
            in preflight_text,
            "schema_check_digest_exit_zero": "2 merged schema(s) built from current source.\n  exit=0"
            in preflight_text,
        },
        "sha256_manifest": {
            "path": str(sha256_file_path),
            "sha256": sha256_bytes(sha256_file_path.read_bytes()),
            "all_three_match_disk": all(
                sha256_lines.get(new_artifacts[k]["path"])
                == new_artifacts[k]["actual_sha256"]
                for k in ("roster", "registration", "sizing")
            ),
        },
        "cross_file_bindings": {
            "sizing_top_registration_path": new_sizing["registration_path"],
            "sizing_top_registration_path_matches": new_sizing["registration_path"]
            == new_artifacts["registration"]["path"],
            "sizing_top_registration_sha256": new_sizing["registration_sha256"],
            "sizing_top_registration_sha256_matches": new_sizing["registration_sha256"]
            == new_artifacts["registration"]["actual_sha256"],
            "sizing_inner_registration_sha256": new_sizing["sizing"]["registration_sha256"],
            "sizing_inner_registration_sha256_matches": new_sizing["sizing"][
                "registration_sha256"
            ]
            == new_artifacts["registration"]["actual_sha256"],
            "roster_row0_registration_path": new_roster["registrations"][0][
                "registration_path"
            ],
            "roster_row0_registration_path_matches": new_roster["registrations"][0][
                "registration_path"
            ]
            == new_artifacts["registration"]["path"],
            "roster_row0_registration_sha256": new_roster["registrations"][0][
                "registration_sha256"
            ],
            "roster_row0_registration_sha256_matches": new_roster["registrations"][0][
                "registration_sha256"
            ]
            == new_artifacts["registration"]["actual_sha256"],
        },
    }

    # Step 2: Every pinned repository file in new and M4 registration & sizing
    new_shape_pins = extract_shape_paired_pins(
        new_reg, "registration"
    ) + extract_shape_paired_pins(new_sizing, "sizing")
    old_shape_pins = extract_shape_paired_pins(
        old_reg, "registration"
    ) + extract_shape_paired_pins(old_sizing, "sizing")

    new_extra_pins = extract_non_shape_file_pins(
        new_reg, "registration"
    ) + extract_non_shape_file_pins(new_sizing, "sizing")
    old_extra_pins = extract_non_shape_file_pins(
        old_reg, "registration"
    ) + extract_non_shape_file_pins(old_sizing, "sizing")

    new_all_file_pins = new_shape_pins + new_extra_pins
    old_all_file_pins = old_shape_pins + old_extra_pins

    # Index old pins by (document, sha256_pointer)
    old_pin_by_ptr = {(p["document"], p["sha256_pointer"]): p for p in old_all_file_pins}
    new_pin_by_ptr = {(p["document"], p["sha256_pointer"]): p for p in new_all_file_pins}

    # Cache git show at MERGE_COMMIT and M4_COMMIT per repo_path
    git_cache_merge: dict[str, tuple[str | None, int | None]] = {}
    git_cache_m4: dict[str, tuple[str | None, int | None]] = {}

    all_repo_paths = sorted(
        {p["repo_path"] for p in new_all_file_pins}
        | {p["repo_path"] for p in old_all_file_pins}
    )
    for rp in all_repo_paths:
        raw_m = git_show_bytes(MERGE_COMMIT, rp)
        git_cache_merge[rp] = (
            (sha256_bytes(raw_m), len(raw_m)) if raw_m is not None else (None, None)
        )
        raw_o = git_show_bytes(M4_COMMIT, rp)
        git_cache_m4[rp] = (
            (sha256_bytes(raw_o), len(raw_o)) if raw_o is not None else (None, None)
        )

    pin_pointer_rows: list[dict[str, Any]] = []
    for p in new_all_file_pins:
        rp = p["repo_path"]
        merge_sha, merge_len = git_cache_merge[rp]
        m4_sha, m4_len = git_cache_m4[rp]
        old_p = old_pin_by_ptr.get((p["document"], p["sha256_pointer"]))
        old_pinned_sha = old_p["pinned_sha256"] if old_p else None
        old_pinned_bytes = old_p.get("pinned_bytes") if old_p else None
        pin_pointer_rows.append(
            {
                **p,
                "git_merge_sha256": merge_sha,
                "git_merge_bytes": merge_len,
                "git_m4_sha256": m4_sha,
                "git_m4_bytes": m4_len,
                "matches_git_at_merge": p["pinned_sha256"] == merge_sha,
                "bytes_match_git_at_merge": (
                    True
                    if p.get("pinned_bytes") is None
                    else p.get("pinned_bytes") == merge_len
                ),
                "old_m4_pinned_sha256": old_pinned_sha,
                "old_m4_pinned_bytes": old_pinned_bytes,
                "changed_from_m4": p["pinned_sha256"] != old_pinned_sha,
            }
        )

    # Unique paths summary (both for shape-paired 82 paths and all 86 file-backed paths)
    shape_unique_paths_new = sorted({p["repo_path"] for p in new_shape_pins})
    shape_unique_paths_old = sorted({p["repo_path"] for p in old_shape_pins})

    all_unique_paths_new = sorted({p["repo_path"] for p in new_all_file_pins})
    all_unique_paths_old = sorted({p["repo_path"] for p in old_all_file_pins})

    unique_path_rows: list[dict[str, Any]] = []
    for rp in all_unique_paths_new:
        ptrs = [r for r in pin_pointer_rows if r["repo_path"] == rp]
        new_shas = sorted({r["pinned_sha256"] for r in ptrs})
        old_shas = sorted({r["old_m4_pinned_sha256"] for r in ptrs if r["old_m4_pinned_sha256"]})
        assert len(new_shas) == 1
        assert len(old_shas) == 1
        merge_sha, merge_len = git_cache_merge[rp]
        m4_sha, m4_len = git_cache_m4[rp]
        unique_path_rows.append(
            {
                "repo_path": rp,
                "in_shape_paired_82": rp in shape_unique_paths_new,
                "pointer_count_in_new_packet": len(ptrs),
                "pointers": [f"{r['document']}#{r['sha256_pointer']}" for r in ptrs],
                "m4_pinned_sha256": old_shas[0],
                "new_pinned_sha256": new_shas[0],
                "git_m4_sha256": m4_sha,
                "git_merge_sha256": merge_sha,
                "git_m4_bytes": m4_len,
                "git_merge_bytes": merge_len,
                "m4_pin_matches_git_m4": old_shas[0] == m4_sha,
                "new_pin_matches_git_merge": new_shas[0] == merge_sha,
                "changed_from_m4": new_shas[0] != old_shas[0],
            }
        )

    changed_unique_paths = [r for r in unique_path_rows if r["changed_from_m4"]]
    unchanged_unique_paths = [r for r in unique_path_rows if not r["changed_from_m4"]]

    # Step 2 pointers covered (both sha256 and bytes pointers of changed pinned files)
    step2_covered_pointers: set[tuple[str, str]] = set()
    for r in pin_pointer_rows:
        if r["changed_from_m4"]:
            step2_covered_pointers.add((r["document"], r["sha256_pointer"]))
            if r.get("bytes_pointer") and r.get("pinned_bytes") != r.get("old_m4_pinned_bytes"):
                step2_covered_pointers.add((r["document"], r["bytes_pointer"]))

    # Step 3: Flatten all 3 documents (registration, sizing, roster) and compare every leaf
    docs_old = {
        "registration": flatten_leaves(old_reg),
        "sizing": flatten_leaves(old_sizing),
        "roster": flatten_leaves(old_roster),
    }
    docs_new = {
        "registration": flatten_leaves(new_reg),
        "sizing": flatten_leaves(new_sizing),
        "roster": flatten_leaves(new_roster),
    }

    # Look up exact line numbers in merge commit for code producers
    line_nums = {
        "build_api_registrations.py": find_line_numbers_in_commit(
            MERGE_COMMIT,
            "scripts/build_api_registrations.py",
            {
                "registration_id_fmt": r'registration_id = f"\{id_prefix\}-\{project\.lower\(\)\}-\{label\}"',
                "reg_dict_registration_id": r'"registration_id": registration_id,',
                "reg_dict_registration_path": r'"registration_path": str\(resolved_reg_path\),',
                "reg_dict_run_label": r'"label": label,',
                "reg_dict_full_schema": r'"full_schema": full_schema_pin,',
                "reg_dict_core_schema": r'"core_schema": core_schema_pin,',
                "reg_dict_bounded_carry": r'reg\["bounded_carry"\] = bc1_selection\.registration_block',
                "sidecar_dict": r'sidecar_bytes = sg\.canonical\(\{"format": SIZING_RECORD_FORMAT,',
                "roster_row_label": r'"label": label,',
                "roster_row_reg_path": r'"registration_path": resolved_path,',
                "roster_row_reg_sha256": r'"registration_sha256": reg_sha256,',
            },
        ),
        "bc1_context.py": find_line_numbers_in_commit(
            MERGE_COMMIT,
            "src/data_sheets_schema/bc1_context.py",
            {
                "FORMAT": r'^FORMAT = "bc1_neutral_term_policy_v2"',
                "TERM_SOURCE_FORMS_ANNOTATION": r'^TERM_SOURCE_FORMS_ANNOTATION = "d4d:termSourceIdentifierForms"',
                "contract_identity_def": r"^def contract_identity\(",
                "contract_v1_return": r'return \{"format": LEGACY_FORMAT,',
                "contract_v2_return": r'return \{"format": FORMAT,',
                "contract_v2_forms_annotation": r'"forms_annotation": TERM_SOURCE_FORMS_ANNOTATION,',
                "contract_v2_fallback": r'"fallback": \[\],',
                "parse_identifier_forms_def": r"^def _parse_identifier_forms\(",
                "sources_def": r"^def _sources\(",
                "derive_term_policy_def": r"^def derive_term_policy\(",
            },
        ),
        "bc1_context_m4.py": find_line_numbers_in_commit(
            M4_COMMIT,
            "src/data_sheets_schema/bc1_context.py",
            {
                "FORMAT_v1": r'^FORMAT = "bc1_neutral_term_policy_v1"',
                "FALLBACK_v1": r'^FALLBACK = \{\("Instance", "data_topic"\): \("GO", "MeSH", "EFO", "NCIT"\)\}',
                "IRI_v1": r'^_IRI = \{',
                "contract_identity_def_v1": r"^def contract_identity\(",
                "contract_v1_fallback": r'"fallback": \[\{"class": cls, "slot": slot,',
                "contract_v1_iri_prefixes": r'"iri_prefixes": \{name: list\(values\)',
            },
        ),
        "bc1_selection.py": find_line_numbers_in_commit(
            MERGE_COMMIT,
            "src/data_sheets_schema/bc1_selection.py",
            {
                "contract_identity_def": r"^def contract_identity\(",
                "context_call": r'"context": bc1_context\.contract_identity\(\),',
                "code_comp": r'"code": \{name: hashlib\.sha256\(resource_path\(name\)\.read_bytes\(\)\)\.hexdigest\(\)',
            },
        ),
        "bc1_registration.py": find_line_numbers_in_commit(
            MERGE_COMMIT,
            "src/data_sheets_schema/bc1_registration.py",
            {
                "registration_sha": r"registration_sha = hashlib\.sha256\(shared\.canonical\(registration\)\)\.hexdigest\(\)",
                "schema_text": r"schema_text = context\.schema_context\(captured,",
                "generation_context": r'"generation_context": context\.generation_context\(captured\)',
                "render_request": r"_, payload = runtime\.render_request\(",
                "wire_canonical": r"wire = shared\.canonical\(payload\)",
                "components_call": r"components = _components\(len\(wire\), floor, scenario, policy\)",
                "row_dict": r'row = \{"stage": deepcopy\(stage\), "scenario": scenario, "wire_bytes": len\(wire\),',
                "totals_dict": r'totals\[name\] = \{"calls": len\(chosen\), "wire_bytes": sum\(r\["wire_bytes"\]',
                "return_dict": r'return \{"format": FORMAT, "registration_sha256": registration_sha,',
                "captured_inputs": r'"captured_inputs": deepcopy\(inputs\),',
                "source_identity": r'"source_identity": selection\.contract_identity\(\)\}',
                "components_def": r"^def _components\(",
            },
        ),
    }

    def classify_non_step2_leaf(
        doc_name: str, ptr: str, change_type: str, old_val: Any, new_val: Any
    ) -> dict[str, Any]:
        bar_ln = line_nums["build_api_registrations.py"]
        ctx_ln = line_nums["bc1_context.py"]
        ctx_m4_ln = line_nums["bc1_context_m4.py"]
        sel_ln = line_nums["bc1_selection.py"]
        reg_ln = line_nums["bc1_registration.py"]

        # 1. Label / registration_id / registration_path
        if doc_name == "registration" and ptr == "/registration_id":
            return {
                "producer_at_merge": f"scripts/build_api_registrations.py:{bar_ln['registration_id_fmt']},{bar_ln['reg_dict_registration_id']}",
                "cause_category": "new_label",
                "cause_detail": "Derived from `f\"{id_prefix}-{project.lower()}-{label}\"` with new label `2026-11-11a_claude-opus-5-api-bc1-a21_rep1`.",
                "explained": True,
            }
        if doc_name == "registration" and ptr == "/registration_path":
            return {
                "producer_at_merge": f"scripts/build_api_registrations.py:{bar_ln['reg_dict_registration_path']}",
                "cause_category": "new_label",
                "cause_detail": "Output registration file path under `a21_registration_2026-11-11a_claude-opus-5-api-bc1-a21_rep1/`.",
                "explained": True,
            }
        if doc_name == "registration" and ptr == "/run/label":
            return {
                "producer_at_merge": f"scripts/build_api_registrations.py:{bar_ln['reg_dict_run_label']}",
                "cause_category": "new_label",
                "cause_detail": "CLI `--label 2026-11-11a_claude-opus-5-api-bc1-a21_rep1`.",
                "explained": True,
            }
        if doc_name == "sizing" and ptr == "/registration_path":
            return {
                "producer_at_merge": f"scripts/build_api_registrations.py:{bar_ln['sidecar_dict']}",
                "cause_category": "new_label",
                "cause_detail": "Sidecar binding to the new registration file path.",
                "explained": True,
            }
        if doc_name == "sizing" and ptr in ("/registration_sha256", "/sizing/registration_sha256"):
            prod = (
                f"scripts/build_api_registrations.py:{bar_ln['sidecar_dict']}"
                if ptr == "/registration_sha256"
                else f"src/data_sheets_schema/bc1_registration.py:{reg_ln['registration_sha']},{reg_ln['return_dict']}"
            )
            return {
                "producer_at_merge": prod,
                "cause_category": "six_moved_files_and_new_label",
                "cause_detail": "SHA-256 of canonical `registration_chorus_2026-11-11a_claude-opus-5-api-bc1-a21_rep1.json` bytes.",
                "explained": True,
            }
        if doc_name == "roster" and ptr == "/registrations/0/label":
            return {
                "producer_at_merge": f"scripts/build_api_registrations.py:{bar_ln['roster_row_label']}",
                "cause_category": "new_label",
                "cause_detail": "Roster row label copied from `reg['run']['label']`.",
                "explained": True,
            }
        if doc_name == "roster" and ptr == "/registrations/0/registration_path":
            return {
                "producer_at_merge": f"scripts/build_api_registrations.py:{bar_ln['roster_row_reg_path']}",
                "cause_category": "new_label",
                "cause_detail": "Roster row `registration_path` copied from `reg['registration_path']`.",
                "explained": True,
            }
        if doc_name == "roster" and ptr == "/registrations/0/registration_sha256":
            return {
                "producer_at_merge": f"scripts/build_api_registrations.py:{bar_ln['roster_row_reg_sha256']}",
                "cause_category": "six_moved_files_and_new_label",
                "cause_detail": "Roster row `registration_sha256` hashing canonical `registration_chorus_2026-11-11a_claude-opus-5-api-bc1-a21_rep1.json` bytes.",
                "explained": True,
            }

        # 2. Context block changes (bc1_context.py)
        if ptr.startswith("/bounded_carry/contract/context/") or ptr.startswith(
            "/sizing/source_identity/context/"
        ):
            sub = ptr.split("/context/", 1)[1]
            if sub == "format":
                return {
                    "producer_at_merge": f"src/data_sheets_schema/bc1_context.py:{ctx_ln['FORMAT']},{ctx_ln['contract_v2_return']} (via bc1_selection.py:{sel_ln['context_call']})",
                    "cause_category": "moved_file:bc1_context.py",
                    "cause_detail": "`bc1_context.contract_identity()` format bumped from `bc1_neutral_term_policy_v1` to `bc1_neutral_term_policy_v2` (#5471 / PR #5531).",
                    "explained": True,
                }
            if sub == "forms_annotation" and change_type == "added":
                return {
                    "producer_at_merge": f"src/data_sheets_schema/bc1_context.py:{ctx_ln['TERM_SOURCE_FORMS_ANNOTATION']},{ctx_ln['contract_v2_forms_annotation']}",
                    "cause_category": "moved_file:bc1_context.py",
                    "cause_detail": "Added `forms_annotation: \"d4d:termSourceIdentifierForms\"` in `bc1_neutral_term_policy_v2` (#5471 / PR #5531).",
                    "explained": True,
                }
            if sub == "fallback" and change_type == "added":
                return {
                    "producer_at_merge": f"src/data_sheets_schema/bc1_context.py:{ctx_ln['contract_v2_fallback']}",
                    "cause_category": "moved_file:bc1_context.py",
                    "cause_detail": "`fallback` is now the empty list `[]` leaf in `bc1_neutral_term_policy_v2` because `Instance.data_topic` carries explicit schema annotations in `data_sheets_schema_all.yaml`.",
                    "explained": True,
                }
            if (sub.startswith("fallback/0/") or sub.startswith("iri_prefixes/")) and change_type == "removed":
                return {
                    "producer_at_merge": f"src/data_sheets_schema/bc1_context.py:{ctx_ln['contract_v2_return']}-{ctx_ln['contract_v2_fallback']} (removed v1 keys from M4 bc1_context.py:{ctx_m4_ln['contract_v1_fallback']}-{ctx_m4_ln['contract_v1_iri_prefixes']})",
                    "cause_category": "moved_file:bc1_context.py",
                    "cause_detail": "Removed hardcoded v1 `fallback[0]` (`Instance.data_topic`) and `iri_prefixes` (`EFO`, `GO`, `MeSH`, `NCIT`) from `contract_identity(version=2)`; identifier forms now come from `d4d:termSourceIdentifierForms` in `data_sheets_schema_all.yaml`.",
                    "explained": True,
                }

        # 3. Sizing rows and own_plan_scenarios
        if doc_name == "sizing" and re.match(
            r"^/sizing/rows/\d+/(request_bytes|wire_bytes|planning_wire_bytes|estimated_input_tokens|estimated_context_tokens|wire_sha256)$",
            ptr,
        ):
            field = ptr.rsplit("/", 1)[1]
            return {
                "producer_at_merge": f"src/data_sheets_schema/bc1_registration.py:{reg_ln['schema_text']},{reg_ln['generation_context']},{reg_ln['render_request']}-{reg_ln['row_dict']},{reg_ln['components_def']}",
                "cause_category": "six_moved_files_and_new_label",
                "cause_detail": f"Rendered stage request `{field}` updated because `schema_context` and `generation_context` embed the updated 3.2.1 schema (`data_sheets_schema_all.yaml` / `data_sheets_schema_core_all.yaml`) and `bc1_neutral_term_policy_v2` (`bc1_context.py`), and `common['registration_sha256']` embeds the new registration digest.",
                "explained": True,
            }
        if doc_name == "sizing" and re.match(
            r"^/sizing/own_plan_scenarios/[^/]+/(wire_bytes|estimated_input_tokens)$",
            ptr,
        ):
            field = ptr.rsplit("/", 1)[1]
            return {
                "producer_at_merge": f"src/data_sheets_schema/bc1_registration.py:{reg_ln['totals_dict']}",
                "cause_category": "six_moved_files_and_new_label",
                "cause_detail": f"Scenario aggregate `{field}` summed over the 4 fixed rows (`worker_0001..0003` + `omission`) plus the 3 integration rows (`group-0001`, `group-0002`, `final`) for that scenario.",
                "explained": True,
            }

        return {
            "producer_at_merge": "UNEXPLAINED",
            "cause_category": "unexplained",
            "cause_detail": "No traced producer.",
            "explained": False,
        }

    all_leaf_diffs: list[dict[str, Any]] = []
    step3_non_step2_diffs: list[dict[str, Any]] = []
    step2_leaf_diffs: list[dict[str, Any]] = []

    for doc_name in ("registration", "sizing", "roster"):
        old_map = docs_old[doc_name]
        new_map = docs_new[doc_name]
        all_ptrs = sorted(set(old_map) | set(new_map))
        for ptr in all_ptrs:
            in_old = ptr in old_map
            in_new = ptr in new_map
            old_val = old_map.get(ptr)
            new_val = new_map.get(ptr)
            if in_old and in_new and old_val == new_val:
                continue
            change_type = (
                "changed"
                if (in_old and in_new)
                else ("added" if in_new else "removed")
            )
            covered_by_step2 = (doc_name, ptr) in step2_covered_pointers
            entry: dict[str, Any] = {
                "document": doc_name,
                "json_pointer": ptr,
                "change_type": change_type,
                "old_value": old_val,
                "new_value": new_val,
                "covered_by_step2": covered_by_step2,
            }
            if not covered_by_step2:
                entry.update(
                    classify_non_step2_leaf(doc_name, ptr, change_type, old_val, new_val)
                )
                step3_non_step2_diffs.append(entry)
            else:
                step2_leaf_diffs.append(entry)
            all_leaf_diffs.append(entry)

    unexplained_diffs = [d for d in step3_non_step2_diffs if not d["explained"]]

    # Step 4: Context block analysis and schema slots carrying d4d:termSources and d4d:termSourceIdentifierForms
    full_schema_annotations = find_term_source_slots_in_schema(
        MERGE_COMMIT, "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
    )
    core_schema_annotations = find_term_source_slots_in_schema(
        MERGE_COMMIT, "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"
    )

    context_block_comparison = {
        "m4_context_block": old_reg["bounded_carry"]["contract"]["context"],
        "new_context_block": new_reg["bounded_carry"]["contract"]["context"],
        "sizing_mirrors_registration_context_exactly": (
            new_sizing["sizing"]["source_identity"]["context"]
            == new_reg["bounded_carry"]["contract"]["context"]
        ),
        "bc1_context_m4_lines": line_nums["bc1_context_m4.py"],
        "bc1_context_merge_lines": line_nums["bc1_context.py"],
        "full_schema_term_source_annotations": full_schema_annotations,
        "core_schema_term_source_annotations": core_schema_annotations,
    }

    # Step 5: Sizing rows and scenario totals
    sizing_row_deltas: list[dict[str, Any]] = []
    for idx, (old_row, new_row) in enumerate(
        zip(old_sizing["sizing"]["rows"], new_sizing["sizing"]["rows"])
    ):
        assert old_row["stage"] == new_row["stage"]
        assert old_row["scenario"] == new_row["scenario"]
        stage = new_row["stage"]
        stage_label = stage["phase"]
        if "worker_id" in stage:
            stage_label += f" ({stage['worker_id']})"
        elif "stage_id" in stage:
            w_str = ",".join(stage.get("worker_ids", []))
            stage_label += f" ({stage['stage_id']}: [{w_str}])"

        context_limit = new_reg["audit_limits"]["context_limit_tokens"]
        max_input_per_call = new_reg["audit_limits"]["max_input_tokens_per_call"]
        out_reserve = new_row["output_token_reserve"]
        effective_input_ceiling = min(max_input_per_call, context_limit - out_reserve)

        sizing_row_deltas.append(
            {
                "row_index": idx,
                "stage": stage,
                "stage_label": stage_label,
                "scenario": new_row["scenario"],
                "old_request_bytes": old_row["request_bytes"],
                "new_request_bytes": new_row["request_bytes"],
                "delta_request_bytes": new_row["request_bytes"] - old_row["request_bytes"],
                "old_wire_bytes": old_row["wire_bytes"],
                "new_wire_bytes": new_row["wire_bytes"],
                "delta_wire_bytes": new_row["wire_bytes"] - old_row["wire_bytes"],
                "old_planning_wire_bytes": old_row["planning_wire_bytes"],
                "new_planning_wire_bytes": new_row["planning_wire_bytes"],
                "delta_planning_wire_bytes": new_row["planning_wire_bytes"]
                - old_row["planning_wire_bytes"],
                "future_wire_bytes": new_row["future_wire_bytes"],
                "planning_future_wire_bytes": new_row["planning_future_wire_bytes"],
                "old_estimated_input_tokens": old_row["estimated_input_tokens"],
                "new_estimated_input_tokens": new_row["estimated_input_tokens"],
                "delta_estimated_input_tokens": new_row["estimated_input_tokens"]
                - old_row["estimated_input_tokens"],
                "output_token_reserve": out_reserve,
                "old_estimated_context_tokens": old_row["estimated_context_tokens"],
                "new_estimated_context_tokens": new_row["estimated_context_tokens"],
                "delta_estimated_context_tokens": new_row["estimated_context_tokens"]
                - old_row["estimated_context_tokens"],
                "effective_input_token_ceiling": effective_input_ceiling,
                "input_token_headroom": effective_input_ceiling
                - new_row["estimated_input_tokens"],
                "context_token_headroom": context_limit
                - new_row["estimated_context_tokens"],
                "old_wire_sha256": old_row["wire_sha256"],
                "new_wire_sha256": new_row["wire_sha256"],
                "old_estimated_context_fits": old_row["estimated_context_fits"],
                "new_estimated_context_fits": new_row["estimated_context_fits"],
                "estimated_context_fits_changed": old_row["estimated_context_fits"]
                != new_row["estimated_context_fits"],
                "old_gated": old_row["gated"],
                "new_gated": new_row["gated"],
                "gated_changed": old_row["gated"] != new_row["gated"],
            }
        )

    scenario_deltas: list[dict[str, Any]] = []
    agg_limit = new_reg["audit_limits"]["aggregate_input_tokens"]
    for scen_name in (
        "empty_future_floor",
        "visible_cap_ascii_scenario",
        "visible_cap_measured_escape",
        "visible_cap_escaped_bound",
    ):
        old_s = old_sizing["sizing"]["own_plan_scenarios"][scen_name]
        new_s = new_sizing["sizing"]["own_plan_scenarios"][scen_name]
        scenario_deltas.append(
            {
                "scenario": scen_name,
                "gated_scenario": scen_name
                in new_sizing["sizing"]["calibration"]["gated_scenarios"],
                "calls": new_s["calls"],
                "old_wire_bytes": old_s["wire_bytes"],
                "new_wire_bytes": new_s["wire_bytes"],
                "delta_wire_bytes": new_s["wire_bytes"] - old_s["wire_bytes"],
                "old_estimated_input_tokens": old_s["estimated_input_tokens"],
                "new_estimated_input_tokens": new_s["estimated_input_tokens"],
                "delta_estimated_input_tokens": new_s["estimated_input_tokens"]
                - old_s["estimated_input_tokens"],
                "aggregate_input_tokens_limit": agg_limit,
                "aggregate_input_tokens_headroom": agg_limit
                - new_s["estimated_input_tokens"],
                "aggregate_input_tokens_pct_of_limit": round(
                    100.0 * new_s["estimated_input_tokens"] / agg_limit, 4
                ),
                "output_token_reservations": new_s["output_token_reservations"],
                "old_estimated_all_calls_fit": old_s["estimated_all_calls_fit"],
                "new_estimated_all_calls_fit": new_s["estimated_all_calls_fit"],
                "estimated_all_calls_fit_changed": old_s["estimated_all_calls_fit"]
                != new_s["estimated_all_calls_fit"],
            }
        )

    gated_rows = [r for r in sizing_row_deltas if r["new_gated"]]
    largest_gated_row = max(gated_rows, key=lambda r: r["new_estimated_context_tokens"])
    largest_overall_row = max(
        sizing_row_deltas, key=lambda r: r["new_estimated_context_tokens"]
    )

    result = {
        "schema": "agy2_a21_rebuild_identity_review_v1",
        "verdict": {
            "unexplained_differences_count": len(unexplained_diffs),
            "all_differences_explained_by_six_moved_files_or_new_label": len(
                unexplained_diffs
            )
            == 0,
            "preview_tree_equals_merge_tree": preview_tree == merge_tree,
            "preview_tree": preview_tree,
            "merge_tree": merge_tree,
            "changed_pinned_files_count": len(changed_unique_paths),
            "added_pinned_paths_count": len(
                set(all_unique_paths_new) - set(all_unique_paths_old)
            ),
            "dropped_pinned_paths_count": len(
                set(all_unique_paths_old) - set(all_unique_paths_new)
            ),
            "any_estimated_context_fits_changed": any(
                r["estimated_context_fits_changed"] for r in sizing_row_deltas
            ),
            "any_gated_changed": any(r["gated_changed"] for r in sizing_row_deltas),
        },
        "commits": {
            "m4_base": M4_COMMIT,
            "main_before_merge": MAIN_BEFORE_MERGE,
            "pr5808_head": PR5808_HEAD,
            "preview_commit": PREVIEW_COMMIT,
            "merge_commit": MERGE_COMMIT,
        },
        "step1_hashes_and_logs": {
            "new_artifacts": new_artifacts,
            "old_artifacts": old_artifacts,
            "log_verification": log_verification,
        },
        "step2_pinned_files": {
            "counts": {
                "shape_paired_pin_pointers_total": len(new_shape_pins),
                "shape_paired_pin_pointers_equal_merge": sum(
                    1
                    for r in pin_pointer_rows
                    if r["pin_kind"] in ("path_and_sha256_object", "path_keyed_sha256_map")
                    and r["matches_git_at_merge"]
                ),
                "shape_paired_pin_pointers_unequal_merge": sum(
                    1
                    for r in pin_pointer_rows
                    if r["pin_kind"] in ("path_and_sha256_object", "path_keyed_sha256_map")
                    and not r["matches_git_at_merge"]
                ),
                "shape_paired_unique_paths": len(shape_unique_paths_new),
                "all_file_backed_pin_pointers_total": len(pin_pointer_rows),
                "all_file_backed_pin_pointers_equal_merge": sum(
                    1 for r in pin_pointer_rows if r["matches_git_at_merge"]
                ),
                "all_file_backed_pin_pointers_unequal_merge": sum(
                    1 for r in pin_pointer_rows if not r["matches_git_at_merge"]
                ),
                "all_file_backed_unique_paths": len(all_unique_paths_new),
                "changed_unique_paths_from_m4": len(changed_unique_paths),
                "unchanged_unique_paths_from_m4": len(unchanged_unique_paths),
                "added_unique_paths_vs_m4": sorted(
                    set(all_unique_paths_new) - set(all_unique_paths_old)
                ),
                "dropped_unique_paths_vs_m4": sorted(
                    set(all_unique_paths_old) - set(all_unique_paths_new)
                ),
            },
            "changed_unique_paths": changed_unique_paths,
            "unchanged_unique_paths": unchanged_unique_paths,
            "all_pin_pointer_rows": pin_pointer_rows,
        },
        "step3_leaf_diffs": {
            "counts": {
                "registration_leaves_old": len(docs_old["registration"]),
                "registration_leaves_new": len(docs_new["registration"]),
                "sizing_leaves_old": len(docs_old["sizing"]),
                "sizing_leaves_new": len(docs_new["sizing"]),
                "roster_leaves_old": len(docs_old["roster"]),
                "roster_leaves_new": len(docs_new["roster"]),
                "total_leaf_diffs_across_all_three": len(all_leaf_diffs),
                "step2_covered_leaf_diffs_count": len(step2_leaf_diffs),
                "step3_other_leaf_diffs_count": len(step3_non_step2_diffs),
                "step3_other_changed_count": sum(
                    1 for d in step3_non_step2_diffs if d["change_type"] == "changed"
                ),
                "step3_other_added_count": sum(
                    1 for d in step3_non_step2_diffs if d["change_type"] == "added"
                ),
                "step3_other_removed_count": sum(
                    1 for d in step3_non_step2_diffs if d["change_type"] == "removed"
                ),
                "unexplained_leaf_diffs_count": len(unexplained_diffs),
            },
            "step2_covered_leaf_diffs": step2_leaf_diffs,
            "step3_other_leaf_diffs": step3_non_step2_diffs,
            "unexplained_leaf_diffs": unexplained_diffs,
        },
        "step4_context_block": context_block_comparison,
        "step5_sizing_rows": {
            "audit_limits": new_reg["audit_limits"],
            "largest_gated_call": largest_gated_row,
            "largest_overall_call": largest_overall_row,
            "any_estimated_context_fits_changed": any(
                r["estimated_context_fits_changed"] for r in sizing_row_deltas
            ),
            "any_gated_changed": any(r["gated_changed"] for r in sizing_row_deltas),
            "rows": sizing_row_deltas,
            "own_plan_scenarios": scenario_deltas,
        },
    }

    OUT_JSON.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"SHA-256: {sha256_bytes(OUT_JSON.read_bytes())}")
    print(f"Unexplained differences: {len(unexplained_diffs)}")


if __name__ == "__main__":
    main()
