"""Profile read-only scanner discovery for H3, 2026-11-12.

Inputs: current tree through isolated test venv. Outputs: scratch profile JSON
and pstats. Run under the H3 OS network/native denial profile. No scanner edits.
"""
import cProfile
import hashlib
import json
from pathlib import Path
import pstats
import time
from tests import test_generation_specificity_skill as test
from tests.utils.native_test_environment import origin_witness

OUT = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-h3-ci-20261112')
result = {'origins': origin_witness(test.ROOT), 'root': str(test.ROOT), 'measurements': []}
for label, function in [('cold_discovery', test._discovered), ('cached_discovery', test._discovered),
                        ('changed_launch_discovery', test._discovered_with_a_bare_launch),
                        ('api_meaning', test._meaning)]:
    profiler = cProfile.Profile()
    start = time.perf_counter()
    error = None
    try:
        value = profiler.runcall(function)
    except Exception as exc:
        error = repr(exc)
    elapsed = time.perf_counter() - start
    profiler.dump_stats(str(OUT / f'{label}.pstats'))
    stats = pstats.Stats(profiler)
    rows = [{'file': k[0], 'line': k[1], 'function': k[2], 'primitive_calls': v[0],
             'calls': v[1], 'self_seconds': v[2], 'cumulative_seconds': v[3]}
            for k, v in stats.stats.items()]
    result['measurements'].append({'label': label, 'seconds': elapsed, 'error': error,
        'top_cumulative': sorted(rows, key=lambda r: -r['cumulative_seconds'])[:35],
        'top_self': sorted(rows, key=lambda r: -r['self_seconds'])[:25],
        'scanner_functions': [r for r in rows if r['file'].endswith('/scan.py')]})
    result['parsed_cache_entries'] = len(test.scan._PARSED)
    result['scanner_sha256'] = hashlib.sha256((test.SKILL / 'scan.py').read_bytes()).hexdigest()
    (OUT / 'scanner-profile.json').write_text(json.dumps(result, indent=2) + '\n')
    print(label, elapsed, error, flush=True)
