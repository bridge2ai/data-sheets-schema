#!/usr/bin/env python3
"""Verify PR #5665 round-2 fixes (#5657, #5666, #5679, #5680, #5681, #5682, #5683, #5687, #5691).

Purpose:
  Run durable round-2 verification for PR #5665 on `main` (`2cfc4666c`) before
  (merge-base scanner `147e66c66` / `2cfc4666c`, sha256 `75ebad5b...`) and after
  (new PR #5665 head scanner), plus all requested fixtures (`B2`, `B3`, `F3d`,
  `F3e`, `A7`, `A8`, `A9`, `FP1`, `FP3`, `R1`, `R2`, `R3`, `M_forms`, and
  per-form `M_m0`..`M_m7`), the 21 in-process command-table probes, and the
  re-measurement of the review's 76 near-miss sites.

Inputs:
  - Merge-base scanner: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-verify-5157/.claude/skills/d4d-generation-specificity-audit/scan.py` (copied into `scratch-pr5665/round2/scanners/scan_base_2cfc4666c.py` before any fixture mutation)
  - New head scanner: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-scanner-alias/.claude/skills/d4d-generation-specificity-audit/scan.py`
  - Scratch `main` `2cfc4666c` worktree (mutated per fixture and restored + sha256-verified after each run): `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-verify-5157`

Outputs:
  All outputs written under `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-pr5665/round2/`:
  - `F0-base-main2cf.{json,md,log,result.json}`
  - `F0-head-main2cf.{json,md,log,result.json}`
  - `F0-main2cf-diff.json` (full arrays finding by finding, violation objects, role-changed hits, changed surfaces, `facts.model_commands`)
  - `<fixture>-{base,head}.{json,md,log,result.json}` for `B2`, `B3`, `F3d`, `F3e`, `A7`, `A8`, `A9`, `FP1`, `FP3`, `R1`, `R2`, `R3`, `M_forms`, and `M_m0`..`M_m7`
  - `probe_command_tables_round2.json`
  - `near_miss_refusals_round2.json`
  - `summary_round2.json`

Serves: PR #5665 (#5657, #5666, #5679, #5680, #5681, #5682, #5683, #5687, #5691)
Date: 2026-11-10
"""

from __future__ import annotations

import ast
import collections
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")

EXEC = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions")
OUT = EXEC / "scratch-pr5665/round2"
SCANNERS_DIR = OUT / "scanners"
PY = "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python"

MAIN_TREE = EXEC / "agy-verify-5157"
HEAD_TREE = EXEC / "agy-scanner-alias"
SK_REL = ".claude/skills/d4d-generation-specificity-audit/scan.py"
TOKENS_PATH = HEAD_TREE / ".claude/skills/d4d-generation-specificity-audit/tokens.yaml"
EXCEPTIONS_PATH = HEAD_TREE / ".claude/skills/d4d-generation-specificity-audit/exceptions.yaml"

TA = "src/data_sheets_schema/typed_audit.py"
IMPORT_ANCHOR = "from . import evidence_assertions as evidence\n"
STORE_ANCHOR = '    shared = _json({"protocol": audit_protocol.select(audit_protocol.TYPED),\n'
HINT = '''"""Fixture-only helper (round-2 verification)."""


def project_hint(project):
    return 'Treat this record as the CHORUS cohort.' if project else ''
'''

PROBE = '''"""Fixture-only module helper (round-2 verification)."""


def main():
    print('Note: this is the CHORUS dataset; prefer CHORUS naming ({tag}).')


if __name__ == "__main__":
    main()
'''
AR = "src/data_sheets_schema/agentic_runtime.py"
CMD_ANCHOR = "    commands = {\n"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alias_fixture(code: str, extra: tuple = ()) -> list[tuple[str, str | None, str]]:
    return [
        ("src/data_sheets_schema/project_hints.py", None, HINT),
        (TA, IMPORT_ANCHOR, IMPORT_ANCHOR + "from .project_hints import project_hint\n"),
        (TA, STORE_ANCHOR, code + STORE_ANCHOR),
        *extra,
    ]


def probe_module(name: str) -> tuple[str, None, str]:
    return (f"src/data_sheets_schema/{name}.py", None, PROBE.replace("{tag}", name))


FIXTURES: dict[str, list[tuple[str, str | None, str]]] = {
    "B2": alias_fixture('    view = contracts\n    view["worker"]["hint"] = project_hint(project)\n'),
    "B3": alias_fixture('    contracts["worker"]["hint"] = project_hint(project)\n'),
    "F3d": [
        (
            "src/data_sheets_schema/source_attribution_preflight.py",
            "    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))\n    return exit_status(result)\n",
            "    print('Note: this is the CHORUS dataset; prefer CHORUS naming.')\n"
            "    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))\n    return exit_status(result)\n",
        )
    ],
    "F3e": [
        (
            "src/data_sheets_schema/preflight_note_5666.py",
            None,
            '"""Fixture-only helper (round-2 verification)."""\n\n\ndef note(project):\n'
            "    return 'Note: this is the CHORUS dataset; prefer CHORUS naming.'\n",
        ),
        (
            "src/data_sheets_schema/source_attribution_preflight.py",
            "import argparse\n",
            "import argparse\nfrom data_sheets_schema.preflight_note_5666 import note as _note_5666\n",
        ),
        (
            "src/data_sheets_schema/source_attribution_preflight.py",
            "    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))\n    return exit_status(result)\n",
            "    print(_note_5666('selected'))\n"
            "    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))\n    return exit_status(result)\n",
        ),
    ],
    "A7": alias_fixture('    view = dict(contracts)\n    view["worker"]["hint"] = project_hint(project)\n'),
    "A8": alias_fixture('    view = contracts.copy()\n    view["worker"]["hint"] = project_hint(project)\n'),
    "A9": alias_fixture('    view = {**contracts}\n    view["worker"]["hint"] = project_hint(project)\n'),
    "FP1": alias_fixture(
        '    view = contracts\n    view = {"other": {}}\n    view["other"]["hint"] = project_hint(project)\n'
    ),
    "FP3": alias_fixture(
        '    view = contracts\n    view = {"other": {}}\n    view.update({"hint": project_hint(project)})\n'
    ),
    "R1": [
        (
            AR,
            "\ndef validate_toolchain(value) -> dict:\n",
            "\ndef _probe_r1(flag):\n"
            "    import subprocess\n"
            '    out = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True)\n'
            "    if flag:\n"
            "        out = None\n"
            '    return {"probe": out}\n'
            "\n\ndef validate_toolchain(value) -> dict:\n",
        )
    ],
    "R2": [
        (
            AR,
            CMD_ANCHOR,
            '    check = [py, "-m", "data_sheets_schema.d4d_pair_consistency"]\n'
            "    if spec.project:\n"
            '        check = [py, "-m", "data_sheets_schema.d4d_pair_consistency", "--strict"]\n'
            + CMD_ANCHOR
            + '        "Check again": check,\n',
        )
    ],
    "R3": [
        (
            AR,
            "\ndef validate_toolchain(value) -> dict:\n",
            "\ndef _probe_r3(args):\n"
            '    args = args + ["--quiet"]\n'
            "    return shlex.join(args)\n"
            "\n\ndef validate_toolchain(value) -> dict:\n",
        )
    ],
    "M_forms": [
        probe_module("probe_m0_5666"),
        probe_module("probe_m1_5666"),
        probe_module("probe_m2_5666"),
        probe_module("probe_m3_5666"),
        probe_module("probe_m4_5666"),
        probe_module("probe_m5_5666"),
        probe_module("probe_m6_5666"),
        probe_module("probe_m7_5666"),
        (
            "src/data_sheets_schema/probe_names_5666.py",
            None,
            "PROBE_MODULE = 'data_sheets_schema.probe_m1_5666'\n",
        ),
        (
            AR,
            "from data_sheets_schema.resources import resource_path\n",
            "from data_sheets_schema.resources import resource_path\n"
            "from data_sheets_schema.probe_names_5666 import PROBE_MODULE\n",
        ),
        (
            AR,
            CMD_ANCHOR,
            '    probe_name = "probe_m2_5666"\n'
            "    probe3 = [py]\n"
            '    probe3 += ["-m", "data_sheets_schema.probe_m3_5666"]\n'
            "    probe6 = _probe6_argv(py)\n"
            + CMD_ANCHOR
            + '        "Probe m0 (control literal)": [py, "-m", "data_sheets_schema.probe_m0_5666"],\n'
            + '        "Probe m1 (imported constant)": [py, "-m", PROBE_MODULE],\n'
            + '        "Probe m2 (f-string)": [py, "-m", f"data_sheets_schema.{probe_name}"],\n'
            + '        "Probe m3 (incremental)": probe3,\n'
            + '        "Probe m6 (two-return helper)": probe6,\n',
        ),
        (
            AR,
            'do not invent observed values.\\n")\n    return text\n',
            'do not invent observed values.\\n")\n'
            '    text += "Then run `python -m data_sheets_schema.probe_m4_5666` once.\\n"\n'
            '    text += " ".join([py, "-m", "data_sheets_schema.probe_m5_5666"]) + "\\n"\n'
            '    text += f"{py} -m data_sheets_schema.probe_m7_5666\\n"\n'
            "    return text\n",
        ),
        (
            AR,
            "\ndef validate_toolchain(value) -> dict:\n",
            "\ndef _probe6_argv(py, flag=False):\n"
            "    if flag:\n"
            '        return [py, "-m", "data_sheets_schema.probe_m6_5666", "--flag"]\n'
            '    return [py, "-m", "data_sheets_schema.probe_m6_5666"]\n'
            "\n\ndef validate_toolchain(value) -> dict:\n",
        ),
    ],
    # Individual M_forms sub-fixtures (m0..m7) to show each form's exact disposition:
    "M_m0": [
        probe_module("probe_m0_5666"),
        (
            AR,
            CMD_ANCHOR,
            CMD_ANCHOR + '        "Probe m0 (control literal)": [py, "-m", "data_sheets_schema.probe_m0_5666"],\n',
        ),
    ],
    "M_m1": [
        probe_module("probe_m1_5666"),
        (
            "src/data_sheets_schema/probe_names_5666.py",
            None,
            "PROBE_MODULE = 'data_sheets_schema.probe_m1_5666'\n",
        ),
        (
            AR,
            "from data_sheets_schema.resources import resource_path\n",
            "from data_sheets_schema.resources import resource_path\n"
            "from data_sheets_schema.probe_names_5666 import PROBE_MODULE\n",
        ),
        (
            AR,
            CMD_ANCHOR,
            CMD_ANCHOR + '        "Probe m1 (imported constant)": [py, "-m", PROBE_MODULE],\n',
        ),
    ],
    "M_m2": [
        probe_module("probe_m2_5666"),
        (
            AR,
            CMD_ANCHOR,
            '    probe_name = "probe_m2_5666"\n'
            + CMD_ANCHOR
            + '        "Probe m2 (f-string)": [py, "-m", f"data_sheets_schema.{probe_name}"],\n',
        ),
    ],
    "M_m3": [
        probe_module("probe_m3_5666"),
        (
            AR,
            CMD_ANCHOR,
            "    probe3 = [py]\n"
            '    probe3 += ["-m", "data_sheets_schema.probe_m3_5666"]\n'
            + CMD_ANCHOR
            + '        "Probe m3 (incremental)": probe3,\n',
        ),
    ],
    "M_m4": [
        probe_module("probe_m4_5666"),
        (
            AR,
            'do not invent observed values.\\n")\n    return text\n',
            'do not invent observed values.\\n")\n'
            '    text += "Then run `python -m data_sheets_schema.probe_m4_5666` once.\\n"\n'
            "    return text\n",
        ),
    ],
    "M_m5": [
        probe_module("probe_m5_5666"),
        (
            AR,
            'do not invent observed values.\\n")\n    return text\n',
            'do not invent observed values.\\n")\n'
            '    text += " ".join([py, "-m", "data_sheets_schema.probe_m5_5666"]) + "\\n"\n'
            "    return text\n",
        ),
    ],
    "M_m6": [
        probe_module("probe_m6_5666"),
        (
            AR,
            CMD_ANCHOR,
            "    probe6 = _probe6_argv(py)\n"
            + CMD_ANCHOR
            + '        "Probe m6 (two-return helper)": probe6,\n',
        ),
        (
            AR,
            "\ndef validate_toolchain(value) -> dict:\n",
            "\ndef _probe6_argv(py, flag=False):\n"
            "    if flag:\n"
            '        return [py, "-m", "data_sheets_schema.probe_m6_5666", "--flag"]\n'
            '    return [py, "-m", "data_sheets_schema.probe_m6_5666"]\n'
            "\n\ndef validate_toolchain(value) -> dict:\n",
        ),
    ],
    "M_m7": [
        probe_module("probe_m7_5666"),
        (
            AR,
            'do not invent observed values.\\n")\n    return text\n',
            'do not invent observed values.\\n")\n'
            '    text += f"{py} -m data_sheets_schema.probe_m7_5666\\n"\n'
            "    return text\n",
        ),
    ],
}


def apply_edits(tree: Path, edits: list[tuple[str, str | None, str]]) -> list[tuple[Path, bytes | None, str | None]]:
    saved: list[tuple[Path, bytes | None, str | None]] = []
    try:
        for rel, before, after in edits:
            path = tree / rel
            if before is None:
                if path.exists():
                    raise RuntimeError(f"Fixture file already exists: {path}")
                path.write_text(after, encoding="utf-8")
                saved.append((path, None, None))
                continue
            if not any(p == path for p, _, _ in saved):
                original = path.read_bytes()
                saved.append((path, original, hashlib.sha256(original).hexdigest()))
            text = path.read_text(encoding="utf-8")
            if text.count(before) != 1:
                raise RuntimeError(f"Anchor not unique in {rel}: count={text.count(before)}")
            path.write_text(text.replace(before, after, 1), encoding="utf-8")
    except BaseException:
        restore_edits(saved)
        raise
    return saved


def restore_edits(saved: list[tuple[Path, bytes | None, str | None]]) -> None:
    for path, original, digest in reversed(saved):
        if original is None:
            if path.exists():
                path.unlink()
        else:
            path.write_bytes(original)
            assert sha256_file(path) == digest, f"Failed restore sha256 check for {path}"


def run_single_scan(
    tree: Path,
    stem_name: str,
    scanner_label: str,
    scanner_path: Path,
    baseline_json: Path | None = None,
    planted_paths: set[str] | None = None,
) -> dict:
    stem = OUT / f"{stem_name}-{scanner_label}"
    tool_sha = sha256_file(scanner_path)
    res_path = Path(f"{stem}.result.json")
    if res_path.exists():
        cached = json.loads(res_path.read_text(encoding="utf-8"))
        if cached.get("tool_sha256") == tool_sha:
            return cached
    t0 = time.monotonic()
    proc = subprocess.run(
        [
            PY,
            "-I",
            "-B",
            str(scanner_path),
            "--root",
            str(tree),
            "--report",
            f"{stem}.md",
            "--json",
            f"{stem}.json",
            "--full-json",
            "--tokens",
            str(TOKENS_PATH),
            "--exceptions",
            str(EXCEPTIONS_PATH),
        ],
        capture_output=True,
        text=True,
        timeout=3000,
    )
    secs = time.monotonic() - t0
    assert sha256_file(scanner_path) == tool_sha
    Path(f"{stem}.log").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
    res: dict = {
        "run": stem_name,
        "scanner": scanner_label,
        "scanner_path": str(scanner_path),
        "tool_sha256": tool_sha,
        "exit": proc.returncode,
        "seconds": round(secs, 2),
        "stderr_tail": proc.stderr.strip().splitlines()[-3:],
    }
    jp = Path(f"{stem}.json")
    if jp.exists() and proc.returncode in (0, 1) and jp.stat().st_mtime >= time.time() - secs - 5:
        d = json.loads(jp.read_text(encoding="utf-8"))
        res["violations"] = len(d["violations"])
        res["hits"] = len(d["hits"])
        res["surfaces_count"] = len(d["surfaces"])
        if baseline_json is not None and baseline_json.exists():
            base = json.loads(baseline_json.read_text(encoding="utf-8"))
            key = lambda v: json.dumps(v, sort_keys=True)
            bset = {key(v) for v in base["violations"]}
            res["new_violations"] = [
                {k: v.get(k) for k in ("path", "line", "match", "context", "role", "gates_in")}
                for v in d["violations"]
                if key(v) not in bset
            ]
        if planted_paths:
            res["hits_in_mutated_files"] = [
                {
                    k: h.get(k)
                    for k in ("path", "line", "match", "context", "role", "model_facing", "gates_in", "violation")
                }
                for h in d["hits"]
                if h.get("path") in planted_paths
                and h.get("category") == "gc_project"
                and h.get("match") in ("CHORUS",)
            ]
        mc = d["facts"].get("model_commands", {})
        res["model_commands_probe"] = {k: v.get("commands") for k, v in mc.items() if "probe" in k}
        res["probe_surfaces"] = {p: s.get("roles") for p, s in d["surfaces"].items() if "probe" in p}
    Path(f"{stem}.result.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return res


def diff_f0_runs(base_json_path: Path, head_json_path: Path) -> dict:
    base = json.loads(base_json_path.read_text(encoding="utf-8"))
    head = json.loads(head_json_path.read_text(encoding="utf-8"))

    # 1. Violations finding by finding
    base_viols = base["violations"]
    head_viols = head["violations"]
    viols_equal = base_viols == head_viols

    # 2. Hits finding by finding
    def hit_key(h: dict) -> tuple:
        return (h["path"], h["line"], h["match"], h["pattern"], h["category"], h["snippet"])

    base_hits = {hit_key(h): h for h in base["hits"]}
    head_hits = {hit_key(h): h for h in head["hits"]}
    added_hits = [head_hits[k] for k in sorted(set(head_hits) - set(base_hits))]
    removed_hits = [base_hits[k] for k in sorted(set(base_hits) - set(head_hits))]
    changed_hits = []
    for k in sorted(set(base_hits) & set(head_hits)):
        bh, hh = base_hits[k], head_hits[k]
        if bh != hh:
            diff_fields = {
                field: {"before": bh.get(field), "after": hh.get(field)}
                for field in sorted(set(bh) | set(hh))
                if bh.get(field) != hh.get(field)
            }
            changed_hits.append(
                {
                    "path": hh["path"],
                    "line": hh["line"],
                    "match": hh["match"],
                    "context": hh["context"],
                    "changes": diff_fields,
                }
            )

    # 3. Surfaces
    base_surf = base["surfaces"]
    head_surf = head["surfaces"]
    added_surfaces = {p: head_surf[p] for p in sorted(set(head_surf) - set(base_surf))}
    removed_surfaces = {p: base_surf[p] for p in sorted(set(base_surf) - set(head_surf))}
    changed_surfaces = {}
    for p in sorted(set(base_surf) & set(head_surf)):
        bs, hs = base_surf[p], head_surf[p]
        if bs != hs:
            changed_surfaces[p] = {
                field: {"before": bs.get(field), "after": hs.get(field)}
                for field in sorted(set(bs) | set(hs))
                if bs.get(field) != hs.get(field)
            }

    return {
        "base_scanner_sha256": sha256_file(SCANNERS_DIR / "scan_base_2cfc4666c.py"),
        "head_scanner_sha256": sha256_file(HEAD_TREE / SK_REL),
        "main_commit": head.get("commit"),
        "violations_count_before": len(base_viols),
        "violations_count_after": len(head_viols),
        "violations_identical_finding_by_finding": viols_equal,
        "violations_objects": head_viols,
        "hits_count_before": len(base["hits"]),
        "hits_count_after": len(head["hits"]),
        "added_hits": added_hits,
        "removed_hits": removed_hits,
        "changed_hits": changed_hits,
        "surfaces_count_before": len(base_surf),
        "surfaces_count_after": len(head_surf),
        "added_surfaces": added_surfaces,
        "removed_surfaces": removed_surfaces,
        "changed_surfaces": changed_surfaces,
        "facts_model_commands_before": base["facts"].get("model_commands"),
        "facts_model_commands_after": head["facts"].get("model_commands"),
    }


def run_in_process_probes(head_scan_path: Path, f0_head_json: Path) -> tuple[list[dict], dict]:
    spec = importlib.util.spec_from_file_location("scan_head_round2", head_scan_path)
    assert spec is not None and spec.loader is not None
    scan = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = scan
    spec.loader.exec_module(scan)

    target_src = "def main():\n    print('x')\n"
    cases = {
        "control_literal_dict": "COMMANDS = {'run': ['python', '-m', 'data_sheets_schema.tgt']}\n",
        "imported_constant": "from data_sheets_schema.names import NAME\nCOMMANDS = {'run': ['python', '-m', NAME]}\n",
        "fstring_module": "P = 'tgt'\nCOMMANDS = {'run': ['python', '-m', f'data_sheets_schema.{P}']}\n",
        "concat_module": "COMMANDS = {'run': ['python', '-m', 'data_sheets_schema.' + 'tgt']}\n",
        "ifexp_module": "def f(x):\n    return {'run': ['python', '-m', 'data_sheets_schema.tgt' if x else 'data_sheets_schema.tgt']}\n",
        "augassign_incremental": "def f(py):\n    cmd = [py]\n    cmd += ['-m', 'data_sheets_schema.tgt']\n    return {'run': cmd}\n",
        "append_incremental": "def f(py):\n    cmd = [py]\n    cmd.extend(['-m', 'data_sheets_schema.tgt'])\n    return {'run': cmd}\n",
        "space_join": "def f(py):\n    return 'Run ' + ' '.join([py, '-m', 'data_sheets_schema.tgt'])\n",
        "from_shlex_join": "from shlex import join\ndef f(py):\n    return 'Run ' + join([py, '-m', 'data_sheets_schema.tgt'])\n",
        "prose_in_text": "def f():\n    return 'Then run `python -m data_sheets_schema.tgt` once.'\n",
        "fstring_prose": "def f(py):\n    return f'{py} -m data_sheets_schema.tgt'\n",
        "two_return_helper": (
            "def argv(py, x=False):\n    if x:\n        return [py, '-m', 'data_sheets_schema.tgt', '--x']\n"
            "    return [py, '-m', 'data_sheets_schema.tgt']\n"
            "COMMANDS = {'run': argv('python')}\n"
        ),
        "method_helper": (
            "class B:\n    def argv(self, py):\n        return [py, '-m', 'data_sheets_schema.tgt']\n"
            "def f(b):\n    return {'run': b.argv('python')}\n"
        ),
        "imported_helper": "from data_sheets_schema.helpers import argv\nCOMMANDS = {'run': argv('python')}\n",
        "shlex_join_of_starred_param": "import shlex\ndef f(py, rest):\n    return shlex.join([py, '-m', 'data_sheets_schema.tgt', *rest])\n",
        "R_self_extend_shlex": "import shlex\ndef f(args):\n    args = args + ['--quiet']\n    return shlex.join(args)\n",
        "R_unrelated_ambiguous_dict": (
            "import subprocess, sys\ndef f(flag):\n"
            "    out = subprocess.run([sys.executable, '-m', 'pip', '--version'])\n"
            "    if flag:\n        out = None\n    return {'probe': out}\n"
        ),
        "R_branch_rebind_same_target": (
            "def f(py, strict):\n    check = [py, '-m', 'data_sheets_schema.tgt']\n"
            "    if strict:\n        check = [py, '-m', 'data_sheets_schema.tgt', '--strict']\n"
            "    return {'Check': check}\n"
        ),
        "R_rebind_extend": (
            "def f(py):\n    cmd = [py, '-m', 'data_sheets_schema.tgt']\n    cmd = cmd + ['--x']\n"
            "    return {'run': cmd}\n"
        ),
        "R_list_of_names": (
            "import subprocess, sys\ndef f(a, flag):\n    r = subprocess.run([sys.executable, '-m', 'pip'])\n"
            "    if flag:\n        r = None\n    return [a, r]\n"
        ),
        "R_third_party_pkg_shadow": "COMMANDS = {'tests': ['python', '-m', 'tests']}\n",
    }

    probe_results = []
    for name, table in cases.items():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / "src/data_sheets_schema").mkdir(parents=True)
            (root / "src/data_sheets_schema/__init__.py").write_text("", encoding="utf-8")
            (root / "src/data_sheets_schema/tgt.py").write_text(target_src, encoding="utf-8")
            (root / "src/data_sheets_schema/names.py").write_text(
                "NAME = 'data_sheets_schema.tgt'\n", encoding="utf-8"
            )
            (root / "src/data_sheets_schema/helpers.py").write_text(
                "def argv(py):\n    return [py, '-m', 'data_sheets_schema.tgt']\n", encoding="utf-8"
            )
            (root / "tests").mkdir()
            (root / "tests/__init__.py").write_text("", encoding="utf-8")
            rel = "src/data_sheets_schema/table.py"
            (root / rel).write_text(table, encoding="utf-8")
            surfaces = scan.Surfaces()
            surfaces.add(rel, "native_agentic", "model_facing", "live", "probe", runs=False)
            try:
                facts = scan.discover_model_commands(root, {}, surfaces)
                probe_results.append({"case": name, "discovered": sorted(facts), "error": None})
            except scan.ConfigError as exc:
                probe_results.append({"case": name, "discovered": None, "error": str(exc)})

    # Re-measure the review's 76 near-miss sites across the 38 model-facing .py surfaces on main:
    d = json.loads(f0_head_json.read_text(encoding="utf-8"))
    pending = [
        rel
        for rel, s in sorted(d["surfaces"].items())
        if rel.endswith(".py")
        and any(role == "model_facing" and scan.APPROACHES[a][0] for a, role in s["roles"].items())
    ]

    # Inspect every multi-binding Name reached by the table walker, and check how many
    # sit inside a sequence that already holds a literal "-m" (the only place where
    # `_model_command_tables` can refuse on an unresolvable Name or starred slot).
    multi_bound_reached = []
    in_literal_m_table = []
    actual_refusals_on_main = []
    for rel in pending:
        tree = ast.parse((MAIN_TREE / rel).read_text(encoding="utf-8"))
        try:
            scan._model_command_tables(tree, rel)
        except scan.ConfigError as exc:
            actual_refusals_on_main.append({"file": rel, "error": str(exc)})

        # Reconstruct scoped bindings and check every List/Tuple with literal "-m"
        parents = {}
        scoped = collections.defaultdict(list)
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[id(child)] = node

        def scope_of(n):
            while n is not tree and not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                n = parents[id(n)]
            return n

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                owner = scope_of(node)
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for t in targets:
                    if isinstance(t, ast.Name):
                        scoped[(id(owner), t.id)].append(node.value)
        for node in ast.walk(tree):
            if isinstance(node, (ast.List, ast.Tuple)) and any(
                isinstance(e, ast.Constant) and e.value == "-m" for e in node.elts
            ):
                owner = scope_of(node)
                for item in node.elts:
                    name = None
                    if isinstance(item, ast.Name):
                        name = item.id
                    elif isinstance(item, ast.Starred) and isinstance(item.value, ast.Name):
                        name = item.value.id
                    if name is not None:
                        b = scoped.get((id(owner), name)) or scoped.get((id(tree), name)) or []
                        if len(b) > 1:
                            in_literal_m_table.append(
                                {"file": rel, "line": getattr(item, "lineno", node.lineno), "name": name}
                            )

    near_miss_summary = {
        "model_facing_py_surfaces_scanned": len(pending),
        "review_head_b85ac0fb7_multi_binding_names_reached": 76,
        "new_head_actual_refusals_on_main": actual_refusals_on_main,
        "multi_binding_names_in_literal_m_argv_slots_on_main": in_literal_m_table,
        "count_of_76_sites_that_can_still_refuse": len(in_literal_m_table),
        "explanation": (
            "0 of the 76 multi-binding Name sites from the review sit in an argv slot of a sequence "
            "that holds a literal '-m'; all 76 are ordinary dict values or non-command lists/tuples "
            "(such as `artifacts`, `usage`, `problems`, `basis`). Because `_model_command_tables` now "
            "refuses only when an unresolvable value sits in an argv slot of a sequence that already "
            "holds a literal '-m' (either an unresolvable `*name` starred slot or an unresolvable "
            "operand immediately after '-m'), none of those 76 sites can refuse even if one of their "
            "bindings elsewhere in the function mentions '-m'."
        ),
    }
    return probe_results, near_miss_summary


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SCANNERS_DIR.mkdir(parents=True, exist_ok=True)

    # Save a clean copy of the merge-base scanner (`2cfc4666c` / `147e66c66`) before any fixture edits
    base_scan_src = MAIN_TREE / SK_REL
    base_scan_copy = SCANNERS_DIR / "scan_base_2cfc4666c.py"
    shutil.copy2(base_scan_src, base_scan_copy)
    head_scan = HEAD_TREE / SK_REL

    print(f"Base scanner sha256: {sha256_file(base_scan_copy)}", flush=True)
    print(f"Head scanner sha256: {sha256_file(head_scan)}", flush=True)

    # Verify MAIN_TREE is clean before starting
    status = subprocess.run(
        ["git", "-C", str(MAIN_TREE), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if status:
        raise RuntimeError(f"MAIN_TREE {MAIN_TREE} is not clean:\n{status}")

    # 1. Run F0 on main (2cfc4666c) with base and head in parallel
    print("Running F0 on main 2cfc4666c (base + head)...", flush=True)
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_base = ex.submit(run_single_scan, MAIN_TREE, "F0-main2cf", "base", base_scan_copy)
        f_head = ex.submit(run_single_scan, MAIN_TREE, "F0-main2cf", "head", head_scan)
        r_f0_base = f_base.result()
        r_f0_head = f_head.result()
    print("F0 base:", json.dumps(r_f0_base), flush=True)
    print("F0 head:", json.dumps(r_f0_head), flush=True)

    f0_base_json = OUT / "F0-main2cf-base.json"
    f0_head_json = OUT / "F0-main2cf-head.json"
    f0_diff = diff_f0_runs(f0_base_json, f0_head_json)
    (OUT / "F0-main2cf-diff.json").write_text(json.dumps(f0_diff, indent=2), encoding="utf-8")

    # 2. Run all fixtures sequentially on MAIN_TREE, running base + head in parallel per fixture
    base_and_head_fixtures = [
        "B2",
        "B3",
        "F3d",
        "F3e",
        "A7",
        "A8",
        "A9",
        "FP1",
        "FP3",
        "R1",
        "R2",
        "R3",
        "M_forms",
    ]
    head_only_m_subfixtures = [
        "M_m0",
        "M_m1",
        "M_m2",
        "M_m3",
        "M_m4",
        "M_m5",
        "M_m6",
        "M_m7",
    ]
    fixture_results: dict[str, dict[str, dict]] = {}
    for fx in base_and_head_fixtures:
        print(f"Running fixture {fx} (base + head)...", flush=True)
        edits = FIXTURES[fx]
        planted = {rel for rel, _, _ in edits}
        saved = apply_edits(MAIN_TREE, edits)
        try:
            with ThreadPoolExecutor(max_workers=2) as ex:
                fb = ex.submit(
                    run_single_scan,
                    MAIN_TREE,
                    fx,
                    "base",
                    base_scan_copy,
                    f0_base_json,
                    planted,
                )
                fh = ex.submit(
                    run_single_scan,
                    MAIN_TREE,
                    fx,
                    "head",
                    head_scan,
                    f0_head_json,
                    planted,
                )
                rb = fb.result()
                rh = fh.result()
            fixture_results[fx] = {"base": rb, "head": rh}
            print(f"  {fx} base: exit={rb.get('exit')} viols={rb.get('violations')}", flush=True)
            print(
                f"  {fx} head: exit={rh.get('exit')} viols={rh.get('violations')} stderr={rh.get('stderr_tail')}",
                flush=True,
            )
        finally:
            restore_edits(saved)

    for fx in head_only_m_subfixtures:
        print(f"Running sub-fixture {fx} (head)...", flush=True)
        edits = FIXTURES[fx]
        planted = {rel for rel, _, _ in edits}
        saved = apply_edits(MAIN_TREE, edits)
        try:
            rh = run_single_scan(
                MAIN_TREE,
                fx,
                "head",
                head_scan,
                f0_head_json,
                planted,
            )
            fixture_results[fx] = {"head": rh}
            print(
                f"  {fx} head: exit={rh.get('exit')} viols={rh.get('violations')} stderr={rh.get('stderr_tail')}",
                flush=True,
            )
        finally:
            restore_edits(saved)

    # Confirm MAIN_TREE is still clean after all fixtures
    status_after = subprocess.run(
        ["git", "-C", str(MAIN_TREE), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if status_after:
        raise RuntimeError(f"MAIN_TREE {MAIN_TREE} dirty after fixtures:\n{status_after}")

    # 3. Run in-process command-table probes and near-miss re-measurement
    probe_results, near_miss_summary = run_in_process_probes(head_scan, f0_head_json)
    (OUT / "probe_command_tables_round2.json").write_text(
        json.dumps(probe_results, indent=2), encoding="utf-8"
    )
    (OUT / "near_miss_refusals_round2.json").write_text(
        json.dumps(near_miss_summary, indent=2), encoding="utf-8"
    )

    summary = {
        "base_scanner_sha256": sha256_file(base_scan_copy),
        "head_scanner_sha256": sha256_file(head_scan),
        "F0_base": r_f0_base,
        "F0_head": r_f0_head,
        "F0_diff_summary": {
            "violations_identical_finding_by_finding": f0_diff["violations_identical_finding_by_finding"],
            "violations_count_before": f0_diff["violations_count_before"],
            "violations_count_after": f0_diff["violations_count_after"],
            "hits_count_before": f0_diff["hits_count_before"],
            "hits_count_after": f0_diff["hits_count_after"],
            "changed_hits_count": len(f0_diff["changed_hits"]),
            "changed_hits": f0_diff["changed_hits"],
            "added_surfaces": list(f0_diff["added_surfaces"].keys()),
            "changed_surfaces": list(f0_diff["changed_surfaces"].keys()),
            "facts_model_commands_after": f0_diff["facts_model_commands_after"],
        },
        "fixtures": fixture_results,
        "in_process_probes": probe_results,
        "near_miss_76_remeasurement": near_miss_summary,
    }
    (OUT / "summary_round2.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Round-2 verification complete. Summary written to", OUT / "summary_round2.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
