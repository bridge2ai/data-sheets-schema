"""Final ordinary artifacts have their own bound, separate from sealed originals."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_sheets_schema import native_shared_contract as c
from data_sheets_schema import native_shared_current as current
from data_sheets_schema import native_shared_evidence as evidence


def run(tmp_path, *, maximum=8_000_000, pool=None):
    paths = {name: str(tmp_path / (name + '.yaml')) for name in ('full', 'core', 'report', 'receipt')}
    return SimpleNamespace(spec=SimpleNamespace(_agentic_artifact_paths=paths),
        composition={'policy': {'post_final_recorder': {'destination': str(tmp_path / 'provenance.yaml')}}},
        selection=SimpleNamespace(bounds=lambda: {'max_input_bytes': maximum}),
        reader=SimpleNamespace(pool=pool))


@pytest.mark.parametrize('role,key', [('final_full', 'full'), ('final_core', 'core'), ('final_report', 'report')])
def test_expanded_final_and_same_captured_only_bytes(tmp_path, monkeypatch, role, key):
    selected = run(tmp_path)
    path = selected.spec._agentic_artifact_paths[key]
    raw = b'# final expansion\n' + b'x' * c.HARD_LIMITS['original_full_bytes']
    Path(path).write_bytes(raw)
    actual = current.current_artifact(selected, role, path)
    member = evidence.read_regular(path, role, max_bytes=8_000_000)
    selected.reader.pool = evidence.CapturePool((member,), ())
    monkeypatch.setattr(evidence, 'read_regular', lambda *a, **k: pytest.fail('saved artifact read live bytes'))
    assert current.current_artifact(selected, role, path) == actual
    assert actual.raw == raw


@pytest.mark.parametrize('role,key', [('final_full', 'full'), ('final_core', 'core'), ('final_report', 'report')])
def test_selected_caller_bound_is_enforced_before_read(tmp_path, role, key):
    selected = run(tmp_path, maximum=10)
    path = selected.spec._agentic_artifact_paths[key]
    Path(path).write_bytes(b'x' * 11)
    with pytest.raises(ValueError, match='role byte bound'):
        current.current_artifact(selected, role, path)


def test_original_receipt_keeps_its_seal_limit(tmp_path):
    selected = run(tmp_path)
    path = selected.spec._agentic_artifact_paths['receipt']
    Path(path).write_bytes(b'x' * (c.HARD_LIMITS['original_full_bytes'] + 1))
    with pytest.raises(ValueError, match='role byte bound'):
        current.current_artifact(selected, 'original_receipt_output', path)


def test_no_saved_fallback_or_role_substitution(tmp_path, monkeypatch):
    selected = run(tmp_path, pool=evidence.CapturePool((), ()))
    path = selected.spec._agentic_artifact_paths['full']
    monkeypatch.setattr(evidence, 'read_regular', lambda *a, **k: pytest.fail('saved fallback'))
    with pytest.raises(ValueError, match='missing, ambiguous or oversized'):
        current.current_artifact(selected, 'final_full', path)
    with pytest.raises(ValueError, match='selected exact role'):
        current.current_artifact(selected, 'final_core', path)
