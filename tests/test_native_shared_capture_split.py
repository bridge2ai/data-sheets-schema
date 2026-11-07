"""Negative C orchestration order tests, U3-C round four, 2026-11-07.

The mocked verifier deliberately refuses. These tests prove only explicit
projection forwarding and refusal before reconstruction/writes; they are not
a positive classifier, committed-consumer or execution-admission proof.
"""
from contextlib import contextmanager
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("entry", ("activate", "_base"))
def test_live_capture_forwards_projection_and_refuses_before_effects(monkeypatch, entry):
    from data_sheets_schema import native_execution_registration_v2 as authority
    from data_sheets_schema import native_shared_capture_orchestration as orchestration
    from data_sheets_schema import native_shared_controller_orchestration as controller
    from data_sheets_schema import native_shared_selection as selection

    class ExpectedRefusal(ValueError):
        pass

    calls = []
    # Opaque identity for a deliberately refusing protocol unit, never a
    # substitute for a real loader-minted positive execution fixture.
    scope_identity = object()
    raw = b"unadmitted execution; verifier must refuse"

    @contextmanager
    def opened_scope():
        calls.append("scope opened")
        try:
            yield scope_identity
        finally:
            calls.append("scope closed")

    def refuse(value, *, classifier_projection):
        assert value is raw
        assert classifier_projection is scope_identity
        calls.append("verification refused")
        raise ExpectedRefusal("deliberate A refusal before C effects")

    def forbidden(*args, **kwargs):
        pytest.fail("refused execution reached reconstruction or a writer")

    monkeypatch.setattr(orchestration.controls_orchestration, "loaded_controls", opened_scope)
    monkeypatch.setattr(authority, "verified", refuse)
    monkeypatch.setattr(controller, "reconstruct_composition", forbidden)
    monkeypatch.setattr(orchestration, "_create", forbidden)
    monkeypatch.setattr(orchestration, "_append", forbidden)

    if entry == "activate":
        invoke = lambda: orchestration.activate(object(), raw, b"unadmitted started bytes")
    else:
        # Only the prerequisite input read is replaced. There is intentionally
        # no complete E/C/S fixture and no possible successful reconstruction.
        captured = SimpleNamespace(role=lambda role: "/selected/execution.json")
        monkeypatch.setattr(selection, "capture", lambda path: captured)

        class Reader:
            def __init__(self, supplied):
                assert supplied is captured

            def read(self, role, path):
                assert (role, path) == ("execution_capture", "/selected/execution.json")
                return SimpleNamespace(raw=raw)

        monkeypatch.setattr(orchestration, "_Reader", Reader)
        invoke = lambda: orchestration._base("/selected/selection.json")

    with pytest.raises(ExpectedRefusal, match="deliberate A refusal"):
        invoke()
    assert calls == ["scope opened", "verification refused", "scope closed"]

