"""Independent PR #5213 guard probes, 2026-11-02.
Synthetic SG1/explicit bindings, no providers. Same file at head and 0fa.
Outputs are scratch pytest evidence, including an explicitly labeled registry residual.
"""
import copy
from dataclasses import fields, make_dataclass, replace
import gc
import os
from pathlib import Path, PurePosixPath
import pickle
from types import SimpleNamespace
import weakref

import pytest
from data_sheets_schema import api_runner as api, shared_generation as sg
from tests.test_generation_manifest_identity import external  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_shared_generation_selection import registration_for, selected_spec
import tests.test_wave7_5213_d76_round2_binding as classification


class DerivedRunSpec(api.RunSpec):
    pass


class LyingString(str):
    shown = ''
    comparisons = 0
    def __str__(self):
        return self.shown
    def __fspath__(self):
        return str.__str__(self)
    def __eq__(self, other):
        type(self).comparisons += 1
        return True


class LyingPurePath(PurePosixPath):
    shown = ''
    comparisons = 0
    def __str__(self):
        return self.shown
    def __fspath__(self):
        return '/different-file-that-must-never-be-opened'
    def __eq__(self, other):
        type(self).comparisons += 1
        return True


def bound(external, monkeypatch):
    monkeypatch.chdir(external.bundle.parent)
    return selected_spec(external, registration_for(external))


def traps(monkeypatch):
    seen = dict(authority=[], count=[], create=[], lock=[], date=[])
    def stop(kind):
        def called(*args, **kwargs):
            seen[kind].append(True)
            raise AssertionError('later boundary: ' + kind)
        return called
    monkeypatch.setattr(sg, 'assert_current', stop('authority'))
    monkeypatch.setattr(api, '_exclusive_run', stop('lock'))
    monkeypatch.setattr(api, '_restore_resume_date', stop('date'))
    fake = SimpleNamespace(messages=SimpleNamespace(count_tokens=stop('count'), create=stop('create')))
    return fake, seen


def refuses(spec, monkeypatch, resume):
    fake, seen = traps(monkeypatch)
    error = None
    try:
        api.execute(spec, client=fake, resume=resume)
    except BaseException as exc:
        error = exc
    assert not any(seen.values()), (seen, repr(error))
    assert isinstance(error, ValueError), repr(error)
    assert 'construction' in str(error) or 'registered input' in str(error), str(error)


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('kind', ['object-setattr', 'shallow', 'deep', 'pickle', 'subclass'])
def test_ordinary_object_and_copy_mutations_refuse(external, monkeypatch, resume, kind):
    spec = bound(external, monkeypatch)
    if kind == 'subclass':
        spec = DerivedRunSpec(**{field.name: getattr(spec, field.name) for field in fields(spec) if field.init})
    elif kind == 'shallow':
        spec = copy.copy(spec)
    elif kind == 'deep':
        spec = copy.deepcopy(spec)
    elif kind == 'pickle':
        spec = pickle.loads(pickle.dumps(spec))
    object.__setattr__(spec, 'bundle', Path(spec.bundle.name))
    object.__setattr__(spec, '_registered_input_spellings', ())
    refuses(spec, monkeypatch, resume)


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('kind', [LyingString, LyingPurePath])
def test_path_subclasses_cannot_lie_to_the_boundary(external, monkeypatch, resume, kind):
    spec = bound(external, monkeypatch)
    kind.shown = os.fspath(spec.bundle)
    kind.comparisons = 0
    spec.bundle = kind('/different-file-that-must-never-be-opened')
    refuses(spec, monkeypatch, resume)
    assert kind.comparisons == 0


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('operation', ['clear', 'replace'])
def test_missing_registry_does_not_establish_origin(external, monkeypatch, resume, operation):
    spec = bound(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    spec._registered_input_spellings = ()
    registry = getattr(api, '_REGISTERED_INPUT_BINDINGS', None)
    saved = dict(registry) if registry is not None else None
    try:
        if registry is not None:
            if operation == 'clear':
                registry.clear()
            else:
                monkeypatch.setattr(api, '_REGISTERED_INPUT_BINDINGS', {})
        refuses(spec, monkeypatch, resume)
    finally:
        if registry is not None and operation == 'clear':
            registry.update(saved)


@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('operation', ['replace-entry', 'mutate-record'])
def test_registry_forgery_is_the_documented_hostile_python_residual(external, monkeypatch, resume, operation):
    spec = bound(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    current = tuple((name, None if getattr(spec, name) is None else os.fspath(getattr(spec, name)))
                    for name in ('bundle', 'manifest', 'chunk_manifest'))
    spec._registered_input_spellings = current
    registry = getattr(api, '_REGISTERED_INPUT_BINDINGS', None)
    if registry is not None:
        old = api._input_binding(spec)
        if operation == 'replace-entry':
            forged = api._RegisteredInputBinding(current, old.selectors, current)
            monkeypatch.setitem(registry, id(spec), (weakref.ref(spec), forged))
        else:
            object.__setattr__(old, 'spellings', current)
            object.__setattr__(old, 'registration_inputs', current)
    fake, seen = traps(monkeypatch)
    with pytest.raises(AssertionError, match='later boundary: authority'):
        api.execute(spec, client=fake, resume=resume)
    assert seen['authority'] == [True] and not seen['count'] and not seen['create']
    print('DOCUMENTED_RESIDUAL: rewriting module registry permits authority access; no client call attempted')


@pytest.mark.parametrize('resume', [False, True])
def test_collected_identity_cannot_authorize_a_forged_spec(external, monkeypatch, resume):
    spec = bound(external, monkeypatch)
    retained = dict(vars(spec))
    old_id, reference = id(spec), weakref.ref(spec)
    del spec
    gc.collect()
    assert reference() is None
    registry = getattr(api, '_REGISTERED_INPUT_BINDINGS', None)
    if registry is not None:
        assert old_id not in registry
    reused = False
    allocated = []
    for attempt in range(20000):
        forged = object.__new__(api.RunSpec)
        allocated.append(forged)
        if id(forged) == old_id:
            reused = True
            break
    forged.__dict__.update(retained)
    print('ACTUAL_ID_REUSE', reused, 'allocation_attempts', attempt + 1)
    refuses(forged, monkeypatch, resume)


@pytest.mark.parametrize('name', ['input_authority', 'future_source_pin'])
def test_full_field_roster_rejects_new_unclassified_fields(monkeypatch, name):
    future = make_dataclass('FutureRunSpec', [(name, object, None)], bases=(api.RunSpec,))
    monkeypatch.setattr(api, 'RunSpec', future)
    with pytest.raises(AssertionError):
        classification.test_all_runspec_registration_and_version_axes_have_a_binding_classification()


def test_replace_with_different_shared_locator_revalidates(external, monkeypatch):
    spec = bound(external, monkeypatch)
    alias = spec.bundle.with_name('replacement-alias-' + spec.bundle.name)
    alias.symlink_to(spec.bundle)
    with pytest.raises(ValueError):
        replace(spec, bundle=alias)


def test_public_phase_builder_refuses_before_shared_authority(external, monkeypatch):
    spec = bound(external, monkeypatch)
    spec.bundle = Path(spec.bundle.name)
    fake, seen = traps(monkeypatch)
    error = None
    try:
        api.build_phase(spec, 'full', carry={})
    except BaseException as exc:
        error = exc
    assert not any(seen.values()), (seen, repr(error))
    assert isinstance(error, ValueError) and 'registered input' in str(error), repr(error)


def test_public_phase_builder_does_not_mix_changed_bundle_with_cached_instruction(external, monkeypatch):
    spec = replace(external, registered_input_paths=True)
    frozen = spec.instruction
    original = spec.bundle
    changed = original.with_name('changed-bound-input.txt')
    marker = 'DIFFERENT_BOUND_INPUT_SENTINEL'
    changed.write_text(marker + '\n')
    spec.bundle = changed
    error, request = None, None
    try:
        request = api.build_phase(spec, 'full', carry={})
    except BaseException as exc:
        error = exc
    if request is not None:
        wire = repr(request)
        print('MIXED_REQUEST_RETURNED', marker in wire,
              'instruction_still_original', spec.instruction == frozen,
              'original_path_in_instruction', str(original) in frozen)
    assert request is None, 'public build_phase returned a request after a bound bundle changed'
    assert isinstance(error, ValueError) and 'registered input' in str(error), repr(error)
