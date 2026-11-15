"""Measure advance computation and genuine durable publication from saved fixture.

Input: trusted consumed variant pickle, output directory. Outputs: profile,
timings, and actual stage files under the fixture's scratch stage root.
Variant advance assignment, 2026-11-15. Captured invocation is synthetic;
public capture_stage admission and live callback reconstruction are excluded.
"""
import cProfile
import json
from pathlib import Path
import pickle
import pstats
import sys
import time

from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import native_shared_publication_orchestration as publication
from tests.test_native_shared_publication import invocation

source, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
case, request, response = pickle.loads(source.read_bytes())
root = Path(case[0].role('stage_root'))
if root.exists():
    raise ValueError('profiling requires a fresh fixture stage directory')
root.mkdir(parents=True)
for item in (case[3].journal, *case[3].records, *case[3].artifacts):
    path = Path(item.pin.path)
    if root not in path.parents:
        raise ValueError('fixture artifact escapes scratch stage root')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(item.raw)

catalogs = stage.nr._catalog_context()
profile = cProfile.Profile()
start, cpu = time.monotonic(), time.process_time()
profile.enable()
replay = stage._Replay(*case, _catalogs=catalogs).run()
assert replay.pending[-1] is not None
proposal = stage._check_response(*case, request, response, catalogs)
assert proposal.disposition == 'checked'
result, observed = publication.publish_derived(invocation(case), proposal, _catalogs=catalogs)
profile.disable()
metrics = {'wall_seconds': time.monotonic() - start, 'cpu_seconds': time.process_time() - cpu,
           'state': result['state'], 'published_files': len(observed),
           'scope': 'Actual advance computation and durable publication; synthetic invocation, no public capture_stage.'}
profile.dump_stats(str(out / 'advance.prof'))
with (out / 'advance.txt').open('w') as stream:
    pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(60)
(out / 'metrics.json').write_text(json.dumps(metrics, indent=2))
(out / 'result.json').write_text(json.dumps(result, indent=2))
print(json.dumps(metrics), flush=True)
assert result['state'] == 'assembly_complete'
for item in observed:
    assert Path(item.captured.pin.path).read_bytes() == item.captured.raw
