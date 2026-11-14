"""Issue 6233, 2026-11-14: run pure regressions with assignment-base modules.

Inputs: base git objects, current regression tests. Outputs: source snapshots
and pytest output in assigned scratch. No verified-loader/public-path claim.
"""
import importlib
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest
import data_sheets_schema


def main():
    root = Path(sys.argv[1])
    root.mkdir(parents=True, exist_ok=False)
    base = 'b35e264571a4e8ba6f152b7fc7053c35758d6823'
    modules = ('native_shared_stage', 'native_shared_capture', 'native_shared_callback_capture',
               'native_shared_callback_orchestration', 'native_shared_capture_orchestration')
    # Establish unchanged carrier/dependency classes through the assigned source
    # tree before substituting only the five modules whose code changed.
    for short in modules:
        importlib.import_module('data_sheets_schema.' + short)
    for short in modules:
        relative = 'src/data_sheets_schema/' + short + ('/__init__.py' if short == 'native_shared_stage' else '.py')
        raw = subprocess.check_output(['git', 'show', base + ':' + relative])
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        assert path.read_bytes() == raw
        name = 'data_sheets_schema.' + short
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        setattr(data_sheets_schema, short, module)
        spec.loader.exec_module(module)
    return pytest.main(['tests/test_native_shared_callback_prefix.py', '-q',
        '--basetemp=' + str(root / 'cases'), '-p', 'no:cacheprovider',
        '--junitxml=' + str(root / 'junit.xml')])


if __name__ == '__main__':
    raise SystemExit(main())
