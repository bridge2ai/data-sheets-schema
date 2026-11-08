#!/usr/bin/env python3
"""C6 offline validation roster and launcher, 2026-11-07.

Inputs: assigned C interface checkout, physical dependency Python (-S -P -B).
Outputs: a new plan or one new run under scratch-native-u3c-r4/r6-*.
Reuse the unchanged C4 runner's sandbox, origins, lock, 3600 s limit and n<=2.
The one-unit canary must be verified before invoking any larger cohort.
Historical B API/BC1 timing campaigns are not rerun or certified here.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent / 'scratch-native-u3c-r4'


def plan():
    source = ROOT / 'scripts/adhoc/plan_native_u3c_round4_20261107.py'
    spec = importlib.util.spec_from_file_location('c6_plan_base', source)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    inherited = base.plan(Path(sys.executable), 'r6-')
    selected = {name: inherited['groups'][name]
                for name in ('canary', 'c', 'a-core', 'b-focused', 'census', 'collect')}
    smoke = 'tests/test_native_u3b_reuse.py::test_native_typed_capture_and_receipt_reconstruction_smoke'
    canary = selected['canary']
    canary['nodes'] = [smoke]
    canary['command'][-1] = smoke
    schema_nodes = ['tests/' + name for name in (
        'test_historical_digest_cache.py', 'test_imported_schema_snapshot.py',
        'test_schema_digest_cache.py', 'test_schema_view.py')]
    if any(not (ROOT / node).is_file() for node in schema_nodes):
        raise RuntimeError('missing controller-round-3 schema roster member')
    selected['b-schema-remaining'] = {
        'nodes': schema_nodes, 'selected_files': len(schema_nodes),
        'deadline_seconds': 3600,
        'command': [sys.executable, '-S', '-P', '-B',
                    str(ROOT / 'scripts/adhoc/run_native_u3c_round4_20261107.py'),
                    '--out', str(SCRATCH / 'r6-b-schema-remaining'),
                    '--workers', '2', *schema_nodes]}
    # Exercise both wrapper routing and all 28 actual/pinned-overlay graphs.
    selected['census']['nodes'] = ['tests/test_native_u3c_round4_helpers.py']
    selected['census']['command'][-1] = selected['census']['nodes'][0]
    return {'groups': selected, 'run_prefix': 'r6-',
            'required_order': 'verify one canary and its persisted artifacts before suites',
            'scope': 'C full; A v2 core; B native/cache plus four R3 schema modules; '
                     '28-graph census; collection only. No full-order API timing/parity claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'run'))
    parser.add_argument('group', nargs='?')
    args = parser.parse_args()
    if not (sys.flags.no_site and sys.flags.safe_path and sys.dont_write_bytecode):
        raise RuntimeError('invoke with physical dependency Python -S -P -B')
    value = plan()
    if args.action == 'plan':
        out = SCRATCH / 'r6-plan.json'
        raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
        with out.open('xb') as stream:
            stream.write(raw)
        assert out.read_bytes() == raw
        print(out)
        return 0
    if args.group not in value['groups']:
        parser.error('choose an explicit group from the saved plan')
    saved = json.loads((SCRATCH / 'r6-plan.json').read_bytes())
    if saved != value:
        raise RuntimeError('saved roster differs from current helper/interpreter')
    return subprocess.call(value['groups'][args.group]['command'], cwd=ROOT)


if __name__ == '__main__':
    raise SystemExit(main())
