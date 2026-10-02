"""Frozen names that semantic v3 may assert absent (#3027, #3196).

This is a token-name authority, not class/range validation. Loading today's
merged schema during acceptance would silently change an existing instrument.
The shipped snapshot instead names its source bytes and has its own digest.
"""
from __future__ import annotations

import hashlib
import json

from data_sheets_schema.resources import resource_path


AUTHORITY_PATH = "data/rubric/semantic_evidence_authority_v3.json"


def load_authority() -> tuple[frozenset[str], str]:
    """Return the trusted frozen names and the SHA256 of their exact artifact."""
    raw = resource_path(AUTHORITY_PATH).read_bytes()
    authority = json.loads(raw)
    names = authority.get("names") if isinstance(authority, dict) else None
    if (not isinstance(authority, dict) or authority.get("semantic_version") != "3.0"
            or authority.get("authority_version") != "1.0"
            or not isinstance(names, list) or not names
            or any(not isinstance(name, str) or not name for name in names)
            or names != sorted(set(names))):
        raise ValueError("invalid semantic v3 absence-name authority")
    return frozenset(names), hashlib.sha256(raw).hexdigest()


def authority_digest() -> str:
    return load_authority()[1]


def verify_authority(metadata: dict) -> frozenset[str]:
    names, digest = load_authority()
    if metadata.get("evidence_authority_sha256") != digest:
        raise ValueError("semantic evidence authority does not match its recorded SHA256; "
                         "validate with the pinned authority")
    return names
