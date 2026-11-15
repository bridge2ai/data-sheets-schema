"""Issue 6260, 2026-11-15: inspect fast-plan coverage and time warm guards.

Input: installed worktree source. Output: JSON on stdout; no model calls.
"""
import json
import time
import sys
from data_sheets_schema import native_catalog_reuse as catalog

def probe(label):
    marker = catalog.runtime_token()
    plans = catalog._FAST_PLANS.get(marker, {})
    plan = next((plan for plan in plans.values() if catalog._guards_match(plan)),
                next(iter(plans.values()), None))
    failures = []
    if plan:
        attributes, mappings, sequences, functions, cells, rosters, missing, parameters, namespaces, model_dicts = plan
        for owner, name, expected in attributes:
            if getattr(owner, name, missing) is not expected:
                failures.append(('attribute', str(type(owner)), name))
        for current, expected in mappings:
            if current != expected:
                failures.append(('mapping', str(tuple(expected)[:8]),
                    [str(key) for key in current.keys() | expected.keys()
                     if current.get(key) is not expected.get(key)]))
        for current, expected in sequences:
            if current != expected:
                failures.append(('sequence', str(type(current))))
        for fn, code, defaults, kwdefaults, closure in functions:
            if (fn.__code__ is not code or fn.__defaults__ is not defaults
                    or fn.__kwdefaults__ is not kwdefaults or fn.__closure__ is not closure):
                failures.append(('function', fn.__qualname__))
        for cell, expected in cells:
            if cell.cell_contents is not expected:
                failures.append(('cell', str(type(expected))))
        for namespace, name, expected in namespaces:
            if namespace.get(name, missing) is not expected:
                failures.append(('namespace', name))
    started = time.perf_counter()
    for _ in range(100):
        assert catalog.runtime_token() is marker
    print(json.dumps({'phase': label, 'supported': marker is not None,
        'plan': plan is not None, 'guards': [len(part) for part in plan[:6]] if plan else [],
        'matches': catalog._guards_match(plan) if plan else False,
        'seconds_per_100': time.perf_counter() - started, 'failures': failures}))

if len(sys.argv) > 1:
    import pickle
    from pathlib import Path
    from data_sheets_schema import native_shared_stage as stage
    case, request, response = pickle.loads(Path(sys.argv[1]).read_bytes())
    stage._Replay(*case).run()
    probe('after_actual_replay')
else:
    probe('original')
    import linkml.utils.rawloader
    catalog.views.DupCheckYamlLoader('x: 1').dispose()
    probe('initialized')
