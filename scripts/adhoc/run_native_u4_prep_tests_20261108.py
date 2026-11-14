#!/usr/bin/env python3
"""U4 preparation offline validation, 2026-11-08 (#4354 / D105 / D106).

Inputs: this committed checkout and explicit pytest nodes, physical dependency
venv Python with -S -P -B. Outputs: fresh scratch-native-u4-prep evidence,
source/origin witnesses, JUnit and sandbox logs. Retains the reviewed D9/C4
runner's network/native-executable/write restrictions and dual-clock deadline.
No native binary, local provider listener or subscription account is exercised.
"""
import importlib.util
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / 'scripts/adhoc/run_native_u3c_round4_20261107.py'
spec = importlib.util.spec_from_file_location('u4_reviewed_runner', source)
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)
SCRATCH = wrapper.runner.EXECUTIONS / 'scratch-native-u4-prep'
wrapper.SCRATCH = SCRATCH
wrapper.__file__ = __file__
wrapper.runner.SCRATCH = SCRATCH
wrapper.runner.__file__ = __file__
wrapper.runner.PROFILE = wrapper.sandbox_profile()
wrapper.dependency.SCRATCH = SCRATCH
wrapper.dependency.SOURCE = wrapper.runner.EXECUTIONS.parent / 'data-sheets-schema/fairscape_models'
wrapper.dependency.DESTINATION = SCRATCH / 'dependencies' / ('fairscape-' + wrapper.dependency.PIN)

_save = wrapper.runner.save
_origin_witness = wrapper.runner.origin_witness


def origin_witness():
    # Keep the exact scratch gitlink package ahead of editable-install paths.
    importlib.import_module('fairscape_models')
    return _origin_witness()


def save(path, value):
    if path.name == 'bootstrap.json':
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
wrapper.runner.origin_witness = origin_witness

if __name__ == '__main__':
    if sys.argv[1:] == ['--hydrate-local-dependency']:
        wrapper.dependency.main()
        raise SystemExit(0)
    wrapper.runner.time = wrapper.DeadlineClock()
    raise SystemExit(wrapper.runner.main())
