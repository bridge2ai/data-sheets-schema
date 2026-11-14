"""Profile the exact failed CI scanner/test tree for H3, 2026-11-12.

Input: immutable archive of CI commit 1a137b588604. Outputs: scratch pstats and
JSON. Executes scanner read-only derivation only, inside OS network denial.
"""
import cProfile
import hashlib
import importlib.util
import json
from pathlib import Path
import pstats
import sys
import time

ROOT = Path('/Users/marcin/agent-work/data-sheets-schema/ci-sim-1a137b588604')
OUT = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-ci-20261112')
spec = importlib.util.spec_from_file_location('h3_original_scanner_test', ROOT / 'tests/test_generation_specificity_skill.py')
test = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = test
spec.loader.exec_module(test)
result = {'root': str(ROOT), 'python': sys.version, 'scanner_sha256': hashlib.sha256((test.SKILL / 'scan.py').read_bytes()).hexdigest(), 'measurements': []}
for label in ('cold', 'repeat'):
    profiler = cProfile.Profile()
    started = time.perf_counter()
    error = None
    try:
        profiler.runcall(test._discovered)
    except Exception as exc:
        error = repr(exc)
    elapsed = time.perf_counter() - started
    profiler.dump_stats(str(OUT / f'original-ci-{label}.pstats'))
    stats = pstats.Stats(profiler)
    rows = [{'file': k[0], 'line': k[1], 'function': k[2], 'calls': v[1],
             'self_seconds': v[2], 'cumulative_seconds': v[3]} for k, v in stats.stats.items()]
    result['measurements'].append({'label': label, 'seconds': elapsed, 'error': error,
        'cache_info': str(test._discovered.cache_info()),
        'top_cumulative': sorted(rows, key=lambda r: -r['cumulative_seconds'])[:40],
        'scanner_functions': [r for r in rows if r['file'].endswith('/scan.py')]})
    result['parsed_cache_entries'] = len(test.scan._PARSED)
    (OUT / 'original-ci-scanner-profile.json').write_text(json.dumps(result, indent=2) + '\n')
    print(label, elapsed, error, test._discovered.cache_info(), flush=True)
