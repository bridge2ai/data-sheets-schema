"""Exact lexical ancestry oracle; no native executable or provider calls."""
from copy import deepcopy
from itertools import product
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_registration as registration
from tests.test_native_shared_contract import selection


def old_ancestor(parent, child):
    """Independent prior operation, including flavor and subclass semantics."""
    return parent in child.parents


def outcome(function, *args, **kwargs):
    try:
        return ("returned", function(*args, **kwargs))
    except Exception as error:
        return ("raised", type(error), str(error))


def test_exact_posix_parts_match_old_membership_without_resolving(monkeypatch):
    spellings = ("", ".", "..", "../a", "/", "//", "///", "/a", "/a/b",
                 "/a/b/c", "/ab", "/a/b2", "/a/../b", "/a/./b", "/a//b",
                 "/a/", "a", "a/b", "a/../b", "é/子", "/é/子")
    pairs = [(factory(left), factory(right))
             for factory in (PurePosixPath, Path)
             for left, right in product(spellings, repeat=2)]
    # The actual call sites also mix exact PosixPath and PurePosixPath.
    pairs += [(PurePosixPath(left), Path(right))
              for left, right in product(spellings, repeat=2)]
    pairs += [(Path(left), PurePosixPath(right))
              for left, right in product(spellings, repeat=2)]
    expected = [old_ancestor(parent, child) for parent, child in pairs]
    monkeypatch.setattr(Path, "resolve",
                        lambda *a, **k: pytest.fail("lexical oracle resolved a path"))
    assert [c._strict_path_ancestor(parent, child) for parent, child in pairs] == expected


def test_exact_posix_fast_path_does_not_construct_ancestor_sequence(monkeypatch):
    def forbidden(path):
        pytest.fail("exact POSIX fast path constructed the old ancestor sequence")
    monkeypatch.setattr(PurePosixPath, "parents", property(forbidden))
    assert c._strict_path_ancestor(PurePosixPath("/a"), PurePosixPath("/a/b"))
    assert not c._strict_path_ancestor(PurePosixPath("/a"), PurePosixPath("/a"))
    assert not c._strict_path_ancestor(PurePosixPath("."), PurePosixPath("/a"))


def test_other_flavors_and_custom_paths_keep_original_membership():
    windows = [PureWindowsPath(value) for value in
               ("C:/", "C:/a", "c:/A/b", "C:a", "C:a/b", "D:/a/b", "//server/share/a")]
    posix = [PurePosixPath(value) for value in ("/", "/a", "a", "a/b", "//server/share/a")]
    for parent, child in product(windows + posix, repeat=2):
        assert c._strict_path_ancestor(parent, child) == old_ancestor(parent, child)

    class Custom(PurePosixPath):
        @property
        def parents(self):
            raise RuntimeError("custom ancestry remains observable")

    child = Custom("/a/b")
    assert outcome(c._strict_path_ancestor, PurePosixPath("/a"), child) == \
        outcome(old_ancestor, PurePosixPath("/a"), child)


@pytest.mark.parametrize("selection_path,stage_root", [
    ("/input/selection", "/stage"), ("/stage", "/stage"), ("/stage/selection", "/stage"),
    ("/stage2/selection", "/stage"), ("/a", "/"), ("/", "/stage"),
    ("/a/../selection", "/stage"), ("/a/./selection", "/stage"),
    ("/a//selection", "/stage"), ("/a/selection/", "/stage"),
    ("//a/selection", "/stage"), ("relative", "/stage"), (None, "/stage"),
])
def test_role_paths_result_and_first_error_match_old_operation(monkeypatch, selection_path, stage_root):
    current = outcome(c.role_paths, selection_path, stage_root)
    monkeypatch.setattr(c, "_strict_path_ancestor", old_ancestor)
    assert outcome(c.role_paths, selection_path, stage_root) == current


@pytest.mark.parametrize("path", [
    "/attempt/stages", "/attempt/stages/nested/file", "/attempt/stages2/file",
    "/attempt", "/", "/bad/../file", "/bad/./file", "/bad//file", "/bad/file/",
    "//bad/file", "relative", None, 12,
])
def test_actual_selection_parser_preserves_overlap_and_validation(monkeypatch, path):
    doc = selection().document()
    doc["inputs"]["bundle"]["path"] = path
    raw = c.canonical(doc)
    current = outcome(c.parse_selection, raw)
    with monkeypatch.context() as patch:
        patch.setattr(c, "_strict_path_ancestor", old_ancestor)
        assert outcome(c.parse_selection, raw) == current
    if path in ("/attempt/stages", "/attempt/stages/nested/file"):
        assert current[0:2] == ("raised", ValueError)
        assert "overlaps its own declaration or mutable stage root" in current[2]
    elif path in ("/attempt/stages2/file", "/attempt", "/"):
        assert current == ("returned", doc)
    else:
        assert current[0:2] == ("raised", ValueError)


def test_every_current_authority_is_checked_and_overlap_keeps_first_error(monkeypatch):
    doc = selection().document()
    calls = []
    current = c._strict_path_ancestor

    def observed(parent, child):
        calls.append((str(parent), str(child)))
        return current(parent, child)

    monkeypatch.setattr(c, "_strict_path_ancestor", observed)
    c.parse_selection(c.canonical(doc))
    expected = [doc["receipt_policy"], *doc["selection"]["assets"].values(),
                *(doc["inputs"][key] for key in ("bundle", "chunk_manifest", "context")),
                *doc["inputs"]["full_schema"]["sources"], *doc["inputs"]["core_schema"]["sources"]]
    assert [child for parent, child in calls if parent == doc["stage_root"]] == \
        [doc["registration_path"], *(pin["path"] for pin in expected)]
    # A current declaration change cannot reuse the prior successful result.
    doc["inputs"]["bundle"]["path"] = doc["stage_root"] + "/new-authority"
    doc["inputs"]["context"]["path"] = doc["inputs"]["chunk_manifest"]["path"]
    doc["inputs"]["context"]["sha256"] = "0" * 64
    raw = c.canonical(doc)
    result = outcome(c.parse_selection, raw)
    monkeypatch.setattr(c, "_strict_path_ancestor", old_ancestor)
    assert outcome(c.parse_selection, raw) == result
    assert "overlaps its own declaration or mutable stage root" in result[2]


@pytest.mark.parametrize("change", ["none", "protected_below", "equal_reserved", "nested_reserved",
                                  "missing_parent", "physical_alias"])
def test_actual_reservations_preserve_physical_checks_and_first_errors(tmp_path, monkeypatch, change):
    root = tmp_path.resolve()
    doc = selection().document()
    doc["stage_root"] = str(root / "stage")
    selected = {
        "selection_raw_json": c.canonical(doc).decode(),
        "runtime_path": str(root / "runtime"),
        "policy": {"readonly_lookups": {"output_directories": [doc["stage_root"]],
                                         "inputs": [str(root / "input")]}}}
    value = {"attempt_directory": str(root / "attempt"),
             "evidence_directory": str(root / "evidence"),
             "composition": str(root / "composition"), "system_path": str(root / "system"),
             "permission_probe": str(root / "probe"),
             "runtime": {"executable": {"path": str(root / "executable")}}}
    if change == "protected_below":
        selected["policy"]["readonly_lookups"]["inputs"] = [str(root / "attempt" / "input")]
    elif change == "equal_reserved":
        value["evidence_directory"] = value["attempt_directory"]
    elif change == "nested_reserved":
        value["evidence_directory"] = str(root / "attempt" / "nested")
    elif change == "missing_parent":
        value["evidence_directory"] = str(root / "absent" / "evidence")
    elif change == "physical_alias":
        (root / "real").mkdir()
        (root / "attempt").symlink_to(root / "real", target_is_directory=True)
    actual = outcome(registration._paths, deepcopy(value), deepcopy(selected), fresh=False)
    monkeypatch.setattr(c, "_strict_path_ancestor", old_ancestor)
    assert outcome(registration._paths, deepcopy(value), deepcopy(selected), fresh=False) == actual
    if change == "none":
        assert actual[0] == "returned"
    else:
        assert actual[0:2] == ("raised", ValueError)
    if change == "physical_alias":
        assert actual[2] == "reserved paths must be canonical physical paths"
