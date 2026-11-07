"""U3-A driver origin witnesses after namespace-path repetition, 2026-11-07.

Synthetic import metadata only: no recorder, native binary, network or test
subprocess. Duplicate own paths must not hide a foreign module or finder.
"""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "_native_u3a_test_driver",
    ROOT / "scripts/adhoc/run_native_u3a_tests_20261107.py",
)
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)
PACKAGE = ROOT / "src/data_sheets_schema"


@pytest.fixture
def namespace(monkeypatch):
    package = ModuleType("data_sheets_schema")
    package.__path__ = [str(PACKAGE)] * 25
    monkeypatch.setitem(sys.modules, "data_sheets_schema", package)
    return package


@pytest.mark.parametrize("copies", [1, 25])
def test_own_namespace_repetitions_preserve_evidence_without_mutation(namespace, copies):
    namespace.__path__ = [str(PACKAGE)] * copies
    original_paths = namespace.__path__
    original_sys_path = sys.path
    sys_path_values = list(sys.path)

    witness = driver.origin_witness()

    assert witness["package_paths_raw"] == [str(PACKAGE)] * copies
    assert witness["package_paths"] == [str(PACKAGE)] * copies
    assert witness["sys_path"] == sys_path_values
    assert namespace.__path__ is original_paths
    assert namespace.__path__ == [str(PACKAGE)] * copies
    assert sys.path is original_sys_path
    assert sys.path == sys_path_values


def test_raw_spelling_is_retained_beside_resolved_paths(namespace):
    raw = str(PACKAGE / ".." / "data_sheets_schema")
    namespace.__path__ = [raw, raw]

    witness = driver.origin_witness()

    assert witness["package_paths_raw"] == [raw, raw]
    assert witness["package_paths"] == [str(PACKAGE), str(PACKAGE)]
    assert namespace.__path__ == [raw, raw]


@pytest.mark.parametrize("case", [
    "empty", "foreign", "own_then_foreign", "foreign_then_own", "own_subdirectory",
])
def test_empty_or_nonexact_namespace_is_refused(namespace, tmp_path, case):
    own = str(PACKAGE)
    foreign = str(tmp_path / "foreign/data_sheets_schema")
    namespace.__path__ = {
        "empty": [],
        "foreign": [foreign],
        "own_then_foreign": [own] * 25 + [foreign],
        "foreign_then_own": [foreign] + [own] * 25,
        "own_subdirectory": [str(PACKAGE / "subpackage")],
    }[case]
    original = list(namespace.__path__)

    with pytest.raises(RuntimeError, match="mixed project namespace"):
        driver.origin_witness()

    assert namespace.__path__ == original


def test_duplicate_own_namespace_still_refuses_foreign_loaded_module(
    namespace, monkeypatch, tmp_path,
):
    name = "data_sheets_schema._u3a_foreign_witness"
    module = ModuleType(name)
    module.__file__ = str(tmp_path / "foreign.py")
    monkeypatch.setitem(sys.modules, name, module)

    with pytest.raises(RuntimeError, match="foreign project module: " + name):
        driver.origin_witness()


def test_duplicate_own_namespace_still_refuses_foreign_subpackage(
    namespace, monkeypatch, tmp_path,
):
    name = "data_sheets_schema._u3a_foreign_package_witness"
    module = ModuleType(name)
    module.__path__ = [str(PACKAGE / "local"), str(tmp_path / "foreign")]
    monkeypatch.setitem(sys.modules, name, module)

    with pytest.raises(RuntimeError, match="foreign project subpackage: " + name):
        driver.origin_witness()


def test_duplicate_own_namespace_still_refuses_editable_finder(namespace, monkeypatch):
    class EditableFinder:
        def __repr__(self):
            return "__editable___synthetic_project_finder"

    monkeypatch.setattr(sys, "meta_path", [*sys.meta_path, EditableFinder()])

    with pytest.raises(RuntimeError, match="editable-install import finder is active"):
        driver.origin_witness()
