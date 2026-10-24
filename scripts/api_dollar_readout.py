#!/usr/bin/env python3
"""Live dollar readout script for D4D API generation runs (Step A3b / #1763, #4345, #4829).

Operator readout tool for monitoring settled ledger costs and in-flight pending calls.
Prices settled calls using CBORG opus-5 rates from ``run_telemetry.py`` and adds
the pending phase's worst case (output cap at $25/M plus input).

Examples:
    # Inspect a historical or active ledger file:
    python scripts/api_dollar_readout.py --ledger data/d4d_concatenated/claudecode_api_core/2026-09-12_claude-opus-5-api-generic-v9_rep1/CHORUS_api_usage_46d8033e251b3c6e.json

    # Monitor an active run with cap and operator stop trigger:
    python scripts/api_dollar_readout.py --ledger path/to/ledger.json --cap 15.0 --trigger 11.50 --watch
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "src").is_dir() and str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import click

from data_sheets_schema.dollar_readout import compute_readout, format_readout


def _find_ledger(
    metadata_dir: Path,
    project: str | None = None,
    label: str | None = None,
) -> Path | None:
    """Find an API usage ledger file in a metadata directory."""
    patterns = []
    if project:
        patterns.append(f"{project}_api_usage_*.json")
    patterns.append("*_api_usage_*.json")

    for pat in patterns:
        matches = sorted(metadata_dir.glob(pat), key=lambda p: p.stat().st_mtime, reverse=True)
        if not label:
            if matches:
                return matches[0]
        else:
            for m in matches:
                try:
                    data = json.loads(m.read_text(encoding="utf-8"))
                    ident = data.get("identity") or {}
                    if ident.get("label") == label:
                        return m
                except (OSError, ValueError):
                    continue
    return None


@click.command()
@click.argument("ledger_arg", required=False, type=click.Path(path_type=Path))
@click.option("--ledger", "-l", "ledger_opt", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Path to the API usage ledger JSON file.")
@click.option("--metadata-dir", "-d", "dir_opt", type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Directory to search for API usage ledger files.")
@click.option("--project", "-p", type=str, default=None,
              help="Project name (e.g. CHORUS, AI_READI).")
@click.option("--label", type=str, default=None,
              help="Run label to filter ledger by identity.")
@click.option("--cap", type=float, default=None,
              help="Dollar cap for the run/allocation (e.g. 15.0).")
@click.option("--trigger", type=float, default=None,
              help="Operator stop trigger in dollars (e.g. 11.50).")
@click.option("--bounds-file", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Optional JSON file with custom per-phase or per-project input bounds.")
@click.option("--worst-case-cache", is_flag=True,
              help="Price un-split integer token input bounds at cache-write rate ($6.25/M) instead of uncached.")
@click.option("--json", "json_out", is_flag=True,
              help="Output readout metrics as JSON.")
@click.option("--watch", "-w", is_flag=True,
              help="Watch mode: continuously refresh readout.")
@click.option("--interval", type=float, default=2.0, show_default=True,
              help="Poll interval in seconds for watch mode.")
def main(
    ledger_arg: Path | None,
    ledger_opt: Path | None,
    dir_opt: Path | None,
    project: str | None,
    label: str | None,
    cap: float | None,
    trigger: float | None,
    bounds_file: Path | None,
    worst_case_cache: bool,
    json_out: bool,
    watch: bool,
    interval: float,
) -> None:
    """Read-only live dollar readout for operator monitoring (Step A3b)."""
    ledger_path = ledger_opt or ledger_arg

    if ledger_path is None and dir_opt is not None:
        ledger_path = _find_ledger(dir_opt, project=project, label=label)
        if ledger_path is None:
            click.echo(f"Error: No matching API usage ledger found in {dir_opt}", err=True)
            sys.exit(1)

    if ledger_path is None:
        click.echo("Error: Must specify a ledger file or --metadata-dir.", err=True)
        sys.exit(1)

    if not ledger_path.is_file():
        click.echo(f"Error: Ledger file does not exist: {ledger_path}", err=True)
        sys.exit(1)

    custom_bounds = None
    if bounds_file is not None:
        try:
            custom_bounds = json.loads(bounds_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            click.echo(f"Error loading bounds file {bounds_file}: {exc}", err=True)
            sys.exit(1)

    def _display_once() -> dict:
        summary = compute_readout(
            ledger_path,
            cap=cap,
            trigger=trigger,
            project=project,
            custom_bounds=custom_bounds,
            worst_case_cache=worst_case_cache,
        )
        if json_out:
            click.echo(json.dumps(summary, indent=2))
        else:
            click.echo(format_readout(summary))
        return summary

    if not watch:
        summary = _display_once()
        if summary.get("cap_reached"):
            sys.exit(2)
        if summary.get("trigger_reached"):
            sys.exit(1)
        return

    # Watch loop
    try:
        while True:
            click.clear()
            summary = _display_once()
            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("\nWatch stopped.")


if __name__ == "__main__":
    main()
