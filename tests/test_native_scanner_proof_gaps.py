"""Offline regressions for review issues 6245–6248, 2026-11-15."""
import ast

import pytest

from tests.test_native_u1_scanner_contracts import _procedure_root
from tests.test_native_u5_scanner import copied_route, PREPARER, RUNNER, scan


def test_6245_class_descriptor_refuses(tmp_path):
    root = _procedure_root(tmp_path)
    assert scan.derive_native_shared_procedure(root)
    path = root / 'src/data_sheets_schema/native_shared_stage/__init__.py'
    text = path.read_text()
    assert text.count('class _Replay:') == 1
    path.write_text(text.replace('class _Replay:', 'class _Replay:\n    options = property(lambda self: {})'))
    with pytest.raises(scan.ConfigError, match='native packet options are replaced, mutated or aliased'):
        scan.derive_native_shared_procedure(root)


def test_6245_dynamic_receiver_lookup_refuses(tmp_path):
    root = _procedure_root(tmp_path)
    assert scan.derive_native_shared_procedure(root)
    path = root / 'src/data_sheets_schema/native_shared_stage/__init__.py'
    text = path.read_text()
    marker = '        self.pending = None\n        self.pending_predecessor = None'
    assert text.count(marker) == 1
    mutation = "        name = 'options'\n        self.__getattribute__(name).clear()\n"
    path.write_text(text.replace(marker, mutation + marker))
    with pytest.raises(scan.ConfigError, match='native packet options are replaced, mutated or aliased'):
        scan.derive_native_shared_procedure(root)


def test_6245_returned_receiver_options_refuses(tmp_path):
    root = _procedure_root(tmp_path)
    assert scan.derive_native_shared_procedure(root)
    path = root / 'src/data_sheets_schema/native_shared_stage/__init__.py'
    text = path.read_text()
    marker = '        self._base()\n'
    assert text.count(marker) == 1
    path.write_text(text.replace(marker, marker + '        self.run().options.clear()\n'))
    with pytest.raises(scan.ConfigError, match='native packet options are replaced, mutated or aliased'):
        scan.derive_native_shared_procedure(root)


def test_6245_returned_receiver_reflection_refuses(tmp_path):
    for index, receiver in enumerate(('self.run()', 'self._owner()')):
        root = _procedure_root(tmp_path / str(index))
        assert scan.derive_native_shared_procedure(root)
        path = root / 'src/data_sheets_schema/native_shared_stage/__init__.py'
        text = path.read_text()
        if index:
            text = text.replace('class _Replay:', 'class _Replay:\n    def _owner(self):\n        return self\n')
        marker = '        self._base()\n'
        assert text.count(marker) == 1
        mutation = "        name = 'options'\n        owner = " + receiver + "\n        getattr(owner, name).clear()\n"
        path.write_text(text.replace(marker, marker + mutation))
        with pytest.raises(scan.ConfigError, match='native packet options are replaced, mutated or aliased'):
            scan.derive_native_shared_procedure(root)


def test_6245_nested_receiver_return_refuses(tmp_path):
    root = _procedure_root(tmp_path)
    assert scan.derive_native_shared_procedure(root)
    path = root / 'src/data_sheets_schema/native_shared_stage/__init__.py'
    text = path.read_text()
    marker = '    def run(self):\n'
    assert text.count(marker) == 1
    mutation = ("        def owner():\n            return self\n"
                "        name = 'options'\n        getattr(owner(), name).clear()\n")
    path.write_text(text.replace(marker, marker + mutation))
    with pytest.raises(scan.ConfigError, match='native packet options are replaced, mutated or aliased'):
        scan.derive_native_shared_procedure(root)


def test_6246_module_execution_refuses(tmp_path):
    mutations = [
        'from .api_runner import RunSpec as _R\n_R.__post_init__ = lambda self: None',
        "import importlib\nimportlib.import_module('data_sheets_schema.native_runtime_profiles').require_production = lambda value: None",
        "import sys\nsys.modules['data_sheets_schema.native_runtime_profiles'].require_production = lambda value: None",
        "setattr(sys.modules['data_sheets_schema.api_runner'].RunSpec, '__post_init__', lambda self: None)",
        'unexpected_call()',
    ]
    for index, mutation in enumerate(mutations):
        root = copied_route(tmp_path / str(index))
        assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
        path = root / PREPARER
        path.write_text(path.read_text() + '\n' + mutation + '\n')
        with pytest.raises(scan.ConfigError, match='v2 producer module execution is not exact'):
            scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def test_6247_pre_guard_mutation_refuses(tmp_path):
    mutations = ['spec.native_shared_generation_version = 0',
                 'spec.render_version = 0',
                 'alias = spec\n    alias.native_shared_generation_version = 0',
                 "setattr(spec, 'native_shared_generation_version', 0)",
                 'unknown(spec)']
    for index, mutation in enumerate(mutations):
        root = copied_route(tmp_path / str(index))
        assert scan.derive_native_shared_route(root, scan._tree(root / RUNNER))
        path = root / RUNNER
        text = path.read_text()
        marker = 'def _require_registered_input_spellings(spec: RunSpec) -> None:\n'
        assert text.count(marker) == 1
        path.write_text(text.replace(marker, marker + '    ' + mutation + '\n'))
        with pytest.raises(scan.ConfigError, match='phase input invariant body is not exact'):
            scan.derive_native_shared_route(root, scan._tree(root / RUNNER))


def test_6248_cli_mutation_refuses(tmp_path):
    mutations = [
        ('def main():', '_Replay.options = {}\n\ndef main():'),
        ('def main():', 'from . import typed\ntyped.worker_request = lambda *args: None\n\ndef main():'),
        ('proposal = _prepare_next(*selected, catalogs)', 'proposal = None'),
        ('from . import _Replay,', 'from . import OtherReplay as _Replay,'),
        ("if __name__ == '__main__':", "if False:"),
    ]
    for index, (before, after) in enumerate(mutations):
        root = _procedure_root(tmp_path / str(index))
        assert scan.derive_native_shared_procedure(root)
        path = root / 'src/data_sheets_schema/native_shared_stage/__main__.py'
        text = path.read_text()
        assert text.count(before) == 1
        path.write_text(text.replace(before, after))
        with pytest.raises(scan.ConfigError, match='native stage CLI execution is not exact'):
            scan.derive_native_shared_procedure(root)


def test_6248_preserves_shared_ast(tmp_path):
    root = _procedure_root(tmp_path)
    tree = scan._tree(root / 'src/data_sheets_schema/native_shared_stage/__main__.py')
    before = ast.dump(tree, include_attributes=True)
    assert scan.derive_native_shared_procedure(root)
    assert ast.dump(tree, include_attributes=True) == before
