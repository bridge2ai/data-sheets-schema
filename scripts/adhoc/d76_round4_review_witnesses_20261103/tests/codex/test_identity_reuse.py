"""PR #5213 allocator identity-reuse probe, 2026-11-02.
Allocate the retaining pool before collecting a registered spec, so the pool
itself cannot occupy the released object's slot. Same scratch test at both heads.
"""
from dataclasses import replace
import gc
import weakref
import pytest
from data_sheets_schema import api_runner as api
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from test_new_guard import refuses


@pytest.mark.parametrize('resume', [False, True])
def test_actual_allocator_reuse_cannot_supply_construction_origin(external, monkeypatch, resume):
    pool = [None] * 20000
    spec = replace(external, registered_input_paths=True)
    retained = dict(vars(spec))
    old_id, reference = id(spec), weakref.ref(spec)
    cls = type(spec)
    del spec
    gc.collect()
    assert reference() is None
    reused = False
    for number in range(len(pool)):
        forged = object.__new__(cls)
        pool[number] = forged
        if id(forged) == old_id:
            reused = True
            break
    forged.__dict__.update(retained)
    print('ALLOCATOR_REUSE_OBSERVED', reused, 'attempts', number + 1)
    refuses(forged, monkeypatch, resume)
