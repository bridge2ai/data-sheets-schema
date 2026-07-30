"""Track and compare parallel D4D generation runs.

Naming convention
-----------------
``data/d4d_concatenated/{METHOD}/{DATE}_{MODEL}_r{N}/{PROJECT}_d4d[_core].yaml``

- **METHOD** encodes the arm (``claudecode_agent`` = baseline,
  ``claudecode_agent_crate`` = de novo, ``claudecode_agent_healthsheet`` =
  healthsheet-only, plus their ``_core`` counterparts).
- **{DATE}_{MODEL}** identifies the configuration.
- **r{N}** is the replicate index.

The label is therefore *identical across arms of the same round*: hold the label
constant and vary METHOD to compare arms; hold METHOD constant and vary ``r{N}``
to compare replicates.

Why "replicate" and not "seed"
------------------------------
These runs expose no seed. Temperature 0.0 does not make an agentic run
deterministic — tool-call ordering, retrieval order and context assembly all
vary between runs. ``r{N}`` therefore labels an independent sample from an
uncontrolled process. Calling it a seed would imply a reproducibility guarantee
that does not exist here.

Deterministic arms (``rocrate_mapped``, ``rocrate_static_map``) are excluded
from the replicate convention on purpose: re-running them over unchanged inputs
is idempotent, so a replicate index would imply sampling that does not happen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
import shutil
from pathlib import Path

import yaml

CONCAT_DIR = Path("data/d4d_concatenated")
# Replicate marker is `_rep{N}` — deliberately NOT `_r{N}`.
#
# Historical runs use `-r{N}` to mean a *revision* (a changed pipeline), e.g.
# 2026-07-23_gpt-5.5-high-fast-r2 switched from Claude Code to Codex CLI. An
# earlier version of this module used `_r{N}` for *replicate*, leaving the two
# opposite meanings separated by a single character. `_rep{N}` cannot be
# confused with `-r{N}` at a glance or under a typo.
REPLICATE_RE = re.compile(r"^(?P<config>.+?)_rep(?P<replicate>\d+)$")
LEGACY_REVISION_RE = re.compile(r"^(?P<config>.+?)-r(?P<revision>\d+)$")

ARM_BY_METHOD = {
    "claudecode_agent": "baseline",
    "claudecode_agent_core": "baseline",
    "claudecode_agent_crate": "de_novo",
    "claudecode_agent_crate_core": "de_novo",
    "claudecode_agent_healthsheet": "healthsheet_only",
    "claudecode_agent_healthsheet_core": "healthsheet_only",
    "claudecode_agent_crate_only": "crate_only",
    "claudecode_agent_crate_only_core": "crate_only",
    "rocrate_mapped": "deterministic_upstream",
    "rocrate_static_map": "deterministic_ours",
}
DETERMINISTIC = {"rocrate_mapped", "rocrate_static_map"}


@dataclass
class Run:
    method: str
    label: str
    arm: str
    config: str | None
    replicate: int | None
    projects: list[str] = field(default_factory=list)
    is_core: bool = False
    deterministic: bool = False
    legacy_revision: int | None = None

    @property
    def path(self) -> Path:
        return CONCAT_DIR / self.method / self.label


def discover(concat_dir: Path = CONCAT_DIR) -> list[Run]:
    """Find every run directory on disk."""
    runs: list[Run] = []
    for method_dir in sorted(p for p in concat_dir.iterdir() if p.is_dir()):
        method = method_dir.name
        for label_dir in sorted(p for p in method_dir.iterdir() if p.is_dir()):
            records = sorted(label_dir.glob("*_d4d*.yaml"))
            if not records:
                continue
            m = REPLICATE_RE.match(label_dir.name)
            legacy = LEGACY_REVISION_RE.match(label_dir.name)
            implicit_first = (m is None and legacy is None
                              and method not in DETERMINISTIC)
            projects = []
            for r in records:
                name = r.stem
                for suffix in ("_d4d_core", "_d4d"):
                    if name.endswith(suffix):
                        projects.append(name[: -len(suffix)])
                        break
            runs.append(Run(
                method=method,
                label=label_dir.name,
                arm=ARM_BY_METHOD.get(method, "unknown"),
                config=m.group("config") if m else (
                    label_dir.name if implicit_first else None),
                replicate=int(m.group("replicate")) if m else (
                    1 if implicit_first else None),
                legacy_revision=int(legacy.group("revision")) if legacy else None,
                projects=sorted(set(projects)),
                is_core=method.endswith("_core"),
                deterministic=method in DETERMINISTIC,
            ))
    return runs


# Header fields that define the *procedure*. Two runs are replicates only if
# these agree; if they differ, the runs used different pipelines and their
# difference measures the pipeline change, not sampling variance.
PROCEDURE_FIELDS = ("Generation Method", "Agent runtime", "Provider", "Model",
                    "Reasoning effort", "Mode")

# Values that carry no procedural information. Agents invent wording for any
# header field the prompt does not pin down — "Reasoning effort" came back as
# "default" from one run and "not applicable" from another on an identical
# configuration. Treating those as a procedure change is a false positive.
# A field with a real value (e.g. "high") still discriminates.
PLACEHOLDER_VALUES = {"", "-", "n/a", "na", "none", "null", "default",
                      "not applicable", "unspecified", "not specified"}


def procedure_fingerprint(path: Path) -> dict[str, str]:
    """Extract the procedure-defining header fields from a generated record."""
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            break
        body = line.lstrip("#").strip()
        key, _, value = body.partition(":")
        if key.strip() in PROCEDURE_FIELDS:
            v = value.strip()
            if v.lower() not in PLACEHOLDER_VALUES:
                out[key.strip()] = v
    return out


def slots(path: Path) -> set[str]:
    return set(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def record_path(method: str, label: str, project: str,
                concat_dir: Path = CONCAT_DIR) -> Path | None:
    core = method.endswith("_core")
    name = f"{project}_d4d_core.yaml" if core else f"{project}_d4d.yaml"
    p = concat_dir / method / label / name
    return p if p.exists() else None


def is_complete(method: str, label: str, project: str,
                concat_dir: Path = CONCAT_DIR) -> bool:
    """A run is complete only when full, core and report all exist.

    Phases 3-4 back-port corrections into the full record, so a full record
    that exists is not necessarily a finished one. Comparing mid-flight output
    silently measures an unfinished run.
    """
    base = method[:-5] if method.endswith("_core") else method
    full = concat_dir / base / label / f"{project}_d4d.yaml"
    core = concat_dir / f"{base}_core" / label / f"{project}_d4d_core.yaml"
    report = concat_dir / f"{base}_core" / label / f"{project}_reconciliation.md"
    return full.exists() and core.exists() and report.exists()


VALID, INVALID, UNVERIFIED, STALE = "valid", "invalid", "unverified", "stale"


def validation_status(method: str, label: str, project: str,
                      concat_dir: Path = CONCAT_DIR) -> str:
    """Whether a run's records are known to validate against the schema.

    Three states, deliberately — `is_complete()` only checks that three files
    exist, so a record that fails LinkML validation is "complete" and gets
    analysed. But validating on demand is not an option either: the corpus holds
    100+ records and each validation costs seconds, so calling the validator
    from an analysis hot path would make `compare()` unusable.

    So the answer is read from the run's own provenance record, which
    `api_runner.execute()` now writes. A run whose record predates that, or was
    produced by the agent path, reports UNVERIFIED — not VALID. Treating absence
    of evidence as validity is how an invalid record enters an analysis, which
    is exactly what this exists to prevent. Populate it with `d4d runs validate`.
    """
    from data_sheets_schema.provenance import record_path_for
    rec = record_path_for(project, method, label, concat_dir)
    if not rec.exists():
        return UNVERIFIED
    try:
        data = yaml.safe_load(rec.read_text(encoding="utf-8")) or {}
    except Exception:
        return UNVERIFIED
    v = data.get("validation")
    if not isinstance(v, dict) or "passed" not in v:
        return UNVERIFIED

    # A verdict is about specific bytes. Re-hash the artifacts it was reached
    # on: if a record was edited since, the recorded `passed` is a claim about
    # a file that no longer exists in that form. STALE rather than UNVERIFIED
    # because the diagnosis differs — "validated, then changed" is a different
    # problem from "never checked" — and both mean do not rely on it.
    from data_sheets_schema.provenance import _md5
    artifacts = v.get("artifacts")
    if isinstance(artifacts, dict) and artifacts:
        for entry in artifacts.values():
            if not isinstance(entry, dict):
                continue
            recorded, path = entry.get("md5"), entry.get("path")
            if not recorded or not path:
                continue
            if _md5(Path(path)) != recorded:
                return STALE

    return VALID if v["passed"] else INVALID


def record_mode(method: str, label: str, project: str,
                concat_dir: Path = CONCAT_DIR) -> str:
    """`live`, `reconstructed`, or `none` — how a run's provenance was obtained.

    A `live` record was written *by the run*, so it observed the model, prompt
    and inputs. A `reconstructed` one was backfilled afterwards from whatever the
    headers preserved, with the rest marked `unrecoverable`. Reconstructed does
    not mean wrong; it means nobody observed it at the time.
    """
    import yaml as _yaml
    from data_sheets_schema.provenance import record_path_for
    p = record_path_for(project, method, label, concat_dir)
    if not p.exists():
        return "none"
    data = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return str(data.get("record_mode") or "none")


# What a record must pin for its run to be re-identifiable. Deliberately not
# "everything a live record captures": hardware and software versions do not
# determine a D4D generation, and 56 of 59 reconstructed records name `system`
# as their only gap. Gating on completeness would reject them for missing a
# field that changes nothing.
ATTESTING_FIELDS = ("inputs.bundle_md5", "schema.full_md5", "model.model")

# Recognised `hash_basis` values, matched exactly. A substring test cannot be
# used here: `"verified" in "unverified"` is True, and so is `"verified" in
# "not verified against the run"` — the two phrasings most likely to describe an
# *unverified* hash would both promote the record. `UNVERIFIED` is already part
# of this module's vocabulary, so that is a phrasing waiting to be written.
VERIFIED_HASH_BASES = frozenset({
    "verified identical to the bytes consumed",
})

LIVE, ATTESTED, PARTIAL, NO_RECORD = "live", "attested", "partial", "none"


# From this date a run is required to write its own provenance. Dated rather
# than applied to the whole corpus on purpose: 59 existing records were
# reconstructed after the fact, and 33 of those are fully attested — the
# 2026-07-27 tuned arm pins its bundle, schema, model and outputs, and lacks only
# the hardware. Failing them retroactively would discard placeable evidence to
# enforce a rule that did not exist when they ran. The requirement is about
# stopping the ratio worsening, so it applies going forward.
LIVE_REQUIRED_FROM = "2026-07-30"


def requires_live(label: str) -> bool:
    """Whether this run is subject to the live-provenance requirement.

    Read from the label's date prefix, which every run label carries by
    convention (`{YYYY-MM-DD}_{provider-model-settings}`). A label with no
    parseable date is treated as subject to the rule: a run that cannot say when
    it happened is a new run for this purpose, and the alternative — exempting
    anything unparseable — is an exemption anyone could take by accident.
    """
    m = re.match(r"(\d{4}-\d{2}-\d{2})", label or "")
    return m.group(1) >= LIVE_REQUIRED_FROM if m else True


def check_provenance(method: str, label: str, project: str,
                     concat_dir: Path = CONCAT_DIR) -> dict:
    """Whether a run satisfies the live-provenance requirement.

    Separate from `is_complete()` deliberately. Folding this into completeness
    would reclassify every pre-cutoff run in one step and change every
    downstream count as a side effect of adding a rule.
    """
    mode = record_mode(method, label, project, concat_dir)
    level = attestation(method, label, project, concat_dir)
    required = requires_live(label)
    ok = (not required) or mode == "live"
    if ok:
        reason = ("live provenance present" if mode == "live"
                  else f"predates {LIVE_REQUIRED_FROM}; not required")
    elif mode == "none":
        reason = ("no provenance record. The run cannot state the conditions it "
                  "ran under, and nobody can reconstruct them later with "
                  "certainty.")
    else:
        reason = (f"provenance is {mode}, not live. It was assembled after the "
                  "fact, so it reports what could be recovered rather than what "
                  "was observed.")
    return {"method": method, "label": label, "project": project,
            "record_mode": mode, "attestation": level,
            "required": required, "ok": ok, "reason": reason}


def attestation(method: str, label: str, project: str,
                concat_dir: Path = CONCAT_DIR) -> str:
    """How well a run's conditions can be established — four levels, not two.

    `record_mode` alone is too blunt to gate on. A reconstructed record can pin
    the bundle by verified md5, the schema by md5, the model, and every output
    hash — the 2026-07-27 tuned arm does exactly that, and names hardware as its
    sole gap. Excluding it as "not live" would drop 24 records for missing a
    field that cannot affect a generation.

    - ``live``     — written by the run, which observed its own conditions.
    - ``attested`` — reconstructed, but every output-determining field is
      present and the input bytes were *verified*, not assumed.
    - ``partial``  — reconstructed with a gap in something that determines the
      output, most often an unverifiable input bundle.
    - ``none``     — no record at all.

    `attested` is the level worth gating on. `live` is stronger evidence about
    *how* the record came to exist, but for the question "can this run be placed
    and reproduced?" the two are equivalent.
    """
    import yaml as _yaml
    from data_sheets_schema.provenance import record_path_for
    p = record_path_for(project, method, label, concat_dir)
    if not p.exists():
        return NO_RECORD
    data = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if data.get("record_mode") == "live":
        return LIVE

    for dotted in ATTESTING_FIELDS:
        node: Any = data
        for part in dotted.split("."):
            node = (node or {}).get(part) if isinstance(node, dict) else None
        if not node:
            return PARTIAL

    # Outputs are checked for a *hash*, not for the presence of the block.
    # `{"full": None, "core": None}` is a truthy dict that pins nothing, so
    # testing the container let a record naming its artifacts without hashing
    # any of them count as attested.
    outputs = data.get("outputs") or {}
    if not any(isinstance(a, dict) and a.get("md5")
               for a in outputs.values() if a):
        return PARTIAL

    # A bundle md5 computed today from a file that may have changed says nothing
    # about the bytes the run consumed. Only a recognised, explicitly verified
    # basis counts; anything unrecognised is treated as unverified.
    basis = ((data.get("inputs") or {}).get("hash_basis") or "").strip().lower()
    return ATTESTED if basis in VERIFIED_HASH_BASES else PARTIAL


def compare(method: str, project: str, labels: list[str],
            concat_dir: Path = CONCAT_DIR,
            exclude_invalid: bool = True,
            require_live: bool = False,
            require_attested: bool = False) -> dict:
    """Slot-level agreement across runs of one method for one project.

    Records known to fail validation are excluded by default: comparing slot
    sets between a valid record and a broken one measures the breakage. Records
    of unknown validity are included but counted, so the caller can see how much
    of the result rests on unchecked input.

    Two gates, and ``require_attested`` is the one worth using.

    ``require_live`` keeps only runs that wrote their own provenance. That sounds
    like the strict choice and is mostly the wrong one: it drops the entire
    2026-07-27 tuned arm, whose records pin the bundle by *verified* md5, the
    schema by md5, the model, and every output hash, and whose sole gap is the
    hardware — which cannot affect a generation. 24 records excluded over a field
    that changes nothing.

    ``require_attested`` keeps `live` and `attested` alike, dropping only runs
    with a gap in something that determines the output. On this corpus that is
    82 runs kept and 23 dropped, and the dropped ones are the 2026-04 and
    2026-07-23 series whose bundles were only committed on 2026-07-28 — their
    consumed bytes are genuinely unverifiable, not merely unrecorded.

    Both are off by default, and `attestations` is returned either way, so a
    permissive result can never look uniform. The strict view is one flag away;
    the loose view never lies about what it rests on.
    """
    present: dict[str, set[str]] = {}
    incomplete: list[str] = []
    invalid: list[str] = []
    unverified: list[str] = []
    modes: dict[str, str] = {}
    levels: dict[str, str] = {}
    not_live: list[str] = []
    unattested: list[str] = []
    for label in labels:
        if not is_complete(method, label, project, concat_dir):
            incomplete.append(label)
            continue
        modes[label] = record_mode(method, label, project, concat_dir)
        levels[label] = attestation(method, label, project, concat_dir)
        if levels[label] != LIVE:
            not_live.append(label)
            if require_live:
                continue
        if levels[label] in (PARTIAL, NO_RECORD):
            unattested.append(f"{label} ({levels[label]})")
            if require_attested:
                continue
        status = validation_status(method, label, project, concat_dir)
        if status == INVALID:
            invalid.append(label)
            if exclude_invalid:
                continue
        elif status in (UNVERIFIED, STALE):
            # STALE is grouped with UNVERIFIED for reporting: both mean the
            # record's validity is unknown *now*, whatever was true before.
            unverified.append(f"{label} ({status})" if status == STALE else label)
        p = record_path(method, label, project, concat_dir)
        if p:
            present[label] = slots(p)
    if len(present) < 2:
        return {"error": f"need >=2 COMPLETE runs with {project} under {method}; "
                         f"found {len(present)}"
                         + (f"; excluded as incomplete: {incomplete}" if incomplete else "")
                         + (f"; excluded as invalid: {invalid}" if invalid else "")}
    sets = list(present.values())
    stable = set.intersection(*sets)
    union = set.union(*sets)

    # Replicate comparison is only meaningful across an identical procedure.
    prints = {}
    for label in present:
        p = record_path(method, label, project, concat_dir)
        if p:
            prints[label] = procedure_fingerprint(p)
    distinct = {tuple(sorted(fp.items())) for fp in prints.values()}
    same_procedure = len(distinct) <= 1

    return {
        "project": project,
        "method": method,
        "labels": list(present),
        "counts": {k: len(v) for k, v in present.items()},
        "stable": sorted(stable),
        "varying": sorted(union - stable),
        "agreement": len(stable) / len(union) if union else 1.0,
        "same_procedure": same_procedure,
        "procedures": prints,
        "excluded_incomplete": incomplete,
        "excluded_invalid": invalid,
        # Always reported, whether or not require_live is set: an agreement
        # figure over reconstructed records is a claim resting on conditions
        # nobody observed, and the caller should be able to see that without
        # having asked.
        "provenance_modes": modes,
        "attestations": levels,
        "reconstructed": not_live,
        "unattested": unattested,
        "excluded_not_live": not_live if require_live else [],
        "excluded_unattested": unattested if require_attested else [],
        "all_live": not not_live,
        # The figure that matters: every run can be placed and reproduced, even
        # where its provenance was recovered afterwards rather than observed.
        "all_attested": not unattested,
        # Not a warning to be ignored: an agreement figure computed over
        # unverified records is a claim about records nobody has checked.
        "unverified": unverified,
        "all_verified": not unverified and not invalid,
    }


class ReplicateMismatch(RuntimeError):
    """A new replicate does not share the established procedure."""


def input_fingerprint(method: str, label: str, project: str,
                      concat_dir: Path = CONCAT_DIR) -> str | None:
    """The md5 of the input bundle a run actually consumed.

    Read from the run's provenance record, not the file header: the header
    names a *path*, and the same path can hold different bytes on different
    days. CM4AI_crate_only.txt changed size by 31% between two crate-only
    conditions while keeping its name, so a path comparison would have called
    those runs replicates of each other.

    Returns None when the record is absent or its input hash was withheld as
    unrecoverable — in which case identity cannot be established and the caller
    must not assume a match.
    """
    from data_sheets_schema.provenance import record_path_for
    rec = record_path_for(project, method, label, concat_dir)
    if not rec.exists():
        return None
    try:
        data = yaml.safe_load(rec.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    return (data.get("inputs") or {}).get("bundle_md5")


def check_replicate(method: str, config: str, new_label: str, project: str,
                    concat_dir: Path = CONCAT_DIR) -> dict:
    """Verify a new replicate matches the procedure AND input of the existing.

    Call this when a replicate is *written*, not only when it is compared —
    catching a change at creation is what stops a revision being mislabelled as
    a replicate in the first place.

    Two runs are replicates only if BOTH their procedure fingerprint and their
    input bytes agree. Procedure alone is insufficient: an identical prompt over
    a changed bundle is a different condition.
    """
    new = record_path(method, new_label, project, concat_dir)
    if new is None:
        raise FileNotFoundError(f"no {project} record under {method}/{new_label}")
    new_fp = procedure_fingerprint(new)

    siblings = [r for r in discover(concat_dir)
                if r.method == method and r.config == config
                and r.label != new_label and r.replicate is not None]
    if not siblings:
        return {"status": "first", "fingerprint": new_fp, "compared_to": []}

    mismatches: list[dict] = []
    variance: list[dict] = []
    for s in siblings:
        p = record_path(method, s.label, project, concat_dir)
        if p is None:
            continue
        fp = procedure_fingerprint(p)
        # Only fields present in BOTH headers can evidence a procedure change.
        # A field emitted by one run and omitted by the other is header
        # formatting variance — agents word optional lines differently — and
        # must not be read as a changed pipeline.
        shared = set(fp) & set(new_fp)
        diff = {k: (fp[k], new_fp[k]) for k in shared if fp[k] != new_fp[k]}
        only_one = sorted((set(fp) ^ set(new_fp)))
        if diff:
            mismatches.append({"label": s.label, "differs": diff})
        elif only_one:
            variance.append({"label": s.label, "fields": only_one})
    if mismatches:
        raise ReplicateMismatch(
            f"{new_label} does not share the procedure of "
            f"{[m['label'] for m in mismatches]}: {mismatches[0]['differs']}. "
            "A changed pipeline is a revision, not a replicate — give it a new "
            "config label instead of a _rep index."
        )

    # Input identity. Unknown hashes are reported, never treated as agreement.
    new_input = input_fingerprint(method, new_label, project, concat_dir)
    input_unknown: list[str] = []
    for s in siblings:
        sib_input = input_fingerprint(method, s.label, project, concat_dir)
        if new_input is None or sib_input is None:
            input_unknown.append(s.label)
        elif sib_input != new_input:
            raise ReplicateMismatch(
                f"{new_label} consumed different input bytes from {s.label} "
                f"({new_input[:12]}… vs {sib_input[:12]}…). Same prompt over a "
                "changed bundle is a different condition, not a replicate — "
                "give it a new config label."
            )
    return {"status": "ok", "fingerprint": new_fp,
            "compared_to": [s.label for s in siblings],
            "header_variance": variance,
            "input_md5": new_input,
            "input_unverified_against": input_unknown or None}


def condition_of(method: str, label: str, project: str,
                 concat_dir: Path = CONCAT_DIR) -> str | None:
    """The prompt condition a run recorded, read from its provenance prompts."""
    import yaml as _yaml
    from data_sheets_schema.provenance import record_path_for
    p = record_path_for(project, method, label, concat_dir)
    if not p.exists():
        return None
    data = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    paths = ((data.get("prompts") or {}).get("files")
             or (data.get("prompts") or {}).get("paths") or [])
    joined = " ".join(str(x) for x in paths)
    if "d4d_generic_arm_prompt_v2.md" in joined:
        return "generic_v2"
    if "d4d_tuned_arm_prompt.md" in joined:
        return "tuned"
    if "d4d_generic_arm_prompt.md" in joined:
        return "generic"
    return None


def arm_delta(baseline_method: str, arm_method: str, project: str,
              config: str, replicates: list[str],
              concat_dir: Path = CONCAT_DIR,
              require_live: bool = False) -> dict:
    """Paired per-replicate delta between two arms, completeness-gated.

    Use this rather than reading record paths directly. Ad-hoc analysis that
    globs the filesystem will happily read a run whose phases 3-4 are still
    executing; twice during the 2026-07-27 series that produced a wrong number
    (a spurious +12 and a spurious -14). The gate belongs in the analysis path,
    not only in the CLI.
    """
    def _ok(method: str, r: str) -> bool:
        label = f"{config}_{r}"
        if not is_complete(method, label, project, concat_dir):
            return False
        # A delta between a valid record and a broken one measures the breakage,
        # not the arm. Excluded here for the same reason incomplete runs are.
        if validation_status(method, label, project, concat_dir) == INVALID:
            return False
        # See compare(): off by default, because on this corpus a hard gate
        # removes the tuned arm and every non-Claude model. Reported either way.
        return not require_live or record_mode(
            method, label, project, concat_dir) == "live"

    usable = [r for r in replicates
              if _ok(baseline_method, r) and _ok(arm_method, r)]
    skipped = [r for r in replicates if r not in usable]
    not_live = [
        r for r in replicates
        if "live" not in {
            record_mode(baseline_method, f"{config}_{r}", project, concat_dir),
            record_mode(arm_method, f"{config}_{r}", project, concat_dir)}]
    unverified = [
        r for r in usable
        if {UNVERIFIED, STALE} & {
            validation_status(baseline_method, f"{config}_{r}", project, concat_dir),
            validation_status(arm_method, f"{config}_{r}", project, concat_dir)}]

    deltas, base_sets, arm_sets = {}, [], []
    for r in usable:
        label = f"{config}_{r}"
        b = slots(record_path(baseline_method, label, project, concat_dir))
        a = slots(record_path(arm_method, label, project, concat_dir))
        deltas[r] = len(a) - len(b)
        base_sets.append(b)
        arm_sets.append(a)

    noise = None
    if len(usable) >= 2:
        # Noise across ALL replicates, not just the first two. A slot counts as
        # varying if it is absent from any run, so this grows with replicate
        # count — the pairwise figure understates it and the two must never be
        # compared with each other.
        def spread(sets):
            return len(set.union(*sets) - set.intersection(*sets))
        noise = max(spread(base_sets), spread(arm_sets))

    verdict = "insufficient replicates"
    if noise is not None and deltas:
        smallest = min(deltas.values())
        verdict = ("real" if smallest > noise
                   else "marginal" if smallest > noise / 2
                   else "not resolvable")

    return {"project": project, "deltas": deltas, "noise": noise,
            "reconstructed": not_live, "all_live": not not_live,
            "verdict": verdict, "skipped_incomplete": skipped,
            "unverified": unverified,
            "all_verified": not unverified}


def needs_replicate_label(runs: list[Run]) -> list[Run]:
    """Model-based runs whose label lacks an r{N} suffix."""
    return [r for r in runs if not r.deterministic and r.replicate is None]


# Archive rather than delete. A run whose provenance was reconstructed is not
# worthless — it is a real generation whose conditions were recovered after the
# fact — so removing it from analysis must not destroy it. ATTIC is the existing
# convention for superseded data (see data/ATTIC/README.md).
ATTIC = Path("data/ATTIC")


def archive_runs(labels: list[str], *, reason: str,
                 concat_dir: Path = CONCAT_DIR,
                 attic: Path = ATTIC,
                 archive_name: str = "d4d_concatenated_archived",
                 dry_run: bool = True,
                 allow_partial_labels: bool = False) -> dict:
    """Move whole run directories out of discovery, preserving their layout.

    `discover()` walks `concat_dir`, so a move to ATTIC removes a run from every
    analysis without any code needing to know about it — archival and exclusion
    are the same operation.

    The relative path under `concat_dir` is preserved exactly beneath the archive
    directory, so restoring is the same move reversed rather than a
    reconstruction. Both the `{method}` and `{method}_core` directories for a
    label travel together: separating a full record from its core and
    reconciliation report would leave a run that `is_complete()` reports as
    unfinished forever.
    """
    # A label is not a unit of attestation. One run directory holds several
    # projects, and they can differ: 2026-07-28_claude-opus-5-crateonly has
    # CHORUS and VOICE live while CM4AI is partial. Archiving by label would
    # move six live records out with three unplaceable ones and report success.
    collateral: dict[str, list[str]] = {}
    for label in labels:
        keep = [f"{m}/{label}/{proj}"
                for run in discover(concat_dir) if run.label == label
                and not run.is_core and not run.deterministic
                for m in [run.method]
                for proj in run.projects
                if attestation(run.method, label, proj, concat_dir)
                in (LIVE, ATTESTED)]
        if keep:
            collateral[label] = keep
    if collateral and not allow_partial_labels:
        detail = "; ".join(f"{lab} would also move {len(v)} placeable record(s)"
                           for lab, v in sorted(collateral.items()))
        raise ValueError(
            "refusing to archive labels whose projects do not agree: " + detail
            + ". A label is not a unit of attestation — archiving it moves every "
              "project it holds. Archive the unplaceable projects on their own, "
              "or pass allow_partial_labels=True to accept the collateral.")

    moved: list[tuple[Path, Path]] = []
    for method_dir in sorted(p for p in concat_dir.iterdir() if p.is_dir()):
        for label_dir in sorted(p for p in method_dir.iterdir() if p.is_dir()):
            if label_dir.name not in labels:
                continue
            dest = attic / archive_name / method_dir.name / label_dir.name
            moved.append((label_dir, dest))

    # Same hazard in the other direction: archiving a label twice would nest the
    # second copy inside the first.
    collisions = [str(d) for _, d in moved if d.exists()]
    if collisions and not dry_run:
        raise FileExistsError(
            "refusing to archive over existing archive directories: "
            + ", ".join(collisions))

    if not dry_run:
        for src, dest in moved:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
        _write_archive_note(attic / archive_name, moved, reason)

    return {"archive": str(attic / archive_name),
            "count": len(moved),
            "collisions": collisions,
            "moved": [(str(a), str(b)) for a, b in moved],
            "dry_run": dry_run}


def restore_runs(labels: list[str], *,
                 concat_dir: Path = CONCAT_DIR,
                 attic: Path = ATTIC,
                 archive_name: str = "d4d_concatenated_archived",
                 dry_run: bool = True) -> dict:
    """Move archived runs back into discovery — the exact inverse of archiving."""
    root = attic / archive_name
    moved: list[tuple[Path, Path]] = []
    if root.exists():
        for method_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            for label_dir in sorted(p for p in method_dir.iterdir() if p.is_dir()):
                if labels and label_dir.name not in labels:
                    continue
                moved.append((label_dir,
                              concat_dir / method_dir.name / label_dir.name))
    # shutil.move puts the source *inside* an existing destination rather than
    # failing, which would nest an archived run under a regenerated one of the
    # same name (`m/L/L/`) and hide it from discover() while reporting success.
    collisions = [str(d) for _, d in moved if d.exists()]
    if collisions and not dry_run:
        raise FileExistsError(
            "refusing to restore over existing run directories: "
            + ", ".join(collisions)
            + ". Move or remove them first; restoring into them would nest one "
              "run inside another and hide it from discovery.")

    if not dry_run:
        for src, dest in moved:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
    return {"count": len(moved),
            "moved": [(str(a), str(b)) for a, b in moved],
            "collisions": collisions,
            "dry_run": dry_run}


def _write_archive_note(root: Path, moved: list[tuple[Path, Path]],
                        reason: str) -> None:
    """Say why these runs were archived, at the place they were archived to.

    Without it an ATTIC directory is indistinguishable from abandoned output,
    and the reason for archiving — which is a claim about the runs — is exactly
    what a later reader needs and cannot reconstruct.
    """
    lines = [f"# Archived runs\n", f"\n{reason}\n",
             "\nThese are real generations, moved out of `data/d4d_concatenated/`",
             "\nso `discover()` no longer finds them. Nothing was deleted, and the",
             "\nlayout is preserved, so restoring is the same move reversed:\n",
             "\n```bash\nd4d runs restore --label <LABEL> --execute\n```\n",
             f"\n## Contents ({len(moved)} run directories)\n\n"]
    for _, dest in sorted(moved, key=lambda t: str(t[1])):
        lines.append(f"- `{dest.parent.name}/{dest.name}`\n")
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("".join(lines), encoding="utf-8")
