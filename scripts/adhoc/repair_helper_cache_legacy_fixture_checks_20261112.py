#!/usr/bin/env python3
"""Repair two v1/v2 test assertions after issue 5966 and list scanner migration.
Inputs/outputs: U4b test and cache identity documentation. No production edits.
2026-11-12; confirmed by cache-integration JUnit (163 passed, 2 failed).
"""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=root/'tests/test_native_u4b_runtime.py';s=p.read_text()
old='    assert historical.validate_runtime(result) == result\n'
assert s.count(old)==1
s=s.replace(old,'    assert historical.validate_runtime_v2(result) == result\n')
old='''    runtime, _ = inputs
    assert historical.validate_runtime(runtime) == runtime
    assert subject.is_prepared_runtime(runtime) is False
'''
new='''    runtime, _ = inputs
    legacy = deepcopy(runtime)
    legacy['environment'].pop('PYSTOW_HOME')
    assert historical.validate_runtime(legacy) == legacy
    with pytest.raises(ValueError, match='environment'):
        historical.validate_runtime(runtime)
    assert historical.validate_runtime_v2(runtime) == runtime
    assert subject.is_prepared_runtime(runtime) is False
'''
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
p=root/'docs/native-helper-cache.md';s=p.read_text()
needle='| Runtime declaration R |'
assert needle in s
s=s.replace(needle,'| Scanner integrated-render source contract | Authority, runtime and profile source pins change; the runtime dispatcher adds native_helper_cache as a callee. Helper 1 must review the expanded finite contract before updating instrument pins; this repair does not restamp them |\n'+needle,1)
p.write_text(s)
