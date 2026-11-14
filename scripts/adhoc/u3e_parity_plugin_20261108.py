"""U3-E 2026-11-08 fixed synthetic paths for exact API byte comparison.
Input: pytest node ID; output: assigned scratch fixtures. No normalization.
"""
from pathlib import Path
import hashlib
import pytest

@pytest.fixture
def tmp_path(request):
    executions = next(p for p in Path(__file__).resolve().parents if p.name == 'd4d-executions')
    path = executions / 'scratch-native-u1u3/parity-inputs' / hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:16]
    path.mkdir(parents=True, exist_ok=True)
    return path

