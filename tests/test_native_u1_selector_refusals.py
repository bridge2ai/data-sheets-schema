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
