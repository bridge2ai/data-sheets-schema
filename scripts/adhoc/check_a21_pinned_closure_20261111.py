#!/usr/bin/env python3
"""Mechanically verify the M4 A21 registration pinned closure against merge preview 44b8a6595.

Purpose:
  Enumerate every SHA-256 pin (with its RFC 6901 JSON pointer) in the M4 CHORUS
  A21 registration (`registration_chorus_2026-11-05a_claude-opus-5-api-bc1-a21_rep1.json`)
  and its companion roster and sizing sidecar. Compare each pinned repository
  path against `git show 44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9:<path>` in the
  primary repository (and against disk for launch-base / untracked inputs outside
  git), identify every moved vs. unchanged item and every non-file computed hash,
  record `git log --oneline 673838c51..44b8a6595 -- <path>` for moved files, and
  check AGY3's Section 2 runbook claims against the byte-level results.

Inputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_2026-11-05a_claude-opus-5-api-bc1-a21_rep1/registration_chorus_2026-11-05a_claude-opus-5-api-bc1-a21_rep1.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_2026-11-05a_claude-opus-5-api-bc1-a21_rep1/registration_chorus_2026-11-05a_claude-opus-5-api-bc1-a21_rep1.sizing.json
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_2026-11-05a_claude-opus-5-api-bc1-a21_rep1/roster_2026-11-05a_claude-opus-5-api-bc1-a21_rep1.json
  - Primary git repository: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema
    (commits 673838c51547278cfd79254670ec95421c7bcaf7 and 44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9)
  - Launch-base data directory: /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21

Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/tmp/a21-pinned-closure-20261111/a21_pinned_closure_check.json

Serves:
  Claude lead assignment `claude-lead-agy2-a21-pinned-closure-check.md` (final-generation track),
  Date: 2026-11-11.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

PRIMARY_REPO = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema")
LAUNCH_BASE = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21")
PREVIEW_WORKTREE = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/claude-pr5808-combined-20261111"
)
REPORT_WORKTREE = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111"
)
M4_PLAN_DIR = Path(
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/"
    "a21_registration_2026-11-05a_claude-opus-5-api-bc1-a21_rep1"
)
REGISTRATION_PATH = M4_PLAN_DIR / "registration_chorus_2026-11-05a_claude-opus-5-api-bc1-a21_rep1.json"
SIZING_PATH = M4_PLAN_DIR / "registration_chorus_2026-11-05a_claude-opus-5-api-bc1-a21_rep1.sizing.json"
ROSTER_PATH = M4_PLAN_DIR / "roster_2026-11-05a_claude-opus-5-api-bc1-a21_rep1.json"

M4_COMMIT = "673838c51547278cfd79254670ec95421c7bcaf7"
PREVIEW_COMMIT = "44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9"
MAIN_COMMIT = "925d726d67cdd03fe28fdeafdde60fa27df57205"
PR5808_COMMIT = "6792947ea6558d10c85106065b023cb57838835a"

OUT_DIR = REPORT_WORKTREE / "tmp" / "a21-pinned-closure-20261111"
OUT_JSON = OUT_DIR / "a21_pinned_closure_check.json"

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

AGY3_CLAIMED_MOVED = {
    "src/data_sheets_schema/schema/data_sheets_schema_all.yaml": (
        "9a821e6a08e8fe8c6b0e2fd1d4bef9e5d4ee3740722b81ab7620c315287bc8da",
        "bc560a3cd5d04c49e95fcbf33fa8ac349171df1a877e7e0882827bd526a95214",
    ),
    "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml": (
        "2bb8827c45a4dac40e834064a65c95cfc13d258b129c3aa1b9cbccba9ef624db",
        "e174a7a6ec1b5eccef5ee4a8b9f8f773f48243c2d6012ff8a1b846b45a40d088",
    ),
    "src/data_sheets_schema/api_runner.py": (
        "365a6431eb869c76d7d06dde7698ce9ce91414a0a2f6c1ad11e60f3a84113930",
        "23dcc828d171000173bd521edfbc55b38bfcf6c0adb41c6b962c10f381e911bb",
    ),
    "src/data_sheets_schema/schema_digest.py": (
        "150a5f005ab1ed5fdf73f927559f15a3c7dbf34a0915ff2b83896991c1fcc095",
        "c30d59fe48ee9bed78bd24bc89366e926e88dbefeba228ff132335066c0af54c",
    ),
    "src/data_sheets_schema/bc1_audit.py": (
        "0e43a00224aa994b765ebc22746a92d044e864ea241f93bcffb8fa2a6b77b572",
        "dbcf87a804dbc486fc76702ff643838c5713ab7129c585d6a7f0a6ec442a9fd7",
    ),
    "src/data_sheets_schema/bc1_context.py": (
        "a3ec22914277e643a125b40711c10f5a7a58e1575a7ec61986bd86dd42ed465e",
        "1e4877b555cae75449883be925713b12f9507c804a0604906a8221d566ae8378",
    ),
}


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def _escape_ptr(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git_show(commit: str, repo_path: str) -> tuple[bool, str | None, int | None]:
    proc = subprocess.run(
        ["git", "-C", str(PRIMARY_REPO), "show", f"{commit}:{repo_path}"],
        capture_output=True,
        env=_git_env(),
    )
    if proc.returncode != 0:
        return False, None, None
    raw = proc.stdout
    return True, _sha256_bytes(raw), len(raw)


def _git_log_oneline(start_commit: str, end_commit: str, repo_path: str) -> list[dict[str, Any]]:
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(PRIMARY_REPO),
            "log",
            "--oneline",
            f"{start_commit}..{end_commit}",
            "--",
            repo_path,
        ],
        capture_output=True,
        text=True,
        check=True,
        env=_git_env(),
    )
    rows = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        sha_short, _, subject = line.partition(" ")
        prs = re.findall(r"#(\d+)", subject)
        rows.append({"commit": sha_short, "subject": subject, "prs_in_subject": [f"#{p}" for p in prs]})
    return rows


def _collect_all_hex64_leaves(obj: Any, prefix: str = "") -> dict[str, str]:
    found: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            ptr = f"{prefix}/{_escape_ptr(str(k))}"
            found.update(_collect_all_hex64_leaves(v, ptr))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            ptr = f"{prefix}/{idx}"
            found.update(_collect_all_hex64_leaves(v, ptr))
    elif isinstance(obj, str) and HEX64_RE.match(obj):
        found[prefix] = obj
    return found


def _normalize_repo_rel(path_str: str) -> tuple[str, Path | None]:
    p = Path(path_str)
    prefix = str(LAUNCH_BASE) + "/"
    if path_str.startswith(prefix):
        return path_str[len(prefix) :], p
    return path_str, LAUNCH_BASE / path_str


def _check_path_target(
    repo_rel: str,
    disk_candidates: list[Path],
    m4_sha256: str,
    m4_bytes: int | None = None,
) -> dict[str, Any]:
    in_git_m4, git_m4_sha, git_m4_bytes = _git_show(M4_COMMIT, repo_rel)
    in_git_prev, git_prev_sha, git_prev_bytes = _git_show(PREVIEW_COMMIT, repo_rel)
    in_git_main, git_main_sha, _ = _git_show(MAIN_COMMIT, repo_rel)

    disk_used: Path | None = None
    disk_sha: str | None = None
    disk_bytes: int | None = None
    for cand in disk_candidates:
        if cand is not None and cand.is_file():
            raw = cand.read_bytes()
            disk_used = cand
            disk_sha = _sha256_bytes(raw)
            disk_bytes = len(raw)
            break

    if in_git_prev:
        source_mode = "git_show"
        preview_sha = git_prev_sha
        preview_bytes = git_prev_bytes
    elif disk_used is not None:
        source_mode = "disk_outside_git"
        preview_sha = disk_sha
        preview_bytes = disk_bytes
    else:
        source_mode = "missing_in_git_and_disk"
        preview_sha = None
        preview_bytes = None

    status = (
        "unchanged"
        if preview_sha == m4_sha256
        else ("moved" if preview_sha is not None else "missing_path")
    )
    log_entries = _git_log_oneline(M4_COMMIT, PREVIEW_COMMIT, repo_rel) if in_git_prev and status == "moved" else []

    return {
        "repo_path": repo_rel,
        "source_mode": source_mode,
        "in_git_at_m4": in_git_m4,
        "git_m4_sha256": git_m4_sha,
        "git_m4_bytes": git_m4_bytes,
        "in_git_at_preview": in_git_prev,
        "git_preview_sha256": git_prev_sha,
        "git_preview_bytes": git_prev_bytes,
        "git_main_925d726d_sha256": git_main_sha if in_git_main else None,
        "disk_path": str(disk_used) if disk_used else None,
        "disk_sha256": disk_sha,
        "disk_bytes": disk_bytes,
        "m4_pinned_sha256": m4_sha256,
        "m4_pinned_bytes": m4_bytes,
        "preview_effective_sha256": preview_sha,
        "preview_effective_bytes": preview_bytes,
        "status": status,
        "git_log_m4_to_preview": log_entries,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    reg_raw = REGISTRATION_PATH.read_bytes()
    sizing_raw = SIZING_PATH.read_bytes()
    roster_raw = ROSTER_PATH.read_bytes()

    reg = json.loads(reg_raw)
    sizing = json.loads(sizing_raw)
    roster = json.loads(roster_raw)

    reg_all_leaves = _collect_all_hex64_leaves(reg)
    sizing_all_leaves = _collect_all_hex64_leaves(sizing)
    roster_all_leaves = _collect_all_hex64_leaves(roster)

    pointer_records: list[dict[str, Any]] = []
    handled_reg_pointers: set[str] = set()

    def add_file_pin(
        doc_name: str,
        pointer: str,
        category: str,
        repo_rel: str,
        m4_sha: str,
        disk_candidates: list[Path],
        m4_bytes: int | None = None,
        note: str | None = None,
    ) -> None:
        if doc_name == "registration":
            handled_reg_pointers.add(pointer)
        target_info = _check_path_target(repo_rel, disk_candidates, m4_sha, m4_bytes)
        rec = {
            "document": doc_name,
            "json_pointer": pointer,
            "category": category,
            **target_info,
        }
        if note:
            rec["note"] = note
        pointer_records.append(rec)

    # 1. inputs.* in registration
    for key in ("bundle", "chunk_manifest", "context", "source_manifest"):
        pin = reg["inputs"][key]
        repo_rel, disk_p = _normalize_repo_rel(pin["path"])
        add_file_pin(
            "registration",
            f"/inputs/{key}/sha256",
            "inputs",
            repo_rel,
            pin["sha256"],
            [disk_p, PRIMARY_REPO / repo_rel],
            pin.get("bytes"),
        )

    for schema_key in ("core_schema", "full_schema"):
        for idx, pin in enumerate(reg["inputs"][schema_key]["sources"]):
            repo_rel, disk_p = _normalize_repo_rel(pin["path"])
            add_file_pin(
                "registration",
                f"/inputs/{schema_key}/sources/{idx}/sha256",
                "inputs.schema",
                repo_rel,
                pin["sha256"],
                [disk_p, PRIMARY_REPO / repo_rel],
                pin.get("bytes"),
            )

    vocab_pin = reg["inputs"]["profile"]["vocabulary"]
    repo_rel, disk_p = _normalize_repo_rel(vocab_pin["path"])
    add_file_pin(
        "registration",
        "/inputs/profile/vocabulary/sha256",
        "inputs.profile.vocabulary",
        repo_rel,
        vocab_pin["sha256"],
        [disk_p, PRIMARY_REPO / repo_rel],
        vocab_pin.get("bytes"),
    )

    # Also record the 12-char embedded sha256 prefix in /inputs/profile/basis
    basis_str = reg["inputs"]["profile"]["basis"]
    basis_path, _, basis_prefix = basis_str.removeprefix("manifest:").partition("@")
    sm_check = _check_path_target(
        basis_path,
        [LAUNCH_BASE / basis_path, PRIMARY_REPO / basis_path],
        reg["inputs"]["source_manifest"]["sha256"],
        reg["inputs"]["source_manifest"]["bytes"],
    )
    pointer_records.append(
        {
            "document": "registration",
            "json_pointer": "/inputs/profile/basis",
            "category": "inputs.profile.basis_prefix",
            "repo_path": basis_path,
            "source_mode": sm_check["source_mode"],
            "m4_pinned_sha256_prefix": basis_prefix,
            "preview_effective_sha256_prefix": (
                sm_check["preview_effective_sha256"][:12] if sm_check["preview_effective_sha256"] else None
            ),
            "status": (
                "unchanged"
                if sm_check["preview_effective_sha256"]
                and sm_check["preview_effective_sha256"].startswith(basis_prefix)
                else "moved"
            ),
            "disk_path": sm_check["disk_path"],
            "note": "12-hex-char SHA-256 prefix embedded in profile.basis string.",
        }
    )

    # 2. runtime.config
    rt_pin = reg["runtime"]["config"]
    repo_rel, disk_p = _normalize_repo_rel(rt_pin["path"])
    add_file_pin(
        "registration",
        "/runtime/config/sha256",
        "runtime.config",
        repo_rel,
        rt_pin["sha256"],
        [disk_p, PRIMARY_REPO / repo_rel],
        rt_pin.get("bytes"),
    )

    # 3. receipt.runtime_policy_sha256 (hashes src/download/prompts/receipt_completion_runtime_v2.md)
    add_file_pin(
        "registration",
        "/receipt/runtime_policy_sha256",
        "receipt.runtime_policy_sha256",
        "src/download/prompts/receipt_completion_runtime_v2.md",
        reg["receipt"]["runtime_policy_sha256"],
        [PRIMARY_REPO / "src/download/prompts/receipt_completion_runtime_v2.md"],
        note="Pinned via receipt_completion_policy.RUNTIME_POLICY_PATH = src/download/prompts/receipt_completion_runtime_v2.md.",
    )

    # 4. selection.assets (9 prompt/command assets)
    for asset_rel, asset_sha in sorted(reg["selection"]["assets"].items()):
        ptr = f"/selection/assets/{_escape_ptr(asset_rel)}"
        add_file_pin(
            "registration",
            ptr,
            "selection.assets",
            asset_rel,
            asset_sha,
            [PRIMARY_REPO / asset_rel],
        )

    # 5. selection.stage_contracts.evidence_protocol_sha256 & omission_assets_sha256
    add_file_pin(
        "registration",
        "/selection/stage_contracts/evidence_protocol_sha256",
        "selection.stage_contracts.file_hash",
        "src/download/prompts/evidence_protocol_v7.md",
        reg["selection"]["stage_contracts"]["evidence_protocol_sha256"],
        [PRIMARY_REPO / "src/download/prompts/evidence_protocol_v7.md"],
        note="shared_generation.py:177 hashes src/download/prompts/evidence_protocol_v7.md for renderer 25.",
    )

    for om_name, om_sha in sorted(reg["selection"]["stage_contracts"]["omission_assets_sha256"].items()):
        om_rel = f"src/data_sheets_schema/omission_inventory_v1/{om_name}"
        ptr = f"/selection/stage_contracts/omission_assets_sha256/{_escape_ptr(om_name)}"
        add_file_pin(
            "registration",
            ptr,
            "selection.stage_contracts.omission_assets_sha256",
            om_rel,
            om_sha,
            [PRIMARY_REPO / om_rel],
        )

    # 6. bounded_carry.contract.audit.omission_contract_sha256
    for om_name, om_sha in sorted(reg["bounded_carry"]["contract"]["audit"]["omission_contract_sha256"].items()):
        om_rel = f"src/data_sheets_schema/omission_inventory_v1/{om_name}"
        ptr = f"/bounded_carry/contract/audit/omission_contract_sha256/{_escape_ptr(om_name)}"
        add_file_pin(
            "registration",
            ptr,
            "bounded_carry.contract.audit.omission_contract_sha256",
            om_rel,
            om_sha,
            [PRIMARY_REPO / om_rel],
        )

    # 7. selection.stage_contracts.request_code_sha256 (53 Python files)
    for code_rel, code_sha in sorted(reg["selection"]["stage_contracts"]["request_code_sha256"].items()):
        ptr = f"/selection/stage_contracts/request_code_sha256/{_escape_ptr(code_rel)}"
        add_file_pin(
            "registration",
            ptr,
            "selection.stage_contracts.request_code_sha256",
            code_rel,
            code_sha,
            [PRIMARY_REPO / code_rel],
        )

    # 8. bounded_carry.contract.code (59 Python files)
    for code_rel, code_sha in sorted(reg["bounded_carry"]["contract"]["code"].items()):
        ptr = f"/bounded_carry/contract/code/{_escape_ptr(code_rel)}"
        add_file_pin(
            "registration",
            ptr,
            "bounded_carry.contract.code",
            code_rel,
            code_sha,
            [PRIMARY_REPO / code_rel],
        )

    # 9. bounded_carry.contract.sizing_calibration provenance hashes naming files in notes/reviews/
    cal = reg["bounded_carry"]["contract"]["sizing_calibration"]
    calibration_file_pins = [
        (
            "/bounded_carry/contract/sizing_calibration/source_sha256",
            "notes/reviews/bc1_fit_calibration_claude_2026-10-28.md",
            cal["source_sha256"],
            "Named in sizing_calibration.source ('bc1_fit_calibration_claude_2026-10-28.md sections 2 and 4.4 (F5-F7)').",
        ),
        (
            "/bounded_carry/contract/sizing_calibration/escape_source_sha256",
            "notes/reviews/bc1_8f83d6cb3_claude_review_2026-10-28.md",
            cal["escape_source_sha256"],
            "Named in sizing_calibration.escape_basis ('bc1_8f83d6cb3_claude_review_2026-10-28.md section 4: 10-22a responses expand 1.11-1.25x').",
        ),
        (
            "/bounded_carry/contract/sizing_calibration/request_measurement/request_sha256",
            "notes/reviews/d63_count_tokens_request_2026-10-28.json",
            cal["request_measurement"]["request_sha256"],
            "Named in sizing_calibration.request_measurement.provenance ('fixed request retained in notes/reviews/d63_count_tokens_request_2026-10-28.json').",
        ),
    ]
    for ptr, rel_p, expected_sha, desc in calibration_file_pins:
        add_file_pin(
            "registration",
            ptr,
            "bounded_carry.contract.sizing_calibration",
            rel_p,
            expected_sha,
            [PRIMARY_REPO / rel_p, LAUNCH_BASE / rel_p],
            note=desc,
        )

    # 10. Non-file (computed / in-memory) SHA-256 leaves in registration
    computed_descriptions = {
        "/bounded_carry/contract/procedure_sha256": (
            "bc1_selection.py:93 — sha256(bc1_selection.PROCEDURE.encode('utf-8'))"
        ),
        "/bounded_carry/contract/audit/instruction_sha256/codec": (
            "bc1_audit.py:71 — sha256(codec.canonical(bc1_codec.contract()))"
        ),
        "/bounded_carry/contract/audit/instruction_sha256/worker": (
            "bc1_audit.py:72 — sha256(codec.canonical(audit_batch_format.contract('worker', version=2)))"
        ),
        "/bounded_carry/contract/audit/instruction_sha256/group": (
            "bc1_audit.py:73 — sha256(codec.canonical(bc1_audit._stage_contract(False)))"
        ),
        "/bounded_carry/contract/audit/instruction_sha256/final": (
            "bc1_audit.py:74 — sha256(codec.canonical(bc1_audit._stage_contract(True)))"
        ),
        "/bounded_carry/contract/audit/instruction_sha256/downstream": (
            "bc1_audit.py:75 — sha256(codec.canonical(bc1_audit.downstream_contract()))"
        ),
        "/selection/schema_context_trim/linkml_dumper_probe_sha256": (
            "shared_generation.py:215 — sha256(canonical({'slot': dumped_slot, 'class': dumped_class, 'enum': dumped_enum}))"
        ),
        "/selection/stage_contracts/api_playbook_probe_sha256": (
            "shared_generation.py:178 — sha256(api_playbook.adapt_template(api.prompt_body(api.GENERIC_PROMPT_V10), version=2).encode('utf-8'))"
        ),
        "/selection/stage_contracts/chunk_projection_probe_sha256": (
            "shared_generation.py:179 — sha256(canonical(evidence_assertions.source_chunks_from_bytes(b'line\\n', chunk_manifest_probe)[0]))"
        ),
        "/selection/stage_contracts/generation_context_header_sha256": (
            "shared_generation.py:181 — sha256(shared_generation.GENERATION_CONTEXT_HEADER.encode('utf-8'))"
        ),
        "/selection/stage_contracts/phase_instructions_sha256/audit": (
            "shared_generation.py:153 — sha256(api_runner.phase_instruction('audit', 25).encode('utf-8'))"
        ),
        "/selection/stage_contracts/phase_instructions_sha256/core": (
            "shared_generation.py:153 — sha256(api_runner.phase_instruction('core', 25).encode('utf-8'))"
        ),
        "/selection/stage_contracts/phase_instructions_sha256/full": (
            "shared_generation.py:153 — sha256(api_runner.phase_instruction('full', 25).encode('utf-8'))"
        ),
        "/selection/stage_contracts/phase_instructions_sha256/full_readdress": (
            "shared_generation.py:153 — sha256(api_runner.phase_instruction('full_readdress', 25).encode('utf-8'))"
        ),
        "/selection/stage_contracts/phase_instructions_sha256/full_receipt": (
            "shared_generation.py:153 — sha256(api_runner.phase_instruction('full_receipt', 25).encode('utf-8'))"
        ),
        "/selection/stage_contracts/phase_instructions_sha256/reconcile_core": (
            "shared_generation.py:153 — sha256(api_runner.phase_instruction('reconcile_core', 25).encode('utf-8'))"
        ),
        "/selection/stage_contracts/phase_instructions_sha256/reconcile_full": (
            "shared_generation.py:153 — sha256(api_runner.phase_instruction('reconcile_full', 25).encode('utf-8'))"
        ),
        "/selection/stage_contracts/phase_instructions_sha256/report": (
            "shared_generation.py:153 — sha256(api_runner.phase_instruction('report', 25).encode('utf-8'))"
        ),
        "/selection/stage_contracts/phase_instructions_sha256/report_regate": (
            "shared_generation.py:153 — sha256(api_runner.phase_instruction('report_regate', 25).encode('utf-8'))"
        ),
        "/selection/stage_contracts/phase_max_tokens_sha256": (
            "shared_generation.py:172 — sha256(canonical(max_tokens)) over PHASE_MAX_TOKENS, RECEIPT_PHASE_MAX_TOKENS, DEFAULT_MAX_TOKENS"
        ),
        "/selection/stage_contracts/phase_system_sha256": (
            "shared_generation.py:170 — sha256(api_runner.PHASE_SYSTEM.encode('utf-8'))"
        ),
        "/selection/stage_contracts/readdress_header_sha256": (
            "shared_generation.py:175 — sha256(api_runner.READDRESS_HEADER.encode('utf-8'))"
        ),
        "/selection/stage_contracts/receipt_completion_audit_carry_sha256": (
            "shared_generation.py:189 — sha256(receipt_completion._audit_carry(probe).encode('utf-8'))"
        ),
        "/selection/stage_contracts/receipt_completion_policy_sha256": (
            "shared_generation.py:188 — sha256(canonical(receipt_completion.policy_identity(version=2)))"
        ),
        "/selection/stage_contracts/regate_headers_sha256": (
            "shared_generation.py:173 — sha256(canonical(api_runner.REGATE_HEADERS))"
        ),
        "/selection/stage_contracts/repair_instruction_sha256": (
            "shared_generation.py:174 — sha256(api_runner.REPAIR_INSTRUCTION.encode('utf-8'))"
        ),
        "/selection/stage_contracts/schema_context_header_sha256": (
            "shared_generation.py:180 — sha256(shared_generation.SCHEMA_CONTEXT_HEADER.encode('utf-8'))"
        ),
        "/selection/stage_contracts/shared_evidence_contract_sha256": (
            "shared_generation.py:176 — sha256(api_runner.shared_evidence_contract().encode('utf-8'))"
        ),
        "/selection/stage_contracts/typed_audit_integration_format_sha256": (
            "shared_generation.py:185 — sha256(audit_batch_format.render('integration', version=2).encode('utf-8'))"
        ),
        "/selection/stage_contracts/typed_audit_system_sha256": (
            "shared_generation.py:182 — sha256(typed_audit_runtime.SYSTEM.encode('utf-8'))"
        ),
        "/selection/stage_contracts/typed_audit_worker_format_sha256": (
            "shared_generation.py:184 — sha256(audit_batch_format.render('worker', version=2).encode('utf-8'))"
        ),
        "/selection/stage_contracts/typed_binding_header_sha256": (
            "shared_generation.py:183 — sha256(typed_audit_runtime.BINDING_HEADER.encode('utf-8'))"
        ),
    }

    # Evaluate computed hashes in preview worktree code via subprocess in preview src
    eval_code = """
import hashlib, json, sys
sys.path.insert(0, %r)
from data_sheets_schema import shared_generation as sg, bc1_selection as bs, bc1_audit as ba
desc = sg.descriptor(version=1, condition="generic_v10")
bc1 = bs.contract_identity()
out = {
    "/bounded_carry/contract/procedure_sha256": bc1["procedure_sha256"],
    "/selection/schema_context_trim/linkml_dumper_probe_sha256": desc["schema_context_trim"]["linkml_dumper_probe_sha256"],
    "bc1_context": bc1["context"],
}
for k, v in bc1["audit"]["instruction_sha256"].items():
    out[f"/bounded_carry/contract/audit/instruction_sha256/{k}"] = v
for k, v in desc["stage_contracts"].items():
    if k in ("omission_assets_sha256", "request_code_sha256", "evidence_protocol_sha256"):
        continue
    if isinstance(v, dict):
        for subk, subv in v.items():
            out[f"/selection/stage_contracts/{k}/{subk}"] = subv
    else:
        out[f"/selection/stage_contracts/{k}"] = v
print(json.dumps(out))
""" % str(PREVIEW_WORKTREE / "src")

    eval_proc = subprocess.run(
        [sys.executable, "-c", eval_code],
        cwd=str(PREVIEW_WORKTREE),
        capture_output=True,
        text=True,
        check=True,
        env=_git_env(),
    )
    preview_computed = json.loads(eval_proc.stdout)

    computed_records: list[dict[str, Any]] = []
    for ptr, m4_sha in sorted(reg_all_leaves.items()):
        if ptr in handled_reg_pointers:
            continue
        prev_val = preview_computed.get(ptr)
        computed_records.append(
            {
                "document": "registration",
                "json_pointer": ptr,
                "m4_pinned_sha256": m4_sha,
                "preview_computed_sha256": prev_val,
                "status": "unchanged" if prev_val == m4_sha else "moved",
                "what_it_hashes": computed_descriptions.get(ptr, "unmapped"),
            }
        )
        handled_reg_pointers.add(ptr)

    unhandled_reg_leaves = sorted(set(reg_all_leaves) - handled_reg_pointers)

    # 11. Sizing sidecar additional file pins (sizing_record.{core,full,receipt}, receipt_completion_carry.source)
    sizing_only_file_pins: list[dict[str, Any]] = []
    for key in ("core", "full", "receipt"):
        pin = sizing["sizing"]["sizing_record"][key]
        repo_rel, disk_p = _normalize_repo_rel(pin["path"])
        info = _check_path_target(repo_rel, [disk_p, PRIMARY_REPO / repo_rel], pin["sha256"], pin.get("bytes"))
        sizing_only_file_pins.append(
            {
                "document": "sizing",
                "json_pointer": f"/sizing/sizing_record/{key}/sha256",
                "category": "sizing.sizing_record",
                **info,
            }
        )

    rc_source_pin = sizing["sizing"]["receipt_completion_carry"]["source"]
    repo_rel, disk_p = _normalize_repo_rel(rc_source_pin["path"])
    rc_info = _check_path_target(
        repo_rel,
        [disk_p, PRIMARY_REPO / repo_rel],
        rc_source_pin["sha256"],
        rc_source_pin.get("bytes"),
    )
    sizing_only_file_pins.append(
        {
            "document": "sizing",
            "json_pointer": "/sizing/receipt_completion_carry/source/sha256",
            "category": "sizing.receipt_completion_carry.source",
            **rc_info,
        }
    )

    # Also verify registration_sha256 pointers in sizing and roster
    m4_reg_disk_sha = _sha256_bytes(reg_raw)
    m4_sizing_disk_sha = _sha256_bytes(sizing_raw)
    m4_roster_disk_sha = _sha256_bytes(roster_raw)

    cross_file_pins = [
        {
            "document": "sizing",
            "json_pointer": "/registration_sha256",
            "target_path": str(REGISTRATION_PATH),
            "pinned_sha256": sizing["registration_sha256"],
            "actual_disk_sha256": m4_reg_disk_sha,
            "matches_m4_registration_bytes": sizing["registration_sha256"] == m4_reg_disk_sha,
        },
        {
            "document": "sizing",
            "json_pointer": "/sizing/registration_sha256",
            "target_path": str(REGISTRATION_PATH),
            "pinned_sha256": sizing["sizing"]["registration_sha256"],
            "actual_disk_sha256": m4_reg_disk_sha,
            "matches_m4_registration_bytes": sizing["sizing"]["registration_sha256"] == m4_reg_disk_sha,
        },
        {
            "document": "roster",
            "json_pointer": "/registrations/0/registration_sha256",
            "target_path": roster["registrations"][0]["registration_path"],
            "pinned_sha256": roster["registrations"][0]["registration_sha256"],
            "actual_disk_sha256": m4_reg_disk_sha,
            "matches_m4_registration_bytes": roster["registrations"][0]["registration_sha256"] == m4_reg_disk_sha,
        },
    ]

    # Summarize unique repository/disk file paths pinned in registration
    by_path: dict[str, dict[str, Any]] = {}
    for rec in pointer_records:
        if rec["category"] == "inputs.profile.basis_prefix":
            continue
        p = rec["repo_path"]
        if p not in by_path:
            by_path[p] = {
                "repo_path": p,
                "pointers_in_registration": [],
                "categories": [],
                "source_mode": rec["source_mode"],
                "in_git_at_m4": rec["in_git_at_m4"],
                "in_git_at_preview": rec["in_git_at_preview"],
                "m4_pinned_sha256": rec["m4_pinned_sha256"],
                "git_m4_sha256": rec["git_m4_sha256"],
                "git_main_925d726d_sha256": rec["git_main_925d726d_sha256"],
                "preview_effective_sha256": rec["preview_effective_sha256"],
                "m4_pinned_bytes": rec["m4_pinned_bytes"],
                "preview_effective_bytes": rec["preview_effective_bytes"],
                "disk_path": rec["disk_path"],
                "status": rec["status"],
                "git_log_m4_to_preview": rec["git_log_m4_to_preview"],
            }
        by_path[p]["pointers_in_registration"].append(rec["json_pointer"])
        if rec["category"] not in by_path[p]["categories"]:
            by_path[p]["categories"].append(rec["category"])

    moved_unique_files = [v for k, v in sorted(by_path.items()) if v["status"] == "moved"]
    unchanged_unique_files = [v for k, v in sorted(by_path.items()) if v["status"] == "unchanged"]
    missing_unique_files = [v for k, v in sorted(by_path.items()) if v["status"] == "missing_path"]

    # Check Python code lists specifically against AGY3's Section 2 counts
    req_code_files = set(reg["selection"]["stage_contracts"]["request_code_sha256"])
    bc1_code_files = set(reg["bounded_carry"]["contract"]["code"])
    all_py_files = sorted(req_code_files | bc1_code_files)
    moved_py_files = [p for p in all_py_files if by_path[p]["status"] == "moved"]
    unchanged_py_files = [p for p in all_py_files if by_path[p]["status"] == "unchanged"]

    # Verify AGY3's 6 claimed moved files
    agy3_comparison = []
    for path_key, (claimed_old, claimed_new) in AGY3_CLAIMED_MOVED.items():
        actual = by_path[path_key]
        agy3_comparison.append(
            {
                "repo_path": path_key,
                "agy3_claimed_m4_sha256": claimed_old,
                "actual_m4_sha256": actual["m4_pinned_sha256"],
                "agy3_claimed_preview_sha256": claimed_new,
                "actual_preview_sha256": actual["preview_effective_sha256"],
                "confirmed_exact_match": (
                    actual["status"] == "moved"
                    and actual["m4_pinned_sha256"] == claimed_old
                    and actual["preview_effective_sha256"] == claimed_new
                ),
                "git_log_m4_to_preview": actual["git_log_m4_to_preview"],
            }
        )

    # Also map all sizing and roster hex64 leaves by JSON pointer
    sizing_computed_pointers = []
    for ptr, val in sorted(sizing_all_leaves.items()):
        if ptr == "/sizing/plan_sha256":
            sizing_computed_pointers.append(
                {
                    "document": "sizing",
                    "json_pointer": ptr,
                    "m4_pinned_sha256": val,
                    "what_it_hashes": "bc1_registration.py:259 — packet['plan']['sha256'] (canonical JSON of BC1 worker partition plan)",
                }
            )
        elif ptr == "/sizing/receipt_completion_carry/sha256":
            sizing_computed_pointers.append(
                {
                    "document": "sizing",
                    "json_pointer": ptr,
                    "m4_pinned_sha256": val,
                    "what_it_hashes": "bc1_registration.py:267 — sha256(receipt_completion.bc1_audit_carry(outcome).encode('utf-8'))",
                }
            )
        elif ptr.startswith("/sizing/rows/") and ptr.endswith("/wire_sha256"):
            row_idx = int(ptr.split("/")[3])
            row_obj = sizing["sizing"]["rows"][row_idx]
            sizing_computed_pointers.append(
                {
                    "document": "sizing",
                    "json_pointer": ptr,
                    "m4_pinned_sha256": val,
                    "stage": row_obj["stage"],
                    "scenario": row_obj["scenario"],
                    "what_it_hashes": "bc1_registration.py:203 — sha256(shared_generation.canonical(payload)) for rendered stage/scenario request",
                }
            )

    output_payload = {
        "schema": "a21_pinned_closure_check_v1",
        "commits": {
            "m4_base": M4_COMMIT,
            "current_main": MAIN_COMMIT,
            "pr5808_head": PR5808_COMMIT,
            "merge_preview": PREVIEW_COMMIT,
        },
        "m4_artifacts": {
            "registration_path": str(REGISTRATION_PATH),
            "registration_sha256": m4_reg_disk_sha,
            "sizing_path": str(SIZING_PATH),
            "sizing_sha256": m4_sizing_disk_sha,
            "roster_path": str(ROSTER_PATH),
            "roster_sha256": m4_roster_disk_sha,
        },
        "counts": {
            "total_hex64_leaves_in_registration": len(reg_all_leaves),
            "unhandled_hex64_leaves_in_registration": len(unhandled_reg_leaves),
            "total_hex64_leaves_in_sizing": len(sizing_all_leaves),
            "total_hex64_leaves_in_roster": len(roster_all_leaves),
            "file_backed_pin_pointers_in_registration": len(pointer_records) - 1,
            "embedded_prefix_pointers_in_registration": 1,
            "computed_non_file_hash_pointers_in_registration": len(computed_records),
            "computed_non_file_hash_pointers_in_sizing": len(sizing_computed_pointers),
            "unique_pinned_files_in_registration": len(by_path),
            "unique_pinned_files_moved": len(moved_unique_files),
            "unique_pinned_files_unchanged": len(unchanged_unique_files),
            "unique_pinned_files_missing": len(missing_unique_files),
            "request_code_sha256_count": len(req_code_files),
            "bounded_carry_contract_code_count": len(bc1_code_files),
            "unique_pinned_python_files_total": len(all_py_files),
            "unique_pinned_python_files_moved": len(moved_py_files),
            "unique_pinned_python_files_unchanged": len(unchanged_py_files),
            "only_in_request_code_sha256": sorted(req_code_files - bc1_code_files),
            "only_in_bounded_carry_contract_code": sorted(bc1_code_files - req_code_files),
            "selection_assets_count": len(reg["selection"]["assets"]),
            "omission_contract_assets_count": len(
                reg["selection"]["stage_contracts"]["omission_assets_sha256"]
            ),
            "sizing_only_additional_file_pins_count": len(sizing_only_file_pins),
        },
        "agy3_runbook_comparison": {
            "six_claimed_moved_items_confirmed": all(r["confirmed_exact_match"] for r in agy3_comparison),
            "anything_else_moved_in_pinned_files": [
                r["repo_path"] for r in moved_unique_files if r["repo_path"] not in AGY3_CLAIMED_MOVED
            ],
            "anything_moved_in_computed_contract_or_instruction_hashes": [
                r["json_pointer"] for r in computed_records if r["status"] != "unchanged"
            ],
            "bounded_carry_contract_context_moved": {
                "m4_value": reg["bounded_carry"]["contract"]["context"],
                "preview_value": preview_computed["bc1_context"],
                "moved": reg["bounded_carry"]["contract"]["context"] != preview_computed["bc1_context"],
            },
            "runbook_count_discrepancies": {
                "agy3_claimed_request_code_sha256_count": 42,
                "actual_request_code_sha256_count": len(req_code_files),
                "agy3_claimed_bounded_carry_code_count": 48,
                "actual_bounded_carry_code_count": len(bc1_code_files),
                "agy3_claimed_total_unique_python_files": 50,
                "actual_total_unique_python_files": len(all_py_files),
                "agy3_claimed_unchanged_python_files": 46,
                "actual_unchanged_python_files": len(unchanged_py_files),
                "explanation": (
                    "AGY3 Section 2 prose (lines 114 and 128) states '50 Python source files "
                    "(42 in selection.stage_contracts.request_code_sha256 and 48 in bounded_carry.contract.code)' "
                    "and 'All other 46 pinned Python files'. In the actual M4 registration JSON, "
                    "request_code_sha256 has 53 files, bounded_carry.contract.code has 59 files, "
                    "their union is 61 unique Python files, and with 4 moved Python files, "
                    "57 pinned Python files are unchanged."
                ),
            },
            "six_claimed_items_detail": agy3_comparison,
        },
        "moved_unique_files": moved_unique_files,
        "unchanged_unique_files": unchanged_unique_files,
        "missing_unique_files": missing_unique_files,
        "computed_non_file_hashes_in_registration": computed_records,
        "computed_non_file_hashes_in_sizing": sizing_computed_pointers,
        "sizing_sidecar_additional_file_pins": sizing_only_file_pins,
        "cross_file_registration_sha256_pins": cross_file_pins,
        "all_registration_file_pin_pointers": pointer_records,
    }

    OUT_JSON.write_text(json.dumps(output_payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    script_sha = _sha256_bytes(Path(__file__).resolve().read_bytes())
    json_sha = _sha256_bytes(OUT_JSON.read_bytes())
    print(f"SCRIPT_SHA256={script_sha}")
    print(f"JSON_SHA256={json_sha}")
    print(json.dumps(output_payload["counts"], indent=2))
    print(json.dumps(output_payload["agy3_runbook_comparison"], indent=2))


if __name__ == "__main__":
    import sys

    main()
