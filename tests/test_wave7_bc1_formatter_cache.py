"""Causal A17 formatter-cache regression for BC1 Wave7 (2026-10-29)."""
import pytest

from data_sheets_schema import audit_omissions as omissions, bc1_audit as audit
from tests.test_bc1_audit import supplied


def test_changed_extracted_formatter_cannot_reuse_a_warmed_bc1_entry(supplied, monkeypatch):
    cache = audit.DerivationCache()
    packet = audit.prepare(**supplied, derivations=cache)
    assert cache.refresh() and len(cache._rows) == 1
    assert audit.prepare(**supplied, derivations=cache) == packet
    assert audit.prepare(**supplied) == packet
    cache._shared_generation_derivations = {"invented": b'"old schema text"'}

    def changed_formatter(*args, **kwargs):
        raise ValueError("wave7 changed omission formatter")

    monkeypatch.setattr(omissions, "_render_prepared", changed_formatter)
    with pytest.raises(ValueError, match="^wave7 changed omission formatter$"):
        audit.prepare(**supplied)
    with pytest.raises(ValueError, match="^wave7 changed omission formatter$"):
        audit.prepare(**supplied, derivations=cache)
    assert cache.refresh() is False
    assert cache._rows == {} and cache._bytes == 0
    assert not hasattr(cache, "_shared_generation_derivations")
