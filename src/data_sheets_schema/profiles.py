"""Study text and vocabularies behind a profile (#628, #1302).

The reusable pipeline is schema-driven; what was Bridge2AI-specific lived
beside it in the same modules: the pinned B2AI vocabularies the schema digest
rendered for every dataset, the four-project defaults of the agreement
matrix, the AI-READI healthsheet input, and the project lists of the
manuscript's comparison arms. None of that is wrong for the study — it is
the study — and none of it belongs in front of another dataset.

A **profile** names those facts. Two ship here:

- ``bridge2ai`` — the study. Its vocabulary pin is the file the digest has
  always rendered, so the study's digest under this profile is exactly what
  its runs consumed; its arm project lists, agreement defaults and
  healthsheet input are the manuscript's.
- ``neutral`` — nothing pinned, nothing named. The digest renders the term
  sources the schema itself declares (GO, MeSH, EFO, NCIT for `data_topic`)
  and no registry list; the study arms do not exist.

**Selection** is by the source manifest, which is already the registry
(#623): a manifest with ``profile: bridge2ai`` selects the study profile, a
manifest with no ``profile:`` (or none selected at all) is neutral, and
``D4D_PROFILE`` in the environment overrides both for a single process. A
profile is never inferred from a project name.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

#: The pinned registry vocabularies the study's digest renders (#538).
STUDY_VOCABULARY_PIN = Path(__file__).with_name("b2ai_registry_vocabularies.yaml")

#: The default source manifest — the registry's own constant where the
#: registry module exists (#623, cluster 1), the same path otherwise, so
#: this module does not depend on that change landing first.
try:                                                    # pragma: no cover - import shape
    from data_sheets_schema.registry import DEFAULT_MANIFEST
except ImportError:
    DEFAULT_MANIFEST = Path("data/preprocessed/source_manifest.yaml")


@dataclass(frozen=True)
class Profile:
    name: str
    #: Vocabularies for slots that declare `values_from`, or None for none:
    #: the digest then renders only the schema's own term sources.
    vocabulary_pin: Path | None = None
    #: The comparison arms that exist only for this study, with the projects
    #: each may run on (`constants.GENERATION_ARMS[...]["projects"]`).
    arm_projects: dict[str, list[str]] = field(default_factory=dict)
    #: The projects a bare `scripts/agreement.py` invocation reports over —
    #: the set the published matrix was computed on (#467).
    agreement_projects: tuple[str, ...] = ()
    #: The healthsheet-only arm's upstream record and bundle name.
    healthsheet_record: Path | None = None
    healthsheet_bundle: str | None = None

    @property
    def pin_path(self) -> Path | None:
        """Where this profile's vocabulary is read from *now*. The study's
        pin is `schema_digest.VOCABULARY_PIN`, read at call time, so a test
        or a caller that repoints that constant repoints the study profile
        too — the one override point the digest has always had."""
        if self.vocabulary_pin is None:
            return None
        if self.vocabulary_pin == STUDY_VOCABULARY_PIN:
            from data_sheets_schema import schema_digest
            return Path(schema_digest.VOCABULARY_PIN)
        return self.vocabulary_pin

    @property
    def has_vocabulary(self) -> bool:
        pin = self.pin_path
        return pin is not None and pin.exists()


BRIDGE2AI = Profile(
    name="bridge2ai",
    vocabulary_pin=STUDY_VOCABULARY_PIN,
    arm_projects={"healthsheet_only": ["AI_READI"],
                  "crate_only": ["CHORUS", "CM4AI", "VOICE"]},
    agreement_projects=("AI_READI", "CHORUS", "CM4AI", "VOICE"),
    healthsheet_record=Path("data/raw/AI_READI/fairhub_api_dataset_3_2026-07-27.json"),
    healthsheet_bundle="AI_READI_healthsheet_only.txt",
)

NEUTRAL = Profile(name="neutral")

PROFILES: dict[str, Profile] = {p.name: p for p in (BRIDGE2AI, NEUTRAL)}

#: Environment override, for one process: `D4D_PROFILE=neutral`.
ENV_VAR = "D4D_PROFILE"


def profile_named(name: str) -> Profile:
    try:
        return PROFILES[name]
    except KeyError:
        raise ValueError(f"unknown profile {name!r}; known: {', '.join(sorted(PROFILES))}") from None


def declared_profile(manifest: Path | str | None) -> str | None:
    """The `profile:` a manifest declares, or None."""
    if manifest is None:
        return None
    p = Path(manifest)
    if not p.exists():
        return None
    from data_sheets_schema.schema_cache import load_yaml
    data = load_yaml(p) or {}
    value = data.get("profile") if isinstance(data, dict) else None
    return str(value) if value else None


def active_profile(manifest: Path | str | None = "default") -> Profile:
    """The profile in force: `D4D_PROFILE` if set, else what the selected
    manifest declares, else neutral.

    `manifest="default"` means "whatever the default registry is" — the
    study's manifest when the checkout carries one — so a caller that has
    not selected a manifest (the digest cache, a bare script) gets the
    study profile in the study's checkout and the neutral one anywhere
    else. Pass `None` for a run that selected no manifest.
    """
    env = os.environ.get(ENV_VAR)
    if env:
        return profile_named(env)
    if manifest == "default":
        manifest = DEFAULT_MANIFEST
    name = declared_profile(manifest)
    return profile_named(name) if name else NEUTRAL


def vocabulary_for(profile: Profile) -> dict[str, dict[str, str]]:
    """The profile's pinned vocabularies keyed by `values_from` name; `{}`
    for a profile that pins none."""
    if not profile.has_vocabulary:
        return {}
    import yaml
    doc = yaml.safe_load(vocabulary_bytes(profile)) or {}
    return dict(doc.get("vocabularies") or {})


def vocabulary_bytes(profile: Profile) -> bytes:
    """The bytes the digest cache keys on: the pin's, or none."""
    return profile.pin_path.read_bytes() if profile.has_vocabulary else b""
