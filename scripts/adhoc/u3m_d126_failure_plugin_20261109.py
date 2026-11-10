"""Failure-only D126 raw evidence, U3-M, 2026-11-09.

Input: the unchanged D126 test's failing frame and U3M_D126_FAILURE_OUT=current
run directory. Output: fresh bounded private snapshots below that run only.
No production imports, substitutions or assertion changes; a capture problem
is attached to the original failed report, never used to change its outcome.
"""
import hashlib
import json
import os
from pathlib import Path
import re

import pytest

EXEC = next(path for path in Path(__file__).resolve().parents if path.name == 'd4d-executions')
BASE = EXEC / 'scratch-native-u1u3/u3m'
TARGET = 'test_d126_in_checkout_manifest_pins_every_native_instruction_delta'
FILE = 'test_native_u4b_a5_producer_integration.py'
LIMIT = 8 * 1024 * 1024


def require(ok, message):
    if not ok:
        raise ValueError(message)


def write(path, raw):
    require(type(raw) is bytes and 0 < len(raw) <= LIMIT, 'snapshot size/type refused')
    with path.open('xb') as stream:
        stream.write(raw)
    require(path.read_bytes() == raw, 'snapshot did not persist')
    return dict(file=path.name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if (not report.failed or call.excinfo is None or getattr(item, 'originalname', None) != TARGET
            or Path(str(item.path)).name != FILE):
        return
    try:
        require(not os.path.lexists(EXEC / 'plans/native_quiet_window.lock'), 'quiet window active')
        out = Path(os.environ['U3M_D126_FAILURE_OUT'])
        require(out.is_absolute() and out.resolve(strict=True) == out and out.is_dir()
                and out != BASE and out.is_relative_to(BASE), 'physical current U3-M run required')
        # Bind to the actual run's pytest basetemp, not merely any writable
        # sibling supplied through an environment variable.
        basetemp = Path(str(item.config.getoption('basetemp')))
        cases = out / 'cases'
        require(basetemp == cases or (basetemp.parent == cases
                and re.fullmatch(r'popen-gw[0-9]+', basetemp.name)),
                'failure output differs from active test run')
        directory = out / 'd126-failures'
        directory.mkdir(exist_ok=True)
        require(directory.resolve(strict=True) == directory, 'failure directory is aliased')
        frames = [entry for entry in call.excinfo.traceback if entry.frame.code.name == TARGET
                  and Path(str(entry.path)).resolve() == Path(str(item.path)).resolve()]
        require(len(frames) <= 1, 'ambiguous D126 failure frame')
        local = frames[0].frame.f_locals if frames else {}
        stem = hashlib.sha256(item.nodeid.encode('utf-8')).hexdigest()[:24]
        result = dict(kind='native_u3m_d126_failure', version=1, nodeid=item.nodeid,
                      when=report.when, frame_found=bool(frames),
                      u4b_runtime=local.get('u4b') if type(local.get('u4b')) is bool else None,
                      exception_type=call.excinfo.type.__name__, before=None, after=None,
                      changes=None, public_ready=False, assertions_unchanged=True)
        for key in ('before', 'after'):
            if key in local:
                result[key] = write(directory / (stem + '-' + key + '-instruction.txt'), local[key])
        if type(local.get('changes')) is list:
            rows = local['changes']
            require(len(rows) <= 100 and all(type(row) is dict for row in rows), 'change roster refused')
            allowed = {'role', 'line_index1', 'before', 'after', 'before_sha256', 'after_sha256'}
            require(all(set(row) == allowed and type(row['role']) is str and type(row['line_index1']) is int
                        and all(type(row[key]) is str for key in allowed - {'line_index1'}) for row in rows),
                    'changed-line payload is not the original fixed shape')
            result['changes'] = rows
        raw = (json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
        write(directory / (stem + '.json'), raw)
        report.sections.append(('U3-M D126 raw failure evidence', str(directory / (stem + '.json'))))
    except Exception as error:
        report.sections.append(('U3-M D126 capture refused', type(error).__name__ + ': ' + str(error)))
