"""The prepare flag and its registration round trip (#2467, #2528-#2530); adapted from the #2518 review."""
from pathlib import Path
import pytest
from budgeted_cborg import BudgetStop
from audit_controls import prepare, registration
from audit_controls import reconcile_stopped as tool
from audit_controls.test_context_preparation import ancestry, save  # noqa: F401


def test_the_flag_round_trips_and_pins_the_authorization(ancestry, tmp_path, tmp_path_factory):
    # The fixture's sequence state sits at the top of tmp_path, so the output needs another root.
    out = tmp_path_factory.mktemp('outside') / 'stop_reconciliation'
    path = prepare.prepare(**ancestry[0], destination=tmp_path/'auto', automatic_stop_reconciliation=True,
                           automatic_stop_reconciliation_dir=str(out))
    manifest = registration.validate_registration(path)
    assert manifest[tool.SELECTION_KEY] == tool.selection(out.resolve())
    assert str(tool.STANDING_AUTHORIZATION) in manifest['pinned_files']
    # The model-facing texts are unchanged by the selection.
    legacy = registration.validate_registration(prepare.prepare(**ancestry[0], destination=tmp_path/'legacy'))
    assert Path(manifest['job']['system_prompt']).read_bytes() == Path(legacy['job']['system_prompt']).read_bytes()
    a = Path(manifest['job']['instruction']).read_text().replace(str(tmp_path/'auto'), 'DEST')
    b = Path(legacy['job']['instruction']).read_text().replace(str(tmp_path/'legacy'), 'DEST')
    assert a == b


def test_a_default_output_inside_the_sequence_directory_is_refused_before_anything_exists(ancestry, tmp_path):
    """#2529/#2530: this fixture keeps the destination beside the sequence state."""
    with pytest.raises(BudgetStop, match="sequence state's directory"):
        prepare.prepare(**ancestry[0], destination=tmp_path/'auto', automatic_stop_reconciliation=True)
    assert not (tmp_path/'auto').exists()


@pytest.mark.parametrize('arguments, match', [
    ({'automatic_stop_reconciliation': 1}, 'explicit boolean'),                     # #2538
    ({'automatic_stop_reconciliation_dir': '/tmp/x'}, 'needs --automatic-stop-reconciliation')])
def test_a_malformed_selection_is_refused_before_the_destination_exists(ancestry, tmp_path, arguments, match):
    with pytest.raises(BudgetStop, match=match):
        prepare.prepare(**ancestry[0], destination=tmp_path/'auto', **arguments)
    assert not (tmp_path/'auto').exists()


@pytest.mark.parametrize('shape', ['existing_dir', 'missing_parent'])
def test_an_output_the_stop_could_not_create_is_refused_at_preparation(ancestry, tmp_path, tmp_path_factory, shape):
    """#2535: refused before anything exists, not discovered at stop."""
    outside = tmp_path_factory.mktemp('outside')
    out = outside / 'missing' / 'out' if shape == 'missing_parent' else outside / 'exists'
    if shape == 'existing_dir':
        out.mkdir()
    with pytest.raises(BudgetStop, match='must not exist yet'):
        prepare.prepare(**ancestry[0], destination=tmp_path/'auto', automatic_stop_reconciliation=True,
                        automatic_stop_reconciliation_dir=str(out))
    assert not (tmp_path/'auto').exists()


def test_a_tampered_selection_is_refused_by_registration(ancestry, tmp_path, tmp_path_factory):
    path = prepare.prepare(**ancestry[0], destination=tmp_path/'auto', automatic_stop_reconciliation=True,
                           automatic_stop_reconciliation_dir=str(tmp_path_factory.mktemp('outside') / 'out'))
    value = registration.read_json(path)
    value[tool.SELECTION_KEY]['authorization']['path'] = '/elsewhere.json'
    save(path, value)
    with pytest.raises(BudgetStop):
        registration.validate_registration(path)
