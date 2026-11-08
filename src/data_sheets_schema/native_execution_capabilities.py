"""Reviewed host-side capabilities for native v2 execution and saved replay.

A's public loader map stays unchanged.  This orchestration context projects
only the historical members used below from A's source-attested modules.
C's genuine projection is scoped to each pure consumer call.  Consumers
receive the four accounting/observation members, never a launcher module.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
from inspect import isfunction
import sys
from types import MappingProxyType

from . import native_execution_authority_v2 as authority
from . import native_shared_controls_orchestration as classifier_loading


_MEMBERS = MappingProxyType({
    'run_direct_canary': frozenset(('NoProxy', 'model_accounting', 'LIMIT_KEYS', 'observed_efforts')),
    'run_native_canary': frozenset(('execute_child', 'BudgetStop', 'observation_problems',
                                  '_too_complex', '_PROC_ENVIRON')),
    'native_readonly': frozenset(('PROGRAMS', 'pipeline_parts', '_literal_arguments', '_paths')),
    'native_command_policy': frozenset(('_simple_command',)),
    'native_control': frozenset(('INIT_ID', 'BLANK_FRAME_TYPE', 'TOOLS', 'control_contract',
        'initialize_frame', 'digest', 'hook_output', 'input_validation_rejection')),
    'budgeted_cborg': frozenset(('BudgetStop',)),
    'run_direct_canary_awake': frozenset(('KeepAwake',)),
})
class _Members:
    """Exact member projection; no module or unlisted attribute is exported."""
    __slots__ = ('_module', '_identity', '_values', '_active')

    def __init__(self, module, identity, names):
        self._module, self._identity, self._active = module, dict(identity), True
        self._values = {}
        for name in names:
            try:
                value = getattr(module, name)
            except AttributeError as error:
                raise ValueError('native execution capability is missing: ' + identity['name'] + '.' + name) from error
            self._values[name] = value if isfunction(value) or isinstance(value, type) else deepcopy(value)
        self._check()

    def _check(self):
        if not self._active:
            raise ValueError('native execution capability scope is closed')
        if (authority.module_source_identity(self._module) != self._identity
                or set(self._values) != _MEMBERS.get(self._identity['name'])):
            raise ValueError('native execution capability source or roster changed')
        for name, value in self._values.items():
            current = getattr(self._module, name, None)
            if type(current) is not type(value) or (current is not value and current != value):
                raise ValueError('native execution capability changed: ' + name)

    def __getattr__(self, name):
        if name not in self._values:
            raise AttributeError(name)
        self._check()
        value = self._values[name]
        if isfunction(value):
            def checked(*args, **kwargs):
                self._check()
                result = value(*args, **kwargs)
                self._check()
                return result
            return checked
        return value if isinstance(value, type) else deepcopy(value)


class _Capabilities(Mapping):
    """Orchestration-only historical projections, with bounded pure-call scopes."""
    __slots__ = ('_members', '_dependencies', '_active')

    def __init__(self, members, dependencies):
        self._members = MappingProxyType(dict(members))
        self._dependencies = deepcopy(dependencies)
        self._active = True

    def require_complete(self):
        if not self._active or set(self._members) != set(_MEMBERS):
            raise ValueError('native execution capabilities are missing or expired')
        for name, member in self._members.items():
            if type(member) is not _Members or member._identity['name'] != name:
                raise ValueError('native execution capability projection changed')
            member._check()
        return self

    def __getitem__(self, name):
        self.require_complete()
        return self._members[name]

    def __iter__(self):
        return iter(self._members)

    def __len__(self):
        return len(self._members)

    @contextmanager
    def loaded_classifier(self):
        """Do not hold A's consumer package finder across live orchestration."""
        self.require_complete()
        with classifier_loading.loaded_controls(self._dependencies) as projection:
            yield projection
        self.require_complete()

    @property
    def package_sources(self):
        self.require_complete()
        return dict(self._dependencies['base']['package_sources'])

    @property
    def gate_members(self):
        self.require_complete()
        direct, native = self['run_direct_canary'], self['run_native_canary']
        return {'model_accounting': direct.model_accounting,
                'LIMIT_KEYS': tuple(direct.LIMIT_KEYS),
                'observed_efforts': direct.observed_efforts,
                'observation_problems': native.observation_problems}


@contextmanager
def loaded_capabilities(dependencies):
    """Check every required capability before yielding to any reservation.

    The historical modules are read only while A's source loader is open.
    Their source identities are attested by A; a similarly named ordinary import
    cannot supply a capability. Nothing is inserted in A's public control map.
    """
    members = {}
    capabilities = None
    with authority.loaded_dependencies(dependencies):
        try:
            pins = {**dependencies['base']['modules'], **dependencies['additional_modules']}
            for name, names in _MEMBERS.items():
                pin = pins.get(name)
                if pin is None:
                    raise ValueError('native execution capability pin is missing: ' + name)
                module = sys.modules.get(name)
                expected = {'name': name, 'path': str(authority.ROOT / pin['path']),
                            'sha256': pin['sha256']}
                if authority.module_source_identity(module) != expected:
                    raise ValueError('native execution capability differs from its source pin: ' + name)
                members[name] = _Members(module, expected, names)
            capabilities = _Capabilities(members, dependencies)
            capabilities.require_complete()
            yield capabilities
            capabilities.require_complete()
        finally:
            if capabilities is not None:
                capabilities._active = False
            for member in members.values():
                member._active = False
