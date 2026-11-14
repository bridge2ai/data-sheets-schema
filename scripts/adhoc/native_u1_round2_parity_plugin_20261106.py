"""#4354 U1 2026-11-06: fixed per-test paths for exact M7/composed byte parity.
Inputs: pytest node ID. Outputs: scratch synthetic fixtures, no normalization.
"""
from pathlib import Path
import hashlib
import pytest

@pytest.fixture
def tmp_path(request):
    root=Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1/r2-parity-inputs')
    path=root/hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:16]
    path.mkdir(parents=True,exist_ok=True)
    return path
