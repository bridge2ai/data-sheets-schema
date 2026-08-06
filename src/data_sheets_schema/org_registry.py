"""Resolve organization identifiers from the B2AI Standards registry (#378).

The registry (https://github.com/bridge2ai/b2ai-standards-registry,
``src/data/Organization.yaml``) assigns stable ``B2AI_ORG:N`` CURIEs to
curated organizations, alongside ROR and Wikidata identifiers. A vendored
snapshot lives beside this module so resolution is deterministic and
offline; the snapshot's hash and fetch date are recorded in every
enrichment, because "which registry" is part of the claim.

Resolution is deliberately strict — exact match on normalized ``name``
(acronym), ``description`` (full name) or ROR id. No fuzzy matching: a
wrong identifier asserted confidently is worse than a name left alone,
and this pass may never invent what the registry does not state.

Enrichment is not extraction. Filling ``Organization.id`` from a lookup
adds a fact no source document stated, so it happens only in this explicit
post-generation pass, is recorded in provenance, and never runs inside the
generation phases.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REGISTRY_PATH = Path(__file__).parent / "registry" / "b2ai_organizations.yaml"
REGISTRY_SOURCE = ("https://github.com/bridge2ai/b2ai-standards-registry/"
                   "blob/main/src/data/Organization.yaml")
REGISTRY_FETCHED = "2026-08-06"

_ROR_IN_TEXT = re.compile(r"ror\.org/([0-9a-z]+)")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


class OrgResolver:
    """Name/ROR -> B2AI_ORG CURIE, from the vendored snapshot."""

    def __init__(self, path: Path = REGISTRY_PATH):
        raw = path.read_bytes()
        self.snapshot_sha256 = hashlib.sha256(raw).hexdigest()
        orgs = yaml.safe_load(raw)["organizations"]
        self._by_name: dict[str, dict[str, Any]] = {}
        self._by_ror: dict[str, dict[str, Any]] = {}
        for o in orgs:
            for key in ("name", "description"):
                if o.get(key):
                    # First writer wins: the registry occasionally reuses a
                    # description; a collision must not silently re-point.
                    self._by_name.setdefault(_norm(o[key]), o)
            if o.get("ror_id"):
                self._by_ror[str(o["ror_id"]).replace("ror:", "")] = o

    def resolve(self, text: str) -> dict[str, Any] | None:
        """The registry entry for a name, full name or embedded ROR, or None."""
        if not text or not isinstance(text, str):
            return None
        ror = _ROR_IN_TEXT.search(text)
        if ror and ror.group(1) in self._by_ror:
            return self._by_ror[ror.group(1)]
        return self._by_name.get(_norm(text))


def enrich_record(record: dict[str, Any],
                  resolver: OrgResolver | None = None,
                  ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Fill Organization.id with B2AI_ORG CURIEs where the registry matches.

    Touches only inline organization objects that have a ``name``, no ``id``,
    and at most the Organization class's own keys — and only when the name
    resolves. Returns (record, enrichments); each enrichment names the path,
    the name matched, and the CURIE written, ready for provenance. The
    record is modified in place and also returned.
    """
    resolver = resolver or OrgResolver()
    log: list[dict[str, Any]] = []

    def walk(v: Any, path: str) -> None:
        if isinstance(v, dict):
            keys = set(v)
            if ("name" in keys and "id" not in keys
                    and keys <= {"name", "description"}):
                hit = resolver.resolve(v["name"])
                if hit:
                    v["id"] = hit["id"]
                    log.append({"path": path, "name": v["name"],
                                "id": hit["id"],
                                "ror_id": hit.get("ror_id")})
            for k, x in v.items():
                walk(x, f"{path}/{k}")
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{path}/{i}")

    walk(record, "")
    return record, log


def enrichment_block(log: list[dict[str, Any]],
                     resolver: OrgResolver) -> dict[str, Any]:
    """The provenance block an enrichment pass writes beside its edits."""
    return {
        "kind": "organization_identifiers",
        "source": REGISTRY_SOURCE,
        "snapshot_sha256": resolver.snapshot_sha256,
        "snapshot_fetched": REGISTRY_FETCHED,
        "performed_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "note": ("Identifiers added by deterministic registry lookup — "
                 "enrichment, not extraction; no source document stated "
                 "them."),
        "resolved": log,
    }
