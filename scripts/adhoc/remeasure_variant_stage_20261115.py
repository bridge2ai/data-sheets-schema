"""Remeasure trusted local captured-stage pickle without profiler overhead.

Inputs: profiler output directory. Outputs: unprofiled timing and cache diagnosis.
Variant advance assignment, 2026-11-15. Never consumes an external pickle.
"""
import json
from pathlib import Path
import pickle
import sys
import time

from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import native_catalog_reuse as reuse

root = Path(sys.argv[1])
case, request, response = pickle.loads((root / 'consumed-integration.pickle').read_bytes())
diagnosis = {'bindings_ready': reuse._FUNCTIONS.ready, 'token_available': reuse.runtime_token() is not None}
try:
    actual = reuse._state()
    diagnosis['changed_state_indices'] = [i for i, (a, b) in enumerate(zip(actual, reuse._STATE)) if a != b]
    diagnosis['changed_initialized_indices'] = [i for i, (a, b) in enumerate(zip(actual, reuse._INITIALIZED_STATE)) if a != b]
except Exception as exc:
    diagnosis['exception'] = type(exc).__name__ + ': ' + str(exc)
start, cpu = time.monotonic(), time.process_time()
result = stage.check_response(*case, request, response)
value = {'wall_seconds': time.monotonic() - start, 'cpu_seconds': time.process_time() - cpu,
         'disposition': result.disposition, 'cache_diagnosis': diagnosis}
diagnosis['token_available_after'] = reuse.runtime_token() is not None
try:
    actual = reuse._state()
    diagnosis['changed_state_indices_after'] = [i for i, (a, b) in enumerate(zip(actual, reuse._STATE)) if a != b]
    diagnosis['changed_initialized_indices_after'] = [i for i, (a, b) in enumerate(zip(actual, reuse._INITIALIZED_STATE)) if a != b]
except Exception as exc:
    diagnosis['exception_after'] = type(exc).__name__ + ': ' + str(exc)
(root / 'unprofiled.json').write_text(json.dumps(value, indent=2))
print(json.dumps(value), flush=True)
assert result.disposition == 'checked'
