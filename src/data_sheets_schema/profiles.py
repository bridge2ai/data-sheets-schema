"""Study text and vocabularies behind a profile (#628, #1302).

The reusable pipeline is schema-driven; what was Bridge2AI-specific lived
beside it in the same modules: the pinned B2AI vocabularies the schema digest
rendered for every dataset, the four-project defaults of the agreement
matrix, the AI-READI healthsheet input, and the project lists of the
manuscript's comparison arms. None of that is wrong for the study — it is
the study — and none of it belongs in front of another dataset.

A **profile** names those facts. Two ship here:

- ``bridge2ai`` — the study. Its vocabulary pin is the file the digest has
  always rendered — the study's registry lists — and its arm project lists,
  agreement defaults and healthsheet input are the manuscript's. (The
  digest text itself moved with the term-source scope, `a91bad8b` →
  `cd3c79f2`, a registered boundary: no earlier record resumes under it.)
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
STUDY_VOCABULARY_PIN = Path("src/data_sheets_schema/b2ai_registry_vocabularies.yaml")   # a resource, resolved when read (#1680)

#: The source checkout this module is imported from, or None for an install:
#: `pyproject.toml` two levels up (`<root>/src/data_sheets_schema/profiles.py`).
from data_sheets_schema.resources import CHECKOUT_ROOT as _CHECKOUT_ROOT   # the one checkout test (#1577, #1643)


class MissingVocabulary(FileNotFoundError, ValueError):
    """A profile declares a vocabulary the resources do not carry (#1715,
    #1729). A `ValueError` too, so every command that already turns an
    unknown profile into a click error does the same for this."""


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
    #: The dataset that record describes — written into the bundle's
    #: header as its identity (#1464).
    healthsheet_project: str | None = None
    #: How that dataset is written in prose — the tracked study bundle says
    #: "AI-READI baseline" where the key is `AI_READI` (#1542).
    healthsheet_display: str | None = None

    @property
    def pin_path(self) -> Path | None:
        """The vocabulary file this profile reads: the digest module's pin
        when the profile tracks it, else its own — resolved through the
        resource resolver when spelled relative, so it is the working
        checkout's copy from a checkout and package data from an install,
        never the importing code's (#1680)."""
        if self.vocabulary_pin is None:
            return None
        if self.tracks_digest_pin:
            from data_sheets_schema import schema_digest
            pin = Path(schema_digest.VOCABULARY_PIN)
        else:
            pin = Path(self.vocabulary_pin)
        if pin.is_absolute():
            return pin
        from data_sheets_schema.resources import resource_path
        return resource_path(pin)

    @property
    def has_vocabulary(self) -> bool:
        """Declared and present. A profile that declares a vocabulary whose
        file is not where the resources are is an error here too, so no
        reader renders the neutral instrument in its place (#1715, #1729)."""
        pin = self.pin_path
        if pin is None:
            return False
        if not pin.exists():
            raise MissingVocabulary(f"the {self.name} profile declares a vocabulary at {pin}, which is not there; "
                                    "its digest cannot be rendered from this checkout (#1715)")
        return True


BRIDGE2AI = Profile(
    name="bridge2ai",
    vocabulary_pin=STUDY_VOCABULARY_PIN,
    tracks_digest_pin=True,
    arm_projects={"healthsheet_only": ["AI_READI"],
                  "crate_only": ["CHORUS", "CM4AI", "VOICE"]},
    agreement_projects=("AI_READI", "CHORUS", "CM4AI", "VOICE"),
    healthsheet_record=Path("data/raw/AI_READI/fairhub_api_dataset_3_2026-07-27.json"),
    healthsheet_bundle="AI_READI_healthsheet_only.txt",
    healthsheet_project="AI_READI",
    healthsheet_display="AI-READI",
)

NEUTRAL = Profile(name="neutral")

PROFILES: dict[str, Profile] = {p.name: p for p in (BRIDGE2AI, NEUTRAL)}

#: Environment override, for one process: `D4D_PROFILE=neutral`.
ENV_VAR = "D4D_PROFILE"


@dataclass(frozen=True)
class Selection:
    """A profile and why it was selected — what a record states (#1443)."""
    profile: Profile
    #: `environment`; `no manifest`; `stated by the caller`;
    #: `manifest:<path>@<sha256[:12]>` or `default manifest:<path>@<sha256[:12]>`,
    #: each with ` (undeclared)` when the manifest has no `profile:` key;
    #: `<kind>:<path> (missing)` when the path is not there;
    #: `rendered instruction`, with ` (this process would select <name>: <basis>)`
    #: when the recorder's own selection differs, or
    #: ` (this process could not select one: <error>)` when it could not
    #: select at all, for the profile a launch instruction carried (#1581,
    #: #1606); `re-rendered to the recorded hash by d4d provenance
    #: backfill-spec (#772)` on a spec that command reconstructed for a
    #: record stating no profile (#1607). The path is repository-relative
    #: under the checkout (#1466, #1494).
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
    try:
        data = load_yaml(p)
    except Exception as exc:                                   # noqa: BLE001 — yaml or OS; the file is named (#1586)
        raise ValueError(f"manifest {p} could not be read: {exc}") from None
    if data is None:
        return None                                            # an empty document declares nothing
    if not isinstance(data, dict):
        # The registry refuses this file; the digest must not read it as
        # an undeclared profile and switch instruments (#1610).
        raise ValueError(f"manifest {p} is not a mapping")
    value = data.get("profile")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"manifest {p} declares profile {value!r}, which is not a profile name")
    return value.strip()


def default_manifest() -> Path | None:
    """The manifest a caller that selected none is read against, decided
    when asked rather than when imported (#1439): the working directory's
    default manifest if there is one, else the checkout's when this package
    is imported from a checkout — so a script run from `tests/` in the
    study's checkout still sees the study's — else none (the registry's
    rule, #1491; an ancestor's manifest waits on #1523)."""
    # The registry's rule, not a second one (#1491).
    from data_sheets_schema.registry import default_manifest_path
    p = default_manifest_path()
    return p if p.exists() else None


def _shown(path: Path) -> str:
    """How a basis names a manifest: repository-relative for one under the
    checkout, so the same file reads the same from any directory and no
    local path reaches a record (#1466, cf. #398); as given otherwise."""
    p = Path(path)
    if _CHECKOUT_ROOT is not None:
        try:
            return p.resolve().relative_to(_CHECKOUT_ROOT.resolve()).as_posix()
        except (ValueError, OSError):
            pass
    return p.as_posix()


def _stamp(path: Path) -> str:
    """Twelve hex characters of the manifest's sha256, so one basis string
    never names two manifests (#1466)."""
    import hashlib
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]
    except OSError:
        return "unreadable"


def basis_for(kind: str, manifest: Path) -> str:
    return f"{kind}:{_shown(manifest)}@{_stamp(manifest)}"


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
    p = Path(manifest)
    if not p.exists():
        # Not a fallback that hides: the basis names the path and says it
        # was not there (#1494).
        return Selection(NEUTRAL, f"{basis}:{_shown(p)} (missing)")
    name = declared_profile(p)
    if name:
        return Selection(profile_named(name), basis_for(basis, p))
    # The silent fallback #1439 wanted visible: neutral because the manifest
    # declares nothing, said as such.
    return Selection(NEUTRAL, basis_for(basis, p) + " (undeclared)")


def active_profile(manifest: Path | str | None | Any = "default") -> Profile:
    """`select_profile(manifest).profile` — for callers that need no basis."""
    return select_profile(manifest).profile


def for_record(record: dict[str, Any] | None) -> Profile:
    """The profile a *record's* readers use (#1462): the one its `schema`
    block states, else the ambient one — a record that predates profiles
    was made under the study's, which is the ambient one in the study's
    checkout. Evaluation, review packs and backfills read this, never the
    environment alone, so a historical record keeps its instrument when the
    environment changes."""
    schema = (record or {}).get("schema") if isinstance(record, dict) else None
    if not isinstance(schema, dict):
        schema = {}
    name = schema.get("profile")
    if name:
        try:
            return profile_named(str(name))
        except ValueError as exc:
            import warnings
            warnings.warn(f"record states a profile this code does not know ({exc}); read as the study's",
                          RuntimeWarning, stacklevel=2)
            return BRIDGE2AI
    # No profile: a record made before profiles existed — every one of them
    # the study's, digest or not (103 corpus records carry neither; #1518,
    # #1583) — and it must not follow the environment.
    return BRIDGE2AI


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
    """The bytes the digest cache keys on: the pin's, or none for a profile
    that declares no vocabulary. A profile that declares one whose file is
    not where the resources are is an error, never the neutral instrument
    in disguise (#1715, #1729): the study's digest cannot be rendered from
    a checkout that lacks the study's vocabulary."""
    return profile.pin_path.read_bytes() if profile.has_vocabulary else b""
