"""`d4d validate` — validate and lint data-sheet instances.

The dataset-author-facing validator: checks one or more YAML/JSON
data-sheet instances against the D4D LinkML schema in-process (no
``poetry run`` subprocess, works from an installed wheel), then runs the
linter (unknown fields, placeholder prose, empty values, missing
identifier prose, British spellings, per-section completeness).

CI-friendly: exits non-zero on schema errors, ``--format json`` emits a
machine-readable report, ``--fail-on-warning`` turns lint warnings into
failures.
"""

import json
import sys
from pathlib import Path

import click

from data_sheets_schema.constants import SCHEMA_DIR, SCHEMA_FULL_PATH
from data_sheets_schema.resources import resource_path

CORE_SCHEMA_PATH = SCHEMA_DIR / "data_sheets_schema_core_all.yaml"

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2


def _resolve_schema(schema_kind: str, schema_file: str | None):
    if schema_file:
        return Path(schema_file), None
    if schema_kind == "core":
        return resource_path(CORE_SCHEMA_PATH), "CoreDataset"
    return resource_path(SCHEMA_FULL_PATH), "Dataset"


def _render_human(report, quiet: bool) -> list:
    summary = report.to_dict()["summary"]
    status = "VALID" if report.valid else "INVALID"
    lines = [
        f"{report.file}: {status} "
        f"({summary['errors']} errors, {summary['warnings']} warnings) "
        f"\u2014 completeness {summary['completeness']}%"
    ]
    if not quiet:
        for issue in report.issues:
            lines.append(
                f"  {issue.severity.upper():7} {issue.code:18} "
                f"{issue.path:40} {issue.message}"
            )
    return lines


@click.command("validate")
@click.argument("files", nargs=-1, required=True,
                type=click.Path(exists=True, dir_okay=False))
@click.option("--schema", "schema_kind", type=click.Choice(["full", "core"]),
              default="full", show_default=True,
              help="Which D4D schema to validate against "
                   "(full: Dataset; core: CoreDataset).")
@click.option("--schema-file", type=click.Path(exists=True, dir_okay=False),
              default=None,
              help="Validate against this schema file instead of --schema.")
@click.option("--target-class", default=None,
              help="Target class in the schema "
                   "(default: Dataset for full, CoreDataset for core).")
@click.option("--format", "fmt", type=click.Choice(["human", "json"]),
              default="human", show_default=True,
              help="Report format.")
@click.option("--output", type=click.Path(dir_okay=False), default=None,
              help="Write the report to this file instead of stdout.")
@click.option("--fail-on-warning", is_flag=True, default=False,
              help="Exit 1 when lint warnings are present, not just on errors.")
@click.option("--quiet", "-q", is_flag=True, default=False,
              help="Human format: print only the per-file summary lines.")
def validate(files, schema_kind, schema_file, target_class, fmt, output,
             fail_on_warning, quiet):
    """Validate and lint data-sheet instance files.

    \b
    Examples:
        d4d validate datasheet.yaml
        d4d validate --schema core datasheet.yaml --format json --output report.json
        d4d validate --fail-on-warning datasheet.yaml
    """
    from data_sheets_schema import instance_lint

    schema_path, default_target = _resolve_schema(schema_kind, schema_file)
    target = target_class or default_target or "Dataset"

    reports = []
    for f in files:
        try:
            reports.append(
                instance_lint.lint_file(f, str(schema_path), target))
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(EXIT_USAGE)
        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(EXIT_USAGE)

    if fmt == "json":
        text = json.dumps([r.to_dict() for r in reports], indent=2)
    else:
        lines = []
        for r in reports:
            lines.extend(_render_human(r, quiet))
        if len(reports) > 1 and not quiet:
            n_valid = sum(1 for r in reports if r.valid)
            lines.append(f"\n{len(reports)} files: {n_valid} valid, "
                         f"{len(reports) - n_valid} invalid")
        text = "\n".join(lines)

    if output:
        Path(output).write_text(text + "\n", encoding="utf-8")
        if fmt == "human":
            click.echo(f"Report written to {output}")
    else:
        click.echo(text)

    any_invalid = any(not r.valid for r in reports)
    any_warnings = any(r.warnings for r in reports)
    if any_invalid or (fail_on_warning and any_warnings):
        sys.exit(EXIT_INVALID)
    sys.exit(EXIT_OK)
