"""C's fixed pure policy projection from A's verified-source loader lifetime.

This does not extend A's public control map or expose a historical launcher.
Only the listed pure helpers, copied constants and BudgetStop type are
projected. Imported source identity is checked before projection and use.
This is a source contract, not a sandbox for arbitrary Python introspection.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from types import FunctionType, MappingProxyType
from weakref import WeakKeyDictionary

_MEMBERS = MappingProxyType({
    'native_command_policy': frozenset(('POLICY_VERSION', 'LITERAL_ADMISSION',
        'LOOKUP_LITERAL_ADMISSION', '_literal_rule', 'runtime_literal_problem',
        '_simple_command', '_too_complex', '_PROC_ENVIRON', 'classify_program_command')),
    'native_readonly': frozenset(('PROGRAMS', 'lookup_command', 'pipeline_parts', 'lookup_guidance')),
    'native_phase_history': frozenset(('HELPER_ARGUMENTS',)),
    'native_control': frozenset(('HISTORY_CONTRACT',)),
    'budgeted_cborg': frozenset(('BudgetStop',)),
})
_LOADER_CONTROLS = WeakKeyDictionary()
# Populated only by C's trusted orchestration after A has source-loaded the
# historical helper. A carrier cannot supply its own identity checker.
_PROJECTION_ATTESTORS = WeakKeyDictionary()


class _PureProjection:
    __slots__ = ('_module', '_identity', '_values', '_active', '__weakref__')

    def __init__(self, module, identity, members):
        self._module, self._identity = module, dict(identity)
        self._active = True
        self._values = {}
        for name in members:
            value = getattr(module, name)
            self._values[name] = value if isinstance(value, (FunctionType, type)) else deepcopy(value)

    def _check(self):
        if not self._active:
            raise ValueError('native shared pure helper scope is closed')
        if (type(self._identity) is not dict
                or set(self._identity) != {'name', 'path', 'sha256'}
                or self._identity.get('name') not in _MEMBERS
                or type(self._values) is not dict
                or set(self._values) != _MEMBERS[self._identity['name']]):
            raise ValueError('native shared pure helper member roster changed')
        attestor = _PROJECTION_ATTESTORS.get(self)
        if attestor is None:
            raise ValueError('native shared pure helper was not minted by the active loader')
        if attestor(self._module) != self._identity:
            raise ValueError('native shared pure helper source identity changed')
        for name, value in self._values.items():
            current = getattr(self._module, name)
            if type(current) is not type(value) or (current is not value and current != value):
                raise ValueError('native shared pure helper member changed: ' + name)

    def __getattr__(self, name):
        if name not in self._values:
            raise AttributeError(name)
        self._check()
        value = self._values[name]
        if isinstance(value, FunctionType):
            def checked(*args, **kwargs):
                self._check()
                result = value(*args, **kwargs)
                self._check()
                return result
            return checked
        if isinstance(value, type):
            # Preserve the exact frozen BudgetStop exception identity.
            return value
        return deepcopy(value)


class _PureControls(Mapping):
    __slots__ = ('_modules', '__weakref__')
    # This is a loader-owned lifetime, not a value-equivalent caller mapping.
    __eq__ = object.__eq__
    __hash__ = object.__hash__

    def __init__(self, modules):
        self._modules = MappingProxyType(dict(modules))

    def __getitem__(self, name):
        require_controls(self)
        module = self._modules[name]
        return module

    def __iter__(self):
        return iter(self._modules)

    def __len__(self):
        return len(self._modules)


def require_controls(value):
    """A caller may pass only this fixed projection, never a module allowlist."""
    if type(value) is not _PureControls:
        raise ValueError('native shared policy requires its fixed pure-control projection')
    minted = _LOADER_CONTROLS.get(value)
    if minted is None:
        raise ValueError('native shared pure controls were not minted by the active loader')
    if type(value._modules) is not MappingProxyType or set(value._modules) != set(_MEMBERS):
        raise ValueError('native shared pure control map roster changed')
    for name, original, identity in minted:
        module = value._modules[name]
        if type(module) is not _PureProjection or module is not original:
            raise ValueError('native shared pure control projection changed: ' + name)
        if module._identity != dict(identity):
            raise ValueError('native shared pure control source pin changed: ' + name)
        module._check()
    return value


def classify_ordinary(command, python, programs, command_policy, controls):
    """Exact ordinary lookup/classifier recipe, without a launcher export.

    This mirrors the frozen run_native_canary._classify_command recipe; tests
    compare both independently using its source-compiled pinned implementation.
    """
    controls = require_controls(controls)
    grammar, readonly = controls['native_command_policy'], controls['native_readonly']
    if readonly.lookup_command(command, (command_policy or {}).get('readonly_lookups'), grammar._simple_command):
        if (isinstance(command_policy, dict)
                and command_policy.get('lookup_literal_admission') == grammar.LOOKUP_LITERAL_ADMISSION):
            problem = grammar._too_complex(command) or (
                'an argument naming a process environment, which the runtime refuses'
                if any(grammar._PROC_ENVIRON.search(word) for part in readonly.pipeline_parts(command)
                       for word in (grammar._simple_command(part)[0] or ())) else None)
            if problem:
                return 'not_prescribed', (f'a registered read-only lookup, spelled so the runtime refuses it: '
                                          f'{problem}. This refusal does not disqualify the attempt; quote each '
                                          'argument with single quotes and name literal paths, or use the Read '
                                          'tool')
        return 'prescribed', 'a registered read-only lookup of this job\'s inputs or outputs'
    return grammar.classify_program_command(command, python, programs, command_policy)
