"""Test generated candidate without altering the running baseline, 2026-11-15.

Inputs: candidate source and pytest arguments. Output: ordinary pytest evidence.
Serves the public-stale census ruling; synthetic unit tests only.
"""
import importlib.util
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
sys.path[0] = str(root)
import data_sheets_schema
name = 'data_sheets_schema.native_environment_manifest'
spec = importlib.util.spec_from_file_location(name, sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
setattr(data_sheets_schema, 'native_environment_manifest', module)
spec.loader.exec_module(module)
import pytest
raise SystemExit(pytest.main(sys.argv[2:]))
