"""Trace manifest-pinned bare imports during full collection, H3 2026-11-12.

Inputs: isolated venv source tree. Output: scratch JSON with importer stacks.
No tests run, no source edits. Run with inherited OS network/native denial.
"""
import builtins
import json
from pathlib import Path
import sys
import traceback
import pytest
from data_sheets_schema import native_attribution_controller_v2 as controller
from data_sheets_schema import native_execution_registration_v2 as registration

ROOT = controller.ROOT
OUT = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-ci-20261112')
names = set(json.loads((ROOT / controller.SOURCES_PATH).read_bytes())['modules'])
names |= set(registration.authority.neutral.ADDITIONAL) | set(registration.authority.ADDITIONAL)
real_import = builtins.__import__
events = []
def snapshot():
    return {name: getattr(sys.modules[name], '__file__', None) for name in names if name in sys.modules}
def traced(name, globals=None, locals=None, fromlist=(), level=0):
    before = snapshot()
    try:
        return real_import(name, globals, locals, fromlist, level)
    finally:
        after = snapshot()
        if after != before:
            events.append({'requested': name, 'caller': (globals or {}).get('__file__'),
                'changed': {k: v for k, v in after.items() if before.get(k) != v},
                'test_stack': sorted({f.filename for f in traceback.extract_stack()
                                      if '/tests/test_' in f.filename})})
builtins.__import__ = traced
try:
    code = pytest.main(['--collect-only', '-q', '-o', 'addopts=', '-p', 'no:cacheprovider',
                        '--basetemp', str(OUT / 'collection-cases'), 'tests'])
finally:
    builtins.__import__ = real_import
    (OUT / 'collection-origins.json').write_text(json.dumps({'events': events, 'final': snapshot(),
        'pinned_names': sorted(names)}, indent=2) + '\n')
raise SystemExit(code)
