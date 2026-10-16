#!/usr/bin/env python3
"""Publish retained v8 replicate 1 for Standards Explorer (#5055), 2026-10-16.

Inputs: four immutable full YAMLs and original provenance at SOURCE_COMMIT.
Outputs: four HTMLs, dedicated CSS and a hashed manifest in src/html/output/.
Run from the repository root with PYTHONPATH=src:. Use --check to verify bytes.
This is historical display only: no generation, schema migration or rescore.
"""

import argparse
from collections import Counter
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

import yaml

from data_sheets_schema.rendering.human_readable_renderer import (
    HumanReadableRenderer,
    provenance_for,
)

SOURCE_COMMIT = "fd031a8517c1dbe0e8b2365c8e784909330e6d02"
RENDERED_ON = "2026-10-16"
OUTPUT = Path("src/html/output")
COHORT = Path("notes/reference_rescore_2026-09-12_cborg_runtime/manifest.json")
PROJECTS = {"AI_READI": "04g", "CHORUS": "04f", "CM4AI": "04g", "VOICE": "04f"}
REPOSITORY = "https://github.com/bridge2ai/data-sheets-schema"
CSS = """/* v8 publication styles: scoped for Standards Explorer's embedded HTML. */
.d4d-v8 { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #253044; background: #fff; max-width: 1200px; margin: 0 auto; padding: 1rem; overflow-wrap: anywhere; }
.d4d-v8 .header { background: #314b76; color: #fff; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; }
.d4d-v8 .header h1 { color: inherit; font-size: 1.75rem; margin: 0 0 .5rem; }
.d4d-v8 .subtitle { color: inherit; margin: 0; }
.d4d-v8 .section { background: #fff; border: 1px solid #dce2eb; border-radius: 8px; margin-bottom: 1.5rem; overflow: hidden; }
.d4d-v8 .section-header { background: #f3f6fa; border-bottom: 1px solid #dce2eb; padding: 1rem; display: flex; gap: .75rem; align-items: center; }
.d4d-v8 .section-title { color: #253044; font-size: 1.25rem; margin: 0; }
.d4d-v8 .section-description { color: #475569; font-size: .95rem; margin: .25rem 0 0; }
.d4d-v8 .section-content { padding: 1rem; }
.d4d-v8 .data-item { border-bottom: 1px solid #dce2eb; padding-bottom: 1rem; margin-bottom: 1rem; }
.d4d-v8 .data-item:last-child { border-bottom: 0; margin-bottom: 0; }
.d4d-v8 .item-label { display: block; color: #253044; font-weight: 600; margin-bottom: .5rem; }
.d4d-v8 .item-value { color: #253044; }
.d4d-v8 .item-context { color: #475569; font-size: .9rem; }
.d4d-v8 .nested-dict { background: #f3f6fa; border-radius: 4px; padding: .75rem; margin: .5rem 0; }
.d4d-v8 .nested-dict dt { color: #253044; font-weight: 600; margin-top: .5rem; }
.d4d-v8 .nested-dict dd { color: #253044; margin: .25rem 0 .5rem 1rem; }
.d4d-v8 .formatted-list { padding-left: 1.5rem; margin: .5rem 0; }
.d4d-v8 .formatted-list li { margin-bottom: .5rem; }
.d4d-v8 .source-value { white-space: pre-wrap; overflow-wrap: anywhere; }
.d4d-v8 .provenance { width: 100%; table-layout: fixed; }
.d4d-v8 .provenance th, .d4d-v8 .provenance td { text-align: left; vertical-align: top; overflow-wrap: anywhere; padding: .4rem; }
.d4d-v8 a { color: #145bad; text-decoration: underline; }
.d4d-v8 a:focus { outline: 2px solid #145bad; outline-offset: 2px; }
.d4d-v8 .timestamp { color: #475569; font-size: .9rem; margin-top: 1.5rem; }
@media (max-width: 600px) {
    .d4d-v8 { padding: .5rem; }
    .d4d-v8 .header h1 { font-size: 1.4rem; }
    .d4d-v8 .section-content { padding: .75rem; }
}
"""


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def scalar_text(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def leaves(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from leaves(child)
    else:
        yield scalar_text(value)


class PublicationRenderer(HumanReadableRenderer):
    """Use the existing section layout without lossy table heuristics.

    Generic author/funder tables omit fields in these historical records.
    Recursive lists and definition lists retain every value and escape literal
    source text, including VOICE's sub-<id>/ses-<id>/audio placeholders.
    """

    def _humanize_key(self, key):
        return html.escape(super()._humanize_key(str(key)))

    def format_value(self, value, context="", key=""):
        if isinstance(value, dict):
            return "<dl class='nested-dict'>" + "".join(
                f"<dt>{self._humanize_key(k)}</dt><dd>{self.format_value(v)}</dd>"
                for k, v in value.items()
            ) + "</dl>"
        if isinstance(value, list):
            return "<ul class='formatted-list'>" + "".join(
                f"<li>{self.format_value(item)}</li>" for item in value
            ) + "</ul>"
        text = html.escape(scalar_text(value))
        if isinstance(value, str) and value.startswith(("https://", "http://", "doi:")) and not any(c.isspace() for c in value):
            url = "https://doi.org/" + value[4:] if value.startswith("doi:") else value
            return f'<a class="source-value" href="{html.escape(url, quote=True)}">{text}</a>'
        return f'<span class="source-value">{text}</span>'


class SourceValues(HTMLParser):
    """Read visible scalar nodes, so escaped source markup is checked as text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = []
        self.parts = None

    def handle_starttag(self, tag, attrs):
        if dict(attrs).get("class") == "source-value":
            if self.parts is not None:
                raise ValueError("Nested source-value node")
            self.parts = []

    def handle_data(self, data):
        if self.parts is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.parts is not None and tag in {"span", "a"}:
            self.values.append("".join(self.parts))
            self.parts = None


def verify_values(data, rendered):
    parser = SourceValues()
    parser.feed(rendered)
    expected, observed = Counter(leaves(data)), Counter(parser.values)
    if expected != observed:
        raise ValueError(f"HTML changed source values: missing={expected - observed}; extra={observed - expected}")
    return sum(expected.values())


def pinned_bytes(path):
    content = path.read_bytes()
    original = subprocess.check_output(["git", "show", f"{SOURCE_COMMIT}:{path.as_posix()}"])
    if content != original:
        raise ValueError(f"Historical source differs from pinned commit: {path}")
    return content


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Renderer template changed: expected one {old!r}")
    return text.replace(old, new, 1)


def build_publication():
    retained = {job["input"] for job in json.loads(pinned_bytes(COHORT))["jobs"] if job["cohort"] == "v8"}
    renderer = PublicationRenderer()
    outputs = {}
    manifest = {
        "issue": 5055,
        "source_commit": SOURCE_COMMIT,
        "rendered_on": RENDERED_ON,
        "selection": "Retained baseline API v8 full records, replicate 1 for each project; no score-based selection.",
        "historical_generation_schema": "2.0.0",
        "rendering": "Current section layout with lossless recursive values; historical records are neither regenerated nor revalidated against today's schema.",
        "cohort_manifest": str(COHORT),
        "cohort_manifest_sha256": sha256(COHORT.read_bytes()),
        "rendering_inputs": {
            str(path): sha256(path.read_bytes()) for path in (
                Path("scripts/adhoc/render_v8_standards_explorer.py"),
                Path("src/data_sheets_schema/rendering/human_readable_renderer.py"),
                *(Path("src/data_sheets_schema/schema") / f"{meta['module']}.yaml" for meta in renderer.d4d_sections.values()),
            )
        },
        "records": [],
    }
    for project, date_suffix in PROJECTS.items():
        label = f"2026-09-{date_suffix}_claude-opus-5-api-generic-v8_rep1"
        source = Path("data/d4d_concatenated/claudecode_api") / label / f"{project}_d4d.yaml"
        provenance = Path("data/d4d_concatenated/claudecode_api_core") / label / f"{project}_provenance.yaml"
        if str(source) not in retained:
            raise ValueError(f"Source is not in the retained v8 cohort: {source}")
        source_bytes, provenance_bytes = pinned_bytes(source), pinned_bytes(provenance)
        data, prov = yaml.safe_load(source_bytes), yaml.safe_load(provenance_bytes)
        if prov["run"]["label"] != label or prov["run"]["project"] != project or prov["run"]["replicate"] != 1 or prov["schema"]["declared_version"] != "2.0.0":
            raise ValueError(f"Unexpected original provenance: {provenance}")
        rows, unverified = provenance_for(source)
        if not rows:
            raise ValueError(f"Missing renderable provenance: {provenance}")
        rows = [("Historical validation result" if k == "Validated" else k, html.escape(str(v))) for k, v in rows]
        rows.append(("Generation schema version", "2.0.0"))
        unverified = [(html.escape(str(k)), html.escape(str(v))) for k, v in (unverified or [])]
        display_project = project.replace("_", "-")
        title = html.escape(data.get("title") or data.get("name") or display_project)
        rendered = renderer.render_to_html(data, title, css_file="datasheet-v8.css", provenance=rows, unverified=unverified)
        rendered = replace_once(rendered, '<link rel="stylesheet" href="datasheet-v8.css">', f'<style>\n{CSS}</style>')
        rendered = replace_once(rendered, "<body>", '<body>\n<div class="d4d-v8">')
        rendered = replace_once(rendered, "</body>", '</div>\n</body>')
        rendered = replace_once(rendered, "Datasheet for Dataset - Human Readable Format", f"{display_project} · Historical v8 datasheet · Replicate 1 · Generation schema 2.0.0")
        note = (
            '<div class="section"><div class="section-content">'
            '<p>This page renders the retained v8 baseline API record, replicate 1. '
            'The original generation used schema 2.0.0. This is a historical record, '
            'not a new generation or validation against the current schema.</p>'
            f'<p><a href="{REPOSITORY}/blob/{SOURCE_COMMIT}/{source}">Original YAML</a> · '
            f'<a href="{REPOSITORY}/blob/{SOURCE_COMMIT}/{provenance}">Original generation provenance</a></p>'
            '</div></div>'
        )
        rendered = replace_once(rendered, '    <div class="header">', note + '\n    <div class="header">')
        rendered, count = re.subn(r"Generated on [0-9 :\-]+ using Datasheets for Datasets", f"HTML rendered on {RENDERED_ON}; original generation date is recorded in the provenance above.", rendered)
        if count != 1:
            raise ValueError("Renderer timestamp template changed")
        # Remove template whitespace, then prove source text was not affected.
        rendered = "\n".join(line.rstrip(" \t") for line in rendered.split("\n"))
        scalar_count = verify_values(data, rendered)
        destination = OUTPUT / f"D4D_-_{display_project}_v8_human_readable.html"
        outputs[destination] = rendered.encode("utf-8")
        manifest["records"].append({
            "project": project, "replicate": 1, "run_label": label,
            "source": str(source), "source_sha256": sha256(source_bytes),
            "provenance": str(provenance), "provenance_sha256": sha256(provenance_bytes),
            "generation_recorded_at": prov["record_generated_at"],
            "html": str(destination), "html_sha256": sha256(outputs[destination]),
            "source_scalar_count": scalar_count,
        })
    outputs[OUTPUT / "datasheet-v8.css"] = CSS.encode("utf-8")
    manifest["css"] = {"path": str(OUTPUT / "datasheet-v8.css"), "sha256": sha256(CSS.encode("utf-8"))}
    outputs[OUTPUT / "v8-publication.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify committed publication bytes without writing")
    args = parser.parse_args()
    outputs = build_publication()  # Complete validation before writing any output.
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_bytes() != content:
                raise SystemExit(f"Publication needs rendering: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        print(f"{'Verified' if args.check else 'Rendered'} {path}")


if __name__ == "__main__":
    main()
