# Purpose: prove the actual execute boundary for post-construction spelling drift, PR #5213.
# Inputs: synthetic SG2 and fake client; output: scratch pytest evidence. 2026-11-01.
# Allow synthetic token counting and stop at fake generation create; no provider.
from pathlib import Path

import pytest

from data_sheets_schema import api_runner as api
from tests.test_source_heading_runtime_api import draft_files, client  # noqa: F401
from tests.test_shared_generation_runtime import offline  # noqa: F401
from tests.test_wave7_5213_d76_registration import _registered_at_root


def test_relative_spelling_after_binding_reaches_provider_boundary(tmp_path, draft_files, monkeypatch):
    spec, reg = _registered_at_root(tmp_path, draft_files, monkeypatch, 'explicit')
    original = spec.bundle
    spec.bundle = Path(original.name)
    assert spec.bundle.absolute() == original
    fake = client(spec)
    reached = []

    class BoundaryReached(Exception):
        pass

    def stop_at_boundary(**kwargs):
        reached.append(sorted(kwargs))
        raise BoundaryReached('registered relative spelling reached the provider boundary')

    monkeypatch.setattr(fake.messages, 'create', stop_at_boundary)
    caught = None
    try:
        api.execute(spec, client=fake)
    except Exception as exc:
        caught = exc
    assert len(reached) == 1, repr(caught)
    assert caught is not None
    assert fake.messages.count_calls
    print('Reached generation create with registered bundle spelling:', str(spec.bundle))
    print('Injected stop surfaced as:', type(caught).__name__, str(caught))
    assert not spec.provenance_path.exists()
