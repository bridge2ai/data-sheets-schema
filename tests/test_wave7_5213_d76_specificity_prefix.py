"""D76 T8: prove observational preconditions before the selected adapter.

Source-only scanner fixtures: no production validator, provider, registration or
model prompt is executed. Preserve these cases for before/after runs (2026-11-02).
"""
import textwrap

import pytest

from tests import test_generation_specificity_skill as fixture_module

ROOT, scan = fixture_module.ROOT, fixture_module.scan


def _fixture(tmp_path, definitions, prefix="validate(spec)"):
    root, body, selection = fixture_module.TestSelectedTemplateDerivation().fixture(tmp_path)
    path = root / scan.RUNNER
    runner = path.read_text()
    runner = runner.replace("    body = prompt_body(spec.base_prompt)",
                            textwrap.indent(textwrap.dedent(prefix).strip(), "    ")
                            + "\n    body = prompt_body(spec.base_prompt)")
    runner = runner.replace('def resolve_prompt(spec):', 'def resolve_prompt(spec: RunSpec):')
    structure = ('from dataclasses import dataclass\n'
                 '@dataclass\nclass RunSpec:\n'
                 '    base_prompt: str | None\n    condition: str\n'
                 '    inputs: dict\n    bundle: str\n    events: object\n    guide_version: int\n')
    path.write_text(structure + '\n' + textwrap.dedent(definitions) + "\n" + runner)
    return root, body, selection


def _derive(fixture):
    root, body, selection = fixture
    return scan._selected_template(root, scan._tree(root / scan.RUNNER), selection, body)


def _expected(tmp_path):
    # The existing no-prefix proof supplies the expected adaptation; do not
    # import or execute the validator being proved by the new checker.
    return _derive(fixture_module.TestSelectedTemplateDerivation().fixture(tmp_path))[0]


@pytest.mark.parametrize("definitions,prefix", [
    ("def validate(spec):\n    if spec.base_prompt is None:\n        raise ValueError('missing')\n",
     "validate(spec)"),
    ("def check_shape(value):\n    return value is not None\n"
     "def differently_named(spec):\n    if not check_shape(spec.base_prompt):\n"
     "        raise ValueError('missing')\n",
     "differently_named(spec)"),
    ("def validate(spec):\n    names = []\n"
     "    for name in ('bundle', 'manifest'):\n        names.append(name)\n"
     "    if len(names) != 2:\n        raise ValueError('shape')\n",
     "validate(spec)"),
    ("def validate(spec):\n    if spec.base_prompt is None:\n        raise ValueError('missing')\n",
     "validate(spec)\nvalidate(spec)"),
])
def test_observational_prefix_keeps_exact_adapter(tmp_path, definitions, prefix):
    expected = _expected(tmp_path / 'unchanged')
    result, evidence = _derive(_fixture(tmp_path / 'prefix', definitions, prefix))
    assert result == expected
    assert evidence['field'] == 'guide_version'


def _real_fixture(tmp_path):
    fixture = fixture_module.TestSelectedTemplateDerivation().fixture(tmp_path)
    root, body, selection = fixture
    for relative in (scan.RUNNER, 'src/data_sheets_schema/provenance.py',
                     'src/data_sheets_schema/registry.py'):
        (root / relative).write_text((ROOT / relative).read_text())
    selection['cases'][0]['values'] = {'api_playbook_version': 2}
    return root, body, selection


@pytest.mark.parametrize('rename', [False, True])
def test_real_registry_precondition_is_source_proven_without_name_exception(tmp_path, rename):
    fixture = _real_fixture(tmp_path / 'real')
    if rename:
        path = fixture[0] / scan.RUNNER
        source = path.read_text()
        for old, new in (('_require_registered_input_spellings', 'assert_frozen_locators'),
                         ('_input_binding', '_lookup_original_state'),
                         ('_REGISTERED_INPUT_BINDINGS', '_ORIGINAL_STATES')):
            source = source.replace(old, new)
        path.write_text(source)
    assert _derive(fixture)[0] == _expected(tmp_path / 'unchanged')


@pytest.mark.parametrize('definitions,prefix', [
    ("def validate(spec):\n    spec.base_prompt = 'different'\n", "validate(spec)"),
    ("def validate(spec):\n    spec.condition = 'different'\n", "validate(spec)"),
    ("def validate(spec):\n    spec.inputs['bundle'] = 'different'\n", "validate(spec)"),
    ("def validate(spec):\n    alias = spec\n    alias.base_prompt = 'different'\n", "validate(spec)"),
    ("def validate(spec):\n    names = spec.inputs\n    names.update({'bundle': 'different'})\n", "validate(spec)"),
    ("PROMPT_FILES = {}\ndef validate(spec):\n    PROMPT_FILES['generic'] = 'different'\n", "validate(spec)"),
    ("PROMPT_FILES = {}\ndef validate(spec):\n    alias = PROMPT_FILES\n    alias.update({'x': 'y'})\n", "validate(spec)"),
    ("body = 'original'\ndef validate(spec):\n    global body\n    body = 'different'\n", "validate(spec)"),
    ("def validate(spec):\n    setattr(spec, 'base_prompt', 'different')\n", "validate(spec)"),
    ("def mutate(spec):\n    spec.base_prompt = 'different'\n"
     "def validate(spec):\n    mutate(spec)\n", "validate(spec)"),
    ("def validate(spec):\n    opaque(spec)\n", "validate(spec)"),
    ("def validate(spec):\n    spec.validate()\n", "validate(spec)"),
    ("def validate(spec):\n    callee = spec.validate\n    callee()\n", "validate(spec)"),
    ("def validate(spec):\n    open('something').read()\n", "validate(spec)"),
    ("def validate(spec):\n    print(spec)\n", "validate(spec)"),
    ("def validate(spec):\n    spec.bundle.read_text()\n", "validate(spec)"),
    ("def validate(spec):\n    return spec\n", "validate(spec)"),
    ("def validate(spec):\n    yield spec\n", "validate(spec)"),
    ("@foreign\ndef validate(spec):\n    return None\n", "validate(spec)"),
    ("def validate(spec):\n    return None\nvalidate = foreign\n", "validate(spec)"),
    ("len = foreign\ndef validate(spec):\n    if len(()) != 0:\n        raise ValueError('bad')\n", "validate(spec)"),
    ("def validate(spec):\n    return None\n", "if spec.condition:\n    validate(spec)"),
    ("def validate(spec):\n    return None\n", "try:\n    validate(spec)\nexcept ValueError:\n    pass"),
    ("def validate(spec):\n    return None\n", "spec = validate(spec)"),
    ("def validate(spec):\n    return None\n", "callback = validate\ncallback(spec)"),
    ("def validate(spec):\n    validate(spec)\n", "validate(spec)"),
    ("def validate(spec):\n    while spec.condition:\n        pass\n", "validate(spec)"),
    ("def validate(spec):\n    for event in spec.events:\n        pass\n", "validate(spec)"),
    ("def validate(spec):\n    values = []\n    spec.inputs['values'] = values\n", "validate(spec)"),
    ("VALUES = {}\ndef validate(spec):\n    values = []\n    VALUES['values'] = values\n", "validate(spec)"),
])
def test_unproven_or_mutating_prefix_refuses(tmp_path, definitions, prefix):
    with pytest.raises(scan.ConfigError, match='not derived'):
        _derive(_fixture(tmp_path, definitions, prefix))


@pytest.mark.parametrize('relative,before,after', [
    (scan.RUNNER, '(weakref.ref(spec, forget), binding)', '(foreign, binding)'),
    (scan.RUNNER, 'import weakref', 'import weakref\nweakref = foreign'),
    (scan.RUNNER, 'import weakref', 'import weakref\nweakref.ref = foreign'),
    (scan.RUNNER, 'import os\n', 'import os\nos.fspath = foreign\n'),
    (scan.RUNNER, 'saved[0]() is spec', 'getattr(saved[0], "callback")() is spec'),
    (scan.RUNNER, 'return saved[1] if saved is not None and saved[0]() is spec else None',
     'spec.base_prompt = "changed"\n    return saved[1] if saved is not None and saved[0]() is spec else None'),
    (scan.RUNNER, 'result.append((name, None if value is None else os.fspath(value)))',
     'spec.inputs.append((name, None if value is None else os.fspath(value)))'),
    ('src/data_sheets_schema/provenance.py', 'shared = selection.get("shared_generation_version")',
     'selection["condition"] = "changed"\n    shared = selection.get("shared_generation_version")'),
    (scan.RUNNER, '_REGISTERED_INPUT_BINDINGS[identity] = (weakref.ref(spec, forget), binding)',
     '_REGISTERED_INPUT_BINDINGS[identity] = (weakref.ref(spec, forget), binding)\n'
     '    opaque(_REGISTERED_INPUT_BINDINGS)'),
    (scan.RUNNER, '_REGISTERED_INPUT_BINDINGS[identity] = (weakref.ref(spec, forget), binding)',
     '_REGISTERED_INPUT_BINDINGS[identity] = (weakref.ref(spec, forget), binding)\n'
     '    alias = _REGISTERED_INPUT_BINDINGS\n    alias[identity] = (foreign, binding)'),
    (scan.RUNNER, '_REGISTERED_INPUT_BINDINGS: dict[int, tuple[weakref.ReferenceType, _RegisteredInputBinding]] = {}',
     '_REGISTERED_INPUT_BINDINGS: dict[int, tuple[weakref.ReferenceType, _RegisteredInputBinding]] = {}\n'
     '_REGISTERED_INPUT_BINDINGS = foreign'),
])
def test_real_prefix_closure_drift_refuses(tmp_path, relative, before, after):
    fixture = _real_fixture(tmp_path)
    path = fixture[0] / relative
    source = path.read_text()
    assert source.count(before) == 1
    path.write_text(source.replace(before, after))
    with pytest.raises(scan.ConfigError, match='not derived'):
        _derive(fixture)


@pytest.mark.parametrize('method', [
    "    @property\n    def base_prompt(self):\n        opaque(self)\n        return 'changed'\n",
    "    def __getattribute__(self, name):\n        opaque(self)\n        return 'changed'\n",
])
def test_declared_fields_do_not_hide_descriptors_or_custom_attribute_access(tmp_path, method):
    fixture = _fixture(tmp_path, "def validate(spec):\n"
                       "    if spec.base_prompt is None:\n        raise ValueError('missing')\n")
    path = fixture[0] / scan.RUNNER
    path.write_text(path.read_text().replace('class RunSpec:\n', 'class RunSpec:\n' + method))
    with pytest.raises(scan.ConfigError, match='not derived'):
        _derive(fixture)


@pytest.mark.parametrize('replacement', [
    'body = body',
    'body = adapt_template(other, version=spec.guide_version)',
    'body = adapt_template(body, version=1)',
])
def test_proven_prefix_does_not_bypass_original_adapter_contract(tmp_path, replacement):
    fixture = _fixture(tmp_path, 'def validate(spec):\n    return None\n')
    path = fixture[0] / scan.RUNNER
    path.write_text(path.read_text().replace(
        'body = adapt_template(body, version=spec.guide_version)', replacement))
    with pytest.raises(scan.ConfigError, match='not derived'):
        _derive(fixture)
