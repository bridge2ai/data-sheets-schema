#!/usr/bin/env python3
"""Bounded component CPU comparison for native import facts, 2026-11-11.

Inputs: reviewed source/test pins, tiny saved graph and current registration graph.
Outputs: tmp/import-facts-small-cpu-20261111 with command, inputs, completed row evidence,
summary and owned deadline. No provider, profiler or whole-launch timing claim.
The original cold branch is selected only by disabling this optional retention.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'tmp/import-facts-small-cpu-20261111'
NAME = 'data_sheets_schema.native_shared_registration'
PINS = {
    'src/data_sheets_schema/native_execution_authority_v2.py':
        'b2189db86428b5977bfcbaa72adc5f504f3449c31b583359555b074916a95558',
    'tests/test_native_import_facts.py':
        'cb565125f92baa095cf0f8489381d7fe82888fd7e8280768f7085e49b772ac9e',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_pins():
    observed = {name: sha((ROOT / name).read_bytes()) for name in PINS}
    if observed != PINS:
        raise ValueError('source/test snapshot changed')
    return observed


def child():
    from tests.utils.subprocess_deadline import save
    from data_sheets_schema import native_execution_authority_v2 as authority
    verify_pins()
    if not authority._current_import_facts():
        raise ValueError('normal interpreter does not support optional retention')
    original_root, original_ready = authority.ROOT, authority._IMPORT_FACT_FUNCTIONS.ready
    tiny = OUTPUT / 'tiny'
    package = tiny / 'src/data_sheets_schema'
    package.mkdir(parents=True)
    tiny_sources = {
        'src/data_sheets_schema/native_shared_registration.py': b'from . import synthetic_dependency\n',
        'src/data_sheets_schema/synthetic_dependency.py': b'def value():\n    return 1\n',
    }
    for name, raw in tiny_sources.items():
        (tiny / name).write_bytes(raw)
    current_sources = {}
    for path in sorted((ROOT / 'src/data_sheets_schema').rglob('*.py')):
        raw = path.read_bytes()
        if len(raw) > 8_000_000:
            raise ValueError('diagnostic source exceeds 8 MB bound')
        current_sources[str(path.relative_to(ROOT))] = raw
    if sum(map(len, current_sources.values())) > 64_000_000:
        raise ValueError('diagnostic source roster exceeds 64 MB bound')
    cases = [
        {'name': 'tiny', 'root': tiny, 'sources': tiny_sources},
        {'name': 'current_registration', 'root': ROOT, 'sources': current_sources},
    ]
    for case in cases:
        case['pins'] = {name: sha(raw) for name, raw in case['sources'].items()}
        case['raw'] = case['sources']['src/data_sheets_schema/native_shared_registration.py']
        save(OUTPUT / (case['name'] + '-inputs.json'), {
            'root': str(case['root']), 'entry_name': NAME, 'entry_bytes': len(case['raw']),
            'sources': {name: {'sha256': case['pins'][name], 'bytes': len(raw)}
                        for name, raw in case['sources'].items()},
        })
    rows, graphs = [], {}

    def clear():
        with authority._IMPORT_FACT_LOCK:
            authority._IMPORT_FACTS.clear()
            authority._IMPORT_FACT_TOTALS = (0, 0, 0)

    with (OUTPUT / 'completed.jsonl').open('x') as stream:
        def measure(case, pair, arm):
            authority.ROOT = case['root']
            authority._IMPORT_FACT_FUNCTIONS.ready = arm != 'cold_reference'
            if arm == 'normal_first':
                clear()
            before = ({key: value[0] for key, value in authority._IMPORT_FACTS.items()}
                      if arm == 'normal_repeat' else None)
            started = time.process_time_ns()
            graph = authority.refuse_legacy_consumer_imports(case['raw'], name=NAME,
                                                          package_sources=case['pins'])
            cpu = time.process_time_ns() - started
            if case['name'] in graphs and graph != graphs[case['name']]:
                raise ValueError('completed graph differs between arms')
            graphs[case['name']] = graph
            eligible = set()
            for name in graph:
                relative = 'src/' + name.replace('.', '/') + '.py'
                if relative not in case['sources']:
                    relative = relative[:-3] + '/__init__.py'
                raw = case['sources'][relative]
                if len(raw) >= 4096:
                    eligible.add((raw, str(case['root'] / relative),
                                  name in authority.CONSUMER_OWNED_MODULES))
            if case['name'] == 'current_registration' and not eligible:
                raise ValueError('representative graph has no eligible source')
            if case['name'] == 'tiny' and eligible:
                raise ValueError('tiny graph unexpectedly eligible for retention')
            if arm != 'cold_reference' and set(authority._IMPORT_FACTS) != eligible:
                raise ValueError('cache coverage differs from eligible sources')
            if arm == 'normal_repeat':
                if set(before) != eligible:
                    raise ValueError('normal repeated arm was not fully primed')
                if any(authority._IMPORT_FACTS[key][0] is not facts
                       for key, facts in before.items()):
                    raise ValueError('retained tuples were replaced instead of reused')
            row = {'case': case['name'], 'pair': pair, 'arm': arm, 'process_cpu_ns': cpu,
                   'graph': graph, 'cache_entries': len(authority._IMPORT_FACTS), 'eligible_sources': len(eligible),
                   'graph_bytes': sum(len(case['sources'][
                       'src/' + name.replace('.', '/') + '.py'])
                       if 'src/' + name.replace('.', '/') + '.py' in case['sources']
                       else len(case['sources']['src/' + name.replace('.', '/') + '/__init__.py'])
                       for name in graph)}
            rows.append(row)
            stream.write(json.dumps(row, sort_keys=True) + '\n')
            stream.flush()

        try:
            # One completed cold/fill/hit comparison for EACH input before repeats.
            for case in cases:
                for arm in ('cold_reference', 'normal_first', 'normal_repeat'):
                    measure(case, 0, arm)
            for pair in (1, 2):
                for case in cases:
                    arms = (('normal_first', 'normal_repeat', 'cold_reference') if pair == 1
                            else ('cold_reference', 'normal_first', 'normal_repeat'))
                    for arm in arms:
                        measure(case, pair, arm)
            verify_pins()
            totals = {}
            for case in cases:
                sums = {arm: sum(row['process_cpu_ns'] for row in rows
                                if row['case'] == case['name'] and row['arm'] == arm)
                        for arm in ('cold_reference', 'normal_first', 'normal_repeat')}
                totals[case['name']] = {**sums,
                    'normal_over_cold_ratio': sums['normal_repeat'] / sums['cold_reference'],
                    'pairs': 3, 'eligible_sources': next(
                        row['eligible_sources'] for row in rows if row['case'] == case['name'])}
            save(OUTPUT / 'comparison.json', {'completed': True, 'totals': totals,
                'scope': 'same public graph checker, original cold branch versus normal path (small cold, eligible retained); '
                         'process CPU only; no previous-head, whole-launch, freshness or quiet-host claim',
                'interpreter': {'executable': sys.executable, 'version': sys.version}})
            print(json.dumps(totals, sort_keys=True))
        finally:
            authority.ROOT = original_root
            authority._IMPORT_FACT_FUNCTIONS.ready = original_ready
            clear()


def main():
    if not sys.dont_write_bytecode:
        raise ValueError('run with -B')
    sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
    if sys.argv[1:] == ['--child']:
        return child()
    if sys.argv[1:]:
        raise ValueError('unexpected arguments')
    from tests.utils.subprocess_deadline import run, save
    observed = verify_pins()
    OUTPUT.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--child']
    excluded = {'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN',
                'ANTHROPIC_BASE_URL', 'OPENAI_BASE_URL', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS'}
    env = {name: value for name, value in os.environ.items()
           if name not in excluded and not name.endswith('_API_KEY')}
    overrides = {'PYTHONDONTWRITEBYTECODE': '1',
                 'PYTHONPATH': str(ROOT / 'src') + os.pathsep + str(ROOT)}
    env.update(overrides)
    save(OUTPUT / 'command.json', {'command': command, 'cwd': str(ROOT),
         'source_sha256': observed, 'environment_overrides': overrides, 'deadline_seconds': 30,
         'helper_sha256': sha(Path(__file__).read_bytes())})
    with (OUTPUT / 'run.log').open('x') as stream:
        result = run(command, cwd=ROOT, env=env, evidence=OUTPUT / 'deadline', stream=stream, seconds=30)
    save(OUTPUT / 'outcome.json', {'returncode': result.returncode, 'expired': result.expired})
    print(json.dumps({'returncode': result.returncode, 'expired': result.expired, 'evidence': str(OUTPUT)}))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
