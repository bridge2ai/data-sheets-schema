"""Issue 6214, 2026-11-15: real source-loader lifetime witness; stdout JSON.

Run in a disposable process because a poisoned loader must stay open.
"""
import gc
import hashlib
import json
from pathlib import Path
import sys
import threading

from data_sheets_schema import native_execution_authority_v2 as authority
from data_sheets_schema import native_shared_callback_orchestration as preload

preload.CALLBACK_TEARDOWN_SECONDS = 0.02
lock = preload._CallbackLock()
entered, release = threading.Event(), threading.Event()
errors = []
name = 'teardown_lifetime_witness'
raw = b'def value():\n    return 7\n'
path = Path(sys.argv[1]) / 'loader_witness.py'
path.write_bytes(raw)
original = RuntimeError('original witness error')
exceptional = sys.argv[2] == 'exception'

def worker():
    try:
        with lock:
            entered.set()
            assert release.wait(2)
            assert authority.module_source_identity(module)['sha256'] == hashlib.sha256(raw).hexdigest()
            assert module.value() == 7
    except BaseException as exc:
        errors.append(repr(exc))

thread = threading.Thread(target=worker)
try:
    try:
        with preload._locked_stack(lock) as stack:
            module = stack.enter_context(authority.verified_source_module(name, path=path, raw=raw, sha256=hashlib.sha256(raw).hexdigest()))
            thread.start()
            assert entered.wait(1)
            if exceptional:
                raise original
    except (ValueError, RuntimeError) as exc:
        refusal = exc.__cause__ if exceptional else exc
        assert not exceptional or exc is original
        assert '0.02 seconds' in str(refusal)
    else:
        raise AssertionError('teardown did not refuse')
    gc.collect()
    assert sys.modules[name] is module
    assert authority.module_source_identity(module)
    try:
        with lock:
            raise AssertionError('poisoned entry accepted')
    except ValueError:
        pass
finally:
    release.set()
    thread.join(2)
assert not thread.is_alive() and not errors, errors
assert sys.modules[name] is module
assert authority.module_source_identity(module)
assert stack in sys.__dict__['_d4d_poisoned_callback_stacks']
print(json.dumps(dict(exceptional=exceptional, loader_alive_during_and_after_worker=True, no_late_close=True, worker_errors=errors)))
