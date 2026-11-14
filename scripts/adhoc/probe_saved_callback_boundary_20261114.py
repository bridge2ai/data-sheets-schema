"""Issue 6233, 2026-11-14: read-only saved adapter construction probe.

Inputs: saved attempts root and output JSON. Never activates or observes:
both operations publish to registered absolute paths in the read-only evidence.
"""
import json
from pathlib import Path
import sys
import time
import traceback
from data_sheets_schema import native_shared_controller_orchestration as controller

root, output = map(Path, sys.argv[1:])
rows = []
for case in ('omissions', 'correction-alone'):
    paths = list((root / case).rglob('native-attempt/registration.json'))
    if len(paths) != 1:
        raise ValueError((case, paths))
    path = paths[0]
    raw = path.read_bytes()
    envelope = json.loads(raw)
    value = envelope['registration']
    started = time.thread_time(), time.process_time(), time.perf_counter()
    row = {'case': case, 'registration': str(path)}
    try:
        controller.CallbackAdapter(value['composition_raw_json'].encode(), execution=value, registration_raw=raw)
    except Exception as error:
        row['boundary'] = type(error).__name__ + ': ' + str(error)
        row['traceback'] = traceback.format_exc()
    else:
        row['boundary'] = 'Construction succeeded; activation and observation not invoked because they publish to saved registered paths.'
    row['clocks'] = dict(zip(('thread_cpu', 'process_cpu', 'wall'), (end - begin for end, begin in zip(
        (time.thread_time(), time.process_time(), time.perf_counter()), started))))
    rows.append(row)
    output.write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(row), flush=True)
