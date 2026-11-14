"""Issue 5966 offline dependency import: inputs HOME/PYSTOW_HOME, stdout census.
No validation request, provider, network operation or native execution, 2026-11-12.
"""
import json
import os
from pathlib import Path
import linkml_term_validator.validator
print(json.dumps({name: sorted(str(p.relative_to(Path(os.environ[name]))) for p in
    Path(os.environ[name]).rglob('*')) for name in ('HOME', 'PYSTOW_HOME') if name in os.environ}))
