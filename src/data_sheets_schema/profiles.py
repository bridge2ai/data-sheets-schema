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
profile is never inferred from a project name. A run resolves its profile
**once**, from the manifest it selected, and passes it to every digest it
renders and to the record it writes (`select_profile`; #1438) — the record
carries the profile and the basis of its selection beside the digest md5
(#1443), so a neutral fallback is visible rather than silent (#1439).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from data_sheets_schema.registry import DEFAULT_MANIFEST

#: The pinned registry vocabularies the study's digest renders (#538).
STUDY_VOCABULARY_PIN = Path(__file__).with_name("b2ai_registry_vocabularies.yaml")

#: The source checkout this module is imported from, or None for an install:
#: `pyproject.toml` two levels up (`<root>/src/data_sheets_schema/profiles.py`).
_CHECKOUT_ROOT: Path | None = (
    Path(__file__).resolve().parents[2]
    if (Path(__file__).resolve().parents[2] / "pyproject.toml").exists() else None)


@dataclass(frozen=True)
class Profile:
    name: str
    #: Vocabularies for slots that declare `values_from`, or None for none:
    #: the digest then renders only the schema's own term sources.
    vocabulary_pin: Path | None = None
    #: Whether `vocabulary_pin` is read through `schema_digest.VOCABULARY_PIN`
    #: at call time — the one override point the digest has always had, so a
    #: test or a caller that repoints that constant repoints this profile
    #: too. Declared, not inferred from the pin's path (#1446).
    tracks_digest_pin: bool = False
    #: The comparison arms that exist only for this study, with the projects
    #: each may run on. The arm table (`constants.GENERATION_ARMS`) declares
    #: the arm; which datasets it applies to is the profile's fact (#1444).
    arm_projects: dict[str, list[str]] = field(default_factory=dict)
    #: The projects a bare `scripts/agreement.py` invocation reports over —
    #: the set the published matrix was computed on (#467).
    agreement_projects: tuple[str, ...] = ()
    #: The healthsheet-only arm's upstream record and bundle name.
    healthsheet_record: Path | None = None
    healthsheet_bundle: str | None = None

    @property
    def pin_path(self) -> Path | None:
        """Where this profile's vocabulary is read from *now*."""
        if self.vocabulary_pin is None:
            return None
        if self.tracks_digest_pin:
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
    tracks_digest_pin=True,
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


@dataclass(frozen=True)
class Selection:
    """A profile and why it was selected — what a record states (#1443)."""
    profile: Profile
    #: `environment`, `manifest:<path>`, `default manifest:<path>`, or
    #: `no manifest`.
    basis: str

    @property
    def name(self) -> str:
        return self.profile.name


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


def default_manifest() -> Path | None:
    """The manifest a caller that selected none is read against, decided
    when asked rather than when imported (#1439): the working directory's
    default manifest if there is one, else the checkout's when this package
    is imported from a checkout — so a script run from `tests/` in the
    study's checkout still sees the study's — else none."""
    rel = Path(DEFAULT_MANIFEST)
    if rel.exists():
        return rel
    if _CHECKOUT_ROOT is not None and (_CHECKOUT_ROOT / rel).exists():
        return _CHECKOUT_ROOT / rel
    return None


def select_profile(manifest: Path | str | None | Any = "default") -> Selection:
    """The profile in force and the basis of its selection: `D4D_PROFILE` if
    set, else what the manifest declares, else neutral.

    `manifest="default"` means "whatever the default registry is" (see
    `default_manifest`). Pass `None` for a run that selected no manifest.
    """
    env = os.environ.get(ENV_VAR)
    if env:
        return Selection(profile_named(env), "environment")
    basis = "manifest"
    if isinstance(manifest, str) and manifest == "default":
        manifest = default_manifest()
        basis = "default manifest"
    if manifest is None:
        return Selection(NEUTRAL, "no manifest")
    name = declared_profile(manifest)
    return Selection(profile_named(name) if name else NEUTRAL, f"{basis}:{Path(manifest).as_posix()}")


def active_profile(manifest: Path | str | None | Any = "default") -> Profile:
    """`select_profile(manifest).profile` — for callers that need no basis."""
    return select_profile(manifest).profile


def arm_projects_for(arm: str, profile: Profile | None = None) -> list[str] | None:
    """The datasets an arm may run on under the profile — the study's
    lists for its comparison arms, None where the profile scopes it to
    none (a neutral profile has no comparison arms)."""
    prof = profile or active_profile()
    return prof.arm_projects.get(arm)


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
