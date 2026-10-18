"""Trusted resource selection for released and explicitly requested instruments.

Selection is independent of evaluator output. Exact new-output acceptance
defaults to version 3; historical versions keep their original resource bytes.
Version 4 changes only rubric20 Q19 and deliberately reuses the frozen v3
evidence-name authority, not the names in the current schema.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticInstrument:
    rubric_path: str
    definition_path: str
    schema_path: str
    agent: str
    version: str
    evidence_authority_path: str | None


def select_semantic_instrument(rubric_name: str, version: str) -> SemanticInstrument:
    """Resolve a supported family/version; refuse unsupported combinations.

    Paths are repository-relative so an isolated registration can copy and pin
    the same resources without depending on this process's working directory.
    """
    if not isinstance(rubric_name, str):
        raise ValueError("unknown general-context semantic rubric")
    rubric = rubric_name.removesuffix("-semantic")
    if rubric not in {"rubric10", "rubric20"}:
        raise ValueError(f"unknown general-context semantic rubric: {rubric_name}")
    if version not in ("2.0", "3.0", "4.0") or (version == "4.0" and rubric != "rubric20"):
        raise ValueError(f"unsupported semantic instrument: {rubric_name} version {version!r}")
    suffix = "_semantic_v4" if version == "4.0" else ""
    agent = f"d4d-{rubric}-semantic" + ("-v4" if version == "4.0" else "")
    return SemanticInstrument(
        rubric_path=f"data/rubric/{rubric}{suffix}.txt",
        definition_path=f".claude/agents/{agent}.md",
        schema_path=f"src/download/prompts/{rubric}_semantic"
                    + ("_v4" if version == "4.0" else "") + "_schema.json",
        agent=agent,
        version=version,
        evidence_authority_path=("data/rubric/semantic_evidence_authority_v3.json"
                                 if version in ("3.0", "4.0") else None),
    )
