"""Measure saved variant response/publication; write timings and profiles.

Inputs: trusted local fixture pickle, fresh output directory, mode, profiling.
Serves the lead's parse-cache assignment, 2026-11-15. Offline only.
Existing scratch stage output is preserved by rename and restored afterward.
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

source, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
mode, profiling = sys.argv[3], sys.argv[4] == 'profile'
if mode not in ('response', 'publication') or sys.argv[4] not in ('plain', 'profile'):
    raise ValueError('expected response/publication and plain/profile')
case, request, response = pickle.loads(source.read_bytes())
root = Path(case[0].role('stage_root'))
scratch = Path.cwd().parent / 'scratch-variant-advance-20261115'
assert scratch in root.parents and scratch in out.parents
out.mkdir(parents=True, exist_ok=False)
backup = out / 'previous-stage'
profile = cProfile.Profile()
try:
    if mode == 'publication':
        if root.exists():
            root.rename(backup)
        root.mkdir(parents=True)
        for item in (case[3].journal, *case[3].records, *case[3].artifacts):
            path = Path(item.pin.path)
            assert root in path.parents
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(item.raw)
    start, cpu = time.monotonic(), time.process_time()
    if profiling:
        profile.enable()
    if mode == 'response':
        result = stage.check_response(*case, request, response)
        assert result.disposition == 'checked'
        state, count = result.disposition, 0
    else:
        catalogs = stage.nr._catalog_context()
        replay = stage._Replay(*case, _catalogs=catalogs).run()
        assert replay.pending[-1] is not None
        proposal = stage._check_response(*case, request, response, catalogs)
        assert proposal.disposition == 'checked'
        result, observed = publication.publish_derived(invocation(case), proposal, _catalogs=catalogs)
        state, count = result['state'], len(observed)
        assert state == 'assembly_complete'
        for item in observed:
            assert Path(item.captured.pin.path).read_bytes() == item.captured.raw
    profile.disable()
    metrics = dict(wall_seconds=time.monotonic()-start, cpu_seconds=time.process_time()-cpu,
                   mode=mode, profiled=profiling, state=state, published_files=count)
    from data_sheets_schema import typed_audit
    cache = getattr(typed_audit, '_JSON_PARSE_CACHE', None)
    if cache is not None:
        metrics['parse_cache'] = dict(hits=cache.hits, entries=len(cache._entries), retained_bytes=cache._bytes)
    (out / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    if profiling:
        profile.dump_stats(str(out / 'costs.prof'))
        with (out / 'costs.txt').open('w') as stream:
            pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(60)
    print(json.dumps(metrics), flush=True)
finally:
    if mode == 'publication':
        if root.exists():
            root.rename(out / 'published-stage')
        if backup.exists():
            backup.rename(root)
