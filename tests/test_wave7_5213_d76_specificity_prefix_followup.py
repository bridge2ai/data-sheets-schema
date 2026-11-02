"""PR #5213 / D76 T8: bounded follow-ups to source-domain proof review.

Inputs: calibrated source-only T8 fixtures and the scanner. Outputs: pytest
results and owned temporary source fixtures, 2026-11-02. No fixture production
code is imported or executed. Preserve the earlier 52- and 22-case files.
"""
import pytest

from tests import test_wave7_5213_d76_specificity_prefix_review as review


def test_r3_r4_wildcard_import_cannot_replace_the_certified_callable(tmp_path):
    fixture = review._simple(tmp_path)
    review._calibrate(fixture, tmp_path)
    path = fixture[0] / review.base.scan.RUNNER
    (path.parent / 'prefix_wildcard.py').write_text(
        "__all__ = ('validate',)\n"
        "def validate(spec):\n    spec.base_prompt = 'changed'\n")
    path.write_text(path.read_text()
                    + '\nfrom data_sheets_schema.prefix_wildcard import *\n')
    review._refuses(fixture)


@pytest.mark.parametrize('declaration', [
    "def unused(self, value=locals().__setitem__('base_prompt', PromptDescriptor())):",
    "def unused(self, *, value=locals().__setitem__('base_prompt', PromptDescriptor())):",
    "def unused(self, value: locals().__setitem__('base_prompt', PromptDescriptor())):",
], ids=['positional-default', 'keyword-only-default', 'eager-annotation'])
def test_r5_method_definition_expressions_cannot_install_a_field_descriptor(tmp_path, declaration):
    fixture = review._reading_fixture(tmp_path)
    review._calibrate(fixture, tmp_path)
    path = fixture[0] / review.base.scan.RUNNER
    review._install_descriptor_definition(path)
    review._replace_once(path, '    guide_version: int\n',
        '    guide_version: int\n    ' + declaration + '\n        pass\n')
    # These expressions are evaluated in the class namespace while the method
    # is defined. The synthetic module has no postponed-annotations import.
    # PromptDescriptor's class access raises AttributeError, so this remains a
    # valid required dataclass field instead of creating a default-order error.
    review._refuses(fixture)


def test_r3_same_named_formal_does_not_hide_its_global_default_capture(tmp_path):
    fixture = review._simple(tmp_path,
        "def mutate(spec):\n    spec.base_prompt = 'changed'\n"
        "def validate(spec):\n    return None\n")
    review._calibrate(fixture, tmp_path)
    path = fixture[0] / review.base.scan.RUNNER
    path.write_text(path.read_text() + '\n'
        'def redirect(validate=validate):\n'
        '    validate.__code__ = mutate.__code__\n'
        'redirect()\n')
    # The default's right-hand validate is the module callable, even though the
    # receiving function binds a same-named local formal in its body.
    review._refuses(fixture)


def _finite_loops(widths):
    lines = ['def validate(spec):']
    for depth, width in enumerate(widths, start=1):
        values = ', '.join(repr(str(i)) for i in range(width))
        lines.append('    ' * depth + f'for name_{depth} in ({values},):')
    lines.append('    ' * (len(widths) + 1) + 'pass')
    return '\n'.join(lines) + '\n'


def test_r1_nested_finite_loops_have_a_shared_abstract_work_bound(tmp_path):
    small = _finite_loops((2, 2, 2))
    fixture = review._simple(tmp_path, small)
    review._calibrate(fixture, tmp_path)
    path = fixture[0] / review.base.scan.RUNNER
    review._replace_once(path, small, _finite_loops((16, 16, 32)))
    # Only source is analyzed: the fixture's 8,192 innermost passes never run.
    # The certificate's shared abstract-work budget is at most 4,096 visits;
    # per-loop length caps alone do not bound nested or interprocedural work.
    # This is a deterministic refusal contract, not a timing benchmark.
    review._refuses(fixture)


def test_r3_eager_function_annotation_cannot_mutate_the_certified_callable(tmp_path):
    fixture = review._simple(tmp_path,
        "def mutate(spec):\n    spec.base_prompt = 'changed'\n"
        "def validate(spec):\n    return None\n")
    review._calibrate(fixture, tmp_path)
    path = fixture[0] / review.base.scan.RUNNER
    path.write_text(path.read_text() + '\n'
        "def unused(value: setattr(validate, '__code__', mutate.__code__)):\n"
        '    pass\n')
    # With no postponed-annotations import, this expression changes the live
    # callable at definition time, even though the receiving function is unused.
    review._refuses(fixture)


def test_r3_eager_annotation_value_cannot_escape_to_a_callable_writer(tmp_path):
    fixture = review._simple(tmp_path,
        "def mutate(spec):\n    spec.base_prompt = 'changed'\n"
        "def validate(spec):\n    return None\n")
    review._calibrate(fixture, tmp_path)
    path = fixture[0] / review.base.scan.RUNNER
    path.write_text(path.read_text() + '\n'
        'def keep(value: validate):\n    pass\n'
        "keep.__annotations__['value'].__code__ = mutate.__code__\n")
    # Merely rejecting annotation Calls is insufficient: this annotation has
    # no Call node, but it exports the actual callable through __annotations__.
    review._refuses(fixture)
