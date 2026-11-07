"""U3-B render parity fixture paths, 2026-11-07.

Input: pytest node id. Output: identical absolute synthetic fixture namespace
for separately run M8 and U3-B processes; no instruction normalization.
"""
from pathlib import Path
import hashlib
import importlib
import json
import os
import pytest


@pytest.fixture(scope='session', autouse=True)
def verify_source_origin(request):
    root = Path(request.config.rootpath).resolve()
    rows = []
    for name in ('api_runner', 'shared_generation', 'audit_omissions', 'typed_audit', 'schema_snapshot'):
        module = importlib.import_module('data_sheets_schema.' + name)
        path = Path(module.__file__).resolve()
        assert path == root / 'src/data_sheets_schema' / (name + '.py')
        rows.append({'module': name, 'path': str(path),
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    output = Path(os.environ['U1_PARITY_OUTPUT'])
    output.mkdir(exist_ok=True)
    worker = os.environ.get('PYTEST_XDIST_WORKER', 'controller')
    (output / ('source-origin-' + worker + '.json')).write_text(json.dumps(rows, indent=2) + '\n')

@pytest.fixture
def tmp_path(request):
    root = Path(__file__).resolve().parents[3] / 'scratch-native-u3b/parity-inputs'
    path = root / hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:16]
    path.mkdir(parents=True, exist_ok=True)
    return path
