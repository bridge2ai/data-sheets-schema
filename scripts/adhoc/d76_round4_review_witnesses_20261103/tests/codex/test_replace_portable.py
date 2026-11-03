"""PR #5213 replacement check, 2026-11-01.
Inputs: unchanged synthetic fixture, current interpreter. Output: scratch pytest evidence.
Correct the original probe's Python-version-specific ValueError expectation;
retain all binding, fresh-cache and literal-replay assertions at both heads.
"""
from dataclasses import replace
from pathlib import Path

import pytest
from data_sheets_schema import api_runner as api
from tests.test_generation_manifest_identity import external  # noqa: F401


def test_replace_revalidates_and_preserves_replay_refusal(external, monkeypatch):
    monkeypatch.chdir(external.bundle.parent)
    spec = replace(external, registered_input_paths=True)
    _ = spec.instruction
    rebuilt = replace(spec, bundle=Path(spec.bundle.name))
    assert rebuilt is not spec and rebuilt.bundle.is_absolute()
    assert rebuilt.bundle == spec.bundle
    assert 'instruction' in vars(spec) and 'instruction' not in vars(rebuilt)
    if hasattr(rebuilt, '_registered_input_spellings'):
        assert rebuilt._registered_input_spellings == spec._registered_input_spellings
        with pytest.raises((TypeError, ValueError), match='init=False'):
            replace(spec, _registered_input_spellings=())
    recorded = {**external.render_spec(), 'registered_input_paths': True}
    replay = api.RunSpec.from_render_spec(recorded, project=external.project,
                                         method=external.method, label=external.label)
    assert replace(replay)._replay_only is True
    with pytest.raises(ValueError, match='historical prompt replay cannot execute'):
        api.execute(replace(replay))
