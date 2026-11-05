"""D67/F17: retirement refuses admission, without erasing historical text."""
import pytest
from data_sheets_schema import api_runner as api
from tests.test_download.test_api_runner import spec


@pytest.mark.parametrize('project', ['CHORUS', 'NEWPROJ'])
def test_new_tuned_registration_refused_before_outputs(project, tmp_path):
    with pytest.raises(ValueError, match='tuned is retired for new registrations'):
        spec(project=project, condition='tuned', out_dir=tmp_path / 'outputs')
    assert list(tmp_path.iterdir()) == []


def test_historical_tuned_reading_retained_but_cannot_execute(tmp_path):
    historical = spec(condition='tuned', _replay_only=True, render_version=7, out_dir=tmp_path / 'outputs')
    assert 'PROJECT-SPECIFIC EVIDENCE' in api.resolve_prompt(historical)
    replayed = api.RunSpec.from_render_spec(historical.render_spec(), project=historical.project,
        method=historical.method, label=historical.label)
    assert replayed.instruction == historical.instruction
    with pytest.raises(ValueError, match='retired for execution'):
        api.execute(replayed, client=object())
    assert list(tmp_path.iterdir()) == []
