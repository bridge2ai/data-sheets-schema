"""Executable views of the agentic instructions for the current installation.

Renderer 6 records the toolchain paths in its render spec. Versions 1–5 retain
their original instruction bytes and never use this adapter. Renderer 7 adds
honest native temperature headers without changing renderer 6 replay.
"""
from __future__ import annotations

import shlex
import sys
import re
from pathlib import Path

from data_sheets_schema.resources import resource_path

PLAYBOOK = ".claude/commands/d4d-full-core.md"
SCHEMAS = ("src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
           "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml")
UNOBSERVED_TEMPERATURE = "unknown (not observed from the agent runtime)"


def temperature_instructions(text: str) -> str:
    """Current native instructions must not copy a template's zero as fact."""
    text = re.sub(r"(?m)^([ \t]*# Temperature: )0\.0[ \t]*$",
                  lambda match: match[1] + UNOBSERVED_TEMPERATURE, text)
    return text + (
        "\n\n## Native sampling metadata (renderer v7)\n\n"
        "The full and derived core headers must state `Temperature: "
        + UNOBSERVED_TEMPERATURE + "`. Do not infer a sampling setting from a prompt, "
        "a shared API configuration, a model name or an effort level. This workflow "
        "does not observe the native runtime's temperature. Preserve any actual request "
        "evidence separately; an omitted parameter does not establish the provider's "
        "effective temperature or deterministic generation. Keep this limitation in "
        "provenance and reports.\n")


def resource_names(directory: str) -> list[str]:
    """Names shipped by the selected D4D installation or source checkout."""
    from data_sheets_schema.resources import resource_root
    root, _ = resource_root()
    return [f"{directory}/{path.name}" for path in sorted((root / directory).glob("*.md"))]


def toolchain() -> dict:
    paths = {name: str(resource_path(name).absolute()) for name in SCHEMAS}
    for directory in (".claude/commands", ".claude/agents"):
        for name in resource_names(directory):
            paths[name] = str(resource_path(name).absolute())
    # Do not resolve the interpreter symlink: its path selects the venv.
    return validate_toolchain({"python": str(Path(sys.executable).absolute()), "resources": paths})


def validate_toolchain(value) -> dict:
    if (not isinstance(value, dict) or set(value) != {"python", "resources"}
            or not isinstance(value["python"], str) or not Path(value["python"]).is_absolute()
            or not isinstance(value["resources"], dict)
            or any(not isinstance(k, str) or not isinstance(v, str) or not Path(v).is_absolute()
                   for k, v in value["resources"].items())
            or any(k not in value["resources"] for k in (*SCHEMAS, PLAYBOOK))):
        raise ValueError("invalid recorded agentic toolchain")
    return {"python": value["python"], "resources": dict(value["resources"])}


def d4d_command(environment: dict, *args) -> list[str]:
    return [environment["python"], "-m", "data_sheets_schema.cli", *map(str, args)]


def portable_text(text: str, environment: dict) -> str:
    """Replace command/resource locations, retaining the playbook's rules."""
    py = shlex.quote(environment["python"])
    replacements = {
        "poetry run python scripts/agentic_observed.py": py + " -m data_sheets_schema.agentic_observed",
        "poetry run linkml-term-validator": shlex.join([environment["python"], "-c",
            "from linkml_term_validator.cli import main; main()"]),
        "poetry run linkml-validate": shlex.join([environment["python"], "-c",
            "from linkml.validator.cli import cli; cli()"]),
        "poetry run d4d": shlex.join(d4d_command(environment)),
        "poetry run python": py,
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    d4d = shlex.join(d4d_command(environment))
    text = re.sub(r"(?m)^(\s*)d4d(?=\s)", lambda match: match[1] + d4d, text)
    text = text.replace("`d4d ", "`" + d4d + " ")
    for logical, physical in sorted(environment["resources"].items(), key=lambda x: -len(x[0])):
        text = text.replace(logical, shlex.quote(physical))
    return text


def playbook_text(environment: dict | None = None) -> str:
    environment = environment or toolchain()
    return portable_text(Path(environment["resources"][PLAYBOOK]).read_text(encoding="utf-8"), environment)


def instruction_adapter(spec) -> str:
    env = spec._agentic_toolchain
    py = env["python"]
    paths = spec._agentic_artifact_paths
    commands = {
        "Read the executable playbook view": d4d_command(env, "agents", "playbook"),
        "Validate the full record": [py, "-c", "from linkml.validator.cli import cli; cli()",
            "-s", env["resources"][SCHEMAS[0]], "-C", "Dataset", paths["full"]],
        "Derive the core": d4d_command(env, "derive", "core", "--full", paths["full"], "--out", paths["core"]),
        "Validate the core record": [py, "-c", "from linkml.validator.cli import cli; cli()",
            "-s", env["resources"][SCHEMAS[1]], "-C", "CoreDataset", paths["core"]],
        "Check the pair": [py, "-m", "data_sheets_schema.d4d_pair_consistency",
            "--full", paths["full"], "--core", paths["core"]],
    }
    text = ("\n\n## Installed agentic execution (renderer v6)\n\n"
            "The executable playbook view preserves the source playbook's rules and replaces "
            "its tool and schema locations for this Python environment. Read that view before "
            "Phase 1 and apply the selected-input overrides above in every phase. "
            "Use the same full, core and receipt paths throughout; substitute them into the "
            "playbook's placeholders. Term validation remains required and requires Python 3.10 or newer.\n\n")
    for purpose, args in commands.items():
        text += purpose + ":\n\n```bash\n" + shlex.join(args) + "\n```\n\n"
    text += ("For the orchestrator's transcript audit, use `" + shlex.join([py, "-m",
             "data_sheets_schema.agentic_observed", "--bundle", str(spec.bundle),
             "--receipt", paths["receipt"], "--manifest", str(spec.chunk_manifest)])
             + "` followed by the actual transcript paths, quoted separately. "
             "The observer's package module is the accounting instrument. Preserve its hash "
             "and the actual transcripts; do not invent observed values.\n")
    return text
