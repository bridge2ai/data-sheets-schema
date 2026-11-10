#!/usr/bin/env python3
"""Verify PR #5677 review and re-review fixes (#5698-#5702, #5706-#5708): cross-version probe and per-clause mutation checks (2026-11-10).

Purpose:
  1. Run a cross-version probe of tests/test_api_launcher.py::_OUTER_SITES_HELPER_SOURCE
     across the Python interpreters passed on the command line (or CANDIDATE_INTERPRETERS
     by default), verifying that:
     - no site.py error occurs on Python 3.9-3.11 (P1-1 / #5698);
     - outer .pth import startup hooks do not execute and do not create a marker file (P2-1 / #5699);
     - foreign src holding data_sheets_schema/, foreign data_sheets_schema parent, and foreign
       checkout root (P3-2 / #5701) are all excluded, while this checkout's own src, src-layout
       dependencies (/x/otherdep/src, N-1 / #5706), path-line site directories holding
       *.dist-info / *.egg-info (N-2 / #5707), and outer site directories themselves (P3-3 / #5702)
       are kept;
     - prints how many interpreters ran and exits non-zero when none ran (N-3 / #5708).
  2. Run a per-clause mutation check against tests/test_api_launcher.py (P3-1 / #5700, N-1 / #5706,
     N-2 / #5707), confirming that mutating any single rule fails its dedicated test.
Inputs: optional interpreter paths on argv (defaults to CANDIDATE_INTERPRETERS); tests/test_api_launcher.py.
Outputs: JSON lines on stdout summarizing cross-version count/results and per-mutant results; non-zero exit if 0 interpreters ran or any check fails.
Serves: PR #5677 (Issues #5676, #5698, #5699, #5700, #5701, #5702, #5706, #5707, #5708).
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_FILE = REPO_ROOT / "tests" / "test_api_launcher.py"

CANDIDATE_INTERPRETERS = [
    "/Users/marcin/.pyenv/versions/3.9.8/bin/python",
    "/Users/marcin/.pyenv/versions/3.10.11/bin/python",
    "/Users/marcin/.pyenv/versions/3.10.13/bin/python",
    "/Users/marcin/.local/share/uv/python/cpython-3.10.16-macos-aarch64-none/bin/python3.10",
    "/Users/marcin/.pyenv/versions/3.11.5/bin/python",
    "/opt/local/bin/python3.11",
    "/Users/marcin/.local/share/uv/python/cpython-3.12.9-macos-aarch64-none/bin/python3.12",
    "/Users/marcin/.pyenv/versions/3.12.11/bin/python",
    "/opt/homebrew/opt/python@3.13/bin/python3.13",
    "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python",
    "/opt/homebrew/bin/python3.14",
]


def _load_helper_source() -> str:
    spec = importlib.util.spec_from_file_location("_verify_tal_5677", TEST_FILE)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_verify_tal_5677"] = mod
    spec.loader.exec_module(mod)
    return mod._OUTER_SITES_HELPER_SOURCE


def run_cross_version_probes(helper_src: str, interpreters: list[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    exp = str((REPO_ROOT / "src").resolve())
    for interp in interpreters:
        if not (Path(interp).is_file() and os.access(interp, os.X_OK)):
            continue
        with tempfile.TemporaryDirectory(prefix="pr5677_xver_verify_") as tmp:
            t = Path(tmp)
            outer = t / "outer_site"
            (outer / "data_sheets_schema").mkdir(parents=True)
            (outer / "sibling_dep_5677.py").write_text("SIBLING = 'ok'\n", encoding="utf-8")

            dep = t / "pth_dep"
            dep.mkdir()
            (dep / "d4d_pth_probe_5676.py").write_text("MARKER = 'ok'\n", encoding="utf-8")

            foreign_src = t / "other_wt" / "src"
            (foreign_src / "data_sheets_schema").mkdir(parents=True)
            foreign_pkg_holder = t / "foreign_pkg_holder"
            (foreign_pkg_holder / "data_sheets_schema").mkdir(parents=True)
            foreign_root = t / "foreign_checkout"
            (foreign_root / "src" / "data_sheets_schema").mkdir(parents=True)

            src_layout_dep = t / "otherdep" / "src"
            (src_layout_dep / "otherdep_5677").mkdir(parents=True)
            (src_layout_dep / "otherdep_5677" / "__init__.py").write_text("DEP = 'ok'\n", encoding="utf-8")

            dep_site = t / "dep_venv_site"
            (dep_site / "data_sheets_schema").mkdir(parents=True)
            (dep_site / "dep_site_5677-1.0.dist-info").mkdir(parents=True)
            (dep_site / "dep_site_5677.py").write_text("SITE_DEP = 'ok'\n", encoding="utf-8")

            own_alias_dir = t / "own_alias"
            own_alias_dir.mkdir()
            own_src_alias = own_alias_dir / "src"
            own_src_alias.symlink_to((REPO_ROOT / "src").resolve())

            marker = t / "startup_hook.marker"
            (outer / "u3a_paths.pth").write_text(
                "# comment line\n"
                "\n"
                f"import pathlib; pathlib.Path({str(marker)!r}).write_text('ran_space', encoding='utf-8')\n"
                f"import\tpathlib; pathlib.Path({str(marker)!r}).write_text('ran_tab', encoding='utf-8')\n"
                f"{foreign_src}\n"
                f"{foreign_pkg_holder}\n"
                f"{foreign_root}\n"
                f"{src_layout_dep}\n"
                f"{dep_site}\n"
                f"{own_src_alias}\n"
                f"{dep}\n",
                encoding="utf-8",
            )

            venv_dir = t / "v"
            subprocess.run([interp, "-m", "venv", "--without-pip", str(venv_dir)], check=True, capture_output=True)
            site_dir = next(venv_dir.glob("lib/python*/site-packages"))
            (site_dir / "_d4d_outer_sites.py").write_text(helper_src, encoding="utf-8")
            (site_dir / "deps.pth").write_text(
                f"import _d4d_outer_sites; _d4d_outer_sites.add_outer_sites({exp!r}, {[str(outer)]!r})\n",
                encoding="utf-8",
            )
            (site_dir / "data_sheets_schema.pth").write_text(f"{REPO_ROOT / 'src'}\n", encoding="utf-8")

            probe_code = (
                "import json, sys, d4d_pth_probe_5676, sibling_dep_5677, otherdep_5677, dep_site_5677\n"
                "out = {\n"
                "    'version': sys.version.split()[0],\n"
                "    'probe': d4d_pth_probe_5676.MARKER,\n"
                "    'sibling': sibling_dep_5677.SIBLING,\n"
                "    'otherdep': otherdep_5677.DEP,\n"
                "    'site_dep': dep_site_5677.SITE_DEP,\n"
                f"    'outer_on_path': {str(outer)!r} in sys.path,\n"
                f"    'own_alias_on_path': {str(own_src_alias)!r} in sys.path,\n"
                f"    'src_layout_dep_on_path': {str(src_layout_dep)!r} in sys.path,\n"
                f"    'dep_site_on_path': {str(dep_site)!r} in sys.path,\n"
                f"    'foreign_src_on_path': {str(foreign_src)!r} in sys.path,\n"
                f"    'foreign_pkg_on_path': {str(foreign_pkg_holder)!r} in sys.path,\n"
                f"    'foreign_root_on_path': {str(foreign_root)!r} in sys.path,\n"
                "}\n"
                "print(json.dumps(out))\n"
            )
            env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
            proc = subprocess.run(
                [str(venv_dir / "bin" / "python"), "-c", probe_code],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"Cross-version probe failed on {interp}: {proc.stderr}\n{proc.stdout}")
            row = json.loads(proc.stdout.strip().splitlines()[-1])
            row["kind"] = "cross_version_probe"
            row["interp"] = interp
            row["site_error"] = "Error processing line" in proc.stderr
            row["hook_ran"] = marker.exists()
            print(json.dumps(row))
            assert row["probe"] == "ok"
            assert row["sibling"] == "ok"
            assert row["otherdep"] == "ok"
            assert row["site_dep"] == "ok"
            assert row["outer_on_path"] is True
            assert row["own_alias_on_path"] is True
            assert row["src_layout_dep_on_path"] is True
            assert row["dep_site_on_path"] is True
            assert row["foreign_src_on_path"] is False
            assert row["foreign_pkg_on_path"] is False
            assert row["foreign_root_on_path"] is False
            assert row["site_error"] is False
            assert row["hook_ran"] is False
            results.append(row)
    summary = {
        "kind": "cross_version_summary",
        "interpreters_requested": len(interpreters),
        "interpreters_ran": len(results),
    }
    print(json.dumps(summary))
    return results


def run_clause_mutations() -> list[dict[str, object]]:
    src = TEST_FILE.read_text(encoding="utf-8")
    mutations = [
        (
            "M1_delete_own_src_clause",
            '    if os.path.realpath(norm) == expected_src_real:\n        return False\n',
            "",
            "test_isolated_venv_keeps_this_checkouts_own_src_from_outer_pth",
        ),
        (
            "M2_reintroduce_basename_src_clause",
            '    if os.path.realpath(norm) == expected_src_real:\n        return False\n',
            '    if os.path.realpath(norm) == expected_src_real:\n        return False\n    if os.path.basename(norm) == "src":\n        return True\n',
            "test_isolated_venv_drops_foreign_src_basename_from_outer_pth",
        ),
        (
            "M3_delete_dist_or_egg_info_site_clause",
            '    if _has_dist_or_egg_info(norm):\n        return False\n',
            "",
            "test_isolated_venv_keeps_pth_site_directory_with_dist_info_and_reports_leak",
        ),
        (
            "M4_delete_dist_info_suffix",
            '        if entry.endswith((".dist-info", ".egg-info")):\n',
            '        if entry.endswith(".egg-info"):\n',
            "test_isolated_venv_keeps_pth_site_directory_with_dist_info_and_reports_leak",
        ),
        (
            "M5_delete_egg_info_suffix",
            '        if entry.endswith((".dist-info", ".egg-info")):\n',
            '        if entry.endswith(".dist-info"):\n',
            "test_isolated_venv_keeps_pth_site_directory_with_dist_info_and_reports_leak",
        ),
        (
            "M6_delete_dss_dir_clause",
            '    if os.path.isdir(os.path.join(norm, "data_sheets_schema")):\n        return True\n',
            "",
            "test_isolated_venv_drops_directory_holding_data_sheets_schema_from_outer_pth",
        ),
        (
            "M7_delete_checkout_root_clause",
            '    if os.path.isdir(os.path.join(norm, "src", "data_sheets_schema")):\n        return True\n',
            "",
            "test_isolated_venv_drops_foreign_checkout_root_from_outer_pth",
        ),
        (
            "M8_filter_outer_site_itself",
            "        _append_unique(site_dir)\n",
            "        if not _is_filtered_pth_path(site_dir, expected_src_real):\n            _append_unique(site_dir)\n",
            "test_isolated_venv_never_drops_outer_site_directory_itself",
        ),
        (
            "M9_execute_outer_import_hooks",
            '                if raw_line.startswith(("import ", "import\\\\t")) or stripped.startswith(("import ", "import\\\\t")):\n                    continue\n',
            '                if raw_line.startswith(("import ", "import\\\\t")) or stripped.startswith(("import ", "import\\\\t")):\n                    exec(stripped)\n                    continue\n',
            "test_isolated_venv_skips_outer_pth_import_startup_hooks",
        ),
    ]

    results: list[dict[str, object]] = []
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{REPO_ROOT / 'src'}:{REPO_ROOT}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    with tempfile.TemporaryDirectory(prefix="pr5677_mut_") as tmp:
        tmp_dir = Path(tmp)
        for name, target, replacement, expected_failing_node in mutations:
            assert target in src, f"Target for {name} not found in {TEST_FILE}"
            mutated = src.replace(target, replacement, 1)
            assert mutated != src
            mut_file = tmp_dir / f"test_mut_{name}.py"
            mutated = mutated.replace(
                "REPO_ROOT = Path(__file__).resolve().parents[1]",
                f"REPO_ROOT = Path({str(REPO_ROOT)!r})",
                1,
            )
            mut_file.write_text(mutated, encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(mut_file),
                    "-k",
                    "TestImportIsolationCheck",
                    "-q",
                    "-o",
                    "addopts=",
                    "-p",
                    "no:cacheprovider",
                    "-rf",
                ],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            failed_nodes = sorted({
                line.split("::")[-1].split(" ")[0]
                for line in (proc.stdout + "\n" + proc.stderr).splitlines()
                if line.startswith("FAILED ")
            })
            row = {
                "kind": "mutation_check",
                "mutant": name,
                "exit_code": proc.returncode,
                "expected_failing_node": expected_failing_node,
                "failed_nodes": failed_nodes,
            }
            print(json.dumps(row))
            assert proc.returncode != 0, f"Mutant {name} unexpectedly passed!"
            assert expected_failing_node in failed_nodes, (
                f"Mutant {name} did not fail {expected_failing_node}; failed={failed_nodes}"
            )
            results.append(row)
    return results


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    skip_mutations = False
    interp_args: list[str] = []
    for arg in raw_args:
        if arg == "--skip-mutations":
            skip_mutations = True
        else:
            interp_args.append(arg)
    interpreters = interp_args if interp_args else list(CANDIDATE_INTERPRETERS)
    helper_src = _load_helper_source()
    ran = run_cross_version_probes(helper_src, interpreters)
    if not ran:
        print(
            f"ERROR: 0 of {len(interpreters)} candidate interpreter(s) ran.",
            file=sys.stderr,
        )
        return 1
    if not skip_mutations:
        run_clause_mutations()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
