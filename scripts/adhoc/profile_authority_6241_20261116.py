"""Profile one fixture registration verification for issue 6241, 2026-11-16.

Input: pytest plugin and AUTHORITY_PROFILE_OUTPUT destination.
Output: JSON call counts/times and cProfile file beside it. No native calls.
"""
import cProfile
import json
import os
from pathlib import Path
import pstats
import sys
import time


def pytest_configure(config):
    from data_sheets_schema import native_execution_registration_v2 as registration
    if os.environ.get('AUTHORITY_PROFILE_BASELINE') == '1':
        authority = registration.authority

        def original_scan():
            return (key for key, loaded in list(sys.modules.items())
                    if key.startswith('data_sheets_schema.') or
                    key != 'data_sheets_schema' and
                    authority._package_name(getattr(loaded, '__file__', None)))

        authority._ambient_package_bindings = original_scan
    original = registration.verified
    completed = False

    def measured(*args, **kwargs):
        nonlocal completed
        if completed:
            return original(*args, **kwargs)
        completed = True
        profiler = cProfile.Profile()
        started = time.perf_counter()
        outcome = 'returned'
        try:
            return profiler.runcall(original, *args, **kwargs)
        except BaseException:
            outcome = 'raised'
            raise
        finally:
            elapsed = time.perf_counter() - started
            destination = Path(os.environ['AUTHORITY_PROFILE_OUTPUT'])
            profiler.dump_stats(str(destination.with_suffix('.prof')))
            stats = pstats.Stats(profiler)
            rows = []
            for (filename, line, name), (primitive, calls, own, cumulative, callers) in stats.stats.items():
                if name in {'resolve', 'lstat', 'stat', 'head', 'require_committed',
                            '_package_name', '_verified_source_bytes', 'check_output'}:
                    rows.append(dict(file=filename, line=line, name=name, calls=calls,
                                     own_seconds=own, cumulative_seconds=cumulative))
            destination.write_text(json.dumps(dict(elapsed_seconds=elapsed,
                outcome=outcome, calls=rows), indent=2) + '\n')

    registration.verified = measured
