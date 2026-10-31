"""Caller-only v9 selection: #5364 CI run 41015551110, #5226 R_V5-F5.

Synthetic artifacts and source inspection; no providers or corpus writes.
"""
import ast
import inspect
from pathlib import Path

import pytest

from data_sheets_schema import provedown, report_claims as reports


ROOT = Path(__file__).resolve().parents[1]
DECLARED = {"Dataset": {"total_files"}, "CoreDataset": {"total_files"}}
REPORT = "Count `3`{pd: full:/total_files}"


@pytest.mark.parametrize("options,instrument", [
    ({}, reports.REPORT_CLAIMS_INSTRUMENT),
    ({"instrument_version": 7}, reports.REPORT_CLAIMS_INSTRUMENT_V7),
    ({"instrument_version": 8}, reports.REPORT_CLAIMS_INSTRUMENT),
])
def test_legacy_selection_never_checks_watermarks(monkeypatch, options, instrument):
    def forbidden(*args, **kwargs):
        pytest.fail("watermarks require an explicit caller opt-in")

    monkeypatch.setattr(provedown, "verify_watermarks", forbidden)
    block = reports.check_report(REPORT, {"total_files": 2}, {}, DECLARED, **options)
    assert block["instrument"] == instrument
    assert block["instrument"] != reports.REPORT_CLAIMS_INSTRUMENT_V9
    assert "watermarks" not in block
    assert block["findings"] == []


@pytest.mark.parametrize("options", [
    {"instrument_version": 9},
    {"check_watermarks": True},
])
def test_each_explicit_optin_labels_the_expanded_measurement(options):
    block = reports.check_report(REPORT, {"total_files": 2}, {}, DECLARED, **options)
    assert block["instrument"] == reports.REPORT_CLAIMS_INSTRUMENT_V9
    assert block["watermarks"]["mismatched"] == 1
    assert block["findings"][0]["kind"].startswith("watermark_")


@pytest.mark.parametrize("artifact", [
    "report", "full", "core", "snapshot", "receipt", "manifest", "chunk_texts",
])
@pytest.mark.parametrize("version", [None, 7, 8])
def test_measured_artifacts_cannot_select_v9(tmp_path, artifact, version):
    selection = {"instrument_version": 9, "report_claims_version": 9,
                 "version": 9, "check_watermarks": True,
                 "instrument": reports.REPORT_CLAIMS_INSTRUMENT_V9,
                 "receipt_format_version": 5}
    inputs = {"report": REPORT, "full": {"total_files": 2}, "core": {},
              "declared": DECLARED}
    if artifact == "report":
        path = tmp_path / "report.md"
        path.write_text(f"---\n{selection}\n---\n{REPORT}\n<!-- {selection} -->\n")
        inputs[artifact] = path
    elif artifact == "chunk_texts":
        inputs[artifact] = {"c001": str(selection)}
    else:
        inputs[artifact] = selection
    if version is not None:
        inputs["instrument_version"] = version
    block = reports.check_report(**inputs)
    assert block["instrument"] == (reports.REPORT_CLAIMS_INSTRUMENT_V7 if version == 7
                                   else reports.REPORT_CLAIMS_INSTRUMENT)
    assert "watermarks" not in block


def test_environment_cannot_select_v9(monkeypatch):
    for key, value in {
        "INSTRUMENT_VERSION": "9", "REPORT_CLAIMS_VERSION": "9",
        "REPORT_CLAIMS_INSTRUMENT_VERSION": "9", "CHECK_WATERMARKS": "True",
        "REPORT_CLAIMS_INSTRUMENT_V9": reports.REPORT_CLAIMS_INSTRUMENT_V9,
        "RECEIPTS_V5_INSTRUMENT": "1", "D4D_REPORT_CLAIMS_VERSION": "9",
        "D4D_CHECK_WATERMARKS": "1",
    }.items():
        monkeypatch.setenv(key, value)
    for options, expected in [({}, reports.REPORT_CLAIMS_INSTRUMENT),
                              ({"instrument_version": 7}, reports.REPORT_CLAIMS_INSTRUMENT_V7)]:
        block = reports.check_report(REPORT, {"total_files": 2}, {}, DECLARED, **options)
        assert block["instrument"] == expected
        assert "watermarks" not in block


def test_selectors_only_come_from_caller_parameters():
    """Guard all selector writes, including a future artifact/environment fallback."""
    for function in (reports.check_report, reports._check_report_text):
        signature = inspect.signature(function)
        assert signature.parameters["instrument_version"].default == 8
        assert signature.parameters["check_watermarks"].default is False
        tree = ast.parse(inspect.getsource(function))
        writes = [node for node in ast.walk(tree) if isinstance(node, ast.Name)
                  and isinstance(node.ctx, ast.Store)
                  and node.id in {"instrument_version", "check_watermarks"}]
        if function is reports.check_report:
            assert writes == []
            delegation = next(node for node in ast.walk(tree) if isinstance(node, ast.Call)
                              and isinstance(node.func, ast.Name)
                              and node.func.id == "_check_report_text")
            for key in ("instrument_version", "check_watermarks"):
                value = next(kw.value for kw in delegation.keywords if kw.arg == key)
                assert isinstance(value, ast.Name) and value.id == key
        else:
            assert len(writes) == 1 and writes[0].id == "instrument_version"
            optin = next(node for node in tree.body[0].body if isinstance(node, ast.If)
                         and isinstance(node.test, ast.Name) and node.test.id == "check_watermarks")
            assert ast.dump(optin) == ast.dump(ast.parse(
                "if check_watermarks:\n    instrument_version = 9").body[0])


def test_production_callers_do_not_opt_in():
    """rglob includes hidden/ignored Python files; inspect code, not docstrings."""
    callers = set()
    for directory in (ROOT / "src", ROOT / "scripts"):
        for path in sorted(directory.rglob("*.py")):
            relative = path.relative_to(ROOT).as_posix()
            if relative == "src/data_sheets_schema/report_claims.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            aliases = set()
            evidence_modules = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.endswith("report_claims"):
                        aliases.update(alias.asname or alias.name for alias in node.names
                                       if alias.name == "check_report")
                    if node.module in {None, "data_sheets_schema"}:
                        evidence_modules.update(alias.asname or alias.name for alias in node.names
                                                if alias.name == "evidence_assertions")
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                location = f"{relative}:{node.lineno}"
                for kw in node.keywords:
                    assert kw.arg != "check_watermarks", location
                    if kw.arg == "instrument_version" and isinstance(kw.value, ast.Constant):
                        assert kw.value.value != 9, location
                    if kw.arg == "report_claims_version":
                        if isinstance(kw.value, ast.Constant):
                            assert type(kw.value.value) is int and kw.value.value in (7, 8), location
                        else:
                            assert relative == "scripts/adhoc/receipts_v5_merge_probes_20261029/report_inert.py"
                            assert isinstance(kw.value, ast.Name) and kw.value.id == "v"
                            loop = next(n for n in ast.walk(tree) if isinstance(n, ast.For)
                                        and isinstance(n.target, ast.Name) and n.target.id == "v")
                            assert ast.literal_eval(loop.iter) == (8, 7)
                # The evidence API shares the name but has different inputs.
                if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                        and node.func.value.id in evidence_modules):
                    continue
                is_checker = ((isinstance(node.func, ast.Name) and node.func.id in aliases)
                              or (isinstance(node.func, ast.Attribute) and node.func.attr == "check_report"))
                if not is_checker:
                    continue
                callers.add(relative)
                for kw in node.keywords:
                    assert kw.arg is not None, f"opaque check_report kwargs at {location}"
                    if kw.arg == "instrument_version":
                        # Backfill exposes an explicit replay parameter, defaulting
                        # to v8. It does not read a version from the measured record.
                        assert relative == "src/data_sheets_schema/backfill_checks.py", location
                        assert isinstance(kw.value, ast.Name) and kw.value.id == "report_claims_version"
                        compute = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                                       and n.name == "compute")
                        defaults = dict(zip((a.arg for a in compute.args.kwonlyargs),
                                            compute.args.kw_defaults))
                        assert ast.literal_eval(defaults["report_claims_version"]) == 8
                        assert not any(isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
                                       and n.id == "report_claims_version" for n in ast.walk(compute))
    assert {"src/data_sheets_schema/api_runner.py", "src/data_sheets_schema/backfill_checks.py",
            "scripts/report_claims_removal_diff.py"} <= callers


def test_runner_report_gate_uses_the_default_checker():
    tree = ast.parse((ROOT / "src/data_sheets_schema/api_runner.py").read_text())
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    for function, callee in [("_gate_report", "report_claims_block"),
                             ("report_claims_block", "check_report")]:
        calls = [node for node in ast.walk(functions[function]) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == callee]
        assert calls
        for call in calls:
            assert not any(kw.arg in {None, "check_watermarks", "instrument_version"}
                           for kw in call.keywords)
