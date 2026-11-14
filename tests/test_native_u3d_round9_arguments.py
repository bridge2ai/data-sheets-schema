"""D9 cheap refusals precede current-source verification and effects."""
import pytest
from data_sheets_schema import native_shared_registration_orchestration as registration


@pytest.mark.parametrize('key,value,diagnostic', [
    ('receipt_origin_version', True, 'receipt_origin_version'),
    ('attempt_id', '../bad', 'safe component'),
    ('max_draft_checks', False, 'draft-check allowance'),
    ('composition_path', 'relative.json', 'canonical'),
    ('attempt_directory', '/different', 'basename'),
])
def test_argument_refusal_precedes_git_file_reads_and_gate_loading(tmp_path, monkeypatch, key, value, diagnostic):
    arguments = dict(composition_path=str(tmp_path / 'composition'), system_path=str(tmp_path / 'system'),
        permission_probe_path=str(tmp_path / 'probe'), attempt_id='attempt',
        attempt_directory=str(tmp_path / 'attempt'), evidence_directory=str(tmp_path / 'evidence'),
        max_draft_checks=2, receipt_origin_version=0)
    arguments[key] = value
    def forbidden(*args, **kwargs):
        pytest.fail('invalid arguments reached source verification or file reads')
    monkeypatch.setattr(registration, '_require_integrated_gate_implementation', forbidden)
    monkeypatch.setattr(registration.authority, 'dependency_identity', forbidden)
    monkeypatch.setattr(registration.consumer, '_read', forbidden)
    with pytest.raises(ValueError, match=diagnostic):
        registration.registration(**arguments)
    assert list(tmp_path.iterdir()) == []
