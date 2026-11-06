#!/usr/bin/env python3
"""Run reviewed U0 tooling tests offline, #4354/D92, 2026-11-06.

Inputs: this tooling checkout, existing venv and optional exact canary node.
Outputs: new external pytest log/XML/bootstrap and outcome; no native trial.
Invoke beneath sandbox-exec deny network*. No production helper is launched.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--canary', action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    lock = root.parent / 'plans/native_quiet_window.lock'
    if lock.exists():
        raise SystemExit('measurement lock exists; tooling tests must pause')
    out = args.out.absolute()
    if not out.is_relative_to(root.parent) or out.is_relative_to(root):
        raise SystemExit('new output must be external under d4d-executions')
    out.mkdir(mode=0o700, exist_ok=False)
    home, temporary = out / 'home', out / 'tmp'
    home.mkdir(); temporary.mkdir()
    spec = importlib.util.spec_from_file_location('u0_wrapper', root / 'scripts/adhoc/native_u0_run_20261106.py')
    wrapper = importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
    os.environ.clear(); os.environ.update(wrapper.clean_environment(home, temporary))
    spec = importlib.util.spec_from_file_location('u0_measure', root / 'scripts/adhoc/native_recorder_measure_20261026.py')
    measure = importlib.util.module_from_spec(spec); spec.loader.exec_module(measure)
    bootstrap = measure.initialize_dependencies()
    sys.path[:0] = [str(root / 'src'), str(root / 'scripts'), str(root)]
    (out / 'bootstrap.json').write_text(json.dumps(bootstrap, indent=2) + '\n')
    os.chdir(root)
    import pytest
    nodes = (['tests/test_native_u0_run_20261106.py::test_exclusive_lock_records_owner_and_does_not_replace']
        if args.canary else ['tests/test_native_recorder_measure_helper.py',
            'tests/test_native_recorder_observer_20261026.py', 'tests/test_native_u0_run_20261106.py'])
    command = ['-q', '-p', 'no:cacheprovider', '--basetemp', str(out / 'cases'),
               '--junitxml', str(out / 'pytest.xml'), *nodes]
    (out / 'command.json').write_text(json.dumps({'arguments': command, 'python': sys.executable,
        'network_policy': 'inherited sandbox-exec deny network*', 'node_scope': 'tooling only'}, indent=2) + '\n')
    started = time.monotonic()
    code = pytest.main(command)
    (out / 'outcome.json').write_text(json.dumps({'returncode': int(code),
        'wall_seconds': time.monotonic() - started, 'kind': 'tooling_tests_not_recorder_trials'}, indent=2) + '\n')
    return int(code)


if __name__ == '__main__':
    raise SystemExit(main())
