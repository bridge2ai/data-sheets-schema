"""Give synthetic native preparation the import paths of its real CLI helpers."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys


def helper_import_paths(root):
    environment = dict(os.environ)
    # The registered native runtime does not inherit the pytest PYTHONPATH.
    environment.pop('PYTHONPATH', None)
    result = subprocess.run(
        [sys.executable, '-B', '-c', 'import json, sys; print(json.dumps(sys.path))'],
        cwd=root, env=environment, check=True, capture_output=True, text=True,
        timeout=30)
    return [str(root) if path == '' else path for path in json.loads(result.stdout)]


def helper_environment(root):
    """Isolate collection pollution before preparation, restoring it afterward.

    Keep the actual path stable across preparation and execution. Do not filter
    a census or change the path during verification of an existing manifest.
    """
    original = sys.path
    sys.path = helper_import_paths(Path(root).resolve(strict=True))
    try:
        yield
    finally:
        sys.path = original


helper_environment = contextmanager(helper_environment)
