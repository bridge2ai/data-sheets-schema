"""`d4d bundle` — deterministic facts about an input bundle (#707)."""
from __future__ import annotations

import sys
from pathlib import Path

import click

from data_sheets_schema.registry import (DEFAULT_MANIFEST, default_manifest_path, load_registry,
                                         project_choice)


@click.group()
def bundle():
    """Deterministic artifacts derived from an input bundle."""


@bundle.command("chunk")
@click.option("--manifest", type=click.Path(), default=str(DEFAULT_MANIFEST),
              show_default=True, is_eager=True,
              help="source manifest that declares the projects (the registry for --project)")
@click.option("--project", callback=project_choice,
              help="one project the manifest declares (default: all it declares)")
@click.option("--bundle", "bundles", multiple=True, type=click.Path(path_type=Path),
              help="an explicit bundle file, wherever it is (repeatable, #1299); its "
                   "manifest is written beside it as `<stem>_chunks.yaml`")
@click.option("--check", is_flag=True,
              help="rebuild each manifest under its recorded rule and compare; write nothing")
@click.option("--strict", is_flag=True, help="with --check: exit 1 on stale or missing")
@click.option("--max-lines", type=int, default=None, help="override the rule's line bound")
@click.option("--max-bytes", type=int, default=None, help="override the rule's byte bound")
def chunk(manifest, project, bundles, check, strict, max_lines, max_bytes):
    """Write a chunk manifest for each bundle.

    A study bundle's manifest is `data/preprocessed/chunks/{PROJECT}_chunks.yaml`;
    an explicit `--bundle` anywhere else gets `{stem}_chunks.yaml` beside it,
    so two bundles with one basename in different places never share one.

    The manifest is a pure function of the bundle's bytes and the rule it
    records: chunks follow the bundle's `FILE:` boundaries, long documents
    are split into windows bounded in lines and bytes, the summary/TOC
    preamble is its own chunk, and every chunk carries the sha256 of its
    text. A coverage receipt (#708) names these ids; this file is what
    anchors them to bytes.
    """
    from data_sheets_schema.chunking import (DEFAULT_RULE, manifest_status_for,
                                              project_bundles, write_manifest_for)

    targets: list[tuple[str, list[Path]]] = []
    if bundles:
        targets.append(("--bundle", [Path(b) for b in bundles]))
    if project or not bundles:
        reg = load_registry(manifest)
        names = [project] if project else reg.projects()
        study = reg.path is not None and reg.path.resolve() == default_manifest_path().resolve()
        for name in names:
            declared = reg.bundle(name)
            if study:
                # The study's registry: every bundle kind it keeps (#725).
                found = project_bundles(name)
                if declared.exists() and declared not in found:
                    found = [declared] + found
            else:
                # Another registry names its own bundles and nothing else —
                # not the study's, which share the project key (#1367
                # review, must-fix 10).
                found = [declared] if declared.exists() else []
            targets.append((name, found))

    if check:
        bad = 0
        for name, found in targets:
            if not found:
                click.echo(f"   · no_bundle  {name}")
            for b in found:
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
    for name, found in targets:
        if not found:
            click.echo(f"   · {name}: no bundle")
        for b in found:            # every kind a run may declare (#725)
            if not b.exists():
                raise click.ClickException(f"bundle not found: {b}")
            out, m = write_manifest_for(b, rule)
            oversize = sum(1 for c in m["chunks"] if c.get("oversize"))
            largest = max(c["bytes"] for c in m["chunks"]) if m["chunks"] else 0
            click.echo(f"   ✓ {out}  {m['chunk_count']} chunks over {m['bundle_lines']} lines; "
                       f"largest {largest} bytes"
                       + (f"; {oversize} oversize (a single line above max_bytes)" if oversize else ""))
