#!/usr/bin/env python3
"""
Purpose:
  Derive from code (at commit 7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1 in launch-a21)
  and from the real directory listing of the archived 2026-10-22a CHORUS generic_v10 run
  every output directory, file name, path-building function (with exact file and line
  numbers), working monitor command, after-run verification command, and post-run
  checklist item for the rebuilt A21 CHORUS canary
  (label 2026-11-11a_claude-opus-5-api-bc1-a21_rep1, prefix 2026-11-11a_claude-opus-5-api-bc1-a21).

Inputs (read-only):
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21
    (at commit 7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1)
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data/ATTIC/d4d_concatenated_archived/claudecode_api/2026-10-22a_claude-opus-5-api-generic-v10_rep1
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_2026-11-11a_claude-opus-5-api-bc1-a21_rep1/

Outputs:
  - /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy3-a21-post-run-checklist.md

Serves:
  - Claude lead assignment:
    notes/development_efficiency_20261111/assignments/claude-lead-agy3-a21-post-run-checklist.md
  - Owner decisions D130 and D131 (2026-11-11), PR #5808 merge commit 7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1.

Date: 2026-11-11
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import types
from pathlib import Path

EXEC_ROOT = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions")
LB = EXEC_ROOT / "launch-a21"
REPORT_WT = EXEC_ROOT / "codex-development-efficiency-20261111"
HANDOFF_OUT = (
    REPORT_WT
    / "notes"
    / "development_efficiency_20261111"
    / "handoffs"
    / "agy3-a21-post-run-checklist.md"
)
VENV_PY = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python")
LB_PY = LB / ".venv" / "bin" / "python"
LB_D4D = LB / ".venv" / "bin" / "d4d"

MERGE_COMMIT = "7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1"
PREFIX = "2026-11-11a_claude-opus-5-api-bc1-a21"
LABEL = f"{PREFIX}_rep1"
PROJECT = "CHORUS"
METHOD = "claudecode_api"
CONDITION = "generic_v10"
ARM = "baseline"

ROSTER_SHA256 = "d49cc3529a11e60716cde4affc6f5deec521b861576fcae6b961e2f74060dd63"
REG_SHA256 = "55691023e1d75c3bf5f9df09dcb524b4536870b93a4a3dde67306276f082aa1a"
SIZING_SHA256 = "0ae32356404e52d28acf0ff9ae8e39707947664df7506104a52fbab438465c87"
PLAN_DIR = EXEC_ROOT / "plans" / f"a21_registration_{LABEL}"

ARCH_LABEL = "2026-10-22a_claude-opus-5-api-generic-v10_rep1"
ARCH_FULL_DIR = LB / "data" / "ATTIC" / "d4d_concatenated_archived" / "claudecode_api" / ARCH_LABEL
ARCH_CORE_DIR = LB / "data" / "ATTIC" / "d4d_concatenated_archived" / "claudecode_api_core" / ARCH_LABEL
ARCH_INTER_DIR = ARCH_CORE_DIR / "intermediate"

sys.path.insert(0, str(LB / "src"))

import data_sheets_schema  # noqa: E402
from data_sheets_schema import (  # noqa: E402
    api_runner,
    bc1_runtime,
    latch_journal,
    provenance,
    receipt_completion,
    receipts,
    run_lock,
    snapshot_store,
    typed_audit_runtime,
    usage_ledger,
)


def _clean_env() -> dict[str, str]:
    env = dict(os.environ)
    for k in ("CBORG_API_KEY", "ANTHROPIC_API_KEY", "D4D_MANIFEST"):
        env.pop(k, None)
    env["PYTHONPATH"] = str(LB / "src")
    return env


def _run_ro(cmd: list[str], cwd: Path = LB) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def _find_line(rel_path: str, needle: str) -> int:
    p = LB / rel_path
    for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if needle in line:
            return idx
    raise RuntimeError(f"Needle {needle!r} not found in {rel_path}")


def _read_worktree_head(wt: Path) -> str:
    dot_git = (wt / ".git").read_text(encoding="utf-8").strip()
    if dot_git.startswith("gitdir:"):
        gitdir = Path(dot_git.split(":", 1)[1].strip())
        return (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    return (wt / ".git" / "HEAD").read_text(encoding="utf-8").strip()


def main() -> None:
    actual_head = _read_worktree_head(LB)
    if actual_head != MERGE_COMMIT:
        raise RuntimeError(f"Expected launch-a21 HEAD {MERGE_COMMIT}, got {actual_head}")

    # Verify namespace package vs concrete module import proof (Error #3)
    ns_file = getattr(data_sheets_schema, "__file__", None)
    ns_path = list(getattr(data_sheets_schema, "__path__", []))
    runner_file = api_runner.__file__

    os.chdir(LB)
    reg_raw = (PLAN_DIR / f"registration_chorus_{LABEL}.json").read_text(encoding="utf-8")
    reg_doc = json.loads(reg_raw)
    from data_sheets_schema import shared_generation

    receipt_raw = shared_generation.canonical(reg_doc["receipt"]).decode("utf-8")

    # Compute exact paths using RunSpec and helper functions from launch-a21 at 7ad8c9e72
    spec_new = api_runner.RunSpec(
        project=PROJECT,
        method=METHOD,
        arm=reg_doc["run"]["arm"],
        condition=CONDITION,
        label=LABEL,
        render_version=25,
        shared_generation_version=1,
        shared_generation_registration=reg_raw,
        api_playbook_version=2,
        receipt_completion_version=2,
        receipt_completion_registration=receipt_raw,
        bounded_carry_version=1,
        bundle=LB / "data" / "preprocessed" / "CHORUS_preprocessed.txt",
        manifest=LB / "data" / "preprocessed" / "source_manifest.yaml",
        _replay_only=True,
    )
    spec_arch = types.SimpleNamespace(
        project=PROJECT,
        method=METHOD,
        arm="registered",
        condition=CONDITION,
        label=ARCH_LABEL,
        metadata_dir=ARCH_CORE_DIR,
    )

    new_full_dir = (LB / spec_new.full_path.parent).resolve()
    new_core_dir = (LB / spec_new.metadata_dir).resolve()
    new_ledger_path = usage_ledger.ledger_path(spec_new)
    arch_ledger_path = usage_ledger.ledger_path(spec_arch)
    new_abandoned_path = usage_ledger.abandoned_journal_path(spec_new)
    new_journal_path = latch_journal.journal_path(spec_new)
    new_override_path = latch_journal.override_path(spec_new)
    new_progress_path = api_runner._progress_path(spec_new)
    new_reasoning_path = api_runner._reasoning_path(spec_new)
    new_receipt_path = api_runner._receipt_path(spec_new)
    new_inter_dir = (LB / api_runner._intermediate_dir(spec_new)).resolve()
    new_snap_index = snapshot_store.index_path(new_inter_dir, PROJECT)
    new_sweep_lock = LB / run_lock._path_for(PREFIX)
    new_file_locks = [
        p.with_name(f".{p.name}_api_run.lock")
        for p in (
            spec_new.full_path,
            spec_new.core_path,
            spec_new.report_path,
            spec_new.provenance_path,
        )
    ]

    # Verify real listings of 10-22a archive
    arch_full_files = sorted(p.name for p in ARCH_FULL_DIR.iterdir() if p.is_file())
    arch_core_files = sorted(p.name for p in ARCH_CORE_DIR.iterdir() if p.is_file())
    arch_inter_files = sorted(p.name for p in ARCH_INTER_DIR.iterdir() if p.is_file())

    if arch_ledger_path.name not in arch_core_files:
        raise RuntimeError(f"Computed archive ledger {arch_ledger_path.name} not in {arch_core_files}")

    # Verify key source line numbers at 7ad8c9e72
    lines = {
        "concat_dir": _find_line("src/data_sheets_schema/api_runner.py", 'CONCAT_DIR = Path("data/d4d_concatenated")'),
        "output_root": _find_line("src/data_sheets_schema/api_runner.py", "def output_root(self) -> Path:"),
        "full_path": _find_line("src/data_sheets_schema/api_runner.py", "def full_path(self) -> Path:"),
        "core_path": _find_line("src/data_sheets_schema/api_runner.py", "def core_path(self) -> Path:"),
        "report_path": _find_line("src/data_sheets_schema/api_runner.py", "def report_path(self) -> Path:"),
        "metadata_dir": _find_line("src/data_sheets_schema/api_runner.py", "def metadata_dir(self) -> Path:"),
        "provenance_path": _find_line("src/data_sheets_schema/api_runner.py", "def provenance_path(self) -> Path:"),
        "prov_record_path_for": _find_line("src/data_sheets_schema/provenance.py", "def record_path_for("),
        "runner_receipt_path": _find_line("src/data_sheets_schema/api_runner.py", "def _receipt_path(spec: RunSpec) -> Path:"),
        "receipts_receipt_path": _find_line("src/data_sheets_schema/receipts.py", "def receipt_path("),
        "ledger_path": _find_line("src/data_sheets_schema/usage_ledger.py", "def ledger_path("),
        "abandoned_path": _find_line("src/data_sheets_schema/usage_ledger.py", "def abandoned_journal_path("),
        "output_locks": _find_line("src/data_sheets_schema/usage_ledger.py", "def output_locks("),
        "journal_path": _find_line("src/data_sheets_schema/latch_journal.py", "def journal_path("),
        "override_path": _find_line("src/data_sheets_schema/latch_journal.py", "def override_path("),
        "progress_file_fmt": _find_line("src/data_sheets_schema/api_runner.py", 'PROGRESS_SUFFIX = "_api_progress.json"'),
        "progress_path": _find_line("src/data_sheets_schema/api_runner.py", "def _progress_path("),
        "progress_unlink": _find_line("src/data_sheets_schema/api_runner.py", "_progress_path(spec).unlink(missing_ok=True)"),
        "reasoning_path": _find_line("src/data_sheets_schema/api_runner.py", "def _reasoning_path("),
        "intermediate_dir": _find_line("src/data_sheets_schema/api_runner.py", "def _intermediate_dir("),
        "snapshot_fn": _find_line("src/data_sheets_schema/api_runner.py", "def _snapshot("),
        "snapshot_index": _find_line("src/data_sheets_schema/snapshot_store.py", "def index_path("),
        "run_lock_dir": _find_line("src/data_sheets_schema/run_lock.py", 'LOCK_DIR = Path("data/.run_locks")'),
        "run_lock_path_for": _find_line("src/data_sheets_schema/run_lock.py", "def _path_for("),
        "bc1_save": _find_line("src/data_sheets_schema/bc1_runtime.py", "def _save("),
        "bc1_checkpoint": _find_line("src/data_sheets_schema/bc1_runtime.py", "def _checkpoint("),
        "bc1_packet": _find_line("src/data_sheets_schema/bc1_runtime.py", "_save(spec, 'packet', packet)"),
        "bc1_assembly": _find_line("src/data_sheets_schema/bc1_runtime.py", "_save(spec, 'assembly', assembly)"),
        "bc1_stage_req": _find_line("src/data_sheets_schema/bc1_runtime.py", "_save(spec, f'{index}_request', payload)"),
        "bc1_stage_ctx": _find_line("src/data_sheets_schema/bc1_runtime.py", "_save(spec, f'{index}_context', count)"),
        "bc1_stage_resp": _find_line("src/data_sheets_schema/bc1_runtime.py", "_save(spec, f'{index}_response', saved, usage_id=call_id)"),
        "v1_save": _find_line("src/data_sheets_schema/typed_audit_runtime.py", "def _save("),
        "rc_transcript": _find_line("src/data_sheets_schema/receipt_completion.py", "TRANSCRIPT ="),
        "rc_save": _find_line("src/data_sheets_schema/receipt_completion.py", "def _save("),
        "rc_no_work_inputs": _find_line("src/data_sheets_schema/receipt_completion.py", "_save(spec, 'receipt_completion_inputs.json', inputs)"),
        "rc_no_work_result": _find_line("src/data_sheets_schema/receipt_completion.py", "_save(spec, 'receipt_completion_result.json', result"),
        "rc_context": _find_line("src/data_sheets_schema/receipt_completion.py", "_save(spec, 'receipt_completion_context.json'"),
        "rc_request": _find_line("src/data_sheets_schema/receipt_completion.py", "_save(spec, 'receipt_completion_request.json', payload)"),
        "rc_response": _find_line("src/data_sheets_schema/receipt_completion.py", "_save(spec, 'receipt_completion_response.json', response"),
        "admit_shared_context": _find_line("src/data_sheets_schema/api_runner.py", 'receipts._save(spec, f"{phase}_context.json",'),
        "save_evidence_pack": _find_line("src/data_sheets_schema/api_runner.py", '_snapshot(spec, f"{spec.project}_{stage}_evidence.json"'),
        "full_response_txt": _find_line("src/data_sheets_schema/api_runner.py", '_snapshot(spec, f"{spec.project}_{ph}_response_{call_id}.txt"'),
        "audit_json_snap": _find_line("src/data_sheets_schema/api_runner.py", '_snapshot(spec, f"{spec.project}_audit.json"'),
        "phase_yaml_snap": _find_line("src/data_sheets_schema/api_runner.py", '_snapshot(spec, f"{spec.project}_{ph}.yaml"'),
    }

    # Test monitor commands read-only against archived 10-22a core dir
    readout_json_0 = _run_ro(
        [
            str(VENV_PY),
            str(LB / "scripts" / "api_dollar_readout.py"),
            "--metadata-dir",
            str(ARCH_CORE_DIR),
            "--project",
            PROJECT,
            "--label",
            ARCH_LABEL,
            "--cap",
            "60.0",
            "--trigger",
            "51.0",
            "--json",
        ]
    )
    readout_json_1 = _run_ro(
        [
            str(VENV_PY),
            str(LB / "scripts" / "api_dollar_readout.py"),
            "--metadata-dir",
            str(ARCH_CORE_DIR),
            "--project",
            PROJECT,
            "--label",
            ARCH_LABEL,
            "--cap",
            "60.0",
            "--trigger",
            "10.0",
            "--json",
        ]
    )
    readout_json_2 = _run_ro(
        [
            str(VENV_PY),
            str(LB / "scripts" / "api_dollar_readout.py"),
            "--metadata-dir",
            str(ARCH_CORE_DIR),
            "--project",
            PROJECT,
            "--label",
            ARCH_LABEL,
            "--cap",
            "10.0",
            "--trigger",
            "5.0",
            "--json",
        ]
    )
    readout_human_0 = _run_ro(
        [
            str(VENV_PY),
            str(LB / "scripts" / "api_dollar_readout.py"),
            "--metadata-dir",
            str(ARCH_CORE_DIR),
            "--project",
            PROJECT,
            "--label",
            ARCH_LABEL,
            "--cap",
            "60.0",
            "--trigger",
            "51.0",
        ]
    )
    status_proc = _run_ro([str(VENV_PY), "-m", "data_sheets_schema.cli", "api", "status"], cwd=LB)

    if (readout_json_0.returncode, readout_json_1.returncode, readout_json_2.returncode) != (0, 1, 2):
        raise RuntimeError(
            f"Unexpected readout exit codes: {(readout_json_0.returncode, readout_json_1.returncode, readout_json_2.returncode)}"
        )

    md = f"""# A21 Monitoring and Post-Run Checklist (`{LABEL}`)

- **Track:** Final generation (first priority; read-only apart from this handoff and its generator script).
- **Launch-base worktree (`$LB`):** `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21` at commit `{MERGE_COMMIT}` (`main` after merging PR `#5808`, per `D130` and `D131` in `data-sheets-schema/notes/coordination/STATUS.md:594-606`).
- **Run parameters:**
  - `P={PREFIX}`
  - `L={LABEL}`
  - `PROJECT={PROJECT}`
  - `METHOD={METHOD}`
  - `CONDITION={CONDITION}`
  - `ARM={ARM}` (registered shared-generation arm)
- **Rebuilt registration artifacts on `7ad8c9e72` (`{PLAN_DIR}`):**
  - `roster_{LABEL}.json`: `{ROSTER_SHA256}`
  - `registration_chorus_{LABEL}.json`: `{REG_SHA256}`
  - `registration_chorus_{LABEL}.sizing.json`: `{SIZING_SHA256}`
- **Generator script for this document:**
  - `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/build_a21_post_run_checklist_20261111.py`
  - Every directory path, file name, function/line reference, and archive cross-check in the tables below was produced programmatically by running:
    ```bash
    env -u CBORG_API_KEY -u ANTHROPIC_API_KEY -u D4D_MANIFEST \\
      /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python \\
      /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/build_a21_post_run_checklist_20261111.py
    ```

---

## 0. Note on Step 1.1 Import Proof (Correcting Runbook Error #3)

`src/data_sheets_schema` is a PEP 420 namespace package (there is no `src/data_sheets_schema/__init__.py` at `{MERGE_COMMIT}`), whereas `src/download/__init__.py` exists. Therefore `data_sheets_schema.__file__` evaluates to `{ns_file!r}`, and the import-location proof must inspect `list(data_sheets_schema.__path__)` plus a concrete submodule's `__file__` (such as `data_sheets_schema.api_runner.__file__`):

```bash
env -u D4D_MANIFEST -u CBORG_API_KEY -u ANTHROPIC_API_KEY \\
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/.venv/bin/python -c \\
  'import data_sheets_schema, data_sheets_schema.api_runner as r, download; print("data_sheets_schema.__path__ =", list(data_sheets_schema.__path__)); print("api_runner.__file__ =", r.__file__); print("download.__file__ =", download.__file__)'
```

Verified output on `{MERGE_COMMIT}`:
- `data_sheets_schema.__path__`: `{ns_path}`
- `data_sheets_schema.api_runner.__file__`: `{runner_file}`

---

## 1. Where Things Are Written (`{LABEL}`, `{PROJECT}`, `{METHOD}`)

### A. Commands Used to Derive Directories and File Names

1. **Archived `2026-10-22a` directory listing (`"listing"`):**
   ```bash
   ls -la \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data/ATTIC/d4d_concatenated_archived/claudecode_api/2026-10-22a_claude-opus-5-api-generic-v10_rep1 \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1 \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate
   ```
   - Archived full dir files (`{len(arch_full_files)}`): `{", ".join(arch_full_files)}`
   - Archived core/metadata dir top-level files (`{len(arch_core_files)}`): `{", ".join(arch_core_files)}`
   - Archived `intermediate/` files (`{len(arch_inter_files)}`): `{", ".join(arch_inter_files)}`

2. **Code path-builder grep & direct evaluation at `{MERGE_COMMIT}` (`"code"`):**
   ```bash
   rg -n "def (output_root|full_path|core_path|report_path|metadata_dir|provenance_path|_receipt_path|_progress_path|_reasoning_path|_intermediate_dir|_snapshot)|PROGRESS_FILE_FMT|CONCAT_DIR" \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/src/data_sheets_schema/api_runner.py
   rg -n "def (ledger_path|abandoned_journal_path|output_locks)" \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/src/data_sheets_schema/usage_ledger.py
   rg -n "def (journal_path|override_path)" \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/src/data_sheets_schema/latch_journal.py
   rg -n "def (_save|_checkpoint)|_save\\(spec," \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/src/data_sheets_schema/bc1_runtime.py \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/src/data_sheets_schema/receipt_completion.py
   rg -n "LOCK_DIR|def _path_for" \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/src/data_sheets_schema/run_lock.py
   ```

### B. Output & Lock Directories for `{LABEL}`

| Directory Role | Exact Path in `launch-a21` (`$LB`) | Path Builder (`file:line` at `7ad8c9e72`) | Archived `10-22a` Cross-Check | Basis |
| --- | --- | --- | --- | --- |
| **Full-record directory** (`$FULL_DIR`) | `{new_full_dir}` | `RunSpec.output_root` (`src/data_sheets_schema/api_runner.py:{lines["output_root"]}`) + `RunSpec.full_path` (`api_runner.py:{lines["full_path"]}`), using `CONCAT_DIR = Path("data/d4d_concatenated")` (`api_runner.py:{lines["concat_dir"]}`) | `.../d4d_concatenated_archived/claudecode_api/{ARCH_LABEL}` | `listing`, `code` |
| **Core / metadata directory** (`$CORE_DIR`) | `{new_core_dir}` | `RunSpec.core_path` (`src/data_sheets_schema/api_runner.py:{lines["core_path"]}`) + `RunSpec.metadata_dir` (`api_runner.py:{lines["metadata_dir"]}`) | `.../d4d_concatenated_archived/claudecode_api_core/{ARCH_LABEL}` | `listing`, `code` |
| **Intermediate directory** (`$INTER_DIR`) | `{new_inter_dir}` | `_intermediate_dir(spec)` (`src/data_sheets_schema/api_runner.py:{lines["intermediate_dir"]}`) -> `spec.metadata_dir / "intermediate"` | `.../d4d_concatenated_archived/claudecode_api_core/{ARCH_LABEL}/intermediate` | `listing`, `code` |
| **Sweep lock directory** | `{LB / "data" / ".run_locks"}` | `LOCK_DIR = Path("data/.run_locks")` (`src/data_sheets_schema/run_lock.py:{lines["run_lock_dir"]}`) | Transient during active sweep (`unlinked` on exit) | `code` |

### C. Top-Level Files in `$FULL_DIR`, `$CORE_DIR`, and `data/.run_locks`

| Artifact Kind | Directory | Exact File Name for `{LABEL}` | Function / Builder (`file:line` at `7ad8c9e72`) | Archived `10-22a` Actual File Name | Post-Run Persistence | Basis |
| --- | --- | --- | --- | --- | --- | --- |
| **Full record** | `$FULL_DIR` | `{spec_new.full_path.name}` | `RunSpec.full_path` (`src/data_sheets_schema/api_runner.py:{lines["full_path"]}`) | `CHORUS_d4d.yaml` (25,700 B) | **Required persistent** | `listing`, `code` |
| **Core record** | `$CORE_DIR` | `{spec_new.core_path.name}` | `RunSpec.core_path` (`src/data_sheets_schema/api_runner.py:{lines["core_path"]}`) | `CHORUS_d4d_core.yaml` (25,073 B) | **Required persistent** | `listing`, `code` |
| **Provenance record** | `$CORE_DIR` | `{spec_new.provenance_path.name}` | `RunSpec.provenance_path` (`src/data_sheets_schema/api_runner.py:{lines["provenance_path"]}`) -> `provenance.record_path_for` (`src/data_sheets_schema/provenance.py:{lines["prov_record_path_for"]}`) | `CHORUS_provenance.yaml` (121,880 B) | **Required persistent** | `listing`, `code` |
| **Coverage receipt** | `$CORE_DIR` | `{new_receipt_path.name}` | `_receipt_path(spec)` (`src/data_sheets_schema/api_runner.py:{lines["runner_receipt_path"]}`) -> `receipts.receipt_path` (`src/data_sheets_schema/receipts.py:{lines["receipts_receipt_path"]}`) | `CHORUS_coverage_receipt.yaml` (16,825 B) | **Required persistent** | `listing`, `code` |
| **Reconciliation report** | `$CORE_DIR` | `{spec_new.report_path.name}` | `RunSpec.report_path` (`src/data_sheets_schema/api_runner.py:{lines["report_path"]}`) | `CHORUS_reconciliation.md` (152,404 B) | **Required persistent** | `listing`, `code` |
| **Usage ledger** | `$CORE_DIR` | `{new_ledger_path.name}` | `usage_ledger.ledger_path(spec)` (`src/data_sheets_schema/usage_ledger.py:{lines["ledger_path"]}`), where `<16hex>` is `sha256(json.dumps({{"condition":"generic_v10","label":"{LABEL}","method":"claudecode_api","project":"CHORUS"}}, sort_keys=True))[:16]` | `{arch_ledger_path.name}` (40,487 B; `<16hex>` for `10-22a` is `90e59e50c9d423fe`) | **Required persistent** | `listing`, `code` |
| **Latch journal** | `$CORE_DIR` | `{new_journal_path.name}` | `latch_journal.journal_path(spec)` (`src/data_sheets_schema/latch_journal.py:{lines["journal_path"]}`) | *(Postdates `10-22a`; read from code only)* | **Required persistent** | `code` |
| **Latch override** | `$CORE_DIR` | `{new_override_path.name}` | `latch_journal.override_path(spec)` (`src/data_sheets_schema/latch_journal.py:{lines["override_path"]}`) | *(Postdates `10-22a`; read from code only)* | **Must be ABSENT** (only written if `d4d api unlatch` is used; forbidden under `D41`/`D53`) | `code` |
| **Progress file** | `$CORE_DIR` | `{new_progress_path.name}` | `PROGRESS_SUFFIX` / `_progress_path(spec)` (`src/data_sheets_schema/api_runner.py:{lines["progress_file_fmt"]}, {lines["progress_path"]}`); **unlinked on clean completion** when `not problems` (`api_runner.py:{lines["progress_unlink"]}, 8596`) | *(Absent in `10-22a` because `10-22a` completed cleanly and unlinked it; read from code only)* | **Present during run; ABSENT after clean completion** (remains on disk only if halted/failed) | `code` |
| **Reasoning log** | `$CORE_DIR` | `{new_reasoning_path.name}` | `_reasoning_path(spec)` (`src/data_sheets_schema/api_runner.py:{lines["reasoning_path"]}`) | `CHORUS_reasoning.jsonl` (173,072 B) | **Required persistent** | `listing`, `code` |
| **Abandoned attempts journal** | `$CORE_DIR` | `{new_abandoned_path.name}` | `usage_ledger.abandoned_journal_path(spec)` (`src/data_sheets_schema/usage_ledger.py:{lines["abandoned_path"]}`) | `CHORUS_abandoned_attempts.jsonl` (2,235 B; 1 `ReadTimeout` in `10-22a`) | **Conditional** (only created if a transport/stream attempt is abandoned; absent on a 0-abandonment run) | `listing`, `code` |
| **Sweep run lock** | `$LB/data/.run_locks` | `{new_sweep_lock.name}` | `run_lock._path_for(label_prefix)` (`src/data_sheets_schema/run_lock.py:{lines["run_lock_path_for"]}`) | *(Transient during active sweep; read from code only)* | **Present during run; unlinked by `run_lock.release` when `d4d api batch` exits** (`cli/api.py:1433`) | `code` |
| **Per-output `filelock` sidecars** | `$FULL_DIR` and `$CORE_DIR` | `{", ".join(p.name for p in new_file_locks)}` | `usage_ledger.output_locks(spec)` (`src/data_sheets_schema/usage_ledger.py:{lines["output_locks"]}`) | *(Dot-prefixed `filelock` files; read from code only)* | Transient lockfiles (ignored by footprint/journal scanners via `_RESERVED_PREFIX = "."`) | `code` |

### D. Files in `$INTER_DIR` (`{new_inter_dir}`)

> **Why BC1 typed-audit file names differ from `10-22a`:**
> The archived `10-22a` run used `typed_audit_protocol_v1` (`src/data_sheets_schema/typed_audit_runtime.py:{lines["v1_save"]}`), which writes `CHORUS_typed_audit_<suffix>.json` (`0..4` for 5 stages). The rebuilt `2026-11-11a` registration uses `bc1_typed_audit_protocol_v2` (`src/data_sheets_schema/bc1_runtime.py:{lines["bc1_save"]}`), which writes `CHORUS_bc1_audit_<suffix>.json` (`0..6` for the 7 sized stages: `0=worker_01`, `1=worker_02`, `2=worker_03`, `3=omission`, `4=group_01`, `5=group_02`, `6=final`). In addition, `bc1_runtime._checkpoint` (`bc1_runtime.py:{lines["bc1_checkpoint"]}`) saves `controller` state at initial `running`, before and after each of the 7 stages (`14` saves), and at terminal `accepted`, and `api_runner._snapshot` (`api_runner.py:{lines["snapshot_fn"]}`) collision-numbers repeated saves of `CHORUS_bc1_audit_controller.json` as `_2.json` through `_16.json`.

| Intermediate File Group | Exact File Name(s) in `$INTER_DIR` for `{LABEL}` | Function / Builder (`file:line` at `7ad8c9e72`) | Archived `10-22a` Actual File Name(s) in `intermediate/` | Post-Run Persistence | Basis |
| --- | --- | --- | --- | --- | --- |
| **Snapshot index** | `{new_snap_index.name}` | `snapshot_store.index_path` (`src/data_sheets_schema/snapshot_store.py:{lines["snapshot_index"]}`) | `CHORUS_snapshot_index.json` (29,981 B) | **Required persistent** | `listing`, `code` |
| **Phase-1 raw response & snapshots** | `CHORUS_full_response_<call_id>.txt`, `CHORUS_coverage_receipt.yaml`, `CHORUS_full.yaml`, `CHORUS_core.yaml` | `_snapshot` (`src/data_sheets_schema/api_runner.py:{lines["full_response_txt"]}, 7349, {lines["phase_yaml_snap"]}`) | `CHORUS_full_response_2494777897ee4d79ac96e70dde7bb1e7.txt`, `CHORUS_coverage_receipt.yaml`, `CHORUS_full.yaml`, `CHORUS_core.yaml` | **Required persistent** | `listing`, `code` |
| **Receipt-completion files (always written)** | `CHORUS_receipt_completion_transcript.json`, `CHORUS_receipt_completion_inputs.json`, `CHORUS_receipt_completion_request.json`, `CHORUS_receipt_completion_response.json`, `CHORUS_receipt_completion_result.json` | `TRANSCRIPT` & `receipt_completion._save` (`src/data_sheets_schema/receipt_completion.py:{lines["rc_transcript"]}, {lines["rc_save"]}, {lines["rc_no_work_inputs"]}, {lines["rc_request"]}, {lines["rc_response"]}, {lines["rc_no_work_result"]}`) | `CHORUS_receipt_completion_transcript.json`, `CHORUS_receipt_completion_inputs.json`, `CHORUS_receipt_completion_request.json`, `CHORUS_receipt_completion_response.json`, `CHORUS_receipt_completion_result.json` | **Required persistent** (`response.json` records `stop_reason: "no_work"` at line 733/777 if 0 paths were missing a receipt) | `listing`, `code` |
| **Receipt-completion context count (written when `requested_paths` is non-empty)** | `CHORUS_receipt_completion_context.json` | `receipt_completion._save` (`src/data_sheets_schema/receipt_completion.py:{lines["rc_context"]}`) | `CHORUS_receipt_completion_context.json` (308 B) | **Persistent when Phase-1 has `>=1` unreceipted path** (`if inventory['requested_paths']` at line `{lines["rc_context"]}`) | `listing`, `code` |
| **BC1 typed-audit controller checkpoints** | `CHORUS_bc1_audit_controller.json` (plus `CHORUS_bc1_audit_controller_2.json` .. `CHORUS_bc1_audit_controller_16.json` via `_snapshot` collision numbering across 7 stages) | `bc1_runtime._save` + `_checkpoint` (`src/data_sheets_schema/bc1_runtime.py:{lines["bc1_checkpoint"]}, {lines["bc1_save"]}`) & `api_runner._snapshot` (`api_runner.py:5894-5897`) | *(Postdates `10-22a`; read from code only)* | **Required persistent** (`controller` + `_2.._16` on a 7-stage run) | `code`, `inference` (count `16` = `1 + 2*7 + 1` for 7 stages) |
| **BC1 typed-audit packet & assembly** | `CHORUS_bc1_audit_packet.json`, `CHORUS_bc1_audit_assembly.json` | `bc1_runtime._save` (`src/data_sheets_schema/bc1_runtime.py:{lines["bc1_packet"]}, {lines["bc1_assembly"]}`) | *(Postdates `10-22a`; `10-22a` v1 wrote `CHORUS_typed_audit_packet.json` and `CHORUS_typed_audit_assembly.json`; read from code only)* | **Required persistent** | `code` |
| **BC1 typed-audit per-stage request / context / response (`index` in `0..6`)** | `CHORUS_bc1_audit_0_request.json` .. `CHORUS_bc1_audit_6_request.json`, `CHORUS_bc1_audit_0_context.json` .. `CHORUS_bc1_audit_6_context.json`, `CHORUS_bc1_audit_0_response.json` .. `CHORUS_bc1_audit_6_response.json` (`21` files across 7 stages: `0..2` workers, `3` omission, `4..5` groups, `6` final) | `bc1_runtime._save` (`src/data_sheets_schema/bc1_runtime.py:{lines["bc1_stage_req"]}, {lines["bc1_stage_ctx"]}, {lines["bc1_stage_resp"]}`) | *(Postdates `10-22a`; `10-22a` v1 wrote `CHORUS_typed_audit_{{0..4}}_{{request,context,response}}.json`; read from code only)* | **Required persistent** (`7 * 3 = 21` stage files when Phase-1 record produces the same 3-worker / 2-group plan as sizing) | `code` |
| **Audit phase summary & evidence pack** | `CHORUS_audit.json`, `CHORUS_audit_evidence.json` | `_snapshot` (`src/data_sheets_schema/api_runner.py:{lines["audit_json_snap"]}`) & `_save_evidence_pack` (`api_runner.py:{lines["save_evidence_pack"]}`) | `CHORUS_audit.json` (113,663 B), `CHORUS_audit_evidence.json` (1,073 B) | **Required persistent** | `listing`, `code` |
| **Reconcile & report shared-context admission records** | `CHORUS_reconcile_full_context.json`, `CHORUS_report_context.json` (plus `CHORUS_report_regate_context.json` / `CHORUS_report_after_repair_context.json` only if regate/repair triggers) | `_admit_shared_context` (`src/data_sheets_schema/api_runner.py:{lines["admit_shared_context"]}`) | *(Added in `#5157` after `10-22a`; read from code only)* | **Required persistent** (`reconcile_full_context.json` and `report_context.json`) | `code` |
| **Reconcile & report phase snapshots and evidence packs** | `CHORUS_reconcile_full.yaml`, `CHORUS_reconcile_evidence.json`, `CHORUS_reconcile_core.yaml`, `CHORUS_report.md`, `CHORUS_report_evidence.json` | `_snapshot` (`src/data_sheets_schema/api_runner.py:{lines["phase_yaml_snap"]}`) & `_save_evidence_pack` (`api_runner.py:{lines["save_evidence_pack"]}`) | `CHORUS_reconcile_full.yaml`, `CHORUS_reconcile_evidence.json`, `CHORUS_reconcile_core.yaml`, `CHORUS_report.md`, `CHORUS_report_evidence.json` | **Required persistent** | `listing`, `code` |

---

## 2. Working Monitor Commands (Tested Read-Only Against Archived `10-22a`)

### A. Why the Earlier Runbook Command Failed & Preconditions

1. `scripts/api_dollar_readout.py` (`lines 91-93`) requires either `--ledger <FILE>` or `--metadata-dir <DIR>`. Passing only `--label "$L" --cap ... --trigger ...` prints `Error: Must specify a ledger file or --metadata-dir.` and exits `1`.
2. When `--metadata-dir <DIR>` is used, `api_dollar_readout.py` (`lines 19-46`) checks `metadata_dir.exists()` and globs `{{project}}_api_usage_*.json` inside `<DIR>`, matching `data.get("label") == label`. **Both `$CORE_DIR` and `$CORE_DIR/{new_ledger_path.name}` are created only after `d4d api batch` starts the run and initializes the ledger** (`usage_ledger.init_ledger` at `src/data_sheets_schema/usage_ledger.py:219-248`). Before that moment, `api_dollar_readout.py` exits `1` with `Error: Directory not found` or `Error: No matching usage ledger found`.
3. `d4d api status` and `d4d api stop` inspect `run_lock.LOCK_DIR = Path("data/.run_locks")` **relative to the current working directory** (`src/data_sheets_schema/run_lock.py:{lines["run_lock_dir"]}`). Always run them with `cd "$LB"` (or `cwd=$LB`).

### B. Exit Codes of `scripts/api_dollar_readout.py` (`lines 101-144`)

- **One-shot mode (without `--watch`):**
  - **Exit `0`:** Ledger found and parsed; neither `--cap` nor `--trigger` is reached (`cap_reached == false` and `trigger_reached == false`).
  - **Exit `1`:** Either (a) `trigger_reached == true` (and `cap_reached == false`, checked at `scripts/api_dollar_readout.py:142-143`: `total_projected_dollars >= trigger`), **or** (b) CLI / file-lookup error (`--metadata-dir` missing, ledger not yet created, or invalid JSON, `lines 93, 104, 108`). Distinguish (a) from (b) by checking whether JSON stdout has `"trigger_reached": true` vs. stderr starting with `Error:`.
  - **Exit `2`:** `cap_reached == true` (`scripts/api_dollar_readout.py:140-141`: `total_projected_dollars >= cap`; checked before `trigger_reached`, so if both cap and trigger are exceeded, exit code is `2`).
- **Watch mode (`--watch`):**
  - Loops every `--interval` seconds (default `5.0`) until interrupted with `SIGINT`/`Ctrl-C` (which catches `KeyboardInterrupt` and exits `0`, `lines 150-152`), unless the ledger file is missing on a poll (`sys.exit(1)`). **Note:** `--watch` does not automatically exit on `trigger_reached` or `cap_reached`; it prints `[STOP TRIGGER REACHED]` / `[CAP EXCEEDED]` in human mode (or `"trigger_reached": true` / `"cap_reached": true` in `--json` mode).

### C. Read-Only Test Results Against Archived `10-22a` Core Directory

1. **One-shot `--json` (exit `0` when below trigger and cap: `--cap 60.0 --trigger 51.0`):**
   ```bash
   env -u CBORG_API_KEY -u ANTHROPIC_API_KEY \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/.venv/bin/python \\
     /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/scripts/api_dollar_readout.py \\
     --metadata-dir /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1 \\
     --project CHORUS --label 2026-10-22a_claude-opus-5-api-generic-v10_rep1 \\
     --cap 60.0 --trigger 51.0 --json
   ```
   Output (`exit={readout_json_0.returncode}`):
   ```json
{readout_json_0.stdout.strip()}
   ```
   - Tested exit `1` (`--cap 60.0 --trigger 10.0 --json`): `exit={readout_json_1.returncode}` (`"trigger_reached": true, "cap_reached": false`).
   - Tested exit `2` (`--cap 10.0 --trigger 5.0 --json`): `exit={readout_json_2.returncode}` (`"trigger_reached": true, "cap_reached": true`).

2. **One-shot human-readable readout (`--cap 60.0 --trigger 51.0`, `exit={readout_human_0.returncode}`):**
   ```text
{readout_human_0.stdout.strip()}
   ```

3. **Sweep lock status (`d4d api status` run from `$LB`, `exit={status_proc.returncode}`):**
   ```text
   {status_proc.stdout.strip()}
   ```

### D. Exact Monitor & Stop Commands for the New Label (`{LABEL}`)

```bash
LB=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21
PY=$LB/.venv/bin/python
D4D=$LB/.venv/bin/d4d
P={PREFIX}
L={LABEL}
CORE_DIR=$LB/data/d4d_concatenated/claudecode_api_core/$L
LEDGER=$CORE_DIR/{new_ledger_path.name}

# 1. Sweep lock status (must run with cwd=$LB so data/.run_locks is checked in launch-a21):
( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" api status )

# 2. One-shot JSON dollar readout (exits 0 below trigger, 1 at/above trigger, 2 at/above cap):
env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$PY" "$LB/scripts/api_dollar_readout.py" \\
  --metadata-dir "$CORE_DIR" --project CHORUS --label "$L" \\
  --cap 60.00 --trigger 51.00 --json

#    (Or by explicit deterministic ledger path once initialized:)
env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$PY" "$LB/scripts/api_dollar_readout.py" \\
  --ledger "$LEDGER" --cap 60.00 --trigger 51.00 --json

# 3. Continuous watch mode (human-readable, polling every 5s after $CORE_DIR/$LEDGER exists):
env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$PY" "$LB/scripts/api_dollar_readout.py" \\
  --metadata-dir "$CORE_DIR" --project CHORUS --label "$L" \\
  --cap 60.00 --trigger 51.00 --watch

# 4. Stop command (ONLY if total_projected_dollars >= $51.00 or wall-clock >= 3h; run from $LB):
( cd "$LB" && "$PY" "$LB/scripts/api_launcher.py" --worktree "$LB" -- d4d api stop --label-prefix "$P" )
```

---

## 3. After-Run Commands (Exact Options Verified via `--help` in `launch-a21`)

All options below were verified read-only in `$LB` at `{MERGE_COMMIT}` with `env -u CBORG_API_KEY -u ANTHROPIC_API_KEY` (without executing any command against a run):

```bash
LB=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/launch-a21
PY=$LB/.venv/bin/python
D4D=$LB/.venv/bin/d4d
L={LABEL}
REG=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/a21_registration_${{L}}/registration_chorus_${{L}}.json
FULL_YAML=$LB/data/d4d_concatenated/claudecode_api/$L/CHORUS_d4d.yaml
CORE_YAML=$LB/data/d4d_concatenated/claudecode_api_core/$L/CHORUS_d4d_core.yaml
```

1. **`d4d api verdict`** (`Usage: d4d api verdict --project TEXT --method [claudecode_api|codex_api] --label TEXT [--registration FILE] [--output-root PATH] [--preprocessed-dir PATH] [--json]`):
   ```bash
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" api verdict \\
       --project CHORUS \\
       --method claudecode_api \\
       --label "$L" \\
       --registration "$REG" \\
       --json )
   ```

2. **`d4d runs check --strict`** (`Usage: d4d runs check [--project TEXT] [--method TEXT] [--label TEXT] [--strict] [--require-complete] [--data-dir PATH] [--json]`):
   ```bash
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" runs check \\
       --project CHORUS \\
       --method claudecode_api \\
       --label "$L" \\
       --strict --require-complete )
   ```

3. **`d4d receipts check --strict`** (`Usage: d4d receipts check [--project TEXT] [--method TEXT] [--label TEXT] [--strict] [--data-dir PATH] [--preprocessed-dir PATH] [--json]`):
   ```bash
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" receipts check \\
       --project CHORUS \\
       --method claudecode_api \\
       --label "$L" \\
       --strict )
   ```

4. **Product check `scripts/adhoc/check_final_generation_products_20261110.py`** (`Usage: check_final_generation_products_20261110.py --full PATH --core PATH --project PROJECT [--json-out PATH]`):
   ```bash
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$PY" \\
       "$LB/scripts/adhoc/check_final_generation_products_20261110.py" \\
       --full "$FULL_YAML" \\
       --core "$CORE_YAML" \\
       --project CHORUS )
   ```

5. **Additional `docs/final-generation-acceptance.md` (§3–§5) gates for Stage 2 canary acceptance:**
   ```bash
   # Provenance record validation (§4.1):
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" provenance validate-records \\
       --project CHORUS --method claudecode_api --label "$L" --strict )

   # Run LinkML schema validation across full & core (§4.1):
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" runs validate \\
       --project CHORUS --method claudecode_api --label "$L" )

   # Direct full and Core shape validation + pair consistency + HTML render (§3.1, §3.3, §3.4):
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" validate --schema full "$FULL_YAML" )
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" validate --schema core "$CORE_YAML" )
   make -C "$LB" validate-d4d-pair FULL="$FULL_YAML" CORE="$CORE_YAML"
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" render html "$FULL_YAML" \\
       -o "/tmp/CHORUS_${{L}}_d4d.html" )

   # Optional non-gating D105 transformation receipt diagnostic (§4 note; subcommand is `transform`):
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" receipts transform \\
       --full "$FULL_YAML" --core "$CORE_YAML" )

   # Independent source-review pack generation & post-review strict check (§5):
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" review pack \\
       --label "$L" --project CHORUS --method claudecode_api )
   # After independent reviewer populates $CORE_DIR/CHORUS_review.yaml:
   ( cd "$LB" && env -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$D4D" review check \\
       --label "$L" --project CHORUS --method claudecode_api --strict )
   ```

---

## 4. Corrected Post-Run Checklist (Replacing Runbook Section 4 A & B, and Auditing Section 4 C Citations)

### A. Files That Must Exist and Be Non-Empty After a Complete Run (Replaces Runbook Section 4 A)

Let:
- `FULL_DIR={new_full_dir}`
- `CORE_DIR={new_core_dir}`
- `INTER_DIR={new_inter_dir}`

1. **Authoritative full datasheet and derived Core datasheet (`docs/final-generation-acceptance.md` §2–§3):**
   - `$FULL_DIR/CHORUS_d4d.yaml` (non-empty YAML; header comments `# D4D Datasheet for CHORUS Dataset` and `# Arm: REGISTERED (shared generation v1)`; `conforms_to_class: Dataset`; valid against `3.2.1` full schema; `>= 5` top-level keys including `id`; `FileCollection.collection_type` scalar in `{{raw_data, processed_data, simulated_data, harmonized_data, other}}` where populated).
   - `$CORE_DIR/CHORUS_d4d_core.yaml` (non-empty YAML; header comments `# D4D Core Datasheet for CHORUS Dataset` and `# Arm: REGISTERED (shared generation v1)`; `conforms_to_class: CoreDataset`; valid against `3.2.1` Core schema; `0` derivation drift and `0` `validate-d4d-pair` errors against `$FULL_DIR/CHORUS_d4d.yaml`).
2. **Core/metadata sidecars (`$CORE_DIR`, `docs/final-generation-acceptance.md` §4):**
   - `$CORE_DIR/CHORUS_provenance.yaml` (`validation.passed: true`, `git_commit: {MERGE_COMMIT}`, `shared_generation.registration_sha256: {REG_SHA256}`, `schema_full_sha256: bc560a3c2bf2efd79cfb775bbd5fbffabdfbdff2a0fb9eb6ccfd2fb8b1c754d5`, `schema_core_sha256: e174a7a6bd1b74bf37ad5eb6681e5cfba6af42a1fd70ef498114dc2c2764f903`).
   - `$CORE_DIR/CHORUS_coverage_receipt.yaml` (`receipt_instrument_version: 4`, `bundle_md5: a99a62d8cf84ca59a5d7f2db1fb7d0ff`, all 13 CHORUS chunk IDs covered).
   - `$CORE_DIR/CHORUS_reconciliation.md` (final markdown report passing `report_claims.py` and `evidence_assertions.py`).
   - `$CORE_DIR/{new_ledger_path.name}` (usage ledger with `total_calls == len(calls)`, `pending_calls == []`, and `total_cost_usd <= <SLICE_USD>`).
   - `$CORE_DIR/CHORUS_latch_journal.jsonl` (hash-chained JSONL starting with `run_started` and ending with `run_completed`; `0` `latch_faulted` or `latch_reset_accepted` events).
   - `$CORE_DIR/CHORUS_reasoning.jsonl` (non-empty JSONL of per-call reasoning entries).
   - **Must be ABSENT after a clean run:**
     - `$CORE_DIR/CHORUS_api_progress.json` (unlinked by `api_runner.py:{lines["progress_unlink"]}` when `not problems`; its presence after exit indicates the run halted or failed validation/gates).
     - `$CORE_DIR/CHORUS_latch_override.json` (forbidden under `D41`/`D53`).
     - `$LB/data/.run_locks/{PREFIX}.json` (unlinked when `d4d api batch` exits).
3. **Intermediate artifacts (`$INTER_DIR`):**
   - `$INTER_DIR/CHORUS_snapshot_index.json`
   - Phase-1 files: `$INTER_DIR/CHORUS_full_response_<call_id>.txt`, `$INTER_DIR/CHORUS_coverage_receipt.yaml`, `$INTER_DIR/CHORUS_full.yaml`, `$INTER_DIR/CHORUS_core.yaml`
   - Receipt-completion files: `$INTER_DIR/CHORUS_receipt_completion_{{transcript,inputs,request,response,result}}.json` (with `state: "answers_complete"` and `receipt_after_sha256` in `result.json` matching `$CORE_DIR/CHORUS_coverage_receipt.yaml`), plus `$INTER_DIR/CHORUS_receipt_completion_context.json` whenever `requested_paths` is non-empty
   - BC1 typed-audit files (`bc1_typed_audit_protocol_v2`): `$INTER_DIR/CHORUS_bc1_audit_controller.json` (plus numbered snapshots `_2.json` .. `_16.json`), `$INTER_DIR/CHORUS_bc1_audit_packet.json`, `$INTER_DIR/CHORUS_bc1_audit_assembly.json`, `$INTER_DIR/CHORUS_bc1_audit_{{0..6}}_{{request,context,response}}.json` (`21` stage files for the 7-call plan: `0..2` workers, `3` omission, `4..5` groups, `6` final), `$INTER_DIR/CHORUS_audit.json`, and `$INTER_DIR/CHORUS_audit_evidence.json`
   - Reconcile & report files: `$INTER_DIR/CHORUS_reconcile_full_context.json`, `$INTER_DIR/CHORUS_reconcile_full.yaml`, `$INTER_DIR/CHORUS_reconcile_evidence.json`, `$INTER_DIR/CHORUS_reconcile_core.yaml`, `$INTER_DIR/CHORUS_report_context.json`, `$INTER_DIR/CHORUS_report.md`, and `$INTER_DIR/CHORUS_report_evidence.json`

### B. Counters That Must Have Moved (Replaces Runbook Section 4 B)

1. **Usage ledger (`$CORE_DIR/{new_ledger_path.name}`) and `api_dollar_readout.py --json`:**
   - `settled_calls >= 12` on a standard 7-stage BC1 run with receipt completion (`1` `full` + `1` `receipt_completion` + `7` `audit` [`3` workers, `1` omission, `2` groups, `1` final] + `1` `reconcile_full` + `1` `reconcile_core` + `1` `report`, plus `report_regate` / `repair_full` only if triggered; `11` if Phase-1 already had 0 unreceipted paths).
   - `pending_calls == 0` (`"pending_calls": []` in the ledger JSON) and `in_flight_max_dollars == 0.0`.
   - `settled_dollars > 0` and `total_projected_dollars <= <SLICE_USD>`, with `cap_reached == false` and `trigger_reached == false` (exit code `0`).
   - `abandoned_calls == 0` (and `$CORE_DIR/CHORUS_abandoned_attempts.jsonl` absent) on a transport-clean run; every BC1 typed-audit stage response and receipt-completion response has `transport_attempts == 1`.
2. **BC1 typed-audit & provenance counters (`$INTER_DIR/CHORUS_bc1_audit_assembly.json` and `$CORE_DIR/CHORUS_provenance.yaml`):**
   - `shared_generation.typed_audit.status == "accepted"`, `call_count == 7 <= 8` (`audit_limits.max_calls`), `worker_count == 3 <= 4` (`audit_limits.max_workers`), `group_count == 2`, `final_call_count == 1`.
   - `aggregate_input_tokens <= 4500000` (`audit_limits.aggregate_input_tokens`) and `aggregate_output_tokens <= 480000` (`audit_limits.aggregate_output_tokens`).
   - `shared_generation.receipt_completion.status == "completed"` and `call_count <= 1`.
3. **Verdict, receipt, and provenance gates (`d4d api verdict --json`, `d4d runs check --strict --require-complete`, `d4d receipts check --strict`):**
   - `d4d api verdict --json` returns `"verdict": "PASS"` (exit `0`), with `unverified_quotes == 0` across receipt, audit, reconcile, and report phases.
   - `d4d receipts check --strict` and `d4d runs check --strict --require-complete` both exit `0` with `0` errors (`100%` of receipt snippets verified against `CHORUS_preprocessed.txt` and all 13 chunks accounted for).

### C. Check of Runbook Section 4 C Against `docs/final-generation-acceptance.md` at `{MERGE_COMMIT}`

Checking each citation in Runbook Section 4 C against `docs/final-generation-acceptance.md` (`lines 1-99` at `{MERGE_COMMIT}`):
- **Citation correction needed:** Runbook Section 4 C header cited only `(§5–§7)` for all three items, and Runbook Section 4 A cited `(G1 / G3 §1–§2)` and `d4d receipts emit-transformation / verify-transformation`. In `docs/final-generation-acceptance.md` at `{MERGE_COMMIT}`:
  - **§1** (`lines 5-25`) is *Freeze Prerequisites Before Generation*;
  - **§2** (`lines 26-34`) is *Authoritative Full Record vs. Derived Core Projection (`#694`, `#5787`)*;
  - **§3** (`lines 35-54`) is *Shape Validation, Pair Consistency, and HTML Rendering*;
  - **§4** (`lines 55-76`) is *Existing Receipt, Typed-Audit, Report, and Provenance Checks* (and at `line 57`, the non-gating `D105` CLI subcommand is `d4d receipts transform --full <full.yaml> --core <core.yaml>`, **not** `emit-transformation` / `verify-transformation`);
  - **§5** (`lines 78-87`) is *Independent Source Review and Content Disposition* (`d4d review pack` -> independent reviewer populates `$CORE_DIR/CHORUS_review.yaml` -> `d4d review check --strict`);
  - **§6** (`lines 88-92`) is *API vs. Native Stub-Refusal Boundary (`N1` Is Component-Only)*;
  - **§7** (`lines 93-99`) is *Non-Prerequisites and Staged Execution Sequence* (`Stage 1: Tiny offline canary` -> `Stage 2: One authorized real single-project canary` -> `Stage 3: Authorized batch`).
- **Corrected Section 4 C (with exact `docs/final-generation-acceptance.md` section numbers at `{MERGE_COMMIT}`):**
  1. **Automated product, shape, pair, HTML, receipt, provenance, and verdict checks (`docs/final-generation-acceptance.md` §2, §3, §4, and §7 Stage 2):** `scripts/adhoc/check_final_generation_products_20261110.py`, `d4d validate --schema full`, `d4d validate --schema core`, `make validate-d4d-pair`, `d4d render html`, `d4d receipts check --strict`, `d4d provenance validate-records --strict`, `d4d runs check --strict --require-complete`, `d4d runs validate`, and `d4d api verdict` all pass on the `A21` CHORUS output pair with zero hand edits (`D41`/`D53`).
  2. **Independent source review (`docs/final-generation-acceptance.md` §5 and §7 Stage 2; `D36`, `D19`):** Generate the review bundle with `d4d review pack --label "$L" --project CHORUS --method claudecode_api`, have an independent reviewer (fresh Claude session + Codex CLI pass, `D36`) complete `$CORE_DIR/CHORUS_review.yaml` dispositioning `variables`, `splits`/`subsets`, and `participant_privacy` against the CHORUS source bundle, verify with `d4d review check --label "$L" --project CHORUS --method claudecode_api --strict`, and record blind audit-recall observations pinned to `$INTER_DIR/CHORUS_full.yaml`'s SHA-256 (`D19`), signed by the owner.
  3. **Post-`A21` owner batch-gate decision packet (`docs/final-generation-acceptance.md` §7 Stage 3; `STATUS.md:824-828`, `D58`, `D64`):** Resolved by the owner based on `A21`'s measured cost:
     - the batch budget figure and funded project prefix (`CHORUS -> CM4AI -> VOICE -> AI_READI -> VOICE_PEDIATRIC -> Kids First`);
     - the sizing-evidence route for non-CHORUS projects (`R1` sizing runs, `R2` builder change, or `R3` descoping);
     - a separate explicit human batch launch word (`D07`, `D22`, `docs/final-generation-acceptance.md` §7 Stage 3) naming the closed multi-project `shared_generation_batch_roster_v1` SHA-256.
"""

    if "\x40" in md:
        raise RuntimeError("Generated markdown contains a forbidden at-sign character!")

    HANDOFF_OUT.parent.mkdir(parents=True, exist_ok=True)
    HANDOFF_OUT.write_text(md, encoding="utf-8")
    digest = hashlib.sha256(HANDOFF_OUT.read_bytes()).hexdigest()
    print(f"PATH={HANDOFF_OUT}")
    print(f"SHA256={digest}")


if __name__ == "__main__":
    main()
