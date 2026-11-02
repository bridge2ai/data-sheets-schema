"""PR #5213 / D76 T8 R1–R7: adversarial source-certificate review controls.

Inputs: the source-only T8 fixtures and current scanner. Outputs: pytest results
and owned temporary source fixtures. 2026-11-02. No production helper execution.
Each mutation first calibrates its unchanged fixture; a calibration failure is
not evidence that the mutation was rejected. Original 52-case assertions remain
intact; the added real-source fixture dependency is versioned separately.
"""
import textwrap

import pytest

from tests import test_wave7_5213_d76_specificity_prefix as base


def _calibrate(fixture, tmp_path):
    expected = base._expected(tmp_path / 'expected')
    assert base._derive(fixture)[0] == expected, 'unchanged fixture must calibrate first'


def _replace_once(path, before, after):
    source = path.read_text()
    assert source.count(before) == 1, 'mutation must hit exactly one source site'
    path.write_text(source.replace(before, after))


def _refuses(fixture):
    with pytest.raises(base.scan.ConfigError, match='not derived'):
        base._derive(fixture)


def _simple(tmp_path, definitions='def validate(spec):\n    return None\n'):
    return base._fixture(tmp_path / 'source', definitions)


def _real(tmp_path):
    return base._real_fixture(tmp_path / 'source')


def test_r1_second_iteration_must_not_mutate_a_borrowed_list(tmp_path):
    fixture = _simple(tmp_path)
    path = fixture[0] / base.scan.RUNNER
    _replace_once(path, '    inputs: dict\n', '    inputs: list\n')
    _calibrate(fixture, tmp_path)
    _replace_once(path, 'def validate(spec):\n    return None',
        "def validate(spec):\n    values = []\n    for name in ('first', 'second'):\n"
        "        values.append('changed')\n        values = spec.inputs")
    _refuses(fixture)


@pytest.mark.parametrize('parameter', ['*, validate=foreign', '*validate', '**validate'])
def test_r2_every_resolver_parameter_kind_can_shadow_the_callee(tmp_path, parameter):
    fixture = _simple(tmp_path, "def foreign(spec):\n    spec.base_prompt = 'changed'\n"
                      "def validate(spec):\n    return None\n")
    _calibrate(fixture, tmp_path)
    _replace_once(fixture[0] / base.scan.RUNNER, 'def resolve_prompt(spec: RunSpec):',
                  'def resolve_prompt(spec: RunSpec, ' + parameter + '):')
    _refuses(fixture)


@pytest.mark.parametrize('mutation', [
    'validate.__code__ = mutate.__code__',
    'alias = validate\nalias.__code__ = mutate.__code__',
    'def consume(callback):\n    callback.__code__ = mutate.__code__\nconsume(validate)',
])
def test_r3_visible_callable_mutation_or_escape_invalidates_its_ast(tmp_path, mutation):
    fixture = _simple(tmp_path, "def mutate(spec):\n    spec.base_prompt = 'changed'\n"
                      "def validate(spec):\n    return None\n")
    _calibrate(fixture, tmp_path)
    path = fixture[0] / base.scan.RUNNER
    path.write_text(path.read_text() + '\n' + mutation + '\n')
    _refuses(fixture)


def test_r3_module_alias_cannot_replace_the_certified_fspath_member(tmp_path):
    fixture = _real(tmp_path)
    _calibrate(fixture, tmp_path)
    path = fixture[0] / base.scan.RUNNER
    path.write_text(path.read_text() + "\n"
        "def altered_fspath(value):\n    return 'changed'\n"
        "module_alias = os\nmodule_alias.fspath = altered_fspath\n")
    _refuses(fixture)


def test_r3_imported_member_alias_cannot_replace_the_predicate_code(tmp_path):
    fixture = _real(tmp_path)
    _calibrate(fixture, tmp_path)
    path = fixture[0] / base.scan.RUNNER
    path.write_text(path.read_text() + "\n"
        "def mutate_selection(selection):\n"
        "    selection['condition'] = 'changed'\n    return True\n"
        "predicate_alias = provenance.registered_input_paths\n"
        "predicate_alias.__code__ = mutate_selection.__code__\n")
    _refuses(fixture)


_DESCRIPTOR = '''
class PromptDescriptor:
    def __get__(self, instance, owner=None):
        if instance is None:
            raise AttributeError('required field, not a dataclass default')
        instance.condition = 'changed'
        return instance.__dict__['base_prompt']
    def __set__(self, instance, value):
        instance.__dict__['base_prompt'] = value
'''


def _install_descriptor_definition(path):
    _replace_once(path, '@dataclass\nclass RunSpec:',
                  textwrap.dedent(_DESCRIPTOR) + '\n@dataclass\nclass RunSpec:')


def _reading_fixture(tmp_path):
    return _simple(tmp_path, "def validate(spec):\n"
                   "    if spec.base_prompt is None:\n        raise ValueError('missing')\n")


def test_r3_class_alias_cannot_install_a_field_descriptor(tmp_path):
    fixture = _reading_fixture(tmp_path)
    _calibrate(fixture, tmp_path)
    path = fixture[0] / base.scan.RUNNER
    _install_descriptor_definition(path)
    path.write_text(path.read_text() + '\nSpecAlias = RunSpec\n'
                    'SpecAlias.base_prompt = PromptDescriptor()\n')
    _refuses(fixture)


@pytest.mark.parametrize('mutation', ['conditional_roster', 'import_roster',
                                     'conditional_path_type', 'path_type_member'])
def test_r4_literal_and_standard_path_bindings_have_no_hidden_writers(tmp_path, mutation):
    fixture = _real(tmp_path)
    _calibrate(fixture, tmp_path)
    path = fixture[0] / base.scan.RUNNER
    if mutation == 'conditional_roster':
        addition = "if True:\n    _INPUT_BINDING_SELECTORS = ('base_prompt',)\n"
    elif mutation == 'import_roster':
        # A real adjacent module supplies a valid tuple; no nonexistent import
        # or malformed syntax is used to obtain the required scanner refusal.
        (path.parent / 'prefix_poison.py').write_text("fields = ('base_prompt',)\n")
        addition = 'from .prefix_poison import fields as _INPUT_BINDING_SELECTORS\n'
    elif mutation == 'conditional_path_type':
        addition = ("class AlternatePath(type(Path())):\n"
                    "    def __fspath__(self):\n        return 'changed'\n"
                    "if True:\n    _PLATFORM_PATH_TYPE = AlternatePath\n")
    else:
        addition = ("def altered_path_spelling(self):\n    return 'changed'\n"
                    "_PLATFORM_PATH_TYPE.__fspath__ = altered_path_spelling\n")
    path.write_text(path.read_text() + '\n' + addition)
    _refuses(fixture)


@pytest.mark.parametrize('placement', ['field_default', 'later_class_assignment', 'class_expression'])
def test_r5_declared_field_annotations_do_not_authorize_descriptor_behavior(tmp_path, placement):
    fixture = _reading_fixture(tmp_path)
    _calibrate(fixture, tmp_path)
    path = fixture[0] / base.scan.RUNNER
    _install_descriptor_definition(path)
    if placement == 'field_default':
        # __get__(None, cls) raises AttributeError, so this is a required
        # descriptor field and does not violate dataclass default ordering.
        _replace_once(path, '    base_prompt: str | None\n',
                      '    base_prompt: str | None = PromptDescriptor()\n')
    elif placement == 'later_class_assignment':
        _replace_once(path, '    guide_version: int\n',
                      '    guide_version: int\n    base_prompt = PromptDescriptor()\n')
    else:
        _replace_once(path, '    guide_version: int\n',
                      "    guide_version: int\n"
                      "    locals().__setitem__('base_prompt', PromptDescriptor())\n")
    _refuses(fixture)


def test_r5_imported_field_default_must_resolve_to_its_source_value(tmp_path):
    fixture = _reading_fixture(tmp_path)
    _calibrate(fixture, tmp_path)
    path = fixture[0] / base.scan.RUNNER
    (path.parent / 'prefix_descriptor.py').write_text(
        textwrap.dedent(_DESCRIPTOR) + '\nDEFAULT_PROMPT = PromptDescriptor()\n')
    _replace_once(path, '@dataclass\nclass RunSpec:',
        'from data_sheets_schema.prefix_descriptor import DEFAULT_PROMPT\n'
        '@dataclass\nclass RunSpec:')
    _replace_once(path, '    base_prompt: str | None\n',
        '    base_prompt: str | None = DEFAULT_PROMPT\n')
    _refuses(fixture)


def test_r5_vars_cannot_read_a_custom_dict_descriptor(tmp_path):
    fixture = _real(tmp_path)
    _calibrate(fixture, tmp_path)
    _replace_once(fixture[0] / base.scan.RUNNER, 'class RunSpec:\n',
        "class RunSpec:\n    @property\n    def __dict__(self):\n"
        "        self.condition = 'changed'\n        return {}\n")
    _refuses(fixture)


def test_r5_frozen_record_class_expression_cannot_add_dispatch(tmp_path):
    fixture = _real(tmp_path)
    _calibrate(fixture, tmp_path)
    _replace_once(fixture[0] / base.scan.RUNNER, 'class _RegisteredInputBinding:\n',
        "class _RegisteredInputBinding:\n"
        "    locals().__setitem__('__getattribute__', lambda self, name: "
        "(globals().__setitem__('D76_PREFIX_SIDE_EFFECT', True), "
        "object.__getattribute__(self, name))[1])\n")
    _refuses(fixture)


def test_r6_registry_lookup_result_cannot_escape_to_an_unproved_writer(tmp_path):
    fixture = _real(tmp_path)
    _calibrate(fixture, tmp_path)
    path = fixture[0] / base.scan.RUNNER
    path.write_text(path.read_text() + "\ndef mutate_retained_record(spec):\n"
        "    binding = _input_binding(spec)\n"
        "    if binding is not None:\n"
        "        object.__setattr__(binding, 'selectors', (('base_prompt', str, ''),))\n")
    _refuses(fixture)


def test_r7_nested_parameter_and_captured_outer_binding_are_not_alpha_equivalent(tmp_path):
    fixture = _real(tmp_path)
    _calibrate(fixture, tmp_path)
    _replace_once(fixture[0] / base.scan.RUNNER, 'saved[0] is reference:',
                  'saved[0] is spec:')
    _refuses(fixture)
