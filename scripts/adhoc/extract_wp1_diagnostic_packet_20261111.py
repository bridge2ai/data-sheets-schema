#!/usr/bin/env python3
"""Extract and verify exact records, hashes, argv, and preflight state for the D132 WP1 cpu-monitoring diagnostic run packet.

Purpose: Read-only extraction of all paths, SHA-256 digests, argv lists, and readiness checks
         from retained WP1/U3-M records and helper scripts without importing project code or
         mutating any target worktree, configuration, or scratch artifact.
Inputs:  Retained JSON records under d4d-executions/scratch-native-u1u3/u3m/ and source files
         in codex-native-u1u3, codex-native-wp1-preparation-20261111, and
         codex-native-capture-cleanup-20261111.
Outputs: d4d-executions/codex-development-efficiency-20261111/tmp/diagnostic-packet-20261111/packet-facts.json
Issue/PR: D132 diagnostic run packet assignment (claude-lead-agy4-diagnostic-run-packet.md)
Date:    2026-11-11
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET


EXECUTIONS = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions")
SCRATCH_U3M = EXECUTIONS / "scratch-native-u1u3/u3m"
SOURCE_ROOT = EXECUTIONS / "codex-native-u1u3"
PREP_ROOT = EXECUTIONS / "codex-native-wp1-preparation-20261111"
CLEANUP_ROOT = EXECUTIONS / "codex-native-capture-cleanup-20261111"
EFFICIENCY_ROOT = EXECUTIONS / "codex-development-efficiency-20261111"
OUT_DIR = EFFICIENCY_ROOT / "tmp/diagnostic-packet-20261111"
OUT_JSON = OUT_DIR / "packet-facts.json"

SOURCE_COMMIT = "382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b"
SHORT_COMMIT = SOURCE_COMMIT[:12]

GIT_ENV = {
    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    "LANG": "en_US.UTF-8",
    "GIT_ALLOW_PROTOCOL": "",
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_CONFIG_GLOBAL": "/dev/null",
}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path):
    return json.loads(path.read_bytes())


def git_read(cwd: Path, *args: str) -> str:
    return subprocess.check_output(
        [
            "/usr/bin/git",
            "--no-replace-objects",
            "--no-optional-locks",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "diff.autoRefreshIndex=false",
            *args,
        ],
        cwd=cwd,
        env=GIT_ENV,
        text=True,
        timeout=15,
    ).strip()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    contract_path = SCRATCH_U3M / f"wp1-contract-{SHORT_COMMIT}.json"
    composition_dir = SCRATCH_U3M / f"composition-{SHORT_COMMIT}"
    composition_path = composition_dir / "composition.json"
    config_restored_path = composition_dir / "config-restored.json"
    worktree_dir = SCRATCH_U3M / f"worktree-{SHORT_COMMIT}"
    canary_dir = SCRATCH_U3M / f"wp1-{SHORT_COMMIT}-canary-capture-ast-20261111"
    capture_dir = SCRATCH_U3M / f"wp1-{SHORT_COMMIT}-capture-recheck-capture-ast-20261111"
    interrupted_dir = SCRATCH_U3M / f"wp1-{SHORT_COMMIT}-cpu-monitoring-post-capture-ast-20261111"
    cleanup_wrapper_dir = SCRATCH_U3M / f"cleanup-wrapper-{SHORT_COMMIT}-20261111"
    completed_4588_dir = SCRATCH_U3M / "wp1-458887766eff-cpu-monitoring-post-5834-20261111"

    contract = read_json(contract_path)
    contract_sha = sha256_file(contract_path)
    composition = read_json(composition_path)
    composition_sha = sha256_file(composition_path)
    config_restored = read_json(config_restored_path)
    config_restored_sha = sha256_file(config_restored_path)

    # 1. Interrupted diagnostic records
    interrupted_supervisor_path = interrupted_dir.with_suffix(".supervisor.json")
    interrupted_outer_path = interrupted_dir.with_suffix(".outer.json")
    interrupted_outer_log_path = interrupted_dir.with_suffix(".outer.log")
    interrupted_supervisor = read_json(interrupted_supervisor_path)
    interrupted_outer = read_json(interrupted_outer_path)
    interrupted_plan = read_json(interrupted_dir / "plan.json")
    interrupted_pytest_cmd = read_json(interrupted_dir / "pytest-command.json")
    interrupted_bootstrap = read_json(interrupted_dir / "bootstrap.json")
    interrupted_dep_links = read_json(interrupted_dir / "dependency-links.json")
    interrupted_wp1_harness = read_json(interrupted_dir / "wp1-harness.json")
    interrupted_u3m_harness = read_json(interrupted_dir / "u3m-harness.json")
    interrupted_quiet_lease = read_json(interrupted_dir / "wp1-quiet-lease.json")
    interrupted_host_load = read_json(interrupted_dir / "host-load.json")
    interrupted_outcome = read_json(interrupted_dir / "outcome.json")
    interrupted_cutoff = read_json(interrupted_dir / "wp1-cutoff.json")
    interrupted_stability = read_json(interrupted_dir / "source-stability.json")

    # 2. Prerequisite canary records
    canary_outer_path = canary_dir.with_suffix(".outer.json")
    canary_supervisor_path = canary_dir.with_suffix(".supervisor.json")
    canary_outer = read_json(canary_outer_path)
    canary_supervisor = read_json(canary_supervisor_path)
    canary_outcome = read_json(canary_dir / "outcome.json")
    canary_harness = read_json(canary_dir / "wp1-harness.json")
    canary_xml_path = canary_dir / "pytest.xml"
    canary_xml_root = ET.fromstring(canary_xml_path.read_bytes())
    canary_testcases = [elem.attrib for elem in canary_xml_root.iter("testcase")]
    canary_failures = (
        list(canary_xml_root.iter("failure"))
        + list(canary_xml_root.iter("error"))
        + list(canary_xml_root.iter("skipped"))
    )
    canary_equiv_files = sorted((canary_dir / "phase-metrics").glob("*-consumer-observer-equivalence.json"))
    canary_lim_files = sorted(
        (canary_dir / "phase-metrics").glob("*-consumer-observer-profile-mutation-limitation.json")
    )
    canary_meas_files = sorted((canary_dir / "phase-metrics").glob("*-measurement.json"))

    # 3. Private config bytes & arming verification
    private_cfg_record = composition["private_config"]
    config_file = Path(private_cfg_record["path"])
    backup_file = Path(private_cfg_record["backup"])
    config_raw = config_file.read_bytes()
    backup_raw = backup_file.read_bytes()
    config_mode = stat.S_IMODE(config_file.lstat().st_mode)
    backup_mode = stat.S_IMODE(backup_file.lstat().st_mode)
    appended_section = b"[d4d]\n\tciRepositoryUrl = https://github.com/bridge2ai/data-sheets-schema.git\n"
    reconstructed_armed_raw = backup_raw + appended_section
    reconstructed_armed_sha = sha256_bytes(reconstructed_armed_raw)

    # 4. Cleanup wrapper records & helper hashes
    cleanup_helper_path = CLEANUP_ROOT / "scripts/adhoc/cleanup_native_capture_config_20261111.py"
    cleanup_started_path = cleanup_wrapper_dir / "started.json"
    cleanup_result_path = cleanup_wrapper_dir / "result.json"
    cleanup_started = read_json(cleanup_started_path)
    cleanup_result = read_json(cleanup_result_path)

    prep_canary_helper_path = PREP_ROOT / "scripts/adhoc/prepare_native_wp1_canary_20261111.py"
    prep_private_cfg_helper_path = PREP_ROOT / "scripts/adhoc/native_wp1_private_config_20261111.py"
    u3m_composer_path = SOURCE_ROOT / "scripts/adhoc/compose_native_u3m_20261109.py"
    u1u3_composer_path = SOURCE_ROOT / "scripts/adhoc/compose_native_u1u3_20261108.py"

    # 5. Implementation SHA-256 verification across SOURCE_ROOT and worktree_dir
    impl_checks = {}
    for rel_path, expected_sha in sorted(contract["implementation_sha256"].items()):
        src_file = SOURCE_ROOT / rel_path
        wt_file = worktree_dir / rel_path
        src_sha = sha256_file(src_file) if src_file.is_file() else None
        wt_sha = sha256_file(wt_file) if wt_file.is_file() else None
        impl_checks[rel_path] = {
            "expected_sha256": expected_sha,
            "source_root_sha256": src_sha,
            "worktree_sha256": wt_sha,
            "source_matches": src_sha == expected_sha,
            "worktree_matches": wt_sha == expected_sha,
        }

    # 6. Protected preimages and packet postimages verification
    preimage_checks = {}
    for rel_path, expected_sha in sorted(composition["protected_preimages_sha256"].items()):
        src_file = SOURCE_ROOT / rel_path
        src_sha = sha256_file(src_file)
        preimage_checks[rel_path] = {
            "expected_sha256": expected_sha,
            "actual_sha256": src_sha,
            "matches": src_sha == expected_sha,
        }

    postimage_checks = {}
    for rel_path, expected_sha in sorted(composition["packet_postimages_sha256"].items()):
        wt_file = worktree_dir / rel_path
        tree_file = composition_dir / "tree" / rel_path
        wt_sha = sha256_file(wt_file)
        tree_sha = sha256_file(tree_file)
        postimage_checks[rel_path] = {
            "expected_sha256": expected_sha,
            "worktree_sha256": wt_sha,
            "tree_sha256": tree_sha,
            "matches": wt_sha == expected_sha and tree_sha == expected_sha,
        }

    # 7. Interpreter and dependency links check
    venv_python = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python")
    resolved_python = venv_python.resolve(strict=True)
    venv_site = venv_python.parent.parent / "lib/python3.13/site-packages"
    pyvenv_cfg = venv_python.parent.parent / "pyvenv.cfg"

    dep_targets_ok = True
    missing_dep_targets = []
    for name, info in sorted(interrupted_dep_links["links"].items()):
        target_path = Path(info["target"])
        if not target_path.exists() or target_path.resolve(strict=True) != target_path:
            dep_targets_ok = False
            missing_dep_targets.append(str(target_path))

    fairscape_dir = SCRATCH_U3M / "dependencies/fairscape-8c80311d7d8b0fadac07dca9567d632103691f48"
    fairscape_manifest = read_json(fairscape_dir / "manifest.json")
    fairscape_manifest_sha = sha256_file(fairscape_dir / "manifest.json")
    fairscape_archive_sha = sha256_file(fairscape_dir / "source.tar")

    # 8. Lock, claim, and proposed second-run output paths
    quiet_lock_path = EXECUTIONS / "plans/native_quiet_window.lock"
    once_claim_path = (
        SCRATCH_U3M / f"capture-recheck-{SOURCE_COMMIT}-{contract_sha}.once.json"
    )
    once_claim = read_json(once_claim_path)
    once_claim_sha = sha256_file(once_claim_path)

    proposed_label = "post-capture-ast-r2-20261111"
    proposed_out = SCRATCH_U3M / f"wp1-{SHORT_COMMIT}-cpu-monitoring-{proposed_label}"
    proposed_paths = [
        proposed_out,
        proposed_out.with_suffix(".supervisor.json"),
        proposed_out.with_suffix(".outer.json"),
        proposed_out.with_suffix(".outer.log"),
        proposed_out.with_suffix(".qualification"),
    ]
    proposed_existence = {str(p): os.path.lexists(p) for p in proposed_paths}

    proposed_cleanup_wrapper_dir = SCRATCH_U3M / f"cleanup-wrapper-{SHORT_COMMIT}-r2-20261111"
    proposed_config_r2_dir = composition_dir / "cpu-diagnostic-config-r2"
    proposed_config_restored_r2 = composition_dir / "config-restored-r2-20261111.json"

    # 9. Completed 458887766eff reference diagnostic
    completed_4588_diag_path = completed_4588_dir / "phase-metrics/34474-diagnostic.json"
    completed_4588_meas_path = completed_4588_dir / "phase-metrics/34474-measurement.json"
    completed_4588_diag = read_json(completed_4588_diag_path)
    completed_4588_meas = read_json(completed_4588_meas_path)

    # 9b. Newly executed D132 lead rerun records (2026-11-11T16:37:20Z - 16:45:46Z)
    lead_once_claim_path = SCRATCH_U3M / f"lead-cpu-monitoring-rerun-{SHORT_COMMIT}.once.json"
    lead_log_path = SCRATCH_U3M / f"lead-cpu-monitoring-rerun-{SHORT_COMMIT}-20261111.log"
    lead_rearm_dir = SCRATCH_U3M / f"lead-config-rearm-{SHORT_COMMIT}-20261111"
    lead_rearm_helper_path = (
        EFFICIENCY_ROOT / "scripts/adhoc/native_private_config_rearm_restore_20261111.py"
    )
    lead_runner_sh_path = (
        EFFICIENCY_ROOT / "scripts/adhoc/run_native_cpu_monitoring_once_20261111.sh"
    )
    lead_canary_dir = SCRATCH_U3M / f"wp1-{SHORT_COMMIT}-canary-lead-rerun-20261111"
    lead_rerun_dir = SCRATCH_U3M / f"wp1-{SHORT_COMMIT}-cpu-monitoring-lead-rerun-20261111"
    lead_rerun_sup_path = lead_rerun_dir.with_suffix(".supervisor.json")
    lead_rerun_outer_path = lead_rerun_dir.with_suffix(".outer.json")
    lead_rerun_diag_path = lead_rerun_dir / "phase-metrics/67941-diagnostic.json"
    lead_rerun_meas_path = lead_rerun_dir / "phase-metrics/67941-measurement.json"
    lead_rerun_diag = read_json(lead_rerun_diag_path)
    lead_rerun_meas = read_json(lead_rerun_meas_path)
    lead_rerun_sup = read_json(lead_rerun_sup_path)
    lead_rerun_outer = read_json(lead_rerun_outer_path)
    lead_rearm_records = {
        p.name: {"path": str(p), "sha256": sha256_file(p), "content": read_json(p)}
        for p in sorted(lead_rearm_dir.glob("*.json"))
    }

    # 10. Current host load sample
    load1, load5, load15 = os.getloadavg()
    logical_cpus = os.cpu_count() or 1

    # 11. Git worktree cleanliness & HEAD checks
    git_states = {}
    for label_name, repo_path in (
        ("codex-native-u1u3", SOURCE_ROOT),
        ("worktree-382f0dfd1ce8", worktree_dir),
        ("composition-382f0dfd1ce8-tree", composition_dir / "tree"),
        ("codex-native-wp1-preparation-20261111", PREP_ROOT),
        ("codex-native-capture-cleanup-20261111", CLEANUP_ROOT),
    ):
        git_states[label_name] = {
            "path": str(repo_path),
            "head": git_read(repo_path, "rev-parse", "HEAD"),
            "branch": git_read(repo_path, "rev-parse", "--abbrev-ref", "HEAD"),
            "status_porcelain": git_read(repo_path, "status", "--porcelain", "--untracked-files=normal"),
        }

    # Reconstruct outermost argv for interrupted run and for proposed second run
    validator_script = SOURCE_ROOT / "scripts/adhoc/native_wp1_validation_20261110.py"
    interrupted_outermost_argv = [
        str(venv_python),
        "-S",
        "-P",
        "-B",
        str(validator_script),
        "cpu-monitoring",
        "--label",
        "post-capture-ast-20261111",
        "--canary-out",
        str(canary_dir),
    ]
    interrupted_supervised_argv = [
        str(venv_python),
        "-S",
        "-P",
        "-B",
        str(validator_script),
        "--supervised",
        "cpu-monitoring",
        "--label",
        "post-capture-ast-20261111",
        "--canary-out",
        str(canary_dir),
    ]
    proposed_outermost_argv = [
        str(venv_python),
        "-S",
        "-P",
        "-B",
        str(validator_script),
        "cpu-monitoring",
        "--label",
        proposed_label,
        "--canary-out",
        str(canary_dir),
    ]
    cleanup_wrapper_argv = [
        str(venv_python),
        "-S",
        "-P",
        "-B",
        str(cleanup_helper_path),
    ]
    composer_cleanup_argv = [
        str(venv_python),
        "-S",
        "-P",
        "-B",
        str(u3m_composer_path),
        "cleanup",
        "--commit",
        SOURCE_COMMIT,
    ]

    facts = {
        "source_commit": SOURCE_COMMIT,
        "short_commit": SHORT_COMMIT,
        "contract": {
            "path": str(contract_path),
            "sha256": contract_sha,
            "kind": contract["kind"],
            "version": contract["version"],
            "source_commit": contract["source_commit"],
            "composition_manifest": contract["composition_manifest"],
            "composition_manifest_sha256": contract["composition_manifest_sha256"],
            "interpreter": contract["interpreter"],
            "implementation_file_count": len(contract["implementation_sha256"]),
            "all_implementation_files_match_source_root": all(
                row["source_matches"] for row in impl_checks.values()
            ),
            "all_implementation_files_match_worktree": all(
                row["worktree_matches"] for row in impl_checks.values()
            ),
            "implementation_checks": impl_checks,
        },
        "composition": {
            "path": str(composition_path),
            "sha256": composition_sha,
            "matches_contract_pin": composition_sha == contract["composition_manifest_sha256"],
            "status": composition["status"],
            "composition_commit": composition["composition_commit"],
            "composition_tree": composition["composition_tree"],
            "source_worktree": composition["source_worktree"],
            "test_worktree": composition["test_worktree"],
            "private_git": composition["private_git"],
            "preparation_tools_worktree": composition["preparation_tools_worktree"],
            "preparation_tools_commit": composition["preparation_tools_commit"],
            "helper_sha256": composition["helper_sha256"],
            "all_protected_preimages_match": all(row["matches"] for row in preimage_checks.values()),
            "all_packet_postimages_match": all(row["matches"] for row in postimage_checks.values()),
            "preimage_checks": preimage_checks,
            "postimage_checks": postimage_checks,
        },
        "private_config": {
            "record": private_cfg_record,
            "current_config_sha256": sha256_bytes(config_raw),
            "current_config_bytes": len(config_raw),
            "current_config_mode_octal": oct(config_mode),
            "current_config_text": config_raw.decode("utf-8"),
            "backup_sha256": sha256_bytes(backup_raw),
            "backup_bytes": len(backup_raw),
            "backup_mode_octal": oct(backup_mode),
            "current_equals_original_backup": config_raw == backup_raw,
            "appended_armed_section_bytes": len(appended_section),
            "appended_armed_section_text": appended_section.decode("utf-8"),
            "reconstructed_armed_bytes": len(reconstructed_armed_raw),
            "reconstructed_armed_sha256": reconstructed_armed_sha,
            "reconstructed_matches_configured_sha256": (
                reconstructed_armed_sha == private_cfg_record["configured_sha256"]
            ),
            "config_restored_json": {
                "path": str(config_restored_path),
                "exists": os.path.lexists(config_restored_path),
                "sha256": config_restored_sha,
                "content": config_restored,
            },
        },
        "helpers": {
            "prepare_native_wp1_canary_20261111": {
                "path": str(prep_canary_helper_path),
                "sha256": sha256_file(prep_canary_helper_path),
                "matches_composition_helper_sha256": (
                    sha256_file(prep_canary_helper_path) == composition["helper_sha256"]
                ),
            },
            "native_wp1_private_config_20261111": {
                "path": str(prep_private_cfg_helper_path),
                "sha256": sha256_file(prep_private_cfg_helper_path),
                "hardcoded_head": "3cc113e2606c563236d9c06098c5329ddd027a38",
            },
            "cleanup_native_capture_config_20261111": {
                "path": str(cleanup_helper_path),
                "sha256": sha256_file(cleanup_helper_path),
                "outermost_argv": cleanup_wrapper_argv,
                "in_process_composer_argv": composer_cleanup_argv,
                "existing_evidence_dir": str(cleanup_wrapper_dir),
                "existing_evidence_exists": os.path.lexists(cleanup_wrapper_dir),
                "started_json": {
                    "path": str(cleanup_started_path),
                    "sha256": sha256_file(cleanup_started_path),
                    "content": cleanup_started,
                },
                "result_json": {
                    "path": str(cleanup_result_path),
                    "sha256": sha256_file(cleanup_result_path),
                    "content": cleanup_result,
                },
            },
            "compose_native_u3m_20261109": {
                "path": str(u3m_composer_path),
                "sha256": sha256_file(u3m_composer_path),
                "matches_cleanup_restored_helper_sha256": (
                    sha256_file(u3m_composer_path) == config_restored["helper_sha256"]
                ),
            },
            "compose_native_u1u3_20261108": {
                "path": str(u1u3_composer_path),
                "sha256": sha256_file(u1u3_composer_path),
            },
        },
        "canary_prerequisite": {
            "dir": str(canary_dir),
            "outer_json_path": str(canary_outer_path),
            "outer_json_sha256": sha256_file(canary_outer_path),
            "supervisor_json_path": str(canary_supervisor_path),
            "supervisor_json_sha256": sha256_file(canary_supervisor_path),
            "pytest_xml_path": str(canary_xml_path),
            "pytest_xml_sha256": sha256_file(canary_xml_path),
            "outer_command": canary_outer["command"],
            "returncode": canary_supervisor["returncode"],
            "cleanup_verified": canary_supervisor["cleanup_verified"],
            "manifest_sha256": canary_supervisor["manifest_sha256"],
            "testcases": canary_testcases,
            "failures_count": len(canary_failures),
            "equivalence_files": [str(p) for p in canary_equiv_files],
            "limitation_files": [str(p) for p in canary_lim_files],
            "measurement_files": [str(p) for p in canary_meas_files],
            "outcome_returncode": canary_outcome["returncode"],
            "harness_source_unchanged": canary_harness["source_unchanged"],
        },
        "interrupted_diagnostic": {
            "dir": str(interrupted_dir),
            "supervisor_json_path": str(interrupted_supervisor_path),
            "supervisor_json_sha256": sha256_file(interrupted_supervisor_path),
            "outer_json_path": str(interrupted_outer_path),
            "outer_json_sha256": sha256_file(interrupted_outer_path),
            "outer_log_path": str(interrupted_outer_log_path),
            "outer_log_sha256": sha256_file(interrupted_outer_log_path),
            "reconstructed_outermost_argv": interrupted_outermost_argv,
            "reconstructed_supervised_argv": interrupted_supervised_argv,
            "recorded_driver_command_in_outer_json": interrupted_outer["command"],
            "recorded_worker_command_in_plan_json": interrupted_plan["command"],
            "recorded_pytest_args_in_pytest_command_json": interrupted_pytest_cmd["args"],
            "plan_source_root": interrupted_plan["source_root"],
            "plan_source_commit": interrupted_plan["source_commit"],
            "plan_environment": interrupted_plan["environment"],
            "supervisor_summary": {
                "kind": interrupted_supervisor["kind"],
                "returncode": interrupted_supervisor["returncode"],
                "cleanup_verified": interrupted_supervisor["cleanup_verified"],
                "forced_cleanup": interrupted_supervisor["forced_cleanup"],
                "interrupted": interrupted_supervisor["interrupted"],
                "seconds": interrupted_supervisor["seconds"],
                "limit_seconds": interrupted_supervisor["limit_seconds"],
                "manifest": interrupted_supervisor["manifest"],
                "manifest_sha256": interrupted_supervisor["manifest_sha256"],
            },
            "outer_summary": {
                "kind": interrupted_outer["kind"],
                "arm": interrupted_outer["arm"],
                "node": interrupted_outer["node"],
                "returncode": interrupted_outer["returncode"],
                "child_returncode": interrupted_outer["child_returncode"],
                "cleanup_verified": interrupted_outer["cleanup_verified"],
                "timed_out": interrupted_outer["timed_out"],
                "interrupted": interrupted_outer["interrupted"],
                "forced_cleanup": interrupted_outer["forced_cleanup"],
                "seconds": interrupted_outer["seconds"],
                "limit_seconds": interrupted_outer["limit_seconds"],
                "host_contention": interrupted_outer["host_contention"],
            },
            "outcome_summary": {
                "returncode": interrupted_outcome["returncode"],
                "worker_returncode": interrupted_outcome["worker_returncode"],
                "interrupted": interrupted_outcome["interrupted"],
                "forced_cleanup": interrupted_outcome["forced_cleanup"],
                "cleanup_verified": interrupted_outcome["cleanup_verified"],
                "seconds": interrupted_outcome["seconds"],
            },
            "host_load_json": interrupted_host_load,
            "quiet_lease_json": interrupted_quiet_lease,
            "wp1_harness_sha256": sha256_file(interrupted_dir / "wp1-harness.json"),
            "wp1_cutoff": interrupted_cutoff,
            "source_stability_unchanged": interrupted_stability["unchanged"],
            "missing_completion_artifacts": {
                "pytest_xml_exists": os.path.lexists(interrupted_dir / "pytest.xml"),
                "origins_after_exists": os.path.lexists(interrupted_dir / "origins-after.json"),
                "worker_outcome_exists": os.path.lexists(interrupted_dir / "worker-outcome.json"),
                "phase_metrics_entries": [
                    p.name for p in sorted((interrupted_dir / "phase-metrics").iterdir())
                ],
            },
        },
        "dependencies_and_interpreter": {
            "venv_python_symlink": str(venv_python),
            "venv_python_resolved": str(resolved_python),
            "resolved_python_sha256": sha256_file(resolved_python),
            "matches_contract_interpreter_sha256": (
                sha256_file(resolved_python) == contract["interpreter"]["sha256"]
            ),
            "pyvenv_cfg_exists": pyvenv_cfg.is_file(),
            "venv_site_packages": str(venv_site),
            "venv_site_is_physical_dir": venv_site.is_dir() and venv_site.resolve(strict=True) == venv_site,
            "dependency_link_count": len(interrupted_dep_links["links"]),
            "all_dependency_targets_exist": dep_targets_ok,
            "missing_dependency_targets": missing_dep_targets,
            "fairscape_dependency": {
                "dir": str(fairscape_dir),
                "manifest_sha256": fairscape_manifest_sha,
                "archive_sha256": fairscape_archive_sha,
                "gitlink": fairscape_manifest["gitlink"],
                "file_count": len(fairscape_manifest["files"]),
            },
        },
        "locks_claims_and_second_run_names": {
            "quiet_window_lock_path": str(quiet_lock_path),
            "quiet_window_lock_exists": os.path.lexists(quiet_lock_path),
            "capture_recheck_once_claim": {
                "path": str(once_claim_path),
                "exists": os.path.lexists(once_claim_path),
                "sha256": once_claim_sha,
                "content": once_claim,
            },
            "proposed_second_run_label": proposed_label,
            "proposed_second_run_out": str(proposed_out),
            "proposed_second_run_outermost_argv": proposed_outermost_argv,
            "proposed_second_run_paths_exist": proposed_existence,
            "proposed_cleanup_wrapper_r2_dir": str(proposed_cleanup_wrapper_dir),
            "proposed_cleanup_wrapper_r2_exists": os.path.lexists(proposed_cleanup_wrapper_dir),
            "proposed_config_r2_dir": str(proposed_config_r2_dir),
            "proposed_config_r2_exists": os.path.lexists(proposed_config_r2_dir),
            "proposed_config_restored_r2_path": str(proposed_config_restored_r2),
            "proposed_config_restored_r2_exists": os.path.lexists(proposed_config_restored_r2),
        },
        "reference_completed_diagnostic_458887766eff": {
            "dir": str(completed_4588_dir),
            "diagnostic_json_path": str(completed_4588_diag_path),
            "diagnostic_json_sha256": sha256_file(completed_4588_diag_path),
            "diagnostic_json": completed_4588_diag,
            "measurement_json_path": str(completed_4588_meas_path),
            "measurement_json_sha256": sha256_file(completed_4588_meas_path),
            "measurement_phases": completed_4588_meas["phases"],
            "measurement_open_call_rows": completed_4588_meas["open_call_rows"],
            "measurement_observed_reservation_windows": completed_4588_meas[
                "observed_reservation_windows"
            ],
        },
        "lead_d132_executed_rerun": {
            "once_claim_path": str(lead_once_claim_path),
            "once_claim_exists": os.path.lexists(lead_once_claim_path),
            "once_claim_sha256": sha256_file(lead_once_claim_path),
            "once_claim_content": read_json(lead_once_claim_path),
            "runner_script_path": str(lead_runner_sh_path),
            "runner_script_sha256": sha256_file(lead_runner_sh_path),
            "rearm_helper_path": str(lead_rearm_helper_path),
            "rearm_helper_sha256": sha256_file(lead_rearm_helper_path),
            "rearm_dir": str(lead_rearm_dir),
            "rearm_records": lead_rearm_records,
            "log_path": str(lead_log_path),
            "log_sha256": sha256_file(lead_log_path),
            "canary_dir": str(lead_canary_dir),
            "canary_supervisor_sha256": sha256_file(lead_canary_dir.with_suffix(".supervisor.json")),
            "rerun_dir": str(lead_rerun_dir),
            "supervisor_json_path": str(lead_rerun_sup_path),
            "supervisor_json_sha256": sha256_file(lead_rerun_sup_path),
            "outer_json_path": str(lead_rerun_outer_path),
            "outer_json_sha256": sha256_file(lead_rerun_outer_path),
            "outer_command": lead_rerun_outer["command"],
            "supervisor_returncode": lead_rerun_sup["returncode"],
            "supervisor_cleanup_verified": lead_rerun_sup["cleanup_verified"],
            "supervisor_forced_cleanup": lead_rerun_sup["forced_cleanup"],
            "supervisor_seconds": lead_rerun_sup["seconds"],
            "outer_host_contention": lead_rerun_outer["host_contention"],
            "diagnostic_json_path": str(lead_rerun_diag_path),
            "diagnostic_json_sha256": sha256_file(lead_rerun_diag_path),
            "diagnostic_json": lead_rerun_diag,
            "measurement_json_path": str(lead_rerun_meas_path),
            "measurement_json_sha256": sha256_file(lead_rerun_meas_path),
            "measurement_phases": lead_rerun_meas["phases"],
            "measurement_open_call_rows": lead_rerun_meas["open_call_rows"],
            "measurement_observed_reservation_windows": lead_rerun_meas[
                "observed_reservation_windows"
            ],
        },
        "current_host_load": {
            "load_1_5_15": [load1, load5, load15],
            "logical_cpus": logical_cpus,
            "one_minute_load_per_cpu": load1 / logical_cpus,
            "below_2_5_operator_gate": (load1 / logical_cpus) < 2.5,
        },
        "git_worktree_states": git_states,
    }

    raw_out = (json.dumps(facts, indent=2, sort_keys=True) + "\n").encode("utf-8")
    OUT_JSON.write_bytes(raw_out)
    print(json.dumps({"output": str(OUT_JSON), "sha256": sha256_bytes(raw_out), "bytes": len(raw_out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
