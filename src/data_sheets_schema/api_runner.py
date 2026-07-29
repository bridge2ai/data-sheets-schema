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
DEFAULT_MAX_TOKENS = 16000

PHASES = ("full", "core", "audit", "reconcile")


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
    subs = {
        "{PROJECT}": spec.project,
        "{ARM}": spec.arm,
        "{METHOD}": spec.method,
        "{BUNDLE}": str(spec.bundle),
        "{LABEL}": spec.label,
        "{MANIFEST_LINE}": spec.manifest_line,
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
    return {
        "name": m.get("name") or "claude-opus-5",
        "temperature": float(m.get("temperature", 0.0)),
        "max_tokens": int(m.get("max_tokens", DEFAULT_MAX_TOKENS)),
        "config_path": str(DETERMINISTIC_CONFIG),
    }


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
    "reconcile": (
        "Phase 4. Given the audit findings, emit a JSON object with keys "
        "`full_yaml`, `core_yaml` and `report_markdown`. The two YAML values are "
        "the corrected records in full; `report_markdown` is the reconciliation "
        "report, which must be written even when nothing changed. Output only "
        "JSON."),
}


def build_phase(spec: RunSpec, phase: str, *, carry: dict[str, str]) -> PhaseRequest:
    """Assemble one phase's request.

    The bundle and schema digest are the cached prefix: identical across all
    four phases of a run, and by far the largest inputs.
    """
    if phase not in PHASES:
        raise ValueError(f"unknown phase {phase!r}")
    cls = "CoreDataset" if phase == "core" else "Dataset"
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


def _client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it, or use plan() / "
            "`d4d api plan` to inspect requests without calling the API.")
    import anthropic
    return anthropic.Anthropic(api_key=key)


def _extract(text: str, kind: str) -> str:
    """Pull YAML or JSON out of a response that may be fenced."""
    fence = re.search(r"```(?:ya?ml|json)?\s*\n(.*?)```", text, re.S)
    return (fence.group(1) if fence else text).strip()


def execute(spec: RunSpec, *, dry_run: bool = False) -> dict[str, Any]:
    """Run all four phases and write the outputs plus a live provenance record."""
    if dry_run:
        return plan(spec)

    # record_path_for, not runs.record_path: the latter returns Path | None
    # because it locates an existing record, and we are choosing where to write
    # a new one.
    from data_sheets_schema.provenance import build_record, record_path_for

    settings = _model_settings()
    client = _client()
    carry: dict[str, str] = {}
    usage: list[dict[str, Any]] = []
    results: dict[str, str] = {}

    for ph in PHASES:
        req = build_phase(spec, ph, carry=carry)
        resp = client.messages.create(
            model=settings["name"],
            max_tokens=settings["max_tokens"],
            temperature=settings["temperature"],
            system=req.system,
            messages=req.messages,
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        results[ph] = text
        usage.append({"phase": ph,
                      "input_tokens": getattr(resp.usage, "input_tokens", None),
                      "output_tokens": getattr(resp.usage, "output_tokens", None),
                      "cache_read": getattr(resp.usage, "cache_read_input_tokens", None),
                      "cache_write": getattr(resp.usage, "cache_creation_input_tokens", None)})
        if ph == "full":
            carry = {"Completed full record": _extract(text, "yaml")}
        elif ph == "core":
            carry = dict(carry, **{"Completed core record": _extract(text, "yaml")})
        elif ph == "audit":
            carry = dict(carry, **{"Audit findings": _extract(text, "json")})

    final = json.loads(_extract(results["reconcile"], "json"))
    for path, key in ((spec.full_path, "full_yaml"),
                      (spec.core_path, "core_yaml"),
                      (spec.report_path, "report_markdown")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(final[key], encoding="utf-8")

    rec = build_record(
        spec.project, spec.method, spec.label, mode="live",
        input_bundle=spec.bundle, input_verified=True,
        prompt_paths=spec.prompt_files,
        schema_digest_md5=schema_digest.fingerprint(schema_digest.digest_text("Dataset")),
        extra_notes=[
            f"Generated via {RUNTIME}; temperature {settings['temperature']} was "
            "set on the request and is therefore observed, not asserted.",
            f"Model settings read from {settings['config_path']}.",
        ])
    rec.data["model"] = {
        "generation_method": "schema-grounded API, four phases",
        "agent_runtime": RUNTIME, "provider": PROVIDER,
        "model": settings["name"], "temperature": settings["temperature"],
        "max_tokens": settings["max_tokens"],
        "temperature_basis": "set on the API request and observed",
    }
    rec.data["api_usage"] = usage
    rec.data["record_generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    prov_path = (spec.out_dir / f"{spec.project}_d4d_metadata.yaml" if spec.out_dir
                 else record_path_for(spec.project, spec.method, spec.label))
    rec.write(prov_path)

    return {"label": spec.label, "project": spec.project, "usage": usage,
            "outputs": {k: str(v) for k, v in
                        (("full", spec.full_path), ("core", spec.core_path),
                         ("report", spec.report_path))}}
