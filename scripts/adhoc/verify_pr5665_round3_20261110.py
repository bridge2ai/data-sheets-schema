#!/usr/bin/env python3
"""
Purpose: Failing-first and post-fix verification harness for PR #5665 round-3 fixes:
  - R2-1 (#5724): Flow-sensitive alias walkers in _local_writes and effects() across
    try/except/else/finally, multi-hop loop-carried aliases (fixed-point convergence),
    and kill_alias after if/else joins (without breaking FP1/FP3 or causing spurious
    cross-container merges).
  - R2-3 (#5725): _model_command_tables multi-bound starred prefixes [*prefix, "--check"]
    and function parameter shadowing of module-level constants, plus documented
    cross-module helper boundary.
Inputs:
  - Worktree scanner at .claude/skills/d4d-generation-specificity-audit/scan.py
Outputs:
  - JSON summary under /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-pr5665/round3/
Issues/PR: #5665, #5657, #5679, #5682, #5684, #5724, #5725, #5726
Date: 2026-11-10
"""

from __future__ import annotations

import ast
import importlib.machinery
import importlib.util
import json
import sys
import tempfile
import textwrap
from pathlib import Path

WORKTREE = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-scanner-alias")
SCAN_PATH = WORKTREE / ".claude/skills/d4d-generation-specificity-audit/scan.py"
TEST_PATH = WORKTREE / "tests/test_generation_specificity_skill.py"
OUT_DIR = Path("/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-pr5665/round3")


def load_module(path: Path, name: str, origin: Path | None = None):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader, origin=str(origin or path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(origin or path)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_alias_fixture(
    scan_mod,
    test_mod,
    helper: object,
    body_lines: list[str],
    direct_return_worker: bool = False,
) -> dict:
    with tempfile.TemporaryDirectory() as directory:
        runner = test_mod.PRECISION_RUNNER.replace(
            "from pathlib import Path\n",
            "from pathlib import Path\nfrom data_sheets_schema import contracts_r3\n",
        ).replace(
            "[guide, value, ids_4085.label(spec)]",
            "[guide, value, ids_4085.label(spec), contracts_r3.render_worker(spec)]",
        )
        modules = dict(test_mod.PRECISION_MODULES)
        modules["project_hints"] = (
            "def project_hint(project: str) -> str:\n"
            '    return f"Review the CHORUS cohort for {project}."\n'
        )
        if direct_return_worker:
            role_lines = [
                "import json",
                "from data_sheets_schema.project_hints import project_hint",
                "",
                "def render_worker(spec) -> str:",
                *[f"    {line}" for line in body_lines],
                '    return contracts["worker"]',
            ]
        else:
            role_lines = [
                "import json",
                "from data_sheets_schema.project_hints import project_hint",
                "",
                "def _contracts_seed() -> dict[str, dict[str, object]]:",
                '    return {"worker": {"stage": "worker"}}',
                "",
                "def _role_contracts(project: str = \"\") -> dict[str, dict[str, object]]:",
                "    contracts = _contracts_seed()",
                *[f"    {line}" for line in body_lines],
                "    return contracts",
                "",
                "def render_worker(spec) -> str:",
                '    return str(_role_contracts(spec.project)["worker"])',
            ]
        modules["contracts_r3"] = "\n".join(role_lines) + "\n"
        root = helper._root(directory, runner, modules)
        try:
            derived, spans, _ = helper._derive(root)
            violations = sorted(
                helper._violations(root, "src/data_sheets_schema/project_hints.py", derived, spans)
            )
            return {
                "status": "ok",
                "project_hints_derived": "project_hints" in derived,
                "project_hints_violations": [list(v) for v in violations],
                "derived_modules": sorted(derived),
            }
        except scan_mod.ConfigError as exc:
            return {
                "status": "refused",
                "error": str(exc),
            }


def check_cases(scan_override: Path | None = None) -> dict:
    test_mod = load_module(TEST_PATH, "test_skill_round3")
    if scan_override is not None:
        scan_mod = load_module(scan_override, "scan_override_round3", origin=SCAN_PATH)
        test_mod.scan = scan_mod
    else:
        scan_mod = test_mod.scan
    helper = test_mod.TestModelFacingDerivation()

    results = {
        "_scan_path": str(scan_override or SCAN_PATH),
    }

    # FP1: sequential rebind to fresh dict before write (must NOT derive project_hints)
    results["FP1_sequential_rebind"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "view = contracts",
            "view = {'other': {}}",
            "view['other']['hint'] = project_hint(project)",
        ],
    )

    # FP1_try_both_kill: both try and except kill the alias before post-try write
    results["FP1_try_both_kill"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "view = contracts",
            "try:",
            "    view = {'other': {}}",
            "except KeyError:",
            "    view = {'other': {}}",
            "view['other']['hint'] = project_hint(project)",
        ],
    )

    # FP3: .update(...) on rebound alias remains conservative (must derive project_hints)
    results["FP3_update_after_rebind"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "view = contracts",
            "view = {'other': {}}",
            "view.update({'hint': project_hint(project)})",
        ],
    )

    # Case 1 (R2-1): try binds view = contracts, except rebinds view = {'worker': {}}
    results["Case1_try_except_rebind"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "try:",
            "    view = contracts",
            "except KeyError:",
            "    view = {'worker': {}}",
            "view['worker']['hint'] = project_hint(project)",
        ],
    )

    # Case 1b: try binds view = contracts, raises mid-block, then rebinds view = {}; except passes
    results["Case1b_try_mid_raise_except_pass"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "view = {'worker': {}}",
            "try:",
            "    view = contracts",
            "    _ = contracts['worker']",
            "    view = {'worker': {}}",
            "except KeyError:",
            "    pass",
            "view['worker']['hint'] = project_hint(project)",
        ],
    )

    # Case 2 (R2-1): 1-hop loop-carried alias
    results["Case2_loop_carried_1hop"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "view = {'worker': {}}",
            "for _ in (1, 2):",
            "    view['worker']['hint'] = project_hint(project)",
            "    view = contracts",
        ],
    )

    # Case 2b (R2-1): 3-hop loop-carried alias (requires >2 loop passes to reach fixed point)
    results["Case2b_loop_carried_3hop"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "v1 = {'worker': {}}",
            "v2 = {'worker': {}}",
            "v3 = {'worker': {}}",
            "for _ in (1, 2, 3, 4):",
            "    v3['worker']['hint'] = project_hint(project)",
            "    v3 = v2",
            "    v2 = v1",
            "    v1 = contracts",
        ],
    )

    # Case 3 (R2-1): exact witness from pr5665_lead_rereview_a939fed2e_2026-11-10.md:95-101
    # kill_alias(v1) after if/else join must not drop contracts from v2 in _local_writes
    results["Case3_kill_alias_after_if_join"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "inner = {'hint': project_hint(spec.project)}",
            "contracts = {}",
            "v2 = {}",
            "if spec.project:",
            "    v1 = v2",
            "else:",
            "    v2 = contracts",
            "    v1 = {}",
            "v1 = 0",
            "v2['worker'] = json.dumps(inner)",
        ],
        direct_return_worker=True,
    )

    # Case 4 (R2-1): kill_alias after if/else join must not spuriously merge two unrelated containers
    fn_ast = ast.parse(
        textwrap.dedent(
            """\
            def f(cond, secret):
                c1 = {}
                c2 = {}
                if cond:
                    view = c1
                else:
                    view = c2
                view = 0
                c2['k'] = secret
                return c1
            """
        )
    ).body[0]
    scan_mod._WRITES.clear()
    writes = scan_mod._local_writes(fn_ast)
    c1_write_names = [
        n.id for w in writes.get("c1", []) for n in ast.walk(w) if isinstance(n, ast.Name)
    ]
    results["Case4_no_spurious_container_merge"] = {
        "c1_write_names": c1_write_names,
        "secret_leaked_into_c1": "secret" in c1_write_names,
    }

    # Case 5a (R3 P2-1a): nested if inside try binds view = contracts, raises, then rebinds view = {}
    results["Case5a_try_nested_if_raise_before_rebind"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "view = {'worker': {}}",
            "try:",
            "    if project:",
            "        view = contracts",
            "        _ = contracts['worker']",
            "        view = {'worker': {}}",
            "except KeyError:",
            "    pass",
            "view['worker']['hint'] = project_hint(project)",
        ],
    )

    # Case 5b (R3 P2-1b): with block binds view = contracts, raises (suppressed by __exit__), skips rebind
    results["Case5b_with_suppression_skips_rebind"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "view = {'worker': {}}",
            "with project:",
            "    view = contracts",
            "    _ = contracts['worker']",
            "    view = {'worker': {}}",
            "view['worker']['hint'] = project_hint(project)",
        ],
    )

    # Case 6 (R3 P2-2): match guard fall-through retains := binding into subsequent case
    results["Case6_match_guard_fallthrough_retains_binding"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "view = {'worker': {}}",
            "match project:",
            "    case _ if (view := contracts) and False:",
            "        pass",
            "    case _:",
            "        view['worker']['hint'] = project_hint(project)",
        ],
    )

    # Case 7 (R3 P2-3): match case view: capture alias unbound elsewhere in the function
    results["Case7_match_capture_alias_unbound_elsewhere"] = run_alias_fixture(
        scan_mod,
        test_mod,
        helper,
        [
            "match contracts:",
            "    case view:",
            "        view['worker']['hint'] = project_hint(project)",
        ],
    )

    # R2-3a (#5725): multi-bound starred prefix [*prefix, "--check"]
    tree_r23a = ast.parse(
        textwrap.dedent(
            """\
            def _cmd(flag):
                if flag:
                    prefix = ["python3", "-m", "data_sheets_schema.a"]
                else:
                    prefix = ["python3", "-m", "data_sheets_schema.b"]
                return [*prefix, "--check"]
            COMMANDS = {"run": _cmd(True)}
            """
        )
    )
    try:
        tables_r23a = [
            [e.value if isinstance(e, ast.Constant) else ast.unparse(e) for e in seq.elts]
            for seq in scan_mod._model_command_tables(tree_r23a, "pkg/r23a.py")
        ]
        results["R2_3a_multi_bound_starred_prefix"] = {"status": "ok", "tables": tables_r23a}
    except scan_mod.ConfigError as exc:
        results["R2_3a_multi_bound_starred_prefix"] = {"status": "refused", "error": str(exc)}

    # R2-3b (#5725): function parameter shadowing module-level constant
    tree_r23b = ast.parse(
        textwrap.dedent(
            """\
            MOD = "data_sheets_schema.target"
            def _cmd(MOD):
                return ["python3", "-m", MOD]
            COMMANDS = {"run": _cmd(runtime_arg)}
            """
        )
    )
    try:
        tables_r23b = [
            [e.value if isinstance(e, ast.Constant) else ast.unparse(e) for e in seq.elts]
            for seq in scan_mod._model_command_tables(tree_r23b, "pkg/r23b.py")
        ]
        results["R2_3b_param_shadowing"] = {"status": "ok", "tables": tables_r23b}
    except scan_mod.ConfigError as exc:
        results["R2_3b_param_shadowing"] = {"status": "refused", "error": str(exc)}

    return results


def verify_expectations(res: dict, mode: str) -> None:
    assert res["FP1_sequential_rebind"]["status"] == "ok", res["FP1_sequential_rebind"]
    assert res["FP1_sequential_rebind"]["project_hints_derived"] is False, res["FP1_sequential_rebind"]
    assert res["FP1_sequential_rebind"]["project_hints_violations"] == [], res["FP1_sequential_rebind"]

    assert res["FP1_try_both_kill"]["status"] == "ok", res["FP1_try_both_kill"]
    assert res["FP1_try_both_kill"]["project_hints_derived"] is False, res["FP1_try_both_kill"]
    assert res["FP1_try_both_kill"]["project_hints_violations"] == [], res["FP1_try_both_kill"]

    assert res["FP3_update_after_rebind"]["status"] == "ok", res["FP3_update_after_rebind"]
    assert res["FP3_update_after_rebind"]["project_hints_derived"] is True, res["FP3_update_after_rebind"]
    assert res["FP3_update_after_rebind"]["project_hints_violations"] == [["CHORUS", 2]], res["FP3_update_after_rebind"]

    if mode == "failing_first_9d70da367":
        for case_key in (
            "Case1_try_except_rebind",
            "Case1b_try_mid_raise_except_pass",
            "Case2_loop_carried_1hop",
            "Case2b_loop_carried_3hop",
            "Case3_kill_alias_after_if_join",
        ):
            assert res[case_key]["status"] == "ok", (case_key, res[case_key])
            assert res[case_key]["project_hints_derived"] is True, (case_key, res[case_key])
        assert res["Case4_no_spurious_container_merge"]["secret_leaked_into_c1"] is False, (
            res["Case4_no_spurious_container_merge"]
        )
        for case_key in (
            "Case5a_try_nested_if_raise_before_rebind",
            "Case5b_with_suppression_skips_rebind",
            "Case6_match_guard_fallthrough_retains_binding",
            "Case7_match_capture_alias_unbound_elsewhere",
        ):
            assert res[case_key]["status"] == "ok", (case_key, res[case_key])
            assert res[case_key]["project_hints_derived"] is False, (case_key, res[case_key])
    elif mode.startswith("failing_first"):
        for case_key in (
            "Case1_try_except_rebind",
            "Case1b_try_mid_raise_except_pass",
            "Case2_loop_carried_1hop",
            "Case2b_loop_carried_3hop",
            "Case5a_try_nested_if_raise_before_rebind",
            "Case5b_with_suppression_skips_rebind",
            "Case6_match_guard_fallthrough_retains_binding",
            "Case7_match_capture_alias_unbound_elsewhere",
        ):
            assert res[case_key]["status"] == "ok", (case_key, res[case_key])
            assert res[case_key]["project_hints_derived"] is False, (case_key, res[case_key])
        assert res["Case3_kill_alias_after_if_join"]["status"] == "refused", res["Case3_kill_alias_after_if_join"]
        assert "unresolved or uncertain receiving callable" in res["Case3_kill_alias_after_if_join"]["error"], (
            res["Case3_kill_alias_after_if_join"]
        )
        assert res["Case4_no_spurious_container_merge"]["secret_leaked_into_c1"] is True, (
            res["Case4_no_spurious_container_merge"]
        )
        assert res["R2_3a_multi_bound_starred_prefix"] == {
            "status": "ok",
            "tables": [["*prefix", "--check"]],
        }, res["R2_3a_multi_bound_starred_prefix"]
        assert res["R2_3b_param_shadowing"] == {
            "status": "ok",
            "tables": [["python3", "-m", "data_sheets_schema.target"]],
        }, res["R2_3b_param_shadowing"]
    elif mode.startswith("after_fix"):
        for case_key in (
            "Case1_try_except_rebind",
            "Case1b_try_mid_raise_except_pass",
            "Case2_loop_carried_1hop",
            "Case2b_loop_carried_3hop",
            "Case3_kill_alias_after_if_join",
            "Case5a_try_nested_if_raise_before_rebind",
            "Case5b_with_suppression_skips_rebind",
            "Case6_match_guard_fallthrough_retains_binding",
            "Case7_match_capture_alias_unbound_elsewhere",
        ):
            assert res[case_key]["status"] == "ok", (case_key, res[case_key])
            assert res[case_key]["project_hints_derived"] is True, (case_key, res[case_key])
            assert res[case_key]["project_hints_violations"] == [["CHORUS", 2]], (case_key, res[case_key])
        assert res["Case4_no_spurious_container_merge"]["secret_leaked_into_c1"] is False, (
            res["Case4_no_spurious_container_merge"]
        )
        assert res["R2_3a_multi_bound_starred_prefix"] == {
            "status": "ok",
            "tables": [
                ["python3", "-m", "data_sheets_schema.a", "--check"],
                ["python3", "-m", "data_sheets_schema.b", "--check"],
            ],
        }, res["R2_3a_multi_bound_starred_prefix"]
        assert res["R2_3b_param_shadowing"]["status"] == "refused", res["R2_3b_param_shadowing"]
        assert "unresolvable -m operand" in res["R2_3b_param_shadowing"]["error"], res["R2_3b_param_shadowing"]


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    scan_override = None
    if mode == "failing_first_9d70da367":
        scan_override = OUT_DIR / "scan_9d70da367.py.snap"
    res = check_cases(scan_override=scan_override)
    tmp_out = Path(f"/tmp/pr5665_round3_{mode}.json")
    tmp_out.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_file = OUT_DIR / f"{mode}.json"
        out_file.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass
    print(json.dumps(res, indent=2, sort_keys=True))
    verify_expectations(res, mode)


if __name__ == "__main__":
    main()
