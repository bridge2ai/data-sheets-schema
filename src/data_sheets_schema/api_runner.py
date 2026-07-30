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
bundle plus digest form a cached prefix reused across all four phases.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from data_sheets_schema import schema_digest
from data_sheets_schema.provenance import (
    DETERMINISTIC_CONFIG,
    load_generation_config,
)

PROMPTS = Path("src/download/prompts")
GENERIC_PROMPT = PROMPTS / "d4d_generic_arm_prompt.md"
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
    "full": 64000, "reconcile_full": 64000,
    "core": 56000, "reconcile_core": 56000,
    "audit": 12000, "report": 12000,
}
DEFAULT_MAX_TOKENS = 64000

# The API is called four to six times per run over minutes; transient 429s and
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
    # The study writes into the run-labelled layout under data/d4d_concatenated.
    # The GitHub assistant writes flat into data/sheets_d4dassistant. Rather than
    # two runners, the layout is a parameter — everything else is identical.
    out_dir: Path | None = None

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
    def prompt_files(self) -> list[Path]:
        files = [GENERIC_PROMPT]
        if self.condition == "tuned":
            files += [TUNED_PROMPT, COMPONENTS / f"{self.project}.md"]
        return files


def prompt_body(path: Path = GENERIC_PROMPT) -> str:
    text = path.read_text(encoding="utf-8")
    if "## Prompt body" not in text:
        raise ValueError(f"{path} has no '## Prompt body' section")
    return text.split("## Prompt body", 1)[1].strip()


def resolve_prompt(spec: RunSpec) -> str:
    """The exact instruction text this run will receive.

    Built here rather than handed to the model as a file reference, so the text
    in the request is the text that was hashed.
    """
    body = prompt_body()
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
        "{RUNTIME}": RUNTIME,
        "{PROVIDER}": ident["provider"] or PROVIDER,
        "{MODEL}": settings["name"],
    }
    for k, v in subs.items():
        body = body.replace(k, v)

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
        chars = len(self.system)
        for b in self.cached_blocks:
            chars += len(b.get("text", ""))
        for m in self.messages:
            c = m.get("content")
            chars += len(c) if isinstance(c, str) else sum(
                len(x.get("text", "")) for x in c)
        return chars // 4


PHASE_INSTRUCTIONS = {
    "full": (
        "Phase 1. Produce the FULL D4D record for class `Dataset`. Output only "
        "the YAML, beginning with the header comment block specified above. No "
        "commentary before or after."),
    "core": (
        "Phase 2. Produce the CORE D4D record for class `CoreDataset`, using "
        "the declared bundle and the completed full record supplied below. The "
        "core record must not assert anything the full record does not support. "
        "Output only the YAML."),
    "audit": (
        "Phase 3. Audit both records against the declared bundle and the "
        "evidence boundary. Report, as a JSON object with keys `findings` (a "
        "list of {severity, record, slot, issue}) and `summary`: any slot whose "
        "value the bundle does not support, any omission the bundle clearly "
        "supports, and any internal inconsistency. Output only JSON."),
    "reconcile_full": (
        "Phase 4a. Apply the audit findings that concern the FULL record and "
        "emit the corrected full record in its entirety, header block included. "
        "If no finding requires a change, emit it unchanged. Output only YAML."),
    "reconcile_core": (
        "Phase 4b. Apply the audit findings that concern the CORE record and "
        "emit the corrected core record in its entirety, header block included. "
        "It must remain consistent with the reconciled full record supplied "
        "below and assert nothing the full record does not support. If no "
        "finding requires a change, emit it unchanged. Output only YAML."),
    "report": (
        "Phase 4c. Write the reconciliation report as Markdown: what the audit "
        "found, what was changed in each record and why, and what was left "
        "as-is and why. Write it even when nothing changed. Output only "
        "Markdown."),
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
    "reconcile_full": ("Completed full record", "Audit findings"),
    "reconcile_core": ("Reconciled full record", "Completed core record", "Audit findings"),
    "report": ("Audit findings",),
}


def build_phase(spec: RunSpec, phase: str, *, carry: dict[str, str]) -> PhaseRequest:
    """Assemble one phase's request.

    The bundle and schema digest are the cached prefix: identical across all
    four phases of a run, and by far the largest inputs.
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

    parts: list[dict[str, Any]] = list(cached)
    parts.append({"type": "text", "text": resolve_prompt(spec)})
    parts.append({"type": "text", "text": PHASE_INSTRUCTIONS[phase]})
    for name, text in carry.items():
        parts.append({"type": "text",
                      "text": f"# {name}\n\n{text}"})

    return PhaseRequest(
        phase=phase,
        system=("You generate Datasheets-for-Datasets records. The declared "
                "input bundle is your only source of dataset facts. The schema "
                "digest defines structure, never content. Never consult a "
                "previously generated D4D record."),
        cached_blocks=cached,
        messages=[{"role": "user", "content": parts}],
    )


def plan(spec: RunSpec) -> dict[str, Any]:
    """Render every phase without calling the API.

    Lets the whole assembly — prompt resolution, caching layout, token cost — be
    inspected and tested without a key or a charge.
    """
    settings = _model_settings()
    carry: dict[str, str] = {}
    phases = []
    for ph in PHASES:
        req = build_phase(spec, ph, carry=carry)
        phases.append({"phase": ph, "approx_input_tokens": req.approx_tokens(),
                       "cached_blocks": len(req.cached_blocks)})
        carry = {"Completed full record": "<phase 1 output>"} if ph == "full" else carry
    return {
        "project": spec.project, "arm": spec.arm, "method": spec.method,
        "label": spec.label, "condition": spec.condition,
        "bundle": str(spec.bundle), "bundle_bytes": spec.bundle.stat().st_size,
        "model": settings,
        "runtime": RUNTIME,
        "prompt_files": [str(p) for p in spec.prompt_files],
        "schema_digest_md5": schema_digest.fingerprint(
            schema_digest.digest_text("Dataset")),
        "phases": phases,
        "approx_total_input_tokens": sum(p["approx_input_tokens"] for p in phases),
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


def _extract(text: str, kind: str) -> str:
    """Pull YAML or JSON out of a response that may be fenced."""
    fence = re.search(r"```(?:ya?ml|json)?\s*\n(.*?)```", text, re.S)
    return (fence.group(1) if fence else text).strip()


PROGRESS_SUFFIX = "_api_progress.json"


def _progress_path(spec: RunSpec) -> Path:
    return spec.metadata_dir / f"{spec.project}{PROGRESS_SUFFIX}"


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


FULL_SCHEMA_PATH = "src/data_sheets_schema/schema/data_sheets_schema_all.yaml"
CORE_SCHEMA_PATH = "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml"


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
    block: dict[str, Any] = {"passed": not problems, "artifacts": artifacts,
                             "recorded_by": recorded_by}
    if problems:
        block["problems"] = problems
    return block


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
        try:
            r = subprocess.run(
                ["poetry", "run", "linkml-validate", "-s", schema, "-C", cls,
                 str(path)],
                capture_output=True, text=True, timeout=180)
        except Exception as exc:                       # noqa: BLE001
            problems.append({"artifact": str(path),
                             "error": f"validator did not run: {exc}"})
            continue
        if r.returncode != 0:
            detail = (r.stdout + r.stderr).strip().splitlines()
            problems.append({"artifact": str(path), "class": cls,
                             "error": " | ".join(detail[:4])})
    return problems


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
            if not transient or attempt == MAX_ATTEMPTS:
                raise
            last = exc
            sleep(BACKOFF_BASE_SECONDS ** attempt)
    raise last  # unreachable; keeps type checkers honest


def execute(spec: RunSpec, *, dry_run: bool = False, resume: bool = True,
            client=None) -> dict[str, Any]:
    """Run the phases, writing each artifact as it completes.

    ``resume`` skips phases whose artifact already exists, so a run that failed
    at phase 5 costs one call to finish rather than six. Set it False to force
    a clean regeneration.
    """
    if dry_run:
        return plan(spec)

    from data_sheets_schema.provenance import build_record, record_path_for

    settings = _model_settings()
    client = client or _client()
    usage: list[dict[str, Any]] = []
    skipped: list[str] = []
    carry: dict[str, str] = {}

    # Resume from an explicit progress file rather than inferring from
    # artifacts. A `full` record on disk may be pre- or post-reconciliation and
    # nothing in the file distinguishes them, so guessing would silently skip
    # reconciliation or redo it.
    progress = _load_progress(spec) if resume else {}
    done = set(progress.get("completed", []))
    carry: dict[str, str] = {}
    if "Audit findings" in progress:
        carry["Audit findings"] = progress["Audit findings"]
    for artifact, name in (("full", "Completed full record"),
                           ("core", "Completed core record")):
        path = _artifact_path(spec, artifact)
        if path.exists():
            carry[name] = path.read_text(encoding="utf-8")
    if "reconcile_full" in done and "Completed full record" in carry:
        carry["Reconciled full record"] = carry["Completed full record"]

    for ph in PHASES:
        artifact = PHASE_ARTIFACT.get(ph)
        target = _artifact_path(spec, artifact) if artifact else None

        if ph in done:
            skipped.append(ph)
            continue

        needed = {k: carry[k] for k in PHASE_NEEDS[ph] if k in carry}
        req = build_phase(spec, ph, carry=needed)
        resp = _call_with_retry(
            client,
            model=settings["name"],
            max_tokens=PHASE_MAX_TOKENS.get(ph, settings["max_tokens"]),
            temperature=settings["temperature"],
            system=req.system,
            messages=req.messages)

        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", "") == "text")
        usage.append({
            "phase": ph,
            "input_tokens": getattr(resp.usage, "input_tokens", None),
            "output_tokens": getattr(resp.usage, "output_tokens", None),
            "cache_read": getattr(resp.usage, "cache_read_input_tokens", None),
            "cache_write": getattr(resp.usage, "cache_creation_input_tokens", None),
            "max_tokens": PHASE_MAX_TOKENS.get(ph, settings["max_tokens"]),
            "stop_reason": getattr(resp, "stop_reason", None),
        })

        # A truncated record is worse than none: it validates as broken YAML or,
        # worse, as a shorter valid record. Fail loudly rather than write it.
        if getattr(resp, "stop_reason", None) == "max_tokens":
            raise RuntimeError(
                f"phase {ph!r} hit max_tokens "
                f"({PHASE_MAX_TOKENS.get(ph)}); output truncated. Raise the "
                f"limit for this phase rather than writing a partial record.")

        body = _extract(text, "json" if ph == "audit" else
                        ("md" if ph == "report" else "yaml"))
        if ph == "audit":
            carry["Audit findings"] = body
        elif artifact:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
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
    ident = provider_identity()
    rec.data["model"] = {
        "generation_method": "schema-grounded API, six phases",
        "agent_runtime": RUNTIME,
        "provider": ident["provider"] or PROVIDER,
        "base_url": ident["base_url"],
        "model": settings["name"],
        "max_tokens_by_phase": PHASE_MAX_TOKENS,
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
    rec.data["validation"] = validation_block(spec, problems)

    rec.write(spec.provenance_path)

    # Only now is the run finished. Keeping the progress file on a validation
    # failure means a rerun resumes instead of regenerating from phase 1.
    if not problems:
        _progress_path(spec).unlink(missing_ok=True)

    return {"label": spec.label, "project": spec.project, "usage": usage,
            "skipped": skipped, "validation_problems": problems,
            "outputs": {"full": str(spec.full_path), "core": str(spec.core_path),
                        "report": str(spec.report_path),
                        "provenance": str(spec.provenance_path)}}
