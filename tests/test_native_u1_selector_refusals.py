"""Native selector refuses before input discovery or spending (#4354 U1)."""
import pytest
from data_sheets_schema import api_runner as api

@pytest.mark.parametrize('axes', [
    {},
    {'native_shared_generation_version': True},
    {'native_shared_generation_version': False},
    {'native_shared_generation_version': 1, 'shared_generation_version': 1},
    {'native_shared_generation_version': 1, 'bounded_carry_version': 1},
    {'native_shared_generation_version': 1},
])
def test_selector_refuses_before_discovery_or_spending(monkeypatch, axes):
    def forbidden(*args, **kwargs):
        pytest.fail('refused selection reached input discovery or execution')
    monkeypatch.setattr(api, 'select_manifest', forbidden)
    monkeypatch.setattr(api, 'execute', forbidden)
    with pytest.raises(ValueError):
        api.RunSpec(project='fixture', arm='generic', method='claudecode_direct', label='offline',
                    bundle=None, condition='generic_v10', runtime='Claude Code', render_version=26,
                    provider='fixture', reasoning_effort='high', profile='neutral',
                    profile_basis='fixture', prompt_text_env=True, **axes)

# Round 2: begin from a valid captured selection so each rejection isolates
# exactly one axis, instead of relying on a second missing prerequisite.
from dataclasses import replace
from tests.test_native_shared_selection import declaration
from tests.test_native_shared_render import native_spec


@pytest.mark.parametrize('axis', [
    'native_source_attribution_version', 'shared_generation_version',
    'api_playbook_version', 'receipt_completion_version',
    'removal_repair_version', 'bounded_carry_version',
])
@pytest.mark.parametrize('value', [1, True, False], ids=['enabled', 'true', 'false'])
def test_each_companion_axis_refuses_before_discovery(native_spec, monkeypatch, axis, value):
    def forbidden(*args, **kwargs):
        pytest.fail('invalid axis reached discovery, capture, or execution')
    monkeypatch.setattr(api, 'select_manifest', forbidden)
    monkeypatch.setattr(api, 'execute', forbidden)
    from data_sheets_schema import native_shared_render, shared_generation
    monkeypatch.setattr(native_shared_render, 'bind_selection', forbidden)
    monkeypatch.setattr(shared_generation, 'select', forbidden)
    with pytest.raises(ValueError, match='cannot mix old/API axes'):
        replace(native_spec, **{axis: value})


@pytest.mark.parametrize('value', [0, True, False, None, 2], ids=['missing', 'true', 'false', 'null', 'unsupported'])
def test_native_selector_axis_refuses_before_discovery(native_spec, monkeypatch, value):
    def forbidden(*args, **kwargs):
        pytest.fail('invalid native selector reached discovery or execution')
    monkeypatch.setattr(api, 'select_manifest', forbidden)
    monkeypatch.setattr(api, 'execute', forbidden)
    with pytest.raises(ValueError, match='native_shared_generation_version|explicit native shared selection'):
        replace(native_spec, native_shared_generation_version=value)


@pytest.mark.parametrize('axis', [
    'native_source_attribution_max_checks', 'receipt_completion_registration',
    'shared_generation_registration',
])
def test_each_old_registration_refuses_before_discovery(native_spec, monkeypatch, axis):
    def forbidden(*args, **kwargs):
        pytest.fail('old registration reached discovery or execution')
    monkeypatch.setattr(api, 'select_manifest', forbidden)
    monkeypatch.setattr(api, 'execute', forbidden)
    with pytest.raises(ValueError, match='cannot reuse old/API registrations'):
        replace(native_spec, **{axis: 1 if axis.endswith('max_checks') else '{}'})
