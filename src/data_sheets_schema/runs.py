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
    except Exception:                                        # noqa: BLE001
        return UNVERIFIED
    # A record that parses but is not a mapping is as unusable as one that does
    # not parse, and treating it as usable crashed here with a bare
    # AttributeError from `.get` (#311).
    if not isinstance(data, dict):
        return UNVERIFIED
    v = data.get("validation")
    if not isinstance(v, dict) or "passed" not in v:
        return UNVERIFIED

    # A verdict is about specific bytes. Re-hash the artifacts it was reached
    # on: if a record was edited since, the recorded `passed` is a claim about
    # a file that no longer exists in that form. STALE rather than UNVERIFIED
    # because the diagnosis differs — "validated, then changed" is a different
    # problem from "never checked" — and both mean do not rely on it.
    from data_sheets_schema.provenance import verify_entry
    artifacts = v.get("artifacts")
    if isinstance(artifacts, dict) and artifacts:
        for entry in artifacts.values():
            if not isinstance(entry, dict):
                continue
            # Verified with whichever algorithm the record carries. Records
            # predating the sha256 unification hold md5, and refusing to read it
            # would turn every historical verdict unverifiable — the opposite of
            # what binding them to a hash was for.
            ok = verify_entry(entry)
            if ok is False:
                return STALE

    return VALID if v["passed"] else INVALID


class AmbiguousCanonical(RuntimeError):
    """A project carries a canonical mark under more than one configuration."""


def canonical_runs(concat_dir: Path | None = None,
                   config: str | None = None) -> dict[str, dict]:
    """project -> the run marked canonical for it, and where its records are.

    `d4d runs select` writes a `canonical` block and nothing read it (#306). A
    mark with no reader answers "which record *is* the CHORUS datasheet" only
    for someone who already knows to go looking in provenance, which is not an
    answer a pipeline can use — and #287's scoping needs to *enumerate* the
    canonical set before it can be evaluated.

    A project with no eligible replicate is simply absent. VOICE is the live
    case: no replicate validates (#292), so it has no canonical record and any
    count over projects is three of four, not four.
    """
    # Resolved at call time, not bound as a default. A default argument freezes
    # CONCAT_DIR at import, which makes the corpus root unpatchable and the
    # function untestable against a fixture.
    concat_dir = Path(concat_dir) if concat_dir is not None else CONCAT_DIR
    out: dict[str, dict] = {}
    seen: dict[str, list[str]] = {}
    for prov in sorted(concat_dir.rglob("*_provenance.yaml")):
        try:
            data = yaml.safe_load(prov.read_text(encoding="utf-8")) or {}
        except (yaml.YAMLError, OSError, UnicodeDecodeError):
            continue
        if not isinstance(data, dict) or "canonical" not in data:
            continue
        run = data.get("run") or {}
        project, label = run.get("project"), run.get("label")
        if not project or not label:
            continue
        if config and not label.startswith(config):
            continue
        outputs = data.get("outputs") or {}
        seen.setdefault(project, []).append(label)
        out[project] = {
            "project": project,
            "label": label,
            "method": run.get("method"),
            "criterion": (data["canonical"] or {}).get("criterion"),
            "candidates": len((data["canonical"] or {}).get("selected_from") or []),
            "full": (outputs.get("full") or {}).get("path"),
            "core": (outputs.get("core") or {}).get("path"),
            "provenance": str(prov),
        }
    # Refuse rather than pick. `select --execute` does not clear a previous
    # mark, so re-selecting under a new config leaves a project with two — and
    # the dict build above would keep whichever label sorted last, which is a
    # property of the string rather than of anything meaningful (#308).
    ambiguous = {p: labels for p, labels in seen.items() if len(labels) > 1}
    if ambiguous:
        detail = "; ".join(f"{p}: {', '.join(sorted(labels))}"
                           for p, labels in sorted(ambiguous.items()))
        raise AmbiguousCanonical(
            f"more than one canonical record per project ({detail}). "
            "Pass config= to say which configuration you mean.")
    return dict(sorted(out.items()))


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
# Either hash satisfies these: a record written before the sha256 unification
# pins its inputs just as firmly as one written after.
ATTESTING_FIELDS = (("inputs.bundle_sha256", "inputs.bundle_md5"),
                    ("schema.full_sha256", "schema.full_md5"),
                    ("model.model",))

# Recognised `hash_basis` values, matched exactly. A substring test cannot be
# used here: `"verified" in "unverified"` is True, and so is `"verified" in
# "not verified against the run"` — the two phrasings most likely to describe an
# *unverified* hash would both promote the record. `UNVERIFIED` is already part
# of this module's vocabulary, so that is a phrasing waiting to be written.
VERIFIED_HASH_BASES = frozenset({
    "verified identical to the bytes consumed",
})

LIVE, ATTESTED, PARTIAL, NO_RECORD = "live", "attested", "partial", "none"
# A derived record is not a generation, so it cannot be graded as one. It has no
# model, no prompt and no input bundle *by design* — they are marked
# `not_applicable` — and grading it against ATTESTING_FIELDS reports a correctly
# formed derived record as a defective generation. What makes it placeable is
# different: its sources pinned by md5, the rule that combined them, and its own
# output hashed.
DERIVED = "derived"
DERIVED_FIELDS = ("sources", "derivation")


# From this date a run is required to write its own provenance. Dated rather
# than applied to the whole corpus on purpose: 59 existing records were
# reconstructed after the fact, and 33 of those are fully attested — the
# 2026-07-27 tuned arm pins its bundle, schema, model and outputs, and lacks only
# the hardware. Failing them retroactively would discard placeable evidence to
# enforce a rule that did not exist when they ran. The requirement is about
# stopping the ratio worsening, so it applies going forward.
LIVE_REQUIRED_FROM = "2026-07-30"

# A label dated before the project existed is not a date, it is a malformed
# label. Without a floor, `0001-01-01_x` or a mistyped `2016-07-30` exempts a run
# from the requirement — an exemption anyone can take by writing one. The
# unparseable case was already handled; this closes the parseable-nonsense case.
EARLIEST_PLAUSIBLE_RUN = "2024-01-01"


def requires_live(label: str) -> bool:
    """Whether this run is subject to the live-provenance requirement.

    Read from the label's date prefix, which every run label carries by
    convention (`{YYYY-MM-DD}_{provider-model-settings}`). A label with no
    parseable date is treated as subject to the rule: a run that cannot say when
    it happened is a new run for this purpose, and the alternative — exempting
    anything unparseable — is an exemption anyone could take by accident.
    """
    m = re.match(r"(\d{4}-\d{2}-\d{2})", label or "")
    if not m:
        return True
    dated = m.group(1)
    if dated < EARLIEST_PLAUSIBLE_RUN:
        return True          # malformed, not old
    return dated >= LIVE_REQUIRED_FROM


def check_provenance(method: str, label: str, project: str,
                     concat_dir: Path = CONCAT_DIR,
                     record: Path | None = None) -> dict:
    """Whether a run satisfies the live-provenance requirement.

    Separate from `is_complete()` deliberately. Folding this into completeness
    would reclassify every pre-cutoff run in one step and change every
    downstream count as a side effect of adding a rule.
    """
    # A caller that just wrote the record passes its path. Re-deriving it has
    # now been wrong twice — once for the assistant's flat layout, once outside
    # the repository root — and the writer always knows where it wrote.
    if record is not None:
        # Unparseable is "no usable record", not an exception. This is called at
        # the end of `execute()`, after all six phases are billed, so a record
        # truncated by a full disk or an interrupted write used to turn a
        # completed run into a traceback — when the gate's whole job is to turn
        # "cannot be attested" into a clean failure carrying a reason.
        data = {}
        unreadable = None
        if record.exists():
            try:
                data = yaml.safe_load(record.read_text(encoding="utf-8")) or {}
            except (yaml.YAMLError, OSError, UnicodeDecodeError) as exc:
                unreadable = f"{type(exc).__name__}: {str(exc).splitlines()[0][:90]}"
            if not isinstance(data, dict):
                unreadable = unreadable or (
                    f"expected a mapping, found {type(data).__name__}")
                data = {}
        if unreadable:
            return {"method": method, "label": label, "project": project,
                    "record_mode": "none", "attestation": NO_RECORD,
                    "drifted": [], "unverifiable": ["(unreadable record)"],
                    "required": requires_live(label), "ok": False,
                    "reason": (f"provenance record at {record} could not be read "
                               f"({unreadable}). A run whose record cannot be "
                               "parsed cannot state the conditions it ran under.")}
        # Knowing where the record is does not establish that it is *this*
        # run's record. Without this check a valid live record for some other
        # run satisfies the gate, and the artifact hashes verify — against that
        # other run's files. The result is a false attribution that every
        # downstream count inherits.
        identity = data.get("run") or {}
        wanted = {"method": method, "label": label, "project": project}
        mismatch = {k: (identity.get(k), v) for k, v in wanted.items()
                    if identity.get(k) != v}
        if data and mismatch:
            # `unverifiable` answers "which artifacts could not be checked", so
            # run-identity field names do not belong in it — anything counting
            # unverifiable artifacts would silently include them. The mismatch
            # gets its own key, and the reason states it in full.
            return {**wanted, "record_mode": str(data.get("record_mode") or "none"),
                    "attestation": NO_RECORD, "drifted": [],
                    "unverifiable": [], "identity_mismatch": sorted(mismatch),
                    "required": requires_live(label),
                    "ok": False,
                    "reason": (
                        "provenance record does not identify which run it "
                        "describes (no `run` block), so it cannot be attributed "
                        "to this one." if not identity else
                        "provenance record describes a different run: "
                        + "; ".join(f"{k} is {got!r}, expected {exp!r}"
                                    for k, (got, exp) in sorted(mismatch.items())))}
        mode = str(data.get("record_mode") or "none")
        level = LIVE if mode == "live" else NO_RECORD if not data else PARTIAL
        artifacts = ((data.get("validation") or {}).get("artifacts") or {})
    else:
        mode = record_mode(method, label, project, concat_dir)
        level = attestation(method, label, project, concat_dir)
        artifacts = (((_prov(method, label, project, concat_dir) or {})
                      .get("validation") or {}).get("artifacts") or {})
    required = requires_live(label)

    # Re-verify, do not merely note the presence of a hash. The agent path
    # records provenance as a step separate from writing the artifacts, so a
    # hash can describe a state the file passed through — one reconciliation
    # report was pinned before its closing rows were appended. The API path
    # cannot do this, because it writes provenance in-process after all phases.
    # Checking at the end of a run gives the agent path the same property.
    drifted = [k for k, e in artifacts.items()
               if isinstance(e, dict) and _verify(e) is False]
    # Three outcomes, not two. `verify_entry` returns None when a file is absent
    # — unknowable is not mismatched, and conflating them would report a moved
    # file as tampering. But treating unknowable as *fine* inverts the gate: it
    # gave its strongest assurance exactly where there was least to go on, so a
    # run with no validation block, or whose artifacts were deleted, passed.
    unverifiable = [k for k, e in artifacts.items()
                    if isinstance(e, dict) and _verify(e) is None]
    # No exemption for a caller-supplied path. The reasoning for one was that a
    # record written moments ago has no validation block yet — but `execute()`
    # writes its validation block before it calls this, so the exemption bought
    # nothing and cost the gate its point: a file containing the single line
    # `record_mode: live` passed, which is the absence-of-evidence pass the
    # `unverifiable` branch exists to stop.
    if not artifacts:
        unverifiable = ["(no validation block)"]

    ok = (((not required) or mode == "live")
          and not drifted and not unverifiable)
    # Ordered by how fundamental the condition is, because the remedies differ.
    # A record that does not exist is not the same as one with nothing to
    # verify: the first needs a record written, the second needs it validated.
    if mode == "none":
        reason = ("no provenance record. The run cannot state the conditions it "
                  "ran under, and nobody can reconstruct them later with "
                  "certainty.")
    elif unverifiable and not drifted:
        reason = (f"nothing to verify: {', '.join(unverifiable)}. A run that "
                  "cannot be checked is not a run that passed — record "
                  "validation with `d4d runs validate`.")
    elif drifted:
        reason = (f"artifacts changed after provenance was recorded: "
                  f"{', '.join(drifted)}. The record pins bytes the files no "
                  "longer have — re-run `d4d runs validate` so the record "
                  "describes what actually shipped.")
    elif ok:
        reason = ("live provenance present" if mode == "live"
                  else f"predates {LIVE_REQUIRED_FROM}; not required")
    else:
        reason = (f"provenance is {mode}, not live. It was assembled after the "
                  "fact, so it reports what could be recovered rather than what "
                  "was observed.")
    return {"method": method, "label": label, "project": project,
            "record_mode": mode, "attestation": level, "drifted": drifted,
            "unverifiable": unverifiable,
            "required": required, "ok": ok, "reason": reason}


def _prov(method: str, label: str, project: str,
          concat_dir: Path = CONCAT_DIR) -> dict | None:
    import yaml as _yaml
    from data_sheets_schema.provenance import record_path_for
    p = record_path_for(project, method, label, concat_dir)
    if not p.exists():
        return None
    try:
        data = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (_yaml.YAMLError, OSError, UnicodeDecodeError):
        return None
    # The annotation said `dict | None` and the code returned whatever YAML
    # parsed, so a list-shaped record reached callers that call `.get` on it and
    # crashed with a bare AttributeError pointing at this module rather than at
    # the file (#311). `check_provenance` already treats a non-mapping as "no
    # usable record"; this is the same read without the same care.
    return data if isinstance(data, dict) else None


def _verify(entry: dict) -> bool | None:
    from data_sheets_schema.provenance import verify_entry
    return verify_entry(entry)


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

    if data.get("record_mode") == "derived":
        if not all(data.get(f) for f in DERIVED_FIELDS):
            return PARTIAL
        outputs = data.get("outputs") or {}
        if not any(isinstance(a, dict) and (a.get("sha256") or a.get("md5"))
                   for a in outputs.values() if a):
            return PARTIAL
        return DERIVED

    def _get(dotted: str) -> Any:
        node: Any = data
        for part in dotted.split("."):
            node = (node or {}).get(part) if isinstance(node, dict) else None
        return node

    for alternatives in ATTESTING_FIELDS:
        if not any(_get(d) for d in alternatives):
            return PARTIAL

    # The pinning artifact hash lives in `validation.artifacts`, not `outputs`.
    # `outputs` used to carry one, recorded before the artifacts were final, and
    # 77 live records pinned a state their files merely passed through. Hashing
    # moved to after the run; `outputs` now describes rather than asserts, so a
    # record is attested when *something* pins its artifacts, wherever that is.
    pinned = data.get("outputs") or {}
    validated = ((data.get("validation") or {}).get("artifacts") or {})
    if not any(isinstance(a, dict) and (a.get("sha256") or a.get("md5"))
               for a in list(pinned.values()) + list(validated.values()) if a):
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
    derived: list[str] = []
    for label in labels:
        # Derived first, *before* completeness. A merged record has no core and
        # no reconciliation report — it is a union of full records, not a
        # generation run, so it has neither by construction. Testing
        # completeness first bucketed it as "still running / incomplete", which
        # sent the reader looking for a run that will never arrive and made the
        # exclusion an accident of its artifact set rather than a property of
        # what it is.
        level = attestation(method, label, project, concat_dir)
        # The playbook's fifth carve-out condition, enforced rather than stated:
        # a derived record is an order statistic over the runs being measured, so
        # including it in an agreement figure would bias the very variance it was
        # built from. Excluded unconditionally — there is no flag for this,
        # because there is no analysis for which it is correct.
        if level == DERIVED:
            derived.append(label)
            continue
        if not is_complete(method, label, project, concat_dir):
            incomplete.append(label)
            continue
        modes[label] = record_mode(method, label, project, concat_dir)
        levels[label] = level
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
        "excluded_derived": derived,
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


def verify_request(method: str, label: str, project: str,
                   concat_dir: Path = CONCAT_DIR) -> tuple[str, str | None]:
    """Does the instruction a run recorded match what its spec renders?

    The gate the whole prompt-provenance thread is for. Rendering the
    instruction (#425) made hand-editing avoidable; this makes it *detectable*,
    which is the difference between a convention and a control.

    Four outcomes, and the two negative ones are deliberately distinct:

    - ``match``       — re-rendering the recorded spec reproduces the recorded
      hash. The run received what its spec says it should have.
    - ``mismatch``    — it does not. Something was edited between rendering and
      sending, or the prompt file has changed since. Either way the record's
      condition label no longer describes what was sent.
    - ``unverifiable`` — the record has a request hash but no spec, or the spec
      is incomplete. Common for records written before the spec was stored.
    - ``absent``      — no request hash at all. Every record written before
      #425, which is all of them.

    `absent` is not `mismatch`. Failing history for a field that postdates it is
    the same error the live-provenance cutoff exists to avoid.
    """
    import yaml as _yaml
    from data_sheets_schema.provenance import record_path_for

    p = record_path_for(project, method, label, concat_dir)
    if not p.exists():
        return "absent", "no provenance record"
    data = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    req = ((data.get("prompts") or {}).get("request")) or {}
    if not req.get("sha256"):
        return "absent", None
    spec_d = req.get("spec")
    if not isinstance(spec_d, dict) or not spec_d.get("condition"):
        return "unverifiable", "request hash recorded without the spec that produced it"

    try:
        import hashlib
        from data_sheets_schema.api_runner import RunSpec, resolve_prompt
        spec = RunSpec(
            project=project, arm=spec_d.get("arm", ""), method=method,
            bundle=Path(spec_d.get("bundle", "")), label=label,
            condition=spec_d["condition"],
            manifest_line=spec_d.get("manifest_line", ""),
            run_date=spec_d.get("run_date", ""),
            runtime=spec_d.get("runtime", ""),
            provider=spec_d.get("provider"))
        got = hashlib.sha256(resolve_prompt(spec).encode("utf-8")).hexdigest()
    except Exception as exc:                                 # noqa: BLE001
        return "unverifiable", f"could not re-render: {exc}"

    if got == req["sha256"]:
        return "match", None
    return "mismatch", (f"recorded {req['sha256'][:12]}… but the spec renders "
                        f"{got[:12]}…; the instruction sent was not the one "
                        "this spec produces")


def condition_from_label(label: str) -> str | None:
    """The prompt condition a label *claims*, or None if it names none.

    Labels spell it with hyphens — `..._claudecode-generic-v3_rep2` — while
    `CONDITION_PROMPTS` keys use underscores, so the two are compared in one
    spelling. Derived from the registry rather than a hardcoded chain, for the
    reason `condition_of` records: a written-out list knew only v1, v2 and
    tuned, and every v3 and v4 run fell through it silently (#340).
    """
    from data_sheets_schema.api_runner import CONDITION_PROMPTS

    hay = label.replace("_", "-").lower()
    # Longest first: `generic` is a prefix of `generic-v3`, so a shortest-first
    # scan would answer `generic` for every versioned label — which is exactly
    # the mismatch this function exists to detect, reported as agreement.
    for cond in sorted(CONDITION_PROMPTS, key=len, reverse=True):
        if cond.replace("_", "-") in hay:
            return cond
    return None


def prompt_condition_mismatch(method: str, label: str, project: str,
                              concat_dir: Path = CONCAT_DIR) -> str | None:
    """Whether a run's label and its hashed prompt name the same condition.

    The 2026-08-07 sweep is labelled `generic-v3` and hashes
    `d4d_generic_arm_prompt.md`, which is v1 (#420). v3 adds seven decision
    rules over v1, so the two are different conditions and the label is the
    only place the v3 claim exists — an assertion by whoever typed it.

    Returns a description when they disagree, None when they agree or when
    either cannot be determined. Silence on "cannot determine" is deliberate:
    labels predating the convention name no condition, and failing them would
    punish records for a rule that postdates them.
    """
    claimed = condition_from_label(label)
    recorded = condition_of(method, label, project, concat_dir)
    if not claimed or not recorded or claimed == recorded:
        return None
    from data_sheets_schema.api_runner import CONDITION_PROMPTS
    return (f"label claims {claimed!r} but the hashed prompt is "
            f"{recorded!r} ({CONDITION_PROMPTS[recorded].name}); "
            "the two are different conditions")


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
    # Entries are mappings — `{"path": ..., "sha256": ...}` — not bare strings.
    # Stringifying the mapping happens to contain the path, which is why the
    # previous version worked, but it also drags every other value into the
    # match. Read the field.
    joined = " ".join(x.get("path", "") if isinstance(x, dict) else str(x)
                      for x in paths)

    # Derived from the registry rather than restated. A hardcoded chain knew
    # only v1, v2 and tuned, so every v3 and v4 run fell through it and returned
    # None — silently, and on the rerun path (#340). `cli/api.py` carries the
    # same lesson from when the condition list was written out three times and
    # left `generic_v2` unreachable.
    from data_sheets_schema.api_runner import CONDITION_PROMPTS, TUNED_PROMPT

    # `tuned` shares v1's generic file and is identified by its own block
    # appearing alongside, so it has to be tested before the generic bases.
    if TUNED_PROMPT.name in joined:
        return "tuned"

    # Longest filename first: `d4d_generic_arm_prompt.md` is not a substring of
    # `..._v2.md`, but ordering by length keeps that true if a future version is
    # ever named in a way that makes it one.
    for condition, path in sorted(CONDITION_PROMPTS.items(),
                                  key=lambda kv: -len(kv[1].name)):
        if condition == "tuned":
            continue
        if path.name in joined:
            return condition
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
                 projects: list[str] | None = None,
                 concat_dir: Path = CONCAT_DIR,
                 attic: Path = ATTIC,
                 archive_name: str = "d4d_concatenated_archived",
                 dry_run: bool = True,
                 allow_partial_labels: bool = False) -> dict:
    """Move runs out of discovery, preserving their layout.

    `discover()` walks `concat_dir`, so a move to ATTIC removes a run from every
    analysis without any code needing to know about it — archival and exclusion
    are the same operation.

    Operates on **files**, not directories, so whole-label and per-project
    archiving are the same code path. ``projects`` narrows the move to records
    whose filenames carry those project prefixes; without it every file under a
    matching label directory moves.

    Per-project archiving is what a mixed label needs.
    `2026-07-28_claude-opus-5-crateonly` holds CHORUS and VOICE *live* alongside
    CM4AI *partial*; archiving by label would move six placeable records out with
    three unplaceable ones. Naming the project moves only CM4AI's records and
    leaves the label otherwise intact.

    The relative path under `concat_dir` is preserved exactly beneath the archive
    directory, so restoring is the same move reversed rather than a
    reconstruction. When a whole label moves, its `{method}` and `{method}_core`
    directories travel together: separating a full record from its core and
    reconciliation report would leave a run `is_complete()` reports as unfinished
    forever.
    """
    wanted = set(projects or [])

    def _files_for(label_dir: Path) -> list[Path]:
        files = [f for f in sorted(label_dir.rglob("*")) if f.is_file()]
        if not wanted:
            return files
        return [f for f in files
                if any(f.name.startswith(f"{proj}_") for proj in wanted)]

    # A label is not a unit of attestation — one run directory holds several
    # projects and they can differ. Checked only when moving whole labels; naming
    # the projects is the precise alternative, so it needs no such guard.
    if not wanted:
        collateral: dict[str, list[str]] = {}
        for label in labels:
            keep = [f"{run.method}/{label}/{proj}"
                    for run in discover(concat_dir) if run.label == label
                    and not run.is_core and not run.deterministic
                    for proj in run.projects
                    if attestation(run.method, label, proj, concat_dir)
                    in (LIVE, ATTESTED)]
            if keep:
                collateral[label] = keep
        if collateral and not allow_partial_labels:
            detail = "; ".join(
                f"{lab} would also move {len(v)} placeable record(s)"
                for lab, v in sorted(collateral.items()))
            raise ValueError(
                "refusing to archive labels whose projects do not agree: "
                + detail + ". A label is not a unit of attestation — archiving "
                "it moves every project it holds. Pass projects=[...] to move "
                "only the unplaceable ones, or allow_partial_labels=True to "
                "accept the collateral.")

    moved: list[tuple[Path, Path]] = []
    for method_dir in sorted(p for p in concat_dir.iterdir() if p.is_dir()):
        for label_dir in sorted(p for p in method_dir.iterdir() if p.is_dir()):
            if label_dir.name not in labels:
                continue
            for f in _files_for(label_dir):
                rel = f.relative_to(concat_dir)
                moved.append((f, attic / archive_name / rel))

    collisions = [str(d) for _, d in moved if d.exists()]
    if collisions and not dry_run:
        raise FileExistsError(
            "refusing to archive over existing archive entries: "
            + ", ".join(collisions[:5]))

    # Reported in both modes, so a dry run previews the whole effect. Moving one
    # project out of a shared label leaves the directory; moving every project
    # removes it. Those are materially different outcomes and a preview that
    # showed only the file moves presented them identically.
    emptied = _would_empty(moved, concat_dir)

    if not dry_run and moved:
        for src, dest in moved:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
        _prune(emptied)
        _write_archive_note(attic / archive_name, moved, reason)

    return {"archive": str(attic / archive_name),
            "count": len(moved),
            "labels": sorted(labels),
            "projects": sorted(wanted) or None,
            "collisions": collisions,
            "would_empty": [str(d) for d in emptied],
            # An empty selection is reported rather than treated as success: a
            # mistyped project name otherwise archives nothing and leaves a note
            # claiming otherwise.
            "matched_nothing": not moved,
            "moved": [(str(a), str(b)) for a, b in moved],
            "dry_run": dry_run}


def restore_runs(labels: list[str], *,
                 projects: list[str] | None = None,
                 concat_dir: Path = CONCAT_DIR,
                 attic: Path = ATTIC,
                 archive_name: str = "d4d_concatenated_archived",
                 dry_run: bool = True) -> dict:
    """Move archived records back into discovery — the exact inverse of archiving."""
    root = attic / archive_name
    wanted = set(projects or [])
    moved: list[tuple[Path, Path]] = []
    if root.exists():
        for f in sorted(root.rglob("*")):
            if not f.is_file() or f.name == "README.md":
                continue
            rel = f.relative_to(root)
            label = rel.parts[1] if len(rel.parts) > 1 else ""
            if labels and label not in labels:
                continue
            if wanted and not any(f.name.startswith(f"{proj}_")
                                  for proj in wanted):
                continue
            moved.append((f, concat_dir / rel))

    # shutil.move puts a source *inside* an existing destination directory
    # rather than failing; for files it would overwrite. Either way a record
    # regenerated while its predecessor sat in ATTIC would be silently replaced
    # or hidden, with the command reporting success.
    collisions = [str(d) for _, d in moved if d.exists()]
    if collisions and not dry_run:
        raise FileExistsError(
            "refusing to restore over existing records: "
            + ", ".join(collisions[:5])
            + ". Move or remove them first; restoring would overwrite a record "
              "that was regenerated while this one was archived.")

    emptied = _would_empty(moved, root)
    if not dry_run and moved:
        for src, dest in moved:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
        _prune(emptied)
    return {"count": len(moved),
            "would_empty": [str(d) for d in emptied],
            "matched_nothing": not moved,
            "collisions": collisions,
            "moved": [(str(a), str(b)) for a, b in moved],
            "dry_run": dry_run}


def _would_empty(moved: list[tuple[Path, Path]], root: Path) -> list[Path]:
    """Directories the move would leave empty, deepest first.

    Scoped to the parents of the files that moved. Pruning the whole corpus root
    instead deleted empty directories the operation never touched — a directory
    someone created ahead of a run would vanish because an unrelated archive
    happened to run, and the resulting corpus depended on what else was empty at
    the time.
    """
    leaving: dict[Path, set[Path]] = {}
    for src, _ in moved:
        leaving.setdefault(src.parent, set()).add(src)

    doomed: list[Path] = []
    for d, going in leaving.items():
        cur = d
        while cur != root and root in cur.parents or cur == d:
            if not cur.exists():
                break
            remaining = [f for f in cur.rglob("*")
                         if f.is_file() and f not in going
                         and not any(str(f).startswith(str(x)) for x in doomed)]
            if remaining:
                break
            doomed.append(cur)
            cur = cur.parent
            if cur == root:
                break
    return sorted(set(doomed), key=lambda p: len(p.parts), reverse=True)


def _prune(dirs: list[Path]) -> None:
    """Remove the named directories, deepest first, if empty."""
    for d in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        if d.exists():
            try:
                next(d.iterdir())
            except StopIteration:
                d.rmdir()


_ARCHIVE_PREAMBLE = (
    "# Archived runs\n"
    "\nReal generations, moved out of `data/d4d_concatenated/` so `discover()`"
    "\nno longer finds them. Nothing was deleted, and the layout is preserved,"
    "\nso restoring is the same move reversed:\n"
    "\n```bash\nd4d runs restore --label <LABEL> --execute\n```\n"
    "\nOne section per archiving run, appended in order. The reason is a claim"
    "\nabout the runs it names and only about those, so the sections are kept"
    "\nseparate rather than merged into a running total.\n"
)


def _write_archive_note(root: Path, moved: list[tuple[Path, Path]],
                        reason: str) -> None:
    """Say why these runs were archived, at the place they were archived to.

    Without it an ATTIC directory is indistinguishable from abandoned output,
    and the reason for archiving — which is a claim about the runs — is exactly
    what a later reader needs and cannot reconstruct.

    Appends. This used to `write_text` the whole file, so every archiving run
    silently destroyed the record of the one before it: four invocations under
    #408 left a README describing only the fourth, and the rationale for the
    2026-04 and 2026-07-23 series — the thing the file exists to carry — was
    gone. A note that documents only the most recent write is worse than none,
    because it reads as complete.
    """
    from datetime import date

    dirs = sorted({dest.parent for _, dest in moved})
    heading = (f"{len(moved)} file(s) in {len(dirs)} run "
               f"director{'y' if len(dirs) == 1 else 'ies'}")
    section = [f"\n## Archived {date.today().isoformat()} — {heading}\n",
               f"\n{reason}\n\n"]
    for _, dest in sorted(moved, key=lambda t: str(t[1])):
        # Relative to the archive root, not just the last two segments: the
        # method directory is what distinguishes `claudecode_agent` from
        # `claudecode_agent_core`, and both hold the same label.
        try:
            shown = dest.relative_to(root)
        except ValueError:
            shown = Path(dest.parent.name) / dest.name
        section.append(f"- `{shown}`\n")

    root.mkdir(parents=True, exist_ok=True)
    path = root / "README.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if not existing.strip():
        existing = _ARCHIVE_PREAMBLE
    path.write_text(existing.rstrip("\n") + "\n" + "".join(section),
                    encoding="utf-8")
