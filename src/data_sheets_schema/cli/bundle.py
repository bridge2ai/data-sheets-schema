"""`d4d bundle` — deterministic facts about an input bundle (#707)."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from data_sheets_schema.constants import PROJECTS


@click.group()
def bundle():
    """Deterministic artifacts derived from an input bundle."""


@bundle.command("chunk")
@click.option("--project", type=click.Choice(PROJECTS), help="one project (default: all)")
@click.option("--check", is_flag=True,
              help="rebuild each manifest under its recorded rule and compare; write nothing")
@click.option("--strict", is_flag=True, help="with --check: exit 1 on stale or missing")
@click.option("--max-lines", type=int, default=None, help="override the rule's line bound")
@click.option("--max-bytes", type=int, default=None, help="override the rule's byte bound")
def chunk(project, check, strict, max_lines, max_bytes):
    """Write `data/preprocessed/chunks/{PROJECT}_chunks.yaml`.

    The manifest is a pure function of the bundle's bytes and the rule it
    records: chunks follow the bundle's `FILE:` boundaries, long documents
    are split into windows bounded in lines and bytes, the summary/TOC
    preamble is its own chunk, and every chunk carries the sha256 of its
    text. A coverage receipt (#708) names these ids; this file is what
    anchors them to bytes.
    """
    from data_sheets_schema.chunking import (DEFAULT_RULE, manifest_status_for,
                                              project_bundles, write_manifest_for)

    targets = [project] if project else list(PROJECTS)
    if check:
        bad = 0
        for name in targets:
            bundles = project_bundles(name)
            if not bundles:
                click.echo(f"   · no_bundle  {name}")
            for b in bundles:
                st, detail = manifest_status_for(b)
                mark = {"current": "✓", "stale": "❌", "missing": "❌", "off_rule": "❌",
                        "unreadable": "❌", "no_bundle": "·"}[st]
                click.echo(f"   {mark} {st:<10} {b.name}: {detail}")
                bad += st in ("stale", "missing", "off_rule", "unreadable")
        if strict and bad:
            sys.exit(1)
        return

    rule = dict(DEFAULT_RULE)
    if max_lines is not None:
        rule["max_lines"] = max_lines
    if max_bytes is not None:
        rule["max_bytes"] = max_bytes
    if rule != DEFAULT_RULE:
        # A manifest under a non-default rule is a different instrument; say so
        # in the rule itself rather than letting it pass as the default.
        rule["version"] = f"{DEFAULT_RULE['version']}-custom"
    for name in targets:
        bundles = project_bundles(name)
        if not bundles:
            click.echo(f"   · {name}: no bundle")
        for b in bundles:            # every kind a run may declare (#725)
            out, m = write_manifest_for(b, rule)
            oversize = sum(1 for c in m["chunks"] if c.get("oversize"))
            largest = max(c["bytes"] for c in m["chunks"]) if m["chunks"] else 0
            click.echo(f"   ✓ {out}  {m['chunk_count']} chunks over {m['bundle_lines']} lines; "
                       f"largest {largest} bytes"
                       + (f"; {oversize} oversize (a single line above max_bytes)" if oversize else ""))
