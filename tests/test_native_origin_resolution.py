"""Fresh fixed-origin resolution; no runtime binary or provider calls."""
import ctypes
import os
from pathlib import Path

import pytest

from data_sheets_schema import native_origin_resolution as origins


@pytest.fixture
def source(tmp_path):
    path = tmp_path.resolve() / 'module.py'
    path.write_text('# fixed source\n')
    return str(path)


def test_real_kernel_resolution_matches_python_and_runs_for_every_call(source, monkeypatch):
    actual = origins._native_functions()
    if actual is None:
        # An unavailable platform still has to satisfy the original route.
        assert origins.resolve_fixed_origin(source, source) == Path(source).resolve()
        return
    library, realpath, free = actual
    calls = []
    def observed(raw, destination):
        calls.append(raw)
        return realpath(raw, destination)
    monkeypatch.setattr(origins, '_native_functions', lambda: (library, observed, free))
    for _ in range(2):
        assert origins.resolve_fixed_origin(source, source) == Path(source).resolve()
    assert calls == [os.fsencode(source)] * 2


@pytest.mark.parametrize('seam', ['resolve', 'concrete_resolve', 'realpath', 'lstat', 'readlink'])
def test_patched_python_seams_always_use_original_route(source, monkeypatch, seam):
    target = (Path if seam == 'resolve' else type(Path()) if seam == 'concrete_resolve'
              else os.path if seam == 'realpath' else os)
    attribute = 'resolve' if seam == 'concrete_resolve' else seam
    original = getattr(target, attribute)
    calls = []
    def observed(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)
    monkeypatch.setattr(target, attribute, observed)
    monkeypatch.setattr(origins, '_matches_native_spelling',
                        lambda raw: pytest.fail('patched Python seam was bypassed'))
    assert origins.resolve_fixed_origin(source, source) == Path(source)
    if seam != 'readlink':
        assert calls


def test_alias_and_noncanonical_spellings_use_python_without_native_attempt(source, tmp_path, monkeypatch):
    alias = tmp_path / 'alias.py'
    alias.symlink_to(source)
    spellings = [str(alias), str(Path(source).parent) + '/./module.py',
                 '//' + source.lstrip('/'), source + '\0', Path(source)]
    monkeypatch.setattr(origins, '_matches_native_spelling',
                        lambda raw: pytest.fail('nonexact spelling reached native fast path'))
    for spelling in spellings:
        try:
            expected = Path(spelling).resolve()
        except Exception as error:
            with pytest.raises(type(error), match=''):
                origins.resolve_fixed_origin(spelling, source)
        else:
            assert origins.resolve_fixed_origin(spelling, source) == expected


@pytest.mark.parametrize('kind', ['missing', 'loop', 'parent_retarget'])
def test_native_failure_or_changed_result_preserves_python_semantics(source, tmp_path, kind):
    if kind == 'missing':
        Path(source).unlink()
    elif kind == 'loop':
        Path(source).unlink()
        Path(source).symlink_to(source)
    else:
        parent = tmp_path.resolve() / 'container'
        parent.mkdir()
        source = str(parent / 'module.py')
        Path(source).write_text('# first\n')
        moved = tmp_path.resolve() / 'moved'
        parent.rename(moved)
        parent.symlink_to(moved)
    try:
        expected = Path(source).resolve()
    except Exception as error:
        with pytest.raises(type(error), match=''):
            origins.resolve_fixed_origin(source, source)
    else:
        assert origins.resolve_fixed_origin(source, source) == expected


def test_unavailable_native_route_preserves_python(source, monkeypatch):
    monkeypatch.setattr(origins, '_native_functions', lambda: None)
    assert origins.resolve_fixed_origin(source, source) == Path(source).resolve()


def test_actual_unsupported_platform_selects_python_fallback(source, monkeypatch):
    origins._native_functions.cache_clear()
    try:
        monkeypatch.setattr(origins.sys, 'platform', 'unsupported-origin-platform')
        assert origins._native_functions() is None
        assert origins.resolve_fixed_origin(source, source) == Path(source).resolve()
    finally:
        origins._native_functions.cache_clear()


def test_allocated_native_result_is_freed_once_even_if_comparison_raises(source, monkeypatch):
    raw = os.fsencode(source)
    buffer = ctypes.create_string_buffer(raw)
    pointer = ctypes.addressof(buffer)
    frees = []
    monkeypatch.setattr(origins, '_native_functions',
                        lambda: (object(), lambda *_: pointer, frees.append))
    assert origins._matches_native_spelling(raw) is True
    assert frees == [pointer]
    def fail(*args):
        raise RuntimeError('comparison failure')
    monkeypatch.setattr(ctypes, 'string_at', fail)
    with pytest.raises(RuntimeError, match='comparison failure'):
        origins._matches_native_spelling(raw)
    assert frees == [pointer, pointer]


def test_null_native_result_is_not_freed_and_falls_back(source, monkeypatch):
    frees = []
    monkeypatch.setattr(origins, '_native_functions',
                        lambda: (object(), lambda *_: None, frees.append))
    assert origins.resolve_fixed_origin(source, source) == Path(source)
    assert frees == []


def test_qualified_origin_still_observes_second_call_change(source, monkeypatch):
    from data_sheets_schema import native_owner_profile_v1 as profile
    from types import ModuleType
    import sys
    role = 'control'
    expected = str(profile.ROOT / profile.IMPLEMENTATIONS[role])
    module = ModuleType(profile._MODULES[role])
    module.__file__ = expected
    monkeypatch.setitem(sys.modules, module.__name__, module)
    calls = []
    def resolve(value, selected):
        calls.append((value, selected))
        return Path(value) if len(calls) == 1 else Path(value + '.changed')
    monkeypatch.setattr(profile, 'resolve_fixed_origin', resolve)
    with pytest.raises(ValueError, match='foreign qualified origin'):
        profile._origin(role, module)
    assert calls == [(expected, expected), (expected, expected)]


def test_parent_retarget_after_success_is_fresh_and_bare_guard_refuses(tmp_path, monkeypatch):
    from types import ModuleType
    from data_sheets_schema import native_owner_profile_v1 as profile
    parent = tmp_path.resolve() / 'original'
    parent.mkdir()
    source = str(parent / 'module.py')
    Path(source).write_text('# exact origin\n')
    module = ModuleType('synthetic_origin')
    module.__file__ = source
    # Use the actual existing bare-origin guard in isolation; no loader,
    # deadline or owner admission is fabricated by this resolution test.
    scope = object.__new__(profile._Scope)
    scope.controls = {module.__name__: module}
    scope._origins = ((module.__name__, source),)
    monkeypatch.setitem(profile.sys.modules, module.__name__, module)
    assert origins.resolve_fixed_origin(source, source) == Path(source)
    scope._require_bare_origins()
    moved = tmp_path.resolve() / 'moved'
    parent.rename(moved)
    parent.symlink_to(moved)
    assert origins.resolve_fixed_origin(source, source) == Path(source).resolve()
    assert origins.resolve_fixed_origin(source, source) != Path(source)
    with pytest.raises(ValueError, match='stale or foreign origin'):
        scope._require_bare_origins()
    parent.unlink()
    moved.rename(parent)
    scope._require_bare_origins()


def test_qualified_origin_keeps_second_call_error(source, monkeypatch):
    from data_sheets_schema import native_owner_profile_v1 as profile
    from types import ModuleType
    import sys
    role = 'control'
    expected = str(profile.ROOT / profile.IMPLEMENTATIONS[role])
    module = ModuleType(profile._MODULES[role])
    module.__file__ = expected
    monkeypatch.setitem(sys.modules, module.__name__, module)
    calls = []
    def resolve(value, selected):
        calls.append((value, selected))
        if len(calls) == 2:
            raise OSError('second physical observation refused')
        return Path(value)
    monkeypatch.setattr(profile, 'resolve_fixed_origin', resolve)
    with pytest.raises(OSError, match='second physical observation refused'):
        profile._origin(role, module)
    assert calls == [(expected, expected), (expected, expected)]
