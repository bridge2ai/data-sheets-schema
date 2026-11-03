# Purpose: probe post-construction registered spelling drift for PR #5213, 2026-11-01.
# Inputs: synthetic SG2 fixture; outputs: preflight/late-guard evidence, no provider calls.
from pathlib import Path

import pytest

from data_sheets_schema import api_runner as api, shared_generation as sg
from data_sheets_schema import source_heading_completed as complete
from tests.test_source_heading_runtime_api import draft_files  # noqa: F401
from tests.test_wave7_5213_d76_registration import _registered_at_root


@pytest.mark.parametrize('field', ['bundle', 'manifest'])
def test_postconstruction_relative_spelling_is_admitted_by_preflight_but_rejected_late(tmp_path, draft_files, monkeypatch, field):
    spec, reg = _registered_at_root(tmp_path, draft_files, monkeypatch, 'explicit')
    original = getattr(spec, field)
    setattr(spec, field, original.relative_to(tmp_path))
    assert getattr(spec, field).absolute() == original
    assert getattr(spec, field).read_bytes() == original.read_bytes()
    monkeypatch.setattr(api, 'provider_identity', lambda: {'provider': None, 'base_url': None, 'key_env': None})
    captured = sg.assert_current(spec)
    assert sg.preflight(spec, api._model_settings(spec.condition)) is captured
    paths = {key: str(getattr(spec, key + '_path')) for key in ('full', 'core', 'report', 'provenance')}

    class Reader:
        def raw(self, path):
            return Path(path).read_bytes()

    with pytest.raises(ValueError, match='completed path display differs'):
        complete._check_path_display(complete._live_path_display(spec), paths, reg, Reader())
