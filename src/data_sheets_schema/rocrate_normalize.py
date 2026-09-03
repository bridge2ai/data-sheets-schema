"""Normalize upstream RO-Crate packages into D4D-usable artifacts.

Reads a crate under ``data/ro-crate_packages/{PROJECT}/`` and writes normalized
outputs to ``{PROJECT}/processed/``. Raw inputs are never modified.

The two consumers are the forks of the with-crate generation arm:

- **deterministic fork** -- uses ``{PROJECT}_crate_d4d.yaml``, the crate's own
  LinkML rendering repaired until it validates against class ``Dataset``.
- **de novo fork** -- uses ``{PROJECT}_crate_metadata_reduced.json``, the crate
  JSON-LD with file inventories collapsed so it fits a generation context.

Every transformation is recorded in ``{PROJECT}_crate_changes.md``. Nothing here
invents facts, fills gaps from the document corpus, or reconciles crate claims
against other sources -- that is the generation agent's job under
``.claude/agents/d4d-provenance-guard.md``.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from linkml_runtime import SchemaView
from data_sheets_schema.schema_view import shared_view

FULL_SCHEMA = Path("src/data_sheets_schema/schema/data_sheets_schema_all.yaml")
TARGET_CLASS = "Dataset"
PACKAGES_DIR = Path("data/ro-crate_packages")

# Keys that duplicate content already carried by a schema slot, so dropping
# them loses nothing. Anything else unknown is dropped but reported louder.
REDUNDANT_KEYS = {
    "format": "distribution_formats",
    "encoding": "distribution_formats",
}

# Non-schema keys that carry a real fact and must be remapped, not dropped.
REMAP_KEYS = {"bytes": "total_size_bytes"}

# Entity-reference lists carrying no descriptive content. A datasheet needs
# their COUNT, not their members: knowing a computation consumed 192 samples is
# informative, listing 192 bare ARK ids is not.
#
# EVI#inputs was missed in the first version and accounted for 33% of CM4AI's
# reduced crate — 46,630 characters of sample identifiers. CHORUS and VOICE
# carry none, which is part of why CM4AI's crate bundle was noisiest.
INVENTORY_SLOTS = ("hasPart",
                   "https://w3id.org/EVI#outputs",
                   "https://w3id.org/EVI#inputs")


# --------------------------------------------------------------------------
# de novo fork input policy
# --------------------------------------------------------------------------
# The de novo arm must extract from crate *evidence*, not copy from a record
# that is already D4D-shaped. Anything already in datasheet form is withheld,
# otherwise the arm measures transcription rather than extraction and stops
# being distinguishable from the deterministic fork.

DE_NOVO_INCLUDE = {
    "{project}_crate_metadata_reduced.json": (
        "crate JSON-LD with file inventories collapsed; the substantive "
        "evidence (rai:* fields, ethics, access, provenance)"
    ),
    "ai_ready_score.json": "AI-readiness self-assessment",
}

DE_NOVO_EXCLUDE = {
    "{project}_crate_d4d.yaml": (
        "already a schema-valid D4D record — this is the deterministic fork's "
        "output; including it would make the de novo arm copy-through"
    ),
    "ro-crate-linkml.yaml": (
        "upstream's own D4D-shaped mapping; same copy-through risk"
    ),
    "ro-crate-datasheet.html": (
        "upstream-authored datasheet rendering of the same content; a "
        "datasheet is the artifact being generated, so it is withheld as input"
    ),
    "ro-crate-preview.html": "per-file listing, up to 11.8 MB, no prose",
}

BUNDLE_SUFFIX = "_preprocessed_with_crate.txt"
CRATE_ONLY_SUFFIX = "_crate_only.txt"
DOCS_BUNDLE_DIR = Path("data/preprocessed/concatenated")


@dataclass
class Change:
    step: str
    action: str
    detail: str
    before: str = ""
    after: str = ""


@dataclass
class Result:
    project: str
    changes: list[Change] = field(default_factory=list)
    outputs: dict[str, Path] = field(default_factory=dict)
    validation: dict[str, str] = field(default_factory=dict)

    def log(self, step: str, action: str, detail: str, before: Any = "", after: Any = "") -> None:
        self.changes.append(
            Change(step, action, detail, _short(before), _short(after))
        )


def _short(v: Any, limit: int = 160) -> str:
    if v == "" or v is None:
        return ""
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= limit else s[: limit - 1] + "…"


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------

def find_crate_files(project_dir: Path) -> dict[str, Path]:
    """Locate crate artifacts, preferring raw/ then the extracted crate/ tree."""
    wanted = {
        "linkml": "ro-crate-linkml.yaml",
        "metadata": "ro-crate-metadata.json",
        "datasheet": "ro-crate-datasheet.html",
        "score": "ai_ready_score.json",
    }
    found: dict[str, Path] = {}
    for key, filename in wanted.items():
        for base in (project_dir / "raw", project_dir / "crate"):
            candidate = base / filename
            if candidate.exists():
                found[key] = candidate
                break
    return found


def build_person_index(metadata: dict) -> dict[str, dict]:
    """Map @id -> Person entity for in-crate reference resolution."""
    return {
        e["@id"]: e
        for e in metadata.get("@graph", [])
        if e.get("@type") == "Person" and "@id" in e
    }


def _org_urn(name: str) -> str:
    """Deterministic surrogate id for an organization named but not identified.

    ``Organization.id`` is a required identifier and the crates supply
    affiliations by name only. Minting an authoritative-looking identifier
    (ROR, GRID) would be a fabricated fact, so this emits an obviously local
    ``urn:d4d:org:`` key that carries no external authority. It is stable
    across runs for the same name.
    """
    slug = "-".join("".join(c.lower() if c.isalnum() else " " for c in name).split())
    return f"urn:d4d:org:{slug}"


def _person_to_creator(ref_id: str, person: dict | None,
                       minted: list[str] | None = None) -> dict:
    """Render a Creator. The ORCID is kept as `id` (range uriorcurie)."""
    creator: dict[str, Any] = {"id": ref_id}
    if not person:
        return creator
    if person.get("name"):
        creator["name"] = person["name"]
    affiliation = person.get("affiliation")
    org_name = None
    if isinstance(affiliation, dict):
        org_name = affiliation.get("name")
    elif isinstance(affiliation, str) and affiliation:
        org_name = affiliation
    if org_name:
        urn = _org_urn(org_name)
        creator["affiliations"] = [{"id": urn, "name": org_name}]
        if minted is not None:
            minted.append(urn)
    return creator


# --------------------------------------------------------------------------
# transform 1-4: the LinkML rendering
# --------------------------------------------------------------------------

def normalize_linkml(
    doc: dict, persons: dict[str, dict], sv: SchemaView, res: Result
) -> dict:
    allowed = {s.name for s in sv.class_induced_slots(TARGET_CLASS)}
    out = dict(doc)

    # 1. reconcile top-level keys against the schema
    for key in list(out):
        if key in allowed:
            continue
        value = out[key]
        if key in REMAP_KEYS and REMAP_KEYS[key] in allowed:
            target = REMAP_KEYS[key]
            if out.get(target) in (None, ""):
                out[target] = value
                res.log("schema-reconcile", "remap", f"`{key}` -> `{target}`",
                        f"{key}: {value}", f"{target}: {value}")
            else:
                res.log("schema-reconcile", "drop",
                        f"`{key}` dropped; `{target}` already populated", value, out[target])
            del out[key]
        elif key in REDUNDANT_KEYS:
            res.log("schema-reconcile", "drop-redundant",
                    f"`{key}` absent from schema; duplicates `{REDUNDANT_KEYS[key]}`", value)
            del out[key]
        else:
            res.log("schema-reconcile", "drop-unknown",
                    f"`{key}` is not a slot on {TARGET_CLASS}", value)
            del out[key]

    # 2. compression must be a single CompressionEnum value
    if "compression" in out:
        enum = sv.get_enum("CompressionEnum")
        permitted = set(enum.permissible_values) if enum else set()
        value = out["compression"]
        if isinstance(value, str) and value in permitted:
            pass  # already valid
        else:
            res.log(
                "compression", "drop",
                "slot is single-valued with range CompressionEnum "
                f"({'|'.join(sorted(permitted))}); supplied value is neither. "
                "Codecs are not inferred from file extensions.",
                value,
            )
            del out["compression"]

    # 3. creators: resolve ORCID references against the crate's Person entities
    if isinstance(out.get("creators"), list):
        resolved, unresolved, rebuilt = 0, 0, []
        minted: list[str] = []
        for entry in out["creators"]:
            if isinstance(entry, dict) and "@id" in entry:
                ref = entry["@id"]
                person = persons.get(ref)
                rebuilt.append(_person_to_creator(ref, person, minted))
                if person:
                    resolved += 1
                else:
                    unresolved += 1
            else:
                rebuilt.append(entry)
        if minted:
            res.log("creators", "mint-surrogate-id",
                    f"{len(set(minted))} organization(s) named without an identifier; "
                    "Organization.id is required, so a local `urn:d4d:org:` "
                    "surrogate was minted. Carries no external authority; not a "
                    "ROR/GRID claim.",
                    "affiliation name only", ", ".join(sorted(set(minted))[:3]))
        if resolved or unresolved:
            out["creators"] = rebuilt
            res.log("creators", "resolve",
                    f"{resolved} reference(s) resolved to name + affiliation "
                    f"from in-crate Person entities; {unresolved} unresolved. "
                    "`@id` renamed to `id`, ORCID retained.",
                    f"{len(out['creators'])} entries, {resolved + unresolved} ref-only",
                    _short(rebuilt[:2]))

    # 4. created_by is a single string on Dataset
    if isinstance(out.get("created_by"), list):
        names: list[str] = []
        for entry in out["created_by"]:
            if isinstance(entry, str) and entry.strip():
                names.append(entry.strip())
            elif isinstance(entry, dict) and "@id" in entry:
                person = persons.get(entry["@id"])
                if person and person.get("name"):
                    names.append(person["name"])
        joined = ", ".join(dict.fromkeys(names))
        res.log("created_by", "flatten",
                f"slot range is string but a {len(out['created_by'])}-item list was "
                f"supplied; resolved and joined into one string ({len(names)} names)",
                f"{len(out['created_by'])} entries", joined)
        out["created_by"] = joined

    return out


# --------------------------------------------------------------------------
# transform 5: reduce the crate JSON-LD
# --------------------------------------------------------------------------

def _summarize_inventory(entries: list) -> dict:
    """Collapse a file-reference list to counts and ARK-family breakdown."""
    families: Counter = Counter()
    for e in entries:
        ident = e.get("@id", "") if isinstance(e, dict) else str(e)
        tail = ident.rsplit("/", 1)[-1]
        stem = tail.split("-")[0] if "-" in tail else tail
        families[stem] += 1
    return {
        "_summarized_by": "d4d rocrate normalize",
        "count": len(entries),
        "id_families": dict(families.most_common(12)),
        "sample_ids": [
            e.get("@id") for e in entries[:5] if isinstance(e, dict) and "@id" in e
        ],
    }


def _summarize_schema_properties(props: dict) -> dict:
    """Compact a data-dictionary `properties` map.

    Column entries whose description merely restates the column name (the
    ``"Column <name>"`` stub emitted by the crate tooling) collapse to
    ``name:type``. Any column carrying a real description is preserved intact,
    so genuine documentation is never traded for compactness.
    """
    columns, kept = [], {}
    for name, spec in props.items():
        if isinstance(spec, dict):
            description = spec.get("description", "")
            if description in ("", f"Column {name}"):
                columns.append(f"{name}:{spec.get('type', '?')}")
                continue
        kept[name] = spec
    summary = {
        "_summarized_by": "d4d rocrate normalize",
        "count": len(props),
        "columns": columns,
    }
    if kept:
        summary["described_columns"] = kept
    return summary


def reduce_metadata(metadata: dict, res: Result, threshold: int = 10) -> dict:
    out = json.loads(json.dumps(metadata))
    collapsed = 0
    for entity in out.get("@graph", []):
        if not isinstance(entity, dict):
            continue
        label = _short(entity.get("name") or entity.get("@id"), 60)

        for slot in INVENTORY_SLOTS:
            value = entity.get(slot)
            if isinstance(value, list) and len(value) > threshold:
                entity[slot] = _summarize_inventory(value)
                collapsed += 1
                res.log("reduce-metadata", "collapse",
                        f"`{slot}` on {label}",
                        f"{len(value):,} entries", f"summary of {len(value):,}")

        # Data-dictionary schemas: large `properties` maps of column definitions.
        props = entity.get("properties")
        if isinstance(props, dict) and len(props) > threshold:
            required = entity.get("required")
            entity["properties"] = _summarize_schema_properties(props)
            collapsed += 1
            res.log("reduce-metadata", "collapse-schema",
                    f"`properties` on {label}; stub descriptions dropped, "
                    "any real description preserved",
                    f"{len(props):,} columns", f"summary of {len(props):,}")
            # `required` that merely repeats the column names is pure duplication.
            if isinstance(required, list) and set(required) == set(props):
                entity["required"] = {
                    "_summarized_by": "d4d rocrate normalize",
                    "count": len(required),
                    "note": "identical to the property names; list omitted",
                }
                res.log("reduce-metadata", "collapse-required",
                        f"`required` on {label} repeated the property names",
                        f"{len(required):,} entries", "count only")

    if not collapsed:
        res.log("reduce-metadata", "none",
                f"no inventory or schema exceeded {threshold} entries")
    return out


# --------------------------------------------------------------------------
# validation + reporting
# --------------------------------------------------------------------------

def validate_d4d(path: Path) -> str:
    proc = subprocess.run(
        ["poetry", "run", "linkml-validate", "-s", str(FULL_SCHEMA),
         "-C", TARGET_CLASS, str(path)],
        capture_output=True, text=True,
    )
    out = (proc.stdout + proc.stderr).strip()
    return "PASS" if proc.returncode == 0 and "No issues found" in out else f"FAIL\n{out}"


def write_report(res: Result, path: Path, sources: dict[str, Path]) -> None:
    lines = [
        f"# RO-Crate Normalization — {res.project}",
        "",
        "Generated by `d4d rocrate normalize`. Raw inputs are never modified;",
        "re-running over unchanged inputs reproduces these outputs exactly.",
        "",
        "## Inputs",
        "",
    ]
    lines += [f"- `{k}`: `{v}`" for k, v in sources.items()]
    lines += ["", "## Outputs", ""]
    lines += [f"- `{k}`: `{v}`" for k, v in res.outputs.items()]
    lines += ["", "## Validation", ""]
    for name, status in res.validation.items():
        head = status.splitlines()[0]
        lines.append(f"- `{name}`: **{head}**")
        if head != "PASS":
            lines += ["", "```", *status.splitlines()[1:][:20], "```", ""]
    lines += ["", f"## Changes ({len(res.changes)})", ""]
    if not res.changes:
        lines.append("No changes were required.")
    else:
        lines += ["| Step | Action | Detail | Before | After |",
                  "|------|--------|--------|--------|-------|"]
        for c in res.changes:
            cells = [c.step, c.action, c.detail, c.before, c.after]
            lines.append("| " + " | ".join(x.replace("|", "\\|").replace("\n", " ")
                                           for x in cells) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# document-corpus separation
# --------------------------------------------------------------------------

def _doi_key(value: str) -> str | None:
    """Reduce any DOI-bearing string to a comparable bare DOI.

    ``doi:10.18130/V3/XNBOPG``, ``https://doi.org/10.18130/V3/XNBOPG`` and
    ``...dataset.xhtml?persistentId=doi:10.18130/V3/XNBOPG`` all reduce to
    ``10.18130/v3/xnbopg``. Returns None when there is no DOI to compare.
    """
    if not value:
        return None
    m = re.search(r"10\.\d{4,9}/[^\s&\"'<>]+", str(value))
    if not m:
        return None
    return m.group(0).rstrip("/.,;").lower()


@dataclass
class CorpusExclusions:
    """Which upstream records are claimed by the crate corpus."""

    dois: dict[str, str] = field(default_factory=dict)      # doi key -> project
    urls: dict[str, str] = field(default_factory=dict)      # url key -> project
    undecided: list[str] = field(default_factory=list)      # projects needing a call
    reasons: dict[str, str] = field(default_factory=dict)   # project -> reason

    def match(self, url: str) -> tuple[str, str] | None:
        """Return (project, reason) if this URL is claimed, else None."""
        key = _doi_key(url)
        if key and key in self.dois:
            project = self.dois[key]
            return project, self.reasons.get(project, "")
        plain = (url or "").rstrip("/").lower()
        if plain in self.urls:
            project = self.urls[plain]
            return project, self.reasons.get(project, "")
        return None


def document_corpus_exclusions(
    packages_dir: Path = PACKAGES_DIR,
) -> CorpusExclusions:
    """Records the crate corpus claims, so the document corpus skips them.

    Derived from ``crate_manifest.yaml`` rather than a separate hand-kept list,
    so it cannot drift from the crates actually held. Only projects that
    declare ``document_corpus: exclude`` contribute; ``allow`` and a missing
    declaration contribute nothing, and ``undecided`` contributes nothing but
    is reported.

    Defaulting to *not* excluding is deliberate: a wrong exclusion silently
    drops a real input document and changes a baseline, which is far harder to
    notice than a wrong inclusion.
    """
    out = CorpusExclusions()
    manifest_path = packages_dir / "crate_manifest.yaml"
    if not manifest_path.exists():
        return out
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    for project, entry in (manifest.get("projects") or {}).items():
        if not isinstance(entry, dict):
            continue
        policy = str(entry.get("document_corpus", "")).strip().lower()
        if policy == "undecided":
            out.undecided.append(project)
            continue
        if policy != "exclude":
            continue
        out.reasons[project] = str(entry.get("document_corpus_reason", "")).strip()
        for field_name in ("dataset_url", "doi", "describes_dataset"):
            value = entry.get(field_name)
            if not value:
                continue
            key = _doi_key(value)
            if key:
                out.dois[key] = project
            if str(value).startswith("http"):
                out.urls[str(value).rstrip("/").lower()] = project
    return out


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def normalize_project(project: str, packages_dir: Path = PACKAGES_DIR,
                      sv: SchemaView | None = None) -> Result:
    project_dir = packages_dir / project
    res = Result(project=project)
    sources = find_crate_files(project_dir)
    if "linkml" not in sources and "metadata" not in sources:
        raise FileNotFoundError(
            f"No crate artifacts found under {project_dir}/raw or {project_dir}/crate"
        )

    sv = sv or shared_view(FULL_SCHEMA)
    out_dir = project_dir / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = json.loads(sources["metadata"].read_text(encoding="utf-8")) \
        if "metadata" in sources else {}
    persons = build_person_index(metadata)

    if "linkml" in sources:
        doc = yaml.safe_load(sources["linkml"].read_text(encoding="utf-8"))
        normalized = normalize_linkml(doc, persons, sv, res)
        target = out_dir / f"{project}_crate_d4d.yaml"
        target.write_text(
            "# Normalized from the upstream crate's own LinkML rendering.\n"
            f"# Source: {sources['linkml']}\n"
            "# Tool: d4d rocrate normalize — see the changes report alongside.\n"
            "# No facts added; repairs only.\n"
            + yaml.safe_dump(normalized, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        res.outputs["d4d"] = target
        res.validation[target.name] = validate_d4d(target)

    if metadata:
        reduced = reduce_metadata(metadata, res)
        target = out_dir / f"{project}_crate_metadata_reduced.json"
        target.write_text(json.dumps(reduced, indent=1, ensure_ascii=False),
                          encoding="utf-8")
        res.outputs["metadata_reduced"] = target

    report = out_dir / f"{project}_crate_changes.md"
    write_report(res, report, sources)
    res.outputs["report"] = report
    return res


# --------------------------------------------------------------------------
# de novo fork: crate-augmented source bundle
# --------------------------------------------------------------------------

class DeNovoPolicyError(RuntimeError):
    """Raised when a withheld artifact would reach the de novo fork's input."""


def assert_de_novo_safe(name: str) -> None:
    """Fail loudly rather than silently admit a datasheet-shaped artifact."""
    for pattern, reason in DE_NOVO_EXCLUDE.items():
        stem = pattern.replace("{project}_", "")
        if name.endswith(stem) or name == stem:
            raise DeNovoPolicyError(
                f"{name!r} is withheld from the de novo fork: {reason}"
            )


def build_crate_bundle(
    project: str,
    packages_dir: Path = PACKAGES_DIR,
    docs_dir: Path = DOCS_BUNDLE_DIR,
    out_path: Path | None = None,
) -> tuple[Path, list[str], list[str]]:
    """Write ``{PROJECT}_preprocessed_with_crate.txt`` for the de novo fork.

    The docs bundle verbatim, plus a crate-evidence section built only from
    artifacts on the include list. Returns (path, included, withheld).

    `out_path` redirects the write, so staleness can be checked by rebuilding
    into a temporary file and comparing (#446). Embedding the docs bundle
    verbatim is what made these go stale: #421 stripped the document bundles
    and nothing rebuilt these, so the de novo arm read curator prose the
    baseline arm no longer saw, for a day, undetected.
    """
    project_dir = packages_dir / project
    processed = project_dir / "processed"
    docs_bundle = docs_dir / f"{project}_preprocessed.txt"

    if not docs_bundle.exists():
        raise FileNotFoundError(
            f"No document bundle at {docs_bundle}; run `make concat-preprocessed` first"
        )
    if not processed.is_dir():
        raise FileNotFoundError(
            f"No normalized crate at {processed}; run `d4d rocrate normalize` first"
        )

    raw_dirs = [project_dir / "raw", project_dir / "crate"]
    included: list[tuple[str, str, str]] = []  # (label, description, text)
    withheld: list[str] = []

    for pattern, description in DE_NOVO_INCLUDE.items():
        filename = pattern.format(project=project)
        for base in (processed, *raw_dirs):
            candidate = base / filename
            if candidate.exists():
                assert_de_novo_safe(candidate.name)
                included.append(
                    (candidate.name, description,
                     candidate.read_text(encoding="utf-8", errors="ignore"))
                )
                break

    # Record what was deliberately left out, so the bundle is self-documenting.
    for pattern, reason in DE_NOVO_EXCLUDE.items():
        filename = pattern.format(project=project)
        for base in (processed, *raw_dirs):
            if (base / filename).exists():
                withheld.append(f"{filename} — {reason}")
                break

    rule = "=" * 80
    header = [
        rule,
        "CRATE-AUGMENTED SOURCE BUNDLE (de novo fork)",
        rule,
        f"Project: {project}",
        f"Document bundle: {docs_bundle}",
        f"Crate package: {project_dir}",
        f"Crate manifest: {packages_dir / 'crate_manifest.yaml'}",
        "",
        "This bundle is the document corpus plus RO-Crate evidence. Artifacts",
        "that are already in D4D or datasheet form are deliberately withheld so",
        "that this arm extracts rather than transcribes; see the exclusion list",
        "below and notes/D4D_GENERATION_ARMS.md.",
        "",
        "CRATE EVIDENCE INCLUDED",
        "-" * 80,
    ]
    header += [f"  + {n} — {d}" for n, d, _ in included] or ["  (none found)"]
    header += ["", "CRATE ARTIFACTS WITHHELD", "-" * 80]
    header += [f"  - {w}" for w in withheld] or ["  (none present)"]
    header += ["", rule, ""]

    parts = [docs_bundle.read_text(encoding="utf-8", errors="ignore")]
    parts.append("\n\n" + rule + "\nCRATE EVIDENCE\n" + rule + "\n")
    for name, description, text in included:
        parts.append(
            f"\n{rule}\nFILE: {name}\nROLE: {description}\n"
            f"SIZE: {len(text):,} characters\n{'-' * 80}\n{text}\n"
        )

    out = out_path or (docs_dir / f"{project}{BUNDLE_SUFFIX}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(header) + "".join(parts), encoding="utf-8")
    return out, [n for n, _, _ in included], withheld


# --------------------------------------------------------------------------
# deterministic fork: publish alongside the model-generated arms
# --------------------------------------------------------------------------

D4D_CONCAT_DIR = Path("data/d4d_concatenated")


def emit_deterministic_arm(
    project: str,
    version: str,
    packages_dir: Path = PACKAGES_DIR,
    concat_dir: Path = D4D_CONCAT_DIR,
    method: str = "rocrate_mapped",
    variant: str = "crate_d4d",
) -> Path:
    """Publish the normalized crate record as the deterministic arm's output.

    Lands at ``{concat_dir}/rocrate_mapped/{version}/{project}_d4d.yaml`` so the
    existing per-method evaluation tooling can compare it against the
    model-generated arms. Never overwrites a populated version directory.
    """
    source = packages_dir / project / "processed" / f"{project}_{variant}.yaml"
    if not source.exists():
        raise FileNotFoundError(
            f"No normalized record at {source}; run `d4d rocrate normalize` first"
        )

    out_dir = concat_dir / method / version
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{project}_d4d.yaml"
    if target.exists():
        raise FileExistsError(
            f"{target} already exists; use a new version label rather than "
            "overwriting a published run"
        )

    header = (
        f"# D4D Datasheet for {project} Dataset\n"
        f"# Generation Method: {method} (no model)\n"
        "# Arm: deterministic — measures mapping fidelity, not extraction\n"
        f"# Source crate: {packages_dir / project}\n"
        f"# Normalized from: {source}\n"
        f"# Crate manifest: {packages_dir / 'crate_manifest.yaml'}\n"
        "# Schema: src/data_sheets_schema/schema/data_sheets_schema_all.yaml\n"
        "# Prior D4D factual reuse: prohibited\n"
        "# Model: none\n"
        f"# Version: {version}\n"
    )
    body = source.read_text(encoding="utf-8")
    # Drop the normalizer's own header; this file carries the arm header instead.
    body = "\n".join(
        line for line in body.splitlines() if not line.startswith("#")
    ).lstrip("\n")
    target.write_text(header + body + "\n", encoding="utf-8")
    return target


def build_crate_only_bundle(
    project: str,
    packages_dir: Path = PACKAGES_DIR,
    docs_dir: Path = DOCS_BUNDLE_DIR,
) -> tuple[Path, list[str], list[str]]:
    """Write ``{PROJECT}_crate_only.txt`` — crate evidence and nothing else.

    The counterpart to AI-READI's healthsheet-only bundle: it measures what one
    upstream structured source supports on its own, with no documents. The same
    withheld-artifact policy applies, so this remains extraction from evidence
    rather than transcription of an already-D4D-shaped rendering.
    """
    project_dir = packages_dir / project
    processed = project_dir / "processed"
    if not processed.is_dir():
        raise FileNotFoundError(
            f"No normalized crate at {processed}; run `d4d rocrate normalize` first"
        )

    raw_dirs = [project_dir / "raw", project_dir / "crate"]
    included: list[tuple[str, str, str]] = []
    withheld: list[str] = []

    for pattern, description in DE_NOVO_INCLUDE.items():
        filename = pattern.format(project=project)
        for base in (processed, *raw_dirs):
            candidate = base / filename
            if candidate.exists():
                assert_de_novo_safe(candidate.name)
                included.append((candidate.name, description,
                                 candidate.read_text(encoding="utf-8", errors="ignore")))
                break
    for pattern, reason in DE_NOVO_EXCLUDE.items():
        filename = pattern.format(project=project)
        for base in (processed, *raw_dirs):
            if (base / filename).exists():
                withheld.append(f"{filename} — {reason}")
                break

    rule = "=" * 80
    header = [
        rule, "CRATE-ONLY SOURCE BUNDLE", rule,
        f"Project: {project}",
        f"Crate package: {project_dir}",
        f"Crate manifest: {packages_dir / 'crate_manifest.yaml'}",
        "",
        "This bundle contains the RO-Crate evidence and NOTHING else — no",
        "publications, no project documentation, no licence pages, no data",
        "repository pages. It measures what a single structured upstream source",
        "supports on its own. It is NOT the project baseline.",
        "",
        "Artifacts that are already D4D-shaped or datasheet-shaped remain",
        "withheld, so this is extraction from evidence, not transcription.",
        "", "CRATE EVIDENCE INCLUDED", "-" * 80,
    ]
    header += [f"  + {n} — {d}" for n, d, _ in included] or ["  (none found)"]
    header += ["", "CRATE ARTIFACTS WITHHELD", "-" * 80]
    header += [f"  - {w}" for w in withheld] or ["  (none present)"]
    header += ["", rule, ""]

    parts = []
    for name, description, text in included:
        parts.append(
            f"\n{rule}\nFILE: {name}\nROLE: {description}\n"
            f"SIZE: {len(text):,} characters\n{'-' * 80}\n{text}\n"
        )
    out = docs_dir / f"{project}{CRATE_ONLY_SUFFIX}"
    out.write_text("\n".join(header) + "".join(parts), encoding="utf-8")
    return out, [n for n, _, _ in included], withheld
