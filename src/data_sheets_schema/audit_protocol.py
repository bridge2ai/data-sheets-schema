"""Explicit offline audit protocol selection; no scientific acceptance."""
from __future__ import annotations

LEGACY = "audit_protocol_v1"
TYPED = "typed_audit_protocol_v1"
KINDS = frozenset({"role_placement", "status_scope", "date_scope",
                   "absence_or_self_narration", "quotation_fidelity",
                   "identifier_count", "attribution", "omission", "other"})


def check_version(value: int) -> int:
    """Version selection is caller-owned, never inferred from candidate JSON."""
    if type(value) is not int or value not in (1, 2):
        raise ValueError("audit version must be exactly 1 or 2")
    return value


def select(name: str) -> dict:
    """Return a fresh descriptor for an explicitly named offline protocol.

    This selector grants no live execution registration or scientific approval.
    Existing unselected grammar/batch calls retain their version-1 defaults.
    """
    if type(name) is not str or name not in (LEGACY, TYPED):
        raise ValueError("unknown audit protocol")
    version = 2 if name == TYPED else 1
    return {"protocol": name, "grammar_version": version,
            "batch_version": version, "output_format_version": version,
            "evidence_protocol": 7,
            "omission_inventory_version": 1 if version == 2 else None}
