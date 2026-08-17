"""Four-phase D4D generation over the Anthropic API.

Why this exists alongside the Claude Code path: the agent runtime is metered
against a subscription, and the API is cheaper to run at the scale this study
needs. But it is emphatically *not* the same procedure — `PROCEDURE_FIELDS`
includes `Agent runtime`, so `check_replicate()` will refuse to pool API runs
with Claude Code runs, which is correct. They are different methods, and the
generic prompt run under both is the control that measures the difference.

Three things this path does better than the agent path, all of which were
weaknesses the study hit:

- **The prompt is injected, not read.** A Claude Code agent is told to read a
  prompt file; nothing guarantees it uses the text verbatim. Here the resolved
  text is the request, and its hash goes in the provenance record.
- **Temperature is real.** Claude Code exposes no temperature setting, so every
  existing header's `Temperature: 0.0` is an assertion. Here it is a parameter.
- **Provenance cannot be skipped.** The orchestrator writes the record, not the
  model, so a run cannot finish without one.

Settings come from the GitHub assistant's deterministic config, so the two
paths cannot drift into different procedures claiming to be the same one.

Cost: the schema digest replaces the merged schema (254 KB -> 18 KB), and the
bundle plus digest form a cached prefix reused across all six phases.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from data_sheets_schema import reasoning, schema_digest
from data_sheets_schema.provenance import (
    DETERMINISTIC_CONFIG,
    load_generation_config,
    repo_relative,
)

PROMPTS = Path("src/download/prompts")
GENERIC_PROMPT = PROMPTS / "d4d_generic_arm_prompt.md"
# v2 is v1 plus three uniform decision rules correcting schema-usage failures
# that fitness scoring found in every project. A separate file rather than an
# edit: v1 produced the 2026-07-28 series and is the baseline v2 is measured
# against, so editing it in place would silently redefine that baseline.
GENERIC_PROMPT_V2 = PROMPTS / "d4d_generic_arm_prompt_v2.md"
# v3 is v2 plus one rule. v2's first rule stopped the model collapsing several
# entities into one object and left objects of the right cardinality whose
# declared fields are empty because the content sits in `description`
# (notes/form_defect_split_2026-08-03.md). A third file for the same reason v2
# was one: v2 produced the 2026-07-31 series and is the baseline v3 is measured
# against. The comparison that isolates the companion rule is v2 against v3.
GENERIC_PROMPT_V3 = PROMPTS / "d4d_generic_arm_prompt_v3.md"
# v4 carries the scalar-range companion to v3's class-range rule. It is a
# separate version rather than a second rule inside v3 because v3's value is
# isolating one change, and `notes/generic_v3_analysis_plan.md` was registered
# before any run naming that one rule (#338).
GENERIC_PROMPT_V4 = PROMPTS / "d4d_generic_arm_prompt_v4.md"
GENERIC_PROMPT_V5 = PROMPTS / "d4d_generic_arm_prompt_v5.md"
CONDITION_PROMPTS = {"generic": GENERIC_PROMPT,
                     "generic_v2": GENERIC_PROMPT_V2,
                     "generic_v3": GENERIC_PROMPT_V3,
                     "generic_v4": GENERIC_PROMPT_V4,
                     "generic_v5": GENERIC_PROMPT_V5,
                     "tuned": GENERIC_PROMPT}

# Which generic base each condition is built on. The generic/tuned comparison
# assumes both arms share a base and differ only in the project-specific block;
# once a second generic base exists that assumption stops holding silently.
# `tuned` is pinned to v1 because the 2026-07-27 tuned series was produced under
# it — so comparing `generic_v2` against `tuned` would measure the three added
# decision rules *and* the tuned block together while appearing to measure only
# tuning. Recorded here so the pairing is checkable rather than implied.
# Each condition on two axes: which generic base it is built on, and whether it
# carries project-specific tuning. A comparison is interpretable when the two
# conditions differ on *one* axis — that is the thing being measured.
CONDITION_AXES = {
    "generic":    {"base": "v1", "tuned": False},
    "generic_v2": {"base": "v2", "tuned": False},
    "generic_v3": {"base": "v3", "tuned": False},
    "generic_v4": {"base": "v4", "tuned": False},
    "generic_v5": {"base": "v5", "tuned": False},
    "tuned":      {"base": "v1", "tuned": True},
}


def condition_delta(a: str, b: str) -> list[str]:
    """Which axes two conditions differ on."""
    ax, bx = CONDITION_AXES.get(a), CONDITION_AXES.get(b)
    if ax is None or bx is None:
        return ["unknown condition"]
    return [k for k in ("base", "tuned") if ax[k] != bx[k]]


#: Bases whose step added several rules at once, and how many. Both were
#: deliberate change-sets registered before the run — v2's three, v5's four — so
#: comparing across them is legitimate; what is unavailable is attributing a
#: difference to one rule inside the set. Recorded so an analysis can say which
#: it is doing.
MULTI_RULE_BASES = {"v2": 3, "v5": 4}


def _base_step(base: str) -> int:
    """`v3` -> 3. Bases are an ordered series, each adding one rule."""
    try:
        return int(base.lstrip("v"))
    except ValueError:
        return -1


def comparable_conditions(a: str, b: str) -> bool:
    """True when a difference between the two *prompt conditions* is one step.

    **This answers a question about prompt text and nothing else.** Two arms can
    satisfy it and still be uncomparable, because a schema digest, a phase
    instruction or a runtime can change between them — none of which is visible
    in a condition name. `runs.arm_confounds` reads what the records state and
    is the check that governs interpretation; #576 exists because this function
    reported v4-against-v5 as isolating while the schema had moved underneath it
    (`622e6d03` to `44d29023`) and `reconcile_full` had gained an input.

    A True here also does not mean one *rule* changed: see `MULTI_RULE_BASES`,
    where v2's step is three rules and v5's is four.

    `generic` vs `generic_v2` differs only in base — that is the v2 experiment.
    `generic` vs `tuned` differs only in tuning — that is the study's main
    comparison. `generic_v2` vs `tuned` differs in **both**, so a difference
    between them measures the added decision rules and the tuned block together
    while appearing to measure only tuning.

    Differing on the base axis is not sufficient once there are more than two
    bases. Each version adds exactly one rule to the one before, so `v2` against
    `v4` spans **two** additions while `condition_delta` reports the single axis
    `base` — one axis, two changes. Adjacency is what makes the delta
    attributable, and v4's arrival is what made that distinction load-bearing
    (it was already latent for v1 against v3).
    """
    delta = condition_delta(a, b)
    if len(delta) != 1:
        return False
    if delta == ["base"]:
        steps = [_base_step(CONDITION_AXES[c]["base"]) for c in (a, b)]
        return -1 not in steps and abs(steps[0] - steps[1]) == 1
    return True


def confounded_note(a: str, b: str) -> str | None:
    """Why a comparison would confound two changes, when it would."""
    delta = condition_delta(a, b)
    if len(delta) <= 1:
        return None
    return (f"{a} and {b} differ on {' and '.join(delta)}. A difference between "
            "them cannot be attributed to either alone. Compare each condition "
            "against one that differs from it on a single axis — a tuned arm "
            "needs a tuned counterpart on the same generic base.")
TUNED_PROMPT = PROMPTS / "d4d_tuned_arm_prompt.md"
COMPONENTS = PROMPTS / "components"
CONCAT_DIR = Path("data/d4d_concatenated")

RUNTIME = "Claude API (direct)"
PROVIDER = "Anthropic"

# One artifact per call. An earlier design had a single `reconcile` phase return
# full + core + report in one JSON object; measured against 112 real records
# that demands 31k-68k output tokens in a single response, which is not a limit
# to raise but a shape to abandon. Splitting it also means every phase writes
# something, so a failure costs one call rather than the whole run.
PHASES = ("full", "core", "audit", "reconcile_full", "reconcile_core", "report")

# Derived from the largest artifact of each kind across 112 full, 104 core and
# 97 report records already generated, plus ~40% headroom. A guessed ceiling is
# how the previous design truncated five of six projects mid-YAML.
PHASE_MAX_TOKENS = {
    # 96000, not 64000. The v3 prompt roughly doubled full-phase thinking spend
    # (35.7k-48.7k tokens observed on AI-READI, vs 14.7k-29.3k under v1/v2),
    # and thinking and record share this budget — two of three 2026-08-05
    # AI-READI full attempts died at 64000 with the record truncated. The value
    # is clamped per route by `output_limit()`, so on a 64k route (the
    # `google/…` rebroadcasts) the request still asks for exactly 64000.
    "full": 96000, "reconcile_full": 96000, "repair_full": 96000,
    "core": 56000, "reconcile_core": 56000, "repair_core": 56000,
    # 24000, not 12000. The original was derived from records generated before
    # the v2 rules existed, and two AI-READI runs truncated mid-audit — a phase
    # that fails at its ceiling costs the whole run, since the phases before it
    # are already billed.
    # Report raised for the same reason as full: under v3 the report phase
    # spent 6.6k-6.8k tokens thinking and hit 12000 twice on 2026-08-05 before
    # a third sample fit at 10.5k. The ceiling was derived from pre-v2 records
    # and left no room for the thinking share.
    "audit": 24000, "report": 24000,
}
DEFAULT_MAX_TOKENS = 64000

# The API is called at least six times per run (one per phase, plus
# phase-level retries) over minutes; transient 429s and
# 5xx are expected rather than exceptional.
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 2


@dataclass
class RunSpec:
    project: str
    arm: str                 # display name for the header
    method: str              # output directory, e.g. claudecode_agent
    bundle: Path
    label: str
    condition: str = "generic"          # generic | tuned
    manifest_line: str = "# Source manifest: data/preprocessed/source_manifest.yaml"
    # Frozen when the run is specified, not read from the clock on each use.
    # A six-phase run takes tens of minutes and this study's sweep genuinely
    # ran past midnight UTC, so recomputing per call gave phases of one run
    # different `# Generated:` dates — and made the provenance digest, which is
    # computed after the last phase, attest a prompt that was never sent.
    run_date: str = field(
        default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    # The study writes into the run-labelled layout under data/d4d_concatenated.
    # The GitHub assistant writes flat into data/sheets_d4dassistant. Rather than
    # two runners, the layout is a parameter — everything else is identical.
    out_dir: Path | None = None
    # Which runtime the rendered instruction should declare. Defaults to this
    # module's own, so the API path is unchanged. It is a parameter because the
    # agentic path needs the same instruction rendered for `Claude Code`: the
    # whole point of rendering is that nobody types the header by hand, and a
    # hardcoded runtime would force exactly that (#419).
    runtime: str = RUNTIME
    # Likewise the provider. `provider_identity()` reports the endpoint *this
    # process* is configured against, which is the right answer for a run this
    # process is about to make and the wrong one for rendering an instruction
    # another runtime will execute — it rendered "LBL CBORG (proxy to
    # Anthropic)" into a Claude Code header, a provider that run never touches.
    provider: str | None = None

    def render_spec(self) -> dict[str, Any]:
        """Everything `resolve_prompt` reads, for the record to keep.

        A record that stores only the resolved hash can say the instruction
        changed but not what it should have been. Storing the spec beside it
        lets `verify_request()` re-render and compare, which is what turns
        "do not intervene" from a rule into something detectable (#420).
        """
        return {"condition": self.condition, "arm": self.arm,
                "manifest_line": self.manifest_line, "run_date": self.run_date,
                "runtime": self.runtime,
                "provider": self.provider or provider_identity()["provider"]
                or PROVIDER,
                "bundle": str(self.bundle)}

    @cached_property
    def instruction(self) -> str:
        """The resolved instruction, rendered once per spec.

        `resolve_prompt` was called at send time and again when the provenance
        record was built after the last phase. It reads `provider_identity()`
        and `_model_settings()`, so anything that moved in between — an edited
        deterministic config, a changed endpoint — would have the record attest
        a prompt that was never sent.

        That is the same failure `run_date` is frozen to avoid, and the comment
        there says so: recomputing per call "made the provenance digest, which
        is computed after the last phase, attest a prompt that was never sent".
        A six-phase run takes tens of minutes, which is long enough for it to
        happen. Resolving once closes it for the whole spec rather than for one
        field of it.
        """
        return resolve_prompt(self)

    @property
    def full_path(self) -> Path:
        if self.out_dir:
            return self.out_dir / f"{self.project}_d4d.yaml"
        return CONCAT_DIR / self.method / self.label / f"{self.project}_d4d.yaml"

    @property
    def core_path(self) -> Path:
        if self.out_dir:
            return self.out_dir / f"{self.project}_d4d_core.yaml"
        return (CONCAT_DIR / f"{self.method}_core" / self.label /
                f"{self.project}_d4d_core.yaml")

    @property
    def report_path(self) -> Path:
        if self.out_dir:
            return self.out_dir / f"{self.project}_reconciliation.md"
        return (CONCAT_DIR / f"{self.method}_core" / self.label /
                f"{self.project}_reconciliation.md")

    @property
    def metadata_dir(self) -> Path:
        """Where a run's *metadata* lives — provenance and resume state.

        One rule for both layouts, alongside the reconciliation report. This
        used to be three rules: provenance named `_provenance.yaml` in the study
        layout but `_d4d_metadata.yaml` in the assistant layout, and the
        progress file landing beside the *full* record while provenance landed
        in the `_core` directory. Reading a run's state then meant knowing which
        of three conventions applied.
        """
        return self.out_dir or self.report_path.parent

    @property
    def provenance_path(self) -> Path:
        return self.metadata_dir / f"{self.project}_provenance.yaml"

    @property
    def base_prompt(self) -> Path:
        try:
            return CONDITION_PROMPTS[self.condition]
        except KeyError:
            raise ValueError(
                f"unknown prompt condition {self.condition!r}; expected one of "
                f"{sorted(CONDITION_PROMPTS)}. A run under an unrecognised "
                "condition cannot be placed in the study.") from None

    @property
    def prompt_files(self) -> list[Path]:
        files = [self.base_prompt]
        if self.condition == "tuned":
            files += [TUNED_PROMPT, COMPONENTS / f"{self.project}.md"]
        return files


def prompt_body(path: Path = GENERIC_PROMPT) -> str:
    text = path.read_text(encoding="utf-8")
    if "## Prompt body" not in text:
        raise ValueError(f"{path} has no '## Prompt body' section")
    return text.split("## Prompt body", 1)[1].strip()


# Updated by hand when build_phase() reorders its parts; the instruction texts
# are hashed mechanically below, so wording changes cannot go unrecorded, but
# nothing derives this ordering from the code — keep it true.
ASSEMBLY_LAYOUT = ("schema digest, input bundle, arm prompt, "
                   "carried artifacts, phase instruction")


def assembly_digest() -> dict[str, Any]:
    """Fingerprint of how requests are assembled, for provenance (#353).

    The prompt-file and resolved-text hashes witness the arm prompt only. #352
    moved the phase instruction after the carried artifacts and reworded two
    instructions — a change that materially altered every request — yet a
    record made the day before and the day after carried byte-identical prompt
    evidence. This digest covers what those hashes do not: the phase
    instruction texts and the order the parts are assembled in.
    """
    basis = json.dumps([ASSEMBLY_LAYOUT, PHASE_INSTRUCTIONS], sort_keys=True)
    return {"sha256": hashlib.sha256(basis.encode("utf-8")).hexdigest(),
            "layout": ASSEMBLY_LAYOUT}


def resolved_prompt_digest(spec: RunSpec) -> dict[str, Any]:
    """A hash of the text the model is actually sent.

    The module docstring claimed the resolved text's hash goes into provenance.
    It did not: only the *file* was hashed, so two runs whose requests differed
    in project, arm, label, model, provider or date were indistinguishable by
    their recorded prompt evidence. Substitution is exactly what makes the file
    and the request different objects, so the request needs its own hash.
    """
    text = spec.instruction
    return {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "bytes": len(text.encode("utf-8"))}


def resolve_prompt(spec: RunSpec) -> str:
    """The exact instruction text this run will receive.

    Built here rather than handed to the model as a file reference, so the text
    in the request is the text that was hashed.
    """
    body = prompt_body(spec.base_prompt)
    ident = provider_identity()
    settings = _model_settings()
    subs = {
        "{PROJECT}": spec.project,
        "{ARM}": spec.arm,
        "{METHOD}": spec.method,
        "{BUNDLE}": str(spec.bundle),
        "{LABEL}": spec.label,
        "{MANIFEST_LINE}": spec.manifest_line,
        # Substituted, not hardcoded. The first live API run emitted records
        # headed "Agent runtime: Claude Code" on "claude-opus-5[1m]" because
        # this prompt was written for the agent path and reused verbatim — the
        # artifact asserted a runtime and model it never touched.
        "{RUNTIME}": spec.runtime,
        "{PROVIDER}": spec.provider or ident["provider"] or PROVIDER,
        "{MODEL}": settings["name"],
        # v2 introduced `{DATE}` but nothing substituted it, so the literal
        # string reached the model. Its records carry the right date only
        # because the model read it off `{LABEL}` and guessed correctly.
        "{DATE}": spec.run_date,
    }
    for k, v in subs.items():
        body = body.replace(k, v)

    # v1 hardcodes `# Generated: 2026-07-28` where every neighbouring header
    # line takes a placeholder, so every record produced under it since that
    # date carries a false one — the twelve baseline-generic runs made on
    # 2026-07-31 all claim 2026-07-28. Normalising the resolved text fixes it
    # without editing v1, whose bytes are pinned as the published baseline for
    # the 2026-07-28 series. See #214.
    body = re.sub(r"(?m)^(\s*#\s*Generated:).*$", rf"\1 {spec.run_date}", body)

    if spec.condition == "tuned":
        comp = COMPONENTS / f"{spec.project}.md"
        block = comp.read_text(encoding="utf-8") if comp.exists() else ""
        body = body.replace(
            "# Mode: four-phase project agent, generic prompt",
            "# Mode: four-phase project agent, tuned prompt")
        body = body.replace(
            "# Prompt: src/download/prompts/d4d_generic_arm_prompt.md "
            "(identical for all projects)",
            f"# Prompt: {TUNED_PROMPT}\n    # Prompt components: {comp}")
        body = body.replace(
            "RETURN:",
            "PROJECT-SPECIFIC EVIDENCE — the following statements describe this "
            "project's input set. They are factual claims about the corpus. They "
            "state nothing about what the output should contain, how many slots "
            "to populate, or how this record should compare to any other.\n\n"
            f"{block}\n\nRETURN:", 1)
    return body


def _model_settings() -> dict[str, Any]:
    cfg = load_generation_config()
    m = (cfg.get("model") or {}) if isinstance(cfg, dict) else {}
    name = m.get("name") or "claude-opus-5"
    settings = {
        "name": name,
        "temperature": float(m.get("temperature", 0.0)),
        "max_tokens": int(m.get("max_tokens", DEFAULT_MAX_TOKENS)),
        "config_path": str(DETERMINISTIC_CONFIG),
        "temperature_applies": accepts_temperature(name),
    }
    if not settings["temperature_applies"]:
        # The config declares temperature 0.0 and this model refuses the
        # parameter, so the declared value is inert. Recording that here means
        # the provenance says "not applicable" instead of restating a setting
        # that never reached the request.
        settings["temperature_note"] = (
            f"{name} rejects `temperature` (400: deprecated for this model), "
            f"so the {settings['temperature']} declared in "
            f"{DETERMINISTIC_CONFIG} is not sent and does not apply. Sampling "
            "for this model family is selected by model-name suffix "
            "(-low/-medium/-high/-xhigh/-max), not by parameter.")
    return settings


@dataclass
class PhaseRequest:
    phase: str
    system: str
    cached_blocks: list[dict[str, Any]] = field(default_factory=list)
    messages: list[dict[str, Any]] = field(default_factory=list)

    def approx_tokens(self) -> int:
        """Rough input size of this request.

        `cached_blocks` are not added separately: `build_phase` starts the
        message parts with `list(cached)`, so those blocks are already inside
        `messages` and counting both double-counted the bundle — the largest
        thing in the request, and the one a cost estimate most needs right
        (#580).
        """
        chars = len(self.system)
        for m in self.messages:
            c = m.get("content")
            chars += len(c) if isinstance(c, str) else sum(
                len(x.get("text", "")) for x in c)
        return chars // 4


PHASE_INSTRUCTIONS = {
    "full": (
        "Phase 1. Produce the FULL D4D record for class `Dataset`. Use only "
        "keys the schema digest declares, and fill them in this order: a "
        "class's structured slots first (name, id, affiliations, grants and "
        "kin must not sit empty while their content sits in prose), then "
        "`description` as the default home for narrative, and `notes` last — "
        "only for content `description` cannot hold. Evidence commentary — "
        "source conflicts, what a value was transcribed from, questions the "
        "sources leave unanswered — goes in `source_caveats`, never in "
        "`notes`. Never restate a sibling slot's value, and never invent a "
        "key. Output only the YAML, beginning with the header comment block "
        "specified above. No commentary before or after."),
    "core": (
        "Phase 2. Produce the CORE D4D record for class `CoreDataset`, using "
        "the declared bundle and the completed full record supplied above. The "
        "core record must not assert anything the full record does not support. "
        "Use only keys the schema digest declares; structured slots first, "
        "then `description`, with `notes` last and only for content "
        "`description` cannot hold; evidence commentary in `source_caveats` "
        "— never an invented key. Output only the YAML."),
    "audit": (
        "Phase 3. Audit both records against the declared bundle and the "
        "evidence boundary. Report, as a JSON object with keys `findings` (a "
        "list of {severity, record, slot, issue}) and `summary`: any slot whose "
        "value the bundle does not support, any omission the bundle clearly "
        "supports, any content the core record states that the full record "
        "does not, any internal inconsistency, and any value whose shape does "
        "not conform to the schema digest supplied above — prose where the "
        "schema requires a list, enum values the schema does not define, or "
        "source commentary embedded inside a name, identifier or affiliation "
        "value. Output only JSON."),
    "reconcile_full": (
        "Phase 4a. Apply the audit findings that concern the FULL record and "
        "emit the corrected full record in its entirety, header block included. "
        "The core record is supplied above. Anything it states that the full "
        "record does not, **and that the input bundle supports**, absorb into "
        "the full record, in the slot that fits it: the core record is a "
        "projection of the full one and cannot outrank it, so a bundle-"
        "supported fact reaching only core is a fact the full record lost. "
        "Absorb the content, not the wording — put it where the schema says it "
        "belongs, which may not be where core put it. "
        "Do not absorb anything the audit findings above identify as "
        "unsupported: content the core record invented must be removed from "
        "core, never copied into full. A fabrication the two records agree on "
        "is worse than one only core carries, because agreement is what a "
        "reader checks. "
        "Every value you write or change must conform to the schema digest "
        "supplied above — a repair that fixes evidence but breaks shape is "
        "still a defect. If no finding requires a change, emit it unchanged. "
        "Output only YAML."),
    "reconcile_core": (
        "Phase 4b. Apply the audit findings that concern the CORE record and "
        "emit the corrected core record in its entirety, header block included. "
        "It must remain consistent with the reconciled full record supplied "
        "above and assert nothing the full record does not support. Every "
        "value you write or change must conform to the schema digest supplied "
        "above. If no "
        "finding requires a change, emit it unchanged. Output only YAML."),
    "report": (
        "Phase 4c. Write the reconciliation report as Markdown: what the audit "
        "found, what was changed in each record and why, and what was left "
        "as-is and why. The reconciled records are supplied above — check each "
        "statement against them before you write it. Do not report a slot as "
        "removed if it is still present, and do not state that a slot is not "
        "declared in the schema without the schema digest supporting you: both "
        "are checked against the records afterwards, and a report that fails "
        "that check is worse than a shorter one that does not. Write it even "
        "when nothing changed. Output only Markdown."),
}

# What each phase produces, and where it lands. Writing as we go is what makes a
# mid-run failure cost one call instead of six.
PHASE_ARTIFACT = {
    "full": "full", "reconcile_full": "full",
    "core": "core", "reconcile_core": "core",
    "report": "report",
}

# What each phase needs carried forward from earlier ones.
PHASE_NEEDS = {
    "full": (),
    "core": ("Completed full record",),
    "audit": ("Completed full record", "Completed core record"),
    # The core record too (#566). Without it there was no path by which a fact
    # the core phase found in the bundle could reach the full record, and 10 of
    # the 12 v4 records ended with core-only prose the full record lacks —
    # 25,417 characters, including AI-READI's recommended train/validation/test
    # split and CHORUS's holdout test set. The full record is the comprehensive
    # one; a reader of it never saw them.
    "reconcile_full": ("Completed full record", "Completed core record",
                       "Audit findings"),
    "reconcile_core": ("Reconciled full record", "Completed core record", "Audit findings"),
    # The reconciled records too (#580). The report is asked what changed in
    # each record and why, and it received only the audit findings — so it had
    # to reconstruct actions it never observed. #546 found every record that
    # emitted a `distributions` block reporting a removal that did not happen;
    # a phase asked to narrate a diff it cannot see is a plausible cause, and
    # #546 fixed the checking rather than the cause.
    "report": ("Audit findings", "Reconciled full record",
               "Completed core record"),
}


def build_phase(spec: RunSpec, phase: str, *, carry: dict[str, str]) -> PhaseRequest:
    """Assemble one phase's request.

    The bundle and schema digest are the cached prefix: identical across all
    six phases of a run, and by far the largest inputs.
    """
    if phase not in PHASES:
        raise ValueError(f"unknown phase {phase!r}")
    # Keyed off which artifact the phase writes, not off the phase name.
    # `reconcile_core` rewrites the CORE record but was being shown the Dataset
    # digest, so it reintroduced full-schema slots (`splits`, `subsets`,
    # `third_party_sharing`) that CoreDataset does not accept — the first live
    # run produced a core record that failed validation for exactly that.
    cls = "CoreDataset" if PHASE_ARTIFACT.get(phase) == "core" else "Dataset"
    digest = schema_digest.digest_text(cls)
    bundle_text = spec.bundle.read_text(encoding="utf-8", errors="ignore")

    cached = [
        {"type": "text", "text": digest,
         "cache_control": {"type": "ephemeral"}},
        {"type": "text",
         "text": f"# Declared input bundle — {spec.bundle}\n\n{bundle_text}",
         "cache_control": {"type": "ephemeral"}},
    ]

    # Carried artifacts go BEFORE the phase instruction, so the instruction is
    # the last thing in the message (#346). With the old order the message
    # ended with the carried full record — for AI-READI an 83KB YAML document
    # sitting 21k tokens after "Output only the YAML" — and the model continued
    # that document instead of answering: ten consecutive core-phase attempts
    # produced a mid-record fragment growing an `extension_mechanism` slot.
    parts: list[dict[str, Any]] = list(cached)
    parts.append({"type": "text", "text": spec.instruction})
    for name, text in carry.items():
        parts.append({"type": "text",
                      "text": f"# {name}\n\n{text}"})
    parts.append({"type": "text", "text": PHASE_INSTRUCTIONS[phase]})

    return PhaseRequest(
        phase=phase,
        system=("You generate Datasheets-for-Datasets records. The declared "
                "input bundle is your only source of dataset facts. The schema "
                "digest defines structure, never content. Never consult a "
                "previously generated D4D record."),
        cached_blocks=cached,
        messages=[{"role": "user", "content": parts}],
    )


def _carry_sizes(spec: RunSpec) -> tuple[dict[str, int], str]:
    """Byte sizes to assume for each carried artifact, and where they came from.

    A dry run cannot know how large this run's records will be. The best
    available evidence is what the same project produced before, so the most
    recent existing artifacts are measured; failing that the estimate says so
    rather than quietly costing the phases as though nothing were carried.
    """
    from data_sheets_schema.provenance import CONCAT_DIR

    wanted = {"Completed full record": f"{spec.project}_d4d.yaml",
              "Reconciled full record": f"{spec.project}_d4d.yaml",
              "Completed core record": f"{spec.project}_d4d_core.yaml",
              "Audit findings": None}
    sizes: dict[str, int] = {}
    source = None
    for name, filename in wanted.items():
        if filename is None:
            continue
        found = sorted(CONCAT_DIR.glob(f"*/*/{filename}"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if found:
            sizes[name] = found[0].stat().st_size
            source = source or found[0].parent.name
    # Measured, not guessed. The audit *is* archived — `_snapshot` writes
    # `{project}_audit.json` under `intermediate/` — and an eighth of the core
    # record, which the first version assumed, understated it by half: the real
    # median ratio across seven AI-READI snapshots is nearer a quarter.
    audits = sorted(CONCAT_DIR.glob(f"*/*/intermediate/{spec.project}_audit.json"),
                    key=lambda p: p.stat().st_mtime, reverse=True)
    if audits:
        sizes["Audit findings"] = audits[0].stat().st_size
    elif "Completed core record" in sizes:
        sizes["Audit findings"] = sizes["Completed core record"] // 4

    if not sizes:
        return {}, ("no previous artifacts for this project; carried inputs "
                    "are costed as empty and the totals are a lower bound")
    return sizes, (f"carried artifacts sized from the most recent existing "
                   f"records for this project ({source})")


def plan(spec: RunSpec) -> dict[str, Any]:
    """Render every phase without calling the API.

    Lets the whole assembly — prompt resolution, caching layout, token cost — be
    inspected and tested without a key or a charge.
    """
    settings = _model_settings()
    sizes, basis = _carry_sizes(spec)
    phases = []
    for ph in PHASES:
        # Every input the phase declares, at a realistic size. The old version
        # carried a nine-character placeholder for the full record after phase
        # 1 and nothing else ever, so `audit` was costed without core,
        # `reconcile_full` without core or audit, and `reconcile_core` and
        # `report` with nothing at all. The free check that exists to size a
        # run could not see the largest thing in it — and after #566 could not
        # see the change whose size was the open question (#568).
        carry = {name: "x" * sizes.get(name, 0) for name in PHASE_NEEDS[ph]}
        req = build_phase(spec, ph, carry=carry)
        phases.append({"phase": ph, "approx_input_tokens": req.approx_tokens(),
                       "carried": {n: sizes.get(n, 0) for n in PHASE_NEEDS[ph]},
                       "cached_blocks": len(req.cached_blocks)})
    return {
        "project": spec.project, "arm": spec.arm, "method": spec.method,
        "label": spec.label, "condition": spec.condition,
        "bundle": str(spec.bundle), "bundle_bytes": spec.bundle.stat().st_size,
        "model": settings,
        "runtime": RUNTIME,
        "prompt_files": [repo_relative(p) for p in spec.prompt_files],
        "schema_digest_md5": schema_digest.fingerprint(
            schema_digest.digest_text("Dataset")),
        "phases": phases,
        "approx_total_input_tokens": sum(p["approx_input_tokens"] for p in phases),
        "estimate_basis": basis,
        "outputs": {"full": str(spec.full_path), "core": str(spec.core_path),
                    "report": str(spec.report_path)},
    }


CBORG_BASE_URL = "https://api.cborg.lbl.gov"

# Models that reject `temperature` outright. claude-opus-5 returns
# 400 "`temperature` is deprecated for this model", so sending it fails the
# request rather than being ignored. Sampling control for these models is
# expressed as a model-name suffix (-low/-medium/-high/-xhigh/-max) rather
# than a request parameter.
NO_TEMPERATURE_MODELS = ("claude-opus-5", "claude-opus-4-6", "claude-opus-4-7",
                         "claude-opus-4-8", "claude-fable-5")

# Output ceilings differ sharply between CBORG routes for the same model:
# claude-opus-5 is 1M in / 128k out, while google/claude-opus-5-high is
# 200k / 64k. Requesting more than a route allows is a 400, and the `full`
# phase asks for exactly 64k, so the request must be clamped rather than
# assumed to fit.
MODEL_OUTPUT_LIMIT = {
    "claude-opus-5": 128000,
    "claude-opus-4-8": 128000,
    "claude-opus-4-7": 128000,
    "claude-opus-4-6": 128000,
}
DEFAULT_OUTPUT_LIMIT = 64000


def output_limit(model: str) -> int:
    """Largest max_tokens this route accepts.

    Prefixed routes (`google/…`, `amazon/…`) are the lower-limit rebroadcasts,
    so only the bare identifiers get the raised ceiling.
    """
    if "/" in model:
        return DEFAULT_OUTPUT_LIMIT
    return MODEL_OUTPUT_LIMIT.get(model, DEFAULT_OUTPUT_LIMIT)


def accepts_temperature(model: str) -> bool:
    """Whether this model will accept a `temperature` parameter."""
    base = model.split("/")[-1]
    return not any(base.startswith(m) for m in NO_TEMPERATURE_MODELS)


def _client():
    """Anthropic-shaped client, pointed at CBORG when a CBORG key is present.

    CBORG is an LBL proxy that exposes *both* an OpenAI-style
    `/v1/chat/completions` and an Anthropic-native `/v1/messages`. Verified
    2026-07-29: the native endpoint returns real `stop_reason` and `usage`
    fields, so the six-phase code runs against it unchanged. Using the OpenAI
    shape instead would have meant re-expressing the truncation guard
    (`stop_reason == "max_tokens"` becomes `finish_reason == "length"`) and
    losing the cache_control blocks the cost model depends on.

    ANTHROPIC_API_KEY still wins when set, so a direct-to-Anthropic run stays
    possible and the two are distinguishable in the provenance record.
    """
    direct = os.environ.get("ANTHROPIC_API_KEY")
    cborg = os.environ.get("CBORG_API_KEY")
    import anthropic
    if direct:
        return anthropic.Anthropic(api_key=direct)
    if cborg:
        return anthropic.Anthropic(api_key=cborg, base_url=CBORG_BASE_URL)
    raise RuntimeError(
        "No API key found. Set CBORG_API_KEY (LBL proxy) or ANTHROPIC_API_KEY, "
        "or use plan() / `d4d api plan` to inspect requests without calling "
        "the API. Note that a non-login shell does not read ~/.bashrc; invoke "
        "via `bash -lc` or put the key in the repo .env.")


def provider_identity() -> dict[str, Any]:
    """Which endpoint a run will actually reach — recorded in provenance."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {"provider": "Anthropic", "base_url": "https://api.anthropic.com",
                "key_env": "ANTHROPIC_API_KEY"}
    if os.environ.get("CBORG_API_KEY"):
        return {"provider": "LBL CBORG (proxy to Anthropic)",
                "base_url": CBORG_BASE_URL, "key_env": "CBORG_API_KEY"}
    return {"provider": None, "base_url": None, "key_env": None}


FULL_SCHEMA_PATH = "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
CORE_SCHEMA_PATH = "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"


@lru_cache(maxsize=4)
def _known_slots(schema_path: str = FULL_SCHEMA_PATH,
                 class_name: str = "Dataset") -> frozenset[str]:
    """The slots the *target class* accepts at its root.

    Not `all_slots()`. Every slot the schema file mentions is a far looser test
    than it looks: the core schema names 262 slots but `CoreDataset` accepts 79
    of them, so two thirds of that vocabulary belongs to some other class and
    would wave through root keys the target class cannot hold.
    """
    from linkml_runtime import SchemaView
    sv = SchemaView(schema_path)
    return frozenset(s.name for s in sv.class_induced_slots(class_name))


# Which vocabulary each record-producing phase is checked against. Using the
# full schema for a core response let full-only root keys pass a check that
# exists precisely to catch a core record that drifted back into full slots.
PHASE_SCHEMA = {
    "full": (FULL_SCHEMA_PATH, "Dataset"),
    "reconcile_full": (FULL_SCHEMA_PATH, "Dataset"),
    "core": (CORE_SCHEMA_PATH, "CoreDataset"),
    "reconcile_core": (CORE_SCHEMA_PATH, "CoreDataset"),
}


def _looks_like_a_record(parsed: dict, schema_path: str = FULL_SCHEMA_PATH,
                         class_name: str = "Dataset") -> bool:
    """Is this the record the phase was asked for, or something else entirely?

    Three separate things have reached this guard and been let through, each
    after a loosening that fixed a real false rejection:

    * narration — `Note: I need to emit the corrected core record.` parses as a
      perfectly good mapping. Requiring *some* known slot was not enough,
      because narration sits happily beside one (`Note: ...` plus `id: x`).
    * refusals — `title: I cannot produce the requested record` names nothing
      but real slots, so a vocabulary test alone cannot see it.
    * fragments — a stray `id: x` example, or the 8-key `_distributions` blob
      that one VOICE core run actually wrote to disk.

    So the test is structural rather than lexical: a record carries the root
    identifier, spends its keys entirely on slots the target class defines, and
    is not a two-key stub. Every one of the 46 real records on disk satisfies
    all three; the fragment satisfies none.
    """
    keys = {str(k) for k in parsed}
    if "id" not in keys:
        return False
    if keys - _known_slots(schema_path, class_name):
        return False
    return len(keys) >= MIN_RECORD_SLOTS


# Real records carry 47-84 top-level slots (full) and 42-69 (core); refusals
# and examples carry one or two. The floor sits far below every observed record
# because its job is to separate a record from a stub, not to police
# completeness — a genuinely sparse record is the validator's business.
MIN_RECORD_SLOTS = 5


def _audit_is_well_formed(parsed: dict) -> bool:
    """Does this JSON actually carry an audit, or merely the word `findings`?

    `{"findings": null}` and `{"findings": "unable to audit"}` both satisfy a
    key-presence test, and both were accepted. Either one is then handed to
    both reconciliation phases as though an audit had happened — three more
    billed calls spent correcting a record against nothing.
    """
    findings = parsed.get("findings")
    if not isinstance(findings, list):
        return False
    return all(isinstance(f, dict) and {"severity", "slot", "issue"} <= set(f)
               for f in findings)


def _extract(text: str, kind: str,
             schema_path: str = FULL_SCHEMA_PATH,
             class_name: str = "Dataset") -> str:
    """Pull YAML or JSON out of a response, refusing anything that is neither.

    Falling back to the raw response when no fence was found wrote the model's
    *narration* into a record. One core file began "I need to emit the corrected
    core record. The core schema (CoreDataset) does not have..." and was saved as
    the artifact; only the downstream validator noticed, after the run had been
    billed in full.

    Markdown is returned untouched and never fence-extracted. A reconciliation
    report is prose that routinely *quotes* corrected slots in fenced blocks, so
    extracting the fence would reduce the report to the example inside it —
    which is what an earlier version of this function did.
    """
    if kind == "md":
        if not text.strip():
            raise RuntimeError(
                "response contained no report text. A phase that produces "
                "nothing must fail rather than write an empty artifact.")
        return text.strip()

    fences = re.findall(r"```(?:ya?ml|json)?\s*\n(.*?)```", text,
                        re.S | re.I)
    # An *unclosed* fence is common enough to handle: the model opens ```yaml,
    # emits the record, and never closes it. And a response sometimes begins
    # with a bare `yaml` line — a fence marker whose backticks did not survive.
    # Both produce a perfectly good record that a strict reader throws away,
    # and each rejection costs every phase already billed for that run.
    unclosed = re.findall(r"```(?:ya?ml|json)?\s*\n(.*)\Z", text, re.S | re.I)
    stripped = re.sub(r"\A\s*(?:ya?ml|json)\s*\n", "", text,
                      flags=re.I)

    def accepts(candidate: str) -> bool:
        if not candidate:
            return False
        try:
            parsed = (json.loads(candidate) if kind == "json"
                      else yaml.safe_load(candidate))
        except (yaml.YAMLError, json.JSONDecodeError):
            return False
        if not isinstance(parsed, dict):
            return False
        # Each phase has a declared shape; anything else carried forward would
        # be a record, or an audit, that never happened.
        if kind == "json":
            return _audit_is_well_formed(parsed)
        return _looks_like_a_record(parsed, schema_path, class_name)

    # Fences first, and *all* of them. Taking the last one on the grounds that
    # the model corrects itself as it goes is a guess about narrative order,
    # not evidence: a complete record followed by a one-line `id: x` example
    # silently became that example. Where two fences both look like the
    # requested record, the response is ambiguous and no positional rule can
    # say which was meant — so fail, rather than pick and write the wrong one.
    good = [f.strip() for f in fences if accepts(f.strip())]
    distinct = {yaml.safe_dump(yaml.safe_load(g), sort_keys=True) for g in good}
    if len(distinct) > 1:
        raise RuntimeError(
            f"response contained {len(distinct)} different fenced {kind} "
            f"objects that each look like the requested record. Refusing to "
            f"guess which was intended.")
    if good:
        return good[0]

    for candidate in ([f.strip() for f in unclosed]
                      + [stripped.strip(), text.strip()]):
        if accepts(candidate):
            return candidate

    raise RuntimeError(
        f"response contained no parseable {kind} object of the expected shape. "
        f"The model appears to have written prose instead of a record; first "
        f"200 characters: {text.strip()[:200]!r}")


# Slots whose range is temporal, by the shape the validator demands. Two
# separate failures were showing up as one (#215):
#
#   issued: 2026-05-01T00:00:00Z      <- CORRECT value, rejected. Unquoted, so
#                                        PyYAML hands the validator a datetime
#                                        object where a string is required.
#   issued: '2026-05-01T00:00:00'     <- genuinely wrong: no timezone.
#   issued: '2026-06-30'              <- genuinely wrong: a date, not a datetime.
#
# So the generator was right half the time and the serialisation lost it. Both
# are fixed by emitting a quoted value shaped to the slot's range.
DATETIME_SLOTS = ("issued", "created_on", "last_updated_on")
DATE_SLOTS = ("start_date", "end_date")

_TEMPORAL_LINE = re.compile(
    r"^(?P<indent>[ \t]*-?[ \t]*)(?P<slot>"
    + "|".join(DATETIME_SLOTS + DATE_SLOTS)
    + r"):[ \t]+(?P<value>\S.*?)[ \t]*$")
# A block scalar opens with `|`/`>` (plus optional chomping/indent indicators)
# and owns every following line indented further than its key.
_BLOCK_OPEN = re.compile(r"^(?P<indent>[ \t]*)(?:-[ \t]+)?[\w.-]+:[ \t]*[|>][+-]?\d*[ \t]*$")
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})[T ](?P<time>\d{2}:\d{2}(?::\d{2})?)"
    r"(?:\.\d+)?(?P<zone>Z|[+-]\d{2}:?\d{2})?$")


@lru_cache(maxsize=1)
def _enum_aliases() -> dict[str, dict[str, str]]:
    """slot name -> {alias or casing variant -> permissible value}.

    Keyed by slot, not global. An earlier version flattened every alias of every
    enum into one table and applied it to any `key: Value` line, which rewrote
    `title: References` to `title: references` — a plain string slot corrupted on
    the write path by the pass meant to be fixing validity (#299). Only slots the
    schema gives an enum range are eligible, so `title`, `name` and `description`
    are not reachable at all.

    Read from the schema rather than listed here, because the schema is where the
    aliases are declared and a second copy would be one to keep in step.

    `linkml-validate` matches permissible values on `text` alone, so a record
    using a name the schema itself declares as an alias fails validation. The
    enum aligned with DataCite (#223) declares DataCite's own CamelCase
    spellings — `IsNewVersionOf`, `HasPart`, `References` — and those are what
    generation emits, because they are what the vocabulary is called elsewhere.
    """
    import yaml as _yaml
    schema = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
    if not schema.exists():
        return {}
    doc = _yaml.safe_load(schema.read_text(encoding="utf-8"))
    enums = doc.get("enums") or {}

    def table_for(enum_name: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for text, pv in (enums[enum_name].get("permissible_values") or {}).items():
            for alias in ((pv or {}).get("aliases") or []):
                out[alias] = text
                out.setdefault(alias.lower(), text)
            # Case alone is not an alias, but it is a difference with no
            # content: `References` against `references` is a validation
            # failure that says nothing about the record.
            out.setdefault(text.lower(), text)
        return out

    by_slot: dict[str, dict[str, str]] = {}
    conflicted: set[str] = set()
    for cls in (doc.get("classes") or {}).values():
        for slot, spec in (cls.get("attributes") or {}).items():
            enum_name = spec.get("range")
            if enum_name not in enums:
                continue
            table = table_for(enum_name)
            if slot in by_slot and by_slot[slot] != table:
                # The same slot name ranged on different enums in different
                # classes. Text alone cannot say which class a line sits in, so
                # rewriting either way would be a guess.
                conflicted.add(slot)
                continue
            by_slot[slot] = table
    for slot in conflicted:
        by_slot.pop(slot, None)
    return by_slot


#: Values may carry digits — `BZ2`, `Big5`, `GB2312` are all permissible values,
#: and a letters-only pattern silently skipped 41 of them.
_ENUM_LINE = re.compile(r"^(?P<head>[ \t]*-?[ \t]*(?P<slot>[a-z_]+):[ \t]+)"
                        r"(?P<value>[A-Za-z][A-Za-z0-9_./+-]*)[ \t]*$")


def normalise_enum_aliases(text: str) -> str:
    """Rewrite a declared alias to the permissible value it names.

    Text-level for the same reason as `normalise_temporal`: re-dumping the YAML
    would drop the `#` provenance header the reader sees first.

    Only bare word-shaped scalars in enum-ranged slots are touched, so prose is
    left exactly as written — a value like `is a later release in the same
    series as` is a real generation failure and normalising it into silence
    would hide it.
    """
    by_slot = _enum_aliases()
    if not by_slot:
        return text

    def fix(m: "re.Match") -> str:
        table = by_slot.get(m.group("slot"))
        if not table:
            return m.group(0)
        value = m.group("value")
        canonical = table.get(value) or table.get(value.lower())
        return f"{m.group('head')}{canonical}" if canonical else m.group(0)

    return "\n".join(_ENUM_LINE.sub(fix, line) for line in text.split("\n"))


def normalise_temporal(text: str) -> str:
    """Quote and shape temporal values to the range their slot declares.

    Text-level on purpose. Parsing and re-dumping the YAML would drop the `#`
    header block every record carries — the provenance the reader sees first.
    """
    def indent_of(line: str) -> int:
        return len(line) - len(line.lstrip(" \t"))

    def fix(m: re.Match) -> str:
        raw = m.group("value").strip()
        # Leave alone anything that is not a plain scalar: nulls, aliases,
        # inline comments, flow collections, block scalars.
        if (not raw or raw in {"null", "~"} or raw[0] in "*&[{|>#"
                or " #" in raw):
            return m.group(0)
        val = raw.strip("'\"")
        want_datetime = m.group("slot") in DATETIME_SLOTS
        if _DATE_ONLY.match(val):
            out = f"{val}T00:00:00Z" if want_datetime else val
        elif (dt := _DATETIME.match(val)):
            if want_datetime:
                time = dt.group("time")
                if len(time) == 5:               # HH:MM -> HH:MM:SS
                    time += ":00"
                out = f"{dt.group('date')}T{time}{dt.group('zone') or 'Z'}"
            else:
                out = dt.group("date")           # a date slot keeps only the date
        else:
            return m.group(0)                    # unrecognised: do not guess
        return f"{m.group('indent')}{m.group('slot')}: '{out}'"

    # Line by line, skipping block scalars. A description is free prose, and
    # prose quoting a field name — "Fields present in the manifest:\nissued:
    # 2026-05-01" — matches the pattern exactly. Rewriting that edits the
    # *content* of a record rather than its serialisation, which is the one
    # thing this function must never do.
    out_lines: list[str] = []
    block_indent: int | None = None
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n\r")
        if block_indent is not None:
            if not stripped.strip() or indent_of(stripped) > block_indent:
                out_lines.append(line)                 # still inside the block
                continue
            block_indent = None                        # block ended
        if (opener := _BLOCK_OPEN.match(stripped)):
            block_indent = len(opener.group("indent"))
            out_lines.append(line)
            continue
        out_lines.append(_TEMPORAL_LINE.sub(fix, stripped)
                         + line[len(stripped):])
    return "".join(out_lines)


PROGRESS_SUFFIX = "_api_progress.json"


def _progress_path(spec: RunSpec) -> Path:
    return spec.metadata_dir / f"{spec.project}{PROGRESS_SUFFIX}"


def _reasoning_path(spec: RunSpec) -> Path:
    """Beside the provenance record, under the same metadata_dir rule.

    Reasoning is provenance about how the record came to say what it says, so
    it belongs with the provenance rather than beside the record. Keeping the
    two placement rules identical is deliberate — the earlier split, where a
    run's metadata landed in two directories, is what made the monitor report
    "no progress file" while five phases had completed.
    """
    return spec.metadata_dir / f"{spec.project}_reasoning.jsonl"


def _load_progress(spec: RunSpec) -> dict[str, Any]:
    p = _progress_path(spec)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}          # a corrupt progress file means redo, never crash


def _save_progress(spec: RunSpec, completed: list[str],
                   audit: str | None) -> None:
    p = _progress_path(spec)
    p.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {"completed": completed, "label": spec.label}
    if audit:
        data["Audit findings"] = audit
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _artifact_path(spec: RunSpec, artifact: str) -> Path:
    return {"full": spec.full_path, "core": spec.core_path,
            "report": spec.report_path}[artifact]




def validation_block(spec: RunSpec, problems: list[dict[str, str]],
                     recorded_by: str = "api_runner.execute") -> dict[str, Any]:
    """The validation verdict, bound to the exact bytes it was reached on.

    A verdict alone is a cached assertion about a file: edit the record and the
    provenance still says `passed: true`. Recording each artifact's md5 makes a
    stale verdict detectable rather than merely improbable — `validation_status`
    re-hashes and reports STALE when they diverge. Hashing a 50-150 KB file is
    microseconds, so this stays cheap enough for an analysis hot path, which
    re-validating never would be.

    md5 to match `provenance._artifact()`, which already hashes run outputs that
    way; see INPUT_HASH there for why prompts use sha256 and these do not.
    """
    from data_sheets_schema.provenance import _md5
    artifacts = {}
    for name, path in (("full", spec.full_path), ("core", spec.core_path)):
        artifacts[name] = {"path": str(path),
                           "md5": _md5(path) if path.exists() else None}
    # The schema the verdict was reached against, not only the record it was
    # reached on. "Validates" is a claim about a record *against a schema*, and
    # pinning only the artifacts let a verdict survive a schema change that
    # would have failed it — `validation_status` re-hashed the record, found it
    # unchanged, and reported VALID for a check that no longer existed (#426).
    from data_sheets_schema.provenance import CORE_SCHEMA, FULL_SCHEMA, _sha256
    block: dict[str, Any] = {"passed": not problems, "artifacts": artifacts,
                             "schema": {"full_sha256": _sha256(FULL_SCHEMA),
                                        "core_sha256": _sha256(CORE_SCHEMA)},
                             "recorded_by": recorded_by}
    if problems:
        block["problems"] = problems
    return block


def _validator_lines(path: Path, schema: str,
                     cls: str) -> tuple[list[str] | None, str | None]:
    """(findings, failure): every validator finding, one per line.

    `findings` is None exactly when `failure` says why the validator itself
    could not run — the two outcomes must stay distinguishable, because a
    record that could not be checked is not a record that passed, and a
    repair attempted against a broken validator would be flying blind.
    """
    try:
        r = subprocess.run(
            ["poetry", "run", "linkml-validate", "-s", schema, "-C", cls,
             str(path)],
            capture_output=True, text=True, timeout=180)
    except Exception as exc:                           # noqa: BLE001
        return None, str(exc)
    if r.returncode == 0:
        return [], None
    lines = [l for l in (r.stdout + r.stderr).strip().splitlines()
             if l.strip()]
    return lines, None


def validate_outputs(spec: RunSpec) -> list[dict[str, str]]:
    """LinkML-validate both records, returning problems rather than raising.

    Returned so the caller can record the outcome in provenance before deciding
    what to do: a record that fails validation should still be inspectable, and
    the provenance should say it failed rather than omit the question.
    """
    problems: list[dict[str, str]] = []
    for path, schema, cls in ((spec.full_path, FULL_SCHEMA_PATH, "Dataset"),
                              (spec.core_path, CORE_SCHEMA_PATH, "CoreDataset")):
        if not path.exists():
            problems.append({"artifact": str(path), "error": "missing"})
            continue
        lines, failure = _validator_lines(path, schema, cls)
        if failure is not None:
            problems.append({"artifact": str(path),
                             "error": f"validator did not run: {failure}"})
            continue
        if lines:
            problems.append({"artifact": str(path), "class": cls,
                             "error": " | ".join(lines[:4])})
    return problems


def pair_consistency(spec: RunSpec) -> dict[str, Any] | None:
    """Does the full/core pair this run produced actually agree? (#544)

    The API path has `reconcile_full` and `reconcile_core` phases and writes
    `# Phase 4 reconciliation: completed` into every core header, but nothing
    ever ran the pair checker afterwards. The agentic playbook does, at its own
    phase 4, and the difference is the whole difference: across the
    2026-08-13 v4 arm 11 of 12 pairs failed, against 0 of 15 in the
    2026-08-11 agentic arm.

    Every individual record validated in both arms, which is why neither
    `linkml-validate` nor `runs check --strict` noticed — both read one file at
    a time, and this is a property of two files together.

    Reported, never fatal. A divergent pair is still usable evidence and the
    records are individually valid; the defect being fixed here is that it was
    invisible, not that it is fatal. Returns None when the checker cannot run,
    so "not established" stays distinct from "consistent".
    """
    try:
        from data_sheets_schema.d4d_pair_consistency import (load_pair_schema,
                                                             validate_pair_data)
        import yaml as _yaml
        missing = [str(f) for f in (spec.full_path, spec.core_path)
                   if not f.exists()]
        if missing:
            # Not None. None means the block was never written; this run wrote
            # one and the file it needed was absent, which `validate_outputs`
            # will also have flagged. Two different states, two answers.
            return {"ran": False, "reason": f"missing: {', '.join(missing)}"}
        pair = load_pair_schema(FULL_SCHEMA_PATH, CORE_SCHEMA_PATH)
        full = _yaml.safe_load(spec.full_path.read_text(encoding="utf-8")) or {}
        core = _yaml.safe_load(spec.core_path.read_text(encoding="utf-8")) or {}
        # `schema_moved` is what #520 is for: a slot added to core after a pair
        # was written is absent from that pair because it could not have been
        # present, which is a fact about the schema's history rather than a
        # defect in the record. Presence then warns; content disagreement stays
        # an error, because two records asserting different values were wrong
        # when written.
        #
        # For a fresh run this is always False — the run just consumed the
        # current schema. Computed rather than hardcoded so the answer stays
        # right if this is ever called on an older pair, which is exactly how
        # the backfill got it wrong (#550).
        from data_sheets_schema.d4d_pair_consistency import (
            pair_predates_current_schema)
        moved = pair_predates_current_schema(spec.core_path)
        # This run's own digest, so a presence mismatch is excused only for
        # slots the ledger shows did not exist then (#580).
        from data_sheets_schema import schema_digest as _sd
        _sd.record_inventory()
        run_digest = _sd.fingerprint(_sd.digest_text("Dataset"))
        report = validate_pair_data(full, core, pair, schema_moved=moved,
                                    run_digest=run_digest)
    except Exception as exc:                                       # noqa: BLE001
        # A checker that cannot run must say so rather than report agreement.
        return {"ran": False, "reason": str(exc)[:200]}
    from data_sheets_schema.provenance import _md5
    return {
        "ran": True,
        "consistent": report.passed,
        # Pinned for the same reason `validation_block` pins its artifacts
        # (#426, #433): a verdict about two files is a cached assertion, and
        # editing either one leaves it saying `consistent: true` about bytes
        # that no longer exist. Both files, because either can break the pair.
        # Paths as well as hashes, and for the same reason `validation_block`
        # records them: the two records do not live in one directory — the full
        # record is under `{method}/{label}/` and the core one under
        # `{method}_core/{label}/`, beside this provenance file. A re-check
        # that reconstructs either path from the record's own location looks
        # for a file that was never there and calls every pair stale.
        "artifacts": {
            "full": {"path": str(spec.full_path), "md5": _md5(spec.full_path)},
            "core": {"path": str(spec.core_path), "md5": _md5(spec.core_path)},
        },
        "errors": len(report.errors),
        "warnings": len(report.warnings),
        "identity_slots": len(report.identity_slots),
        # Recorded, because it changes what the verdict means: with it true,
        # a presence divergence is a warning and the pair can pass.
        "schema_moved": moved,
        # Bounded, and says so. A list silently cut at 20 reads as a complete
        # one; `errors` above is the true count either way.
        "findings": [{"code": i.code, "path": i.path, "message": i.message[:200]}
                     for i in report.errors[:20]],
        "findings_truncated": max(0, len(report.errors) - 20) or None,
    }


#: Context windows a model name states outright. The route is the only place
#: this appears — CBORG returns no limit in its responses — so a name that does
#: not carry one leaves the limit genuinely unknown (#568).
CONTEXT_FROM_NAME = ((r"\[1m\]|-1m\b|:1m\b", 1_000_000),)


def context_facts(model_name: str,
                  usage: list[dict[str, Any]]) -> dict[str, Any]:
    """What the run can honestly say about its context window (#568).

    Two different claims, kept apart:

    `peak_request_tokens` is **observed** — the largest request this run
    actually sent, summing input, cache reads and cache writes, because cached
    tokens occupy the window just as fresh ones do. It is what answers "did it
    fit", and it is available whatever the model says about itself.

    `limit_tokens` is the ceiling, and is usually **not knowable here**. The
    v4 arm named `claude-opus-5` and sent a 249,015-token request that
    succeeded, so the name understated the truth by at least a quarter. A guess
    would be worse than the gap: it would make headroom computable and wrong.
    Recorded only when the route states it, and named as a gap otherwise —
    the same rule `reasoning_effort` follows (#397, #470).
    """
    peak, phase = 0, None
    for u in usage:
        total = (int(u.get("input_tokens") or 0) + int(u.get("cache_read") or 0)
                 + int(u.get("cache_write") or 0))
        if total > peak:
            peak, phase = total, u.get("phase")
    out: dict[str, Any] = {"peak_request_tokens": peak or None,
                           "peak_phase": phase,
                           "peak_basis": "observed: input + cache_read + "
                                         "cache_write of the largest request"}
    for pattern, limit in CONTEXT_FROM_NAME:
        if re.search(pattern, model_name or "", re.I):
            out["limit_tokens"] = limit
            out["limit_basis"] = f"the model route names it ({model_name})"
            break
    else:
        out["limit_tokens"] = None
        out["limit_basis"] = ("not stated by the route and not returned by the "
                              "provider; headroom cannot be computed from this "
                              "record")
    return out


def report_claims_block(spec: RunSpec) -> dict[str, Any] | None:
    """Check the reconciliation report against the record and the schema (#546).

    The report is what a reviewer reads instead of diffing YAML, and nothing
    checked it against anything. In the v4 arm every record that emitted a
    `distributions` block — 9 of 12 — reported removing it, from the premise
    that `distributions` is not a declared slot. It is, with range
    `CoreDistribution`, and the blocks are still there.

    Reported, never fatal, like the pair check: a wrong report does not make a
    record wrong, and the whole corpus predates this.
    """
    try:
        import yaml as _yaml

        from data_sheets_schema.report_claims import (check_report,
                                                      declared_slots)
        if not spec.report_path.exists():
            return {"checked": False, "reason": "no reconciliation report"}
        full = _yaml.safe_load(spec.full_path.read_text(encoding="utf-8")) \
            if spec.full_path.exists() else {}
        core = _yaml.safe_load(spec.core_path.read_text(encoding="utf-8")) \
            if spec.core_path.exists() else {}
        out = check_report(spec.report_path, full or {}, core or {},
                           declared_slots())
    except Exception as exc:                                       # noqa: BLE001
        return {"checked": False, "reason": str(exc)[:200]}
    from data_sheets_schema.provenance import (CORE_SCHEMA, FULL_SCHEMA, _md5,
                                                _sha256)
    # The records and the schema, not only the report (#580). A claim is
    # checked *against* a record and a slot inventory, so a verdict pinned to
    # the report alone survives an edit to either — the same reason
    # `validation_block` pins its schema (#426) and the pair verdict pins both
    # records (#544).
    out["artifacts"] = {
        "report": {"path": str(spec.report_path),
                   "md5": _md5(spec.report_path)},
        "full": {"path": str(spec.full_path), "md5": _md5(spec.full_path)},
        "core": {"path": str(spec.core_path), "md5": _md5(spec.core_path)},
    }
    out["schema"] = {"full_sha256": _sha256(FULL_SCHEMA),
                     "core_sha256": _sha256(CORE_SCHEMA)}
    return out


def grounding_block(spec: RunSpec) -> dict[str, Any] | None:
    """Are this run's external identifiers in the bundle it read? (#547)

    VOICE rep1 supplied 19 RORs that appear nowhere in its bundle. Every one is
    correct — the run learned the institutions from the evidence and the
    identifiers from memory. Right answer, no evidence, and no existing check
    can see it: `linkml-validate` accepts any well-formed `uriorcurie`, and
    `d4d runs identifiers` treats a resolvable IRI as the best possible
    outcome.

    Reported, never fatal, following #520.
    """
    try:
        from data_sheets_schema.grounding import check_run
        out = check_run(spec.full_path, spec.core_path, spec.bundle)
    except Exception as exc:                                       # noqa: BLE001
        return {"checked": False, "reason": str(exc)[:200]}
    if out.get("checked"):
        from data_sheets_schema.provenance import _md5
        out["artifacts"] = {"bundle": {"path": str(spec.bundle),
                                       "md5": _md5(spec.bundle)}}
    return out


REPAIR_SYSTEM = (
    "You repair the shape of Datasheets-for-Datasets records. The schema "
    "digest defines the required structure. The validator findings are the "
    "complete work order: correct what they name and nothing else. Never add, "
    "remove or reword dataset facts; a fact whose required structure the "
    "record cannot supply moves to the nearest slot that accepts it, or is "
    "omitted as a last resort.")

REPAIR_INSTRUCTION = (
    "Shape repair. The record above failed LinkML validation; each finding "
    "names the failing path and the shape the schema requires. Emit the "
    "record in its entirety with only those failures corrected. Output only "
    "YAML.")

# The loop runs while the finding count strictly decreases, up to this
# ceiling. A fixed budget of 2 was cut short by the live canary (#364): the
# core record converged 76 -> 9 -> 4 and was stopped mid-repair. Strict
# decrease is the real convergence test — a round that leaves the count equal
# or higher IS non-convergence and stops immediately — and the ceiling bounds
# what a stubborn record can bill.
REPAIR_ROUNDS = 4


#: Slots whose declared range is multivalued, from the schema rather than a
#: hand-kept list — the same derivation `_enum_aliases` uses.
_MULTIVALUED: set[str] | None = None


def _multivalued_slots() -> set[str]:
    global _MULTIVALUED
    if _MULTIVALUED is None:
        from linkml_runtime import SchemaView
        names: set[str] = set()
        for schema, in ((FULL_SCHEMA_PATH,), (CORE_SCHEMA_PATH,)):
            try:
                sv = SchemaView(str(schema))
                for cls in sv.all_classes():
                    for slot in sv.class_induced_slots(cls):
                        if slot.multivalued and str(slot.range) == "string":
                            names.add(str(slot.name))
            except Exception:                                      # noqa: BLE001
                continue
        _MULTIVALUED = names
    return _MULTIVALUED


#: `  key: value` on one line — a plain scalar, or a block-scalar indicator.
#:
#: Flow collections (`[`, `{`), anchors and aliases (`&`, `*`) and tags (`!`)
#: are excluded: those are either already a collection or too structured to
#: rewrite blind. Block indicators (`>`, `|`) are *included*, because that is
#: the shape the failing record actually used — an earlier version excluded
#: them here while handling them below, so the branch was unreachable and the
#: function silently did nothing.
_SCALAR_LINE = re.compile(
    r"^(?P<head>\s*)(?P<slot>[A-Za-z_][\w]*): (?P<value>(?![\[\{&*!])"
    r"(?!\s*$).*?)\s*$")


def normalise_multivalued(text: str) -> str:
    """Wrap a lone scalar into a list where the slot declares multivalued.

    Text-level for the same reason as `normalise_temporal` and
    `normalise_enum_aliases`: re-dumping the YAML would drop the `#` provenance
    header the reader sees first.

    There is exactly one correct repair here and it needs no evidence — a
    multivalued slot holding one value is that value in a one-element list — so
    doing it deterministically is both cheaper and more reliable than asking
    the model. AI_READI rep3 of the v4 arm wrote `special_populations` as a
    sentence, the model-driven loop fixed 36 of 37 findings and then logged
    `not converging: 1 -> 1 findings; stopped`, and the run failed validation
    over a fix that could not have been ambiguous.

    Only unquoted or simply-quoted single-line scalars are touched. A block
    scalar, a flow collection, an anchor or an empty value is left alone: those
    are either already correct or a real generation failure that normalising
    would hide.
    """
    slots = _multivalued_slots()
    if not slots:
        return text
    out = []
    for line in text.split("\n"):
        m = _SCALAR_LINE.match(line)
        if m and m.group("slot") in slots:
            value = m.group("value")
            head = m.group("head")
            # A block scalar: keep the indicator, put it on a list item, and
            # leave the indented continuation lines untouched. They stay more
            # indented than the `- `, so the block still belongs to the item.
            # This is the shape AI_READI rep3 actually used — the first version
            # of this function excluded block scalars and did nothing at all.
            if value in (">-", ">", "|-", "|", ">+", "|+"):
                out.append(f"{head}{m.group('slot')}:")
                out.append(f"{head}- {value}")
                continue
            if value not in ("null", "~", "") and not value.startswith("#"):
                out.append(f"{head}{m.group('slot')}:")
                out.append(f"{head}- {value}")
                continue
        out.append(line)
    return "\n".join(out)


def build_repair(artifact: str, body: str, errors: list[str]) -> PhaseRequest:
    """A shape-repair request: digest, failing record, validator findings.

    Deliberately excludes the input bundle. The validator names shapes, not
    facts; a repair with the corpus in view is an invitation to fix content,
    and the evidence boundary belongs to the six generation phases. Excluding
    it also makes a repair call an order of magnitude cheaper than a phase.
    """
    cls = "CoreDataset" if artifact == "core" else "Dataset"
    digest = schema_digest.digest_text(cls)
    cached = [{"type": "text", "text": digest,
               "cache_control": {"type": "ephemeral"}}]
    parts: list[dict[str, Any]] = list(cached)
    parts.append({"type": "text",
                  "text": f"# Record that failed validation\n\n{body}"})
    parts.append({"type": "text",
                  "text": "# Validator findings\n\n" + "\n".join(errors)})
    parts.append({"type": "text", "text": REPAIR_INSTRUCTION})
    return PhaseRequest(phase=f"repair_{artifact}", system=REPAIR_SYSTEM,
                        cached_blocks=cached,
                        messages=[{"role": "user", "content": parts}])


def _intermediate_dir(spec: RunSpec) -> Path:
    """Where a run's phase snapshots live, beside its provenance."""
    return spec.provenance_path.parent / "intermediate"


def _snapshot(spec: RunSpec, name: str, body: str) -> Path:
    """Preserve one phase's output before a later phase overwrites it (#369).

    Never overwrites: repair round numbers restart on a resumed invocation,
    so a colliding name gets a numeric suffix — losing the earlier round's
    state to the later one would defeat the point.
    """
    d = _intermediate_dir(spec)
    d.mkdir(parents=True, exist_ok=True)
    stem, dot, ext = name.rpartition(".")
    path = d / name
    n = 2
    while path.exists():
        path = d / f"{stem}_{n}.{ext}"
        n += 1
    path.write_text(body, encoding="utf-8")
    return path


def _intermediates_block(spec: RunSpec) -> list[dict[str, Any]] | None:
    """Every snapshot on disk for this run's project, pinned by hash.

    Globbed at record-build time rather than accumulated in memory, so a
    resumed invocation lists the earlier invocations' snapshots too.
    """
    d = _intermediate_dir(spec)
    if not d.is_dir():
        return None
    out = []
    for p in sorted(d.glob(f"{spec.project}_*")):
        # The remainder after the project name must be a phase token:
        # VOICE and VOICE_PEDIATRIC share label directories, and a bare
        # prefix glob would claim the other project's snapshots.
        rest = p.name[len(spec.project) + 1:]
        if not rest.startswith(("full", "core", "audit", "reconcile",
                                "repair", "report")):
            continue
        out.append({"path": str(p),
                    "sha256": hashlib.sha256(
                        p.read_bytes()).hexdigest()})
    return out or None


def _repair_invalid(spec: RunSpec, client, settings: dict[str, Any],
                    usage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validator-driven shape repair of whichever artifacts fail (#356).

    The six phases audit evidence; none of them reliably checks values
    against the digest even when asked (#360: the shape-instructed audit
    discussed `external_resources` without noticing its `restrictions` type).
    The LinkML validator does exactly that, precisely — so its findings drive
    a bounded repair pass instead of failing the fully billed run outright.

    Every failure mode leaves the last-written bytes on disk and is recorded
    in the returned log; the caller re-validates afterwards, so a repair that
    made things worse is caught by the same gate that caught the original.
    """
    log: list[dict[str, Any]] = []
    for artifact, schema, cls in (("full", FULL_SCHEMA_PATH, "Dataset"),
                                  ("core", CORE_SCHEMA_PATH, "CoreDataset")):
        path = _artifact_path(spec, artifact)
        if not path.exists():
            continue
        ph = f"repair_{artifact}"
        # The count the last APPLIED repair was working from. Compared only
        # against applied rounds: a truncated or unusable round rewrote
        # nothing, so its unchanged count says nothing about convergence and
        # must not cancel the retry the round ceiling allows for.
        applied_from: int | None = None
        for rnd in range(1, REPAIR_ROUNDS + 1):
            errors, failure = _validator_lines(path, schema, cls)
            if failure is not None:
                log.append({"phase": ph, "round": rnd,
                            "outcome": f"validator did not run: {failure}"})
                break
            if not errors:
                break

            if applied_from is not None and len(errors) >= applied_from:
                log.append({"phase": ph, "round": rnd,
                            "outcome": (f"not converging: {applied_from} -> "
                                        f"{len(errors)} findings; stopped")})
                break
            req = build_repair(artifact, path.read_text(encoding="utf-8"),
                               errors)
            attempt_started = datetime.now(timezone.utc).isoformat(
                timespec="seconds")
            attempt_t0 = time.monotonic()
            try:
                resp = _call_with_retry(
                    client, model=settings["name"],
                    max_tokens=PHASE_MAX_TOKENS.get(ph, DEFAULT_MAX_TOKENS),
                    temperature=settings["temperature"],
                    system=req.system, messages=req.messages)
            except Exception as exc:                   # noqa: BLE001
                # A dead repair call must not take down a run that would
                # otherwise report invalid-but-complete, as before repair
                # existed.
                log.append({"phase": ph, "round": rnd,
                            "outcome": f"call failed: {exc}"})
                break
            cap = reasoning.capture(resp)
            reasoning.append(_reasoning_path(spec),
                             {"phase": ph, "label": spec.label,
                              "project": spec.project,
                              "model": settings["name"],
                              "attempt": rnd, **cap.to_dict()})
            usage.append({
                "phase": ph, "attempt": rnd,
                "started_at": attempt_started,
                "seconds": round(time.monotonic() - attempt_t0, 3),
                "input_tokens": getattr(resp.usage, "input_tokens", None),
                "output_tokens": getattr(resp.usage, "output_tokens", None),
                "cache_read": getattr(resp.usage, "cache_read_input_tokens", None),
                "cache_write": getattr(resp.usage, "cache_creation_input_tokens", None),
                "max_tokens": PHASE_MAX_TOKENS.get(ph, DEFAULT_MAX_TOKENS),
                "stop_reason": getattr(resp, "stop_reason", None),
            })
            if getattr(resp, "stop_reason", None) == "max_tokens":
                log.append({"phase": ph, "round": rnd,
                            "outcome": "truncated; record left as it was"})
                continue
            text = "".join(b.text for b in resp.content
                           if getattr(b, "type", "") == "text")
            try:
                body = _extract(text, "yaml", schema, cls)
            except RuntimeError as exc:
                log.append({"phase": ph, "round": rnd,
                            "outcome": f"unusable response: {exc}"})
                continue
            body = normalise_multivalued(
                normalise_enum_aliases(normalise_temporal(body)))
            path.write_text(body, encoding="utf-8")
            _snapshot(spec, f"{spec.project}_{ph}_r{rnd}.yaml", body)
            applied_from = len(errors)
            log.append({"phase": ph, "round": rnd, "outcome": "applied",
                        "findings": len(errors)})
    return log


# Server-side conditions that clear on their own. `overloaded_error` is the one
# that matters in practice: CBORG fronts Vertex, and a busy upstream returns it
# mid-stream rather than as an HTTP status.
TRANSIENT_ERROR_TYPES = frozenset({
    "overloaded_error", "api_error", "rate_limit_error", "timeout_error",
})


def _transient_error_type(exc: Exception) -> str | None:
    """The error body's own `type`, when it names a retryable condition.

    Reads the structured body first and only falls back to the message text.
    String matching alone would be fragile, but as a fallback it covers SDK
    versions that do not attach a parsed body to a mid-stream error.
    """
    declared = _declared_error_type(exc)
    if declared is not None:
        # The body stated a type. Trust it either way — falling through to text
        # matching let a 400 whose message merely *quoted* "overloaded_error" be
        # retried five times, which is the opposite of this function's purpose.
        # D4D requests carry dataset prose, so an error echoing back offending
        # content can contain almost any token.
        return declared if declared in TRANSIENT_ERROR_TYPES else None

    # No parsed body — the case the text fallback was written for.
    text = str(exc)
    return next((k for k in TRANSIENT_ERROR_TYPES if k in text), None)


def _declared_error_type(exc: Exception) -> str | None:
    """The `type` the error body states, transient or not, if it states one."""
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return None
    inner = body.get("error")
    if isinstance(inner, dict) and isinstance(inner.get("type"), str):
        return inner["type"]
    kind = body.get("type")
    # A bare {"type": "error"} envelope names no condition; keep looking.
    if isinstance(kind, str) and kind != "error":
        return kind
    return None


def _call_with_retry(client, *, model, max_tokens, temperature, system, messages,
                     sleep=time.sleep):
    """One API call, retrying transient failures.

    Retries rate limits, connection errors and 5xx. Does not retry 4xx other
    than 429: an invalid key or a malformed request will fail identically on
    every attempt, and retrying only multiplies the delay before the operator
    sees the real problem.
    """
    import anthropic
    # Omitted rather than defaulted: claude-opus-5 rejects the parameter with
    # 400 "`temperature` is deprecated for this model", so passing 0.0 fails
    # the request. Sending it only where the model accepts it keeps one code
    # path for both.
    kwargs: dict[str, Any] = {"model": model,
                              "max_tokens": min(max_tokens, output_limit(model)),
                              "system": system, "messages": messages}
    if temperature is not None and accepts_temperature(model):
        kwargs["temperature"] = temperature

    last: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            # Streamed, not because we consume tokens incrementally but because
            # the SDK refuses a non-streaming request whose max_tokens implies a
            # response longer than 10 minutes — and the `full` phase asks for
            # 64k. get_final_message() reassembles the whole Message, so
            # stop_reason and usage stay available and the truncation guard and
            # cache accounting are unaffected.
            with client.messages.stream(**kwargs) as stream:
                return stream.get_final_message()
        except Exception as exc:                      # noqa: BLE001 - re-raised
            transient = isinstance(exc, (
                getattr(anthropic, "RateLimitError", ()),
                getattr(anthropic, "APIConnectionError", ()),
                getattr(anthropic, "InternalServerError", ()),
            ))
            # Raw httpx transport errors are not wrapped in an anthropic class
            # when they occur mid-stream, so classifying only on anthropic types
            # misses them. A 64k-token streamed response through a proxy is a
            # long-lived connection; `RemoteProtocolError: peer closed
            # connection without sending complete message body` killed the
            # second live CHORUS run in phase 1 without a single retry.
            # TransportError is the base for connect/read/write/protocol/timeout.
            try:
                import httpx
                if isinstance(exc, httpx.TransportError):
                    transient = True
            except ImportError:          # pragma: no cover - httpx ships with the SDK
                pass
            status = getattr(exc, "status_code", None)
            if status is not None and 500 <= status < 600:
                transient = True
            # Mid-stream errors carry the *stream's* status, which is 200: the
            # connection opened fine and the failure arrived later as an SSE
            # `error` event. So an `overloaded_error` reaches here as a plain
            # APIStatusError with status_code 200, matches none of the checks
            # above, and kills the run on the first attempt — which is what
            # happened to the first fitness sweep. Classify on the error body's
            # own type, which is where the transience is actually stated.
            if not transient and _transient_error_type(exc):
                transient = True
            if not transient or attempt == MAX_ATTEMPTS:
                raise
            last = exc
            # A rate limit is not the same shape of transient as a dropped
            # connection, and treating it as one loses runs. CBORG's limit is
            # *requests* — 20 per roughly ten minutes — so the whole 2+4+8+16s
            # ladder expires inside a single window and every attempt is spent
            # before the budget refills. 23 runs died this way in one sweep.
            # The error states when it resets; wait for that rather than guess.
            sleep(_rate_limit_pause(exc) or BACKOFF_BASE_SECONDS ** attempt)
    raise last  # unreachable; keeps type checkers honest


RATE_LIMIT_MAX_PAUSE = 15 * 60      # never sleep longer than this on one attempt
RATE_LIMIT_FALLBACK = 90            # limit hit, but no reset time stated


def _rate_limit_pause(exc: Exception, *, now: datetime | None = None) -> float | None:
    """Seconds to wait for a rate limit to clear, or None if not a rate limit.

    CBORG reports `Limit resets at: 2026-07-31 20:28:19 UTC` in the error body.
    Honouring that is the difference between a run that pauses and a run that
    dies: the reset can be ten minutes out, and the ordinary backoff ladder is
    thirty seconds long.
    """
    import anthropic          # imported here, as in `_call_with_retry`
    if not isinstance(exc, getattr(anthropic, "RateLimitError", ())):
        return None
    m = re.search(r"resets at:\s*([\d]{4}-[\d]{2}-[\d]{2}[ T][\d]{2}:[\d]{2}:[\d]{2})",
                  str(exc))
    if not m:
        return RATE_LIMIT_FALLBACK
    try:
        reset = datetime.strptime(m.group(1).replace("T", " "),
                                  "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return RATE_LIMIT_FALLBACK
    current = now or datetime.now(timezone.utc)
    # +2s so the request lands after the window turns over, not on the boundary.
    return max(1.0, min((reset - current).total_seconds() + 2, RATE_LIMIT_MAX_PAUSE))


def execute(spec: RunSpec, *, dry_run: bool = False, resume: bool = True,
            client=None) -> dict[str, Any]:
    """Run the phases, writing each artifact as it completes.

    ``resume`` skips phases whose artifact already exists, so a run that failed
    at phase 5 costs one call to finish rather than six. Set it False to force
    a clean regeneration.
    """
    if dry_run:
        return plan(spec)

    # Before a token is spent. The digest this run is about to send, the schema
    # it validates against and the identity slots its pair check uses all come
    # from the *merged* schemas, which are generated artifacts — so a module
    # edited without regenerating makes every record in the arm attest to a
    # schema this repository no longer holds, invisibly, because the record
    # correctly hashes the file it actually read.
    #
    # Fatal, unlike every other check here. Bundle drift, pair divergence,
    # report claims and grounding all describe a record that remains usable
    # evidence; this corrupts the run's central input, and there would be
    # nothing to preserve by continuing.
    from data_sheets_schema.schema_sync import blocking, check as _schema_check
    stale = blocking(_schema_check())
    if stale:
        detail = "; ".join(f"{r['class']}: {r.get('reason', r['status'])}"
                           for r in stale)
        raise RuntimeError(
            "the merged schema is not built from the current source, so this "
            f"run would record a digest for a schema that does not exist — "
            f"{detail}. Run `make regen-all`, review the diff and commit it, "
            "or check with `d4d schema check-digest`.")

    from data_sheets_schema.provenance import build_record, record_path_for

    settings = _model_settings()
    client = client or _client()
    usage: list[dict[str, Any]] = []
    skipped: list[str] = []
    carry: dict[str, str] = {}

    # Seed the accounting from a prior pass (#362). A completed-but-invalid
    # run keeps its resume state so a re-run can repair it (#361) — but this
    # invocation rebuilds the provenance record, and starting `usage` empty
    # would replace six phases of real token accounting with only the calls
    # this invocation makes. Every billed call stays on the record. Gated on
    # the progress file too: without resume state this is a from-scratch
    # regeneration, and a dead run's accounting does not belong on it.
    prior_repair: list[dict[str, Any]] = []
    if spec.provenance_path.exists() and _progress_path(spec).exists():
        try:
            prior = yaml.safe_load(
                spec.provenance_path.read_text(encoding="utf-8")) or {}
            usage.extend(prior.get("api_usage") or [])
            # The repair log is seeded for the same reason as usage (#366):
            # AI-READI rep1's record showed one repair round where eight had
            # run, because the second invocation overwrote the convergence
            # story its predecessor recorded.
            prior_repair = list(prior.get("repair") or [])
        except yaml.YAMLError:
            pass

    # Resume from an explicit progress file rather than inferring from
    # artifacts. A `full` record on disk may be pre- or post-reconciliation and
    # nothing in the file distinguishes them, so guessing would silently skip
    # reconciliation or redo it.
    progress = _load_progress(spec) if resume else {}
    done = set(progress.get("completed", []))
    # A *finished* run has no progress file — success deletes it — so resuming
    # found nothing and re-ran all six phases of work already paid for. The
    # artifacts on disk are the durable record of what completed; the progress
    # file only adds the phases that leave no artifact of their own.
    # Completion is inferred from the *provenance record*, never from artifacts
    # alone. Three files on disk say nothing about who wrote them: with a flat
    # `out_dir` the paths carry no label at all, so a new label would adopt an
    # older run's outputs and restamp them as its own. Even for a legitimate
    # same-label resume, continuing here rebuilds the record from the current
    # bundle and writes `api_usage: []` over six phases of real token
    # accounting — destroying the measurement the sweep exists to collect.
    #
    # So a run already carrying provenance that matches this spec, and whose
    # artifact hashes still verify, is returned exactly as it was found.
    if (resume and not done and spec.provenance_path.exists()
            and all(_artifact_path(spec, a).exists()
                    for a in ("full", "core", "report"))):
        from data_sheets_schema.runs import check_provenance
        prior = check_provenance(spec.method, spec.label, spec.project,
                                 record=spec.provenance_path)
        if prior["ok"]:
            existing = yaml.safe_load(
                spec.provenance_path.read_text(encoding="utf-8")) or {}
            _progress_path(spec).unlink(missing_ok=True)
            # Re-validate rather than report a clean bill nobody checked.
            # Returning `[]` here asserted "no problems" about records this call
            # never looked at, so a run that had failed validation came back
            # clean the moment it was resumed — and `batch` counts successes
            # from exactly this field. Validation is local and free, and it
            # checks the bytes on disk now rather than a claim recorded earlier.
            problems = validate_outputs(spec)
            return {"label": spec.label, "project": spec.project,
                    "usage": existing.get("api_usage") or [],
                    "skipped": list(PHASES), "validation_problems": problems,
                    "already_complete": True,
                    "outputs": {"full": str(spec.full_path),
                                "core": str(spec.core_path),
                                "report": str(spec.report_path),
                                "provenance": str(spec.provenance_path)}}
    carry: dict[str, str] = {}
    if "Audit findings" in progress:
        carry["Audit findings"] = progress["Audit findings"]
    # An artifact on disk is only resumable if it is still a record. One VOICE
    # core artifact was an 8-key fragment with no `id`, written by the looser
    # extraction guard — and its progress file listed `core` as completed, so a
    # resume would have carried that fragment into reconciliation and spent two
    # further phases correcting a record that was never there. Re-checking on
    # the way *in* costs nothing and localises the damage to the phase that
    # produced it.
    for artifact, name, produced_by in (
            ("full", "Completed full record", ("full", "reconcile_full")),
            ("core", "Completed core record", ("core", "reconcile_core"))):
        path = _artifact_path(spec, artifact)
        if not path.exists():
            continue
        body = path.read_text(encoding="utf-8")
        schema_path, class_name = PHASE_SCHEMA[artifact]
        try:
            parsed = yaml.safe_load(body)
        except yaml.YAMLError:
            parsed = None
        if isinstance(parsed, dict) and _looks_like_a_record(
                parsed, schema_path, class_name):
            carry[name] = body
        else:
            # Not a record: forget the phases that claim to have written it so
            # they run again, rather than resuming on top of a fragment — and
            # the phases that *consumed* it too (#575). Dropping only the
            # producers left `audit` marked done with findings computed against
            # the artifact just discarded, and `reconcile_full` marked done
            # having absorbed from it.
            done -= set(produced_by)
            done -= {ph for ph in PHASES if name in PHASE_NEEDS.get(ph, ())}
    if "reconcile_full" in done and "Completed full record" in carry:
        carry["Reconciled full record"] = carry["Completed full record"]

    for ph in PHASES:
        artifact = PHASE_ARTIFACT.get(ph)
        target = _artifact_path(spec, artifact) if artifact else None

        if ph in done:
            skipped.append(ph)
            continue

        # Every declared input, or none. Filtering to whatever happened to be
        # present let a phase run short of its context and write a record
        # indistinguishable from one where there was nothing to use — the
        # resumed `reconcile_full` that silently absorbs nothing because the
        # core record never reached it (#575).
        absent = [k for k in PHASE_NEEDS[ph] if k not in carry]
        if absent:
            raise RuntimeError(
                f"phase {ph!r} declares inputs {list(PHASE_NEEDS[ph])} and "
                f"{absent} are not available on this resume. Re-run with "
                "--no-resume to regenerate from the phase that produces them; "
                "continuing would write a record that cannot be told from one "
                "produced with the full context.")
        needed = {k: carry[k] for k in PHASE_NEEDS[ph]}
        req = build_phase(spec, ph, carry=needed)

        # A 200 whose body is unusable is not a permanent failure, and treating
        # it as one is expensive. A live CHORUS run returned the whole of
        # `**Phase 2 — Core record.**` for phase 2 — stop_reason `end_turn`,
        # nine tokens of reasoning, no record — and killed a run whose phase 1
        # had already spent ~16k reasoning tokens. `_call_with_retry` cannot see
        # this: at the transport layer the call succeeded. So the *usability* of
        # the body is retried here, on the same budget, and only a phase that
        # fails every attempt takes the run down with it.
        for attempt in range(1, MAX_ATTEMPTS + 1):
            # Stamped per attempt so telemetry can reconstruct wall time; file
            # mtimes only date the artifact a phase wrote, not the attempts
            # that failed on the way there.
            attempt_started = datetime.now(timezone.utc).isoformat(
                timespec="seconds")
            attempt_t0 = time.monotonic()
            resp = _call_with_retry(
                client,
                model=settings["name"],
                max_tokens=PHASE_MAX_TOKENS.get(ph, settings["max_tokens"]),
                temperature=settings["temperature"],
                system=req.system,
                messages=req.messages)

            text = "".join(b.text for b in resp.content
                           if getattr(b, "type", "") == "text")

            # Written before the checks below, so a phase that dies of
            # max_tokens still leaves the record showing where its budget went —
            # that is exactly the case where the thinking share is the diagnosis.
            cap = reasoning.capture(resp)
            reasoning.append(_reasoning_path(spec),
                             {"phase": ph, "label": spec.label,
                              "project": spec.project, "model": settings["name"],
                              "attempt": attempt, **cap.to_dict()})

            usage.append({
                "phase": ph,
                "attempt": attempt,
                "started_at": attempt_started,
                "seconds": round(time.monotonic() - attempt_t0, 3),
                "input_tokens": getattr(resp.usage, "input_tokens", None),
                "output_tokens": getattr(resp.usage, "output_tokens", None),
                "cache_read": getattr(resp.usage, "cache_read_input_tokens", None),
                "cache_write": getattr(resp.usage, "cache_creation_input_tokens", None),
                "max_tokens": PHASE_MAX_TOKENS.get(ph, settings["max_tokens"]),
                "stop_reason": getattr(resp, "stop_reason", None),
            })

            # A truncated record is worse than none: it validates as broken YAML
            # or, worse, as a shorter valid record. Never write it — but a
            # ceiling that one attempt overran is not a fact about the phase, so
            # this is retried too rather than ending the run outright.
            truncated = getattr(resp, "stop_reason", None) == "max_tokens"
            problem = (f"hit max_tokens ({PHASE_MAX_TOKENS.get(ph)}); output "
                       f"truncated" if truncated else None)
            if not truncated:
                try:
                    body = _extract(
                        text, "json" if ph == "audit" else
                        ("md" if ph == "report" else "yaml"),
                        *PHASE_SCHEMA.get(ph, (FULL_SCHEMA_PATH, "Dataset")))
                    break
                except RuntimeError as exc:
                    problem = str(exc)
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"phase {ph!r} produced no usable output in "
                    f"{MAX_ATTEMPTS} attempts. Last problem: {problem}")
            print(f"   phase {ph} attempt {attempt} unusable "
                  f"({problem.splitlines()[0][:70]}); retrying")
            time.sleep(BACKOFF_BASE_SECONDS ** attempt)
        if ph == "audit":
            carry["Audit findings"] = body
            # The progress file that carries the findings is deleted on
            # success, so without this the run's richest intermediate
            # survives only as the report's prose summary (#369).
            _snapshot(spec, f"{spec.project}_audit.json", body)
        elif artifact:
            target.parent.mkdir(parents=True, exist_ok=True)
            if artifact in ("full", "core"):
                body = normalise_multivalued(
                normalise_enum_aliases(normalise_temporal(body)))
            target.write_text(body, encoding="utf-8")
            # Reconcile (and later repair) overwrite the artifact in place;
            # the snapshot is the only record of what this phase produced.
            _snapshot(spec, f"{spec.project}_{ph}.yaml"
                      if artifact != "report" else f"{spec.project}_{ph}.md",
                      body)
            label = {"full": "Completed full record",
                     "core": "Completed core record",
                     "report": "Reconciliation report"}[artifact]
            if ph == "reconcile_full":
                label = "Reconciled full record"
            carry[label] = body

        done.add(ph)
        _save_progress(spec, [x for x in PHASES if x in done],
                       carry.get("Audit findings"))

    rec = build_record(
        spec.project, spec.method, spec.label, mode="live",
        input_bundle=spec.bundle, input_verified=True,
        prompt_paths=spec.prompt_files,
        # The API path builds its instruction with `resolve_prompt`, so it can
        # record exactly what it sent rather than only what it was built from
        # (#419). `prompt_request_hash` was written for this and had no caller.
        prompt_request=spec.instruction,
        prompt_request_spec=spec.render_spec(),
        schema_digest_md5=schema_digest.fingerprint(schema_digest.digest_text("Dataset")),
        extra_notes=[
            (f"Generated via {RUNTIME}; temperature {settings['temperature']} "
             "was set on the request and is therefore observed, not asserted."
             if settings["temperature_applies"]
             else f"Generated via {RUNTIME}. {settings['temperature_note']}"),
            f"Model settings read from {settings['config_path']}.",
            f"Endpoint: {provider_identity()['provider']} at "
            f"{provider_identity()['base_url']}.",
        ] + ([f"Resumed run; phases skipped as already present: {', '.join(skipped)}."]
             if skipped else []))
    # The file hash alone does not identify the request. Substitution is what
    # makes the file and the resolved text different objects, so two runs
    # differing in project, arm, label, model, provider or date shared a prompt
    # hash and were indistinguishable by their recorded prompt evidence — while
    # the module docstring claimed the resolved text was what got hashed. Record
    # both: the file for provenance of the source, the resolution for the
    # request actually sent.
    rec.data["prompts"]["resolved"] = resolved_prompt_digest(spec)
    rec.data["prompts"]["assembly"] = assembly_digest()
    ident = provider_identity()
    rec.data["model"] = {
        "generation_method": "schema-grounded API, six phases",
        "agent_runtime": RUNTIME,
        "provider": ident["provider"] or PROVIDER,
        "base_url": ident["base_url"],
        "model": settings["name"],
        "max_tokens_by_phase": PHASE_MAX_TOKENS,
        # What the run sent, and what it was allowed to send. The second is
        # usually unknown, and #568 exists because that could not be told from
        # the record: AI-READI's reconcile_full ran at 249,015 tokens under a
        # name suggesting far less.
        "context": context_facts(settings["name"], usage),
    }
    if settings["temperature_applies"]:
        rec.data["model"]["temperature"] = settings["temperature"]
        rec.data["model"]["temperature_basis"] = (
            "set on the API request and observed")
    else:
        # Do not record a temperature the request never carried. Writing 0.0
        # here would recreate exactly the unverified claim this module was
        # built to eliminate — the Claude Code headers assert 0.0 for a
        # runtime that never exposed the setting.
        rec.data["model"]["temperature"] = None
        rec.data["model"]["temperature_basis"] = "not applicable to this model"
        rec.data.setdefault("unverified", None)
        rec.data["unverified"] = (rec.data.get("unverified") or []) + [{
            "field": "model.temperature",
            "value": None,
            "reason": settings["temperature_note"],
        }]
    rec.data["api_usage"] = usage
    rec.data["phases_skipped"] = skipped or None
    rec.data["record_generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Validate before declaring success. The first live run completed all six
    # phases, exited 0, printed a tick — and produced a full record whose five
    # DataSubsets lacked required ids and a core record carrying slots
    # CoreDataset does not accept. is_complete() returned True throughout,
    # because it only checks that files exist. An invalid record that looks
    # finished is worse than a failed run.
    problems = validate_outputs(spec)
    if problems:
        # Validator-driven shape repair (#356): the validator's findings are
        # precise and the run is already fully billed, so a bounded repair is
        # cheaper than discarding the run. Hashing happens in
        # validation_block() below, *after* repair — integrity pins the final
        # bytes, never an intermediate state.
        rec.data["repair"] = (prior_repair
                              + _repair_invalid(spec, client, settings,
                                                usage)) or None
        problems = validate_outputs(spec)
    else:
        rec.data["repair"] = prior_repair or None
    rec.data["validation"] = validation_block(spec, problems)
    # After repair, not before: repair rewrites both records, so a pair checked
    # earlier would describe bytes that no longer exist (#544).
    rec.data["pair_consistency"] = pair_consistency(spec)
    rec.data["report_claims"] = report_claims_block(spec)
    rec.data["grounding"] = grounding_block(spec)
    rec.data["intermediates"] = _intermediates_block(spec)

    rec.write(spec.provenance_path)

    # Verify what was just written rather than assuming it. The playbook lists a
    # live record as a completion criterion, and a criterion nothing checks is a
    # request. This path writes the record itself, so the check is cheap — and
    # it fails the run rather than leaving an unattestable artifact behind.
    from data_sheets_schema.runs import check_provenance
    # Checked against the corpus this run wrote into, not the default one. With
    # `out_dir` set — the GitHub assistant's layout — the gate looked in
    # data/d4d_concatenated, found no record, and failed every run that had in
    # fact written one correctly. Same class as the declared-bundle bug: a path
    # assumed rather than derived.
    prov = check_provenance(spec.method, spec.label, spec.project,
                            record=spec.provenance_path)
    if not prov["ok"]:
        raise RuntimeError(
            f"run {spec.label} for {spec.project} finished without usable "
            f"provenance: {prov['reason']}")

    # Only now is the run finished. Keeping the progress file on a validation
    # failure means a rerun resumes instead of regenerating from phase 1.
    if not problems:
        _progress_path(spec).unlink(missing_ok=True)

    return {"label": spec.label, "project": spec.project, "usage": usage,
            "skipped": skipped, "validation_problems": problems,
            # The three post-generation checks, returned rather than only
            # written to the record (#579). A batch that cannot see them counts
            # a run with 11 pair errors and 19 ungrounded identifiers as a
            # success, which is how the v4 arm swept clean.
            "checks": {"pair": rec.data.get("pair_consistency"),
                       "report": rec.data.get("report_claims"),
                       "grounding": rec.data.get("grounding")},
            "outputs": {"full": str(spec.full_path), "core": str(spec.core_path),
                        "report": str(spec.report_path),
                        "provenance": str(spec.provenance_path)}}
