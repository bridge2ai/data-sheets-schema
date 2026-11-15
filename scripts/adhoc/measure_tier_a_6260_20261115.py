"""Measure late-stage components for issue 6260, 2026-11-15.

Input: trusted variant fixture pickle, fresh scratch output, mode, profile flag.
Output: timings, profile, and verified publication files. No admission/model
launch. Final-decision mode is only a component, not a full observer callback.
Preserves and restores the original fixture stage directory by rename.
"""
import cProfile
import hashlib
import json
from pathlib import Path
import pickle
import pstats
import sys
import time

from data_sheets_schema import native_shared_stage as stage
from data_sheets_schema import native_shared_publication_orchestration as publication
from data_sheets_schema import typed_audit
from tests.test_native_shared_publication import invocation
from tests.test_native_shared_stages import append

source, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
source_paths = [Path(typed_audit.__file__).parent / name for name in (
    'native_catalog_reuse.py', 'native_shared_capture.py',
    'native_shared_callback_capture.py', 'native_shared_observations.py', 'typed_audit.py')]
source_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
mode, profiling = sys.argv[3], sys.argv[4]
if mode not in ('publication', 'final') or profiling not in ('plain', 'profile'):
    raise ValueError('expected publication/final and plain/profile')
scratch = Path.cwd().parent / 'scratch-tier-a-6260-20261115'
fixture_scratch = Path.cwd().parent / 'scratch-variant-advance-20261115'
assert scratch in out.parents and fixture_scratch in source.parents
case, request, response = pickle.loads(source.read_bytes())
root = Path(case[0].role('stage_root'))
assert fixture_scratch in root.parents
out.mkdir(parents=True, exist_ok=False)
backup = out / 'previous-stage'
profile = cProfile.Profile()
catalogs = stage.nr._catalog_context()
if mode == 'final':
    proposal = stage._check_response(*case, request, response, catalogs)
    assert proposal.disposition == 'checked'
    case = (*case[:3], append(case[3], proposal.records_to_append,
                             proposal.predicted_journal,
                             tuple(pub.artifact for pub in proposal.publications)))
    # Preparation warmed pure parses in this process, like earlier callbacks.
    # It does not supply a completed-stage decision to either measured call.
cache = typed_audit._JSON_PARSE_CACHE
hits_before = cache.hits
packet_cache = getattr(typed_audit, '_OPEN_PACKET_CACHE', None)
packet_hits_before = packet_cache.hits if packet_cache is not None else 0
rows = []
materialized = False
try:
    if mode == 'publication':
        if root.exists():
            root.rename(backup)
        root.mkdir(parents=True)
        materialized = True
        for item in (case[3].journal, *case[3].records, *case[3].artifacts):
            path = Path(item.pin.path)
            assert root in path.parents
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(item.raw)
    wall, cpu = time.monotonic(), time.process_time()
    if profiling == 'profile':
        profile.enable()
    if mode == 'publication':
        replay = stage._Replay(*case, _catalogs=catalogs).run()
        assert replay.pending[-1] is not None
        proposal = stage._check_response(*case, request, response, catalogs)
        assert proposal.disposition == 'checked'
        result, observed = publication.publish_derived(invocation(case), proposal, _catalogs=catalogs)
        state = result['state']
        for item in observed:
            assert Path(item.captured.pin.path).read_bytes() == item.captured.raw
        count = len(observed)
        assert count == 6
    else:
        count = 0
        for ordinal in range(2):
            start, process = time.monotonic(), time.process_time()
            decision = stage._prepare_next(*case, catalogs)
            assert decision.state == 'assembly_complete'
            rows.append({'ordinal': ordinal + 1, 'wall_seconds': time.monotonic() - start,
                         'cpu_seconds': time.process_time() - process})
        state = decision.state
    profile.disable()
    metrics = {'wall_seconds': time.monotonic() - wall, 'cpu_seconds': time.process_time() - cpu,
               'mode': mode, 'profiled': profiling == 'profile', 'state': state,
               'history_records': len(case[3].records), 'published_files': count,
               'decision_calls': rows, 'parse_cache_hits': cache.hits - hits_before,
               'parse_cache_entries': len(cache._entries), 'parse_cache_bytes': cache._bytes,
               'scope': 'Stage component only; excludes public capture and observer admission.'}
    if packet_cache is not None:
        metrics['packet_cache_hits'] = packet_cache.hits - packet_hits_before
        metrics['packet_cache_entries'] = len(packet_cache._entries)
        metrics['packet_cache_bytes'] = packet_cache._bytes
    assert state == 'assembly_complete'
    assert source_hashes == {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
    metrics['source_sha256'] = source_hashes
    (out / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    if profiling == 'profile':
        profile.dump_stats(str(out / 'costs.prof'))
        with (out / 'costs.txt').open('w') as stream:
            pstats.Stats(profile, stream=stream).sort_stats('cumulative').print_stats(60)
    print(json.dumps(metrics), flush=True)
finally:
    if mode == 'publication':
        if materialized and root.exists():
            root.rename(out / 'published-stage')
        if backup.exists():
            backup.rename(root)
