"""D156 regression: full-suite collection must not contaminate helper authority."""
from pathlib import Path
import sys

from tests.utils.native_helper_environment import helper_environment, helper_import_paths


def test_preparation_and_helper_paths_match_despite_collection_pollution(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    foreign = tmp_path / 'collection-only'
    foreign.mkdir()
    (foreign / 'unowned.py').write_text('value = 1\n')
    polluted = [str(foreign), str(root / 'fairscape_models'), *sys.path]
    monkeypatch.setattr(sys, 'path', polluted)
    expected = helper_import_paths(root)
    with helper_environment(root):
        assert sys.path == expected
        assert str(foreign) not in sys.path
        # Isolation is at entry, not a census filter or reusable verdict.
        sys.path.append(str(foreign))
        assert str(foreign) in sys.path
    assert sys.path is polluted


def test_helper_environment_restores_paths_on_refusal(tmp_path):
    import pytest
    original = sys.path
    with pytest.raises(ValueError, match='synthetic refusal'):
        with helper_environment(Path(__file__).resolve().parents[1]):
            raise ValueError('synthetic refusal')
    assert sys.path is original
