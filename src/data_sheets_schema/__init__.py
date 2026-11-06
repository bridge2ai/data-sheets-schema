"""Diagnostic-only ordinary package: U0-R7 source closure, 2026-11-06."""
from pathlib import Path as _u0_closure_Path
import hashlib as _u0_closure_hashlib
import runpy as _u0_closure_runpy
_u0_closure_root = _u0_closure_Path(__file__).resolve().parents[2]
_u0_closure_helper = _u0_closure_root / 'scripts/adhoc/native_u0_source_closure_20261106.py'
if _u0_closure_hashlib.sha256(_u0_closure_helper.read_bytes()).hexdigest() != 'd9e95e2e8c4d178e4f6bd3093a65695a4568a2bcc230d4cd24b21262ca4e396e':
    raise RuntimeError('U0 source-closure helper hash differs')
_u0_closure_runpy.run_path(str(_u0_closure_helper))['install_source_closure'](_u0_closure_root)
