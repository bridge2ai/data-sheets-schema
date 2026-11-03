"""PR #5213 closed RunSpec boundary inventory and real input-read witnesses.

2026-11-02. Inputs: all package Python sources, synthetic source copies and real
constructed specs. Outputs: explicit unresolved source contracts/test failures.
New public candidates have no implicit exemption; no generation module executes
while discovering the inventory.
"""
from dataclasses import replace
import importlib
import inspect
from pathlib import Path
import re

import pytest

from data_sheets_schema import api_runner as api
from data_sheets_schema import native_attribution_registration as native
from data_sheets_schema import shared_generation as shared
from tests.test_generation_manifest_identity import external, snapshot  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.utils.run_spec_boundaries import contract, discover, missing_contracts

ROOT = Path(__file__).resolve().parents[1]
DISCOVERED = discover(ROOT)
GUARDED = tuple(candidate for candidate in DISCOVERED if contract(candidate, ROOT) == ('guarded', None))


def test_every_public_runspec_boundary_has_an_explicit_contract():
    missing = missing_contracts(ROOT)
    assert not missing, '\n'.join(missing)


def _callable(candidate):
    value = importlib.import_module(candidate.module)
    for name in candidate.qualname.split('.'):
        value = inspect.getattr_static(value, name)
    if isinstance(value, property):
        return value.fget
    if hasattr(value, 'func') and candidate.member_kind == 'cached_property':
        return value.func
    if isinstance(value, (staticmethod, classmethod)):
        return value.__func__
    return value


def _assert_first_boundary(function, external, monkeypatch):
    spec = replace(external, registered_input_paths=True)
    spec.bundle = spec.bundle.with_name('unbound-inventory-input.txt')
    signature = inspect.signature(function)
    args, kwargs = [], {}
    opaque = object()
    supplied = False
    for parameter in signature.parameters.values():
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        annotation = parameter.annotation
        annotated_spec = (annotation is api.RunSpec or
                          isinstance(annotation, str) and bool(re.search(r'\bRunSpec\b', annotation)))
        if parameter.name == 'specs':
            value = (spec,)
            supplied = True
        elif parameter.name in {'spec', 'self'} or annotated_spec:
            value = spec
            supplied = True
        elif parameter.default is not parameter.empty:
            continue
        else:
            value = opaque
        if parameter.kind is parameter.POSITIONAL_ONLY:
            args.append(value)
        else:
            kwargs[parameter.name] = value
    assert supplied, 'guarded boundary needs a runtime RunSpec argument witness'
    before = snapshot(external.bundle.parent)
    reached = []

    def later(*args, **kwargs):
        reached.append('input/model/authority')
        raise AssertionError('input or authority preceded the RunSpec entry invariant')

    error = None
    with monkeypatch.context() as patched:
        for name in ('read_bytes', 'read_text', 'open'):
            patched.setattr(Path, name, later)
        patched.setattr(api, 'prompt_body', later)
        patched.setattr(api, '_model_settings', later)
        patched.setattr(api, 'provider_identity', later)
        patched.setattr(api, '_exclusive_run', later)
        patched.setattr(shared, 'assert_current', later)
        patched.setattr(native, '_inputs', later)
        try:
            function(*args, **kwargs)
        except BaseException as exc:
            error = exc
    assert not reached, (reached, repr(error))
    assert snapshot(external.bundle.parent) == before
    assert isinstance(error, ValueError) and 'registered input' in str(error), repr(error)


@pytest.mark.parametrize('candidate', GUARDED, ids=[candidate.identity for candidate in GUARDED])
def test_declared_entry_guard_precedes_input_model_and_authority(candidate, external, monkeypatch):
    _assert_first_boundary(_callable(candidate), external, monkeypatch)


def _source(tmp_path, text, name='api_runner.py'):
    root = tmp_path / 'copy'
    source = root / 'src' / 'data_sheets_schema'
    source.mkdir(parents=True, exist_ok=True)
    (source / name).write_text(text)
    return root


def test_inventory_discovers_members_annotations_factories_and_untyped_signatures(tmp_path):
    root = _source(tmp_path, '''
class RunSpec:
    @property
    def selected(self):
        return None
    def public_method(self):
        return None

def annotated(value: "RunSpec"):
    return value

def untyped(spec):
    return None

def _factory():
    return RunSpec()

def factory_caller():
    return _factory()
''')
    names = {candidate.qualname for candidate in discover(root)}
    assert names == {'RunSpec.selected', 'RunSpec.public_method', 'annotated', 'untyped', 'factory_caller'}
    assert len(missing_contracts(root)) == 5


def test_inventory_follows_runspec_subclass_and_alias_factories(tmp_path):
    root = _source(tmp_path, '''
class RunSpec:
    @classmethod
    def from_render_spec(cls, recorded):
        return cls()

class SelectedRunSpec(RunSpec):
    pass

Alias = SelectedRunSpec

def unchanged_base_factory():
    return RunSpec()

def subclass_factory():
    return SelectedRunSpec()

def aliased_factory():
    return Alias()

def inherited_restore(recorded):
    return Alias.from_render_spec(recorded)

def aliased_annotation(value: Alias):
    return value
''')
    names = {candidate.qualname for candidate in discover(root)}
    assert 'unchanged_base_factory' in names, 'ordinary constructor discovery must calibrate'
    assert {'subclass_factory', 'aliased_factory', 'inherited_restore', 'aliased_annotation'} <= names


def test_function_local_import_cannot_hide_a_public_runspec_annotation(tmp_path):
    root = _source(tmp_path, '''
from .api_runner import RunSpec as Selected

def public_consumer(value: Selected):
    return value

def unrelated_function():
    from unrelated_package import AnotherType as Selected
    return Selected
''', name='consumer.py')
    names = {candidate.qualname for candidate in discover(root)}
    assert 'public_consumer' in names


def test_match_arm_declarations_remain_public_inventory_candidates(tmp_path):
    root = _source(tmp_path, '''
match True:
    case True:
        def conditional_public(spec):
            return spec

class RunSpec:
    match True:
        case True:
            @property
            def conditional_member(self):
                return None
''')
    names = {candidate.qualname for candidate in discover(root)}
    assert {'conditional_public', 'RunSpec.conditional_member'} <= names


def test_conditional_definition_cannot_erase_another_arms_runspec_contract(tmp_path):
    root = _source(tmp_path, '''
class RunSpec:
    pass

enabled = True
if enabled:
    def public_consumer(value: RunSpec):
        return value
else:
    def public_consumer(value):
        return value
''')
    candidates = [candidate for candidate in discover(root) if candidate.qualname == 'public_consumer']
    assert candidates, 'a later same-qualified definition must not erase the RunSpec arm'
    assert any('RunSpec-parameter-annotation' in candidate.reasons for candidate in candidates)
    assert missing_contracts(root)


def test_module_qualified_subclass_annotation_is_a_runspec_boundary(tmp_path):
    root = _source(tmp_path, '''
class RunSpec:
    pass

class Derived(RunSpec):
    pass
''', name='model.py')
    (root / 'src/data_sheets_schema/consumer.py').write_text('''
from . import model as selected_model

def public_consumer(value: selected_model.Derived):
    return value
''')
    candidates = discover(root)
    assert any(candidate.identity == 'data_sheets_schema.consumer.public_consumer'
               and 'RunSpec-parameter-annotation' in candidate.reasons for candidate in candidates)


@pytest.mark.parametrize('annotation', [
    'selected_model.Derived',
    'list[selected_model.Derived]',
    'list["selected_model.Derived"]',
    'Optional["selected_model.Derived"]',
    '"list[selected_model.Derived]"',
], ids=['direct', 'list-direct', 'list-quoted', 'optional-quoted', 'whole-quoted'])
def test_qualified_subclass_forward_references_remain_visible(tmp_path, annotation):
    root = _source(tmp_path, '''
class RunSpec:
    pass

class Derived(RunSpec):
    pass
''', name='model.py')
    (root / 'src/data_sheets_schema/consumer.py').write_text(
        'from typing import Optional\n'
        'from . import model as selected_model\n\n'
        f'def public_consumer(value: {annotation}):\n'
        '    return value\n')
    candidates = discover(root)
    assert any(candidate.identity == 'data_sheets_schema.consumer.public_consumer'
               and 'RunSpec-parameter-annotation' in candidate.reasons for candidate in candidates)


def test_new_public_callable_in_a_scratch_copy_has_no_implicit_exemption(tmp_path, monkeypatch):
    root = _source(tmp_path, '''
class RunSpec:
    pass

def original(spec):
    """RunSpec boundary: validated-caller

    RunSpec precondition: caller has validated its RunSpec before delegation.
    """
    return None
''')
    monkeypatch.setitem(globals(), 'ROOT', root)
    test_every_public_runspec_boundary_has_an_explicit_contract()
    (tmp_path / 'closed-inventory-before.txt').write_text('Actual closed-inventory assertion passed before insertion.\n')
    assert missing_contracts(root) == ()
    path = root / 'src/data_sheets_schema/new_public_module.py'
    path.write_text('from .api_runner import RunSpec\n\ndef newly_added(value: RunSpec):\n    return value.bundle.read_bytes()\n')
    missing = missing_contracts(root)
    assert len(missing) == 1
    assert 'new_public_module.newly_added' in missing[0]
    with pytest.raises(AssertionError, match=r'new_public_module\.newly_added') as failure:
        test_every_public_runspec_boundary_has_an_explicit_contract()
    (tmp_path / 'closed-inventory-after.txt').write_text(str(failure.getrepr()) + '\n')


def test_explicit_other_type_classification_does_not_hide_a_runspec_annotation(tmp_path):
    root = _source(tmp_path, '''
def parse(spec: dict[str, str]):
    """RunSpec boundary: unrelated

    RunSpec precondition: this argument is parsed JSON data, never a RunSpec.
    """
    return spec
''')
    assert missing_contracts(root) == ()
    path = root / 'src/data_sheets_schema/api_runner.py'
    path.write_text(path.read_text().replace('dict[str, str]', 'RunSpec'))
    assert len(missing_contracts(root)) == 1


def test_a_guard_declaration_cannot_replace_the_runtime_refusal(external, monkeypatch):
    def missing_guard(spec):
        """RunSpec boundary: guarded"""
        return None
    with pytest.raises(AssertionError):
        _assert_first_boundary(missing_guard, external, monkeypatch)
    _assert_first_boundary(api._require_registered_input_spellings, external, monkeypatch)


def test_protected_contracts_bind_function_and_shared_source_bytes():
    selected = next(row for row in DISCOVERED
                    if row.identity == 'data_sheets_schema.shared_generation.capture')
    assert contract(selected, ROOT) == ('validated-caller', None)
    assert contract(replace(selected, function_sha256='0' * 64), ROOT)[1] == (
        'protected function bytes, including docstring, changed')
    assert contract(replace(selected, source_sha256='0' * 64), ROOT)[1] == (
        'protected shared-generation source bytes changed')


def test_latch_contract_pins_the_function_not_unrelated_module_docstrings():
    selected = next(row for row in DISCOVERED
                    if row.identity == 'data_sheets_schema.latch_journal.refuse_legacy_execution')
    assert contract(selected, ROOT) == ('validated-caller', None)
    assert contract(replace(selected, source_sha256='0' * 64), ROOT) == ('validated-caller', None)
    assert contract(replace(selected, function_sha256='0' * 64), ROOT)[1] == (
        'protected function bytes, including docstring, changed')


def test_new_public_protected_function_has_no_sidecar_exemption(tmp_path):
    import shutil

    root = _source(tmp_path, 'def new_public(spec):\n    return spec\n', name='shared_generation.py')
    destination = root / 'tests/utils'
    destination.mkdir(parents=True)
    shutil.copyfile(ROOT / 'tests/utils/run_spec_boundary_contracts.json',
                    destination / 'run_spec_boundary_contracts.json')
    missing = missing_contracts(root)
    assert len(missing) == 1
    assert 'data_sheets_schema.shared_generation.new_public' in missing[0]
