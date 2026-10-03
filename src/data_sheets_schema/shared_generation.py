"""Explicit shared-generation API protocol and immutable caller registration.

Selection is preparation, not campaign, comparator or scientific approval.
No client, native process or network access occurs in this module.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

NAME = "shared_generation_v1"
FORMAT = "shared_generation_registration_v1"
PROMPT = "src/download/prompts/d4d_generic_arm_prompt_v10.md"
POLICY = "src/download/prompts/shared_generation_v1.md"
API_POLICY = "src/download/prompts/api_playbook_v2.md"
RECEIPT_POLICY = "src/download/prompts/receipt_completion_runtime_v2.md"
SELECTED_PLAYBOOKS = (
    ".claude/agents/d4d-provenance-guard-v2.md",
    ".claude/commands/d4d-agent-v2.md",
    ".claude/commands/d4d-full-core-v2.md",
    ".claude/commands/d4d-uniform-rules-v2.md",
)
# Versioned content identities. This is separate from the history-backed prompt
# registry; both must agree. No asset is trusted merely because it names itself.
ASSET_HASHES = {'.claude/agents/d4d-provenance-guard-v2.md': '10dc4689e1855096ef3507de01b129abfd5795690fbcfbd3458407741fe30085',
 '.claude/commands/d4d-agent-v2.md': 'dcb33659014a68596a248ed768c196dd0b1e396a0fe41579918dff95ac559299',
 '.claude/commands/d4d-full-core-v2.md': '2f52d3e70d7a6f3098b7acfcc80b9e9d0f318c9ca1517f711eae9fb789410124',
 '.claude/commands/d4d-uniform-rules-v2.md': '7b511b1ef15d6fb56d47dc58b367196ed9c7269a61406ed19127481f719c885a',
 'src/download/prompts/api_playbook_v2.md': '5fa3385ae994231cf68f8432d0dba35a86d8c4e37120e80d0aecda199f5ad719',
 'src/download/prompts/d4d_generic_arm_prompt_v10.md': 'a3a2004cef2147b3351613cb38a67abde1d58c91c19ee0c72c66ff476d0722ec',
 'src/download/prompts/receipt_completion_runtime_v2.md': 'c5f6b3818fabb9256bdb6d035eb1760b92cfe03ad0d8a60ab80becb51bf30d5c',
 'src/download/prompts/shared_generation_v1.md': '34608f26b4a0407da036486a6e8ec6692df6b54594335140bdc3df4229d78450'}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def captured_assets() -> dict[str, bytes]:
    """Verify installed bytes, then resolve references from those same bytes.

    The released provenance walker is deliberately tolerant for historical
    reports. A new selected execution instead refuses missing/changed inputs.
    """
    from .resources import resource_path
    from .provenance import _PLAYBOOK_REF
    captured = {name: resource_path(name).read_bytes() for name in ASSET_HASHES}
    for name, raw in captured.items():
        if sha(raw) != ASSET_HASHES[name]:
            raise ValueError(f"shared-generation selected asset changed: {name}")
    pending, reached = [PROMPT], set()
    while pending:
        name = pending.pop()
        for ref in _PLAYBOOK_REF.findall(captured[name].decode("utf-8")):
            if ref not in reached:
                if ref not in captured:
                    raise ValueError(f"unbound selected playbook reference: {ref}")
                reached.add(ref)
                pending.append(ref)
    expected = {name for name in ASSET_HASHES if name.startswith(".claude/")}
    if reached != expected:
        raise ValueError("selected playbook closure differs from the frozen protocol")
    return captured


def descriptor() -> dict:
    captured_assets()
    return {"protocol": NAME, "version": 1, "condition": "generic_v10",
            "renderer": 25, "runtime": "Claude API (direct)",
            "typed_protocol": "typed_audit_protocol_v1", "api_playbook_version": 2,
            "receipt_completion_version": 2, "assets": dict(ASSET_HASHES)}


def policy_text() -> str:
    return captured_assets()[POLICY].decode("utf-8").split("## Prompt body", 1)[1].strip()


def role_instruction() -> str:
    return "## Role relationship review v1" + policy_text().split("## Role relationship review v1", 1)[1]


def select(spec) -> dict | None:
    version = getattr(spec, "shared_generation_version", 0)
    if type(version) is not int or version not in (0, 1):
        raise ValueError("shared_generation_version must be the integer 0 or 1")
    registration = getattr(spec, "shared_generation_registration", None)
    if not version:
        if (registration is not None or spec.condition == "generic_v10"
                or spec.render_version == 25 or spec.api_playbook_version == 2
                or spec.receipt_completion_version == 2):
            raise ValueError("shared-generation selections require explicit version 1 and registration")
        return None
    if (spec.condition != "generic_v10" or spec.render_version != 25
            or spec.runtime != "Claude API (direct)" or spec.api_playbook_version != 2
            or spec.receipt_completion_version != 2 or spec.removal_repair_version
            or spec.native_source_attribution_version):
        raise ValueError("shared generation v1 requires generic_v10/API25/playbook2/receipt2; native and removal repair are not supported")
    if type(registration) is not str or not registration:
        raise ValueError("shared generation requires captured immutable registration JSON")
    return descriptor()
