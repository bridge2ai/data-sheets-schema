"""U3-M fixed offline API fixture paths, 2026-11-09.

Inputs: the explicit frozen source SHA and its fresh parity-input directory.
Output: per-node fixture files at identical paths for fixed main and candidate.
No production overlay, prompt normalisation, provider or native execution.
"""
import hashlib
import os
from pathlib import Path
import re

import pytest


@pytest.fixture
def tmp_path(request):
    executions = next(p for p in Path(__file__).resolve().parents if p.name == 'd4d-executions')
    source = os.environ['U3M_PARITY_SOURCE']
    if re.fullmatch('[0-9a-f]{40}', source) is None:
        raise ValueError('full frozen U3-M parity source SHA required')
    expected = executions / 'scratch-native-u1u3/u3m' / ('parity-inputs-' + source[:12])
    root = Path(os.environ['U3M_PARITY_INPUTS'])
    if root != expected or root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError('fresh physical U3-M parity fixture root differs')
    path = root / hashlib.sha256(request.node.nodeid.encode()).hexdigest()[:16]
    if path.resolve() != path:
        raise ValueError('parity node fixture is aliased')
    path.mkdir(exist_ok=True)
    return path
