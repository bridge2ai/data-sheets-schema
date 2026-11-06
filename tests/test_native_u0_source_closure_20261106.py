"""Synthetic source-closure tests for U0-R7, 2026-11-06.

Inputs: tiny temporary diagnostic/foreign packages and a copied guard helper.
Outputs: in-memory inventories only. No real recorder, native or provider call.
"""
import hashlib
import importlib
import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import types

import pytest


HELPER = Path(__file__).resolve().parents[1] / "scripts/adhoc/native_u0_source_closure_20261106.py"
_spec = importlib.util.spec_from_file_location("u0_source_closure_test_helper", HELPER)
closure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(closure)


@pytest.fixture
def project_state():
    saved = {name: module for name, module in sys.modules.items()
             if name == closure.PACKAGE or name.startswith(closure.PACKAGE + ".")}
    old_meta = sys.meta_path
    sys.meta_path = list(old_meta)
    for name in saved:
        del sys.modules[name]
    try:
        yield
    finally:
        for name in tuple(sys.modules):
            if name == closure.PACKAGE or name.startswith(closure.PACKAGE + "."):
                del sys.modules[name]
        sys.modules.update(saved)
        sys.meta_path = old_meta


def diagnostic(tmp_path):
    root = tmp_path.resolve() / "diagnostic"
    package = root / "src" / closure.PACKAGE
    package.mkdir(parents=True)
    helper = root / closure.HELPER_RELATIVE
    helper.parent.mkdir(parents=True)
    raw = HELPER.read_bytes()
    helper.write_bytes(raw)
    (package / "__init__.py").write_bytes(closure.package_bootstrap(hashlib.sha256(raw).hexdigest()))
    return root, package


def bind_package(package):
    spec = importlib.util.spec_from_file_location(closure.PACKAGE, package / "__init__.py",
                                                submodule_search_locations=[str(package)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[closure.PACKAGE] = module
    spec.loader.exec_module(module)
    return module


def fake_module(name, path, *, namespaces=None):
    module = types.ModuleType(name)
    spec = importlib.machinery.ModuleSpec(name, loader=None, origin=str(path) if path else None,
                                        is_package=namespaces is not None)
    if path:
        module.__file__ = str(path)
    if namespaces is not None:
        module.__path__ = list(namespaces)
        spec.submodule_search_locations = list(namespaces)
    module.__spec__ = spec
    return module


def test_first_import_bootstrap_binds_root_and_normal_child_packages(tmp_path, project_state):
    root, package = diagnostic(tmp_path)
    nested = package / "nested"
    nested.mkdir()
    (nested / "__init__.py").write_text('"""Synthetic child package."""\n')
    (nested / "answer.py").write_text("answer = 17\n")
    module = bind_package(package)
    imported = importlib.import_module(closure.PACKAGE + ".nested.answer")
    assert imported.answer == 17
    evidence = closure.assert_source_closure(root)
    assert evidence["project_finder_first"] and evidence["ordinary_root_package"]
    assert evidence["namespace_pruned"] is False
    assert evidence["project_module_count"] == 3
    assert all(row.get("file", "").startswith(str(package)) for row in evidence["modules"])
    assert module.__path__ == [str(package)]
    assert evidence["modules"][0]["file"] == str(package / "__init__.py")
    assert all("sha256" in row for row in evidence["modules"])


def test_mixed_existing_namespace_refused_without_pruning(tmp_path, project_state):
    root, package = diagnostic(tmp_path)
    foreign = tmp_path / "primary" / closure.PACKAGE
    foreign.mkdir(parents=True)
    module = fake_module(closure.PACKAGE, None, namespaces=[str(package), str(foreign)])
    sys.modules[closure.PACKAGE] = module
    before = list(module.__path__)
    with pytest.raises(RuntimeError, match="namespace"):
        closure.install_source_closure(root)
    assert module.__path__ == before
    assert not hasattr(module, closure._GUARD_ATTRIBUTE)


def test_foreign_already_loaded_child_refused_without_removal(tmp_path, project_state):
    root, package = diagnostic(tmp_path)
    bind_package(package)
    foreign = tmp_path / "primary" / "wrong.py"
    foreign.parent.mkdir()
    foreign.write_text("answer = 23\n")
    name = closure.PACKAGE + ".wrong"
    wrong = fake_module(name, foreign)
    sys.modules[name] = wrong
    with pytest.raises(RuntimeError, match="foreign"):
        closure.assert_source_closure(root)
    with pytest.raises(RuntimeError, match="foreign"):
        closure.install_source_closure(root)
    assert sys.modules[name] is wrong


def test_missing_child_cannot_fall_through_to_primary_editable_finder(tmp_path, project_state, monkeypatch):
    root, package = diagnostic(tmp_path)
    module = bind_package(package)
    foreign = tmp_path / "primary" / closure.PACKAGE
    foreign.mkdir(parents=True)
    (foreign / "foreign_only.py").write_text("answer = 99\n")
    class EditableFallback:
        calls = 0
        def find_spec(self, fullname, path=None, target=None):
            if fullname == closure.PACKAGE + ".foreign_only":
                self.calls += 1
                return importlib.util.spec_from_file_location(fullname, foreign / "foreign_only.py")
    fallback = EditableFallback()
    sys.meta_path.insert(1, fallback)
    monkeypatch.syspath_prepend(str(foreign.parent))
    with pytest.raises(ModuleNotFoundError) as raised:
        importlib.import_module(closure.PACKAGE + ".foreign_only")
    assert raised.value.name == closure.PACKAGE + ".foreign_only"
    assert fallback.calls == 0 and module.__path__ == [str(package)]
    assert closure.assert_source_closure(root)["project_module_count"] == 1


def test_existing_primary_source_wins_neither_child_resolution_nor_specs(tmp_path, project_state, monkeypatch):
    root, package = diagnostic(tmp_path)
    (package / "same.py").write_text("identity = 'diagnostic'\n")
    foreign = tmp_path / "primary" / closure.PACKAGE
    foreign.mkdir(parents=True)
    (foreign / "same.py").write_text("identity = 'primary'\n")
    bind_package(package)
    monkeypatch.syspath_prepend(str(foreign.parent))
    imported = importlib.import_module(closure.PACKAGE + ".same")
    assert imported.identity == "diagnostic"
    assert imported.__spec__.origin == str(package / "same.py")


def test_namespace_widening_is_refused_on_next_child_import(tmp_path, project_state):
    root, package = diagnostic(tmp_path)
    module = bind_package(package)
    foreign = tmp_path / "primary" / closure.PACKAGE
    foreign.mkdir(parents=True)
    module.__path__.append(str(foreign))
    with pytest.raises(RuntimeError, match="namespace"):
        importlib.import_module(closure.PACKAGE + ".new_child")
    with pytest.raises(RuntimeError, match="namespace"):
        closure.assert_source_closure(root)
    assert str(foreign) in module.__path__


def test_external_and_stdlib_imports_are_not_claimed(tmp_path, project_state):
    root, package = diagnostic(tmp_path)
    module = bind_package(package)
    finder = getattr(module, closure._GUARD_ATTRIBUTE)
    assert finder.find_spec("json") is None
    assert finder.find_spec("linkml_runtime") is None
    assert finder.find_spec("data_sheets_schema_other") is None
    assert "prior site/.pth" in closure.assert_source_closure(root)["dependency_scope"]


def test_removed_or_displaced_guard_refused(tmp_path, project_state):
    root, package = diagnostic(tmp_path)
    module = bind_package(package)
    finder = getattr(module, closure._GUARD_ATTRIBUTE)
    sys.meta_path.remove(finder)
    with pytest.raises(RuntimeError, match="not first and active"):
        closure.assert_source_closure(root)
    sys.meta_path.append(finder)
    with pytest.raises(RuntimeError, match="not first and active"):
        closure.assert_source_closure(root)


def test_hash_bound_bootstrap_refuses_changed_helper_before_execution(tmp_path, project_state):
    root, package = diagnostic(tmp_path)
    helper = root / closure.HELPER_RELATIVE
    helper.write_bytes(helper.read_bytes() + b"\n# altered\n")
    with pytest.raises(RuntimeError, match="helper hash differs"):
        bind_package(package)


def test_noncanonical_bootstrap_and_foreign_root_file_refused(tmp_path, project_state):
    root, package = diagnostic(tmp_path)
    module = bind_package(package)
    path = package / "__init__.py"
    original = path.read_bytes()
    path.write_bytes(original + b"\n")
    with pytest.raises(RuntimeError, match="bootstrap"):
        closure.assert_source_closure(root)
    path.write_bytes(original)
    foreign = tmp_path / "primary.py"
    foreign.write_text("# foreign root\n")
    module.__file__ = str(foreign)
    module.__spec__.origin = str(foreign)
    with pytest.raises(RuntimeError, match="foreign"):
        closure.assert_source_closure(root)


def test_closure_install_is_idempotent_and_preserves_guard_order(tmp_path, project_state):
    root, package = diagnostic(tmp_path)
    module = bind_package(package)
    finder = getattr(module, closure._GUARD_ATTRIBUTE)
    count = len(sys.meta_path)
    evidence = closure.install_source_closure(root)
    assert evidence["project_finder_first"] and len(sys.meta_path) == count
    assert sys.meta_path[0] is finder


@pytest.mark.parametrize("digest", ["", "0" * 63, "A" * 64, "z" * 64, None])
def test_bootstrap_requires_exact_sha256(digest):
    with pytest.raises(ValueError, match="SHA-256"):
        closure.package_bootstrap(digest)
