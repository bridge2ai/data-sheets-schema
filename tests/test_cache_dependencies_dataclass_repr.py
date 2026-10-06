"""Actual stdlib dataclass wrappers are portable; filename claims are not."""
import dataclasses
import sys
import types

import pytest
from linkml_runtime.utils.schemaview import SchemaView
from data_sheets_schema.cache_dependencies import FunctionBindings


def bind(function):
    result = FunctionBindings()
    result.bind(lambda: result.key(function))
    return result


def copied(function, *, code=None, name=None):
    value = types.FunctionType(code or function.__code__, function.__globals__,
                               name or function.__name__, function.__defaults__, function.__closure__)
    value.__module__ = function.__module__
    value.__kwdefaults__ = function.__kwdefaults__
    if hasattr(function, '__wrapped__'):
        value.__wrapped__ = function.__wrapped__
    return value


def test_actual_installed_schema_view_repr_binds():
    actual = SchemaView.__repr__
    binding = bind(actual)
    assert binding.ready
    assert binding.key(actual) == binding.key(actual)
    if sys.version_info[:2] == (3, 12):
        helper = dataclasses._recursive_repr
        assert actual.__code__.co_filename == dataclasses.__file__
        assert any(actual.__code__ is code for code in helper.__code__.co_consts)


def test_counterfeit_stdlib_filename_never_enables_binding():
    namespace = {'__name__': SchemaView.__module__}
    exec(compile('def __repr__(self):\n    return "counterfeit"\n', dataclasses.__file__, 'exec'), namespace)
    forged = namespace['__repr__']
    assert forged.__module__ == SchemaView.__module__
    assert forged.__code__.co_filename == dataclasses.__file__
    binding = bind(forged)
    assert not binding.ready and not binding._functions
    with pytest.raises(TypeError, match='unfamiliar'):
        binding.key(forged)


@pytest.mark.skipif(not hasattr(dataclasses, '_recursive_repr'), reason='this runtime uses reprlib dataclass repr')
def test_equal_but_distinct_wrapper_code_is_not_actual_nested_code():
    original = SchemaView.__repr__
    assert original.__code__.co_filename == dataclasses.__file__
    code = original.__code__.replace()
    assert code == original.__code__ and code is not original.__code__
    forged = copied(original, code=code)
    binding = bind(forged)
    assert not binding.ready and not binding._functions


@pytest.mark.skipif(not hasattr(dataclasses, '_recursive_repr'), reason='this runtime uses reprlib dataclass repr')
def test_actual_nested_code_with_wrong_effective_name_is_refused():
    forged = copied(SchemaView.__repr__, name='foreign')
    binding = bind(forged)
    assert not binding.ready and not binding._functions


@pytest.mark.parametrize('change', ['defaults', 'code', 'closure'])
def test_new_origin_exception_keeps_later_state_guards(change, monkeypatch):
    function = copied(SchemaView.__repr__)
    binding = bind(function)
    assert binding.ready
    if change == 'defaults':
        function.__defaults__ = ('changed default',)
    elif change == 'code':
        function.__code__ = function.__code__.replace(co_name='modified code')
    else:
        # The real recursive wrapper closes over the effective user function;
        # swapping that function must not become a new cacheable dependency.
        cell = next(cell for name, cell in zip(function.__code__.co_freevars, function.__closure__)
                    if name == 'user_function')
        previous = cell.cell_contents
        try:
            cell.cell_contents = lambda self: 'foreign result'
            with pytest.raises(TypeError, match='unfamiliar|modified'):
                binding.key(function)
        finally:
            cell.cell_contents = previous
        return
    with pytest.raises(TypeError, match='modified|unverified stdlib dataclass repr'):
        binding.key(function)


python312_repr = pytest.mark.skipif(not hasattr(dataclasses, '_recursive_repr'),
                                   reason='this runtime uses reprlib dataclass repr')


@python312_repr
def test_counterfeit_decorator_cannot_authorize_its_own_nested_code(monkeypatch):
    namespace = {'__name__': 'dataclasses', 'changing': {'value': 'before'}}
    exec(compile('def counterfeit_decorator():\n    def __repr__(self):\n        return changing["value"]\n    return __repr__\n', dataclasses.__file__, 'exec'), namespace)
    helper = namespace['counterfeit_decorator']
    function = helper()
    function.__module__ = SchemaView.__repr__.__module__
    monkeypatch.setattr(dataclasses, '_recursive_repr', helper)
    binding = bind(function)
    assert not binding.ready and not binding._functions
    assert function(None) == 'before'
    namespace['changing']['value'] = 'after'
    assert function(None) == 'after'
    with pytest.raises(TypeError, match='unfamiliar'):
        binding.key(function)


@python312_repr
@pytest.mark.parametrize('when', ['before', 'after'])
@pytest.mark.parametrize('name', ['get_ident', 'id'])
def test_effective_dataclass_globals_are_validated_before_and_after_bind(monkeypatch, when, name):
    import _thread
    function = copied(SchemaView.__repr__)
    if when == 'after':
        binding = bind(function)
        assert binding.ready
    if name == 'get_ident':
        monkeypatch.setattr(_thread, 'get_ident', lambda: 99)
    else:
        monkeypatch.setattr(dataclasses, 'id', lambda value: 99, raising=False)
    if when == 'before':
        binding = bind(function)
        assert not binding.ready and not binding._functions
    else:
        with pytest.raises(TypeError, match='unverified dataclass repr builtin'):
            binding.key(function)


@python312_repr
def test_actual_code_with_foreign_global_dictionary_is_refused():
    original = SchemaView.__repr__
    function = types.FunctionType(original.__code__, dict(original.__globals__), '__repr__',
                                  original.__defaults__, original.__closure__)
    function.__module__ = original.__module__
    function.__wrapped__ = original.__wrapped__
    assert not bind(function).ready


@python312_repr
def test_thread_proxy_is_refused_without_invoking_accessor(monkeypatch):
    calls = []
    class Proxy:
        @property
        def get_ident(self):
            calls.append('access')
            raise AssertionError('not a real thread module')
    monkeypatch.setattr(dataclasses, '_thread', Proxy())
    assert not bind(SchemaView.__repr__).ready
    assert calls == []


@python312_repr
def test_effective_function_builtins_are_checked_not_module_metadata(monkeypatch):
    original = SchemaView.__repr__
    namespace = dict(original.__builtins__)
    with monkeypatch.context() as patch:
        patch.setitem(original.__globals__, '__builtins__', namespace)
        function = copied(original)
    assert function.__builtins__ is namespace
    assert function.__globals__['__builtins__'] is not namespace
    binding = bind(function)
    assert binding.ready
    namespace['id'] = lambda value: 99
    with pytest.raises(TypeError, match='unverified dataclass repr builtin'):
        binding.key(function)


@python312_repr
def test_unavailable_stdlib_source_only_bypasses_cache(monkeypatch, tmp_path):
    from data_sheets_schema import cache_dependencies as dependencies
    monkeypatch.setattr(dependencies.sysconfig, 'get_path', lambda name: str(tmp_path))
    path, code = dependencies._stdlib_dataclass_repr()
    assert path is None and code is None
    monkeypatch.setattr(dependencies, '_DATACLASS_REPR_CODE', code)
    assert not bind(SchemaView.__repr__).ready
