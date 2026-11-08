#!/usr/bin/env python3
"""U3-D9 offline validation, 2026-11-07.

Inputs: committed D checkout and explicit pytest nodes. Outputs: exclusive
scratch-native-u3d run directories, source witnesses, JUnit and sandbox logs.
Retains the C4 credential/network/native-exec/write restrictions and deadline.
"""
import importlib.util
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'scripts/adhoc/run_native_u3c_round4_20261107.py'
spec = importlib.util.spec_from_file_location('d9_reviewed_runner', source)
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)
SCRATCH = wrapper.runner.EXECUTIONS / 'scratch-native-u3d'
wrapper.SCRATCH = SCRATCH
wrapper.__file__ = __file__
wrapper.runner.SCRATCH = SCRATCH
wrapper.runner.__file__ = __file__
wrapper.runner.PROFILE = wrapper.sandbox_profile()
wrapper.dependency.SCRATCH = SCRATCH
wrapper.dependency.SOURCE = wrapper.runner.EXECUTIONS.parent / 'data-sheets-schema/fairscape_models'
wrapper.dependency.DESTINATION = SCRATCH / 'dependencies' / ('fairscape-' + wrapper.dependency.PIN)

_save = wrapper.runner.save


def save(path, value):
    if path.name == 'bootstrap.json':
        # D has a preserved older local submodule tree. Keep it untouched but
        # remove it from this disposable bootstrap before C inserts the exact
        # scratch gitlink. The source-origin assertion stays unchanged.
        paths = list(value['paths'])
        local = str(ROOT / 'fairscape_models')
        if local in paths:
            pth = next(Path(item) for item in value['files'] if item.endswith('/u3a_paths.pth'))
            if pth.read_text() != ''.join(item + '\n' for item in paths):
                raise RuntimeError('unrecognized inherited bootstrap paths')
            paths.remove(local)
            pth.write_text(''.join(item + '\n' for item in paths))
            value = {**value, 'paths': paths, 'files': {**value['files'],
                str(pth): hashlib.sha256(pth.read_bytes()).hexdigest()}}
    _save(path, value)


wrapper.runner.save = save

if __name__ == '__main__':
    if sys.argv[1:] == ['--hydrate-local-dependency']:
        wrapper.dependency.main()
        raise SystemExit(0)
    wrapper.runner.time = wrapper.DeadlineClock()
    raise SystemExit(wrapper.runner.main())
